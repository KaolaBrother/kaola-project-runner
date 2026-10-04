#!/usr/bin/env python3
"""Issue #255: lifecycle state maintenance, continuity and migration.

The state tool runs as a CLI against isolated temporary projects. Holder and
Runner pieces run in-process against temporary record roots with stubbed
agents and a fake Sideagent socket; no live session or real `.kaola` is used.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
PLATFORMS = REPO / "platforms"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for name in CALLER_ENV:
    os.environ.pop(name, None)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


holder_module = load("kaola_acp_holder_255", REPO / "scripts" / "kaola-acp-holder.py")
acp_module = load("kaola_acp_255", REPO / "scripts" / "kaola-acp.py")
dispatch_module = load("kaola_dispatch_255", SCRIPT)


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env=env or {k: v for k, v in os.environ.items() if k not in CALLER_ENV})
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


AUTH = {"classes": {"Expert": "e", "Elite": "l", "Worker": "w"},
        "grants": [{"id": "codex/default", "state": "granted", "count": 1},
                   {"id": "zcode/default", "state": "granted"}],
        "elite_cap": 2}


class StateProject(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        return run(["state", *args], env)

    def init(self) -> None:
        code, out = self.state("init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
                               "--project", json.dumps({"code": "KT", "goal": "ship"}),
                               "--authorization", json.dumps(AUTH))
        self.assertEqual(code, 0, out)

    def update(self, writer: str, kind: str, ident: str, patch: dict, *extra: str,
               env: dict[str, str] | None = None) -> tuple[int, dict]:
        return self.state("update", "--file", str(self.file), "--writer", writer, "--source", "evt",
                          "--kind", kind, "--id", ident, "--set", json.dumps(patch), *extra, env=env)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def caller_env(self, session: str, holder: str) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": holder, "platform": "zcode",
                                                  "repo": str(self.repo), "session": session})
        return env


class StateTool(StateProject):
    def test_record_updates_conflicts_and_role_rules(self) -> None:
        self.init()
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "parser"})
        self.assertEqual((code, out["value"]["rev"]), (0, 1), out)
        code, out = self.update("host", "tasks", "t1", {"stage": "doing"})
        self.assertEqual((code, out["reason"]), (2, "expect-rev-required"))
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "0")
        self.assertEqual((code, out["reason"]), (3, "conflict"))
        self.assertEqual(out["current"]["rev"], 1)
        self.assertEqual(out["unapplied"], {"stage": "doing"})
        code, out = self.update("worker", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "writer-refused")
        code, out = self.update("sideagent", "tasks", "t1", {"goal": "other"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "host-turn-required")
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "review", "dispatch": ["i1"]},
                                "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        code, out = self.update("sideagent", "tasks", "t1", {"verdict": {"value": "accepted"}},
                                "--expect-rev", "2", "--host-turn", "host-turn-9")
        self.assertEqual(code, 0, out)
        record = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(record["verdict"], {"value": "accepted", "by": "host", "host_turn": "host-turn-9"})
        body = json.loads(self.doc()["body"])
        echo = [row for row in body["attention"] if row["why"] == "transcribed-check"]
        self.assertEqual(echo[0]["host_turn"], "host-turn-9", "the Host sees what was transcribed")
        code, out = self.update("host", "tasks", "t1", {"stage": "done"}, "--expect-rev", "3")
        self.assertEqual(code, 0, out)
        self.assertNotIn("transcribed", self.doc()["state"]["tasks"]["t1"])
        code, out = self.update("host", "tasks", "t1", {"stage": "shipped"}, "--expect-rev", "4")
        self.assertEqual(out["reason"], "invalid-input")

    def test_retire_and_late_event_cannot_reopen(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "g"})
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "1", "--evidence", "c1")
        self.assertEqual(out["reason"], "retire-unmet", "unfinished work is not retired")
        self.update("host", "tasks", "t1", {"stage": "done"}, "--expect-rev", "1")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "2", "--evidence", "commit c1")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertNotIn("t1", doc["state"]["tasks"])
        self.assertEqual(doc["state"]["retired"][-1]["evidence"], "commit c1")
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"})
        self.assertEqual(out["reason"], "record-retired", "a late event does not reopen a retired task")
        self.update("host", "decisions", "d1", {"owner": "user", "question": "Expert?"})
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "s",
                               "--kind", "decisions", "--id", "d1", "--expect-rev", "1", "--evidence", "x")
        self.assertEqual(out["reason"], "retire-unmet", "a pending decision stays")

    def test_alerts_coalesce_and_stay_after_acknowledgement(self) -> None:
        self.init()
        self.update("sideagent", "alerts", "quota-codex", {"level": "warn", "summary": "limit"})
        for _ in range(2):
            code, out = self.update("sideagent", "alerts", "quota-codex", {"ack": True}, "--coalesce")
            self.assertEqual(code, 0, out)
        alert = self.doc()["state"]["alerts"]["quota-codex"]
        self.assertEqual((alert["count"], alert["ack"], alert["level"]), (3, True, "warn"))
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator")
        self.assertEqual(out["special"]["alerts"][0]["id"], "quota-codex",
                         "an acknowledged alert is still reported")

    def test_sections_need_revision_and_host_ownership(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--section", "authorization", "--expect-revision", str(revision),
                               "--set", '{"elite_cap": 9}')
        self.assertEqual(out["reason"], "host-only")
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                               "--section", "project", "--expect-revision", str(revision - 1),
                               "--set", '{"goal": "new"}')
        self.assertEqual((code, out["reason"]), (3, "conflict"))
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner",
                               "--section", "project", "--expect-revision", str(revision),
                               "--set", '{"goal": "new", "code": null}')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["project"], {"goal": "new"})

    def test_binding_guards_late_writes_of_a_replaced_sideagent(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                               "--section", "sideagent", "--expect-revision", str(revision),
                               "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent-a",
                                                    "preset": "zcode/default", "state": "active"}))
        self.assertEqual(code, 0, out)
        old = self.caller_env("zcode-KT-sideagent-a", "holder-a")
        code, out = self.state("update", "--file", str(self.file), "--writer", "sideagent", "--source", "own",
                               "--section", "sideagent", "--expect-revision", str(revision + 1),
                               "--set", '{"holder_instance_id": "holder-a"}', env=old)
        self.assertEqual(code, 0, out)
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "todo", "goal": "g"},
                                "--host-turn", "h1", env=old)
        self.assertEqual(code, 0, out)
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "replace",
                               "--section", "sideagent", "--expect-revision", str(revision),
                               "--set", json.dumps({"session": "zcode-KT-sideagent-b",
                                                    "holder_instance_id": None, "state": "active"}))
        self.assertEqual(code, 0, out)
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "1", env=old)
        self.assertEqual(out["reason"], "binding-superseded", "the old Sideagent's late write is refused")
        new = self.caller_env("zcode-KT-sideagent-b", "holder-b")
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing", "wait": "capacity"},
                                "--expect-rev", "1", env=new)
        self.assertEqual(code, 0, out)
        code, out = self.update("host", "tasks", "t1", {"stage": "done"}, "--expect-rev", "2", env=new)
        self.assertEqual(out["reason"], "writer-mismatch")
        stray = self.caller_env("zcode-KT-i9-helper", "holder-h")
        code, out = self.update("sideagent", "alerts", "a1", {"level": "watch", "summary": "s"}, env=stray)
        self.assertEqual(out["reason"], "binding-superseded", "a helper is not the maintenance Sideagent")

    def test_concurrent_writers_never_lose_an_update(self) -> None:
        self.init()
        results: list[tuple[int, dict]] = []

        def write(index: int) -> None:
            results.append(self.update("sideagent", "alerts", f"a{index}",
                                       {"level": "watch", "summary": f"s{index}"}))

        threads = [threading.Thread(target=write, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertTrue(all(code == 0 for code, _ in results), results)
        doc = self.doc()
        self.assertEqual(sorted(doc["state"]["alerts"]), sorted(f"a{index}" for index in range(8)))
        self.assertEqual(doc["revision"], 9)
        revisions = sorted(out["revision"] for _, out in results)
        self.assertEqual(revisions, list(range(2, 10)), "each write saw the previous one")

    def test_large_state_projects_a_bounded_host_view(self) -> None:
        self.init()
        doc = self.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2", "holder_instance_id": "h"}
        for index in range(60):
            doc["state"]["tasks"][f"t{index}"] = {
                "stage": "doing", "goal": f"task {index}", "rev": 1, "source": "s",
                "dispatch": [f"item-{index}-{n}" for n in range(10)],
                "evidence": ["receipt " + "x" * 400 for _ in range(10)]}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.update("host", "tasks", "t0", {"next": "review"}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        self.assertGreater(out["file_bytes"], 65536)
        self.assertLess(out["body_bytes"], 65536)
        body = json.loads(self.doc()["body"])
        self.assertNotIn("evidence", json.dumps(body["tasks"]), "evidence stays out of the Host view")
        self.assertEqual(len(body["tasks"]), 60, "no responsibility is truncated away")
        self.assertEqual(body["authorization"], AUTH)
        holder_body, defect = holder_module.heartbeat_prompt_body(self.file)
        self.assertEqual((json.loads(holder_body), defect), (body, None),
                         "a new holder injects only the projected body")
        doc = self.doc()
        doc.pop("carrier")
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.update("host", "tasks", "t1", {"next": "x"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "carrier-limit",
                         "without a proven holder the file stays readable by the old holder")
        self.assertNotIn("x", self.doc()["state"]["tasks"]["t1"].get("next", ""))

    def test_host_view_over_the_injection_bound_is_refused_not_truncated(self) -> None:
        self.init()
        doc = self.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2"}
        for index in range(400):
            doc["state"]["tasks"][f"t{index}"] = {"stage": "todo", "goal": "g" * 200, "rev": 1,
                                                  "next": "n" * 200, "source": "s"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = self.update("host", "tasks", "t0", {"wait": "w"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "host-view-too-large")
        self.assertEqual(self.file.read_bytes(), before)

    def test_snapshot_does_not_overwrite_structured_state(self) -> None:
        self.init()
        snapshot = self.repo / "plain.json"
        snapshot.write_text(json.dumps({"project": {}}), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = run(["snapshot", "--state", str(snapshot), "--out", str(self.file)])
        self.assertEqual((code, out["reason"]), (2, "state-managed"))
        self.assertEqual(self.file.read_bytes(), before)

    def test_dispatch_reads_authorization_from_structured_state(self) -> None:
        self.init()
        code, out = run(["project", "--authorization", str(self.file), "--platforms", str(PLATFORMS)])
        self.assertEqual(code, 0, out)
        self.assertIn("codex/default", {row["id"] for row in out["candidates"]})

    def test_timer_template_check_is_exact(self) -> None:
        expected = ("/kaola-delegator\nKaola-Delegator inquiry: read "
                    f"{self.repo.resolve()}/.kaola/delegator-heartbeat.json on target local and run "
                    "the loaded Skill's standard inquiry.")
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator", "--body", expected + "\n")
        self.assertEqual((code, out["result"]), (0, "match"))
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator", "--body", expected + "\nalso check PRs")
        self.assertEqual((code, out["result"], out["expected"]), (1, "mismatch", expected))

    def test_delegator_view_reports_user_requirements_from_agents(self) -> None:
        self.init()
        (self.repo / "AGENTS.md").write_text(
            "# Project\n\n<!-- KPR-USER-REQUIREMENTS-START -->\n- Never log in.\n- Ask before release.\n"
            "<!-- KPR-USER-REQUIREMENTS-END -->\n", encoding="utf-8")
        self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g"})
        self.update("host", "holds", "h1", {"scope": "codex/default", "reason": "limit"})
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator")
        self.assertEqual(out["user_requirements"]["items"], ["- Never log in.", "- Ask before release."])
        self.assertEqual([row["id"] for row in out["todo"]], ["t1"])
        self.assertEqual(out["special"]["holds"][0]["id"], "h1")
        (self.repo / "AGENTS.md").unlink()
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator")
        self.assertIn("missing", out["user_requirements"], "a missing source is named")

    def test_check_finds_untraced_and_unassociated_work(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "g"})
        index = self.repo / "index.json"
        index.write_text(json.dumps({"items": [
            {"item_id": "i1", "status": "in-flight", "session": "codex-KT-i1-a"},
            {"item_id": "i2", "status": "in-flight", "task_id": "gone"}]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"session": "zcode-KT-helper", "session_role": "sideagent", "repo": str(self.repo),
             "state": "ready"}]}), encoding="utf-8")
        code, out = self.state("check", "--file", str(self.file), "--index", str(index), "--live", str(live))
        codes = {problem["code"] for problem in out["problems"]}
        self.assertTrue({"doing-untraced", "dispatch-unassociated", "dispatch-task-missing",
                         "sideagent-helper"} <= codes, codes)
        self.assertTrue(out["read_only"])


LEGACY_BODY = {
    "project": {"repo": "/abs/kt", "code": "KT", "goal": "close issues", "stop": "backlog empty",
                "rules": ["no Friday release"]},
    "authorization": AUTH,
    "active": [{"ref": "#12", "session": "claude-code-KT-i12-fix", "next": "accept", "evidence": "wt-12"},
               {"ref": "#12", "session": "codex-KT-i12-qa", "next": "qa"}],
    "pending": [{"duty": "integration QA", "scope": "#12", "owner": "Host", "evidence": "not run"},
                {"duty": "accept #13", "scope": "#13", "owner": "Host"}],
    "recovery": {"old_repo": "/abs/old"},
    "cadence_note": "every two hours",
}


class Migration(StateProject):
    def write_legacy(self, body: dict | str = LEGACY_BODY) -> bytes:
        text = json.dumps({"schema": "kaola-heartbeat-prompt/1",
                           "body": body if isinstance(body, str) else json.dumps(body)})
        self.file.write_text(text, encoding="utf-8")
        return self.file.read_bytes()

    def test_plan_then_write_preserves_duties_and_lists_unknowns(self) -> None:
        raw = self.write_legacy()
        index = self.repo / "index.json"
        index.write_text(json.dumps({"items": [
            {"item_id": "qa", "status": "in-flight", "session": "codex-KT-i12-qa"},
            {"item_id": "lost", "status": "unknown", "session": "droid-KT-i99-x"}]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"session": "zcode-KT-orchestrator-main", "host_class": True, "session_role": "host",
             "repo": str(self.repo), "state": "ready", "holder_instance_id": "host-1",
             "holder_features": ["heartbeat-state/2", "sideagent-relay/1"]},
            {"session": "zcode-KT-sideagent", "platform": "zcode", "session_role": "sideagent",
             "repo": str(self.repo), "state": "ready", "holder_instance_id": "side-1"}]}), encoding="utf-8")
        args = ["migrate", "--file", str(self.file), "--index", str(index), "--live", str(live)]
        code, out = self.state(*args)
        self.assertEqual((code, out["result"], out["writes"]), (0, "planned", False), out)
        self.assertEqual(self.file.read_bytes(), raw, "a plan writes nothing")
        code, out = self.state(*args, "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        doc = self.doc()
        state = doc["state"]
        self.assertEqual(doc["schema"], "kaola-heartbeat-prompt/2")
        self.assertEqual(state["authorization"], AUTH, "valid authorization is kept as is")
        self.assertEqual(state["project"]["rules"], ["no Friday release"], "adopted rules are not re-asked")
        self.assertEqual(state["tasks"]["#12"]["sessions"], ["claude-code-KT-i12-fix", "codex-KT-i12-qa"])
        self.assertEqual(state["tasks"]["#12"]["dispatch"], ["qa"])
        self.assertEqual(state["tasks"]["duty-1"]["stage"], "closeout")
        self.assertEqual(state["tasks"]["duty-2"]["stage"], "review")
        self.assertIn("legacy-cadence_note", state["unverified"], "an unknown key is kept for review")
        self.assertIn("index-lost", state["unverified"])
        self.assertIn("rules-source", state["unverified"])
        self.assertEqual(state["sideagent"]["session"], "zcode-KT-sideagent")
        self.assertEqual(doc["carrier"]["holder_instance_id"], "host-1")
        raw_copy = Path(state["recovery"]["migration"]["raw"])
        self.assertEqual(raw_copy.read_bytes(), raw, "the one raw migration evidence is kept")
        self.assertEqual(state["recovery"]["legacy"], {"old_repo": "/abs/old"})
        body = json.loads(doc["body"])
        self.assertEqual(body["authorization"], AUTH, "old readers of body still find authorization")
        code, again = self.state(*args, "--write")
        self.assertEqual(again["result"], "current", "a repeated migration changes nothing")

    def test_interrupted_migration_resumes_from_the_same_raw_evidence(self) -> None:
        raw = self.write_legacy()
        digest = hashlib.sha256(raw).hexdigest()
        stale = self.file.with_name(f"heartbeat-prompt.v1-{digest[:12]}.json")
        stale.write_bytes(raw)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        self.assertIn("live", out["unchecked"], "unchecked sources are named")
        stale.write_text("other", encoding="utf-8")
        self.write_legacy()
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(out["reason"], "raw-evidence-conflict")

    def test_unreadable_legacy_body_is_left_unchanged(self) -> None:
        raw = self.write_legacy("not json at all")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["reason"]), (2, "legacy-unreadable"))
        self.assertEqual(self.file.read_bytes(), raw)

    def test_old_holder_bound_keeps_the_file_small_without_a_capable_host(self) -> None:
        body = dict(LEGACY_BODY)
        body["active"] = [{"ref": f"#{n}", "session": f"codex-KT-i{n}-x", "evidence": "e" * 900}
                          for n in range(80)]
        raw = self.write_legacy(body)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(out["reason"], "carrier-limit")
        self.assertEqual(self.file.read_bytes(), raw)


class ExecuteSeats(StateProject):
    def test_bound_sideagent_is_exempt_and_helpers_count(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        run(["state", "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
             "--section", "sideagent", "--expect-revision", str(revision), "--set",
             json.dumps({"platform": "codex", "session": "codex-KT-sideagent", "state": "active",
                         "preset": "codex/default"})])
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": []}), encoding="utf-8")
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({"scope": "research", "repo": str(self.repo), "items": [
            {"item_id": "side", "preset": "codex/default", "session": "codex-KT-sideagent",
             "prompt": "maintain", "role": "sideagent", "task_id": "t-maint"},
            {"item_id": "w1", "preset": "codex/default", "session": "codex-KT-i1-a", "prompt": "a",
             "task_id": "t1", "output": "docs/a.md"},
            {"item_id": "helper", "preset": "codex/default", "session": "codex-KT-i1-b", "prompt": "b",
             "role": "sideagent"},
            {"item_id": "exp", "preset": "codex/default", "session": "codex-KT-i1-c", "prompt": "c",
             "requires": {"class": "Expert"}}]}), encoding="utf-8")
        code, out = run(["execute", "--plan", str(plan), "--authorization", str(self.file),
                         "--platforms", str(PLATFORMS), "--skills-root", str(self.repo / "skills"),
                         "--live", str(live), "--dry-run"])
        self.assertEqual(code, 0, out)
        items = {row["item_id"]: row for row in out["items"]}
        self.assertEqual(items["side"]["reason"], "dry-run", items)
        self.assertTrue(items["side"]["seat_exempt"])
        self.assertEqual(items["w1"]["reason"], "dry-run", "the exempt Sideagent left the one seat free")
        self.assertEqual((items["w1"]["task_id"], items["w1"]["output"]), ("t1", "docs/a.md"))
        self.assertEqual(items["helper"]["reason"], "count", "a second Sideagent-role item is a worker")
        self.assertIn("seat_note", items["helper"]["evidence"])
        self.assertEqual(items["exp"]["reason"], "requirement-unmet")
        self.assertIn("Expert", items["exp"]["detail"])


# -- holder: projected carrier, capability and relay --------------------------

class StubProc:
    pid = 25500


class StubAgent:
    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
        self.exit_code = None
        self.exit_signal = None
        self.stderr_pump = None
        self.malformed_lines = 0
        self.handler_errors = 0
        self.pending_out: dict = {}
        self.sent: list[dict] = []
        self.next_id = 0

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(self.next_id)] = method
        self.sent.append({"method": method, "id": self.next_id, "params": params})
        return self.next_id

    def send_message(self, message: dict) -> None:
        self.sent.append(message)

    def wait_response(self, request_id, timeout):
        time.sleep(0.01)
        return None

    def prompts(self) -> list[str]:
        return [m["params"]["prompt"][0]["text"] for m in self.sent if m.get("method") == "session/prompt"]


class FakeSideagent:
    """A Sideagent holder socket that records relay prompts."""

    def __init__(self, path: Path, busy: bool = False) -> None:
        self.path = path
        self.busy = busy
        self.prompts: list[dict] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(path))
        self.server.listen(4)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self) -> None:
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            with connection:
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                message = json.loads(data.decode())
                self.prompts.append(message)
                if self.busy:
                    reply = {"error": {"code": "prompt-in-progress"}, "outcome": "in_progress"}
                else:
                    reply = {"outcome": "in_progress", "prompt_fingerprint": f"sha256:{len(self.prompts)}"}
                connection.sendall(json.dumps(reply).encode() + b"\n")

    def close(self) -> None:
        self.server.close()
        try:
            self.path.unlink()
        except OSError:
            pass


class HolderRelay(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-holder-")
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        (self.repo / ".kaola").mkdir(parents=True)
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        self.records = root / "records"
        host_dir = self.records / "zcode" / "zcode-KT-orchestrator-main" / digest
        host_dir.mkdir(parents=True)
        args = argparse.Namespace(record_dir=str(host_dir), socket=str(root / "host.sock"),
                                  platform="zcode", session="zcode-KT-orchestrator-main",
                                  repo=str(self.repo), init_meta="", command="stub")
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-host-255"
        self.holder.state = "ready"
        self.holder.heartbeat_host = None
        self.side_dir = self.records / "zcode" / "zcode-KT-sideagent" / digest
        self.side_dir.mkdir(parents=True)
        sock_digest = hashlib.sha256(str(self.side_dir).encode()).hexdigest()[:24]
        self.side_sock = Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{sock_digest}.sock"
        self.fake: FakeSideagent | None = None

    def tearDown(self) -> None:
        if self.fake:
            self.fake.close()
        self.tmp.cleanup()

    def write_state(self, attention: list) -> None:
        body = json.dumps({"view": "host", "attention": attention, "tasks": []})
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2", "body": body,
            "state": {"sideagent": {"platform": "zcode", "session": "zcode-KT-sideagent",
                                    "holder_instance_id": "side-1", "state": "active"}}}), encoding="utf-8")

    def live_sideagent(self, busy: bool = False) -> None:
        (self.side_dir / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "repo": str(self.repo), "state": "ready",
            "holder_instance_id": "side-1", "holder_pid": os.getpid()}), encoding="utf-8")
        self.fake = FakeSideagent(self.side_sock, busy=busy)

    def event(self, session: str, kind: str, cursor: int) -> dict:
        return self.holder.op_worker_event({"kind": kind, "platform": "codex", "session": session,
                                            "repo": str(self.repo), "reason": "end_turn",
                                            "event_cursor": cursor})

    def finish_host_turn(self) -> None:
        fingerprint = self.holder.turn.get("fingerprint")
        self.holder.turn["active"] = False
        self.holder._worker_event_turn_end(fingerprint, "turn_completed")

    def test_record_advertises_features_and_big_state_file_is_read(self) -> None:
        self.holder.write_record()
        record = json.loads((Path(self.holder.args.record_dir) / "record.json").read_text())
        self.assertIn("heartbeat-state/2", record["holder_features"])
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        path.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/2", "body": "VIEW",
                                    "state": {"pad": "p" * 300000}}), encoding="utf-8")
        self.assertEqual(holder_module.heartbeat_prompt_body(path), ("VIEW", None))
        path.write_text(json.dumps({"body": "x" * 70000}), encoding="utf-8")
        body, defect = holder_module.heartbeat_prompt_body(path)
        self.assertIsNone(body)
        self.assertIn("65536", defect)

    def test_routine_events_go_to_the_bound_sideagent_not_the_host(self) -> None:
        self.write_state([])
        self.live_sideagent()
        receipt = self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(self.agent.prompts(), [], "the Host is not woken for a routine event")
        self.assertEqual(len(self.fake.prompts), 1)
        relay = self.fake.prompts[0]
        self.assertEqual(relay["op"], "prompt")
        self.assertEqual(relay["params"]["expected_holder_instance_id"], "side-1")
        self.assertIn("codex-KT-i1-a", relay["params"]["text"])
        self.assertEqual(receipt["relay"]["relayed"], 1)
        # The Sideagent's own turn end wakes the Host once (attention unseen) ...
        self.event("zcode-KT-sideagent", "idle", 9)
        self.assertEqual(len(self.agent.prompts()), 1)
        self.assertNotIn("codex/codex-KT-i1-a/idle/5",
                         [item["event_id"] for item in self.holder.pending_worker_events],
                         "the relayed event is confirmed by the Sideagent's turn end")
        self.finish_host_turn()
        # ... and later quiet turn ends do not.
        self.event("codex-KT-i1-b", "idle", 6)
        self.event("zcode-KT-sideagent", "idle", 12)
        self.assertEqual(len(self.agent.prompts()), 1, "unchanged attention does not wake the Host")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.write_state([{"kind": "decisions", "id": "d1", "why": "host-decision"}])
        self.event("zcode-KT-sideagent", "idle", 15)
        self.assertEqual(len(self.agent.prompts()), 2, "a new Host judgment wakes the Host")

    def test_busy_sideagent_keeps_events_and_dead_sideagent_falls_back_to_host(self) -> None:
        self.write_state([])
        self.live_sideagent(busy=True)
        self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(self.agent.prompts(), [])
        self.assertEqual(len(self.holder.pending_worker_events), 1, "busy is not lost")
        (self.side_dir / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "repo": str(self.repo), "state": "stopped",
            "holder_instance_id": "side-1", "holder_pid": os.getpid()}), encoding="utf-8")
        self.event("zcode-KT-sideagent", "terminated", 7)
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1)
        self.assertIn("codex-KT-i1-a", prompts[0], "the Host takes over undelivered events")
        self.assertIn("zcode-KT-sideagent", prompts[0])

    def test_without_a_binding_every_event_reaches_the_host(self) -> None:
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(
            json.dumps({"body": json.dumps({"project": {}})}), encoding="utf-8")
        self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(len(self.agent.prompts()), 1)


class ProcessPreservation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-stop-")
        self.dir = Path(self.tmp.name)
        self.child = subprocess.Popen(["sleep", "30"], start_new_session=True)
        time.sleep(0.2)

    def tearDown(self) -> None:
        self.child.kill()
        self.child.wait()
        self.tmp.cleanup()

    def spawn_record(self) -> None:
        entry = {"pid": self.child.pid, "pgid": self.child.pid, "spawned_at": int(time.time() * 1000)}
        (self.dir / "children.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")

    def child_start(self) -> str:
        table = acp_module.run_ps(["pid", "pgid", "state", "lstart"], env=acp_module.PS_ENV)
        for line in table.stdout.splitlines():
            fields = line.split(None, 3)
            if fields and fields[0] == str(self.child.pid):
                return fields[3].strip()
        self.fail("child not in the process table")

    def test_sideagent_record_spares_runner_holder_groups(self) -> None:
        self.spawn_record()
        host = acp_module.recorded_groups({"session_role": "host"}, self.dir)
        side = acp_module.recorded_groups({"session_role": "sideagent"}, self.dir)
        self.assertIn(self.child.pid, host, "a Host stop still sweeps its recorded inner sessions")
        self.assertNotIn(self.child.pid, side, "a Sideagent stop spares the workers it dispatched")
        live = {self.child.pid: [self.child.pid]}
        self.assertEqual(holder_module.runner_holder_groups(self.dir / "children.jsonl", live),
                         {self.child.pid})

    def test_other_children_of_a_sideagent_are_still_swept(self) -> None:
        record = {"session_role": "sideagent",
                  "agent_child_groups": {str(self.child.pid): {str(self.child.pid): self.child_start()}}}
        side = acp_module.recorded_groups(record, self.dir)
        self.assertIn(self.child.pid, side, "a detached agent child that is no Runner holder is swept")
        self.assertEqual(holder_module.runner_holder_groups(self.dir / "children.jsonl", {}), set())


class CarrierAnchor(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-anchor-")
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.repo_text = acp_module.canonical_dir(str(self.repo))
        self.args = argparse.Namespace(record_root=str(root / "records"), platform="codex",
                                       session="codex-KT-i3-worker")
        digest = hashlib.sha256(self.repo_text.encode()).hexdigest()[:16]
        self.side_dir = Path(self.args.record_root) / "zcode" / "zcode-KT-sideagent" / digest
        self.host_dir = Path(self.args.record_root) / "zcode" / "zcode-KT-orchestrator-main" / digest
        self.side_dir.mkdir(parents=True)
        self.host_dir.mkdir(parents=True)
        self.dispatcher = {"holder_instance_id": "side-1", "platform": "zcode",
                           "repo": self.repo_text, "session": "zcode-KT-sideagent"}
        (self.side_dir / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "holder_instance_id": "side-1", "holder_pid": os.getpid(),
            "heartbeat_host": {"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                               "repo": self.repo_text}}), encoding="utf-8")
        (self.host_dir / "record.json").write_text(json.dumps({
            "session_role": "host", "session": "zcode-KT-orchestrator-main",
            "holder_instance_id": "host-2", "holder_pid": os.getpid()}), encoding="utf-8")
        self.sock = acp_module.sock_path_for_directory(self.host_dir)
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        self.sock.touch()

    def tearDown(self) -> None:
        try:
            self.sock.unlink()
        except OSError:
            pass
        self.tmp.cleanup()

    def test_sideagent_dispatch_notifies_its_bound_host(self) -> None:
        target, failed = acp_module.sideagent_host_anchor(self.args, self.repo_text, self.dispatcher)
        self.assertIsNone(failed)
        self.assertEqual((target["platform"], target["session"]), ("zcode", "zcode-KT-orchestrator-main"))
        self.assertEqual(target["socket"], str(self.sock))

    def test_a_host_dispatcher_is_not_re_anchored(self) -> None:
        host = dict(self.dispatcher, session="zcode-KT-orchestrator-main", holder_instance_id="host-2")
        self.assertIsNone(acp_module.sideagent_host_anchor(self.args, self.repo_text, host))

    def test_missing_host_is_a_named_failure_not_a_silent_unbound_start(self) -> None:
        self.sock.unlink()
        target, failed = acp_module.sideagent_host_anchor(self.args, self.repo_text, self.dispatcher)
        self.assertIsNone(target)
        self.assertIn("socket", failed)


class RenderedGuidance(unittest.TestCase):
    """The generated Skills carry the lifecycle roles and commands the tool
    implements, inside their byte budgets."""

    ORCH = REPO / "skills" / "kaola-project-runner"
    DELEGATOR = REPO / "skills" / "kaola-delegator"

    def test_lifecycle_reference_is_generated_linked_and_bounded(self) -> None:
        template = (REPO / "templates/orchestrator/references/lifecycle-state.md").read_bytes()
        generated = (self.ORCH / "references/lifecycle-state.md").read_bytes()
        self.assertEqual(template, generated)
        self.assertLessEqual(len(generated), 8192)
        text = generated.decode()
        for term in ("kaola-heartbeat-prompt/2", "--expect-rev", "exits 3", "--host-turn",
                     "`attention`", "binding-superseded", "sideagent-relay/1", "heartbeat-state/2",
                     "record-retired", "host-view-too-large", "carrier-limit",
                     "heartbeat-prompt.v1-<sha12>.json", "`unverified`", "writer-refused",
                     "No synchronous Sideagent round trip"):
            self.assertIn(term, text)
        for kind in dispatch_module.RECORD_KINDS + dispatch_module.SECTIONS:
            self.assertIn(kind, text)
        skill = (self.ORCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("](references/lifecycle-state.md)", skill)
        self.assertLessEqual(len(skill.encode()), 17408)
        dispatch = (self.ORCH / "references/dispatch-collect.md").read_text(encoding="utf-8")
        self.assertIn("[lifecycle-state.md](lifecycle-state.md)", dispatch)
        self.assertIn("`state-managed`", dispatch)
        self.assertIn("`requirement-unmet`", dispatch)
        self.assertNotIn("It does not start other workers, dispatch", dispatch)
        skeleton = (self.ORCH / "references/heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertNotIn("Sideagent 仅提案", skeleton)
        self.assertIn("lifecycle-state.md", skeleton)

    def test_delegator_timer_sentence_matches_the_tool(self) -> None:
        report = (self.DELEGATOR / "references/inquiry-report.md").read_text(encoding="utf-8")
        locator = dispatch_module.TIMER_LOCATOR.format(repo="<repo>", target="<target>")
        self.assertIn(f"`{locator}`", report)
        self.assertIn("view --role delegator", report)
        for part in ("User special requirements", "Special situations", "Tasks in progress",
                     "Tasks to do", "outcomes and next steps"):
            self.assertIn(part, report)
        skill = (self.DELEGATOR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("](references/inquiry-report.md)", skill)
        self.assertLessEqual(len(skill.encode()), 4096)
        snapshot = (self.DELEGATOR / "references/snapshot.md").read_text(encoding="utf-8")
        self.assertIn("[inquiry-report.md](inquiry-report.md)", snapshot)
        self.assertLessEqual(len(snapshot.encode()), 8192)


if __name__ == "__main__":
    unittest.main(verbosity=2)
