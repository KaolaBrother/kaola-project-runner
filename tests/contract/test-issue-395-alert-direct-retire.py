#!/usr/bin/env python3
"""Issue #395: a resolved pre-revision alert retires without a migration.

The vrpai shape is an ``alerts`` row written before record revisions: no
``rev``, and ``inputs`` is an empty object because no returned input remains.
On v0.9.23 that row is classified ``resolved`` by ``state check`` but every
retire refuses ``record-versionless``; the only route is ``state migrate``,
which rewrites the whole file. Issue #395 admits one narrow direct exit:
``kind == alerts``, empty ``inputs``, explicit ``--expect-rev 0``, and
non-empty ``--evidence`` remove the row and keep the evidence in the receipt.
A versioned row still conflicts at 0, a row without ``inputs`` is not assumed
resolved, and update / returned-input settle still require the migration.

The #397 scope is recorded as two skips: v1 ``body.alerts`` mapping and a
large carrier without a proving holder are not handled by this change.
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
IDENT = "exclusion-breach-codex-default-i1687"
ABSENT = object()


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args]
        if args[:2] != [sys.executable, str(SCRIPT)] else args,
        capture_output=True, text=True,
        env=env if env is not None else {k: v for k, v in os.environ.items()
                                         if k not in CALLER_ENV},
        timeout=60,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def execute(command: str) -> tuple[int, dict]:
    return run(shlex.split(command))


def legacy_alert(*, inputs=ABSENT, rev=ABSENT,
                 blob: str = "legacy evidence " + "x" * 300) -> dict:
    record = {"level": "warn", "summary": "exclusion breach", "owner": "host",
              "next": "no duty remains", "evidence": [blob],
              "created_at": "2026-09-01T00:00:00Z",
              "updated_at": "2026-09-02T00:00:00Z",
              "source": "legacy-host-write", "writer": "host"}
    if inputs is not ABSENT:
        record["inputs"] = inputs
    if rev is not ABSENT:
        record["rev"] = rev
    return record


class AlertDirectRetire(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i395-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.records = Path(self.tmp.name) / "records"
        self.saved_root = os.environ.get("KAOLA_ACP_RECORD_ROOT")
        os.environ["KAOLA_ACP_RECORD_ROOT"] = str(self.records)
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1",
                         "--project", json.dumps({"code": "VRPAI", "goal": "ship"}),
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

    def plant(self, row: dict, ident: str = IDENT) -> None:
        doc = self.doc()
        doc["state"]["alerts"][ident] = row
        self.write_doc(doc)

    def retire(self, *extra: str, ident: str = IDENT,
               evidence: str = "original handled evidence") -> tuple[int, dict]:
        return run(["state", "retire", "--file", str(self.file), "--writer", "host",
                    "--source", "evt", "--kind", "alerts", "--id", ident,
                    "--evidence", evidence, *extra])

    def check(self) -> tuple[int, dict]:
        return run(["state", "check", "--file", str(self.file)])

    def bloat(self, out: dict) -> dict:
        return {row["id"]: row for row in out.get("problems") or []
                if row.get("code") == "state-bloat"}

    def test_direct_retire_requires_explicit_zero_and_keeps_evidence(self) -> None:
        self.plant(legacy_alert(inputs={}))
        before = self.file.read_bytes()

        # No explicit zero: the record-versionless refusal stays, with the
        # direct command named as this shape's exit.
        code, out = self.retire()
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        self.assertIn("--expect-rev 0", out["recovery"])
        self.assertEqual(self.file.read_bytes(), before)

        # Explicit zero and evidence: remove the row, store no revision, and
        # carry the supplied evidence in the receipt.
        code, out = self.retire("--expect-rev", "0",
                                evidence="original handled evidence 395")
        self.assertEqual((code, out.get("result")), (0, "written"), out)
        value = out["value"]
        self.assertEqual(value["kind"], "alerts")
        self.assertEqual(value["id"], IDENT)
        self.assertEqual(value["outcome"], "resolved")
        self.assertEqual(value["evidence"], "original handled evidence 395")
        doc = self.doc()
        self.assertNotIn(IDENT, doc["state"].get("alerts") or {})
        self.assertGreater(doc["revision"], 1)
        self.assertFalse(doc["state"].get("retired"))

        # A second retire creates no row: record-missing still wins.
        code, out = self.retire("--expect-rev", "0")
        self.assertEqual((code, out.get("reason")), (2, "record-missing"), out)

    def test_unresolved_or_non_dict_inputs_still_take_the_migration(self) -> None:
        for label, inputs in (
            ("non-empty", {"batch:1": {"why": "pending", "evidence": "e"}}),
            ("null", None),
            ("string", "not-a-mapping"),
        ):
            with self.subTest(label=label):
                self.plant(legacy_alert(inputs=inputs))
                before = self.file.read_bytes()
                code, out = self.retire("--expect-rev", "0")
                self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
                self.assertIn("migrate", out["recovery"])
                self.assertIn(IDENT, self.doc()["state"]["alerts"])
                self.assertEqual(self.file.read_bytes(), before)

    def test_absent_inputs_are_not_assumed_resolved(self) -> None:
        self.plant(legacy_alert())
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn(IDENT, self.bloat(out))
        before = self.file.read_bytes()
        code, out = self.retire("--expect-rev", "0")
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        self.assertIn("migrate", out["recovery"])
        self.assertIn(IDENT, self.doc()["state"]["alerts"])
        self.assertEqual(self.file.read_bytes(), before)

    def test_versioned_zero_still_conflicts(self) -> None:
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", "versioned",
                         "--set", json.dumps({"level": "warn", "summary": "handled",
                                              "inputs": {}})])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["alerts"]["versioned"]["rev"], 1)
        code, out = self.retire("--expect-rev", "0", ident="versioned")
        self.assertEqual((code, out.get("reason")), (3, "conflict"), out)
        self.assertIn("versioned", self.doc()["state"]["alerts"])
        code, out = self.retire("--expect-rev", "1", ident="versioned")
        self.assertEqual(code, 0, out)

    def test_update_and_returned_input_settle_still_require_migration(self) -> None:
        self.plant(legacy_alert(inputs={}))
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", IDENT,
                         "--expect-rev", "0", "--set", json.dumps({"summary": "x"})])
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        self.assertIn("migrate", out["recovery"])
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", IDENT,
                         "--expect-rev", "0",
                         "--set", json.dumps({"inputs": {"batch:1": None}})])
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        self.assertIn(IDENT, self.doc()["state"]["alerts"])

    def test_check_emits_a_runnable_direct_command(self) -> None:
        blob = "original handled evidence " + "y" * 300
        self.plant(legacy_alert(inputs={}, blob=blob))
        code, out = self.check()
        self.assertEqual(code, 0, out)
        row = self.bloat(out)[IDENT]
        self.assertEqual(row["class"], "resolved")
        self.assertIsNone(row["rev"])
        command = row["command"]
        self.assertIn("retire", command)
        self.assertIn("--expect-rev 0", command)
        self.assertIn("--evidence", command)
        self.assertNotIn("migrate", command)
        self.assertNotIn("--expect-rev None", command)

        ran, receipt = execute(command)
        self.assertEqual(ran, 0, receipt)
        self.assertEqual(receipt["value"]["evidence"], blob)
        self.assertNotIn(IDENT, self.doc()["state"].get("alerts") or {})
        again_code, again = self.check()
        self.assertEqual(again_code, 0, again)
        self.assertNotIn(IDENT, self.bloat(again))

    @unittest.skip("#397: v1 body.alerts mapping is outside #395's narrow scope")
    def test_v1_body_alerts_is_out_of_scope(self) -> None:
        pass

    @unittest.skip("#397: a large carrier without a proving holder is outside #395")
    def test_large_carrier_is_out_of_scope(self) -> None:
        pass

    def test_non_object_row_is_json_refused(self) -> None:
        doc = self.doc()
        doc["state"]["alerts"][IDENT] = ["not", "a", "row"]
        self.write_doc(doc)
        before = self.file.read_bytes()
        for extra in ([], ["--expect-rev", "0"]):
            with self.subTest(extra=extra):
                code, out = self.retire(*extra)
                self.assertEqual((code, out.get("reason")), (2, "state-unreadable"), out)
                self.assertNotIn("AttributeError", json.dumps(out))
                self.assertEqual(self.doc()["state"]["alerts"][IDENT], ["not", "a", "row"])
                self.assertEqual(self.file.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
