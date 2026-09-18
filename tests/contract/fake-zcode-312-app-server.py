#!/usr/bin/env python3
"""Hermetic fake ZCode 3.12+ `app-server --stdio` for the Issue #79 suite.

Mirrors the strictness measured in the installed 3.12.3 bundle
(`/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`), recorded in
`kaola-workflow/issue-79/evidence/03-registry-push-schema.md`:

* `session/create` is `.strict()` and has no model channel at all, so a
  pre-3.12 `runtimeModel` overlay is rejected with -32602.
* `provider/updateAccountConfig` validates like `G6n`
  (`parseProcessAccountProviderConfigSnapshot`): non-empty `revision` and
  `basedOnZCodeBuiltinRevision`, a providers record narrowed to
  `{builtinModelIds, access:{type, entitled}}`, and a REQUIRED boolean
  `states[id].current` for every entitled zhipu-account provider.
* `session/setModel` validates like `mo`
  (`{providerId, modelId, options?:{reasoningLevel?}}`, all strict) and refuses
  a provider that was never registered.
* a turn with no selection fails like `createRuntimeModel`, with
  `CONFIGURATION_ERROR` / `Select a model before continuing` at turn phase
  `model_creation`.
* scenario `switch_rejected` refuses every `session/setModel` after the first,
  so a rejected mid-session switch can be driven end to end.
* every model request first asks `interaction/requestProviderRuntimeHeaders`
  and refuses to proceed unless the answer matches the strict `VKe` union and
  actually carries `requestAuth`.

No credential, network, login or installed ZCode is involved. The API key it
checks against is a fixture value that exists only inside the test tree.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from typing import Any

WRITE_LOCK = threading.Lock()

# `session/create` accepted keys, from the installed 3.12.3 schema.
CREATE_KEYS = {
    "sessionId", "workspace", "parentSessionId", "mode", "model", "persistence",
    "thoughtLevel", "titleGenerationEnabled", "mcpServers", "toolAllowlist",
    "toolDenylist", "importedHistory", "offPeakToolEnabled",
}
SETMODEL_KEYS = {"sessionId", "model", "expectedRevision", "persistAsWorkspaceLastUsed"}
MODEL_KEYS = {"providerId", "modelId", "options"}
ACCOUNT_KEYS = {"revision", "basedOnZCodeBuiltinRevision", "providers", "states"}
AVAILABILITY = {"available", "pending", "unavailable", "unknown"}


def emit(msg: dict[str, Any]) -> None:
    data = json.dumps(msg).encode("utf-8") + b"\n"
    with WRITE_LOCK:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


def record(update: dict[str, Any]) -> None:
    path = os.environ.get("FAKE_ZCODE_RECORD")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        payload = {}
    payload.update(update)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


class Fake312:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.seq = 0
        self.counter = 0
        self.next_request_id = 5000
        self.catalog: dict[str, list[str]] = {}
        self.selection: dict[str, dict[str, str]] = {}
        self.set_model_calls = 0
        self.sessions: dict[str, dict[str, Any]] = {}
        self.pending: dict[Any, threading.Event] = {}
        self.answers: dict[Any, Any] = {}

    # -- wire -------------------------------------------------------------

    def result(self, rid: Any, value: Any) -> None:
        emit({"id": rid, "result": value})

    def error(self, rid: Any, code: int, message: str) -> None:
        emit({"id": rid, "error": {"code": code, "message": message}})

    def event(self, session_id: str, etype: str, payload: dict[str, Any]) -> None:
        self.seq += 1
        emit({"method": "session/event", "params": {
            "sessionId": session_id, "seq": self.seq, "type": etype, "payload": payload}})

    def ask(self, method: str, params: dict[str, Any], timeout: float = 10.0) -> Any:
        self.next_request_id += 1
        rid = self.next_request_id
        done = threading.Event()
        self.pending[rid] = done
        emit({"id": rid, "method": method, "params": params})
        if not done.wait(timeout):
            return None
        return self.answers.pop(rid, None)

    # -- validation mirrors ----------------------------------------------

    def check_account(self, params: dict[str, Any]) -> str | None:
        extra = set(params) - ACCOUNT_KEYS
        if extra:
            return f'Invalid params - (root): Unrecognized key: "{sorted(extra)[0]}"'
        if not str(params.get("revision") or "").strip():
            return "Account Config revision cannot be empty"
        if not str(params.get("basedOnZCodeBuiltinRevision") or "").strip():
            return "Account Config Built-in revision cannot be empty"
        providers = params.get("providers")
        if not isinstance(providers, dict) or not providers:
            return "providers must be a non-empty record"
        states = params.get("states") or {}
        for pid, entry in providers.items():
            if not isinstance(entry, dict):
                return f"provider entry must be an object: {pid}"
            ids = entry.get("builtinModelIds")
            if not isinstance(ids, list) or not ids:
                return f"builtinModelIds must be a non-empty array: {pid}"
            access = entry.get("access") or {}
            entitled = isinstance(access, dict) and access.get("entitled") is True
            zhipu = isinstance(access, dict) and access.get("type") == "zhipu-account"
            if pid.startswith("account:") and zhipu and entitled:
                state = states.get(pid) or {}
                # Measured live against installed 3.12.3: all three are required.
                if not isinstance(state.get("current"), bool):
                    return f"Account State missing current: {pid}"
                if state.get("availability") not in AVAILABILITY:
                    return (f"states.{pid}.availability: Invalid option: expected one of "
                            '"available"|"pending"|"unavailable"|"unknown"')
                if not isinstance(state.get("entitled"), bool):
                    return (f"states.{pid}.entitled: Invalid input: expected boolean, "
                            "received undefined")
        return None

    # -- dispatch ---------------------------------------------------------

    def handle(self, msg: dict[str, Any]) -> None:
        if "id" in msg and "method" not in msg:
            rid = msg.get("id")
            self.answers[rid] = msg.get("result")
            waiter = self.pending.pop(rid, None)
            if waiter:
                waiter.set()
            return

        method = msg.get("method")
        rid = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            self.result(rid, {"protocolVersion": 1,
                              "capabilities": {"independentPlanState": True}})
            return

        if method == "provider/updateAccountConfig":
            if self.scenario == "no_account_method":
                self.error(rid, -32601, "Method not found: provider/updateAccountConfig")
                return
            problem = self.check_account(params)
            if problem:
                self.error(rid, -32602, f"invalid params: {problem}")
                return
            for pid, entry in params["providers"].items():
                self.catalog[pid] = list(entry["builtinModelIds"])
            record({"account_push": params, "catalog": self.catalog})
            self.result(rid, {})
            return

        if method == "session/create":
            extra = sorted(set(params) - CREATE_KEYS)
            if extra:
                # The exact 3.12.3 rejection a pre-3.12 overlay triggers.
                self.error(rid, -32602,
                           f'Invalid params - (root): Unrecognized key: "{extra[0]}"')
                return
            self.counter += 1
            sid = f"sess_312_{self.counter}"
            self.sessions[sid] = {"mode": params.get("mode")}
            record({"create_params": params})
            self.result(rid, {"session": {"sessionId": sid, "mode": params.get("mode")}})
            return

        if method == "session/setModel":
            extra = sorted(set(params) - SETMODEL_KEYS)
            if extra:
                self.error(rid, -32602,
                           f'Invalid params - (root): Unrecognized key: "{extra[0]}"')
                return
            model = params.get("model")
            if not isinstance(model, dict) or sorted(set(model) - MODEL_KEYS):
                self.error(rid, -32602, "invalid params: model")
                return
            pid, mid = model.get("providerId"), model.get("modelId")
            # `switch_rejected`: the initial selection succeeds, every later one
            # is refused, so a mid-session switch can be observed failing.
            if self.scenario == "switch_rejected":
                self.set_model_calls += 1
                if self.set_model_calls > 1:
                    self.error(rid, -32602, f"{mid} refused by the backend")
                    return
            if pid not in self.catalog:
                self.error(rid, -32602,
                           f"{pid} is not in the Provider Registry")
                return
            if mid not in self.catalog[pid]:
                self.error(rid, -32602, f"{mid} is not offered by {pid}")
                return
            # Measured live against installed 3.12.3: an account provider
            # refuses a selection that carries no explicit reasoning level.
            if pid.startswith("account:"):
                level = (model.get("options") or {}).get("reasoningLevel")
                if not level:
                    self.error(rid, -32603,
                               f"Reasoning level is required for {pid}/{mid}")
                    return
            self.selection[params.get("sessionId")] = {"providerId": pid, "modelId": mid}
            record({"set_model": params})
            self.result(rid, {})
            return

        if method == "session/subscribe":
            self.result(rid, {})
            return

        if method in ("session/close", "session/stop"):
            self.result(rid, {})
            return

        if method == "session/send":
            sid = params.get("sessionId")
            self.result(rid, {"turnId": "turn_1"})
            threading.Thread(target=self.turn, args=(sid,), daemon=True).start()
            return

        if rid is not None:
            self.result(rid, {})

    # -- one turn ---------------------------------------------------------

    def turn(self, sid: str) -> None:
        selection = self.selection.get(sid)
        if not selection:
            # createRuntimeModel with an empty registry.
            self.event(sid, "turn.terminal", {
                "kind": "turn.terminal", "status": "failed",
                "turnPhase": "model_creation",
                "errorCode": "CONFIGURATION_ERROR",
                "errorMessage": "Select a model before continuing"})
            return
        answer = self.ask("interaction/requestProviderRuntimeHeaders", {
            "requestId": "req_1", "sessionId": sid, "turnId": "turn_1",
            "workspace": {"workspacePath": os.getcwd(), "workspaceKey": os.getcwd()},
            "modelSelection": selection, "providerId": selection["providerId"],
            "reason": "model-request"})
        problem = self.validate_headers(answer)
        record({"headers_answer_ok": problem is None, "headers_problem": problem})
        if problem is not None:
            self.event(sid, "turn.terminal", {
                "kind": "turn.terminal", "status": "failed",
                "turnPhase": "model_request",
                "errorCode": "-32031",
                "errorMessage": "Provider runtime headers were not applied before "
                                "model request attempt."})
            return
        self.event(sid, "model.streaming", {
            "kind": "text", "text": "hermetic-312-reply"})
        self.event(sid, "turn.terminal", {
            "kind": "turn.terminal", "status": "completed", "turnPhase": "done"})

    def validate_headers(self, answer: Any) -> str | None:
        if not isinstance(answer, dict):
            return "no response"
        applied = answer.get("headersApplied")
        if applied is not True:
            return f"headersApplied={applied!r}"
        extra = sorted(set(answer) - {"headersApplied", "requestAuth", "errorMessage"})
        if extra:
            return f"unrecognized key {extra[0]}"
        auth = answer.get("requestAuth")
        if not isinstance(auth, dict):
            return "requestAuth missing"
        if sorted(set(auth) - {"apiKey", "headers"}):
            return "requestAuth unrecognized key"
        expected = os.environ.get("FAKE_ZCODE_EXPECT_KEY")
        if expected and auth.get("apiKey") != expected:
            return "apiKey mismatch"
        if not auth.get("apiKey") and not auth.get("headers"):
            return "requestAuth carries neither apiKey nor headers"
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="app-server")
    parser.add_argument("--stdio", action="store_true")
    args, _ = parser.parse_known_args()
    scenario = os.environ.get("FAKE_ZCODE_SCENARIO", "basic")
    # Proof that the adapter injected a real, existing bundled table path.
    record({
        "argv": sys.argv[1:],
        "env_names": sorted(os.environ),
        "builtin_env": os.environ.get("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"),
        "personal_env": os.environ.get("ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"),
        "builtin_env_exists": os.path.isfile(
            os.environ.get("ZCODE_BUILTIN_PROVIDER_CONFIG_FILE") or ""),
        "scenario": scenario,
    })
    fake = Fake312(scenario)
    for raw in sys.stdin.buffer:
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if isinstance(msg, dict):
            fake.handle(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
