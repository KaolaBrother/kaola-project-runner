#!/usr/bin/env python3
"""Issue #50 Mission 1: offline acceptance for the vendored Claude Code ACP bridge.

No network, no account, no real `claude`: `CLAUDE_BIN` points at
`fake-claude.py`, which records argv, cwd, process group, and environment
variable names (never values). Every bridge process runs with a sandbox HOME,
its own state and runtime directories, credential variables that must be
stripped, an unrelated canary variable that must survive, and a PATH whose
first `claude` is a trap that must never run.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "claude-code-acp"
BIN = VENDOR / "bin" / "claude-code-acp.js"
DIST = VENDOR / "dist" / "index.js"
FAKE = ROOT / "tests" / "contract" / "fake-claude.py"
UPSTREAM_COMMIT = "6c20f2802e390c80b0542247c6b9738e11efdc11"
UPSTREAM_URL = "https://github.com/harukitosa/claude-code-acp"
UPSTREAM_LICENSE_SHA256 = "9aef7c953434dde57dc0e9f7b596651b7e2353ef2e4b04470eb8bb8238d37443"
NODE_BUILTINS = {
    "assert", "buffer", "child_process", "crypto", "events", "fs", "http", "https", "net",
    "os", "path", "process", "readline", "stream", "string_decoder", "timers", "tty", "url",
    "util", "worker_threads", "zlib", "module",
}
NODE = shutil.which("node")
PYTHON = sys.executable or shutil.which("python3")

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pid_alive(pid: int) -> bool:
    out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(out) and not out.startswith("Z")


def wait_until(predicate, timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timeout: {label}")


def read_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class Sandbox:
    """One isolated environment per bridge process."""

    def __init__(self, name: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-acp-{name}-"))
        self.home = self.dir / "home"
        self.state = self.dir / "state"
        self.runtime = self.dir / "runtime"
        self.repo = self.dir / "repo"
        self.trap_dir = self.dir / "path-trap"
        self.trap_hit = self.dir / "path-trap-hit"
        for path in (self.home, self.state, self.runtime, self.repo, self.trap_dir):
            path.mkdir(parents=True)
        trap = self.trap_dir / "claude"
        trap.write_text(f"#!/bin/sh\ntouch '{self.trap_hit}'\nexit 97\n")
        trap.chmod(trap.stat().st_mode | stat.S_IXUSR)
        self.record = self.dir / "record.jsonl"
        self.canary = f"canary-{uuid.uuid4()}"
        self.api_key = f"fake-api-key-{uuid.uuid4()}"
        self.auth_token = f"fake-auth-token-{uuid.uuid4()}"

    def env(self, **overrides: str | None) -> dict[str, str]:
        base = {
            "PATH": f"{self.trap_dir}:{os.environ.get('PATH', '')}",
            "HOME": str(self.home),
            "TMPDIR": str(self.dir),
            "LANG": os.environ.get("LANG", "C"),
            "CLAUDE_ACP_STATE_DIR": str(self.state),
            "CLAUDE_ACP_RUNTIME_DIR": str(self.runtime),
            "CLAUDE_BIN": str(FAKE),
            "FAKE_CLAUDE_RECORD": str(self.record),
            "KAOLA_FAKE_CANARY": self.canary,
            "ANTHROPIC_API_KEY": self.api_key,
            "ANTHROPIC_AUTH_TOKEN": self.auth_token,
            "LOG_LEVEL": "debug",
        }
        for key, value in overrides.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        return base

    def records(self) -> list[dict]:
        return read_records(self.record)

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class Bridge:
    """Minimal ACP client over the bridge's stdio."""

    def __init__(self, sandbox: Sandbox, entry: Path = BIN, **env_overrides: str | None):
        self.sandbox = sandbox
        self.stderr_path = sandbox.dir / f"stderr-{uuid.uuid4().hex[:6]}.log"
        self.stderr_file = open(self.stderr_path, "wb")
        self.proc = subprocess.Popen(
            [NODE, str(entry)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr_file,
            cwd=str(sandbox.repo), env=sandbox.env(**env_overrides), start_new_session=True,
        )
        self.next_id = 0
        self.responses: dict[int, dict] = {}
        self.incoming: queue.Queue = queue.Queue()
        self.updates: list[dict] = []
        self.lock = threading.Condition()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        for raw in self.proc.stdout:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "method" in message and "id" in message:
                self.incoming.put(message)
            elif "method" in message:
                if message["method"] == "session/update":
                    self.updates.append(message["params"])
            else:
                with self.lock:
                    self.responses[message["id"]] = message
                    self.lock.notify_all()

    def send(self, message: dict) -> None:
        self.proc.stdin.write((json.dumps(message) + "\n").encode())
        self.proc.stdin.flush()

    def request_async(self, method: str, params: dict) -> int:
        self.next_id += 1
        request_id = self.next_id
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        return request_id

    def wait(self, request_id: int, timeout: float = 20.0) -> dict:
        deadline = time.monotonic() + timeout
        with self.lock:
            while request_id not in self.responses:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f"no response for request {request_id}")
                self.lock.wait(remaining)
            return self.responses.pop(request_id)

    def request(self, method: str, params: dict, timeout: float = 20.0) -> dict:
        return self.wait(self.request_async(method, params), timeout)

    def result(self, method: str, params: dict, timeout: float = 20.0) -> dict:
        response = self.request(method, params, timeout)
        if "error" in response:
            raise AssertionError(f"{method} failed: {response['error']}")
        return response["result"]

    def error(self, method: str, params: dict) -> dict:
        response = self.request(method, params)
        if "error" not in response:
            raise AssertionError(f"{method} unexpectedly succeeded: {response.get('result')}")
        return response["error"]

    def notify(self, method: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def respond(self, request_id, result: dict) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def next_incoming(self, timeout: float = 10.0) -> dict:
        try:
            return self.incoming.get(timeout=timeout)
        except queue.Empty as exc:
            raise AssertionError("no agent request arrived") from exc

    def initialize(self) -> dict:
        return self.result("initialize", {
            "protocolVersion": 1, "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False},
            "clientInfo": {"name": "kaola-harness", "version": "1"},
        })

    def new_session(self, cwd: Path | None = None, mcp_servers: list | None = None) -> dict:
        return self.result("session/new", {"cwd": str(cwd or self.sandbox.repo), "mcpServers": mcp_servers or []})

    def configure(self, session_id: str, **options: str) -> None:
        for config_id, value in options.items():
            self.result("session/set_config_option", {"sessionId": session_id, "configId": config_id, "value": value})

    def prompt(self, session_id: str, text: str) -> dict:
        return self.result("session/prompt", {"sessionId": session_id, "prompt": [{"type": "text", "text": text}]}, 30.0)

    def stop(self, timeout: float = 8.0) -> int:
        """Close the client side of stdio like the holder's stop does."""
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            code = self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            raise AssertionError("bridge did not exit after stdin closed")
        self.stderr_file.close()
        return code

    def stderr(self) -> str:
        if not self.stderr_file.closed:
            self.stderr_file.flush()
        return self.stderr_path.read_text(errors="replace")


def argv_value(argv: list[str], flag: str) -> str | None:
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return None


def ids_of(bridge: Bridge, update_kind: str) -> list[dict]:
    return [u["update"] for u in bridge.updates if u.get("update", {}).get("sessionUpdate") == update_kind]


# --------------------------------------------------------------------------- tests


def test_provenance() -> None:
    check(sha256(VENDOR / "LICENSE") == UPSTREAM_LICENSE_SHA256, "LICENSE is the upstream MIT file verbatim")
    notice = (VENDOR / "UPSTREAM.md").read_text()
    check(UPSTREAM_URL in notice and UPSTREAM_COMMIT in notice and "MIT" in notice, "UPSTREAM.md names url, pinned commit, MIT")
    check("## Local modifications" in notice, "UPSTREAM.md enumerates local modifications")
    rows = re.findall(r"^\| `([^`]+)` \| (verbatim|modified|omitted) \| `([0-9a-f]{64})` \|$", notice, re.M)
    check(len(rows) >= 40, "UPSTREAM.md carries the upstream file inventory")
    inventoried = set()
    for path, status, upstream_hash in rows:
        target = VENDOR / path
        inventoried.add(path)
        if status == "omitted":
            check(not target.exists(), f"omitted upstream file absent: {path}")
        elif status == "verbatim":
            check(target.is_file() and sha256(target) == upstream_hash, f"verbatim upstream file unchanged: {path}")
        else:
            check(target.is_file() and sha256(target) != upstream_hash, f"modified upstream file differs: {path}")
    listed_modified = {p for p, s, _ in rows if s == "modified"}
    for line in notice.splitlines():
        for path in re.findall(r"`((?:src|tests)/[A-Za-z0-9._-]+|tsup\.config\.ts|\.gitignore)`", line):
            if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")) and path in inventoried:
                check(path in listed_modified, f"modification list entry is inventoried as modified: {path}")
    package = json.loads((VENDOR / "package.json").read_text())
    check(package["name"] == "claude-code-acp" and list(package["dependencies"]) == ["@agentclientprotocol/sdk"], "package.json runtime dependency is only the ACP SDK")
    lock = json.loads((VENDOR / "package-lock.json").read_text())
    check(lock["packages"]["node_modules/@agentclientprotocol/sdk"]["version"] == "0.16.1", "lock pins @agentclientprotocol/sdk 0.16.1")
    for path in ("platforms", "scripts", "docs", "README.md"):
        for file in ([ROOT / path] if (ROOT / path).is_file() else (ROOT / path).rglob("*")):
            if file.is_file() and file.suffix in (".yaml", ".py", ".sh", ".md"):
                text = file.read_text(errors="replace")
                check("npx claude-code-acp" not in text and "npm install -g claude-code-acp" not in text, f"no registry install reference: {file.relative_to(ROOT)}")
    result = subprocess.run([PYTHON, str(VENDOR / "kaola-dist.py"), "--check"], capture_output=True, text=True)
    check(result.returncode == 0, f"kaola-dist.py --check passes: {result.stdout.strip()} {result.stderr.strip()}")
    ignore = (VENDOR / ".gitignore").read_text()
    check("node_modules/" in ignore and "dist/" not in ignore.replace("dist/DERIVATION", ""), "vendor .gitignore excludes node_modules and commits dist")


def test_dist_self_contained() -> None:
    text = DIST.read_text()
    specifiers = set(re.findall(r'\bfrom\s*"([^"]+)"', text)) | set(re.findall(r'\brequire\("([^"]+)"\)', text)) | set(re.findall(r'\bimport\("([^"]+)"\)', text))
    external = {s for s in specifiers if s.removeprefix("node:") not in NODE_BUILTINS}
    check(not external, f"dist imports only node builtins (found: {sorted(external)})")
    check("registry.npmjs.org" not in text and "npx" not in text.split("\n", 1)[0], "dist carries no registry reference")
    sandbox = Sandbox("selfcontained")
    try:
        island = sandbox.dir / "island"
        (island / "dist").mkdir(parents=True)
        (island / "bin").mkdir()
        shutil.copy(DIST, island / "dist" / "index.js")
        shutil.copy(BIN, island / "bin" / "claude-code-acp.js")
        bridge = Bridge(sandbox, entry=island / "bin" / "claude-code-acp.js")
        init = bridge.initialize()
        check(init["agentInfo"]["name"] == "claude-code-acp" and init["protocolVersion"] == 1, "island copy (bin+dist only, no node_modules) initializes")
        caps = init["agentCapabilities"]["sessionCapabilities"]
        check("list" in caps and "resume" in caps, "agent advertises session list and resume")
        session = bridge.new_session()
        bridge.prompt(session["sessionId"], "island")
        check(sandbox.records()[0]["argv0"] == str(FAKE.resolve()), "island copy spawned the exact CLAUDE_BIN")
        check(bridge.stop() == 0, "island bridge exits 0 on stdin close")
    finally:
        sandbox.cleanup()


def test_turns_flags_env_cwd_logs() -> None:
    sandbox = Sandbox("turns")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        session = bridge.new_session()
        sid = session["sessionId"]
        option_ids = {o["id"] for o in session["configOptions"]}
        check({"mode", "model", "effort", "fast"} <= option_ids, "session/new advertises mode, model, effort, fast")
        check(session["modes"]["currentModeId"] == "bypassPermissions", "default session mode is bypassPermissions")
        bridge.configure(sid, model="fable", effort="high", mode="bypassPermissions", fast="off")
        first = bridge.prompt(sid, "hello one")
        check(first["stopReason"] == "end_turn", "first prompt ends the turn")
        chunks = [u["content"]["text"] for u in ids_of(bridge, "agent_message_chunk")]
        check("echo:hello one" in chunks, "assistant text is relayed as agent_message_chunk")
        rec = sandbox.records()
        check(len(rec) == 1, "first turn spawned exactly one claude process")
        r1 = rec[0]
        argv = r1["argv"]
        check(r1["argv0"] == str(FAKE.resolve()), "spawned binary is the exact CLAUDE_BIN path")
        check(argv_value(argv, "-p") == "hello one", "prompt travels as -p <prompt>")
        check(argv_value(argv, "--output-format") == "stream-json" and "--verbose" in argv, "stream-json verbose output")
        check(argv_value(argv, "--model") == "fable", "first turn carries --model fable")
        check(argv_value(argv, "--effort") == "high", "first turn carries --effort high")
        check(argv_value(argv, "--permission-mode") == "bypassPermissions", "first turn carries --permission-mode bypassPermissions")
        check(json.loads(argv_value(argv, "--settings")) == {"fastMode": False}, "fast off pins --settings fastMode=false")
        check("--dangerously-skip-permissions" not in argv, "no --dangerously-skip-permissions once a permission mode governs")
        check("--resume" not in argv, "first turn has no --resume")
        check(Path(r1["cwd"]).resolve() == sandbox.repo.resolve(), "claude runs in the session cwd")
        check(r1["has_api_key"] is False and r1["has_auth_token"] is False, "ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN stripped from the child env")
        check(r1["canary"] == sandbox.canary, "unrelated inherited variable reaches the child untouched")
        check({"HOME", "PATH", "CLAUDE_BIN"} <= set(r1["env_keys"]), "HOME, PATH, CLAUDE_BIN inherited by the child")
        check(r1["pgid"] == r1["pid"], "claude is its own process-group leader")
        second = bridge.prompt(sid, "hello two")
        check(second["stopReason"] == "end_turn", "second prompt ends the turn")
        r2 = sandbox.records()[1]
        check(argv_value(r2["argv"], "--resume") == r1["session_id"], "second turn resumes the Claude session id returned by the first")
        check(argv_value(r2["argv"], "--model") == "fable" and argv_value(r2["argv"], "--effort") == "high" and argv_value(r2["argv"], "--permission-mode") == "bypassPermissions", "second turn repeats model, effort, permission mode")
        check(Path(r2["cwd"]).resolve() == sandbox.repo.resolve(), "resume turn keeps the session cwd")
        bridge.configure(sid, fast="on", model="opus", effort="max")
        bridge.prompt(sid, "hello three")
        r3 = sandbox.records()[2]
        check(json.loads(argv_value(r3["argv"], "--settings")) == {"fastMode": True}, "fast on pins --settings fastMode=true")
        check(argv_value(r3["argv"], "--model") == "opus" and argv_value(r3["argv"], "--effort") == "max", "changed model and effort apply on the next turn")
        bridge.result("session/set_mode", {"sessionId": sid, "modeId": "plan"})
        bridge.prompt(sid, "hello four")
        check(argv_value(sandbox.records()[3]["argv"], "--permission-mode") == "plan", "session/set_mode maps to --permission-mode")
        for config_id, value in (("effort", "bogus"), ("mode", "yolo"), ("fast", "maybe"), ("model", "-x"), ("thought_level", "high")):
            err = bridge.error("session/set_config_option", {"sessionId": sid, "configId": config_id, "value": value})
            check(err["code"] == -32602, f"invalid config {config_id}={value} rejected with invalid params")
        err = bridge.error("session/set_mode", {"sessionId": sid, "modeId": "architect"})
        check(err["code"] == -32602, "unknown session mode rejected")
        check(bridge.stop() == 0, "bridge exits 0 on stdin close")
        log = bridge.stderr()
        check("spawn streaming: claude" in log and "<session-id>" in log and "<prompt:" in log, "debug log masks --resume id and prompt")
        for secret, label in ((r1["session_id"], "raw Claude session id"), (sandbox.canary, "inherited env value"), (sandbox.api_key, "API key value"), (sandbox.auth_token, "auth token value")):
            check(secret not in log, f"bridge log never prints {label}")
        check(not sandbox.trap_hit.exists(), "PATH claude trap never executed")
        state = json.loads((sandbox.state / "sessions.json").read_text())
        check(state["version"] == 2 and r1["session_id"] in state["sessions"], "session record lives under CLAUDE_ACP_STATE_DIR")
        check(not (sandbox.home / ".claude-code-acp").exists(), "nothing written to HOME when a state dir is set")
        for record in sandbox.records():
            check(record["pid"] and not pid_alive(record["pid"]), f"claude pid {record['pid']} exited")
    finally:
        sandbox.cleanup()


def test_cwd_validation() -> None:
    sandbox = Sandbox("cwd")
    try:
        other = sandbox.dir / "other-repo"
        other.mkdir()
        bridge = Bridge(sandbox)
        bridge.initialize()
        err = bridge.error("session/new", {"cwd": "relative/path", "mcpServers": []})
        check(err["code"] == -32602, "relative cwd rejected")
        err = bridge.error("session/new", {"cwd": str(sandbox.dir / "missing"), "mcpServers": []})
        check(err["code"] == -32602, "missing cwd rejected")
        session = bridge.new_session(other)
        bridge.prompt(session["sessionId"], "where")
        check(Path(sandbox.records()[0]["cwd"]).resolve() == other.resolve(), "claude runs in the per-session cwd")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_permission_roundtrip() -> None:
    sandbox = Sandbox("permission")
    try:
        bridge = Bridge(sandbox, FAKE_CLAUDE_MODE="permission")
        bridge.initialize()
        sid = bridge.new_session()["sessionId"]
        request_id = bridge.request_async("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "needs permission"}]})
        incoming = bridge.next_incoming()
        check(incoming["method"] == "session/request_permission", "bridge forwards permission_request as session/request_permission")
        options = {o["optionId"] for o in incoming["params"]["options"]}
        check({"allow_once", "reject_once"} <= options, "permission options include allow/reject")
        tool_call_id = incoming["params"]["toolCall"]["toolCallId"]
        bridge.respond(incoming["id"], {"outcome": {"outcome": "selected", "optionId": "allow_once"}})
        response = bridge.wait(request_id, 30.0)
        check(response.get("result", {}).get("stopReason") == "end_turn", "prompt completes after permit")
        statuses = [u["status"] for u in ids_of(bridge, "tool_call") if u["toolCallId"] == tool_call_id]
        check(statuses[:1] == ["pending"] and statuses[-1] == "completed", "tool_call goes pending then completed on allow")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_cancel_kills_process_group() -> None:
    sandbox = Sandbox("cancel")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        sid = bridge.new_session()["sessionId"]
        request_id = bridge.request_async("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "[hang] long task"}]})
        wait_until(lambda: bool(sandbox.records()) and "grandchild_pid" in sandbox.records()[0], 10.0, "hanging claude recorded")
        rec = sandbox.records()[0]
        pid, grandchild = rec["pid"], rec["grandchild_pid"]
        check(pid_alive(pid) and pid_alive(grandchild), "claude and its grandchild are alive before cancel")
        bridge.notify("session/cancel", {"sessionId": sid})
        response = bridge.wait(request_id, 15.0)
        check(response.get("result", {}).get("stopReason") == "cancelled", "cancelled prompt reports stopReason=cancelled")
        wait_until(lambda: not pid_alive(pid) and not pid_alive(grandchild), 6.0, "process group dead after cancel")
        check(True, "cancel kills claude and its grandchild (whole process group)")
        follow = bridge.prompt(sid, "after cancel")
        check(follow["stopReason"] == "end_turn", "session stays usable after cancel")
        check(argv_value(sandbox.records()[1]["argv"], "--resume") == rec["session_id"], "turn after cancel resumes the same Claude session")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_stop_during_turn_cleans_everything() -> None:
    sandbox = Sandbox("stop")
    try:
        bridge = Bridge(sandbox, FAKE_CLAUDE_MODE="hang")
        bridge.initialize()
        servers = [{"name": "fake-mcp", "command": "python3", "args": ["-c", "pass"], "env": [{"name": "MCP_FAKE", "value": "1"}]}]
        sid = bridge.new_session(mcp_servers=servers)["sessionId"]
        bridge.request_async("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "hang with mcp"}]})
        wait_until(lambda: bool(sandbox.records()) and "grandchild_pid" in sandbox.records()[0], 10.0, "hanging claude recorded")
        rec = sandbox.records()[0]
        mcp_path = rec["mcp_config"]
        check(mcp_path and rec["mcp_config_exists"] and Path(mcp_path).is_relative_to(sandbox.runtime), "MCP temp config written under CLAUDE_ACP_RUNTIME_DIR for the turn")
        check(json.loads(Path(mcp_path).read_text())["mcpServers"]["fake-mcp"]["env"] == {"MCP_FAKE": "1"}, "ACP stdio MCP shape translated into claude mcp.json")
        code = bridge.stop()
        check(code == 0, "bridge exits 0 when stdin closes mid-turn")
        wait_until(lambda: not pid_alive(rec["pid"]) and not pid_alive(rec["grandchild_pid"]), 6.0, "children dead after stop")
        check(True, "stop mid-turn kills claude and its grandchild")
        check(not Path(mcp_path).exists() and not list(sandbox.runtime.glob("claude-acp-mcp-*")), "no MCP temp file survives stop")
    finally:
        sandbox.cleanup()


def test_missing_binary_fails_closed() -> None:
    sandbox = Sandbox("missing")
    try:
        cases = {
            "missing absolute path": str(sandbox.dir / "no-such-claude"),
            "relative name": "claude",
            "directory": str(sandbox.dir),
        }
        plain = sandbox.dir / "not-executable"
        plain.write_text("#!/bin/sh\nexit 0\n")
        plain.chmod(0o644)
        cases["non-executable file"] = str(plain)
        for label, value in cases.items():
            bridge = Bridge(sandbox, CLAUDE_BIN=value)
            bridge.initialize()
            err = bridge.error("session/new", {"cwd": str(sandbox.repo), "mcpServers": []})
            check(err["code"] == -32603 and "CLAUDE_BIN" in err["message"], f"CLAUDE_BIN {label}: session/new fails closed")
            err = bridge.error("session/resume", {"sessionId": str(uuid.uuid4()), "cwd": str(sandbox.repo), "mcpServers": []})
            check(err["code"] == -32603, f"CLAUDE_BIN {label}: session/resume fails closed")
            bridge.stop()
        bridge = Bridge(sandbox, CLAUDE_ACP_CLAUDE_BIN=str(sandbox.dir / "absent"))
        bridge.initialize()
        err = bridge.error("session/new", {"cwd": str(sandbox.repo), "mcpServers": []})
        check(err["code"] == -32603, "CLAUDE_ACP_CLAUDE_BIN overrides CLAUDE_BIN and fails closed when absent")
        bridge.stop()
        check(not sandbox.trap_hit.exists() and not sandbox.records(), "no PATH fallback: neither the trap nor the fake ran")
    finally:
        sandbox.cleanup()


def test_concurrent_session_isolation() -> None:
    sandbox = Sandbox("isolation")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        a = bridge.new_session()["sessionId"]
        b = bridge.new_session()["sessionId"]
        check(a != b, "two sessions in one bridge get distinct ACP ids")
        bridge.prompt(a, "a1")
        bridge.prompt(b, "b1")
        rec = sandbox.records()
        ida, idb = rec[0]["session_id"], rec[1]["session_id"]
        check(ida != idb and "--resume" not in rec[0]["argv"] and "--resume" not in rec[1]["argv"], "each session starts its own Claude conversation")
        bridge.prompt(a, "a2")
        bridge.prompt(b, "b2")
        rec = sandbox.records()
        check(argv_value(rec[2]["argv"], "--resume") == ida and argv_value(rec[3]["argv"], "--resume") == idb, "each session resumes only its own Claude conversation")
        bridge.stop()
        fresh = Bridge(sandbox)
        fresh.initialize()
        fresh.prompt(fresh.new_session()["sessionId"], "fresh")
        check("--resume" not in sandbox.records()[4]["argv"], "a new bridge without ACPX_SESSION_NAME does not silently continue the previous conversation in the same cwd")
        fresh.stop()
    finally:
        sandbox.cleanup()


def test_named_continuity_list_and_resume() -> None:
    sandbox = Sandbox("resume")
    try:
        named = Bridge(sandbox, ACPX_SESSION_NAME="alpha")
        named.initialize()
        named.prompt(named.new_session()["sessionId"], "named one")
        named_id = sandbox.records()[0]["session_id"]
        named.stop()
        again = Bridge(sandbox, ACPX_SESSION_NAME="alpha")
        again.initialize()
        again.prompt(again.new_session()["sessionId"], "named two")
        check(argv_value(sandbox.records()[1]["argv"], "--resume") == named_id, "ACPX_SESSION_NAME continues the named conversation across bridge processes")
        again.stop()
        plain = Bridge(sandbox)
        plain.initialize()
        listed = plain.result("session/list", {"cwd": str(sandbox.repo)})["sessions"]
        entry = next((s for s in listed if s["sessionId"] == named_id), None)
        check(entry is not None and Path(entry["cwd"]).resolve() == sandbox.repo.resolve() and entry.get("updatedAt"), "session/list offers the persisted Claude session with cwd and updatedAt")
        check(not plain.result("session/list", {"cwd": str(sandbox.dir)})["sessions"], "session/list filters by cwd")
        resumed = plain.result("session/resume", {"sessionId": named_id, "cwd": str(sandbox.repo), "mcpServers": []})
        check(resumed["sessionId"] == named_id and resumed["modes"]["currentModeId"] == "bypassPermissions", "session/resume binds the Claude session id")
        plain.configure(named_id, model="fable", effort="high")
        plain.prompt(named_id, "resumed")
        r = sandbox.records()[2]
        check(argv_value(r["argv"], "--resume") == named_id and argv_value(r["argv"], "--model") == "fable" and argv_value(r["argv"], "--effort") == "high", "resumed session runs --resume with the per-session model and effort")
        err = plain.error("session/resume", {"sessionId": "not-a-claude-id", "cwd": str(sandbox.repo), "mcpServers": []})
        check(err["code"] == -32002, "session/resume with an unknown non-UUID id is not found")
        plain.stop()
        check(sandbox.api_key not in (sandbox.state / "sessions.json").read_text(), "state file holds no credential value")
    finally:
        sandbox.cleanup()


def main() -> int:
    if not NODE:
        print("test-issue-50: node is required on PATH", file=sys.stderr)
        return 1
    for path in (BIN, DIST, FAKE, VENDOR / "LICENSE", VENDOR / "UPSTREAM.md", VENDOR / "dist" / "DERIVATION.json"):
        if not path.is_file():
            print(f"test-issue-50: missing {path}", file=sys.stderr)
            return 1
    tests = [
        test_provenance,
        test_dist_self_contained,
        test_turns_flags_env_cwd_logs,
        test_cwd_validation,
        test_permission_roundtrip,
        test_cancel_kills_process_group,
        test_stop_during_turn_cleans_everything,
        test_missing_binary_fails_closed,
        test_concurrent_session_isolation,
        test_named_continuity_list_and_resume,
    ]
    failures = 0
    for test in tests:
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report every test, then fail
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"test-issue-50: {len(CHECKS)} checks, {len(tests) - failures}/{len(tests)} tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
