#!/usr/bin/env python3
"""Issue #369 Fix 1 / #389: a removal never leaves a shell dangling.

Reuses the Issue #348 tool harness (bare origin + clone + real linked
worktrees, fake ``gh``, fake skills root with a scripted ``kaola-acp.py list``):

1. a live process cwd inside the target (listed as a verified session with
   ``agent_pid``) is recoverable under Issue #389: the sweep removes the
   worktree, carries `occupied-cwd-recoverable` in the receipt warnings, and
   the post-check restores an empty placeholder so the shell never dangles;
2. a recorded tool cwd (`tool_cwd_path`) inside the target is an occupant with
   `source: recorded`, with no live process at all; it only warns and the
   worktree is removed;
3. `worktree-remove` invoked from inside the worktree relocates its own cwd
   first and then removes it;
4. the check-then-delete race: a live cwd that appears between the check and
   the removal is caught by the post-check and repaired into an empty
   placeholder;
5. an unavailable cwd probe answers `cwd-unverifiable`, proceeds with a typed
   warning, and removes the worktree. A live cwd plus uncommitted changes is
   the one hard block (covered by the #374 contract suite).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"
ISSUE348 = REPO / "tests" / "contract" / "test-issue-348-backstop-sweep.py"
SHELL_BIN = next((path for path in ("/bin/zsh", "/bin/bash", "/bin/sh")
                  if os.path.exists(path)), None)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


dispatch = load_module("kaola_dispatch_i369_guard", DISPATCH)
issue348 = load_module("issue348_i369_guard", ISSUE348)

# Issue #348's tool harness (temp repo, fake gh, fake skills root) as a plain
# mixin: its own tests stay in its own suite and are not replayed here.
SweepHarness = type("SweepHarness", (), {
    name: value for name, value in vars(issue348.SweepTool).items()
    if not name.startswith("test_") and not name.startswith("__")})


class WorktreeGuard(SweepHarness, unittest.TestCase):
    """The guarded removal and the sweep that reuses it."""

    def live_process(self, cwd: Path) -> subprocess.Popen:
        return subprocess.Popen([SHELL_BIN, "-c", "while :; do sleep 5; done"], cwd=str(cwd),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def session_row(self, pid: int, **kw) -> dict:
        return {"platform": "opencode", "session": "opencode-KT-i99-guard",
                "repo": str(self.repo), "identity": "verified", "name_role": "worker",
                "session_role": "worker", "holder_instance_id": "h-i99", "state": "ready",
                "holder_pid": os.getpid(), "agent_pid": pid, **kw}

    def worktree_item(self, out: dict, path: Path) -> dict:
        items = [item for item in out.get("kept", [])
                 if str(item.get("path")) and Path(item["path"]).resolve() == path.resolve()]
        self.assertTrue(items, out.get("kept"))
        return items[0]

    def warning(self, out: dict, path: Path) -> dict:
        items = [item for item in out.get("warnings", [])
                 if str(item.get("path")) and Path(item["path"]).resolve() == path.resolve()]
        self.assertTrue(items, out.get("warnings"))
        return items[0]

    def test_live_cwd_is_recoverable_and_gets_a_placeholder(self) -> None:
        if SHELL_BIN is None:
            self.skipTest("no shell binary on this host")
        self.init_state()
        path = self.add_worktree(41)
        self.issues["41"] = "CLOSED"
        self.prs["41"] = self.worktree_head(path)
        self.write_gh()
        live = self.live_process(path)
        try:
            self.set_rows([self.session_row(live.pid)])
            code, out = self.sweep("--apply")
            self.assertEqual(code, 0, out)
            self.assertTrue(any(ident.startswith("worktree:") and "issue-41" in ident
                                for ident in out["removed"]), out)
            self.assertEqual(out["kept"], [], out)
            self.assertEqual(self.warning(out, path)["code"],
                             "occupied-cwd-recoverable")
            # The post-check repaired the live cwd into an empty placeholder.
            self.assertTrue(path.is_dir(), out)
            self.assertEqual(list(path.iterdir()), [])
        finally:
            live.terminate()
            live.wait(timeout=30)

    def test_recorded_tool_cwd_only_warns_and_removes(self) -> None:
        self.init_state()
        path = self.add_worktree(42)
        self.issues["42"] = "CLOSED"
        self.prs["42"] = self.worktree_head(path)
        self.write_gh()
        self.set_rows([self.session_row(0, agent_pid=None, tool_cwd_path=str(path),
                                        tool_cwd_exists=True)])
        code, out = self.sweep("--apply")
        self.assertEqual(code, 0, out)
        self.assertTrue(any(ident.startswith("worktree:") and "issue-42" in ident
                            for ident in out["removed"]), out)
        self.assertEqual(out["kept"], [], out)
        self.assertEqual(self.warning(out, path)["code"],
                         "occupied-cwd-recoverable")
        self.assertFalse(path.exists())

    def test_worktree_remove_relocates_its_own_cwd(self) -> None:
        path = self.add_worktree(43)
        rows = Path(self.tmp.name) / "rows.json"
        rows.write_text(json.dumps({"rows": []}), encoding="utf-8")
        argv = [sys.executable, str(DISPATCH), "worktree-remove", "--repo", str(self.repo),
                "--path", str(path), "--live", str(rows)]
        done = subprocess.run(argv, capture_output=True, text=True, cwd=str(path), timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipt = json.loads(done.stdout)
        self.assertEqual(receipt["result"], "removed")
        self.assertEqual(receipt["actions"][0]["action"], "relocated")
        self.assertEqual(receipt["actions"][0]["occupant"], "self")
        self.assertFalse(path.exists())

    def test_the_race_is_repaired_into_an_empty_placeholder(self) -> None:
        path = self.add_worktree(44)
        calls: list[int] = []

        def occupancy(args, repo, target, rows=None, known=None):
            calls.append(1)
            if len(calls) == 1:
                return {"result": "clear", "occupants": [], "probe": "lsof"}
            return {"result": "occupied", "probe": "lsof", "occupants": [
                {"pid": os.getpid() + 1, "ppid": None, "exe_basename": "zsh",
                 "cwd": str(target), "cwd_deleted": True, "source": "process",
                 "session": None}]}

        saved = dispatch._worktree_occupancy
        dispatch._worktree_occupancy = occupancy
        try:
            args = argparse.Namespace(live=None, skills_root=None, assume_clear=False,
                                      all_user_processes=False)
            receipt = dispatch._worktree_remove(args, self.repo.resolve(), path.resolve())
        finally:
            dispatch._worktree_occupancy = saved
        self.assertEqual(receipt["result"], "removed")
        self.assertEqual(receipt.get("action"), "placeholder-restored")
        self.assertEqual(receipt["post_check"]["result"], "occupied")
        self.assertTrue(path.is_dir())
        self.assertEqual(list(path.iterdir()), [])

    def test_relocation_failure_warns_and_still_removes(self) -> None:
        path = self.add_worktree(49)
        args = argparse.Namespace(live=None, skills_root=None, assume_clear=False,
                                  all_user_processes=False)
        saved = dispatch._worktree_relocate_self
        dispatch._worktree_relocate_self = lambda target, repo: {
            "action": "relocate-failed", "occupant": "self",
            "cwd": str(target), "error": "denied"}
        try:
            receipt = dispatch._worktree_remove(
                args, self.repo.resolve(), path.resolve(), rows=[], known=True)
        finally:
            dispatch._worktree_relocate_self = saved
        self.assertEqual(receipt["result"], "removed", receipt)
        self.assertEqual(receipt["actions"][0]["action"], "relocate-failed")
        self.assertEqual(receipt["warnings"][0]["code"],
                         "occupied-cwd-recoverable")
        self.assertFalse(path.exists())

    def test_live_cwd_plus_uncommitted_changes_defers_the_wrapper(self) -> None:
        if SHELL_BIN is None:
            self.skipTest("no shell binary on this host")
        path = self.add_worktree(48)
        (path / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
        live = self.live_process(path)
        try:
            args = argparse.Namespace(live=None, skills_root=None, assume_clear=False,
                                      all_user_processes=False)
            receipt = dispatch._worktree_remove(
                args, self.repo.resolve(), path.resolve(),
                rows=[self.session_row(live.pid)], known=True)
            self.assertEqual(receipt["result"], "deferred", receipt)
            self.assertEqual(receipt["reason"], "cwd-occupied", receipt)
            self.assertIn("uncommitted", receipt["route"], receipt)
            self.assertEqual(receipt["warnings"], [])
            self.assertTrue(path.exists())
        finally:
            live.terminate()
            live.wait(timeout=30)

    def test_remove_failed_detail_carries_git_stderr(self) -> None:
        """Deviation b: git reports a failed removal on stderr, so `detail`
        must not be empty."""
        path = self.add_worktree(46)
        locked = subprocess.run(["git", "-C", str(self.repo), "worktree", "lock",
                                 str(path)], capture_output=True, text=True)
        self.assertEqual(locked.returncode, 0, locked.stderr)
        try:
            args = argparse.Namespace(live=None, skills_root=None, assume_clear=False,
                                      all_user_processes=False)
            receipt = dispatch._worktree_remove(args, self.repo.resolve(), path.resolve(),
                                                rows=[], known=True)
            self.assertEqual(receipt["result"], "deferred", receipt)
            self.assertEqual(receipt["reason"], "remove-failed", receipt)
            self.assertTrue(receipt.get("detail"), receipt)
            self.assertIn("locked", receipt["detail"], receipt)
            self.assertTrue(path.exists())
        finally:
            subprocess.run(["git", "-C", str(self.repo), "worktree", "unlock", str(path)],
                           capture_output=True)

    def _unavailable_probe_linux(self, path: Path) -> None:
        """Linux always has /proc, so an absent lsof is not an unavailable
        probe; simulate the unreadable /proc answer ``read_cwds`` reports."""
        guard = dispatch._load_cwd_guard()
        saved = guard.read_cwds
        guard.read_cwds = lambda pids: ("proc", {}, True)
        try:
            repo = self.repo.resolve()
            args = argparse.Namespace(live=None, skills_root=None, assume_clear=False,
                                      all_user_processes=False)
            occupancy = dispatch._worktree_occupancy(args, repo, path.resolve(),
                                                     rows=[], known=True)
            self.assertEqual(occupancy["result"], "unverifiable", occupancy)
            receipt = dispatch._worktree_remove(args, repo, path.resolve(),
                                                rows=[], known=True)
            self.assertEqual(receipt["result"], "removed", receipt)
            self.assertEqual(receipt["warnings"][0]["code"], "cwd-unverifiable")
            self.assertFalse(path.exists())
            # The compatibility flag still removes normally.
            second = self.add_worktree(47)
            args.assume_clear = True
            receipt = dispatch._worktree_remove(args, repo, second.resolve(),
                                                rows=[], known=True)
            self.assertEqual(receipt["result"], "removed", receipt)
            self.assertFalse(second.exists())
        finally:
            guard.read_cwds = saved

    def test_unavailable_probe_proceeds_with_warning(self) -> None:
        path = self.add_worktree(45)
        if sys.platform.startswith("linux"):
            # Deviation e: the /proc probe always answers on Linux.
            self._unavailable_probe_linux(path)
            return
        # A PATH with the tools the wrapper needs and no cwd probe.
        stub = Path(self.tmp.name) / "no-probe-bin"
        stub.mkdir(exist_ok=True)
        for name in ("ps", "git", "python3", "sh", "env"):
            found = shutil.which(name)
            if found:
                link = stub / name
                if not link.exists():
                    link.symlink_to(found)
        env = {key: value for key, value in os.environ.items()}
        env["PATH"] = str(stub)
        rows = Path(self.tmp.name) / "rows-empty.json"
        rows.write_text(json.dumps({"rows": []}), encoding="utf-8")
        guard_argv = [sys.executable, str(DISPATCH), "worktree-guard", "--repo", str(self.repo),
                      "--path", str(path), "--live", str(rows)]
        done = subprocess.run(guard_argv, capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipt = json.loads(done.stdout)
        self.assertEqual(receipt["result"], "unverifiable")
        self.assertEqual(receipt["warnings"][0]["code"], "cwd-unverifiable")
        self.assertIn("route", receipt)
        self.assertTrue(path.exists())

        remove_argv = [sys.executable, str(DISPATCH), "worktree-remove", "--repo", str(self.repo),
                       "--path", str(path), "--live", str(rows)]
        done = subprocess.run(remove_argv, capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipt = json.loads(done.stdout)
        self.assertEqual(receipt["result"], "removed")
        self.assertEqual(receipt["warnings"][0]["code"], "cwd-unverifiable")
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
