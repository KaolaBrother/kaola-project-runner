#!/usr/bin/env python3
"""Issue #236: installation finishes with ACP preparation, not payload verification.

The installer footer is covered by tests/contract/test-installer-runtimes.sh.
This file checks the entry pages, the canonical procedure, and isolated fixtures
for the compact completion rows. It does not install a CLI, log in, restart a
session, or open a live ACP connection.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
API = PROJECT / "docs" / "api.md"
README = PROJECT / "README.md"
GUIDE = PROJECT / "hosts" / "grok-bot" / "INSTALL.md"
GUIDE_TMPL = PROJECT / "templates" / "grok-bot" / "INSTALL.md.tmpl"
HOST_DOC = PROJECT / "docs" / "grok-bot-host.md"
DSH_MANIFEST = PROJECT / "platforms" / "dsh.yaml"
CODEX_MANIFEST = PROJECT / "platforms" / "codex.yaml"
ISSUE_226 = PROJECT / "kaola-workflow" / "archive" / "issue-226" / "finalization-summary.md"
ANCHOR = "docs/api.md#acp-layer-preparation-during-install"
DSH_INSPECT = (
    'const p=require("path"),f=require("fs");let d=p.dirname(process.argv[1]);'
    'for(const n of ["dsh","dsh-acp-app","dsh-acp"]){let m;for(let c=d;!m;c=p.dirname(c)){'
    'const x=p.join(c,"node_modules/@deepseek-ai",n,"package.json");'
    'if(f.existsSync(x))m=x;else if(c===p.dirname(c))break}'
    'if(!m){console.log(n,"not found");break}'
    'console.log(n,JSON.parse(f.readFileSync(m)).version,m);d=p.dirname(m)}'
)


def manifest_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and value.strip():
            values[key.strip()] = json.loads(value.strip())
    return values


def verified_parts(record: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in record.split(";") if "=" in part)


def write_exec(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def write_package(root: Path, name: str, version: str) -> None:
    path = root / "node_modules" / "@deepseek-ai" / name / "package.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": f"@deepseek-ai/{name}", "version": version}) + "\n",
                    encoding="utf-8")


def inspect_dsh(binary: Path) -> dict[str, str]:
    real = os.path.realpath(binary)
    result = subprocess.run(
        ["node", "-e", DSH_INSPECT, real],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    found: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, version, _path = line.split(" ", 2)
        found[name] = version
    return found


def completion_row(
    runtime: str,
    *,
    survey: str,
    component: str,
    observed: str,
    verified: str,
    relation: str,
    agent_info: str = "",
    agent_field: str = "",
    authorization_covers: bool = False,
    shared_live: bool = False,
    launch_override: str = "",
    path_cli: str = "",
    protocol_evidence: bool = False,
    account_limit: str = "",
    unrelated_global_cli: bool = False,
) -> list[str]:
    """Compact installation row. Exact version equality only; no semver ranking.

    ``agent_info`` matching the manifest agent field does not establish a package
    upgrade. A PATH CLI is not an independently pinned ACP pair. This function
    does not install, log in, restart, or contact a model.
    """
    if survey == "absent":
        readiness = ("not-ready: absent; install the named CLI through its supported "
                     "mechanism and rerun; do not install automatically")
        action = "none"
        relation = "absent"
    elif survey == "unknown":
        readiness = "not-ready: unknown"
        action = "none"
        relation = "unknown"
    elif relation == "match" and protocol_evidence:
        readiness = "ready"
        action = "none"
    elif relation == "match":
        readiness = ("not-ready: bounded ACP preflight/start/status/stop still required; "
                     "a transport handshake does not prove model execution")
        action = "none"
    elif relation == "newer-unverified":
        readiness = "not-ready: unverified; do not silently downgrade"
        action = "none"
    elif unrelated_global_cli:
        readiness = "not-ready: the PATH CLI is not the pinned ACP pair"
        action = "none"
    elif shared_live:
        readiness = "not-ready: HUMAN_DECISION_REQUIRED; shared live session; do not restart"
        action = "pending"
    elif not authorization_covers:
        readiness = ("not-ready: HUMAN_DECISION_REQUIRED; authorization does not cover "
                     "this whole-app update")
        action = "pending"
    else:
        readiness = "not-ready: loaded component is not the verified record"
        action = "pending: authorized whole-component update; do not ask again"
    if agent_info and agent_info == agent_field and relation not in ("match", "absent", "unknown"):
        observed = f"{observed};agentInfo={agent_info} does not establish the upgrade"
    if path_cli:
        observed = f"{observed};path_cli={path_cli}"
    if launch_override:
        observed = f"{observed};launch_override={launch_override}"
    lines = [
        f"acp: {runtime} component={component} versions={observed} verified={verified} "
        f"action={action} readiness={readiness}"
    ]
    if account_limit:
        lines.append(f"acp-limit: {runtime} {account_limit}")
    return lines


class InstallEntriesTest(unittest.TestCase):
    def test_readme_finishes_through_the_canonical_procedure(self) -> None:
        install = README.read_text(encoding="utf-8").split("## Select workers", 1)[0]
        self.assertIn(ANCHOR, install)
        self.assertLess(install.index(ANCHOR), install.index("# Native host destinations"))
        self.assertIn("do not\nfinish installation", install)
        self.assertIn("not the only CLI to inspect", install)
        self.assertIn("locator attestation is not this step", install)
        self.assertIn("Registering it does not finish installation", install)

    def test_grok_bot_install_and_update_route_through_the_procedure(self) -> None:
        guide = GUIDE.read_text(encoding="utf-8")
        template = GUIDE_TMPL.read_text(encoding="utf-8")
        for text in (guide, template):
            self.assertEqual(text.count(ANCHOR), 2, text)
            self.assertIn("establishes placement only, not live use", text)
            self.assertIn("Placement does not finish installation", text)
            self.assertIn("Uninstall is not ACP preparation", text)
            self.assertLess(text.index("Placement does not finish"), text.index("## 5. Update"))
            self.assertGreater(text.index("Uninstall is not ACP preparation"), text.index("## 5. Update"))
        host = HOST_DOC.read_text(encoding="utf-8")
        self.assertIn("api.md#acp-layer-preparation-during-install", host)
        self.assertIn("This preflight is placement", host)
        self.assertIn("Uninstall is not that procedure", host)
        self.assertIn("never part of installation", host.lower())

    def test_generated_guide_matches_the_renderer(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "render_skills_236", PROJECT / "scripts" / "render-skills.py")
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        expected = module.expected_grok_bot_host_files()["INSTALL.md"]
        self.assertEqual(GUIDE.read_bytes(), expected)
        self.assertLessEqual(len(expected), module.budgets()["bridge_guide_bytes"])

    def test_canonical_procedure_is_the_required_sequence(self) -> None:
        api = API.read_text(encoding="utf-8")
        section = api.split("### ACP layer preparation during install", 1)[1]
        section = " ".join(section.split("#### DSH loaded ACP harness", 1)[0].split())
        for phrase in (
            "Check each detected in-scope runtime once",
            "not the only worker CLI to inspect",
            "`--platform` narrows",
            "and unknown separately",
            "Do not install an absent CLI automatically",
            "Do not silently downgrade",
            "stays unverified",
            "HUMAN_DECISION_REQUIRED",
            "Do not ask again",
            "do not restart shared live sessions",
            "Do not log in or relogin",
            "Do not fix the OpenCode Go route",
            "`--uninstall` is not this procedure",
            "CODEX_PATH",
            "codex` on `PATH` is a different fact",
            "Call the installation complete only when",
            "No new state file, schema, or ledger",
            "not-ready:",
        ):
            self.assertIn(phrase, section, phrase)
        self.assertNotIn("prepare ACP for an unselected runtime", api)
        self.assertIn("`render-skills.py --verify-install` check Skill payloads only", api)
        self.assertIn("cannot establish an upgrade", api)
        self.assertIn(DSH_INSPECT, api)


class FixtureRowsTest(unittest.TestCase):
    def test_stale_dsh_packages_are_not_ready_and_agentinfo_does_not_upgrade_them(self) -> None:
        dsh = manifest_values(DSH_MANIFEST)
        verified = verified_parts(dsh["acp_verified_versions"])
        self.assertEqual(verified["cli"], "0.1.7-rc.2")
        self.assertEqual(verified["agent"], "deepseek-harness-acp/0.0.1")
        with tempfile.TemporaryDirectory(prefix="kaola-236-dsh-") as tmp:
            root = Path(tmp)
            for name in ("dsh", "dsh-acp-app", "dsh-acp"):
                write_package(root, name, "0.1.5-rc.3")
            binary = root / "node_modules" / "@deepseek-ai" / "dsh" / "bin" / "dsh"
            write_exec(binary, "#!/bin/sh\nprintf '%s\\n' '0.1.5-rc.3'\n")
            loaded = inspect_dsh(binary)
        self.assertEqual(loaded, {"dsh": "0.1.5-rc.3", "dsh-acp-app": "0.1.5-rc.3",
                                   "dsh-acp": "0.1.5-rc.3"})
        observed = ",".join(f"{name}={loaded[name]}" for name in ("dsh", "dsh-acp-app", "dsh-acp"))
        rows = completion_row(
            "dsh", survey="present", component=dsh["acp_command"], observed=observed,
            verified=dsh["acp_verified_versions"], relation="not-verified",
            agent_info=verified["agent"], agent_field=verified["agent"],
            authorization_covers=True,
        )
        text = "\n".join(rows)
        self.assertIn("does not establish the upgrade", text)
        self.assertIn("do not ask again", text)
        self.assertIn("readiness=not-ready:", text)
        self.assertNotIn("readiness=ready", text)
        self.assertNotIn("upgraded", text)
        self.assertNotIn("HUMAN_DECISION_REQUIRED", text)
        self.assertNotIn("npm install", text)  # the row does not carry out the update

    def test_matching_dsh_packages_still_need_bounded_acp_when_the_layer_changed(self) -> None:
        dsh = manifest_values(DSH_MANIFEST)
        verified = verified_parts(dsh["acp_verified_versions"])["cli"]
        with tempfile.TemporaryDirectory(prefix="kaola-236-dsh-match-") as tmp:
            root = Path(tmp)
            for name in ("dsh", "dsh-acp-app", "dsh-acp"):
                write_package(root, name, verified)
            binary = root / "node_modules" / "@deepseek-ai" / "dsh" / "bin" / "dsh"
            write_exec(binary, "#!/bin/sh\nexit 0\n")
            loaded = inspect_dsh(binary)
        self.assertEqual(set(loaded.values()), {verified})
        rows = completion_row(
            "dsh", survey="present", component="dsh --profile acp",
            observed="dsh=0.1.7-rc.2,dsh-acp-app=0.1.7-rc.2,dsh-acp=0.1.7-rc.2",
            verified=dsh["acp_verified_versions"], relation="match",
            protocol_evidence=False,
            account_limit="OpenCode Go route unchanged; not a model-execution proof",
        )
        self.assertTrue(rows[0].endswith(
            "readiness=not-ready: bounded ACP preflight/start/status/stop still required; "
            "a transport handshake does not prove model execution"))
        self.assertIn("OpenCode Go route unchanged", rows[1])
        self.assertNotIn("login", "\n".join(rows).lower())

    def test_codex_pin_is_not_the_path_cli_and_an_override_is_kept(self) -> None:
        codex = manifest_values(CODEX_MANIFEST)
        self.assertIn("@openai/codex@0.158.0", codex["acp_command"])
        self.assertIn("@agentclientprotocol/codex-acp@2.0.0", codex["acp_command"])
        saved = ISSUE_226.read_text(encoding="utf-8")
        self.assertIn("@openai/codex` 0.158.0", saved)
        self.assertIn("@agentclientprotocol/codex-acp` 2.0.0", saved)
        with tempfile.TemporaryDirectory(prefix="kaola-236-codex-") as tmp:
            root = Path(tmp)
            path_cli = root / "bin" / "codex"
            write_exec(path_cli, "#!/bin/sh\nprintf '%s\\n' '0.157.1'\n")
            override = root / "override" / "codex"
            write_exec(override, "#!/bin/sh\nprintf '%s\\n' 'override'\n")
            path_version = subprocess.run([str(path_cli), "--version"], capture_output=True,
                                          text=True, check=True).stdout.strip()
        self.assertEqual(path_version, "0.157.1")
        rows = completion_row(
            "codex", survey="present", component=codex["acp_command"],
            observed="configured-pair", verified=codex["acp_verified_versions"],
            relation="not-verified", launch_override=str(override), path_cli=path_version,
            unrelated_global_cli=True, authorization_covers=True,
        )
        text = rows[0]
        self.assertIn("component=" + codex["acp_command"], text)
        self.assertIn("path_cli=0.157.1", text)
        self.assertIn(f"launch_override={override}", text)
        self.assertIn("the PATH CLI is not the pinned ACP pair", text)
        self.assertIn("action=none", text)
        self.assertNotIn("whole-component", text)
        self.assertNotIn("versions=0.157.1", text)
        self.assertNotIn("verified=cli=0.157.1", text)
        self.assertIn("cli=0.158.0;adapter=2.0.0;protocol=1", text)
        overlooked = completion_row(
            "codex", survey="present", component=codex["acp_command"],
            observed="configured-pair", verified=codex["acp_verified_versions"],
            relation="not-verified", launch_override="", path_cli=path_version,
            unrelated_global_cli=True,
        )[0]
        self.assertIn("path_cli=0.157.1", overlooked)
        self.assertNotIn("launch_override=", overlooked)
        self.assertNotIn("verified=cli=0.157.1", overlooked)

    def test_partial_preparation_stays_honest(self) -> None:
        absent = completion_row(
            "devin", survey="absent", component="devin acp", observed="absent",
            verified="manifest", relation="absent")
        unknown = completion_row(
            "devin", survey="unknown", component="devin acp", observed="unknown",
            verified="manifest", relation="unknown")
        self.assertIn("not-ready: absent", absent[0])
        self.assertIn("do not install automatically", absent[0])
        self.assertIn("not-ready: unknown", unknown[0])
        self.assertNotIn("not-ready: absent", unknown[0])
        newer = completion_row(
            "dsh", survey="present", component="dsh --profile acp", observed="dsh=9.9.9",
            verified="cli=0.1.7-rc.2", relation="newer-unverified", authorization_covers=True)
        self.assertIn("do not silently downgrade", newer[0])
        self.assertNotIn("npm install", newer[0])
        self.assertNotIn("0.1.7-rc.2@", newer[0])
        blocked = completion_row(
            "dsh", survey="present", component="dsh --profile acp", observed="dsh=0.1.5-rc.3",
            verified="cli=0.1.7-rc.2", relation="not-verified",
            authorization_covers=False, shared_live=True)
        self.assertIn("HUMAN_DECISION_REQUIRED", blocked[0])
        self.assertIn("do not restart", blocked[0])
        self.assertNotIn("restarted", blocked[0])
        covered = completion_row(
            "dsh", survey="present", component="dsh --profile acp", observed="dsh=0.1.5-rc.3",
            verified="cli=0.1.7-rc.2", relation="not-verified", authorization_covers=True)
        self.assertNotIn("HUMAN_DECISION_REQUIRED", covered[0])
        self.assertIn("do not ask again", covered[0])


if __name__ == "__main__":
    unittest.main()
