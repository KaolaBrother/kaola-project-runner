#!/usr/bin/env python3
"""Issue #363: a resumed dsh session keeps the permission pinned at birth.

dsh writes ``permission/preset``, ``sandbox/mode`` and ``approval/policy``
into the session log when a session is created and keeps those values on
``session/resume``; the launch variable ``DSH_PERMISSION_MODE`` is delivered
to the process but can never change a resumed session's recorded permission.
A ``start --resume`` receipt that reports
``config_application.mode = {applied: true, value: danger-full-access}``
therefore lies: the session's own log is the only honest source. The receipt
must report the request as not applied (``reason: resumed-session-permission``)
and, when the log is readable, the session's effective facts under
``effective``.

The birth pinning is real dsh source behavior
(``PermissionPresetService.pinInitialPermission`` in
``@deepseek-ai/dsh-permission-presets``): a resumed session restores the
recorded knobs and the log's last ``permission/preset`` is the effective
preset. The session-store directory naming (``projectKey``/``encodeSegment``
in ``@deepseek-ai/dsh-session-persistence-jsonl``) is what the Runner mirrors
to find that log; the tests below pin it against directory names observed on
a live install.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
CLI = SCRIPTS / "kaola-acp.py"


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DshSessionStoreNaming(unittest.TestCase):
    """The directory layout the reader must hit, pinned against the real
    ``$DSH_HOME/sessions`` layout on a live dsh install."""

    def setUp(self) -> None:
        self.acp = load("kaola-acp")

    def test_project_key_matches_observed_directories(self) -> None:
        for cwd, key in (
            ("/tmp", "--tmp--"),
            ("/private/tmp/dshchk/repo", "--private-tmp-dshchk-repo--"),
            ("/Users/ylpromax5/Workspace/kaola-project-runner-dev",
             "--Users-ylpromax5-Workspace-kaola-project-runner-dev--"),
            ("/Users/x/a.b-c_d", "--Users-x-a.b-c_d--"),
        ):
            with self.subTest(cwd=cwd):
                self.assertEqual(self.acp.dsh_project_key(cwd), key)

    def test_project_key_collapses_separator_runs_and_escapes(self) -> None:
        self.assertEqual(self.acp.dsh_project_key("/a//b"), "--a-b--")
        self.assertEqual(self.acp.dsh_project_key("C:\\work\\repo"), "--C-work-repo--")
        self.assertEqual(self.acp.dsh_project_key("/t~x"), "--t~007Ex--")
        # Leading separators are stripped; a trailing one is not (the JS
        # strips ``/^-+/`` only). A process cwd never carries one anyway.
        self.assertEqual(self.acp.dsh_project_key("/tmp/"), "--tmp---")

    def test_path_segment_escapes_like_dsh(self) -> None:
        self.assertEqual(self.acp.dsh_path_segment("a-b_c.d"), "a-b_c.d")
        self.assertEqual(self.acp.dsh_path_segment("."), "~002E")
        self.assertEqual(self.acp.dsh_path_segment(".."), "~002E~002E")
        self.assertEqual(self.acp.dsh_path_segment("a/b"), "a~002Fb")


class ResumedSessionModeReceipt(unittest.TestCase):
    """The contract: a confined-born session resumed under the Runner default
    reports the resumed truth, not the launch variable's intent."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i363-")
        self.root = Path(os.path.realpath(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.dsh_home = self.root / "dsh-home"
        self.session = f"dsh-i363-{self._testMethodName[-20:].lower()}-{os.getpid()}"
        self.acp = load("kaola-acp")

    def cli(self, command: str, *args: str, **env: str) -> subprocess.CompletedProcess:
        base = {k: v for k, v in os.environ.items()
                if (not k.startswith("KAOLA_")
                    or (k == "KAOLA_LAUNCH_BACKEND" and v == "direct"))
                and k != "DSH_PERMISSION_MODE"}
        base.update(KAOLA_ACP_RECORD_ROOT=str(self.root / "records"),
                    KAOLA_LAUNCH_BACKEND="direct", MOCK_ACP_RESUME_ANY="1",
                    DSH_HOME=str(self.dsh_home), **env)
        return subprocess.run(
            [sys.executable, str(CLI), "dsh", command, "--repo", str(self.repo),
             "--session", self.session,
             "--command", f"{sys.executable} {MOCK} --caps resume,list,close", *args],
            capture_output=True, text=True, env=base, timeout=60)

    def start(self, *args: str, **env: str) -> dict:
        self.addCleanup(self.cli, "stop", "--force")
        return json.loads(self.cli("start", *args, **env).stdout)

    def write_log(self, session_id: str, events: list[dict],
                  name: str = "session.v4.jsonl") -> Path:
        directory = (self.dsh_home / "sessions"
                     / self.acp.dsh_project_key(str(self.repo))
                     / self.acp.dsh_path_segment(session_id))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text("\n".join(json.dumps(e) for e in events) + "\n",
                        encoding="utf-8")
        return path

    @staticmethod
    def pins(preset: str, sandbox: str, approval: str) -> list[dict]:
        return [
            {"type": "session", "version": 4, "id": "x"},
            {"type": "permission/preset", "seq": 0, "data": {"preset": preset}},
            {"type": "sandbox/mode", "seq": 1, "data": {"mode": sandbox}},
            {"type": "approval/policy", "seq": 2, "data": {"policy": approval}},
        ]

    def test_fresh_start_still_reports_the_env_apply(self) -> None:
        receipt = self.start()
        self.assertEqual(receipt.get("state"), "ready", receipt)
        self.assertEqual(receipt["config_application"]["mode"],
                         {"applied": True, "applied_via": "env",
                          "env": "DSH_PERMISSION_MODE",
                          "value": "danger-full-access", "source": "runner-default"})

    def test_resumed_session_reports_its_recorded_permission(self) -> None:
        """The issue's reproduction: born workspace-write, resumed under the
        runner default — the receipt must show the resumed truth."""
        born = self.start(DSH_PERMISSION_MODE="workspace-write")
        self.assertEqual(born.get("state"), "ready", born)
        session_id = born["acp_session_id"]
        self.write_log(session_id, self.pins("workspace-write", "workspace-write", "ask"))
        self.assertEqual(self.cli("stop", "--force").returncode, 0)
        resumed = json.loads(
            self.cli("start", "--resume", session_id).stdout)
        self.assertEqual(resumed.get("state"), "ready", resumed)
        mode = resumed["config_application"]["mode"]
        self.assertIs(mode["applied"], False, mode)
        self.assertEqual(mode["reason"], "resumed-session-permission")
        self.assertEqual(mode["value"], "danger-full-access")
        self.assertEqual(mode["source"], "runner-default")
        self.assertEqual(mode["env"], "DSH_PERMISSION_MODE")
        self.assertEqual(mode["effective_via"], "session-log")
        self.assertEqual(mode["effective"]["preset"], "workspace-write")
        self.assertEqual(mode["effective"]["sandbox"], "workspace-write")
        self.assertEqual(mode["effective"]["approval"], "ask")

    def test_the_last_preset_event_is_the_effective_one(self) -> None:
        """An in-session preset change appends another event; the latest
        recorded value is what the resumed session keeps."""
        born = self.start(DSH_PERMISSION_MODE="workspace-write")
        session_id = born["acp_session_id"]
        events = self.pins("workspace-write", "workspace-write", "ask")
        events += [
            {"type": "permission/preset", "seq": 40, "data": {"preset": "read-only"}},
            {"type": "sandbox/mode", "seq": 41, "data": {"mode": "read-only"}},
        ]
        self.write_log(session_id, events)
        self.cli("stop", "--force")
        resumed = json.loads(self.cli("start", "--resume", session_id).stdout)
        effective = resumed["config_application"]["mode"]["effective"]
        self.assertEqual(effective["preset"], "read-only")
        self.assertEqual(effective["sandbox"], "read-only")
        self.assertEqual(effective["approval"], "ask")

    def test_an_unreadable_or_absent_log_claims_no_effective_value(self) -> None:
        """No session log is no evidence: applied stays false with the reason,
        and no effective value is invented."""
        born = self.start()
        session_id = born["acp_session_id"]
        self.cli("stop", "--force")
        resumed = json.loads(self.cli("start", "--resume", session_id).stdout)
        self.assertEqual(resumed.get("state"), "ready", resumed)
        mode = resumed["config_application"]["mode"]
        self.assertIs(mode["applied"], False, mode)
        self.assertEqual(mode["reason"], "resumed-session-permission")
        self.assertNotIn("effective", mode)

    def test_a_symlinked_repo_path_still_finds_the_log(self) -> None:
        """dsh records the resolved cwd (on macOS a /tmp birth lands under
        --private-tmp-…), so the reader resolves the repo path before keying
        the session-store directory."""
        link = self.root / "repo-link"
        os.symlink(self.repo, link)
        session_id = "sym-1"
        self.write_log(session_id, self.pins("workspace-write", "workspace-write", "ask"))
        prior = os.environ.get("DSH_HOME")
        os.environ["DSH_HOME"] = str(self.dsh_home)
        self.addCleanup(lambda: os.environ.__setitem__("DSH_HOME", prior)
                        if prior is not None else os.environ.pop("DSH_HOME", None))
        found = self.acp.dsh_session_permission(str(link), session_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["preset"], "workspace-write")
        self.assertEqual(found["approval"], "ask")

    def test_a_full_birth_reports_full_access_on_resume(self) -> None:
        """A session born under the default keeps it; the receipt still names
        the log as the source, never the launch variable."""
        born = self.start()
        session_id = born["acp_session_id"]
        self.write_log(session_id,
                       self.pins("danger-full-access", "danger-full-access", "never"))
        self.cli("stop", "--force")
        resumed = json.loads(self.cli("start", "--resume", session_id).stdout)
        mode = resumed["config_application"]["mode"]
        self.assertIs(mode["applied"], False, mode)
        self.assertEqual(mode["effective"]["preset"], "danger-full-access")
        self.assertEqual(mode["effective"]["approval"], "never")

    @unittest.skipUnless(shutil.which("zstd"), "zstd binary required")
    def test_a_compressed_log_is_read(self) -> None:
        born = self.start(DSH_PERMISSION_MODE="workspace-write")
        session_id = born["acp_session_id"]
        path = self.write_log(session_id,
                              self.pins("workspace-write", "workspace-write", "ask"))
        compressed = path.with_suffix(path.suffix + ".zstd")
        out = subprocess.run(["zstd", "-q", "-f", str(path), "-o", str(compressed)],
                             capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        path.unlink()
        self.cli("stop", "--force")
        resumed = json.loads(self.cli("start", "--resume", session_id).stdout)
        self.assertEqual(resumed["config_application"]["mode"]
                         ["effective"]["preset"], "workspace-write")


if __name__ == "__main__":
    unittest.main()
