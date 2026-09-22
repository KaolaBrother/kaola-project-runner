#!/usr/bin/env python3
"""Issue #26 contract: host-wide list, typed view, cursor reload, local-bin install.

Pins the frozen stdout schemas in docs/acp-watch/list-view.md. Does not cover
follow (#27) or permit double-answer (#25). Live CLI UAT is not claimed here.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
SWEEP = PROJECT / "scripts" / "kaola-acp-sweep.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
INSTALLER = PROJECT / "scripts" / "install-local.sh"
TMUX = PROJECT / "scripts" / "kaola-tmux.sh"
SAMPLE = PROJECT / "tests" / "contract" / "fixtures" / "kaola-acp-view-1.sample.json"
ACP_TMPL = PROJECT / "templates" / "references" / "acp.md.tmpl"
GROK_ACP_REF = PROJECT / "skills" / "grok-kaola-project-runner" / "references" / "acp.md"

LIST_ROW_KEYS = {
    "platform", "session", "repo", "state", "holder_pid", "agent_alive",
    "event_cursor", "mutation_status", "pending_count", "socket_ok", "transport",
}
L0_FORBIDDEN = {"timeline", "thinking_text", "plan", "messages", "tools"}
CONTENT_TYPES = {"text", "diff", "terminal"}
HOLDER_STATES = {
    "starting", "ready", "agent_exited", "stopping", "stopped", "error",
}


def wait_for(predicate, timeout: float, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


def json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def assert_shape(test: unittest.TestCase, sample: Any, actual: Any, path: str) -> None:
    sample_t = json_type_name(sample)
    actual_t = json_type_name(actual)
    if sample is None:
        return
    test.assertEqual(
        actual_t, sample_t,
        f"{path}: expected {sample_t}, got {actual_t} ({actual!r})",
    )
    if isinstance(sample, dict):
        missing = set(sample) - set(actual)
        test.assertFalse(missing, f"{path}: missing keys {sorted(missing)}")
        for key, expected in sample.items():
            assert_shape(test, expected, actual[key], f"{path}.{key}")
        return
    if isinstance(sample, list):
        if not sample:
            return
        test.assertTrue(actual, f"{path}: expected a non-empty array")
        if isinstance(sample[0], dict) and "type" in sample[0]:
            for index, item in enumerate(actual):
                test.assertIsInstance(item, dict, f"{path}[{index}]")
                test.assertIn("type", item, f"{path}[{index}]")
                test.assertIsInstance(item["type"], str, f"{path}[{index}].type")
            return
        if isinstance(sample[0], dict):
            for index, item in enumerate(actual):
                assert_shape(test, sample[0], item, f"{path}[{index}]")


def flag_value(tokens: list[str], flag: str) -> str | None:
    for index in range(len(tokens) - 1):
        if tokens[index] == flag:
            return tokens[index + 1]
    return None


def live_process_table() -> dict[int, tuple[str, str]]:
    """pid -> (state, command) for every process on the host."""
    table = subprocess.run(
        ["ps", "-axo", "pid=,state=,command="], capture_output=True, text=True
    )
    found: dict[int, tuple[str, str]] = {}
    for line in table.stdout.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit():
            found[int(fields[0])] = (fields[1].upper(), fields[2])
    return found


def own_processes(root: Path) -> dict[int, str]:
    """Live processes this suite's temp root still owns.

    Holders are matched by a ``--record-dir``/``--socket`` argv value under
    ``root`` — the exact match ``kaola-acp-sweep.py`` uses. Agents are matched
    through the suite's own ``record.json`` files: the record names the exact
    pids, and a command-name check keeps a reused pid from accusing a foreign
    process. Nothing outside ``root`` is ever reported.
    """
    bases = {str(root), str(root.resolve())}
    table = live_process_table()
    found: dict[int, str] = {}
    for pid, (state, command) in table.items():
        if state.startswith("Z") or "kaola-acp-holder.py" not in command:
            continue
        tokens = command.split()
        values = [
            flag_value(tokens, flag) for flag in ("--record-dir", "--socket")
        ]
        if any(
            value == base or value.startswith(base + os.sep)
            for value in values if value for base in bases
        ):
            found[pid] = command
    records = root / "records"
    if records.is_dir():
        for path in records.glob("*/*/*/record.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for key, marker in (
                ("holder_pid", "kaola-acp-holder.py"),
                ("agent_pid", "mock-acp-agent.py"),
            ):
                pid = record.get(key)
                live = table.get(pid) if isinstance(pid, int) else None
                if live and not live[0].startswith("Z") and marker in live[1]:
                    found[pid] = live[1]
    return found


class AcpWatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for path in (CLI, HOLDER, SWEEP, MOCK, SAMPLE, INSTALLER, TMUX):
            if not path.is_file():
                raise AssertionError(f"missing {path}")
        cls.sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-acp-watch-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.repo = Path(os.path.realpath(cls.repo))
        cls.other_repo = cls.root / "other-repo"
        cls.other_repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.other_repo, check=True)
        cls.other_repo = Path(os.path.realpath(cls.other_repo))
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            if not wait_for(lambda: not own_processes(cls.root), 15):
                raise AssertionError(
                    f"fixture leaked its own processes: {own_processes(cls.root)}"
                )
        finally:
            cls._tmp.cleanup()

    def setUp(self) -> None:
        self._started: list[tuple[str, str, Path]] = []
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        for platform, session, repo in list(self._started):
            self.run_cli(
                platform, "stop", repo=repo, session=session,
                extra=["--force"], check=False, timeout=15,
            )
        self._started.clear()

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        return env

    def mock_command(self, scenario: str = "normal") -> str:
        return " ".join([sys.executable, str(MOCK), "--scenario", scenario])

    def run_raw(self, argv: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout,
        )

    def load_object(self, result: subprocess.CompletedProcess, context: str) -> dict:
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"{context} did not emit one JSON object\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        self.assertIsInstance(payload, dict, f"{context} stdout must be one JSON object")
        return payload

    def run_cli(
        self,
        platform: str,
        command: str,
        *args: str,
        repo: Path | None = None,
        session: str | None = None,
        scenario: str = "normal",
        extra: list[str] | None = None,
        check: bool = True,
        timeout: float = 30,
    ) -> dict:
        target = repo or self.repo
        name = session or f"wch-{platform[:4]}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        argv = [
            sys.executable, str(CLI), platform, command,
            "--repo", str(target), "--session", name,
            "--command", self.mock_command(scenario),
            *(extra or []),
            *args,
        ]
        result = self.run_raw(argv, timeout=timeout)
        receipt = self.load_object(result, f"kaola-acp {platform} {command}")
        if check and "error" in receipt:
            self.fail(f"kaola-acp {platform} {command} error {receipt['error']}\n{receipt}")
        return receipt

    def start(
        self,
        platform: str = "grok",
        repo: Path | None = None,
        session: str | None = None,
        scenario: str = "normal",
    ) -> tuple[str, Path, dict]:
        target = repo or self.repo
        name = session or f"wch-{platform[:4]}-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        receipt = self.run_cli(
            platform, "start", repo=target, session=name, scenario=scenario,
        )
        self._started.append((platform, name, target))
        return name, target, receipt

    def run_list(self, *args: str, check: bool = True) -> dict:
        argv = [sys.executable, str(CLI), "list", *args]
        result = self.run_raw(argv)
        payload = self.load_object(result, "kaola-acp list")
        if check and payload.get("error"):
            self.fail(f"kaola-acp list error {payload['error']}\n{payload}")
        return payload

    def run_view(
        self,
        platform: str,
        session: str,
        repo: Path,
        *args: str,
        check: bool = True,
        timeout: float = 30,
    ) -> dict:
        argv = [
            sys.executable, str(CLI), platform, "view",
            "--repo", str(repo), "--session", session, *args,
        ]
        result = self.run_raw(argv, timeout=timeout)
        payload = self.load_object(result, f"kaola-acp {platform} view")
        if check and payload.get("error"):
            self.fail(f"kaola-acp view error {payload['error']}\n{payload}")
        return payload

    def record_dir(self, platform: str, session: str, repo: Path) -> Path:
        digest = hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:16]
        return self.record_root / platform / session / digest

    def read_mock_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def identity(self, platform: str, session: str, repo: Path):
        return (platform, session, str(repo))

    def test_list_is_host_wide_and_omits_dead_holders(self) -> None:
        grok_session, grok_repo, _ = self.start("grok", repo=self.repo)
        cursor_session, cursor_repo, _ = self.start(
            "cursor-cli", repo=self.other_repo,
        )
        listed = self.run_list()
        self.assertEqual(listed.get("schema"), "kaola-acp-list/1")
        self.assertIsInstance(listed.get("rows"), list)
        rows = listed["rows"]
        self.assertGreaterEqual(len(rows), 2)
        by_id = {
            self.identity(row["platform"], row["session"], Path(row["repo"])): row
            for row in rows
        }
        grok_row = by_id.get(self.identity("grok", grok_session, grok_repo))
        cursor_row = by_id.get(self.identity("cursor-cli", cursor_session, cursor_repo))
        self.assertIsNotNone(grok_row, f"live grok holder missing from list: {rows}")
        self.assertIsNotNone(cursor_row, f"live cursor-cli holder missing from list: {rows}")
        for row in (grok_row, cursor_row):
            missing = LIST_ROW_KEYS - set(row)
            self.assertFalse(missing, f"list row missing {sorted(missing)}")
            self.assertIsInstance(row["holder_pid"], int)
            self.assertIsInstance(row["agent_alive"], bool)
            self.assertIsInstance(row["event_cursor"], int)
            self.assertGreaterEqual(row["event_cursor"], 0)
            self.assertIsInstance(row["pending_count"], int)
            self.assertIsInstance(row["socket_ok"], bool)
            self.assertIsInstance(row["mutation_status"], str)
            self.assertEqual(row["transport"], "acp")
            self.assertIn(row["state"], HOLDER_STATES)

        only_grok = self.run_list("--platform", "grok")
        self.assertTrue(all(row["platform"] == "grok" for row in only_grok["rows"]))
        only_other = self.run_list("--repo", str(self.other_repo))
        self.assertTrue(all(row["repo"] == str(self.other_repo) for row in only_other["rows"]))
        self.assertTrue(
            any(row["session"] == cursor_session for row in only_other["rows"]),
            only_other,
        )

        self.run_cli(
            "cursor-cli", "stop", repo=cursor_repo, session=cursor_session, extra=["--force"],
        )
        self._started = [
            item for item in self._started if item != ("cursor-cli", cursor_session, cursor_repo)
        ]
        after = self.run_list()
        after_ids = {
            self.identity(row["platform"], row["session"], Path(row["repo"]))
            for row in after["rows"]
        }
        self.assertIn(self.identity("grok", grok_session, grok_repo), after_ids)
        self.assertNotIn(
            self.identity("cursor-cli", cursor_session, cursor_repo), after_ids,
        )

    def test_view_matches_sample_key_set_and_types(self) -> None:
        session, repo, _ = self.start("grok", scenario="watch_projection")
        sent = self.run_cli(
            "grok", "send", "--text", "Fix the login redirect loop.", "--no-wait",
            session=session, repo=repo, scenario="watch_projection",
        )
        self.assertIsNone(sent.get("error"))
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "watch_projection_emitted"
                    for event in self.read_mock_log()
                ),
                8,
            ),
            "mock never emitted the watch_projection stream",
        )
        view = self.run_view("grok", session, repo)
        self.assertEqual(view.get("schema"), "kaola-acp-view/1")
        assert_shape(self, self.sample, view, "view")

        roles = {message["role"] for message in view["messages"]}
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)
        assistant = " ".join(
            message["text"] for message in view["messages"] if message["role"] == "assistant"
        )
        self.assertIn("I'll start by", assistant)
        self.assertIn("auth middleware", assistant)
        self.assertEqual(
            sum(1 for message in view["messages"] if message.get("messageId") == "m1"),
            1,
            "same messageId chunks must be joined into one message",
        )

        self.assertIsInstance(view["thinking"]["chars"], int)
        self.assertGreater(view["thinking"]["chars"], 0)
        self.assertIn("cookie", view["thinking"]["text_tail"])

        tools = view["tools"]
        ids = [tool["toolCallId"] for tool in tools]
        self.assertEqual(len(ids), len(set(ids)), "toolCallId must be unique")
        tool = next(item for item in tools if item["toolCallId"] == "call_7")
        self.assertEqual(tool["kind"], "edit")
        self.assertEqual(tool["locations"][0]["path"], "src/auth/middleware.ts")
        kinds = {item["type"] for item in tool["content"]}
        self.assertTrue(kinds <= CONTENT_TYPES)
        self.assertIn("diff", kinds)
        for item in tool["content"]:
            self.assertIn(item["type"], CONTENT_TYPES)
            if item["type"] == "text":
                self.assertIsInstance(item.get("text"), str)
            elif item["type"] == "diff":
                self.assertIsInstance(item.get("path"), str)
                self.assertTrue(item.get("oldText") is None or isinstance(item.get("oldText"), str))
                self.assertIsInstance(item.get("newText"), str)
            elif item["type"] == "terminal":
                self.assertIsInstance(item.get("terminalId"), str)
        diff = next(item for item in tool["content"] if item["type"] == "diff")
        self.assertIn("oldText", diff)
        self.assertIn("newText", diff)
        for message in view["messages"]:
            self.assertTrue(
                message.get("messageId") is None or isinstance(message.get("messageId"), str)
            )
        self.assertTrue(view["commands"] is None or isinstance(view["commands"], list))
        self.assertTrue(
            view["turn"]["outcome"] is None or isinstance(view["turn"]["outcome"], str)
        )

        self.assertIsInstance(view["plan"], dict)
        contents = [entry["content"] for entry in view["plan"]["entries"]]
        self.assertEqual(contents, ["Read middleware", "Patch redirect guard"])
        self.assertNotIn("Stale merged entry", contents)

        pending = view["pending_permissions"]
        self.assertTrue(pending, view)
        options = pending[0]["options"]
        self.assertTrue(options)
        self.assertEqual(set(options[0]), {"optionId", "name", "kind"})
        self.assertEqual(options[0]["optionId"], "allow_once")

        gapped = self.run_view("grok", session, repo, "--since", "0")
        self.assertTrue(gapped["cursor_gap"], gapped)
        self.assertTrue(gapped["truncated"], gapped)

    def test_holder_restart_does_not_reuse_low_cursors(self) -> None:
        session, repo, _ = self.start("grok")
        self.run_cli("grok", "send", "--text", "hello mock", session=session, repo=repo)
        directory = self.record_dir("grok", session, repo)
        live = directory / "events.jsonl"
        self.assertTrue(live.is_file(), f"missing {live}")
        rotated = live.with_suffix(".jsonl.1")
        rotated.write_text(
            json.dumps({"cursor": 800, "kind": "seed-rotated"}) + "\n",
            encoding="utf-8",
        )
        self.run_cli("grok", "stop", session=session, repo=repo, extra=["--force"])
        self._started.clear()

        session, repo, started = self.start("grok", repo=repo, session=session)
        self.run_cli("grok", "send", "--text", "after restart", session=session, repo=repo)
        view = self.run_view("grok", session, repo)
        self.assertGreater(
            view["event_cursor"], 800,
            f"restart ignored rotated jsonl max cursor: {view['event_cursor']}",
        )
        self.assertGreater(started.get("holder_pid") or 0, 0)

    def test_l0_send_wait_keys_stay_orchestrator_shaped(self) -> None:
        session, repo, _ = self.start("grok")
        receipt = self.run_cli(
            "grok", "send", "--text", "hello mock", session=session, repo=repo,
        )
        self.assertEqual(receipt.get("schema_version"), 3)
        forbidden = L0_FORBIDDEN & set(receipt)
        self.assertFalse(forbidden, f"L0 grew human keys {sorted(forbidden)}")
        self.assertNotIn("thinking_text", receipt)
        self.assertIsInstance(receipt.get("thinking_chars"), int)

        session, repo, _ = self.start(
            "cursor-cli", repo=self.other_repo, scenario="watch_projection",
        )
        self.run_cli(
            "cursor-cli", "send", "--text", "gate", "--no-wait",
            repo=self.other_repo, session=session, scenario="watch_projection",
        )
        self.assertTrue(
            wait_for(
                lambda: any(
                    event.get("event") == "watch_projection_emitted"
                    for event in self.read_mock_log()
                ),
                8,
            ),
        )
        observe = self.run_cli(
            "cursor-cli", "observe", repo=self.other_repo, session=session, check=False,
        )
        pending = observe.get("pending_permissions") or []
        self.assertTrue(pending, observe)
        option = (pending[0].get("options") or [None])[0]
        self.assertIsInstance(option, dict)
        self.assertEqual(set(option), {"id", "kind", "label"})

    def test_view_runtime_facts_are_one_json_object(self) -> None:
        missing = self.run_view(
            "grok", f"wch-none-{os.getpid()}", self.repo, check=False,
        )
        self.assertIn("error", missing)
        self.assertEqual(missing["error"].get("code"), "no-session")
        self.assertIn("schema", missing)

        session, repo, started = self.start("grok")
        pid = started.get("holder_pid")
        self.assertIsInstance(pid, int)
        os.kill(pid, signal.SIGKILL)
        wait_for(lambda: not _pid_alive(pid), 5)
        lost = self.run_view("grok", session, repo, check=False)
        self.assertIn("error", lost)
        self.assertEqual(lost["error"].get("code"), "holder-lost")
        self.assertIn("schema", lost)
        self.assertIsInstance(lost["error"].get("message"), str)

    def test_view_accept_then_close_uses_frozen_runtime_code(self) -> None:
        session, repo, started = self.start("grok")
        directory = self.record_dir("grok", session, repo)
        sock = (
            Path(tempfile.gettempdir())
            / f"kaola-{os.getuid()}-acp"
            / f"{hashlib.sha256(str(directory).encode('utf-8')).hexdigest()[:24]}.sock"
        )
        try:
            sock.unlink()
        except FileNotFoundError:
            pass
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(sock))
        listener.listen(1)

        def serve() -> None:
            try:
                connection, _unused = listener.accept()
                connection.close()
            except OSError:
                pass

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            payload = self.run_view("grok", session, repo, check=False)
        finally:
            listener.close()
            thread.join(timeout=2)
            # The stub listener replaced the holder's socket path, so nothing
            # at that path reaches the real holder any more and teardown's
            # stop cannot find it. Sweep this test's exact record dir — the
            # same bounded path an interrupted run uses — which identifies the
            # holder by its own --record-dir argv value, never a bare pid.
            swept = self.run_raw(
                [
                    sys.executable, str(SWEEP), "--root",
                    str(self.record_dir("grok", session, repo)),
                ],
                timeout=40,
            )
        receipt = self.load_object(swept, "kaola-acp-sweep")
        self.assertEqual(
            receipt.get("matched_pids"), [started.get("holder_pid")],
            f"sweep must match exactly the orphaned holder: {receipt}",
        )
        self.assertEqual(
            receipt.get("residual_pids"), [],
            f"sweep left residue: {receipt}",
        )
        self.assertEqual(payload.get("schema"), "kaola-acp-view/1")
        self.assertIn((payload.get("error") or {}).get("code"), {
            "holder-lost", "holder-unreachable", "no-session",
        }, payload)

    def test_tmux_view_emits_view_unsupported(self) -> None:
        result = subprocess.run(
            [
                str(TMUX), "grok", "view",
                "--repo", str(self.repo), "--session", f"wch-tmux-{os.getpid()}",
            ],
            capture_output=True, text=True, env=self.env(), timeout=15,
        )
        self.assertNotEqual(result.returncode, 0, result.stderr)
        payload = self.load_object(result, "kaola-tmux view")
        self.assertEqual(payload.get("schema"), "kaola-acp-view/1")
        self.assertEqual((payload.get("error") or {}).get("code"), "view-unsupported")
        # Issue #130: there is no pty/tmux view to point at any more.
        message = (payload.get("error") or {}).get("message", "")
        self.assertEqual(message, "view is not a Runner command; use kaola-acp")
        self.assertNotIn("pty", message.lower())

    def test_acp_reference_names_human_list_and_view(self) -> None:
        for path in (ACP_TMPL, GROK_ACP_REF):
            text = path.read_text(encoding="utf-8")
            self.assertRegex(
                text, r"`list`",
                f"{path} must name the human list command",
            )
            self.assertRegex(
                text, r"`view`",
                f"{path} must name the human view command",
            )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class AcpWatchInstallTests(unittest.TestCase):
    def test_install_local_creates_owned_bin_symlinks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-acp-bin-") as raw:
            home = Path(raw) / "home"
            codex = Path(raw) / "codex"
            home.mkdir()
            env = dict(os.environ)
            env["HOME"] = str(home)
            env["CODEX_HOME"] = str(codex)
            result = subprocess.run(
                [str(INSTALLER), "--platform", "grok"],
                capture_output=True, text=True, env=env, cwd=str(PROJECT),
            )
            acp = home / ".local" / "bin" / "kaola-acp"
            holder = home / ".local" / "bin" / "kaola-acp-holder"
            self.assertEqual(
                result.returncode, 0,
                f"install failed\nstdout={result.stdout!r}\nstderr={result.stderr!r}",
            )
            for link, source in ((acp, CLI), (holder, HOLDER)):
                self.assertTrue(link.is_symlink(), f"{link} is not a symlink")
                self.assertEqual(link.resolve(), source.resolve())
                self.assertEqual(link.lstat().st_uid, os.getuid())
            uninstalled = subprocess.run(
                [str(INSTALLER), "--uninstall", "--platform", "grok"],
                capture_output=True, text=True, env=env, cwd=str(PROJECT),
            )
            self.assertEqual(uninstalled.returncode, 0, uninstalled.stderr)
            # Ordinary uninstall leaves shared helper links alone; they may be
            # needed by another installation.
            self.assertTrue(acp.is_symlink())
            self.assertTrue(holder.is_symlink())
            removed = subprocess.run(
                [str(INSTALLER), "--uninstall", "--platform", "grok", "--bin-links"],
                capture_output=True, text=True, env=env, cwd=str(PROJECT),
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(acp.exists() or acp.is_symlink())
            self.assertFalse(holder.exists() or holder.is_symlink())

    def test_install_refuses_foreign_bin_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-acp-foreign-") as raw:
            home = Path(raw) / "home"
            codex = Path(raw) / "codex"
            bin_dir = home / ".local" / "bin"
            bin_dir.mkdir(parents=True)
            foreign = bin_dir / "kaola-acp"
            foreign.write_text("foreign-binary\n", encoding="utf-8")
            env = dict(os.environ)
            env["HOME"] = str(home)
            env["CODEX_HOME"] = str(codex)
            result = subprocess.run(
                [str(INSTALLER), "--platform", "grok"],
                capture_output=True, text=True, env=env, cwd=str(PROJECT),
            )
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertTrue(foreign.is_file())
            self.assertFalse(foreign.is_symlink())
            self.assertEqual(foreign.read_text(encoding="utf-8"), "foreign-binary\n")
            self.assertTrue(foreign.stat().st_mode & stat.S_IFREG)



def load_holder_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("kaola_acp_holder", HOLDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AcpProjectionOfflineTests(unittest.TestCase):
    """Reduction facts that the mock stream cannot show: real agents (Grok)
    send no ``messageId`` and stream thousands of updates, so the caps in
    list-view.md must be enforced, not only flagged."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.holder_module = load_holder_module()

    def offline_holder(self, tmp: str):
        import argparse

        args = argparse.Namespace(
            record_dir=tmp, socket=None, repo="/repo", platform="grok", session="s",
            command="true", resume=None, use_continue=False,
        )
        return self.holder_module.Holder(args)

    @staticmethod
    def chunk(text: str, message_id: str | None = None) -> dict:
        update = {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}}
        if message_id is not None:
            update["messageId"] = message_id
        return update

    def test_chunks_without_message_id_join_until_a_boundary(self) -> None:
        projection = self.holder_module.ViewProjection()
        projection.add_user_from_prompt("Fix it.", 1)
        for index, piece in enumerate(("I'll ", "start ", "here.")):
            projection.apply(self.chunk(piece), 2 + index)
        projection.apply({"sessionUpdate": "tool_call", "toolCallId": "t1", "title": "Read"}, 5)
        projection.apply(self.chunk("Done."), 6)
        projection.close_message()
        projection.apply(self.chunk("Next turn."), 7)
        texts = [(m["role"], m["text"], m["cursor"]) for m in projection.snapshot()["messages"]]
        self.assertEqual(texts, [
            ("user", "Fix it.", 1),
            ("assistant", "I'll start here.", 2),
            ("assistant", "Done.", 6),
            ("assistant", "Next turn.", 7),
        ])

    def test_caps_bound_memory_and_view_bytes(self) -> None:
        mod = self.holder_module
        with tempfile.TemporaryDirectory() as tmp:
            holder = self.offline_holder(tmp)
            projection = holder.projection
            for index in range(mod.TIMELINE_MAX + 50):
                projection.apply(self.chunk("x" * 300, message_id=f"m{index}"), index + 1)
            projection.apply(
                {"sessionUpdate": "agent_thought_chunk", "content": {"type": "text", "text": "t" * (mod.THINKING_TAIL_CHARS * 2)}},
                1000,
            )
            big = "y" * (mod.TOOL_VIEW_BYTES * 2)
            for index in range(40):
                projection.apply({
                    "sessionUpdate": "tool_call", "toolCallId": f"big{index}", "title": "Write",
                    "content": [{"type": "text", "text": big}],
                }, 2000 + index)
            snap = projection.snapshot()
            self.assertEqual(len(snap["messages"]), mod.TIMELINE_MAX)
            self.assertTrue(snap["messages_dropped"])
            self.assertEqual(len(snap["thinking_text"]), mod.THINKING_TAIL_CHARS)
            self.assertEqual(snap["thinking_chars"], mod.THINKING_TAIL_CHARS * 2)
            for tool in snap["tools"]:
                self.assertTrue(tool["truncated"])
                self.assertLessEqual(len(mod.canonical(tool["content"])), mod.TOOL_VIEW_BYTES)

            view = holder.op_view({})
            encoded = json.dumps(view, ensure_ascii=False).encode("utf-8")
            self.assertLessEqual(len(encoded), mod.VIEW_BYTES, len(encoded))
            self.assertTrue(view["truncated"])
            self.assertEqual(view["schema"], "kaola-acp-view/1")
            self.assertEqual(view["tools"][-1]["toolCallId"], "big39", "newest tools survive the view cap")
            self.assertEqual(len(view["thinking"]["text_tail"]), mod.THINKING_TAIL_CHARS)

    def test_event_log_oldest_cursor_is_cached_across_append_and_rotation(self) -> None:
        mod = self.holder_module
        with tempfile.TemporaryDirectory() as tmp:
            live = Path(tmp) / "events.jsonl"
            live.with_suffix(".jsonl.2").write_text(json.dumps({"cursor": 5}) + "\n", encoding="utf-8")
            live.write_text(json.dumps({"cursor": 9}) + "\n", encoding="utf-8")
            log = mod.EventLog(live)
            self.assertEqual((log.cursor, log.oldest_cursor()), (9, 5))
            log.append({"kind": "x"})
            self.assertEqual((log.cursor, log.oldest_cursor()), (10, 5))
            live.with_suffix(".jsonl.2").unlink()
            log._rotate()
            self.assertEqual(log.oldest_cursor(), 9)
            fresh = mod.EventLog(Path(tmp) / "empty.jsonl")
            self.assertIsNone(fresh.oldest_cursor())
            fresh.append({"kind": "first"})
            self.assertEqual(fresh.oldest_cursor(), 1)


if __name__ == "__main__":
    unittest.main()
