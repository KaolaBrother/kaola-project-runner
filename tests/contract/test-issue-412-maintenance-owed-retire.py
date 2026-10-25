#!/usr/bin/env python3
"""Issue #412: Host-view node liveness without a carrier, the stranded
already-returned owed range, and a cancelled per-item disposition on the
dead-holder unknown retire route.

E1: ``node_is_running`` proved the node's dispatcher only against the state
file's ``carrier``, which ``state migrate --live`` alone writes. An ordinary
file, or one whose carrier names a stale incarnation of the same Host
session, reported ``no node is running`` while the bound node was live. The
dispatcher is now also proven by the dispatcher's own live ready Host record
in this repo. A dispatcher of a different Host session than a recorded
carrier still fails.

E2: the holder selects a batch only after ``max(handled, sent_through,
returned_through)``, so an owed range already returned to the Host is never
reselected and the Host view's ``next`` named no executable route. The view
now names the bounded ``state recovery-input --kind request`` route; the
holder and its no-auto-replay selection are unchanged.

E3: ``dead_holder_unknown_settlement`` refused every per-item disposition
other than ``accepted``. An accepted-done task now retires an unknown row
whose per-item disposition is ``cancelled`` too, reported as ``cancelled``;
any other value still refuses.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for name in CALLER_ENV:
    os.environ.pop(name, None)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


holder_module = load("kaola_acp_holder_412", REPO / "scripts" / "kaola-acp-holder.py")

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}
CITE = json.dumps({"path": "README.md", "locator": "README.md"})
ROUTE = "dead-holder unknown route"

HOST = {"platform": "codex", "session": "codex-KT-host", "holder_instance_id": "host-1"}
NODE = {"platform": "zcode", "session": "zcode-KT-node"}


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True,
                          env=env if env is not None else {k: v for k, v in os.environ.items()
                                                           if k not in CALLER_ENV},
                          timeout=60)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


class Fixture:
    """One isolated project: state file, record root, index and live rows."""

    def __init__(self, root: Path) -> None:
        repo = root / "consumer"
        (repo / ".kaola").mkdir(parents=True)
        self.repo = repo.resolve()
        (self.repo / "README.md").write_text("evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.records = root / "records"
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1", "--project", json.dumps({"code": "KT", "goal": "ship"}),
                         "--authorization", json.dumps(AUTH)])
        assert code == 0, out
        self.digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        return env

    def state(self, *args: str, env: dict | None = None) -> tuple[int, dict]:
        return run(["state", *args], env if env is not None else self.env())

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def write(self, doc: dict) -> None:
        self.file.write_text(json.dumps(doc), encoding="utf-8")

    def bind_node(self, **binding: object) -> None:
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
                               "--source", "bind", "--section", "sideagent",
                               "--expect-revision", str(self.doc()["revision"]),
                               "--set", json.dumps({"platform": NODE["platform"],
                                                    "session": NODE["session"],
                                                    "state": "active", "mode": "node", **binding}))
        assert code == 0, out

    def record_dir(self, platform: str, session: str) -> Path:
        directory = self.records / platform / session / self.digest
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write_record(self, platform: str, session: str, record: dict) -> Path:
        directory = self.record_dir(platform, session)
        path = directory / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def node_record(self, *, pid: int | None = None, host: dict | None = None,
                    holder: str = "node-1", session: str | None = None,
                    features: list | None = None, socket: bool = False) -> dict:
        host = host or HOST
        session = session or NODE["session"]
        record = {"session_role": "sideagent", "state": "ready",
                  "platform": NODE["platform"], "session": session,
                  "repo": str(self.repo), "holder_instance_id": holder,
                  "holder_pid": os.getpid() if pid is None else pid,
                  "dispatcher": {"holder_instance_id": host["holder_instance_id"],
                                 "platform": host["platform"], "session": host["session"],
                                 "repo": str(self.repo)}}
        if features is not None:
            record["holder_features"] = features
        if socket:
            sock = self.record_dir(NODE["platform"], session) / "holder.sock"
            sock.write_text("", encoding="utf-8")
            record["socket_path"] = str(sock)
        return record

    def write_node_record(self, root: Path, **kwargs) -> Path:
        session = kwargs.get("session") or NODE["session"]
        directory = root / NODE["platform"] / session / self.digest
        directory.mkdir(parents=True, exist_ok=True)
        record = self.node_record(**kwargs)
        if kwargs.get("socket"):
            sock = directory / "holder.sock"
            sock.write_text("", encoding="utf-8")
            record["socket_path"] = str(sock)
        path = directory / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def make_holder(self, platform: str = "zcode",
                    session: str = "zcode-KT-i412-orch") -> object:
        """A real Host Holder against this fixture's record root and repo."""
        args = argparse.Namespace(record_dir=str(self.record_dir(platform, session)),
                                  socket=str(self.records.parent / "host.sock"),
                                  platform=platform, session=session, repo=str(self.repo),
                                  init_meta="", command="stub", session_role="host")
        return holder_module.Holder(args)

    def host_record(self, *, holder: str | None = None, pid: int | None = None,
                    role: str = "host", state: str = "ready",
                    session: str | None = None) -> dict:
        return {"session_role": role, "state": state,
                "platform": HOST["platform"], "session": session or HOST["session"],
                "repo": str(self.repo),
                "holder_instance_id": holder or HOST["holder_instance_id"],
                "holder_pid": os.getpid() if pid is None else pid,
                "acp_session_id": "ses-412"}

    def host_view(self) -> dict:
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        assert code == 0, out
        return out

    def dead_pid(self) -> int:
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait()
        return proc.pid


class NodeLivenessWithoutCarrier(unittest.TestCase):
    """E1: the dispatcher is proven by its own live Host record too."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-liveness-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def fixture(self) -> Fixture:
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        fx = Fixture(root)
        fx.bind_node()
        fx.write_record(NODE["platform"], NODE["session"], fx.node_record())
        return fx

    def test_no_carrier_live_host_record_counts_as_running(self) -> None:
        fx = self.fixture()
        self.assertNotIn("carrier", fx.doc())
        fx.write_record(HOST["platform"], HOST["session"], fx.host_record())
        view = fx.host_view()
        self.assertEqual(view["sideagent_maintenance"], "a node is running")

    def test_stale_carrier_of_the_same_host_session_counts_as_running(self) -> None:
        # After a Host restart the file's recorded carrier names the old
        # holder of this same Host session; the dispatcher's live Host record
        # is the same session and holder.
        fx = self.fixture()
        doc = fx.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2",
                          "holder_instance_id": "host-old", "platform": HOST["platform"],
                          "session": HOST["session"]}
        fx.write(doc)
        fx.write_record(HOST["platform"], HOST["session"], fx.host_record())
        view = fx.host_view()
        self.assertEqual(view["sideagent_maintenance"], "a node is running")

    def test_no_host_record_stays_not_running(self) -> None:
        fx = self.fixture()
        self.assertIn("no node is running", fx.host_view()["sideagent_maintenance"])

    def test_host_record_of_another_holder_stays_not_running(self) -> None:
        fx = self.fixture()
        fx.write_record(HOST["platform"], HOST["session"], fx.host_record(holder="host-9"))
        self.assertIn("no node is running", fx.host_view()["sideagent_maintenance"])

    def test_host_record_with_a_dead_pid_stays_not_running(self) -> None:
        fx = self.fixture()
        fx.write_record(HOST["platform"], HOST["session"], fx.host_record(pid=fx.dead_pid()))
        self.assertIn("no node is running", fx.host_view()["sideagent_maintenance"])

    def test_a_dispatcher_of_another_host_session_stays_not_running(self) -> None:
        # A recorded carrier for a different Host session never adopts this
        # node's dispatcher, live record or not.
        fx = self.fixture()
        doc = fx.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2",
                          "holder_instance_id": "host-other", "platform": HOST["platform"],
                          "session": "codex-KT-other"}
        fx.write(doc)
        fx.write_record(HOST["platform"], HOST["session"], fx.host_record())
        self.assertIn("no node is running", fx.host_view()["sideagent_maintenance"])


class StrandedReturnedRange(unittest.TestCase):
    """E2: an owed range already returned to the Host gets an executable route."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-stranded-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def stranded(self, **binding: object) -> Fixture:
        """handled=1 < current=T; every change is already inside a returned
        input reaching T; no recovery input."""
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        fx = Fixture(root)
        fx.bind_node(**binding)
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "work", "--kind", "tasks", "--id", "t1",
                             "--set", json.dumps({"stage": "doing", "goal": "g"}))
        assert code == 0, out
        current = fx.doc()["host_revision"]
        doc = fx.doc()
        doc["state"]["maintenance"] = {"handled_host_revision": 1, "acked_host_revision": 1}
        doc["state"]["alerts"] = {"maintenance-returned": {
            "owner": "host", "level": "warn", "rev": 1,
            "summary": "maintenance needs Host recovery from original receipts",
            "inputs": {"batch:b-returned": {"why": "checkpoint-missing",
                                            "host_revision_through": current}}}}
        fx.write(doc)
        return fx

    @staticmethod
    def carrier() -> object:
        carrier = holder_module.Holder.__new__(holder_module.Holder)
        carrier.session_role = "host"
        carrier.node = {}
        return carrier

    @staticmethod
    def maintenance_row(view: dict) -> dict | None:
        return next((row for row in view["attention"]
                     if row.get("kind") == "maintenance" and row.get("id") == "pending"), None)

    def test_the_returned_range_is_never_reselected(self) -> None:
        # Control on baseline and candidate alike: no automatic replay.
        fx = self.stranded()
        carrier = self.carrier()
        self.assertIsNone(carrier._node_host_pending(fx.doc()))
        self.assertIsNone(carrier._node_recovery_pending(fx.doc()))

    def test_the_host_view_names_the_bounded_request_route(self) -> None:
        fx = self.stranded()
        row = self.maintenance_row(fx.host_view())
        self.assertIsNotNone(row)
        self.assertEqual(row["why"],
                         "owed range already returned to the Host; the carrier does not resend it")
        self.assertIn(f"state recovery-input --file {fx.file} --kind request", row["next"])
        self.assertIn("--source ORIGINAL_SOURCE", row["next"])
        self.assertIn("--evidence alerts/maintenance-returned", row["next"])

    def test_the_stranded_next_uses_the_bindings_state_tool(self) -> None:
        tool = Path(self.tmp.name) / "state-tool"
        tool.write_text("#!/bin/sh\n", encoding="utf-8")
        fx = self.stranded(recipe={"runner": "/abs/runner", "argv": ["start"],
                                   "state_tool": str(tool)})
        row = self.maintenance_row(fx.host_view())
        self.assertIsNotNone(row)
        self.assertIn(f"python3 {tool} state recovery-input", row["next"])

    def test_a_dead_node_reports_the_stranded_range(self) -> None:
        fx = self.stranded()
        self.assertEqual(fx.host_view()["sideagent_maintenance"],
                         "no node is running; the owed range was already returned to the Host "
                         "and is not resent automatically; request one bounded batch with "
                         "state recovery-input --kind request")

    @staticmethod
    def usable_recipe(fx: Fixture) -> dict:
        """A node recipe the real Holder's `_node_binding` accepts, without an
        explicit `state_tool` — discovery must find the sibling dispatch tool."""
        return {"runner": str(SCRIPT),
                "argv": ["start", "--repo", str(fx.repo), "--session", NODE["session"],
                         "--role", "sideagent"]}

    def test_the_emitted_route_runs_without_an_explicit_state_tool(self) -> None:
        fx = self.stranded()
        doc = fx.doc()
        binding = doc["state"]["sideagent"]
        binding["recipe"] = self.usable_recipe(fx)
        doc["carrier"] = {"holder_instance_id": HOST["holder_instance_id"],
                          "platform": HOST["platform"], "session": HOST["session"]}
        fx.write(doc)
        fx.write_record(NODE["platform"], NODE["session"],
                        fx.node_record(holder="node-1",
                                       features=["sideagent-relay/1"], socket=True))
        holder = fx.make_holder()
        self.assertEqual((holder._node_binding() or {}).get("session"), NODE["session"],
                         "the recipe is usable to a real Holder without state_tool")
        view = fx.host_view()
        self.assertEqual(view["sideagent_maintenance"], "a node is running")
        row = self.maintenance_row(view)
        self.assertIsNotNone(row)
        self.assertNotIn("<Project Runner>", row["next"])
        command = row["next"].split("request one bounded batch: ", 1)[1]
        argv = shlex.split(command)
        self.assertTrue(Path(argv[1]).is_file(), f"no resolved tool: {command}")
        # Execute exactly the emitted command under the verified Host identity.
        host = {"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                "repo": str(fx.repo), "holder_instance_id": "host-recovery"}
        fx.write_record(host["platform"], host["session"], {
            "holder_instance_id": host["holder_instance_id"], "session_role": "host",
            "state": "ready", "repo": str(fx.repo), "holder_pid": os.getpid(),
            "acp_session_id": "ses-412"})
        env = fx.env()
        env["KAOLA_ACP_DISPATCHER"] = json.dumps(host)
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = fx.doc()
        item = doc["state"]["maintenance"].get("recovery_input")
        self.assertEqual((item or {}).get("kind"), "request")
        current = doc["host_revision"]
        # The live node then gets exactly one batch for the requested range.
        sends = []
        holder._relay_send = lambda target, text: (
            sends.append((target, text)) or {"outcome": "in_progress",
                                             "prompt_fingerprint": "sha256:x"})
        holder._sweep_pass = lambda *a, **k: None
        holder.turn["active"] = False
        holder.node.update(holder="node-1", phase="running")
        for _ in range(2):
            holder._node_relay_pass(binding)
        self.assertEqual(len(sends), 1, "exactly one send for the requested range")
        self.assertEqual(sends[0][0]["holder_instance_id"], "node-1")
        events = [json.loads(line)
                  for line in (holder.record_dir / "events.jsonl").read_text().splitlines()
                  if line.strip()]
        batches = [event for event in events if event.get("kind") == "sideagent_node_batch"]
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["host_revision_through"], current)
        self.assertEqual(batches[0]["recovery_input"], item)

    def test_the_request_selector_selects_the_stranded_range_once(self) -> None:
        """Proves the existing request selector for a stranded range — it calls
        `state recovery-input` directly rather than executing the emitted
        `next` command, so it does not prove the command itself is runnable."""
        fx = self.stranded()
        carrier = self.carrier()
        # The route itself runs under the verified Host identity.
        host = {"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                "repo": str(fx.repo), "holder_instance_id": "host-recovery"}
        fx.write_record(host["platform"], host["session"], {
            "holder_instance_id": host["holder_instance_id"], "session_role": "host",
            "state": "ready", "repo": str(fx.repo), "holder_pid": os.getpid(),
            "acp_session_id": "ses-412"})
        env = fx.env()
        env["KAOLA_ACP_DISPATCHER"] = json.dumps(host)
        code, out = fx.state("recovery-input", "--file", str(fx.file), "--kind", "request",
                             "--source", "ORIGINAL_SOURCE",
                             "--evidence", "alerts/maintenance-returned", env=env)
        self.assertEqual(code, 0, out)
        item = out["value"]
        self.assertEqual(item["kind"], "request")
        doc = fx.doc()
        current = doc["host_revision"]
        self.assertEqual((doc["state"]["maintenance"].get("recovery_input") or {}).get("seq"),
                         item["seq"])
        self.assertEqual(carrier._node_recovery_pending(doc), item)
        self.assertEqual(carrier._node_host_pending(doc, requested=True), current,
                         "one bounded selection over the stranded range")
        carrier.node["recovery_sent"] = item["seq"]
        self.assertIsNone(carrier._node_recovery_pending(doc),
                          "once sent it is not selected again")

    def test_a_new_host_change_restores_the_original_row(self) -> None:
        fx = self.stranded()
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "work", "--kind", "tasks", "--id", "t2",
                             "--set", json.dumps({"stage": "todo", "goal": "new"}))
        self.assertEqual(code, 0, out)
        current = fx.doc()["host_revision"]
        self.assertEqual(self.carrier()._node_host_pending(fx.doc()), current)
        self.assertEqual(self.maintenance_row(fx.host_view()),
                         {"kind": "maintenance", "id": "pending",
                          "why": "bounded reconciliation owed",
                          "next": "use the bound node or recover from original receipts"})


class StopDutyPrecedence(unittest.TestCase):
    """Item 1: a returned stop duty gates before the bounded request route.

    The holder returns early on ``stop_unconfirmed`` (it starts and sends no
    node while that old node holder is alive), so the stranded-range view must
    name the exact stop before the recovery request.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-stopduty-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def stranded_with_stop_duty(self) -> Fixture:
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        fx = Fixture(root)
        fx.bind_node()
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "work", "--kind", "tasks", "--id", "t1",
                             "--set", json.dumps({"stage": "doing", "goal": "g"}))
        assert code == 0, out
        current = fx.doc()["host_revision"]
        doc = fx.doc()
        doc["state"]["maintenance"] = {"handled_host_revision": 1, "acked_host_revision": 1}
        doc["state"]["alerts"] = {"maintenance-returned": {
            "owner": "host", "level": "warn", "rev": 1,
            "summary": "maintenance needs Host recovery from original receipts",
            "inputs": {"batch:b-oldnode": {"why": "old-node-live",
                                           "evidence": "carrier-events#9",
                                           "host_revision_through": current}}}}
        fx.write(doc)
        return fx

    @staticmethod
    def maintenance_row(view: dict) -> dict | None:
        return next((row for row in view["attention"]
                     if row.get("kind") == "maintenance" and row.get("id") == "pending"), None)

    def test_the_stop_duty_row_names_the_exact_stop_first(self) -> None:
        fx = self.stranded_with_stop_duty()
        row = self.maintenance_row(fx.host_view())
        self.assertIsNotNone(row)
        self.assertEqual(row["why"],
                         "owed range waits on a maintenance stop duty; the carrier starts "
                         "or sends no node while that old node holder is alive")
        self.assertIn("confirm the exact stop of the old node holder named by "
                      "alerts/maintenance-returned input(s) batch:b-oldnode", row["next"])
        self.assertIn(f"then request one bounded batch: python3", row["next"])
        self.assertIn(f"state recovery-input --file {fx.file} --kind request", row["next"])

    def test_the_stop_duty_sentence_reports_running_and_dead_nodes(self) -> None:
        fx = self.stranded_with_stop_duty()
        tail = ("the owed range waits on a maintenance stop duty in alerts/maintenance-returned; "
                "confirm that old node holder's exact stop, then request one bounded batch with "
                "state recovery-input --kind request")
        self.assertEqual(fx.host_view()["sideagent_maintenance"], f"no node is running; {tail}")
        fx.write_record(NODE["platform"], NODE["session"], fx.node_record())
        doc = fx.doc()
        doc["carrier"] = {"holder_instance_id": HOST["holder_instance_id"],
                          "platform": HOST["platform"], "session": HOST["session"]}
        fx.write(doc)
        self.assertEqual(fx.host_view()["sideagent_maintenance"], f"a node is running; {tail}")

    def test_the_stop_duty_route_resolves_a_real_tool(self) -> None:
        fx = self.stranded_with_stop_duty()
        doc = fx.doc()
        doc["state"]["sideagent"]["recipe"] = StrandedReturnedRange.usable_recipe(fx)
        fx.write(doc)
        row = self.maintenance_row(fx.host_view())
        self.assertIsNotNone(row)
        self.assertNotIn("<Project Runner>", row["next"])
        self.assertIn("confirm the exact stop of the old node holder named by "
                      "alerts/maintenance-returned input(s) batch:b-oldnode", row["next"])
        command = row["next"].split("then request one bounded batch: ", 1)[1]
        argv = shlex.split(command)
        self.assertTrue(Path(argv[1]).is_file(), f"no resolved tool: {command}")
        # Not executed: the live old node holder still blocks the batch.

    def test_a_live_old_node_holder_blocks_the_request_batch(self) -> None:
        """Control, green on baseline too: while ``stop_unconfirmed`` names a
        holder whose record pid is still alive, the carrier's relay pass sends
        nothing — even with a pending Host recovery request."""
        fx = self.stranded_with_stop_duty()
        # The Host's bounded request is registered for real.
        host = {"platform": "zcode", "session": "zcode-KT-i412-orch",
                "repo": str(fx.repo), "holder_instance_id": "host-recovery"}
        fx.write_record(host["platform"], host["session"], {
            "holder_instance_id": host["holder_instance_id"], "session_role": "host",
            "state": "ready", "repo": str(fx.repo), "holder_pid": os.getpid(),
            "acp_session_id": "ses-412"})
        env = fx.env()
        env["KAOLA_ACP_DISPATCHER"] = json.dumps(host)
        code, out = fx.state("recovery-input", "--file", str(fx.file), "--kind", "request",
                             "--source", "ORIGINAL_SOURCE",
                             "--evidence", "alerts/maintenance-returned", env=env)
        self.assertEqual(code, 0, out)
        # The old node holder still runs: its record pid is alive.
        fx.write_record(NODE["platform"], NODE["session"],
                        fx.node_record(holder="old-node"))
        holder = fx.make_holder(session=host["session"])
        sends = []
        holder._relay_send = lambda target, text: sends.append(text) or {"outcome": "in_progress"}
        holder._sweep_pass = lambda *a, **k: None
        holder.turn["active"] = False
        holder.node["stop_unconfirmed"] = {"holder": "old-node"}
        binding = fx.doc()["state"]["sideagent"]
        holder._node_relay_pass(binding)
        self.assertEqual(sends, [], "no batch while the old node holder is alive")
        self.assertEqual(holder.node.get("stop_unconfirmed"), {"holder": "old-node"})


class StateToolDiscoveryNotFound(unittest.TestCase):
    """Item: when no state tool exists anywhere the view names the prerequisite
    instead of a runnable-looking placeholder command."""

    def load_isolated_record(self, isolated: Path):
        """Load a copy of the record module beside no dispatch tool and no
        sibling `kaola-project-runner` Skill (the installed-Skill layout)."""
        import shutil
        module_dir = isolated / "deep" / "mod"
        module_dir.mkdir(parents=True)
        shutil.copy(REPO / "scripts" / "kaola-record-contract.py", module_dir)
        shutil.copy(REPO / "scripts" / "kaola-acp-paths.py", module_dir)
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(
            "kaola_record_contract_isolated", module_dir / "kaola-record-contract.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def stranded_doc(recipe: dict | None = None) -> dict:
        binding = {"platform": "zcode", "session": "zcode-KT-i412-notool",
                   "state": "active", "mode": "node"}
        if recipe is not None:
            binding["recipe"] = recipe
        return {"host_revision": 5,
                "state": {"sideagent": binding,
                          "maintenance": {"handled_host_revision": 1,
                                          "acked_host_revision": 1},
                          "alerts": {"maintenance-returned": {
                              "owner": "host", "level": "warn", "rev": 1,
                              "summary": "s",
                              "inputs": {"batch:b-returned": {
                                  "why": "checkpoint-missing",
                                  "host_revision_through": 5}}}},
                          "tasks": {"t1": {"stage": "doing", "goal": "g",
                                          "host_revision": 5}}}}

    def test_no_tool_anywhere_names_the_prerequisite(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-notool-")
        self.addCleanup(tmp.cleanup)
        isolated = Path(tmp.name)
        record = self.load_isolated_record(isolated)
        for recipe in (None,
                       {"runner": "/abs/runner", "argv": ["start"],
                        "state_tool": "/abs/nonexistent-state-tool"}):
            with self.subTest(recipe=recipe):
                view = record.host_view(self.stranded_doc(recipe), None)
                row = next(row for row in view["attention"]
                           if row.get("kind") == "maintenance" and row.get("id") == "pending")
                self.assertIn("none was found (checked:", row["next"])
                self.assertIn(str(isolated / "deep" / "mod" / "kaola-dispatch.py"), row["next"])
                self.assertIn("set sideagent.recipe.state_tool", row["next"])
                self.assertIn("state recovery-input --file", row["next"])
                self.assertNotIn("<Project Runner>", row["next"])
                self.assertNotIn("python3 ", row["next"],
                                 "no runnable-looking command without a real tool")
                if recipe is not None:
                    self.assertIn("/abs/nonexistent-state-tool", row["next"],
                                  "the checked candidates are listed")


class LiveNodeHolderVisible(unittest.TestCase):
    """Item 3: the Host view names the live node holder; checkpoint history
    stays truthful (the dead checkpoint author is never rewritten)."""

    def test_the_view_names_the_live_holder_not_the_checkpoint_author(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-holder-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "case"
        root.mkdir()
        fx = Fixture(root)
        fx.bind_node()
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "work", "--kind", "tasks", "--id", "t1",
                             "--set", json.dumps({"stage": "doing", "goal": "g"}))
        self.assertEqual(code, 0, out)
        current = fx.doc()["host_revision"]
        doc = fx.doc()
        doc["carrier"] = {"holder_instance_id": HOST["holder_instance_id"],
                          "platform": HOST["platform"], "session": HOST["session"]}
        doc["state"]["maintenance"] = {
            "handled_host_revision": current - 1, "acked_host_revision": current - 1,
            "last_verified": {"batch": "b-old", "verified": True,
                              "node": {"session": NODE["session"],
                                       "holder_instance_id": "dead-7d3675cc"}},
            "last_checkpoint": {"batch": "b-old", "verified": True,
                                "node": {"session": NODE["session"],
                                         "holder_instance_id": "dead-7d3675cc"},
                                "host_revision": {"through": current - 1}, "settled": []}}
        fx.write(doc)
        fx.write_record(NODE["platform"], NODE["session"],
                        fx.node_record(holder="live-d5852950"))
        before = fx.doc()["state"]["maintenance"]
        view = fx.host_view()
        self.assertEqual(view.get("sideagent_node_holder"), "live-d5852950")
        self.assertEqual(view["sideagent_maintenance"], "a node is running")
        self.assertEqual(fx.doc()["state"]["maintenance"], before,
                         "the view never rewrites checkpoint or verified evidence")
        # The next real checkpoint writes its own caller's holder, never a
        # rebind: test-issue-255-lifecycle-state.py::MaintenanceCheckpoint.
        # test_two_consecutive_nodes_account_for_their_fixed_inputs already
        # proves apply_checkpoint records the live writer (node-1 then node-2).


class MatrixCounterexamples(unittest.TestCase):
    """Probe section-3 anti-cases that must stay quiet (controls; the two
    relay-gate checks also hold on baseline)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-matrix-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def fixture(self, *, handled_same: bool) -> Fixture:
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        fx = Fixture(root)
        fx.bind_node()
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "work", "--kind", "tasks", "--id", "t1",
                             "--set", json.dumps({"stage": "doing", "goal": "g"}))
        assert code == 0, out
        current = fx.doc()["host_revision"]
        doc = fx.doc()
        doc["carrier"] = {"holder_instance_id": HOST["holder_instance_id"],
                          "platform": HOST["platform"], "session": HOST["session"]}
        doc["state"]["maintenance"] = {
            "handled_host_revision": current if handled_same else current - 1,
            "acked_host_revision": current if handled_same else current - 1}
        fx.write(doc)
        fx.write_record(NODE["platform"], NODE["session"],
                        fx.node_record(holder="node-1", features=["sideagent-relay/1"],
                                       socket=True))
        return fx

    def relay_once(self, fx: Fixture, node: dict) -> list:
        holder = fx.make_holder()
        sends = []
        holder._relay_send = lambda target, text: sends.append(text) or {"outcome": "in_progress"}
        holder._sweep_pass = lambda *a, **k: None  # no sweep thread in this test
        holder.turn["active"] = False
        holder.node.update(node)
        holder._node_relay_pass(fx.doc()["state"]["sideagent"])
        return sends

    def test_nothing_owed_sends_no_batch(self) -> None:
        fx = self.fixture(handled_same=True)
        view = fx.host_view()
        self.assertIsNone(next((row for row in view["attention"]
                                if row.get("kind") == "maintenance"), None))
        carrier = StrandedReturnedRange.carrier()
        self.assertIsNone(carrier._node_host_pending(fx.doc()))
        sends = self.relay_once(fx, {"holder": "node-1"})
        self.assertEqual(sends, [], "no batch when nothing is owed")

    def test_node_phase_or_sent_batch_sends_nothing(self) -> None:
        fx = self.fixture(handled_same=False)
        self.assertEqual(self.relay_once(fx, {"phase": "starting"}), [])
        self.assertEqual(self.relay_once(fx, {"phase": "stopping"}), [])
        self.assertEqual(self.relay_once(fx, {"phase": "running", "batch": "b-1",
                                              "holder": "node-1"}), [])

    def test_one_failure_is_recorded_once(self) -> None:
        fx = self.fixture(handled_same=False)
        holder = fx.make_holder()
        calls = {"tool": 0, "wake": 0}
        holder._maintenance_tool = lambda argv: calls.__setitem__("tool", calls["tool"] + 1) or {}
        holder._node_to_host = lambda *a, **k: calls.__setitem__("wake", calls["wake"] + 1)
        holder._kick_worker_events = lambda *a, **k: None
        holder._maintenance_failure("relay-unadmitted", 1)
        deadline = time.monotonic() + 10
        while calls["tool"] == 0 and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(calls, {"tool": 1, "wake": 1})
        holder._maintenance_failure("relay-unadmitted", 1)
        time.sleep(0.05)
        self.assertEqual(calls, {"tool": 1, "wake": 1},
                         "the same (input, why) failure is never recorded twice")


class Kw1116Shape(unittest.TestCase):
    """Item 4: the real kw1116 shape — one cancelled plus two accepted
    session-gone unknown items, item repos differing from the index repo."""

    ITEMS = [
        {"item_id": "kw1116-band-impl", "session": "dsh-KW-i1116-band",
         "platform": "dsh", "holder": "65ce409a8d8427036c696cc72cfda235",
         "disposition": "cancelled"},
        {"item_id": "kw1116-band-impl2", "session": "dsh-KW-i1116-band-2",
         "platform": "dsh", "holder": "e37e6e33a1450df38da9f4a75d705953",
         "disposition": "accepted"},
        {"item_id": "kw1116-review", "session": "devin-KW-i1116-review",
         "platform": "devin", "holder": "0c6c64f9c7640ae9637354a31bf83d9f",
         "disposition": "accepted"},
    ]
    ITEM_REPO = "/Users/ylpromax5/Workspace/Kaola-Workflow"  # differs from the fixture repo

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-kw1116-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def fixture(self, *, verdict: str = "accepted",
                drop_live: str | None = None) -> tuple:
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        fx = Fixture(root)
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "evt", "--kind", "tasks", "--id", "kw1116",
                             "--set", json.dumps({
                                 "stage": "done", "goal": "structural copy of kw1116",
                                 "evidence": "original close; do not rewrite cancelled to accepted",
                                 "verdict": {"value": verdict},
                                 "dispatch": [item["item_id"] for item in self.ITEMS],
                                 "dispositions": {item["item_id"]: item["disposition"]
                                                  for item in self.ITEMS}}))
        assert code == 0, out
        rev = str(fx.doc()["state"]["tasks"]["kw1116"]["rev"])
        index = root / "index.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(fx.repo), "items": [
                {"item_id": item["item_id"], "task_id": "kw1116", "status": "unknown",
                 "reason": "session-gone", "acceptance": "pending",
                 "session": item["session"], "platform": item["platform"],
                 "holder_instance_id": item["holder"], "repo": self.ITEM_REPO,
                 "evidence": {"collect_status": {"outcome": None, "mutation_status": None,
                                                "error_code": "no-session",
                                                "repo": str(fx.repo)}}}
                for item in self.ITEMS]}), encoding="utf-8")
        live = root / "live.json"
        live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": [
            {"session": item["session"], "platform": item["platform"], "state": "stopped",
             "holder_instance_id": item["holder"], "repo": str(fx.repo)}
            for item in self.ITEMS if item["item_id"] != drop_live]}), encoding="utf-8")
        return fx, rev, index, live

    def retire(self, fx: Fixture, rev: str, index: Path, live: Path,
               cite: bool = True) -> tuple[int, dict]:
        return fx.state("retire", "--file", str(fx.file), "--writer", "host",
                        "--source", "s", "--kind", "tasks", "--id", "kw1116",
                        "--expect-rev", rev, "--evidence", "original close",
                        *(["--cite", CITE] if cite else []),
                        "--index", str(index), "--live", str(live))

    def _check_command(self, fx: Fixture, index: Path, live: Path) -> str:
        code, out = fx.state("check", "--file", str(fx.file),
                             "--index", str(index), "--live", str(live))
        self.assertEqual(code, 0, out)
        commands = [row["command"] for row in out.get("problems") or []
                    if row.get("id") == "kw1116" and row.get("command")]
        self.assertTrue(commands, f"no runnable retire command: {out.get('problems')}")
        return commands[0]

    def _assert_retired(self, fx: Fixture, index: Path, index_before: bytes, out: dict) -> None:
        entries = {row["item_id"]: row["disposition"]
                   for row in out["value"]["reconciled_dispatch"]}
        self.assertEqual(entries, {"kw1116-band-impl": "cancelled",
                                 "kw1116-band-impl2": "accepted",
                                 "kw1116-review": "accepted"})
        self.assertEqual(index.read_bytes(), index_before, "no index bytes")
        self.assertNotIn("kw1116", fx.doc()["state"]["tasks"])
        self.assertFalse(fx.doc()["state"].get("retired"))
        view = fx.host_view()
        self.assertNotIn("kw1116", [row.get("id") for row in view["tasks"]])
        self.assertNotIn("kw1116", fx.doc().get("body") or "")

    def test_check_names_a_runnable_command_and_it_retires(self) -> None:
        for drop_live in (None, "kw1116-band-impl"):
            with self.subTest(drop_live=drop_live):
                fx, rev, index, live = self.fixture(drop_live=drop_live)
                index_before = index.read_bytes()
                command = self._check_command(fx, index, live)
                proc = subprocess.run(shlex.split(command), capture_output=True, text=True,
                                      timeout=60, env={k: v for k, v in os.environ.items()
                                                       if k not in CALLER_ENV})
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self._assert_retired(fx, index, index_before, json.loads(proc.stdout))

    def test_missing_cite_still_refuses(self) -> None:
        # Control: the accepted task cannot retire without --cite, before and
        # after the fix (baseline refuses earlier on the cancelled item).
        fx, rev, index, live = self.fixture()
        before = fx.file.read_bytes()
        code, out = self.retire(fx, rev, index, live, cite=False)
        self.assertEqual(code, 2, out)
        self.assertEqual(fx.file.read_bytes(), before)
        self.assertIn("kw1116", fx.doc()["state"]["tasks"])

    def test_missing_cite_names_cite_required_once_dispatch_closes(self) -> None:
        fx, rev, index, live = self.fixture()
        code, out = self.retire(fx, rev, index, live, cite=False)
        self.assertEqual((code, out.get("reason")), (2, "cite-required"), out)
        self.assertIn("kw1116", fx.doc()["state"]["tasks"])

    def test_cancelled_verdict_session_gone_stays_refused(self) -> None:
        # Control, unchanged and out of scope: the dead-holder route requires
        # accepted-done; a cancelled verdict does not settle unknown rows.
        fx, rev, index, live = self.fixture(verdict="cancelled")
        before = fx.file.read_bytes()
        code, out = self.retire(fx, rev, index, live)
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("is unknown", out["detail"])
        self.assertEqual(fx.file.read_bytes(), before)
        self.assertIn("kw1116", fx.doc()["state"]["tasks"])


class CancelledDispositionRetire(unittest.TestCase):
    """E3: a cancelled per-item disposition retires as cancelled."""

    ITEM_A = "kw412-a"
    ITEM_B = "kw412-b"
    SESS_A = "zcode-KT-i412-a"
    SESS_B = "zcode-KT-i412-b"
    HOLDER_A = "holder-412-a"
    HOLDER_B = "holder-412-b"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i412-retire-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def fixture(self, *, dispositions: dict | None = None, task: dict | None = None,
                live_rows: list | None = None, reason: str = "session-gone") -> tuple:
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        fx = Fixture(root)
        patch = {"stage": "done", "goal": "g", "verdict": {"value": "accepted"},
                 "dispatch": [self.ITEM_A, self.ITEM_B]}
        if dispositions is not None:
            patch["dispositions"] = dispositions
        if task:
            patch.update(task)
        code, out = fx.state("update", "--file", str(fx.file), "--writer", "host",
                             "--source", "evt", "--kind", "tasks", "--id", "t1",
                             "--set", json.dumps(patch))
        assert code == 0, out
        rev = str(fx.doc()["state"]["tasks"]["t1"]["rev"])
        index = root / "index.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(fx.repo), "items": [
                {"item_id": self.ITEM_A, "task_id": "t1", "status": "unknown",
                 "reason": reason, "session": self.SESS_A,
                 "holder_instance_id": self.HOLDER_A, "platform": "zcode",
                 "repo": str(fx.repo)},
                {"item_id": self.ITEM_B, "task_id": "t1", "status": "unknown",
                 "reason": reason, "session": self.SESS_B,
                 "holder_instance_id": self.HOLDER_B, "platform": "zcode",
                 "repo": str(fx.repo)}]}), encoding="utf-8")
        live = root / "live.json"
        live.write_text(json.dumps({"schema": "kaola-acp-list/1",
                                    "rows": live_rows or []}), encoding="utf-8")
        return fx, rev, index, live

    def retire(self, fx: Fixture, rev: str, index: Path, live: Path) -> tuple[int, dict]:
        return fx.state("retire", "--file", str(fx.file), "--writer", "host",
                        "--source", "s", "--kind", "tasks", "--id", "t1",
                        "--expect-rev", rev, "--evidence", "original close-out evidence",
                        "--cite", CITE, "--index", str(index), "--live", str(live))

    def test_cancelled_and_accepted_items_retire_as_their_dispositions(self) -> None:
        fx, rev, index, live = self.fixture(dispositions={self.ITEM_A: "cancelled",
                                                        self.ITEM_B: "accepted"})
        before_index = index.read_bytes()
        code, out = self.retire(fx, rev, index, live)
        self.assertEqual(code, 0, out)
        entries = {row["item_id"]: row for row in out["value"]["reconciled_dispatch"]}
        self.assertEqual(entries[self.ITEM_A]["disposition"], "cancelled")
        self.assertEqual(entries[self.ITEM_B]["disposition"], "accepted")
        self.assertEqual(index.read_bytes(), before_index, "no index bytes")
        self.assertNotIn("t1", fx.doc()["state"]["tasks"])
        self.assertFalse(fx.doc()["state"].get("retired"))
        view = fx.host_view()
        self.assertNotIn("t1", [row.get("id") for row in view["tasks"]])
        self.assertNotIn("t1", fx.doc().get("body") or "")

    def _refuse(self, fragment: str, **kwargs) -> dict:
        fx, rev, index, live = self.fixture(**kwargs)
        before_state = fx.file.read_bytes()
        before_index = index.read_bytes()
        code, out = self.retire(fx, rev, index, live)
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn(fragment, out["detail"], out)
        self.assertEqual(fx.file.read_bytes(), before_state)
        self.assertEqual(index.read_bytes(), before_index)
        self.assertIn("t1", fx.doc()["state"]["tasks"])
        return out

    def test_a_cancelled_item_whose_session_is_live_refuses(self) -> None:
        out = self._refuse("live session",
                           dispositions={self.ITEM_A: "cancelled", self.ITEM_B: "accepted"},
                           live_rows=[{"session": self.SESS_A, "state": "ready",
                                       "holder_instance_id": self.HOLDER_A}])
        self.assertIn(ROUTE, out["detail"])

    def test_a_superseded_item_refuses(self) -> None:
        out = self._refuse("not accepted",
                           dispositions={self.ITEM_A: "superseded", self.ITEM_B: "accepted"})
        self.assertIn(ROUTE, out["detail"])

    def test_a_not_accepted_done_task_refuses(self) -> None:
        self._refuse("accepted it done or cancelled",
                     dispositions={self.ITEM_A: "cancelled", self.ITEM_B: "accepted"},
                     task={"verdict": {"value": "repair"}})

    def test_a_foreign_holder_for_the_cancelled_row_refuses(self) -> None:
        out = self._refuse("foreign holder",
                           dispositions={self.ITEM_A: "cancelled", self.ITEM_B: "accepted"},
                           live_rows=[{"session": self.SESS_A, "state": "stopped",
                                       "holder_instance_id": "holder-foreign"},
                                      {"session": self.SESS_B, "state": "stopped",
                                       "holder_instance_id": self.HOLDER_B}])
        self.assertIn(ROUTE, out["detail"])


if __name__ == "__main__":
    unittest.main()
