#!/usr/bin/env python3
"""Issue #146: the holder's session/new wait is a per-platform manifest fact.

Live codex answered ``session/new`` about 18.1 s after holder creation while
the holder had already given up at its fixed 15 s wait and failed the start
with ``acp-session-timeout`` (the answer landed as ``orphan_response``;
``kaola-workflow/archive/issue-145/.cache/probes/``). The fix is an optional
manifest key ``acp_session_new_timeout`` that the holder honours for
``session/new`` in both ``start`` and the ``preflight`` probe, while the client
start window and the probe bound grow by the same amount so they still enclose
it. Platforms that declare nothing keep today's 15 s / 20 s / 60 s exactly.

Timings are scaled down (a 2.5 s mock delay against 1 s and 10 s waits) so the
suite stays hermetic and quick; the mock delays its answer, it never drops it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"
SKILLS = PROJECT / "skills"
HOLDER = SCRIPTS / "kaola-acp-holder.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
DELAY_ENV = "MOCK_ACP_SESSION_NEW_DELAY_MS"
DELAY_MS = 2500
# The slowest live codex session/new answer measured in #145 (holder creation
# to orphan_response), in seconds.
MEASURED_CODEX_MAX = 18.1


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hermetic_env(**extra: str) -> dict[str, str]:
    """No inherited KAOLA_* Host/dispatcher facts, so a live Host cannot leak in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
    env.update(extra)
    return env


def mock_command() -> str:
    return f"{sys.executable} {MOCK} --scenario normal"


class TestManifestFact(unittest.TestCase):
    """The key is optional, validated, declared by codex, and rendered."""

    def setUp(self) -> None:
        self.render = load("render-skills")
        self.acp = load("kaola-acp")

    def manifest_with(self, value: str | None) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="kaola-i146-manifest-")
        self.addCleanup(tmp.cleanup)
        lines = [line for line in (PLATFORMS / "grok.yaml").read_text(encoding="utf-8").splitlines()
                 if not line.startswith("acp_session_new_timeout:")]
        if value is not None:
            lines.append(f"acp_session_new_timeout: {json.dumps(value)}")
        path = Path(tmp.name) / "grok.yaml"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_codex_declares_a_wait_above_the_measured_latency(self) -> None:
        codex = self.render.parse_manifest(PLATFORMS / "codex.yaml")
        self.assertGreater(float(codex["acp_session_new_timeout"]), MEASURED_CODEX_MAX)

    def test_undeclared_platforms_keep_the_shared_default(self) -> None:
        self.assertEqual(self.acp.SESSION_NEW_TIMEOUT, 15.0)
        self.assertEqual(self.acp.START_WAIT, 20.0)
        self.assertEqual(self.acp.PROBE_WAIT, 60.0)
        for path in sorted(PLATFORMS.glob("*.yaml")):
            if path.stem == "codex":
                continue
            with self.subTest(platform=path.stem):
                manifest = self.render.parse_manifest(path)
                self.assertNotIn("acp_session_new_timeout", manifest)

    def test_render_rejects_a_non_positive_or_non_numeric_wait(self) -> None:
        self.render.parse_manifest(self.manifest_with(None))
        self.render.parse_manifest(self.manifest_with("45"))
        self.render.parse_manifest(self.manifest_with("600"))
        # 1e10 would overflow threading.TIMEOUT_MAX inside the holder's wait.
        for bad in ("", "0", "-5", "abc", "inf", "nan", "601", "1e10"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    self.render.parse_manifest(self.manifest_with(bad))

    def test_client_window_encloses_the_declared_wait(self) -> None:
        class Args:
            manifest: dict[str, str] = {}

        args = Args()
        args.manifest = {}
        self.assertEqual(self.acp.session_new_timeout(args), 15.0)
        self.assertEqual(self.acp.session_new_extra(args), 0.0)
        args.manifest = {"acp_session_new_timeout": "60"}
        self.assertEqual(self.acp.session_new_timeout(args), 60.0)
        self.assertEqual(self.acp.session_new_extra(args), 45.0)
        # A shorter declared wait never shrinks the shared start window.
        args.manifest = {"acp_session_new_timeout": "5"}
        self.assertEqual(self.acp.session_new_extra(args), 0.0)
        args.manifest = {"acp_session_new_timeout": "garbage"}
        self.assertEqual(self.acp.session_new_timeout(args), 15.0)
        args.manifest = {"acp_session_new_timeout": "1e10"}
        self.assertEqual(self.acp.session_new_timeout(args), 15.0)

    def test_generated_codex_skill_carries_the_fact(self) -> None:
        generated = SKILLS / "codex-kaola-project-runner" / "scripts" / "platform.yaml"
        declared = [json.loads(line.split(":", 1)[1])
                    for line in generated.read_text(encoding="utf-8").splitlines()
                    if line.startswith("acp_session_new_timeout:")]
        self.assertEqual(
            declared,
            [self.render.parse_manifest(PLATFORMS / "codex.yaml")["acp_session_new_timeout"]],
        )


class TestProbeWait(unittest.TestCase):
    """The preflight probe honours --session-new-timeout."""

    def probe(self, wait: float) -> dict[str, Any]:
        tmp = tempfile.TemporaryDirectory(prefix="kaola-i146-probe-")
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        result = subprocess.run(
            [sys.executable, str(HOLDER), "--probe", "--repo", str(repo),
             "--platform", "grok", "--command", mock_command(),
             "--session-new-timeout", str(wait)],
            capture_output=True, text=True, timeout=60,
            env=hermetic_env(**{DELAY_ENV: str(DELAY_MS)}),
        )
        return json.loads(result.stdout)

    def test_short_wait_times_out_on_a_slow_session_new(self) -> None:
        probe = self.probe(1.0)
        self.assertEqual((probe.get("error") or {}).get("code"), "acp-session-timeout")

    def test_declared_wait_admits_the_same_slow_session_new(self) -> None:
        probe = self.probe(10.0)
        self.assertNotIn("error", probe)
        self.assertTrue(probe.get("session_probe"))


class TestStartWait(unittest.TestCase):
    """start through a generated worker Skill whose platform.yaml declares the wait."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i146-start-")
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name).resolve()
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.record_root = root / "records"
        self.skill = root / "skill"
        shutil.copytree(SKILLS / "grok-kaola-project-runner", self.skill)
        self.session = f"i146-{self._testMethodName.lower()}-{os.getpid()}"[:79]

    def declare(self, value: str) -> None:
        manifest = self.skill / "scripts" / "platform.yaml"
        lines = [line for line in manifest.read_text(encoding="utf-8").splitlines()
                 if not line.startswith("acp_session_new_timeout:")]
        lines.append(f"acp_session_new_timeout: {json.dumps(value)}")
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def acp(self, command: str, *args: str, timeout: float = 90,
            delay_ms: int = DELAY_MS) -> dict[str, Any]:
        result = subprocess.run(
            [sys.executable, str(self.skill / "scripts" / "kaola-acp.py"), "grok", command,
             "--repo", str(self.repo), "--session", self.session,
             "--command", mock_command(), *args],
            capture_output=True, text=True, timeout=timeout,
            env=hermetic_env(KAOLA_ACP_RECORD_ROOT=str(self.record_root),
                             **{DELAY_ENV: str(delay_ms)}),
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command}: rc={result.returncode}\n"
                      f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def start(self, delay_ms: int = DELAY_MS) -> dict[str, Any]:
        # A holder never self-exits: register its force-stop before the start.
        self.addCleanup(lambda: self.acp("stop", "--force", timeout=30))
        return self.acp("start", delay_ms=delay_ms)

    def test_short_declared_wait_fails_start_and_the_late_answer_is_orphaned(self) -> None:
        self.declare("1")
        receipt = self.start()
        self.assertEqual((receipt.get("error") or {}).get("code"), "acp-session-timeout", receipt)
        # The agent did answer; the holder had already given up (the #146 shape).
        deadline = time.monotonic() + 10
        orphaned = False
        while not orphaned and time.monotonic() < deadline:
            for path in self.record_root.rglob("events.jsonl"):
                text = path.read_text(encoding="utf-8", errors="replace")
                orphaned = orphaned or '"orphan_response"' in text
            if not orphaned:
                time.sleep(0.2)
        self.assertTrue(orphaned, "the delayed session/new answer never reached the holder")

    def test_declared_wait_starts_the_same_slow_agent(self) -> None:
        self.declare("10")
        receipt = self.start()
        self.assertNotIn("error", receipt, receipt)
        self.assertEqual(receipt.get("state"), "ready")
        self.assertTrue(receipt.get("acp_session_id"))

    # The next two cases cross the shared 15 s / 20 s bounds for real, so they
    # prove the client half: kaola-acp.py must hand the holder the declared wait
    # and widen its own start window, not just compute the numbers.

    def test_declared_wait_widens_the_client_start_window(self) -> None:
        # session/new answers ~21 s after spawn: past the shared 20 s start
        # window, inside the 35 s window a declared 30 s wait earns.
        self.declare("30")
        receipt = self.start(delay_ms=21000)
        self.assertNotIn("error", receipt, receipt)
        self.assertEqual(receipt.get("state"), "ready")

    def test_preflight_hands_the_probe_the_declared_wait(self) -> None:
        # session/new answers ~16 s after spawn: past the holder's 15 s default.
        self.declare("20")
        receipt = self.acp("preflight", delay_ms=16000)
        self.assertNotEqual((receipt.get("error") or {}).get("code"), "acp-session-timeout", receipt)
        self.assertTrue(receipt.get("session_probe"), receipt)


if __name__ == "__main__":
    unittest.main()
