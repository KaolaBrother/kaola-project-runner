#!/usr/bin/env python3
"""Issue #298: Host retire --absent records a receipt for a decision id with no row.

The file stores no decision row, stone, or tombstone. host_revision still rises,
so the receipt's revision is citable. Without --absent an absent id stays
record-missing and the file is byte-identical.
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
AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}
EVIDENCE = "owner-msg-298-never-a-row"
DECISION_ID = "owner-1725"
RECEIPT_KEYS = {"kind", "id", "outcome", "absent_at_retire", "evidence", "at", "host_revision"}


def run(args: list[str]) -> tuple[int, dict]:
    env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


def load_dispatch():
    spec = importlib.util.spec_from_file_location("kaola_dispatch_298", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AbsentDecisionRetire(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i298-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str) -> tuple[int, dict]:
        return run(["state", *args])

    def init(self) -> None:
        code, out = self.state("init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
                               "--project", json.dumps({"code": "KT", "goal": "ship"}),
                               "--authorization", json.dumps(AUTH))
        self.assertEqual(code, 0, out)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def retire(self, *extra: str, writer: str = "host", ident: str = DECISION_ID,
               kind: str = "decisions") -> tuple[int, dict]:
        return self.state("retire", "--file", str(self.file), "--writer", writer, "--source", "owner-closure",
                          "--kind", kind, "--id", ident, *extra)

    def test_absent_id_returns_a_citable_receipt_and_stores_nothing(self) -> None:
        self.init()
        code, before_view = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, before_view)
        before = self.doc()
        before_bytes_host = before["host_revision"]
        code, out = self.retire("--absent", "--evidence", EVIDENCE, "--outcome", "owner-closed")
        self.assertEqual(code, 0, out)
        receipt = out["value"]
        self.assertEqual(set(receipt), RECEIPT_KEYS)
        self.assertEqual(receipt["kind"], "decisions")
        self.assertEqual(receipt["id"], DECISION_ID)
        self.assertEqual(receipt["outcome"], "owner-closed")
        self.assertIs(receipt["absent_at_retire"], True)
        self.assertEqual(receipt["evidence"], EVIDENCE)
        self.assertIsInstance(receipt["at"], str)
        self.assertIn("T", receipt["at"])
        self.assertEqual(receipt["host_revision"], before_bytes_host + 1)
        self.assertEqual(out["host_revision"], receipt["host_revision"])
        self.assertEqual(out["result"], "written")
        stored = self.doc()
        self.assertEqual(stored["host_revision"], receipt["host_revision"])
        self.assertEqual(stored["revision"], before["revision"] + 1)
        self.assertNotIn(DECISION_ID, stored["state"]["decisions"])
        self.assertNotIn("retired", stored["state"])
        raw = self.file.read_bytes()
        self.assertNotIn(EVIDENCE.encode(), raw)
        self.assertNotIn(b"absent_at_retire", raw)
        self.assertNotIn(b"owner-closed", raw)
        code, host = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, host)
        self.assertEqual(host["host_revision"], receipt["host_revision"])
        self.assertNotIn(DECISION_ID, json.dumps(host))
        code, side = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, side)
        self.assertEqual(side["host_revision"], receipt["host_revision"])
        self.assertEqual(side["pending_host_changes"], before_view["pending_host_changes"])
        self.assertFalse(any(DECISION_ID in item for item in side["pending_host_changes"]))
        # Nothing was stored, so the id is still absent and a later call is another receipt.
        code, again = self.retire("--absent", "--evidence", EVIDENCE)
        self.assertEqual(code, 0, again)
        self.assertEqual(again["value"]["outcome"], "resolved")
        self.assertEqual(again["value"]["host_revision"], receipt["host_revision"] + 1)
        self.assertNotIn(DECISION_ID, self.doc()["state"]["decisions"])
        self.assertNotIn("retired", self.doc()["state"])

    def test_retired_decisions_checkpoint_still_accepts_an_absent_row(self) -> None:
        self.init()
        code, out = self.retire("--absent", "--evidence", EVIDENCE)
        self.assertEqual(code, 0, out)
        revision = out["value"]["host_revision"]
        ident, problem = load_dispatch().checkpoint_entry(
            self.doc()["state"],
            {"input": f"host:decisions/{DECISION_ID}@{revision}",
             "applied": f"retired:decisions/{DECISION_ID}"},
            "node-holder")
        self.assertEqual(ident, f"host:decisions/{DECISION_ID}@{revision}")
        self.assertIsNone(problem)

    def test_absent_on_a_current_decision_is_refused(self) -> None:
        self.init()
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "ask",
                               "--kind", "decisions", "--id", DECISION_ID,
                               "--set", json.dumps({"owner": "user", "question": "ship it?"}))
        self.assertEqual(code, 0, out)
        before = self.file.read_bytes()
        code, out = self.retire("--absent", "--evidence", EVIDENCE, "--expect-rev", "1")
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn("is current", out["detail"])
        self.assertIn("--expect-rev", out["recovery"])
        self.assertIn("ORIGINAL_HANDLED_EVIDENCE", out["recovery"])
        self.assertNotIn("--absent", out["recovery"])
        self.assertEqual(self.file.read_bytes(), before)
        self.assertIn(DECISION_ID, self.doc()["state"]["decisions"])

    def test_without_absent_an_absent_id_stays_record_missing(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.retire("--expect-rev", "1", "--evidence", EVIDENCE)
        self.assertEqual((code, out["reason"]), (2, "record-missing"), out)
        self.assertIn(f"decisions/{DECISION_ID}", out["detail"])
        self.assertIn("--absent", out["recovery"])
        self.assertIn("ORIGINAL_OWNER_EVIDENCE", out["recovery"])
        self.assertIn("Do not create", out["recovery"])
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.retire("--expect-rev", "1", "--evidence", "ended", kind="holds", ident="absent-hold")
        self.assertEqual((code, out["reason"]), (2, "record-missing"), out)
        self.assertNotIn("--absent", out["recovery"])
        self.assertEqual(self.file.read_bytes(), before)

    def test_sideagent_and_tool_writers_are_refused(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.retire("--absent", "--evidence", EVIDENCE, writer="sideagent")
        self.assertEqual((code, out["reason"]), (2, "host-only"), out)
        self.assertEqual(self.file.read_bytes(), before)
        for writer in ("tool", "tool:execute"):
            code, out = self.retire("--absent", "--evidence", EVIDENCE, writer=writer)
            self.assertEqual((code, out["reason"]), (2, "writer-refused"), out)
            self.assertEqual(self.file.read_bytes(), before)

    def test_absent_is_decisions_only_and_rejects_a_current_row_flag(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.retire("--absent", "--evidence", EVIDENCE, kind="holds", ident="h1")
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn("only to decisions", out["detail"])
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.retire("--absent", "--evidence", EVIDENCE, kind="alerts", ident="a1")
        self.assertEqual(out["reason"], "invalid-input", out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.retire("--absent", "--evidence", "", )
        self.assertEqual((code, out["reason"]), (2, "evidence-required"), out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.retire("--absent", "--evidence", EVIDENCE, "--expect-rev", "0")
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn("--expect-rev", out["recovery"])
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "s",
                               "--kind", "holds", "--id", "h1", "--evidence", "ended")
        self.assertEqual(out["reason"], "record-missing", out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_docs_name_the_absent_receipt(self) -> None:
        api = (REPO / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertIn("--absent", api)
        self.assertIn("absent_at_retire", api)
        reference = (REPO / "templates" / "orchestrator" / "references" / "sideagent-node.md").read_text(encoding="utf-8")
        self.assertIn("retire --kind decisions --id ID --absent --evidence E", reference)
        self.assertLessEqual(len(reference.encode()), 8192)
        lifecycle = (REPO / "templates" / "orchestrator" / "references" / "lifecycle-state.md").read_text(encoding="utf-8")
        self.assertIn("--absent", lifecycle)
        self.assertLessEqual(len(lifecycle.encode()), 8192)
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = changelog.split("## 0.9.3", 1)[0]
        self.assertIn("Issue #298", unreleased)
        self.assertIn("Seats: restart not required", unreleased)
        help_out = subprocess.run([sys.executable, str(SCRIPT), "state", "retire", "--help"],
                                  capture_output=True, text=True, check=True).stdout
        self.assertIn("--absent", help_out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
