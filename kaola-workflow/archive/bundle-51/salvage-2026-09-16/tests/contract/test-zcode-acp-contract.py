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
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
ADAPTER = PROJECT / "scripts" / "kaola-zcode-acp.py"
FAKE = PROJECT / "tests" / "contract" / "fake-zcode-app-server.py"
PROBE = PROJECT / "tests" / "contract" / "hooks" / "zcode-probe"
UPSTREAM = PROJECT / "third_party" / "zcode-acp" / "UPSTREAM.md"

FORBIDDEN_IMPORTS = {
    "socket", "ssl", "http", "httpx", "urllib", "requests", "aiohttp",
    "websockets", "sqlite3", "sqlite",
}
FORBIDDEN_OPEN_MARKERS = (
    "/.zcode/",
    "credentials.json",
    "setting.json",
    "tasks-index.sqlite",
    "zcode-acp/config.json",
)
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
        (self.home / ".config" / "zcode-acp").mkdir(parents=True, exist_ok=True)
        (self.home / ".zcode" / "v2" / "config.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "credentials.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "setting.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "tasks-index.sqlite").write_bytes(b"")
        (self.home / ".config" / "zcode-acp" / "config.json").write_text("{}\n", encoding="utf-8")
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

    def start(self, scenario: str = "basic", extra_env: dict[str, str] | None = None) -> AdapterDriver:
        self.driver = AdapterDriver(self.tmp, scenario=scenario, extra_env=extra_env)
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
        driver.request(4, "session/close", {"sessionId": session_id})
        closed = driver.wait_result(4)
        self.assertIsNotNone(closed)

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
            "sessionId": session_id, "configId": "model", "value": "builtin:zai-coding-plan\\other-model",
        })
        model_ok = driver.wait_result(4, timeout=8)
        self.assertIsNotNone(model_ok)
        assert model_ok is not None
        self.assertNotIn("error", model_ok)
        set_model = driver.rpc_calls("session/setModel")
        self.assertTrue(set_model)
        payload = json.dumps(set_model[-1])
        self.assertNotIn("apiKey", payload)
        self.assertNotIn("runtimeModel", payload)
        self.assertFalse((set_model[-1].get("params") or {}).get("persistAsWorkspaceLastUsed"))
        driver.request(5, "session/set_config_option", {
            "sessionId": session_id, "configId": "model", "value": "no-such-model",
        })
        rejected = driver.wait_result(5, timeout=8)
        self.assertIsNotNone(rejected)
        assert rejected is not None
        self.assertIn("error", rejected)
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
        driver.request(2, "authenticate", {"methodId": "anything"})
        auth = driver.wait_result(2)
        self.assertIsNotNone(auth)
        assert auth is not None
        self.assertEqual(auth.get("result"), {})
        self.assertFalse(driver.record_path.is_file())


if __name__ == "__main__":
    unittest.main()
