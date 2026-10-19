#!/usr/bin/env python3
"""Issue #348: the node-mode backstop sweep and its state tool.

Tool level runs `kaola-dispatch.py sweep` against a bare origin + clone with
real linked worktrees, a fake ``gh`` on PATH driven by a JSON file, and a fake
skills root whose ``kaola-acp.py`` answers list/status/stop from a JSON rows
file and records argv. Carrier level reuses the Issue #255/#324/#336 harness:
a stubbed Host holder with a node binding and a fake node runner. No real ACP
session, holder, or forge is ever touched.

1. A closed issue's leftovers the main flow missed - a verified idle worker
   session, merged linked worktrees (one holding only ignored build output,
   one whose session is already dead), prunable worktree metadata and a stale
   `.kaola/*.tmp` - are removed by one `--apply`; the fresh `.tmp` survives.
2. `--dry-run` writes nothing at all.
3. A second `--apply` is a no-op.
4. Kept items (dirty or unpushed worktree, turn-active session, a live
   session's worktree, an outside-project worktree) are reported in
   `alerts.sweep-kept`, never removed; an open issue is silently skipped; a
   repeat changes nothing.
5. `--apply --batch` re-verifies every planned candidate at delete time and
   refuses a forged batch.
6-10. The carrier: not-due spends nothing; due-empty records without a node;
   due-with-candidates sends exactly one sweep batch and settles it quiet;
   reconcile wins over a queued sweep; a HEAD move is due exactly once.

Issue #357 adds B1 (a merged local `workflow/issue-N` branch of a closed
issue, deleted only when no surviving worktree or live session holds it) and
the report-only rules R1-R3 (closed-issue Kaola-Workflow folders, foreign
`.kaola/` entries, heartbeat backups), which land in the receipt's `report`
and never in candidates, kept, state, alerts or maintenance.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
ISSUE255 = REPO / "tests" / "contract" / "test-issue-255-lifecycle-state.py"

spec = importlib.util.spec_from_file_location("issue255_node_348", ISSUE255)
issue255 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue255)
holder_module = issue255.holder_module

CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_RECORD_ROOT", "FAKE_GH_FILE",
              "FAKE_GH_CALLS", "FAKE_GH_PID", "FAKE_ACP_ROWS", "FAKE_ACP_CALLS",
              "KAOLA_SWEEP_INTERVAL_HOURS", "KAOLA_SWEEP_FORGE_TIMEOUT",
              "KAOLA_DISPATCH_RUNNER_TIMEOUT")
for name in CALLER_ENV:
    os.environ.pop(name, None)

FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, re, sys, time
    data = json.loads(open(os.environ["FAKE_GH_FILE"]).read())
    pid_file = os.environ.get("FAKE_GH_PID")
    if pid_file:
        open(pid_file, "w").write(str(os.getpid()))
    if data.get("sleep"):
        time.sleep(float(data["sleep"]))
    calls = os.environ.get("FAKE_GH_CALLS")
    argv = sys.argv[1:]
    if calls:
        with open(calls, "a") as stream:
            stream.write(json.dumps(argv) + "\\n")
    if argv[:2] == ["issue", "view"]:
        print(json.dumps({"state": data["issues"].get(argv[2], "OPEN")}))
    elif argv[:2] == ["pr", "list"]:
        head = argv[argv.index("--head") + 1]
        number = head.rsplit("-", 1)[1]
        oid = data.get("prs", {}).get(number)
        print(json.dumps([{"number": int(number), "headRefOid": oid}] if oid else []))
    elif argv[:2] == ["api", "graphql"]:
        if data.get("graphql") == "fail":
            sys.exit(1)
        query = next((a[len("query="):] for a in argv if a.startswith("query=")), "")
        repo = {}
        for key, number in re.findall(r"i(\\d+): issue\\(number: (\\d+)\\)", query):
            repo[f"i{key}"] = {"state": data["issues"].get(number, "OPEN")}
        for key in re.findall(r"p(\\d+): pullRequests", query):
            oid = data.get("prs", {}).get(key)
            repo[f"p{key}"] = {"nodes": ([{"number": int(key), "headRefOid": oid}]
                                          if oid else [])}
        print(json.dumps({"data": {"repository": repo}}))
    else:
        sys.exit(2)
    """)

FAKE_ACP = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys, time
    calls = os.environ.get("FAKE_ACP_CALLS")
    if calls:
        with open(calls, "a") as stream:
            stream.write(json.dumps(sys.argv[1:]) + "\\n")
    data = json.loads(open(os.environ["FAKE_ACP_ROWS"]).read())
    argv = sys.argv[1:]
    if argv[0] == "list" and data.get("list_sleep"):
        time.sleep(float(data["list_sleep"]))
    if argv[0] == "list":
        repo = None
        if "--repo" in argv:
            repo = os.path.realpath(argv[argv.index("--repo") + 1])
        rows = [r for r in data["rows"]
                if repo is None or os.path.realpath(r.get("repo") or "/none") == repo]
        print(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}))
    elif len(argv) > 1 and argv[1] == "status":
        session = argv[argv.index("--session") + 1]
        print(json.dumps(data.get("status", {}).get(session, {})))
    elif len(argv) > 1 and argv[1] == "stop":
        session = argv[argv.index("--session") + 1]
        holder = argv[argv.index("--expected-holder-instance-id") + 1]
        for row in data["rows"]:
            if row.get("session") == session and row.get("holder_instance_id") == holder:
                row["identity"] = "dead"
        open(os.environ["FAKE_ACP_ROWS"], "w").write(json.dumps(data))
        print(json.dumps({"stopped": True}))
    else:
        print(json.dumps({"error": {"code": "fake-unknown"}}))
        sys.exit(2)
    """)


def git(repo: Path, *argv: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True)
    assert proc.returncode == 0, (argv, proc.stderr)
    return proc.stdout


class SweepTool(unittest.TestCase):
    """The tool against temp repos, fake gh and a fake skills root."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i348-")
        root = Path(self.tmp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        (self.bin / "gh").write_text(FAKE_GH, encoding="utf-8")
        (self.bin / "gh").chmod(0o755)
        self.gh_data = root / "gh.json"
        self.gh_data.write_text(json.dumps({"issues": {}, "prs": {}}), encoding="utf-8")

        self.origin = root / "origin.git"
        subprocess.run(["git", "init", "--bare", str(self.origin)], check=True,
                       capture_output=True)
        self.repo = root / "repo"
        subprocess.run(["git", "clone", str(self.origin), str(self.repo)], check=True,
                       capture_output=True)
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "t")
        (self.repo / ".gitignore").write_text("build/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("x\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "init")
        git(self.repo, "push", "-u", "origin", "main")
        git(self.repo, "update-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        (self.repo / ".kaola").mkdir()
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"

        self.records = root / "records"
        self.host_dir = self._record_dir("zcode", "zcode-KT-orchestrator-main")
        self._write_record(self.host_dir, {"holder_instance_id": "host-1",
                                           "session_role": "host",
                                           "accepted_revision": "abc123",
                                           "holder_pid": os.getpid(),
                                           "repo": str(self.repo)})
        self.skills = root / "skills"
        acp = self.skills / "fake-kaola-project-runner" / "scripts" / "kaola-acp.py"
        acp.parent.mkdir(parents=True)
        acp.write_text(FAKE_ACP, encoding="utf-8")
        self.acp_rows = root / "rows.json"
        self.acp_calls = root / "calls.jsonl"
        self.gh_calls_file = root / "gh-calls.jsonl"
        self.set_rows([])
        self.issues: dict[str, str] = {}
        self.prs: dict[str, str] = {}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _record_dir(self, platform: str, session: str, repo: Path | None = None) -> Path:
        repo = repo or self.repo
        digest = hashlib.sha256(str(repo).encode()).hexdigest()[:16]
        directory = self.records / platform / session / digest
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def _write_record(directory: Path, record: dict) -> None:
        (directory / "record.json").write_text(json.dumps(record), encoding="utf-8")

    def set_rows(self, rows: list[dict], status: dict | None = None) -> None:
        self.acp_rows.write_text(json.dumps({"rows": rows, "status": status or {}}),
                                 encoding="utf-8")

    def write_gh(self) -> None:
        self.gh_data.write_text(json.dumps({"issues": self.issues, "prs": self.prs}),
                                encoding="utf-8")

    def env(self, holder: str = "host-1", session: str = "zcode-KT-orchestrator-main",
            platform: str = "zcode") -> dict[str, str]:
        env = {k: v for k, v in os.environ.items()
               if k not in CALLER_ENV and k != "KAOLA_ACP_HEARTBEAT_HOST"}
        env["PATH"] = f"{self.bin}:{env.get('PATH', '')}"
        env["FAKE_GH_FILE"] = str(self.gh_data)
        env["FAKE_ACP_ROWS"] = str(self.acp_rows)
        env["FAKE_ACP_CALLS"] = str(self.acp_calls)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": holder,
                                                  "platform": platform, "repo": str(self.repo),
                                                  "session": session})
        return env

    def sweep(self, *argv: str, env: dict | None = None) -> tuple[int, dict]:
        proc = subprocess.run([sys.executable, str(SCRIPT), "sweep", "--repo", str(self.repo),
                               "--skills-root", str(self.skills), *argv],
                              capture_output=True, text=True, env=env or self.env())
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError as exc:
            raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc

    def init_state(self) -> None:
        code, out = issue255.run(["state", "init", "--file", str(self.file), "--writer", "host",
                                  "--source", "turn-1",
                                  "--project", json.dumps({"code": "KT", "goal": "ship"}),
                                  "--authorization", json.dumps(issue255.AUTH)],
                                 env=self.env())
        self.assertEqual(code, 0, out)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def add_worktree(self, issue: int, branch: bool = True,
                     inside: bool = True, commit: bool = False) -> Path:
        path = (self.repo / ".kw" / "worktrees" / f"issue-{issue}") if inside \
            else Path(self.tmp.name) / "outside" / f"issue-{issue}"
        argv = ["worktree", "add", str(path)]
        if branch:
            argv += ["-b", f"workflow/issue-{issue}"]
        git(self.repo, *argv)
        if commit:
            (path / "newfile.txt").write_text("work\n", encoding="utf-8")
            git(path, "add", "newfile.txt")
            git(path, "commit", "-m", "wip")
        return path

    def worktree_head(self, path: Path) -> str:
        return git(path, "rev-parse", "HEAD").strip()

    def make_branch(self, issue: int, kind: str) -> str:
        """A local ``workflow/issue-N`` branch not held by any worktree.
        ``merge-commit`` lands its tip on pushed main (an ancestor);
        ``squash`` makes it the merged-PR head; ``unmerged`` neither."""
        sha = git(self.repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD",
                  "-m", f"wip-{issue}").strip()
        git(self.repo, "branch", f"workflow/issue-{issue}", sha)
        if kind == "merge-commit":
            git(self.repo, "merge", "--no-ff", "-m", f"merge-{issue}",
                f"workflow/issue-{issue}")
            git(self.repo, "push", "origin", "main")
            # setUp stores origin/HEAD as a plain sha; restore the symref
            # target so _sweep_remote_head still resolves it after a push.
            git(self.repo, "update-ref", "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main")
        elif kind == "squash":
            self.prs[str(issue)] = sha
        return sha

    def session_row(self, session: str, issue_holder: str, **kw) -> dict:
        return {"platform": "opencode", "session": session, "repo": str(self.repo),
                "identity": "verified", "name_role": "worker", "session_role": "worker",
                "holder_instance_id": issue_holder, "state": "ready",
                "accepted_revision": "abc123", "stale": False, "stale_reasons": [],
                "reported_drift": [], **kw}

    def test_apply_removes_exactly_the_closed_issue_residues(self) -> None:
        self.init_state()
        wt11 = self.add_worktree(11)
        (wt11 / "build").mkdir()
        (wt11 / "build" / "out.o").write_text("obj\n", encoding="utf-8")
        wt12 = self.add_worktree(12)
        wt13 = self.add_worktree(13)
        for number, path in ((11, wt11), (12, wt12), (13, wt13)):
            self.issues[str(number)] = "CLOSED"
            self.prs[str(number)] = self.worktree_head(path)
        self.issues["17"] = "OPEN"
        wt17 = self.add_worktree(17)  # open issue: never a candidate
        self.write_gh()
        subprocess.run(["rm", "-rf", str(wt13)], check=True)  # prunable metadata
        self.set_rows([self.session_row("opencode-KT-i11-x", "h-i11", stale=True,
                                        stale_reasons=["accepted-revision"]),
                       self.session_row("opencode-KT-i12-a", "h-i12", identity="dead"),
                       self.session_row("opencode-KT-i17-a", "h-i17")],
                      status={"opencode-KT-i11-x": {"turn_active": False,
                                                    "pending_permissions": [],
                                                    "holder_instance_id": "h-i11"}})
        old = self.repo / ".kaola" / "old.tmp"
        old.write_text("leftover\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(old, (two_days, two_days))
        fresh = self.repo / ".kaola" / "fresh.tmp"
        fresh.write_text("in-flight\n", encoding="utf-8")
        revision_before = self.doc().get("host_revision")

        code, out = self.sweep("--apply")
        self.assertEqual((code, out["result"]), (0, "swept"), out)
        removed = out["removed"]
        self.assertIn(f"session:opencode/opencode-KT-i11-x@h-i11", removed)
        self.assertTrue(any(r.startswith("worktree:") and f"issue-11" in r for r in removed))
        self.assertTrue(any(r.startswith("worktree:") and f"issue-12" in r for r in removed))
        self.assertTrue(any(r.startswith("worktree-prune:") and "issue-13" in r for r in removed))
        self.assertTrue(any(r.startswith("stale-file:") and "old.tmp" in r for r in removed))
        self.assertFalse(wt11.exists() or wt12.exists() or wt13.exists())
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())
        self.assertTrue(wt17.exists())
        stops = [json.loads(line) for line in self.acp_calls.read_text().splitlines()
                 if json.loads(line)[1:2] == ["stop"]]
        self.assertEqual(len(stops), 1)
        self.assertIn("h-i11", stops[0][stops[0].index("--expected-holder-instance-id") + 1])
        self.assertNotIn("--force", stops[0])
        last = self.doc()["state"]["maintenance"]["last_sweep"]
        self.assertEqual(last["removed"], removed)
        self.assertEqual(last["holder"], "host-1")
        self.assertIsNone(last["batch"])
        self.assertNotIn("sweep-kept", self.doc()["state"].get("alerts") or {})
        self.assertEqual(self.doc()["host_revision"], revision_before,
                         "tool writes never bump host_revision")
        # The stopped row is gone from live identity; issue-17 rows untouched.
        rows = {row["session"]: row for row in json.loads(self.acp_rows.read_text())["rows"]}
        self.assertEqual(rows["opencode-KT-i11-x"]["identity"], "dead")
        self.assertEqual(rows["opencode-KT-i17-a"]["identity"], "verified")

    def test_dry_run_changes_nothing(self) -> None:
        self.init_state()
        wt11 = self.add_worktree(11)
        self.issues["11"] = "CLOSED"
        self.prs["11"] = self.worktree_head(wt11)
        self.write_gh()
        self.set_rows([self.session_row("opencode-KT-i11-x", "h-i11")],
                      status={"opencode-KT-i11-x": {"turn_active": False,
                                                    "pending_permissions": [],
                                                    "holder_instance_id": "h-i11"}})
        old = self.repo / ".kaola" / "old.tmp"
        old.write_text("x\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(old, (two_days, two_days))

        def snapshot() -> dict:
            tree = {}
            for path in sorted(self.repo.rglob("*")):
                if ".git" in path.parts or path.is_dir():
                    continue
                tree[str(path)] = path.stat().st_mtime_ns
            return {"tree": tree, "state": self.file.read_bytes(),
                    "porcelain": git(self.repo, "worktree", "list", "--porcelain")}

        before = snapshot()
        code, out = self.sweep("--dry-run")
        after = snapshot()
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "planned")
        self.assertEqual(before, after, "dry-run writes nothing: no state write, "
                                       "remove or prune")
        calls = self.acp_calls.read_text() if self.acp_calls.exists() else ""
        self.assertNotIn('"stop"', calls, "dry-run never stops a session")
        kinds = {item["kind"] for item in out["candidates"]}
        self.assertEqual(kinds, {"session", "worktree", "branch", "stale-file"})

    def test_second_apply_is_a_no_op(self) -> None:
        self.init_state()
        wt11 = self.add_worktree(11)
        self.issues["11"] = "CLOSED"
        self.prs["11"] = self.worktree_head(wt11)
        self.write_gh()
        old = self.repo / ".kaola" / "old.tmp"
        old.write_text("x\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(old, (two_days, two_days))
        code, out = self.sweep("--apply")
        self.assertEqual(out["result"], "swept", out)
        code, out = self.sweep("--apply")
        self.assertEqual((code, out["result"]), (0, "nothing"), out)
        self.assertEqual(out["removed"], [])
        code, out = self.sweep("--dry-run")
        self.assertEqual(out["candidates"], [])

    def test_kept_items_are_reported_never_removed(self) -> None:
        self.init_state()
        dirty = self.add_worktree(14)
        (dirty / "scratch.txt").write_text("dirty\n", encoding="utf-8")
        unpushed = self.add_worktree(15, commit=True)
        outside = self.add_worktree(16, inside=False)
        live_wt = self.add_worktree(17)
        for number, path in ((14, dirty), (15, unpushed), (16, outside), (17, live_wt)):
            self.issues[str(number)] = "CLOSED"
            if number != 15:  # 15's head is no merged PR head: it stays unmerged
                self.prs[str(number)] = self.worktree_head(path)
        self.issues["18"] = "OPEN"
        open_wt = self.add_worktree(18)
        self.write_gh()
        self.set_rows([self.session_row("opencode-KT-i17-a", "h-i17"),
                       self.session_row("opencode-KT-i18-a", "h-i18")],
                      status={"opencode-KT-i17-a": {"turn_active": True,
                                                    "pending_permissions": [],
                                                    "holder_instance_id": "h-i17"},
                              "opencode-KT-i18-a": {"turn_active": False,
                                                    "pending_permissions": [],
                                                    "holder_instance_id": "h-i18"}})
        code, out = self.sweep("--apply")
        self.assertEqual((code, out["result"]), (0, "nothing"), out)
        self.assertEqual(out["removed"], [])
        kept = {item["id"]: item["kept"] for item in out["kept"]}
        self.assertIn(f"session:opencode/opencode-KT-i17-a@h-i17", kept)
        self.assertEqual(kept["session:opencode/opencode-KT-i17-a@h-i17"], "turn-active")
        why = {item["kept"] for item in out["kept"]}
        self.assertEqual(why, {"turn-active", "uncommitted-changes", "unmerged-or-unpushed",
                               "outside-project", "live-session"})
        for path in (dirty, unpushed, outside, live_wt, open_wt):
            self.assertTrue(path.exists())
        alert = (self.doc()["state"].get("alerts") or {}).get("sweep-kept")
        self.assertIsNotNone(alert)
        self.assertEqual((alert["owner"], alert["level"], alert["writer"]),
                         ("host", "warn", "tool:sweep"))
        self.assertEqual(set(alert["inputs"]), set(kept))
        self.assertTrue(all({"why", "evidence", "next"} == set(row)
                            for row in alert["inputs"].values()))
        # A repeat with the same kept set leaves the alert's bytes untouched;
        # only last_sweep moves (it is the due mark, written on every apply).
        alert_rev = alert["rev"]
        code, out = self.sweep("--apply")
        self.assertEqual(out["removed"], [])
        again = (self.doc()["state"].get("alerts") or {})["sweep-kept"]
        self.assertEqual((again["rev"], again["inputs"]), (alert_rev, alert["inputs"]))

    def test_node_batch_reverifies_and_a_forged_batch_is_refused(self) -> None:
        self.init_state()
        wt11 = self.add_worktree(11)
        self.issues["11"] = "CLOSED"
        self.prs["11"] = self.worktree_head(wt11)
        self.write_gh()
        # The bound node's record names this repo's Host carrier; the
        # carrier's events hold the sent sweep plan.
        node_dir = self._record_dir("zcode", "zcode-KT-sideagent")
        self._write_record(node_dir, {"holder_instance_id": "node-1",
                                      "session_role": "sideagent",
                                      "holder_pid": os.getpid(),
                                      "repo": str(self.repo),
                                      "dispatcher": {"holder_instance_id": "host-1",
                                                     "platform": "zcode",
                                                     "repo": str(self.repo),
                                                     "session": "zcode-KT-orchestrator-main"}})
        code, plan = self.sweep("--dry-run")
        ids = [item["id"] for item in plan["candidates"]]
        self.assertTrue(any(ident.startswith("worktree:") for ident in ids))
        batch = "s-" + hashlib.sha256(json.dumps(["node-1", plan["key"]])
                                      .encode()).hexdigest()[:12]
        log = self.host_dir / "events.jsonl"
        log.write_text(json.dumps({"kind": "sideagent_node_batch", "batch": batch,
                                   "target_holder": "node-1", "host_holder": "host-1",
                                   "host_revision_through": 0,
                                   "sweep": {"key": plan["key"], "candidates": ids,
                                             "reason": "interval"}}) + "\n",
                       encoding="utf-8")
        node_env = self.env(holder="node-1", session="zcode-KT-sideagent")
        code, out = self.sweep("--apply", "--batch", "s-forged", env=node_env)
        self.assertEqual((code, out["result"]), (2, "refused"), out)
        # The planned worktree went dirty after the plan was sent.
        (wt11 / "scratch.txt").write_text("dirty\n", encoding="utf-8")
        code, out = self.sweep("--apply", "--batch", batch, env=node_env)
        self.assertEqual(code, 0, out)
        self.assertTrue(wt11.exists(), "a candidate re-verified dirty is kept, not removed")
        self.assertTrue(any(item.get("kept") == "uncommitted-changes"
                            for item in out["kept"]), out)
        last = self.doc()["state"]["maintenance"]["last_sweep"]
        self.assertEqual((last["batch"], last["holder"]), (batch, "node-1"))
        self.assertEqual(last["accepted_revision"], "abc123")

    def test_stale_tmp_symlinks_are_never_candidates(self) -> None:
        self.init_state()
        outside = Path(self.tmp.name) / "outside-target"
        outside.write_text("keep me\n", encoding="utf-8")
        link = self.repo / ".kaola" / "link.tmp"
        link.symlink_to(outside)
        two_days = time.time() - 2 * 86400
        os.utime(link, (two_days, two_days), follow_symlinks=False)
        code, out = self.sweep("--apply")
        self.assertTrue(outside.exists())
        self.assertFalse(any(item["kind"] == "stale-file" for item in out["candidates"]),
                        "a symlink entry is never an F1 candidate")
        # `.kaola` itself a symlink: no F1 scan of it at all.
        real = self.repo / ".kaola-real"
        (self.repo / ".kaola").rename(real)
        (self.repo / ".kaola").symlink_to(real)
        stale = real / "old.tmp"
        stale.write_text("x\n", encoding="utf-8")
        os.utime(stale, (two_days, two_days))
        code, out = self.sweep("--dry-run")
        self.assertFalse(any(item["kind"] == "stale-file" for item in out["candidates"]))
        self.assertTrue(stale.exists())

    def test_record_empty_never_touches_attention_or_host_revision(self) -> None:
        self.init_state()
        before = self.doc()
        code, out = self.sweep("--record-empty")
        self.assertEqual((code, out["result"]), (0, "recorded-empty"), out)
        after = self.doc()
        self.assertEqual(before["host_revision"], after["host_revision"])
        fp = holder_module.attention_fingerprint
        self.assertEqual(fp(before["body"]), fp(after["body"]))
        self.assertIsNotNone(after["state"]["maintenance"]["last_sweep"]["at"])

    # -- Issue #353: batched forge, one list, timeouts, state gate -----------

    def closed_merged_worktrees(self, count: int, base: int = 100) -> list[Path]:
        paths = [self.add_worktree(base + i) for i in range(count)]
        for i, path in enumerate(paths):
            number = str(base + i)
            self.issues[number] = "CLOSED"
            self.prs[number] = self.worktree_head(path)
        self.write_gh()
        return paths

    def logged_env(self, **extra: str) -> dict:
        env = self.env()
        env["FAKE_GH_CALLS"] = str(self.gh_calls_file)
        env.update(extra)
        return env

    def gh_calls(self) -> list[list[str]]:
        if not self.gh_calls_file.exists():
            return []
        return [json.loads(line) for line in self.gh_calls_file.read_text().splitlines()]

    def acp_calls_of(self, command: str) -> list[list[str]]:
        if not self.acp_calls.exists():
            return []
        return [row for row in
                (json.loads(line) for line in self.acp_calls.read_text().splitlines())
                if row and row[0] == command]

    def test_dry_run_batches_forge_and_one_list(self) -> None:  # T1
        self.init_state()
        self.closed_merged_worktrees(50)
        code, out = self.sweep("--dry-run", env=self.logged_env())
        self.assertEqual(code, 0, out)
        gh = self.gh_calls()
        self.assertEqual(len(gh), 1, gh)
        self.assertEqual(gh[0][:2], ["api", "graphql"])
        self.assertEqual(len(self.acp_calls_of("list")), 1)
        worktrees = [item for item in out["candidates"] if item["kind"] == "worktree"]
        self.assertEqual(len(worktrees), 50)
        self.assertEqual(out["timed_out"], [])
        self.assertEqual(out["acp"], "known")

    def test_apply_reuses_the_scan_forge_facts(self) -> None:  # T2
        self.init_state()
        paths = self.closed_merged_worktrees(50)
        code, out = self.sweep("--apply", env=self.logged_env())
        self.assertEqual((code, out["result"]), (0, "swept"), out)
        self.assertEqual(len(self.gh_calls()), 1, self.gh_calls())
        self.assertLessEqual(len(self.acp_calls_of("list")), 1 + 50 + 1)
        self.assertEqual(len(out["removed"]), 100)
        self.assertFalse(any(path.exists() for path in paths))
        refs = git(self.repo, "for-each-ref", "--format=%(refname)",
                   "refs/heads/workflow/")
        self.assertEqual(refs.strip(), "", "the 50 merged branches are gone")

    def test_node_apply_verifies_only_planned_ids(self) -> None:  # T3
        self.init_state()
        paths = self.closed_merged_worktrees(50)
        kept = {"id": "session:opencode/opencode-KT-i99-a@h-99", "kind": "session",
                "issue": 99, "platform": "opencode", "session": "opencode-KT-i99-a",
                "holder_instance_id": "h-99", "kept": "unreachable"}
        ids = [f"worktree:{path.resolve()}@{self.worktree_head(path)}"
               for path in paths[:2]]
        node_dir = self._record_dir("zcode", "zcode-KT-sideagent")
        self._write_record(node_dir, {"holder_instance_id": "node-1",
                                      "session_role": "sideagent",
                                      "holder_pid": os.getpid(),
                                      "repo": str(self.repo),
                                      "dispatcher": {"holder_instance_id": "host-1",
                                                     "platform": "zcode",
                                                     "repo": str(self.repo),
                                                     "session": "zcode-KT-orchestrator-main"}})
        batch = "s-planned353"
        (self.host_dir / "events.jsonl").write_text(
            json.dumps({"kind": "sideagent_node_batch", "batch": batch,
                        "target_holder": "node-1", "host_holder": "host-1",
                        "host_revision_through": 0,
                        "sweep": {"key": "k353", "candidates": ids, "reason": "interval",
                                  "kept": [kept]}}) + "\n",
            encoding="utf-8")
        env = self.logged_env()
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": "node-1",
                                                  "platform": "zcode", "repo": str(self.repo),
                                                  "session": "zcode-KT-sideagent"})
        code, out = self.sweep("--apply", "--batch", batch, env=env)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.gh_calls()), 1, self.gh_calls())
        self.assertLessEqual(len(self.acp_calls_of("list")), 3)
        self.assertFalse(paths[0].exists() or paths[1].exists())
        self.assertTrue(all(path.exists() for path in paths[2:]),
                        "unplanned worktrees are never scanned")
        alert = (self.doc()["state"].get("alerts") or {}).get("sweep-kept") or {}
        self.assertIn(kept["id"], alert.get("inputs") or {})

    def test_graphql_failure_falls_back_to_serial(self) -> None:  # T4
        self.init_state()
        paths = self.closed_merged_worktrees(2)
        self.gh_data.write_text(json.dumps({"issues": self.issues, "prs": self.prs,
                                            "graphql": "fail"}), encoding="utf-8")
        code, out = self.sweep("--dry-run", env=self.logged_env())
        self.assertEqual(code, 0, out)
        worktrees = [item for item in out["candidates"] if item["kind"] == "worktree"]
        self.assertEqual(len(worktrees), 2, out)
        calls = self.gh_calls()
        self.assertEqual(calls[0][:2], ["api", "graphql"])
        self.assertTrue(all(argv[:1] in (["issue"], ["pr"]) for argv in calls[1:]), calls)
        for path in paths:
            self.assertTrue(path.exists())

    def test_forge_timeout_is_recorded_not_rescanned(self) -> None:  # T5
        self.init_state()
        path = self.add_worktree(100)
        self.gh_data.write_text(json.dumps({"issues": {"100": "CLOSED"},
                                            "prs": {"100": self.worktree_head(path)},
                                            "sleep": 30}), encoding="utf-8")
        started = time.monotonic()
        code, out = self.sweep("--dry-run",
                               env=self.logged_env(KAOLA_SWEEP_FORGE_TIMEOUT="1"))
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["timed_out"], ["gh"])
        self.assertEqual(out["forge"], "unavailable")
        self.assertEqual(out["candidates"], [])

    def test_unknown_list_never_removes_a_worktree(self) -> None:  # T6
        self.init_state()
        path = self.add_worktree(100)
        self.issues["100"] = "CLOSED"
        self.prs["100"] = self.worktree_head(path)
        self.write_gh()
        self.acp_rows.write_text(json.dumps({"rows": [], "status": {},
                                             "list_sleep": 30}), encoding="utf-8")
        code, out = self.sweep("--apply",
                               env=self.logged_env(KAOLA_DISPATCH_RUNNER_TIMEOUT="1"))
        self.assertEqual(code, 0, out)
        self.assertTrue(path.exists())
        self.assertIn("acp-unknown", out["skipped"].values())
        self.assertEqual(out["acp"], "unavailable")
        self.assertIn("acp", out["timed_out"])
        self.assertEqual(out["removed"], [])

    def test_missing_gh_is_forge_unavailable_not_timed_out(self) -> None:
        self.init_state()
        path = self.add_worktree(100)
        self.issues["100"] = "CLOSED"
        self.prs["100"] = self.worktree_head(path)
        self.write_gh()
        clean = Path(self.tmp.name) / "nogh-bin"
        clean.mkdir()
        for tool in ("git",):
            target = shutil.which(tool)
            self.assertIsNotNone(target)
            (clean / tool).symlink_to(target)
        env = self.logged_env()
        env["PATH"] = str(clean)
        code, out = self.sweep("--dry-run", env=env)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["forge"], "unavailable")
        self.assertEqual(out["timed_out"], [])
        self.assertIn("forge-unknown", out["skipped"].values())
        self.assertTrue(path.exists())

    def test_apply_requires_current_state(self) -> None:  # T7
        path = self.add_worktree(100)
        self.issues["100"] = "CLOSED"
        self.prs["100"] = self.worktree_head(path)
        self.write_gh()
        stale = self.repo / ".kaola" / "old.tmp"
        stale.write_text("leftover\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(stale, (two_days, two_days))

        code, out = self.sweep("--apply")  # no state file at all
        self.assertEqual((code, out["result"]), (2, "refused"), out)
        self.assertEqual(out["reason"], "state-missing")
        self.assertIn("state init", out["recovery"])
        self.assertTrue(path.exists() and stale.exists())

        self.file.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1",
                                         "state": {}}), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = self.sweep("--apply")
        self.assertEqual((code, out["result"]), (2, "refused"), out)
        self.assertEqual(out["reason"], "legacy-format")
        self.assertIn("state migrate", out["recovery"])
        self.assertTrue(path.exists() and stale.exists())
        self.assertEqual(self.file.read_bytes(), before)
        stops = []
        if self.acp_calls.exists():
            stops = [row for row in
                     (json.loads(line) for line in self.acp_calls.read_text().splitlines())
                     if row[1:2] == ["stop"]]
        self.assertEqual(stops, [])

    # -- Issue #357: B1 merged local branches, R1-R3 report-only ----------

    def branch_id(self, issue: int, sha: str) -> str:
        return f"branch:workflow/issue-{issue}@{sha}"

    def ref_exists(self, issue: int) -> bool:
        proc = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "--verify",
                               "--quiet", f"refs/heads/workflow/issue-{issue}"],
                              capture_output=True)
        return proc.returncode == 0

    def write_workflow_folder(self, issue: int, status: str = "active",
                              parent: Path | None = None) -> Path:
        folder = (parent or self.repo / "kaola-workflow" / f"issue-{issue}")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "workflow-state.md").write_text(
            f"issue_number: {issue}\nstatus: {status}\n", encoding="utf-8")
        return folder

    def test_b1_six_cases(self) -> None:
        sha21 = self.make_branch(21, "merge-commit")
        sha22 = self.make_branch(22, "squash")
        sha23 = self.make_branch(23, "unmerged")
        wt24 = self.add_worktree(24)  # merged, CLOSED, then made dirty
        sha24 = self.worktree_head(wt24)
        sha25 = self.make_branch(25, "squash")
        sha26 = self.make_branch(26, "merge-commit")  # OPEN: never listed
        for number in (21, 22, 23, 24, 25):
            self.issues[str(number)] = "CLOSED"
        self.issues["26"] = "OPEN"
        self.prs["23"] = "0" * 40  # a merged PR head that is not the tip
        self.prs["24"] = sha24
        self.write_gh()
        (wt24 / "scratch.txt").write_text("dirty\n", encoding="utf-8")
        self.init_state()

        code, out = self.sweep("--dry-run")
        self.assertEqual(code, 0, out)
        candidates = {item["id"]: item for item in out["candidates"]
                      if item["kind"] == "branch"}
        self.assertEqual(candidates[self.branch_id(21, sha21)]["merge"], "ancestor")
        self.assertEqual(candidates[self.branch_id(22, sha22)]["merge"], "merged-pr-head")
        self.assertEqual(candidates[self.branch_id(25, sha25)]["merge"], "merged-pr-head")
        kept = {item["id"]: item["kept"] for item in out["kept"]}
        self.assertEqual(kept[self.branch_id(23, sha23)], "unmerged-or-unpushed")
        self.assertEqual(out["skipped"][self.branch_id(24, sha24)], "checked-out")
        self.assertNotIn(self.branch_id(26, sha26),
                         {item["id"] for item in out["candidates"] + out["kept"]}
                         | set(out["skipped"]))
        refs_before = git(self.repo, "for-each-ref", "--format=%(refname)",
                          "refs/heads/workflow/")
        remote_before = git(self.repo, "ls-remote", "origin")
        state_before = self.file.read_bytes()
        code, again = self.sweep("--dry-run")
        self.assertEqual(again, out, "a second dry-run is byte-identical")
        self.assertEqual(git(self.repo, "for-each-ref", "--format=%(refname)",
                             "refs/heads/workflow/"), refs_before)
        self.assertEqual(git(self.repo, "ls-remote", "origin"), remote_before)
        self.assertEqual(self.file.read_bytes(), state_before)

        self.issues["25"] = "OPEN"  # reopened between plan and apply
        self.write_gh()
        trace = Path(self.tmp.name) / "git-trace.log"
        env = self.logged_env()
        env["GIT_TRACE"] = str(trace)
        code, out = self.sweep("--apply", env=env)
        self.assertEqual(code, 0, out)
        self.assertEqual(set(out["removed"]),
                         {self.branch_id(21, sha21), self.branch_id(22, sha22)})
        for issue in (23, 24, 25, 26):
            self.assertTrue(self.ref_exists(issue), f"issue-{issue} ref survives")
        self.assertFalse(self.ref_exists(21) or self.ref_exists(22))
        log = trace.read_text(encoding="utf-8")
        self.assertIn("branch -d workflow/issue-21", log)
        self.assertIn("branch -D workflow/issue-22", log)
        self.assertNotIn("push", log)
        self.assertEqual(git(self.repo, "ls-remote", "origin"), remote_before,
                         "remote branches are never touched")
        last = self.doc()["state"]["maintenance"]["last_sweep"]
        self.assertIn(self.branch_id(21, sha21), last["removed"])
        self.assertIn(self.branch_id(22, sha22), last["removed"])
        git(self.repo, "branch", "workflow/issue-22", sha22)
        self.assertEqual(git(self.repo, "rev-parse", "workflow/issue-22").strip(),
                         sha22, "the restore hint on the receipt works")
        git(self.repo, "branch", "-D", "workflow/issue-22")
        code, out = self.sweep("--apply")
        self.assertFalse(any(r.startswith("branch:") for r in out["removed"]), out)

    def test_b1_node_batch_skips_a_reopened_issue(self) -> None:
        self.init_state()
        sha25 = self.make_branch(25, "squash")
        sha27 = self.make_branch(27, "squash")
        self.issues["25"] = "CLOSED"
        self.issues["27"] = "CLOSED"
        self.write_gh()
        node_dir = self._record_dir("zcode", "zcode-KT-sideagent")
        self._write_record(node_dir, {"holder_instance_id": "node-1",
                                      "session_role": "sideagent",
                                      "holder_pid": os.getpid(),
                                      "repo": str(self.repo),
                                      "dispatcher": {"holder_instance_id": "host-1",
                                                     "platform": "zcode",
                                                     "repo": str(self.repo),
                                                     "session": "zcode-KT-orchestrator-main"}})
        code, plan = self.sweep("--dry-run")
        ids = [item["id"] for item in plan["candidates"]]
        self.assertIn(self.branch_id(25, sha25), ids)
        self.assertIn(self.branch_id(27, sha27), ids)
        batch = "s-" + hashlib.sha256(json.dumps(["node-1", plan["key"]])
                                      .encode()).hexdigest()[:12]
        (self.host_dir / "events.jsonl").write_text(
            json.dumps({"kind": "sideagent_node_batch", "batch": batch,
                        "target_holder": "node-1", "host_holder": "host-1",
                        "host_revision_through": 0,
                        "sweep": {"key": plan["key"], "candidates": ids,
                                  "reason": "interval"}}) + "\n",
            encoding="utf-8")
        self.issues["25"] = "OPEN"  # reopened between plan and apply
        self.write_gh()
        node_env = self.env(holder="node-1", session="zcode-KT-sideagent")
        code, out = self.sweep("--apply", "--batch", batch, env=node_env)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["skipped"][self.branch_id(25, sha25)],
                         "no-longer-candidate")
        self.assertTrue(self.ref_exists(25))
        self.assertFalse(self.ref_exists(27))
        self.assertIn(self.branch_id(27, sha27), out["removed"])

    def test_b1_forge_unreachable_skips_issue_linked_items(self) -> None:
        self.init_state()
        sha21 = self.make_branch(21, "merge-commit")
        sha22 = self.make_branch(22, "squash")
        self.issues["21"] = "CLOSED"
        self.issues["22"] = "CLOSED"
        self.write_gh()
        folder = self.write_workflow_folder(21)
        bak = self.repo / ".kaola" / "x.bak"
        bak.write_text("12345", encoding="utf-8")
        clean = Path(self.tmp.name) / "nogh-bin"
        clean.mkdir()
        for tool in ("git",):
            target = shutil.which(tool)
            self.assertIsNotNone(target)
            (clean / tool).symlink_to(target)
        env = self.logged_env()
        env["PATH"] = str(clean)
        expected_skipped = {self.branch_id(21, sha21), self.branch_id(22, sha22),
                            f"workflow-folder:{folder.resolve()}"}
        for mode in ("--dry-run", "--apply"):
            code, out = self.sweep(mode, env=env)
            self.assertEqual(code, 0, out)
            for ident in expected_skipped:
                self.assertEqual(out["skipped"].get(ident), "forge-unknown", mode)
            self.assertTrue(self.ref_exists(21) and self.ref_exists(22))
            report = {item["id"]: item for item in out["report"]}
            self.assertNotIn(f"workflow-folder:{folder.resolve()}", report)
            self.assertIn(f"kaola-foreign:{bak.resolve()}", report)

    def test_b1_live_session_keeps_branch(self) -> None:
        self.init_state()
        sha28 = self.make_branch(28, "merge-commit")
        self.issues["28"] = "CLOSED"
        self.write_gh()
        self.set_rows([self.session_row("opencode-KT-i28-a", "h-i28")],
                      status={"opencode-KT-i28-a": {"turn_active": True,
                                                    "pending_permissions": [],
                                                    "holder_instance_id": "h-i28"}})
        code, out = self.sweep("--apply")
        self.assertEqual(code, 0, out)
        kept = {item["id"]: item["kept"] for item in out["kept"]}
        self.assertEqual(kept[self.branch_id(28, sha28)], "live-session")
        self.assertTrue(self.ref_exists(28))
        self.assertNotIn(self.branch_id(28, sha28), out["removed"])

    def test_b1_worktree_and_its_branch_go_in_one_apply(self) -> None:
        self.init_state()
        wt11 = self.add_worktree(11)
        head = self.worktree_head(wt11)
        self.issues["11"] = "CLOSED"
        self.prs["11"] = head
        self.write_gh()
        code, out = self.sweep("--apply")
        self.assertEqual((code, out["result"]), (0, "swept"), out)
        self.assertTrue(any(r.startswith("worktree:") for r in out["removed"]))
        self.assertIn(self.branch_id(11, head), out["removed"])
        self.assertFalse(wt11.exists() or self.ref_exists(11))
        code, out = self.sweep("--apply")
        self.assertEqual(out["result"], "nothing")

    def test_report_only_items_never_reach_state(self) -> None:
        self.init_state()
        kwf = self.repo / "kaola-workflow"
        folder31 = self.write_workflow_folder(31)
        self.write_workflow_folder(32)
        self.write_workflow_folder(33, parent=kwf / "archive" / "issue-33")
        (kwf / "release").mkdir(parents=True)  # no workflow-state.md
        self.issues["31"] = "CLOSED"
        self.issues["32"] = "OPEN"
        self.issues["33"] = "CLOSED"
        self.write_gh()
        ka = self.repo / ".kaola"
        (ka / "x.bak").write_text("12345", encoding="utf-8")
        for name, sizes in (("host-evidence", (3, 4)), ("codex-handoff", (6,)),
                            ("delegator-evidence", (7,))):
            folder = ka / name
            folder.mkdir()
            for index, size in enumerate(sizes):
                (folder / chr(ord("a") + index)).write_text("x" * size,
                                                           encoding="utf-8")
        (ka / "target").mkdir()
        (ka / "target" / "t").write_text("x", encoding="utf-8")
        (ka / "build").mkdir()
        (ka / "build" / "b").write_text("x", encoding="utf-8")
        (ka / "dispatch-index.json").write_text("{}", encoding="utf-8")
        (ka / "delegator-heartbeat.json").write_text("{}", encoding="utf-8")
        (ka / "run").mkdir()
        (ka / "run" / "note.md").write_text("x", encoding="utf-8")
        (ka / "y.tmp").write_text("fresh", encoding="utf-8")
        (ka / "heartbeat-prompt.v1-aaaaaaaaaaaa.json").write_text(
            "x" * 10, encoding="utf-8")
        (ka / "heartbeat-prompt.v2-bbbbbbbbbbbb.json").write_text(
            "x" * 20, encoding="utf-8")

        code, out = self.sweep("--dry-run")
        self.assertEqual(code, 0, out)
        report = {item["id"]: item for item in out["report"]}
        r1 = report[f"workflow-folder:{folder31.resolve()}"]
        self.assertEqual((r1["rule"], r1["kind"], r1["issue"], r1["status"]),
                         ("R1", "workflow-folder", 31, "active"))
        self.assertNotIn(f"workflow-folder:{(kwf / 'issue-32').resolve()}", report)
        self.assertFalse(any("issue-33" in i or "release" in i for i in report))
        paths = {item["path"] for item in out["report"] if item["rule"] == "R2"}
        self.assertEqual(paths, {str((ka / name).resolve()) for name in
                                 ("x.bak", "host-evidence", "codex-handoff",
                                  "delegator-evidence")})
        sizes = {item["path"]: item["bytes"]
                 for item in out["report"] if item["rule"] == "R2"}
        self.assertEqual(sizes[str((ka / "x.bak").resolve())], 5)
        self.assertEqual(sizes[str((ka / "host-evidence").resolve())], 7)
        self.assertEqual(sizes[str((ka / "codex-handoff").resolve())], 6)
        self.assertEqual(sizes[str((ka / "delegator-evidence").resolve())], 7)
        r3 = report["heartbeat-backups"]
        self.assertEqual((r3["rule"], r3["count"], r3["bytes"]), ("R3", 2, 30))

        kwf_bytes = {str(p): p.read_bytes() for p in sorted(kwf.rglob("*"))
                     if p.is_file()}
        commits_before = git(self.repo, "rev-list", "--count", "HEAD")
        maintenance_before = set((self.doc()["state"].get("maintenance") or {}))
        code, out = self.sweep("--apply")
        self.assertEqual(code, 0, out)
        code, out = self.sweep("--record-empty")
        self.assertEqual((code, out["result"]), (0, "recorded-empty"), out)
        for path in [folder31, ka / "x.bak", ka / "host-evidence",
                     ka / "codex-handoff", ka / "delegator-evidence",
                     ka / "heartbeat-prompt.v1-aaaaaaaaaaaa.json",
                     ka / "heartbeat-prompt.v2-bbbbbbbbbbbb.json"]:
            self.assertTrue(path.exists(), path)
        self.assertEqual({str(p): p.read_bytes() for p in sorted(kwf.rglob("*"))
                          if p.is_file()}, kwf_bytes)
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD"),
                         commits_before)
        state = self.doc()["state"]
        self.assertNotIn("sweep-kept", state.get("alerts") or {})
        self.assertEqual(set((state.get("maintenance") or {})),
                         maintenance_before | {"last_sweep"})
        self.assertEqual(set(state["maintenance"]["last_sweep"]),
                         {"at", "key", "batch", "holder", "accepted_revision",
                          "head", "removed"})
        text = self.file.read_text(encoding="utf-8")
        for word in ("host-evidence", "issue-31", "heartbeat-backups",
                     "kaola-foreign", "workflow-folder", "report"):
            self.assertNotIn(word, text)
        keys_before = set(state)
        alerts_before = len(state.get("alerts") or {})
        code, out = self.sweep("--apply")
        state = self.doc()["state"]
        self.assertEqual(set(state), keys_before)
        self.assertEqual(len(state.get("alerts") or {}), alerts_before)


class SweepCarrier(issue255.HolderFixture):
    """The Host carrier's due mechanism. Same fixture shape as the 255
    ``HolderNodeMode`` (fake node runner, FakeNode socket, node-mode binding)
    but without replaying that suite's own tests."""

    def setUp(self) -> None:
        super().setUp()
        root = Path(self.tmp.name)
        self.runner = root / "runtime-tmux.sh"
        self.runner.write_text(issue255.FAKE_NODE_RUNNER, encoding="utf-8")
        self.runner.chmod(0o755)
        self.saved_env = {key: os.environ.get(key) for key in
                          ("FAKE_NODE_COUNTER", "FAKE_NODE_ARGV", "FAKE_NODE_RECORD",
                           "FAKE_NODE_REPO", "FAKE_NODE_PID", "FAKE_NODE_DELAY")}
        os.environ.update(FAKE_NODE_COUNTER=str(root / "count"),
                          FAKE_NODE_ARGV=str(root / "argv"),
                          FAKE_NODE_RECORD=str(self.side_dir / "record.json"),
                          FAKE_NODE_REPO=str(self.repo), FAKE_NODE_PID=str(os.getpid()))
        self.fake = issue255.FakeNode(self.side_sock, self.side_dir / "record.json")
        self.saved_confirm = holder_module.NODE_STOP_CONFIRM_SECONDS
        holder_module.NODE_STOP_CONFIRM_SECONDS = 1.5
        self.saved_interval = holder_module.SWEEP_INTERVAL_SECONDS
        holder_module.SWEEP_INTERVAL_SECONDS = 3600.0
        subprocess.run(["git", "init"], cwd=self.repo, capture_output=True, check=True)
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "f").write_text("x\n", encoding="utf-8")
        git(self.repo, "add", "f")
        git(self.repo, "commit", "-m", "init")
        self.holder.session_role = "host"
        self.holder.write_record()
        # A fake gh for issue-linked scans (the sweep tool inherits PATH).
        self.bin = root / "bin"
        self.bin.mkdir()
        (self.bin / "gh").write_text(FAKE_GH, encoding="utf-8")
        (self.bin / "gh").chmod(0o755)
        self.gh_data = root / "gh.json"
        self.saved_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.bin}:{self.saved_path}"
        self.saved_gh_file = os.environ.get("FAKE_GH_FILE")
        os.environ["FAKE_GH_FILE"] = str(self.gh_data)
        self.set_gh({})

    def tearDown(self) -> None:
        holder_module.NODE_STOP_CONFIRM_SECONDS = self.saved_confirm
        holder_module.SWEEP_INTERVAL_SECONDS = self.saved_interval
        os.environ["PATH"] = self.saved_path
        if self.saved_gh_file is None:
            os.environ.pop("FAKE_GH_FILE", None)
        else:
            os.environ["FAKE_GH_FILE"] = self.saved_gh_file
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        super().tearDown()

    def set_gh(self, issues: dict, prs: dict | None = None, **extra) -> None:
        self.gh_data.write_text(json.dumps({"issues": issues, "prs": prs or {},
                                            **extra}), encoding="utf-8")

    def kept_worker_record(self, session: str = "opencode-KT-i99-a",
                           holder: str = "h-99", issue: int = 99) -> str:
        """An unreachable closed-issue worker: a kept item, never a candidate."""
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.records / "opencode" / session / digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "record.json").write_text(json.dumps({
            "holder_instance_id": holder, "session_role": "worker",
            "repo": str(self.repo), "state": "ready", "holder_pid": os.getpid()}),
            encoding="utf-8")
        self.set_gh({str(issue): "CLOSED"})
        return f"session:opencode/{session}@{holder}"

    def write_node_state(self, maintenance: dict | None = None,
                         host_revision: int = 0) -> None:
        state: dict = {"sideagent": {"platform": "zcode", "session": "zcode-KT-sideagent",
                                     "state": "active", "mode": "node",
                                     "recipe": {"runner": str(self.runner),
                                                "argv": ["start", "--repo", str(self.repo),
                                                         "--session", "zcode-KT-sideagent",
                                                         "--role", "sideagent"]}},
                       "maintenance": maintenance or {}}
        if host_revision:
            # A Host business change the selector can see (host_changes).
            state["section_sources"] = {"project": {"writer": "host",
                                                    "host_revision": host_revision}}
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2", "host_revision": host_revision,
            "body": json.dumps({"view": "host", "attention": [], "tasks": []}),
            "state": state}), encoding="utf-8")

    def boundary(self) -> None:
        with self.holder.worker_events_lock:
            self.holder._relay_pass()

    def node_count(self) -> int:
        counter = Path(self.tmp.name) / "count"
        return int(counter.read_text()) if counter.exists() else 0

    def wait_for(self, check, what: str, timeout: float = 15.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.05)
        self.fail(f"timed out waiting for {what}")

    def head(self) -> str:
        return git(self.repo, "rev-parse", "HEAD").strip()

    def last_sweep(self, at: str | None = None, head: str | None = None,
                   accepted=None) -> dict:
        return {"at": at or datetime.now(timezone.utc).isoformat(), "key": "k",
                "batch": None, "holder": "host-x",
                "accepted_revision": self.holder.runner_identity["accepted_revision"]
                if accepted is None else accepted,
                "head": self.head() if head is None else head, "removed": []}

    def write_sweep_state(self, maintenance: dict) -> None:
        self.write_node_state(maintenance, host_revision=0)

    def host_change(self, revision: int) -> None:
        handled = getattr(self, "handled", 0)
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        try:
            maintenance = (json.loads(path.read_text()).get("state") or {}).get(
                "maintenance") or {}
        except (OSError, ValueError):
            maintenance = {}
        # A Host business write keeps the rest of maintenance (last_sweep...).
        maintenance["handled_host_revision"] = handled
        self.write_node_state(maintenance, host_revision=revision)

    def batch_of(self, index: int) -> str:
        return self.fake.prompts[index]["params"]["text"].split("batch ", 1)[1].split()[0]

    def checkpoint(self, batch: str, holder: str, through: int) -> None:
        self.write_node_state({"last_checkpoint": {
            "batch": batch, "node": {"holder_instance_id": holder},
            "host_revision": {"from": getattr(self, "handled", 0), "through": through,
                              "current": through}, "verified": True},
            "handled_host_revision": through})
        self.handled = through

    def node_env(self, holder: str = "node-1") -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": holder,
                                                  "platform": "zcode",
                                                  "repo": str(self.repo),
                                                  "session": "zcode-KT-sideagent"})
        return env

    def apply_as_node(self, batch: str) -> dict:
        proc = subprocess.run([sys.executable, str(SCRIPT), "sweep", "--apply", "--batch", batch,
                               "--repo", str(self.repo),
                               "--file", str(self.repo / ".kaola" / "heartbeat-prompt.json")],
                              capture_output=True, text=True, env=self.node_env())
        return json.loads(proc.stdout)

    def end_node_turn(self, outcome: str = "turn_completed", cursor: int = 90) -> dict:
        node = self.holder.node
        return self.holder.op_worker_event({
            "kind": "idle", "platform": "zcode", "session": "zcode-KT-sideagent",
            "repo": str(self.repo), "reason": f"outcome={outcome} stop_reason=end_turn",
            "event_cursor": cursor, "holder_instance_id": node["holder"],
            "turn_fingerprint": node["fingerprint"], "turn_outcome": outcome})

    def sweep_events(self, kind: str) -> list[dict]:
        log = Path(self.holder.args.record_dir) / "events.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()
                if json.loads(line).get("kind") == kind]

    def drive(self, check, what: str, timeout: float = 30.0) -> None:
        """Boundaries until check: the scan and the node start are threads, so
        each pass needs a fresh boundary to act on."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.boundary()
            if check():
                return
            time.sleep(0.1)
        self.fail(f"timed out waiting for {what}")

    def test_not_due_spends_nothing(self) -> None:
        self.write_sweep_state({"last_sweep": self.last_sweep(),
                                "handled_host_revision": 0})
        for _ in range(3):
            self.boundary()
        self.assertEqual(self.node_count(), 0)
        self.assertEqual(self.sweep_events("sideagent_sweep_scan_failed"), [])
        self.assertEqual(self.sweep_events("sideagent_node_batch"), [])
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertNotIn("sweep", self.holder.node)

    def test_due_empty_records_without_a_node(self) -> None:
        self.write_sweep_state({"handled_host_revision": 0})
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_empty")), "empty sweep receipt")
        doc = self.holder._lifecycle_state()
        last = doc["state"]["maintenance"]["last_sweep"]
        self.assertTrue(last["at"])
        self.assertIsNone(last["batch"])
        self.assertEqual(last["accepted_revision"],
                         self.holder.runner_identity["accepted_revision"])
        self.assertEqual(last["head"], self.head())
        self.assertEqual(self.node_count(), 0)
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(doc.get("host_revision"), 0)
        # The fresh due mark makes the next pass quiet.
        self.boundary()
        self.assertEqual(len(self.sweep_events("sideagent_sweep_empty")), 1)

    def test_due_candidates_send_exactly_one_sweep_batch(self) -> None:
        self.write_sweep_state({"handled_host_revision": 0})
        stale = self.repo / ".kaola" / "x.tmp"
        stale.write_text("leftover\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(stale, (two_days, two_days))
        self.drive(lambda: len(self.fake.prompts) == 1, "the sweep batch prompt")
        self.assertEqual(self.node_count(), 1)
        batches = self.sweep_events("sideagent_node_batch")
        self.assertEqual(len(batches), 1)
        batch = batches[0]
        self.assertTrue(batch["batch"].startswith("s-"))
        self.assertIn("sweep", batch)
        self.assertEqual(batch["target_holder"], "node-1")
        text = self.fake.prompts[0]["params"]["text"]
        self.assertIn(f"sweep --apply --batch {batch['batch']}", text)
        # The node runs exactly the planned apply; the tool writes the
        # checkpoint (last_sweep) under the node's own identity.
        receipt = self.apply_as_node(batch["batch"])
        self.assertEqual(receipt["result"], "swept", receipt)
        self.assertFalse(stale.exists())
        self.end_node_turn()
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_settled")), "sweep settle")
        settled = self.sweep_events("sideagent_sweep_settled")[0]
        self.assertEqual((settled["checkpoint"], settled["host_woken"]), ("verified", False))
        self.assertTrue(any(r.startswith("stale-file:") for r in settled["removed"]))
        self.wait_for(lambda: self.holder.node.get("phase") == "stopped", "node exact-stopped")
        self.assertTrue(self.fake.stops, "the carrier exact-stopped the node")
        for _ in range(2):
            self.boundary()
        self.assertEqual(len(self.sweep_events("sideagent_node_batch")), 1,
                         "a settled sweep is not re-sent")
        self.assertEqual(self.node_count(), 1)

    def test_reconcile_wins_over_a_queued_sweep(self) -> None:
        self.write_sweep_state({"handled_host_revision": 0})
        stale = self.repo / ".kaola" / "x.tmp"
        stale.write_text("leftover\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(stale, (two_days, two_days))
        self.host_change(4)  # a pending Host business change
        self.drive(lambda: len(self.fake.prompts) >= 1, "first batch")
        self.assertIn("maintenance node batch", self.fake.prompts[0]["params"]["text"],
                      "the reconcile batch goes first")
        self.assertNotIn("sweep --apply", self.fake.prompts[0]["params"]["text"])
        batches = [e for e in self.sweep_events("sideagent_node_batch")]
        self.assertFalse(any("sweep" in e for e in batches))
        # Settle the reconcile batch; the sweep then goes through a fresh node.
        self.checkpoint(self.batch_of(0), self.holder.node["holder"], through=4)
        self.end_node_turn()
        self.drive(lambda: any("sweep --apply" in p["params"]["text"]
                               for p in self.fake.prompts), "the queued sweep batch")
        self.assertEqual(self.node_count(), 2)

    def test_head_move_is_due_once(self) -> None:
        last = self.last_sweep(head="0" * 40)
        self.write_sweep_state({"last_sweep": last, "handled_host_revision": 0})
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_empty")), "merge-due sweep")
        doc = self.holder._lifecycle_state()
        self.assertEqual(doc["state"]["maintenance"]["last_sweep"]["head"], self.head())
        for _ in range(2):
            self.boundary()
        self.assertEqual(len(self.sweep_events("sideagent_sweep_empty")), 1,
                         "the recorded head is handled; not due again")
        self.assertEqual(self.node_count(), 0)

    def test_recorded_empty_moves_the_due_mark_once(self) -> None:
        """An unchanged kept set still moves last_sweep.at: the next pass is
        not due, so exactly one scan happens across many ticks."""
        kept_id = self.kept_worker_record()
        old_at = datetime.fromtimestamp(time.time() - 2 * 3600, tz=timezone.utc).isoformat()
        self.write_sweep_state({"handled_host_revision": 0,
                                "last_sweep": self.last_sweep(at=old_at)})
        # Pre-seed the identical kept alert the first record-empty will write.
        doc = self.holder._lifecycle_state()
        doc["state"].setdefault("alerts", {})["sweep-kept"] = {
            "level": "warn", "owner": "host", "rev": 1,
            "summary": "x", "next": "x", "writer": "tool:sweep",
            "writer_holder": "host-x",
            "inputs": {kept_id: {"why": "identity-mismatch",
                                 "evidence": "opencode-KT-i99-a",
                                 "next": "Host: reconcile the session's original holder record"}}}
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        path.write_text(json.dumps(doc))
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_empty")), "empty sweep")
        last = self.holder._lifecycle_state()["state"]["maintenance"]["last_sweep"]
        self.assertNotEqual(last["at"], old_at, "the due mark moved")
        for _ in range(4):
            self.boundary()
        self.assertEqual(len(self.sweep_events("sideagent_sweep_empty")), 1,
                         "one scan across many ticks, not one per tick")
        self.assertEqual(self.node_count(), 0)
        self.assertEqual(self.holder.pending_worker_events, [])

    def test_a_failed_record_empty_is_a_failed_scan_not_an_empty_one(self) -> None:
        self.write_sweep_state({"handled_host_revision": 0})
        # The binding stays usable; only the tool's state write can fail.
        os.chmod(self.repo / ".kaola", 0o555)
        try:
            self.drive(lambda: bool(self.sweep_events("sideagent_sweep_scan_failed")),
                       "the failed scan")
        finally:
            os.chmod(self.repo / ".kaola", 0o755)
        self.assertEqual(self.sweep_events("sideagent_sweep_empty"), [])
        for _ in range(3):
            self.boundary()
        self.assertEqual(len(self.sweep_events("sideagent_sweep_scan_failed")), 1,
                         "the failed attempt cools down; no rescan")
        self.assertEqual(self.node_count(), 0)

    def test_a_fully_vanished_plan_still_settles_verified(self) -> None:
        self.write_sweep_state({"handled_host_revision": 0})
        stale = self.repo / ".kaola" / "x.tmp"
        stale.write_text("leftover\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(stale, (two_days, two_days))
        self.drive(lambda: len(self.fake.prompts) == 1, "the sweep batch prompt")
        batch = self.sweep_events("sideagent_node_batch")[0]["batch"]
        stale.unlink()  # every planned candidate vanished before the apply
        receipt = self.apply_as_node(batch)
        self.assertEqual(receipt["result"], "nothing", receipt)
        last = self.holder._lifecycle_state()["state"]["maintenance"]["last_sweep"]
        self.assertEqual((last["batch"], last["holder"], last["removed"]),
                         (batch, "node-1", []))
        self.end_node_turn()
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_settled")), "sweep settle")
        settled = self.sweep_events("sideagent_sweep_settled")[0]
        self.assertEqual((settled["checkpoint"], settled["host_woken"], settled["removed"]),
                         ("verified", False, []))

    # -- Issue #353: child-process bounds and anti-starvation -----------------

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def linked_worktree(self, issue: int = 5) -> tuple[Path, str]:
        path = self.repo / ".kw" / "worktrees" / f"issue-{issue}"
        git(self.repo, "worktree", "add", str(path), "-b", f"workflow/issue-{issue}")
        return path, git(path, "rev-parse", "HEAD").strip()

    def set_env(self, name: str, value: str) -> None:
        old = os.environ.get(name)
        os.environ[name] = value
        self.addCleanup(lambda: os.environ.pop(name, None) if old is None
                        else os.environ.__setitem__(name, old))

    def test_scan_timeout_kills_the_tool_group_and_cools_down(self) -> None:  # T8
        saved = getattr(holder_module, "SWEEP_SCAN_TIMEOUT_SECONDS", 600.0)
        holder_module.SWEEP_SCAN_TIMEOUT_SECONDS = 2.0
        self.addCleanup(setattr, holder_module, "SWEEP_SCAN_TIMEOUT_SECONDS", saved)
        _path, head = self.linked_worktree(5)
        self.set_gh({"5": "CLOSED"}, {"5": head}, sleep=30)
        pid_file = Path(self.tmp.name) / "gh.pid"
        self.set_env("KAOLA_SWEEP_FORGE_TIMEOUT", "60")
        self.set_env("FAKE_GH_PID", str(pid_file))
        self.write_sweep_state({"handled_host_revision": 0})
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_scan_failed")),
                   "scan_failed", timeout=10)
        self.assertEqual(self.holder.node["sweep"]["phase"], "cooldown")
        self.wait_for(lambda: pid_file.exists(), "fake gh pid file")
        pid = int(pid_file.read_text())
        self.wait_for(lambda: not self._pid_alive(pid), "fake gh process-group kill")
        # A fast forge plus an expired cooldown recovers at the next boundaries.
        self.set_gh({"5": "CLOSED"}, {"5": head})
        self.holder.node["sweep"]["until"] = 0
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_empty"))
                   or any("sweep" in e for e in self.sweep_events("sideagent_node_batch")),
                   "sweep recovery")

    def test_timed_out_receipt_is_a_failed_scan(self) -> None:  # T9
        _path, head = self.linked_worktree(5)
        self.set_gh({"5": "CLOSED"}, {"5": head}, sleep=30)
        self.set_env("KAOLA_SWEEP_FORGE_TIMEOUT", "1")
        self.write_sweep_state({"handled_host_revision": 0})
        self.drive(lambda: bool(self.sweep_events("sideagent_sweep_scan_failed")),
                   "scan_failed", timeout=15)
        self.assertEqual(self.holder.node["sweep"]["phase"], "cooldown")
        doc = self.holder._lifecycle_state()
        self.assertNotIn("last_sweep", doc["state"]["maintenance"])

    def test_overdue_sweep_preempts_pending_reconcile(self) -> None:  # T10
        old_at = datetime.fromtimestamp(time.time() - 3 * 3600,
                                        tz=timezone.utc).isoformat()
        self.write_sweep_state({"last_sweep": self.last_sweep(at=old_at),
                                "handled_host_revision": 0})
        stale = self.repo / ".kaola" / "x.tmp"
        stale.write_text("leftover\n", encoding="utf-8")
        two_days = time.time() - 2 * 86400
        os.utime(stale, (two_days, two_days))
        # A Host change is pending and the Host turn is active: nothing is sent.
        self.host_change(1)
        self.holder.turn["active"] = True
        for _ in range(3):
            self.boundary()
        self.assertEqual(self.fake.prompts, [])
        self.holder.turn["active"] = False
        # A fresh Host change stays pending across every boundary: the overdue
        # sweep still gets its batch through between reconcile batches.
        rev = 1
        handled_prompts = 0
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            self.boundary()
            if any("sweep --apply" in p["params"]["text"] for p in self.fake.prompts):
                break
            if len(self.fake.prompts) > handled_prompts:
                text = self.fake.prompts[handled_prompts]["params"]["text"]
                if "sweep --apply" not in text and self.holder.node.get("batch"):
                    batch = text.split("batch ", 1)[1].split()[0]
                    self.checkpoint(batch, self.holder.node["holder"], through=rev)
                    rev += 1
                    self.host_change(rev)
                    self.end_node_turn()
                handled_prompts = len(self.fake.prompts)
            time.sleep(0.1)
        self.assertTrue(any("sweep --apply" in p["params"]["text"]
                            for p in self.fake.prompts),
                        "an overdue sweep batch is sent while a Host change is pending")
        doc = self.holder._lifecycle_state()
        self.assertGreater(doc.get("host_revision") or 0,
                           (doc["state"].get("maintenance") or {}).get(
                               "handled_host_revision") or -1)


class SweepDocs(unittest.TestCase):
    """Issue #353: the shipped Skill text names the new sweep duties."""

    def test_close_out_sweep_docs(self) -> None:  # T11
        maintenance = (REPO / "templates" / "orchestrator" / "references"
                       / "doc-maintenance.md").read_text(encoding="utf-8")
        self.assertIn("sweep --apply --repo", maintenance)
        self.assertIn("maintenance.last_sweep", maintenance)


if __name__ == "__main__":
    unittest.main()
