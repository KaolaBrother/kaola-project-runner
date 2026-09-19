#!/bin/bash
# Issue #92: prove test_the_retention_has_no_retry_deadline actually CATCHES a
# give-up cap. Three cap forms that all passed the earlier regex-based version
# of that test are injected into a scratch copy of the holder; each must fail.
# Usage: 04-no-cap-mutation-probe.sh /path/to/checkout
set -e
SRC="$1"; WORK=$(mktemp -d)
cp -R "$SRC"/. "$WORK"/
cd "$WORK"
run_case () {
  python3 - "$1" "$SRC" <<'PYEOF'
import sys, shutil
from pathlib import Path
which, src = sys.argv[1], sys.argv[2]
shutil.copy(f"{src}/scripts/kaola-acp-holder.py", "scripts/kaola-acp-holder.py")
p = Path("scripts/kaola-acp-holder.py"); t = p.read_text()
if which == "attempt-cap":
    old = '            owed = error in CARRIER_UNDELIVERED_CODES'
    new = '            owed = error in CARRIER_UNDELIVERED_CODES and wake["attempts"] < 20'
elif which == "separate-cap":
    old = '            owed = error in CARRIER_UNDELIVERED_CODES'
    new = ('            owed = error in CARRIER_UNDELIVERED_CODES\n'
           '            if wake["attempts"] > 20:\n'
           '                owed = False')
elif which == "clock-cap":
    old = '''            self.undelivered_wakes[key] = {"params": params, "attempts": 1,
                                           "last_error": error, "logged_error": error}'''
    new = '''            self.undelivered_wakes[key] = {"params": params, "attempts": 1,
                                           "last_error": error, "logged_error": error,
                                           "first_at": time.monotonic()}'''
assert old in t, which
p.write_text(t.replace(old, new, 1))
print(f"mutated: {which}")
PYEOF
  python3 tests/contract/test-issue-92-permission-wake-recovery.py \
    test_the_retention_has_no_retry_deadline 2>&1 | tail -2
  echo
}
for c in attempt-cap separate-cap clock-cap; do echo "### $c"; run_case "$c"; done
rm -rf "$WORK"
