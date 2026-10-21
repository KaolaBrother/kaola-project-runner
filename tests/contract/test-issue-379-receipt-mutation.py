#!/usr/bin/env python3
"""Issue #379: send/steer receipts state mutation for THIS request.

The reproduction showed three shapes that let a consumer mistake an unsent
request for an uncertain one (or the reverse):

* ``no-session``/``record-lost``/``holder-socket-missing`` carried an error
  but no ``mutation_performed`` key;
* a dead-holder ``holder-lost`` inherited the previous prompt's mutation fact;
* a busy prompt reused the successful ``--no-wait`` word ``in_progress``.

This suite pins the wrapper that answers the first two for the request that
just failed, the holder's ``refused_busy`` word, the steer companion fields,
the status/observe regression boundary, the start-brief prompt and failure
paths, the post-wire holder-death boundary, the forward ``error.stage`` hook
(#383), and the consumer classification matrix. The holder-closed fixture also
serves a deliberate ``state`` probe, the shape a Host ``kaola-acp list`` scan
can send to a temporary record, so that probe cannot consume the send's only
connection.

Run: python3 tests/contract/test-issue-379-receipt-mutation.py -v
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class ReceiptMutationCase(unittest.TestCase):
    """Real CLI + real holder + mock agent, one temp project per test."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i379-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "kpr379@example.invalid"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "kpr379"],
                       cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("kpr379\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.repo, check=True)
        self.project = os.path.realpath(str(self.repo))
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session = f"grok-w379-{self._testMethodName.replace('_', '-')[:40]}"
        self.started = False
        self.extra: list[subprocess.Popen] = []

    def tearDown(self) -> None:
        if self.started:
            self.cli("stop", "--force", check=False, timeout=30)
        for proc in self.extra:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
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

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["HOME"] = str(self.home)
        env["MOCK_ACP_LOG"] = str(self.root / "mock-events.jsonl")
        return env

    def mock_command(self, scenario: str = "normal") -> str:
        return f"{sys.executable} {MOCK} --scenario {scenario}"

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 60, scenario: str = "normal") -> tuple[int, dict]:
        argv = [
            sys.executable, str(CLI), "grok", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(scenario), *args,
        ]
        proc = subprocess.run(argv, capture_output=True, text=True,
                              env=self.env(), timeout=timeout)
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

    def start(self, scenario: str = "normal", *args: str) -> dict:
        _, receipt = self.cli("start", *args, scenario=scenario)
        self.started = True
        return receipt

    def record_path(self) -> Path:
        digest = hashlib.sha256(self.project.encode("utf-8")).hexdigest()[:16]
        return self.record_root / "grok" / self.session / digest / "record.json"

    def read_record(self) -> dict:
        return json.loads(self.record_path().read_text(encoding="utf-8"))

    def write_record(self, record: dict) -> None:
        self.record_path().write_text(json.dumps(record, sort_keys=True) + "\n",
                                      encoding="utf-8")

    def dead_holder(self) -> subprocess.Popen:
        """A live pid for a record whose holder is otherwise gone."""
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.extra.append(proc)
        return proc

    # -- pre-write answers ---------------------------------------------------

    def test_no_session_send_and_steer_are_unsent(self) -> None:
        rc, send = self.cli("send", "--text", "x", "--no-wait", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((send.get("error") or {}).get("code"), "no-session")
        self.assertIs(send.get("mutation_performed"), False)
        self.assertEqual(send.get("mutation_status"), "not_started")

        rc, steer = self.cli("steer", "--text", "y", "--steer-mode", "native",
                             check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((steer.get("error") or {}).get("code"), "no-session")
        self.assertIs(steer.get("mutation_performed"), False)
        self.assertEqual(steer.get("mutation_status"), "not_started")
        self.assertEqual(steer.get("steer_outcome"), "not_consumed")
        self.assertIs(steer.get("steer_consumed"), False)
        self.assertEqual(steer.get("steer_confirmation"), "none")

    def test_record_lost_send_is_unsent(self) -> None:
        registry = self.repo / ".kaola" / "host-registry.json"
        registry.parent.mkdir()
        registry.write_text(json.dumps({
            "schema": "kaola-host-registry/1",
            "hosts": {f"grok/{self.session}": {
                "platform": "grok",
                "session": self.session,
                "repo": self.project,
                "record_dir": str(self.root / "gone" / "record"),
                "socket_path": str(self.root / "gone" / "holder.sock"),
                "holder_pid": os.getpid(),
                "holder_instance_id": "0" * 32,
            }},
        }), encoding="utf-8")

        rc, receipt = self.cli("send", "--text", "x", "--no-wait", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((receipt.get("error") or {}).get("code"), "record-lost")
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(receipt.get("mutation_status"), "not_started")

    def test_holder_socket_missing_send_is_unsent(self) -> None:
        self.start()
        self.cli("stop")
        self.started = False
        record = self.read_record()
        record.update(holder_pid=self.dead_holder().pid, state="ready")
        self.write_record(record)
        sock = Path(record["socket_path"])
        if sock.exists() or sock.is_symlink():
            sock.unlink()

        rc, receipt = self.cli("send", "--text", "x", "--no-wait", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "holder-socket-missing")
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(receipt.get("mutation_status"), "not_started")

    def test_holder_lost_reports_this_request_and_keeps_previous_prompt(self) -> None:
        self.start()
        _, first = self.cli("send", "--text", "first", "--timeout", "20")
        self.assertEqual(first.get("stop_reason"), "end_turn")
        before = self.read_record()["last_prompt"]
        self.assertEqual(before["mutation_status"], "completed")
        fingerprint = before["fingerprint"]
        self.cli("stop")
        self.started = False

        rc, send = self.cli("send", "--text", "second", "--no-wait", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((send.get("error") or {}).get("code"), "holder-lost")
        self.assertIs(send.get("mutation_performed"), False)
        self.assertEqual(send.get("mutation_status"), "not_started")
        self.assertEqual((send.get("previous_prompt") or {}).get("fingerprint"),
                         fingerprint)
        self.assertEqual(((send.get("record") or {}).get("last_prompt") or {})
                         .get("mutation_status"), "completed")

        rc, steer = self.cli("steer", "--text", "third", "--steer-mode", "interrupt",
                             check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((steer.get("error") or {}).get("code"), "holder-lost")
        self.assertIs(steer.get("mutation_performed"), False)
        self.assertEqual(steer.get("mutation_status"), "not_started")
        self.assertEqual(steer.get("steer_outcome"), "not_consumed")
        self.assertIs(steer.get("steer_consumed"), False)

    def test_holder_closed_is_uncertain_and_received_the_request(self) -> None:
        self.start()
        self.cli("stop")
        self.started = False
        record = self.read_record()
        record.update(holder_pid=self.dead_holder().pid, state="ready")
        self.write_record(record)
        sock = Path(record["socket_path"])
        if sock.exists() or sock.is_symlink():
            sock.unlink()
        sock.parent.mkdir(parents=True, exist_ok=True)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(sock))
        server.listen(2)
        server.settimeout(0.2)
        received: list[bytes] = []
        errors: list[BaseException] = []
        ready = threading.Event()
        finished = threading.Event()

        def stub() -> None:
            ready.set()
            try:
                while not finished.is_set():
                    try:
                        connection, _ = server.accept()
                    except socket.timeout:
                        continue
                    try:
                        data = b""
                        while b"\n" not in data:
                            chunk = connection.recv(65536)
                            if not chunk:
                                break
                            data += chunk
                        if not data:
                            continue
                        received.append(data)
                        if b'"op": "prompt"' in data:
                            break
                        # A Host `kaola-acp list` liveness scan can probe a
                        # temporary record's socket before the prompt arrives.
                        # Answer it and keep listening for the request under
                        # test instead of letting the probe consume the stub.
                        try:
                            connection.sendall(b'{"state": "ready"}\n')
                        except OSError:
                            pass
                    finally:
                        connection.close()
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                server.close()

        thread = threading.Thread(target=stub, daemon=True)
        thread.start()
        self.assertTrue(ready.wait(2), "stub never listened")
        # A Host `kaola-acp list` scan can probe this temporary record's
        # socket at any moment. Deliver one probe deterministically so the
        # fixture's multi-connection protection is covered, then run the send
        # whose reply must still decide this receipt.
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(2)
        probe.connect(str(sock))
        probe.sendall(b'{"op": "state", "request_id": "probe", "params": {}}\n')
        probe.recv(65536)
        probe.close()
        try:
            rc, receipt = self.cli("send", "--text", "x", "--no-wait", check=False)
        finally:
            finished.set()
            thread.join(timeout=5)
        self.assertEqual(rc, 0)
        self.assertEqual((receipt.get("error") or {}).get("code"), "holder-closed",
                         {"receipt": receipt, "stub_errors": errors,
                          "stub_received": received})
        self.assertIsNone(receipt.get("mutation_performed"))
        self.assertEqual(receipt.get("mutation_status"), "unknown")
        self.assertFalse(errors, errors)
        prompt_frames = [frame for frame in received if b'"op": "prompt"' in frame]
        self.assertTrue(prompt_frames, {"received": received, "errors": errors})
        self.assertIn(b'"text": "x"', prompt_frames[0])

    def test_holder_unreachable_connect_stage_is_unsent(self) -> None:
        """Issue #383: the transport now proves the connect step failed.

        The stage-less form stays unknown through the unit matrix in
        ``ReceiptClassificationTests``; this integration case pins the real
        socket's connect refusal.
        """
        self.start()
        self.cli("stop")
        self.started = False
        record = self.read_record()
        record.update(holder_pid=self.dead_holder().pid, state="ready")
        self.write_record(record)
        sock = Path(record["socket_path"])
        if sock.exists() or sock.is_symlink():
            sock.unlink()
        sock.parent.mkdir(parents=True, exist_ok=True)
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.bind(str(sock))
        probe.close()

        rc, receipt = self.cli("send", "--text", "x", "--no-wait", check=False)
        self.assertEqual(rc, 0)
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-unreachable")
        self.assertEqual(error.get("stage"), "connect")
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(receipt.get("mutation_status"), "not_started")

    # -- holder busy ---------------------------------------------------------

    def test_busy_send_uses_refused_busy(self) -> None:
        self.start("hang_until_cancel")
        _, first = self.cli("send", "--text", "first", "--no-wait")
        self.assertEqual(first.get("outcome"), "in_progress")
        self.assertIs(first.get("mutation_performed"), True)
        wait_for(lambda: self.cli("observe", check=False)[1].get("turn_active"),
                 10, "mock turn active")

        rc, second = self.cli("send", "--text", "second", "--no-wait", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((second.get("error") or {}).get("code"),
                         "prompt-in-progress")
        self.assertEqual(second.get("outcome"), "refused_busy")
        self.assertIs(second.get("mutation_performed"), False)
        self.assertIn(second.get("mutation_status"), ("accepted", "in_progress"))
        self.assertIsNotNone(second.get("active_turn_request_id"))
        self.cli("cancel", "--timeout", "10", check=False)
        self.cli("stop", "--force", check=False, timeout=30)
        self.started = False

    # -- unchanged paths -----------------------------------------------------

    def test_status_keeps_the_previous_prompt_fact(self) -> None:
        self.start()
        self.cli("send", "--text", "first", "--timeout", "20")
        before = self.read_record()["last_prompt"]
        self.assertEqual(before["mutation_status"], "completed")
        self.cli("stop")
        self.started = False
        record = self.read_record()
        record.update(holder_pid=999999, state="ready")
        self.write_record(record)

        rc, status = self.cli("status", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual((status.get("error") or {}).get("code"), "holder-lost")
        self.assertEqual(status.get("mutation_status"), "completed")
        self.assertIs(status.get("mutation_performed"), True)
        self.assertEqual(((status.get("record") or {}).get("last_prompt") or {})
                         .get("mutation_status"), "completed")

    def test_start_brief_uses_the_prompt_wrapper_without_clobbering_success(self) -> None:
        receipt = self.start("normal", "--text", "brief")
        self.assertTrue(receipt.get("brief_delivered"), receipt)
        self.assertIs(receipt.get("mutation_performed"), True)
        self.assertEqual(receipt.get("prompt_fingerprint"),
                         "sha256:" + hashlib.sha256(b"brief").hexdigest())
        self.cli("stop")
        self.started = False


class ReceiptClassificationTests(unittest.TestCase):
    """The stage hook and the consumer matrix, without a live socket."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("kaola_acp_379", CLI)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        cls.module = module

    def stamp(self, op: str, code: str, stage: str | None = None,
              **extra) -> dict:
        receipt = {"error": {"code": code}}
        if stage is not None:
            receipt["error"]["stage"] = stage
        receipt.update(extra)
        return self.module._stamp_request_mutation(receipt, op)

    def test_stage_hook_classification_matrix(self) -> None:
        for code in ("no-session", "record-lost", "holder-socket-missing"):
            receipt = self.stamp("prompt", code)
            self.assertIs(receipt["mutation_performed"], False, code)
            self.assertEqual(receipt["mutation_status"], "not_started", code)

        receipt = self.stamp("prompt", "holder-lost",
                             record={"last_prompt": {"fingerprint": "sha256:old",
                                                     "mutation_status": "completed"}})
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertEqual(receipt["previous_prompt"]["fingerprint"], "sha256:old")

        for stage in (None, "connect"):
            receipt = self.stamp("prompt", "holder-lost", stage)
            self.assertIs(receipt["mutation_performed"], False, stage)
        # Issue #383: the newline is the last byte, so a failed sendall cannot
        # have delivered a frame the holder can parse. Only a read failure is
        # uncertain.
        receipt = self.stamp("prompt", "holder-lost", "send")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        receipt = self.stamp("prompt", "holder-lost", "read")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

        for stage in (None, "read"):
            receipt = self.stamp("prompt", "holder-closed", stage)
            self.assertIsNone(receipt["mutation_performed"], stage)
            self.assertEqual(receipt["mutation_status"], "unknown", stage)

        receipt = self.stamp("prompt", "holder-unreachable")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")
        receipt = self.stamp("prompt", "holder-unreachable", "connect")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        receipt = self.stamp("prompt", "holder-unreachable", "send")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        receipt = self.stamp("prompt", "holder-unreachable", "read")
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

    def test_holder_explicit_values_are_not_overwritten(self) -> None:
        receipt = self.stamp("prompt", "holder-unreachable", "read",
                             mutation_performed=True,
                             mutation_status="in_progress")
        self.assertIs(receipt["mutation_performed"], True)
        self.assertEqual(receipt["mutation_status"], "in_progress")

        # holder-lost is the one exception: its value is the previous prompt's.
        receipt = self.stamp("prompt", "holder-lost",
                             mutation_performed=True,
                             mutation_status="completed",
                             record={"last_prompt": {"fingerprint": "sha256:old"}})
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")

    def test_non_prompt_steer_operations_are_untouched(self) -> None:
        for op in ("state", "stop", "capture", "permit", "cancel", "observe"):
            receipt = self.stamp(op, "no-session")
            self.assertNotIn("mutation_performed", receipt, op)
            self.assertNotIn("mutation_status", receipt, op)
            self.assertNotIn("steer_outcome", receipt, op)

    def test_steer_companion_fields_match_the_mutation_claim(self) -> None:
        unsent = self.stamp("steer", "no-session")
        self.assertEqual(unsent["steer_outcome"], "not_consumed")
        self.assertIs(unsent["steer_consumed"], False)
        self.assertEqual(unsent["steer_confirmation"], "none")

        uncertain = self.stamp("steer_interrupt", "holder-closed")
        self.assertEqual(uncertain["steer_outcome"], "unknown")
        self.assertIsNone(uncertain["steer_consumed"])
        self.assertEqual(uncertain["steer_confirmation"], "none")

        lost = self.stamp("steer", "holder-lost")
        self.assertEqual(lost["steer_outcome"], "not_consumed")
        self.assertIs(lost["steer_consumed"], False)

    def test_post_wire_holder_death_uses_the_stage(self) -> None:
        receipt = self.stamp("prompt", "holder-lost", _wire_attempted=True,
                             record={"last_prompt": {"fingerprint": "sha256:old"}})
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")
        self.assertNotIn("_wire_attempted", receipt)

        # Issue #383: a send-stage loss never delivered the trailing newline;
        # a read-stage loss may have been admitted.
        receipt = self.stamp("prompt", "holder-lost", "send",
                             _wire_attempted=True)
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        receipt = self.stamp("prompt", "holder-lost", "read",
                             _wire_attempted=True)
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

        # With #383's stage the wire attempt is already classified; connect and
        # send are definitely unsent and read is unknown.
        receipt = self.stamp("prompt", "holder-lost", "connect",
                             _wire_attempted=True)
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")

        # The pre-check has no marker and remains definitely unsent.
        receipt = self.stamp("prompt", "holder-lost")
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")

    def test_brief_failure_keeps_the_request_mutation(self) -> None:
        receipt = {"mutation_status": "not_started", "mutation_performed": False}
        self.module.stamp_brief_undelivered(
            receipt, "holder-closed",
            request_mutation={"mutation_performed": None,
                              "mutation_status": "unknown"})
        self.assertIsNone(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "unknown")

        default = {}
        self.module.stamp_brief_undelivered(default, "brief-turn-unverified")
        self.assertIs(default["mutation_performed"], False)
        self.assertEqual(default["mutation_status"], "not_started")

    def test_consumer_classification_matrix(self) -> None:
        """KaolaTerminal's published branches over these receipt shapes."""

        def classify(receipt: dict) -> str:
            error = receipt.get("error") or {}
            code = error.get("code")
            if code == "holder-lost":
                return "unsent" if receipt.get("mutation_performed") is False else "holder-lost"
            if code:
                if code == "prompt-in-progress":
                    return ("unsent-busy"
                            if receipt.get("mutation_performed") is False
                            else "uncertain")
                return ("unsent"
                        if receipt.get("mutation_performed") is False
                        else "uncertain")
            if (receipt.get("mutation_performed") is True
                    and receipt.get("outcome") == "in_progress"):
                return "accepted"
            return "other"

        no_session = self.stamp("prompt", "no-session")
        self.assertEqual(classify(no_session), "unsent")
        closed = self.stamp("prompt", "holder-closed")
        self.assertEqual(classify(closed), "uncertain")
        busy = self.stamp("prompt", "prompt-in-progress",
                          mutation_performed=False, mutation_status="accepted",
                          outcome="refused_busy")
        self.assertEqual(classify(busy), "unsent-busy")
        lost = self.stamp("prompt", "holder-lost",
                          record={"last_prompt": {"fingerprint": "sha256:old"}})
        self.assertEqual(classify(lost), "unsent")
        accepted = {"mutation_performed": True, "outcome": "in_progress"}
        self.assertEqual(classify(accepted), "accepted")



BOUNDARY_STUB = r"""
import socket, sys, time
from pathlib import Path

sock, ready, frames, mode = sys.argv[1:5]
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(sock)
server.listen(4)
Path(ready).write_text("ready")
deadline = time.monotonic() + 15
while time.monotonic() < deadline:
    server.settimeout(max(0.1, deadline - time.monotonic()))
    try:
        connection, _ = server.accept()
    except socket.timeout:
        break
    data = b""
    while b"\n" not in data:
        chunk = connection.recv(65536)
        if not chunk:
            break
        data += chunk
    with open(frames, "ab") as handle:
        handle.write(data)
    if b'"op": "prompt"' in data:
        if mode == "partial":
            connection.sendall(b'{"incomplete":')
            connection.close()
            break
        connection.close()
        # The start-brief path probes state once after the prompt. Serve that
        # trailing probe so the fixture can exit on its own.
        try:
            server.settimeout(5.0)
            follow, _ = server.accept()
            trailing = b""
            while b"\n" not in trailing:
                chunk = follow.recv(65536)
                if not chunk:
                    break
                trailing += chunk
            with open(frames, "ab") as handle:
                handle.write(trailing)
            follow.close()
        except (socket.timeout, OSError):
            pass
        break
    # A Host `kaola-acp list` scan may probe this temporary record first.
    try:
        connection.sendall(b'{"state": "ready"}\n')
    except OSError:
        pass
    connection.close()
server.close()
"""


class BoundaryIntegrationTests(unittest.TestCase):
    """The two review probes: post-wire death and start-brief failures."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("kaola_acp_379_bound", CLI)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        cls.module = module

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i379-bound-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "kpr379@example.invalid"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "kpr379"],
                       cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("kpr379\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.repo, check=True)
        self.extra: list[subprocess.Popen] = []

    def tearDown(self) -> None:
        for proc in self.extra:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
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

    def args(self, command: str, **kw) -> argparse.Namespace:
        values = {
            "platform": "grok", "session": "grok-w379-boundary",
            "command": command, "wait": False, "timeout": 1,
            "max_final_chars": 1000, "expected_holder_instance_id": None,
        }
        values.update(kw)
        return argparse.Namespace(**values)

    def stub(self, mode: str) -> tuple[subprocess.Popen, Path, Path]:
        sock = self.root / "s"
        ready = self.root / "ready"
        frames = self.root / "frames"
        proc = subprocess.Popen(
            [sys.executable, "-c", BOUNDARY_STUB, str(sock), str(ready),
             str(frames), mode])
        self.extra.append(proc)
        wait_for(ready.exists, 5, "boundary stub ready")
        return proc, sock, frames

    def test_post_write_holder_death_is_unknown(self) -> None:
        proc, sock, frames = self.stub("partial")
        record = {
            "holder_pid": proc.pid,
            "state": "ready",
            "last_prompt": {"fingerprint": "sha256:older",
                            "mutation_status": "completed",
                            "stop_reason": "end_turn"},
        }
        wire: dict = {}
        real_socket = self.module.socket_request

        def read_then_reap(*call_args, **call_kwargs):
            reply = real_socket(*call_args, **call_kwargs)
            wire.update(reply)
            proc.wait(timeout=5)
            return reply

        directory = self.root / "records" / "grok" / "s" / "digest"
        try:
            with patch.object(self.module, "sock_path", return_value=sock), \
                 patch.object(self.module, "read_record", return_value=record), \
                 patch.object(self.module, "socket_request",
                              side_effect=read_then_reap):
                result = self.module.op_or_holder_lost(
                    self.args("send"), str(self.repo), directory, "prompt",
                    {"text": "second", "wait": False}, 1)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        self.assertEqual((wire.get("error") or {}).get("code"),
                         "holder-unreachable")
        # Issue #383: the partial reply proves the frame was read, so this is
        # the read stage, not an unknown pre-wire state.
        self.assertEqual((wire.get("error") or {}).get("stage"), "read")
        self.assertEqual((result.get("error") or {}).get("code"), "holder-lost")
        self.assertIsNone(result.get("mutation_performed"))
        self.assertEqual(result.get("mutation_status"), "unknown")
        self.assertNotIn("_wire_attempted", result)
        self.assertTrue(frames.is_file(), "stub received no request")
        self.assertIn(b'"text": "second"', frames.read_bytes())

    def start_brief_failure(self, source: str) -> None:
        proc, sock, frames = self.stub("close")
        record = {"holder_pid": proc.pid, "state": "ready"}
        ready_receipt = {"state": "ready", "acp_session_id": "fixture-acp",
                         "holder_pid": proc.pid}
        inner: list[dict] = []
        real_op = self.module.op_or_holder_lost

        def capture(*call_args, **call_kwargs):
            reply = real_op(*call_args, **call_kwargs)
            inner.append(reply)
            return reply

        args = self.args("start", text="brief" if source == "text" else None,
                         stdin=source == "stdin")
        stdin = io.StringIO("brief") if source == "stdin" else sys.stdin
        directory = self.root / "records" / "grok" / "s" / "digest"
        try:
            with patch.object(self.module, "sock_path", return_value=sock), \
                 patch.object(self.module, "record_dir", return_value=directory), \
                 patch.object(self.module, "read_record", return_value=record), \
                 patch.object(self.module, "_command_start_seat",
                              return_value=ready_receipt), \
                 patch.object(self.module, "op_or_holder_lost",
                              side_effect=capture), \
                 patch.object(sys, "stdin", stdin):
                result = self.module.command_start(args, str(self.repo))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        self.assertTrue(inner, "start brief did not call the prompt wrapper")
        self.assertEqual((inner[0].get("error") or {}).get("code"),
                         "holder-closed")
        self.assertIsNone(inner[0].get("mutation_performed"))
        self.assertEqual(inner[0].get("mutation_status"), "unknown")
        self.assertEqual((result.get("error") or {}).get("code"),
                         "holder-closed")
        self.assertIsNone(result.get("mutation_performed"))
        self.assertEqual(result.get("mutation_status"), "unknown")
        self.assertFalse(result.get("brief_delivered"))
        self.assertIn(b'"text": "brief"', frames.read_bytes())

    def test_start_brief_text_failure_keeps_unknown(self) -> None:
        self.start_brief_failure("text")

    def test_start_brief_stdin_failure_keeps_unknown(self) -> None:
        self.start_brief_failure("stdin")


if __name__ == "__main__":
    unittest.main()
