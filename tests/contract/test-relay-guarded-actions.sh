#!/usr/bin/env bash
set -u -o pipefail

# The original Issue #6 public guarded-action scenario is retained as the
# detailed fixture oracle. Its assertions are now schema-v2/relay-aware, and
# this architecture-named entrypoint keeps the acceptance command stable for
# focused validation. The delegated scenario invokes only the public Runner
# observe/send/stop/answer commands for action paths.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
if [[ ! -f "$project_root/scripts/kaola-pane-relay.py" ]]; then
  printf 'RED: test_issue6_relay_guarded_actions_requires_managed_relay — missing %s\n' \
    "$project_root/scripts/kaola-pane-relay.py" >&2
  exit 1
fi
exec bash "$project_root/tests/contract/test-guarded-actions.sh" "$@"
