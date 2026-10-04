#!/usr/bin/env python3
"""Issue #255: lifecycle state maintenance, continuity and migration.

The state tool runs as a CLI against isolated temporary projects. Holder and
Runner pieces run in-process against temporary record roots with stubbed
agents and a fake Sideagent socket; no live session or real `.kaola` is used.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
PLATFORMS = REPO / "platforms"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for name in CALLER_ENV:
    os.environ.pop(name, None)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


holder_module = load("kaola_acp_holder_255", REPO / "scripts" / "kaola-acp-holder.py")
acp_module = load("kaola_acp_255", REPO / "scripts" / "kaola-acp.py")
dispatch_module = load("kaola_dispatch_255", SCRIPT)


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env=env or {k: v for k, v in os.environ.items() if k not in CALLER_ENV})
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


AUTH = {"classes": {"Expert": "e", "Elite": "l", "Worker": "w"},
        "grants": [{"id": "codex/default", "state": "granted", "count": 1},
                   {"id": "zcode/default", "state": "granted"}],
        "elite_cap": 2}


class StateProject(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        return run(["state", *args], env)

    def init(self) -> None:
        code, out = self.state("init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
                               "--project", json.dumps({"code": "KT", "goal": "ship"}),
                               "--authorization", json.dumps(AUTH))
        self.assertEqual(code, 0, out)

    def update(self, writer: str, kind: str, ident: str, patch: dict, *extra: str,
               env: dict[str, str] | None = None) -> tuple[int, dict]:
        return self.state("update", "--file", str(self.file), "--writer", writer, "--source", "evt",
                          "--kind", kind, "--id", ident, "--set", json.dumps(patch), *extra, env=env)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def caller_env(self, session: str, holder: str) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": holder, "platform": "zcode",
                                                  "repo": str(self.repo), "session": session})
        return env


class StateTool(StateProject):
    def test_record_updates_conflicts_and_role_rules(self) -> None:
        self.init()
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "parser"})
        self.assertEqual((code, out["value"]["rev"]), (0, 1), out)
        code, out = self.update("host", "tasks", "t1", {"stage": "doing"})
        self.assertEqual((code, out["reason"]), (2, "expect-rev-required"))
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "0")
        self.assertEqual((code, out["reason"]), (3, "conflict"))
        self.assertEqual(out["current"]["rev"], 1)
        self.assertEqual(out["unapplied"], {"stage": "doing"})
        code, out = self.update("worker", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "writer-refused")
        code, out = self.update("sideagent", "tasks", "t1", {"goal": "other"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "host-turn-required")
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "review", "dispatch": ["i1"]},
                                "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        code, out = self.update("sideagent", "tasks", "t1", {"verdict": {"value": "accepted"}},
                                "--expect-rev", "2", "--host-turn", "host-turn-9")
        self.assertEqual(code, 0, out)
        record = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(record["verdict"], {"value": "accepted", "by": "host", "host_turn": "host-turn-9"})
        body = json.loads(self.doc()["body"])
        echo = [row for row in body["attention"] if row["why"] == "transcribed-check"]
        self.assertEqual(echo[0]["host_turn"], "host-turn-9", "the Host sees what was transcribed")
        code, out = self.update("host", "tasks", "t1", {"stage": "done"}, "--expect-rev", "3")
        self.assertEqual(code, 0, out)
        self.assertNotIn("transcribed", self.doc()["state"]["tasks"]["t1"])
        code, out = self.update("host", "tasks", "t1", {"stage": "shipped"}, "--expect-rev", "4")
        self.assertEqual(out["reason"], "invalid-input")

    def test_retire_and_late_event_cannot_reopen(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "g"})
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "1", "--evidence", "c1")
        self.assertEqual(out["reason"], "retire-unmet", "unfinished work is not retired")
        self.update("sideagent", "tasks", "t1", {"stage": "done"}, "--expect-rev", "1")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "2", "--evidence", "commit c1")
        self.assertEqual(out["reason"], "retire-unmet", "done without a Host verdict does not retire")
        self.update("host", "tasks", "t1", {"verdict": {"value": "partial"}}, "--expect-rev", "2")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "3", "--evidence", "commit c1")
        self.assertEqual(out["reason"], "retire-unmet", "a partial verdict does not retire")
        self.update("host", "tasks", "t1", {"verdict": {"value": "accepted"}}, "--expect-rev", "3")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "4", "--evidence", "commit c1")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertNotIn("t1", doc["state"]["tasks"])
        self.assertEqual(doc["state"]["retired"][-1]["evidence"], "commit c1")
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"})
        self.assertEqual(out["reason"], "record-retired", "a late event does not reopen a retired task")
        self.update("host", "decisions", "d1", {"owner": "user", "question": "Expert?"})
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "s",
                               "--kind", "decisions", "--id", "d1", "--expect-rev", "1", "--evidence", "x")
        self.assertEqual(out["reason"], "retire-unmet", "a pending decision stays")

    def test_retirement_needs_dispatched_work_closed_and_stopped(self) -> None:
        self.init()
        self.update("host", "tasks", "t2", {"stage": "done", "goal": "g", "dispatch": ["i7"],
                                             "verdict": {"value": "accepted"}})
        index = self.repo / "index.json"
        live = self.repo / "live.json"
        retire = lambda *extra: self.state("retire", "--file", str(self.file), "--writer", "sideagent",
                                           "--source", "s", "--kind", "tasks", "--id", "t2",
                                           "--expect-rev", "1", "--evidence", "merged c2", *extra)
        code, out = retire()
        self.assertEqual(out["reason"], "retire-unmet")
        self.assertIn("--index and --live", out["detail"])
        index.write_text(json.dumps({"items": [{"item_id": "i7", "status": "in-flight",
                                                "session": "codex-KT-i7-a"}]}), encoding="utf-8")
        live.write_text(json.dumps({"rows": [{"session": "codex-KT-i7-a", "state": "ready"}]}),
                        encoding="utf-8")
        code, out = retire("--index", str(index), "--live", str(live))
        self.assertIn("i7 is in-flight", out["detail"])
        self.assertIn("still live", out["detail"])
        code, check = self.state("check", "--file", str(self.file), "--index", str(index))
        self.assertIn("done-dispatch-open", [p["code"] for p in check["problems"]])
        index.write_text(json.dumps({"items": [{"item_id": "i7", "status": "returned",
                                                "session": "codex-KT-i7-a"}]}), encoding="utf-8")
        live.write_text(json.dumps({"rows": [{"session": "codex-KT-i7-a", "state": "stopped"}]}),
                        encoding="utf-8")
        code, out = retire("--index", str(index), "--live", str(live))
        self.assertEqual(code, 0, out)

    def test_a_sideagent_settles_a_decision_only_as_transcribed_evidence(self) -> None:
        self.init()
        self.update("sideagent", "decisions", "d1", {"owner": "user", "question": "Expert?"})
        code, out = self.update("sideagent", "decisions", "d1", {"status": "settled"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "host-turn-required")
        code, out = self.update("sideagent", "decisions", "d1", {"status": "settled", "evidence": "user msg 9"},
                                "--expect-rev", "1", "--host-turn", "host-turn-4")
        self.assertEqual(code, 0, out)
        body = json.loads(self.doc()["body"])
        echo = [row for row in body["attention"] if row["id"] == "d1"]
        self.assertEqual((echo[0]["why"], echo[0]["host_turn"]), ("transcribed-check", "host-turn-4"))
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "decisions", "--id", "d1", "--expect-rev", "2", "--evidence", "x")
        self.assertEqual(out["reason"], "retire-unmet", "the Host sees the settlement first")
        self.update("host", "decisions", "d1", {"seen": True}, "--expect-rev", "2")
        body = json.loads(self.doc()["body"])
        self.assertEqual([row for row in body["attention"] if row["id"] == "d1"], [])

    def test_a_repair_verdict_does_not_answer_the_next_review(self) -> None:
        self.init()
        fingerprint = lambda: holder_module.attention_fingerprint(self.doc()["body"])
        self.update("host", "tasks", "t3", {"stage": "review", "goal": "g"})
        self.update("host", "tasks", "t3", {"verdict": {"value": "repair", "why": "P1"}}, "--expect-rev", "1")
        self.assertEqual(json.loads(self.doc()["body"])["attention"], [])
        quiet = fingerprint()
        self.update("sideagent", "tasks", "t3", {"stage": "doing"}, "--expect-rev", "2")
        code, out = self.update("sideagent", "tasks", "t3", {"stage": "review"}, "--expect-rev", "3")
        self.assertEqual(code, 0, out)
        task = self.doc()["state"]["tasks"]["t3"]
        self.assertNotIn("verdict", task)
        self.assertEqual(task["prior_verdict"]["value"], "repair", "the repair evidence stays")
        rows = json.loads(self.doc()["body"])["attention"]
        self.assertEqual([(r["why"], r.get("prior_verdict")) for r in rows], [("awaiting-verdict", "repair")])
        self.assertNotEqual(fingerprint(), quiet, "the Host is woken for the second review")
        code, out = self.update("sideagent", "tasks", "t3", {"prior_verdict": None}, "--expect-rev", "4")
        self.assertEqual(out["reason"], "invalid-input")

    def test_section_sources_and_resolved_unknowns_are_kept(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner-msg-3",
                   "--section", "authorization", "--expect-revision", str(revision),
                   "--set", '{"elite_cap": 3}')
        sources = self.doc()["state"]["section_sources"]
        self.assertEqual(sources["authorization"]["source"], "owner-msg-3")
        self.assertEqual(sources["project"]["source"], "turn-1")
        revision = self.doc()["revision"]
        self.state("update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                   "--section", "unverified", "--expect-revision", str(revision),
                   "--set", '{"index-lost": {"summary": "x"}}')
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "sideagent",
                               "--source", "associated to #12 by index row i3", "--section", "unverified",
                               "--expect-revision", str(revision), "--set", '{"index-lost": null}')
        self.assertEqual(code, 0, out)
        stone = self.doc()["state"]["retired"][-1]
        self.assertEqual((stone["kind"], stone["id"], stone["evidence"]),
                         ("unverified", "index-lost", "associated to #12 by index row i3"))

    def test_a_stable_fault_id_recurs_but_a_stale_event_does_not(self) -> None:
        self.init()
        self.update("sideagent", "alerts", "quota-codex", {"level": "warn", "summary": "limit"})
        self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                   "--kind", "alerts", "--id", "quota-codex", "--expect-rev", "1", "--evidence", "reset")
        retired_at = self.doc()["state"]["retired"][-1]["at"]
        code, out = self.update("sideagent", "alerts", "quota-codex", {"level": "warn", "summary": "limit"})
        self.assertEqual(out["reason"], "record-retired", "a late event without its time does not reopen")
        code, out = self.update("sideagent", "alerts", "quota-codex",
                                {"level": "warn", "summary": "limit", "observed_at": "2020-01-01T00:00:00+00:00"})
        self.assertEqual(out["reason"], "record-retired", "an occurrence before the retirement is stale")
        code, out = self.update("sideagent", "alerts", "quota-codex",
                                {"level": "warn", "summary": "limit again", "observed_at": "2999-01-01T00:00:00+00:00"})
        self.assertEqual(code, 0, out)
        self.assertGreater(out["value"]["observed_at"], retired_at)
        self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g", "verdict": {"value": "cancelled"}})
        self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t1", "--expect-rev", "1", "--evidence", "dropped")
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g",
                                                        "observed_at": "2999-01-01T00:00:00+00:00"})
        self.assertEqual(out["reason"], "record-retired", "a retired task id never reopens")

    def test_a_worker_caller_cannot_write_as_host(self) -> None:
        self.init()
        root = Path(self.tmp.name) / "records"
        repo = str(self.repo)
        digest = hashlib.sha256(repo.encode()).hexdigest()[:16]
        worker_dir = root / "codex" / "codex-KT-i1-worker" / digest
        worker_dir.mkdir(parents=True)
        (worker_dir / "record.json").write_text(json.dumps({
            "holder_instance_id": "w-1", "session_role": "worker"}), encoding="utf-8")
        env = self.caller_env("codex-KT-i1-worker", "w-1")
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({"holder_instance_id": "w-1", "platform": "codex",
                                                  "repo": repo, "session": "codex-KT-i1-worker"})
        env["KAOLA_ACP_RECORD_ROOT"] = str(root)
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g"}, env=env)
        self.assertEqual(out["reason"], "writer-refused")
        (worker_dir / "record.json").write_text(json.dumps({"holder_instance_id": "w-1"}), encoding="utf-8")
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g"}, env=env)
        self.assertEqual(code, 0, "a record without a role is a trace, as before")

    def test_host_view_marks_omitted_text_and_keeps_judgment_text_whole(self) -> None:
        self.init()
        long = "q" * 600
        self.update("host", "tasks", "t1", {"stage": "review", "goal": "g" * 600, "acceptance": long})
        self.update("sideagent", "decisions", "d1", {"owner": "host", "question": long})
        body = json.loads(self.doc()["body"])
        task = body["tasks"][0]
        self.assertIn("+360 chars omitted", task["goal"])
        self.assertEqual(task["acceptance"], long)
        self.assertEqual(body["decisions"][0]["question"], long)

    def test_future_schema_is_refused_unchanged(self) -> None:
        self.file.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/3", "body": "{}",
                                         "state": {"x": 1}}), encoding="utf-8")
        raw = self.file.read_bytes()
        for args in (["migrate", "--file", str(self.file), "--write"],
                     ["view", "--file", str(self.file), "--role", "host"]):
            code, out = self.state(*args)
            self.assertEqual((code, out["reason"]), (2, "schema-unsupported"), out)
        code, out = run(["snapshot", "--state", str(self.file), "--out", str(self.file)])
        self.assertEqual(out["reason"], "state-managed")
        self.assertEqual(self.file.read_bytes(), raw)

    def test_alerts_coalesce_and_stay_after_acknowledgement(self) -> None:
        self.init()
        self.update("sideagent", "alerts", "quota-codex", {"level": "warn", "summary": "limit"})
        for _ in range(2):
            code, out = self.update("sideagent", "alerts", "quota-codex", {"ack": True}, "--coalesce")
            self.assertEqual(code, 0, out)
        alert = self.doc()["state"]["alerts"]["quota-codex"]
        self.assertEqual((alert["count"], alert["ack"], alert["level"]), (3, True, "warn"))
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator")
        self.assertEqual(out["special"]["alerts"][0]["id"], "quota-codex",
                         "an acknowledged alert is still reported")

    def test_wake_fingerprint_follows_what_a_host_judgment_asks(self) -> None:
        self.init()
        fingerprint = lambda: holder_module.attention_fingerprint(self.doc()["body"])
        self.update("sideagent", "decisions", "d1", {"owner": "host", "question": "Use Expert?"})
        self.update("sideagent", "alerts", "a1", {"level": "severe", "summary": "quota"})
        first = fingerprint()
        self.update("sideagent", "tasks", "t9", {"stage": "doing", "goal": "unrelated"})
        code, out = self.update("sideagent", "alerts", "a1", {"summary": "quota"}, "--coalesce")
        self.assertEqual((code, out["value"]["count"]), (0, 2), out)
        self.assertEqual(fingerprint(), first, "unrelated work and a repeated alert do not wake")
        self.update("sideagent", "decisions", "d1", {"question": "Use Elite instead?"}, "--expect-rev", "1")
        changed = fingerprint()
        self.assertNotEqual(changed, first, "the same decision id with a new question is new attention")
        self.update("sideagent", "decisions", "d1", {"options": ["Elite", "wait"]}, "--expect-rev", "2")
        self.assertNotEqual(fingerprint(), changed, "new options are new attention")

    def test_sections_need_revision_and_host_ownership(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--section", "authorization", "--expect-revision", str(revision),
                               "--set", '{"elite_cap": 9}')
        self.assertEqual(out["reason"], "host-only")
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                               "--section", "project", "--expect-revision", str(revision - 1),
                               "--set", '{"goal": "new"}')
        self.assertEqual((code, out["reason"]), (3, "conflict"))
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner",
                               "--section", "project", "--expect-revision", str(revision),
                               "--set", '{"goal": "new", "code": null}')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["project"], {"goal": "new"})

    def test_binding_guards_late_writes_of_a_replaced_sideagent(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                               "--section", "sideagent", "--expect-revision", str(revision),
                               "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent-a",
                                                    "preset": "zcode/default", "state": "active"}))
        self.assertEqual(code, 0, out)
        old = self.caller_env("zcode-KT-sideagent-a", "holder-a")
        code, out = self.state("update", "--file", str(self.file), "--writer", "sideagent", "--source", "own",
                               "--section", "sideagent", "--expect-revision", str(revision + 1),
                               "--set", '{"holder_instance_id": "holder-a"}', env=old)
        self.assertEqual(code, 0, out)
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "todo", "goal": "g"},
                                "--host-turn", "h1", env=old)
        self.assertEqual(code, 0, out)
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "replace",
                               "--section", "sideagent", "--expect-revision", str(revision),
                               "--set", json.dumps({"session": "zcode-KT-sideagent-b",
                                                    "holder_instance_id": None, "state": "active"}))
        self.assertEqual(code, 0, out)
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "1", env=old)
        self.assertEqual(out["reason"], "binding-superseded", "the old Sideagent's late write is refused")
        new = self.caller_env("zcode-KT-sideagent-b", "holder-b")
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing", "wait": "capacity"},
                                "--expect-rev", "1", env=new)
        self.assertEqual(code, 0, out)
        code, out = self.update("host", "tasks", "t1", {"stage": "done"}, "--expect-rev", "2", env=new)
        self.assertEqual(out["reason"], "writer-mismatch")
        stray = self.caller_env("zcode-KT-i9-helper", "holder-h")
        code, out = self.update("sideagent", "alerts", "a1", {"level": "watch", "summary": "s"}, env=stray)
        self.assertEqual(out["reason"], "binding-superseded", "a helper is not the maintenance Sideagent")

    def test_concurrent_writers_never_lose_an_update(self) -> None:
        self.init()
        results: list[tuple[int, dict]] = []

        def write(index: int) -> None:
            results.append(self.update("sideagent", "alerts", f"a{index}",
                                       {"level": "watch", "summary": f"s{index}"}))

        threads = [threading.Thread(target=write, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertTrue(all(code == 0 for code, _ in results), results)
        doc = self.doc()
        self.assertEqual(sorted(doc["state"]["alerts"]), sorted(f"a{index}" for index in range(8)))
        self.assertEqual(doc["revision"], 9)
        revisions = sorted(out["revision"] for _, out in results)
        self.assertEqual(revisions, list(range(2, 10)), "each write saw the previous one")

    def test_large_state_projects_a_bounded_host_view(self) -> None:
        self.init()
        doc = self.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2", "holder_instance_id": "h"}
        for index in range(60):
            doc["state"]["tasks"][f"t{index}"] = {
                "stage": "doing", "goal": f"task {index}", "rev": 1, "source": "s",
                "dispatch": [f"item-{index}-{n}" for n in range(10)],
                "evidence": ["receipt " + "x" * 400 for _ in range(10)]}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.update("host", "tasks", "t0", {"next": "review"}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        self.assertGreater(out["file_bytes"], 65536)
        self.assertLess(out["body_bytes"], 65536)
        body = json.loads(self.doc()["body"])
        self.assertNotIn("evidence", json.dumps(body["tasks"]), "evidence stays out of the Host view")
        self.assertEqual(len(body["tasks"]), 60, "no responsibility is truncated away")
        self.assertEqual(body["authorization"], AUTH)
        holder_body, defect = holder_module.heartbeat_prompt_body(self.file)
        self.assertEqual((json.loads(holder_body), defect), (body, None),
                         "a new holder injects only the projected body")
        doc = self.doc()
        doc.pop("carrier")
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.update("host", "tasks", "t1", {"next": "x"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "carrier-limit",
                         "without a proven holder the file stays readable by the old holder")
        self.assertNotIn("x", self.doc()["state"]["tasks"]["t1"].get("next", ""))

    def test_host_view_over_the_injection_bound_is_refused_not_truncated(self) -> None:
        self.init()
        doc = self.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2"}
        for index in range(400):
            doc["state"]["tasks"][f"t{index}"] = {"stage": "todo", "goal": "g" * 200, "rev": 1,
                                                  "next": "n" * 200, "source": "s"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = self.update("host", "tasks", "t0", {"wait": "w"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "host-view-too-large")
        self.assertEqual(self.file.read_bytes(), before)

    def test_snapshot_does_not_overwrite_structured_state(self) -> None:
        self.init()
        snapshot = self.repo / "plain.json"
        snapshot.write_text(json.dumps({"project": {}}), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = run(["snapshot", "--state", str(snapshot), "--out", str(self.file)])
        self.assertEqual((code, out["reason"]), (2, "state-managed"))
        self.assertEqual(self.file.read_bytes(), before)

    def test_dispatch_reads_authorization_from_structured_state(self) -> None:
        self.init()
        code, out = run(["project", "--authorization", str(self.file), "--platforms", str(PLATFORMS)])
        self.assertEqual(code, 0, out)
        self.assertIn("codex/default", {row["id"] for row in out["candidates"]})

    def test_timer_template_check_is_exact(self) -> None:
        expected = ("/kaola-delegator\nKaola-Delegator inquiry: read "
                    f"{self.repo.resolve()}/.kaola/delegator-heartbeat.json on target local and run "
                    "the loaded Skill's standard inquiry.")
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator", "--body", expected + "\n")
        self.assertEqual((code, out["result"]), (0, "match"))
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator", "--body", expected + "\nalso check PRs")
        self.assertEqual((code, out["result"], out["expected"]), (1, "mismatch", expected))

    def test_delegator_view_reports_user_requirements_from_agents(self) -> None:
        self.init()
        (self.repo / "AGENTS.md").write_text(
            "# Project\n\n<!-- KPR-USER-REQUIREMENTS-START -->\n- Never log in.\n- Ask before release.\n"
            "<!-- KPR-USER-REQUIREMENTS-END -->\n", encoding="utf-8")
        self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g"})
        self.update("host", "holds", "h1", {"scope": "codex/default", "reason": "limit"})
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator")
        self.assertEqual(out["user_requirements"]["items"], ["- Never log in.", "- Ask before release."])
        self.assertEqual([row["id"] for row in out["todo"]], ["t1"])
        self.assertEqual(out["special"]["holds"][0]["id"], "h1")
        (self.repo / "AGENTS.md").unlink()
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator")
        self.assertIn("missing", out["user_requirements"], "a missing source is named")

    def test_scoped_requirement_headings_are_all_reported(self) -> None:
        self.init()
        (self.repo / "AGENTS.md").write_text(
            "# Project\n\n## Commands\n\n- make\n\n## User special requirements — release (#9)\n\n"
            "Source: owner, 2026-10-04.\n\n1. **Fidelity.** Keep templates exact.\n2. **Upgrade.** Migrate.\n\n"
            "## Notes\n\n- not a requirement\n\n## User requirements: style\n\n- Plain words.\n",
            encoding="utf-8")
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator", "--repo", str(self.repo))
        items = out["user_requirements"]["items"]
        self.assertEqual(items, ["## User special requirements — release (#9)", "Source: owner, 2026-10-04.",
                                 "1. **Fidelity.** Keep templates exact.", "2. **Upgrade.** Migrate.",
                                 "## User requirements: style", "- Plain words."])
        self.assertNotIn("missing", out["user_requirements"])

    def test_repeated_cycles_keep_current_records_not_history(self) -> None:
        self.init()
        sizes = []
        for cycle in range(40):
            task = f"t{cycle}"
            self.update("host", "tasks", task, {"stage": "doing", "goal": f"work {cycle}"})
            self.update("sideagent", "alerts", "conn-wait", {"level": "watch", "summary": "slow ACP"},
                        "--coalesce")
            self.update("sideagent", "tasks", task, {"next": "collect", "evidence": [f"index:{task}"]},
                        "--expect-rev", "1")
            self.update("host", "tasks", task, {"stage": "done", "verdict": {"value": "accepted"}},
                        "--expect-rev", "2")
            code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent",
                                   "--source", "closeout", "--kind", "tasks", "--id", task,
                                   "--expect-rev", "3", "--evidence", f"commit c{cycle}")
            self.assertEqual(code, 0, out)
            sizes.append(len(self.file.read_bytes()))
        doc = self.doc()
        self.assertEqual(doc["state"]["tasks"], {}, "finished work left the current set")
        self.assertEqual(list(doc["state"]["alerts"]), ["conn-wait"], "a repeat updates one alert")
        self.assertEqual(doc["state"]["alerts"]["conn-wait"]["count"], 40)
        self.assertEqual(len(doc["state"]["retired"]), 40)
        self.assertLess(sizes[-1] - sizes[20], (sizes[20] - sizes[0]) + 4096,
                        "growth is the bounded tombstone list, not history")
        self.assertNotIn("index:t0", doc["body"], "evidence stays out of the Host view")

    def test_a_repair_keeps_its_failure_evidence_for_the_next_decision(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "parser", "dispatch": ["i1"]})
        self.update("sideagent", "holds", "codex-quota", {"scope": "codex/default", "reason": "limit",
                                                         "evidence": "receipt r1", "resume_when": "owner"})
        self.update("sideagent", "tasks", "t1",
                    {"stage": "review", "verdict": {"value": "repair", "why": "edge case e2 fails"},
                     "evidence": ["qa:e2 failed on codex/default"]},
                    "--expect-rev", "1", "--host-turn", "host-turn-7")
        code, side = self.state("view", "--file", str(self.file), "--role", "sideagent")
        task = side["state"]["tasks"]["t1"]
        self.assertEqual(task["verdict"]["value"], "repair")
        self.assertEqual(task["evidence"], ["qa:e2 failed on codex/default"])
        self.assertIn("codex-quota", side["state"]["holds"], "the failed runtime stays held")
        code, host = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertIn({"kind": "tasks", "id": "t1", "why": "transcribed-check", "host_turn": "host-turn-7",
                       "fields": ["verdict"]}, host["attention"])
        self.update("sideagent", "tasks", "t1", {"stage": "doing", "dispatch": ["i1", "i2"]},
                    "--expect-rev", "2")
        task = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual((task["dispatch"], task["verdict"]["value"]), (["i1", "i2"], "repair"),
                         "the repair stays the same task with its earlier evidence")

    def test_timer_body_is_the_same_at_every_cadence(self) -> None:
        bodies = set()
        for minutes in (30, 60, 120, 240):
            (self.repo / ".kaola" / "delegator-heartbeat.json").write_text(json.dumps(
                {"cadence": {"timezone": "Asia/Shanghai", "start_local": "08:00", "end_local": "22:00",
                             "interval_minutes": minutes}}), encoding="utf-8")
            code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                                   "--entry", "/kaola-delegator", "--body", "")
            self.assertEqual(code, 1)
            bodies.add(out["expected"])
        self.assertEqual(len(bodies), 1, "cadence lives in the Delegator file, not in the timer text")
        self.assertNotRegex(bodies.pop(), r"\d+ ?min|interval|08:00")

    def test_check_finds_untraced_and_unassociated_work(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "g"})
        index = self.repo / "index.json"
        index.write_text(json.dumps({"items": [
            {"item_id": "i1", "status": "in-flight", "session": "codex-KT-i1-a"},
            {"item_id": "i2", "status": "in-flight", "task_id": "gone"}]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"session": "zcode-KT-helper", "session_role": "sideagent", "repo": str(self.repo),
             "state": "ready"}]}), encoding="utf-8")
        code, out = self.state("check", "--file", str(self.file), "--index", str(index), "--live", str(live))
        codes = {problem["code"] for problem in out["problems"]}
        self.assertTrue({"doing-untraced", "dispatch-unassociated", "dispatch-task-missing",
                         "sideagent-helper"} <= codes, codes)
        self.assertTrue(out["read_only"])


LEGACY_BODY = {
    "project": {"repo": "/abs/kt", "code": "KT", "goal": "close issues", "stop": "backlog empty",
                "rules": ["no Friday release"]},
    "authorization": AUTH,
    "active": [{"ref": "#12", "session": "claude-code-KT-i12-fix", "next": "accept", "evidence": "wt-12"},
               {"ref": "#12", "session": "codex-KT-i12-qa", "next": "qa"}],
    "pending": [{"duty": "integration QA", "scope": "#12", "owner": "Host", "evidence": "not run"},
                {"duty": "accept #13", "scope": "#13", "owner": "Host"}],
    "recovery": {"old_repo": "/abs/old"},
    "cadence_note": "every two hours",
}


class Migration(StateProject):
    def write_legacy(self, body: dict | str = LEGACY_BODY) -> bytes:
        text = json.dumps({"schema": "kaola-heartbeat-prompt/1",
                           "body": body if isinstance(body, str) else json.dumps(body)})
        self.file.write_text(text, encoding="utf-8")
        return self.file.read_bytes()

    def test_plan_then_write_preserves_duties_and_lists_unknowns(self) -> None:
        raw = self.write_legacy()
        index = self.repo / "index.json"
        index.write_text(json.dumps({"items": [
            {"item_id": "qa", "status": "in-flight", "session": "codex-KT-i12-qa"},
            {"item_id": "lost", "status": "unknown", "session": "droid-KT-i99-x"}]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"session": "zcode-KT-orchestrator-main", "host_class": True, "session_role": "host",
             "repo": str(self.repo), "state": "ready", "holder_instance_id": "host-1",
             "holder_features": ["heartbeat-state/2", "sideagent-relay/1"]},
            {"session": "zcode-KT-sideagent", "platform": "zcode", "session_role": "sideagent",
             "repo": str(self.repo), "state": "ready", "holder_instance_id": "side-1"}]}), encoding="utf-8")
        args = ["migrate", "--file", str(self.file), "--index", str(index), "--live", str(live)]
        code, out = self.state(*args)
        self.assertEqual((code, out["result"], out["writes"]), (0, "planned", False), out)
        self.assertEqual(self.file.read_bytes(), raw, "a plan writes nothing")
        code, out = self.state(*args, "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        doc = self.doc()
        state = doc["state"]
        self.assertEqual(doc["schema"], "kaola-heartbeat-prompt/2")
        self.assertEqual(state["authorization"], AUTH, "valid authorization is kept as is")
        self.assertEqual(state["project"]["rules"], ["no Friday release"], "adopted rules are not re-asked")
        self.assertEqual(state["tasks"]["#12"]["sessions"], ["claude-code-KT-i12-fix", "codex-KT-i12-qa"])
        self.assertEqual(state["tasks"]["#12"]["dispatch"], ["qa"])
        self.assertEqual(len(state["tasks"]["#12"]["assignments"]), 2, "one assignment per v1 active row")
        self.assertEqual(state["tasks"]["#12"]["next"], ["accept", "qa"])
        for duty in ("duty-1", "duty-2"):
            self.assertEqual(state["tasks"][duty]["stage"], "todo", "no stage is guessed from the text")
            self.assertIn(f"{duty}-stage", state["unverified"])
        self.assertIn("legacy-cadence_note", state["unverified"], "an unknown key is kept for review")
        self.assertIn("index-lost", state["unverified"])
        self.assertIn("rules-source", state["unverified"])
        self.assertIsNone(state["sideagent"], "a live Sideagent-role row alone is never bound")
        self.assertEqual(state["unverified"]["sideagent-candidate"]["live"][0]["session"], "zcode-KT-sideagent")
        self.assertEqual(doc["carrier"]["holder_instance_id"], "host-1")
        raw_copy = Path(state["recovery"]["migration"]["raw"])
        self.assertEqual(raw_copy.read_bytes(), raw, "the one raw migration evidence is kept")
        self.assertEqual(state["recovery"]["legacy"], {"old_repo": "/abs/old"})
        body = json.loads(doc["body"])
        self.assertEqual(body["authorization"], AUTH, "old readers of body still find authorization")
        code, again = self.state(*args, "--write")
        self.assertEqual(again["result"], "current", "a repeated migration changes nothing")

    def test_real_v1_shape_keeps_every_nested_field_or_lists_it(self) -> None:
        body = {
            "project": {"code": "KT"}, "authorization": AUTH,
            "host": {"holder_instance_id": "host-0", "platform": "zcode", "repo": "/abs/kt",
                     "session": "zcode-KT-orchestrator-main"},
            "sideagent": {"preset": "zcode/default", "state": "active", "authorization_source": "owner msg 2",
                          "session": "zcode-KT-sideagent", "holder_instance_id": "side-1",
                          "evidence": "e", "dispatch_event_cursor": 3, "prompt_fingerprint": "sha256:s",
                          "next": "maintain"},
            "active": [
                {"ref": "#255", "session": "droid-KT-i255-impl", "platform": "droid", "preset": "droid/opus",
                 "holder_instance_id": "w-1", "dispatch_event_cursor": 9, "prompt_fingerprint": "sha256:a",
                 "next": "repair", "evidence": "wt", "candidate": {"commit": "ae3f0006"},
                 "wait": "Opus review", "custom_duty": "re-run QA after repair"},
                {"ref": "#255", "session": "codex-KT-i255-qa", "platform": "codex", "preset": "codex/default",
                 "holder_instance_id": "w-2", "dispatch_event_cursor": 4, "prompt_fingerprint": "sha256:b",
                 "candidate": "ae3f0006", "next": "live QA", "evidence": "qa.md"}],
            "pending": [
                {"duty": "continue implementation", "owner": "Host", "scope": "#255", "boundary": "merge",
                 "evidence": "e", "next": "verdict", "wait": "QA", "resume_when": "QA returns",
                 "holder": "w-1", "platform": "droid", "follow_up": "doc check"},
                {"duty": "closeout #254", "stage": "closeout", "owner": "Host", "scope": "#254"}],
        }
        raw = self.write_legacy(body)
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"session": "zcode-KT-sideagent", "platform": "zcode", "session_role": "sideagent",
             "repo": str(self.repo), "state": "ready", "holder_instance_id": "side-1"}]}), encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--live", str(live), "--write")
        self.assertEqual(code, 0, out)
        state = self.doc()["state"]
        task = state["tasks"]["#255"]
        self.assertEqual([row["locator"] for row in task["assignments"]], ["active[0]", "active[1]"])
        first = task["assignments"][0]
        for key, value in body["active"][0].items():
            self.assertEqual(first[key], value, f"active[0].{key} is kept with its assignment")
        self.assertEqual(state["unverified"]["active-0-fields"]["locator"], ["active[0].custom_duty"])
        self.assertNotIn("active-1-fields", state["unverified"])
        duty = state["tasks"]["duty-1"]
        self.assertEqual(duty["stage"], "todo", "'continue implementation' is not closeout")
        for key in ("next", "wait", "resume_when", "holder", "platform", "boundary", "follow_up"):
            self.assertEqual(duty[key], body["pending"][0][key])
        self.assertEqual(state["unverified"]["pending-0-fields"]["locator"], ["pending[0].follow_up"])
        self.assertEqual(state["tasks"]["duty-2"]["stage"], "closeout", "an explicit stage is kept")
        self.assertNotIn("duty-2-stage", state["unverified"])
        self.assertEqual(state["sideagent"]["holder_instance_id"], "side-1",
                         "the authorized v1 binding proven by its live holder carries over")
        self.assertEqual(state["sideagent"]["authorization_source"], "owner msg 2")
        self.assertEqual(state["recovery"]["v1_host"]["holder_instance_id"], "host-0")
        self.assertFalse([key for key in state["unverified"] if key.startswith("legacy-")],
                         "host and sideagent have a lifecycle home")
        self.assertTrue(Path(state["recovery"]["migration"]["raw"]).read_bytes() == raw)

    def test_a_v1_binding_not_proven_live_stays_a_candidate(self) -> None:
        body = dict(LEGACY_BODY, sideagent={"session": "zcode-KT-sideagent", "holder_instance_id": "side-0",
                                            "authorization_source": "owner", "state": "active"})
        self.write_legacy(body)
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"session": "zcode-KT-sideagent", "platform": "zcode", "session_role": "sideagent",
             "repo": str(self.repo), "state": "ready", "holder_instance_id": "side-9"}]}), encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--live", str(live), "--write")
        state = self.doc()["state"]
        self.assertIsNone(state["sideagent"])
        self.assertEqual(state["unverified"]["sideagent-candidate"]["v1"]["holder_instance_id"], "side-0")

    def test_a_v1_file_after_an_earlier_migration_is_flagged_as_overwritten(self) -> None:
        self.write_legacy()
        self.state("migrate", "--file", str(self.file), "--write")
        body = dict(LEGACY_BODY, project={"code": "KT", "goal": "older writer"})
        self.write_legacy(body)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        alert = doc["state"]["alerts"]["state-overwritten"]
        self.assertEqual(alert["level"], "severe")
        self.assertIn("state-overwritten", [row["id"] for row in json.loads(doc["body"])["attention"]])

    def test_interrupted_migration_resumes_from_the_same_raw_evidence(self) -> None:
        raw = self.write_legacy()
        digest = hashlib.sha256(raw).hexdigest()
        stale = self.file.with_name(f"heartbeat-prompt.v1-{digest[:12]}.json")
        stale.write_bytes(raw)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        self.assertIn("live", out["unchecked"], "unchecked sources are named")
        stale.write_text("other", encoding="utf-8")
        self.write_legacy()
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(out["reason"], "raw-evidence-conflict")

    def test_unreadable_legacy_body_is_left_unchanged(self) -> None:
        raw = self.write_legacy("not json at all")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["reason"]), (2, "legacy-unreadable"))
        self.assertEqual(self.file.read_bytes(), raw)

    def test_a_carrier_replaced_by_an_older_holder_reads_the_legacy_bound(self) -> None:
        state_file = self.file
        records = Path(self.tmp.name) / "records"
        digest = hashlib.sha256(str(dispatch_module.repo_of_state_file(state_file)).encode()).hexdigest()[:16]
        host_dir = records / "zcode" / "zcode-KT-orchestrator-main" / digest
        host_dir.mkdir(parents=True)
        carrier = {"capability": "heartbeat-state/2", "platform": "zcode",
                   "session": "zcode-KT-orchestrator-main", "holder_instance_id": "host-new"}
        previous = os.environ.get("KAOLA_ACP_RECORD_ROOT")
        os.environ["KAOLA_ACP_RECORD_ROOT"] = str(records)
        try:
            def holder(instance: str, features: list) -> bool:
                (host_dir / "record.json").write_text(json.dumps({
                    "holder_instance_id": instance, "holder_pid": os.getpid(),
                    "holder_features": features}), encoding="utf-8")
                return dispatch_module.carrier_replaced_by_older(carrier, state_file)
            self.assertFalse(holder("host-new", []), "the recorded carrier itself")
            self.assertFalse(holder("host-later", ["heartbeat-state/2"]), "a capable successor")
            self.assertTrue(holder("host-old", []), "a live holder without the capability")
        finally:
            if previous is None:
                os.environ.pop("KAOLA_ACP_RECORD_ROOT", None)
            else:
                os.environ["KAOLA_ACP_RECORD_ROOT"] = previous

    def test_old_holder_bound_keeps_the_file_small_without_a_capable_host(self) -> None:
        body = dict(LEGACY_BODY)
        body["active"] = [{"ref": f"#{n}", "session": f"codex-KT-i{n}-x", "evidence": "e" * 900}
                          for n in range(80)]
        raw = self.write_legacy(body)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(out["reason"], "carrier-limit")
        self.assertEqual(self.file.read_bytes(), raw)


class ExecuteSeats(StateProject):
    def test_bound_sideagent_is_exempt_and_helpers_count(self) -> None:
        self.init()
        revision = self.doc()["revision"]
        run(["state", "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
             "--section", "sideagent", "--expect-revision", str(revision), "--set",
             json.dumps({"platform": "codex", "session": "codex-KT-sideagent", "state": "active",
                         "preset": "codex/default"})])
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": []}), encoding="utf-8")
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({"scope": "research", "repo": str(self.repo), "items": [
            {"item_id": "side", "preset": "codex/default", "session": "codex-KT-sideagent",
             "prompt": "maintain", "role": "sideagent", "task_id": "t-maint"},
            {"item_id": "w1", "preset": "codex/default", "session": "codex-KT-i1-a", "prompt": "a",
             "task_id": "t1", "output": "docs/a.md"},
            {"item_id": "helper", "preset": "codex/default", "session": "codex-KT-i1-b", "prompt": "b",
             "role": "sideagent"},
            {"item_id": "exp", "preset": "codex/default", "session": "codex-KT-i1-c", "prompt": "c",
             "requires": {"class": "Expert"}}]}), encoding="utf-8")
        code, out = run(["execute", "--plan", str(plan), "--authorization", str(self.file),
                         "--platforms", str(PLATFORMS), "--skills-root", str(self.repo / "skills"),
                         "--live", str(live), "--dry-run"])
        self.assertEqual(code, 0, out)
        items = {row["item_id"]: row for row in out["items"]}
        self.assertEqual(items["side"]["reason"], "dry-run", items)
        self.assertTrue(items["side"]["seat_exempt"])
        self.assertEqual(items["w1"]["reason"], "dry-run", "the exempt Sideagent left the one seat free")
        self.assertEqual((items["w1"]["task_id"], items["w1"]["output"]), ("t1", "docs/a.md"))
        self.assertEqual(items["helper"]["reason"], "count", "a second Sideagent-role item is a worker")
        self.assertIn("seat_note", items["helper"]["evidence"])
        self.assertEqual(items["exp"]["reason"], "requirement-unmet")
        self.assertIn("Expert", items["exp"]["detail"])

    def test_bound_sideagent_never_takes_or_waits_for_a_shared_worker_seat(self) -> None:
        auth = {**AUTH, "grants": [{"id": "codex/default", "state": "granted", "count": 1,
                                    "shared_seat": "codex-acct"}]}
        code, _ = self.state("init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
                             "--project", json.dumps({"code": "KT"}), "--authorization", json.dumps(auth))
        self.assertEqual(code, 0)
        run(["state", "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
             "--section", "sideagent", "--expect-revision", str(self.doc()["revision"]), "--set",
             json.dumps({"platform": "codex", "session": "codex-KT-sideagent", "state": "active",
                         "preset": "codex/default"})])
        live = self.repo / "live.json"
        plan = self.repo / "plan.json"
        side = {"item_id": "side", "preset": "codex/default", "session": "codex-KT-sideagent",
                "prompt": "maintain", "role": "sideagent"}
        worker = {"item_id": "w1", "preset": "codex/default", "session": "codex-KT-i1-a", "prompt": "a"}
        helper = {"item_id": "helper", "preset": "codex/default", "session": "codex-KT-i1-h",
                  "prompt": "h", "role": "sideagent"}
        row = lambda session: {"session": session, "platform": "codex", "preset": "codex/default",
                               "repo": str(self.repo), "state": "ready"}

        def execute(rows: list, items: list, availability: dict | None = None) -> dict:
            live.write_text(json.dumps({"rows": rows}), encoding="utf-8")
            plan.write_text(json.dumps({"scope": "research", "repo": str(self.repo), "items": items}),
                            encoding="utf-8")
            extra = []
            if availability is not None:
                path = self.repo / "availability.json"
                path.write_text(json.dumps(availability), encoding="utf-8")
                extra = ["--availability", str(path)]
            code, out = run(["execute", "--plan", str(plan), "--authorization", str(self.file),
                             "--platforms", str(PLATFORMS), "--skills-root", str(self.repo / "skills"),
                             "--live", str(live), "--dry-run", *extra])
            self.assertEqual(code, 0, out)
            return {item["item_id"]: item["reason"] for item in out["items"]}

        self.assertEqual(execute([row("codex-KT-sideagent")], [worker]), {"w1": "dry-run"},
                         "a live bound Sideagent takes no shared worker seat")
        self.assertEqual(execute([row("codex-KT-i1-a")], [side, helper]),
                         {"side": "dry-run", "helper": "shared-occupied"},
                         "a worker on the shared seat does not hold up the bound Sideagent; a helper counts")
        reasons = execute([], [side], {"absent": ["codex/default"]})
        self.assertNotEqual(reasons["side"], "dry-run", "an evidenced service limit still applies")


# -- holder: projected carrier, capability and relay --------------------------

class StubProc:
    pid = 25500


class StubAgent:
    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
        self.exit_code = None
        self.exit_signal = None
        self.stderr_pump = None
        self.malformed_lines = 0
        self.handler_errors = 0
        self.pending_out: dict = {}
        self.sent: list[dict] = []
        self.next_id = 0

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(self.next_id)] = method
        self.sent.append({"method": method, "id": self.next_id, "params": params})
        return self.next_id

    def send_message(self, message: dict) -> None:
        self.sent.append(message)

    def wait_response(self, request_id, timeout):
        time.sleep(0.01)
        return None

    def prompts(self) -> list[str]:
        return [m["params"]["prompt"][0]["text"] for m in self.sent if m.get("method") == "session/prompt"]


class FakeSideagent:
    """A Sideagent holder socket that records relay prompts."""

    def __init__(self, path: Path, busy: bool = False) -> None:
        self.path = path
        self.busy = busy
        self.prompts: list[dict] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(path))
        self.server.listen(4)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self) -> None:
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            with connection:
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                message = json.loads(data.decode())
                self.prompts.append(message)
                if self.busy:
                    reply = {"error": {"code": "prompt-in-progress"}, "outcome": "in_progress"}
                else:
                    reply = {"outcome": "in_progress", "prompt_fingerprint": f"sha256:{len(self.prompts)}"}
                connection.sendall(json.dumps(reply).encode() + b"\n")

    def close(self) -> None:
        self.server.close()
        try:
            self.path.unlink()
        except OSError:
            pass


class HolderRelay(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-holder-")
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        (self.repo / ".kaola").mkdir(parents=True)
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        self.records = root / "records"
        host_dir = self.records / "zcode" / "zcode-KT-orchestrator-main" / digest
        host_dir.mkdir(parents=True)
        args = argparse.Namespace(record_dir=str(host_dir), socket=str(root / "host.sock"),
                                  platform="zcode", session="zcode-KT-orchestrator-main",
                                  repo=str(self.repo), init_meta="", command="stub")
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-host-255"
        self.holder.state = "ready"
        self.holder.heartbeat_host = None
        self.side_dir = self.records / "zcode" / "zcode-KT-sideagent" / digest
        self.side_dir.mkdir(parents=True)
        sock_digest = hashlib.sha256(str(self.side_dir).encode()).hexdigest()[:24]
        self.side_sock = Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{sock_digest}.sock"
        self.fake: FakeSideagent | None = None

    def tearDown(self) -> None:
        if self.fake:
            self.fake.close()
        self.tmp.cleanup()

    def write_state(self, attention: list) -> None:
        body = json.dumps({"view": "host", "attention": attention, "tasks": []})
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2", "body": body,
            "state": {"sideagent": {"platform": "zcode", "session": "zcode-KT-sideagent",
                                    "holder_instance_id": "side-1", "state": "active"}}}), encoding="utf-8")

    def live_sideagent(self, busy: bool = False, holder: str = "side-1") -> None:
        (self.side_dir / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "repo": str(self.repo), "state": "ready",
            "holder_instance_id": holder, "holder_pid": os.getpid(),
            "holder_features": ["heartbeat-state/2", "sideagent-relay/1"]}), encoding="utf-8")
        if self.fake is None:
            self.fake = FakeSideagent(self.side_sock, busy=busy)

    def event(self, session: str, kind: str, cursor: int, **extra: str) -> dict:
        return self.holder.op_worker_event({"kind": kind, "platform": "codex", "session": session,
                                            "repo": str(self.repo), "reason": "end_turn",
                                            "event_cursor": cursor, **extra})

    def sideagent_end(self, cursor: int, turn: int, holder: str = "side-1",
                      outcome: str = "turn_completed") -> dict:
        return self.event("zcode-KT-sideagent", "idle", cursor, holder_instance_id=holder,
                          turn_fingerprint=f"sha256:{turn}", turn_outcome=outcome)

    def finish_host_turn(self) -> None:
        fingerprint = self.holder.turn.get("fingerprint")
        self.holder.turn["active"] = False
        self.holder._worker_event_turn_end(fingerprint, "turn_completed")

    def test_rebind_moves_the_carrier_in_place_and_keeps_the_seat(self) -> None:
        old = {"platform": "codex", "session": "codex-KT-orchestrator-old", "repo": str(self.repo),
               "socket": str(Path(self.tmp.name) / "old-host.sock")}
        self.holder.heartbeat_host = dict(old)
        instance, agent = self.holder.holder_instance_id, self.holder.agent
        new_sock = Path(self.tmp.name) / "new-host.sock"
        new = {"platform": "zcode", "session": "zcode-KT-orchestrator-main", "repo": str(self.repo),
               "socket": str(new_sock)}
        refused = self.holder.op_rebind_heartbeat_host(
            {"target": dict(new, repo="/elsewhere")})
        self.assertEqual(refused["error"]["code"], "heartbeat-host-foreign-repo")
        mismatch = self.holder.op_rebind_heartbeat_host(
            {"target": new, "expected_holder_instance_id": "someone-else"})
        self.assertIn("error", mismatch)
        self.assertEqual(self.holder.heartbeat_host, old, "a refusal changes nothing")
        receipt = self.holder.op_rebind_heartbeat_host(
            {"target": new, "host_holder_instance_id": "host-2",
             "expected_holder_instance_id": instance})
        self.assertTrue(receipt["rebound"])
        self.assertEqual(self.holder.heartbeat_host, new)
        self.assertIs(self.holder.agent, agent, "the agent process is not restarted")
        self.assertEqual(self.holder.holder_instance_id, instance)
        record = json.loads((Path(self.holder.args.record_dir) / "record.json").read_text())
        self.assertEqual(record["heartbeat_host"]["session"], "zcode-KT-orchestrator-main")
        self.assertEqual(record["holder_instance_id"], instance)
        events = (Path(self.holder.args.record_dir) / "events.jsonl").read_text().splitlines()
        self.assertIn("heartbeat_host_rebound", [json.loads(line)["kind"] for line in events])
        new_host = FakeSideagent(new_sock)
        try:
            self.holder._notify_heartbeat_host_now("idle", "end_turn")
            self.assertEqual([m["op"] for m in new_host.prompts], ["worker_event"],
                             "the next event reaches the replacement Host")
        finally:
            new_host.close()
        self.holder.heartbeat_host = None
        unbound = self.holder.op_rebind_heartbeat_host({"target": new})
        self.assertEqual(unbound["error"]["code"], "no-heartbeat-host")

    def test_record_advertises_features_and_big_state_file_is_read(self) -> None:
        self.holder.write_record()
        record = json.loads((Path(self.holder.args.record_dir) / "record.json").read_text())
        self.assertIn("heartbeat-state/2", record["holder_features"])
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        path.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/2", "body": "VIEW",
                                    "state": {"pad": "p" * 300000}}), encoding="utf-8")
        self.assertEqual(holder_module.heartbeat_prompt_body(path), ("VIEW", None))
        path.write_text(json.dumps({"body": "x" * 70000}), encoding="utf-8")
        body, defect = holder_module.heartbeat_prompt_body(path)
        self.assertIsNone(body)
        self.assertIn("65536", defect)

    def test_routine_events_go_to_the_bound_sideagent_not_the_host(self) -> None:
        self.write_state([])
        self.live_sideagent()
        receipt = self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(self.agent.prompts(), [], "the Host is not woken for a routine event")
        self.assertEqual(len(self.fake.prompts), 1)
        relay = self.fake.prompts[0]
        self.assertEqual(relay["op"], "prompt")
        self.assertEqual(relay["params"]["expected_holder_instance_id"], "side-1")
        self.assertIn("codex-KT-i1-a", relay["params"]["text"])
        self.assertEqual(receipt["relay"]["relayed"], 1)
        # The Sideagent's own turn end wakes the Host once (attention unseen) ...
        self.sideagent_end(9, 1)
        self.assertEqual(len(self.agent.prompts()), 1)
        self.assertNotIn("codex/codex-KT-i1-a/idle/5",
                         [item["event_id"] for item in self.holder.pending_worker_events],
                         "the relayed event is confirmed by the Sideagent's turn end")
        self.finish_host_turn()
        # ... and later quiet turn ends do not.
        self.event("codex-KT-i1-b", "idle", 6)
        self.sideagent_end(12, 2)
        self.assertEqual(len(self.agent.prompts()), 1, "unchanged attention does not wake the Host")
        self.assertEqual(self.holder.pending_worker_events, [])
        self.write_state([{"kind": "decisions", "id": "d1", "why": "host-decision"}])
        self.sideagent_end(15, 3)
        self.assertEqual(len(self.agent.prompts()), 2, "a new Host judgment wakes the Host")

    def test_only_the_turn_that_carried_a_relay_confirms_it(self) -> None:
        self.write_state([])
        self.live_sideagent()
        self.event("codex-KT-i1-a", "idle", 5)
        event_id = "codex/codex-KT-i1-a/idle/5"
        pending = lambda: [item["event_id"] for item in self.holder.pending_worker_events]
        self.event("zcode-KT-sideagent", "idle", 7)
        self.sideagent_end(8, 99)
        self.sideagent_end(9, 1, holder="side-0")
        self.assertIn(event_id, pending(), "a generic, late or foreign turn end confirms nothing")
        self.sideagent_end(10, 1)
        self.assertNotIn(event_id, pending())

    def unconsumed_relay_returns_to_the_host(self, outcome: str) -> None:
        self.write_state([])
        self.live_sideagent()
        self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(self.agent.prompts(), [])
        self.sideagent_end(9, 1, outcome=outcome)
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1, "the Host is woken once")
        self.assertIn("codex-KT-i1-a", prompts[0], "the unconsumed worker event is the Host's")
        self.assertIn("zcode-KT-sideagent", prompts[0], "and so is the failed turn end")
        self.assertEqual(len(self.fake.prompts), 1, "it is not relayed to the same Sideagent again")
        log = (Path(self.holder.args.record_dir) / "events.jsonl").read_text()
        self.assertIn("worker_event_relay_returned", log)
        self.finish_host_turn()
        self.assertEqual(self.holder.pending_worker_events, [], "delivered exactly once")

    def test_failed_maintenance_turn_returns_events_to_the_host(self) -> None:
        self.unconsumed_relay_returns_to_the_host("turn_failed")

    def test_cancelled_maintenance_turn_returns_events_to_the_host(self) -> None:
        self.unconsumed_relay_returns_to_the_host("turn_canceled")

    def test_a_sideagent_turn_end_names_its_holder_and_turn(self) -> None:
        args = argparse.Namespace(record_dir=str(self.side_dir), socket=str(self.side_dir / "s.sock"),
                                  platform="zcode", session="zcode-KT-sideagent", repo=str(self.repo),
                                  init_meta="", command="stub")
        side = holder_module.Holder(args)
        side.agent = StubAgent()
        side.session_role = "sideagent"
        side.heartbeat_host = {"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                               "socket": str(self.side_dir / "host.sock")}
        sent: list[dict] = []
        side._carrier_send = lambda target, params, still_owed=None: sent.append(params) or {"staged": True}
        side.turn.update({"active": True, "request_id": 7, "fingerprint": "sha256:turn-7",
                          "written_at": "now", "mutation_status": "running", "stop_reason": None})
        side.on_prompt_response(7, {"result": {"stopReason": "end_turn"}})
        self.assertEqual(len(sent), 1)
        self.assertEqual((sent[0]["kind"], sent[0]["holder_instance_id"], sent[0]["turn_fingerprint"],
                          sent[0]["turn_outcome"]),
                         ("idle", side.holder_instance_id, "sha256:turn-7", "turn_completed"))
        side.turn.update({"active": True, "request_id": 8, "fingerprint": "sha256:turn-8"})
        side.on_prompt_response(8, {"result": {"stopReason": "cancelled"}})
        self.assertEqual((len(sent), sent[1]["turn_outcome"]), (2, "turn_canceled"),
                         "a cancelled maintenance turn is reported too")

    def test_direct_replacement_moves_open_relays_to_the_new_sideagent(self) -> None:
        self.write_state([])
        self.live_sideagent()
        self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(len(self.fake.prompts), 1)
        # The Host binds a new Sideagent in the same session at once: no
        # interval without a binding is ever observed.
        state = {"sideagent": {"platform": "zcode", "session": "zcode-KT-sideagent",
                               "holder_instance_id": "side-2", "state": "active"}}
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = json.loads(path.read_text())
        doc["state"] = state
        path.write_text(json.dumps(doc), encoding="utf-8")
        self.live_sideagent(holder="side-2")
        self.event("codex-KT-i1-b", "idle", 6)
        self.assertEqual(len(self.fake.prompts), 2)
        second = self.fake.prompts[1]
        self.assertEqual(second["params"]["expected_holder_instance_id"], "side-2")
        self.assertIn("codex-KT-i1-a", second["params"]["text"], "the stranded relay moved")
        self.assertIn("codex-KT-i1-b", second["params"]["text"])
        log = (Path(self.holder.args.record_dir) / "events.jsonl").read_text()
        self.assertIn("worker_event_relay_transferred", log)
        self.assertEqual(self.agent.prompts(), [], "the Host is not woken for the transfer")
        # The old Sideagent's late turn end no longer settles anything.
        self.sideagent_end(9, 1, holder="side-1")
        self.assertIn("codex/codex-KT-i1-a/idle/5",
                      [item["event_id"] for item in self.holder.pending_worker_events])
        self.sideagent_end(10, 2, holder="side-2")
        self.assertNotIn("codex/codex-KT-i1-a/idle/5",
                         [item["event_id"] for item in self.holder.pending_worker_events])

    def test_busy_sideagent_keeps_events_and_dead_sideagent_falls_back_to_host(self) -> None:
        self.write_state([])
        self.live_sideagent(busy=True)
        self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(self.agent.prompts(), [])
        self.assertEqual(len(self.holder.pending_worker_events), 1, "busy is not lost")
        (self.side_dir / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "repo": str(self.repo), "state": "stopped",
            "holder_instance_id": "side-1", "holder_pid": os.getpid()}), encoding="utf-8")
        self.event("zcode-KT-sideagent", "terminated", 7)
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1)
        self.assertIn("codex-KT-i1-a", prompts[0], "the Host takes over undelivered events")
        self.assertIn("zcode-KT-sideagent", prompts[0])

    def test_without_a_binding_every_event_reaches_the_host(self) -> None:
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(
            json.dumps({"body": json.dumps({"project": {}})}), encoding="utf-8")
        self.event("codex-KT-i1-a", "idle", 5)
        self.assertEqual(len(self.agent.prompts()), 1)


class ProcessPreservation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-stop-")
        self.dir = Path(self.tmp.name)
        self.child = subprocess.Popen(["sleep", "30"], start_new_session=True)
        time.sleep(0.2)

    def tearDown(self) -> None:
        self.child.kill()
        self.child.wait()
        self.tmp.cleanup()

    def spawn_record(self) -> None:
        entry = {"pid": self.child.pid, "pgid": self.child.pid, "spawned_at": int(time.time() * 1000)}
        (self.dir / "children.jsonl").write_text(json.dumps(entry) + "\n", encoding="utf-8")

    def child_start(self) -> str:
        table = acp_module.run_ps(["pid", "pgid", "state", "lstart"], env=acp_module.PS_ENV)
        for line in table.stdout.splitlines():
            fields = line.split(None, 3)
            if fields and fields[0] == str(self.child.pid):
                return fields[3].strip()
        self.fail("child not in the process table")

    def test_sideagent_record_spares_runner_holder_groups(self) -> None:
        self.spawn_record()
        host = acp_module.recorded_groups({"session_role": "host"}, self.dir)
        side = acp_module.recorded_groups({"session_role": "sideagent"}, self.dir)
        self.assertIn(self.child.pid, host, "a Host stop still sweeps its recorded inner sessions")
        self.assertNotIn(self.child.pid, side, "a Sideagent stop spares the workers it dispatched")
        live = {self.child.pid: [self.child.pid]}
        self.assertEqual(holder_module.dispatched_worker_groups(self.dir / "children.jsonl", live),
                         {self.child.pid})

    def test_other_children_of_a_sideagent_are_still_swept(self) -> None:
        record = {"session_role": "sideagent",
                  "agent_child_groups": {str(self.child.pid): {str(self.child.pid): self.child_start()}}}
        side = acp_module.recorded_groups(record, self.dir)
        self.assertIn(self.child.pid, side, "a detached agent child that is no Runner holder is swept")
        self.assertEqual(holder_module.dispatched_worker_groups(self.dir / "children.jsonl", {}), set())


FAKE_WORKER_HOLDER = """
import subprocess, sys, time
pids = sys.argv[sys.argv.index("--pids") + 1]
tool = "import subprocess,sys,time;t=subprocess.Popen(['sleep','60'],start_new_session=True);" \\
       "open(sys.argv[1],'w').write(str(t.pid));time.sleep(60)"
native = subprocess.Popen([sys.executable, "-c", tool, pids + ".tool"], start_new_session=True)
open(pids, "w").write(str(native.pid))
time.sleep(60)
"""


class RealAgent(StubAgent):
    """A live Sideagent agent process for the holder's own stop sweep."""

    def __init__(self) -> None:
        super().__init__()
        self.proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
        threading.Thread(target=lambda: (self.proc.wait(), self.exited.set()), daemon=True).start()


class NestedWorkerTopology(unittest.TestCase):
    """A worker a Sideagent dispatched is a holder, its native agent in its
    own session, and that agent's tool in another: the whole tree survives
    the Sideagent's stop, cooperative or after its holder died, while the
    Sideagent's unrelated detached child is still swept."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-tree-")
        root = Path(self.tmp.name)
        self.side_dir = root / "side"
        self.worker_dir = root / "worker"
        self.side_dir.mkdir()
        self.worker_dir.mkdir()
        script = root / "kaola-acp-holder.py"
        script.write_text(FAKE_WORKER_HOLDER, encoding="utf-8")
        pids = root / "pids"
        self.groups: list[int] = []
        self.holder = subprocess.Popen([sys.executable, str(script), "--record-dir", str(self.worker_dir),
                                        "--socket", str(root / "w.sock"), "--pids", str(pids)],
                                       start_new_session=True)
        spawned_at = int(time.time() * 1000)
        self.groups.append(self.holder.pid)
        deadline = time.time() + 10
        while time.time() < deadline and not (pids.exists() and Path(f"{pids}.tool").exists()
                                              and Path(f"{pids}.tool").read_text()):
            time.sleep(0.05)
        self.native = int(pids.read_text())
        self.tool = int(Path(f"{pids}.tool").read_text())
        self.orphan = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.unrelated = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.groups += [self.native, self.tool, self.orphan.pid, self.unrelated.pid]
        time.sleep(0.2)
        starts = self.starts()
        (self.side_dir / "children.jsonl").write_text(json.dumps(
            {"pid": self.holder.pid, "pgid": self.holder.pid, "spawned_at": spawned_at}) + "\n",
            encoding="utf-8")
        # The worker's own record attests its agent and a tool group whose
        # parent already left the tree.
        (self.worker_dir / "record.json").write_text(json.dumps({
            "holder_pid": self.holder.pid, "agent_pgid": self.native,
            "agent_started": holder_module.start_epoch(starts[self.native]),
            "agent_child_groups": {str(self.tool): {str(self.tool): starts[self.tool]},
                                   str(self.orphan.pid): {str(self.orphan.pid): starts[self.orphan.pid]}}}),
            encoding="utf-8")
        # What the Sideagent's holder noted from its agent's process tree.
        self.noted = {pgid: {pgid: starts[pgid]} for pgid in self.groups}

    def tearDown(self) -> None:
        for pgid in self.groups:
            try:
                os.killpg(pgid, 9)
            except OSError:
                pass
        for proc in (self.holder, self.orphan, self.unrelated):
            proc.wait()
        self.tmp.cleanup()

    def starts(self) -> dict[int, str]:
        return {pid: started for pid, _, _, started in holder_module.process_table()}

    def alive(self, pid: int) -> bool:
        return holder_module.process_alive(pid)

    def test_dead_holder_cleanup_keeps_the_whole_worker_tree(self) -> None:
        record = {"session_role": "sideagent",
                  "agent_child_groups": {str(g): {str(p): s for p, s in m.items()} for g, m in self.noted.items()}}
        for verified_only in (False, True):
            side = acp_module.recorded_groups(record, self.side_dir, verified_only=verified_only)
            self.assertEqual(side, [self.unrelated.pid], f"verified_only={verified_only}")
        host = acp_module.recorded_groups(dict(record, session_role="host"), self.side_dir)
        self.assertEqual(sorted(host), sorted(self.groups), "a Host stop keeps sweeping everything")

    def test_cooperative_stop_keeps_the_whole_worker_tree(self) -> None:
        live = {pgid: [pgid] for pgid in self.groups}
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live),
                         {self.holder.pid, self.native, self.tool, self.orphan.pid})
        args = argparse.Namespace(record_dir=str(self.side_dir), socket=str(self.side_dir / "s.sock"),
                                  platform="zcode", session="zcode-KT-sideagent", repo=self.tmp.name,
                                  init_meta="", command="stub")
        holder = holder_module.Holder(args)
        holder.agent = RealAgent()
        holder.session_role = "sideagent"
        holder.agent_child_groups = {pgid: dict(members) for pgid, members in self.noted.items()}
        holder._terminate_group(False)
        self.groups.append(holder.agent.proc.pid)
        self.assertEqual(holder.swept_child_pgids, [self.unrelated.pid])
        for pid in (self.holder.pid, self.native, self.tool, self.orphan.pid):
            self.assertTrue(self.alive(pid), f"worker process {pid} survived the Sideagent stop")
        self.unrelated.wait(timeout=5)
        self.assertFalse(self.alive(self.unrelated.pid))

    def test_a_foreign_record_or_lost_spawn_line_protects_nothing(self) -> None:
        (self.worker_dir / "record.json").write_text(json.dumps({"holder_pid": 1}), encoding="utf-8")
        live = {pgid: [pgid] for pgid in self.groups}
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live),
                         {self.holder.pid, self.native, self.tool},
                         "without its own record only the live descendants are the worker")
        (self.side_dir / "children.jsonl").write_text("", encoding="utf-8")
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live),
                         set(), "a command line alone is never worker identity")


class CarrierAnchor(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-anchor-")
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.repo_text = acp_module.canonical_dir(str(self.repo))
        self.args = argparse.Namespace(record_root=str(root / "records"), platform="codex",
                                       session="codex-KT-i3-worker")
        digest = hashlib.sha256(self.repo_text.encode()).hexdigest()[:16]
        self.side_dir = Path(self.args.record_root) / "zcode" / "zcode-KT-sideagent" / digest
        self.host_dir = Path(self.args.record_root) / "zcode" / "zcode-KT-orchestrator-main" / digest
        self.side_dir.mkdir(parents=True)
        self.host_dir.mkdir(parents=True)
        self.dispatcher = {"holder_instance_id": "side-1", "platform": "zcode",
                           "repo": self.repo_text, "session": "zcode-KT-sideagent"}
        (self.side_dir / "record.json").write_text(json.dumps({
            "session_role": "sideagent", "holder_instance_id": "side-1", "holder_pid": os.getpid(),
            "heartbeat_host": {"platform": "zcode", "session": "zcode-KT-orchestrator-main",
                               "repo": self.repo_text}}), encoding="utf-8")
        (self.host_dir / "record.json").write_text(json.dumps({
            "session_role": "host", "session": "zcode-KT-orchestrator-main",
            "holder_instance_id": "host-2", "holder_pid": os.getpid()}), encoding="utf-8")
        self.sock = acp_module.sock_path_for_directory(self.host_dir)
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        self.sock.touch()

    def tearDown(self) -> None:
        try:
            self.sock.unlink()
        except OSError:
            pass
        self.tmp.cleanup()

    def test_sideagent_dispatch_notifies_its_bound_host(self) -> None:
        target, failed = acp_module.sideagent_host_anchor(self.args, self.repo_text, self.dispatcher)
        self.assertIsNone(failed)
        self.assertEqual((target["platform"], target["session"]), ("zcode", "zcode-KT-orchestrator-main"))
        self.assertEqual(target["socket"], str(self.sock))

    def test_a_host_dispatcher_is_not_re_anchored(self) -> None:
        host = dict(self.dispatcher, session="zcode-KT-orchestrator-main", holder_instance_id="host-2")
        self.assertIsNone(acp_module.sideagent_host_anchor(self.args, self.repo_text, host))

    def test_missing_host_is_a_named_failure_not_a_silent_unbound_start(self) -> None:
        self.sock.unlink()
        target, failed = acp_module.sideagent_host_anchor(self.args, self.repo_text, self.dispatcher)
        self.assertIsNone(target)
        self.assertIn("socket", failed)

    def test_an_unbound_sideagent_falls_through_to_the_dispatcher_rows(self) -> None:
        record = json.loads((self.side_dir / "record.json").read_text())
        record["heartbeat_host"] = None
        (self.side_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
        self.assertIsNone(acp_module.sideagent_host_anchor(self.args, self.repo_text, self.dispatcher))

    def rebind(self, dispatcher: dict) -> tuple[dict, list]:
        calls: list = []
        original = acp_module.op_or_holder_lost

        def capture(args, repo, directory, op, params, timeout):
            calls.append((op, params))
            return {"rebound": True}
        acp_module.op_or_holder_lost = capture
        previous = os.environ.get("KAOLA_ACP_DISPATCHER")
        os.environ["KAOLA_ACP_DISPATCHER"] = json.dumps(dispatcher)
        try:
            args = argparse.Namespace(**vars(self.args), expected_holder_instance_id="seat-1")
            receipt = acp_module.command_rebind_host(args, self.repo_text, Path(self.tmp.name))
        finally:
            acp_module.op_or_holder_lost = original
            if previous is None:
                os.environ.pop("KAOLA_ACP_DISPATCHER", None)
            else:
                os.environ["KAOLA_ACP_DISPATCHER"] = previous
        return receipt, calls

    def test_rebind_host_anchors_a_seat_to_the_live_host_running_it(self) -> None:
        host = dict(self.dispatcher, session="zcode-KT-orchestrator-main", holder_instance_id="host-2")
        receipt, calls = self.rebind(host)
        self.assertEqual(receipt["action"], "rebind-host")
        self.assertEqual(len(calls), 1)
        op, params = calls[0]
        self.assertEqual(op, "rebind_heartbeat_host")
        self.assertEqual(params["target"]["session"], "zcode-KT-orchestrator-main")
        self.assertEqual(params["target"]["socket"], str(self.sock))
        self.assertEqual(params["host_holder_instance_id"], "host-2")
        self.assertEqual(params["expected_holder_instance_id"], "seat-1")

    def test_rebind_host_refuses_a_non_host_or_stale_caller(self) -> None:
        receipt, calls = self.rebind(self.dispatcher)
        self.assertEqual(receipt["result"], "refused", "a Sideagent cannot take a seat's carrier")
        self.assertIn("not a Host", receipt["detail"])
        stale = dict(self.dispatcher, session="zcode-KT-orchestrator-main", holder_instance_id="host-1")
        receipt, more = self.rebind(stale)
        self.assertEqual(receipt["result"], "refused", "only the live Host instance itself")
        self.assertIn("holder_instance_id", receipt["detail"])
        self.assertEqual(calls + more, [], "a refusal never reaches the seat")


class HostReanchorLive(unittest.TestCase):
    """Real Runner CLI, real holders, hermetic fake ZCode: a replacement Host
    takes a healthy worker's carrier without restarting the worker."""

    def test_replacement_host_takes_a_healthy_worker_in_place(self) -> None:
        hb = load("kaola_zcode_heartbeat_255", REPO / "tests" / "contract" / "test-zcode-heartbeat-contract.py")
        sandbox = hb.Sandbox("i255-reanchor")
        try:
            tag = os.urandom(3).hex()
            old, new = f"zcode-KT-orchestrator-a{tag}", f"zcode-KT-orchestrator-b{tag}"
            sandbox.start(old, "basic")
            sandbox.write_prompt_file("HEARTBEAT: Issue #255 re-anchor.")
            worker = sandbox.session()
            repo = os.path.realpath(str(sandbox.repo))
            sandbox.start(worker, "basic",
                          heartbeat_host={"platform": "zcode", "session": old, "repo": repo})
            read = lambda session: json.loads((sandbox.record_dir(session) / "record.json").read_text())
            before = read(worker)
            self.assertEqual(sandbox.cli("stop", session=old).get("stopped"), True)
            sandbox.start(new, "basic")
            host = read(new)
            dispatcher = json.dumps({"holder_instance_id": host["holder_instance_id"], "platform": "zcode",
                                     "repo": repo, "session": new})
            receipt = sandbox.cli("rebind-host", session=worker, KAOLA_ACP_DISPATCHER=dispatcher)
            self.assertIs(receipt.get("rebound"), True, receipt)
            after = read(worker)
            for key in ("holder_pid", "holder_instance_id", "agent_pid", "acp_session_id"):
                self.assertEqual(after[key], before[key], f"{key} survives the re-anchor")
            self.assertEqual(after["heartbeat_host"]["session"], new)
            reply = sandbox.cli("send", "--text", "work after the Host changed", session=worker)
            self.assertEqual(reply.get("outcome"), "turn_completed")
            hb.wait_until(lambda: hb.events_of_kind(sandbox.record_dir(new), "worker_event"), 10,
                          "the worker's next turn end reaches the replacement Host")
        finally:
            sandbox.cleanup()


class RenderedGuidance(unittest.TestCase):
    """The generated Skills carry the lifecycle roles and commands the tool
    implements, inside their byte budgets."""

    ORCH = REPO / "skills" / "kaola-project-runner"
    DELEGATOR = REPO / "skills" / "kaola-delegator"

    def test_lifecycle_reference_is_generated_linked_and_bounded(self) -> None:
        template = (REPO / "templates/orchestrator/references/lifecycle-state.md").read_bytes()
        generated = (self.ORCH / "references/lifecycle-state.md").read_bytes()
        self.assertEqual(template, generated)
        self.assertLessEqual(len(generated), 8192)
        text = generated.decode()
        for term in ("kaola-heartbeat-prompt/2", "--expect-rev", "exits 3", "--host-turn",
                     "`attention`", "binding-superseded", "sideagent-relay/1", "heartbeat-state/2",
                     "record-retired", "host-view-too-large", "carrier-limit",
                     "heartbeat-prompt.v1-<sha12>.json", "`unverified`", "writer-refused",
                     "No synchronous Sideagent round trip"):
            self.assertIn(term, text)
        for kind in dispatch_module.RECORD_KINDS + dispatch_module.SECTIONS:
            self.assertIn(kind, text)
        skill = (self.ORCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("](references/lifecycle-state.md)", skill)
        self.assertLessEqual(len(skill.encode()), 17408)
        dispatch = (self.ORCH / "references/dispatch-collect.md").read_text(encoding="utf-8")
        self.assertIn("[lifecycle-state.md](lifecycle-state.md)", dispatch)
        self.assertIn("`state-managed`", dispatch)
        self.assertIn("`requirement-unmet`", dispatch)
        self.assertNotIn("It does not start other workers, dispatch", dispatch)
        skeleton = (self.ORCH / "references/heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertNotIn("Sideagent 仅提案", skeleton)
        self.assertIn("lifecycle-state.md", skeleton)

    def test_delegator_timer_sentence_matches_the_tool(self) -> None:
        report = (self.DELEGATOR / "references/inquiry-report.md").read_text(encoding="utf-8")
        locator = dispatch_module.TIMER_LOCATOR.format(repo="<repo>", target="<target>")
        self.assertIn(f"`{locator}`", report)
        self.assertIn("view --role delegator", report)
        for part in ("User special requirements", "Special situations", "Tasks in progress",
                     "Tasks to do", "outcomes and next steps"):
            self.assertIn(part, report)
        skill = (self.DELEGATOR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("](references/inquiry-report.md)", skill)
        self.assertLessEqual(len(skill.encode()), 4096)
        snapshot = (self.DELEGATOR / "references/snapshot.md").read_text(encoding="utf-8")
        self.assertIn("[inquiry-report.md](inquiry-report.md)", snapshot)
        self.assertLessEqual(len(snapshot.encode()), 8192)


if __name__ == "__main__":
    unittest.main(verbosity=2)
