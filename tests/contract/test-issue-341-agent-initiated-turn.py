#!/usr/bin/env python3
"""Issue #341: treat agent-initiated session/update activity while idle as a real turn.

Covers:
  (a) autonomous continuation after the last prompt response opens a synthetic
      turn (durable turn_started, prompt_source="self", agent_initiated=True,
      seat_turn_blocks_all_idle(record) True and last_prompt.mutation_status
      busy while active), closes after the quiet period with a second durable
      turn_ended (outcome="agent_turn_completed", stop_reason=None), and emits
      exactly ONE additional Delegator wake POST with a reason per #302;
  (b) a holder prompt / steer arriving mid-continuation behaves as steer/send
      does for an active turn today: no double turn_ended and no duplicate wake;
  (c) stray/empty updates and usage/config/foreign-session noise when idle do
      not open a synthetic turn, do not emit turn_ended, and do not wake.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
MOCK_AGENT = REPO / "tests" / "contract" / "mock-acp-agent.py"


def _run_autonomous_mock(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="autonomous_burst")
    parser.add_argument("--delay-ms", type=int, default=200)
    parser.add_argument("--chunk-ms", type=int, default=80)
    parser.add_argument("--chunks", type=int, default=4)
    parser.add_argument("--steering", default="none")
    args, _ = parser.parse_known_args(argv)

    spec = importlib.util.spec_from_file_location("mock_acp_base_341", MOCK_AGENT)
    assert spec is not None and spec.loader is not None
    mock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mock)

    agent = mock.MockAgent(
        scenario="normal",
        caps=set(),
        turn_ms=40,
        flood_bytes=0,
        steering=args.steering,
    )
    orig_finish = agent.finish_turn
    orig_cancel = agent.on_cancel_notification
    done_count = [0]
    continuation_canceled = threading.Event()

    def patched_cancel(params: dict[str, Any]) -> None:
        continuation_canceled.set()
        orig_cancel(params)

    agent.on_cancel_notification = patched_cancel

    def patched_finish(request_id: Any, stop: str = "end_turn") -> bool:
        ok = orig_finish(request_id, stop)
        if not ok:
            return False
        done_count[0] += 1
        if done_count[0] != 1:
            return True
        session_id = next(iter(agent.sessions), "")

        if args.mode in ("autonomous_burst", "mid_continuation"):
            def autonomous_continuation() -> None:
                if continuation_canceled.wait(max(args.delay_ms, 0) / 1000.0):
                    return
                mock.thought_chunk(session_id, "autonomous follow-up thinking...")
                if continuation_canceled.wait(max(args.chunk_ms, 10) / 1000.0):
                    return
                mock.session_update(session_id, {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "tc-auto-1",
                    "title": "check-worker-delivery",
                    "kind": "execute",
                    "status": "in_progress",
                })
                if continuation_canceled.wait(max(args.chunk_ms, 10) / 1000.0):
                    return
                mock.session_update(session_id, {
                    "sessionUpdate": "tool_call_update",
                    "toolCallId": "tc-auto-1",
                    "status": "completed",
                    "content": [{"type": "text", "text": "ok"}],
                })
                for idx in range(max(1, args.chunks)):
                    if continuation_canceled.wait(max(args.chunk_ms, 10) / 1000.0):
                        return
                    mock.message_chunk(
                        session_id,
                        f"autonomous chunk {idx + 1}/{max(1, args.chunks)}; ",
                    )

            threading.Thread(target=autonomous_continuation, daemon=True).start()
        elif args.mode == "noise_only":
            def noise_burst() -> None:
                time.sleep(max(args.delay_ms, 0) / 1000.0)
                mock.session_update(session_id, {
                    "sessionUpdate": "usage_update",
                    "used": 2048,
                    "size": 128000,
                })
                mock.session_update(session_id, {
                    "sessionUpdate": "available_commands_update",
                    "availableCommands": [{"name": "help", "description": "help"}],
                })
                mock.session_update(session_id, {
                    "sessionUpdate": "current_mode_update",
                    "currentModeId": "auto",
                    "availableModes": [{"id": "auto", "name": "Auto"}],
                })
                mock.session_update(session_id, {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": ""},
                })
                mock.session_update(session_id, {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "   "},
                })
                mock.session_update("foreign-session-999", {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "sub-agent work on foreign session"},
                })
                mock.session_update(session_id, {
                    "sessionUpdate": "session_info_update",
                    "_meta": {"codex": {"threadStatus": {"type": "idle"}}},
                })

            threading.Thread(target=noise_burst, daemon=True).start()
        return True

    agent.finish_turn = patched_finish
    return agent.serve()


if __name__ == "__main__" and "--mock-agent" in sys.argv:
    idx = sys.argv.index("--mock-agent")
    raise SystemExit(_run_autonomous_mock(sys.argv[idx + 1:]))


ISSUE302 = REPO / "tests" / "contract" / "test-issue-302-delegator-wake-gate.py"
spec302 = importlib.util.spec_from_file_location("issue302_wake_341", ISSUE302)
assert spec302 is not None and spec302.loader is not None
issue302 = importlib.util.module_from_spec(spec302)
spec302.loader.exec_module(issue302)

holder = issue302.holder
wait_for = issue302.wait_for
host_view = issue302.host_view


class AgentInitiatedTurnTest(unittest.TestCase):
    """End-to-end and unit coverage for Issue #341 agent-initiated turns."""

    setUp = issue302.issue299.WebhookCase.setUp
    env = issue302.issue299.WebhookCase.env
    holder_record = issue302.issue299.WebhookCase.holder_record
    write_config = issue302.issue299.WebhookCase.write_config
    posts_for = issue302.WakeGate.posts_for
    write_heartbeat = issue302.WakeGate.write_heartbeat
    configure_endpoint = issue302.WakeGate.configure_endpoint

    def tearDown(self) -> None:
        current = getattr(self, "session", None)
        for name in list(getattr(self, "extra_sessions", []) or []):
            if name and name != current:
                self.session = name
                self.acp("stop", "--force", check=False, timeout=30)
        self.session = current
        self.extra_sessions = []
        issue302.issue299.WebhookCase.tearDown(self)

    def autonomous_command(self, mode: str = "autonomous_burst",
                           delay_ms: int = 200, chunk_ms: int = 80,
                           chunks: int = 4, steering: str = "none") -> str:
        return (
            f"{sys.executable} {Path(__file__).resolve()} --mock-agent "
            f"--mode {mode} --delay-ms {delay_ms} --chunk-ms {chunk_ms} "
            f"--chunks {chunks} --steering {steering}"
        )

    def acp_custom(self, command: str, *args: str, agent_cmd: str | None = None,
                   check: bool = True, timeout: float = 60,
                   extra_env: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        cmd = agent_cmd or self.autonomous_command()
        env = dict(extra_env or {})
        env.setdefault("KAOLA_ACP_AGENT_TURN_QUIET_SECONDS", "0.45")
        argv = [
            sys.executable, str(issue302.issue299.CLI), "grok", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", cmd, *args,
        ]
        proc = issue302.subprocess.run(
            argv, capture_output=True, text=True,
            env=self.env(env), timeout=timeout,
        )
        try:
            receipt = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command} not JSON: {proc.stdout!r} stderr={proc.stderr!r}")
        if check:
            self.assertNotIn("error", receipt, f"{command} failed: {receipt.get('error')}")
            self.assertNotEqual(receipt.get("result"), "refused", f"{command} refused: {receipt}")
        return proc.returncode, receipt

    def acp(self, command: str, *args: str, check: bool = True,
            timeout: float = 60, scenario: str = "normal",
            turn_ms: int = 0, extra_env: dict | None = None):
        return self.acp_custom(
            command, *args, check=check, timeout=timeout, extra_env=extra_env,
        )

    def test_case_a_autonomous_continuation_emits_turn_ended_and_single_wake(self) -> None:
        """Case (a): autonomous continuation after prompt 1 opens a synthetic turn,
        marks the seat busy (seat_turn_blocks_all_idle True, last_prompt.mutation_status
        busy), closes after the quiet period with a second turn_ended
        (outcome='agent_turn_completed'), and delivers exactly ONE additional wake POST.
        """
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        self.session = "grok-w341-orchestrator-a"
        cmd = self.autonomous_command(
            mode="autonomous_burst", delay_ms=250, chunk_ms=100, chunks=3,
        )
        _, start_receipt = self.acp_custom("start", agent_cmd=cmd)
        holder_id = start_receipt["holder_instance_id"]
        self.assertEqual(start_receipt.get("session_role"), "host")

        # Prompt 1 finishes normally and emits the first all-idle wake.
        _, send_receipt = self.acp_custom("send", "--text", "kickoff", "--wait", agent_cmd=cmd)
        self.assertEqual(send_receipt.get("outcome"), "turn_completed")
        wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "first prompt turn wake")
        self.assertEqual(len(self.endpoint.posts), 1, self.endpoint.posts)
        first_post = self.endpoint.posts[0]["body"]
        self.assertEqual(first_post.get("reason"), "all-idle")
        self.assertEqual(first_post.get("holder_instance_id"), holder_id)

        # During the autonomous continuation, the holder record and state must
        # report an active turn and busy last_prompt.mutation_status.
        def observe_busy() -> dict[str, Any] | None:
            record = self.holder_record()
            last = record.get("last_prompt") if isinstance(record.get("last_prompt"), dict) else {}
            if last.get("mutation_status") in ("in_progress", "accepted"):
                return record
            return None

        busy_record = wait_for(observe_busy, 5, "synthetic turn busy record")
        self.assertTrue(
            holder.seat_turn_blocks_all_idle(busy_record),
            f"seat_turn_blocks_all_idle must be True during continuation: {busy_record}",
        )
        self.assertNotEqual(
            (busy_record.get("last_prompt") or {}).get("mutation_status"),
            "completed",
        )

        # Wait for the quiet window to close the synthetic turn and deliver wake #2.
        def second_turn_ended() -> list[dict[str, Any]] | None:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            ended = [e for e in cap.get("events", []) if e.get("kind") == "turn_ended"]
            return ended if len(ended) >= 2 else None

        ended_events = wait_for(second_turn_ended, 10, "second turn_ended after continuation")
        assert ended_events is not None
        self.assertEqual(len(ended_events), 2, ended_events)
        self.assertEqual(ended_events[0].get("outcome"), "turn_completed")
        self.assertEqual(ended_events[1].get("outcome"), "agent_turn_completed")
        self.assertIsNone(ended_events[1].get("stop_reason"))
        self.assertEqual(ended_events[1].get("prompt_source"), "self")
        self.assertIs(ended_events[1].get("agent_initiated"), True)

        _, cap_all = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        started_events = [e for e in cap_all.get("events", []) if e.get("kind") == "turn_started"]
        self.assertEqual(len(started_events), 1, started_events)
        self.assertEqual(started_events[0].get("prompt_source"), "self")
        self.assertIs(started_events[0].get("agent_initiated"), True)

        # Record must now be back to completed / non-blocking.
        settled_record = self.holder_record()
        self.assertFalse(holder.seat_turn_blocks_all_idle(settled_record), settled_record)
        self.assertEqual(
            (settled_record.get("last_prompt") or {}).get("mutation_status"),
            "completed",
        )

        # Exactly ONE additional wake POST must arrive for the entire burst.
        wait_for(lambda: len(self.endpoint.posts) >= 2, 10, "second wake POST after continuation")
        time.sleep(0.4)
        self.assertEqual(len(self.endpoint.posts), 2, self.endpoint.posts)
        second_post = self.endpoint.posts[1]["body"]
        self.assertEqual(second_post.get("holder_instance_id"), holder_id)
        self.assertEqual(second_post.get("state"), "end_turn")
        self.assertIsNone(second_post.get("state_detail"))
        self.assertEqual(second_post.get("reason"), "all-idle")
        self.assertGreater(second_post.get("event_seq", 0), first_post.get("event_seq", 0))

    def test_case_b_holder_prompt_mid_continuation_no_double_turn_ended(self) -> None:
        """Case (b): a holder prompt or steer arriving mid-continuation behaves as
        send/steer does for an active turn today and never double-emits turn_ended.
        """
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        self.session = "grok-w341-orchestrator-b"
        cmd = self.autonomous_command(
            mode="mid_continuation", delay_ms=150, chunk_ms=120, chunks=5,
            steering="injected",
        )
        _, start_receipt = self.acp_custom("start", agent_cmd=cmd)
        self.assertEqual(start_receipt.get("session_role"), "host")

        _, send1 = self.acp_custom("send", "--text", "first prompt", "--wait", agent_cmd=cmd)
        self.assertEqual(send1.get("outcome"), "turn_completed")
        wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "wake #1")

        # Wait until the synthetic continuation turn is active.
        def continuation_active() -> dict[str, Any] | None:
            record = self.holder_record()
            return record if holder.seat_turn_blocks_all_idle(record) else None

        wait_for(continuation_active, 5, "continuation turn active")

        # 1. A concurrent `send` mid-continuation refuses with prompt-in-progress
        # just like an active prompt turn.
        _, refused_send = self.acp_custom(
            "send", "--text", "concurrent send", "--no-wait",
            agent_cmd=cmd, check=False,
        )
        self.assertEqual((refused_send.get("error") or {}).get("code"), "prompt-in-progress")
        self.assertIs(refused_send.get("mutation_performed"), False)

        # 2. `steer --delivery after-turn` queues cleanly for the end of the
        # active continuation turn.
        _, steer_receipt = self.acp_custom(
            "steer", "--text", "after continuation follow-up",
            "--delivery", "after-turn", agent_cmd=cmd,
        )
        self.assertEqual(steer_receipt.get("steer_outcome"), "queued", steer_receipt)

        # Wait for both the continuation turn and the queued follow-up prompt
        # turn to finish.
        def both_finished() -> list[dict[str, Any]] | None:
            if holder.seat_turn_blocks_all_idle(self.holder_record()):
                return None
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            ended = [e for e in cap.get("events", []) if e.get("kind") == "turn_ended"]
            return ended if len(ended) >= 3 else None

        ended = wait_for(both_finished, 12, "continuation + queued follow-up completion")
        assert ended is not None
        time.sleep(0.5)
        _, cap_final = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        ended_final = [e for e in cap_final.get("events", []) if e.get("kind") == "turn_ended"]
        # Exactly 3 turns total:
        #   1) prompt 1 -> turn_completed
        #   2) autonomous continuation -> agent_turn_completed (only ONE!)
        #   3) after-turn follow-up prompt -> turn_completed
        self.assertEqual(
            [e.get("outcome") for e in ended_final],
            ["turn_completed", "agent_turn_completed", "turn_completed"],
            ended_final,
        )

        # Also verify `steer --steer-mode interrupt` during a synthetic turn on
        # a fresh session cancels the synthetic turn once and runs the new prompt
        # without emitting a second turn_ended when the quiet timer expires.
        self.extra_sessions = [self.session]
        self.session = "grok-w341-worker-b-int"
        self.extra_sessions.append(self.session)
        _, _ = self.acp_custom("start", agent_cmd=cmd)
        _, _ = self.acp_custom("send", "--text", "start worker", "--wait", agent_cmd=cmd)
        wait_for(continuation_active, 5, "worker continuation active")
        _, int_receipt = self.acp_custom(
            "steer", "--text", "interrupt continuation",
            "--steer-mode", "interrupt", agent_cmd=cmd,
        )
        self.assertEqual(int_receipt.get("steer_outcome"), "interrupted_and_resent", int_receipt)
        wait_for(
            lambda: not holder.seat_turn_blocks_all_idle(self.holder_record()),
            10,
            "interrupted resend finished",
        )
        time.sleep(0.6)
        _, worker_cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        worker_ended = [e for e in worker_cap.get("events", []) if e.get("kind") == "turn_ended"]
        self.assertEqual(
            [e.get("outcome") for e in worker_ended],
            ["turn_completed", "turn_canceled", "turn_completed"],
            worker_ended,
        )

    def test_case_c_stray_and_usage_noise_does_not_wake(self) -> None:
        """Case (c): stray empty chunks, usage_update, mode/command updates, and
        foreign-session updates while idle never open a synthetic turn or wake.
        """
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        self.session = "grok-w341-orchestrator-c"
        cmd = self.autonomous_command(mode="noise_only", delay_ms=150)
        _, _ = self.acp_custom("start", agent_cmd=cmd)

        _, send1 = self.acp_custom("send", "--text", "only real turn", "--wait", agent_cmd=cmd)
        self.assertEqual(send1.get("outcome"), "turn_completed")
        wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "initial turn wake")
        self.assertEqual(len(self.endpoint.posts), 1)

        # Wait past the noise burst + quiet period.
        time.sleep(1.0)
        _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        events = cap.get("events", [])
        started = [e for e in events if e.get("kind") == "turn_started"]
        ended = [e for e in events if e.get("kind") == "turn_ended"]
        self.assertEqual(started, [], f"noise must not open a synthetic turn: {started}")
        self.assertEqual(len(ended), 1, f"noise must not emit a second turn_ended: {ended}")
        self.assertEqual(len(self.endpoint.posts), 1, f"noise must not wake: {self.endpoint.posts}")

    def test_attention_reason_and_unit_predicates_on_agent_initiated_turn(self) -> None:
        """Verify #302 wake reason mapping (e.g. question_waiting / delivery_review)
        and explicit idle signal handling for agent_turn_completed.
        """
        question = [{"kind": "decisions", "why": "host-decision"}]
        delivery = [{"kind": "tasks", "why": "awaiting-verdict"}]
        self.assertEqual(
            holder.delegator_turn_wake_reason(
                outcome="agent_turn_completed",
                stop_reason=None,
                prompt_source="self",
                self_continuing=False,
                stop_requested=False,
                attention_rows=question,
                staged_undelivered=False,
                live_seats=True,
            ),
            "question_waiting",
        )
        self.assertEqual(
            holder.delegator_turn_wake_reason(
                outcome="agent_turn_completed",
                stop_reason=None,
                prompt_source="self",
                self_continuing=False,
                stop_requested=False,
                attention_rows=delivery,
                staged_undelivered=False,
                live_seats=True,
            ),
            "delivery_review",
        )
        self.assertEqual(
            holder.delegator_turn_wake_reason(
                outcome="agent_turn_completed",
                stop_reason=None,
                prompt_source="self",
                self_continuing=False,
                stop_requested=False,
                attention_rows=None,
                staged_undelivered=False,
                live_seats=False,
            ),
            "all-idle",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
