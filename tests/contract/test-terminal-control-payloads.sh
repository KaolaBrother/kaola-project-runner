#!/usr/bin/env bash
set -u -o pipefail

# Issue #6 terminal-input acceptance. Guarded send/answer payloads are text,
# not terminal programs. CR, ESC, other C0/C1 controls, and embedded paste
# closers must never reach the child. LF/TAB preserve multiline prompts only
# when the child has attested bracketed-paste mode.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
raw_tui="$project_root/tests/fixtures/observations/claude-code/raw-mode-tui.py"
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
}

json_value() {
  local input="$1" expression="$2"
  JSON_INPUT="$input" python3 -c \
    "import json, os; d=json.loads(os.environ['JSON_INPUT']); print($expression)"
}

assert_public_refusal() {
  local label="$1"
  [[ "$COMMAND_RC" -ne 0 ]] || \
    fail "$label" "unsafe payload succeeded: $COMMAND_OUTPUT"
  JSON_INPUT="$COMMAND_OUTPUT" python3 -c \
    'import json, os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "refused", d' 2>/dev/null || \
    fail "$label" "unsafe payload did not return a public result=refused receipt: $COMMAND_OUTPUT"
}

assert_no_child_input() {
  local label="$1" repo="$2" session="$3" offset_before="$4" submit_log="$5"
  local after offset_after
  if ! after="$(run_runner claude-code observe --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "session could not be observed after refusal: $after"
    return
  fi
  offset_after="$(json_value "$after" 'd["relay"]["child_input_offset"]')"
  [[ "$offset_after" == "$offset_before" ]] || \
    fail "$label" "child PTY input offset changed from $offset_before to $offset_after"
  [[ ! -s "$submit_log" ]] || \
    fail "$label" "unsafe payload submitted input to the child: $(cat "$submit_log")"
  "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1 || \
    fail "$label" "refusal removed the managed session"
}

assert_exact_submission() {
  local label="$1" submit_log="$2" payload="$3"
  EXPECTED_PAYLOAD="$payload" SUBMIT_LOG="$submit_log" python3 -c '
import os
from pathlib import Path
actual = Path(os.environ["SUBMIT_LOG"]).read_text(encoding="utf-8")
expected = "submitted=" + os.environ["EXPECTED_PAYLOAD"] + "\n"
assert actual == expected, {"expected": expected, "actual": actual}
' || fail "$label" "payload was not submitted exactly once as bracketed text"
}

prepare_repo() {
  local repo="$1"
  mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
  printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
  printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
  printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
  printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"
}

run_send_vector() {
  local vector_name="$1" payload="$2" index="$3"
  local session="issue6-control-send-${index}-$$"
  local submit_log="$issue_tmp_root/send-${index}.log"
  local start observe snapshot offset_before label
  label="test_issue6_send_rejects_${vector_name}_before_pty_write"
  : >"$submit_log"
  export FAKE_CLAUDE_MODE=empty FAKE_CLAUDE_SUBMIT_LOG="$submit_log"

  if ! start="$(run_runner claude-code start --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "fixture start failed: $start"
    return
  fi
  if ! observe="$(run_runner claude-code observe --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "fixture observe failed: $observe"
    "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
    return
  fi
  snapshot="$(json_value "$observe" 'd["snapshot_id"]')"
  offset_before="$(json_value "$observe" 'd["relay"]["child_input_offset"]')"

  capture_command claude-code send --repo "$repo" --session "$session" \
    --if-snapshot "$snapshot" --require-empty-editor --text "$payload"
  assert_public_refusal "$label"
  assert_no_child_input "$label" "$repo" "$session" "$offset_before" "$submit_log"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

run_answer_vector() {
  local vector_name="$1" payload="$2" index="$3"
  local session="issue6-control-answer-${index}-$$"
  local submit_log="$issue_tmp_root/answer-${index}.log"
  local start observe snapshot decision_id offset_before label
  label="test_issue6_answer_rejects_${vector_name}_before_pty_write"
  : >"$submit_log"
  export FAKE_CLAUDE_MODE=decision FAKE_CLAUDE_SUBMIT_LOG="$submit_log"

  if ! start="$(run_runner claude-code start --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "fixture start failed: $start"
    return
  fi
  if ! observe="$(run_runner claude-code observe --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "fixture observe failed: $observe"
    "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
    return
  fi
  snapshot="$(json_value "$observe" 'd["snapshot_id"]')"
  decision_id="$(json_value "$observe" 'd["structured_decision_marker"]["decision_id"]')"
  offset_before="$(json_value "$observe" 'd["relay"]["child_input_offset"]')"

  capture_command claude-code answer --repo "$repo" --session "$session" \
    --decision-id "$decision_id" --if-snapshot "$snapshot" --replace-editor --text "$payload"
  assert_public_refusal "$label"
  assert_no_child_input "$label" "$repo" "$session" "$offset_before" "$submit_log"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

run_bracketed_text_vector() {
  local action="$1" payload="$2" index="$3"
  local session="issue6-bracketed-${action}-${index}-$$"
  local submit_log="$issue_tmp_root/bracketed-${action}-${index}.log"
  local start observe snapshot decision_id offset_before offset_after label
  label="test_issue6_${action}_accepts_lf_tab_only_as_bracketed_text"
  : >"$submit_log"
  unset FAKE_CLAUDE_BRACKETED_PASTE
  if [[ "$action" == send ]]; then
    export FAKE_CLAUDE_MODE=empty
  else
    export FAKE_CLAUDE_MODE=decision
  fi
  export FAKE_CLAUDE_SUBMIT_LOG="$submit_log"

  if ! start="$(run_runner claude-code start --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "fixture start failed: $start"
    return
  fi
  if ! observe="$(run_runner claude-code observe --repo "$repo" --session "$session" 2>&1)"; then
    fail "$label" "fixture observe failed: $observe"
    "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
    return
  fi
  snapshot="$(json_value "$observe" 'd["snapshot_id"]')"
  offset_before="$(json_value "$observe" 'd["relay"]["child_input_offset"]')"
  [[ "$(json_value "$observe" 'd["relay"]["bracketed_paste"]')" == True ]] || \
    fail "$label" "fixture did not attest bracketed-paste mode"

  if [[ "$action" == send ]]; then
    capture_command claude-code send --repo "$repo" --session "$session" \
      --if-snapshot "$snapshot" --require-empty-editor --text "$payload"
  else
    decision_id="$(json_value "$observe" 'd["structured_decision_marker"]["decision_id"]')"
    capture_command claude-code answer --repo "$repo" --session "$session" \
      --decision-id "$decision_id" --if-snapshot "$snapshot" --replace-editor --text "$payload"
  fi
  [[ "$COMMAND_RC" -eq 0 ]] || fail "$label" "safe bracketed text was refused: $COMMAND_OUTPUT"
  JSON_INPUT="$COMMAND_OUTPUT" ACTION="$action" python3 -c '
import json, os
d = json.loads(os.environ["JSON_INPUT"])
expected = "sent" if os.environ["ACTION"] == "send" else "answer-sent"
assert d["result"] == expected, d
' 2>/dev/null || fail "$label" "missing successful public receipt: $COMMAND_OUTPUT"
  assert_exact_submission "$label" "$submit_log" "$payload"
  if observe="$(run_runner claude-code observe --repo "$repo" --session "$session" 2>&1)"; then
    offset_after="$(json_value "$observe" 'd["relay"]["child_input_offset"]')"
    [[ "$offset_after" -gt "$offset_before" ]] || \
      fail "$label" "accepted text did not reach child PTY"
  else
    fail "$label" "accepted session could not be observed: $observe"
  fi
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo issue6-terminal-control-payloads)"
prepare_repo "$repo"
chmod +x "$raw_tui"
export CLAUDE_BIN="$raw_tui" KAOLA_START_TIMEOUT=5

vector_names=(
  carriage_return
  escape
  c0_bell
  c1_csi
  bracketed_paste_end
)
vector_payloads=(
  $'safe\runsafe'
  $'safe\x1bunsafe'
  $'safe\x07unsafe'
  $'safe\x9bunsafe'
  $'safe\x1b[201~unsafe'
)

for index in "${!vector_names[@]}"; do
  run_send_vector "${vector_names[$index]}" "${vector_payloads[$index]}" "$index"
  run_answer_vector "${vector_names[$index]}" "${vector_payloads[$index]}" "$index"
done

# LF and TAB are the two text controls retained for existing multiline prompt
# compatibility. They are safe only inside an attested bracketed-paste event.
multiline_payload=$'line one\nline two\tindented'
run_bracketed_text_vector send "$multiline_payload" 0
run_bracketed_text_vector answer "$multiline_payload" 0

# The same payload must fail before any PTY write if bracketed paste was not
# negotiated by the child. Reuse the public refusal oracle with independent
# sessions so send and answer each prove their own boundary.
export FAKE_CLAUDE_BRACKETED_PASTE=0
run_send_vector lf_tab_without_bracketed_paste "$multiline_payload" 90
run_answer_vector lf_tab_without_bracketed_paste "$multiline_payload" 90
unset FAKE_CLAUDE_BRACKETED_PASTE

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #6 terminal-control payload acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #6 terminal-control payload acceptance: PASS\n'
