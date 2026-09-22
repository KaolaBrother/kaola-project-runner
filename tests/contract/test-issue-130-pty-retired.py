#!/usr/bin/env python3
"""Issue #130: PTY is retired unconditionally; the Runner is ACP-only.

Owner ruling (Yanlei 2026-09-22), Fable design accepted on the issue:

1. Any command carrying ``--transport pty`` is refused by the one shared
   entrypoint ``scripts/kaola-tmux.sh`` with the typed reason
   ``transport-pty-retired``, decided from the arguments alone, before the
   manifest, Git, the Issue #73 canonical-root binding, or the Issue #104
   dispatcher fact is consulted, and before any process, holder, or record
   exists.
2. There is no dual-transport choice left in the schema: manifests carry no
   ``default_transport`` (the renderer rejects it as an extra key) and the ACP
   receipt's ``transport`` block no longer names a default, alternatives, or a
   selection reason.
3. No live surface (docs, templates, manifests, generated Skills, scripts)
   documents PTY as an option, and the retired PTY machinery and fixtures are
   gone rather than left unreachable.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
TMUX_CLI = SCRIPTS / "kaola-tmux.sh"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"

PLATFORMS = ("grok", "claude-code", "opencode", "kimi-cli", "cursor-cli",
             "devin", "codex", "zcode", "droid", "dsh")
COMMANDS = (
    ("preflight", ()), ("start", ()), ("send", ("--text", "x")), ("observe", ()),
    ("status", ()), ("capture", ()), ("stop", ()), ("steer", ("--text", "x")),
)
REFUSAL_RECEIPT_BYTES = 4096
REASON = "transport-pty-retired"
RETIRED_REASONS = ("heartbeat-host-pty-unsupported", "steer-unsupported-transport",
                   "transport-mismatch")
SCRUB = ("KAOLA_PROJECT_RUNNER_CANONICAL_REPO", "KAOLA_ACP_DISPATCHER",
         "KAOLA_ACP_HEARTBEAT_HOST", "KAOLA_ACP_HEARTBEAT_HOST_SOCKET",
         "KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_skills_i130", SCRIPTS / "render-skills.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i130-")
        cls.root = Path(cls._tmp.name).resolve()
        cls.repo = cls.root / "project"
        cls.repo.mkdir()
        git("init", "-q", "-b", "main", cwd=cls.repo)
        git("config", "user.email", "t@example.invalid", cwd=cls.repo)
        git("config", "user.name", "t", cwd=cls.repo)
        (cls.repo / "README.md").write_text("i130\n", encoding="utf-8")
        git("add", "README.md", cwd=cls.repo)
        git("commit", "-qm", "seed", cwd=cls.repo)
        cls.other = cls.root / "other"
        cls.other.mkdir()
        git("init", "-q", "-b", "main", cwd=cls.other)
        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in SCRUB}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        # A refusal must never reach an agent; if one did, it would fail here.
        env["KAOLA_ACP_COMMAND"] = str(self.root / "no-such-agent")
        env.update(extra)
        return env

    def run_cli(self, platform: str, command: str, *args: str,
                env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(TMUX_CLI), platform, command, *args],
            capture_output=True, text=True, timeout=60,
            env=env if env is not None else self.env())

    def assert_retired(self, result: subprocess.CompletedProcess, action: str,
                       platform: str, session: str) -> dict:
        self.assertEqual(result.returncode, 1, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, f"one-line receipt expected: {result.stdout!r}")
        self.assertLessEqual(len(result.stdout.encode("utf-8")), REFUSAL_RECEIPT_BYTES)
        receipt = json.loads(lines[0])
        self.assertEqual(receipt["schema_version"], 3)
        self.assertEqual(receipt["result"], "refused")
        self.assertEqual(receipt["reason"], REASON)
        self.assertEqual(receipt["action"], action)
        self.assertEqual(receipt["platform"], platform)
        self.assertEqual(receipt["session"], session)
        self.assertIs(receipt["mutation_performed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertIn("ACP-only", receipt["detail"])
        self.assertEqual(receipt["transport"], {"requested": "pty", "supported": ["acp"]})
        self.assertNotIn("canonical_repo", receipt)
        return receipt

    def assert_no_side_effect(self, session: str) -> None:
        if self.record_root.exists():
            leftovers = [p for p in self.record_root.rglob("*") if session in str(p)]
            self.assertEqual(leftovers, [], "a refusal left a record behind")
        self.assertEqual(git("status", "--porcelain", cwd=self.repo), "")
        if shutil.which("tmux"):
            probe = subprocess.run(["tmux", "has-session", "-t", f"={session}"],
                                   capture_output=True)
            self.assertNotEqual(probe.returncode, 0, "a refusal created a tmux session")
        ps = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True)
        holders = [line for line in ps.stdout.splitlines()
                   if "kaola-acp-holder" in line and session in line]
        self.assertEqual(holders, [], "a refusal spawned a holder")


class TypedRefusal(Fixture):
    def test_every_platform_and_command_refuses_a_pty_request(self) -> None:
        for platform in PLATFORMS:
            for command, extra in COMMANDS:
                session = f"i130-{platform}-{command}"
                with self.subTest(platform=platform, command=command):
                    result = self.run_cli(platform, command, "--repo", str(self.repo),
                                          "--session", session, "--transport", "pty", *extra)
                    self.assert_retired(result, command, platform, session)
                    self.assert_no_side_effect(session)

    def test_the_refusal_needs_no_manifest_git_or_valid_repo(self) -> None:
        # Decided from the arguments alone: a nonexistent repo still gets the
        # typed refusal rather than a repository error.
        missing = str(self.root / "does-not-exist")
        result = self.run_cli("codex", "start", "--repo", missing,
                              "--session", "i130-no-repo", "--transport", "pty")
        receipt = self.assert_retired(result, "start", "codex", "i130-no-repo")
        self.assertEqual(receipt["repo"], missing)
        self.assertFalse(Path(missing).exists())

    def test_the_pty_refusal_precedes_the_canonical_root_guard(self) -> None:
        # A drifted root would be canonical-root-mismatch; the PTY request
        # itself is illegal, so the retired refusal answers first.
        env = self.env(KAOLA_PROJECT_RUNNER_CANONICAL_REPO=str(self.repo))
        session = "i130-drifted"
        result = self.run_cli("codex", "start", "--repo", str(self.other),
                              "--session", session, "--transport", "pty", env=env)
        self.assert_retired(result, "start", "codex", session)
        self.assert_no_side_effect(session)

    def test_the_dispatcher_refusal_is_absorbed(self) -> None:
        env = self.env(KAOLA_ACP_DISPATCHER='{"platform":"zcode","session":"zcode-kaola-host"}',
                       KAOLA_PROJECT_RUNNER_CANONICAL_REPO=str(self.repo))
        session = "i130-dispatched"
        result = self.run_cli("grok", "start", "--repo", str(self.repo),
                              "--session", session, "--transport", "pty", env=env)
        self.assert_retired(result, "start", "grok", session)
        self.assertNotIn("heartbeat-host-pty-unsupported", result.stdout)

    def test_any_other_transport_value_is_an_argument_error(self) -> None:
        result = self.run_cli("grok", "status", "--repo", str(self.repo),
                              "--session", "i130-bad", "--transport", "tmux")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("--transport must be acp", result.stderr)
        self.assertNotIn("pty", result.stderr)


class NoTransportOption(Fixture):
    def preflight(self, *extra: str) -> dict:
        env = self.env(KAOLA_ACP_COMMAND=f"{sys.executable} {MOCK}",
                       GROK_BIN=str(self.root / "no-such-grok"))
        result = self.run_cli("grok", "preflight", "--repo", str(self.repo), *extra, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_transport_acp_is_a_no_op(self) -> None:
        explicit = self.preflight("--transport", "acp")
        implicit = self.preflight()
        self.assertEqual(sorted(explicit), sorted(implicit))
        self.assertEqual(explicit["transport"]["selected"], "acp")
        self.assertEqual(sorted(explicit["transport"]), sorted(implicit["transport"]))

    def test_the_receipt_names_no_default_alternative_or_reason(self) -> None:
        transport = self.preflight()["transport"]
        self.assertEqual(transport["selected"], "acp")
        for retired in ("default", "alternatives", "reason"):
            self.assertNotIn(retired, transport)

    def test_the_acp_cli_takes_no_transport_reason(self) -> None:
        source = (SCRIPTS / "kaola-acp.py").read_text(encoding="utf-8")
        self.assertNotIn("--transport-reason", source)
        self.assertNotIn("default_transport", source)
        self.assertNotIn('"has-session"', source)
        for reason in RETIRED_REASONS:
            self.assertNotIn(reason, source)
        entry = TMUX_CLI.read_text(encoding="utf-8")
        # The entrypoint's comment may name the absorbed #104 reason; no code emits it.
        self.assertNotIn("s:reason:heartbeat-host-pty-unsupported", entry)
        self.assertNotIn("steer-unsupported-transport", entry)
        self.assertNotIn("TMUX_BIN", entry)
        self.assertNotIn("default_transport", entry)


class RenderFailsClosed(unittest.TestCase):
    def test_default_transport_is_not_a_manifest_key(self) -> None:
        renderer = load_renderer()
        self.assertNotIn("default_transport", renderer.REQUIRED)
        for platform in PLATFORMS:
            text = (PROJECT / "platforms" / f"{platform}.yaml").read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^default_transport:")

    def test_reintroducing_default_transport_is_rejected(self) -> None:
        renderer = load_renderer()
        with tempfile.TemporaryDirectory(prefix="kaola-i130-manifest-") as tmp:
            for value in ("acp", "pty"):
                with self.subTest(value=value):
                    path = Path(tmp) / "codex.yaml"
                    text = (PROJECT / "platforms" / "codex.yaml").read_text(encoding="utf-8")
                    path.write_text(text + f'default_transport: "{value}"\n', encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "extra=.*default_transport"):
                        renderer.parse_manifest(path)


# A live PTY-as-option statement; the refusal text itself names neither form.
LIVE_OPTION = re.compile(
    r"(?i)--transport\s+pty|acp\|pty|pty\|acp|pty\s+(fallback|diagnostic)|both transports"
    r"|dual[- ]transport|PTY and ACP|ACP and PTY|nested-PTY relay"
)
RETIRED_STATEMENT = re.compile(r"(?i)transport-pty-retired|\bretired\b|\brefused\b")
DATED = re.compile(r"20\d\d-\d\d-\d\d")


def live_surfaces() -> list[Path]:
    paths: list[Path] = [PROJECT / "README.md", PROJECT / "AGENTS.md"]
    for base in ("docs", "templates", "platforms", "skills", "hosts", "scripts"):
        for path in sorted((PROJECT / base).rglob("*")):
            if not path.is_file() or path.suffix in (".pyc",):
                continue
            rel = path.relative_to(PROJECT).as_posix()
            if base == "docs" and (DATED.search(path.name) or "/decisions/" in f"/{rel}"):
                continue
            if rel.startswith("templates/grok-golden/"):
                continue  # frozen (AGENTS.md); not a live option surface
            paths.append(path)
    return paths


class NoLiveOption(unittest.TestCase):
    def test_no_live_surface_documents_pty_as_an_option(self) -> None:
        hits = []
        for path in live_surfaces():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                # Stating the refusal names PTY without offering it.
                if LIVE_OPTION.search(line) and not RETIRED_STATEMENT.search(line):
                    hits.append(f"{path.relative_to(PROJECT)}:{number}: {line.strip()[:160]}")
        self.assertEqual(hits, [], "live PTY-as-option statements remain:\n" + "\n".join(hits))

    def test_worker_skills_ship_no_pty_machinery(self) -> None:
        for platform in PLATFORMS:
            skill = PROJECT / "skills" / f"{platform}-kaola-project-runner"
            with self.subTest(platform=platform):
                self.assertEqual(sorted(p.name for p in (skill / "references").iterdir()),
                                 ["acp.md", "platform.md", "steering.md"])
                scripts = {p.name for p in (skill / "scripts").iterdir()}
                for gone in ("kaola-observation.py", "kaola-pane-relay.py",
                             "kaola-relay-client.py", "kaola-relay-protocol.py"):
                    self.assertNotIn(gone, scripts)

    def test_retired_machinery_and_fixtures_are_gone(self) -> None:
        for rel in ("scripts/kaola-observation.py", "scripts/kaola-pane-relay.py",
                    "scripts/kaola-relay-client.py", "scripts/kaola-relay-protocol.py",
                    "templates/references/transport.md.tmpl", "tests/fixtures",
                    "tests/lib/issue-1-test-lib.sh", "tests/contract/test-model-policy.sh",
                    "tests/contract/test-relay-pty.py", "tests/contract/test-kaola-tmux.sh"):
            with self.subTest(path=rel):
                self.assertFalse((PROJECT / rel).exists(), f"{rel} must be removed")

    def test_validate_has_no_pty_lane(self) -> None:
        text = (SCRIPTS / "validate.sh").read_text(encoding="utf-8")
        self.assertNotIn("python_suites_c", text)
        self.assertNotIn("test-model-policy.sh", text)
        self.assertIn('"test-issue-130-pty-retired.py"', text)


# -- Issue #8 model-policy guarantees, re-homed from the deleted PTY suite -----
#
# tests/contract/test-model-policy.sh proved them against a fake TUI. Each class
# is mapped below to ACP coverage (kaola-workflow/issue-130 model-policy map);
# the classes no ACP suite covered are asserted here with the offline mock agent,
# reusing test-acp-contract.py's fixture (holder leak check included). Covered
# elsewhere: tier presets and user override on a fresh start
# (test-acp-contract.py Issue34ModelSelectionAcpTests, test-droid-acp-contract.py,
# test-issue-111-model-tiers.py), no invented effort, resume preservation, and ACP
# Fast. What PTY exposed and ACP does not (a computed true/false model_verified,
# actual_runtime_model_id, status-time model provenance) is a stated loss in
# CHANGELOG, pinned here so bringing it back is a deliberate change.

def _load_acp_contract():
    spec = importlib.util.spec_from_file_location(
        "acp_contract_i130", PROJECT / "tests" / "contract" / "test-acp-contract.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_ACP = _load_acp_contract()
_MODEL_TESTS = _ACP.Issue34ModelSelectionAcpTests
MISMATCH_CONFIG = {"set_result": {"configOptions": [
    {"id": "model", "type": "select", "currentValue": "saved-picker/other",
     "options": [{"value": "gpt-5.6-sol"}, {"value": "gpt-6-astra"}]},
    {"id": "reasoning_effort", "type": "select", "currentValue": "high", "options": []},
]}}


class ModelPolicyOnAcp(_ACP.AcpSessionFixture, unittest.TestCase):
    cli = _MODEL_TESTS.cli
    start = _MODEL_TESTS.start
    config_events = _MODEL_TESTS.config_events

    def setUp(self) -> None:
        _ACP.AcpSessionFixture.setUp(self)
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in _ACP.AcpSessionFixture.env(self).items() if k not in SCRUB}
        # Deterministic catalog: the probe fails instead of reading a real codex.
        env["CODEX_BIN"] = str(self.root / "no-such-codex")
        return env

    def guarded_start(self, *args: str, **kwargs) -> dict:
        # #77: the holder is force-stopped even if start itself fails mid-way.
        self.addCleanup(self.cli, "stop", "--force", platform="codex", check=False, timeout=15)
        return self.start("codex", *args, **kwargs)

    def test_a_hostile_model_id_is_data_reported_and_applied_verbatim(self) -> None:
        marker = self.root / "model-input-executed"
        hostile = f"model with spaces (x) [y]; $(touch {marker}); `touch {marker}.bt`"
        receipt = self.guarded_start("--model", hostile)
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt["requested_model_source"], "user")
        self.assertEqual(receipt["requested_model_name"], hostile)
        self.assertEqual(receipt["resolved_runtime_model_id"], hostile)
        self.assertEqual(receipt["config_application"]["model"]["value"], hostile)
        self.assertIn(("model", hostile), self.config_events())
        self.assertFalse(marker.exists())
        self.assertFalse(Path(f"{marker}.bt").exists())

    def test_a_hostile_model_id_survives_the_shared_entrypoint(self) -> None:
        marker = self.root / "entrypoint-executed"
        hostile = f"m (x); $(touch {marker}); `touch {marker}.bt`"
        env = self.env()
        env["KAOLA_ACP_COMMAND"] = self.mock_command()
        base = [str(TMUX_CLI), "codex"]
        tail = ["--repo", str(self.repo), "--session", self.session]
        self.addCleanup(subprocess.run, [*base, "stop", *tail, "--force"], env=env,
                        capture_output=True, timeout=30)
        result = subprocess.run([*base, "start", *tail, "--model", hostile], env=env,
                                capture_output=True, text=True, timeout=60)
        receipt = json.loads(result.stdout)
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt["requested_model_name"], hostile)
        self.assertEqual(receipt["config_application"]["model"]["value"], hostile)
        self.assertFalse(marker.exists())
        self.assertFalse(Path(f"{marker}.bt").exists())

    def test_b_an_unavailable_model_the_agent_accepts_is_reported_verbatim(self) -> None:
        receipt = self.guarded_start("--model", "unavailable/codex")
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt["requested_model_name"], "unavailable/codex")
        self.assertEqual(receipt["resolved_runtime_model_id"], "unavailable/codex")
        self.assertEqual(receipt["config_application"]["model"],
                         {"applied": True, "config_id": "model", "value": "unavailable/codex"})

    def test_b_an_unavailable_model_the_agent_rejects_is_reported_not_a_gate(self) -> None:
        receipt = self.guarded_start("--model", "unavailable/codex", caps="strict-config")
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt["requested_model_name"], "unavailable/codex")
        model = receipt["config_application"]["model"]
        self.assertFalse(model["applied"])
        self.assertEqual(model["value"], "unavailable/codex")
        self.assertEqual(model["error"]["code"], "config-option-failed")
        sent = self.cli("send", "--text", "usable", platform="codex")
        self.assertEqual(sent["outcome"], "turn_completed", sent)

    def test_c_resume_with_an_explicit_model_reports_request_and_agent_answer(self) -> None:
        pages = [{"sessions": [{"sessionId": "saved-codex-1", "cwd": str(self.repo)}]}]
        receipt = self.guarded_start(
            "--resume", "saved-codex-1", "--model", "gpt-6-astra", caps="resume",
            extra_env={"MOCK_ACP_LIST_PAGES": json.dumps(pages),
                       "MOCK_ACP_CONFIG": json.dumps(MISMATCH_CONFIG)})
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt["model_selection"]["source"], "user")
        self.assertFalse(receipt["model_selection"]["preserved"])
        self.assertIn(("model", "gpt-6-astra"), self.config_events())
        # The override is not claimed: the agent's own answer is reported beside it.
        self.assertEqual(receipt["effective_selection"]["effective_model"], "saved-picker/other")

    def test_c_resume_with_a_tier_applies_the_tier(self) -> None:
        pages = [{"sessions": [{"sessionId": "saved-codex-1", "cwd": str(self.repo)}]}]
        receipt = self.guarded_start("--resume", "saved-codex-1", "--tier", "upgrade",
                                     caps="resume",
                                     extra_env={"MOCK_ACP_LIST_PAGES": json.dumps(pages)})
        self.assertEqual(receipt["model_selection"]["source"], "runner-upgrade")
        self.assertFalse(receipt["model_selection"]["preserved"])
        self.assertIn(("model", "gpt-6-astra"), self.config_events())

    def test_d_an_effective_model_mismatch_is_evidence_not_a_gate(self) -> None:
        receipt = self.guarded_start(extra_env={"MOCK_ACP_CONFIG": json.dumps(MISMATCH_CONFIG)})
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertNotEqual(receipt.get("result"), "refused")
        self.assertEqual(receipt["resolved_runtime_model_id"], "gpt-5.6-sol")
        self.assertEqual(receipt["effective_selection"],
                         {"effective_model": "saved-picker/other", "effective_effort": "high",
                          "effort_config_id": "reasoning_effort"})
        # Loss: ACP computes no true/false verdict; the mismatch is the two facts above.
        self.assertEqual(receipt["model_verified"], "unknown")
        sent = self.cli("send", "--text", "still usable", platform="codex")
        self.assertEqual(sent["outcome"], "turn_completed", sent)

    def test_e_status_reports_the_native_selection(self) -> None:
        config = {"set_result": {"configOptions": [
            {"id": "model", "type": "select", "currentValue": "gpt-6-astra", "options": []}]}}
        self.guarded_start("--model", "gpt-6-astra",
                           extra_env={"MOCK_ACP_CONFIG": json.dumps(config)})
        status = self.cli("status", platform="codex")
        options = {o["id"]: o for o in (status.get("session_meta") or {}).get("configOptions") or []}
        self.assertEqual(options["model"]["currentValue"], "gpt-6-astra")
        # Loss: request provenance lives only in the start receipt.
        self.assertNotIn("requested_model_source", status)
        self.assertNotIn("model_selection", status)

    def test_f_an_unreadable_effective_model_is_unknown_never_a_guess(self) -> None:
        receipt = self.guarded_start()  # the default mock advertises no currentValue
        self.assertIsNone(receipt.get("error"), receipt)
        self.assertEqual(receipt["effective_selection"],
                         {"effective_model": None, "effective_effort": None,
                          "effort_config_id": "reasoning_effort"})
        self.assertIsNone(receipt["actual_runtime_model_id"])
        self.assertIsNone(receipt["actual_parameters"])
        self.assertEqual(receipt["model_verified"], "unknown")
        self.assertTrue(receipt["model_mismatch_reason"])

    def test_start_writes_no_prompt(self) -> None:
        self.guarded_start()
        self.assertEqual([e for e in self.read_mock_log() if e.get("event") == "prompt"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
