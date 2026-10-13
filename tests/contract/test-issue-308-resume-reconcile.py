#!/usr/bin/env python3
"""Issue #308: stale exited launch jobs, and a late resume success.

Model-free. Launchd cases use the per-user GUI domain and boot the label out
afterwards. Resume-timing cases launch the mock ACP agent directly. No install,
no login, no live session.
"""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shlex
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
CLIENT = ROOT / "scripts" / "kaola-acp.py"
LOCATE = ROOT / "scripts" / "kaola-locate.py"
MOCK = ROOT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable or shutil.which("python3")
LABEL_PREFIX = "com.kaolabrother.kaola-runner.launch."


def label_for(platform: str, session: str, repo: str) -> str:
    digest = hashlib.sha256(f"{platform}\0{session}\0{repo}".encode()).hexdigest()
    return LABEL_PREFIX + digest[:16]


def record_dir(root: Path, platform: str, session: str, repo: str) -> Path:
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    return root / platform / session / digest


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


class ResumeReconcileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="k308."))
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
        self.platform = "codex"
        self.labels: list[str] = []
        self.pids: list[int] = []
        self.agents: list[subprocess.Popen] = []
        self.sessions: list[str] = []

    def tearDown(self) -> None:
        for session in self.sessions:
            self.stop(session)
        for proc in self.agents:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        for pid in self.pids:
            for sig in (15, 9):
                try:
                    os.kill(pid, sig)
                except (ProcessLookupError, PermissionError):
                    break
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
        for label in self.labels:
            bootout(label)
        shutil.rmtree(self.base, ignore_errors=True)

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "USER": os.environ.get("USER", "tester"),
            "LOGNAME": os.environ.get("LOGNAME", "tester"),
            "LANG": "C",
            "TMPDIR": str(self.base),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "KAOLA_LAUNCH_BACKEND": "direct",
            "PYTHONUNBUFFERED": "1",
            "MOCK_ACP_RESUME_ANY": "1",
        }
        base.update(extra)
        return base

    def session(self) -> str:
        name = f"codex-K308-{uuid.uuid4().hex[:8]}"
        self.sessions.append(name)
        return name

    def track_label(self, session: str) -> str:
        label = label_for(self.platform, session, self.repo_path)
        self.labels.append(label)
        return label

    def run_json(self, argv: list[str], env: dict[str, str], timeout: float = 90) -> dict:
        result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)
        lines = (result.stdout or "").strip().splitlines()
        if not lines:
            self.fail(f"no JSON from {argv[1:4]}: {result.stderr[-800:]}")
        try:
            payload = json.loads(lines[-1])
        except ValueError:
            self.fail(f"not JSON: {result.stdout[-800:]} {result.stderr[-400:]}")
        payload["_returncode"] = result.returncode
        return payload

    def start(self, session: str, *, backend: str, resume: str = "sess_k308",
              timeout_env: dict[str, str] | None = None, command: str | None = None
              ) -> dict:
        agent = command or f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"
        argv = [PYTHON, str(CLIENT), self.platform, "start",
                "--repo", self.repo_path, "--session", session,
                "--command", agent, "--resume", resume,
                "--launch-backend", backend]
        return self.run_json(argv, self.env(**(timeout_env or {})), timeout=90)

    def stop(self, session: str) -> dict:
        argv = [PYTHON, str(CLIENT), self.platform, "stop", "--force",
                "--repo", self.repo_path, "--session", session]
        try:
            return self.run_json(argv, self.env(), timeout=40)
        except (subprocess.TimeoutExpired, AssertionError):
            return {}

    def events(self, session: str) -> list[dict]:
        path = record_dir(self.records, self.platform, session, self.repo_path) / "events.jsonl"
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def wrapper(self, delay_ms: int = 0) -> str:
        path = self.base / f"wrap-{uuid.uuid4().hex[:6]}.py"
        path.write_text(
            "import os, sys\n"
            "os.environ['MOCK_ACP_RESUME_ANY'] = '1'\n"
            f"os.environ['MOCK_ACP_RESUME_DELAY_MS'] = '{delay_ms}'\n"
            f"os.execv({PYTHON!r}, [{PYTHON!r}, {str(MOCK)!r}, "
            "'--scenario', 'normal', '--caps', 'resume,load,list,close'])\n",
            encoding="utf-8")
        return shlex.join([PYTHON, str(path)])

    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_stale_exited_job_lets_start_resume_proceed(self) -> None:
        session = self.session()
        label = self.track_label(session)
        bootstrap(label, ["/usr/bin/true"], self.base / "exited.plist")
        wait_until(lambda: job_state(label) == "exited", 5, f"planted job did not exit: {job_state(label)}")
        started = self.start(session, backend="launchd", command=self.wrapper(),
                             timeout_env={"KAOLA_RESUME_TIMEOUT": "5"})
        self.assertNotEqual((started.get("error") or {}).get("code"), "job-occupied", started)
        self.assertEqual(started.get("state"), "ready", started)
        self.assertIsNone(started.get("error"), started)
        self.assertEqual(job_state(label), "absent", started)
        if isinstance(started.get("holder_pid"), int):
            self.pids.append(started["holder_pid"])

    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_live_foreign_job_refuses_with_the_route(self) -> None:
        session = self.session()
        label = self.track_label(session)
        bootstrap(label, ["/bin/sleep", "300"], self.base / "live.plist")
        wait_until(lambda: job_state(label) == "running", 5, "sleep job did not start")
        log = self.base / "holder.log"
        log.write_text("")
        directory = record_dir(self.records, self.platform, session, self.repo_path)
        directory.mkdir(parents=True)
        payload = self.run_json(
            [PYTHON, str(BROKER), "submit",
             "--platform", self.platform, "--session", session, "--repo", self.repo_path,
             "--record-dir", str(directory), "--log", str(log),
             "--run-base", str(self.base / "launch"), "--ready-timeout", "2",
             "--backend", "launchd"],
            self.env(), timeout=30)
        text = json.dumps(payload)
        self.assertEqual(payload.get("reason"), "launch-in-progress", payload)
        self.assertIn("reconcile", text)
        self.assertIn("start --resume", text)
        self.assertIn("Exact-stop", text)
        self.assertIn("Do not run launchctl or systemctl by hand.", text)
        self.assertIn("kaola-launchd-broker.py", text)
        self.assertEqual(job_state(label), "running")

    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_exited_job_with_a_live_agent_is_not_reaped(self) -> None:
        session = self.session()
        label = self.track_label(session)
        bootstrap(label, ["/usr/bin/true"], self.base / "owned.plist")
        wait_until(lambda: job_state(label) == "exited", 5, "owned job did not exit")
        agent = subprocess.Popen(["/bin/sleep", "300"])
        self.agents.append(agent)
        self.pids.append(agent.pid)
        directory = record_dir(self.records, self.platform, session, self.repo_path)
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(json.dumps({
            "platform": self.platform, "session": session, "repo": self.repo_path,
            "holder_pid": 2 ** 30, "agent_pid": agent.pid, "agent_pgid": agent.pid,
            "state": "error",
        }), encoding="utf-8")
        payload = self.run_json(
            [PYTHON, str(BROKER), "reconcile",
             "--platform", self.platform, "--session", session, "--repo", self.repo_path,
             "--record-dir", str(directory), "--run-base", str(directory / "launch"),
             "--backend", "launchd"],
            self.env(), timeout=30)
        self.assertEqual(payload.get("reason"), "job-occupied", payload)
        self.assertIn("reconcile", json.dumps(payload))
        self.assertEqual(job_state(label), "exited")
        self.assertTrue(agent.poll() is None)

    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_exact_stop_reaps_a_stale_exited_job(self) -> None:
        session = self.session()
        label = self.track_label(session)
        bootstrap(label, ["/usr/bin/true"], self.base / "stop.plist")
        wait_until(lambda: job_state(label) == "exited", 5, "stop fixture did not exit")
        stopped = self.stop(session)
        self.assertEqual((stopped.get("broker_job") or {}).get("reaped"), True, stopped)
        self.assertEqual((stopped.get("broker_job") or {}).get("label"), label)
        self.assertEqual(job_state(label), "absent")

    @unittest.skipUnless(sys.platform == "darwin", "launchd contract")
    def test_attest_resume_reaps_and_a_bare_attest_does_not(self) -> None:
        session = self.session()
        label = self.track_label(session)
        bootstrap(label, ["/usr/bin/true"], self.base / "attest.plist")
        wait_until(lambda: job_state(label) == "exited", 5, "attest fixture did not exit")
        bare = self.run_json(
            [PYTHON, str(LOCATE), "receipt", "--intent", "resume", "--worker", "codex"],
            self.env(), timeout=60)
        self.assertNotIn("broker_job", bare)
        self.assertEqual(job_state(label), "exited")
        attested = self.run_json(
            [PYTHON, str(LOCATE), "receipt", "--intent", "resume", "--worker", "codex",
             "--session", session, "--project", self.repo_path],
            self.env(), timeout=60)
        self.assertEqual((attested.get("broker_job") or {}).get("reaped"), True, attested)
        self.assertNotIn("job-occupied", attested.get("reasons") or [])
        self.assertEqual(job_state(label), "absent")

    def test_late_resume_success_is_recorded_ready(self) -> None:
        session = self.session()
        started = self.start(session, backend="direct", timeout_env={
            "KAOLA_RESUME_TIMEOUT": "0.6",
            "MOCK_ACP_RESUME_DELAY_MS": "1500",
        })
        self.assertEqual(started.get("state"), "ready", started)
        self.assertIsNone(started.get("error"), started)
        self.assertNotEqual((started.get("error") or {}).get("code"), "resume-failed")
        kinds = [row.get("kind") for row in self.events(session)]
        self.assertIn("resume_recovered", kinds, kinds)
        if isinstance(started.get("holder_pid"), int):
            self.pids.append(started["holder_pid"])

    def test_resume_inside_the_wait_is_not_a_recovery(self) -> None:
        session = self.session()
        started = self.start(session, backend="direct", timeout_env={
            "KAOLA_RESUME_TIMEOUT": "3",
            "MOCK_ACP_RESUME_DELAY_MS": "500",
        })
        self.assertEqual(started.get("state"), "ready", started)
        self.assertIsNone(started.get("error"), started)
        kinds = [row.get("kind") for row in self.events(session)]
        self.assertNotIn("resume_recovered", kinds, kinds)
        if isinstance(started.get("holder_pid"), int):
            self.pids.append(started["holder_pid"])

    def test_resume_timeout_is_configurable_and_size_aware(self) -> None:
        import argparse
        import importlib.util
        spec = importlib.util.spec_from_file_location("kaola_acp_308", CLIENT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        args = argparse.Namespace(manifest={}, resume="sess", use_continue=False)
        saved = {key: os.environ.get(key) for key in ("KAOLA_RESUME_TIMEOUT", "KAOLA_RESUME_TOKENS")}
        try:
            os.environ.pop("KAOLA_RESUME_TIMEOUT", None)
            os.environ.pop("KAOLA_RESUME_TOKENS", None)
            self.assertEqual(module.resume_wait_seconds(args), 15.0)
            self.assertEqual(module.resume_window_extra(
                argparse.Namespace(manifest={}, resume=None, use_continue=False)), 0.0)
            os.environ["KAOLA_RESUME_TOKENS"] = "960000"
            self.assertEqual(module.resume_wait_seconds(args), 111.0)
            os.environ["KAOLA_RESUME_TIMEOUT"] = "4.5"
            self.assertEqual(module.resume_wait_seconds(args), 4.5)
            os.environ["KAOLA_RESUME_TIMEOUT"] = "nan"
            self.assertEqual(module.resume_wait_seconds(args), 111.0)
            os.environ["KAOLA_RESUME_TIMEOUT"] = "inf"
            self.assertEqual(module.resume_wait_seconds(args), 111.0)
            os.environ["KAOLA_RESUME_TIMEOUT"] = "nope"
            self.assertEqual(module.resume_wait_seconds(args), 111.0)
            os.environ.pop("KAOLA_RESUME_TIMEOUT", None)
            os.environ["KAOLA_RESUME_TOKENS"] = "10000000"
            self.assertEqual(module.resume_wait_seconds(args), 600.0)
            os.environ.pop("KAOLA_RESUME_TOKENS", None)
            resumed = argparse.Namespace(manifest={}, resume="sess", use_continue=False)
            self.assertEqual(module.resume_window_extra(resumed), 20.0)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
