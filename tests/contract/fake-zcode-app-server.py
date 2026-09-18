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
  echo_error   session/create fails and echoes the request params in error.data
  echo_events  streaming text, tool input/output and turn.failed echo the credential
  resume_missing      session/resume fails 1404 (session unknown)
  resume_needs_overlay session/resume fails without a runtimeModel overlay
  read_fails   session/read fails after a successful resume
  read_path    Read tool_call with file_path (Issue #67)
  no_input     tool.updated without cached input (Issue #67)
  sensitive_extra  Read input mixes a path with secrets and nested blobs
  huge_nested  Read input with a huge command and deep extra dict
  command_token  Bash input whose command carries an unregistered token
  steer_guide  v4 sendText admitted guide: steerQueued + steerDrained (Issue #81)
  steer_queue  v4 sendText admitted to the queue only: steerQueued, no drain
  steer_turnend steerQueued{guide} then the turn ends without a drain
  steer_xturn  steerQueued{targetTurnId:A} then steerDrained{targetTurnId:B}
  steer_phantom adversarial: queued omits pendingInputId; an UNRELATED drain
              also omits it but names our turn — must never report injected
  steer_guide_nopid guide drain correlating by sourceCommandId only — the
              pending-id-free happy path that must still report injected
  steer_noexpect adversarial: turn.started never carries turnId, then a
              queue/drain pair agrees on a successor-turn id — with the
              steered turn's identity unknown it must never report injected
  steer_mixed adversarial: guide admission, then a drain batch holding our
              input (p1->m1) AND an unrelated one (p2->m2) while
              injectedMessageIds names only m2 — must never report injected
  steer_qdrain adversarial: queue admission plus a same-turn drain whose
              injectedMessageIds includes our messageId, both staged before
              the ack — a queue-admitted input must never report injected
  steer_timeout_staged v4/command ack withheld entirely (client timeout), but
              the server had already staged a steerQueued{queue} admission
  steer_timeout_silent v4/command ack withheld and no steer events — the
              request may or may not have reached the server
  steer_exit_staged app-server process dies inside v4/command AFTER a
              steerQueued{queue} was already emitted — transport loss, never
              a business rejection
  steer_exit_silent app-server process dies inside v4/command with no events
              — the request may or may not have been processed
  steer_race_end the steer's target turn COMPLETES inside the subscribe call,
              before v4/command can be sent — no text may go out
  steer_race_replaced the target turn completes inside subscribe and a
              successor turn starts before v4/command — the adapter must not
              learn the successor's turnId nor send any text
  steer_slow_subscribe subscribe answers after ~4 s but turn.started carries
              no turnId — with a short budget the global deadline must fire
              before v4/command is sent
  steer_slow_exchange subscribe answers after ~14 s, no turnId, and the
              v4/command ack never arrives — the whole exchange must stay
              bounded by the global deadline, not stacked per-phase timeouts
  steer_silent v4 sendText accepted but no steer events at all
  steer_reject v4 sendText answered status:"rejected" with a reasonCode
  steer_unsupported no v4 methods at all (pre-0.16 build parity): -32601
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
        self.last_secret: str | None = None
        # Issue #81: v4 steering legs. `v4_seen` releases the scripted turn once
        # any v4 call landed (or failed); `turn_gate` releases it after the leg's
        # events were emitted so `turn.completed` keeps causal order.
        self.v4_seen = threading.Event()
        self.turn_gate = threading.Event()
        self.active_turn_id: str | None = None
        # Distinct platform turn ids per prompt so a successor turn can never
        # be confused with the one the steer targeted.
        self.turn_seq = 0
        # Turn ids already completed out-of-band (the steer target-change legs
        # end the running turn inside the subscribe call) — run_turn must not
        # emit a second completion for them.
        self.early_completed_turns: set[str] = set()

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
        api_key = provider.get("apiKey") or {}
        if api_key.get("source") == "inline":
            self.last_secret = api_key.get("value")
        record_overlay(overlay, method)
        return overlay

    # -- helpers ----------------------------------------------------------

    def event(self, session_id: str, etype: str, payload: dict[str, Any],
              params_extra: dict[str, Any] | None = None) -> None:
        self.seq += 1
        params: dict[str, Any] = {
            "sessionId": session_id,
            "seq": self.seq,
            "type": etype,
            "payload": payload,
        }
        if params_extra:
            params.update(params_extra)
        emit({"method": "session/event", "params": params})

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
            if self.scenario == "echo_error":
                # A backend that echoes the offending request in its error.
                emit({"id": rid, "error": {"code": -32602, "message": "invalid params",
                                           "data": {"received": params}}})
                return
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
            if self.scenario == "resume_missing":
                self.error(rid, 1404, f"session not found: {params.get('sessionId')}")
                return
            if self.scenario == "resume_needs_overlay" and params.get("runtimeModel") is None:
                self.error(rid, -32000, MODEL_CONFIG_MISSING)
                return
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
            if self.scenario == "read_fails":
                self.error(rid, -32000, "session/read failed (scenario)")
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

        if method == "v4/conversation/subscribe":
            # Issue #81: the adapter primes this inside the steer path. A pre-v4
            # build has no such method at all — the steer_unsupported leg.
            self.v4_seen.set()
            if self.scenario == "steer_unsupported":
                self.error(rid, -32601, f"method not found: {method}")
                return
            if self.scenario in ("steer_race_end", "steer_race_replaced"):
                # Adversarial target-change race: the turn the steer targeted
                # ENDS while the steer is being set up — before v4/command can
                # be sent. Emitting the completion BEFORE this subscribe ack
                # keeps causal order on the adapter's event stream (the
                # adapter sees turn A die, then gets its subscription).
                session_id = (params.get("topic") or "").rsplit("/", 1)[-1]
                if self.active_turn_id:
                    self.early_completed_turns.add(self.active_turn_id)
                self.event(session_id, "turn.completed",
                           {"response": "DONE-FAKE-TURN"})
                if self.scenario == "steer_race_replaced":
                    # ...and a queued follow-up turn starts SERVER-SIDE while
                    # the steer is still in flight (the realistic succession —
                    # a second ACP prompt could not even be dispatched while
                    # the steer holds the request loop). A buggy adapter
                    # learns B's turnId and CASes expectedTurnId=turn-B — the
                    # reviewer's exact false-injection shape.
                    self.turn_seq += 1
                    self.active_turn_id = (
                        f"turn_{session_id}_{self.turn_seq - 1}")
                    self.event(session_id, "turn.started",
                               {"queryId": f"query_{session_id}_successor"},
                               params_extra={"turnId": self.active_turn_id})
                else:
                    self.turn_gate.set()
            if self.scenario == "steer_slow_subscribe":
                # Budget adversarial: the subscribe phase eats most of a
                # short steer budget — the adapter must never send v4/command
                # after the global deadline.
                time.sleep(4.0)
            elif self.scenario == "steer_slow_exchange":
                # Budget adversarial: subscribe answers inside its own cap
                # but consumes ~14 s of the whole-operation budget; the
                # command then never answers, so the total exchange must stay
                # bounded by the global deadline, not per-phase timeouts.
                time.sleep(14.0)
            self.result(rid, {
                "ack": {"subscriptionId": "sub-v4-1", "mode": "delta",
                        "logEpoch": "log-epoch-1"},
            })
            return

        if method == "v4/command":
            self.v4_seen.set()
            if self.scenario == "steer_unsupported":
                self.error(rid, -32601, f"method not found: {method}")
                return
            self.handle_v4_command(rid, params)
            return

        if rid is not None:
            self.error(rid, -32601, f"method not found: {method}")

    # -- Issue #81: the v4 steer legs --------------------------------------

    def handle_v4_command(self, rid: Any, params: dict[str, Any]) -> None:
        """Answer `v4/command sendText` the way the 3.12.3 app-server does.

        The ack shape is verbatim from live evidence — including the trap that
        ``result.delivery`` reports ``"queue"`` even for admitted guide input.
        The injected/queued distinction lives in the session/event legs each
        scenario emits (or pointedly does not emit).
        """
        session_id = params.get("sessionId") or ""
        command_id = params.get("commandId") or "cmd-unknown"
        payload = params.get("payload") or {}
        if params.get("type") != "sendText" or session_id not in self.sessions:
            self.result(rid, {
                "commandId": command_id, "status": "rejected",
                "reasonCode": "proto.invalidPayload",
            })
            return
        text = payload.get("text") or ""
        pending_id = f"queue_{command_id}"
        turn_id = self.active_turn_id or "turn_fake"
        scenario = self.scenario

        # Issue #81: the platform enforces expectedTurnId as a per-turn CAS —
        # a stale expectation is a machine-readable rejection, not a quiet
        # admission against whoever runs now.
        expected = payload.get("expectedTurnId")
        if expected and expected != turn_id:
            self.result(rid, {
                "commandId": command_id, "status": "rejected",
                "reasonCode": "expected_turn_mismatch",
            })
            self.turn_gate.set()
            return

        if scenario == "steer_reject":
            self.result(rid, {
                "commandId": command_id, "status": "rejected",
                "reasonCode": "fault.command.inputRejected",
                "message": "turn is not steerable",
            })
            self.turn_gate.set()
            return

        # Queue-admission legs: the steerQueued reports delivery `queue` on
        # both the top-level and intent.admittedDelivery fields.
        queue_admission = scenario in (
            "steer_queue", "steer_qdrain", "steer_timeout_staged",
            "steer_exit_staged")

        def emit_leg() -> None:
            queued_payload = {
                "inputId": command_id, "queryId": command_id,
                "pendingInputId": pending_id,
                "input": text, "inputPreview": text, "inputSize": len(text),
                "targetTurnId": turn_id, "queueLength": 1,
                "delivery": "queue" if queue_admission else "guide",
                "intent": {
                    "sourceCommandId": command_id,
                    "queueItemId": pending_id,
                    "clientId": params.get("clientId"),
                    "kind": "sendText", "text": text,
                    "requestedDelivery": payload.get("requestedDelivery"),
                    "admittedDelivery": (
                        "queue" if queue_admission else "guide"),
                },
            }
            if scenario in ("steer_phantom", "steer_guide_nopid"):
                # The adversarial review leg: our admission carries no
                # pendingInputId, so the ledger has no id to match on.
                queued_payload.pop("pendingInputId", None)
            if scenario == "steer_noexpect":
                # Queue/drain agree on a SUCCESSOR-turn id — but turn.started
                # never named any turn, so the adapter cannot prove this pair
                # belongs to the turn it steered.
                queued_payload["targetTurnId"] = f"{turn_id}_later"
            if scenario in ("steer_guide", "steer_queue", "steer_turnend",
                            "steer_xturn", "steer_phantom", "steer_guide_nopid",
                            "steer_noexpect", "steer_mixed", "steer_qdrain",
                            "steer_timeout_staged", "steer_exit_staged",
                            "steer_race_replaced"):
                self.event(session_id, "turn.steerQueued", queued_payload)
            if scenario in ("steer_guide", "steer_xturn", "steer_guide_nopid",
                            "steer_noexpect", "steer_mixed", "steer_qdrain",
                            "steer_race_replaced"):
                time.sleep(0.15)
                # steer_xturn drains into a DIFFERENT turn id — a same-turn
                # claim off this pair would be a lie, so the adapter must not
                # report injected.
                drained_turn = turn_id
                if scenario == "steer_xturn":
                    drained_turn = f"{turn_id}_other"
                elif scenario == "steer_noexpect":
                    drained_turn = f"{turn_id}_later"
                drained_item = {
                    "messageId": "msg_fake_injected_1",
                    "text": text, "delivery": "guide",
                    "intent": queued_payload["intent"],
                }
                drained_payload = {
                    "injectedMessageIds": ["msg_fake_injected_1"],
                    "pendingInputIds": [pending_id],
                    "queryIds": [command_id],
                    "targetTurnId": drained_turn,
                    "drainedInputs": [dict(drained_item, pendingInputId=pending_id)],
                }
                if scenario == "steer_guide_nopid":
                    # Correlation only by intent.sourceCommandId: no
                    # pendingInputId field anywhere in this drain.
                    drained_payload["pendingInputIds"] = []
                    drained_payload["drainedInputs"] = [drained_item]
                elif scenario == "steer_mixed":
                    # Adversarial mixed drain: the batch contains OUR input
                    # (pendingInputId -> msg_fake_mixed_ours) AND an unrelated
                    # input (-> msg_fake_mixed_other), but only the UNRELATED
                    # messageId is in injectedMessageIds. A batch-level match
                    # must never be read as our injection.
                    drained_payload["injectedMessageIds"] = [
                        "msg_fake_mixed_other"]
                    drained_payload["pendingInputIds"] = [
                        pending_id, "queue_cmd-unrelated-2"]
                    drained_payload["drainedInputs"] = [
                        dict(drained_item, pendingInputId=pending_id,
                             messageId="msg_fake_mixed_ours"),
                        {"messageId": "msg_fake_mixed_other",
                         "pendingInputId": "queue_cmd-unrelated-2",
                         "text": "someone else's input", "delivery": "guide",
                         "intent": {"sourceCommandId": "cmd-unrelated-2"}},
                    ]
                self.event(session_id, "turn.steerDrained", drained_payload)
            if scenario == "steer_phantom":
                time.sleep(0.15)
                # Adversarial: an unrelated input drains into our turn while
                # our steer is pending. Neither side carries pendingInputId,
                # so a None==None match would claim this drain is ours —
                # the adapter must ignore it entirely.
                self.event(session_id, "turn.steerDrained", {
                    "injectedMessageIds": ["msg_fake_unrelated"],
                    "pendingInputIds": ["queue_cmd-unrelated-1"],
                    "targetTurnId": turn_id,
                    "drainedInputs": [{
                        "messageId": "msg_fake_unrelated",
                        "text": "someone else's input", "delivery": "guide",
                        "intent": {"sourceCommandId": "cmd-unrelated-1"},
                    }],
                })
            # steer_silent emits nothing: accepted ack, then only the turn end.
            self.turn_gate.set()

        if scenario in ("steer_timeout_staged", "steer_timeout_silent",
                        "steer_slow_exchange"):
            # The ack is withheld entirely: the adapter's `v4/command` call
            # must time out. `steer_timeout_staged` still emits the
            # steerQueued the server had already recorded; the request
            # demonstrably reached the server even though the client never
            # learns it from an ack. `steer_timeout_silent` emits nothing —
            # the request may or may not have arrived.
            emit_leg()
            return
        if scenario in ("steer_exit_staged", "steer_exit_silent"):
            # The app-server process DIES mid-request: the command was
            # received (the staged variant even queued the input first) but
            # the ack never leaves. The adapter must classify this as
            # transport-uncertain — never a business rejection.
            emit_leg()
            sys.stdout.flush()
            os._exit(0)
        if scenario == "steer_qdrain":
            # Stage the queue admission AND the same-turn drain before the
            # ack reaches the adapter: its ledger then holds both when the
            # wait loop starts, making the outcome deterministic (the loop
            # would otherwise break early on the `queue` admission and never
            # evaluate the drain).
            emit_leg()
        self.result(rid, {
            "commandId": command_id, "status": "accepted",
            "revisionAtDecision": 7,
            "result": {"type": "inputAccepted", "delivery": "queue",
                       "inputId": command_id},
        })
        if scenario != "steer_qdrain":
            threading.Thread(target=emit_leg, daemon=True).start()

    # -- the scripted turn -------------------------------------------------

    def run_turn(self, session_id: str) -> None:
        scenario = self.scenario
        self.turn_seq += 1
        turn_id = f"turn_{session_id}_{self.turn_seq - 1}"
        self.active_turn_id = turn_id
        # Live parity: `turn.started` carries the platform's own `turnId` at
        # params level (sibling of `type`), not inside `payload` — the adapter
        # reads it for the sendText expectedTurnId CAS.
        if scenario in ("steer_noexpect", "steer_slow_subscribe",
                        "steer_slow_exchange"):
            # Adversarial: a build whose turn.started never surfaces the
            # platform turnId. The adapter's expected-turn CAS stays unlearned,
            # so no queue/drain pair can ever be confirmed same-turn.
            self.event(session_id, "turn.started",
                       {"queryId": f"query_{session_id}"})
        else:
            self.event(session_id, "turn.started",
                       {"queryId": f"query_{session_id}"},
                       params_extra={"turnId": self.active_turn_id})

        if scenario.startswith("steer_"):
            # The turn stays alive until the steer's v4 activity resolved: the
            # first v4 call marks `v4_seen`; the leg's own events (or deliberate
            # silence) then open `turn_gate` and the turn completes.
            flag = threading.Event()
            self.stop_flags[session_id] = flag
            self.event(session_id, "model.streaming",
                       {"kind": "text_delta", "delta": "working"})
            self.v4_seen.wait(20)
            # Successor turns in the race legs must not linger the full 20 s —
            # the adapter under test has already answered by then; 6 s keeps
            # turn B alive long enough to expose a buggy expectedTurnId CAS.
            self.turn_gate.wait(6 if self.turn_seq > 1 else 20)
            if turn_id in self.early_completed_turns:
                # The steer target-change legs already completed THIS turn
                # inside the subscribe call — a second completion would be
                # a protocol violation no real server emits.
                return
            if scenario in ("steer_guide", "steer_guide_nopid"):
                response = "STEERED-FAKE-OK"
            else:
                response = "DONE-FAKE-TURN"
            self.event(session_id, "turn.completed", {"response": response})
            return

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

        if scenario == "echo_events":
            # A backend that echoes the inline credential inside event payloads.
            secret = self.last_secret or "no-secret-seen"
            self.event(session_id, "model.streaming",
                       {"kind": "text_delta", "delta": f"hello key={secret} world"})
            self.event(session_id, "model.streaming", {
                "kind": "tool_call", "toolCallId": "call_e1",
                "toolName": "Bash", "input": {"command": f"echo {secret}"},
            })
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_e1", "toolName": "Bash",
                "output": f"printed {secret}",
            })
            self.event(session_id, "turn.failed",
                       {"error": {"code": 1401, "message": f"auth rejected for {secret}"}})
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

        if scenario == "read_path":
            self.event(session_id, "model.streaming", {
                "kind": "tool_call", "toolCallId": "call_r1",
                "toolName": "Read",
                "input": {"file_path": "/tmp/kpr-issue-67-fixture/MARKER.txt"},
            })
            self.event(session_id, "tool.updated", {
                "kind": "scheduled", "toolCallId": "call_r1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "started", "toolCallId": "call_r1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_r1", "toolName": "Read",
                "output": "marker-line",
            })
            self.complete(session_id)
            return

        if scenario == "no_input":
            self.event(session_id, "tool.updated", {
                "kind": "started", "toolCallId": "call_n1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_n1", "toolName": "Read",
                "output": "opaque",
            })
            self.complete(session_id)
            return

        if scenario == "sensitive_extra":
            secret = self.last_secret or "no-secret-seen"
            nested: dict[str, Any] = {
                "blob": "PAD" * 20000,
                "secret": secret,
                "unregistered": "unregistered-secret-value-abc123xyz",
            }
            for _ in range(12):
                nested = {"child": nested, "pad": "Y" * 1000}
            self.event(session_id, "model.streaming", {
                "kind": "tool_call", "toolCallId": "call_s1",
                "toolName": "Read",
                "input": {
                    "file_path": "/tmp/kpr-issue-67-fixture/MARKER.txt",
                    "contents": secret,
                    "apiKey": secret,
                    "extra": nested,
                    "unregistered": "unregistered-secret-value-abc123xyz",
                    "command": f"echo {secret}",
                },
            })
            self.event(session_id, "tool.updated", {
                "kind": "scheduled", "toolCallId": "call_s1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "started", "toolCallId": "call_s1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_s1", "toolName": "Read",
                "output": secret,
            })
            self.complete(session_id)
            return

        if scenario == "huge_nested":
            nested = {"leaf": "Z" * 8000}
            for _ in range(16):
                nested = {"k": nested, **{f"p{i}": "Q" * 200 for i in range(24)}}
            self.event(session_id, "model.streaming", {
                "kind": "tool_call", "toolCallId": "call_h1",
                "toolName": "Read",
                "input": {
                    "file_path": "/tmp/kpr-issue-67-fixture/MARKER.txt",
                    "command": "x" * 80000,
                    "extra": nested,
                },
            })
            self.event(session_id, "tool.updated", {
                "kind": "scheduled", "toolCallId": "call_h1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "started", "toolCallId": "call_h1", "toolName": "Read",
            })
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_h1", "toolName": "Read",
                "output": "ok",
            })
            self.complete(session_id)
            return

        if scenario == "command_token":
            self.event(session_id, "model.streaming", {
                "kind": "tool_call", "toolCallId": "call_c1",
                "toolName": "Bash",
                "input": {
                    "command": "curl -H 'Authorization: Bearer unreg-i67-token-9f3a7c2e' https://example.invalid",
                },
            })
            self.event(session_id, "tool.updated", {
                "kind": "scheduled", "toolCallId": "call_c1", "toolName": "Bash",
            })
            self.event(session_id, "tool.updated", {
                "kind": "started", "toolCallId": "call_c1", "toolName": "Bash",
            })
            self.event(session_id, "tool.updated", {
                "kind": "result", "toolCallId": "call_c1", "toolName": "Bash",
                "output": "ok",
            })
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
