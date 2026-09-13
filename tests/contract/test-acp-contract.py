#!/usr/bin/env python3
"""Offline contract for the Runner v2 ACP transport PoC (issue #15, Part A).

Drives ``scripts/kaola-acp.py`` against ``tests/contract/mock-acp-agent.py``
and covers every branch in design §7.3/§7.4/§7.6:

- agent dies while a permission request is pending
- stdout emits a half line / a non-JSON line
- stderr floods the pipe
- ``session/cancel`` races ``end_turn``
- ``$/cancel_request`` cascade (agent cancels its own permission, and cancels
  a client request -> client surfaces -32800)
- agent returns ``protocolVersion: 2`` -> ``acp-protocol-version-unsupported``
- agent calls ``fs/*`` / ``elicitation/create`` -> client returns -32601
- JSON-RPC response id arrives as a numeric string
- multiple concurrent permission requests
- ``stop`` sequence leaves no residual pids
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"

SESSION_RE = "acpt"

# Issue #25: sequential second permit on a still-pending *other* id already
# returns this code. Concurrent same-id loser is frozen to the same fact.
SETTLED_PERMISSION_ERROR = "unknown-request"

L0_SEND_WAIT_KEYS = frozenset({
    "schema_version",
    "transport",
    "acp_session_id",
    "prompt_fingerprint",
    "outcome",
    "stop_reason",
    "mutation_status",
    "mutation_performed",
    "duration_ms",
    "final_text",
    "final_text_truncated",
    "tool_calls",
    "side_effects",
    "failed_tools",
    "thinking_chars",
    "context_usage",
    "pending_permissions",
    "event_cursor",
    "event_log_bytes",
    "git",
})
L0_FORBIDDEN_WATCH_KEYS = frozenset({
    "timeline", "thinking_text", "plan", "messages", "tools",
})


def rpc_ids_match(left, right) -> bool:
    if left is None or right is None:
        return False
    if left == right:
        return True
    return str(left) == str(right)


def wait_for(predicate, timeout: float, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


class AcpSessionFixture:
    @classmethod
    def setUpClass(cls) -> None:
        if not CLI.is_file():
            raise AssertionError(f"missing ACP CLI at {CLI}")
        if not MOCK.is_file():
            raise AssertionError(f"missing mock agent at {MOCK}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-acp-contract-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"{SESSION_RE}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=15)

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        return env

    def mock_command(self, scenario: str = "normal", caps: str = "", turn_ms: int = 0) -> str:
        parts = [sys.executable, str(MOCK), "--scenario", scenario]
        if caps:
            parts += ["--caps", caps]
        if turn_ms:
            parts += ["--turn-ms", str(turn_ms)]
        return " ".join(parts)

    def cli(self, command: str, *args: str, check: bool = True, timeout: float = 30,
            scenario: str = "normal", caps: str = "", turn_ms: int = 0,
            extra_env: dict[str, str] | None = None) -> dict:
        argv = [
            sys.executable, str(CLI), "grok", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(scenario, caps, turn_ms),
            *args,
        ]
        env = self.env()
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env, timeout=timeout
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp {command} did not emit a JSON receipt\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if check and "error" in receipt:
            self.fail(f"kaola-acp {command} returned error {receipt['error']}\nreceipt={receipt}")
        return receipt

    def read_mock_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def start(self, scenario: str = "normal", caps: str = "", turn_ms: int = 0) -> dict:
        receipt = self.cli("start", scenario=scenario, caps=caps, turn_ms=turn_ms)
        self._started = True
        return receipt

    def pending_permissions(self) -> list:
        obs = self.cli("observe", check=False)
        return obs.get("pending_permissions") or []

    def jsonrpc_results_for(self, request_id) -> list[dict]:
        """JSON-RPC responses (no method) whose id matches the permission request."""
        found = []
        for event in self.read_mock_log():
            if event.get("event") != "outbound_response":
                continue
            message = event.get("message") or {}
            if "method" in message:
                continue
            event_id = message.get("id", event.get("id"))
            if not rpc_ids_match(event_id, request_id):
                continue
            found.append(event)
        return found

    def holder_sock(self) -> Path:
        repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
        directory = self.record_root / "grok" / self.session / digest
        sock_digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:24]
        return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{sock_digest}.sock"

    def concurrent_holder_ops(self, n: int, op: str, params: dict, timeout: float = 15) -> list[dict]:
        """Two already-connected Unix clients send the same op after one barrier.

        Matches ``kaola-acp.py`` socket framing so the holder race is not hidden
        by CLI process startup.
        """
        path = self.holder_sock()
        self.assertTrue(path.exists(), f"missing holder socket {path}")
        barrier = threading.Barrier(n)
        slots: list[dict | None] = [None] * n
        errors: list[BaseException] = []

        def worker(index: int) -> None:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                connection.settimeout(timeout)
                connection.connect(str(path))
                payload = json.dumps({
                    "op": op,
                    "request_id": secrets.token_hex(8),
                    "params": params,
                }).encode("utf-8") + b"\n"
                barrier.wait(timeout=10)
                connection.sendall(payload)
                buffer = bytearray()
                while True:
                    data = connection.recv(65536)
                    if not data:
                        break
                    buffer.extend(data)
                    if b"\n" in buffer:
                        line, _, _ = buffer.partition(b"\n")
                        slots[index] = json.loads(line.decode("utf-8"))
                        return
                if buffer:
                    slots[index] = json.loads(buffer.decode("utf-8"))
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=timeout + 5)
        still = [thread for thread in threads if thread.is_alive()]
        self.assertFalse(still, f"holder op {op} hung under concurrency")
        self.assertFalse(errors, f"holder op {op} raised {errors!r}")
        return [slot if slot is not None else {} for slot in slots]

    def wait_for_jsonrpc_results(self, request_id, minimum: int, timeout: float = 1.0) -> list[dict]:
        deadline = time.monotonic() + timeout
        found: list[dict] = []
        while time.monotonic() < deadline:
            found = self.jsonrpc_results_for(request_id)
            if len(found) >= minimum:
                return found
            time.sleep(0.05)
        return self.jsonrpc_results_for(request_id)


class AcpContractTests(AcpSessionFixture, unittest.TestCase):
    # -- happy path ----------------------------------------------------------

    def test_send_wait_end_turn_receipt(self) -> None:
        self.start()
        receipt = self.cli("send", "--text", "hello mock")
        self.assertEqual(receipt.get("schema_version"), 3)
        self.assertEqual(receipt.get("transport", {}).get("selected"), "acp")
        self.assertEqual(receipt.get("outcome"), "turn_completed")
        self.assertEqual(receipt.get("stop_reason"), "end_turn")
        self.assertEqual(receipt.get("mutation_status"), "completed")
        self.assertEqual(receipt.get("mutation_performed"), True)
        self.assertIn("MOCK-REPLY", receipt.get("final_text") or "")
        self.assertIsInstance(receipt.get("event_cursor"), int)
        usage = receipt.get("context_usage") or {}
        self.assertEqual(usage.get("used"), 1234)
        self.assertEqual(usage.get("size"), 8192)
        stop = self.cli("stop")
        self.assertEqual(stop.get("residual_pids"), [])

    # -- §7.4: agent dies while a permission request is pending ---------------

    def test_agent_dies_with_pending_permission(self) -> None:
        self.start(scenario="die_during_permission")
        receipt = self.cli("send", "--text", "trigger", "--timeout", "15", check=False)
        self.assertEqual(receipt.get("outcome"), "process_exited")
        # write boundary passed and the agent's first request was seen
        self.assertEqual(receipt.get("mutation_status"), "accepted")
        self.assertEqual(receipt.get("mutation_performed"), True)
        self.assertIsNone(receipt.get("stop_reason"))
        observe = self.cli("observe", check=False)
        self.assertIn("process_exited", json.dumps(observe))
        stop = self.cli("stop", "--force", check=False)
        self.assertIn(stop.get("residual_pids"), ([], None))
        self._started = False

    # -- §7.1: half line and non-JSON line on stdout ---------------------------

    def test_stdout_half_line_and_garbage(self) -> None:
        self.start(scenario="garbage_lines")
        receipt = self.cli("send", "--text", "decode me", "--timeout", "15")
        self.assertEqual(receipt.get("outcome"), "turn_completed")
        self.assertEqual(receipt.get("stop_reason"), "end_turn")
        self.assertIn("MOCK-REPLY", receipt.get("final_text") or "")

    # -- §7.4: stderr flood must not deadlock the turn -------------------------

    def test_stderr_flood_does_not_block(self) -> None:
        self.start(scenario="stderr_flood")
        receipt = self.cli("send", "--text", "flood", "--timeout", "25")
        self.assertEqual(receipt.get("outcome"), "turn_completed")
        self.assertEqual(receipt.get("stop_reason"), "end_turn")

    # -- §7.4: session/cancel races end_turn; first stopReason wins ------------

    def test_cancel_races_end_turn(self) -> None:
        self.start(scenario="slow", turn_ms=30000)
        sent = self.cli("send", "--text", "slow task", "--no-wait")
        self.assertIn(sent.get("mutation_status"), ("in_progress", "accepted"))
        cancel = self.cli("cancel", "--timeout", "10", check=False)
        receipt = self.cli("wait", "--timeout", "10", check=False)
        outcome = (cancel.get("outcome") or receipt.get("outcome"))
        self.assertIn(outcome, ("turn_canceled", "turn_completed"))
        stop_reason = cancel.get("stop_reason") or receipt.get("stop_reason")
        self.assertIn(stop_reason, ("cancelled", "end_turn"))
        self.assertEqual(receipt.get("mutation_status"), "completed")

    # -- §7.3: $/cancel_request cascade ----------------------------------------

    def test_agent_cancels_own_permission_request(self) -> None:
        self.start(scenario="agent_cancels_permission")
        sent = self.cli("send", "--text", "go", "--no-wait")
        self.assertIsNone(sent.get("error"))

        def pending():
            obs = self.cli("observe", check=False)
            return obs.get("pending_permissions") or []

        self.assertTrue(wait_for(lambda: len(pending()) >= 1, 8))
        self.assertTrue(wait_for(lambda: len(pending()) == 0, 8))
        receipt = self.cli("wait", "--timeout", "10")
        self.assertEqual(receipt.get("outcome"), "turn_completed")
        self.assertEqual(receipt.get("stop_reason"), "end_turn")

    def test_agent_cancels_prompt_request_returns_32800(self) -> None:
        self.start(scenario="agent_cancels_prompt")
        receipt = self.cli("send", "--text", "doomed", "--timeout", "15", check=False)
        self.assertIn("-32800", json.dumps(receipt))
        self.assertIn(receipt.get("outcome"), ("turn_canceled", "turn_failed", "cancelled"))

    # -- §7.2: protocolVersion != 1 is refused -----------------------------------

    def test_protocol_version_unsupported(self) -> None:
        receipt = self.cli("start", scenario="protocol_v2", check=False)
        self._started = True  # error-state holder still needs stop --force
        self.assertIn("acp-protocol-version-unsupported", json.dumps(receipt))
        status = self.cli("status", check=False)
        self.assertNotIn('"agent_alive": true', json.dumps(status))
        observe = self.cli("observe", check=False)
        self.assertNotIn('"state": "ready"', json.dumps(observe))

    # -- §7.3: fs/*, elicitation/create, unknown methods -> -32601 ---------------

    def test_unsupported_agent_requests_get_32601(self) -> None:
        self.start(scenario="fs_unknown_calls")
        receipt = self.cli("send", "--text", "call stuff", "--timeout", "20")
        self.assertEqual(receipt.get("outcome"), "turn_completed")
        events = [
            e for e in self.read_mock_log()
            if e.get("event") == "outbound_response" and e.get("method")
        ]
        by_method = {e["method"]: e["message"] for e in events}
        for method in (
            "fs/read_text_file",
            "fs/write_text_file",
            "elicitation/create",
            "kaola/bogus_method",
        ):
            self.assertIn(method, by_method, f"mock never saw a response for {method}")
            self.assertEqual(
                by_method[method].get("error", {}).get("code"), -32601,
                f"{method} expected -32601, got {by_method[method]!r}",
            )

    # -- §7.1: response id as numeric string ------------------------------------

    def test_numeric_string_response_id(self) -> None:
        self.start(scenario="numeric_string_id")
        receipt = self.cli("send", "--text", "lenient ids", "--timeout", "15")
        self.assertEqual(receipt.get("outcome"), "turn_completed")

    # -- §7.3: multiple concurrent permission requests --------------------------

    def test_multiple_concurrent_permissions(self) -> None:
        self.start(scenario="multi_permission")
        self.cli("send", "--text", "needs permits", "--no-wait")

        def pending():
            obs = self.cli("observe", check=False)
            return obs.get("pending_permissions") or []

        found = wait_for(lambda: pending() if len(pending()) == 3 else None, 10)
        self.assertTrue(found, f"expected 3 pending permissions, saw {pending()}")
        ids = {entry["request_id"] for entry in pending()}
        ambiguous = self.cli("permit", "--option", "allow", check=False)
        self.assertIsNotNone(ambiguous.get("error") or ambiguous.get("outcome"))
        for request_id in ids:
            granted = self.cli(
                "permit", "--request-id", str(request_id), "--option", "allow", check=False
            )
            self.assertIsNone(granted.get("error"), f"permit {request_id} failed: {granted}")
        receipt = self.cli("wait", "--timeout", "10")
        self.assertEqual(receipt.get("outcome"), "turn_completed")
        self.assertEqual(receipt.get("stop_reason"), "end_turn")

    # -- §7.6: stop leaves no residual processes ----------------------------------

    def test_stop_leaves_no_residual_pids(self) -> None:
        self.start(scenario="stubborn_child")
        self.cli("send", "--text", "work", "--no-wait")
        spawned = wait_for(
            lambda: [e for e in self.read_mock_log() if e.get("event") == "stubborn_child_spawned"],
            8,
        )
        self.assertTrue(spawned, "mock never spawned its stubborn child")
        child_pid = spawned[0]["pid"]
        receipt = self.cli("stop", check=False, timeout=30)
        self.assertEqual(receipt.get("residual_pids"), [])
        for pid in (child_pid,):
            alive = subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode == 0
            self.assertFalse(alive, f"residual child pid {pid} still running")
        self._started = False

    # -- §4: a second send during an active turn is a fact, not a queue ----------

    def test_send_during_active_turn_is_prompt_in_progress(self) -> None:
        self.start(scenario="hang_until_cancel")
        self.cli("send", "--text", "first", "--no-wait")
        second = self.cli("send", "--text", "second", "--no-wait", check=False)
        self.assertIn("prompt-in-progress", json.dumps(second))
        cancel = self.cli("cancel", "--timeout", "10", check=False)
        self.assertIn(cancel.get("outcome"), ("turn_canceled", None))
        receipt = self.cli("wait", "--timeout", "10", check=False)
        self.assertEqual(receipt.get("stop_reason"), "cancelled")


class Issue25PermitLockTests(AcpSessionFixture, unittest.TestCase):
    """Issue #25: at-most-once permit/cancel on one request_id.

    Distinct-id concurrency stays in ``test_multiple_concurrent_permissions``.
    """

    def env(self) -> dict[str, str]:
        env = super().env()
        hook = PROJECT / "tests" / "contract" / "hooks"
        env["PYTHONPATH"] = str(hook) + os.pathsep + env.get("PYTHONPATH", "")
        return env

    def setUp(self) -> None:
        super().setUp()
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def test_sequential_second_permit_same_id_is_unknown_request(self) -> None:
        self.start(scenario="multi_permission")
        self.cli("send", "--text", "needs permits", "--no-wait", scenario="multi_permission")
        found = wait_for(lambda: self.pending_permissions() if len(self.pending_permissions()) == 3 else None, 10)
        self.assertTrue(found, f"expected 3 pending permissions, saw {self.pending_permissions()}")
        request_id = found[0]["request_id"]
        first = self.cli(
            "permit", "--request-id", str(request_id), "--option", "allow",
            check=False, scenario="multi_permission",
        )
        self.assertIsNone(first.get("error"), f"first permit failed: {first}")
        self.assertIn("permitted", first)
        second = self.cli(
            "permit", "--request-id", str(request_id), "--option", "allow",
            check=False, scenario="multi_permission",
        )
        error = second.get("error") or {}
        self.assertEqual(
            error.get("code"), SETTLED_PERMISSION_ERROR,
            f"sequential second permit must be {SETTLED_PERMISSION_ERROR}, got {second}",
        )
        self.assertNotIn("permitted", second)
        results = self.wait_for_jsonrpc_results(request_id, 1)
        self.assertEqual(
            len(results), 1,
            f"sequential second permit must not write agent stdin again: {results}",
        )

    def test_concurrent_permit_same_request_id_at_most_once(self) -> None:
        self.start(scenario="multi_permission")
        self.cli("send", "--text", "needs permits", "--no-wait", scenario="multi_permission")
        found = wait_for(lambda: self.pending_permissions() if len(self.pending_permissions()) == 3 else None, 10)
        self.assertTrue(found, f"expected 3 pending permissions, saw {self.pending_permissions()}")
        request_id = found[0]["request_id"]
        receipts = self.concurrent_holder_ops(
            2, "permit", {"request_id": request_id, "option": "allow"},
        )
        results = self.wait_for_jsonrpc_results(request_id, 2, timeout=1.0)
        winners = [
            receipt for receipt in receipts
            if receipt.get("error") is None and "permitted" in receipt
        ]
        losers = [receipt for receipt in receipts if (receipt.get("error") or {}).get("code")]
        self.assertEqual(
            len(winners), 1,
            f"exactly one concurrent permit may succeed; receipts={receipts}",
        )
        self.assertEqual(
            len(losers), 1,
            f"loser must return a structured error fact, not hang or success; receipts={receipts}",
        )
        self.assertEqual(
            (losers[0].get("error") or {}).get("code"), SETTLED_PERMISSION_ERROR,
            f"loser error.code frozen to {SETTLED_PERMISSION_ERROR}; receipts={receipts}",
        )
        self.assertNotIn("permitted", losers[0])
        tagged = [
            event for event in results
            if event.get("method") == "session/request_permission"
            or ((event.get("message") or {}).get("result") or {}).get("outcome")
        ]
        self.assertEqual(
            len(results), 1,
            f"agent stdin must see one JSON-RPC result for {request_id}; events={results}",
        )
        self.assertEqual(len(tagged), 1, f"permission results for {request_id}: {tagged}")

    def test_concurrent_cancel_same_pending_id_at_most_once(self) -> None:
        self.start(scenario="permission_gate")
        self.cli("send", "--text", "gate", "--no-wait", scenario="permission_gate")
        found = wait_for(lambda: self.pending_permissions() if self.pending_permissions() else None, 10)
        self.assertTrue(found, f"expected a pending permission, saw {self.pending_permissions()}")
        request_id = found[0]["request_id"]
        self.concurrent_holder_ops(2, "cancel", {"timeout": 10})
        results = self.wait_for_jsonrpc_results(request_id, 2, timeout=1.0)
        cancelled = []
        for event in results:
            message = event.get("message") or {}
            outcome = (message.get("result") or {}).get("outcome")
            if outcome == "cancelled" or (
                isinstance(outcome, dict) and outcome.get("outcome") == "cancelled"
            ):
                cancelled.append(event)
        self.assertLessEqual(
            len(cancelled), 1,
            f"op_cancel must not double-cancel {request_id}; events={cancelled}",
        )
        self.assertEqual(
            len(results), 1,
            f"at most one JSON-RPC result for pending id {request_id}; events={results}",
        )

    def test_l0_send_wait_receipt_keys_unchanged(self) -> None:
        self.start()
        receipt = self.cli("send", "--text", "hello mock")
        missing = sorted(L0_SEND_WAIT_KEYS - set(receipt))
        self.assertFalse(missing, f"L0 send --wait lost keys {missing}")
        leaked = sorted(L0_FORBIDDEN_WATCH_KEYS & set(receipt))
        self.assertFalse(leaked, f"L0 send --wait grew watch keys {leaked}")
        self.assertEqual(receipt.get("schema_version"), 3)
        self.assertEqual((receipt.get("transport") or {}).get("selected"), "acp")
        options = []
        for entry in receipt.get("pending_permissions") or []:
            options.extend(entry.get("options") or [])
        for option in options:
            self.assertEqual(set(option), {"id", "kind", "label"}, option)


class Issue22KimiDefaultYoloAcpTests(unittest.TestCase):
    """Issue #22: default kimi ACP start (no --mode) must set mode=yolo."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-acp-issue22-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"acp22-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        if self._started:
            self._run("stop", "--force")

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        env["KAOLA_ACP_COMMAND"] = (
            f"{sys.executable} {MOCK} --scenario permission_unless_yolo"
        )
        return env

    def _run(self, command: str, *args: str, timeout: float = 30) -> dict:
        argv = [
            "bash", str(PROJECT / "scripts" / "kaola-tmux.sh"),
            "kimi-cli", command, "--repo", str(self.repo), "--session", self.session,
            *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kimi-cli {command} did not emit JSON rc={result.returncode} "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )

    def test_public_default_start_sets_mode_yolo(self) -> None:
        receipt = self._run("start")
        self._started = True
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        events = [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        yolo = [
            event
            for event in events
            if event.get("event") == "set_config_option"
            and (event.get("params") or {}).get("value") == "yolo"
            and (
                (event.get("params") or {}).get("configId") == "mode"
                or (event.get("params") or {}).get("config_id") == "mode"
            )
        ]
        self.assertTrue(
            yolo,
            "default start must set ACP mode=yolo without caller --permission-mode; "
            f"events={events}",
        )
        send = self._run("send", "--text", "use a tool", "--timeout", "15")
        self.assertEqual(send.get("outcome"), "turn_completed")
        self.assertEqual(send.get("stop_reason"), "end_turn")


if __name__ == "__main__":
    unittest.main()
