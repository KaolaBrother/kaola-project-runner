#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"

# The whole suite runs in a controlled temporary HOME: no Codex (or other
# runtime) configuration is required, and real user configuration is never
# read or modified.
sandbox_home="$(mktemp -d "${TMPDIR:-/tmp}/kaola-validate-home.XXXXXX")"
trap 'rm -rf "$sandbox_home"' EXIT
export HOME="$sandbox_home"
unset CODEX_HOME CLAUDE_CONFIG_DIR DEVIN_CONFIG_DIR

python3 "$repo_root/scripts/render-skills.py" --check
for skill_dir in "$repo_root"/skills/*-kaola-project-runner; do
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
python3 "$repo_root/tests/contract/test-runner-v2.py"
python3 "$repo_root/tests/contract/test-generated-skills.py"
python3 "$repo_root/tests/contract/test-issue-24-opencode-pty-bypass.py"
