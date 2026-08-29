#!/usr/bin/env bash
set -euo pipefail

# Cursor authority receipt boundary.  The helper is deliberately a fake Node
# program under a temporary CURSOR_HOME: this test proves which authority bytes
# the real adapter validates and whether it executes an unproved helper.

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

make_cursor_helper() {
  local path="$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'CURSOR_SURFACE'
#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const log = process.env.CURSOR_HELPER_LOG;
if (log) fs.appendFileSync(log, JSON.stringify(args) + "\n");

if (args.includes("--doctor")) {
  process.stdout.write(JSON.stringify({authority: {receipt_status: "valid", freshness: "current"}}) + "\n");
  process.exit(0);
}

const index = args.indexOf("--ensure-target");
if (index !== -1) {
  const target = args[index + 1];
  if (!target || !path.isAbsolute(target)) process.exit(2);
  process.stdout.write(JSON.stringify({status: "current", scope: "project", target, files: 2}) + "\n");
  process.exit(0);
}
process.exit(2);
CURSOR_SURFACE
  chmod +x "$path"
}

write_authority_receipt() {
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
    json.dumps({"schema_version": 1, "kind": "cursor_global_authority", "forge": "github", "files": files}) + "\n",
    encoding="utf-8",
)
PY
}

assert_helper_record() {
  CURSOR_ROOT="$CURSOR_HOME" python3 - <<'PY' || {
import hashlib
import json
import os
import pathlib
import stat

root = pathlib.Path(os.environ["CURSOR_ROOT"])
receipt = json.loads((root / "kaola-workflow/cursor-authority.json").read_text(encoding="utf-8"))
relative = "kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
record = receipt.get("files", {}).get(relative)
helper = root / relative
assert record is not None, receipt
assert record["sha256"] == hashlib.sha256(helper.read_bytes()).hexdigest(), record
assert record["mode"] == stat.S_IMODE(helper.stat().st_mode), record
assert [key for key in receipt["files"] if key.endswith("kaola-workflow-cursor-surface.js")] == [relative]
PY
    fail test_cursor_authority_helper_record_exact "authority receipt does not bind exact helper path/hash/mode"
  }
}

expect_preflight_refusal_without_helper_execution() {
  local label="$1" output rc
  set +e
  output="$(run_runner cursor-cli preflight --repo "$repo" --session "authority-$label-$$" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "$label" "preflight accepted invalid helper authority: $output"
  [[ ! -s "$CURSOR_HELPER_LOG" ]] || fail "$label" "invalid helper was executed: $(cat "$CURSOR_HELPER_LOG")"
}

issue_setup
trap issue_cleanup EXIT

export CURSOR_HOME="$issue_tmp_root/cursor-home"
export CURSOR_HELPER_LOG="$issue_tmp_root/cursor-helper-execution.log"
mkdir -p "$CURSOR_HOME/commands" "$CURSOR_HOME/kaola-workflow"
printf '%s\n' 'workflow-next fixture authority bytes' >"$CURSOR_HOME/commands/workflow-next.md"
printf '%s\n' 'finalize fixture authority bytes' >"$CURSOR_HOME/commands/kaola-workflow-finalize.md"
make_cursor_helper
write_authority_receipt
cursor_bin="$(make_cursor_binary)"
export CURSOR_AGENT_BIN="$cursor_bin"
repo="$(issue_new_repo cursor-authority-repo)"

: >"$CURSOR_HELPER_LOG"
valid_preflight="$(run_runner cursor-cli preflight --repo "$repo" --session authority-valid-$$ 2>&1)" || \
  fail test_cursor_authority_helper_record_exact "valid authority preflight failed: $valid_preflight"
json_assert test_cursor_authority_helper_record_exact "d['result'] == 'ready' and d['platform'] == 'cursor-cli'" "$valid_preflight"
assert_helper_record
grep -q -- '--doctor' "$CURSOR_HELPER_LOG" || fail test_cursor_authority_helper_record_exact "valid helper was not used for the read-only doctor"

# Removing the helper record must fail before the helper is even read.  The
# executable remains on disk to distinguish an omitted receipt record from a
# missing helper path.
write_authority_receipt
AUTHORITY="$CURSOR_HOME/kaola-workflow/cursor-authority.json" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["AUTHORITY"])
receipt = json.loads(path.read_text(encoding="utf-8"))
receipt["files"].pop("kaola-workflow/scripts/kaola-workflow-cursor-surface.js")
path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
PY
: >"$CURSOR_HELPER_LOG"
expect_preflight_refusal_without_helper_execution test_cursor_authority_omitted_helper_not_executed

# Restore the reviewed record, then alter helper bytes and verify that the
# adapter validates the receipt before invoking Node.
make_cursor_helper
write_authority_receipt
printf '%s\n' '// intentional authority tamper' >>"$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
: >"$CURSOR_HELPER_LOG"
expect_preflight_refusal_without_helper_execution test_cursor_authority_tampered_helper_not_executed

# A mode-only drift is also an authority failure.  Node can still read a
# non-executable file, so a helper execution log proves ordering rather than
# relying on the OS permission error.
make_cursor_helper
write_authority_receipt
chmod 0644 "$CURSOR_HOME/kaola-workflow/scripts/kaola-workflow-cursor-surface.js"
: >"$CURSOR_HELPER_LOG"
expect_preflight_refusal_without_helper_execution test_cursor_authority_mode_mismatch_not_executed

if [[ "$failures" -gt 0 ]]; then
  printf 'Cursor authority receipt acceptance: %d failure(s)\n' "$failures" >&2
  exit 1
fi
printf 'Cursor authority receipt acceptance: PASS\n'
