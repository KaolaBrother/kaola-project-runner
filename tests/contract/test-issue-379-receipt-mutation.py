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
the status/observe regression boundary, the start-brief prompt path, the
forward ``error.stage`` hook (#383), and the consumer classification matrix.

Run: python3 tests/contract/test-issue-379-receipt-mutation.py -v
"""

from __future__ import annotations

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
import unittest
from pathlib import Path

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
        server.listen(1)
        received: list[bytes] = []
        errors: list[BaseException] = []
        ready = threading.Event()

        def stub() -> None:
            ready.set()
            try:
                connection, _ = server.accept()
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                received.append(data)
                connection.close()
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                server.close()

        thread = threading.Thread(target=stub, daemon=True)
        thread.start()
        self.assertTrue(ready.wait(2), "stub never listened")
        try:
            rc, receipt = self.cli("send", "--text", "x", "--no-wait", check=False)
        finally:
            thread.join(timeout=5)
        self.assertEqual(rc, 0)
        self.assertEqual((receipt.get("error") or {}).get("code"), "holder-closed")
        self.assertIsNone(receipt.get("mutation_performed"))
        self.assertEqual(receipt.get("mutation_status"), "unknown")
        self.assertFalse(errors, errors)
        self.assertTrue(received, "stub received no request")
        self.assertIn(b'"op": "prompt"', received[0])
        self.assertIn(b'"text": "x"', received[0])

    def test_holder_unreachable_without_stage_is_uncertain(self) -> None:
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
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "holder-unreachable")
        self.assertNotIn("stage", receipt.get("error") or {})
        self.assertIsNone(receipt.get("mutation_performed"))
        self.assertEqual(receipt.get("mutation_status"), "unknown")

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
        for stage in ("send", "read"):
            receipt = self.stamp("prompt", "holder-lost", stage)
            self.assertIsNone(receipt["mutation_performed"], stage)
            self.assertEqual(receipt["mutation_status"], "unknown", stage)

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


if __name__ == "__main__":
    unittest.main()
