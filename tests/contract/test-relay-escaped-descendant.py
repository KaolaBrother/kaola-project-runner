#!/usr/bin/env python3
"""Acceptance oracles for descendants that escape the managed child group."""

from __future__ import annotations

import json
import os
import signal
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT / "scripts" / "kaola-tmux.sh"
RUNTIME = PROJECT / "tests" / "fixtures" / "relay" / "child-process-group.py"


class EscapedDescendantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kaola-issue6-escaped-")
        self.temp = Path(self.temporary.name)
        self.socket_temp = Path(tempfile.mkdtemp(prefix="kpr-issue6-escaped-", dir="/tmp"))
        self.socket_name = f"issue6-escaped-{os.getpid()}-{time.time_ns()}"
        self.session = f"issue6-escaped-{os.getpid()}-{time.time_ns()}"
        self.repo = self.temp / "repo"
        self.repo.mkdir()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Issue 6 Acceptance")
        self._git("config", "user.email", "issue-6@example.invalid")
        (self.repo / "README.md").write_text("# fixture\n", encoding="utf-8")
        self._git("add", "README.md")
        self._git("commit", "-q", "-m", "fixture")

        claude = self.repo / ".claude"
        (claude / "commands").mkdir(parents=True)
        (claude / "agents").mkdir()
        (claude / "kaola-workflow" / "scripts").mkdir(parents=True)
        (claude / "commands" / "workflow-next.md").write_text("fixture\n", encoding="utf-8")
        (claude / "commands" / "kaola-workflow-finalize.md").write_text("fixture\n", encoding="utf-8")
        (claude / "agents" / ".kaola-workflow-agent-manifest").write_text("fixture\n", encoding="utf-8")
        (claude / "kaola-workflow" / "scripts" / "kaola-workflow-claim.js").write_text(
            "fixture\n", encoding="utf-8"
        )

        self.state = self.temp / "runtime.state"
        self.input_log = self.temp / "input.log"
        self.tmux_bin = self.temp / "tmux-wrapper"
        self.tmux_bin.write_text(
            "#!/bin/sh\nexec tmux -L \"$KAOLA_TEST_TMUX_SOCKET\" \"$@\"\n",
            encoding="utf-8",
        )
        self.tmux_bin.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(
            {
                "TMUX_BIN": str(self.tmux_bin),
                "KAOLA_TEST_TMUX_SOCKET": self.socket_name,
                "CLAUDE_BIN": str(RUNTIME),
                "FAKE_RELAY_FIXTURE_STATE": str(self.state),
                "FAKE_CLAUDE_SUBMIT_LOG": str(self.input_log),
                "FAKE_RELAY_ESCAPE_DESCENDANT": "1",
                "FAKE_RELAY_RENDER_EDITOR": "1",
                "KAOLA_START_TIMEOUT": "5",
                "HOME": str(self.temp / "home"),
                "TMPDIR": str(self.socket_temp),
            }
        )
        (self.temp / "home").mkdir()
        self.escaped_pid: int | None = None
        self.escaped_pgid: int | None = None
        self.relay_socket: Path | None = None

        started = self._run("claude-code", "start", "--repo", str(self.repo), "--session", self.session)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertTrue(self._wait_for_state("ready"), "escaped-descendant fixture did not become ready")
        state = self._state_values()
        self.escaped_pid = int(state["descendant_pid"])
        self.escaped_pgid = int(state["descendant_pgid"])
        self.assertEqual(state["descendant_start_new_session"], "true")

        process = self._process_facts(self.escaped_pid)
        self.assertEqual(process["ppid"], int(state["pid"]), process)
        self.assertEqual(process["pgid"], self.escaped_pid, process)
        self.assertFalse(process["state"].startswith(("T", "Z")), process)

    def tearDown(self) -> None:
        subprocess.run(
            [str(self.tmux_bin), "kill-session", "-t", f"={self.session}"],
            capture_output=True,
            env=self.env,
        )
        subprocess.run(["tmux", "-L", self.socket_name, "kill-server"], capture_output=True, env=self.env)
        if self.escaped_pgid is not None:
            try:
                os.killpg(self.escaped_pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._wait_for_exit(self.escaped_pid, 2.0)
        if self.relay_socket is not None:
            try:
                info = self.relay_socket.lstat()
                if stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid() and not self.relay_socket.is_symlink():
                    self.relay_socket.unlink()
            except FileNotFoundError:
                pass
        shutil.rmtree(self.socket_temp, ignore_errors=True)
        self.temporary.cleanup()

    def test_direct_send_does_not_pause_or_gate_on_an_owned_escaped_descendant(self) -> None:
        observed = self._observe()
        tracked = {row["pid"] for row in observed["child_processes"]}
        self.assertIn(self.escaped_pid, tracked, "public snapshot did not track the escaped runtime descendant")
        self.relay_socket = Path(observed["relay"]["socket_path"])
        self.assertEqual(
            os.path.commonpath((str(self.relay_socket), str(self.socket_temp))),
            str(self.socket_temp),
            "relay socket escaped the test-owned TMPDIR",
        )

        result = self._run(
            "claude-code",
            "send",
            "--repo",
            str(self.repo),
            "--session",
            self.session,
            "--if-snapshot",
            observed["snapshot_id"],
            "--text",
            "escaped-descendant-is-evidence",
        )

        receipt = json.loads(result.stdout)
        logged = self.state.read_text(encoding="utf-8")
        payload_hex = "escaped-descendant-is-evidence\r".encode().hex()
        payload_events = [
            line
            for line in logged.splitlines()
            if line.startswith("input_descendant_state=") and line.endswith(f";input={payload_hex}")
        ]
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(receipt.get("result"), "sent", receipt)
        self.assertEqual(len(payload_events), 1, logged)
        state = payload_events[0].split("=", 1)[1].split(";", 1)[0]
        self.assertFalse(
            state.startswith(("T", "Z")),
            f"direct send changed owned descendant runtime state to {state!r}",
        )
        self.assertTrue(self._process_exists(self.escaped_pid))

    def test_force_stop_never_reports_success_before_tracked_escaped_descendant_is_absent(self) -> None:
        observed = self._observe()
        tracked = {row["pid"] for row in observed["child_processes"]}
        self.assertIn(self.escaped_pid, tracked, "public snapshot did not track the escaped runtime descendant")
        self.relay_socket = Path(observed["relay"]["socket_path"])
        self.assertEqual(
            os.path.commonpath((str(self.relay_socket), str(self.socket_temp))),
            str(self.socket_temp),
            "relay socket escaped the test-owned TMPDIR",
        )

        result = self._run(
            "claude-code",
            "stop",
            "--repo",
            str(self.repo),
            "--session",
            self.session,
            "--if-snapshot",
            observed["snapshot_id"],
            "--force",
        )
        receipt = json.loads(result.stdout)
        reports_success = result.returncode == 0 and receipt.get("result") == "stopped"
        if reports_success:
            self.assertTrue(
                self._wait_for_exit(self.escaped_pid, 2.0),
                f"force-stop reported success while tracked escaped descendant {self.escaped_pid} remained alive",
            )

    def _observe(self) -> dict:
        result = self._run("claude-code", "observe", "--repo", str(self.repo), "--session", self.session)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(RUNNER), *arguments],
            cwd=PROJECT,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def _git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.repo), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def _wait_for_state(self, marker: str, timeout: float = 5.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.state.exists() and marker in self.state.read_text(encoding="utf-8"):
                return True
            time.sleep(0.02)
        return False

    def _state_values(self) -> dict[str, str]:
        return dict(
            line.split("=", 1)
            for line in self.state.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )

    @staticmethod
    def _process_facts(pid: int) -> dict[str, int | str]:
        result = subprocess.run(
            ["ps", "-o", "pid=,ppid=,pgid=,state=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=True,
        )
        fields = result.stdout.split()
        if len(fields) != 4:
            raise AssertionError(f"missing process facts for {pid}: {result.stdout!r}")
        return {
            "pid": int(fields[0]),
            "ppid": int(fields[1]),
            "pgid": int(fields[2]),
            "state": fields[3],
        }

    @staticmethod
    def _process_exists(pid: int | None) -> bool:
        if pid is None:
            return False
        result = subprocess.run(["ps", "-o", "state=", "-p", str(pid)], capture_output=True, text=True)
        state = result.stdout.strip()
        return result.returncode == 0 and bool(state) and not state.startswith("Z")

    @classmethod
    def _wait_for_exit(cls, pid: int | None, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not cls._process_exists(pid):
                return True
            time.sleep(0.02)
        return not cls._process_exists(pid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
