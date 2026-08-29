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

printf 'argv0=%s\nargv1=%s\nargv2=%s\n' "$0" "${1-}" "${2-}" >"${WRONG_PROCESS_ARGS_LOG:?}"

while IFS= read -r line; do
  printf 'WRONG_SHELL_RECEIVED:%s\n' "$line" >>"${WRONG_PROCESS_LOG:?}"
done
WRONG_SHELL
  chmod +x "$path"
  printf '%s\n' "$path"
}

make_kimi_process_title_fake() {
  local path="$issue_tmp_root/kimi-process-title-fake.js"
  cat >"$path" <<'KIMI_PROCESS_TITLE'
#!/usr/bin/env node

process.title = 'kimi-code';
const args = process.argv.slice(2);
if (args[0] === 'doctor') {
  process.stdout.write(JSON.stringify({kaolaWorkflow: true, workflowNext: true, finalize: true}) + '\n');
  process.exit(0);
}
if (args[0] === '--version') {
  process.stdout.write('kimi-process-title-fixture 1.0.0\n');
  process.exit(0);
}

process.stdout.write('\x1b]0;Kimi Code\x07');
process.stdout.write('Kimi Code\nKaola Workflow surface\n│ > │\n');
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  if (chunk.includes('/exit') || chunk.includes('/quit')) process.exit(0);
});
setInterval(() => {}, 1000);
KIMI_PROCESS_TITLE
  chmod +x "$path"
  printf '%s\n' "$path"
}

prepare_kimi_surface() {
  local repo="$1"
  mkdir -p "$repo/.kimi-code/skills/workflow-next" \
    "$repo/.kimi-code/skills/kaola-workflow-finalize" "$repo/.kimi-code/agents" \
    "$repo/.kimi-code/kaola-workflow/scripts"
  printf '%s\n' workflow-next >"$repo/.kimi-code/skills/workflow-next/SKILL.md"
  printf '%s\n' finalize >"$repo/.kimi-code/skills/kaola-workflow-finalize/SKILL.md"
  printf '%s\n' 'fixture agent manifest' >"$repo/.kimi-code/agents/.kaola-workflow-agent-manifest"
  printf '%s\n' 'fixture claim hook' >"$repo/.kimi-code/kaola-workflow/scripts/kaola-workflow-claim.js"
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
  args_log="$issue_tmp_root/${platform}-wrong-process-args.log"
  : >"$receive_log"
  : >"$args_log"
  export WRONG_PROCESS_PLATFORM="$platform" WRONG_PROCESS_LOG="$receive_log" WRONG_PROCESS_ARGS_LOG="$args_log"

  # Invoke an actual /bin/sh process in the pane, then stamp the exact Runner
  # ownership markers around it.  The scrollback and title intentionally spoof
  # the adapter's normal TUI/idle evidence.  The fake runtime path is passed
  # only as argv[2] to the unrelated shell (after an unused marker), so a
  # substring search cannot mistake a later argument for the running process.
  runtime_marker="unused-runtime-argument"
  "$issue_tmux_bin" new-session -d -s "$session" -c "$repo" \
    /bin/sh -c 'exec "$1" "$2" "$3"' wrong-process-launch "$wrong_shell" "$runtime_marker" "$fake_runtime"
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
  grep -Fq "argv1=$runtime_marker" "$args_log" || \
    fail "test_${platform}_wrong_process_is_spoofed_but_owned" "unused marker did not occupy argv[1]: $(cat "$args_log")"
  grep -Fq "argv2=$fake_runtime" "$args_log" || \
    fail "test_${platform}_wrong_process_is_spoofed_but_owned" "fake runtime path was not an unused later argv[2]: $(cat "$args_log")"
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

# Kimi's installed launcher is a Node script that rewrites process.title to
# `kimi-code`.  The adapter must accept that observed process identity while
# retaining the normal Kimi title/prompt evidence and a live pane.
kimi_repo="$(issue_new_repo kimi-process-title)"
prepare_kimi_surface "$kimi_repo"
kimi_title_bin="$(make_kimi_process_title_fake)"
export KIMI_BIN="$kimi_title_bin" KIMI_CODE_HOME="$issue_tmp_root/kimi-code-home"
mkdir -p "$KIMI_CODE_HOME"
kimi_title_session="kimi-process-title-$$"
set +e
kimi_title_start="$(run_runner kimi-cli start --repo "$kimi_repo" --session "$kimi_title_session" 2>&1)"
kimi_title_start_rc=$?
set -e
[[ "$kimi_title_start_rc" -eq 0 ]] || \
  fail test_kimi_process_title_rewrite "start failed for process.title=kimi-code: $kimi_title_start"
if "$issue_tmux_bin" has-session -t "=$kimi_title_session" >/dev/null 2>&1; then
  kimi_title_status="$(run_runner kimi-cli status --repo "$kimi_repo" --session "$kimi_title_session")"
  json_assert test_kimi_process_title_rewrite \
    "d['present'] and d['owned'] and d['platform_match'] and d['repo_match'] and d['pane_count'] == 1 and d['process_match'] is True and d['tui_detected'] is True and d['activity'] == 'idle' and 'Kimi' in d['pane_title']" \
    "$kimi_title_status"
  run_runner kimi-cli stop --repo "$kimi_repo" --session "$kimi_title_session" --force >/dev/null 2>&1 || true
else
  fail test_kimi_process_title_rewrite "start left no live Kimi process-title session"
fi

if [[ "$failures" -gt 0 ]]; then
  printf 'process identity acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'process identity acceptance: PASS\n'
