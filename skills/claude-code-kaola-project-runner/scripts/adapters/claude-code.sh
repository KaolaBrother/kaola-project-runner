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
  local user_root="${CLAUDE_CONFIG_DIR:-$HOME/.claude}" carrier help_text
  if claude_surface "$repo/.claude"; then carrier="$repo/.claude"
  elif claude_surface "$user_root"; then carrier="$user_root"
  else die "missing complete Claude Kaola commands/Skills, agents, or support scripts"
  fi
  if [[ "${KAOLA_CLAUDE_PROFILE_REQUIRED:-false}" == true ]]; then
    help_text="$("$RUNTIME_BIN" --help 2>&1)"
    for option in --model --effort --permission-mode; do
      grep -Fq -- "$option" <<<"$help_text" || \
        die "Claude Code does not expose required launch option: $option"
    done
  fi
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1)"
  PREFLIGHT_WORKFLOW_NEXT=true
  PREFLIGHT_FINALIZE=true
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="complete Claude Kaola carrier at $carrier"
  if [[ "${KAOLA_CLAUDE_PROFILE_REQUIRED:-false}" == true ]]; then
    PREFLIGHT_DETAIL+="; model, effort, and permission-mode launch options verified"
  fi
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
  if [[ -n "${model:-}" ]]; then ADAPTER_LAUNCH_ARGS+=(--model "$model"); fi
  if [[ -n "${effort:-}" ]]; then ADAPTER_LAUNCH_ARGS+=(--effort "$effort"); fi
  if [[ -n "${permission_mode:-}" ]]; then
    ADAPTER_LAUNCH_ARGS+=(--permission-mode "$permission_mode")
  fi
}

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  # Claude replaces the terminal title with the active task after intake. Core
  # has already proved the exact launcher process, ownership, and repository;
  # keep the second predicate on stable live CLI surfaces rather than title alone.
  [[ "$title" =~ [Cc]laude || "$command" == claude* ]] || \
    printf '%s\n' "$capture" | grep -Eqi 'Claude Code|Opus [0-9]|auto mode on|bypass permissions on'
}

claude_has_unresolved_decision_conflict() {
  # A prompt glyph is not sufficient idle evidence when the visible frame also
  # contains a Workflow decision that is still pending. Keep this deliberately
  # compound: no free-form waiting sentence can gate input by itself.
  #
  # A later runtime output followed by a fresh empty prompt proves that the
  # captured pending frame is stale. This gives manually answered conversations
  # a deterministic clear path without letting old scrollback latch the session.
  awk '
    function is_prompt(line) {
      return line ~ /^[[:space:]]*(❯|›|>)/
    }
    function is_pending(line) {
      return line ~ /^HUMAN_DECISION_REQUIRED[[:space:]]*$/ ||
             line ~ /Workflow decision state:[[:space:]]*PENDING/ ||
             line ~ /Waiting on your #[0-9]+ call[.]?/ ||
             line ~ /Decision remains unresolved[.]?/ ||
             line ~ /Draft response:/
    }
    {
      line = $0
      if (is_pending(line)) {
        pending = NR
        output_after_pending = 0
      } else if (pending && line !~ /^[[:space:]]*$/ && !is_prompt(line)) {
        output_after_pending = NR
      }

      if (is_prompt(line)) {
        prompt = NR
        prompt_text = line
        sub(/^[[:space:]]*(❯|›|>)[[:space:]]*/, "", prompt_text)
        prompt_has_text = prompt_text ~ /[^[:space:]]/
      }
    }
    END {
      if (pending && prompt && (prompt_has_text || output_after_pending <= pending)) exit 0
      exit 1
    }
  '
}

adapter_detect_activity() {
  local capture="$1" tail_sample
  tail_sample="$(printf '%s\n' "$capture" | tail -n 18)"
  if printf '%s\n' "$tail_sample" | grep -Eqi \
      'This command requires approval|Do you want to proceed\?|switch to auto mode|Esc to cancel.*Tab to amend'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'esc to interrupt|working|thinking|running tool|responding|press esc'; then printf '%s\n' busy
  elif printf '%s\n' "$tail_sample" | grep -Eqi 'Quick safety check|trust this folder|Enter to confirm'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^HUMAN_DECISION_REQUIRED[[:space:]]*$'; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | claude_has_unresolved_decision_conflict; then printf '%s\n' waiting-human
  elif printf '%s\n' "$tail_sample" | grep -Eq '^[[:space:]]*(❯|›|>)'; then printf '%s\n' idle
  else printf '%s\n' unknown
  fi
}

adapter_extract_session_id() { printf '%s\n' "$1" | sed -nE 's/.*Session ID: ([0-9a-fA-F-]{16,}).*/\1/p' | tail -1; }
