#!/usr/bin/env python3
"""Affected project-hook -> real holder admission checks, with no model."""
import importlib.util
import json
from pathlib import Path
import socket
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


race = load("notice_race", ROOT / "tests/contract/test-issue-65-steer-race.py")
hook = load("project_notice", ROOT / "scripts/kaola-project-compact-notice.py")


class Notice(unittest.TestCase):
    def setUp(self):
        race.SteerRaceContract.setUp(self)
        self.holder.args.platform = "droid"
        self.holder._await_prompt = lambda request: None
        self.root = Path(self.holder.args.repo).resolve()
        self.agent.unknown_updates = {}
        self.skills = [self.root / "platform-SKILL.md", self.root / "task-SKILL.md"]
        for path in self.skills:
            path.write_text("Full current fixture Skill\n")
        self.start_turn("original scratch task")
        self.params = {
            "expected_holder_instance_id": self.holder.holder_instance_id,
            "expected_acp_session_id": self.holder.acp_session_id,
            "expected_prior_turn_request_id": self.holder.turn["request_id"],
            "hook_event_name": "PreCompact", "hook_session_id": self.holder.acp_session_id,
            "project_root": str(self.root), "hook_cwd": str(self.root),
            "platform_skill_path": str(self.skills[0]),
            "task_skill_paths": [str(self.skills[1])]}

    tearDown = race.SteerRaceContract.tearDown
    start_turn = race.SteerRaceContract.start_turn
    settle = race.SteerRaceContract.settle

    def notice(self, **overrides):
        return self.holder.handle_request({"op": "compact_notice", "params": {
            **self.params, **overrides}})

    def test_notice_waits_for_real_successful_response_then_standard_prompt(self):
        prior = self.holder.turn
        result = self.notice()
        self.assertTrue(result["notice_pending"])
        self.assertEqual(result["completion"], "unconfirmed")
        self.assertIs(self.holder.turn, prior)
        self.assertEqual(len(self.agent.prompts_sent()), 1)
        self.settle(self.params["expected_prior_turn_request_id"])
        self.assertEqual(len(self.agent.prompts_sent()), 2)
        message = self.agent.prompts_sent()[-1]
        self.assertEqual(message["params"]["sessionId"], self.holder.acp_session_id)
        text = message["params"]["prompt"][0]["text"]
        self.assertIn("completion is unconfirmed", text)
        self.assertNotIn("context was compacted", text)
        self.assertIn("file read tool", text)
        for path in self.skills:
            self.assertIn(str(path), text)
        self.assertFalse(self.holder.compact_reload.pending)
        self.assertIsNone(self.holder.compact_notice_pending)
        self.assertFalse(self.agent.cancels_sent())
        events = self.holder.events.read_since(0, None)
        kinds = [e["kind"] for e in events]
        self.assertLess(kinds.index("turn_ended"), kinds.index("compact_project_notice_admitted"))
        admission = next(e for e in events if e["kind"] == "compact_project_notice_admitted")
        self.assertEqual(admission["read_use"], "unverified")

    def test_duplicate_notice_coalesces_current_pending(self):
        self.notice()
        seq = self.holder.compact_reload.pending_seq
        self.assertEqual(self.notice()["reason"], "coalesced")
        self.assertEqual(self.holder.compact_reload.pending_seq, seq)

    def test_staging_event_precedes_admission_when_prior_ends_at_append(self):
        append = self.holder.events.append
        ended, finished = threading.Event(), threading.Event()
        threads = []

        def end_prior():
            try:
                self.settle(self.params["expected_prior_turn_request_id"])
            finally:
                finished.set()

        def interleave(event, **kwargs):
            if event["kind"] == "turn_ended":
                ended.set()
            if event["kind"] == "compact_project_notice":
                thread = threading.Thread(target=end_prior)
                threads.append(thread)
                thread.start()
                self.assertTrue(ended.wait(3))
                # At the old unlocked boundary the response can finish before
                # the append. Under the fixed staging lock it must wait.
                if not self.holder.worker_events_lock.locked():
                    self.assertTrue(finished.wait(3))
            return append(event, **kwargs)

        self.holder.events.append = interleave
        self.notice()
        for thread in threads:
            thread.join(3)
            self.assertFalse(thread.is_alive())
        kinds = [event["kind"] for event in self.holder.events.read_since(0, None)]
        self.assertLess(kinds.index("compact_project_notice"),
                        kinds.index("compact_project_notice_admitted"), kinds)

    def test_missing_host_entry_retains_notice_and_reload(self):
        self.holder.session_role = "host"
        self.holder.host_entry = ""
        self.notice()
        self.settle(self.params["expected_prior_turn_request_id"])
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertIsNotNone(self.holder.compact_notice_pending)
        self.assertEqual(self.holder._deliver_compact_reload()["reason"],
                         "notice-host-entry-absent")
        self.holder.compact_notice_pending = None
        self.assertEqual(self.holder._deliver_compact_reload()["reason"],
                         "host-entry-absent")
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertEqual(len(self.agent.prompts_sent()), 1)

    def test_source_checkout_does_not_name_directory_as_installed_skill(self):
        self.assertIsNone(self.holder.installed_skill_path)
        self.settle(self.params["expected_prior_turn_request_id"])
        module = race.holder_module.compact_module()
        self.holder.compact_reload = module.CompactReloadTracker()
        self.holder.compact_reload.observe(module.CompactSignal(
            "acp-compaction-update", self.holder.acp_session_id, "fixture"))
        self.assertTrue(self.holder._deliver_compact_reload()["delivered"])
        text = self.agent.prompts_sent()[-1]["params"]["prompt"][0]["text"]
        self.assertIn("droid-kaola-project-runner", text)
        self.assertNotIn(str(ROOT) + " and", text)
        event = next(e for e in self.holder.events.read_since(0, None)
                     if e["kind"] == "compact_reload_delivered")
        self.assertIsNone(event["skill_path"])

    def test_foreign_missing_or_stop_hook_never_writes_or_stages(self):
        for bad in ({"hook_session_id": "foreign"}, {"hook_cwd": "/other"},
                    {"expected_holder_instance_id": "foreign"},
                    {"expected_acp_session_id": None}, {"task_skill_paths": []},
                    {"platform_skill_path": "relative"}, {"hook_event_name": "Stop"},
                    {"expected_prior_turn_request_id": -1}):
            with self.subTest(bad=bad):
                self.assertFalse(self.notice(**bad)["notice_pending"])
                self.assertIsNone(self.holder.compact_reload)
        self.assertEqual(len(self.agent.prompts_sent()), 1)

    def test_failed_refused_cancelled_or_stopping_original_retains_obligation(self):
        self.notice()
        prior = self.params["expected_prior_turn_request_id"]
        self.settle(prior, "refusal")
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertEqual(len(self.agent.prompts_sent()), 1)
        for reason in ("cancelled", "max_tokens", "end_turn"):
            self.holder.turn["stop_reason"] = reason
            self.holder.turn["outcome"] = "turn_failed"
            self.holder._deliver_compact_reload()
        self.holder.turn.update(outcome="turn_completed", stop_reason="end_turn")
        self.holder.stop_requested = True
        self.holder._deliver_compact_reload()
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertEqual(len(self.agent.prompts_sent()), 1)

    def test_active_false_alone_is_not_success(self):
        self.notice()
        self.holder.turn["active"] = False
        self.holder._deliver_compact_reload()
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertEqual(len(self.agent.prompts_sent()), 1)

    def test_intervening_turn_can_start_and_end_before_admission_no_write(self):
        self.notice()
        original = self.holder.op_prompt
        def interleave(params):
            self.holder.turn = {**self.holder.turn, "request_id": 999,
                                "active": False, "outcome": "turn_completed",
                                "stop_reason": "end_turn"}
            return original(params)
        self.holder.op_prompt = interleave
        self.settle(self.params["expected_prior_turn_request_id"])
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertFalse(self.holder.compact_notice_pending["write_unknown"])
        self.assertEqual(len(self.agent.prompts_sent()), 1)

    def test_success_change_at_actual_admission_lock_prevents_write(self):
        self.notice()
        original = self.holder.op_prompt
        def interleave(params):
            self.holder.turn["outcome"] = "turn_failed"
            return original(params)
        self.holder.op_prompt = interleave
        self.settle(self.params["expected_prior_turn_request_id"])
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertEqual(len(self.agent.prompts_sent()), 1)

    def test_unknown_write_is_retained_and_never_replayed(self):
        self.notice()
        calls = []
        def unknown(params):
            calls.append(params)
            raise OSError("after possible write")
        self.holder.op_prompt = unknown
        self.settle(self.params["expected_prior_turn_request_id"])
        self.holder._deliver_compact_reload()
        self.holder._deliver_compact_reload()
        self.assertEqual(len(calls), 1)
        self.assertTrue(self.holder.compact_notice_pending["write_unknown"])
        self.assertTrue(self.holder.compact_reload.pending)

    def test_partial_write_failure_is_unknown_and_not_replayed(self):
        self.notice()
        calls = []
        self.holder.op_prompt = lambda params: calls.append(params) or {
            "outcome": "turn_failed", "mutation_performed": False,
            "error": {"code": "acp-write-failed"}}
        self.settle(self.params["expected_prior_turn_request_id"])
        self.holder._deliver_compact_reload()
        self.assertEqual(len(calls), 1)
        self.assertTrue(self.holder.compact_notice_pending["write_unknown"])

    def test_native_codex_remains_exempt(self):
        for platform in ("codex",):
            self.holder.args.platform = platform
            self.assertFalse(self.notice()["notice_pending"])
        self.assertIsNone(self.holder.compact_reload)

    def test_cursor_exact_acp_id_and_data_project_root_admit_notice(self):
        self.holder.args.platform = "cursor-cli"
        data_root = self.root / "cursor-data"
        import re
        key = re.sub(r"[^a-zA-Z0-9]+", "-", str(self.root)).strip("-")
        roots = [str(data_root / "projects" / key)]
        with patch.dict("os.environ", {"CURSOR_DATA_DIR": str(data_root)}):
            wrong = self.notice(hook_event_name="preCompact", hook_workspace_roots=[str(self.root)])
            self.assertFalse(wrong["notice_pending"])
            right = self.notice(hook_event_name="preCompact", hook_workspace_roots=roots)
            self.assertTrue(right["notice_pending"])
            self.settle(self.params["expected_prior_turn_request_id"])
        self.assertEqual(len(self.agent.prompts_sent()), 2)
        self.assertFalse(self.agent.cancels_sent())

    def test_cursor_hook_requires_both_session_fields_to_match(self):
        binding = {"platform": "cursor-cli", "socket_path": str(self.root / "h.sock"),
                   "holder_instance_id": self.holder.holder_instance_id,
                   "acp_session_id": "ses-race", "project_root": str(self.root),
                   "hook_project_root": str(self.root / "data-project"),
                   "platform_skill_path": str(self.skills[0]), "task_skill_paths": [str(self.skills[1])]}
        payload = {"hook_event_name": "preCompact", "conversation_id": "ses-race",
                   "session_id": "foreign", "workspace_roots": [binding["hook_project_root"]]}
        with patch.object(hook, "request") as req:
            self.assertEqual(hook.forward(binding, payload)["notice_write"], "not_attempted")
            req.assert_not_called()

    def test_newer_native_occurrence_less_signal_survives_notice_admission(self):
        self.notice()
        original = self.holder.op_prompt
        module = race.holder_module.compact_module()
        def newer(params):
            self.holder.compact_reload.observe(module.CompactSignal("native", "ses-race", None))
            return original(params)
        self.holder.op_prompt = newer
        self.settle(self.params["expected_prior_turn_request_id"])
        self.assertTrue(self.holder.compact_reload.pending)
        self.assertIsNone(self.holder.compact_notice_pending)

    def test_hook_uses_existing_socket_and_filters_auth_fields(self):
        binding = {"platform": "droid", "socket_path": str(self.root / "hook.sock"),
                   "holder_instance_id": self.holder.holder_instance_id,
                   "acp_session_id": self.holder.acp_session_id, "project_root": str(self.root),
                   "platform_skill_path": str(self.skills[0]),
                   "task_skill_paths": [str(self.skills[1])]}
        payload = {"hook_event_name": "PreCompact", "session_id": "ses-race",
                   "cwd": str(self.root), "headers": {"authorization": "FIXTURE-REDACT"}}
        received = []
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(binding["socket_path"])
            listener.listen(2)
            def serve():
                for _ in range(2):
                    connection, _ = listener.accept()
                    with connection, connection.makefile("rb") as stream:
                        request = json.loads(stream.readline())
                        received.append(request)
                        result = self.holder.handle_request(request)
                        connection.sendall(json.dumps(result).encode() + b"\n")
            thread = threading.Thread(target=serve)
            thread.start()
            result = hook.forward(binding, payload)
            thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertTrue(result["notice_pending"])
        self.assertEqual([r["op"] for r in received], ["state", "compact_notice"])
        self.assertNotIn("authorization", json.dumps(received))
        self.assertNotIn("FIXTURE-REDACT", json.dumps(result))

    def test_real_socket_before_write_failure_is_not_attempted(self):
        result = hook.request(str(self.root / "missing.sock"), "compact_notice", {})
        self.assertEqual(result["notice_write"], "not_attempted")

    def test_real_socket_after_write_reply_loss_is_unknown(self):
        path = str(self.root / "lost.sock")
        received = []
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(path)
            listener.listen(1)
            def lose_reply():
                connection, _ = listener.accept()
                with connection, connection.makefile("rb") as stream:
                    received.append(json.loads(stream.readline()))
            thread = threading.Thread(target=lose_reply)
            thread.start()
            result = hook.request(path, "compact_notice", {"fixture": "selected-fields-only"})
            thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(result["notice_write"], "unknown")
        self.assertEqual(len(received), 1)

    def test_hook_socket_reply_loss_is_unknown_not_retry(self):
        binding = {"platform": "droid", "socket_path": str(self.root / "h.sock"),
                   "holder_instance_id": self.holder.holder_instance_id,
                   "acp_session_id": self.holder.acp_session_id, "project_root": str(self.root),
                   "platform_skill_path": str(self.skills[0]),
                   "task_skill_paths": [str(self.skills[1])]}
        state = {"holder_instance_id": binding["holder_instance_id"], "acp_session_id": "ses-race",
                 "turn_active": True, "turn_request_id": 1}
        with patch.object(hook, "request", side_effect=[state, {"notice_write": "unknown"}]) as req:
            result = hook.forward(binding, {"hook_event_name": "PreCompact",
                                          "session_id": "ses-race", "cwd": str(self.root)})
        self.assertEqual(result["notice_write"], "unknown")
        self.assertEqual(req.call_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
