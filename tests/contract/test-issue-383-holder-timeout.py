#!/usr/bin/env python3
"""Issue #383: bounded client transport with a stage-aware holder timeout.

The pre-fix client computed ``sock_timeout = (timeout + 30.0) if timeout else
None`` and then handed that value to every socket call separately. A no-wait
send without ``--timeout`` therefore had no bound at all, and an explicit
``--timeout 2`` could still spend 32 s because connect, sendall and recv each
got their own allowance. A wedged holder blocked the client indefinitely.

This suite pins the repair end to end:

* one monotonic deadline across connect/send/read (never 3 x the bound);
* ``holder-timeout`` with ``stage`` and ``timeout_s``;
* connect/send are provably unsent (``false``/``not_started``), read is
  uncertain (``null``/``unknown``) because the request may be admitted late;
* the no-wait send/start brief admission bound, steer 60 s, cancel 35 s,
  ``send --wait``/``wait`` unchanged and unbounded, and ``--timeout <= 0``
  refused as typed ``invalid-input``;
* the companion holder fix: ``stop --force`` does not wait on the admission
  lock, so it recovers a lock-wedged holder and the blocked send gets a
  definitive ``acp-write-failed`` receipt;
* the ``holder-timeout`` recovery route and the text-free verify block.

Pre-fix counter-proof: run this file in a checkout of the base commit. The
unit cases fail because ``stage``/``holder-timeout``/the bound helper do not
exist; the 30 s no-wait case would hang past its 40 s external bound (the
unpatched client has no deadline); and ``stop --force`` would hang on the same
lock the blocked prompt holds (the holder fix is absent).

Run: python3 tests/contract/test-issue-383-holder-timeout.py -v
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "kaola-acp.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"
ROUTES = REPO / "scripts" / "kaola-recovery-routes.py"


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSocket:
    """A deterministic socket whose stage can be made to fail."""

    def __init__(self, *, clock: FakeClock | None = None,
                 connect_exc: BaseException | None = None,
                 send_exc: BaseException | None = None,
                 recv = None) -> None:
        self.clock = clock
        self.connect_exc = connect_exc
        self.send_exc = send_exc
        self.recv_impl = recv
        self.timeouts: list[float | None] = []
        self.recv_calls = 0
        self.sent = b""
        self.closed = False

    def settimeout(self, value: float | None) -> None:
        self.timeouts.append(value)

    def connect(self, path: str) -> None:
        if self.connect_exc is not None:
            raise self.connect_exc

    def sendall(self, payload: bytes) -> None:
        if self.send_exc is not None:
            raise self.send_exc
        self.sent = payload

    def recv(self, size: int) -> bytes:
        self.recv_calls += 1
        if self.recv_impl is None:
            return b""
        return self.recv_impl(self)

    def close(self) -> None:
        self.closed = True


class SocketDeadlineTests(unittest.TestCase):
    """socket_request: one absolute deadline and the stage fact."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(CLI, "kaola_acp_383_socket")

    def call(self, fake: FakeSocket, timeout: float | None = 5.0,
             clock: FakeClock | None = None, op: str = "prompt",
             params: dict | None = None) -> dict:
        module = self.module
        fake_time = types.SimpleNamespace(monotonic=clock.monotonic) if clock else None
        patches = [patch.object(module.socket, "socket", return_value=fake)]
        if fake_time is not None:
            patches.append(patch.object(module, "time", fake_time))
        with patches[0]:
            if fake_time is not None:
                with patches[1]:
                    return module.socket_request(
                        Path("/unused/holder.sock"), op,
                        params if params is not None else {"text": "x"}, timeout)
            return module.socket_request(
                Path("/unused/holder.sock"), op,
                params if params is not None else {"text": "x"}, timeout)

    def test_connect_timeout_is_unsent(self) -> None:
        fake = FakeSocket(connect_exc=socket.timeout("timed out"))
        receipt = self.call(fake, 1.5)
        error = receipt["error"]
        self.assertEqual(error["code"], "holder-timeout")
        self.assertEqual(error["stage"], "connect")
        self.assertEqual(error["timeout_s"], 1.5)
        self.assertEqual(receipt["outcome"], "not_sent")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertTrue(fake.closed)

    def test_send_timeout_is_unsent(self) -> None:
        fake = FakeSocket(send_exc=socket.timeout("timed out"))
        receipt = self.call(fake, 2.0)
        error = receipt["error"]
        self.assertEqual(error["code"], "holder-timeout")
        self.assertEqual(error["stage"], "send")
        self.assertEqual(error["timeout_s"], 2.0)
        self.assertEqual(receipt["outcome"], "not_sent")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")

    def test_read_timeout_is_uncertain(self) -> None:
        fake = FakeSocket(recv=lambda sock: (_ for _ in ()).throw(
            socket.timeout("timed out")))
        receipt = self.call(fake, 3.0)
        error = receipt["error"]
        self.assertEqual(error["code"], "holder-timeout")
        self.assertEqual(error["stage"], "read")
        self.assertEqual(error["timeout_s"], 3.0)
        self.assertEqual(receipt["outcome"], "unknown")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")
        self.assertEqual(fake.recv_calls, 1)

    def test_holder_closed_is_read_stage_and_uncertain(self) -> None:
        receipt = self.call(FakeSocket(recv=lambda sock: b""), 3.0)
        error = receipt["error"]
        self.assertEqual(error["code"], "holder-closed")
        self.assertEqual(error["stage"], "read")
        self.assertEqual(receipt["outcome"], "unknown")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

    def test_malformed_reply_is_read_stage(self) -> None:
        receipt = self.call(FakeSocket(recv=lambda sock: b"{not-json\n"), 3.0)
        error = receipt["error"]
        self.assertEqual(error["code"], "holder-unreachable")
        self.assertEqual(error["stage"], "read")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

    def test_absolute_deadline_is_not_per_syscall(self) -> None:
        """Two trickled bytes must consume the one 0.3 s budget, not reset it."""
        clock = FakeClock()

        def trickle(sock: FakeSocket) -> bytes:
            clock.advance(0.2)
            return b"x"

        fake = FakeSocket(clock=clock, recv=trickle)
        receipt = self.call(fake, 0.3, clock)
        self.assertEqual(receipt["error"]["code"], "holder-timeout")
        self.assertEqual(receipt["error"]["stage"], "read")
        # The third remaining() call is already negative, so recv is not called.
        self.assertEqual(fake.recv_calls, 2)
        # The first read timeout is the whole budget; the second is the
        # remainder. A per-syscall timeout would have been 0.3 both times.
        self.assertAlmostEqual(fake.timeouts[0], 0.3, places=6)
        self.assertLess(fake.timeouts[-1], 0.2)
        self.assertGreater(fake.timeouts[-1], 0.0)

    def test_absolute_deadline_on_a_real_trickling_server(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="kpr-i383-trickle-"))
        sock_path = root / "s"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(sock_path))
        server.listen(1)

        def serve() -> None:
            connection = None
            try:
                connection, _ = server.accept()
                connection.recv(65536)
                for _ in range(30):
                    time.sleep(0.1)
                    connection.sendall(b"x")
            except OSError:
                pass
            finally:
                if connection is not None:
                    connection.close()
                server.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        started = time.monotonic()
        try:
            receipt = self.module.socket_request(
                sock_path, "prompt", {"text": "x"}, 0.35)
        finally:
            server.close()
            thread.join(timeout=5)
        elapsed = time.monotonic() - started
        self.assertEqual(receipt["error"]["code"], "holder-timeout")
        self.assertEqual(receipt["error"]["stage"], "read")
        self.assertGreaterEqual(elapsed, 0.3)
        self.assertLess(elapsed, 1.5)

    def test_connect_refusal_keeps_connect_stage(self) -> None:
        fake = FakeSocket(connect_exc=ConnectionRefusedError(61, "refused"))
        receipt = self.call(fake, 1.0)
        self.assertEqual(receipt["error"]["code"], "holder-unreachable")
        self.assertEqual(receipt["error"]["stage"], "connect")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")


class ClientBoundTests(unittest.TestCase):
    """The per-command client bound and the timeout refusal."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(CLI, "kaola_acp_383_bounds")

    def bound(self, command: str, timeout=None, wait=None,
              cancel_timeout=None, op: str | None = None) -> float | None:
        args = argparse.Namespace(command=command, timeout=timeout,
                                  cancel_timeout=cancel_timeout)
        return self.module.client_socket_timeout(args, wait, op=op)

    def test_admission_bound_matrix(self) -> None:
        rows = [
            # The CLI command is "steer" for both native and interrupt; the
            # resolved holder op is what selects the formula.
            ("send", None, False, None, "prompt", 30.0),
            ("send", None, True, None, "prompt", None),
            ("send", 5.0, False, None, "prompt", 35.0),
            ("start", None, False, None, "prompt", 30.0),
            ("start", None, True, None, "prompt", None),
            ("steer", None, None, None, "steer", 60.0),
            ("steer", 5.0, None, None, "steer", 35.0),
            ("cancel", None, None, None, "cancel", 35.0),
            ("cancel", 5.0, None, None, "cancel", 35.0),
            ("steer", None, None, None, "steer_interrupt", 35.0),
            ("steer", None, None, 40.0, "steer_interrupt", 70.0),
            ("steer", 1.0, None, 80.0, "steer_interrupt", 110.0),
            ("steer", 10.0, None, None, "steer_interrupt", 40.0),
            ("steer", 10.0, None, 60.0, "steer_interrupt", 90.0),
            ("wait", None, None, None, "wait", None),
            ("wait", 5.0, None, None, "wait", 35.0),
            ("wake", None, None, None, "wake_delegator", None),
        ]
        for command, timeout, wait, cancel_timeout, op, expected in rows:
            with self.subTest(command=command, timeout=timeout, wait=wait,
                              cancel_timeout=cancel_timeout, op=op):
                self.assertEqual(
                    self.bound(command, timeout, wait, cancel_timeout, op),
                    expected)

    def test_steer_no_wait_is_a_noop(self) -> None:
        """Only send/start consume --wait; steer's bound is timeout + grace."""
        self.assertEqual(self.bound("steer", None, False, None, "steer"), 60.0)
        self.assertEqual(self.bound("steer", None, True, None, "steer"), 60.0)
        self.assertEqual(self.bound("send", None, False, None, "prompt"), 30.0)
        self.assertEqual(self.bound("send", None, True, None, "prompt"), None)

    def test_shipped_constants(self) -> None:
        self.assertEqual(self.module.ADMISSION_BOUND, 30.0)
        self.assertEqual(self.module.REPLY_GRACE, 30.0)
        self.assertEqual(self.module.STEER_ADMISSION_BOUND, 30.0)
        self.assertEqual(self.module.CANCEL_GRACE, 5.0)

    def test_start_brief_passes_the_admission_bound(self) -> None:
        module = self.module
        args = argparse.Namespace(
            command="start", platform="grok", session="brief-383",
            timeout=None, wait=False, max_final_chars=1000,
            expected_holder_instance_id=None)
        captured: list[float | None] = []

        def capture(*call_args, **call_kwargs):
            captured.append(call_args[5] if len(call_args) > 5
                            else call_kwargs.get("timeout"))
            return {"error": {"code": "holder-timeout", "stage": "read",
                              "timeout_s": 30.0},
                    "outcome": "unknown", "mutation_performed": None,
                    "mutation_status": "unknown"}

        with patch.object(module, "record_dir", return_value=Path("/unused")), \
             patch.object(module, "resolve_send_wait",
                          return_value=({"wait": False, "source": "explicit"}, None)), \
             patch.object(module, "sock_path", return_value=Path("/unused/missing")), \
             patch.object(module, "op_or_holder_lost", side_effect=capture):
            module.deliver_start_brief(args, "/unused", {}, "brief")
        self.assertEqual(captured, [30.0])

    def interrupt_bound_through_cli(self, extra: list[str]
                                    ) -> tuple[list[tuple[str, float]], dict]:
        """Run the real CLI steer --steer-mode interrupt dispatch.

        The command stays ``steer``; the resolved holder op is
        ``steer_interrupt``. Only this catches a command-keyed formula that the
        real path can never select.
        """
        module = self.module
        root = Path(tempfile.mkdtemp(prefix="kpr-i383-cli-interrupt-"))
        sock = root / "holder.sock"
        sock.write_text("", encoding="utf-8")
        captured: list[tuple[str, float]] = []

        def fake_socket_request(sock_path, op, params, timeout, directory=None):
            captured.append((op, timeout))
            return {"error": {"code": "holder-timeout", "stage": "read",
                              "timeout_s": timeout},
                    "outcome": "unknown", "mutation_performed": None,
                    "mutation_status": "unknown"}

        argv = [str(CLI), "grok", "steer", "--repo", str(root),
                "--session", "s-383", "--command", "true",
                "--text", "interrupt probe", "--steer-mode", "interrupt",
                *extra]
        stdout = io.StringIO()
        with patch.object(sys, "argv", argv), \
             patch.object(module, "resolve_repo", return_value=str(root)), \
             patch.object(module, "sock_path", return_value=sock), \
             patch.object(module, "read_record",
                          return_value={"holder_pid": os.getpid(),
                                        "state": "ready"}), \
             patch.object(module, "pid_alive", return_value=True), \
             patch.object(module, "socket_request",
                          side_effect=fake_socket_request), \
             contextlib.redirect_stdout(stdout):
            rc = module.main()
        lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
        receipt = json.loads(lines[-1])
        self.assertEqual(rc, 0, receipt)
        return captured, receipt

    def test_real_cli_interrupt_uses_the_cancel_formula(self) -> None:
        captured, receipt = self.interrupt_bound_through_cli(
            ["--cancel-timeout", "80", "--timeout", "1"])
        self.assertEqual(captured, [("steer_interrupt", 110.0)])
        self.assertEqual((receipt.get("error") or {}).get("timeout_s"), 110.0)
        self.assertEqual(receipt["verify"]["match"], "last_prompt.fingerprint")
        self.assertIn("status", receipt["verify"]["command"])

    def test_real_cli_interrupt_default_is_35(self) -> None:
        captured, receipt = self.interrupt_bound_through_cli([])
        self.assertEqual(captured, [("steer_interrupt", 35.0)])
        self.assertEqual((receipt.get("error") or {}).get("timeout_s"), 35.0)


class ReceiptMutationTests(unittest.TestCase):
    """The #379 stamp now uses the #383 stage facts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(CLI, "kaola_acp_383_receipts")

    def stamp(self, op: str, code: str, stage: str | None = None,
              **extra) -> dict:
        receipt = {"error": {"code": code}}
        if stage is not None:
            receipt["error"]["stage"] = stage
        receipt.update(extra)
        return self.module._stamp_request_mutation(receipt, op)

    def test_stage_mutation_matrix(self) -> None:
        for code in ("holder-timeout", "holder-unreachable"):
            for stage in ("connect", "send"):
                receipt = self.stamp("prompt", code, stage)
                self.assertIs(receipt["mutation_performed"], False,
                              (code, stage))
                self.assertEqual(receipt["mutation_status"], "not_started",
                                 (code, stage))
            receipt = self.stamp("prompt", code, "read")
            self.assertIsNone(receipt["mutation_performed"], code)
            self.assertEqual(receipt["mutation_status"], "unknown", code)
            receipt = self.stamp("prompt", code)
            self.assertIsNone(receipt["mutation_performed"], code)
            self.assertEqual(receipt["mutation_status"], "unknown", code)

        receipt = self.stamp("prompt", "holder-lost", "send")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        receipt = self.stamp("prompt", "holder-lost", "read")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

    def test_explicit_transport_keys_are_preserved(self) -> None:
        for stage, performed, status in (
                ("connect", False, "not_started"),
                ("send", False, "not_started"),
                ("read", None, "unknown")):
            receipt = {"error": {"code": "holder-timeout", "stage": stage},
                       "outcome": "not_sent" if performed is False else "unknown",
                       "mutation_performed": performed,
                       "mutation_status": status}
            stamped = self.module._stamp_request_mutation(receipt, "prompt")
            self.assertIs(stamped["mutation_performed"], performed, stage)
            self.assertEqual(stamped["mutation_status"], status, stage)

    def test_steer_companion_fields_follow_the_stage(self) -> None:
        unsent = self.stamp("steer", "holder-timeout", "send")
        self.assertEqual(unsent["steer_outcome"], "not_consumed")
        self.assertIs(unsent["steer_consumed"], False)
        self.assertEqual(unsent["steer_confirmation"], "none")
        uncertain = self.stamp("steer_interrupt", "holder-timeout", "read")
        self.assertEqual(uncertain["steer_outcome"], "unknown")
        self.assertIsNone(uncertain["steer_consumed"])
        self.assertEqual(uncertain["steer_confirmation"], "none")

    def test_read_only_ops_never_grow_mutation_keys(self) -> None:
        for op in ("state", "capture", "wait"):
            receipt = {"error": {"code": "holder-timeout", "stage": "read"},
                       "mutation_performed": None,
                       "mutation_status": "unknown"}
            self.module._scope_transport_mutation(receipt, op)
            self.assertNotIn("mutation_performed", receipt, op)
            self.assertNotIn("mutation_status", receipt, op)
            # A successful read-only reply keeps the holder's turn fact.
            success = {"outcome": "turn_completed",
                       "mutation_status": "completed"}
            self.module._scope_transport_mutation(success, op)
            self.assertEqual(success.get("mutation_status"), "completed")
        for op in ("prompt", "steer", "steer_interrupt", "cancel", "permit",
                   "stop", "wake_delegator"):
            receipt = {"error": {"code": "holder-timeout", "stage": "read"},
                       "mutation_performed": None,
                       "mutation_status": "unknown"}
            self.module._scope_transport_mutation(receipt, op)
            self.assertIn("mutation_performed", receipt, op)
            self.assertIn("mutation_status", receipt, op)

    def test_timeout_verification_is_text_free(self) -> None:
        text = "a secret prompt body"
        args = argparse.Namespace(platform="grok", session="s-383")
        for stage in ("connect", "send"):
            receipt = {"error": {"code": "holder-timeout", "stage": stage,
                                 "timeout_s": 30.0}}
            stamped = self.module._stamp_timeout_verification(
                receipt, args, "/tmp/repo", "prompt", {"text": text})
            self.assertEqual(stamped["prompt_fingerprint"], fingerprint(text))
            self.assertNotIn("verify", stamped, stage)
        receipt = {"error": {"code": "holder-timeout", "stage": "read",
                             "timeout_s": 30.0}}
        stamped = self.module._stamp_timeout_verification(
            receipt, args, "/tmp/repo", "prompt", {"text": text})
        self.assertEqual(stamped["prompt_fingerprint"], fingerprint(text))
        self.assertNotIn(text, json.dumps(stamped))
        self.assertEqual(stamped["verify"]["match"], "last_prompt.fingerprint")
        self.assertIn("status", stamped["verify"]["command"])
        self.assertIn("resend", stamped["verify"]["do_not"])

        # Interrupt: the follow-up prompt carries this steer text, so status's
        # last_prompt fingerprint is the real surface.
        interrupt = {"error": {"code": "holder-timeout", "stage": "read",
                               "timeout_s": 35.0}}
        stamped = self.module._stamp_timeout_verification(
            interrupt, args, "/tmp/repo", "steer_interrupt", {"text": text})
        self.assertEqual(stamped["steer_fingerprint"], fingerprint(text))
        self.assertIn("status", stamped["verify"]["command"])
        self.assertEqual(stamped["verify"]["match"], "last_prompt.fingerprint")
        self.assertIn("follow-up prompt", stamped["verify"]["note"])

        # Native steer has no status field. The verify must name the existing
        # capture events (steer_sent fingerprint -> steer_result request_id),
        # and must not present a bare write as consumption.
        native = {"error": {"code": "holder-timeout", "stage": "read",
                            "timeout_s": 60.0}}
        stamped = self.module._stamp_timeout_verification(
            native, args, "/tmp/repo", "steer", {"text": text})
        self.assertEqual(stamped["steer_fingerprint"], fingerprint(text))
        self.assertIn("capture", stamped["verify"]["command"])
        self.assertNotIn("status", stamped["verify"]["command"])
        self.assertIn("steer_sent.fingerprint", stamped["verify"]["match"])
        self.assertIn("steer_result", stamped["verify"]["match"])
        self.assertIn("consumption", stamped["verify"]["note"])
        self.assertNotEqual(stamped["verify"]["match"], "steer_fingerprint")

    def test_recovery_route_exists_and_is_honest(self) -> None:
        routes = load_module(ROUTES, "kaola_routes_383").ROUTES
        kind, text = routes["holder-timeout"]
        self.assertEqual(kind, "self-route")
        for needle in ("status", "fingerprint", "resend", "--force",
                       "turn_active"):
            self.assertIn(needle, text)

    def test_timeout_keeps_the_force_stop_recovery_branch(self) -> None:
        """A wedged holder must reach force-stop, not become unkillable."""
        module = self.module
        root = Path(tempfile.mkdtemp(prefix="kpr-i383-recovery-"))
        sock = root / "holder.sock"
        sock.write_text("", encoding="utf-8")
        args = argparse.Namespace(command="stop", platform="grok",
                                  session="s-383")
        sentinel = {"stopped": True, "force_recovery": True}
        record = {"holder_pid": 424242, "state": "ready"}
        with patch.object(module, "sock_path", return_value=sock), \
             patch.object(module, "read_record", return_value=record), \
             patch.object(module, "pid_alive", return_value=True), \
             patch.object(module, "socket_request",
                          return_value={"error": {"code": "holder-timeout",
                                                  "stage": "read",
                                                  "timeout_s": 30.0}}), \
             patch.object(module, "force_stop_unreachable",
                          return_value=sentinel) as forced:
            result = module._op_or_holder_lost(
                args, str(root), root / "record", "stop", {"force": True}, 30.0)
        self.assertEqual(result, sentinel)
        forced.assert_called_once()

    def test_timeout_on_a_dead_holder_keeps_the_timeout_fact(self) -> None:
        module = self.module
        root = Path(tempfile.mkdtemp(prefix="kpr-i383-dead-"))
        sock = root / "holder.sock"
        sock.write_text("", encoding="utf-8")
        args = argparse.Namespace(command="send", platform="grok",
                                  session="s-383")
        # Alive at the pre-check, dead when the timed-out wire answer arrives:
        # the holder died during the request, not before it.
        with patch.object(module, "sock_path", return_value=sock), \
             patch.object(module, "read_record",
                          return_value={"holder_pid": 424242, "state": "ready"}), \
             patch.object(module, "pid_alive", side_effect=[True, False]), \
             patch.object(module, "base_receipt", return_value={}), \
             patch.object(module, "socket_request",
                          return_value={"error": {"code": "holder-timeout",
                                                  "stage": "read",
                                                  "timeout_s": 30.0}}):
            result = module._op_or_holder_lost(
                args, str(root), root / "record", "prompt",
                {"text": "x"}, 30.0)
        self.assertEqual((result.get("error") or {}).get("code"),
                         "holder-timeout")
        self.assertIs(result.get("holder_alive"), False)
        self.assertNotIn("previous_prompt", result)
        self.assertNotIn("record", result)


class ReceiptIntegrationCase(unittest.TestCase):
    """Real CLI + real holder + mock agent, one temp project per test."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i383-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "kpr383@example.invalid"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "kpr383"],
                       cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("kpr383\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.repo, check=True)
        self.project = os.path.realpath(str(self.repo))
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session = f"grok-w383-{self._testMethodName.replace('_', '-')[:42]}"
        self.platform = "grok"
        self.started = False
        self.extra: list[subprocess.Popen] = []
        self.suspended: list[int] = []
        self.samples: list[Path] = []

    def tearDown(self) -> None:
        for pid in self.suspended:
            try:
                os.kill(pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
        if self.started:
            self.cli("stop", "--force", check=False, timeout=15)
            self.started = False
        # A failed assertion can leave the exact holder/agent alive; never let
        # a scratch fixture leak them into the next case.
        try:
            record = self.read_record()
        except (OSError, ValueError):
            record = {}
        for key in ("agent_pid", "holder_pid"):
            pid = record.get(key)
            if isinstance(pid, int) and pid > 0 and self.alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        for proc in self.extra:
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
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

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["HOME"] = str(self.home)
        env["TMPDIR"] = str(self.root / "tmp")
        Path(env["TMPDIR"]).mkdir(exist_ok=True)
        env["MOCK_ACP_LOG"] = str(self.root / "mock-events.jsonl")
        return env

    def mock_command(self, scenario: str = "normal", *extra: str) -> str:
        tail = (" " + " ".join(extra)) if extra else ""
        return f"{sys.executable} {MOCK} --scenario {scenario}{tail}"

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 60, scenario: str = "normal",
            mock_args: tuple[str, ...] = (),
            stdin_text: str | None = None,
            platform: str | None = None,
            agent_command: str | None = None) -> tuple[int, dict]:
        target = platform or self.platform
        argv = [
            sys.executable, str(CLI), target, command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", agent_command or self.mock_command(scenario, *mock_args),
            *args,
        ]
        proc = subprocess.run(argv, capture_output=True, text=True,
                              env=self.env(), timeout=timeout,
                              input=stdin_text)
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

    def start(self, scenario: str = "normal", *args: str,
              mock_args: tuple[str, ...] = (),
              platform: str | None = None) -> dict:
        target = platform or self.platform
        self.platform = target
        _, receipt = self.cli("start", *args, scenario=scenario,
                              mock_args=mock_args, platform=target)
        self.started = True
        return receipt

    def record_path(self) -> Path:
        digest = hashlib.sha256(self.project.encode("utf-8")).hexdigest()[:16]
        return (self.record_root / self.platform / self.session / digest
                / "record.json")

    def read_record(self) -> dict:
        return json.loads(self.record_path().read_text(encoding="utf-8"))

    def suspend(self, pid: int) -> None:
        os.kill(pid, signal.SIGSTOP)
        self.suspended.append(pid)

    def resume(self, pid: int) -> None:
        try:
            os.kill(pid, signal.SIGCONT)
        finally:
            if pid in self.suspended:
                self.suspended.remove(pid)

    def alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def holder_write_blocked(self, holder_pid: int, send_proc: subprocess.Popen,
                             timeout: float = 10.0) -> bool:
        """True once the holder is proven blocked writing agent stdin.

        macOS ``sample`` gives the stack directly. Elsewhere the 8 MB frame
        and a stopped agent make the same block inevitable; the send process
        still being alive after the wait is the fallback fact.
        """
        sample = shutil.which("sample")
        if sys.platform == "darwin" and sample:
            deadline = time.monotonic() + timeout
            sample_path = self.root / f"sample-{holder_pid}.txt"
            self.samples.append(sample_path)
            while time.monotonic() < deadline:
                subprocess.run([sample, str(holder_pid), "1", "-file",
                                str(sample_path)],
                               capture_output=True, text=True)
                text = (sample_path.read_text(encoding="utf-8", errors="ignore")
                        if sample_path.exists() else "")
                if ("_io_BufferedWriter_write" in text
                        or "_io_FileIO_write" in text):
                    return send_proc.poll() is None
                time.sleep(0.2)
            return False
        time.sleep(2.0)
        return send_proc.poll() is None


class HolderTimeoutIntegrationTests(ReceiptIntegrationCase):
    """Slow real-holder cases, including the lock-wedge recovery."""

    def test_timeout_zero_and_negative_are_typed_refusals(self) -> None:
        for value in ("0", "-1", "0.0"):
            with self.subTest(value=value):
                rc, receipt = self.cli("send", "--text", "x",
                                       f"--timeout={value}", check=False)
                self.assertEqual(rc, 1)
                self.assertEqual(receipt.get("result"), "refused")
                self.assertEqual(receipt.get("reason"), "invalid-input")
                self.assertEqual(receipt.get("outcome"), "invalid_input")
                self.assertEqual((receipt.get("error") or {}).get("code"),
                                 "invalid-input")
                self.assertIs(receipt.get("mutation_performed"), False)
                self.assertEqual(receipt.get("mutation_status"), "not_started")
        # A positive value is not refused by this guard; the absent session is
        # the next (different) refusal.
        rc, receipt = self.cli("send", "--text", "x", "--timeout", "0.5",
                               check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((receipt.get("error") or {}).get("code"), "no-session")
        # Nothing created a record or a holder for the refused calls.
        self.assertFalse(self.record_path().exists())

    def test_no_wait_default_is_30s_and_late_admission_is_visible(self) -> None:
        self.start()
        record = self.read_record()
        holder_pid = record["holder_pid"]
        self.suspend(holder_pid)
        text = "issue 383 late admission probe"
        started = time.monotonic()
        try:
            rc, send = self.cli("send", "--text", text, "--no-wait",
                                check=False, timeout=45)
        finally:
            elapsed = time.monotonic() - started
            self.resume(holder_pid)

        self.assertEqual(rc, 0, send)
        error = send.get("error") or {}
        self.assertEqual(error.get("code"), "holder-timeout", send)
        self.assertEqual(error.get("stage"), "read", send)
        self.assertEqual(error.get("timeout_s"), 30.0, send)
        self.assertEqual(send.get("outcome"), "unknown")
        self.assertIsNone(send.get("mutation_performed"))
        self.assertEqual(send.get("mutation_status"), "unknown")
        self.assertGreaterEqual(elapsed, 28.0, send)
        self.assertLess(elapsed, 36.0, send)
        expected = fingerprint(text)
        self.assertEqual(send.get("prompt_fingerprint"), expected)
        self.assertNotIn(text, json.dumps(send))
        verify = send.get("verify") or {}
        self.assertEqual(verify.get("match"), "last_prompt.fingerprint")
        self.assertIn("status", verify.get("command", ""))

        # SIGCONT: the request the client abandoned is admitted late. Its
        # fingerprint in the record is the proof that a read-stage timeout is
        # uncertain, never "not sent".
        def admitted():
            _, status = self.cli("status", check=False)
            last = status.get("last_prompt") or {}
            return last if last.get("fingerprint") == expected else None

        last = wait_for(admitted, 20, "late admission fingerprint")
        self.assertEqual(last.get("fingerprint"), expected)
        self.assertEqual(last.get("mutation_status"), "completed")

    def test_start_brief_timeout_keeps_fingerprint_and_verify(self) -> None:
        """F2: the final start receipt must carry the timeout's verify handle.

        A mock agent stops itself after two configuration replies, so the
        holder's 2 MB brief write blocks while the start client still owns the
        30 s admission bound.
        """
        wrapper = self.root / "mock-stop-after-config.py"
        wrapper.write_text(
            "import importlib.util, os, signal\n"
            f"spec = importlib.util.spec_from_file_location('mock', {str(MOCK)!r})\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "orig = m.MockAgent.on_set_config\n"
            "count = [0]\n"
            "def stop_after(self, request_id, params):\n"
            "    orig(self, request_id, params)\n"
            "    count[0] += 1\n"
            "    if count[0] == 2:\n"
            "        os.kill(os.getpid(), signal.SIGSTOP)\n"
            "m.MockAgent.on_set_config = stop_after\n"
            "raise SystemExit(m.main())\n",
            encoding="utf-8")
        text = "b" * 2_000_000
        started = time.monotonic()
        self.started = True
        try:
            rc, receipt = self.cli(
                "start", "--stdin", "--no-wait", stdin_text=text,
                timeout=45, check=False,
                agent_command=f"{sys.executable} {wrapper}")
            elapsed = time.monotonic() - started
        finally:
            try:
                record = self.read_record()
            except (OSError, ValueError):
                record = {}
            agent_pid = record.get("agent_pid")
            if isinstance(agent_pid, int) and agent_pid > 0:
                try:
                    os.kill(agent_pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
        self.assertEqual(rc, 1, receipt)
        self.assertIs(receipt.get("brief_delivered"), False, receipt)
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-timeout", receipt)
        self.assertEqual(error.get("stage"), "read", receipt)
        self.assertEqual(error.get("timeout_s"), 30.0, receipt)
        self.assertIsNone(receipt.get("mutation_performed"), receipt)
        self.assertEqual(receipt.get("mutation_status"), "unknown", receipt)
        self.assertEqual(receipt.get("prompt_fingerprint"), fingerprint(text))
        verify = receipt.get("verify") or {}
        self.assertEqual(verify.get("match"), "last_prompt.fingerprint")
        self.assertIn("status", verify.get("command", ""))
        self.assertNotIn(text, json.dumps(receipt))
        self.assertGreaterEqual(elapsed, 28.0, receipt)
        self.assertLess(elapsed, 36.0, receipt)

    def test_send_wait_without_timeout_is_not_cut_at_admission(self) -> None:
        self.start("slow", mock_args=("--turn-ms", "1500"))
        started = time.monotonic()
        rc, receipt = self.cli("send", "--text", "wait turn", "--wait",
                              timeout=15)
        elapsed = time.monotonic() - started
        self.assertEqual(rc, 0, receipt)
        self.assertEqual(receipt.get("outcome"), "turn_completed", receipt)
        self.assertEqual(receipt.get("stop_reason"), "end_turn", receipt)
        self.assertLess(elapsed, 10.0)
        self.assertNotIn("holder-timeout",
                         json.dumps(receipt.get("error") or {}))

    def test_interrupt_success_verify_surface_is_status_fingerprint(self) -> None:
        """F3: an interrupt's follow-up prompt is the status-verifiable fact."""
        self.start()
        text = "interrupt verification text"
        rc, steer = self.cli("steer", "--text", text,
                             "--steer-mode", "interrupt")
        self.assertEqual(rc, 0, steer)
        self.assertEqual(steer.get("outcome"),
                         "steer_resent_without_interrupt", steer)
        self.assertIs(steer.get("steer_consumed"), True, steer)
        fp = steer.get("steer_fingerprint")
        self.assertTrue(fp, steer)
        self.assertEqual(steer.get("new_prompt_fingerprint"), fp, steer)

        def admitted():
            _, status = self.cli("status", check=False)
            last = status.get("last_prompt") or {}
            return last if last.get("fingerprint") == fp else None

        last = wait_for(admitted, 10, "interrupt follow-up prompt")
        self.assertEqual(last.get("fingerprint"), fp)

    def test_native_steer_verify_surface_is_capture_events(self) -> None:
        """F3: native steer has no status field; capture has the real events."""
        self.start("hang_until_cancel", mock_args=("--steering", "written"),
                   platform="codex")
        rc, sent = self.cli("send", "--text", "keep the turn open", "--no-wait")
        self.assertEqual(rc, 0, sent)
        wait_for(lambda: self.cli("observe", check=False)[1].get("turn_active"),
                 10, "mock turn active")
        text = "native steer capture probe"
        rc, steer = self.cli("steer", "--text", text, "--steer-mode", "native",
                             check=False)
        self.assertEqual(rc, 0, steer)
        self.assertEqual((steer.get("error") or {}).get("code"),
                         "steer-write-only-confirmation", steer)
        self.assertIs(steer.get("mutation_performed"), True, steer)
        self.assertEqual(steer.get("steer_outcome"), "written", steer)
        self.assertIsNone(steer.get("steer_consumed"), steer)
        fp = steer.get("steer_fingerprint")
        request_id = steer.get("steer_request_id")
        self.assertTrue(fp, steer)
        self.assertIsNotNone(request_id, steer)
        _, capture = self.cli("capture", "--since", "0", check=False)
        events = capture.get("events") or []
        sent_events = [event for event in events
                       if event.get("kind") == "steer_sent"
                       and event.get("fingerprint") == fp]
        self.assertTrue(sent_events, events)
        result_events = [event for event in events
                          if event.get("kind") == "steer_result"
                          and event.get("request_id") == request_id]
        self.assertTrue(result_events, events)
        result = result_events[-1]
        self.assertEqual(result.get("steer_outcome"), "written", result)
        self.assertIsNone(result.get("steer_consumed"), result)
        self.cli("cancel", "--timeout", "10", check=False)

    def test_force_stop_recovers_lock_wedged_holder(self) -> None:
        self.start()
        record = self.read_record()
        holder_pid = record["holder_pid"]
        agent_pid = record["agent_pid"]
        self.suspend(agent_pid)
        big = b"x" * 8_000_000 + b"\n"
        send = subprocess.Popen(
            [sys.executable, str(CLI), "grok", "send",
             "--repo", str(self.repo), "--session", self.session,
             "--command", self.mock_command("normal"), "--stdin", "--no-wait"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=self.env(), text=False)
        self.extra.append(send)
        assert send.stdin is not None
        send.stdin.write(big)
        send.stdin.close()
        self.assertTrue(self.holder_write_blocked(holder_pid, send),
                        "holder never blocked in the agent write")
        started = time.monotonic()
        rc, stop = self.cli("stop", "--force", check=False, timeout=10)
        elapsed = time.monotonic() - started
        self.assertEqual(rc, 0, stop)
        self.assertLess(elapsed, 5.0, stop)
        self.assertTrue(stop.get("stopped"), stop)
        self.assertEqual(stop.get("residual_pids"), [], stop)
        self.started = False
        wait_for(lambda: not self.alive(holder_pid), 10, "holder gone")
        wait_for(lambda: not self.alive(agent_pid), 10, "agent gone")

        out, err = send.communicate(timeout=15)
        self.assertEqual(send.returncode, 0, (out, err))
        blocked = json.loads(out.decode("utf-8"))
        self.assertEqual((blocked.get("error") or {}).get("code"),
                         "acp-write-failed", blocked)
        self.assertIs(blocked.get("mutation_performed"), False, blocked)
        self.assertEqual(blocked.get("mutation_status"), "not_started")


if __name__ == "__main__":
    unittest.main()
