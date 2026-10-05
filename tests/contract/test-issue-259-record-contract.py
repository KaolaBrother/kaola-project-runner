#!/usr/bin/env python3
"""Issue #259: closed current-state contract, migration, and injection.

These cases sit on the existing state tool and ACP CLI. They do not add a
second QA framework. The shared-seat case records the current admission
result; it does not change that admission.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"
PLATFORMS = REPO / "platforms"
PYTHON = sys.executable
CITE = '{"path":"README.md","locator":"README.md"}'
CLASS_SENTENCES = {
    "Expert": "Expert is the stored grant sentence for this project.",
    "Elite": "Elite is the stored grant sentence for this project.",
    "Worker": "Worker is the stored grant sentence for this project.",
}
DEVIN_SCOPE = "devin/default account west only; do not widen this hold to the project"


CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")


def run_dispatch(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args], capture_output=True, text=True, timeout=60,
        env=env or {key: value for key, value in os.environ.items() if key not in CALLER_ENV})
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RecordContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i259-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.delegator = self.repo / ".kaola" / "delegator-heartbeat.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str) -> tuple[int, dict]:
        return run_dispatch(["state", *args])

    def init(self, authorization: dict | None = None) -> None:
        auth = authorization or {
            "classes": dict(CLASS_SENTENCES),
            "grants": [{"id": "codex/default", "state": "granted", "count": 1}],
            "elite_cap": 2,
        }
        code, out = self.state(
            "init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
            "--project", json.dumps({"code": "KT", "goal": "close the selected issues", "repo": str(self.repo)}),
            "--authorization", json.dumps(auth))
        self.assertEqual(code, 0, out)

    def test_unknown_nested_key_refuses_without_mutation(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--set",
            json.dumps({"stage": "todo", "goal": "repair", "narrative": "old story"}))
        self.assertEqual(out["reason"], "invalid-input", out)
        self.assertIn("path", out)
        self.assertIn("recovery", out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--set", json.dumps({"stage": "todo", "goal": "repair"}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["goal"], "repair")

    def test_stored_class_sentences_stay_and_capability_is_separate(self) -> None:
        self.init({
            "classes": dict(CLASS_SENTENCES),
            "grants": [
                {"id": "droid/default", "state": "granted", "count": 2, "shared_seat": "droid"},
                {"id": "droid/opus", "state": "granted", "count": 2, "shared_seat": "droid"},
            ],
            "elite_cap": 2,
        })
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["authorization"]["classes"], CLASS_SENTENCES)
        self.assertNotIn("paraphrase", json.dumps(out["authorization"]["classes"]))
        seat = out["capability"]["shared_seats"][0]
        self.assertEqual((seat["seat"], seat["count"]), ("droid", 2))
        code, side = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, side)
        self.assertEqual(side["state"]["authorization"]["classes"], CLASS_SENTENCES)
        code, delegator = self.state("view", "--file", str(self.file), "--role", "delegator",
                                     "--repo", str(self.repo))
        self.assertEqual(code, 0, delegator)
        self.assertIn("doing", delegator)
        self.assertNotIn("retired", delegator)

    def test_shared_seat_group_is_still_admitted_as_one(self) -> None:
        """Owner grant count is 2. Current admission still returns shared-occupied."""
        dispatch = load_module(DISPATCH, "kpr_i259_dispatch")
        grants = [
            {"id": "droid/default", "state": "granted", "count": 2, "shared_seat": "droid"},
            {"id": "droid/opus", "state": "granted", "count": 2, "shared_seat": "droid"},
            {"id": "droid/core", "state": "granted", "count": 2, "shared_seat": "droid"},
        ]
        catalog = {grant["id"]: {"class": "Elite"} for grant in grants}
        rows = [{
            "session": "droid-KT-one", "state": "ready", "platform": "droid",
            "preset": "droid/default", "repo": str(self.repo),
        }]
        used_count, _seats, occupied, unnamed = dispatch.live_occupancy(
            rows, str(self.repo), catalog, grants)
        self.assertEqual(occupied, {"droid"})
        self.assertEqual(used_count["droid/default"], 1)
        item = {
            "preset": "droid/opus", "_shared_seat": "droid", "_count": 2,
            "_platform": "droid", "_pool": True,
        }
        self.assertEqual(
            dispatch.held_refusal(item, used_count, 1, occupied, unnamed, None, grants, catalog),
            "shared-occupied")

    def test_stage_warning_clears_only_on_a_sourced_stage(self) -> None:
        body = {"project": {"code": "KT"}, "authorization": {"elite_cap": 2},
                "pending": [{"duty": "apply the named repair", "owner": "Host"}]}
        self.file.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1", "body": json.dumps(body)}),
                             encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertIn("duty-1-stage", self.doc()["state"]["unverified"])
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
            "--kind", "tasks", "--id", "duty-1", "--expect-rev", "1",
            "--set", json.dumps({"stage": "doing"}))
        self.assertEqual(code, 0, out)
        self.assertIn("duty-1-stage", self.doc()["state"]["unverified"])
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "host-turn",
            "--kind", "tasks", "--id", "duty-1", "--expect-rev", "2",
            "--set", json.dumps({"stage": "doing", "next": "apply the repair"}))
        self.assertEqual(code, 0, out)
        self.assertNotIn("duty-1-stage", self.doc()["state"]["unverified"])

    def test_closed_task_leaves_and_pending_goal_stays(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "done-one",
                   "--set", json.dumps({"stage": "done", "goal": "finished note",
                                        "verdict": {"value": "accepted"}}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "open-one",
                   "--set", json.dumps({"stage": "doing", "goal": "apply repair", "next": "seat the repair"}))
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "done-one", "--expect-rev", "1", "--evidence", "reviewed",
            "--cite", CITE)
        self.assertEqual(code, 0, out)
        state = self.doc()["state"]
        self.assertNotIn("done-one", state["tasks"])
        self.assertEqual(state["tasks"]["open-one"]["goal"], "apply repair")
        stone = state["retired"][-1]
        self.assertEqual(stone["cite"]["path"], "README.md")
        self.assertNotIn("evidence", stone)

    def test_devin_hold_scope_is_not_shortened(self) -> None:
        self.init()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "holds", "--id", "devin-west",
            "--set", json.dumps({"preset": "devin/default", "scope": DEVIN_SCOPE, "owner": "host",
                                 "reason": "account limit"}))
        self.assertEqual(code, 0, out)
        view = json.loads(self.doc()["body"])
        shown = view["holds"][0]
        self.assertEqual(shown["preset"], "devin/default")
        self.assertEqual(shown["scope"], DEVIN_SCOPE)

    def test_later_dispatch_batch_keeps_the_live_ref(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t1",
                   "--set", json.dumps({"stage": "doing", "goal": "g", "dispatch": ["first-live"]}))
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--expect-rev", "1",
            "--set", json.dumps({"dispatch": ["second-batch"]}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["dispatch"], ["first-live", "second-batch"])

    def test_repair_result_keeps_the_delivery_goal_open(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t1",
                   "--set", json.dumps({"stage": "review", "goal": "close the selected issues",
                                        "next": "review the research"}))
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "host-turn-2",
            "--kind", "tasks", "--id", "t1", "--expect-rev", "1",
            "--set", json.dumps({"verdict": {"value": "repair", "why": "named repair remains"},
                                 "next": "seat the named repair"}))
        self.assertEqual(code, 0, out)
        task = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(task["goal"], "close the selected issues")
        self.assertEqual(task["next"], "seat the named repair")
        why = [row["why"] for row in json.loads(self.doc()["body"])["attention"] if row["id"] == "t1"]
        self.assertIn("delivery-open", why)

    def test_sideagent_idle_binding_is_not_a_missing_binding(self) -> None:
        self.init()
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertIn("no binding", out["sideagent_maintenance"])
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-node",
                                        "preset": "zcode/default", "state": "active", "mode": "node"}))
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertIn("idle binding is not missing", out["sideagent_maintenance"])

    def test_delegator_relay_tokens_and_a_prose_status_blocks_the_write(self) -> None:
        self.delegator.write_text(json.dumps({
            "project": {"goal": "close the selected issues"},
            "host": {"platform": "codex", "session": "codex-KT-host"},
            "authorization": {"elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus", "droid/core"],
                "count": 2, "class": "Elite",
            }]},
            "watch": {
                "relay-1": {"relay_status": "Pending the design note", "summary": "hand off"},
            },
        }), encoding="utf-8")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(out["result"], "blocked", out)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.delegator.write_text(json.dumps({
            "revision": 0,
            "project": {"goal": "close the selected issues"},
            "authorization": {"elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus", "droid/core"],
                "count": 2, "class": "Elite",
            }]},
            "watch": {"relay-1": {"kind": "relay", "status": "pending", "summary": "hand off",
                                  "next": "host adopts"}},
        }), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "host record", "--expect-revision", "0",
            "--set", json.dumps({"watch": {"relay-1": {"status": "adopted", "next": "repair seated",
                                                       "evidence": "host:tasks/t1"}}})])
        self.assertEqual(code, 0, out)
        watched = json.loads(self.delegator.read_text())["watch"]["relay-1"]["status"]
        self.assertEqual(watched, "adopted")

    def test_cleanup_keeps_pending_duties_and_does_not_delete_hash_copies(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["open-one"] = {
            "stage": "todo", "goal": "still open", "rev": 1, "writer": "host", "source": "s"}
        doc["state"]["recovery"] = {
            "legacy": {"protected_untracked": ["notes/local.txt"], "completion_evidence": "old prose"},
            "migration": {"raw": "heartbeat-prompt.v1-aaaaaaaaaaaa.json"},
        }
        doc["state"]["retired"] = [{
            "kind": "tasks", "id": "old", "outcome": "accepted", "at": "2026-10-05T00:00:00+00:00",
            "evidence": "do not keep this prose", "cite": {"path": "README.md", "locator": "README.md"},
        }]
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        stale = self.file.with_name("heartbeat-prompt.v1-aaaaaaaaaaaa.json")
        stale.write_text("unique-old-bytes", encoding="utf-8")
        code, out = self.state("backups", "--file", str(self.file))
        self.assertEqual(code, 0, out)
        self.assertFalse(out["deleted"])
        self.assertFalse(out["backups"][0]["trusted"])
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        state = self.doc()["state"]
        self.assertEqual(state["tasks"]["open-one"]["goal"], "still open")
        self.assertEqual(state["recovery"]["protected_untracked"], ["notes/local.txt"])
        self.assertNotIn("legacy", state["recovery"])
        self.assertNotIn("evidence", state["retired"][0])
        self.assertEqual(stale.read_text(encoding="utf-8"), "unique-old-bytes")
        self.assertFalse(list(self.file.parent.glob("heartbeat-prompt.v2-*.json")))

    def test_malformed_hold_stays_visible_and_timer_mismatch_does_not_block_stop(self) -> None:
        self.init()
        self.file.write_text(json.dumps(self.doc()), encoding="utf-8")
        doc = self.doc()
        doc["state"]["holds"]["partial"] = {"reason": "unreadable hold", "rev": 1}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["holds"][0]["id"], "partial")
        code, timer = self.state(
            "timer", "--repo", str(self.repo), "--target", "local", "--entry", "/kaola-delegator",
            "--body", "not the locator")
        self.assertEqual(timer["result"], "mismatch")
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "owner stop",
            "--section", "project", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"stop": "owner stop now"}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["project"]["stop"], "owner stop now")

    def test_v090_execute_reads_the_new_file_both_ways(self) -> None:
        auth = {
            "classes": dict(CLASS_SENTENCES),
            "grants": [
                {"id": "codex/default", "state": "granted", "count": 1},
                {"id": "zcode/default", "state": "paused", "count": 1},
            ],
            "elite_cap": 2,
        }
        self.init(auth)
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t-live",
                   "--set", json.dumps({"stage": "doing", "goal": "keep the seat",
                                        "dispatch": ["i-hold"]}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "holds", "--id", "devin-west",
                   "--set", json.dumps({"preset": "codex/default", "scope": DEVIN_SCOPE,
                                        "owner": "host", "reason": "account"}))
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(self.repo.resolve()),
            "items": [
                {"item_id": "i-hold", "preset": "codex/default", "session": "codex-KT-i259-hold",
                 "prompt": "held", "task_id": "t-live"},
                {"item_id": "i-pause", "preset": "zcode/default", "session": "zcode-KT-i259-pause",
                 "prompt": "paused", "task_id": "t-live"},
                {"item_id": "i-missing", "preset": "zcode/default", "session": "zcode-KT-i259-miss",
                 "prompt": "missing", "task_id": "t-missing"},
            ],
        }), encoding="utf-8")
        direct = self.repo / "auth.json"
        direct.write_text(json.dumps(auth), encoding="utf-8")
        old = Path(self.tmp.name) / "v090-dispatch.py"
        old.write_bytes(subprocess.check_output(["git", "show", "v0.9.0:scripts/kaola-dispatch.py"]))
        current_auth = self.execute(DISPATCH, plan, self.file, None)
        current_state = self.execute(DISPATCH, plan, direct, self.file)
        old_auth = self.execute(old, plan, self.file, None)
        old_state = self.execute(old, plan, direct, self.file)
        for label, payload in (("current-auth", current_auth), ("current-state", current_state),
                               ("v090-auth", old_auth), ("v090-state", old_state)):
            self.assertEqual(payload["returncode"], 0, label)
        self.assertEqual(self.facts(current_auth), self.facts(old_auth))
        self.assertEqual(self.facts(current_state), self.facts(old_state))
        auth_facts = {row["item_id"]: row for row in self.facts(current_auth)}
        state_facts = {row["item_id"]: row for row in self.facts(current_state)}
        for item_id in ("i-hold", "i-pause", "i-missing"):
            self.assertEqual(auth_facts[item_id]["reason"], state_facts[item_id]["reason"])
            self.assertEqual(auth_facts[item_id]["holds"], state_facts[item_id]["holds"])
            self.assertEqual(auth_facts[item_id]["task_id"], state_facts[item_id]["task_id"])
        facts = state_facts
        self.assertEqual(facts["i-hold"]["reason"], "on-hold")
        self.assertEqual(facts["i-hold"]["holds"], ["devin-west"])
        self.assertEqual(facts["i-pause"]["reason"], "paused")
        self.assertIsNone(facts["i-pause"].get("task_note"))
        self.assertIn("t-missing", facts["i-missing"]["task_note"])

    def execute(self, script: Path, plan: Path, authorization: Path, state: Path | None) -> dict:
        argv = [PYTHON, str(script), "execute", "--plan", str(plan), "--authorization", str(authorization),
                "--platforms", str(PLATFORMS), "--dry-run"]
        if state is not None:
            argv.extend(["--state", str(state)])
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        try:
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError as exc:
            raise AssertionError(f"{script.name} not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
        payload["returncode"] = proc.returncode
        payload["stderr"] = proc.stderr
        return payload

    def facts(self, payload: dict) -> list[dict]:
        rows = []
        for item in payload.get("items") or []:
            evidence = item.get("evidence") or {}
            rows.append({
                "item_id": item.get("item_id"),
                "reason": item.get("reason"),
                "holds": item.get("holds"),
                "task_id": item.get("task_id"),
                "task_note": (evidence.get("task_note") if isinstance(evidence, dict) else None),
            })
        return rows

    def test_v090_holder_injects_stored_body_and_the_new_holder_projects(self) -> None:
        self.init()
        doc = self.doc()
        doc["body"] = "STORED-BODY-SENTINEL"
        doc["state"]["tasks"]["t1"] = {
            "stage": "doing", "goal": "projected-goal-marker", "rev": 1, "writer": "host", "source": "s"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        old_path = Path(self.tmp.name) / "v090-holder.py"
        old_path.write_bytes(subprocess.check_output(["git", "show", "v0.9.0:scripts/kaola-acp-holder.py"]))
        old = load_module(old_path, "kpr_i259_v090_holder")
        old_body, old_defect = old.heartbeat_prompt_body(self.file)
        self.assertEqual((old_body, old_defect), ("STORED-BODY-SENTINEL", None))
        new = load_module(HOLDER, "kpr_i259_holder")
        new_body, new_defect = new.heartbeat_prompt_body(self.file)
        self.assertIsNone(new_defect)
        self.assertNotIn("STORED-BODY-SENTINEL", new_body or "")
        self.assertIn("projected-goal-marker", new_body or "")
        self.assertIn(CLASS_SENTENCES["Elite"], new_body or "")

    def test_a_migrate_note_is_not_a_seat_and_a_session_name_still_needs_live(self) -> None:
        self.init()
        note = "no in-flight seats (v1 note, stopped)"
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "migrate-note",
            "--kind", "tasks", "--id", "noted", "--set",
            json.dumps({"stage": "done", "goal": "close the note", "verdict": {"value": "accepted"},
                        "sessions": [note]}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "retire-note",
            "--kind", "tasks", "--id", "noted", "--expect-rev", "1", "--evidence", "note is not a seat",
            "--cite", CITE)
        self.assertEqual(code, 0, out)
        self.assertNotIn("noted", self.doc()["state"]["tasks"])
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "real-seat",
            "--kind", "tasks", "--id", "seated", "--set",
            json.dumps({"stage": "done", "goal": "close the seat", "verdict": {"value": "accepted"},
                        "sessions": ["codex-KT-real"]}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "retire-seat",
            "--kind", "tasks", "--id", "seated", "--expect-rev", "1", "--evidence", "needs the live row",
            "--cite", CITE)
        self.assertEqual(out["reason"], "retire-unmet", out)
        self.assertIn("--live", out["detail"])
        self.assertIn("seated", self.doc()["state"]["tasks"])

    def test_settled_task_and_retirement_leave_the_routine_view(self) -> None:
        """A node checkpoint must not return an already accepted task or its
        retirement as maintenance-returned, and that stopped row leaves the view."""
        self.init()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
            "--section", "sideagent", "--expect-revision", "1", "--set",
            json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "design",
            "--kind", "tasks", "--id", "design-1", "--set",
            json.dumps({"stage": "done", "goal": "stopped design row", "verdict": {"value": "accepted"}}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "host-retire",
            "--kind", "tasks", "--id", "design-1", "--expect-rev", "1",
            "--evidence", "accepted design row", "--cite", CITE)
        self.assertEqual(code, 0, out)
        stone = self.doc()["state"]["retired"][-1]
        self.assertNotEqual(stone.get("writer_holder"), "node-1")
        ident = f"host:retired/tasks/design-1@{stone['host_revision']}"
        doc = self.doc()
        doc["state"].setdefault("alerts", {})["maintenance-returned"] = {
            "level": "warn", "owner": "host", "summary": "1 maintenance input(s) not applied by a node",
            "inputs": {ident: {"why": "is not a retirement by this node", "batch": "old"},
                       "host:tasks/design-1@1": {"why": "not-in-batch", "batch": "old"}},
            "rev": 1, "source": "old", "writer": "sideagent", "writer_holder": "node-0"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, pending = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, pending)
        entries = []
        for item in pending["pending_host_changes"]:
            if "design-1" in item:
                entries.append({"input": item, "applied": ["retired:tasks/design-1"]})
            elif item.startswith("host:section/"):
                name = item.split("/", 2)[1].split("@", 1)[0]
                entries.append({"input": item, "retained": f"section/{name}"})
            else:
                body = item[len("host:"):].split("@", 1)[0]
                entries.append({"input": item, "retained": body})
        entries.append({"input": "host:tasks/design-1@1", "applied": ["retired:tasks/design-1"]})
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({
            "holder_instance_id": "node-1", "platform": "zcode", "repo": str(self.repo),
            "session": "zcode-KT-sideagent"})
        code, out = run_dispatch([
            "state", "checkpoint", "--file", str(self.file), "--writer", "sideagent",
            "--source", "b-settled", "--batch", "b-settled",
            "--through-host-revision", str(self.doc()["host_revision"]),
            "--entries", json.dumps(entries)], env)
        self.assertEqual(code, 0, out)
        returned = out["value"]["returned_to_host"]
        self.assertFalse([key for key in returned if "design-1" in key], returned)
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})
        view = json.loads(self.doc()["body"])
        self.assertNotIn("design-1", [row.get("id") for row in view.get("tasks") or []])
        self.assertNotIn("design-1", json.dumps(view.get("alerts")))
        self.assertNotIn("maintenance-returned", [row.get("id") for row in view.get("attention") or []])

    def test_delegator_migration_keeps_duties_and_blocks_unmapped_text(self) -> None:
        self.delegator.write_text(json.dumps({
            "revision": 2,
            "project": {"goal": "close the selected issues", "user_language": "zh"},
            "host": {"platform": "codex", "session": "codex-KT-host"},
            "day_start": {"action": "reconcile_then_open_intake", "state": "pending", "evidence": "owner-day"},
            "day_end": {"action": "pause_new_claims_keep_inflight", "state": "confirmed",
                        "host_ack": "host-ack", "claim_check": "none"},
            "final_stop": "stop at the owner boundary",
            "authorization": {"elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus"], "count": 2, "class": "Elite",
                "lifetime": "task", "special_requirements": "owner limit",
            }]},
            "watch": {"relay-1": {
                "kind": "relay", "status": "pending", "summary": "owner constraint",
                "detail": "pending relay text", "evidence": "owner msg 3", "next": "host adopts",
                "report": {"old": True},
            }},
        }), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        doc = json.loads(self.delegator.read_text(encoding="utf-8"))
        self.assertEqual(doc["project"]["user_language"], "zh")
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertEqual(view["project"]["user_language"], "zh")
        self.assertEqual(doc["day_start"]["evidence"], "owner-day")
        self.assertEqual(doc["day_end"]["host_ack"], "host-ack")
        self.assertEqual(doc["final_stop"], "stop at the owner boundary")
        self.assertEqual(doc["authorization"]["elite_grants"][0]["special_requirements"], "owner limit")
        self.assertEqual(doc["watch"]["relay-1"]["detail"], "pending relay text")
        self.assertIn("watch.relay-1.report", out["dropped"])
        self.delegator.write_text(json.dumps({
            "revision": 1,
            "watch": {"relay-1": {"kind": "relay", "status": "pending", "narrative": "unmapped owner text",
                                  "next": "deliver"}},
        }), encoding="utf-8")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator)])
        self.assertEqual(out["result"], "blocked", out)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.assertTrue(any("narrative" in item.get("path", "") for item in out["blockers"]))

    def test_delegator_update_and_view_are_closed(self) -> None:
        self.delegator.write_text(json.dumps({
            "revision": 0, "project": {"goal": "close the selected issues"},
            "authorization": {"elite_grants": [{"preset_ids": ["droid/default"], "count": 2, "class": "Elite"}]},
            "watch": {"relay-1": {"kind": "relay", "status": "pending", "summary": "text", "next": "send"}},
        }), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("user_language", json.loads(self.delegator.read_text(encoding="utf-8"))["project"])
        revision = json.loads(self.delegator.read_text(encoding="utf-8"))["revision"]
        before = self.delegator.read_bytes()
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "s", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-2": {"kind": "journal", "status": "Pending note"}}})])
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.delegator.read_bytes(), before)
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "s", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-1": {"status": "adopted", "next": "done"}}})])
        self.assertNotEqual(code, 0, out)
        self.assertIn("evidence", out["detail"])
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "s", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-1": {"status": "sent", "next": "wait for host"}}})])
        self.assertEqual(code, 0, out)
        revision = json.loads(self.delegator.read_text(encoding="utf-8"))["revision"]
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "host record", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-1": {"status": "adopted", "evidence": "host:tasks/t1"}}})])
        self.assertEqual(code, 0, out)
        doc = json.loads(self.delegator.read_text(encoding="utf-8"))
        doc["authorization"]["secret_grant"] = "no"
        doc["journal"] = ["hand"]
        self.delegator.write_text(json.dumps(doc), encoding="utf-8")
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertEqual(code, 0, view)
        self.assertNotIn("secret_grant", json.dumps(view["authorization"]))
        self.assertTrue(any(item["path"] == "authorization.secret_grant" for item in view["unknown"]))
        self.assertTrue(any(item["path"] == "journal" for item in view["unknown"]))

    def test_capability_keeps_worker_pool_presets_and_stored_classes(self) -> None:
        self.init({
            "classes": dict(CLASS_SENTENCES),
            "capability_summary": {"presets": [
                "codex/default", "codex/luna", "devin/default", "dsh/default",
                "opencode/default", "zcode/default",
            ]},
            "grants": [{"id": "codex/default", "state": "paused", "count": 1}],
            "paused": ["codex/default"],
            "elite_cap": 2,
        })
        view = json.loads(self.doc()["body"])
        presets = view["capability"]["presets"]
        for preset in ("codex/luna", "devin/default", "dsh/default", "opencode/default", "zcode/default"):
            self.assertIn(preset, presets)
        self.assertNotIn("codex/default", presets)
        self.assertEqual(view["authorization"]["classes"]["Worker"], CLASS_SENTENCES["Worker"])

    def test_nested_types_are_refused_and_bytes_stay(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1",
            "--set", json.dumps({"stage": "todo", "goal": "g", "next": {"history": [{"turn": 1}]}}))
        self.assertNotEqual(code, 0, out)
        self.assertIn("path", out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--section", "sideagent", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-node", "state": "active",
                                 "narrative": "free"}))
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_cleanup_names_removals_and_legacy_refusal_says_how(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["t1"] = {
            "stage": "doing", "goal": "keep", "next": "continue", "legacy": {"note": "old"},
            "rev": 1, "writer": "host", "source": "s",
        }
        doc["state"]["recovery"] = {"legacy": {"completion_evidence": "old"}, "v1_host": {"session": "x"}}
        doc["state"]["unverified"] = {"t1-stage": {"summary": "old warning", "locator": "pending[0]"}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--expect-rev", "1", "--set", json.dumps({"next": "still open"}))
        self.assertNotEqual(code, 0, out)
        self.assertIn("state migrate", out.get("recovery", ""))
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        removed = " ".join(out.get("removed") or [])
        self.assertIn("tasks.t1.legacy", removed)
        self.assertIn("recovery.legacy", removed)
        self.assertIn("recovery.v1_host", removed)
        self.assertIn("unverified.t1-stage", removed)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["goal"], "keep")
        self.assertNotIn("t1-stage", self.doc()["state"].get("unverified") or {})

    def test_cancelled_seat_and_keep_open_stay_unaccounted(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "live-cancel",
                   "--set", json.dumps({"stage": "doing", "goal": "stop the seat",
                                        "next": "stop codex-KT-live", "sessions": ["codex-KT-live"],
                                        "verdict": {"value": "cancelled"}}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "kept",
                   "--set", json.dumps({"stage": "done", "goal": "still open", "keep_open": True,
                                        "next": "new obligation", "verdict": {"value": "accepted"}}))
        code, pending = self.state("view", "--file", str(self.file), "--role", "sideagent")
        entries = [{"input": item, "retained": item[len("host:"):].split("@", 1)[0]}
                   for item in pending["pending_host_changes"] if item.startswith("host:section/")]
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({
            "holder_instance_id": "node-1", "platform": "zcode", "repo": str(self.repo),
            "session": "zcode-KT-sideagent"})
        code, out = run_dispatch([
            "state", "checkpoint", "--file", str(self.file), "--writer", "sideagent",
            "--source", "open-duties", "--batch", "open-duties",
            "--through-host-revision", str(self.doc()["host_revision"]),
            "--entries", json.dumps(entries)], env)
        self.assertEqual(code, 0, out)
        returned = out["value"]["returned_to_host"]
        self.assertTrue(any("live-cancel" in key for key in returned), returned)
        self.assertTrue(any(key.startswith("host:tasks/kept@") for key in returned), returned)
        self.assertFalse(out["value"]["verified"])

    def test_node_process_write_does_not_change_delivery_open(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t3",
                   "--set", json.dumps({"stage": "review", "goal": "close the selected issues",
                                        "next": "review the research"}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "host-turn",
                   "--kind", "tasks", "--id", "t3", "--expect-rev", "1",
                   "--set", json.dumps({"verdict": {"value": "repair", "why": "named repair remains"},
                                        "next": "seat the named repair"}))
        first = [row for row in json.loads(self.doc()["body"])["attention"] if row["why"] == "delivery-open"]
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({
            "holder_instance_id": "node-1", "platform": "zcode", "repo": str(self.repo),
            "session": "zcode-KT-sideagent"})
        code, out = run_dispatch([
            "state", "update", "--file", str(self.file), "--writer", "sideagent",
            "--source", "stop confirmed", "--kind", "tasks", "--id", "t3", "--expect-rev", "2",
            "--set", json.dumps({"wait": "codex-KT-repair stopped"})], env)
        self.assertEqual(code, 0, out)
        second = [row for row in json.loads(self.doc()["body"])["attention"] if row["why"] == "delivery-open"]
        self.assertEqual(first, second)
        self.assertEqual(self.doc()["state"]["tasks"]["t3"]["goal"], "close the selected issues")

    def test_node_running_follows_the_live_record(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-node", "state": "active",
                                        "mode": "node"}))
        root = self.repo / "records"
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_RECORD_ROOT"] = str(root)
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertIn("no node is running", out["sideagent_maintenance"])
        record = root / "zcode" / "zcode-KT-node" / "digest" / "record.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({
            "session_role": "sideagent", "state": "ready", "holder_pid": os.getpid(),
        }), encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertEqual(out["sideagent_maintenance"], "a node is running")

    def test_timer_without_a_body_is_unavailable(self) -> None:
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator")
        self.assertEqual(out["result"], "unavailable")
        self.assertNotEqual(out["result"], "mismatch")

    def test_a_fabricated_cite_is_refused_and_a_real_path_is_kept(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "done-one",
                   "--set", json.dumps({"stage": "done", "goal": "finished", "verdict": {"value": "accepted"}}))
        before = self.file.read_bytes()
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "done-one", "--expect-rev", "1", "--evidence", "not a commit",
            "--cite", '{"commit":"abcdef1","path":"README.md"}')
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertIn("invent", out["detail"])
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "done-one", "--expect-rev", "1", "--evidence", "README.md",
            "--cite", CITE)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["retired"][-1]["cite"]["path"], "README.md")
        self.assertNotIn("commit", self.doc()["state"]["retired"][-1]["cite"])

    def test_delegator_role_view_uses_locators(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["holds"]["h1"] = {
            "reason": "quota", "narrative": "secret prose", "rev": 1, "writer": "host", "source": "s",
        }
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator", "--repo", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertNotIn("secret prose", json.dumps(out["special"]["holds"]))
        self.assertTrue(any(item["path"] == "state.holds.h1.narrative" for item in out["unknown"]))

    def test_owner_stop_is_not_blocked_by_the_legacy_bound(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["pad"] = {
            "stage": "todo", "goal": "x" * 70000, "rev": 1, "writer": "host", "source": "s",
        }
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "pad", "--expect-rev", "1", "--set", json.dumps({"next": "continue"}))
        self.assertEqual(out["reason"], "carrier-limit", out)
        self.assertIn("owner stop", out["recovery"])
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "owner",
            "--section", "project", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"stop": "stop at the owner boundary"}))
        self.assertEqual(code, 0, out)
        self.assertNotEqual(self.file.read_bytes(), before)
        self.assertEqual(self.doc()["state"]["project"]["stop"], "stop at the owner boundary")
        self.assertEqual(self.doc()["state"]["tasks"]["pad"]["goal"], "x" * 70000)

    def test_a_failed_write_removes_its_temp_file(self) -> None:
        spec = importlib.util.spec_from_file_location("kpr_dispatch_259", DISPATCH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        target = self.repo / "atomic.json"
        target.write_text("original\n", encoding="utf-8")
        real = Path.write_text

        def fail_temp(path: Path, *args: object, **kwargs: object) -> int:
            if path.name.endswith(".tmp"):
                raise OSError("disk")
            return real(path, *args, **kwargs)

        with unittest.mock.patch.object(Path, "write_text", fail_temp):
            with self.assertRaises(OSError):
                module.atomic_write(target, "new\n")
        self.assertFalse(target.with_name("atomic.json.tmp").exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "original\n")

    def test_an_oversized_migrated_record_still_accepts_an_owner_stop(self) -> None:
        body = {
            "project": {"code": "KT", "goal": "keep the open duty"},
            "authorization": {"elite_cap": 2},
            "active": [
                {"ref": f"row-{n}", "session": f"codex-KT-i{n}-x", "evidence": "e" * 900}
                for n in range(80)
            ],
        }
        self.file.write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/1", "body": json.dumps(body),
        }), encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertGreater(self.file.stat().st_size, 65536)
        self.assertIsNone(self.doc().get("carrier"))
        revision = str(self.doc()["revision"])
        code, stopped = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "owner",
            "--section", "project", "--expect-revision", revision,
            "--set", json.dumps({"stop": "stop at the owner boundary"}))
        self.assertEqual(code, 0, stopped)
        self.assertEqual(self.doc()["state"]["project"]["stop"], "stop at the owner boundary")
        task_id = next(iter(self.doc()["state"]["tasks"]))
        code, ordinary = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", task_id, "--expect-rev", "1",
            "--set", json.dumps({"next": "continue"}))
        self.assertEqual(ordinary["reason"], "carrier-limit", ordinary)
        self.assertIn("owner stop", ordinary["recovery"])

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))


class RealAcpInjection(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i259-acp-", dir="/tmp")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.records = self.root / "records"
        self.repo = self.root / "repo"
        self.home.mkdir()
        self.records.mkdir()
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        (self.repo / ".kaola").mkdir()
        self.log = self.root / "mock.jsonl"
        self.started: list[str] = []
        self.agent = f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"

    def tearDown(self) -> None:
        for session in self.started:
            self.cli("stop", "--force", session=session, check=False)
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
            "MOCK_ACP_LOG": str(self.log),
        }
        base.update(extra)
        return base

    def cli(self, command: str, *args: str, session: str, check: bool = True,
            env: dict[str, str] | None = None) -> dict:
        argv = [PYTHON, str(CLI), "codex", command, "--repo", str(self.repo), "--session", session, *args]
        if command == "start":
            argv.extend(["--command", self.agent])
            self.started.append(session)
        proc = subprocess.run(argv, capture_output=True, text=True, env=env or self.env(), timeout=90)
        payload: dict = {}
        for line in reversed((proc.stdout or "").splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            break
        if check and proc.returncode != 0:
            self.fail(f"{command} exited {proc.returncode}: {payload or proc.stderr[-800:]}")
        payload["_returncode"] = proc.returncode
        return payload

    def test_start_send_observe_stop_injects_the_projected_view(self) -> None:
        state = self.repo / ".kaola" / "heartbeat-prompt.json"
        code, out = run_dispatch([
            "state", "init", "--file", str(state), "--writer", "host", "--source", "turn-1",
            "--project", json.dumps({"code": "KT", "goal": "close the selected issues"}),
            "--authorization", json.dumps({"classes": dict(CLASS_SENTENCES), "elite_cap": 1,
                                           "grants": [{"id": "codex/default", "state": "granted", "count": 1}]})])
        self.assertEqual(code, 0, out)
        run_dispatch([
            "state", "update", "--file", str(state), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "repair-1",
            "--set", json.dumps({"stage": "doing", "goal": "projected-goal-marker",
                                 "next": "seat the named repair"})])
        doc = json.loads(state.read_text(encoding="utf-8"))
        doc["body"] = "STORED-BODY-SENTINEL"
        state.write_text(json.dumps(doc), encoding="utf-8")
        host = "codex-KPR-i259-host"
        worker = "codex-KPR-i259-work"
        started = self.cli("start", session=host)
        self.assertEqual(started.get("state"), "ready", started.get("error") or started)
        target = json.dumps({"platform": "codex", "session": host, "repo": str(self.repo)})
        self.cli("start", session=worker, env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        sent = self.cli("send", "--text", "advance the named repair", session=worker,
                        env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        self.assertIn(sent.get("outcome") or sent.get("turn_outcome"),
                      ("turn_completed", "in_progress", "idle"), sent.get("error") or sent.get("state"))
        observed = self.cli("observe", session=worker, env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        self.assertEqual(observed.get("turn_outcome"), "turn_completed", observed.get("error"))
        deadline = time.monotonic() + 15
        text = ""
        while time.monotonic() < deadline:
            text = self.log.read_text(encoding="utf-8") if self.log.exists() else ""
            if "projected-goal-marker" in text and "kaola-host-notify/1" in text:
                break
            time.sleep(0.2)
        self.assertIn("projected-goal-marker", text)
        self.assertIn(CLASS_SENTENCES["Worker"], text)
        self.assertNotIn("STORED-BODY-SENTINEL", text)
        host_observe = self.cli("observe", session=host)
        self.assertTrue(host_observe)
        stopped = self.cli("stop", "--force", session=worker, env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        self.assertTrue(stopped.get("stopped") or stopped.get("state") == "stopped"
                        or stopped.get("residual_pids") == [])
        host_stopped = self.cli("stop", "--force", session=host)
        self.assertTrue(host_stopped.get("stopped") or host_stopped.get("state") == "stopped"
                        or host_stopped.get("residual_pids") == [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
