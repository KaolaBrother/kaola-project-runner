#!/usr/bin/env bash
set -euo pipefail

# A start timeout is a wall-clock deadline. A slow complete observation must
# not be multiplied by a fixed number of polling iterations.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

issue_setup
trap issue_cleanup EXIT

repo="$(issue_new_repo start-deadline-repo)"
mkdir -p "$repo/.claude/commands" "$repo/.claude/agents" \
  "$repo/.claude/kaola-workflow/scripts"
printf '%s\n' workflow-next >"$repo/.claude/commands/workflow-next.md"
printf '%s\n' finalize >"$repo/.claude/commands/kaola-workflow-finalize.md"
printf '%s\n' manifest >"$repo/.claude/agents/.kaola-workflow-agent-manifest"
printf '%s\n' claim >"$repo/.claude/kaola-workflow/scripts/kaola-workflow-claim.js"

runtime="$issue_tmp_root/no-tui-claude"
apply_runtime='#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --version ]]; then printf "%s\\n" "claude fixture 1.0"; exit 0; fi
printf "%s\\n" "booting fixture without an attested Claude TUI"
while IFS= read -r _line; do :; done'
printf '%s\n' "$apply_runtime" >"$runtime"
chmod +x "$runtime"

session="start-deadline-$$"
export CLAUDE_BIN="$runtime" KAOLA_START_TIMEOUT=1
started_ms="$(python3 -c 'import time; print(time.time_ns() // 1000000)')"
set +e
output="$(TMUX_BIN="$issue_tmux_bin" bash "$runner" claude-code start \
  --repo "$repo" --session "$session" 2>&1)"
rc=$?
set -e
finished_ms="$(python3 -c 'import time; print(time.time_ns() // 1000000)')"
elapsed_ms=$(( finished_ms - started_ms ))

[[ "$rc" -eq 2 ]] || {
  printf 'RED: expected start-pending exit 2, got %s: %s\n' "$rc" "$output" >&2
  exit 1
}
grep -Fq '"result": "start-pending"' <<<"$output" || {
  printf 'RED: missing start-pending receipt: %s\n' "$output" >&2
  exit 1
}
(( elapsed_ms < 8000 )) || {
  printf 'RED: one-second start deadline took %sms\n' "$elapsed_ms" >&2
  exit 1
}

printf 'start deadline acceptance: PASS (%sms)\n' "$elapsed_ms"
