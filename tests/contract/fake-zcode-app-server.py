#!/usr/bin/env python3
"""Hermetic fake ZCode `app-server --stdio` for the Issue #51 contract suite.

Speaks the private ZCode Protocol (newline-delimited JSON-RPC) exactly as
documented in william0wang/zcode-acp `docs/PROTOCOL.md` @ 80aa4e2c399, so the
Runner-owned adapter can be accepted offline with no ZCode install, no login,
no account and no network.

It also records its own argv and environment to ``FAKE_ZCODE_RECORD`` so the
suite can assert that the adapter forwarded no credential environment, plus
the provider/model/credential it received in the ``runtimeModel`` overlay so
the suite can prove in-memory bridging without the value ever reaching ACP.

CLI 0.16.5 parity: ``session/create`` and ``session/resume`` without a
``runtimeModel`` overlay fail with ``Model config is missing`` (the backend
would otherwise read ``~/.zcode/cli/config.json``); the overlay is validated
against the backend's strict zod shapes (`$f` / `Nje` / `mEt`).

Scenarios (argv ``--scenario``):
  basic        text + reasoning stream, one tool call, usage, turn.completed
  tool_error   a failing tool, then turn.completed
  permission   backend asks interaction/requestPermission before finishing
  plan         backend asks interaction/requestUserInput (plan_approval)
  question     backend asks interaction/requestUserInput (AskUserQuestion)
  failure      turn.failed with an error payload
  slow         waits for session/stop, then reports a terminal turn (cancel)
  batch        a tool.updated batch payload
  strict_model kept for compatibility; every scenario now rejects a model
               that the registered overlay did not list (no silent fallback)
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


MODEL_CONFIG_MISSING = (
    "ModelProtocolError: Model config is missing. Create ~/.zcode/cli/config.json "
    "with an explicit model provider before running ZCode."
)
PROVIDER_KEYS = {
    "providerId", "kind", "apiFormat", "label", "source", "baseURL", "apiKey",
    "apiKeyRequired", "headers", "providerOptions", "logoUrl", "modelsDevProviderId", "models",
}
MODEL_ELEMENT_KEYS = {
    "modelId", "label", "description", "contextWindow", "maxOutputTokens", "reasoning",
    "reasoningProfile", "supportsImages", "supportsPdf", "supportsVideo", "supportsTools",
    "supportsStructuredOutput", "providerOptions",
}


def validate_runtime_model(overlay: Any) -> str | None:
    """Mirror the backend's strict schemas; return an error message or None."""
    if not isinstance(overlay, dict):
        return "runtimeModel must be an object"
    extra = set(overlay) - {"revision", "generatedAt", "model", "provider", "thoughtLevel"}
    if extra:
        return f"runtimeModel unrecognized keys: {sorted(extra)}"
    if not isinstance(overlay.get("revision"), str) or not overlay["revision"]:
        return "runtimeModel.revision must be a non-empty string"
    if not isinstance(overlay.get("generatedAt"), int):
        return "runtimeModel.generatedAt must be an integer timestamp"
    model = overlay.get("model")
    if not isinstance(model, dict) or set(model) - {"providerId", "modelId", "variant"}:
        return "runtimeModel.model must be {providerId, modelId[, variant]}"
    if not model.get("providerId") or not model.get("modelId"):
        return "runtimeModel.model needs providerId and modelId"
    provider = overlay.get("provider")
    if not isinstance(provider, dict):
        return "runtimeModel.provider must be an object"
    extra = set(provider) - PROVIDER_KEYS
    if extra:
        return f"runtimeModel.provider unrecognized keys: {sorted(extra)}"
    if provider.get("providerId") != model["providerId"]:
        return "runtimeModel.provider.providerId must match runtimeModel.model.providerId"
    if provider.get("kind") not in ("anthropic", "openai", "openai-compatible"):
        return "runtimeModel.provider.kind invalid"
    if "apiFormat" in provider and provider["apiFormat"] not in (
        "anthropic-messages", "openai-chat-completions", "openai-responses"
    ):
        return "runtimeModel.provider.apiFormat invalid"
    if "source" in provider and provider["source"] not in (
        "builtin", "models-dev", "custom", "user", "workspace", "ephemeral"
    ):
        return "runtimeModel.provider.source invalid"
    api_key = provider.get("apiKey")
    if api_key is not None:
        if not isinstance(api_key, dict) or api_key.get("source") not in (
            "credential", "env", "server-config", "inline"
        ):
            return "runtimeModel.provider.apiKey must be a discriminated union"
        if api_key["source"] == "inline" and (set(api_key) != {"source", "value"} or not api_key["value"]):
            return "runtimeModel.provider.apiKey inline needs exactly {source, value}"
    models = provider.get("models")
    if not isinstance(models, list) or not models:
        return "runtimeModel.provider.models must be a non-empty array"
    for element in models:
        if not isinstance(element, dict) or not element.get("modelId"):
            return "runtimeModel.provider.models[] needs modelId"
        extra = set(element) - MODEL_ELEMENT_KEYS
        if extra:
            return f"runtimeModel.provider.models[] unrecognized keys: {sorted(extra)}"
        reasoning = element.get("reasoning")
        if reasoning is not None:
            if not isinstance(reasoning, dict) or not isinstance(reasoning.get("enabled"), bool):
                return "runtimeModel reasoning needs enabled"
            levels = reasoning.get("levels")
            if not isinstance(levels, list) or any(
                not isinstance(level, dict) or set(level) - {"value", "label", "description"}
                or not level.get("value") or not level.get("label")
                for level in levels
            ):
                return "runtimeModel reasoning.levels must be [{value, label}]"
    if not any(element["modelId"] == model["modelId"] for element in models):
        return "runtimeModel.model.modelId is not in runtimeModel.provider.models"
    return None


def record_overlay(overlay: dict[str, Any], method: str) -> None:
    """Append what the overlay carried (test evidence; secret stays in tmp)."""
    path = os.environ.get("FAKE_ZCODE_RECORD")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        payload = {}
    api_key = (overlay.get("provider") or {}).get("apiKey") or {}
    payload.setdefault("overlays", []).append({
        "method": method,
        "providerId": overlay["provider"]["providerId"],
        "modelId": overlay["model"]["modelId"],
        "baseURL": overlay["provider"].get("baseURL"),
        "apiKeySource": api_key.get("source"),
        "apiKeyValue": api_key.get("value"),
        "modelIds": [m["modelId"] for m in overlay["provider"]["models"]],
        "revision": overlay["revision"],
    })
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


class FakeAppServer:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.seq = 0
        self.sessions: dict[str, dict[str, Any]] = {}
        self.counter = 0
        self.next_request_id = 1000
        self.stop_flags: dict[str, threading.Event] = {}
        # Workspace catalog registered through overlays (backend `q8` parity).
        self.catalog: dict[str, list[str]] = {}

    def register_overlay(self, rid: Any, params: dict[str, Any], method: str) -> dict[str, Any] | None:
        overlay = params.get("runtimeModel")
        if overlay is None:
            if not self.catalog:
                self.error(rid, -32000, MODEL_CONFIG_MISSING)
                return None
            return {}
        problem = validate_runtime_model(overlay)
        if problem:
            self.error(rid, -32602, f"invalid params: {problem}")
            return None
        provider = overlay["provider"]
        self.catalog[provider["providerId"]] = [m["modelId"] for m in provider["models"]]
        record_overlay(overlay, method)
        return overlay

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
            overlay = self.register_overlay(rid, params, method)
            if overlay is None:
                return
            self.counter += 1
            session_id = f"sess_fake{self.counter}"
            model = overlay.get("model") or {}
            self.sessions[session_id] = {
                "mode": params.get("mode") or "yolo",
                "modelId": model.get("modelId") or "fake-model",
                "providerId": model.get("providerId") or "builtin:fake-coding-plan",
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
                {"sessionId": sid, "title": f"fake session {sid}",
                 "createdAt": 1789552001462 + index, "updatedAt": 1789552106400 + index,
                 "status": "idle", "mode": session.get("mode") or "yolo"}
                for index, (sid, session) in enumerate(self.sessions.items())
            ]})
            return

        if method == "session/resume":
            # CLI 0.16.5 parity: a faithful resume (no overlay) succeeds even in
            # a fresh app-server; the persisted model is simply unavailable
            # until a provider overlay registers it (see session/send).
            overlay = {}
            if params.get("runtimeModel") is not None:
                overlay = self.register_overlay(rid, params, method)
                if overlay is None:
                    return
            session_id = params.get("sessionId")
            model = overlay.get("model") or {}
            self.sessions.setdefault(session_id, {
                "mode": "yolo",
                "modelId": model.get("modelId") or "GLM-5.3-Flash",
                "providerId": model.get("providerId") or "builtin:bigmodel-coding-plan",
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
            if (params.get("model") or {}).get("apiKey"):
                self.error(rid, -32602, "invalid params: model.apiKey unrecognized key")
                return
            if params.get("runtimeModel") is not None:
                if self.register_overlay(rid, params, method) is None:
                    return
            model = params.get("model") or {}
            model_id = model.get("modelId") or params.get("modelId")
            if not model_id:
                self.error(rid, -32602, "setModel requires modelId")
                return
            known = self.catalog.get(model.get("providerId") or "", [])
            if model_id not in known:
                self.error(rid, 1402, f"unknown model {model_id} for provider {model.get('providerId')}")
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
            session = self.sessions[session_id]
            if session.get("modelId") not in self.catalog.get(session.get("providerId") or "", []):
                self.error(rid, -32031, "ZCODE_RUNTIME_MODEL_UNAVAILABLE: the persisted model is "
                                        "not registered in this app-server (register a provider)")
                return
            self.result(rid, {"accepted": True})
            threading.Thread(target=self.run_turn, args=(session_id,), daemon=True).start()
            return

        if method == "session/stop":
            session_id = params.get("sessionId")
            flag = self.stop_flags.get(session_id)
            if flag is not None:
                flag.set()
            if rid is not None:
                self.result(rid, {"stopped": True})
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
