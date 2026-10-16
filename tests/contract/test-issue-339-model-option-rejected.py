#!/usr/bin/env python3
"""Issue #339: `start` refuses when the resolved model config option is rejected.

A start whose resolved model option the agent rejects is refused and the
just-created session stopped (``model-config-option-rejected``, top-level
``error``, exit 1): a dsh seat had returned ``ready`` with
``config-option-failed -32602 unknown model option`` and silently run
another model. ``--allow-unapplied-model`` is the caller's explicit
acceptance of the agent's own selection. A rejected effort option stays a
limitation receipt, as before.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).resolve().parent
CLI = PROJECT / "scripts" / "kaola-acp.py"
for _name in ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD"):
    os.environ.pop(_name, None)

_spec = importlib.util.spec_from_file_location("acp_contract_issue_339", CONTRACT / "test-acp-contract.py")
_ACP_CONTRACT = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_ACP_CONTRACT)

DSH_ROUTE = '["opencode-go","deepseek-v4.1-flash"]'
DSH_REJECTION = {"code": -32602, "message": f"unknown model option {DSH_ROUTE}"}


def option(config_id: str, values: list[str], current: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"id": config_id, "name": config_id, "category": config_id, "type": "select",
                           "options": [{"value": value, "name": value or "default"} for value in values]}
    if current is not None:
        row["currentValue"] = current
    return row


def dsh_fixture(route_advertised: bool = True) -> dict[str, Any]:
    models = [DSH_ROUTE, '["deepseek-official","deepseek-v4-flash"]'] if route_advertised \
        else ['["deepseek-official","deepseek-v4-flash"]']
    efforts = ["", "low", "high", "max"]
    return {"new": [option("model", models, '["deepseek-official","deepseek-v4-flash"]'),
                    option("reasoning_effort", efforts, "")],
            "set_result": {"configOptions": [option("model", models, DSH_ROUTE),
                                             option("reasoning_effort", efforts, "max")]}}


class RejectedModelOptionRefuses(_ACP_CONTRACT.AcpSessionFixture, unittest.TestCase):
    def raw_start(self, platform: str, *args: str, fixture: dict[str, Any] | None = None,
                  caps: str = "") -> tuple[int, dict[str, Any]]:
        argv = [sys.executable, str(CLI), platform, "start", "--repo", str(self.repo),
                "--session", self.session, "--command", self.mock_command("normal", caps), *args]
        env = self.env()
        if fixture is not None:
            env["MOCK_ACP_CONFIG"] = json.dumps(fixture)
        run = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=60)
        self._started = True
        self._started_platform = platform
        return run.returncode, json.loads(run.stdout)

    def test_a_rejected_model_option_refuses_and_stops_the_session(self) -> None:
        fixture = {**dsh_fixture(route_advertised=False), "set_error": DSH_REJECTION}
        code, receipt = self.raw_start("dsh", fixture=fixture)
        self.assertEqual((code, receipt.get("result"), receipt.get("reason")),
                         (1, "refused", "model-config-option-rejected"), receipt)
        self.assertEqual(receipt["error"]["code"], "config-option-failed")
        self.assertEqual(receipt["error"]["detail"], DSH_REJECTION)
        self.assertIn("--allow-unapplied-model", receipt["detail"])
        self.assertIn("no other model was substituted", receipt["detail"])
        model = receipt["config_application"]["model"]
        self.assertEqual((model.get("applied"), model.get("value")), (False, DSH_ROUTE))
        self.assertEqual(receipt.get("mutation_status"), "not_started", receipt)
        self.assertIs(receipt.get("holder_reclaimed"), True, "the wrong-model session does not linger")
        self.assertIs(receipt.get("host_session_stopped"), True)
        self.assertIs(receipt.get("holder_alive"), False)

    def test_the_caller_may_explicitly_accept_the_agents_own_model(self) -> None:
        fixture = {**dsh_fixture(route_advertised=False), "set_error": DSH_REJECTION}
        code, receipt = self.raw_start("dsh", "--allow-unapplied-model", fixture=fixture)
        self.assertEqual((code, receipt.get("result"), receipt.get("state")), (0, None, "ready"), receipt)
        model = receipt["config_application"]["model"]
        self.assertEqual((model.get("applied"), model["error"]["code"]), (False, "config-option-failed"))
        sent = self.cli("send", "--text", "usable", platform="dsh")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)

    def test_a_rejected_effort_option_stays_a_limitation_receipt(self) -> None:
        code, receipt = self.raw_start("grok", caps="reject-effort")
        self.assertEqual((code, receipt.get("result"), receipt.get("state")), (0, None, "ready"), receipt)
        self.assertIs(receipt["config_application"]["model"].get("applied"), True)
        effort = receipt["config_application"]["effort"]
        self.assertEqual((effort.get("applied"), effort["error"]["code"]), (False, "config-option-failed"))


class SuiteRegistered(unittest.TestCase):
    def test_validate_sh_runs_this_suite(self) -> None:
        text = (PROJECT / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertIn('"test-issue-339-model-option-rejected.py"', text)


if __name__ == "__main__":
    unittest.main()
