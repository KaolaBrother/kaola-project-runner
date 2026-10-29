#!/usr/bin/env python3
"""Issue #427: a tool-written collect binds itself, and hand-over dispositions settle.

`collect` never wrote a `session` key on `evidence.collect_status` (only
exact-stop receipts carry one), so the #426 collect-terminal route could never
match a real tool receipt. A receipt that names no `session` now binds through
a non-empty `acp_session_id` plus the same strict holder and repo equality; a
present `session` key must still equal the item session. Per-item
`superseded` and `handed-off` dispositions settle on the collect-terminal and
dead-holder routes and are reported as that disposition; `repair` still
refuses. New collect receipts record the runner `session`; existing index
rows are not rewritten.
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
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
AUTH = {"grants": [{"id": "dsh/default", "state": "granted", "count": 1}]}
CITE = {"path": "README.md", "locator": "README.md"}
SEAT = "dsh-KT-i427-review"
HOLDER = "holder-427"
PRESET = "dsh/default"
ITEM = "i427-review"
ACP = "acp-427"

for _name in CALLER_ENV:
    os.environ.pop(_name, None)


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


def dispatch_module():
    spec = importlib.util.spec_from_file_location("kaola_dispatch_i427", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i427-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.index = self.repo / "index.json"
        self.live = self.repo / "live.json"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        self.env["KAOLA_ACP_RECORD_ROOT"] = str(Path(self.tmp.name) / "records")

    def state(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        return run(["state", *args], env)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def init(self) -> None:
        code, out = self.state("init", "--file", str(self.file), "--writer", "host",
                               "--source", "turn-1",
                               "--project", json.dumps({"code": "KT", "goal": "g",
                                                        "repo": str(self.repo)}),
                               "--authorization", json.dumps(AUTH), env=self.env)
        self.assertEqual(code, 0, out)

    def add_task(self, ident: str, patch: dict) -> int:
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
                               "--source", "evt", "--kind", "tasks", "--id", ident,
                               "--set", json.dumps(patch), env=self.env)
        self.assertEqual(code, 0, out)
        return self.doc()["state"]["tasks"][ident]["rev"]

    def accepted(self, patch: dict | None = None, ident: str = "t1") -> int:
        body = {"stage": "done", "goal": "deliver", "verdict": {"value": "accepted"},
                "dispatch": [ITEM]}
        body.update(patch or {})
        return self.add_task(ident, body)

    def write_live(self, rows: list[dict]) -> None:
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}),
                             encoding="utf-8")

    def write_index(self, items: list[dict], path: Path | None = None) -> None:
        target = path or self.index
        target.write_text(json.dumps({"schema": "kaola-dispatch-index/1",
                                      "repo": str(self.repo), "items": items}),
                          encoding="utf-8")

    def retire(self, ident: str, rev: int, *extra: str,
               writer: str = "host") -> tuple[int, dict]:
        return self.state("retire", "--file", str(self.file), "--writer", writer,
                          "--source", "original result", "--kind", "tasks",
                          "--id", ident, "--expect-rev", str(rev),
                          "--evidence", "original close-out evidence",
                          "--cite", json.dumps(CITE),
                          "--live", str(self.live), *extra, env=self.env)

    def item(self, **overrides) -> dict:
        """A tool-shaped row: collect wrote no `session` key on collect_status."""
        row = {
            "item_id": ITEM, "task_id": "t1", "status": "unknown",
            "reason": "fingerprint-differs", "acceptance": "pending",
            "session": SEAT, "holder_instance_id": HOLDER, "preset": PRESET,
            "platform": "dsh", "repo": str(self.repo),
            "evidence": {"collect_status": {
                "outcome": "stopped", "mutation_status": "completed",
                "holder_instance_id": HOLDER, "repo": str(self.repo),
                "acp_session_id": ACP,
            }},
        }
        row.update(overrides)
        return row

    def dead_item(self, **overrides) -> dict:
        """A dead-holder row: no collected continuation evidence at all."""
        row = self.item(reason="no-last-prompt", evidence={})
        row.update(overrides)
        return row

    def unlinked_item(self, task_id_marker: str = "absent", **overrides) -> dict:
        """A tool-shaped row with no task linkage (legacy, plan-level task_id
        was dropped before #427). `task_id_marker` "absent" removes the key;
        "null" leaves an explicit None."""
        row = self.item()
        if task_id_marker == "absent":
            row.pop("task_id", None)
        elif task_id_marker == "null":
            row["task_id"] = None
        else:
            row["task_id"] = task_id_marker
        row.update(overrides)
        return row

    def stopped_live(self) -> dict:
        return {"session": SEAT, "state": "stopped", "platform": "dsh",
                "repo": str(self.repo), "holder_instance_id": HOLDER}

    def reset(self) -> None:
        for path in (self.file, self.index, self.live):
            path.unlink(missing_ok=True)

    def stayed(self, before_state: bytes, before_index: bytes, ident: str = "t1") -> None:
        self.assertEqual(self.file.read_bytes(), before_state)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertIn(ident, self.doc()["state"]["tasks"])

    def ready(self, patch: dict | None = None, row: dict | None = None,
              live: list[dict] | None = None) -> tuple[int, bytes, bytes]:
        self.init()
        rev = self.accepted(patch)
        self.write_index([row if row is not None else self.item()])
        self.write_live(live if live is not None else [])
        return rev, self.file.read_bytes(), self.index.read_bytes()

    def refuse(self, patch: dict | None = None, row: dict | None = None,
               live: list[dict] | None = None) -> dict:
        rev, before_state, before_index = self.ready(patch, row, live)
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn(f"{ITEM} is unknown", out["detail"])
        self.assertNotIn("collect-terminal", out["detail"])
        self.stayed(before_state, before_index)
        return out

    def entry(self, patch: dict | None = None, row: dict | None = None,
              live: list[dict] | None = None) -> dict:
        rev, _state, before_index = self.ready(patch, row, live)
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])
        return out["value"]["reconciled_dispatch"][0]


class CollectTerminalBinding(Fixture):
    """A receipt with no `session` key binds through acp/holder/repo (#427)."""

    def test_a_tool_shaped_receipt_settles_when_the_session_is_absent(self) -> None:
        entry = self.entry()
        self.assertEqual(entry["route"], "collect-terminal")
        self.assertEqual(entry["disposition"], "accepted")
        self.assertEqual(entry["live"], "absent")
        self.assertEqual(entry["collected"],
                         {"outcome": "stopped", "mutation_status": "completed"})
        self.assertEqual(entry["session"], SEAT)
        self.assertEqual(entry["holder_instance_id"], HOLDER)

    def test_a_tool_shaped_receipt_settles_when_the_session_is_stopped(self) -> None:
        entry = self.entry(live=[self.stopped_live()])
        self.assertEqual(entry["route"], "collect-terminal")
        self.assertEqual(entry["live"], "stopped")

    def test_superseded_and_handed_off_settle_as_their_disposition(self) -> None:
        for disposition in ("superseded", "handed-off"):
            with self.subTest(disposition=disposition):
                self.reset()
                entry = self.entry({"dispositions": {ITEM: disposition}})
                self.assertEqual(entry["route"], "collect-terminal")
                self.assertEqual(entry["disposition"], disposition)

    def test_a_present_session_key_that_differs_refuses(self) -> None:
        row = self.item()
        row["evidence"]["collect_status"]["session"] = "dsh-KT-i427-other"
        self.refuse(row=row)

    def test_a_present_null_session_key_refuses(self) -> None:
        row = self.item()
        row["evidence"]["collect_status"]["session"] = None
        self.refuse(row=row)

    def test_a_foreign_collected_repo_refuses(self) -> None:
        row = self.item()
        row["evidence"]["collect_status"]["repo"] = "/foreign"
        self.refuse(row=row)

    def test_an_absent_or_blank_collected_holder_refuses(self) -> None:
        for value in ("absent", None, ""):
            with self.subTest(value=value):
                self.reset()
                row = self.item()
                if value == "absent":
                    row["evidence"]["collect_status"].pop("holder_instance_id")
                else:
                    row["evidence"]["collect_status"]["holder_instance_id"] = value
                self.refuse(row=row)

    def test_an_unusable_acp_session_id_refuses(self) -> None:
        for value in ("absent", None, "", "   ", 123):
            with self.subTest(value=value):
                self.reset()
                row = self.item()
                if value == "absent":
                    row["evidence"]["collect_status"].pop("acp_session_id")
                else:
                    row["evidence"]["collect_status"]["acp_session_id"] = value
                self.refuse(row=row)

    def test_a_repair_disposition_does_not_settle(self) -> None:
        self.refuse({"dispositions": {ITEM: "repair"}})

    def test_a_non_terminal_mutation_does_not_settle(self) -> None:
        for value in (None, "queued", {}):
            with self.subTest(value=value):
                self.reset()
                row = self.item()
                row["evidence"]["collect_status"]["mutation_status"] = value
                self.refuse(row=row)


class DeadHolderDispositions(Fixture):
    """superseded/handed-off settle the dead-holder route; repair refuses."""

    def test_superseded_and_handed_off_settle(self) -> None:
        for disposition in ("superseded", "handed-off"):
            with self.subTest(disposition=disposition):
                self.reset()
                entry = self.entry({"dispositions": {ITEM: disposition}},
                                   row=self.dead_item(),
                                   live=[self.stopped_live()])
                self.assertEqual(entry["disposition"], disposition)
                self.assertEqual(entry["reason"], "no-last-prompt")

    def test_a_repair_disposition_names_the_route(self) -> None:
        self.init()
        rev = self.accepted({"dispositions": {ITEM: "repair"}})
        self.write_index([self.dead_item()])
        self.write_live([self.stopped_live()])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("'repair'", out["detail"])
        self.assertIn("dead-holder unknown route", out["detail"])
        self.stayed(before_state, before_index)


class TaskLinkage(Fixture):
    """An index row with no `task_id` is unlinked (legacy), not foreign."""

    def test_unlinked_row_settles_superseded_on_collect_terminal(self) -> None:
        for marker in ("absent", "null"):
            with self.subTest(task_id=marker):
                self.reset()
                entry = self.entry({"dispositions": {ITEM: "superseded"}},
                                   row=self.unlinked_item(marker),
                                   live=[self.stopped_live()])
                self.assertEqual(entry["route"], "collect-terminal")
                self.assertEqual(entry["disposition"], "superseded")
                self.assertEqual(entry["live"], "stopped")

    def test_unlinked_row_settles_accepted_on_the_continuation_gate(self) -> None:
        for marker in ("absent", "null"):
            with self.subTest(task_id=marker):
                self.reset()
                entry = self.entry({"dispositions": {ITEM: "accepted"}},
                                   row=self.unlinked_item(marker),
                                   live=[self.stopped_live()])
                self.assertNotIn("route", entry)
                self.assertEqual(entry["collect_status"], "unknown")
                self.assertEqual(entry["reason"], "fingerprint-differs")
                self.assertEqual(entry["disposition"], "accepted")

    def test_unlinked_row_settles_accepted_when_the_session_is_absent(self) -> None:
        for marker in ("absent", "null"):
            with self.subTest(task_id=marker):
                self.reset()
                entry = self.entry(row=self.unlinked_item(marker), live=[])
                self.assertEqual(entry["route"], "collect-terminal")
                self.assertEqual(entry["disposition"], "accepted")
                self.assertEqual(entry["live"], "absent")

    def test_a_foreign_task_id_still_refuses(self) -> None:
        for dispositions, live in (
                ({"dispositions": {ITEM: "superseded"}}, [self.stopped_live()]),
                ({"dispositions": {ITEM: "accepted"}}, [self.stopped_live()])):
            with self.subTest(dispositions=dispositions):
                self.reset()
                self.refuse(dispositions,
                            row=self.unlinked_item("t-other"),
                            live=live)

    def test_execute_persists_a_plan_level_task_id(self) -> None:
        auth = self.repo / "auth.json"
        auth.write_text(json.dumps({"grants": []}), encoding="utf-8")
        live = self.repo / "exec-live.json"
        live.write_text(json.dumps({"rows": []}), encoding="utf-8")

        def plan(body: dict, name: str) -> Path:
            path = self.repo / name
            path.write_text(json.dumps(body), encoding="utf-8")
            return path

        item_a = {"item_id": "a", "preset": "dsh/ungranted",
                  "session": "dsh-KT-i427-a", "prompt": "a"}
        item_b = {"item_id": "b", "preset": "dsh/ungranted", "task_id": "t2",
                  "session": "dsh-KT-i427-b", "prompt": "b"}

        index = self.repo / "exec-index.json"
        code, out = run([
            "execute", "--plan", str(plan({
                "scope": "research", "repo": str(self.repo), "task_id": "t1",
                "items": [item_a, item_b]}, "plan-linked.json")),
            "--authorization", str(auth), "--platforms", str(REPO / "platforms"),
            "--skills-root", str(self.repo / "skills"),
            "--index", str(index), "--live", str(live)], self.env)
        self.assertEqual(code, 0, out)
        rows = {row["item_id"]: row for row in json.loads(index.read_text())["items"]}
        self.assertEqual(rows["a"].get("task_id"), "t1")
        self.assertEqual(rows["b"].get("task_id"), "t2")

        index2 = self.repo / "exec-index-2.json"
        code, out = run([
            "execute", "--plan", str(plan({
                "scope": "research", "repo": str(self.repo),
                "items": [dict(item_a)]}, "plan-bare.json")),
            "--authorization", str(auth), "--platforms", str(REPO / "platforms"),
            "--skills-root", str(self.repo / "skills"),
            "--index", str(index2), "--live", str(live)], self.env)
        self.assertEqual(code, 0, out)
        rows2 = json.loads(index2.read_text())["items"]
        self.assertNotIn("task_id", rows2[0])


class CollectWritesSession(Fixture):
    """collect records the runner session on each new collect_status receipt."""

    def module(self):
        return dispatch_module()

    def in_flight(self, **overrides) -> dict:
        row = {"item_id": ITEM, "task_id": "t1", "status": "in-flight",
               "session": SEAT, "holder_instance_id": HOLDER, "platform": "dsh",
               "repo": str(self.repo), "prompt_fingerprint": "sha256:aaa"}
        row.update(overrides)
        return row

    def collect(self, module, item: dict, receipt: dict) -> dict:
        module.runner_resolution = lambda root, platform: (Path("/bin/true"), "skills-root")
        module.run_runner = lambda script, argv: (0, receipt, "")
        return module.collect_one(item, str(self.repo), Path(self.tmp.name) / "skills")

    def test_collect_names_the_item_session_when_the_receipt_is_silent(self) -> None:
        module = self.module()
        receipt = {"repo": str(self.repo), "holder_instance_id": HOLDER,
                   "prompt_fingerprint": "sha256:bbb", "mutation_status": "completed",
                   "outcome": "stopped", "acp_session_id": ACP}
        kept = self.collect(module, self.in_flight(), receipt)
        self.assertEqual(kept["status"], "unknown")
        self.assertEqual(kept["reason"], "fingerprint-differs")
        self.assertEqual(kept["evidence"]["collect_status"]["session"], SEAT)

    def test_collect_keeps_the_receipt_session_when_it_names_one(self) -> None:
        module = self.module()
        receipt = {"repo": str(self.repo), "holder_instance_id": HOLDER,
                   "prompt_fingerprint": "sha256:bbb", "mutation_status": "completed",
                   "outcome": "stopped", "session": SEAT}
        kept = self.collect(module, self.in_flight(), receipt)
        self.assertEqual(kept["evidence"]["collect_status"]["session"], SEAT)

    def test_collect_preserves_an_existing_task_id(self) -> None:
        module = self.module()
        receipt = {"repo": str(self.repo), "holder_instance_id": HOLDER,
                   "prompt_fingerprint": "sha256:bbb", "mutation_status": "completed",
                   "outcome": "stopped"}
        kept = self.collect(module, self.in_flight(task_id="t1"), receipt)
        self.assertEqual(kept.get("task_id"), "t1")

    def test_collect_leaves_a_non_in_flight_item_untouched(self) -> None:
        module = self.module()
        kept = self.collect(module, self.in_flight(status="returned"), {})
        self.assertNotIn("collect_status", kept.get("evidence") or {})
        self.assertEqual(kept["status"], "returned")


if __name__ == "__main__":
    unittest.main()
