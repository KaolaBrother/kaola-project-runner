#!/usr/bin/env python3
"""Issue #267: the tool keeps the current owner's repair count.

A Host ``repair`` verdict is one failed formal submission. The second such
verdict for the same obligation and the same owner is the escalation trigger.
Replays, late results, and results whose order cannot be bound do not
double-count. The count is absent when it is unknown; it is never stored as
zero. No second ledger or history list is created.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
LEGACY_COMMIT = "dad228e4898e8f440e6227077917161c2d7e9fdb"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for _name in CALLER_ENV:
    os.environ.pop(_name, None)


def run_script(script: Path, args: list[str]) -> tuple[int, dict, str]:
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          env={key: value for key, value in os.environ.items() if key not in CALLER_ENV})
    try:
        return proc.returncode, json.loads(proc.stdout), proc.stderr
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def attention_fingerprint(body: str) -> str:
    view = json.loads(body)
    text = json.dumps(view["attention"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class RejectionCount(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i267-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        code, out, err = self.state("init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
                                    "--project", json.dumps({"code": "KT", "goal": "ship"}),
                                    "--authorization", json.dumps({"grants": [{"id": "zcode/default", "state": "granted", "count": 1}]}))
        self.assertEqual(code, 0, (out, err))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str, script: Path = SCRIPT) -> tuple[int, dict, str]:
        return run_script(script, ["state", *args])

    def update(self, writer: str, kind: str, ident: str, patch: dict, *extra: str,
               script: Path = SCRIPT) -> tuple[int, dict, str]:
        return self.state("update", "--file", str(self.file), "--writer", writer, "--source", "evt",
                          "--kind", kind, "--id", ident, "--set", json.dumps(patch), *extra, script=script)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def task(self, ident: str = "gate") -> dict:
        return self.doc()["state"]["tasks"][ident]

    def rejection(self, ident: str = "gate") -> dict:
        stored = self.task(ident).get("rejection")
        self.assertIsInstance(stored, dict)
        return stored

    def view(self, role: str) -> dict:
        code, out, err = self.state("view", "--file", str(self.file), "--role", role, "--repo", str(self.repo))
        self.assertEqual(code, 0, (out, err))
        return out

    def open_task(self, ident: str = "gate", **patch: object) -> None:
        body = {"stage": "review", "goal": "ship the parser", "preset": "worker-a",
                "acceptance": "the package gate passes", "dispatch": ["item-1"]}
        body.update(patch)
        code, out, err = self.update("host", "tasks", ident, body)
        self.assertEqual(code, 0, (out, err))

    def reject(self, ident: str = "gate", why: str = "rejected", writer: str = "host",
               **patch: object) -> dict:
        rev = str(self.task(ident)["rev"])
        extra: list[str] = ["--expect-rev", rev]
        host_turn = patch.pop("host_turn", None)
        if host_turn is not None:
            extra.extend(["--host-turn", str(host_turn)])
        body = {"verdict": {"value": "repair", "why": why}, **patch}
        code, out, err = self.update(writer, "tasks", ident, body, *extra)
        self.assertEqual(code, 0, (out, err))
        return self.task(ident)

    def reopen(self, ident: str = "gate") -> None:
        """Return the same obligation for a new acceptance submission."""
        rev = str(self.task(ident)["rev"])
        code, out, err = self.update("sideagent", "tasks", ident, {"stage": "doing"}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        rev = str(self.task(ident)["rev"])
        code, out, err = self.update("sideagent", "tasks", ident, {"stage": "review"}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))

    def fingerprint(self) -> str:
        return attention_fingerprint(self.doc()["body"])

    def test_repeated_rejection_increments_and_both_views_show_it(self) -> None:
        self.open_task()
        self.assertNotIn("count", self.task().get("rejection") or {})
        first = self.reject(why="defect a; defect b; defect c", evidence="receipt-1",
                            dispositions={"item-1": "repair"})
        self.assertEqual(first["rejection"]["count"], 1)
        self.assertEqual(first["rejection"]["v"], 1)
        self.assertEqual(first["rejection"]["owner"], "worker-a")
        self.assertEqual(first["rejection"]["dispatch"], "item-1")
        self.assertEqual(first["rejection"]["receipt"], "receipt-1")
        self.reopen()
        self.assertEqual(self.task()["prior_verdict"]["value"], "repair")
        self.assertEqual(self.task()["evidence"], "receipt-1", "the first receipt stays on the task")
        second = self.reject(why="self-tests passed; acceptance evidence is empty",
                             evidence="receipt-2", dispositions={"item-2": "repair"})
        self.assertEqual(second["rejection"]["count"], 2, "the second formal submission is the escalation count")
        self.assertEqual(second["rejection"]["dispatch"], "item-2")
        self.assertEqual(second["rejection"]["receipt"], "receipt-2")
        self.assertNotIn("review", second, "review is consumed, not stored on the task")
        self.assertNotIn("effort", second)
        host = self.view("host")
        delegator = self.view("delegator")
        host_row = host["tasks"][0]["rejection"]
        brief = delegator["doing"][0]["rejection"]
        for shown in (host_row, brief):
            self.assertEqual(shown["count"], 2)
            self.assertEqual(shown["owner"], "worker-a")
            self.assertEqual(shown["escalation"], "owed")
            self.assertEqual(shown["submission"]["dispatch"], "item-2")
            self.assertEqual(shown["submission"]["receipt"], "receipt-2")
        self.assertEqual(delegator["doing"][0]["verdict"], "repair")
        self.assertTrue(delegator["special"]["holds"] == [])
        opened = [row for row in host["attention"] if row["why"] == "delivery-open"]
        self.assertEqual(opened[0]["rejection_count"], 2)
        self.assertEqual(opened[0]["escalation"], "owed")
        self.assertEqual(self.doc()["schema"], "kaola-heartbeat-prompt/2")

    def test_explicit_review_gap_counts_once_and_replays_do_not(self) -> None:
        self.open_task()
        self.reject(why="first", review=1, evidence="receipt-1", dispositions={"item-1": "repair"})
        self.assertEqual(self.rejection()["count"], 1)
        again = self.reject(why="first again", review=1, evidence="receipt-1b",
                            dispositions={"item-1": "repair"})
        self.assertEqual(again["rejection"]["count"], 1)
        self.assertEqual(again["rejection"]["receipt"], "receipt-1", "a replay keeps the counted receipt")
        jumped = self.reject(why="fifth review, second submission", review=5, evidence="receipt-5",
                             dispositions={"item-5": "repair"})
        self.assertEqual(jumped["rejection"]["count"], 2, "the count is submissions, not the review index")
        self.assertEqual(jumped["rejection"]["review"], 5)
        self.assertEqual(jumped["verdict"]["why"], "fifth review, second submission")

    def test_host_and_sideagent_replays_of_one_submission_count_once(self) -> None:
        self.open_task()
        rev = str(self.task()["rev"])
        code, out, err = self.update("sideagent", "tasks", "gate",
                                     {"verdict": {"value": "repair", "why": "transcribed"}, "review": 1,
                                      "evidence": "receipt-1"},
                                     "--expect-rev", rev, "--host-turn", "turn-a")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 1)
        self.assertEqual(self.task()["verdict"]["host_turn"], "turn-a")
        self.assertEqual(self.task()["verdict"]["by"], "host", "the Sideagent transcribed; it did not judge")
        self.reject(why="host confirms the same review", review=1)
        self.assertEqual(self.rejection()["count"], 1)
        rev = str(self.task()["rev"])
        code, out, err = self.update("sideagent", "tasks", "gate",
                                     {"verdict": {"value": "repair", "why": "same turn, later review"},
                                      "review": 2, "evidence": "receipt-2"},
                                     "--expect-rev", rev, "--host-turn", "turn-a")
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "the same Host turn id is not the idempotency key")
        self.assertEqual(self.rejection()["receipt"], "receipt-2")

    def test_late_and_unbound_results_leave_the_current_count(self) -> None:
        self.open_task()
        self.reject(why="current", review=2, evidence="receipt-2", dispositions={"item-2": "repair"})
        self.assertEqual(self.rejection()["count"], 1)
        late = self.reject(why="old result", review=1, evidence="receipt-1",
                           dispositions={"item-1": "repair"})
        self.assertEqual(late["rejection"]["count"], 1)
        self.assertEqual(late["rejection"]["review"], 2)
        self.assertEqual(late["rejection"]["dispatch"], "item-2")
        self.assertEqual(late["verdict"]["why"], "current")
        unbound = self.reject(why="no order", review=0, evidence="receipt-x",
                              dispositions={"item-x": "repair"})
        self.assertEqual(unbound["rejection"]["count"], 1)
        self.assertEqual(unbound["verdict"]["why"], "current")
        self.assertEqual(unbound["rejection"]["dispatch"], "item-2")
        self.assertNotIn("history", unbound)
        self.assertNotIn("attempts", unbound)

    def test_a_new_owner_segment_does_not_escalate_on_the_first_repair(self) -> None:
        self.open_task()
        self.reject(why="one", evidence="receipt-1", dispositions={"item-1": "repair"})
        self.reopen()
        self.reject(why="two", evidence="receipt-2", dispositions={"item-2": "repair"})
        self.assertEqual(self.rejection()["count"], 2)
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"preset": "elite-b"}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "a preset rename is not a handoff")
        self.assertEqual(self.rejection()["owner"], "worker-a")
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate",
                                     {"dispositions": {"item-1": "handed-off"}}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "handed-off without a new dispatch does not reset")
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"dispatch": ["item-1", "item-8"]},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "a new dispatch id without handed-off does not reset")
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate",
                                     {"preset": "elite-b", "dispatch": ["item-1", "item-8", "item-9"],
                                      "dispositions": {"item-2": "handed-off"}},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        stored = self.rejection()
        self.assertNotIn("count", stored)
        self.assertNotEqual(stored.get("count"), 0)
        self.assertEqual(stored["owner"], "elite-b")
        self.reopen()
        first = self.reject(why="elite first delivery", evidence="receipt-9",
                            dispositions={"item-9": "repair"})
        self.assertEqual(first["rejection"]["count"], 1)
        self.assertEqual(first["rejection"]["owner"], "elite-b")
        shown = self.view("host")["tasks"][0]["rejection"]
        self.assertEqual(shown["escalation"], "same-assignment")
        self.assertEqual(self.view("delegator")["doing"][0]["rejection"]["escalation"], "same-assignment")

    def test_renames_acceptance_edits_and_internal_work_do_not_count(self) -> None:
        self.open_task(session="shell-1", candidate="package-a")
        self.reject(why="one", evidence="receipt-1")
        self.reopen()
        self.reject(why="two", evidence="receipt-2")
        self.assertEqual(self.rejection()["count"], 2)
        rev = str(self.task()["rev"])
        code, out, err = self.update(
            "host", "tasks", "gate",
            {"acceptance": "also check the hash", "goal": "ship the parser, renamed",
             "candidate": "package-b", "session": "shell-2", "preset": "worker-a"},
            "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2)
        self.assertEqual(self.rejection()["owner"], "worker-a")
        rev = str(self.task()["rev"])
        code, out, err = self.update("sideagent", "tasks", "gate",
                                     {"stage": "doing", "evidence": "red test in the worker loop",
                                      "next": "wip consult"},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "a worker-internal red or consult is not a submission")
        code, out, err = self.update("sideagent", "alerts", "stall",
                                     {"level": "watch", "summary": "connection wait"})
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "a stall is not an attempt")
        for value in ("partial", "accepted", "cancelled"):
            rev = str(self.task()["rev"])
            code, out, err = self.update("host", "tasks", "gate", {"verdict": {"value": value}},
                                         "--expect-rev", rev)
            self.assertEqual(code, 0, (out, err))
            self.assertEqual(self.rejection()["count"], 2, value)

    def test_a_raised_effort_starts_a_segment_and_other_effort_writes_do_not(self) -> None:
        self.open_task()
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"effort": "high"}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["effort"], "high")
        self.assertNotIn("count", self.rejection())
        self.assertNotIn("effort", self.task())
        self.reject(why="one")
        self.reopen()
        self.reject(why="two")
        self.assertEqual(self.rejection()["count"], 2)
        for effort in ("high", "medium", "ultra"):
            rev = str(self.task()["rev"])
            code, out, err = self.update("host", "tasks", "gate", {"effort": effort}, "--expect-rev", rev)
            self.assertEqual(code, 0, (out, err))
            self.assertEqual(self.rejection()["count"], 2, effort)
            self.assertEqual(self.rejection()["effort"], "high")
        rev = str(self.task()["rev"])
        code, out, err = self.update("sideagent", "tasks", "gate", {"effort": "xhigh"}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "a Sideagent does not raise effort")
        self.assertEqual(self.rejection()["effort"], "high")
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"effort": "xhigh"}, "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertNotIn("count", self.rejection())
        self.assertEqual(self.rejection()["effort"], "xhigh")
        self.reopen()
        self.reject(why="after the raise")
        self.assertEqual(self.rejection()["count"], 1)
        self.assertEqual(self.view("host")["tasks"][0]["rejection"]["escalation"], "same-assignment")

    def test_roles_cannot_write_the_count_or_judge(self) -> None:
        self.open_task()
        code, out, err = self.update("delegator", "tasks", "gate", {"stage": "doing"})
        self.assertEqual(out["reason"], "writer-refused", err)
        self.assertEqual(code, 2)
        rev = str(self.task()["rev"])
        code, out, err = self.update("sideagent", "tasks", "gate", {"verdict": {"value": "repair", "why": "mine"}},
                                     "--expect-rev", rev)
        self.assertEqual((code, out["reason"]), (2, "host-turn-required"), err)
        self.assertNotIn("count", self.task().get("rejection") or {})
        code, out, err = self.update("host", "tasks", "gate", {"rejection": {"count": 9}}, "--expect-rev", rev)
        self.assertEqual(out["reason"], "invalid-input", err)
        self.assertIn("rejection is kept by the tool", out["detail"])
        self.assertNotIn("count", self.task().get("rejection") or {})
        code, out, err = self.update("host", "tasks", "gate", {"prior_verdict": {"value": "repair"}},
                                     "--expect-rev", rev)
        self.assertEqual(out["reason"], "invalid-input")

    def test_attention_changes_once_when_the_count_or_the_recovery_changes(self) -> None:
        self.open_task()
        quiet_before = self.fingerprint()
        self.reject(why="one", evidence="receipt-1")
        once = self.fingerprint()
        self.assertNotEqual(once, quiet_before)
        self.reject(why="same submission, rewritten", evidence="receipt-1")
        self.assertEqual(self.fingerprint(), once, "a replay does not wake again")
        self.assertEqual(self.rejection()["count"], 1)
        self.reopen()
        self.reject(why="two", evidence="receipt-2")
        twice = self.fingerprint()
        self.assertNotEqual(twice, once)
        self.assertEqual(self.rejection()["count"], 2)
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"next": "hand to an authorized elite"},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        recovered = self.fingerprint()
        self.assertNotEqual(recovered, twice)
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {}, "--expect-rev", rev)
        self.assertEqual((code, self.fingerprint()), (0, recovered))
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"resume_when": "an authorized elite is free"},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        held = self.fingerprint()
        self.assertNotEqual(held, recovered)
        self.assertEqual(self.view("host")["tasks"][0]["rejection"]["escalation"], "held")
        self.assertEqual(self.view("delegator")["doing"][0]["rejection"]["escalation"], "held")
        rev = str(self.task()["rev"])
        self.update("host", "tasks", "gate", {}, "--expect-rev", rev)
        self.assertEqual(self.fingerprint(), held)

    def test_a_matching_hold_is_held_and_an_absent_count_is_not_zero(self) -> None:
        self.open_task("bare", stage="doing")
        bare = next(row for row in self.view("delegator")["doing"] if row["id"] == "bare")
        self.assertNotIn("rejection", bare)
        self.assertNotIn("rejection", next(row for row in self.view("host")["tasks"] if row["id"] == "bare"))
        self.open_task()
        self.reject(why="one")
        self.reopen()
        self.reject(why="two")
        code, out, err = self.update("host", "holds", "no-seat",
                                     {"scope": "gate", "reason": "no authorized seat",
                                      "resume_when": "a seat is granted"})
        self.assertEqual(code, 0, (out, err))
        host_gate = next(row for row in self.view("host")["tasks"] if row["id"] == "gate")
        self.assertEqual(host_gate["rejection"]["escalation"], "held")
        delegator = self.view("delegator")
        brief = next(row for row in delegator["doing"] if row["id"] == "gate")
        self.assertEqual(brief["rejection"]["escalation"], "held")
        self.assertEqual(delegator["special"]["holds"][0]["id"], "no-seat")
        self.assertNotIn('"count": 0', json.dumps(self.task()["rejection"]))
        self.assertNotIn("unknown", self.task()["rejection"].values())

    def test_original_evidence_stays_in_git_and_on_the_task(self) -> None:
        notes = self.repo / "notes.txt"
        notes.write_text("receipt-1\n", encoding="utf-8")
        git = ["git", "-C", str(self.repo), "-c", "user.email=test@example.com", "-c", "user.name=test"]
        subprocess.run(["git", "-C", str(self.repo), "init"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "notes.txt"], check=True, capture_output=True, text=True)
        subprocess.run([*git, "commit", "-m", "keep the receipt"], check=True, capture_output=True, text=True)
        head = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.open_task()
        self.reject(why="one", evidence="receipt-1")
        self.reopen()
        self.assertEqual(self.task()["prior_verdict"]["value"], "repair")
        self.assertEqual(self.task()["evidence"], "receipt-1")
        self.reject(why="two")
        self.assertEqual(self.task()["evidence"], "receipt-1")
        self.assertEqual(self.task()["prior_verdict"]["value"], "repair")
        self.assertNotIn("history", self.task())
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate",
                                     {"stage": "done", "verdict": {"value": "accepted"}, "dispatch": None},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        rev = str(self.task()["rev"])
        code, out, err = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "close",
                                    "--kind", "tasks", "--id", "gate", "--expect-rev", rev, "--evidence", "commit kept",
                                    "--cite", json.dumps({"path": "notes.txt", "commit": head}))
        self.assertEqual(code, 0, (out, err))
        self.assertNotIn("gate", self.doc()["state"]["tasks"])
        # Closed current-only contract (#259): a handled row leaves atomically;
        # no tombstone list is kept beyond seats/dispatch it still names.
        state_text = json.dumps(self.doc()["state"])
        self.assertNotIn('"rejection"', state_text)
        self.assertNotIn('"history"', state_text)
        self.assertEqual(notes.read_text(encoding="utf-8"), "receipt-1\n")
        self.assertEqual(subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                                                 text=True).strip(), head)
        self.assertFalse(any(path.suffix == ".jsonl" for path in self.repo.rglob("*")))
        self.assertFalse((self.repo / "kaola-workflow").exists())

    def test_an_older_writer_preserves_the_count_and_does_not_refuse(self) -> None:
        legacy_path = Path(self.tmp.name) / "legacy-dispatch.py"
        show = subprocess.run(["git", "-C", str(REPO), "show", f"{LEGACY_COMMIT}:scripts/kaola-dispatch.py"],
                              check=True, capture_output=True)
        legacy_path.write_bytes(show.stdout)
        self.open_task()
        self.reject(why="one", review=1, evidence="receipt-1")
        self.reject(why="two", review=2, evidence="receipt-2")
        self.assertEqual(self.rejection()["count"], 2)
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"next": "still owed"}, "--expect-rev", rev,
                                     script=legacy_path)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2)
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate",
                                     {"verdict": {"value": "repair", "why": "legacy writer"}},
                                     "--expect-rev", rev, script=legacy_path)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 2, "the older writer does not increment or zero the count")
        self.assertEqual(self.doc()["schema"], "kaola-heartbeat-prompt/2")
        self.reopen()
        self.reject(why="three", review=3, evidence="receipt-3")
        self.assertEqual(self.rejection()["count"], 3)

    def test_a_closed_contract_writer_without_the_allowlist_refuses(self) -> None:
        """Root-demanded mixed-version proof: the issue-264-line CLOSED writer
        (94f62785, unknown_record_keys enforced, no `rejection` in TASK_KEYS)
        refuses a task row carrying the rejection object instead of silently
        dropping it; recovery is this writer's allowlist, carried in the same
        change. Open-writer preservation above is NOT the compatibility proof."""
        closed_dir = Path(self.tmp.name) / "closed-writer"
        closed_dir.mkdir()
        for name in ("kaola-dispatch.py", "kaola-record-contract.py"):
            show = subprocess.run(["git", "-C", str(REPO), "show",
                                   f"94f6278523cca13c120264eaae7b77ee79dcae0c:scripts/{name}"],
                                  check=True, capture_output=True)
            (closed_dir / name).write_bytes(show.stdout)
        closed_path = closed_dir / "kaola-dispatch.py"
        self.open_task()
        self.reject(why="one", review=1, evidence="receipt-1")
        self.assertEqual(self.rejection()["count"], 1)
        before = self.file.read_bytes()
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"next": "older closed writer"},
                                     "--expect-rev", rev, script=closed_path)
        self.assertEqual(code, 2, (out, err))
        self.assertIn("rejection", out["detail"])
        self.assertEqual(self.file.read_bytes(), before, "the refusal wrote nothing")
        rev = str(self.task()["rev"])
        code, out, err = self.update("host", "tasks", "gate", {"next": "recovered by the new writer"},
                                     "--expect-rev", rev)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(self.rejection()["count"], 1)

    def test_policy_text_replaces_the_conflicting_sentences(self) -> None:
        failure = (REPO / "templates" / "orchestrator" / "references" / "task-failure.md").read_text(encoding="utf-8")
        skill = (REPO / "templates" / "orchestrator" / "SKILL.md.tmpl").read_text(encoding="utf-8")
        inquiry = (REPO / "templates" / "kaola-delegator" / "references" / "inquiry-report.md").read_text(
            encoding="utf-8")
        delegator = (REPO / "templates" / "kaola-delegator" / "SKILL.md.tmpl").read_text(encoding="utf-8")
        self.assertNotIn("There is no fixed retry count", failure)
        self.assertNotIn("whose repair is still that assignment", failure)
        self.assertIn("second Host `repair` verdict", failure)
        self.assertIn("does not dispatch or name a seat", failure)
        self.assertIn("does not judge", failure)
        self.assertIn("A green self-test does not erase a `repair`", failure)
        old = "a rejected delivery's repair is the same assignment unless substantive (task-failure)"
        new = "same assignment for one repair; a second Host repair verdict escalates (task-failure)"
        self.assertNotIn(old, skill)
        self.assertIn(new, skill)
        self.assertEqual(len(old.encode()), len(new.encode()), "the generated Skill has no spare bytes")
        self.assertIn("Name no seat and do not dispatch", inquiry)
        self.assertIn("Absent count is unknown, never zero", inquiry)
        self.assertIn("Do not dispatch workers", delegator)
        self.assertLessEqual(len(failure.encode()), 8192)
        self.assertLessEqual(len(inquiry.encode()), 8192)


if __name__ == "__main__":
    unittest.main()
