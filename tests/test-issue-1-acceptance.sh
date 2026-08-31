#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
failures=0

run_case() {
  local path="$1" rc
  printf '\n== %s ==\n' "${path#$project_root/}"
  set +e
  if [[ "$path" == *.py ]]; then
    python3 "$path"
  else
    bash "$path"
  fi
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    failures=$((failures + 1))
  fi
}

run_case "$project_root/tests/contract/test-generated-skills.py"
run_case "$project_root/tests/contract/test-lifecycle-contract.py"
run_case "$project_root/tests/contract/test-observation-contract.py"
run_case "$project_root/tests/contract/test-direct-transport-contract.py"
run_case "$project_root/tests/contract/test-relay-fence.py"
run_case "$project_root/tests/contract/test-relay-pty.py"
run_case "$project_root/tests/contract/test-relay-escaped-descendant.py"
run_case "$project_root/tests/contract/test-start-deadline.sh"
run_case "$project_root/tests/contract/test-tmux-native-atomicity.sh"
run_case "$project_root/tests/contract/test-relay-guarded-actions.sh"
run_case "$project_root/tests/contract/test-terminal-control-payloads.sh"
run_case "$project_root/tests/contract/test-long-wrapped-send.sh"
run_case "$project_root/tests/contract/test-installer-migration.sh"
run_case "$project_root/tests/contract/test-claude-code-runtime.sh"
run_case "$project_root/tests/contract/test-kaola-tmux.sh"
run_case "$project_root/tests/contract/test-adapters.sh"
run_case "$project_root/tests/contract/test-live-smoke-adapters.sh"
run_case "$project_root/tests/contract/test-cursor-authority-receipt.sh"
run_case "$project_root/tests/contract/test-process-identity.sh"
run_case "$project_root/tests/contract/test-grok-compat.sh"
run_case "$project_root/tests/contract/test-grok-validation-isolation.sh"
run_case "$project_root/tests/contract/test-claude-human-decision.sh"
run_case "$project_root/tests/contract/test-model-policy.sh"

if [[ "$failures" -gt 0 ]]; then
  printf '\nIssue #1 acceptance: %d case(s) failed\n' "$failures" >&2
  exit 1
fi
printf '\nIssue #1 acceptance: PASS\n'
