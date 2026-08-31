#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
helper="$project_root/scripts/grok-tmux.sh"
tmp_root="$(mktemp -d "${TMPDIR:-/tmp}/grok-kaola-runner-test.XXXXXX")"
socket_tmp_root="$(mktemp -d /tmp/kpr-grok-test.XXXXXX)"
export TMPDIR="$socket_tmp_root"
tmux_base_bin="$(command -v tmux)"
tmux_socket="gkpr-test-$$-${RANDOM}"
tmux_bin="$tmp_root/tmux"
session="gkpr-test-$$"
unrelated="gkpr-unrelated-$$"
keeper="gkpr-keeper-$$"

cat >"$tmux_bin" <<'TMUX_SHIM'
#!/usr/bin/env bash
set -euo pipefail
exec "$GROK_TEST_TMUX_BIN" -L "$GROK_TEST_TMUX_SOCKET" "$@"
TMUX_SHIM
chmod +x "$tmux_bin"
export GROK_TEST_TMUX_BIN="$tmux_base_bin"
export GROK_TEST_TMUX_SOCKET="$tmux_socket"

cleanup() {
  "$tmux_bin" kill-session -t "$session" 2>/dev/null || true
  "$tmux_bin" kill-session -t "$unrelated" 2>/dev/null || true
  "$tmux_bin" kill-session -t "$keeper" 2>/dev/null || true
  "$tmux_bin" kill-server 2>/dev/null || true
  rm -rf "$tmp_root"
  rm -rf "$socket_tmp_root"
}
trap cleanup EXIT

repo="$tmp_root/repo"
other_repo="$tmp_root/other-repo"
fake_grok="$tmp_root/grok"
mkdir -p "$repo" "$other_repo"
git -C "$repo" init -q -b main
git -C "$other_repo" init -q -b main

# Keep the legacy validation hermetic. Its own server uses explicit ordinary
# numbering so a user's/default server configuration cannot affect the test.
"$tmux_bin" new-session -d -s "$keeper" -c "$tmp_root"
"$tmux_bin" set-option -g base-index 0
"$tmux_bin" set-window-option -g pane-base-index 0

cat >"$fake_grok" <<'FAKE'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "inspect" && "${2:-}" == "--json" ]]; then
  printf '%s\n' '{"grokVersion":"test","projectRoot":"test","skills":[{"name":"workflow-next"},{"name":"kaola-workflow-finalize"}]}'
  exit 0
fi

printf '\033]0;grok\007'
printf 'Grok Build test\nminimal · /help\n❯ '
while IFS= read -r line; do
  if [[ "$line" == "/quit" ]]; then
    exit 0
  fi
  if [[ "$line" == "BUSY" ]]; then
    printf 'Waiting for response…'
    sleep 2
    printf '\r\033[2KDONE\nminimal · /help\n❯ '
  else
    printf 'ECHO:%s\nminimal · /help\n❯ ' "$line"
  fi
done
FAKE
chmod +x "$fake_grok"

run_helper() {
  TMUX_BIN="$tmux_bin" GROK_BIN="$fake_grok" GROK_START_TIMEOUT=5 "$helper" "$@"
}

json_assert() {
  local expression="$1"
  JSON_INPUT="$(cat)" python3 -c "import json,os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d"
}

json_value() {
  local input="$1" expression="$2"
  JSON_INPUT="$input" python3 -c "import json,os; d=json.loads(os.environ['JSON_INPUT']); print($expression)"
}

expect_refusal() {
  local expected="$1"
  shift
  local output rc
  set +e
  output="$("$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || {
    printf 'expected non-zero exit: %s\n' "$output" >&2
    return 1
  }
  grep -Fq "$expected" <<<"$output" || {
    printf 'expected %s: %s\n' "$expected" "$output" >&2
    return 1
  }
  printf '%s\n' "$output"
}

run_helper preflight --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'ready' and d['workflow_next'] and d['kaola_workflow_finalize']"

"$tmux_bin" new-session -d -s "$unrelated" -c "$other_repo"

run_helper start --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'started' and d['owned'] and d['repo_match'] and d['grok_tui']"

run_helper status --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'present' and d['activity'] == 'idle' and d['pane_count'] == 1"

literal='literal ; $(touch SHOULD_NOT_EXIST) `touch ALSO_NOT`'
observe_before_send="$(run_helper observe --repo "$repo" --session "$session")"
snapshot_before_send="$(json_value "$observe_before_send" "d['snapshot_id']")"
sent_output="$(run_helper send --repo "$repo" --session "$session" --text "$literal")" || {
  printf 'RED: test_grok_send_accepts_idle_literal — tokenized send failed: %s\n' "$sent_output" >&2
  exit 1
}
printf '%s\n' "$sent_output" | json_assert "d['result'] == 'sent' and d['action'] == 'send' and d['based_on_snapshot'] == '' and d['mutation_performed'] is True and d['payload_fingerprint'].startswith('sha256:') and 'action_time_snapshot' not in d and 'observation_changed' not in d"
sleep 1
capture="$(run_helper capture --repo "$repo" --session "$session" --lines 40)"
printf '%s\n' "$capture" | grep -Fq 'ECHO:literal ; $(touch SHOULD_NOT_EXIST) `touch ALSO_NOT`'
[[ ! -e "$repo/SHOULD_NOT_EXIST" && ! -e "$repo/ALSO_NOT" ]]

wrong_repo_output="$(run_helper send --repo "$other_repo" --session "$session" --text wrong-repo 2>&1)" || true
if [[ "$wrong_repo_output" != *'repo-mismatch'* ]]; then
  printf 'expected repo mismatch to fail\n' >&2
  exit 1
fi

busy_start_observe="$(run_helper observe --repo "$repo" --session "$session")"
busy_start_snapshot="$(json_value "$busy_start_observe" "d['snapshot_id']")"
run_helper send --repo "$repo" --session "$session" --if-snapshot "$busy_start_snapshot" --text BUSY >/dev/null
sleep 1
busy_observe="$(run_helper observe --repo "$repo" --session "$session")"
busy_snapshot="$(json_value "$busy_observe" "d['snapshot_id']")"
busy_output="$(run_helper send --repo "$repo" --session "$session" --if-snapshot "$busy_snapshot" --text must-wait 2>&1)" || true
if [[ "$busy_output" != *'"result": "sent"'* ]]; then
  printf 'RED: test_busy_activity_is_advisory — busy advisory blocked caller-selected send: %s\n' "$busy_output" >&2
  exit 1
fi
sleep 2

stopped_output="$(run_helper stop --repo "$repo" --session "$session")" || {
  printf 'RED: test_grok_stop_exact_owned_session — tokenized stop failed: %s\n' "$stopped_output" >&2
  exit 1
}
printf '%s\n' "$stopped_output" | json_assert "d['result'] == 'stopped' and d['action'] == 'stop'"

"$tmux_bin" has-session -t "$unrelated"
run_helper status --repo "$repo" --session "$session" | \
  json_assert "d['result'] == 'absent' and not d['present']"

printf 'grok-tmux tests: PASS\n'
