#!/usr/bin/env python3
"""Issue #64: the ordinary ACP observe/status receipt budget is state-sized.

A real platform's session state — Devin's ~70.6 KB ``session_meta`` beside the
~142.5 KB stored ``record`` — exceeded the old capture-sized bound, so
``bound_state_receipt`` replaced the whole ``session_meta`` with
``{omitted, bytes, sha256}`` and consumers could never read
``session_meta.configOptions`` ``currentValue`` (the configured model). The
state path now has its own larger ``state_receipt_bytes`` budget: realistic
meta and record sizes stay whole — the model is readable from ordinary
observe/status receipts — while a structure over the limit is still summarised
exactly as before. Capture receipts and the PTY bound keep the unchanged
``capture_receipt_bytes``; ``--full`` and credential hygiene are untouched.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
ACP_CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK_ACP_AGENT = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
BUDGETS = json.loads((PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8"))
MODEL = "swe-2-max"


def load_cli_module() -> Any:
    spec = importlib.util.spec_from_file_location("kaola_acp_issue64", ACP_CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def options_list(min_bytes: int) -> list[dict[str, Any]]:
    """A realistic ACP ``configOptions`` list: a model option carrying a small
    ``currentValue`` beside a large option catalog, padded deterministically
    until the serialized list passes ``min_bytes``."""
    options: list[dict[str, Any]] = [
        {"id": "mode", "name": "Mode", "category": "mode", "type": "select",
         "currentValue": "bypass",
         "options": [{"value": "read-only", "name": "Read only"},
                     {"value": "bypass", "name": "Bypass"}]},
        {"id": "model", "name": "Model", "category": "model", "type": "select",
         "currentValue": MODEL, "options": []},
    ]
    index = 0
    while len(json.dumps(options, ensure_ascii=False, sort_keys=True).encode("utf-8")) < min_bytes:
        options[1]["options"].append(
            {"value": f"catalog-{index:05d}", "name": f"Catalog {index:05d}",
             "description": "d" * 160})
        index += 1
    return options


def state_receipt(session_meta: dict[str, Any], initial_config_options: list[Any],
                  record: dict[str, Any] | None = None) -> dict[str, Any]:
    """The observe/status receipt shape: base facts plus holder state fields."""
    receipt: dict[str, Any] = {
        "schema_version": 3, "platform": "devin", "session": "issue-64", "repo": "/repo",
        "transport": {"selected": "acp", "default": "acp", "alternatives": ["pty"],
                      "reason": "manifest-default"},
        "git": {"branch": "main", "dirty": False},
        "state": "ready", "activity_hint": "idle", "holder_pid": 4242,
        "holder_instance_id": "instance-hex", "agent_pid": 4243, "agent_pgid": 4243,
        "agent_alive": True, "acp_session_id": "native-1", "protocol_version": 1,
        "event_cursor": 7, "mutation_status": "completed", "turn_active": False,
        "turn_outcome": None, "stop_reason": None, "context_usage": None,
        "session_meta": session_meta,
        "initial_config_options": initial_config_options,
        "capabilities": {"prompt": True, "set_config_option": True},
        "agent_info": {"name": "Mock", "version": "1.0"},
        "pending_permissions": [],
    }
    if record is not None:
        receipt["record"] = record
    return receipt


def record_of(session_meta: dict[str, Any], initial_config_options: list[Any]) -> dict[str, Any]:
    """The holder's on-disk record mirrors the session structures."""
    return {
        "platform": "devin", "session": "issue-64", "repo": "/repo", "state": "ready",
        "holder_pid": 4242, "holder_instance_id": "instance-hex", "agent_pid": 4243,
        "agent_pgid": 4243, "agent_alive": True, "acp_session_id": "native-1",
        "protocol_version": 1, "session_meta": session_meta,
        "initial_config_options": initial_config_options,
        "capabilities": {"prompt": True}, "agent_info": {"name": "Mock"},
        "pending_permissions": [], "last_prompt": {}, "event_cursor": 7,
        "fatal_error": None, "created_at": 1.0, "updated_at": 2.0,
    }


def emitted_line_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")) + 1


def stub_of(value: Any) -> dict[str, Any]:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"omitted": True, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class StateBudgetIsDeclared(unittest.TestCase):
    def test_state_budget_is_its_own_larger_limit_and_capture_is_unchanged(self) -> None:
        module = load_cli_module()
        self.assertEqual(module.STATE_RECEIPT_BYTES, BUDGETS["state_receipt_bytes"])
        self.assertEqual(module.STATE_RECEIPT_BYTES, 262144)
        self.assertEqual(module.CAPTURE_RECEIPT_BYTES, BUDGETS["capture_receipt_bytes"])
        self.assertEqual(module.CAPTURE_RECEIPT_BYTES, 65536)
        self.assertGreater(module.STATE_RECEIPT_BYTES, module.CAPTURE_RECEIPT_BYTES)


class RealisticStatePassesWhole(unittest.TestCase):
    def test_seventy_kib_session_meta_with_the_record_stays_whole_model_readable(self) -> None:
        module = load_cli_module()
        options = options_list(70_000)
        meta = {"sessionId": "native-1", "configOptions": options}
        meta_bytes = len(json.dumps(meta, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        self.assertGreater(meta_bytes, BUDGETS["capture_receipt_bytes"])
        self.assertLess(meta_bytes, 80_000)
        record = record_of(meta, options)
        receipt = state_receipt(meta, options, record)
        self.assertGreater(emitted_line_size(receipt), BUDGETS["state_receipt_bytes"],
                           "the unbounded receipt busts the state budget")
        bounded = module.bound_state_receipt(copy.deepcopy(receipt))
        self.assertLessEqual(emitted_line_size(bounded), BUDGETS["state_receipt_bytes"])
        self.assertEqual(bounded["session_meta"], meta, "session_meta passes through whole")
        model = next(o for o in bounded["session_meta"]["configOptions"] if o.get("id") == "model")
        self.assertEqual(model["currentValue"], MODEL)
        self.assertEqual(bounded["record"], stub_of(record))
        self.assertEqual(set(bounded["truncated"]["fields"]), {"record"})
        for scalar in ("state", "activity_hint", "holder_pid", "event_cursor",
                       "mutation_status", "acp_session_id"):
            self.assertIn(scalar, bounded)

    def test_hundred_forty_kib_session_meta_stays_whole(self) -> None:
        module = load_cli_module()
        options = options_list(140_000)
        meta = {"sessionId": "native-1", "configOptions": options}
        meta_bytes = len(json.dumps(meta, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        self.assertGreater(meta_bytes, 130_000)
        self.assertLess(meta_bytes, 150_000)
        record = record_of(meta, options)
        receipt = state_receipt(meta, options, record)
        self.assertGreater(emitted_line_size(receipt), BUDGETS["state_receipt_bytes"])
        bounded = module.bound_state_receipt(copy.deepcopy(receipt))
        self.assertLessEqual(emitted_line_size(bounded), BUDGETS["state_receipt_bytes"])
        self.assertEqual(bounded["session_meta"], meta, "session_meta passes through whole")
        model = next(o for o in bounded["session_meta"]["configOptions"] if o.get("id") == "model")
        self.assertEqual(model["currentValue"], MODEL)
        self.assertEqual(set(bounded["truncated"]["fields"]), {"record", "initial_config_options"})
        self.assertEqual(bounded["initial_config_options"], stub_of(options))

    def test_over_state_budget_session_meta_is_still_omitted_attested(self) -> None:
        module = load_cli_module()
        options = options_list(300_000)
        meta = {"sessionId": "native-1", "configOptions": options}
        self.assertGreater(emitted_line_size(meta), BUDGETS["state_receipt_bytes"])
        receipt = state_receipt(meta, [])
        bounded = module.bound_state_receipt(copy.deepcopy(receipt))
        self.assertLessEqual(emitted_line_size(bounded), BUDGETS["state_receipt_bytes"])
        self.assertEqual(bounded["session_meta"], stub_of(meta))
        self.assertNotIn("configOptions", bounded["session_meta"],
                         "an over-budget field keeps nothing readable")
        summary = bounded["truncated"]["fields"]["session_meta"]
        self.assertEqual(summary["kind"], "object")
        self.assertEqual(summary["sha256"], stub_of(meta)["sha256"])
        self.assertEqual(summary["bytes"], stub_of(meta)["bytes"])

    def test_small_state_passes_through_unchanged(self) -> None:
        module = load_cli_module()
        options = [{"id": "model", "currentValue": MODEL,
                    "options": [{"value": MODEL, "name": "SWE"}]}]
        meta = {"sessionId": "native-1", "configOptions": options}
        receipt = state_receipt(meta, options)
        bounded = module.bound_state_receipt(copy.deepcopy(receipt))
        self.assertEqual(bounded, receipt)
        self.assertNotIn("truncated", bounded)


class ObserveExposesTheModelThroughTheRealCli(unittest.TestCase):
    """End-to-end on the issue's shape: a Devin session whose session_meta is
    ~70 KB with the model currentValue inside, observed through the real CLI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i64-live-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.session = f"i64-{os.getpid()}"
        cls.options = options_list(70_000)
        cls.started = False
        cls.cli("start")
        cls.started = True

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.started:
            cls.cli("stop", "--force", check=False)
        cls._tmp.cleanup()

    @classmethod
    def cli(cls, command: str, *args: str, check: bool = True) -> dict:
        env = dict(os.environ, KAOLA_ACP_RECORD_ROOT=str(cls.root / "records"),
                   MOCK_ACP_LOG=str(cls.root / "mock.jsonl"),
                   MOCK_ACP_CONFIG=json.dumps(
                       {"new": cls.options, "set_result": {"configOptions": cls.options}}))
        argv = [sys.executable, str(ACP_CLI), "devin", command, "--repo", str(cls.repo),
                "--session", cls.session,
                "--command", f"{sys.executable} {MOCK_ACP_AGENT} --scenario tool_call_only",
                *args]
        completed = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
        if check and completed.returncode != 0:
            raise AssertionError(f"{command} failed: {completed.stderr}\n{completed.stdout}")
        return json.loads(completed.stdout) if completed.stdout.strip() else {}

    def test_observe_and_status_return_whole_session_meta_with_the_configured_model(self) -> None:
        for command in ("observe", "status"):
            receipt = self.cli(command)
            self.assertLessEqual(emitted_line_size(receipt), BUDGETS["state_receipt_bytes"], command)
            self.assertGreater(emitted_line_size(receipt), BUDGETS["capture_receipt_bytes"],
                               f"{command}: the bounded receipt legally exceeds the old capture bound")
            fields = receipt["truncated"]["fields"]
            self.assertEqual(set(fields), {"record"}, command)
            self.assertEqual(receipt["record"]["omitted"], True, command)
            self.assertEqual(receipt["session_meta"]["configOptions"], self.options, command)
            model = next(o for o in receipt["session_meta"]["configOptions"] if o.get("id") == "model")
            self.assertEqual(model["currentValue"], MODEL, command)


if __name__ == "__main__":
    unittest.main()
