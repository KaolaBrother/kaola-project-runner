#!/usr/bin/env python3
"""Focused fast regressions for Devin CLI platform integration (Issue #13).

These are static source-analysis checks that run in validate.sh's quick suite.
Each test targets a specific bug observed in the original PR commit b341232.
"""

from __future__ import annotations

import re
import subprocess
import sys
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


class DevinCatalogParserTests(unittest.TestCase):
    """models_from_output must parse Devin catalog rows including single-token IDs."""

    def _parse(self, text: str) -> dict[str, str]:
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0,'scripts'); "
             "from importlib.util import spec_from_file_location, module_from_spec; "
             f"spec = spec_from_file_location('kmp', {str(MODEL_POLICY)!r}); "
             "mod = module_from_spec(spec); spec.loader.exec_module(mod); "
             "import json; print(json.dumps(mod.models_from_output(sys.stdin.read())))"],
            input=text, capture_output=True, text=True, cwd=str(PROJECT),
        )
        if result.returncode != 0:
            self.fail(f"models_from_output failed: {result.stderr}")
        import json
        return json.loads(result.stdout)

    def test_adaptive_single_token_parsed(self):
        catalog = (
            "Adaptive (adaptive)\n"
            "  adaptive                               Adaptive  "
            "[$0.5 / 1M Input]\n"
        )
        found = self._parse(catalog)
        self.assertIn("adaptive", found, f"adaptive not found in {found}")
        self.assertEqual(found["adaptive"], "Adaptive")

    def test_multi_token_id_parsed(self):
        catalog = (
            "  claude-opus-5-medium                   Claude Opus 5 Medium  "
            "[1M context, $5 / 1M Input]\n"
        )
        found = self._parse(catalog)
        self.assertIn("claude-opus-5-medium", found)

    def test_header_not_parsed_as_model(self):
        catalog = "Claude Opus 5 (claude-opus-5)\n"
        found = self._parse(catalog)
        # Family header should not appear as a model ID
        self.assertNotIn("Claude", found)

    def test_alias_line_not_parsed_as_model(self):
        catalog = "  aliases: opus\n"
        found = self._parse(catalog)
        self.assertNotIn("aliases", found)


class DevinAdapterLaunchShapeTests(unittest.TestCase):
    """adapter_build_launch must always pass --model and pass through permission_mode."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = ADAPTER.read_text(encoding="utf-8")

    def test_model_flag_not_gated_on_adaptive(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        self.assertIsNotNone(m, "adapter_build_launch not found")
        body = m.group(0)
        self.assertNotIn("adaptive", body,
                         "adapter_build_launch must not special-case the adaptive model id")
        self.assertIn('--model "$RESOLVED_MODEL_ID"', body)

    def test_no_empty_model_possible(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        body = m.group(0)
        self.assertIn('-n "$RESOLVED_MODEL_ID"', body)

    def test_permission_mode_passthrough_not_bypass(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        self.assertIsNotNone(m, "adapter_build_launch not found")
        body = m.group(0)
        self.assertNotIn("bypass", body,
                         "adapter_build_launch must not use 'bypass'")
        # Must pass through $permission_mode from the core, not hardcode a value.
        self.assertIn('--permission-mode "$permission_mode"', body)

    def test_no_unreachable_dangerous_fallback(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        body = m.group(0)
        # The core always sets permission_mode (default: auto), so an
        # else-branch fallback to "dangerous" would be unreachable dead code.
        self.assertNotIn("dangerous", body,
                         "adapter_build_launch must not have an unreachable dangerous fallback")


class DevinNoFlagPermissionModeTests(unittest.TestCase):
    """A no-flag Devin start must launch with --permission-mode auto."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_core_default_permission_mode_is_auto(self):
        m = re.search(r"permission_mode=(\S+)", self.runner)
        self.assertIsNotNone(m, "permission_mode default not found in runner")
        self.assertEqual(m.group(1), "auto",
                         "core default permission_mode must be auto")

    def test_manifest_launch_summary_says_auto(self):
        manifest = (PROJECT / "platforms" / "devin.yaml").read_text(encoding="utf-8")
        m = re.search(r"launch_summary:.*?--permission-mode\s+(\S+)", manifest)
        self.assertIsNotNone(m, "launch_summary permission-mode not found")
        self.assertEqual(m.group(1), "auto",
                         "manifest launch_summary must document auto, not dangerous")


class DevinSessionIdTests(unittest.TestCase):
    """adapter_extract_session_id must not falsely extract the tmux session name."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = ADAPTER.read_text(encoding="utf-8")

    def test_extract_session_id_returns_empty(self):
        m = re.search(r"adapter_extract_session_id\(\).*?^\}", self.adapter, re.S | re.M)
        self.assertIsNotNone(m, "adapter_extract_session_id not found")
        body = m.group(0)
        self.assertNotIn("sed ", body,
                         "adapter_extract_session_id must not regex-extract from TUI output")
        self.assertRegex(body, r'printf.*""',
                         "adapter_extract_session_id should return empty")


class DevinPermissionModeGateTests(unittest.TestCase):
    """Runner core must accept --permission-mode for devin alongside claude-code."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_permission_mode_gate_allows_devin(self):
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
        paste_to_cr = re.search(
            r"201~.*?time\.sleep\(.*?\).*?\\r",
            body,
            re.S,
        )
        self.assertIsNotNone(paste_to_cr,
                             "send_input_direct must sleep between paste-close and CR")


if __name__ == "__main__":
    unittest.main()
