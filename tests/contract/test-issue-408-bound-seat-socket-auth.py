#!/usr/bin/env python3
"""Issue #408: dispatcher-binding enforcement on a heartbeat-bound seat.

The Host reproduction is the failing-before case: a foreign same-UID process
speaking the socket protocol directly — no ``KAOLA_ACP_DISPATCHER``, no
``expected_holder_instance_id``, no ``auth_token`` — had its raw
``{"op":"prompt"}`` accepted by a worker seat genuinely bound to a live Host,
and the foreign prompt was normalized to ``"delegator"`` provenance.

These tests drive the candidate checkout's holder and kaola-acp client paths.
They do not start a CLI, and they do not read an installed Skill root.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from unittest.mock import patch
import stat
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HOLDER_PATH = PROJECT / "scripts" / "kaola-acp-holder.py"
ACP_PATH = PROJECT / "scripts" / "kaola-acp.py"
PATHS_PATH = PROJECT / "scripts" / "kaola-acp-paths.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


holder_module = load("kaola_acp_holder_i408", HOLDER_PATH)
acp_module = load("kaola_acp_i408", ACP_PATH)
paths_module = load("kaola_acp_paths_i408", PATHS_PATH)


class StubProc:
    pid = 4242


class StubAgent:
    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
        self.exit_code: int | None = None
        self.unknown_updates = 0
        self.sent: list[dict] = []
        self.pending_out: dict = {}
        self.malformed_lines = 0
        self.handler_errors = 0
        self.next_id = 0
        self.release_wait = threading.Event()

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(self.next_id)] = method
        self.sent.append({"method": method, "id": self.next_id, "params": params})
        return self.next_id

    def prompts(self) -> list[dict]:
        return [row for row in self.sent if row.get("method") == "session/prompt"]

    def wait_response(self, request_id, timeout):
        self.release_wait.wait(0.2)
        return {"result": {"stopReason": "end_turn"}}


def make_holder(root: Path, session: str, *, bound: bool) -> tuple:
    record_dir = root / "record"
    args = argparse.Namespace(
        record_dir=str(record_dir), socket=str(root / "h.sock"),
        platform="zcode", session=session, repo=str(root),
        init_meta="", command="stub",
    )
    # The holder reads its binding from KAOLA_ACP_HEARTBEAT_HOST /
    # KAOLA_ACP_DISPATCHER at construction. A run inside a managed seat would
    # otherwise inherit that ambient binding, so the fixture clears it.
    ambient = {key: os.environ.pop(key) for key in
               ("KAOLA_ACP_HEARTBEAT_HOST", "KAOLA_ACP_HEARTBEAT_HOST_SOCKET",
                "KAOLA_ACP_DISPATCHER", "KAOLA_ACP_CHILD_RECORD")
               if key in os.environ}
    try:
        holder = holder_module.Holder(args)
    finally:
        os.environ.update(ambient)
    agent = StubAgent()
    holder.agent = agent
    holder.acp_session_id = "ses-408"
    holder.state = "ready"
    if bound:
        # The defect's seat: a worker genuinely bound to a live Host holder.
        holder.heartbeat_host = {
            "platform": "zcode", "session": "zcode-KPR-i408-host",
            "repo": str(root), "socket": str(root / "host.sock")}
        holder.dispatched_by = {
            "platform": "zcode", "session": "zcode-KPR-i408-host",
            "repo": str(root), "holder_instance_id": "host-holder-id"}
    return holder, agent, record_dir


def event_rows(record_dir: Path) -> list[dict]:
    path = record_dir / "events.jsonl"
    try:
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def refusal_events(record_dir: Path) -> list[dict]:
    return [row for row in event_rows(record_dir)
            if row.get("kind") == "socket_op_refused"]


class BoundSeatAuth(unittest.TestCase):
    """The bound seat: heartbeat_host set, dispatcher identity recorded."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i408-holder-")
        self.root = Path(self._tmp.name)
        self.holder, self.agent, self.record_dir = make_holder(
            self.root, "zcode-KPR-i408-bound", bound=True)
        self.token = self.holder.auth_token
        self.hid = self.holder.holder_instance_id

    def tearDown(self) -> None:
        self.agent.release_wait.set()
        for thread in threading.enumerate():
            if thread is not threading.current_thread() and thread.name.startswith("Thread-"):
                thread.join(timeout=1)
        self._tmp.cleanup()

    def test_holder_mints_a_private_token_file(self) -> None:
        token_path = self.record_dir / "auth.token"
        self.assertTrue(token_path.is_file())
        self.assertEqual(stat.S_IMODE(token_path.stat().st_mode), 0o600)
        self.assertEqual(paths_module.read_auth_token(self.record_dir),
                         self.token)
        self.assertNotEqual(self.token, self.hid)
        # The capability never appears in the record or a state reply.
        self.holder.write_record()
        record = json.loads((self.record_dir / "record.json").read_text())
        self.assertNotIn("auth_token", json.dumps(record))
        state = self.holder.handle_request({"op": "state", "params": {}})
        self.assertNotIn("auth_token", json.dumps(state))

    def test_foreign_prompt_without_proof_is_refused(self) -> None:
        """The Host reproduction: a raw same-UID prompt with no dispatcher
        context is refused before it can start a turn."""
        receipt = self.holder.handle_request(
            {"op": "prompt", "params": {"text": "foreign write", "wait": False}})
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "unauthenticated", receipt)
        self.assertEqual(receipt.get("mutation_status"), "not_started")
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(self.agent.prompts(), [])
        self.assertIs(self.holder.turn.get("active"), False)
        # No prompt row, no delegator attribution, one named refusal event.
        self.assertEqual(self.holder.last_prompt.get("fingerprint"), None)
        refused = refusal_events(self.record_dir)
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0]["op"], "prompt")
        self.assertEqual(refused[0]["reason"], "unauthenticated")

    def test_repeated_foreign_prompts_never_wedge_the_holder(self) -> None:
        """The consumer crash loop: repeated refused foreign writes stay
        idempotent refusals — no turn, no crash, the seat stays usable."""
        for _ in range(5):
            receipt = self.holder.handle_request(
                {"op": "prompt",
                 "params": {"text": "foreign write", "wait": False}})
            self.assertEqual((receipt.get("error") or {}).get("code"),
                             "unauthenticated", receipt)
        self.assertEqual(self.agent.prompts(), [])
        self.assertIs(self.holder.turn.get("active"), False)
        self.assertEqual(self.holder.state, "ready")
        refused = refusal_events(self.record_dir)
        self.assertEqual(len(refused), 5)
        self.assertTrue(all(row["op"] == "prompt" for row in refused))
        # The seat still admits a legitimate prompt after the storm.
        good = self.holder.handle_request({"op": "prompt", "params": {
            "text": "legitimate", "wait": False,
            "auth_token": self.token,
            "expected_holder_instance_id": self.hid}})
        self.assertEqual(good.get("outcome"), "in_progress", good)
        self.assertEqual(len(self.agent.prompts()), 1)

    def test_legitimate_prompt_with_proof_is_admitted(self) -> None:
        receipt = self.holder.handle_request({"op": "prompt", "params": {
            "text": "dispatch execute", "wait": False,
            "auth_token": self.token,
            "expected_holder_instance_id": self.hid}})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        self.assertEqual(len(self.agent.prompts()), 1)
        # #380/#387: the socket path still strips internal provenance, so a
        # socket-admitted prompt is attributed "delegator", never "self".
        self.assertEqual(self.holder.last_prompt.get("source"), "delegator")
        self.assertEqual(refusal_events(self.record_dir), [])
        # The capability is wire-only: it is stripped before the op runs, so
        # it persists nowhere — not in last_prompt, the record, or the ACP
        # payload handed to the agent.
        self.assertNotIn("auth_token", json.dumps(self.holder.last_prompt))
        self.assertNotIn("auth_token",
                         json.dumps(self.agent.prompts()))
        self.assertNotIn(self.token, json.dumps(self.holder.last_prompt))

    def test_proof_prompt_claiming_self_source_is_still_stripped(self) -> None:
        receipt = self.holder.handle_request({"op": "prompt", "params": {
            "text": "claim self", "wait": False, "_prompt_source": "self",
            "auth_token": self.token,
            "expected_holder_instance_id": self.hid}})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        self.assertEqual(self.holder.last_prompt.get("source"), "delegator")

    def test_wrong_expected_id_is_holder_instance_mismatch(self) -> None:
        receipt = self.holder.handle_request({"op": "prompt", "params": {
            "text": "wrong id", "wait": False,
            "auth_token": self.token,
            "expected_holder_instance_id": "not-this-holder"}})
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-instance-mismatch", receipt)
        self.assertEqual(error.get("expected_holder_instance_id"),
                         "not-this-holder")
        self.assertEqual(error.get("holder_instance_id"), self.hid)
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(self.agent.prompts(), [])
        # The id check lives once in the gate: a bound-seat wrong id stamps
        # the same socket_op_refused event kind as every other refusal, not
        # the older per-op holder_instance_mismatch shape.
        refused = refusal_events(self.record_dir)
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0]["reason"], "holder-instance-mismatch")
        self.assertEqual(refused[0]["expected_holder_instance_id"],
                         "not-this-holder")
        self.assertEqual([row for row in event_rows(self.record_dir)
                          if row.get("kind") == "holder_instance_mismatch"], [])

    def test_malformed_token_is_a_typed_invalid_token_refusal(self) -> None:
        """secrets.compare_digest raises TypeError on a non-ASCII str; a
        malformed credential is the typed invalid-token refusal instead, and
        the connection path stays healthy enough to admit a good prompt."""
        for bad in ("tök-408", {"nested": "dict"}, 7):
            with self.subTest(bad=bad):
                receipt = self.holder.handle_request({"op": "prompt", "params": {
                    "text": "bad token", "wait": False, "auth_token": bad,
                    "expected_holder_instance_id": self.hid}})
                self.assertEqual((receipt.get("error") or {}).get("code"),
                                 "invalid-token", (bad, receipt))
                self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(self.agent.prompts(), [])
        self.assertEqual([row["reason"] for row in refusal_events(self.record_dir)],
                         ["invalid-token"] * 3)
        # Holder health: the same seat still admits a legitimate prompt.
        good = self.holder.handle_request({"op": "prompt", "params": {
            "text": "after", "wait": False, "auth_token": self.token,
            "expected_holder_instance_id": self.hid}})
        self.assertEqual(good.get("outcome"), "in_progress", good)

    def test_watchdog_tick_restores_the_minted_token_file(self) -> None:
        """A deleted or overwritten auth.token is rewritten from the
        in-memory value — never rotated — on the existing tick."""
        token_path = self.record_dir / "auth.token"
        token_path.unlink()
        self.assertIsNone(paths_module.read_auth_token(self.record_dir))
        self.holder._restore_auth_token_file()
        self.assertEqual(paths_module.read_auth_token(self.record_dir),
                         self.token)
        self.assertEqual(stat.S_IMODE(token_path.stat().st_mode), 0o600)
        # An overwritten file heals to the in-memory value, which is not
        # re-minted.
        token_path.write_text("stale-bytes\n", encoding="utf-8")
        self.holder._restore_auth_token_file()
        self.assertEqual(paths_module.read_auth_token(self.record_dir),
                         self.token)
        # A correct file is not rewritten.
        with patch.object(holder_module.acp_paths, "write_auth_token",
                          side_effect=AssertionError("rewrote a valid file")):
            self.holder._restore_auth_token_file()

    def test_right_token_but_omitted_id_is_refused(self) -> None:
        receipt = self.holder.handle_request({"op": "prompt", "params": {
            "text": "no id", "wait": False, "auth_token": self.token}})
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "holder-instance-required", receipt)
        self.assertEqual(self.agent.prompts(), [])
        refused = refusal_events(self.record_dir)
        self.assertEqual([row["reason"] for row in refused],
                         ["holder-instance-required"])

    def test_wrong_token_is_refused(self) -> None:
        receipt = self.holder.handle_request({"op": "prompt", "params": {
            "text": "bad token", "wait": False, "auth_token": "0" * 64,
            "expected_holder_instance_id": self.hid}})
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "unauthenticated", receipt)
        self.assertEqual(self.agent.prompts(), [])

    def test_every_mutating_op_is_gated(self) -> None:
        """Every op a bound seat mutates on refuses an unauthenticated caller
        — and a refused ``stop`` must not stop anything."""
        for op in ("prompt", "steer", "steer_interrupt", "cancel", "permit",
                   "stop", "wake_delegator", "worker_event", "compact_notice",
                   "set_config_option", "record_start_evidence",
                   "rebind_heartbeat_host"):
            with self.subTest(op=op):
                receipt = self.holder.handle_request(
                    {"op": op, "params": {"text": "x"}})
                self.assertEqual((receipt.get("error") or {}).get("code"),
                                 "unauthenticated", (op, receipt))
        self.assertEqual(self.agent.prompts(), [])
        self.assertIs(self.holder.stop_requested, False)
        self.assertEqual(self.holder.state, "ready")
        refused = refusal_events(self.record_dir)
        self.assertEqual(len(refused), len(holder_module.BOUND_WRITE_OPS))
        self.assertEqual({row["op"] for row in refused},
                         set(holder_module.BOUND_WRITE_OPS))

    def test_read_ops_stay_open_on_a_bound_seat(self) -> None:
        state = self.holder.handle_request({"op": "state", "params": {}})
        self.assertEqual(state.get("state"), "ready", state)
        view = self.holder.handle_request({"op": "view", "params": {}})
        self.assertNotIn("error", view)
        wait = self.holder.handle_request(
            {"op": "wait", "params": {"timeout": 0}})
        self.assertNotEqual((wait.get("error") or {}).get("code"),
                            "unauthenticated")
        self.assertEqual(refusal_events(self.record_dir), [])

    def test_holder_restart_mints_a_fresh_token(self) -> None:
        """Drain-restart/resume adoption: a replacement holder instance on the
        same record dir mints its own token; the dead one's is refused."""
        old_token = self.token
        old_id = self.hid
        successor, agent2, _ = make_holder(
            self.root, "zcode-KPR-i408-bound", bound=True)
        self.assertNotEqual(successor.auth_token, old_token)
        self.assertNotEqual(successor.holder_instance_id, old_id)
        # The record dir now holds the successor's token.
        self.assertEqual(paths_module.read_auth_token(self.record_dir),
                         successor.auth_token)
        stale = successor.handle_request({"op": "prompt", "params": {
            "text": "stale token", "wait": False,
            "auth_token": old_token,
            "expected_holder_instance_id": successor.holder_instance_id}})
        self.assertEqual((stale.get("error") or {}).get("code"),
                         "unauthenticated", stale)
        adopted = successor.handle_request({"op": "prompt", "params": {
            "text": "adopted", "wait": False,
            "auth_token": successor.auth_token,
            "expected_holder_instance_id": successor.holder_instance_id}})
        self.assertEqual(adopted.get("outcome"), "in_progress", adopted)
        self.assertEqual(len(agent2.prompts()), 1)


class UnboundSeatAuth(unittest.TestCase):
    """An unbound seat — standalone or Host-role — keeps its documented
    caller-asserted behavior exactly."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i408-unbound-")
        self.root = Path(self._tmp.name)
        self.holder, self.agent, self.record_dir = make_holder(
            self.root, "zcode-KPR-i408-solo", bound=False)

    def tearDown(self) -> None:
        self.agent.release_wait.set()
        for thread in threading.enumerate():
            if thread is not threading.current_thread() and thread.name.startswith("Thread-"):
                thread.join(timeout=1)
        self._tmp.cleanup()

    def test_unbound_prompt_needs_no_proof(self) -> None:
        receipt = self.holder.handle_request(
            {"op": "prompt", "params": {"text": "standalone", "wait": False}})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        self.assertEqual(len(self.agent.prompts()), 1)
        self.assertEqual(refusal_events(self.record_dir), [])

    def test_unbound_caller_asserted_id_still_checked(self) -> None:
        bad = self.holder.handle_request({"op": "prompt", "params": {
            "text": "x", "wait": False,
            "expected_holder_instance_id": "not-this-holder"}})
        self.assertEqual((bad.get("error") or {}).get("code"),
                         "holder-instance-mismatch")
        good = self.holder.handle_request({"op": "prompt", "params": {
            "text": "x", "wait": False,
            "expected_holder_instance_id": self.holder.holder_instance_id}})
        self.assertEqual(good.get("outcome"), "in_progress", good)


class ClientProof(unittest.TestCase):
    """The Runner client presents the token and fills the bound id."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i408-client-")
        self.root = Path(self._tmp.name)
        self.directory = self.root / "record"
        self.directory.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_socket_request_presents_the_record_dir_token(self) -> None:
        paths_module.write_auth_token(self.directory, "tok-408")
        captured: dict = {}

        class FakeConnection:
            def settimeout(self, value):
                pass

            def connect(self, path):
                pass

            def sendall(self, payload):
                captured["wire"] = json.loads(payload.decode("utf-8"))

            def recv(self, size):
                return b'{"outcome":"in_progress"}\n'

            def close(self):
                pass

        with patch.object(acp_module.socket, "socket",
                          return_value=FakeConnection()):
            reply = acp_module.socket_request(
                self.root / "h.sock", "prompt",
                {"text": "x", "wait": False}, 5.0, self.directory)
        self.assertEqual(reply.get("outcome"), "in_progress")
        params = captured["wire"]["params"]
        self.assertEqual(params["auth_token"], "tok-408")
        self.assertEqual(params["text"], "x")

    def test_socket_request_without_directory_sends_no_token(self) -> None:
        captured: dict = {}

        class FakeConnection:
            def settimeout(self, value):
                pass

            def connect(self, path):
                pass

            def sendall(self, payload):
                captured["wire"] = json.loads(payload.decode("utf-8"))

            def recv(self, size):
                return b'{"outcome":"in_progress"}\n'

            def close(self):
                pass

        with patch.object(acp_module.socket, "socket",
                          return_value=FakeConnection()):
            acp_module.socket_request(
                self.root / "h.sock", "prompt", {"text": "x"}, 5.0)
        self.assertNotIn("auth_token", captured["wire"]["params"])

    def _funnel_args(self) -> argparse.Namespace:
        return argparse.Namespace(command="stop", force=True,
                                  platform="zcode",
                                  session="zcode-KPR-i408-bound")

    def test_funnel_fills_expected_id_only_for_a_bound_record(self) -> None:
        captured: dict = {}
        record = {"holder_instance_id": "hid-live", "holder_pid": os.getpid(),
                  "heartbeat_host": {"platform": "zcode",
                                     "session": "host", "repo": str(self.root),
                                     "socket": str(self.root / "host.sock")}}
        with patch.object(acp_module, "read_record", return_value=record), \
                patch.object(acp_module, "sock_path",
                             return_value=self.root / "h.sock"), \
                patch.object(acp_module.Path, "exists", return_value=True), \
                patch.object(acp_module, "socket_request",
                             side_effect=lambda *a, **k: captured.update(
                                 {"args": a, "kwargs": k}) or
                             {"stopped": True}):
            acp_module._op_or_holder_lost(
                self._funnel_args(), str(self.root), self.directory,
                "stop", {"force": True}, 30.0)
        params = captured["args"][2]
        self.assertEqual(params["expected_holder_instance_id"], "hid-live")
        # The directory the token lives in reaches socket_request.
        self.assertEqual(captured["kwargs"]["directory"], self.directory)

    def test_funnel_keeps_omission_on_an_unbound_record(self) -> None:
        captured: dict = {}
        record = {"holder_instance_id": "hid-solo", "holder_pid": os.getpid()}
        with patch.object(acp_module, "read_record", return_value=record), \
                patch.object(acp_module, "sock_path",
                             return_value=self.root / "h.sock"), \
                patch.object(acp_module.Path, "exists", return_value=True), \
                patch.object(acp_module, "socket_request",
                             side_effect=lambda *a, **k: captured.update(
                                 {"args": a}) or {"stopped": True}):
            acp_module._op_or_holder_lost(
                self._funnel_args(), str(self.root), self.directory,
                "stop", {"force": True}, 30.0)
        self.assertNotIn("expected_holder_instance_id", captured["args"][2])

    def test_explicit_flag_wins_over_the_record_fill(self) -> None:
        captured: dict = {}
        record = {"holder_instance_id": "hid-live", "holder_pid": os.getpid(),
                  "heartbeat_host": {"platform": "zcode",
                                     "session": "host", "repo": str(self.root),
                                     "socket": str(self.root / "host.sock")}}
        with patch.object(acp_module, "read_record", return_value=record), \
                patch.object(acp_module, "sock_path",
                             return_value=self.root / "h.sock"), \
                patch.object(acp_module.Path, "exists", return_value=True), \
                patch.object(acp_module, "socket_request",
                             side_effect=lambda *a, **k: captured.update(
                                 {"args": a}) or {"stopped": True}):
            acp_module._op_or_holder_lost(
                self._funnel_args(), str(self.root), self.directory, "stop",
                {"force": True, "expected_holder_instance_id": "explicit"},
                30.0)
        self.assertEqual(captured["args"][2]["expected_holder_instance_id"],
                         "explicit")

    def test_send_still_puts_the_flag_on_the_prompt_op(self) -> None:
        captured: dict = {}

        def capture(args, repo, directory, op, params, timeout):
            captured["op"] = op
            captured["params"] = dict(params)
            return {"outcome": "in_progress", "mutation_status": "in_progress"}

        argv = [
            "kaola-acp.py", "zcode", "send",
            "--repo", str(PROJECT),
            "--session", "zcode-KPR-i408-bound",
            "--no-wait", "--text", "look",
            "--expected-holder-instance-id", "holder-live",
        ]
        with patch.object(acp_module, "op_or_holder_lost",
                          side_effect=capture), patch.object(
                sys, "argv", argv), redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(acp_module.main(), 0)
        self.assertEqual(captured["op"], "prompt")
        self.assertEqual(captured["params"]["expected_holder_instance_id"],
                         "holder-live")

    def test_peer_auth_reads_the_peer_record_dir(self) -> None:
        """The holder's own outbound ops present the peer's minted token plus
        the holder_instance_id the peer's live record names — not the stale
        dispatched_by a Host restart left behind."""
        holder, _, _ = make_holder(self.root, "zcode-KPR-i408-worker",
                                   bound=True)
        peer_dir = self.root / "peer" / "record"
        peer_dir.mkdir(parents=True)
        paths_module.write_auth_token(peer_dir, "peer-tok")
        (peer_dir / "record.json").write_text(
            json.dumps({"holder_instance_id": "peer-hid"}), encoding="utf-8")
        with patch.object(holder_module.acp_paths, "find_directory",
                          return_value=peer_dir):
            auth = holder._socket_peer_auth("zcode", "peer", str(self.root))
        self.assertEqual(auth, {"auth_token": "peer-tok",
                                "expected_holder_instance_id": "peer-hid"})
        with patch.object(holder_module.acp_paths, "find_directory",
                          side_effect=holder_module.acp_paths.RecordRootMismatch("x")):
            self.assertEqual(
                holder._socket_peer_auth("zcode", "gone", str(self.root)), {})


    def _bound_record(self) -> dict:
        return {"holder_instance_id": "hid-live", "holder_pid": os.getpid(),
                "heartbeat_host": {"platform": "zcode",
                                   "session": "host", "repo": str(self.root),
                                   "socket": str(self.root / "host.sock")}}

    def test_force_stop_falls_back_when_no_token_is_presentable(self) -> None:
        """stop --force on a bound seat that refuses unauthenticated reaches
        the argv-verified kill when this caller has no token to present — a
        deleted auth.token can never lock out force-stop."""
        record = self._bound_record()
        calls: dict = {}
        with patch.object(acp_module, "read_record", return_value=record), \
                patch.object(acp_module, "sock_path",
                             return_value=self.root / "h.sock"), \
                patch.object(acp_module.Path, "exists", return_value=True), \
                patch.object(acp_module, "socket_request",
                             return_value={"error": {"code": "unauthenticated",
                                                     "mutation_status": "not_started",
                                                     "mutation_performed": False}}), \
                patch.object(acp_module, "force_stop_unreachable",
                             side_effect=lambda *a: calls.update(
                                 {"args": a}) or {"stopped": True,
                                                  "holder_force_killed": 42}):
            receipt = acp_module._op_or_holder_lost(
                self._funnel_args(), str(self.root), self.directory,
                "stop", {"force": True}, 30.0)
        # The directory holds no auth.token, so nothing could be presented.
        self.assertIsNone(paths_module.read_auth_token(self.directory))
        self.assertTrue(receipt.get("stopped"), receipt)
        self.assertEqual(calls["args"][3], record)
        # The funnel filled the still-optional id from the verified record —
        # the refused op carried both the flag and no token.
        self.assertEqual(calls["args"][4],
                         {"force": True,
                          "expected_holder_instance_id": "hid-live"})

    def test_force_stop_keeps_the_refusal_when_a_token_is_presented(self) -> None:
        """A presented-but-wrong token stays the honest refusal — the
        fallback only applies when the caller cannot present one at all."""
        paths_module.write_auth_token(self.directory, "stale-tok")
        record = self._bound_record()
        with patch.object(acp_module, "read_record", return_value=record), \
                patch.object(acp_module, "sock_path",
                             return_value=self.root / "h.sock"), \
                patch.object(acp_module.Path, "exists", return_value=True), \
                patch.object(acp_module, "socket_request",
                             return_value={"error": {"code": "unauthenticated"}}), \
                patch.object(acp_module, "force_stop_unreachable",
                             side_effect=AssertionError("fallback with a presentable token")):
            receipt = acp_module._op_or_holder_lost(
                self._funnel_args(), str(self.root), self.directory,
                "stop", {"force": True}, 30.0)
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "unauthenticated", receipt)

    def test_force_stop_unreachable_falls_through_to_the_argv_kill(self) -> None:
        """The answering bound socket refusing an unauthenticated stop does
        not return early: the argv-verified signal path still fires."""
        record = self._bound_record()
        sock = self.root / "h.sock"
        killed: list = []

        def fake_kill(pid, sig):
            killed.append((pid, sig))

        with patch.object(acp_module, "holder_argv_anchor", return_value=True), \
                patch.object(acp_module, "answering_socket",
                             return_value=(sock, {"holder_instance_id": "hid-live"})), \
                patch.object(acp_module, "socket_request",
                             return_value={"error": {"code": "unauthenticated"}}), \
                patch.object(acp_module.os, "kill", side_effect=fake_kill), \
                patch.object(acp_module, "pid_alive", return_value=False), \
                patch.object(acp_module, "force_kill_from_record",
                             return_value={"stopped": True, "residual_pids": []}):
            receipt = acp_module.force_stop_unreachable(
                self._funnel_args(), str(self.root), self.directory,
                record, {"force": True})
        self.assertTrue(receipt.get("unauthenticated_stop_fallback"), receipt)
        self.assertEqual(receipt.get("answering_socket"), str(sock))
        self.assertTrue(killed, "the argv-verified holder PID was signalled")
        self.assertEqual(killed[0][0], os.getpid())
        self.assertEqual(receipt.get("holder_force_killed"), os.getpid())


class RecoveryRoutesAndBroker(unittest.TestCase):
    """The #259 contract on the new codes, and the F7 shared reader."""

    ROUTES_PATH = PROJECT / "scripts" / "kaola-recovery-routes.py"
    BROKER_PATH = PROJECT / "scripts" / "kaola-launchd-broker.py"

    def test_the_new_refusal_codes_have_working_routes(self) -> None:
        routes = load("kaola_recovery_routes_i408", self.ROUTES_PATH)
        for code in ("unauthenticated", "holder-instance-required",
                     "invalid-token"):
            with self.subTest(code=code):
                kind, text = routes.ROUTES[code]
                self.assertEqual(kind, "route", code)
                self.assertTrue(text, code)
        # Each route names the tested recovery, not a dead end.
        self.assertIn("auth.token", routes.ROUTES["unauthenticated"][1])
        self.assertIn("--force", routes.ROUTES["unauthenticated"][1])
        self.assertIn("expected-holder-instance-id",
                      routes.ROUTES["holder-instance-required"][1])
        self.assertIn("ASCII", routes.ROUTES["invalid-token"][1])

    def test_broker_reads_the_token_through_the_shared_reader(self) -> None:
        broker = load("kaola_launchd_broker_i408", self.BROKER_PATH)
        seen: dict = {}

        class Proc:
            pid = 424242

        def fake_read(directory):
            seen["dir"] = directory
            return "minted-tok"

        with tempfile.TemporaryDirectory(prefix="kaola-i408-broker-") as tmp:
            record_dir = Path(tmp) / "record"
            record_dir.mkdir()
            with patch.object(broker.acp_paths, "read_auth_token",
                              side_effect=fake_read), \
                    patch.object(broker, "socket_op",
                                 side_effect=lambda s, op, p, t: seen.update(
                                     {"params": dict(p)}) or
                                 {"stopped": True, "residual_pids": []}), \
                    patch.object(broker, "terminate_owned"), \
                    patch.object(broker, "pid_alive", return_value=False):
                fact = broker._stop_owned_holder(
                    Path(tmp) / "h.sock", "inst-1", Proc(), record_dir)
        self.assertEqual(seen["dir"], record_dir)
        self.assertEqual(seen["params"]["auth_token"], "minted-tok")
        self.assertEqual(seen["params"]["expected_holder_instance_id"],
                         "inst-1")
        self.assertTrue(fact.get("host_session_stopped"), fact)


class RenderedBytes(unittest.TestCase):
    def test_rendered_worker_scripts_are_the_candidate_bytes(self) -> None:
        for name in ("kaola-acp-holder.py", "kaola-acp.py",
                     "kaola-acp-paths.py", "kaola-launchd-broker.py",
                     "kaola-project-compact-notice.py",
                     "kaola-recovery-routes.py"):
            source = (PROJECT / "scripts" / name).read_bytes()
            rendered = (PROJECT / "skills" / "zcode-kaola-project-runner"
                        / "scripts" / name).read_bytes()
            self.assertEqual(rendered, source, name)


if __name__ == "__main__":
    unittest.main()
