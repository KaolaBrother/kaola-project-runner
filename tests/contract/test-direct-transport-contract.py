#!/usr/bin/env python3
"""Regression contract for direct, non-blocking Runner communication."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT / "scripts" / "kaola-tmux.sh"
RELAY = PROJECT / "scripts" / "kaola-pane-relay.py"
SKILL_TEMPLATE = PROJECT / "templates" / "SKILL.md.tmpl"


def shell_function(source: str, name: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(name)}\(\) \{{.*?^\}}$", source)
    if match is None:
        raise AssertionError(f"missing shell function: {name}")
    return match.group(0)


def action(source: str, name: str, following: str | None) -> str:
    start = f"  {name})\n"
    body = source.split(start, 1)[1]
    if following is not None:
        body = body.split(f"  {following})\n", 1)[0]
    return body


class DirectTransportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = RUNNER.read_text(encoding="utf-8")
        cls.relay = RELAY.read_text(encoding="utf-8")

    def test_observe_reads_live_state_without_quiescing_the_cli(self) -> None:
        observe = shell_function(self.runner, "observe_managed")
        self.assertIn('"operation":"state"', observe)
        self.assertNotIn('"operation":"quiesce"', observe)
        self.assertNotIn('"operation":"resume"', observe)
        self.assertNotIn("lease", observe)

    def test_agent_actions_use_one_direct_relay_transfer(self) -> None:
        channel = shell_function(self.runner, "open_transport_channel")
        self.assertIn("direct_input", channel)
        self.assertIn("relay-upgrade-required", channel)
        answer = action(self.runner, "answer", "send")
        send = action(self.runner, "send", "key")
        key = action(self.runner, "key", "stop")
        stop = action(self.runner, "stop", None)

        for name, body in (("answer", answer), ("send", send), ("stop", stop)):
            with self.subTest(action=name):
                self.assertRegex(body, r'operation\\?"?:\\?"send-input')
                for forbidden in (
                    "prepare_transaction",
                    "prepare-input",
                    '"operation":"submit"',
                    "renew_transaction",
                    "restore_transaction",
                    "action-prepare-uncertain",
                ):
                    self.assertNotIn(forbidden, body)

        self.assertRegex(key, r'operation\\?"?:\\?"send-control')
        self.assertNotIn("prepare_transaction", key)

    def test_direct_relay_input_never_stops_or_fences_the_child(self) -> None:
        match = re.search(
            r"(?ms)^def send_input_direct\(.*?^def ", self.relay
        )
        self.assertIsNotNone(match, "missing direct relay input implementation")
        direct = match.group(0) if match is not None else ""
        self.assertIn("_write_child", direct)
        self.assertNotIn("stop_child_tree", direct)
        self.assertNotIn("run_decrqm_fence", direct)
        self.assertNotIn("set_pane_input", direct)

    def test_action_receipts_are_compact_transport_facts(self) -> None:
        actions = self.runner.rsplit('case "$command_name" in', 1)[1]
        for noisy_internal in (
            "restoration_evidence",
            "prepared_pane_revision",
            "prepared_clear_editor",
            "action_time_snapshot",
        ):
            self.assertNotIn(noisy_internal, actions)
        self.assertIn("payload_fingerprint", actions)

    def test_skill_keeps_protocol_detail_out_of_user_progress_updates(self) -> None:
        template = SKILL_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("Do not narrate raw relay", template)


if __name__ == "__main__":
    unittest.main()
