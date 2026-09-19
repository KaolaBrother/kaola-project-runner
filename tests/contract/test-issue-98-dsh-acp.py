#!/usr/bin/env python3
"""Issue #98: dsh as the tenth worker, and the two shared receipt fixes it forced.

dsh is the first platform whose ACP ``model`` option values are JSON arrays
serialized as strings (``["deepseek-official","deepseek-v4-pro"]``) and the
first whose select options are **grouped** by provider. Both shapes broke
receipt code that every platform shares, so the two repairs are pinned here
rather than resting on one live smoke:

* ``kaola-acp.py::acp_value_params`` read a value bracketed end to end as a
  trailing ``[k=v,...]`` descriptor;
* ``kaola-acp-holder.py`` read ``value`` off a group entry, which carries none.

Both functions had no test reference at all before this file. The manifest
assertions below are the measured facts from
``kaola-workflow/issue-98/evidence/`` (raw frames in ``evidence/raw/``), not
restatements of the manifest; each one fails if a future dsh build changes and
the manifest is edited to follow without re-measuring.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
MANIFEST = PROJECT / "platforms" / "dsh.yaml"
ADAPTER = SCRIPTS / "adapters" / "dsh.sh"
SKILL = PROJECT / "skills" / "dsh-kaola-project-runner"


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^([a-z_]+):\s*"(.*)"\s*$', line)
        if match:
            values[match.group(1)] = json.loads(f'"{match.group(2)}"')
    return values


class AcpValueParamsRejectsAWholeValueBracket(unittest.TestCase):
    """A descriptor qualifies a base value, so it can never be the whole value."""

    def setUp(self) -> None:
        self.acp = load("kaola-acp")

    def test_cursor_descriptor_still_parses(self) -> None:
        """The only real user of the feature must not regress."""
        self.assertEqual(
            self.acp.acp_value_params("grok-4.6[effort=high,fast=true]"),
            {"effort": "high", "fast": "true"},
        )

    def test_dsh_json_array_declares_nothing(self) -> None:
        self.assertEqual(
            self.acp.acp_value_params('["deepseek-official","deepseek-v4-pro"]'), {}
        )

    def test_a_json_array_never_forges_a_fast_declaration(self) -> None:
        """The consequential case: ``declared_fast`` is inferred from this map, so a
        value whose text merely contains ``fast=true`` must not assert native Fast."""
        self.assertEqual(self.acp.acp_value_params('["vendor","model-fast=true"]'), {})

    def test_plain_and_empty_values_are_unchanged(self) -> None:
        for value in ("auto", "deepseek-v4-pro", "", "grok-4.6"):
            with self.subTest(value=value):
                self.assertEqual(self.acp.acp_value_params(value), {})

    def test_every_mapped_dsh_value_declares_nothing(self) -> None:
        for value in manifest_values()["acp_model_map"].split(";"):
            _key, _, mapped = value.partition("=")
            with self.subTest(value=mapped):
                self.assertEqual(self.acp.acp_value_params(mapped), {})


class GroupedSelectOptionsAreFlattenedOnce(unittest.TestCase):
    """The ACP schema nests exactly one level: a list of options OR a list of groups."""

    GROUPED = {
        "id": "model",
        "options": [
            {"group": "deepseek-official", "name": "DeepSeek",
             "options": [{"value": '["deepseek-official","deepseek-v4-pro"]', "name": "Pro"}]},
            {"group": "opencode-go", "name": "OpenCode Go",
             "options": [{"value": '["opencode-go","deepseek-v4.1-flash"]', "name": "Flash"}]},
        ],
    }
    FLAT = {"id": "reasoning_effort",
            "options": [{"value": "off", "name": "Off"}, {"value": "high", "name": "High"}]}

    def setUp(self) -> None:
        self.holder = load("kaola-acp-holder")

    def test_grouped_values_are_the_leaf_routes_in_order(self) -> None:
        self.assertEqual(
            self.holder.config_option_values(self.GROUPED),
            ['["deepseek-official","deepseek-v4-pro"]', '["opencode-go","deepseek-v4.1-flash"]'],
        )

    def test_grouped_choices_keep_their_human_names(self) -> None:
        """This is what the ``set_config_option`` receipt's ``value_name`` comes from."""
        self.assertEqual(
            [choice["name"] for choice in self.holder.config_option_choices(self.GROUPED)],
            ["Pro", "Flash"],
        )

    def test_flat_options_are_untouched(self) -> None:
        """Nine platforms are flat; their receipts must not change shape."""
        self.assertEqual(self.holder.config_option_values(self.FLAT), ["off", "high"])
        self.assertEqual(
            [choice["name"] for choice in self.holder.config_option_choices(self.FLAT)],
            ["Off", "High"],
        )

    def test_a_group_never_becomes_a_nameless_choice(self) -> None:
        """The actual defect: the old reader emitted one ``None`` per group."""
        self.assertNotIn(None, self.holder.config_option_values(self.GROUPED))

    def test_degenerate_shapes_yield_nothing_rather_than_null(self) -> None:
        for label, option in (
            ("no options key", {"id": "x"}),
            ("empty group", {"id": "x", "options": [{"group": "g", "options": []}]}),
            ("entry with no value", {"id": "x", "options": [{"name": "orphan"}]}),
            ("non-dict entries", {"id": "x", "options": ["nope", None, 3]}),
        ):
            with self.subTest(shape=label):
                self.assertEqual(self.holder.config_option_values(option), [])

    def test_the_set_config_option_receipt_uses_the_same_flattening(self) -> None:
        """Both sites, not just the probe: a grouped platform kept losing
        ``value_name`` from its selection receipt while the probe was already fixed."""
        source = (SCRIPTS / "kaola-acp-holder.py").read_text(encoding="utf-8")
        evidence = source.split("def op_set_config_option", 1)[1].split("\n    def ", 1)[0]
        self.assertIn("config_option_choices(option)", evidence)
        self.assertNotRegex(
            evidence,
            r'for choice in option\.get\("options"\)',
            "the selection receipt must not walk raw options: a group carries no value",
        )


class DshManifestMatchesTheMeasuredSurface(unittest.TestCase):
    """Each assertion names a frame in kaola-workflow/issue-98/evidence/raw/."""

    def setUp(self) -> None:
        self.values = manifest_values()

    def test_the_acp_peer_is_dsh_itself_with_no_wrapper(self) -> None:
        self.assertEqual(self.values["acp_command"], "dsh --profile acp")
        self.assertEqual(self.values["acp_wrapper_pin"], "")
        self.assertEqual(self.values["default_transport"], "acp")
        self.assertFalse(list(SKILL.glob("scripts/kaola-dsh-acp.py")))
        self.assertFalse((SKILL / "scripts" / "vendor").exists())

    def test_no_mode_option_so_no_skip_all_entry(self) -> None:
        """handshake.txt: session/new declares model and reasoning_effort only."""
        self.assertEqual(self.values["acp_mode_config_id"], "")
        acp = load("kaola-acp")
        self.assertNotIn("dsh", acp.ACP_SKIP_MODE)
        self.assertNotIn("dsh", acp.ACP_MODE_VALUE_MAP)

    def test_continue_is_refused_not_advertised(self) -> None:
        """resume.txt: session/list entries carry sessionId and cwd, no updatedAt,
        so latest_session() cannot order them."""
        self.assertEqual(self.values["continue_syntax"], "unsupported")
        holder = load("kaola-acp-holder")
        undated = [{"sessionId": "a", "cwd": "/x"}, {"sessionId": "b", "cwd": "/x"}]
        self.assertEqual(holder.latest_session(undated)[0], None)
        self.assertEqual(holder.latest_session(undated[:1])[0], None)

    def test_resume_rides_the_capability_branch_not_session_load(self) -> None:
        """handshake.txt: sessionCapabilities {close,list,resume}; session/load -32601."""
        holder = load("kaola-acp-holder")
        caps = {"close": {}, "list": {}, "resume": {}}
        self.assertTrue(holder.capability_supported(caps, "resume"))
        self.assertFalse(holder.capability_supported({"mcpCapabilities": {"http": True}},
                                                     "loadSession"))
        self.assertIn("session/resume", self.values["resume_syntax"])

    def test_native_steering_unsupported_with_its_evidence(self) -> None:
        """method-surface.txt: all four candidate methods answer -32601."""
        self.assertEqual(self.values["native_steering"], "unsupported")
        self.assertEqual(self.values["acp_steer_method"], "")
        self.assertIn("-32601", self.values["steering_summary"])
        self.assertIn("0.1.5-rc.2", self.values["steering_summary"])

    def test_model_map_values_are_well_formed_two_element_routes(self) -> None:
        """set_config_option only accepts the agent's own [provider, model] strings."""
        entries = manifest_values()["acp_model_map"].split(";")
        self.assertEqual(len(entries), 8)
        for entry in entries:
            key, separator, value = entry.partition("=")
            with self.subTest(entry=key):
                self.assertTrue(separator, entry)
                route = json.loads(value)
                self.assertIsInstance(route, list)
                self.assertEqual(len(route), 2)
                self.assertEqual(key, f"{route[0]}/{route[1]}")

    def test_verified_versions_name_the_launcher_and_the_agent_separately(self) -> None:
        """agentInfo is deepseek-harness-acp/0.0.1 while the CLI is 0.1.5-rc.2."""
        versions = self.values["acp_verified_versions"]
        self.assertIn("cli=0.1.5-rc.2", versions)
        self.assertIn("deepseek-harness-acp/0.0.1", versions)
        self.assertIn("protocol=1", versions)


class DshIsRegisteredEverywhereAPlatformMustBe(unittest.TestCase):
    """The mechanical half of adding a platform: one missed roster is a real defect."""

    def test_every_python_roster_carries_dsh(self) -> None:
        for name, attribute in (("kaola-acp", "PLATFORMS"),
                                ("kaola-locate", "WORKER_IDS"),
                                ("kaola-grok-bot-verify", "WORKER_IDS")):
            with self.subTest(module=name):
                self.assertIn("dsh", getattr(load(name), attribute))

    def test_the_model_policy_probe_table_is_total(self) -> None:
        """probes_for is a bare dict lookup: a missing id is a KeyError, not a default."""
        policy = load("kaola-model-policy")
        self.assertEqual(policy.probes_for("dsh"), [["--version"]])

    def test_the_shell_entrypoint_and_installer_accept_dsh(self) -> None:
        tmux = (SCRIPTS / "kaola-tmux.sh").read_text(encoding="utf-8")
        self.assertRegex(tmux, r'case "\$platform" in [^)]*\bdsh\b[^)]*\)')
        installer = (SCRIPTS / "install-local.sh").read_text(encoding="utf-8")
        self.assertIn("dsh) printf '%s\\n' 'dsh-kaola-project-runner' ;;", installer)
        self.assertRegex(installer, r"selection=\([^)]*\bdsh\b[^)]*\)")

    def test_the_generated_skill_exists_and_ships_its_own_adapter(self) -> None:
        self.assertTrue((SKILL / "SKILL.md").is_file())
        self.assertEqual(
            (SKILL / "scripts" / "adapters" / "dsh.sh").read_bytes(),
            ADAPTER.read_bytes(),
        )


class TheAdapterNeverWritesUnderDshHome(unittest.TestCase):
    """The run's binding constraint, enforced on the source rather than trusted."""

    def test_dsh_home_is_only_ever_read(self) -> None:
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("dsh_home=", source)
        for line in source.splitlines():
            if "dsh_home" not in line or line.lstrip().startswith("#"):
                continue
            with self.subTest(line=line.strip()):
                self.assertNotRegex(
                    line, r"(?:>|>>|mkdir|cp |mv |rm |touch|install |tee)\s*\S*\$\{?dsh_home",
                    "the adapter must never write under $DSH_HOME",
                )

    def test_the_adapter_does_not_create_a_profile(self) -> None:
        """The comment may explain why creating one is refused; no code may do it."""
        source = ADAPTER.read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.lstrip().startswith("#"):
                continue
            self.assertNotIn("--from-default-profile", line,
                             "creating a profile writes under $DSH_HOME and is an operator act")


if __name__ == "__main__":
    unittest.main()
