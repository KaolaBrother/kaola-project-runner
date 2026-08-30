#!/usr/bin/env bash

ADAPTER_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ADAPTER_ID="claude-code"
ADAPTER_DISPLAY_NAME="Claude Code"
ADAPTER_DEFAULT_BIN="claude"
ADAPTER_BIN_ENV="CLAUDE_BIN"
ADAPTER_RECURRING_EXECUTION="unsupported"
ADAPTER_QUIT_TEXT="/exit"
ADAPTER_ANSWER_MODE="claude-clear-v1"
ADAPTER_DEFAULT_MODEL_NAME="Opus 5 High"
ADAPTER_DEFAULT_MODEL_ID="opus"
ADAPTER_DEFAULT_MODEL_EFFORT="high"
ADAPTER_DEFAULT_MODEL_FAST="unknown"

claude_surface() {
  local root="$1"
  [[ -f "$root/commands/workflow-next.md" || -f "$root/skills/workflow-next/SKILL.md" ]] || return 1
  [[ -f "$root/commands/kaola-workflow-finalize.md" || \
     -f "$root/skills/kaola-workflow-finalize/SKILL.md" ]] || return 1
  [[ -f "$root/agents/.kaola-workflow-agent-manifest" || -f "$root/agents/implementer.md" ]] || return 1
  [[ -f "$root/kaola-workflow/scripts/kaola-workflow-claim.js" ]] || return 1
}

adapter_preflight() {
  local user_root="${CLAUDE_CONFIG_DIR:-$HOME/.claude}" carrier="" help_text option_summary="not-checked"
  if claude_surface "$repo/.claude"; then carrier="$repo/.claude"
  elif claude_surface "$user_root"; then carrier="$user_root"
  fi
  PREFLIGHT_WORKFLOW_NEXT=false; PREFLIGHT_FINALIZE=false
  [[ -n "$carrier" ]] && PREFLIGHT_WORKFLOW_NEXT=true PREFLIGHT_FINALIZE=true
  if [[ "${KAOLA_CLAUDE_PROFILE_REQUIRED:-false}" == true ]]; then
    help_text="$("$RUNTIME_BIN" --help 2>&1 || true)"
    option_summary=available
    for option in --model --effort --permission-mode; do
      grep -Fq -- "$option" <<<"$help_text" || option_summary=incomplete
    done
  fi
  PREFLIGHT_VERSION="$("$RUNTIME_BIN" --version 2>&1 | head -1 || true)"; [[ -n "$PREFLIGHT_VERSION" ]] || PREFLIGHT_VERSION=unknown
  PREFLIGHT_PROJECT_MATERIALIZATION=not-required
  PREFLIGHT_DETAIL="Claude Code communication is available; Kaola carrier=${carrier:-not-discovered}; launch-option evidence=$option_summary"
}

adapter_build_launch() {
  local launch_repo="$1" resume_id="$2" continue_mode="$3"
  ADAPTER_LAUNCH_ARGS=()
  if [[ -n "$resume_id" ]]; then ADAPTER_LAUNCH_ARGS+=(--resume "$resume_id")
  elif [[ "$continue_mode" == true ]]; then ADAPTER_LAUNCH_ARGS+=(--continue)
  fi
  ADAPTER_LAUNCH_ARGS+=(--model "$RESOLVED_MODEL_ID")
  if [[ -n "$RESOLVED_MODEL_EFFORT" ]]; then ADAPTER_LAUNCH_ARGS+=(--effort "$RESOLVED_MODEL_EFFORT"); fi
  if [[ -n "${permission_mode:-}" ]]; then
    ADAPTER_LAUNCH_ARGS+=(--permission-mode "$permission_mode")
  fi
}

adapter_prepare_model_environment() { ADAPTER_MODEL_ENV=(); }

adapter_detect_tui() {
  local title="$1" command="$2" capture="$3"
  # Claude replaces the terminal title with the active task after intake. Core
  # has already proved the exact launcher process, ownership, and repository;
  # keep the second predicate on stable live CLI surfaces rather than title alone.
  [[ "$title" =~ [Cc]laude || "$command" == claude* ]] || \
    printf '%s\n' "$capture" | grep -Eqi 'Claude Code|Opus [0-9]|auto mode on|bypass permissions on' || \
    {
      printf '%s\n' "$capture" | grep -Fq 'Completed work is ready to continue.' &&
      printf '%s\n' "$capture" | grep -Eq '^[[:space:]]*shells:[[:space:]]*[0-9]+[[:space:]]*$' &&
      printf '%s\n' "$capture" | grep -Eq '^[[:space:]]*agents:[[:space:]]*[0-9]+[[:space:]]*$' &&
      printf '%s\n' "$capture" | grep -Eq '^[[:space:]]*(❯|›|>)[[:space:]]*$'
    }
}

claude_has_unresolved_decision_conflict() {
  # A prompt glyph is not sufficient idle evidence when the visible frame also
  # contains a Workflow decision that is still pending. Keep this deliberately
  # compound: no free-form waiting sentence can gate input by itself.
  #
  # The gate clears only after later runtime output has replaced the pending
  # evidence in this short current-frame tail. Older scrollback is deliberately
  # outside this classifier, so answered conversations cannot latch forever.
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
      }

      if (is_prompt(line)) {
        prompt = NR
      }
    }
    END {
      if (pending && prompt) exit 0
      exit 1
    }
  '
}

adapter_activity_hint() {
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

adapter_observe_frame() {
  local frame="$1" pane_facts="${2:-}" hint helper python_bin
  [[ -n "$pane_facts" ]] || pane_facts='{}'
  hint="$(adapter_activity_hint "$frame")"
  helper="${OBSERVATION_HELPER:-$(dirname "$ADAPTER_SOURCE_DIR")/kaola-observation.py}"
  python_bin="${PYTHON_BIN:-python3}"
  printf '%s' "$frame" | KPR_ADAPTER_PANE_FACTS="$pane_facts" "$python_bin" "$helper" claude-frame "$hint"
}

adapter_answer_clear_keys() {
  printf '%s\n' C-u
}

adapter_extract_session_id() { printf '%s\n' "$1" | sed -nE 's/.*Session ID: ([0-9a-fA-F-]{16,}).*/\1/p' | tail -1; }
