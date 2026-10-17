#!/usr/bin/env python3
"""Issue #342: Devin default reads thought_level and verifies the argv model.

``devin/default`` launches ``devin acp --model swe-2-max``. ACP advertises
``model=swe-2-high`` only and rejects ``set_config_option model=swe-2-max``.
The effort option is ``thought_level``. A start sends ``thought_level=max``,
does not set the model through ACP, and marks ``model_verified`` true only
when the argv model and that thought level match the resolved selection.
``opus-fusion`` and ``fable`` keep an empty launch effort.
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
import uuid
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
ARGV_MODEL = "swe-2-max"
ADVERTISED = "swe-2-high"
FUSION_MODEL = "fusion-claude-opus-5-5-high-sidekick-swe-2-medium"
FUSION_ADVERTISED = "fusion-claude-opus-5-5-medium-sidekick-swe-2-medium"


def load_acp():
    spec = importlib.util.spec_from_file_location("kaola_acp_i342", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def option(config_id: str, values: list[str], current: str, *,
           name: str | None = None, category: str | None = None) -> dict[str, Any]:
    return {
        "id": config_id,
        "name": name or config_id,
        "category": category or config_id,
        "type": "select",
        "currentValue": current,
        "options": [{"value": value, "name": value} for value in values],
    }


def model_option(current: str) -> dict[str, Any]:
    return option("model", [current], current, name="Model", category="model")


def thought_option(current: str) -> dict[str, Any]:
    return option(
        "thought_level", ["medium", "high", "max"], current,
        name="Thinking", category="thought_level",
    )


def mode_option(current: str = "agent") -> dict[str, Any]:
    return option("mode", ["agent", "bypass"], current, name="Mode", category="mode")


def fixture(*options: dict[str, Any], echo: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = list(options)
    return {"new": rows, "set_result": {"configOptions": echo if echo is not None else rows}}


class ManifestThoughtLevel(unittest.TestCase):
    def test_default_declares_thought_level_max_and_fusion_stays_empty(self) -> None:
        text = (PROJECT / "platforms" / "devin.yaml").read_text(encoding="utf-8")
        adapter = (PROJECT / "scripts" / "adapters" / "devin.sh").read_text(encoding="utf-8")
        readme = (PROJECT / "README.md").read_text(encoding="utf-8")
        self.assertIn('acp_effort_config_id: "thought_level"', text)
        self.assertIn('default_model_effort: "max"', text)
        self.assertIn(
            'default_model_parameters: "effort=max via ACP option thought_level"', text)
        self.assertIn('opus_fusion_model_effort: ""', text)
        self.assertIn('fable_model_effort: ""', text)
        self.assertIn("Issue #342", text)
        self.assertIn('ADAPTER_DEFAULT_MODEL_EFFORT="max"', adapter)
        self.assertIn('ADAPTER_OPUS_FUSION_MODEL_EFFORT=""', adapter)
        self.assertIn('ADAPTER_FABLE_MODEL_EFFORT=""', adapter)
        self.assertIn(
            "| `devin/default` | SWE-2 | effort=max via ACP option thought_level |",
            readme)


class ArgvThoughtVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load_acp()

    def verdict(self, *, model: str = ARGV_MODEL, effort: str = "max",
                thought: str | None = "max", effort_id: str = "thought_level",
                applied_via: str = "argv", expected_model: str | None = None,
                expected_effort: str = "max") -> dict[str, Any] | None:
        return self.acp.argv_thought_verification(
            {
                "resolved_runtime_model_id": expected_model if expected_model is not None else model,
                "resolved_parameters": {"effort": expected_effort},
            },
            {
                "effective_model": model,
                "effective_effort": thought,
                "effort_config_id": effort_id,
                "advertised_model": ADVERTISED,
            },
            {"model": {"applied": True, "applied_via": applied_via, "value": model}},
        )

    def test_match_is_true_without_comparing_the_advertised_model(self) -> None:
        verdict = self.verdict()
        self.assertIsNotNone(verdict)
        assert verdict is not None
        self.assertIs(verdict["model_verified"], True)
        self.assertEqual(verdict["actual_runtime_model_id"], ARGV_MODEL)
        self.assertEqual(verdict["actual_parameters"], {"effort": "max"})
        self.assertIsNone(verdict["model_mismatch_reason"])

    def test_thought_mismatch_is_false_and_keeps_the_argv_model(self) -> None:
        verdict = self.verdict(thought="high")
        self.assertIsNotNone(verdict)
        assert verdict is not None
        self.assertIs(verdict["model_verified"], False)
        self.assertEqual(verdict["model_mismatch_reason"], "actual-effort-mismatch:high")
        self.assertEqual(verdict["actual_runtime_model_id"], ARGV_MODEL)

    def test_effective_model_mismatch_is_false(self) -> None:
        verdict = self.verdict(model=ADVERTISED, expected_model=ARGV_MODEL)
        self.assertIsNotNone(verdict)
        assert verdict is not None
        self.assertIs(verdict["model_verified"], False)
        self.assertEqual(verdict["model_mismatch_reason"], f"actual-model-mismatch:{ADVERTISED}")

    def test_missing_thought_stays_unverified(self) -> None:
        self.assertIsNone(self.verdict(thought=None))
        self.assertIsNone(self.verdict(thought=""))

    def test_fusion_and_other_effort_ids_stay_unverified(self) -> None:
        self.assertIsNone(self.verdict(model=FUSION_MODEL, expected_model=FUSION_MODEL))
        self.assertIsNone(self.verdict(expected_effort=""))
        self.assertIsNone(self.verdict(effort_id="reasoning_effort"))
        self.assertIsNone(self.verdict(applied_via="config"))


class DevinThoughtLevelLive(unittest.TestCase):
    """Real kaola-acp.py over a fake agent that offers swe-2-high plus thought_level."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i342-")
        root = Path(self._tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.session = f"acpt-i342-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.log = root / "mock-events.jsonl"
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                    "ALL_PROXY", "all_proxy"):
            env.pop(key, None)
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(root / "records")
        env["MOCK_ACP_LOG"] = str(self.log)
        self.env = env
        self.started = False

    def tearDown(self) -> None:
        try:
            if self.started:
                self.cli("stop", "--force", model=ARGV_MODEL)
        finally:
            time.sleep(0.2)
            self._tmp.cleanup()

    def cli(self, command: str, *extra: str, model: str) -> dict[str, Any]:
        launch = f"{sys.executable} {MOCK} --scenario normal --model {model}"
        result = subprocess.run(
            [sys.executable, str(CLI), "devin", command, "--repo", str(self.repo),
             "--session", self.session, "--command", launch, *extra],
            capture_output=True, text=True, env=self.env, timeout=60,
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command}: no JSON receipt rc={result.returncode}\n"
                      f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def sets(self) -> list[tuple[str, str]]:
        rows = []
        if not self.log.is_file():
            return rows
        for line in self.log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") != "set_config_option":
                continue
            params = event.get("params") or {}
            config_id = params.get("configId") or params.get("config_id")
            rows.append((str(config_id), str(params.get("value"))))
        return rows

    def start(self, tier: str, model: str, config: dict[str, Any]) -> dict[str, Any]:
        self.env["MOCK_ACP_CONFIG"] = json.dumps(config)
        receipt = self.cli("start", "--tier", tier, "--mode", "agent", model=model)
        self.started = True
        return receipt

    def test_default_start_verifies_argv_model_and_thought_max(self) -> None:
        echoed = [
            model_option(ADVERTISED),
            thought_option("max"),
            mode_option("agent"),
        ]
        receipt = self.start("default", ARGV_MODEL, fixture(
            model_option(ADVERTISED), thought_option("high"), mode_option(),
            echo=echoed,
        ))
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertNotEqual(receipt.get("result"), "refused", receipt)
        self.assertEqual(receipt.get("state"), "ready", receipt)
        self.assertEqual(receipt["config_application"]["model"],
                         {"applied": True, "applied_via": "argv", "value": ARGV_MODEL})
        effort = receipt["config_application"]["effort"]
        self.assertEqual(
            (effort.get("applied"), effort.get("config_id"), effort.get("value"),
             effort.get("advertised")),
            (True, "thought_level", "max", True), effort)
        selection = receipt["effective_selection"]
        self.assertEqual(selection.get("effective_model"), ARGV_MODEL)
        self.assertEqual(selection.get("effective_model_source"), "launch-argv")
        self.assertEqual(selection.get("advertised_model"), ADVERTISED)
        self.assertEqual(selection.get("effective_effort"), "max")
        self.assertEqual(selection.get("effort_config_id"), "thought_level")
        self.assertIs(receipt.get("model_verified"), True)
        self.assertEqual(receipt.get("actual_runtime_model_id"), ARGV_MODEL)
        self.assertEqual(receipt.get("actual_parameters"), {"effort": "max"})
        self.assertIsNone(receipt.get("model_mismatch_reason"))
        actual = receipt["model_evidence_provenance"]["actual"]
        self.assertEqual(actual["source"], "acp-thought-level")
        self.assertEqual(actual["model_id"], ARGV_MODEL)
        self.assertEqual(receipt["model_display"]["preset_effort"], "max")
        sent = self.sets()
        self.assertIn(("thought_level", "max"), sent)
        self.assertNotIn("model", [config_id for config_id, _ in sent])

        for command in ("status", "observe"):
            with self.subTest(command=command):
                viewed = self.cli(command, model=ARGV_MODEL)
                self.assertIsNone(viewed.get("error"), viewed)
                self.assertEqual(viewed["effective_selection"]["effective_model"], ARGV_MODEL)
                self.assertEqual(viewed["effective_selection"]["effective_effort"], "max")
                evidence = viewed["start_evidence"]
                self.assertIs(evidence.get("model_verified"), True)
                self.assertEqual(evidence.get("actual_runtime_model_id"), ARGV_MODEL)
                self.assertEqual(evidence["effective_selection"]["effective_effort"], "max")
                self.assertEqual(
                    evidence["model_evidence_provenance"]["actual"]["source"],
                    "acp-thought-level")

    def test_thought_mismatch_is_recorded_and_does_not_refuse_the_start(self) -> None:
        echoed = [
            model_option(ADVERTISED),
            thought_option("high"),
            mode_option("agent"),
        ]
        receipt = self.start("default", ARGV_MODEL, fixture(
            model_option(ADVERTISED), thought_option("high"), mode_option(),
            echo=echoed,
        ))
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertNotEqual(receipt.get("result"), "refused", receipt)
        self.assertEqual(receipt.get("state"), "ready", receipt)
        self.assertEqual(receipt["effective_selection"]["effective_model"], ARGV_MODEL)
        self.assertEqual(receipt["effective_selection"]["effective_effort"], "high")
        self.assertIs(receipt.get("model_verified"), False)
        self.assertEqual(receipt.get("model_mismatch_reason"), "actual-effort-mismatch:high")
        self.assertEqual(receipt.get("actual_runtime_model_id"), ARGV_MODEL)
        self.assertIn(("thought_level", "max"), self.sets())
        self.assertNotIn("model", [config_id for config_id, _ in self.sets()])

    def test_missing_thought_current_value_stays_unknown(self) -> None:
        receipt = self.start("default", ARGV_MODEL, fixture(
            model_option(ADVERTISED), mode_option(),
        ))
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt.get("model_verified"), "unknown")
        self.assertIsNone(receipt.get("actual_runtime_model_id"))
        self.assertEqual(receipt.get("model_mismatch_reason"),
                         "actual-model-evidence-not-yet-read")
        self.assertIsNone(receipt["effective_selection"].get("effective_effort"))
        self.assertEqual(receipt["effective_selection"]["effective_model"], ARGV_MODEL)
        self.assertIn(("thought_level", "max"), self.sets())
        self.assertNotIn("model", [config_id for config_id, _ in self.sets()])

    def test_opus_fusion_does_not_apply_or_verify_thought_level(self) -> None:
        echoed = [
            model_option(FUSION_ADVERTISED),
            thought_option("high"),
            mode_option("agent"),
        ]
        receipt = self.start("opus-fusion", FUSION_MODEL, fixture(
            model_option(FUSION_ADVERTISED), thought_option("high"), mode_option(),
            echo=echoed,
        ))
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertNotEqual(receipt.get("result"), "refused", receipt)
        effort = receipt["config_application"]["effort"]
        self.assertEqual(effort, {"applied": False, "reason": "no-resolved-value"})
        self.assertIsNone(receipt["model_display"]["preset_effort"])
        self.assertEqual(
            [item["effort"] for item in receipt["model_display"]["components"]],
            ["high", "medium"])
        selection = receipt["effective_selection"]
        self.assertEqual(selection.get("effective_model"), FUSION_MODEL)
        self.assertEqual(selection.get("advertised_model"), FUSION_ADVERTISED)
        self.assertEqual(selection.get("effective_effort"), "high")
        self.assertEqual(receipt.get("model_verified"), "unknown")
        self.assertIsNone(receipt.get("actual_runtime_model_id"))
        sent = self.sets()
        self.assertNotIn("thought_level", [config_id for config_id, _ in sent])
        self.assertNotIn("model", [config_id for config_id, _ in sent])


if __name__ == "__main__":
    unittest.main()
