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
  local cursor_root="${CURSOR_HOME:-$HOME/.cursor}" authority doctor doctor_json doctor_state
  authority="$cursor_root/kaola-workflow/cursor-authority.json"
  [[ -f "$authority" ]] || die "missing Kaola Cursor authority receipt: $authority"
  [[ -f "$cursor_root/commands/workflow-next.md" && -f "$cursor_root/commands/kaola-workflow-finalize.md" ]] || \
    die "missing global Kaola Cursor commands"
  doctor="$cursor_root/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
  [[ -f "$doctor" ]] || die "missing Kaola Cursor project materializer: $doctor"
  CURSOR_SURFACE_HELPER="$doctor"
  CURSOR_FORGE="$(AUTHORITY="$authority" CURSOR_ROOT="$cursor_root" "$PYTHON_BIN" <<'PY'
import hashlib, json, os, pathlib, stat
root = pathlib.Path(os.environ["CURSOR_ROOT"]).resolve()
receipt_path = pathlib.Path(os.environ["AUTHORITY"])
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
if receipt.get("schema_version") != 1 or receipt.get("kind") != "cursor_global_authority":
    raise SystemExit(1)
forge = receipt.get("forge", "github")
if forge not in {"github", "gitlab", "gitea"}:
    raise SystemExit(1)
files = receipt.get("files")
if not isinstance(files, dict) or not files:
    raise SystemExit(1)
required = {
    "commands/workflow-next.md",
    "commands/kaola-workflow-finalize.md",
    "kaola-workflow/scripts/kaola-workflow-cursor-surface.js",
}
if not required.issubset(files):
    raise SystemExit(1)
for relative, record in files.items():
    pure = pathlib.PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not relative:
        raise SystemExit(1)
    path = root.joinpath(*pure.parts)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise SystemExit(1)
    if hashlib.sha256(path.read_bytes()).hexdigest() != record.get("sha256"):
        raise SystemExit(1)
    if stat.S_IMODE(info.st_mode) != record.get("mode"):
        raise SystemExit(1)
print(forge)
PY
)" || \
    die "Kaola Cursor authority receipt or managed files are invalid"
  CURSOR_NODE_BIN="$(resolve_tool node)" || die "node executable not found for Cursor authority"
  doctor_state=unavailable
  if doctor_json="$("$CURSOR_NODE_BIN" "$CURSOR_SURFACE_HELPER" --doctor --product cli --host local --json 2>/dev/null)"; then
      DOCTOR_JSON="$doctor_json" "$PYTHON_BIN" <<'PY' >/dev/null || die "Kaola Cursor authority is not current"
import json, os
p = json.loads(os.environ["DOCTOR_JSON"])
a = p.get("authority") or {}
if a.get("receipt_status") != "valid" or a.get("freshness") != "current":
    raise SystemExit(1)
PY
      doctor_state=current
  fi
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1)"
  PREFLIGHT_WORKFLOW_NEXT=true
  PREFLIGHT_FINALIZE=true
  if [[ -f "$repo/.cursor/commands/workflow-next.md" && -f "$repo/.cursor/commands/kaola-workflow-finalize.md" ]]; then
    PREFLIGHT_PROJECT_MATERIALIZATION=current
  else
    PREFLIGHT_PROJECT_MATERIALIZATION=required-at-point-of-use
  fi
  PREFLIGHT_DETAIL="valid exact-hash global Cursor authority (doctor=$doctor_state); project materialization remains an explicit Kaola transaction"
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
