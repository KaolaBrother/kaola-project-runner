#!/usr/bin/env python3
"""Expose DSH agent.steer through the existing external ACP steer contract.

The documented launch overlay loads one local plugin in the native ACP process.
The native child owns all other ACP frames, permissions and original prompt replies.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading

# Reuse the unchanged ACP forwarder and its exact original-request guard.
spec = importlib.util.spec_from_file_location("kpr_dsh_forwarder", Path(__file__).with_name("kaola-opencode-acp.py"))
forwarder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forwarder)

class Adapter(forwarder.Adapter):
    def steer(self, message):
        params = message.get("params") or {}
        session = params.get("sessionId")
        expected = (params.get("_meta") or {}).get("steering", {}).get("expectedTurnId")
        with self.lock:
            current = self.active.get(session)
            if current is None or expected is None or str(current) != str(expected):
                return {"outcome": "promptRequired", "reason": "original ACP prompt is not active"}
            parts = params.get("prompt")
            if not isinstance(parts, list) or not parts or any(
                    not isinstance(p, dict) or p.get("type") != "text" or
                    not isinstance(p.get("text"), str) for p in parts):
                return {"outcome": "promptRequired", "reason": "text prompt required"}
            written = False
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    connection.settimeout(15)
                    connection.connect(self.endpoint)
                    written = True
                    connection.sendall((json.dumps({"id": message.get("id"), "op": "steer",
                        "sessionId": session, "text": "\n".join(p["text"] for p in parts)}) + "\n").encode())
                    with connection.makefile("r") as reply:
                        native = json.loads(reply.readline())
                if not isinstance(native, dict) or native.get("id") != message.get("id"):
                    return {"outcome": "unknown", "reason": "uncorrelated native reply"}
                if native.get("ok") is True and native.get("admitted") == "native-steer":
                    return {"outcome": "startedNewTurn" if native.get("agentStatus") == "idle" else "written",
                            "confirmation": "native-admitted", "admission": native,
                            "reason": "native steer admission; processing and inbox target need session output"}
                error = native.get("error") or {}
                if error.get("code") in ("session/not-found", "empty-text", "service-unavailable"):
                    return {"outcome": "promptRequired", "reason": error, "admission": native}
                return {"outcome": "unknown", "reason": native}
            except (OSError, ValueError, AttributeError) as error:
                if written:
                    return {"outcome": "unknown", "reason": str(error)}
                return {"error": {"code": -32001, "message": "native steer plugin unavailable",
                                  "data": str(error)}}


def main():
    binary = os.environ.get("DSH_BIN") or "dsh"
    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="kpr-dsh-", dir="/tmp") as temporary:
        directory = Path(temporary)
        endpoint = str(directory / "steer.sock")
        (directory / "steer.mjs").write_bytes(Path(__file__).with_name("kaola-dsh-steer.mjs").read_bytes())
        overlay = directory / "overlay.yml"
        overlay.write_text("- insert:\n    - id: kpr-dsh-steer-bridge\n      name: ./steer.mjs\n")
        env["KPR_DSH_STEER_SOCK"] = endpoint
        child = subprocess.Popen([binary, "--profile", "acp", "--patch", str(overlay)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None, text=True, env=env)
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
                child.wait()
                if not closing.is_set(): os.kill(os.getpid(), signal.SIGTERM)
        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            for line in sys.stdin: adapter.input(json.loads(line))
        finally:
            closing.set()
            try: child.stdin.close()
            except BrokenPipeError: pass
            try: child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.terminate()
                try: child.wait(timeout=4)
                except subprocess.TimeoutExpired: child.kill(); child.wait()
            reader.join(timeout=1)
    return child.returncode

if __name__ == "__main__":
    sys.exit(main())
