#!/usr/bin/env bash
set -euo pipefail

# Process-identity acceptance.  Marker strings and idle prompts are attacker-
# controllable scrollback; ownership is not enough to authorize input when the
# one pane is actually an unrelated shell.  Each case uses a private tmux
# server and a shell that records any bytes delivered to stdin.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  JSON_INPUT="$input" python3 -c "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d" || \
    fail "$label" "JSON assertion failed: $input"
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@"
}

make_wrong_shell() {
  local path="$issue_tmp_root/wrong-process-shell"
  cat >"$path" <<'WRONG_SHELL'
#!/bin/sh
set -eu

case "${WRONG_PROCESS_PLATFORM:?}" in
  grok)
    printf '%s\n' 'Grok Build' 'minimal · /help' '❯'
    ;;
  claude-code)
    printf '%s\n' 'Claude Code' '❯'
    ;;
  opencode)
    printf '%s\n' '█▀▀█  OpenCode' 'Ask anything'
    ;;
  kimi-cli)
    printf '%s\n' 'Kimi Code' '│ > │'
    ;;
  cursor-cli)
    printf '%s\n' 'Cursor Agent' '→ Plan, search, build anything'
    ;;
esac

while IFS= read -r line; do
  printf 'WRONG_SHELL_RECEIVED:%s\n' "$line" >>"${WRONG_PROCESS_LOG:?}"
done
WRONG_SHELL
  chmod +x "$path"
  printf '%s\n' "$path"
}

set_runtime_binary() {
  local platform="$1" path="$2"
  case "$platform" in
    grok) GROK_BIN="$path" ;;
    claude-code) CLAUDE_BIN="$path" ;;
    opencode) OPENCODE_BIN="$path" ;;
    kimi-cli) KIMI_BIN="$path" ;;
    cursor-cli) CURSOR_AGENT_BIN="$path" ;;
  esac
  export GROK_BIN CLAUDE_BIN OPENCODE_BIN KIMI_BIN CURSOR_AGENT_BIN
}

issue_setup
trap issue_cleanup EXIT

wrong_shell="$(make_wrong_shell)"
platforms=(grok claude-code opencode kimi-cli cursor-cli)

for platform in "${platforms[@]}"; do
  repo="$(issue_new_repo "wrong-process-$platform")"
  IFS=$'\t' read -r fake_runtime _fake_log < <(issue_make_fake_runtime "$platform")
  set_runtime_binary "$platform" "$fake_runtime"
  session="wrong-process-${platform//[^A-Za-z0-9]/-}-$$"
  receive_log="$issue_tmp_root/${platform}-wrong-process-received.log"
  : >"$receive_log"
  export WRONG_PROCESS_PLATFORM="$platform" WRONG_PROCESS_LOG="$receive_log"

  # Invoke an actual /bin/sh process in the pane, then stamp the exact Runner
  # ownership markers around it.  The scrollback and title intentionally spoof
  # the adapter's normal TUI/idle evidence.
  "$issue_tmux_bin" new-session -d -s "$session" -c "$repo" /bin/sh "$wrong_shell"
  canonical_repo="$(cd "$repo" && pwd -P)"
  "$issue_tmux_bin" set-environment -t "=$session" KAOLA_PROJECT_RUNNER 1
  "$issue_tmux_bin" set-environment -t "=$session" KAOLA_PROJECT_RUNNER_PLATFORM "$platform"
  "$issue_tmux_bin" set-environment -t "=$session" KAOLA_PROJECT_RUNNER_REPO "$canonical_repo"
  "$issue_tmux_bin" select-pane -t "=$session:0.0" -T "$platform"
  sleep 0.2

  status_before="$(run_runner "$platform" status --repo "$repo" --session "$session")"
  runtime_name="${fake_runtime##*/}"
  json_assert "test_${platform}_wrong_process_is_spoofed_but_owned" \
    "d['present'] and d['owned'] and d['platform_match'] and d['repo_match'] and d['pane_count'] == 1 and d['tui_detected'] is False and d['activity'] == 'unknown' and d['pane_command'] != '$runtime_name'" \
    "$status_before"

  pane_before="$("$issue_tmux_bin" capture-pane -p -t "=$session:0.0" -S -50)"
  case "$platform" in
    grok) spoof_marker='Grok Build' ;;
    claude-code) spoof_marker='Claude Code' ;;
    opencode) spoof_marker='OpenCode' ;;
    kimi-cli) spoof_marker='Kimi Code' ;;
    cursor-cli) spoof_marker='Cursor Agent' ;;
  esac
  grep -Fq "$spoof_marker" <<<"$pane_before" || \
    fail "test_${platform}_wrong_process_is_spoofed_but_owned" "fixture did not expose spoofed runtime marker: $pane_before"
  set +e
  send_output="$(run_runner "$platform" send --repo "$repo" --session "$session" --text "WRONG_PROCESS_PROMPT_$platform" 2>&1)"
  send_rc=$?
  set -e
  [[ "$send_rc" -ne 0 ]] || fail "test_${platform}_wrong_process_rejects_send" "send succeeded through wrong process: $send_output"
  grep -Eqi 'process|runtime|command' <<<"$send_output" || \
    fail "test_${platform}_wrong_process_rejects_send" "refusal lacks process-identity evidence: $send_output"
  [[ ! -s "$receive_log" ]] || fail "test_${platform}_wrong_process_rejects_send" "wrong shell received prompt bytes: $(cat "$receive_log")"
  pane_after="$("$issue_tmux_bin" capture-pane -p -t "=$session:0.0" -S -50)"
  [[ "$pane_before" == "$pane_after" ]] || fail "test_${platform}_wrong_process_rejects_send" "wrong process scrollback changed"
  "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1 || \
    fail "test_${platform}_wrong_process_rejects_send" "wrong process session was removed"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
done

if [[ "$failures" -gt 0 ]]; then
  printf 'process identity acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'process identity acceptance: PASS\n'
