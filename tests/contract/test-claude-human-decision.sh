#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/claude-code-tmux.sh"
raw_tui="$project_root/tests/fixtures/observations/claude-code/raw-mode-tui.py"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  JSON_INPUT="$input" python3 -c \
    "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d" || \
    fail "$label" "JSON assertion failed: $input"
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" claude-code "$@"
}

make_claude_fixture() {
  local mode="$1" path="$issue_tmp_root/claude-$1"
  cat >"$path" <<EOF
#!/usr/bin/env bash
set -euo pipefail

if [[ "\${1:-}" == --version ]]; then
  printf '%s\\n' 'Claude Code fixture 1.0.0'
  exit 0
fi
if [[ "\${1:-}" == --help ]]; then
  printf '%s\\n' '--model <model>' '--effort <level>' '--permission-mode <mode>'
  exit 0
fi

# The title is deliberately task-specific and is changed again by the test
# after launch. Claude task titles are not a stable identity field.
printf '\\033]0;Issue #842 decision review\\007'
printf '%s\\n' 'Claude Code' 'Opus 5 | high effort'
case '$mode' in
  decision)
    printf '%s\\n' 'HUMAN_DECISION_REQUIRED'
    for ((i = 1; i <= 24; i++)); do printf 'history line %02d\\n' "\$i"; done
    printf '%s\\n' \\
      'Workflow decision state: PENDING' \\
      'Waiting on your #842 call.' \\
      'Decision remains unresolved.' \\
      'Draft response: option 1, rename both' \\
      '❯ option 1, rename both'
    ;;
  decision-empty)
    printf '%s\\n' 'HUMAN_DECISION_REQUIRED'
    for ((i = 1; i <= 24; i++)); do printf 'history line %02d\\n' "\$i"; done
    printf '%s\\n' \\
      'Workflow decision state: PENDING' \\
      'Waiting on your #842 call.' \\
      'Decision options: 1. rename both  2. leave unchanged' \\
      'Claude Code' \\
      'Opus 5 | high effort' \\
      '❯'
    ;;
  idle)
    printf '%s\\n' 'Completed work: issue #900 is finished.' 'Final response recorded.' '❯'
    ;;
  approval)
    printf '%s\\n' \\
      'This command requires approval' \\
      'Do you want to proceed?' \\
      '❯ 1. Yes' \\
      '   2. No' \\
      'Esc to cancel · Tab to amend'
    ;;
  trust)
    printf '%s\\n' 'Quick safety check' 'Trust this folder?' 'Enter to confirm  Esc to exit' '❯'
    ;;
esac

while IFS= read -r line; do
  if [[ "\$line" == /exit ]]; then
    exit 0
  fi
  if [[ '$mode' == decision && "\$line" == 'option 1, rename both' ]]; then
    printf '%s\\n' 'Decision answer received: option 1, rename both'
    for ((i = 1; i <= 16; i++)); do printf 'Resumed work output %02d\\n' "\$i"; done
    printf '%s\\n' \\
      'Claude resumed visibly after the explicit answer.' \\
      'Completed decision-gated work.' \\
      '❯'
  elif [[ '$mode' == decision ]]; then
    # An injected prompt must not accidentally look like a resumed turn.
    printf '%s\\n' \\
      'Workflow decision state: PENDING' \\
      'Waiting on your #842 call.' \\
      'Draft response: option 1, rename both' \\
      '❯ option 1, rename both'
  elif [[ '$mode' == decision-empty ]]; then
    # The empty editor is still unresolved; do not manufacture a resume marker.
    printf '%s\\n' \\
      'Workflow decision state: PENDING' \\
      'Waiting on your #842 call.' \\
      'Decision options: 1. rename both  2. leave unchanged' \\
      'Claude Code' \\
      'Opus 5 | high effort' \\
      '❯'
  else
    printf 'Echoed completed prompt: %s\\n' "\$line"
    printf '%s\\n' 'Completed work remains resumable.' '❯'
  fi
done
EOF
  chmod +x "$path"
  printf '%s\n' "$path"
}

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo claude-human-decision)"
mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"

# Keep this acceptance independent of the user's tmux server and exercise
# both nonzero numbering dimensions. All commands below use the returned
# pane_id, never a guessed window.pane index.
keeper="claude-human-decision-keeper-$$"
"$issue_tmux_bin" new-session -d -s "$keeper" -c "$repo"
"$issue_tmux_bin" set-option -g base-index 1
"$issue_tmux_bin" set-window-option -g pane-base-index 1

decision_fake="$(make_claude_fixture decision)"
empty_decision_fake="$(make_claude_fixture decision-empty)"
idle_fake="$(make_claude_fixture idle)"
approval_fake="$(make_claude_fixture approval)"
trust_fake="$(make_claude_fixture trust)"
export KAOLA_START_TIMEOUT=5

# Recreate the observed frame: the marker is in scrollback, but outside the
# captured tail; current visible evidence still says pending and contains an
# unsent editor draft. A prompt glyph alone must not win this conflict.
export CLAUDE_BIN="$decision_fake"
decision_session="claude-human-decision-$$"
decision_start="$(run_runner start --repo "$repo" --session "$decision_session" 2>&1)" || \
  fail test_claude_decision_start "start failed: $decision_start"

if "$issue_tmux_bin" has-session -t "=$decision_session" >/dev/null 2>&1; then
  decision_status="$(run_runner status --repo "$repo" --session "$decision_session")"
  decision_pane_id="$(JSON_INPUT="$decision_status" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['pane_id'])")"
  [[ "$decision_pane_id" == %* ]] || fail test_claude_decision_stable_pane_id "invalid pane_id: $decision_status"

  dynamic_title='Issue-842-dynamic-task-title'
  "$issue_tmux_bin" select-pane -t "$decision_pane_id" -T "$dynamic_title"
  decision_status="$(run_runner status --repo "$repo" --session "$decision_session")"
  json_assert test_claude_decision_conflict_state \
    "d['activity'] in ('waiting-human', 'unknown') and d['activity'] != 'idle' and d['tui_detected'] and d['pane_count'] == 1" \
    "$decision_status"
  json_assert test_claude_dynamic_title_and_stable_pane_id \
    "d['pane_id'] == '$decision_pane_id' and d['pane_title'] == '$dynamic_title' and d['tui_detected']" \
    "$decision_status"

  decision_capture="$(run_runner capture --repo "$repo" --session "$decision_session" --lines 120)"
  decision_tail="$(printf '%s\n' "$decision_capture" | tail -n 18)"
  if grep -Fq 'HUMAN_DECISION_REQUIRED' <<<"$decision_tail"; then
    fail test_claude_marker_is_outside_captured_tail "marker unexpectedly remained in tail: $decision_tail"
  fi
  grep -Fq 'Waiting on your #842 call.' <<<"$decision_tail" || \
    fail test_claude_visible_waiting_evidence "waiting language missing from tail: $decision_tail"
  grep -Fq 'Draft response: option 1, rename both' <<<"$decision_tail" || \
    fail test_claude_visible_unsent_draft "unsent draft missing from tail: $decision_tail"
  grep -Fq '❯ option 1, rename both' <<<"$decision_tail" || \
    fail test_claude_visible_editor_prompt "editor prompt missing from tail: $decision_tail"

  # The free-form decision evidence above is reporting-only; the controlling
  # agent owns the decision not to append to its retained draft. Stop it with a
  # fresh token, then exercise the answer operation against the structured
  # current-frame marker in the raw-mode fixture. This keeps the old visible
  # decision evidence while ensuring no answer path uses direct tmux input.
  decision_force_stop="$(run_runner stop --repo "$repo" --session "$decision_session" --force)" || \
    fail test_claude_decision_force_stop "force stop failed: $decision_force_stop"
  [[ -z "${decision_force_stop:-}" ]] || json_assert test_claude_decision_force_stop \
    "d['result'] == 'stopped' and d['action'] == 'force-stop' and d['final_state']['session_present'] is False" \
    "$decision_force_stop"

  answer_log="$issue_tmp_root/claude-human-answer.log"
  answer_release="$issue_tmp_root/claude-human-answer-release"
  : >"$answer_log"
  rm -f "$answer_release"
  export CLAUDE_BIN="$raw_tui" FAKE_CLAUDE_MODE=decision FAKE_CLAUDE_SUBMIT_LOG="$answer_log" FAKE_CLAUDE_RELEASE="$answer_release"
  answer_session="claude-human-answer-$$"
  answer_start="$(run_runner start --repo "$repo" --session "$answer_session" 2>&1)" || \
    fail test_claude_public_answer_start "start failed: $answer_start"
  if "$issue_tmux_bin" has-session -t "=$answer_session" >/dev/null 2>&1; then
    answer_observe="$(run_runner observe --repo "$repo" --session "$answer_session")"
    answer_snapshot="$(JSON_INPUT="$answer_observe" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['snapshot_id'])")"
    answer_decision_id="$(JSON_INPUT="$answer_observe" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['structured_decision_marker']['decision_id'])")"
    json_assert test_claude_public_answer_marker \
      "d['editor_state'] == 'nonempty' and d['visible_shell_count'] == 0 and d['visible_agent_count'] == 0 and d['structured_decision_marker']['decision_id'] == '$answer_decision_id'" \
      "$answer_observe"

    answer_result="$(run_runner answer --repo "$repo" --session "$answer_session" --decision-id "$answer_decision_id" --replace-editor --text chosen-answer)" || \
      fail test_claude_public_answer "public answer failed: $answer_result"
    if [[ -n "${answer_result:-}" ]]; then
      json_assert test_claude_public_answer \
        "d['schema_version'] == 2 and d['result'] == 'answer-sent' and d['action'] == 'answer' and d['decision_id'] == '$answer_decision_id' and d['based_on_snapshot'] == '' and d['action_time_snapshot'].startswith('kpr-snapshot-v2:') and d['observation_changed'] is False and d['receipt_id'].startswith('kpr-answer-v2:') and d['prepared_pane_revision'].startswith('kpr-pane-v2:') and 'chosen-answer' not in json.dumps(d) and 'draft-prefix' not in json.dumps(d)" \
        "$answer_result"
      grep -Fxq 'submitted=chosen-answer' "$answer_log" || \
        fail test_claude_public_answer "replacement receipt missing or appended draft: $(cat "$answer_log")"

      pending_answer_observe="$(run_runner observe --repo "$repo" --session "$answer_session")"
      json_assert test_claude_public_answer_barrier_pending \
        "d['later_output_barrier'] is not None and d['later_output_barrier']['state'] == 'pending'" \
        "$pending_answer_observe"
      touch "$answer_release"
      resumed_capture=''
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        resumed_capture="$(run_runner capture --repo "$repo" --session "$answer_session" --lines 18 2>/dev/null || true)"
        if grep -Fq 'Completed work is ready to continue.' <<<"$resumed_capture"; then
          break
        fi
        sleep 0.2
      done
      grep -Fq 'Completed work is ready to continue.' <<<"$resumed_capture" || \
        fail test_claude_public_answer_visible_resume "visible resume evidence missing: $resumed_capture"
      answer_after=''
      barrier_ready=false
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        answer_after="$(run_runner observe --repo "$repo" --session "$answer_session" 2>/dev/null || true)"
        if grep -Fq '"state": "satisfied"' <<<"$answer_after"; then
          barrier_ready=true
          break
        fi
        sleep 0.2
      done
      [[ "$barrier_ready" == true ]] || fail test_claude_public_answer_barrier "later-output barrier did not become satisfied: $answer_after"
      if [[ "$barrier_ready" == true ]]; then
        json_assert test_claude_public_answer_barrier \
          "d['later_output_barrier']['state'] == 'satisfied'" "$answer_after"
        answer_after_snapshot="$(JSON_INPUT="$answer_after" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['snapshot_id'])")"
        follow_up="$(run_runner send --repo "$repo" --session "$answer_session" --if-snapshot "$answer_after_snapshot" --text follow-up-after-resume)" || \
          fail test_claude_public_answer_follow_up "fresh guarded send failed: $follow_up"
        [[ -z "${follow_up:-}" ]] || json_assert test_claude_public_answer_follow_up \
          "d['result'] == 'sent' and d['action'] == 'send'" "$follow_up"
      fi
    fi
    answer_final_observe="$(run_runner observe --repo "$repo" --session "$answer_session")"
    answer_final_snapshot="$(JSON_INPUT="$answer_final_observe" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['snapshot_id'])")"
    run_runner stop --repo "$repo" --session "$answer_session" --force >/dev/null 2>&1 || \
      fail test_claude_public_answer_force_stop "force stop failed"
  fi
fi

# Recreate the same unresolved boundary with an empty editor. Decision and
# footer lines intervene before the final bare prompt, so a prompt glyph is
# not evidence that the conversation is idle. This fixture remains unresolved
# throughout and intentionally has no resume/completion marker.
export CLAUDE_BIN="$empty_decision_fake"
empty_decision_session="claude-human-decision-empty-$$"
empty_decision_start="$(run_runner start --repo "$repo" --session "$empty_decision_session" 2>&1)" || \
  fail test_claude_empty_decision_start "start failed: $empty_decision_start"

if "$issue_tmux_bin" has-session -t "=$empty_decision_session" >/dev/null 2>&1; then
  empty_decision_status="$(run_runner status --repo "$repo" --session "$empty_decision_session")"
  json_assert test_claude_empty_editor_conflict_state \
    "d['activity'] in ('waiting-human', 'unknown') and d['activity'] != 'idle' and d['tui_detected'] and d['pane_count'] == 1" \
    "$empty_decision_status"

  empty_decision_capture="$(run_runner capture --repo "$repo" --session "$empty_decision_session" --lines 120)"
  empty_decision_tail="$(printf '%s\n' "$empty_decision_capture" | tail -n 18)"
  if grep -Fq 'HUMAN_DECISION_REQUIRED' <<<"$empty_decision_tail"; then
    fail test_claude_empty_marker_is_outside_captured_tail "marker unexpectedly remained in tail: $empty_decision_tail"
  fi
  grep -Fq 'Waiting on your #842 call.' <<<"$empty_decision_tail" || \
    fail test_claude_empty_visible_waiting_evidence "waiting language missing from tail: $empty_decision_tail"
  grep -Fq 'Decision options: 1. rename both  2. leave unchanged' <<<"$empty_decision_tail" || \
    fail test_claude_empty_visible_decision_options "decision options missing from tail: $empty_decision_tail"
  grep -Fq 'Opus 5 | high effort' <<<"$empty_decision_tail" || \
    fail test_claude_empty_visible_claude_footer "Claude footer missing from tail: $empty_decision_tail"
  grep -Eq '^[[:space:]]*❯[[:space:]]*$' <<<"$empty_decision_tail" || \
    fail test_claude_empty_editor_prompt "empty editor prompt missing from tail: $empty_decision_tail"
  if grep -Fq 'Claude resumed visibly after the explicit answer.' <<<"$empty_decision_capture" || \
     grep -Fq 'Completed decision-gated work.' <<<"$empty_decision_capture"; then
    fail test_claude_empty_remains_unresolved "fixture emitted a resume/completion marker"
  fi

  # No generic send is attempted: retained-draft/unresolved handling belongs
  # to the controlling agent and Skill policy, not a runner-owned state gate.
  run_runner stop --repo "$repo" --session "$empty_decision_session" --force >/dev/null 2>&1 || \
    fail test_claude_empty_decision_force_stop "force stop failed"
fi

# Preserve an ordinary completed-work prompt as idle.
export CLAUDE_BIN="$idle_fake"
idle_session="claude-completed-idle-$$"
idle_start="$(run_runner start --repo "$repo" --session "$idle_session" 2>&1)" || \
  fail test_claude_completed_idle_start "start failed: $idle_start"
if "$issue_tmux_bin" has-session -t "=$idle_session" >/dev/null 2>&1; then
  idle_status="$(run_runner status --repo "$repo" --session "$idle_session")"
  json_assert test_claude_completed_work_is_idle \
    "d['activity'] == 'idle' and d['tui_detected'] and d['pane_count'] == 1" "$idle_status"
  run_runner stop --repo "$repo" --session "$idle_session" --force >/dev/null 2>&1 || \
    fail test_claude_idle_force_stop "force stop failed"
fi

gate_case() {
  local mode="$1" fake="$2" expected="$3" label="$4" session start_output status
  session="claude-$mode-gate-$$"
  export CLAUDE_BIN="$fake"
  start_output="$(run_runner start --repo "$repo" --session "$session" 2>&1)" || \
    fail "${label}_start" "start failed: $start_output"
  if "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1; then
    status="$(run_runner status --repo "$repo" --session "$session")"
    json_assert "${label}_waits" "d['activity'] == 'waiting-human' and d['activity'] != 'idle' and d['tui_detected']" "$status"
    grep -Fq "$expected" <<<"$(run_runner capture --repo "$repo" --session "$session" --lines 18)" || \
      fail "${label}_surface" "expected gate evidence missing"
    gate_observe="$(run_runner observe --repo "$repo" --session "$session")"
    gate_snapshot="$(JSON_INPUT="$gate_observe" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['snapshot_id'])")"
    # Approval/trust is evidence for the controlling agent; no generic send is
    # attempted and force-stop uses exact identity without a snapshot gate.
    run_runner stop --repo "$repo" --session "$session" --force >/dev/null 2>&1 || \
      fail "${label}_force_stop" "force stop failed"
  fi
}

gate_case approval "$approval_fake" 'Do you want to proceed?' test_claude_native_approval
gate_case trust "$trust_fake" 'Trust this folder?' test_claude_native_trust

if [[ "$failures" -gt 0 ]]; then
  printf 'Claude human-decision acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Claude human-decision acceptance: PASS\n'
