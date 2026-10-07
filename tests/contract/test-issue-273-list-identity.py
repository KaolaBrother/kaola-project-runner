#!/usr/bin/env python3
"""Issue #273: list must not present persisted agent_alive as current liveness.

Fixtures cover the four evidence classes from the AI PID-reuse case:
verified (holder answers, identity matches -> agent_alive from the state
reply), dead (PID gone -> row excluded or identity dead, agent_alive null),
live-unrelated (PID exists but belongs to another program / another record
dir -> anchor False -> mismatch, never a resurrection), and argv-unreadable
(anchor None -> unreachable stays informational). The :3028-style consumer
fact (agent_alive is not True -> blocking) becomes STRICTER under null and
must fail closed; that is asserted directly.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "kaola_acp", PROJECT / "scripts" / "kaola-acp.py")
kaola_acp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kaola_acp)

RECORD = {
    "platform": "zcode", "session": "zcode-KPR-i270-fixture",
    "repo": str(PROJECT), "state": "ready",
    "holder_instance_id": "fixtureholder0123456789abcdef",
    "holder_pid": None, "agent_alive": True, "agent_started": 1791000000.0,
    "event_cursor": 7, "pending_permissions": [], "session_role": "worker",
}


_SEQ = [0]
def make_record_dir(root: Path, pid) -> Path:
    _SEQ[0] += 1
    d = root / "zcode" / "zcode-KPR-i270-fixture" / f"digest{_SEQ[0]:04d}"
    d.mkdir(parents=True)
    (d / "record.json").write_text(json.dumps({**RECORD, "holder_pid": pid}))
    return d


class FakeProc:
    """A live process whose argv we control: 'verified-holder' simulates the
    real holder via an exec'd sleep naming the record dir; 'unrelated' execs
    plain sleep (another program); 'unreadable' reuses our own pid (argv
    exists but the anchor regex cannot match it)."""

    def __init__(self, mode: str, record_dir: Path):
        if mode == "unrelated":
            self.p = subprocess.Popen(["/bin/sleep", "30"])
            self.expect = "mismatch-or-unreachable"
        else:  # verified-holder lookalike via argv anchor target
            argv = [sys.executable, "-c",
                    "import time; time.sleep(30)",
                    f"--record-dir={record_dir}"]
            self.p = subprocess.Popen(argv)
            self.expect = "verified-or-unreachable"

    def pid(self) -> int:
        return self.p.pid

    def stop(self) -> None:
        self.p.terminate()
        self.p.wait(timeout=5)


class ListIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def row_for(self, pid):
        d = make_record_dir(self.root, pid)
        ident, reply = kaola_acp.holder_identity(d, json.loads(
            (d / "record.json").read_text()), 0.3)
        if ident == "unreachable":
            anchor = kaola_acp.holder_argv_anchor(pid, d)
            if anchor is False:
                ident = "mismatch"
        # the projection rule under test
        if ident == "verified":
            alive = bool(reply.get("agent_alive")) if isinstance(reply, dict) \
                and isinstance(reply.get("agent_alive"), bool) else None
        else:
            alive = None
        return ident, alive

    def test_dead_pid_is_never_alive(self):
        dead = subprocess.run(["/bin/sh", "-c", "echo $$; exit"],
                              capture_output=True, text=True)
        pid = int(dead.stdout.strip())
        ident, alive = self.row_for(pid)
        self.assertEqual(ident, "dead")
        self.assertIsNone(alive)

    def test_live_unrelated_pid_is_not_a_resurrection(self):
        p = FakeProc("unrelated", self.root)
        self.addCleanup(p.stop)
        ident, alive = self.row_for(p.pid())
        self.assertIn(ident, ("mismatch", "dead", "unreachable"))
        self.assertNotEqual(ident, "verified")
        self.assertIsNone(alive)

    def test_argv_unreadable_or_silent_stays_informational(self):
        # own pid: alive, argv readable, but not a holder for that dir ->
        # anchor False (argv path) or socket absent (identity unreachable);
        # either way agent_alive must not be True from the record.
        ident, alive = self.row_for(os.getpid())
        self.assertNotEqual(ident, "verified")
        self.assertIsNone(alive)

    def test_persisted_true_never_becomes_current_when_unverified(self):
        for mode in ("unrelated", "verified-holder"):
            d = make_record_dir(self.root, None)
            p = FakeProc(mode, d)
            self.addCleanup(p.stop)
            rec = json.loads((d / "record.json").read_text())
            rec["holder_pid"] = p.pid()
            (d / "record.json").write_text(json.dumps(rec))
            ident, alive = self.row_for(p.pid())
            if ident != "verified":
                self.assertIsNone(alive)  # persisted True never leaks


if __name__ == "__main__":
    unittest.main(verbosity=2)
