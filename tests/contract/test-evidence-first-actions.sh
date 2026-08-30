#!/usr/bin/env bash
set -u -o pipefail

# Issue #7 public transport acceptance. The faithful Claude-shaped TUI is only
# the child runtime; observe/send/stop all exercise the real shared Runner,
# managed relay, tmux identity, lease, mutation lock, and literal-input path.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
raw_tui="$project_root/tests/fixtures/observations/claude-code/raw-mode-tui.py"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"
# The shared helper enables errexit for its own suites. This test intentionally
# accumulates independent RED assertions, so restore its declared policy.
set +e
set -u -o pipefail

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
  # This suite deliberately accumulates independent assertions. Do not let
  # the sourced helper's errexit policy leak back in after a command capture.
  set +e
  COMMAND_OUTPUT="$output"
  COMMAND_RC=$rc
}

json_value() {
  local input="$1" expression="$2"
  JSON_INPUT="$input" python3 -c \
    "import json,os; d=json.loads(os.environ['JSON_INPUT']); print($expression)"
}

prepare_claude_repo() {
  local repo="$1"
  mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
  printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
  printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
  printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
  printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"
}

prepare_cursor_authority() {
  export CURSOR_HOME="$issue_tmp_root/cursor-home"
  local helper="$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
  mkdir -p "$CURSOR_HOME/commands" "$(dirname "$helper")"
  printf '%s\n' workflow-next >"$CURSOR_HOME/commands/workflow-next.md"
  printf '%s\n' finalize >"$CURSOR_HOME/commands/kaola-workflow-finalize.md"
  cat >"$helper" <<'CURSOR_HELPER'
#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const args = process.argv.slice(2);
if (args.includes("--doctor")) {
  process.stdout.write(JSON.stringify({authority:{receipt_status:"valid",freshness:"current"}})+"\n");
  process.exit(0);
}
const index = args.indexOf("--ensure-target");
if (index !== -1) {
  const target = path.resolve(args[index + 1]);
  const commands = path.join(target, ".cursor", "commands");
  fs.mkdirSync(commands, {recursive:true});
  fs.writeFileSync(path.join(commands, "workflow-next.md"), "workflow-next\n");
  fs.writeFileSync(path.join(commands, "kaola-workflow-finalize.md"), "finalize\n");
  process.stdout.write(JSON.stringify({status:"materialized",scope:"project",target,files:2})+"\n");
  process.exit(0);
}
process.exit(2);
CURSOR_HELPER
  chmod +x "$helper"
  CURSOR_ROOT="$CURSOR_HOME" python3 - <<'PY'
import hashlib
import json
import os
import pathlib
import stat

root = pathlib.Path(os.environ["CURSOR_ROOT"])
files = {}
for relative in (
    "commands/workflow-next.md",
    "commands/kaola-workflow-finalize.md",
    "kaola-workflow/scripts/kaola-workflow-cursor-surface.js",
):
    path = root / relative
    files[relative] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mode": stat.S_IMODE(path.stat().st_mode),
    }
(root / "kaola-workflow/cursor-authority.json").write_text(
    json.dumps({"schema_version":1,"kind":"cursor_global_authority","forge":"github","files":files})+"\n",
    encoding="utf-8",
)
PY
}

start_fixture() {
  local label="$1" repo="$2" session="$3" mode="$4"
  export CLAUDE_BIN="$raw_tui"
  export FAKE_CLAUDE_MODE="$mode"
  capture_command claude-code start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public start failed: $COMMAND_OUTPUT"
    return 1
  fi
  JSON_INPUT="$COMMAND_OUTPUT" python3 -c \
    'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "started", d' 2>/dev/null || {
      fail "$label" "public start lacked result=started: $COMMAND_OUTPUT"
      return 1
    }
}

observe_snapshot() {
  local label="$1" repo="$2" session="$3" observation snapshot
  capture_command claude-code observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public observe failed: $COMMAND_OUTPUT"
    printf '%s\n' ''
    return
  fi
  observation="$COMMAND_OUTPUT"
  snapshot="$(json_value "$observation" 'd.get("snapshot_id")')"
  JSON_INPUT="$observation" python3 -c '
import json, os, re
d=json.loads(os.environ["JSON_INPUT"])
assert d["result"] == "observed", d
assert isinstance(d["raw_current_frame"], str) and d["raw_current_frame"], d
assert d["hard_evidence"]["owned"] is True, d
assert d["hard_evidence"]["repo_match"] is True, d
assert d["hard_evidence"]["platform_match"] is True, d
assert d["relay"]["managed"] is True, d
assert re.fullmatch(r"kpr-snapshot-v2:[0-9a-f]{64}", d.get("snapshot_id") or ""), d
' 2>/dev/null || fail "$label" "semantic advisory evidence suppressed the factual fresh snapshot: $observation"
  printf '%s\n' "$snapshot"
}

test_generic_send_uses_agent_decision() {
  local label=test_issue7_generic_send_ignores_semantic_advisories
  local repo session log snapshot payload expected_fp changed_observe changed_snapshot second_payload second_fp
  repo="$(issue_new_repo issue7-evidence-send)"
  prepare_claude_repo "$repo"
  session="issue7-evidence-send-$$"
  log="$issue_tmp_root/issue7-evidence-send.log"
  : >"$log"
  export FAKE_CLAUDE_SUBMIT_LOG="$log"
  unset FAKE_CLAUDE_EXIT_ON_PREPARE FAKE_CLAUDE_PREPARE_DRIFT
  start_fixture "$label" "$repo" "$session" unknown || return
  snapshot="$(observe_snapshot "$label" "$repo" "$session")"
  payload='literal issue-7 prompt selected by the controlling agent'
  expected_fp="$(PAYLOAD="$payload" python3 -c 'import hashlib,os; print("sha256:"+hashlib.sha256(os.environ["PAYLOAD"].encode()).hexdigest())')"

  capture_command claude-code send --repo "$repo" --session "$session" --text "$payload"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "generic send treated advisory runtime state as a hard gate: $COMMAND_OUTPUT"
  else
    RECEIPT="$COMMAND_OUTPUT" EXPECTED_FP="$expected_fp" python3 -c '
import json, os
d=json.loads(os.environ["RECEIPT"])
assert d["result"] == "sent", d
assert d["mutation_performed"] is True, d
assert d["based_on_snapshot"] == "", d
assert d["action_time_snapshot"].startswith("kpr-snapshot-v2:"), d
assert d["observation_changed"] is False, d
assert d["prepared_payload_fingerprint"] == os.environ["EXPECTED_FP"], d
assert d["prepared_clear_editor"] is False, d
' 2>/dev/null || fail "$label" "send receipt omitted or misstated prepared-input facts: $COMMAND_OUTPUT"
  fi

  changed_snapshot="$snapshot"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    capture_command claude-code observe --repo "$repo" --session "$session"
    [[ "$COMMAND_RC" -eq 0 ]] || continue
    changed_observe="$COMMAND_OUTPUT"
    changed_snapshot="$(json_value "$changed_observe" 'd.get("snapshot_id")')"
    [[ "$changed_snapshot" != "$snapshot" ]] && break
    sleep 0.1
  done
  [[ "$changed_snapshot" != "$snapshot" ]] || \
    fail test_issue7_fixture_produces_changed_observation "fixture did not change after first literal transfer"

  second_payload='literal prompt correlated to an older observation'
  second_fp="$(PAYLOAD="$second_payload" python3 -c 'import hashlib,os; print("sha256:"+hashlib.sha256(os.environ["PAYLOAD"].encode()).hexdigest())')"
  capture_command claude-code send --repo "$repo" --session "$session" \
    --if-snapshot "$snapshot" --text "$second_payload"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue7_changed_snapshot_is_audit_evidence "ordinary observation change caused stale refusal: $COMMAND_OUTPUT"
  else
    RECEIPT="$COMMAND_OUTPUT" OLD_SNAPSHOT="$snapshot" CURRENT_SNAPSHOT="$changed_snapshot" EXPECTED_FP="$second_fp" python3 -c '
import json, os
d=json.loads(os.environ["RECEIPT"])
assert d["result"] == "sent", d
assert d["based_on_snapshot"] == os.environ["OLD_SNAPSHOT"], d
assert d["action_time_snapshot"] == os.environ["CURRENT_SNAPSHOT"], d
assert d["observation_changed"] is True, d
assert d["prepared_payload_fingerprint"] == os.environ["EXPECTED_FP"], d
' 2>/dev/null || fail test_issue7_changed_snapshot_is_audit_evidence "changed-observation receipt is not factual: $COMMAND_OUTPUT"
  fi
  EXPECTED="$payload"$'\n'"$second_payload" LOG="$log" python3 -c '
import os
from pathlib import Path
expected="".join(f"submitted={line}\n" for line in os.environ["EXPECTED"].splitlines())
actual=Path(os.environ["LOG"]).read_text(encoding="utf-8")
assert actual == expected, {"actual":actual,"expected":expected}
' 2>/dev/null || fail "$label" "literal prompts did not cross the managed relay exactly once each: $(cat "$log")"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

test_cursor_x0_transports_literal_input() {
  local label=test_issue7_cursor_x0_is_evidence_not_a_send_hard_gate
  local repo session log snapshot payload
  prepare_cursor_authority
  repo="$(issue_new_repo issue7-cursor-x0)"
  session="issue7-cursor-x0-$$"
  log="$issue_tmp_root/issue7-cursor-x0.log"
  : >"$log"
  export CURSOR_AGENT_BIN="$raw_tui"
  export FAKE_CLAUDE_MODE=cursor-ready
  export FAKE_CLAUDE_TITLE='Cursor Agent'
  export FAKE_CLAUDE_SUBMIT_LOG="$log"
  unset FAKE_CLAUDE_EXIT_ON_PREPARE FAKE_CLAUDE_PREPARE_DRIFT

  capture_command cursor-cli start --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public Cursor start failed: $COMMAND_OUTPUT"
    return
  fi
  capture_command cursor-cli observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public Cursor observe failed: $COMMAND_OUTPUT"
    return
  fi
  JSON_INPUT="$COMMAND_OUTPUT" python3 -c '
import json, os, re
d=json.loads(os.environ["JSON_INPUT"])
frame=d["raw_current_frame"]
assert d["hard_evidence"]["cursor_x"] == 0, d
assert d["hard_evidence"]["owned"] and d["hard_evidence"]["repo_match"] and d["hard_evidence"]["platform_match"], d
assert d["relay"]["managed"] is True, d
assert all(marker in frame for marker in ("Cursor Agent", "v2026.08.25-3e8eec8", "Plan, search, build anything", "Run Everything")), d
assert re.fullmatch(r"kpr-snapshot-v2:[0-9a-f]{64}", d.get("snapshot_id") or ""), d
' 2>/dev/null || fail "$label" "Cursor x=0 observation omitted required raw transport evidence: $COMMAND_OUTPUT"
  snapshot="$(json_value "$COMMAND_OUTPUT" 'd.get("snapshot_id")')"
  payload='literal Cursor issue-7 prompt'
  capture_command cursor-cli send --repo "$repo" --session "$session" --text "$payload"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "Cursor x=0/fixed-placeholder advisory blocked generic send: $COMMAND_OUTPUT"
  fi
  [[ "$(cat "$log")" == "submitted=$payload" ]] || \
    fail "$label" "Cursor literal prompt was not submitted exactly once: $(cat "$log")"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
  unset FAKE_CLAUDE_TITLE
}

test_generic_stop_uses_agent_decision() {
  local label=test_issue7_generic_stop_ignores_semantic_advisories
  local repo session snapshot
  repo="$(issue_new_repo issue7-evidence-stop)"
  prepare_claude_repo "$repo"
  session="issue7-evidence-stop-$$"
  : >"$issue_tmp_root/issue7-evidence-stop.log"
  export FAKE_CLAUDE_SUBMIT_LOG="$issue_tmp_root/issue7-evidence-stop.log"
  unset FAKE_CLAUDE_EXIT_ON_PREPARE FAKE_CLAUDE_PREPARE_DRIFT
  start_fixture "$label" "$repo" "$session" unknown || return
  snapshot="$(observe_snapshot "$label" "$repo" "$session")"
  capture_command claude-code stop --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "generic stop treated advisory runtime state as a hard gate: $COMMAND_OUTPUT"
  else
    JSON_INPUT="$COMMAND_OUTPUT" python3 -c \
      'import json,os; d=json.loads(os.environ["JSON_INPUT"]); assert d["result"] == "stopped", d' 2>/dev/null || \
      fail "$label" "generic stop lacked a factual terminal receipt: $COMMAND_OUTPUT"
  fi
  "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1 && \
    fail "$label" "stop receipt returned while the exact session still existed"
}

test_disconnect_never_claims_unproved_restoration() {
  local label=test_issue7_prepare_disconnect_never_claims_unproved_restored_true
  local repo session snapshot payload observation child_pid watcher marker
  repo="$(issue_new_repo issue7-restore-proof)"
  prepare_claude_repo "$repo"
  session="issue7-restore-proof-$$"
  export FAKE_CLAUDE_SUBMIT_LOG="$issue_tmp_root/issue7-restore-proof.log"
  unset FAKE_CLAUDE_EXIT_ON_PREPARE FAKE_CLAUDE_PREPARE_DRIFT
  start_fixture "$label" "$repo" "$session" empty || return
  capture_command claude-code observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail "$label" "public observe failed before fault injection: $COMMAND_OUTPUT"
    return
  fi
  observation="$COMMAND_OUTPUT"
  snapshot="$(json_value "$observation" 'd.get("snapshot_id")')"
  child_pid="$(json_value "$observation" 'd["relay"]["child_pid"]')"
  marker="$issue_tmp_root/issue7-killed-quiesced-child"
  (
    for _ in $(seq 1 2000); do
      state="$(ps -o state= -p "$child_pid" 2>/dev/null | tr -d '[:space:]')"
      if [[ "$state" == T* ]]; then
        kill -KILL "$child_pid" 2>/dev/null || exit 1
        : >"$marker"
        exit 0
      fi
      sleep 0.005
    done
    exit 1
  ) &
  watcher=$!
  payload='disconnect-after-prepare'
  capture_command claude-code send --repo "$repo" --session "$session" \
    --if-snapshot "$snapshot" --require-empty-editor --text "$payload"
  wait "$watcher"
  [[ -f "$marker" ]] || {
    fail "$label" "fault injector never observed and killed the exact quiesced child"
    "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
    return
  }
  [[ "$COMMAND_RC" -ne 0 ]] || fail "$label" "send reported success after the runtime vanished: $COMMAND_OUTPUT"
  RECEIPT="$COMMAND_OUTPUT" python3 -c '
import json, os
raw=os.environ["RECEIPT"]
try:
    d=json.loads(raw)
except json.JSONDecodeError:
    assert "\"restored\": true" not in raw.lower(), raw
else:
    assert d.get("result") != "sent", d
    if d.get("restored") is True:
        proof=d.get("restoration_evidence") or {}
        required=(
            "child_resumed", "pane_input_restored", "relay_responsive",
            "process_group_running", "lease_released", "mutation_lock_released",
        )
        assert all(proof.get(key) is True for key in required), d
' 2>/dev/null || fail "$label" "disconnect path claimed success/restoration without complete re-observed proof: $COMMAND_OUTPUT"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

issue_setup
trap issue_cleanup EXIT
chmod +x "$raw_tui"
export KAOLA_START_TIMEOUT=5

test_generic_send_uses_agent_decision
test_cursor_x0_transports_literal_input
test_generic_stop_uses_agent_decision
test_disconnect_never_claims_unproved_restoration

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #7 evidence-first action acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #7 evidence-first action acceptance: PASS\n'
