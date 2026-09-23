#!/usr/bin/env python3
"""Issue #22 RED contract: default start bypasses security-permission prompts.

Public ``start`` (no caller ``--permission-mode``) must launch skip-all on ACP,
the only transport since Issue #130 retired PTY/tmux. Known ACP knobs:

- Claude ACP: ``mode=bypassPermissions``
- Kimi ACP: ``mode=yolo``
- Devin ACP: ``mode=bypass``
- Cursor ACP: ``cursor-agent --yolo acp``
- Grok ACP: ``grok agent --always-approve stdio``
- Codex ACP: ``mode=agent-full-access``

OpenCode ACP has no skip argv and is not asserted as skipped.
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
ACP = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
CLAUDE_ADAPTER = PROJECT / "scripts" / "adapters" / "claude-code.sh"
DEVIN_ADAPTER = PROJECT / "scripts" / "adapters" / "devin.sh"
# Issue #73 binds Orchestrator dispatch to one canonical root. This suite starts
# against its own throwaway repository, which is an ordinary standalone
# invocation, so it states that intent instead of inheriting the operator shell.
CANONICAL_KEY = "KAOLA_PROJECT_RUNNER_CANONICAL_REPO"


class Issue22StaticSkipKnobs(unittest.TestCase):
    """Source contracts for measured skip knobs. Unknown ACP mode strings omitted."""

    def test_claude_adapter_still_forwards_permission_mode(self) -> None:
        body = CLAUDE_ADAPTER.read_text(encoding="utf-8")
        self.assertIn('--permission-mode "$permission_mode"', body)

    def test_devin_adapter_still_forwards_permission_mode(self) -> None:
        body = DEVIN_ADAPTER.read_text(encoding="utf-8")
        self.assertIn('--permission-mode "$permission_mode"', body)
        self.assertIn("--respect-workspace-trust false", body)

    def test_cursor_acp_command_includes_yolo(self) -> None:
        manifest = (PROJECT / "platforms" / "cursor-cli.yaml").read_text(encoding="utf-8")
        self.assertIn('acp_command: "cursor-agent --yolo acp"', manifest)

    def test_grok_acp_command_includes_always_approve(self) -> None:
        manifest = (PROJECT / "platforms" / "grok.yaml").read_text(encoding="utf-8")
        self.assertIn('acp_command: "grok agent --always-approve stdio"', manifest)

    def test_acp_skip_mode_maps_devin_bypass(self) -> None:
        body = ACP.read_text(encoding="utf-8")
        self.assertIn('"devin": "bypass"', body)
        self.assertIn('"kimi-cli": "yolo"', body)
        self.assertIn('"claude-code": "bypassPermissions"', body)


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
        env.pop(CANONICAL_KEY, None)
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
        self.assertNotEqual(start.get("result"), "refused", f"start was refused: {start}")
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

    def unanswered_permission_requests(self, send: dict, observe: dict) -> list[dict]:
        """Unanswered ``session/request_permission`` still listed as pending."""
        pending: list[dict] = []
        for receipt in (send, observe):
            for entry in receipt.get("pending_permissions") or []:
                if entry not in pending:
                    pending.append(entry)
        return pending

    def permit_actions(self, send: dict, observe: dict) -> list[str]:
        """Permit command or client reply to ``session/request_permission``."""
        found: list[str] = []
        for receipt, label in ((send, "send"), (observe, "observe")):
            if receipt.get("command") == "permit" or receipt.get("action") == "permit":
                found.append(f"{label}.command=permit")
            if "permitted" in receipt:
                found.append(f"{label}.permitted={receipt.get('permitted')!r}")
        for event in self.read_mock_log():
            if (
                event.get("event") == "outbound_response"
                and event.get("method") == "session/request_permission"
            ):
                found.append(f"answered request_permission id={event.get('id')!r}")
        return found

    def still_waiting_on_permission(self, send: dict, observe: dict) -> list[str]:
        """Turn still active and blocked on permission, not ``end_turn``."""
        reasons: list[str] = []
        pending = self.unanswered_permission_requests(send, observe)
        if send.get("outcome") in ("prompt_timeout", "in_progress") and pending:
            reasons.append(
                f"send outcome={send.get('outcome')!r} with pending_permissions={pending!r}"
            )
        if observe.get("turn_active") and (
            pending or observe.get("activity_hint") == "waiting"
        ):
            reasons.append(
                "observe turn still active waiting on permission: "
                f"activity_hint={observe.get('activity_hint')!r} pending={pending!r}"
            )
        return reasons

    def test_default_send_wait_completes_without_permit(self) -> None:
        start = self._tmux("start")
        self._started = True
        self.assertNotEqual(start.get("result"), "refused", f"start was refused: {start}")
        self.assertIsNone(start.get("error"), f"start failed: {start}")
        send = self._tmux(
            "send", "--text", "write a file then run a shell", "--timeout", "15"
        )
        self.assertIsNone(send.get("error"), f"send failed: {send}")
        self.assertEqual(send.get("outcome"), "turn_completed")
        self.assertEqual(send.get("stop_reason"), "end_turn")
        observe = self._tmux("observe")
        unanswered = self.unanswered_permission_requests(send, observe)
        self.assertEqual(
            unanswered,
            [],
            "send --wait must not leave unanswered session/request_permission: "
            f"pending={unanswered!r} observe={observe}",
        )
        permit_steps = self.permit_actions(send, observe)
        self.assertEqual(
            permit_steps,
            [],
            "send --wait must complete without a permit action: "
            f"{permit_steps}; send={send}",
        )
        waiting = self.still_waiting_on_permission(send, observe)
        self.assertEqual(
            waiting,
            [],
            "send --wait must not leave an active turn waiting on permission: "
            f"{waiting}",
        )


class Issue22AcpDefaultStart(unittest.TestCase):
    """Default ACP skip knobs must be forwarded by the shared entrypoint.

    Issue #130 removed the PTY no-flag ``permission_mode`` mapping with the
    tmux branch; the no-flag ACP ``--mode`` mapping is the one that remains.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_devin_acp_default_forwards_bypass(self) -> None:
        self.assertIn(
            "devin) acp_args+=(--mode bypass) ;;",
            self.runner,
            "no-flag Devin ACP start must forward --mode bypass",
        )

    def test_claude_acp_default_forwards_bypass_permissions(self) -> None:
        self.assertIn(
            "claude-code) acp_args+=(--mode bypassPermissions) ;;",
            self.runner,
            "no-flag Claude ACP start must forward --mode bypassPermissions",
        )
        self.assertNotIn("claude-code) permission_mode=bypassPermissions ;;", self.runner)

    def test_codex_acp_default_forwards_agent_full_access(self) -> None:
        self.assertIn(
            "codex) acp_args+=(--mode agent-full-access) ;;",
            self.runner,
            "no-flag Codex ACP start must forward --mode agent-full-access",
        )


class Issue22CodexPermissionMappings(unittest.TestCase):
    """Codex ACP mode names (issue #28); the PTY sandbox/approval pairs retired with #130."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = (PROJECT / "scripts" / "kaola-acp.py").read_text(encoding="utf-8")
        cls.runner = RUNNER.read_text(encoding="utf-8")
        cls.manifest = (PROJECT / "platforms" / "codex.yaml").read_text(encoding="utf-8")

    def test_acp_skip_mode_maps_codex_agent_full_access(self) -> None:
        self.assertIn('"codex": "agent-full-access"', self.acp)

    def test_manifest_pins_codex_acp_command(self) -> None:
        self.assertIn(
            'acp_command: "npx --yes --package @openai/codex@0.155.1 '
            '--package @agentclientprotocol/codex-acp@1.13.0 codex-acp"',
            self.manifest,
        )
        self.assertNotIn("default_transport", self.manifest)


if __name__ == "__main__":
    unittest.main()
