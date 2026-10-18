#!/usr/bin/env python3
"""Issue #349: a wrong verb on an unchanged Host-owned input settles as retained.

A selected ``host:<kind>/<id>@<rev>`` whose current record is still that
revision, was written by the Host, and names ``owner``, ``next`` or ``wait``
is retained whichever verb the node used. It is not returned and it does not
wake the Host. A vanished row, a later rewrite, a row with no next reader,
and a record this node did not write stay on the existing paths.

The single unreproduced ``checkpoint: missing`` with no ``missing_sources``
is not asserted here.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ISSUE255 = REPO / "tests" / "contract" / "test-issue-255-lifecycle-state.py"
DECISION_SENTENCE = (
    "A Host decision row is `retained`, or `retired:decisions/<id>` when the row is gone, "
    "never `applied`.")

spec = importlib.util.spec_from_file_location("issue255_checkpoint_349", ISSUE255)
issue255 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(issue255)


def _name(ident: str) -> str:
    return ident.split(":", 1)[1].rsplit("@", 1)[0]


class CheckpointVerb(issue255.MaintenanceCheckpoint):
    """Checkpoint settlement for Host-owned rows, against the real state tool."""

    NEXT = {"owner": "host", "question": "q", "status": "pending", "next": "host adopts"}
    ANSWER = {"owner": "host", "question": "q", "answer": "owner approved", "status": "pending"}

    def decision(self, ident: str, patch: dict, env: dict | None = None) -> int:
        code, out = self.update("host", "decisions", ident, patch, env=env)
        self.assertEqual(code, 0, out)
        return self.doc()["host_revision"]

    def entries(self, pending: list[str], overrides: dict | None = None) -> list[dict]:
        overrides = overrides or {}
        rows = []
        for ident in pending:
            if ident in overrides:
                rows.append(overrides[ident])
            else:
                rows.append({"input": ident, "retained": _name(ident)})
        return rows

    def checkpoint_pending(self, node: dict, batch: str, through: int,
                           overrides: dict | None = None, pending: list[str] | None = None):
        pending = self.sideagent_view()["pending_host_changes"] if pending is None else pending
        return self.checkpoint(node, batch, through, self.entries(pending, overrides))

    def assert_retained(self, node: dict, batch: str, through: int, ident: str,
                        entry: dict) -> dict:
        code, out = self.checkpoint_pending(node, batch, through, {ident: entry})
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertTrue(value["verified"], value)
        self.assertEqual(value["returned_to_host"], {})
        self.assertIn(ident, value["settled"])
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})
        attention = [row["id"] for row in json.loads(self.doc()["body"])["attention"]]
        self.assertNotIn("maintenance-returned", attention)
        return value

    def unverified_host(self) -> dict:
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.records / "zcode" / "zcode-KT-host" / digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "record.json").write_text(
            json.dumps({"holder_instance_id": "host-1"}), encoding="utf-8")
        return self.caller_env("zcode-KT-host", "host-1")

    def test_owner_and_next_retained_verifies(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-next", self.NEXT)
        ident = f"host:decisions/d-next@{rev}"
        self.assert_retained(self.node("node-1"), "b-retained-next", rev, ident,
                             {"input": ident, "retained": "decisions/d-next"})
        self.assertEqual(self.doc()["state"]["decisions"]["d-next"]["owner"], "host")

    def test_owner_and_next_applied_settles_as_retained(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-next", self.NEXT)
        ident = f"host:decisions/d-next@{rev}"
        self.assert_retained(self.node("node-1"), "b-applied-next", rev, ident,
                             {"input": ident, "applied": ["decisions/d-next"]})

    def test_answer_without_next_retained_verifies(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-answer", self.ANSWER)
        ident = f"host:decisions/d-answer@{rev}"
        self.assert_retained(self.node("node-1"), "b-retained-answer", rev, ident,
                             {"input": ident, "retained": "decisions/d-answer"})

    def test_answer_without_next_applied_settles_as_retained(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-answer", self.ANSWER)
        ident = f"host:decisions/d-answer@{rev}"
        self.assert_retained(self.node("node-1"), "b-applied-answer", rev, ident,
                             {"input": ident, "applied": ["decisions/d-answer"]})

    def test_unverified_host_writer_applied_settles_as_retained(self) -> None:
        self.init()
        self.bind()
        env = self.unverified_host()
        rev = self.decision("d-unverified", self.NEXT, env=env)
        row = self.doc()["state"]["decisions"]["d-unverified"]
        self.assertEqual(row["writer"], "host:zcode-KT-host (role unverified)")
        ident = f"host:decisions/d-unverified@{rev}"
        self.assert_retained(self.node("node-1"), "b-unverified", rev, ident,
                             {"input": ident, "applied": ["decisions/d-unverified"]})

    def test_a_host_task_with_next_applied_settles_as_retained(self) -> None:
        self.init()
        self.bind()
        code, out = self.update("host", "tasks", "t-owned",
                                {"stage": "todo", "goal": "g", "next": "host plans"})
        self.assertEqual(code, 0, out)
        rev = self.doc()["host_revision"]
        ident = f"host:tasks/t-owned@{rev}"
        self.assert_retained(self.node("node-1"), "b-task", rev, ident,
                             {"input": ident, "applied": ["tasks/t-owned"]})

    def test_a_host_task_with_no_reader_applied_still_returns(self) -> None:
        self.init()
        self.bind()
        code, out = self.update("host", "tasks", "t-bare", {"stage": "doing", "goal": "a"})
        self.assertEqual(code, 0, out)
        rev = self.doc()["host_revision"]
        ident = f"host:tasks/t-bare@{rev}"
        code, out = self.checkpoint_pending(
            self.node("node-1"), "b-bare", rev, {ident: {"input": ident, "applied": ["tasks/t-bare"]}})
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertFalse(value["verified"], value)
        self.assertIn("not a current record this node wrote", value["returned_to_host"][ident])
        self.assertEqual(self.doc()["state"]["alerts"]["maintenance-returned"]["owner"], "host")

    def test_another_nodes_record_applied_still_returns(self) -> None:
        self.init()
        self.bind()
        code, out = self.update("host", "tasks", "t-side", {"stage": "todo", "goal": "g"})
        self.assertEqual(code, 0, out)
        node1 = self.node("node-1")
        code, out = self.update("sideagent", "tasks", "t-side", {"next": "node continues"},
                                "--expect-rev", "1", env=node1)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t-side"]["writer_holder"], "node-1")
        rev = self.doc()["state"]["tasks"]["t-side"]["host_revision"]
        ident = f"host:tasks/t-side@{rev}"
        code, out = self.checkpoint_pending(
            self.node("node-2"), "b-foreign", self.doc()["host_revision"],
            {ident: {"input": ident, "applied": ["tasks/t-side"]}})
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertFalse(value["verified"], value)
        self.assertIn("not a current record this node wrote", value["returned_to_host"][ident])

    def test_a_wrong_retained_name_on_a_standing_decision_settles(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-wrong", self.NEXT)
        ident = f"host:decisions/d-wrong@{rev}"
        self.assert_retained(self.node("node-1"), "b-wrong", rev, ident,
                             {"input": ident, "retained": "tasks/not-this"})

    def test_neither_verb_on_a_standing_decision_settles(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-neither", self.NEXT)
        ident = f"host:decisions/d-neither@{rev}"
        self.assert_retained(self.node("node-1"), "b-neither", rev, ident, {"input": ident})

    def test_an_unselected_standing_decision_stays_returned(self) -> None:
        self.init()
        self.bind()
        sent = self.doc()["host_revision"]
        pending = self.sideagent_view()["pending_host_changes"]
        rev = self.decision("d-later", self.NEXT)
        ident = f"host:decisions/d-later@{rev}"
        self.assertGreater(rev, sent)
        code, out = self.checkpoint(
            self.node("node-1"), "b-later", sent,
            self.entries(pending, {ident: {"input": ident, "applied": ["decisions/d-later"]}})
            + [{"input": ident, "applied": ["decisions/d-later"]}])
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertFalse(value["verified"], value)
        self.assertIn("not a current record this node wrote", value["returned_to_host"][ident])
        self.assertNotIn(ident, value["settled"])

    def test_a_decision_written_during_the_batch_stays_verified(self) -> None:
        self.init()
        self.bind()
        sent = self.decision("d-before", self.NEXT)
        pending = self.sideagent_view()["pending_host_changes"]
        later = self.decision("d-during", self.NEXT)
        self.assertGreater(later, sent)
        code, out = self.checkpoint(self.node("node-1"), "b-mid", sent, self.entries(pending))
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertTrue(value["verified"], value)
        self.assertEqual(value["returned_to_host"], {})
        self.assertEqual(value["host_revision"]["through"], sent)
        self.assertEqual(value["host_revision"]["current"], later)
        self.assertIn(f"host:decisions/d-during@{later}", self.sideagent_view()["pending_host_changes"])
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})

    def test_applied_on_a_rewritten_decision_stays_returned(self) -> None:
        self.init()
        self.bind()
        sent = self.decision("d-rewrite", self.NEXT)
        ident = f"host:decisions/d-rewrite@{sent}"
        pending = self.sideagent_view()["pending_host_changes"]
        code, out = self.update("host", "decisions", "d-rewrite", {"next": "revised"}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        self.assertGreater(self.doc()["host_revision"], sent)
        code, out = self.checkpoint(
            self.node("node-1"), "b-rewrite-applied", sent,
            self.entries(pending, {ident: {"input": ident, "applied": ["decisions/d-rewrite"]}}))
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertFalse(value["verified"], value)
        self.assertIn("not a current record this node wrote", value["returned_to_host"][ident])
        self.assertNotIn("superseded", value)

    def test_retained_on_a_rewritten_decision_stays_superseded(self) -> None:
        self.init()
        self.bind()
        sent = self.decision("d-rewrite", self.NEXT)
        ident = f"host:decisions/d-rewrite@{sent}"
        pending = self.sideagent_view()["pending_host_changes"]
        code, out = self.update("host", "decisions", "d-rewrite", {"next": "revised"}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        later = self.doc()["host_revision"]
        code, out = self.checkpoint(
            self.node("node-1"), "b-rewrite-retained", sent,
            self.entries(pending, {ident: {"input": ident, "retained": "decisions/d-rewrite"}}))
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertTrue(value["verified"], value)
        self.assertEqual(value["returned_to_host"], {})
        self.assertEqual(value["superseded"], [ident])
        self.assertEqual(self.sideagent_view()["pending_host_changes"],
                         [f"host:decisions/d-rewrite@{later}"])

    def test_a_listed_vanished_decision_settles_with_the_live_inputs(self) -> None:
        self.init()
        self.bind()
        sent = self.decision("d-gone", self.NEXT)
        ident = f"host:decisions/d-gone@{sent}"
        pending = self.sideagent_view()["pending_host_changes"]
        code, out = self.update("host", "decisions", "d-gone",
                                {"status": "settled", "evidence": ["README.md"]}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        self.assertNotIn("d-gone", self.doc()["state"].get("decisions") or {})
        code, out = self.checkpoint(self.node("node-1"), "b-gone-listed", sent, self.entries(pending))
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertTrue(value["verified"], value)
        self.assertEqual(value["returned_to_host"], {})
        self.assertIn(ident, value["settled"])
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})

    def test_empty_entries_after_a_settled_decision_leave_live_sections_unaccounted(self) -> None:
        self.init()
        self.bind()
        sent = self.decision("d-gone", self.NEXT)
        ident = f"host:decisions/d-gone@{sent}"
        pending = self.sideagent_view()["pending_host_changes"]
        code, out = self.update("host", "decisions", "d-gone",
                                {"status": "settled", "evidence": ["README.md"]}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        code, out = self.checkpoint(self.node("node-1"), "b-gone-empty", sent, [])
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertFalse(value["verified"], value)
        self.assertNotIn(ident, value["returned_to_host"])
        self.assertNotIn(ident, value["settled"])
        for item in pending:
            if item.startswith("host:section/"):
                self.assertEqual(value["returned_to_host"].get(item), "unaccounted", value)
        self.assertIn("maintenance-returned", self.doc()["state"].get("alerts") or {})

    def test_retired_decisions_id_still_settles_a_gone_row(self) -> None:
        self.init()
        self.bind()
        sent = self.decision("d-gone", self.NEXT)
        ident = f"host:decisions/d-gone@{sent}"
        pending = self.sideagent_view()["pending_host_changes"]
        code, out = self.update("host", "decisions", "d-gone",
                                {"status": "settled", "evidence": ["README.md"]}, "--expect-rev", "1")
        self.assertEqual(code, 0, out)
        code, out = self.checkpoint(
            self.node("node-1"), "b-gone-retired", sent,
            self.entries(pending, {ident: {"input": ident, "applied": ["retired:decisions/d-gone"]}}))
        self.assertEqual(code, 0, out)
        value = out["value"]
        self.assertTrue(value["verified"], value)
        self.assertEqual(value["returned_to_host"], {})
        self.assertIn(ident, value["settled"])

    def drive(self, batch: str, holder_id: str, through: int, attention_sent: str | None = None):
        holder = issue255.holder_module.Holder.__new__(issue255.holder_module.Holder)
        holder.args = argparse.Namespace(repo=str(self.repo))
        holder.node = {"batch": batch, "holder": holder_id, "fingerprint": "fp",
                       "sent_through": through, "phase": "running",
                       "attention_sent": attention_sent}
        holder.host_attention_seen = None
        holder.session_role = "host"
        log: list[dict] = []

        class Events:
            def append(self, row: dict) -> int:
                log.append(row)
                return len(log)

        holder.events = Events()
        failures: list[tuple] = []
        holder._maintenance_failure = lambda *args, **kwargs: failures.append((args, kwargs))
        holder._stop_node = lambda *args, **kwargs: None
        end = {"holder_instance_id": holder_id, "turn_fingerprint": "fp",
               "turn_outcome": "turn_completed", "reason": "turn end"}
        holder._settle_node_batch([end])
        return end, log, failures

    def test_applied_decision_does_not_alert_or_wake_the_host(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-next", self.NEXT)
        ident = f"host:decisions/d-next@{rev}"
        self.assert_retained(self.node("node-1"), "b-wake", rev, ident,
                             {"input": ident, "applied": ["decisions/d-next"]})
        end, log, failures = self.drive("b-wake", "node-1", rev)
        self.assertTrue(end.get("node_quiet"))
        self.assertNotIn("host_owned", end)
        settled = [row for row in log if row.get("kind") == "sideagent_node_settled"]
        self.assertEqual([(row["checkpoint"], row["host_woken"]) for row in settled],
                         [("verified", False)])
        self.assertEqual(failures, [])

    def test_a_standing_only_partial_does_not_wake_the_host(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-next", self.NEXT)
        ident = f"host:decisions/d-next@{rev}"
        doc = self.doc()
        doc["state"]["maintenance"] = {"handled_host_revision": 0, "last_checkpoint": {
            "batch": "b-plant", "node": {"holder_instance_id": "node-1"}, "verified": False,
            "host_revision": {"from": 0, "through": rev, "current": rev},
            "returned_to_host": {ident: "decisions/d-next is not a current record this node wrote"},
            "settled": []}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        end, log, failures = self.drive("b-plant", "node-1", rev)
        self.assertTrue(end.get("node_quiet"), end)
        self.assertNotIn("host_owned", end)
        settled = [row for row in log if row.get("kind") == "sideagent_node_settled"]
        self.assertEqual(settled[0]["host_woken"], False)
        self.assertEqual(failures, [])

    def test_a_mix_of_standing_and_unaccounted_still_wakes(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-next", self.NEXT)
        ident = f"host:decisions/d-next@{rev}"
        other = "host:tasks/t-missing@1"
        doc = self.doc()
        doc["state"]["maintenance"] = {"handled_host_revision": 0, "last_checkpoint": {
            "batch": "b-mix", "node": {"holder_instance_id": "node-1"}, "verified": False,
            "host_revision": {"from": 0, "through": rev, "current": rev},
            "returned_to_host": {
                ident: "decisions/d-next is not a current record this node wrote",
                other: "unaccounted"},
            "settled": []}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        end, log, failures = self.drive("b-mix", "node-1", rev)
        self.assertTrue(end.get("host_owned"), end)
        self.assertFalse(end.get("node_quiet"))
        settled = [row for row in log if row.get("kind") == "sideagent_node_settled"]
        self.assertEqual(settled[0]["host_woken"], True)
        self.assertEqual(settled[0]["checkpoint"], "partial")
        self.assertTrue(failures)

    def test_a_standing_only_alert_is_not_attention_news(self) -> None:
        self.init()
        self.bind()
        rev = self.decision("d-next", self.NEXT)
        ident = f"host:decisions/d-next@{rev}"
        doc = self.doc()
        doc["state"].setdefault("alerts", {})["maintenance-returned"] = {
            "level": "warn", "owner": "host", "writer": "sideagent", "writer_holder": "node-1",
            "summary": "planted", "inputs": {ident: {"why": "other", "host_revision_through": rev}}}
        doc["state"]["maintenance"] = {"handled_host_revision": rev, "last_checkpoint": {
            "batch": "b-attn", "node": {"holder_instance_id": "node-1"}, "verified": True,
            "host_revision": {"from": 0, "through": rev, "current": rev},
            "returned_to_host": {}, "settled": [ident]}}
        doc["body"] = json.dumps({"view": "host", "attention": [
            {"kind": "alerts", "id": "maintenance-returned", "why": "warn"},
            {"kind": "decisions", "id": "d-next", "why": "host-decision"}]})
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        end, log, failures = self.drive("b-attn", "node-1", rev, attention_sent="sha256:sent")
        self.assertTrue(end.get("node_quiet"), end)
        self.assertNotIn("host_owned", end)
        settled = [row for row in log if row.get("kind") == "sideagent_node_settled"]
        self.assertEqual([(row["checkpoint"], row["host_woken"]) for row in settled],
                         [("verified", False)])
        self.assertNotIn("attention_changed", settled[0])
        self.assertEqual(failures, [])


class PromptVerb(unittest.TestCase):
    def test_prompts_name_the_host_decision_verb_once(self) -> None:
        holder = issue255.holder_module.Holder.__new__(issue255.holder_module.Holder)
        holder.host_name = "Host"
        holder.args = argparse.Namespace(session="zcode-KT-host", repo=str(REPO))
        holder._state_tool = lambda: None
        prompt = holder._node_prompt("b-1", 0, 1, None)
        self.assertEqual(prompt.count(DECISION_SENTENCE), 1)
        for name in ("templates/orchestrator/references/sideagent-node.md",
                     "templates/orchestrator/references/duty-reconcile.md"):
            text = (REPO / name).read_text(encoding="utf-8")
            self.assertEqual(text.count(DECISION_SENTENCE), 1, name)
            self.assertLessEqual(len(text.encode()), 8192, name)
        api = (REPO / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertEqual(api.count(DECISION_SENTENCE), 1)
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased, _, _ = changelog.partition("## 0.9.18")
        self.assertIn("## Unreleased", unreleased)
        self.assertIn("#349", unreleased)
        self.assertIn("Seats: restart required", unreleased)


if __name__ == "__main__":
    unittest.main(verbosity=2)
