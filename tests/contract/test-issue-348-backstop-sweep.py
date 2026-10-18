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
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
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
              "FAKE_ACP_ROWS", "FAKE_ACP_CALLS", "KAOLA_SWEEP_INTERVAL_HOURS")
for name in CALLER_ENV:
    os.environ.pop(name, None)

FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    data = json.loads(open(os.environ["FAKE_GH_FILE"]).read())
    argv = sys.argv[1:]
    if argv[:2] == ["issue", "view"]:
        print(json.dumps({"state": data["issues"].get(argv[2], "OPEN")}))
    elif argv[:2] == ["pr", "list"]:
        head = argv[argv.index("--head") + 1]
        number = head.rsplit("-", 1)[1]
        oid = data.get("prs", {}).get(number)
        print(json.dumps([{"number": int(number), "headRefOid": oid}] if oid else []))
    else:
        sys.exit(2)
    """)

FAKE_ACP = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    calls = os.environ.get("FAKE_ACP_CALLS")
    if calls:
        with open(calls, "a") as stream:
            stream.write(json.dumps(sys.argv[1:]) + "\\n")
    data = json.loads(open(os.environ["FAKE_ACP_ROWS"]).read())
    argv = sys.argv[1:]
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
        self.assertEqual(kinds, {"session", "worktree", "stale-file"})

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

    def set_gh(self, issues: dict, prs: dict | None = None) -> None:
        self.gh_data.write_text(json.dumps({"issues": issues, "prs": prs or {}}),
                                encoding="utf-8")

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
        self.write_node_state({"handled_host_revision": handled}, host_revision=revision)

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


if __name__ == "__main__":
    unittest.main()
