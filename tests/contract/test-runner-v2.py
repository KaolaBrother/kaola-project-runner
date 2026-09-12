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
    "claude-code": ("pty", "npx --yes @agentclientprotocol/claude-agent-acp@"),
}

spec = importlib.util.spec_from_file_location("renderer", RENDERER)
renderer = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(renderer)


class RunnerV2Contract(unittest.TestCase):
    def test_manifests_and_generated_skills_describe_both_transports(self) -> None:
        for platform, (default, command) in PLATFORMS.items():
            manifest = renderer.parse_manifest(ROOT / "platforms" / f"{platform}.yaml")
            self.assertEqual(manifest["default_transport"], default)
            self.assertIn(command, manifest["acp_command"])
            skill = ROOT / "skills" / manifest["skill_name"]
            text = (skill / "SKILL.md").read_text()
            self.assertIn(f"Default transport: **{default}**", text)
            self.assertIn(manifest["acp_command"], text)
            self.assertIn("Cost hints", text)
            self.assertIn("Runner never auto-falls back or resends", text)
            self.assertTrue((skill / "references/acp.md").is_file())
            self.assertTrue((skill / "scripts/kaola-acp.py").is_file())
            self.assertTrue((skill / "scripts/kaola-acp-holder.py").is_file())

    def test_renderer_rejects_invalid_default_transport(self) -> None:
        source = ROOT / "platforms/grok.yaml"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "grok.yaml"
            target.write_text(source.read_text().replace('default_transport: "acp"', 'default_transport: "invalid"'))
            with self.assertRaisesRegex(ValueError, "default_transport"):
                renderer.parse_manifest(target)

    def test_runtime_has_manifest_dispatch_and_v3_pty_receipts(self) -> None:
        runtime = (ROOT / "scripts/kaola-tmux.sh").read_text()
        self.assertIn("--transport", runtime)
        self.assertIn("kaola-acp.py", runtime)
        self.assertIn("mutation_status", runtime)
        observation = (ROOT / "scripts/kaola-observation.py").read_text()
        self.assertIn('"schema_version": 3', observation)
        self.assertIn('"transport":', observation)

    def test_acp_has_no_platform_command_table(self) -> None:
        acp = (ROOT / "scripts/kaola-acp.py").read_text()
        self.assertNotIn("DEFAULT_COMMANDS", acp)
        self.assertIn("acp_command", acp)


if __name__ == "__main__":
    unittest.main()
