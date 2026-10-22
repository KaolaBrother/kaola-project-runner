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
      not open a synthetic turn, do not emit turn_ended, and do not wake;
  (d) agent output streamed right after session/new (backend replay before any
      prompt, e.g. the ZCode app-server's [interaction-result] echo) does not
      open a synthetic turn and the first real prompt still completes;
  (e) chunks the agent emits after its prompt turn was canceled are a
      post-cancel tail, not an agent-initiated continuation: no synthetic
      turn, no extra wake;
  (f1) the ZCode bridge emits one usage_update{stopReason} when a backend
      turn terminal has no ACP prompt in flight (the holder's idle signal)
      and keeps the rid path byte-identical;
  (f2) that explicit idle signal closes the synthetic turn at once instead
      of waiting out the quiet window (run at KAOLA_ACP_AGENT_TURN_QUIET_
      SECONDS=30 so the effect is observable in seconds).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
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
        turn_ms=1500 if args.mode == "cancel_tail" else 40,
        flood_bytes=0,
        steering=args.steering,
    )
    orig_finish = agent.finish_turn
    orig_cancel = agent.on_cancel_notification
    orig_session_new = agent.on_session_new
    done_count = [0]
    continuation_canceled = threading.Event()

    def patched_cancel(params: dict[str, Any]) -> None:
        continuation_canceled.set()
        orig_cancel(params)
        if args.mode != "cancel_tail":
            return
        session_id = params.get("sessionId") or next(iter(agent.sessions), "")

        def tail_chunk() -> None:
            time.sleep(0.1)
            mock.message_chunk(session_id, "tail after cancel")

        threading.Thread(target=tail_chunk, daemon=True).start()

    agent.on_cancel_notification = patched_cancel

    def patched_session_new(request_id: Any, params: dict[str, Any]) -> None:
        orig_session_new(request_id, params)
        if args.mode != "pre_prompt_noise":
            return
        session_id = next(iter(agent.sessions), "")
        if not session_id:
            return

        def pre_prompt_replay() -> None:
            # The hermetic fake ZCode app-server replay: an [interaction-result]
            # echo and replayed context streamed before any prompt.
            time.sleep(max(args.delay_ms, 0) / 1000.0)
            mock.session_update(session_id, {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text",
                            "text": '[interaction-result] {"memoryEnabled": false}'},
            })
            mock.thought_chunk(session_id, "replayed thought")
            mock.session_update(session_id, {
                "sessionUpdate": "tool_call",
                "toolCallId": "tc-replay-1",
                "title": "replayed",
                "kind": "read",
                "status": "completed",
            })
            mock.session_update(session_id, {
                "sessionUpdate": "usage_update", "used": 512, "size": 128000,
            })

        threading.Thread(target=pre_prompt_replay, daemon=True).start()

    agent.on_session_new = patched_session_new

    def patched_finish(request_id: Any, stop: str = "end_turn") -> bool:
        ok = orig_finish(request_id, stop)
        if not ok:
            return False
        done_count[0] += 1
        if done_count[0] != 1:
            return True
        session_id = next(iter(agent.sessions), "")

        if args.mode in ("autonomous_burst", "mid_continuation", "pre_prompt_noise",
                         "explicit_idle"):
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
                if args.mode == "explicit_idle":
                    # The kaola-zcode-acp bridge frame for a backend turn
                    # terminal with no ACP prompt in flight: the holder's
                    # explicit idle signal.
                    mock.session_update(session_id, {
                        "sessionUpdate": "usage_update",
                        "stopReason": "end_turn",
                    })

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


def _deliver_children(repo_realpath: str) -> tuple:
    """(pid, cputime) for live ``delegator-webhook deliver`` children whose
    cwd is this fixture's repo — the wake delivery's mid-flight observable
    (Issue #405). Other suites' children share the argv but not the cwd."""
    try:
        out = subprocess.run(["ps", "-eo", "pid=,time=,args="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ()
    children = []
    for line in out.splitlines():
        if "delegator-webhook deliver" not in line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        try:
            cwd = subprocess.run(["lsof", "-a", "-p", parts[0], "-d", "cwd", "-Fn"],
                                 capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        if f"n{repo_realpath}" not in cwd:
            continue
        children.append((int(parts[0]), parts[1]))
    return tuple(sorted(children))


class AgentInitiatedTurnTest(unittest.TestCase):
    """End-to-end and unit coverage for Issue #341 agent-initiated turns.

    Unique coverage (Issue #405): a synthetic turn on agent-initiated
    session/update activity while idle, its quiet-window or explicit
    idle-signal close, and exactly-one Delegator wake per episode.

    Load sensitivity: every producer hop is a separate process — the mock
    ACP agent, the out-of-process holder, its deliver child, and the
    ``kaola-acp`` CLI calls inside predicates — so machine load stretches
    the chain to seconds per hop while it keeps making progress. The waits
    therefore synchronize on observable conditions (``wait_for`` below):
    their numeric budget is a stall watchdog reset by any change in
    ``_wait_probe``, not a wall-clock window the event must fit inside;
    a wall bound remains only as the hang backstop. ``wait_stable`` is the
    event-driven form of a settle sleep for negative assertions: it ends
    on real quiet, not a guessed window.
    """

    setUp = issue302.issue299.WebhookCase.setUp
    env = issue302.issue299.WebhookCase.env
    holder_record = issue302.issue299.WebhookCase.holder_record
    write_config = issue302.issue299.WebhookCase.write_config
    posts_for = issue302.WakeGate.posts_for
    write_heartbeat = issue302.WakeGate.write_heartbeat
    configure_endpoint = issue302.WakeGate.configure_endpoint

    def _wait_probe(self) -> tuple:
        """The fixture's observable signature for stall detection: every file
        under the sandbox root (holder ``record.json``/``events.jsonl``,
        webhook receipts, the heartbeat prompt, endpoint-facing state) plus
        the in-process endpoint post count — and, at most once a second, the
        live wake ``deliver`` children for this fixture's repo.

        The deliver child is a spawned ``kaola-acp.py delegator-webhook
        deliver`` whose only fixture-visible writes (the POST, the receipt)
        appear at completion; under load its interpreter boot and module
        init can exceed the stall budget while it writes nothing. Its (pid,
        CPU) pair is the only mid-flight progress surface — a working child
        advances CPU, a hung one does not, a dead one disappears."""
        signature: list = [len(self.endpoint.posts) if self.endpoint else 0]
        if self.root.is_dir():
            for path in sorted(self.root.rglob("*")):
                try:
                    st = path.stat()
                except OSError:
                    continue
                signature.append((str(path), st.st_size, st.st_mtime_ns))
        now = time.monotonic()
        if now - getattr(self, "_probe_ps_at", 0.0) >= 1.0:
            self._probe_ps_at = now
            self._probe_ps = _deliver_children(self.project)
        signature.append(getattr(self, "_probe_ps", ()))
        return tuple(signature)

    def wait_for(self, predicate, timeout: float, label: str,
                 interval: float = 0.05):
        """Wait on the observable condition, not a wall window (Issue #405)."""
        return wait_for(predicate, timeout, label, interval,
                        probe=self._wait_probe)

    def wait_stable(self, seconds: float) -> None:
        """Wait until nothing observable has changed for ``seconds`` — the
        event-driven form of a settle sleep for 'nothing more arrives'
        assertions: a late event extends the window instead of passing it.
        An absolute ceiling of ``max(6 * seconds, 10)`` stays as the hang
        watchdog for a fixture that never goes quiet."""
        signature = self._wait_probe()
        quiet_since = time.monotonic()
        deadline = quiet_since + max(6 * seconds, 10.0)
        while time.monotonic() - quiet_since < seconds:
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"no observable quiet for {seconds:g}s "
                    f"within {max(6 * seconds, 10.0):g}s")
            time.sleep(0.05)
            current = self._wait_probe()
            if current != signature:
                signature = current
                quiet_since = time.monotonic()

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
        self.wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "first prompt turn wake")
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

        busy_record = self.wait_for(observe_busy, 5, "synthetic turn busy record")
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

        ended_events = self.wait_for(second_turn_ended, 10, "second turn_ended after continuation")
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
        self.wait_for(lambda: len(self.endpoint.posts) >= 2, 10, "second wake POST after continuation")
        self.wait_stable(0.4)
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
        self.wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "wake #1")

        # Wait until the synthetic continuation turn is active.
        def continuation_active() -> dict[str, Any] | None:
            record = self.holder_record()
            return record if holder.seat_turn_blocks_all_idle(record) else None

        self.wait_for(continuation_active, 5, "continuation turn active")

        # 1. A concurrent `send` mid-continuation refuses with prompt-in-progress
        # just like an active prompt turn.
        _, refused_send = self.acp_custom(
            "send", "--text", "concurrent send", "--no-wait",
            agent_cmd=cmd, check=False,
        )
        self.assertEqual((refused_send.get("error") or {}).get("code"), "prompt-in-progress")
        self.assertEqual(refused_send.get("outcome"), "refused_busy")
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

        ended = self.wait_for(both_finished, 12, "continuation + queued follow-up completion")
        assert ended is not None
        self.wait_stable(0.5)
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
        # The queued steer really reached the agent once the synthetic turn
        # closed.
        followups = [
            e for e in cap_final.get("events", []) if e.get("kind") == "steer_followup"
        ]
        self.assertTrue(followups, cap_final.get("events", []))
        self.assertIs(
            (followups[-1].get("receipt") or {}).get("mutation_performed"),
            True,
            followups,
        )

        # Also verify `steer --steer-mode interrupt` during a synthetic turn on
        # a fresh session cancels the synthetic turn once and runs the new prompt
        # without emitting a second turn_ended when the quiet timer expires.
        self.extra_sessions = [self.session]
        self.session = "grok-w341-worker-b-int"
        self.extra_sessions.append(self.session)
        _, _ = self.acp_custom("start", agent_cmd=cmd)
        _, _ = self.acp_custom("send", "--text", "start worker", "--wait", agent_cmd=cmd)
        self.wait_for(continuation_active, 5, "worker continuation active")
        _, int_receipt = self.acp_custom(
            "steer", "--text", "interrupt continuation",
            "--steer-mode", "interrupt", agent_cmd=cmd,
        )
        self.assertEqual(int_receipt.get("steer_outcome"), "interrupted_and_resent", int_receipt)
        self.wait_for(
            lambda: not holder.seat_turn_blocks_all_idle(self.holder_record()),
            10,
            "interrupted resend finished",
        )
        self.wait_stable(0.6)
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
        self.wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "initial turn wake")
        self.assertEqual(len(self.endpoint.posts), 1)

        # Wait for the whole noise burst to be observed (its last update is
        # the session_info_update), not for a guessed window — then settle.
        def noise_delivered() -> bool:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            return any(
                e.get("kind") == "session_update"
                and isinstance(e.get("update"), dict)
                and e["update"].get("sessionUpdate") == "session_info_update"
                for e in cap.get("events", [])
            ) or None

        self.wait_for(noise_delivered, 10, "the full noise burst delivered")
        self.wait_stable(0.6)
        _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        events = cap.get("events", [])
        started = [e for e in events if e.get("kind") == "turn_started"]
        ended = [e for e in events if e.get("kind") == "turn_ended"]
        self.assertEqual(started, [], f"noise must not open a synthetic turn: {started}")
        self.assertEqual(len(ended), 1, f"noise must not emit a second turn_ended: {ended}")
        self.assertEqual(len(self.endpoint.posts), 1, f"noise must not wake: {self.endpoint.posts}")

    def _chunk_texts(self, events: list[dict[str, Any]]) -> list[str]:
        texts = []
        for event in events:
            update = event.get("update")
            if not isinstance(update, dict):
                continue
            content = update.get("content")
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
        return texts

    def test_case_d_pre_prompt_output_does_not_open_turn(self) -> None:
        """Case (d): agent output streamed right after session/new (backend
        replay before any prompt) must not open a synthetic turn, and the
        first real prompt must still complete instead of refusing
        prompt-in-progress.
        """
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        self.session = "grok-w341-orchestrator-d"
        cmd = self.autonomous_command(mode="pre_prompt_noise", delay_ms=300)
        _, start_receipt = self.acp_custom("start", agent_cmd=cmd)
        self.assertEqual(start_receipt.get("session_role"), "host")

        def replay_seen() -> bool:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            return any(
                "[interaction-result]" in text
                for text in self._chunk_texts(cap.get("events", []))
            ) or None

        self.wait_for(replay_seen, 8, "pre-prompt replay update captured")

        # Wait for the replay's last update (usage_update used=512), not a
        # guessed window — then settle past the quiet period.
        def replay_done() -> bool:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            return any(
                e.get("kind") == "session_update"
                and isinstance(e.get("update"), dict)
                and e["update"].get("sessionUpdate") == "usage_update"
                and e["update"].get("used") == 512
                for e in cap.get("events", [])
            ) or None

        self.wait_for(replay_done, 8, "the full pre-prompt replay delivered")
        self.wait_stable(0.6)
        _, cap_idle = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        idle_events = cap_idle.get("events", [])
        self.assertEqual(
            [e for e in idle_events if e.get("kind") == "turn_started"], [],
            idle_events,
        )
        self.assertEqual(
            [e for e in idle_events if e.get("kind") == "turn_ended"], [],
            idle_events,
        )
        self.assertEqual(self.endpoint.posts, [], self.endpoint.posts)

        # The first real prompt must complete (this regressed: the replay
        # opened a synthetic turn and send refused prompt-in-progress).
        _, send1 = self.acp_custom("send", "--text", "kickoff", "--wait", agent_cmd=cmd)
        self.assertEqual(send1.get("outcome"), "turn_completed", send1)
        self.wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "first prompt wake")

        # The autonomous continuation after prompt 1 still opens exactly one
        # synthetic turn.
        def second_ended() -> list[dict[str, Any]] | None:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            ended = [e for e in cap.get("events", []) if e.get("kind") == "turn_ended"]
            return ended if len(ended) >= 2 else None

        ended_events = self.wait_for(second_ended, 12, "synthetic turn_ended after kickoff")
        assert ended_events is not None
        self.assertEqual(
            [e.get("outcome") for e in ended_events],
            ["turn_completed", "agent_turn_completed"],
            ended_events,
        )
        _, cap_all = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        started = [e for e in cap_all.get("events", []) if e.get("kind") == "turn_started"]
        self.assertEqual(len(started), 1, started)
        self.assertEqual(started[0].get("prompt_source"), "self")
        self.assertIs(started[0].get("agent_initiated"), True)
        self.wait_for(lambda: len(self.endpoint.posts) >= 2, 10, "second wake after continuation")
        self.wait_stable(0.4)
        self.assertEqual(len(self.endpoint.posts), 2, self.endpoint.posts)

    def test_case_e_tail_after_canceled_turn_does_not_open_turn(self) -> None:
        """Case (e): with turn_ms=1500 the mock's prompt thread is still
        sleeping when the turn is canceled; the chunks it emits afterwards are
        a post-cancel tail, not an agent-initiated continuation.
        """
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        self.session = "grok-w341-orchestrator-e"
        cmd = self.autonomous_command(mode="cancel_tail")
        _, _ = self.acp_custom("start", agent_cmd=cmd)

        _, send1 = self.acp_custom("send", "--text", "first", "--wait", agent_cmd=cmd)
        self.assertEqual(send1.get("outcome"), "turn_completed")
        self.wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "first turn wake")

        _, send2 = self.acp_custom("send", "--text", "slow", "--no-wait", agent_cmd=cmd)
        self.assertNotIn("error", send2, send2)
        self.wait_for(
            lambda: holder.seat_turn_blocks_all_idle(self.holder_record()),
            5, "slow turn active",
        )
        _, cancel = self.acp_custom("cancel", "--timeout", "10", agent_cmd=cmd)
        self.assertNotIn("error", cancel, cancel)

        def turn_canceled() -> bool:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            return any(
                e.get("kind") == "turn_ended" and e.get("outcome") == "turn_canceled"
                for e in cap.get("events", [])
            ) or None

        self.wait_for(turn_canceled, 10, "turn_canceled turn_ended")
        self.wait_stable(0.5)  # let the cancel wake settle
        settled_posts = len(self.endpoint.posts)

        # Wait for the mock's post-cancel tail itself (observed, not a guessed
        # window: the tail thread emits it after the sleeping prompt thread),
        # then settle past the quiet window.
        def tail_delivered() -> bool:
            _, cap = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
            return "tail after cancel" in self._chunk_texts(cap.get("events", [])) or None

        self.wait_for(tail_delivered, 10, "the post-cancel tail chunk")
        self.wait_stable(0.6)
        _, cap_final = self.acp_custom("capture", "--since", "0", agent_cmd=cmd)
        events = cap_final.get("events", [])
        ended = [e for e in events if e.get("kind") == "turn_ended"]
        self.assertEqual(
            [e.get("outcome") for e in ended],
            ["turn_completed", "turn_canceled"],
            ended,
        )
        started = [e for e in events if e.get("kind") == "turn_started"]
        self.assertEqual(started, [], f"post-cancel tail must not open a turn: {started}")
        self.assertEqual(
            len(self.endpoint.posts), settled_posts,
            f"post-cancel tail must not wake: {self.endpoint.posts}",
        )
        self.assertIn(
            "tail after cancel", self._chunk_texts(events),
            "the post-cancel tail must have really arrived",
        )

    def test_agent_turn_quiet_window_defaults(self) -> None:
        """Issue #341: the synthetic-turn quiet window defaults to 60 s with a
        600 s cap; the env override still wins inside the cap.
        """
        quiet = holder.Holder._agent_turn_quiet_seconds
        self.assertEqual(holder.AGENT_TURN_QUIET_DEFAULT, 60.0)
        self.assertEqual(holder.AGENT_TURN_QUIET_MAX, 600.0)
        saved = dict(os.environ)
        try:
            os.environ.pop("KAOLA_ACP_AGENT_TURN_QUIET_SECONDS", None)
            self.assertEqual(quiet(None), 60.0)
            os.environ["KAOLA_ACP_AGENT_TURN_QUIET_SECONDS"] = "0.45"
            self.assertEqual(quiet(None), 0.45)
            os.environ["KAOLA_ACP_AGENT_TURN_QUIET_SECONDS"] = "601"
            self.assertEqual(quiet(None), 60.0)
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_case_f1_bridge_emits_idle_signal_for_promptless_turn(self) -> None:
        """Case (f1): a backend turn terminal with no ACP prompt in flight
        (rid None) emits one usage_update{stopReason} — the holder's idle
        signal — while the rid path stays byte-identical.
        """
        spec = importlib.util.spec_from_file_location(
            "zcode_bridge_341", REPO / "scripts" / "kaola-zcode-acp.py")
        assert spec is not None and spec.loader is not None
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)

        agent = bridge.ZCodeAcpAgent("entry", "node", "/tmp", "yolo")
        sent: list[dict[str, Any]] = []
        agent.send = sent.append
        session = bridge.Session("acp-1", "/tmp", "yolo")

        def updates() -> list[dict[str, Any]]:
            return [
                m["params"]["update"] for m in sent
                if m.get("method") == "session/update"
            ]

        usage = {"inputTokens": 11, "outputTokens": 7, "totalTokens": 18}

        # rid None: turn.completed emits usage first, then the idle signal.
        self.assertIsNone(session.turn_request_id)
        agent.translate_event(session, "turn.completed", {"usage": usage})
        self.assertEqual(updates(), [
            {"sessionUpdate": "usage_update", "usage": usage},
            {"sessionUpdate": "usage_update", "stopReason": "end_turn"},
        ])
        self.assertEqual([m for m in sent if "id" in m], [], sent)
        sent.clear()

        # turn.terminal: exactly the idle signal.
        agent.translate_event(session, "turn.terminal", {"reason": "stopped"})
        self.assertEqual(updates(), [
            {"sessionUpdate": "usage_update", "stopReason": "end_turn"},
        ])
        sent.clear()

        # turn.failed: the failure chunk, then the refusal idle signal.
        agent.translate_event(session, "turn.failed",
                              {"error": {"code": 1308, "message": "boom"}})
        self.assertEqual(updates(), [
            {"sessionUpdate": "agent_message_chunk",
             "content": {"type": "text", "text": "[zcode turn failed] boom"}},
            {"sessionUpdate": "usage_update", "stopReason": "refusal"},
        ])
        sent.clear()

        # rid set: the normal prompt path is unchanged — usage update plus the
        # response carrying stopReason and usage, no stopReason update.
        session.turn_request_id = 7
        agent.translate_event(session, "turn.completed", {"usage": usage})
        self.assertEqual(updates(), [
            {"sessionUpdate": "usage_update", "usage": usage},
        ])
        self.assertEqual(
            [m for m in sent if "result" in m],
            [{"jsonrpc": "2.0", "id": 7,
              "result": {"stopReason": "end_turn", "usage": usage}}],
            sent,
        )
        self.assertIsNone(session.turn_request_id)

    def test_case_f2_explicit_idle_signal_closes_synthetic_turn(self) -> None:
        """Case (f2): the bridge's usage_update{stopReason} idle signal closes
        the synthetic turn at once. The quiet window is set to 30 s, so a
        close within seconds proves the signal was honored, not the timeout.
        """
        self.endpoint = issue302.Endpoint()
        self.configure_endpoint()
        self.session = "grok-w341-orchestrator-f"
        cmd = self.autonomous_command(
            mode="explicit_idle", delay_ms=150, chunk_ms=60, chunks=3,
        )
        env = {"KAOLA_ACP_AGENT_TURN_QUIET_SECONDS": "30"}
        _, _ = self.acp_custom("start", agent_cmd=cmd, extra_env=env)

        _, send1 = self.acp_custom(
            "send", "--text", "kickoff", "--wait", agent_cmd=cmd, extra_env=env)
        self.assertEqual(send1.get("outcome"), "turn_completed")
        self.wait_for(lambda: len(self.endpoint.posts) >= 1, 10, "first prompt wake")

        def second_ended() -> list[dict[str, Any]] | None:
            _, cap = self.acp_custom(
                "capture", "--since", "0", agent_cmd=cmd, extra_env=env)
            ended = [e for e in cap.get("events", []) if e.get("kind") == "turn_ended"]
            return ended if len(ended) >= 2 else None

        ended_events = self.wait_for(second_ended, 10, "synthetic turn_ended")
        assert ended_events is not None
        self.assertEqual(
            [e.get("outcome") for e in ended_events],
            ["turn_completed", "agent_turn_completed"],
            ended_events,
        )
        self.assertEqual(ended_events[1].get("stop_reason"), "end_turn")
        self.assertEqual(ended_events[1].get("prompt_source"), "self")
        self.assertIs(ended_events[1].get("agent_initiated"), True)

        _, cap_all = self.acp_custom(
            "capture", "--since", "0", agent_cmd=cmd, extra_env=env)
        events = cap_all.get("events", [])
        started = [e for e in events if e.get("kind") == "turn_started"]
        self.assertEqual(len(started), 1, started)
        self.assertEqual(started[0].get("prompt_source"), "self")
        self.assertIs(started[0].get("agent_initiated"), True)

        stop_updates = [
            e for e in events
            if e.get("kind") == "session_update"
            and isinstance(e.get("update"), dict)
            and e["update"].get("stopReason") == "end_turn"
        ]
        self.assertTrue(stop_updates, events[-8:])
        delta = ended_events[1].get("ts", 0) - stop_updates[-1].get("ts", 0)
        self.assertLess(
            delta, 2.0,
            f"turn_ended must follow the idle signal, not the 30 s quiet "
            f"window (delta={delta:.3f}s)",
        )

        self.wait_for(lambda: len(self.endpoint.posts) >= 2, 10, "second wake")
        self.wait_stable(1.0)
        _, cap2 = self.acp_custom(
            "capture", "--since", "0", agent_cmd=cmd, extra_env=env)
        self.assertEqual(
            len([e for e in cap2.get("events", []) if e.get("kind") == "turn_ended"]),
            2,
        )
        self.assertEqual(len(self.endpoint.posts), 2, self.endpoint.posts)

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
