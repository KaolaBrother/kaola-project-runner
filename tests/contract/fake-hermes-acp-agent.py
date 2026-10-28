#!/usr/bin/env python3
"""Scriptable fake Hermes Agent ACP server for the Issue #416 contract suite.

Models the source-read Hermes ``hermes acp`` surface the adapter adapts:

* ``initialize`` advertises ``sessionCapabilities`` including ``resume`` and
  ``authMethods`` carrying only the terminal ``hermes-setup`` method; the
  ``session/new``/``session/load``/``session/fork`` results carry the older
  ``models``/``modes`` blocks and **no** ``configOptions``.
* ``session/set_config_option`` is a silent accept: it answers
  ``{"configOptions": []}`` for any configId.
* ``session/set_model`` answers -32602 for an unservable model and -32603
  while a turn is busy; ``session/set_mode`` accepts the mode ids.
* a second ``session/prompt`` while a turn is busy emits a "Queued for the
  next turn" chunk and returns ``end_turn`` at once.
* ``session/resume`` of an unknown id silently creates a new session (no
  ``sessionId`` in the result); ``session/load`` of an unknown id returns a
  null result.
* ``FAKE_HERMES_SCENARIO=uncredentialed``: ``session/new`` errors and
  ``authenticate`` returns a null result.
* a prompt whose text is ``hold <seconds>`` keeps the turn busy for that
  long (handled on a thread so stdin keeps flowing), then ends it.

``FAKE_HERMES_LOG`` names a JSONL path recording the spawn argv, whether
``HERMES_YOLO_MODE``/``HERMES_ACCEPT_HOOKS`` reached the child environment,
and every received method.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from typing import Any

LOG_PATH = os.environ.get("FAKE_HERMES_LOG", "")
SCENARIO = os.environ.get("FAKE_HERMES_SCENARIO", "ok")
LOG_LOCK = threading.Lock()
STDOUT_LOCK = threading.Lock()

MODEL_VALUES = ("deepseek:deepseek-flash", "deepseek:deepseek-pro")
MODE_VALUES = ("ask", "accept_edits", "dont_ask")


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


def session_update(session_id: str, update: dict[str, Any]) -> None:
    send({"jsonrpc": "2.0", "method": "session/update",
          "params": {"sessionId": session_id, "update": update}})


class FakeHermesAgent:
    def __init__(self) -> None:
        self.next_session = 1
        self.sessions: dict[str, dict[str, str]] = {}
        self.busy: set[str] = set()
        self.lock = threading.Lock()

    def state_result(self, session: dict[str, str]) -> dict[str, Any]:
        return {
            "models": {
                "currentModelId": session["model"],
                "availableModels": [
                    {"modelId": value, "name": f"Hermes model {value}"}
                    for value in MODEL_VALUES
                ],
            },
            "modes": {
                "currentModeId": session["mode"],
                "availableModes": [
                    {"id": value, "name": f"Hermes mode {value}"}
                    for value in MODE_VALUES
                ],
            },
        }

    def new_session(self) -> str:
        session_id = f"hermes-session-{self.next_session}"
        self.next_session += 1
        self.sessions[session_id] = {"model": "deepseek:deepseek-flash", "mode": "ask"}
        return session_id

    def on_initialize(self, request_id: Any, params: dict[str, Any]) -> None:
        respond(request_id, {
            "protocolVersion": 1,
            "agentCapabilities": {
                "loadSession": True,
                "sessionCapabilities": {
                    "resume": {},
                    "load": {},
                    "fork": {},
                    "list": {},
                },
                "promptCapabilities": {"image": True},
            },
            "agentInfo": {"name": "hermes-agent", "version": "0.0.0-fake"},
            "authMethods": [
                {"id": "hermes-setup", "name": "Provider setup",
                 "type": "terminal", "args": ["--setup"]},
            ],
        })

    def on_session_new(self, request_id: Any, params: dict[str, Any]) -> None:
        if SCENARIO == "uncredentialed":
            respond(request_id, error={
                "code": -32603,
                "message": "no resolved provider credential",
                "data": {"provider": "deepseek"},
            })
            return
        session_id = self.new_session()
        respond(request_id, {"sessionId": session_id,
                             **self.state_result(self.sessions[session_id])})

    def on_session_load(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = params.get("sessionId", "")
        session = self.sessions.get(session_id)
        if session is None:
            respond(request_id, None)
            return
        respond(request_id, {"sessionId": session_id, **self.state_result(session)})

    def on_session_resume(self, request_id: Any, params: dict[str, Any]) -> None:
        # Hermes semantics: an unknown resume target silently creates a fresh
        # session and the result carries no sessionId.
        session_id = params.get("sessionId", "")
        if session_id in self.sessions:
            respond(request_id, {"sessionId": session_id,
                                 **self.state_result(self.sessions[session_id])})
            return
        self.new_session()
        respond(request_id, self.state_result({"model": "deepseek:deepseek-flash",
                                               "mode": "ask"}))

    def on_session_fork(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = self.new_session()
        respond(request_id, {"sessionId": session_id,
                             **self.state_result(self.sessions[session_id])})

    def on_set_config_option(self, request_id: Any, params: dict[str, Any]) -> None:
        # The silent accept the adapter exists to prevent: any configId is
        # acknowledged with an empty list and no effect.
        respond(request_id, {"configOptions": []})

    def on_set_model(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = params.get("sessionId", "")
        model = params.get("modelId")
        with self.lock:
            if session_id in self.busy:
                respond(request_id, error={
                    "code": -32603,
                    "message": "Internal error: agent busy",
                    "data": {"sessionId": session_id},
                })
                return
        session = self.sessions.get(session_id)
        if session is None or model not in MODEL_VALUES:
            respond(request_id, error={
                "code": -32602,
                "message": f"Invalid params: model not found: {model}",
                "data": {"modelId": model},
            })
            return
        session["model"] = model
        respond(request_id, {})

    def on_set_mode(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = params.get("sessionId", "")
        mode = params.get("modeId")
        session = self.sessions.get(session_id)
        if session is None or mode not in MODE_VALUES:
            respond(request_id, error={
                "code": -32602,
                "message": f"Invalid params: mode not found: {mode}",
                "data": {"modeId": mode},
            })
            return
        session["mode"] = mode
        respond(request_id, {})
        session_update(session_id, {"sessionUpdate": "current_mode_update",
                                    "currentModeId": mode})

    def on_prompt(self, request_id: Any, params: dict[str, Any]) -> None:
        session_id = params.get("sessionId", "")
        text = " ".join(
            part.get("text", "") for part in params.get("prompt", [])
            if isinstance(part, dict))
        with self.lock:
            if session_id in self.busy:
                # Queued or redirected: the second prompt ends at once.
                session_update(session_id, {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "Queued for the next turn"}})
                respond(request_id, {"stopReason": "end_turn"})
                return
        if text.startswith("hold"):
            seconds = float(text.split()[1]) if len(text.split()) > 1 else 1.0
            with self.lock:
                self.busy.add(session_id)

            def finish() -> None:
                time.sleep(seconds)
                session_update(session_id, {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "held turn done"}})
                respond(request_id, {"stopReason": "end_turn"})
                with self.lock:
                    self.busy.discard(session_id)

            threading.Thread(target=finish, daemon=True).start()
            return
        session_update(session_id, {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": f"echo: {text}"}})
        respond(request_id, {"stopReason": "end_turn"})

    def dispatch(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message.get("id")
        if not method:
            return
        log_event({"event": "request", "method": method, "params": params})
        if "id" not in message:
            if method == "session/cancel":
                with self.lock:
                    self.busy.clear()
            return
        if method == "initialize":
            self.on_initialize(request_id, params)
        elif method == "session/new":
            self.on_session_new(request_id, params)
        elif method == "session/load":
            self.on_session_load(request_id, params)
        elif method == "session/resume":
            self.on_session_resume(request_id, params)
        elif method == "session/fork":
            self.on_session_fork(request_id, params)
        elif method == "session/set_config_option":
            self.on_set_config_option(request_id, params)
        elif method == "session/set_model":
            self.on_set_model(request_id, params)
        elif method == "session/set_mode":
            self.on_set_mode(request_id, params)
        elif method == "session/prompt":
            self.on_prompt(request_id, params)
        elif method == "authenticate":
            respond(request_id, None)
        else:
            respond(request_id, error={"code": -32601, "message": f"unsupported: {method}"})

    def serve(self) -> int:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                log_event({"event": "unparseable_inbound"})
                continue
            self.dispatch(message)
        log_event({"event": "fake_exit"})
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_known_args()
    log_event({
        "event": "spawn", "argv": sys.argv,
        "env_yolo_mode": "HERMES_YOLO_MODE" in os.environ,
        "env_accept_hooks": "HERMES_ACCEPT_HOOKS" in os.environ,
        "env_hermes_home": os.environ.get("HERMES_HOME", ""),
    })
    return FakeHermesAgent().serve()


if __name__ == "__main__":
    raise SystemExit(main())
