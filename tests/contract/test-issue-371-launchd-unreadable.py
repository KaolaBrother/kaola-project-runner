#!/usr/bin/env python3
"""Issue #371: an unreadable service manager is not an exited job.

Model-free. On macOS the confined cases run the broker inside ``sandbox-exec``,
where ``launchctl list`` exits nonzero for any profile, against a session name
that was never started; the unsandboxed cases use real launchd jobs this suite
boots out. No install, no login, no live session.
"""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BROKER = ROOT / "scripts" / "kaola-launchd-broker.py"
ROUTES = ROOT / "scripts" / "kaola-recovery-routes.py"
PYTHON = sys.executable or shutil.which("python3")
LABEL_PREFIX = "com.kaolabrother.kaola-runner.launch."
FALSE_CLAIMS = ("exited and not owned", "stays loaded")


def label_for(platform: str, session: str, repo: str) -> str:
    digest = hashlib.sha256(f"{platform}\0{session}\0{repo}".encode()).hexdigest()
    return LABEL_PREFIX + digest[:16]


def job_state(label: str) -> str:
    result = subprocess.run(["/bin/launchctl", "list"], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return "unknown"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == label:
            return "running" if parts[0].isdigit() else "exited"
    return "absent"


def wait_until(predicate, timeout: float, detail: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(detail)


def bootout(label: str) -> None:
    subprocess.run(["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{label}"],
                   capture_output=True, text=True, timeout=30)


def bootstrap(label: str, program: list[str], plist_path: Path) -> None:
    bootout(label)
    plist_path.write_bytes(plistlib.dumps({
        "Label": label,
        "ProgramArguments": program,
        "RunAtLoad": True,
        "KeepAlive": False,
    }))
    result = subprocess.run(
        ["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)],
        capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise AssertionError(f"bootstrap failed: {result.stderr or result.stdout}")


class LaunchdUnreadableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="k371."))
        self.home = self.base / "home"
        self.repo = self.base / "repo"
        self.records = self.base / "records"
        self.home.mkdir()
        self.repo.mkdir()
        self.records.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        top = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True).stdout.strip()
        self.repo_path = os.path.realpath(top)
        self.platform = "dsh"
        self.labels: list[str] = []
        self.agents: list[subprocess.Popen] = []

    def tearDown(self) -> None:
        for proc in self.agents:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        for label in self.labels:
            bootout(label)
        shutil.rmtree(self.base, ignore_errors=True)

    # ------------------------------------------------------------------ fixtures
    def session(self) -> str:
        """A name nothing has ever started: no record, no job, no run dir."""
        return f"dsh-K371-never-started-{uuid.uuid4().hex[:8]}"

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "USER": os.environ.get("USER", "tester"),
            "LOGNAME": os.environ.get("LOGNAME", "tester"),
            "LANG": "C",
            "TMPDIR": str(self.base),
            "PYTHONUNBUFFERED": "1",
        }
        base.update(extra)
        return base

    def profile(self) -> str:
        return f'(version 1) (allow default) (deny file-write* (subpath "{self.home}/.dsh"))'

    def run_json(self, argv: list[str], *, sandboxed: bool = False,
                 timeout: float = 60) -> dict:
        if sandboxed:
            argv = ["/usr/bin/sandbox-exec", "-p", self.profile(), *argv]
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(), timeout=timeout)
        lines = (result.stdout or "").strip().splitlines()
        if not lines:
            self.fail(f"no JSON from {argv[-4:]}: rc={result.returncode} {result.stderr[-800:]}")
        try:
            payload = json.loads(lines[-1])
        except ValueError:
            self.fail(f"not JSON: {result.stdout[-800:]} {result.stderr[-400:]}")
        payload["_returncode"] = result.returncode
        return payload

    def broker_argv(self, mode: str, session: str, directory: Path) -> list[str]:
        return [PYTHON, str(BROKER), mode,
                "--platform", self.platform, "--session", session,
                "--repo", self.repo_path, "--record-dir", str(directory),
                "--run-base", str(directory / "launch"), "--backend", "launchd"]

    def record_dir(self, session: str) -> Path:
        directory = self.records / self.platform / session
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write_record(self, directory: Path, session: str, **fields: object) -> None:
        payload = {"platform": self.platform, "session": session,
                   "repo": self.repo_path, "state": "error"}
        payload.update(fields)
        (directory / "record.json").write_text(json.dumps(payload), encoding="utf-8")

    def assert_unknown_refusal(self, payload: dict, session: str) -> str:
        """The confined refusal: honest facts, no stale-job claim, real route."""
        text = json.dumps(payload)
        self.assertEqual(payload.get("reason"), "job-state-unknown", payload)
        self.assertEqual(payload.get("os_state"), "unknown", payload)
        self.assertIs(payload.get("caller_confined"), True, payload)
        self.assertEqual(payload.get("manager_rc"), 1, payload)
        self.assertIsInstance(payload.get("manager_stderr"), str, payload)
        self.assertNotEqual(payload.get("_returncode"), 0, payload)
        self.assertFalse(payload.get("holder_may_exist"), payload)
        for false_claim in FALSE_CLAIMS:
            self.assertNotIn(false_claim, text, payload)
        self.assertIn("could not be read from this process", text)
        self.assertIn("is not evidence of a stale job", text)
        self.assertIn("Do not retry reconcile or start from this same shell", text)
        self.assertIn("unconfined shell", text)
        self.assertIn("os_state absent with reaped false", text)
        self.assertIn("kaola-launchd-broker.py", text)
        self.assertIn("Do not run launchctl or systemctl by hand.", text)
        return text

    # ------------------------------------------------------------------ probes
    @unittest.skipUnless(sys.platform == "darwin", "sandbox-exec contract")
    def test_a_confined_caller_cannot_read_launchd(self) -> None:
        """The probe the whole issue rests on: Seatbelt breaks launchctl list."""
        confined = subprocess.run(
            ["/usr/bin/sandbox-exec", "-p", self.profile(), "/bin/launchctl", "list"],
            capture_output=True, text=True, env=self.env(), timeout=30)
        self.assertNotEqual(confined.returncode, 0, confined.stdout[-400:])
        plain = subprocess.run(["/bin/launchctl", "list"], capture_output=True,
                               text=True, env=self.env(), timeout=30)
        self.assertEqual(plain.returncode, 0, plain.stderr[-400:])

    @unittest.skipUnless(sys.platform == "darwin", "sandbox-exec contract")
    def test_confined_reconcile_refuses_with_facts_and_the_unknown_route(self) -> None:
        session = self.session()
        directory = self.record_dir(session)
        payload = self.run_json(self.broker_argv("reconcile", session, directory),
                                sandboxed=True)
        text = self.assert_unknown_refusal(payload, session)
        # No record exists, so there is nothing to resume: the route names start.
        self.assertIn("Then start.", text)
        self.assertNotIn("start --resume", text)
        # The same command from an unconfined shell proves there was no leftover.
        control = self.run_json(self.broker_argv("reconcile", session, directory))
        self.assertEqual(control.get("result"), "reconciled", control)
        self.assertEqual(control.get("os_state"), "absent", control)
        self.assertIs(control.get("reaped"), False, control)
        self.assertEqual(job_state(label_for(self.platform, session, self.repo_path)),
                         "absent")

    @unittest.skipUnless(sys.platform == "darwin", "sandbox-exec contract")
    def test_confined_reconcile_names_resume_only_with_a_recorded_acp_session_id(self) -> None:
        session = self.session()
        directory = self.record_dir(session)
        self.write_record(directory, session, acp_session_id="sess_371_probe",
                          holder_pid=2 ** 30)
        payload = self.run_json(self.broker_argv("reconcile", session, directory),
                                sandboxed=True)
        text = self.assert_unknown_refusal(payload, session)
        self.assertIn("start --resume sess_371_probe", text)

    @unittest.skipUnless(sys.platform == "darwin", "sandbox-exec contract")
    def test_confined_submit_refuses_with_facts_and_the_unknown_route(self) -> None:
        session = self.session()
        directory = self.record_dir(session)
        argv = self.broker_argv("submit", session, directory)
        argv += ["--log", str(self.base / "submit.log")]
        payload = self.run_json(argv, sandboxed=True)
        text = self.assert_unknown_refusal(payload, session)
        self.assertIn("Then start.", text)
        # A refused submit wrote no attempt artifacts and loaded no job.
        self.assertFalse((directory / "launch").exists(), directory)
        self.assertEqual(job_state(label_for(self.platform, session, self.repo_path)),
                         "absent")

    @unittest.skipUnless(sys.platform == "darwin", "sandbox-exec contract")
    def test_confined_cleanup_refuses_with_facts_and_the_unknown_route(self) -> None:
        session = self.session()
        directory = self.record_dir(session)
        payload = self.run_json(self.broker_argv("cleanup", session, directory),
                                sandboxed=True)
        self.assert_unknown_refusal(payload, session)

    # ------------------------------------------------------------------ unsandboxed
    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_a_real_exited_unowned_job_still_reaps(self) -> None:
        """The exited branch is unchanged: a genuine leftover is still reaped."""
        session = self.session()
        label = label_for(self.platform, session, self.repo_path)
        self.labels.append(label)
        bootstrap(label, ["/usr/bin/true"], self.base / "exited.plist")
        wait_until(lambda: job_state(label) == "exited", 5,
                   f"planted job did not exit: {job_state(label)}")
        directory = self.record_dir(session)
        payload = self.run_json(self.broker_argv("reconcile", session, directory))
        self.assertEqual(payload.get("result"), "reconciled", payload)
        self.assertIs(payload.get("reaped"), True, payload)
        self.assertEqual(payload.get("os_state"), "absent", payload)
        self.assertEqual(job_state(label), "absent")

    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_a_real_exited_job_with_a_live_effect_keeps_the_exited_route(self) -> None:
        """An exited job the session still owns keeps the pre-#371 route text."""
        session = self.session()
        label = label_for(self.platform, session, self.repo_path)
        self.labels.append(label)
        bootstrap(label, ["/usr/bin/true"], self.base / "owned.plist")
        wait_until(lambda: job_state(label) == "exited", 5,
                   f"owned job did not exit: {job_state(label)}")
        agent = subprocess.Popen(["/bin/sleep", "300"])
        self.agents.append(agent)
        directory = self.record_dir(session)
        self.write_record(directory, session, holder_pid=2 ** 30,
                          agent_pid=agent.pid, agent_pgid=agent.pid)
        payload = self.run_json(self.broker_argv("reconcile", session, directory))
        text = json.dumps(payload)
        self.assertEqual(payload.get("reason"), "job-occupied", payload)
        self.assertEqual(payload.get("os_state"), "exited", payload)
        self.assertIn("is exited and not owned by this attempt", text)
        self.assertIn("then retry start --resume", text)
        self.assertNotIn("could not be read from this process", text)
        self.assertEqual(job_state(label), "exited")
        self.assertIsNone(agent.poll())

    # ------------------------------------------------------------------ static
    def test_the_false_claims_are_gone_and_the_table_matches_the_route(self) -> None:
        broker = BROKER.read_text(encoding="utf-8")
        self.assertNotIn("the job stays loaded", broker)
        self.assertIn("def unknown_route", broker)
        self.assertIn("def session_retry_command", broker)
        routes = ROUTES.read_text(encoding="utf-8")
        row = [line for line in routes.splitlines()
               if line.strip().startswith('"job-state-unknown"')]
        self.assertEqual(len(row), 1, row)
        for needle in (
            "Do not retry reconcile or start from the same confined shell",
            "launch_backend_fallback_reason job-state-unknown",
            "without --resume under full access",
            "workspace-write",
            "os_state absent with reaped false",
        ):
            self.assertIn(needle, row[0], needle)
        self.assertNotIn("Read launchctl or systemctl for the label", row[0])


if __name__ == "__main__":
    unittest.main()
