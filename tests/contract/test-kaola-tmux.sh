#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

expect_fail() {
  local label="$1"
  shift
  local output rc
  set +e
  output="$("$@" 2>&1)"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    fail "$label" "expected non-zero exit"
  fi
  printf '%s\n' "$output"
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  JSON_INPUT="$input" python3 -c "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d" || \
    fail "$label" "JSON assertion failed: $input"
}

snapshot_id() {
  JSON_INPUT="$1" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['snapshot_id'])"
}

pane_id() {
  JSON_INPUT="$1" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['hard_evidence']['pane_id'])"
}

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo tmux-repo)"
other_repo="$(issue_new_repo tmux-other-repo)"
IFS=$'\t' read -r fake_grok fake_log < <(issue_make_fake_runtime grok)
IFS=$'\t' read -r fake_claude _ < <(issue_make_fake_runtime claude-code)
session="grok-contract-$$"
unrelated="unrelated-contract-$$"
unowned="unowned-contract-$$"
waiting_human="waiting-human-contract-$$"

export FAKE_RUNTIME_NAME=grok
export FAKE_RUNTIME_LOG="$fake_log"
export GROK_BIN="$fake_grok"
export CLAUDE_BIN="$fake_claude"
export GROK_START_TIMEOUT=5
export KAOLA_START_TIMEOUT=5

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@"
}

if [[ ! -f "$runner" ]]; then
  fail "test_kaola_tmux_entrypoint_exists" "missing $runner"
else
  # A private tmux server is mandatory: this test must never inspect or mutate
  # the user's default server, even when a real session has the same name.
  preflight="$(run_runner grok preflight --repo "$repo" --session "$session")" || fail "test_preflight_reports_capabilities" "preflight failed: $preflight"
  json_assert "test_preflight_reports_capabilities" "d['result'] == 'ready' and d['platform'] == 'grok' and d['workflow_next'] and d['kaola_workflow_finalize'] and d['recurring_execution'] == 'supported'" "$preflight"

  "$issue_tmux_bin" new-session -d -s "$unrelated" -c "$other_repo"
  started="$(run_runner grok start --repo "$repo" --session "$session")" || fail "test_start_creates_owned_session" "start failed: $started"
  json_assert "test_start_creates_owned_session" "d['result'] == 'started' and d['owned'] and d['platform_match'] and d['repo_match'] and d['tui_detected']" "$started"

  canonical_repo="$(cd "$repo" && pwd -P)"
  [[ "$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER 2>/dev/null)" == 'KAOLA_PROJECT_RUNNER=1' ]] || \
    fail "test_session_owner_marker" "missing KAOLA_PROJECT_RUNNER=1"
  [[ "$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER_PLATFORM 2>/dev/null)" == 'KAOLA_PROJECT_RUNNER_PLATFORM=grok' ]] || \
    fail "test_session_platform_marker" "missing grok platform marker"
  [[ "$("$issue_tmux_bin" show-environment -t "=$session" KAOLA_PROJECT_RUNNER_REPO 2>/dev/null)" == "KAOLA_PROJECT_RUNNER_REPO=$canonical_repo" ]] || \
    fail "test_session_repo_marker" "repository marker is not canonical"

  symlink_repo="$issue_tmp_root/tmux-repo-link"
  ln -s "$repo" "$symlink_repo"
  symlink_status="$(run_runner grok status --repo "$symlink_repo" --session "$session")"
  json_assert "test_repo_path_is_canonicalized" "d['repo'] == '$canonical_repo' and d['repo_match'] and d['platform_match']" "$symlink_status"

  status_json="$(run_runner grok status --repo "$repo" --session "$session")"
  json_assert "test_status_reports_idle_single_pane" "d['result'] == 'present' and d['activity'] == 'idle' and d['pane_count'] == 1 and d['tui_detected']" "$status_json"

  literal='literal ; $(touch SHOULD_NOT_EXIST) `touch ALSO_NOT`'
  missing_send="$(expect_fail "test_send_requires_snapshot" run_runner grok send --repo "$repo" --session "$session" --require-empty-editor --text "$literal")"
  grep -Fq '"result": "snapshot-required"' <<<"$missing_send" || fail "test_send_requires_snapshot" "missing snapshot refusal: $missing_send"
  idle_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
  idle_snapshot="$(snapshot_id "$idle_observe")"
  if sent="$(run_runner grok send --repo "$repo" --session "$session" --if-snapshot "$idle_snapshot" --require-empty-editor --text "$literal")"; then
    json_assert "test_send_accepts_idle_literal" "d['result'] == 'sent' and d['action'] == 'send' and d['based_on_snapshot'] == '$idle_snapshot'" "$sent"
    sleep 1
    capture="$(run_runner grok capture --repo "$repo" --session "$session" --lines 80)"
    grep -Fq "ECHO:$literal" <<<"$capture" || fail "test_send_accepts_idle_literal" "literal prompt did not reach runtime"
    [[ ! -e "$repo/SHOULD_NOT_EXIST" && ! -e "$repo/ALSO_NOT" ]] || fail "test_prompt_is_not_shell_evaluated" "literal prompt executed shell syntax"
  else
    fail "test_send_accepts_idle_literal" "tokenized send failed: $sent"
  fi

  post_send_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
  post_send_snapshot="$(snapshot_id "$post_send_observe")"
  wrong_repo_output="$(expect_fail "test_wrong_repo_is_rejected" run_runner grok send --repo "$other_repo" --session "$session" --if-snapshot "$post_send_snapshot" --require-empty-editor --text wrong-repo)"
  grep -Eq 'repo-mismatch|repo_match[^:]*false' <<<"$wrong_repo_output" || fail "test_wrong_repo_is_rejected" "no repository mismatch evidence: $wrong_repo_output"

  wrong_platform_output="$(run_runner claude-code status --repo "$repo" --session "$session")" || fail "test_wrong_platform_is_rejected" "status command failed unexpectedly: $wrong_platform_output"
  json_assert "test_wrong_platform_is_rejected" "d['result'] == 'present' and not d['platform_match'] and d['repo_match']" "$wrong_platform_output"
  capture_before="$(run_runner grok capture --repo "$repo" --session "$session" --lines 20)"
  wrong_platform_observe="$(run_runner claude-code observe --repo "$repo" --session "$session")"
  wrong_platform_snapshot="$(snapshot_id "$wrong_platform_observe")"
  wrong_platform_send="$(expect_fail "test_wrong_platform_cannot_inject" run_runner claude-code send --repo "$repo" --session "$session" --if-snapshot "$wrong_platform_snapshot" --require-empty-editor --text wrong-platform)"
  grep -Eq 'platform-mismatch|platform_match[^:]*false' <<<"$wrong_platform_send" || fail "test_wrong_platform_cannot_inject" "no platform mismatch evidence: $wrong_platform_send"
  capture_after="$(run_runner grok capture --repo "$repo" --session "$session" --lines 20)"
  [[ "$capture_before" == "$capture_after" ]] || fail "test_wrong_platform_cannot_inject" "wrong platform changed target pane"

  idle_pane_id="$(pane_id "$idle_observe")"
  "$issue_tmux_bin" split-window -t "$idle_pane_id" -c "$repo"
  if split_observe="$(run_runner grok observe --repo "$repo" --session "$session" 2>&1)"; then
    json_assert "test_unexpected_pane_count_is_reported" \
      "d['snapshot_id'] is None and d['hard_evidence']['pane_count'] == 2 and 'unexpected-pane-count' in d['guard_failures']" \
      "$split_observe"
    split_token='kpr-snapshot-v2:0000000000000000000000000000000000000000000000000000000000000000'
    pane_output="$(expect_fail "test_unexpected_pane_count_is_rejected" run_runner grok send --repo "$repo" --session "$session" --if-snapshot "$split_token" --require-empty-editor --text pane-count)"
    grep -Fq '"result": "unexpected-pane-count"' <<<"$pane_output" || \
      fail "test_unexpected_pane_count_is_rejected" "missing unexpected-pane-count refusal: $pane_output"
  else
    fail "test_unexpected_pane_count_is_rejected" "observe failed before pane-count refusal: $split_observe"
  fi
  "$issue_tmux_bin" kill-session -t "=$session"

  # A session that happens to run a Grok-looking process but has no Runner
  # markers is unowned and cannot be adopted.
  "$issue_tmux_bin" new-session -d -s "$unowned" -c "$repo" "$fake_grok"
  unowned_status="$(run_runner grok status --repo "$repo" --session "$unowned")"
  json_assert "test_unowned_session_is_reported" "d['result'] == 'present' and not d['owned'] and not d['platform_match']" "$unowned_status"
  unowned_send_missing="$(expect_fail "test_unowned_send_requires_snapshot" run_runner grok send --repo "$repo" --session "$unowned" --require-empty-editor --text adopt)"
  grep -Fq '"result": "snapshot-required"' <<<"$unowned_send_missing" || fail "test_unowned_send_requires_snapshot" "missing snapshot refusal: $unowned_send_missing"
  unowned_observe="$(run_runner grok observe --repo "$repo" --session "$unowned")"
  json_assert "test_unowned_observe_is_reporting_only" "d['result'] == 'observed' and d['relay']['managed'] is False and d['snapshot_id'] is None and 'relay-required' in d['guard_failures']" "$unowned_observe"
  unowned_snapshot='kpr-snapshot-v2:0000000000000000000000000000000000000000000000000000000000000000'
  expect_fail "test_unowned_session_cannot_receive_input" run_runner grok send --repo "$repo" --session "$unowned" --if-snapshot "$unowned_snapshot" --require-empty-editor --text adopt
  unowned_stop_missing="$(expect_fail "test_unowned_stop_requires_snapshot" run_runner grok stop --repo "$repo" --session "$unowned")"
  grep -Fq '"result": "snapshot-required"' <<<"$unowned_stop_missing" || fail "test_unowned_stop_requires_snapshot" "missing snapshot refusal: $unowned_stop_missing"
  expect_fail "test_unowned_session_cannot_stop" run_runner grok stop --repo "$repo" --session "$unowned" --if-snapshot "$unowned_snapshot"
  "$issue_tmux_bin" has-session -t "=$unowned" || fail "test_unowned_session_is_preserved" "unowned session disappeared"
  "$issue_tmux_bin" kill-session -t "=$unowned"

  # A human-decision gate is not an ordinary graceful-stop boundary.  The
  # session and its scrollback must remain available until an explicit force
  # stop, rather than silently answering the runtime's quit prompt.
  export FAKE_RUNTIME_STATE=decision
  # tmux servers snapshot their environment when first created (the earlier
  # unrelated session made that happen before this export), so set the fixture
  # state on the private server explicitly for the new pane.
  "$issue_tmux_bin" set-environment -g FAKE_RUNTIME_STATE decision
  run_runner grok start --repo "$repo" --session "$waiting_human" >/dev/null || \
    fail "test_waiting_human_stop_refuses" "waiting-human start failed"
  waiting_status="$(run_runner grok status --repo "$repo" --session "$waiting_human")"
  json_assert "test_waiting_human_stop_refuses" "d['activity'] == 'waiting-human' and d['tui_detected']" "$waiting_status"
  waiting_before="$(run_runner grok capture --repo "$repo" --session "$waiting_human" --lines 30)"
  waiting_stop_missing="$(expect_fail "test_waiting_human_stop_requires_snapshot" run_runner grok stop --repo "$repo" --session "$waiting_human")"
  grep -Fq '"result": "snapshot-required"' <<<"$waiting_stop_missing" || fail "test_waiting_human_stop_requires_snapshot" "missing snapshot refusal: $waiting_stop_missing"
  waiting_observe="$(run_runner grok observe --repo "$repo" --session "$waiting_human")"
  waiting_snapshot="$(snapshot_id "$waiting_observe")"
  waiting_stop="$(expect_fail "test_waiting_human_stop_refuses" run_runner grok stop --repo "$repo" --session "$waiting_human" --if-snapshot "$waiting_snapshot")"
  if "$issue_tmux_bin" has-session -t "=$waiting_human" >/dev/null 2>&1; then
    waiting_after="$(run_runner grok capture --repo "$repo" --session "$waiting_human" --lines 30)"
    [[ "$waiting_before" == "$waiting_after" ]] || \
      fail "test_waiting_human_stop_refuses" "ordinary stop changed waiting-human scrollback"
  else
    fail "test_waiting_human_stop_refuses" "ordinary stop removed waiting-human session: $waiting_stop"
  fi
  if "$issue_tmux_bin" has-session -t "=$waiting_human" >/dev/null 2>&1; then
    waiting_force_observe="$(run_runner grok observe --repo "$repo" --session "$waiting_human")"
    waiting_force_snapshot="$(snapshot_id "$waiting_force_observe")"
    waiting_force_stop="$(expect_fail "test_waiting_human_force_stop_requires_snapshot" run_runner grok stop --repo "$repo" --session "$waiting_human" --force)"
    grep -Fq '"result": "snapshot-required"' <<<"$waiting_force_stop" || fail "test_waiting_human_force_stop_requires_snapshot" "missing snapshot refusal: $waiting_force_stop"
    if waiting_force_stopped="$(run_runner grok stop --repo "$repo" --session "$waiting_human" --if-snapshot "$waiting_force_snapshot" --force)"; then
      json_assert "test_waiting_human_force_stop" "d['result'] == 'stopped' and d['action'] == 'force-stop' and d['final_state']['session_present'] is False" "$waiting_force_stopped"
    else
      fail "test_waiting_human_force_stop" "force stop failed: $waiting_force_stopped"
    fi
  fi
  export FAKE_RUNTIME_STATE=ready
  "$issue_tmux_bin" set-environment -g FAKE_RUNTIME_STATE ready

  run_runner grok start --repo "$repo" --session "$session" >/dev/null
  ready_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
  ready_snapshot="$(snapshot_id "$ready_observe")"
  if ! run_runner grok send --repo "$repo" --session "$session" --if-snapshot "$ready_snapshot" --require-empty-editor --text BUSY >/dev/null; then
    fail "test_busy_session_starts" "tokenized busy send failed"
  fi
  busy_capture=""
  for _ in 1 2 3 4 5; do
    busy_capture="$(run_runner grok capture --repo "$repo" --session "$session" --lines 30 2>/dev/null || true)"
    grep -q 'Waiting for response' <<<"$busy_capture" && break
    sleep 1
  done
  grep -q 'Waiting for response' <<<"$busy_capture" || fail "test_busy_session_is_detected" "busy marker was not observed"
  busy_status="$(run_runner grok status --repo "$repo" --session "$session")"
  json_assert "test_busy_session_is_detected" "d['activity'] == 'busy'" "$busy_status"
  busy_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
  busy_snapshot="$(snapshot_id "$busy_observe")"
  expect_fail "test_busy_session_rejects_input" run_runner grok send --repo "$repo" --session "$session" --if-snapshot "$busy_snapshot" --require-empty-editor --text must-wait
  sleep 4
  stopped_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
  stopped_snapshot="$(snapshot_id "$stopped_observe")"
  if stopped="$(run_runner grok stop --repo "$repo" --session "$session" --if-snapshot "$stopped_snapshot")"; then
    json_assert "test_graceful_stop_only_exact_owned_session" "d['result'] == 'stopped' and d['action'] == 'stop'" "$stopped"
  else
    fail "test_graceful_stop_only_exact_owned_session" "tokenized stop failed: $stopped"
    cleanup_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
    cleanup_snapshot="$(snapshot_id "$cleanup_observe")"
    run_runner grok stop --repo "$repo" --session "$session" --if-snapshot "$cleanup_snapshot" --force >/dev/null 2>&1 || true
  fi
  "$issue_tmux_bin" has-session -t "=$unrelated" || fail "test_unrelated_session_survives_graceful_stop" "unrelated session was changed"

  run_runner grok start --repo "$repo" --session "$session" >/dev/null
  force_observe="$(run_runner grok observe --repo "$repo" --session "$session")"
  force_snapshot="$(snapshot_id "$force_observe")"
  force_child_pid="$(JSON_INPUT="$force_observe" python3 -c 'import json,os; print(json.loads(os.environ["JSON_INPUT"])["relay"]["child_pid"])')"
  force_child_pgid="$(JSON_INPUT="$force_observe" python3 -c 'import json,os; print(json.loads(os.environ["JSON_INPUT"])["relay"]["child_pgid"])')"
  force_socket="$(JSON_INPUT="$force_observe" python3 -c 'import json,os; print(json.loads(os.environ["JSON_INPUT"])["relay"]["socket_path"])')"
  force_missing="$(expect_fail "test_force_stop_requires_snapshot" run_runner grok stop --repo "$repo" --session "$session" --force)"
  grep -Fq '"result": "snapshot-required"' <<<"$force_missing" || fail "test_force_stop_requires_snapshot" "missing snapshot refusal: $force_missing"
  force_stopped="$(run_runner grok stop --repo "$repo" --session "$session" --if-snapshot "$force_snapshot" --force)"
  json_assert "test_force_stop_is_exact" "d['result'] == 'stopped' and d['action'] == 'force-stop' and d['final_state'] == {'session_present':False,'child_running':False,'child_group_running':False,'socket_present':False,'pane_input_off':None}" "$force_stopped"
  [[ ! -e "$force_socket" ]] || fail "test_force_stop_is_exact" "relay socket remains after stopped receipt: $force_socket"
  ps -p "$force_child_pid" -o pid= 2>/dev/null | grep -q '[0-9]' && \
    fail "test_force_stop_is_exact" "runtime child remains after stopped receipt: $force_child_pid"
  ps -axo pgid= 2>/dev/null | awk -v pgid="$force_child_pgid" '$1 == pgid { found=1 } END { exit !found }' && \
    fail "test_force_stop_is_exact" "runtime child group remains after stopped receipt: $force_child_pgid"
  "$issue_tmux_bin" has-session -t "=$unrelated" || fail "test_force_stop_is_exact" "force stop touched unrelated session"
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'kaola tmux acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'kaola tmux acceptance: PASS\n'
