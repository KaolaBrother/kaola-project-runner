#!/usr/bin/env python3
"""Issue #111: the live-verified model presets; Issue #188: per-runtime named tiers.

Every id asserted here was read from the live ACP catalog on 2026-09-21
(``initialize`` -> ``session/new`` -> ``configOptions``, read-only), and the
whole point of pinning them is that a future manifest edit that *follows* a
catalog change without re-measuring fails loudly instead of silently starting
a worker on a different model.

Three separate things are pinned:

* the five re-pointed presets, on **both** declarations -- ``platforms/*.yaml``
  feeds the ACP path through ``kaola-acp.py`` and ``scripts/adapters/*.sh``
  still carries the same preset facts (the retired PTY path used to read them,
  Issue #130), and nothing but this test makes the two agree;
* the named presets (Issue #188: only ``default`` is common; every other word
  is the runtime's own, listed in ``named_tiers``): each resolves where
  declared and is **absent** from the generated output of platforms that
  declare none, while an undeclared tier is a typed refusal rather than a
  quiet fallback to ``default``;
* two tolerances that are load-bearing but invisible: ZCode's ``thought`` vs
  live ``thoughtLevel`` config id, and the equality of ``platforms/zcode.yaml``
  with the Issue #108 Host constants -- the issue requires one source of truth,
  and this assertion is what makes the duplication safe.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"
SKILLS = PROJECT / "skills"

# The live catalog read recorded in Issue #111, with the Issue #188 tier words
# and display names (effort is shown separately). `effort` is the Runner preset
# effort, which is empty where no effort was verified for that exact model.
LIVE_PRESETS = {
    "kimi-cli": {
        "default": ("Kimi K3", "kimi-code/k3", "max"),
        "named": [("kimi-k2-8", "Kimi K2.8", "kimi-code/kimi-for-coding", "max")],
    },
    "droid": {
        # Issue #125 (correcting #117): default is Auto; the alternative tier
        # stays deleted. Issue #188 adds opus beside the existing core.
        "default": ("Auto Model", "auto", ""),
        "named": [("opus", "Opus 5.5", "claude-opus-5-5", "medium"),
                  ("core", "Kimi K3", "kimi-k3", "max")],
    },
    "dsh": {
        "default": ("DeepSeek V4.1 Flash", "opencode-go/deepseek-v4.1-flash", ""),
        "named": [],
    },
    "zcode": {
        "default": ("GLM 5.3", "GLM-5.3", "max"),
        "named": [],
    },
    "devin": {
        "default": ("SWE-2", "swe-2-max", ""),
        # Issue #144: `fable` is the Fable fusion; the pure
        # claude-fable-5-1-high preset is retired.
        # Issue #237: display names drop the encoded effort; launch effort stays empty.
        "named": [("opus-fusion", "Opus Fusion",
                   "fusion-claude-opus-5-5-medium-sidekick-swe-2-medium", ""),
                  ("fable", "Fable Fusion",
                   "fusion-claude-fable-5-1-high-sidekick-swe-2-medium", "")],
    },
}

ALL_PLATFORMS = sorted(path.stem for path in PLATFORMS.glob("*.yaml"))
THOUGHT_SPELLINGS = ("thought", "thoughtLevel", "thought_level")


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def named(values: dict[str, str]) -> list[str]:
    return [word for word in values["named_tiers"].split(",") if word]


def key(word: str) -> str:
    return word.replace("-", "_")


def manifest(platform: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PLATFORMS / f"{platform}.yaml").read_text(encoding="utf-8").splitlines():
        match = re.match(r'^([a-z0-9_]+):\s*(".*")\s*$', line)
        if match:
            values[match.group(1)] = json.loads(match.group(2))
    return values


def adapter(platform: str) -> dict[str, str]:
    values: dict[str, str] = {}
    text = (SCRIPTS / "adapters" / f"{platform}.sh").read_text(encoding="utf-8")
    for match in re.finditer(r'^(ADAPTER_[A-Z0-9_]+)="(.*)"$', text, re.M):
        values[match.group(1)] = match.group(2)
    return values


def run_acp(platform: str, *extra: str) -> tuple[int, dict[str, Any]]:
    """`kaola-acp.py preflight` in this checkout, with the host's ZCode and
    dispatcher env stripped so a live Host cannot leak into the result."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE", "KAOLA_ACP_DISPATCHER")}
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "kaola-acp.py"), platform, "preflight",
         "--repo", str(PROJECT), *extra],
        capture_output=True, text=True, timeout=120, env=env,
    )
    return proc.returncode, json.loads(proc.stdout)


class LiveVerifiedPresets(unittest.TestCase):
    """Each re-pointed preset names the exact id read from the live catalog."""

    def test_manifest_pins_the_measured_default(self) -> None:
        for platform, presets in LIVE_PRESETS.items():
            name, model_id, effort = presets["default"]
            with self.subTest(platform=platform):
                values = manifest(platform)
                self.assertEqual(values["default_model_name"], name)
                self.assertEqual(values["default_model_id"], model_id)
                self.assertEqual(values["default_model_effort"], effort)

    def test_manifest_pins_the_measured_named_tiers(self) -> None:
        for platform, presets in LIVE_PRESETS.items():
            with self.subTest(platform=platform):
                values = manifest(platform)
                self.assertEqual(named(values), [word for word, *_ in presets["named"]])
                for word, name, model_id, effort in presets["named"]:
                    self.assertEqual(values[f"{key(word)}_model_name"], name)
                    self.assertEqual(values[f"{key(word)}_model_id"], model_id)
                    self.assertEqual(values[f"{key(word)}_model_effort"], effort)

    def test_droid_needs_no_model_map_for_its_first_class_id(self) -> None:
        """`auto` and `kimi-k3` are real Droid catalog ids, so nothing is hardcoded."""
        self.assertEqual(manifest("droid")["acp_model_map"], "")

    def test_dsh_default_is_already_carried_by_the_model_map(self) -> None:
        """The ACP wire value is the JSON pair, and the map was already right."""
        acp = load("kaola-acp")
        mapping = acp.parse_acp_model_map(manifest("dsh")["acp_model_map"])
        self.assertEqual(
            mapping["opencode-go/deepseek-v4.1-flash"],
            '["opencode-go","deepseek-v4.1-flash"]',
        )

    def test_droid_launch_summary_names_auto_default_and_no_alternative(self) -> None:
        """Issue #125/#188: the summary states the Auto default, opus, and K3 core."""
        summary = manifest("droid")["launch_summary"]
        # Issue #130 dropped the PTY launch clause that spelled "default Auto
        # Model"; the ACP clause states the same default.
        self.assertIn("The default preset is the first-class catalog id auto", summary)
        self.assertNotIn("--skip-permissions-unsafe", summary)
        self.assertIn("--tier core is the first-class catalog id kimi-k3", summary)
        self.assertNotIn("--tier upgrade", summary)
        for leftover in ("kimi-k2.7", "K2.7", "K2.8", "alternative"):
            self.assertNotIn(leftover, summary)

    def test_dsh_records_the_runner_side_display_name(self) -> None:
        """"DeepSeek V4.1 Flash" is ours; the catalog's is bare."""
        summary = manifest("dsh")["launch_summary"]
        self.assertIn("Runner-side display name", summary)
        self.assertIn("deepseek-v4.1-flash", summary)


class ManifestAndAdapterAgree(unittest.TestCase):
    """Two transports, two declarations of the same preset, one meaning.

    `kaola-acp.py` reads `platforms/*.yaml`; `scripts/adapters/*.sh` carries
    the same preset facts (read by the PTY path until Issue #130 retired it).
    Nothing else makes them agree, so a skew is still pinned here.
    """

    def test_every_platform_declares_the_same_presets_on_both_paths(self) -> None:
        for platform in ALL_PLATFORMS:
            values, flags = manifest(platform), adapter(platform)
            self.assertEqual(flags["ADAPTER_NAMED_TIERS"], values["named_tiers"])
            for tier in ("default", *named(values)):
                with self.subTest(platform=platform, tier=tier):
                    for field in ("NAME", "ID", "EFFORT"):
                        self.assertEqual(flags[f"ADAPTER_{key(tier).upper()}_MODEL_{field}"],
                                         values[f"{key(tier)}_model_{field.lower()}"])
            self.assertFalse([flag for flag in flags
                              if flag.startswith(("ADAPTER_UPGRADE_", "ADAPTER_ALT_"))])


class NamedTiersAreOptional(unittest.TestCase):
    """A platform that declares no named tier shows no trace of one."""

    def test_render_rejects_a_word_without_a_model(self) -> None:
        render = load("render-skills")
        values = manifest("opencode") | {"named_tiers": "alternative"}
        with self.assertRaises(ValueError):
            self._reparse(render, values)

    def test_render_rejects_a_model_without_a_word(self) -> None:
        render = load("render-skills")
        values = manifest("opencode") | {"orphan_model_id": "orphan-model"}
        with self.assertRaises(ValueError):
            self._reparse(render, values)

    def _reparse(self, render: Any, values: dict[str, str]) -> None:
        """Round-trip a manifest through the real parser, shape checks included."""
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"{values['id']}.yaml"
            path.write_text("".join(f"{k}: {json.dumps(v)}\n" for k, v in values.items()),
                            encoding="utf-8")
            render.parse_manifest(path)

    def test_generated_skills_list_exactly_the_declared_tiers(self) -> None:
        for platform in ALL_PLATFORMS:
            values = manifest(platform)
            skill = SKILLS / f"{platform}-kaola-project-runner"
            body = (skill / "SKILL.md").read_text(encoding="utf-8")
            reference = (skill / "references" / "platform.md").read_text(encoding="utf-8")
            with self.subTest(platform=platform):
                declared = ["default", *named(values)]
                self.assertEqual(re.findall(r"Runner (\S+) preset", reference), declared)
                for tier in declared:
                    self.assertIn(f"`--tier {tier}`", body)
                self.assertNotIn("--tier upgrade", body + reference)


class TierAgentCommand(unittest.TestCase):
    """Issue #140: devin's presets ride the spawn argv; every other platform
    keeps its base acp_command for every tier."""

    DEVIN = {
        "default": "devin acp --model swe-2-max",
        "opus-fusion": "devin acp --model fusion-claude-opus-5-5-medium-sidekick-swe-2-medium",
        "fable": "devin acp --model fusion-claude-fable-5-1-high-sidekick-swe-2-medium",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load("kaola-acp")

    def args(self, platform: str, **overrides: Any) -> Any:
        import argparse
        values = {"model": None, "effort": None, "tier": None, "resume": None,
                  "use_continue": False} | overrides
        return argparse.Namespace(manifest=manifest(platform), **values)

    def test_devin_tier_commands_carry_the_original_preset_ids(self) -> None:
        values = manifest("devin")
        self.assertEqual(values["acp_command"], "devin acp")
        for tier, command in self.DEVIN.items():
            with self.subTest(tier=tier):
                self.assertEqual(self.acp.tier_agent_command(self.args("devin", tier=tier)), command)
                prefix = self.acp.tier_prefix(values, tier)
                self.assertEqual(self.acp.argv_model(command), values[f"{prefix}_model_id"])
        self.assertEqual(self.acp.tier_agent_command(self.args("devin")), self.DEVIN["default"])

    def test_explicit_model_and_preserved_resume_keep_the_base_command(self) -> None:
        self.assertEqual(self.acp.tier_agent_command(
            self.args("devin", tier="opus-fusion", model="swe-1-6")), "")
        self.assertEqual(self.acp.tier_agent_command(
            self.args("devin", resume="sess-1")), "")
        self.assertEqual(self.acp.tier_agent_command(
            self.args("devin", use_continue=True, tier="opus-fusion")), self.DEVIN["opus-fusion"])

    def test_other_platforms_are_unchanged(self) -> None:
        for platform in ALL_PLATFORMS:
            if platform == "devin":
                continue
            values = manifest(platform)
            with self.subTest(platform=platform):
                self.assertFalse([k for k in values if k.startswith("acp_command_")])
                self.assertEqual(self.acp.argv_model(values["acp_command"]), "")
                for tier in ("default", *named(values)):
                    self.assertEqual(self.acp.tier_agent_command(self.args(platform, tier=tier)), "")

    def test_render_rejects_empty_or_unlabelled_tier_commands(self) -> None:
        render = load("render-skills")
        for extra in ({"acp_command_default": ""},
                      {"acp_command_fable": "codex-acp --model x"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                NamedTiersAreOptional._reparse(None, render, manifest("opencode") | extra)


class UndeclaredTierIsRefused(unittest.TestCase):
    """The one thing a third tier must never do is quietly become `default`."""

    def test_acp_path_refuses_by_name_and_mutates_nothing(self) -> None:
        # Issue #188: the retired `upgrade` word is as undeclared as any other.
        code, receipt = run_acp("opencode", "--tier", "upgrade")
        self.assertEqual(code, 1)
        self.assertEqual(receipt["result"], "refused")
        self.assertEqual(receipt["reason"], "tier-not-declared")
        self.assertEqual(receipt["requested_tier"], "upgrade")
        self.assertEqual(receipt["available_tiers"], ["default"])
        self.assertFalse(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "not_started")

    def test_a_platform_refuses_another_platforms_tier_word(self) -> None:
        """Droid declares `core`, so devin must not quietly accept it."""
        code, receipt = run_acp("devin", "--tier", "core")
        self.assertEqual(code, 1)
        self.assertEqual(receipt["reason"], "tier-not-declared")
        self.assertEqual(receipt["available_tiers"], ["default", "opus-fusion", "fable"])

    def test_devin_fable_tier_selects_the_fable_fusion(self) -> None:
        """Issue #144: `fable` stays declared, now as the Fable fusion; the
        retired pure claude-fable-5-1-high is no tier's model."""
        acp = load("kaola-acp")
        values = manifest("devin")
        self.assertEqual(acp.tier_prefix(values, "fable"), "fable")
        self.assertEqual(values["fable_model_id"], "fusion-claude-fable-5-1-high-sidekick-swe-2-medium")
        for prefix in ("default", "opus_fusion", "fable"):
            self.assertNotEqual(values[f"{prefix}_model_id"], "claude-fable-5-1-high")

    def test_droid_refuses_its_deleted_alternative_tier(self) -> None:
        """Issue #117: droid no longer declares `alternative`; no silent fallback."""
        code, receipt = run_acp("droid", "--tier", "alternative")
        self.assertEqual(code, 1)
        self.assertEqual(receipt["reason"], "tier-not-declared")
        self.assertEqual(receipt["available_tiers"], ["default", "opus", "core"])
        self.assertFalse(receipt["mutation_performed"])


class BothTransportsResolveTheSamePreset(unittest.TestCase):
    """The ACP transport's preset mapping is pinned deterministically.

    Deliberately not end to end: `preflight` resolution probes the real CLI
    catalog, which takes minutes for the larger catalogs and answers
    differently on a machine where a binary is absent. What is actually at risk
    is the *mapping* -- which manifest keys a `--tier` word selects -- so that is
    what is asserted here, deterministically. The end-to-end refusal is covered
    by `UndeclaredTierIsRefused`, which returns before any probe.
    """

    def test_acp_maps_each_tier_word_onto_its_manifest_keys(self) -> None:
        acp = load("kaola-acp")
        for platform in ALL_PLATFORMS:
            values = manifest(platform)
            with self.subTest(platform=platform):
                self.assertEqual(acp.tier_prefix(values, "default"), "default")
                for word in named(values):
                    self.assertEqual(acp.tier_prefix(values, word), key(word))

    def test_acp_resolves_the_measured_id_for_every_pinned_tier(self) -> None:
        acp = load("kaola-acp")
        for platform, presets in LIVE_PRESETS.items():
            values = manifest(platform)
            with self.subTest(platform=platform, tier="default"):
                prefix = acp.tier_prefix(values, "default")
                self.assertEqual(values[f"{prefix}_model_id"], presets["default"][1])
            for word, _, model_id, effort in presets["named"]:
                with self.subTest(platform=platform, tier=word):
                    prefix = acp.tier_prefix(values, word)
                    self.assertEqual(values[f"{prefix}_model_id"], model_id)
                    self.assertEqual(values[f"{prefix}_model_effort"], effort)


class ZcodeHasOneSourceOfTruth(unittest.TestCase):
    """The Issue #108 Host gate and the ordinary default must not drift apart.

    #108 refuses a Host-shaped session that is not GLM 5.3 at effort max, using
    module constants; Issue #111 pins the same pair as the ordinary preset in
    the manifest. The issue allows the duplication only if a test asserts the
    equality, so this is that test.
    """

    def test_manifest_default_equals_the_host_constants(self) -> None:
        acp = load("kaola-acp")
        values = manifest("zcode")
        self.assertEqual(values["default_model_id"], acp.ZCODE_HOST_MODEL_ID)
        self.assertEqual(values["default_model_effort"], acp.ZCODE_HOST_EFFORT)

    def test_the_default_satisfies_the_host_matcher(self) -> None:
        """Including the provider-qualified live spelling, and not the Flash."""
        acp = load("kaola-acp")
        self.assertTrue(acp.zcode_host_model_match(manifest("zcode")["default_model_id"]))
        self.assertTrue(acp.zcode_host_model_match("builtin:bigmodel-coding-plan\\GLM-5.3"))
        self.assertTrue(acp.zcode_host_model_match("account:plan\\GLM-5.3"))
        self.assertFalse(acp.zcode_host_model_match("builtin:bigmodel-coding-plan\\GLM-5.3-Flash"))


class ZcodeThoughtConfigIdTolerance(unittest.TestCase):
    """The manifest says `thought`; the live agent says `thoughtLevel`.

    Both paths accept either today, which is the only reason the manifest is
    not a bug. A future narrowing of either list would silently stop applying
    or verifying the new GLM 5.3 default, so both lists are pinned here.
    """

    def test_manifest_still_declares_the_tolerated_spelling(self) -> None:
        self.assertIn(manifest("zcode")["acp_effort_config_id"], THOUGHT_SPELLINGS)

    def test_read_path_accepts_every_spelling(self) -> None:
        acp = load("kaola-acp")
        for spelling in THOUGHT_SPELLINGS:
            with self.subTest(config_id=spelling):
                state = {"session_meta": {"configOptions": [
                    {"id": "model", "currentValue": "builtin:x\\GLM-5.3"},
                    {"id": spelling, "currentValue": "max"},
                ]}}
                model, effort = acp.zcode_host_config_state(state)
                self.assertEqual(effort, "max")
                self.assertTrue(acp.zcode_host_model_match(model))

    def test_adapter_write_path_accepts_every_spelling(self) -> None:
        """Read structurally, not by substring: a narrowed tuple must fail."""
        tree = ast.parse((SCRIPTS / "kaola-zcode-acp.py").read_text(encoding="utf-8"))
        accepted: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                continue
            if not isinstance(node.ops[0], ast.In):
                continue
            if not (isinstance(node.left, ast.Name) and node.left.id == "config_id"):
                continue
            for element in getattr(node.comparators[0], "elts", []):
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    accepted.add(element.value)
        self.assertTrue(set(THOUGHT_SPELLINGS) <= accepted,
                        f"kaola-zcode-acp.py narrowed the thought config id to {accepted}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
