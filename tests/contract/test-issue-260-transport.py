#!/usr/bin/env python3
"""Issue #260: input receipts and isolated parent-exit evidence.

These parent tests use a mock ACP agent. They do not exit Grok Bot or its
execution service and cannot establish that service's cleanup scope.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts/kaola-acp.py"
RUNNER = PROJECT / "scripts/kaola-tmux.sh"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("issue260_fixture", PROJECT / "tests/contract/test-acp-contract.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class InputReceiptTests(unittest.TestCase):
    def test_invalid_flags_have_json_on_both_entries_for_every_platform(self):
        platforms = ("claude-code", "codex", "cursor-cli", "devin", "droid", "dsh", "grok", "kimi-cli", "opencode", "zcode")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            records = root / "records"
            env = {k: v for k, v in os.environ.items() if not k.startswith(("KAOLA_", "KPR_"))}
            env["KAOLA_ACP_RECORD_ROOT"] = str(records)
            for platform in platforms:
                for entry in ([sys.executable, str(CLI)], ["bash", str(RUNNER)]):
                    for flags in (["--text-file", "SECRET_PROMPT_VALUE"], ["--text"], ["--timeout", "SECRET_INVALID_NUMBER"], ["--fast", "SECRET_INVALID_CHOICE"]):
                        with self.subTest(platform=platform, entry=entry, flags=flags):
                            result = subprocess.run([*entry, platform, "start" if flags[0] == "--fast" else "send", "--repo", str(repo), "--session", "i260-invalid", *flags], env=env, capture_output=True, text=True, timeout=10)
                            self.assertNotEqual(result.returncode, 0)
                            receipt = json.loads(result.stdout)
                            self.assertEqual(receipt["schema_version"], 3)
                            self.assertEqual(receipt["error"]["code"], "invalid-input")
                            self.assertEqual(receipt["mutation_status"], "not_started")
                            self.assertIs(receipt["mutation_performed"], False)
                            self.assertEqual(receipt["platform"], platform)
                            self.assertNotIn("SECRET", result.stdout + result.stderr)
                            self.assertFalse(records.exists())

    def test_missing_repo_session_text_and_special_command_flags(self):
        cases = (["grok", "send"], ["grok", "send", "--repo", str(PROJECT)], ["grok", "send", "--repo", str(PROJECT), "--session", "i260-empty"], ["survey", "--bad-flag"], ["list", "--bad-flag"], ["packages", "--bad-flag"], ["model-package", "--bad-flag"], [])
        for args in cases:
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["error"]["code"], "invalid-input")
        for entry in ([sys.executable, str(CLI)], ["bash", str(RUNNER)]):
            result = subprocess.run([*entry, "--help"], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage", result.stdout.lower())


class OwnedSessionTests(fixture.AcpSessionFixture, unittest.TestCase):
    def test_bad_flag_does_not_change_an_existing_prompt(self):
        self.cli("start", turn_ms=2000)
        self._started = True
        accepted = self.cli("send", "--text", "I260_VALID_PROMPT", "--no-wait")
        self.assertTrue(accepted["mutation_performed"])
        paths = list(self.record_root.rglob("record.json"))
        self.assertEqual(len(paths), 1)
        before = json.loads(paths[0].read_text())["last_prompt"]
        result = subprocess.run(["bash", str(RUNNER), "grok", "send", "--repo", str(self.repo), "--session", self.session, "--text-file", "/tmp/unused"], env=self.env(), capture_output=True, text=True, timeout=10)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertEqual(json.loads(paths[0].read_text())["last_prompt"], before)
        settled = self.cli("wait", "--timeout", "10")
        self.assertEqual(settled["stop_reason"], "end_turn")

    def parent_exit(self, terminate_group):
        argv = [sys.executable, str(CLI), "grok", "start", "--repo", str(self.repo), "--session", self.session, "--command", shlex.join([sys.executable, str(fixture.MOCK), "--scenario", "normal"])]
        receipt_path = self.root / (self.session + ".start.json")
        code = "import pathlib,subprocess,sys,time; r=subprocess.run(sys.argv[2:],capture_output=True,text=True); pathlib.Path(sys.argv[1]).write_text(r.stdout); " + ("time.sleep(30)" if terminate_group else "sys.exit(r.returncode)")
        parent = subprocess.Popen([sys.executable, "-c", code, str(receipt_path), *argv], env=self.env(), start_new_session=True)
        self._started = True
        try:
            self.assertTrue(fixture.wait_for(lambda: receipt_path.exists(), 15))
            started = json.loads(receipt_path.read_text())
            self.assertNotIn("error", started)
            holder_pid = started["holder_pid"]
            self.assertEqual(os.getpgid(holder_pid), holder_pid)
            self.assertNotEqual(os.getpgid(holder_pid), parent.pid)
            if terminate_group:
                os.killpg(parent.pid, signal.SIGTERM)
            parent.wait(timeout=5)
            observed = self.cli("status")
            self.assertEqual(observed["holder_instance_id"], started["holder_instance_id"])
            sent = self.cli("send", "--text", "I260_AFTER_PARENT_EXIT")
            self.assertEqual(sent["stop_reason"], "end_turn")
            stopped = self.cli("stop", "--force")
            self._started = False
            self.assertEqual(stopped["residual_pids"], [])
            print(json.dumps({"item": 6, "scope": "mock ACP; parent simulation only", "exit": "SIGTERM parent group" if terminate_group else "normal parent exit", "parent_pid": parent.pid, "parent_returncode": parent.returncode, "holder_pid": holder_pid, "holder_instance_id": started["holder_instance_id"], "acp_session_id": started["acp_session_id"], "session": self.session, "send_stop_reason": sent["stop_reason"], "residual_pids": stopped["residual_pids"]}, sort_keys=True))
        finally:
            if parent.poll() is None:
                parent.terminate()
                parent.wait(timeout=5)

    def test_normal_parent_exit_keeps_the_owned_holder(self):
        self.parent_exit(False)

    def test_parent_group_sigterm_keeps_the_owned_holder(self):
        self.parent_exit(True)


if __name__ == "__main__":
    unittest.main()
