#!/usr/bin/env python3
"""Issue #98 mission 1 — drive `dsh --profile acp` directly over ACP JSON-RPC stdio.

Read-only with respect to ~/.dsh: this probe never writes a dsh profile, patch,
setting, or credential file. It only speaks the protocol dsh itself serves.

Usage: dsh_acp_probe.py <phase> [args...]
Phases are separate processes on purpose, so a phase that wedges cannot poison
the next one's evidence.
"""
import json
import os
import subprocess
import sys
import threading
import time

DSH = os.environ.get("DSH_BIN", "/opt/homebrew/bin/dsh")
PROTOCOL_VERSION = 1


class Peer:
    def __init__(self, cwd):
        self.proc = subprocess.Popen(
            [DSH, "--profile", "acp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=cwd, text=True, bufsize=1,
        )
        self.next_id = 0
        self.responses = {}
        self.notifications = []
        self.inbound_requests = []
        self.stderr = []
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                with self.cv:
                    self.notifications.append({"NON_JSON_STDOUT": line})
                    self.cv.notify_all()
                continue
            with self.cv:
                if "id" in msg and "method" in msg:
                    self.inbound_requests.append(msg)
                elif "id" in msg:
                    self.responses[msg["id"]] = msg
                else:
                    self.notifications.append(msg)
                self.cv.notify_all()

    def _read_stderr(self):
        for line in self.proc.stderr:
            with self.lock:
                self.stderr.append(line.rstrip())

    def send(self, method, params=None):
        with self.lock:
            self.next_id += 1
            rid = self.next_id
        frame = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            frame["params"] = params
        self.proc.stdin.write(json.dumps(frame) + "\n")
        self.proc.stdin.flush()
        return rid

    def reply(self, rid, result):
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}) + "\n")
        self.proc.stdin.flush()

    def wait(self, rid, timeout=30.0, auto_permission=None):
        """Wait for response `rid`, auto-answering inbound permission requests."""
        deadline = time.monotonic() + timeout
        answered = set()
        while True:
            with self.cv:
                if rid in self.responses:
                    return self.responses.pop(rid)
                pending = [r for r in self.inbound_requests if r["id"] not in answered]
                remaining = deadline - time.monotonic()
                if not pending:
                    if remaining <= 0:
                        return None
                    self.cv.wait(min(remaining, 0.5))
                    continue
            for req in pending:
                answered.add(req["id"])
                if auto_permission is not None and req.get("method") == "session/request_permission":
                    self.reply(req["id"], auto_permission(req))
                else:
                    self.reply(req["id"], {})

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        return self.proc.returncode


def emit(tag, value):
    print(f"@@{tag} " + json.dumps(value, ensure_ascii=False, default=str))


def initialize(peer):
    rid = peer.send("initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "clientCapabilities": {
            "fs": {"readTextFile": False, "writeTextFile": False},
            "terminal": False,
        },
    })
    resp = peer.wait(rid, 20.0)
    emit("initialize", resp)
    return resp


def allow_first(req):
    """Answer a permission request by selecting the first allow-ish option."""
    opts = ((req.get("params") or {}).get("options")) or []
    emit("permission_request", req)
    chosen = None
    for opt in opts:
        if "allow" in str(opt.get("kind", "")).lower():
            chosen = opt.get("optionId")
            break
    if chosen is None and opts:
        chosen = opts[0].get("optionId")
    return {"outcome": {"outcome": "selected", "optionId": chosen}}


def phase_handshake(cwd):
    peer = Peer(cwd)
    init = initialize(peer)
    emit("authenticate", peer.wait(peer.send("authenticate", {"methodId": ""}), 15.0))
    # Probe the methods the shipped README says are rejected, before opening a session.
    emit("session_load_probe", peer.wait(
        peer.send("session/load", {"sessionId": "nonexistent", "cwd": cwd, "mcpServers": []}), 15.0))
    new = peer.wait(peer.send("session/new", {"cwd": cwd, "mcpServers": []}), 60.0)
    emit("session_new", new)
    sid = ((new or {}).get("result") or {}).get("sessionId")
    if sid:
        emit("session_list", peer.wait(peer.send("session/list", {"cwd": cwd}), 20.0))
        emit("set_config_option_probe", peer.wait(
            peer.send("session/set_config_option", {"sessionId": sid, "configOptionId": "mode",
                                                    "value": "bypassPermissions"}), 20.0))
        emit("session_close", peer.wait(peer.send("session/close", {"sessionId": sid}), 30.0))
    emit("stderr", peer.stderr[-40:])
    emit("exit_code", peer.close())


def phase_prompt(cwd, text):
    peer = Peer(cwd)
    initialize(peer)
    new = peer.wait(peer.send("session/new", {"cwd": cwd, "mcpServers": []}), 60.0)
    sid = ((new or {}).get("result") or {}).get("sessionId")
    emit("session_id", sid)
    if not sid:
        emit("session_new_failed", new)
        emit("stderr", peer.stderr[-40:])
        emit("exit_code", peer.close())
        return
    started = time.monotonic()
    rid = peer.send("session/prompt", {
        "sessionId": sid,
        "prompt": [{"type": "text", "text": text}],
    })
    resp = peer.wait(rid, 240.0, auto_permission=allow_first)
    emit("prompt_elapsed_s", round(time.monotonic() - started, 2))
    emit("prompt_response", resp)
    with peer.lock:
        notes = list(peer.notifications)
    emit("update_count", len(notes))
    emit("update_methods", sorted({n.get("method", "?") for n in notes}))
    emit("update_kinds", sorted({
        str(((n.get("params") or {}).get("update") or {}).get("sessionUpdate"))
        for n in notes if n.get("method") == "session/update"
    }))
    emit("updates", notes[:80])
    emit("session_close", peer.wait(peer.send("session/close", {"sessionId": sid}), 30.0))
    emit("stderr", peer.stderr[-40:])
    emit("exit_code", peer.close())
    emit("resume_candidate", sid)


def phase_prompt_model(cwd, model_value, text):
    """Same as `prompt`, but select an authenticated route first.

    The shipped acp bundle pins provider/model to deepseek-official, which has
    no credential on this machine; `session/set_config_option` is the runtime,
    ~/.dsh-untouched way to move the session onto a route that does.
    """
    peer = Peer(cwd)
    initialize(peer)
    new = peer.wait(peer.send("session/new", {"cwd": cwd, "mcpServers": []}), 60.0)
    sid = ((new or {}).get("result") or {}).get("sessionId")
    emit("session_id", sid)
    if not sid:
        emit("session_new_failed", new)
        emit("exit_code", peer.close())
        return
    emit("set_model", peer.wait(peer.send("session/set_config_option", {
        "sessionId": sid, "configId": "model", "value": model_value}), 30.0))
    started = time.monotonic()
    rid = peer.send("session/prompt", {"sessionId": sid,
                                       "prompt": [{"type": "text", "text": text}]})
    resp = peer.wait(rid, 300.0, auto_permission=allow_first)
    emit("prompt_elapsed_s", round(time.monotonic() - started, 2))
    emit("prompt_response", resp)
    with peer.lock:
        notes = list(peer.notifications)
    emit("update_count", len(notes))
    emit("update_kinds", sorted({
        str(((n.get("params") or {}).get("update") or {}).get("sessionUpdate"))
        for n in notes if n.get("method") == "session/update"
    }))
    emit("updates", notes[:120])
    emit("session_close", peer.wait(peer.send("session/close", {"sessionId": sid}), 30.0))
    emit("stderr", peer.stderr[-40:])
    emit("exit_code", peer.close())
    emit("resume_candidate", sid)


def phase_methods(cwd):
    """Probe every method the manifest claims answers -32601, in one run.

    Issue #98 review: the manifest and steering summary named nine methods, but
    only three were preserved in a raw frame. This phase sends all of them so
    the claim and the artifact match.
    """
    peer = Peer(cwd)
    initialize(peer)
    new = peer.wait(peer.send("session/new", {"cwd": cwd, "mcpServers": []}), 60.0)
    sid = ((new or {}).get("result") or {}).get("sessionId")
    emit("session_id", sid)
    for method in ("session/load", "session/set_mode", "session/delete", "session/fork",
                   "terminal/create", "terminal/output", "_session/steering",
                   "session/steering", "session/steer", "_session/steer"):
        response = peer.wait(peer.send(method, {"sessionId": sid}), 15.0)
        error = (response or {}).get("error") or {}
        emit("method", {"method": method, "code": error.get("code"),
                        "message": error.get("message"),
                        "has_result": "result" in (response or {})})
    if sid:
        emit("session_close", peer.wait(peer.send("session/close", {"sessionId": sid}), 30.0))
    emit("stderr", peer.stderr[-40:])
    emit("exit_code", peer.close())


def phase_resume(cwd, sid):
    peer = Peer(cwd)
    initialize(peer)
    emit("session_list", peer.wait(peer.send("session/list", {"cwd": cwd}), 20.0))
    emit("session_resume", peer.wait(
        peer.send("session/resume", {"sessionId": sid, "cwd": cwd, "mcpServers": []}), 60.0))
    emit("stderr", peer.stderr[-40:])
    emit("exit_code", peer.close())


def phase_tool(cwd, model_value, text):
    """Drive a tool-using turn so the permission surface shows itself."""
    peer = Peer(cwd)
    initialize(peer)
    new = peer.wait(peer.send("session/new", {"cwd": cwd, "mcpServers": []}), 60.0)
    sid = ((new or {}).get("result") or {}).get("sessionId")
    emit("session_id", sid)
    peer.wait(peer.send("session/set_config_option", {
        "sessionId": sid, "configId": "model", "value": model_value}), 30.0)
    rid = peer.send("session/prompt", {"sessionId": sid,
                                       "prompt": [{"type": "text", "text": text}]})
    resp = peer.wait(rid, 300.0, auto_permission=allow_first)
    emit("prompt_response", resp)
    with peer.lock:
        notes = list(peer.notifications)
        inbound = list(peer.inbound_requests)
    emit("inbound_request_methods", sorted({r.get("method", "?") for r in inbound}))
    emit("inbound_requests", inbound)
    emit("update_kinds", sorted({
        str(((n.get("params") or {}).get("update") or {}).get("sessionUpdate"))
        for n in notes if n.get("method") == "session/update"
    }))
    emit("updates", notes[:200])
    emit("session_close", peer.wait(peer.send("session/close", {"sessionId": sid}), 30.0))
    emit("exit_code", peer.close())


def phase_cancel(cwd, text, model_value=None):
    peer = Peer(cwd)
    initialize(peer)
    new = peer.wait(peer.send("session/new", {"cwd": cwd, "mcpServers": []}), 60.0)
    sid = ((new or {}).get("result") or {}).get("sessionId")
    emit("session_id", sid)
    if not sid:
        emit("session_new_failed", new)
        emit("exit_code", peer.close())
        return
    if model_value:
        peer.wait(peer.send("session/set_config_option", {
            "sessionId": sid, "configId": "model", "value": model_value}), 30.0)
    rid = peer.send("session/prompt", {"sessionId": sid,
                                       "prompt": [{"type": "text", "text": text}]})
    time.sleep(8)
    peer.proc.stdin.write(json.dumps(
        {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": sid}}) + "\n")
    peer.proc.stdin.flush()
    started = time.monotonic()
    resp = peer.wait(rid, 180.0, auto_permission=allow_first)
    emit("cancel_settle_s", round(time.monotonic() - started, 2))
    emit("prompt_response_after_cancel", resp)
    emit("steer_probe_session_steering", peer.wait(
        peer.send("_session/steering", {"sessionId": sid}), 15.0))
    emit("steer_probe_session_steer", peer.wait(
        peer.send("session/steer", {"sessionId": sid}), 15.0))
    emit("session_close", peer.wait(peer.send("session/close", {"sessionId": sid}), 30.0))
    emit("exit_code", peer.close())


if __name__ == "__main__":
    phase = sys.argv[1]
    if phase == "handshake":
        phase_handshake(sys.argv[2])
    elif phase == "prompt":
        phase_prompt(sys.argv[2], sys.argv[3])
    elif phase == "prompt-model":
        phase_prompt_model(sys.argv[2], sys.argv[3], sys.argv[4])
    elif phase == "tool":
        phase_tool(sys.argv[2], sys.argv[3], sys.argv[4])
    elif phase == "methods":
        phase_methods(sys.argv[2])
    elif phase == "resume":
        phase_resume(sys.argv[2], sys.argv[3])
    elif phase == "cancel":
        phase_cancel(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        raise SystemExit(f"unknown phase {phase}")
