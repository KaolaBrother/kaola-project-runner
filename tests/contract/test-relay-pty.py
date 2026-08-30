#!/usr/bin/env python3
"""Issue #6 managed-relay identity, quiesce, lease, and crash oracles."""

from __future__ import annotations

import importlib.util
import inspect
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
RELAY = PROJECT / "scripts" / "kaola-pane-relay.py"
CLIENT = PROJECT / "scripts" / "kaola-relay-client.py"
RUNTIME = PROJECT / "tests" / "fixtures" / "relay" / "child-process-group.py"


def load_module(path: Path, name: str):
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_pane_id(env: dict[str, str], session: str) -> str:
    result = subprocess.run(
        [env["TMUX_BIN"], "list-panes", "-t", f"={session}", "-F", "#{pane_id}"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    panes = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(panes) != 1:
        raise AssertionError(f"expected one pane for {session}, found {panes}")
    return panes[0]


class RelayPtyTests(unittest.TestCase):
    def test_managed_identity_quiesce_restore_disconnect_and_sigkill(self) -> None:
        self.assertTrue(RUNNER.is_file(), f"missing public Runner at {RUNNER}")
        self.assertTrue(RELAY.is_file(), f"missing managed relay at {RELAY}")
        self.assertTrue(CLIENT.is_file(), f"missing relay client at {CLIENT}")
        client_module = load_module(CLIENT, "issue6_pty_client")
        self.assertIsNotNone(client_module)

        with tempfile.TemporaryDirectory(prefix="kaola-issue6-pty-") as raw_tmp:
            temp = Path(raw_tmp)
            socket_temp = Path(tempfile.mkdtemp(prefix="kpr-issue6-pty-", dir="/tmp"))
            socket_name = f"issue6-pty-{os.getpid()}-{int(time.time() * 1000)}"
            session = f"issue6-relay-{os.getpid()}"
            repo = temp / "repo"
            repo.mkdir()
            self._git(repo, "init", "-q", "-b", "main")
            self._git(repo, "config", "user.name", "Issue 6 Acceptance")
            self._git(repo, "config", "user.email", "issue-6@example.invalid")
            (repo / "README.md").write_text("# fixture\n", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-q", "-m", "fixture")
            claude = repo / ".claude"
            (claude / "commands").mkdir(parents=True)
            (claude / "agents").mkdir()
            (claude / "kaola-workflow" / "scripts").mkdir(parents=True)
            (claude / "commands" / "workflow-next.md").write_text("fixture\n", encoding="utf-8")
            (claude / "commands" / "kaola-workflow-finalize.md").write_text("fixture\n", encoding="utf-8")
            (claude / "agents" / ".kaola-workflow-agent-manifest").write_text("fixture\n", encoding="utf-8")
            (claude / "kaola-workflow" / "scripts" / "kaola-workflow-claim.js").write_text("fixture\n", encoding="utf-8")

            state = temp / "runtime.state"
            grid_neutral = temp / "grid-neutral"
            silent_input = temp / "silent-input"
            input_log = temp / "input.log"
            tmux_bin = temp / "tmux-wrapper"
            tmux_bin.write_text(
                "#!/bin/sh\nexec tmux -L \"$KAOLA_TEST_TMUX_SOCKET\" \"$@\"\n",
                encoding="utf-8",
            )
            tmux_bin.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "TMUX_BIN": str(tmux_bin),
                    "KAOLA_TEST_TMUX_SOCKET": socket_name,
                    "CLAUDE_BIN": str(RUNTIME),
                    "FAKE_RELAY_FIXTURE_STATE": str(state),
                    "FAKE_GRID_NEUTRAL": str(grid_neutral),
                    "FAKE_SILENT_INPUT": str(silent_input),
                    "FAKE_CLAUDE_SUBMIT_LOG": str(input_log),
                    "KAOLA_START_TIMEOUT": "5",
                    "HOME": str(temp / "home"),
                    "TMPDIR": str(socket_temp),
                }
            )
            (temp / "home").mkdir()
            relay_socket: Path | None = None
            try:
                started = self._run(env, "claude-code", "start", "--repo", str(repo), "--session", session)
                self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
                self.assertTrue(self._wait_for(state, "ready"), "managed child did not start")

                first = self._observe(env, repo, session)
                self.assertEqual(first["schema_version"], 2)
                self.assertTrue(first["relay"]["managed"])
                relay = first["relay"]
                self.assertEqual(relay["pid"], first["hard_evidence"]["pane_pid"])
                self.assertTrue(first["hard_evidence"]["relay_process_match"])
                self.assertTrue(relay["child_process_match"])
                self.assertNotEqual(relay["child_pid"], relay["pid"])
                self.assertEqual(relay["child_pgid"], relay["child_pid"])
                self.assertRegex(relay["epoch"], r"^[0-9a-f]{32}$")
                self.assertRegex(relay["child_start_fingerprint"], r"^sha256:[0-9a-f]{64}$")
                child_ps = self._ps_row(relay["child_pid"])
                self.assertEqual(child_ps["ppid"], relay["pid"], child_ps)
                self.assertEqual(child_ps["pgid"], relay["child_pid"], child_ps)
                self.assertTrue(Path(relay["socket_path"]).is_socket())
                relay_socket = Path(relay["socket_path"])
                self.assertEqual(
                    os.path.commonpath((str(relay_socket), str(socket_temp))),
                    str(socket_temp),
                    "relay socket escaped the test-owned TMPDIR",
                )
                self.assertEqual(relay["socket_mode"], "0600")
                self.assertEqual(relay["socket_owner_uid"], os.getuid())
                self.assertTrue(relay["peer_pid_verified"])

                # A grid-neutral escape changes the child output digest and
                # pane revision without changing the rendered frame/cursor/
                # history. This is the transport fact a v1 activity flag loses.
                grid_before = first
                grid_neutral.touch()
                second = self._observe(env, repo, session)
                self.assertNotEqual(second["pane_revision"], grid_before["pane_revision"])
                self.assertNotEqual(second["relay"]["child_output_offset"], grid_before["relay"]["child_output_offset"])
                self.assertNotEqual(second["relay"]["child_output_digest"], grid_before["relay"]["child_output_digest"])
                self.assertEqual(second["raw_current_frame"], grid_before["raw_current_frame"])
                for key in ("cursor_x", "cursor_y", "history_size", "history_bytes"):
                    self.assertEqual(second["hard_evidence"][key], grid_before["hard_evidence"][key], key)

                # Silent input/editor bytes are also a revision even though
                # the raw frame remains unchanged.
                silent_input.touch()
                pane = second["hard_evidence"]["pane_id"]
                subprocess.run(
                    self._tmux(env) + ["send-keys", "-t", pane, "-l", "silent-input"],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                third = self._observe(env, repo, session)
                self.assertNotEqual(third["pane_revision"], second["pane_revision"])
                self.assertGreater(third["relay"]["child_input_offset"], second["relay"]["child_input_offset"])
                self.assertEqual(third["raw_current_frame"], second["raw_current_frame"])

                # A changed visual snapshot is audit evidence, not a refusal.
                correlated = self._run(
                    env,
                    "claude-code",
                    "send",
                    "--repo",
                    str(repo),
                    "--session",
                    session,
                    "--if-snapshot",
                    first["snapshot_id"],
                    "--text",
                    "must-not-send",
                )
                self.assertEqual(correlated.returncode, 0, correlated.stdout + correlated.stderr)
                receipt = json.loads(correlated.stdout)
                self.assertEqual(receipt["result"], "sent", receipt)
                self.assertEqual(receipt["based_on_snapshot"], first["snapshot_id"], receipt)
                self.assertEqual(receipt["action_time_snapshot"], third["snapshot_id"], receipt)
                self.assertIs(receipt["observation_changed"], True, receipt)
                self.assertRegex(receipt["prepared_payload_fingerprint"], r"^sha256:[0-9a-f]{64}$")
                restored = self._observe(env, repo, session)
                self.assertFalse(restored["hard_evidence"]["pane_input_off"])
                self.assertNotEqual(self._ps_row(relay["child_pid"])["state"][0], "T")

                # Drive the relay's public control socket. The helper is
                # called through its required client surface; no private relay
                # class is named by this acceptance test.
                connection = self._connect(client_module, relay, env)
                quiesced = self._call_client(client_module.quiesce, connection, relay)
                self.assertIn(quiesced.get("result"), {"quiesced", "ok"}, quiesced)
                self.assertNotEqual(self._ps_row(relay["pid"])["state"][0], "T")
                self.assertEqual(self._tmux_value(env, session, "#{pane_input_off}"), "1")
                for row in self._group_rows(relay["child_pgid"]):
                    if not row["state"].startswith("Z"):
                        self.assertTrue(row["state"].startswith("T"), row)
                self._close_client(connection)
                self.assertTrue(self._wait_until_child_running(env, session, relay["child_pid"]))
                self.assertEqual(self._tmux_value(env, session, "#{pane_input_off}"), "0")

                # A second quiesce followed by an explicit resume proves the
                # ordinary lease path leaves the relay live and restores only
                # its exact child group.
                connection = self._connect(client_module, relay, env)
                quiesced = self._call_client(client_module.quiesce, connection, relay)
                self.assertIn(quiesced.get("result"), {"quiesced", "ok"}, quiesced)
                resumed = self._call_client(client_module.resume, connection, quiesced)
                self.assertIn(resumed.get("result"), {"resumed", "ok"}, resumed)
                self._close_client(connection)
                self.assertEqual(self._tmux_value(env, session, "#{pane_input_off}"), "0")
                self.assertNotEqual(self._ps_row(relay["child_pid"])["state"][0], "T")

                # A client that quiesces and then remains half-open must not
                # retain the lease forever. The relay's bounded socket read
                # restores both the exact child group and tmux pane input.
                connection = self._connect(client_module, relay, env)
                quiesced = self._call_client(client_module.quiesce, connection, relay)
                self.assertIn(quiesced.get("result"), {"quiesced", "ok"}, quiesced)
                self.assertTrue(
                    self._wait_until_child_running(env, session, relay["child_pid"], attempts=140),
                    "half-open control connection did not restore the child group",
                )
                self._close_client(connection)
                self.assertEqual(self._tmux_value(env, session, "#{pane_input_off}"), "0")

                # SIGKILL is uncatchable. The nested child group must not be
                # left alive on the current macOS host; wait for the pane to
                # disappear and prove both the leader and descendant vanish.
                os.kill(relay["pid"], signal.SIGKILL)
                self.assertTrue(self._wait_for_process_exit(relay["child_pid"], 2.0))
                self.assertTrue(self._wait_for_process_exit_by_pgid(relay["child_pgid"], 2.0))
                self.assertTrue(self._wait_for_session_exit(env, session, 2.0))
            finally:
                subprocess.run(self._tmux(env) + ["kill-session", "-t", f"={session}"], capture_output=True, env=env)
                subprocess.run(["tmux", "-L", socket_name, "kill-server"], capture_output=True, env=env)
                if relay_socket is not None:
                    try:
                        info = relay_socket.lstat()
                        if stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid() and not relay_socket.is_symlink():
                            relay_socket.unlink()
                    except FileNotFoundError:
                        pass
                shutil.rmtree(socket_temp, ignore_errors=True)

    def _observe(self, env: dict[str, str], repo: Path, session: str) -> dict:
        result = self._run(env, "claude-code", "observe", "--repo", str(repo), "--session", session)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def _run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(RUNNER), *args],
            cwd=PROJECT,
            env=env,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)

    @staticmethod
    def _tmux(env: dict[str, str]) -> list[str]:
        return [env["TMUX_BIN"]]

    def _tmux_value(self, env: dict[str, str], session: str, format_string: str) -> str:
        pane_id = resolve_pane_id(env, session)
        result = subprocess.run(
            self._tmux(env) + ["display-message", "-p", "-t", pane_id, format_string],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return result.stdout.strip()

    @staticmethod
    def _ps_row(pid: int) -> dict[str, str | int]:
        result = subprocess.run(
            ["ps", "-o", "pid=,ppid=,pgid=,state=,command=", "-p", str(pid)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise AssertionError(f"process {pid} is absent: {result.stderr}")
        line = result.stdout.strip()
        fields = line.split(None, 4)
        return {"pid": int(fields[0]), "ppid": int(fields[1]), "pgid": int(fields[2]), "state": fields[3], "command": fields[4]}

    def _group_rows(self, pgid: int) -> list[dict[str, str | int]]:
        result = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,state=,command="], capture_output=True, text=True)
        rows: list[dict[str, str | int]] = []
        for line in result.stdout.splitlines():
            fields = line.split(None, 4)
            if len(fields) < 5:
                continue
            try:
                if int(fields[2]) == pgid:
                    rows.append({"pid": int(fields[0]), "ppid": int(fields[1]), "pgid": int(fields[2]), "state": fields[3], "command": fields[4]})
            except ValueError:
                continue
        return rows

    def _connect(self, module, relay: dict, env: dict[str, str]):
        values = {
            "socket_path": relay["socket_path"],
            "socket": relay["socket_path"],
            "relay_epoch": relay["epoch"],
            "epoch": relay["epoch"],
            "expected_child_fingerprint": relay["child_start_fingerprint"],
            "child_fingerprint": relay["child_start_fingerprint"],
            "pane_pid": relay["pid"],
            "relay_pid": relay["pid"],
        }
        return self._invoke_required(module.connect_attested, values, "connect_attested")

    def _call_client(self, function, connection, facts: dict) -> dict:
        values = {
            "client": connection,
            "connection": connection,
            "sock": connection,
            "lease": facts.get("lease_id"),
            "lease_id": facts.get("lease_id"),
            "expected_child_fingerprint": facts.get("child_start_fingerprint"),
            "child_fingerprint": facts.get("child_start_fingerprint"),
            "relay_epoch": facts.get("relay_epoch") or facts.get("epoch"),
            "epoch": facts.get("relay_epoch") or facts.get("epoch"),
        }
        result = self._invoke_required(function, values, getattr(function, "__name__", "client operation"))
        self.assertIsInstance(result, dict, result)
        return result

    def _invoke_required(self, function, values: dict, label: str):
        signature = inspect.signature(function)
        args = []
        kwargs = {}
        for parameter in signature.parameters.values():
            if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                continue
            if parameter.name in values and values[parameter.name] is not None:
                if parameter.kind == parameter.POSITIONAL_ONLY:
                    args.append(values[parameter.name])
                else:
                    kwargs[parameter.name] = values[parameter.name]
            elif parameter.default is parameter.empty:
                self.fail(f"{label} has undocumented required parameter {parameter.name}")
        return function(*args, **kwargs)

    @staticmethod
    def _close_client(connection) -> None:
        for name in ("close", "shutdown"):
            method = getattr(connection, name, None)
            if callable(method):
                try:
                    method()
                except OSError:
                    pass
                return

    @staticmethod
    def _wait_for(path: Path, text: str) -> bool:
        for _ in range(100):
            if path.exists() and text in path.read_text(encoding="utf-8"):
                return True
            time.sleep(0.05)
        return False

    @staticmethod
    def _wait_until_child_running(
        env: dict[str, str], session: str, child_pid: int, attempts: int = 60
    ) -> bool:
        for _ in range(attempts):
            try:
                row = RelayPtyTests._ps_row(child_pid)
                pane_off = RelayPtyTests._tmux_value_static(env, session, "#{pane_input_off}")
                if not row["state"].startswith("T") and pane_off == "0":
                    return True
            except (AssertionError, subprocess.CalledProcessError):
                pass
            time.sleep(0.05)
        return False

    @staticmethod
    def _tmux_value_static(env: dict[str, str], session: str, format_string: str) -> str:
        pane_id = resolve_pane_id(env, session)
        result = subprocess.run(
            [env["TMUX_BIN"], "display-message", "-p", "-t", pane_id, format_string],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return result.stdout.strip()

    @staticmethod
    def _wait_for_process_exit(pid: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = subprocess.run(["ps", "-p", str(pid)], capture_output=True, text=True)
            if result.returncode != 0:
                return True
            time.sleep(0.05)
        return False

    @staticmethod
    def _wait_for_process_exit_by_pgid(pgid: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = subprocess.run(["ps", "-axo", "pgid="], capture_output=True, text=True)
            if str(pgid) not in {line.strip() for line in result.stdout.splitlines()}:
                return True
            time.sleep(0.05)
        return False

    def _wait_for_session_exit(self, env: dict[str, str], session: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = subprocess.run(self._tmux(env) + ["has-session", "-t", f"={session}"], capture_output=True, env=env)
            if result.returncode != 0:
                return True
            time.sleep(0.05)
        return False


if __name__ == "__main__":
    unittest.main(verbosity=2)
