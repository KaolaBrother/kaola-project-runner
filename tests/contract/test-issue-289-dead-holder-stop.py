#!/usr/bin/env python3
"""Issue #289: a dead-holder stop must honor --expected-holder-instance-id.

Temp records and this test's own sleep process groups only. No ACP holder,
no mock agent, and no real session is started. A foreign expected id is
refused with the live silent-holder mismatch and one holder_instance_mismatch
event. A matching id, or none, still sweeps the verified group without
--force.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaola-acp.py"
FOREIGN = "0" * 32
OWN_ID = "ab" * 16


class DeadHolderStopTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-289-")
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.repo = Path(os.path.realpath(self.repo))
        self.record_root = self.root / "records"
        self.session = f"i289{self._testMethodName.replace('_', '')[:40]}{os.getpid()}"
        self.session = self.session[:79]
        self.procs: list[subprocess.Popen] = []
        self.directory = self._directory()
        self.directory.mkdir(parents=True)

    def tearDown(self) -> None:
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
        self._tmp.cleanup()

    def _directory(self) -> Path:
        digest = hashlib.sha256(str(self.repo).encode("utf-8")).hexdigest()[:16]
        return self.record_root / "grok" / self.session / digest

    def _env(self) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("KAOLA_") and not key.startswith("KPR_")
        }
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        return env

    def _module(self):
        spec = importlib.util.spec_from_file_location(
            f"acp289_{self._testMethodName}", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _dead_pid(self) -> int:
        for _ in range(8):
            child = subprocess.Popen(["/usr/bin/true"])
            child.wait(timeout=5)
            try:
                os.kill(child.pid, 0)
            except ProcessLookupError:
                return child.pid
        self.fail("could not observe a dead pid")

    def _spawn_group(self) -> subprocess.Popen:
        proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.procs.append(proc)
        self.assertIsNone(proc.poll(), "the dummy group exited before the stop")
        return proc

    def _started_epoch(self, pid: int) -> float:
        module = self._module()
        table = module.run_ps(["pid", "pgid", "state", "lstart"], env=module.PS_ENV)
        started = next(
            line.split(None, 3)[3].strip()
            for line in table.stdout.splitlines()
            if line.split(None, 1) and line.split(None, 1)[0] == str(pid)
        )
        return time.mktime(time.strptime(started, "%a %b %d %H:%M:%S %Y"))

    def _write_record(self, holder_pid: int, group: subprocess.Popen | None,
                      **extra) -> dict:
        record = {
            "transport": "acp",
            "platform": "grok",
            "session": self.session,
            "repo": str(self.repo),
            "holder_pid": holder_pid,
            "holder_instance_id": OWN_ID,
            "state": "ready",
            "agent_alive": group is not None,
            "pending_permissions": [],
            "event_cursor": 0,
        }
        if group is not None:
            record.update(
                agent_pid=group.pid,
                agent_pgid=group.pid,
                agent_started=self._started_epoch(group.pid),
            )
        record.update(extra)
        path = self.directory / "record.json"
        path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        return record

    def _stop(self, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "grok", "stop",
             "--repo", str(self.repo), "--session", self.session,
             "--command", "/usr/bin/true", *args],
            capture_output=True, text=True, env=self._env(), timeout=30,
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"stop emitted no JSON\nrc={result.returncode}\n"
                f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
            )

    def _events(self) -> list[dict]:
        path = self.directory / "events.jsonl"
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _mismatch_events(self) -> list[dict]:
        return [row for row in self._events()
                if row.get("kind") == "holder_instance_mismatch"]

    def _assert_refused(self, receipt: dict, record_bytes: bytes,
                        group: subprocess.Popen) -> None:
        self.assertEqual(receipt.get("error"), {
            "code": "holder-instance-mismatch",
            "expected_holder_instance_id": FOREIGN,
            "holder_instance_id": OWN_ID,
        }, receipt)
        self.assertEqual(receipt.get("mutation_status"), "not_started", receipt)
        self.assertIs(receipt.get("mutation_performed"), False, receipt)
        self.assertNotIn("force_killed_pids", receipt, receipt)
        self.assertNotIn("holder_lost", receipt, receipt)
        self.assertIsNot(receipt.get("stopped"), True, receipt)
        self.assertEqual((self.directory / "record.json").read_bytes(), record_bytes)
        self.assertIsNone(group.poll(), "the dummy group was signalled")
        events = self._mismatch_events()
        self.assertEqual(len(events), 1, self._events())
        event = events[0]
        self.assertEqual(event.get("op"), "stop", event)
        self.assertEqual(event.get("expected_holder_instance_id"), FOREIGN, event)
        self.assertIsInstance(event.get("cursor"), int, event)
        self.assertNotIsInstance(event.get("cursor"), bool, event)

    def _assert_swept(self, receipt: dict, group: subprocess.Popen) -> None:
        self.assertIs(receipt.get("holder_lost"), True, receipt)
        self.assertNotIn("error", receipt, receipt)
        self.assertIn(group.pid, receipt.get("force_killed_pids") or [], receipt)
        self.assertEqual(receipt.get("residual_pids"), [], receipt)
        self.assertEqual(self._mismatch_events(), [], self._events())
        group.wait(timeout=5)
        record = json.loads((self.directory / "record.json").read_text(encoding="utf-8"))
        self.assertEqual(record.get("state"), "stopped", record)

    def test_dead_holder_foreign_id_without_force_changes_nothing(self) -> None:
        group = self._spawn_group()
        self._write_record(self._dead_pid(), group)
        before = (self.directory / "record.json").read_bytes()
        receipt = self._stop("--expected-holder-instance-id", FOREIGN)
        self._assert_refused(receipt, before, group)

    def test_dead_holder_foreign_id_with_force_changes_nothing(self) -> None:
        group = self._spawn_group()
        self._write_record(self._dead_pid(), group)
        before = (self.directory / "record.json").read_bytes()
        receipt = self._stop("--force", "--expected-holder-instance-id", FOREIGN)
        self._assert_refused(receipt, before, group)

    def test_dead_holder_matching_id_sweeps_without_force(self) -> None:
        group = self._spawn_group()
        self._write_record(self._dead_pid(), group)
        receipt = self._stop("--expected-holder-instance-id", OWN_ID)
        self._assert_swept(receipt, group)

    def test_dead_holder_omitted_id_sweeps_without_force(self) -> None:
        group = self._spawn_group()
        self._write_record(self._dead_pid(), group)
        receipt = self._stop()
        self._assert_swept(receipt, group)

    def test_live_unreachable_foreign_id_writes_one_mismatch_event(self) -> None:
        """The live silent-holder path already refuses. It must also write the event."""
        holder = self._spawn_group()
        group = self._spawn_group()
        self._write_record(holder.pid, group)
        before = (self.directory / "record.json").read_bytes()
        receipt = self._stop("--force", "--expected-holder-instance-id", FOREIGN)
        self._assert_refused(receipt, before, group)
        self.assertIsNone(holder.poll(), "the stand-in holder pid was signalled")

    def test_unreachable_reply_after_holder_death_still_refuses(self) -> None:
        """The holder-unreachable branch must use the same check once the pid is dead."""
        group = self._spawn_group()
        holder_pid = self._dead_pid()
        sock = self.root / "silent.sock"
        sock.write_bytes(b"")
        self._write_record(holder_pid, group, socket_path=str(sock))
        before = (self.directory / "record.json").read_bytes()
        module = self._module()
        seen = {"n": 0}
        real_alive = module.pid_alive

        def alive(pid):
            seen["n"] += 1
            if seen["n"] == 1 and pid == holder_pid:
                return True
            return real_alive(pid)

        module.pid_alive = alive
        module.socket_request = lambda *_args, **_kwargs: {
            "error": {"code": "holder-unreachable"}
        }
        args = argparse.Namespace(
            platform="grok",
            session=self.session,
            record_root=str(self.record_root),
            command="stop",
            preserve_dispatched_workers=False,
        )
        receipt = module.op_or_holder_lost(
            args, str(self.repo), self.directory, "stop",
            {"force": False, "expected_holder_instance_id": FOREIGN}, 1.0,
        )
        self._assert_refused(receipt, before, group)
        self.assertTrue(sock.is_file(), "a refused stop unlinked the socket path")


if __name__ == "__main__":
    unittest.main(verbosity=2)
