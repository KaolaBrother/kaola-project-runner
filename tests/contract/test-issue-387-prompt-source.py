#!/usr/bin/env python3
"""Issue #387: a view names who wrote a prompt (Delegator or holder itself).

The defect: ``add_user_from_prompt`` stored only role/text/cursor, so a Host
carrier self prompt (``kaola-host-notify/1: ...``) and a Delegator ``send``
produced structurally identical ``view.messages[]`` user rows and ``turns[]``
rows. ``prompt_source`` existed only in the holder's in-memory turn and in the
agent-initiated ``turn_started``/``turn_ended`` events.

The fix stores the source ("delegator" or "self") and the optional carrier
schema id on the prompt row and its turn row as internal facts. ``snapshot``
publishes ``prompt_source`` and ``carrier`` on that prompt's user row,
``source`` and ``carrier`` on that turn row, adds ``prompt_source`` to every
``turn_ended`` event, and records ``last_prompt.source`` so a reconnect can
still tell even though the in-memory projection starts empty. The view schema
stays ``kaola-acp-view/1``: these are additive optional fields.

Run: python3 tests/contract/test-issue-387-prompt-source.py -v
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"
SAMPLE = REPO / "tests" / "contract" / "fixtures" / "kaola-acp-view-1.sample.json"

_spec = importlib.util.spec_from_file_location("kaola_acp_holder_i387", HOLDER)
assert _spec is not None and _spec.loader is not None
holder_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(holder_module)

HOST_SCHEMA = "kaola-host-notify/1"
WORKER_SCHEMA = "kaola-worker-notify/1"
CARRIER_MARK = f"{HOST_SCHEMA}: event-driven heartbeat carrier"


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout waiting for {label}")


def internal_keys(value: Any) -> list[str]:
    """Every private view-row key found anywhere in a payload or row."""
    found: list[str] = []

    def walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if isinstance(key, str) and key.startswith("_"):
                    found.append(f"{path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")

    walk(value, "$")
    return found


class LegacyProjection:
    """The pre-#387 message/turn projection shape, kept for counter-proofs.

    It is reconstructed from the old ``ViewProjection`` public rows: a prompt
    message row has no source/carrier and a turn row has no source. Test code
    only, not a second production projection.
    """

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.turns: list[dict[str, Any]] = []

    def add_user_from_prompt(self, text: str, cursor: int,
                             started_at: float | None = None,
                             client_message_id: str | None = None) -> None:
        self.messages.append({
            "role": "user", "text": text, "messageId": None,
            "cursor": cursor, "received_at": None,
        })
        turn: dict[str, Any] = {
            "started_at": started_at, "ended_at": None, "outcome": None,
            "stop_reason": None, "start_cursor": cursor, "end_cursor": None,
        }
        if client_message_id is not None:
            turn["clientMessageId"] = client_message_id
        self.turns.append(turn)

    def snapshot(self) -> dict[str, Any]:
        return {"messages": copy.deepcopy(self.messages),
                "turns": copy.deepcopy(self.turns)}


def legacy_turn_ended(turn: dict[str, Any]) -> dict[str, Any]:
    """The pre-#387 normal ``turn_ended`` event shape (no prompt_source)."""
    return {"kind": "turn_ended", "outcome": "turn_completed",
            "stop_reason": "end_turn",
            "prompt_fingerprint": turn.get("fingerprint")}


def legacy_last_prompt(turn: dict[str, Any]) -> dict[str, Any]:
    """The pre-#387 ``record.last_prompt`` shape (no source)."""
    return {"fingerprint": turn.get("fingerprint"),
            "written_at": turn.get("written_at"),
            "transport": "acp", "mutation_status": "completed",
            "stop_reason": "end_turn"}


class ProjectionProvenanceTests(unittest.TestCase):
    """The projection row storage, the snapshot mapping and the frozen sample."""

    def test_prompt_rows_publish_source_and_optional_carrier(self) -> None:
        projection = holder_module.ViewProjection()
        projection.add_user_from_prompt(
            "carrier text", 1, 10.0, source="self", carrier=HOST_SCHEMA)
        projection.apply(
            {"sessionUpdate": "agent_message_chunk",
             "content": {"type": "text", "text": "reply"}}, 2, 11.0)
        projection.add_user_from_prompt(
            "delegator text", 3, 12.0, "client-1", source="delegator")
        snapshot = projection.snapshot()
        carrier_row, assistant, delegator_row = snapshot["messages"]
        self.assertEqual(carrier_row["prompt_source"], "self")
        self.assertEqual(carrier_row["carrier"], HOST_SCHEMA)
        self.assertEqual(carrier_row["text"], "carrier text")
        self.assertNotIn("prompt_source", assistant)
        self.assertNotIn("carrier", assistant)
        self.assertEqual(delegator_row["prompt_source"], "delegator")
        self.assertNotIn("carrier", delegator_row)
        self.assertEqual(delegator_row["clientMessageId"], "client-1")
        self.assertEqual(internal_keys(snapshot), [])

        carrier_turn, delegator_turn = snapshot["turns"]
        self.assertEqual(carrier_turn["source"], "self")
        self.assertEqual(carrier_turn["carrier"], HOST_SCHEMA)
        self.assertEqual(carrier_turn["start_cursor"], 1)
        self.assertEqual(delegator_turn["source"], "delegator")
        self.assertNotIn("carrier", delegator_turn)
        self.assertEqual(delegator_turn["clientMessageId"], "client-1")

    def test_default_source_and_unusable_carrier_are_normalized(self) -> None:
        projection = holder_module.ViewProjection()
        projection.add_user_from_prompt("default", 1)
        projection.add_user_from_prompt(
            "bogus", 2, source="not-a-source", carrier="")
        projection.add_user_from_prompt(
            "object", 3, source="self", carrier=17)  # type: ignore[arg-type]
        snapshot = projection.snapshot()
        self.assertEqual(snapshot["messages"][0]["prompt_source"], "delegator")
        self.assertEqual(snapshot["messages"][1]["prompt_source"], "delegator")
        self.assertEqual(snapshot["messages"][2]["prompt_source"], "self")
        for row in snapshot["messages"]:
            self.assertNotIn("carrier", row)
        self.assertEqual([turn["source"] for turn in snapshot["turns"]],
                         ["delegator", "delegator", "self"])
        for turn in snapshot["turns"]:
            self.assertNotIn("carrier", turn)

    def test_agent_initiated_turn_row_is_self_and_has_no_message(self) -> None:
        projection = holder_module.ViewProjection()
        projection.add_user_from_prompt("prompt", 1, 10.0, source="delegator")
        projection.end_turn(11.0, 2, "turn_completed", "end_turn")
        projection.start_agent_turn(3, 12.0)
        projection.end_turn(13.0, 4, "turn_completed", "end_turn")
        snapshot = projection.snapshot()
        self.assertEqual([row["role"] for row in snapshot["messages"]], ["user"])
        self.assertEqual([turn["source"] for turn in snapshot["turns"]],
                         ["delegator", "self"])
        self.assertNotIn("carrier", snapshot["turns"][1])

    def test_sample_fixture_carries_the_additive_provenance(self) -> None:
        sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(sample["schema"], "kaola-acp-view/1")
        prompt = sample["messages"][0]
        self.assertEqual(prompt["role"], "user")
        self.assertEqual(prompt["prompt_source"], "delegator")
        self.assertNotIn("carrier", prompt)
        for row in sample["messages"]:
            if row["role"] == "assistant":
                self.assertNotIn("prompt_source", row)
                self.assertNotIn("carrier", row)
        for turn in sample["turns"]:
            self.assertIn(turn["source"], ("delegator", "self"))
        self.assertEqual(sample["turns"][0]["source"], "delegator")
        self.assertNotIn("carrier", sample["turns"][0])
        self.assertEqual(internal_keys(sample), [])


class PreFixCounterProofTests(unittest.TestCase):
    """Two concrete pre-fix failures this contract suite closes."""

    def test_pre_fix_view_cannot_distinguish_carrier_from_delegator(self) -> None:
        legacy = LegacyProjection()
        legacy.add_user_from_prompt(CARRIER_MARK + "\nworker events", 1, 10.0)
        legacy.add_user_from_prompt("i387 Delegator prompt", 2, 20.0)
        old = legacy.snapshot()
        self.assertEqual(
            sorted(old["messages"][0]), sorted(old["messages"][1]),
            "pre-fix user rows must have one identical shape")
        for key in ("prompt_source", "carrier"):
            self.assertNotIn(key, old["messages"][0])
            self.assertNotIn(key, old["messages"][1])
        self.assertNotIn("source", old["turns"][0])
        self.assertNotIn("source", old["turns"][1])

        fixed = holder_module.ViewProjection()
        fixed.add_user_from_prompt(
            CARRIER_MARK + "\nworker events", 1, 10.0,
            source="self", carrier=HOST_SCHEMA)
        fixed.add_user_from_prompt("i387 Delegator prompt", 2, 20.0)
        now = fixed.snapshot()
        self.assertEqual(now["messages"][0]["prompt_source"], "self")
        self.assertEqual(now["messages"][0]["carrier"], HOST_SCHEMA)
        self.assertEqual(now["messages"][1]["prompt_source"], "delegator")
        self.assertNotIn("carrier", now["messages"][1])
        self.assertEqual([turn["source"] for turn in now["turns"]],
                         ["self", "delegator"])

    def test_pre_fix_turn_ended_and_last_prompt_had_no_source(self) -> None:
        turn = {"fingerprint": "sha256:carrier",
                "written_at": 10.0, "prompt_source": "self"}
        ended = legacy_turn_ended(turn)
        last = legacy_last_prompt(turn)
        self.assertNotIn("prompt_source", ended)
        self.assertNotIn("source", last)
        # The same turn data through the current holder is checked against the
        # real event log and record in
        # HolderProvenanceTests.test_pre_fix_record_and_event_shapes_have_no_source.


class StubAgent:
    """The AgentConnection facts the in-process holder tests need."""

    def __init__(self, *, fail_write: bool = False) -> None:
        self.proc = types.SimpleNamespace(pid=os.getpid())
        self.exited = threading.Event()
        self.lock = threading.Lock()
        self.pending_out: dict[str, dict[str, object]] = {}
        self.unknown_updates = 0
        self.malformed_lines = 0
        self.handler_errors: list[dict[str, object]] = []
        self.exit_code: int | None = 0
        self.exit_signal: int | None = None
        self.next_id = 100
        self.fail_write = fail_write

    def send_request(self, method: str, params: dict[str, object]) -> int:
        request_id = self.next_id
        self.next_id += 1
        if not self.fail_write:
            self.pending_out[holder_module.normalize_id(request_id)] = {
                "response": None, "event": threading.Event()}
        return request_id

    def wait_response(self, request_id: int, timeout: float | None
                      ) -> dict[str, object]:
        return {"result": {"stopReason": "end_turn"}}

    def send_message(self, message: dict[str, object]) -> bool:
        return True

    def cancel_outbound(self, request_id: object) -> bool:
        return True


class HolderProvenanceTests(unittest.TestCase):
    """Real holder methods and real record/event files, with a stub agent."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i387-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session_seq = 0
        self.holders: list[Any] = []
        self.saved_env = {key: value for key, value in os.environ.items()
                          if key.startswith("KAOLA_")}
        for key in list(self.saved_env):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key in list(os.environ):
            if key.startswith("KAOLA_"):
                os.environ.pop(key, None)
        os.environ.update(self.saved_env)
        for holder in self.holders:
            try:
                holder.agent.exited.set()
            except Exception:
                pass
        last_error: OSError | None = None
        for _ in range(25):
            try:
                self.tmp.cleanup()
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.2)
        if last_error is not None:
            raise last_error

    def make_holder(self, suffix: str, *, fail_write: bool = False):
        self.session_seq += 1
        session = f"grok-w387-{suffix}-{os.getpid()}-{self.session_seq}"
        digest = hashlib.sha256(str(self.repo).encode("utf-8")).hexdigest()[:16]
        record_dir = self.record_root / "grok" / session / digest
        record_dir.mkdir(parents=True)
        args = argparse.Namespace(
            record_dir=str(record_dir), socket=str(self.root / f"{session}.sock"),
            platform="grok", session=session, repo=str(self.repo), init_meta="",
            command="stub", resume=None, use_continue=False,
            session_role="worker", host_entry=None, accepted_revision="",
            start_selection="", baseline_exempt="", cli_version="")
        holder = holder_module.Holder(args)
        stub = StubAgent(fail_write=fail_write)
        holder.agent = stub
        holder.agent_exited = stub.exited
        holder.heartbeat_host = None
        holder.dispatched_by = None
        holder.host_entry = None
        holder.state = "ready"
        holder.acp_session_id = "mock-session-1"
        holder.session_role = "worker"
        holder._await_prompt = lambda request_id: None
        holder._await_agent_turn = lambda turn: None
        holder._delegator_turn_end_reason = lambda turn: None
        self.holders.append(holder)
        return holder, stub, args

    def read_events(self, holder) -> list[dict[str, Any]]:
        path = Path(holder.record_dir) / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def read_record(self, holder) -> dict[str, Any]:
        return json.loads((Path(holder.record_dir) / "record.json").read_text(
            encoding="utf-8"))

    def finish(self, holder, receipt: dict[str, Any]) -> None:
        holder.on_prompt_response(
            receipt["turn_request_id"], {"result": {"stopReason": "end_turn"}})

    def assert_no_internal_rows(self, view: dict[str, Any]) -> None:
        self.assertEqual(internal_keys(view), [])

    def test_delegator_chain_row_turn_event_and_record(self) -> None:
        holder, _stub, _args = self.make_holder("delegator")
        receipt = holder.op_prompt({"text": "delegator text", "wait": False})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        view = holder.op_view({})
        row = view["messages"][0]
        self.assertEqual(row["role"], "user")
        self.assertEqual(row["prompt_source"], "delegator")
        self.assertNotIn("carrier", row)
        turn = view["turns"][0]
        self.assertEqual(turn["source"], "delegator")
        self.assertNotIn("carrier", turn)
        self.assert_no_internal_rows(view)
        self.finish(holder, receipt)
        ended = [event for event in self.read_events(holder)
                 if event.get("kind") == "turn_ended"]
        self.assertEqual(len(ended), 1, ended)
        self.assertEqual(ended[0]["prompt_source"], "delegator")
        self.assertEqual(self.read_record(holder)["last_prompt"]["source"],
                         "delegator")

    def test_self_chain_row_turn_event_and_record(self) -> None:
        holder, _stub, _args = self.make_holder("self")
        receipt = holder.op_prompt(
            {"text": CARRIER_MARK + "\nworker events", "wait": False,
             "_prompt_source": "self", "_prompt_carrier": HOST_SCHEMA})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        view = holder.op_view({})
        row = view["messages"][0]
        self.assertEqual(row["prompt_source"], "self")
        self.assertEqual(row["carrier"], HOST_SCHEMA)
        turn = view["turns"][0]
        self.assertEqual(turn["source"], "self")
        self.assertEqual(turn["carrier"], HOST_SCHEMA)
        self.assert_no_internal_rows(view)
        self.finish(holder, receipt)
        ended = [event for event in self.read_events(holder)
                 if event.get("kind") == "turn_ended"]
        self.assertEqual(ended[-1]["prompt_source"], "self")
        record = self.read_record(holder)
        self.assertEqual(record["last_prompt"]["source"], "self")

    def test_pre_fix_record_and_event_shapes_have_no_source(self) -> None:
        """The same turn data: old event/record shapes vs the real new files."""
        holder, _stub, _args = self.make_holder("pre-fix-record")
        receipt = holder.op_prompt(
            {"text": CARRIER_MARK, "wait": False,
             "_prompt_source": "self", "_prompt_carrier": HOST_SCHEMA})
        self.finish(holder, receipt)
        turn = holder.turn
        self.assertNotIn("prompt_source", legacy_turn_ended(turn))
        self.assertNotIn("source", legacy_last_prompt(turn))
        ended = [event for event in self.read_events(holder)
                 if event.get("kind") == "turn_ended"][-1]
        self.assertEqual(ended["prompt_source"], "self")
        self.assertEqual(self.read_record(holder)["last_prompt"]["source"], "self")

    def test_invalid_source_defaults_and_bad_carrier_is_omitted(self) -> None:
        holder, _stub, _args = self.make_holder("invalid")
        receipt = holder.op_prompt(
            {"text": "not internal", "wait": False,
             "_prompt_source": "self-ish", "_prompt_carrier": "not a schema id"})
        view = holder.op_view({})
        self.assertEqual(view["messages"][0]["prompt_source"], "delegator")
        self.assertNotIn("carrier", view["messages"][0])
        self.finish(holder, receipt)
        ended = [event for event in self.read_events(holder)
                 if event.get("kind") == "turn_ended"]
        self.assertEqual(ended[-1]["prompt_source"], "delegator")
        self.assertEqual(self.read_record(holder)["last_prompt"]["source"],
                         "delegator")

    def test_socket_entry_strips_both_internal_prompt_arguments(self) -> None:
        holder, _stub, _args = self.make_holder("socket")
        receipt = holder.handle_request({
            "op": "prompt",
            "params": {"text": "socket text", "wait": False,
                       "_prompt_source": "self",
                       "_prompt_carrier": HOST_SCHEMA,
                       "_client_message_id_registered": True},
        })
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        view = holder.op_view({})
        row = view["messages"][0]
        self.assertEqual(row["text"], "socket text")
        self.assertEqual(row["prompt_source"], "delegator")
        self.assertNotIn("carrier", row)
        turn = view["turns"][0]
        self.assertEqual(turn["source"], "delegator")
        self.assertNotIn("carrier", turn)
        self.finish(holder, receipt)
        ended = [event for event in self.read_events(holder)
                 if event.get("kind") == "turn_ended"]
        self.assertEqual(ended[-1]["prompt_source"], "delegator")
        self.assertEqual(self.read_record(holder)["last_prompt"]["source"],
                         "delegator")

    def test_failed_write_still_names_the_attempted_source(self) -> None:
        holder, _stub, _args = self.make_holder("failed", fail_write=True)
        receipt = holder.op_prompt(
            {"text": "unwritten", "wait": False,
             "_prompt_source": "self", "_prompt_carrier": HOST_SCHEMA})
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "acp-write-failed", receipt)
        record = self.read_record(holder)
        self.assertEqual(record["last_prompt"]["source"], "self")
        self.assertEqual(record["last_prompt"]["mutation_status"], "not_started")

    def test_last_prompt_source_survives_a_holder_reload(self) -> None:
        holder, _stub, args = self.make_holder("reload")
        receipt = holder.op_prompt(
            {"text": CARRIER_MARK, "wait": False,
             "_prompt_source": "self", "_prompt_carrier": HOST_SCHEMA})
        self.finish(holder, receipt)
        self.assertEqual(self.read_record(holder)["last_prompt"]["source"], "self")
        restarted = holder_module.Holder(args)
        try:
            # A new holder process starts with an empty projection; the durable
            # record is the reconnect-readable fact.
            self.assertEqual(restarted.op_view({})["messages"], [])
            self.assertEqual(restarted.last_prompt.get("source"), "self")
        finally:
            restarted.agent_exited.set()

    def test_steer_interrupt_resend_never_inherits_the_target_source(self) -> None:
        holder, _stub, _args = self.make_holder("steer-matrix")
        captured: list[dict[str, Any]] = []

        def fake_prompt(params: dict[str, Any]) -> dict[str, Any]:
            captured.append(dict(params))
            return {"outcome": "in_progress", "mutation_status": "in_progress",
                    "prompt_fingerprint": "sha256:resend", "turn_request_id": 99,
                    "dispatch_event_cursor": 1, "event_cursor": 2}

        def confirmed_cancel(target, timeout):
            return ({"outcome": "canceled", "stop_reason": "cancelled",
                     "mutation_status": "completed",
                     "request_id": target.get("request_id"),
                     "cancel_sent": True}, True,
                    {"is_current": True, "active": False,
                     "stop_reason": "cancelled",
                     "mutation_status": "completed"})

        holder.op_prompt = fake_prompt
        rows = [
            ("self", True, None, False, "steer_interrupted_and_resent"),
            ("delegator", True, None, False, "steer_interrupted_and_resent"),
            ("self", False, None, False, "steer_resent_without_interrupt"),
            ("delegator", False, None, False, "steer_resent_without_interrupt"),
            ("self", True, {"_prompt_source": "self",
                            "_prompt_carrier": HOST_SCHEMA}, False,
             "steer_interrupted_and_resent"),
            ("self", True, None, True, "steer_interrupted_and_resent"),
        ]
        for source, active, extra, agent_initiated, expected_outcome in rows:
            with self.subTest(source=source, active=active, extra=extra,
                              agent_initiated=agent_initiated):
                captured.clear()
                turn = holder._empty_turn()
                turn.update({
                    "active": active, "request_id": 10,
                    "prompt_source": source,
                    "agent_initiated": agent_initiated,
                    "mutation_status": "in_progress" if active else "completed",
                    "written_at": 10.0, "fingerprint": "sha256:target",
                })
                holder.turn = turn
                holder.cancel_turn = confirmed_cancel if active else mock.Mock()
                params = {"text": f"steer {source} {active}", "timeout": 1}
                if extra:
                    params.update(extra)
                receipt = holder.op_steer_interrupt(params)
                self.assertEqual(receipt.get("outcome"), expected_outcome,
                                 receipt)
                self.assertEqual(receipt.get("steer_consumed"), True)
                self.assertTrue(captured, "the composite sent no follow-up")
                follow = captured[-1]
                self.assertNotIn("_prompt_source", follow)
                self.assertNotIn("_prompt_carrier", follow)
                self.assertEqual(sorted(follow),
                                 ["expected_holder_instance_id", "text", "wait"])
                self.assertEqual(follow["text"], params["text"])


class LivePromptSourceTests(unittest.TestCase):
    """A real holder, the real CLI and the mock ACP agent."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i387-live-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.repo = Path(os.path.realpath(self.repo))
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.mock_log = self.root / "mock-events.jsonl"
        self.session = "grok-w387-orchestrator-main"
        self.started = False
        self.scenario = "normal"
        self.mock_command = " ".join([
            sys.executable, str(MOCK), "--scenario", self.scenario])
        self.saved_env = {key: value for key, value in os.environ.items()
                          if key.startswith("KAOLA_")}
        for key in list(self.saved_env):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        if self.started:
            self.cli("stop", "--force", check=False, timeout=30)
        for key in list(os.environ):
            if key.startswith("KAOLA_"):
                os.environ.pop(key, None)
        os.environ.update(self.saved_env)
        last_error: OSError | None = None
        for _ in range(25):
            try:
                self.tmp.cleanup()
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.2)
        if last_error is not None:
            raise last_error

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env.update({
            "KAOLA_LAUNCH_BACKEND": "direct",
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "KAOLA_DELEGATOR_WEBHOOK_CONFIG": str(
                self.root / "config" / "delegator-webhook.json"),
            "HOME": str(self.home),
            "MOCK_ACP_LOG": str(self.mock_log),
        })
        return env

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 60) -> dict[str, Any]:
        argv = [
            sys.executable, str(CLI), "grok", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command, *args,
        ]
        proc = subprocess.run(argv, capture_output=True, text=True,
                              env=self.env(), timeout=timeout)
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command} did not emit JSON: "
                      f"stdout={proc.stdout!r} stderr={proc.stderr!r}")
        if check and payload.get("error"):
            self.fail(f"{command} failed: {payload.get('error')} {payload}")
        return payload

    def record_dir(self) -> Path:
        digest = hashlib.sha256(str(self.repo).encode("utf-8")).hexdigest()[:16]
        return self.record_root / "grok" / self.session / digest

    def wait_record(self, timeout: float = 20) -> dict[str, Any]:
        def read():
            path = self.record_dir() / "record.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        record = wait_for(read, timeout, "record.json")
        return record

    def holder_op(self, sock: Path, op: str, params: dict[str, Any]) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(20)
            connection.connect(str(sock))
            request = {"op": op, "request_id": f"i387-{op}",
                       "params": params}
            connection.sendall(json.dumps(request).encode("utf-8") + b"\n")
            buffer = bytearray()
            while b"\n" not in buffer:
                data = connection.recv(65536)
                if not data:
                    break
                buffer.extend(data)
        line = bytes(buffer).split(b"\n", 1)[0]
        if not line:
            raise AssertionError(f"holder returned no reply to {op}")
        return json.loads(line.decode("utf-8"))

    def view(self) -> dict[str, Any]:
        return self.cli("view", check=False)

    def wait_view(self, predicate, label: str, timeout: float = 25
                  ) -> dict[str, Any]:
        return wait_for(lambda: (payload if predicate(payload := self.view())
                                 else None), timeout, label)

    @staticmethod
    def user_row(view: dict[str, Any], needle: str) -> dict[str, Any] | None:
        for row in view.get("messages") or []:
            if row.get("role") == "user" and needle in (row.get("text") or ""):
                return row
        return None

    def start_host(self) -> dict[str, Any]:
        receipt = self.cli("start")
        self.started = True
        self.assertEqual(receipt.get("session_role"), "host", receipt)
        return receipt

    def read_events(self) -> list[dict[str, Any]]:
        path = self.record_dir() / "events.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def stage_worker_event(self, sock: Path) -> dict[str, Any]:
        return self.holder_op(sock, "worker_event", {
            "kind": "idle",
            "platform": "grok",
            "session": "grok-w387-worker-a",
            "repo": str(self.repo),
            "reason": "outcome=turn_completed stop_reason=end_turn",
            "event_cursor": 387001,
        })

    def test_carrier_and_delegator_full_chain_live(self) -> None:
        self.start_host()
        record = self.wait_record()
        sock = Path(record["socket_path"])
        staged = self.stage_worker_event(sock)
        self.assertFalse(staged.get("error"), staged)

        carrier_view = self.wait_view(
            lambda view: (self.user_row(view, CARRIER_MARK)
                          and not view["turn"]["active"]),
            "carrier turn end")
        carrier_row = self.user_row(carrier_view, CARRIER_MARK)
        self.assertIsNotNone(carrier_row, carrier_view["messages"])
        self.assertEqual(carrier_row["prompt_source"], "self")
        self.assertEqual(carrier_row["carrier"], HOST_SCHEMA)
        carrier_turn = next(turn for turn in carrier_view["turns"]
                            if turn["start_cursor"] == carrier_row["cursor"])
        self.assertEqual(carrier_turn["source"], "self")
        self.assertEqual(carrier_turn["carrier"], HOST_SCHEMA)
        self.assertEqual(self.wait_record()["last_prompt"]["source"], "self")

        delegator_text = "i387 Delegator prompt: report the last worker event."
        sent = self.cli("send", "--text", delegator_text, "--no-wait")
        self.assertFalse(sent.get("error"), sent)
        view = self.wait_view(
            lambda view: (self.user_row(view, delegator_text)
                          and not view["turn"]["active"]),
            "delegator turn end")
        delegator_row = self.user_row(view, delegator_text)
        self.assertIsNotNone(delegator_row, view["messages"])
        self.assertEqual(delegator_row["prompt_source"], "delegator")
        self.assertNotIn("carrier", delegator_row)
        delegator_turn = next(turn for turn in view["turns"]
                              if turn["start_cursor"] == delegator_row["cursor"])
        self.assertEqual(delegator_turn["source"], "delegator")
        self.assertNotIn("carrier", delegator_turn)
        self.assertEqual(internal_keys(view), [])
        for message in view["messages"]:
            if message["role"] == "assistant":
                self.assertNotIn("prompt_source", message)
                self.assertNotIn("carrier", message)

        ended = [event for event in self.read_events()
                 if event.get("kind") == "turn_ended"]
        self.assertEqual(sorted(event["prompt_source"] for event in ended),
                         ["delegator", "self"])
        self.assertEqual(self.wait_record()["last_prompt"]["source"],
                         "delegator")

        # The socket entry must strip both internal arguments a client could
        # try to attach, so this row is an ordinary Delegator prompt.
        socket_text = "i387 socket prompt with internal claims."
        receipt = self.holder_op(sock, "prompt", {
            "text": socket_text, "wait": False,
            "_prompt_source": "self", "_prompt_carrier": HOST_SCHEMA,
            "_client_message_id_registered": True,
        })
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        view = self.wait_view(
            lambda view: (self.user_row(view, socket_text)
                          and not view["turn"]["active"]),
            "socket prompt turn end")
        row = self.user_row(view, socket_text)
        self.assertEqual(row["prompt_source"], "delegator")
        self.assertNotIn("carrier", row)
        turn = next(turn for turn in view["turns"]
                    if turn["start_cursor"] == row["cursor"])
        self.assertEqual(turn["source"], "delegator")
        self.assertNotIn("carrier", turn)
        ended = [event for event in self.read_events()
                 if event.get("kind") == "turn_ended"]
        self.assertEqual(ended[-1]["prompt_source"], "delegator")
        self.assertEqual(self.wait_record()["last_prompt"]["source"],
                         "delegator")

        # The record line is what a new client can read after the holder (and
        # its in-memory projection) is gone.
        stopped = self.cli("stop", "--force")
        self.started = False
        self.assertTrue(stopped.get("stopped"), stopped)
        final = json.loads((self.record_dir() / "record.json").read_text(
            encoding="utf-8"))
        self.assertEqual(final["last_prompt"]["source"], "delegator")

    def test_steer_interrupt_self_carrier_resend_is_delegator_live(self) -> None:
        self.scenario = "hang_until_cancel"
        self.mock_command = " ".join([
            sys.executable, str(MOCK), "--scenario", self.scenario])
        self.start_host()
        record = self.wait_record()
        sock = Path(record["socket_path"])
        staged = self.stage_worker_event(sock)
        self.assertFalse(staged.get("error"), staged)
        view = self.wait_view(
            lambda view: (self.user_row(view, CARRIER_MARK)
                          and view["turn"]["active"]),
            "carrier turn active")
        carrier_row = self.user_row(view, CARRIER_MARK)
        before = self.wait_record()
        carrier_fingerprint = before["last_prompt"]["fingerprint"]
        self.assertEqual(before["last_prompt"]["source"], "self")

        steer_text = "i387 interrupt: report the carrier turn, then wait."
        receipt = self.cli("steer", "--text", steer_text,
                           "--steer-mode", "interrupt")
        self.assertTrue(receipt.get("interrupted"), receipt)
        self.assertTrue(receipt.get("steer_consumed"), receipt)
        view = self.wait_view(
            lambda view: (self.user_row(view, steer_text)
                          and view["turn"]["active"]),
            "steer resend turn")
        row = self.user_row(view, steer_text)
        self.assertEqual(row["prompt_source"], "delegator")
        self.assertNotIn("carrier", row)
        turn = next(turn for turn in view["turns"]
                    if turn["start_cursor"] == row["cursor"])
        self.assertEqual(turn["source"], "delegator")
        self.assertNotIn("carrier", turn)

        ended = [event for event in self.read_events()
                 if event.get("kind") == "turn_ended"
                 and event.get("prompt_fingerprint") == carrier_fingerprint]
        self.assertTrue(ended, "the cancelled carrier turn has no turn_ended")
        self.assertEqual(ended[-1]["prompt_source"], "self")
        record = self.wait_record()
        self.assertEqual(record["last_prompt"]["source"], "delegator")
        self.assertEqual(record["last_prompt"]["fingerprint"],
                         receipt["new_prompt_fingerprint"])


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
