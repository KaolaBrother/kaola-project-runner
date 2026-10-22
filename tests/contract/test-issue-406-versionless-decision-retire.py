#!/usr/bin/env python3
"""Issue #406: a versionless row already in its closed shape retires directly.

The dead-end shape is a ``decisions`` row written before record revisions:
no ``rev``, ``status`` ``settled``, and ``evidence`` that migration cannot
judge — missing, an empty string, ``null``, or a leafless container. On
v0.9.27 ``state migrate`` and ``state migrate --write`` blocked the whole
file on ``decisions.<id>.evidence`` ("keep the row visible"), while ``state
update`` and ``state retire`` refused ``record-versionless`` and named that
same blocked migrate, so no refusal named an operation that worked.

Issue #406 generalizes the narrow #395 alert exit into one closed-shape
rule: a versionless record whose stored shape already ends its duty —
``alerts`` with empty ``inputs``, a ``decisions`` row with ``status``
``settled``, or a ``tasks`` row cancelled or accepted at stage ``done`` —
retires directly with explicit ``--expect-rev 0`` and non-empty
``--evidence`` supplied by the operator. Migration still refuses to write a
file holding such a row (it cannot invent the owner answer; Unknown is not
resolved), but its blocker now names the working retire command. A pending
decision, an alert with returned inputs, a live task, and a hold have no
closed shape and stay on the migrate plan, and the #404 migrate-only
tolerance for a usable legacy freeform evidence container is unchanged.

Review repair: the evidence a retire supplies for a settled decision whose
stored evidence is unusable attests the owner's original answer, so only the
Host runs it — other writers are ``host-only`` and the refusal names the
exact Host command. The migrate blocker also names the row's recorded
revision when it carries one (``--expect-rev <rev>``), not always the
explicit zero.
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
ABSENT = object()
SUPPLIED = "the owner answered: seat plan B applies"
# The four evidence variants issue #406 names: missing key, empty string,
# null, and a container with no nonblank string leaf.
EVIDENCE_VARIANTS = (
    ("missing", ABSENT),
    ("empty-string", ""),
    ("null", None),
    ("leafless-container", {"answer": {"text": "", "ref": None}, "notes": []}),
)


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


def legacy_decision(*, evidence=ABSENT, status: str = "settled",
                    owner: str = "user") -> dict:
    record = {"owner": owner, "question": "Which seat plan applies?",
              "status": status, "created_at": "2026-09-01T00:00:00Z",
              "updated_at": "2026-09-02T00:00:00Z",
              "source": "legacy-host-write", "writer": "host"}
    if evidence is not ABSENT:
        record["evidence"] = evidence
    return record


class VersionlessDecisionRetire(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i406-")
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

    def plant(self, row: dict, ident: str) -> None:
        doc = self.doc()
        doc["state"]["decisions"][ident] = row
        self.write_doc(doc)

    def retire(self, *extra: str, ident: str, evidence: str = SUPPLIED) -> tuple[int, dict]:
        return run(["state", "retire", "--file", str(self.file), "--writer", "host",
                    "--source", "evt", "--kind", "decisions", "--id", ident,
                    "--evidence", evidence, *extra])

    def migrate(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "migrate", "--file", str(self.file), *extra])

    def check(self) -> tuple[int, dict]:
        return run(["state", "check", "--file", str(self.file)])

    def bloat(self, out: dict) -> dict:
        return {row["id"]: row for row in out.get("problems") or []
                if row.get("code") == "state-bloat"}

    def blockers_for(self, out: dict, ident: str) -> list[dict]:
        return [row for row in out.get("blockers") or []
                if row.get("path") == f"decisions.{ident}.evidence"]

    def test_migrate_refusal_names_the_working_route_for_each_variant(self) -> None:
        for label, evidence in EVIDENCE_VARIANTS:
            ident = f"legacy-seat-plan-{label}"
            self.plant(legacy_decision(evidence=evidence), ident)

        for extra in ([], ["--write"]):
            with self.subTest(extra=extra):
                before = self.file.read_bytes()
                code, out = self.migrate(*extra)
                self.assertEqual((code, out.get("result")), (2, "blocked"), out)
                self.assertFalse(out.get("writes"), out)
                for label, _evidence in EVIDENCE_VARIANTS:
                    ident = f"legacy-seat-plan-{label}"
                    blockers = self.blockers_for(out, ident)
                    self.assertTrue(blockers, out)
                    text = blockers[0]["detail"] + " " + blockers[0].get("recovery", "")
                    self.assertIn(f"--kind decisions --id {ident} --expect-rev 0", text)
                    self.assertIn("--evidence ORIGINAL_OWNER_EVIDENCE", text)
                    self.assertIn("Unknown is not resolved", text)
                    self.assertIn(ident, self.doc()["state"]["decisions"])
                self.assertEqual(self.file.read_bytes(), before)

    def test_refusals_name_the_direct_route_and_write_nothing(self) -> None:
        for label, evidence in EVIDENCE_VARIANTS:
            ident = f"legacy-seat-plan-{label}"
            self.plant(legacy_decision(evidence=evidence), ident)
            before = self.file.read_bytes()

            # A record write still needs a migration-assigned revision, but the
            # refusal now names the direct retire this closed shape supports.
            code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                             "--source", "evt", "--kind", "decisions", "--id", ident,
                             "--expect-rev", "0", "--set", json.dumps({"next": "none"})])
            self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
            self.assertIn("retire", out["recovery"])
            self.assertIn("--expect-rev 0", out["recovery"])

            # Retire without the explicit zero, with a nonzero, with no
            # evidence, or with blank evidence all stay refused on the same
            # named route; the row is never dropped.
            for extra, evidence in (([], SUPPLIED), (["--expect-rev", "1"], SUPPLIED),
                                    (["--expect-rev", "0"], " \t\n")):
                with self.subTest(label=label, extra=extra):
                    code, out = self.retire(*extra, ident=ident, evidence=evidence)
                    self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
                    self.assertIn(f"--id {ident} --expect-rev 0", out["recovery"])
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "state", "retire", "--file", str(self.file),
                 "--writer", "host", "--source", "evt", "--kind", "decisions",
                 "--id", ident, "--expect-rev", "0"],
                capture_output=True, text=True, timeout=60,
                env={k: v for k, v in os.environ.items() if k not in CALLER_ENV})
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("--evidence", proc.stderr)

            self.assertIn(ident, self.doc()["state"]["decisions"])
            self.assertEqual(self.file.read_bytes(), before)

    def test_direct_retire_removes_the_row_and_keeps_supplied_evidence(self) -> None:
        for label, evidence in EVIDENCE_VARIANTS:
            with self.subTest(label=label):
                ident = f"legacy-seat-plan-{label}"
                self.plant(legacy_decision(evidence=evidence), ident)
                code, out = self.retire("--expect-rev", "0", ident=ident)
                self.assertEqual((code, out.get("result")), (0, "written"), out)
                value = out["value"]
                self.assertEqual(value["kind"], "decisions")
                self.assertEqual(value["id"], ident)
                self.assertEqual(value["outcome"], "resolved")
                self.assertEqual(value["evidence"], SUPPLIED)
                doc = self.doc()
                self.assertNotIn(ident, doc["state"].get("decisions") or {})
                self.assertFalse(doc["state"].get("retired"))
                code, out = self.retire("--expect-rev", "0", ident=ident)
                self.assertEqual((code, out.get("reason")), (2, "record-missing"), out)

    def test_check_emits_a_runnable_direct_command_for_each_variant(self) -> None:
        for label, evidence in EVIDENCE_VARIANTS:
            with self.subTest(label=label):
                ident = f"legacy-seat-plan-{label}"
                self.plant(legacy_decision(evidence=evidence), ident)
                code, out = self.check()
                self.assertEqual(code, 0, out)
                row = self.bloat(out)[ident]
                self.assertEqual(row["class"], "settled")
                self.assertIsNone(row["rev"])
                command = row["command"]
                self.assertIn("retire", command)
                self.assertIn(f"--kind decisions --id {ident}", command)
                self.assertIn("--expect-rev 0", command)
                self.assertIn("--evidence", command)
                self.assertNotIn("migrate", command)
                self.assertNotIn("--expect-rev None", command)
                # The stored evidence cannot be judged, so the command names
                # the placeholder the operator replaces with the original
                # owner answer.
                self.assertIn("ORIGINAL_OWNER_EVIDENCE", command)
                ran, receipt = execute(
                    command.replace("ORIGINAL_OWNER_EVIDENCE", shlex.quote(SUPPLIED)))
                self.assertEqual(ran, 0, receipt)
                self.assertEqual(receipt["value"]["evidence"], SUPPLIED)
                self.assertNotIn(ident, self.doc()["state"].get("decisions") or {})

    def test_decision_retire_with_unusable_stored_evidence_is_host_only(self) -> None:
        # Review: the supplied evidence attests the owner's original answer,
        # so only the Host may run this retire; the refusal names the exact
        # Host command. A rev-bearing settled row in the same shape is the
        # same gate.
        idents = []
        for label, evidence in EVIDENCE_VARIANTS:
            ident = f"legacy-seat-plan-{label}"
            self.plant(legacy_decision(evidence=evidence), ident)
            idents.append(ident)
        versioned = legacy_decision(evidence=None)
        versioned["rev"] = 1
        self.plant(versioned, "versioned-settled")
        idents.append("versioned-settled")

        for ident in idents:
            with self.subTest(ident=ident):
                expect = "1" if ident == "versioned-settled" else "0"
                before = self.file.read_bytes()
                code, out = run(["state", "retire", "--file", str(self.file),
                                 "--writer", "sideagent", "--source", "evt",
                                 "--kind", "decisions", "--id", ident,
                                 "--expect-rev", expect, "--evidence", SUPPLIED])
                self.assertEqual((code, out.get("reason")), (2, "host-only"), out)
                recovery = out.get("recovery") or ""
                self.assertIn("the Host runs", recovery)
                self.assertIn("--writer host", recovery)
                self.assertIn(f"--kind decisions --id {ident}", recovery)
                self.assertIn(f"--expect-rev {expect}", recovery)
                self.assertIn("--evidence ORIGINAL_OWNER_EVIDENCE", recovery)
                self.assertIn(ident, self.doc()["state"]["decisions"])
                self.assertEqual(self.file.read_bytes(), before)

                # The named Host route completes with the real evidence.
                code, out = self.retire("--expect-rev", expect, ident=ident)
                self.assertEqual((code, out.get("result")), (0, "written"), out)
                self.assertNotIn(ident, self.doc()["state"]["decisions"])

        # A settled row with usable stored evidence keeps the existing writer
        # rules: the stored value already carries the owner answer.
        self.plant(legacy_decision(evidence="owner said plan B"), "usable-settled")
        code, out = run(["state", "retire", "--file", str(self.file),
                         "--writer", "sideagent", "--source", "evt",
                         "--kind", "decisions", "--id", "usable-settled",
                         "--expect-rev", "0", "--evidence", SUPPLIED])
        self.assertNotEqual(out.get("reason"), "host-only", out)

        # The literal placeholder the emitted command carries is not evidence.
        self.plant(legacy_decision(evidence=ABSENT), "placeholder-row")
        code, out = self.retire("--expect-rev", "0", ident="placeholder-row",
                                evidence="ORIGINAL_OWNER_EVIDENCE")
        self.assertEqual((code, out.get("reason")), (2, "invalid-input"), out)
        self.assertIn("placeholder-row", self.doc()["state"]["decisions"])

    def test_blocker_names_the_recorded_revision_when_the_row_has_one(self) -> None:
        # #259 exactness: a settled row that already carries a revision names
        # that revision in the retire command its blocker prints.
        row = legacy_decision(evidence=ABSENT)
        row["rev"] = 1
        self.plant(row, "versioned-settled")
        for extra in ([], ["--write"]):
            with self.subTest(extra=extra):
                before = self.file.read_bytes()
                code, out = self.migrate(*extra)
                self.assertEqual((code, out.get("result")), (2, "blocked"), out)
                blockers = self.blockers_for(out, "versioned-settled")
                self.assertTrue(blockers, out)
                text = blockers[0]["detail"]
                self.assertIn("--id versioned-settled --expect-rev 1", text)
                self.assertIn("--evidence ORIGINAL_OWNER_EVIDENCE", text)
                self.assertEqual(self.file.read_bytes(), before)
        # The named route works at that revision — for the Host only.
        code, out = run(["state", "retire", "--file", str(self.file),
                         "--writer", "sideagent", "--source", "evt",
                         "--kind", "decisions", "--id", "versioned-settled",
                         "--expect-rev", "1", "--evidence", SUPPLIED])
        self.assertEqual((code, out.get("reason")), (2, "host-only"), out)
        code, out = self.retire("--expect-rev", "1", ident="versioned-settled")
        self.assertEqual((code, out.get("result")), (0, "written"), out)

    def test_migrate_write_succeeds_after_the_dead_end_rows_retire(self) -> None:
        # The original symptom end to end: while the dead-end rows stay, the
        # file cannot be written at all; once each named route retires its
        # row, migrate --write completes and revises what remains.
        idents = []
        for label, evidence in EVIDENCE_VARIANTS:
            ident = f"legacy-seat-plan-{label}"
            self.plant(legacy_decision(evidence=evidence), ident)
            idents.append(ident)
        self.plant(legacy_decision(evidence=ABSENT, status="pending"), "open-question")

        code, out = self.migrate("--write")
        self.assertEqual((code, out.get("result")), (2, "blocked"), out)
        self.assertFalse(out.get("writes"), out)
        for ident in idents:
            self.assertTrue(self.blockers_for(out, ident), out)

        for ident in idents:
            with self.subTest(ident=ident):
                code, out = self.retire("--expect-rev", "0", ident=ident)
                self.assertEqual((code, out.get("result")), (0, "written"), out)

        code, out = self.migrate("--write")
        self.assertEqual((code, out.get("result")), (0, "migrated"), out)
        decisions = self.doc()["state"]["decisions"]
        self.assertEqual(list(decisions), ["open-question"])
        self.assertEqual(decisions["open-question"]["rev"], 1)

    def test_usable_stored_evidence_is_carried_into_the_command(self) -> None:
        ident = "legacy-seat-plan-usable"
        self.plant(legacy_decision(evidence="owner said plan B"), ident)
        code, out = self.check()
        self.assertEqual(code, 0, out)
        command = self.bloat(out)[ident]["command"]
        self.assertIn("--evidence 'owner said plan B'", command)
        self.assertIn("--expect-rev 0", command)
        # An explicit operator evidence still wins over the stored string.
        code, out = self.retire("--expect-rev", "0", ident=ident,
                                evidence="the owner's recorded answer")
        self.assertEqual((code, out.get("result")), (0, "written"), out)
        self.assertEqual(out["value"]["evidence"], "the owner's recorded answer")
        self.assertNotIn(ident, self.doc()["state"].get("decisions") or {})

    def test_pending_decision_and_hold_have_no_closed_shape(self) -> None:
        self.plant(legacy_decision(evidence=ABSENT, status="pending"), "open-question")
        doc = self.doc()
        doc["state"]["holds"]["legacy-hold"] = {
            "scope": "seats", "reason": "legacy grant freeze",
            "created_at": "2026-09-01T00:00:00Z", "source": "legacy", "writer": "host"}
        self.write_doc(doc)
        before = self.file.read_bytes()

        for kind, ident in (("decisions", "open-question"), ("holds", "legacy-hold")):
            with self.subTest(kind=kind):
                code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                                 "--source", "evt", "--kind", kind, "--id", ident,
                                 "--expect-rev", "0", "--evidence", SUPPLIED])
                self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
                self.assertIn("migrate", out["recovery"])
                self.assertIn("--write", out["recovery"])
                self.assertNotIn("--expect-rev 0", out["recovery"])
        self.assertEqual(self.file.read_bytes(), before)

        # Unknown is not resolved: migration keeps the pending row current
        # and assigns its first revision; the normal gates then apply.
        code, out = self.migrate("--write")
        self.assertEqual((code, out.get("result")), (0, "migrated"), out)
        doc = self.doc()
        self.assertEqual(doc["state"]["decisions"]["open-question"]["rev"], 1)
        self.assertEqual(doc["state"]["decisions"]["open-question"]["status"], "pending")
        self.assertEqual(doc["state"]["holds"]["legacy-hold"]["rev"], 1)

    def test_404_migrate_tolerance_for_usable_legacy_evidence_is_intact(self) -> None:
        self.plant(legacy_decision(evidence="owner said plan B"), "string-evidence")
        self.plant(legacy_decision(evidence=["owner said plan B"]), "list-evidence")
        self.plant(legacy_decision(evidence={"answer": "plan B"}), "freeform-evidence")
        code, out = self.migrate("--write")
        self.assertEqual((code, out.get("result")), (0, "migrated"), out)
        removed = out.get("removed") or out.get("report", {}).get("removed") or []
        for ident in ("string-evidence", "list-evidence", "freeform-evidence"):
            self.assertIn(f"decisions.{ident}", removed, out)
        self.assertEqual(self.doc()["state"].get("decisions") or {}, {})

    def test_versioned_settled_decision_keeps_conflict_semantics(self) -> None:
        row = legacy_decision(evidence="owner said plan B")
        row["rev"] = 1
        self.plant(row, "versioned")
        # A stored settled row with a revision is not a direct candidate: the
        # explicit zero conflicts like any wrong --expect-rev.
        code, out = self.retire("--expect-rev", "0", ident="versioned")
        self.assertEqual((code, out.get("reason")), (3, "conflict"), out)
        self.assertIn("versioned", self.doc()["state"]["decisions"])
        code, out = self.retire("--expect-rev", "1", ident="versioned")
        self.assertEqual(code, 0, out)

    def test_closed_shapes_on_other_kinds(self) -> None:
        doc = self.doc()
        doc["state"]["tasks"]["cancelled-legacy"] = {
            "stage": "review", "goal": "dropped work",
            "verdict": {"value": "cancelled", "why": "no longer needed"},
            "created_at": "2026-09-01T00:00:00Z", "source": "legacy", "writer": "host"}
        doc["state"]["tasks"]["accepted-legacy"] = {
            "stage": "done", "goal": "finished work",
            "verdict": {"value": "accepted", "why": "verified"},
            "created_at": "2026-09-01T00:00:00Z", "source": "legacy", "writer": "host"}
        doc["state"]["tasks"]["doing-legacy"] = {
            "stage": "doing", "goal": "unfinished work", "next": "keep going",
            "created_at": "2026-09-01T00:00:00Z", "source": "legacy", "writer": "host"}
        doc["state"]["alerts"]["resolved-legacy"] = {
            "level": "warn", "summary": "handled exception", "inputs": {},
            "evidence": ["handled"], "created_at": "2026-09-01T00:00:00Z",
            "source": "legacy", "writer": "host"}
        self.write_doc(doc)

        # The cancelled task and the resolved alert take the same direct path.
        for kind, ident in (("tasks", "cancelled-legacy"), ("alerts", "resolved-legacy")):
            with self.subTest(kind=kind, ident=ident):
                code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                                 "--source", "evt", "--kind", kind, "--id", ident,
                                 "--expect-rev", "0", "--evidence", SUPPLIED])
                self.assertEqual((code, out.get("result")), (0, "written"), out)
                self.assertNotIn(ident, self.doc()["state"].get(kind) or {})

        # The accepted-done task keeps its substantive gates: the cite that
        # must survive is still required on the direct path.
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "accepted-legacy",
                         "--expect-rev", "0", "--evidence", SUPPLIED])
        self.assertEqual((code, out.get("reason")), (2, "cite-required"), out)
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "accepted-legacy",
                         "--expect-rev", "0", "--evidence", SUPPLIED,
                         "--cite", json.dumps({"path": "README.md"})])
        self.assertEqual((code, out.get("result")), (0, "written"), out)
        self.assertNotIn("accepted-legacy", self.doc()["state"].get("tasks") or {})

        # A live task has no closed shape: it refuses and names the migrate
        # plan, and the plan assigns the first revision without deleting it.
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "doing-legacy",
                         "--expect-rev", "0", "--evidence", SUPPLIED])
        self.assertEqual((code, out.get("reason")), (2, "record-versionless"), out)
        self.assertIn("migrate", out["recovery"])
        code, out = self.migrate("--write")
        self.assertEqual((code, out.get("result")), (0, "migrated"), out)
        self.assertEqual(self.doc()["state"]["tasks"]["doing-legacy"]["rev"], 1)

    @unittest.skip("#397: v1 body.alerts mapping is outside this change's scope")
    def test_v1_body_alerts_is_out_of_scope(self) -> None:
        pass

    @unittest.skip("#397: a large carrier without a proving holder is outside this change")
    def test_large_carrier_is_out_of_scope(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
