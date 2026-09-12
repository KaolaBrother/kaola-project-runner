#!/usr/bin/env python3
"""Issue #22 RED contract: default start bypasses security-permission prompts.

Public ``start`` (no caller ``--permission-mode``) must launch skip-all on both
ACP and PTY/tmux. Known knobs only:

- Claude PTY: ``bypassPermissions`` or ``dontAsk``
- Devin PTY: ``dangerous`` (workspace-trust false is not enough)
- Kimi ACP: ``mode=yolo``

Cursor/Devin/OpenCode ACP ``mode`` values are unmeasured and are not asserted.
Claude ACP initialize is still ``probe-eof``; this file does not invent a knob.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT / "scripts" / "kaola-tmux.sh"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
CLAUDE_ADAPTER = PROJECT / "scripts" / "adapters" / "claude-code.sh"
DEVIN_ADAPTER = PROJECT / "scripts" / "adapters" / "devin.sh"


class Issue22StaticSkipKnobs(unittest.TestCase):
    """Source contracts for measured skip knobs. Unknown ACP mode strings omitted."""

    def test_devin_manifest_documents_dangerous_not_auto(self) -> None:
        manifest = (PROJECT / "platforms" / "devin.yaml").read_text(encoding="utf-8")
        match = re.search(r"launch_summary:.*?--permission-mode\s+(\S+)", manifest)
        self.assertIsNotNone(match, "launch_summary permission-mode not found")
        self.assertEqual(
            match.group(1),
            "dangerous",
            "no-flag Devin start must document --permission-mode dangerous; "
            "--respect-workspace-trust false does not satisfy Issue #22",
        )

    def test_claude_adapter_still_forwards_permission_mode(self) -> None:
        body = CLAUDE_ADAPTER.read_text(encoding="utf-8")
        self.assertIn('--permission-mode "$permission_mode"', body)

    def test_devin_adapter_still_forwards_permission_mode(self) -> None:
        body = DEVIN_ADAPTER.read_text(encoding="utf-8")
        self.assertIn('--permission-mode "$permission_mode"', body)
        self.assertIn("--respect-workspace-trust false", body)


class Issue22KimiAcpDefaultYolo(unittest.TestCase):
    """Default public ACP start for kimi-cli must set mode=yolo without caller flag."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-issue-22-acp-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"i22kimi-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        if self._started:
            self._tmux("stop", "--force")

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        env["KAOLA_ACP_COMMAND"] = (
            f"{sys.executable} {MOCK} --scenario permission_unless_yolo"
        )
        return env

    def _tmux(self, command: str, *args: str, timeout: float = 30) -> dict:
        argv = [
            "bash", str(RUNNER), "kimi-cli", command,
            "--repo", str(self.repo), "--session", self.session, *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kimi-cli {command} did not emit JSON\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        return receipt

    def read_mock_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_default_start_sets_kimi_mode_yolo(self) -> None:
        start = self._tmux("start")
        self._started = True
        self.assertIsNone(start.get("error"), f"start failed: {start}")
        configured = [
            event
            for event in self.read_mock_log()
            if event.get("event") == "set_config_option"
        ]
        values = [
            (event.get("params") or {}).get("configId")
            or (event.get("params") or {}).get("config_id")
            for event in configured
        ]
        yolo = [
            event
            for event in configured
            if (
                (event.get("params") or {}).get("configId") == "mode"
                or (event.get("params") or {}).get("config_id") == "mode"
            )
            and (event.get("params") or {}).get("value") == "yolo"
        ]
        self.assertTrue(
            yolo,
            "default kimi ACP start (no --permission-mode) must set "
            f"session/set_config_option mode=yolo; saw {configured!r} ids={values!r}",
        )

    def test_default_send_wait_completes_without_permit(self) -> None:
        start = self._tmux("start")
        self._started = True
        self.assertIsNone(start.get("error"), f"start failed: {start}")
        send = self._tmux(
            "send", "--text", "write a file then run a shell", "--timeout", "15"
        )
        self.assertIsNone(send.get("error"), f"send failed: {send}")
        self.assertEqual(send.get("outcome"), "turn_completed")
        self.assertEqual(send.get("stop_reason"), "end_turn")
        observe = self._tmux("observe")
        pending = observe.get("pending_permissions") or []
        self.assertEqual(
            pending,
            [],
            "send --wait must not hang in pending_permissions after default yolo start: "
            f"{observe}",
        )
        self.assertNotIn("permit", json.dumps(send))


class Issue22PtyDefaultStart(unittest.TestCase):
    """Default PTY skip knobs must be assigned by core, not only listed as allowed values.

    Live tmux start is covered by ``test-adapters.sh`` / ``test-claude-code-runtime.sh``.
    This file keeps a tmux-independent oracle so Issue #22 is RED even when a
    nested Cloud tmux server cannot hold a pane.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_claude_no_flag_default_is_bypass_or_dont_ask(self) -> None:
        remainder = re.sub(
            r'case "\$permission_mode" in acceptEdits\|auto\|bypassPermissions\|manual\|dontAsk\|plan\).*',
            "",
            self.runner,
        )
        self.assertTrue(
            "bypassPermissions" in remainder or "dontAsk" in remainder,
            "no-flag Claude PTY start must assign bypassPermissions or dontAsk; "
            "listing those tokens only in the allowlist is not enough",
        )

    def test_devin_no_flag_default_is_dangerous(self) -> None:
        remainder = re.sub(
            r'case "\$permission_mode" in auto\|accept-edits\|smart\|dangerous\).*',
            "",
            self.runner,
        )
        self.assertTrue(
            "dangerous" in remainder,
            "no-flag Devin PTY start must assign dangerous; listing it only in "
            "the allowlist (or only skipping workspace trust) is not enough",
        )


if __name__ == "__main__":
    unittest.main()
