#!/usr/bin/env python3
"""Issue #336: a node whose admitted turn its runtime refuses moves on.

A Sideagent node that starts and admits its batch, but whose turn the runtime
then refuses, is an unavailable runtime like a failed start (#324). ZCode's
5-hour limit and provider rejections arrive as a completed turn with
``stopReason: refusal`` (``[zcode turn failed] ...``) and no checkpoint; a
JSON-RPC error on the prompt is ``turn_failed``. Before the fix every such
turn end was "checkpoint missing": it woke the Host (one Host turn each), the
chain never advanced, and the next Host write started the same runtime again
(the KT Host log on 2026-10-16: two refusals at 16:06 and 16:12, both
``host_woken``, no ``sideagent_node_fallback``; vrpai on the Studio: 20).

1. The refused node is exact-stopped under the runtime it ran on, the carrier
   moves to the next eligible Worker runtime, the failed range stays
   selectable for it, and the move wakes no Host turn.
2. An exhausted chain fails once: the Host is told once, later Host writes
   start no node until the binding or recipe changes.
3. A completed turn that merely wrote no checkpoint is the Host's as before:
   no fallback, and the next Host write starts the bound runtime again.
4. The node's turn end names its stop reason; a Host holder also reads it
   from the ``outcome=... stop_reason=...`` reason text.
5. A node start carries the carrier's own record root, so the Runner resolves
   the node's record directory without the all-roots ``ps`` enumeration; that
   enumeration refused a fresh dsh node with ``record-root-mismatch`` whenever
   ``ps`` failed or exceeded its 3 s (deterministic with a failing ``ps`` shim;
   the Delegator's measurement of 2026-10-16). An explicit root resolves
   under a failing ``ps``; the root-less start keeps its refusal.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ISSUE324 = REPO / "tests" / "contract" / "test-issue-324-wake-fixes.py"
ACP_PATHS = REPO / "scripts" / "kaola-acp-paths.py"

spec = importlib.util.spec_from_file_location("issue324_refusal_336", ISSUE324)
issue324 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue324)
issue255 = issue324.issue255
holder_module = issue255.holder_module

paths_spec = importlib.util.spec_from_file_location("acp_paths_336", ACP_PATHS)
acp_paths = importlib.util.module_from_spec(paths_spec)
assert paths_spec.loader is not None
paths_spec.loader.exec_module(acp_paths)

WORKERS_OFF = ["codex/luna", "devin/default", "opencode/default"]
ALL_OFF = ["codex/luna", "devin/default", "dsh/default", "opencode/default"]

# The fake node runner, also noting the record root its start was given.
ROOT_NOTING_RUNNER = issue255.FAKE_NODE_RUNNER.replace(
    'Path(os.environ["FAKE_NODE_ARGV"]).write_text(json.dumps(sys.argv[1:]))',
    'Path(os.environ["FAKE_NODE_ARGV"]).write_text(json.dumps(sys.argv[1:]))\n'
    'Path(os.environ["FAKE_NODE_ARGV"] + ".root").write_text(os.environ.get("KAOLA_ACP_RECORD_ROOT", ""))')
assert ROOT_NOTING_RUNNER != issue255.FAKE_NODE_RUNNER

# A runner that spawns the node (live record, this carrier as dispatcher) and
# then exits non-zero: the Runner's own failure after the holder came up.
LIVE_THEN_FAIL_RUNNER = issue255.FAKE_NODE_RUNNER.replace(
    'print(json.dumps({"holder_instance_id": holder, "session": "zcode-KT-sideagent"}))',
    'print(json.dumps({"error": {"code": "node-start-error", "message": "runner exited after the spawn"}}))\n'
    'sys.exit(1)')
assert LIVE_THEN_FAIL_RUNNER != issue255.FAKE_NODE_RUNNER

# The same, but the holder is still starting when the Runner gives up (the
# record says ``starting``); it writes where FAKE_NODE_RECORD_DSH points when set.
STARTING_THEN_FAIL_RUNNER = LIVE_THEN_FAIL_RUNNER.replace(
    '"state": "ready"', '"state": "starting"').replace(
    'Path(os.environ["FAKE_NODE_RECORD"]).write_text(',
    'Path(os.environ.get("FAKE_NODE_RECORD_DSH") or os.environ["FAKE_NODE_RECORD"]).write_text(')
assert STARTING_THEN_FAIL_RUNNER.count('"starting"') == 1


class NodeTurnRefusal(issue324.NodeRuntimeFallback):
    """The runtime refused the admitted node turn (Issue #336)."""

    def setUp(self) -> None:
        super().setUp()
        self.saved_adopt = holder_module.NODE_ADOPT_READY_SECONDS
        holder_module.NODE_ADOPT_READY_SECONDS = 6.0

    def tearDown(self) -> None:
        holder_module.NODE_ADOPT_READY_SECONDS = self.saved_adopt
        os.environ.pop("FAKE_NODE_RECORD_DSH", None)
        super().tearDown()

    def node_dir(self, platform: str) -> Path:
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        return self.records / platform / self.SESSION / digest

    def fake_at(self, platform: str) -> issue255.FakeNode:
        """A second fake node holder for ``platform``, beside ``self.fake``."""
        directory = self.node_dir(platform)
        directory.mkdir(parents=True, exist_ok=True)
        sock = Path("/tmp") / f"kaola-{os.getuid()}-acp" / (
            hashlib.sha256(str(directory).encode()).hexdigest()[:24] + ".sock")
        fake = issue255.FakeNode(sock, directory / "record.json")
        self.addCleanup(fake.close)
        return fake

    def partial_checkpoint(self, through: int) -> None:
        """The running node's own checkpoint for its batch, short of the range."""
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = json.loads(path.read_text())
        doc["state"]["maintenance"]["last_checkpoint"] = {
            "batch": self.holder.node["batch"], "node": {"holder_instance_id": self.holder.node["holder"]},
            "host_revision": {"from": 0, "through": through, "current": doc.get("host_revision")},
            "verified": True}
        path.write_text(json.dumps(doc))

    def end_node_turn(self, platform: str, outcome: str = "turn_completed", stop: str | None = None,
                      explicit: bool = True, reason: str | None = None, cursor: int = 90) -> dict:
        """The node holder's own turn end for the batch it carries."""
        node = self.holder.node
        params = {"kind": "idle", "platform": platform, "session": self.SESSION, "repo": str(self.repo),
                  "reason": f"outcome={outcome} stop_reason={stop}" if reason is None else reason,
                  "event_cursor": cursor, "holder_instance_id": node["holder"],
                  "turn_fingerprint": node["fingerprint"], "turn_outcome": outcome}
        if explicit and stop:
            params["turn_stop_reason"] = stop
        return self.holder.op_worker_event(params)

    def staged_nodes(self) -> list[dict]:
        return [row for row in self.holder.pending_worker_events if row.get("kind") == "node"]

    def first_batch(self, exclusions: list[str]) -> None:
        self.prepare_recovery_host()
        self.install("zcode", issue255.FAKE_NODE_RUNNER)
        self.install("dsh", issue255.FAKE_NODE_RUNNER)
        self.serve("zcode")
        self.bind("zcode", exclusions)
        self.drive(lambda: len(self.fake.prompts) == 1, "the bound runtime's batch")
        self.assertIn("host revision 1..4", self.fake.prompts[0]["params"]["text"])

    def moves_to_dsh(self, **turn_end) -> None:
        self.first_batch(WORKERS_OFF)
        # The next runtime's node holder is ready before the refusal; the
        # refused node keeps its socket to answer its exact stop.
        zcode = self.fake
        self.addCleanup(zcode.close)
        self.fake = None
        self.serve("dsh")
        self.end_node_turn("zcode", **turn_end)
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the refused node stopped")
        self.assertEqual(len(zcode.stops), 1, "the refused node is exact-stopped under its own runtime")
        moves = self.events_of("sideagent_node_fallback")
        self.assertEqual([(m["from"], m.get("to")) for m in moves], [("zcode", "dsh/default")])
        self.assertTrue(moves[0]["reason"].startswith("turn-refused:"), moves[0]["reason"])
        settled = self.events_of("sideagent_node_settled")
        self.assertEqual((settled[-1]["checkpoint"], settled[-1]["host_woken"], settled[-1].get("runtime_moved")),
                         ("missing", False, "dsh/default"))
        self.drive(lambda: len(self.fake.prompts) == 1, "the same range on the next runtime")
        self.assertIn("host revision 1..4", self.fake.prompts[0]["params"]["text"])
        self.assertEqual(json.loads((Path(self.tmp.name) / "argv").read_text())[-2:], ["--tier", "default"])
        self.assertEqual(self.node_count(), 2)
        self.assertEqual(self.holder.node["sent_through"], 4)
        time.sleep(0.3)
        self.assertEqual(self.staged_nodes(), [], "a move to the next runtime starts no Host turn")
        self.assertEqual(self.agent.prompts(), [])
        self.assertEqual(self.events_of("sideagent_maintenance_failure_recorded"), [],
                         "the range is not returned; the next runtime takes it")
        self.holder._reclaim_node()

    def test_refused_turn_moves_to_the_next_runtime_and_keeps_the_range(self) -> None:
        # ZCode: `[zcode turn failed] [1308][已达到 5 小时的使用上限 ...]` → stopReason refusal.
        self.moves_to_dsh(stop="refusal", reason="idle")  # the explicit field alone carries it

    def test_failed_turn_moves_too(self) -> None:
        self.moves_to_dsh(outcome="turn_failed")

    def test_refusal_in_the_reason_text_is_read_without_the_field(self) -> None:
        self.moves_to_dsh(stop="refusal", explicit=False)

    def test_refused_turn_with_an_exhausted_chain_fails_once(self) -> None:
        self.first_batch(ALL_OFF)
        batch = self.holder.node["batch"]
        self.end_node_turn("zcode", stop="refusal")
        self.wait_for(lambda: len(self.agent.prompts()) == 1, "the Host told once")
        self.assertIn("no eligible fallback runtime", self.agent.prompts()[0])
        self.assertIn("turn refused (refusal)", self.agent.prompts()[0])
        moves = self.events_of("sideagent_node_fallback")
        self.assertEqual([(m["from"], m.get("to"), m.get("exhausted")) for m in moves], [("zcode", None, True)])
        self.wait_for(lambda: [row["input"] for row in self.events_of("sideagent_maintenance_failure_recorded")]
                      == [f"batch:{batch}"], "the one recorded failure")
        self.assertEqual(self.events_of("sideagent_maintenance_failure_recorded")[0]["reason"],
                         "checkpoint-missing")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the refused node stopped")
        self.assertEqual(len(self.fake.stops), 1)
        self.assertEqual(self.holder.node.get("failed", {}).get("code"), "turn-refused:refusal")
        self.finish_host_turn()
        for revision in (5, 6, 7):
            self.bind("zcode", ALL_OFF, revision)
            self.holder.turn["active"] = False
            self.boundary()
        time.sleep(0.5)
        self.assertEqual(self.node_count(), 1, "no node starts until the binding or recipe changes")
        self.assertEqual(len(self.agent.prompts()), 1, "no Host turn per later write")
        self.assertEqual(len(self.events_of("sideagent_node_fallback")), 1)
        # The Host repairs the binding (a new session name): the bound runtime
        # is tried first again and takes the later range.
        self.SESSION = "KT-maintenance-node-2"
        self.serve("zcode")
        self.bind("zcode", ALL_OFF, 8)
        self.drive(lambda: len(self.fake.prompts) == 1, "the repaired binding's batch")
        self.assertEqual(self.node_count(), 2)
        self.holder._reclaim_node()

    def test_completed_turn_without_a_checkpoint_stays_with_the_host(self) -> None:
        self.first_batch(WORKERS_OFF)
        self.end_node_turn("zcode", stop="end_turn")
        self.wait_for(lambda: len(self.agent.prompts()) == 1, "the Host is woken as before")
        self.assertIn("checkpoint missing", self.agent.prompts()[0])
        self.assertNotIn("turn refused", self.agent.prompts()[0])
        self.assertEqual(self.events_of("sideagent_node_fallback"), [], "a turn the node ran is not a runtime failure")
        self.assertIsNone(self.holder.node.get("failed"))
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stopped")
        self.finish_host_turn()
        self.bind("zcode", WORKERS_OFF, 5)
        self.drive(lambda: len(self.fake.prompts) == 2, "the next Host write starts the bound runtime again")
        self.assertEqual(self.node_count(), 2)
        # A batch runs from the handled checkpoint: the unhandled range is in it.
        self.assertIn("host revision 1..5", self.fake.prompts[1]["params"]["text"])
        self.holder._reclaim_node()

    def test_a_sideagent_turn_end_names_its_stop_reason(self) -> None:
        args = argparse.Namespace(record_dir=str(self.side_dir), socket=str(self.side_dir / "s.sock"),
                                  platform="zcode", session="zcode-KT-sideagent", repo=str(self.repo),
                                  init_meta="", command="stub")
        side = holder_module.Holder(args)
        side.agent = issue255.StubAgent()
        side.session_role = "sideagent"
        side.heartbeat_host = {"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                               "socket": str(self.side_dir / "host.sock")}
        sent: list[dict] = []
        side._carrier_send = lambda target, params, still_owed=None: sent.append(params) or {"staged": True}
        side.turn.update({"active": True, "request_id": 7, "fingerprint": "sha256:turn-7",
                          "written_at": "now", "mutation_status": "running", "stop_reason": None})
        side.on_prompt_response(7, {"result": {"stopReason": "refusal"}})
        self.assertEqual((sent[0]["turn_outcome"], sent[0]["turn_stop_reason"], sent[0]["reason"]),
                         ("turn_completed", "refusal", "outcome=turn_completed stop_reason=refusal"))
        side.turn.update({"active": True, "request_id": 8, "fingerprint": "sha256:turn-8", "stop_reason": None})
        side.on_prompt_response(8, {"error": {"code": -32000, "message": "backend rejected the prompt"}})
        self.assertEqual((sent[1]["turn_outcome"], "turn_stop_reason" in sent[1]), ("turn_failed", False))

    def test_a_node_start_carries_the_carriers_record_root(self) -> None:
        self.prepare_recovery_host()
        self.install("zcode", ROOT_NOTING_RUNNER)
        self.serve("zcode")
        self.bind("zcode", WORKERS_OFF)
        self.drive(lambda: len(self.fake.prompts) == 1, "the node's batch")
        given = Path(str(Path(self.tmp.name) / "argv") + ".root").read_text()
        self.assertEqual(given, str(Path(self.holder.args.record_dir).parent.parent.parent),
                         "the Runner start resolves the node under this carrier's own root")
        self.holder._reclaim_node()

    def test_a_failed_turn_with_a_partial_checkpoint_stays_with_the_host(self) -> None:
        self.first_batch(WORKERS_OFF)
        self.partial_checkpoint(2)
        self.end_node_turn("zcode", outcome="turn_failed")
        self.wait_for(lambda: len(self.agent.prompts()) == 1, "the Host is woken as before")
        self.assertIn("checkpoint partial: host revision 3..4 not handled", self.agent.prompts()[0])
        self.assertEqual(self.events_of("sideagent_node_fallback"), [], "a node that ran is not a runtime failure")
        self.assertIsNone(self.holder.node.get("failed"))
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stopped")
        self.holder._reclaim_node()

    def test_an_unconfirmed_stop_after_a_move_is_checked_under_the_old_runtime(self) -> None:
        self.first_batch(WORKERS_OFF)
        zcode = self.fake
        self.addCleanup(zcode.close)
        zcode.ignore_stop = True  # a wedged node: the stop is answered but not applied
        self.fake = None
        self.serve("dsh")
        self.end_node_turn("zcode", stop="refusal")
        self.wait_for(lambda: "sideagent_node_stop_unconfirmed" in self.log_kinds(), "the stop stays unconfirmed")
        self.assertEqual([(m["from"], m.get("to")) for m in self.events_of("sideagent_node_fallback")],
                         [("zcode", "dsh/default")])
        self.wait_for(lambda: ("batch:4", "stop-unconfirmed") in
                      [(row["input"], row["reason"]) for row in self.events_of("sideagent_maintenance_failure_recorded")],
                      "the unconfirmed stop names the batch's own range")
        for _ in range(4):
            self.holder.turn["active"] = False
            self.boundary()
            time.sleep(0.2)
        self.assertEqual(self.node_count(), 1, "no next-runtime start while the refused node may still run")
        self.assertEqual(self.events_of("sideagent_node_stop_confirmed_late"), [])
        self.assertEqual(self.holder.node["stop_unconfirmed"]["platform"], "zcode")
        # The unconfirmed stop woke the Host once (a wedged node is its to see);
        # the recorded failure gates the range until the Host writes again.
        self.wait_for(lambda: len(self.agent.prompts()) == 1, "the Host told once")
        self.finish_host_turn()
        # The wedged node finally dies: the late confirmation is read under its
        # own runtime, and the next Host change resumes on the fallback runtime
        # with the whole unhandled range.
        record = json.loads(zcode.record.read_text())
        record.update(state="stopped", holder_pid=zcode.dead_pid)
        zcode.record.write_text(json.dumps(record))
        self.holder.turn["active"] = False
        self.boundary()
        self.assertEqual(len(self.events_of("sideagent_node_stop_confirmed_late")), 1)
        self.bind("zcode", WORKERS_OFF, 5)
        self.drive(lambda: len(self.fake.prompts) == 1, "the next runtime takes the range on the next Host write")
        self.assertIn("host revision 1..5", self.fake.prompts[0]["params"]["text"])
        self.assertEqual(self.node_count(), 2)
        self.holder._reclaim_node()

    def test_a_starting_holder_is_adopted_once_ready(self) -> None:
        self.prepare_recovery_host()
        self.install("dsh", STARTING_THEN_FAIL_RUNNER)
        self.install("zcode", issue255.FAKE_NODE_RUNNER)
        self.serve("dsh")
        record = self.node_dir("dsh") / "record.json"

        def finish_starting() -> None:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not record.exists():
                time.sleep(0.05)
            time.sleep(1.2)
            doc = json.loads(record.read_text())
            doc["state"] = "ready"
            record.write_text(json.dumps(doc))
        threading.Thread(target=finish_starting, daemon=True).start()
        self.bind("dsh", WORKERS_OFF)
        self.drive(lambda: len(self.fake.prompts) == 1, "the batch on the holder that finished starting")
        self.assertEqual([row["session"] for row in self.events_of("sideagent_node_adopted")], [self.SESSION])
        self.assertEqual(self.events_of("sideagent_node_fallback"), [])
        self.assertEqual(self.node_count(), 1)
        self.holder._reclaim_node()

    def test_a_holder_that_never_becomes_ready_is_stopped_before_the_chain(self) -> None:
        holder_module.NODE_ADOPT_READY_SECONDS = 1.0
        self.prepare_recovery_host()
        self.install("dsh", STARTING_THEN_FAIL_RUNNER)
        self.install("zcode", issue255.FAKE_NODE_RUNNER)
        dsh = self.fake_at("dsh")
        os.environ["FAKE_NODE_RECORD_DSH"] = str(dsh.record)
        self.serve("zcode")
        self.bind("dsh", WORKERS_OFF)
        self.drive(lambda: len(self.fake.prompts) == 1, "the batch on the next runtime")
        self.assertEqual(len(dsh.stops), 1, "the never-ready holder was exact-stopped under its own runtime")
        kinds = self.log_kinds()
        self.assertLess(kinds.index("sideagent_node_stopped"), kinds.index("sideagent_node_fallback"))
        self.assertEqual([(m["from"], m.get("to")) for m in self.events_of("sideagent_node_fallback")],
                         [("dsh", "zcode/default")])
        self.assertEqual(self.events_of("sideagent_node_adopted"), [])
        self.assertEqual(self.node_count(), 2)
        self.holder._reclaim_node()

    def test_a_failed_start_whose_holder_is_live_is_adopted_not_twinned(self) -> None:
        # vrpai's "zcode twin beside the proper DSH sideagent": the dsh Runner
        # reported a failed start although the holder it spawned was live.
        self.prepare_recovery_host()
        self.install("dsh", LIVE_THEN_FAIL_RUNNER)
        self.install("zcode", issue255.FAKE_NODE_RUNNER)
        self.serve("dsh")
        self.bind("dsh", WORKERS_OFF)
        self.drive(lambda: len(self.fake.prompts) == 1, "the batch on the live dsh holder")
        self.assertEqual([row["session"] for row in self.events_of("sideagent_node_adopted")], [self.SESSION])
        self.assertEqual(self.events_of("sideagent_node_fallback"), [], "no twin on another runtime")
        self.assertEqual(self.events_of("sideagent_node_start_failed"), [])
        self.assertEqual(self.node_count(), 1, "the zcode Runner never ran")
        self.assertEqual(json.loads((Path(self.tmp.name) / "argv").read_text())[0], "start")
        self.holder._reclaim_node()


for _name in dir(issue324.NodeRuntimeFallback):
    if _name.startswith("test_") and _name not in NodeTurnRefusal.__dict__:
        setattr(NodeTurnRefusal, _name, None)


class RecordRootEnumeration(unittest.TestCase):
    """An explicit record root resolves without the ``ps`` enumeration."""

    def test_explicit_root_resolves_under_a_failing_ps(self) -> None:
        session = f"dsh-KPR-shim-{os.getpid()}"
        saved = {key: os.environ.get(key) for key in ("PATH", "KAOLA_ACP_RECORD_ROOT")}
        with tempfile.TemporaryDirectory() as tmp:
            shim = Path(tmp) / "bin"
            shim.mkdir()
            (shim / "ps").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            (shim / "ps").chmod(0o755)
            root = Path(tmp) / "root"
            root.mkdir(mode=0o700)
            os.environ["PATH"] = f"{shim}:{saved['PATH'] or ''}"
            os.environ.pop("KAOLA_ACP_RECORD_ROOT", None)
            try:
                self.assertFalse(acp_paths.roots(None)[1], "the shim leaves the enumeration incomplete")
                with self.assertRaises(acp_paths.RecordRootMismatch):
                    acp_paths.find_directory("dsh", session, "/repo", None)
                found = acp_paths.find_directory("dsh", session, "/repo", str(root))
                self.assertEqual(found.parent.parent.parent, root, "an explicit root runs no ps")
                os.environ["KAOLA_ACP_RECORD_ROOT"] = str(root)
                found = acp_paths.find_directory("dsh", session, "/repo", None)
                self.assertEqual(found.parent.parent.parent, root, "the carrier's env root too")
            finally:
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
