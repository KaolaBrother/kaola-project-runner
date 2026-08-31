#!/usr/bin/env bash
set -u -o pipefail

# Issue #9 acceptance owns the communication boundary. These cases execute
# the real public Runner, tmux server, nested PTY relay, model-policy helper,
# and adapters; only the child CLIs/socket failure are isolated fixtures.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
semantic_runtime="$project_root/tests/fixtures/issue-9/semantic-frame-runtime.py"
catalog_runtime="$project_root/tests/fixtures/issue-9/catalog-missing-runtime.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
COMMAND_OUTPUT=""
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
  set +e
  COMMAND_OUTPUT="$output"
  COMMAND_RC=$rc
}

json_value() {
  local input="$1" expression="$2"
  JSON_INPUT="$input" python3 -c \
    "import json, os; d=json.loads(os.environ['JSON_INPUT']); print($expression)"
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  if ! JSON_INPUT="$input" python3 -c \
      "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression"; then
    fail "$label" "JSON assertion failed: $input"
  fi
}

prepare_repo() {
  local repo="$1"
  mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" "$repo/.claude/kaola-workflow/scripts"
  printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
  printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
  printf '%s\n' 'fixture agent manifest' >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
  printf '%s\n' 'fixture claim hook' >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"
}

cleanup_session() {
  local session="$1"
  "$issue_tmux_bin" kill-session -t "=$session" >/dev/null 2>&1 || true
}

assert_session_present() {
  local label="$1" session="$2"
  "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1 || \
    fail "$label" "exact session is absent"
}

test_editor_surface_is_evidence_only() {
  local repo session log observe snapshot payload stop_session stop_log
  repo="$(issue_new_repo issue9-editor-surface)"
  prepare_repo "$repo"
  chmod +x "$semantic_runtime"

  session="issue9-editor-send-$$"
  log="$issue_tmp_root/issue9-editor-send.log"
  : >"$log"
  export CLAUDE_BIN="$semantic_runtime"
  export FAKE_ISSUE9_SUBMIT_LOG="$log"
  unset FAKE_ISSUE9_CHANGE_FILE

  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_editor_surface_send_start "start failed: $COMMAND_OUTPUT"
    return
  }

  capture_command claude-code observe --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_editor_surface_send_observe "observe failed: $COMMAND_OUTPUT"
    cleanup_session "$session"
    return
  }
  observe="$COMMAND_OUTPUT"
  snapshot="$(json_value "$observe" 'd.get("snapshot_id")')"
  json_assert test_issue9_editor_surface_initial_observation \
    'd["hard_evidence"]["owned"] and d["hard_evidence"]["repo_match"] and d["relay"]["managed"] is True' \
    "$observe"

  payload='agent-selected bytes survive semantic UI classification'
  capture_command claude-code send --repo "$repo" --session "$session" \
    --if-snapshot "$snapshot" --text "$payload"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_editor_surface_send_uses_relay_receipt \
      "editor/UI classification blocked a byte-attested send: $COMMAND_OUTPUT"
  else
    json_assert test_issue9_editor_surface_send_receipt \
      'd["result"] == "sent" and d["mutation_performed"] is True and d["prepared_payload_fingerprint"].startswith("sha256:")' \
      "$COMMAND_OUTPUT"
    grep -Fxq "submitted=$payload" "$log" || \
      fail test_issue9_editor_surface_send_exact_bytes \
        "child did not receive the exact prepared bytes: $(cat "$log")"
  fi
  cleanup_session "$session"

  stop_session="issue9-editor-stop-$$"
  stop_log="$issue_tmp_root/issue9-editor-stop.log"
  : >"$stop_log"
  export FAKE_ISSUE9_SUBMIT_LOG="$stop_log"
  capture_command claude-code start --repo "$repo" --session "$stop_session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_editor_surface_stop_start "start failed: $COMMAND_OUTPUT"
    return
  }
  capture_command claude-code stop --repo "$repo" --session "$stop_session"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_editor_surface_stop_uses_relay_receipt \
      "editor/UI classification blocked graceful stop: $COMMAND_OUTPUT"
  else
    json_assert test_issue9_editor_surface_stop_receipt \
      'd["result"] == "stopped" and d["action"] == "stop"' "$COMMAND_OUTPUT"
    grep -Fxq 'submitted=/exit' "$stop_log" || \
      fail test_issue9_editor_surface_stop_exact_quit \
        "graceful stop did not transfer the adapter quit bytes: $(cat "$stop_log")"
  fi
  cleanup_session "$stop_session"
}

test_snapshot_change_is_audit_evidence() {
  local repo session log change_file observe old_snapshot changed payload
  repo="$(issue_new_repo issue9-snapshot-evidence)"
  prepare_repo "$repo"
  chmod +x "$semantic_runtime"
  session="issue9-snapshot-evidence-$$"
  log="$issue_tmp_root/issue9-snapshot.log"
  change_file="$issue_tmp_root/issue9-snapshot-change"
  : >"$log"
  rm -f "$change_file"
  export CLAUDE_BIN="$semantic_runtime"
  export FAKE_ISSUE9_SUBMIT_LOG="$log"
  export FAKE_ISSUE9_CHANGE_FILE="$change_file"

  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_snapshot_start "start failed: $COMMAND_OUTPUT"
    return
  }
  capture_command claude-code observe --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_snapshot_observe "observe failed: $COMMAND_OUTPUT"
    cleanup_session "$session"
    return
  }
  observe="$COMMAND_OUTPUT"
  old_snapshot="$(json_value "$observe" 'd.get("snapshot_id")')"
  touch "$change_file"
  changed="$observe"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    capture_command claude-code observe --repo "$repo" --session "$session"
    if [[ "$COMMAND_RC" -eq 0 ]]; then
      changed="$COMMAND_OUTPUT"
      [[ "$(json_value "$changed" 'd.get("snapshot_id")')" != "$old_snapshot" ]] && break
    fi
    sleep 0.1
  done
  [[ "$(json_value "$changed" 'd.get("snapshot_id")')" != "$old_snapshot" ]] || \
    fail test_issue9_snapshot_change_is_observed \
      "fixture did not produce a changed snapshot: $changed"

  payload='snapshot changed but controller still chose this literal'
  capture_command claude-code send --repo "$repo" --session "$session" \
    --if-snapshot "$old_snapshot" --text "$payload"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_snapshot_change_does_not_block_transport \
      "stale snapshot was treated as a hard gate: $COMMAND_OUTPUT"
  else
    json_assert test_issue9_snapshot_change_receipt \
      'd["result"] == "sent" and d["based_on_snapshot"] == "'"$old_snapshot"'" and d["observation_changed"] is True' \
      "$COMMAND_OUTPUT"
    grep -Fxq "submitted=$payload" "$log" || \
      fail test_issue9_snapshot_change_exact_bytes \
        "changed-snapshot send did not transfer exact bytes: $(cat "$log")"
  fi
  cleanup_session "$session"
  unset FAKE_ISSUE9_CHANGE_FILE
}

test_decision_and_key_advisories_are_evidence_only() {
  local repo session change_file observe initial_snapshot changed_snapshot decision_id
  local key_log answer_log payload
  repo="$(issue_new_repo issue9-advisory-actions)"
  prepare_repo "$repo"
  chmod +x "$semantic_runtime"

  # A changed observation containing a fully classified decision frame must
  # not prevent an explicitly selected native key from crossing the relay.
  session="issue9-advisory-key-$$"
  change_file="$issue_tmp_root/issue9-advisory-key-change"
  key_log="$issue_tmp_root/issue9-advisory-key.log"
  : >"$key_log"
  rm -f "$change_file"
  export CLAUDE_BIN="$semantic_runtime"
  export FAKE_ISSUE9_SUBMIT_LOG="$key_log"
  export FAKE_ISSUE9_CHANGE_FILE="$change_file"
  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_advisory_key_start "start failed: $COMMAND_OUTPUT"
    unset FAKE_ISSUE9_CHANGE_FILE
    return
  }
  capture_command claude-code observe --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_advisory_key_observe "observe failed: $COMMAND_OUTPUT"
    cleanup_session "$session"
    unset FAKE_ISSUE9_CHANGE_FILE
    return
  }
  initial_snapshot="$(json_value "$COMMAND_OUTPUT" 'd["snapshot_id"]')"
  touch "$change_file"
  changed_snapshot="$initial_snapshot"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    capture_command claude-code observe --repo "$repo" --session "$session"
    if [[ "$COMMAND_RC" -eq 0 ]]; then
      observe="$COMMAND_OUTPUT"
      changed_snapshot="$(json_value "$observe" 'd.get("snapshot_id")')"
      if [[ "$changed_snapshot" != "$initial_snapshot" && "$(json_value "$observe" 'd.get("structured_decision_marker") is not None')" == true ]]; then
        break
      fi
    fi
    sleep 0.1
  done
  [[ "$changed_snapshot" != "$initial_snapshot" ]] || \
    fail test_issue9_advisory_key_snapshot_changed "key fixture did not advance its snapshot"
  capture_command claude-code key --repo "$repo" --session "$session" \
    --if-snapshot "$initial_snapshot" --key escape
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_advisory_key_crosses_relay \
      "decision/activity classification blocked an Agent-selected key: $COMMAND_OUTPUT"
  else
    json_assert test_issue9_advisory_key_receipt \
      'd["result"] == "key-sent" and d["action"] == "key" and d["observation_changed"] is True and d["payload_fingerprint"].startswith("sha256:")' \
      "$COMMAND_OUTPUT"
  fi
  cleanup_session "$session"
  unset FAKE_ISSUE9_CHANGE_FILE

  # The same advisory frame is used while replacing an explicitly selected
  # answer. The decision id is read from current evidence, but it does not
  # authorize or veto the byte-attested replacement.
  session="issue9-advisory-answer-$$"
  change_file="$issue_tmp_root/issue9-advisory-answer-change"
  answer_log="$issue_tmp_root/issue9-advisory-answer.log"
  : >"$answer_log"
  rm -f "$change_file"
  export FAKE_ISSUE9_SUBMIT_LOG="$answer_log"
  export FAKE_ISSUE9_CHANGE_FILE="$change_file"
  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_advisory_answer_start "start failed: $COMMAND_OUTPUT"
    unset FAKE_ISSUE9_CHANGE_FILE
    return
  }
  capture_command claude-code observe --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_advisory_answer_observe "observe failed: $COMMAND_OUTPUT"
    cleanup_session "$session"
    unset FAKE_ISSUE9_CHANGE_FILE
    return
  }
  initial_snapshot="$(json_value "$COMMAND_OUTPUT" 'd["snapshot_id"]')"
  touch "$change_file"
  changed_snapshot="$initial_snapshot"
  decision_id=""
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    capture_command claude-code observe --repo "$repo" --session "$session"
    if [[ "$COMMAND_RC" -eq 0 ]]; then
      observe="$COMMAND_OUTPUT"
      changed_snapshot="$(json_value "$observe" 'd.get("snapshot_id")')"
      decision_id="$(json_value "$observe" 'd.get("structured_decision_marker",{}).get("decision_id","")')"
      if [[ "$changed_snapshot" != "$initial_snapshot" && "$decision_id" == kpr-decision-v1:* ]]; then
        break
      fi
    fi
    sleep 0.1
  done
  [[ "$changed_snapshot" != "$initial_snapshot" && "$decision_id" == kpr-decision-v1:* ]] || \
    fail test_issue9_advisory_answer_evidence "decision fixture did not expose a changed current marker: $observe"
  payload='answer bytes selected despite advisory evidence'
  capture_command claude-code answer --repo "$repo" --session "$session" \
    --decision-id "$decision_id" --if-snapshot "$initial_snapshot" \
    --replace-editor --text "$payload"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_advisory_answer_crosses_relay \
      "decision/editor classification blocked an Agent-selected answer: $COMMAND_OUTPUT"
  else
    json_assert test_issue9_advisory_answer_receipt \
      'd["result"] == "answer-sent" and d["action"] == "answer" and d["decision_id"] == "'"$decision_id"'" and d["based_on_snapshot"] == "'"$initial_snapshot"'" and d["observation_changed"] is True' \
      "$COMMAND_OUTPUT"
    grep -Fxq "submitted=$payload" "$answer_log" || \
      fail test_issue9_advisory_answer_exact_bytes \
        "answer fixture did not receive exact replacement bytes: $(cat "$answer_log")"
  fi
  cleanup_session "$session"
  unset FAKE_ISSUE9_CHANGE_FILE
}

test_transport_control_bytes_are_still_rejected() {
  local repo session log observe offset unsafe
  repo="$(issue_new_repo issue9-control-safety)"
  prepare_repo "$repo"
  chmod +x "$semantic_runtime"
  session="issue9-control-safety-$$"
  log="$issue_tmp_root/issue9-control-safety.log"
  : >"$log"
  export CLAUDE_BIN="$semantic_runtime"
  export FAKE_ISSUE9_SUBMIT_LOG="$log"

  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_control_safety_start "start failed: $COMMAND_OUTPUT"
    return
  }
  capture_command claude-code observe --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_control_safety_observe "observe failed: $COMMAND_OUTPUT"
    cleanup_session "$session"
    return
  }
  observe="$COMMAND_OUTPUT"
  offset="$(json_value "$observe" 'd["relay"]["child_input_offset"]')"
  unsafe=$'literal\rcontrol-byte'
  capture_command claude-code send --repo "$repo" --session "$session" --text "$unsafe"
  [[ "$COMMAND_RC" -ne 0 ]] || \
    fail test_issue9_control_safety_rejects_cr "unsafe CR payload was submitted: $COMMAND_OUTPUT"
  json_assert test_issue9_control_safety_public_refusal \
    'd["result"] == "refused" and d["reason"] == "unsafe-terminal-control"' "$COMMAND_OUTPUT"
  capture_command claude-code observe --repo "$repo" --session "$session"
  if [[ "$COMMAND_RC" -eq 0 ]]; then
    [[ "$(json_value "$COMMAND_OUTPUT" 'd["relay"]["child_input_offset"]')" == "$offset" ]] || \
      fail test_issue9_control_safety_no_child_write "unsafe payload changed child input offset"
  else
    fail test_issue9_control_safety_post_refusal_observe "observe after unsafe refusal failed: $COMMAND_OUTPUT"
  fi
  [[ ! -s "$log" ]] || fail test_issue9_control_safety_no_child_submission "unsafe payload reached child: $(cat "$log")"
  assert_session_present test_issue9_control_safety_session_preserved "$session"
  cleanup_session "$session"
}

replace_socket_with_refusing_endpoint() {
  local socket_path="$1"
  SOCKET_PATH="$socket_path" python3 - <<'PY'
import os
import socket
import stat

path = os.environ["SOCKET_PATH"]
os.unlink(path)
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(path)
os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
# Closing an unlinked/rebound endpoint leaves a same-UID socket node whose
# connect(2) returns ECONNREFUSED, while the real relay still owns its old
# listener inode.
server.close()
PY
}

test_force_stop_contains_only_owned_dead_relay() {
  local repo other_repo session unrelated target_observe socket_path
  local target_child target_pgid target_relay unrelated_pid unrelated_process force_result restart_result
  repo="$(issue_new_repo issue9-dead-relay)"
  other_repo="$(issue_new_repo issue9-dead-relay-other)"
  prepare_repo "$repo"
  chmod +x "$semantic_runtime"
  export CLAUDE_BIN="$semantic_runtime"
  export FAKE_ISSUE9_SUBMIT_LOG="$issue_tmp_root/issue9-dead-relay.log"
  : >"$FAKE_ISSUE9_SUBMIT_LOG"

  unrelated="issue9-unrelated-$$"
  "$issue_tmux_bin" new-session -d -s "$unrelated" -c "$other_repo" sleep 60
  sleep 60 &
  unrelated_process=$!
  unrelated_pid="$unrelated_process"

  session="issue9-dead-relay-$$"
  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_dead_relay_start "start failed: $COMMAND_OUTPUT"
    cleanup_session "$unrelated"
    kill "$unrelated_process" 2>/dev/null || true
    return
  }
  capture_command claude-code observe --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_dead_relay_observe "observe failed: $COMMAND_OUTPUT"
    cleanup_session "$session"
    cleanup_session "$unrelated"
    kill "$unrelated_process" 2>/dev/null || true
    return
  }
  target_observe="$COMMAND_OUTPUT"
  socket_path="$(json_value "$target_observe" 'd["relay"]["socket_path"]')"
  target_child="$(json_value "$target_observe" 'd["relay"]["child_pid"]')"
  target_pgid="$(json_value "$target_observe" 'd["relay"]["child_pgid"]')"
  target_relay="$(json_value "$target_observe" 'd["relay"]["pid"]')"
  [[ -S "$socket_path" ]] || fail test_issue9_dead_relay_fixture_socket "live relay socket missing: $socket_path"
  [[ "$target_relay" =~ ^[0-9]+$ && "$target_child" =~ ^[0-9]+$ && "$target_pgid" =~ ^[0-9]+$ ]] || \
    fail test_issue9_dead_relay_identity_evidence "invalid relay identity: $target_observe"

  replace_socket_with_refusing_endpoint "$socket_path"
  if ! SOCKET_PATH="$socket_path" python3 - <<'PY'
import errno
import os
import socket

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    sock.connect(os.environ["SOCKET_PATH"])
except OSError as exc:
    raise SystemExit(0 if exc.errno == errno.ECONNREFUSED else 1)
else:
    raise SystemExit(1)
finally:
    sock.close()
PY
  then
    fail test_issue9_dead_relay_fixture_refuses_connections \
      "fault injection did not produce ECONNREFUSED at $socket_path"
  fi

  capture_command claude-code stop --repo "$repo" --session "$session" --force
  force_result="$COMMAND_OUTPUT"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_dead_relay_force_stop_succeeds \
      "exact owned force-stop depended on the dead relay: $force_result"
  else
    json_assert test_issue9_dead_relay_force_stop_receipt \
      'd["result"] == "stopped" and d["action"] == "force-stop" and d["final_state"]["session_present"] is False and d["final_state"]["socket_present"] is False' \
      "$force_result"
    [[ ! -e "$socket_path" ]] || \
      fail test_issue9_dead_relay_socket_removed "dead relay socket remains: $socket_path"
  fi
  if "$issue_tmux_bin" has-session -t "=$session" >/dev/null 2>&1; then
    fail test_issue9_dead_relay_session_absent "force-stop returned while exact session remained"
  fi

  capture_command claude-code start --repo "$repo" --session "$session"
  restart_result="$COMMAND_OUTPUT"
  if [[ "$COMMAND_RC" -ne 0 ]]; then
    fail test_issue9_dead_relay_same_name_restart \
      "same-name start failed after dead-relay force recovery: $restart_result"
  else
    json_assert test_issue9_dead_relay_same_name_restart_receipt \
      'd["result"] == "started" and d["owned"] is True and d["repo_match"] is True' \
      "$restart_result"
  fi
  cleanup_session "$session"

  "$issue_tmux_bin" has-session -t "=$unrelated" >/dev/null 2>&1 || \
    fail test_issue9_dead_relay_unrelated_session_survives "force-stop touched unrelated tmux session"
  kill -0 "$unrelated_pid" 2>/dev/null || \
    fail test_issue9_dead_relay_unrelated_process_survives "force-stop touched unrelated process"
  cleanup_session "$unrelated"
  kill "$unrelated_process" 2>/dev/null || true
  wait "$unrelated_process" 2>/dev/null || true
}

test_dead_relay_identity_boundaries() {
  local repo other_repo unowned session output pane_id multipane
  repo="$(issue_new_repo issue9-identity-boundaries)"
  other_repo="$(issue_new_repo issue9-identity-boundaries-other)"
  prepare_repo "$repo"
  chmod +x "$semantic_runtime"
  export CLAUDE_BIN="$semantic_runtime"
  export FAKE_ISSUE9_SUBMIT_LOG="$issue_tmp_root/issue9-identity-boundaries.log"
  : >"$FAKE_ISSUE9_SUBMIT_LOG"

  unowned="issue9-unowned-$$"
  "$issue_tmux_bin" new-session -d -s "$unowned" -c "$repo" sleep 60
  capture_command claude-code stop --repo "$repo" --session "$unowned" --force
  [[ "$COMMAND_RC" -ne 0 ]] || \
    fail test_issue9_force_stop_rejects_unowned "unowned session was terminated: $COMMAND_OUTPUT"
  "$issue_tmux_bin" has-session -t "=$unowned" >/dev/null 2>&1 || \
    fail test_issue9_force_stop_preserves_unowned "unowned session disappeared"
  cleanup_session "$unowned"

  session="issue9-foreign-repo-$$"
  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_foreign_repo_setup "start failed: $COMMAND_OUTPUT"
    return
  }
  capture_command claude-code stop --repo "$other_repo" --session "$session" --force
  output="$COMMAND_OUTPUT"
  [[ "$COMMAND_RC" -ne 0 ]] || \
    fail test_issue9_force_stop_rejects_repo_mismatch "foreign repository stopped target: $output"
  assert_session_present test_issue9_force_stop_preserves_repo_mismatch "$session"
  cleanup_session "$session"

  session="issue9-foreign-platform-$$"
  capture_command claude-code start --repo "$repo" --session "$session"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_foreign_platform_setup "start failed: $COMMAND_OUTPUT"
    return
  }
  export GROK_BIN="$semantic_runtime"
  capture_command grok stop --repo "$repo" --session "$session" --force
  [[ "$COMMAND_RC" -ne 0 ]] || \
    fail test_issue9_force_stop_rejects_platform_mismatch "foreign platform stopped target: $COMMAND_OUTPUT"
  assert_session_present test_issue9_force_stop_preserves_platform_mismatch "$session"
  cleanup_session "$session"

  multipane="issue9-multipane-$$"
  capture_command claude-code start --repo "$repo" --session "$multipane"
  [[ "$COMMAND_RC" -eq 0 ]] || {
    fail test_issue9_multipane_setup "start failed: $COMMAND_OUTPUT"
    return
  }
  pane_id="$($issue_tmux_bin list-panes -t "=$multipane" -F '#{pane_id}' | head -1)"
  "$issue_tmux_bin" split-window -t "$pane_id" -c "$repo" sleep 60 >/dev/null
  capture_command claude-code stop --repo "$repo" --session "$multipane" --force
  [[ "$COMMAND_RC" -ne 0 ]] || \
    fail test_issue9_force_stop_rejects_multipane "multi-pane target was terminated: $COMMAND_OUTPUT"
  assert_session_present test_issue9_force_stop_preserves_multipane "$multipane"
  cleanup_session "$multipane"
}

catalog_model_ids() {
  case "$1" in
    grok) printf '%s\n' grok-4.6 ;;
    claude-code) printf '%s\n' opus ;;
    opencode) printf '%s\n' zhipuai-coding-plan/glm-5.3 ;;
    kimi-cli) printf '%s\n' kimi-code/k3 ;;
    cursor-cli) printf '%s\n' cursor-grok-4.6-xhigh ;;
  esac
}

test_catalog_missing_model_reaches_cli() {
  local repo platform binary_env default_id explicit session output argv_log
  repo="$(issue_new_repo issue9-catalog-missing)"
  chmod +x "$catalog_runtime"
  export KAOLA_START_TIMEOUT=5

  for platform in grok claude-code opencode kimi-cli cursor-cli; do
    binary_env=""
    case "$platform" in
      grok) binary_env=GROK_BIN ;;
      claude-code) binary_env=CLAUDE_BIN ;;
      opencode) binary_env=OPENCODE_BIN ;;
      kimi-cli) binary_env=KIMI_BIN ;;
      cursor-cli) binary_env=CURSOR_AGENT_BIN ;;
    esac
    printf -v "$binary_env" '%s' "$catalog_runtime"
    export "$binary_env"
    export FAKE_ISSUE9_RUNTIME_NAME="$platform"
    argv_log="$issue_tmp_root/issue9-$platform-argv.log"
    : >"$argv_log"
    export FAKE_ISSUE9_ARGV_LOG="$argv_log"

    explicit="issue9/catalog-missing-explicit"
    session="issue9-catalog-explicit-$platform-$$"
    capture_command "$platform" start --repo "$repo" --session "$session" --model "$explicit"
    output="$COMMAND_OUTPUT"
    if [[ "$COMMAND_RC" -ne 0 ]]; then
      fail "test_issue9_${platform}_explicit_catalog_missing_reaches_cli" \
        "Runner refused before CLI could classify explicit model: $output"
    else
      json_assert "test_issue9_${platform}_explicit_catalog_missing_evidence" \
        'd["model"]["requested_model_name"] == "'"$explicit"'" and d["model"]["actual_runtime_model_id"] == "'"$explicit"'" and d["model"]["model_verified"] in (True, "true") and d["model"]["model_evidence_provenance"]["catalog_probe"]["state"] == "readable" and "'"$explicit"'" not in d["model"]["model_evidence_provenance"]["catalog_probe"]["available_models"] and "CLI accepted catalog-missing model: '"$explicit"'" in d["raw_current_frame"]' \
        "$output"
      grep -Fq $'event=launch\tselected='"$explicit"$'\t' "$argv_log" || \
        fail "test_issue9_${platform}_explicit_model_argv" \
          "exact explicit model was not passed to CLI: $(cat "$argv_log")"
      grep -Fq 'known/' "$argv_log" && \
        fail "test_issue9_${platform}_explicit_model_no_catalog_fallback" \
          "Runner launched catalog fallback: $(cat "$argv_log")"
    fi
    cleanup_session "$session"

    default_id="$(catalog_model_ids "$platform")"
    session="issue9-catalog-default-$platform-$$"
    : >"$argv_log"
    capture_command "$platform" start --repo "$repo" --session "$session"
    output="$COMMAND_OUTPUT"
    if [[ "$COMMAND_RC" -ne 0 ]]; then
      fail "test_issue9_${platform}_default_catalog_missing_reaches_cli" \
        "Runner refused before CLI could classify default model: $output"
    else
      json_assert "test_issue9_${platform}_default_catalog_missing_evidence" \
        'd["model"]["requested_model_name"] and d["model"]["actual_runtime_model_id"] == "'"$default_id"'" and d["model"]["model_evidence_provenance"]["catalog_probe"]["state"] == "readable" and "'"$default_id"'" not in d["model"]["model_evidence_provenance"]["catalog_probe"]["available_models"] and "CLI accepted catalog-missing model: '"$default_id"'" in d["raw_current_frame"]' \
        "$output"
      grep -Fq $'event=launch\tselected='"$default_id"$'\t' "$argv_log" || \
        fail "test_issue9_${platform}_default_model_argv" \
          "exact Runner default was not passed to CLI: $(cat "$argv_log")"
    fi
    cleanup_session "$session"
  done
}

issue_setup
trap issue_cleanup EXIT

export KAOLA_START_TIMEOUT=5
test_editor_surface_is_evidence_only
test_snapshot_change_is_audit_evidence
test_decision_and_key_advisories_are_evidence_only
test_transport_control_bytes_are_still_rejected
test_force_stop_contains_only_owned_dead_relay
test_dead_relay_identity_boundaries
test_catalog_missing_model_reaches_cli

if [[ "$failures" -gt 0 ]]; then
  printf 'Issue #9 communication-only acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Issue #9 communication-only acceptance: PASS\n'
