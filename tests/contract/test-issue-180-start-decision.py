#!/usr/bin/env python3
"""Issue #180: pre_spawn_refusal is the single start-decision site.

A call counter around a real in-process ``start`` shows
``worker_skill_alignment`` runs exactly once per start, and a
``drain-restart`` shows two calls - the pre-stop refusal decision plus the
post-stop start, down from three before #180 - because the stop is a state
boundary: the post-stop start re-decides on post-stop state instead of
reusing pre-stop facts. The #171 latency proof (a refused start never waits
on the runtime ``--version``) lives with the other refusal-facts checks in
``test-issue-164-pre-spawn-bridge-facts.py``.

Offline only. The seat is the mock ACP agent under an isolated HOME and
record root, and it is stopped in place before the temporary directory is
removed. No platform CLI is launched.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable
AGENT = f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"


def load_acp():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_acp_issue180", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StartDecisionScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "home").mkdir()
        (self.root / "records").mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)],
                       check=True, capture_output=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def env(self) -> dict[str, str]:
        return {
            "HOME": str(self.root / "home"),
            "PATH": "/usr/bin:/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.root / "records"),
            # The mock agent accepts the recorded sessionId a --resume
            # drain-restart replays into the new holder (the #162 pattern).
            "MOCK_ACP_RESUME_ANY": "1",
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
        }

    def test_worker_skill_alignment_runs_once_per_start(self) -> None:
        session = "claude-code-KPR-i180-count"
        mod = load_acp()
        calls: list[str] = []
        real_alignment = mod.worker_skill_alignment

        def counting(repo: str, platform: str = "zcode") -> dict:
            calls.append(platform)
            return real_alignment(repo, platform)

        mod.worker_skill_alignment = counting
        # The in-process start's holder Popen is intentionally left running
        # (the finally below stops it); its garbage collection would warn.
        warnings.simplefilter("ignore", ResourceWarning)
        saved_argv, saved_env = sys.argv, dict(os.environ)
        os.environ.clear()
        os.environ.update(self.env())
        stdout = io.StringIO()
        try:
            sys.argv = [str(CLI), "claude-code", "start", "--repo", str(self.repo),
                        "--session", session, "--command", AGENT]
            with contextlib.redirect_stdout(stdout):
                rc = mod.main()
            self.assertEqual(rc, 0, stdout.getvalue()[-800:])
            started = json.loads(stdout.getvalue().strip().splitlines()[-1])
            self.assertEqual(started.get("state"), "ready", started)
            self.assertEqual(
                len(calls), 1, "worker_skill_alignment must run once per start")

            calls.clear()
            sys.argv = [str(CLI), "claude-code", "drain-restart", "--repo",
                        str(self.repo), "--session", session, "--command", AGENT,
                        "--resume", started["acp_session_id"]]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = mod.main()
            self.assertEqual(rc, 0, stdout.getvalue()[-800:])
            restarted = json.loads(stdout.getvalue().strip().splitlines()[-1])
            self.assertEqual(restarted.get("state"), "ready", restarted)
            # The pre-stop refusal decision plus the post-stop start; the
            # third pre-#180 scan of command_start is gone.
            self.assertEqual(len(calls), 2, calls)
        finally:
            sys.argv = [str(CLI), "claude-code", "stop", "--repo", str(self.repo),
                        "--session", session, "--force"]
            with contextlib.redirect_stdout(io.StringIO()):
                mod.main()
            sys.argv = saved_argv
            os.environ.clear()
            os.environ.update(saved_env)


if __name__ == "__main__":
    unittest.main()
