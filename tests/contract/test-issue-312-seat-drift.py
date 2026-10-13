#!/usr/bin/env python3
"""Issue #312: a live seat whose dispatch issue differs from its name is an advisory.

The seat view flags the mismatch and a name whose issue has no active run.
It does not stop, rename, or refuse. A matching name and issue with an active
claim is not flagged. The orchestrator reference states the new-session rule.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
DISPATCH = PROJECT / "scripts" / "kaola-dispatch.py"
NAMES = PROJECT / "scripts" / "kaola-session-names.py"
RECORD = PROJECT / "scripts" / "kaola-record-contract.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
PLATFORMS = PROJECT / "platforms"
TEMPLATE = PROJECT / "templates" / "orchestrator" / "references" / "issue-dispatch.md"
RENDERED = PROJECT / "skills" / "kaola-project-runner" / "references" / "issue-dispatch.md"
PYTHON = sys.executable
REPO_ID = "https://github.com/example/consumer.git"
SENTENCE = (
    "new issue => new session; never retarget a live seat to another issue "
    "(exact-stop at a safe point, then a fresh standard-named session)."
)


def load(name: str, path: Path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def write_state(path: Path, issue: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Kaola-Workflow State\n\n"
        "## Project\n"
        "name: issue-test\n"
        "status: active\n\n"
        "## Claim Identity\n"
        f"claim_repository_id: {REPO_ID}\n\n"
        "## Sink\n"
        f"issue_number: {issue}\n",
        encoding="utf-8",
    )


def git_init(repo: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "init", "-q"],
        check=True, capture_output=True, text=True,
    )


def run_dispatch(args: list[str], env: dict[str, str]) -> tuple[int, str, dict]:
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args],
        capture_output=True, text=True, env=env,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"stdout was not JSON ({exc}): {proc.stdout}\n{proc.stderr}"
        ) from exc
    return proc.returncode, proc.stdout, payload


class SeatDriftAdvisory(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i312-")
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(os.path.realpath(self.root / "repo"))
        self.repo.mkdir()
        git_init(self.repo)
        write_state(self.repo / "kaola-workflow" / "issue-1720" / "workflow-state.md", 1720)
        write_state(self.repo / "kaola-workflow" / "issue-1758" / "workflow-state.md", 1758)
        self.names = load("kaola_session_names_312", NAMES)
        self.env = os.environ.copy()
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env.pop("KAOLA_ACP_DISPATCHER", None)

    def authorization(self, grants: list[dict]) -> Path:
        spec = importlib.util.spec_from_file_location("kpr_i312_record", RECORD)
        record = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(record)
        body, blockers, _ = record.migrate_authorization_limits({"grants": grants})
        self.assertEqual(blockers, [])
        path = self.root / "auth.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_live_seat_drift_is_advisory_and_does_not_stop(self) -> None:
        repo = str(self.repo)
        mismatch = "codex-PROJ-i1720-work"
        matching = "codex-PROJ-i1758-work"
        idle = "grok-PROJ-i1683-atomic"
        alias = "cursor-PROJ-i1733-joints"
        stopped = "codex-PROJ-i1720-old"
        host = "codex-PROJ-orchestrator-main"

        def live(platform: str, session: str, holder: str, preset: str, **extra: object) -> dict:
            return {
                "repo": repo, "identity": "verified", "state": "ready",
                "platform": platform, "session": session, "holder_instance_id": holder,
                "preset": preset, **extra,
            }

        live_file = self.root / "live.json"
        live_file.write_text(json.dumps({"rows": [
            live("codex", mismatch, "h-mismatch", "codex/default"),
            live("codex", matching, "h-match", "codex/default"),
            live("grok", idle, "h-idle", "grok/default"),
            live("cursor-cli", alias, "h-alias", "cursor-cli/default"),
            live("codex", stopped, "h-stopped", "codex/default", state="stopped"),
            {"repo": repo, "identity": "verified", "host_class": True, "state": "ready",
             "platform": "codex", "session": host, "holder_instance_id": "h-host",
             "preset": "codex/default"},
        ]}), encoding="utf-8")
        index = self.root / "index.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": repo, "items": [
                {"item_id": "mismatch", "task_id": "t-mismatch", "session": mismatch,
                 "holder_instance_id": "h-mismatch", "status": "in-flight", "issue": 1758,
                 "preset": "codex/default", "repo": repo},
                {"item_id": "match", "task_id": "t-match", "session": matching,
                 "holder_instance_id": "h-match", "status": "in-flight", "issue": 1758,
                 "preset": "codex/default", "repo": repo},
                {"item_id": "settled", "session": matching, "holder_instance_id": "h-match",
                 "status": "returned", "acceptance": "accepted", "issue": 9, "repo": repo},
                {"item_id": "other-holder", "session": matching, "holder_instance_id": "other",
                 "status": "in-flight", "issue": 1, "repo": repo},
                {"item_id": "idle", "task_id": "t-idle", "session": idle,
                 "holder_instance_id": "h-idle", "status": "in-flight", "issue": 1683,
                 "preset": "grok/default", "repo": repo},
                {"item_id": "alias", "task_id": "t-alias", "session": alias,
                 "holder_instance_id": "h-alias", "status": "unknown", "issue": 1759,
                 "preset": "cursor-cli/default", "repo": repo},
                {"item_id": "stopped", "session": stopped, "holder_instance_id": "h-stopped",
                 "status": "in-flight", "issue": 9, "repo": repo},
            ],
        }), encoding="utf-8")
        auth = self.authorization([
            {"id": "codex/default", "state": "granted", "count": 4},
            {"id": "grok/default", "state": "granted", "count": 1},
            {"id": "cursor-cli/default", "state": "granted", "count": 1},
        ])
        before = {live_file: live_file.read_bytes(), index: index.read_bytes()}
        code, _stdout, view = run_dispatch([
            "project", "--seats", "--repo", repo, "--authorization", str(auth),
            "--platforms", str(PLATFORMS), "--live", str(live_file), "--index", str(index),
        ], self.env)
        self.assertEqual(code, 0, view)
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertNotIn("result", view)
        self.assertFalse(any("issue-drift" in reason for reason in view["unknown_reasons"]))
        suggestion = self.names.SAFE_POINT_SUGGESTION
        by_session = {row["session"]: row for row in view["issue_drift"]}
        self.assertEqual(list(by_session), [mismatch, idle, alias])
        self.assertEqual(view["summary"]["issue_drift"], view["issue_drift"])
        flagged = by_session[mismatch]
        self.assertEqual(flagged["advisories"], ["dispatch-issue-mismatch"])
        self.assertEqual(flagged["name_issue"], 1720)
        self.assertEqual(flagged["dispatch_issue"], 1758)
        self.assertEqual(flagged["holder_instance_id"], "h-mismatch")
        self.assertEqual(flagged["platform"], "codex")
        self.assertEqual(flagged["suggestion"], suggestion)
        self.assertNotIn("dispatch_issues", flagged)
        idle_row = by_session[idle]
        self.assertEqual(idle_row["advisories"], ["no-active-run"])
        self.assertEqual(idle_row["name_issue"], 1683)
        self.assertEqual(idle_row["dispatch_issue"], 1683)
        self.assertEqual(idle_row["suggestion"], suggestion)
        alias_row = by_session[alias]
        self.assertEqual(alias_row["advisories"], ["dispatch-issue-mismatch"])
        self.assertNotIn("no-active-run", alias_row["advisories"])
        self.assertEqual(alias_row["name_issue"], 1733)
        self.assertEqual(alias_row["dispatch_issue"], 1759)
        sessions = {row["session"]: row for row in view["sessions"]}
        self.assertEqual(set(sessions), {mismatch, matching, idle, alias})
        for session in (mismatch, matching, idle, alias):
            self.assertEqual(sessions[session]["state"], "ready")
        self.assertNotIn(stopped, sessions)
        self.assertNotIn(host, sessions)
        self.assertNotIn("issue_drift", sessions[matching])
        self.assertEqual(sessions[mismatch]["issue_drift"]["advisories"], ["dispatch-issue-mismatch"])
        self.assertNotIn("session", sessions[mismatch]["issue_drift"])
        occupied = {row["session"]: row for row in view["summary"]["occupied"]}
        self.assertEqual(occupied[mismatch]["issue_drift"]["suggestion"], suggestion)
        self.assertNotIn("issue_drift", occupied[matching])
        self.assertIn(idle, occupied)
        self.assertIn(alias, occupied)

    def test_pure_drift_rules(self) -> None:
        names = self.names
        suggestion = names.SAFE_POINT_SUGGESTION
        both = names.seat_issue_drift(
            "codex-PROJ-i1720-work", "codex", [1758], active_claim_count=0,
            platforms_dir=PLATFORMS,
        )
        self.assertEqual(both["advisories"], ["dispatch-issue-mismatch", "no-active-run"])
        self.assertEqual(both["suggestion"], suggestion)
        alias = names.seat_issue_drift(
            "cursor-PROJ-i1733-joints", "cursor-cli", [1759], active_claim_count=0,
            platforms_dir=PLATFORMS,
        )
        self.assertEqual(alias["advisories"], ["dispatch-issue-mismatch"])
        self.assertIsNone(names.seat_issue_drift(
            "codex-PROJ-i1758-work", "codex", [1758], active_claim_count=2,
            platforms_dir=PLATFORMS,
        ))
        self.assertIsNone(names.seat_issue_drift(
            "codex-PROJ-i1758-work", "codex", [1758], active_claim_count=1,
            platforms_dir=PLATFORMS,
        ))
        self.assertIsNone(names.seat_issue_drift(
            "claude-PROJ-haiku-1749-x", "claude-code", [1758], active_claim_count=0,
            platforms_dir=PLATFORMS,
        ))
        several = names.seat_issue_drift(
            "codex-PROJ-i1720-work", "codex", [1758, 9], active_claim_count=1,
            platforms_dir=PLATFORMS,
        )
        self.assertEqual(several["advisories"], ["dispatch-issue-mismatch"])
        self.assertIsNone(several["dispatch_issue"])
        self.assertEqual(several["dispatch_issues"], [9, 1758])
        dispatch = load("kaola_dispatch_312", DISPATCH)
        self.assertIsNone(dispatch.normalize_issue(True))
        self.assertIsNone(dispatch.normalize_issue("nope"))
        self.assertEqual(dispatch.normalize_issue("1758"), 1758)
        self.assertEqual(dispatch.current_dispatch_issues({
            "open": {"session": "s", "holder_instance_id": "h", "status": "in-flight", "issue": 3},
            "settled": {"session": "s", "holder_instance_id": "h", "status": "returned",
                        "acceptance": "accepted", "issue": 9},
            "other": {"session": "s", "holder_instance_id": "other", "status": "in-flight", "issue": 1},
            "pending": {"session": "s", "holder_instance_id": "h", "status": "returned",
                        "acceptance": "pending", "issue": "4"},
        }, "s", "h"), [3, 4])

    def test_execute_copies_issue_and_does_not_refuse_or_stop(self) -> None:
        repo = str(self.repo)
        auth = self.authorization([{"id": "codex/default", "state": "granted", "count": 1}])
        live = self.root / "empty-live.json"
        live.write_text(json.dumps({"rows": []}), encoding="utf-8")
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": repo, "items": [{
                "item_id": "drift", "preset": "codex/default",
                "session": "codex-PROJ-i1720-work", "prompt": "look",
                "issue": 1758, "task_id": "t-drift",
            }],
        }), encoding="utf-8")
        index = self.root / "would-write.json"
        code, _stdout, payload = run_dispatch([
            "execute", "--plan", str(plan), "--authorization", str(auth),
            "--platforms", str(PLATFORMS), "--live", str(live),
            "--index", str(index), "--dry-run",
        ], self.env)
        self.assertEqual(code, 0, payload)
        self.assertFalse(index.exists())
        row = payload["items"][0]
        self.assertEqual(row["status"], "not-run")
        self.assertEqual(row["reason"], "dry-run")
        self.assertEqual(row["issue"], 1758)
        self.assertEqual(set(row["argv"]), {"status", "start", "send"})
        self.assertNotIn("stop", {argv[0] for argv in row["argv"].values()})
        self.assertNotIn("issue_drift", row)


class DriftContractText(unittest.TestCase):
    def test_rendered_reference_states_the_new_session_rule(self) -> None:
        template = TEMPLATE.read_text(encoding="utf-8")
        rendered = RENDERED.read_text(encoding="utf-8")
        self.assertEqual(template, rendered)
        self.assertIn(SENTENCE, normalize(rendered))
        self.assertIn(
            "A worker reassigned to a different issue is exact-stopped and a new-named session is started",
            normalize(rendered),
        )

    def test_docs_and_inventory(self) -> None:
        names = load("kaola_session_names_312_docs", NAMES)
        api = (PROJECT / "docs" / "api.md").read_text(encoding="utf-8")
        conventions = (PROJECT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(names.SAFE_POINT_SUGGESTION, api)
        self.assertIn("dispatch-issue-mismatch", api)
        self.assertIn("no-active-run", api)
        self.assertIn("does not exact-stop", api)
        self.assertIn("issue_drift", conventions)
        self.assertIn("the 1-80 `--session` syntax is the only validator", conventions)
        changelog = (PROJECT / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = changelog.split("## 0.9.9", 1)[0]
        self.assertIn("Seats: restart not required", unreleased)
        self.assertIn("Seats: restart required", unreleased)
        start = unreleased.index("Issue #312")
        bullet = normalize(unreleased[start:unreleased.find("\n\nSeats:", start)])
        self.assertIn("per-call", bullet)
        self.assertIn("is unchanged", bullet)
        self.assertIn("does not install", bullet)
        self.assertNotIn("restart required", bullet)
        holder = HOLDER.read_text(encoding="utf-8")
        self.assertNotIn("issue_drift", holder)
        self.assertNotIn("seat_issue_drift", holder)
        validate = (PROJECT / "scripts" / "validate.sh").read_text(encoding="utf-8")
        self.assertEqual(validate.count('"test-issue-312-seat-drift.py"'), 2)


if __name__ == "__main__":
    unittest.main()
