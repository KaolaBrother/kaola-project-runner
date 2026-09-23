#!/usr/bin/env python3
"""Issue #148: quota package schema, query tool, and quotaPool stamping.

The research table is not on this machine. Seeds are the package ids and rule
kinds named in the issue. A model id with no verified rule is unmapped.
``single`` and codex ``absent: primary`` are declared rules, not fallbacks.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
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
            ("claude-code", "opus", "claude-code:subscription"),
            ("claude-code", "sonnet", "claude-code:subscription"),
            ("claude-code", "haiku", "claude-code:subscription"),
            ("claude-code", "default", "claude-code:subscription"),
            ("claude-code", "fable", "claude-code:scoped-weekly"),
            ("claude-code", "claude-fable-5", None),
            ("cursor-cli", "auto", "cursor-cli:cursor-models"),
            ("cursor-cli", "grok-4.7", "cursor-cli:other-models"),
            ("cursor-cli", "grok-4.7-xhigh", "cursor-cli:other-models"),
            ("cursor-cli", "grok-4.7-xhigh-fast", "cursor-cli:other-models"),
            ("cursor-cli", "claude-opus-5-5", "cursor-cli:other-models"),
            ("cursor-cli", "claude-opus-5-5-high", "cursor-cli:other-models"),
            ("cursor-cli", "brand-new-model", None),
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
        native = {"configOptions": json.loads(json.dumps(options))}
        receipt = {"session_meta": native, "record": {"session_meta": native["configOptions"]}}
        # ``record`` is a different object here; annotate must not walk it.
        stored = json.loads(json.dumps(receipt["record"]))
        self.quota.annotate_observe({"session_meta": receipt["session_meta"], "record": receipt["record"]}, catalog)
        self.assertEqual(receipt["record"], stored)

    def test_view_models_copies_and_keeps_only_the_model_option(self) -> None:
        catalog = self.catalogs["droid"]
        meta = {
            "configOptions": [
                {
                    "id": "model",
                    "options": [
                        {"value": "core-model", "name": "Core", "billingPool": "core"},
                        {"value": "mystery", "name": "Mystery"},
                    ],
                },
                {"id": "mode", "options": [{"value": "agent", "name": "Agent"}]},
            ],
            "models": {"availableModels": [{"id": "named", "billingPool": "standard"}]},
        }
        snapshot = json.dumps(meta, sort_keys=True)
        view = self.quota.view_models(meta, catalog)
        self.assertEqual(json.dumps(meta, sort_keys=True), snapshot)
        self.assertEqual([option["id"] for option in view["options"]], ["model"])
        self.assertEqual(view["options"][0]["options"][0]["quotaPool"], "droid:core")
        self.assertNotIn("quotaPoolStatus", view["options"][0]["options"][0])
        self.assertEqual(view["options"][0]["options"][1]["quotaPool"], None)
        self.assertEqual(view["options"][0]["options"][1]["quotaPoolStatus"], "unmapped")
        self.assertEqual(view["availableModels"][0]["quotaPool"], "droid:standard")

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
            self.assertEqual(self.quota.available_platforms(script_dir), ["grok"])
        self.assertEqual(loaded.public_packages(), catalog.public_packages())
        self.assertEqual(
            self.quota.resolve_model(loaded, "anything"),
            {"packageId": "grok:account", "status": "mapped"},
        )


def write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class QuotaQueryCliTest(unittest.TestCase):
    """``packages`` and ``model-package`` are read-only and do not start an agent."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-148-")
        root = Path(self.tmp.name)
        self.markers = root / "markers"
        self.markers.mkdir()
        self.login_bin = root / "login-bin"
        self.login_bin.mkdir()
        self.record_root = root / "records"
        write_exec(self.login_bin / "codex", f"#!/bin/sh\n: > '{self.markers}/codex-ran'\n")
        self.login_shell = root / "fake-login-shell"
        write_exec(self.login_shell, (
            "#!/bin/sh\n"
            f": > '{self.markers}/login-shell-ran'\n"
            '[ "$1" = "-l" ] && [ "$2" = "-c" ] || exit 64\n'
            f"export PATH='{self.login_bin}:/usr/bin:/bin'\n"
            'exec /bin/sh -c "$3"\n'
        ))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_") and not key.endswith("_BIN")}
        env["PATH"] = "/usr/bin:/bin"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        return env

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True, text=True, timeout=60, env=self.env(),
        )

    def test_packages_lists_every_platform_without_a_login_shell(self) -> None:
        result = self.run_cli("packages")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"schema", "installed_only", "platforms"})
        self.assertEqual(payload["schema"], "kaola-acp-packages/1")
        self.assertIs(payload["installed_only"], False)
        self.assertEqual([row["platform"] for row in payload["platforms"]], PLATFORM_ORDER)
        droid = next(row for row in payload["platforms"] if row["platform"] == "droid")
        self.assertEqual(
            [package["id"] for package in droid["packages"]],
            ["droid:standard", "droid:core", "droid:extra_usage"],
        )
        self.assertIsNone(droid["packages"][0]["windows"])
        self.assertFalse(self.record_root.exists())
        self.assertFalse((self.markers / "login-shell-ran").exists())
        self.assertFalse((self.markers / "codex-ran").exists())

    def test_installed_only_keeps_survey_present_rows(self) -> None:
        result = self.run_cli("packages", "--installed-only", "--login-shell", str(self.login_shell))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIs(payload["installed_only"], True)
        self.assertEqual(payload["login_env"]["status"], "ok")
        self.assertEqual([row["platform"] for row in payload["platforms"]], ["codex"])
        self.assertEqual(payload["platforms"][0]["packages"][0]["id"], "codex:primary")
        self.assertTrue((self.markers / "login-shell-ran").exists())
        self.assertFalse((self.markers / "codex-ran").exists())
        self.assertFalse(self.record_root.exists())

    def test_model_package_shapes(self) -> None:
        mapped = self.run_cli("model-package", "--platform", "grok", "--model", "grok-4.7")
        self.assertEqual(mapped.returncode, 0, mapped.stderr)
        self.assertEqual(json.loads(mapped.stdout), {
            "schema": "kaola-acp-model-package/1",
            "platform": "grok",
            "model": "grok-4.7",
            "packageId": "grok:account",
            "status": "mapped",
        })
        unmapped = self.run_cli(
            "model-package", "--platform", "droid", "--model", "claude-opus-5-5",
        )
        self.assertEqual(unmapped.returncode, 0, unmapped.stderr)
        self.assertEqual(json.loads(unmapped.stdout), {
            "schema": "kaola-acp-model-package/1",
            "platform": "droid",
            "model": "claude-opus-5-5",
            "packageId": None,
            "status": "unmapped",
        })
        self.assertFalse(self.record_root.exists())
        self.assertFalse((self.markers / "login-shell-ran").exists())

    def test_model_package_requires_platform_and_model(self) -> None:
        missing = self.run_cli("model-package", "--platform", "grok")
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse(self.record_root.exists())


class QuotaEmissionCliTest(unittest.TestCase):
    """Live observe/view stamps are copies. The stored record stays native."""

    def test_observe_and_view_stamp_copies_only(self) -> None:
        mock = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
        native = [
            {
                "id": "model",
                "name": "Model",
                "currentValue": "opencode-go/deepseek-v4.1-flash",
                "options": [
                    {"value": "opencode-go/deepseek-v4.1-flash", "name": "Flash"},
                    {"value": "zen/glm-4.6", "name": "Zen"},
                ],
            },
            {
                "id": "mode",
                "name": "Mode",
                "currentValue": "agent",
                "options": [{"value": "agent", "name": "Agent"}],
            },
        ]
        with tempfile.TemporaryDirectory(prefix="kaola-148-emit-") as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            records = root / "records"
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("KAOLA_")}
            env["KAOLA_ACP_RECORD_ROOT"] = str(records)
            env["MOCK_ACP_CONFIG"] = json.dumps({"new": native})
            session = "i148-emit"
            base = [
                sys.executable, str(CLI), "opencode",
                "--repo", str(repo), "--session", session,
                "--command", f"{sys.executable} {mock} --scenario normal",
            ]

            def run(*args: str) -> dict:
                completed = subprocess.run(
                    [*base[:3], args[0], *base[3:], *args[1:]],
                    capture_output=True, text=True, env=env, timeout=60,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
                return json.loads(completed.stdout)

            try:
                run("start")
                observed = run("observe")
                viewed = run("view")
            finally:
                subprocess.run([*base[:3], "stop", *base[3:], "--force"],
                               capture_output=True, text=True, env=env, timeout=20)
            model = next(option for option in observed["session_meta"]["configOptions"]
                         if option["id"] == "model")
            leaves = {leaf["value"]: leaf for leaf in model["options"]}
            self.assertEqual(leaves["opencode-go/deepseek-v4.1-flash"]["quotaPool"], "opencode:opencode-go")
            self.assertNotIn("quotaPoolStatus", leaves["opencode-go/deepseek-v4.1-flash"])
            self.assertEqual(leaves["zen/glm-4.6"]["quotaPool"], None)
            self.assertEqual(leaves["zen/glm-4.6"]["quotaPoolStatus"], "unmapped")
            mode = next(option for option in observed["session_meta"]["configOptions"]
                        if option["id"] == "mode")
            self.assertNotIn("quotaPool", mode["options"][0])
            view_model = viewed["models"]["options"][0]
            view_leaves = {leaf["value"]: leaf for leaf in view_model["options"]}
            self.assertEqual(view_leaves["zen/glm-4.6"]["quotaPoolStatus"], "unmapped")
            self.assertEqual(view_leaves["opencode-go/deepseek-v4.1-flash"]["quotaPool"], "opencode:opencode-go")
            self.assertEqual([option["id"] for option in viewed["models"]["options"]], ["model"])
            matches = list(records.rglob("record.json"))
            self.assertEqual(len(matches), 1, matches)
            stored = json.loads(matches[0].read_text(encoding="utf-8"))
            stored_model = next(option for option in stored["session_meta"]["configOptions"]
                                if option["id"] == "model")
            self.assertEqual(stored_model["options"], native[0]["options"])
            self.assertNotIn("quotaPool", json.dumps(stored))


if __name__ == "__main__":
    unittest.main()
