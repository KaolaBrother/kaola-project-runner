#!/usr/bin/env python3
"""Issue #338: a plain dsh/opencode default start applies effort max.

``dsh/default`` and ``opencode/default`` declare ``default_model_effort``
``max``. A plain ``start`` (no ``--effort``, tier ``default``) therefore
sends the exact option the runtime accepts — dsh ``reasoning_effort=max``,
opencode ``effort=max`` — and the receipt shows
``config_application.effort`` applied with that ``config_id`` and value
``max``, plus ``effective_selection.effective_effort`` ``max``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).resolve().parent
for _name in ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD"):
    os.environ.pop(_name, None)

_spec = importlib.util.spec_from_file_location(
    "acp_contract_issue_338", CONTRACT / "test-acp-contract.py")
_ACP_CONTRACT = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_ACP_CONTRACT)

DSH_ROUTE = '["opencode-go","deepseek-v4.1-flash"]'
OPENCODE_MODEL = "opencode-go/deepseek-v4.1-flash"


def option(config_id: str, values: list[str], current: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": config_id, "name": config_id, "category": config_id, "type": "select",
        "options": [{"value": value, "name": value or "default"} for value in values],
    }
    if current is not None:
        row["currentValue"] = current
    return row


def dsh_fixture() -> dict[str, Any]:
    models = [DSH_ROUTE, '["deepseek-official","deepseek-v4-flash"]']
    # dsh reasoning_effort values on the opencode-go route (measured 2026-10-16).
    efforts = ["", "low", "high", "max"]
    return {
        "new": [option("model", models, '["deepseek-official","deepseek-v4-flash"]'),
                option("reasoning_effort", efforts, "")],
        "set_result": {"configOptions": [
            option("model", models, DSH_ROUTE),
            option("reasoning_effort", efforts, "max"),
        ]},
    }


def opencode_fixture() -> dict[str, Any]:
    models = ["opencode/big-pickle", OPENCODE_MODEL]
    # OpenCode effort values (measured 2026-10-16).
    efforts = ["low", "high", "max", "default"]
    return {
        "new": [option("model", models, "opencode/big-pickle"),
                option("effort", efforts, "default")],
        "set_result": {"configOptions": [
            option("model", models, OPENCODE_MODEL),
            option("effort", efforts, "max"),
        ]},
    }


class ManifestEffortDeclaration(unittest.TestCase):
    def test_dsh_and_opencode_declare_effort_max_and_the_catalog_row_says_so(self) -> None:
        readme = (PROJECT / "README.md").read_text(encoding="utf-8")
        for platform, config_id in (("dsh", "reasoning_effort"), ("opencode", "effort")):
            manifest = (PROJECT / "platforms" / f"{platform}.yaml").read_text(encoding="utf-8")
            self.assertIn('default_model_effort: "max"', manifest, platform)
            self.assertIn(
                f'default_model_parameters: "effort=max via ACP option {config_id}"',
                manifest, platform)
            self.assertIn(
                f"| `{platform}/default` | DeepSeek V4.1 Flash | effort=max via ACP option {config_id} |",
                readme, platform)


class PlainStartAppliesMaxEffort(_ACP_CONTRACT.AcpSessionFixture, unittest.TestCase):
    def plain_start(self, platform: str, fixture: dict[str, Any]) -> dict[str, Any]:
        receipt = self.cli(
            "start", platform=platform, timeout=60,
            extra_env={"MOCK_ACP_CONFIG": json.dumps(fixture)},
        )
        self._started = True
        self._started_platform = platform
        return receipt

    def effort_sets(self, config_id: str) -> list[Any]:
        return [
            (event.get("params") or {}).get("value")
            for event in self.read_mock_log()
            if event.get("event") == "set_config_option"
            and (event.get("params") or {}).get("configId") == config_id
        ]

    def assert_max_applied(self, receipt: dict[str, Any], config_id: str) -> None:
        self.assertEqual(receipt.get("state"), "ready", receipt)
        effort = receipt["config_application"]["effort"]
        self.assertEqual(
            (effort.get("applied"), effort.get("config_id"), effort.get("value"),
             effort.get("advertised")),
            (True, config_id, "max", True), effort)
        self.assertEqual(
            receipt["effective_selection"]["effective_effort"], "max",
            receipt["effective_selection"])
        self.assertEqual(self.effort_sets(config_id), ["max"],
                         "the exact option id and value were sent")

    def test_dsh_plain_start_applies_reasoning_effort_max(self) -> None:
        receipt = self.plain_start("dsh", dsh_fixture())
        self.assertEqual(receipt["config_application"]["model"].get("value"), DSH_ROUTE)
        self.assert_max_applied(receipt, "reasoning_effort")

    def test_opencode_plain_start_applies_effort_max(self) -> None:
        receipt = self.plain_start("opencode", opencode_fixture())
        self.assertEqual(receipt["config_application"]["model"].get("value"), OPENCODE_MODEL)
        self.assert_max_applied(receipt, "effort")


if __name__ == "__main__":
    unittest.main()
