#!/usr/bin/env python3
"""Issue #354: settled rows leave, and state check diagnoses the residue.

These regression cases fail on v0.9.20 (b35165ff). A check there does not
emit ``state-bloat``, a clean accepted task with no dispatch is not
``done-not-retired``, ``carrier-unproven`` does not name ``state migrate
--live``, and the copied i338 row (unknown, fingerprint-differs, collected
outcome absent, status evidence ``no-session``) cannot be retired. Guards
keep the continuation route and the dead-holder route on their own shapes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "issue-354"
ORIGIN_REPO = "/Users/ylpromax5/Workspace/kaola-project-runner-dev"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for _name in CALLER_ENV:
    os.environ.pop(_name, None)

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}
CITE = {"path": "README.md", "locator": "README.md"}
ROUTE = "stale-collect session-gone route"
SESSION = "zcode-KT-sideagent"


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args] if args[:2] != [sys.executable, str(SCRIPT)] else args,
        capture_output=True, text=True,
        env=env if env is not None else {k: v for k, v in os.environ.items() if k not in CALLER_ENV},
        timeout=60,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def execute(command: str) -> tuple[int, dict]:
    return run(shlex.split(command))


def relocate_repo(value, origin: str, replacement: str):
    if isinstance(value, dict):
        return {key: (replacement if key == "repo" and item == origin else relocate_repo(item, origin, replacement))
                for key, item in value.items()}
    if isinstance(value, list):
        return [relocate_repo(item, origin, replacement) for item in value]
    return value


def repo_diffs(left, right, path: str = "") -> list[str]:
    if type(left) is not type(right):
        return [path or "<root>"]
    if isinstance(left, dict):
        found = []
        for key in set(left) | set(right):
            child = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                found.append(child)
            else:
                found.extend(repo_diffs(left[key], right[key], child))
        return found
    if isinstance(left, list):
        if len(left) != len(right):
            return [path or "<root>"]
        found = []
        for index, (one, two) in enumerate(zip(left, right)):
            found.extend(repo_diffs(one, two, f"{path}[{index}]"))
        return found
    if left != right:
        return [path or "<root>"]
    return []


class StateBloat(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i354-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.index = self.repo / "index.json"
        self.live = self.repo / "live.json"
        self.records = Path(self.tmp.name) / "records"
        self.saved_root = os.environ.get("KAOLA_ACP_RECORD_ROOT")
        os.environ["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1", "--project", json.dumps({"code": "KT", "goal": "ship"}),
                         "--authorization", json.dumps(AUTH)])
        self.assertEqual(code, 0, out)

    def tearDown(self) -> None:
        if self.saved_root is None:
            os.environ.pop("KAOLA_ACP_RECORD_ROOT", None)
        else:
            os.environ["KAOLA_ACP_RECORD_ROOT"] = self.saved_root
        self.tmp.cleanup()

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def update(self, kind: str, ident: str, patch: dict, *extra: str) -> tuple[int, dict]:
        return run(["state", "update", "--file", str(self.file), "--writer", "host",
                    "--source", "evt", "--kind", kind, "--id", ident, "--set",
                    json.dumps(patch), *extra])

    def write_index(self, items: list[dict]) -> None:
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "repo": str(self.repo),
                                          "items": items}), encoding="utf-8")

    def write_live(self, rows: list[dict]) -> None:
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}), encoding="utf-8")

    def check(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "check", "--file", str(self.file), *extra])

    def bloat(self, out: dict, ident: str | None = None) -> list[dict]:
        rows = [row for row in out.get("problems") or [] if row.get("code") == "state-bloat"]
        if ident is None:
            return rows
        return [row for row in rows if row.get("id") == ident]

    def install_i338(self, row_change=None) -> tuple[dict, bytes]:
        task = json.loads((FIXTURE / "i338-task.json").read_text(encoding="utf-8"))
        row = json.loads((FIXTURE / "i338-effort-max.json").read_text(encoding="utf-8"))
        moved = relocate_repo(row, ORIGIN_REPO, str(self.repo.resolve()))
        diffs = repo_diffs(row, moved)
        self.assertTrue(diffs, "the copied row names the live repo and must be relocated for this temp repo")
        self.assertTrue(all(item == "repo" or item.endswith(".repo") for item in diffs), diffs)
        if row_change:
            row_change(moved)
        doc = self.doc()
        doc["state"]["tasks"]["i338"] = task
        self.file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        self.write_index([moved])
        return task, self.index.read_bytes()

    def test_regression_check_names_each_settled_row_and_the_command_removes_it(self) -> None:
        code, out = self.update("tasks", "duty", {"stage": "todo", "goal": "keep", "next": "stay"})
        self.assertEqual(code, 0, out)
        code, out = self.update("tasks", "flight", {"stage": "doing", "goal": "open", "dispatch": ["item-live"],
                                                    "wait": "running"})
        self.assertEqual(code, 0, out)
        code, out = self.update("tasks", "done-row", {"stage": "done", "goal": "finished",
                                                      "verdict": {"value": "accepted"}})
        self.assertEqual(code, 0, out)
        code, out = self.update("tasks", "cancelled-row", {"stage": "review", "goal": "stop",
                                                           "verdict": {"value": "cancelled"}})
        self.assertEqual(code, 0, out)
        code, out = self.update("alerts", "resolved-row", {"level": "watch", "summary": "handled", "inputs": {}})
        self.assertEqual(code, 0, out)
        planted = self.doc()
        # A shell has no duty text. The tool requires goal on create, so this
        # residue is planted the way an older file still holds it.
        planted["state"]["tasks"]["shell-row"] = {
            "stage": "done", "verdict": {"value": "accepted", "by": "host"},
            "evidence": "retired:tasks/older", "rev": 1, "source": "evt", "writer": "host",
        }
        planted["state"]["decisions"]["settled-row"] = {
            "owner": "user", "question": "ship?", "status": "settled", "evidence": "owner said yes",
            "rev": 1, "source": "evt", "writer": "host",
        }
        self.file.write_text(json.dumps(planted, ensure_ascii=False), encoding="utf-8")
        self.write_index([{"item_id": "item-live", "status": "in-flight", "task_id": "flight",
                           "session": "codex-KT-live"}])
        self.write_live([])
        code, out = self.check("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 0, out)
        self.assertIn("diagnosis", out, out)
        self.assertFalse(out["diagnosis"]["stored"])
        by_id = {row["id"]: row for row in self.bloat(out)}
        self.assertEqual(set(by_id), {"done-row", "cancelled-row", "shell-row", "resolved-row", "settled-row"}, by_id)
        self.assertEqual(by_id["shell-row"]["class"], "shell")
        self.assertEqual(by_id["done-row"]["class"], "accepted-done")
        self.assertEqual(by_id["settled-row"]["kind"], "decisions")
        self.assertEqual(by_id["resolved-row"]["kind"], "alerts")
        for row in by_id.values():
            self.assertIn(f"{row['kind']}/{row['id']}", row["detail"])
            self.assertIn(f"rev {row['rev']}", row["detail"])
            self.assertIn("state", row["command"])
            self.assertIn("retire", row["command"])
            ran, removed = execute(row["command"])
            self.assertEqual(ran, 0, removed)
        doc = self.doc()
        self.assertEqual(set(doc["state"]["tasks"]), {"duty", "flight"})
        self.assertNotIn("resolved-row", doc["state"].get("alerts") or {})
        self.assertNotIn("settled-row", doc["state"].get("decisions") or {})
        self.assertEqual(doc["state"]["authorization"]["grants"], AUTH["grants"])
        self.assertEqual(doc["state"]["tasks"]["flight"]["dispatch"], ["item-live"])
        again_code, again = self.check("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(again_code, 0, again)
        self.assertEqual(self.bloat(again), [])
        self.assertEqual(again["problems"], [], again)

    def test_regression_the_copied_i338_row_retires_and_keeps_the_index(self) -> None:
        task, before_index = self.install_i338()
        self.write_live([])
        code, out = self.check("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 0, out)
        rows = self.bloat(out, "i338")
        self.assertEqual(len(rows), 1, out)
        self.assertIn("tasks/i338", rows[0]["detail"])
        self.assertIn(f"rev {task['rev']}", rows[0]["detail"])
        self.assertIn(str(self.index), rows[0]["command"])
        self.assertIn(str(self.live), rows[0]["command"])
        ran, removed = execute(rows[0]["command"])
        self.assertEqual(ran, 0, removed)
        entry = removed["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], "stale-collect-session-gone")
        self.assertEqual(entry["live"], "absent")
        self.assertEqual(entry["reason"], "fingerprint-differs")
        self.assertEqual(entry["collect_status"], "unknown")
        self.assertNotIn("i338", self.doc()["state"]["tasks"])
        self.assertFalse(self.doc()["state"].get("retired"))
        self.assertEqual(self.index.read_bytes(), before_index)

    def test_regression_a_listed_session_names_the_route_and_writes_nothing(self) -> None:
        task, before_index = self.install_i338()
        before = self.file.read_bytes()
        self.write_live([{"session": "grok-KPR-i338-effort", "state": "ready", "platform": "grok",
                          "repo": str(self.repo), "holder_instance_id": "4b486a5c911c7f8d18d076d0f3a702aa"}])
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "i338",
                         "--expect-rev", str(task["rev"]), "--evidence", task["source"],
                         "--cite", json.dumps(CITE), "--index", str(self.index), "--live", str(self.live)])
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("tasks/i338", out["detail"])
        self.assertIn(f"rev {task['rev']}", out["detail"])
        self.assertIn(ROUTE, out["detail"])
        self.assertIn("state", out["detail"])
        self.assertIn("retire", out["detail"])
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.index.read_bytes(), before_index)

    def test_guard_a_stopped_outcome_stays_on_the_continuation_route(self) -> None:
        def stopped(row: dict) -> None:
            row["evidence"]["collect_status"]["outcome"] = "stopped"
        task, before_index = self.install_i338(stopped)
        holder = "4b486a5c911c7f8d18d076d0f3a702aa"
        self.write_live([{"session": "grok-KPR-i338-effort", "state": "stopped", "platform": "grok",
                          "repo": str(self.repo), "holder_instance_id": holder}])
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "i338",
                         "--expect-rev", str(task["rev"]), "--evidence", task["source"],
                         "--cite", json.dumps(CITE), "--index", str(self.index), "--live", str(self.live)])
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertNotIn("route", entry)
        self.assertEqual(entry["reason"], "fingerprint-differs")
        self.assertEqual(self.index.read_bytes(), before_index)

    def test_guard_an_empty_collect_stays_on_the_dead_holder_route(self) -> None:
        def drop_collect(row: dict) -> None:
            row["evidence"].pop("collect_status", None)
        task, before_index = self.install_i338(drop_collect)
        self.write_live([])
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "i338",
                         "--expect-rev", str(task["rev"]), "--evidence", task["source"],
                         "--cite", json.dumps(CITE), "--index", str(self.index), "--live", str(self.live)])
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertNotEqual(entry.get("route"), "stale-collect-session-gone")
        self.assertEqual(entry["live"], "absent")
        self.assertEqual(entry["reason"], "fingerprint-differs")
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertNotIn(ROUTE, json.dumps(out))

    def test_regression_done_not_retired_is_watch_until_the_handled_batch(self) -> None:
        code, out = self.update("tasks", "t-done", {"stage": "done", "goal": "accepted", "next": "leave",
                                                    "verdict": {"value": "accepted"}})
        self.assertEqual(code, 0, out)
        task_rev = self.doc()["state"]["tasks"]["t-done"]["host_revision"]
        code, out = self.check()
        self.assertEqual(code, 0, out)
        noted = [row for row in out["problems"] if row.get("code") == "done-not-retired" and row.get("id") == "t-done"]
        self.assertEqual(len(noted), 1, out)
        self.assertEqual(noted[0]["level"], "watch")
        self.assertIn("tasks/t-done", noted[0]["detail"])
        self.assertIn("retire", noted[0]["command"])
        self.bind_node()
        through = self.doc()["host_revision"]
        node = self.node_env("node-1")
        code, view = run(["state", "view", "--file", str(self.file), "--role", "sideagent"])
        self.assertEqual(code, 0, view)
        entries = []
        for item in view["pending_host_changes"]:
            body = item[len("host:"):].rsplit("@", 1)[0]
            self.assertTrue(body.startswith("tasks/") or body.startswith("section/"), item)
            entries.append({"input": item, "retained": body})
        code, checkpoint = run(["state", "checkpoint", "--file", str(self.file), "--writer", "sideagent",
                                "--source", "b-354", "--batch", "b-354", "--through-host-revision", str(through),
                                "--entries", json.dumps(entries)], env=node)
        self.assertEqual(code, 0, checkpoint)
        self.assertTrue(checkpoint["value"]["verified"], checkpoint)
        self.assertGreaterEqual(self.doc()["state"]["maintenance"]["handled_host_revision"], task_rev)
        code, out = self.check()
        noted = [row for row in out["problems"] if row.get("code") == "done-not-retired" and row.get("id") == "t-done"]
        self.assertEqual(noted[0]["level"], "warn", out)
        code, later = self.update("tasks", "t-open", {"stage": "todo", "goal": "still writable", "next": "stay"})
        self.assertEqual(code, 0, later)
        self.assertIn("t-done", self.doc()["state"]["tasks"])

    def test_regression_carrier_unproven_names_state_migrate_live(self) -> None:
        doc = self.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2", "platform": "zcode",
                          "session": "zcode-KT-orchestrator-main", "holder_instance_id": "host-old"}
        self.file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        self.write_live([{"platform": "zcode", "session": "zcode-KT-orchestrator-main", "session_role": "host",
                          "host_class": True, "repo": str(self.repo), "state": "ready",
                          "holder_instance_id": "host-new", "holder_features": []}])
        code, out = self.check("--live", str(self.live))
        self.assertEqual(code, 0, out)
        rows = [row for row in out["problems"] if row.get("code") == "carrier-unproven"]
        self.assertEqual(len(rows), 1, out)
        self.assertIn("state migrate", rows[0]["detail"])
        self.assertIn("--live", rows[0]["detail"])
        self.assertIn(str(self.live), rows[0]["detail"])

    def test_regression_rounds_drop_settled_rows_and_keep_the_open_duty(self) -> None:
        code, out = self.update("tasks", "duty", {"stage": "todo", "goal": "keep", "next": "stay"})
        self.assertEqual(code, 0, out)
        code, out = self.update("tasks", "flight", {"stage": "doing", "goal": "open", "dispatch": ["item-live"],
                                                    "wait": "running"})
        self.assertEqual(code, 0, out)
        self.write_index([{"item_id": "item-live", "status": "in-flight", "task_id": "flight",
                           "session": "codex-KT-live"}])
        self.write_live([])
        before_index = self.index.read_bytes()
        sizes: list[int] = []
        for round_no in range(12):
            code, out = self.update("tasks", f"done-{round_no}", {"stage": "done", "goal": f"round {round_no}",
                                                                  "verdict": {"value": "accepted"}})
            self.assertEqual(code, 0, out)
            code, out = self.update("alerts", f"alert-{round_no}", {"level": "watch", "summary": "handled",
                                                                    "inputs": {}})
            self.assertEqual(code, 0, out)
            planted = self.doc()
            planted["state"]["decisions"][f"settled-{round_no}"] = {
                "owner": "user", "question": "q", "status": "settled", "evidence": "owner said yes",
                "rev": 1, "source": "evt", "writer": "host",
            }
            self.file.write_text(json.dumps(planted, ensure_ascii=False), encoding="utf-8")
            code, checked = self.check("--index", str(self.index), "--live", str(self.live))
            self.assertEqual(code, 0, checked)
            commands = [row["command"] for row in self.bloat(checked)]
            self.assertGreaterEqual(len(commands), 3, checked)
            for command in commands:
                ran, removed = execute(command)
                self.assertEqual(ran, 0, removed)
            code, after = self.check("--index", str(self.index), "--live", str(self.live))
            self.assertEqual(after["problems"], [], after)
            doc = self.doc()
            self.assertEqual(set(doc["state"]["tasks"]), {"duty", "flight"})
            self.assertFalse(doc["state"].get("decisions"))
            self.assertFalse(doc["state"].get("alerts"))
            self.assertEqual(doc["state"]["authorization"]["grants"], AUTH["grants"])
            sizes.append(len(doc["body"].encode("utf-8")))
        self.assertLessEqual(max(sizes) - min(sizes), 16, sizes)
        self.assertEqual(self.index.read_bytes(), before_index)

    def test_regression_an_oversized_goal_is_stored_and_only_hinted(self) -> None:
        goal = "g" * 4000
        code, out = self.update("tasks", "wide", {"stage": "todo", "goal": goal, "next": "stay"})
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["wide"]["goal"], goal)
        code, checked = self.check()
        self.assertEqual(code, 0, checked)
        self.assertNotIn("field-too-long", {row.get("code") for row in checked["problems"]})
        hints = checked["diagnosis"]["hints"]
        named = [row for row in hints if row.get("id") == "wide"]
        self.assertEqual(len(named), 1, checked)
        self.assertIn("tasks/wide", named[0]["detail"])
        self.assertIn("not a gate", named[0]["detail"])
        self.assertIn("update", named[0]["command"])
        self.assertIn("CURRENT_PATCH", named[0]["command"])
        self.assertNotIn("field-too-long", json.dumps(checked))

    def test_regression_check_stores_nothing(self) -> None:
        code, out = self.update("tasks", "done-row", {"stage": "done", "goal": "finished",
                                                      "verdict": {"value": "accepted"}})
        self.assertEqual(code, 0, out)
        before = self.file.read_bytes()
        keys = set(json.loads(before))
        state_keys = set(json.loads(before)["state"])
        code, checked = self.check()
        self.assertEqual(code, 0, checked)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertFalse(checked["diagnosis"]["stored"])
        self.assertEqual(set(self.doc()), keys)
        self.assertEqual(set(self.doc()["state"]), state_keys)
        self.assertTrue(self.bloat(checked, "done-row"))

    def test_regression_migrate_keeps_done_tasks_and_names_the_existing_backup(self) -> None:
        code, out = self.update("tasks", "done-row", {"stage": "done", "goal": "finished",
                                                      "verdict": {"value": "accepted"}})
        self.assertEqual(code, 0, out)
        code, out = self.update("tasks", "duty", {"stage": "todo", "goal": "keep", "next": "stay"})
        self.assertEqual(code, 0, out)
        code, out = self.update("tasks", "flight", {"stage": "doing", "goal": "open", "dispatch": ["item-live"],
                                                    "wait": "running"})
        self.assertEqual(code, 0, out)
        planted = self.doc()
        planted["state"]["decisions"]["settled-row"] = {
            "owner": "user", "question": "ship?", "status": "settled", "evidence": "owner said yes",
            "rev": 1, "source": "evt", "writer": "host",
        }
        self.file.write_text(json.dumps(planted, ensure_ascii=False), encoding="utf-8")
        self.write_index([{"item_id": "item-live", "status": "in-flight", "task_id": "flight",
                           "session": "codex-KT-live"}])
        code, checked = self.check("--index", str(self.index))
        self.assertTrue(self.bloat(checked, "done-row"), checked)
        backup = self.file.with_name("heartbeat-prompt.v1-aaaaaaaaaaaa.json")
        backup.write_text("{}\n", encoding="utf-8")
        code, first = run(["state", "migrate", "--file", str(self.file), "--write"])
        self.assertEqual(code, 0, first)
        self.assertIn("done-row", self.doc()["state"]["tasks"])
        self.assertIn("duty", self.doc()["state"]["tasks"])
        self.assertIn("flight", self.doc()["state"]["tasks"])
        self.assertNotIn("settled-row", self.doc()["state"].get("decisions") or {})
        self.assertEqual(self.doc()["state"]["authorization"]["grants"], AUTH["grants"])
        names = [row["name"] for row in first["backups"]["backups"]]
        self.assertIn(backup.name, names)
        self.assertEqual(backup.read_text(encoding="utf-8"), "{}\n")
        kept = set(self.doc()["state"]["tasks"])
        code, second = run(["state", "migrate", "--file", str(self.file), "--write"])
        self.assertEqual((code, second.get("result")), (0, "current"), second)
        self.assertEqual(set(self.doc()["state"]["tasks"]), kept)

    def bind_node(self) -> None:
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                         "--section", "sideagent", "--expect-revision", str(self.doc()["revision"]),
                         "--set", json.dumps({"platform": "zcode", "session": SESSION, "state": "active",
                                              "mode": "node"})])
        self.assertEqual(code, 0, out)

    def node_env(self, holder: str) -> dict[str, str]:
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.records / "zcode" / SESSION / digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "record.json").write_text(json.dumps({"holder_instance_id": holder,
                                                           "session_role": "sideagent"}), encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": holder, "platform": "zcode",
                                                  "repo": str(self.repo), "session": SESSION})
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        return env


if __name__ == "__main__":
    unittest.main()
