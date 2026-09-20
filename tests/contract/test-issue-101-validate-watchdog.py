#!/usr/bin/env python3
"""Issue #101: every validate suite runs under a watchdog that kills and reports.

``./scripts/validate.sh`` hung for 13 minutes inside ``install-local.sh`` and had
to be killed by hand, and the process was gone before anyone could ``sample`` it.
The structural repair (no here-documents in the installer) is pinned by
``test-issue-78-heredoc-deadlock.py``; this file pins the second half of the
remedy: ``scripts/validate-watchdog.sh`` runs one suite in its foreground and,
once the budget elapses with the suite still alive, writes a receipt (process
tree, ``lsof -p`` and ``sample`` of the deepest childless process), kills the
whole tree deepest-first, names the receipt in a FAILED line, and exits 124.
A suite that finishes gets its own exit status back and leaves no receipt.
macOS ships no timeout(1), which is why the helper exists.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import unittest
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
WATCHDOG = PROJECT / "scripts" / "validate-watchdog.sh"
VALIDATE = PROJECT / "scripts" / "validate.sh"


def run_watchdog(receipt_dir: Path, label: str, budget: int, interval: int,
                 *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(WATCHDOG), "--label", label, "--budget", str(budget),
         "--interval", str(interval), "--receipt-dir", str(receipt_dir), "--", *command],
        capture_output=True, text=True, timeout=120, cwd=PROJECT)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class TestValidateWatchdog(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-issue-101-")
        self.receipts = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_a_hung_suite_is_killed_diagnosed_and_reported(self) -> None:
        started = time.monotonic()
        result = run_watchdog(self.receipts, "hung", 2, 1, "bash", "-c", "sleep 300")
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 124, result.stderr)
        receipt = self.receipts / "hung.watchdog.txt"
        self.assertTrue(receipt.is_file(), "no receipt written")
        self.assertIn(
            f"FAILED: hung (watchdog: still running after 2 s; process tree killed; receipt {receipt})",
            result.stderr)
        text = receipt.read_text(encoding="utf-8")
        for section in ("watchdog receipt: hung", "== process tree below the owner (ps) ==",
                        "== lsof -p ", "== sample "):
            self.assertIn(section, text)
        leaf = re.search(r"^leaf pid: (\d+)$", text, re.M)
        self.assertIsNotNone(leaf, text)
        self.assertFalse(alive(int(leaf.group(1))), "the hung leaf survived the watchdog")
        self.assertIn("sleep 300", text, "the receipt does not show the hung process")
        self.assertLess(elapsed, 60, f"trip took {elapsed:.0f}s")
        self.assertEqual(sorted(p.name for p in self.receipts.iterdir()), ["hung.watchdog.txt"],
                         "markers or sample temp files were left behind")

    def test_a_finished_suite_passes_its_status_through(self) -> None:
        started = time.monotonic()
        result = run_watchdog(self.receipts, "done", 60, 5, "bash", "-c", "echo out; echo err >&2; exit 3")
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "out\n")
        self.assertEqual(result.stderr, "err\n")
        self.assertLess(elapsed, 10, "the caller waited on the monitor instead of cancelling it")
        self.assertEqual(list(self.receipts.iterdir()), [], "a finished suite must leave no receipt")

    def test_validate_runs_every_suite_under_the_watchdog(self) -> None:
        text = VALIDATE.read_text(encoding="utf-8")
        self.assertIn('"$script_dir/validate-watchdog.sh" --label "$label" --budget "$suite_budget"', text)
        for line in ("watched render-check python3 ", "watched installer-migration bash ",
                     "watched installer-runtimes bash ", "watched grok-bot-verify python3 "):
            self.assertIn("\n" + line, text)
        self.assertIn('watched "$suite" python3 "$repo_root/tests/contract/$suite"', text)
        self.assertIn('if (( rc == 124 )); then', text)
        self.assertIn('"$repo_root/scripts/validate-watchdog.sh"', text.split("bash -n", 1)[1].split("\n\n", 1)[0])
        self.assertIn("test-issue-101-validate-watchdog.py", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
