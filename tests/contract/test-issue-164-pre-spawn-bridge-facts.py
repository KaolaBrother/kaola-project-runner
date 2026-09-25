#!/usr/bin/env python3
"""Issue #164: pre-spawn bridge and ZCode-runtime refusals carry preflight facts.

Since #180 the refusal carries those facts without the ``--version``
probe: its runtime-binary facts match preflight's minus ``version``, only
``preflight`` still reports it, and a refusal never waits on the runtime.
Since #180 the same consolidation is counted in-process: one start scans
the installed Skill roots once, a drain-restart twice.

Offline only. A live seat, when one is required, is the mock ACP agent under
an isolated HOME and record root, and each one is force-stopped before the
temporary directory is removed. No platform CLI is launched.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable

MISSING_BRIDGE = "python3 $SKILL_DIR/scripts/missing-bridge-164.py"
BRIDGE_FACT_KEYS = ("bridge", "runtime_binary")
BRIDGE_SHAPE = ("relative", "path", "layout", "present", "upstream_pin", "verified_versions")
RUNTIME_SHAPE = ("env", "path", "absolute", "present", "passed_as")


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def load_acp():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_acp_issue164", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PreSpawnBridgeFactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git_init(self.repo)
        self.started: list[tuple[str, str]] = []
        self.agent = (
            f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"
        )
        self.claude_bin = self.root / "claude-stub"
        self.claude_bin.write_text("#!/bin/sh\nprintf 'claude-stub 9.9.9\\n'\n", encoding="utf-8")
        self.claude_bin.chmod(self.claude_bin.stat().st_mode | stat.S_IXUSR)
        self.zcode_entry = self.root / "zcode-entry.js"
        self.zcode_entry.write_text("// not a runtime\n", encoding="utf-8")
        self.zcode_node = self.root / "zcode-node"
        self.zcode_node.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.zcode_node.chmod(self.zcode_node.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        for platform, session in self.started:
            self.run_cli(platform, "stop", "--force", session=session, check=False)
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
        }
        base.update(extra)
        return base

    def run_cli(self, platform: str, command: str, *args: str, session: str,
                check: bool = True, env: dict[str, str] | None = None,
                agent: str | None = None, manifest_command: bool = False
                ) -> tuple[subprocess.CompletedProcess, dict]:
        argv = [PYTHON, str(CLI), platform, command, "--repo", str(self.repo),
                "--session", session, *args]
        if command in ("start", "drain-restart"):
            self.started.append((platform, session))
            if not manifest_command:
                argv += ["--command", agent or self.agent]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env or self.env(), timeout=90,
        )
        payload: dict = {}
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            payload = json.loads(lines[-1])
        if check and result.returncode != 0:
            self.fail(f"{command} exited {result.returncode}: {payload or result.stderr[-800:]}")
        return result, payload

    def bridge_facts(self, receipt: dict) -> dict:
        return {key: receipt[key] for key in BRIDGE_FACT_KEYS if key in receipt}

    def bridge_facts_without_version(self, receipt: dict) -> dict:
        # A rebuilt dict, never a mutation: bridge_facts() copies only the top
        # level, so popping "version" in place would edit the caller's receipt.
        facts = self.bridge_facts(receipt)
        binary = facts.get("runtime_binary")
        if isinstance(binary, dict):
            facts["runtime_binary"] = {key: value for key, value in binary.items()
                                       if key != "version"}
        return facts

    def assert_preflight_facts(self, refusal: dict, preflight: dict, code: str) -> None:
        self.assertEqual(refusal.get("error", {}).get("code"), code, refusal)
        self.assertEqual(preflight.get("error", {}).get("code"), code, preflight)
        self.assertEqual(
            refusal.get("error", {}).get("message"),
            preflight.get("error", {}).get("message"),
        )
        facts = self.bridge_facts(refusal)
        self.assertTrue(facts, refusal)
        self.assertEqual(facts, self.bridge_facts_without_version(preflight))
        bridge = facts.get("bridge")
        if bridge is not None:
            self.assertNotIn("token", bridge)
            for key in BRIDGE_SHAPE:
                self.assertIn(key, bridge, bridge)
        binary = facts.get("runtime_binary")
        if binary is not None:
            self.assertNotIn("version", binary, refusal)
            for key in RUNTIME_SHAPE:
                self.assertIn(key, binary, binary)
        self.assertIs(refusal.get("mutation_performed"), False, refusal)
        self.assertEqual(refusal.get("mutation_status"), "not_started", refusal)

    def assert_no_record(self, platform: str, session: str) -> None:
        self.assertFalse(
            any(self.records.glob(f"{platform}/{session}/*/record.json")),
            f"refused {platform} {session} wrote a holder record",
        )

    def test_start_missing_bridge_matches_preflight(self) -> None:
        session = "claude-code-KPR-i164-bridge"
        env = self.env(CLAUDE_BIN=str(self.claude_bin))
        _result, preflight = self.run_cli(
            "claude-code", "preflight", "--command", MISSING_BRIDGE,
            session=session, env=env)
        result, refusal = self.run_cli(
            "claude-code", "start", session=session, agent=MISSING_BRIDGE,
            check=False, env=env)
        self.assertEqual(result.returncode, 0, refusal or result.stderr)
        self.assert_preflight_facts(refusal, preflight, "acp-bridge-missing")
        self.assertIs(refusal["bridge"]["present"], False, refusal["bridge"])
        self.assertIsNone(refusal["bridge"]["path"])
        self.assertEqual(refusal["runtime_binary"]["path"], str(self.claude_bin))
        self.assertIs(refusal["runtime_binary"]["present"], True)
        self.assertNotIn("version", refusal["runtime_binary"], refusal)
        self.assertEqual(preflight["runtime_binary"]["version"], "claude-stub 9.9.9")
        self.assertNotIn("result", refusal)
        self.assert_no_record("claude-code", session)

    def test_start_missing_bridge_does_not_probe_an_absent_runtime(self) -> None:
        session = "claude-code-KPR-i164-nobin"
        missing = str(self.root / "no-such-claude")
        env = self.env(CLAUDE_BIN=missing)
        _result, preflight = self.run_cli(
            "claude-code", "preflight", "--command", MISSING_BRIDGE,
            session=session, env=env)
        result, refusal = self.run_cli(
            "claude-code", "start", session=session, agent=MISSING_BRIDGE,
            check=False, env=env)
        self.assertEqual(result.returncode, 0, refusal or result.stderr)
        self.assert_preflight_facts(refusal, preflight, "acp-bridge-missing")
        self.assertIs(refusal["runtime_binary"]["present"], False)
        self.assertNotIn("version", refusal["runtime_binary"])
        self.assertNotIn("version", preflight["runtime_binary"])
        self.assert_no_record("claude-code", session)

    def test_refusals_return_without_waiting_on_a_hanging_version(self) -> None:
        # #171, folded into #180: a refused start/drain-restart never runs
        # the runtime --version probe, so a hanging runtime cannot stall it
        # (the old probe bound was 15 s; both refusals stay well under it).
        session = "claude-code-KPR-i180-hang"
        hanging = self.root / "claude-hangs"
        hanging.write_text("#!/bin/sh\nsleep 60\n", encoding="utf-8")
        hanging.chmod(hanging.stat().st_mode | stat.S_IXUSR)
        live = self.env(CLAUDE_BIN=str(self.claude_bin))
        refuse = self.env(CLAUDE_BIN=str(hanging))
        began = time.monotonic()
        _result, refusal = self.run_cli(
            "claude-code", "start", session=session, agent=MISSING_BRIDGE,
            check=False, env=refuse)
        self.assertLess(time.monotonic() - began, 10.0,
                        "the start refusal waited on the --version probe")
        self.assertEqual(refusal.get("error", {}).get("code"), "acp-bridge-missing",
                         refusal)
        started = self.run_cli("claude-code", "start", session=session, env=live)[1]
        self.assertEqual(started.get("state"), "ready", started)
        pid = started["holder_pid"]
        began = time.monotonic()
        _result, refusal = self.run_cli(
            "claude-code", "drain-restart", "--resume", started["acp_session_id"],
            session=session, agent=MISSING_BRIDGE, check=False, env=refuse)
        self.assertLess(time.monotonic() - began, 10.0,
                        "the drain-restart refusal waited on the --version probe")
        self.assertEqual(refusal.get("error", {}).get("code"), "acp-bridge-missing",
                         refusal)
        self.assertNotIn("version", refusal["runtime_binary"], refusal)
        self.assertTrue(_pid_alive(pid), "the pre-stop refusal took the seat down")

    def test_worker_skill_alignment_runs_once_per_start(self) -> None:
        # #180: pre_spawn_refusal is the single start-decision site, so one
        # start scans the installed Skill roots once; a drain-restart scans
        # twice - the pre-stop decision plus the post-stop start.
        session = "claude-code-KPR-i180-count"
        mod = load_acp()
        calls: list[str] = []
        real = mod.worker_skill_alignment

        def counting(repo: str, platform: str = "zcode") -> dict:
            calls.append(platform)
            return real(repo, platform)

        mod.worker_skill_alignment = counting
        # The in-process start leaves its holder Popen to this case's
        # tearDown stop; its garbage collection would warn.
        warnings.simplefilter("ignore", ResourceWarning)
        saved_argv, saved_env = sys.argv, dict(os.environ)
        os.environ.clear()
        os.environ.update(self.env(MOCK_ACP_RESUME_ANY="1"))
        try:
            sys.argv = [str(CLI), "claude-code", "start", "--repo", str(self.repo),
                        "--session", session, "--command", self.agent]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(mod.main(), 0, out.getvalue()[-800:])
            started = json.loads(out.getvalue().strip().splitlines()[-1])
            self.started.append(("claude-code", session))
            self.assertEqual(started["state"], "ready", started)
            self.assertEqual(len(calls), 1, calls)
            calls.clear()
            sys.argv = [str(CLI), "claude-code", "drain-restart", "--repo",
                        str(self.repo), "--session", session, "--command",
                        self.agent, "--resume", started["acp_session_id"]]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(mod.main(), 0, out.getvalue()[-800:])
            restarted = json.loads(out.getvalue().strip().splitlines()[-1])
            self.assertEqual(restarted["state"], "ready", restarted)
            self.assertEqual(len(calls), 2, calls)
        finally:
            sys.argv = saved_argv
            os.environ.clear()
            os.environ.update(saved_env)

    def test_start_missing_zcode_runtime_matches_preflight(self) -> None:
        session = "zcode-KPR-i164-runtime"
        _result, preflight = self.run_cli("zcode", "preflight", session=session)
        result, refusal = self.run_cli(
            "zcode", "start", session=session, manifest_command=True, check=False)
        self.assertEqual(result.returncode, 0, refusal or result.stderr)
        self.assert_preflight_facts(refusal, preflight, "acp-runtime-missing")
        self.assertIs(refusal["bridge"]["present"], True, refusal["bridge"])
        self.assertTrue(refusal["bridge"]["sha256"], refusal["bridge"])
        self.assertNotIn("runtime_binary", refusal)
        self.assertIn("KAOLA_ZCODE_ENTRY", refusal["error"]["message"])
        self.assert_no_record("zcode", session)

    def test_drain_restart_missing_bridge_keeps_facts_and_the_seat(self) -> None:
        session = "claude-code-KPR-i164-drainbr"
        env = self.env(CLAUDE_BIN=str(self.claude_bin))
        started = self.run_cli("claude-code", "start", session=session, env=env)[1]
        self.assertEqual(started.get("state"), "ready", started)
        pid = started["holder_pid"]
        _result, preflight = self.run_cli(
            "claude-code", "preflight", "--command", MISSING_BRIDGE,
            session=session, env=env)
        result, refusal = self.run_cli(
            "claude-code", "drain-restart", "--resume", started["acp_session_id"],
            session=session, agent=MISSING_BRIDGE, check=False, env=env)
        self.assertEqual(result.returncode, 0, refusal or result.stderr)
        self.assert_preflight_facts(refusal, preflight, "acp-bridge-missing")
        self.assertEqual(refusal.get("action"), "drain-restart", refusal)
        self.assertIsInstance(refusal.get("start_selection"), dict, refusal)
        self.assertIn("fast", refusal["start_selection"])
        self.assertTrue(_pid_alive(pid), refusal)
        self.assertNotIn("version", refusal["runtime_binary"], refusal)

    def test_drain_restart_missing_zcode_runtime_keeps_facts_and_the_seat(self) -> None:
        session = "zcode-KPR-i164-drainrt"
        live = self.env(
            KAOLA_ZCODE_ENTRY=str(self.zcode_entry),
            KAOLA_ZCODE_NODE=str(self.zcode_node),
        )
        started = self.run_cli("zcode", "start", session=session, env=live)[1]
        self.assertEqual(started.get("state"), "ready", started)
        pid = started["holder_pid"]
        _result, preflight = self.run_cli("zcode", "preflight", session=session)
        result, refusal = self.run_cli(
            "zcode", "drain-restart", "--resume", started["acp_session_id"],
            session=session, manifest_command=True, check=False)
        self.assertEqual(result.returncode, 0, refusal or result.stderr)
        self.assert_preflight_facts(refusal, preflight, "acp-runtime-missing")
        self.assertEqual(refusal.get("action"), "drain-restart", refusal)
        self.assertIsInstance(refusal.get("start_selection"), dict, refusal)
        self.assertIs(refusal["bridge"]["present"], True, refusal["bridge"])
        self.assertTrue(_pid_alive(pid), refusal)


if __name__ == "__main__":
    unittest.main()
