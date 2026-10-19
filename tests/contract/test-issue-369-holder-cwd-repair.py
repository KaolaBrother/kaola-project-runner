#!/usr/bin/env python3
"""Issue #369 Fix 2: the holder's tool-cwd detector, repair, notice and cleanup.

A real holder runs against the scripted mock agent (``cwd_vanish`` scenario) on
a fixture platform whose manifest carries the measured ZCode Read note — the
one in-band carrier of the tool cwd. The tests remove a real linked worktree
out of band and prove, from the holder's own record, event log and status:

* tier B records the noted path; a vanished path is repaired into an empty
  placeholder and the agent is told to ``cd`` the project root (case 6);
* V2 pre-emption needs no tool call at all: the worktree set difference at the
  status tick repairs an unknown tool cwd (case 8);
* V3 fires on the forwarded ``spawn <shell> ENOENT`` text (case 9);
* R4 leaves a registered-again or non-empty placeholder alone and reports it,
  and an exact stop removes an empty one (case 10);
* three failed calls coalesce into one repair and one notice (case 11).

Case 7 (tier A: the runner-owned ``ZDOTDIR``/``BASH_ENV`` shell entry) is
skipped pending HUMAN_DECISION_REQUIRED D1; tier A is not implemented.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"
# The fixture platform: codex's start path needs no runtime binary and already
# declares native steering, so the fixture manifest carries only the two
# tool-cwd fields with the measured ZCode note (design section 7).
PLATFORM = "codex"
NOTE_RE = r"Note: your current working directory is (?P<path>.+?)\.?$"


def mock_command(scenario: str, steering: str, turn_ms: int = 0, log: Path | None = None,
                 vanish: dict[str, str] | None = None) -> str:
    parts = [sys.executable, str(MOCK), "--scenario", scenario,
             "--steering", steering, "--turn-ms", str(turn_ms)]
    if log is not None:
        parts += ["--log", str(log)]
    for key, flag in (("path", "--cwd-vanish-path"), ("repo", "--cwd-vanish-repo"),
                      ("mode", "--cwd-vanish-mode"), ("marker", "--cwd-vanish-marker"),
                      ("release", "--cwd-vanish-release")):
        value = (vanish or {}).get(key)
        if value:
            parts += [flag, str(value)]
    return " ".join(shlex.quote(part) for part in parts)


class HolderCwdRepair(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i369-holder-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        subprocess.run(["git", "-C", str(cls.repo), "config", "user.email", "t@e.invalid"],
                       check=True)
        subprocess.run(["git", "-C", str(cls.repo), "config", "user.name", "t"], check=True)
        (cls.repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(cls.repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(cls.repo), "commit", "-qm", "base"], check=True)
        cls.repo_real = Path(os.path.realpath(cls.repo))
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock.jsonl"
        # A fixture checkout: the real scripts and manifests, with the two
        # tool-cwd fields added to the fixture platform's manifest.
        cls.fixture = cls.root / "fixture"
        shutil.copytree(REPO / "scripts", cls.fixture / "scripts")
        shutil.copytree(REPO / "platforms", cls.fixture / "platforms")
        manifest_path = cls.fixture / "platforms" / f"{PLATFORM}.yaml"
        manifest_path.write_text(
            manifest_path.read_text(encoding="utf-8")
            + 'tool_cwd_note_regex: "' + NOTE_RE.replace("\\", "\\\\") + '"\n'
            + 'shell_cwd_persistence: "persistent"\n',
            encoding="utf-8")
        cls.cli_path = cls.fixture / "scripts" / "kaola-acp.py"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"s-i369-{self._testMethodName.lower().replace('_', '-')}"[:79]
        self.issue = abs(hash(self._testMethodName)) % 900 + 100
        self._started = False
        self.mock_log.unlink(missing_ok=True)

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=30)
        self.remove_worktree()

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        return env

    def cli(self, command: str, *args: str, scenario: str = "slow",
            steering: str = "none", turn_ms: int = 0,
            vanish: dict[str, str] | None = None,
            check: bool = True, timeout: float = 60) -> dict:
        argv = [sys.executable, str(self.cli_path), PLATFORM, command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", mock_command(scenario, steering, turn_ms, self.mock_log, vanish),
                *args]
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(), timeout=timeout)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command} emitted no JSON: rc={result.returncode} "
                      f"stdout={result.stdout!r} stderr={result.stderr!r}")
        if check and ("error" in receipt or receipt.get("result") == "refused"):
            self.fail(f"{command} failed: {receipt}")
        return receipt

    def start(self, scenario: str, steering: str = "none", turn_ms: int = 0,
              vanish: dict[str, str] | None = None) -> None:
        self.cli("start", scenario=scenario, steering=steering, turn_ms=turn_ms, vanish=vanish)
        self._started = True

    def send(self, text: str = "go", scenario: str = "slow", steering: str = "none",
             turn_ms: int = 0, vanish: dict[str, str] | None = None) -> dict:
        return self.cli("send", "--no-wait", "--text", text, scenario=scenario,
                        steering=steering, turn_ms=turn_ms, vanish=vanish)

    def status(self) -> dict:
        return self.cli("status", check=False)

    def tool_cwd(self) -> dict:
        return self.status().get("tool_cwd") or {}

    def record_dir(self) -> Path:
        digest = hashlib.sha256(str(self.repo_real).encode()).hexdigest()[:16]
        return self.record_root / PLATFORM / self.session / digest

    def events(self) -> list[dict]:
        path = self.record_dir() / "events.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def event_kinds(self) -> list[str]:
        return [event.get("kind") for event in self.events()]

    def mock_events(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [json.loads(line)
                for line in self.mock_log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def wait_for(self, check, what: str, timeout: float = 45) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.2)
        self.fail(f"timed out waiting for {what}")

    def worktree(self) -> Path:
        return self.repo / ".kw" / "worktrees" / f"issue-{self.issue}"

    def add_worktree(self) -> Path:
        path = self.worktree()
        path.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(["git", "-C", str(self.repo), "worktree", "add", str(path),
                               "-b", f"workflow/issue-{self.issue}"],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return path

    def remove_worktree(self) -> None:
        path = self.worktree()
        subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force",
                        str(path)], capture_output=True)
        subprocess.run(["git", "-C", str(self.repo), "branch", "-D",
                        f"workflow/issue-{self.issue}"], capture_output=True)

    def marker(self) -> Path:
        return self.root / f"removed-{self.issue}"

    def release(self) -> Path:
        return self.root / f"release-{self.issue}"

    def vanish(self, path: Path, mode: str = "full") -> dict[str, str]:
        return {"path": str(path), "repo": str(self.repo), "mode": mode,
                "marker": str(self.marker()), "release": str(self.release())}

    def remove_out_of_band(self, path: Path, release_marker: bool = False) -> None:
        removed = subprocess.run(["git", "-C", str(self.repo), "worktree", "remove",
                                  str(path)], capture_output=True, text=True)
        self.assertEqual(removed.returncode, 0, removed.stderr)
        if release_marker:
            self.marker().write_text("removed\n", encoding="utf-8")

    # -- case 6: tier B ------------------------------------------------------

    def test_tier_b_note_repairs_notices_and_cleans_up(self) -> None:
        path = self.add_worktree()
        self.marker().unlink(missing_ok=True)
        vanish = self.vanish(path, "full")
        self.start("cwd_vanish", steering="injected", vanish=vanish)
        self.send("go", "cwd_vanish", steering="injected", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted worktree path")
        observed = [e for e in self.events() if e.get("kind") == "tool_cwd_observed"]
        self.assertTrue(any(e.get("source") == "note" for e in observed), observed)

        self.remove_out_of_band(path, release_marker=True)
        self.wait_for(lambda: path.is_dir(), "the placeholder to be created")
        state = self.tool_cwd()
        self.assertEqual(Path(state.get("placeholder") or "").resolve(), path.resolve())
        self.assertFalse(state.get("exists"), state)
        kinds = self.event_kinds()
        self.assertIn("tool_cwd_vanished", kinds)
        self.assertIn("tool_cwd_placeholder_created", kinds)

        # The idle boundary steers the notice into the still-running turn; the
        # mock reads and logs that request once its own script ends.
        self.wait_for(lambda: "steer_sent" in self.event_kinds(),
                      "the notice steer to be sent", timeout=60)
        self.release().write_text("go\n", encoding="utf-8")
        self.wait_for(lambda: any(e.get("event") == "steering" for e in self.mock_events()),
                      "the mock to read the steer", timeout=60)
        steered = [e for e in self.mock_events() if e.get("event") == "steering"]
        self.assertTrue(
            any(str(path) in e.get("text", "") and f"cd {self.repo_real}" in e.get("text", "")
                for e in steered),
            f"the notice text is wrong: {steered}")
        self.wait_for(lambda: "tool_cwd_notice_delivered" in self.event_kinds(),
                      "the notice to be marked delivered")

        self.wait_for(lambda: not path.is_dir(), "the placeholder to be removed")
        self.assertIn("tool_cwd_placeholder_removed", self.event_kinds())

    # -- case 8: V2 without any tool call ------------------------------------

    def test_v2_worktree_set_difference_repairs_without_a_tool_call(self) -> None:
        path = self.add_worktree()
        self.start("slow", steering="none", turn_ms=8000)
        self.send("go", "slow", steering="none")
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the turn to become active")
        self.remove_out_of_band(path)

        self.wait_for(lambda: path.is_dir(), "the V2 pre-emptive placeholder")
        state = self.tool_cwd()
        self.assertIsNone(state.get("last_known"), state)
        self.assertEqual(state.get("notice"), "pending", state)
        created = [e for e in self.events() if e.get("kind") == "tool_cwd_placeholder_created"]
        self.assertTrue(any(e.get("trigger") == "V2" for e in created), created)

        # Steering is unavailable on this mock, so the notice waits for the
        # turn end and is delivered as one self prompt at that boundary.
        self.wait_for(lambda: "tool_cwd_notice_delivered" in self.event_kinds(),
                      "the notice to be delivered at a boundary")

    # -- case 9: V3 ----------------------------------------------------------

    def test_v3_error_text_repairs_the_recorded_cwd(self) -> None:
        path = self.add_worktree()
        self.marker().unlink(missing_ok=True)
        vanish = self.vanish(path, "v3")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path, release_marker=True)
        self.wait_for(lambda: path.is_dir(), "the V3 placeholder")
        vanished = [e for e in self.events() if e.get("kind") == "tool_cwd_vanished"]
        self.assertTrue(any(e.get("trigger") == "V3" for e in vanished), vanished)

    # -- case 10: cleanup corners -------------------------------------------

    def test_cleanup_leaves_a_registered_again_placeholder(self) -> None:
        path = self.add_worktree()
        # The second prompt notes the repo root, which is when R4 runs.
        vanish = self.vanish(path, "note_then_repo")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        again = subprocess.run(["git", "-C", str(self.repo), "worktree", "add", str(path),
                                f"workflow/issue-{self.issue}"],
                               capture_output=True, text=True)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: "tool_cwd_placeholder_left" in self.event_kinds(),
                      "the registered-again placeholder to be left alone")
        left = [e for e in self.events() if e.get("kind") == "tool_cwd_placeholder_left"]
        self.assertTrue(any(e.get("reason") == "registered worktree again" for e in left), left)
        self.assertIsNone(self.tool_cwd().get("placeholder"))
        self.assertTrue(path.is_dir())

    def test_cleanup_reports_a_non_empty_placeholder(self) -> None:
        path = self.add_worktree()
        # The first prompt notes the worktree; the second notes the repo root.
        vanish = self.vanish(path, "note_then_repo")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        (path / "stray.txt").write_text("kept\n", encoding="utf-8")
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(
            lambda: (self.status().get("tool_cwd_error") or {}).get("code")
            == "cwd-placeholder-not-empty",
            "the non-empty placeholder report")
        self.assertTrue((path / "stray.txt").is_file())

    def test_exact_stop_removes_an_empty_placeholder(self) -> None:
        path = self.add_worktree()
        vanish = self.vanish(path, "note")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        self.cli("stop", "--force", check=False, timeout=30)
        self._started = False
        self.assertFalse(path.exists(), "the empty placeholder outlived the stop")
        self.assertIn("tool_cwd_placeholder_removed", self.event_kinds())

    # -- case 11: coalescing -------------------------------------------------

    def test_three_failed_calls_coalesce_into_one_repair(self) -> None:
        path = self.add_worktree()
        self.marker().unlink(missing_ok=True)
        vanish = self.vanish(path, "triple")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path, release_marker=True)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        self.wait_for(lambda: self.tool_cwd().get("repairs") == 1, "one repair")
        created = [e for e in self.events() if e.get("kind") == "tool_cwd_placeholder_created"]
        self.assertEqual(len(created), 1, created)
        staged = [e for e in self.events() if e.get("kind") == "tool_cwd_notice_staged"]
        self.assertEqual(len(staged), 1, staged)

    # -- case 7: tier A, pending D1 -----------------------------------------

    @unittest.skip("tier A (runner-owned ZDOTDIR/BASH_ENV shell entry) is not implemented: "
                   "HUMAN_DECISION_REQUIRED D1 is open")
    def test_tier_a_shell_entry_records_the_cwd(self) -> None:
        raise AssertionError("unreachable while D1 is open")


if __name__ == "__main__":
    unittest.main()
