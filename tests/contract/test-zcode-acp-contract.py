#!/usr/bin/env python3
"""Hermetic ACP contract for the Issue #51 ZCode adapter (Mission 2).

Drives ``scripts/kaola-zcode-acp.py`` against
``tests/contract/fake-zcode-app-server.py``. No installed ZCode binary, no
login, no account, no network, and no real credential/config files are used.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import queue
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ADAPTER = PROJECT / "scripts" / "kaola-zcode-acp.py"
CHECKOUT_CLI = PROJECT / "scripts" / "kaola-acp.py"
FAKE = PROJECT / "tests" / "contract" / "fake-zcode-app-server.py"
PROBE = PROJECT / "tests" / "contract" / "hooks" / "zcode-probe"
UPSTREAM = PROJECT / "third_party" / "zcode-acp" / "UPSTREAM.md"

FORBIDDEN_IMPORTS = {
    "socket", "ssl", "http", "httpx", "urllib", "requests", "aiohttp",
    "websockets", "sqlite3", "sqlite",
}
# Issue #51 owner correction: the desktop provider registry (`v2/config.json`)
# and the plan cache are read-only exceptions; everything else stays shut.
FORBIDDEN_OPEN_MARKERS = (
    "/.zcode/cli/",
    "credentials.json",
    "setting.json",
    "tasks-index.sqlite",
    "telemetry-state.json",
    "/.zcode/v2/certs",
    "zcode-acp/config.json",
)
FIXTURES = PROJECT / "tests" / "contract" / "fixtures"
DESKTOP_CONFIG_FIXTURE = FIXTURES / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = FIXTURES / "zcode-coding-plan-cache.json"
DESKTOP_CONFIG = json.loads(DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"))
CODING_PLAN_ID = "builtin:bigmodel-coding-plan"
FIXTURE_SECRET = DESKTOP_CONFIG["provider"][CODING_PLAN_ID]["options"]["apiKey"]
START_PLAN_SECRET = DESKTOP_CONFIG["provider"]["builtin:bigmodel-start-plan"]["options"]["apiKey"]
DENIED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "ZCODE_API_KEY",
    "ZCODE_BASE_URL",
    "ZCODE_MODEL",
    "ZCODE_PROVIDER",
    "ZCODE_CREDENTIAL_SECRET",
    "ZCODE_BIGMODEL_USAGE_API_KEY",
    "ZCODE_BIGMODEL_USAGE_QUOTA_URL",
    "ZCODE_ACP_REMOTE",
    "ZCODE_ACP_REMOTE_TOKEN",
    "ZCODE_ACP_HUB_HOST",
    "ZCODE_ACP_HUB_PORT",
)


def load_adapter_module():
    spec = importlib.util.spec_from_file_location("kaola_zcode_acp", ADAPTER)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {ADAPTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wait_for(predicate, timeout: float, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class AdapterDriver:
    def __init__(
        self,
        tmp: Path,
        scenario: str = "basic",
        extra_env: dict[str, str] | None = None,
        cwd: Path | None = None,
        desktop_config: dict | str | None = None,
    ) -> None:
        self.tmp = tmp
        self.scenario = scenario
        self.cwd = cwd or (tmp / "workspace")
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.record_path = tmp / f"fake-record-{scenario}.json"
        self.rpc_log = tmp / f"fake-rpc-{scenario}.jsonl"
        self.open_log = tmp / "opens.jsonl"
        self.home = tmp / "home"
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / ".zcode" / "v2").mkdir(parents=True, exist_ok=True)
        (self.home / ".zcode" / "cli").mkdir(parents=True, exist_ok=True)
        (self.home / ".config" / "zcode-acp").mkdir(parents=True, exist_ok=True)
        if desktop_config is None:
            registry_text = DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8")
        elif isinstance(desktop_config, str):
            registry_text = desktop_config
        else:
            registry_text = json.dumps(desktop_config, indent=1)
        if registry_text != "ABSENT":
            (self.home / ".zcode" / "v2" / "config.json").write_text(registry_text, encoding="utf-8")
        (self.home / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "credentials.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "setting.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "tasks-index.sqlite").write_bytes(b"")
        (self.home / ".zcode" / "cli" / "config.json").write_text('{"hooks":{}}\n', encoding="utf-8")
        (self.home / ".config" / "zcode-acp" / "config.json").write_text("{}\n", encoding="utf-8")
        self.cli_config = self.home / ".zcode" / "cli" / "config.json"
        self.shim = self._write_shim()
        self.messages: list[dict] = []
        self.queue: queue.Queue = queue.Queue()
        env = {
            "HOME": str(self.home),
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "PYTHONPATH": str(PROBE),
            "PYTHONUNBUFFERED": "1",
            "ZCODE_OPEN_LOG": str(self.open_log),
            "LANG": "C",
        }
        for name in DENIED_ENV:
            env[name] = "must-not-forward"
        if extra_env:
            env.update(extra_env)
        self.proc = subprocess.Popen(
            [
                sys.executable, str(ADAPTER),
                "--zcode-entry", str(self.shim),
                "--zcode-node", sys.executable,
                "--cwd", str(self.cwd),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.cwd),
            env=env,
        )
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._err = threading.Thread(target=self._read_stderr, daemon=True)
        self.stderr_bytes = bytearray()
        self._reader.start()
        self._err.start()

    def _write_shim(self) -> Path:
        shim = self.tmp / f"zcode-entry-{self.scenario}.py"
        shim.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {self.scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(self.record_path)!r}\n"
            f"os.environ['FAKE_ZCODE_RPC_LOG'] = {str(self.rpc_log)!r}\n"
            f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        return shim

    def _read_stdout(self) -> None:
        assert self.proc.stdout is not None
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                self.messages.append(msg)
                self.queue.put(msg)

    def _read_stderr(self) -> None:
        assert self.proc.stderr is not None
        for chunk in iter(lambda: self.proc.stderr.read(4096), b""):
            if not chunk:
                break
            self.stderr_bytes.extend(chunk)

    def send(self, msg: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(msg).encode("utf-8") + b"\n")
        self.proc.stdin.flush()

    def request(self, rid, method: str, params: dict | None = None) -> None:
        payload: dict = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)

    def wait_for(self, pred, timeout: float = 5.0):
        deadline = time.monotonic() + timeout
        for msg in list(self.messages):
            if pred(msg):
                return msg
        while time.monotonic() < deadline:
            try:
                msg = self.queue.get(timeout=0.05)
            except queue.Empty:
                if self.proc.poll() is not None:
                    break
                continue
            if pred(msg):
                return msg
        for msg in list(self.messages):
            if pred(msg):
                return msg
        return None

    def wait_result(self, rid, timeout: float = 5.0):
        return self.wait_for(
            lambda msg: msg.get("id") == rid and ("result" in msg or "error" in msg),
            timeout,
        )

    def wait_method(self, method: str, timeout: float = 5.0):
        return self.wait_for(lambda msg: msg.get("method") == method, timeout)

    def updates(self, session_id: str) -> list[dict]:
        found = []
        for msg in self.messages:
            if msg.get("method") != "session/update":
                continue
            params = msg.get("params") or {}
            if params.get("sessionId") == session_id:
                found.append(params.get("update") or {})
        return found

    def rpc_calls(self, method: str) -> list[dict]:
        if not self.rpc_log.is_file():
            return []
        calls = []
        for line in self.rpc_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            msg = row.get("msg") or {}
            if row.get("direction") == "in" and msg.get("method") == method:
                calls.append(msg)
        return calls

    def record(self) -> dict:
        if not self.record_path.is_file():
            return {}
        return json.loads(self.record_path.read_text(encoding="utf-8"))

    def open_entries(self) -> list[str]:
        if not self.open_log.is_file():
            return []
        return [line.strip() for line in self.open_log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def close(self) -> int:
        if self.proc.stdin and not self.proc.stdin.closed:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        try:
            code = self.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            code = self.proc.returncode if self.proc.returncode is not None else -9
        for stream in (self.proc.stdout, self.proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        fake_pid = self.record().get("pid")
        wait_for(lambda: not pid_alive(fake_pid), 3)
        return code


class HolderTurn:
    """Drive one fake-ZCode turn through the real holder so events.jsonl is the record."""

    def __init__(self, tmp: Path, scenario: str) -> None:
        self.scenario = scenario
        self.root = tmp / f"holder-{scenario}-{uuid.uuid4().hex[:8]}"
        self.home = self.root / "home"
        self.repo = self.root / "repo"
        self.record_root = self.root / "records"
        for path in (self.home, self.repo, self.record_root):
            path.mkdir(parents=True)
        (self.home / ".zcode" / "v2").mkdir(parents=True)
        (self.home / ".zcode" / "cli").mkdir(parents=True)
        (self.home / ".zcode" / "v2" / "config.json").write_text(
            DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "cli" / "config.json").write_text('{"hooks":{}}\n', encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.fake_record = self.root / "fake-record.json"
        self.entry = self.root / f"zcode-entry-{scenario}.py"
        self.entry.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(self.fake_record)!r}\n"
            f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        self.entry.chmod(self.entry.stat().st_mode | stat.S_IXUSR)
        self.session = f"zcode-i67-{uuid.uuid4().hex[:8]}"
        self.record_dir = self.record_root / "zcode" / self.session

    def env(self) -> dict[str, str]:
        return {
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "HOME": str(self.home),
            "LANG": "C",
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "KAOLA_ZCODE_ENTRY": str(self.entry),
            "KAOLA_ZCODE_NODE": sys.executable,
            "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1",
        }

    def cli(self, command: str, *args: str, timeout: float = 30) -> dict:
        argv = [sys.executable, str(CHECKOUT_CLI), "zcode", command,
                "--repo", str(self.repo), "--session", self.session, *args]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout)
        text = (result.stdout or "").strip()
        payload = None
        if text:
            try:
                payload = json.loads(text.splitlines()[-1])
            except ValueError:
                payload = None
        if result.returncode != 0 or not isinstance(payload, dict):
            raise AssertionError(
                f"{command} exit {result.returncode}: {(result.stderr or '')[-800:]} "
                f"{(result.stdout or '')[-400:]}")
        return payload

    def start(self) -> dict:
        receipt = self.cli("start", "--mode", "yolo")
        if receipt.get("error") or receipt.get("state") != "ready":
            raise AssertionError(f"holder start failed: {receipt.get('error') or receipt}")
        return receipt

    def send(self, text: str) -> dict:
        return self.cli("send", "--text", text)

    def stop(self) -> None:
        subprocess.run(
            [sys.executable, str(CHECKOUT_CLI), "zcode", "stop",
             "--repo", str(self.repo), "--session", self.session, "--force"],
            capture_output=True, env=self.env(), timeout=30,
        )


class ZcodeAcpStaticTests(unittest.TestCase):
    def test_pin_and_gate2_attribution(self) -> None:
        text = UPSTREAM.read_text(encoding="utf-8")
        self.assertIn("80aa4e2c39909f91145dfdf6428a3867b5c61701", text)
        self.assertIn("Apache-2.0", text)
        self.assertIn("Gate 2", text)
        self.assertIn("Vendored upstream source bytes: **none**", text)
        adapter = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("third_party/zcode-acp/UPSTREAM.md", adapter)
        self.assertIn("no auth environment injection", adapter)

    def test_adapter_imports_stay_local(self) -> None:
        tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported & FORBIDDEN_IMPORTS, set())

    def test_allowlist_excludes_denied_env(self) -> None:
        module = load_adapter_module()
        self.assertEqual(set(module.DENIED_ENV) & set(module.ENV_ALLOWLIST), set())
        for name in DENIED_ENV:
            self.assertIn(name, module.DENIED_ENV)

    def test_extract_tool_evidence_keeps_only_bounded_path_command(self) -> None:
        module = load_adapter_module()
        module.register_secret("super-secret-value-xyz")
        path = "/tmp/kpr-issue-67-fixture/MARKER.txt"
        nested = {"file_path": path, "blob": "PAD" * 5000}
        for _ in range(8):
            nested = {"child": nested}
        raw = module.extract_tool_evidence({
            "file_path": path,
            "command": "echo super-secret-value-xyz " + ("x" * 400),
            "apiKey": "super-secret-value-xyz",
            "contents": "unregistered-secret-value-abc123xyz",
            "extra": nested,
        })
        assert raw is not None
        self.assertEqual(raw.get("file_path"), path)
        self.assertTrue(str(raw.get("command", "")).startswith("echo <redacted-credential>"))
        self.assertLessEqual(len(str(raw.get("command"))), module.RAW_INPUT_COMMAND_CAP + 1)
        self.assertNotIn("apiKey", raw)
        self.assertNotIn("contents", raw)
        self.assertNotIn("extra", raw)
        self.assertNotIn("unregistered-secret-value-abc123xyz", json.dumps(raw))
        self.assertLessEqual(
            len(json.dumps(raw, ensure_ascii=False).encode("utf-8")),
            module.RAW_INPUT_MAX_BYTES,
        )
        self.assertEqual(module.RAW_INPUT_MAX_DEPTH, 1)
        self.assertIsNone(module.extract_tool_evidence(nested), "nested path is not lifted")
        self.assertEqual(
            module.locations_from_input(raw),
            [{"path": path, "line": None}],
        )
        self.assertEqual(module.locations_from_input({"command": "cat /etc/passwd"}), [])
        self.assertIsNone(module.extract_tool_evidence({}))
        self.assertIsNone(module.extract_tool_evidence(None))

    def test_resolve_runtime_fails_closed(self) -> None:
        module = load_adapter_module()
        with self.assertRaises(module.RuntimeError_):
            module.resolve_runtime(None, None)
        with self.assertRaises(module.RuntimeError_):
            module.resolve_runtime("zcode.cjs", "/usr/bin/true")
        missing = "/tmp/kaola-zcode-missing-entry-does-not-exist.cjs"
        with self.assertRaises(module.RuntimeError_):
            module.resolve_runtime(missing, sys.executable)


class ZcodeAcpContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-zcode-acp-")
        self.tmp = Path(self._tmp.name)
        self.driver: AdapterDriver | None = None

    def tearDown(self) -> None:
        self.stop_driver()
        self._tmp.cleanup()

    def stop_driver(self) -> None:
        if self.driver is None:
            return
        record = self.driver.record()
        self.driver.close()
        fake_pid = record.get("pid")
        self.assertFalse(pid_alive(fake_pid), f"fake app-server still alive pid={fake_pid}")
        self.driver = None

    def start(
        self,
        scenario: str = "basic",
        extra_env: dict[str, str] | None = None,
        desktop_config: dict | str | None = None,
    ) -> AdapterDriver:
        self.driver = AdapterDriver(
            self.tmp, scenario=scenario, extra_env=extra_env, desktop_config=desktop_config,
        )
        return self.driver

    def handshake(self, driver: AdapterDriver) -> str:
        driver.request(1, "initialize", {
            "protocolVersion": 1,
            "clientCapabilities": {"fs": False, "terminal": False},
            "clientInfo": {"name": "kaola-zcode-test", "version": "0"},
        })
        init = driver.wait_result(1)
        self.assertIsNotNone(init)
        assert init is not None
        result = init.get("result") or {}
        self.assertEqual(result.get("protocolVersion"), 1)
        self.assertEqual(result.get("authMethods"), [])
        self.assertEqual((result.get("agentInfo") or {}).get("name"), "kaola-zcode-acp")
        caps = result.get("agentCapabilities") or {}
        self.assertTrue(caps.get("loadSession"))
        driver.request(2, "session/new", {"cwd": str(driver.cwd), "mcpServers": []})
        created = driver.wait_result(2)
        self.assertIsNotNone(created)
        assert created is not None
        session_id = (created.get("result") or {}).get("sessionId")
        self.assertTrue(session_id)
        options = (created.get("result") or {}).get("configOptions") or []
        mode_ids = {item.get("id") for item in options}
        self.assertIn("mode", mode_ids)
        self.assertIn("model", mode_ids)
        return session_id

    def test_fail_closed_cli_missing_runtime(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ADAPTER)],
            capture_output=True, text=True, timeout=5,
            env={"HOME": str(self.tmp), "PATH": os.environ.get("PATH", "/usr/bin")},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("fail-closed", result.stderr)

    def test_fail_closed_relative_and_missing_paths(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ADAPTER), "--zcode-entry", "zcode.cjs",
             "--zcode-node", sys.executable],
            capture_output=True, text=True, timeout=5,
            env={"HOME": str(self.tmp), "PATH": os.environ.get("PATH", "/usr/bin")},
        )
        self.assertEqual(result.returncode, 2)
        missing = str(self.tmp / "no-such-zcode.cjs")
        result = subprocess.run(
            [sys.executable, str(ADAPTER), "--zcode-entry", missing,
             "--zcode-node", sys.executable],
            capture_output=True, text=True, timeout=5,
            env={"HOME": str(self.tmp), "PATH": os.environ.get("PATH", "/usr/bin")},
        )
        self.assertEqual(result.returncode, 2)

    def test_session_new_does_not_spawn_backend(self) -> None:
        driver = self.start("basic")
        self.handshake(driver)
        self.assertFalse(driver.record_path.is_file())
        self.assertIsNone(driver.proc.poll())

    def test_basic_stream_tool_usage_and_cleanup(self) -> None:
        driver = self.start("basic")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "hello"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "end_turn")
        self.assertIn("usage", done.get("result") or {})
        kinds = [update.get("sessionUpdate") for update in driver.updates(session_id)]
        self.assertIn("agent_thought_chunk", kinds)
        self.assertIn("agent_message_chunk", kinds)
        self.assertIn("tool_call", kinds)
        texts = []
        for update in driver.updates(session_id):
            if update.get("sessionUpdate") == "agent_message_chunk":
                texts.append((update.get("content") or {}).get("text") or "")
        self.assertIn("hello ", texts)
        self.assertIn("from zcode", texts)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        self.assertTrue(any(u.get("kind") == "execute" and u.get("status") == "completed" for u in tools))
        completed = [u for u in tools if u.get("status") == "completed"]
        self.assertTrue(completed)
        self.assertEqual(completed[-1].get("rawInput"), {"command": "echo hi"})
        self.assertNotIn("locations", completed[-1])
        record = wait_for(lambda: driver.record() or None, 3)
        self.assertIsNotNone(record)
        assert record is not None
        env_names = record.get("env_names") or []
        leaked = [name for name in DENIED_ENV if name in env_names]
        self.assertEqual(leaked, [])
        self.assertIn("ELECTRON_RUN_AS_NODE", env_names)
        self.assertEqual(record.get("argv")[:2], ["app-server", "--stdio"])
        forbidden = [entry for entry in driver.open_entries() if any(marker in entry for marker in FORBIDDEN_OPEN_MARKERS)]
        self.assertEqual(forbidden, [])
        connects = [entry for entry in driver.open_entries() if entry.startswith("socket.connect:")]
        self.assertEqual(connects, [])
        self.assert_registry_read_only_and_secret_contained(driver)
        driver.request(4, "session/close", {"sessionId": session_id})
        closed = driver.wait_result(4)
        self.assertIsNotNone(closed)

    def test_concurrent_prompt_never_steals_the_active_request_id(self) -> None:
        """Issue #65: one turn owns one request id.

        A second ``session/prompt`` that lands while a turn is running used to
        overwrite ``turn_request_id``, which orphaned the original request for
        good and handed its completion to the newcomer. It is now refused with
        the same code ZCode 0.16.5 uses itself, and the original turn keeps its
        own response attribution.
        """
        driver = self.start("slow")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "long running"}],
        })
        # wait until the turn is genuinely streaming before the second prompt
        streaming = wait_for(
            lambda: any(u.get("sessionUpdate") == "agent_message_chunk"
                        for u in driver.updates(session_id)),
            8,
        )
        self.assertTrue(streaming, "the slow turn never started streaming")
        driver.request(4, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "second prompt"}],
        })
        refused = driver.wait_result(4, timeout=8)
        self.assertIsNotNone(refused)
        assert refused is not None
        error = refused.get("error") or {}
        self.assertEqual(error.get("code"), -32010)
        self.assertIn("already running", str(error.get("message", "")))
        self.assertIsNone(refused.get("result"))
        # the original request is still the one that settles this turn
        self.assertIsNone(driver.wait_result(3, timeout=0.5))
        driver.request(5, "session/cancel", {"sessionId": session_id})
        settled = driver.wait_result(3, timeout=12)
        self.assertIsNotNone(settled, "the original prompt never got its own response")
        assert settled is not None
        self.assertIn("stopReason", settled.get("result") or {})

    def test_tool_error_and_turn_failure(self) -> None:
        driver = self.start("tool_error")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "fail tool"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        self.assertTrue(any(u.get("status") == "failed" for u in tools))
        self.stop_driver()

        driver = self.start("failure")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "fail turn"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "refusal")

    def test_permission_plan_question_and_batch(self) -> None:
        driver = self.start("permission")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "need permit"}],
        })
        permit = driver.wait_method("session/request_permission", timeout=8)
        self.assertIsNotNone(permit)
        assert permit is not None
        tool_call = (permit.get("params") or {}).get("toolCall") or {}
        self.assertEqual(tool_call.get("rawInput"), {"command": "ls -la"})
        self.assertNotIn("locations", tool_call)
        driver.send({
            "jsonrpc": "2.0",
            "id": permit.get("id"),
            "result": {"outcome": {"outcome": "selected", "optionId": "allow"}},
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        self.stop_driver()

        driver = self.start("plan")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "plan"}],
        })
        permit = driver.wait_method("session/request_permission", timeout=8)
        self.assertIsNotNone(permit)
        plans = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "plan"]
        self.assertTrue(plans)
        assert permit is not None
        driver.send({
            "jsonrpc": "2.0",
            "id": permit.get("id"),
            "result": {"outcome": {"outcome": "selected", "optionId": "approve"}},
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        self.stop_driver()

        driver = self.start("question")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "ask"}],
        })
        permit = driver.wait_method("session/request_permission", timeout=8)
        self.assertIsNotNone(permit)
        assert permit is not None
        driver.send({
            "jsonrpc": "2.0",
            "id": permit.get("id"),
            "result": {"outcome": {"outcome": "selected", "optionId": "auth"}},
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        self.stop_driver()

        driver = self.start("batch")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "batch"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        ids = {u.get("toolCallId") for u in tools}
        self.assertIn("call_b1", ids)
        self.assertIn("call_b2", ids)

    def test_cancel_slow_turn(self) -> None:
        driver = self.start("slow")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": "slow"}],
        })
        chunk = driver.wait_for(lambda msg: msg.get("method") == "session/update" and ((msg.get("params") or {}).get("update") or {}).get("sessionUpdate") == "agent_message_chunk", timeout=8)
        self.assertIsNotNone(chunk)
        driver.send({"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session_id}})
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "cancelled")

    def test_mode_model_thought_without_silent_fallback(self) -> None:
        driver = self.start("strict_model")
        session_id = self.handshake(driver)
        driver.request(3, "session/set_config_option", {
            "sessionId": session_id, "configId": "mode", "value": "plan",
        })
        mode_result = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(mode_result)
        assert mode_result is not None
        self.assertNotIn("error", mode_result)
        driver.request(4, "session/set_config_option", {
            "sessionId": session_id, "configId": "model", "value": f"{CODING_PLAN_ID}\\GLM-5.3-Flash",
        })
        model_ok = driver.wait_result(4, timeout=8)
        self.assertIsNotNone(model_ok)
        assert model_ok is not None
        self.assertNotIn("error", model_ok)
        options = {o["id"]: o for o in (model_ok.get("result") or {}).get("configOptions") or []}
        self.assertEqual(options["model"]["currentValue"], f"{CODING_PLAN_ID}\\GLM-5.3-Flash")
        self.assertEqual(
            sorted(o["value"] for o in options["model"]["options"]),
            [f"{CODING_PLAN_ID}\\GLM-5.3", f"{CODING_PLAN_ID}\\GLM-5.3-Flash"],
        )
        set_model = driver.rpc_calls("session/setModel")
        self.assertTrue(set_model)
        params = set_model[-1].get("params") or {}
        self.assertEqual(params.get("model"), {"providerId": CODING_PLAN_ID, "modelId": "GLM-5.3-Flash"})
        self.assertNotIn("apiKey", params.get("model") or {})
        overlay = params.get("runtimeModel") or {}
        self.assertEqual(overlay.get("provider", {}).get("providerId"), CODING_PLAN_ID)
        self.assertEqual(overlay.get("provider", {}).get("apiKey"), {"source": "inline", "value": FIXTURE_SECRET})
        self.assertFalse(params.get("persistAsWorkspaceLastUsed"))
        before = len(set_model)
        # Unknown model: refused by the adapter before any backend call.
        driver.request(5, "session/set_config_option", {
            "sessionId": session_id, "configId": "model", "value": "no-such-model",
        })
        rejected = driver.wait_result(5, timeout=8)
        self.assertIsNotNone(rejected)
        assert rejected is not None
        self.assertIn("error", rejected)
        # Pay-as-you-go provider for the same model id: refused, never billed.
        driver.request(7, "session/set_config_option", {
            "sessionId": session_id, "configId": "model", "value": "builtin:bigmodel\\GLM-5.3",
        })
        billing = driver.wait_result(7, timeout=8)
        self.assertIsNotNone(billing)
        assert billing is not None
        self.assertIn("not the enabled GLM Coding Plan provider", (billing.get("error") or {}).get("message", ""))
        # Start Plan provider: refused likewise.
        driver.request(8, "session/set_config_option", {
            "sessionId": session_id, "configId": "model", "value": "builtin:bigmodel-start-plan\\GLM-5.3",
        })
        start_plan = driver.wait_result(8, timeout=8)
        self.assertIsNotNone(start_plan)
        assert start_plan is not None
        self.assertIn("error", start_plan)
        self.assertEqual(len(driver.rpc_calls("session/setModel")), before)
        self.assert_registry_read_only_and_secret_contained(driver)
        driver.request(6, "session/set_config_option", {
            "sessionId": session_id, "configId": "thoughtLevel", "value": "max",
        })
        thought = driver.wait_result(6, timeout=8)
        self.assertIsNotNone(thought)
        assert thought is not None
        self.assertNotIn("error", thought)
        self.assertTrue(driver.rpc_calls("session/setMode"))
        self.assertTrue(driver.rpc_calls("session/setThoughtLevel"))

    def test_list_resume_and_concurrent_sessions(self) -> None:
        driver = self.start("basic")
        first = self.handshake(driver)
        driver.request(10, "session/new", {"cwd": str(driver.cwd), "mcpServers": []})
        second_msg = driver.wait_result(10)
        self.assertIsNotNone(second_msg)
        assert second_msg is not None
        second = (second_msg.get("result") or {}).get("sessionId")
        self.assertTrue(second)
        self.assertNotEqual(first, second)
        driver.request(11, "session/prompt", {
            "sessionId": first, "prompt": [{"type": "text", "text": "one"}],
        })
        driver.request(12, "session/prompt", {
            "sessionId": second, "prompt": [{"type": "text", "text": "two"}],
        })
        one = driver.wait_result(11, timeout=8)
        two = driver.wait_result(12, timeout=8)
        self.assertIsNotNone(one)
        self.assertIsNotNone(two)
        self.assertTrue(driver.updates(first))
        self.assertTrue(driver.updates(second))
        driver.request(13, "session/list", {})
        listed = driver.wait_result(13, timeout=8)
        self.assertIsNotNone(listed)
        assert listed is not None
        sessions = (listed.get("result") or {}).get("sessions") or []
        backend_ids = [item.get("sessionId") for item in sessions]
        self.assertEqual(len(backend_ids), 2)
        resume_id = backend_ids[0]
        driver.request(14, "session/load", {"sessionId": resume_id, "cwd": str(driver.cwd)})
        loaded = driver.wait_result(14, timeout=8)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertNotIn("error", loaded)
        driver.request(15, "session/fork", {"sessionId": first})
        forked = driver.wait_result(15, timeout=3)
        self.assertIsNotNone(forked)
        assert forked is not None
        self.assertEqual((forked.get("error") or {}).get("code"), -32601)

    def test_authenticate_is_noop_and_native_login_is_not_adapter_owned(self) -> None:
        driver = self.start("basic")
        driver.request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        init = driver.wait_result(1)
        self.assertIsNotNone(init)
        assert init is not None
        self.assertEqual((init.get("result") or {}).get("authMethods"), [])
        meta = (((init.get("result") or {}).get("agentInfo") or {}).get("_meta") or {}).get("zcode") or {}
        self.assertEqual(meta.get("plan"), "coding-plan")
        self.assertEqual(meta.get("providerId"), CODING_PLAN_ID)
        self.assertEqual(meta.get("baseURL"), "https://open.bigmodel.cn/api/anthropic")
        self.assertEqual(meta.get("planCacheStatus"), "available")
        self.assertEqual(meta.get("modelIds"), ["GLM-5.3", "GLM-5.3-Flash"])
        self.assertEqual(meta.get("defaultModelId"), "GLM-5.3")
        self.assertIn("builtin:bigmodel-start-plan", meta.get("rejectedProviders") or {})
        self.assertIn("builtin:bigmodel", meta.get("rejectedProviders") or {})
        self.assertNotIn(FIXTURE_SECRET, json.dumps(init))
        driver.request(2, "authenticate", {"methodId": "anything"})
        auth = driver.wait_result(2)
        self.assertIsNotNone(auth)
        assert auth is not None
        self.assertEqual(auth.get("result"), {})
        self.assertFalse(driver.record_path.is_file())

    # -- Issue #51 owner correction: in-memory Coding Plan bridging ---------

    def assert_registry_read_only_and_secret_contained(self, driver: AdapterDriver) -> None:
        registry_opens = [e for e in driver.open_entries() if "/.zcode/v2/" in e]
        self.assertTrue(registry_opens, "adapter read the desktop registry")
        self.assertTrue(all(e.endswith(":mode=r") for e in registry_opens), registry_opens)
        touched = {e.split(":mode=")[0].rsplit("/", 1)[-1] for e in registry_opens}
        self.assertLessEqual(touched, {"config.json", "coding-plan-cache.json"})
        stdout_blob = json.dumps(driver.messages)
        self.assertNotIn(FIXTURE_SECRET, stdout_blob)
        self.assertNotIn(START_PLAN_SECRET, stdout_blob)
        self.assertNotIn(FIXTURE_SECRET, bytes(driver.stderr_bytes).decode("utf-8", "replace"))
        self.assertEqual(driver.cli_config.read_text(encoding="utf-8"), '{"hooks":{}}\n')
        # Registry and plan cache are byte-identical after the run.
        self.assertEqual(
            (driver.home / ".zcode" / "v2" / "config.json").read_text(encoding="utf-8"),
            DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (driver.home / ".zcode" / "v2" / "coding-plan-cache.json").read_text(encoding="utf-8"),
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"),
        )

    def test_create_carries_coding_plan_overlay_in_memory(self) -> None:
        driver = self.start("basic")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "sentinel"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "end_turn")
        creates = driver.rpc_calls("session/create")
        self.assertEqual(len(creates), 1)
        overlay = (creates[0].get("params") or {}).get("runtimeModel") or {}
        self.assertEqual(overlay.get("model"), {"providerId": CODING_PLAN_ID, "modelId": "GLM-5.3"})
        provider = overlay.get("provider") or {}
        self.assertEqual(provider.get("providerId"), CODING_PLAN_ID)
        self.assertEqual(provider.get("kind"), "anthropic")
        self.assertEqual(provider.get("apiFormat"), "anthropic-messages")
        self.assertEqual(provider.get("baseURL"), "https://open.bigmodel.cn/api/anthropic")
        self.assertEqual(provider.get("apiKey"), {"source": "inline", "value": FIXTURE_SECRET})
        self.assertEqual([m["modelId"] for m in provider.get("models") or []], ["GLM-5.3", "GLM-5.3-Flash"])
        flash = provider["models"][1]
        self.assertEqual(flash.get("reasoning", {}).get("defaultLevel"), "max")
        self.assertEqual([lvl["value"] for lvl in flash["reasoning"]["levels"]], ["low", "max", "high"])
        self.assertEqual(flash.get("contextWindow"), 1000000)
        self.assertTrue(flash.get("supportsImages"))
        self.assertTrue(overlay.get("revision", "").startswith("kaola-zcode-acp:"))
        self.assertNotIn(FIXTURE_SECRET, overlay["revision"])
        # Only the selected provider ever crosses to the backend.
        self.assertNotIn(START_PLAN_SECRET, json.dumps(creates))
        self.assertNotIn("builtin:bigmodel-start-plan", json.dumps(creates))
        record = wait_for(lambda: driver.record() or None, 3)
        assert record is not None
        overlays = record.get("overlays") or []
        self.assertEqual([o["method"] for o in overlays], ["session/create"])
        self.assertEqual(overlays[0]["apiKeyValue"], FIXTURE_SECRET)
        config_updates = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "config_option_update"]
        self.assertTrue(config_updates)
        model_opt = next(o for o in config_updates[-1]["configOptions"] if o["id"] == "model")
        self.assertEqual(model_opt.get("currentValue"), f"{CODING_PLAN_ID}\\GLM-5.3")
        self.assert_registry_read_only_and_secret_contained(driver)

    def test_fake_rejects_create_without_overlay(self) -> None:
        """The fake is discriminating: no overlay reproduces CLI 0.16.5's error."""
        proc = subprocess.Popen(
            [sys.executable, str(FAKE), "app-server", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={"PATH": os.environ.get("PATH", "/usr/bin"), "FAKE_ZCODE_SCENARIO": "basic"},
        )
        assert proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write(json.dumps({
                "id": 1, "method": "session/create",
                "params": {"workspace": {"workspacePath": "/tmp", "workspaceKey": "/tmp"}, "mode": "yolo"},
            }).encode("utf-8") + b"\n")
            proc.stdin.flush()
            reply = json.loads(proc.stdout.readline().decode("utf-8"))
            self.assertIn("Model config is missing", (reply.get("error") or {}).get("message", ""))
            bad = json.dumps({
                "id": 2, "method": "session/create",
                "params": {"workspace": {"workspacePath": "/tmp", "workspaceKey": "/tmp"},
                           "runtimeModel": {"revision": "x", "generatedAt": 1,
                                            "model": {"providerId": "p", "modelId": "m"},
                                            "provider": {"providerId": "p", "kind": "anthropic",
                                                         "apiKey": "bare-string-rejected",
                                                         "models": [{"modelId": "m"}]}}},
            })
            proc.stdin.write(bad.encode("utf-8") + b"\n")
            proc.stdin.flush()
            reply = json.loads(proc.stdout.readline().decode("utf-8"))
            self.assertEqual((reply.get("error") or {}).get("code"), -32602)
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)
            proc.stdout.close()

    def test_fail_closed_without_eligible_coding_plan(self) -> None:
        cases = {
            "start-plan-only": {"provider": {
                "builtin:bigmodel-start-plan": {
                    **DESKTOP_CONFIG["provider"]["builtin:bigmodel-start-plan"],
                    "enabled": True, "models": {"GLM-5.3": {}},
                },
            }},
            "pay-as-you-go-only": {"provider": {
                "builtin:bigmodel": {
                    **DESKTOP_CONFIG["provider"]["builtin:bigmodel"], "enabled": True,
                    "options": {"apiKey": "payg-key-must-not-be-used",
                                "baseURL": "https://open.bigmodel.cn/api/anthropic"},
                },
            }},
            "custom-coding-plan-suffix": {"provider": {
                "custom:payg-coding-plan": {
                    **DESKTOP_CONFIG["provider"][CODING_PLAN_ID], "enabled": True,
                    "options": {"apiKey": "custom-payg-key-must-not-be-used",
                                "baseURL": "https://example.invalid/api"},
                },
            }},
            "coding-plan-disabled": {"provider": {
                CODING_PLAN_ID: {**DESKTOP_CONFIG["provider"][CODING_PLAN_ID], "enabled": False,
                                 "systemDisabledReason": "oauth_provider_inactive"},
            }},
            "coding-plan-no-credential": {"provider": {
                CODING_PLAN_ID: {**DESKTOP_CONFIG["provider"][CODING_PLAN_ID],
                                 "options": {"apiKey": "", "baseURL": "https://open.bigmodel.cn/api/anthropic"}},
            }},
            "two-coding-plans-enabled": {"provider": {
                CODING_PLAN_ID: DESKTOP_CONFIG["provider"][CODING_PLAN_ID],
                "builtin:zai-coding-plan": {
                    **DESKTOP_CONFIG["provider"]["builtin:zai-coding-plan"], "enabled": True,
                    "options": {"apiKey": "second-plan-key-must-not-be-used",
                                "baseURL": "https://api.z.ai/api/anthropic"},
                },
            }},
            "registry-absent": "ABSENT",
            "registry-malformed": "{not json",
        }
        for label, registry in cases.items():
            with self.subTest(label):
                driver = self.start("basic", desktop_config=registry)
                driver.request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
                init = driver.wait_result(1)
                assert init is not None
                meta = (((init.get("result") or {}).get("agentInfo") or {}).get("_meta") or {}).get("zcode") or {}
                self.assertEqual(meta.get("plan"), "unavailable", label)
                self.assertNotIn("payg-key-must-not-be-used", json.dumps(init))
                self.assertNotIn(START_PLAN_SECRET, json.dumps(init))
                driver.request(2, "session/new", {"cwd": str(driver.cwd), "mcpServers": []})
                new = driver.wait_result(2)
                assert new is not None
                session_id = (new.get("result") or {}).get("sessionId")
                driver.request(3, "session/prompt", {
                    "sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}],
                })
                failed = driver.wait_result(3, timeout=8)
                assert failed is not None
                message = (failed.get("error") or {}).get("message", "")
                self.assertIn("HUMAN_DECISION_REQUIRED" if registry not in ("ABSENT", "{not json") else "registry", message, label)
                # Nothing was spawned, nothing forwarded, nothing written.
                self.assertFalse(driver.record_path.is_file(), label)
                self.assertNotIn("payg-key-must-not-be-used", json.dumps(driver.messages))
                self.assertNotIn(START_PLAN_SECRET, json.dumps(driver.messages))
                self.assertEqual(driver.cli_config.read_text(encoding="utf-8"), '{"hooks":{}}\n')
                self.stop_driver()

    def test_resume_is_faithful_then_reregisters_persisted_model(self) -> None:
        driver = self.start("basic")
        self.handshake(driver)
        driver.request(20, "session/load", {"sessionId": "sess_persisted1", "cwd": str(driver.cwd)})
        loaded = driver.wait_result(20, timeout=8)
        assert loaded is not None
        self.assertNotIn("error", loaded)
        resumes = driver.rpc_calls("session/resume")
        self.assertEqual(len(resumes), 1)
        self.assertNotIn("runtimeModel", resumes[0].get("params") or {})
        # The persisted model (GLM-5.3-Flash in the fake) is kept, not replaced
        # by the default, and the provider is re-registered through setModel.
        set_model = driver.rpc_calls("session/setModel")
        self.assertEqual(len(set_model), 1)
        params = set_model[0].get("params") or {}
        self.assertEqual(params.get("model"), {"providerId": CODING_PLAN_ID, "modelId": "GLM-5.3-Flash"})
        self.assertEqual((params.get("runtimeModel") or {}).get("provider", {}).get("providerId"), CODING_PLAN_ID)
        driver.request(21, "session/prompt", {
            "sessionId": "sess_persisted1", "prompt": [{"type": "text", "text": "again"}],
        })
        done = driver.wait_result(21, timeout=8)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "end_turn")
        driver.request(22, "session/list", {})
        listed = driver.wait_result(22, timeout=8)
        assert listed is not None
        sessions = (listed.get("result") or {}).get("sessions") or []
        self.assertTrue(sessions)
        for item in sessions:
            self.assertRegex(item.get("updatedAt") or "", r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        self.assertEqual(sessions[0]["updatedAt"], "2026-09-16T09:48:26.400Z")
        self.assert_registry_read_only_and_secret_contained(driver)

    def test_backend_error_echoing_the_overlay_is_redacted(self) -> None:
        driver = self.start("echo_error")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}],
        })
        failed = driver.wait_result(3, timeout=8)
        assert failed is not None
        self.assertIn("error", failed)
        blob = json.dumps(failed)
        self.assertNotIn(FIXTURE_SECRET, blob)
        self.assertIn("<redacted-credential>", blob)
        self.assert_registry_read_only_and_secret_contained(driver)

    def test_event_payloads_echoing_the_credential_are_redacted(self) -> None:
        """Outbound boundary: streaming text, tool cards and failure messages
        are backend-controlled and must be redacted like error objects."""
        driver = self.start("echo_events")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}],
        })
        done = driver.wait_result(3, timeout=8)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "refusal")
        blob = json.dumps(driver.messages)
        self.assertNotIn(FIXTURE_SECRET, blob)
        self.assertGreaterEqual(blob.count("<redacted-credential>"), 3)
        texts = [((u.get("content") or {}).get("text") or "") for u in driver.updates(session_id)
                 if u.get("sessionUpdate") == "agent_message_chunk"]
        self.assertIn("hello key=<redacted-credential> world", texts, "ordinary text is kept intact")
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") in ("tool_call", "tool_call_update")]
        self.assertTrue(tools)
        self.assertNotIn(FIXTURE_SECRET, json.dumps(tools))
        raw_inputs = [u.get("rawInput") for u in tools if u.get("rawInput") is not None]
        self.assertTrue(raw_inputs)
        self.assertTrue(all("<redacted-credential>" in json.dumps(raw) for raw in raw_inputs))
        self.assert_registry_read_only_and_secret_contained(driver)

    def test_read_file_path_is_forwarded_as_locations(self) -> None:
        """Issue #67: live 0.16.5 Read `input.file_path` must surface on ACP."""
        driver = self.start("read_path")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "read"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        self.assertTrue(tools)
        path = "/tmp/kpr-issue-67-fixture/MARKER.txt"
        for update in tools:
            self.assertEqual(update.get("rawInput"), {"file_path": path})
            self.assertEqual(update.get("locations"), [{"path": path, "line": None}])
            self.assertNotEqual(update.get("title"), path)

    def test_absent_tool_input_is_not_invented(self) -> None:
        """Issue #67: no path key on the backend means no locations/rawInput."""
        driver = self.start("no_input")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "read"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        self.assertTrue(tools)
        for update in tools:
            self.assertNotIn("rawInput", update)
            self.assertNotIn("locations", update)
            self.assertEqual(update.get("title"), "Read")

    def test_sensitive_extra_fields_are_not_forwarded(self) -> None:
        driver = self.start("sensitive_extra")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "read"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        self.assertTrue(tools)
        path = "/tmp/kpr-issue-67-fixture/MARKER.txt"
        blob = json.dumps(driver.messages)
        self.assertNotIn(FIXTURE_SECRET, blob)
        self.assertNotIn("unregistered-secret-value-abc123xyz", blob)
        self.assertNotIn("PADPAD", blob)
        for update in tools:
            raw = update.get("rawInput") or {}
            self.assertEqual(raw.get("file_path"), path)
            self.assertNotIn("contents", raw)
            self.assertNotIn("apiKey", raw)
            self.assertNotIn("extra", raw)
            self.assertNotIn("unregistered", raw)
            self.assertEqual(update.get("locations"), [{"path": path, "line": None}])
            if "command" in raw:
                self.assertIn("<redacted-credential>", str(raw["command"]))
                self.assertNotIn(FIXTURE_SECRET, str(raw["command"]))

    def test_huge_nested_input_stays_within_raw_input_bound(self) -> None:
        driver = self.start("huge_nested")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "read"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        tools = [u for u in driver.updates(session_id) if u.get("sessionUpdate") == "tool_call"]
        self.assertTrue(tools)
        module = load_adapter_module()
        for update in tools:
            raw = update.get("rawInput") or {}
            self.assertEqual(raw.get("file_path"), "/tmp/kpr-issue-67-fixture/MARKER.txt")
            self.assertNotIn("extra", raw)
            if "command" in raw:
                self.assertLessEqual(len(str(raw["command"])), module.RAW_INPUT_COMMAND_CAP + 1)
            encoded = json.dumps(raw, ensure_ascii=False).encode("utf-8")
            self.assertLessEqual(len(encoded), module.RAW_INPUT_MAX_BYTES)
            self.assertLess(len(json.dumps(update, ensure_ascii=False)), 4096)

    def test_holder_events_drop_secrets_and_stay_bounded(self) -> None:
        """Issue #67 comment 5728867515: holder persistence matches the bound."""
        self._assert_holder_events("sensitive_extra", secret=True)
        self._assert_holder_events("huge_nested", secret=False)

    def _assert_holder_events(self, scenario: str, *, secret: bool) -> None:
        turn = HolderTurn(self.tmp, scenario)
        try:
            turn.start()
            turn.send("read")
            matches = list(turn.record_dir.rglob("events.jsonl"))
            self.assertEqual(len(matches), 1, f"holder events.jsonl missing under {turn.record_dir}")
            events_path = matches[0]
            turn.record_dir = events_path.parent
            blob = events_path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn(FIXTURE_SECRET, blob)
            self.assertNotIn("unregistered-secret-value-abc123xyz", blob)
            self.assertNotIn("PADPAD", blob)
            self.assertLess(events_path.stat().st_size, 256_000)
            tool_lines = []
            for line in blob.splitlines():
                if "tool_call" not in line:
                    continue
                self.assertLess(len(line), 8192, "a persisted tool_call event stayed bounded")
                tool_lines.append(line)
            self.assertTrue(tool_lines)
            if secret:
                self.assertIn("MARKER.txt", blob)
            record = turn.record_dir / "record.json"
            if record.is_file():
                self.assertNotIn(FIXTURE_SECRET, record.read_text(encoding="utf-8", errors="replace"))
        finally:
            turn.stop()

    def test_failed_load_leaves_no_half_registered_session(self) -> None:
        driver = self.start("resume_missing")
        self.handshake(driver)
        driver.request(20, "session/load", {"sessionId": "sess_gone", "cwd": str(driver.cwd)})
        first = driver.wait_result(20, timeout=8)
        assert first is not None
        self.assertIn("error", first)
        driver.request(21, "session/load", {"sessionId": "sess_gone", "cwd": str(driver.cwd)})
        second = driver.wait_result(21, timeout=8)
        assert second is not None
        self.assertIn("error", second, "a retried load must not succeed silently")
        driver.request(22, "session/prompt", {
            "sessionId": "sess_gone", "prompt": [{"type": "text", "text": "hello"}],
        })
        prompt = driver.wait_result(22, timeout=8)
        assert prompt is not None
        self.assertIn("error", prompt)
        self.assertEqual(driver.rpc_calls("session/create"), [], "no silent new session")

    def test_resume_falls_back_to_overlay_when_backend_requires_it(self) -> None:
        driver = self.start("resume_needs_overlay")
        self.handshake(driver)
        driver.request(20, "session/load", {"sessionId": "sess_persisted2", "cwd": str(driver.cwd)})
        loaded = driver.wait_result(20, timeout=8)
        assert loaded is not None
        self.assertNotIn("error", loaded)
        resumes = driver.rpc_calls("session/resume")
        self.assertEqual(len(resumes), 2)
        self.assertNotIn("runtimeModel", resumes[0].get("params") or {})
        overlay = (resumes[1].get("params") or {}).get("runtimeModel") or {}
        self.assertEqual(overlay.get("provider", {}).get("providerId"), CODING_PLAN_ID)
        driver.request(21, "session/prompt", {
            "sessionId": "sess_persisted2", "prompt": [{"type": "text", "text": "again"}],
        })
        done = driver.wait_result(21, timeout=8)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "end_turn")
        self.assert_registry_read_only_and_secret_contained(driver)

    def test_resume_with_unknown_persisted_model_fails_closed(self) -> None:
        driver = self.start("read_fails")
        self.handshake(driver)
        driver.request(20, "session/load", {"sessionId": "sess_persisted3", "cwd": str(driver.cwd)})
        loaded = driver.wait_result(20, timeout=8)
        assert loaded is not None
        self.assertIn("refusing to substitute", (loaded.get("error") or {}).get("message", ""))
        self.assertEqual(driver.rpc_calls("session/setModel"), [], "no default model substituted")
        driver.request(21, "session/load", {"sessionId": "sess_persisted3", "cwd": str(driver.cwd)})
        again = driver.wait_result(21, timeout=8)
        assert again is not None
        self.assertIn("error", again)

    def test_cancel_sends_stop_as_a_request(self) -> None:
        driver = self.start("slow")
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "slow"}],
        })
        driver.wait_for(lambda msg: msg.get("method") == "session/update", timeout=8)
        driver.send({"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session_id}})
        done = driver.wait_result(3, timeout=8)
        assert done is not None
        self.assertEqual((done.get("result") or {}).get("stopReason"), "cancelled")
        stops = driver.rpc_calls("session/stop")
        self.assertEqual(len(stops), 1)
        self.assertIsNotNone(stops[0].get("id"), "session/stop must carry a request id")


    def test_forwards_runner_internal_env_facts_but_never_credentials(self) -> None:
        child_record = self.tmp / "outer-children.jsonl"
        driver = self.start(
            "basic",
            extra_env={
                "KAOLA_ACP_CHILD_RECORD": str(child_record),
                "KAOLA_ZCODE_ENTRY": "/tmp/kaola-zcode-explicit-entry.cjs",
                "KAOLA_ZCODE_NODE": "/usr/bin/env python3",
            },
        )
        session_id = self.handshake(driver)
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        record = wait_for(lambda: driver.record() or None, 3)
        self.assertIsNotNone(record)
        assert record is not None
        # Explicit ZCode runtime facts pass to a nested ZCode child (Issue #62
        # reuse); the explicit credential names never travel.
        env_names = record.get("env_names") or []
        self.assertIn("KAOLA_ZCODE_ENTRY", env_names)
        self.assertIn("KAOLA_ZCODE_NODE", env_names)
        leaked = [name for name in DENIED_ENV if name in env_names]
        self.assertEqual(leaked, [])
        # Trust boundary: the holder's child-record path is a write handle to a
        # holder record and must never reach an external agent child.
        self.assertNotIn("KAOLA_ACP_CHILD_RECORD", env_names)
        self.assertNotIn(FIXTURE_SECRET, json.dumps(driver.messages))
        self.assertFalse(child_record.exists(), "no child was spawned by a bare prompt")

    def test_native_session_identity_and_load_result(self) -> None:
        driver = self.start("basic")
        session_id = self.handshake(driver)
        # Materialize is lazy: the identity update appears on the first prompt.
        driver.request(3, "session/prompt", {
            "sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}],
        })
        done = driver.wait_result(3, timeout=8)
        self.assertIsNotNone(done)
        identities = [
            update for update in driver.updates(session_id)
            if update.get("sessionUpdate") == "native_session_identity"
        ]
        self.assertEqual(len(identities), 1, identities)
        self.assertNotIn(FIXTURE_SECRET, json.dumps(identities))
        payload = identities[0]
        self.assertEqual(payload.get("acpSessionId"), session_id)
        self.assertTrue(str(payload.get("nativeSessionId") or "").startswith("sess_"))
        # session/load adopts the native id and returns it plus config options.
        driver.request(20, "session/load", {"sessionId": "sess_persisted1", "cwd": str(driver.cwd)})
        loaded = driver.wait_result(20, timeout=8)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertNotIn("error", loaded)
        result = loaded.get("result") or {}
        self.assertEqual(result.get("sessionId"), "sess_persisted1")
        option_ids = {item.get("id") for item in result.get("configOptions") or []}
        self.assertIn("mode", option_ids)
        self.assertIn("model", option_ids)
        # A faithful resume re-emits the credential-free identity for the
        # loaded native id.
        resumed = [
            update for update in driver.updates("sess_persisted1")
            if update.get("sessionUpdate") == "native_session_identity"
        ]
        self.assertTrue(resumed)
        self.assertEqual(resumed[-1].get("nativeSessionId"), "sess_persisted1")
        self.assertNotIn(FIXTURE_SECRET, json.dumps(driver.messages))
        self.assert_registry_read_only_and_secret_contained(driver)


if __name__ == "__main__":
    unittest.main()
