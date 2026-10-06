#!/usr/bin/env python3
"""Expose DSH steer and a finite native /compact through the local overlay.

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
    def input(self, message):
        params = message.get("params") or {}
        parts = params.get("prompt")
        if (message.get("method") == "session/prompt" and isinstance(parts, list)
                and len(parts) == 1 and isinstance(parts[0], dict)
                and parts[0].get("type") == "text"
                and isinstance(parts[0].get("text"), str)
                and parts[0]["text"].strip() == "/compact"):
            # Keep stdio control live. Native session/cancel aborts the agent's
            # maintenance signal; the native maintenance lock owns overlap.
            operation = threading.Thread(target=self.compact, args=(message,), daemon=True)
            operation.start()
            return operation
        super().input(message)

    def compact(self, message):
        session = message["params"].get("sessionId")
        request = message.get("id")
        def fail(code, reason, data=None):
            self.emit({"jsonrpc": "2.0", "id": request, "error": {
                "code": code, "message": reason, "data": data}})
        with self.lock:
            if not isinstance(session, str) or not session:
                fail(-32602, "compact needs an exact session")
                return
            if session in self.active:
                fail(-32602, "compact requires an idle original ACP prompt")
                return
        written = False
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(15)  # Existing connection bound; no turn deadline.
                connection.connect(self.endpoint)
                connection.settimeout(None)
                written = True
                connection.sendall((json.dumps({"id": request, "op": "compact",
                    "sessionId": session}) + "\n").encode())
                with connection.makefile("r") as reply:
                    native = json.loads(reply.readline())
            if (not isinstance(native, dict) or native.get("id") != request
                    or native.get("sessionId") != session):
                fail(-32001, "uncorrelated compact reply; reconcile before retry", native)
                return
            if native.get("ok") is not True:
                fail(-32001, "native compact refused or failed", native)
                return
            if native.get("compacted") is not False:
                summary = native.get("summary") or {}
                end = native.get("end") or {}
                occurrence = native.get("compactionId")
                command = native.get("sourceCommandId")
                if not (native.get("compacted") is True and occurrence and command
                        and summary.get("seq") == native.get("summarySeq")
                        and end.get("seq") == native.get("endSeq")
                        and isinstance(native.get("summarySeq"), int)
                        and isinstance(native.get("endSeq"), int)
                        and all(event.get("data", {}).get("compactionId") == occurrence
                                and event.get("data", {}).get("sourceCommandId") == command
                                for event in (summary, end))
                        and "error" not in end.get("data", {})):
                    fail(-32001, "compact returned without matching original completion", native)
                    return
                # Local adapter mapping of real native events, not an upstream
                # ACP notification or a token-drop/model-ack inference.
                self.emit({"jsonrpc": "2.0", "method": "session/update", "params": {
                    "sessionId": session, "update": {"sessionUpdate": "compaction_update",
                    "status": "completed", "compactionId": occurrence,
                    "_meta": {"dsh/compaction": native}}}})
            self.emit({"jsonrpc": "2.0", "id": request, "result": {
                "stopReason": "end_turn", "_meta": {"dsh/compaction": native}}})
        except (OSError, ValueError, AttributeError, TypeError) as error:
            fail(-32001, "compact effect unknown; reconcile before retry" if written
                 else "native compact plugin unavailable", str(error))

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
