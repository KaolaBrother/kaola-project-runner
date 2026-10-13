#!/usr/bin/env python3
"""Issue #315: register a Delegator decision, and fall back to all-idle.

A pending ``state.decisions`` row (owner delegator or user) is the record the
runner reads. At a Host turn end with no active seat turn, that row wakes
``needs_decision``. The all-idle episode latch does not suppress it, including
the turn after ``compact_reload_delivered``. With nothing registered, the same
turn falls back to the existing ``all-idle`` wake, once per episode. A seat
with an active turn keeps the current rule.
"""

from __future__ import annotations

import importlib.util
import json
import re
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ISSUE302 = REPO / "tests" / "contract" / "test-issue-302-delegator-wake-gate.py"

spec = importlib.util.spec_from_file_location("issue302_wake_315", ISSUE302)
issue302 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue302)

holder = issue302.holder
wait_for = issue302.wait_for


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def decision(owner: str, status: str | None = "pending") -> dict:
    row = {"owner": owner, "question": "which wave?"}
    if status is not None:
        row["status"] = status
    return row


class OpenRows(unittest.TestCase):
    def test_open_registered_decision_rows(self) -> None:
        doc = {"state": {"decisions": {
            "waves": decision("delegator"),
            "user-q": decision("user", None),
            "done": decision("delegator", "settled"),
            "host-q": decision("host"),
            "": decision("delegator"),
            "bad": "not-a-row",
        }}}
        rows = holder.open_registered_decision_rows(doc)
        self.assertEqual(
            [(row["id"], row["why"], row["kind"]) for row in rows],
            [("waves", "registered-decision", "decisions"),
             ("user-q", "registered-decision", "decisions")])
        self.assertEqual(
            holder.classify_delegator_attention(rows), "needs_decision")
        self.assertEqual(holder.open_registered_decision_rows(None), [])
        self.assertEqual(holder.open_registered_decision_rows({"state": []}), [])
        numeric = {"state": {"decisions": {1: decision("delegator")}}}
        self.assertEqual(holder.open_registered_decision_rows(numeric), [])


class RegistrationText(unittest.TestCase):
    """Rendered skills, not the templates. render-skills.py --write emits them."""

    def test_rendered_skills_require_registration(self) -> None:
        skill = flat((REPO / "skills" / "kaola-project-runner" / "SKILL.md").read_text(
            encoding="utf-8"))
        lifecycle = flat((REPO / "skills" / "kaola-project-runner" / "references"
                          / "lifecycle-state.md").read_text(encoding="utf-8"))
        wake = flat((REPO / "skills" / "kaola-delegator" / "references"
                     / "webhook-wake.md").read_text(encoding="utf-8"))
        self.assertIn(
            "Register each Delegator decision in `state.decisions` (`owner` `delegator` or `user`)",
            skill)
        self.assertIn(".kaola/run", skill)
        self.assertIn("does not wake the runner", skill)
        self.assertIn("The runner reads `state.decisions` and wakes `needs_decision`", lifecycle)
        self.assertIn("A note only in `.kaola/run/*.md` or the turn text does not", lifecycle)
        self.assertIn("wakes `needs_decision` only from `state.decisions`", wake)
        self.assertIn("A `.kaola/run` file or turn text does not", wake)
        self.assertIn("including the turn after a compaction reload", wake)


class DecisionWake(unittest.TestCase):
    """Uses the #302 harness methods without collecting that suite's tests."""

    setUp = issue302.issue299.WebhookCase.setUp
    tearDown = issue302.issue299.WebhookCase.tearDown
    write_config = issue302.issue299.WebhookCase.write_config
    idle_host = issue302.WakeGate.idle_host
    end_turn_wake = issue302.WakeGate.end_turn_wake
    posts_for = issue302.WakeGate.posts_for
    spawn_seat = issue302.WakeGate.spawn_seat
    event_rows = issue302.WakeGate.event_rows
    configure_endpoint = issue302.WakeGate.configure_endpoint
    webhook_process_env = issue302.WakeGate.webhook_process_env

    def write_state(self, decisions: dict, *, checkpoint: bool = False) -> Path:
        maintenance: dict = {}
        if checkpoint:
            maintenance["last_checkpoint"] = {
                "batch": "b-315",
                "at": "2026-10-13T18:38:00Z",
                "verified": True,
            }
            maintenance["last_verified"] = "2026-10-13T18:38:00Z"
        doc = {
            "schema": "kaola-heartbeat-prompt/2",
            "revision": 1,
            "host_revision": 1,
            "updated_at": "2026-10-13T18:38:00+00:00",
            "state": {
                "project": {"repo": self.project, "goal": "issue 315"},
                "tasks": {},
                "holds": {},
                "alerts": {},
                "decisions": decisions,
                "maintenance": maintenance,
            },
        }
        path = Path(self.project) / ".kaola" / "heartbeat-prompt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_registered_pending_decision_wakes_needs_decision(self) -> None:
        # (a) No active seat turn. A pending delegator row wakes
        # needs_decision, not all-idle. A later turn wakes again while the
        # row stays pending. Settling it leaves the all-idle fallback.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("decision")
            self.write_state({"waves-183-184": decision("delegator")})
            self.assertEqual(self.end_turn_wake(host, "delegator"), "needs_decision")
            wait_for(
                lambda: self.posts_for(host.holder_instance_id, "needs_decision") or None,
                15, "needs_decision for the registered row")
            self.assertFalse(self.posts_for(host.holder_instance_id, "all-idle"))
            host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})
            self.assertEqual(self.end_turn_wake(host, "self"), "needs_decision")
            wait_for(
                lambda: len(self.posts_for(host.holder_instance_id, "needs_decision")) == 2,
                15, "second turn still wakes while the row is pending")
            self.assertFalse(self.posts_for(host.holder_instance_id, "all-idle"))
            self.assertFalse(host._all_idle_woken)
            self.write_state({"waves-183-184": decision("delegator", "settled")})
            # A new event_seq: deliver dedupes holder_instance_id + event_seq,
            # and the previous needs_decision already claimed the old cursor.
            host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})
            self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
            wait_for(
                lambda: self.posts_for(host.holder_instance_id, "all-idle") or None,
                15, "settled row falls back to all-idle")
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            time.sleep(0.4)
            self.assertEqual(len(self.posts_for(host.holder_instance_id, "all-idle")), 1)
            self.assertEqual(len(self.posts_for(host.holder_instance_id, "needs_decision")), 2)

    def test_silent_turn_falls_back_to_all_idle_once(self) -> None:
        # (b) No registered decision and no active seat. One all-idle. A
        # .kaola/run note is not a decision. The episode latch holds.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("silent")
            note = Path(self.project) / ".kaola" / "run" / "decision.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                "Delegator decision required for waves 183-184.\n",
                encoding="utf-8")
            self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
            wait_for(
                lambda: self.posts_for(host.holder_instance_id, "all-idle") or None,
                15, "one all-idle fallback")
            self.assertFalse(self.posts_for(host.holder_instance_id, "needs_decision"))
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            time.sleep(0.4)
            self.assertEqual(len(self.posts_for(host.holder_instance_id, "all-idle")), 1)
            self.assertFalse(self.posts_for(host.holder_instance_id, "needs_decision"))

    def test_compact_reload_registered_decision_still_wakes(self) -> None:
        # (c) The latch is already set and compact_reload_delivered is logged.
        # A verified maintenance checkpoint is in the heartbeat. The quiet
        # turn still names all-idle and the latch drops the POST. The next
        # turn end, with the decision registered, wakes needs_decision.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("compact")
            host._all_idle_woken = True
            host.events.append({
                "kind": "compact_reload_delivered",
                "session_role": "host",
            })
            path = self.write_state({}, checkpoint=True)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertIs(stored["state"]["maintenance"]["last_checkpoint"]["verified"], True)
            self.assertIn(
                "compact_reload_delivered",
                [row.get("kind") for row in self.event_rows(host)])
            host._worker_event_turn_end(None, "turn_completed")
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            self.assertFalse(self.posts_for(host.holder_instance_id))
            self.assertTrue(host._all_idle_woken)
            self.write_state(
                {"waves-183-184": decision("delegator")}, checkpoint=True)
            doc, _body, defect = holder.read_heartbeat_file(path)
            self.assertIsNone(defect, defect)
            self.assertEqual(
                [row["id"] for row in holder.open_registered_decision_rows(doc)],
                ["waves-183-184"])
            self.assertEqual(self.end_turn_wake(host, "self"), "needs_decision")
            wait_for(
                lambda: self.posts_for(host.holder_instance_id, "needs_decision") or None,
                15, "needs_decision after compact_reload_delivered")
            self.assertFalse(self.posts_for(host.holder_instance_id, "all-idle"))
            self.assertTrue(host._all_idle_woken)
            # The row is still pending, so a Delegator turn wakes again.
            # The episode latch stays set and still does not suppress it.
            host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})
            self.assertEqual(self.end_turn_wake(host, "delegator"), "needs_decision")
            wait_for(
                lambda: len(self.posts_for(host.holder_instance_id, "needs_decision")) == 2,
                15, "pending row still wakes after the reload")
            self.assertFalse(self.posts_for(host.holder_instance_id, "all-idle"))
            self.assertTrue(host._all_idle_woken)

    def test_active_seat_keeps_current_behavior(self) -> None:
        # (d) A seat with an active turn stays quiet, registered decision or not.
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("active-seat")
            self.write_state({"waves-183-184": decision("delegator")})
            try:
                proc, _record_dir = self.spawn_seat(
                    "grok-i315-active", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "in_progress"})
                found = wait_for(
                    lambda: holder.holders_dispatched_by(
                        host.holder_instance_id, working=True) or None,
                    5, "active seat visible")
                self.assertEqual(found, [proc.pid])
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                self.assertIsNone(self.end_turn_wake(host, "self"))
                self.assertFalse(self.posts_for(host.holder_instance_id, "needs_decision"))
                self.assertFalse(self.posts_for(host.holder_instance_id, "all-idle"))
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
