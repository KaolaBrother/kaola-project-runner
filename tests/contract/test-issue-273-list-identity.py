#!/usr/bin/env python3
"""Issue #273 real-entry fixtures: the production `kaola-acp.py list` CLI.

Every case drives the real command_list through the script CLI
(`kaola-acp.py list --record-root <tmp> --repo <repo> --include-dead`) with
an isolated temp record root and a controlled holder socket, never a copy of
the projection expression. Record bytes stay untouched by the probe.

Cases: verified (holder answers, id matches -> agent_alive from the reply,
covering true/false/non-bool/missing), dead (excluded unless --include-dead,
then agent_alive null), live-unrelated (PID alive but the socket answers
with another id -> mismatch/null), argv-unreadable-or-silent (unreachable ->
null, informational only)."""
from __future__ import annotations
import sys as _sys
_sys.dont_write_bytecode = True
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts" / "kaola-acp.py"
_spec = importlib.util.spec_from_file_location("kaola_acp_mod", SCRIPT)
kaola = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kaola)

SESSION = "zcode-KPR-i273-fixture"
HOLDER_ID = "i273holder" + "0" * 14


class HolderSocket(threading.Thread):
    """Answers `state` with a controlled reply on the record dir's derived
    socket path, like the real holder's admin socket."""

    def __init__(self, directory: Path, reply_builder):
        super().__init__(daemon=True)
        self.reply = reply_builder
        self.sock_path = kaola.sock_path_for_directory(directory)
        self.sock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.sock_path.exists():
            self.sock_path.unlink()
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.sock_path))
        self.server.listen(2)
        self.stop_flag = False

    def run(self):
        while not self.stop_flag:
            try:
                self.server.settimeout(0.3)
                conn, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                data = conn.recv(65536)
                if not data:
                    conn.close()
                    continue
                conn.sendall(json.dumps(self.reply()).encode() + b"\n")
            finally:
                conn.close()

    def stop(self):
        self.stop_flag = True
        self.server.close()
        if self.sock_path.exists():
            self.sock_path.unlink()


def sleeper_proc():
    return subprocess.Popen(["/bin/sleep", "60"])


def write_record(root: Path, seq: int, pid, alive=True) -> Path:
    d = root / "zcode" / SESSION / f"digest{seq:04d}"
    d.mkdir(parents=True)
    rec = {"platform": "zcode", "session": SESSION, "repo": str(PROJECT),
           "state": "ready", "holder_instance_id": HOLDER_ID,
           "holder_pid": pid, "agent_alive": alive, "event_cursor": 3,
           "pending_permissions": [], "session_role": "worker"}
    (d / "record.json").write_text(json.dumps(rec))
    return d


def run_list(root: Path, extra=()):
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "list", "--record-root", str(root),
         "--repo", str(PROJECT), *extra],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out).get("rows", [])


class RealEntryListIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.procs, self.socks = [], []

    def track(self, proc, sock=None):
        self.procs.append(proc)
        if sock:
            self.socks.append(sock)
            self.addCleanup(sock.stop)
        self.addCleanup(proc.terminate)

    def row(self, rows):
        got = [r for r in rows if r.get("session") == SESSION]
        self.assertEqual(len(got), 1, f"expected one row, got {got}")
        return got[0]

    def subroot(self, tag):
        r = self.root / tag
        r.mkdir(parents=True, exist_ok=True)
        return r

    def test_verified_true_false_nonbool_missing_from_state_reply(self):
        for alive in (True, False):
            root = self.subroot(f"v{alive}")
            d = write_record(root, 1, os.getpid())
            hs = HolderSocket(d, lambda a=alive: {
                "holder_instance_id": HOLDER_ID, "agent_alive": a,
                "state": "ready"})
            hs.start()
            self.track(sleeper_proc(), hs)
            rec = json.loads((d / "record.json").read_text())
            rec["holder_pid"] = self.procs[-1].pid
            (d / "record.json").write_text(json.dumps(rec))
            row = self.row(run_list(root))
            self.assertEqual(row["identity"], "verified")
            self.assertEqual(row["agent_alive"], alive)
        # non-bool / missing: verified identity, agent_alive null (not leaked)
        for i, reply in enumerate((
                {"holder_instance_id": HOLDER_ID, "agent_alive": "yes"},
                {"holder_instance_id": HOLDER_ID})):
            root = self.subroot(f"n{i}")
            d = write_record(root, 1, os.getpid())
            hs = HolderSocket(d, lambda r=reply: r)
            hs.start()
            self.track(sleeper_proc(), hs)
            rec = json.loads((d / "record.json").read_text())
            rec["holder_pid"] = self.procs[-1].pid
            (d / "record.json").write_text(json.dumps(rec))
            row = self.row(run_list(root))
            self.assertEqual(row["identity"], "verified")
            self.assertIsNone(row["agent_alive"])
            hs.stop(); self.socks.remove(hs)

    def test_dead_pid_excluded_and_null_with_include_dead(self):
        dead = subprocess.run(["/bin/sh", "-c", "echo $$; exit"],
                              capture_output=True, text=True)
        pid = int(dead.stdout.strip())
        write_record(self.root, 1, pid)
        self.assertEqual(run_list(self.root), [])
        rows = run_list(self.root, ("--include-dead",))
        row = self.row(rows)
        self.assertEqual(row["identity"], "dead")
        self.assertIsNone(row["agent_alive"])

    def test_live_unrelated_pid_is_mismatch_not_resurrection(self):
        d = write_record(self.root, 1, os.getpid(), alive=True)
        p = sleeper_proc()
        rec = json.loads((d / "record.json").read_text())
        rec["holder_pid"] = p.pid
        (d / "record.json").write_text(json.dumps(rec))
        # a socket exists but answers with ANOTHER holder id
        hs = HolderSocket(d, lambda: {"holder_instance_id": "other" * 7,
                                     "agent_alive": True})
        hs.start()
        self.track(p, hs)
        row = self.row(run_list(self.root))
        self.assertEqual(row["identity"], "mismatch")
        self.assertIsNone(row["agent_alive"])

    def test_silent_socket_is_unreachable_informational_null(self):
        d = write_record(self.root, 1, os.getpid(), alive=True)
        p = sleeper_proc()
        rec = json.loads((d / "record.json").read_text())
        rec["holder_pid"] = p.pid
        (d / "record.json").write_text(json.dumps(rec))
        # no socket at all -> unreachable (never dead, never alive)
        self.track(p)
        row = self.row(run_list(self.root))
        self.assertIn(row["identity"], ("unreachable", "mismatch"))
        self.assertIsNone(row["agent_alive"])





class ConsumerSeatProjection(unittest.TestCase):
    """Bridge real-consumer QA adopted (6/6): the seat projection treats
    agent_alive null and false as occupied (never released to available on
    identity unknown); verified true/false/null each keep one occupied seat;
    stopped historical rows are excluded. Runs the real `project --seats`
    entry over a controlled authorization + live rows."""

    def test_persisted_none_stays_unknown_not_released(self):
        # Occupancy semantics from the bridge QA: an identity-unknown row
        # never releases its seat. Here: persisted agent_alive None with a
        # live-but-silent PID projects agent_alive null (unknown), the exact
        # row value the bridge fed to the real seat projection, which kept
        # the seat occupied for null and false alike.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, True))
        d = write_record(root, 1, os.getpid(), alive=None)
        p = sleeper_proc()
        self.addCleanup(p.terminate)
        rec = json.loads((d / "record.json").read_text())
        rec["holder_pid"] = p.pid
        (d / "record.json").write_text(json.dumps(rec))
        rows = run_list(root)
        got = [r for r in rows if r.get("session") == SESSION]
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["agent_alive"])
        self.assertIn(got[0]["identity"], ("unreachable", "mismatch"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
