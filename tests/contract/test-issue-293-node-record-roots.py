#!/usr/bin/env python3
"""Issue #293: the Host carrier resolves its node record across every record
root, and a verified ``session-exists`` refusal adopts or defers to the live
holder instead of orphaning it.

A node start resolves through ``find_directory`` across all roots, so the
node's holder can write its record under a legacy TMPDIR root or the fixed
root while the Host holder's lookups were scoped to the Host's own root. The
pre-fix carrier then found no target, started the node again, got a verified
``session-exists`` refusal and marked the live node failed - orphaned and
never reclaimed. These tests run the real holder in-process with stub agents
and fake node sockets against records planted in each root; no live session
is used.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import textwrap
import time
import unittest

PROJECT = Path(__file__).resolve().parents[2]
ISSUE255 = PROJECT / "tests" / "contract" / "test-issue-255-lifecycle-state.py"

spec = importlib.util.spec_from_file_location("issue255_helpers", ISSUE255)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

holder_module = helpers.holder_module
acp_paths = holder_module.acp_paths
StubAgent = helpers.StubAgent
FakeNode = helpers.FakeNode

FIXED = acp_paths.default_root()
UID_ROOT = f"kaola-{os.getuid()}"

NODE_RUNNER = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    counter = Path(os.environ["FAKE_NODE_COUNTER"])
    n = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(n))
    if os.environ.get("FAKE_NODE_REFUSED"):
        print(json.dumps({"result": "refused", "error": {
            "code": "session-exists",
            "holder_pid": int(os.environ["FAKE_NODE_LIVE_PID"]),
            "identity": os.environ.get("FAKE_NODE_IDENTITY") or "verified"}}))
        sys.exit(1)
    holder = f"node-{n}"
    Path(os.environ["FAKE_NODE_RECORD"]).write_text(json.dumps({
        "session_role": "sideagent", "repo": os.environ["FAKE_NODE_REPO"], "state": "ready",
        "holder_instance_id": holder, "holder_pid": int(os.environ["FAKE_NODE_PID"]),
        "socket_path": os.environ["FAKE_NODE_SOCKET"],
        "dispatcher": json.loads(os.environ.get("KAOLA_ACP_DISPATCHER") or "null"),
        "holder_features": ["heartbeat-state/2", "sideagent-relay/1", "sideagent-node/1"]}))
    print(json.dumps({"holder_instance_id": holder,
                      "session": os.environ["FAKE_NODE_SESSION"]}))
""")

FAKE_ENV = ("FAKE_NODE_COUNTER", "FAKE_NODE_RECORD", "FAKE_NODE_REPO", "FAKE_NODE_PID",
            "FAKE_NODE_SOCKET", "FAKE_NODE_SESSION", "FAKE_NODE_REFUSED",
            "FAKE_NODE_LIVE_PID", "FAKE_NODE_IDENTITY")


class PathsAllRoots(unittest.TestCase):
    """``find_directory`` with an explicit root plus ``all_roots`` keeps the
    explicit root first but also covers the other record roots."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i293-paths-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = str(self.base / "repo")
        self.digest = hashlib.sha256(self.repo.encode()).hexdigest()[:16]
        self.explicit = self.base / "records"
        self.session = f"zcode-I293-{os.getpid()}-paths"
        self.saved_tmpdir = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(self.base / "tmpdir-env")
        self.addCleanup(self.restore_tmpdir)
        self.legacy = Path(os.environ["TMPDIR"]) / UID_ROOT

    def restore_tmpdir(self) -> None:
        if self.saved_tmpdir is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = self.saved_tmpdir

    def plant(self, root: Path) -> Path:
        directory = root / "zcode" / self.session / self.digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "repo": self.repo, "state": "ready",
            "holder_instance_id": "node-1", "holder_pid": os.getpid()}))
        return directory

    def test_all_roots_finds_a_live_record_in_a_legacy_tmpdir_root(self) -> None:
        planted = self.plant(self.legacy)
        found = acp_paths.find_directory("zcode", self.session, self.repo,
                                         self.explicit, all_roots=True)
        self.assertEqual(found, planted)

    def test_all_roots_finds_a_live_record_in_the_explicit_root(self) -> None:
        planted = self.plant(self.explicit)
        found = acp_paths.find_directory("zcode", self.session, self.repo,
                                         self.explicit, all_roots=True)
        self.assertEqual(found, planted)

    def test_explicit_root_without_all_roots_stays_scoped(self) -> None:
        self.plant(self.legacy)
        found = acp_paths.find_directory("zcode", self.session, self.repo, self.explicit)
        self.assertEqual(found, self.explicit / "zcode" / self.session / self.digest)


class NodeRecordRoots(unittest.TestCase):
    """Minimal Host-carrier fixture modeled on HolderNodeMode: one Host holder
    with a node-mode binding, a fake runner recipe and a fake node socket."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i293-node-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        (self.repo / ".kaola").mkdir(parents=True)
        self.digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        self.records = self.base / "records"
        self.host_session = f"zcode-I293-{os.getpid()}-host"
        host_dir = self.records / "zcode" / self.host_session / self.digest
        host_dir.mkdir(parents=True)
        args = argparse.Namespace(record_dir=str(host_dir), socket=str(self.base / "host.sock"),
                                  platform="zcode", session=self.host_session,
                                  repo=str(self.repo), init_meta="", command="stub")
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-host-293"
        self.holder.state = "ready"
        self.holder.heartbeat_host = None
        self.holder.session_role = "host"
        self.holder.write_record()
        self.side_session = f"zcode-I293-{os.getpid()}-side"
        self.runner = self.base / "node-runner.sh"
        self.runner.write_text(NODE_RUNNER, encoding="utf-8")
        self.runner.chmod(0o755)
        self.side_sock = self.base / "node.sock"
        self.fake: FakeNode | None = None
        self.planted_roots: list[Path] = []
        self.addCleanup(self.remove_planted)
        self.saved_env = {key: os.environ.get(key) for key in (*FAKE_ENV, "TMPDIR")}
        self.addCleanup(self.restore_env)
        os.environ.update(FAKE_NODE_COUNTER=str(self.base / "count"),
                          FAKE_NODE_REPO=str(self.repo),
                          FAKE_NODE_PID=str(os.getpid()),
                          FAKE_NODE_SOCKET=str(self.side_sock),
                          FAKE_NODE_SESSION=self.side_session)
        for key in ("FAKE_NODE_REFUSED", "FAKE_NODE_LIVE_PID", "FAKE_NODE_IDENTITY"):
            os.environ.pop(key, None)
        self.saved_confirm = holder_module.NODE_STOP_CONFIRM_SECONDS
        holder_module.NODE_STOP_CONFIRM_SECONDS = 1.5
        self.addCleanup(self.restore_confirm)

    def restore_env(self) -> None:
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def restore_confirm(self) -> None:
        holder_module.NODE_STOP_CONFIRM_SECONDS = self.saved_confirm

    def remove_planted(self) -> None:
        # Only this test's unique session trees under shared roots.
        for root in self.planted_roots:
            session_dir = root / "zcode" / self.side_session
            shutil.rmtree(session_dir, ignore_errors=True)
            try:
                session_dir.parent.rmdir()
            except OSError:
                pass

    def legacy_root(self, name: str) -> Path:
        os.environ["TMPDIR"] = str(self.base / name)
        return Path(os.environ["TMPDIR"]) / UID_ROOT

    def plant_record(self, root: Path, holder: str = "node-planted", pid: int | None = None,
                     dispatcher: dict | None = None, register: bool = True) -> Path:
        directory = root / "zcode" / self.side_session / self.digest
        directory.mkdir(parents=True, exist_ok=True)
        record = {"session_role": "sideagent", "repo": str(self.repo), "state": "ready",
                  "holder_instance_id": holder,
                  "holder_pid": os.getpid() if pid is None else pid,
                  "socket_path": str(self.side_sock),
                  "holder_features": ["heartbeat-state/2", "sideagent-relay/1", "sideagent-node/1"]}
        if dispatcher is not None:
            record["dispatcher"] = dispatcher
        (directory / "record.json").write_text(json.dumps(record))
        if register:
            self.planted_roots.append(root)
        return directory

    def recipe(self) -> dict:
        return {"runner": str(self.runner),
                "argv": ["start", "--repo", str(self.repo), "--session", self.side_session,
                         "--role", "sideagent"]}

    def binding(self) -> dict:
        return {"platform": "zcode", "session": self.side_session, "state": "active",
                "mode": "node", "recipe": self.recipe()}

    def fingerprint(self, binding: dict) -> str:
        return json.dumps({key: binding.get(key) for key in ("session", "recipe", "since")},
                          sort_keys=True)

    def write_node_state(self, host_revision: int = 0, handled: int = 0) -> None:
        state = {"sideagent": self.binding(), "maintenance": {"handled_host_revision": handled}}
        if host_revision:
            state["section_sources"] = {"project": {"writer": "host",
                                                    "host_revision": host_revision}}
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2", "host_revision": host_revision,
            "body": json.dumps({"view": "host", "attention": [], "tasks": []}),
            "state": state}), encoding="utf-8")

    def boundary(self) -> None:
        with self.holder.worker_events_lock:
            self.holder._relay_pass()

    def wait_for(self, check, what: str, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.05)
        self.fail(f"timed out waiting for {what}")

    def log_kinds(self) -> list[str]:
        log = Path(self.holder.args.record_dir) / "events.jsonl"
        return [json.loads(line)["kind"] for line in log.read_text().splitlines()
                ] if log.exists() else []

    def node_count(self) -> int:
        counter = self.base / "count"
        return int(counter.read_text()) if counter.exists() else 0

    def record_dir_for(self, root: Path) -> Path:
        return root / "zcode" / self.side_session / self.digest

    def one_start_delivers_the_batch(self, root: Path) -> None:
        os.environ["FAKE_NODE_RECORD"] = str(self.record_dir_for(root) / "record.json")
        self.record_dir_for(root).mkdir(parents=True, exist_ok=True)
        self.fake = FakeNode(self.side_sock, Path(os.environ["FAKE_NODE_RECORD"]))
        self.write_node_state(host_revision=4)
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 1, "the node's batch")
        self.assertEqual(self.node_count(), 1, "one Host change starts exactly one node")
        kinds = self.log_kinds()
        self.assertIn("sideagent_node_started", kinds)
        self.assertNotIn("sideagent_node_start_failed", kinds)

    def test_node_record_in_a_legacy_tmpdir_root(self) -> None:
        root = self.legacy_root("tmpdir-legacy")
        self.planted_roots.append(root)
        self.one_start_delivers_the_batch(root)

    def test_node_record_in_the_fixed_root(self) -> None:
        self.planted_roots.append(FIXED)
        self.one_start_delivers_the_batch(FIXED)

    def drive_start_refused(self, record_path: Path, pid: int) -> None:
        os.environ.update(FAKE_NODE_REFUSED="1", FAKE_NODE_LIVE_PID=str(pid))
        self.holder._start_node(self.binding(), self.fingerprint(self.binding()))

    def test_session_exists_adopts_this_carrier_dispatched_holder(self) -> None:
        root = self.legacy_root("tmpdir-adopt")
        record_path = self.plant_record(
            root, holder="node-adopted",
            dispatcher={"holder_instance_id": self.holder.holder_instance_id,
                        "platform": "zcode", "session": self.host_session,
                        "repo": str(self.repo)}) / "record.json"
        self.fake = FakeNode(self.side_sock, record_path)
        self.write_node_state(host_revision=4)
        self.drive_start_refused(record_path, os.getpid())
        node = self.holder.node
        self.assertEqual(node.get("phase"), "running")
        self.assertEqual(node.get("holder"), "node-adopted")
        self.assertIn("node-adopted", node.get("holders", []))
        self.assertNotIn("failed", node)
        kinds = self.log_kinds()
        self.assertIn("sideagent_node_adopted", kinds)
        self.assertNotIn("sideagent_node_start_failed", kinds)
        # Never orphaned: the adopted holder is reclaimed by an exact stop.
        self.holder._reclaim_node()
        self.assertTrue(self.fake.stops, "the adopted node got no stop")
        self.assertEqual(self.fake.stops[0]["params"]["expected_holder_instance_id"],
                         "node-adopted")

    def test_session_exists_foreign_dispatched_defers_to_the_live_holder(self) -> None:
        root = self.legacy_root("tmpdir-foreign")
        record_path = self.plant_record(
            root, holder="node-foreign",
            dispatcher={"holder_instance_id": "other-carrier",
                        "platform": "zcode", "session": "other-host",
                        "repo": str(self.repo)}) / "record.json"
        self.fake = FakeNode(self.side_sock, record_path)
        self.write_node_state(host_revision=4)
        self.drive_start_refused(record_path, os.getpid())
        node = self.holder.node
        self.assertEqual(node.get("stop_unconfirmed"), {"holder": "node-foreign"})
        self.assertNotEqual(node.get("phase"), "running")
        self.assertNotIn("failed", node)
        kinds = self.log_kinds()
        self.assertIn("sideagent_node_start_refused_live", kinds)
        self.assertNotIn("sideagent_node_start_failed", kinds)
        # Once that holder is gone the late-confirm clears the stop and the
        # next pending Host change starts a fresh node.
        record = json.loads(record_path.read_text())
        record["holder_pid"] = self.fake.dead_pid
        record_path.write_text(json.dumps(record))
        os.environ["FAKE_NODE_RECORD"] = str(record_path)
        os.environ.pop("FAKE_NODE_REFUSED", None)
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = json.loads(path.read_text())
        doc["host_revision"] = 5
        doc["state"]["section_sources"] = {"project": {"writer": "host", "host_revision": 5}}
        doc["state"].setdefault("tasks", {})["t-5"] = {"stage": "review", "goal": "g",
                                                     "writer": "host"}
        path.write_text(json.dumps(doc))
        self.holder.turn["active"] = False
        self.boundary()
        self.wait_for(lambda: self.node_count() >= 2
                      and self.holder.node.get("phase") == "running",
                      "a fresh node after the foreign holder died")
        kinds = self.log_kinds()
        self.assertIn("sideagent_node_stop_confirmed_late", kinds)
        self.assertIn("sideagent_node_started", kinds)
        self.assertNotIn("failed", self.holder.node)

    def test_session_exists_unverified_keeps_the_failure_branch(self) -> None:
        root = self.legacy_root("tmpdir-unverified")
        record_path = self.plant_record(root, holder="node-x") / "record.json"
        self.fake = FakeNode(self.side_sock, record_path)
        self.write_node_state(host_revision=4)
        os.environ.update(FAKE_NODE_REFUSED="1", FAKE_NODE_LIVE_PID=str(os.getpid()),
                          FAKE_NODE_IDENTITY="unverified")
        self.holder._start_node(self.binding(), self.fingerprint(self.binding()))
        node = self.holder.node
        self.assertEqual(node.get("phase"), "stopped")
        self.assertIn("failed", node)
        self.assertIn("sideagent_node_start_failed", self.log_kinds())


if __name__ == "__main__":
    unittest.main()
