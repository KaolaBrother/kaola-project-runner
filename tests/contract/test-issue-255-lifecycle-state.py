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
import textwrap
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
CITE = '{"path":"README.md","locator":"README.md"}'


class StateProject(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i255-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
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
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "4", "--evidence", "commit c1",
                               "--cite", CITE)
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertNotIn("t1", doc["state"]["tasks"])
        self.assertEqual(out["value"]["cite"], {"path": "README.md", "locator": "README.md"})
        self.assertNotIn("evidence", out["value"])
        self.assertFalse(doc["state"].get("retired"))
        code, out = self.update("sideagent", "tasks", "t1", {"stage": "doing"}, "--expect-rev", "4")
        self.assertEqual(out["reason"], "record-retired", "an old revision does not restore the settled task")
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
                                           "--expect-rev", "1", "--evidence", "merged c2", "--cite", CITE, *extra)
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

    def test_a_live_seat_can_be_handed_to_a_continuing_task_with_its_evidence(self) -> None:
        self.init()
        self.update("host", "tasks", "t5", {"stage": "done", "goal": "g", "dispatch": ["i7"],
                                             "sessions": ["codex-KT-i7-a"], "verdict": {"value": "accepted"}})
        self.update("host", "tasks", "t6", {"stage": "doing", "goal": "next", "dispatch": ["i8"]})
        index = self.repo / "index.json"
        index.write_text(json.dumps({"items": [{"item_id": "i7", "status": "returned",
                                                "session": "codex-KT-i7-a"}]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [{"session": "codex-KT-i7-a", "state": "ready"}]}),
                        encoding="utf-8")
        retire = lambda *extra: self.state("retire", "--file", str(self.file), "--writer", "sideagent",
                                           "--source", "s", "--kind", "tasks", "--id", "t5",
                                           "--expect-rev", "1", "--evidence", "seat reused for t6", "--cite", CITE,
                                           *extra)
        code, out = retire("--index", str(index), "--live", str(live))
        self.assertEqual(out["reason"], "retire-unmet", "a live seat is not a stop")
        self.assertIn("--handoff", out["detail"])
        for target in ("t5", "nope"):
            code, out = retire("--handoff", target)
            self.assertEqual(out["reason"], "invalid-input", target)
        code, out = retire("--handoff", "t6")
        self.assertEqual(code, 0, out)
        doc = self.doc()
        self.assertNotIn("t5", doc["state"]["tasks"])
        self.assertEqual((out["value"]["handed_to"], out["value"]["seats"], out["value"]["dispatch"],
                          out["value"]["cite"]["path"]),
                         ("t6", ["codex-KT-i7-a"], ["i7"], "README.md"))
        self.assertNotIn("evidence", out["value"])
        self.assertFalse(doc["state"].get("retired"))
        receiver = doc["state"]["tasks"]["t6"]
        self.assertEqual((receiver["dispatch"], receiver["sessions"], receiver["rev"]),
                         (["i8", "i7"], ["codex-KT-i7-a"], 2), "the receiver owns the seat now")
        self.update("host", "tasks", "t6", {"stage": "done", "verdict": {"value": "accepted"}},
                    "--expect-rev", "2")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                               "--kind", "tasks", "--id", "t6", "--expect-rev", "3", "--evidence", "e",
                               "--index", str(index), "--live", str(live))
        self.assertEqual(out["reason"], "retire-unmet", "the handed seat still needs its stop")

    def test_a_known_holder_in_any_seat_shape_survives_a_handoff(self) -> None:
        self.init()
        live = self.repo / "live.json"
        rows = lambda holder: live.write_text(json.dumps({"rows": [
            {"session": name, "state": "stopped", "holder_instance_id": holder}
            for name in ("worker-a", "worker-b")]}), encoding="utf-8")
        accepted = {"stage": "done", "goal": "g", "verdict": {"value": "accepted"}}
        self.update("host", "tasks", "direct", {**accepted, "session": "worker-a",
                                                "holder_instance_id": "owned-a"})
        self.update("host", "tasks", "object", {**accepted, "sessions": [
            {"session": "worker-b", "holder_instance_id": "owned-b", "evidence": "start-receipt"}]})
        self.update("host", "tasks", "next", {"stage": "doing", "goal": "continue"})
        retire = lambda ident, rev, *extra: self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s", "--kind", "tasks",
            "--id", ident, "--expect-rev", rev, "--evidence", "e", "--cite", CITE, *extra)
        rows("foreign")
        for ident in ("direct", "object"):
            code, out = retire(ident, "1", "--live", str(live))
            self.assertEqual(out["reason"], "retire-unmet", f"{ident}: a foreign stop proves nothing")
            self.assertIn("not the recorded owned-", out["detail"])
        self.assertEqual(retire("direct", "1", "--handoff", "next")[0], 0)
        self.assertEqual(retire("object", "1", "--handoff", "next")[0], 0)
        receiver = self.doc()["state"]["tasks"]["next"]
        self.assertIn({"session": "worker-b", "holder_instance_id": "owned-b", "evidence": "start-receipt",
                       "handed_from": "object"}, receiver["sessions"])
        self.assertIn({"session": "worker-a", "holder_instance_id": "owned-a", "handed_from": "direct"},
                      receiver["sessions"])
        self.update("host", "tasks", "next", accepted, "--expect-rev", str(receiver["rev"]))
        rev = str(self.doc()["state"]["tasks"]["next"]["rev"])
        code, out = retire("next", rev, "--live", str(live))
        self.assertEqual(out["reason"], "retire-unmet", "a handoff keeps each recorded holder")
        self.assertIn("worker-a is stopped under holder foreign", out["detail"])
        self.assertIn("worker-b is stopped under holder foreign", out["detail"])
        self.update("host", "tasks", "next", {"sessions": receiver["sessions"] + [
            {"session": "worker-a", "holder_instance_id": "other-a"}]}, "--expect-rev", rev)
        rev = str(self.doc()["state"]["tasks"]["next"]["rev"])
        live.write_text(json.dumps({"rows": [
            {"session": "worker-a", "state": "stopped", "holder_instance_id": "owned-a"},
            {"session": "worker-b", "state": "stopped", "holder_instance_id": "owned-b"}]}), encoding="utf-8")
        code, out = retire("next", rev, "--live", str(live))
        self.assertIn("conflicting recorded holders other-a, owned-a", out.get("detail", ""),
                      "two recorded holders stay unresolved, never a name-only match")
        receiver = self.doc()["state"]["tasks"]["next"]
        self.update("host", "tasks", "next", {"sessions": receiver["sessions"][:-1]}, "--expect-rev", rev)
        rev = str(self.doc()["state"]["tasks"]["next"]["rev"])
        code, out = retire("next", rev, "--live", str(live))
        self.assertEqual(code, 0, out)

    def test_moving_past_review_without_a_verdict_keeps_the_host_asked(self) -> None:
        self.init()
        why = lambda: [(row["id"], row["why"]) for row in json.loads(self.doc()["body"])["attention"]]
        rev = lambda: str(self.doc()["state"]["tasks"]["t7"]["rev"])
        self.update("host", "tasks", "t7", {"stage": "review", "goal": "g"})
        self.assertEqual(why(), [("t7", "awaiting-verdict")])
        for stage in ("closeout", "done"):
            code, out = self.update("sideagent", "tasks", "t7", {"stage": stage}, "--expect-rev", rev())
            self.assertEqual(code, 0, out)
            self.assertEqual(why(), [("t7", "verdict-missing")], stage)
        self.update("host", "tasks", "t7", {"verdict": {"value": "repair"}}, "--expect-rev", rev())
        self.assertEqual(why(), [("t7", "verdict-missing"), ("t7", "delivery-open")],
                         "repair does not close a done task, and the goal stays open")
        for value, stage in (("partial", "closeout"), ("cancelled", "done"), ("accepted", "done")):
            self.update("host", "tasks", "t7", {"stage": stage, "verdict": {"value": value}},
                        "--expect-rev", rev())
            self.assertEqual(why(), [], f"{value} at {stage} is a judgment")

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
        self.update("host", "decisions", "d1", {"answer": "yes"}, "--expect-rev", "2")
        body = json.loads(self.doc()["body"])
        self.assertEqual([row for row in body["attention"] if row["id"] == "d1"], [])

    def test_a_repair_verdict_does_not_answer_the_next_review(self) -> None:
        self.init()
        fingerprint = lambda: holder_module.attention_fingerprint(self.doc()["body"])
        self.update("host", "tasks", "t3", {"stage": "review", "goal": "g"})
        self.update("host", "tasks", "t3", {"verdict": {"value": "repair", "why": "P1"}}, "--expect-rev", "1")
        self.assertEqual([(row["id"], row["why"]) for row in json.loads(self.doc()["body"])["attention"]],
                         [("t3", "delivery-open")])
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

    def test_every_repeated_repair_result_is_new_attention(self) -> None:
        self.init()
        fingerprint = lambda: holder_module.attention_fingerprint(self.doc()["body"])
        rev = lambda: str(self.doc()["state"]["tasks"]["t4"]["rev"])
        self.update("host", "tasks", "t4", {"stage": "review", "goal": "g", "evidence": ["c1"]})
        seen = [fingerprint()]
        for round_no in (1, 2, 3):
            # The Host's seen fingerprint is taken before its own review writes.
            code, out = self.update("host", "tasks", "t4", {"verdict": {
                "value": "repair", "why": "P1", "host_turn": f"review-round-{round_no}"}}, "--expect-rev", rev())
            self.assertEqual(code, 0, out)
            self.update("sideagent", "tasks", "t4", {"stage": "doing"}, "--expect-rev", rev())
            code, out = self.update("sideagent", "tasks", "t4",
                                    {"stage": "review", "evidence": [f"c{round_no + 1}"]}, "--expect-rev", rev())
            self.assertEqual(code, 0, out)
            rows = json.loads(self.doc()["body"])["attention"]
            self.assertEqual([(r["why"], r.get("prior_verdict")) for r in rows], [("awaiting-verdict", "repair")])
            self.assertNotIn(fingerprint(), seen, f"repair result {round_no} wakes the Host")
            seen.append(fingerprint())
        code, out = self.update("sideagent", "tasks", "t4", {"evidence": ["c4"]}, "--expect-rev", rev())
        self.assertEqual(code, 0, out)
        self.assertEqual(fingerprint(), seen[-1], "a rewrite of the same result is metadata only")
        self.assertEqual(self.doc()["state"]["tasks"]["t4"]["rev"], 11)
        code, out = self.update("sideagent", "tasks", "t4", {}, "--expect-rev", rev())
        self.assertEqual((code, fingerprint()), (0, seen[-1]), "an empty update stays quiet")

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
        self.assertNotIn("index-lost", self.doc()["state"].get("unverified") or {})
        self.assertFalse(self.doc()["state"].get("retired"))

    def test_a_stable_fault_id_recurs_but_a_stale_event_does_not(self) -> None:
        self.init()
        self.update("sideagent", "alerts", "quota-codex", {"level": "warn", "summary": "limit"})
        self.state("retire", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
                   "--kind", "alerts", "--id", "quota-codex", "--expect-rev", "1", "--evidence", "reset")
        self.assertNotIn("quota-codex", self.doc()["state"]["alerts"])
        self.assertFalse(self.doc()["state"].get("retired"))
        code, out = self.update("sideagent", "alerts", "quota-codex", {"level": "warn", "summary": "limit"},
                                "--expect-rev", "1")
        self.assertEqual(out["reason"], "record-retired", "an old revision does not restore the cleared alert")
        code, out = self.update("sideagent", "alerts", "quota-codex",
                                {"level": "warn", "summary": "limit again"})
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["alerts"]["quota-codex"]["summary"], "limit again")
        self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g", "verdict": {"value": "cancelled"}})
        self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t1", "--expect-rev", "1", "--evidence", "dropped")
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "g"}, "--expect-rev", "1")
        self.assertEqual(out["reason"], "record-retired", "an old revision does not restore the settled task")
        code, out = self.update("host", "tasks", "t1", {"stage": "todo", "goal": "new duty"})
        self.assertEqual(code, 0, out)
        self.assertNotIn("verdict", self.doc()["state"]["tasks"]["t1"])

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
        self.assertEqual(out["value"]["writer"], "host:codex-KT-i1-worker (role unverified)",
                         "the trace does not claim a verified Host")
        (worker_dir / "record.json").write_text(json.dumps({
            "holder_instance_id": "w-1", "session_role": "host"}), encoding="utf-8")
        code, out = self.update("host", "tasks", "t1", {"goal": "g2"}, "--expect-rev", "1", env=env)
        self.assertEqual(out["value"]["writer"], "host:codex-KT-i1-worker")

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
                                   "--expect-rev", "3", "--evidence", f"commit c{cycle}", "--cite", CITE)
            self.assertEqual(code, 0, out)
            sizes.append(len(self.file.read_bytes()))
        doc = self.doc()
        self.assertEqual(doc["state"]["tasks"], {}, "finished work left the current set")
        self.assertEqual(list(doc["state"]["alerts"]), ["conn-wait"], "a repeat updates one alert")
        self.assertEqual(doc["state"]["alerts"]["conn-wait"]["count"], 40)
        self.assertFalse(doc["state"].get("retired"))
        self.assertNotIn("commit c0", self.file.read_text(encoding="utf-8"))
        self.assertLess(sizes[-1] - sizes[0], 8192, "finished rows do not accumulate a history list")
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

    def test_timer_readback_stays_the_entry_and_can_be_unavailable(self) -> None:
        (self.repo / ".kaola" / "delegator-heartbeat.json").write_text(json.dumps(
            {"cadence": {"timezone": "Asia/Shanghai", "start_local": "08:00", "end_local": "22:00",
                         "interval_minutes": 60}}), encoding="utf-8")
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator", "--body", "not-the-template")
        self.assertEqual((code, out["result"]), (1, "mismatch"))
        self.assertNotRegex(out["expected"], r"\d+ ?min|interval|08:00")
        missing_code, missing = self.state("timer", "--repo", str(self.repo), "--target", "local",
                                           "--entry", "/kaola-delegator")
        self.assertEqual((missing_code, missing["result"]), (0, "unavailable"))

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
        self.assertNotIn("migration", state["recovery"])
        self.assertNotIn("legacy", state["recovery"])
        self.assertNotIn("/abs/old", json.dumps(state))
        self.assertEqual(state["unverified"]["recovery-fields"]["locator"], ["recovery.old_repo"])
        self.assertFalse(list(self.file.parent.glob("heartbeat-prompt.v1-*.json")))
        self.assertFalse(out["report"]["overwrite_detection"]["raised"])
        body = json.loads(doc["body"])
        self.assertEqual(body["authorization"]["classes"], AUTH["classes"])
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
            if key == "custom_duty":
                self.assertNotIn(key, first)
                continue
            self.assertEqual(first[key], value, f"active[0].{key} is kept with its assignment")
        self.assertEqual(state["unverified"]["active-0-fields"]["locator"], ["active[0].custom_duty"])
        self.assertNotIn("active-1-fields", state["unverified"])
        duty = state["tasks"]["duty-1"]
        self.assertEqual(duty["stage"], "todo", "'continue implementation' is not closeout")
        for key in ("next", "wait", "resume_when", "holder", "platform", "boundary"):
            self.assertEqual(duty[key], body["pending"][0][key])
        self.assertNotIn("legacy", duty)
        self.assertNotIn("follow_up", duty)
        self.assertEqual(state["unverified"]["pending-0-fields"]["locator"], ["pending[0].follow_up"])
        self.assertEqual(state["tasks"]["duty-2"]["stage"], "closeout", "an explicit stage is kept")
        self.assertNotIn("duty-2-stage", state["unverified"])
        self.assertEqual(state["sideagent"]["holder_instance_id"], "side-1",
                         "the authorized v1 binding proven by its live holder carries over")
        self.assertEqual(state["sideagent"]["authorization_source"], "owner msg 2")
        self.assertNotIn("v1_host", state["recovery"])
        self.assertNotIn("migration", state["recovery"])
        self.assertIn("host.holder_instance_id", state["unverified"]["host-fields"]["locator"])
        self.assertNotIn("host-0", json.dumps(state["recovery"]))
        self.assertFalse([key for key in state["unverified"] if key.startswith("legacy-")],
                         "host and sideagent have a lifecycle home")
        self.assertFalse(list(self.file.parent.glob("heartbeat-prompt.v1-*.json")))
        self.assertNotEqual(self.file.read_bytes(), raw)

    def test_a_v1_key_named_like_a_v2_field_does_not_take_effect(self) -> None:
        body = {"project": {"code": "KT"}, "authorization": AUTH,
                "pending": [{"duty": "closeout #254", "stage": "done", "verdict": {"value": "accepted"},
                             "dispatch": ["i9"], "keep_open": True}]}
        self.write_legacy(body)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        state = self.doc()["state"]
        task = state["tasks"]["duty-1"]
        for key in ("verdict", "dispatch", "keep_open"):
            self.assertNotIn(key, task, f"v1 {key} is not a v2 decision")
        self.assertNotIn("legacy", task)
        self.assertEqual(sorted(state["unverified"]["pending-0-fields"]["locator"]),
                         ["pending[0].dispatch", "pending[0].keep_open", "pending[0].verdict"])
        attention = json.loads(self.doc()["body"])["attention"]
        self.assertEqual([(row["id"], row["why"]) for row in attention], [("duty-1", "verdict-missing")],
                         "a done duty with no Host verdict asks the Host")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "s",
                               "--kind", "tasks", "--id", "duty-1", "--expect-rev", "1", "--evidence", "x")
        self.assertEqual(out["reason"], "retire-unmet", "the copied v1 verdict accepts nothing")

    def test_a_migrated_task_with_a_known_seat_retires_only_once_it_is_shown_stopped(self) -> None:
        body = {"project": {"code": "KT"}, "authorization": AUTH,
                "active": [{"ref": "#255", "session": "still-working", "holder_instance_id": "h",
                            "next": "deliver work"}]}
        self.write_legacy(body)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        task = self.doc()["state"]["tasks"]["#255"]
        self.assertNotIn("dispatch", task, "no index associates the seat")
        code, out = self.update("host", "tasks", "#255", {"stage": "done", "verdict": {"value": "accepted"}},
                                "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        live = self.repo / "live.json"
        retire = lambda *extra: self.state("retire", "--file", str(self.file), "--writer", "sideagent",
                                           "--source", "s", "--kind", "tasks", "--id", "#255",
                                           "--expect-rev", "2", "--evidence", "host-review", "--cite", CITE, *extra)
        code, out = retire()
        self.assertEqual(out["reason"], "retire-unmet", "acceptance does not prove the seat stopped")
        self.assertIn("still-working needs --live", out["detail"])
        cases = (([{"session": "still-working", "state": "ready", "holder_instance_id": "h"}], "still live"),
                 ([], "not in the live rows"),
                 ([{"session": "still-working", "state": "ready", "holder_instance_id": "h2"}],
                  "association is unresolved"),
                 ([{"session": "still-working", "state": "stopped", "holder_instance_id": "h2"}],
                  "stopped under holder h2"))
        for rows, why in cases:
            live.write_text(json.dumps({"rows": rows}), encoding="utf-8")
            code, out = retire("--live", str(live))
            self.assertEqual(out["reason"], "retire-unmet", why)
            self.assertIn(why, out["detail"])
            self.assertIn("#255", self.doc()["state"]["tasks"], "the cleanup duty stays current")
            code, check = self.state("check", "--file", str(self.file), "--live", str(live))
            self.assertIn("done-seat-open", [p["code"] for p in check["problems"]], why)
        live.write_text(json.dumps({"rows": [{"session": "still-working", "state": "stopped",
                                              "holder_instance_id": "h"}]}), encoding="utf-8")
        code, out = self.state("check", "--file", str(self.file), "--live", str(live))
        self.assertNotIn("done-seat-open", [p["code"] for p in out["problems"]])
        code, out = retire("--live", str(live))
        self.assertEqual(code, 0, out)
        self.assertNotIn("#255", self.doc()["state"]["tasks"])

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
        before = set(self.file.parent.glob("heartbeat-prompt.v1-*.json"))
        body = dict(LEGACY_BODY, project={"code": "KT", "goal": "older writer"})
        self.write_legacy(body)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        self.assertFalse(out["report"]["overwrite_detection"]["raised"])
        self.assertNotIn("state-overwritten", self.doc()["state"]["alerts"])
        self.assertEqual(set(self.file.parent.glob("heartbeat-prompt.v1-*.json")), before)

    def test_interrupted_migration_resumes_from_the_same_raw_evidence(self) -> None:
        raw = self.write_legacy()
        digest = hashlib.sha256(raw).hexdigest()
        stale = self.file.with_name(f"heartbeat-prompt.v1-{digest[:12]}.json")
        stale.write_bytes(raw)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        self.assertIn("live", out["unchecked"], "unchecked sources are named")
        named = [row for row in out["report"]["backups"]["backups"] if row["name"] == stale.name]
        self.assertEqual(named[0]["trusted"], False)
        self.assertEqual(named[0]["deleted"], False)
        self.assertEqual(stale.read_bytes(), raw)
        stale.write_text("other", encoding="utf-8")
        self.write_legacy()
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        self.assertEqual(stale.read_text(encoding="utf-8"), "other")

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
        code, out = self.state("migrate", "--file", str(self.file))
        self.assertEqual(out["result"], "planned", out)
        self.assertGreater(out["report"]["file_bytes"], 65536)
        self.assertEqual(self.file.read_bytes(), raw, "a plan does not write")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        self.assertGreater(out["file_bytes"], 65536)
        self.assertIsNone(self.doc().get("carrier"))
        raw = self.write_legacy(body)
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [{
            "platform": "zcode", "session": "zcode-KT-orchestrator-main", "session_role": "host",
            "repo": str(self.repo), "state": "ready", "holder_instance_id": "host-old",
            "holder_features": []}]}), encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--write", "--live", str(live))
        self.assertEqual(out["reason"], "carrier-limit", out)
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
        # Optional realism: the Sideagent holder's dispatch cursor per relay,
        # and a peer that trickles bytes without ever ending its reply line.
        self.cursor_step: int | None = None
        self.trickle = False
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
                if self.trickle:
                    try:
                        for _ in range(30):
                            connection.sendall(b" ")
                            time.sleep(0.1)
                    except OSError:
                        pass
                    continue
                if self.busy:
                    reply = {"error": {"code": "prompt-in-progress"}, "outcome": "in_progress"}
                else:
                    reply = {"outcome": "in_progress", "prompt_fingerprint": f"sha256:{len(self.prompts)}"}
                    if self.cursor_step is not None:
                        reply["dispatch_event_cursor"] = self.cursor_step * len(self.prompts)
                connection.sendall(json.dumps(reply).encode() + b"\n")

    def close(self) -> None:
        self.server.close()
        try:
            self.path.unlink()
        except OSError:
            pass


class HolderFixture(unittest.TestCase):
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
        """Attention the holder injects comes from structured records. The stored
        body is the old hand-written list and is not what a current holder reads."""
        state: dict = {"sideagent": {"platform": "zcode", "session": "zcode-KT-sideagent",
                                    "holder_instance_id": "side-1", "state": "active"}}
        for row in attention:
            kind, item_id = row.get("kind"), row.get("id")
            if not isinstance(kind, str) or not isinstance(item_id, str):
                continue
            if kind == "tasks":
                task = {"stage": "review", "goal": "g",
                        "evidence": [row.get("content") or item_id]}
                if row.get("prior_verdict"):
                    task["prior_verdict"] = {"value": row["prior_verdict"], "by": "host",
                                             "host_turn": str(row.get("content") or item_id)}
                state.setdefault("tasks", {})[item_id] = task
            elif kind == "decisions":
                state.setdefault("decisions", {})[item_id] = {
                    "owner": "host", "question": row.get("why") or item_id, "status": "open",
                    "evidence": [row.get("content") or item_id]}
            elif kind == "alerts":
                state.setdefault("alerts", {})[item_id] = {
                    "owner": "host", "summary": row.get("why") or item_id}
        body = json.dumps({"view": "host", "attention": attention, "tasks": []})
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2", "body": body, "state": state}), encoding="utf-8")

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

    def pending_ids(self) -> list[str]:
        return [item["event_id"] for item in self.holder.pending_worker_events]

    def confirmed_ids(self) -> list[str]:
        log = (Path(self.holder.args.record_dir) / "events.jsonl").read_text().splitlines()
        return [event_id for line in log for entry in [json.loads(line)]
                if entry.get("kind") == "worker_event_confirmed" for event_id in entry["event_ids"]]


class HolderRelay(HolderFixture):
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
        injected, defect = holder_module.heartbeat_prompt_body(path)
        self.assertIsNone(defect)
        self.assertNotEqual(injected, "VIEW")
        self.assertNotIn("p" * 80, injected or "")
        self.assertIn("state.pad", injected or "")
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

    def test_a_third_review_on_the_host_direct_path_wakes_the_host(self) -> None:
        def review(round_no: int) -> list:
            task = {"stage": "review", "goal": "g", "evidence": [f"c{round_no}"],
                    "prior_verdict": {"value": "repair", "by": "host", "host_turn": f"review-{round_no - 1}"}}
            return dispatch_module.RECORD.task_attention("t", task)

        self.live_sideagent()
        self.write_state(review(2))
        self.sideagent_end(9, 50)
        self.assertEqual(len(self.agent.prompts()), 1, "the Host sees round 2")
        self.finish_host_turn()
        # The Host records `repair` and asks the worker itself; no Sideagent
        # turn ends while attention is empty. The fix comes back for round 3.
        self.write_state(review(3))
        self.sideagent_end(12, 51)
        self.assertEqual(len(self.agent.prompts()), 2, "round 3 is a new judgment")
        self.finish_host_turn()
        self.sideagent_end(15, 52)
        self.assertEqual(len(self.agent.prompts()), 2, "an unchanged round 3 stays quiet")

    def test_a_lost_turn_end_returns_the_relay_to_the_host_once(self) -> None:
        self.write_state([])
        self.live_sideagent()
        self.fake.cursor_step = 10
        first = "codex/codex-KT-i1-a/idle/5"
        self.event("codex-KT-i1-a", "idle", 5)            # relayed in turn sha256:1, cursor 10
        # That turn's end never reaches the Host holder.
        self.sideagent_end(8, 99)                          # an earlier turn's late end
        self.assertIn(first, self.pending_ids(), "an end older than the relay proves nothing")
        self.assertFalse(any("codex-KT-i1-a" in prompt for prompt in self.agent.prompts()))
        while self.holder.turn.get("active"):
            self.finish_host_turn()
        self.event("codex-KT-i1-b", "idle", 6)             # relayed in turn sha256:2, cursor 20
        self.assertNotIn("codex-KT-i1-a", self.fake.prompts[1]["params"]["text"], "not relayed twice")
        self.sideagent_end(25, 2)
        self.assertIn("codex/codex-KT-i1-b/idle/6", self.confirmed_ids(), "its own turn confirms the second")
        self.assertIn("codex-KT-i1-a", self.agent.prompts()[-1],
                      "the first event's outcome is unknown: the Host has it")
        log = (Path(self.holder.args.record_dir) / "events.jsonl").read_text()
        self.assertIn("turn-end-missing", log)
        self.finish_host_turn()
        self.assertEqual(self.confirmed_ids().count(first), 1, "confirmed exactly once")
        self.sideagent_end(11, 1)                          # the lost end turns up late
        self.assertEqual(self.confirmed_ids().count(first), 1, "and never a second time")
        self.assertEqual(len(self.fake.prompts), 2)

    def test_a_full_queue_still_takes_the_turn_end_that_drains_it(self) -> None:
        self.write_state([])
        self.live_sideagent()
        self.fake.cursor_step = 10
        cap = holder_module.HEARTBEAT_EVENT_CAP
        for n in range(cap):
            self.event(f"codex-KT-i2-w{n}", "idle", 1000 + n)
        workers = [f"codex/codex-KT-i2-w{n}/idle/{1000 + n}" for n in range(cap)]
        self.assertEqual(len(self.holder.pending_worker_events), cap)
        self.assertEqual(self.event("codex-KT-i2-extra", "idle", 1)["error"]["code"], "worker-event-queue-full")
        for turn in range(1, cap + 1):
            self.sideagent_end(10 * turn + 5, turn)
        self.assertEqual(sorted(set(self.confirmed_ids()) & set(workers)), sorted(workers),
                         "every relay is confirmed by its own turn end")
        self.assertFalse(any(item["event_id"] in workers for item in self.holder.pending_worker_events))
        self.assertFalse(any("codex-KT-i2-w" in prompt for prompt in self.agent.prompts()),
                         "a confirmed relay is not also given to the Host")
        while self.holder.turn.get("active"):
            self.finish_host_turn()
        receipt = self.event("codex-KT-i2-new", "idle", 9000)
        self.assertTrue(receipt.get("staged"), receipt)

    def test_a_trickling_sideagent_cannot_hold_the_event_lock_past_the_deadline(self) -> None:
        self.write_state([])
        self.live_sideagent()
        self.fake.trickle = True
        results: dict[str, float] = {}

        def send(name: str, cursor: int) -> None:
            started = time.monotonic()
            self.event(name, "idle", cursor)
            results[name] = time.monotonic() - started

        first = threading.Thread(target=send, args=("codex-KT-i3-a", 5))
        first.start()
        time.sleep(0.2)
        second = threading.Thread(target=send, args=("codex-KT-i3-b", 6))
        second.start()
        first.join(10)
        second.join(10)
        bound = holder_module.RELAY_SEND_TIMEOUT
        self.assertLess(results["codex-KT-i3-a"], bound + 0.5, "one total deadline, not per receive")
        self.assertLess(results["codex-KT-i3-b"], 2 * bound + 1.0, "the waiting event is not held longer")
        while self.holder.turn.get("active"):
            self.finish_host_turn()
        seen = " ".join(self.agent.prompts()) + " ".join(self.pending_ids())
        for name in ("codex-KT-i3-a", "codex-KT-i3-b"):
            self.assertIn(name, seen, f"{name} is not lost behind a slow Sideagent")
        log = (Path(self.holder.args.record_dir) / "events.jsonl").read_text()
        self.assertIn("worker_event_relay_failed", log)

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


class WorkerTree(unittest.TestCase):
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



class NestedWorkerTopology(WorkerTree):
    """The Sideagent's stop keeps the dispatched worker tree."""

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

    def name_dispatcher(self, holder_instance_id: str, holder_pid: int | None = None) -> None:
        record = json.loads((self.worker_dir / "record.json").read_text(encoding="utf-8"))
        record["dispatcher"] = {"holder_instance_id": holder_instance_id, "platform": "zcode",
                                "session": "zcode-KT-sideagent", "repo": self.tmp.name}
        if holder_pid is not None:
            record["holder_pid"] = holder_pid
        (self.worker_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")

    def test_a_foreign_record_or_lost_spawn_line_protects_nothing(self) -> None:
        live = {pgid: [pgid] for pgid in self.groups}
        saved = (self.worker_dir / "record.json").read_text(encoding="utf-8")
        (self.worker_dir / "record.json").write_text(json.dumps({"holder_pid": 1}), encoding="utf-8")
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live),
                         {self.holder.pid, self.native, self.tool},
                         "without its own record only the live descendants are the worker")
        (self.worker_dir / "record.json").write_text(saved, encoding="utf-8")
        (self.side_dir / "children.jsonl").write_text("", encoding="utf-8")
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live,
                                                                holder_instance_id="side-1"),
                         set(), "a command line alone is never worker identity")
        self.name_dispatcher("side-other")
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live,
                                                                holder_instance_id="side-1"),
                         set(), "a worker another holder dispatched is not this Sideagent's")
        self.name_dispatcher("side-1", holder_pid=1)
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live,
                                                                holder_instance_id="side-1"),
                         set(), "a record that does not name the live holder proves nothing")
        (self.worker_dir / "record.json").write_text("[1]", encoding="utf-8")
        self.assertEqual(holder_module.holders_dispatched_by("side-1"), [], "a malformed record is skipped")
        self.assertEqual(acp_module.holders_dispatched_by("side-1"), [])
        (self.worker_dir / "record.json").write_text(saved, encoding="utf-8")
        record = {"session_role": "sideagent", "holder_instance_id": "side-1",
                  "agent_child_groups": {str(g): {str(p): s for p, s in m.items()} for g, m in self.noted.items()}}
        self.assertEqual(sorted(acp_module.recorded_groups(record, self.side_dir, verified_only=True)),
                         sorted(self.groups))
        (self.side_dir / "children.jsonl").write_text(json.dumps(
            {"pid": self.holder.pid, "pgid": self.holder.pid, "spawned_at": 1}) + "\n", encoding="utf-8")
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live), set(),
                         "a spawn line whose time does not match the live holder is a reused pid")

    def test_a_worker_naming_this_sideagent_as_dispatcher_is_kept_without_a_spawn_line(self) -> None:
        # The ZCode bridge does not forward KAOLA_ACP_CHILD_RECORD, so its
        # Sideagent's spawn record stays empty; KAOLA_ACP_DISPATCHER does reach
        # the worker start and lands in the worker's own record.
        (self.side_dir / "children.jsonl").write_text("", encoding="utf-8")
        self.name_dispatcher("side-1")
        tree = {self.holder.pid, self.native, self.tool, self.orphan.pid}
        live = {pgid: [pgid] for pgid in self.groups}
        self.assertEqual(holder_module.dispatched_worker_groups(self.side_dir / "children.jsonl", live,
                                                                holder_instance_id="side-1"), tree)
        record = {"session_role": "sideagent", "holder_instance_id": "side-1",
                  "agent_child_groups": {str(g): {str(p): s for p, s in m.items()} for g, m in self.noted.items()}}
        for verified_only in (False, True):
            self.assertEqual(acp_module.recorded_groups(record, self.side_dir, verified_only=verified_only),
                             [self.unrelated.pid], f"dead-holder path, verified_only={verified_only}")
        args = argparse.Namespace(record_dir=str(self.side_dir), socket=str(self.side_dir / "s.sock"),
                                  platform="zcode", session="zcode-KT-sideagent", repo=self.tmp.name,
                                  init_meta="", command="stub")
        holder = holder_module.Holder(args)
        holder.holder_instance_id = "side-1"
        holder.agent = RealAgent()
        holder.session_role = "sideagent"
        holder.agent_child_groups = {pgid: dict(members) for pgid, members in self.noted.items()}
        holder._terminate_group(False)
        self.groups.append(holder.agent.proc.pid)
        self.assertEqual(holder.swept_child_pgids, [self.unrelated.pid])
        self.assertEqual(holder.spared_child_pgids, sorted(tree))
        for pid in tree:
            self.assertTrue(self.alive(pid), f"worker process {pid} survived the Sideagent stop")
        self.unrelated.wait(timeout=5)
        self.assertFalse(self.alive(self.unrelated.pid))


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

    def resolve(self, dispatcher: dict) -> dict:
        previous = {key: os.environ.pop(key, None)
                    for key in ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST")}
        os.environ["KAOLA_ACP_DISPATCHER"] = json.dumps(dispatcher)
        try:
            return acp_module.resolve_heartbeat_host(self.args, self.repo_text)
        finally:
            os.environ.pop("KAOLA_ACP_DISPATCHER", None)
            os.environ.update({key: value for key, value in previous.items() if value is not None})

    def test_a_worker_is_not_the_carrier_of_the_sessions_it_starts(self) -> None:
        digest = hashlib.sha256(self.repo_text.encode()).hexdigest()[:16]
        worker_dir = Path(self.args.record_root) / "codex" / "codex-KT-i255-research" / digest
        worker_dir.mkdir(parents=True)
        worker = {"holder_instance_id": "worker-1", "platform": "codex", "repo": self.repo_text,
                  "session": "codex-KT-i255-research"}
        (worker_dir / "record.json").write_text(json.dumps(dict(
            worker, session_role="worker", holder_pid=os.getpid())), encoding="utf-8")
        resolved = self.resolve(worker)
        self.assertEqual((resolved["target"], resolved["source"], resolved["refusal"]),
                         (None, "dispatcher-not-host", None),
                         "a worker's own session is started unbound, never refused")
        self.assertEqual(resolved["dispatcher"], worker, "who dispatched it stays recorded")
        host = dict(self.dispatcher, session="zcode-KT-orchestrator-main", holder_instance_id="host-2")
        resolved = self.resolve(host)
        self.assertEqual((resolved["source"], resolved["target"]["session"]),
                         ("dispatcher", "zcode-KT-orchestrator-main"), "a Host still carries its workers")

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


# -- consolidated #255: dispatch linkage, results, dispositions, nodes, preserve -

dispatch_fixtures = load("kaola_dispatch_fixtures_255", REPO / "tests" / "contract" / "test-issue-244-dispatch.py")


class ConsolidatedDispatch(StateProject):
    """One `execute` entry for implementation work: the Host's exact text,
    task linkage, holds that are not re-probed, explicit result gaps and the
    Host's per-assignment disposition mirrored onto the index."""

    def setUp(self) -> None:
        super().setUp()
        self.skills = Path(self.tmp.name) / "skills"
        dispatch_fixtures.install_fake(self.skills, ["zcode"])
        self.log = Path(self.tmp.name) / "runner.log"
        self.spec = Path(self.tmp.name) / "spec.json"
        self.env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
        self.env.update(FAKE_LOG=str(self.log), FAKE_SPEC=str(self.spec))
        self.index = self.repo / "index.json"

    def sessions(self, names: list[str]) -> None:
        repo = str(self.repo)
        self.spec.write_text(json.dumps({"sessions": {name: {
            "status": dispatch_fixtures.absent(repo),
            "start": dispatch_fixtures.started(repo, "GLM-5.3", "max", holder=f"holder-{name[-1]}"),
            "send": dispatch_fixtures.sent(f"fp-{name[-1]}")} for name in names}}), encoding="utf-8")

    def execute(self, plan: dict, *extra: str) -> tuple[int, dict]:
        path = self.repo / "plan.json"
        path.write_text(json.dumps({"repo": str(self.repo), **plan}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": []}), encoding="utf-8")
        return run(["execute", "--plan", str(path), "--authorization", str(self.file),
                    "--platforms", str(PLATFORMS), "--skills-root", str(self.skills),
                    "--live", str(live), "--index", str(self.index), *extra], self.env)

    def test_implementation_sends_the_hosts_core_and_scope_and_links_the_task(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "parser", "keep_open": True})
        host_revision = self.doc()["host_revision"]
        self.sessions(["zcode-KT-i1-a", "zcode-KT-i1-b"])
        core = "Implement the parser per the design.\n"
        code, out = self.execute({
            "scope": "implementation", "mutation": True, "core": core, "core_revision": "r3",
            "items": [{"item_id": "w1", "preset": "zcode/default", "session": "zcode-KT-i1-a",
                       "worker_scope": "Scope A: lexer only.", "task_id": "t1"},
                      {"item_id": "w2", "preset": "zcode/default", "session": "zcode-KT-i1-b",
                       "worker_scope": "Scope B: tests only.", "task_id": "t1"}]}, "--state", str(self.file))
        self.assertEqual(code, 0, out)
        rows = {row["item_id"]: row for row in out["items"]}
        self.assertEqual({row["status"] for row in rows.values()}, {"in-flight"}, rows)
        sends = [row for row in dispatch_fixtures.commands(self.log) if row["command"] == "send"]
        texts = sorted(row["argv"][row["argv"].index("--text") + 1] for row in sends)
        self.assertEqual(texts, [core.rstrip("\n") + "\n\nScope A: lexer only.",
                                 core.rstrip("\n") + "\n\nScope B: tests only."],
                         "the Host's core and per-worker scope are sent unchanged")
        for row in rows.values():
            source = row["prompt_source"]
            self.assertEqual((source["kind"], source["core_revision"]), ("core+scope", "r3"))
            self.assertEqual(source["core_sha256"], dispatch_module.prompt_sha(core))
            self.assertEqual(source["prompt_sha256"], row["prompt_sha256"])
        task = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(task["dispatch"], ["w1", "w2"], "the task names its items")
        self.assertEqual(task["writer"], "tool:execute")
        self.assertEqual(self.doc()["host_revision"], host_revision,
                         "tool-only linkage is not a Host business write")
        self.assertEqual(out["task_links"]["linked"], {"t1": ["w1", "w2"]})

    def test_a_second_execute_batch_keeps_the_first_in_flight_ref(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "parser", "keep_open": True})
        self.sessions(["zcode-KT-i1-a", "zcode-KT-i1-b"])
        first = {"scope": "implementation", "mutation": True, "core": "core\n", "core_revision": "r1",
                 "items": [{"item_id": "w1", "preset": "zcode/default", "session": "zcode-KT-i1-a",
                            "worker_scope": "first", "task_id": "t1"}]}
        code, out = self.execute(first, "--state", str(self.file))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["dispatch"], ["w1"])
        second = {"scope": "implementation", "mutation": True, "core": "core\n", "core_revision": "r1",
                  "items": [{"item_id": "w2", "preset": "zcode/default", "session": "zcode-KT-i1-b",
                             "worker_scope": "second", "task_id": "t1"}]}
        code, out = self.execute(second, "--state", str(self.file))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["dispatch"], ["w1", "w2"])

    def test_mutation_stays_refused_outside_implementation_and_prompts_are_exact(self) -> None:
        self.init()
        self.sessions(["zcode-KT-i1-a"])
        item = {"item_id": "w1", "preset": "zcode/default", "session": "zcode-KT-i1-a", "prompt": "edit"}
        code, out = self.execute({"scope": "research", "mutation": True, "items": [item]})
        self.assertEqual(out["items"][0]["reason"], "scope-outside-bounded")
        code, out = self.execute({"scope": "implementation", "items": [dict(item, worker_scope="x")]})
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), "one prompt source per item")
        code, out = self.execute({"scope": "implementation", "core": "c",
                                  "items": [{**item, "prompt": None, "worker_scope": "x"}]})
        self.assertEqual((code, out["reason"]), (2, "invalid-input"), "a core needs its revision")
        self.assertEqual(dispatch_fixtures.commands(self.log), [])

    def test_a_recorded_hold_is_not_re_probed(self) -> None:
        self.init()
        self.update("host", "holds", "h-zcode", {"scope": "account", "reason": "quota",
                                                 "preset": "zcode/default", "owner": "user"})
        self.sessions(["zcode-KT-i1-a"])
        code, out = self.execute({"scope": "research", "items": [
            {"item_id": "w1", "preset": "zcode/default", "session": "zcode-KT-i1-a", "prompt": "p"}]})
        self.assertEqual(code, 0, out)
        self.assertEqual((out["items"][0]["status"], out["items"][0]["reason"]), ("not-run", "on-hold"))
        self.assertEqual(out["items"][0]["holds"], ["h-zcode"])
        self.assertEqual(dispatch_fixtures.commands(self.log), [], "no status, start or send reaches it")

    def collect_spec(self, session: str, reply: str) -> None:
        repo = str(self.repo)
        self.spec.write_text(json.dumps({"sessions": {session: {
            "status": {"repo": repo, "session": session, "holder_instance_id": "holder-a",
                       "turn_active": False, "turn_outcome": "turn_completed", "stop_reason": "end_turn",
                       "mutation_status": "completed",
                       "last_prompt": {"fingerprint": "fp-a", "stop_reason": "end_turn",
                                       "mutation_status": "completed"}},
            "capture": {"repo": repo, "session": session, "event_log_path": "/x/events.jsonl", "events": [
                {"cursor": 12, "kind": "session_update", "update": {
                    "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": reply}}}]}}}}),
            encoding="utf-8")

    def index_row(self, item_id: str, session: str, **extra) -> dict:
        return {"item_id": item_id, "preset": "zcode/default", "platform": "zcode", "session": session,
                "repo": str(self.repo), "holder_instance_id": "holder-a", "prompt_fingerprint": "fp-a",
                "prompt_sha256": "fp-a", "status": "in-flight", "acceptance": "pending",
                "dispatch_event_cursor": 11, "task_id": "t1", **extra}

    def test_collect_names_the_turn_locators_truncation_and_an_absent_output(self) -> None:
        self.collect_spec("zcode-KT-i1-a", "r" * 600)
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "correlation_only": True,
                                          "repo": str(self.repo), "items": [
                                              self.index_row("w1", "zcode-KT-i1-a", output="docs/a.md",
                                                             acceptance="repair")]}), encoding="utf-8")
        code, out = run(["collect", "--index", str(self.index), "--skills-root", str(self.skills)], self.env)
        self.assertEqual(code, 0, out)
        row = out["items"][0]
        result = row["result"]
        self.assertEqual((row["status"], row["acceptance"], row["prior_acceptance"]),
                         ("returned", "pending", "repair"), "a new return is a new candidate")
        self.assertTrue(result["excerpt_truncated"])
        self.assertEqual((len(result["excerpt"]), result["reply_chars"]), (480, 600))
        self.assertEqual(result["locator"]["argv"][-2:], ["--full", "--inline"])
        self.assertEqual((result["locator"]["since"], result["locator"]["event_log_path"]), (11, "/x/events.jsonl"))
        self.assertEqual(result["turn"], {"holder_instance_id": "holder-a", "prompt_fingerprint": "fp-a"})
        self.assertEqual(result["output"]["present"], False)
        self.assertEqual(result["gaps"], ["output-absent"], "absence is a gap, not a transport failure")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "a.md").write_text("report", encoding="utf-8")
        self.collect_spec("zcode-KT-i1-a", "short")
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "correlation_only": True,
                                          "repo": str(self.repo), "items": [
                                              self.index_row("w1", "zcode-KT-i1-a", output="docs/a.md")]}),
                              encoding="utf-8")
        code, out = run(["collect", "--index", str(self.index), "--skills-root", str(self.skills)], self.env)
        result = out["items"][0]["result"]
        self.assertEqual((result["excerpt"], result["excerpt_truncated"], result["gaps"]), ("short", False, []))
        self.assertTrue(result["output"]["present"])

    def returned_spec(self, sessions: dict[str, dict]) -> None:
        """Completed turns for several sessions; extra keys (``wait_for``)
        go on the session row of the fake Runner."""
        repo = str(self.repo)
        self.spec.write_text(json.dumps({"sessions": {session: {
            "status": {"repo": repo, "session": session, "holder_instance_id": "holder-a",
                       "turn_active": False, "turn_outcome": "turn_completed", "stop_reason": "end_turn",
                       "mutation_status": "completed",
                       "last_prompt": {"fingerprint": "fp-a", "stop_reason": "end_turn",
                                       "mutation_status": "completed"}},
            "capture": {"repo": repo, "session": session, "events": [
                {"cursor": 12, "kind": "session_update", "update": {
                    "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "done"}}}]},
            **extra} for session, extra in sessions.items()}}), encoding="utf-8")

    def test_only_a_declared_file_can_be_reported_absent(self) -> None:
        declared = {"w1": "Original final reply with command, line count, integer sum, and SHA-256.",
                    "w2": "https://example.invalid/pr/7", "w3": {"kind": "capture"}, "w4": "docs/missing.md",
                    "w5": {"path": "docs/also missing.md"}}
        self.returned_spec({f"zcode-KT-i1-{key}": {} for key in declared})
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": [
            self.index_row(key, f"zcode-KT-i1-{key}", output=value) for key, value in declared.items()]}),
            encoding="utf-8")
        code, out = run(["collect", "--index", str(self.index), "--skills-root", str(self.skills)], self.env)
        self.assertEqual(code, 0, out)
        facts = {row["item_id"]: (row["result"]["output"]["kind"], row["result"]["output"].get("present"),
                                  row["result"]["gaps"]) for row in out["items"]}
        self.assertEqual(facts, {"w1": ("description", None, []), "w2": ("remote", None, []),
                                 "w3": ("capture", True, []), "w4": ("file", False, ["output-absent"]),
                                 "w5": ("file", False, ["output-absent"])})

    def test_a_disposition_mirrored_during_a_collect_survives_it(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "review", "goal": "g", "dispatch": ["w1", "w2"]})
        gate = Path(self.tmp.name) / "gate"
        self.returned_spec({"zcode-KT-i1-a": {}, "zcode-KT-i1-b": {"wait_for": str(gate)}})
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": [
            self.index_row("w1", "zcode-KT-i1-a"), self.index_row("w2", "zcode-KT-i1-b")]}), encoding="utf-8")
        collect = subprocess.Popen([sys.executable, str(SCRIPT), "collect", "--index", str(self.index),
                                    "--skills-root", str(self.skills)], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    rows = {row["item_id"]: row for row in json.loads(self.index.read_text())["items"]}
                except (OSError, ValueError):
                    rows = {}
                if rows.get("w1", {}).get("status") == "returned":
                    break
                time.sleep(0.02)
            self.assertEqual(rows["w1"]["status"], "returned", "the collect published its first return")
            self.assertIsNone(collect.poll(), "the collect is still waiting on w2")
            code, out = self.update("host", "tasks", "t1", {"dispositions": {"w1": "accepted"}},
                                    "--expect-rev", "1", "--index", str(self.index))
            self.assertEqual((code, out["index_mirror"]["changed"]), (0, {"w1": "accepted"}), out)
        finally:
            gate.write_text("go", encoding="utf-8")
            stdout, stderr = collect.communicate(timeout=30)
        self.assertEqual(collect.returncode, 0, stderr)
        rows = {row["item_id"]: row for row in json.loads(self.index.read_text())["items"]}
        self.assertEqual((rows["w1"]["acceptance"], rows["w1"]["acceptance_source"]["task_id"]), ("accepted", "t1"),
                         "the Host's disposition is not overwritten by the collect's earlier read")
        self.assertEqual((rows["w2"]["status"], rows["w2"]["acceptance"]), ("returned", "pending"))
        self.assertEqual({row["item_id"]: row["acceptance"] for row in json.loads(stdout)["items"]},
                         {"w1": "accepted", "w2": "pending"})

    def test_per_assignment_dispositions_are_mirrored_never_left_pending(self) -> None:
        self.init()
        self.update("host", "tasks", "t1", {"stage": "review", "goal": "g", "dispatch": ["w1", "w2"]})
        rows = [dict(self.index_row("w1", "zcode-KT-i1-a"), status="returned"),
                dict(self.index_row("w2", "zcode-KT-i1-b"), status="returned"),
                dict(self.index_row("w3", "zcode-KT-i1-c"), task_id="t9", status="returned")]
        self.index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "repo": str(self.repo),
                                          "items": rows}), encoding="utf-8")
        code, out = self.update("host", "tasks", "t1", {"verdict": {"value": "partial"},
                                                        "dispositions": {"w1": "accepted"}},
                                "--expect-rev", "1", "--index", str(self.index))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["index_mirror"]["changed"], {"w1": "accepted", "w2": "undecided"})
        index = {row["item_id"]: row for row in json.loads(self.index.read_text())["items"]}
        self.assertEqual(index["w1"]["acceptance"], "accepted")
        self.assertEqual(index["w1"]["acceptance_source"]["task_id"], "t1")
        self.assertEqual(index["w2"]["acceptance"], "undecided")
        self.assertIn("without a disposition", index["w2"]["acceptance_note"])
        self.assertEqual(index["w3"]["acceptance"], "pending", "another task's item is untouched")
        code, out = self.update("host", "tasks", "t1", {"dispositions": {"w2": "cancelled"}},
                                "--expect-rev", "2", "--index", str(self.index))
        index = {row["item_id"]: row for row in json.loads(self.index.read_text())["items"]}
        self.assertEqual(index["w2"]["acceptance"], "cancelled")
        self.assertNotIn("acceptance_note", index["w2"])
        code, out = self.update("host", "tasks", "t1", {"dispositions": {"w2": "maybe"}},
                                "--expect-rev", "3")
        self.assertEqual(out["reason"], "invalid-input")
        view = json.loads(self.doc()["body"])
        self.assertEqual(view["tasks"][0]["dispositions"], {"w1": "accepted", "w2": "cancelled"})


class MaintenanceCheckpoint(StateProject):
    """Fixed input accounting for fresh Sideagent nodes."""

    SESSION = "zcode-KT-sideagent"

    def setUp(self) -> None:
        super().setUp()
        self.records = Path(self.tmp.name) / "records"
        self.saved_root = os.environ.get("KAOLA_ACP_RECORD_ROOT")
        os.environ["KAOLA_ACP_RECORD_ROOT"] = str(self.records)

    def tearDown(self) -> None:
        if self.saved_root is None:
            os.environ.pop("KAOLA_ACP_RECORD_ROOT", None)
        else:
            os.environ["KAOLA_ACP_RECORD_ROOT"] = self.saved_root
        super().tearDown()

    def node(self, holder: str) -> dict[str, str]:
        """The bound session now runs this fresh holder: its own record says so."""
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.records / "zcode" / self.SESSION / digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "record.json").write_text(json.dumps({"holder_instance_id": holder,
                                                           "session_role": "sideagent"}), encoding="utf-8")
        return self.caller_env(self.SESSION, holder)

    def bind(self) -> None:
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                               "--section", "sideagent", "--expect-revision", str(self.doc()["revision"]),
                               "--set", json.dumps({"platform": "zcode", "session": self.SESSION,
                                                    "state": "active", "mode": "node"}))
        self.assertEqual(code, 0, out)

    def checkpoint(self, env: dict | None, batch: str, through: int, entries: list,
                   events: list | None = None) -> tuple[int, dict]:
        return self.state("checkpoint", "--file", str(self.file), "--writer", "sideagent", "--source", batch,
                          "--batch", batch, "--through-host-revision", str(through),
                          "--entries", json.dumps(entries), *(["--events", json.dumps(events)] if events else []),
                          env=env)

    def sideagent_view(self) -> dict:
        code, out = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, out)
        return out

    def test_two_consecutive_nodes_account_for_their_fixed_inputs(self) -> None:
        self.init()
        self.bind()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "a"})
        self.update("host", "tasks", "t2", {"stage": "todo", "goal": "b", "next": "host plans"})
        first = self.doc()["host_revision"]
        pending = self.sideagent_view()["pending_host_changes"]
        self.assertIn(f"host:tasks/t1@{first - 1}", pending)
        self.assertIn(f"host:tasks/t2@{first}", pending)
        node1 = self.node("node-1")
        code, out = self.update("sideagent", "tasks", "t1", {"wait": "worker running"}, "--expect-rev", "1",
                                env=node1)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["host_revision"], first, "a node's write is no new business input")
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["writer_holder"], "node-1")
        entries = [{"input": f"host:section/{name}@{revision}", "retained": f"section/{name}"}
                   for name, revision in (("authorization", 1), ("project", 1), ("sideagent", first - 2))]
        entries += [
                    {"input": f"host:tasks/t1@{first - 1}", "applied": ["tasks/t1"]},
                    {"input": f"host:tasks/t2@{first}", "retained": "tasks/t2"}]
        code, out = self.checkpoint(node1, "b-1", first, entries)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["value"]["verified"], out)
        maintenance = self.doc()["state"]["maintenance"]
        self.assertEqual(maintenance["last_verified"]["node"]["holder_instance_id"], "node-1")
        self.assertEqual((maintenance["acked_host_revision"], maintenance["handled_host_revision"]),
                         (first, first))
        self.assertEqual(self.sideagent_view()["pending_host_changes"], [])
        view = json.loads(self.doc()["body"])
        self.assertEqual(view["maintenance"]["last_verified"]["batch"], "b-1",
                         "the last verified checkpoint sits beside current obligations")

        # A later Host change and a worker event make the next batch.
        self.update("host", "tasks", "t3", {"stage": "todo", "goal": "c"})
        later = self.doc()["host_revision"]
        node2 = self.node("node-2")
        code, out = self.update("sideagent", "tasks", "t1", {"wait": "late"}, "--expect-rev", "2", env=node1)
        self.assertEqual(out["reason"], "binding-superseded", "the old node is no longer a writer")
        code, out = self.checkpoint(node2, "b-2", later,
                                    [{"input": "codex/codex-KT-i1-a/idle/5", "applied": ["tasks/t1"]}],
                                    events=["codex/codex-KT-i1-a/idle/5"])
        self.assertEqual(code, 0, out)
        record = out["value"]
        self.assertFalse(record["verified"], "a partial checkpoint is never verified")
        self.assertIn("not a current record this node wrote",
                      record["returned_to_host"]["codex/codex-KT-i1-a/idle/5"],
                      "older evidence cannot settle a new input")
        self.assertEqual(record["returned_to_host"][f"host:tasks/t3@{later}"], "unaccounted")
        maintenance = self.doc()["state"]["maintenance"]
        self.assertEqual(maintenance["acked_host_revision"], later - 1,
                         "the acknowledgment does not pass an unaccounted change")
        self.assertEqual(maintenance["handled_host_revision"], later)
        self.assertEqual(maintenance["last_verified"]["batch"], "b-1")
        alert = self.doc()["state"]["alerts"]["maintenance-returned"]
        self.assertEqual(alert["owner"], "host")
        self.assertEqual(sorted(alert["inputs"]), sorted(record["returned_to_host"]))
        self.assertEqual(self.sideagent_view()["pending_host_changes"], [],
                         "returned inputs are the Host's, never re-sent to another node")
        attention = json.loads(self.doc()["body"])["attention"]
        self.assertIn("maintenance-returned", [row["id"] for row in attention])

    def test_host_retirement_preserves_an_earlier_sent_checkpoint_range(self) -> None:
        self.init()
        self.bind()
        code, out = self.update("host", "tasks", "t1", {
            "stage": "done", "goal": "a", "verdict": {"value": "accepted"}})
        self.assertEqual(code, 0, out)
        through = self.doc()["host_revision"]
        node = self.node("node-1")
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "retire",
                               "--kind", "tasks", "--id", "t1", "--expect-rev", "1",
                               "--evidence", "README.md", "--cite", CITE)
        self.assertEqual(code, 0, out)
        raw = self.file.read_bytes()
        carrier = holder_module.Holder.__new__(holder_module.Holder)
        carrier.node = {"sent_through": through, "batch": "b-1"}
        self.assertIsNone(carrier._node_host_pending(self.doc()))
        self.assertEqual(self.file.read_bytes(), raw, "selection writes no checkpoint proof")
        entries = [{"input": f"host:section/{name}@{revision}", "retained": f"section/{name}"}
                   for name, revision in (("authorization", 1), ("project", 1), ("sideagent", through - 1))]
        entries.append({"input": f"host:tasks/t1@{through}", "applied": ["retired:tasks/t1"]})
        code, out = self.checkpoint(node, "b-1", through, entries)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["value"]["verified"], out)
        maintenance = self.doc()["state"]["maintenance"]
        self.assertEqual(maintenance["handled_host_revision"], through)
        self.assertEqual(maintenance["acked_host_revision"], through)
        self.assertEqual(self.doc()["host_revision"], through + 1)
        self.assertFalse(self.doc()["state"].get("retired"))

    def test_a_host_rewrite_during_the_batch_is_superseded_not_returned(self) -> None:
        """Native QA: the Host's next turn rewrote batch records while the
        node ran; the node's entries for the earlier changes were returned
        as not-in-batch although the next batch carries the rewrite."""
        self.init()
        self.bind()
        self.update("host", "tasks", "t1", {"stage": "doing", "goal": "a"})
        through = self.doc()["host_revision"]
        node1 = self.node("node-1")
        self.update("host", "tasks", "t1", {"stage": "review"}, "--expect-rev", "1")
        rewrite = self.doc()["host_revision"]
        entries = [{"input": f"host:section/{name}@{revision}", "retained": f"section/{name}"}
                   for name, revision in (("authorization", 1), ("project", 1), ("sideagent", through - 1))]
        entries.append({"input": f"host:tasks/t1@{through}", "retained": "section/project"})
        code, out = self.checkpoint(node1, "b-1", through, entries)
        self.assertEqual(code, 0, out)
        record = out["value"]
        self.assertTrue(record["verified"], record)
        self.assertEqual(record["superseded"], [f"host:tasks/t1@{through}"])
        self.assertEqual(record["returned_to_host"], {})
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})
        self.assertEqual(self.sideagent_view()["pending_host_changes"], [f"host:tasks/t1@{rewrite}"],
                         "the rewrite is the next batch's input")

    def test_a_checkpoint_needs_the_nodes_own_identity_and_a_valid_range(self) -> None:
        self.init()
        self.bind()
        code, out = self.checkpoint(None, "b-1", 0, [])
        self.assertEqual(out["reason"], "node-identity-required")
        node = self.node("node-1")
        code, out = self.checkpoint(node, "b-1", self.doc()["host_revision"] + 5, [])
        self.assertEqual(out["reason"], "invalid-input")
        stray = self.caller_env("zcode-KT-i1-helper", "h-1")
        code, out = self.checkpoint(stray, "b-1", 0, [])
        self.assertEqual(out["reason"], "binding-superseded")


FAKE_NODE_RUNNER = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, os, sys, time
    from pathlib import Path
    counter = Path(os.environ["FAKE_NODE_COUNTER"])
    n = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(n))
    Path(os.environ["FAKE_NODE_ARGV"]).write_text(json.dumps(sys.argv[1:]))
    holder = f"node-{n}"
    Path(os.environ["FAKE_NODE_RECORD"]).write_text(json.dumps({
        "session_role": "sideagent", "repo": os.environ["FAKE_NODE_REPO"], "state": "ready",
        "holder_instance_id": holder, "holder_pid": int(os.environ["FAKE_NODE_PID"]),
        "dispatcher": json.loads(os.environ.get("KAOLA_ACP_DISPATCHER") or "null"),
        "holder_features": ["heartbeat-state/2", "sideagent-relay/1", "sideagent-node/1"]}))
    time.sleep(float(os.environ.get("FAKE_NODE_DELAY") or 0))
    print(json.dumps({"holder_instance_id": holder, "session": "zcode-KT-sideagent"}))
""")


class FakeNode(FakeSideagent):
    """A node holder socket: prompts are admitted; an exact stop marks the
    record stopped and its holder gone unless the test holds it (``linger``
    keeps the holder process after the stopped record)."""

    def __init__(self, path: Path, record: Path) -> None:
        self.record = record
        self.ignore_stop = False
        self.linger = False
        self.refuse = False
        reaped = subprocess.Popen(["true"])
        reaped.wait()
        self.dead_pid = reaped.pid
        self.stops: list[dict] = []
        super().__init__(path)

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
                if message.get("op") == "stop":
                    self.stops.append(message)
                    if not self.ignore_stop:
                        record = json.loads(self.record.read_text())
                        record["state"] = "stopped"
                        if not self.linger:
                            record["holder_pid"] = self.dead_pid
                        self.record.write_text(json.dumps(record))
                    connection.sendall(json.dumps({"stopped": not self.ignore_stop}).encode() + b"\n")
                    continue
                self.prompts.append(message)
                reply = ({"error": {"code": "prompt-refused"}} if self.refuse else
                         {"outcome": "in_progress", "prompt_fingerprint": f"sha256:{len(self.prompts)}"})
                connection.sendall(json.dumps(reply).encode() + b"\n")


class HolderNodeMode(HolderFixture):
    """The Host carrier starts a fresh node per batch from the recipe argv,
    settles the batch from that node's checkpoint, and exact-stops it."""

    def setUp(self) -> None:
        super().setUp()
        root = Path(self.tmp.name)
        self.runner = root / "runtime-tmux.sh"
        self.runner.write_text(FAKE_NODE_RUNNER, encoding="utf-8")
        self.runner.chmod(0o755)
        self.saved_env = {key: os.environ.get(key) for key in
                          ("FAKE_NODE_COUNTER", "FAKE_NODE_ARGV", "FAKE_NODE_RECORD", "FAKE_NODE_REPO",
                           "FAKE_NODE_PID", "FAKE_NODE_DELAY")}
        os.environ.update(FAKE_NODE_COUNTER=str(root / "count"), FAKE_NODE_ARGV=str(root / "argv"),
                          FAKE_NODE_RECORD=str(self.side_dir / "record.json"),
                          FAKE_NODE_REPO=str(self.repo), FAKE_NODE_PID=str(os.getpid()))
        self.fake = FakeNode(self.side_sock, self.side_dir / "record.json")
        self.saved_confirm = holder_module.NODE_STOP_CONFIRM_SECONDS
        holder_module.NODE_STOP_CONFIRM_SECONDS = 1.5
        self.saved_reclaim = getattr(holder_module, "NODE_RECLAIM_SECONDS", None)

    def tearDown(self) -> None:
        holder_module.NODE_STOP_CONFIRM_SECONDS = self.saved_confirm
        if self.saved_reclaim is not None:
            holder_module.NODE_RECLAIM_SECONDS = self.saved_reclaim
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        super().tearDown()

    def write_node_state(self, maintenance: dict | None = None, argv: list | None = None,
                         host_revision: int | None = None, attention: list | None = None,
                         author: str | None = None) -> None:
        """`author` is the holder that wrote the attention records, the Host
        when None."""
        argv = argv or ["start", "--repo", str(self.repo), "--session", "zcode-KT-sideagent",
                        "--role", "sideagent"]
        self.rev = getattr(self, "rev", 0) if host_revision is None else host_revision
        if attention is not None:
            self.attention, self.author = attention, author
        self.attention = getattr(self, "attention", [])
        state = {"sideagent": {"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active",
                               "mode": "node", "recipe": {"runner": str(self.runner), "argv": argv}},
                 "maintenance": maintenance or {}}
        if self.rev:
            state["section_sources"] = {"project": {"writer": "host", "host_revision": self.rev}}
        for row in self.attention:
            record = {
                "writer": "sideagent" if getattr(self, "author", None) else "host",
                **({"writer_holder": self.author} if getattr(self, "author", None) else {})}
            if row["kind"] == "alerts":
                record["owner"] = "host"
                record["summary"] = row.get("why") or row["id"]
            elif row["kind"] == "decisions":
                record.update(owner="host", status="open", question=row.get("why") or row["id"])
            elif row["kind"] == "tasks":
                record.update(stage="review", goal=row.get("why") or row["id"])
            state.setdefault(row["kind"], {})[row["id"]] = record
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2", "host_revision": self.rev,
            "body": json.dumps({"view": "host", "attention": self.attention, "tasks": []}),
            "state": state}), encoding="utf-8")

    def boundary(self) -> None:
        """A Host turn boundary or the holder tick."""
        with self.holder.worker_events_lock:
            self.holder._relay_pass()

    def host_change(self, revision: int, attention: list | None = None) -> None:
        handled = getattr(self, "handled", 0)
        self.write_node_state({"handled_host_revision": handled}, host_revision=revision, attention=attention)

    def batch_of(self, index: int) -> str:
        return self.fake.prompts[index]["params"]["text"].split("batch ", 1)[1].split()[0]

    def wait_for(self, check, what: str, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.05)
        self.fail(f"timed out waiting for {what}")

    def log_kinds(self) -> list[str]:
        log = Path(self.holder.args.record_dir) / "events.jsonl"
        return [json.loads(line)["kind"] for line in log.read_text().splitlines()] if log.exists() else []

    def checkpoint(self, batch: str, holder: str, through: int | None = None, verified: bool = True,
                   attention: list | None = None, author: str | None = "node") -> None:
        """The node's own checkpoint as `state checkpoint` records it; an
        omitted `--through-host-revision` records the handled revision.
        Changed attention is the node's own records unless `author` is None
        (the Host's)."""
        handled = getattr(self, "handled", 0)
        through = handled if through is None else through
        self.write_node_state({"last_checkpoint": {"batch": batch, "node": {"holder_instance_id": holder},
                                                   "host_revision": {"from": handled, "through": through,
                                                                     "current": self.rev},
                                                   "verified": verified},
                               "handled_host_revision": through}, attention=attention,
                              author=holder if author == "node" else author)
        self.handled = through

    def node_count(self) -> int:
        counter = Path(self.tmp.name) / "count"
        return int(counter.read_text()) if counter.exists() else 0

    def first_node(self, revision: int = 4) -> str:
        """One Host change at an idle boundary: one fresh node and its batch."""
        self.host_change(revision)
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 1, "the first node's batch")
        return self.batch_of(0)

    def retire_input(self, revision: int) -> bytes:
        """Deletion raises the revision, but leaves no selectable current record."""
        self.host_change(revision)
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = json.loads(path.read_text())
        doc["state"].pop("section_sources", None)
        path.write_text(json.dumps(doc))
        return path.read_bytes()

    def test_retirement_only_starts_no_node_and_later_work_selects_the_full_range(self) -> None:
        raw = self.retire_input(4)
        self.boundary()
        self.assertNotIn(self.holder.node.get("phase"), ("starting", "running"))
        self.assertEqual(self.node_count(), 0)
        self.assertEqual(self.fake.prompts, [])
        self.assertEqual((self.repo / ".kaola" / "heartbeat-prompt.json").read_bytes(), raw)
        self.host_change(5)
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 1, "useful work after retirement")
        self.assertIn("host revision 1..5", self.fake.prompts[0]["params"]["text"])
        self.assertEqual(self.holder.node["sent_through"], 5)
        self.checkpoint(self.batch_of(0), "node-1", through=5)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stop")

    def test_retirement_mixed_with_current_work_still_sends_one_useful_batch(self) -> None:
        self.retire_input(4)
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = json.loads(path.read_text())
        doc["state"]["tasks"] = {"keep": {"stage": "todo", "goal": "next", "host_revision": 3}}
        path.write_text(json.dumps(doc))
        self.assertEqual(dispatch_module.host_changes(doc, 0, 4), {"host:tasks/keep@3": 3})
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 1, "the mixed batch")
        self.assertIn("host revision 1..4", self.fake.prompts[0]["params"]["text"])
        self.assertEqual(self.holder.node["sent_through"], 4)
        self.checkpoint(self.batch_of(0), "node-1", through=4)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stop")

    def test_retirement_during_an_assigned_batch_preserves_its_checkpoint(self) -> None:
        batch = self.first_node(3)
        raw = self.retire_input(4)
        self.boundary()
        self.assertEqual(self.holder.node["batch"], batch)
        self.assertEqual(self.holder.node["sent_through"], 3)
        self.assertEqual(self.fake.stops, [])
        self.assertEqual(len(self.fake.prompts), 1)
        self.assertEqual((self.repo / ".kaola" / "heartbeat-prompt.json").read_bytes(), raw)
        self.checkpoint(batch, "node-1", through=3)
        # Keep the deleted input absent when recording the earlier checkpoint.
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        doc = json.loads(path.read_text())
        doc["state"].pop("section_sources", None)
        path.write_text(json.dumps(doc))
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the original node stop")
        self.boundary()
        self.assertEqual(self.node_count(), 1)
        self.assertEqual(self.holder._lifecycle_state()["state"]["maintenance"]["handled_host_revision"], 3)

    def test_startup_then_empty_exact_stops_only_the_owned_unassigned_node(self) -> None:
        os.environ["FAKE_NODE_DELAY"] = "0.4"
        self.host_change(3)
        self.boundary()
        self.wait_for(lambda: self.node_count() == 1, "the start in flight")
        self.holder.turn["active"] = True
        raw = self.retire_input(4)
        self.holder.node_start.join(3)
        self.assertEqual(self.holder.node["phase"], "running")
        self.assertEqual(self.fake.prompts, [], "startup does not send during the newer Host turn")
        self.assertEqual(self.fake.stops, [], "the Host can still add useful input")
        # A foreign replacement is neither assigned nor stopped by this carrier.
        path = self.side_dir / "record.json"
        owned = path.read_bytes()
        record = json.loads(owned)
        record["holder_instance_id"] = "foreign"
        path.write_text(json.dumps(record))
        self.holder.turn["active"] = False
        self.boundary()
        self.assertEqual(self.fake.stops, [])
        path.write_bytes(owned)
        self.boundary()
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "unassigned node cleanup")
        self.assertEqual([row["params"]["expected_holder_instance_id"] for row in self.fake.stops], ["node-1"])
        self.assertEqual(self.fake.prompts, [])
        self.assertEqual((self.repo / ".kaola" / "heartbeat-prompt.json").read_bytes(), raw)

    def test_startup_coalesces_new_useful_work_until_the_host_turn_ends(self) -> None:
        os.environ["FAKE_NODE_DELAY"] = "0.4"
        self.host_change(3)
        self.boundary()
        self.wait_for(lambda: self.node_count() == 1, "the start in flight")
        self.holder.turn["active"] = True
        self.retire_input(4)
        self.holder.node_start.join(3)
        self.host_change(5)
        self.boundary()
        self.assertEqual(self.fake.prompts, [])
        self.assertEqual(self.fake.stops, [])
        self.finish_host_turn()
        self.wait_for(lambda: len(self.fake.prompts) == 1, "the useful batch after startup")
        self.assertEqual(self.node_count(), 1)
        self.assertIn("host revision 1..5", self.fake.prompts[0]["params"]["text"])
        self.checkpoint(self.batch_of(0), "node-1", through=5)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stop")

    def test_a_pinned_legacy_contract_keeps_revision_only_node_selection(self) -> None:
        self.retire_input(4)
        saved = holder_module._RECORD
        holder_module._RECORD = False
        try:
            doc = json.loads((self.repo / ".kaola" / "heartbeat-prompt.json").read_text())
            self.assertEqual(self.holder._node_host_pending(doc), 4)
        finally:
            holder_module._RECORD = saved

    def test_ordinary_worker_returns_reach_the_host_and_start_no_node(self) -> None:
        self.write_node_state()
        self.event("codex-KT-i1-a", "idle", 5)
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1, "a worker return reaches the Host at its boundary")
        self.assertIn("codex/codex-KT-i1-a/idle/5", prompts[0])
        self.finish_host_turn()
        self.event("codex-KT-i1-b", "terminated", 6)
        self.assertEqual(len(self.agent.prompts()), 2)
        self.finish_host_turn()
        time.sleep(0.3)
        self.assertEqual(self.node_count(), 0, "an ordinary return or termination starts no node")
        self.assertEqual(self.fake.prompts, [])
        self.assertEqual(sorted(self.confirmed_ids()), ["codex/codex-KT-i1-a/idle/5",
                                                        "codex/codex-KT-i1-b/terminated/6"])

    def test_one_host_turn_makes_one_batch_at_its_end(self) -> None:
        self.write_node_state()
        self.holder.turn["active"] = True
        self.host_change(3)
        self.boundary()
        self.host_change(4)
        self.boundary()
        time.sleep(0.3)
        self.assertEqual(self.node_count(), 0, "no node while the Host turn may still write")
        self.finish_host_turn()
        self.wait_for(lambda: len(self.fake.prompts) == 1, "the batch at the Host turn end")
        text = self.fake.prompts[0]["params"]["text"]
        self.assertIn("host revision 1..4", text, "both writes are one batch")
        self.assertNotIn("--events", text, "worker events are not node inputs")
        self.assertIn("Role limits", text)
        self.assertIn("never a restated, summarized or judged worker result", text)
        self.assertIn("exact-stop only a finished worker whose reclaim the Host recorded", text)
        self.boundary()
        time.sleep(0.2)
        self.assertEqual(len(self.fake.prompts), 1, "the same Host revision is sent once")
        self.assertEqual(self.node_count(), 1)

    def test_a_verified_batch_wakes_the_host_only_for_changed_attention(self) -> None:
        self.write_node_state()
        batch = self.first_node()
        argv = json.loads((Path(self.tmp.name) / "argv").read_text())
        self.assertEqual(argv[:1] + argv[argv.index("--role"):], ["start", "--role", "sideagent"],
                         "the recipe argv is run as given, no shell")
        text = self.fake.prompts[0]["params"]["text"]
        self.assertEqual(self.fake.prompts[0]["params"]["expected_holder_instance_id"], "node-1")
        self.assertIn(f"python3 {REPO / 'scripts' / 'kaola-dispatch.py'} state checkpoint --file "
                      f"{self.repo / '.kaola' / 'heartbeat-prompt.json'} --writer sideagent --source {batch}", text,
                      "the fresh node gets the exact command, without needing the Skill loaded")
        self.checkpoint(batch, "node-1", through=4)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the exact node stop")
        self.assertEqual(self.fake.stops[0]["params"]["expected_holder_instance_id"], "node-1")
        self.assertEqual(self.agent.prompts(), [], "a verified batch with unchanged attention stays quiet")
        self.assertEqual(self.holder.pending_worker_events, [])

        # The next Host change: a second fresh node whose checkpoint adds Host attention.
        self.host_change(5)
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 2, "the second node's batch")
        self.assertEqual(self.fake.prompts[1]["params"]["expected_holder_instance_id"], "node-2")
        self.assertIn("host revision 5..5", self.fake.prompts[1]["params"]["text"])
        self.checkpoint(self.batch_of(1), "node-2", through=5,
                        attention=[{"kind": "alerts", "id": "w1-gap", "why": "warn"}])
        self.holder.turn["active"] = True
        self.sideagent_end(12, 2, holder="node-2")
        self.wait_for(lambda: self.log_kinds().count("sideagent_node_stopped") == 2, "the second stop")
        self.assertEqual(self.agent.prompts(), [], "a busy Host is not interrupted")
        self.finish_host_turn()
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1, "changed attention wakes the Host exactly once")
        self.assertIn("verified; Host attention changed", prompts[0])
        self.assertIn("w1-gap", prompts[0], "the Host reads the changed view")
        self.finish_host_turn()
        self.boundary()
        time.sleep(0.2)
        self.assertEqual(len(self.agent.prompts()), 1)
        self.assertEqual(len(self.fake.prompts), 2)
        self.assertEqual(self.holder.pending_worker_events, [])
        settled = [json.loads(line) for line in
                   (Path(self.holder.args.record_dir) / "events.jsonl").read_text().splitlines()
                   if json.loads(line).get("kind") == "sideagent_node_settled"]
        self.assertEqual([(entry["checkpoint"], entry["host_woken"]) for entry in settled],
                         [("verified", False), ("verified", True)])

    def test_the_hosts_own_attention_change_during_a_batch_stays_quiet(self) -> None:
        """Native QA: the Host settled a decision and retired an alert while
        a node ran; the node's verified batch then woke the Host for the
        Host's own change."""
        self.write_node_state(attention=[{"kind": "alerts", "id": "old-gap", "why": "warn"}])
        batch = self.first_node()
        self.checkpoint(batch, "node-1", through=4, attention=[], author=None)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the exact node stop")
        self.assertEqual(self.agent.prompts(), [], "the Host's own change is not news to it")
        log = Path(self.holder.args.record_dir) / "events.jsonl"
        settled = [json.loads(line) for line in log.read_text().splitlines()
                   if json.loads(line)["kind"] == "sideagent_node_settled"]
        self.assertEqual([(row["checkpoint"], row["host_woken"]) for row in settled], [("verified", False)])

    def test_a_checkpoint_short_of_its_batch_is_partial_and_reaches_the_host_once(self) -> None:
        self.write_node_state()
        batch = self.first_node()
        self.checkpoint(batch, "node-1")  # --through-host-revision omitted
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stop")
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1, "an omitted range is partial, not quiet")
        self.assertIn("checkpoint partial: host revision 1..4 not handled", prompts[0])
        self.finish_host_turn()
        self.boundary()
        time.sleep(0.2)
        self.assertEqual(self.node_count(), 1, "no node restarts for the same range")

        self.host_change(6)
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 2, "a later Host change")
        self.checkpoint(self.batch_of(1), "node-2", through=2)  # lowered
        self.sideagent_end(12, 2, holder="node-2")
        self.wait_for(lambda: self.log_kinds().count("sideagent_node_stopped") == 2, "the second stop")
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 2)
        self.assertIn("checkpoint partial: host revision 3..6 not handled", prompts[1])
        self.finish_host_turn()
        self.boundary()
        time.sleep(0.2)
        self.assertEqual(self.node_count(), 2, "no restart storm")
        self.assertEqual(self.holder.pending_worker_events, [])

    def test_a_partial_checkpoint_returns_its_batch_to_the_host_once(self) -> None:
        self.write_node_state()
        batch = self.first_node()
        self.checkpoint(batch, "node-1", through=4, verified=False)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stop")
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1, "the unsettled batch reaches the Host once")
        self.assertIn("checkpoint partial", prompts[0])
        self.finish_host_turn()
        self.boundary()
        time.sleep(0.2)
        self.assertEqual(len(self.fake.prompts), 1, "and no node is started for it")
        self.assertEqual(self.holder.pending_worker_events, [])

    def test_a_missing_checkpoint_reaches_the_host_once(self) -> None:
        self.write_node_state()
        self.first_node()
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the node stop")
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1)
        self.assertIn("checkpoint missing", prompts[0])
        self.finish_host_turn()
        self.assertEqual(self.node_count(), 1)

    def test_a_batch_the_node_does_not_admit_is_returned_once_and_not_resent(self) -> None:
        self.write_node_state()
        self.fake.refuse = True
        self.host_change(4)
        self.boundary()
        self.wait_for(lambda: "sideagent_node_stopped" in self.log_kinds(), "the refused node's stop")
        self.assertEqual(len(self.fake.prompts), 1)
        prompts = self.agent.prompts()
        self.assertEqual(len(prompts), 1, "the Host is told once")
        self.assertIn("did not admit", prompts[0])
        self.assertIn("host revision 1..4 not handled", prompts[0])
        self.finish_host_turn()
        self.host_change(5)
        self.boundary()
        time.sleep(0.3)
        self.assertEqual((len(self.fake.prompts), self.node_count()), (1, 1), "no resend, no restart")
        self.assertEqual(self.holder.pending_worker_events, [])

    def test_an_unconfirmed_stop_blocks_a_competing_node(self) -> None:
        self.write_node_state()
        self.fake.ignore_stop = True
        batch = self.first_node()
        self.checkpoint(batch, "node-1", through=4)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stop_unconfirmed" in self.log_kinds(), "the unconfirmed stop")
        self.host_change(5)
        self.boundary()
        time.sleep(0.3)
        self.assertEqual(self.node_count(), 1, "no second node starts")

    def test_a_stopped_record_is_not_a_stopped_node_until_its_holder_is_gone(self) -> None:
        self.write_node_state()
        self.fake.linger = True
        batch = self.first_node()
        self.checkpoint(batch, "node-1", through=4)
        self.sideagent_end(9, 1, holder="node-1")
        self.wait_for(lambda: "sideagent_node_stop_unconfirmed" in self.log_kinds(),
                      "a stop whose holder still runs")
        self.assertNotIn("sideagent_node_stopped", self.log_kinds())
        record = json.loads((self.side_dir / "record.json").read_text())
        record["holder_pid"] = self.fake.dead_pid
        (self.side_dir / "record.json").write_text(json.dumps(record))
        self.host_change(5)
        self.boundary()
        self.wait_for(lambda: len(self.fake.prompts) == 2, "a fresh node once the old holder is gone")
        self.assertEqual(self.fake.prompts[1]["params"]["expected_holder_instance_id"], "node-2")
        self.assertIn("sideagent_node_stop_confirmed_late", self.log_kinds())
        self.assertNotIn("sideagent_node_start_failed", self.log_kinds())

    def test_a_stop_whose_caller_gave_up_still_ends_the_holder(self) -> None:
        ours, theirs = socket.socketpair()
        theirs.sendall(b'{"op": "stop"}\n')
        theirs.close()
        exits: list[int] = []

        class Exited(Exception):
            pass

        def fake_exit(code: int) -> None:
            exits.append(code)
            raise Exited

        saved_exit, saved_handle = holder_module.os._exit, self.holder.handle_request
        holder_module.os._exit = fake_exit
        self.holder.handle_request = lambda message: {"stopped": True, "_exit_after_reply": True}
        try:
            with self.assertRaises(Exited):
                self.holder.serve_connection(ours)
        finally:
            holder_module.os._exit = saved_exit
            self.holder.handle_request = saved_handle
        self.assertEqual(exits, [0], "the reply cannot be sent, the holder still exits")

    def test_a_stopping_carrier_ends_its_running_node_and_starts_none(self) -> None:
        self.write_node_state()
        self.first_node()
        self.holder.stop_requested = True
        self.holder._reclaim_node()
        self.assertEqual([stop["params"]["expected_holder_instance_id"] for stop in self.fake.stops],
                         ["node-1"], "the carrier's own node is not a dispatched worker")
        self.assertIn("sideagent_node_stopped", self.log_kinds())
        self.host_change(5)
        self.boundary()
        time.sleep(0.3)
        self.assertEqual(self.node_count(), 1, "a stopping carrier starts no node")

    def test_a_node_start_in_flight_ends_with_the_stopping_carrier(self) -> None:
        self.write_node_state()
        os.environ["FAKE_NODE_DELAY"] = "0.6"
        self.host_change(4)
        self.boundary()
        self.wait_for(lambda: self.node_count() == 1, "the start in flight")
        self.holder.stop_requested = True
        self.holder._reclaim_node()
        self.assertEqual([stop["params"]["expected_holder_instance_id"] for stop in self.fake.stops],
                         ["node-1"], "the start is waited for, then its node is stopped")
        self.assertEqual(self.fake.prompts, [], "no batch goes to a node of a stopping carrier")

    def test_a_start_slower_than_the_stop_is_found_by_its_record(self) -> None:
        self.write_node_state()
        holder_module.NODE_RECLAIM_SECONDS = 0.3
        os.environ["FAKE_NODE_DELAY"] = "3"
        self.host_change(4)
        self.boundary()
        self.wait_for(lambda: (self.side_dir / "record.json").exists(), "the node's early record")
        self.holder.stop_requested = True
        self.holder._reclaim_node()
        self.assertEqual([stop["params"]["expected_holder_instance_id"] for stop in self.fake.stops],
                         ["node-1"], "the record naming this carrier as dispatcher finds the node")
        self.holder.node_start.join(5)

    def test_a_resume_recipe_or_failed_start_is_not_retried(self) -> None:
        self.write_node_state(argv=["start", "--repo", str(self.repo), "--session", "zcode-KT-sideagent",
                                    "--role", "sideagent", "--continue"], host_revision=2)
        self.boundary()
        self.assertIn("sideagent_node_recipe_refused", self.log_kinds())
        self.assertEqual(self.node_count(), 0)
        os.environ["FAKE_NODE_RECORD"] = str(Path(self.tmp.name) / "missing" / "record.json")
        self.host_change(4)
        self.boundary()
        self.wait_for(lambda: "sideagent_node_start_failed" in self.log_kinds(), "the failed start")
        self.wait_for(lambda: len(self.agent.prompts()) == 1, "the Host told of the failure")
        self.assertIn("sideagent node start failed", self.agent.prompts()[0])
        self.assertIn("host revision 1..4 not handled", self.agent.prompts()[0])
        self.finish_host_turn()
        self.host_change(5)
        self.boundary()
        time.sleep(0.3)
        self.assertEqual(self.node_count(), 1, "one recorded failure, no retry storm")
        self.assertEqual(len(self.agent.prompts()), 1)

    def test_the_checkout_entrypoint_recipe_names_the_bound_platform_first(self) -> None:
        tail = ["start", "--repo", str(self.repo), "--session", "zcode-KT-sideagent", "--role", "sideagent"]
        self.write_node_state(argv=["zcode", *tail])
        self.assertIsNotNone(self.holder._node_binding())
        self.write_node_state(argv=["codex", *tail])
        self.assertIsNone(self.holder._node_binding(), "another platform's start is not this binding")
        self.assertIn("sideagent_node_recipe_refused", self.log_kinds())

    def test_a_holder_known_not_to_be_the_host_never_starts_a_node(self) -> None:
        self.holder.session_role = "elite"
        self.write_node_state(host_revision=4)
        with self.holder.worker_events_lock:
            self.assertEqual(self.holder._relay_pass(), {}, "its own turn end relays nothing")
        self.event("codex-KT-i1-a", "idle", 5)
        time.sleep(0.3)
        self.assertFalse((Path(self.tmp.name) / "count").exists(), "no node is started")
        self.assertEqual(self.fake.prompts, [])
        self.assertNotIn("sideagent_node_started", self.log_kinds())
        self.assertEqual(len(self.agent.prompts()), 1, "the event still reaches the session it names")


class HostPreserveStop(WorkerTree):
    """An explicit preserve intent keeps a Host's dispatched worker trees
    across its stop; the default Host stop is unchanged."""

    def host(self, preserve: bool):
        args = argparse.Namespace(record_dir=str(self.side_dir), socket=str(self.side_dir / "h.sock"),
                                  platform="zcode", session="zcode-KT-orchestrator-main", repo=self.tmp.name,
                                  init_meta="", command="stub")
        holder = holder_module.Holder(args)
        holder.agent = RealAgent()
        holder.session_role = "host"
        holder.preserve_dispatched = preserve
        holder.agent_child_groups = {pgid: dict(members) for pgid, members in self.noted.items()}
        return holder

    def test_preserve_keeps_the_complete_worker_tree_on_cooperative_stop(self) -> None:
        holder = self.host(True)
        holder._terminate_group(False)
        self.groups.append(holder.agent.proc.pid)
        self.assertEqual(holder.swept_child_pgids, [self.unrelated.pid])
        for pid in (self.holder.pid, self.native, self.tool, self.orphan.pid):
            self.assertTrue(self.alive(pid), f"worker process {pid} survived the Host stop")

    def test_preserve_on_dead_holder_cleanup_and_default_stop_unchanged(self) -> None:
        record = {"session_role": "host",
                  "agent_child_groups": {str(g): {str(p): s for p, s in m.items()} for g, m in self.noted.items()}}
        self.assertEqual(acp_module.recorded_groups(record, self.side_dir, verified_only=True,
                                                    preserve_dispatched=True), [self.unrelated.pid])
        self.assertEqual(sorted(acp_module.recorded_groups(record, self.side_dir, verified_only=True)),
                         sorted(self.groups), "without the intent a Host stop sweeps as before")
        holder = self.host(False)
        holder._terminate_group(False)
        self.groups.append(holder.agent.proc.pid)
        self.assertIn(self.holder.pid, holder.swept_child_pgids, "the default stop still ends its workers")

    def test_a_live_holder_without_the_feature_refuses_the_preserve_intent(self) -> None:
        directory = Path(self.tmp.name) / "host-record"
        directory.mkdir()
        args = argparse.Namespace(platform="zcode", session="zcode-KT-orchestrator-main",
                                  preserve_dispatched_workers=True)
        (directory / "record.json").write_text(json.dumps({"holder_pid": os.getpid(),
                                                           "holder_features": ["heartbeat-state/2"]}))
        refused = acp_module.preserve_refusal(args, self.tmp.name, directory)
        self.assertEqual((refused["result"], refused["reason"], refused["mutation_status"]),
                         ("refused", "preserve-unsupported", "not_started"))
        (directory / "record.json").write_text(json.dumps({"holder_pid": os.getpid(),
                                                           "holder_features": list(holder_module.HOLDER_FEATURES)}))
        self.assertIsNone(acp_module.preserve_refusal(args, self.tmp.name, directory))
        (directory / "record.json").write_text(json.dumps({"holder_pid": 999999,
                                                           "holder_features": ["heartbeat-state/2"]}))
        self.assertIsNone(acp_module.preserve_refusal(args, self.tmp.name, directory),
                          "a dead holder is swept by the Runner, which honours the intent")
        self.assertIsNone(acp_module.preserve_refusal(
            argparse.Namespace(platform="zcode", session="s", preserve_dispatched_workers=False),
            self.tmp.name, directory))
        self.assertIn("preserve-dispatched/1", holder_module.HOLDER_FEATURES)
        self.assertEqual(acp_module.PRESERVE_FEATURE, "preserve-dispatched/1")


class RunnerPreserveFlag(unittest.TestCase):
    """The platform Runner forwards the explicit intent; without it the stop
    argument list is unchanged."""

    def test_stop_and_drain_restart_forward_the_intent_only_when_given(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kpr-i255-tmux-") as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            for entry in (REPO / "scripts").iterdir():
                if entry.name != "kaola-acp.py":
                    (scripts / entry.name).symlink_to(entry)
            (scripts / "kaola-acp.py").write_text(
                "import json, sys\nprint(json.dumps({'argv': sys.argv[1:]}))\n", encoding="utf-8")
            repo = root / "repo"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV
                   and k not in ("KPR_CANONICAL_REPO", "KAOLA_PROJECT_RUNNER_CANONICAL_REPO")}

            def argv(*args: str) -> list[str]:
                done = subprocess.run(["bash", str(scripts / "kaola-tmux.sh"), "zcode", *args, "--repo",
                                       str(repo), "--session", "zcode-KT-orchestrator-main"],
                                      capture_output=True, text=True, env=env, timeout=60)
                self.assertEqual(done.returncode, 0, done.stderr)
                return json.loads(done.stdout.strip().splitlines()[-1])["argv"]

            self.assertIn("--preserve-dispatched-workers", argv("stop", "--preserve-dispatched-workers"))
            self.assertNotIn("--preserve-dispatched-workers", argv("stop"))
            self.assertIn("--preserve-dispatched-workers",
                          argv("drain-restart", "--continue", "--preserve-dispatched-workers"))


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

    def test_node_reference_names_the_implemented_contract(self) -> None:
        template = (REPO / "templates/orchestrator/references/sideagent-node.md").read_bytes()
        generated = (self.ORCH / "references/sideagent-node.md").read_bytes()
        self.assertEqual(template, generated)
        self.assertLessEqual(len(generated), 8192)
        text = generated.decode()
        for term in ("scope: implementation", "core_revision", "worker_scope", "prompt_source", "on-hold",
                     "excerpt_truncated", "output-absent", "prior_acceptance", "undecided", "host_revision",
                     "writer_holder", "pending_host_changes", "sideagent-node/1", "maintenance-returned", "last_verified", "binding-superseded",
                     "sideagent_node_stop_unconfirmed", "--preserve-dispatched-workers",
                     acp_module.PRESERVE_FEATURE, "preserve-unsupported", "rebind-host"):
            self.assertIn(term, text)
        for disposition in dispatch_module.DISPOSITIONS:
            self.assertIn(f"`{disposition}`", text)
        self.assertIn("sideagent-node/1", holder_module.HOLDER_FEATURES)
        skill = (self.ORCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("](references/sideagent-node.md)", skill)
        for name in ("lifecycle-state.md", "dispatch-collect.md"):
            self.assertIn("[sideagent-node.md](sideagent-node.md)",
                          (self.ORCH / "references" / name).read_text(encoding="utf-8"))
        report = (self.DELEGATOR / "references/inquiry-report.md").read_text(encoding="utf-8")
        self.assertIn("maintenance.last_verified", report)

    def test_host_owns_dispatch_and_the_sideagent_allocates_nothing(self) -> None:
        skill = (self.ORCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("You pick presets, write assignments, dispatch, judge originals", skill)
        self.assertNotIn("Sideagent runs dispatch", skill)
        lifecycle = (self.ORCH / "references/lifecycle-state.md").read_text(encoding="utf-8")
        self.assertIn("preset choice", lifecycle)
        self.assertIn("It assigns, grants\n  and accepts nothing", lifecycle)
        self.assertNotIn("it selects presets", lifecycle)
        dispatch = (self.ORCH / "references/dispatch-collect.md").read_text(encoding="utf-8")
        self.assertIn("## Who dispatches", dispatch)
        self.assertIn("writes and allocates no assignment", dispatch)
        self.assertNotIn("runs routine dispatch", dispatch)
        skeleton = (self.ORCH / "references/heartbeat-skeleton.md").read_text(encoding="utf-8")
        self.assertIn("Host 记决定与派发", skeleton)
        self.assertNotIn("Sideagent 记派发", skeleton)
        design = (REPO / "docs/designs/lifecycle-state-2026-10-04/design.md").read_text(encoding="utf-8")
        self.assertNotIn("Sideagent 执行派发", design)
        self.assertNotIn("Sideagent 在当前授权、profile 和真实容量内选配", design)

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
