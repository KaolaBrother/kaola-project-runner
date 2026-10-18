#!/usr/bin/env python3
"""Issue #352: the droid factory session/new wait is 60 s.

On v0.9.19 a live Droid ``session/new`` answered after about 24 s. The holder
was still on the shared 15 s default, so ``start`` returned
``acp-session-timeout``. The fix is the existing manifest key
``acp_session_new_timeout`` set to ``"60"`` on droid only. Codex stays 60 s.
Every other platform stays on the shared 15 s default.

The holder cases scale those three numbers by 10 (24 s -> 2.4 s, 15 s -> 1.5 s,
60 s -> 6 s), the same mock-delay shape as test-issue-146. The mock delays its
answer; it never drops it. ``session_new_timeout()`` and the ``start`` argv
are asserted at the real factory value, not the scaled one.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"
SKILLS = PROJECT / "skills"
HOLDER = SCRIPTS / "kaola-acp-holder.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
FAKE_DROID = PROJECT / "tests" / "contract" / "fake-droid-acp-agent.py"
DROID_SKILL = SKILLS / "droid-kaola-project-runner"
RENDERED_MANIFEST = DROID_SKILL / "scripts" / "platform.yaml"
DELAY_ENV = "MOCK_ACP_SESSION_NEW_DELAY_MS"
# Live droid answered session/new about 24 s after the request (Issue #352).
MEASURED_DROID_S = 24.0
DEFAULT_WAIT_S = 15.0
DECLARED_WAIT_S = 60.0
# Same idea as test-issue-146: shrink the waits so the suite stays hermetic.
SCALE = 10.0
SCALED_DELAY_MS = int(MEASURED_DROID_S / SCALE * 1000)
SCALED_DEFAULT_S = DEFAULT_WAIT_S / SCALE
SCALED_DECLARED_S = DECLARED_WAIT_S / SCALE


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hermetic_env(**extra: str) -> dict[str, str]:
    """No inherited KAOLA_* Host/dispatcher facts, so a live Host cannot leak in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_") or (k == "KAOLA_LAUNCH_BACKEND" and v == "direct")}
    env["KAOLA_LAUNCH_BACKEND"] = "direct"
    env.update(extra)
    return env


def declared_values(path: Path) -> list[str]:
    return [json.loads(line.split(":", 1)[1])
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("acp_session_new_timeout:")]


class Args:
    manifest: dict[str, str]


class TestDroidFactoryWait(unittest.TestCase):
    """The shipped droid manifest, its rendered copy, and the client reader."""

    def setUp(self) -> None:
        self.render = load("render-skills")
        self.acp = load("kaola-acp")

    def test_factory_manifests_declare_60(self) -> None:
        self.assertEqual(declared_values(PLATFORMS / "droid.yaml"), ["60"])
        self.assertEqual(declared_values(RENDERED_MANIFEST), ["60"])
        source = (PLATFORMS / "droid.yaml").read_text(encoding="utf-8").splitlines()
        keys = [line.split(":", 1)[0] for line in source if line.startswith("acp_")]
        self.assertLess(keys.index("acp_init_meta"), keys.index("acp_session_new_timeout"))
        self.assertLess(keys.index("acp_session_new_timeout"), keys.index("acp_mode_config_id"))

    def test_session_new_timeout_and_other_platforms(self) -> None:
        self.assertEqual(self.acp.SESSION_NEW_TIMEOUT, DEFAULT_WAIT_S)
        for path in sorted(PLATFORMS.glob("*.yaml")):
            manifest = self.render.parse_manifest(path)
            args = Args()
            args.manifest = manifest
            got = self.acp.session_new_timeout(args)
            with self.subTest(platform=path.stem):
                if path.stem in {"droid", "codex"}:
                    self.assertEqual(got, DECLARED_WAIT_S)
                    self.assertEqual(manifest.get("acp_session_new_timeout"), "60")
                else:
                    self.assertEqual(got, DEFAULT_WAIT_S)
                    self.assertNotIn("acp_session_new_timeout", manifest)


class TestScaledHolderWait(unittest.TestCase):
    """A 24 s session/new, scaled like test-issue-146, against 15 s and 60 s."""

    def probe(self, wait: float) -> dict[str, Any]:
        tmp = tempfile.TemporaryDirectory(prefix="kaola-i352-probe-")
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        result = subprocess.run(
            [sys.executable, str(HOLDER), "--probe", "--repo", str(repo),
             "--platform", "droid",
             "--command", f"{sys.executable} {MOCK} --scenario normal",
             "--session-new-timeout", str(wait)],
            capture_output=True, text=True, timeout=30,
            env=hermetic_env(**{DELAY_ENV: str(SCALED_DELAY_MS)}),
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"holder probe rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}")

    def test_scaled_default_returns_acp_session_timeout(self) -> None:
        self.assertEqual(SCALED_DELAY_MS, 2400)
        self.assertEqual(SCALED_DEFAULT_S, 1.5)
        probe = self.probe(SCALED_DEFAULT_S)
        self.assertEqual((probe.get("error") or {}).get("code"), "acp-session-timeout", probe)

    def test_scaled_declared_wait_admits_the_same_answer(self) -> None:
        self.assertGreater(SCALED_DECLARED_S, SCALED_DELAY_MS / 1000)
        probe = self.probe(SCALED_DECLARED_S)
        self.assertNotIn("error", probe, probe)
        self.assertTrue(probe.get("session_probe"), probe)


class TestStartPassesFactoryWait(unittest.TestCase):
    """start of the rendered droid skill passes --session-new-timeout 60."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i352-start-")
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name).resolve()
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.record_root = root / "records"
        self.home = root / "home"
        self.home.mkdir()
        self.skill = root / "skill"
        shutil.copytree(DROID_SKILL, self.skill)
        shim = root / "droid-fixture"
        shim.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "${1:-}" == --version ]]; then printf "droid 0.220.0\\n"; exit 0; fi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        self.shim = shim
        self.session = f"i352-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self.addCleanup(self.stop)

    def stop(self) -> None:
        subprocess.run(
            [sys.executable, str(self.skill / "scripts" / "kaola-acp.py"), "droid", "stop",
             "--repo", str(self.repo), "--session", self.session, "--force"],
            capture_output=True, text=True, timeout=30,
            env=hermetic_env(KAOLA_ACP_RECORD_ROOT=str(self.record_root), HOME=str(self.home),
                             DROID_BIN=str(self.shim)),
        )

    def test_start_argv_carries_60(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.skill / "scripts" / "kaola-acp.py"), "droid", "start",
             "--repo", str(self.repo), "--session", self.session,
             "--command", f"{sys.executable} {FAKE_DROID}"],
            capture_output=True, text=True, timeout=45,
            env=hermetic_env(KAOLA_ACP_RECORD_ROOT=str(self.record_root), HOME=str(self.home),
                             DROID_BIN=str(self.shim)),
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"start rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}")
        self.assertNotIn("error", receipt, receipt)
        self.assertEqual(receipt.get("state"), "ready", receipt)
        pid = receipt.get("holder_pid")
        self.assertIsInstance(pid, int, receipt)
        command = subprocess.run(
            ["ps", "-ww", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertIn("--session-new-timeout 60.0", command.stdout, command.stdout)


if __name__ == "__main__":
    unittest.main()
