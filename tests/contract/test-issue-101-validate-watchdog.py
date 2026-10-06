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

Issue #265 adds the validate entry's bounded selector: ``--suite NAME`` runs
only the named contract suites, through the same controlled entry. The cases
at the end of this file drive that real entry and read its actual output.
"""

from __future__ import annotations

import json
import os
import re
import shutil
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


# Issue #151: the watchdog's monitor/kill path needs bash >= 4 (mapfile,
# BASHPID). The rows below run the watchdog through `bash` from PATH, so probe
# that same interpreter: on bash 3.2 (the macOS /bin/bash) mapfile is not a
# builtin and the monitor dies at trip, so the hung suite it was meant to kill
# is never killed and the row times out instead. Detection, not weakening:
# with bash >= 4 both rows run unchanged; without it they skip with a named
# receipt.
BASH_VERSION_TEXT = subprocess.run(
    ["bash", "-c", 'printf %s "$BASH_VERSION"'], capture_output=True, text=True,
).stdout.strip()
BASH4_WATCHDOG_OK = subprocess.run(
    ["bash", "-c", 'type mapfile >/dev/null 2>&1 && [[ -n "${BASHPID:-}" ]]'],
).returncode == 0
BASH4_WATCHDOG_RECEIPT = (
    "prerequisite missing: bash >= 4 with mapfile/BASHPID (watchdog "
    f"monitor/kill path); detected bash {BASH_VERSION_TEXT or 'unknown'}"
)


class TestValidateWatchdog(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-issue-101-")
        self.receipts = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    @unittest.skipUnless(BASH4_WATCHDOG_OK, BASH4_WATCHDOG_RECEIPT)
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

    @unittest.skipUnless(BASH4_WATCHDOG_OK, BASH4_WATCHDOG_RECEIPT)
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


# Issue #265: the validate entry accepts explicit suite names and runs only
# them, through the same controlled entry. These cases drive the real script
# (not a copy) and read its actual output: a named subset with preparation
# kept, repeatable names and stem resolution, unknown-name refusal, the name
# list, failure propagation for a selected suite, and the sweep of its own
# TMPDIR root. The selection layer never infers dependency coverage; the Host
# chooses the set.
class TestValidateSuiteSelection(unittest.TestCase):

    def run_validate(self, *args: str, env: dict | None = None,
                     timeout: int = 180) -> subprocess.CompletedProcess[str]:
        merged = dict(os.environ)
        if env:
            merged.update(env)
        return subprocess.run(
            ["bash", str(VALIDATE), *args], capture_output=True, text=True,
            timeout=timeout, cwd=PROJECT, env=merged)

    @staticmethod
    def sweep_root(output: str) -> str | None:
        """The validate TMPDIR root named by the exit sweep's JSON receipt."""
        found = None
        for line in output.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "root" in data:
                found = data["root"]
        return found

    def test_selected_run_is_a_named_subset_and_keeps_preparation(self) -> None:
        result = self.run_validate("--suite", "test-issue-78-heredoc-deadlock.py")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("coverage: SUBSET RUN (1 of", output)
        self.assertIn("not full-inventory coverage", output)
        self.assertNotIn("FULL INVENTORY", output)
        self.assertIn("selected: test-issue-78-heredoc-deadlock.py", output)
        self.assertIn("candidate: ", output)
        # Controlled preparation still runs for a subset.
        self.assertIn("render-skills: PASS", output)
        self.assertIn("validate-skill: PASS", output)
        self.assertIn("scrubbed inherited env:", output)
        # Only the selected suite ran.
        self.assertIn("elapsed test-issue-78-heredoc-deadlock.py", output)
        self.assertNotIn("elapsed test-issue-101-validate-watchdog.py", output)
        self.assertNotIn("elapsed installer-runtimes", output)
        self.assertIn("total wall:", output)

    def test_repeatable_names_select_the_named_set(self) -> None:
        result = self.run_validate(
            "--suite", "test-issue-236-install-completion.py",
            "--suite", "test-issue-237-model-display")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("coverage: SUBSET RUN (2 of", output)
        self.assertIn("elapsed test-issue-236-install-completion.py", output)
        self.assertIn("elapsed test-issue-237-model-display.py", output)
        self.assertNotIn("elapsed test-issue-78-heredoc-deadlock.py", output)

    def test_unknown_suite_name_is_refused_actionably(self) -> None:
        result = self.run_validate("--suite", "definitely-not-a-suite.py")
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("unknown suite: definitely-not-a-suite.py", output)
        self.assertIn("--list", output)
        self.assertNotIn("elapsed ", output)

    def test_list_names_the_inventory_without_running(self) -> None:
        result = self.run_validate("--list")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        names = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertIn("test-issue-236-install-completion.py", names)
        self.assertIn("test-issue-237-model-display.py", names)
        self.assertIn("test-installer-runtimes.sh", names)
        for name in names:
            self.assertTrue(name.endswith((".py", ".sh")), name)
        self.assertNotIn("elapsed ", output)
        self.assertNotIn("render-skills: PASS", output)

    def test_a_selected_failing_suite_propagates_and_retains_its_receipt(self) -> None:
        result = self.run_validate(
            "--suite", "test-issue-49-grok-bot-host.py",
            env={"KAOLA_VALIDATE_SUITE_BUDGET": "1"})
        output = result.stdout + result.stderr
        match = re.search(r"retained under (\S+)", output)
        try:
            self.assertEqual(result.returncode, 1, output)
            self.assertIn("FAILED: test-issue-49-grok-bot-host.py", output)
            self.assertIsNotNone(match, output)
            watchdog_dir = Path(match.group(1))
            self.assertTrue(watchdog_dir.is_dir(),
                            "a tripped selected run must retain its watchdog receipt")
            self.assertTrue(list(watchdog_dir.glob("*.watchdog.txt")),
                            "the retained watchdog directory holds no receipt")
        finally:
            if match is not None:
                shutil.rmtree(Path(match.group(1)).parent, ignore_errors=True)

    def test_a_clean_run_sweeps_its_own_validate_root(self) -> None:
        result = self.run_validate("--suite", "test-issue-78-heredoc-deadlock.py")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        root = self.sweep_root(output)
        self.assertIsNotNone(root, f"no sweep root in output:\n{output}")
        self.assertFalse(Path(root).exists(),
                         "a clean run must remove its own validate TMPDIR root")


if __name__ == "__main__":
    unittest.main(verbosity=2)
