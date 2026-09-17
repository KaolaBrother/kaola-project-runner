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
for skill_dir in "$repo_root"/skills/*kaola-project-runner; do
  python3 "$repo_root/scripts/validate-skill.py" "$skill_dir"
done
bash -n "$repo_root/scripts/kaola-tmux.sh" "$repo_root"/scripts/adapters/*.sh \
  "$repo_root/scripts/install-local.sh"
bash "$repo_root/tests/contract/test-installer-migration.sh"
bash "$repo_root/tests/contract/test-installer-runtimes.sh"
python3 "$repo_root/tests/contract/test-issue-9-contract.py"
python3 "$repo_root/tests/contract/test-direct-transport-contract.py"
python3 "$repo_root/tests/contract/test-devin-regressions.py"
python3 "$repo_root/tests/contract/test-acp-contract.py"
python3 "$repo_root/tests/contract/test-acp-watch-contract.py"
python3 "$repo_root/tests/contract/test-acp-follow-contract.py"
python3 "$repo_root/tests/contract/test-acp-holder-continue.py"
python3 "$repo_root/tests/contract/test-acp-sweep-contract.py"
python3 "$repo_root/tests/contract/test-issue-33-config-meta.py"
python3 "$repo_root/tests/contract/test-runner-v2.py"
python3 "$repo_root/tests/contract/test-generated-skills.py"
python3 "$repo_root/tests/contract/test-issue-24-opencode-pty-bypass.py"
python3 "$repo_root/tests/contract/test-issue-41-orchestrator.py"
python3 "$repo_root/scripts/kaola-grok-bot-verify.py" "$repo_root/hosts/grok-bot" --repo "$repo_root"
python3 "$repo_root/tests/contract/test-issue-49-grok-bot-host.py"
python3 "$repo_root/tests/contract/test-progressive-disclosure.py"
python3 "$repo_root/tests/contract/test-issue-50-claude-acp-bridge.py"
python3 "$repo_root/tests/contract/test-issue-50-runner-integration.py"
python3 "$repo_root/tests/contract/test-zcode-acp-contract.py"
python3 "$repo_root/tests/contract/test-droid-acp-contract.py"
python3 "$repo_root/tests/contract/test-issue-51-runner-integration.py"
python3 "$repo_root/tests/contract/test-zcode-host-contract.py"
python3 "$repo_root/tests/contract/test-zcode-heartbeat-contract.py"
python3 "$repo_root/tests/contract/test-issue-52-workflow-worktree.py"
python3 "$repo_root/tests/contract/test-issue-64-receipt-bound.py"
# Acceptance line "git diff --check clean": tracked changes must carry no whitespace errors.
if git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$repo_root" diff --check
  git -C "$repo_root" diff --check --cached
fi
