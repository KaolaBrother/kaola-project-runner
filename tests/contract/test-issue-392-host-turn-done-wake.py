#!/usr/bin/env python3
"""Issue #392: an unconsumed Host turn end wakes the Delegator once.

The report: an ``all-idle`` wake was already delivered for this idle episode,
the Delegator then sent a prompt WITHOUT ``--wait``, the Host turn ended
``end_turn`` with no live seat, and the Delegator received neither a wake nor
a receipt. The admission flag is now recorded on the turn, and the latched
turn-end branch sends ``host_turn_done`` when nobody consumed that result.

The two layers mirror the reproduction:

* ``LatchMicro`` drives the production holder object (the #302/#317 fixture
  style) for the latch, detail and vocabulary boundaries.
* ``RealHost`` drives the real CLI + holder + mock ACP agent + loopback
  endpoint, i.e. the path the report observed.

Run: python3 tests/contract/test-issue-392-host-turn-done-wake.py -v
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
T299 = REPO / "tests" / "contract" / "test-issue-299-delegator-webhook.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
CLI = REPO / "scripts" / "kaola-acp.py"

spec = importlib.util.spec_from_file_location("issue299_webhook_392", T299)
issue299 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue299)

holder_spec = importlib.util.spec_from_file_location("kaola_acp_holder_392", HOLDER)
holder = importlib.util.module_from_spec(holder_spec)
assert holder_spec.loader is not None
holder_spec.loader.exec_module(holder)

wait_for = issue299.wait_for
Endpoint = issue299.Endpoint
PAYLOAD_KEYS = issue299.PAYLOAD_KEYS


class HostTurnDone(issue299.WebhookCase):
    """The #299 harness plus the few helpers this issue needs."""

    def start_host(self, suffix: str) -> str:
        self.host_session = f"grok-w392-orchestrator-{suffix}"
        self.session = self.host_session
        _, receipt = self.acp("start")
        self.assertEqual(receipt.get("session_role"), "host", receipt)
        return self.session

    @contextmanager
    def webhook_process_env(self):
        """An in-process holder spawns deliver with the test process environment."""
        keys = ("KAOLA_DELEGATOR_WEBHOOK_CONFIG", "HOME", "KAOLA_ACP_RECORD_ROOT",
                "KAOLA_ACP_HEARTBEAT_HOST", "KAOLA_ACP_DISPATCHER",
                "KAOLA_ACP_HEARTBEAT_HOST_SOCKET")
        saved = {key: os.environ.get(key) for key in keys}
        os.environ["KAOLA_DELEGATOR_WEBHOOK_CONFIG"] = str(self.config)
        os.environ["HOME"] = str(self.home)
        os.environ["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        for key in ("KAOLA_ACP_HEARTBEAT_HOST", "KAOLA_ACP_DISPATCHER",
                    "KAOLA_ACP_HEARTBEAT_HOST_SOCKET"):
            os.environ.pop(key, None)
        try:
            yield
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def idle_host(self, suffix: str):
        digest = hashlib.sha256(self.project.encode()).hexdigest()[:16]
        session = f"grok-w392-orchestrator-{suffix}"
        record_dir = self.record_root / "grok" / session / digest
        record_dir.mkdir(parents=True)
        args = argparse.Namespace(
            record_dir=str(record_dir), socket=str(self.root / f"{suffix}.sock"),
            platform="grok", session=session, repo=self.project, init_meta="",
            command="stub", session_role="host",
            host_entry="/kaola-project-runner")
        host = holder.Holder(args)
        host.session_role = "host"
        host.state = "ready"
        host.stop_requested = False
        host.turn["active"] = False
        host.turn["outcome"] = "turn_completed"
        host.turn["stop_reason"] = "end_turn"
        host._delegator_followups = 0
        host._all_idle_woken = False
        return host

    def end_turn_wake(self, host, prompt_source: str, wait: bool = True,
                      stop_reason: str = "end_turn") -> str | None:
        """The production turn-end wake branch for one already-ended turn."""
        host.turn["active"] = False
        host.turn["outcome"] = "turn_completed"
        host.turn["stop_reason"] = stop_reason
        host.turn["prompt_source"] = prompt_source
        host.turn["wait"] = wait
        host._delegator_followups = 0
        reason = host._delegator_turn_end_reason(host.turn)
        host._finish_delegator_turn_wake(host.turn, reason)
        return reason

    def posts_for(self, holder_id: str, reason: str = "all-idle") -> list[dict]:
        return [post for post in (self.endpoint.posts if self.endpoint else [])
                if (post["body"] or {}).get("reason") == reason
                and (post["body"] or {}).get("holder_instance_id") == holder_id]

    def configure_endpoint(self) -> None:
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})

    def latched_real_host(self, suffix: str) -> tuple[str, int]:
        """A real Host in one idle episode that already sent ``all-idle``."""
        self.endpoint = Endpoint()
        self.configure_endpoint()
        self.start_host(suffix)
        holder_id = self.acp("status")[1]["holder_instance_id"]
        self.acp("send", "--text", f"i392-warmup-{suffix}", "--wait")
        post = wait_for(lambda: self.posts_for(holder_id, "all-idle") or None,
                        20, "episode all-idle")[0]
        return holder_id, post["body"]["event_seq"]

    def run_no_wait(self, text: str) -> None:
        _, receipt = self.acp("send", "--text", text, "--no-wait")
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 20, f"{text} turn ended")


class RealHost(HostTurnDone):
    """The reported path: real CLI, real holder, mock agent, loopback sink."""

    def test_all_idle_then_no_wait_sends_exactly_one_host_turn_done(self) -> None:
        holder_id, anchor = self.latched_real_host("once")
        self.run_no_wait("i392-once")
        post = wait_for(
            lambda: self.posts_for(holder_id, "host_turn_done") or None,
            20, "host_turn_done")[0]
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "end_turn")
        self.assertGreater(post["body"]["event_seq"], anchor)
        self.assertEqual(set(post["body"]), PAYLOAD_KEYS)
        wait_for(
            lambda: [row for row in self.receipts()
                     if row.get("holder_instance_id") == holder_id
                     and row.get("event_seq") == post["body"]["event_seq"]
                     and row.get("result") == "delivered"] or None,
            15, "delivered host_turn_done receipt")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_for(holder_id, "host_turn_done")), 1)
        # The wake ends one turn, not the idle episode: the latch still holds.
        self.assertEqual(len(self.posts_for(holder_id, "all-idle")), 1)

    def test_two_no_wait_turns_wake_twice_with_distinct_event_seq(self) -> None:
        holder_id, anchor = self.latched_real_host("twice")
        seqs: list[int] = []
        for index, text in enumerate(("i392-twice-1", "i392-twice-2"), start=1):
            self.run_no_wait(text)

            def latest(target: int = index):
                posts = self.posts_for(holder_id, "host_turn_done")
                return posts[target - 1] if len(posts) >= target else None

            post = wait_for(latest, 20, f"host_turn_done {index}")
            seqs.append(post["body"]["event_seq"])
        self.assertEqual(len(seqs), 2)
        self.assertEqual(len(set(seqs)), 2)
        self.assertTrue(all(seq > anchor for seq in seqs), seqs)
        time.sleep(0.6)
        self.assertEqual(len(self.posts_for(holder_id, "host_turn_done")), 2)

    def test_redelivery_is_skipped_duplicate(self) -> None:
        holder_id, _anchor = self.latched_real_host("dup")
        self.run_no_wait("i392-dup")
        post = wait_for(
            lambda: self.posts_for(holder_id, "host_turn_done") or None,
            20, "host_turn_done")[0]
        posts_before = len(self.endpoint.posts)
        proc = self.deliver(post["body"])
        self.assertEqual(proc.returncode, 0, (proc.stdout, proc.stderr))
        time.sleep(0.3)
        self.assertEqual(len(self.endpoint.posts), posts_before)
        rows = [row for row in self.receipts()
                if row.get("holder_instance_id") == holder_id
                and row.get("event_seq") == post["body"]["event_seq"]]
        self.assertTrue(any(row.get("result") == "skipped"
                            and row.get("skip_reason") == "duplicate"
                            for row in rows), rows)

    def test_wait_turn_in_the_same_episode_stays_silent(self) -> None:
        holder_id, anchor = self.latched_real_host("wait")
        self.acp("send", "--text", "i392-wait", "--wait")
        time.sleep(1.0)
        self.assertEqual(self.posts_for(holder_id, "host_turn_done"), [])
        later = [post for post in self.endpoint.posts
                 if post["body"]["holder_instance_id"] == holder_id
                 and post["body"]["event_seq"] > anchor]
        self.assertEqual(later, [], "a consumed --wait turn must not wake")


class LatchMicro(HostTurnDone):
    """Deterministic predicate, latch, detail and vocabulary boundaries."""

    def test_issue_317_carried_latch_still_sends_one_all_idle(self) -> None:
        # Real work resumed after the last all-idle. The first all-ended
        # transition is still all-idle, including for an unconsumed
        # Delegator turn; the new reason does not replace that rule.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("carried")
            holder_id = host.holder_instance_id
            host._all_idle_woken = True
            host._all_ended_busy = True
            host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})
            self.assertEqual(self.end_turn_wake(host, "delegator", wait=False),
                             "all-idle")
            wait_for(lambda: self.posts_for(holder_id, "all-idle") or None,
                     15, "carried all-idle")
            self.assertEqual(self.posts_for(holder_id, "host_turn_done"), [])
            self.assertTrue(host._all_idle_woken)
            self.assertFalse(host._all_ended_busy)

    def test_unconsumed_turn_detail_is_max_tokens(self) -> None:
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("maxtokens")
            holder_id = host.holder_instance_id
            self.assertTrue(host._emit_delegator_all_idle("end_turn", "end_turn"))
            wait_for(lambda: self.posts_for(holder_id, "all-idle") or None,
                     15, "episode all-idle")
            host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})
            self.assertEqual(
                self.end_turn_wake(host, "delegator", wait=False,
                                   stop_reason="max_tokens"),
                "host_turn_done")
            post = wait_for(
                lambda: self.posts_for(holder_id, "host_turn_done") or None,
                15, "host_turn_done")[0]
            self.assertEqual(post["body"]["state_detail"], "max_tokens")
            self.assertEqual(post["body"]["reason"], "host_turn_done")
            time.sleep(0.4)
            self.assertEqual(len(self.posts_for(holder_id, "all-idle")), 1)

    def test_live_seat_keeps_delegator_silence(self) -> None:
        # Boundary: the new fact never overrides the live-seat rule (#302).
        # Attention and pending facts also stay suppressed for that source.
        def reason(**overrides):
            base = dict(
                outcome="turn_completed", stop_reason="end_turn",
                prompt_source="delegator", self_continuing=False,
                stop_requested=False, attention_rows=None,
                staged_undelivered=False, live_seats=True,
                all_idle_due=False, unconsumed=True)
            base.update(overrides)
            return holder.delegator_turn_wake_reason(**base)

        question = [{"kind": "decisions", "why": "host-decision"}]
        self.assertIsNone(reason())
        self.assertIsNone(reason(attention_rows=question))
        self.assertIsNone(reason(stop_reason="max_tokens"))
        self.assertIsNone(reason(staged_undelivered=True))
        self.assertEqual(reason(live_seats=False), "host_turn_done")
        self.assertEqual(reason(live_seats=False, unconsumed=False), None)

    def test_reason_vocabulary_is_in_lockstep(self) -> None:
        cli_spec = importlib.util.spec_from_file_location("kaola_acp_392", CLI)
        cli = importlib.util.module_from_spec(cli_spec)
        assert cli_spec.loader is not None
        cli_spec.loader.exec_module(cli)
        self.assertIn("host_turn_done", holder.DELEGATOR_WAKE_REASONS)
        self.assertEqual(holder.DELEGATOR_WAKE_REASONS,
                         cli.DELEGATOR_WEBHOOK_REASONS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
