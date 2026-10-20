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
* three failed calls coalesce into one repair and one notice (case 11);
* tier C accepts only a shell descendant's cwd: a non-shell descendant is no
  observation at all, and a shell descendant is recorded as `process`;
* a resumed holder restores `tool_cwd` from its record and reconciles the
  placeholder claim (empty and unregistered stays, non-empty is dropped);
* repeated status ticks record one vanish event for the same path (N-2);
* two removed worktrees keep two placeholders and two notices (N-1, N-5);
* V3 with no recorded path leaves the `tool-cwd-unknown` duty (deviation d);
* an unanswered `git worktree list` is reported, not silently trusted (N-3).

Case 7 (tier A: the runner-owned ``ZDOTDIR``/``BASH_ENV`` shell entry) is
skipped pending HUMAN_DECISION_REQUIRED D1; tier A is not implemented.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"
# The fixture platform: codex's start path needs no runtime binary and already
# declares native steering, so the fixture manifest carries only the two
# tool-cwd fields with the measured ZCode note (design section 7).
PLATFORM = "codex"
NOTE_RE = r"Note: your current working directory is (?P<path>.+?)\.?$"


def mock_command(scenario: str, steering: str, turn_ms: int = 0, log: Path | None = None,
                 vanish: dict[str, str] | None = None, caps: str = "",
                 resume_any: bool = False) -> str:
    parts = [sys.executable, str(MOCK), "--scenario", scenario,
             "--steering", steering, "--turn-ms", str(turn_ms)]
    if caps:
        parts += ["--caps", caps]
    if resume_any:
        parts += ["--resume-any"]
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
        # Issue #373: a second fixture whose manifest declares the tool shell,
        # so tier A is on only for its own tests. No note regex (tier B off)
        # and per-call persistence (no V2 pre-emption).
        cls.fixture_a = cls.root / "fixture-a"
        shutil.copytree(REPO / "scripts", cls.fixture_a / "scripts")
        shutil.copytree(REPO / "platforms", cls.fixture_a / "platforms")
        manifest_a = cls.fixture_a / "platforms" / f"{PLATFORM}.yaml"
        manifest_a.write_text(
            manifest_a.read_text(encoding="utf-8")
            + 'tool_shell: "zsh"\n'
            + 'shell_cwd_persistence: "per-call"\n',
            encoding="utf-8")
        cls.cli_path_a = cls.fixture_a / "scripts" / "kaola-acp.py"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"s-i369-{self._testMethodName.lower().replace('_', '-')}"[:79]
        self.issue = abs(hash(self._testMethodName)) % 900 + 100
        self._started = False
        self._worktrees: list[tuple[Path, str]] = []
        self.mock_log.unlink(missing_ok=True)

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=30)
        for path, branch in list(self._worktrees):
            subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force",
                            str(path)], capture_output=True)
            subprocess.run(["git", "-C", str(self.repo), "branch", "-D", branch],
                           capture_output=True)
        self._worktrees.clear()

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        return env

    def cli(self, command: str, *args: str, scenario: str = "slow",
            steering: str = "none", turn_ms: int = 0,
            vanish: dict[str, str] | None = None, caps: str = "",
            resume_any: bool = False, path_prefix: str = "",
            tier_a: bool = False,
            check: bool = True, timeout: float = 60) -> dict:
        cli_path = self.cli_path_a if tier_a else self.cli_path
        argv = [sys.executable, str(cli_path), PLATFORM, command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", mock_command(scenario, steering, turn_ms, self.mock_log,
                                          vanish, caps, resume_any),
                *args]
        env = self.env()
        if path_prefix:
            env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=env, timeout=timeout)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command} emitted no JSON: rc={result.returncode} "
                      f"stdout={result.stdout!r} stderr={result.stderr!r}")
        if check and ("error" in receipt or receipt.get("result") == "refused"):
            self.fail(f"{command} failed: {receipt}")
        return receipt

    def start(self, scenario: str, steering: str = "none", turn_ms: int = 0,
              vanish: dict[str, str] | None = None, caps: str = "",
              resume_any: bool = False, path_prefix: str = "",
              tier_a: bool = False) -> None:
        self.cli("start", scenario=scenario, steering=steering, turn_ms=turn_ms,
                 vanish=vanish, caps=caps, resume_any=resume_any,
                 path_prefix=path_prefix, tier_a=tier_a)
        self._started = True

    def send(self, text: str = "go", scenario: str = "slow", steering: str = "none",
             turn_ms: int = 0, vanish: dict[str, str] | None = None) -> dict:
        return self.cli("send", "--no-wait", "--text", text, scenario=scenario,
                        steering=steering, turn_ms=turn_ms, vanish=vanish)

    def status(self) -> dict:
        return self.cli("status", check=False)

    def errors(self) -> list[dict]:
        return self.status().get("tool_cwd_errors") or []

    def has_error(self, code: str) -> bool:
        return any(item.get("code") == code for item in self.errors())

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

    def add_worktree_n(self, issue: int) -> Path:
        path = self.repo / ".kw" / "worktrees" / f"issue-{issue}"
        path.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(["git", "-C", str(self.repo), "worktree", "add", str(path),
                               "-b", f"workflow/issue-{issue}"],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self._worktrees.append((path, f"workflow/issue-{issue}"))
        return path

    def add_worktree(self) -> Path:
        return self.add_worktree_n(self.issue)

    def same_path(self, left: object, right: object) -> bool:
        if not isinstance(left, str) or not left or right is None:
            return False
        return os.path.realpath(left) == os.path.realpath(str(right))

    def wait_pid_gone(self, pid: int, timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.1)
        self.fail(f"process {pid} stayed alive")

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
        self.assertEqual([Path(item).resolve() for item in state.get("placeholder") or []],
                         [path.resolve()])
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
        # Read the event log, never status: a status read is a V1 tick and may
        # repair the path (with a V1 trigger) before the scripted V3 text.
        self.wait_for(lambda: any(e.get("event") == "cwd_vanish_v3_sent"
                                  for e in self.mock_events()),
                      "the scripted V3 text", timeout=60)
        self.wait_for(lambda: any(e.get("kind") == "tool_cwd_placeholder_created"
                                  and e.get("trigger") == "V3" for e in self.events()),
                      "the V3 placeholder")
        vanished = [e for e in self.events() if e.get("kind") == "tool_cwd_vanished"]
        self.assertTrue(any(e.get("trigger") == "V3" for e in vanished), vanished)

    def test_v3_on_a_live_path_does_not_repair_or_notice(self) -> None:
        """B-2: a path that still exists is not a vanish, whatever V3 says."""
        path = self.add_worktree()
        self.marker().unlink(missing_ok=True)
        vanish = self.vanish(path, "v3")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        # Release the scripted spawn errors while the worktree is still there.
        self.marker().write_text("go\n", encoding="utf-8")
        self.wait_for(lambda: any(e.get("event") == "cwd_vanish_v3_sent"
                                  for e in self.mock_events()),
                      "the scripted V3 text", timeout=60)
        time.sleep(1)
        self.assertTrue(path.is_dir(), "the live worktree was touched")
        state = self.tool_cwd()
        self.assertEqual(state.get("placeholder"), [], state)
        self.assertFalse(any(e.get("kind") == "tool_cwd_vanished"
                             and e.get("trigger") == "V3" for e in self.events()))
        self.assertFalse(any(e.get("kind") == "tool_cwd_notice_staged"
                             for e in self.events()))

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
        self.assertEqual(self.tool_cwd().get("placeholder"), [])
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
            lambda: self.has_error("cwd-placeholder-not-empty"),
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

    # -- B-1: tier C accepts only a shell descendant -------------------------

    def test_tier_c_ignores_descendants_that_are_not_a_shell(self) -> None:
        """B-1: a non-shell descendant's cwd is not the tool shell's.

        Every other process in the agent's tree (an adapter, a helper, the
        agent CLI itself) says nothing about the tool cwd; with no shell alive
        there is no observation, and the recorded fact stays empty."""
        path = self.add_worktree()
        vanish = self.vanish(path, "tier_c_nonshell")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(
            lambda: any(e.get("event") == "cwd_vanish_execute_sent"
                        for e in self.mock_events()),
            "the execute event")
        time.sleep(3)  # one sample interval past the event
        self.assertIsNone(self.tool_cwd().get("last_known"), self.tool_cwd())
        observed = [e for e in self.events() if e.get("kind") == "tool_cwd_observed"]
        self.assertEqual(observed, [], observed)

    def test_tier_c_records_a_shell_descendant(self) -> None:
        """The positive control for B-1: a shell's cwd is still recorded."""
        path = self.add_worktree()
        vanish = self.vanish(path, "tier_c_shell")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.same_path(self.tool_cwd().get("last_known"), path),
                      "tier C to record the shell cwd")
        observed = [e for e in self.events() if e.get("kind") == "tool_cwd_observed"]
        self.assertTrue(any(e.get("source") == "process" for e in observed), observed)

    # -- N-1 / N-5: several removed worktrees -------------------------------

    def test_two_removed_worktrees_keep_two_placeholders_and_notices(self) -> None:
        first = self.add_worktree_n(71)
        second = self.add_worktree_n(72)
        self.start("slow", steering="none", turn_ms=8000)
        self.send("go", "slow", steering="none")
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the turn to become active")
        self.remove_out_of_band(first)
        self.remove_out_of_band(second)
        self.wait_for(lambda: first.is_dir() and second.is_dir(),
                      "both V2 placeholders")
        placeholders = self.tool_cwd().get("placeholder") or []
        resolved = {os.path.realpath(item) for item in placeholders}
        self.assertEqual(resolved, {os.path.realpath(str(first)),
                                    os.path.realpath(str(second))}, placeholders)
        staged = [e for e in self.events() if e.get("kind") == "tool_cwd_notice_staged"]
        self.assertEqual({os.path.realpath(e.get("path") or "") for e in staged},
                         {os.path.realpath(str(first)), os.path.realpath(str(second))},
                         staged)

    def test_one_steer_names_every_repaired_path(self) -> None:
        """Issue #373: the steer is one batch, not the latest path only."""
        first = self.add_worktree_n(81)
        second = self.add_worktree_n(82)
        self.start("slow", steering="injected", turn_ms=30000)
        self.send("go", "slow", steering="injected", turn_ms=30000)
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the turn to become active")
        self.remove_out_of_band(first)
        self.remove_out_of_band(second)
        self.wait_for(lambda: first.is_dir() and second.is_dir(),
                      "both V2 placeholders")
        self.wait_for(
            lambda: any(e.get("event") == "steering" for e in self.mock_events()),
            "the batch steer", timeout=60)
        texts = [e.get("text", "") for e in self.mock_events()
                 if e.get("event") == "steering"]
        real_first = os.path.realpath(str(first))
        real_second = os.path.realpath(str(second))
        self.assertTrue(
            any((real_first in text or str(first) in text)
                and (real_second in text or str(second) in text)
                for text in texts),
            f"the steer did not name every repaired path: {texts}")

    # -- N-2: one vanish event per path -------------------------------------

    def test_repeated_status_ticks_do_not_replay_the_vanish_event(self) -> None:
        path = self.add_worktree()
        vanish = self.vanish(path, "note")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        before = len([e for e in self.events() if e.get("kind") == "tool_cwd_vanished"])
        self.assertEqual(before, 1)
        for _ in range(5):
            self.status()
        after = len([e for e in self.events() if e.get("kind") == "tool_cwd_vanished"])
        self.assertEqual(after, 1, "a status read replayed the vanish event")

    # -- deviation d: V3 with no recorded path ------------------------------

    def test_v3_without_a_recorded_path_leaves_the_unknown_route(self) -> None:
        vanish = self.vanish(self.worktree(), "v3_unknown")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(
            lambda: self.has_error("tool-cwd-unknown"),
            "the tool-cwd-unknown duty")
        unknown = [e for e in self.events() if e.get("kind") == "tool_cwd_unknown"]
        self.assertEqual(len(unknown), 1, unknown)
        self.assertIsNone(self.tool_cwd().get("last_known"), self.tool_cwd())

    # -- N-3: git worktree list does not answer -----------------------------

    def git_stub(self) -> tuple[str, Path]:
        """A git on PATH that fails only ``worktree list`` once the marker
        exists; every other call (including this test's own status) delegates
        to the real binary."""
        real = shutil.which("git")
        self.assertIsNotNone(real, "git is not on PATH")
        stub_dir = self.root / f"git-stub-{self.issue}"
        stub_dir.mkdir(exist_ok=True)
        marker = stub_dir / "fail"
        script = stub_dir / "git"
        script.write_text(
            "#!/bin/sh\n"
            f'if [ -e "{marker}" ]; then\n'
            '  prev=""\n'
            '  for arg in "$@"; do\n'
            '    if [ "$prev" = "worktree" ] && [ "$arg" = "list" ]; then\n'
            '      echo "fatal: simulated worktree list failure" >&2\n'
            "      exit 128\n"
            "    fi\n"
            '    prev="$arg"\n'
            "  done\n"
            "fi\n"
            f'exec "{real}" "$@"\n',
            encoding="utf-8")
        script.chmod(0o755)
        return str(stub_dir), marker

    def test_unanswered_worktree_list_is_reported_not_silent(self) -> None:
        path = self.add_worktree()
        vanish = self.vanish(path, "note")
        stub, marker = self.git_stub()
        self.start("cwd_vanish", steering="none", vanish=vanish, path_prefix=stub)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        marker.write_text("fail\n", encoding="utf-8")
        try:
            self.wait_for(
                lambda: self.has_error("cwd-unverifiable"),
                "the git-unverifiable report")
        finally:
            marker.unlink(missing_ok=True)
        errors = [e for e in self.events() if e.get("kind") == "tool_cwd_unverifiable"]
        self.assertTrue(errors, self.event_kinds())
        self.assertFalse(path.exists(), "a placeholder was created without a git answer")

    # -- B-3: resume restores the fact and reconciles the claim -------------

    def test_resume_restores_and_reconciles_the_placeholder(self) -> None:
        path = self.add_worktree()
        vanish = self.vanish(path, "note")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        status = self.status()
        acp_id = status.get("acp_session_id")
        self.assertTrue(acp_id, status)

        # An unclean holder exit leaves the record's claim in place.
        os.kill(status["holder_pid"], signal.SIGKILL)
        self.wait_pid_gone(status["holder_pid"])
        if status.get("agent_pid"):
            self.wait_pid_gone(status["agent_pid"])
        self._started = False
        self.cli("start", "--resume", acp_id, scenario="cwd_vanish",
                 vanish=vanish, caps="resume,load", resume_any=True)
        self._started = True
        state = self.tool_cwd()
        self.assertEqual(state.get("last_known"), str(path), state)
        self.assertEqual([os.path.realpath(item) for item in state.get("placeholder") or []],
                         [os.path.realpath(str(path))], state)
        self.assertTrue(path.is_dir())

        # A claim that no longer fits is dropped by the same reconciliation.
        status = self.status()
        os.kill(status["holder_pid"], signal.SIGKILL)
        self.wait_pid_gone(status["holder_pid"])
        if status.get("agent_pid"):
            self.wait_pid_gone(status["agent_pid"])
        self._started = False
        (path / "stray.txt").write_text("kept\n", encoding="utf-8")
        self.cli("start", "--resume", status.get("acp_session_id"), scenario="cwd_vanish",
                 vanish=vanish, caps="resume,load", resume_any=True)
        self._started = True
        state = self.tool_cwd()
        self.assertEqual(state.get("placeholder"), [], state)
        self.assertTrue((path / "stray.txt").is_file())

    # -- R2-1: a fresh start inherits only the placeholder claim ------------

    def test_a_fresh_start_inherits_only_the_placeholder_claim(self) -> None:
        path = self.add_worktree()
        vanish = self.vanish(path, "note")
        self.start("cwd_vanish", steering="none", vanish=vanish)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        status = self.status()

        os.kill(status["holder_pid"], signal.SIGKILL)
        self.wait_pid_gone(status["holder_pid"])
        if status.get("agent_pid"):
            self.wait_pid_gone(status["agent_pid"])
        self._started = False
        # A fresh session (no --resume) starts on the same record.
        self.start("slow", steering="none", turn_ms=1000)
        state = self.tool_cwd()
        self.assertIsNone(state.get("last_known"), state)
        self.assertIsNone(state.get("source"), state)
        self.assertEqual([os.path.realpath(item) for item in state.get("placeholder") or []],
                         [os.path.realpath(str(path))], state)
        self.assertTrue(path.is_dir())
        created = [e for e in self.events()
                   if e.get("kind") == "tool_cwd_placeholder_created"]
        self.assertEqual(len(created), 1, created)

    # -- R2-2: an unknown worktree probe keeps the claim --------------------

    def test_unknown_worktree_probe_keeps_the_placeholder_claim(self) -> None:
        path = self.add_worktree()
        vanish = self.vanish(path, "note_then_repo")
        stub, marker = self.git_stub()
        self.start("cwd_vanish", steering="none", vanish=vanish, path_prefix=stub)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.tool_cwd().get("last_known") == str(path),
                      "tier B to record the noted path")
        self.remove_out_of_band(path)
        self.wait_for(lambda: path.is_dir(), "the placeholder")
        marker.write_text("fail\n", encoding="utf-8")
        try:
            # The second prompt notes the repo root: cleanup now runs with an
            # unreadable worktree list and must keep the claim.
            self.send("again", "cwd_vanish", steering="none", vanish=vanish)
            self.wait_for(
                lambda: self.has_error("cwd-unverifiable"),
                "the unknown probe duty")
            state = self.tool_cwd()
            self.assertEqual(
                [os.path.realpath(item) for item in state.get("placeholder") or []],
                [os.path.realpath(str(path))], state)
            self.assertTrue(path.is_dir())
            left = [e for e in self.events() if e.get("kind") == "tool_cwd_placeholder_left"]
            self.assertFalse(any(e.get("reason") == "registered worktree again"
                                 for e in left), left)
            # The same unknown answer on resume keeps it too.
            status = self.status()
            os.kill(status["holder_pid"], signal.SIGKILL)
            self.wait_pid_gone(status["holder_pid"])
            if status.get("agent_pid"):
                self.wait_pid_gone(status["agent_pid"])
            self._started = False
            self.cli("start", "--resume", status.get("acp_session_id"),
                     scenario="cwd_vanish", vanish=vanish, caps="resume,load",
                     resume_any=True, path_prefix=stub)
            self._started = True
            state = self.tool_cwd()
            self.assertEqual(
                [os.path.realpath(item) for item in state.get("placeholder") or []],
                [os.path.realpath(str(path))], state)
            left = [e for e in self.events() if e.get("kind") == "tool_cwd_placeholder_left"]
            self.assertFalse(any(e.get("reason") == "registered worktree again"
                                 for e in left), left)
        finally:
            marker.unlink(missing_ok=True)

    # -- case 7: tier A -----------------------------------------------------

    def shell_path(self, name: str) -> str | None:
        fixed = f"/bin/{name}"
        return fixed if os.path.exists(fixed) else shutil.which(name)

    def tier_a_env(self, shellenv: Path, trace: Path, fake_home: Path,
                   *, zsh: bool) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env.update({"HOME": str(fake_home), "KAOLA_TOOL_CWD_FILE": str(trace),
                    "SMOKE_SHELLENV": str(shellenv)})
        if zsh:
            env["ZDOTDIR"] = str(shellenv)
        else:
            env["BASH_ENV"] = str(shellenv / ".bashenv")
            env["KAOLA_USER_BASH_ENV"] = str(fake_home / ".bash_env")
        return env

    def test_tier_a_shell_entry_records_the_cwd(self) -> None:
        """The holder-generated entry writes $PWD for zsh and bash once, keeps
        the user's init, and a missing trace directory adds no stderr."""
        zsh = self.shell_path("zsh")
        bash = self.shell_path("bash")
        if not zsh or not bash:
            self.skipTest("#151: zsh and bash are required for the tier A entry")
        # Start a tier A holder only to have it generate the runner-owned files.
        self.start("slow", tier_a=True)
        shellenv = self.record_dir() / "shellenv"
        self.wait_for(lambda: (shellenv / ".zshenv").is_file()
                      and (shellenv / ".bashenv").is_file(),
                      "the holder-generated shell entries")
        fake_home = self.root / f"home-{self.issue}"
        fake_home.mkdir(exist_ok=True)
        (fake_home / ".zshenv").write_text(
            f'printf ran > "{fake_home}/zsh-init-ran"\n', encoding="utf-8")
        (fake_home / ".bash_env").write_text(
            f'printf ran > "{fake_home}/bash-init-ran"\n', encoding="utf-8")
        target = self.root / f"tier-a-{self.issue}"
        target.mkdir(exist_ok=True)

        zsh_trace = self.root / f"zsh-trace-{self.issue}"
        zsh_env = self.tier_a_env(shellenv, zsh_trace, fake_home, zsh=True)
        done = subprocess.run([zsh, "-c", "true"], cwd=target, env=zsh_env,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "", "the zsh entry wrote to stderr")
        self.assertTrue(self.same_path(zsh_trace.read_text(encoding="utf-8").strip(),
                                       target), zsh_trace.read_text(encoding="utf-8"))
        self.assertTrue((fake_home / "zsh-init-ran").is_file(),
                        "the user's ~/.zshenv did not run")

        bash_trace = self.root / f"bash-trace-{self.issue}"
        bash_env = self.tier_a_env(shellenv, bash_trace, fake_home, zsh=False)
        done = subprocess.run([bash, "-c", "true"], cwd=target, env=bash_env,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "", "the bash entry wrote to stderr")
        self.assertTrue(self.same_path(bash_trace.read_text(encoding="utf-8").strip(),
                                       target), bash_trace.read_text(encoding="utf-8"))
        self.assertTrue((fake_home / "bash-init-ran").is_file(),
                        "the user's BASH_ENV did not run")

        # A nested shell inherits the guard, even when it is pointed back at
        # the runner-owned entry, so the sentinel survives.
        nested_trace = self.root / f"nested-trace-{self.issue}"
        nested_env = self.tier_a_env(shellenv, nested_trace, fake_home, zsh=True)
        nested = ('printf "sentinel\\n" > "$KAOLA_TOOL_CWD_FILE"; '
                  'ZDOTDIR="$SMOKE_SHELLENV" ' + zsh + ' -c true; '
                  'cat "$KAOLA_TOOL_CWD_FILE"')
        done = subprocess.run([zsh, "-c", nested], cwd=target, env=nested_env,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "sentinel",
                         done.stdout)
        self.assertEqual(nested_trace.read_text(encoding="utf-8"), "sentinel\n")

        nested_bash_trace = self.root / f"nested-bash-trace-{self.issue}"
        nested_bash_env = self.tier_a_env(shellenv, nested_bash_trace, fake_home,
                                          zsh=False)
        nested = ('printf "sentinel\\n" > "$KAOLA_TOOL_CWD_FILE"; '
                  'BASH_ENV="$SMOKE_SHELLENV/.bashenv" ' + bash + ' -c true; '
                  'cat "$KAOLA_TOOL_CWD_FILE"')
        done = subprocess.run([bash, "-c", nested], cwd=target, env=nested_bash_env,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "sentinel",
                         done.stdout)

        # A missing trace directory is silent: the entry suppresses its own
        # redirection failure instead of leaking shell-init noise.
        missing = self.root / f"missing-{self.issue}" / "tool-cwd"
        zsh_env["KAOLA_TOOL_CWD_FILE"] = str(missing)
        done = subprocess.run([zsh, "-c", "true"], cwd=target, env=zsh_env,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "", done.stderr)
        bash_env["KAOLA_TOOL_CWD_FILE"] = str(missing)
        done = subprocess.run([bash, "-c", "true"], cwd=target, env=bash_env,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stderr, "", done.stderr)

    def test_tier_a_alone_records_repairs_and_cleans_up(self) -> None:
        """Mock-ACP: with tiers B/C disabled, the holder's own entry records
        the worktree cwd and a removal out of band is repaired and cleaned."""
        if not self.shell_path("zsh"):
            self.skipTest("#151: zsh is required for the tier A entry")
        path = self.add_worktree()
        self.marker().unlink(missing_ok=True)
        vanish = self.vanish(path, "tier_a")
        self.start("cwd_vanish", steering="none", vanish=vanish, tier_a=True)
        self.send("go", "cwd_vanish", steering="none", vanish=vanish)
        self.wait_for(lambda: self.same_path(self.tool_cwd().get("last_known"), path)
                      and self.tool_cwd().get("source") == "trace",
                      "tier A to record the tool cwd")
        observed = [e for e in self.events() if e.get("kind") == "tool_cwd_observed"]
        self.assertTrue(any(e.get("source") == "trace" for e in observed), observed)
        self.assertFalse(any(e.get("source") in ("note", "process") for e in observed),
                         f"tier B/C observed with tier A only: {observed}")

        self.remove_out_of_band(path, release_marker=True)
        self.wait_for(lambda: path.is_dir(), "the tier A placeholder")
        state = self.tool_cwd()
        self.assertEqual([os.path.realpath(item) for item in state.get("placeholder") or []],
                         [os.path.realpath(str(path))], state)

        self.release().write_text("go\n", encoding="utf-8")
        self.wait_for(lambda: not path.is_dir(), "the placeholder cleanup")
        self.assertIn("tool_cwd_placeholder_removed", self.event_kinds())


class CwdFactsUnit(unittest.TestCase):
    """Issue #373 leftovers at the fact layer: observed_at precedence and the
    repair-duty list (the integration harness covers the same status surface)."""

    @classmethod
    def setUpClass(cls) -> None:
        path = REPO / "scripts" / "kaola-acp-holder.py"
        loader = importlib.machinery.SourceFileLoader("kaola_acp_holder_i373", str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.module = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.module)

    def holder(self):
        class Events:
            def __init__(self) -> None:
                self.cursor = 0
                self.items: list[dict] = []

            def append(self, event, ts=None):
                self.cursor += 1
                self.items.append(event)
                return self.cursor

        holder = self.module.Holder.__new__(self.module.Holder)
        holder.tool_cwd = {
            "last_known": None, "source": None, "observed_at": None, "exists": None,
            "placeholder": [], "notice": "none", "notice_paths": [], "repairs": 0}
        holder.tool_cwd_lock = threading.Lock()
        holder.tool_cwd_errors = []
        holder.tool_cwd_vanished_path = None
        holder.args = SimpleNamespace(repo=str(REPO))
        holder.events = Events()
        holder.write_record = lambda **extra: None
        holder._cwd_check = lambda path: None
        holder._cwd_cleanup = lambda **extra: None
        return holder

    def test_newer_tier_a_beats_an_older_tier_c_sample(self) -> None:
        holder = self.holder()
        holder._cwd_note("/tier-a", "trace", observed_at=200.0)
        holder._cwd_note("/tier-c-old", "process", observed_at=100.0)
        self.assertEqual(holder.tool_cwd["last_known"], "/tier-a",
                         holder.tool_cwd)
        self.assertEqual(holder.tool_cwd["source"], "trace")
        holder._cwd_note("/tier-c-tie", "process", observed_at=200.0)
        self.assertEqual(holder.tool_cwd["last_known"], "/tier-a",
                         "a same-time tier C sample overwrote the trace")
        self.assertEqual(holder.tool_cwd["source"], "trace")

    def test_tier_a_file_older_than_the_agent_start_is_ignored(self) -> None:
        holder = self.holder()
        holder.args = SimpleNamespace(repo=str(REPO), tool_shell="zsh")
        with tempfile.TemporaryDirectory(prefix="kaola-i373-trace-") as tmp:
            holder.record_dir = Path(tmp)
            trace = holder.record_dir / "tool-cwd"
            trace.write_text("/old/path\n", encoding="utf-8")
            os.utime(trace, (100.0, 100.0))
            holder.agent_started = 200.0
            self.assertIsNone(holder._cwd_trace_read())
            self.assertIsNone(holder.tool_cwd["last_known"])
            trace.write_text("/fresh/path\n", encoding="utf-8")
            os.utime(trace, (300.0, 300.0))
            self.assertEqual(holder._cwd_trace_read(), "/fresh/path")
            self.assertEqual(holder.tool_cwd["last_known"], "/fresh/path")
            self.assertEqual(holder.tool_cwd["source"], "trace")
            self.assertEqual(holder.tool_cwd["observed_at"], 300.0)

    def test_every_simultaneous_repair_duty_is_visible(self) -> None:
        holder = self.holder()
        holder._cwd_error_set("cwd-unverifiable", "/a", "one", "route-a")
        holder._cwd_error_set("cwd-repair-failed", "/b", "two", "route-b")
        facts = holder._cwd_errors_facts()
        self.assertEqual([(item["code"], item["path"]) for item in facts],
                         [("cwd-unverifiable", "/a"), ("cwd-repair-failed", "/b")])
        holder._cwd_error_clear("cwd-unverifiable", "/a")
        self.assertEqual([item["path"] for item in holder._cwd_errors_facts()], ["/b"])
        holder._cwd_error_clear(path="/b")
        self.assertEqual(holder._cwd_errors_facts(), [])


if __name__ == "__main__":
    unittest.main()
