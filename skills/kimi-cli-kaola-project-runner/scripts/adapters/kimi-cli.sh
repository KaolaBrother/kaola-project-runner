#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="kimi-cli"
ADAPTER_DISPLAY_NAME="Kimi CLI"
ADAPTER_DEFAULT_BIN="kimi"
ADAPTER_BIN_ENV="KIMI_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="unsupported"
ADAPTER_CHILD_PROCESS_TITLE_EXACT="kimi-code"
ADAPTER_DEFAULT_MODEL_NAME="Kimi K3 Max"
ADAPTER_DEFAULT_MODEL_ID="kimi-code/k3"
ADAPTER_DEFAULT_MODEL_EFFORT="max"
ADAPTER_DEFAULT_MODEL_FAST="unknown"

kimi_surface() {
  local root="$1"
  [[ -f "$root/skills/workflow-next/SKILL.md" && \
     -f "$root/skills/kaola-workflow-finalize/SKILL.md" ]] || return 1
  [[ -f "$root/agents/.kaola-workflow-agent-manifest" || -f "$root/agents/implementer.md" ]] || return 1
  [[ -f "$root/kaola-workflow/scripts/kaola-workflow-claim.js" ]] || return 1
}

adapter_preflight() {
  local user_root="${KIMI_CODE_HOME:-$HOME/.kimi-code}" carrier="" doctor_state=failed
  if kimi_surface "$repo/.kimi-code"; then carrier="$repo/.kimi-code"
  elif kimi_surface "$user_root"; then carrier="$user_root"
  fi
  "$RUNTIME_BIN" doctor >/dev/null 2>&1 && doctor_state=passed
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="Kimi CLI communication is available; Kaola carrier=${carrier:-not-discovered}; doctor=$doctor_state"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--session "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
  ADAPTER_LAUNCH_ARGS+=(--model "$RESOLVED_MODEL_ID")
}

adapter_prepare_model_environment() {
  ADAPTER_MODEL_ENV=()
  [[ -z "$RESOLVED_MODEL_EFFORT" ]] || ADAPTER_MODEL_ENV+=("KIMI_MODEL_THINKING_EFFORT=$RESOLVED_MODEL_EFFORT")
}

adapter_process_matches() {
  local process_command="$1" pane_command="$2"
  # Kimi CLI 0.39.x deliberately rewrites Node's process title to this fixed product identity.
  # Require both the exact rewritten command and the live Node process reported by tmux; neither
  # a later argv mention nor a shell with Kimi-looking scrollback satisfies this exception.
  [[ "$process_command" =~ ^kimi-code[[:space:]]*$ && "$pane_command" == node ]]
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  # Kimi 0.39.x leaves the terminal title at the host name. The core has already required either
  # the exact launcher argv path or the exact `kimi-code`/Node process-title identity above.
  [[ "$title" =~ [Kk]imi || "$command" == node ]] || {
    [[ "$capture" == *'Trust this folder?'* && \
       "$capture" == *'Project-level MCP servers are disabled'* && \
       "$capture" == *'Enter select'* && \
       "$capture" == *"Don't trust"* ]]
  }
}

adapter_activity_hint() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'working|thinking\.\.\.|running tool|responding|esc to cancel|esc to interrupt|Waiting for response'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'Trust this folder\?|Enter select.*Esc exit'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)|[│|][[:space:]]*>[[:space:]]*[│|]'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_observe_frame() {
  local frame="$1" pane_facts="${2:-}" hint helper python_bin
  [[ -n "$pane_facts" ]] || pane_facts='{}'
  hint="$(adapter_activity_hint "$frame")"
  helper="${OBSERVATION_HELPER:-$(dirname "$ADAPTER_SOURCE_DIR")/kaola-observation.py}"
  python_bin="${PYTHON_BIN:-python3}"
  printf '%s' "$frame" | KPR_ADAPTER_PANE_FACTS="$pane_facts" "$python_bin" "$helper" kimi-frame "$hint"
}

adapter_extract_session_id() {
  local session_id
  session_id="$(printf '%s\n' "$1" | \
    sed -nE 's/.*[Ss]ession([ _-]?[Ii][Dd])?:[[:space:]]*(session_[A-Za-z0-9_-]+).*/\2/p' | tail -1)"
  if [[ -n "$session_id" ]]; then
    printf '%s\n' "$session_id"
    return 0
  fi
  printf '%s\n' "$1" | grep -oE '[0-9A-HJKMNP-TV-Z]{20,}' | tail -1
}
