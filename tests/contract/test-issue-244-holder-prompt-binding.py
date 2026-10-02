#!/usr/bin/env python3
"""Issue #244: the new prompt holder binding.

These call the candidate checkout's holder and kaola-acp send path. They do
not start a CLI, and they do not read an installed v0.6.18 skill root.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HOLDER_PATH = PROJECT / "scripts" / "kaola-acp-holder.py"
ACP_PATH = PROJECT / "scripts" / "kaola-acp.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


holder_module = load("kaola_acp_holder_i244", HOLDER_PATH)
acp_module = load("kaola_acp_i244", ACP_PATH)


class StubProc:
    pid = 4242


class StubAgent:
    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
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


class PromptBinding(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i244-holder-")
        root = Path(self._tmp.name)
        args = argparse.Namespace(
            record_dir=str(root / "record"), socket=str(root / "h.sock"),
            platform="zcode", session="zcode-KPR-i244-bind", repo=str(root),
            init_meta="", command="stub",
        )
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-bind"
        self.holder.state = "ready"

    def tearDown(self) -> None:
        self.agent.release_wait.set()
        for thread in threading.enumerate():
            if thread is not threading.current_thread() and thread.name.startswith("Thread-"):
                thread.join(timeout=1)
        self._tmp.cleanup()

    def test_a_wrong_expected_holder_does_not_start_a_turn(self) -> None:
        receipt = self.holder.op_prompt({
            "text": "look", "wait": False,
            "expected_holder_instance_id": "not-this-holder",
        })
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-instance-mismatch")
        self.assertEqual(receipt.get("mutation_status"), "not_started")
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertEqual(self.agent.prompts(), [])
        self.assertIs(self.holder.turn.get("active"), False)

    def test_the_matching_id_and_an_omitted_id_still_admit(self) -> None:
        matched = self.holder.op_prompt({
            "text": "look", "wait": False,
            "expected_holder_instance_id": self.holder.holder_instance_id,
        })
        self.assertEqual(matched.get("outcome"), "in_progress", matched)
        self.assertEqual(len(self.agent.prompts()), 1)
        self.holder.turn["active"] = False
        omitted = self.holder.op_prompt({"text": "again", "wait": False})
        self.assertEqual(omitted.get("outcome"), "in_progress", omitted)
        self.assertEqual(len(self.agent.prompts()), 2)

    def test_send_puts_the_flag_on_the_prompt_op(self) -> None:
        captured: dict = {}

        def capture(args, repo, directory, op, params, timeout):
            captured["op"] = op
            captured["params"] = dict(params)
            return {"outcome": "in_progress", "mutation_status": "in_progress"}

        acp_module.op_or_holder_lost = capture
        argv = [
            "kaola-acp.py", "zcode", "send",
            "--repo", str(PROJECT),
            "--session", "zcode-KPR-i244-bind",
            "--no-wait", "--text", "look",
            "--expected-holder-instance-id", "holder-live",
        ]
        previous = sys.argv
        sys.argv = argv
        try:
            with redirect_stdout(io.StringIO()) as stdout:
                code = acp_module.main()
        finally:
            sys.argv = previous
        self.assertEqual(code, 0)
        self.assertEqual(captured["op"], "prompt")
        self.assertEqual(captured["params"]["expected_holder_instance_id"], "holder-live")
        self.assertEqual(captured["params"]["text"], "look")
        receipt = json.loads(stdout.getvalue())
        self.assertEqual(receipt.get("outcome"), "in_progress")

    def test_rendered_worker_scripts_are_the_candidate_bytes(self) -> None:
        for name in ("kaola-acp-holder.py", "kaola-acp.py"):
            source = (PROJECT / "scripts" / name).read_bytes()
            rendered = (PROJECT / "skills" / "zcode-kaola-project-runner" / "scripts" / name).read_bytes()
            self.assertEqual(rendered, source)


if __name__ == "__main__":
    unittest.main()
