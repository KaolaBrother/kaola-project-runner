#!/usr/bin/env python3
"""Issue #362: records written before record revisions carried no ``rev``.

On v0.9.21 every ``--expect-rev`` path refused them: ``state retire``
answered ``expect-rev-required`` or ``conflict`` ("at rev None"), ``state
update`` and the input-settle route failed the same way, and ``state
check`` emitted an unparseable ``--expect-rev None`` command, so a
resolved legacy alert could never leave the file or the Host view. The
documented repair is ``state migrate`` (read-only plan, then ``--write``):
it assigns ``rev 1`` to each pre-revision record, and every normal gate
then applies unchanged. Unresolved records stay refused.
"""
from __future__ import annotations

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
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for _name in CALLER_ENV:
    os.environ.pop(_name, None)

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}
ALERT_IDS = ("exclusion-breach-codex-default-i1687", "exclusion-breach-codex-default-i1779")


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


def legacy_alert(summary: str, inputs: dict | None, blob: str) -> dict:
    """The vrpai shape: a resolved alert row with no ``rev`` field at all."""
    record = {"level": "warn", "summary": summary, "owner": "host", "next": "no duty remains",
              "evidence": [blob, blob],
              "created_at": "2026-09-01T00:00:00Z", "updated_at": "2026-09-02T00:00:00Z",
              "source": "legacy-host-write", "writer": "host"}
    if inputs is not None:
        record["inputs"] = inputs
    return record


class VersionlessRecords(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i362-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.records = Path(self.tmp.name) / "records"
        self.saved_root = os.environ.get("KAOLA_ACP_RECORD_ROOT")
        os.environ["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1", "--project", json.dumps({"code": "VRPAI", "goal": "ship"}),
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

    def write_doc(self, doc: dict) -> None:
        self.file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def retire(self, kind: str, ident: str, *extra: str) -> tuple[int, dict]:
        return run(["state", "retire", "--file", str(self.file), "--writer", "host",
                    "--source", "evt", "--kind", kind, "--id", ident,
                    "--evidence", "original handled evidence", *extra])

    def check(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "check", "--file", str(self.file), *extra])

    def bloat_rows(self, out: dict) -> dict:
        return {row["id"]: row for row in out.get("problems") or []
                if row.get("code") == "state-bloat"}

    def host_view_bytes(self) -> int:
        code, view = run(["state", "view", "--file", str(self.file), "--role", "host"])
        self.assertEqual(code, 0, view)
        return len(json.dumps(view, ensure_ascii=False, sort_keys=True).encode("utf-8"))

    def test_regression_versionless_resolved_alerts_migrate_then_retire(self) -> None:
        blob = "legacy evidence " + "x" * 1150
        doc = self.doc()
        for ident in ALERT_IDS:
            doc["state"]["alerts"][ident] = legacy_alert(
                f"exclusion breach for {ident}", {}, blob)
        self.write_doc(doc)
        for ident in ALERT_IDS:
            self.assertNotIn("rev", self.doc()["state"]["alerts"][ident])

        code, out = self.check()
        self.assertEqual(code, 0, out)
        rows = self.bloat_rows(out)
        for ident in ALERT_IDS:
            self.assertIn(ident, rows, out)
            self.assertEqual(rows[ident]["class"], "resolved")
            self.assertIsNone(rows[ident]["rev"])
            self.assertGreater(rows[ident]["bytes"], 2000)
            # The emitted next step is the migrate plan, never a command with
            # a literal --expect-rev None.
            self.assertIn("state", rows[ident]["command"])
            self.assertIn("migrate", rows[ident]["command"])
            self.assertNotIn("--expect-rev", rows[ident]["command"])

        # Every --expect-rev path refuses a pre-revision record and names the
        # documented migrate repair.
        for extra in ([], ["--expect-rev", "0"]):
            code, out = self.retire("alerts", ALERT_IDS[0], *extra)
            self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
            self.assertIn("state", out["recovery"])
            self.assertIn("migrate", out["recovery"])
            self.assertIn("--write", out["recovery"])
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", ALERT_IDS[0],
                         "--expect-rev", "0", "--set", json.dumps({"summary": "x"})])
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        self.assertIn("migrate", out["recovery"])
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", ALERT_IDS[0],
                         "--expect-rev", "0", "--set", json.dumps({"inputs": {"any": None}})])
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)

        # The read-only plan names each assigned revision and writes nothing.
        before_bytes = self.file.read_bytes()
        code, out = run(["state", "migrate", "--file", str(self.file)])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "planned", out)
        self.assertFalse(out["writes"])
        removed = out["report"]["removed"]
        for ident in ALERT_IDS:
            self.assertIn(f"alerts.{ident}.rev assigned 1 (pre-revision record)", removed)
        self.assertEqual(self.file.read_bytes(), before_bytes)

        # --write assigns the first revision; the records stay current rows.
        code, out = run(["state", "migrate", "--file", str(self.file), "--write"])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "migrated", out)
        doc = self.doc()
        for ident in ALERT_IDS:
            self.assertEqual(doc["state"]["alerts"][ident]["rev"], 1, ident)
            self.assertTrue(doc["state"]["alerts"][ident]["inputs"] == {})

        # state check now emits a runnable retire command at the assigned rev.
        code, out = self.check()
        self.assertEqual(code, 0, out)
        rows = self.bloat_rows(out)
        view_before = self.host_view_bytes()
        ran, removed_out = execute(rows[ALERT_IDS[0]]["command"])
        self.assertIn("--expect-rev 1", rows[ALERT_IDS[0]]["command"])
        self.assertEqual(ran, 0, removed_out)
        code, out = self.retire("alerts", ALERT_IDS[1], "--expect-rev", "1")
        self.assertEqual(code, 0, out)

        doc = self.doc()
        self.assertEqual(doc["state"].get("alerts") or {}, {})
        self.assertLess(self.host_view_bytes(), view_before)
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertFalse(any(ident in self.bloat_rows(out) for ident in ALERT_IDS), out)

    def test_guard_unresolved_versionless_records_stay_refused(self) -> None:
        blob = "pending recovery " + "y" * 300
        doc = self.doc()
        doc["state"]["maintenance"] = {
            "recovery_seq": 3,
            "recovery_input": {"seq": 3, "kind": "request", "occurrence_id": None,
                               "source": "signal", "holder": "holder-1",
                               "at": "2026-09-03T00:00:00Z", "evidence": "signal"}}
        doc["state"]["alerts"]["unresolved-alert"] = legacy_alert(
            "still names the pending recovery input",
            {"recovery#3": {"why": "pending", "evidence": "e"}}, blob)
        doc["state"]["tasks"]["open-task"] = {
            "stage": "doing", "goal": "unfinished work", "next": "keep going",
            "created_at": "2026-09-01T00:00:00Z", "source": "legacy", "writer": "host"}
        self.write_doc(doc)

        # Pre-revision rows still refuse and name the migrate repair.
        code, out = self.retire("alerts", "unresolved-alert", "--expect-rev", "0")
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        code, out = run(["state", "migrate", "--file", str(self.file), "--write"])
        self.assertEqual(out["result"], "migrated", out)
        doc = self.doc()
        self.assertEqual(doc["state"]["alerts"]["unresolved-alert"]["rev"], 1)
        self.assertEqual(doc["state"]["tasks"]["open-task"]["rev"], 1)

        # Migration assigns the revision; it lifts none of the normal gates.
        code, out = self.retire("alerts", "unresolved-alert", "--expect-rev", "1")
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("current pending recovery input", out["detail"])
        code, out = self.retire("tasks", "open-task", "--expect-rev", "1")
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("done or cancelled", out["detail"])
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", "unresolved-alert",
                         "--expect-rev", "9", "--set", json.dumps({"summary": "x"})])
        self.assertEqual((code, out.get("reason")), (3, "conflict"), out)
        doc = self.doc()
        self.assertIn("unresolved-alert", doc["state"]["alerts"])
        self.assertIn("open-task", doc["state"]["tasks"])

    def test_guard_versioned_records_keep_conflict_semantics(self) -> None:
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", "normal",
                         "--set", json.dumps({"level": "watch", "summary": "handled",
                                              "inputs": {}})])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["alerts"]["normal"]["rev"], 1)

        code, out = self.retire("alerts", "normal")
        self.assertEqual((code, out.get("reason")), (2, "expect-rev-required"), out)
        code, out = self.retire("alerts", "normal", "--expect-rev", "5")
        self.assertEqual((code, out.get("reason")), (3, "conflict"), out)

        # A migrate on a fully-versioned file assigns nothing.
        code, out = run(["state", "migrate", "--file", str(self.file), "--write"])
        self.assertEqual(code, 0, out)
        self.assertNotEqual(out.get("result"), "blocked", out)
        self.assertFalse(any("pre-revision record" in entry for entry in out.get("removed") or []),
                         out)

        code, out = self.retire("alerts", "normal", "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        self.assertNotIn("normal", self.doc()["state"].get("alerts") or {})


if __name__ == "__main__":
    unittest.main()
