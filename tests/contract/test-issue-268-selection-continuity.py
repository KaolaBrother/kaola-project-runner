#!/usr/bin/env python3
"""Issue #268: bare ACP continuation must not report a silent model/effort drift as preserved.

The live fixture traces a fresh Codex preset start, a bare continuation whose
session/load readback is low, and an explicit continuation that re-applies
flags. Classification cases that do not need a process run against
``reconcile_selection_continuity`` directly.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
CONTRACT = Path(__file__).resolve().parent
BASH = Path("/Users/ylmacstudio/.local/bin/bash")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def namespace(**overrides):
    values = {
        "platform": "codex",
        "manifest": {
            "default_model_name": "GPT-6.1 Sol",
            "default_model_id": "gpt-6.1-sol",
            "default_model_effort": "high",
            "named_tiers": "astra,luna",
            "astra_model_name": "GPT-6 Astra",
            "astra_model_id": "gpt-6-astra",
            "astra_model_effort": "high",
        },
        "model": None,
        "effort": None,
        "tier": None,
        "resume": None,
        "use_continue": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def applied(model: str | None, effort: str | None) -> dict:
    def axis(value: str | None, reason: str | None = None) -> dict:
        if value is None:
            return {"applied": False, "reason": reason or "no-resolved-value"}
        return {"applied": True, "value": value}
    return {"model": axis(model), "effort": axis(effort)}


def effective(model: str | None, effort: str | None, **extra) -> dict:
    fact = {
        "effective_model": model,
        "effective_effort": effort,
        "effort_config_id": "reasoning_effort",
    }
    fact.update(extra)
    return fact


def inherited(model: str = "gpt-6.1-sol", effort: str = "high",
              live_model: str | None = "gpt-6.1-sol",
              live_effort: str | None = "high", **effective_extra) -> dict:
    return {
        "source": "prior-holder-record",
        "config_application": applied(model, effort),
        "effective_selection": effective(live_model, live_effort, **effective_extra),
    }


class SelectionContinuityClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load(SCRIPTS / "kaola-acp.py", "kaola_acp_issue_268")

    def reconcile(self, **kwargs):
        values = {
            "resumed": True,
            "explicit": False,
            "recorded_source": "resume-preserved",
            "recorded_model": None,
            "recorded_effort": None,
            "application": applied(None, None),
            "fresh": effective("gpt-6.1-sol", "low"),
            "inherited": inherited(),
        }
        values.update(kwargs)
        return self.acp.reconcile_selection_continuity(**values)

    def assert_no_persistence_cause(self, fact: dict) -> None:
        blob = json.dumps(fact).lower()
        self.assertNotIn("does not persist", blob)
        self.assertNotIn("cli does not", blob)
        self.assertNotIn("hard-code", blob)

    def test_bare_continue_resolves_no_model_or_effort(self) -> None:
        basis = self.acp.selection_basis(namespace(use_continue=True))
        self.assertEqual(basis["source"], "resume-preserved")
        self.assertEqual(basis["candidate"], "")
        self.assertEqual(basis["effort"], "")
        explicit = self.acp.selection_basis(namespace(use_continue=True, effort="low"))
        self.assertNotEqual(explicit["source"], "resume-preserved")
        self.assertEqual(explicit["candidate"], "gpt-6.1-sol")
        self.assertEqual(explicit["effort"], "low")
        tier = self.acp.selection_basis(namespace(resume="sess-1", tier="astra"))
        self.assertEqual(tier["source"], "runner-astra")
        self.assertEqual(tier["candidate"], "gpt-6-astra")
        self.assertEqual(tier["effort"], "high")

    def test_prior_high_fresh_low_is_not_preserved(self) -> None:
        fact = self.reconcile()
        self.assertEqual(fact["outcome"], "differs-from-prior-applied")
        self.assertIs(fact["prior_settings_preserved"], False)
        self.assertEqual(fact["precedence"], "unresolved")
        self.assertEqual(fact["cause"], "unproven")
        self.assertEqual(fact["recorded_selection"]["effort"], None)
        self.assertFalse(fact["applied_configuration"]["effort"]["applied"])
        self.assertEqual(fact["applied_configuration"]["effort"]["reason"], "no-resolved-value")
        self.assertEqual(fact["fresh_effective_readback"]["effort"], "low")
        self.assertEqual(fact["prior_applied_selection"]["effort"], "high")
        self.assertIs(fact["prior_applied_selection"]["historical"], True)
        self.assertEqual(fact["axes"]["effort"]["status"], "differs-from-prior-applied")
        self.assertEqual(fact["axes"]["model"]["status"], "matches-prior-applied")
        self.assertIn("--effort", fact["recovery"])
        self.assert_no_persistence_cause(fact)

    def test_matching_readback_is_the_only_preservation_claim(self) -> None:
        fact = self.reconcile(fresh=effective("gpt-6.1-sol", "high"))
        self.assertEqual(fact["outcome"], "matches-prior-applied")
        self.assertIs(fact["prior_settings_preserved"], True)
        self.assertEqual(fact["precedence"], "prior-applied")
        self.assertNotIn("recovery", fact)
        self.assertNotIn("cause", fact)

    def test_missing_readback_is_unverifiable(self) -> None:
        fact = self.reconcile(fresh=effective("gpt-6.1-sol", None))
        self.assertEqual(fact["outcome"], "unverifiable")
        self.assertIsNone(fact["prior_settings_preserved"])
        self.assertEqual(fact["precedence"], "unresolved")
        self.assertIn("recovery", fact)
        self.assert_no_persistence_cause(fact)

    def test_unsupported_effort_compares_only_the_applied_model(self) -> None:
        prior = inherited(effort=None, live_effort=None)
        prior["config_application"]["effort"] = {
            "applied": False, "reason": "no-advertised-config-option",
        }
        fact = self.reconcile(
            fresh=effective("gpt-6.1-sol", None, effort_config_id=None),
            inherited=prior,
        )
        self.assertEqual(fact["axes"]["effort"]["status"], "not-applicable")
        self.assertEqual(fact["outcome"], "matches-prior-applied")
        self.assertIs(fact["prior_settings_preserved"], True)
        self.assertEqual(fact["prior_applied_selection"]["model"], "gpt-6.1-sol")
        self.assertIsNone(fact["prior_applied_selection"]["effort"])

    def test_saved_session_change_is_left_in_place(self) -> None:
        fact = self.reconcile(
            fresh=effective("gpt-6.1-sol", "low"),
            inherited=inherited(live_effort="low"),
        )
        self.assertEqual(fact["outcome"], "saved-session-change")
        self.assertEqual(fact["precedence"], "saved-session-selection")
        self.assertIs(fact["prior_settings_preserved"], False)
        self.assertNotIn("recovery", fact)
        self.assertIn("left unchanged", fact["detail"])
        self.assert_no_persistence_cause(fact)

    def test_contradictory_evidence_does_not_follow_stale_applied(self) -> None:
        reverted = self.reconcile(
            fresh=effective("gpt-6.1-sol", "high"),
            inherited=inherited(live_effort="low"),
        )
        self.assertEqual(reverted["outcome"], "contradictory-evidence")
        self.assertIs(reverted["prior_settings_preserved"], False)
        self.assertEqual(reverted["cause"], "unproven")
        self.assertEqual(reverted["precedence"], "unresolved")
        neither = self.reconcile(
            fresh=effective("gpt-6.1-sol", "medium"),
            inherited=inherited(live_effort="low"),
        )
        self.assertEqual(neither["outcome"], "contradictory-evidence")
        self.assert_no_persistence_cause(neither)

    def test_launch_argv_model_is_not_a_native_readback(self) -> None:
        fact = self.reconcile(
            fresh=effective("swe-2-max", "high"),
            inherited=inherited(
                model="gpt-6.1-sol",
                live_model="swe-2-max",
                effective_model_source="launch-argv",
                advertised_model="swe-2-high",
            ),
        )
        self.assertEqual(fact["axes"]["model"]["status"], "differs-from-prior-applied")
        self.assertIsNone(fact["axes"]["model"]["prior_live"])
        self.assertEqual(
            fact["axes"]["model"]["prior_live_note"],
            "launch-argv-not-a-native-readback",
        )
        self.assertNotEqual(fact["outcome"], "saved-session-change")
        self.assertIs(fact["prior_settings_preserved"], False)

    def test_explicit_selection_outranks_prior_applied(self) -> None:
        fact = self.reconcile(
            explicit=True,
            recorded_source="user",
            recorded_model="gpt-6-luna",
            recorded_effort="max",
            application=applied("gpt-6-luna", "max"),
            fresh=effective("gpt-6-luna", "max"),
        )
        self.assertEqual(fact["outcome"], "explicit-current")
        self.assertEqual(fact["precedence"], "explicit-current")
        self.assertIs(fact["prior_settings_preserved"], False)
        self.assertIs(fact["explicit_readback_matches"], True)
        self.assertEqual(fact["recorded_selection"]["model"], "gpt-6-luna")
        self.assertEqual(fact["applied_configuration"]["effort"]["value"], "max")
        self.assertEqual(fact["fresh_effective_readback"]["effort"], "max")
        self.assertEqual(fact["prior_applied_selection"]["effort"], "high")

    def test_explicit_readback_mismatch_is_not_verified(self) -> None:
        fact = self.reconcile(
            explicit=True,
            recorded_source="runner-default",
            recorded_model="gpt-6.1-sol",
            recorded_effort="high",
            application=applied("gpt-6.1-sol", "high"),
            fresh=effective("gpt-6.1-sol", "low"),
        )
        self.assertEqual(fact["outcome"], "explicit-current")
        self.assertIs(fact["explicit_readback_matches"], False)
        self.assertIn("recovery", fact)
        self.assertIs(fact["prior_settings_preserved"], False)

    def test_fresh_start_default_has_no_prior_claim(self) -> None:
        fact = self.reconcile(
            resumed=False,
            recorded_source="runner-default",
            recorded_model="gpt-6.1-sol",
            recorded_effort="high",
            application=applied("gpt-6.1-sol", "high"),
            fresh=effective("gpt-6.1-sol", "high"),
            inherited=None,
        )
        self.assertEqual(fact["outcome"], "fresh-start-default")
        self.assertEqual(fact["precedence"], "fresh-start-default")
        self.assertIsNone(fact["prior_settings_preserved"])
        self.assertIsNone(fact["prior_applied_selection"])

    def test_resume_without_prior_applied_does_not_claim_preservation(self) -> None:
        fact = self.reconcile(inherited=None, fresh=effective("gpt-6.1-sol", "low"))
        self.assertEqual(fact["outcome"], "resume-without-prior-applied")
        self.assertIsNone(fact["prior_settings_preserved"])
        self.assertEqual(fact["precedence"], "saved-session-selection")

    def test_codex_adapter_omits_model_and_effort_until_they_are_resolved(self) -> None:
        bash = BASH if BASH.is_file() else Path("bash")
        adapter = SCRIPTS / "adapters" / "codex.sh"
        script = r'''
die() { printf 'die:%s\n' "$*" >&2; exit 1; }
source "$1"
permission_mode=agent
RESOLVED_FAST=
if [[ "$2" == bare ]]; then
  RESOLVED_MODEL_ID=
  RESOLVED_MODEL_EFFORT=
else
  RESOLVED_MODEL_ID=gpt-6.1-sol
  RESOLVED_MODEL_EFFORT=high
fi
adapter_build_launch /tmp/repo "" true
printf '%s\n' "${ADAPTER_LAUNCH_ARGS[@]}"
'''
        bare = subprocess.run(
            [str(bash), "-c", script, "codex-adapter", str(adapter), "bare"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(bare.returncode, 0, bare.stderr)
        bare_args = bare.stdout.splitlines()
        self.assertEqual(bare_args[:2], ["resume", "--last"])
        self.assertNotIn("--model", bare_args)
        self.assertFalse(any("model_reasoning_effort" in item for item in bare_args))
        explicit = subprocess.run(
            [str(bash), "-c", script, "codex-adapter", str(adapter), "explicit"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        explicit_args = explicit.stdout.splitlines()
        self.assertIn("--model", explicit_args)
        self.assertIn("gpt-6.1-sol", explicit_args)
        self.assertTrue(any("model_reasoning_effort" in item for item in explicit_args))
        self.assertIn('model_reasoning_effort="high"', explicit_args)


class Issue268LiveContinuationTests(unittest.TestCase):
    """Fresh preset, bare continuation, and explicit continuation on one seat."""

    @classmethod
    def setUpClass(cls) -> None:
        # Same convention as the other ACP-heavy suites (E1 harness pins): the
        # #266 broker boundary drops fixture env channels by design, so this
        # suite pins the direct backend when invoked bare; validate.sh exports
        # it for the whole run anyway.
        os.environ["KAOLA_LAUNCH_BACKEND"] = "direct"
        cls.contract = load(CONTRACT / "test-acp-contract.py", "acp_contract_issue_268")
        cls.contract.AcpSessionFixture.setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.contract.AcpSessionFixture.tearDownClass()

    def setUp(self) -> None:
        self.fx = self.contract.Issue34ModelSelectionAcpTests(
            "test_codex_default_applies_model_effort_fast_mode_in_order")
        self.fx.env = self._env
        self.fx.setUp()

    def _env(self) -> dict[str, str]:
        env = self.contract.AcpSessionFixture.env(self.fx)
        env["CODEX_BIN"] = str(self.fx.root / "no-such-codex")
        return env

    def tearDown(self) -> None:
        self.fx.tearDown()

    def stop(self) -> None:
        self.fx.cli("stop", platform="codex", check=False, timeout=15)
        self.fx._started = False

    def continue_env(self, native: str, effort: str) -> dict[str, str]:
        pages = [{
            "sessions": [{
                "sessionId": native,
                "cwd": str(self.fx.repo),
                "updatedAt": "2026-10-07T00:00:00Z",
            }],
        }]
        resume = [
            {"id": "model", "name": "Model", "type": "select",
             "currentValue": "gpt-6.1-sol",
             "options": [{"value": "gpt-6.1-sol", "name": "Sol"}]},
            {"id": "reasoning_effort", "name": "Reasoning effort", "type": "select",
             "currentValue": effort,
             "options": [{"value": "low", "name": "Low"}, {"value": "high", "name": "High"}]},
        ]
        return {
            "MOCK_ACP_LIST_PAGES": json.dumps(pages),
            "MOCK_ACP_CONFIG": json.dumps({"resume": resume}),
        }

    def test_fresh_bare_low_and_explicit_reapply(self) -> None:
        first = self.fx.start("codex", caps="echo-current")
        self.assertTrue(first.get("start_evidence_recorded"), first)
        self.assertEqual(first["model_selection"]["source"], "runner-default")
        self.assertEqual(first["model_selection"]["resolved_model"], "gpt-6.1-sol")
        self.assertEqual(first["model_selection"]["resolved_effort"], "high")
        self.assertTrue(first["config_application"]["model"]["applied"])
        self.assertEqual(first["config_application"]["model"]["value"], "gpt-6.1-sol")
        self.assertTrue(first["config_application"]["effort"]["applied"])
        self.assertEqual(first["config_application"]["effort"]["value"], "high")
        self.assertEqual(first["effective_selection"]["effective_model"], "gpt-6.1-sol")
        self.assertEqual(first["effective_selection"]["effective_effort"], "high")
        fresh = first["selection_continuity"]
        self.assertEqual(fresh["outcome"], "fresh-start-default")
        self.assertEqual(fresh["precedence"], "fresh-start-default")
        self.assertIsNone(fresh["prior_settings_preserved"])
        self.assertIsNone(fresh["prior_applied_selection"])
        native = first["acp_session_id"]
        self.assertTrue(native)
        self.stop()
        if self.fx.mock_log.is_file():
            self.fx.mock_log.write_text("", encoding="utf-8")

        resumed = self.fx.start(
            "codex", "--continue", caps="list,resume,echo-current",
            extra_env=self.continue_env(native, "low"),
        )
        self.assertTrue(resumed.get("start_evidence_recorded"), resumed)
        self.assertEqual(resumed["acp_session_id"], native)
        self.assertEqual(resumed.get("session"), first.get("session"))
        self.assertEqual(resumed.get("session_role"), first.get("session_role"))
        sent = [config_id for config_id, _value in self.fx.config_events()]
        self.assertNotIn("model", sent)
        self.assertNotIn("reasoning_effort", sent)
        selection = resumed["model_selection"]
        self.assertEqual(selection["source"], "resume-preserved")
        self.assertTrue(selection["override_omitted"])
        self.assertFalse(selection["preserved"])
        self.assertIsNone(selection["resolved_model"])
        self.assertIsNone(selection["resolved_effort"])
        continuity = resumed["selection_continuity"]
        self.assertEqual(continuity["outcome"], "differs-from-prior-applied")
        self.assertIs(continuity["prior_settings_preserved"], False)
        self.assertEqual(continuity["cause"], "unproven")
        self.assertEqual(continuity["precedence"], "unresolved")
        self.assertIsNone(continuity["recorded_selection"]["effort"])
        self.assertFalse(continuity["applied_configuration"]["effort"]["applied"])
        self.assertEqual(continuity["applied_configuration"]["effort"]["reason"], "no-resolved-value")
        self.assertEqual(continuity["fresh_effective_readback"]["effort"], "low")
        self.assertEqual(continuity["fresh_effective_readback"]["model"], "gpt-6.1-sol")
        self.assertEqual(continuity["prior_applied_selection"]["effort"], "high")
        self.assertIs(continuity["prior_applied_selection"]["historical"], True)
        self.assertNotEqual(
            continuity["recorded_selection"]["effort"],
            continuity["fresh_effective_readback"]["effort"],
        )
        self.assertNotEqual(
            continuity["applied_configuration"]["effort"]["value"],
            continuity["prior_applied_selection"]["effort"],
        )
        blob = json.dumps(continuity).lower()
        self.assertNotIn("does not persist", blob)
        self.assertNotIn("cli does not", blob)
        status = self.fx.cli("status", platform="codex")
        self.assertEqual(
            status["start_evidence"]["selection_continuity"]["outcome"],
            "differs-from-prior-applied",
        )
        self.assertFalse(status["start_evidence"]["model_selection"]["preserved"])
        self.stop()
        if self.fx.mock_log.is_file():
            self.fx.mock_log.write_text("", encoding="utf-8")

        explicit = self.fx.start(
            "codex", "--continue", "--effort", "high",
            caps="list,resume,echo-current",
            extra_env=self.continue_env(native, "low"),
        )
        self.assertEqual(explicit["acp_session_id"], native)
        self.assertEqual(explicit.get("session_role"), first.get("session_role"))
        events = self.fx.config_events()
        self.assertIn(("model", "gpt-6.1-sol"), events)
        self.assertIn(("reasoning_effort", "high"), events)
        self.assertEqual(explicit["model_selection"]["source"], "runner-default")
        self.assertFalse(explicit["model_selection"]["preserved"])
        self.assertFalse(explicit["model_selection"]["override_omitted"])
        again = explicit["selection_continuity"]
        self.assertEqual(again["outcome"], "explicit-current")
        self.assertEqual(again["precedence"], "explicit-current")
        self.assertIs(again["prior_settings_preserved"], False)
        self.assertIs(again["explicit_readback_matches"], True)
        self.assertEqual(again["recorded_selection"]["effort"], "high")
        self.assertEqual(again["applied_configuration"]["effort"]["value"], "high")
        self.assertEqual(again["fresh_effective_readback"]["effort"], "high")
        self.assertEqual(again["prior_applied_selection"]["effort"], "high")
        self.assertTrue(again["prior_applied_selection"]["historical"])

    def test_matching_bare_continuation_claims_preservation(self) -> None:
        first = self.fx.start("codex", caps="echo-current")
        native = first["acp_session_id"]
        self.stop()
        if self.fx.mock_log.is_file():
            self.fx.mock_log.write_text("", encoding="utf-8")
        resumed = self.fx.start(
            "codex", "--continue", caps="list,resume,echo-current",
            extra_env=self.continue_env(native, "high"),
        )
        self.assertEqual(resumed["acp_session_id"], native)
        sent = [config_id for config_id, _value in self.fx.config_events()]
        self.assertNotIn("model", sent)
        self.assertNotIn("reasoning_effort", sent)
        continuity = resumed["selection_continuity"]
        self.assertEqual(continuity["outcome"], "matches-prior-applied")
        self.assertIs(continuity["prior_settings_preserved"], True)
        self.assertTrue(resumed["model_selection"]["preserved"])
        self.assertTrue(resumed["model_selection"]["override_omitted"])
        self.assertEqual(continuity["fresh_effective_readback"]["effort"], "high")
        self.assertEqual(continuity["prior_applied_selection"]["effort"], "high")


if __name__ == "__main__":
    unittest.main()
