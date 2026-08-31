#!/usr/bin/env bash
set -u -o pipefail

# A guarded payload is identified by its original bytes, not by how a TUI's
# terminal grid wraps those bytes.  Exercise the public Runner on both managed
# raw-mode carriers with a narrow pane and a single logical line long enough to
# occupy several visual rows.

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

prepare_claude_repo() {
  local repo="$1"
  mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
  printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
  printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
  printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
  printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"
}

assert_exact_submission() {
  local label="$1" submit_log="$2" payload="$3"
  EXPECTED_PAYLOAD="$payload" SUBMIT_LOG="$submit_log" python3 -c '
import os
from pathlib import Path
actual = Path(os.environ["SUBMIT_LOG"]).read_text(encoding="utf-8")
expected = "submitted=" + os.environ["EXPECTED_PAYLOAD"] + "\n"
assert actual == expected, {"expected": expected, "actual": actual}
' || fail "$label" "long wrapped payload was not submitted exactly once: $(python3 -c 'import pathlib,sys; print(repr(pathlib.Path(sys.argv[1]).read_text()))' "$submit_log")"
}

run_wrapped_send() {
  local platform="$1" index="$2" payload="${3:-$long_payload}"
  local scenario="${4:-long_single_line_wrap}"
  local platform_label="${platform//-/_}"
  local label="test_issue6_${platform_label}_${scenario}_submits_exact_payload"
  local repo session submit_log started observed snapshot pane_width first_line
  repo="$(issue_new_repo "issue6-wrapped-${platform}-${index}")"
  session="issue6-wrapped-${platform}-${index}-$$"
  submit_log="$issue_tmp_root/wrapped-${platform}-${index}.log"
  : >"$submit_log"

  if [[ "$platform" == claude-code ]]; then
    prepare_claude_repo "$repo"
    export CLAUDE_BIN="$raw_tui"
    unset FAKE_CLAUDE_TITLE
  else
    export GROK_BIN="$raw_tui" FAKE_CLAUDE_TITLE=grok
  fi
  export FAKE_CLAUDE_MODE=empty FAKE_CLAUDE_SUBMIT_LOG="$submit_log"
  unset FAKE_CLAUDE_PREPARE_DRIFT

  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public start failed: $COMMAND_OUTPUT"
    return
  fi
  started="$COMMAND_OUTPUT"
  JSON_INPUT="$started" python3 -c \
    'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "started", d' 2>/dev/null || \
    fail "$label" "public start did not return result=started: $started"

  "$issue_tmux_bin" resize-window -t "=$session" -x 40 -y 24 || \
    fail "$label" "could not establish the narrow wrapping pane"
  sleep 0.1
  capture_command "$platform" observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public observe failed: $COMMAND_OUTPUT"
  else
    observed="$COMMAND_OUTPUT"
    snapshot="$(json_value "$observed" 'd["snapshot_id"]')"
    pane_width="$(json_value "$observed" 'd["hard_evidence"]["pane_width"]')"
    first_line="${payload%%$'\n'*}"
    [[ "$pane_width" -eq 40 && "${#first_line}" -gt $((pane_width * 3)) ]] || \
      fail "$label" "fixture did not prove a naturally wrapping first logical line: width=$pane_width length=${#first_line}"

    capture_command "$platform" send --repo "$repo" --session "$session" \
      --if-snapshot "$snapshot" --text "$payload"
    [[ "$COMMAND_RC" -eq 0 ]] || \
      fail "$label" "public guarded send refused the naturally wrapped payload: $COMMAND_OUTPUT"
    if [[ "$COMMAND_RC" -eq 0 ]]; then
      JSON_INPUT="$COMMAND_OUTPUT" python3 -c \
        'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "sent", d' 2>/dev/null || \
        fail "$label" "public send lacked result=sent: $COMMAND_OUTPUT"
    fi
    assert_exact_submission "$label" "$submit_log" "$payload"
  fi

  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

run_wrapped_claude_answer() {
  local index="$1" payload="$2"
  local label="test_issue6_claude_code_composed_soft_wrap_lf_tab_answer_submits_exact_payload"
  local repo session submit_log started observed snapshot decision_id pane_width first_line
  repo="$(issue_new_repo "issue6-wrapped-claude-answer-${index}")"
  session="issue6-wrapped-claude-answer-${index}-$$"
  submit_log="$issue_tmp_root/wrapped-claude-answer-${index}.log"
  : >"$submit_log"
  prepare_claude_repo "$repo"
  export CLAUDE_BIN="$raw_tui" FAKE_CLAUDE_MODE=decision FAKE_CLAUDE_SUBMIT_LOG="$submit_log"
  unset FAKE_CLAUDE_TITLE FAKE_CLAUDE_PREPARE_DRIFT

  capture_command claude-code start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public start failed: $COMMAND_OUTPUT"
    return
  fi
  started="$COMMAND_OUTPUT"
  JSON_INPUT="$started" python3 -c \
    'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "started", d' 2>/dev/null || \
    fail "$label" "public start did not return result=started: $started"

  "$issue_tmux_bin" resize-window -t "=$session" -x 40 -y 24 || \
    fail "$label" "could not establish the narrow wrapping pane"
  sleep 0.1
  capture_command claude-code observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public observe failed: $COMMAND_OUTPUT"
  else
    observed="$COMMAND_OUTPUT"
    snapshot="$(json_value "$observed" 'd["snapshot_id"]')"
    decision_id="$(json_value "$observed" 'd["structured_decision_marker"]["decision_id"]')"
    pane_width="$(json_value "$observed" 'd["hard_evidence"]["pane_width"]')"
    first_line="${payload%%$'\n'*}"
    [[ "$pane_width" -eq 40 && "${#first_line}" -gt $((pane_width * 3)) ]] || \
      fail "$label" "fixture did not prove a naturally wrapping first logical line: width=$pane_width length=${#first_line}"

    capture_command claude-code answer --repo "$repo" --session "$session" \
      --decision-id "$decision_id" --if-snapshot "$snapshot" --replace-editor --text "$payload"
    [[ "$COMMAND_RC" -eq 0 ]] || \
      fail "$label" "public guarded answer refused the naturally wrapped LF/TAB payload: $COMMAND_OUTPUT"
    if [[ "$COMMAND_RC" -eq 0 ]]; then
      JSON_INPUT="$COMMAND_OUTPUT" python3 -c \
        'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "answer-sent", d' 2>/dev/null || \
        fail "$label" "public answer lacked result=answer-sent: $COMMAND_OUTPUT"
    fi
    assert_exact_submission "$label" "$submit_log" "$payload"
  fi

  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

run_wrapped_drift_evidence() {
  local platform="$1" index="$2" payload="$3"
  local platform_label="${platform//-/_}"
  local label="test_direct_${platform_label}_live_editor_change_is_evidence_not_a_gate"
  local repo session submit_log observed snapshot pane_width first_line
  repo="$(issue_new_repo "issue6-wrapped-drift-${platform}-${index}")"
  session="issue6-wrapped-drift-${platform}-${index}-$$"
  submit_log="$issue_tmp_root/wrapped-drift-${platform}-${index}.log"
  : >"$submit_log"

  if [[ "$platform" == claude-code ]]; then
    prepare_claude_repo "$repo"
    export CLAUDE_BIN="$raw_tui"
    unset FAKE_CLAUDE_TITLE
  else
    export GROK_BIN="$raw_tui" FAKE_CLAUDE_TITLE=grok
  fi
  export FAKE_CLAUDE_MODE=empty FAKE_CLAUDE_SUBMIT_LOG="$submit_log"
  export FAKE_CLAUDE_PREPARE_DRIFT=editor-hard-line

  capture_command "$platform" start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public start failed: $COMMAND_OUTPUT"
    return
  fi
  "$issue_tmux_bin" resize-window -t "=$session" -x 40 -y 24 || \
    fail "$label" "could not establish the narrow wrapping pane"
  sleep 0.1
  capture_command "$platform" observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public observe failed: $COMMAND_OUTPUT"
  else
    observed="$COMMAND_OUTPUT"
    snapshot="$(json_value "$observed" 'd["snapshot_id"]')"
    pane_width="$(json_value "$observed" 'd["hard_evidence"]["pane_width"]')"
    first_line="${payload%%$'\n'*}"
    [[ "$pane_width" -eq 40 && "${#first_line}" -gt $((pane_width * 3)) && "$payload" == *$'\n'* ]] || \
      fail "$label" "fixture did not prove soft-wrap followed by a real logical newline"

    capture_command "$platform" send --repo "$repo" --session "$session" \
      --if-snapshot "$snapshot" --text "$payload"
    [[ "$COMMAND_RC" -eq 0 ]] || \
      fail "$label" "live editor change blocked the Agent-selected transport: $COMMAND_OUTPUT"
    JSON_INPUT="$COMMAND_OUTPUT" python3 -c \
      'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "sent", d' 2>/dev/null || \
      fail "$label" "public send did not return result=sent: $COMMAND_OUTPUT"
    EXPECTED_PAYLOAD="$payload" SUBMIT_LOG="$submit_log" python3 -c '
import os
from pathlib import Path
actual = Path(os.environ["SUBMIT_LOG"]).read_text(encoding="utf-8")
expected = "submitted=" + os.environ["EXPECTED_PAYLOAD"] + "\nforeign-hard-line\n"
assert actual == expected, {"expected": expected, "actual": actual}
' || fail "$label" "fixture did not expose the live editor change after transport"
    "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1 || \
      fail "$label" "refused send removed the exact managed session"
  fi

  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
  unset FAKE_CLAUDE_PREPARE_DRIFT
}

issue_setup
trap issue_cleanup EXIT
chmod +x "$raw_tui"
export KAOLA_START_TIMEOUT=5

long_payload='wrap-proof-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMNOPQRSTUVWXYZ-wrap-proof-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMNOPQRSTUVWXYZ-wrap-proof-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
[[ "$long_payload" != *$'\n'* ]] || fail test_issue6_long_wrap_fixture_is_single_line "fixture payload contains a logical newline"
composed_payload="${long_payload}"$'\n\tsecond logical line with a real tab'
COMPOSED_PAYLOAD="$composed_payload" python3 -c '
import os
payload = os.environ["COMPOSED_PAYLOAD"]
assert payload.count("\n") == 1
assert payload.count("\t") == 1
assert len(payload.split("\n", 1)[0]) > 120
' || fail test_issue6_composed_wrap_fixture_shape "composed fixture lacks the exact soft-wrap + LF + TAB shape"

run_wrapped_send claude-code 1
run_wrapped_send grok 2
run_wrapped_send claude-code 3 "$composed_payload" composed_soft_wrap_lf_tab_send
run_wrapped_send grok 4 "$composed_payload" composed_soft_wrap_lf_tab_send
run_wrapped_claude_answer 5 "$composed_payload"
relay_regression_payload=''
for _ in {1..24}; do
  relay_regression_payload+="long-relay-regression-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
done
relay_regression_payload+=$'\nsecond line ensures bracketed paste remains literal'

run_wrapped_send claude-code 6 "$relay_regression_payload" relay_timeout_regression
run_wrapped_drift_evidence claude-code 7 "$composed_payload"
run_wrapped_drift_evidence grok 8 "$composed_payload"

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #6 long wrapped send acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #6 long wrapped send acceptance: PASS\n'
