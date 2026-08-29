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
  sent="$(run_runner grok send --repo "$repo" --session "$session" --text "$literal")"
  json_assert "test_send_accepts_idle_literal" "d['result'] == 'sent'" "$sent"
  sleep 1
  capture="$(run_runner grok capture --repo "$repo" --session "$session" --lines 80)"
  grep -Fq "ECHO:$literal" <<<"$capture" || fail "test_send_accepts_idle_literal" "literal prompt did not reach runtime"
  [[ ! -e "$repo/SHOULD_NOT_EXIST" && ! -e "$repo/ALSO_NOT" ]] || fail "test_prompt_is_not_shell_evaluated" "literal prompt executed shell syntax"

  wrong_repo_output="$(expect_fail "test_wrong_repo_is_rejected" run_runner grok send --repo "$other_repo" --session "$session" --text wrong-repo)"
  grep -Eq 'repo-mismatch|repo_match[^:]*false' <<<"$wrong_repo_output" || fail "test_wrong_repo_is_rejected" "no repository mismatch evidence: $wrong_repo_output"

  wrong_platform_output="$(run_runner claude-code status --repo "$repo" --session "$session")" || fail "test_wrong_platform_is_rejected" "status command failed unexpectedly: $wrong_platform_output"
  json_assert "test_wrong_platform_is_rejected" "d['result'] == 'present' and not d['platform_match'] and d['repo_match']" "$wrong_platform_output"
  capture_before="$(run_runner grok capture --repo "$repo" --session "$session" --lines 20)"
  expect_fail "test_wrong_platform_cannot_inject" run_runner claude-code send --repo "$repo" --session "$session" --text wrong-platform >/dev/null
  capture_after="$(run_runner grok capture --repo "$repo" --session "$session" --lines 20)"
  [[ "$capture_before" == "$capture_after" ]] || fail "test_wrong_platform_cannot_inject" "wrong platform changed target pane"

  "$issue_tmux_bin" split-window -t "=$session:0.0" -c "$repo"
  pane_output="$(expect_fail "test_unexpected_pane_count_is_rejected" run_runner grok send --repo "$repo" --session "$session" --text pane-count)"
  grep -Fq '"pane_count": 2' <<<"$pane_output" || fail "test_unexpected_pane_count_is_rejected" "no pane-count refusal evidence: $pane_output"
  "$issue_tmux_bin" kill-session -t "=$session"

  # A session that happens to run a Grok-looking process but has no Runner
  # markers is unowned and cannot be adopted.
  "$issue_tmux_bin" new-session -d -s "$unowned" -c "$repo" "$fake_grok"
  unowned_status="$(run_runner grok status --repo "$repo" --session "$unowned")"
  json_assert "test_unowned_session_is_reported" "d['result'] == 'present' and not d['owned'] and not d['platform_match']" "$unowned_status"
  expect_fail "test_unowned_session_cannot_receive_input" run_runner grok send --repo "$repo" --session "$unowned" --text adopt
  expect_fail "test_unowned_session_cannot_stop" run_runner grok stop --repo "$repo" --session "$unowned"
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
  waiting_stop="$(expect_fail "test_waiting_human_stop_refuses" run_runner grok stop --repo "$repo" --session "$waiting_human")"
  if "$issue_tmux_bin" has-session -t "=$waiting_human" >/dev/null 2>&1; then
    waiting_after="$(run_runner grok capture --repo "$repo" --session "$waiting_human" --lines 30)"
    [[ "$waiting_before" == "$waiting_after" ]] || \
      fail "test_waiting_human_stop_refuses" "ordinary stop changed waiting-human scrollback"
  else
    fail "test_waiting_human_stop_refuses" "ordinary stop removed waiting-human session: $waiting_stop"
  fi
  run_runner grok stop --repo "$repo" --session "$waiting_human" --force >/dev/null 2>&1 || true
  export FAKE_RUNTIME_STATE=ready
  "$issue_tmux_bin" set-environment -g FAKE_RUNTIME_STATE ready

  run_runner grok start --repo "$repo" --session "$session" >/dev/null
  run_runner grok send --repo "$repo" --session "$session" --text BUSY >/dev/null
  busy_capture=""
  for _ in 1 2 3 4 5; do
    busy_capture="$(run_runner grok capture --repo "$repo" --session "$session" --lines 30 2>/dev/null || true)"
    grep -q 'Waiting for response' <<<"$busy_capture" && break
    sleep 1
  done
  grep -q 'Waiting for response' <<<"$busy_capture" || fail "test_busy_session_is_detected" "busy marker was not observed"
  busy_status="$(run_runner grok status --repo "$repo" --session "$session")"
  json_assert "test_busy_session_is_detected" "d['activity'] == 'busy'" "$busy_status"
  expect_fail "test_busy_session_rejects_input" run_runner grok send --repo "$repo" --session "$session" --text must-wait
  sleep 4
  stopped="$(run_runner grok stop --repo "$repo" --session "$session")"
  json_assert "test_graceful_stop_only_exact_owned_session" "d['result'] == 'stopped' and not d['present']" "$stopped"
  "$issue_tmux_bin" has-session -t "=$unrelated" || fail "test_unrelated_session_survives_graceful_stop" "unrelated session was changed"

  run_runner grok start --repo "$repo" --session "$session" >/dev/null
  force_stopped="$(run_runner grok stop --repo "$repo" --session "$session" --force)"
  json_assert "test_force_stop_is_exact" "d['result'] == 'force-stopped' and not d['present']" "$force_stopped"
  "$issue_tmux_bin" has-session -t "=$unrelated" || fail "test_force_stop_is_exact" "force stop touched unrelated session"
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'kaola tmux acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'kaola tmux acceptance: PASS\n'
