#!/usr/bin/env bash

ADAPTER_ID="claude-code"
ADAPTER_DISPLAY_NAME="Claude Code"
ADAPTER_DEFAULT_BIN="claude"
ADAPTER_BIN_ENV="CLAUDE_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"

claude_surface() {
  local root="$1"
  [[ -f "$root/commands/workflow-next.md" || -f "$root/skills/workflow-next/SKILL.md" ]] || return 1
  [[ -f "$root/commands/kaola-workflow-finalize.md" || \
     -f "$root/skills/kaola-workflow-finalize/SKILL.md" ]] || return 1
  [[ -f "$root/agents/.kaola-workflow-agent-manifest" || -f "$root/agents/implementer.md" ]] || return 1
  [[ -f "$root/kaola-workflow/scripts/kaola-workflow-claim.js" ]] || return 1
}

adapter_preflight() {
  local user_root="${CLAUDE_CONFIG_DIR:-$HOME/.claude}" carrier
  if claude_surface "$repo/.claude"; then carrier="$repo/.claude"
  elif claude_surface "$user_root"; then carrier="$user_root"
  else die "missing complete Claude Kaola commands/Skills, agents, or support scripts"
  fi
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1)"
  PREFLIGHT_WORKFLOW_NEXT=true
  PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="complete Claude Kaola carrier at $carrier"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  [[ "$title" =~ [Cc]laude ]]
}

adapter_detect_activity() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi 'esc to interrupt|working|thinking|running tool|responding|press esc'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'Quick safety check|trust this folder|Enter to confirm'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_extract_session_id() { printf '%s\n' "$1" | sed -nE 's/.*Session ID: ([0-9a-fA-F-]{16,}).*/\1/p' | tail -1; }
