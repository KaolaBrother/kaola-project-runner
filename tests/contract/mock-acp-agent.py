#!/usr/bin/env python3
"""Scriptable mock ACP agent for the offline Runner v2 contract suite.

Speaks newline-delimited JSON-RPC on stdin/stdout. A scenario name (argv
``--scenario NAME``) selects scripted behavior; ``--caps a,b`` enables optional
session capabilities. ``MOCK_ACP_LOG`` names a JSONL path that records every
response the mock receives for its own outbound requests plus protocol notes.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from typing import Any

LOG_LOCK = threading.Lock()
LOG_PATH = os.environ.get("MOCK_ACP_LOG", "")
STDOUT_LOCK = threading.Lock()


def log_event(event: dict[str, Any]) -> None:
    if not LOG_PATH:
        return
    event.setdefault("ts", round(time.time(), 3))
    with LOG_LOCK:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def send(message: dict[str, Any]) -> None:
    data = json.dumps(message).encode("utf-8") + b"\n"
    with STDOUT_LOCK:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def send_raw(data: bytes) -> None:
    with STDOUT_LOCK:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def respond(request_id: Any, result: Any = None, error: Any = None) -> None:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        message["error"] = error
    else:
        message["result"] = result
    send(message)


def request(request_id: Any, method: str, params: dict[str, Any]) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})


def notify(method: str, params: dict[str, Any]) -> None:
    send({"jsonrpc": "2.0", "method": method, "params": params})


def session_update(session_id: str, update: dict[str, Any]) -> None:
    notify("session/update", {"sessionId": session_id, "update": update})


def message_chunk(session_id: str, text: str) -> None:
    session_update(
        session_id,
        {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": text},
        },
    )


def thought_chunk(session_id: str, text: str) -> None:
    session_update(
        session_id,
        {
            "sessionUpdate": "agent_thought_chunk",
            "content": {"type": "text", "text": text},
        },
    )


class MockAgent:
    def __init__(self, scenario: str, caps: set[str], turn_ms: int, flood_bytes: int):
        self.scenario = scenario
        self.caps = caps
        self.turn_ms = turn_ms
        self.flood_bytes = flood_bytes
        self.next_outbound_id = 1000
        self.pending: dict[Any, str] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.session_counter = 0
        self.authenticated = False
        self.lock = threading.Lock()
        self.active_turn: tuple[Any, str] | None = None
        self.child_proc: subprocess.Popen | None = None
        self.configured: dict[str, Any] = {}
        log_event({"event": "mock_start", "scenario": scenario, "caps": sorted(caps)})

    # -- outbound helpers -------------------------------------------------

    def outbound_id(self) -> int:
        self.next_outbound_id += 1
        return self.next_outbound_id

    def ask_permission(self, session_id: str, title: str, options: list[str]) -> int:
        request_id = self.outbound_id()
        self.pending[request_id] = "session/request_permission"
        request(
            request_id,
            "session/request_permission",
            {
                "sessionId": session_id,
                "toolCall": {"toolCallId": f"tc-{request_id}", "title": title},
                "options": [
                    {"optionId": option, "name": option, "kind": "allow_once"}
                    for option in options
                ],
            },
        )
        return request_id

    # -- capability map ----------------------------------------------------

    def capabilities(self) -> dict[str, Any]:
        return {
            "loadSession": "load" in self.caps,
            "sessionCapabilities": {
                "list": "list" in self.caps,
                "resume": "resume" in self.caps,
                "close": "close" in self.caps,
            },
            "promptCapabilities": {"embeddedContext": True},
        }

    # -- turn lifecycle ------------------------------------------------------

    def begin_turn(self, request_id: Any, session_id: str) -> None:
        with self.lock:
            self.active_turn = (request_id, session_id)

    def finish_turn(self, request_id: Any, stop: str = "end_turn") -> bool:
        """Respond to the active prompt; first stopReason wins."""
        with self.lock:
            if self.active_turn is None or self.active_turn[0] != request_id:
                return False
            self.active_turn = None
        respond(request_id, {"stopReason": stop})
        return True

    def finish_active_turn(self, stop: str) -> bool:
        with self.lock:
            turn = self.active_turn
            self.active_turn = None
        if turn is None:
            return False
        respond(turn[0], {"stopReason": stop})
        return True

    # -- per-method handlers ------------------------------------------------

    def on_initialize(self, request_id: Any, params: dict[str, Any]) -> None:
        log_event({"event": "initialize", "params": params})
        if self.scenario == "protocol_v2":
            respond(
                request_id,
                {
                    "protocolVersion": 2,
                    "agentCapabilities": self.capabilities(),
                    "authMethods": [],
                    "agentInfo": {"name": "mock-acp-agent", "version": "2.0.0"},
                },
            )
            return
        result = {
            "protocolVersion": 1,
            "agentCapabilities": self.capabilities(),
            "authMethods": [{"id": "mock-auth", "name": "Mock auth"}]
            if self.scenario == "auth_required"
            else [],
            "agentInfo": {"name": "mock-acp-agent", "version": "0.0.1"},
        }
        if self.scenario == "numeric_string_id":
            respond(str(request_id), result)
        else:
            respond(request_id, result)

    def on_authenticate(self, request_id: Any, params: dict[str, Any]) -> None:
        self.authenticated = True
        respond(request_id, {})

    def on_session_new(self, request_id: Any, params: dict[str, Any]) -> None:
        if self.scenario == "auth_required" and not self.authenticated:
            respond(
                request_id,
                error={"code": -32000, "message": "authentication required"},
            )
            return
        self.session_counter += 1
        session_id = f"mock-session-{self.session_counter}"
        self.sessions[session_id] = {"cwd": params.get("cwd", "")}
        log_event({"event": "session_new", "sessionId": session_id})
        respond(request_id, {"sessionId": session_id})

    def on_session_list(self, request_id: Any) -> None:
        if "list" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/list unsupported"})
            return
        respond(
            request_id,
            {
                "sessions": [
                    {"sessionId": sid, "cwd": meta.get("cwd", "")}
                    for sid, meta in self.sessions.items()
                ]
            },
        )

    def on_session_resume(self, request_id: Any, params: dict[str, Any]) -> None:
        if "resume" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/resume unsupported"})
            return
        session_id = params.get("sessionId", "")
        if session_id not in self.sessions:
            respond(request_id, error={"code": -32002, "message": "unknown sessionId"})
            return
        respond(request_id, {"sessionId": session_id})

    def on_session_close(self, request_id: Any, params: dict[str, Any]) -> None:
        if "close" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/close unsupported"})
            return
        self.sessions.pop(params.get("sessionId", ""), None)
        respond(request_id, {})

    def on_set_config(self, request_id: Any, params: dict[str, Any]) -> None:
        config_id = params.get("configId") or params.get("config_id")
        if config_id is not None:
            self.configured[str(config_id)] = params.get("value")
        log_event({"event": "set_config_option", "params": params})
        respond(request_id, {})

    # -- prompt turn scenarios -----------------------------------------------

    def emit_prelude(self, session_id: str) -> None:
        if self.scenario == "garbage_lines":
            send_raw(b'{"jsonrpc":"2.0","method":"session/up')
            time.sleep(0.15)
            send_raw(
                b'date","params":{"sessionId":"' + session_id.encode() +
                b'","update":{"sessionUpdate":"agent_thought_chunk","content":{"type":"text","text":"half"}}}\n'
            )
            send_raw(b"this is not json at all\n")
        if self.scenario == "stderr_flood":
            chunk = b"mock-stderr-flood\n" * 64
            written = 0
            while written < self.flood_bytes:
                sys.stderr.buffer.write(chunk)
                written += len(chunk)
            sys.stderr.buffer.flush()

    def run_prompt(self, request_id: Any, session_id: str, text: str) -> None:
        scenario = self.scenario
        if scenario == "die_during_permission":
            self.ask_permission(session_id, "mock dangerous op", ["allow", "deny"])
            log_event({"event": "dying_with_pending_permission"})
            time.sleep(0.3)
            os._exit(3)
        if scenario == "multi_permission":
            ids = [
                self.ask_permission(session_id, f"mock op {index}", ["allow", "deny"])
                for index in range(3)
            ]
            log_event({"event": "multi_permission_sent", "ids": ids})
            return  # turn completes in on_response once all three answered
        if scenario == "agent_cancels_permission":
            permission_id = self.ask_permission(session_id, "will be cancelled", ["allow", "deny"])
            time.sleep(0.4)
            notify("$/cancel_request", {"id": permission_id})
            self.pending.pop(permission_id, None)
            log_event({"event": "cancelled_own_permission", "id": permission_id})
            message_chunk(session_id, "MOCK-REPLY after cancel cascade")
            self.finish_turn(request_id)
            return
        if scenario == "agent_cancels_prompt":
            notify("$/cancel_request", {"id": request_id})
            log_event({"event": "cancelled_prompt_request", "id": request_id})
            with self.lock:
                self.active_turn = None
            return  # never responds to the prompt
        if scenario == "fs_unknown_calls":
            for method, params in (
                ("fs/read_text_file", {"sessionId": session_id, "path": "/etc/hostname"}),
                ("fs/write_text_file", {"sessionId": session_id, "path": "/tmp/x", "content": "y"}),
                ("elicitation/create", {"sessionId": session_id, "message": "pick"}),
                ("kaola/bogus_method", {"sessionId": session_id}),
            ):
                outbound = self.outbound_id()
                self.pending[outbound] = method
                request(outbound, method, params)
            return  # finishes in on_response once all four answered
        if scenario == "hang_until_cancel":
            message_chunk(session_id, "MOCK-REPLY working")
            return  # only session/cancel resolves this turn
        if scenario == "permission_gate":
            self.ask_permission(session_id, "mock gated op", ["allow", "deny"])
            return  # resumes in on_response
        if scenario == "permission_unless_yolo":
            if self.configured.get("mode") == "yolo":
                log_event({"event": "yolo_skip_permission", "configured": dict(self.configured)})
            else:
                self.ask_permission(session_id, "mock gated op", ["allow", "deny"])
                return
        self.emit_prelude(session_id)
        if self.turn_ms:
            time.sleep(self.turn_ms / 1000.0)
        thought_chunk(session_id, "thinking about it")
        message_chunk(session_id, "MOCK-REPLY " + text[:64])
        session_update(
            session_id,
            {"sessionUpdate": "usage_update", "used": 1234, "size": 8192},
        )
        self.finish_turn(request_id)

    def on_prompt(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = params.get("sessionId", "")
        text = " ".join(
            part.get("text", "") for part in params.get("prompt", []) if isinstance(part, dict)
        )
        log_event({"event": "prompt", "sessionId": session_id, "text": text})
        self.begin_turn(request_id, session_id)
        if self.scenario in ("normal", "garbage_lines", "stderr_flood", "slow", "cancel_race"):
            thread = threading.Thread(
                target=self.run_prompt, args=(request_id, session_id, text), daemon=True
            )
            thread.start()
            return
        self.run_prompt(request_id, session_id, text)

    def on_cancel_notification(self, params: dict[str, Any]) -> None:
        log_event({"event": "session_cancel", "params": params})
        self.finish_active_turn("cancelled")

    # -- inbound dispatch -----------------------------------------------------

    def on_response(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        method = self.pending.pop(request_id, None)
        if method is None and isinstance(request_id, str) and request_id.isdigit():
            method = self.pending.pop(int(request_id), None)
        if method is None and isinstance(request_id, int):
            method = self.pending.pop(str(request_id), None)
        log_event({"event": "outbound_response", "id": request_id, "method": method, "message": message})
        if method == "session/request_permission" and self.scenario == "multi_permission":
            if not any(m == "session/request_permission" for m in self.pending.values()):
                sid = next(iter(self.sessions), "")
                message_chunk(sid, "MOCK-REPLY all permitted")
                self.finish_active_turn("end_turn")
        elif method == "session/request_permission" and self.scenario in (
            "permission_gate",
            "permission_unless_yolo",
        ):
            sid = next(iter(self.sessions), "")
            message_chunk(sid, "MOCK-REPLY permitted")
            self.finish_active_turn("end_turn")
        elif method in ("fs/read_text_file", "fs/write_text_file", "elicitation/create", "kaola/bogus_method"):
            if not self.pending:
                sid = next(iter(self.sessions), "")
                message_chunk(sid, "MOCK-REPLY unknowns answered")
                self.finish_active_turn("end_turn")

    def dispatch(self, message: dict[str, Any]) -> None:
        if "method" not in message:
            self.on_response(message)
            return
        method = message["method"]
        params = message.get("params") or {}
        request_id = message.get("id")
        is_request = "id" in message
        if method == "$/cancel_request":
            cancelled = params.get("id")
            note = self.pending.pop(cancelled, None)
            if note is None and isinstance(cancelled, str) and cancelled.isdigit():
                note = self.pending.pop(int(cancelled), None)
            if note is None and isinstance(cancelled, int):
                note = self.pending.pop(str(cancelled), None)
            log_event({"event": "cancel_request_inbound", "id": cancelled, "was": note})
            return
        if not is_request:
            if method == "session/cancel":
                self.on_cancel_notification(params)
            else:
                log_event({"event": "notification", "method": method})
            return
        handlers = {
            "initialize": self.on_initialize,
            "authenticate": self.on_authenticate,
            "session/new": self.on_session_new,
            "session/resume": self.on_session_resume,
            "session/load": self.on_session_resume,
            "session/close": self.on_session_close,
            "session/prompt": self.on_prompt,
            "session/set_mode": self.on_set_config,
            "session/set_config_option": self.on_set_config,
        }
        if method == "session/list":
            self.on_session_list(request_id)
            return
        handler = handlers.get(method)
        if handler is None:
            respond(request_id, error={"code": -32601, "message": f"unsupported: {method}"})
            return
        handler(request_id, params)

    def serve(self) -> int:
        if self.scenario == "stubborn_child":
            self.child_proc = subprocess.Popen(["sleep", "300"])
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            log_event({"event": "stubborn_child_spawned", "pid": self.child_proc.pid})
        buffer = bytearray()
        while True:
            chunk = sys.stdin.buffer.read(1)
            if not chunk:
                if self.scenario == "stubborn_child":
                    time.sleep(0.2)
                    continue
                break
            buffer.extend(chunk)
            if chunk == b"\n":
                line = bytes(buffer).strip()
                buffer.clear()
                if not line:
                    continue
                try:
                    message = json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    log_event({"event": "unparseable_inbound", "line": line[:80].decode("utf-8", "replace")})
                    continue
                self.dispatch(message)
        log_event({"event": "mock_exit"})
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="normal")
    parser.add_argument("--caps", default="")
    parser.add_argument("--turn-ms", type=int, default=0)
    parser.add_argument("--flood-bytes", type=int, default=1024 * 1024)
    args, _unknown = parser.parse_known_args()
    caps = {item for item in args.caps.split(",") if item}
    agent = MockAgent(args.scenario, caps, args.turn_ms, args.flood_bytes)
    return agent.serve()


if __name__ == "__main__":
    raise SystemExit(main())
