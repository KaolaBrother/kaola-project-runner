#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="devin"
ADAPTER_DISPLAY_NAME="Devin CLI"
ADAPTER_DEFAULT_BIN="devin"
ADAPTER_BIN_ENV="DEVIN_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_DEFAULT_MODEL_NAME="Adaptive"
ADAPTER_DEFAULT_MODEL_ID="adaptive"
ADAPTER_DEFAULT_MODEL_EFFORT=""
ADAPTER_DEFAULT_MODEL_FAST="unknown"

devin_surface() {
  local root="$1"
  [[ -f "$root/skills/workflow-next/SKILL.md" || -f "$root/commands/workflow-next.md" ]] || return 1
  [[ -f "$root/skills/kaola-workflow-finalize/SKILL.md" || -f "$root/commands/kaola-workflow-finalize.md" ]] || return 1
}

adapter_preflight() {
  local devin_root="${DEVIN_CONFIG_DIR:-$HOME/.config/devin}" carrier=""
  if devin_surface "$repo/.devin"; then carrier="$repo/.devin"
  elif devin_surface "$devin_root"; then carrier="$devin_root"
  fi
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="Devin CLI communication is available; Kaola carrier=${carrier:-not-discovered}"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
  if [[ -n "$RESOLVED_MODEL_ID" ]]; then
    ADAPTER_LAUNCH_ARGS+=(--model "$RESOLVED_MODEL_ID")
  fi
  ADAPTER_LAUNCH_ARGS+=(--permission-mode "$permission_mode")
  ADAPTER_LAUNCH_ARGS+=(--respect-workspace-trust false)
}

adapter_prepare_model_environment() { ADAPTER_MODEL_ENV=(); }

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Dd]evin || "$command" == devin* ]] || \
    printf '%s\n' "$capture" | grep -Eqi 'Devin CLI|Devin [0-9]|bypass permissions on|accept-edits'
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi \
      'Do you want to proceed|requires approval|switch to auto mode|Esc to cancel.*Tab to amend'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'esc to interrupt|working|thinking|running tool|responding|press esc|Esc to cancel'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'Quick safety check|trust this folder|Enter to confirm'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)'; then printf '%s\n' idle
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
  # Devin CLI does not display a session identifier in TUI output.
  # Return empty to avoid falsely extracting the tmux session name from
  # the relay launch command visible in scrollback.
  printf '%s\n' ""
}
