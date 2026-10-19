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
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
QUOTA_PATH = PROJECT / "scripts" / "kaola-quota.py"
RENDER_PATH = PROJECT / "scripts" / "render-skills.py"
PLATFORMS = PROJECT / "platforms"
PLATFORM_ORDER = [
    "antigravity", "claude-code", "codex", "cursor-cli", "devin", "droid",
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
                self.assertEqual(
                    ids,
                    [catalog.qualified(package["id"]) for package in catalog.packages],
                )
                for row in catalog.public_packages():
                    windows = row["windows"]
                    self.assertTrue(windows is None or isinstance(windows, list))
                    if windows is not None:
                        self.assertTrue(all(isinstance(window, str) and window for window in windows))
                    self.assertIsInstance(row["binds_models"], bool)

    def test_seeded_package_tokens(self) -> None:
        expected = {
            "antigravity": ["account"],
            "claude-code": ["subscription", "scoped-weekly", "extra_usage"],
            "codex": ["primary", "base_model_inference"],
            "cursor-cli": ["account"],
            "devin": ["max", "overage"],
            "droid": ["standard", "core", "extra_usage"],
            "dsh": ["opencode-go", "commandcode"],
            "grok": ["account"],
            "kimi-cli": ["managed", "managed_monthly"],
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
        # Issue #222: the display name changes; the id does not.
        self.assertEqual(
            [(package["id"], package["name"])
             for package in self.catalogs["zcode"].public_packages()],
            [("zcode:bigmodel-coding-plan", "GLM Coding Plan")],
        )

    def test_issue_192_package_windows_match_verified_period_facts(self) -> None:
        expected = {
            "claude-code": {
                "subscription": ["weekly"],
                "scoped-weekly": ["weekly"],
                "extra_usage": None,
            },
            "codex": {
                "primary": ["weekly"],
                "base_model_inference": ["weekly"],
            },
            "cursor-cli": {"account": ["monthly"]},
            "antigravity": {"account": ["5h", "weekly"]},
            "devin": {"max": ["weekly"], "overage": None},
            "droid": {
                "standard": ["5h", "weekly", "monthly"],
                "core": ["weekly", "monthly"],
                "extra_usage": [],
            },
            "dsh": {
                "opencode-go": ["weekly", "monthly"],
                "commandcode": ["5h", "weekly", "monthly"],
            },
            "grok": {"account": ["monthly"]},
            "kimi-cli": {
                "managed": ["weekly", "monthly"],
                "managed_monthly": ["monthly"],
            },
            "opencode": {
                "opencode-go": ["weekly", "monthly"],
                "zhipuai-coding-plan": ["5h"],
                "zen": None,
            },
            "zcode": {"bigmodel-coding-plan": ["5h"]},
        }
        for platform, packages in expected.items():
            actual = {
                package["id"]: package["windows"]
                for package in self.catalogs[platform].packages
            }
            self.assertEqual(actual, packages, platform)

        kimi = self.catalogs["kimi-cli"]
        self.assertFalse(next(p for p in kimi.packages if p["id"] == "managed_monthly")["binds_models"])
        self.assertEqual(
            self.quota.resolve_model(kimi, "kimi-code/k3")["packageId"],
            "kimi-cli:managed",
        )

    def test_partial_rules_leave_unverified_ids_unmapped(self) -> None:
        cases = [
            ("claude-code", "opus", "claude-code:subscription"),
            # Issue #230: opus-xhigh is a preset ID. Both Opus presets launch
            # the alias ``opus``, which is the subscription map key.
            ("claude-code", "opus-xhigh", None),
            ("claude-code", "sonnet", "claude-code:subscription"),
            ("claude-code", "haiku", "claude-code:subscription"),
            ("claude-code", "default", "claude-code:subscription"),
            ("claude-code", "fable", "claude-code:scoped-weekly"),
            ("claude-code", "claude-fable-5", None),
            # Issue #368: Grok and Cursor usage draw from one shared pool
            # (``cursor-grok``). Every cursor-cli model resolves to
            # cursor-cli:account and every grok model to grok:account — the
            # two runtimes' own ids for that pool; the
            # cursor-models/other-models split is gone.
            ("cursor-cli", "auto", "cursor-cli:account"),
            ("cursor-cli", "default", "cursor-cli:account"),
            ("cursor-cli", "grok-4.7", "cursor-cli:account"),
            ("cursor-cli", "grok-4.7-high", "cursor-cli:account"),
            ("cursor-cli", "grok-4.7-high-fast", "cursor-cli:account"),
            ("cursor-cli", "grok-4.7-xhigh", "cursor-cli:account"),
            ("cursor-cli", "grok-4.7-xhigh-fast", "cursor-cli:account"),
            ("cursor-cli", "claude-opus-5-5", "cursor-cli:account"),
            ("cursor-cli", "claude-opus-5-5-high", "cursor-cli:account"),
            ("cursor-cli", "brand-new-model", "cursor-cli:account"),
            ("grok", "grok-4.7", "grok:account"),
            ("grok", "grok-4.7-brand-new", "grok:account"),
            # Issue #222: the owner-confirmed droid presets are static preset
            # knowledge; the static query has no live billingPool row.
            ("droid", "auto", "droid:standard"),
            ("droid", "claude-opus-5-5", "droid:standard"),
            ("droid", "kimi-k3", "droid:core"),
            ("droid", "brand-new-model", None),
            ("dsh", "opencode-go/deepseek-v4.1-flash", "dsh:opencode-go"),
            ("dsh", '["opencode-go","deepseek-v4.1-flash"]', "dsh:opencode-go"),
            ("dsh", "commandcode/deepseek/deepseek-v4.1-flash", "dsh:commandcode"),
            ("dsh", '["commandcode","deepseek/deepseek-v4.1-flash"]', "dsh:commandcode"),
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
            # Issue #222: the bare configured default is static preset knowledge
            # and keeps the provider-qualified routes untouched.
            ("zcode", "GLM-5.3", "zcode:bigmodel-coding-plan"),
            ("zcode", r"builtin:zai-coding-plan\GLM-5.3", None),
        ]
        for platform, model_id, package_id in cases:
            with self.subTest(platform=platform, model_id=model_id):
                resolved = self.quota.resolve_model(self.catalogs[platform], model_id)
                self.assertEqual(resolved["packageId"], package_id)
                self.assertEqual(resolved["status"], "mapped" if package_id else "unmapped")

    def test_declared_total_rules_are_not_a_fallback_across_packages(self) -> None:
        grok = self.quota.resolve_model(self.catalogs["grok"], "grok-4.7-brand-new")
        self.assertEqual(grok, {"packageId": "grok:account", "pool": "cursor-grok", "status": "mapped"})
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
        # Issue #222: a live row whose native field is missing falls back to the
        # static preset map, and an unknown id with the same row stays unmapped.
        missing = self.quota.resolve_model(droid, "claude-opus-5-5", {})
        self.assertEqual(missing["packageId"], "droid:standard")
        stranger = self.quota.resolve_model(droid, "brand-new-model", {})
        self.assertEqual(stranger, {"packageId": None, "status": "unmapped"})
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
            {"packageId": "grok:account", "pool": "cursor-grok", "status": "mapped"},
        )

    def test_issue_368_shared_pool_two_own_ids(self) -> None:
        """Issue #368: one shared pool, each runtime keeps its own id.

        Grok and Cursor usage draw from the shared pool ``cursor-grok``.
        Each runtime describes that pool with its own package id —
        ``cursor-cli:account`` and ``grok:account`` carry the same ``pool``
        marker — with no cross-mapping between namespaces, and a stamped
        ``quotaPool`` names the pool so Delegator and Host views present one
        shared line.
        """
        cursor = self.catalogs["cursor-cli"]
        grok = self.catalogs["grok"]
        cursor_row = {"id": "cursor-cli:account", "name": "Cursor+Grok account usage",
                      "windows": ["monthly"], "binds_models": True, "pool": "cursor-grok"}
        grok_row = {"id": "grok:account", "name": "Cursor+Grok account usage",
                    "windows": ["monthly"], "binds_models": True, "pool": "cursor-grok"}
        self.assertEqual(cursor.public_packages(), [cursor_row])
        self.assertEqual(grok.public_packages(), [grok_row])
        for model in ("grok-4.7-high", "claude-opus-5-5-high", "auto", "unlisted"):
            resolved = self.quota.resolve_model(cursor, model)
            self.assertEqual(resolved["packageId"], "cursor-cli:account")
            self.assertEqual(resolved["pool"], "cursor-grok")
        for model in ("grok-4.7", "unlisted"):
            resolved = self.quota.resolve_model(grok, model)
            self.assertEqual(resolved["packageId"], "grok:account")
            self.assertEqual(resolved["pool"], "cursor-grok")
        # The removed cursor-cli split ids are gone from every catalog.
        emitted = {
            package["id"]
            for catalog in self.catalogs.values()
            for package in catalog.public_packages()
        }
        self.assertFalse(emitted & {
            "cursor-cli:cursor-models", "cursor-cli:other-models",
        })
        # Stamped rows name the shared pool itself on both runtimes; a stored
        # row naming a removed package is migrated by re-emission, not read
        # back.
        for catalog, config_id in ((cursor, cursor.model_config_id),
                                   (grok, grok.model_config_id)):
            row = {"value": "grok-4.7", "quotaPool": "cursor-cli:cursor-models",
                   "quotaPoolStatus": "unmapped"}
            self.quota.annotate_config_options(
                [{"id": config_id, "options": [row]}], catalog)
            self.assertEqual(row["quotaPool"], "cursor-grok")
            self.assertNotIn("quotaPoolStatus", row)
        # ``pool`` is a bare token; a qualified or malformed value refuses
        # at load with the schema route.
        with self.assertRaises(self.quota.QuotaError):
            self.quota.parse_packages(
                '[{"id":"account","name":"X","pool":"a:b"}]')
        with self.assertRaises(self.quota.QuotaError):
            self.quota.parse_packages(
                '[{"id":"account","name":"X","pool":""}]')
        with self.assertRaises(self.quota.QuotaError):
            self.quota.parse_packages(
                '[{"id":"account","name":"X","pool":3}]')


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
               if (not key.startswith("KAOLA_") and not key.endswith("_BIN")) or (key == "KAOLA_LAUNCH_BACKEND" and value == "direct")}
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
        self.assertEqual(droid["packages"][0]["windows"], ["5h", "weekly", "monthly"])
        self.assertEqual(droid["packages"][1]["windows"], ["weekly", "monthly"])
        self.assertEqual(droid["packages"][2]["windows"], [])
        kimi = next(row for row in payload["platforms"] if row["platform"] == "kimi-cli")
        self.assertEqual(
            [(package["id"], package["windows"], package["binds_models"])
             for package in kimi["packages"]],
            [
                ("kimi-cli:managed", ["weekly", "monthly"], True),
                ("kimi-cli:managed_monthly", ["monthly"], False),
            ],
        )
        self.assertFalse(self.record_root.exists())
        self.assertFalse((self.markers / "login-shell-ran").exists())
        self.assertFalse((self.markers / "codex-ran").exists())

    def test_orchestrator_package_examples_match_cli_output(self) -> None:
        # Issue #239: catalog examples and the display rule live in docs/api.md.
        # The installed quota reference keeps the seat-failure rule only.
        reference = (PROJECT / "docs" / "api.md").read_text(encoding="utf-8")
        seat = (PROJECT / "templates" / "orchestrator" / "references"
                / "quota-packages.md").read_text(encoding="utf-8")
        self.assertIn("## Confirmed exhaustion", seat)
        self.assertIn("## Account unavailable", seat)
        self.assertNotIn("```json", seat)
        self.assertNotIn("windows is null until a release seeds one", reference)
        self.assertIn("show the weekly or monthly window when the plan has one", reference)
        self.assertIn("show the 5h window only when it has neither", reference)
        for label, platform in (
            ("One platform:", "grok"),
            ("A platform with several packages:", "droid"),
        ):
            with self.subTest(platform=platform):
                section = reference.split(label, 1)[1]
                example = section.split("```json", 1)[1].split("```", 1)[0].strip()
                result = self.run_cli("packages", "--platform", platform)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(example), json.loads(result.stdout))

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
            "pool": "cursor-grok",
            "status": "mapped",
        })
        unmapped = self.run_cli(
            "model-package", "--platform", "droid", "--model", "brand-new-model",
        )
        self.assertEqual(unmapped.returncode, 0, unmapped.stderr)
        self.assertEqual(json.loads(unmapped.stdout), {
            "schema": "kaola-acp-model-package/1",
            "platform": "droid",
            "model": "brand-new-model",
            "packageId": None,
            "status": "unmapped",
        })
        self.assertFalse(self.record_root.exists())
        self.assertFalse((self.markers / "login-shell-ran").exists())

    def test_model_package_requires_platform_and_model(self) -> None:
        missing = self.run_cli("model-package", "--platform", "grok")
        self.assertNotEqual(missing.returncode, 0)
        self.assertFalse(self.record_root.exists())

    def _usage_server(self) -> tuple[ThreadingHTTPServer, list[str]]:
        """One fixture server exposing each runtime's own usage route.

        ``/auth/usage`` answers the Cursor usage shape and ``/billing`` the
        Grok billing shape; both carry the same shared-pool numbers so the
        two independent acquisitions can be compared for agreement.
        """
        hits: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                hits.append(self.path)
                if self.path == "/auth/usage":
                    body = {
                        "grok": {"numRequests": 30, "numRequestsTotal": 30,
                                 "numTokens": 4100, "maxRequestUsage": 300},
                        "startOfMonth": "2026-10-01T00:00:00Z",
                    }
                elif self.path == "/billing?format=credits":
                    body = {"config": {
                        "includedUsed": 30, "monthlyLimit": 300,
                        "creditUsagePercent": 10.0,
                        "currentPeriod": {"end": 1793491200000},
                        "isUnifiedBillingUser": True,
                    }}
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                encoded = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args: object) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.base = f"http://127.0.0.1:{server.server_address[1]}"  # type: ignore[attr-defined]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, hits

    def test_issue_368_each_runtime_has_own_acquisition(self) -> None:
        """Issue #368: ``--probe`` runs each runtime's own acquisition.

        The Cursor runtime reads Cursor usage (``/auth/usage`` on its own
        endpoint, ``CURSOR_API_KEY``); the Grok runtime reads Grok billing
        (``/billing?format=credits`` on its own endpoint, ``GROK_API_KEY`` or
        the ``grok login`` session key). Neither spawns a binary, derives
        from the other, or needs the other's credentials.
        """
        server, hits = self._usage_server()
        try:
            env = self.env()
            env["CURSOR_API_KEY"] = "fixture-cursor-key-368-not-secret"
            env["GROK_API_KEY"] = "fixture-grok-key-368-not-secret"
            env["CURSOR_API_ENDPOINT"] = server.base  # type: ignore[attr-defined]
            env["GROK_WEB_BASE_URL"] = server.base  # type: ignore[attr-defined]
            for platform in ("cursor-cli", "grok"):
                result = subprocess.run(
                    [sys.executable, str(QUOTA_PATH), "--platform", platform,
                     "--model", "grok-4.7", "--probe"],
                    capture_output=True, text=True, timeout=60, env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                usage = payload["usage"]
                self.assertEqual(usage["platform"], platform)
                self.assertEqual(usage["status"], "ok", payload)
                self.assertEqual(usage["pool"], "cursor-grok")
                self.assertNotIn("command", usage)
            self.assertFalse(self.record_root.exists())
        finally:
            server.shutdown()
        self.assertEqual(sorted(hits), ["/auth/usage", "/billing?format=credits"])

    def test_issue_368_two_acquisitions_agree(self) -> None:
        """Issue #368: with both available, the two readings agree.

        Each acquisition is invoked against its own route on the fixture
        server; the normalized shared-pool numbers (``pool``, ``used``,
        ``limit``, ``used_percent``, ``reset_at``) must match — two real
        reads of one pool, not one read echoed.
        """
        quota = load(QUOTA_PATH, "kaola_quota_368_agree")
        server, _hits = self._usage_server()
        try:
            cursor = quota.probe_cursor_usage(
                model="grok-4.7", timeout=5.0,
                env={"CURSOR_API_KEY": "fixture-cursor-key-368-not-secret",
                     "CURSOR_API_ENDPOINT": server.base,  # type: ignore[attr-defined]
                     "HOME": str(self.record_root)},
            )
            grok = quota.probe_grok_usage(
                model="grok-4.7", timeout=5.0,
                env={"GROK_API_KEY": "fixture-grok-key-368-not-secret",
                     "GROK_WEB_BASE_URL": server.base,  # type: ignore[attr-defined]
                     "HOME": str(self.record_root)},
            )
        finally:
            server.shutdown()
        self.assertEqual(cursor["status"], "ok", cursor)
        self.assertEqual(grok["status"], "ok", grok)
        self.assertEqual(cursor["pool"], grok["pool"])
        for field in ("used", "limit", "used_percent", "remaining_percent",
                      "reset_at"):
            self.assertEqual(cursor["quota"][field], grok["quota"][field], field)

    def test_issue_368_cursor_needs_no_grok_install(self) -> None:
        """Issue #368: the Cursor value needs no Grok build.

        With every Grok credential surface absent (no ``GROK_API_KEY``, no
        ``~/.grok``) the Cursor acquisition still reads its own endpoint;
        the Grok acquisition honestly reports ``key_missing`` in that env.
        """
        quota = load(QUOTA_PATH, "kaola_quota_368_nogrok")
        server, _hits = self._usage_server()
        try:
            env = {"CURSOR_API_KEY": "fixture-cursor-key-368-not-secret",
                   "CURSOR_API_ENDPOINT": server.base,  # type: ignore[attr-defined]
                   "HOME": str(self.record_root),
                   "PATH": "/usr/bin:/bin"}
            cursor = quota.probe_cursor_usage(model="grok-4.7", timeout=5.0, env=env)
            grok = quota.probe_grok_usage(model="grok-4.7", timeout=5.0, env=env)
        finally:
            server.shutdown()
        self.assertEqual(cursor["status"], "ok", cursor)
        self.assertEqual(cursor["pool"], "cursor-grok")
        self.assertEqual(cursor["quota"]["used"], 30.0)
        self.assertNotIn("command", cursor)
        self.assertEqual(grok["status"], "key_missing")
        self.assertFalse(self.record_root.exists())

    def test_issue_368_packages_mark_one_shared_pool(self) -> None:
        """Issue #368: both rows name the shared pool, the split is gone.

        ``packages`` presents each runtime's own id with the same ``pool``
        marker — the view's one shared pool — and no row names the removed
        ``cursor-models``/``other-models`` packages.
        """
        result = self.run_cli("packages")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertNotIn("cursor-models", result.stdout)
        self.assertNotIn("other-models", result.stdout)
        expected = {
            "cursor-cli": "cursor-cli:account",
            "grok": "grok:account",
        }
        for platform, package_id in expected.items():
            row = next(r for r in payload["platforms"] if r["platform"] == platform)
            self.assertEqual(
                row["packages"],
                [{"id": package_id, "name": "Cursor+Grok account usage",
                  "windows": ["monthly"], "binds_models": True,
                  "pool": "cursor-grok"}],
            )


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
                   if not key.startswith("KAOLA_") or (key == "KAOLA_LAUNCH_BACKEND" and value == "direct")}
            env["KAOLA_ACP_RECORD_ROOT"] = str(records)
            # Issue #200: opencode's default tier pins the model, so a plain
            # start applies it; the agent reports the same native options.
            env["MOCK_ACP_CONFIG"] = json.dumps(
                {"new": native, "set_result": {"configOptions": native}})
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
