#!/usr/bin/env python3
"""Focused fast regressions for Devin CLI platform integration (Issue #13).

These are static source-analysis checks that run in validate.sh's quick suite.
Each test targets a specific bug observed in the original PR commit b341232.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT / "scripts" / "kaola-tmux.sh"
MODEL_POLICY = PROJECT / "scripts" / "kaola-model-policy.py"
ADAPTER = PROJECT / "scripts" / "adapters" / "devin.sh"
RELAY = PROJECT / "scripts" / "kaola-pane-relay.py"


class DevinModelPolicyProbeTests(unittest.TestCase):
    """probes_for must include devin so preflight does not KeyError."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = MODEL_POLICY.read_text(encoding="utf-8")

    def test_probes_for_contains_devin_key(self):
        m = re.search(r"def probes_for\(.*?\n(.*?)\}[\[)]", self.policy, re.S)
        self.assertIsNotNone(m, "probes_for function not found")
        self.assertIn('"devin"', m.group(1))

    def test_real_surface_evidence_handles_devin(self):
        m = re.search(r"def real_surface_evidence\(.*?\n(.*?\n)^def ", self.policy, re.S | re.M)
        self.assertIsNotNone(m, "real_surface_evidence function not found")
        body = m.group(1)
        self.assertIn('"devin"', body,
                       "real_surface_evidence must handle the devin platform")


class DevinAdapterLaunchShapeTests(unittest.TestCase):
    """adapter_build_launch must always pass --model and use valid permission modes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = ADAPTER.read_text(encoding="utf-8")

    def test_model_flag_not_gated_on_adaptive(self):
        # The original bug: skipping --model for adaptive let saved-picker
        # override Runner default; RESOLVED_MODEL_ID='' produced --model ''.
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        self.assertIsNotNone(m, "adapter_build_launch not found")
        body = m.group(0)
        # Must pass --model whenever RESOLVED_MODEL_ID is non-empty — no
        # secondary comparison against a specific default value.
        self.assertNotIn("adaptive", body,
                         "adapter_build_launch must not special-case the adaptive model id")
        self.assertIn('--model "$RESOLVED_MODEL_ID"', body)

    def test_no_empty_model_possible(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        body = m.group(0)
        # The guard must require -n (non-empty) before appending --model.
        self.assertIn('-n "$RESOLVED_MODEL_ID"', body)

    def test_permission_mode_uses_dangerous_not_bypass(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        self.assertIsNotNone(m, "adapter_build_launch not found")
        body = m.group(0)
        self.assertNotIn("bypass", body,
                         "adapter_build_launch must use 'dangerous', not 'bypass'")
        self.assertIn("dangerous", body)


class DevinSessionIdTests(unittest.TestCase):
    """adapter_extract_session_id must not falsely extract the tmux session name."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = ADAPTER.read_text(encoding="utf-8")

    def test_extract_session_id_returns_empty(self):
        m = re.search(r"adapter_extract_session_id\(\).*?^\}", self.adapter, re.S | re.M)
        self.assertIsNotNone(m, "adapter_extract_session_id not found")
        body = m.group(0)
        # Must not contain a sed/grep/regex extraction pattern that could
        # falsely match tmux session names from relay scrollback.
        self.assertNotIn("sed ", body,
                         "adapter_extract_session_id must not regex-extract from TUI output")
        # Should emit empty string.
        self.assertRegex(body, r'printf.*""',
                         "adapter_extract_session_id should return empty")


class DevinPermissionModeGateTests(unittest.TestCase):
    """Runner core must accept --permission-mode for devin alongside claude-code."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_permission_mode_gate_allows_devin(self):
        # The gate is a single long line; grab the full line containing "platform-specific".
        for line in self.runner.splitlines():
            if "platform-specific" in line:
                self.assertIn("devin", line,
                              "permission-mode gate must exempt devin alongside claude-code")
                return
        self.fail("permission-mode gate line not found")

    def test_devin_permission_mode_validation(self):
        m = re.search(r'platform.*==.*devin.*\n\s*case "\$permission_mode" in (.*?)\)', self.runner)
        self.assertIsNotNone(m, "devin permission_mode validation not found")
        modes = m.group(1)
        for expected in ("auto", "accept-edits", "smart", "dangerous"):
            self.assertIn(expected, modes,
                          f"devin permission validation must accept '{expected}'")
        self.assertNotIn("bypass", modes)


class RelaySendSubmitSeparationTests(unittest.TestCase):
    """send_input_direct must yield between bracketed-paste close and CR."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.relay = RELAY.read_text(encoding="utf-8")

    def test_sleep_between_paste_close_and_cr(self):
        m = re.search(
            r"def send_input_direct\(.*?\ndef ",
            self.relay,
            re.S,
        )
        self.assertIsNotNone(m, "send_input_direct not found")
        body = m.group(0)
        # After the bracketed-paste write and before the CR write, there
        # must be a time.sleep call.
        paste_to_cr = re.search(
            r"201~.*?time\.sleep\(.*?\).*?\\r",
            body,
            re.S,
        )
        self.assertIsNotNone(paste_to_cr,
                             "send_input_direct must sleep between paste-close and CR")


if __name__ == "__main__":
    unittest.main()
