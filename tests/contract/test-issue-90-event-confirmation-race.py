#!/usr/bin/env python3
"""Issue #90: ZCode Host worker-event admission/confirmation race + confirmed dedup.

These drive the REAL `Holder` in-process with a stubbed agent connection, following
`tests/contract/test-issue-65-steer-race.py`: the interleaving is arranged exactly
rather than slept for, and nothing about test waiting ships in the holder or the
generated Skills.

The defect class: `_deliver_worker_events()` admits the notification prompt through
`op_prompt(wait=False)` and only AFTERWARD marks the staged events with that turn's
`prompt_fingerprint` and snaps the overflow in-flight generation. `op_prompt` starts
its response thread before returning, so a Host that answers immediately runs
`on_prompt_response -> _worker_event_turn_end()` inside that window. The callback
finds no event carrying the fingerprint, concludes the turn was not a notification,
and re-enters `_deliver_worker_events()` - one worker event prompts the Host twice
and the completed turn is never confirmed. The overflow full-check generation races
the same way.

The second, adjacent defect: after a confirmed turn the event is gone from
`pending_worker_events`, and `op_worker_event()` dedups against that list alone, so
a retry of the same deterministic `event_id` re-stages and re-prompts an already
confirmed event.

The wrapper below reproduces "the Host answered before `op_prompt` returned"
deterministically: the real `op_prompt` runs to completion, the response is
delivered synchronously, and only then does the caller get its receipt back.
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

CAP = holder_module.HEARTBEAT_EVENT_CAP
OVERFLOW_MARK = holder_module.OVERFLOW_FULL_CHECK_MARK


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
        self.pending_out: dict[int, str] = {}
        self.sent: list[dict] = []
        self.next_id = 0
        self.release_wait = threading.Event()
        # When set, the frame is "not written": op_prompt must report
        # acp-write-failed, which is the admission-failure branch.
        self.write_fails = False

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        if not self.write_fails:
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


class EventConfirmationRace(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i90-race-")
        root = Path(self._tmp.name)
        args = argparse.Namespace(
            record_dir=str(root / "record"), socket=str(root / "h.sock"),
            platform="zcode", session="kaola-zcode-host-90", repo=str(root),
            init_meta="", command="stub",
        )
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-host-90"
        self.holder.state = "ready"
        self.holder.heartbeat_host = None

    def tearDown(self) -> None:
        self.agent.release_wait.set()
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------------

    def arm_instant_host(self, stop_reason: str = "end_turn") -> dict:
        """Answer the FIRST admitted prompt before its caller gets the receipt.

        This is the whole race: `on_prompt_response` (and therefore
        `_worker_event_turn_end`) completes while `_deliver_worker_events` is
        still between `op_prompt` and its post-hoc bookkeeping.
        """
        real_op_prompt = self.holder.op_prompt
        state: dict = {"answered": 0}

        def op_prompt_then_answer(params):
            receipt = real_op_prompt(params)
            if receipt.get("outcome") == "in_progress" and not state["answered"]:
                state["answered"] += 1
                self.holder.on_prompt_response(
                    receipt["turn_request_id"], {"result": {"stopReason": stop_reason}})
            return receipt

        self.holder.op_prompt = op_prompt_then_answer
        return state

    def stage(self, cursor: int, kind: str = "idle", session: str = "w-1") -> dict:
        return self.holder.op_worker_event({
            "schema": holder_module.WORKER_EVENT_SCHEMA, "kind": kind,
            "platform": "codex", "session": session, "repo": "/tmp/consuming",
            "reason": f"outcome=turn_completed c={cursor}", "event_cursor": cursor,
        })

    def log_kinds(self, kind: str) -> list[dict]:
        return [e for e in self.holder.events.read_since(0, None)
                if e.get("kind") == kind]

    def notification_prompts(self) -> list[dict]:
        return [p for p in self.agent.prompts_sent()
                if "kaola-host-notify/1" in p["params"]["prompt"][0]["text"]]

    # -- the race: one event, one prompt, one confirmation -------------------

    def test_instant_response_does_not_double_prompt_a_staged_event(self) -> None:
        self.arm_instant_host()
        receipt = self.stage(7)

        self.assertEqual(receipt.get("event_id"), "codex/w-1/idle/7")
        self.assertEqual(len(self.notification_prompts()), 1,
                         "the Host must be prompted exactly once for one worker event")
        self.assertEqual(self.holder.pending_worker_events, [],
                         "the completed turn must confirm the event it delivered")
        confirmed = self.log_kinds("worker_event_confirmed")
        self.assertEqual(len(confirmed), 1, confirmed)
        self.assertEqual(confirmed[0]["event_ids"], ["codex/w-1/idle/7"])
        self.assertEqual(len(self.log_kinds("worker_event_delivered")), 1)

    def test_instant_response_does_not_double_prompt_the_overflow_full_check(self) -> None:
        """Overflow full-check carries a generation, and races the same window."""
        self.holder._record_overflow_full_check()
        self.arm_instant_host()
        result = self.holder._deliver_worker_events()

        self.assertTrue(result.get("delivered"), result)
        self.assertIs(result.get("overflow_full_check"), True)
        prompts = self.notification_prompts()
        self.assertEqual(len(prompts), 1,
                         "one pending full-check generation is one Host prompt")
        self.assertIn(OVERFLOW_MARK, prompts[0]["params"]["prompt"][0]["text"])
        self.assertEqual(self.holder.overflow_confirmed_generation, 1,
                         "the completed turn must confirm the generation it delivered")
        self.assertIsNone(self.holder.overflow_inflight_generation)
        self.assertIsNone(self.holder.overflow_inflight_fingerprint)
        self.assertEqual(
            [e.get("generation") for e in self.log_kinds("worker_event_overflow_confirmed")],
            [1])

    def test_instant_response_confirms_a_full_queue_and_its_overflow_together(self) -> None:
        """Realistic path: a busy Host fills the cap, overflows, then goes idle."""
        busy = self.holder.op_prompt({"text": "host is working", "wait": False})
        self.assertEqual(busy.get("outcome"), "in_progress")
        for cursor in range(CAP):
            staged = self.stage(cursor)
            self.assertIs(staged.get("staged"), True, staged)
            self.assertNotIn("delivered", staged,
                             "a busy Host stages without attempting delivery")
        overflowed = self.stage(CAP)
        self.assertEqual(overflowed.get("error", {}).get("code"), "worker-event-queue-full")
        self.assertEqual(overflowed.get("generation"), 1)
        self.assertEqual(len(self.notification_prompts()), 0)

        # The Host finishes its own turn; the flush answers instantly.
        self.arm_instant_host()
        self.holder.on_prompt_response(busy["turn_request_id"],
                                       {"result": {"stopReason": "end_turn"}})

        self.assertEqual(len(self.notification_prompts()), 1)
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(self.holder.overflow_confirmed_generation, 1)
        confirmed = self.log_kinds("worker_event_confirmed")
        self.assertEqual(len(confirmed), 1, confirmed)
        self.assertEqual(len(confirmed[0]["event_ids"]), CAP)

    # -- confirmed event ids are not re-delivered ----------------------------

    def test_retry_of_a_confirmed_event_id_does_not_prompt_again(self) -> None:
        self.arm_instant_host()
        first = self.stage(11)
        self.assertEqual(len(self.notification_prompts()), 1)
        self.assertEqual(self.holder.pending_worker_events, [])

        retry = self.stage(11)
        self.assertIs(retry.get("duplicate"), True,
                      "a confirmed event_id offered again is a duplicate")
        self.assertEqual(retry.get("event_id"), first["event_id"])
        self.assertNotEqual(retry.get("staged"), True)
        self.assertEqual(len(self.notification_prompts()), 1,
                         "a confirmed event_id must not prompt the Host again")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(len(self.log_kinds("worker_event")), 1,
                         "the retry must not be staged into the event log again")

    def test_a_distinct_later_event_is_still_delivered_after_a_confirmed_retry(self) -> None:
        state = self.arm_instant_host()
        self.stage(11)
        self.stage(11)
        state["answered"] = 0  # the next turn's Host answers instantly too
        fresh = self.stage(12)

        self.assertIs(fresh.get("delivered"), True, fresh)
        self.assertEqual(len(self.notification_prompts()), 2,
                         "a genuinely new event is a new notification")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(
            [ids for e in self.log_kinds("worker_event_confirmed")
             for ids in e["event_ids"]],
            ["codex/w-1/idle/11", "codex/w-1/idle/12"])

    # -- everything that must keep working -----------------------------------

    def test_a_failed_notification_turn_leaves_the_event_redeliverable(self) -> None:
        self.arm_instant_host(stop_reason="cancelled")
        self.stage(21)

        self.assertEqual(len(self.notification_prompts()), 1)
        self.assertEqual(len(self.holder.pending_worker_events), 1,
                         "an unfinished notification turn keeps its event staged")
        self.assertNotIn("prompt_fingerprint", self.holder.pending_worker_events[0],
                         "the failed turn's mark must be cleared for the next boundary")
        self.assertEqual(self.log_kinds("worker_event_confirmed"), [])

        # the next healthy boundary redelivers it
        self.holder.op_prompt = holder_module.Holder.op_prompt.__get__(self.holder)
        again = self.holder._deliver_worker_events()
        self.assertTrue(again.get("delivered"), again)
        self.assertEqual(len(self.notification_prompts()), 2)

    def test_admission_failure_rolls_back_and_keeps_the_event_deliverable(self) -> None:
        """A prompt frame that is never written must not wedge the queue."""
        self.holder._record_overflow_full_check()
        self.agent.write_fails = True
        self.stage(31)

        self.assertEqual(len(self.holder.pending_worker_events), 1)
        self.assertNotIn("prompt_fingerprint", self.holder.pending_worker_events[0],
                         "a failed admission must leave nothing marked in flight")
        self.assertIsNone(self.holder.overflow_inflight_generation)
        self.assertIsNone(self.holder.overflow_inflight_fingerprint)
        self.assertEqual(self.log_kinds("worker_event_delivered"), [],
                         "nothing was delivered, so nothing may claim it was")

        self.agent.write_fails = False
        self.arm_instant_host()
        retry = self.holder._deliver_worker_events()
        self.assertTrue(retry.get("delivered"), retry)
        self.assertIs(retry.get("overflow_full_check"), True)
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(self.holder.overflow_confirmed_generation, 1)

    def test_resume_redelivers_unconfirmed_and_never_a_confirmed_event(self) -> None:
        self.arm_instant_host()
        self.stage(41)                                  # delivered and confirmed
        self.holder.op_prompt = holder_module.Holder.op_prompt.__get__(self.holder)
        self.stage(42)                                  # delivered, never answered
        self.assertEqual(len(self.notification_prompts()), 2)

        # resume: rebuild from this holder's own event log
        self.holder.turn = self.holder._empty_turn()
        self.holder.pending_worker_events = []
        self.holder.overflow_generation = 0
        self.holder.overflow_confirmed_generation = 0
        self.holder._restore_worker_events()

        restored = self.log_kinds("worker_event_restored")
        self.assertEqual(len(restored), 1, restored)
        self.assertEqual(restored[0]["event_ids"], ["codex/w-1/idle/42"],
                         "only the genuinely unconfirmed event resumes")
        self.assertEqual(len(self.notification_prompts()), 3)
        self.assertEqual([e["event_id"] for e in self.holder.pending_worker_events],
                         ["codex/w-1/idle/42"])

    def test_the_carrier_op_stays_a_zcode_host_capability(self) -> None:
        self.holder.args.platform = "codex"
        refusal = self.stage(51)
        self.assertEqual(refusal.get("error", {}).get("code"), "worker-event-unsupported")
        self.assertEqual(self.notification_prompts(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
