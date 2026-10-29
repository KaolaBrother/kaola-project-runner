#!/usr/bin/env python3
"""Issue #426: retire accepted-done rows whose seats are not on the task.

Legacy rows name dispatch item ids only. The session, holder, and preset
live on the supplied kaola-dispatch-index/1 item. Four shapes:

- (A) --stop-evidence binds to that item's session.
- (B) archived-ledger reads the item's holder or preset.
- (C) a terminal collect (outcome stopped, or mutation accepted/completed)
  settles when the session is absent from --live or stopped under its holder.
- (D) refs that never entered an index settle from one committed archive
  whose every line is terminal, without a session name on the ledger.

Neighboring refusals stay refusals. ledger_problem is unchanged.
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
AUTH = {"grants": [{"id": "dsh/default", "state": "granted", "count": 1}]}
CITE = {"path": "README.md", "locator": "README.md"}
SEAT = "dsh-KT-i426-review"
OTHER = "dsh-KT-i426-other"
HOLDER = "holder-426"
PRESET = "dsh/default"
ITEM = "i426-review"
STALE_KEY = "stale-collect-session-gone"

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


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i426-")
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

    def accepted(self, patch: dict, ident: str = "t1") -> int:
        body = {"stage": "done", "goal": "deliver", "verdict": {"value": "accepted"}}
        body.update(patch)
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
        row = {
            "item_id": ITEM, "task_id": "t1", "status": "unknown",
            "reason": "fingerprint-differs", "acceptance": "pending",
            "session": SEAT, "holder_instance_id": HOLDER, "preset": PRESET,
            "platform": "dsh", "repo": str(self.repo),
            "evidence": {"collect_status": {
                "outcome": "stopped", "mutation_status": "completed",
                "holder_instance_id": HOLDER, "repo": str(self.repo),
                "session": SEAT,
            }},
        }
        row.update(overrides)
        return row

    def stop_block(self, holder: str = HOLDER, observed_at: str = "2020-01-01T00:00:00Z") -> dict:
        return {"stopped": True, "residual_pids": [], "holder_instance_id": holder,
                "session": SEAT, "observed_at": observed_at}

    def git_init(self) -> None:
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.git_env = {**os.environ, **env}
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True, env=self.git_env)

    def git_commit(self, message: str, paths: list[str], when: str | None = None) -> str:
        env = dict(self.git_env)
        if when:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
        subprocess.run(["git", "-C", str(self.repo), "add", "--", *paths], check=True, env=env)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", message],
                       check=True, env=env)
        out = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                             check=True, capture_output=True, text=True, env=env)
        return out.stdout.strip()

    def write_ledger(self, lines: list[dict], folder: str = "issue-426") -> str:
        rel = f"kaola-workflow/archive/{folder}/mission-ledger.jsonl"
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
        return rel

    def stayed(self, before_state: bytes, before_index: bytes) -> None:
        self.assertEqual(self.file.read_bytes(), before_state)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertIn("t1", self.doc()["state"]["tasks"])


class SeatFallback(Fixture):
    """(A) a task that names no seat binds --stop-evidence to the index item."""

    def evidence(self, session: str = SEAT, item_id: str = ITEM) -> str:
        return json.dumps({"kind": "index-stop-receipt", "session": session,
                           "item_id": item_id, "block": "stop-1"})

    def open_item(self, **overrides) -> dict:
        row = self.item(status="unknown", reason="fingerprint-differs",
                        acceptance="accepted")
        row["evidence"] = {
            "collect_status": {"outcome": "stopped", "mutation_status": "in_progress",
                               "holder_instance_id": HOLDER, "repo": str(self.repo)},
            "stop-1": self.stop_block(),
        }
        row.update(overrides)
        return row

    def test_an_index_session_binds_stop_evidence_and_settles(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.open_item()])
        self.write_live([])
        before_index = self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "index-stop-receipt")
        self.assertEqual(receipt["session"], SEAT)
        self.assertEqual(receipt["holder_instance_id"], HOLDER)
        self.assertEqual(receipt["item_id"], ITEM)
        self.assertNotIn("reconciled_dispatch", out["value"])
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_session_on_neither_the_task_nor_the_index_names_no_seat(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.open_item()])
        self.write_live([])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence(session=OTHER))
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn(f"--stop-evidence session {OTHER} names no seat of this task", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_task_that_names_a_different_seat_refuses_the_index_session(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM], "session": OTHER})
        self.write_index([self.open_item()])
        self.write_live([])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn(f"--stop-evidence session {SEAT} names no seat of this task", out["detail"])
        self.stayed(before_state, before_index)

    def test_two_indices_for_one_ref_do_not_settle(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        row = self.open_item()
        self.write_index([row])
        second = self.repo / "index-b.json"
        self.write_index([row], path=second)
        self.write_live([])
        before_state = self.file.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index), "--index", str(second))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("more than one supplied index", out["detail"])
        self.assertEqual(self.file.read_bytes(), before_state)
        self.assertIn("t1", self.doc()["state"]["tasks"])
        code, out = self.retire("t1", rev, "--index", str(self.index), "--index", str(second),
                                "--stop-evidence", self.evidence())
        self.assertNotEqual(code, 0, out)
        self.assertIn("t1", self.doc()["state"]["tasks"])

    def test_a_wrong_holder_stop_receipt_still_refuses(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.open_item(evidence={
            "collect_status": {"outcome": "stopped", "mutation_status": "in_progress",
                               "holder_instance_id": HOLDER},
            "stop-1": self.stop_block(holder="holder-other"),
        })])
        self.write_live([])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("holder", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_closed_item_whose_session_is_still_live_stays_open(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.item(status="returned", acceptance="accepted",
                                    evidence={"stop-1": self.stop_block()})])
        self.write_live([{"session": SEAT, "state": "ready", "platform": "dsh",
                          "repo": str(self.repo), "holder_instance_id": HOLDER}])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{SEAT} is still live", out["detail"])
        self.stayed(before_state, before_index)


class ArchivedLedgerIndexSeat(Fixture):
    """(B) archived-ledger takes the holder or preset the index item recorded."""

    def archive(self, details: str, when: str = "2020-01-01T00:00:00Z",
                status: str = "done") -> tuple[str, str]:
        self.git_init()
        rel = self.write_ledger([{"n": 1, "name": "deliver", "details": details,
                                  "status": status}])
        commit = self.git_commit("archive", [rel], when=when)
        return rel, commit

    def evidence(self, commit: str, path: str) -> str:
        return json.dumps({"kind": "archived-ledger", "session": SEAT,
                           "path": path, "commit": commit})

    def test_an_index_holder_settles_when_the_task_records_neither(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.item(status="returned", acceptance="accepted",
                                    evidence={})])
        self.write_live([])
        rel, commit = self.archive(f"{SEAT} {HOLDER} returned")
        before_index = self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence(commit, rel))
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "archived-ledger")
        self.assertEqual(receipt["session"], SEAT)
        self.assertEqual(receipt["holder_instance_id"], HOLDER)
        self.assertEqual(receipt["line"], 1)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_selection_preset_settles_when_the_item_has_no_holder(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        row = self.item(status="returned", acceptance="accepted", evidence={})
        row.pop("holder_instance_id")
        row.pop("preset")
        row["selection"] = {"preset": None, "requested": {"preset": PRESET}}
        self.write_index([row])
        self.write_live([])
        rel, commit = self.archive(f"{SEAT} {PRESET} returned")
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence(commit, rel))
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "archived-ledger")
        self.assertNotIn("holder_instance_id", receipt)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_neither_holder_nor_preset_still_refuses(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        row = self.item(status="returned", acceptance="accepted", evidence={})
        row.pop("holder_instance_id")
        row.pop("preset")
        self.write_index([row])
        self.write_live([])
        rel, commit = self.archive(f"{SEAT} returned")
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence(commit, rel))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("archived-ledger needs a recorded holder or a platform/tier preset",
                      out["detail"])
        self.stayed(before_state, before_index)

    def test_a_ledger_that_does_not_name_the_session_still_refuses(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.item(status="returned", acceptance="accepted", evidence={})])
        self.write_live([])
        rel, commit = self.archive("dispatched: self — done")
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence(commit, rel))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("no ledger line names this session", out["detail"])
        self.stayed(before_state, before_index)


class CollectTerminal(Fixture):
    """(C) a finished collect settles when the session is gone or stopped."""

    def ready(self, **overrides) -> tuple[int, bytes]:
        self.init()
        patch = {"dispatch": [ITEM]}
        patch.update(overrides.pop("task", {}))
        rev = self.accepted(patch)
        self.write_index([self.item(**overrides)])
        self.write_live([])
        return rev, self.index.read_bytes()

    def test_an_absent_session_with_a_finished_collect_settles(self) -> None:
        rev, before_index = self.ready()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], "collect-terminal")
        self.assertEqual(entry["item_id"], ITEM)
        self.assertEqual(entry["session"], SEAT)
        self.assertEqual(entry["holder_instance_id"], HOLDER)
        self.assertEqual(entry["collect_status"], "terminal")
        self.assertEqual(entry["collected"], {"outcome": "stopped", "mutation_status": "completed"})
        self.assertEqual(entry["live"], "absent")
        self.assertEqual(entry["disposition"], "accepted")
        self.assertEqual(entry["evidence"], "original close-out evidence")
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_stopped_live_row_without_a_disposition_settles(self) -> None:
        rev, before_index = self.ready()
        self.write_live([{"session": SEAT, "state": "stopped", "platform": "dsh",
                          "repo": str(self.repo), "holder_instance_id": HOLDER}])
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], "collect-terminal")
        self.assertEqual(entry["live"], "stopped")
        self.assertEqual(entry["collected"]["mutation_status"], "completed")
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_live_session_row_is_not_settled(self) -> None:
        rev, before_index = self.ready()
        self.write_live([{"session": SEAT, "state": "ready", "platform": "dsh",
                          "repo": str(self.repo), "holder_instance_id": HOLDER}])
        before_state = self.file.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("collect-terminal", out["detail"])
        self.assertIn("still live", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_stop_under_another_holder_refuses(self) -> None:
        rev, before_index = self.ready()
        self.write_live([{"session": SEAT, "state": "stopped", "platform": "dsh",
                          "repo": str(self.repo), "holder_instance_id": "holder-other"}])
        before_state = self.file.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("foreign holder", out["detail"])
        self.assertIn("holder-other", out["detail"])
        self.stayed(before_state, before_index)

    def test_an_in_progress_mutation_still_refuses(self) -> None:
        rev, before_index = self.ready()
        row = self.item()
        row["evidence"]["collect_status"]["mutation_status"] = "in_progress"
        self.write_index([row])
        before_index = self.index.read_bytes()
        before_state = self.file.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{ITEM} is unknown", out["detail"])
        self.assertNotIn("collect-terminal", out["detail"])
        self.stayed(before_state, before_index)

    def test_an_absent_outcome_stays_on_the_stale_collect_route(self) -> None:
        rev, _before = self.ready()
        row = self.item()
        row["evidence"]["collect_status"]["outcome"] = None
        row["evidence"]["collect_status"]["mutation_status"] = "accepted"
        self.write_index([row])
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], STALE_KEY)
        self.assertNotEqual(entry["route"], "collect-terminal")
        self.assertEqual(entry["collect_status"], "unknown")

    def test_an_in_flight_row_stays_open(self) -> None:
        rev, _before = self.ready()
        self.write_index([self.item(status="in-flight")])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{ITEM} is in-flight", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_live_row_without_a_repo_does_not_settle(self) -> None:
        rev, _before = self.ready()
        self.write_index([self.item()])
        self.write_live([{"session": SEAT, "state": "stopped", "platform": "dsh",
                          "holder_instance_id": HOLDER}])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{ITEM} is unknown", out["detail"])
        self.assertNotIn("collect-terminal", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_foreign_collected_holder_does_not_settle(self) -> None:
        rev, _before = self.ready()
        row = self.item()
        row["evidence"]["collect_status"]["holder_instance_id"] = "holder-other"
        self.write_index([row])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{ITEM} is unknown", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_disposition_that_is_not_accepted_does_not_settle(self) -> None:
        self.init()
        rev = self.accepted({"dispatch": [ITEM], "dispositions": {ITEM: "superseded"}})
        self.write_index([self.item()])
        self.write_live([])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{ITEM} is unknown", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_sideagent_writer_does_not_get_this_route(self) -> None:
        rev, before_index = self.ready()
        before_state = self.file.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index), writer="sideagent")
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertNotIn("collect-terminal", out["detail"])
        self.stayed(before_state, before_index)


class RefsUnindexed(Fixture):
    """(D) refs that never entered an index settle from a committed archive."""

    REFS = ["i426-fix", "i426-probe"]

    def citation(self, commit: str, path: str) -> str:
        return json.dumps({"kind": "refs-unindexed", "path": path, "commit": commit})

    def mission(self, status: str = "done") -> dict:
        return {"n": 1, "name": "deliver", "details": "dispatched: self — done",
                "status": status}

    def test_a_committed_archive_settles_refs_the_index_never_held(self) -> None:
        self.init()
        self.git_init()
        rev = self.accepted({"dispatch": self.REFS, "evidence": "original close"})
        self.write_index([{"item_id": "unrelated", "task_id": "other", "status": "returned",
                           "acceptance": "accepted"}])
        self.write_live([{"session": "dsh-KT-still-running", "state": "ready",
                          "platform": "dsh", "repo": str(self.repo),
                          "holder_instance_id": "holder-live"}])
        rel = self.write_ledger([self.mission(),
                                 {"n": 2, "name": "review",
                                  "details": "dispatched: self — review", "status": "failed"}])
        commit = self.git_commit("archive", [rel])
        before_index = self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.citation(commit, rel))
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "refs-unindexed")
        self.assertEqual(receipt["shape"], "refs-unindexed")
        self.assertEqual(receipt["refs"], self.REFS)
        self.assertEqual(receipt["live"], "not-used")
        self.assertEqual(receipt["path"], rel)
        self.assertEqual(receipt["commit"], commit)
        self.assertNotIn("session", receipt)
        self.assertEqual(self.index.read_bytes(), before_index)
        stored = self.index.read_text(encoding="utf-8")
        for ref in self.REFS:
            self.assertNotIn(ref, stored)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_non_terminal_ledger_line_refuses(self) -> None:
        self.init()
        self.git_init()
        rev = self.accepted({"dispatch": self.REFS})
        self.write_index([])
        self.write_live([])
        rel = self.write_ledger([self.mission(status="in-flight")])
        commit = self.git_commit("archive", [rel])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.citation(commit, rel))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("done, failed, or a handed-over blocked", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_commit_that_lacks_the_path_refuses(self) -> None:
        self.init()
        self.git_init()
        readme = self.git_commit("readme", ["README.md"])
        rev = self.accepted({"dispatch": self.REFS})
        self.write_index([])
        self.write_live([])
        rel = self.write_ledger([self.mission()])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.citation(readme, rel))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("does not contain that ledger path", out["detail"])
        self.stayed(before_state, before_index)

    def test_direct_dispatch_still_refuses_while_dispatch_refs_exist(self) -> None:
        self.init()
        rev = self.accepted({
            "dispatch": ["never-indexed"],
            "sessions": [{"session": SEAT, "preset": PRESET}],
            "evidence": f"accepted: {SEAT} delivered",
        })
        self.write_index([])
        self.write_live([])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire(
            "t1", rev, "--index", str(self.index),
            "--stop-evidence", json.dumps({"kind": "direct-dispatch", "session": SEAT}))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("still has dispatch refs", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_ref_the_index_already_holds_is_not_an_archive_proof(self) -> None:
        self.init()
        self.git_init()
        rev = self.accepted({"dispatch": [ITEM]})
        self.write_index([self.item(status="returned", acceptance="accepted", evidence={})])
        self.write_live([])
        rel = self.write_ledger([self.mission()])
        commit = self.git_commit("archive", [rel])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.citation(commit, rel))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("refs-unindexed applies only when every dispatch ref is absent",
                      out["detail"])
        self.stayed(before_state, before_index)
        self.assertNotIn("i426-fabricated", self.index.read_text(encoding="utf-8"))

    def test_two_citations_refuse(self) -> None:
        self.init()
        self.git_init()
        rev = self.accepted({"dispatch": self.REFS})
        self.write_index([])
        self.write_live([])
        rel = self.write_ledger([self.mission()])
        commit = self.git_commit("archive", [rel])
        cite = self.citation(commit, rel)
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", cite, "--stop-evidence", cite)
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("refs-unindexed takes one archive citation", out["detail"])
        self.stayed(before_state, before_index)

    def test_a_task_that_is_not_accepted_done_refuses(self) -> None:
        self.init()
        self.git_init()
        rev = self.add_task("t1", {"stage": "done", "goal": "deliver",
                                   "verdict": {"value": "cancelled"}, "dispatch": self.REFS})
        self.write_index([])
        self.write_live([])
        rel = self.write_ledger([self.mission()])
        commit = self.git_commit("archive", [rel])
        before_state, before_index = self.file.read_bytes(), self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.citation(commit, rel))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("refs-unindexed settles only an accepted-done task", out["detail"])
        self.stayed(before_state, before_index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
