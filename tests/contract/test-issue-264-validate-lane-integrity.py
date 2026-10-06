#!/usr/bin/env python3
"""Issue #264 / E1 registration-integrity regression (root 2026-10-07).

The four no-log SKIPs came from suites registered in the replay list but
in no execution lane, hidden by the --suite narrowing's else->keep_b
fallback. This test pins the three structural invariants on the REAL
validate.sh arrays (no framework, same extraction technique as
test-issue-83-lane-failure-visibility.py):

  1. every python_suites_all member is in EXACTLY ONE execution lane;
  2. no .py suite is registered in shell_suites;
  3. a suite registered in NO list is refused by --suite (it must not
     silently fall back into a lane and masquerade as coverage).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VALIDATE = REPO / "scripts" / "validate.sh"
BASH = shutil.which("bash") or "bash"


def arrays() -> dict[str, list[str]]:
    src = VALIDATE.read_text(encoding="utf-8")
    found: dict[str, list[str]] = {}
    for name in ("python_suites_all", "python_suites_a", "python_suites_b", "shell_suites"):
        match = re.search(name + r"=\((.*?)\n\)", src, re.S)
        if match is None:
            raise AssertionError(f"validate.sh array {name} not found")
        found[name] = re.findall(r'"([^"]+)"', match.group(1))
    return found


class LaneIntegrity(unittest.TestCase):
    def test_every_replayed_python_suite_is_in_exactly_one_lane(self) -> None:
        rows = arrays()
        lanes = [set(rows["python_suites_a"]), set(rows["python_suites_b"])]
        problems = []
        for suite in rows["python_suites_all"]:
            count = sum(suite in lane for lane in lanes)
            if count != 1:
                problems.append(f"{suite} in {count} lane(s)")
        self.assertEqual(problems, [])

    def test_lane_members_are_registered_for_replay(self) -> None:
        rows = arrays()
        replay = set(rows["python_suites_all"])
        gaps = [s for lane in ("python_suites_a", "python_suites_b")
                for s in rows[lane] if s not in replay]
        self.assertEqual(gaps, [])

    def test_no_python_suite_is_miscategorized_as_a_shell_suite(self) -> None:
        rows = arrays()
        mixed = [s for s in rows["shell_suites"] if s.endswith(".py")]
        self.assertEqual(mixed, [])

    def test_an_unregistered_suite_is_refused_not_silently_run(self) -> None:
        # A name in NO list must be rejected up front; the else->keep_b
        # fallback may only ever see registered names. Needs bash >= 4; skip
        # with this named receipt when the interpreter cannot be resolved
        # (#151 convention).
        version = subprocess.run([BASH, "--version"], capture_output=True, text=True)
        match = re.search(r"version (\d+)", version.stdout)
        if not match or int(match.group(1)) < 4:
            self.skipTest("prerequisite missing: bash >= 4 is required; "
                          "detected " + BASH)
        proc = subprocess.run(
            [BASH, str(VALIDATE), "--suite", "test-issue-999-does-not-exist.py"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PATH": os.environ["PATH"]},
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("unknown", (proc.stderr + proc.stdout).lower(),
                      "an unregistered suite must be refused by name, not run")


if __name__ == "__main__":
    unittest.main()
