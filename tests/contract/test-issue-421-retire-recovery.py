#!/usr/bin/env python3
"""Issue #421: retire schema compat, durable stop evidence, failed-binding recovery.

- (b) `state retire` reads a KPM dispatch index (`kpm.dispatch-index/1.x`,
  identified by `project.canonical_root`) beside `kaola-dispatch-index/1`, with
  `<task_id>/<id>` refs and the KPM closed set. The mirror never writes it.
- (c/d/e) `--stop-evidence` settles a task-named seat absent from `--live`:
  `index-stop-receipt` (a pre-reboot recorded stop), `archived-ledger` (a
  committed pre-reboot ledger line), `direct-dispatch` (no dispatch refs, no
  recorded holder, Host-acceptance evidence), `sweep-purge` (the recorded
  `maintenance.last_sweep.removed` id). Every route is Host-only and needs an
  accepted-done task.
- (a) `state ensure-sideagent --recover-failed` rebinds a failed binding once
  the old node is shown gone and no hold or decision holds it; `state check`
  reports `sideagent-failed`.
"""
from __future__ import annotations

import hashlib
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
AUTH = {"grants": [{"id": "zcode/default", "state": "granted", "count": 1}]}
CITE = {"path": "README.md", "locator": "README.md"}
SEAT = "zcode-KT-i421-seat"
HINT = '--stop-evidence {"kind": "index-stop-receipt"|"archived-ledger"|"sweep-purge"|"direct-dispatch"'

for _name in CALLER_ENV:
    os.environ.pop(_name, None)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


dispatch_module = load("kaola_dispatch_421", SCRIPT)


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
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i421-")
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

    def write_live(self, rows: list[dict]) -> None:
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}),
                             encoding="utf-8")

    def write_index(self, doc: dict) -> None:
        self.index.write_text(json.dumps(doc), encoding="utf-8")

    def retire(self, ident: str, rev: int, *extra: str,
               writer: str = "host") -> tuple[int, dict]:
        return self.state("retire", "--file", str(self.file), "--writer", writer,
                          "--source", "original result", "--kind", "tasks",
                          "--id", ident, "--expect-rev", str(rev),
                          "--evidence", "original close-out evidence",
                          "--cite", json.dumps(CITE),
                          "--live", str(self.live), *extra, env=self.env)

    def ensure(self, *extra: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        return self.state("ensure-sideagent", "--file", str(self.file),
                          "--repo", str(self.repo), *extra, env=env)

    def host_env(self, role: str = "host", session: str = "zcode-KT-orchestrator-main",
                 holder: str = "host-421") -> dict[str, str]:
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        root = Path(self.tmp.name) / "records"
        directory = root / "zcode" / session / digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "record.json").write_text(json.dumps({
            "session_role": role, "holder_instance_id": holder, "holder_pid": os.getpid(),
            "holder_features": ["heartbeat-state/2", "sideagent-node/1"],
            "platform": "zcode", "session": session, "repo": str(self.repo),
        }), encoding="utf-8")
        env = dict(self.env)
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": holder,
                                                  "platform": "zcode",
                                                  "repo": str(self.repo), "session": session})
        return env

    def failed_binding(self, session: str = "zcode-KT-sideagent-old") -> None:
        doc = self.doc()
        doc["state"]["sideagent"] = {"platform": "zcode", "session": session,
                                     "preset": "zcode/default", "state": "failed",
                                     "mode": "node", "source": "default-bind",
                                     "since": "2026-10-22T00:00:00+00:00"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")

    def stop_live(self, session: str = SEAT, holder: str = "h-1") -> None:
        self.write_live([{"session": session, "state": "stopped", "platform": "zcode",
                          "repo": str(self.repo), "holder_instance_id": holder}])


class KpmIndexCompat(Fixture):
    """(b) kpm.dispatch-index/1.x reads as this project's index."""

    def kpm_index(self, schema: str = "kpm.dispatch-index/1.7", root: str | None = None,
                  items: list[tuple[str, str, str]] | None = None) -> dict:
        plans: dict[str, list[dict]] = {}
        for task_id, item_id, state in items or [("plan-1", "it-1", "returned")]:
            plans.setdefault(task_id, []).append({
                "id": item_id, "state": state, "preset": "zcode/default",
                "execution": {"holder": "h-1",
                              "start_input": {"session_name": SEAT,
                                              "task_id": task_id}}})
        return {"schema": schema, "revision": 1,
                "project": {"canonical_root": root if root is not None else str(self.repo)},
                "plans": [{"task_id": task_id, "plan_revision": 1, "items": rows}
                          for task_id, rows in plans.items()]}

    def test_a_kpm_index_closes_the_bare_unique_ref_and_is_never_written(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"}, "dispatch": ["it-1"]})
        self.write_index(self.kpm_index())
        self.stop_live()
        before = self.index.read_bytes()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.index.read_bytes(), before,
                         "the KPM index is never written by the retire mirror")
        self.assertEqual(out["index_mirror"]["skipped"],
                         "kpm.dispatch-index is written only by KPM dispatch")
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_kpm_2_and_a_foreign_root_refuse_index_unidentified(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"}, "dispatch": ["it-1"]})
        self.write_index(self.kpm_index(schema="kpm.dispatch-index/2.0"))
        self.stop_live()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "index-unidentified"), out)
        self.write_index(self.kpm_index(root="/elsewhere/project"))
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "index-unidentified"), out)

    def test_a_bare_id_in_two_plans_is_ambiguous_and_the_full_form_resolves(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"}, "dispatch": ["dup"]})
        self.write_index(self.kpm_index(items=[("plan-a", "dup", "returned"),
                                               ("plan-b", "dup", "returned")]))
        self.stop_live()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("ambiguous", out["detail"])
        self.assertIn("plan-a/dup", out["detail"])
        doc = self.doc()
        doc["state"]["tasks"]["t1"]["dispatch"] = ["plan-a/dup"]
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        rev = doc["state"]["tasks"]["t1"]["rev"]
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual(code, 0, out)

    def test_an_in_flight_kpm_item_stays_open(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"}, "dispatch": ["it-1"]})
        self.write_index(self.kpm_index(items=[("plan-1", "it-1", "in-flight")]))
        self.stop_live()
        code, out = self.retire("t1", rev, "--index", str(self.index))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("it-1 is in-flight", out["detail"])


class IndexStopReceipt(Fixture):
    """(c1) a pre-reboot recorded exact-stop receipt settles the absent seat."""

    def build(self, observed_at: str = "2020-01-01T00:00:00Z",
              residual: list | None = None, holder: str = "h-1",
              task_id: str = "t1") -> int:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"},
                                   "session": SEAT, "holder_instance_id": "h-1",
                                   "preset": "zcode/default"})
        self.write_index({"schema": "kaola-dispatch-index/1", "repo": str(self.repo),
                          "items": [{"item_id": "it-1", "task_id": task_id,
                                     "preset": "zcode/default", "session": SEAT,
                                     "status": "returned", "platform": "zcode",
                                     "holder_instance_id": "h-1",
                                     "repo": str(self.repo),
                                     "evidence": {"stop-1": {
                                         "stopped": True,
                                         "residual_pids": residual if residual is not None else [],
                                         "holder_instance_id": holder,
                                         "session": SEAT,
                                         "observed_at": observed_at}}}]})
        self.write_live([])
        return rev

    def evidence(self) -> str:
        return json.dumps({"kind": "index-stop-receipt", "session": SEAT,
                           "item_id": "it-1", "block": "stop-1"})

    def test_a_pre_reboot_recorded_stop_settles_the_seat(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "index-stop-receipt")
        self.assertEqual(receipt["observed_at"], "2020-01-01T00:00:00Z")
        self.assertEqual(receipt["holder_instance_id"], "h-1")
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_post_boot_receipt_refuses(self) -> None:
        rev = self.build(observed_at="2999-01-01T00:00:00Z")
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("not pre-reboot", out["detail"])

    def test_a_receipt_with_residual_pids_refuses(self) -> None:
        rev = self.build(residual=[123])
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("residual_pids", out["detail"])

    def test_a_receipt_for_another_holder_refuses(self) -> None:
        rev = self.build(holder="h-2")
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("holder", out["detail"])

    def test_a_row_of_another_task_refuses(self) -> None:
        rev = self.build(task_id="other")
        code, out = self.retire("t1", rev, "--index", str(self.index),
                                "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("not this task's row", out["detail"])


class ArchivedLedger(Fixture):
    """(c2) a committed pre-reboot ledger naming the seat settles it."""

    def setUp(self) -> None:
        super().setUp()
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True, env={**os.environ, **env})
        self.git_env = {**os.environ, **env}
        self.commit("readme", ["README.md"])

    def commit(self, message: str, paths: list[str], when: str | None = None) -> str:
        env = dict(self.git_env)
        if when:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
        subprocess.run(["git", "-C", str(self.repo), "add", *paths], check=True, env=env)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", message],
                       check=True, env=env)
        out = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                             check=True, capture_output=True, text=True, env=env)
        return out.stdout.strip()

    def ledger(self, details: str, status: str = "done") -> str:
        path = self.repo / "kaola-workflow" / "archive" / "t" / "mission-ledger.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"n": 1, "name": "mission",
                                    "details": details, "status": status}) + "\n",
                        encoding="utf-8")
        return "kaola-workflow/archive/t/mission-ledger.jsonl"

    def build(self) -> int:
        self.init()
        return self.add_task("t1", {"stage": "done", "goal": "g",
                                    "verdict": {"value": "accepted"},
                                    "sessions": [SEAT], "preset": "zcode/default"})

    def evidence(self, commit: str, path: str = "kaola-workflow/archive/t/mission-ledger.jsonl") -> str:
        return json.dumps({"kind": "archived-ledger", "session": SEAT,
                           "path": path, "commit": commit})

    def test_a_committed_pre_reboot_ledger_settles_the_seat(self) -> None:
        rev = self.build()
        path = self.ledger(f"{SEAT} zcode/default returned")
        commit = self.commit("archive", [path], when="2020-01-01T00:00:00Z")
        self.write_live([])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence(commit, path))
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "archived-ledger")
        self.assertEqual(receipt["commit"], commit)
        self.assertEqual(receipt["line"], 1)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_commit_made_now_refuses_post_boot(self) -> None:
        rev = self.build()
        path = self.ledger(f"{SEAT} zcode/default returned")
        commit = self.commit("archive", [path])
        self.write_live([])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence(commit, path))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("not pre-reboot", out["detail"])

    def test_a_non_terminal_line_refuses(self) -> None:
        rev = self.build()
        path = self.ledger(f"{SEAT} zcode/default still running", status="in-flight")
        commit = self.commit("archive", [path], when="2020-01-01T00:00:00Z")
        self.write_live([])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence(commit, path))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("done, failed, or a handed-over blocked", out["detail"])

    def test_a_ledger_not_naming_the_session_refuses(self) -> None:
        rev = self.build()
        path = self.ledger("zcode-KT-other zcode/default returned")
        commit = self.commit("archive", [path], when="2020-01-01T00:00:00Z")
        self.write_live([])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence(commit, path))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("no ledger line names this session", out["detail"])

    def test_a_working_tree_only_file_refuses(self) -> None:
        rev = self.build()
        path = self.ledger(f"{SEAT} zcode/default returned")  # never committed
        first = subprocess.run(["git", "-C", str(self.repo), "rev-list", "--max-parents=0", "HEAD"],
                               check=True, capture_output=True, text=True,
                               env=self.git_env).stdout.strip()
        self.write_live([])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence(first, path))
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("does not contain that ledger path", out["detail"])


class DirectDispatch(Fixture):
    """(d) a directly dispatched seat needs no index row at all."""

    def build(self, **overrides) -> int:
        self.init()
        patch = {"stage": "done", "goal": "g", "verdict": {"value": "accepted"},
                 "sessions": [{"session": SEAT, "preset": "zcode/default"}],
                 "evidence": f"accepted: {SEAT} delivered"}
        patch.update(overrides)
        rev = self.add_task("t1", patch)
        self.write_live([])
        return rev

    def evidence(self) -> str:
        return json.dumps({"kind": "direct-dispatch", "session": SEAT})

    def test_a_directly_named_seat_settles(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "direct-dispatch")
        self.assertEqual(receipt["holder_instance_id"], None)
        self.assertEqual(receipt["live"], "absent")
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_a_task_with_dispatch_refs_refuses(self) -> None:
        rev = self.build(dispatch=["it-1"])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)

    def test_a_recorded_holder_refuses(self) -> None:
        rev = self.build(sessions=[{"session": SEAT, "preset": "zcode/default",
                                    "holder_instance_id": "h-1"}])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("a recorded holder is not direct dispatch", out["detail"])

    def test_evidence_not_naming_the_session_refuses(self) -> None:
        rev = self.build(evidence="accepted: some other seat delivered")
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("does not name this session", out["detail"])

    def test_a_live_seat_refuses(self) -> None:
        rev = self.build()
        self.write_live([{"session": SEAT, "state": "ready", "platform": "zcode",
                          "repo": str(self.repo), "holder_instance_id": "h-1"}])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("still live", out["detail"])


class SweepPurge(Fixture):
    """(e) the recorded sweep's removed id is report-only provenance."""

    PURGE_ID = f"session:zcode/{SEAT}@h-1"

    def build(self, removed: list[str] | None = None, holder: str | None = None) -> int:
        self.init()
        seat = {"session": SEAT}
        if holder:
            seat["holder_instance_id"] = holder
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"},
                                   "sessions": [seat], "preset": "zcode/default"})
        doc = self.doc()
        doc["state"]["maintenance"]["last_sweep"] = {
            "at": "2026-10-27T00:00:00Z", "key": "k", "batch": "b-1",
            "holder": "tool", "accepted_revision": None, "head": None,
            "removed": removed if removed is not None else [self.PURGE_ID]}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        self.write_live([])
        return rev

    def evidence(self, ident: str | None = None) -> str:
        return json.dumps({"kind": "sweep-purge", "session": SEAT,
                           "id": ident or self.PURGE_ID})

    def test_a_recorded_purge_settles_the_seat(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual(code, 0, out)
        receipt = out["value"]["stop_evidence"][0]
        self.assertEqual(receipt["route"], "sweep-purge")
        self.assertEqual(receipt["purge"]["source"], "maintenance.last_sweep")
        self.assertIsNone(receipt["stop_receipt"])
        self.assertNotIn("t1", self.doc()["state"]["tasks"])

    def test_an_unrecorded_purge_refuses(self) -> None:
        rev = self.build(removed=["session:zcode/other@h-9"])
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("not in maintenance.last_sweep.removed", out["detail"])

    def test_a_purge_holder_differing_from_the_record_refuses(self) -> None:
        rev = self.build(holder="h-2")
        code, out = self.retire("t1", rev, "--stop-evidence", self.evidence())
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("purge holder", out["detail"])


class StopEvidenceInput(Fixture):
    """Closed-shape validation and the unchanged absent-row refusal."""

    def build(self) -> int:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"},
                                   "sessions": [SEAT], "preset": "zcode/default"})
        self.write_live([])
        return rev

    def test_an_absent_row_without_evidence_refuses_as_before_with_the_hint(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev)
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn(f"{SEAT} is not in the live rows; its stop is not shown", out["detail"])
        self.assertIn(HINT, out["detail"])

    def test_free_text_and_unknown_kinds_refuse_invalid_input(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev, "--stop-evidence", "seat was stopped")
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        code, out = self.retire("t1", rev, "--stop-evidence",
                                json.dumps({"kind": "witness", "session": SEAT}))
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn("kind", out["detail"])

    def test_an_extra_key_refuses(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev, "--stop-evidence",
                                json.dumps({"kind": "direct-dispatch", "session": SEAT,
                                            "note": "extra"}))
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)

    def test_a_session_that_is_no_seat_refuses(self) -> None:
        rev = self.build()
        code, out = self.retire("t1", rev, "--stop-evidence",
                                json.dumps({"kind": "direct-dispatch",
                                            "session": "zcode-KT-other"}))
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)
        self.assertIn("names no seat of this task", out["detail"])

    def test_a_non_accepted_task_and_a_sideagent_writer_refuse(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "review", "goal": "g",
                                   "verdict": {"value": "accepted"},
                                   "sessions": [SEAT], "preset": "zcode/default"})
        self.write_live([])
        entry = json.dumps({"kind": "direct-dispatch", "session": SEAT})
        code, out = self.retire("t1", rev, "--stop-evidence", entry)
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
                               "--source", "evt", "--kind", "tasks", "--id", "t1",
                               "--expect-rev", str(self.doc()["state"]["tasks"]["t1"]["rev"]),
                               "--set", json.dumps({"stage": "done",
                                                    "verdict": {"value": "cancelled"}}),
                               env=self.env)
        self.assertEqual(code, 0, out)
        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        code, out = self.retire("t1", rev, "--stop-evidence", entry)
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("accepted-done", out["detail"])
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
                               "--source", "evt", "--kind", "tasks", "--id", "t1",
                               "--expect-rev", str(self.doc()["state"]["tasks"]["t1"]["rev"]),
                               "--set", json.dumps({"verdict": {"value": "accepted"}}),
                               env=self.env)
        self.assertEqual(code, 0, out)
        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        code, out = self.retire("t1", rev, "--stop-evidence", entry, writer="sideagent")
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("Host route", out["detail"])


class RecoverFailedSideagent(Fixture):
    """(a) a failed binding rebinds once the old node is gone and unheld."""

    OLD = "zcode-KT-sideagent-old"

    def build(self) -> None:
        self.init()
        self.failed_binding(self.OLD)
        self.write_live([])

    def test_recover_rebinds_without_touching_sweep_or_host_revision(self) -> None:
        self.build()
        doc = self.doc()
        doc["state"]["maintenance"]["last_sweep"] = {
            "at": "2026-10-27T00:00:00Z", "key": "k", "batch": "b-1",
            "holder": "tool", "accepted_revision": None, "head": None,
            "removed": ["session:zcode/other@h-9"]}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.doc()
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed rebind",
                                env=self.host_env())
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "recovered")
        self.assertEqual(out["previous"]["session"], self.OLD)
        self.assertEqual(out["previous"]["state"], "failed")
        self.assertEqual(out["sideagent"]["session"], "zcode-KT-sideagent")
        self.assertEqual(out["sideagent"]["mode"], "node")
        self.assertIn("sweep", out)
        after = self.doc()
        self.assertEqual(after["host_revision"], before["host_revision"])
        self.assertEqual(after["state"]["maintenance"]["last_sweep"],
                         before["state"]["maintenance"]["last_sweep"])
        self.assertEqual(after["state"]["sideagent"]["source"], "recover-failed")
        self.assertEqual(after["state"]["sideagent"]["state"], "active")

    def test_a_hold_naming_sideagent_refuses(self) -> None:
        self.build()
        doc = self.doc()
        doc["state"]["holds"]["h1"] = {"preset": "zcode/default", "reason": "owner",
                                       "note": "sideagent rebind question open"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed", env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "sideagent-held"), out)
        self.assertEqual(out["held_by"], ["holds/h1"])
        self.assertEqual(self.doc()["state"]["sideagent"]["state"], "failed")

    def test_a_settled_decision_naming_the_old_session_refuses(self) -> None:
        self.build()
        doc = self.doc()
        doc["state"]["decisions"]["d1"] = {"status": "settled", "owner": "host",
                                           "summary": f"{self.OLD} ended by owner",
                                           "rev": 1, "source": "turn-2",
                                           "created_at": "2026-10-01T00:00:00Z",
                                           "updated_at": "2026-10-01T00:00:00Z"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed", env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "sideagent-held"), out)
        self.assertEqual(out["held_by"], ["decisions/d1"])

    def test_a_live_old_node_refuses(self) -> None:
        self.build()
        self.write_live([{"session": self.OLD, "state": "ready", "platform": "zcode",
                          "repo": str(self.repo), "holder_instance_id": "node-1"}])
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed", env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "old-node-live"), out)

    def test_recover_requires_a_failed_binding(self) -> None:
        self.init()
        self.write_live([])
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed", env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "sideagent-not-failed"), out)
        doc = self.doc()
        doc["state"]["sideagent"] = {"platform": "zcode", "session": "zcode-KT-sideagent",
                                     "preset": "zcode/default", "state": "active",
                                     "mode": "node", "since": "2026-10-22T00:00:00+00:00"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed", env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "sideagent-not-failed"), out)

    def test_recover_requires_original_evidence_not_a_placeholder(self) -> None:
        self.build()
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "evidence-required"), out)
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "ORIGINAL_OWNER_EVIDENCE", env=self.host_env())
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), out)

    def test_a_non_host_caller_cannot_recover(self) -> None:
        self.build()
        worker = self.host_env(role="worker", session="zcode-KT-worker", holder="w-1")
        code, out = self.ensure("--recover-failed", "--live", str(self.live),
                                "--evidence", "owner confirmed", env=worker)
        self.assertEqual((code, out["reason"]), (2, "host-only"), out)
        self.assertEqual(self.doc()["state"]["sideagent"]["state"], "failed")

    def test_kept_reports_failed_with_the_recovery_command(self) -> None:
        self.build()
        code, out = self.ensure(env=self.host_env())
        self.assertEqual((code, out["result"]), (0, "kept"), out)
        self.assertEqual(out["state"], "failed")
        self.assertIn("--recover-failed", out["recovery"])
        self.assertIn("ORIGINAL_OWNER_EVIDENCE", out["recovery"])

    def test_check_reports_the_failed_binding_and_writes_nothing(self) -> None:
        self.build()
        before = self.file.read_bytes()
        code, out = self.state("check", "--file", str(self.file), "--repo", str(self.repo),
                               env=self.env)
        self.assertEqual(code, 0, out)
        found = [row for row in out["problems"] if row.get("code") == "sideagent-failed"]
        self.assertEqual(len(found), 1, out["problems"])
        self.assertEqual(found[0]["level"], "warn")
        self.assertIn("--recover-failed", found[0]["command"])
        self.assertIn("--live", found[0]["command"])
        self.assertIn("ORIGINAL_OWNER_EVIDENCE", found[0]["command"])
        self.assertEqual(found[0]["held_by"], [])
        self.assertEqual(self.file.read_bytes(), before, "state check stays read-only")


class EvidenceKeys(unittest.TestCase):
    """evidence() records the stop facts only when the receipt has `stopped`."""

    def test_a_stop_receipt_records_session_stopped_residuals_and_time(self) -> None:
        body = dispatch_module.evidence(
            {"session": "s-1", "stopped": True, "residual_pids": [],
             "holder_instance_id": "h-1"}, 0)
        self.assertEqual(body["session"], "s-1")
        self.assertIs(body["stopped"], True)
        self.assertEqual(body["residual_pids"], [])
        self.assertRegex(body["observed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_a_receipt_without_stopped_keeps_todays_keys(self) -> None:
        body = dispatch_module.evidence({"session": "s-1", "holder_instance_id": "h-1"}, 0)
        for key in ("session", "stopped", "residual_pids", "observed_at"):
            self.assertNotIn(key, body)


record_module = load("kaola_record_contract_421",
                     REPO / "scripts" / "kaola-record-contract.py")

RETURN_NEXT = ("Host: reconcile the original node and stop receipts; "
               "repair the binding; request a bounded check")


class ReturnedAlertCompaction(Fixture):
    """Issue #421 (c): maintenance-returned cannot grow one row per failure."""

    def recovery_env(self) -> dict[str, str]:
        return self.host_env()

    def fail_input(self, ident: str, evidence: str, *extra: str,
                   env: dict[str, str] | None = None) -> tuple[int, dict]:
        return self.state("recovery-input", "--file", str(self.file),
                          "--source", "carrier-maintenance-failure",
                          "--fail", "binding-or-recipe-unavailable",
                          "--input", ident, "--evidence", evidence, *extra,
                          env=env if env is not None else self.recovery_env())

    def alert(self) -> dict:
        return (self.doc()["state"].get("alerts") or {}).get("maintenance-returned") or {}

    def seed(self, inputs: dict, evidence: list | None = None,
             summary: str = "maintenance needs Host recovery from original receipts") -> None:
        doc = self.doc()
        doc["state"].setdefault("alerts", {})["maintenance-returned"] = {
            "level": "warn", "owner": "host", "summary": summary, "rev": 1,
            "inputs": inputs,
            **({"evidence": evidence} if evidence else {})}
        self.file.write_text(json.dumps(doc), encoding="utf-8")

    def test_repeated_binding_failures_coalesce_with_count(self) -> None:
        self.init()
        self.seed({"host:tasks/t9@2": {"why": "not-in-batch", "evidence": "host-ref"}},
                  evidence=["host-added-ref"])
        env = self.recovery_env()
        folded = []
        for seq in (5, 6, 7):
            code, out = self.fail_input(f"recovery#{seq}", f"/tmp/events.jsonl#{seq}",
                                        "--through-host-revision", "1", env=env)
            self.assertEqual(code, 0, out)
            folded += out.get("coalesced") or []
        self.assertEqual(folded, ["recovery#5", "recovery#6"])
        inputs = self.alert()["inputs"]
        self.assertEqual(set(inputs) - {"host:tasks/t9@2"}, {"recovery#7"})
        row = inputs["recovery#7"]
        self.assertEqual(row["count"], 3)
        self.assertEqual(row["coalesced_from"], "recovery#5")
        self.assertEqual(row["evidence"], "/tmp/events.jsonl#7")
        self.assertEqual(row["host_revision_through"], 1)
        evidence = self.alert()["evidence"]
        self.assertNotIn("/tmp/events.jsonl#5", evidence)
        self.assertNotIn("/tmp/events.jsonl#6", evidence)
        self.assertIn("/tmp/events.jsonl#7", evidence)
        self.assertIn("host-added-ref", evidence)

    def test_blow_up_shape_is_bounded(self) -> None:
        rows = {f"recovery#{seq}": {"why": "binding-or-recipe-unavailable",
                                  "next": RETURN_NEXT,
                                  "evidence": f"/tmp/events.jsonl#{seq}",
                                  "host_revision_through": seq}
                for seq in range(1, 157)}
        merged, folded = record_module.coalesce_returned_inputs(rows)
        self.assertEqual(len(folded), 155)
        self.assertEqual(set(merged), {"recovery#156"})
        self.assertEqual(merged["recovery#156"]["count"], 156)
        self.assertEqual(merged["recovery#156"]["coalesced_from"], "recovery#1")
        self.assertEqual(merged["recovery#156"]["host_revision_through"], 156)
        # A live CLI pass over the seeded 156-row alert folds one more.
        self.init()
        self.seed(rows)
        code, out = self.fail_input("recovery#157", "/tmp/events.jsonl#157")
        self.assertEqual(code, 0, out)
        inputs = self.alert()["inputs"]
        self.assertEqual(set(inputs), {"recovery#157"})
        self.assertEqual(inputs["recovery#157"]["count"], 157)
        self.assertLess(len(json.dumps(self.alert())), 4096)

    def test_unsettled_inputs_are_retained_with_evidence(self) -> None:
        self.init()
        other = {
            "recovery#40": {"why": "checkpoint-partial", "evidence": "events#40",
                            "host_revision_through": 40},
            "batch:b-1": {"why": "node-admission-failed", "evidence": "events#b1",
                          "batch": "b-1"},
            "host:tasks/t5@3": {"why": "not-in-batch", "evidence": "events#t5"},
            "host:tasks/t6@7": {"why": "stop-unconfirmed", "evidence": "events#t6"},
        }
        self.seed(other, evidence=["events#40", "events#b1", "events#t5", "events#t6",
                                   "host-added"])
        code, out = self.fail_input("recovery#8", "events#8")
        self.assertEqual(code, 0, out)
        code, out = self.fail_input("recovery#9", "events#9")
        self.assertEqual(code, 0, out)
        inputs = self.alert()["inputs"]
        for ident, row in other.items():
            self.assertEqual(inputs[ident], row, ident)
        self.assertEqual(inputs["recovery#9"]["count"], 2)
        evidence = self.alert()["evidence"]
        self.assertNotIn("events#8", evidence)
        for ref in ("events#40", "events#t5", "events#t6", "events#9", "host-added"):
            self.assertIn(ref, evidence)

    def test_compaction_never_drops_an_unsettled_input(self) -> None:
        different_next = {"recovery#2": {"why": "binding-or-recipe-unavailable",
                                        "next": "Host: a different duty",
                                        "evidence": "e2"}}
        merged, folded = record_module.coalesce_returned_inputs({
            **different_next,
            "recovery#3": {"why": "binding-or-recipe-unavailable",
                           "next": RETURN_NEXT, "evidence": "e3"},
            "recovery#4": {"why": "binding-or-recipe-unavailable",
                           "next": RETURN_NEXT, "evidence": "e4"},
            "recovery#5": {"why": "stop-unconfirmed", "next": RETURN_NEXT,
                           "evidence": "e5"},
            "recovery#6": {"why": "stop-unconfirmed", "next": RETURN_NEXT,
                           "evidence": "e6"},
            "recovery#7": {"why": "binding-or-recipe-unavailable",
                           "next": RETURN_NEXT, "evidence": "e7"},
        })
        self.assertEqual(folded, ["recovery#3", "recovery#4"])
        self.assertEqual(set(merged), {"recovery#2", "recovery#5", "recovery#6", "recovery#7"})
        self.assertEqual(merged["recovery#7"]["count"], 3)
        # A lone row gets no count; a repeated id keeps its fold.
        lone, folded = record_module.coalesce_returned_inputs(
            {"recovery#9": {"why": "binding-or-recipe-unavailable", "evidence": "e9"}})
        self.assertEqual(folded, [])
        self.assertNotIn("count", lone["recovery#9"])
        self.init()
        self.seed({"recovery#3": {"why": "binding-or-recipe-unavailable",
                                 "next": RETURN_NEXT, "count": 4,
                                 "coalesced_from": "recovery#1",
                                 "evidence": "e3"}})
        code, out = self.fail_input("recovery#3", "e3")
        self.assertEqual((code, out["result"]), (0, "unchanged"), out)
        self.assertEqual(self.alert()["inputs"]["recovery#3"]["count"], 4)

    def test_host_retire_collapses_its_settled_inputs(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"}})
        self.add_task("t2", {"stage": "doing", "goal": "g2"})
        self.seed({"host:tasks/t1@4": {"why": "not-in-batch", "evidence": "e4"},
                   "host:tasks/t1@9": {"why": "unaccounted", "evidence": "e9"},
                   "host:tasks/t2@5": {"why": "not-in-batch", "evidence": "e5"},
                   "host:tasks/t1@11": {"why": "stop-unconfirmed", "evidence": "e11"}},
                  evidence=["e4", "e9", "e5", "e11", "host-added"])
        self.write_live([])
        code, out = self.retire("t1", rev)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(out["value"]["settled_inputs"]),
                         ["host:tasks/t1@4", "host:tasks/t1@9"])
        inputs = self.alert()["inputs"]
        self.assertEqual(set(inputs), {"host:tasks/t2@5", "host:tasks/t1@11"})
        evidence = self.alert()["evidence"]
        self.assertNotIn("e4", evidence)
        self.assertNotIn("e9", evidence)
        self.assertIn("e5", evidence)
        self.assertIn("e11", evidence)
        self.assertIn("host-added", evidence)
        # Retiring the task whose remaining non-stop inputs are last deletes the alert.
        rev2 = self.doc()["state"]["tasks"]["t2"]["rev"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
                               "--source", "evt", "--kind", "tasks", "--id", "t2",
                               "--expect-rev", str(rev2),
                               "--set", json.dumps({"stage": "done",
                                                    "verdict": {"value": "accepted"}}),
                               env=self.env)
        self.assertEqual(code, 0, out)
        doc = self.doc()
        doc["state"]["alerts"]["maintenance-returned"]["inputs"] = {
            "host:tasks/t2@5": {"why": "not-in-batch", "evidence": "e5"}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.retire("t2", doc["state"]["tasks"]["t2"]["rev"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("maintenance-returned", self.doc()["state"]["alerts"])

    def test_sideagent_or_handoff_retire_does_not_collapse(self) -> None:
        self.init()
        rev = self.add_task("t1", {"stage": "done", "goal": "g",
                                   "verdict": {"value": "accepted"}})
        self.add_task("t2", {"stage": "doing", "goal": "g2"})
        inputs = {"host:tasks/t1@4": {"why": "not-in-batch", "evidence": "e4"},
                  "host:tasks/t2@5": {"why": "not-in-batch", "evidence": "e5"}}
        self.seed(inputs)
        self.write_live([])
        code, out = self.retire("t1", rev, writer="sideagent")
        self.assertEqual((code, out["reason"]), (2, "retire-unmet"), out)
        self.assertIn("still reference tasks/t1", out["detail"])
        rev = self.doc()["state"]["tasks"]["t1"]["rev"]
        code, out = self.retire("t1", rev, "--handoff", "t2")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.alert()["inputs"], inputs)

    def test_alert_row_typing(self) -> None:
        base = {"level": "warn", "owner": "host", "summary": "s",
                "inputs": {"recovery#1": {"why": "x", "evidence": "e"}}}
        for bad in ({"count": 1}, {"count": "3"}, {"coalesced_from": ""}):
            record = json.loads(json.dumps(base))
            record["inputs"]["recovery#1"].update(bad)
            self.assertIsNotNone(
                record_module.record_type_problem("alerts", record), bad)
        good = json.loads(json.dumps(base))
        good["inputs"]["recovery#1"].update({"count": 3, "coalesced_from": "recovery#0"})
        self.assertIsNone(record_module.record_type_problem("alerts", good))


if __name__ == "__main__":
    unittest.main()
