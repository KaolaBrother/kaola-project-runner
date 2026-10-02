#!/usr/bin/env python3
"""Issue #237: display name, effort, and the live current pair.

Covers the identities this change actually moved, override acceptance and
rejection, a known direct native id, preserved resume, and a live option
change. It does not snapshot every platform preset.
"""

from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"


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
        cls.holder = load("kaola-acp-holder")
        cls.render = load("render-skills")
        cls.quota = load("kaola-quota")
        cls.manifests = {
            platform: cls.render.parse_manifest(PLATFORMS / f"{platform}.yaml")
            for platform in ("claude-code", "codex", "cursor-cli", "devin", "droid")
        }

    def view_model(self, platform: str, evidence: dict, options: list) -> dict:
        holder = self.holder.Holder.__new__(self.holder.Holder)
        holder.args = argparse.Namespace(platform=platform)
        holder.start_evidence = evidence
        holder.session_meta = {"configOptions": options}
        return holder._view_model()

    def test_claude_opus_presets_share_a_name_and_not_an_effort(self) -> None:
        manifest = self.manifests["claude-code"]
        default = self.acp.model_display_fact(
            self.acp.selection_basis(args("claude-code", manifest)))
        extra = self.acp.model_display_fact(
            self.acp.selection_basis(args("claude-code", manifest, tier="opus-xhigh")))
        self.assertEqual(default["name"], extra["name"])
        self.assertEqual(default["name"], "Opus 5.5")
        self.assertEqual(default["preset_effort"], "high")
        self.assertEqual(extra["preset_effort"], "xhigh")
        self.assertEqual(default["preset_id"], "claude-code/default")
        self.assertEqual(extra["preset_id"], "claude-code/opus-xhigh")
        self.assertIsNone(default["components"])
        shared = self.acp.model_display_fact(
            self.acp.selection_basis(args("claude-code", manifest, model="opus")))
        self.assertEqual(shared["name"], "Opus 5.5")
        self.assertIsNone(shared["preset_id"])
        self.assertIsNone(shared["preset_effort"])
        self.assertIsNone(shared["components"])

    def test_devin_identities_keep_component_efforts_off_the_launch(self) -> None:
        manifest = self.manifests["devin"]
        self.assertEqual(manifest["acp_effort_config_id"], "")
        expected = {
            "default": (
                "SWE-2",
                "swe-2-max",
                "devin acp --model swe-2-max",
                [{"role": "main", "name": "SWE-2", "effort": "max"}],
            ),
            "opus-fusion": (
                "Opus Fusion",
                "fusion-claude-opus-5-5-high-sidekick-swe-2-medium",
                "devin acp --model fusion-claude-opus-5-5-high-sidekick-swe-2-medium",
                [
                    {"role": "main", "name": "Opus 5.5", "effort": "high"},
                    {"role": "sidekick", "name": "SWE-2", "effort": "medium"},
                ],
            ),
            "fable": (
                "Fable Fusion",
                "fusion-claude-fable-5-1-high-sidekick-swe-2-medium",
                "devin acp --model fusion-claude-fable-5-1-high-sidekick-swe-2-medium",
                [
                    {"role": "main", "name": "Fable 5.1", "effort": "high"},
                    {"role": "sidekick", "name": "SWE-2", "effort": "medium"},
                ],
            ),
        }
        for tier, (name, model_id, command, components) in expected.items():
            basis = self.acp.selection_basis(args("devin", manifest, tier=tier))
            display = self.acp.model_display_fact(basis)
            self.assertEqual(basis["effort"], "", tier)
            self.assertEqual(basis["candidate"], model_id, tier)
            self.assertEqual(self.acp.tier_agent_command(args("devin", manifest, tier=tier)), command)
            self.assertEqual(display["name"], name, tier)
            self.assertIsNone(display["preset_effort"], tier)
            self.assertEqual(display["components"], components, tier)
            self.assertEqual(display["components"][0]["role"], "main", tier)
        fable = expected["fable"][3]
        self.assertNotEqual(fable[0]["effort"], fable[1]["effort"])
        direct = self.acp.model_display_fact(self.acp.selection_basis(
            args("devin", manifest, model=expected["fable"][1])))
        self.assertEqual(direct["name"], "Fable Fusion")
        self.assertIsNone(direct["preset_id"])
        self.assertIsNone(direct["preset_effort"])
        self.assertIsNone(direct["components"])

    def test_explicit_effort_stays_requested_and_preset_effort_stays_declared(self) -> None:
        manifest = self.manifests["claude-code"]
        overridden = self.acp.selection_basis(
            args("claude-code", manifest, tier="opus-xhigh", effort="low"))
        self.assertEqual(overridden["effort"], "low")
        self.assertEqual(self.acp.model_display_fact(overridden)["preset_effort"], "xhigh")
        self.assertEqual(self.acp.model_display_fact(overridden)["preset_id"], "claude-code/opus-xhigh")

    def test_rejected_override_is_not_the_current_effort(self) -> None:
        view = self.view_model("codex", {
            "model_display": {
                "name": "GPT-6.1 Sol",
                "preset_id": "codex/default",
                "preset_effort": "high",
                "components": None,
            },
            "requested_effort": "low",
            "model_selection": {"resolved_effort": "low"},
            "config_application": {"effort": {"applied": False, "error": {"code": -32602}}},
            "effective_selection": {
                "effort_config_id": "reasoning_effort",
                "effective_effort": "high",
            },
        }, [
            {"id": "model", "currentValue": "gpt-6.1-sol"},
            {"id": "reasoning_effort", "currentValue": "high"},
        ])
        self.assertEqual(view["requested_effort"], "low")
        self.assertEqual(view["resolved_effort"], "low")
        self.assertFalse(view["applied_effort"]["applied"])
        self.assertEqual(view["model_display"]["preset_effort"], "high")
        self.assertEqual(view["current_effort"], "high")
        self.assertEqual(view["current"]["effort"], "high")
        self.assertNotEqual(view["current"]["effort"], "low")
        self.assertEqual(view["current"]["name_provenance"], "catalog-declared")

    def test_known_direct_selection_names_the_id_without_a_preset(self) -> None:
        manifest = self.manifests["codex"]
        basis = self.acp.selection_basis(
            args("codex", manifest, model="gpt-6-luna", effort="high", tier="luna"))
        display = self.acp.model_display_fact(basis)
        self.assertEqual(basis["candidate"], "gpt-6-luna")
        self.assertEqual(basis["effort"], "high")
        self.assertEqual(display, {
            "name": "GPT-6 Luna",
            "preset_id": None,
            "preset_effort": None,
            "components": None,
        })
        self.assertIsNone(self.quota.declared_display_name(
            {"default_model_id": "opus", "default_model_name": "Opus 5.5",
             "opus_xhigh_model_id": "opus", "opus_xhigh_model_name": "Opus Extra"},
            "opus",
        ))

    def test_unknown_direct_selection_stays_unnamed(self) -> None:
        manifest = self.manifests["codex"]
        basis = self.acp.selection_basis(
            args("codex", manifest, model="custom-model-max", tier="luna"))
        display = self.acp.model_display_fact(basis)
        self.assertEqual(basis["candidate"], "custom-model-max")
        self.assertEqual(basis["effort"], "")
        self.assertEqual(display, {
            "name": None, "preset_id": None, "preset_effort": None, "components": None,
        })
        self.assertIsNone(self.acp.parse_model_components("custom-model-max"))
        view = self.view_model("codex", {
            "model_display": display,
            "effective_selection": {"effort_config_id": "reasoning_effort"},
        }, [
            {"id": "model", "currentValue": "custom-model-max"},
            {"id": "reasoning_effort", "currentValue": "high"},
        ])
        self.assertEqual(view["current"], {
            "name": None,
            "native_id": "custom-model-max",
            "effort": "high",
            "name_provenance": None,
        })

    def test_declared_acp_wire_ids_keep_names_without_inheriting_effort(self) -> None:
        for platform, native_id, name in (
            ("cursor-cli", "grok-4.7", "Grok 4.7"),
            ("cursor-cli", "claude-opus-5-5", "Claude Opus 5.5"),
            ("dsh", '["opencode-go","deepseek-v4.1-flash"]', "DeepSeek V4.1 Flash"),
            ("zcode", "account:bigmodel-individual-coding-plan\\GLM-5.3", "GLM 5.3"),
            ("zcode", "builtin:bigmodel-coding-plan\\GLM-5.3-Flash", None),
        ):
            with self.subTest(platform=platform, native_id=native_id):
                view = self.view_model(platform, {}, [
                    {"id": "model", "currentValue": native_id},
                ])
                self.assertEqual(view["current"]["name"], name)
                self.assertEqual(view["current"]["native_id"], native_id)
                self.assertIsNone(view["current"]["effort"])
                manifest = self.quota.read_manifest(platform, SCRIPTS)
                direct = self.acp.model_display_fact(self.acp.selection_basis(
                    args(platform, manifest, model=native_id)))
                self.assertEqual(direct["name"], name)
                self.assertIsNone(direct["preset_id"])
                self.assertIsNone(direct["preset_effort"])

    def test_preserved_resume_uses_current_evidence_only(self) -> None:
        for platform in ("claude-code", "cursor-cli", "devin", "droid"):
            preserved_preset = self.acp.selection_basis(
                args(platform, self.manifests[platform], resume="sess-1"))
            self.assertEqual(preserved_preset["source"], "resume-preserved", platform)
            self.assertEqual(preserved_preset["effort"], "", platform)
            self.assertEqual(preserved_preset["candidate"], "", platform)
            self.assertIsNone(self.acp.model_display_fact(preserved_preset)["preset_effort"], platform)
        manifest = self.manifests["codex"]
        preserved = self.acp.selection_basis(args("codex", manifest, resume="sess-1"))
        self.assertEqual(preserved["source"], "resume-preserved")
        self.assertEqual(preserved["effort"], "")
        self.assertEqual(self.acp.model_display_fact(preserved), {
            "name": None, "preset_id": None, "preset_effort": None, "components": None,
        })
        inherited = {
            "name": "GPT-6.1 Sol",
            "preset_id": "codex/default",
            "preset_effort": "high",
            "components": None,
        }
        blank = self.view_model("codex", {
            "model_display": {
                "name": None, "preset_id": None, "preset_effort": None, "components": None,
            },
            "model_selection": {"preserved": True, "source": "resume-preserved"},
            "effective_selection": {"effort_config_id": "reasoning_effort"},
            "inherited": {"model_display": inherited},
        }, [])
        self.assertIsNone(blank["model_display"]["name"])
        self.assertEqual(blank["current"], {
            "name": None, "native_id": None, "effort": None, "name_provenance": None,
        })
        self.assertNotEqual(blank["current"]["name"], inherited["name"])
        live = self.view_model("codex", {
            "model_display": {
                "name": None, "preset_id": None, "preset_effort": None, "components": None,
            },
            "model_selection": {"preserved": True, "source": "resume-preserved"},
            "effective_selection": {"effort_config_id": "reasoning_effort"},
            "inherited": {"model_display": inherited},
        }, [
            {"id": "model", "currentValue": "gpt-6-luna"},
            {"id": "reasoning_effort", "currentValue": "max"},
        ])
        self.assertIsNone(live["model_display"]["name"])
        self.assertEqual(live["current"], {
            "name": "GPT-6 Luna",
            "native_id": "gpt-6-luna",
            "effort": "max",
            "name_provenance": "catalog-declared",
        })

    def test_live_option_change_is_not_paired_with_the_launch_name(self) -> None:
        view = self.view_model("codex", {
            "model_display": {
                "name": "GPT-6.1 Sol",
                "preset_id": "codex/default",
                "preset_effort": "high",
                "components": None,
            },
            "requested_effort": None,
            "model_selection": {"resolved_effort": "high", "resolved_model": "gpt-6.1-sol"},
            "effective_selection": {"effort_config_id": "reasoning_effort"},
        }, [
            {"id": "model", "currentValue": "gpt-6-luna"},
            {"id": "reasoning_effort", "currentValue": "max"},
        ])
        self.assertEqual(view["model_display"]["name"], "GPT-6.1 Sol")
        self.assertEqual(view["current_effort"], "max")
        self.assertEqual(view["current"], {
            "name": "GPT-6 Luna",
            "native_id": "gpt-6-luna",
            "effort": "max",
            "name_provenance": "catalog-declared",
        })
        self.assertNotEqual(view["model_display"]["name"], view["current"]["name"])

    def test_devin_current_id_stays_the_advertised_option(self) -> None:
        view = self.view_model("devin", {
            "model_display": {
                "name": "SWE-2",
                "preset_id": "devin/default",
                "preset_effort": None,
                "components": [{"role": "main", "name": "SWE-2", "effort": "max"}],
            },
            "effective_selection": {
                "effective_model": "swe-2-max",
                "effective_model_source": "launch-argv",
                "advertised_model": "swe-2-high",
                "effort_config_id": None,
            },
        }, [
            {"id": "model", "currentValue": "swe-2-high"},
        ])
        self.assertEqual(view["model_display"]["name"], "SWE-2")
        self.assertEqual(view["current"], {
            "name": None,
            "native_id": "swe-2-high",
            "effort": None,
            "name_provenance": None,
        })
        self.assertNotEqual(view["current"]["native_id"], "swe-2-max")

    def test_missing_current_value_stays_null(self) -> None:
        view = self.view_model("codex", {
            "model_display": {
                "name": "GPT-6.1 Sol", "preset_id": "codex/default",
                "preset_effort": "high", "components": None,
            },
            "effective_selection": {"effort_config_id": "reasoning_effort"},
        }, [
            {"id": "model"},
            {"id": "reasoning_effort", "currentValue": None},
        ])
        self.assertIsNone(view["current_effort"])
        self.assertEqual(view["current"], {
            "name": None, "native_id": None, "effort": None, "name_provenance": None,
        })
        self.assertEqual(view["model_display"]["name"], "GPT-6.1 Sol")


if __name__ == "__main__":
    unittest.main()
