#!/usr/bin/env python3
"""Issue #381: one view snapshot, one (turn, event_cursor) publication.

The defect: ``op_view`` read ``self.turn`` and ``self.events.cursor`` without a
common lock.  A view served between a turn's ``active=False`` and its
``turn_ended`` append reported a terminal turn at the previous live cursor; a
view served during prompt admission reported ``active=true`` with
``started_at`` (the turn's ``written_at``) still null.  The adjudicated repair
is an independent leaf ``view_lock``: every publication point makes the turn
state and the event cursor visible together, and the view copies its snapshot
under the same lock.  ``view_lock`` is a leaf: nothing may acquire
``self.lock`` or ``followers_lock``, wait on ``turn_cond``, write a record, fan
out or wake while holding it.  ``on_prompt_response`` therefore moves its
fanout after the release.

The suite covers the ten research 5.2 cases and pins invariants I1-I6.
The independent review's F1-F4 races are cases 11-15: response x exit,
synthetic finish x exit, admission x exit, provider evidence I/O outside
the publish lock, and the no-write admission distinction.  The review's
R1 races are cases 16-18: a session/update threadStatus error or recovery
accepted while the synthetic finisher pre-reads its evidence (fail-to-
recover and no-fail-to-fail), and the check+write atomicity of that error
writer against the finisher's publication lock.

I1 terminal freshness   - a terminal view's cursor is strictly newer than the
                          last view that observed the turn active.
I2 admission complete   - active=true implies a non-null started_at and a
                          mutation_status other than not_started.
I3 terminal durability  - a started terminal view has its ending
                          turn_ended/process_exited event at or before the
                          cursor and the projection records that end.
I4 cursor monotonicity  - successive views never report a lower cursor.
I5 leaf discipline      - view_lock is never held across self.lock,
                          followers_lock, turn_cond.wait, write_record, fanout
                          or a wake.
I6 pending snapshot     - pending_permissions is copied defensively; a
                          concurrent settle neither raises during iteration
                          nor tears an entry.

Run: python3 tests/contract/test-issue-381-view-snapshot.py -v
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"

_spec = importlib.util.spec_from_file_location("kaola_acp_holder_i381", HOLDER)
assert _spec is not None and _spec.loader is not None
holder_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(holder_module)


class StubAgent:
    """The AgentConnection facts these in-process publication tests need."""

    def __init__(self) -> None:
        self.proc = types.SimpleNamespace(pid=os.getpid())
        self.exited = threading.Event()
        self.lock = threading.Lock()
        self.pending_out: dict[str, dict[str, object]] = {}
        self.unknown_updates = 0
        self.malformed_lines = 0
        self.handler_errors: list[dict[str, object]] = []
        self.exit_code: int | None = 0
        self.exit_signal: int | None = None
        self.next_id = 100

    def send_request(self, method: str, params: dict[str, object]) -> int:
        request_id = self.next_id
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(request_id)] = {
            "response": None, "event": threading.Event()}
        return request_id

    def wait_response(self, request_id: int, timeout: float | None) -> dict[str, object]:
        return {"result": {"stopReason": "end_turn"}}

    def send_message(self, message: dict[str, object]) -> bool:
        return True

    def cancel_outbound(self, request_id: object) -> bool:
        return True


class Gate:
    """One deterministic pause inside a publication critical section."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.fired = False
        self.cursor: int | None = None
        self.calls = 0

    def wait_entered(self, timeout: float = 10.0) -> None:
        if not self.entered.wait(timeout):
            raise AssertionError("publication gate never opened")

    def open(self) -> None:
        self.release.set()


class BeforeAcquire:
    """Pause one named thread just before it acquires the wrapped lock."""

    def __init__(self, real, thread_name: str) -> None:
        self.real = real
        self.thread_name = thread_name
        self.entered = threading.Event()
        self.release = threading.Event()

    def __enter__(self):
        if threading.current_thread().name == self.thread_name:
            self.entered.set()
            if not self.release.wait(10):
                raise AssertionError("view_lock gate was never released")
        self.real.acquire()
        return self

    def __exit__(self, *exc) -> bool:
        self.real.release()
        return False


class ViewSnapshotCase(unittest.TestCase):
    """Real Holder methods, a stub ACP connection, deterministic gates."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i381-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session_seq = 0
        self.holders: list[object] = []
        # The suite is hermetic: no inherited carrier, webhook or record root.
        self.saved_env = {key: value for key, value in os.environ.items()
                          if key.startswith("KAOLA_")}
        for key in list(self.saved_env):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key in list(os.environ):
            if key.startswith("KAOLA_"):
                os.environ.pop(key, None)
        os.environ.update(self.saved_env)
        for holder in self.holders:
            try:
                holder.agent.exited.set()
            except Exception:
                pass
        last_error: OSError | None = None
        for _ in range(25):
            try:
                self.tmp.cleanup()
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.2)
        if last_error is not None:
            raise last_error

    # -- fixture -------------------------------------------------------------

    def make_holder(self, suffix: str):
        self.session_seq += 1
        session = f"grok-w381-{suffix}-{self.session_seq}"
        digest = hashlib.sha256(str(self.repo).encode("utf-8")).hexdigest()[:16]
        record_dir = self.record_root / "grok" / session / digest
        record_dir.mkdir(parents=True)
        args = argparse.Namespace(
            record_dir=str(record_dir), socket=str(self.root / f"{session}.sock"),
            platform="grok", session=session, repo=str(self.repo), init_meta="",
            command="stub", resume=None, use_continue=False,
            session_role="worker", host_entry=None, accepted_revision="",
            start_selection="", baseline_exempt="", cli_version="")
        holder = holder_module.Holder(args)
        stub = StubAgent()
        holder.agent = stub
        holder.agent_exited = stub.exited
        holder.heartbeat_host = None
        holder.dispatched_by = None
        holder.state = "ready"
        holder.acp_session_id = "mock-session-1"
        holder.session_role = "worker"
        # The publication tests drive the turn state directly; never let the
        # real await threads end or continue a turn behind the gate.
        holder._await_prompt = lambda request_id: None
        holder._await_agent_turn = lambda turn: None
        # The wake predicate scans other holders' records; this suite tests
        # lock placement, not the wake decision.
        holder._delegator_turn_end_reason = lambda turn: None
        self.holders.append(holder)
        return holder, stub

    def read_events(self, holder) -> list[dict[str, object]]:
        path = Path(holder.record_dir) / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def start_view(self, holder):
        slot: dict[str, object] = {}
        started = threading.Event()

        def run() -> None:
            started.set()
            slot["view"] = holder.op_view({})

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self.assertTrue(started.wait(2), "view thread did not start")
        return thread, slot

    def assert_blocked(self, thread: threading.Thread, slot: dict[str, object]) -> None:
        time.sleep(0.2)
        self.assertTrue(thread.is_alive(), "view did not block on view_lock")
        self.assertNotIn("view", slot)

    def join(self, thread: threading.Thread, timeout: float = 10.0) -> None:
        thread.join(timeout)
        self.assertFalse(thread.is_alive(), "thread did not finish")

    def gate_append(self, holder, gate: Gate, kind: str) -> None:
        original = holder.events.append

        def gated(event, ts=None):
            if event.get("kind") == kind and not gate.fired:
                gate.fired = True
                gate.entered.set()
                if not gate.release.wait(15):
                    raise AssertionError(f"gate for {kind} was never released")
            cursor = original(event, ts)
            if event.get("kind") == kind:
                gate.cursor = cursor
            return cursor

        holder.events.append = gated

    def gate_projection_add(self, holder, gate: Gate) -> None:
        original = holder.projection.add_user_from_prompt

        def gated(text, cursor, started_at=None, client_message_id=None, **kwargs):
            gate.calls += 1
            gate.cursor = cursor
            gate.entered.set()
            if not gate.release.wait(15):
                raise AssertionError("admission publication gate was never released")
            return original(text, cursor, started_at, client_message_id, **kwargs)

        holder.projection.add_user_from_prompt = gated

    def gate_send(self, stub: StubAgent, gate: Gate) -> None:
        original = stub.send_request

        def gated(method, params):
            gate.calls += 1
            gate.entered.set()
            if not gate.release.wait(15):
                raise AssertionError("admission send gate was never released")
            return original(method, params)

        stub.send_request = gated

    def assert_turn_invariants(self, holder, view: dict[str, object],
                               last_cursor: int,
                               last_active_cursor: int | None = None) -> None:
        """I1-I4 and I6 for one view of a holder driven by this suite."""
        cursor = view["event_cursor"]
        self.assertIsInstance(cursor, int)
        self.assertGreaterEqual(cursor, last_cursor, "I4 cursor went backwards")
        turn = view["turn"]
        if turn["active"]:
            self.assertIsNotNone(turn["started_at"], "I2 active turn without start")
            self.assertNotEqual(turn["mutation_status"], "not_started",
                                "I2 active turn still not_started")
        if not turn["active"] and turn.get("outcome") is not None:
            if last_active_cursor is not None:
                self.assertGreater(cursor, last_active_cursor,
                                   "I1 terminal view kept the live cursor")
            ended = [row for row in self.read_events(holder)
                     if row.get("kind") in ("turn_ended", "process_exited")
                     and isinstance(row.get("cursor"), int)
                     and row["cursor"] <= cursor]
            self.assertTrue(ended, "I3 terminal view has no terminal event")
            projection_turn = (view.get("turns") or [None])[-1]
            if projection_turn is not None:
                self.assertIsNotNone(projection_turn.get("ended_at"),
                                     "I3 projection turn has no ended_at")
                self.assertLessEqual(projection_turn.get("end_cursor"), cursor,
                                     "I3 projection end_cursor is newer than the view")
        for row in view.get("pending_permissions") or []:
            self.assertIn("request_id", row)
            self.assertIn("title", row)
            self.assertIn("options", row)

    # -- the ten research 5.2 cases -----------------------------------------

    def test_case_1_prompt_response_terminal_publication(self) -> None:
        """The normal turn end: active=False and turn_ended share one window."""
        holder, _stub = self.make_holder("prompt-end")
        receipt = holder.op_prompt({"text": "hello", "wait": False})
        live = holder.op_view({})
        self.assert_turn_invariants(holder, live, 0)
        live_cursor = live["event_cursor"]
        self.assertTrue(live["turn"]["active"])
        gate = Gate()
        self.gate_append(holder, gate, "turn_ended")
        ending = threading.Thread(
            target=lambda: holder.on_prompt_response(
                receipt["turn_request_id"], {"result": {"stopReason": "end_turn"}}),
            daemon=True)
        ending.start()
        gate.wait_entered()
        self.assertFalse(holder.turn["active"])
        self.assertEqual(holder.events.cursor, live_cursor)
        view_thread, slot = self.start_view(holder)
        self.assert_blocked(view_thread, slot)
        gate.open()
        self.join(view_thread)
        self.join(ending)
        view = slot["view"]
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], "turn_completed")
        self.assertEqual(view["turn"]["stop_reason"], "end_turn")
        self.assertEqual(view["turn"]["started_at"], live["turn"]["started_at"])
        self.assertIsNotNone(view["turn"]["ended_at"])
        self.assertGreater(view["event_cursor"], live_cursor)
        self.assertGreaterEqual(view["event_cursor"], gate.cursor)
        self.assertEqual(view["turns"][-1]["end_cursor"], gate.cursor)
        ended = [row for row in self.read_events(holder)
                 if row.get("kind") == "turn_ended"]
        self.assertEqual(ended[-1]["cursor"], gate.cursor)
        self.assert_turn_invariants(holder, view, live_cursor, live_cursor)

    def test_case_2_finish_agent_turn_terminal_publication(self) -> None:
        """The synthetic turn end has the same atomic terminal pair."""
        holder, _stub = self.make_holder("agent-end")
        written_at = round(time.time(), 3)
        holder.turn.update({
            "active": True, "agent_initiated": True, "mutation_status": "in_progress",
            "written_at": written_at, "started_at": time.monotonic(),
            "fingerprint": "sha256:synthetic",
        })
        holder.projection.start_agent_turn(0, written_at)
        live = holder.op_view({})
        live_cursor = live["event_cursor"]
        gate = Gate()
        self.gate_append(holder, gate, "turn_ended")
        ending = threading.Thread(
            target=lambda: holder._finish_agent_turn(holder.turn), daemon=True)
        ending.start()
        gate.wait_entered()
        self.assertFalse(holder.turn["active"])
        view_thread, slot = self.start_view(holder)
        self.assert_blocked(view_thread, slot)
        gate.open()
        self.join(view_thread)
        self.join(ending)
        view = slot["view"]
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], "agent_turn_completed")
        self.assertGreater(view["event_cursor"], live_cursor)
        self.assertGreaterEqual(view["event_cursor"], gate.cursor)
        ended = [row for row in self.read_events(holder)
                 if row.get("kind") == "turn_ended"]
        self.assertEqual(ended[-1]["cursor"], gate.cursor)
        self.assertTrue(ended[-1].get("agent_initiated"))
        self.assertEqual(view["turns"][-1]["end_cursor"], gate.cursor)
        self.assert_turn_invariants(holder, view, live_cursor, live_cursor)

    def test_case_3_agent_exit_terminal_publication(self) -> None:
        """process_exited and the terminal turn are one publication."""
        holder, stub = self.make_holder("agent-exit")
        written_at = round(time.time(), 3)
        holder.turn.update({
            "active": True, "mutation_status": "in_progress",
            "written_at": written_at, "started_at": time.monotonic(),
            "fingerprint": "sha256:exit",
        })
        holder.projection.add_user_from_prompt("hello", 0, written_at)
        live = holder.op_view({})
        live_cursor = live["event_cursor"]
        stub.exit_code = 0
        stub.exit_signal = None
        gate = Gate()
        self.gate_append(holder, gate, "process_exited")
        exiting = threading.Thread(target=lambda: holder.on_agent_exit(0), daemon=True)
        exiting.start()
        gate.wait_entered()
        self.assertTrue(holder.agent_exited.is_set())
        view_thread, slot = self.start_view(holder)
        self.assert_blocked(view_thread, slot)
        gate.open()
        self.join(view_thread)
        self.join(exiting)
        view = slot["view"]
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], "process_exited")
        self.assertFalse(view["agent_alive"])
        self.assertGreater(view["event_cursor"], live_cursor)
        self.assertGreaterEqual(view["event_cursor"], gate.cursor)
        exited = [row for row in self.read_events(holder)
                  if row.get("kind") == "process_exited"]
        self.assertEqual(exited[-1]["cursor"], gate.cursor)
        self.assertEqual(view["turns"][-1]["end_cursor"], gate.cursor)
        self.assert_turn_invariants(holder, view, live_cursor, live_cursor)

    def test_case_4_admission_window_never_exposes_a_half_turn(self) -> None:
        """During send a view sees the old turn; after publication it is whole."""
        holder, stub = self.make_holder("admission-send")
        gate = Gate()
        self.gate_send(stub, gate)
        admitted: dict[str, object] = {}
        admitting = threading.Thread(
            target=lambda: admitted.setdefault(
                "receipt", holder.op_prompt({"text": "hello", "wait": False})),
            daemon=True)
        admitting.start()
        gate.wait_entered()
        during = holder.op_view({})
        self.assertFalse(during["turn"]["active"])
        self.assertIsNone(during["turn"]["started_at"])
        gate.open()
        self.join(admitting)
        receipt = admitted["receipt"]
        after = holder.op_view({})
        self.assertTrue(after["turn"]["active"])
        self.assertIsNotNone(after["turn"]["started_at"])
        self.assertNotEqual(after["turn"]["mutation_status"], "not_started")
        self.assertEqual(after["event_cursor"], receipt["event_cursor"])

        # The publication itself is a critical section: a view waits for the
        # whole turn, not just its active flag.
        holder2, _stub2 = self.make_holder("admission-publish")
        publish_gate = Gate()
        self.gate_projection_add(holder2, publish_gate)
        admitted2: dict[str, object] = {}
        admitting2 = threading.Thread(
            target=lambda: admitted2.setdefault(
                "receipt", holder2.op_prompt({"text": "hello", "wait": False})),
            daemon=True)
        admitting2.start()
        publish_gate.wait_entered()
        view_thread, slot = self.start_view(holder2)
        self.assert_blocked(view_thread, slot)
        publish_gate.open()
        self.join(view_thread)
        self.join(admitting2)
        view = slot["view"]
        receipt2 = admitted2["receipt"]
        self.assertTrue(view["turn"]["active"])
        self.assertIsNotNone(view["turn"]["started_at"])
        self.assertNotEqual(view["turn"]["mutation_status"], "not_started")
        self.assertEqual(view["event_cursor"], receipt2["event_cursor"])
        self.assertEqual(view["turns"][-1]["start_cursor"], receipt2["event_cursor"])

        # written_at is stamped once at admission and never rewritten.
        holder2.on_prompt_response(receipt2["turn_request_id"],
                                   {"result": {"stopReason": "end_turn"}})
        terminal = holder2.op_view({})
        self.assertFalse(terminal["turn"]["active"])
        self.assertEqual(terminal["turn"]["started_at"],
                         view["turn"]["started_at"])

    def test_case_5_synthetic_turn_start_publication(self) -> None:
        """A session/update continuation publishes turn_started with the turn."""
        holder, _stub = self.make_holder("synthetic-start")
        holder.turn.update({
            "active": False, "outcome": "turn_completed", "stop_reason": "end_turn",
            "written_at": round(time.time(), 3), "fingerprint": "sha256:prior",
        })
        holder.last_prompt = {
            "fingerprint": "sha256:prior", "written_at": round(time.time(), 3),
            "transport": "acp", "mutation_status": "completed",
            "stop_reason": "end_turn",
        }
        live = holder.op_view({})
        gate = Gate()
        self.gate_append(holder, gate, "turn_started")
        update = {
            "sessionId": "mock-session-1",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": "continuation"}},
        }
        starting = threading.Thread(
            target=lambda: holder.on_session_update(update), daemon=True)
        starting.start()
        gate.wait_entered()
        self.assertTrue(holder.turn["active"])
        self.assertEqual(holder.events.cursor, live["event_cursor"])
        view_thread, slot = self.start_view(holder)
        self.assert_blocked(view_thread, slot)
        gate.open()
        self.join(view_thread)
        self.join(starting)
        view = slot["view"]
        self.assertTrue(view["turn"]["active"])
        self.assertIsNotNone(view["turn"]["started_at"])
        self.assertNotEqual(view["turn"]["mutation_status"], "not_started")
        self.assertGreaterEqual(view["event_cursor"], gate.cursor)
        self.assertEqual(view["turns"][-1]["start_cursor"], gate.cursor)
        started = [row for row in self.read_events(holder)
                   if row.get("kind") == "turn_started"]
        self.assertEqual(started[-1]["cursor"], gate.cursor)
        self.assertTrue(started[-1].get("agent_initiated"))

    def test_case_6_pending_permissions_defensive_snapshot(self) -> None:
        """A settle during the view loop must not tear or raise."""
        holder, _stub = self.make_holder("pending")
        for index in range(3):
            holder.pending_permissions[str(index)] = {
                "request_id": index,
                "title": f"tool {index}",
                "tool_call_id": f"tc-{index}",
                "options": [{"id": "allow", "kind": "allow_once", "label": "Allow"}],
            }
        original = holder_module.permission_options_view
        fired: list[bool] = []

        def settle_during_view(entry):
            if not fired:
                fired.append(True)
                # The agent reader or on_agent_exit can settle a permission
                # while op_view is building its payload.
                holder.pending_permissions.pop("1", None)
            return original(entry)

        with mock.patch.object(holder_module, "permission_options_view",
                               settle_during_view):
            view = holder.op_view({})
        self.assertEqual(len(view["pending_permissions"]), 3)
        self.assertEqual({row["request_id"] for row in view["pending_permissions"]},
                         {"0", "1", "2"})
        for row in view["pending_permissions"]:
            self.assertIn("options", row)
            self.assertIn("tool_call_id", row)
        self.assertEqual(sorted(holder.pending_permissions), ["0", "2"])
        self.assertEqual(len(holder.op_view({})["pending_permissions"]), 2)

        # A live churn loop must not make the view iteration fail either.
        stop = threading.Event()

        def churn() -> None:
            index = 100
            while not stop.is_set():
                holder.pending_permissions[str(index)] = {
                    "request_id": index, "title": f"churn {index}",
                    "tool_call_id": f"churn-{index}", "options": [],
                }
                holder.pending_permissions.pop(str(index - 5), None)
                index += 1

        mutator = threading.Thread(target=churn, daemon=True)
        mutator.start()
        try:
            for _ in range(40):
                view = holder.op_view({})
                self.assertIsInstance(view["pending_permissions"], list)
                for row in view["pending_permissions"]:
                    self.assertIn("request_id", row)
        finally:
            stop.set()
            self.join(mutator)

    def test_case_7_invariants_i1_to_i6_across_a_stream(self) -> None:
        """One stream that checks the published invariants explicitly."""
        holder, _stub = self.make_holder("invariants")
        holder.pending_permissions["p1"] = {
            "request_id": 1, "title": "permission", "tool_call_id": "tc-p1",
            "options": [{"id": "allow", "kind": "allow_once", "label": "Allow"}],
        }
        last_cursor = 0
        receipt = holder.op_prompt({"text": "invariant turn", "wait": False})
        live = holder.op_view({})
        self.assert_turn_invariants(holder, live, last_cursor)
        self.assertTrue(live["turn"]["active"])
        self.assertIsNotNone(live["turn"]["started_at"])
        last_cursor = live["event_cursor"]
        last_active_cursor = live["event_cursor"]

        holder.on_prompt_response(receipt["turn_request_id"],
                                  {"result": {"stopReason": "end_turn"}})
        terminal = holder.op_view({})
        self.assert_turn_invariants(holder, terminal, last_cursor, last_active_cursor)
        self.assertFalse(terminal["turn"]["active"])
        self.assertGreater(terminal["event_cursor"], last_active_cursor)
        last_cursor = terminal["event_cursor"]

        update = {
            "sessionId": "mock-session-1",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": "synthetic"}},
        }
        holder.on_session_update(update)
        synthetic = holder.op_view({})
        self.assert_turn_invariants(holder, synthetic, last_cursor)
        self.assertTrue(synthetic["turn"]["active"])
        self.assertIsNotNone(synthetic["turn"]["started_at"])
        last_cursor = synthetic["event_cursor"]
        last_active_cursor = synthetic["event_cursor"]

        holder._finish_agent_turn(holder.turn)
        synthetic_end = holder.op_view({})
        self.assert_turn_invariants(holder, synthetic_end, last_cursor, last_active_cursor)
        self.assertFalse(synthetic_end["turn"]["active"])
        self.assertGreater(synthetic_end["event_cursor"], last_active_cursor)

    def test_case_8_view_lock_is_a_leaf(self) -> None:
        """No forbidden lock, wait, record, fanout or wake under view_lock."""
        guard = LeafGuard()
        holder, stub = self.make_holder("leaf-guard")
        holder.heartbeat_host = {"session": "host-session"}
        holder._carrier_send = lambda target, params: {
            "count": 1, "delivered": True, "event_id": "e-1", "pending": 0,
            "staged": False, "overflow_full_check": False,
        }
        holder._delegator_turn_end_reason = lambda turn: "turn-completed"
        woken: list[tuple] = []
        holder._delegator_wake = lambda *args, **kwargs: woken.append(args)
        guard.install(holder)
        receipt = holder.op_prompt({"text": "guarded", "wait": False})
        live = holder.op_view({})
        self.assertTrue(live["turn"]["active"])
        holder.on_prompt_response(receipt["turn_request_id"],
                                  {"result": {"stopReason": "end_turn"}})
        holder.op_view({})
        with holder.lock:
            holder.fanout_follow_delta()
        holder.on_session_update({
            "sessionId": "mock-session-1",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": "guarded synthetic"}},
        })
        holder._finish_agent_turn(holder.turn)
        holder.op_view({})
        holder.on_agent_exit(0)
        holder.op_view({})
        self.assertEqual(guard.violations, [],
                         f"view_lock held across: {guard.violations}")
        self.assertTrue(woken, "the terminal wake path was not exercised")

    def test_case_9_fanout_shape_does_not_deadlock(self) -> None:
        """op_permit's self.lock -> followers_lock -> op_view shape completes."""
        holder, _stub = self.make_holder("fanout-shape")

        class Follower:
            def __init__(self) -> None:
                self.payload = None

            def offer_delta(self, payload) -> None:
                self.payload = payload

        follower = Follower()
        holder.followers = [follower]
        done = threading.Event()

        def fanout() -> None:
            with holder.lock:
                holder.fanout_follow_delta()
            done.set()

        thread = threading.Thread(target=fanout, daemon=True)
        thread.start()
        self.assertTrue(done.wait(5), "fanout deadlocked on the view lock")
        self.join(thread)
        self.assertIsNotNone(follower.payload)
        self.assertIn("turn", follower.payload)

    def test_case_10_publication_does_not_hold_view_lock_for_fanout(self) -> None:
        """A terminal publication is visible while followers_lock is held."""
        holder, _stub = self.make_holder("fanout-order")
        receipt = holder.op_prompt({"text": "hello", "wait": False})
        gate = Gate()
        self.gate_append(holder, gate, "turn_ended")
        ending = threading.Thread(
            target=lambda: holder.on_prompt_response(
                receipt["turn_request_id"], {"result": {"stopReason": "end_turn"}}),
            daemon=True)
        ending.start()
        gate.wait_entered()
        with holder.followers_lock:
            gate.open()
            deadline = time.monotonic() + 5
            while holder.turn["active"] and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertFalse(holder.turn["active"])
            # The publication thread is now waiting for followers_lock to
            # fan out; view_lock must already be free.
            view = holder.op_view({})
            self.assertFalse(view["turn"]["active"])
            self.assertEqual(view["turn"]["outcome"], "turn_completed")
        self.join(ending)
        view = holder.op_view({})
        self.assertFalse(view["turn"]["active"])

    # -- review F1-F4 races --------------------------------------------------

    def test_case_11_response_vs_exit_recheck(self) -> None:
        """A response that waited for view_lock must lose to a published exit."""
        holder, stub = self.make_holder("response-exit")
        stub.exit_code = 1
        receipt = holder.op_prompt({"text": "normal", "wait": False})
        gate = BeforeAcquire(holder.view_lock, "response")
        holder.view_lock = gate
        response = threading.Thread(
            name="response",
            target=lambda: holder.on_prompt_response(
                receipt["turn_request_id"], {"result": {"stopReason": "end_turn"}}),
            daemon=True)
        response.start()
        self.assertTrue(gate.entered.wait(3), "response did not reach view_lock")
        holder.on_agent_exit(1)
        gate.release.set()
        self.join(response)
        view = holder.op_view({})
        exited = [row for row in self.read_events(holder)
                  if row.get("kind") == "process_exited"]
        self.assertTrue(exited)
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], "process_exited")
        self.assertEqual(view["turn"]["outcome"], view["turns"][-1]["outcome"])
        self.assertEqual(view["turns"][-1]["end_cursor"], exited[-1]["cursor"])
        self.assertFalse(any(row.get("kind") == "turn_ended"
                             for row in self.read_events(holder)))

    def test_case_12_synthetic_finish_vs_exit_recheck(self) -> None:
        """The synthetic finisher rechecks ownership inside view_lock."""
        holder, stub = self.make_holder("synthetic-exit")
        stub.exit_code = 1
        written_at = round(time.time(), 3)
        holder.turn.update({
            "active": False, "outcome": "turn_completed", "stop_reason": "end_turn",
            "written_at": written_at, "fingerprint": "sha256:prior",
        })
        holder.last_prompt = {
            "fingerprint": "sha256:prior", "written_at": written_at,
            "transport": "acp", "mutation_status": "completed",
            "stop_reason": "end_turn",
        }
        holder.on_session_update({
            "sessionId": "mock-session-1",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": "continuation"}},
        })
        target = holder.turn
        self.assertTrue(target["active"])
        gate = BeforeAcquire(holder.view_lock, "finisher")
        holder.view_lock = gate
        finisher = threading.Thread(
            name="finisher",
            target=lambda: holder._finish_agent_turn(target),
            daemon=True)
        finisher.start()
        self.assertTrue(gate.entered.wait(3), "finisher did not reach view_lock")
        holder.on_agent_exit(1)
        gate.release.set()
        self.join(finisher)
        view = holder.op_view({})
        exited = [row for row in self.read_events(holder)
                  if row.get("kind") == "process_exited"]
        self.assertTrue(exited)
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], "process_exited")
        self.assertEqual(view["turn"]["outcome"], view["turns"][-1]["outcome"])
        self.assertEqual(view["turns"][-1]["end_cursor"], exited[-1]["cursor"])
        self.assertFalse(any(row.get("kind") == "turn_ended"
                             for row in self.read_events(holder)))

    def test_case_13_admission_vs_exit_never_reactivates(self) -> None:
        """A written admission after process_exited publishes exited, not active."""
        holder, stub = self.make_holder("admission-exit")
        stub.exit_code = 1
        entered = threading.Event()
        release = threading.Event()
        original = stub.send_request

        def sent_then_pause(method, params):
            request_id = original(method, params)
            entered.set()
            if not release.wait(5):
                raise AssertionError("admission gate timed out")
            return request_id

        stub.send_request = sent_then_pause
        receipts: list[dict[str, object]] = []
        admitting = threading.Thread(
            name="admit",
            target=lambda: receipts.append(
                holder.op_prompt({"text": "sent before exit", "wait": False})),
            daemon=True)
        admitting.start()
        self.assertTrue(entered.wait(3), "admission did not reach the write pause")
        holder.on_agent_exit(1)
        release.set()
        self.join(admitting)
        view = holder.op_view({})
        receipt = receipts[0]
        exited = [row for row in self.read_events(holder)
                  if row.get("kind") == "process_exited"]
        self.assertTrue(exited)
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], "process_exited")
        self.assertIsNotNone(view["turn"]["started_at"])
        self.assertEqual(view["turns"][-1]["outcome"], "process_exited")
        self.assertEqual(view["turns"][-1]["end_cursor"], exited[-1]["cursor"])
        self.assertGreaterEqual(view["event_cursor"], exited[-1]["cursor"])
        self.assertEqual(receipt["outcome"], "process_exited")
        self.assertIs(receipt["mutation_performed"], True)
        self.assertNotEqual(receipt["mutation_status"], "not_started")
        self.assertEqual(receipt["error"]["code"], "agent-exited-after-write")
        self.assertFalse(any(row.get("kind") == "turn_ended"
                             for row in self.read_events(holder)))

    def test_case_14_provider_summary_io_outside_view_lock(self) -> None:
        """Kimi provider evidence is read before view_lock, not under it."""
        holder, _stub = self.make_holder("provider-io")
        holder.args.platform = "kimi-cli"
        receipt = holder.op_prompt({"text": "provider failure", "wait": False})
        wire = self.root / "wire.jsonl"
        wire.write_text("{}\n", encoding="utf-8")
        holder._kimi_wire_file = lambda: (wire, "")
        observed: list[bool] = []
        original = holder_module.read_latest_kimi_wire_error

        def read(path):
            observed.append(holder.view_lock.locked())
            return original(path)

        holder_module.read_latest_kimi_wire_error = read
        try:
            holder.on_prompt_response(receipt["turn_request_id"], {"error": {}})
        finally:
            holder_module.read_latest_kimi_wire_error = original
        self.assertEqual(observed, [False],
                         "provider evidence was read while view_lock was held")
        self.assertEqual(holder.op_view({})["turn"]["outcome"], "turn_failed")

    def test_case_15_no_write_admission_stays_not_started(self) -> None:
        """A pending_out miss is a no-write failure with no ending event."""
        holder, stub = self.make_holder("no-write")
        stub.send_request = lambda method, params: 901
        receipt = holder.op_prompt({"text": "no write", "wait": False})
        view = holder.op_view({})
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertEqual(receipt["error"]["code"], "acp-write-failed")
        self.assertFalse(view["turn"]["active"])
        self.assertIsNone(view["turn"]["started_at"])
        self.assertEqual(view["turn"]["mutation_status"], "not_started")
        self.assertEqual(view["turn"]["outcome"], "turn_failed")
        self.assertEqual(view["event_cursor"], 0)
        self.assertFalse(any(row.get("kind") == "turn_ended"
                             for row in self.read_events(holder)))

    # -- review R1: session/update evidence vs the synthetic finisher --------

    def _open_agent_initiated_turn(self, holder) -> dict[str, object]:
        """Open the agent-initiated turn exactly as case 12 does."""
        written_at = round(time.time(), 3)
        holder.turn.update({
            "active": False, "outcome": "turn_completed", "stop_reason": "end_turn",
            "written_at": written_at, "fingerprint": "sha256:prior",
        })
        holder.last_prompt = {
            "fingerprint": "sha256:prior", "written_at": written_at,
            "transport": "acp", "mutation_status": "completed",
            "stop_reason": "end_turn",
        }
        holder.on_session_update({
            "sessionId": "mock-session-1",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": "continuation"}},
        })
        turn = holder.turn
        self.assertTrue(turn["active"])
        self.assertTrue(turn.get("agent_initiated"))
        return turn

    @staticmethod
    def _codex_status_update(status: str) -> dict[str, object]:
        return {
            "sessionId": "mock-session-1",
            "update": {"sessionUpdate": "session_info_update",
                       "_meta": {"codex": {"threadStatus": {"type": status}}}},
        }

    def _paused_update(self, holder, status: str, pause_text: str):
        """Run one real session_info_update in a thread paused (via settrace)
        at the first line of on_session_update containing ``pause_text``.
        ``assigned`` is set when the update reaches the projection apply line,
        i.e. after the error write and its lock have completed."""
        code = holder.on_session_update.__func__.__code__
        text = Path(code.co_filename).read_text().splitlines()
        pause_line = next(i + 1 for i, line in enumerate(text)
                          if i + 1 > code.co_firstlineno and pause_text in line)
        after_line = next(
            i + 1 for i, line in enumerate(text)
            if i + 1 > pause_line
            and 'if variant != "usage_update" or same_session:' in line)
        entered = threading.Event()
        release = threading.Event()
        assigned = threading.Event()

        def trace(frame, event, arg):
            if frame.f_code is code and event == "line":
                if frame.f_lineno == pause_line:
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError("paused update was never released")
                elif frame.f_lineno == after_line:
                    assigned.set()
            return trace

        def run() -> None:
            sys.settrace(trace)
            try:
                holder.on_session_update(self._codex_status_update(status))
            finally:
                sys.settrace(None)

        thread = threading.Thread(name="update", target=run, daemon=True)
        thread.start()
        self.assertTrue(entered.wait(3), "update did not reach the pause line")
        return thread, release, assigned

    def _last_turn_ended(self, holder) -> dict[str, object]:
        ended = [row for row in self.read_events(holder)
                 if row.get("kind") == "turn_ended"]
        self.assertTrue(ended, "no turn_ended event was published")
        return ended[-1]

    def test_case_16_synthetic_finish_evidence_recovers_after_preread(self) -> None:
        """An accepted error cleared during the pre-read stays recovered."""
        holder, _stub = self.make_holder("synthetic-recover")
        target = self._open_agent_initiated_turn(holder)
        holder.on_session_update(self._codex_status_update("systemError"))
        self.assertEqual(target["error"]["code"], "agent-system-error")
        updater, release, assigned = self._paused_update(
            holder, "idle", 'if turn["active"] and same_session:')
        original = holder._turn_failure_summary

        def summary(outcome, error):
            result = original(outcome, error)
            release.set()
            self.assertTrue(assigned.wait(5),
                            "paused update did not finish its error write")
            return result

        holder._turn_failure_summary = summary
        try:
            holder._finish_agent_turn(target)
        finally:
            release.set()
        self.join(updater)
        self.assertIsNone(target["error"])
        self.assertEqual(target["outcome"], "agent_turn_completed")
        self.assertIsNone(holder.turn_error)
        ended = self._last_turn_ended(holder)
        self.assertEqual(ended["outcome"], "agent_turn_completed")
        self.assertNotIn("error", ended)
        view = holder.op_view({})
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], view["turns"][-1]["outcome"])
        self.assertEqual(view["turn"]["outcome"], "agent_turn_completed")

    def test_case_17_synthetic_finish_failure_arrives_after_preread(self) -> None:
        """An error accepted during the pre-read fails the turn it landed on."""
        holder, _stub = self.make_holder("synthetic-late-error")
        target = self._open_agent_initiated_turn(holder)
        self.assertIsNone(target["error"])
        updater, release, assigned = self._paused_update(
            holder, "systemError", 'if turn["active"] and same_session:')
        original = holder._turn_failure_summary

        def summary(outcome, error):
            result = original(outcome, error)
            release.set()
            self.assertTrue(assigned.wait(5),
                            "paused update did not finish its error write")
            return result

        holder._turn_failure_summary = summary
        try:
            holder._finish_agent_turn(target)
        finally:
            release.set()
        self.join(updater)
        self.assertEqual(target["error"]["code"], "agent-system-error")
        self.assertEqual(target["outcome"], "turn_failed")
        self.assertEqual(holder.turn_error["source"], "unavailable")
        self.assertEqual(holder.turn_error["reason"], "evidence-raced")
        ended = self._last_turn_ended(holder)
        self.assertEqual(ended["outcome"], "turn_failed")
        self.assertEqual(ended["error"]["reason"], "evidence-raced")
        view = holder.op_view({})
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], view["turns"][-1]["outcome"])
        self.assertEqual(view["turn"]["outcome"], "turn_failed")

    def test_case_18_error_writer_check_and_write_are_one_publication(self) -> None:
        """The error writer holds view_lock across check and write, so the
        finisher cannot publish between them."""
        holder, _stub = self.make_holder("writer-atomicity")
        target = self._open_agent_initiated_turn(holder)
        self.assertIsNone(target["error"])
        updater, release, _assigned = self._paused_update(
            holder, "systemError", 'turn["error"] = (')
        finisher = threading.Thread(
            name="finisher",
            target=lambda: holder._finish_agent_turn(target),
            daemon=True)
        finisher.start()
        try:
            time.sleep(0.2)
            self.assertTrue(finisher.is_alive(),
                            "finisher did not block on view_lock")
            self.assertTrue(holder.turn["active"],
                            "finisher published while the writer held view_lock")
        finally:
            release.set()
        self.join(finisher)
        self.join(updater)
        self.assertEqual(target["error"]["code"], "agent-system-error")
        self.assertEqual(target["outcome"], "turn_failed")
        self.assertEqual(holder.turn_error["source"], "unavailable")
        self.assertEqual(holder.turn_error["reason"], "evidence-raced")
        ended = self._last_turn_ended(holder)
        self.assertEqual(ended["outcome"], "turn_failed")
        self.assertEqual(ended["error"]["reason"], "evidence-raced")
        view = holder.op_view({})
        self.assertFalse(view["turn"]["active"])
        self.assertEqual(view["turn"]["outcome"], view["turns"][-1]["outcome"])
        self.assertEqual(view["turn"]["outcome"], "turn_failed")


class LeafGuard:
    """Thread-local detector for forbidden work under view_lock."""

    def __init__(self) -> None:
        self.local = threading.local()
        self.violations: list[str] = []

    def mark(self, name: str) -> None:
        if getattr(self.local, "held", False):
            self.violations.append(name)

    def _lock_proxy(self, real, name: str):
        guard = self

        class Proxy:
            def acquire(self, blocking: bool = True, timeout: float = -1):
                guard.mark(f"{name}.acquire")
                if timeout == -1:
                    return real.acquire(blocking)
                return real.acquire(blocking, timeout)

            def release(self) -> None:
                real.release()

            def __enter__(self):
                self.acquire()
                return self

            def __exit__(self, *exc) -> bool:
                self.release()
                return False

        return Proxy()

    def _view_proxy(self, real):
        guard = self

        class Proxy:
            def acquire(self, blocking: bool = True, timeout: float = -1):
                real.acquire(blocking)
                guard.local.held = True

            def release(self) -> None:
                guard.local.held = False
                real.release()

            def __enter__(self):
                self.acquire()
                return self

            def __exit__(self, *exc) -> bool:
                self.release()
                return False

        return Proxy()

    def install(self, holder) -> None:
        holder.view_lock = self._view_proxy(holder.view_lock)
        holder.lock = self._lock_proxy(holder.lock, "self.lock")
        holder.followers_lock = self._lock_proxy(holder.followers_lock,
                                                 "followers_lock")
        for name in ("write_record", "fanout_follow_delta", "fanout_follow_eof",
                     "_notify_heartbeat_host_now", "_delegator_wake"):
            original = getattr(holder, name)
            self._wrap(holder, name, original)
        original_wait = holder.turn_cond.wait

        def gated_wait(*args, **kwargs):
            self.mark("turn_cond.wait")
            return original_wait(*args, **kwargs)

        holder.turn_cond.wait = gated_wait

    def _wrap(self, holder, name: str, original) -> None:
        guard = self

        def gated(*args, **kwargs):
            guard.mark(name)
            return original(*args, **kwargs)

        setattr(holder, name, gated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
