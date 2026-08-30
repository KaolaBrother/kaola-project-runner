#!/usr/bin/env bash
set -euo pipefail

# Cursor authority is optional evidence. Preflight may report its presence but
# must never execute the helper or gate the exact CLI communication transport on
# receipt schema, hashes, modes, or freshness.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
runner="$project_root/scripts/kaola-tmux.sh"
# shellcheck source=../lib/issue-1-test-lib.sh
source "$project_root/tests/lib/issue-1-test-lib.sh"

failures=0
fail() {
  printf 'RED: %s — %s\n' "$1" "$2" >&2
  failures=$((failures + 1))
}

json_assert() {
  local label="$1" expression="$2" input="$3"
  JSON_INPUT="$input" python3 -c "import json, os; d=json.loads(os.environ['JSON_INPUT']); assert $expression, d" || \
    fail "$label" "JSON assertion failed: $input"
}

run_runner() {
  TMUX_BIN="$issue_tmux_bin" bash "$runner" "$@"
}

make_cursor_binary() {
  local path="$issue_tmp_root/cursor-authority-fake"
  cat >"$path" <<'FAKE_CURSOR'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --version ]]; then
  printf '%s\n' 'cursor-agent-fixture 1.0.0'
else
  printf '%s\n' 'Cursor Agent' '→ Plan, search, build anything'
  while IFS= read -r _line; do :; done
fi
FAKE_CURSOR
  chmod +x "$path"
  printf '%s\n' "$path"
}

make_trapping_helper() {
  local path="$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'CURSOR_SURFACE'
#!/usr/bin/env node
require('fs').appendFileSync(process.env.CURSOR_HELPER_LOG, 'EXECUTED\n');
process.exit(99);
CURSOR_SURFACE
  chmod +x "$path"
}

assert_advisory_ready() {
  local label="$1" expected_authority="$2" output
  : >"$CURSOR_HELPER_LOG"
  output="$(run_runner cursor-cli preflight --repo "$repo" --session "authority-$label-$$" 2>&1)" || \
    fail "$label" "preflight blocked CLI communication: $output"
  json_assert "$label" "d['result'] == 'ready' and d['platform'] == 'cursor-cli' and d['workflow_next'] and d['kaola_workflow_finalize'] and d['project_materialization'] == 'not-present' and 'authority=$expected_authority' in d['detail']" "$output"
  [[ ! -s "$CURSOR_HELPER_LOG" ]] || fail "$label" "advisory helper was executed: $(cat "$CURSOR_HELPER_LOG")"
}

issue_setup
trap issue_cleanup EXIT

export CURSOR_HOME="$issue_tmp_root/cursor-home"
export CURSOR_HELPER_LOG="$issue_tmp_root/cursor-helper-execution.log"
mkdir -p "$CURSOR_HOME/commands" "$CURSOR_HOME/kaola-workflow"
printf '%s\n' 'workflow-next fixture bytes' >"$CURSOR_HOME/commands/workflow-next.md"
printf '%s\n' 'finalize fixture bytes' >"$CURSOR_HOME/commands/kaola-workflow-finalize.md"
make_trapping_helper
cursor_bin="$(make_cursor_binary)"
export CURSOR_AGENT_BIN="$cursor_bin"
repo="$(issue_new_repo cursor-authority-repo)"

# Even a malformed, stale, or mismatched receipt is only reported as present.
printf '%s\n' '{not-json' >"$CURSOR_HOME/kaola-workflow/cursor-authority.json"
assert_advisory_ready malformed_receipt present

printf '%s\n' '{"schema_version":999,"files":{"wrong":{"sha256":"bad","mode":0}}}' >"$CURSOR_HOME/kaola-workflow/cursor-authority.json"
chmod 0644 "$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
assert_advisory_ready mismatched_receipt present

rm "$CURSOR_HOME/kaola-workflow/cursor-authority.json"
assert_advisory_ready missing_receipt missing

if [[ "$failures" -gt 0 ]]; then
  printf 'Cursor authority advisory acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Cursor authority advisory acceptance: PASS\n'
