#!/usr/bin/env python3
"""Issue #324: no nothing-to-do wake, and no endless maintenance failures.

1. A standing Host-owned attention row (a ``holds`` row owned by the host, the
   Host alert ``maintenance-returned``, a ``maintenance`` or ``sideagent`` duty)
   is not a Delegator decision. A compaction-reload turn that ends next to a
   Sideagent node settle, with ``state.decisions`` empty, wakes nothing.
2. ``binding-or-recipe-unavailable``: a Host with no node binding owes no node
   batch, so its business writes record no failure and stage no Host turn. A
   node binding whose recipe is unusable fails once; later Host writes do not
   mint a new failure each, and a repaired binding picks the later range up.
3. A bound node whose runtime fails moves through granted Worker presets
   sorted by id, never retrying a runtime and never using an excluded or
   ungranted preset; an exhausted chain fails once, with no retry.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ISSUE302 = REPO / "tests" / "contract" / "test-issue-302-delegator-wake-gate.py"
ISSUE315 = REPO / "tests" / "contract" / "test-issue-315-decision-wake.py"
ISSUE255 = REPO / "tests" / "contract" / "test-issue-255-lifecycle-state.py"

spec = importlib.util.spec_from_file_location("issue302_wake_324", ISSUE302)
issue302 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue302)

spec315 = importlib.util.spec_from_file_location("issue315_wake_324", ISSUE315)
issue315 = importlib.util.module_from_spec(spec315)
assert spec315.loader is not None
spec315.loader.exec_module(issue315)

spec255 = importlib.util.spec_from_file_location("issue255_node_324", ISSUE255)
issue255 = importlib.util.module_from_spec(spec255)
assert spec255.loader is not None
spec255.loader.exec_module(issue255)

holder = issue302.holder
wait_for = issue302.wait_for

# The rows the KPM Host's heartbeat view carried at the filing (read-only copy
# of its current `.kaola/heartbeat-prompt.json` host view): a standing
# Host-owned hold and the Host's non-severe `maintenance-returned` alert.
STANDING_ROWS = [
    {"kind": "holds", "id": "migration-impl", "why": "host-owned", "content": "76bcd08d2f76159e"},
    {"kind": "alerts", "id": "maintenance-returned", "why": "warn", "content": "133de3b6e3f230c9"},
]
MAINTENANCE_ROWS = [
    {"kind": "maintenance", "id": "pending", "why": "bounded reconciliation owed"},
    {"kind": "sideagent", "id": "node6", "why": "failed"},
    {"kind": "decisions", "id": "d1", "why": "transcribed-check"},
    {"kind": "tasks", "id": "t1", "why": "transcribed-check"},
]


class Classifier(unittest.TestCase):
    def test_needs_decision_needs_a_decision_cause(self) -> None:
        classify = holder.classify_delegator_attention
        self.assertIsNone(classify(STANDING_ROWS))
        self.assertIsNone(classify(MAINTENANCE_ROWS))
        self.assertIsNone(classify([{"kind": "future-kind", "why": "unknown"}]))
        self.assertIsNone(classify([{"kind": "alerts", "why": "warn", "owner": "host"}]))
        self.assertEqual(classify([{"kind": "decisions", "id": "x", "why": "registered-decision"}]),
                         "needs_decision")
        self.assertEqual(classify([{"kind": "alerts", "id": "a", "why": "severe"}]),
                         "needs_decision")
        # A real cause still wins when a standing row sits beside it.
        self.assertEqual(classify(STANDING_ROWS + [{"kind": "alerts", "why": "severe"}]),
                         "needs_decision")
        self.assertEqual(classify(STANDING_ROWS + [{"kind": "decisions", "why": "host-decision"}]),
                         "question_waiting")
        self.assertEqual(classify(STANDING_ROWS + [{"kind": "tasks", "why": "awaiting-verdict"}]),
                         "delivery_review")

    def test_predicate_standing_rows_are_silent(self) -> None:
        base = dict(outcome="turn_completed", stop_reason="end_turn", prompt_source="self",
                    self_continuing=False, stop_requested=False, staged_undelivered=False,
                    attention_rows=STANDING_ROWS)
        # A seat still works: the compaction-reload self turn ends quietly.
        self.assertIsNone(holder.delegator_turn_wake_reason(live_seats=True, **base))
        # No seat works: the standing rows do not outrank the all-idle fallback.
        self.assertEqual(holder.delegator_turn_wake_reason(live_seats=False, **base), "all-idle")
        # A length stop with a standing row is still host_stopped_pending.
        self.assertEqual(holder.delegator_turn_wake_reason(
            live_seats=True, **{**base, "stop_reason": "max_tokens"}), "host_stopped_pending")


class Wakes(issue315.DecisionWake):
    """Reuses the #315 in-process Host harness without collecting its tests."""

    test_registered_pending_decision_wakes_needs_decision = None
    test_silent_turn_falls_back_to_all_idle_once = None
    test_compact_reload_registered_decision_still_wakes = None
    test_active_seat_keeps_current_behavior = None

    def write_view(self, extra_state: dict | None = None,
                   decisions: dict | None = None) -> Path:
        """Real lifecycle state; the record contract projects the Host view.

        Standing state: a Host-owned hold and the Host's non-severe
        ``maintenance-returned`` alert, the two attention rows the KPM Host
        carried at the filing. ``extra_state`` adds Host maintenance duties.
        """
        path = self.write_state(decisions or {}, checkpoint=True)
        doc = json.loads(path.read_text(encoding="utf-8"))
        state = doc["state"]
        state["holds"] = {"migration-impl": {
            "owner": "host", "scope": "external publish", "reason": "standing", "rev": 8}}
        state["alerts"] = {"maintenance-returned": {
            "level": "warn", "owner": "host", "summary": "node returned", "rev": 3}}
        state.update(extra_state or {})
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def attention_rows(self, host) -> list:
        _staged, rows, decisions = host._delegator_pending_facts()
        return [*(rows or []), *decisions]

    def end_turn(self, host, source: str):
        """Production turn-end branch for an ended turn."""
        ended = host._empty_turn()
        ended.update(outcome="turn_completed", stop_reason="end_turn", prompt_source=source)
        host._delegator_followups = 0
        host.turn = host._empty_turn()
        reason = host._delegator_turn_end_reason(ended)
        host._finish_delegator_turn_wake(ended, reason)
        return reason

    def test_reload_turn_with_node_settle_and_empty_decisions_does_not_wake(self) -> None:
        # The filing: a seat works, state.decisions is {}, the reload self turn
        # ends beside a Sideagent node settle. Standing Host rows whose digest
        # moved are undelivered attention, and the old catch-all called that
        # needs_decision. Case 1 and case 2 of the filing, both orders.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("reload-settle")
            host.events.append({"kind": "compact_reload_delivered", "session_role": "host"})
            self.write_view()
            rows = self.attention_rows(host)
            self.assertEqual([(r["kind"], r["id"], r["why"]) for r in rows],
                             [("holds", "migration-impl", "host-owned"),
                              ("alerts", "maintenance-returned", "warn")], rows)
            try:
                proc, _dir = self.spawn_seat(
                    "grok-i324-working", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "in_progress"})
                wait_for(lambda: holder.holders_dispatched_by(
                    host.holder_instance_id, working=True) or None, 5, "working seat visible")
                host.events.append({"kind": "sideagent_node_settled", "checkpoint": "verified",
                                    "host_woken": False})
                self.assertIsNone(self.end_turn(host, "self"))
                # The node settle moves the Host's maintenance duties and the
                # row digests; the attention list changes again.
                self.write_view({
                    "maintenance": {"recovery_input": {"seq": 1, "kind": "host-compaction"}},
                    "sideagent": {"mode": "node", "platform": "grok", "session": "n",
                                  "state": "failed"}})
                self.assertGreater(len(self.attention_rows(host)), 2)
                self.assertIsNone(self.end_turn(host, "self"))
                time.sleep(0.4)
                self.assertEqual(self.endpoint.posts, [])
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_registered_decision_still_wakes_beside_standing_rows(self) -> None:
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("decision-kept")
            self.write_view()
            try:
                proc, _dir = self.spawn_seat(
                    "grok-i324-decision", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "in_progress"})
                wait_for(lambda: holder.holders_dispatched_by(
                    host.holder_instance_id, working=True) or None, 5, "working seat visible")
                # A working seat keeps the #315 rule: the registered row is not merged.
                self.assertIsNone(self.end_turn(host, "self"))
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)
            # No seat works: the registered row is a true decision cause.
            self.write_view(decisions={"waves": issue315.decision("delegator")})
            self.assertEqual(self.end_turn(host, "self"), "needs_decision")
            wait_for(lambda: self.posts_for(host.holder_instance_id, "needs_decision") or None,
                     15, "needs_decision for the registered row")


class CarrierFailure(issue255.HolderNodeMode):
    """``binding-or-recipe-unavailable`` from the Host carrier (Issue #324).

    The KPR Host's state had ``sideagent`` null; every Host business write
    (host revisions 83 to 156) minted a new ``batch:<rev>`` failure, a new
    ``maintenance-returned`` input and a staged ``node`` item that started the
    next Host turn.
    """

    def doc(self) -> dict:
        return json.loads((self.repo / ".kaola" / "heartbeat-prompt.json").read_text())

    def bump(self, revision: int, sideagent=None, keep: bool = True) -> None:
        """One Host business write at ``revision``. ``keep`` preserves what
        the carrier and its tool already wrote (alerts, maintenance)."""
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = self.doc() if keep and path.exists() else {
            "schema": "kaola-heartbeat-prompt/2", "body": json.dumps({"view": "host", "attention": []}),
            "state": {"maintenance": {"handled_host_revision": 0}}}
        if sideagent is not None or not keep:
            doc["state"]["sideagent"] = sideagent
        doc["host_revision"] = revision
        doc["state"].setdefault("section_sources", {})["project"] = {"writer": "host", "host_revision": revision}
        path.write_text(json.dumps(doc))

    def failures(self) -> list[str]:
        log = Path(self.holder.args.record_dir) / "events.jsonl"
        rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return [row["input"] for row in rows if row.get("kind") == "sideagent_maintenance_failure_recorded"]

    def staged_nodes(self) -> list[dict]:
        return [row for row in self.holder.pending_worker_events if row.get("kind") == "node"]

    def returned(self) -> dict:
        alerts = self.doc()["state"].get("alerts") or {}
        return (alerts.get("maintenance-returned") or {}).get("inputs") or {}

    def test_unbound_host_business_writes_record_no_failure(self) -> None:
        self.prepare_recovery_host()
        unbound = [None, {"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"},
                   {"platform": "zcode", "session": "zcode-KT-sideagent", "state": "ended", "mode": "node",
                    "recipe": {"runner": str(self.runner), "argv": ["start"]}}]
        revision = 0
        for binding in unbound:
            for _ in range(3):
                revision += 1
                self.bump(revision, binding, keep=False)
                self.assertIsNotNone(self.holder._node_host_pending(self.doc()), "a selectable Host change")
                self.boundary()
            time.sleep(0.3)
            self.assertEqual(self.failures(), [], binding)
            self.assertEqual(self.staged_nodes(), [], binding)
            self.assertNotIn("sideagent_node_returned", self.log_kinds(), binding)
            self.assertEqual(self.returned(), {}, binding)
        self.assertEqual(self.node_count(), 0)

    def test_broken_recipe_fails_once_and_repair_takes_the_later_range(self) -> None:
        self.prepare_recovery_host()
        broken = {"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active", "mode": "node",
                  "recipe": {"runner": "/absent-runner", "argv": ["start", "--repo", str(self.repo),
                             "--session", "zcode-KT-sideagent", "--role", "sideagent"]}}
        self.bump(3, broken)
        self.boundary()
        self.wait_for(lambda: self.failures() == ["batch:3"], "the one visible failure")
        self.assertEqual(len(self.staged_nodes()), 1, "the Host is woken once")
        # The evidence pointer names the failure's own event, not the stream
        # row before it (the KPR log had #41565 for the row at #41566).
        cursor = int(self.returned()["batch:3"]["evidence"].rsplit("#", 1)[1])
        self.assertEqual(cursor, self.staged_nodes()[0]["event_cursor"])
        for revision in (4, 5, 6):
            self.bump(revision)
            self.boundary()
        # Carrier memory loss (a restarted holder) does not reopen it either.
        self.holder.node.clear()
        self.bump(7)
        self.boundary()
        time.sleep(0.3)
        self.assertEqual(self.failures(), ["batch:3"])
        self.assertEqual(len(self.staged_nodes()), 1)
        self.assertEqual(list(self.returned()), ["batch:3"])
        self.assertEqual(self.node_count(), 0)
        # The Host repairs the binding: the next boundary sends the later
        # range to a fresh node. The failed range waits for the Host's request.
        doc = self.doc()
        doc["state"]["sideagent"]["recipe"]["runner"] = str(self.runner)
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps(doc))
        def sent() -> bool:
            self.holder.turn["active"] = False  # the Host turn the failure started has ended
            self.boundary()
            return len(self.fake.prompts) == 1
        self.wait_for(sent, "the repaired binding's batch")
        self.assertEqual(self.holder.node["sent_through"], 7)
        self.assertEqual(self.node_count(), 1)
        self.holder._reclaim_node()

    def test_owed_recovery_without_a_binding_stays_one_visible_failure(self) -> None:
        # A verified compaction input is a real duty without a binding: it
        # keeps its one visible failure per sequence (unchanged).
        self.prepare_recovery_host()
        self.bump(0, None, keep=False)
        doc = self.doc()
        doc["state"]["maintenance"].update(recovery_seq=1, recovery_input={
            "seq": 1, "kind": "host-compaction", "occurrence_id": "o-1", "source": "completed-host-signal",
            "holder": self.holder.holder_instance_id, "at": "2026-10-14", "evidence": "events.jsonl#1"})
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps(doc))
        for _ in range(3):
            self.boundary()
        self.wait_for(lambda: self.failures() == ["recovery#1"], "the recovery failure")
        time.sleep(0.3)
        self.assertEqual(self.failures(), ["recovery#1"])
        self.assertEqual(len(self.staged_nodes()), 1)


# Only this module's own cases run; the #255 harness's tests stay in their suite.
for _name in dir(issue255.HolderNodeMode):
    if _name.startswith("test_") and _name not in CarrierFailure.__dict__:
        setattr(CarrierFailure, _name, None)


FAILING_RUNNER = "#!/bin/sh\nexit 1\n"


class NodeRuntimeFallback(issue255.HolderNodeMode):
    """Issue #324 final scope: the node runtime is not pinned to the binding."""

    SESSION = "KT-maintenance-node"

    def install(self, platform: str, body: str) -> Path:
        runner = Path(self.tmp.name) / "skills" / f"{platform}-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text(body, encoding="utf-8")
        runner.chmod(0o755)
        return runner

    def serve(self, platform: str) -> None:
        """The fake node holder for ``platform``: its record and socket."""
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.records / platform / self.SESSION / digest
        directory.mkdir(parents=True, exist_ok=True)
        sock = Path("/tmp") / f"kaola-{os.getuid()}-acp" / (
            hashlib.sha256(str(directory).encode()).hexdigest()[:24] + ".sock")
        if self.fake:
            self.fake.close()
        self.fake = issue255.FakeNode(sock, directory / "record.json")
        os.environ["FAKE_NODE_RECORD"] = str(directory / "record.json")

    def bind(self, platform: str, exclusions: list[str], revision: int = 4) -> None:
        runner = Path(self.tmp.name) / "skills" / f"{platform}-kaola-project-runner" / "scripts" / "runtime-tmux.sh"
        worker_grants = [
            {"id": preset, "state": "granted", "count": 1}
            for preset in (
                "claude-code/haiku", "codex/luna", "devin/default", "dsh/commandcode",
                "dsh/default", "opencode/default", "zcode/default",
            )
        ]
        doc = {"schema": "kaola-heartbeat-prompt/2", "host_revision": revision,
               "body": json.dumps({"view": "host", "attention": []}),
               "state": {"authorization": {"grants": worker_grants, "exclusions": exclusions},
                         "sideagent": {"platform": platform, "session": self.SESSION, "state": "active",
                                       "mode": "node", "recipe": {"runner": str(runner), "argv": [
                                           "start", "--repo", str(self.repo), "--session", self.SESSION,
                                           "--role", "sideagent", "--model", "bound-model"]}},
                         "maintenance": {"handled_host_revision": 0},
                         "section_sources": {"project": {"writer": "host", "host_revision": revision}}}}
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps(doc))

    def events_of(self, kind: str) -> list[dict]:
        log = Path(self.holder.args.record_dir) / "events.jsonl"
        return [row for row in (json.loads(line) for line in log.read_text().splitlines())
                if row.get("kind") == kind] if log.exists() else []

    def drive(self, until, what: str) -> None:
        def step() -> bool:
            self.holder.turn["active"] = False
            self.boundary()
            return until()
        self.wait_for(step, what, timeout=20)

    def test_failed_runtime_falls_back_through_the_eligible_worker_chain(self) -> None:
        self.prepare_recovery_host()
        self.install("claude-code", FAILING_RUNNER)
        self.install("dsh", FAILING_RUNNER)
        self.install("zcode", issue255.FAKE_NODE_RUNNER)
        self.install("opencode", issue255.FAKE_NODE_RUNNER)  # installed but excluded
        self.serve("zcode")
        self.bind("claude-code", ["codex/luna", "devin/default", "dsh/commandcode", "opencode/default"])
        self.drive(lambda: len(self.fake.prompts) == 1, "a batch on the first runtime that starts")
        moves = self.events_of("sideagent_node_fallback")
        self.assertEqual([(m["from"], m.get("to"), m["chain"]) for m in moves],
                         [("claude-code", "dsh/default", ["dsh/default", "zcode/default"]),
                          ("dsh", "zcode/default", ["zcode/default"])],
                         "granted Worker presets by id; a failed runtime is not retried")
        self.assertEqual([row["session"] for row in self.events_of("sideagent_node_start_failed")],
                         [self.SESSION, self.SESSION])
        argv = json.loads((Path(self.tmp.name) / "argv").read_text())
        self.assertEqual(argv, ["start", "--repo", str(self.repo), "--session", self.SESSION,
                                "--role", "sideagent", "--tier", "default"])
        self.assertEqual(self.node_count(), 1, "the excluded opencode Runner never ran")
        self.assertEqual([row for row in self.holder.pending_worker_events if row.get("kind") == "node"], [],
                         "a move to the next runtime starts no Host turn")
        self.assertEqual(self.events_of("sideagent_maintenance_failure_recorded"), [])
        self.assertIn("host revision 1..4", self.fake.prompts[0]["params"]["text"])
        self.holder._reclaim_node()

    def test_exhausted_chain_fails_once_and_is_not_requeued(self) -> None:
        self.prepare_recovery_host()
        self.install("zcode", FAILING_RUNNER)
        self.install("claude-code", FAILING_RUNNER)
        self.install("dsh", issue255.FAKE_NODE_RUNNER)  # installed but excluded
        excluded = ["codex/luna", "devin/default", "dsh/default", "dsh/commandcode", "opencode/default"]
        self.bind("zcode", excluded)
        self.drive(lambda: self.holder.node.get("failed") is not None, "the exhausted chain")
        self.wait_for(lambda: len(self.agent.prompts()) == 1, "the Host told once")
        self.assertIn("no eligible fallback runtime", self.agent.prompts()[0])
        moves = self.events_of("sideagent_node_fallback")
        self.assertEqual([(m["from"], m.get("to"), m.get("exhausted")) for m in moves],
                         [("zcode", "claude-code/haiku", None), ("claude-code", None, True)])
        self.finish_host_turn()
        for revision in (5, 6, 7):
            self.bind("zcode", excluded, revision)
            # The binding is the same; only Host business changed.
            self.holder.turn["active"] = False
            self.boundary()
        time.sleep(0.5)
        self.assertEqual(len(self.events_of("sideagent_node_start_failed")), 2, "no runtime is retried")
        self.assertEqual(len(self.events_of("sideagent_node_fallback")), 2)
        self.assertEqual(len(self.agent.prompts()), 1, "no Host turn per later write")
        self.assertEqual(self.node_count(), 0, "the excluded dsh Runner never ran")

    def test_missing_bound_runner_moves_to_the_next_runtime(self) -> None:
        self.prepare_recovery_host()
        self.install("claude-code", issue255.FAKE_NODE_RUNNER)
        self.serve("claude-code")
        self.bind("zcode", ["codex/luna", "devin/default", "dsh/default", "dsh/commandcode", "opencode/default"])
        self.drive(lambda: len(self.fake.prompts) == 1, "a batch on the installed runtime")
        self.assertIn("sideagent_node_recipe_refused", self.log_kinds())
        self.assertEqual([(m["from"], m.get("to")) for m in self.events_of("sideagent_node_fallback")],
                         [("zcode", "claude-code/haiku")])
        self.assertEqual(json.loads((Path(self.tmp.name) / "argv").read_text())[-2:], ["--tier", "haiku"])
        self.holder._reclaim_node()


for _name in dir(issue255.HolderNodeMode):
    if _name.startswith("test_") and _name not in NodeRuntimeFallback.__dict__:
        setattr(NodeRuntimeFallback, _name, None)


if __name__ == "__main__":
    unittest.main()
