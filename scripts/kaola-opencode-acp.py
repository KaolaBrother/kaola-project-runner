#!/usr/bin/env python3
"""Add one steer entry to native OpenCode V2 ACP. Keep native stream ownership.

The local plugin uses the installed V2 session.prompt API. No second ACP
prompt, cancellation, endpoint discovery, or automatic retry is used.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading


class Adapter:
    def __init__(self, child, endpoint):
        self.child = child
        self.endpoint = endpoint
        self.lock = threading.RLock()
        self.output_lock = threading.Lock()
        self.active = {}  # exact session -> original ACP prompt request id
        self.pending = {}

    def emit(self, message):
        with self.output_lock:
            print(json.dumps(message, ensure_ascii=False), flush=True)

    def native_output(self):
        for line in self.child.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                # Preserve native stdout; holder owns malformed-line evidence.
                with self.output_lock:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                continue
            with self.lock:
                key = str(message.get("id"))
                if "method" not in message and key in self.pending:
                    session = self.pending.pop(key)
                    if str(self.active.get(session)) == key:
                        self.active.pop(session, None)
                if isinstance(message.get("result"), dict) and "protocolVersion" in message["result"]:
                    message["result"].setdefault("_meta", {})["steering"] = {"supported": True}
            self.emit(message)

    def steer(self, message):
        params = message.get("params") or {}
        session = params.get("sessionId")
        expected = (params.get("_meta") or {}).get("steering", {}).get("expectedTurnId")
        with self.lock:
            current = self.active.get(session)
            if current is None or expected is None or str(current) != str(expected):
                return {"outcome": "promptRequired", "reason": "original ACP prompt is not active"}
            parts = params.get("prompt")
            if (not isinstance(parts, list) or not parts
                    or any(not isinstance(p, dict) or p.get("type") != "text"
                           or not isinstance(p.get("text"), str) for p in parts)):
                return {"outcome": "promptRequired", "reason": "text prompt required"}
            text = "\n".join(p["text"] for p in parts)
            # One write, one reply. A missing plugin or a socket failure has no
            # cancel fallback. Native unknown effects remain unknown.
            written = False
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    connection.settimeout(15)
                    connection.connect(self.endpoint)
                    written = True
                    connection.sendall((json.dumps({"sessionId": session, "text": text}) + "\n").encode())
                    with connection.makefile("r") as reply:
                        result = json.loads(reply.readline())
                return result
            except (OSError, ValueError) as error:
                if written:
                    return {"outcome": "unknown", "reason": str(error)}
                return {"error": {"code": -32001, "message": "native steer plugin unavailable",
                                  "data": str(error)}}

    def input(self, message):
        if message.get("method") == "_session/steering":
            result = self.steer(message)
            key = "error" if "error" in result else "result"
            self.emit({"jsonrpc": "2.0", "id": message.get("id"),
                       key: result["error"] if key == "error" else result})
            return
        with self.lock:
            if message.get("method") == "session/prompt":
                session = message["params"]["sessionId"]
                # Keep native concurrent-prompt refusal and its original owner.
                if session not in self.active:
                    self.active[session] = message["id"]
                    self.pending[str(message["id"])] = session
            self.child.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.child.stdin.flush()


def main():
    binary = os.environ.get("OPENCODE_BIN") or "opencode"
    plugin = Path(__file__).with_name("kaola-opencode-steer.mjs")
    env = os.environ.copy()
    # Preserve file/global/project policy. Add only this process's plugin to
    # the existing content overlay. Invalid supplied JSON must stay an error.
    content = json.loads(env.get("OPENCODE_CONFIG_CONTENT") or "{}")
    if not isinstance(content, dict) or not isinstance(content.get("plugins", []), list):
        raise ValueError("OPENCODE_CONFIG_CONTENT must be an object with a plugins list")
    with tempfile.TemporaryDirectory(prefix="kpr-oc-", dir="/tmp") as temporary:
        endpoint = str(Path(temporary) / "steer.sock")
        package = Path(temporary) / "plugin"
        package.mkdir()
        (package / "server.js").write_bytes(plugin.read_bytes())
        (package / "package.json").write_text(json.dumps({"name": "kaola-opencode-steer",
            "private": True, "type": "module", "exports": {"./server": "./server.js"}}))
        content.setdefault("plugins", []).append({"package": package.as_uri(),
            "options": {"socket": endpoint, "directory": os.getcwd()}})
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(content)
        child = subprocess.Popen([binary, "acp"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=None, text=True, env=env)
        adapter = Adapter(child, endpoint)
        closing = threading.Event()
        def stop(signum, frame):
            code = child.poll()
            raise SystemExit(code if code is not None and code >= 0 else 128 + signum)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        def pump():
            try:
                adapter.native_output()
            finally:
                # Native EOF must reach the holder even while its stdin is open.
                child.wait()
                if not closing.is_set():
                    os.kill(os.getpid(), signal.SIGTERM)
        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            for line in sys.stdin:
                adapter.input(json.loads(line))
        finally:
            closing.set()
            try:
                child.stdin.close()
            except BrokenPipeError:
                pass
            try:
                child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            reader.join(timeout=1)
    return child.returncode


if __name__ == "__main__":
    sys.exit(main())
