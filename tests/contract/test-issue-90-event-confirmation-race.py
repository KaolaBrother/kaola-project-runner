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
        self.handler_errors = 0
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
        self._answers: dict = {}
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

        This is the whole race: the turn ENDS while `_deliver_worker_events` is
        still inside its own `op_prompt` call. The answer is delivered on its own
        thread, exactly as production does it - `op_prompt` starts `_await_prompt`
        and that thread calls `on_prompt_response` - so the callback contends for
        `worker_events_lock` for real instead of re-entering it on this thread.

        The join is bounded rather than unconditional: a holder that serialises
        admission and marking leaves the callback waiting on the lock (it
        finishes right after this returns and the delivery releases), while a
        holder that marks after admission lets it run straight through. Both
        outcomes are reached without a sleep in the passing path.
        """
        real_op_prompt = self.holder.op_prompt
        state: dict = {"answered": 0, "threads": []}

        def op_prompt_then_answer(params):
            receipt = real_op_prompt(params)
            if receipt.get("outcome") == "in_progress" and not state["answered"]:
                state["answered"] += 1
                answer = threading.Thread(
                    target=self.holder.on_prompt_response,
                    args=(receipt["turn_request_id"],
                          {"result": {"stopReason": stop_reason}}))
                state["threads"].append(answer)
                answer.start()
                answer.join(0.5)
            return receipt

        self.holder.op_prompt = op_prompt_then_answer
        self._answers = state
        self.addCleanup(self.settle)
        return state

    def settle(self) -> None:
        """Let an answer that is waiting on `worker_events_lock` finish.

        On a holder that serialises admission with marking, the callback is
        still blocked when the delivery returns; it completes as soon as the
        lock is released. Assertions about confirmation read state after this.
        """
        for answer in list(self._answers.get("threads", [])):
            answer.join(10)
            self.assertFalse(answer.is_alive(), "a turn-end callback never returned")

    def stage(self, cursor: int, kind: str = "idle", session: str = "w-1") -> dict:
        receipt = self.holder.op_worker_event({
            "schema": holder_module.WORKER_EVENT_SCHEMA, "kind": kind,
            "platform": "codex", "session": session, "repo": "/tmp/consuming",
            "reason": f"outcome=turn_completed c={cursor}", "event_cursor": cursor,
        })
        self.settle()
        return receipt

    def stage_without_delivery(self, cursor: int) -> None:
        """Stage one event with the Host busy, then free the turn, so a test can
        drive `_deliver_worker_events()` itself."""
        busy = self.holder.op_prompt({"text": "host is working", "wait": False})
        self.stage(cursor)
        self.holder.turn = self.holder._empty_turn()
        self.agent.sent = [m for m in self.agent.sent
                           if m.get("id") != busy["turn_request_id"]]

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
        order = [e["kind"] for e in self.holder.events.read_since(0, None)
                 if str(e.get("kind", "")).startswith("worker_event")]
        self.assertEqual(order, ["worker_event", "worker_event_delivered",
                                 "worker_event_confirmed"],
                         "an instant answer must not invert the recorded chain")

    def test_instant_response_does_not_double_prompt_the_overflow_full_check(self) -> None:
        """Overflow full-check carries a generation, and races the same window."""
        self.holder._record_overflow_full_check()
        self.arm_instant_host()
        result = self.holder._deliver_worker_events()
        self.settle()

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
        self.settle()

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
        self.assertIs(retry.get("confirmed"), True,
                      "and says WHY it is a duplicate: already confirmed, not still pending")
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

    def test_admission_failure_marks_nothing_and_keeps_the_event_deliverable(self) -> None:
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
        self.settle()
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

    def test_resume_rebuilds_the_confirmed_memory_from_the_event_log(self) -> None:
        """Dedup must survive a resume: the memory is derived from the log, so a
        retry arriving after `start --resume` is still the same confirmed event."""
        self.arm_instant_host()
        self.stage(61)
        self.assertEqual(self.holder.pending_worker_events, [])

        # resume: only this holder's own event log survives
        self.holder.turn = self.holder._empty_turn()
        self.holder.pending_worker_events = []
        self.holder.confirmed_worker_events = {}
        self.holder._restore_worker_events()

        self.assertIn("codex/w-1/idle/61", self.holder.confirmed_worker_events)
        retry = self.stage(61)
        self.assertIs(retry.get("duplicate"), True, retry)
        self.assertIs(retry.get("confirmed"), True, retry)
        self.assertEqual(len(self.notification_prompts()), 1,
                         "a resumed holder must not re-prompt a confirmed event")

    def test_the_confirmed_memory_is_bounded_and_keeps_the_newest(self) -> None:
        bound = holder_module.HEARTBEAT_CONFIRMED_MEMORY
        self.holder._remember_confirmed_worker_events(
            {f"codex/w/idle/{index}": index + 1 for index in range(bound + 50)})

        self.assertEqual(len(self.holder.confirmed_worker_events), bound,
                         "an unbounded memory would grow with every confirmed turn")
        self.assertNotIn("codex/w/idle/0", self.holder.confirmed_worker_events,
                         "the oldest confirmed ids are the ones evicted")
        self.assertIn(f"codex/w/idle/{bound + 49}", self.holder.confirmed_worker_events,
                      "the most recent confirmed id is always remembered")

    def test_a_second_delivery_cannot_disturb_the_one_in_flight(self) -> None:
        """The interleaving a per-delivery rollback gets wrong.

        Connections are served on their own threads and a turn boundary starts a
        delivery of its own, so a second `_deliver_worker_events()` arriving over
        the same staged events is ordinary. Both would build the SAME prompt
        text, so nothing derived from that text can tell the second attempt from
        the first one's live turn: the second must not be able to undo the
        first's mark, or the completed turn confirms nothing and the same events
        go out twice - the very Issue #90 symptom.
        """
        self.stage_without_delivery(71)
        first = self.holder._deliver_worker_events()
        self.assertTrue(first.get("delivered"), first)
        claimed = dict(self.holder.pending_worker_events[0])

        second = self.holder._deliver_worker_events()

        self.assertEqual(second.get("reason"), "queue-empty",
                         "the in-flight events are claimed; there is nothing to send")
        self.assertEqual(len(self.notification_prompts()), 1)
        self.assertEqual(self.holder.pending_worker_events[0], claimed,
                         "the second attempt must leave the live claim untouched")

        self.holder.on_prompt_response(self.holder.turn["request_id"],
                                       {"result": {"stopReason": "end_turn"}})
        self.assertEqual(len(self.notification_prompts()), 1,
                         "the completed turn must not redeliver what it confirmed")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(
            [ids for e in self.log_kinds("worker_event_confirmed") for ids in e["event_ids"]],
            ["codex/w-1/idle/71"])

    def test_two_deliveries_cannot_be_inside_the_admission_window_together(self) -> None:
        """Real threads, and deterministic in BOTH directions.

        The rendezvous sits in `_heartbeat_payload`, i.e. between reading the
        staged list and admitting the prompt. A holder that builds the payload
        while holding `worker_events_lock` can never have two deliveries there
        at once, so the barrier times out, the first delivery proceeds alone,
        and the second finds the events already claimed - the wait is the proof.
        A holder that leaves that window unlocked lets both through instantly,
        and then the loser's rollback strips the winner's live mark: one worker
        event goes out twice and the completed turn confirms nothing.
        """
        rendezvous = threading.Barrier(2)
        real_payload = self.holder._heartbeat_payload

        def payload_then_rendezvous(events, overflow_full_check=False):
            out = real_payload(events, overflow_full_check)
            try:
                rendezvous.wait(1.0)
            except threading.BrokenBarrierError:
                pass          # serialised: nobody else can be in here
            return out

        self.holder._heartbeat_payload = payload_then_rendezvous
        self.stage_without_delivery(72)
        results: list[dict] = []
        guard = threading.Lock()

        def deliver() -> None:
            out = self.holder._deliver_worker_events()
            with guard:
                results.append(out)

        threads = [threading.Thread(target=deliver) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
            self.assertFalse(thread.is_alive(), "a delivery never returned")

        self.assertEqual(len(self.notification_prompts()), 1,
                         "two racing deliveries are still one Host prompt")
        self.assertEqual(len([out for out in results if out.get("delivered")]), 1, results)
        self.assertEqual(len(self.holder.pending_worker_events), 1,
                         "the event is in flight, not dropped")
        self.assertEqual(self.holder.pending_worker_events[0].get("prompt_fingerprint"),
                         self.holder.turn["fingerprint"],
                         "the live turn's mark must survive the refused sibling")

        self.holder.on_prompt_response(self.holder.turn["request_id"],
                                       {"result": {"stopReason": "end_turn"}})
        self.assertEqual(len(self.notification_prompts()), 1,
                         "the completed turn must not redeliver what it confirmed")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.assertEqual(
            [ids for e in self.log_kinds("worker_event_confirmed") for ids in e["event_ids"]],
            ["codex/w-1/idle/72"])

    # -- the promise is as wide as the retained log, not the last N ids -------

    def seed_confirmed_log(self, count: int) -> list[str]:
        """Write `count` real stage+confirmation pairs into this holder's own
        event log, the way completed notification turns would have, then resume
        from it. Nothing else persists these facts."""
        event_ids = []
        for cursor in range(count):
            event_id = f"codex/w-bulk/idle/{cursor}"
            event_ids.append(event_id)
            self.holder.events.append({"kind": "worker_event", "event": {
                "schema": holder_module.WORKER_EVENT_SCHEMA, "event_id": event_id,
                "kind": "idle", "platform": "codex", "session": "w-bulk",
                "repo": "/tmp/consuming", "reason": "end_turn", "event_cursor": cursor}})
            self.holder.events.append({"kind": "worker_event_confirmed",
                                       "event_ids": [event_id]})
        self.holder._restore_worker_events()
        return event_ids

    def test_a_confirmed_retry_is_ignored_past_the_hot_cache_bound(self) -> None:
        """The Issue says a confirmed event_id retry is ignored - with no "unless
        more than N events were confirmed since" exception.

        The in-memory index is bounded, so beyond that bound it stops being proof
        on its own. The confirmation is still right there in the holder's event
        log, which is the only place any of this is persisted, so the answer must
        still be `duplicate`.
        """
        bound = holder_module.HEARTBEAT_CONFIRMED_MEMORY
        event_ids = self.seed_confirmed_log(bound + 1)
        evicted = event_ids[0]
        self.assertNotIn(evicted, self.holder.confirmed_worker_events,
                         "precondition: the oldest id no longer fits the index")
        self.assertTrue(any(
            evicted in (entry.get("event_ids") or [])
            for entry in self.log_kinds("worker_event_confirmed")),
            "precondition: its confirmation is still in the retained log")

        retry = self.holder.op_worker_event({
            "schema": holder_module.WORKER_EVENT_SCHEMA, "kind": "idle",
            "platform": "codex", "session": "w-bulk", "repo": "/tmp/consuming",
            "reason": "end_turn", "event_cursor": 0})

        self.assertIs(retry.get("duplicate"), True,
                      "a confirmation the log still holds is still a confirmation")
        self.assertIs(retry.get("confirmed"), True, retry)
        self.assertNotEqual(retry.get("staged"), True, retry)
        self.assertEqual(self.notification_prompts(), [],
                         "the Host must not be prompted for an event it confirmed")
        self.assertEqual(self.holder.pending_worker_events, [])

    def test_a_new_event_is_still_delivered_past_the_hot_cache_bound(self) -> None:
        """The wider lookup must not start swallowing genuinely new events."""
        self.seed_confirmed_log(holder_module.HEARTBEAT_CONFIRMED_MEMORY + 1)
        self.arm_instant_host()

        fresh = self.stage(999, session="w-new")

        self.assertIs(fresh.get("delivered"), True, fresh)
        self.assertNotEqual(fresh.get("duplicate"), True, fresh)
        self.assertEqual(len(self.notification_prompts()), 1)
        self.assertEqual(
            [ids for e in self.log_kinds("worker_event_confirmed")
             for ids in e["event_ids"] if ids.startswith("codex/w-new/")],
            ["codex/w-new/idle/999"])

    def test_an_unconfirmed_event_past_the_bound_still_resumes(self) -> None:
        """At-least-once is unchanged: only CONFIRMED ids are suppressed."""
        self.seed_confirmed_log(holder_module.HEARTBEAT_CONFIRMED_MEMORY + 1)
        self.holder.events.append({"kind": "worker_event", "event": {
            "schema": holder_module.WORKER_EVENT_SCHEMA,
            "event_id": "codex/w-lost/idle/5", "kind": "idle", "platform": "codex",
            "session": "w-lost", "repo": "/tmp/consuming", "reason": "end_turn",
            "event_cursor": 5}})

        self.holder._restore_worker_events()

        self.assertEqual([e["event_id"] for e in self.holder.pending_worker_events],
                         ["codex/w-lost/idle/5"],
                         "an event the log never confirmed still redelivers")
        self.assertEqual(len(self.notification_prompts()), 1)

    def test_a_confirmation_the_log_no_longer_holds_is_deliverable_again(self) -> None:
        """The exact edge of the promise: it is as wide as the RETAINED log.

        Rotation can drop an old confirmation. Once the holder has no record of
        it anywhere, the event is new again - at-least-once, not a silent drop.
        """
        self.seed_confirmed_log(holder_module.HEARTBEAT_CONFIRMED_MEMORY + 1)
        self.arm_instant_host()
        # a confirmed id the retained log does not mention
        forgotten = self.holder.op_worker_event({
            "schema": holder_module.WORKER_EVENT_SCHEMA, "kind": "idle",
            "platform": "codex", "session": "w-rotated", "repo": "/tmp/consuming",
            "reason": "end_turn", "event_cursor": 7})

        self.assertIs(forgotten.get("delivered"), True, forgotten)
        self.assertNotEqual(forgotten.get("duplicate"), True, forgotten)
        self.assertEqual(len(self.notification_prompts()), 1)

    def rotate_log_past(self, keep_writing: int = 2) -> None:
        """Rotate the live event log until the currently retained oldest file is
        dropped, writing between rotations so the surviving files are real."""
        for _ in range(holder_module.EVENT_LOG_KEEP + 1):
            for index in range(keep_writing):
                self.holder.events.append({"kind": "filler", "index": index})
            with self.holder.events.lock:
                self.holder.events._rotate()

    def test_a_cached_confirmation_that_rotated_away_is_deliverable_again(self) -> None:
        """The promise is the RETAINED log - including for an id sitting in the
        in-memory cache.

        The cache answers from memory, so without a retention check it keeps
        saying `duplicate` for a confirmation the holder can no longer produce.
        That is the fixed-id horizon again, just hidden in the cache: the same
        running Holder must notice its evidence is gone and let the event
        through, while an id whose confirmation IS still retained stays a
        duplicate.
        """
        state = self.arm_instant_host()
        self.stage(101)                       # confirmed, now in the cache
        rotated_id = "codex/w-1/idle/101"
        self.assertIn(rotated_id, self.holder.confirmed_worker_events)

        self.rotate_log_past()                # its confirmation leaves the log

        state["answered"] = 0                 # the Host answers this one too
        self.stage(102)                       # confirmed AFTER rotation: retained
        retained_id = "codex/w-1/idle/102"
        self.assertIn(rotated_id, self.holder.confirmed_worker_events,
                      "precondition: the cache still holds the rotated-away id")
        self.assertFalse(
            any(rotated_id in (entry.get("event_ids") or [])
                for entry in self.log_kinds("worker_event_confirmed")),
            "precondition: its confirmation is no longer in the retained log")
        self.assertTrue(
            any(retained_id in (entry.get("event_ids") or [])
                for entry in self.log_kinds("worker_event_confirmed")),
            "precondition: the newer confirmation IS retained")
        before = len(self.notification_prompts())

        gone = self.stage(101)
        still_there = self.stage(102)

        self.assertNotEqual(gone.get("duplicate"), True,
                            "a confirmation the holder can no longer show is not evidence")
        self.assertIs(gone.get("delivered"), True, gone)
        self.assertEqual(len(self.notification_prompts()), before + 1)
        self.assertIs(still_there.get("duplicate"), True,
                      "a retained confirmation is still a duplicate")
        self.assertIs(still_there.get("confirmed"), True, still_there)
        self.assertEqual(len(self.notification_prompts()), before + 1,
                         "the retained duplicate must not prompt")

    def test_a_confirmation_is_durable_before_it_is_answerable(self) -> None:
        """The event log is the only persistence, so nothing may observe an
        event as confirmed before the record exists.

        If the in-memory state is updated first and the append follows, a retry
        in between is answered `confirmed` against a fact that is not written
        yet, and a crash there loses the only durable truth while the event has
        already been dropped from the pending list.
        """
        seen: dict = {}
        real_remember = self.holder._remember_confirmed_worker_events

        def remember_then_look(*args, **kwargs):
            # the moment the confirmation becomes visible in memory
            event_ids = args[0] if args else kwargs.get("event_ids")
            ids = list(event_ids) if not isinstance(event_ids, dict) else list(event_ids)
            seen["durable"] = {
                recorded
                for entry in self.holder.events.read_since(0, None)
                if entry.get("kind") == "worker_event_confirmed"
                for recorded in (entry.get("event_ids") or [])
            }
            seen["ids"] = set(ids)
            seen["pending"] = [item["event_id"]
                               for item in self.holder.pending_worker_events]
            return real_remember(*args, **kwargs)

        self.holder._remember_confirmed_worker_events = remember_then_look
        self.arm_instant_host()
        self.stage(111)

        self.assertEqual(seen.get("ids"), {"codex/w-1/idle/111"}, seen)
        self.assertTrue(seen["ids"] <= seen["durable"],
                        "the confirmation must already be in the event log "
                        f"when it becomes answerable (durable={seen['durable']})")
        self.assertNotIn("codex/w-1/idle/111", seen["pending"],
                         "and the event is removed only once that record exists")

    def test_the_carrier_op_stays_a_zcode_host_capability(self) -> None:
        self.holder.args.platform = "codex"
        refusal = self.stage(51)
        self.assertEqual(refusal.get("error", {}).get("code"), "worker-event-unsupported")
        self.assertEqual(self.notification_prompts(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
