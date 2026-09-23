#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "scripts/render-skills.py"
PLATFORMS = {
    "grok": ("acp", "grok agent --always-approve stdio"),
    "kimi-cli": ("acp", "kimi acp"),
    "cursor-cli": ("acp", "cursor-agent --yolo acp"),
    "devin": ("acp", "devin acp"),
    "opencode": ("acp", "opencode acp"),
    "claude-code": ("acp", "node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js"),
    "codex": (
        "acp",
        "npx --yes --package @openai/codex@0.155.1 "
        "--package @agentclientprotocol/codex-acp@1.13.0 codex-acp",
    ),
    "zcode": ("acp", "$SKILL_DIR/scripts/kaola-zcode-acp.py"),
}

spec = importlib.util.spec_from_file_location("renderer", RENDERER)
renderer = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(renderer)


class RunnerV2Contract(unittest.TestCase):
    def test_manifests_and_generated_skills_describe_the_acp_transport(self) -> None:
        # Issue #130: ACP is the only transport; there is no default to declare.
        for platform, (transport, command) in PLATFORMS.items():
            self.assertEqual(transport, "acp")
            manifest = renderer.parse_manifest(ROOT / "platforms" / f"{platform}.yaml")
            self.assertNotIn("default_transport", manifest)
            self.assertIn(command, manifest["acp_command"])
            skill = ROOT / "skills" / manifest["skill_name"]
            text = (skill / "SKILL.md").read_text()
            self.assertIn("ACP is the only transport (Issue #130).", text)
            self.assertNotIn("Default transport:", text)
            self.assertIn(manifest["acp_command"], text)
            self.assertIn("Runner never auto-falls back or resends", text)
            self.assertTrue((skill / "references/acp.md").is_file())
            self.assertFalse((skill / "references/transport.md").exists())
            self.assertTrue((skill / "scripts/kaola-acp.py").is_file())
            self.assertTrue((skill / "scripts/kaola-acp-holder.py").is_file())
            for retired in ("kaola-observation.py", "kaola-pane-relay.py",
                            "kaola-relay-client.py", "kaola-relay-protocol.py"):
                self.assertFalse((skill / "scripts" / retired).exists(), (platform, retired))

    def test_renderer_rejects_a_reintroduced_default_transport(self) -> None:
        source = ROOT / "platforms/grok.yaml"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "grok.yaml"
            target.write_text(source.read_text() + 'default_transport: "pty"\n')
            with self.assertRaisesRegex(ValueError, "default_transport"):
                renderer.parse_manifest(target)

    def test_runtime_dispatches_to_acp_and_has_no_pty_branch(self) -> None:
        runtime = (ROOT / "scripts/kaola-tmux.sh").read_text()
        self.assertIn("--transport", runtime)
        self.assertIn("kaola-acp.py", runtime)
        self.assertIn("mutation_status", runtime)
        self.assertIn("transport-pty-retired", runtime)
        # The tmux branch is gone: no pane/relay machinery, no pty dispatch.
        for marker in ('"$TMUX_BIN"', "capture-pane", "OBSERVATION_HELPER",
                       "kaola-pane-relay.py", "KPR_DEFAULT_TRANSPORT", "default_transport"):
            self.assertNotIn(marker, runtime, marker)
        # the only pty comparison left is the retirement refusal itself
        self.assertEqual(runtime.count("== pty"), 1)
        self.assertNotIn("acp|pty", runtime)
        self.assertFalse((ROOT / "scripts/kaola-observation.py").exists())

    def test_acp_has_no_platform_command_table(self) -> None:
        acp = (ROOT / "scripts/kaola-acp.py").read_text()
        self.assertNotIn("DEFAULT_COMMANDS", acp)
        self.assertIn("acp_command", acp)


if __name__ == "__main__":
    unittest.main()
