#!/usr/bin/env python3
"""Issue #397: three hard-stuck retire/migrate paths.

Pre-fix evidence (main 2330fe3e, /tmp/kpr395 and the copied i398-fix row):

- a carrier-less v2 state file that ``migrate --write`` grew past 64 KiB made
  every later ordinary write refuse ``carrier-limit`` while its recovery only
  said "retire finished records"; the retire commands ``state check`` printed
  all failed;
- a v1 ``body.alerts`` dict or list collapsed into one ``legacy-alerts``
  summary, so a later ``state retire`` named no record (``record-missing``);
- the copied i398-fix row (unknown / fingerprint-differs, collected
  ``outcome: stopped`` and ``mutation_status: unknown`` because the seat's
  follow-up turn died on a 429) was refused by the strict route (wants
  completed), the stale-collect route (wants no outcome) and the dead-holder
  route (leaves collected proof alone).

The fixed tip makes migration use the same whole-file bound as every later
write, names the live-holder migration as the local exit, maps every v1 alert
row to a retirable current row, and adds one strict reconciliation route for
the stopped/unknown collected proof. The pre-fix tree fails the three positive
cases below; that comparison is recorded in the run report.
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
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "issue-397"
ORIGIN_REPO = "/Users/ylpromax5/Workspace/kaola-project-runner-issues"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}
CITE = {"path": "README.md", "locator": "README.md"}
TARGET = "exclusion-breach-codex-default-i1687"
ROUTE = "stopped-collect incomplete-turn route"
ROUTE_KEY = "stopped-collect-incomplete-turn"
STALE_KEY = "stale-collect-session-gone"

for _name in CALLER_ENV:
    os.environ.pop(_name, None)


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        args if args[:2] == [sys.executable, str(SCRIPT)] else [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        env=env if env is not None else {k: v for k, v in os.environ.items()
                                         if not k.startswith("KAOLA_")},
        timeout=120,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def execute(command: str) -> tuple[int, dict]:
    return run(shlex.split(command))


def rewrite_repo(value, repo: str):
    if isinstance(value, dict):
        return {key: rewrite_repo(item, repo) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_repo(item, repo) for item in value]
    return repo if value == ORIGIN_REPO else value


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i397-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        self.env["KAOLA_ACP_RECORD_ROOT"] = str(Path(self.tmp.name) / "records")

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def init(self) -> None:
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1",
                         "--project", json.dumps({"code": "KT", "goal": "g", "repo": str(self.repo)}),
                         "--authorization", json.dumps(AUTH)], self.env)
        self.assertEqual(code, 0, out)

    def write_legacy(self, body: dict) -> bytes:
        self.file.write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/1", "body": json.dumps(body),
        }), encoding="utf-8")
        return self.file.read_bytes()

    def migrate(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "migrate", "--file", str(self.file), *extra], self.env)


class MigrateSizeGate(Fixture):
    """Shape 1: migration and ordinary writes share the whole-file bound."""

    def oversized_current(self) -> bytes:
        self.init()
        doc = self.doc()
        for index in range(120):
            doc["state"]["alerts"][f"filler-{index}"] = {
                "level": "watch", "summary": "s" * 300, "owner": "host", "next": "x",
                "evidence": ["e"], "inputs": {}, "rev": 1,
                "created_at": "2026-09-01T00:00:00Z", "updated_at": "2026-09-01T00:00:00Z",
                "source": "f", "writer": "host",
            }
        doc["state"]["alerts"][TARGET] = {
            "level": "warn", "summary": "target", "owner": "host", "next": "none",
            "evidence": ["e" * 1200], "inputs": {}, "rev": 1,
            "created_at": "2026-09-01T00:00:00Z", "updated_at": "2026-09-01T00:00:00Z",
            "source": "legacy", "writer": "host",
        }
        # A pre-revision row makes the migration cleanup work to do; the write
        # is where the old unchecked 1 MiB bound used to bypass the carrier.
        doc["state"]["tasks"]["pad"] = {
            "stage": "todo", "goal": "p", "rev": None, "writer": "host", "source": "s",
        }
        self.file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return self.file.read_bytes()

    def capable_live(self) -> Path:
        live = self.repo / "live.json"
        live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": [{
            "platform": "zcode", "session": "zcode-KT-orchestrator-main",
            "session_role": "host", "repo": str(self.repo), "state": "ready",
            "holder_instance_id": "host-new",
            "holder_features": ["heartbeat-state/2"],
        }]}), encoding="utf-8")
        return live

    def test_migrate_refuses_to_create_a_carrier_less_file_past_the_legacy_bound(self) -> None:
        before = self.oversized_current()
        code, out = self.migrate("--write")
        self.assertEqual((code, out["reason"]), (2, "carrier-limit"), out)
        self.assertGreater(out["sizes"]["file_bytes"], 65536)
        self.assertEqual(out["sizes"]["file_limit"], 65536)
        self.assertEqual(self.file.read_bytes(), before, "a refused write leaves the file unchanged")
        for token in ("state migrate", "--live", "LIVE_JSON", "--write",
                      "heartbeat-state/2", "owner stop"):
            self.assertIn(token, out["recovery"])
        code, check = run(["state", "check", "--file", str(self.file)], self.env)
        self.assertEqual(code, 0, check)
        limit = [row for row in check["problems"] if row.get("code") == "carrier-limit"]
        self.assertEqual(len(limit), 1, check)
        self.assertIn("state migrate", limit[0]["detail"])
        self.assertIn("--live", limit[0]["detail"])

    def test_a_capable_live_holder_is_the_local_exit_then_retire_writes(self) -> None:
        self.oversized_current()
        code, out = self.migrate("--write")
        self.assertEqual((code, out["reason"]), (2, "carrier-limit"), out)
        live = self.capable_live()
        code, out = self.migrate("--write", "--live", str(live))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "migrated")
        self.assertGreater(out["file_bytes"], 65536)
        self.assertEqual(self.doc()["carrier"]["capability"], "heartbeat-state/2")
        code, retired = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                             "--source", "evt", "--kind", "alerts", "--id", TARGET,
                             "--expect-rev", "1", "--evidence", "original handled evidence"], self.env)
        self.assertEqual(code, 0, retired)
        self.assertEqual(retired["result"], "written")
        self.assertNotIn(TARGET, self.doc()["state"]["alerts"])

    def test_a_large_v1_file_uses_the_same_bound_and_the_same_exit(self) -> None:
        body = {
            "project": {"code": "KT", "goal": "large v1"},
            "authorization": AUTH,
            "active": [{"ref": f"row-{n}", "session": f"codex-KT-i{n}-x",
                        "evidence": "e" * 900} for n in range(80)],
            "alerts": {TARGET: {"level": "warn", "summary": "handled", "owner": "host",
                                "next": "none", "evidence": ["e" * 1200]}},
        }
        before = self.write_legacy(body)
        code, out = self.migrate("--write")
        self.assertEqual((code, out["reason"]), (2, "carrier-limit"), out)
        self.assertEqual(self.file.read_bytes(), before)
        live = self.capable_live()
        code, out = self.migrate("--write", "--live", str(live))
        self.assertEqual(code, 0, out)
        self.assertIsNotNone(self.doc().get("carrier"))
        self.assertEqual(self.doc()["state"]["alerts"][TARGET]["rev"], 1)
        code, retired = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                             "--source", "evt", "--kind", "alerts", "--id", TARGET,
                             "--expect-rev", "1", "--evidence", "original handled evidence"], self.env)
        self.assertEqual(code, 0, retired)
        self.assertNotIn(TARGET, self.doc()["state"]["alerts"])


class LegacyBodyAlerts(Fixture):
    """Shape 2: every v1 body.alerts row stays nameable and retirable."""

    def test_a_v1_dict_alerts_row_maps_to_rev_one_and_retires(self) -> None:
        body = {"project": {"code": "KT", "goal": "v1"}, "authorization": AUTH,
                "alerts": {
                    TARGET: {"level": "warn", "summary": "legacy", "owner": "host",
                             "next": "none", "evidence": ["v1 evidence"]},
                    "second-row": {"level": "watch", "summary": "other", "owner": "host",
                                   "next": "none", "evidence": ["other"]},
                }}
        self.write_legacy(body)
        code, out = self.migrate("--write")
        self.assertEqual(code, 0, out)
        alerts = self.doc()["state"]["alerts"]
        self.assertEqual(set(alerts), {TARGET, "second-row"})
        self.assertEqual(alerts[TARGET]["rev"], 1)
        code, retired = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                             "--source", "evt", "--kind", "alerts", "--id", TARGET,
                             "--expect-rev", "1", "--evidence", "original handled evidence"], self.env)
        self.assertEqual(code, 0, retired)
        remaining = self.doc()["state"]["alerts"]
        self.assertEqual(set(remaining), {"second-row"})

    def test_a_v1_list_alerts_row_maps_to_rev_one_and_retires(self) -> None:
        body = {"project": {"code": "KT", "goal": "v1"}, "authorization": AUTH,
                "alerts": [{"id": TARGET, "level": "warn", "summary": "legacy",
                            "owner": "host", "next": "none", "evidence": ["v1 evidence"]}]}
        self.write_legacy(body)
        code, out = self.migrate("--write")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["alerts"][TARGET]["rev"], 1)
        code, retired = run(["state", "retire", "--file", str(self.file), "--writer", "host",
                             "--source", "evt", "--kind", "alerts", "--id", TARGET,
                             "--expect-rev", "1", "--evidence", "original handled evidence"], self.env)
        self.assertEqual(code, 0, retired)
        self.assertNotIn(TARGET, self.doc()["state"]["alerts"])

    def test_unknown_alert_fields_are_named_locators_not_a_lossy_list_summary(self) -> None:
        body = {"project": {"code": "KT", "goal": "v1"}, "authorization": AUTH,
                "alerts": {
                    "first": {"level": "warn", "summary": "legacy", "owner": "host",
                              "next": "none", "legacy_note": "keep this name"},
                    "second": {"level": "watch", "summary": "other", "owner": "host",
                               "next": "none"},
                }}
        self.write_legacy(body)
        code, out = self.migrate("--write")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertEqual(set(doc["state"]["alerts"]), {"first", "second"})
        self.assertNotIn("legacy-alerts", doc["state"]["unverified"])
        named = [row for row in doc["state"]["unverified"].values()
                 if isinstance(row, dict) and "legacy_note" in str(row.get("summary"))]
        self.assertEqual(len(named), 1, doc["state"]["unverified"])
        self.assertIn("alerts[first].legacy_note", named[0]["locator"])

    def test_a_v1_id_that_cannot_be_a_record_key_keeps_a_nameable_mapping(self) -> None:
        body = {"project": {"code": "KT", "goal": "v1"}, "authorization": AUTH,
                "alerts": [{"id": "not a record key", "level": "warn", "summary": "legacy",
                            "owner": "host", "next": "none"}]}
        self.write_legacy(body)
        code, out = self.migrate("--write")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertEqual(set(doc["state"]["alerts"]), {"alert-1"})
        legacy_id = doc["state"]["unverified"]["alert-1-legacy-id"]
        self.assertIn("alerts[0]", legacy_id["locator"])
        self.assertIn("not a record key", legacy_id["summary"])

    def test_colliding_old_alert_keys_keep_both_unknown_locators(self) -> None:
        # Two v1 keys can derive the same old locator key (a and a]); the
        # migrated alert id keys the unverified entry and both original
        # locator texts survive.
        body = {"project": {"code": "KT", "goal": "v1"}, "authorization": AUTH,
                "alerts": {
                    "a": {"summary": "one", "custom_one": "pending fact one"},
                    "a]": {"summary": "two", "custom_two": "pending fact two"},
                }}
        self.write_legacy(body)
        code, out = self.migrate("--write")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertEqual(set(doc["state"]["alerts"]), {"a", "alert-2"})
        entries = doc["state"]["unverified"]
        locators = {locator for row in entries.values() if isinstance(row, dict)
                    for locator in (row.get("locator") or [])}
        self.assertIn("alerts[a].custom_one", locators)
        self.assertIn("alerts[a]].custom_two", locators)
        self.assertEqual(entries["a-fields"]["locator"], ["alerts[a].custom_one"])
        self.assertEqual(entries["alert-2-fields"]["locator"], ["alerts[a]].custom_two"])
        self.assertNotEqual("a-fields", "alert-2-fields")


class StoppedCollectIncomplete(Fixture):
    """Shape 3: stopped collected proof with an unknown last mutation."""

    def build(self) -> tuple[dict, dict, dict, str]:
        row = rewrite_repo(json.loads((FIXTURES / "i398-fix-row.json").read_text()),
                           str(self.repo))
        row["task_id"] = "i398"
        self.init()
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "i398", "--set",
                         json.dumps({"stage": "doing", "goal": "fix routes",
                                     "verdict": {"value": "accepted"},
                                     "dispatch": [row["item_id"]],
                                     "dispositions": {row["item_id"]: "accepted"}})], self.env)
        self.assertEqual(code, 0, out)
        doc = self.doc()
        doc["state"]["tasks"]["i398"]["stage"] = "done"
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        task = self.doc()["state"]["tasks"]["i398"]
        self.index = self.repo / "index.json"
        self.live = self.repo / "live.json"
        self.write_inputs(row, [{"session": row["session"], "state": "stopped",
                                 "platform": row["platform"], "repo": str(self.repo),
                                 "holder_instance_id": row["holder_instance_id"]}])
        return row, task, self.doc(), str(task["rev"])

    def write_inputs(self, row: dict, live_rows: list[dict]) -> None:
        self.index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": [row],
        }), encoding="utf-8")
        self.live.write_text(json.dumps({
            "schema": "kaola-acp-list/1", "rows": live_rows,
        }), encoding="utf-8")

    def retire(self, task_rev: str, writer: str = "host") -> tuple[int, dict]:
        return run(["state", "retire", "--file", str(self.file), "--writer", writer,
                    "--source", "original result and exact stop", "--kind", "tasks",
                    "--id", "i398", "--expect-rev", task_rev,
                    "--evidence", "original close-out evidence", "--cite", json.dumps(CITE),
                    "--index", str(self.index), "--live", str(self.live)], self.env)

    def test_the_copied_i398_fix_row_reconciles_on_the_incomplete_turn_route(self) -> None:
        row, _task, _doc, rev = self.build()
        before_index = self.index.read_bytes()
        code, out = self.retire(rev)
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], ROUTE_KEY)
        self.assertEqual(entry["item_id"], row["item_id"])
        self.assertEqual(entry["live"], "stopped")
        self.assertEqual(entry["collected"],
                         {"outcome": "stopped", "mutation_status": "unknown"})
        self.assertEqual(entry["holder_instance_id"], row["holder_instance_id"])
        self.assertEqual(self.index.read_bytes(), before_index,
                         "the unknown index row is not rewritten")
        self.assertNotIn("i398", self.doc()["state"]["tasks"])

    def test_state_check_advertises_the_same_reconcile_command(self) -> None:
        _row, _task, _doc, _rev = self.build()
        code, check = run(["state", "check", "--file", str(self.file),
                           "--index", str(self.index), "--live", str(self.live)], self.env)
        self.assertEqual(code, 0, check)
        emitted = [row for row in check["problems"]
                   if row.get("id") == "i398" and row.get("command")
                   and row.get("code") in ("done-not-retired", "state-bloat")]
        self.assertTrue(emitted, check)
        code, out = execute(emitted[0]["command"])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["reconciled_dispatch"][0]["route"], ROUTE_KEY)
        self.assertNotIn("i398", self.doc()["state"]["tasks"])

    def test_completed_mutation_stays_on_the_strict_continuation_route(self) -> None:
        row, _task, _doc, rev = self.build()
        row["evidence"]["collect_status"]["mutation_status"] = "completed"
        self.write_inputs(row, [{"session": row["session"], "state": "stopped",
                                 "platform": row["platform"], "repo": str(self.repo),
                                 "holder_instance_id": row["holder_instance_id"]}])
        code, out = self.retire(rev)
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertNotIn("route", entry)

    def test_absent_outcome_stays_on_the_stale_collect_route(self) -> None:
        row, _task, _doc, rev = self.build()
        row["evidence"]["collect_status"]["outcome"] = None
        self.write_inputs(row, [{"session": row["session"], "state": "stopped",
                                 "platform": row["platform"], "repo": str(self.repo),
                                 "holder_instance_id": row["holder_instance_id"]}])
        code, out = self.retire(rev)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["reconciled_dispatch"][0]["route"], STALE_KEY)

    def _refusal(self, mutate) -> dict:
        row, _task, _doc, rev = self.build()
        live_rows = [{"session": row["session"], "state": "stopped",
                      "platform": row["platform"], "repo": str(self.repo),
                      "holder_instance_id": row["holder_instance_id"]}]
        mutate(row, live_rows)
        self.write_inputs(row, live_rows)
        before_state = self.file.read_bytes()
        before_index = self.index.read_bytes()
        code, out = self.retire(rev)
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertEqual(self.file.read_bytes(), before_state)
        self.assertEqual(self.index.read_bytes(), before_index)
        self.assertIn("i398", self.doc()["state"]["tasks"])
        return out

    def test_a_live_session_refuses(self) -> None:
        def mutate(_row, live):
            live[0]["state"] = "ready"
        out = self._refusal(mutate)
        self.assertIn(ROUTE, out["detail"])
        self.assertIn("still live", out["detail"])

    def test_a_foreign_stopped_holder_refuses(self) -> None:
        def mutate(_row, live):
            live[0]["holder_instance_id"] = "holder-foreign"
        out = self._refusal(mutate)
        self.assertIn("foreign holder", out["detail"])
        self.assertIn("holder-foreign", out["detail"])

    def test_a_missing_live_row_refuses(self) -> None:
        def mutate(_row, live):
            live.clear()
        out = self._refusal(mutate)
        self.assertIn("no stopped --live row", out["detail"])

    def test_a_task_that_is_not_accepted_done_refuses(self) -> None:
        def mutate(_row, _live):
            doc = self.doc()
            doc["state"]["tasks"]["i398"]["verdict"] = {"value": "partial"}
            self.file.write_text(json.dumps(doc), encoding="utf-8")
        out = self._refusal(mutate)
        self.assertIn("only when the Host accepted it done or cancelled it", out["detail"])

    def test_a_disposition_that_is_not_accepted_refuses(self) -> None:
        def mutate(_row, _live):
            doc = self.doc()
            doc["state"]["tasks"]["i398"]["dispositions"] = {"i398-fix": "pending"}
            self.file.write_text(json.dumps(doc), encoding="utf-8")
        out = self._refusal(mutate)
        self.assertIn("per-item disposition is not accepted", out["detail"])

    def test_a_collected_holder_mismatch_refuses(self) -> None:
        def mutate(row, _live):
            row["evidence"]["collect_status"]["holder_instance_id"] = "holder-other"
        out = self._refusal(mutate)
        self.assertIn("collected holder does not match", out["detail"])

    def test_a_collected_repo_mismatch_refuses(self) -> None:
        def mutate(row, _live):
            row["evidence"]["collect_status"]["repo"] = str(self.repo / "elsewhere")
        out = self._refusal(mutate)
        self.assertIn("collected repo differs", out["detail"])

    def test_a_row_without_the_exact_task_link_refuses(self) -> None:
        def mutate(row, _live):
            row.pop("task_id", None)
        out = self._refusal(mutate)
        self.assertIn("names another task", out["detail"])

    def test_a_collected_session_mismatch_refuses(self) -> None:
        def mutate(row, _live):
            row["evidence"]["collect_status"]["session"] = "another-session"
        out = self._refusal(mutate)
        self.assertIn("collected session differs", out["detail"])

    def test_a_live_row_from_another_repo_refuses(self) -> None:
        def mutate(_row, live):
            live[0]["repo"] = str(self.repo / "elsewhere")
        out = self._refusal(mutate)
        self.assertIn("names another repo", out["detail"])

    def test_a_sideagent_writer_refuses_this_route(self) -> None:
        _row, _task, _doc, rev = self.build()
        code, out = self.retire(rev, writer="sideagent")
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("Host-only", out["detail"])
        self.assertIn("i398", self.doc()["state"]["tasks"])

    def test_a_foreign_live_platform_refuses(self) -> None:
        def mutate(_row, live):
            live[0]["platform"] = "codex"
        out = self._refusal(mutate)
        self.assertIn("platform 'codex'", out["detail"])

    def test_a_live_row_without_platform_refuses(self) -> None:
        def mutate(_row, live):
            live[0].pop("platform", None)
        out = self._refusal(mutate)
        self.assertIn("platform None", out["detail"])

    def test_a_conflicting_turn_outcome_refuses(self) -> None:
        def mutate(row, _live):
            row["evidence"]["collect_status"]["turn_outcome"] = "turn_failed"
        out = self._refusal(mutate)
        self.assertIn("turn outcome", out["detail"])

    def test_an_in_progress_mutation_is_not_this_route(self) -> None:
        def mutate(row, _live):
            row["evidence"]["collect_status"]["mutation_status"] = "in_progress"
        out = self._refusal(mutate)
        self.assertNotIn(ROUTE, out["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
