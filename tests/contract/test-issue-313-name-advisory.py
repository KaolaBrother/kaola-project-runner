#!/usr/bin/env python3
"""Issue #313: advisory issue_name on start and list, and the shared name contract.

The fixture is the artifact a consumer can vendor. This file runs the parser
against every row and checks the join rule the fixture states. Start is
exercised with the mock ACP agent: every advisory value still reaches a ready
session. List rows carry the same advisory. A host name omits issue_name.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
PARSER = PROJECT / "scripts" / "kaola-session-names.py"
CLI = PROJECT / "scripts" / "kaola-acp.py"
FIXTURE = PROJECT / "tests" / "contract" / "kaola-terminal-name-contract.json"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable
REPO_ID = "https://github.com/example/consumer.git"
EXPECTED_IDS = (
    "antigravity", "claude-code", "codex", "cursor-cli", "devin", "droid", "dsh",
    "grok", "hermes", "kimi-cli", "opencode", "zcode",
)


def load_parser():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_session_names_313", PARSER)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_acp():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_acp_313", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).strip()


def write_state(path: Path, status: str, issue: int, claim: str | None) -> None:
    claim_line = f"claim_repository_id: {claim}\n" if claim else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Kaola-Workflow State\n\n"
        "## Project\n"
        "name: issue-test\n"
        f"status: {status}\n\n"
        "## Claim Identity\n"
        f"{claim_line}\n"
        "## Sink\n"
        f"issue_number: {issue}\n",
        encoding="utf-8",
    )


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.email=issue-313@example.com",
         "-c", "user.name=issue-313", *args],
        check=True, capture_output=True, text=True,
    )


class FixtureMatchesParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.names = load_parser()
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_states_the_closed_vocabularies_and_the_join_rule(self) -> None:
        fixture = self.fixture
        self.assertEqual(fixture["schema"], "kaola-terminal-name-contract/1")
        self.assertEqual(fixture["advisory_values"], list(self.names.ISSUE_NAME_VALUES))
        self.assertEqual(fixture["advisory_blocks_start"], False)
        self.assertEqual(fixture["non_worker_omits_issue_name"], True)
        self.assertEqual(fixture["join_rule"], self.names.JOIN_RULE)
        self.assertEqual(fixture["advisory_note"], self.names.ADVISORY_NOTE)
        self.assertTrue(fixture["join_rule"].startswith(
            "name parses AND the repo's active run claims that issue number => bound; "
            "else unbound."
        ))
        self.assertEqual(set(fixture["name_role_values"]), set(self.names.NAME_ROLES))
        self.assertEqual(
            fixture["general_form"], "<platform>-<CODE>-general-<purpose>",
        )
        self.assertEqual(self.names._PROJECT.pattern, r"^[A-Za-z][A-Za-z0-9]*$")

    def test_each_row_matches_the_parser_and_the_join(self) -> None:
        seen_advisories = set()
        for row in self.fixture["rows"]:
            with self.subTest(name=row["name"], platform=row["platform_id"]):
                parsed = self.names.parse_session_name(row["name"], row["platform_id"])
                self.assertEqual(set(parsed), set(self.names.PARSED_KEYS))
                self.assertEqual(parsed, row["parsed"])
                self.assertIn(parsed["classification"], self.names.CLASSIFICATIONS)
                issue_name = self.names.issue_name_for(
                    parsed, row["active_claim_count"], claims=row["claims"],
                    session_origin_value=row.get("record_repository_id"),
                )
                self.assertEqual(issue_name, row["issue_name"])
                if issue_name is not None:
                    self.assertIn(issue_name, self.names.ISSUE_NAME_VALUES)
                    seen_advisories.add(issue_name)
                else:
                    self.assertNotEqual(parsed["name_role"], "worker")
                bound = self.names.join_bound(
                    parsed, row["claims"], row["record_repository_id"])
                self.assertEqual(bound, row["join"]["bound"])
                self.assertEqual(row["join"]["platform_id"], row["platform_id"])
                self.assertEqual(row["join"]["project"], parsed["project"])
                self.assertEqual(row["join"]["issue"], parsed["issue"])
                self.assertEqual(row["join"]["purpose"], parsed["purpose"])
                countable = [
                    claim for claim in row["claims"]
                    if claim.get("archived") is not True
                    and claim.get("status") == "active"
                    and claim.get("issue_number") == parsed.get("issue")
                    and isinstance(claim.get("claim_repository_id"), str)
                    and claim["claim_repository_id"].strip()
                ]
                if parsed["classification"] == "ok":
                    self.assertEqual(len(countable), row["active_claim_count"])
        self.assertEqual(seen_advisories, set(self.names.ISSUE_NAME_VALUES))

    def test_platform_ids_come_from_session_prefix(self) -> None:
        catalog = self.names.platform_catalog(PROJECT / "platforms")
        ids = tuple(row["id"] for row in catalog)
        self.assertEqual(ids, EXPECTED_IDS)
        for row in catalog:
            self.assertEqual(row["session_prefix"], f"{row['id']}-kaola")
            self.assertEqual(row["name_token"], row["id"])
        self.assertEqual(self.names.platform_ids(), EXPECTED_IDS)


class ActiveRunLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.names = load_parser()

    def test_reads_claim_fields_and_skips_archive_closed_and_folder_names(self) -> None:
        main = self.root / "main"
        main.mkdir()
        git(main, "init", "-q")
        git(main, "commit", "--allow-empty", "-m", "init")
        git(main, "remote", "add", "origin", REPO_ID)
        write_state(
            main / "kaola-workflow" / "issue-123" / "workflow-state.md",
            "active", 123, REPO_ID,
        )
        write_state(
            main / "kaola-workflow" / "issue-123-closed" / "workflow-state.md",
            "closed", 123, REPO_ID,
        )
        write_state(
            main / "kaola-workflow" / "archive" / "issue-123" / "workflow-state.md",
            "active", 123, REPO_ID,
        )
        write_state(
            main / "kaola-workflow" / "named-like-123" / "workflow-state.md",
            "active", 456, REPO_ID,
        )
        write_state(
            main / "kaola-workflow" / "missing-claim-id" / "workflow-state.md",
            "active", 789, None,
        )
        found = self.names.find_active_claims(str(main), 123)
        self.assertEqual(found["count"], 1)
        self.assertEqual(found["claims"][0]["issue_number"], 123)
        self.assertEqual(found["claims"][0]["claim_repository_id"], REPO_ID)
        self.assertEqual(found["claims"][0]["path"], "kaola-workflow/issue-123/workflow-state.md")
        self.assertEqual(self.names.find_active_claims(str(main), 456)["count"], 1)
        self.assertEqual(self.names.find_active_claims(str(main), 789)["count"], 0)
        advice = self.names.advise("claude-code-PROJ-i123-x", "claude-code", str(main))
        self.assertEqual(advice["issue_name"], "ok")
        self.assertEqual(advice["name_role"], "worker")
        absent = self.names.advise("grok-PROJ-i999-x", "grok", str(main))
        self.assertEqual(absent["issue_name"], "no-active-run")
        self.assertEqual(absent["classification"], "ok")

    def test_a_worktree_reads_the_main_checkout_only(self) -> None:
        main = self.root / "main"
        main.mkdir()
        git(main, "init", "-q")
        git(main, "commit", "--allow-empty", "-m", "init")
        git(main, "remote", "add", "origin", REPO_ID)
        worktree = self.root / "worktree"
        subprocess.run(
            ["git", "-C", str(main), "worktree", "add", "--detach", str(worktree)],
            check=True, capture_output=True, text=True,
        )
        write_state(
            main / "kaola-workflow" / "issue-123" / "workflow-state.md",
            "active", 123, REPO_ID,
        )
        write_state(
            worktree / "kaola-workflow" / "issue-999" / "workflow-state.md",
            "active", 999, REPO_ID,
        )
        self.assertEqual(self.names.find_active_claims(str(worktree), 123)["count"], 1)
        self.assertEqual(self.names.find_active_claims(str(worktree), 999)["count"], 0)

    def test_bundle_two_runs_and_origin_decide_the_advisory(self) -> None:
        main = self.root / "main"
        main.mkdir()
        git(main, "init", "-q")
        git(main, "commit", "--allow-empty", "-m", "init")
        git(main, "remote", "add", "origin", "git@github.com:example/consumer.git")
        write_state(
            main / "kaola-workflow" / "issue-10" / "workflow-state.md",
            "active", 10, "https://github.com/example/consumer.git",
        )
        write_state(
            main / "kaola-workflow" / "issue-10-again" / "workflow-state.md",
            "active", 12, REPO_ID,
        )
        bundle = main / "kaola-workflow" / "bundle-10-11" / "workflow-state.md"
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_text(
            "# Kaola-Workflow State\n\n"
            "## Project\n"
            "name: bundle-10-11\n"
            "status: active\n"
            "bundle_id: bundle-10-11\n"
            "issue_numbers: 10,11\n\n"
            "## Claim Identity\n"
            f"claim_repository_id: {REPO_ID}\n\n"
            "## Sink\n"
            "issue_number: 11\n",
            encoding="utf-8",
        )
        one = self.names.advise("grok-KT-i10-work", "grok", str(main))
        self.assertEqual(one["issue_name"], "ok")
        self.assertEqual(one["active_claim_count"], 1)
        two = self.names.advise("grok-KT-i12-work", "grok", str(main))
        self.assertEqual(two["issue_name"], "ok")
        write_state(
            main / "kaola-workflow" / "issue-12-second" / "workflow-state.md",
            "active", 12, REPO_ID,
        )
        doubled = self.names.advise("grok-KT-i12-work", "grok", str(main))
        self.assertEqual(doubled["issue_name"], "no-active-run")
        bundled = self.names.advise("grok-KT-i11-bundle", "grok", str(main))
        self.assertEqual(bundled["issue_name"], "no-active-run")
        self.assertEqual(self.names.find_active_claims(str(main), 11)["count"], 0)
        other = self.root / "other"
        other.mkdir()
        git(other, "init", "-q")
        git(other, "commit", "--allow-empty", "-m", "init")
        git(other, "remote", "add", "origin", "https://github.com/example/other.git")
        write_state(
            other / "kaola-workflow" / "issue-10" / "workflow-state.md",
            "active", 10, REPO_ID,
        )
        mismatch = self.names.advise("codex-KT-i10-work", "codex", str(other))
        self.assertEqual(mismatch["issue_name"], "no-active-run")
        general = self.names.advise("cursor-cli-KT-general-watch", "cursor-cli", str(main))
        self.assertEqual(general["name_role"], "general")
        self.assertIsNone(general["issue_name"])
        self.assertIsNone(general["issue"])
        digit = self.names.advise("codex-1KT-i1-work", "codex", str(main))
        self.assertEqual(digit["issue_name"], "malformed")
        self.assertIsNone(digit["issue"])


class DocsAndInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.names = load_parser()

    def test_docs_state_the_exact_id_the_advisory_and_the_fixture(self) -> None:
        conventions = normalize((PROJECT / "docs" / "conventions.md").read_text(encoding="utf-8"))
        display = normalize((PROJECT / "docs" / "issue-dispatch-display.md").read_text(encoding="utf-8"))
        api = normalize((PROJECT / "docs" / "api.md").read_text(encoding="utf-8"))
        self.assertIn("The exact platform id is required", conventions)
        self.assertIn("claude- is not claude-code-", conventions)
        self.assertIn("cursor- is not cursor-cli-", conventions)
        self.assertIn("They do not block a start", conventions)
        self.assertIn("the 1-80 --session syntax is the only validator", conventions)
        self.assertIn(normalize(self.names.JOIN_RULE), display)
        self.assertIn("tests/contract/kaola-terminal-name-contract.json", display)
        self.assertIn("Do not add a blocking classifier, a registry, a daemon, or a new Workflow state field", display)
        self.assertIn("Nothing here was verified end to end against a consumer", display)
        self.assertIn("issue_name", api)
        self.assertIn("platform-token-mismatch", api)
        self.assertIn("no-active-run", api)
        self.assertIn("name_role", api)
        changelog = (PROJECT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Issue #313", changelog)
        self.assertIn("scripts/kaola-acp.py` is a per-call CLI", changelog)
        self.assertIn("Seats: restart not required", changelog.split("## 0.9.9", 1)[0])

    def test_validate_registers_the_suite_in_the_inventory_and_a_lane(self) -> None:
        text = (PROJECT / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertEqual(text.count('"test-issue-313-name-advisory.py"'), 2)
        render = (PROJECT / "scripts" / "render-skills.py").read_text(encoding="utf-8")
        self.assertIn(
            '(shared_root / "kaola-session-names.py", "scripts/kaola-session-names.py")',
            render,
        )

    def test_the_session_syntax_validator_is_unchanged(self) -> None:
        acp = load_acp()
        self.assertEqual(acp.SESSION_PATTERN.pattern, r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class StartStillSucceeds(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.repo = Path(os.path.realpath(self.root / "repo"))
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "remote", "add", "origin", REPO_ID)
        write_state(
            self.repo / "kaola-workflow" / "issue-123" / "workflow-state.md",
            "active", 123, REPO_ID,
        )
        self.agent = f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"
        self.started: list[tuple[str, str]] = []

    def tearDown(self) -> None:
        for platform, session in self.started:
            self.run_cli(platform, "stop", "--force", session=session, check=False)

    def env(self) -> dict[str, str]:
        return {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "KAOLA_LAUNCH_BACKEND": "direct",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
        }

    def run_cli(self, platform: str, command: str, *args: str, session: str | None = None,
                check: bool = True) -> tuple[subprocess.CompletedProcess, dict]:
        argv = [PYTHON, str(CLI)]
        if command == "list":
            argv += ["list", "--record-root", str(self.records), "--repo", str(self.repo), *args]
        else:
            assert session is not None
            argv += [platform, command, "--repo", str(self.repo), "--session", session, *args]
            if command == "start":
                self.started.append((platform, session))
                argv += ["--command", self.agent]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=90,
        )
        payload: dict = {}
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            payload = json.loads(lines[-1])
        if check and result.returncode != 0:
            self.fail(f"{command} exited {result.returncode}: {payload or result.stderr[-800:]}")
        return result, payload

    def test_each_advisory_starts_and_list_marks_the_row(self) -> None:
        cases = (
            ("claude-code", "claude-PROJ-i123-x", "platform-token-mismatch", "worker"),
            ("grok", "grok-PROJ-i456-x", "no-active-run", "worker"),
            ("claude-code", "claude-PROJ-haiku-1749-x", "malformed", "worker"),
            ("claude-code", "claude-code-PROJ-i123-x", "ok", "worker"),
            ("grok", "grok-KT-general-watch", None, "general"),
        )
        for platform, session, issue_name, role in cases:
            with self.subTest(session=session):
                result, receipt = self.run_cli(platform, "start", session=session)
                self.assertEqual(result.returncode, 0, receipt)
                self.assertNotEqual(receipt.get("result"), "refused", receipt)
                self.assertEqual(receipt.get("state"), "ready", receipt)
                self.assertEqual(receipt.get("name_role"), role, receipt)
                if issue_name is None:
                    self.assertNotIn("issue_name", receipt)
                else:
                    self.assertEqual(receipt.get("issue_name"), issue_name, receipt)
                self.assertNotIn("error", receipt, receipt)
        host = "grok-PROJ-orchestrator-main"
        dead = subprocess.Popen(["/bin/sleep", "30"])
        dead.kill()
        dead.wait(timeout=5)
        directory = self.records / "grok" / host / "dead0001"
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(json.dumps({
            "platform": "grok",
            "session": host,
            "repo": str(self.repo),
            "state": "stopped",
            "holder_pid": dead.pid,
            "holder_instance_id": "i313host" + "0" * 16,
            "event_cursor": 0,
            "pending_permissions": [],
        }), encoding="utf-8")
        _result, listing = self.run_cli("grok", "list", "--include-dead")
        rows = {row["session"]: row for row in listing["rows"]}
        for _platform, session, issue_name, role in cases:
            self.assertEqual(rows[session]["name_role"], role)
            if issue_name is None:
                self.assertNotIn("issue_name", rows[session])
            else:
                self.assertEqual(rows[session]["issue_name"], issue_name)
        self.assertNotIn("issue_name", rows[host])
        self.assertEqual(rows[host]["name_role"], "host")
        self.assertTrue(rows[host]["host_class"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
