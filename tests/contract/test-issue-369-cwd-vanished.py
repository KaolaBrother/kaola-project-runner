#!/usr/bin/env python3
"""Issue #369: a removed tool-shell cwd, and the documented recovery.

A shell tool that keeps its working directory between calls loses it to
``git worktree remove``. Every later call fails with ENOENT while the shell
binary exists, and the ``tool-cwd-vanished`` route recovers the shell in place
with no Host restart. The sweep-side guard and the holder-side repair have
their own suites (``test-issue-369-worktree-guard.py`` and
``test-issue-369-holder-cwd-repair.py``); this one pins the failure itself, the
route text, and the Host guidance that ships.
"""

from __future__ import annotations

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
ROUTES_PATH = REPO / "scripts" / "kaola-recovery-routes.py"
SHELL_BIN = next((path for path in ("/bin/zsh", "/bin/bash", "/bin/sh")
                  if os.path.exists(path)), None)

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


routes = load_module("kaola_recovery_routes_i369", ROUTES_PATH)


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
        kind, text = routes.ROUTES["tool-cwd-vanished"]
        self.assertEqual(kind, "route")
        for needle in ("removed", "mkdir -p", "cd REPO", "rmdir PATH",
                       "Do not stop or restart the session"):
            self.assertIn(needle, text, needle)
        self.assertEqual(routes.lookup("tool-cwd-vanished")[0], "route")

    def test_the_holder_codes_have_their_designed_kinds(self) -> None:
        for code, kind in (("tool-cwd-vanished", "route"),
                           ("tool-cwd-unknown", "self-route"),
                           ("cwd-occupied", "route"),
                           ("cwd-unverifiable", "self-route"),
                           ("cwd-repair-failed", "route"),
                           ("cwd-placeholder-not-empty", "self-route")):
            self.assertIn(code, routes.ROUTES)
            self.assertEqual(routes.ROUTES[code][0], kind, code)

    def test_the_host_guidance_carries_the_rule_and_the_route(self) -> None:
        for path in (REPO / "templates" / "orchestrator" / "references" / "workflow-worktree.md",
                     REPO / "skills" / "kaola-project-runner" / "references" / "workflow-worktree.md"):
            text = path.read_text(encoding="utf-8")
            for needle in ("Acceptance and every re-run", "spawn <shell> ENOENT",
                           "tool-cwd-vanished", "cwd-occupied"):
                self.assertIn(needle, text, f"{needle} in {path}")
        brick = (REPO / "templates" / "kaola-delegator" / "references" / "host-brick.md"
                 ).read_text(encoding="utf-8")
        self.assertIn("tool-cwd-vanished", brick)
        self.assertIn("no replacement", brick)


if __name__ == "__main__":
    unittest.main()
