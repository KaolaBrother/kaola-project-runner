#!/usr/bin/env python3
"""Issue #399: a settled Host decision is not attention, and a Delegator
turn end consumes the attention batch it already saw.

Two root causes produced ``question_waiting`` at every Host turn end with no
open question:

1. ``kaola-record-contract.py`` projected every ``owner`` ``host`` decision as
   an attention row, even a ``status`` ``settled`` row. Only an open row is
   attention; a settled row with ``transcribed`` keeps its migration
   ``transcribed-check`` row.
2. ``kaola-acp-holder.py`` advanced ``host_attention_seen`` only when the
   self carrier delivered the heartbeat body. A Delegator-admitted turn (a
   socket send or a steer) never advanced it, so the same rows woke again at
   every such turn end. The holder now refreshes the mark at that turn end;
   an unknown body leaves it alone.

The pure predicate is unchanged: a given undelivered ``host-decision`` row
still classifies as ``question_waiting`` (test-issue-302 keeps that line).
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ISSUE302 = REPO / "tests" / "contract" / "test-issue-302-delegator-wake-gate.py"
ISSUE315 = REPO / "tests" / "contract" / "test-issue-315-decision-wake.py"
RECORD_CONTRACT = REPO / "scripts" / "kaola-record-contract.py"

spec = importlib.util.spec_from_file_location("issue302_wake_399", ISSUE302)
issue302 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue302)

spec315 = importlib.util.spec_from_file_location("issue315_wake_399", ISSUE315)
issue315 = importlib.util.module_from_spec(spec315)
assert spec315.loader is not None
spec315.loader.exec_module(issue315)

record_spec = importlib.util.spec_from_file_location("record_contract_399", RECORD_CONTRACT)
record = importlib.util.module_from_spec(record_spec)
assert record_spec.loader is not None
record_spec.loader.exec_module(record)

holder = issue302.holder
wait_for = issue302.wait_for


def decision(owner: str, status: str | None = "pending", **extra) -> dict:
    row = {"owner": owner, "question": "which wave?"}
    if status is not None:
        row["status"] = status
    row.update(extra)
    return row


def attention(view: dict) -> list[tuple[str, str, str]]:
    return [(row.get("kind"), row.get("id"), row.get("why"))
            for row in view.get("attention") or []]


class HostViewDecisions(unittest.TestCase):
    """The record contract's attention projection, the first root cause."""

    def view(self, decisions: dict) -> dict:
        return record.host_view({"state": {"decisions": decisions}}, None)

    def test_settled_host_decision_is_not_attention(self) -> None:
        self.assertEqual(attention(self.view({"q": decision("host", "settled")})), [])

    def test_pending_host_decision_is_one_attention_row(self) -> None:
        rows = attention(self.view({"q": decision("host", "pending")}))
        self.assertEqual(rows, [("decisions", "q", "host-decision")])

    def test_missing_status_counts_as_open(self) -> None:
        # ``open_registered_decision_rows`` uses the same rule: only an
        # explicit ``status`` ``settled`` closes a row.
        self.assertEqual(attention(self.view({"q": decision("host", None)})),
                         [("decisions", "q", "host-decision")])

    def test_settled_transcribed_row_keeps_its_migration_check(self) -> None:
        # The pending-adoption migration shape: settling the decision does not
        # retire the transcribed-check duty. It is not a question.
        sources = {"q": decision("host", "settled", transcribed={"host_turn": 7})}
        rows = attention(self.view(sources))
        self.assertEqual(rows, [("decisions", "q", "transcribed-check")])
        self.assertIsNone(holder.classify_delegator_attention(
            self.view(sources).get("attention")))

    def test_pending_transcribed_row_keeps_both_rows(self) -> None:
        sources = {"q": decision("host", "pending", transcribed={"host_turn": 7})}
        self.assertEqual(attention(self.view(sources)),
                         [("decisions", "q", "transcribed-check"),
                          ("decisions", "q", "host-decision")])

    def test_settled_delegator_or_user_row_is_not_attention(self) -> None:
        # Host-view attention was never the channel for these rows; the holder
        # reads them through open_registered_decision_rows.
        for owner in ("delegator", "user"):
            self.assertEqual(attention(self.view({"q": decision(owner, "settled")})), [])

    def test_mixed_rows_keep_only_the_open_host_decision(self) -> None:
        rows = attention(self.view({
            "open": decision("host", "pending"),
            "settled": decision("host", "settled"),
            "transcribed": decision("host", "settled", transcribed={"host_turn": 3}),
        }))
        self.assertEqual(rows, [("decisions", "open", "host-decision"),
                                ("decisions", "transcribed", "transcribed-check")])

    def test_projected_body_carries_the_same_attention(self) -> None:
        # The holder reads the projection, not the stored state.
        body, defect = record.injection_body(
            {"schema": "kaola-heartbeat-prompt/2", "revision": 1,
             "state": {"decisions": {
                 "open": decision("host", "pending"),
                 "settled": decision("host", "settled")}}},
            Path("heartbeat-prompt.json"))
        self.assertIsNone(defect)
        view = json.loads(body or "")
        self.assertEqual(attention(view), [("decisions", "open", "host-decision")])


class _Harness(issue315.DecisionWake):
    """The #315 in-process Host without collecting its tests."""

    test_registered_pending_decision_wakes_needs_decision = None
    test_silent_turn_falls_back_to_all_idle_once = None
    test_compact_reload_registered_decision_still_wakes = None
    test_active_seat_keeps_current_behavior = None

    def end_turn(self, host, source: str = "delegator") -> str | None:
        """The production turn-end branch for one ended turn.

        A real turn writes its ``turn_ended`` row (the event cursor) before
        the wake decision; append it here so two wakes are two events.
        """
        ended = host._empty_turn()
        ended.update(outcome="turn_completed", stop_reason="end_turn",
                     prompt_source=source, wait=True)
        host._delegator_followups = 0
        host.turn = host._empty_turn()
        host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})
        reason = host._delegator_turn_end_reason(ended)
        host._finish_delegator_turn_wake(ended, reason)
        return reason

    def pending_attention(self, host) -> list:
        _staged, rows, decisions = host._delegator_pending_facts()
        return [*(rows or []), *decisions]

    def body_attention(self, host) -> list:
        _doc, body, defect = holder.read_heartbeat_file(
            Path(host.args.repo) / ".kaola" / "heartbeat-prompt.json")
        self.assertIsNone(defect, defect)
        return json.loads(body or "").get("attention") or []

    def question_posts(self, host) -> list:
        return self.posts_for(host.holder_instance_id, "question_waiting")


class DelegatorTurnConsumes(_Harness):
    """The holder's second root cause, through the real state projection."""

    def test_same_attention_is_consumed_by_a_delegator_turn_end(self) -> None:
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("same-attention")
            # Isolate the attention wake from the separate #302 all-idle
            # fallback: this Host has already sent its episode's all-idle.
            host._all_idle_woken = True
            self.write_state({"host-q": decision("host")})
            # Before the turn the row is real, undelivered attention.
            self.assertEqual(
                [(r.get("kind"), r.get("id"), r.get("why"))
                 for r in self.pending_attention(host)],
                [("decisions", "host-q", "host-decision")])
            self.assertIsNone(self.end_turn(host, "delegator"))
            self.assertIsNotNone(host.host_attention_seen)
            self.assertEqual(self.pending_attention(host), [])
            # The same stored row no longer wakes the next Delegator turn.
            self.assertIsNone(self.end_turn(host, "delegator"))
            self.assertIsNone(self.end_turn(host, "delegator"))
            wait_for(lambda: host.events.cursor >= 3, 5, "three recorded turns")
            self.assertEqual(self.question_posts(host), [])

    def test_new_attention_wakes_once_then_is_consumed(self) -> None:
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("new-attention")
            host._all_idle_woken = True
            self.write_state({"host-q": decision("host")})
            first = json.dumps(self.body_attention(host), sort_keys=True)
            self.assertIsNone(self.end_turn(host, "delegator"))
            # A changed row is a changed fingerprint: still a real question.
            self.write_state({"host-q": decision("host", question="which wave now?")})
            self.assertNotEqual(json.dumps(self.body_attention(host), sort_keys=True), first)
            self.assertEqual(self.end_turn(host, "self"), "question_waiting")
            post = wait_for(lambda: (self.question_posts(host) or [None])[-1],
                            15, "question_waiting for the new row")
            self.assertEqual(post["body"]["state"], "end_turn")
            self.assertEqual(post["body"]["state_detail"], "end_turn")
            self.assertFalse(self.posts_for(host.holder_instance_id, "all-idle"))
            # The Delegator's next turn consumes the same new row: no repeat.
            self.assertIsNone(self.end_turn(host, "delegator"))
            self.assertIsNone(self.end_turn(host, "delegator"))
            wait_for(lambda: host.events.cursor >= 4, 5, "four recorded turns")
            self.assertEqual(len(self.question_posts(host)), 1)

    def test_unknown_body_leaves_the_mark_alone(self) -> None:
        # A non-host-view body is not evidence the attention was consumed.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("plain-body")
            host._all_idle_woken = True
            self.write_state({"host-q": decision("host")})
            self.assertIsNone(self.end_turn(host, "delegator"))
            seen = host.host_attention_seen
            self.assertIsInstance(seen, str)
            path = Path(host.args.repo) / ".kaola" / "heartbeat-prompt.json"
            path.write_text(json.dumps({"body": "plain heartbeat text"}), encoding="utf-8")
            self.assertIsNone(self.end_turn(host, "delegator"))
            self.assertEqual(host.host_attention_seen, seen)

    def test_settled_host_decision_never_wakes_question_waiting(self) -> None:
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("settled")
            host._all_idle_woken = True
            self.write_state({"host-q": decision("host", "settled")})
            self.assertEqual(self.body_attention(host), [])
            self.assertEqual(self.pending_attention(host), [])
            self.assertNotEqual(self.end_turn(host, "self"), "question_waiting")
            wait_for(lambda: host.events.cursor >= 1, 5, "recorded turn")
            self.assertEqual(self.question_posts(host), [])


class SelfTurnUnchanged(_Harness):
    """A self turn keeps its #315/#324 behavior."""

    def test_compact_reload_registered_decision_still_wakes(self) -> None:
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("compact")
            host._all_idle_woken = True
            host.events.append({"kind": "compact_reload_delivered",
                                "session_role": "host"})
            self.write_state({"waves": decision("delegator")}, checkpoint=True)
            self.assertEqual(self.end_turn(host, "self"), "needs_decision")
            wait_for(lambda: self.posts_for(host.holder_instance_id, "needs_decision")
                     or None, 15, "needs_decision after the reload")
            self.assertEqual(self.pending_attention(host)[-1].get("why"),
                             "registered-decision")

    def test_compact_reload_new_host_decision_still_wakes(self) -> None:
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("compact-question")
            host._all_idle_woken = True
            host.events.append({"kind": "compact_reload_delivered",
                                "session_role": "host"})
            self.write_state({"host-q": decision("host")}, checkpoint=True)
            self.assertEqual(self.end_turn(host, "self"), "question_waiting")
            wait_for(lambda: self.question_posts(host) or None,
                     15, "self turn still reports a pending Host question")

    def test_settled_transcribed_row_is_silent_at_a_self_turn_end(self) -> None:
        # The migration row keeps its check but is not a question.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("transcribed")
            host._all_idle_woken = True
            self.write_state({"adoption": decision("host", "settled",
                                                  transcribed={"host_turn": 7})})
            self.assertEqual(
                [(r.get("kind"), r.get("id"), r.get("why"))
                 for r in self.body_attention(host)],
                [("decisions", "adoption", "transcribed-check")])
            self.assertNotEqual(self.end_turn(host, "self"), "question_waiting")
            self.assertEqual(self.question_posts(host), [])

    def test_predicate_contract_is_unchanged(self) -> None:
        # The pure mapping still names question_waiting for the rows; the fix
        # is which rows the holder hands it at a Delegator turn end.
        row = [{"kind": "decisions", "why": "host-decision"}]
        self.assertEqual(holder.delegator_turn_wake_reason(
            outcome="turn_completed", stop_reason="end_turn",
            prompt_source="delegator", self_continuing=False,
            stop_requested=False, attention_rows=row, staged_undelivered=False,
            live_seats=False), "question_waiting")
        self.assertEqual(holder.delegator_turn_wake_reason(
            outcome="turn_completed", stop_reason="end_turn",
            prompt_source="self", self_continuing=False,
            stop_requested=False, attention_rows=row, staged_undelivered=False,
            live_seats=True), "question_waiting")


if __name__ == "__main__":
    unittest.main()
