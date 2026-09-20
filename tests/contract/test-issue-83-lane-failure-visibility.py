#!/usr/bin/env python3
"""Issue #83: a failing suite must not hide the rest of a validate lane.

``scripts/validate.sh`` runs its Python contract suites as two background lanes
and replays each suite's ``$validate_tmp/<suite>.log`` afterwards in the fixed
``python_suites_all`` order. The original ``run_suite_lane`` returned 1 on the
first failing suite, so every suite ordered after it in that lane never ran and
never left a log. Under ``set -e`` the ordered ``cat`` replay then died on the
first missing log — one ``FAILED:`` line, a truncated replay that even hid logs
which did exist, and a single ``cat: ... No such file or directory`` instead of
a list of untested suites.

The contract: a suite failure never decides what runs later. Every suite in a
lane is attempted and measured, each failure prints ``FAILED: <suite>``, the
replay shows every log that exists, any suite that left no log is reported
``SKIPPED: <suite>`` explicitly (never a bare cat error), and the script still
exits nonzero. The green path is unchanged.

This test extracts the real lane/replay block out of ``scripts/validate.sh``
and drives it with stub suites — failing, passing, and one that deletes its own
log — so the shipped code, not a copy of it, is what is measured.
"""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
VALIDATE = PROJECT / "scripts" / "validate.sh"

# The block under test: run_suite_lane's definition through the `exit 1` fi.
# Inner `fi` lines are indented; the first `fi` at column 0 closes
# `if (( python_status ))`.
def lane_block() -> str:
    lines = VALIDATE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("run_suite_lane()"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "fi")
    block = "\n".join(lines[start:end + 1])
    for marker in ("run_suite_lane", "python_suites_all", "python_status"):
        if marker not in block:
            raise AssertionError(
                f"extracted validate.sh block lost {marker!r}; the lane/replay "
                "region moved and this test's slice boundaries need updating")
    return block


# Issue #101: run_suite_lane runs each suite through validate.sh's `watched`
# wrapper (scripts/validate-watchdog.sh). Extract the real function too, so the
# lane is measured with the watchdog it ships with rather than a stub of it.
def watched_block() -> str:
    lines = VALIDATE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("watched()"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    block = "\n".join(lines[start:end + 1])
    if "validate-watchdog.sh" not in block:
        raise AssertionError(
            "extracted validate.sh `watched` block does not call "
            "validate-watchdog.sh; the wrapper moved and this test's slice "
            "boundaries need updating")
    return block


STUB_OK = 'print("SUITE-LOG-{name}")\n'
STUB_FAIL = 'import sys\nprint("SUITE-LOG-{name}")\nsys.exit(1)\n'
# Passes, but removes its own replay log: the abnormal "no log" case the
# replay must report as SKIPPED rather than trip over with a cat error.
STUB_EATER = (
    'import os\n'
    'print("SUITE-LOG-{name}")\n'
    'os.remove(os.path.join(os.environ["EAT_ROOT"],\n'
    '          os.path.basename(__file__) + ".log"))\n'
)

HARNESS = textwrap.dedent("""\
    #!/usr/bin/env bash
    set -euo pipefail
    repo_root="{repo}"
    script_dir="{scripts}"
    validate_tmp="{tmp}"
    suite_budget=600
    watchdog_dir="$validate_tmp/watchdog"
    export EAT_ROOT="$validate_tmp"
    {watched}
    python_suites_all=({all})
    python_suites_a=({a})
    python_suites_b=({b})
    {block}
    echo LANE-BLOCK-SURVIVED
""")


def run_lane(fixture: Path, suites: dict[str, str],
             lane_a: list[str], lane_b: list[str],
             lane_all: list[str]) -> subprocess.CompletedProcess[str]:
    """Run validate.sh's real lane block against stub suites; return the run."""
    repo = fixture / "repo"
    contract = repo / "tests" / "contract"
    contract.mkdir(parents=True)
    for name, body in suites.items():
        (contract / name).write_text(body.format(name=name), encoding="utf-8")
    validate_tmp = fixture / "valtmp"
    validate_tmp.mkdir()
    harness = fixture / "harness.sh"
    harness.write_text(HARNESS.format(
        repo=repo, scripts=PROJECT / "scripts", tmp=validate_tmp,
        block=lane_block(), watched=watched_block(),
        all=" ".join(f'"{s}"' for s in lane_all),
        a=" ".join(f'"{s}"' for s in lane_a),
        b=" ".join(f'"{s}"' for s in lane_b)), encoding="utf-8")
    return subprocess.run(["bash", str(harness)],
                          capture_output=True, text=True, timeout=60)


def markers_in_order(output: str, lane_all: list[str]) -> bool:
    """Every suite's replayed log appears, in python_suites_all order."""
    positions = [output.find(f"SUITE-LOG-{s}") for s in lane_all]
    return all(pos >= 0 for pos in positions) and positions == sorted(positions)


class TestLaneFailureVisibility(unittest.TestCase):

    def setUp(self) -> None:
        self.fixture = Path(tempfile.mkdtemp(prefix="kaola-i83-lane-"))
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        import shutil
        shutil.rmtree(self.fixture, ignore_errors=True)

    def test_failing_suite_does_not_hide_downstream_suites(self) -> None:
        """Both lanes finish every suite; nothing unmeasured, nothing hidden."""
        suites = {
            "s-a1.py": STUB_OK, "s-fa.py": STUB_FAIL, "s-a2.py": STUB_OK,
            "s-b1.py": STUB_OK, "s-fb.py": STUB_FAIL, "s-b2.py": STUB_OK,
        }
        lane_all = ["s-a1.py", "s-fa.py", "s-a2.py",
                    "s-b1.py", "s-fb.py", "s-b2.py"]
        run = run_lane(self.fixture, suites,
                       lane_a=lane_all[:3], lane_b=lane_all[3:],
                       lane_all=lane_all)
        output = run.stdout + run.stderr
        self.assertNotEqual(run.returncode, 0,
                            f"a lane with failures must exit nonzero:\n{output}")
        self.assertIn("FAILED: s-fa.py", output)
        self.assertIn("FAILED: s-fb.py", output)
        self.assertNotIn("No such file or directory", output,
                         "a missing log must never surface as a cat error")
        self.assertTrue(
            markers_in_order(output, lane_all),
            "every suite must run and replay in order, including suites "
            f"ordered after a failure:\n{output}")

    def test_missing_log_is_reported_skipped_not_a_cat_error(self) -> None:
        """A suite that left no log is reported SKIPPED; replay continues."""
        suites = {
            "s-a1.py": STUB_OK, "s-eater.py": STUB_EATER, "s-a2.py": STUB_OK,
            "s-b1.py": STUB_OK,
        }
        lane_all = ["s-a1.py", "s-eater.py", "s-a2.py", "s-b1.py"]
        run = run_lane(self.fixture, suites,
                       lane_a=lane_all[:3], lane_b=lane_all[3:],
                       lane_all=lane_all)
        output = run.stdout + run.stderr
        self.assertNotEqual(run.returncode, 0,
                            f"a suite with no log must keep the run nonzero:\n{output}")
        self.assertIn("SKIPPED: s-eater.py", output)
        self.assertNotIn("No such file or directory", output)
        for name in ("s-a1.py", "s-a2.py", "s-b1.py"):
            self.assertIn(f"SUITE-LOG-{name}", output,
                          f"replay must continue past the missing log:\n{output}")

    def test_green_path_is_unchanged(self) -> None:
        """All suites pass: zero exit, every log replayed in order."""
        suites = {f"s-{n}.py": STUB_OK for n in ("a1", "a2", "b1")}
        lane_all = ["s-a1.py", "s-a2.py", "s-b1.py"]
        run = run_lane(self.fixture, suites,
                       lane_a=lane_all[:2], lane_b=lane_all[2:],
                       lane_all=lane_all)
        output = run.stdout + run.stderr
        self.assertEqual(run.returncode, 0, f"green lane must pass:\n{output}")
        self.assertIn("LANE-BLOCK-SURVIVED", output)
        self.assertNotIn("FAILED:", output)
        self.assertTrue(markers_in_order(output, lane_all),
                        f"green replay order changed:\n{output}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
