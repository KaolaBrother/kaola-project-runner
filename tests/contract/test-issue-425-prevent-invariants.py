#!/usr/bin/env python3
"""Issue #425: Host prevent-invariants on the state writer.

P1 terminal write deletes the task. P3/A2 bounds every duty-row string at
512 UTF-8 bytes. A1 refuses an orphan disposition and drops a settled
dispatch ref with its disposition. P5 keeps those checks row-scoped and
independent of Sideagent maintenance.

NOT RUN here (settle §4, not this writer's fixture):
- P6 J prose/history under the cap, shrink-as-PASS, omitted review,
  in-flight correction versus steer consumption (Delegator #902).
- P4 KPM native Host-role record and the L2 `tasks: []` alias removal.
- L2 legacy cleanup acceptance (#421 / KPM #893).

A non-terminal `stage: done` update is still stored. Sideagent retire of
those legacy rows is unchanged; this suite does not clear them by itself.
A new row may still store a dispatch ref with a settled disposition so
that retire keeps the ref. Settling an id already on the task removes the
ref and the disposition together.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
CONTRACT = REPO / "scripts" / "kaola-record-contract.py"
AUTH = {"grants": [{"id": "dsh/default", "state": "granted", "count": 1}]}
CITE = {"path": "README.md", "locator": "README.md:1"}
CANCEL_CITE = {"path": "README.md", "locator": "README.md:cancel"}
SEAT = "dsh-KT-i425-seat"


def load_contract():
    spec = importlib.util.spec_from_file_location("kaola_record_contract_425", CONTRACT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exact_bytes(n: int, multibyte: bool = False) -> str:
    """A string of exactly n UTF-8 bytes. Multibyte uses U+4E2D (3 bytes)."""
    if not multibyte:
        return "a" * n
    count, extra = divmod(n, 3)
    return ("中" * count) + ("b" * extra)


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        env=env if env is not None else {k: v for k, v in os.environ.items()
                                         if not k.startswith("KAOLA_")},
        timeout=120,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i425-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("terminal evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.index = self.repo / "index.json"
        self.live = self.repo / "live.json"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        self.env["KAOLA_ACP_RECORD_ROOT"] = str(Path(self.tmp.name) / "records")
        self.contract = load_contract()

    def state(self, *args: str) -> tuple[int, dict]:
        return run(["state", *args], self.env)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def init(self) -> None:
        code, out = self.state("init", "--file", str(self.file), "--writer", "host",
                               "--source", "turn-1",
                               "--project", json.dumps({"code": "KT", "goal": "g",
                                                        "repo": str(self.repo)}),
                               "--authorization", json.dumps(AUTH))
        self.assertEqual(code, 0, out)

    def update(self, kind: str, ident: str, patch: dict, *extra: str,
               source: str = "evt") -> tuple[int, dict]:
        return self.state("update", "--file", str(self.file), "--writer", "host",
                          "--source", source, "--kind", kind, "--id", ident,
                          "--set", json.dumps(patch), *extra)

    def add_task(self, ident: str, patch: dict) -> int:
        code, out = self.update("tasks", ident, patch)
        self.assertEqual(code, 0, out)
        return self.doc()["state"]["tasks"][ident]["rev"]

    def write_live(self, rows: list[dict]) -> None:
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}),
                             encoding="utf-8")

    def write_index(self, items: list[dict]) -> None:
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1",
                                          "repo": str(self.repo), "items": items}),
                              encoding="utf-8")

    def terminal(self, ident: str, rev: int, verdict: str, cite: dict | None = None,
                 patch: dict | None = None, *extra: str) -> tuple[int, dict]:
        body = {"verdict": {"value": verdict}}
        if patch:
            body.update(patch)
        return self.update("tasks", ident, body, "--expect-rev", str(rev),
                           "--cite", json.dumps(cite or CITE),
                           "--live", str(self.live), *extra)

    def check(self, *extra: str) -> tuple[int, dict]:
        return self.state("check", "--file", str(self.file), *extra)


class TerminalDelete(Fixture):
    def test_accepted_and_cancelled_leave_with_outcome_and_cite(self) -> None:
        self.init()
        self.write_live([])
        accepted = self.add_task("t-ok", {"stage": "doing", "goal": "ship", "next": "read the result"})
        cancelled = self.add_task("t-no", {"stage": "review", "goal": "drop", "next": "record the cancel"})
        code, out = self.terminal("t-ok", accepted, "accepted")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["outcome"], "accepted")
        self.assertEqual(out["value"]["cite"], CITE)
        self.assertEqual(out["value"]["removed"], True)
        self.assertEqual(out["value"]["unknown_refs"], [])
        code, out = self.terminal("t-no", cancelled, "cancelled", CANCEL_CITE)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["outcome"], "cancelled")
        self.assertEqual(out["value"]["cite"], CANCEL_CITE)
        state = self.doc()["state"]
        self.assertNotIn("t-ok", state["tasks"])
        self.assertNotIn("t-no", state["tasks"])
        self.assertNotIn("retired", state)
        self.assertNotIn("completed", state)
        self.assertNotIn("tombstone", state)
        self.assertFalse(any(isinstance(row, dict) and row.get("stage") == "done"
                             for row in state["tasks"].values()))
        body = json.loads(self.doc()["body"])
        self.assertIsInstance(body, dict)
        self.assertNotIn("t-ok", json.dumps(body))

    def test_missing_index_is_unknown_and_not_fabricated(self) -> None:
        self.init()
        self.write_live([])
        missing = self.repo / "missing-index.json"
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "dispatch": ["old-item"],
                                   "next": "finish"})
        before_live = self.live.read_bytes()
        code, out = self.update(
            "tasks", "t1", {"verdict": {"value": "accepted"}},
            "--expect-rev", str(rev), "--cite", json.dumps(CITE),
            "--live", str(self.live), "--index", str(missing))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["unknown_refs"], ["old-item"])
        self.assertNotIn("stopped", json.dumps(out["value"]))
        self.assertNotIn("completed", json.dumps(out["value"]))
        self.assertFalse(missing.exists())
        self.assertEqual(self.live.read_bytes(), before_live)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_present_index_is_not_rewritten(self) -> None:
        self.init()
        self.write_live([])
        self.write_index([{"item_id": "old-item", "task_id": "t1", "status": "returned",
                           "acceptance": "pending"}])
        before = self.index.read_bytes()
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "dispatch": ["old-item"],
                                   "next": "finish"})
        code, out = self.update(
            "tasks", "t1", {"verdict": {"value": "accepted"}},
            "--expect-rev", str(rev), "--cite", json.dumps(CITE),
            "--live", str(self.live), "--index", str(self.index))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["unknown_refs"], [])
        self.assertEqual(self.index.read_bytes(), before)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_live_seat_and_unreadable_list_change_nothing(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "session": SEAT, "next": "wait"})
        self.write_live([{"platform": "dsh", "session": SEAT, "state": "ready",
                          "repo": str(self.repo), "holder_instance_id": "h1"}])
        before = self.file.read_bytes()
        code, out = self.terminal("t1", rev, "accepted", patch={"stage": "done", "keep_open": False})
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "live-seat")
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["stage"], "doing")

        self.live.write_text("{not json", encoding="utf-8")
        code, out = self.terminal("t1", rev, "accepted")
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "live-unreadable")
        self.assertIn("does not", out["detail"])
        self.assertEqual(self.file.read_bytes(), before)

        code, out = self.update(
            "tasks", "t1", {"verdict": {"value": "cancelled"}},
            "--expect-rev", str(rev), "--cite", json.dumps(CITE))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "live-unreadable")
        self.assertEqual(self.file.read_bytes(), before)

    def test_unknown_index_status_is_not_a_terminal_delete(self) -> None:
        self.init()
        self.write_live([])
        self.write_index([{"item_id": "old-item", "task_id": "t1", "status": "unknown"}])
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "dispatch": ["old-item"],
                                   "next": "recover the seat"})
        before = self.file.read_bytes()
        before_index = self.index.read_bytes()
        code, out = self.update(
            "tasks", "t1", {"verdict": {"value": "accepted"}},
            "--expect-rev", str(rev), "--cite", json.dumps(CITE),
            "--live", str(self.live), "--index", str(self.index))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "unknown-effect")
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["stage"], "doing")

    def test_closeout_duty_is_retained(self) -> None:
        self.init()
        self.write_live([])
        rev = self.add_task("t1", {
            "stage": "closeout", "goal": "ship", "owner": "host",
            "dispatch": ["qa-1"], "next": "run the unrun QA", "wait": "QA has not run",
        })
        before = self.file.read_bytes()
        code, out = self.terminal("t1", rev, "accepted")
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "duty-remains")
        self.assertEqual(self.file.read_bytes(), before)
        row = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(row["stage"], "closeout")
        self.assertEqual(row["next"], "run the unrun QA")
        self.assertEqual(row["owner"], "host")
        self.assertEqual(row["dispatch"], ["qa-1"])

    def test_keep_open_never_persists_done(self) -> None:
        self.init()
        self.write_live([])
        variants = (
            ("t-true", {"stage": "done", "keep_open": True}),
            ("t-false", {"stage": "done", "keep_open": False}),
            ("t-absent", {}),
        )
        for ident, extra in variants:
            rev = self.add_task(ident, {"stage": "doing", "goal": "g", "next": "close"})
            code, out = self.terminal(ident, rev, "accepted", patch=extra)
            self.assertEqual(code, 0, out)
            self.assertNotIn(ident, self.doc()["state"]["tasks"])
        self.assertFalse(any(isinstance(row, dict) and row.get("stage") == "done"
                             for row in self.doc()["state"]["tasks"].values()))

    def test_legacy_done_stays_until_an_explicit_terminal_write(self) -> None:
        self.init()
        self.write_live([])
        rev = self.add_task("legacy", {"stage": "done", "goal": "old",
                                       "verdict": {"value": "accepted"}})
        self.assertEqual(self.doc()["state"]["tasks"]["legacy"]["stage"], "done")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertTrue(any(row.get("code") == "done-not-retired" and row.get("id") == "legacy"
                            for row in out["problems"]))
        doc = self.doc()
        doc["state"]["maintenance"] = {"handled_host_revision": doc["host_revision"],
                                       "acked_host_revision": doc["host_revision"]}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.check()
        self.assertTrue(any(row.get("code") == "done-not-retired" and row.get("id") == "legacy"
                            for row in out["problems"]), out)
        self.assertIn("legacy", self.doc()["state"]["tasks"])
        other = self.add_task("open", {"stage": "todo", "goal": "stay", "next": "continue"})
        self.assertIn("legacy", self.doc()["state"]["tasks"])
        self.assertIn("open", self.doc()["state"]["tasks"])
        code, out = self.terminal("legacy", rev, "accepted")
        self.assertEqual(code, 0, out)
        self.assertNotIn("legacy", self.doc()["state"]["tasks"])
        self.assertEqual(self.doc()["state"]["tasks"]["open"]["rev"], other)

    def test_sideagent_retire_of_a_legacy_done_row_still_deletes_it(self) -> None:
        self.init()
        rev = self.add_task("legacy", {"stage": "done", "goal": "old",
                                       "verdict": {"value": "accepted"}})
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host",
            "--source", "legacy retire", "--kind", "tasks", "--id", "legacy",
            "--expect-rev", str(rev), "--evidence", "original close-out",
            "--cite", json.dumps(CITE))
        self.assertEqual(code, 0, out)
        self.assertNotIn("legacy", self.doc()["state"]["tasks"])


class DutyBounds(Fixture):
    def test_constant_matches_writer_and_checker(self) -> None:
        limit = self.contract.DUTY_STRING_MAX_BYTES
        self.assertEqual(limit, 512)
        self.init()
        for label, text, multibyte in (
            ("ascii", exact_bytes(512), False),
            ("han", exact_bytes(512, multibyte=True), True),
        ):
            ident = "fit-" + label
            code, out = self.update("tasks", ident, {"stage": "doing", "goal": "g", "next": text})
            self.assertEqual(code, 0, f"{label}: {out}")
            self.assertEqual(self.doc()["state"]["tasks"][ident]["next"], text)
            self.assertEqual(len(text.encode("utf-8")), 512)
        self.assertEqual(self.contract.duty_string_offenses(
            "tasks", "fit-ascii", {"next": exact_bytes(512)}), {})
        over = self.contract.duty_string_offenses(
            "tasks", "t", {"next": exact_bytes(513, multibyte=True)})
        self.assertEqual(over, {"tasks.t.next": 513})

    def test_over_limit_names_path_bytes_and_limit(self) -> None:
        self.init()
        limit = self.contract.DUTY_STRING_MAX_BYTES
        cases = (
            ("tasks", "t-next", {"stage": "doing", "goal": "g", "next": exact_bytes(513)},
             "tasks.t-next.next"),
            ("tasks", "t-wait", {"stage": "doing", "goal": "g", "wait": exact_bytes(513, True)},
             "tasks.t-wait.wait"),
            ("tasks", "t-nest", {"stage": "doing", "goal": "g",
                                 "assignments": [{"next": exact_bytes(513)}]},
             "tasks.t-nest.assignments[0].next"),
            ("tasks", "t-arr", {"stage": "doing", "goal": "g",
                                "needs": ["keep", exact_bytes(513, True)]},
             "tasks.t-arr.needs[1]"),
            ("holds", "h1", {"scope": "preset", "reason": exact_bytes(513)},
             "holds.h1.reason"),
            ("alerts", "a1", {"level": "watch", "summary": "s",
                              "inputs": {"in1": {"why": exact_bytes(513), "next": "fix"}}},
             "alerts.a1.inputs.in1.why"),
            ("decisions", "d1", {"owner": "host", "question": exact_bytes(513, True)},
             "decisions.d1.question"),
        )
        for kind, ident, patch, path in cases:
            before = self.file.read_bytes()
            code, out = self.update(kind, ident, patch)
            self.assertEqual(code, 2, out)
            self.assertEqual(out["reason"], "field-too-large")
            self.assertEqual(out["path"], path)
            self.assertEqual(out["bytes"], 513)
            self.assertEqual(out["limit"], limit)
            self.assertIn("locator", out["recovery"])
            self.assertEqual(self.file.read_bytes(), before)
            self.assertNotIn(ident, self.doc()["state"].get(kind) or {})
        code, out = self.check()
        self.assertFalse(any(row.get("code") == "field-too-large" for row in out["problems"]))

    def test_checker_reports_a_legacy_over_limit_value(self) -> None:
        self.init()
        self.add_task("t1", {"stage": "doing", "goal": "g", "next": "short"})
        doc = self.doc()
        doc["state"]["tasks"]["t1"]["goal"] = exact_bytes(600)
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        rows = [row for row in out["problems"] if row.get("code") == "field-too-large"]
        self.assertEqual(len(rows), 1, out)
        self.assertEqual(rows[0]["path"], "tasks.t1.goal")
        self.assertEqual(rows[0]["bytes"], 600)
        self.assertEqual(rows[0]["limit"], 512)

    def test_project_and_authorization_are_exempt(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        long = exact_bytes(600)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "grant",
            "--section", "project", "--expect-revision", str(revision),
            "--set", json.dumps({"goal": long}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["project"]["goal"], long)
        revision = self.doc()["revision"]
        auth = {"grants": [{"id": "dsh/default", "state": "granted", "count": 1,
                            "special_requirements": {"task_scope": long}}]}
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "grant",
            "--section", "authorization", "--expect-revision", str(revision),
            "--set", json.dumps(auth))
        self.assertEqual(code, 0, out)
        stored = self.doc()["state"]["authorization"]["grants"][0]["special_requirements"]["task_scope"]
        self.assertEqual(stored, long)
        code, out = self.check()
        self.assertFalse(any(row.get("code") == "field-too-large" for row in out["problems"]), out)


class Dispositions(Fixture):
    def test_orphan_is_refused_and_null_repair_removes_it(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "dispatch": ["live-item"],
                                   "next": "review"})
        before = self.file.read_bytes()
        code, out = self.update(
            "tasks", "t1", {"dispositions": {"missing": "accepted"}},
            "--expect-rev", str(rev))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "disposition-orphan")
        self.assertEqual(out["path"], "tasks.t1.dispositions.missing")
        self.assertEqual(self.file.read_bytes(), before)

        doc = self.doc()
        doc["state"]["tasks"]["t1"]["dispositions"] = {"missing": "repair", "live-item": "repair"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        code, out = self.update(
            "tasks", "t1", {"dispositions": {"missing": None}},
            "--expect-rev", str(rev))
        self.assertEqual(code, 0, out)
        row = self.doc()["state"]["tasks"]["t1"]
        self.assertNotIn("missing", row.get("dispositions") or {})
        self.assertEqual(row["dispositions"]["live-item"], "repair")
        self.assertEqual(row["dispatch"], ["live-item"])

    def test_settled_item_drops_ref_and_disposition_together(self) -> None:
        self.init()
        self.write_index([{"item_id": "item-a", "task_id": "t1", "status": "returned",
                           "session": "gone-seat", "acceptance": "pending"}])
        before = self.index.read_bytes()
        rev = self.add_task("t1", {
            "stage": "doing", "goal": "g", "dispatch": ["item-a", "item-b"],
            "dispositions": {"item-b": "repair"}, "next": "review item-b",
        })
        code, out = self.update(
            "tasks", "t1", {"dispositions": {"item-a": "accepted"}},
            "--expect-rev", str(rev), "--index", str(self.index))
        self.assertEqual(code, 0, out)
        row = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(row["dispatch"], ["item-b"])
        self.assertNotIn("item-a", row.get("dispositions") or {})
        self.assertEqual(row["dispositions"]["item-b"], "repair")
        self.assertEqual(self.index.read_bytes(), before)
        self.assertEqual(json.loads(before)["items"][0]["acceptance"], "pending")

        rev = row["rev"]
        before = self.file.read_bytes()
        before_index = self.index.read_bytes()
        code, out = self.update(
            "tasks", "t1",
            {"dispatch": ["item-a"], "dispositions": {"item-a": "accepted"}},
            "--expect-rev", str(rev), "--index", str(self.index))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "disposition-sham")
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["dispatch"], ["item-b"])

    def test_missing_index_does_not_excuse_an_orphan(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "next": "stay"})
        missing = self.repo / "no-index.json"
        before = self.file.read_bytes()
        code, out = self.update(
            "tasks", "t1", {"dispositions": {"ghost": "repair"}},
            "--expect-rev", str(rev), "--index", str(missing))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "disposition-orphan")
        self.assertEqual(out["path"], "tasks.t1.dispositions.ghost")
        self.assertFalse(missing.exists())
        self.assertEqual(self.file.read_bytes(), before)

    def test_checker_reports_a_legacy_orphan(self) -> None:
        self.init()
        self.add_task("t1", {"stage": "doing", "goal": "g", "dispatch": ["live-item"],
                             "next": "stay"})
        doc = self.doc()
        doc["state"]["tasks"]["t1"]["dispositions"] = {"ghost": "repair"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.check()
        rows = [row for row in out["problems"] if row.get("code") == "disposition-orphan"]
        self.assertEqual([row["path"] for row in rows], ["tasks.t1.dispositions.ghost"])


class RowScope(Fixture):
    def test_partial_repair_leaves_the_other_offense_visible(self) -> None:
        self.init()
        self.add_task("t1", {"stage": "doing", "goal": "g", "dispatch": ["live-item"],
                             "next": "stay"})
        self.add_task("other", {"stage": "todo", "goal": "other", "next": "go"})
        doc = self.doc()
        doc["state"]["tasks"]["t1"]["goal"] = exact_bytes(600)
        doc["state"]["tasks"]["t1"]["dispositions"] = {"ghost": "repair"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        other_rev = self.doc()["state"]["tasks"]["other"]["rev"]
        code, out = self.update("tasks", "other", {"next": "still go"},
                                "--expect-rev", str(other_rev), source="other-row")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["goal"], exact_bytes(600))
        self.assertIn("ghost", self.doc()["state"]["tasks"]["t1"]["dispositions"])

        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        code, out = self.update("tasks", "t1", {"dispositions": {"ghost": None}},
                                "--expect-rev", str(rev))
        self.assertEqual(code, 0, out)
        row = self.doc()["state"]["tasks"]["t1"]
        self.assertNotIn("dispositions", row)
        self.assertEqual(row["goal"], exact_bytes(600))
        code, out = self.check()
        codes = {item["code"] for item in out["problems"] if item.get("id") == "t1"}
        self.assertIn("field-too-large", codes)
        self.assertNotIn("disposition-orphan", codes)

        before = self.file.read_bytes()
        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        code, out = self.update("tasks", "t1", {"goal": exact_bytes(700)},
                                "--expect-rev", str(rev))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "field-too-large")
        self.assertEqual(out["bytes"], 700)
        self.assertEqual(self.file.read_bytes(), before)

    def test_terminal_delete_is_allowed_while_another_row_is_invalid(self) -> None:
        self.init()
        self.write_live([])
        self.add_task("dirty", {"stage": "doing", "goal": "g", "next": "stay"})
        doc = self.doc()
        doc["state"]["tasks"]["dirty"]["next"] = exact_bytes(700)
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        rev = self.add_task("clean", {"stage": "doing", "goal": "g", "next": "close"})
        code, out = self.terminal("clean", rev, "cancelled", CANCEL_CITE)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["outcome"], "cancelled")
        self.assertNotIn("clean", self.doc()["state"]["tasks"])
        self.assertEqual(self.doc()["state"]["tasks"]["dirty"]["next"], exact_bytes(700))
        code, out = self.check()
        self.assertTrue(any(row.get("code") == "field-too-large" and row.get("id") == "dirty"
                            for row in out["problems"]))

    def test_maintenance_state_does_not_gate_enforcement(self) -> None:
        self.init()
        self.write_live([])
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "next": "close"})
        modes = (
            None,
            {"platform": "dsh", "session": "dsh-KT-i425-side", "preset": "dsh/default",
             "state": "active"},
            {"platform": "dsh", "session": "dsh-KT-i425-side", "preset": "dsh/default",
             "state": "failed"},
            {"platform": "dsh", "session": "dsh-KT-i425-side", "preset": "dsh/default",
             "state": "ended"},
        )
        for binding in modes:
            doc = self.doc()
            doc["state"]["sideagent"] = binding
            doc["state"]["holds"]["held"] = {
                "scope": "maintenance", "reason": "held", "rev": 1,
                "source": "evt", "writer": "host",
            }
            self.file.write_text(json.dumps(doc), encoding="utf-8")
            before = self.file.read_bytes()
            code, out = self.update("tasks", "t1", {"next": exact_bytes(513)},
                                    "--expect-rev", str(rev))
            self.assertEqual((code, out.get("reason")), (2, "field-too-large"), binding)
            self.assertEqual(self.file.read_bytes(), before)
        code, out = self.terminal("t1", rev, "accepted")
        self.assertEqual(code, 0, out)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])
        self.assertEqual(self.doc()["state"]["sideagent"]["state"], "ended")
        self.assertIn("held", self.doc()["state"]["holds"])
        self.assertNotIn("last_sweep", self.doc()["state"].get("maintenance") or {})

    def test_repeated_unchanged_write_creates_nothing(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "doing", "goal": "g", "next": "the one action"})
        before = self.file.read_bytes()
        revision = self.doc()["revision"]
        code, out = self.update(
            "tasks", "t1", {"next": "the one action"},
            "--expect-rev", str(rev), source="later-beat")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "unchanged")
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.doc()["revision"], revision)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["rev"], rev)


if __name__ == "__main__":
    unittest.main(verbosity=2)
