#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="cursor-cli"
ADAPTER_DISPLAY_NAME="Cursor CLI"
ADAPTER_DEFAULT_BIN="cursor-agent"
ADAPTER_BIN_ENV="CURSOR_AGENT_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"

adapter_preflight() {
  local cursor_root="${CURSOR_HOME:-$HOME/.cursor}" authority workflow_state=false finalize_state=false authority_state=missing
  authority="$cursor_root/kaola-workflow/cursor-authority.json"
  [[ -f "$authority" ]] && authority_state=present
  [[ -f "$cursor_root/commands/workflow-next.md" ]] && workflow_state=true
  [[ -f "$cursor_root/commands/kaola-workflow-finalize.md" ]] && finalize_state=true
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT="$workflow_state"
  PREFLIGHT_FINALIZE="$finalize_state"
  if [[ -f "$repo/.cursor/commands/workflow-next.md" && -f "$repo/.cursor/commands/kaola-workflow-finalize.md" ]]; then
    PREFLIGHT_PROJECT_MATERIALIZATION=current
  else
    PREFLIGHT_PROJECT_MATERIALIZATION=not-present
  fi
  PREFLIGHT_DETAIL="Cursor CLI communication is available; global Workflow commands are advisory (workflow_next=$workflow_state finalize=$finalize_state authority=$authority_state); Runner start does not materialize project files"
}

adapter_prepare_launch() {
  local launch_repo="$1" materialization
  materialization="$("$CURSOR_NODE_BIN" "$CURSOR_SURFACE_HELPER" \
    --ensure-target "$launch_repo" --forge "$CURSOR_FORGE")" || \
    die "Kaola Cursor project materialization failed"
  MATERIALIZATION_JSON="$materialization" EXPECTED_TARGET="$launch_repo" "$PYTHON_BIN" <<'PY' >/dev/null || \
    die "Kaola Cursor project materializer returned invalid evidence"
import json, os, pathlib
payload = json.loads(os.environ["MATERIALIZATION_JSON"])
target = pathlib.Path(os.environ["EXPECTED_TARGET"]).resolve()
reported = pathlib.Path(payload.get("target", "")).resolve()
if payload.get("status") not in {"current", "materialized"}:
    raise SystemExit(1)
if payload.get("scope") != "project" or reported != target:
    raise SystemExit(1)
if not isinstance(payload.get("files"), int) or payload["files"] < 2:
    raise SystemExit(1)
PY
  [[ -f "$launch_repo/.cursor/commands/workflow-next.md" && \
     -f "$launch_repo/.cursor/commands/kaola-workflow-finalize.md" ]] || \
    die "Kaola Cursor project materialization omitted required commands"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=(--workspace "$launch_repo")
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Cc]ursor ]]
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'ctrl\+c to stop|esc to cancel|Press Esc to interrupt|Waiting for response|^[[:space:]]*[^[:alnum:][:space:]]+.*(Working|Thinking|Reading|Globbing|Grepping|Searching|Running|Responding).*tokens'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|→|>)|Plan, search, build anything'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_observe_frame() {
  local frame="$1" pane_facts="${2:-}" hint helper python_bin
  [[ -n "$pane_facts" ]] || pane_facts='{}'
  hint="$(adapter_activity_hint "$frame")"
  helper="${OBSERVATION_HELPER:-$(dirname "$ADAPTER_SOURCE_DIR")/kaola-observation.py}"
  python_bin="${PYTHON_BIN:-python3}"
  printf '%s' "$frame" | KPR_ADAPTER_PANE_FACTS="$pane_facts" "$python_bin" "$helper" cursor-frame "$hint"
}

adapter_extract_session_id() { printf '%s\n' "$1" | sed -nE 's/.*(chat[_ -]?id|session[_ -]?id)[:= ]+([A-Za-z0-9_-]+).*/\2/ip' | tail -1; }
