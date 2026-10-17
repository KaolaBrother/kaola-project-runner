#!/usr/bin/env python3
"""Issue #345: dsh/commandcode is the Command Code DeepSeek V4.1 Flash tier.

A ``--tier commandcode`` start sends the compact ACP model wire value
``["commandcode","deepseek/deepseek-v4.1-flash"]`` (no space after the comma)
and ``reasoning_effort=max``. The receipt shows the model applied, the effort
option applied, and effective effort ``max``. ``dsh/default`` stays the
opencode-go route with the same effort mechanism.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).resolve().parent
for _name in ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD"):
    os.environ.pop(_name, None)

_spec = importlib.util.spec_from_file_location(
    "acp_contract_issue_345", CONTRACT / "test-acp-contract.py")
_ACP_CONTRACT = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_ACP_CONTRACT)

RUNNER_ID = "commandcode/deepseek/deepseek-v4.1-flash"
DISPLAY = "DeepSeek V4.1 Flash (Command Code)"
WIRE = '["commandcode","deepseek/deepseek-v4.1-flash"]'
DEFAULT_ID = "opencode-go/deepseek-v4.1-flash"
DEFAULT_WIRE = '["opencode-go","deepseek-v4.1-flash"]'
DEFAULT_NAME = "DeepSeek V4.1 Flash"
PARAMETERS = "effort=max via ACP option reasoning_effort"
PROFILE = (
    "Fast implementation worker for tasks with clear goals and boundaries; "
    "emphasizes autonomous progress, iterative validation, and self-repair."
)
SPACED_WIRE = '["commandcode", "deepseek/deepseek-v4.1-flash"]'


def manifest() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PROJECT / "platforms" / "dsh.yaml").read_text(encoding="utf-8").splitlines():
        match = re.match(r'^([a-z0-9_]+):\s*(".*")\s*$', line)
        if match:
            values[match.group(1)] = json.loads(match.group(2))
    return values


def adapter_flags() -> dict[str, str]:
    text = (PROJECT / "scripts" / "adapters" / "dsh.sh").read_text(encoding="utf-8")
    return {
        match.group(1): match.group(2)
        for match in re.finditer(r'^(ADAPTER_[A-Z0-9_]+)="(.*)"$', text, re.M)
    }


def option(config_id: str, values: list[str], current: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": config_id, "name": config_id, "category": config_id, "type": "select",
        "options": [{"value": value, "name": value or "default"} for value in values],
    }
    if current is not None:
        row["currentValue"] = current
    return row


def dsh_fixture(current_model: str) -> dict[str, Any]:
    models = [WIRE, DEFAULT_WIRE, '["deepseek-official","deepseek-v4-flash"]']
    efforts = ["", "low", "high", "max"]
    return {
        "new": [option("model", models, '["deepseek-official","deepseek-v4-flash"]'),
                option("reasoning_effort", efforts, "")],
        "set_result": {"configOptions": [
            option("model", models, current_model),
            option("reasoning_effort", efforts, "max"),
        ]},
    }


class CommandCodeTierDeclaration(unittest.TestCase):
    def test_commandcode_tier_wire_quota_and_unchanged_default(self) -> None:
        values = manifest()
        self.assertEqual(values["named_tiers"], "commandcode")
        self.assertEqual(values["commandcode_model_name"], DISPLAY)
        self.assertEqual(values["commandcode_model_id"], RUNNER_ID)
        self.assertEqual(values["commandcode_model_parameters"], PARAMETERS)
        self.assertEqual(values["commandcode_model_effort"], "max")
        self.assertEqual(values["commandcode_model_profile"], PROFILE)
        self.assertEqual(values["commandcode_model_class"], "Worker")
        mapping = {}
        for pair in values["acp_model_map"].split(";"):
            key, separator, value = pair.partition("=")
            if separator:
                mapping[key] = value
        self.assertEqual(mapping[RUNNER_ID], WIRE)
        self.assertNotIn(SPACED_WIRE, values["acp_model_map"])
        self.assertNotIn(", ", mapping[RUNNER_ID])
        self.assertEqual(mapping[DEFAULT_ID], DEFAULT_WIRE)
        self.assertEqual(values["default_model_name"], DEFAULT_NAME)
        self.assertEqual(values["default_model_id"], DEFAULT_ID)
        self.assertEqual(values["default_model_parameters"], PARAMETERS)
        self.assertEqual(values["default_model_effort"], "max")
        self.assertEqual(values["default_model_profile"], PROFILE)
        self.assertEqual(values["default_model_class"], "Worker")
        packages = json.loads(values["quota_packages"])
        self.assertEqual(
            [package["id"] for package in packages],
            ["opencode-go", "commandcode"],
        )
        commandcode = packages[1]
        self.assertEqual(commandcode["name"], "Command Code")
        self.assertEqual(commandcode["windows"], ["5h", "weekly", "monthly"])
        self.assertEqual(packages[0]["windows"], ["weekly", "monthly"])
        rule = json.loads(values["model_package_rule"])
        self.assertEqual(rule["kind"], "provider_prefix")
        self.assertEqual(rule["providers"]["opencode-go"], "opencode-go")
        self.assertEqual(rule["providers"]["commandcode"], "commandcode")
        self.assertEqual(rule["gaps"], ["deepseek-official"])
        summary = values["launch_summary"]
        self.assertIn(WIRE, summary)
        self.assertIn("https://api.commandcode.ai/provider/v1", summary)
        self.assertIn("COMMANDCODE_API_KEY", summary)
        self.assertIn("Runner-side display name", summary)
        flags = adapter_flags()
        self.assertEqual(flags["ADAPTER_NAMED_TIERS"], "commandcode")
        self.assertEqual(flags["ADAPTER_COMMANDCODE_MODEL_NAME"], DISPLAY)
        self.assertEqual(flags["ADAPTER_COMMANDCODE_MODEL_ID"], RUNNER_ID)
        self.assertEqual(flags["ADAPTER_COMMANDCODE_MODEL_EFFORT"], "max")
        self.assertEqual(flags["ADAPTER_DEFAULT_MODEL_ID"], DEFAULT_ID)
        self.assertEqual(flags["ADAPTER_DEFAULT_MODEL_EFFORT"], "max")


class CommandCodeStartAppliesRouteAndMaxEffort(_ACP_CONTRACT.AcpSessionFixture, unittest.TestCase):
    def start_with(self, fixture: dict[str, Any], *args: str) -> dict[str, Any]:
        # The fixture log is one file for the class. Keep this start's sets.
        self.mock_log.write_text("", encoding="utf-8")
        receipt = self.cli(
            "start", *args, platform="dsh", timeout=60,
            extra_env={"MOCK_ACP_CONFIG": json.dumps(fixture)},
        )
        self._started = True
        self._started_platform = "dsh"
        return receipt

    def option_sets(self, config_id: str) -> list[Any]:
        return [
            (event.get("params") or {}).get("value")
            for event in self.read_mock_log()
            if event.get("event") == "set_config_option"
            and (event.get("params") or {}).get("configId") == config_id
        ]

    def assert_max_effort(self, receipt: dict[str, Any]) -> None:
        self.assertEqual(receipt.get("state"), "ready", receipt)
        effort = receipt["config_application"]["effort"]
        self.assertEqual(
            (effort.get("applied"), effort.get("config_id"), effort.get("value"),
             effort.get("advertised")),
            (True, "reasoning_effort", "max", True), effort)
        self.assertEqual(receipt["effective_selection"]["effective_effort"], "max")
        self.assertEqual(self.option_sets("reasoning_effort"), ["max"])

    def test_commandcode_start_sends_compact_wire_and_effort_max(self) -> None:
        receipt = self.start_with(dsh_fixture(WIRE), "--tier", "commandcode")
        model = receipt["config_application"]["model"]
        self.assertEqual(
            (model.get("applied"), model.get("value"), model.get("requested_id")),
            (True, WIRE, RUNNER_ID), model)
        self.assertEqual(self.option_sets("model"), [WIRE])
        self.assertNotEqual(WIRE, SPACED_WIRE)
        self.assertEqual(receipt["effective_selection"]["effective_model"], WIRE)
        self.assert_max_effort(receipt)

    def test_default_start_stays_on_the_opencode_go_route(self) -> None:
        receipt = self.start_with(dsh_fixture(DEFAULT_WIRE))
        model = receipt["config_application"]["model"]
        self.assertEqual(
            (model.get("applied"), model.get("value"), model.get("requested_id")),
            (True, DEFAULT_WIRE, DEFAULT_ID), model)
        self.assertEqual(self.option_sets("model"), [DEFAULT_WIRE])
        self.assertEqual(receipt["effective_selection"]["effective_model"], DEFAULT_WIRE)
        self.assert_max_effort(receipt)


if __name__ == "__main__":
    unittest.main()
