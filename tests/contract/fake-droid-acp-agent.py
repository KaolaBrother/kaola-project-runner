#!/usr/bin/env python3
"""Scriptable fake Droid ACP agent for the Issue #58 droid contract suite.

Models the live-verified droid 0.220.0 native ACP surface (``droid exec
--output-format acp``): initialize advertises no ``configOptions``; the
session/new result declares exactly three select options (``autonomy_level``,
``model``, ``reasoning_effort``) with the observed defaults (auto-high /
gpt-5.6-sol / high); session/set_config_option accepts only those ids and
their option values (unknown id -> -32602 "Unknown config option", invalid
value -> -32602 "Invalid ..."); session/resume and session/load return the
saved selection without echoing the sessionId; prompt turns end with
``stopReason: end_turn``.

``DROID_ACP_LOG`` names a JSONL path recording initialize, session/new,
set_config_option (configId/value), resume, list, prompt, and exit events.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from typing import Any

LOG_PATH = os.environ.get("DROID_ACP_LOG", "")
LOG_LOCK = threading.Lock()
STDOUT_LOCK = threading.Lock()

AUTONOMY_VALUES = ("normal", "spec", "auto-low", "auto-medium", "auto-high")
MODEL_VALUES = ("auto", "gpt-5.6-sol", "gpt-5.6-sol-fast", "grok-4.7", "claude-opus-5",
                "deepseek-v4-pro",
                # Issue #111 read these three from the live 51-value catalog;
                # the Runner core preset names kimi-k3. kimi-k2.7-code stays
                # so the deleted alternative tier (Issue #117) is refused by
                # tier, not by catalog absence.
                "kimi-k3", "kimi-k2.7-code", "kimi-k2.6")
EFFORT_VALUES = ("none", "low", "medium", "high", "xhigh", "max")

CONFIG_OPTIONS = [
    {
        "id": "autonomy_level", "name": "Autonomy Level", "category": "mode",
        "type": "select", "currentValue": "auto-high",
        "options": [{"value": value, "name": value} for value in AUTONOMY_VALUES],
    },
    {
        "id": "model", "name": "Model", "category": "model",
        "type": "select", "currentValue": "gpt-5.6-sol",
        "options": [{"value": value, "name": value} for value in MODEL_VALUES],
    },
    {
        "id": "reasoning_effort", "name": "Reasoning Effort", "category": "thought_level",
        "type": "select", "currentValue": "high",
        "options": [{"value": value, "name": value} for value in EFFORT_VALUES],
    },
]

OPTION_VALUES = {
    option["id"]: {entry["value"] for entry in option["options"]}
    for option in CONFIG_OPTIONS
}


def log_event(event: dict[str, Any]) -> None:
    if not LOG_PATH:
        return
    with LOG_LOCK:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def send(message: dict[str, Any]) -> None:
    data = json.dumps(message).encode("utf-8") + b"\n"
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


def notify(method: str, params: dict[str, Any]) -> None:
    send({"jsonrpc": "2.0", "method": method, "params": params})


def session_update(session_id: str, update: dict[str, Any]) -> None:
    notify("session/update", {"sessionId": session_id, "update": update})


def option_current(options: list[dict[str, Any]], option_id: str, value: Any) -> list[dict[str, Any]]:
    return [
        {**option, "currentValue": value} if option.get("id") == option_id else option
        for option in options
    ]


class FakeDroidAgent:
    def __init__(self, caps: set[str]):
        self.caps = caps
        self.next_session = 1
        self.known: dict[str, bool] = {}
        self.current: dict[str, str] = {
            "autonomy_level": "auto-high",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
        }
        self.active_turn: tuple[Any, str] | None = None
        self.lock = threading.Lock()
        log_event({"event": "fake_start", "caps": sorted(caps)})

    def _cap(self, name: str) -> Any:
        return {} if name in self.caps else False

    def capabilities(self) -> dict[str, Any]:
        # droid natively supports session load/resume regardless of the
        # sessionCapabilities list fixtures the runner needs.
        return {
            "loadSession": True,
            "sessionCapabilities": {
                "list": self._cap("list"),
                "resume": self._cap("resume"),
                "close": self._cap("close"),
            },
            "promptCapabilities": {"image": True, "embeddedContext": True},
            "_meta": {"terminal_output": True, "terminal-auth": True},
        }

    def selection_result(self) -> dict[str, Any]:
        return {
            "models": {
                "currentModelId": self.current["model"],
                "availableModels": [{"id": value, "name": value} for value in MODEL_VALUES],
            },
            "modes": {
                "currentModeId": self.current["autonomy_level"],
                "availableModes": [{"id": value, "name": value} for value in AUTONOMY_VALUES],
            },
            "configOptions": CONFIG_OPTIONS,
        }

    def on_initialize(self, request_id: Any, params: dict[str, Any]) -> None:
        log_event({"event": "initialize", "params": params})
        respond(
            request_id,
            {
                "protocolVersion": 1,
                "agentCapabilities": self.capabilities(),
                "agentInfo": {"name": "@factory/cli", "title": "Factory Droid", "version": "0.220.0"},
                "authMethods": [
                    {"id": "device-pairing", "name": "Login"},
                    {"id": "factory-api-key", "name": "Factory API Key"},
                ],
            },
        )

    def on_session_new(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = f"droid-session-{self.next_session}"
        self.next_session += 1
        self.known[session_id] = True
        log_event({"event": "session_new", "sessionId": session_id})
        respond(request_id, {"sessionId": session_id, **self.selection_result()})

    def on_session_resume(self, request_id: Any, params: dict[str, Any]) -> None:
        if "resume" not in self.caps and "load" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/resume unsupported"})
            return
        session_id = params.get("sessionId", "")
        self.known[session_id] = True
        log_event({"event": "session_resume", "sessionId": session_id})
        # Per probe P4: resume/load return the saved selection and do NOT echo
        # the sessionId; the holder preserves the session/new result id.
        respond(request_id, self.selection_result())

    def on_session_list(self, request_id: Any, params: dict[str, Any]) -> None:
        if "list" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/list unsupported"})
            return
        log_event({"event": "session_list", "params": params})
        respond(
            request_id,
            {
                "sessions": [
                    {"sessionId": session_id, "cwd": params.get("cwd", ""), "title": "Fixture"}
                    for session_id in self.known
                ]
            },
        )

    def on_set_config(self, request_id: Any, params: dict[str, Any]) -> None:
        option_id = params.get("configId")
        value = params.get("value")
        log_event({"event": "set_config_option", "configId": option_id, "value": value,
                   "sessionId": params.get("sessionId")})
        if option_id not in OPTION_VALUES:
            respond(
                request_id,
                error={
                    "code": -32602,
                    "message": f"Invalid params: Unknown config option: {option_id}",
                    "data": {"configId": option_id},
                },
            )
            return
        if value not in OPTION_VALUES[option_id]:
            respond(
                request_id,
                error={
                    "code": -32602,
                    "message": f"Invalid params: Invalid {option_id} value: {value}",
                    "data": {"configId": option_id, "value": value},
                },
            )
            return
        self.current[option_id] = value
        # Probe P2: an accepted change echoes a config_option_update.
        session_update(
            params.get("sessionId", ""),
            {"sessionUpdate": "config_option_update",
             "configOptions": option_current(CONFIG_OPTIONS, option_id, value)},
        )
        respond(request_id, {})

    def on_prompt(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = params.get("sessionId", "")
        text = " ".join(
            part.get("text", "") for part in params.get("prompt", []) if isinstance(part, dict)
        )
        log_event({"event": "prompt", "sessionId": session_id, "text": text})
        with self.lock:
            self.active_turn = (request_id, session_id)
        session_update(
            session_id,
            {"sessionUpdate": "current_mode_update", "currentModeId": self.current["autonomy_level"]},
        )
        session_update(
            session_id,
            {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "pong"}},
        )
        respond(request_id, {"stopReason": "end_turn"})

    def on_close(self, request_id: Any, params: dict[str, Any]) -> None:
        if "close" not in self.caps:
            respond(request_id, error={"code": -32601, "message": "session/close unsupported"})
            return
        self.known.pop(params.get("sessionId", ""), None)
        respond(request_id, {})

    def dispatch(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message.get("id")
        if not method:
            log_event({"event": "response", "id": request_id, "message": message})
            return
        if "id" not in message:
            if method == "session/cancel":
                with self.lock:
                    self.active_turn = None
                log_event({"event": "session_cancel", "params": params})
            elif method == "$/cancel_request":
                log_event({"event": "cancel_request", "params": params})
            else:
                log_event({"event": "notification", "method": method, "params": params})
            return
        if method == "initialize":
            self.on_initialize(request_id, params)
        elif method == "session/new":
            self.on_session_new(request_id, params)
        elif method in ("session/resume", "session/load"):
            self.on_session_resume(request_id, params)
        elif method == "session/list":
            self.on_session_list(request_id, params)
        elif method in ("session/set_config_option", "session/set_mode"):
            self.on_set_config(request_id, params)
        elif method == "session/prompt":
            self.on_prompt(request_id, params)
        elif method == "session/close":
            self.on_close(request_id, params)
        else:
            respond(request_id, error={"code": -32601, "message": f"unsupported: {method}"})

    def serve(self) -> int:
        buffer = bytearray()
        while True:
            chunk = sys.stdin.buffer.read(1)
            if not chunk:
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
                    log_event({"event": "unparseable_inbound"})
                    continue
                self.dispatch(message)
        log_event({"event": "fake_exit"})
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--caps", default="")
    args, _unknown = parser.parse_known_args()
    caps = {item for item in args.caps.split(",") if item}
    agent = FakeDroidAgent(caps)
    return agent.serve()


if __name__ == "__main__":
    raise SystemExit(main())
