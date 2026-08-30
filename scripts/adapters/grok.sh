#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="grok"
ADAPTER_DISPLAY_NAME="Grok CLI"
ADAPTER_DEFAULT_BIN="grok"
ADAPTER_BIN_ENV="GROK_BIN"
ADAPTER_RECURRING_EXECUTION="supported"
ADAPTER_QUIT_TEXT="/quit"
ADAPTER_ANSWER_MODE="unsupported"

adapter_preflight() {
  local inspect_json parsed
  inspect_json="$(cd "$repo" && "$RUNTIME_BIN" inspect --json)" || die "grok inspect --json failed"
  parsed="$(INSPECT_JSON="$inspect_json" "$PYTHON_BIN" <<'PY'
import json, os, sys
try:
    payload = json.loads(os.environ["INSPECT_JSON"])
except Exception as exc:
    print(f"invalid grok inspect JSON: {exc}", file=sys.stderr)
    raise SystemExit(2)
skills = {item.get("name") for item in payload.get("skills", [])}
missing = sorted({"workflow-next", "kaola-workflow-finalize"} - skills)
if missing:
    print("missing Grok skills: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(3)
print(str(payload.get("grokVersion", "unknown")).replace("\n", " "))
print(json.dumps(payload.get("projectRoot"), ensure_ascii=False))
print("grok inspect discovered required Kaola Skills")
PY
)" || die "Grok Kaola preflight failed"
  PREFLIGHT_VERSION="${parsed%%$'\n'*}"
  parsed="${parsed#*$'\n'}"
  PREFLIGHT_PROJECT_ROOT_JSON="${parsed%%$'\n'*}"
  PREFLIGHT_DETAIL="${parsed#*$'\n'}"
  PREFLIGHT_WORKFLOW_NEXT=true
  PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=(--cwd "$launch_repo" --minimal)
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" == grok ]]
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 16)"
  if printf '%s\n' "$tail_sample" | grep -Eq 'Waiting for response|Press Esc to interrupt|Running tool|Working…|Thinking…|Responding…|esc to cancel'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -q '^❯'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_observe_frame() {
  local frame="$1" pane_facts="${2:-}" hint helper python_bin
  [[ -n "$pane_facts" ]] || pane_facts='{}'
  hint="$(adapter_activity_hint "$frame")"
  helper="${OBSERVATION_HELPER:-$(dirname "$ADAPTER_SOURCE_DIR")/kaola-observation.py}"
  python_bin="${PYTHON_BIN:-python3}"
  printf '%s' "$frame" | KPR_ADAPTER_PANE_FACTS="$pane_facts" "$python_bin" "$helper" generic-frame "$hint"
}

adapter_extract_session_id() {
  printf '%s\n' "$1" | sed -nE 's/.*session[_ ]id[:= ]+([A-Za-z0-9-]+).*/\1/p' | tail -1
}
