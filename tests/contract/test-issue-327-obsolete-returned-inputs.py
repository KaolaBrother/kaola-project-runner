#!/usr/bin/env python3
"""Issue #327: a Host can retire obsolete pre-v0.9.12 maintenance-returned inputs.

The checkpoint path still refuses an input it did not settle. The new path
accepts only batch:<rev>, host:tasks/<id>@<rev>, and a not-in-batch task id,
and only when the named original record checks out. The alert leaves when
nothing remains. The file host revision does not move, so the removal is not
a new queue input.
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
for name in CALLER_ENV:
    os.environ.pop(name, None)

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1},
                   {"id": "zcode/default", "state": "granted", "count": 1}]}


def load_dispatch():
    spec = importlib.util.spec_from_file_location("kaola_dispatch_327", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


DISPATCH = load_dispatch()


def run(args: list[str]) -> tuple[int, dict]:
    env = {key: value for key, value in os.environ.items()
           if key not in CALLER_ENV and key.lower() not in ("http_proxy", "https_proxy")}
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def task(revision: int, goal: str = "g") -> dict:
    return {"stage": "done", "goal": goal, "host_revision": revision, "rev": 1}


class ObsoleteReturnedInputs(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i327-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.index = self.repo / "index.json"
        self.live = self.repo / "live.json"
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
                         "--project", json.dumps({"code": "KT", "goal": "ship"}),
                         "--authorization", json.dumps(AUTH)])
        self.assertEqual(code, 0, out)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def changes(self) -> dict:
        doc = self.doc()
        return DISPATCH.host_changes(doc, 0, int(doc["host_revision"]))

    def seed(self, inputs: dict, tasks: dict, host_revision: int = 1700, rev: int = 4) -> None:
        doc = self.doc()
        doc["host_revision"] = host_revision
        doc["state"]["tasks"] = tasks
        doc["state"]["maintenance"] = {"handled_host_revision": 1000, "acked_host_revision": 1000}
        doc["state"]["alerts"] = {"maintenance-returned": {
            "owner": "host", "level": "warn", "rev": rev,
            "summary": "maintenance needs Host recovery from original receipts",
            "inputs": inputs}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")

    def write_index(self, items: list[dict]) -> None:
        self.index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": items}), encoding="utf-8")

    def write_live(self, rows: list[dict]) -> None:
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}), encoding="utf-8")

    def remove(self, ident: str, evidence: str, *extra: str, rev: str = "4",
               writer: str = "host") -> tuple[int, dict]:
        return run(["state", "update", "--file", str(self.file), "--writer", writer, "--source", "reconcile",
                    "--kind", "alerts", "--id", "maintenance-returned", "--expect-rev", rev,
                    "--evidence", evidence, "--set", json.dumps({"inputs": {ident: None}}), *extra])

    def alert_inputs(self) -> dict:
        return self.doc()["state"]["alerts"]["maintenance-returned"]["inputs"]

    def test_obsolete_inputs_retire_with_original_evidence(self) -> None:
        """(a) each pre-v0.9.12 shape leaves when its original record checks out."""
        inputs = {
            "batch:1261": {"why": "binding-or-recipe-unavailable", "host_revision_through": 1261,
                           "evidence": "events#1261"},
            "host:tasks/w5-i135@1444": {"why": "unaccounted", "host_revision_through": 1444,
                                        "evidence": "events#1444"},
            "w5-i1669": {"why": "not-in-batch", "host_revision_through": 1669, "evidence": "events#1669"},
            "host:tasks/w5-held@1669": {"why": "not-in-batch", "host_revision_through": 1669,
                                        "evidence": "events#held"},
        }
        # w5-i135 and w5-i1669 are gone (retired). w5-held was rewritten at 1700.
        # Nothing current sits at or below the batch:1261 range.
        self.seed(inputs, {
            "w5-later": task(1700, "rewritten queue"),
            "w5-held": task(1700, "rewritten hold"),
        })
        self.write_index([{"item_id": "i1669", "task_id": "w5-i1669", "issue": 1669, "status": "returned"}])
        self.write_live([{"holder_instance_id": "old-node", "state": "stopped", "repo": str(self.repo),
                          "session": "zcode-KT-sideagent", "platform": "zcode"}])
        before_changes = self.changes()
        host_revision = self.doc()["host_revision"]

        code, out = self.remove("batch:1261", "superseded:1700")
        self.assertEqual(code, 0, out)
        self.assertNotIn("batch:1261", self.alert_inputs())
        self.assertEqual(set(self.alert_inputs()), {
            "host:tasks/w5-i135@1444", "w5-i1669", "host:tasks/w5-held@1669"})
        self.assertIn("maintenance-returned", self.doc()["state"]["alerts"])

        code, out = self.remove("host:tasks/w5-i135@1444", "retired:tasks/w5-i135", rev="5")
        self.assertEqual(code, 0, out)
        self.assertNotIn("host:tasks/w5-i135@1444", self.alert_inputs())

        code, out = self.remove("w5-i1669", "closed:issue/1669", "--index", str(self.index), rev="6")
        self.assertEqual(code, 0, out)
        self.assertNotIn("w5-i1669", self.alert_inputs())
        self.assertIn("maintenance-returned", self.doc()["state"]["alerts"],
                      "the alert stays while an input remains")

        code, out = self.remove("host:tasks/w5-held@1669", "stopped:holder/old-node",
                                "--live", str(self.live), rev="7")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["value"]["removed"], out)
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})
        self.assertEqual(self.doc()["host_revision"], host_revision)
        self.assertEqual(self.changes(), before_changes)
        self.assertNotIn("recovery_input", self.doc()["state"].get("maintenance") or {})

    def test_unproven_inputs_still_refuse(self) -> None:
        """(b) a reference that does not check out, and every other shape, stay input-unproven."""
        current = {
            "batch:1261": {"why": "binding-or-recipe-unavailable", "host_revision_through": 1261},
            "host:tasks/w5-i135@1444": {"why": "unaccounted", "host_revision_through": 1444},
            "w5-i1669": {"why": "not-in-batch", "host_revision_through": 1669},
            "host:tasks/w5-held@1669": {"why": "not-in-batch", "host_revision_through": 1669},
            "recovery#4": {"why": "recovery-originals-unavailable"},
            "batch:b-failed": {"why": "checkpoint-missing", "host_revision_through": 1261},
            "bare-other": {"why": "unaccounted"},
            "batch:900": {"why": "stop-unconfirmed", "host_revision_through": 900},
        }
        self.seed(current, {
            "w5-i135": task(1444, "still this change"),
            "w5-i1669": task(1669, "still this change"),
            "w5-held": task(1669, "still this change"),
            "old-row": task(1200, "inside the batch range"),
        })
        self.write_index([{"item_id": "i1669", "task_id": "w5-i1669", "issue": 1669, "status": "in-flight"}])
        self.write_live([{"holder_instance_id": "old-node", "state": "ready", "repo": str(self.repo),
                          "session": "zcode-KT-sideagent", "platform": "zcode"}])
        cases = (
            ("batch:1261", "superseded:1700", ()),
            ("host:tasks/w5-i135@1444", "retired:tasks/w5-i135", ()),
            ("host:tasks/w5-i135@1444", "superseded:1700", ()),
            ("w5-i1669", "closed:issue/1669", ("--index", str(self.index))),
            ("host:tasks/w5-held@1669", "stopped:holder/old-node", ("--live", str(self.live))),
            ("recovery#4", "retired:tasks/w5-i135", ()),
            ("batch:b-failed", "superseded:1700", ()),
            ("bare-other", "retired:tasks/bare-other", ()),
            ("batch:900", "superseded:1700", ()),
            ("batch:1261", "checkpoint:b-missing", ()),
            ("batch:1261", "README.md", ()),
        )
        for ident, evidence, extra in cases:
            before = self.file.read_bytes()
            code, out = self.remove(ident, evidence, *extra)
            self.assertEqual((code, out.get("reason")), (2, "input-unproven"), (ident, evidence, out))
            self.assertEqual(out["path"], f"alerts.maintenance-returned.inputs.{ident}")
            self.assertIn("state update", out["recovery"])
            self.assertEqual(self.file.read_bytes(), before, (ident, evidence))
            if ident == "batch:900":
                self.assertIn("stop duty", out["detail"])
            if ident in ("recovery#4", "batch:b-failed", "bare-other"):
                self.assertIn("not an obsolete pre-v0.9.12", out["detail"])
            if evidence.startswith("checkpoint:"):
                self.assertIn("checkpoint:b-missing", out["detail"])
        before = self.file.read_bytes()
        code, out = self.remove("batch:999", "superseded:1700")
        self.assertEqual((code, out["reason"]), (2, "input-missing"), out)
        self.assertEqual(self.file.read_bytes(), before)
        before = self.file.read_bytes()
        code, out = self.remove("batch:1261", "retired:tasks/old-row", writer="sideagent")
        self.assertEqual((code, out["reason"]), (2, "host-only"), out)
        self.assertEqual(self.file.read_bytes(), before)
        # A stored through that disagrees with batch:<rev> is not that range.
        doc = self.doc()
        doc["state"]["alerts"]["maintenance-returned"]["inputs"]["batch:1261"]["host_revision_through"] = 999
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = self.remove("batch:1261", "superseded:1700")
        self.assertEqual((code, out["reason"]), (2, "input-unproven"), out)
        self.assertIn("not an obsolete pre-v0.9.12", out["detail"])
        self.assertEqual(self.file.read_bytes(), before)

    def test_alert_clears_only_when_no_input_remains(self) -> None:
        """(c) one proven removal leaves the other input untouched; the last removal clears the alert."""
        kept = {"why": "unaccounted", "host_revision_through": 1444, "evidence": "events#1444"}
        self.seed({
            "batch:1444": {"why": "binding-or-recipe-unavailable", "host_revision_through": 1444},
            "host:tasks/w5-i135@1444": dict(kept),
        }, {"w5-later": task(1700)})
        before_changes = self.changes()
        host_revision = self.doc()["host_revision"]
        code, out = self.remove("batch:1444", "superseded:1700")
        self.assertEqual(code, 0, out)
        alert = self.doc()["state"]["alerts"]["maintenance-returned"]
        self.assertEqual(alert["inputs"], {"host:tasks/w5-i135@1444": kept})
        self.assertEqual(self.doc()["host_revision"], host_revision)
        self.assertEqual(self.changes(), before_changes)
        self.assertNotIn("host_revision", alert)
        code, out = self.remove("host:tasks/w5-i135@1444", "retired:tasks/w5-i135", rev="5")
        self.assertEqual(code, 0, out)
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})
        self.assertEqual(self.doc()["host_revision"], host_revision)
        self.assertEqual(self.changes(), before_changes)

    def test_checkpoint_settlement_still_raises_host_revision(self) -> None:
        """The checkpoint path is unchanged: a settled input still counts as a Host business write."""
        kept = {"why": "unaccounted", "host_revision_through": 1500}
        self.seed({
            "host:tasks/w5-i135@1444": {"why": "unaccounted", "host_revision_through": 1444},
            "host:tasks/w5-open@1500": dict(kept),
        }, {"w5-i135": task(1444), "w5-open": task(1500)})
        doc = self.doc()
        doc["state"]["maintenance"]["last_checkpoint"] = {
            "batch": "b-real", "verified": True,
            "host_revision": {"from": 1400, "through": 1444, "current": 1700},
            "settled": ["host:tasks/w5-i135@1444"]}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        host_revision = doc["host_revision"]
        code, out = self.remove("host:tasks/w5-i135@1444", "checkpoint:b-real")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["host_revision"], host_revision + 1)
        alert = self.doc()["state"]["alerts"]["maintenance-returned"]
        self.assertEqual(alert["inputs"], {"host:tasks/w5-open@1500": kept})
        self.assertEqual(alert["host_revision"], host_revision + 1)


if __name__ == "__main__":
    unittest.main()
