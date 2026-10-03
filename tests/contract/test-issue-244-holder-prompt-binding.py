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
import os
from unittest.mock import patch
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

    def test_owning_host_default_pins_admission_to_the_read_worker_holder(self) -> None:
        captured = {}
        def capture(args, repo, directory, op, params, timeout):
            captured.update(params)
            return {"outcome": "in_progress"}
        argv = ["kaola-acp.py", "zcode", "send", "--repo", str(PROJECT),
                "--session", "zcode-KPR-i246-bind", "--text", "look"]
        with patch.object(sys, "argv", argv), patch.object(
                acp_module, "resolve_send_wait",
                return_value=({"wait": False, "source": "owning-host-default"}, "worker-exact")), patch.object(
                acp_module, "op_or_holder_lost", side_effect=capture), redirect_stdout(io.StringIO()):
            self.assertEqual(acp_module.main(), 0)
        self.assertIs(captured["wait"], False)
        self.assertEqual(captured["expected_holder_instance_id"], "worker-exact")

    def test_wait_default_requires_all_existing_identity_and_binding_facts(self) -> None:
        root = Path(self._tmp.name)
        worker_dir = root / "worker"
        sock = root / "holder.sock"
        sock.touch()
        caller = {"platform": "zcode", "session": "zcode-KPR-orchestrator-main",
                  "repo": str(PROJECT), "holder_instance_id": "host-exact"}
        host = {**caller, "holder_pid": os.getpid(), "agent_alive": True, "session_role": "host"}
        binding = {k: caller[k] for k in ("platform", "session", "repo")}
        binding["socket"] = str(sock)
        worker = {"platform": "zcode", "session": "zcode-KPR-i246-bind", "repo": str(PROJECT),
                  "holder_instance_id": "worker-exact", "holder_pid": os.getpid(),
                  "dispatcher": caller, "heartbeat_host": binding}
        args = argparse.Namespace(wait=None, record_root=str(root),
                                  platform="zcode", session=worker["session"])
        legacy = {k: v for k, v in host.items() if k != "session_role"}
        cases = [(host, worker, False),
                 (legacy, worker, False),
                 ({**legacy, "session_role": None}, worker, False),
                 ({**host, "session_role": "worker"}, worker, True),
                 ({**host, "session_role": "guru"}, worker, True),
                 ({**legacy, "holder_instance_id": "replacement"}, worker, True),
                 ({**legacy, "session": "zcode-KPR-orchestrator-other"}, worker, True),
                 ({**legacy, "platform": "grok"}, worker, True),
                 ({**legacy, "repo": "/foreign"}, worker, True),
                 ({**legacy, "holder_instance_id": None}, worker, True),
                 ({**legacy, "holder_pid": None}, worker, True),
                 ({**legacy, "agent_alive": False}, worker, True),
                 ({**host, "agent_alive": False}, worker, True),
                 ({**host, "holder_pid": None}, worker, True),
                 ({**host, "holder_instance_id": "replacement"}, worker, True),
                 ({**host, "repo": "/foreign"}, worker, True),
                 ({}, worker, True),
                 (["unusable host record"], worker, True),
                 (host, ["unusable worker record"], True),
                 (host, {**worker, "repo": "/foreign"}, True),
                 (host, {**worker, "dispatcher": None}, True),
                 (host, {**worker, "heartbeat_host": None}, True),
                 (host, {**worker, "heartbeat_host": {**binding, "socket": "/wrong"}}, True),
                 (host, {**worker, "holder_instance_id": None}, True),
                 (host, {**worker, "holder_pid": None}, True)]
        for host_fact, worker_fact, expected_wait in cases:
            with self.subTest(host=host_fact, worker=worker_fact), patch.dict(
                    os.environ, {acp_module.DISPATCHER_ENV: json.dumps(caller)}), patch.object(
                    acp_module, "read_record", side_effect=lambda path:
                    worker_fact if path == worker_dir else host_fact), patch.object(
                    acp_module, "sock_path_for_directory", return_value=sock), patch.object(
                    acp_module, "socket_request", side_effect=AssertionError("no probe allowed")):
                selection, holder_id = acp_module.resolve_send_wait(args, str(PROJECT), worker_dir)
            self.assertIs(selection["wait"], expected_wait)
            self.assertEqual(holder_id, None if expected_wait else "worker-exact")
            if expected_wait:
                self.assertTrue(selection.get("detail"))

        # All exact ownership facts match; vague names, worker-marked names,
        # and a supplied host_class bool still cannot invent the legacy role.
        for session in ("zcode-KPR-orch-main", "zcode-KPR-i246-orchestrator-main",
                        "grok-KPR-orchestrator-main", "zcode-KPR-orchestrator-"):
            named_caller = {**caller, "session": session}
            named_host = {**legacy, "session": session, "host_class": True}
            named_worker = {**worker, "dispatcher": named_caller,
                            "heartbeat_host": {**binding, "session": session}}
            with self.subTest(session=session), patch.dict(
                    os.environ, {acp_module.DISPATCHER_ENV: json.dumps(named_caller)}), patch.object(
                    acp_module, "read_record", side_effect=lambda path:
                    named_worker if path == worker_dir else named_host), patch.object(
                    acp_module, "sock_path_for_directory", return_value=sock):
                selection, holder_id = acp_module.resolve_send_wait(args, str(PROJECT), worker_dir)
            self.assertIs(selection["wait"], True)
            self.assertEqual(selection["source"], "standalone-default")
            self.assertTrue(selection.get("detail"))
            self.assertIsNone(holder_id)

    def test_explicit_wait_flags_do_not_read_identity_records(self) -> None:
        for wait in (True, False):
            with self.subTest(wait=wait), patch.object(
                    acp_module, "dispatcher_identity", side_effect=AssertionError("no identity needed")), patch.object(
                    acp_module, "read_record", side_effect=AssertionError("no records needed")):
                selection, holder_id = acp_module.resolve_send_wait(
                    argparse.Namespace(wait=wait), str(PROJECT), Path(self._tmp.name))
            self.assertEqual(selection, {"wait": wait, "source": "explicit"})
            self.assertIsNone(holder_id)

    def test_rendered_worker_scripts_are_the_candidate_bytes(self) -> None:
        for name in ("kaola-acp-holder.py", "kaola-acp.py"):
            source = (PROJECT / "scripts" / name).read_bytes()
            rendered = (PROJECT / "skills" / "zcode-kaola-project-runner" / "scripts" / name).read_bytes()
            self.assertEqual(rendered, source)


if __name__ == "__main__":
    unittest.main()
