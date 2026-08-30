#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/claude-code-tmux.sh"
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

snapshot_id() {
  JSON_INPUT="$1" python3 -c "import json, os; print(json.loads(os.environ['JSON_INPUT'])['snapshot_id'])"
}

expect_fail() {
  local label="$1"
  shift
  local output rc
  set +e
  output="$("$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "$label" "expected non-zero exit"
  printf '%s\n' "$output"
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" claude-code "$@"
}

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo claude-runtime)"
mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"

claude_fake="$issue_tmp_root/claude-fake"
claude_log="$issue_tmp_root/claude-argv.log"
cat >"$claude_fake" <<'FAKE_CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
printf 'cwd=%s\targs=' "$PWD" >>"${CLAUDE_TEST_LOG:?}"
printf '%q ' "$@" >>"$CLAUDE_TEST_LOG"
printf '\n' >>"$CLAUDE_TEST_LOG"
if [[ "${1:-}" == --version ]]; then
  printf '%s\n' 'Claude Code fixture 1.0.0'
  exit 0
fi
if [[ "${1:-}" == --help ]]; then
  printf '%s\n' '--model <model>' '--effort <level>' '--permission-mode <mode>'
  exit 0
fi
printf '\033]0;%s\007' 'Implement selected Kaola batch'
printf '%s\n' \
  'Claude Code' \
  'Opus 5 | high effort' \
  'This command requires approval' \
  'Do you want to proceed?' \
  '❯ 1. Yes' \
  "   2. Yes, and don't ask again" \
  '   3. Yes, and switch to auto mode · auto mode handles these prompts for you' \
  '   4. No' \
  'Esc to cancel · Tab to amend · ctrl+e to explain'
while IFS= read -r line; do
  [[ "$line" == /exit ]] && exit 0
done
FAKE_CLAUDE
chmod +x "$claude_fake"
export CLAUDE_BIN="$claude_fake" CLAUDE_TEST_LOG="$claude_log" KAOLA_START_TIMEOUT=5

# Keep the private server alive, then reproduce the live user's 1-based tmux
# numbering. The Claude carrier must target the resulting stable pane id.
keeper="claude-keeper-$$"
"$issue_tmux_bin" new-session -d -s "$keeper" -c "$repo"
"$issue_tmux_bin" set-option -g base-index 1
"$issue_tmux_bin" set-window-option -g pane-base-index 1

session="claude-base-index-one-$$"
start_output="$(run_runner start --repo "$repo" --session "$session" 2>&1)" || \
  fail test_claude_base_index_one "start failed: $start_output"

if "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1; then
  status_json="$(run_runner status --repo "$repo" --session "$session")"
  json_assert test_claude_base_index_one \
    "d['owned'] and d['repo_match'] and d['process_match'] and d['tui_detected'] and d['pane_id'].startswith('%')" \
    "$status_json"
  json_assert test_claude_native_approval_waits \
    "d['activity'] == 'waiting-human'" "$status_json"
  grep -Fq -- '--model opus --effort high --permission-mode auto' "$claude_log" || \
    fail test_claude_default_launch_configuration "missing launch args: $(cat "$claude_log")"

  send_missing="$(expect_fail test_claude_send_requires_snapshot \
    run_runner send --repo "$repo" --session "$session" --require-empty-editor --text must-not-inject)"
  grep -Fq '"result": "snapshot-required"' <<<"$send_missing" || \
    fail test_claude_send_requires_snapshot "missing snapshot refusal: $send_missing"
  approval_observe="$(run_runner observe --repo "$repo" --session "$session")"
  approval_snapshot="$(snapshot_id "$approval_observe")"
  send_output="$(expect_fail test_claude_approval_rejects_input \
    run_runner send --repo "$repo" --session "$session" --if-snapshot "$approval_snapshot" --require-empty-editor --text must-not-inject)"
  grep -Fq '"result": "editor-unknown"' <<<"$send_output" || \
    fail test_claude_approval_rejects_input "missing editor-unknown refusal: $send_output"
  force_missing="$(expect_fail test_claude_force_stop_requires_snapshot \
    run_runner stop --repo "$repo" --session "$session" --force)"
  grep -Fq '"result": "snapshot-required"' <<<"$force_missing" || \
    fail test_claude_force_stop_requires_snapshot "missing snapshot refusal: $force_missing"
  force_stopped="$(run_runner stop --repo "$repo" --session "$session" --if-snapshot "$approval_snapshot" --force)" || \
    fail test_claude_force_stop "force stop failed: $force_stopped"
  if [[ -n "${force_stopped:-}" ]]; then
    json_assert test_claude_force_stop \
      "d['result'] == 'stopped' and d['action'] == 'force-stop' and d['final_state']['session_present'] is False" \
      "$force_stopped"
  fi
fi

invalid_effort="$(expect_fail test_claude_invalid_effort \
  run_runner start --repo "$repo" --session "claude-invalid-effort-$$" --effort extreme)"
grep -Fq 'unsupported Claude effort' <<<"$invalid_effort" || \
  fail test_claude_invalid_effort "missing typed refusal: $invalid_effort"

if [[ "$failures" -gt 0 ]]; then
  printf 'Claude runtime acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Claude runtime acceptance: PASS\n'
