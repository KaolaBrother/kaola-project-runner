#!/usr/bin/env python3
"""Issue #378 F1: the cwd-repair notice is delivered once per turn.

dsh's native ``_session/steering`` answers ``written`` with
``mutation_performed: true``; the holder used to mark the notice delivered only
on ``injected``, so ``idle_watcher`` steered the whole batch again every 15 s
for the rest of the turn (494 written steer results in the recorded
``dsh-KPR-i373-cwdtrace`` session). The same review showed ``_cwd_notice_text``
regenerating ``ts`` per attempt, so every retry had a new fingerprint.

A real holder runs against the scripted mock agent (``slow`` scenario) on a
fixture platform whose manifest carries the measured V2 persistence field. The
tests prove, from the holder's record, event log, status and the mock's own
steering log:

* a ``written`` steer marks the pending notice delivered once, and the next
  idle tick (past 15 s) sends no second steer for that batch (case A);
* one batch names every path repaired before delivery, and the text's ``ts``
  is the batch's one stable stamp, reused by every staged event (case A);
* V2 pre-emption still delivers a newly removed worktree after the previous
  batch was delivered, and the new batch is itself delivered once (case B);
* the delivery predicate accepts ``written``/``queued`` only when
  ``mutation_performed`` is true, and an idle record's text is stable across
  repeated reads and survives a resume (case C).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
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
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
# codex needs no runtime binary and already advertises native steering, so the
# fixture only adds the measured persistence field.
PLATFORM = "codex"
NOTE_RE = r"Note: your current working directory is (?P<path>.+?)\.?$"
TS_RE = re.compile(r"at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})")
STEER_SETTLE_SECONDS = 17


def mock_command(steering: str, turn_ms: int, log: Path) -> str:
    parts = [sys.executable, str(MOCK), "--scenario", "slow",
             "--steering", steering, "--turn-ms", str(turn_ms),
             "--log", str(log)]
    return " ".join(shlex.quote(part) for part in parts)


def load_holder():
    spec = importlib.util.spec_from_file_location("kaola_acp_holder_378", HOLDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoticeDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i378-notice-")
        cls.root = Path(cls._tmp.name)
        cls._serial = 1000
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
        cls.fixture = cls.root / "fixture"
        shutil.copytree(REPO / "scripts", cls.fixture / "scripts")
        shutil.copytree(REPO / "platforms", cls.fixture / "platforms")
        manifest = cls.fixture / "platforms" / f"{PLATFORM}.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            + 'tool_cwd_note_regex: "' + NOTE_RE.replace("\\", "\\\\") + '"\n'
            + 'shell_cwd_persistence: "persistent"\n',
            encoding="utf-8")
        cls.cli_path = cls.fixture / "scripts" / "kaola-acp.py"
        cls.module = load_holder()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"s-i378-{self._testMethodName.lower().replace('_', '-')}"[:79]
        self.issue = self.__class__._serial
        self.__class__._serial += 1
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

    def cli(self, command: str, *args: str, steering: str = "written",
            turn_ms: int = 0, check: bool = True, timeout: float = 60) -> dict:
        argv = [sys.executable, str(self.cli_path), PLATFORM, command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", mock_command(steering, turn_ms, self.mock_log),
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

    def start(self, turn_ms: int, steering: str = "written") -> None:
        self.cli("start", steering=steering, turn_ms=turn_ms)
        self._started = True

    def send(self, steering: str = "written", turn_ms: int = 0) -> dict:
        return self.cli("send", "--no-wait", "--text", "go",
                        steering=steering, turn_ms=turn_ms)

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

    def steer_results(self, outcome: str = "written") -> list[dict]:
        return [event for event in self.events()
                if event.get("kind") == "steer_result"
                and event.get("steer_outcome") == outcome]

    def mock_events(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [json.loads(line)
                for line in self.mock_log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def mock_steers(self) -> list[str]:
        return [event.get("text", "") for event in self.mock_events()
                if event.get("event") == "steering"]

    def wait_for(self, check, what: str, timeout: float = 60) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.2)
        self.fail(f"timed out waiting for {what}")

    def add_worktree(self) -> Path:
        serial = self.__class__._serial
        self.__class__._serial += 1
        name = f"issue-{self.issue}-{serial}"
        path = self.repo / ".kw" / "worktrees" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(["git", "-C", str(self.repo), "worktree", "add", str(path),
                               "-b", f"workflow/{name}"],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self._worktrees.append((path, f"workflow/{name}"))
        return path

    def remove_out_of_band(self, path: Path) -> None:
        removed = subprocess.run(["git", "-C", str(self.repo), "worktree", "remove",
                                  str(path)], capture_output=True, text=True)
        self.assertEqual(removed.returncode, 0, removed.stderr)

    def wait_active(self) -> None:
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the turn to become active")

    # -- case A: written is delivery once, for the whole batch --------------

    def test_written_steer_delivers_the_batch_once_past_the_next_tick(self) -> None:
        first = self.add_worktree()
        second = self.add_worktree()
        # Long enough for two idle ticks after delivery.
        self.start(turn_ms=120000)
        self.send(turn_ms=120000)
        self.wait_active()
        self.remove_out_of_band(first)
        self.remove_out_of_band(second)
        self.wait_for(lambda: first.is_dir() and second.is_dir(),
                      "both V2 placeholders")
        self.wait_for(lambda: self.steer_results("written"), "the written batch steer")
        self.assertGreaterEqual(len(self.mock_steers()), 1)
        self.wait_for(lambda: self.tool_cwd().get("notice") == "delivered",
                      "the notice to be marked delivered")

        texts = self.mock_steers()
        self.assertEqual(len(texts), 1, f"the notice was steered more than once: {texts}")
        batch_text = texts[0]
        real_first = os.path.realpath(str(first))
        real_second = os.path.realpath(str(second))
        self.assertIn(real_first, batch_text)
        self.assertIn(real_second, batch_text)

        # One batch is staged for both paths; the steer names both and carries
        # the batch's one stable ts (the exact retry-stability proof lives in
        # test_notice_text_is_stable_for_one_pending_batch).
        staged = [event for event in self.events()
                  if event.get("kind") == "tool_cwd_notice_staged"]
        self.assertEqual(len(staged), 2, staged)
        batch_match = TS_RE.search(batch_text)
        self.assertIsNotNone(batch_match, batch_text)
        state = self.tool_cwd()
        self.assertEqual(state.get("notice_paths"), [], state)
        # The delivered batch releases its stamp, so a later repair starts a
        # new (and again stable) batch.
        self.assertIsNone(state.get("notice_ts"), state)

        # The next 15 s idle tick lands inside this same turn: the fixed holder
        # must send nothing, while the #378 bug sent the whole batch again.
        time.sleep(STEER_SETTLE_SECONDS)
        self.assertTrue(self.status().get("turn_active"), "the turn ended too early")
        self.assertEqual(self.mock_steers(), [batch_text],
                         "the same notice batch was steered again in one turn")
        self.assertEqual(len(self.steer_results("written")), 1)
        delivered = [event for event in self.events()
                     if event.get("kind") == "tool_cwd_notice_delivered"]
        self.assertEqual([event.get("via") for event in delivered], ["steer"], delivered)

    # -- case B: V2 pre-emption after a delivered batch ---------------------

    def test_v2_preemption_still_delivers_a_newly_removed_worktree(self) -> None:
        first = self.add_worktree()
        second = self.add_worktree()
        self.start(turn_ms=180000)
        self.send(turn_ms=180000)
        self.wait_active()

        self.remove_out_of_band(first)
        self.wait_for(lambda: first.is_dir(), "the first V2 placeholder")
        self.wait_for(lambda: len(self.steer_results("written")) == 1,
                      "the first batch steer")
        self.assertEqual(len(self.mock_steers()), 1, self.mock_steers())

        # The previous batch is delivered and the shell cwd is still
        # unobserved; the second removed worktree must still be announced.
        self.remove_out_of_band(second)
        self.wait_for(lambda: second.is_dir(), "the second V2 placeholder")
        self.wait_for(lambda: len(self.steer_results("written")) == 2,
                      "the second batch steer")
        texts = self.mock_steers()
        self.assertEqual(len(texts), 2, texts)
        self.assertIn(os.path.realpath(str(second)), texts[1])
        self.assertNotIn(os.path.realpath(str(first)), texts[1])
        self.wait_for(lambda: self.tool_cwd().get("notice") == "delivered",
                      "the second notice to be marked delivered")

        time.sleep(STEER_SETTLE_SECONDS)
        self.assertEqual(len(self.mock_steers()), 2,
                         "a delivered batch was steered again in one turn")

    # -- case C: the predicate, the stable text and the resume restore ------

    def test_delivery_predicate_accepts_only_a_performed_write(self) -> None:
        delivered = self.module.cwd_steer_delivered
        self.assertTrue(delivered({"steer_outcome": "injected"}))
        self.assertTrue(delivered({"steer_outcome": "written",
                                   "mutation_performed": True}))
        self.assertTrue(delivered({"steer_outcome": "queued",
                                   "mutation_performed": True}))
        self.assertFalse(delivered({"steer_outcome": "written"}))
        self.assertFalse(delivered({"steer_outcome": "written",
                                    "mutation_performed": False}))
        self.assertFalse(delivered({"steer_outcome": "queued",
                                    "mutation_performed": None}))
        self.assertFalse(delivered({"steer_outcome": "rejected",
                                    "mutation_performed": False}))
        self.assertFalse(delivered({"steer_outcome": "not_consumed",
                                    "mutation_performed": False}))

    def test_notice_text_is_stable_for_one_pending_batch(self) -> None:
        holder = self.module.Holder.__new__(self.module.Holder)
        holder.tool_cwd = {"notice": "pending", "notice_paths": ["/repo/.kw/worktrees/a"],
                           "notice_ts": None}
        holder.tool_cwd_lock = threading.Lock()
        holder.args = SimpleNamespace(repo="/repo")
        holder.write_record = lambda **extra: None
        first = holder._cwd_notice_text(["/repo/.kw/worktrees/a"])
        second = holder._cwd_notice_text(["/repo/.kw/worktrees/a"])
        self.assertEqual(first, second)
        self.assertIn(holder.tool_cwd["notice_ts"], first)
        self.assertIn("at " + holder.tool_cwd["notice_ts"], first)

        holder.events = SimpleNamespace(append=lambda payload: 1)
        holder._cwd_notice_delivered("steer")
        self.assertEqual(holder.tool_cwd["notice"], "delivered")
        self.assertIsNone(holder.tool_cwd["notice_ts"])

    def test_resume_restores_the_pending_batch_stamp(self) -> None:
        restored = self.module.Holder._restore_tool_cwd({
            "notice": "pending", "notice_paths": ["/repo/wt"],
            "notice_ts": "2026-10-20T14:00:00+0800"})
        self.assertEqual(restored["notice_ts"], "2026-10-20T14:00:00+0800")
        # A stamp without a pending notice announces nothing.
        restored = self.module.Holder._restore_tool_cwd({
            "notice": "delivered", "notice_paths": [],
            "notice_ts": "2026-10-20T14:00:00+0800"})
        self.assertNotIn("notice_ts", restored)


if __name__ == "__main__":
    unittest.main(verbosity=2)
