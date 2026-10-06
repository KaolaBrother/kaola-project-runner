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

Issue #265 repair: an interrupted run must stop this invocation's writers
before the holder sweep and the root removal, so a late write cannot recreate
``$validate_tmp`` (the observed SIGINT failure: exit 130, empty sweep residue,
``rm: Directory not empty``). The cases below drive the real
``stop_owned_writers`` and the real entry under SIGINT and SIGTERM.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
import unittest
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
WATCHDOG = PROJECT / "scripts" / "validate-watchdog.sh"
VALIDATE = PROJECT / "scripts" / "validate.sh"


def stop_writers_block() -> str:
    """The real ``stop_owned_writers`` from validate.sh, driven as shipped."""
    lines = VALIDATE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("stop_owned_writers()"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    block = "\n".join(lines[start:end + 1])
    for marker in ("ps", "-axo", "kill -KILL", "os.getpid"):
        if marker not in block:
            raise AssertionError(
                f"extracted validate.sh stop_owned_writers lost {marker!r}; "
                "the function moved and this test's slice needs updating")
    return block


# Drives the real stop_owned_writers against a writer subtree that keeps
# creating files under ROOT. A foreign process is started by the caller (a
# sibling, not a descendant) and must survive.
STOP_WRITERS_HARNESS = """\
#!/usr/bin/env bash
set -euo pipefail
root="@ROOT@"
@BLOCK@
bash -c 'while true; do mkdir -p "$0/a/b"; echo x >> "$0/a/b/w"; sleep 0.02; done' "$root" &
w1=$!
bash -c 'while true; do echo y >> "$0/top.log"; sleep 0.02; done' "$root" &
w2=$!
trap 'kill -KILL "$w1" "$w2" 2>/dev/null || true' EXIT
sleep 0.6
stop_owned_writers
for pair in "W1:$w1" "W2:$w2"; do
  name=${pair%%:*}; pid=${pair##*:}
  if kill -0 "$pid" 2>/dev/null; then echo "$name ALIVE"; else echo "$name DEAD"; fi
done
count_a="$(find "$root" -type f | wc -l | tr -d ' ')"
sleep 0.4
count_b="$(find "$root" -type f | wc -l | tr -d ' ')"
echo "COUNT_A=$count_a COUNT_B=$count_b"
if rm -rf "$root" && [ ! -e "$root" ]; then echo "RM_OK"; else echo "RM_FAIL"; fi
"""


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

    def test_unsupported_bash_refuses_before_allocating_roots(self) -> None:
        shell = Path("/bin/bash")
        if not shell.is_file():
            self.skipTest("no /bin/bash for the unsupported-shell check")
        version = subprocess.run(
            [str(shell), "-c", 'printf %s "${BASH_VERSINFO[0]}"'],
            capture_output=True, text=True, timeout=10).stdout.strip()
        if not version.isdigit() or int(version) >= 4:
            self.skipTest("/bin/bash is not an unsupported Bash version")
        with tempfile.TemporaryDirectory(prefix="kaola-i265-prerequisite-") as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            trace = root / "mktemp-calls"
            mktemp = bin_dir / "mktemp"
            mktemp.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$*" >> "$KPR_ENTRY_MKTEMP_TRACE"\n'
                'exec "$KPR_ENTRY_REAL_MKTEMP" "$@"\n', encoding="utf-8")
            mktemp.chmod(0o755)
            env = dict(os.environ, TMPDIR=tmp,
                       PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                       KPR_ENTRY_MKTEMP_TRACE=str(trace),
                       KPR_ENTRY_REAL_MKTEMP=shutil.which("mktemp") or "/usr/bin/mktemp")
            result = subprocess.run(
                [str(shell), str(VALIDATE), "--suite", "test-issue-78-heredoc-deadlock.py"],
                capture_output=True, text=True, timeout=10, cwd=PROJECT, env=env)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Bash >= 4", result.stderr)
            self.assertFalse(trace.exists(), "the refused entry allocated a root")
            self.assertEqual(list(root.iterdir()), [bin_dir])

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

    def test_help_is_read_only(self) -> None:
        for flag in ("--help", "-h"):
            with self.subTest(flag=flag):
                result = self.run_validate(flag)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertIn("usage: scripts/validate.sh", output)
                # A read-only exit runs no check and reports no run.
                self.assertNotIn("render-skills: PASS", output)
                self.assertNotIn("validate: elapsed", output)
                self.assertNotIn("total wall:", output)

    def test_a_clean_run_sweeps_its_own_validate_root(self) -> None:
        result = self.run_validate("--suite", "test-issue-78-heredoc-deadlock.py")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        root = self.sweep_root(output)
        self.assertIsNotNone(root, f"no sweep root in output:\n{output}")
        self.assertFalse(Path(root).exists(),
                         "a clean run must remove its own validate TMPDIR root")
        # The total wall is measured after the cleanup sweep, and an
        # unavailable measurement is never printed as a fabricated 0.
        match = re.search(r"validate: total wall: ([0-9.]+) s", output)
        self.assertIsNotNone(match, f"no numeric total wall in output:\n{output}")
        self.assertGreater(float(match.group(1)), 0.0,
                           "the total wall must not be a fabricated 0")
        self.assertLess(output.index('"root"'), match.start(),
                        "the total wall must be measured after the cleanup sweep")

    def test_stop_owned_writers_stops_only_this_invocation(self) -> None:
        fixture = Path(tempfile.mkdtemp(prefix="kaola-i265-stopw-"))
        self.addCleanup(shutil.rmtree, fixture, ignore_errors=True)
        root = fixture / "root"
        root.mkdir()
        harness = fixture / "harness.sh"
        harness.write_text(
            STOP_WRITERS_HARNESS.replace("@ROOT@", str(root)).replace(
                "@BLOCK@", stop_writers_block()), encoding="utf-8")
        foreign = subprocess.Popen(["sleep", "300"])
        self.addCleanup(lambda: (foreign.kill(), foreign.wait()))
        result = subprocess.run(
            ["bash", str(harness)], capture_output=True, text=True, timeout=60,
            start_new_session=True)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("W1 DEAD", output)
        self.assertIn("W2 DEAD", output)
        counts = re.search(r"COUNT_A=(\d+) COUNT_B=(\d+)", output)
        self.assertIsNotNone(counts, output)
        self.assertEqual(counts.group(1), counts.group(2),
                         "a writer kept recreating files after the stop")
        self.assertIn("RM_OK", output, "the root was not removable after the stop")
        self.assertIsNone(foreign.poll(),
                          "the stop touched a process this invocation did not own")

    @staticmethod
    def _default_signals() -> None:
        # A background job inherits SIGINT/SIGQUIT ignored from the shell. The
        # real foreground entry receives them, so reset both to the default in
        # the child before it execs the entry under test.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

    def _interrupt_midflight(self, sig: int, expected_rc: int) -> None:
        foreign = subprocess.Popen(["sleep", "300"])
        self.addCleanup(lambda: (foreign.kill(), foreign.wait()))
        proc = subprocess.Popen(
            ["bash", str(VALIDATE), "--suite", "test-issue-49-grok-bot-host.py"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            cwd=PROJECT, start_new_session=True,
            preexec_fn=self._default_signals)
        root = None
        try:
            started = False
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                line = proc.stdout.readline()
                if not line:
                    break
                if "coverage:" in line:
                    started = True
                    break
            self.assertTrue(started, "the controlled run did not start")
            time.sleep(0.5)
            proc.send_signal(sig)
            try:
                output = proc.communicate(timeout=90)[0]
            except subprocess.TimeoutExpired:
                proc.kill()
                output = proc.communicate()[0]
                self.fail(f"the interrupted run did not exit:\n{output}")
            self.assertEqual(proc.returncode, expected_rc, output)
            root = self.sweep_root(output)
            self.assertIsNotNone(root, f"no sweep root in output:\n{output}")
            time.sleep(0.3)
            self.assertFalse(
                Path(root).exists(),
                f"the interrupted run left or recreated its root: {root}\n{output}")
            self.assertIsNone(foreign.poll(),
                              "an unrelated process was stopped")
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            if root:
                shutil.rmtree(root, ignore_errors=True)

    def test_sigint_midflight_exits_130_and_removes_the_root(self) -> None:
        self._interrupt_midflight(signal.SIGINT, 130)

    def test_sigterm_midflight_exits_143_and_removes_the_root(self) -> None:
        self._interrupt_midflight(signal.SIGTERM, 143)


if __name__ == "__main__":
    unittest.main(verbosity=2)
