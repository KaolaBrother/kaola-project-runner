#!/usr/bin/env python3
"""Issue #302: wake the Delegator only when it must act, and never twice.

Extends the #299 webhook harness. The endpoint is a loopback http.server.
KAOLA_DELEGATOR_WEBHOOK_CONFIG and HOME stay on temp paths.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ISSUE299 = REPO / "tests" / "contract" / "test-issue-299-delegator-webhook.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"

spec = importlib.util.spec_from_file_location("issue299_webhook", ISSUE299)
issue299 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue299)

holder_spec = importlib.util.spec_from_file_location("kaola_acp_holder_302", HOLDER)
holder = importlib.util.module_from_spec(holder_spec)
assert holder_spec.loader is not None
holder_spec.loader.exec_module(holder)

wait_for = issue299.wait_for
Endpoint = issue299.Endpoint
PAYLOAD_KEYS = issue299.PAYLOAD_KEYS


def host_view(rows: list) -> str:
    return json.dumps({"view": "host", "attention": rows}, separators=(",", ":"))


class Predicate(unittest.TestCase):
    """The pure holder-side mapping. Integration tests cover the wiring."""

    def reason(self, **kwargs):
        base = dict(
            outcome="turn_completed",
            stop_reason="end_turn",
            prompt_source="self",
            self_continuing=False,
            stop_requested=False,
            attention_rows=None,
            staged_undelivered=False,
            live_seats=True,
        )
        base.update(kwargs)
        return holder.delegator_turn_wake_reason(**base)

    def test_mapping(self) -> None:
        question = [{"kind": "decisions", "why": "host-decision"}]
        delivery = [{"kind": "tasks", "why": "awaiting-verdict"}]
        other = [{"kind": "holds", "why": "host-owned"}]
        cases = [
            ({}, None),
            ({"prompt_source": "delegator"}, None),
            ({"prompt_source": "delegator", "attention_rows": question}, None),
            ({"self_continuing": True, "stop_reason": "max_tokens"}, None),
            ({"stop_reason": "max_tokens"}, "host_stopped_pending"),
            ({"stop_reason": "max_turn_requests"}, "host_stopped_pending"),
            ({"stop_reason": "length"}, "host_stopped_pending"),
            ({"staged_undelivered": True}, "host_stopped_pending"),
            ({"attention_rows": question}, "question_waiting"),
            ({"attention_rows": question + delivery}, "question_waiting"),
            ({"attention_rows": delivery}, "delivery_review"),
            ({"attention_rows": [{"kind": "tasks", "why": "delivery-open"}]},
             "delivery_review"),
            ({"attention_rows": [{"kind": "tasks", "why": "verdict-missing"}]},
             "delivery_review"),
            ({"attention_rows": other}, "needs_decision"),
            ({"stop_reason": "refusal"}, "needs_decision"),
            ({"outcome": "turn_canceled", "stop_reason": None}, "needs_decision"),
            ({"outcome": "turn_canceled", "stop_requested": True}, None),
            ({"outcome": "turn_failed"}, None),
            ({"prompt_source": "delegator", "stop_reason": "max_tokens"}, None),
            # Owner rule 2026-10-11 16:49: nobody left working wakes all-idle
            # even when pending attention is recorded. all_idle_due defaults
            # true, so a Delegator turn whose episode latch is still clear
            # reports the one transition. Issue #307: once this episode has
            # sent all-idle, a Delegator turn returns None. A self turn still
            # names all-idle; the emit latch drops the duplicate POST.
            # A live seat with nothing owed stays quiet. A Host that already
            # continued does not wake.
            ({"live_seats": False}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator"}, "all-idle"),
            ({"live_seats": False, "attention_rows": question,
              "prompt_source": "delegator"}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator",
              "all_idle_due": True}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator",
              "stop_reason": "max_tokens", "all_idle_due": True}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator",
              "stop_reason": "refusal", "all_idle_due": False}, None),
            ({"live_seats": False, "prompt_source": "delegator",
              "all_idle_due": False}, None),
            ({"live_seats": False, "attention_rows": question,
              "prompt_source": "delegator", "all_idle_due": False}, None),
            ({"live_seats": False, "prompt_source": "self",
              "all_idle_due": False}, "all-idle"),
            ({"live_seats": False, "stop_reason": "max_tokens"}, "all-idle"),
            ({"live_seats": False, "self_continuing": True}, None),
            ({"live_seats": False, "self_continuing": True,
              "prompt_source": "delegator", "all_idle_due": True}, None),
            ({"live_seats": False, "outcome": "turn_canceled",
              "stop_requested": True}, None),
        ]
        for kwargs, expected in cases:
            self.assertEqual(self.reason(**kwargs), expected, kwargs)


class WakeGate(issue299.WebhookCase):
    def mock_command(self, scenario: str = "normal", turn_ms: int = 0) -> str:
        command = super().mock_command(scenario)
        if turn_ms:
            command += f" --turn-ms {int(turn_ms)}"
        return command

    def acp(self, command: str, *args: str, check: bool = True,
            timeout: float = 60, scenario: str = "normal",
            turn_ms: int = 0, extra_env: dict | None = None):
        argv = [sys.executable, str(issue299.CLI), "grok", command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", self.mock_command(scenario, turn_ms), *args]
        proc = subprocess.run(argv, capture_output=True, text=True,
                              env=self.env(extra_env), timeout=timeout)
        try:
            receipt = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command} not JSON: {proc.stdout!r} "
                      f"stderr={proc.stderr!r}")
        if check:
            self.assertNotIn("error", receipt,
                             f"{command} failed: {receipt.get('error')}")
            self.assertNotEqual(receipt.get("result"), "refused",
                                f"{command} refused: {receipt}")
        return proc.returncode, receipt

    def tearDown(self) -> None:
        names: list[str] = []
        for name in list(getattr(self, "extra_sessions", []) or []):
            if name and name not in names:
                names.append(name)
        worker = getattr(self, "worker", None)
        if worker and worker not in names:
            names.append(worker)
        current = self.session
        for name in names:
            if name == current:
                continue
            self.session = name
            self.acp("stop", "--force", check=False, timeout=30)
        self.session = current
        self.worker = None
        self.extra_sessions = []
        super().tearDown()

    def start_host(self, suffix: str, scenario: str = "normal",
                   turn_ms: int = 0) -> str:
        self.host_session = f"grok-w302-orchestrator-{suffix}"
        self.session = self.host_session
        _, receipt = self.acp("start", scenario=scenario, turn_ms=turn_ms)
        self.assertEqual(receipt.get("session_role"), "host", receipt)
        return self.session

    def start_worker(self, suffix: str, scenario: str = "normal") -> str:
        self.worker = f"grok-i302-worker-{suffix}"
        host = self.session
        _, status = self.acp("status")
        holder_id = status.get("holder_instance_id")
        self.assertIsInstance(holder_id, str, status)
        self.session = self.worker
        # The Host counts a live seat from holders whose record names it as
        # dispatcher. The heartbeat target and the dispatcher must name the
        # same Host or start refuses the binding.
        _, receipt = self.acp("start", scenario=scenario, extra_env={
            "KAOLA_ACP_HEARTBEAT_HOST": json.dumps({
                "platform": "grok", "session": host, "repo": str(self.repo),
            }),
            "KAOLA_ACP_DISPATCHER": json.dumps({
                "holder_instance_id": holder_id,
                "platform": "grok",
                "session": host,
                "repo": str(self.repo),
            }),
        })
        self.assertNotEqual(receipt.get("session_role"), "host", receipt)
        record = self.holder_record()
        self.assertEqual(
            (record.get("dispatcher") or {}).get("holder_instance_id"), holder_id,
            record.get("dispatcher"))
        self.session = host
        return self.worker

    def start_sideagent(self, suffix: str) -> str:
        """A live Sideagent whose record names the current Host as dispatcher.

        The session name is not a Host name. ``--role sideagent`` is what
        keeps it out of the live-seat scan.
        """
        node = f"grok-i305-node-{suffix}"
        self.worker = node
        host = self.session
        _, status = self.acp("status")
        holder_id = status.get("holder_instance_id")
        self.assertIsInstance(holder_id, str, status)
        self.session = node
        _, receipt = self.acp("start", "--role", "sideagent", extra_env={
            "KAOLA_ACP_HEARTBEAT_HOST": json.dumps({
                "platform": "grok", "session": host, "repo": str(self.repo),
            }),
            "KAOLA_ACP_DISPATCHER": json.dumps({
                "holder_instance_id": holder_id,
                "platform": "grok",
                "session": host,
                "repo": str(self.repo),
            }),
        })
        self.assertEqual(receipt.get("session_role"), "sideagent", receipt)
        record = self.holder_record()
        self.assertEqual(record.get("session_role"), "sideagent", record)
        self.assertEqual(
            (record.get("dispatcher") or {}).get("holder_instance_id"), holder_id,
            record.get("dispatcher"))
        self.session = host
        return node

    @contextmanager
    def webhook_process_env(self):
        """The in-process holder spawns deliver with the test process environment."""
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
        """A Host holder whose last turn already ended, with no all-idle sent."""
        digest = hashlib.sha256(self.project.encode()).hexdigest()[:16]
        session = f"grok-w305-orchestrator-{suffix}"
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

    def end_turn_wake(self, host, prompt_source: str) -> str | None:
        """The production turn-end wake branch, for one already-ended turn."""
        host.turn["active"] = False
        host.turn["outcome"] = "turn_completed"
        host.turn["stop_reason"] = "end_turn"
        host.turn["prompt_source"] = prompt_source
        host._delegator_followups = 0
        reason = host._delegator_turn_end_reason(host.turn)
        if reason == "all-idle":
            host._emit_delegator_all_idle("end_turn", "end_turn")
        elif reason is not None:
            host._delegator_wake("end_turn", "end_turn", reason)
        return reason

    def event_rows(self, host) -> list[dict]:
        path = Path(host.record_dir) / "events.jsonl"
        rows = []
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def posts_for(self, holder_id: str, reason: str = "all-idle") -> list[dict]:
        return [post for post in (self.endpoint.posts if self.endpoint else [])
                if (post["body"] or {}).get("reason") == reason
                and (post["body"] or {}).get("holder_instance_id") == holder_id]

    def spawn_seat(self, session: str, role: str, state: str, dispatcher_id: str):
        """A live process whose argv matches the holder scan, plus its record."""
        digest = hashlib.sha256(self.project.encode()).hexdigest()[:16]
        record_dir = self.record_root / "grok" / session / digest
        record_dir.mkdir(parents=True)
        sock = self.root / f"{session}.sock"
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)",
             "kaola-acp-holder", "--record-dir", str(record_dir),
             "--socket", str(sock)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        record = {
            "holder_pid": proc.pid,
            "session": session,
            "session_role": role,
            "state": state,
            "dispatcher": {"holder_instance_id": dispatcher_id},
        }
        (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
        return proc, record_dir

    def write_heartbeat(self, body: str) -> None:
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"body": body}), encoding="utf-8")

    def session_events(self, session: str) -> list[dict]:
        base = self.record_root / "grok" / session
        rows: list[dict] = []
        if not base.exists():
            return rows
        for path in sorted(base.rglob("events.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def delivered_count(self, session: str) -> int:
        return sum(1 for event in self.session_events(session)
                   if event.get("kind") == "worker_event_delivered")

    def posts_with_reason(self, reason: str) -> list[dict]:
        return [post for post in (self.endpoint.posts if self.endpoint else [])
                if (post["body"] or {}).get("reason") == reason]

    def signal(self, **overrides) -> dict:
        payload = {
            "schema": "kaola-delegator-wake/1", "project": self.project,
            "session": "s1", "holder_instance_id": "h-302", "event_seq": 7,
            "state": "stopped", "state_detail": "exact_stop",
            "reason": "exact_stop", "ts": "2026-01-01T00:00:00Z",
        }
        payload.update(overrides)
        return payload

    def configure_endpoint(self, url: str | None = None) -> None:
        self.write_config({self.project: {
            "url": url or self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})

    def test_slow_endpoint_delivers_once(self) -> None:
        self.endpoint = Endpoint(sleep_seconds=4.0)
        self.configure_endpoint()
        proc = self.deliver(self.signal(event_seq=1), timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.endpoint.posts), 1)
        self.assertEqual(len(self.receipts()), 1)
        receipt = self.receipts()[0]
        self.assertEqual(receipt["result"], "delivered")
        self.assertEqual(receipt["reason"], "exact_stop")
        self.assertNotIn("skip_reason", receipt)
        self.assertEqual(receipt["attempt"], 1)
        self.assertIs(receipt["final"], True)
        self.assertIsNone(receipt["error"])
        self.assertGreaterEqual(receipt["elapsed_ms"], 3000)
        self.assertEqual(self.endpoint.posts[0]["body"]["reason"], "exact_stop")

    def test_timeout_does_not_retry(self) -> None:
        self.endpoint = Endpoint(sleep_seconds=13.0)
        self.configure_endpoint()
        proc = self.deliver(self.signal(event_seq=2), timeout=30)
        self.assertNotEqual(proc.returncode, 0)
        time.sleep(2.5)
        self.assertEqual(len(self.endpoint.posts), 1)
        receipts = self.receipts()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["error"], "timeout")
        self.assertEqual(receipts[0]["reason"], "exact_stop")
        self.assertNotIn("skip_reason", receipts[0])
        self.assertEqual(receipts[0]["attempt"], 1)
        self.assertIs(receipts[0]["final"], True)
        time.sleep(1.0)
        self.assertEqual(len(self.endpoint.posts), 1)

    def test_connection_and_status_retries(self) -> None:
        self.endpoint = Endpoint()
        closed = issue299.socket_probe_closed_port()
        self.configure_endpoint(f"http://127.0.0.1:{closed}/hook")
        proc = self.deliver(self.signal(event_seq=3), timeout=30)
        self.assertNotEqual(proc.returncode, 0)
        connection = self.receipts()
        self.assertEqual(len(connection), 4)
        self.assertTrue(all(item["error"] == "connection" for item in connection))
        self.assertTrue(all(item["reason"] == "exact_stop" for item in connection))
        self.assertIs(connection[0]["final"], False)
        self.assertIs(connection[-1]["final"], True)

        for code, attempts in ((500, 4), (408, 4), (429, 4), (400, 1)):
            self.endpoint.posts.clear()
            self.configure_endpoint(f"http://127.0.0.1:{self.endpoint.port}/status/{code}")
            proc = self.deliver(self.signal(event_seq=10 + code), timeout=30)
            self.assertNotEqual(proc.returncode, 0)
            matching = [item for item in self.receipts()
                        if item.get("event_seq") == 10 + code]
            self.assertEqual(len(matching), attempts, code)
            self.assertTrue(all(item["http_status"] == code for item in matching))
            self.assertEqual(len(self.endpoint.posts), attempts, code)
            self.assertIs(matching[-1]["final"], True)
            if attempts > 1:
                self.assertIs(matching[0]["final"], False)

    def test_duplicate_event_posts_once_and_recovery_seq_does_not(self) -> None:
        self.endpoint = Endpoint(sleep_seconds=0.4)
        self.configure_endpoint()
        payload = self.signal(holder_instance_id="holder-a", event_seq=4)
        procs = []
        for _ in range(2):
            procs.append(subprocess.Popen(
                [sys.executable, str(issue299.CLI), "delegator-webhook", "deliver"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=self.env()))
        for proc in procs:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(payload).encode())
            proc.stdin.close()
        for proc in procs:
            proc.communicate(timeout=20)
        self.assertEqual(len(self.endpoint.posts), 1)
        skipped = [item for item in self.receipts()
                   if item.get("skip_reason") == "duplicate"]
        self.assertEqual(len(skipped), 1)
        self.assertNotIn("reason", skipped[0])
        self.assertEqual(skipped[0]["attempt"], 0)
        self.assertEqual(skipped[0]["result"], "skipped")
        self.assertIs(skipped[0]["final"], True)
        delivered = [item for item in self.receipts()
                     if item.get("result") == "delivered"]
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]["reason"], "exact_stop")
        self.assertNotIn("skip_reason", delivered[0])
        # A later event_seq for the same holder is a different event.
        proc = self.deliver(self.signal(holder_instance_id="holder-a", event_seq=5),
                            timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.endpoint.posts), 2)
        self.assertEqual(
            [post["body"]["event_seq"] for post in self.endpoint.posts], [4, 5])

    def test_skipped_and_invalid_do_not_consume_the_event(self) -> None:
        self.endpoint = Endpoint()
        payload = self.signal(event_seq=6)
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.receipts()[-1]["skip_reason"], "not-configured")
        self.assertNotIn("reason", self.receipts()[-1])
        self.assertFalse(self.endpoint.posts)
        bad = dict(payload)
        bad["reason"] = "not_a_reason"
        self.configure_endpoint()
        proc = self.deliver(bad)
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(self.endpoint.posts)
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.endpoint.posts), 1)
        self.assertEqual(self.receipts()[-1]["reason"], "exact_stop")
        self.assertNotIn("skip_reason", self.receipts()[-1])

    def test_delegator_send_does_not_wake(self) -> None:
        # A live dispatched seat is still running, and these turns are the
        # Delegator's own sends. Nothing else needs the Delegator, so the
        # recorded question does not wake either.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat(host_view([{"kind": "decisions", "why": "host-decision"}]))
        self.start_host("delegator", scenario="stop_reason")
        self.start_worker("delegator")
        self.session = self.host_session
        for text in ("end_turn", "max_tokens", "refusal"):
            self.acp("send", "--text", text, "--wait", scenario="stop_reason")
        time.sleep(0.5)
        self.assertFalse(self.endpoint.posts)
        self.assertFalse(self.receipts())

    def test_zero_live_seats_wakes_all_idle(self) -> None:
        # No dispatched holder is live. The turn is the Delegator's and a
        # question is recorded; the wake is still all-idle.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat(host_view([{"kind": "decisions", "why": "host-decision"}]))
        self.start_host("alone", scenario="normal")
        self.acp("send", "--text", "idle", "--wait")
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        15, "all-idle wake")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "end_turn")
        self.assertEqual(set(post["body"]), PAYLOAD_KEYS)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

    def test_self_continuing_turn_does_not_wake_until_the_host_stops(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat("KAOLA_STOP_REASON:max_tokens\n")
        host = self.start_host("chain", scenario="stop_marker", turn_ms=4000)
        worker = self.start_worker("chain")
        self.session = worker
        self.acp("send", "--text", "first", "--wait")
        self.session = host
        wait_for(lambda: self.delivered_count(host) >= 1, 15, "first delivery")
        self.session = worker
        self.acp("send", "--text", "second", "--wait")
        self.session = host
        wait_for(lambda: self.delivered_count(host) >= 2, 15, "second delivery")
        time.sleep(0.4)
        status = self.acp("status")[1]
        self.assertIs(status.get("turn_active"), True, status)
        self.assertFalse(self.endpoint.posts, self.endpoint.posts)
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 15, "continuation ended")
        post = wait_for(lambda: (self.posts_with_reason("host_stopped_pending") or [None])[-1],
                        15, "pending wake")
        self.assertEqual(len(self.posts_with_reason("host_stopped_pending")), 1)
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "max_tokens")
        self.assertEqual(set(post["body"]), PAYLOAD_KEYS)

    def test_attention_reasons_and_clean_idle(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        host = self.start_host("attn", scenario="normal", turn_ms=2000)
        worker = self.start_worker("attn")
        cycles = [
            ([{"kind": "decisions", "why": "host-decision"}], "question_waiting"),
            ([{"kind": "tasks", "why": "awaiting-verdict"}], "delivery_review"),
            ([{"kind": "holds", "why": "host-owned"}], "needs_decision"),
        ]
        for rows, reason in cycles:
            before = self.delivered_count(host)
            self.session = worker
            self.acp("send", "--text", reason, "--wait")
            self.session = host
            wait_for(lambda: self.delivered_count(host) > before, 15,
                     f"delivered before {reason}")
            self.write_heartbeat(host_view(rows))
            post = wait_for(
                lambda: (self.posts_with_reason(reason) or [None])[-1],
                15, reason)
            self.assertEqual(post["body"]["state"], "end_turn")
            self.assertEqual(post["body"]["state_detail"], "end_turn")
        # A later self turn whose attention was already delivered does not wake.
        before_posts = len(self.endpoint.posts)
        before = self.delivered_count(host)
        self.session = worker
        self.acp("send", "--text", "idle", "--wait")
        self.session = host
        wait_for(lambda: self.delivered_count(host) > before, 15, "idle delivery")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 15, "idle turn ended")
        time.sleep(0.5)
        self.assertEqual(len(self.endpoint.posts), before_posts)

    def test_refusal_marker_needs_decision(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat("KAOLA_STOP_REASON:refusal\n")
        host = self.start_host("refuse", scenario="stop_marker", turn_ms=200)
        worker = self.start_worker("refuse")
        self.session = worker
        self.acp("send", "--text", "refuse", "--wait")
        self.session = host
        post = wait_for(lambda: (self.posts_with_reason("needs_decision") or [None])[-1],
                        15, "refusal wake")
        self.assertEqual(post["body"]["state_detail"], "refusal")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(len(self.posts_with_reason("needs_decision")), 1)

    def test_permission_failure_exit_and_boot_still_wake(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        host = self.start_host("perm", scenario="permission_gate")
        self.acp("send", "--text", "need permission", "--no-wait",
                 scenario="permission_gate")
        post = wait_for(lambda: (self.posts_with_reason("permission_required") or [None])[-1],
                        15, "permission wake")
        self.assertEqual(post["body"]["state"], "blocked")
        self.assertEqual(post["body"]["state_detail"], "permission_required")
        self.acp("stop", "--force", scenario="permission_gate")
        self.session = None

        self.start_host("fail", scenario="prompt_error")
        self.acp("send", "--text", "fail", "--wait", scenario="prompt_error",
                 check=False)
        post = wait_for(lambda: (self.posts_with_reason("turn_failed") or [None])[-1],
                        15, "turn_failed wake")
        self.assertEqual(post["body"]["state"], "error")
        self.assertEqual(post["body"]["state_detail"], "turn_failed")
        self.acp("stop", "--force", check=False)
        self.session = None

        self.start_host("die", scenario="die_on_prompt")
        self.acp("send", "--text", "die", "--no-wait", scenario="die_on_prompt",
                 check=False)
        post = wait_for(lambda: (self.posts_with_reason("agent_exited") or [None])[-1],
                        15, "agent exit wake")
        self.assertEqual(post["body"]["state"], "error")
        self.assertEqual(post["body"]["state_detail"], "agent_exit")
        self.acp("stop", "--force", check=False)
        self.session = None

        self.session = "grok-w302-orchestrator-boot"
        _, receipt = self.acp("start", scenario="session_new_fails", check=False)
        self.assertEqual(receipt.get("state"), "error", receipt)
        post = wait_for(lambda: (self.posts_with_reason("boot_failure") or [None])[-1],
                        15, "boot wake")
        self.assertEqual(post["body"]["state_detail"], "boot_failure")
        self.assertEqual(len(self.posts_with_reason("boot_failure")), 1)

    def test_killed_holder_recovered_once_not_a_duplicate(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("recover", scenario="permission_gate")
        self.acp("send", "--text", "block", "--no-wait", scenario="permission_gate")
        blocked = wait_for(
            lambda: (self.posts_with_reason("permission_required") or [None])[-1],
            15, "permission before kill")
        dead = self.sigkill_session()
        dead_id = dead["holder_instance_id"]
        _, receipt = self.acp("start", scenario="normal")
        wake = receipt.get("delegator_death_wake")
        self.assertTrue(wake and wake.get("sent"), receipt)
        lost = wait_for(lambda: self.posts_with_reason("holder_lost") or None,
                        15, "holder_lost")
        self.assertEqual(len(lost), 1)
        body = lost[0]["body"]
        self.assertEqual(body["reason"], "holder_lost")
        self.assertEqual(body["state_detail"], "holder_lost")
        self.assertEqual(body["holder_instance_id"], dead_id)
        self.assertNotEqual(body["event_seq"], blocked["body"]["event_seq"])
        _, again = self.acp("start", check=False)
        self.assertNotIn("delegator_death_wake", again)
        time.sleep(0.4)
        self.assertEqual(len(self.posts_with_reason("holder_lost")), 1)

    def test_turn_end_all_idle_while_sideagent_node_stays_alive(self) -> None:
        # (a) The Host's last turn ends with no working seat. The live
        # Sideagent node is not counted, so the wake is at this turn end.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("node-idle")
        node = self.start_sideagent("node-idle")
        self.session = self.host_session
        self.acp("send", "--text", "idle", "--wait")
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        15, "all-idle at turn end")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "end_turn")
        self.assertEqual(post["body"]["reason"], "all-idle")
        self.assertEqual(set(post["body"]), PAYLOAD_KEYS)
        time.sleep(0.4)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)
        self.session = node
        record = self.holder_record()
        self.assertEqual(record.get("session_role"), "sideagent")
        os.kill(int(record["holder_pid"]), 0)
        self.session = self.host_session

    def test_node_stop_after_idle_turn_sends_one_all_idle(self) -> None:
        # (b) The 20:33 shape. The Host's last turn already ended and this
        # episode has not woken. The confirmed node stop is the first time
        # the condition holds, so the one all-idle is at that stop.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("node-stop")
            host._stop_node("node-holder")
            post = wait_for(
                lambda: (self.posts_for(host.holder_instance_id) or [None])[-1],
                15, "all-idle at node stop")
            self.assertEqual(post["body"]["state"], "end_turn")
            self.assertEqual(post["body"]["state_detail"], "end_turn")
            self.assertEqual(post["body"]["reason"], "all-idle")
            self.assertEqual(set(post["body"]), PAYLOAD_KEYS)
            stopped = [row for row in self.event_rows(host)
                       if row.get("kind") == "sideagent_node_stopped"]
            self.assertEqual(len(stopped), 1)
            self.assertEqual(post["body"]["event_seq"], stopped[0]["cursor"])
            host._stop_node("node-holder")
            time.sleep(0.6)
            self.assertEqual(len(self.posts_for(host.holder_instance_id)), 1)

    def test_node_stop_skips_when_the_host_is_not_idle(self) -> None:
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            active = self.idle_host("active")
            active.turn["active"] = True
            active._stop_node("node-holder")
            follow = self.idle_host("follow")
            follow._delegator_followups = 1
            follow._stop_node("node-holder")
            stopping = self.idle_host("stopping")
            stopping.stop_requested = True
            stopping.state = "stopping"
            stopping._stop_node("node-holder")
            startup = self.idle_host("startup")
            startup.turn["outcome"] = None
            startup._stop_node("node-holder")
            failed = self.idle_host("failed")
            failed.turn["outcome"] = "turn_failed"
            failed._stop_node("node-holder")
            time.sleep(0.8)
            self.assertFalse(self.endpoint.posts, self.endpoint.posts)

    def test_last_worker_stop_after_turn_wakes_all_idle_once(self) -> None:
        # (c) The Delegator's send does not wake while the worker is live.
        # Stopping that worker after the turn sends exactly one all-idle.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("last-seat")
        worker = self.start_worker("last-seat")
        self.session = self.host_session
        self.acp("send", "--text", "work", "--wait")
        time.sleep(0.5)
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        self.session = worker
        self.acp("stop", "--force")
        self.worker = None
        self.session = self.host_session
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        20, "all-idle after last worker")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "end_turn")
        self.assertEqual(post["body"]["reason"], "all-idle")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

    def test_a_live_worker_blocks_all_idle_until_the_last_stops(self) -> None:
        # (d) One remaining worker blocks the wake at the send and at the
        # first stop. The second stop is the one all-idle.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("two")
        first = self.start_worker("two-a")
        self.extra_sessions = [first]
        second = self.start_worker("two-b")
        self.session = self.host_session
        self.acp("send", "--text", "work", "--wait")
        time.sleep(0.4)
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        self.session = first
        self.acp("stop", "--force")
        self.extra_sessions = []
        self.session = self.host_session
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 20, "host idle after the first stop")
        time.sleep(0.6)
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        self.session = second
        self.acp("stop", "--force")
        self.worker = None
        self.session = self.host_session
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        20, "all-idle after the second stop")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "end_turn")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

    def test_node_stop_skips_while_a_worker_seat_is_working(self) -> None:
        # (d) in-process: a ready worker blocks the node-stop re-check.
        # stopping still counts for preservation and does not count as working.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("seat")
            try:
                proc, record_dir = self.spawn_seat(
                    "grok-i305-worker-seat", "expert", "ready", host.holder_instance_id)
                found = wait_for(
                    lambda: holder.holders_dispatched_by(host.holder_instance_id) or None,
                    5, "spawned seat visible")
                self.assertEqual(found, [proc.pid])
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True),
                    [proc.pid])
                host._stop_node("node-holder")
                time.sleep(0.6)
                self.assertFalse(self.endpoint.posts, self.endpoint.posts)
                record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))
                record["state"] = "stopping"
                (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id), [proc.pid])
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True), [])
                record["state"] = "ready"
                record["session_role"] = "sideagent"
                (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
                self.assertEqual(holder.holders_dispatched_by(host.holder_instance_id), [])
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True), [])
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_same_event_posts_once_and_the_episode_latch_holds(self) -> None:
        # (e) The webhook claim still posts one wake for one event_seq.
        # The latch holds a second stop in the same episode. Clearing it and
        # appending a new event may wake again: there is no time throttle.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("dedupe")
            host._delegator_wake("end_turn", "end_turn", "all-idle")
            host._all_idle_woken = False
            host._delegator_wake("end_turn", "end_turn", "all-idle")
            wait_for(lambda: self.posts_for(host.holder_instance_id) or None,
                     15, "first all-idle")
            time.sleep(0.6)
            self.assertEqual(len(self.posts_for(host.holder_instance_id)), 1)
            skipped = [item for item in self.receipts()
                       if item.get("skip_reason") == "duplicate"
                       and item.get("holder_instance_id") == host.holder_instance_id]
            self.assertEqual(len(skipped), 1)
            self.assertNotIn("reason", skipped[0])

            other = self.idle_host("episode")
            other._maybe_delegator_all_idle()
            wait_for(lambda: self.posts_for(other.holder_instance_id) or None,
                     15, "episode all-idle")
            other._maybe_delegator_all_idle()
            time.sleep(0.6)
            self.assertEqual(len(self.posts_for(other.holder_instance_id)), 1)
            other._note_delegator_working_again()
            other.events.append({"kind": "later_worker_stopped"})
            other._maybe_delegator_all_idle()
            wait_for(lambda: len(self.posts_for(other.holder_instance_id)) >= 2,
                     15, "new episode all-idle")
            time.sleep(0.4)
            posts = self.posts_for(other.holder_instance_id)
            self.assertEqual(len(posts), 2)
            self.assertNotEqual(posts[0]["body"]["event_seq"], posts[1]["body"]["event_seq"])

    def test_exact_stop_does_not_also_send_all_idle(self) -> None:
        # (f) Exact stop keeps its own stopped wake. The live worker, and
        # stop_requested before the node reclaim, send no all-idle.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("exact")
        self.start_worker("exact")
        self.session = self.host_session
        self.acp("send", "--text", "work", "--wait")
        time.sleep(0.4)
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        self.acp("stop", "--force")
        self.session = None
        post = wait_for(lambda: (self.posts_with_reason("exact_stop") or [None])[-1],
                        15, "exact stop wake")
        self.assertEqual(post["body"]["state"], "stopped")
        self.assertEqual(post["body"]["state_detail"], "exact_stop")
        self.assertEqual(post["body"]["reason"], "exact_stop")
        time.sleep(0.8)
        self.assertEqual(len(self.posts_with_reason("exact_stop")), 1)
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)

        self.endpoint.posts.clear()
        with self.webhook_process_env():
            host = self.idle_host("exact-node")
            host.stop_requested = True
            host.state = "stopping"
            host._stop_node("node-holder")
            time.sleep(0.6)
            self.assertFalse(self.posts_for(host.holder_instance_id), self.endpoint.posts)

    def test_delegator_sends_to_an_idle_host_do_not_wake_again(self) -> None:
        # Issue #307, KPM receipts 4382-4418. The fresh holder's latch is
        # clear, so the first idle turn is the one transition wake (4369).
        # Each later Delegator send, with no live seat, ends with no wake.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("kpm-repeat")
        self.acp("send", "--text", "restart-context", "--wait")
        wait_for(lambda: len(self.posts_with_reason("all-idle")) == 1,
                 15, "one transition all-idle")
        for text in ("evidence", "choice-3", "choice-4", "choice-5"):
            self.acp("send", "--text", text, "--wait")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)
        self.assertFalse(self.posts_with_reason("needs_decision"))
        self.assertFalse(self.posts_with_reason("question_waiting"))

    def test_delegator_turn_that_stops_the_last_seat_wakes_once(self) -> None:
        # The transition happens during a Delegator-admitted turn: the Host
        # stops the last working seat before that turn ends. Exactly one
        # all-idle, and a later send does not add another.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("during", turn_ms=3000)
        worker = self.start_worker("during")
        self.session = self.host_session
        self.acp("send", "--text", "stop-last", "--no-wait")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is True,
                 15, "delegator turn active")
        self.session = worker
        self.acp("stop", "--force")
        self.worker = None
        self.session = self.host_session
        status = self.acp("status")[1]
        if status.get("turn_active"):
            time.sleep(0.4)
            self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        20, "transition all-idle")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["reason"], "all-idle")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 20, "continuation ended")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)
        self.acp("send", "--text", "still-idle", "--wait")
        time.sleep(0.5)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

    def test_latched_delegator_turn_and_quiet_self_turn_do_not_wake(self) -> None:
        # After the episode has woken, a Delegator turn end is not a wake,
        # and a self continuation with no new worker events does not POST
        # a second all-idle. Admitting either turn does not clear the latch.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("latched")
            host._maybe_delegator_all_idle()
            wait_for(lambda: self.posts_for(host.holder_instance_id) or None,
                     15, "episode all-idle")
            self.assertTrue(host._all_idle_woken)
            host.acp_session_id = "sess-307"
            host.agent.proc = argparse.Namespace(pid=1)
            host.agent.exited.clear()
            host.agent.pending_out = {}
            host.agent.send_request = lambda method, params: 1
            for params in (
                    {"text": "delegator-again", "wait": False},
                    {"text": "self-quiet", "wait": False, "_prompt_source": "self"},
            ):
                receipt = host.op_prompt(params)
                self.assertEqual(receipt.get("outcome"), "turn_failed", receipt)
                self.assertTrue(host._all_idle_woken)
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            # A self turn still names all-idle. The episode latch drops the POST.
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            self.assertTrue(host._all_idle_woken)
            time.sleep(0.6)
            self.assertEqual(len(self.posts_for(host.holder_instance_id)), 1)

    def test_worker_event_self_turn_reopens_the_idle_episode(self) -> None:
        # A self turn that admits new worker events clears the latch. The
        # next all-idle transition wakes once. A following self turn with
        # no new events does not.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("reopen")
            host._maybe_delegator_all_idle()
            wait_for(lambda: self.posts_for(host.holder_instance_id) or None,
                     15, "first episode")
            self.assertTrue(host._all_idle_woken)
            host.agent.proc = object()
            host.agent.exited.clear()
            host.pending_worker_events.append({
                "event_id": "grok/worker/idle/1",
                "kind": "idle",
                "platform": "grok",
                "session": "grok-i307-worker",
                "repo": host.args.repo,
                "reason": "end_turn",
                "event_cursor": 1,
            })

            def admit(params):
                self.assertEqual(params.get("_prompt_source"), "self")
                host.turn["prompt_source"] = "self"
                host.turn["active"] = False
                host.turn["outcome"] = "turn_completed"
                host.turn["stop_reason"] = "end_turn"
                return {"outcome": "in_progress", "prompt_fingerprint": "fp-307",
                        "mutation_performed": True}

            host.op_prompt = admit
            delivered = host._deliver_worker_events()
            self.assertTrue(delivered.get("delivered"), delivered)
            self.assertFalse(host._all_idle_woken)
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            wait_for(lambda: len(self.posts_for(host.holder_instance_id)) >= 2,
                     15, "reopened all-idle")
            self.assertTrue(host._all_idle_woken)
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            time.sleep(0.6)
            posts = self.posts_for(host.holder_instance_id)
            self.assertEqual(len(posts), 2)
            self.assertTrue(all(post["body"]["reason"] == "all-idle" for post in posts))


if __name__ == "__main__":
    unittest.main()
