#!/usr/bin/env python3
"""Issue #148: quota package schema, seeded rules, and quotaPool stamping.

The research table is not on this machine. Seeds are the package ids and rule
kinds named in the issue. A model id with no verified rule is unmapped.
``single`` and codex ``absent: primary`` are declared rules, not fallbacks.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
QUOTA_PATH = PROJECT / "scripts" / "kaola-quota.py"
RENDER_PATH = PROJECT / "scripts" / "render-skills.py"
PLATFORMS = PROJECT / "platforms"
PLATFORM_ORDER = [
    "claude-code", "codex", "cursor-cli", "devin", "droid",
    "dsh", "grok", "kimi-cli", "opencode", "zcode",
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class QuotaSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quota = load(QUOTA_PATH, "kaola_quota_148")
        cls.render = load(RENDER_PATH, "render_skills_148")
        cls.catalogs = {
            platform: cls.quota.load_catalog(platform)
            for platform in PLATFORM_ORDER
        }

    def test_every_manifest_parses_and_render_accepts_it(self) -> None:
        self.assertEqual(self.quota.RULE_KINDS, ("single", "provider_prefix", "native_field", "explicit"))
        for platform in PLATFORM_ORDER:
            with self.subTest(platform=platform):
                manifest = self.render.parse_manifest(PLATFORMS / f"{platform}.yaml")
                self.assertEqual(manifest["id"], platform)
                catalog = self.catalogs[platform]
                self.assertEqual(catalog.rule["kind"], json.loads(manifest["model_package_rule"])["kind"])
                self.assertTrue(catalog.packages)
                ids = [row["id"] for row in catalog.public_packages()]
                self.assertEqual(ids, [f"{platform}:{package['id']}" for package in catalog.packages])
                for row in catalog.public_packages():
                    self.assertIsNone(row["windows"])
                    self.assertIsInstance(row["binds_models"], bool)

    def test_seeded_package_tokens(self) -> None:
        expected = {
            "claude-code": ["subscription", "scoped-weekly", "extra_usage"],
            "codex": ["primary", "base_model_inference"],
            "cursor-cli": ["cursor-models", "other-models"],
            "devin": ["max", "overage"],
            "droid": ["standard", "core", "extra_usage"],
            "dsh": ["opencode-go"],
            "grok": ["account"],
            "kimi-cli": ["managed"],
            "opencode": ["opencode-go", "zhipuai-coding-plan", "zen"],
            "zcode": ["bigmodel-coding-plan"],
        }
        for platform, tokens in expected.items():
            self.assertEqual(
                [package["id"] for package in self.catalogs[platform].packages],
                tokens,
                platform,
            )
        self.assertFalse(self.catalogs["claude-code"].packages[2]["binds_models"])
        self.assertFalse(self.catalogs["devin"].packages[1]["binds_models"])

    def test_partial_rules_leave_unverified_ids_unmapped(self) -> None:
        cases = [
            ("claude-code", "opus", None),
            ("claude-code", "fable", "claude-code:scoped-weekly"),
            ("claude-code", "claude-fable-5", None),
            ("cursor-cli", "auto", "cursor-cli:cursor-models"),
            ("cursor-cli", "grok-4.7-xhigh", None),
            ("droid", "claude-opus-5-5", None),
            ("dsh", "opencode-go/deepseek-v4.1-flash", "dsh:opencode-go"),
            ("dsh", '["opencode-go","deepseek-v4.1-flash"]', "dsh:opencode-go"),
            ("dsh", '["deepseek-official","deepseek-v4-pro"]', None),
            ("dsh", "deepseek-official/deepseek-flash", None),
            ("kimi-cli", "kimi-code/k3", "kimi-cli:managed"),
            ("kimi-cli", "kimi-code/kimi-for-coding", "kimi-cli:managed"),
            ("kimi-cli", "other/k3", None),
            ("opencode", "zhipuai-coding-plan/glm-5.3-flash", "opencode:zhipuai-coding-plan"),
            ("opencode", "opencode-go/deepseek-v4.1-flash", "opencode:opencode-go"),
            ("opencode", "zen/glm-5", None),
            ("opencode", "brand-new-model", None),
            ("zcode", r"builtin:bigmodel-coding-plan\GLM-5.3", "zcode:bigmodel-coding-plan"),
            ("zcode", r"account:bigmodel-individual-coding-plan\GLM-5.3", "zcode:bigmodel-coding-plan"),
            ("zcode", "GLM-5.3", None),
            ("zcode", r"builtin:zai-coding-plan\GLM-5.3", None),
        ]
        for platform, model_id, package_id in cases:
            with self.subTest(platform=platform, model_id=model_id):
                resolved = self.quota.resolve_model(self.catalogs[platform], model_id)
                self.assertEqual(resolved["packageId"], package_id)
                self.assertEqual(resolved["status"], "mapped" if package_id else "unmapped")

    def test_declared_total_rules_are_not_a_fallback_across_packages(self) -> None:
        grok = self.quota.resolve_model(self.catalogs["grok"], "grok-4.7-brand-new")
        self.assertEqual(grok, {"packageId": "grok:account", "status": "mapped"})
        self.assertEqual(
            self.quota.resolve_model(self.catalogs["grok"], "  "),
            {"packageId": None, "status": "unmapped"},
        )
        devin = self.quota.resolve_model(self.catalogs["devin"], "swe-2-max")
        self.assertEqual(devin["packageId"], "devin:max")
        codex = self.quota.resolve_model(self.catalogs["codex"], "gpt-6-sol-brand-new")
        self.assertEqual(codex["packageId"], "codex:primary")

    def test_native_field_uses_the_row_and_never_guesses(self) -> None:
        droid = self.catalogs["droid"]
        mapped = self.quota.resolve_model(
            droid, "claude-opus-5-5", {"value": "claude-opus-5-5", "billingPool": "core"},
        )
        self.assertEqual(mapped["packageId"], "droid:core")
        unknown = self.quota.resolve_model(
            droid, "claude-opus-5-5", {"billingPool": "nope"},
        )
        self.assertEqual(unknown, {"packageId": None, "status": "unmapped"})
        missing = self.quota.resolve_model(droid, "claude-opus-5-5", {})
        self.assertEqual(missing["status"], "unmapped")
        codex = self.catalogs["codex"]
        second = self.quota.resolve_model(codex, "gpt-6-sol", {"limitIds": ["base_model_inference"]})
        self.assertEqual(second["packageId"], "codex:base_model_inference")
        conflict = self.quota.resolve_model(
            codex, "gpt-6-sol", {"limitIds": ["primary", "base_model_inference"]},
        )
        self.assertEqual(conflict["status"], "unmapped")
        exposed = self.quota.resolve_model(codex, "gpt-6-sol", {"limitIds": ["not-a-package"]})
        self.assertEqual(exposed["status"], "unmapped")
        hidden = self.quota.resolve_model(codex, "gpt-6-sol", {})
        self.assertEqual(hidden["packageId"], "codex:primary")

    def test_observe_rows_carry_quota_pool_without_touching_other_options(self) -> None:
        catalog = self.catalogs["dsh"]
        options = [
            {
                "id": "model",
                "options": [
                    {
                        "group": "deepseek-official",
                        "options": [{"value": '["deepseek-official","deepseek-v4-pro"]', "name": "Pro"}],
                    },
                    {
                        "group": "opencode-go",
                        "options": [{"value": '["opencode-go","deepseek-v4.1-flash"]', "name": "Flash"}],
                    },
                ],
            },
            {"id": "reasoning_effort", "options": [{"value": "high", "name": "High"}]},
        ]
        receipt = {
            "session_meta": {
                "configOptions": options,
                "models": {"availableModels": [{"id": "opencode-go/deepseek-v4.1-flash", "name": "Flash"}]},
                "availableModels": [{"modelId": "GLM-5.3"}],
            },
            "initial_config_options": [
                {"id": "model", "options": [{"value": "opencode-go/deepseek-v4.1-flash", "name": "Flash"}]},
            ],
        }
        self.quota.annotate_observe(receipt, catalog)
        leaves = []
        for group in options[0]["options"]:
            self.assertNotIn("quotaPool", group)
            leaves.extend(group["options"])
        self.assertEqual(leaves[0]["quotaPool"], None)
        self.assertEqual(leaves[0]["quotaPoolStatus"], "unmapped")
        self.assertEqual(leaves[1]["quotaPool"], "dsh:opencode-go")
        self.assertNotIn("quotaPoolStatus", leaves[1])
        self.assertNotIn("quotaPool", options[1]["options"][0])
        available = receipt["session_meta"]["models"]["availableModels"][0]
        self.assertEqual(available["quotaPool"], "dsh:opencode-go")
        bare = receipt["session_meta"]["availableModels"][0]
        self.assertEqual(bare["quotaPool"], None)
        self.assertEqual(bare["quotaPoolStatus"], "unmapped")
        initial = receipt["initial_config_options"][0]["options"][0]
        self.assertEqual(initial["quotaPool"], "dsh:opencode-go")

    def test_schema_rejects_a_guess_shaped_rule(self) -> None:
        packages = json.dumps([
            {"id": "standard", "name": "Standard"},
            {"id": "extra_usage", "name": "Extra usage", "binds_models": False},
        ])
        with self.assertRaises(self.quota.QuotaError):
            self.quota.parse_rule(json.dumps({"kind": "fallback", "package": "standard"}), 
                                   self.quota.parse_packages(packages))
        parsed = self.quota.parse_packages(packages)
        with self.assertRaises(self.quota.QuotaError):
            self.quota.parse_rule(
                json.dumps({"kind": "single", "package": "extra_usage"}), parsed,
            )
        with self.assertRaises(self.quota.QuotaError):
            self.quota.parse_rule(
                json.dumps({
                    "kind": "provider_prefix",
                    "providers": {"zen": "standard"},
                    "gaps": ["zen"],
                }),
                parsed,
            )

    def test_skill_local_platform_yaml_is_the_catalog(self) -> None:
        catalog = self.catalogs["grok"]
        with tempfile.TemporaryDirectory() as tmp:
            script_dir = Path(tmp)
            source = (PLATFORMS / "grok.yaml").read_text(encoding="utf-8")
            (script_dir / "platform.yaml").write_text(source, encoding="utf-8")
            loaded = self.quota.load_catalog("grok", script_dir)
        self.assertEqual(loaded.public_packages(), catalog.public_packages())
        self.assertEqual(
            self.quota.resolve_model(loaded, "anything"),
            {"packageId": "grok:account", "status": "mapped"},
        )


if __name__ == "__main__":
    unittest.main()
