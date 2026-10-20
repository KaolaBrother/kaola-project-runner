#!/usr/bin/env python3
"""Issue #374: the `worktree-guard` receipt Kaola-Workflow consumes is frozen here.

Kaola-Workflow calls ``kaola-dispatch.py worktree-guard --repo <root> --path <wt>``
before its own ``git worktree remove``. This suite is the KPR-side gate for that
consumer contract:

1. the clear, occupied and ``cwd-unverifiable`` receipts keep exactly the fields
   documented in ``docs/api.md`` (a rename or a dropped field fails here);
2. the exit codes scripts consume are stable: 0 clear, 3 occupied /
   ``cwd-unverifiable``, 2 refused (missing repo);
3. every verified ``list --include-dead`` row whose ``repo`` is the repo or the
   target counts, whatever its ``session_role``: a Host, a Sideagent and a seat
   (worker) each appear as an occupant, and a live process tree is probed too.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"

# The frozen consumer surface. Exact equality is deliberate: the point of the
# contract is that removing or renaming a field breaks this gate, not that an
# additive field is silently admitted.
GUARD_FIELDS = {"schema", "repo", "path", "result", "occupants", "probe", "route"}
CLEAR_FIELDS = {"schema", "repo", "path", "result", "occupants", "probe"}
OCCUPANT_FIELDS = {"pid", "ppid", "exe_basename", "cwd", "cwd_deleted", "source", "session"}
SESSION_FIELDS = {"platform", "session", "role", "holder_instance_id"}
REFUSED_FIELDS = {"schema", "result", "reason", "detail", "route"}
SCHEMA = "kaola-worktree-remove/1"


def load_dispatch():
    spec = importlib.util.spec_from_file_location("kaola_dispatch_i374_contract", DISPATCH)
    assert spec is not None and spec.loader is not None, DISPATCH
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


dispatch = load_dispatch()


class WorktreeGuardContract(unittest.TestCase):
    """The receipt and exit codes Kaola-Workflow depends on."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i374-")
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "i374@example.invalid")
        self.git("config", "user.name", "Issue 374")
        self.git("commit", "-q", "--allow-empty", "-m", "base")
        self.wt = Path(self.tmp.name) / "wt"
        self.git("worktree", "add", "-q", "-b", "workflow/issue-374", str(self.wt))
        self.rows_path = Path(self.tmp.name) / "rows.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *argv: str) -> str:
        done = subprocess.run(["git", "-C", str(self.repo), *argv],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def run_guard(self, rows: list[dict]) -> tuple[subprocess.CompletedProcess, dict]:
        self.rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
        done = subprocess.run(
            [sys.executable, str(DISPATCH), "worktree-guard",
             "--repo", str(self.repo), "--path", str(self.wt),
             "--live", str(self.rows_path)],
            cwd=str(self.repo), capture_output=True, text=True, timeout=120)
        self.assertTrue(done.stdout.strip(), done.stderr)
        return done, json.loads(done.stdout)

    def row(self, role: str, **fields) -> dict:
        row = {
            "platform": "codex",
            "session": "codex-374-" + role,
            "repo": str(self.repo),
            "identity": "verified",
            "name_role": role,
            "session_role": role,
            "holder_instance_id": "h-374-" + role,
            "holder_pid": None,
            "agent_pid": None,
            "tool_cwd_path": str(self.wt),
        }
        row.update(fields)
        return row

    def test_clear_receipt_is_frozen_and_exits_zero(self) -> None:
        done, receipt = self.run_guard([])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(set(receipt), CLEAR_FIELDS, receipt)
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertEqual(receipt["result"], "clear")
        self.assertEqual(receipt["repo"], str(self.repo.resolve()))
        self.assertEqual(receipt["path"], str(self.wt.resolve()))
        self.assertEqual(receipt["occupants"], [])
        self.assertTrue(receipt["probe"])

    def test_host_sideagent_and_seat_rows_are_each_occupants(self) -> None:
        for role in ("host", "sideagent", "worker"):
            with self.subTest(role=role):
                done, receipt = self.run_guard([self.row(role)])
                self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
                self.assertEqual(set(receipt), GUARD_FIELDS, receipt)
                self.assertEqual(receipt["schema"], SCHEMA)
                self.assertEqual(receipt["result"], "occupied")
                self.assertTrue(receipt["route"], receipt)
                self.assertEqual(len(receipt["occupants"]), 1, receipt["occupants"])
                occupant = receipt["occupants"][0]
                self.assertEqual(set(occupant), OCCUPANT_FIELDS, occupant)
                self.assertIsNone(occupant["pid"])
                self.assertIsNone(occupant["ppid"])
                self.assertIsNone(occupant["exe_basename"])
                self.assertEqual(Path(occupant["cwd"]).resolve(), self.wt.resolve())
                self.assertEqual(occupant["source"], "recorded")
                self.assertFalse(occupant["cwd_deleted"])
                self.assertEqual(set(occupant["session"]), SESSION_FIELDS, occupant["session"])
                self.assertEqual(occupant["session"]["role"], role)
                self.assertEqual(occupant["session"]["platform"], "codex")

    def test_live_process_tree_of_a_seat_is_an_occupant(self) -> None:
        live = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=str(self.wt), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            done, receipt = self.run_guard([
                self.row("worker", holder_pid=live.pid, tool_cwd_path=None)])
            self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
            self.assertEqual(receipt["result"], "occupied")
            found = [occ for occ in receipt["occupants"] if occ["pid"] == live.pid]
            self.assertTrue(found, receipt["occupants"])
            self.assertEqual(found[0]["source"], "process")
            self.assertEqual(found[0]["session"]["role"], "worker")
        finally:
            live.terminate()
            live.wait(timeout=30)

    def test_cwd_unverifiable_exits_three_and_is_frozen(self) -> None:
        args = argparse.Namespace(repo=str(self.repo), path=str(self.wt), live=None,
                                  skills_root=None, all_user_processes=False)
        saved = dispatch._worktree_occupancy
        dispatch._worktree_occupancy = lambda *a, **k: {
            "result": "unverifiable", "occupants": [], "probe": "none"}
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = dispatch.command_worktree_guard(args)
        finally:
            dispatch._worktree_occupancy = saved
        self.assertEqual(code, 3, buf.getvalue())
        receipt = json.loads(buf.getvalue())
        self.assertEqual(set(receipt), GUARD_FIELDS, receipt)
        self.assertEqual(receipt["result"], "unverifiable")
        self.assertEqual(receipt["occupants"], [])
        self.assertTrue(receipt["route"], receipt)

    def test_missing_repo_is_a_refusal_with_exit_two(self) -> None:
        done = subprocess.run(
            [sys.executable, str(DISPATCH), "worktree-guard",
             "--repo", str(Path(self.tmp.name) / "absent"), "--path", str(self.wt)],
            cwd=str(self.repo), capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        receipt = json.loads(done.stdout)
        self.assertEqual(set(receipt), REFUSED_FIELDS, receipt)
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertEqual(receipt["result"], "refused")
        self.assertEqual(receipt["reason"], "repo-missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
