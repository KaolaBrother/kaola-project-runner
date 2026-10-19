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
        # Issue #324: a standing Host-owned row is not a Delegator decision.
        # A severe alert and a registered decision are.
        other = [{"kind": "alerts", "why": "severe"}]
        standing = [{"kind": "holds", "why": "host-owned"},
                    {"kind": "alerts", "why": "warn"}]
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
            ({"attention_rows": standing}, None),
            ({"attention_rows": standing, "stop_reason": "max_tokens"},
             "host_stopped_pending"),
            ({"stop_reason": "refusal"}, "needs_decision"),
            ({"outcome": "turn_canceled", "stop_reason": None}, "needs_decision"),
            ({"outcome": "turn_canceled", "stop_requested": True}, None),
            ({"outcome": "turn_failed"}, None),
            ({"prompt_source": "delegator", "stop_reason": "max_tokens"}, None),
            # Owner rule 2026-10-11 16:49, narrowed 2026-10-13 (#315):
            # nobody in a turn wakes all-idle only when no attention row is
            # pending. A registered row wins, and the episode latch does not
            # suppress it. all_idle_due defaults true, so a Delegator turn
            # whose latch is still clear reports the one transition.
            # Issue #307: once this episode has sent all-idle, a Delegator
            # turn with nothing registered returns None. A self turn still
            # names all-idle; the emit latch drops the duplicate POST.
            # A length stop or a refusal with no row stays inside that
            # fallback. A live seat with nothing owed stays quiet. A Host
            # that already continued does not wake.
            ({"live_seats": False}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator"}, "all-idle"),
            ({"live_seats": False, "attention_rows": question,
              "prompt_source": "delegator"}, "question_waiting"),
            ({"live_seats": False, "prompt_source": "delegator",
              "all_idle_due": True}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator",
              "stop_reason": "max_tokens", "all_idle_due": True}, "all-idle"),
            ({"live_seats": False, "prompt_source": "delegator",
              "stop_reason": "refusal", "all_idle_due": False}, None),
            ({"live_seats": False, "prompt_source": "delegator",
              "all_idle_due": False}, None),
            ({"live_seats": False, "attention_rows": question,
              "prompt_source": "delegator", "all_idle_due": False},
             "question_waiting"),
            ({"live_seats": False, "attention_rows": other,
              "all_idle_due": False}, "needs_decision"),
            ({"live_seats": False, "attention_rows": standing,
              "all_idle_due": False}, "all-idle"),
            ({"live_seats": False, "attention_rows": delivery,
              "prompt_source": "delegator"}, "delivery_review"),
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

    def test_issue_314_turn_state_classification(self) -> None:
        # record.json has no turn_active. last_prompt.mutation_status is the
        # scan's turn fact. Unknown shapes block; a missing turn does not.
        block = holder.seat_turn_blocks_all_idle
        self.assertFalse(block({"state": "ready"}))
        self.assertFalse(block({"last_prompt": {}}))
        self.assertFalse(block({"last_prompt": {"fingerprint": "fp"}}))
        self.assertFalse(block({"last_prompt": {"mutation_status": "completed"}}))
        self.assertFalse(block({"last_prompt": {"mutation_status": "not_started"}}))
        self.assertTrue(block({"last_prompt": {"mutation_status": "in_progress"}}))
        self.assertTrue(block({"last_prompt": {"mutation_status": "accepted"}}))
        self.assertTrue(block({"last_prompt": None}))
        self.assertTrue(block({"last_prompt": "in_progress"}))
        self.assertTrue(block({"last_prompt": []}))
        self.assertTrue(block({"last_prompt": {"mutation_status": "unknown"}}))
        self.assertTrue(block({"last_prompt": {"mutation_status": None}}))
        self.assertTrue(block({"last_prompt": {"mutation_status": "running"}}))
        self.assertTrue(block({"last_prompt": {"mutation_status": 1}}))
        self.assertTrue(block("not-a-record"))


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

    def start_worker(self, suffix: str, scenario: str = "normal",
                     turn_ms: int = 0) -> str:
        self.worker = f"grok-i302-worker-{suffix}"
        host = self.session
        _, status = self.acp("status")
        holder_id = status.get("holder_instance_id")
        self.assertIsInstance(holder_id, str, status)
        self.session = self.worker
        # The Host counts a live seat from holders whose record names it as
        # dispatcher. The heartbeat target and the dispatcher must name the
        # same Host or start refuses the binding.
        _, receipt = self.acp("start", scenario=scenario, turn_ms=turn_ms, extra_env={
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
        host._finish_delegator_turn_wake(host.turn, reason)
        return reason

    def note_ended_turn(self, host) -> None:
        """Append the ``turn_ended`` row a real turn writes before the wake.

        ``event_seq`` is that cursor. A new all-ended episode is a new event,
        so the deliver claim does not treat the next ``all-idle`` as a replay
        of the previous one.
        """
        host.events.append({"kind": "turn_ended", "outcome": "turn_completed"})

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

    def spawn_seat(self, session: str, role: str, state: str, dispatcher_id: str,
                   last_prompt: dict | None = None, include_last_prompt: bool = False):
        """A live process whose argv matches the holder scan, plus its record.

        ``include_last_prompt`` writes ``last_prompt`` even when it is None,
        which is an unknown turn and blocks all-idle. Omitting it is a seat
        with no recorded turn.
        """
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
        if include_last_prompt or last_prompt is not None:
            record["last_prompt"] = last_prompt
        (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
        return proc, record_dir

    def begin_active_turn(self, session: str) -> None:
        """Admit one prompt on a worker started with a long ``turn_ms``.

        The record must still say ``in_progress`` after a short pause. A
        worker whose mock turn is instant would already be idle, and an idle
        held seat does not block all-idle.
        """
        current = self.session
        self.session = session
        self.acp("send", "--text", "hold-turn", "--no-wait")

        def in_progress():
            record = self.holder_record()
            last = record.get("last_prompt") if isinstance(record.get("last_prompt"), dict) else {}
            if (record.get("state") == "ready"
                    and last.get("mutation_status") == "in_progress"):
                return record
            return None

        wait_for(in_progress, 15, f"{session} active turn")
        time.sleep(0.15)
        record = self.holder_record()
        last = record.get("last_prompt") if isinstance(record.get("last_prompt"), dict) else {}
        self.assertEqual(last.get("mutation_status"), "in_progress", record.get("last_prompt"))
        self.session = current

    def write_seat_prompt(self, record_dir: Path, mutation_status) -> None:
        record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))
        record["state"] = "ready"
        record["last_prompt"] = {"mutation_status": mutation_status}
        (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")

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
        self.assertEqual(receipts[0]["route"], issue299.LOST_WAKE_ROUTE)
        self.assertNotIn(issue299.FINAL_RECEIPT_TEXT, receipts[0]["route"])
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
        for item in connection[:-1]:
            self.assertNotIn("route", item)
            self.assertNotIn("self_route", item)
            self.assertNotIn(issue299.FINAL_RECEIPT_TEXT, json.dumps(item))
        self.assertEqual(connection[-1]["route"], issue299.LOST_WAKE_ROUTE)

        # Issue #311: 400 joins the delayed retry set. 401, 403 and 404 stay
        # final on attempt 1. Other 4xx stay final too (422 stands for them).
        for code, attempts in ((500, 4), (408, 4), (429, 4), (400, 4),
                               (401, 1), (403, 1), (404, 1), (422, 1)):
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
            if code in (401, 403):
                expected = issue299.ROTATE_KEY_ROUTE
            elif code == 404:
                expected = issue299.RECONFIGURE_URL_ROUTE
            else:
                expected = issue299.LOST_WAKE_ROUTE
            self.assertEqual(matching[-1]["route"], expected, code)
            self.assertNotIn(issue299.FINAL_RECEIPT_TEXT, matching[-1]["route"])
            if attempts > 1:
                self.assertIs(matching[0]["final"], False)
                for item in matching[:-1]:
                    self.assertNotIn("route", item, code)
                    self.assertNotIn("self_route", item, code)
                    self.assertNotIn(issue299.FINAL_RECEIPT_TEXT, json.dumps(item))

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
        # A dispatched seat is in an active turn, and these turns are the
        # Delegator's own sends. Nothing else needs the Delegator, so the
        # recorded question does not wake either. An idle held seat would
        # not keep this quiet (Issue #314).
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat(host_view([{"kind": "decisions", "why": "host-decision"}]))
        self.start_host("delegator", scenario="stop_reason")
        worker = self.start_worker("delegator", turn_ms=30000)
        self.begin_active_turn(worker)
        self.session = self.host_session
        for text in ("end_turn", "max_tokens", "refusal"):
            self.acp("send", "--text", text, "--wait", scenario="stop_reason")
        time.sleep(0.5)
        self.assertFalse(self.endpoint.posts)
        self.assertFalse(self.receipts())

    def test_zero_live_seats_wakes_all_idle(self) -> None:
        # No dispatched holder is live and nothing is registered. The turn
        # is the Delegator's; the fallback is one all-idle. A recorded
        # decision is needs_decision instead (Issue #315).
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat(host_view([]))
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
        # The notifier's own turns end before the Host continuation does.
        # A second seat stays in a turn, so the length stop is still
        # host_stopped_pending rather than all-idle.
        busy = self.start_worker("chain-busy", turn_ms=90000)
        self.extra_sessions = [worker]
        self.begin_active_turn(busy)
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
        # Attention wins only while some seat is still in a turn. The
        # notifier's turn has already ended when the Host turn ends.
        busy = self.start_worker("attn-busy", turn_ms=120000)
        self.extra_sessions = [worker]
        self.begin_active_turn(busy)
        cycles = [
            ([{"kind": "decisions", "why": "host-decision"}], "question_waiting"),
            ([{"kind": "tasks", "why": "awaiting-verdict"}], "delivery_review"),
            ([{"kind": "alerts", "why": "severe"}], "needs_decision"),
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
        busy = self.start_worker("refuse-busy", turn_ms=60000)
        self.extra_sessions = [worker]
        self.begin_active_turn(busy)
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
        worker = self.start_worker("last-seat", turn_ms=30000)
        self.begin_active_turn(worker)
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
        first = self.start_worker("two-a", turn_ms=40000)
        self.begin_active_turn(first)
        second = self.start_worker("two-b", turn_ms=40000)
        self.extra_sessions = [first]
        self.begin_active_turn(second)
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

    def test_rebound_busy_worker_blocks_all_idle_until_it_stops(self) -> None:
        # Issue #365: a seat rebound to the replacement Host is that Host's
        # live seat. rebind-host rewrites its record dispatcher, the new
        # Host's turn end sends no all-idle while the rebound seat is in a
        # turn, and its stop still sends the one all-idle.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.write_heartbeat(host_view([]))
        old_host = self.start_host("old")
        worker = self.start_worker("rebound", turn_ms=120000)
        self.begin_active_turn(worker)
        self.session = old_host
        self.acp("stop", "--preserve-dispatched-workers")
        self.extra_sessions = [old_host]
        new_host = self.start_host("new")
        _, status = self.acp("status")
        new_id = status.get("holder_instance_id")
        self.assertIsInstance(new_id, str, status)
        self.session = worker
        self.acp("rebind-host", extra_env={"KAOLA_ACP_DISPATCHER": json.dumps({
            "holder_instance_id": new_id, "platform": "grok",
            "session": new_host, "repo": self.project})})
        record = self.holder_record()
        dispatcher = record.get("dispatcher") or {}
        self.assertEqual(
            (dispatcher.get("platform"), dispatcher.get("session"),
             dispatcher.get("repo"), dispatcher.get("holder_instance_id")),
            ("grok", new_host, self.project, new_id),
            "rebind-host rewrites the seat's dispatcher to the replacement Host")
        self.assertEqual((record.get("heartbeat_host") or {}).get("session"), new_host)
        self.session = new_host
        self.acp("send", "--text", "work", "--wait")
        time.sleep(0.6)
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        self.session = worker
        self.acp("stop", "--force")
        self.worker = None
        self.session = new_host
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        20, "all-idle after the rebound seat stopped")
        self.assertEqual(post["body"]["reason"], "all-idle")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

    def test_node_stop_skips_while_a_worker_seat_is_working(self) -> None:
        # (d) in-process: a ready worker in an active turn blocks the
        # node-stop re-check. stopping still counts for preservation and
        # does not count as working.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("seat")
            try:
                proc, record_dir = self.spawn_seat(
                    "grok-i305-worker-seat", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "in_progress"})
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
        worker = self.start_worker("exact", turn_ms=30000)
        self.begin_active_turn(worker)
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
        # Issue #307, receipts 4382-4418. The fresh holder's latch is
        # clear, so the first idle turn is the one transition wake (4369).
        # Each later Delegator send, with no live seat, ends with no wake.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("repeat-host")
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

    def test_issue_314_idle_held_seat_wakes_all_idle_once(self) -> None:
        # (a) Real holders. The only live seat is ready and its turn has
        # ended (awaiting acceptance). The Host turn that observes that
        # ends with exactly one all-idle. A later Delegator send does not
        # add another. Nothing else is pending.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("held")
        worker = self.start_worker("held")
        self.session = worker
        self.acp("send", "--text", "accepted-work", "--wait")
        status = self.acp("status")[1]
        self.assertEqual(status.get("state"), "ready", status)
        self.assertIs(status.get("turn_active"), False, status)
        record = self.holder_record()
        last = record.get("last_prompt") if isinstance(record.get("last_prompt"), dict) else {}
        self.assertEqual(last.get("mutation_status"), "completed", last)
        self.session = self.host_session
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 15, "host idle after the worker turn")
        if not self.posts_with_reason("all-idle"):
            # The worker's idle notice may already have ended a Host turn.
            # If it did not, this Delegator turn is the observation.
            self.acp("send", "--text", "host-observes-idle-seat", "--wait")
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        20, "all-idle for the idle held seat")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["reason"], "all-idle")
        self.assertEqual(set(post["body"]), PAYLOAD_KEYS)
        self.acp("send", "--text", "still-idle", "--wait")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)
        self.assertFalse(self.posts_with_reason("needs_decision"))
        self.assertFalse(self.posts_with_reason("question_waiting"))

    def test_issue_314_completed_record_one_all_idle_in_process(self) -> None:
        # (a) The record shape, without a second Host prompt: ready, last
        # prompt completed, no attention. One all-idle, then the latch holds.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("held-record")
            try:
                proc, _record_dir = self.spawn_seat(
                    "grok-i314-held", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "completed"})
                found = wait_for(
                    lambda: holder.holders_dispatched_by(host.holder_instance_id) or None,
                    5, "idle held seat visible")
                self.assertEqual(found, [proc.pid])
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True), [])
                self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
                wait_for(lambda: self.posts_for(host.holder_instance_id) or None,
                         15, "all-idle for completed seat")
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
                time.sleep(0.6)
                self.assertEqual(len(self.posts_for(host.holder_instance_id)), 1)
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_issue_314_active_turn_blocks_until_it_ends(self) -> None:
        # (b) A real worker turn still in progress blocks the Host's idle
        # transition. When that turn ends, the next Host observation wakes
        # once.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("active")
        worker = self.start_worker("active", turn_ms=12000)
        self.begin_active_turn(worker)
        self.session = self.host_session
        self.acp("send", "--text", "host-while-worker-busy", "--wait")
        self.session = worker
        status = self.acp("status")[1]
        self.assertIs(status.get("turn_active"), True, status)
        record = self.holder_record()
        last = record.get("last_prompt") if isinstance(record.get("last_prompt"), dict) else {}
        self.assertEqual(last.get("mutation_status"), "in_progress", last)
        self.session = self.host_session
        self.assertFalse(self.posts_with_reason("all-idle"), self.endpoint.posts)
        post = wait_for(lambda: (self.posts_with_reason("all-idle") or [None])[-1],
                        20, "all-idle after the worker turn ends")
        self.assertEqual(post["body"]["reason"], "all-idle")
        self.assertEqual(post["body"]["state"], "end_turn")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

    def test_issue_314_active_record_blocks_then_completed_wakes_once(self) -> None:
        # (b) Same transition on the record the scan reads. in_progress
        # blocks. completed is the one all-idle. The latch holds a repeat.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("active-record")
            try:
                proc, record_dir = self.spawn_seat(
                    "grok-i314-active", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "in_progress"})
                found = wait_for(
                    lambda: holder.holders_dispatched_by(
                        host.holder_instance_id, working=True) or None,
                    5, "active seat visible")
                self.assertEqual(found, [proc.pid])
                self.assertIsNone(self.end_turn_wake(host, "self"))
                self.assertFalse(self.posts_for(host.holder_instance_id))
                self.write_seat_prompt(record_dir, "completed")
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True), [])
                self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
                wait_for(lambda: len(self.posts_for(host.holder_instance_id)) == 1,
                         15, "one all-idle after the turn ended")
                self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
                time.sleep(0.6)
                self.assertEqual(len(self.posts_for(host.holder_instance_id)), 1)
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_issue_314_unknown_turn_blocks_all_idle(self) -> None:
        # (d) Unknown blocks. A false all-idle would claim nobody is working
        # while this seat's turn cannot be read. A later known-idle status
        # is the one transition.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("unknown-turn")
            try:
                proc, record_dir = self.spawn_seat(
                    "grok-i314-unknown", "expert", "ready", host.holder_instance_id,
                    last_prompt={"mutation_status": "unknown"})
                found = wait_for(
                    lambda: holder.holders_dispatched_by(
                        host.holder_instance_id, working=True) or None,
                    5, "unknown-turn seat visible")
                self.assertEqual(found, [proc.pid])
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id), [proc.pid])
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                self.assertFalse(self.posts_for(host.holder_instance_id))
                record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))
                record["last_prompt"] = None
                (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True),
                    [proc.pid])
                self.assertIsNone(self.end_turn_wake(host, "self"))
                self.assertFalse(self.posts_for(host.holder_instance_id))
                self.write_seat_prompt(record_dir, "completed")
                self.assertEqual(
                    holder.holders_dispatched_by(host.holder_instance_id, working=True), [])
                self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
                wait_for(lambda: len(self.posts_for(host.holder_instance_id)) == 1,
                         15, "all-idle once the unknown turn is completed")
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                time.sleep(0.5)
                self.assertEqual(len(self.posts_for(host.holder_instance_id)), 1)
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_issue_317_carried_latch_wakes_once_per_new_episode(self) -> None:
        # The previous episode already sent all-idle. A Delegator turn with
        # no new work stays silent. Arming the next episode while that latch
        # is still set, then ending with nobody running, sends exactly one
        # all-idle. The same episode does not send another. A later episode
        # does.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("carried-latch")
            holder_id = host.holder_instance_id
            host._all_idle_woken = True
            host._all_ended_busy = False
            self.note_ended_turn(host)
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            time.sleep(0.4)
            self.assertFalse(self.posts_for(holder_id))
            self.assertTrue(host._all_idle_woken)

            host._all_ended_busy = True
            self.assertTrue(host._all_idle_woken)
            self.note_ended_turn(host)
            self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
            wait_for(lambda: len(self.posts_for(holder_id)) == 1,
                     15, "one all-idle despite the carried latch")
            self.assertTrue(host._all_idle_woken)
            self.assertFalse(host._all_ended_busy)
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            # A self turn still names all-idle. The episode latch drops the POST.
            self.assertEqual(self.end_turn_wake(host, "self"), "all-idle")
            time.sleep(0.5)
            self.assertEqual(len(self.posts_for(holder_id)), 1)

            host._all_ended_busy = True
            self.assertTrue(host._all_idle_woken)
            self.note_ended_turn(host)
            self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
            wait_for(lambda: len(self.posts_for(holder_id)) == 2,
                     15, "the next episode wakes again")
            posts = self.posts_for(holder_id)
            self.assertEqual(len(posts), 2)
            self.assertTrue(all(post["body"]["reason"] == "all-idle" for post in posts))
            self.assertNotEqual(posts[0]["body"]["event_seq"], posts[1]["body"]["event_seq"])
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            time.sleep(0.4)
            self.assertEqual(len(self.posts_for(holder_id)), 2)

    def test_issue_317_completed_seat_opens_one_new_episode(self) -> None:
        # VRPCadCore shape: the seat's turn completes and the process stays
        # up, so nothing calls the terminated re-check. Seeing that seat
        # working re-opens the episode. The Delegator turn that then finds
        # it idle sends one all-idle. A repeat does not. Another working
        # stretch does.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("completed-seat")
            holder_id = host.holder_instance_id
            try:
                self.note_ended_turn(host)
                self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
                wait_for(lambda: len(self.posts_for(holder_id)) == 1,
                         15, "first idle episode")
                self.assertTrue(host._all_idle_woken)
                self.assertFalse(host._all_ended_busy)

                proc, record_dir = self.spawn_seat(
                    "grok-i317-seat", "expert", "ready", holder_id,
                    last_prompt={"mutation_status": "in_progress"})
                found = wait_for(
                    lambda: holder.holders_dispatched_by(holder_id, working=True) or None,
                    5, "working seat visible")
                self.assertEqual(found, [proc.pid])
                self.note_ended_turn(host)
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                self.assertTrue(host._all_ended_busy)
                self.assertFalse(host._all_idle_woken)
                time.sleep(0.4)
                self.assertEqual(len(self.posts_for(holder_id)), 1)

                self.write_seat_prompt(record_dir, "completed")
                self.assertEqual(
                    holder.holders_dispatched_by(holder_id, working=True), [])
                self.note_ended_turn(host)
                self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
                wait_for(lambda: len(self.posts_for(holder_id)) == 2,
                         15, "all-idle after the seat's turn completed")
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                time.sleep(0.4)
                self.assertEqual(len(self.posts_for(holder_id)), 2)

                self.write_seat_prompt(record_dir, "in_progress")
                self.assertEqual(
                    holder.holders_dispatched_by(holder_id, working=True), [proc.pid])
                self.note_ended_turn(host)
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                self.assertTrue(host._all_ended_busy)
                self.write_seat_prompt(record_dir, "completed")
                self.note_ended_turn(host)
                self.assertEqual(self.end_turn_wake(host, "delegator"), "all-idle")
                wait_for(lambda: len(self.posts_for(holder_id)) == 3,
                         15, "third episode after work resumed")
                self.assertIsNone(self.end_turn_wake(host, "delegator"))
                time.sleep(0.4)
                posts = self.posts_for(holder_id)
                self.assertEqual(len(posts), 3)
                self.assertEqual(
                    len({post["body"]["event_seq"] for post in posts}), 3)
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_issue_317_live_send_waiter_defers_one_all_idle(self) -> None:
        # A caller still blocked on send is not all-ended. The owed wake
        # runs once that caller has left, and the same episode does not
        # send a second one. A timeout while the Host turn is still active
        # does not send it either.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        with self.webhook_process_env():
            host = self.idle_host("waiter")
            holder_id = host.holder_instance_id
            host._all_idle_woken = True
            host._all_ended_busy = True
            host._send_waiters = 1
            self.note_ended_turn(host)
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            self.assertTrue(host._all_ended_deferred)
            self.assertTrue(host._all_idle_woken)
            time.sleep(0.4)
            self.assertFalse(self.posts_for(holder_id))

            host.turn["active"] = True
            host._send_waiters = 0
            host._flush_all_ended_after_waiter()
            self.assertTrue(host.turn["active"])
            self.assertTrue(host._all_ended_deferred)
            self.assertFalse(self.posts_for(holder_id))

            host.turn["active"] = False
            host.turn["outcome"] = "turn_completed"
            host._flush_all_ended_after_waiter()
            wait_for(lambda: len(self.posts_for(holder_id)) == 1,
                     15, "one all-idle after the waiter left")
            self.assertTrue(host._all_idle_woken)
            self.assertFalse(host._all_ended_busy)
            self.assertFalse(host._all_ended_deferred)
            self.note_ended_turn(host)
            self.assertIsNone(self.end_turn_wake(host, "delegator"))
            time.sleep(0.4)
            self.assertEqual(len(self.posts_for(holder_id)), 1)
            self.assertEqual(self.posts_for(holder_id)[0]["body"]["reason"], "all-idle")

    def test_issue_317_real_host_wakes_once_per_all_ended_episode(self) -> None:
        # Both send forms. The first idle turn is one all-idle. Later sends
        # in that episode are not. A long worker turn blocks the next one.
        # Stopping that worker is the second. Sends after it stay quiet.
        # A second worker cycle is the third.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("episode")
        self.acp("send", "--text", "first-idle", "--wait")
        wait_for(lambda: len(self.posts_with_reason("all-idle")) == 1,
                 15, "first all-ended episode")
        self.acp("send", "--text", "same-episode-wait", "--wait")
        self.acp("send", "--text", "same-episode-nowait", "--no-wait")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 15, "same-episode send ended")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)

        worker = self.start_worker("episode", turn_ms=20000)
        self.begin_active_turn(worker)
        self.session = self.host_session
        self.acp("send", "--text", "while-seat-works", "--wait")
        time.sleep(0.5)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 1)
        self.session = worker
        status = self.acp("status")[1]
        self.assertIs(status.get("turn_active"), True, status)
        self.acp("stop", "--force")
        self.worker = None
        self.session = self.host_session
        wait_for(lambda: len(self.posts_with_reason("all-idle")) == 2,
                 20, "second episode after the worker stopped")
        self.acp("send", "--text", "after-second-wait", "--wait")
        self.acp("send", "--text", "after-second-nowait", "--no-wait")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 15, "post-episode send ended")
        time.sleep(0.6)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 2)

        worker = self.start_worker("episode-b", turn_ms=20000)
        self.begin_active_turn(worker)
        self.session = self.host_session
        self.acp("send", "--text", "while-second-seat-works", "--no-wait")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is False,
                 15, "second observation ended")
        time.sleep(0.4)
        self.assertEqual(len(self.posts_with_reason("all-idle")), 2)
        self.session = worker
        self.acp("stop", "--force")
        self.worker = None
        self.session = self.host_session
        wait_for(lambda: len(self.posts_with_reason("all-idle")) == 3,
                 20, "third episode after work resumed")
        posts = self.posts_with_reason("all-idle")
        self.assertEqual(len(posts), 3)
        self.assertEqual(len({post["body"]["event_seq"] for post in posts}), 3)
        self.assertTrue(all(post["body"]["state"] == "end_turn" for post in posts))

    def test_issue_317_host_wake_while_a_seat_works(self) -> None:
        # Rule 2. The Host records the request by calling the holder. The
        # wake is that call, not the all-ended transition. A working seat
        # and a set latch do not suppress it, and the call does not clear
        # the latch. A second call is a new event. Replaying the first
        # event_seq does not POST again.
        self.endpoint = Endpoint()
        self.configure_endpoint()
        proc = None
        with self.webhook_process_env():
            host = self.idle_host("host-wake")
            holder_id = host.holder_instance_id
            host._all_idle_woken = True
            host._all_ended_busy = False
            try:
                proc, _record_dir = self.spawn_seat(
                    "grok-i317-wake", "expert", "ready", holder_id,
                    last_prompt={"mutation_status": "in_progress"})
                found = wait_for(
                    lambda: holder.holders_dispatched_by(holder_id, working=True) or None,
                    5, "seat still working")
                self.assertEqual(found, [proc.pid])
                refused = host.op_wake_delegator({"reason": "all-idle"})
                self.assertEqual(refused.get("error", {}).get("code"), "wake-reason-refused")
                host.session_role = "expert"
                not_host = host.op_wake_delegator({"reason": "needs_decision"})
                self.assertEqual(not_host.get("error", {}).get("code"), "wake-not-host")
                host.session_role = "host"
                receipt = host.op_wake_delegator({"reason": "needs_decision"})
                self.assertTrue(receipt.get("woke"), receipt)
                self.assertEqual(receipt.get("state_detail"), "host_initiated")
                post = wait_for(
                    lambda: (self.posts_for(holder_id, "needs_decision") or [None])[-1],
                    15, "needs_decision while the seat works")
                self.assertEqual(post["body"]["state"], "end_turn")
                self.assertEqual(post["body"]["state_detail"], "host_initiated")
                self.assertEqual(post["body"]["event_seq"], receipt["event_seq"])
                self.assertEqual(
                    holder.holders_dispatched_by(holder_id, working=True), [proc.pid])
                self.assertFalse(self.posts_for(holder_id, "all-idle"))
                self.assertTrue(host._all_idle_woken)
                self.assertFalse(host._all_ended_busy)
                replay = self.deliver(post["body"], timeout=20)
                self.assertEqual(replay.returncode, 0, replay.stderr)
                time.sleep(0.4)
                self.assertEqual(len(self.posts_for(holder_id, "needs_decision")), 1)
                second = host.op_wake_delegator({"reason": "question_waiting"})
                self.assertTrue(second.get("woke"), second)
                self.assertNotEqual(second["event_seq"], receipt["event_seq"])
                wait_for(
                    lambda: self.posts_for(holder_id, "question_waiting") or None,
                    15, "second explicit wake")
                self.assertEqual(
                    holder.holders_dispatched_by(holder_id, working=True), [proc.pid])
                self.assertFalse(self.posts_for(holder_id, "all-idle"))
            finally:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    def test_issue_317_cli_wake_does_not_wait_for_the_seat(self) -> None:
        # The same call through the CLI, with a real worker turn still open.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("cli-wake")
        worker = self.start_worker("cli-wake", turn_ms=20000)
        self.begin_active_turn(worker)
        self.session = self.host_session
        _code, receipt = self.acp("wake", "--reason", "needs_decision")
        self.assertTrue(receipt.get("woke"), receipt)
        self.assertEqual(receipt.get("reason"), "needs_decision")
        post = wait_for(lambda: (self.posts_with_reason("needs_decision") or [None])[-1],
                        15, "CLI wake while the worker turn is open")
        self.assertEqual(post["body"]["state_detail"], "host_initiated")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.session = worker
        status = self.acp("status")[1]
        self.assertIs(status.get("turn_active"), True, status)
        self.session = self.host_session
        self.assertFalse(self.posts_with_reason("all-idle"))
        _code, second = self.acp("wake", "--reason", "delivery_review")
        self.assertNotEqual(second.get("event_seq"), receipt.get("event_seq"))
        wait_for(lambda: self.posts_with_reason("delivery_review") or None,
                 15, "second CLI wake")
        self.session = worker
        status = self.acp("status")[1]
        self.assertIs(status.get("turn_active"), True, status)
        time.sleep(0.4)
        self.assertEqual(len(self.posts_with_reason("needs_decision")), 1)
        self.assertEqual(len(self.posts_with_reason("delivery_review")), 1)
        self.assertFalse(self.posts_with_reason("all-idle"))

    def test_issue_321_steer_interrupt_of_a_self_turn_does_not_wake(self) -> None:
        # Review G5. A worker-event self turn is open and a seat is in a
        # turn. ``steer --steer-mode interrupt`` cancels that self turn
        # from the socket and admits the steering text as the next turn.
        # That cancel does not POST ``needs_decision`` / ``cancelled``.
        # ``op_steer_interrupt`` does not increment ``_delegator_followups``
        # (only an after-turn steer queue does). The follow-up admission
        # replaces ``self.turn`` with an active turn before the predicate
        # reads it: ``holders_dispatched_by`` scans ps first, and
        # ``self_continuing`` is that active follow-up, so the
        # ``turn_canceled`` branch is not reached.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        host = self.start_host("g5", scenario="hang_until_cancel")
        notifier = self.start_worker("g5-note")
        busy = self.start_worker("g5-busy", turn_ms=60000)
        self.extra_sessions = [notifier]
        self.begin_active_turn(busy)
        self.session = notifier
        self.acp("send", "--text", "notify-host", "--wait")
        self.session = host
        wait_for(lambda: self.delivered_count(host) >= 1, 15, "self turn admitted")
        wait_for(lambda: self.acp("status")[1].get("turn_active") is True,
                 15, "self turn still open")
        self.session = busy
        busy_status = self.acp("status")[1]
        self.assertIs(busy_status.get("turn_active"), True, busy_status)
        self.session = host
        self.assertFalse(self.endpoint.posts, self.endpoint.posts)

        _code, receipt = self.acp(
            "steer", "--steer-mode", "interrupt", "--text", "redirect the self turn",
            timeout=30)
        self.assertEqual(receipt.get("steer_outcome"), "interrupted_and_resent", receipt)
        self.assertIs(receipt.get("interrupted"), True, receipt)
        self.assertEqual(receipt.get("steer_confirmation"), "cancel-confirmed", receipt)
        self.assertEqual(receipt.get("steer_mode"), "interrupt", receipt)
        self.assertEqual(receipt.get("steer_method"), "cancel+prompt", receipt)
        cancelled_id = receipt.get("cancelled_turn_request_id")
        new_id = receipt.get("new_turn_request_id")
        self.assertIsNotNone(cancelled_id, receipt)
        self.assertNotEqual(new_id, cancelled_id, receipt)

        events = self.session_events(host)
        delivered = [event for event in events
                     if event.get("kind") == "worker_event_delivered"]
        self.assertTrue(delivered, events[-8:])
        fingerprint = delivered[-1].get("prompt_fingerprint")
        self.assertIsInstance(fingerprint, str)
        canceled = [event for event in events
                    if event.get("kind") == "turn_ended"
                    and event.get("outcome") == "turn_canceled"]
        self.assertTrue(canceled, events[-8:])
        self.assertEqual(canceled[-1].get("prompt_fingerprint"), fingerprint)
        self.assertEqual(canceled[-1].get("stop_reason"), "cancelled")
        interrupts = [event for event in events if event.get("kind") == "steer_interrupt"]
        self.assertEqual(len(interrupts), 1, interrupts)
        self.assertIs(interrupts[0].get("interrupted"), True)

        status = self.acp("status")[1]
        self.assertIs(status.get("turn_active"), True, status)
        self.session = busy
        still = self.acp("status")[1]
        self.assertIs(still.get("turn_active"), True, still)
        self.session = host
        time.sleep(1.0)
        self.assertFalse(self.posts_with_reason("needs_decision"), self.endpoint.posts)
        self.assertFalse(
            [post for post in self.endpoint.posts
             if (post.get("body") or {}).get("state_detail") == "cancelled"],
            self.endpoint.posts)
        self.assertFalse(self.endpoint.posts, self.endpoint.posts)
        self.assertEqual(self.receipts(), [])


if __name__ == "__main__":
    unittest.main()
