#!/usr/bin/env python3
"""Per-session ACP connection holder for the Runner v2 PoC (design §3.3/§7).

Spawned once per session by ``kaola-acp.py start``. Owns the agent's stdio,
runs the NDJSON JSON-RPC loop, keeps ``record.json`` / ``events.jsonl`` /
``stderr.log`` in the session record directory, and serves local NDJSON
requests on ``holder.sock``. Pure Python 3, macOS-compatible (no /proc, no
setsid binary).
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import secrets
import shlex
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
IDLE_EXIT_SECONDS = 600
STDERR_RING = 64 * 1024
EVENT_LOG_MAX = 10 * 1024 * 1024
EVENT_LOG_KEEP = 3
CANCEL_GRACE = 5.0
EXIT_GRACE = 5.0
TERM_GRACE = 3.0
SENSITIVE_KEYS = ("_API_KEY", "TOKEN", "Authorization")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_id(value: Any) -> str:
    return str(value)


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def group_members(pgid: int) -> list[int]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid=,state="], capture_output=True, text=True
    )
    members = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0].isdigit() and int(fields[1]) == pgid:
            if fields[2].upper().startswith("Z"):
                continue
            members.append(int(fields[0]))
    return members


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if any(marker in str(key) for marker in SENSITIVE_KEYS):
                out[key] = "<redacted>"
            else:
                out[key] = scrub(item)
        return out
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


class EventLog:
    def __init__(self, path: Path):
        self.path = path
        self.cursor = 0
        self.lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> int:
        with self.lock:
            self.cursor += 1
            entry = {"cursor": self.cursor, "ts": round(time.time(), 3), **scrub(event)}
            line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            try:
                if self.path.exists() and self.path.stat().st_size > EVENT_LOG_MAX:
                    self._rotate()
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(line)
            except OSError:
                pass
            return self.cursor

    def _rotate(self) -> None:
        for index in range(EVENT_LOG_KEEP - 1, 0, -1):
            older = self.path.with_suffix(f".jsonl.{index}")
            newer = self.path.with_suffix(f".jsonl.{index + 1}")
            if older.exists():
                older.replace(newer)
        if self.path.exists():
            self.path.replace(self.path.with_suffix(".jsonl.1"))

    def read_since(self, cursor: int, limit: int | None) -> list[dict[str, Any]]:
        entries = []
        if not self.path.exists():
            return entries
        with open(self.path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("cursor", 0) > cursor:
                    entries.append(entry)
                    if limit and len(entries) >= limit:
                        break
        return entries


class StderrPump:
    def __init__(self, stream, log_path: Path):
        self.stream = stream
        self.log_path = log_path
        self.ring = bytearray()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        try:
            while True:
                data = self.stream.read(65536)
                if not data:
                    return
                with self.lock:
                    self.ring.extend(data)
                    if len(self.ring) > STDERR_RING:
                        del self.ring[: len(self.ring) - STDERR_RING]
                try:
                    with open(self.log_path, "ab") as handle:
                        handle.write(data)
                except OSError:
                    pass
        except (OSError, ValueError):
            return

    def tail(self, count: int = 20) -> list[str]:
        with self.lock:
            text = bytes(self.ring).decode("utf-8", "replace")
        return text.splitlines()[-count:]


class AgentConnection:
    """Owns the agent process, its reader threads, and JSON-RPC state."""

    def __init__(self, holder: "Holder"):
        self.holder = holder
        self.proc: subprocess.Popen | None = None
        self.next_id = 0
        self.pending_out: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.reader: threading.Thread | None = None
        self.stderr_pump: StderrPump | None = None
        self.exited = threading.Event()
        self.exit_code: int | None = None
        self.exit_signal: int | None = None
        self.malformed_lines = 0
        self.unknown_updates = 0

    def spawn(self, command: str, cwd: str, env: dict[str, str] | None = None) -> None:
        argv = shlex.split(command)
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        self.stderr_pump = StderrPump(self.proc.stderr, self.holder.record_dir / "stderr.log")
        self.stderr_pump.start()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()
        threading.Thread(target=self._wait_loop, daemon=True).start()

    def _wait_loop(self) -> None:
        code = self.proc.wait() if self.proc else -1
        self.exit_code = code if code >= 0 else None
        self.exit_signal = -code if code < 0 else None
        self.exited.set()
        self.holder.on_agent_exit(code)

    def _read_loop(self) -> None:
        stream = self.proc.stdout
        while True:
            try:
                line = stream.readline()
            except (OSError, ValueError):
                break
            if not line:
                break
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            try:
                message = json.loads(text)
            except ValueError:
                self.malformed_lines += 1
                self.holder.events.append(
                    {"kind": "malformed_stdout", "head": text[:120]}
                )
                continue
            if not isinstance(message, dict):
                self.malformed_lines += 1
                continue
            self.holder.on_agent_message(message)

    # -- JSON-RPC out ---------------------------------------------------------

    def send_message(self, message: dict[str, Any]) -> bool:
        if self.proc is None or self.proc.stdin is None or self.exited.is_set():
            return False
        try:
            self.proc.stdin.write(canonical(message) + b"\n")
            self.proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def send_request(self, method: str, params: dict[str, Any]) -> int:
        with self.lock:
            self.next_id += 1
            request_id = self.next_id
            slot = {"event": threading.Event(), "response": None}
            self.pending_out[normalize_id(request_id)] = slot
        written = self.send_message(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        if not written:
            with self.lock:
                self.pending_out.pop(normalize_id(request_id), None)
            slot["response"] = {"error": {"code": -32000, "message": "write failed"}}
            slot["event"].set()
        return request_id

    def wait_response(self, request_id: int, timeout: float | None) -> dict[str, Any] | None:
        key = normalize_id(request_id)
        with self.lock:
            slot = self.pending_out.get(key)
        if slot is None:
            return None
        slot["event"].wait(timeout)
        with self.lock:
            self.pending_out.pop(key, None)
        return slot["response"]

    def resolve_response(self, message: dict[str, Any]) -> None:
        key = normalize_id(message.get("id"))
        with self.lock:
            slot = self.pending_out.get(key)
        if slot is not None:
            slot["response"] = message
            slot["event"].set()
        else:
            self.holder.events.append({"kind": "orphan_response", "id": message.get("id")})

    def cancel_outbound(self, request_id: Any) -> bool:
        key = normalize_id(request_id)
        with self.lock:
            slot = self.pending_out.get(key)
        if slot is None:
            return False
        slot["response"] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32800, "message": "request cancelled by agent"},
        }
        slot["event"].set()
        return True


KNOWN_UPDATES = {
    "agent_message_chunk",
    "agent_thought_chunk",
    "tool_call",
    "tool_call_update",
    "plan",
    "available_commands_update",
    "current_mode_update",
    "config_option_update",
    "usage_update",
    "user_message_chunk",
}


class Holder:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.record_dir = Path(args.record_dir)
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.events = EventLog(self.record_dir / "events.jsonl")
        self.record_path = self.record_dir / "record.json"
        self.socket_path = Path(args.socket) if args.socket else self.record_dir / "holder.sock"
        self.agent = AgentConnection(self)
        self.listener: socket.socket | None = None
        self.lock = threading.Lock()
        self.turn_cond = threading.Condition()
        self.state = "starting"
        self.stop_requested = False
        self.acp_session_id: str | None = None
        self.session_meta: dict[str, Any] = {}
        self.protocol_version: int | None = None
        self.agent_info: dict[str, Any] = {}
        self.capabilities: dict[str, Any] = {}
        self.auth_methods: list[dict[str, Any]] = []
        self.pending_permissions: dict[str, dict[str, Any]] = {}
        self.turn: dict[str, Any] = self._empty_turn()
        self.last_prompt: dict[str, Any] = {}
        self.fatal_error: dict[str, Any] | None = None
        self.record_lock = threading.Lock()
        self.last_activity = time.monotonic()
        self.agent_exited = threading.Event()

    # -- record ---------------------------------------------------------------

    def _empty_turn(self) -> dict[str, Any]:
        return {
            "active": False,
            "request_id": None,
            "fingerprint": None,
            "written_at": None,
            "mutation_status": "not_started",
            "stop_reason": None,
            "outcome": None,
            "final_text": "",
            "final_text_truncated": False,
            "thinking_chars": 0,
            "tool_calls": {},
            "tool_order": [],
            "failed_tools": [],
            "started_at": None,
            "cancel_requested": False,
        }

    def write_record(self, **extra: Any) -> None:
        record = {
            "transport": "acp",
            "platform": self.args.platform,
            "session": self.args.session,
            "repo": self.args.repo,
            "holder_pid": os.getpid(),
            "agent_pid": self.agent.proc.pid if self.agent.proc else None,
            "agent_pgid": self.agent.proc.pid if self.agent.proc else None,
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "acp_session_id": self.acp_session_id,
            "session_meta": self.session_meta,
            "protocol_version": self.protocol_version,
            "agent_info": self.agent_info,
            "capabilities": self.capabilities,
            "state": self.state,
            "pending_permissions": list(self.pending_permissions.values()),
            "last_prompt": self.last_prompt,
            "event_cursor": self.events.cursor,
            "malformed_stdout_lines": self.agent.malformed_lines,
            "fatal_error": self.fatal_error,
            "created_at": getattr(self, "created_at", None),
            "updated_at": round(time.time(), 3),
            **extra,
        }
        with self.record_lock:
            tmp = self.record_path.with_name(f"record.{secrets.token_hex(4)}.tmp")
            tmp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            tmp.replace(self.record_path)

    # -- ACP lifecycle ----------------------------------------------------------

    def initialize_agent(self, resume: str | None = None, use_continue: bool = False,
                         list_supported: bool = False) -> dict[str, Any]:
        command = self.args.command
        try:
            self.agent.spawn(command, self.args.repo)
        except (OSError, ValueError) as exc:
            return {"error": {"code": "acp-spawn-failed", "message": str(exc)}}
        self.write_record()
        request_id = self.agent.send_request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False},
                                       "terminal": False},
            },
        )
        response = self.agent.wait_response(request_id, 15.0)
        if response is None:
            return {"error": {"code": "acp-initialize-timeout", "message": "no initialize response"}}
        if "error" in response:
            return {"error": {"code": "acp-initialize-failed", "message": response["error"]}}
        result = response.get("result") or {}
        self.protocol_version = result.get("protocolVersion")
        self.agent_info = result.get("agentInfo") or {}
        self.capabilities = result.get("agentCapabilities") or {}
        self.auth_methods = result.get("authMethods") or []
        if self.protocol_version != PROTOCOL_VERSION:
            self.write_record()
            return {
                "error": {
                    "code": "acp-protocol-version-unsupported",
                    "message": f"agent negotiated protocolVersion={self.protocol_version}",
                    "agent_version": self.protocol_version,
                }
            }
        session_caps = self.capabilities.get("sessionCapabilities") or {}
        if resume is not None:
            if not session_caps.get("resume") and not self.capabilities.get("loadSession"):
                return {"error": {"code": "resume-unsupported", "message": "agent lacks resume/loadSession"}}
            method = "session/resume" if session_caps.get("resume") else "session/load"
            request_id = self.agent.send_request(
                method, {"sessionId": resume, "cwd": self.args.repo, "mcpServers": []}
            )
            response = self.agent.wait_response(request_id, 15.0)
            if response is None or "error" in response:
                return {"error": {"code": "resume-failed", "message": json.dumps(response)}}
            self.session_meta = response.get("result") or {}
            self.acp_session_id = self.session_meta.get("sessionId", resume)
        elif use_continue:
            if not session_caps.get("list"):
                return {"error": {"code": "continue-unsupported", "message": "agent lacks session/list"}}
            request_id = self.agent.send_request("session/list", {"cwd": self.args.repo})
            response = self.agent.wait_response(request_id, 15.0)
            sessions = ((response or {}).get("result") or {}).get("sessions") or []
            if not sessions:
                return {"error": {"code": "continue-empty", "message": "no sessions to resume"}}
            return self.initialize_agent_resume(sessions[-1]["sessionId"])
        else:
            request_id = self.agent.send_request(
                "session/new", {"cwd": self.args.repo, "mcpServers": []}
            )
            response = self.agent.wait_response(request_id, 15.0)
            if response is None:
                return {"error": {"code": "acp-session-timeout", "message": "no session/new response"}}
            if "error" in response:
                error = response["error"]
                if error.get("code") in (-32000, -32001) or "auth" in str(error.get("message", "")).lower():
                    if self.auth_methods:
                        auth_id = self.agent.send_request(
                            "authenticate", {"methodId": self.auth_methods[0]["id"]}
                        )
                        auth_response = self.agent.wait_response(auth_id, 30.0)
                        if auth_response and "error" not in auth_response:
                            return self.initialize_agent()
                    return {"error": {"code": "login-required", "message": error.get("message")}}
                return {"error": {"code": "acp-session-failed", "message": error}}
            self.session_meta = response.get("result") or {}
            self.acp_session_id = self.session_meta.get("sessionId")
        self.state = "ready"
        self.write_record()
        return {"acp_session_id": self.acp_session_id, "agent_info": self.agent_info,
                "protocol_version": self.protocol_version, "capabilities": self.capabilities}

    def initialize_agent_resume(self, session_id: str) -> dict[str, Any]:
        session_caps = self.capabilities.get("sessionCapabilities") or {}
        if not session_caps.get("resume") and not self.capabilities.get("loadSession"):
            return {"error": {"code": "resume-unsupported"}}
        method = "session/resume" if session_caps.get("resume") else "session/load"
        request_id = self.agent.send_request(
            method, {"sessionId": session_id, "cwd": self.args.repo, "mcpServers": []}
        )
        response = self.agent.wait_response(request_id, 15.0)
        if response is None or "error" in response:
            return {"error": {"code": "resume-failed", "message": json.dumps(response)}}
        self.session_meta = response.get("result") or {}
        self.acp_session_id = self.session_meta.get("sessionId", session_id)
        self.state = "ready"
        self.write_record()
        return {"acp_session_id": self.acp_session_id, "agent_info": self.agent_info,
                "protocol_version": self.protocol_version, "capabilities": self.capabilities}

    # -- inbound agent messages --------------------------------------------------

    def on_agent_message(self, message: dict[str, Any]) -> None:
        self.last_activity = time.monotonic()
        if "method" in message:
            if "id" in message:
                self.on_agent_request(message)
            else:
                self.on_agent_notification(message)
        else:
            self.agent.resolve_response(message)

    def on_agent_notification(self, message: dict[str, Any]) -> None:
        method = message["method"]
        params = message.get("params") or {}
        if method == "session/update":
            self.on_session_update(params)
        elif method == "$/cancel_request":
            cancelled = params.get("id")
            if cancelled is not None and self.agent.cancel_outbound(cancelled):
                self.events.append({"kind": "outbound_cancelled", "id": cancelled})
                return
            key = normalize_id(cancelled)
            if key in self.pending_permissions:
                self.pending_permissions.pop(key, None)
                self.events.append({"kind": "permission_cancelled", "request_id": cancelled})
                self.write_record()
            else:
                self.events.append({"kind": "cancel_request_unknown", "id": cancelled})
        else:
            self.events.append({"kind": "notification", "method": method, "params": params})

    def on_agent_request(self, message: dict[str, Any]) -> None:
        method = message["method"]
        request_id = message["id"]
        params = message.get("params") or {}
        if method == "session/request_permission":
            tool_call = params.get("toolCall") or {}
            entry = {
                "request_id": request_id,
                "title": tool_call.get("title") or params.get("title") or method,
                "tool_call_id": tool_call.get("toolCallId"),
                "options": [
                    {"id": opt.get("optionId"), "kind": opt.get("kind"), "label": opt.get("name")}
                    for opt in params.get("options") or []
                ],
            }
            self.pending_permissions[normalize_id(request_id)] = entry
            if self.turn["active"] and self.turn["mutation_status"] == "in_progress":
                self.turn["mutation_status"] = "accepted"
            self.events.append({"kind": "request_permission", "request": entry})
            self.write_record()
            with self.turn_cond:
                self.turn_cond.notify_all()
            return
        self.agent.send_message(
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32601, "message": f"client does not implement {method}"}}
        )
        self.events.append({"kind": "unsupported_agent_request", "method": method})

    def on_session_update(self, params: dict[str, Any]) -> None:
        update = params.get("update") or {}
        variant = update.get("sessionUpdate", "unknown")
        turn = self.turn
        if turn["active"] and turn["mutation_status"] == "in_progress":
            turn["mutation_status"] = "accepted"
        if variant == "agent_message_chunk":
            text = ((update.get("content") or {}).get("text")) or ""
            turn["final_text"] += text
        elif variant == "agent_thought_chunk":
            turn["thinking_chars"] += len(((update.get("content") or {}).get("text")) or "")
        elif variant in ("tool_call", "tool_call_update"):
            tool_id = update.get("toolCallId") or f"anon-{len(turn['tool_order'])}"
            known = variant == "tool_call_update" and tool_id in turn["tool_calls"]
            record = turn["tool_calls"].setdefault(
                tool_id, {"kind": update.get("kind"), "title": update.get("title"),
                          "status": update.get("status")}
            )
            for field in ("kind", "title", "status"):
                if update.get(field) is not None:
                    record[field] = update[field]
            if update.get("content") is not None:
                record["error_head"] = str(update.get("content"))[:200]
            if not known:
                turn["tool_order"].append(tool_id)
        elif variant == "usage_update":
            turn["context_usage"] = {"used": update.get("used"), "size": update.get("size")}
        elif variant not in KNOWN_UPDATES:
            self.agent.unknown_updates += 1
        self.events.append({"kind": "session_update", "sessionId": params.get("sessionId"),
                            "update": update})
        self.write_record()

    def on_prompt_response(self, request_id: int, response: dict[str, Any] | None) -> None:
        turn = self.turn
        if response is None or not turn["active"]:
            return
        if "error" in response:
            turn["error"] = response["error"]
            turn["outcome"] = (
                "turn_canceled" if (response["error"] or {}).get("code") == -32800
                else "turn_failed"
            )
        else:
            stop = (response.get("result") or {}).get("stopReason")
            turn["stop_reason"] = stop
            turn["outcome"] = "turn_canceled" if stop == "cancelled" else "turn_completed"
        turn["mutation_status"] = "completed"
        turn["active"] = False
        self.last_prompt = {
            "fingerprint": turn["fingerprint"],
            "written_at": turn["written_at"],
            "transport": "acp",
            "mutation_status": turn["mutation_status"],
            "stop_reason": turn["stop_reason"],
        }
        self.write_record()
        with self.turn_cond:
            self.turn_cond.notify_all()

    def on_agent_exit(self, code: int) -> None:
        self.agent_exited.set()
        self.events.append({"kind": "process_exited", "code": self.agent.exit_code,
                            "signal": self.agent.exit_signal})
        turn = self.turn
        if turn["active"]:
            turn["outcome"] = "process_exited"
            turn["active"] = False
            self.last_prompt = {
                "fingerprint": turn["fingerprint"],
                "written_at": turn["written_at"],
                "transport": "acp",
                "mutation_status": turn["mutation_status"],
                "stop_reason": None,
            }
        for key, entry in list(self.pending_permissions.items()):
            self.pending_permissions.pop(key, None)
        if self.state not in ("stopping", "stopped"):
            self.state = "agent_exited"
        with self.agent.lock:
            stranded = list(self.agent.pending_out.values())
            self.agent.pending_out.clear()
        for slot in stranded:
            if slot["response"] is None:
                slot["response"] = {"error": {"code": "agent-exited",
                                              "message": "agent process exited"}}
            slot["event"].set()
        self.write_record()
        with self.turn_cond:
            self.turn_cond.notify_all()

    # -- ops ---------------------------------------------------------------------

    def op_state(self) -> dict[str, Any]:
        turn = self.turn
        if turn["active"]:
            activity = "waiting" if self.pending_permissions else "busy"
        elif self.agent.exited.is_set():
            activity = "exited"
        else:
            activity = "idle"
        return {
            "state": self.state,
            "holder_pid": os.getpid(),
            "agent_pid": self.agent.proc.pid if self.agent.proc else None,
            "agent_pgid": self.agent.proc.pid if self.agent.proc else None,
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "agent_exit_code": self.agent.exit_code,
            "acp_session_id": self.acp_session_id,
            "session_meta": self.session_meta,
            "protocol_version": self.protocol_version,
            "agent_info": self.agent_info,
            "capabilities": self.capabilities,
            "pending_permissions": list(self.pending_permissions.values()),
            "activity_hint": activity,
            "last_prompt": self.last_prompt,
            "turn_active": turn["active"],
            "turn_outcome": turn.get("outcome"),
            "stop_reason": turn.get("stop_reason"),
            "mutation_status": turn.get("mutation_status"),
            "context_usage": turn.get("context_usage"),
            "event_cursor": self.events.cursor,
            "malformed_stdout_lines": self.agent.malformed_lines,
            "unknown_update_variants": self.agent.unknown_updates,
            "fatal_error": self.fatal_error,
        }

    def turn_receipt(self, wait_timeout: float | None = None,
                     max_final_chars: int = 4000) -> dict[str, Any]:
        turn = self.turn
        outcome = turn.get("outcome")
        mutation_status = turn.get("mutation_status") or "not_started"
        performed = {"completed": True, "accepted": True, "in_progress": True,
                     "not_started": False, "unknown": None}.get(mutation_status)
        final_text = turn.get("final_text") or ""
        truncated = False
        if len(final_text) > max_final_chars:
            final_text = final_text[:max_final_chars]
            truncated = True
        tools = list(turn["tool_calls"].values())
        failed = [t for t in tools if (t.get("status") or "") in ("failed", "error")]
        kinds: dict[str, int] = {}
        for tool in tools:
            kind = tool.get("kind") or "other"
            kinds[kind] = kinds.get(kind, 0) + 1
        receipt = {
            "acp_session_id": self.acp_session_id,
            "prompt_fingerprint": turn.get("fingerprint"),
            "outcome": outcome or ("in_progress" if turn["active"] else None),
            "stop_reason": turn.get("stop_reason"),
            "mutation_status": mutation_status,
            "mutation_performed": performed,
            "duration_ms": round((time.monotonic() - turn["started_at"]) * 1000)
            if turn.get("started_at") else None,
            "final_text": final_text,
            "final_text_truncated": truncated,
            "event_log_path": str(self.events.path) if truncated else None,
            "tool_calls": {"count": len(tools), "kinds": kinds, "failed": len(failed)},
            "side_effects": {
                "files_changed": sum(
                    1 for t in tools if (t.get("kind") or "") in ("edit", "write", "delete")
                ),
                "commands_run": sum(
                    1 for t in tools if (t.get("kind") or "") in ("execute", "shell")
                ),
            },
            "failed_tools": [
                {"title": t.get("title"), "kind": t.get("kind"),
                 "error_head": t.get("error_head")}
                for t in failed[:3]
            ],
            "thinking_chars": turn.get("thinking_chars", 0),
            "context_usage": turn.get("context_usage"),
            "pending_permissions": list(self.pending_permissions.values()),
            "event_cursor": self.events.cursor,
            "event_log_bytes": self.events.path.stat().st_size
            if self.events.path.exists() else 0,
        }
        if turn.get("error"):
            receipt["error"] = turn["error"]
            if self.agent.stderr_pump:
                receipt["error"]["stderr_tail"] = self.agent.stderr_pump.tail()
        return receipt

    def op_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.agent.exited.is_set() or self.agent.proc is None:
            return {"outcome": "process_exited", "mutation_status": "not_started",
                    "mutation_performed": False,
                    "error": {"code": "agent-not-running", "message": "agent process is not running"}}
        with self.lock:
            if self.turn["active"]:
                return {"error": {"code": "prompt-in-progress",
                                  "message": "a prompt turn is already active"},
                        "outcome": "in_progress", "mutation_status": self.turn["mutation_status"]}
            text = params.get("text") or ""
            fingerprint = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
            previous = self.last_prompt or {}
            self.turn = self._empty_turn()
            self.turn.update({
                "active": True,
                "fingerprint": fingerprint,
                "started_at": time.monotonic(),
            })
            duplicate = None
            if previous.get("fingerprint") == fingerprint:
                duplicate = {
                    "code": "duplicate-prompt-warning",
                    "previous_transport": previous.get("transport"),
                    "previous_written_at": previous.get("written_at"),
                    "previous_mutation_status": previous.get("mutation_status"),
                    "previous_stop_reason": previous.get("stop_reason"),
                }
            request_id = self.agent.send_request(
                "session/prompt",
                {
                    "sessionId": self.acp_session_id,
                    "prompt": [{"type": "text", "text": text}],
                },
            )
            if normalize_id(request_id) not in self.agent.pending_out:
                self.turn["active"] = False
                self.turn["mutation_status"] = "not_started"
                self.turn["outcome"] = "turn_failed"
                self.last_prompt = {
                    "fingerprint": fingerprint,
                    "written_at": None,
                    "transport": "acp",
                    "mutation_status": "not_started",
                    "stop_reason": None,
                }
                self.write_record()
                return {"outcome": "turn_failed", "mutation_status": "not_started",
                        "mutation_performed": False,
                        "error": {"code": "acp-write-failed", "message": "prompt frame was not written"}}
            self.turn["request_id"] = request_id
            self.turn["written_at"] = round(time.time(), 3)
            self.turn["mutation_status"] = "in_progress"
            self.last_prompt = {
                "fingerprint": fingerprint,
                "written_at": self.turn["written_at"],
                "transport": "acp",
                "mutation_status": "in_progress",
                "stop_reason": None,
            }
            self.write_record()

        threading.Thread(
            target=self._await_prompt, args=(request_id,), daemon=True
        ).start()
        wait = params.get("wait", True)
        timeout = params.get("timeout")
        max_chars = params.get("max_final_chars", 4000)
        if not wait:
            return {"outcome": "in_progress", "mutation_status": "in_progress",
                    "mutation_performed": True, "prompt_fingerprint": fingerprint,
                    "duplicate_warning": duplicate, "acp_session_id": self.acp_session_id}
        deadline = time.monotonic() + timeout if timeout else None
        with self.turn_cond:
            while self.turn["active"]:
                remaining = (deadline - time.monotonic()) if deadline else 0.5
                if deadline and remaining <= 0:
                    break
                self.turn_cond.wait(timeout=max(remaining, 0.05))
                if deadline and time.monotonic() >= deadline and self.turn["active"]:
                    break
        if self.turn["active"]:
            return {**self.turn_receipt(max_final_chars=max_chars),
                    "outcome": "prompt_timeout",
                    "duplicate_warning": duplicate}
        receipt = self.turn_receipt(max_final_chars=max_chars)
        receipt["duplicate_warning"] = duplicate
        return receipt

    def _await_prompt(self, request_id: int) -> None:
        response = self.agent.wait_response(request_id, None)
        self.on_prompt_response(request_id, response)

    def op_wait(self, params: dict[str, Any]) -> dict[str, Any]:
        timeout = params.get("timeout")
        deadline = time.monotonic() + timeout if timeout else None
        with self.turn_cond:
            while self.turn["active"]:
                remaining = (deadline - time.monotonic()) if deadline else 0.5
                if deadline and remaining <= 0:
                    return {**self.turn_receipt(), "outcome": "prompt_timeout"}
                self.turn_cond.wait(timeout=max(remaining, 0.05))
        return self.turn_receipt()

    def op_permit(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = params.get("request_id")
        option = params.get("option")
        pending = self.pending_permissions
        if not pending:
            return {"error": {"code": "no-pending-permission",
                              "message": "no permission request is pending"}}
        if request_id is None:
            if len(pending) > 1:
                return {"error": {"code": "request-id-required",
                                  "message": f"{len(pending)} permissions pending; --request-id required"}}
            request_id = next(iter(pending))
        key = normalize_id(request_id)
        entry = pending.get(key)
        if entry is None:
            return {"error": {"code": "unknown-request",
                              "message": f"no pending permission with id {request_id}"}}
        outcome = {"outcome": "cancelled"} if option in (None, "cancelled", "cancel") else {
            "outcome": "selected", "optionId": option
        }
        self.agent.send_message(
            {"jsonrpc": "2.0", "id": entry["request_id"], "result": {"outcome": outcome}}
        )
        pending.pop(key, None)
        self.events.append({"kind": "permission_answered", "request_id": request_id,
                            "option": option})
        self.write_record()
        return {"permitted": request_id, "option": option,
                "pending_permissions": list(pending.values())}

    def op_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.turn["active"]:
            return {"outcome": "no-active-turn", "mutation_status": self.turn.get("mutation_status")}
        for key, entry in list(self.pending_permissions.items()):
            self.agent.send_message(
                {"jsonrpc": "2.0", "id": entry["request_id"],
                 "result": {"outcome": {"outcome": "cancelled"}}}
            )
            self.pending_permissions.pop(key, None)
        self.turn["cancel_requested"] = True
        self.agent.send_message(
            {"jsonrpc": "2.0", "method": "session/cancel",
             "params": {"sessionId": self.acp_session_id}}
        )
        timeout = params.get("timeout", CANCEL_GRACE)
        deadline = time.monotonic() + timeout
        with self.turn_cond:
            while self.turn["active"]:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {**self.turn_receipt(), "outcome": "cancel-unconfirmed"}
                self.turn_cond.wait(timeout=remaining)
        return self.turn_receipt()

    def op_capture(self, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("full"):
            size = self.events.path.stat().st_size if self.events.path.exists() else 0
            result = {"level": "L3", "event_log_path": str(self.events.path),
                      "event_log_bytes": size}
            if params.get("inline"):
                result["events"] = self.events.read_since(0, params.get("limit"))
            return result
        if params.get("since") is not None:
            return {"level": "L2",
                    "events": self.events.read_since(int(params["since"]), params.get("limit")),
                    "event_cursor": self.events.cursor}
        if params.get("tools"):
            tools = [
                {"tool_call_id": tid, **self.turn["tool_calls"][tid]}
                for tid in self.turn["tool_order"]
            ]
            return {"level": "L1", "tool_calls": tools}
        if params.get("lines") is not None:
            return {"level": "L2",
                    "events": self.events.read_since(
                        max(0, self.events.cursor - int(params["lines"])), None),
                    "event_cursor": self.events.cursor}
        return {"level": "L0", **self.turn_receipt()}

    def op_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        force = bool(params.get("force"))
        self.stop_requested = True
        self.state = "stopping"
        self.write_record()
        for key, entry in list(self.pending_permissions.items()):
            self.agent.send_message(
                {"jsonrpc": "2.0", "id": entry["request_id"],
                 "result": {"outcome": {"outcome": "cancelled"}}}
            )
            self.pending_permissions.pop(key, None)
        if not force:
            if self.turn["active"]:
                self.agent.send_message(
                    {"jsonrpc": "2.0", "method": "session/cancel",
                     "params": {"sessionId": self.acp_session_id}}
                )
                deadline = time.monotonic() + CANCEL_GRACE
                with self.turn_cond:
                    while self.turn["active"] and time.monotonic() < deadline:
                        self.turn_cond.wait(timeout=deadline - time.monotonic())
            session_caps = self.capabilities.get("sessionCapabilities") or {}
            if session_caps.get("close") and self.acp_session_id and not self.agent.exited.is_set():
                request_id = self.agent.send_request(
                    "session/close", {"sessionId": self.acp_session_id}
                )
                self.agent.wait_response(request_id, CANCEL_GRACE)
            if self.agent.proc and self.agent.proc.stdin:
                try:
                    self.agent.proc.stdin.close()
                except OSError:
                    pass
                self.agent.exited.wait(EXIT_GRACE)
        residual = self._terminate_group(force)
        self.state = "stopped"
        self.write_record()
        result = {"stopped": True, "residual_pids": residual,
                  "agent_exit_code": self.agent.exit_code,
                  "agent_exit_signal": self.agent.exit_signal,
                  "mutation_status": self.turn.get("mutation_status"),
                  "_exit_after_reply": True}
        return result

    def _terminate_group(self, force: bool) -> list[int]:
        proc = self.agent.proc
        if proc is None:
            return []
        pgid = proc.pid
        try:
            pgid = os.getpgid(proc.pid)
        except OSError:
            pass
        if not self.agent.exited.is_set():
            try:
                os.killpg(pgid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            if not self.agent.exited.wait(TERM_GRACE):
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                self.agent.exited.wait(2.0)
        for member in group_members(pgid):
            if member != proc.pid and process_alive(member):
                try:
                    os.kill(member, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        time.sleep(0.1)
        return [pid for pid in group_members(pgid) if process_alive(pid)]

    # -- socket server ------------------------------------------------------------

    def handle_request(self, message: dict[str, Any]) -> dict[str, Any]:
        op = message.get("op")
        params = message.get("params") or {}
        if op == "state":
            return self.op_state()
        if op == "prompt":
            return self.op_prompt(params)
        if op == "wait":
            return self.op_wait(params)
        if op == "permit":
            return self.op_permit(params)
        if op == "cancel":
            return self.op_cancel(params)
        if op == "capture":
            return self.op_capture(params)
        if op == "stop":
            return self.op_stop(params)
        return {"error": {"code": "unknown-op", "message": f"unsupported op {op}"}}

    def serve_connection(self, connection: socket.socket) -> None:
        try:
            buffer = bytearray()
            while True:
                data = connection.recv(65536)
                if not data:
                    return
                buffer.extend(data)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if not line.strip():
                        continue
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except ValueError:
                        connection.sendall(b'{"error":{"code":"bad-request"}}\n')
                        continue
                    response = self.handle_request(message)
                    exit_after = bool(response.pop("_exit_after_reply", False))
                    connection.sendall(canonical(response) + b"\n")
                    if exit_after:
                        connection.close()
                        os._exit(0)
        except (OSError, ValueError):
            return
        finally:
            try:
                connection.close()
            except OSError:
                pass

    def verify_peer(self, connection: socket.socket) -> bool:
        if sys.platform == "darwin":
            uid = ctypes.c_uint()
            gid = ctypes.c_uint()
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) == 0:
                return uid.value == os.getuid()
            return False
        if hasattr(socket, "SO_PEERCRED"):
            try:
                _pid, uid, _gid = struct.unpack(
                    "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                )
                return uid == os.getuid()
            except (OSError, struct.error):
                pass
        return os.stat(connection.fileno()).st_uid == os.getuid()

    def idle_watcher(self) -> None:
        while True:
            time.sleep(15)
            if self.agent.exited.is_set() and not self.turn["active"]:
                if time.monotonic() - self.last_activity > IDLE_EXIT_SECONDS:
                    self.state = "stopped"
                    self.write_record()
                    os._exit(0)

    def run(self) -> int:
        self.created_at = round(time.time(), 3)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.socket_path.parent, 0o700)
        if self.socket_path.exists() or self.socket_path.is_symlink():
            self.socket_path.unlink()
        self.listener.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        self.listener.listen(16)
        link = self.record_dir / "holder.sock"
        if link != self.socket_path:
            try:
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to(self.socket_path)
            except OSError:
                pass
        self.write_record(socket_path=str(self.socket_path))
        result = self.initialize_agent(
            resume=self.args.resume, use_continue=self.args.use_continue
        )
        if "error" in result:
            self.fatal_error = result["error"]
            self.state = "error"
            self.write_record()
            if result["error"].get("code") == "acp-protocol-version-unsupported":
                self._terminate_group(force=True)
            elif self.agent.proc and not self.agent.exited.is_set():
                pass
        threading.Thread(target=self.idle_watcher, daemon=True).start()
        while not self.stop_requested or self.listener:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                break
            if not self.verify_peer(connection):
                connection.close()
                continue
            threading.Thread(
                target=self.serve_connection, args=(connection,), daemon=True
            ).start()
        return 0


def run_probe(args: argparse.Namespace) -> int:
    """Short-lived preflight probe: spawn, initialize, session/new, close, exit."""
    env = dict(os.environ)
    env["NO_BROWSER"] = "true"
    result: dict[str, Any] = {"probe": True}
    try:
        argv = shlex.split(args.command)
        proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=args.repo, env=env, start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"probe": True, "error": {"code": "acp-spawn-failed",
                                                   "message": str(exc)}}))
        return 0
    pending: dict[str, dict[str, Any]] = {}
    next_id = [0]
    lock = threading.Lock()

    def send(method: str, params: dict[str, Any]) -> int:
        with lock:
            next_id[0] += 1
            rid = next_id[0]
            pending[str(rid)] = {"event": threading.Event(), "response": None}
        try:
            proc.stdin.write(canonical({"jsonrpc": "2.0", "id": rid,
                                        "method": method, "params": params}) + b"\n")
            proc.stdin.flush()
        except OSError:
            pass
        return rid

    def wait(rid: int, timeout: float) -> dict[str, Any] | None:
        slot = pending[str(rid)]
        slot["event"].wait(timeout)
        return slot["response"]

    def reader() -> None:
        while True:
            line = proc.stdout.readline()
            if not line:
                for slot in pending.values():
                    if slot["response"] is None:
                        slot["response"] = {"error": {"code": "probe-eof"}}
                        slot["event"].set()
                return
            try:
                message = json.loads(line.decode("utf-8", "replace"))
            except ValueError:
                continue
            if "id" in message and "method" not in message:
                slot = pending.get(str(message["id"]))
                if slot is None and isinstance(message["id"], int):
                    slot = pending.get(str(message["id"]))
                if slot:
                    slot["response"] = message
                    slot["event"].set()
            elif "id" in message:
                try:
                    proc.stdin.write(canonical(
                        {"jsonrpc": "2.0", "id": message["id"],
                         "error": {"code": -32601, "message": "unsupported"}}) + b"\n")
                    proc.stdin.flush()
                except OSError:
                    pass

    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(
        target=lambda: [proc.stderr.read(65536) for _ in iter(int, 1) if not proc.stderr.closed],
        daemon=True,
    ).start()
    response = wait(send("initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False},
                               "terminal": False},
    }), 15.0)
    if response is None:
        result["error"] = {"code": "acp-initialize-timeout"}
    elif "error" in response:
        result["error"] = {"code": "acp-initialize-failed", "detail": response["error"]}
    else:
        init = response.get("result") or {}
        result["protocol_version"] = init.get("protocolVersion")
        result["agent_info"] = init.get("agentInfo") or {}
        caps = init.get("agentCapabilities") or {}
        session_caps = caps.get("sessionCapabilities") or {}
        result["capabilities"] = {
            "prompt": True,
            "cancel": True,
            "permission": True,
            "load_session": bool(caps.get("loadSession")),
            "resume": bool(session_caps.get("resume")),
            "list": bool(session_caps.get("list")),
            "close": bool(session_caps.get("close")),
            "set_config_option": True,
        }
        result["auth_methods"] = init.get("authMethods") or []
        if result["protocol_version"] != PROTOCOL_VERSION:
            result["error"] = {"code": "acp-protocol-version-unsupported",
                               "agent_version": result["protocol_version"]}
        else:
            response = wait(send("session/new", {"cwd": args.repo, "mcpServers": []}), 15.0)
            if response and "error" in response:
                message = str((response["error"] or {}).get("message", "")).lower()
                if "auth" in message or (response["error"] or {}).get("code") in (-32000, -32001):
                    result["login_required"] = True
                else:
                    result["error"] = {"code": "acp-session-failed",
                                       "detail": response["error"]}
            elif response:
                result["login_required"] = False
                result["session_probe"] = (response.get("result") or {}).get("sessionId")
                if result["capabilities"]["close"] and result.get("session_probe"):
                    wait(send("session/close",
                              {"sessionId": result["session_probe"]}), 5.0)
            else:
                result["error"] = {"code": "acp-session-timeout"}
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = proc.pid
    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=EXIT_GRACE)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=TERM_GRACE)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-dir")
    parser.add_argument("--socket")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--session", default="")
    parser.add_argument("--command", required=True)
    parser.add_argument("--resume")
    parser.add_argument("--continue", dest="use_continue", action="store_true")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        return run_probe(args)
    holder = Holder(args)
    return holder.run()


if __name__ == "__main__":
    raise SystemExit(main())
