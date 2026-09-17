#!/usr/bin/env python3
"""Issue #27 contract: local holder `follow` NDJSON stream.

Pins docs/acp-watch/follow.md against the request/response holder. Does not
cover list/view (#26) or permit double-answer (#25) beyond a third-socket
permit while followers are attached. Live CLI UAT is not claimed here.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
SAMPLE = PROJECT / "tests" / "contract" / "fixtures" / "kaola-acp-view-1.sample.json"

FOLLOW_KINDS = {"snapshot", "delta", "heartbeat", "eof", "error"}
FOLLOW_QUEUE_CAP = 256
L0_FORBIDDEN = {"timeline", "thinking_text", "plan", "messages", "tools"}
WRITE_OPS = ("prompt", "permit", "cancel", "stop")


def wait_for(predicate, timeout: float, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def assert_shape(test: unittest.TestCase, sample: Any, actual: Any, path: str) -> None:
    sample_t = json_type_name(sample)
    actual_t = json_type_name(actual)
    if sample is None:
        return
    test.assertEqual(
        actual_t, sample_t,
        f"{path}: expected {sample_t}, got {actual_t} ({actual!r})",
    )
    if isinstance(sample, dict):
        missing = set(sample) - set(actual)
        test.assertFalse(missing, f"{path}: missing keys {sorted(missing)}")
        for key, expected in sample.items():
            assert_shape(test, expected, actual[key], f"{path}.{key}")
        return
    if isinstance(sample, list):
        if not sample:
            return
        test.assertTrue(actual, f"{path}: expected a non-empty array")
        if isinstance(sample[0], dict) and "type" in sample[0]:
            for index, item in enumerate(actual):
                test.assertIsInstance(item, dict, f"{path}[{index}]")
                test.assertIn("type", item, f"{path}[{index}]")
            return
        if isinstance(sample[0], dict):
            for index, item in enumerate(actual):
                assert_shape(test, sample[0], item, f"{path}[{index}]")


def follow_view_payload(event: dict) -> dict:
    if event.get("schema") == "kaola-acp-view/1":
        return event
    for key in ("payload", "view", "snapshot", "delta", "data"):
        inner = event.get(key)
        if isinstance(inner, dict) and (
            inner.get("schema") == "kaola-acp-view/1" or "event_cursor" in inner
        ):
            return inner
    return event


def follow_cursor(event: dict) -> int | None:
    payload = follow_view_payload(event)
    for candidate in (payload.get("event_cursor"), event.get("event_cursor"), event.get("cursor")):
        if isinstance(candidate, int):
            return candidate
    return None


def follow_error_code(event: dict) -> str | None:
    err = event.get("error")
    if isinstance(err, dict) and err.get("code") is not None:
        return str(err.get("code"))
    if isinstance(err, str):
        return err
    if event.get("code") is not None:
        return str(event.get("code"))
    return None


def tool_ids_from_events(events: list[dict]) -> set[str]:
    found: set[str] = set()
    for event in events:
        if event.get("kind") not in {"snapshot", "delta"}:
            continue
        payload = follow_view_payload(event)
        for tool in payload.get("tools") or []:
            if isinstance(tool, dict) and tool.get("toolCallId"):
                found.add(str(tool["toolCallId"]))
    return found


class LineCollector:
    """Drain a follow CLI stdout so a live stream cannot stall the test pipe."""

    def __init__(self, proc: subprocess.Popen, pause_after_kinds: int | None = None):
        self.proc = proc
        self.pause_after_kinds = pause_after_kinds
        self.paused = threading.Event()
        self.resume = threading.Event()
        self.closed = threading.Event()
        self.raw_lines: list[str] = []
        self.events: list[dict] = []
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if proc.stderr is not None:
            self.err_thread = threading.Thread(target=self._drain_err, daemon=True)
            self.err_thread.start()
        else:
            self.err_thread = None
        self.stderr_text = ""

    def _drain_err(self) -> None:
        assert self.proc.stderr is not None
        self.stderr_text = self.proc.stderr.read() or ""

    def _run(self) -> None:
        stdout = self.proc.stdout
        if stdout is None:
            self.closed.set()
            return
        try:
            for line in stdout:
                with self._lock:
                    self.raw_lines.append(line)
                    try:
                        parsed = json.loads(line)
                    except ValueError:
                        parsed = None
                    if isinstance(parsed, dict):
                        self.events.append(parsed)
                        kinds = sum(1 for item in self.events if item.get("kind") in FOLLOW_KINDS)
                    else:
                        kinds = 0
                if (
                    self.pause_after_kinds is not None
                    and kinds >= self.pause_after_kinds
                    and not self.resume.is_set()
                ):
                    self.paused.set()
                    self.resume.wait()
        finally:
            self.closed.set()

    def snapshot(self) -> tuple[list[str], list[dict]]:
        with self._lock:
            return list(self.raw_lines), list(self.events)

    def wait_kind(self, kind: str, timeout: float) -> dict | None:
        def found():
            _, events = self.snapshot()
            for event in events:
                if event.get("kind") == kind:
                    return event
            return None

        return wait_for(found, timeout)

    def wait_tool(self, tool_id: str, timeout: float) -> bool:
        return bool(wait_for(lambda: tool_id in tool_ids_from_events(self.snapshot()[1]), timeout))

    def wait_error_code(self, code: str, timeout: float) -> dict | None:
        def found():
            for event in self.snapshot()[1]:
                if event.get("kind") == "error" and follow_error_code(event) == code:
                    return event
            return None

        return wait_for(found, timeout)

    def unpause(self) -> None:
        self.resume.set()


class AcpFollowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (CLI, HOLDER, MOCK, SAMPLE):
            if not path.is_file():
                raise AssertionError(f"missing {path}")
        cls.sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-acp-follow-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.repo = Path(os.path.realpath(cls.repo))
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self._started: list[tuple[str, str, Path]] = []
        self._follows: list[subprocess.Popen] = []
        self._collectors: list[LineCollector] = []
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        for collector in self._collectors:
            collector.unpause()
        for proc in list(self._follows):
            if proc.poll() is None:
                try:
                    os.kill(proc.pid, signal.SIGCONT)
                except OSError:
                    pass
                proc.send_signal(signal.SIGKILL)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
        # The follow CLIs run with text pipes. Killing the process reaps it,
        # but the test-side stream wrappers stay open until gc, which surfaces
        # ResourceWarnings during suite teardown; let the collector threads
        # reach EOF and close the streams explicitly before clearing.
        for collector in self._collectors:
            collector.thread.join(timeout=2)
            if collector.err_thread is not None:
                collector.err_thread.join(timeout=2)
        for proc in self._follows:
            for stream in (proc.stdout, proc.stderr, proc.stdin):
                if stream is not None:
                    try:
                        stream.close()
                    except (OSError, ValueError):
                        pass
        self._follows.clear()
        self._collectors.clear()
        for platform, session, repo in list(self._started):
            self.run_cli(
                platform, "stop", repo=repo, session=session,
                extra=["--force"], check=False, timeout=15,
            )
        self._started.clear()

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        return env

    def mock_command(self, scenario: str = "normal") -> str:
        return " ".join([sys.executable, str(MOCK), "--scenario", scenario])

    def run_raw(self, argv: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout,
        )

    def load_object(self, result: subprocess.CompletedProcess, context: str) -> dict:
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"{context} did not emit one JSON object\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        self.assertIsInstance(payload, dict, f"{context} stdout must be one JSON object")
        return payload

    def run_cli(
        self,
        platform: str,
        command: str,
        *args: str,
        repo: Path | None = None,
        session: str | None = None,
        scenario: str = "normal",
        extra: list[str] | None = None,
        check: bool = True,
        timeout: float = 30,
    ) -> dict:
        target = repo or self.repo
        name = session or f"fol-{platform[:4]}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        argv = [
            sys.executable, str(CLI), platform, command,
            "--repo", str(target), "--session", name,
            "--command", self.mock_command(scenario),
            *(extra or []),
            *args,
        ]
        result = self.run_raw(argv, timeout=timeout)
        receipt = self.load_object(result, f"kaola-acp {platform} {command}")
        if check and "error" in receipt:
            self.fail(f"kaola-acp {platform} {command} error {receipt['error']}\n{receipt}")
        return receipt

    def start(
        self,
        platform: str = "grok",
        repo: Path | None = None,
        session: str | None = None,
        scenario: str = "normal",
    ) -> tuple[str, Path, dict]:
        target = repo or self.repo
        name = session or f"fol-{platform[:4]}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        receipt = self.run_cli(
            platform, "start", repo=target, session=name, scenario=scenario,
        )
        self._started.append((platform, name, target))
        return name, target, receipt

    def run_view(
        self,
        platform: str,
        session: str,
        repo: Path,
        *args: str,
        check: bool = True,
        timeout: float = 30,
    ) -> dict:
        argv = [
            sys.executable, str(CLI), platform, "view",
            "--repo", str(repo), "--session", session, *args,
        ]
        result = self.run_raw(argv, timeout=timeout)
        payload = self.load_object(result, f"kaola-acp {platform} view")
        if check and payload.get("error"):
            self.fail(f"kaola-acp view error {payload['error']}\n{payload}")
        return payload

    def run_list(self) -> dict:
        result = self.run_raw([sys.executable, str(CLI), "list"])
        return self.load_object(result, "kaola-acp list")

    def record_dir(self, platform: str, session: str, repo: Path) -> Path:
        digest = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:16]
        return self.record_root / platform / session / digest

    def read_record(self, platform: str, session: str, repo: Path) -> dict:
        path = self.record_dir(platform, session, repo) / "record.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def holder_sock(self, platform: str, session: str, repo: Path) -> Path:
        directory = self.record_dir(platform, session, repo)
        digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:24]
        return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"

    def read_mock_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def inbound_trace(self) -> list[tuple]:
        trace = []
        for event in self.read_mock_log():
            name = event.get("event")
            if name in {
                "inbound_frame", "prompt", "outbound_response",
                "unparseable_inbound", "session_cancel",
            }:
                trace.append((
                    name,
                    event.get("method"),
                    event.get("id"),
                    event.get("text") if name == "prompt" else None,
                    event.get("line") if name == "unparseable_inbound" else None,
                ))
        return trace

    def spawn_follow(
        self,
        platform: str,
        session: str,
        repo: Path,
        extra: list[str] | None = None,
        pause_after_kinds: int | None = None,
    ) -> tuple[subprocess.Popen, LineCollector]:
        argv = [
            sys.executable, str(CLI), platform, "follow",
            "--repo", str(repo), "--session", session,
            *(extra or []),
        ]
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            text=True,
            bufsize=1,
        )
        self._follows.append(proc)
        collector = LineCollector(proc, pause_after_kinds=pause_after_kinds)
        self._collectors.append(collector)
        return proc, collector

    def wait_snapshot(self, collector: LineCollector, timeout: float = 8) -> dict:
        event = collector.wait_kind("snapshot", timeout)
        self.assertIsNotNone(
            event,
            f"follow never emitted kind=snapshot; events={collector.snapshot()[1]!r} "
            f"raw={collector.snapshot()[0]!r} stderr={collector.stderr_text!r} "
            f"rc={collector.proc.poll()}",
        )
        assert event is not None
        return event

    def assert_heartbeat_shape(self, events: list[dict]) -> None:
        for event in events:
            if event.get("kind") != "heartbeat":
                continue
            payload = follow_view_payload(event)
            self.assertTrue(
                "pending_permissions" in event or "pending_permissions" in payload,
                f"heartbeat missing pending_permissions: {event}",
            )
            self.assertTrue(
                "mutation_status" in event
                or "mutation_status" in payload
                or isinstance((payload.get("turn") or {}).get("mutation_status"), str),
                f"heartbeat missing mutation_status: {event}",
            )

    def assert_stream_kinds(self, events: list[dict]) -> None:
        self.assertTrue(events, "follow stdout produced no NDJSON objects")
        for event in events:
            self.assertIn(event.get("kind"), FOLLOW_KINDS, event)

    def test_follow_usage_missing_session_is_exit_2(self) -> None:
        result = self.run_raw([
            sys.executable, str(CLI), "grok", "follow",
            "--repo", str(self.repo),
        ])
        self.assertEqual(result.returncode, 2, result.stderr)
        combined = f"{result.stdout}\n{result.stderr}".lower()
        self.assertNotIn(
            "invalid choice: 'follow'",
            combined,
            "follow must be a real command; usage errors stay exit 2",
        )
        self.assertIn("session", combined)

    def test_follow_prints_snapshot_then_increasing_cursor_deltas(self) -> None:
        session, repo, _ = self.start("grok", scenario="watch_projection")
        _proc, collector = self.spawn_follow("grok", session, repo)
        snapshot = self.wait_snapshot(collector)
        payload = follow_view_payload(snapshot)
        self.assertEqual(payload.get("schema"), "kaola-acp-view/1", snapshot)
        start_cursor = follow_cursor(snapshot)
        self.assertIsInstance(start_cursor, int, snapshot)

        self.run_cli(
            "grok", "send", "--text", "Fix the login redirect loop.", "--no-wait",
            session=session, repo=repo, scenario="watch_projection",
        )
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "watch_projection_emitted"
                    for event in self.read_mock_log()
                ),
                8,
            ),
            "mock never emitted watch_projection",
        )
        self.assertTrue(collector.wait_tool("call_7", 8), collector.snapshot()[1])

        _, events = collector.snapshot()
        self.assert_stream_kinds(events)
        self.assert_heartbeat_shape(events)
        stream = [event for event in events if event.get("kind") in {"snapshot", "delta"}]
        self.assertGreaterEqual(len(stream), 2, events)
        self.assertEqual(stream[0].get("kind"), "snapshot", stream[0])
        cursors = []
        for event in stream:
            cursor = follow_cursor(event)
            self.assertIsInstance(cursor, int, event)
            cursors.append(cursor)
        self.assertGreater(cursors[-1], cursors[0], cursors)
        for previous, current in zip(cursors, cursors[1:]):
            self.assertGreaterEqual(current, previous, cursors)
        deltas = [event for event in stream[1:] if event.get("kind") == "delta"]
        self.assertTrue(deltas, f"expected cursor deltas after snapshot: {events}")
        for previous, event in zip(deltas, deltas[1:]):
            self.assertGreater(follow_cursor(event), follow_cursor(previous), events)

        since = follow_cursor(stream[-1])
        late_proc, late = self.spawn_follow(
            "grok", session, repo, extra=["--since", str(since)],
        )
        self.assertIsNone(
            late_proc.poll(),
            f"--since must be accepted on follow; rc={late_proc.poll()} stderr={late.stderr_text!r}",
        )
        self.assertTrue(
            wait_for(lambda: bool(late.snapshot()[1]) or late.proc.poll() is None, 3),
        )
        for event in late.snapshot()[1]:
            if event.get("kind") in {"snapshot", "delta"}:
                cursor = follow_cursor(event)
                self.assertIsInstance(cursor, int, event)
                self.assertGreaterEqual(cursor, since, event)

    def test_two_followers_see_the_same_tool_call(self) -> None:
        session, repo, _ = self.start("grok", scenario="watch_projection")
        _left_proc, left = self.spawn_follow("grok", session, repo)
        _right_proc, right = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(left)
        self.wait_snapshot(right)
        self.run_cli(
            "grok", "send", "--text", "Fix the login redirect loop.", "--no-wait",
            session=session, repo=repo, scenario="watch_projection",
        )
        # The scenario emits call_7, then plan/usage/mode updates, then leaves a
        # permission request pending; each step fans out its own delta. Sample
        # the settled view (call_7 present and the permission pending) rather
        # than the first delta that shows call_7, which under load can be
        # observed before the later deltas arrive.
        def settled_view(collector: LineCollector) -> dict | None:
            payload = None
            for event in collector.snapshot()[1]:
                if event.get("kind") not in {"snapshot", "delta"}:
                    continue
                view = follow_view_payload(event)
                tools = view.get("tools") or []
                if any(tool.get("toolCallId") == "call_7" for tool in tools if isinstance(tool, dict)):
                    payload = view
            if payload is not None and payload.get("pending_permissions"):
                return payload
            return None

        self.assertTrue(left.wait_tool("call_7", 8), left.snapshot()[1])
        self.assertTrue(right.wait_tool("call_7", 8), right.snapshot()[1])
        for collector in (left, right):
            payload = wait_for(lambda: settled_view(collector), 8)
            self.assertIsNotNone(payload, collector.snapshot()[1])
            assert payload is not None
            self.assertEqual(payload.get("schema"), "kaola-acp-view/1", payload)
            assert_shape(self, self.sample, payload, "follow.view")

    def test_follow_fd_prompt_permit_is_error_without_agent_stdin(self) -> None:
        session, repo, started = self.start("grok", scenario="watch_projection")
        self.run_cli(
            "grok", "send", "--text", "Fix the login redirect loop.", "--no-wait",
            session=session, repo=repo, scenario="watch_projection",
        )
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "watch_projection_emitted"
                    for event in self.read_mock_log()
                ),
                8,
            ),
        )
        path = self.holder_sock("grok", session, repo)
        self.assertTrue(path.exists(), path)
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(8)
        connection.connect(str(path))
        try:
            connection.sendall(b'{"op":"follow","params":{}}\n')
            first = _recv_json_line(connection)
            self.assertEqual(first.get("kind"), "snapshot", first)
            before = self.inbound_trace()
            for op in WRITE_OPS:
                connection.sendall(
                    json.dumps({"op": op, "params": {"text": "sneak", "option": "allow_once"}}).encode("utf-8")
                    + b"\n"
                )
                reply = _recv_json_line(connection)
                self.assertEqual(reply.get("kind"), "error", f"{op} on follow FD: {reply}")
            time.sleep(0.4)
            after = self.inbound_trace()
            self.assertEqual(
                after, before,
                "follow FD writes must not add ACP frames on agent stdin",
            )
        finally:
            connection.close()
        self.assertTrue(pid_alive(int(started["holder_pid"])))

    def test_third_socket_permit_still_works_with_followers(self) -> None:
        session, repo, _ = self.start("grok", scenario="watch_projection")
        _left_proc, left = self.spawn_follow("grok", session, repo)
        _right_proc, right = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(left)
        self.wait_snapshot(right)
        self.run_cli(
            "grok", "send", "--text", "Fix the login redirect loop.", "--no-wait",
            session=session, repo=repo, scenario="watch_projection",
        )
        self.assertTrue(left.wait_tool("call_7", 8))
        view = wait_for(
            lambda: (
                payload
                if (payload := self.run_view("grok", session, repo, check=False)).get("pending_permissions")
                else None
            ),
            8,
        )
        self.assertTrue(view and view.get("pending_permissions"), view)
        pending = view["pending_permissions"][0]
        request_id = pending["request_id"]
        option = pending["options"][0]["optionId"]
        before = [
            event for event in self.read_mock_log()
            if event.get("event") == "outbound_response"
        ]
        permitted = self.run_cli(
            "grok", "permit",
            "--request-id", str(request_id), "--option", str(option),
            session=session, repo=repo, scenario="watch_projection",
        )
        self.assertIsNone(permitted.get("error"), permitted)
        self.assertIn("permitted", permitted)
        self.assertTrue(
            wait_for(
                lambda: len([
                    event for event in self.read_mock_log()
                    if event.get("event") == "outbound_response"
                ]) > len(before),
                5,
            ),
            "third-socket permit never reached the mock agent",
        )

    def test_slow_follower_dropped_without_pausing_agent_stdio(self) -> None:
        session, repo, _ = self.start("grok", scenario="follow_flood")
        _fast_proc, fast = self.spawn_follow("grok", session, repo)
        _slow_proc, slow = self.spawn_follow(
            "grok", session, repo, pause_after_kinds=1,
        )
        self.wait_snapshot(fast)
        self.wait_snapshot(slow)
        self.assertTrue(slow.paused.wait(timeout=5), "slow follower never paused after snapshot")
        os.kill(slow.proc.pid, signal.SIGSTOP)
        self.run_cli(
            "grok", "send", "--text", "flood", "--no-wait",
            session=session, repo=repo, scenario="follow_flood",
        )
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "follow_flood_emitted"
                    for event in self.read_mock_log()
                ),
                15,
            ),
            "agent stdio paused before the flood finished",
        )
        self.assertTrue(fast.wait_tool("call_flood", 8), fast.snapshot()[1])
        os.kill(slow.proc.pid, signal.SIGCONT)
        slow.unpause()
        dropped = slow.wait_error_code("follow-dropped", 8)
        self.assertIsNotNone(dropped, slow.snapshot()[1])
        self.assertTrue(
            wait_for(lambda: slow.proc.poll() is not None or slow.closed.is_set(), 8),
            "slow follow path must disconnect after follow-dropped",
        )
        self.assertIsNone(
            fast.wait_error_code("follow-dropped", 0.4),
            "follow-dropped must not disconnect the other follower",
        )
        view = self.run_view("grok", session, repo)
        ids = {
            tool.get("toolCallId")
            for tool in view.get("tools") or []
            if isinstance(tool, dict)
        }
        self.assertIn("call_flood", ids, view)
        self.assertEqual(view.get("schema"), "kaola-acp-view/1")
        self.assertIsInstance(view, dict)
        self.assertGreater(FOLLOW_QUEUE_CAP, 0)

    def test_killing_follow_cli_leaves_holder_and_agent(self) -> None:
        session, repo, started = self.start("grok")
        holder_pid = int(started["holder_pid"])
        proc, collector = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(collector)
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=5)
        self.assertTrue(pid_alive(holder_pid), "killing follow stopped the holder")
        listed = self.run_list()
        rows = listed.get("rows") or []
        self.assertTrue(
            any(row.get("session") == session and row.get("holder_pid") == holder_pid for row in rows),
            listed,
        )
        view = self.run_view("grok", session, repo)
        self.assertEqual(view.get("schema"), "kaola-acp-view/1")
        self.assertNotIn("error", view)
        record = self.read_record("grok", session, repo)
        agent_pid = record.get("agent_pid")
        self.assertIsInstance(agent_pid, int)
        self.assertTrue(pid_alive(int(agent_pid)), "killing follow stopped the agent")

    def test_process_exited_emits_follow_eof(self) -> None:
        session, repo, started = self.start("grok")
        _proc, collector = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(collector)
        record = self.read_record("grok", session, repo)
        agent_pid = record.get("agent_pid")
        self.assertIsInstance(agent_pid, int)
        os.kill(int(agent_pid), signal.SIGKILL)
        wait_for(lambda: not pid_alive(int(agent_pid)), 5)
        eof = collector.wait_kind("eof", 8)
        self.assertIsNotNone(eof, collector.snapshot()[1])
        self.assertEqual(eof.get("kind"), "eof")
        self.assertTrue(pid_alive(int(started["holder_pid"])))
        view = self.run_view("grok", session, repo, check=False)
        self.assertEqual(view.get("schema"), "kaola-acp-view/1")
        # eof ends the stream: nothing follows it and the CLI exits on its own.
        self.assertTrue(wait_for(lambda: _proc.poll() is not None, 8), "follow CLI must exit after eof")
        self.assertEqual(_proc.returncode, 0)
        _, events = collector.snapshot()
        self.assertEqual(events[-1].get("kind"), "eof", events[-1])
        # A follower that attaches after the agent exited gets snapshot then eof.
        late_proc, late = self.spawn_follow("grok", session, repo)
        self.assertIsNotNone(late.wait_kind("snapshot", 8), late.snapshot()[1])
        self.assertIsNotNone(late.wait_kind("eof", 8), late.snapshot()[1])
        self.assertTrue(wait_for(lambda: late_proc.poll() is not None, 8), "late follow CLI must exit after eof")

    def test_holder_lost_emits_follow_error_line(self) -> None:
        session, repo, started = self.start("grok")
        _proc, collector = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(collector)
        holder_pid = int(started["holder_pid"])
        os.kill(holder_pid, signal.SIGKILL)
        wait_for(lambda: not pid_alive(holder_pid), 5)
        error = collector.wait_error_code("holder-lost", 8)
        self.assertIsNotNone(error, collector.snapshot()[1])
        self.assertEqual(error.get("kind"), "error")
        self.assertEqual(follow_error_code(error), "holder-lost")

    def test_format_text_joins_titles_and_is_not_ndjson_only(self) -> None:
        session, repo, _ = self.start("grok", scenario="watch_projection")
        _proc, collector = self.spawn_follow(
            "grok", session, repo, extra=["--format", "text"],
        )
        self.assertTrue(
            wait_for(lambda: collector.proc.poll() is None or collector.snapshot()[0], 4),
            collector.stderr_text,
        )
        self.run_cli(
            "grok", "send", "--text", "Fix the login redirect loop.", "--no-wait",
            session=session, repo=repo, scenario="watch_projection",
        )
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "watch_projection_emitted"
                    for event in self.read_mock_log()
                ),
                8,
            ),
        )
        self.assertTrue(
            wait_for(
                lambda: (
                    "I'll start by" in "".join(collector.snapshot()[0])
                    or "Edit src/auth/middleware.ts" in "".join(collector.snapshot()[0])
                    or "auth middleware" in "".join(collector.snapshot()[0])
                ),
                8,
            ),
            collector.snapshot()[0],
        )
        raw, events = collector.snapshot()
        text = "".join(raw)
        ndjson_only = bool(raw) and all(
            line.strip() and _is_follow_ndjson(line) for line in raw if line.strip()
        )
        self.assertFalse(ndjson_only, "follow --format text must not be NDJSON-only")
        self.assertNotRegex(text, r"\x1b\]|\x1bP", "text format is not a second TUI engine")
        # Every delta carries the whole projection; text mode prints each item once.
        self.assertEqual(text.count("Fix the login redirect loop."), 1, text)
        self.assertEqual(text.count("I'll start by"), 1, text)
        self.assertEqual(text.count("Edit src/auth/middleware.ts"), 1, text)

    def test_tool_call_emits_delta_without_permission(self) -> None:
        session, repo, _ = self.start("grok", scenario="tool_call_only")
        _proc, collector = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(collector)
        self.run_cli(
            "grok", "send", "--text", "solo tool", "--no-wait",
            session=session, repo=repo, scenario="tool_call_only",
        )
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "tool_call_only_emitted"
                    for event in self.read_mock_log()
                ),
                8,
            ),
            "mock never emitted tool_call_only",
        )
        self.assertTrue(collector.wait_tool("call_solo", 8), collector.snapshot()[1])
        _, events = collector.snapshot()
        stream = [event for event in events if event.get("kind") in {"snapshot", "delta"}]
        self.assertTrue(
            any(
                any(
                    tool.get("toolCallId") == "call_solo"
                    for tool in (follow_view_payload(event).get("tools") or [])
                    if isinstance(tool, dict)
                )
                for event in stream
            ),
            events,
        )

    def test_view_one_object_and_l0_keys_stay_while_follow_attached(self) -> None:
        session, repo, _ = self.start("grok")
        _proc, collector = self.spawn_follow("grok", session, repo)
        self.wait_snapshot(collector)
        view = self.run_view("grok", session, repo)
        self.assertEqual(view.get("schema"), "kaola-acp-view/1")
        self.assertIsInstance(view, dict)
        self.assertNotIn("kind", view)
        receipt = self.run_cli(
            "grok", "send", "--text", "hello mock", session=session, repo=repo,
        )
        self.assertEqual(receipt.get("schema_version"), 3)
        forbidden = L0_FORBIDDEN & set(receipt)
        self.assertFalse(forbidden, f"L0 grew human keys {sorted(forbidden)}")
        self.assertIsInstance(receipt.get("thinking_chars"), int)
        self.assertNotIn("thinking_text", receipt)


def _is_follow_ndjson(line: str) -> bool:
    try:
        parsed = json.loads(line)
    except ValueError:
        return False
    return isinstance(parsed, dict) and parsed.get("kind") in FOLLOW_KINDS


def _recv_json_line(connection: socket.socket) -> dict:
    buffer = bytearray()
    while True:
        data = connection.recv(65536)
        if not data:
            break
        buffer.extend(data)
        if b"\n" in buffer:
            line, _, _unused = buffer.partition(b"\n")
            return json.loads(line.decode("utf-8"))
    if buffer:
        return json.loads(buffer.decode("utf-8"))
    return {}


if __name__ == "__main__":
    unittest.main()
