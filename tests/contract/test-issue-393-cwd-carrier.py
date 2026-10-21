#!/usr/bin/env python3
"""Issue #393: a worker's cwd-repair notice never becomes the Host carrier.

The reported route: a dsh worker's tool shell cwd is a linked worktree; the
Host removes that worktree with ``git worktree remove``; the worker holder
detects the vanished path, stages a holder-owned ``cwd_repaired`` event, and
delivers it as one self prompt. On v0.9.23 that self prompt must be the compact
``kaola-worker-notify/1`` line for a worker/Expert/Sideagent holder, and only a
``host`` holder may receive the full ``kaola-host-notify/1`` carrier with the
heartbeat body and the one-pass Project Runner instruction.

The suite pins the whole route, not only the payload selector:

* a real dsh worker start, a real linked worktree removed out of band, and the
  holder's own self prompt read from the mock agent's prompt log (compact);
* the same route after a resume-preserved start and after ``drain-restart``;
* a directly spawned holder carrying the legacy ``--host-entry`` with a
  worker role (compact) and with no role (compact), plus the Host control
  (carrier);
* the recorded role/entry evidence that decides the carrier.

No platform binary or credential is used: the mock ACP agent is the seat.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PLATFORM = "dsh"
HOST_ENTRY = "/kaola-project-runner"
TURN_MS = 6000
ONE_PASS = "Perform exactly one full Project Runner heartbeat pass"


def mock_command(log: Path, turn_ms: int = TURN_MS, caps: str = "",
                 resume_any: bool = False) -> str:
    parts = [sys.executable, str(MOCK), "--scenario", "slow",
             "--steering", "injected", "--turn-ms", str(turn_ms),
             "--log", str(log)]
    if caps:
        parts += ["--caps", caps]
    if resume_any:
        parts += ["--resume-any"]
    return " ".join(shlex.quote(part) for part in parts)


class DirectHolder:
    """One real holder process on the mock agent, with exact argv facts."""

    def __init__(self, root: Path, repo: Path, *, session: str, role: str,
                 entry: str) -> None:
        self.root = root
        self.repo = repo
        self.session = session
        self.record_dir = root / "records" / PLATFORM / session / ("a" * 16)
        self.record_dir.mkdir(parents=True)
        self.socket_path = root / f"{session}.sock"
        self.log = root / f"{session}.jsonl"
        self.proc: subprocess.Popen | None = None
        argv = [
            sys.executable, str(HOLDER),
            "--record-dir", str(self.record_dir),
            "--socket", str(self.socket_path),
            "--repo", str(repo),
            "--platform", PLATFORM,
            "--session", session,
            "--command", mock_command(self.log),
            "--host-entry", entry,
            "--host-name", "dsh",
            "--shell-cwd-persistence", "persistent",
            "--steer-method", "_session/steering",
            "--native-steering", "supported",
            "--session-role", role,
            "--accepted-revision", "",
        ]
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, env=env)

    def request(self, op: str, params: dict, timeout: float = 30) -> dict:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.settimeout(timeout)
            connection.connect(str(self.socket_path))
            connection.sendall((json.dumps({"op": op, "request_id": "i393",
                                            "params": params}) + "\n").encode())
            buffer = b""
            while b"\n" not in buffer:
                data = connection.recv(65536)
                if not data:
                    break
                buffer += data
            return json.loads(buffer.split(b"\n")[0])
        finally:
            connection.close()

    def record(self) -> dict:
        return json.loads((self.record_dir / "record.json").read_text(encoding="utf-8"))

    def events(self) -> list[dict]:
        path = self.record_dir / "events.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def prompts(self) -> list[str]:
        if not self.log.is_file():
            return []
        return [event["text"] for event in
                (json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()
                 if line.strip())
                if event.get("event") == "prompt"]

    def stop(self) -> None:
        try:
            self.request("stop", {"force": True}, timeout=30)
        except (OSError, ValueError):
            pass
        if self.proc is not None:
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)


class CwdCarrierRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i393-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        subprocess.run(["git", "-C", str(cls.repo), "config", "user.email", "t@e.invalid"],
                       check=True)
        subprocess.run(["git", "-C", str(cls.repo), "config", "user.name", "t"], check=True)
        (cls.repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(cls.repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(cls.repo), "commit", "-qm", "base"], check=True)
        cls.repo_real = Path(os.path.realpath(cls.repo))
        cls.fixture = cls.root / "fixture"
        shutil.copytree(PROJECT / "scripts", cls.fixture / "scripts")
        shutil.copytree(PROJECT / "platforms", cls.fixture / "platforms")
        manifest = cls.fixture / "platforms" / f"{PLATFORM}.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8")
            + 'shell_cwd_persistence: "persistent"\n',
            encoding="utf-8")
        cls.cli_path = cls.fixture / "scripts" / "kaola-acp.py"
        cls.record_root = cls.root / "records"
        cls._serial = 393
        cls._holders: list[DirectHolder] = []

    @classmethod
    def tearDownClass(cls) -> None:
        for holder in cls._holders:
            holder.stop()
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"s-i393-{self._testMethodName.lower().replace('_', '-')}"[:79]
        self.log = self.root / f"{self.session}.mock.jsonl"
        self.log.unlink(missing_ok=True)
        self._started = False
        self._worktrees: list[tuple[Path, str]] = []

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=30)
        for path, branch in list(self._worktrees):
            subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force",
                            str(path)], capture_output=True)
            subprocess.run(["git", "-C", str(self.repo), "branch", "-D", branch],
                           capture_output=True)
        self._worktrees.clear()

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        return env

    def cli(self, command: str, *args: str, caps: str = "",
            resume_any: bool = False, check: bool = True,
            timeout: float = 90) -> dict:
        argv = [sys.executable, str(self.cli_path), PLATFORM, command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", mock_command(self.log, caps=caps, resume_any=resume_any),
                *args]
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(), timeout=timeout)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command} emitted no JSON: rc={result.returncode} "
                      f"stdout={result.stdout!r} stderr={result.stderr!r}")
        if check and ("error" in receipt or receipt.get("result") == "refused"):
            self.fail(f"{command} failed: {receipt}")
        return receipt

    def start(self, *args: str, caps: str = "", resume_any: bool = False) -> dict:
        receipt = self.cli("start", *args, caps=caps, resume_any=resume_any)
        self._started = True
        return receipt

    def send(self) -> dict:
        return self.cli("send", "--no-wait", "--text", "go")

    def status(self) -> dict:
        return self.cli("status", check=False)

    def record_dir(self) -> Path:
        digest = hashlib.sha256(str(self.repo_real).encode()).hexdigest()[:16]
        return self.record_root / PLATFORM / self.session / digest

    def record(self) -> dict:
        path = self.record_dir() / "record.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def events(self) -> list[dict]:
        path = self.record_dir() / "events.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def mock_prompts(self) -> list[str]:
        if not self.log.is_file():
            return []
        return [event["text"] for event in
                (json.loads(line) for line in
                 self.log.read_text(encoding="utf-8").splitlines() if line.strip())
                if event.get("event") == "prompt"]

    def wait_for(self, check, what: str, timeout: float = 60) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if check():
                return
            time.sleep(0.2)
        self.fail(f"timed out waiting for {what}")

    def add_worktree(self) -> Path:
        serial = self.__class__._serial
        self.__class__._serial += 1
        name = f"issue-393-{serial}"
        path = self.repo / ".kw" / "worktrees" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(["git", "-C", str(self.repo), "worktree", "add", str(path),
                               "-b", f"workflow/{name}"],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self._worktrees.append((path, f"workflow/{name}"))
        return path

    def remove_worktree(self, path: Path) -> None:
        removed = subprocess.run(["git", "-C", str(self.repo), "worktree", "remove",
                                  str(path)], capture_output=True, text=True)
        self.assertEqual(removed.returncode, 0, removed.stderr)

    def wait_notice(self, path: Path) -> None:
        self.wait_for(lambda: path.is_dir(), "the repaired placeholder")
        self.wait_for(lambda: any(event.get("kind") == "tool_cwd_notice_delivered"
                                  for event in self.events()),
                      "the cwd notice to be delivered", timeout=90)

    def wait_self_prompt(self, count: int = 2, timeout: float = 90) -> str:
        self.wait_for(lambda: len(self.mock_prompts()) >= count, "the self prompt",
                      timeout=timeout)
        return self.mock_prompts()[count - 1]

    def assert_compact(self, text: str) -> None:
        first = text.splitlines()[0]
        self.assertTrue(first.startswith("kaola-worker-notify/1:"), first)
        self.assertIn(f"{PLATFORM} session", first)
        self.assertIn('"kind": "cwd_repaired"', text)
        self.assertNotIn("kaola-host-notify/1", text)
        self.assertNotIn("<<<heartbeat-prompt", text)
        self.assertNotIn(ONE_PASS, text)
        self.assertNotIn(HOST_ENTRY, text)

    def assert_carrier(self, text: str) -> None:
        lines = text.splitlines()
        self.assertEqual(lines[0], HOST_ENTRY)
        self.assertEqual(lines[1],
                         f"kaola-host-notify/1: event-driven heartbeat carrier "
                         f"(dsh Host)")
        self.assertIn("<<<heartbeat-prompt", text)
        self.assertIn(ONE_PASS, text)
        self.assertIn('"kind": "cwd_repaired"', text)
        self.assertNotIn("kaola-worker-notify/1", text)

    # -- the reported route on the CLI start seam ---------------------------

    def test_worker_start_cwd_repair_self_prompt_is_compact(self) -> None:
        self.start("--tier", "default")
        record = self.record()
        self.assertEqual(record.get("session_role"), "worker", record)
        self.assertEqual(record.get("host_skill_entry"), "", record)

        path = self.add_worktree()
        self.send()
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the worker turn")
        self.remove_worktree(path)
        self.wait_notice(path)
        self.assert_compact(self.wait_self_prompt())

    def test_resume_preserved_worker_keeps_role_and_compacts(self) -> None:
        self.start("--tier", "default")
        acp_id = self.status().get("acp_session_id")
        self.assertTrue(acp_id, self.status())
        self.cli("stop", "--force")
        self._started = False

        self.start("--resume", str(acp_id), caps="resume,load", resume_any=True)
        record = self.record()
        self.assertEqual(record.get("session_role"), "worker", record)
        self.assertEqual(record.get("host_skill_entry"), "", record)

        path = self.add_worktree()
        self.send()
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the resumed worker turn")
        self.remove_worktree(path)
        self.wait_notice(path)
        self.assert_compact(self.wait_self_prompt())

    def test_drain_restart_worker_keeps_role_and_compacts(self) -> None:
        self.start("--tier", "default")
        acp_id = self.status().get("acp_session_id")
        self.assertTrue(acp_id, self.status())
        self.cli("drain-restart", "--resume", str(acp_id),
                 caps="resume,load", resume_any=True)
        self._started = True
        record = self.record()
        self.assertEqual(record.get("session_role"), "worker", record)
        self.assertEqual(record.get("host_skill_entry"), "", record)

        path = self.add_worktree()
        self.send()
        self.wait_for(lambda: self.status().get("turn_active") is True,
                      "the drained worker turn")
        self.remove_worktree(path)
        self.wait_notice(path)
        self.assert_compact(self.wait_self_prompt())

    # -- the legacy direct-holder argv --------------------------------------

    def direct(self, role: str, entry: str = HOST_ENTRY) -> DirectHolder:
        # The direct socket path is not shortened by the CLI, so the session
        # stays short enough for a macOS AF_UNIX path.
        serial = self.__class__._serial
        self.__class__._serial += 1
        holder = DirectHolder(self.root, self.repo, session=f"d393-{serial}",
                              role=role, entry=entry)
        self.__class__._holders.append(holder)
        return holder

    def run_direct_case(self, role: str, entry: str = HOST_ENTRY) -> tuple[dict, str]:
        path = self.add_worktree()
        holder = self.direct(role, entry)
        self.wait_for(lambda: (holder.record_dir / "record.json").is_file()
                      and holder.record().get("state") == "ready", "the direct holder")
        receipt = holder.request("prompt", {"text": "go", "wait": False})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        self.wait_for(lambda: holder.request("state", {}).get("turn_active") is True,
                      "the direct holder turn")
        self.remove_worktree(path)
        self.wait_for(lambda: path.is_dir(), "the direct-holder placeholder")
        self.wait_for(lambda: any(event.get("kind") == "tool_cwd_notice_delivered"
                                  for event in holder.events()),
                      "the direct-holder notice", timeout=90)
        self.wait_for(lambda: len(holder.prompts()) >= 2, "the direct-holder self prompt")
        holder.stop()
        return holder.record(), holder.prompts()[1]

    def test_direct_worker_holder_with_legacy_entry_compacts(self) -> None:
        record, text = self.run_direct_case("worker")
        self.assertEqual(record.get("session_role"), "worker", record)
        self.assertEqual(record.get("host_skill_entry"), HOST_ENTRY, record)
        self.assert_compact(text)

    def test_direct_unknown_role_with_legacy_entry_compacts(self) -> None:
        record, text = self.run_direct_case("")
        self.assertIsNone(record.get("session_role"), record)
        self.assertEqual(record.get("host_skill_entry"), HOST_ENTRY, record)
        self.assert_compact(text)

    def test_direct_host_holder_still_gets_the_carrier(self) -> None:
        record, text = self.run_direct_case("host")
        self.assertEqual(record.get("session_role"), "host", record)
        self.assertEqual(record.get("host_skill_entry"), HOST_ENTRY, record)
        self.assert_carrier(text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
