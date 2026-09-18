#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"

# The whole suite runs in a controlled temporary HOME: no Codex (or other
# runtime) configuration is required, and real user configuration is never
# read or modified.
sandbox_home="$(mktemp -d "${TMPDIR:-/tmp}/kaola-validate-home.XXXXXX")"
# Issue #63: the suites run under one validate-owned TMPDIR root, so every
# fixture temp root and the shared kaola-<uid>-acp ACP socket dir — and with
# them every spawned holder's --record-dir/--socket — lands under it. An
# interrupted or early-exited run (set -e, SIGINT, SIGTERM) then sweeps
# exactly its own holders on the way out instead of leaking them re-parented
# to launchd. The root is short and flat because ACP admin sockets live
# under it and AF_UNIX sun_path is ~104 bytes on macOS.
validate_tmp="$(mktemp -d "/tmp/kaola-val.XXXXXX")"
cleanup_done=""
cleanup() {
  if [[ -z "$cleanup_done" ]]; then
    cleanup_done=1
    # Sweep before removal and never let a nonzero sweep block the removal.
    python3 "$repo_root/scripts/kaola-acp-sweep.py" --root "$validate_tmp" || true
    rm -rf "$validate_tmp" "$sandbox_home" || true
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
export HOME="$sandbox_home"
export TMPDIR="$validate_tmp"
unset CODEX_HOME CLAUDE_CONFIG_DIR DEVIN_CONFIG_DIR

python3 "$repo_root/scripts/render-skills.py" --check
for skill_dir in "$repo_root"/skills/*kaola-project-runner "$repo_root"/skills/kaola-delegator; do
  python3 "$repo_root/scripts/validate-skill.py" "$skill_dir"
done
bash -n "$repo_root/scripts/kaola-tmux.sh" "$repo_root"/scripts/adapters/*.sh \
  "$repo_root/scripts/install-local.sh"
bash "$repo_root/tests/contract/test-installer-migration.sh"
bash "$repo_root/tests/contract/test-installer-runtimes.sh"

# The contract suites dominate validate wall time (measured ~200 s combined).
# Every suite is a self-contained fixture under the validate-owned TMPDIR
# root — its temp dirs, ACP record dirs, and the shared kaola-<uid>-acp
# socket dir all descend from $validate_tmp — so they run as two balanced
# lanes instead of one serial list. Nothing is skipped: each suite runs the
# identical command it ran serially, its log is replayed in the original
# order after both lanes finish, and the logs live under $validate_tmp so
# the Issue #63 sweep still covers exactly this invocation's holders and the
# root removal takes the logs with it. A lane reports FAILED per failing
# suite but still runs every suite, and the script exits nonzero only after
# every suite has run; a suite that somehow left no log is reported SKIPPED
# rather than letting a missing-log cat error abort the replay (Issue #83).
python_suites_all=(
  "test-issue-78-heredoc-deadlock.py"
  "test-issue-9-contract.py"
  "test-direct-transport-contract.py"
  "test-devin-regressions.py"
  "test-acp-contract.py"
  "test-acp-watch-contract.py"
  "test-acp-follow-contract.py"
  "test-acp-holder-continue.py"
  "test-acp-sweep-contract.py"
  "test-issue-33-config-meta.py"
  "test-runner-v2.py"
  "test-generated-skills.py"
  "test-issue-24-opencode-pty-bypass.py"
  "test-issue-41-orchestrator.py"
  "test-issue-68-heartbeat-snapshot.py"
  "test-issue-72-session-naming.py"
  "test-issue-73-canonical-root.py"
  "test-issue-49-grok-bot-host.py"
  "test-progressive-disclosure.py"
  "test-issue-50-claude-acp-bridge.py"
  "test-issue-50-runner-integration.py"
  "test-zcode-acp-contract.py"
  "test-droid-acp-contract.py"
  "test-issue-51-runner-integration.py"
  "test-zcode-host-contract.py"
  "test-zcode-heartbeat-contract.py"
  "test-issue-52-workflow-worktree.py"
  "test-issue-64-receipt-bound.py"
  "test-issue-65-steering.py"
  "test-issue-65-steer-race.py"
  "test-issue-65-host-contract.py"
  "test-issue-70-binding-fact.py"
  "test-issue-76-permission-wake.py"
  "test-issue-79-zcode-312.py"
  "test-issue-83-lane-failure-visibility.py"
  "test-issue-74-kaola-delegator.py"
  "test-issue-84-zcode-native-resume.py"
  "test-issue-85-zcode-resume-advertised-model.py"
  "test-issue-86-delegator-quota.py"
  "test-issue-88-permission-defaults.py"
  "test-issue-90-event-confirmation-race.py"
)
python_suites_a=(
  "test-issue-79-zcode-312.py"
  "test-issue-84-zcode-native-resume.py"
  "test-issue-85-zcode-resume-advertised-model.py"
  "test-issue-65-steering.py"
  "test-acp-contract.py"
  "test-zcode-heartbeat-contract.py"
  "test-issue-76-permission-wake.py"
  "test-acp-follow-contract.py"
  "test-progressive-disclosure.py"
  "test-droid-acp-contract.py"
  "test-issue-41-orchestrator.py"
  "test-issue-68-heartbeat-snapshot.py"
  "test-issue-72-session-naming.py"
  "test-runner-v2.py"
  "test-direct-transport-contract.py"
  "test-issue-9-contract.py"
  "test-issue-83-lane-failure-visibility.py"
  "test-issue-88-permission-defaults.py"
)
python_suites_b=(
  "test-issue-78-heredoc-deadlock.py"
  "test-issue-33-config-meta.py"
  "test-issue-50-runner-integration.py"
  "test-issue-49-grok-bot-host.py"
  "test-acp-watch-contract.py"
  "test-acp-holder-continue.py"
  "test-zcode-host-contract.py"
  "test-issue-50-claude-acp-bridge.py"
  "test-issue-51-runner-integration.py"
  "test-acp-sweep-contract.py"
  "test-zcode-acp-contract.py"
  "test-generated-skills.py"
  "test-devin-regressions.py"
  "test-issue-52-workflow-worktree.py"
  "test-issue-24-opencode-pty-bypass.py"
  "test-issue-64-receipt-bound.py"
  "test-issue-65-steer-race.py"
  "test-issue-65-host-contract.py"
  "test-issue-70-binding-fact.py"
  "test-issue-73-canonical-root.py"
  "test-issue-74-kaola-delegator.py"
  "test-issue-86-delegator-quota.py"
  "test-issue-90-event-confirmation-race.py"
)
run_suite_lane() {
  local status=0
  for suite in "$@"; do
    if ! python3 "$repo_root/tests/contract/$suite" >"$validate_tmp/$suite.log" 2>&1; then
      printf 'FAILED: %s\n' "$suite"
      status=1
    fi
  done
  return "$status"
}
run_suite_lane "${python_suites_a[@]}" & lane_a=$!
run_suite_lane "${python_suites_b[@]}" & lane_b=$!
python_status=0
wait "$lane_a" || python_status=1
wait "$lane_b" || python_status=1
for suite in "${python_suites_all[@]}"; do
  if [[ -f "$validate_tmp/$suite.log" ]]; then
    cat "$validate_tmp/$suite.log"
  else
    printf 'SKIPPED: %s (no log; execution status unknown)\n' "$suite"
    python_status=1
  fi
done
if (( python_status )); then
  exit 1
fi
python3 "$repo_root/scripts/kaola-grok-bot-verify.py" "$repo_root/hosts/grok-bot" --repo "$repo_root"

# Acceptance line "git diff --check clean": tracked changes must carry no whitespace errors.
if git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$repo_root" diff --check
  git -C "$repo_root" diff --check --cached
fi
