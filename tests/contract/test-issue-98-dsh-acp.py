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
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
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


# Issue #120: a dsh Host runs its model shell tool under macOS Seatbelt
# (``DSH_PERMISSION_MODE`` default ``workspace-write``) and every Runner process
# started from that shell inherits it. The profile below is the shape dsh
# applies: everything allowed except writes outside the named roots.
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
CLI = SCRIPTS / "kaola-acp.py"


def seatbelt_profile(denied: Path) -> str:
    """Any Seatbelt profile denies the setuid ``/bin/ps`` exec; this one also
    denies writes under the agent's home, as dsh's denies ``~/.dsh``."""
    return f'(version 1) (allow default) (deny file-write* (subpath "{os.path.realpath(denied)}"))'


@unittest.skipUnless(sys.platform == "darwin" and os.access(SANDBOX_EXEC, os.X_OK),
                     "Seatbelt is macOS-only")
class Issue120RunnerUnderAHostSeatbelt(unittest.TestCase):
    """The #119 failure: a worker started from a dsh Host's confined shell died
    at boot with EPERM and the receipt said only ``agent-exited``; its exact
    stop then crashed because the setuid ``/bin/ps`` cannot exec there."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i120-")
        self.root = Path(os.path.realpath(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        # The agent's home is not writable under the profile, like ~/.dsh.
        self.home = self.root / "home"
        self.home.mkdir()
        self.session = f"dsh-i120-{self._testMethodName[-24:].lower()}-{os.getpid()}"

    def cli(self, command: str, *args: str, agent: str = "", confined: bool = True) -> dict:
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.root / "records")
        argv = [sys.executable, str(CLI), "dsh", command, "--repo", str(self.repo),
                "--session", self.session, *args]
        if agent:
            argv += ["--command", agent]
        if confined:
            argv = [SANDBOX_EXEC, "-p", seatbelt_profile(self.home), *argv]
        result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=60)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def own_pids(self) -> list[int]:
        out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True)
        return [int(line.split(None, 1)[0]) for line in out.stdout.splitlines()
                if self.session in line or str(self.root) in line]

    def cleanup_session(self) -> None:
        """Stop from outside the sandbox; kill whatever a broken stop left."""
        self.cli("stop", "--force", confined=False)
        for pid in self.own_pids():
            try:
                os.kill(pid, 9)
            except OSError:
                pass

    def boot_writer(self) -> str:
        """An agent that, like ``dsh --profile acp``, rewrites a file under its
        own home before speaking ACP."""
        script = self.root / "boot-writer.py"
        target = self.home / "profiles" / "acp" / "cordis.yml"
        target.parent.mkdir(parents=True)
        script.write_text(
            "import sys\n"
            f"open({str(target)!r}, 'w').write('{{}}\\n')\n"
            f"import runpy; sys.argv = [{str(MOCK)!r}]; runpy.run_path({str(MOCK)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        return f"{sys.executable} {script}"

    def test_a_confined_boot_write_failure_names_its_cause(self) -> None:
        self.addCleanup(self.cleanup_session)
        receipt = self.cli("start", agent=self.boot_writer())
        self.assertEqual(receipt.get("state"), "error", receipt)
        error = receipt["error"]
        self.assertEqual(error.get("code"), "acp-initialize-failed")
        self.assertIs(error.get("seatbelt_confined"), True)
        tail = "\n".join(error.get("stderr_tail") or [])
        self.assertIn("Operation not permitted", tail)
        self.assertIn("cordis.yml", tail)

    def test_the_same_agent_starts_unconfined(self) -> None:
        """The control: nothing about the agent itself fails."""
        self.addCleanup(self.cleanup_session)
        receipt = self.cli("start", agent=self.boot_writer(), confined=False)
        self.assertEqual(receipt.get("state"), "ready", receipt)

    def test_an_unconfined_start_failure_reports_false(self) -> None:
        self.addCleanup(self.cleanup_session)
        receipt = self.cli("start", agent=f"{sys.executable} -c 'import sys; sys.exit(1)'",
                           confined=False)
        self.assertIs(receipt["error"].get("seatbelt_confined"), False)

    def test_exact_stop_works_inside_the_sandbox(self) -> None:
        self.addCleanup(self.cleanup_session)
        started = self.cli("start", agent=f"{sys.executable} {MOCK}")
        self.assertEqual(started.get("state"), "ready", started)
        stopped = self.cli("stop", "--force")
        self.assertIs(stopped.get("stopped"), True, stopped)
        self.assertEqual(stopped.get("residual_pids"), [])
        for pid in (started["holder_pid"], started["agent_pid"]):
            with self.subTest(pid=pid):
                self.assertFalse(self._alive(pid))

    @staticmethod
    def _alive(pid: int) -> bool:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            time.sleep(0.1)
        return True


@unittest.skipUnless(sys.platform == "darwin", "libproc is macOS-only")
class Issue120ProcessTableWithoutPs(unittest.TestCase):
    """When ``ps`` cannot exec, both scripts read the same columns from libproc."""

    def test_libproc_rows_match_ps(self) -> None:
        pid = os.getpid()
        real = subprocess.run(["ps", "-o", "pid=,ppid=,pgid=,lstart=", "-p", str(pid)],
                              capture_output=True, text=True,
                              env={**os.environ, "LC_ALL": "C"}).stdout.split()
        for name in ("kaola-acp", "kaola-acp-holder"):
            module = load(name)
            with self.subTest(script=name), mock.patch.object(
                    module.subprocess, "run", side_effect=PermissionError(1, "denied")):
                result = module.run_ps(["pid", "ppid", "pgid", "state", "lstart"])
                self.assertEqual(result.returncode, 0)
                rows = {line.split(None, 1)[0]: line.split() for line in result.stdout.splitlines()}
                row = rows[str(pid)]
                self.assertEqual(row[:3], real[:3])
                self.assertEqual(row[4:], real[3:])


if __name__ == "__main__":
    unittest.main()
