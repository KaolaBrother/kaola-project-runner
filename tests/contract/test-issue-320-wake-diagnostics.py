#!/usr/bin/env python3
"""Issue #320: each Delegator-wake failure mode has a route or a self-route.

One test per mode, plus the death-wake OSError that used to return None.

Unresolvable project (mode vi): no fallback receipts file. ``status --project``
refuses a missing directory, so it could not read one. The record is the
stderr line ``project-unresolved``. A holder stores that instruction on
``delegator_wake_child_stderr`` when the child started, or on
``delegator_wake_spawn_failed`` when the directory was already gone. Death
recovery still discards stderr and does not wait; the child appends the same
line to the dead holder's event log when ``KAOLA_DELEGATOR_WAKE_EVENT_LOG``
is set. That line has no EventLog cursor.

Tests pin ``KAOLA_DELEGATOR_WEBHOOK_CONFIG`` to a missing temp file. They do
not read or call a real webhook.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "kaola-acp.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
ROUTES = REPO / "scripts" / "kaola-recovery-routes.py"
VALIDATE = REPO / "scripts" / "validate.sh"
LEAK = "secret-path-should-not-leak"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def wait_for(predicate: Any, timeout: float, label: str, interval: float = 0.05) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class _Events:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.cursor = 4

    def append(self, event: dict[str, Any]) -> None:
        self.rows.append(event)


class _Chunks:
    """Bytes stream that yields fixed blocks. ``read`` reaches EOF."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.closed = False

    def read(self, count: int) -> bytes:
        block = self.payload[:count]
        self.payload = self.payload[count:]
        return block

    def close(self) -> None:
        self.closed = True


class WakeDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.routes = load_module("kaola_recovery_routes_i320", ROUTES)
        cls.holder = load_module("kaola_acp_holder_i320", HOLDER)
        cls.acp = load_module("kaola_acp_i320", CLI)

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i320-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.config = self.root / "missing-webhook.json"
        self._saved: dict[str, str | None] = {}
        for key, value in {
            "HOME": str(self.home),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "KAOLA_DELEGATOR_WEBHOOK_CONFIG": str(self.config),
            "KAOLA_LAUNCH_BACKEND": "direct",
        }.items():
            self._saved[key] = os.environ.get(key)
            os.environ[key] = value
        self._saved_log = os.environ.pop("KAOLA_DELEGATOR_WAKE_EVENT_LOG", None)

    def tearDown(self) -> None:
        for key, old in self._saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        if self._saved_log is None:
            os.environ.pop("KAOLA_DELEGATOR_WAKE_EVENT_LOG", None)
        else:
            os.environ["KAOLA_DELEGATOR_WAKE_EVENT_LOG"] = self._saved_log
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

    def make_repo(self, name: str) -> Path:
        path = Path(os.path.realpath(self.root / name))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def make_host(self, repo: Path) -> Any:
        host = self.holder.Holder.__new__(self.holder.Holder)
        host.session_role = "host"
        host.holder_instance_id = "hid-320"
        host.args = argparse.Namespace(repo=str(repo), session="grok-w320-orchestrator")
        host.events = _Events()
        return host

    def wake_payload(self, project: str) -> dict[str, Any]:
        return {
            "schema": "kaola-delegator-wake/1",
            "project": project,
            "session": "grok-w320-orchestrator",
            "holder_instance_id": "hid-320",
            "event_seq": 1,
            "state": "end_turn",
            "state_detail": "end_turn",
            "reason": "all-idle",
            "ts": "2026-10-14T00:00:00Z",
        }

    def deliver(self, payload: dict[str, Any], extra_env: dict[str, str] | None = None,
                cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(CLI), "delegator-webhook", "deliver"],
            input=json.dumps(payload), capture_output=True, text=True, env=env,
            cwd=str(cwd or self.root), timeout=30, check=False)

    def test_mode_i_spawn_failure_writes_failed_receipt(self) -> None:
        repo = self.make_repo("spawn")
        host = self.make_host(repo)
        real = self.holder.subprocess.Popen

        def boom(*_args: Any, **_kwargs: Any) -> Any:
            raise FileNotFoundError(LEAK)

        self.holder.subprocess.Popen = boom
        try:
            host._delegator_wake("end_turn", "end_turn", "all-idle")
            event = wait_for(
                lambda: next((row for row in host.events.rows
                              if row.get("kind") == "delegator_wake_spawn_failed"), None),
                30, "spawn-failed event")
        finally:
            self.holder.subprocess.Popen = real
        self.assertEqual(event["error"], "FileNotFoundError")
        self.assertEqual(event["self_route"], self.routes.WAKE_SPAWN_FAILED)
        self.assertNotIn(LEAK, json.dumps(event))
        self.assertNotIn("Exact-stop", event["self_route"])
        path = repo / ".kaola" / "delegator-webhook-receipts.json"
        self.assertTrue(path.is_file(), "spawn-failed receipt was not stored")
        rows = json.loads(path.read_text(encoding="utf-8"))["receipts"]
        self.assertEqual(len(rows), 1)
        row = rows[-1]
        self.assertEqual(row["result"], "failed")
        self.assertEqual(row["error"], "spawn-failed")
        self.assertTrue(row["final"])
        self.assertEqual(row["reason"], "all-idle")
        self.assertEqual(row["event_seq"], 4)
        self.assertEqual(row["route"], self.routes.WAKE_SPAWN_FAILED)
        self.assertNotIn("Exact-stop", row["route"])
        self.assertNotIn(LEAK, path.read_text(encoding="utf-8"))
        proc = subprocess.run(
            [sys.executable, str(CLI), "delegator-webhook", "status",
             "--project", str(repo)],
            capture_output=True, text=True, env=os.environ.copy(), timeout=30, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        status = json.loads(proc.stdout)
        last = status["last_receipt"]
        self.assertEqual(last["result"], "failed")
        self.assertEqual(last["error"], "spawn-failed")
        self.assertEqual(last["route"], self.routes.WAKE_SPAWN_FAILED)
        self.assertNotIn(LEAK, proc.stdout)

    def test_mode_ii_wake_spawn_failed_route(self) -> None:
        sentence = self.routes.WAKE_SPAWN_FAILED
        self.assertEqual(self.routes.ROUTES["spawn-failed"], ("route", sentence))
        self.assertEqual(self.routes.ROUTES["wake-spawn-failed"], ("route", sentence))
        self.assertIn("delegator-webhook test", sentence)
        self.assertIn("continue the inquiry now", sentence)
        self.assertNotIn("Exact-stop", sentence)
        restart = self.routes.ROUTES["acp-spawn-failed"][1]
        self.assertIn("Exact-stop", restart)
        self.assertNotEqual(restart, sentence)
        stamped = self.routes.stamp({"result": "failed", "error": "spawn-failed", "final": True})
        self.assertEqual(stamped["route"], sentence)
        named = self.routes.stamp({"result": "refused", "reason": "wake-spawn-failed"})
        self.assertEqual(named["route"], sentence)
        validate = VALIDATE.read_text(encoding="utf-8")
        self.assertEqual(validate.count('"test-issue-320-wake-diagnostics.py"'), 2)
        holder_src = HOLDER.read_text(encoding="utf-8")
        self.assertNotIn("kaola-recovery-routes", holder_src)
        self.assertIn("_load_recovery_routes", holder_src)

    def test_mode_iii_stamp_recurses_into_death_wake(self) -> None:
        nested = {"sent": False, "reason": "spawn-failed", "error": "FileNotFoundError"}
        parent = self.routes.stamp({"result": "ok", "delegator_death_wake": dict(nested)})
        wake = parent["delegator_death_wake"]
        self.assertEqual(wake["route"], self.routes.WAKE_SPAWN_FAILED)
        self.assertNotIn("Exact-stop", wake["route"])
        self.assertNotIn("route", parent)
        self.assertNotIn("self_route", parent)
        wrapped = self.routes.stamp({
            "result": "ok",
            "holder_lost": {
                "scan": "complete",
                "leg": "delegator-webhook status",
                "wakes": [{
                    "session": "s",
                    "holder_instance_id": "h",
                    "delegator_death_wake": dict(nested),
                }],
            },
        })
        inner = wrapped["holder_lost"]["wakes"][0]["delegator_death_wake"]
        self.assertEqual(inner["route"], self.routes.WAKE_SPAWN_FAILED)
        self.assertNotIn("route", wrapped)
        self.assertNotIn("self_route", wrapped["holder_lost"])
        sent_ok = self.routes.stamp({"sent": True, "holder_instance_id": "h", "event_seq": 1})
        self.assertEqual(set(sent_ok), {"sent", "holder_instance_id", "event_seq"})
        recovered = self.routes.stamp({
            "sent": False, "reason": "already-recovered", "event_seq": 2})
        self.assertEqual(recovered["self_route"], self.routes.ROUTES["already-recovered"][1])
        self.assertNotIn("route", recovered)
        self.assertNotIn("Exact-stop", recovered["self_route"])

    def test_mode_iv_record_root_mismatch_reason(self) -> None:
        def raise_mismatch(*_args: Any, **_kwargs: Any) -> Any:
            raise self.acp.acp_paths.RecordRootMismatch(LEAK)

        real = self.acp.acp_paths.record_paths
        self.acp.acp_paths.record_paths = raise_mismatch
        try:
            scanned = self.acp._webhook_scan_holder_lost("/tmp/kaola-i320-not-used")
        finally:
            self.acp.acp_paths.record_paths = real
        self.assertEqual(scanned["scan"], "incomplete")
        self.assertEqual(scanned["leg"], "delegator-webhook status")
        self.assertEqual(scanned["reason"], "record-root-mismatch")
        self.assertEqual(scanned["wakes"], [])
        self.assertNotIn(LEAK, json.dumps(scanned))
        stamped = self.routes.stamp({
            "schema": "kaola-delegator-webhook-status/1",
            "holder_lost": scanned,
        })
        lost = stamped["holder_lost"]
        self.assertEqual(lost["self_route"], self.routes.ROUTES["record-root-mismatch"][1])
        self.assertIn("KAOLA_ACP_RECORD_ROOT", lost["self_route"])
        self.assertNotIn("route", lost)
        self.assertNotIn("self_route", stamped)
        self.assertNotIn(LEAK, lost["self_route"])

    def test_mode_v_receipt_write_stderr_is_captured(self) -> None:
        stream = _Chunks(b"y" * 5000)
        text = self.holder._bounded_stream_text(stream, 1024)
        self.assertEqual(len(text), 1024)
        self.assertEqual(stream.payload, b"")
        self.assertTrue(stream.closed)
        long_host = self.make_host(self.make_repo("clip"))
        long_host._note_wake_child_stderr("prefix Self-route: " + ("x" * 2000))
        clipped = long_host.events.rows[0]
        self.assertEqual(clipped["kind"], "delegator_wake_child_stderr")
        self.assertLessEqual(len(clipped["text"]), 1024)
        self.assertIn("self_route", clipped)
        self.assertLessEqual(len(clipped["self_route"]), 1024)

        repo = self.make_repo("write-fail")
        kaola = repo / ".kaola"
        kaola.write_text("not a directory", encoding="utf-8")
        direct = self.deliver(self.wake_payload(str(repo)), cwd=repo)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertIn("receipt-write-failed", direct.stderr)
        self.assertIn("Self-route:", direct.stderr)
        self.assertNotIn("FileExistsError", direct.stderr)
        self.assertFalse((repo / ".kaola" / "delegator-webhook-receipts.json").exists())
        self.assertLessEqual(len(direct.stderr.strip()), 1024)

        sentinel = self.root / "holder-must-not-append.jsonl"
        os.environ["KAOLA_DELEGATOR_WAKE_EVENT_LOG"] = str(sentinel)
        host = self.make_host(repo)
        seen: dict[str, Any] = {}
        real = self.holder.subprocess.Popen

        def spy(*args: Any, **kwargs: Any) -> Any:
            seen["stderr"] = kwargs.get("stderr")
            seen["env"] = kwargs.get("env")
            return real(*args, **kwargs)

        self.holder.subprocess.Popen = spy
        try:
            host._delegator_wake("end_turn", "end_turn", "all-idle")
            event = wait_for(
                lambda: next((row for row in host.events.rows
                              if row.get("kind") == "delegator_wake_child_stderr"), None),
                30, "child stderr event")
        finally:
            self.holder.subprocess.Popen = real
            os.environ.pop("KAOLA_DELEGATOR_WAKE_EVENT_LOG", None)
        self.assertIs(seen["stderr"], subprocess.PIPE)
        self.assertNotIn("KAOLA_DELEGATOR_WAKE_EVENT_LOG", seen.get("env") or {})
        self.assertFalse(sentinel.exists())
        self.assertIn("receipt-write-failed", event["text"])
        self.assertIn("Self-route:", event["text"])
        self.assertLessEqual(len(event["text"]), 1024)
        self.assertIn("the POST may have succeeded", event["self_route"])
        self.assertNotIn("FileExistsError", event["text"])
        self.assertNotIn("Exact-stop", event["self_route"])

        quiet_repo = self.make_repo("write-ok")
        quiet = self.make_host(quiet_repo)
        quiet._delegator_wake("end_turn", "end_turn", "all-idle")
        receipt_path = quiet_repo / ".kaola" / "delegator-webhook-receipts.json"
        wait_for(lambda: receipt_path.is_file() or None, 30, "skipped receipt")
        stored = json.loads(receipt_path.read_text(encoding="utf-8"))["receipts"][-1]
        self.assertEqual(stored["result"], "skipped")
        self.assertEqual(stored["skip_reason"], "not-configured")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            self.assertEqual(quiet.events.rows, [])
            time.sleep(0.05)

    def test_mode_vi_unresolvable_project_is_an_event(self) -> None:
        # Choice: the holder event log (and the caller's stderr for a direct
        # deliver). Not a fallback receipts path. status cannot open a missing
        # project, so a receipt stored somewhere else would have no reader.
        missing = self.root / "gone"
        log = self.root / "death-events.jsonl"
        proc = self.deliver(
            self.wake_payload(str(missing)),
            extra_env={"KAOLA_DELEGATOR_WAKE_EVENT_LOG": str(log)})
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("project-unresolved", proc.stderr)
        self.assertIn("Self-route:", proc.stderr)
        self.assertIn("delegator-webhook test", proc.stderr)
        self.assertNotIn("Exact-stop", proc.stderr)
        self.assertFalse(missing.exists())
        self.assertFalse((self.root / ".kaola").exists())
        line = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(line["kind"], "delegator_wake_child_stderr")
        self.assertIn("project-unresolved", line["text"])
        self.assertIn("project directory is gone", line["self_route"])
        self.assertNotIn("cursor", line)
        invalid = self.deliver(
            {"schema": "nope"},
            extra_env={"KAOLA_DELEGATOR_WAKE_EVENT_LOG": str(self.root / "invalid.jsonl")})
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("project-unresolved", invalid.stderr)

        status = subprocess.run(
            [sys.executable, str(CLI), "delegator-webhook", "status",
             "--project", str(missing)],
            capture_output=True, text=True, env=os.environ.copy(), timeout=30, check=False)
        self.assertNotEqual(status.returncode, 0)
        self.assertIn("invalid-input", status.stdout + status.stderr)

        host = self.make_host(missing)
        host._delegator_wake("end_turn", "end_turn", "all-idle", inline=True)
        event = host.events.rows[0]
        self.assertEqual(event["kind"], "delegator_wake_spawn_failed")
        self.assertEqual(event["error"], "FileNotFoundError")
        self.assertIn("project directory is gone", event["self_route"])
        self.assertIn("delegator-webhook test", event["self_route"])
        self.assertNotIn("Exact-stop", event["self_route"])
        self.assertFalse(missing.exists())

        directory = self.make_repo("dead-record")
        alive = self.make_repo("dead-project")
        record = {
            "session_role": "host",
            "holder_instance_id": "hid-dead",
            "state": "error",
            "repo": str(alive),
            "session": "grok-w320-orchestrator",
        }
        captured: dict[str, Any] = {}

        class _Stdin:
            def write(self, data: bytes) -> int:
                captured["body"] = data
                return len(data)

            def close(self) -> None:
                return None

        class _Proc:
            def __init__(self) -> None:
                self.stdin = _Stdin()

        real = self.acp.subprocess.Popen

        def spy(*_args: Any, **kwargs: Any) -> Any:
            captured["stderr"] = kwargs.get("stderr")
            captured["env"] = kwargs.get("env")
            return _Proc()

        self.acp.subprocess.Popen = spy
        try:
            wake = self.acp.recover_host_death_wake(directory, record)
        finally:
            self.acp.subprocess.Popen = real
        self.assertTrue(wake.get("sent"), wake)
        self.assertIs(captured["stderr"], subprocess.DEVNULL)
        self.assertEqual(
            captured["env"]["KAOLA_DELEGATOR_WAKE_EVENT_LOG"],
            str(directory / "events.jsonl"))

    def test_oserror_death_wake_unrecorded(self) -> None:
        directory = self.make_repo("oserror-record")
        (directory / "delegator-death-wake.lock").mkdir()
        record = {
            "session_role": "host",
            "holder_instance_id": "hid-os",
            "state": "error",
            "repo": str(directory),
            "session": "grok-w320-orchestrator",
        }
        result = self.acp.recover_host_death_wake(directory, record)
        self.assertEqual(result, {"sent": False, "reason": "death-wake-unrecorded"})
        self.assertNotIn(LEAK, json.dumps(result))
        parent = self.routes.stamp({
            "result": "ok", "delegator_death_wake": dict(result)})
        nested = parent["delegator_death_wake"]
        self.assertEqual(nested["route"], self.routes.ROUTES["death-wake-unrecorded"][1])
        self.assertIn("delegator-webhook status", nested["route"])
        self.assertIn("continue the inquiry now", nested["route"])
        self.assertNotIn("Exact-stop", nested["route"])
        self.assertNotIn("route", parent)
        self.assertNotIn("self_route", parent)


if __name__ == "__main__":
    unittest.main()
