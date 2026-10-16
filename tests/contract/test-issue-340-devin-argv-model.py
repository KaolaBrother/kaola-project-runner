#!/usr/bin/env python3
"""Issue #340: an argv-launched Devin tier shows its argv model as effective.

``devin/default`` launches ``devin acp --model swe-2-max`` while Devin's ACP
model option advertises ``swe-2-high`` and ignores ``--model``. The start
receipt, ``status`` and ``observe`` must present ``swe-2-max`` as the
effective model with ``applied_via: argv``; the advertised currentValue stays
only as ``advertised_model`` evidence, and nothing claims verification.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
ARGV_MODEL = "swe-2-max"
ADVERTISED = "swe-2-high"


def load_acp():
    spec = importlib.util.spec_from_file_location("kaola_acp_i340", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stale_options() -> list[dict]:
    return [{"id": "model", "name": "Model", "category": "model", "type": "select",
             "currentValue": ADVERTISED,
             "options": [{"value": ADVERTISED, "name": ADVERTISED}]}]


class DevinArgvModelLive(unittest.TestCase):
    """Real kaola-acp.py over the mock agent: start, status, observe, stop."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i340-")
        root = Path(self._tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.session = f"acpt-i340-{os.getpid()}"
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(root / "records")
        env["MOCK_ACP_LOG"] = str(root / "mock-events.jsonl")
        env["MOCK_ACP_CONFIG"] = json.dumps(
            {"new": stale_options(), "set_result": {"configOptions": stale_options()}})
        self.env = env
        self.command = (f"{sys.executable} {MOCK} --scenario normal --caps strict-config"
                        f" --model {ARGV_MODEL}")
        self.started = False

    def tearDown(self) -> None:
        try:
            if self.started:
                self.cli("stop", "--force")
        finally:
            time.sleep(0.2)
            self._tmp.cleanup()

    def cli(self, command: str, *extra: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "devin", command, "--repo", str(self.repo),
             "--session", self.session, "--command", self.command, *extra],
            capture_output=True, text=True, env=self.env, timeout=60,
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command}: no JSON receipt rc={result.returncode}\n"
                      f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def assert_argv_effective(self, selection: dict, where: str) -> None:
        self.assertEqual(selection.get("effective_model"), ARGV_MODEL, where)
        self.assertEqual(selection.get("effective_model_source"), "launch-argv", where)
        self.assertEqual(selection.get("applied_via"), "argv", where)
        self.assertEqual(selection.get("advertised_model"), ADVERTISED, where)
        self.assertNotEqual(selection.get("effective_model"), ADVERTISED, where)

    def test_start_status_observe_present_the_argv_model(self) -> None:
        start = self.cli("start", "--tier", "default", "--mode", "agent")
        self.started = True
        self.assertIsNone(start.get("error"), start)
        self.assertNotEqual(start.get("result"), "refused", start)
        self.assertEqual(start["config_application"]["model"],
                         {"applied": True, "applied_via": "argv", "value": ARGV_MODEL})
        self.assert_argv_effective(start["effective_selection"], "start")
        # No verification is invented from the argv the Runner itself supplied.
        self.assertEqual(start.get("model_verified"), "unknown")
        self.assertIsNone(start.get("actual_runtime_model_id"))
        self.assertTrue(start.get("start_evidence_recorded"), start)

        for command in ("status", "observe"):
            with self.subTest(command=command):
                receipt = self.cli(command)
                self.assertIsNone(receipt.get("error"), receipt)
                selection = receipt.get("effective_selection")
                self.assertIsInstance(selection, dict, f"{command} has no effective_selection")
                self.assert_argv_effective(selection, command)
                self.assertEqual(selection.get("advertised_source"), "live-config-option")
                evidence = receipt["start_evidence"]
                self.assert_argv_effective(evidence["effective_selection"],
                                           f"{command} start_evidence")
                self.assertEqual(evidence["config_application"]["model"]["applied_via"], "argv")
                self.assertEqual(evidence.get("model_verified"), "unknown")
                # The raw agent advertisement is left as the agent sent it.
                options = receipt["session_meta"]["configOptions"]
                model_option = next(o for o in options if o.get("id") == "model")
                self.assertEqual(model_option["currentValue"], ADVERTISED)


class ArgvEffectiveSelectionUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load_acp()
        cls.manifest = {"acp_model_config_id": "model", "acp_effort_config_id": ""}

    def argv_evidence(self) -> dict:
        return {
            "config_application": {
                "model": {"applied": True, "applied_via": "argv", "value": ARGV_MODEL}},
            "effective_selection": {
                "effective_model": ARGV_MODEL, "effective_model_source": "launch-argv",
                "applied_via": "argv", "advertised_model": ADVERTISED,
                "effective_effort": None, "effort_config_id": None},
            "model_verified": "unknown",
        }

    def test_stopped_holder_falls_back_to_start_evidence(self) -> None:
        receipt = {"start_evidence": self.argv_evidence()}
        self.acp.annotate_argv_effective_selection(receipt, self.manifest)
        selection = receipt["effective_selection"]
        self.assertEqual(selection["effective_model"], ARGV_MODEL)
        self.assertEqual(selection["applied_via"], "argv")
        self.assertEqual(selection["advertised_model"], ADVERTISED)
        self.assertEqual(selection["advertised_source"], "start-evidence")
        self.assertNotIn("model_verified", receipt)

    def test_live_advertisement_stays_advertised_evidence(self) -> None:
        receipt = {"start_evidence": self.argv_evidence(),
                   "session_meta": {"configOptions": [
                       {"id": "model", "currentValue": "swe-2-low"}]}}
        self.acp.annotate_argv_effective_selection(receipt, self.manifest)
        selection = receipt["effective_selection"]
        self.assertEqual(selection["effective_model"], ARGV_MODEL)
        self.assertEqual(selection["advertised_model"], "swe-2-low")
        self.assertEqual(selection["advertised_source"], "live-config-option")

    def test_option_applied_model_is_left_alone(self) -> None:
        evidence = {"config_application": {
            "model": {"applied": True, "config_id": "model", "value": ARGV_MODEL}},
            "effective_selection": {"effective_model": ARGV_MODEL}}
        receipt = {"start_evidence": evidence,
                   "session_meta": {"configOptions": [
                       {"id": "model", "currentValue": ARGV_MODEL}]}}
        self.acp.annotate_argv_effective_selection(receipt, self.manifest)
        self.assertNotIn("effective_selection", receipt)

    def test_apply_argv_model_ignores_a_non_argv_application(self) -> None:
        effective = {"effective_model": ADVERTISED}
        self.acp.apply_argv_model(effective, {"model": {"applied": False}})
        self.assertEqual(effective, {"effective_model": ADVERTISED})


if __name__ == "__main__":
    unittest.main()
