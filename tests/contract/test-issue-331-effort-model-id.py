#!/usr/bin/env python3
"""Issue #331: an effort the accepted model ID carries is applied, not a mismatch.

antigravity advertises no effort config option: its effort is part of the model
slug (``gemini-4-argon-{low,medium,high}``). Before the fix the start receipt
recorded effort as ``applied: false`` while the requested model matched, and
dispatch failed the item with ``selection-mismatch`` although the seat started
on the right model. The suite pins:

* (a) antigravity default and xhigh starts, through the real ``kaola-acp.py``
  holder over the mock agy, dispatch without a selection mismatch;
* (b) a real model mismatch (the agent accepted a different slug) still fails
  ``selection-mismatch``;
* (c) cursor-cli, which advertises its own effort option, keeps its applied
  record and dispatch verdict unchanged;
* the continuity guard: a resume judges the model-carried effort by the model
  axis, so an unchanged model keeps the effort ``preserved``.
"""

from __future__ import annotations

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
SCRIPTS = PROJECT / "scripts"
CONTRACT = Path(__file__).resolve().parent
CLI = SCRIPTS / "kaola-acp.py"
WRAPPER = SCRIPTS / "kaola-antigravity-acp.py"
MOCK_AGY = CONTRACT / "mock-agy.py"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for _name in CALLER_ENV:
    os.environ.pop(_name, None)


def load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ACP = load(CLI, "kaola_acp_issue_331")
DISPATCH = load(SCRIPTS / "kaola-dispatch.py", "kaola_dispatch_issue_331")
_ACP_CONTRACT = load(CONTRACT / "test-acp-contract.py", "acp_contract_issue_331")


class EffortAppliedByModelId(unittest.TestCase):
    def test_accepted_slug_with_the_requested_suffix_applies_the_effort(self) -> None:
        model = {"applied": True, "value": "gemini-4-argon-medium"}
        self.assertTrue(ACP.effort_applied_by_model_id(model, "gemini-4-argon-medium", "medium"))
        self.assertTrue(ACP.effort_applied_by_model_id(
            {"applied": True, "applied_via": "argv"}, "gemini-4-argon-high", "high"))
        self.assertTrue(ACP.effort_applied_by_model_id(
            {"applied": True, "config_id": "model", "value": "claude-opus-5-5-high"},
            "claude-opus-5-5-high", "high"))

    def test_an_unapplied_model_or_a_disagreeing_suffix_proves_nothing(self) -> None:
        self.assertFalse(ACP.effort_applied_by_model_id(
            {"applied": False, "reason": "no-resolved-value"}, "gemini-4-argon-medium", "medium"))
        self.assertFalse(ACP.effort_applied_by_model_id(None, "gemini-4-argon-medium", "medium"))
        self.assertFalse(ACP.effort_applied_by_model_id(
            {"applied": True}, "gemini-4-argon-high", "medium"))
        self.assertFalse(ACP.effort_applied_by_model_id(
            {"applied": True}, "claude-opus-5-5-high", "medium"))
        self.assertFalse(ACP.effort_applied_by_model_id({"applied": True}, "auto", "medium"))
        self.assertFalse(ACP.effort_applied_by_model_id({"applied": True}, "gemini-4-argon-medium", ""))


class AntigravityEffortThroughRealHolder(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-i331-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.home = root / "home"
        self.home.mkdir()
        self.records = root / "records"
        self.log = root / "agy.jsonl"
        self.session = f"i331-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self.addCleanup(self.force_stop)

    def force_stop(self) -> None:
        try:
            self.acp("stop", "--force", timeout=30)
        except Exception:      # noqa: BLE001 - cleanup must never mask the test result
            pass

    def acp(self, command: str, *args: str, timeout: float = 90) -> dict[str, Any]:
        # Same clean environment as the antigravity contract: no ambient dispatcher or Host identity.
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home),
               "KAOLA_ACP_RECORD_ROOT": str(self.records), "KAOLA_LAUNCH_BACKEND": "direct",
               "AGY_BIN": str(MOCK_AGY), "MOCK_AGY_SCENARIO": "ok",
               "MOCK_AGY_LOG": str(self.log), "KAOLA_ANTIGRAVITY_START_WINDOW": "3"}
        result = subprocess.run(
            [sys.executable, str(CLI), "antigravity", command, "--repo", str(self.repo),
             "--session", self.session, "--command", f"{sys.executable} {WRAPPER}", *args],
            capture_output=True, text=True, timeout=timeout, env=env)
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command}: rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}")

    def dispatch_verdict(self, requested: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
        report = DISPATCH.selection_report(requested, receipt)
        return {"comparison": report["comparison"], "mismatch": DISPATCH.applied_mismatch(report),
                "fields": report["fields"]}

    def test_a_default_start_dispatches_without_a_selection_mismatch(self) -> None:
        receipt = self.acp("start")
        self.assertEqual(receipt["state"], "ready", receipt)
        effort = receipt["config_application"]["effort"]
        self.assertEqual(effort, {"applied": True, "applied_via": "model-id", "value": "medium"})
        verdict = self.dispatch_verdict(
            {"model_id": "gemini-4-argon-medium", "effort": "medium"}, receipt)
        self.assertFalse(verdict["mismatch"], verdict)
        self.assertEqual(verdict["comparison"], "match", verdict)

    def test_b_xhigh_tier_dispatches_without_a_selection_mismatch(self) -> None:
        receipt = self.acp("start", "--tier", "xhigh")
        self.assertEqual(receipt["state"], "ready", receipt)
        self.assertEqual(receipt["config_application"]["model"]["value"], "gemini-4-argon-high")
        verdict = self.dispatch_verdict(
            {"model_id": "gemini-4-argon-high", "effort": "high"}, receipt)
        self.assertFalse(verdict["mismatch"], verdict)
        self.assertEqual(verdict["comparison"], "match", verdict)

    def test_b2_opus_tier_dispatches_without_a_selection_mismatch(self) -> None:
        receipt = self.acp("start", "--tier", "opus")
        self.assertEqual(receipt["state"], "ready", receipt)
        self.assertEqual(receipt["config_application"]["model"]["value"], "claude-opus-5-5-high")
        self.assertEqual(receipt["config_application"]["effort"],
                         {"applied": True, "applied_via": "model-id", "value": "high"})
        verdict = self.dispatch_verdict(
            {"model_id": "claude-opus-5-5-high", "effort": "high"}, receipt)
        self.assertFalse(verdict["mismatch"], verdict)
        self.assertEqual(verdict["comparison"], "match", verdict)

    def test_c_a_real_model_mismatch_still_fails_selection(self) -> None:
        # The agent accepted gemini-4-argon-high; the item asked for the medium slug.
        receipt = self.acp("start", "--model", "gemini-4-argon-high")
        self.assertEqual(receipt["state"], "ready", receipt)
        self.assertEqual(receipt["config_application"]["model"]["value"], "gemini-4-argon-high")
        verdict = self.dispatch_verdict(
            {"model_id": "gemini-4-argon-medium", "effort": "medium"}, receipt)
        self.assertTrue(verdict["mismatch"], verdict)
        self.assertEqual(verdict["fields"]["model_id"]["applied"], "mismatch")


class ModelCarriedEffortContinuity(unittest.TestCase):
    """A resume judges an effort the model ID carries by the model axis (no effort readback exists)."""

    def reconcile(self, fresh_model: str) -> dict[str, Any]:
        inherited = {
            "source": "prior-holder-record",
            "config_application": {
                "model": {"applied": True, "value": "gemini-4-argon-medium"},
                "effort": {"applied": True, "applied_via": "model-id", "value": "medium"},
            },
            "effective_selection": {"effective_model": "gemini-4-argon-medium",
                                    "effective_effort": None, "effort_config_id": None},
        }
        return ACP.reconcile_selection_continuity(
            resumed=True, explicit=False, recorded_source="resume-preserved",
            recorded_model=None, recorded_effort=None,
            application={"model": {"applied": False, "reason": "no-resolved-value"},
                         "effort": {"applied": False, "reason": "no-resolved-value"}},
            fresh={"effective_model": fresh_model, "effective_effort": None, "effort_config_id": None},
            inherited=inherited,
        )

    def test_unchanged_model_keeps_the_carried_effort_preserved(self) -> None:
        continuity = self.reconcile("gemini-4-argon-medium")
        self.assertEqual(continuity["axes"]["effort"]["status"], "matches-prior-applied", continuity)
        self.assertEqual(continuity["outcome"], "matches-prior-applied", continuity)
        self.assertIs(continuity["prior_settings_preserved"], True, continuity)

    def test_a_changed_model_takes_the_carried_effort_with_it(self) -> None:
        continuity = self.reconcile("gemini-4-argon-high")
        self.assertEqual(continuity["axes"]["effort"]["status"], "differs-from-prior-applied", continuity)
        self.assertEqual(continuity["outcome"], "differs-from-prior-applied", continuity)
        self.assertIs(continuity["prior_settings_preserved"], False, continuity)


class CursorEffortOptionUnchanged(_ACP_CONTRACT.AcpSessionFixture, unittest.TestCase):
    """cursor-cli advertises its own effort option, so the model-id branch is never taken."""

    def test_cursor_effort_is_applied_through_its_option_and_dispatches_clean(self) -> None:
        receipt = self.start("cursor-cli", caps="cursor-params,strict-config", platform="cursor-cli")
        self.assertIsNone(receipt.get("error"), f"start failed: {receipt}")
        effort = receipt["config_application"]["effort"]
        self.assertIs(effort.get("applied"), True, effort)
        self.assertEqual(effort.get("config_id"), "reasoning_effort")
        self.assertNotIn("applied_via", effort)
        verdict = self.dispatch_verdict_for_cursor(receipt)
        self.assertFalse(verdict["mismatch"], verdict)
        self.assertEqual(verdict["comparison"], "match", verdict)

    def dispatch_verdict_for_cursor(self, receipt: dict[str, Any]) -> dict[str, Any]:
        report = DISPATCH.selection_report({"model_id": "grok-4.7-high", "effort": "high"}, receipt)
        return {"comparison": report["comparison"], "mismatch": DISPATCH.applied_mismatch(report),
                "fields": report["fields"]}


if __name__ == "__main__":
    unittest.main()
