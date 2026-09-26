#!/usr/bin/env python3
"""Issue #173: a Codex turn that dies in `threadStatus systemError` (a failed
remote compact) must be recorded `turn_failed`, and its worker events must stay
staged rather than confirmed.

These drive the REAL `Holder` in-process with a stubbed agent connection,
following `tests/contract/test-issue-90-event-confirmation-race.py`.

The defect class: codex-acp 1.13.1 does not advertise the AIR "typed session
failures" capability, so a failed app-server turn becomes a plain error
`agent_message_chunk` and `session/prompt` still answers
`{stopReason: "end_turn"}`. The only structured failure signal on the wire is
`session_info_update` `_meta.codex.threadStatus.type == "systemError"`, which
the holder used to log raw and ignore - so the turn was recorded
`turn_completed/end_turn`, `_worker_event_turn_end` confirmed the events the
notification turn had delivered, and the Host sat idle looking healthy while
finished workers were never processed.

The fix reads that signal during the turn and fails the turn without rewriting
the stop reason: the event log still says what the agent sent (#113).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import tempfile
import threading
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HOLDER_PATH = PROJECT / "scripts" / "kaola-acp-holder.py"

# This holder is the ZCode Host itself, never a worker armed at one.
os.environ.pop("KAOLA_ACP_HEARTBEAT_HOST", None)
os.environ.pop("KAOLA_ACP_HEARTBEAT_HOST_SOCKET", None)

spec = importlib.util.spec_from_file_location("kaola_acp_holder", HOLDER_PATH)
holder_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(holder_module)


class StubProc:
    pid = 9090


class StubAgent:
    """Just enough agent for prompt admission; turns are settled explicitly."""

    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
        self.exit_code = None
        self.exit_signal = None
        self.stderr_pump = None
        self.malformed_lines = 0
        self.handler_errors = 0
        self.unknown_updates = 0
        self.pending_out: dict[int, str] = {}
        self.sent: list[dict] = []
        self.next_id = 0
        self.release_wait = threading.Event()

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(self.next_id)] = method
        self.sent.append({"method": method, "id": self.next_id, "params": params})
        return self.next_id

    def send_message(self, message: dict) -> None:
        self.sent.append(message)

    def wait_response(self, request_id, timeout):
        self.release_wait.wait(timeout if timeout else 30)
        return None

    def prompts_sent(self) -> list[dict]:
        return [m for m in self.sent if m.get("method") == "session/prompt"]


class CodexSystemErrorTurn(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i173-")
        root = Path(self._tmp.name)
        args = argparse.Namespace(
            record_dir=str(root / "record"), socket=str(root / "h.sock"),
            platform="codex", session="codex-host-173", repo=str(root),
            init_meta="", command="stub",
        )
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-host-173"
        self.holder.state = "ready"
        self.holder.heartbeat_host = None
        # The carrier capability is armed independently of the platform under
        # test: this exercises the codex turn-outcome path, which is the fix.
        self.holder.host_entry = holder_module.HOST_SKILL_ENTRY

    def tearDown(self) -> None:
        self.agent.release_wait.set()
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------------

    def thread_status(self, status_type: str, session_id: str | None = None) -> None:
        """Feed the one structured failure signal codex-acp emits on the wire."""
        self.holder.on_session_update({
            "sessionId": self.holder.acp_session_id if session_id is None else session_id,
            "update": {
                "sessionUpdate": "session_info_update",
                "_meta": {"codex": {"threadStatus": {"type": status_type}}},
            },
        })

    def stage(self, cursor: int, session: str = "w-1") -> dict:
        return self.holder.op_worker_event({
            "schema": holder_module.WORKER_EVENT_SCHEMA, "kind": "idle",
            "platform": "codex", "session": session, "repo": "/tmp/consuming",
            "reason": f"outcome=turn_completed c={cursor}", "event_cursor": cursor,
        })

    def log_kinds(self, kind: str) -> list[dict]:
        return [e for e in self.holder.events.read_since(0, None)
                if e.get("kind") == kind]

    def notification_prompts(self) -> list[dict]:
        return [p for p in self.agent.prompts_sent()
                if "kaola-host-notify/1" in p["params"]["prompt"][0]["text"]]

    def end_turn(self, stop_reason: str = "end_turn") -> None:
        self.holder.on_prompt_response(
            self.holder.turn["request_id"],
            {"result": {"stopReason": stop_reason}})

    # -- the defect ----------------------------------------------------------

    def test_a_system_error_turn_is_failed_and_leaves_its_event_staged(self) -> None:
        """The reported timeline, exactly: deliver an event, compact fails with
        systemError, the adapter still answers end_turn."""
        delivered = self.stage(197, session="newpin")
        self.assertEqual(len(self.notification_prompts()), 1,
                         "the staged event is delivered as a notification turn")

        self.thread_status("systemError")
        self.end_turn("end_turn")

        ended = self.log_kinds("turn_ended")
        self.assertEqual(len(ended), 1, ended)
        self.assertEqual(ended[0]["outcome"], "turn_failed",
                         "a systemError turn must not be recorded as completed")
        self.assertEqual(ended[0]["stop_reason"], "end_turn",
                         "Issue #113: the log records the stop reason the agent sent")

        self.assertEqual(self.log_kinds("worker_event_confirmed"), [],
                         "a failed turn must not confirm the events it delivered")
        self.assertEqual([e["event_id"] for e in self.holder.pending_worker_events],
                         ["codex/newpin/idle/197"],
                         "the event stays staged for redelivery")
        self.assertNotIn("prompt_fingerprint", self.holder.pending_worker_events[0],
                         "the failed turn's mark is cleared for the next boundary")
        self.assertIsNotNone(delivered.get("event_id"))

    def test_the_failed_turn_carries_the_typed_error_on_its_receipt(self) -> None:
        self.stage(198)
        self.thread_status("systemError")
        self.end_turn()

        receipt = self.holder.turn_receipt()
        self.assertEqual(receipt["outcome"], "turn_failed")
        self.assertEqual(receipt["stop_reason"], "end_turn")
        self.assertEqual(receipt.get("error", {}).get("code"), "agent-system-error")
        self.assertEqual(receipt["error"].get("threadStatus"), "systemError")

    def test_the_staged_event_is_redelivered_at_the_next_healthy_boundary(self) -> None:
        self.stage(199)
        self.thread_status("systemError")
        self.end_turn()
        self.assertEqual(len(self.notification_prompts()), 1)

        # a new turn succeeds; the flush redelivers what the failed turn left
        self.holder.turn = self.holder._empty_turn()
        again = self.holder._deliver_worker_events()

        self.assertTrue(again.get("delivered"), again)
        self.assertEqual(len(self.notification_prompts()), 2,
                         "the unconfirmed event redelivers on the next healthy boundary")
        self.end_turn()
        self.assertEqual([ids for e in self.log_kinds("worker_event_confirmed")
                          for ids in e["event_ids"]],
                         ["codex/w-1/idle/199"],
                         "the healthy turn confirms it")

    def test_status_and_observe_surface_the_failed_outcome(self) -> None:
        self.stage(200)
        self.thread_status("systemError")
        self.end_turn()

        self.assertEqual(self.holder.op_state().get("turn_outcome"), "turn_failed",
                         "an outer agent must see the failure without reading raw events")

    # -- what must not change ------------------------------------------------

    def test_a_healthy_thread_status_keeps_the_turn_completed(self) -> None:
        """The idle control: codex healthy turns emit only `active`/`idle`, so
        the receipt must be byte-identical to main."""
        self.stage(201)
        self.thread_status("active")
        self.thread_status("idle")
        self.end_turn()

        ended = self.log_kinds("turn_ended")
        self.assertEqual(ended[0]["outcome"], "turn_completed")
        self.assertEqual(ended[0]["stop_reason"], "end_turn")
        self.assertEqual(self.holder.pending_worker_events, [],
                         "a healthy turn still confirms what it delivered")
        self.assertEqual([ids for e in self.log_kinds("worker_event_confirmed")
                          for ids in e["event_ids"]], ["codex/w-1/idle/201"])
        self.assertNotIn("error", self.holder.turn_receipt())

    def test_a_turn_that_recovers_stays_healthy(self) -> None:
        """The last status in the turn wins: a systemError followed by a
        recovered idle is a healthy turn, not a failed one."""
        self.stage(202)
        self.thread_status("systemError")
        self.thread_status("idle")
        self.end_turn()

        self.assertEqual(self.log_kinds("turn_ended")[0]["outcome"], "turn_completed")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertNotIn("error", self.holder.turn_receipt())

    def test_a_retry_only_reconnect_does_not_fail_the_turn(self) -> None:
        """`codex.error willRetry: true` is a reconnect attempt, not a verdict."""
        self.stage(203)
        self.holder.on_session_update({
            "sessionId": self.holder.acp_session_id,
            "update": {"sessionUpdate": "session_info_update",
                       "_meta": {"codex": {"error": {
                           "willRetry": True, "responseStreamDisconnected": True}}}},
        })
        self.end_turn()

        self.assertEqual(self.log_kinds("turn_ended")[0]["outcome"], "turn_completed")
        self.assertEqual(self.holder.pending_worker_events, [],
                         "a reconnecting turn that answered is still a completed turn")

    def test_a_child_session_status_cannot_fail_this_turn(self) -> None:
        """A different sessionId is a native sub-agent child thread, not this turn."""
        self.stage(204)
        self.thread_status("systemError", session_id="ses-child-thread")
        self.end_turn()

        self.assertEqual(self.log_kinds("turn_ended")[0]["outcome"], "turn_completed")
        self.assertEqual(self.holder.pending_worker_events, [],
                         "a child thread's failure must not fail the parent turn")

    def test_a_status_outside_any_turn_is_inert(self) -> None:
        """No turn is active, so there is nothing to attach a failure to."""
        self.thread_status("systemError")
        self.assertIsNone(self.holder.turn.get("error"))

    def test_the_unknown_update_receipt_is_unchanged(self) -> None:
        """`session_info_update` is still counted as unknown: the fix is a
        separate `if`, never a new `elif` that would silently reclassify it."""
        self.assertEqual(self.agent.unknown_updates, 0)
        self.holder.op_prompt({"text": "work", "wait": False})
        self.thread_status("systemError")

        self.assertEqual(self.agent.unknown_updates, 1,
                         "healthy receipts must not change for codex seats")


if __name__ == "__main__":
    unittest.main(verbosity=2)
