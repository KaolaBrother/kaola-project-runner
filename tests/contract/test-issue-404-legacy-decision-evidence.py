#!/usr/bin/env python3
"""Issue #404: legacy settled decisions with freeform evidence block migration.

The vrpai shape (rebuilt from the issue text only, no live state read): the
stored ``authorization.grants`` keeps each shared seat group split across one
row per member preset (Claude, kimi, antigravity), and two settled decision
rows dated 2026-10-14 carry ``evidence`` as a freeform object. On v0.9.26 an
``state update --section authorization`` that leaves the split rows in place
is refused ``authorization.grants: one authoritative row per shared group``,
and the sanctioned repair, ``state migrate``, then blocks the whole file on
``decisions.<id>.evidence``.

The fix is migrate-only tolerance: a present, nonempty evidence value in a
legacy freeform shape (object or array) still names original owner answer
evidence, so the settled row is removed exactly like the string case and the
split groups are consolidated. Missing, null or empty evidence is no answer
and keeps blocking (Unknown is not resolved), as do a type problem or a
non-owner row. The decisions write path stays closed-shape.
"""
from __future__ import annotations

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
for _name in CALLER_ENV:
    os.environ.pop(_name, None)

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}

# Legacy split shared-seat rows: one shared group per platform, stored as one
# row per member preset (issue: "one shared seat group split across multiple
# rows (legacy format)", groups Claude, kimi, antigravity).
SPLIT_GRANTS = [
    {"id": "claude-code/default", "state": "granted", "count": 1,
     "shared_seat": "vrpai-claude-shared"},
    {"id": "claude-code/opus-xhigh", "state": "granted", "count": 1,
     "shared_seat": "vrpai-claude-shared"},
    {"id": "kimi-cli/default", "state": "granted", "count": 1,
     "shared_seat": "vrpai-kimi-shared"},
    {"id": "kimi-cli/pro", "state": "granted", "count": 1,
     "shared_seat": "vrpai-kimi-shared"},
    {"id": "antigravity/default", "state": "granted", "count": 1,
     "shared_seat": "vrpai-antigravity-shared"},
    {"id": "antigravity/pro", "state": "granted", "count": 1,
     "shared_seat": "vrpai-antigravity-shared"},
]
SHARED_SEATS = ("vrpai-claude-shared", "vrpai-kimi-shared", "vrpai-antigravity-shared")

# The two settled rows named in the issue, evidence in the disallowed legacy
# freeform object shape.
OBJECT_EVIDENCE_DECISIONS = {
    "owner-shared-cache-rule-20261014": {
        "owner": "user", "question": "shared cache rule for worker seats",
        "status": "settled", "answer": "adopted",
        "evidence": {"source": "owner message 2026-10-14"},
        "created_at": "2026-10-14T10:00:00Z", "updated_at": "2026-10-14T10:00:00Z",
    },
    "selena-diskclean2-executed-20261014": {
        "owner": "user", "question": "diskclean2 executed",
        "status": "settled", "answer": "confirmed",
        "evidence": {"source": "selena receipt 2026-10-14"},
        "created_at": "2026-10-14T11:00:00Z", "updated_at": "2026-10-14T11:00:00Z",
    },
}
ABSENT = object()


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60,
        env=env if env is not None else {k: v for k, v in os.environ.items() if k not in CALLER_ENV})
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def settled_decision(evidence=ABSENT, **fields) -> dict:
    record = {"owner": "user", "question": "a legacy owner answer",
              "status": "settled", "answer": "done",
              "created_at": "2026-10-14T10:00:00Z", "updated_at": "2026-10-14T10:00:00Z"}
    record.update(fields)
    if evidence is not ABSENT:
        record["evidence"] = evidence
    return record


class LegacyDecisionEvidence(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i404-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str) -> tuple[int, dict]:
        return run(["state", *args])

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def write_state(self, state: dict, revision: int = 4) -> None:
        doc = {"schema": "kaola-heartbeat-prompt/2", "revision": revision,
               "host_revision": revision, "body": "{}",
               "state": {"project": {"code": "VRPAI", "goal": "fixture built from KPR #404 issue text",
                                     "repo": str(self.repo), "status": "active"},
                         **state}}
        self.file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def init(self) -> None:
        code, out = self.state(
            "init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
            "--project", json.dumps({"code": "KT", "goal": "ship", "repo": str(self.repo)}),
            "--authorization", json.dumps(AUTH))
        self.assertEqual(code, 0, out)

    def update(self, *extra: str) -> tuple[int, dict]:
        return self.state("update", "--file", str(self.file), *extra)

    def vrpai_doc(self) -> None:
        self.write_state({"authorization": {"grants": json.loads(json.dumps(SPLIT_GRANTS))},
                          "decisions": json.loads(json.dumps(OBJECT_EVIDENCE_DECISIONS))})

    def test_vrpai_state_refuses_authorization_write_then_migrates(self) -> None:
        self.vrpai_doc()
        original = self.file.read_bytes()

        # (a) Symptom 1: an authorization change that leaves the split
        # shared-seat rows in place is refused; migration is the named repair.
        code, out = self.update("--writer", "host", "--source", "owner-worker-grants",
                                "--section", "authorization", "--expect-revision", "4",
                                "--set", json.dumps({"exclusions": ["zcode/default"]}))
        self.assertEqual((code, out.get("reason")), (2, "invalid-input"), out)
        self.assertEqual(out.get("path"), "authorization.grants")
        self.assertIn("one authoritative row per shared group", out.get("allowed", ""))
        self.assertIn("plan migration", out.get("recovery", ""))
        self.assertEqual(self.file.read_bytes(), original)

        # The read-only plan is clean: it names the three groupings and both
        # settled decision removals, and writes nothing.
        code, plan = self.state("migrate", "--file", str(self.file))
        self.assertEqual((code, plan.get("result")), (0, "planned"), plan)
        self.assertFalse(plan.get("writes"))
        removed = plan["report"]["removed"]
        for seat in SHARED_SEATS:
            self.assertIn(f"authorization.grants.{seat} repeated rows -> one group", removed)
        for ident in OBJECT_EVIDENCE_DECISIONS:
            self.assertIn(f"decisions.{ident}", removed)
        self.assertEqual(self.file.read_bytes(), original)

        # The write lands: three groups consolidated, both settled rows gone.
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out.get("result")), (0, "migrated"), out)
        grants = self.doc()["state"]["authorization"]["grants"]
        self.assertEqual(len(grants), 3)
        by_seat = {grant["shared_seat"]: grant for grant in grants}
        self.assertEqual(set(by_seat), set(SHARED_SEATS))
        self.assertEqual(by_seat["vrpai-claude-shared"]["preset_ids"],
                         ["claude-code/default", "claude-code/opus-xhigh"])
        self.assertEqual(by_seat["vrpai-kimi-shared"]["preset_ids"], ["kimi-cli/default", "kimi-cli/pro"])
        self.assertEqual(by_seat["vrpai-antigravity-shared"]["preset_ids"],
                         ["antigravity/default", "antigravity/pro"])
        self.assertEqual(self.doc()["state"]["decisions"], {})

        # The original write symptom is gone once the stored shape is grouped.
        code, out = self.update("--writer", "host", "--source", "owner-worker-grants",
                                "--section", "authorization",
                                "--expect-revision", str(self.doc()["revision"]),
                                "--set", json.dumps({"exclusions": ["zcode/default"]}))
        self.assertEqual((code, out.get("result")), (0, "written"), out)

        # A second migrate is a clean no-op.
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out.get("result")), (0, "current"), out)

    def test_missing_or_empty_evidence_still_blocks(self) -> None:
        variants = (
            ("missing", ABSENT),
            ("null", None),
            ("empty-string", ""),
            ("empty-list", []),
            ("empty-object", {}),
        )
        for label, evidence in variants:
            with self.subTest(evidence=label):
                self.write_state({"authorization": json.loads(json.dumps(AUTH)),
                                  "decisions": {"d1": settled_decision(evidence)}})
                original = self.file.read_bytes()
                code, out = self.state("migrate", "--file", str(self.file))
                self.assertEqual((code, out.get("result")), (2, "blocked"), out)
                self.assertFalse(out.get("writes"))
                self.assertEqual([row["path"] for row in out["blockers"]],
                                 ["decisions.d1.evidence"])
                self.assertIn("Unknown is not resolved", out["blockers"][0]["recovery"])
                self.assertEqual(self.file.read_bytes(), original)

    def test_type_problem_or_foreign_owner_still_blocks(self) -> None:
        variants = (
            ("answer-not-a-string", settled_decision("owner note", answer=["not", "a", "string"])),
            ("owner-not-a-role", settled_decision("owner note", owner="selena")),
        )
        for label, record in variants:
            with self.subTest(row=label):
                self.write_state({"authorization": json.loads(json.dumps(AUTH)),
                                  "decisions": {"d1": record}})
                original = self.file.read_bytes()
                code, out = self.state("migrate", "--file", str(self.file), "--write")
                self.assertEqual((code, out.get("result")), (2, "blocked"), out)
                self.assertEqual([row["path"] for row in out["blockers"]],
                                 ["decisions.d1.evidence"])
                self.assertEqual(self.file.read_bytes(), original)

    def test_string_and_string_list_evidence_migrate(self) -> None:
        self.write_state({"authorization": json.loads(json.dumps(AUTH)),
                          "decisions": {
                              "d-string": settled_decision("owner message 9"),
                              "d-list": settled_decision(["commit a1b2c3", "owner note"]),
                              "d-freeform-array": settled_decision([{"legacy": "receipt"}]),
                          }})
        code, plan = self.state("migrate", "--file", str(self.file))
        self.assertEqual((code, plan.get("result")), (0, "planned"), plan)
        removed = plan["report"]["removed"]
        for ident in ("d-string", "d-list", "d-freeform-array"):
            self.assertIn(f"decisions.{ident}", removed)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out.get("result")), (0, "migrated"), out)
        self.assertEqual(self.doc()["state"]["decisions"], {})

    def test_decisions_write_path_stays_closed_shape(self) -> None:
        self.init()
        code, out = self.update("--writer", "host", "--source", "turn-2",
                                "--kind", "decisions", "--id", "d1",
                                "--set", json.dumps({"owner": "user", "question": "ship now?"}))
        self.assertEqual(code, 0, out)

        # A create carrying legacy object evidence is refused.
        before = self.file.read_bytes()
        code, out = self.update("--writer", "host", "--source", "legacy-shape",
                                "--kind", "decisions", "--id", "d2",
                                "--set", json.dumps({"owner": "user", "question": "new",
                                                     "evidence": {"legacy": "object"}}))
        self.assertEqual((code, out.get("reason")), (2, "invalid-input"), out)
        self.assertIn("evidence must be a reference string or a list of references",
                      out.get("detail", ""))
        self.assertEqual(self.file.read_bytes(), before)

        # So is a settle of the pending row carrying object evidence.
        row = self.doc()["state"]["decisions"]["d1"]
        code, out = self.update("--writer", "host", "--source", "legacy-shape",
                                "--kind", "decisions", "--id", "d1",
                                "--expect-rev", str(row["rev"]),
                                "--set", json.dumps({"status": "settled",
                                                     "evidence": {"legacy": "object"}}))
        self.assertEqual((code, out.get("reason")), (2, "invalid-input"), out)
        self.assertIn("evidence must be a reference string or a list of references",
                      out.get("detail", ""))
        self.assertEqual(self.file.read_bytes(), before)

        # The pending row survives untouched and still settles on a string.
        row = self.doc()["state"]["decisions"]["d1"]
        self.assertEqual(row.get("status", "pending"), "pending")
        self.assertNotIn("evidence", row)
        code, out = self.update("--writer", "host", "--source", "owner-answer",
                                "--kind", "decisions", "--id", "d1",
                                "--expect-rev", str(row["rev"]),
                                "--set", json.dumps({"status": "settled",
                                                     "evidence": "owner message 9"}))
        self.assertEqual(code, 0, out)
        self.assertNotIn("d1", self.doc()["state"]["decisions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
