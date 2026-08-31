#!/usr/bin/env bash
set -u -o pipefail

# Issue #6 public compare-and-act acceptance.  All answer/send/stop operations
# go through kaola-tmux.sh; the tmux shim is used only to isolate the server
# and inspect state, never to answer the Claude editor directly.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
raw_tui="$project_root/tests/fixtures/observations/claude-code/raw-mode-tui.py"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
COMMAND_OUTPUT=''
COMMAND_RC=0
answer_result=''
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@"
}

capture_command() {
  local output rc
  set +e
  output="$(run_runner "$@" 2>&1)"
  rc=$?
  COMMAND_OUTPUT="$output"
  COMMAND_RC=$rc
  return "$rc"
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  JSON_INPUT="$input" python3 -c \
    "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d" || \
    fail "$label" "JSON assertion failed: $input"
}

json_value() {
  local input="$1" expression="$2"
  JSON_INPUT="$input" python3 -c "import json, os; d=json.loads(os.environ['JSON_INPUT']); print($expression)"
}

expect_refusal() {
  local label="$1" expected="$2"
  if [[ "$COMMAND_RC" -eq 0 ]]; then
    fail "$label" "expected non-zero exit; output: $COMMAND_OUTPUT"
  fi
  grep -Fq "$expected" <<<"$COMMAND_OUTPUT" || \
    fail "$label" "expected $expected; output: $COMMAND_OUTPUT"
}

issue_setup
trap issue_cleanup EXIT

if [[ ! -f "$runner" ]]; then
  fail test_issue6_runner_exists "missing $runner"
fi
if [[ ! -f "$raw_tui" ]]; then
  fail test_issue6_raw_mode_fixture_exists "missing $raw_tui"
fi

repo="$(issue_new_repo issue6-claude-answer)"
mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"

chmod +x "$raw_tui"
submit_log="$issue_tmp_root/claude-submissions.log"
release_file="$issue_tmp_root/release-later-output"
editor_change_file="$issue_tmp_root/editor-change"
grid_neutral_file="$issue_tmp_root/grid-neutral-output"
: >"$submit_log"
export CLAUDE_BIN="$raw_tui"
export FAKE_CLAUDE_SUBMIT_LOG="$submit_log"
export FAKE_CLAUDE_RELEASE="$release_file"
export FAKE_CLAUDE_EDITOR_CHANGE="$editor_change_file"
export FAKE_CLAUDE_GRID_NEUTRAL="$grid_neutral_file"
export KAOLA_START_TIMEOUT=5

session="issue6-claude-answer-$$"
if capture_command claude-code start --repo "$repo" --session "$session"; then
  json_assert test_issue6_start "d['result'] == 'started' and d['owned'] and d['platform_match'] and d['repo_match']" "$COMMAND_OUTPUT"
else
  fail test_issue6_start "public start failed: $COMMAND_OUTPUT"
fi

if "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1; then
  # Observe is the only source of a mutation token. The exact schema assertion
  # rejects legacy flattened status and accidental relay fields.
  if capture_command claude-code observe --repo "$repo" --session "$session"; then
    observe_before="$COMMAND_OUTPUT"
    json_assert test_issue6_observe_schema \
      "set(d) == {'schema_version','result','platform','runtime','session','repo','snapshot_id','pane_revision','raw_current_frame','editor_state','editor_fingerprint','hard_evidence','relay','child_processes','child_process_count','visible_shell_count','visible_agent_count','native_approval','structured_decision_marker','later_output_barrier','activity_hint','runtime_session_id','git','evidence_flags','model'} and d['schema_version'] == 2 and d['result'] == 'observed' and d['platform'] == 'claude-code' and d['relay']['managed'] is True and d['model']['requested_model_source'] == 'runner-default'" \
      "$observe_before"
    json_assert test_issue6_observe_hard_evidence \
      "set(d['hard_evidence']) == {'present','owned','platform_match','repo_match','pane_count','pane_id','pane_dead','pane_input_off','pane_path','pane_pid','pane_command','pane_title','pane_process','relay_process_match','process_match','tui_detected','pane_width','pane_height','cursor_x','cursor_y','cursor_flag','alternate_on','history_size','history_bytes'} and d['hard_evidence']['pane_count'] == 1 and d['hard_evidence']['pane_id'].startswith('%') and d['hard_evidence']['relay_process_match'] is True" \
      "$observe_before"
    json_assert test_issue6_observe_relay_attestation \
      "set(d['relay']) == {'managed','protocol_version','epoch','pid','start_fingerprint','socket_path','socket_owner_uid','socket_mode','peer_pid_verified','state','child_pid','child_pgid','child_start_fingerprint','child_runtime_path','child_process','child_process_state','child_process_match','process_group_running','lease_active','child_input_offset','child_output_offset','child_output_digest','resize_revision','bracketed_paste','terminal_fence'} and d['relay']['managed'] is True and d['relay']['pid'] == d['hard_evidence']['pane_pid'] and d['relay']['child_pid'] != d['relay']['pid'] and d['relay']['child_pgid'] == d['relay']['child_pid'] and d['relay']['socket_mode'] == '0600' and d['relay']['terminal_fence'] == 'decrqm-nonce-v1'" \
      "$observe_before"
    json_assert test_issue6_observe_advisory_surface \
      "d['editor_state'] in ('empty','nonempty','unknown') and d['structured_decision_marker'] is not None and d['later_output_barrier'] is None" \
      "$observe_before"

    if capture_command claude-code status --repo "$repo" --session "$session"; then
      json_assert test_issue6_status_activity_is_advisory_alias \
        "d['activity'] == d['activity_hint'] and d['activity_hint'] in ('busy','waiting-human','idle','unknown')" \
        "$COMMAND_OUTPUT"
    else
      fail test_issue6_status_activity_is_advisory_alias "status failed: $COMMAND_OUTPUT"
    fi

    snapshot_before="$(json_value "$observe_before" "d['snapshot_id']")"
    pane_before="$(json_value "$observe_before" "d['pane_revision']")"
    decision_id="$(json_value "$observe_before" "d['structured_decision_marker']['decision_id']")"
    [[ "$snapshot_before" == kpr-snapshot-v2:* ]] || fail test_issue6_snapshot_is_opaque "invalid snapshot: $snapshot_before"
    [[ "$pane_before" == kpr-pane-v2:* ]] || fail test_issue6_pane_revision_is_opaque "invalid pane revision: $pane_before"
    [[ "$decision_id" == kpr-decision-v1:* ]] || fail test_issue6_decision_id_is_opaque "invalid decision id: $decision_id"

    sleep 0.1
    export BASE_OBSERVE="$observe_before"
    if capture_command claude-code observe --repo "$repo" --session "$session"; then
      observe_repeat="$COMMAND_OUTPUT"
      json_assert test_issue6_unchanged_observe_is_stable \
        "d['snapshot_id'] == '$snapshot_before' and d['pane_revision'] == '$pane_before' and d['raw_current_frame'] == json.loads(__import__('os').environ['BASE_OBSERVE'])['raw_current_frame']" \
        "$observe_repeat"
    else
      fail test_issue6_unchanged_observe_is_stable "repeat observe failed: $COMMAND_OUTPUT"
    fi

    # The controlling agent owns the choice not to send/stop on this retained
    # decision draft. Generic snapshot identifiers are audit correlation, not
    # required acknowledgements or semantic mutation gates.
    [[ ! -s "$submit_log" ]] || fail test_issue6_guards_do_not_submit "$submit_log changed before answer: $(cat "$submit_log")"

    # The completed-empty frame is the one ordinary send may accept.  Include
    # shell metacharacters in a literal payload and verify that no command is
    # evaluated by a shell on the way to the raw-mode TUI.
    empty_log="$issue_tmp_root/claude-empty-submissions.log"
    : >"$empty_log"
    export FAKE_CLAUDE_MODE=empty FAKE_CLAUDE_SUBMIT_LOG="$empty_log" FAKE_CLAUDE_REDRAW_ON_CONT=1
    empty_session="issue6-claude-empty-$$"
    if capture_command claude-code start --repo "$repo" --session "$empty_session"; then
      if capture_command claude-code observe --repo "$repo" --session "$empty_session"; then
        empty_observe="$COMMAND_OUTPUT"
        json_assert test_issue6_completed_surface_observation \
          "d['raw_current_frame'] and d['native_approval']['state'] == 'absent' and d['structured_decision_marker'] is None and d['later_output_barrier'] is None" \
          "$empty_observe"
        empty_snapshot="$(json_value "$empty_observe" "d['snapshot_id']")"
        literal='literal ; $(touch issue6-no-side-effect) `touch issue6-no-side-effect-too`'
        capture_command claude-code send --repo "$repo" --session "$empty_session" --if-snapshot "$empty_snapshot" --text "$literal"
        if [[ "$COMMAND_RC" -ne 0 ]]; then
          fail test_issue6_completed_empty_accepts_literal "send failed: $COMMAND_OUTPUT"
        else
          json_assert test_issue6_completed_empty_accepts_literal "d['result'] == 'sent'" "$COMMAND_OUTPUT"
          grep -Fxq "submitted=$literal" "$empty_log" || fail test_issue6_completed_empty_accepts_literal "literal did not arrive exactly once: $(cat "$empty_log")"
          [[ ! -e "$repo/issue6-no-side-effect" && ! -e "$repo/issue6-no-side-effect-too" ]] || \
            fail test_issue6_literal_not_shell_evaluated "literal payload executed shell syntax"
        fi
      else
        fail test_issue6_completed_empty_observation "observe failed: $COMMAND_OUTPUT"
      fi
    else
      fail test_issue6_completed_empty_start "start failed: $COMMAND_OUTPUT"
    fi
    "$issue_tmux_bin" kill-session -t "=$empty_session" >/dev/null 2>&1 || true
    unset FAKE_CLAUDE_REDRAW_ON_CONT

    export FAKE_CLAUDE_MODE=decision FAKE_CLAUDE_SUBMIT_LOG="$submit_log"

    # A visible editor/frame change invalidates the old token before any
    # action-specific editor guard.  The raw TUI emits a changed current grid
    # after this flag is created; no tmux send-keys is used here.
    touch "$editor_change_file"
    changed_observe=''
    changed_ready=false
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      if capture_command claude-code observe --repo "$repo" --session "$session"; then
        changed_observe="$COMMAND_OUTPUT"
        if grep -Fq 'changed-draft' <<<"$changed_observe"; then
          changed_ready=true
          break
        fi
      fi
      sleep 0.1
    done
    [[ "$changed_ready" == true ]] || fail test_issue6_editor_change_observed "changed editor frame was not observed: $changed_observe"
    changed_snapshot="$(json_value "$changed_observe" "d['snapshot_id']")"
    [[ "$changed_snapshot" != "$snapshot_before" ]] || fail test_issue6_editor_change_changes_snapshot "editor change reused old snapshot"

    # The decision identifier is receipt correlation evidence, not mutation
    # authority. Whole-editor replacement remains an explicit mechanical
    # capability because appending to the retained draft would not transfer
    # the agent-selected literal answer.
    capture_command claude-code answer --repo "$repo" --session "$session" --if-snapshot "$changed_snapshot" --text chosen-answer
    [[ "$COMMAND_RC" -ne 0 ]] || fail test_issue6_answer_requires_replace_authorization "answer without --replace-editor succeeded"
    [[ ! -s "$submit_log" ]] || fail test_issue6_missing_replace_preserves_draft "missing replace authorization submitted: $(cat "$submit_log")"

    capture_command claude-code answer --repo "$repo" --session "$session" --if-snapshot "$changed_snapshot" --replace-editor --text chosen-answer
    if [[ "$COMMAND_RC" -ne 0 ]]; then
      fail test_issue6_answer_replaces_editor "public answer failed: $COMMAND_OUTPUT"
    else
      answer_result="$COMMAND_OUTPUT"
      canonical_repo="$(cd "$repo" && pwd -P)"
      json_assert test_issue6_answer_receipt \
        "d['schema_version'] == 2 and d['result'] == 'answer-sent' and d['action'] == 'answer' and d['platform'] == 'claude-code' and d['session'] == '$session' and d['repo'] == '$canonical_repo' and d['decision_id'] == '' and d['based_on_snapshot'] == '$changed_snapshot' and d['mutation_performed'] is True and d['clear_editor'] is True and d['payload_fingerprint'].startswith('sha256:') and 'receipt_id' not in d and 'restoration_evidence' not in d" \
        "$answer_result"
      grep -Fxq 'submitted=chosen-answer' "$submit_log" || \
        fail test_issue6_answer_replaces_editor "raw-mode receipt did not contain exactly chosen-answer: $(cat "$submit_log")"
      if grep -Fq 'submitted=draft-prefixchosen-answer' "$submit_log"; then
        fail test_issue6_answer_replaces_editor "answer appended to draft: $(cat "$submit_log")"
      fi
    fi

    touch "$release_file"
    satisfied_observe=''
    satisfied_ready=false
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
      if capture_command claude-code observe --repo "$repo" --session "$session"; then
        satisfied_observe="$COMMAND_OUTPUT"
        if grep -Fq 'Later output line' <<<"$satisfied_observe"; then
          satisfied_ready=true
          break
        fi
      fi
      sleep 0.1
    done
    [[ "$satisfied_ready" == true ]] || fail test_issue6_later_output_observed "later output was not observed: $satisfied_observe"
    json_assert test_issue6_later_output_observation \
      "d['later_output_barrier'] is None and d['editor_state'] == 'empty' and d['visible_shell_count'] == 0 and d['visible_agent_count'] == 0" \
      "$satisfied_observe"
    satisfied_snapshot="$(json_value "$satisfied_observe" "d['snapshot_id']")"
    capture_command claude-code send --repo "$repo" --session "$session" --if-snapshot "$satisfied_snapshot" --text follow-up
    if [[ "$COMMAND_RC" -ne 0 ]]; then
      fail test_issue6_follow_up_after_barrier "fresh guarded send failed: $COMMAND_OUTPUT"
    else
      json_assert test_issue6_follow_up_after_barrier "d['result'] == 'sent' and d['platform'] == 'claude-code'" "$COMMAND_OUTPUT"
      grep -Fxq 'submitted=follow-up' "$submit_log" || fail test_issue6_follow_up_after_barrier "follow-up did not reach raw TUI: $(cat "$submit_log")"
    fi

    # Force stop requires exact identity but no visual snapshot gate.
    if capture_command claude-code observe --repo "$repo" --session "$session"; then
      capture_command claude-code stop --repo "$repo" --session "$session" --force
      if [[ "$COMMAND_RC" -ne 0 ]]; then
        fail test_issue6_force_stop_requires_exact_identity "force stop failed: $COMMAND_OUTPUT"
      else
        json_assert test_issue6_force_stop_requires_exact_identity "d['result'] == 'stopped' and d['action'] == 'force-stop' and d['final_state']['session_present'] is False and d['final_state']['relay_running'] is False and d['final_state']['socket_present'] is False" "$COMMAND_OUTPUT"
        if capture_command claude-code observe --repo "$repo" --session "$session"; then
          json_assert test_issue6_absent_observation_schema \
            "d['result'] == 'absent' and d['snapshot_id'] is None and d['pane_revision'] is None and d['raw_current_frame'] == '' and d['editor_state'] == 'unknown' and d['child_processes'] is None and d['child_process_count'] is None and 'session-absent' in d['evidence_flags']" \
            "$COMMAND_OUTPUT"
        else
          fail test_issue6_absent_observation_schema "observe on absent session failed: $COMMAND_OUTPUT"
        fi
      fi
    fi
  else
    fail test_issue6_observe_public_command "observe failed: $COMMAND_OUTPUT"
    "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
  fi
fi

# Public answer exists for every adapter, but only Claude has the reviewed
# replacement sequence in v1.  Exercise the unsupported result through the
# Grok wrapper's public observe/answer calls rather than a private adapter hook.
grok_repo="$(issue_new_repo issue6-grok-unsupported)"
IFS=$'\t' read -r fake_grok fake_grok_log < <(issue_make_fake_runtime grok)
export FAKE_RUNTIME_NAME=grok FAKE_RUNTIME_LOG="$fake_grok_log" FAKE_RUNTIME_SESSION_ID=grok-issue6-fixture GROK_BIN="$fake_grok"
grok_session="issue6-grok-unsupported-$$"
if capture_command grok start --repo "$grok_repo" --session "$grok_session"; then
  if capture_command grok observe --repo "$grok_repo" --session "$grok_session"; then
    grok_snapshot="$(json_value "$COMMAND_OUTPUT" "d['snapshot_id']")"
    capture_command grok answer --repo "$grok_repo" --session "$grok_session" --decision-id "kpr-decision-v1:$(printf '%064d' 1)" --if-snapshot "$grok_snapshot" --replace-editor --text should-not-send
    expect_refusal test_issue6_grok_answer_unsupported 'answer-unsupported'
  else
    fail test_issue6_grok_observe_for_unsupported "observe failed: $COMMAND_OUTPUT"
  fi
else
  fail test_issue6_grok_start_for_unsupported "start failed: $COMMAND_OUTPUT"
fi
"$issue_tmux_bin" kill-session -t "=$grok_session" >/dev/null 2>&1 || true

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #6 guarded-action acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #6 guarded-action acceptance: PASS\n'
