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


class DevinFooterEvidenceTests(unittest.TestCase):
    """real_surface_evidence must extract the model display name from the Devin footer."""

    def _evidence(self, frame: str):
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; "
             "from importlib.util import spec_from_file_location, module_from_spec; "
             f"spec = spec_from_file_location('kmp', {str(MODEL_POLICY)!r}); "
             "mod = module_from_spec(spec); spec.loader.exec_module(mod); "
             "import json; "
             "mid, params, src = mod.real_surface_evidence('devin', sys.stdin.read()); "
             "print(json.dumps({'model_id': mid, 'parameters': params, 'source': src}))"],
            input=frame, capture_output=True, text=True, cwd=str(PROJECT),
        )
        if result.returncode != 0:
            self.fail(f"real_surface_evidence failed: {result.stderr}")
        import json
        return json.loads(result.stdout)

    def test_adaptive_footer_after_message(self):
        # Real Devin TUI after a message: model name on last line with context.
        frame = (
            "❭ What is 2+2?\n"
            "\n"
            " 4\n"
            "\n"
            "────────────────────────────────────────\n"
            "❭ Ask Devin to build features, fix bugs, or work on your code\n"
            "────────────────────────────────────────\n"
            "Adaptive                                                     Context: 14k tokens\n"
        )
        ev = self._evidence(frame)
        self.assertEqual(ev["model_id"], "Adaptive")
        self.assertEqual(ev["source"], "devin-footer")

    def test_adaptive_footer_idle(self):
        # Real Devin TUI before any message: model name with hint text.
        frame = (
            "────────────────────────────────────────\n"
            "❭ Ask Devin to build features, fix bugs, or work on your code\n"
            "────────────────────────────────────────\n"
            "Adaptive                         Type @ to mention files and add them as context\n"
        )
        ev = self._evidence(frame)
        self.assertEqual(ev["model_id"], "Adaptive")
        self.assertEqual(ev["source"], "devin-footer")

    def test_adaptive_footer_ctrl_hint(self):
        # Real Devin TUI idle variant: "Press Ctrl+L to clear the screen..."
        frame = (
            "────────────────────────────────────────\n"
            "❭ Ask Devin to build features, fix bugs, or work on your code\n"
            "────────────────────────────────────────\n"
            "Adaptive                Press Ctrl+L to clear the screen, Ctrl+Shift+L to redraw\n"
        )
        ev = self._evidence(frame)
        self.assertEqual(ev["model_id"], "Adaptive")
        self.assertEqual(ev["source"], "devin-footer")

    def test_adaptive_footer_alt_enter_hint(self):
        # Real Devin TUI idle variant: "Alt+Enter for multiline prompts"
        frame = (
            "────────────────────────────────────────\n"
            "❭ Ask Devin to build features, fix bugs, or work on your code\n"
            "────────────────────────────────────────\n"
            "Adaptive                                                                          Alt+Enter for multiline prompts\n"
        )
        ev = self._evidence(frame)
        self.assertEqual(ev["model_id"], "Adaptive")
        self.assertEqual(ev["source"], "devin-footer")

    def test_non_default_model_footer(self):
        # If the user switches to a different model, the footer reflects it.
        frame = (
            "────────────────────────────────────────\n"
            "❭ Ask Devin\n"
            "────────────────────────────────────────\n"
            "Claude Opus 5 Medium                                         Context: 5k tokens\n"
        )
        ev = self._evidence(frame)
        self.assertEqual(ev["model_id"], "Claude Opus 5 Medium")
        self.assertEqual(ev["source"], "devin-footer")

    def test_launch_preamble_not_trusted(self):
        # The shell launch preamble contains --model but must not be treated
        # as runtime-owned evidence.  Only the TUI footer is trusted.
        frame = (
            "exec python3 kaola-pane-relay.py -- --model adaptive --permission-mode auto\n"
        )
        ev = self._evidence(frame)
        self.assertIsNone(ev["model_id"],
                          "launch preamble must not be trusted as model evidence")

    def test_max_usage_line_not_model(self):
        # "Max · 97% remaining (resets in 2d 16h)" is capitalized usage text,
        # not a model name.  It must not be extracted.
        frame = (
            "Max \u00b7 97% remaining (resets in 2d 16h)\n"
            "\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            "\u276d Ask Devin\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        )
        ev = self._evidence(frame)
        self.assertIsNone(ev["model_id"],
                          "Max usage line must not be classified as a model")

    def test_done_output_not_model(self):
        # Ordinary capitalized output like "Done" must not match.
        frame = (
            "Done\n"
            "\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            "\u276d Ask Devin\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        )
        ev = self._evidence(frame)
        self.assertIsNone(ev["model_id"],
                          "ordinary capitalized output must not be classified as a model")

    def test_truncated_frame_without_footer(self):
        # If the footer is scrolled away, evidence must be None.
        frame = (
            "Some long conversation output...\n"
            "More output lines here\n"
        )
        ev = self._evidence(frame)
        self.assertIsNone(ev["model_id"],
                          "truncated frame without footer must yield no evidence")


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

    def test_help_list_command_not_parsed_as_model(self):
        # Real Devin --help output: "list" is a CLI command, not a model.
        # The bracket content "[aliases: ls]" must not trigger the catalog
        # row parser because it lacks pricing/context indicators.
        helpline = "  list       List sessions in the current directory [aliases: ls]\n"
        found = self._parse(helpline)
        self.assertNotIn("list", found, f"'list' falsely parsed as model: {found}")

    def test_free_tier_model_parsed(self):
        catalog = "  swe-2-max                              SWE-2 Max  [262K context, Free]\n"
        found = self._parse(catalog)
        self.assertIn("swe-2-max", found)


class DevinActivityHintTests(unittest.TestCase):
    """adapter_activity_hint must not false-positive on footer hints."""

    def _hint(self, capture: str) -> str:
        result = subprocess.run(
            ["bash", "-c",
             f"source {ADAPTER} && adapter_activity_hint \"$1\"",
             "_", capture],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.fail(f"adapter_activity_hint failed: {result.stderr}")
        return result.stdout.strip()

    def test_idle_footer_thinking_trace_not_busy(self):
        # Real idle footer: "Press Ctrl+O to view the full thinking trace"
        # must NOT trigger the busy regex via the bare word "thinking".
        frame = (
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            "\u276d Ask Devin to build features, fix bugs, or work on your code\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            "Adaptive                Press Ctrl+O to view the full thinking trace\n"
        )
        hint = self._hint(frame)
        self.assertNotEqual(hint, "busy",
                            "idle footer with 'thinking trace' must not be classified busy")

    def test_completed_prompt_with_devin_glyph_is_idle(self):
        # After a completed reply, the real Devin prompt glyph is \u276d.
        frame = (
            " 42\n"
            "\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            "\u276d Ask Devin to build features, fix bugs, or work on your code\n"
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            "Adaptive                                                     Context: 14k tokens\n"
        )
        hint = self._hint(frame)
        self.assertEqual(hint, "idle",
                         "completed prompt with \u276d glyph must be idle")

    def test_thinking_with_timer_is_busy(self):
        # Real busy status: "Thinking \u00b7" (middle-dot timer).
        frame = (
            "\u276d What is 2+2?\n"
            "\n"
            "Thinking \u00b7\n"
        )
        hint = self._hint(frame)
        self.assertEqual(hint, "busy",
                         "Thinking with middle-dot timer must be busy")

    def test_thinking_standalone_is_busy(self):
        # "Thinking" alone on a line is genuine busy status.
        frame = (
            "\u276d What is 2+2?\n"
            "\n"
            "Thinking\n"
        )
        hint = self._hint(frame)
        self.assertEqual(hint, "busy",
                         "standalone Thinking must be busy")


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
        # Issue #13 aliases (bypass / autonomous) stay rejected; skip-all is "dangerous".
        self.assertNotIn("bypass", body,
                         "adapter_build_launch must not use Issue #13 alias 'bypass'")
        self.assertIn('--permission-mode "$permission_mode"', body)

    def test_dangerous_is_the_skip_all_value_not_dead_code(self):
        m = re.search(r"adapter_build_launch\(\).*?^\}", self.adapter, re.S | re.M)
        body = m.group(0)
        # Issue #22: default Devin start uses dangerous. The adapter may pass
        # $permission_mode (core default) or mention dangerous; neither is a
        # regression. An unreachable else-branch is not required.
        self.assertIn('--permission-mode "$permission_mode"', body)


class DevinNoFlagPermissionModeTests(unittest.TestCase):
    """A no-flag Devin start must launch with --permission-mode dangerous (Issue #22)."""

    def test_core_assigns_dangerous_when_caller_omits_permission_mode(self):
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn(
            "devin) permission_mode=dangerous ;;",
            runner,
            "no-flag Devin PTY start must assign permission_mode=dangerous",
        )

    def test_manifest_launch_summary_says_dangerous(self):
        manifest = (PROJECT / "platforms" / "devin.yaml").read_text(encoding="utf-8")
        m = re.search(r"launch_summary:.*?--permission-mode\s+(\S+)", manifest)
        self.assertIsNotNone(m, "launch_summary permission-mode not found")
        self.assertEqual(m.group(1), "dangerous",
                         "manifest launch_summary must document dangerous, not auto")


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
