#!/usr/bin/env python3
"""Hermetic fake ZCode `app-server --stdio` for the Issue #51 contract suite.

Speaks the private ZCode Protocol (newline-delimited JSON-RPC) exactly as
documented in william0wang/zcode-acp `docs/PROTOCOL.md` @ 80aa4e2c399, so the
Runner-owned adapter can be accepted offline with no ZCode install, no login,
no account and no network.

It also records its own argv and environment to ``FAKE_ZCODE_RECORD`` so the
suite can assert that the adapter forwarded no credential environment.

Scenarios (argv ``--scenario``):
  basic        text + reasoning stream, one tool call, usage, turn.completed
  tool_error   a failing tool, then turn.completed
  permission   backend asks interaction/requestPermission before finishing
  plan         backend asks interaction/requestUserInput (plan_approval)
  question     backend asks interaction/requestUserInput (AskUserQuestion)
  failure      turn.failed with an error payload
  slow         waits for session/stop, then reports a terminal turn (cancel)
  batch        a tool.updated batch payload
  strict_model session/setModel rejects unknown model ids (no silent fallback)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from typing import Any

WRITE_LOCK = threading.Lock()


def emit(msg: dict[str, Any]) -> None:
    data = json.dumps(msg).encode("utf-8") + b"\n"
    with WRITE_LOCK:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def record_startup(scenario: str) -> None:
    path = os.environ.get("FAKE_ZCODE_RECORD")
    if not path:
        return
    payload = {
        "argv": sys.argv[1:],
        "env_names": sorted(os.environ),
        "cwd": os.getcwd(),
        "scenario": scenario,
        "pid": os.getpid(),
        "pgid": os.getpgrp(),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def log_rpc(direction: str, msg: dict[str, Any]) -> None:
    path = os.environ.get("FAKE_ZCODE_RPC_LOG")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"direction": direction, "msg": msg}, sort_keys=True) + "\n")


class FakeAppServer:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.seq = 0
        self.sessions: dict[str, dict[str, Any]] = {}
        self.counter = 0
        self.next_request_id = 1000
        self.stop_flags: dict[str, threading.Event] = {}

    # -- helpers ----------------------------------------------------------

    def event(self, session_id: str, etype: str, payload: dict[str, Any]) -> None:
        self.seq += 1
        emit({
            "method": "session/event",
            "params": {
                "sessionId": session_id,
                "seq": self.seq,
                "type": etype,
                "payload": payload,
            },
        })

    def result(self, rid: Any, result: Any) -> None:
        emit({"id": rid, "result": result})

    def error(self, rid: Any, code: int, message: str) -> None:
        emit({"id": rid, "error": {"code": code, "message": message}})

    # -- request handling -------------------------------------------------

    def handle(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        rid = msg.get("id")
        params = msg.get("params") or {}

        if method == "session/create":
            self.counter += 1
            session_id = f"sess_fake{self.counter}"
            self.sessions[session_id] = {
                "mode": params.get("mode") or "yolo",
                "modelId": "fake-model",
                "providerId": "builtin:zai-coding-plan",
                "thoughtLevel": "high",
                "subscribed": False,
            }
            # CLI 0.16.5 asks the client for runtime preferences during create.
            pref_id = self.next_request_id
            self.next_request_id += 1
            emit({
                "id": pref_id,
                "method": "session/requestRuntimePreferences",
                "params": {"sessionId": session_id, "scope": "runtime-materialization"},
            })
            self.result(rid, {"session": {
                "sessionId": session_id, "title": "", "traceId": f"trace_{self.counter}",
            }})
            return

        if method == "session/subscribe":
            session_id = params.get("sessionId")
            if session_id in self.sessions:
                self.sessions[session_id]["subscribed"] = True
            self.result(rid, {"eventSeq": self.seq, "snapshot": None})
            return

        if method == "session/list":
            self.result(rid, {"sessions": [
                {"sessionId": sid, "title": f"fake session {sid}"} for sid in self.sessions
            ]})
            return

        if method == "session/resume":
            session_id = params.get("sessionId")
            self.sessions.setdefault(session_id, {
                "mode": "yolo",
                "modelId": "fake-model",
                "providerId": "builtin:zai-coding-plan",
                "thoughtLevel": "high",
                "subscribed": False,
            })
            self.result(rid, {"session": {"sessionId": session_id, "title": "resumed"}})
            return

        if method == "session/read":
            session_id = params.get("sessionId")
            session = self.sessions.get(session_id)
            if session is None:
                self.error(rid, 1404, "session not found")
                return
            self.result(rid, {
                "projection": {"status": "idle"},
                "settings": {
                    "mode": {"current": session.get("mode") or "yolo"},
                    "model": {"current": {
                        "modelId": session.get("modelId") or "fake-model",
                        "providerId": session.get("providerId") or "builtin:zai-coding-plan",
                    }},
                    "thoughtLevel": {"current": session.get("thoughtLevel") or "high"},
                },
            })
            return

        if method == "session/setModel":
            session_id = params.get("sessionId")
            session = self.sessions.get(session_id)
            if session is None:
                self.error(rid, 1404, "session not found")
                return
            if params.get("runtimeModel") or (params.get("model") or {}).get("apiKey"):
                self.error(rid, 1401, "runtime overlay / apiKey is not accepted")
                return
            model = params.get("model") or {}
            model_id = model.get("modelId") or params.get("modelId")
            if self.scenario == "strict_model" and model_id not in ("fake-model", "other-model"):
                self.error(rid, 1402, f"unknown model {model_id}")
                return
            if not model_id:
                self.error(rid, -32602, "setModel requires modelId")
                return
            session["modelId"] = model_id
            if model.get("providerId"):
                session["providerId"] = model.get("providerId")
            self.result(rid, {"ok": True})
            return

        if method == "session/setThoughtLevel":
            session_id = params.get("sessionId")
            session = self.sessions.get(session_id)
            if session is None:
                self.error(rid, 1404, "session not found")
                return
            session["thoughtLevel"] = params.get("thoughtLevel")
            self.result(rid, {"ok": True})
            return

        if method == "session/send":
            session_id = params.get("sessionId")
            if session_id not in self.sessions:
                self.error(rid, 1404, "session not found")
                return
            self.result(rid, {"accepted": True})
            threading.Thread(target=self.run_turn, args=(session_id,), daemon=True).start()
            return

        if method == "session/stop":
            session_id = params.get("sessionId")
            flag = self.stop_flags.get(session_id)
            if flag is not None:
                flag.set()
            return

        if method == "session/setMode":
            session_id = params.get("sessionId")
            if session_id in self.sessions:
                self.sessions[session_id]["mode"] = params.get("mode")
            self.result(rid, {"ok": True})
            return

        if method == "session/close":
            self.sessions.pop(params.get("sessionId"), None)
            self.result(rid, {"ok": True})
            return

        if rid is not None:
            self.error(rid, -32601, f"method not found: {method}")

    # -- the scripted turn -------------------------------------------------

    def run_turn(self, session_id: str) -> None:
        scenario = self.scenario
        self.event(session_id, "turn.started", {})

        if scenario == "failure":
            self.event(session_id, "turn.failed",
                       {"error": {"code": 1308, "message": "prompt is running"}})
            return

        if scenario == "slow":
            flag = threading.Event()
            self.stop_flags[session_id] = flag
            self.event(session_id, "model.streaming",
                       {"kind": "text_delta", "delta": "working"})
            flag.wait(10)
            self.event(session_id, "turn.terminal", {"reason": "stopped"})
            return

        if scenario == "permission":
            rid = self.next_request_id
            self.next_request_id += 1
            emit({"id": rid, "method": "interaction/requestPermission", "params": {
                "requestId": "req_1", "sessionId": session_id,
                "toolCallId": "call_perm", "toolName": "Bash",
                "reason": "run command", "input": {"command": "ls -la"},
                "options": [
                    {"optionId": "allow", "kind": "allow_once", "name": "Allow once"},
                    {"optionId": "deny", "kind": "deny_once", "name": "Deny"},
                ],
            }})
            return

        if scenario == "plan":
            rid = self.next_request_id
            self.next_request_id += 1
            emit({"id": rid, "method": "interaction/requestUserInput", "params": {
                "requestId": "req_2", "sessionId": session_id, "toolCallId": "call_plan",
                "schema": {"interaction": "plan_approval"},
                "input": {"plan": "1. Implement login\n2. Implement signup"},
            }})
            return

        if scenario == "question":
            rid = self.next_request_id
            self.next_request_id += 1
            emit({"id": rid, "method": "interaction/requestUserInput", "params": {
                "requestId": "req_3", "sessionId": session_id, "toolCallId": "call_q",
                "questions": [{
                    "question": "Select the files to test", "multiSelect": True,
                    "options": [
                        {"label": "auth.test.ts", "value": "auth"},
                        {"label": "user.test.ts", "value": "user"},
                    ],
                }],
            }})
            return

        if scenario == "batch":
            self.event(session_id, "tool.updated", {"kind": "batch", "items": [
                {"kind": "result", "toolCallId": "call_b1", "toolName": "Read",
                 "output": "first"},
                {"kind": "result", "toolCallId": "call_b2", "toolName": "Grep",
                 "output": "second"},
            ]})
            self.complete(session_id)
            return

        # basic / tool_error
        self.event(session_id, "model.streaming",
                   {"kind": "reasoning_delta", "delta": "thinking about it"})
        self.event(session_id, "model.streaming",
                   {"kind": "text_delta", "delta": "hello "})
        self.event(session_id, "model.streaming",
                   {"kind": "text_delta", "delta": "from zcode"})
        self.event(session_id, "model.streaming", {
            "kind": "tool_call", "toolCallId": "call_1",
            "toolName": "Bash", "input": {"command": "echo hi"},
        })
        self.event(session_id, "tool.updated", {
            "kind": "scheduled", "toolCallId": "call_1", "toolName": "Bash",
            "input": {"command": "echo hi"},
        })
        self.event(session_id, "tool.updated", {
            "kind": "started", "toolCallId": "call_1", "toolName": "Bash",
        })
        if scenario == "tool_error":
            self.event(session_id, "tool.updated", {
                "kind": "error", "toolCallId": "call_1", "toolName": "Bash",
                "message": "command failed",
            })
        else:
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_1", "toolName": "Bash",
                "output": "hi",
            })
        self.complete(session_id)

    def complete(self, session_id: str) -> None:
        self.event(session_id, "turn.completed", {
            "resultType": "success",
            "usage": {
                "source": "provider", "modelRequestCount": 1,
                "inputTokens": 11, "outputTokens": 7, "totalTokens": 18,
                "cacheReadTokens": 0, "cacheWriteTokens": 0, "reasoningTokens": 3,
                "webFetchRequests": 0, "webSearchRequests": 0,
            },
        })

    def run(self) -> int:
        for raw in sys.stdin.buffer:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            log_rpc("in", msg)
            if "method" in msg:
                self.handle(msg)
            elif "id" in msg:
                self.on_response(msg)
        return 0

    def on_response(self, msg: dict[str, Any]) -> None:
        """The adapter answered one of our interaction requests."""
        session_id = next(iter(self.sessions), None)
        if session_id is None:
            return
        result = msg.get("result") or {}
        self.event(session_id, "model.streaming", {
            "kind": "text_delta",
            "delta": f"[interaction-result] {json.dumps(result, sort_keys=True)}",
        })
        self.complete(session_id)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="app-server")
    parser.add_argument("--stdio", action="store_true")
    parser.add_argument("--scenario", default=os.environ.get("FAKE_ZCODE_SCENARIO", "basic"))
    args, _unknown = parser.parse_known_args(argv)
    record_startup(args.scenario)
    if args.command != "app-server":
        sys.stderr.write("fake zcode: only app-server is supported\n")
        return 2
    return FakeAppServer(args.scenario).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
