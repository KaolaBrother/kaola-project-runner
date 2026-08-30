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
      "set(d) == {'schema_version','result','platform','runtime','session','repo','snapshot_id','pane_revision','raw_current_frame','editor_state','editor_fingerprint','hard_evidence','relay','child_processes','child_process_count','visible_shell_count','visible_agent_count','native_approval','structured_decision_marker','later_output_barrier','activity_hint','runtime_session_id','git','evidence_flags'} and d['schema_version'] == 2 and d['result'] == 'observed' and d['platform'] == 'claude-code' and d['relay']['managed'] is True" \
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
        empty_pane_revision="$(json_value "$empty_observe" "d['pane_revision']")"
        equivalent_redraw_observe=''
        equivalent_redraw_ready=false
        for _ in 1 2 3 4 5 6 7 8 9 10; do
          if capture_command claude-code observe --repo "$repo" --session "$empty_session"; then
            equivalent_redraw_observe="$COMMAND_OUTPUT"
            redraw_snapshot="$(json_value "$equivalent_redraw_observe" "d['snapshot_id']")"
            redraw_pane_revision="$(json_value "$equivalent_redraw_observe" "d['pane_revision']")"
            if [[ "$redraw_snapshot" == "$empty_snapshot" && "$redraw_pane_revision" != "$empty_pane_revision" ]]; then
              equivalent_redraw_ready=true
              break
            fi
          fi
          sleep 0.1
        done
        [[ "$equivalent_redraw_ready" == true ]] || fail test_issue6_equivalent_redraw_snapshot_stability "equivalent redraw did not preserve snapshot while advancing pane revision: $equivalent_redraw_observe"
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

    # A prepare-time foreign-byte change is distinct from a native approval.
    # The payload has already crossed the relay when this drift appears, so
    # Enter would submit bytes outside the attested payload. Refusal is based
    # on changed factual prepared surface/receipt evidence, not an editor label.
    prepare_editor_log="$issue_tmp_root/claude-prepare-send-editor-drift.log"
    : >"$prepare_editor_log"
    export FAKE_CLAUDE_MODE=empty
    export FAKE_CLAUDE_SUBMIT_LOG="$prepare_editor_log"
    export FAKE_CLAUDE_PREPARE_DRIFT=editor-change
    prepare_editor_session="issue6-claude-prepare-send-editor-drift-$$"
    if capture_command claude-code start --repo "$repo" --session "$prepare_editor_session"; then
      if capture_command claude-code observe --repo "$repo" --session "$prepare_editor_session"; then
        prepare_editor_snapshot="$(json_value "$COMMAND_OUTPUT" "d['snapshot_id']")"
        capture_command claude-code send --repo "$repo" --session "$prepare_editor_session" \
          --if-snapshot "$prepare_editor_snapshot" --text drift-send
        [[ "$COMMAND_RC" -ne 0 ]] || \
          fail test_issue6_send_refuses_prepare_time_editor_change "send succeeded after foreign bytes changed the prepared editor: $COMMAND_OUTPUT"
        grep -Fq '"result": "refused"' <<<"$COMMAND_OUTPUT" || \
          fail test_issue6_send_refuses_prepare_time_editor_change "expected a public refusal receipt: $COMMAND_OUTPUT"
        [[ ! -s "$prepare_editor_log" ]] || \
          fail test_issue6_send_does_not_submit_prepare_time_editor_change "guarded send pressed Enter on the changed editor: $(cat "$prepare_editor_log")"
        "$issue_tmux_bin" has-session -t "=$prepare_editor_session" >/dev/null 2>&1 || \
          fail test_issue6_send_preserves_session_after_prepare_time_editor_change "refused send removed the managed session"
      else
        fail test_issue6_send_prepare_time_editor_change_observe "observe failed: $COMMAND_OUTPUT"
      fi
    else
      fail test_issue6_send_prepare_time_editor_change_start "start failed: $COMMAND_OUTPUT"
    fi
    "$issue_tmux_bin" kill-session -t "=$prepare_editor_session" >/dev/null 2>&1 || true

    # The same prepared-payload identity rule applies to bracketed multiline
    # input. Enter must never submit the two attested lines plus a foreign
    # suffix, irrespective of any inferred editor state.
    prepare_multiline_log="$issue_tmp_root/claude-prepare-send-multiline-editor-drift.log"
    : >"$prepare_multiline_log"
    export FAKE_CLAUDE_MODE=empty
    export FAKE_CLAUDE_SUBMIT_LOG="$prepare_multiline_log"
    export FAKE_CLAUDE_PREPARE_DRIFT=editor-change
    prepare_multiline_session="issue6-claude-prepare-send-multiline-editor-drift-$$"
    if capture_command claude-code start --repo "$repo" --session "$prepare_multiline_session"; then
      if capture_command claude-code observe --repo "$repo" --session "$prepare_multiline_session"; then
        prepare_multiline_snapshot="$(json_value "$COMMAND_OUTPUT" "d['snapshot_id']")"
        multiline_drift_payload=$'drift\nsend'
        capture_command claude-code send --repo "$repo" --session "$prepare_multiline_session" \
          --if-snapshot "$prepare_multiline_snapshot" --text "$multiline_drift_payload"
        [[ "$COMMAND_RC" -ne 0 ]] || \
          fail test_issue6_multiline_send_refuses_prepare_time_editor_change "multiline send succeeded after foreign bytes changed the prepared editor: $COMMAND_OUTPUT"
        grep -Fq '"result": "refused"' <<<"$COMMAND_OUTPUT" || \
          fail test_issue6_multiline_send_refuses_prepare_time_editor_change "expected a public refusal receipt: $COMMAND_OUTPUT"
        [[ ! -s "$prepare_multiline_log" ]] || \
          fail test_issue6_multiline_send_does_not_submit_prepare_time_editor_change "guarded multiline send pressed Enter on the changed editor: $(python3 -c 'import pathlib,sys; print(repr(pathlib.Path(sys.argv[1]).read_text()))' "$prepare_multiline_log")"
        "$issue_tmux_bin" has-session -t "=$prepare_multiline_session" >/dev/null 2>&1 || \
          fail test_issue6_multiline_send_preserves_session_after_prepare_time_editor_change "refused multiline send removed the managed session"
      else
        fail test_issue6_multiline_send_prepare_time_editor_change_observe "observe failed: $COMMAND_OUTPUT"
      fi
    else
      fail test_issue6_multiline_send_prepare_time_editor_change_start "start failed: $COMMAND_OUTPUT"
    fi
    "$issue_tmux_bin" kill-session -t "=$prepare_multiline_session" >/dev/null 2>&1 || true

    # Ordinary stop has the same prepare/submit split. If unrelated editor
    # bytes appear while /exit is being prepared, stop must refuse before the
    # carriage return. EXIT_ON_SUBMIT makes the current blind-submit near miss
    # terminate immediately, keeping this regression deterministic and fast.
    prepare_stop_log="$issue_tmp_root/claude-prepare-stop-drift.log"
    : >"$prepare_stop_log"
    export FAKE_CLAUDE_SUBMIT_LOG="$prepare_stop_log"
    export FAKE_CLAUDE_PREPARE_DRIFT=editor-change
    export FAKE_CLAUDE_EXIT_ON_SUBMIT=1
    prepare_stop_session="issue6-claude-prepare-stop-drift-$$"
    if capture_command claude-code start --repo "$repo" --session "$prepare_stop_session"; then
      if capture_command claude-code observe --repo "$repo" --session "$prepare_stop_session"; then
        prepare_stop_snapshot="$(json_value "$COMMAND_OUTPUT" "d['snapshot_id']")"
        capture_command claude-code stop --repo "$repo" --session "$prepare_stop_session" \
          --if-snapshot "$prepare_stop_snapshot"
        [[ "$COMMAND_RC" -ne 0 ]] || \
          fail test_issue6_stop_refuses_prepare_time_editor_change "stop succeeded after unrelated bytes changed the prepared editor: $COMMAND_OUTPUT"
        grep -Fq '"result": "refused"' <<<"$COMMAND_OUTPUT" || \
          fail test_issue6_stop_refuses_prepare_time_editor_change "expected a public refusal receipt: $COMMAND_OUTPUT"
        [[ ! -s "$prepare_stop_log" ]] || \
          fail test_issue6_stop_does_not_submit_after_prepare_time_editor_change "ordinary stop submitted the changed editor: $(cat "$prepare_stop_log")"
        "$issue_tmux_bin" has-session -t "=$prepare_stop_session" >/dev/null 2>&1 || \
          fail test_issue6_stop_preserves_session_after_prepare_time_editor_change "refused ordinary stop removed the managed session"
      else
        fail test_issue6_stop_prepare_time_editor_change_observe "observe failed: $COMMAND_OUTPUT"
      fi
    else
      fail test_issue6_stop_prepare_time_editor_change_start "start failed: $COMMAND_OUTPUT"
    fi
    "$issue_tmux_bin" kill-session -t "=$prepare_stop_session" >/dev/null 2>&1 || true
    unset FAKE_CLAUDE_PREPARE_DRIFT FAKE_CLAUDE_EXIT_ON_SUBMIT
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
      json_assert test_issue6_answer_receipt \
        "d['schema_version'] == 2 and d['result'] == 'answer-sent' and d['action'] == 'answer' and d['platform'] == 'claude-code' and d['session'] == '$session' and d['repo'] == '$repo' and d['decision_id'] == '' and d['based_on_snapshot'] == '$changed_snapshot' and d['later_output_barrier'] == 'pending' and d['receipt_id'].startswith('kpr-answer-v2:') and d['prepared_pane_revision'].startswith('kpr-pane-v2:') and d['relay_epoch'] and d['child_start_fingerprint'].startswith('sha256:') and d['replaced_editor_fingerprint'].startswith('sha256:') and d['answer_fingerprint'].startswith('sha256:') and 'chosen-answer' not in json.dumps(d) and 'draft-prefix' not in json.dumps(d)" \
        "$answer_result"
      answer_receipt="$(json_value "$answer_result" "d['receipt_id']")"
      barrier_receipt_line="$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER_BARRIER_RECEIPT 2>/dev/null || true)"
      barrier_revision_line="$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER_BARRIER_PANE_REVISION 2>/dev/null || true)"
      [[ -z "$barrier_receipt_line" && -z "$barrier_revision_line" ]] || \
        fail test_issue6_answer_does_not_persist_barrier_secrets "barrier receipt/revision leaked into tmux environment: $barrier_receipt_line $barrier_revision_line"
      grep -Fxq 'submitted=chosen-answer' "$submit_log" || \
        fail test_issue6_answer_replaces_editor "raw-mode receipt did not contain exactly chosen-answer: $(cat "$submit_log")"
      if grep -Fq 'submitted=draft-prefixchosen-answer' "$submit_log"; then
        fail test_issue6_answer_replaces_editor "answer appended to draft: $(cat "$submit_log")"
      fi
    fi

    # The immediate frame has not changed, so the answer installs a pending
    # barrier. A grid-neutral child byte advances the relay output digest and
    # enters output-seen, but does not satisfy the later-output barrier until
    # a later fenced frame differs.
    export ANSWER_RESULT="$answer_result"
    if capture_command claude-code observe --repo "$repo" --session "$session"; then
      pending_observe="$COMMAND_OUTPUT"
      json_assert test_issue6_later_output_barrier_pending \
        "d['later_output_barrier'] is not None and d['later_output_barrier']['state'] == 'pending' and d['later_output_barrier']['receipt_id'] == json.loads(__import__('os').environ['ANSWER_RESULT'])['receipt_id']" \
        "$pending_observe"
      touch "$grid_neutral_file"
      output_seen_observe=''
      output_seen_ready=false
      for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
        if capture_command claude-code observe --repo "$repo" --session "$session"; then
          output_seen_observe="$COMMAND_OUTPUT"
          if grep -Fq '"state": "output-seen"' <<<"$output_seen_observe"; then
            output_seen_ready=true
            break
          fi
        fi
        sleep 0.1
      done
      [[ "$output_seen_ready" == true ]] || fail test_issue6_grid_neutral_output_seen "grid-neutral child output did not enter output-seen: $output_seen_observe"
      if [[ "$output_seen_ready" == true ]]; then
        json_assert test_issue6_grid_neutral_output_seen \
          "d['later_output_barrier']['state'] == 'output-seen' and d['later_output_barrier']['receipt_id'] == json.loads(__import__('os').environ['ANSWER_RESULT'])['receipt_id']" \
          "$output_seen_observe"
      fi
    else
      fail test_issue6_later_output_barrier_pending "observe after answer failed: $COMMAND_OUTPUT"
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
    json_assert test_issue6_later_output_barrier_satisfied \
      "d['later_output_barrier'] is not None and d['later_output_barrier']['state'] == 'satisfied' and d['editor_state'] == 'empty' and d['visible_shell_count'] == 0 and d['visible_agent_count'] == 0" \
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
        json_assert test_issue6_force_stop_requires_exact_identity "d['result'] == 'stopped' and d['action'] == 'force-stop' and d['final_state'] == {'session_present': False, 'child_running': False, 'child_group_running': False, 'socket_present': False, 'pane_input_off': None}" "$COMMAND_OUTPUT"
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
