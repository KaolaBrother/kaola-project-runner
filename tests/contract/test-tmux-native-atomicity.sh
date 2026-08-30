#!/usr/bin/env bash
set -u -o pipefail

# Issue #6 negative proof and migration boundary. This test deliberately uses
# tmux only to create/inspect an isolated pane; all guarded actions below go
# through the public Runner command.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
direct_fixture="$project_root/tests/fixtures/relay/direct-pane-leader.py"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
COMMAND_OUTPUT=''
COMMAND_RC=0

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
  set -e
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
if [[ ! -f "$direct_fixture" ]]; then
  fail test_issue6_direct_fixture_exists "missing $direct_fixture"
fi

direct_repo="$(issue_new_repo issue6-direct-native)"
native_state="$issue_tmp_root/native-pane.state"
native_session="issue6-direct-native-$$"

# A direct pane leader is the exact candidate rejected by the relay design.
# tmux's server_child_stopped path immediately continues this process/group.
"$issue_tmux_bin" new-session -d -s "$native_session" -c "$direct_repo" \
  "exec python3 '$direct_fixture' --state '$native_state'" >/dev/null 2>&1 || \
  fail test_issue6_native_fixture_start "could not create isolated direct pane"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  grep -Fq 'ready' "$native_state" 2>/dev/null && break
  sleep 0.1
done
native_pane="$("$issue_tmux_bin" list-panes -t "=$native_session" -F '#{pane_id}' 2>/dev/null | awk 'NF {print; exit}')"
native_pid="$("$issue_tmux_bin" display-message -p -t "$native_pane" '#{pane_pid}' 2>/dev/null || true)"
if [[ ! "$native_pid" =~ ^[0-9]+$ ]]; then
  fail test_issue6_native_pane_pid "missing direct pane leader pid: $native_pid"
else
  pane_command="$("$issue_tmux_bin" display-message -p -t "$native_pane" '#{pane_current_command}' 2>/dev/null || true)"
  [[ "$pane_command" == *direct-pane-leader* || "$pane_command" == [Pp]ython* ]] || \
    fail test_issue6_native_pane_leader "unexpected direct pane command: $pane_command"
  kill -STOP "$native_pid" 2>/dev/null || fail test_issue6_native_stop_signal "SIGSTOP failed for isolated pane leader"
  resumed=false
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    if grep -Fq 'SIGCONT' "$native_state" 2>/dev/null; then
      resumed=true
      break
    fi
    sleep 0.05
  done
  [[ "$resumed" == true ]] || fail test_issue6_direct_pane_stop_auto_resumes "direct pane leader remained stopped"
  native_state_value="$(ps -o state= -p "$native_pid" 2>/dev/null | awk 'NF {print $1; exit}')"
  [[ "$native_state_value" != T* ]] || fail test_issue6_direct_pane_stop_auto_resumes "direct pane state remained $native_state_value"
fi

# The production path must not retain a direct-runtime freeze or restop
# fallback. A dead helper is still a misleading implementation path because
# a later caller could accidentally make it authoritative again.
if rg -n \
  'kill[[:space:]]+-STOP|OBSERVATION_HELPER.*signal.*:stop|freeze_exact_process_tree|restop_committed_process' \
  "$runner" >/dev/null 2>&1; then
  fail test_issue6_direct_freeze_path_removed "public core still contains a direct process freeze path"
fi

# Older direct sessions are reporting-only. The fixture is intentionally
# marked as owned Claude state so the refusal proves the relay requirement,
# not a generic ownership failure.
legacy_repo="$(issue_new_repo issue6-legacy-direct)"
legacy_repo="$(cd "$legacy_repo" && pwd -P)"
legacy_state="$issue_tmp_root/legacy-pane.state"
legacy_input="$issue_tmp_root/legacy-pane.input"
legacy_session="issue6-legacy-direct-$$"
python_bin="$(command -v python3)"
CLAUDE_BIN="$python_bin" \
  "$issue_tmux_bin" new-session -d -s "$legacy_session" -c "$legacy_repo" \
  "exec '$python_bin' '$direct_fixture' --state '$legacy_state' --input-log '$legacy_input' --claude" \
  >/dev/null 2>&1 || fail test_issue6_legacy_fixture_start "could not create legacy direct session"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  grep -Fq 'ready' "$legacy_state" 2>/dev/null && break
  sleep 0.1
done
"$issue_tmux_bin" set-environment -t "=$legacy_session" KAOLA_PROJECT_RUNNER 1
"$issue_tmux_bin" set-environment -t "=$legacy_session" KAOLA_PROJECT_RUNNER_PLATFORM claude-code
"$issue_tmux_bin" set-environment -t "=$legacy_session" KAOLA_PROJECT_RUNNER_REPO "$legacy_repo"

export CLAUDE_BIN="$python_bin"
fake_snapshot="kpr-snapshot-v2:$(printf '%064d' 0)"
if capture_command claude-code observe --repo "$legacy_repo" --session "$legacy_session"; then
  legacy_observe="$COMMAND_OUTPUT"
  json_assert test_issue6_legacy_observe_schema \
    "d['result'] == 'observed' and d['snapshot_id'] is None and d['relay']['managed'] is False and d['relay']['child_pid'] is None and 'relay-required' in d['evidence_flags']" \
    "$legacy_observe"
else
  fail test_issue6_legacy_observe_schema "legacy observe failed: $COMMAND_OUTPUT"
fi

capture_command claude-code send --repo "$legacy_repo" --session "$legacy_session" \
  --if-snapshot "$fake_snapshot" --text must-not-send || true
expect_refusal test_issue6_legacy_send_refuses 'relay-required'

capture_command claude-code stop --repo "$legacy_repo" --session "$legacy_session" \
  --if-snapshot "$fake_snapshot" || true
expect_refusal test_issue6_legacy_stop_refuses 'relay-required'

capture_command claude-code stop --repo "$legacy_repo" --session "$legacy_session" \
  --if-snapshot "$fake_snapshot" --force || true
expect_refusal test_issue6_legacy_force_stop_refuses 'relay-required'

capture_command claude-code answer --repo "$legacy_repo" --session "$legacy_session" \
  --if-snapshot "$fake_snapshot" --decision-id "kpr-decision-v1:$(printf '%064d' 1)" \
  --replace-editor --text must-not-answer || true
expect_refusal test_issue6_legacy_answer_refuses 'relay-required'

[[ -z "$(cat "$legacy_input" 2>/dev/null || true)" ]] || \
  fail test_issue6_legacy_mutations_are_read_only "legacy direct session received bytes: $(cat "$legacy_input")"
"$issue_tmux_bin" has-session -t "=$legacy_session" >/dev/null 2>&1 || \
  fail test_issue6_legacy_mutations_are_read_only "legacy direct session was removed"

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #6 native/legacy acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #6 native/legacy acceptance: PASS\n'
