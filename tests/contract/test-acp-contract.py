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
import shlex
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
# Issue #73 binds Orchestrator dispatch to one canonical root. Suites here start
# against their own throwaway repository, which is an ordinary standalone
# invocation, so they state that intent instead of inheriting the operator shell.
CANONICAL_KEY = "KAOLA_PROJECT_RUNNER_CANONICAL_REPO"

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


def flag_value(tokens: list[str], flag: str) -> str | None:
    for index in range(len(tokens) - 1):
        if tokens[index] == flag:
            return tokens[index + 1]
    return None


def live_process_table() -> dict[int, tuple[str, str]]:
    """pid -> (state, command) for every process on the host."""
    table = subprocess.run(
        ["ps", "-axo", "pid=,state=,command="], capture_output=True, text=True
    )
    found: dict[int, tuple[str, str]] = {}
    for line in table.stdout.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit():
            found[int(fields[0])] = (fields[1].upper(), fields[2])
    return found


def process_gone(pid) -> bool:
    """Zombie-safe liveness, the same read kaola-acp-sweep.py trusts."""
    live = live_process_table().get(pid)
    return live is None or live[0].startswith("Z")


def own_processes(root: Path) -> dict[int, str]:
    """Live processes this suite's temp root still owns.

    Holders are matched by a ``--record-dir``/``--socket`` argv value under
    ``root`` — the exact match ``kaola-acp-sweep.py`` uses. Agents are matched
    through the suite's own ``record.json`` files: the record names the exact
    pids, and a command-name check keeps a reused pid from accusing a foreign
    process. Nothing outside ``root`` is ever reported.
    """
    bases = {str(root), str(root.resolve())}
    table = live_process_table()
    found: dict[int, str] = {}
    for pid, (state, command) in table.items():
        if state.startswith("Z") or "kaola-acp-holder.py" not in command:
            continue
        tokens = command.split()
        values = [
            flag_value(tokens, flag) for flag in ("--record-dir", "--socket")
        ]
        if any(
            value == base or value.startswith(base + os.sep)
            for value in values if value for base in bases
        ):
            found[pid] = command
    records = root / "records"
    if records.is_dir():
        for path in records.glob("*/*/*/record.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for key, marker in (
                ("holder_pid", "kaola-acp-holder.py"),
                ("agent_pid", "mock-acp-agent.py"),
            ):
                pid = record.get(key)
                live = table.get(pid) if isinstance(pid, int) else None
                if live and not live[0].startswith("Z") and marker in live[1]:
                    found[pid] = live[1]
    return found


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
        try:
            if not wait_for(lambda: not own_processes(cls.root), 15):
                raise AssertionError(
                    f"fixture leaked its own processes: {own_processes(cls.root)}"
                )
        finally:
            cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"{SESSION_RE}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False
        self._started_platform = "grok"

    def tearDown(self) -> None:
        if self._started:
            self.cli(
                "stop", "--force", platform=self._started_platform,
                check=False, timeout=15,
            )

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
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
            extra_env: dict[str, str] | None = None,
            platform: str = "grok") -> dict:
        argv = [
            sys.executable, str(CLI), platform, command,
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
        if check and receipt.get("result") == "refused":
            self.fail(f"kaola-acp {command} refused: {receipt.get('reason')}: {receipt.get('detail')}")
        return receipt

    def read_mock_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def start(self, scenario: str = "normal", caps: str = "", turn_ms: int = 0,
              platform: str = "grok") -> dict:
        receipt = self.cli(
            "start", scenario=scenario, caps=caps, turn_ms=turn_ms,
            platform=platform,
        )
        self._started = True
        self._started_platform = platform
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

    def test_runner_preflight_receipt_carries_adapter_base_fields(self) -> None:
        # Issue #114: the shared Runner's default (acp) preflight must still carry
        # the adapter's base fields, not only the ACP/model-policy receipt.
        native = self.root / "grok-114"
        native.write_text("#!/bin/sh\necho 'grok fixture 1.14'\n", encoding="utf-8")
        native.chmod(0o755)
        env = self.env()
        env.pop(CANONICAL_KEY, None)
        env.update(KAOLA_ACP_COMMAND=self.mock_command(), GROK_BIN=str(native))
        result = subprocess.run(
            ["bash", str(PROJECT / "scripts" / "kaola-tmux.sh"), "grok", "preflight",
             "--repo", str(self.repo), "--session", self.session],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt.get("transport", {}).get("selected"), "acp")
        self.assertNotIn("error", receipt)
        self.assertEqual(receipt.get("result"), "ready")
        self.assertEqual(receipt.get("runtime_version"), "grok fixture 1.14")
        self.assertIn("Grok CLI communication is available", receipt.get("detail") or "")

    def test_start_records_launched_cli_version_without_gating(self) -> None:
        # Issue #124: grok's initialize returns no agentInfo, so start records
        # the launched binary's own --version beside acp_verified_versions in
        # record.json and the start receipt. A version that differs from the
        # verified one is a fact only: the session still starts.
        fake = self.root / "bin-124" / "grok"
        fake.parent.mkdir(exist_ok=True)
        fake.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = --version ]; then echo 'grok 9.9.124 (fixture)'; exit 0; fi\n"
            f"exec {shlex.quote(sys.executable)} {shlex.quote(str(MOCK))} --scenario normal\n",
            encoding="utf-8")
        fake.chmod(0o755)
        env = self.env()
        env["PATH"] = f"{fake.parent}{os.pathsep}{env.get('PATH', '')}"
        result = subprocess.run(
            [sys.executable, str(CLI), "grok", "start", "--repo", str(self.repo),
             "--session", self.session, "--command", "grok agent --always-approve stdio"],
            capture_output=True, text=True, env=env, timeout=60)
        self._started = True
        receipt = json.loads(result.stdout)
        self.assertNotIn("error", receipt, receipt)
        verified = next(line for line in (PROJECT / "platforms" / "grok.yaml")
                        .read_text(encoding="utf-8").splitlines()
                        if line.startswith("acp_verified_versions:"))
        expected = {"path": str(fake), "version": "grok 9.9.124 (fixture)",
                    "verified_versions": json.loads(verified.partition(":")[2])}
        self.assertEqual(receipt["transport"].get("cli_version"), expected)
        repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
        record = json.loads((self.record_root / "grok" / self.session / digest
                             / "record.json").read_text(encoding="utf-8"))
        self.assertEqual(record.get("cli_version"), expected)
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


class Issue39HolderInstanceTests(AcpSessionFixture, unittest.TestCase):
    """Issue #39: optional expected-holder-instance binding on permit/cancel.

    A restarted holder at the same platform/session/repo socket identity is a
    different instance. A caller that pins a stale ``holder_instance_id`` must
    get ``holder-instance-mismatch`` with zero agent writes; an omitted flag
    keeps legacy behavior.
    """

    def setUp(self) -> None:
        super().setUp()
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    # -- helpers -------------------------------------------------------------

    def record(self) -> dict:
        repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
        path = self.record_root / "grok" / self.session / digest / "record.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def pending_id(self, timeout: float = 10) -> str:
        found = wait_for(lambda: self.pending_permissions() or None, timeout)
        self.assertTrue(found, f"no pending permission appeared: {self.pending_permissions()}")
        return str(found[0]["request_id"])

    def session_cancels(self) -> list[dict]:
        return [
            event for event in self.read_mock_log()
            if event.get("event") == "session_cancel"
        ]

    def assert_mismatch(self, receipt: dict, expected, actual) -> None:
        error = receipt.get("error") or {}
        self.assertEqual(
            error.get("code"), "holder-instance-mismatch",
            f"expected holder-instance-mismatch, got {receipt}",
        )
        self.assertEqual(error.get("expected_holder_instance_id"), expected)
        self.assertEqual(error.get("holder_instance_id"), actual)
        self.assertEqual(receipt.get("mutation_status"), "not_started")
        self.assertIs(receipt.get("mutation_performed"), False)

    def follow_snapshot(self, timeout: float = 10) -> dict:
        path = self.holder_sock()
        self.assertTrue(path.exists(), f"missing holder socket {path}")
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.settimeout(timeout)
            connection.connect(str(path))
            connection.sendall(json.dumps({
                "op": "follow", "request_id": secrets.token_hex(8), "params": {},
            }).encode("utf-8") + b"\n")
            buffer = bytearray()
            while True:
                data = connection.recv(65536)
                if not data:
                    break
                buffer.extend(data)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if not line.strip():
                        continue
                    event = json.loads(line.decode("utf-8"))
                    if event.get("kind") == "snapshot":
                        return event
        finally:
            connection.close()
        return {}

    def run_list(self) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "list",
             "--platform", "grok", "--repo", str(self.repo)],
            capture_output=True, text=True, env=self.env(), timeout=15,
        )
        return json.loads(result.stdout)

    # -- restart at the same triplet: stale binding must not write -----------

    def test_restart_same_triplet_stale_instance_gets_mismatch(self) -> None:
        self.start(scenario="permission_gate")
        self.cli("send", "--text", "gate", "--no-wait", scenario="permission_gate")
        request_id = self.pending_id()
        holder_a = self.cli("view").get("holder_instance_id")
        self.assertIsInstance(holder_a, str)
        self.assertTrue(holder_a)
        self.assertEqual(self.record().get("holder_instance_id"), holder_a)
        self.cli("stop", "--force")
        self._started = False

        # The restarted holder is a different process instance; the fresh mock
        # reuses the same ACP request id for its first permission.
        self.mock_log.write_text("", encoding="utf-8")
        self.start(scenario="permission_gate")
        self.cli("send", "--text", "gate again", "--no-wait", scenario="permission_gate")
        reused = self.pending_id()
        self.assertEqual(
            reused, request_id,
            "same-triplet restart must surface the reused request_id scenario",
        )
        holder_b = self.cli("view").get("holder_instance_id")
        self.assertNotEqual(holder_b, holder_a)

        stale_permit = self.cli(
            "permit", "--request-id", reused, "--option", "allow",
            "--expected-holder-instance-id", holder_a, check=False,
        )
        self.assert_mismatch(stale_permit, holder_a, holder_b)
        stale_cancel = self.cli(
            "cancel", "--expected-holder-instance-id", holder_a,
            check=False, timeout=15,
        )
        self.assert_mismatch(stale_cancel, holder_a, holder_b)
        stale_escape = self.cli(
            "key", "--key", "escape",
            "--expected-holder-instance-id", holder_a, check=False,
        )
        self.assert_mismatch(stale_escape, holder_a, holder_b)

        # Zero writes reached B's agent; pending permission and turn intact.
        self.assertEqual(
            self.jsonrpc_results_for(reused), [],
            "stale permit/cancel wrote a permission result to the agent",
        )
        self.assertEqual(
            self.session_cancels(), [],
            "stale cancel wrote session/cancel to the agent",
        )
        self.assertIn(
            reused,
            [str(entry["request_id"]) for entry in self.pending_permissions()],
        )
        observe = self.cli("observe", check=False)
        self.assertTrue(observe.get("turn_active"), observe)

        # Fresh call with B's identity settles; omitted flag keeps legacy path.
        granted = self.cli(
            "permit", "--request-id", reused, "--option", "allow",
            "--expected-holder-instance-id", holder_b, check=False,
        )
        self.assertIsNone(granted.get("error"), granted)
        self.assertIn("permitted", granted)
        self.assertTrue(
            wait_for(lambda: len(self.jsonrpc_results_for(reused)) == 1, 5),
            "correctly bound permit never reached the agent",
        )

        self.cli("send", "--text", "legacy cancel", "--no-wait", scenario="permission_gate")
        legacy_pending = self.pending_id()
        legacy = self.cli("cancel", "--timeout", "10", check=False)
        self.assertIsNone(legacy.get("error"), legacy)
        self.assertTrue(
            wait_for(lambda: self.session_cancels(), 5),
            "legacy cancel without the flag never wrote session/cancel",
        )
        self.assertTrue(
            wait_for(
                lambda: self.jsonrpc_results_for(legacy_pending), 5,
            ),
            "legacy cancel did not settle the pending permission",
        )

        # With no turn/pending active a stale binding still mismatches instead
        # of masquerading as the factual no-active-turn outcome.
        settled = self.cli(
            "cancel", "--expected-holder-instance-id", holder_a, check=False,
        )
        self.assert_mismatch(settled, holder_a, holder_b)

    def test_explicit_empty_expected_token_is_not_omitted(self) -> None:
        self.start(scenario="permission_gate")
        self.cli("send", "--text", "gate", "--no-wait", scenario="permission_gate")
        request_id = self.pending_id()
        holder_id = self.cli("view").get("holder_instance_id")
        receipt = self.cli(
            "permit", "--request-id", request_id, "--option", "allow",
            "--expected-holder-instance-id", "", check=False,
        )
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-instance-mismatch", receipt)
        self.assertEqual(error.get("expected_holder_instance_id"), "")
        self.assertEqual(error.get("holder_instance_id"), holder_id)
        self.assertEqual(
            self.jsonrpc_results_for(request_id), [],
            "an explicit empty expected token must not run unguarded",
        )
        self.assertIn(
            request_id,
            [str(entry["request_id"]) for entry in self.pending_permissions()],
        )

    def test_instance_id_exposed_on_all_projections(self) -> None:
        started = self.start()
        holder_id = started.get("holder_instance_id")
        self.assertIsInstance(holder_id, str)
        self.assertTrue(holder_id)
        self.assertEqual(self.record().get("holder_instance_id"), holder_id)
        for command in ("observe", "status", "view"):
            receipt = self.cli(command, check=False)
            self.assertEqual(
                receipt.get("holder_instance_id"), holder_id,
                f"{command} lost holder_instance_id: {receipt}",
            )
        rows = [
            row for row in self.run_list().get("rows", [])
            if row.get("session") == self.session
        ]
        self.assertEqual(len(rows), 1, f"own session missing from list: {rows}")
        self.assertEqual(rows[0].get("holder_instance_id"), holder_id)
        snapshot = self.follow_snapshot()
        self.assertEqual(snapshot.get("kind"), "snapshot", snapshot)
        self.assertEqual(snapshot.get("holder_instance_id"), holder_id)

    def test_native_resume_still_mints_new_instance_id(self) -> None:
        pages = json.dumps({
            "sessions": [{"sessionId": "mock-session-1", "cwd": str(self.repo)}],
        })
        extra_env = {"MOCK_ACP_LIST_PAGES": f"[{pages}]"}
        first = self.cli("start", caps="resume", extra_env=extra_env)
        self._started = True
        holder_a = first.get("holder_instance_id")
        self.assertIsInstance(holder_a, str)
        self.assertTrue(holder_a)
        acp_session = first.get("acp_session_id")
        self.cli("stop", "--force")
        self._started = False

        resumed = self.cli(
            "start", "--resume", str(acp_session), caps="resume",
            extra_env=extra_env, check=False,
        )
        self._started = True
        self.assertIsNone(resumed.get("error"), resumed)
        self.assertEqual(
            resumed.get("acp_session_id"), acp_session,
            "resume must keep the native session id",
        )
        self.assertNotEqual(
            resumed.get("holder_instance_id"), holder_a,
            "native resume must still mint a fresh holder_instance_id",
        )

    def test_concurrent_permit_with_matching_expected_at_most_once(self) -> None:
        self.start(scenario="multi_permission")
        self.cli("send", "--text", "needs permits", "--no-wait", scenario="multi_permission")
        found = wait_for(
            lambda: self.pending_permissions() if len(self.pending_permissions()) == 3 else None,
            10,
        )
        self.assertTrue(found, f"expected 3 pending, saw {self.pending_permissions()}")
        request_id = found[0]["request_id"]
        holder_id = self.cli("view").get("holder_instance_id")
        receipts = self.concurrent_holder_ops(
            2, "permit",
            {"request_id": request_id, "option": "allow",
             "expected_holder_instance_id": holder_id},
        )
        results = self.wait_for_jsonrpc_results(request_id, 2, timeout=1.0)
        winners = [r for r in receipts if r.get("error") is None and "permitted" in r]
        losers = [r for r in receipts if (r.get("error") or {}).get("code")]
        self.assertEqual(len(winners), 1, f"receipts={receipts}")
        self.assertEqual(len(losers), 1, f"receipts={receipts}")
        self.assertEqual(
            (losers[0].get("error") or {}).get("code"), SETTLED_PERMISSION_ERROR,
            f"loser error.code frozen to {SETTLED_PERMISSION_ERROR}; receipts={receipts}",
        )
        self.assertEqual(
            len(results), 1,
            f"agent stdin must see one JSON-RPC result for {request_id}; events={results}",
        )

    def test_shell_wrapper_forwards_expected_flag(self) -> None:
        stub = self.root / f"python-stub-{os.getpid()}"
        # The wrapper reads the platform manifest with Python before it execs
        # kaola-acp.py. Issue #78 moved that read off `python3 - <<heredoc` and
        # onto `python3 -c <program>`, because a here-document deadlocks against
        # its own pipe under load, so the stub recognises both spellings of
        # "this is the manifest read, not the exec". What the test asserts is
        # unchanged: only the exec reaches the argv echo below.
        stub.write_text(
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  -) cat >/dev/null; printf 'pty\\n'; exit 0 ;;\n"
            "  -c) printf 'pty\\n'; exit 0 ;;\n"
            "esac\n"
            "printf '%s\\n' \"$@\"\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        env = self.env()
        env["PYTHON_BIN"] = str(stub)
        runner = PROJECT / "scripts" / "kaola-tmux.sh"
        for value in ("holder-abc-123", ""):
            result = subprocess.run(
                [
                    "bash", str(runner), "grok", "permit",
                    "--repo", str(self.repo), "--session", self.session,
                    "--transport", "acp", "--request-id", "7",
                    "--expected-holder-instance-id", value,
                ],
                capture_output=True, text=True, env=env, timeout=15,
            )
            self.assertEqual(
                result.returncode, 0,
                f"wrapper run failed\nstdout={result.stdout!r}\nstderr={result.stderr!r}",
            )
            argv = result.stdout.splitlines()
            self.assertIn("kaola-acp.py", argv[0])
            self.assertIn("--expected-holder-instance-id", argv)
            index = argv.index("--expected-holder-instance-id")
            self.assertEqual(
                argv[index + 1] if index + 1 < len(argv) else None,
                value,
                f"wrapper must forward the exact value incl. empty: {argv}",
            )


class Issue132HolderIdentityTests(AcpSessionFixture, unittest.TestCase):
    """Issue #132: a live PID is necessary, never sufficient. ``list`` rows
    carry the identity check (record, PID, socket, holder_instance_id) and the
    binding a repo sweep classifies by; ``start`` treats a reused PID as no
    holder without signalling it; ``stop --force`` signals only a PID whose
    argv anchors it to the record; a dead holder's stop proves it gone."""

    def record_path(self, repo: Path | None = None, session: str | None = None) -> Path:
        repo = os.path.realpath(str(repo or self.repo))
        digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
        return self.record_root / "grok" / (session or self.session) / digest / "record.json"

    def write_stale_record(self, holder_pid: int, repo: Path | None = None,
                           session: str | None = None, **extra) -> dict:
        path = self.record_path(repo, session)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"transport": "acp", "platform": "grok", "session": session or self.session,
                  "repo": os.path.realpath(str(repo or self.repo)), "holder_pid": holder_pid,
                  "holder_instance_id": "f" * 32, "state": "ready", "agent_alive": True,
                  "pending_permissions": [], "event_cursor": 0, **extra}
        path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        return record

    def list_rows(self, *args: str) -> list[dict]:
        result = subprocess.run([sys.executable, str(CLI), "list", *args],
                                capture_output=True, text=True, env=self.env(), timeout=30)
        payload = json.loads(result.stdout)
        self.assertEqual(payload.get("schema"), "kaola-acp-list/1")
        return payload["rows"]

    def row(self, rows: list[dict], session: str | None = None) -> dict | None:
        return next((row for row in rows if row["session"] == (session or self.session)), None)

    def dead_pid(self) -> int:
        child = subprocess.Popen(["true"])
        child.wait()
        return child.pid

    def acp_module(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"acp132_{self._testMethodName}", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_t3_same_name_start_on_a_verified_holder_is_session_exists(self) -> None:
        first = self.start()
        # Review L2: the real spawn argv satisfies both anchors.
        module = self.acp_module()
        directory = self.record_path().parent
        self.assertIs(module.holder_argv_anchor(first["holder_pid"], directory), True)
        own = module.holder_argv_paths(first["holder_pid"])
        self.assertEqual(os.path.realpath(own[1]), os.path.realpath(str(self.holder_sock())))
        # Review N3: the holder records its agent's start time at spawn.
        record = json.loads(self.record_path().read_text())
        self.assertIsInstance(record.get("agent_started"), (int, float), record)
        self.assertIn(record["agent_pgid"], module.recorded_groups(record, directory))
        again = self.cli("start", check=False)
        self.assertEqual((again.get("error") or {}).get("code"), "session-exists", again)
        self.assertEqual(again["error"].get("identity"), "verified")
        self.assertEqual(again["error"].get("holder_pid"), first.get("holder_pid"))
        row = self.row(self.list_rows("--repo", str(self.repo)))
        self.assertIsNotNone(row)
        self.assertEqual(row["identity"], "verified")
        self.assertIs(row["host_class"], False)
        self.assertEqual(row["holder_instance_id"], first["holder_instance_id"])

    def test_t9_unbound_live_holder_row_says_unbound(self) -> None:
        self.start()
        row = self.row(self.list_rows("--repo", str(self.repo)))
        self.assertIsNotNone(row)
        self.assertIn("heartbeat_host", row)
        self.assertIsNone(row["heartbeat_host"], "an ordinary worker is unbound, not unknown")
        self.assertIs(row["heartbeat_host_known"], True)
        self.assertIn("dispatcher", row)
        self.assertIsNone(row["dispatcher"], "a start under no holder records no dispatcher")

    def test_t4_reused_pid_is_never_live_and_never_signalled(self) -> None:
        received: list[int] = []
        caught = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT, signal.SIGUSR1)
        previous = {sig: signal.signal(sig, lambda number, _frame: received.append(number))
                    for sig in caught}
        try:
            # A record whose holder PID is this live test process: no socket,
            # and its argv is not a holder of this record directory.
            stale = self.write_stale_record(os.getpid())
            row = self.row(self.list_rows("--repo", str(self.repo)))
            self.assertIsNotNone(row, "a PID-alive record stays in the live-holder view")
            self.assertNotEqual(row["identity"], "verified", row)
            stop = self.cli("stop", "--force", "--expected-holder-instance-id",
                            stale["holder_instance_id"], check=False)
            self.assertIs(stop.get("pid_reused"), True, stop)
            self.assertIs(stop.get("stopped"), True, stop)
            self.assertIs(stop.get("holder_signalled"), False, stop)
            self.assertEqual(stop.get("force_killed_pids"), [], stop)
            self.assertNotIn("error", stop)
            gone = self.cli("status", check=False)
            self.assertEqual((gone.get("error") or {}).get("code"), "no-session", gone)
            # Same fixture again, then a same-name start replaces it.
            self.write_stale_record(os.getpid())
            started = self.start()
            self.assertEqual(started.get("state"), "ready", started)
            self.assertEqual(started.get("replaced_record", {}).get("pid_reused"), True, started)
            self.assertNotEqual(started.get("holder_pid"), os.getpid())
            self.assertEqual(self.row(self.list_rows("--repo", str(self.repo)))["identity"],
                             "verified")
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        self.assertEqual(received, [], "the reused PID's owner received a signal")

    def test_reused_pid_stop_sweeps_surviving_agent_group_before_retiring(self) -> None:
        """Review F2: the dead holder's own groups are swept like any dead
        holder's; only the reused holder PID is spared."""
        orphan = subprocess.Popen(["sleep", "60"], start_new_session=True)
        try:
            stale = self.write_stale_record(os.getpid(), agent_pid=orphan.pid,
                                            agent_pgid=orphan.pid)
            stop = self.cli("stop", "--force", "--expected-holder-instance-id",
                            stale["holder_instance_id"], check=False)
            self.assertIs(stop.get("pid_reused"), True, stop)
            self.assertIn(orphan.pid, stop.get("force_killed_pids") or [], stop)
            self.assertNotIn(os.getpid(), stop.get("force_killed_pids") or [], stop)
            self.assertEqual(stop.get("residual_pids"), [], stop)
            orphan.wait(timeout=10)
            gone = self.cli("status", check=False)
            self.assertEqual((gone.get("error") or {}).get("code"), "no-session", gone)
        finally:
            if orphan.poll() is None:
                orphan.kill()
                orphan.wait()

    def test_same_name_start_over_a_silent_anchored_holder_is_session_exists(self) -> None:
        """Review F3: a live holder whose socket is gone (initializing or
        wedged) keeps its session; no second holder is spawned over it."""
        started = self.start()
        self.holder_sock().unlink()
        again = self.cli("start", check=False)
        self.assertEqual((again.get("error") or {}).get("code"), "session-exists", again)
        self.assertEqual(again["error"].get("identity"), "unreachable", again)
        self.assertEqual(again["error"].get("holder_pid"), started["holder_pid"])
        holders = [pid for pid, command in own_processes(self.root).items()
                   if "kaola-acp-holder" in command and self.session in command]
        self.assertEqual(holders, [started["holder_pid"]], holders)
        self.cli("stop", "--force", "--expected-holder-instance-id",
                 started["holder_instance_id"], check=False)
        self.assertTrue(wait_for(lambda: process_gone(started["holder_pid"]), 10))
        self._started = False

    def test_stop_force_mismatch_on_unreachable_holder_writes_nothing(self) -> None:
        stale = self.write_stale_record(os.getpid())
        refused = self.cli("stop", "--force", "--expected-holder-instance-id", "0" * 32,
                           check=False)
        self.assertEqual((refused.get("error") or {}).get("code"), "holder-instance-mismatch")
        self.assertIs(refused.get("mutation_performed"), False)
        self.assertEqual(json.loads(self.record_path().read_text())["holder_instance_id"],
                         stale["holder_instance_id"], "the record was not retired")
        self.record_path().unlink()

    def test_t7_dead_holder_force_stop_sweeps_and_proves_gone(self) -> None:
        started = self.start()
        holder_pid = started["holder_pid"]
        record = json.loads(self.record_path().read_text())
        os.kill(holder_pid, signal.SIGKILL)
        self.assertTrue(wait_for(lambda: process_gone(holder_pid), 10))
        self.assertTrue(wait_for(lambda: process_gone(record.get("agent_pid")), 10),
                        "the mock agent exits on stdin EOF")
        # A surviving agent group of the dead holder.
        orphan = subprocess.Popen(["sleep", "60"], start_new_session=True)
        try:
            # The stand-in agent carries its own recorded start time (#132 N3).
            module = self.acp_module()
            table = module.run_ps(["pid", "pgid", "state", "lstart"], env=module.PS_ENV)
            started = next(line.split(None, 3)[3].strip() for line in table.stdout.splitlines()
                           if line.split() and line.split()[0] == str(orphan.pid))
            epoch = time.mktime(time.strptime(started, "%a %b %d %H:%M:%S %Y"))
            record.update(agent_pid=orphan.pid, agent_pgid=orphan.pid, agent_started=epoch)
            self.record_path().write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            listed = self.row(self.list_rows("--repo", str(self.repo), "--include-dead"))
            self.assertEqual((listed or {}).get("identity"), "dead", listed)
            self.assertIsNone(self.row(self.list_rows("--repo", str(self.repo))),
                              "the default view stays live holders only")
            stop = self.cli("stop", "--force", "--expected-holder-instance-id",
                            record["holder_instance_id"], check=False)
            self.assertIs(stop.get("holder_lost"), True, stop)
            self.assertIn(orphan.pid, stop.get("force_killed_pids") or [], stop)
            self.assertEqual(stop.get("residual_pids"), [], stop)
            orphan.wait(timeout=10)
            self.assertFalse(self.holder_sock().exists(), "the socket path was unlinked")
            status = self.cli("status", check=False)
            self.assertEqual(status.get("outcome"), "stopped", status)
            self.assertEqual(status.get("residual_pids"), [], status)
        finally:
            if orphan.poll() is None:
                orphan.kill()
                orphan.wait()
        self._started = False

    def test_wedged_holder_without_socket_is_stopped_by_its_argv_anchor(self) -> None:
        started = self.start()
        self.holder_sock().unlink()
        row = self.row(self.list_rows("--repo", str(self.repo)))
        self.assertEqual((row or {}).get("identity"), "unreachable", row)
        stop = self.cli("stop", "--force", "--expected-holder-instance-id",
                        started["holder_instance_id"], check=False)
        self.assertEqual(stop.get("holder_force_killed"), started["holder_pid"], stop)
        self.assertEqual(stop.get("residual_pids"), [], stop)
        self.assertTrue(wait_for(lambda: process_gone(started["holder_pid"]), 10))
        self._started = False

    def test_m1_other_spelling_of_the_root_reaches_the_live_holder(self) -> None:
        """Review M1: a caller spelling the record root differently derives
        another socket path; it must still verify the live holder through the
        socket its argv names, and a force stop must stop it gracefully there
        rather than signal a holder that answers."""
        started = self.start()
        alias = self.root / f"alias-{self._testMethodName}"
        alias.symlink_to(self.record_root)
        env = {"KAOLA_ACP_RECORD_ROOT": str(alias)}
        listed = subprocess.run([sys.executable, str(CLI), "list", "--repo", str(self.repo)],
                                capture_output=True, text=True, timeout=30,
                                env={**self.env(), **env})
        row = self.row(json.loads(listed.stdout)["rows"])
        self.assertEqual((row or {}).get("identity"), "verified", row)
        stop = self.cli("stop", "--force", "--expected-holder-instance-id",
                        started["holder_instance_id"], check=False, extra_env=env)
        self.assertNotIn("holder_force_killed", stop, stop)
        self.assertEqual(os.path.realpath(stop.get("answering_socket") or ""),
                         os.path.realpath(str(self.holder_sock())), stop)
        self.assertTrue(wait_for(lambda: process_gone(started["holder_pid"]), 15))
        status = self.cli("status", check=False)
        self.assertIn(status.get("outcome"), ("stopped",), status)
        self._started = False

    def test_t6_list_repo_filter_never_reaches_another_repo(self) -> None:
        other = self.root / f"other-{self._testMethodName}"
        other.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=other, check=True)
        mine = self.write_stale_record(self.dead_pid())
        theirs = self.write_stale_record(self.dead_pid(), repo=other)
        theirs_bytes = self.record_path(other).read_bytes()
        rows = self.list_rows("--repo", str(self.repo), "--include-dead")
        self.assertTrue(rows and all(row["repo"] == mine["repo"] for row in rows), rows)
        self.assertEqual(self.row(rows)["identity"], "dead")
        self.cli("stop", "--force", "--expected-holder-instance-id",
                 mine["holder_instance_id"], check=False)
        self.assertEqual(self.record_path(other).read_bytes(), theirs_bytes,
                         "another repo's dead record is untouched")
        other_rows = self.list_rows("--repo", str(other), "--include-dead")
        self.assertEqual([row["repo"] for row in other_rows], [theirs["repo"]])


class Issue132AnchorUnitTests(unittest.TestCase):
    """Issue #132 re-review N1/N2/N6: the argv anchor resolves both path
    spellings, reads argv without ``ps``, and an unreadable argv never frees a
    root or licenses a signal; a reused-PID stop keeps a record whose groups
    survive."""

    def setUp(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"acp132_{self._testMethodName}", CLI)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-132-anchor-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def holder_command(self, record_dir: str) -> str:
        return (f"/usr/bin/python3 /x/kaola-acp-holder.py --record-dir {record_dir} "
                "--socket /x/s.sock --repo /r --platform grok --session s")

    def test_n1_anchor_matches_across_path_spellings(self) -> None:
        from unittest.mock import patch
        real = Path(os.path.realpath(self.root)) / "rec"
        real.mkdir()
        spelled = str(self.root / "rec")
        linked = self.root / "alias"
        linked.symlink_to(real)
        for argv_dir, directory in ((spelled, real), (str(real), Path(spelled)),
                                    (str(linked), real)):
            with patch.object(self.module, "process_command",
                              return_value=self.holder_command(argv_dir)):
                self.assertIs(self.module.holder_argv_anchor(os.getpid(), directory), True,
                              (argv_dir, directory))
        with patch.object(self.module, "process_command",
                          return_value=self.holder_command(str(real) + "-other")):
            self.assertIs(self.module.holder_argv_anchor(os.getpid(), real), False)

    @unittest.skipUnless(sys.platform == "darwin", "KERN_PROCARGS2 is macOS")
    def test_n2_argv_is_read_without_ps(self) -> None:
        from unittest.mock import patch
        with patch.object(self.module.subprocess, "run", side_effect=OSError("no ps")):
            command = self.module.process_command(os.getpid())
        self.assertIsNotNone(command)
        self.assertIn("test-acp-contract", command)

    def stale_host(self, holder_pid: int, **extra) -> tuple[object, Path]:
        import argparse
        repo = os.path.realpath(self.root)
        args = argparse.Namespace(platform="grok", session="grok-KPR-orchestrator-new",
                                  record_root=str(self.root / "records"), command="stop")
        old = argparse.Namespace(**{**vars(args), "session": "grok-KPR-orchestrator-old"})
        directory = self.module.record_dir(old, repo)
        directory.mkdir(parents=True)
        record = {"platform": "grok", "session": old.session, "repo": repo,
                  "holder_pid": holder_pid, "holder_instance_id": "e" * 32,
                  "state": "ready", **extra}
        (directory / "record.json").write_text(json.dumps(record), encoding="utf-8")
        return args, directory

    def test_n6_unreadable_argv_holds_the_root_and_refuses_the_stop(self) -> None:
        from unittest.mock import patch
        args, directory = self.stale_host(os.getpid())
        repo = os.path.realpath(self.root)
        with patch.object(self.module, "process_command", return_value=None):
            hosts = self.module.verified_hosts(args, repo)
            self.assertEqual([host["identity"] for host in hosts], ["unreachable"])
            self.assertEqual(hosts[0].get("argv"), "unreadable", hosts)
            with patch.object(self.module, "base_receipt", return_value={}):
                refusal = self.module.host_exists_refusal(args, repo, hosts)
            self.assertIn("unsandboxed shell", refusal["detail"], refusal)
            record = json.loads((directory / "record.json").read_text())
            with patch.object(self.module, "base_receipt", return_value={}), \
                 patch.object(self.module.os, "kill") as kill:
                refused = self.module.force_stop_unreachable(args, repo, directory, record,
                                                             {"force": True})
            self.assertEqual(refused["error"]["code"], "holder-unreachable")
            self.assertEqual([call for call in kill.call_args_list if call.args[1] != 0], [],
                             "only the kill(pid, 0) liveness probe, never a signal")
        self.assertTrue((directory / "record.json").is_file(), "the record stays")
        with patch.object(self.module, "process_command", return_value="/bin/sleep 60"):
            self.assertEqual(self.module.verified_hosts(args, repo), [],
                             "a provably reused PID frees the root")

    def test_n3_agent_group_is_swept_only_under_its_recorded_start_time(self) -> None:
        leader = subprocess.Popen(["sleep", "60"], start_new_session=True)
        try:
            table = self.module.run_ps(["pid", "pgid", "state", "lstart"], env=self.module.PS_ENV)
            started = next(line.split(None, 3)[3].strip() for line in table.stdout.splitlines()
                           if line.split() and line.split()[0] == str(leader.pid))
            epoch = time.mktime(time.strptime(started, "%a %b %d %H:%M:%S %Y"))
            base = {"agent_pid": leader.pid, "agent_pgid": leader.pid}
            self.assertIn(leader.pid, self.module.recorded_groups(
                dict(base, agent_started=epoch)), "the recorded agent group")
            self.assertNotIn(leader.pid, self.module.recorded_groups(
                dict(base, agent_started=epoch - 3600)),
                "a live leader with another start time is a reused id")
            # Review M2: a caller under another time zone renders lstart
            # differently; the epoch comparison still matches.
            other_tz = "UTC" if time.strftime("%z") != "+0000" else "Asia/Shanghai"
            probe = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.util,json,sys;"
                 f"s=importlib.util.spec_from_file_location('k',{str(CLI)!r});"
                 "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                 f"print(json.dumps({leader.pid} in m.recorded_groups("
                 f"{{'agent_pid':{leader.pid},'agent_pgid':{leader.pid},'agent_started':{epoch}}})))"],
                capture_output=True, text=True, timeout=30, env={**os.environ, "TZ": other_tz})
            self.assertEqual(probe.stdout.strip(), "true", (other_tz, probe.stderr[-400:]))
            self.assertIn(leader.pid, self.module.recorded_groups(base),
                          "a record from before #132 keeps its trusted group")
        finally:
            leader.kill()
            leader.wait()

    def test_l3_argv_socket_answering_as_another_instance_is_never_stopped(self) -> None:
        from unittest.mock import patch
        args, directory = self.stale_host(os.getpid())
        repo = os.path.realpath(self.root)
        record = json.loads((directory / "record.json").read_text())
        with patch.object(self.module, "holder_argv_anchor", return_value=True), \
             patch.object(self.module, "answering_socket",
                          return_value=(Path("/x/other.sock"), {"holder_instance_id": "0" * 32})), \
             patch.object(self.module, "base_receipt", return_value={}), \
             patch.object(self.module, "socket_request") as request, \
             patch.object(self.module.os, "kill") as kill:
            receipt = self.module.force_stop_unreachable(args, repo, directory, record,
                                                         {"force": True})
        self.assertEqual(receipt["error"]["code"], "holder-instance-mismatch", receipt)
        request.assert_not_called()
        self.assertEqual([call for call in kill.call_args_list if call.args[1] != 0], [])

    def test_n6_reused_pid_stop_keeps_the_record_while_a_group_survives(self) -> None:
        from unittest.mock import patch
        args, directory = self.stale_host(os.getpid(), agent_pid=424242, agent_pgid=424242)
        repo = os.path.realpath(self.root)
        record = json.loads((directory / "record.json").read_text())
        with patch.object(self.module, "process_command", return_value="/bin/sleep 60"), \
             patch.object(self.module, "base_receipt", return_value={}), \
             patch.object(self.module, "recorded_groups", return_value=[424242]), \
             patch.object(self.module, "live_group_members", return_value=[424243]), \
             patch.object(self.module.os, "kill", side_effect=PermissionError) as kill:
            receipt = self.module.force_stop_unreachable(args, repo, directory, record,
                                                         {"force": True})
        self.assertIs(receipt["pid_reused"], True)
        self.assertIs(receipt["stopped"], False, receipt)
        self.assertEqual(receipt["residual_pids"], [424243])
        self.assertIsNone(receipt["retired_record"])
        self.assertTrue((directory / "record.json").is_file(), "a survivor keeps its record")
        self.assertNotIn(os.getpid(), [call.args[0] for call in kill.call_args_list],
                         "the reused holder PID is never signalled")


class Issue34ModelSelectionAcpTests(AcpSessionFixture, unittest.TestCase):
    """Issue #34: ACP applies resolved model → effort → Fast in order and
    reports each configuration as a receipt, never a hard gate."""

    def cli(self, command: str, *args: str, platform: str = "grok", **kwargs) -> dict:
        argv = [
            sys.executable, str(CLI), platform, command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(
                kwargs.pop("scenario", "normal"),
                kwargs.pop("caps", ""),
                kwargs.pop("turn_ms", 0),
            ),
            *args,
        ]
        env = self.env()
        env.update(kwargs.pop("extra_env", {}) or {})
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env,
            timeout=kwargs.pop("timeout", 30),
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp {platform} {command} did not emit a JSON receipt\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if kwargs.get("check", True) and "error" in receipt:
            self.fail(f"kaola-acp {platform} {command} returned error {receipt['error']}\nreceipt={receipt}")
        if kwargs.get("check", True) and receipt.get("result") == "refused":
            self.fail(f"kaola-acp {platform} {command} refused: {receipt.get('reason')}: {receipt.get('detail')}")
        return receipt

    def start(self, platform: str = "grok", *args: str, **kwargs) -> dict:
        receipt = self.cli("start", *args, platform=platform, **kwargs)
        self._started = True
        self._started_platform = platform
        return receipt

    def test_teardown_stops_the_started_platform(self) -> None:
        # Issue #82: a teardown stop addressed at a platform the test did not
        # start hits a session that does not exist and leaks the real holder.
        started = self.start("codex")
        holder_pid = started.get("holder_pid")
        self.assertIsInstance(holder_pid, int)
        self.tearDown()
        self._started = False
        self.assertTrue(
            wait_for(lambda: process_gone(holder_pid), 10),
            f"codex holder {holder_pid} survived the fixture teardown",
        )

    def config_events(self) -> list[tuple[str, str]]:
        events = []
        for event in self.read_mock_log():
            if event.get("event") != "set_config_option":
                continue
            params = event.get("params") or {}
            config_id = params.get("configId") or params.get("config_id")
            events.append((str(config_id), str(params.get("value"))))
        return events

    def setUp(self) -> None:
        super().setUp()
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def test_codex_default_applies_model_effort_fast_mode_in_order(self) -> None:
        # Issue #145: on codex-acp (measured 1.13.0 on codex 0.155.1; pins at
        # 1.13.1 / 0.156.1 since the 2026-09-24 Pink class-2 report) gpt-6-sol
        # advertises reasoning_effort and applies high (corrects the Issue #142
        # no-effort finding, which was specific to the old 1.11.0 bundled
        # catalog).
        receipt = self.start("codex")
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        self.assertEqual(
            self.config_events(),
            [
                ("model", "gpt-6-sol"),
                ("reasoning_effort", "high"),
                ("fast-mode", "off"),
                ("mode", "agent-full-access"),
            ],
        )
        application = receipt.get("config_application") or {}
        self.assertTrue((application.get("model") or {}).get("applied"))
        self.assertTrue((application.get("effort") or {}).get("applied"))
        self.assertTrue((application.get("fast") or {}).get("applied"))
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "runner-default")
        self.assertEqual(selection.get("tier"), "default")
        self.assertEqual(selection.get("resolved_model"), "gpt-6-sol")
        self.assertEqual(selection.get("resolved_effort"), "high")
        fast = receipt.get("fast") or {}
        self.assertEqual(fast.get("requested"), "off")
        self.assertEqual(fast.get("effective"), "off")
        self.assertEqual(fast.get("applied_via"), "acp-config")

    def test_codex_upgrade_tier_selects_astra(self) -> None:
        receipt = self.start("codex", "--tier", "upgrade")
        self.assertEqual(
            [event for event in self.config_events() if event[0] == "model"],
            [("model", "gpt-6-astra")],
        )
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "runner-upgrade")
        self.assertEqual(selection.get("tier"), "upgrade")

    def test_codex_bare_explicit_model_gets_no_invented_effort(self) -> None:
        receipt = self.start("codex", "--model", "gpt-6-astra")
        events = self.config_events()
        self.assertIn(("model", "gpt-6-astra"), events)
        self.assertNotIn("reasoning_effort", [config_id for config_id, _ in events])
        application = receipt.get("config_application") or {}
        self.assertEqual((application.get("effort") or {}).get("reason"), "no-resolved-value")
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("source"), "user")

    def test_codex_explicit_effort_applies_to_explicit_model(self) -> None:
        self.start("codex", "--model", "gpt-6-astra", "--effort", "low")
        self.assertIn(("reasoning_effort", "low"), self.config_events())

    def test_codex_fast_on_applies_fast_mode(self) -> None:
        receipt = self.start("codex", "--fast", "on")
        self.assertIn(("fast-mode", "on"), self.config_events())
        self.assertEqual((receipt.get("fast") or {}).get("effective"), "on")
        self.assertTrue((receipt.get("fast") or {}).get("applied"))

    def test_grok_fast_on_is_reported_unsupported(self) -> None:
        receipt = self.start("grok", "--fast", "on")
        fast = receipt.get("fast") or {}
        self.assertEqual(fast.get("requested"), "on")
        self.assertEqual(fast.get("effective"), "unsupported")
        self.assertFalse(fast.get("applied"))
        self.assertNotIn("fast-mode", [config_id for config_id, _ in self.config_events()])
        application = receipt.get("config_application") or {}
        self.assertEqual((application.get("fast") or {}).get("reason"), "no-advertised-config-option")

    def test_codex_rejected_model_is_limitation_not_failure(self) -> None:
        receipt = self.start(
            "codex", "--model", "unavailable/model", "--effort", "high",
            caps="strict-config",
        )
        self.assertIsNone(receipt.get("error"), f"rejected option must not fail start: {receipt}")
        application = receipt.get("config_application") or {}
        model = application.get("model") or {}
        self.assertFalse(model.get("applied"))
        self.assertIsNotNone(model.get("error"))
        self.assertTrue((application.get("effort") or {}).get("applied"))
        self.assertTrue((application.get("fast") or {}).get("applied"))
        send = self.cli("send", "--text", "still usable", platform="codex")
        self.assertEqual(send.get("outcome"), "turn_completed")

    def test_codex_resume_preserves_saved_selection(self) -> None:
        pages = [{"sessions": [{"sessionId": "saved-codex-1", "cwd": str(self.repo)}]}]
        receipt = self.start(
            "codex", "--resume", "saved-codex-1", caps="resume",
            extra_env={"MOCK_ACP_LIST_PAGES": json.dumps(pages)},
        )
        events = self.config_events()
        self.assertNotIn("model", [config_id for config_id, _ in events])
        self.assertNotIn("reasoning_effort", [config_id for config_id, _ in events])
        selection = receipt.get("model_selection") or {}
        self.assertTrue(selection.get("preserved"))
        self.assertIsNone(selection.get("resolved_model"))

    def test_preflight_reports_advertised_config_ids_and_selection(self) -> None:
        receipt = self.cli("preflight", platform="codex", check=False)
        advertised = (receipt.get("transport") or {}).get("advertised_config_ids") or []
        for config_id in ("mode", "model", "reasoning_effort", "fast-mode"):
            self.assertIn(config_id, advertised)
        options = (receipt.get("transport") or {}).get("advertised_config_options") or []
        model_option = next((o for o in options if o.get("id") == "model"), {})
        self.assertIn("gpt-6-sol", model_option.get("values") or [])
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("resolved_model"), "gpt-6-sol")
        self.assertFalse((receipt.get("config_application") or {}).get("applied"))

    def test_codex_rejected_fast_config_reports_unknown(self) -> None:
        # A rejected fast config option is a limitation: applied=False and
        # effective=unknown — never the resolved intent reported as fact.
        receipt = self.start(
            "codex", "--fast", "on", caps="strict-config,reject-fast",
        )
        self.assertIsNone(receipt.get("error"), f"rejected fast must not fail start: {receipt}")
        fast = receipt.get("fast") or {}
        self.assertEqual(fast.get("requested"), "on")
        self.assertFalse(fast.get("applied"))
        self.assertEqual(fast.get("effective"), "unknown")
        application = receipt.get("config_application") or {}
        fast_app = application.get("fast") or {}
        self.assertFalse(fast_app.get("applied"))
        self.assertIsNotNone(fast_app.get("error"))
        send = self.cli("send", "--text", "still usable", platform="codex")
        self.assertEqual(send.get("outcome"), "turn_completed")

    def test_fast_variant_model_rejected_reports_unknown(self) -> None:
        # A fast-suffix model ID that the agent rejects must not report
        # fast-on — the fast variant was never applied (model-id path on a
        # platform without a native fast config option).
        receipt = self.start(
            "devin", "--model", "experimental-7-fast", "--fast", "on",
            "--mode", "agent",
            caps="strict-config",
        )
        application = receipt.get("config_application") or {}
        self.assertFalse((application.get("model") or {}).get("applied"))
        fast = receipt.get("fast") or {}
        self.assertFalse(fast.get("applied"))
        self.assertEqual(fast.get("effective"), "unknown")
        self.assertEqual(fast.get("applied_via"), "model-id")

    def test_argv_carried_model_skips_the_redundant_option_apply(self) -> None:
        # Issue #140: devin 3000.11.1 rejects its presets on the ACP model
        # option (-32602) but honours `devin acp --model <id>`. When the spawn
        # argv already carries the resolved model, the option apply is skipped
        # and the receipt names the argv, keeping the stale advertised value.
        command = self.mock_command(caps="strict-config") + " --model swe-2-max"
        env = self.env()
        # devin keeps advertising the stale initial value after the argv set it.
        stale = [{"id": "model", "name": "Model", "category": "model", "type": "select",
                  "currentValue": "swe-2-high",
                  "options": [{"value": "swe-2-high", "name": "SWE-2"}]}]
        env["MOCK_ACP_CONFIG"] = json.dumps(
            {"new": stale, "set_result": {"configOptions": stale}})
        result = subprocess.run(
            [sys.executable, str(CLI), "devin", "start", "--repo", str(self.repo),
             "--session", self.session, "--command", command,
             "--tier", "default", "--mode", "agent"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        self._started = True
        self._started_platform = "devin"
        receipt = json.loads(result.stdout)
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        self.assertEqual(receipt.get("resolved_runtime_model_id"), "swe-2-max")
        self.assertNotIn("model", [config_id for config_id, _ in self.config_events()])
        self.assertEqual((receipt.get("config_application") or {}).get("model"),
                         {"applied": True, "applied_via": "argv", "value": "swe-2-max"})
        selection = receipt.get("effective_selection") or {}
        self.assertEqual(selection.get("effective_model"), "swe-2-max")
        self.assertEqual(selection.get("effective_model_source"), "launch-argv")
        self.assertEqual(selection.get("advertised_model"), "swe-2-high")

    def test_model_not_in_argv_still_goes_through_the_option(self) -> None:
        # Issue #140: without an argv --model the apply path is unchanged.
        receipt = self.start("devin", "--tier", "default", "--mode", "agent",
                             caps="strict-config")
        self.assertIn(("model", "swe-2-max"), self.config_events())
        model = (receipt.get("config_application") or {}).get("model") or {}
        self.assertNotIn("applied_via", model)
        self.assertNotIn("effective_model_source", receipt.get("effective_selection") or {})

    # -- Cursor parameterized picker (client _meta parameterizedModelPicker) --

    def initialize_meta(self) -> dict:
        for event in self.read_mock_log():
            if event.get("event") == "initialize":
                capabilities = (event.get("params") or {}).get("clientCapabilities") or {}
                return capabilities.get("_meta") or {}
        return {}

    def test_cursor_sends_parameterized_picker_init_meta(self) -> None:
        # Cursor unlocks separate model/effort/fast options only when the
        # client negotiates _meta.parameterizedModelPicker during initialize.
        self.start("cursor-cli", caps="cursor-params")
        self.assertEqual(self.initialize_meta(), {"parameterizedModelPicker": True})

    def test_codex_does_not_send_cursor_init_meta(self) -> None:
        # The capability is Cursor-only: other platforms' initialize must not
        # carry the parameterizedModelPicker _meta.
        self.cli("preflight", platform="codex", check=False)
        self.assertEqual(self.initialize_meta(), {})

    def test_cursor_preflight_reports_parameterized_options(self) -> None:
        receipt = self.cli("preflight", platform="cursor-cli", check=False,
                           caps="cursor-params")
        options = (receipt.get("transport") or {}).get("advertised_config_options") or []
        ids = {option.get("id") for option in options}
        self.assertTrue({"model", "reasoning_effort", "fast"} <= ids, f"options={options}")
        fast = next((o for o in options if o.get("id") == "fast"), {})
        self.assertEqual(set(fast.get("values") or []), {"false", "true"})

    def test_cursor_default_exact_order_and_semantics(self) -> None:
        # Grok 4.7 Extra High Fast Off: the picker ID decomposes onto the
        # parameterized surface — native model id, then effort, then the
        # fast STRING "false" — with no semantic substitution.
        receipt = self.start("cursor-cli", caps="cursor-params,strict-config")
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        self.assertEqual(
            self.config_events(),
            [
                ("model", "grok-4.7"),
                ("reasoning_effort", "xhigh"),
                ("fast", "false"),
            ],
        )
        application = receipt.get("config_application") or {}
        effort = application.get("effort") or {}
        self.assertEqual(effort.get("config_id"), "reasoning_effort")
        self.assertIs(effort.get("advertised"), True)
        self.assertEqual(effort.get("candidates"), ["reasoning_effort", "effort"])
        self.assertEqual(receipt.get("effective_selection"), {
            "effective_model": "grok-4.7", "effective_effort": "xhigh",
            "effort_config_id": "reasoning_effort"})
        model = application.get("model") or {}
        self.assertTrue(model.get("applied"))
        self.assertEqual(model.get("requested_id"), "grok-4.7-xhigh")
        self.assertTrue(model.get("mapped"))
        self.assertNotIn("[", str(model.get("value")))
        self.assertTrue((application.get("effort") or {}).get("applied"))
        self.assertTrue((application.get("fast") or {}).get("applied"))
        selection = receipt.get("model_selection") or {}
        self.assertEqual(selection.get("resolved_model"), "grok-4.7-xhigh")
        fast = receipt.get("fast") or {}
        self.assertEqual(fast.get("requested"), "off")
        self.assertEqual(fast.get("effective"), "off")
        self.assertEqual(fast.get("applied_via"), "acp-config")
        send = self.cli("send", "--text", "verify exact semantics", platform="cursor-cli")
        self.assertEqual(send.get("outcome"), "turn_completed")

    def test_cursor_upgrade_tier_maps_opus_base_id(self) -> None:
        receipt = self.start(
            "cursor-cli", "--tier", "upgrade", caps="cursor-params,strict-config",
        )
        self.assertEqual(
            self.config_events(),
            [
                ("model", "claude-opus-5-5"),
                ("effort", "high"),
                ("fast", "false"),
            ],
        )
        model = (receipt.get("config_application") or {}).get("model") or {}
        self.assertTrue(model.get("applied"))
        self.assertEqual(model.get("requested_id"), "claude-opus-5-5-high")
        # Regression guard against a naive flip to reasoning_effort (#135):
        # Claude Opus 5.5 advertises its effort option as ``effort`` (#143).
        effort = (receipt.get("config_application") or {}).get("effort") or {}
        self.assertTrue(effort.get("applied"))
        self.assertEqual(effort.get("config_id"), "effort")
        self.assertIs(effort.get("advertised"), True)
        selection = receipt.get("effective_selection") or {}
        self.assertEqual(selection.get("effective_effort"), "high")
        self.assertEqual(selection.get("effort_config_id"), "effort")

    def test_cursor_explicit_fast_variant_id_decomposes(self) -> None:
        # A bare explicit fast-variant picker ID carries its semantics in the
        # ID: base model value, suffix-derived effort, fast on.
        receipt = self.start(
            "cursor-cli", "--model", "grok-4.7-xhigh-fast",
            caps="cursor-params,strict-config",
        )
        self.assertIn(("model", "grok-4.7"), self.config_events())
        self.assertIn(("reasoning_effort", "xhigh"), self.config_events())
        self.assertIn(("fast", "true"), self.config_events())
        fast = receipt.get("fast") or {}
        self.assertEqual(fast.get("effective"), "on")

    def test_cursor_effort_candidates_fall_back_literally(self) -> None:
        # A model that advertises neither candidate (gpt-5.6-sol: reasoning)
        # gets the first candidate literally; the rejection is a limitation
        # receipt and the session stays usable (#135).
        receipt = self.start(
            "cursor-cli", "--model", "gpt-5.6-sol", "--effort", "medium",
            caps="cursor-params,strict-config",
        )
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        self.assertIn(("model", "gpt-5.6-sol"), self.config_events())
        effort = (receipt.get("config_application") or {}).get("effort") or {}
        self.assertEqual(effort.get("config_id"), "reasoning_effort")
        self.assertIs(effort.get("advertised"), False)
        self.assertIs(effort.get("applied"), False)
        self.assertIn("Unknown model config option: reasoning_effort",
                      json.dumps(effort.get("error")))
        self.assertIsNone((receipt.get("effective_selection") or {}).get("effective_effort"))
        send = self.cli("send", "--text", "still usable", platform="cursor-cli")
        self.assertEqual(send.get("outcome"), "turn_completed")

    def test_cursor_manifest_declares_effort_candidates(self) -> None:
        manifest = (PROJECT / "platforms" / "cursor-cli.yaml").read_text()
        fields = dict(
            (line.split(":", 1)[0], line.split(":", 1)[1].strip().strip('"'))
            for line in manifest.splitlines() if line.startswith("acp_")
        )
        self.assertEqual(fields["acp_effort_config_id"], "reasoning_effort;effort")
        self.assertIn("cli=2026.09.18-9a7762b", fields["acp_verified_versions"])

    def test_single_effort_id_resolves_to_itself(self) -> None:
        # Every other manifest names one id: it is sent unchanged.
        receipt = self.start("grok", "--effort", "high", caps="strict-config")
        effort = (receipt.get("config_application") or {}).get("effort") or {}
        self.assertEqual(effort.get("config_id"), "reasoning_effort")
        self.assertEqual(effort.get("candidates"), ["reasoning_effort"])
        self.assertIs(effort.get("advertised"), True)
        self.assertIn(("reasoning_effort", "high"), self.config_events())

    def test_cursor_fast_on_sends_string_true(self) -> None:
        # Cursor's fast option takes "true"/"false" strings, never the
        # on/off vocabulary other agents use.
        receipt = self.start(
            "cursor-cli", "--fast", "on", caps="cursor-params,strict-config",
        )
        self.assertIn(("fast", "true"), self.config_events())
        self.assertNotIn(("fast", "on"), self.config_events())
        self.assertEqual((receipt.get("fast") or {}).get("effective"), "on")

    def test_cursor_manifest_maps_only_base_ids(self) -> None:
        # Regression for the rejected mapping: acp_model_map may only map
        # picker IDs onto advertised base model values — never a bracketed
        # descriptor that smuggles different effort/fast semantics.
        manifest = (PROJECT / "platforms" / "cursor-cli.yaml").read_text()
        raw = next(
            line.split(":", 1)[1].strip()
            for line in manifest.splitlines()
            if line.startswith("acp_model_map:")
        )
        mapped_values = [
            pair.split("=", 1)[1]
            for pair in json.loads(raw).split(";")
            if "=" in pair
        ]
        self.assertTrue(mapped_values)
        for value in mapped_values:
            self.assertNotIn("[", value, f"descriptor substitution in map: {value}")
            self.assertIn(value, {"grok-4.7", "claude-opus-5-5"})


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
        try:
            if not wait_for(lambda: not own_processes(cls.root), 15):
                raise AssertionError(
                    f"fixture leaked its own processes: {own_processes(cls.root)}"
                )
        finally:
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
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        env.pop(CANONICAL_KEY, None)
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
        self.assertNotEqual(receipt.get("result"), "refused", f"start was refused: {receipt}")
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



class StoppedStatusTests(unittest.TestCase):
    def test_normal_stop_is_distinct_from_loss(self):
        import argparse
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("acp_status_test", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        args = argparse.Namespace(command="status")
        record = {"state": "stopped", "holder_pid": 101, "agent_pid": 102,
                  "agent_pgid": 102, "last_prompt": {"written_at": 1,
                  "stop_reason": "end_turn", "mutation_status": "completed"}}
        with patch.object(module, "base_receipt", return_value={}), \
             patch.object(module, "pid_alive", return_value=False), \
             patch.object(module.subprocess, "run") as ps:
            ps.return_value = subprocess.CompletedProcess([], 0, "", "")
            result = module.holder_lost_receipt(args, "/unused", record)
            self.assertEqual(result["outcome"], "stopped")
            self.assertNotIn("error", result)
            for state in ("ready", "stopping"):
                changed = dict(record, state=state, last_prompt={"written_at": 1})
                result = module.holder_lost_receipt(args, "/unused", changed)
                self.assertEqual(result["error"]["code"], "holder-lost")
                self.assertEqual(result["mutation_status"], "unknown")
            ps.return_value = subprocess.CompletedProcess([], 0, "103 102 S\n", "")
            self.assertEqual(module.holder_lost_receipt(args, "/unused", record)["outcome"], "holder_lost")
            ps.return_value = subprocess.CompletedProcess([], 1, "", "unavailable")
            self.assertEqual(module.holder_lost_receipt(args, "/unused", record)["outcome"], "holder_lost")
            ps.return_value = subprocess.CompletedProcess([], 0, "", "")
            args.command = "send"
            self.assertEqual(module.holder_lost_receipt(args, "/unused", record)["outcome"], "holder_lost")

    def test_stopped_reads_the_spawn_record_only_for_a_session(self):
        """Issue #53: a stopped-record receipt consults the agent's spawn record
        (``children.jsonl`` under the session's record directory) with the
        same identity check as the holder: an entry whose pid is alive in its
        recorded group at its recorded time is residue, a stale one is not. A
        receipt built without a platform/session (no record directory) has no
        spawn record and must not fail."""
        import argparse
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("acp_spawn_record_test", CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        record = {"state": "stopped", "holder_pid": 101, "agent_pid": 102,
                  "agent_pgid": 102, "last_prompt": {"written_at": 1,
                  "stop_reason": "end_turn", "mutation_status": "completed"}}
        with tempfile.TemporaryDirectory() as root:
            args = argparse.Namespace(command="status", platform="claude-code",
                                      session="spawn-record", record_root=root)
            directory = module.record_dir(args, "/unused")
            directory.mkdir(parents=True)
            spawn_record = directory / "children.jsonl"
            child = subprocess.Popen(["sleep", "60"], start_new_session=True)
            try:
                spawned_at = int(time.time() * 1000)
                with patch.object(module, "base_receipt", return_value={}), \
                     patch.object(module, "pid_alive", return_value=False):
                    self.assertEqual(module.holder_lost_receipt(args, "/unused", record)["outcome"],
                                     "stopped", "no spawn record: a clean stop reads as stopped")
                    spawn_record.write_text(json.dumps({"pid": child.pid, "pgid": child.pid,
                                                        "spawned_at": spawned_at,
                                                        "binary": "sleep"}) + "\n")
                    result = module.holder_lost_receipt(args, "/unused", record)
                    self.assertEqual(result["outcome"], "holder_lost",
                                     "a live spawn-recorded child is residue of the stopped session")
                    self.assertIn(child.pid, module.recorded_groups(record, directory))
                    stale = dict(pid=child.pid, pgid=child.pid, binary="sleep",
                                 spawned_at=spawned_at - 60_000)
                    spawn_record.write_text(json.dumps(stale) + "\n")
                    self.assertNotIn(child.pid, module.recorded_groups(record, directory),
                                     "an entry whose spawn time does not match the live process is ignored")
                    early = dict(stale, spawned_at=spawned_at - 3_000)
                    spawn_record.write_text(json.dumps(early) + "\n")
                    self.assertNotIn(child.pid, module.recorded_groups(record, directory),
                                     "a process that started after its recorded spawn is not the recorded child")
                    self.assertEqual(module.holder_lost_receipt(args, "/unused", record)["outcome"], "stopped")
                    spawn_record.write_text("not json\n" + json.dumps({"pid": "x"}) + "\n")
                    self.assertEqual(module.holder_lost_receipt(args, "/unused", record)["outcome"], "stopped")
                    bare = argparse.Namespace(command="status")
                    self.assertIsNone(module.spawn_record_dir(bare, "/unused"))
                    self.assertEqual(module.holder_lost_receipt(bare, "/unused", record)["outcome"], "stopped")
            finally:
                child.kill()
                child.wait()


if __name__ == "__main__":
    unittest.main()
