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
run_case "$project_root/tests/contract/test-installer-migration.sh"
run_case "$project_root/tests/contract/test-kaola-tmux.sh"
run_case "$project_root/tests/contract/test-adapters.sh"
run_case "$project_root/tests/contract/test-live-smoke-adapters.sh"
run_case "$project_root/tests/contract/test-grok-compat.sh"

if [[ "$failures" -gt 0 ]]; then
  printf '\nIssue #1 acceptance: %d case(s) failed\n' "$failures" >&2
  exit 1
fi
printf '\nIssue #1 acceptance: PASS\n'
