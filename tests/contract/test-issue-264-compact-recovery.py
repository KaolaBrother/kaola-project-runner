#!/usr/bin/env python3
"""Issue #264: post-compaction Skill reread recognition contract.

Two layers, both offline and deterministic:

* ``scripts/kaola-compact-recovery.py`` recognizes a real, session-bound,
  completed compaction on every positively sourced ACP wire shape, and builds
  the one role-appropriate reload prompt. It requires a session id and the
  exact ``completed`` status. A start, a failure, a cancel, a summary chunk, a
  token drop, prose, an alias status, a sessionless payload, and a bare payload
  must never match.
* ``scripts/kaola-zcode-acp.py`` projects the ZCode engine's compact state
  (``state.updated`` reasons and ``session/event`` compact types) onto the same
  ACP ``compaction_update`` variant.

No model session, no real CLI, no login, and no network. The ZCode layer
loads the adapter module and calls its pure translation methods with a
captured outbound channel.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HELPER = PROJECT / "scripts" / "kaola-compact-recovery.py"
ZCODE = PROJECT / "scripts" / "kaola-zcode-acp.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def session_update(session_id, **update):
    return {"method": "session/update",
            "params": {"sessionId": session_id, "update": update}}


class ClassifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cr = load_module("kaola_compact_recovery_264", HELPER)

    def test_codex_completed_compaction_update(self) -> None:
        signal = self.cr.classify(session_update(
            "s1", sessionUpdate="compaction_update", status="completed",
            compactionId="c1"))
        self.assertEqual(signal, self.cr.CompactSignal(
            "acp-compaction-update", "s1", "c1"))

    def test_codex_completed_without_occurrence_id_is_still_a_signal(self) -> None:
        signal = self.cr.classify(session_update(
            "s1", sessionUpdate="compaction_update", status="completed"))
        self.assertEqual(signal.occurrence_id, None)
        self.assertEqual(signal.source, "acp-compaction-update")

    def test_opencode_session_info_meta_completed(self) -> None:
        signal = self.cr.classify(session_update(
            "s1", sessionUpdate="session_info_update",
            _meta={"opencode/compaction": {"status": "completed",
                                           "messageId": "m1"}}))
        self.assertEqual(signal, self.cr.CompactSignal(
            "opencode-compaction-meta", "s1", "m1"))

    def test_opencode_child_session_update_is_rejected(self) -> None:
        # `hu` wraps a child update with `opencode/child-session`; it must not
        # wake the parent even when it carries a compaction marker.
        self.assertIsNone(self.cr.classify(session_update(
            "s1", sessionUpdate="session_info_update",
            _meta={"opencode/child-session": {"id": "child"},
                   "opencode/compaction": {"status": "completed",
                                           "messageId": "m1"}})))

    def test_devin_completed_notification(self) -> None:
        signal = self.cr.classify({
            "method": "_cognition.ai/compaction",
            "params": {"sessionId": "luxurious-seed", "status": "completed"}})
        self.assertEqual(signal, self.cr.CompactSignal(
            "devin-compaction", "luxurious-seed", None))

    def test_grok_completed_notification_both_wire_forms(self) -> None:
        for method in ("_x.ai/session_notification", "x.ai/session_notification"):
            signal = self.cr.classify({
                "method": method,
                "params": {"sessionId": "s1",
                           "update": {"sessionUpdate": "auto_compact_completed"}}})
            self.assertEqual(signal, self.cr.CompactSignal(
                "grok-auto-compact-completed", "s1", None))

    def test_kimi_completed_chunk_on_kimi_platform(self) -> None:
        text = ("Compaction completed.\n"
                "- Messages compacted: 1,234\n"
                "- Tokens before: 95,000\n"
                "- Tokens after: 31,000")
        message = session_update(
            "s1", sessionUpdate="agent_message_chunk",
            content={"type": "text", "text": text})
        self.assertEqual(self.cr.classify(message, "kimi-cli"),
                         self.cr.CompactSignal("kimi-compaction-chunk", "s1", None))
        # Offline controller with no platform still recognizes the exact shape.
        self.assertEqual(self.cr.classify(message).source,
                         "kimi-compaction-chunk")

    def test_kimi_completed_chunk_record_shape(self) -> None:
        record = {"kind": "session_update", "sessionId": "s1",
                  "update": {"sessionUpdate": "agent_message_chunk",
                             "content": {"type": "text",
                                         "text": "Compaction completed.\n"
                                                 "- Messages compacted: 10\n"
                                                 "- Tokens before: 9,000\n"
                                                 "- Tokens after: 3,000"}}}
        self.assertEqual(self.cr.classify(record, "kimi-cli").source,
                         "kimi-compaction-chunk")

    def test_kimi_marker_is_rejected_on_another_platform(self) -> None:
        # A model could echo the identical four lines. The platform gate keeps
        # a non-Kimi session from waking on it.
        text = ("Compaction completed.\n- Messages compacted: 10\n"
                "- Tokens before: 9,000\n- Tokens after: 3,000")
        message = session_update(
            "s1", sessionUpdate="agent_message_chunk",
            content={"type": "text", "text": text})
        self.assertIsNone(self.cr.classify(message, "codex"))
        self.assertIsNone(self.cr.classify(message, "opencode"))

    def test_recorded_event_log_shape(self) -> None:
        record = {"kind": "session_update", "sessionId": "s1",
                  "update": {"sessionUpdate": "compaction_update",
                             "status": "completed", "compactionId": "c9"}}
        self.assertEqual(self.cr.classify(record).occurrence_id, "c9")
        note = {"kind": "notification",
                "method": "_cognition.ai/compaction",
                "params": {"sessionId": "s1", "status": "completed"}}
        self.assertEqual(self.cr.classify(note).source, "devin-compaction")

    def test_non_completed_and_prose_never_match(self) -> None:
        negatives = [
            session_update("s1", sessionUpdate="compaction_update",
                           status="in_progress", compactionId="c1"),
            session_update("s1", sessionUpdate="compaction_update",
                           status="failed", compactionId="c1"),
            session_update("s1", sessionUpdate="compaction_update",
                           status="cancelled", compactionId="c1"),
            session_update("s1", sessionUpdate="compaction_summary_chunk",
                           status="completed"),
            session_update("s1", sessionUpdate="session_info_update",
                           _meta={"opencode/compaction": {"status": "started"}}),
            {"method": "_cognition.ai/compaction",
             "params": {"sessionId": "s1", "status": "started"}},
            {"method": "_x.ai/session_notification",
             "params": {"sessionId": "s1",
                        "update": {"sessionUpdate": "auto_compact_started"}}},
            {"method": "session/update",
             "params": {"sessionId": "s1",
                        "update": {"sessionUpdate": "agent_message_chunk",
                                   "content": {"type": "text",
                                               "text": "Context compacted"}}}},
            {"method": "session/update", "params": {}},
            "Context compacted",
            None,
        ]
        for item in negatives:
            with self.subTest(item=item):
                self.assertIsNone(self.cr.classify(item))

    def test_status_aliases_are_rejected(self) -> None:
        # Only the inspected sources' exact `completed` is accepted. Fuzzy
        # aliases would be an unsourced trigger.
        for alias in ("complete", "compacted", "done", "success", "completed "):
            with self.subTest(alias=alias):
                self.assertIsNone(self.cr.classify(session_update(
                    "s1", sessionUpdate="compaction_update", status=alias)))
                self.assertIsNone(self.cr.classify({
                    "method": "_cognition.ai/compaction",
                    "params": {"sessionId": "s1", "status": alias}}))

    def test_session_id_is_required_for_every_source(self) -> None:
        sessionless = [
            {"method": "session/update",
             "params": {"update": {"sessionUpdate": "compaction_update",
                                   "status": "completed", "compactionId": "c1"}}},
            {"method": "session/update",
             "params": {"update": {"sessionUpdate": "session_info_update",
                                   "_meta": {"opencode/compaction": {
                                       "status": "completed", "messageId": "m1"}}}}},
            {"method": "_cognition.ai/compaction",
             "params": {"status": "completed"}},
            {"method": "_x.ai/session_notification",
             "params": {"update": {"sessionUpdate": "auto_compact_completed"}}},
        ]
        for item in sessionless:
            with self.subTest(item=item):
                self.assertIsNone(self.cr.classify(item))

    def test_bare_payload_has_no_proven_scope(self) -> None:
        # A bare update dict with no JSON-RPC wrapper is not an accepted shape.
        self.assertIsNone(self.cr.classify(
            {"sessionUpdate": "compaction_update", "status": "completed"}))
        self.assertIsNone(self.cr.classify(
            {"kind": "unknown", "update": {"sessionUpdate": "compaction_update"}}))

    def test_same_session_scope(self) -> None:
        own = self.cr.CompactSignal("x", "s1", None)
        foreign = self.cr.CompactSignal("x", "child", None)
        self.assertTrue(self.cr.is_same_session(own, "s1"))
        self.assertFalse(self.cr.is_same_session(own, "child"))
        self.assertFalse(self.cr.is_same_session(foreign, "s1"))
        # An unestablished holder session must not accept a signal at all.
        self.assertFalse(self.cr.is_same_session(own, None))

    def test_reload_instruction_names_installed_directory_and_resume(self) -> None:
        text = self.cr.reload_instruction()
        self.assertIn("completely re-read", text.lower())
        self.assertIn("installed", text.lower())
        self.assertIn("not from memory", text.lower())
        self.assertIn("continue", text.lower())

    def test_worker_instruction_names_exact_skill_path(self) -> None:
        text = self.cr.worker_reload_prompt("/skills/codex/SKILL.md")
        self.assertIn("/skills/codex/SKILL.md", text)
        self.assertIn("completely re-read", text.lower())
        # A worker prompt does not open the Host control-plane entry.
        self.assertNotIn("$kaola-project-runner", text)

    def test_host_prompt_leads_with_host_entry(self) -> None:
        prompt = self.cr.host_reload_prompt("/kaola-project-runner")
        self.assertTrue(prompt.startswith("/kaola-project-runner\n"))
        self.assertIn("completely re-read", prompt.lower())

    def test_host_prompt_without_entry_is_still_usable(self) -> None:
        self.assertIn("completely re-read",
                      self.cr.host_reload_prompt("").lower())


class TrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cr = load_module("kaola_compact_recovery_264", HELPER)

    def test_adjacent_duplicate_is_suppressed_but_new_id_is_not(self) -> None:
        tracker = self.cr.CompactReloadTracker()
        self.assertTrue(tracker.observe(self.cr.CompactSignal("a", "s1", "c1")))
        tracker.mark_delivered()
        self.assertFalse(tracker.observe(self.cr.CompactSignal("a", "s1", "c1")))
        self.assertTrue(tracker.observe(self.cr.CompactSignal("a", "s1", "c2")))

    def test_identityless_completion_is_never_suppressed(self) -> None:
        tracker = self.cr.CompactReloadTracker()
        self.assertTrue(tracker.observe(self.cr.CompactSignal("d", "s1", None)))
        tracker.mark_delivered()
        self.assertTrue(tracker.observe(self.cr.CompactSignal("d", "s1", None)))
        self.assertIsNone(tracker.last_delivered_id)

    def test_newer_pending_survives_an_older_admission(self) -> None:
        tracker = self.cr.CompactReloadTracker()
        tracker.observe(self.cr.CompactSignal("a", "s1", "c1"))
        older = tracker.pending_id
        # A newer signal lands while the older one is being admitted.
        tracker.observe(self.cr.CompactSignal("a", "s1", "c2"))
        tracker.mark_delivered_occurrence(older)
        self.assertEqual(tracker.last_delivered_id, "c1")
        self.assertTrue(tracker.pending)
        self.assertEqual(tracker.pending_id, "c2")

    def test_matching_occurrence_clears_pending(self) -> None:
        tracker = self.cr.CompactReloadTracker()
        tracker.observe(self.cr.CompactSignal("a", "s1", "c1"))
        tracker.mark_delivered_occurrence("c1")
        self.assertFalse(tracker.pending)
        self.assertEqual(tracker.last_delivered_id, "c1")

    def test_none_signal_does_nothing(self) -> None:
        tracker = self.cr.CompactReloadTracker()
        self.assertFalse(tracker.observe(None))
        self.assertFalse(tracker.pending)


class ZcodeCompactMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module("kaola_zcode_acp_264", ZCODE)

    def _agent_with_session(self):
        agent = self.module.ZCodeAcpAgent(
            "/bin/true", "/bin/true", "/tmp", "build")
        out: list[dict] = []
        agent.send = lambda msg: out.append(msg)
        session = self.module.Session("acp-1", "/tmp", "build")
        session.backend_id = "backend-1"
        agent.by_backend["backend-1"] = session
        return agent, out

    @staticmethod
    def _updates(out: list[dict]) -> list[dict]:
        result = []
        for message in out:
            if (message.get("method") == "session/update"
                    and message["params"]["update"].get("sessionUpdate")
                    == "compaction_update"):
                result.append(message["params"]["update"])
        return result

    def test_state_updated_completion_maps_to_completed(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"sessionId": "backend-1", "scope": "session",
                       "reason": "session_compacted", "revision": 6,
                       "patch": {}}})
        updates = self._updates(out)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["status"], "completed")
        self.assertEqual(updates[0]["compactionId"], "zcode-state-6")

    def test_state_updated_start_is_not_a_completion(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"sessionId": "backend-1", "scope": "session",
                       "reason": "compact_started", "revision": 5,
                       "patch": {"status": "running"}}})
        updates = self._updates(out)
        self.assertEqual(updates[0]["status"], "in_progress")

    def test_state_updated_requires_session_scope(self) -> None:
        agent, out = self._agent_with_session()
        for scope in (None, "workspace", "global"):
            agent.on_backend_event({
                "method": "state.updated",
                "params": {"sessionId": "backend-1", "scope": scope,
                           "reason": "session_compacted", "revision": 6}})
        self.assertEqual(self._updates(out), [])

    def test_state_updated_requires_a_session_id(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"scope": "session", "reason": "session_compacted",
                       "revision": 6}})
        self.assertEqual(self._updates(out), [])

    def test_session_event_completion_carries_operation_id(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "session/event",
            "params": {"sessionId": "backend-1", "type": "compact_completed",
                       "payload": {"operationId": "cmp_abc", "boundaryId": "bd1",
                                   "status": "completed"}}})
        updates = self._updates(out)
        self.assertEqual(updates[0]["status"], "completed")
        self.assertEqual(updates[0]["compactionId"], "cmp_abc")

    def test_failed_and_cancelled_map_to_their_own_statuses(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "session/event",
            "params": {"sessionId": "backend-1", "type": "compact_failed",
                       "payload": {"operationId": "cmp_def"}}})
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"sessionId": "backend-1", "scope": "session",
                       "reason": "session_compact_cancelled", "revision": 7}})
        statuses = [update["status"] for update in self._updates(out)]
        self.assertEqual(statuses, ["failed", "cancelled"])

    def test_unrelated_state_updated_is_ignored(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"sessionId": "backend-1", "scope": "session",
                       "reason": "model_changed", "revision": 8}})
        self.assertEqual(self._updates(out), [])

    def test_foreign_backend_session_is_ignored(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"sessionId": "someone-else", "scope": "session",
                       "reason": "session_compacted", "revision": 9}})
        self.assertEqual(out, [])

    def test_emitted_update_uses_agent_acp_session_id(self) -> None:
        agent, out = self._agent_with_session()
        agent.on_backend_event({
            "method": "state.updated",
            "params": {"sessionId": "backend-1", "scope": "session",
                       "reason": "session_compacted", "revision": 10}})
        self.assertEqual(out[0]["params"]["sessionId"], "acp-1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
