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


def message_chunk(session_id: str, text: str, message_id: str | None = None) -> None:
    update = {
        "sessionUpdate": "agent_message_chunk",
        "content": {"type": "text", "text": text},
    }
    if message_id is not None:
        update["messageId"] = message_id
    session_update(session_id, update)


def thought_chunk(session_id: str, text: str, message_id: str | None = None) -> None:
    update = {
        "sessionUpdate": "agent_thought_chunk",
        "content": {"type": "text", "text": text},
    }
    if message_id is not None:
        update["messageId"] = message_id
    session_update(session_id, update)


class MockAgent:
    def __init__(self, scenario: str, caps: set[str], turn_ms: int, flood_bytes: int,
                 steering: str = "none", ignore_cancel: bool = False,
                 caps_objects: bool = False):
        self.scenario = scenario
        # Issue #65: native mid-turn steering. "none" leaves `_session/steering`
        # unimplemented (JSON-RPC -32601), exactly like a platform without the
        # entry; every other value advertises `_meta.steering` and answers.
        self.steering = steering
        # Issue #65: a turn that does NOT stop when cancelled, so the composite
        # steering path can be proven to send nothing on an unconfirmed cancel.
        self.ignore_cancel = ignore_cancel
        self.steer_texts: list[str] = []
        self.caps = caps
        self.caps_objects = caps_objects
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
        self.config_fixture = self._load_config_fixture()
        self.list_pages = self._load_list_pages()
        if self.list_pages:
            for page in self.list_pages:
                for entry in page.get("sessions") or []:
                    if isinstance(entry, dict) and entry.get("sessionId"):
                        self.sessions.setdefault(
                            entry["sessionId"], {"cwd": entry.get("cwd", "")}
                        )
        log_event({"event": "mock_start", "scenario": scenario, "caps": sorted(caps)})

    @staticmethod
    def _load_config_fixture() -> dict[str, Any]:
        """Issue #33 fixture. ``MOCK_ACP_CONFIG`` JSON object keys:

        - ``new``/``resume``: configOptions list embedded in session/new and
          session/resume|load results (``null`` omits the key entirely)
        - ``set_result``: full result object for session/set_config_option
        - ``set_error``: error object returned instead of a result
        - ``set_drop``: truthy -> never respond (client timeout path)
        - ``set_notify``: configOptions list emitted as a config_option_update
          shortly after a successful set response
        """
        raw = os.environ.get("MOCK_ACP_CONFIG", "")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _load_list_pages() -> list[dict[str, Any]] | None:
        raw = os.environ.get("MOCK_ACP_LIST_PAGES", "")
        if not raw:
            return None
        try:
            pages = json.loads(raw)
        except ValueError:
            return None
        return pages if isinstance(pages, list) else None

    # -- outbound helpers -------------------------------------------------

    def outbound_id(self) -> int:
        self.next_outbound_id += 1
        return self.next_outbound_id

    def ask_permission(
        self,
        session_id: str,
        title: str,
        options: list,
        tool_call_id: str | None = None,
    ) -> int:
        request_id = self.outbound_id()
        self.pending[request_id] = "session/request_permission"
        option_objs = []
        for option in options:
            if isinstance(option, str):
                option_objs.append({"optionId": option, "name": option, "kind": "allow_once"})
            else:
                option_objs.append(option)
        request(
            request_id,
            "session/request_permission",
            {
                "sessionId": session_id,
                "toolCall": {
                    "toolCallId": tool_call_id or f"tc-{request_id}",
                    "title": title,
                },
                "options": option_objs,
            },
        )
        return request_id

    # -- capability map ----------------------------------------------------

    def _cap(self, name: str) -> Any:
        enabled = name in self.caps
        return {} if (enabled and self.caps_objects) else enabled

    def capabilities(self) -> dict[str, Any]:
        return {
            "loadSession": "load" in self.caps,
            "sessionCapabilities": {
                "list": self._cap("list"),
                "resume": self._cap("resume"),
                "close": self._cap("close"),
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
            # Issue #65: the steering wire protocol advertises support at the
            # top-level `_meta.steering`, a sibling of `agentCapabilities`.
            **({"_meta": {"steering": {"supported": True}}}
               if self.steering != "none" else {}),
        }
        if self.scenario == "numeric_string_id":
            respond(str(request_id), result)
        else:
            respond(request_id, result)

    def on_authenticate(self, request_id: Any, params: dict[str, Any]) -> None:
        self.authenticated = True
        respond(request_id, {})

    def on_session_new(self, request_id: Any, params: dict[str, Any]) -> None:
        if self.scenario == "session_new_fails":
            # Issue #65: what OpenCode did when its bootstrap could not reach the
            # network - the process stays alive and healthy, but no session id is
            # ever negotiated. Nothing may be dispatched onto such a holder.
            respond(
                request_id,
                error={"code": -32603, "message": "Internal error: service failure",
                       "data": {"service": "directory"}},
            )
            return
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
        result: dict[str, Any] = {"sessionId": session_id,
                                "configOptions": self.config_options()}
        if "new" in self.config_fixture:
            if self.config_fixture["new"] is None:
                result.pop("configOptions", None)
            else:
                result["configOptions"] = self.config_fixture["new"]
        respond(request_id, result)

    def on_session_list(self, request_id: Any, params: dict[str, Any]) -> None:
        if "list" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/list unsupported"})
            return
        if self.list_pages is not None:
            cursor = params.get("cursor")
            index = 0
            if cursor is not None:
                index = next(
                    (i + 1 for i, page in enumerate(self.list_pages)
                     if page.get("nextCursor") == cursor),
                    -1,
                )
            if index < 0 or index >= len(self.list_pages):
                respond(request_id, {"sessions": []})
                return
            page = self.list_pages[index]
            entries = []
            for entry in page.get("sessions") or []:
                if isinstance(entry, dict):
                    entries.append(entry)
                    if entry.get("sessionId"):
                        self.sessions.setdefault(
                            entry["sessionId"],
                            {"cwd": entry.get("cwd", params.get("cwd", ""))},
                        )
            result: dict[str, Any] = {"sessions": entries}
            if page.get("nextCursor") is not None:
                result["nextCursor"] = page["nextCursor"]
            log_event({"event": "session_list_page", "index": index, "cursor": cursor})
            respond(request_id, result)
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
        result: dict[str, Any] = {"sessionId": session_id}
        if self.config_fixture.get("resume") is not None:
            result["configOptions"] = self.config_fixture["resume"]
        respond(request_id, result)

    def on_session_close(self, request_id: Any, params: dict[str, Any]) -> None:
        if "close" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/close unsupported"})
            return
        self.sessions.pop(params.get("sessionId", ""), None)
        respond(request_id, {})

    # Mirrors the codex-acp adapter's session/set_config_option result: the
    # full configOptions list with upstream display names and descriptions.
    CONFIG_OPTIONS = [
        {"id": "mode", "name": "Mode",
         "description": "Approval and sandboxing preset for the session",
         "category": "mode", "type": "select", "options": [
             {"value": "read-only", "name": "Ask for approval",
              "description": "Always ask to edit external files and use the internet"},
             {"value": "agent", "name": "Approve for me",
              "description": "Only ask for actions detected as potentially unsafe"},
             {"value": "agent-full-access", "name": "Full access",
              "description": "Unrestricted access to the internet and any file on your computer"},
         ]},
        {"id": "model", "name": "Model",
         "description": "Model Codex uses for the session",
         "category": "model", "type": "select", "options": [
             {"value": "gpt-5.6-sol", "name": "5.6 Sol",
              "description": "Fast and affordable agentic coding model."},
             {"value": "gpt-6-astra", "name": "6 Astra",
              "description": "Frontier agentic coding model."},
         ]},
        {"id": "reasoning_effort", "name": "Reasoning effort",
         "description": "Reasoning effort Codex uses for the session",
         "category": "reasoning_effort", "type": "select", "options": [
             {"value": "low", "name": "Low"},
             {"value": "medium", "name": "Medium"},
             {"value": "high", "name": "High"},
         ]},
        {"id": "fast-mode", "name": "Fast mode",
         "description": "Fast service tier for the session",
         "category": "fast-mode", "type": "select", "options": [
             {"value": "off", "name": "Off"},
             {"value": "on", "name": "On"},
         ]},
    ]

    # Cursor's parameterized picker surface (client _meta
    # parameterizedModelPicker): separate model/effort/fast options with
    # base model IDs and string "true"/"false" fast values.
    CURSOR_CONFIG_OPTIONS = [
        {"id": "mode", "name": "Mode",
         "description": "Controls how the agent executes tasks",
         "category": "mode", "type": "select", "options": [
             {"value": "agent", "name": "Agent"},
             {"value": "plan", "name": "Plan"},
             {"value": "ask", "name": "Ask"},
         ]},
        {"id": "model", "name": "Model",
         "description": "Controls which model variant is used for responses",
         "category": "model", "type": "select", "options": [
             {"value": "default", "name": "Auto"},
             {"value": "grok-4.6", "name": "Cursor Grok 4.6"},
             {"value": "claude-fable-5-1", "name": "Claude Fable 5.1"},
         ]},
        {"id": "effort", "name": "Effort",
         "description": "Reasoning effort for the session",
         "category": "effort", "type": "select", "options": [
             {"value": "low", "name": "Low"},
             {"value": "medium", "name": "Medium"},
             {"value": "high", "name": "High"},
             {"value": "xhigh", "name": "Extra High"},
         ]},
        {"id": "fast", "name": "Fast",
         "description": "Fast serving tier for the session",
         "category": "fast", "type": "select", "options": [
             {"value": "false", "name": "Off"},
             {"value": "true", "name": "Fast"},
         ]},
    ]

    def config_options(self) -> list[dict[str, Any]]:
        if "cursor-params" in self.caps:
            return self.CURSOR_CONFIG_OPTIONS
        return self.CONFIG_OPTIONS

    def on_set_config(self, request_id: Any, params: dict[str, Any]) -> None:
        config_id = params.get("configId") or params.get("config_id")
        log_event({"event": "set_config_option", "params": params})
        fixture = self.config_fixture
        if fixture.get("set_drop"):
            return  # no response: client-side timeout path
        error = fixture.get("set_error")
        if error is not None:
            respond(request_id, error=error)
            return
        if "reject-fast" in self.caps and config_id in ("fast-mode", "fast"):
            respond(
                request_id,
                error={
                    "code": -32602,
                    "message": f"fast-mode unavailable in this build: {params.get('value')}",
                },
            )
            return
        if "strict-config" in self.caps:
            option = next(
                (entry for entry in self.config_options() if entry.get("id") == config_id),
                None,
            )
            values = {entry.get("value") for entry in (option or {}).get("options") or []}
            if option is None or (values and params.get("value") not in values):
                respond(
                    request_id,
                    error={
                        "code": -32602,
                        "message": f"unsupported config option {config_id}={params.get('value')}",
                    },
                )
                return
        if config_id is not None:
            self.configured[str(config_id)] = params.get("value")
        result = fixture.get("set_result")
        if not isinstance(result, dict):
            result = {"configOptions": self.config_options()}
        respond(request_id, result)
        notify_options = fixture.get("set_notify")
        if isinstance(notify_options, list):
            time.sleep(0.4)
            session_update(
                params.get("sessionId", ""),
                {
                    "sessionUpdate": "config_option_update",
                    "configOptions": notify_options,
                },
            )

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
        if scenario == "handler_raises":
            # Issue #95: by-position `params` is legal JSON-RPC, and the
            # client's session/update handler reads `params` as an object, so
            # this array raises inside on_agent_message. It is one reachable
            # trigger, not the contract: what is under test is that the reader
            # survives it and still delivers what follows.
            send_raw(json.dumps({
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": ["kaola-i95-payload-secret", session_id],
            }).encode("utf-8") + b"\n")
            message_chunk(session_id, "MOCK-REPLY after handler failure")
            self.finish_turn(request_id)
            return
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
        if scenario == "watch_projection":
            thought_chunk(
                session_id,
                "the cookie is cleared before redirect.",
                message_id="m1",
            )
            session_update(
                session_id,
                {
                    "sessionUpdate": "user_message_chunk",
                    "content": {"type": "text", "text": text or "Fix the login redirect loop."},
                },
            )
            message_chunk(session_id, "I'll start by ", message_id="m1")
            message_chunk(session_id, "reading the auth middleware.", message_id="m1")
            session_update(
                session_id,
                {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "call_7",
                    "title": "Edit src/auth/middleware.ts",
                    "kind": "edit",
                    "status": "completed",
                    "locations": [{"path": "src/auth/middleware.ts", "line": 88}],
                    "content": [
                        {
                            "type": "diff",
                            "path": "src/auth/middleware.ts",
                            "oldText": "res.redirect('/login')",
                            "newText": "if (!req.path.startsWith('/login')) res.redirect('/login')",
                        },
                        {"type": "text", "text": "patched redirect guard"},
                    ],
                },
            )
            session_update(
                session_id,
                {
                    "sessionUpdate": "plan",
                    "entries": [
                        {"content": "Read middleware", "priority": "high", "status": "completed"},
                        {"content": "Stale merged entry", "priority": "low", "status": "pending"},
                    ],
                },
            )
            session_update(
                session_id,
                {
                    "sessionUpdate": "plan",
                    "entries": [
                        {"content": "Read middleware", "priority": "high", "status": "completed"},
                        {"content": "Patch redirect guard", "priority": "high", "status": "in_progress"},
                    ],
                },
            )
            session_update(
                session_id,
                {"sessionUpdate": "usage_update", "used": 38211, "size": 262144},
            )
            session_update(
                session_id,
                {
                    "sessionUpdate": "current_mode_update",
                    "currentModeId": "plan",
                    "availableModes": [
                        {"id": "plan", "name": "Plan"},
                        {"id": "yolo", "name": "Yolo"},
                    ],
                },
            )
            self.ask_permission(
                session_id,
                "Exit plan mode and start editing?",
                [
                    {"optionId": "allow_once", "name": "Allow once", "kind": "allow_once"},
                    {"optionId": "reject_once", "name": "Reject", "kind": "reject_once"},
                ],
                tool_call_id="call_8",
            )
            log_event({"event": "watch_projection_emitted"})
            return
        if scenario == "follow_flood":
            # >256 session/update notifications so a stalled follower queue can
            # hit the follow.md drop cap without needing the test to count them.
            for index in range(280):
                message_chunk(session_id, f"flood-{index}", message_id="flood")
            session_update(
                session_id,
                {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "call_flood",
                    "title": "Flood complete marker",
                    "kind": "read",
                    "status": "completed",
                    "locations": [{"path": "flood.txt", "line": 1}],
                    "content": [{"type": "text", "text": "flood-complete"}],
                },
            )
            log_event({"event": "follow_flood_emitted"})
            self.finish_turn(request_id)
            return
        if scenario == "tool_call_only":
            session_update(
                session_id,
                {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "call_solo",
                    "title": "Read flood.txt",
                    "kind": "read",
                    "status": "completed",
                    "locations": [{"path": "flood.txt", "line": 1}],
                    "content": [{"type": "text", "text": "solo-tool"}],
                },
            )
            log_event({"event": "tool_call_only_emitted"})
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
        if self.scenario in (
            "normal", "garbage_lines", "stderr_flood", "slow", "cancel_race",
            "watch_projection", "follow_flood", "tool_call_only",
        ):
            thread = threading.Thread(
                target=self.run_prompt, args=(request_id, session_id, text), daemon=True
            )
            thread.start()
            return
        self.run_prompt(request_id, session_id, text)

    def on_steering(self, request_id: Any, params: dict[str, Any]) -> None:
        """Issue #65: the `_session/steering` extension, scripted per mode."""
        text = " ".join(
            part.get("text", "") for part in params.get("prompt", []) if isinstance(part, dict)
        )
        with self.lock:
            active = self.active_turn
        log_event({"event": "steering", "text": text, "mode": self.steering,
                   "turn_active": active is not None})
        if self.steering == "none":
            respond(request_id, error={"code": -32601,
                                       "message": "unsupported: _session/steering"})
            return
        if self.steering == "silent":
            return
        if self.steering == "error":
            respond(request_id, error={"code": -32602, "message": "mock refuses this steer"})
            return
        if self.steering == "weird":
            respond(request_id, {"outcome": "somethingElse"})
            return
        if self.steering == "promptRequired":
            respond(request_id, {"outcome": "promptRequired", "reason": "noRunningTurn"})
            return
        if self.steering == "startedNewTurn":
            respond(request_id, {"outcome": "startedNewTurn"})
            return
        # injected: the running turn really takes the text
        self.steer_texts.append(text)
        if active is not None:
            message_chunk(active[1], f"MOCK-STEERED {text[:64]}")
        respond(request_id, {"outcome": "injected"})

    def on_cancel_notification(self, params: dict[str, Any]) -> None:
        log_event({"event": "session_cancel", "params": params,
                   "ignored": self.ignore_cancel})
        if self.ignore_cancel:
            return
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
        log_event({
            "event": "inbound_frame",
            "method": message.get("method"),
            "id": message.get("id"),
            "has_result": "result" in message,
            "has_error": "error" in message,
        })
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
            self.on_session_list(request_id, params)
            return
        if method == "_session/steering":
            self.on_steering(request_id, params)
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
    parser.add_argument("--caps-objects", action="store_true")
    parser.add_argument("--turn-ms", type=int, default=0)
    parser.add_argument("--flood-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--ignore-cancel", action="store_true")
    parser.add_argument("--steering", default="none",
                        choices=("none", "injected", "promptRequired", "startedNewTurn",
                                 "error", "silent", "weird"))
    args, _unknown = parser.parse_known_args()
    caps = {item for item in args.caps.split(",") if item}
    agent = MockAgent(args.scenario, caps, args.turn_ms, args.flood_bytes,
                      steering=args.steering, ignore_cancel=args.ignore_cancel,
                      caps_objects=args.caps_objects)
    return agent.serve()


if __name__ == "__main__":
    raise SystemExit(main())
