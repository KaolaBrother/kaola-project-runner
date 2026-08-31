#!/usr/bin/env python3
"""Independent static contract oracles for Issue #9 subtractive behavior."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT / "scripts" / "kaola-tmux.sh"
CURSOR_ADAPTER = PROJECT / "scripts" / "adapters" / "cursor-cli.sh"
TEMPLATES = PROJECT / "templates"
GOLDEN = TEMPLATES / "grok-golden"
RENDERER = PROJECT / "scripts" / "render-skills.py"

PLATFORMS = (
    "grok-kaola-project-runner",
    "claude-code-kaola-project-runner",
    "opencode-kaola-project-runner",
    "kimi-cli-kaola-project-runner",
    "cursor-cli-kaola-project-runner",
)

GOLDEN_SHA256 = {
    "SKILL.md": "ae74d354ef1059a60edbde8cb4a99dad09d2d25cc47e0fc637e2c9164cc70dbe",
    "agents/openai.yaml": "66699c5188eb10c53ab166572d530bbe77132c64d5b666c7258f68188bc64ddd",
    "references/closing.md": "2fda2a5726fa39abbbeb87ce7e80815e2d2870f001d7198e949e26f46a2b60c1",
    "references/codex-supervision.md": "b9c3ec5d4aa7081faccf7773d84b08b10bad828cc8e15f4221de9435be7cb2d4",
    "references/grok-tui.md": "818f9c7496d7d9a132112ceeb4d29c03d10d0c7a7765945026353d8e4033a6f8",
    "references/human-decisions.md": "f7abfdda3d3590fcefd10316cf3bc51a6ffcf79834ae7b23cf7c25f1ba621a2c",
    "references/kaola-lifecycle.md": "2c545d92737fee3bf3b3f1d147ac1e425999f698d0aa3e69a4afe210106dd9ea",
    "references/pr-claim-handoff.md": "d7b452943c5775aa2fc79db402ded3aab9a0cc332230b59f910ce334415c2377",
    "references/project-run.md": "742ec446152abd484fb4c7368da27183878d0f2075c63cec10a1327a8923187f",
    "references/scheduling.md": "6ea889913d7e8109767b61695b9d0030e393941861023a2a9955f093e2558e9e",
    "references/status-monitoring.md": "a113eee36c698c8c85d7e2e9a303837a8cc8dfd9c27a6e7e944789758776db20",
    "references/task-modes.md": "c9e8333d82a44edbdf8eb1d2bbb2f3f4f317b9ed34a02aea69fa2240aff3ca23",
}


class Issue9ContractTests(unittest.TestCase):
    def test_issue9_cursor_materialization_gate_is_absent(self) -> None:
        source = CURSOR_ADAPTER.read_text(encoding="utf-8")
        self.assertNotIn("adapter_prepare_launch", source)
        self.assertNotIn("--ensure-target", source)
        self.assertNotIn("CURSOR_SURFACE_HELPER", source)
        generated = (
            PROJECT
            / "skills"
            / "cursor-cli-kaola-project-runner"
            / "scripts"
            / "adapters"
            / "cursor-cli.sh"
        ).read_text(encoding="utf-8")
        self.assertNotIn("adapter_prepare_launch", generated)
        self.assertNotIn("--ensure-target", generated)
        self.assertNotIn("CURSOR_SURFACE_HELPER", generated)

    def test_issue9_send_and_graceful_stop_have_no_editor_authority_gate(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        actions = source.rsplit('case "$command_name" in', 1)[1]
        # UI/editor facts remain observable in build_sample; they must not be
        # consulted by send, answer, or graceful stop after relay preparation.
        answer = actions.split("  answer)\n", 1)[1].split("  send)\n", 1)[0]
        send = actions.split("  send)\n", 1)[1].split("  key)\n", 1)[0]
        stop = actions.split("  stop)\n", 1)[1]
        with self.subTest(action="answer"):
            self.assertNotIn("prepared_answer_surface_result", answer)
        with self.subTest(action="send"):
            self.assertNotIn("prepared_surface_result", send)
            self.assertNotIn("prepared_guard", send)
        with self.subTest(action="stop"):
            self.assertNotIn("prepared_surface_result", stop)
            self.assertNotIn("prepared_guard", stop)
        self.assertRegex(actions, r'operation.{0,12}send-input')
        self.assertNotRegex(actions, r'operation.{0,12}prepare-input')
        self.assertNotRegex(actions, r'operation.{0,12}submit')
        self.assertIn("payload_fingerprint", actions)

    def test_issue9_force_branch_precedes_relay_transaction(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        stop = source.split("  stop)\n", 1)[1]
        force_index = stop.find('if [[ "$force" == true ]]')
        prepare_index = stop.find("prepare_transaction")
        self.assertGreaterEqual(force_index, 0)
        self.assertTrue(
            prepare_index < 0 or force_index < prepare_index,
            "force recovery must not call relay-dependent prepare_transaction first",
        )

    def test_issue9_catalog_missing_start_does_not_preempt_cli(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        start = source.split("  start)\n", 1)[1].split("  answer)\n", 1)[0]
        self.assertNotIn("emit_model_unavailable", start)
        self.assertNotIn("model-unavailable", start)
        self.assertIn("ADAPTER_LAUNCH_ARGS", start)

    def test_issue9_transport_safety_and_identity_boundaries_remain(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        for marker in (
            "validate_payload_controls",
            "runtime_process_matches",
            "STATE_OWNED",
            "STATE_PLATFORM_MATCH",
            "STATE_REPO_MATCH",
            "STATE_PANE_COUNT",
            "expected_child_fingerprint",
            "payload_fingerprint",
            "cleanup_terminal_socket",
        ):
            self.assertIn(marker, source, marker)

    def test_issue9_generated_platform_copies_are_renderer_clean(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RENDERER), "--check"],
            cwd=PROJECT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        shared = (
            "scripts/kaola-tmux.sh",
            "scripts/kaola-pane-relay.py",
            "scripts/kaola-relay-client.py",
            "scripts/kaola-relay-protocol.py",
            "scripts/kaola-observation.py",
            "scripts/kaola-model-policy.py",
        )
        for platform in PLATFORMS:
            package = PROJECT / "skills" / platform
            self.assertTrue(package.is_dir(), platform)
            for relative in shared:
                source = PROJECT / relative
                generated = package / relative
                self.assertTrue(generated.is_file(), str(generated))
                self.assertEqual(
                    hashlib.sha256(source.read_bytes()).digest(),
                    hashlib.sha256(generated.read_bytes()).digest(),
                    f"generated copy drifted: {platform}/{relative}",
                )

    def test_issue9_grok_golden_bytes_remain_frozen(self) -> None:
        actual = {
            path.relative_to(GOLDEN).as_posix()
            for path in GOLDEN.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, set(GOLDEN_SHA256))
        for relative, expected in GOLDEN_SHA256.items():
            path = GOLDEN / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), expected, relative
            )


if __name__ == "__main__":
    unittest.main()
