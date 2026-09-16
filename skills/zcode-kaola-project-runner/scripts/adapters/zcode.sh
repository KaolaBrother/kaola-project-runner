#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="zcode"
ADAPTER_DISPLAY_NAME="ZCode"
ADAPTER_BIN_ENV="ZCODE_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="native Coding Plan default"
ADAPTER_DEFAULT_MODEL_ID=""
ADAPTER_DEFAULT_MODEL_EFFORT=""
ADAPTER_UPGRADE_MODEL_NAME="native Coding Plan default"
ADAPTER_UPGRADE_MODEL_ID=""
ADAPTER_UPGRADE_MODEL_EFFORT=""
ADAPTER_FAST_MECHANISM="none"

# Never PATH-search `zcode`. An explicit absolute ZCODE_BIN wins; otherwise the
# node runtime from KAOLA_ZCODE_NODE. Missing both fails closed in kaola-tmux.sh.
if [[ -n "${ZCODE_BIN:-}" && "${ZCODE_BIN}" == /* && -x "${ZCODE_BIN}" ]]; then
  ADAPTER_DEFAULT_BIN="$ZCODE_BIN"
elif [[ -n "${KAOLA_ZCODE_NODE:-}" && "${KAOLA_ZCODE_NODE}" == /* && -x "${KAOLA_ZCODE_NODE}" ]]; then
  ADAPTER_DEFAULT_BIN="$KAOLA_ZCODE_NODE"
else
  ADAPTER_DEFAULT_BIN=""
fi

adapter_preflight() {
  local entry="${KAOLA_ZCODE_ENTRY:-}"
  PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false
  PREFLIGHT_FINALIZE=false
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  if [[ -n "$RUNTIME_BIN" && -x "$RUNTIME_BIN" ]]; then
    PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"
    [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  fi
  if [[ -n "$entry" && "$entry" == /* && -f "$entry" ]]; then
    PREFLIGHT_DETAIL="ZCode communication is available; explicit entry=$entry node=$RUNTIME_BIN (no PATH discovery)"
  else
    PREFLIGHT_DETAIL="ZCode runtime is not explicit; set KAOLA_ZCODE_ENTRY and KAOLA_ZCODE_NODE to absolute paths (or ZCODE_BIN)"
  fi
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "${KAOLA_ZCODE_ENTRY:-}" && "${KAOLA_ZCODE_ENTRY}" == /* && -f "${KAOLA_ZCODE_ENTRY}" ]]; then
    ADAPTER_LAUNCH_ARGS+=("$KAOLA_ZCODE_ENTRY")
  fi
  ADAPTER_LAUNCH_ARGS+=(--cwd "$launch_repo")
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
  if [[ -n "$RESOLVED_MODEL_ID" ]]; then ADAPTER_LAUNCH_ARGS+=(--model "$RESOLVED_MODEL_ID"); fi
}

adapter_prepare_model_environment() {
  ADAPTER_MODEL_ENV=("ELECTRON_RUN_AS_NODE=1")
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Zz][Cc]ode || "$command" == *zcode* ]] || \
    printf '%s\n' "$capture" | grep -Eqi 'ZCode|Coding Plan|zcode'
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 16)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'Waiting for response|Press Esc to interrupt|Running tool|Working…|Thinking…|Responding…|esc to cancel'; then printf '%s\n' busy
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
  printf '%s\n' "$1" | sed -nE 's/.*sess[_-]?([A-Za-z0-9-]+).*/sess_\1/p' | tail -1
}
