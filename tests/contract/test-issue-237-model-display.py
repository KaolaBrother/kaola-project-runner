#!/usr/bin/env python3
"""Issue #237: consumer display names stay separate from effort.

Preset IDs, native IDs, launch efforts, and Devin argv stay as declared.
Display metadata does not invent a current effort or a name by stripping a suffix.
"""

from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"

# name, native id, launch effort. Components are asserted separately.
EXPECTED = {
    "claude-code": {
        "default": ("Opus 5.5", "opus", "medium"),
        "opus-xhigh": ("Opus 5.5", "opus", "xhigh"),
        "fable": ("Fable", "fable", "high"),
        "sonnet": ("Sonnet", "sonnet", "high"),
    },
    "codex": {
        "default": ("GPT-6 Sol", "gpt-6-sol", "high"),
        "astra": ("GPT-6 Astra", "gpt-6-astra", "high"),
        "luna": ("GPT-6 Luna", "gpt-6-luna", "max"),
    },
    "cursor-cli": {
        "default": ("Grok 4.7", "grok-4.7-xhigh", "xhigh"),
        "opus": ("Claude Opus 5.5", "claude-opus-5-5-medium", "medium"),
    },
    "devin": {
        "default": ("SWE-2", "swe-2-max", ""),
        "opus-fusion": ("Opus Fusion", "fusion-claude-opus-5-5-medium-sidekick-swe-2-medium", ""),
        "fable": ("Fable Fusion", "fusion-claude-fable-5-1-high-sidekick-swe-2-medium", ""),
    },
    "droid": {
        "default": ("Auto Model", "auto", ""),
        "opus": ("Opus 5.5", "claude-opus-5-5", "medium"),
        "core": ("Kimi K3", "kimi-k3", "max"),
    },
    "dsh": {"default": ("DeepSeek V4.1 Flash", "opencode-go/deepseek-v4.1-flash", "")},
    "grok": {"default": ("Grok 4.7", "grok-4.7", "xhigh")},
    "kimi-cli": {
        "default": ("Kimi K3", "kimi-code/k3", "max"),
        "kimi-k2-8": ("Kimi K2.8", "kimi-code/kimi-for-coding", "max"),
    },
    "opencode": {"default": ("DeepSeek V4.1 Flash", "opencode-go/deepseek-v4.1-flash", "")},
    "zcode": {"default": ("GLM 5.3", "GLM-5.3", "max")},
}

DEVIN_ARGV = {
    "default": "devin acp --model swe-2-max",
    "opus-fusion": "devin acp --model fusion-claude-opus-5-5-medium-sidekick-swe-2-medium",
    "fable": "devin acp --model fusion-claude-fable-5-1-high-sidekick-swe-2-medium",
}

EXAMPLES = (
    '{"name": "Opus 5.5", "preset_id": "claude-code/default", "preset_effort": "medium", "components": null}',
    '{"name": "Opus 5.5", "preset_id": "claude-code/opus-xhigh", "preset_effort": "xhigh", "components": null}',
    '{"name": "Auto Model", "preset_id": "droid/default", "preset_effort": null, "components": null}',
    '{"name": "Fable Fusion", "preset_id": "devin/fable", "preset_effort": null, "components": [{"role": "main", "name": "Fable 5.1", "effort": "high"}, {"role": "sidekick", "name": "SWE-2", "effort": "medium"}]}',
)


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def args(platform: str, manifest: dict, **overrides):
    values = {
        "platform": platform,
        "manifest": manifest,
        "model": None,
        "effort": None,
        "tier": None,
        "resume": None,
        "use_continue": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class ModelDisplayContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load("kaola-acp")
        cls.render = load("render-skills")
        cls.manifests = {
            path.stem: cls.render.parse_manifest(path)
            for path in sorted(PLATFORMS.glob("*.yaml"))
        }

    def test_ten_runtime_display_names_keep_ids_and_launch_efforts(self) -> None:
        self.assertEqual(set(self.manifests), set(EXPECTED))
        for platform, tiers in EXPECTED.items():
            manifest = self.manifests[platform]
            declared = ["default", *[
                word for word in manifest["named_tiers"].split(",") if word
            ]]
            self.assertEqual(declared, list(tiers), platform)
            for tier, (name, model_id, effort) in tiers.items():
                prefix = tier.replace("-", "_")
                self.assertEqual(manifest[f"{prefix}_model_name"], name, f"{platform}/{tier}")
                self.assertEqual(manifest[f"{prefix}_model_id"], model_id, f"{platform}/{tier}")
                self.assertEqual(manifest[f"{prefix}_model_effort"], effort, f"{platform}/{tier}")

    def test_only_devin_declares_components_and_they_do_not_launch(self) -> None:
        for platform, manifest in self.manifests.items():
            keys = [key for key in manifest if key.endswith("_model_components")]
            if platform != "devin":
                self.assertEqual(keys, [], platform)
                continue
            self.assertEqual(manifest["acp_effort_config_id"], "")
            self.assertEqual(
                self.acp.parse_model_components(manifest["default_model_components"]),
                [{"role": "main", "name": "SWE-2", "effort": "max"}],
            )
            fusion = self.acp.parse_model_components(manifest["opus_fusion_model_components"])
            self.assertEqual([item["effort"] for item in fusion], ["medium", "medium"])
            self.assertNotEqual(fusion[0]["name"], fusion[1]["name"])
            fable = self.acp.parse_model_components(manifest["fable_model_components"])
            self.assertEqual(fable[0], {"role": "main", "name": "Fable 5.1", "effort": "high"})
            self.assertEqual(fable[1], {"role": "sidekick", "name": "SWE-2", "effort": "medium"})
            self.assertNotEqual(fable[0]["effort"], fable[1]["effort"])
            for tier, command in DEVIN_ARGV.items():
                basis = self.acp.selection_basis(args("devin", manifest, tier=tier))
                self.assertEqual(basis["effort"], "")
                self.assertEqual(basis["candidate"], manifest[f"{tier.replace('-', '_')}_model_id"])
                self.assertEqual(
                    self.acp.tier_agent_command(args("devin", manifest, tier=tier)), command)
                self.assertEqual(self.acp.argv_model(command), basis["candidate"])
                display = self.acp.model_display_fact(basis)
                self.assertIsNone(display["preset_effort"])
                self.assertEqual(display["components"][0]["role"], "main")

    def test_claude_opus_presets_share_a_name_and_not_an_effort(self) -> None:
        manifest = self.manifests["claude-code"]
        default = self.acp.model_display_fact(
            self.acp.selection_basis(args("claude-code", manifest)))
        extra = self.acp.model_display_fact(
            self.acp.selection_basis(args("claude-code", manifest, tier="opus-xhigh")))
        self.assertEqual(default["name"], extra["name"])
        self.assertEqual(default["name"], "Opus 5.5")
        self.assertEqual(default["preset_effort"], "medium")
        self.assertEqual(extra["preset_effort"], "xhigh")
        self.assertEqual(default["preset_id"], "claude-code/default")
        self.assertEqual(extra["preset_id"], "claude-code/opus-xhigh")
        self.assertIsNone(default["components"])
        overridden = self.acp.selection_basis(
            args("claude-code", manifest, tier="opus-xhigh", effort="low"))
        self.assertEqual(overridden["effort"], "low")
        self.assertEqual(
            self.acp.model_display_fact(overridden)["preset_effort"], "xhigh")

    def test_direct_model_and_preserved_resume_do_not_invent_display_or_effort(self) -> None:
        manifest = self.manifests["codex"]
        direct = self.acp.selection_basis(
            args("codex", manifest, model="custom-model-max", tier="luna"))
        display = self.acp.model_display_fact(direct)
        self.assertEqual(direct["candidate"], "custom-model-max")
        self.assertEqual(direct["effort"], "")
        self.assertEqual(display, {
            "name": None, "preset_id": None, "preset_effort": None, "components": None,
        })
        self.assertIsNone(self.acp.parse_model_components("custom-model-max"))
        preserved = self.acp.selection_basis(args("codex", manifest, resume="sess-1"))
        self.assertEqual(preserved["source"], "resume-preserved")
        self.assertEqual(preserved["effort"], "")
        self.assertEqual(self.acp.model_display_fact(preserved), display)
        unknown = self.acp.model_display_fact(
            self.acp.selection_basis(args("droid", self.manifests["droid"])))
        self.assertEqual(unknown["name"], "Auto Model")
        self.assertIsNone(unknown["preset_effort"])
        self.assertIsNone(unknown["components"])

    def test_docs_examples_match_the_display_facts(self) -> None:
        text = (PROJECT / "docs" / "api.md").read_text(encoding="utf-8")
        for example in EXAMPLES:
            self.assertIn(example, text)
        for path in (
            "model_display",
            "requested_effort",
            "model_selection.resolved_effort",
            "config_application.effort",
            "effective_selection.effective_effort",
            "view.model.current_effort",
            "view.models",
            "start_evidence.inherited",
        ):
            self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
