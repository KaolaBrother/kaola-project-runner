#!/usr/bin/env python3
"""Issue #369: a shell cwd removed under a live shell, and the removal guard.

Tool level: the real ``kaola-dispatch.py sweep`` runs against a temp repo, a
fake ``gh`` and a fake skills root, with a live process cwd inside a closed
issue's linked worktree. The plan and the delete-time re-check both defer the
removal (``live-cwd``), the receipt names the process and its cwd, the state
alert carries the recovery, and the worktree survives. With that cwd gone the
same worktree is planned again.

Contract level: a shell tool that keeps its working directory between calls
loses it to ``git worktree remove``. Every later call fails with ENOENT while
the shell binary exists, and the documented route recovers the shell in place
with no Host restart.
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
ROUTES_PATH = REPO / "scripts" / "kaola-recovery-routes.py"
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


dispatch = load_module("kaola_dispatch_i369", DISPATCH)
routes = load_module("kaola_recovery_routes_i369", ROUTES_PATH)
issue348 = load_module("issue348_i369", ISSUE348)

# Issue #348's tool harness (temp repo, fake gh, fake skills root) as a plain
# mixin: its own tests stay in its own suite and are not replayed here.
SweepHarness = type("SweepHarness", (), {
    name: value for name, value in vars(issue348.SweepTool).items()
    if not name.startswith("test_") and not name.startswith("__")})

# The platform shell tool model: a recorded cwd, one shell per call, and the
# cwd advancing only when the call itself succeeds.
TOOL_SHELL = """
import json, os, subprocess, sys
cwd = sys.argv[1]
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    request = json.loads(line)
    answer = {"cwd": cwd}
    try:
        run = subprocess.run([sys.argv[2], "-c", request["cmd"]], cwd=cwd,
                             capture_output=True, text=True)
        answer.update(rc=run.returncode, stdout=run.stdout.strip(),
                      stderr=run.stderr.strip())
        if request.get("cd"):
            cwd = request["cd"]
    except OSError as exc:
        answer.update(errno=exc.errno, error=type(exc).__name__)
    print(json.dumps(answer), flush=True)
"""

NODE_SHELL = """
const { spawnSync } = require("child_process");
const readline = require("readline");
let cwd = process.argv[1];
readline.createInterface({ input: process.stdin }).on("line", (line) => {
  if (!line.trim()) return;
  const request = JSON.parse(line);
  const answer = { cwd };
  const run = spawnSync(process.argv[2], ["-c", request.cmd], { cwd, encoding: "utf8" });
  if (run.error) {
    answer.error = run.error.code || String(run.error);
    answer.message = run.error.message;
  } else {
    answer.rc = run.status;
    answer.stdout = (run.stdout || "").trim();
    if (request.cd) cwd = request.cd;
  }
  console.log(JSON.stringify(answer));
});
"""


class ToolShell:
    """One shell tool whose cwd persists between calls."""

    def __init__(self, recorded: Path, node: bool = False):
        self.recorded = str(recorded)
        argv = ([sys.executable, "-c", TOOL_SHELL, self.recorded, SHELL_BIN]
                if not node else
                ["node", "-e", NODE_SHELL, self.recorded, SHELL_BIN])
        # The tool process itself starts at a neutral cwd: the recorded cwd is
        # what each call spawns in, exactly as the platform tool behaves.
        self.proc = subprocess.Popen(argv, cwd=str(REPO), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True)

    def call(self, command: str, cd: Path | None = None) -> dict:
        self.proc.stdin.write(json.dumps({"cmd": command,
                                          "cd": str(cd) if cd else None}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise AssertionError("the tool shell answered nothing")
        return json.loads(line)

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        self.proc.wait(timeout=30)
        if self.proc.stdout is not None:
            self.proc.stdout.close()


class RemovedCwd(unittest.TestCase):
    def setUp(self) -> None:
        if SHELL_BIN is None:
            self.skipTest("no shell binary on this host")
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i369-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.worktree = self.repo / ".kw" / "worktrees" / "issue-364"

    def git(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.repo), *argv],
                              capture_output=True, text=True)

    def make_worktree(self) -> None:
        self.repo.mkdir(parents=True)
        self.git("init")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-m", "base")
        added = self.git("worktree", "add", str(self.worktree), "-b", "workflow/issue-364")
        self.assertEqual(added.returncode, 0, added.stderr)

    def test_a_removed_cwd_breaks_the_shell_and_the_route_recovers_it(self) -> None:
        self.make_worktree()
        shell = ToolShell(self.worktree)
        self.addCleanup(shell.close)
        first = shell.call("pwd && echo shell-ok")
        self.assertEqual(first.get("rc"), 0, first)
        self.assertIn("shell-ok", first.get("stdout", ""))

        removed = self.git("worktree", "remove", str(self.worktree))
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertFalse(self.worktree.exists())
        # The shell binary is present: ENOENT names the vanished cwd, not it.
        self.assertTrue(os.path.exists(SHELL_BIN), SHELL_BIN)

        for _ in range(2):
            failed = shell.call("echo shell-ok")
            self.assertEqual(failed.get("errno"), 2, failed)
            self.assertNotIn("rc", failed)
            self.assertEqual(failed.get("cwd"), str(self.worktree))

        if shutil.which("node"):
            gone = Path(self.tmp.name) / "gone"
            gone.mkdir()
            node_shell = ToolShell(gone, node=True)
            self.addCleanup(node_shell.close)
            self.assertEqual(node_shell.call("echo shell-ok").get("rc"), 0)
            gone.rmdir()
            message = node_shell.call("echo shell-ok").get("message", "")
            self.assertIn("ENOENT", message, message)

        # The documented recovery, run from outside the stuck shell.
        self.assertEqual(subprocess.run(["mkdir", "-p", str(self.worktree)]).returncode, 0)
        self.assertTrue(self.worktree.exists())
        moved = shell.call(f"cd {self.repo}", cd=self.repo)
        self.assertEqual(moved.get("rc"), 0, moved)
        here = shell.call("pwd")
        self.assertEqual(Path(here.get("stdout", "")).resolve(), self.repo.resolve())
        cleaned = shell.call(f"rmdir {self.worktree} && echo shell-ok")
        self.assertEqual(cleaned.get("rc"), 0, cleaned)
        self.assertIn("shell-ok", cleaned.get("stdout", ""))
        self.assertFalse(self.worktree.exists())

    def test_the_route_names_the_symptom_and_the_recovery(self) -> None:
        kind, text = routes.ROUTES["cwd-vanished"]
        self.assertEqual(kind, "route")
        for needle in ("ENOENT", "shell binary exists", "mkdir -p", "cd <repo-root>",
                       "rmdir", "restarting the Host"):
            self.assertIn(needle, text, needle)
        self.assertEqual(routes.lookup("cwd-vanished")[0], "route")

    def test_an_unreadable_process_table_keeps_the_worktree(self) -> None:
        """No process table means an unverified cwd state, never a removal."""
        saved = dispatch._sweep_ps
        dispatch._sweep_ps = lambda: {}
        try:
            self.assertIsNone(dispatch._sweep_watch_pids([], self.repo))
        finally:
            dispatch._sweep_ps = saved
        self.assertEqual(dispatch._sweep_cwd_keep(self.repo, None),
                         ("cwd-unverified", {"cwd_probe": "ps"}))
        self.assertIn("cwd-unverified", routes.ROUTES)

    def test_the_host_guidance_carries_the_rule_and_the_route(self) -> None:
        for path in (REPO / "templates" / "orchestrator" / "references" / "workflow-worktree.md",
                     REPO / "skills" / "kaola-project-runner" / "references" / "workflow-worktree.md"):
            text = path.read_text(encoding="utf-8")
            for needle in ("Acceptance and every re-run", "spawn <shell> ENOENT",
                           "cwd-vanished", "live-cwd"):
                self.assertIn(needle, text, f"{needle} in {path}")
        brick = (REPO / "templates" / "kaola-delegator" / "references" / "host-brick.md"
                 ).read_text(encoding="utf-8")
        self.assertIn("cwd-vanished", brick)
        self.assertIn("no replacement", brick)


class SweepLiveCwd(SweepHarness, unittest.TestCase):
    """The real sweep against a linked worktree a live process sits in."""

    def test_apply_defers_removal_under_a_live_cwd(self) -> None:
        if SHELL_BIN is None:
            self.skipTest("no shell binary on this host")
        self.init_state()
        worktree = self.add_worktree(21)
        self.issues["21"] = "CLOSED"
        self.prs["21"] = self.worktree_head(worktree)
        self.write_gh()
        live = subprocess.Popen([SHELL_BIN, "-c", "while :; do sleep 5; done"],
                                cwd=str(worktree))
        try:
            self.set_rows([{"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                            "repo": str(self.repo), "identity": "verified",
                            "name_role": "host", "session_role": "host",
                            "holder_instance_id": "host-1", "state": "ready",
                            "holder_pid": live.pid}])
            code, out = self.sweep("--apply")
            self.assertEqual(code, 0, out)
            self.assertEqual(out["result"], "nothing", out)
            self.assertEqual(out["removed"], [], out)
            kept = [item for item in out["kept"] if item.get("kept") == "live-cwd"]
            self.assertEqual(len(kept), 1, out["kept"])
            item = kept[0]
            self.assertEqual(Path(item["path"]).resolve(), worktree.resolve())
            holders = item["cwd_holders"]
            self.assertIn(live.pid, [holder["pid"] for holder in holders])
            self.assertTrue(any(str(worktree) in holder["cwd"] for holder in holders), holders)
            self.assertTrue(worktree.exists())
            self.assertIn("live-cwd", routes.ROUTES)

            alert = self.doc()["state"]["alerts"]["sweep-kept"]
            self.assertIn("live process cwd", alert["inputs"][item["id"]]["next"])
            self.assertIn("project root", alert["inputs"][item["id"]]["next"])

            # The delete-time re-check defers on its own, not only the plan.
            outcome, why = dispatch._sweep_apply_candidate(
                {"id": item["id"], "kind": "worktree", "path": str(worktree.resolve()),
                 "issue": 21},
                argparse.Namespace(live=str(self.acp_rows)), self.repo.resolve(), None,
                {}, set())
            self.assertEqual((outcome, why), ("kept", "live-cwd"))
            self.assertTrue(worktree.exists())
        finally:
            live.terminate()
            live.wait(timeout=30)

        # The deferral was that cwd: with it gone the worktree is planned again.
        code, out = self.sweep("--dry-run")
        self.assertEqual(code, 0, out)
        planned = [ident for ident in (item["id"] for item in out["candidates"])
                   if ident.startswith("worktree:") and "issue-21" in ident]
        self.assertEqual(len(planned), 1, out["candidates"])

    def test_the_guard_does_not_keep_an_idle_worktree(self) -> None:
        """No live cwd: the ordinary removal path is unchanged."""
        self.init_state()
        worktree = self.add_worktree(22)
        self.issues["22"] = "CLOSED"
        self.prs["22"] = self.worktree_head(worktree)
        self.write_gh()
        self.set_rows([])
        code, out = self.sweep("--apply")
        self.assertEqual((code, out["result"]), (0, "swept"), out)
        self.assertFalse(worktree.exists())
        self.assertTrue(any(ident.startswith("worktree:") and "issue-22" in ident
                            for ident in out["removed"]), out)


if __name__ == "__main__":
    unittest.main()
