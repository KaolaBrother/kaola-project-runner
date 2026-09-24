#!/usr/bin/env python3
"""Issue #147 contract: the read-only installed-platforms survey.

`kaola-acp survey` answers which platform CLIs are installed on this host,
resolved through the login environment as well as the invoking PATH. It must
start no agent, open no ACP session, create no holder or record, and run no
platform binary. Every fixture here is hermetic: a fake login shell with its
own bin directory, an empty invoking PATH, and a private record root.
"""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
PLATFORMS_DIR = PROJECT / "platforms"
API_DOC = PROJECT / "docs" / "api.md"
ACP_TMPL = PROJECT / "templates" / "references" / "acp.md.tmpl"
ACP_REF = PROJECT / "skills" / "codex-kaola-project-runner" / "references" / "acp.md"
README = PROJECT / "README.md"

PLATFORM_ORDER = [
    "claude-code", "codex", "cursor-cli", "devin", "droid",
    "dsh", "grok", "kimi-cli", "opencode", "zcode",
]
TOP_KEYS = {"schema", "login_env", "platforms"}
LOGIN_KEYS = {"shell", "shell_source", "status", "detail", "path"}
ROW_KEYS = {
    "platform", "runtime_name", "status", "installed", "path", "source",
    "binary", "binary_env", "requires_env", "process_path", "login_path",
}
STATUSES = {"present", "absent", "unknown"}
SOURCES = {None, "binary_env", "process_path", "login_binary_env", "login_path",
           "process_env", "login_env"}


def write_exec(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def load_cli_module():
    spec = importlib.util.spec_from_file_location("kaola_acp_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def manifest(platform: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (PLATFORMS_DIR / f"{platform}.yaml").read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        if key.strip() and value.strip():
            result[key.strip()] = json.loads(value.strip())
    return result


class InstalledSurveyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-147-")
        root = Path(self.tmp.name)
        self.markers = root / "markers"
        self.markers.mkdir()
        self.login_bin = root / "login-bin"
        self.login_bin.mkdir()
        self.process_bin = root / "process-bin"
        self.process_bin.mkdir()
        self.record_root = root / "records"
        self.login_exports = ""
        # Every fake binary, including tmux/npx/node, records that it ran.
        for name in ("codex", "opencode", "tmux", "npx", "node"):
            write_exec(self.login_bin / name,
                       f"#!/bin/sh\n: > '{self.markers}/{name}-ran'\nexit 0\n")
        self.login_shell = root / "fake-login-shell"
        self.write_login_shell()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_login_shell(self) -> None:
        # A login shell that prints profile noise first, then runs the
        # survey's command with its own login PATH (argv: -l -c COMMAND).
        write_exec(self.login_shell, (
            "#!/bin/sh\n"
            f": > '{self.markers}/login-shell-ran'\n"
            '[ "$1" = "-l" ] && [ "$2" = "-c" ] || exit 64\n'
            "echo 'profile banner noise'\n"
            f"export PATH='{self.login_bin}:/usr/bin:/bin'\n"
            f"{self.login_exports}"
            'exec /bin/sh -c "$3"\n'
        ))

    def env(self, **extra: str) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_") and not key.endswith("_BIN")}
        env["PATH"] = str(self.process_bin)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env.update(extra)
        return env

    def survey(self, *args: str, env: dict[str, str] | None = None) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "survey", "--login-shell", str(self.login_shell), *args],
            capture_output=True, text=True, timeout=60, env=env or self.env(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsInstance(payload, dict)
        return payload

    def rows(self, payload: dict) -> dict[str, dict]:
        return {row["platform"]: row for row in payload["platforms"]}

    def live_list(self) -> list:
        result = subprocess.run(
            [sys.executable, str(CLI), "list", "--record-root", str(self.record_root),
             "--include-dead"],
            capture_output=True, text=True, timeout=60, env=self.env(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["rows"]

    def test_login_path_install_without_sessions_is_present(self) -> None:
        self.assertEqual(self.live_list(), [])
        payload = self.survey()
        self.assertEqual(payload["login_env"]["status"], "ok")
        self.assertEqual(payload["login_env"]["shell_source"], "argument")
        rows = self.rows(payload)
        for platform, binary in (("codex", "codex"), ("opencode", "opencode")):
            row = rows[platform]
            self.assertEqual(row["status"], "present", row)
            self.assertIs(row["installed"], True)
            self.assertEqual(row["source"], "login_path")
            self.assertEqual(row["path"], str(self.login_bin / binary))
            self.assertEqual(row["login_path"], str(self.login_bin / binary))
            self.assertIsNone(row["process_path"])
        self.assertEqual(self.live_list(), [])

    def test_uninstalled_cli_is_absent(self) -> None:
        rows = self.rows(self.survey())
        for platform in ("claude-code", "cursor-cli", "devin", "droid", "dsh", "grok",
                         "kimi-cli", "zcode"):
            row = rows[platform]
            self.assertEqual(row["status"], "absent", row)
            self.assertIs(row["installed"], False)
            self.assertIsNone(row["path"])
            self.assertIsNone(row["source"])
        # Removing the one install flips that row honestly, nothing else.
        (self.login_bin / "codex").unlink()
        rows = self.rows(self.survey())
        self.assertEqual(rows["codex"]["status"], "absent")
        self.assertIsNone(rows["codex"]["login_path"])
        self.assertEqual(rows["opencode"]["status"], "present")

    def test_survey_starts_nothing_and_runs_no_platform_binary(self) -> None:
        write_exec(self.process_bin / "claude",
                   f"#!/bin/sh\n: > '{self.markers}/claude-ran'\n")
        before = self.live_list()
        payload = self.survey()
        self.assertEqual(self.rows(payload)["claude-code"]["source"], "process_path")
        self.assertEqual(before, [])
        self.assertEqual(self.live_list(), [])
        # No record root, no holder socket, no session record came into being.
        self.assertFalse(self.record_root.exists())
        # The login shell ran; no platform binary, tmux, npx, or node did.
        self.assertEqual(sorted(p.name for p in self.markers.iterdir()), ["login-shell-ran"])

    def test_output_shape_is_stable(self) -> None:
        payload = self.survey()
        self.assertEqual(set(payload), TOP_KEYS)
        self.assertEqual(payload["schema"], "kaola-acp-survey/1")
        self.assertEqual(set(payload["login_env"]), LOGIN_KEYS)
        self.assertEqual([row["platform"] for row in payload["platforms"]], PLATFORM_ORDER)
        for row in payload["platforms"]:
            self.assertEqual(set(row), ROW_KEYS, row["platform"])
            self.assertIn(row["status"], STATUSES)
            self.assertIs(row["installed"], row["status"] == "present")
            self.assertIn(row["source"], SOURCES)
            self.assertIsInstance(row["requires_env"], list)
            self.assertIsInstance(row["runtime_name"], str)
        zcode = self.rows(payload)["zcode"]
        self.assertEqual(zcode["requires_env"], ["KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE"])
        self.assertIsNone(zcode["binary"])
        filtered = self.survey("--platform", "opencode")
        self.assertEqual(set(filtered), TOP_KEYS)
        self.assertEqual([row["platform"] for row in filtered["platforms"]], ["opencode"])

    def test_unreachable_login_env_is_unknown_not_absent(self) -> None:
        write_exec(self.process_bin / "grok", "#!/bin/sh\nexit 0\n")
        result = subprocess.run(
            [sys.executable, str(CLI), "survey", "--login-shell",
             str(Path(self.tmp.name) / "no-such-shell")],
            capture_output=True, text=True, timeout=60, env=self.env(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["login_env"]["status"], "unavailable")
        self.assertIsNone(payload["login_env"]["path"])
        self.assertTrue(payload["login_env"]["detail"])
        rows = self.rows(payload)
        self.assertEqual(rows["grok"]["status"], "present")
        self.assertEqual(rows["codex"]["status"], "unknown")
        self.assertIs(rows["codex"]["installed"], False)

    def test_hung_login_shell_is_bounded(self) -> None:
        # The shell hangs and a detached child outside its process group keeps
        # stdout open; the survey still returns, reporting the login env
        # unavailable instead of waiting on either.
        pid_file = Path(self.tmp.name) / "daemon.pid"
        hung = write_exec(Path(self.tmp.name) / "hung-shell", (
            "#!/bin/sh\n"
            f"'{sys.executable}' -c 'import os,time; os.setsid(); "
            f"open(\"{pid_file}\",\"w\").write(str(os.getpid())); time.sleep(30)' &\n"
            "sleep 30\n"
        ))
        module = load_cli_module()
        module.SURVEY_LOGIN_TIMEOUT = 0.5
        started = time.monotonic()
        try:
            fact, login = module.survey_login_env(str(hung), "argument")
        finally:
            if pid_file.exists():
                try:
                    os.kill(int(pid_file.read_text()), signal.SIGKILL)
                except (OSError, ValueError):
                    pass
        self.assertLess(time.monotonic() - started, 10.0)
        self.assertIsNone(login)
        self.assertEqual(fact["status"], "unavailable")
        self.assertIn("did not answer", fact["detail"])

    def test_binary_env_overrides_win_in_launch_order(self) -> None:
        override = write_exec(Path(self.tmp.name) / "my-codex", "#!/bin/sh\nexit 0\n")
        row = self.rows(self.survey(env=self.env(CODEX_BIN=str(override))))["codex"]
        self.assertEqual((row["source"], row["path"]), ("binary_env", str(override)))
        self.login_exports = f"export OPENCODE_BIN='{override}'\n"
        self.write_login_shell()
        row = self.rows(self.survey())["opencode"]
        self.assertEqual((row["source"], row["path"]), ("login_binary_env", str(override)))

    def test_zcode_needs_both_explicit_paths(self) -> None:
        entry = Path(self.tmp.name) / "zcode.cjs"
        entry.write_text("", encoding="utf-8")
        node = write_exec(Path(self.tmp.name) / "node-rt", "#!/bin/sh\nexit 0\n")
        # A `zcode` on PATH is not a ZCode install for the Runner.
        write_exec(self.login_bin / "zcode", "#!/bin/sh\nexit 0\n")
        self.assertEqual(self.rows(self.survey())["zcode"]["status"], "absent")
        self.login_exports = (f"export KAOLA_ZCODE_ENTRY='{entry}'\n"
                              f"export KAOLA_ZCODE_NODE='{node}'\n")
        self.write_login_shell()
        row = self.rows(self.survey())["zcode"]
        self.assertEqual((row["status"], row["source"], row["path"]),
                         ("present", "login_env", str(entry)))
        row = self.rows(self.survey(env=self.env(KAOLA_ZCODE_ENTRY=str(entry))))["zcode"]
        self.assertEqual(row["source"], "login_env")  # process env lacks the node path

    def test_runtime_table_mirrors_every_manifest(self) -> None:
        module = load_cli_module()
        self.assertEqual(list(module.PLATFORMS), PLATFORM_ORDER)
        self.assertEqual(sorted(module.SURVEY_RUNTIMES), sorted(PLATFORM_ORDER))
        self.assertEqual(sorted(p.stem for p in PLATFORMS_DIR.glob("*.yaml")),
                         sorted(PLATFORM_ORDER))
        for platform in PLATFORM_ORDER:
            facts = manifest(platform)
            self.assertEqual(
                module.SURVEY_RUNTIMES[platform],
                (facts["runtime_name"], facts["binary_name"], facts["binary_env"]),
                platform,
            )

    def test_survey_is_documented_on_the_contract_surfaces(self) -> None:
        api = API_DOC.read_text(encoding="utf-8")
        for phrase in ("kaola-acp survey", "kaola-acp-survey/1", "login_path", "unknown"):
            self.assertIn(phrase, api)
        self.assertIn("kaola-acp survey", README.read_text(encoding="utf-8"), README)
        # Issue #157 (W-A8): the worker reference calls the Skill's own script by
        # absolute path; `kaola-acp` is on PATH only where helper links exist.
        for path in (ACP_TMPL, ACP_REF):
            self.assertIn('"$SKILL_DIR/scripts/kaola-acp.py" survey', path.read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
