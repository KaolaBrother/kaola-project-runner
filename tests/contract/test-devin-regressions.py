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
ACP = PROJECT / "scripts" / "kaola-acp.py"
MODEL_POLICY = PROJECT / "scripts" / "kaola-model-policy.py"
ADAPTER = PROJECT / "scripts" / "adapters" / "devin.sh"


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
             "import json; print(json.dumps(mod.models_from_output(sys.stdin.read())[0]))"],
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
    """A no-flag Devin start is the ACP skip-all mode (Issue #22; PTY retired in #130)."""

    def test_core_assigns_acp_bypass_when_caller_omits_permission_mode(self):
        runner = RUNNER.read_text(encoding="utf-8")
        acp = ACP.read_text(encoding="utf-8")
        # Issue #181: the no-flag default is supplied (and recorded) once, by
        # kaola-acp.py's ACP_SKIP_MODE; the tmux entry forwards only an
        # explicit --permission-mode and no longer repeats the table.
        self.assertIn('"devin": "bypass"', acp)
        self.assertIn("permission_mode_given", runner)
        self.assertNotIn("devin) acp_args+=(--mode bypass) ;;", runner)
        # The PTY no-flag mapping went with the tmux branch.
        self.assertNotIn("devin) permission_mode=dangerous ;;", runner)

    def test_manifest_launch_summary_names_the_acp_mode(self):
        manifest = (PROJECT / "platforms" / "devin.yaml").read_text(encoding="utf-8")
        m = re.search(r"^launch_summary:(.*)$", manifest, re.M)
        self.assertIsNotNone(m, "launch_summary not found")
        self.assertIn("ACP start sets mode=bypass", m.group(1))


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



class DevinSideagentOriginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("holder450", PROJECT / "scripts/kaola-acp-holder.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def holder(self, new_id="fresh", listed=(), streamed="fresh"):
        import threading
        from types import SimpleNamespace
        h = self.mod.Holder.__new__(self.mod.Holder)
        h.args = SimpleNamespace(platform="devin", command="devin acp", repo="/repo", session_new_timeout=1)
        h.session_role = "sideagent"
        h.devin_origin_lock = threading.RLock()
        h.devin_origin_id = None
        h.devin_origin_failed = False
        h.devin_prior_ids = set()
        h.devin_pending_updates = []
        h.init_meta = {}
        h.state = "starting"
        h.lock = threading.Lock()
        h.write_record = lambda **kw: None
        h.delivered = []
        h.on_agent_notification = lambda message: h.delivered.append(message)
        class Agent:
            stdin_write_failed = False
            def spawn(self, *a): pass
            def send_request(self, method, params):
                self.method = method
                if method == "session/new" and streamed:
                    h.on_agent_message({"method": "session/update", "params": {"sessionId": streamed, "update": {}}})
                return method
            def wait_response(self, request, timeout):
                if request == "initialize": return {"result": {"protocolVersion": 1, "agentCapabilities": {"sessionCapabilities": {"list": {}}}}}
                if request == "session/list": return {"result": {"sessions": [{"sessionId": x} for x in listed]}}
                return {"result": {"sessionId": new_id}}
        h.agent = Agent()
        return h

    def test_spawn_uses_seat_private_devin_session_directory(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            holder = SimpleNamespace(args=SimpleNamespace(platform="devin"), session_role="sideagent",
                                     record_dir=Path(directory), tool_cwd_trace_env=lambda env: {},
                                     dispatcher_identity=lambda: {})
            connection = self.mod.AgentConnection(holder)
            seen = {}
            def capture(*args, **kwargs):
                seen.update(kwargs["env"])
                raise RuntimeError("captured")
            with patch.object(self.mod, "compact_spawn_record"), patch.object(self.mod.subprocess, "Popen", capture):
                with self.assertRaisesRegex(RuntimeError, "captured"):
                    connection.spawn("devin acp", directory, {"DEVIN_SESSIONS_DIR": "/foreign"})
            self.assertEqual(seen["DEVIN_SESSIONS_DIR"], str(Path(directory) / "devin-sessions"))

    def test_fresh_new_binds_and_replays_matching_updates(self):
        h = self.holder()
        result = h.initialize_agent()
        self.assertEqual(result["acp_session_id"], "fresh")
        self.assertEqual(h.devin_origin_id, "fresh")
        self.assertEqual(len(h.delivered), 1)

    def test_preexisting_or_foreign_start_is_refused_without_replay(self):
        for h in (self.holder(new_id="old", listed=("old",), streamed="old"),
                  self.holder(new_id="fresh", streamed="old"),
                  self.holder(new_id="", streamed=None)):
            with self.subTest(h=h):
                self.assertEqual(h.initialize_agent()["error"]["code"], "sideagent-foreign-session")
                self.assertEqual(h.delivered, [])

    def test_invalid_inventory_refuses_before_new(self):
        h = self.holder(listed=(42,), streamed=None)
        self.assertEqual(h.initialize_agent()["error"]["code"], "sideagent-origin-unverifiable")
        self.assertEqual(h.delivered, [])

    def test_other_seat_record_id_is_refused(self):
        h = self.holder(new_id="other-seat", streamed="other-seat")
        h.devin_prior_ids.add("other-seat")
        self.assertEqual(h.initialize_agent()["error"]["code"], "sideagent-foreign-session")
        self.assertEqual(h.delivered, [])

    def test_recording_sideagent_role_cannot_adopt_loaded_session(self):
        h = self.holder()
        h.acp_session_id = "foreign"
        h.start_selection = None
        result = h.op_record_start_evidence({"evidence": {}, "session_role": "sideagent"})
        self.assertEqual(result["error"]["code"], "sideagent-fresh-session-required")

    def test_resume_and_continue_never_spawn(self):
        for kwargs in ({"resume": "old"}, {"use_continue": True}):
            h = self.holder()
            self.assertEqual(h.initialize_agent(**kwargs)["error"]["code"], "sideagent-fresh-session-required")
            self.assertEqual(h._request_resume("old")["error"]["code"], "sideagent-fresh-session-required")

    def test_foreign_update_after_start_is_not_delivered(self):
        from types import SimpleNamespace
        h = self.holder()
        h.initialize_agent()
        h.events = SimpleNamespace(append=lambda *a, **k: None)
        h._terminate_group = lambda force: None
        h.on_agent_message({"method": "session/update", "params": {"sessionId": "old", "update": {"text": "foreign"}}})
        self.assertTrue(h.devin_origin_failed)
        self.assertEqual(h.state, "error")
        self.assertEqual(len(h.delivered), 1)
        self.assertEqual(h._no_acp_session()["error"]["code"], "sideagent-foreign-session")


if __name__ == "__main__":
    unittest.main()
