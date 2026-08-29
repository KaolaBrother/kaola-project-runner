#!/usr/bin/env bash

ADAPTER_ID="kimi-cli"
ADAPTER_DISPLAY_NAME="Kimi CLI"
ADAPTER_DEFAULT_BIN="kimi"
ADAPTER_BIN_ENV="KIMI_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"

kimi_surface() {
  local root="$1"
  [[ -f "$root/skills/workflow-next/SKILL.md" && \
     -f "$root/skills/kaola-workflow-finalize/SKILL.md" ]] || return 1
  [[ -f "$root/agents/.kaola-workflow-agent-manifest" || -f "$root/agents/implementer.md" ]] || return 1
  [[ -f "$root/kaola-workflow/scripts/kaola-workflow-claim.js" ]] || return 1
}

adapter_preflight() {
  local user_root="${KIMI_CODE_HOME:-$HOME/.kimi-code}" carrier
  if kimi_surface "$repo/.kimi-code"; then carrier="$repo/.kimi-code"
  elif kimi_surface "$user_root"; then carrier="$user_root"
  else die "missing complete Kimi Kaola Skills, agents, or support scripts"
  fi
  "$RUNTIME_BIN" doctor >/dev/null 2>&1 || die "kimi doctor rejected current configuration"
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1)"
  PREFLIGHT_WORKFLOW_NEXT=true
  PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="complete Kimi Kaola carrier at $carrier and kimi doctor passed"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--session "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
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
  [[ "$title" =~ [Kk]imi || "$command" == node ]]
}

adapter_detect_activity() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'working|thinking\.\.\.|running tool|responding|esc to cancel|esc to interrupt|Waiting for response'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'Trust this folder\?|Enter select.*Esc exit'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)|[│|][[:space:]]*>[[:space:]]*[│|]'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
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
