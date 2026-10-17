#!/usr/bin/env python3
"""Issue #344: a start brief is that session's first verified prompt turn.

``start --stdin`` / ``start --text`` must deliver the text through the holder
prompt path and must not report ``ready`` as a dispatch until the turn has
started (``turn_request_id`` assigned and ``last_prompt.mutation_status`` at
``in_progress`` or later). A start with no brief stays seat-only. ``--no-wait``
waits for that admission and not for the turn to end.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).resolve().parent
CLI = PROJECT / "scripts" / "kaola-acp.py"
for _name in ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD"):
    os.environ.pop(_name, None)

_spec = importlib.util.spec_from_file_location(
    "acp_contract_issue_344", CONTRACT / "test-acp-contract.py")
_ACP = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_ACP)

_zspec = importlib.util.spec_from_file_location(
    "zcode_heartbeat_issue_344", CONTRACT / "test-zcode-heartbeat-contract.py")
_ZCODE = importlib.util.module_from_spec(_zspec)
assert _zspec.loader is not None
_zspec.loader.exec_module(_ZCODE)

_cspec = importlib.util.spec_from_file_location(
    "claude_runner_issue_344", CONTRACT / "test-issue-50-runner-integration.py")
_CLAUDE = importlib.util.module_from_spec(_cspec)
assert _cspec.loader is not None
_cspec.loader.exec_module(_CLAUDE)

BRIEF = "reply with only OK"
ADMITTED = {"in_progress", "accepted", "completed"}
SUITE = "test-issue-344-start-brief.py"


def fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class StartBriefNative(_ACP.AcpSessionFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.mock_log.write_text("", encoding="utf-8")

    def start_raw(self, *args: str, stdin: str | None = None, turn_ms: int = 0,
                  timeout: float = 45) -> tuple[int, dict[str, Any], float]:
        argv = [sys.executable, str(CLI), "grok", "start", "--repo", str(self.repo),
                "--session", self.session, "--launch-backend", "direct",
                "--command", self.mock_command("normal", turn_ms=turn_ms),
                *args]
        env = self.env()
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        begun = time.monotonic()
        run = subprocess.run(argv, capture_output=True, text=True, env=env,
                             input=stdin, timeout=timeout)
        elapsed = time.monotonic() - begun
        self._started = True
        try:
            receipt = json.loads(run.stdout)
        except ValueError:
            self.fail(f"start emitted no JSON\nrc={run.returncode}\n"
                      f"stdout={run.stdout!r}\nstderr={run.stderr!r}")
        return run.returncode, receipt, elapsed

    def status(self) -> dict[str, Any]:
        return self.cli("status", check=False)

    def prompt_texts(self) -> list[str]:
        return [str(event.get("text") or "")
                for event in self.read_mock_log() if event.get("event") == "prompt"]

    def records(self) -> list[Path]:
        return list(self.record_root.glob(f"grok/{self.session}/*/record.json"))

    def assert_delivered(self, code: int, receipt: dict[str, Any], text: str) -> None:
        expected = fingerprint(text)
        self.assertEqual(code, 0, receipt)
        self.assertIs(receipt.get("brief_delivered"), True, receipt)
        self.assertTrue(receipt.get("turn_request_id"), receipt)
        self.assertEqual(receipt.get("prompt_fingerprint"), expected, receipt)
        self.assertIn(receipt.get("mutation_status"), ADMITTED, receipt)
        self.assertIs(receipt.get("mutation_performed"), True, receipt)
        self.assertNotEqual(receipt.get("result"), "refused", receipt)
        state = self.status()
        self.assertEqual(state.get("turn_request_id"), receipt["turn_request_id"], state)
        last = state.get("last_prompt") or {}
        self.assertEqual(last.get("fingerprint"), expected, state)
        self.assertIn(last.get("mutation_status"), ADMITTED, state)
        self.assertIn(text, self.prompt_texts(), self.read_mock_log())

    def test_text_brief_admits_the_first_turn(self) -> None:
        code, receipt, _elapsed = self.start_raw("--no-wait", "--text", BRIEF)
        self.assert_delivered(code, receipt, BRIEF)
        self.assertEqual(receipt.get("state"), "ready", receipt)
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)

    def test_stdin_brief_is_the_turn_text(self) -> None:
        code, receipt, _elapsed = self.start_raw(
            "--no-wait", "--stdin", "--text", "not-the-brief", stdin=BRIEF)
        self.assert_delivered(code, receipt, BRIEF)
        self.assertNotIn("not-the-brief", self.prompt_texts())

    def test_wait_still_reports_the_admitted_turn(self) -> None:
        code, receipt, _elapsed = self.start_raw("--wait", "--text", BRIEF)
        self.assert_delivered(code, receipt, BRIEF)
        self.assertEqual(receipt.get("outcome"), "turn_completed", receipt)
        self.assertEqual(receipt.get("mutation_status"), "completed", receipt)

    def test_no_brief_stays_ready_without_a_turn(self) -> None:
        code, receipt, _elapsed = self.start_raw()
        self.assertEqual((code, receipt.get("result"), receipt.get("state")),
                         (0, None, "ready"), receipt)
        for key in ("brief_delivered", "prompt_fingerprint", "turn_request_id", "outcome"):
            self.assertNotIn(key, receipt, receipt)
        state = self.status()
        self.assertFalse(state.get("turn_request_id"), state)
        self.assertFalse((state.get("last_prompt") or {}).get("fingerprint"), state)
        self.assertEqual(self.prompt_texts(), [])

    def test_no_wait_verifies_admission_without_waiting_for_the_turn(self) -> None:
        code, receipt, elapsed = self.start_raw(
            "--no-wait", "--text", BRIEF, turn_ms=8000, timeout=20)
        self.assertLess(elapsed, 4.0, receipt)
        self.assert_delivered(code, receipt, BRIEF)
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        self.assertEqual(receipt.get("mutation_status"), "in_progress", receipt)

    def test_empty_brief_refuses_before_a_seat_exists(self) -> None:
        for args, stdin in ((("--stdin",), ""), (("--text", ""), None)):
            with self.subTest(args=args):
                code, receipt, _elapsed = self.start_raw(*args, stdin=stdin)
                self.assertEqual(code, 1, receipt)
                self.assertEqual(receipt.get("result"), "refused", receipt)
                self.assertEqual(receipt.get("reason"), "brief-empty", receipt)
                self.assertIs(receipt.get("brief_delivered"), False, receipt)
                self.assertNotEqual(receipt.get("state"), "ready", receipt)
                self.assertNotIn("prompt_fingerprint", receipt, receipt)
                self.assertNotIn("turn_request_id", receipt, receipt)
                self.assertEqual(self.records(), [])
                self.assertEqual(self.prompt_texts(), [])

    def test_undelivered_brief_is_not_a_ready_dispatch(self) -> None:
        code, receipt, _elapsed = self.start_raw(
            "--no-wait", "--text", BRIEF, "--expected-holder-instance-id", "not-this-holder")
        self.assertNotEqual(code, 0, receipt)
        self.assertIs(receipt.get("brief_delivered"), False, receipt)
        self.assertEqual(receipt.get("result"), "refused", receipt)
        self.assertEqual(receipt.get("reason"), "holder-instance-mismatch", receipt)
        self.assertNotEqual(receipt.get("state"), "ready", receipt)
        self.assertNotIn("prompt_fingerprint", receipt, receipt)
        self.assertEqual(self.prompt_texts(), [])
        state = self.status()
        self.assertFalse(state.get("turn_request_id"), state)


class StartBriefOtherPlatforms(unittest.TestCase):
    def test_zcode_bridge_start_brief_admits_a_turn(self) -> None:
        sandbox = _ZCODE.Sandbox("r344")
        session = f"zcode-r344-{uuid.uuid4().hex[:8]}"
        try:
            result, receipt = sandbox.invoke(
                "start", "--mode", "yolo", "--no-wait", "--text", BRIEF,
                session=session, scenario="basic", timeout=90)
            self.assertEqual(result.returncode, 0, (result.stderr or "")[-800:])
            self.assertIsInstance(receipt, dict, result.stdout)
            assert isinstance(receipt, dict)
            self.assertIs(receipt.get("brief_delivered"), True, receipt)
            self.assertTrue(receipt.get("turn_request_id"), receipt)
            self.assertEqual(receipt.get("prompt_fingerprint"), fingerprint(BRIEF), receipt)
            self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
            self.assertIn(receipt.get("mutation_status"), ADMITTED, receipt)
            sends = _ZCODE.rpc_sends(sandbox.rpcs[session])
            self.assertTrue(any(BRIEF in text for text in sends), sends)
        finally:
            sandbox.cleanup()

    def test_claude_code_adapter_start_brief_admits_a_turn(self) -> None:
        sandbox = _CLAUDE.Sandbox("r344")
        session = sandbox.session()
        try:
            argv = [sys.executable, str(_CLAUDE.CHECKOUT_CLI), "claude-code", "start",
                    "--repo", str(sandbox.repo), "--session", session,
                    "--no-wait", "--text", BRIEF]
            sandbox.sessions.append((_CLAUDE.CHECKOUT_CLI, session))
            run = subprocess.run(argv, capture_output=True, text=True, env=sandbox.env(), timeout=90)
            self.assertEqual(run.returncode, 0, (run.stderr or "")[-800:])
            receipt = json.loads(run.stdout)
            self.assertIs(receipt.get("brief_delivered"), True, receipt)
            self.assertTrue(receipt.get("turn_request_id"), receipt)
            self.assertEqual(receipt.get("prompt_fingerprint"), fingerprint(BRIEF), receipt)
            self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
            self.assertIn(receipt.get("mutation_status"), ADMITTED, receipt)
            self.assertEqual(receipt.get("state"), "ready", receipt)
        finally:
            sandbox.cleanup()


class SuiteRegistered(unittest.TestCase):
    def test_validate_sh_runs_this_suite_on_one_lane(self) -> None:
        text = (PROJECT / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertEqual(text.count(f'"{SUITE}"'), 2)
        lane_a = text.split("python_suites_a=(", 1)[1].split("\n)", 1)[0]
        lane_b = text.split("python_suites_b=(", 1)[1].split("\n)", 1)[0]
        self.assertNotIn(f'"{SUITE}"', lane_a)
        self.assertIn(f'"{SUITE}"', lane_b)


if __name__ == "__main__":
    unittest.main()
