#!/usr/bin/env python3
"""Hermes Agent ACP adapter (Issue #416, Option A).

A stdio pass-through over ``hermes --yolo acp`` (never ``--accept-hooks``; the
caller's ``HERMES_YOLO_MODE``/``HERMES_ACCEPT_HOOKS`` are stripped from the
child environment) with five honest transforms:

* ``initialize``: drop ``resume`` from ``sessionCapabilities`` so the holder
  takes ``session/load``; record whether ``authMethods`` offers any
  non-terminal method (only ``hermes-setup`` counts as terminal).
* ``session/new`` | ``session/load`` | ``session/fork`` results: synthesize
  ``model`` and ``mode`` select ``configOptions`` from the result's
  ``models``/``modes`` blocks and cache them per session.
* ``session/set_config_option``: ``model`` -> ``session/set_model``,
  ``mode`` -> ``session/set_mode`` (real Hermes errors pass through
  unchanged); any other configId is refused locally -32602 because Hermes
  would accept it silently.
* ``session/resume`` received anyway: forwarded as ``session/load``; a null
  or session-id-mismatched result is an error, so a silent fresh session is
  never reported as resumed.
* ``authenticate`` null result and an uncredentialed ``session/new`` (only
  terminal auth advertised) become ``-32000`` login-required errors naming
  ``hermes acp --setup`` / ``hermes model`` - provider setup is a human act
  the Runner never runs.

A busy second ``session/prompt`` is a pure pass-through. Writes nothing to
disk; standalone, stdlib only.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading

LOGIN_MESSAGE = ("login required: Hermes has no resolved provider credential. "
                 "Provider setup is a human act: run `hermes acp --setup` or "
                 "`hermes model` in a terminal; the Runner never runs it.")


def is_terminal_auth(method: object) -> bool:
    """A Hermes auth method that needs an interactive terminal setup."""
    if not isinstance(method, dict):
        return False
    args = method.get("args")
    return (method.get("type") == "terminal"
            or (isinstance(args, list) and "--setup" in args))


def build_options(result: dict) -> list[dict]:
    """Select configOptions synthesized from Hermes ``models``/``modes``."""
    options = []
    models = result.get("models")
    if isinstance(models, dict) and isinstance(models.get("availableModels"), list):
        options.append({
            "id": "model", "name": "Model", "category": "model", "type": "select",
            "currentValue": models.get("currentModelId"),
            "options": [{"value": entry.get("modelId"),
                         "name": entry.get("name") or entry.get("modelId")}
                        for entry in models["availableModels"] if isinstance(entry, dict)],
        })
    modes = result.get("modes")
    if isinstance(modes, dict) and isinstance(modes.get("availableModes"), list):
        options.append({
            "id": "mode", "name": "Mode", "category": "mode", "type": "select",
            "currentValue": modes.get("currentModeId"),
            "options": [{"value": entry.get("id"),
                         "name": entry.get("name") or entry.get("id")}
                        for entry in modes["availableModes"] if isinstance(entry, dict)],
        })
    return options


class Adapter:
    def __init__(self, child: subprocess.Popen) -> None:
        self.child = child
        self.lock = threading.RLock()
        self.output_lock = threading.Lock()
        # request id -> (downstream method, info dict)
        self.sent: dict[str, tuple[str, dict]] = {}
        # sessionId -> {"model": option|None, "mode": option|None}
        self.configs: dict[str, dict[str, dict | None]] = {}
        self.only_terminal_auth = False

    def emit(self, message) -> None:
        with self.output_lock:
            if isinstance(message, str):
                sys.stdout.write(message)
            else:
                print(json.dumps(message, ensure_ascii=False))
            sys.stdout.flush()

    def cache_options(self, session: str, options: list[dict]) -> None:
        cached = self.configs.setdefault(session, {"model": None, "mode": None})
        for option in options:
            if option.get("id") in cached:
                cached[option["id"]] = option

    def session_options(self, session: str) -> list[dict]:
        cached = self.configs.get(session) or {}
        return [cached[key] for key in ("model", "mode") if cached.get(key)]

    def native_output(self) -> None:
        for line in self.child.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                # Preserve native stdout; the holder owns malformed evidence.
                self.emit(line if line.endswith("\n") else line + "\n")
                continue
            self.transform_outbound(message)
            self.emit(message)

    def transform_outbound(self, message: dict) -> None:
        if "method" in message or "id" not in message:
            params = message.get("params")
            if (message.get("method") == "session/update" and isinstance(params, dict)
                    and isinstance(params.get("update"), dict)
                    and params["update"].get("sessionUpdate") == "current_mode_update"):
                session = params.get("sessionId")
                mode = self.configs.get(session, {}).get("mode")
                if mode is not None:
                    mode["currentValue"] = params["update"].get("currentModeId")
            return
        with self.lock:
            sent = self.sent.pop(str(message.get("id")), None)
        if sent is None:
            return
        method, info = sent
        result = message.get("result")
        error = message.get("error")
        if method == "initialize" and isinstance(result, dict):
            session_caps = (result.get("agentCapabilities") or {}).get("sessionCapabilities")
            if isinstance(session_caps, dict):
                session_caps.pop("resume", None)
            auth = result.get("authMethods")
            if isinstance(auth, list):
                self.only_terminal_auth = not any(
                    not is_terminal_auth(entry) for entry in auth)
        elif method in ("session/new", "session/fork") and isinstance(result, dict):
            session = result.get("sessionId")
            options = build_options(result)
            if isinstance(session, str):
                self.cache_options(session, options)
            if options:
                result["configOptions"] = options
        elif method == "session/new" and error is not None and self.only_terminal_auth:
            message["error"] = {
                "code": -32000,
                "message": f"{LOGIN_MESSAGE} Hermes said: {error.get('message')}",
                "data": error.get("data"),
            }
        elif method == "authenticate" and error is None and result is None:
            message.pop("result", None)
            message["error"] = {"code": -32000, "message": LOGIN_MESSAGE}
        elif method == "session/load":
            requested = info.get("sessionId")
            if error is None and (not isinstance(result, dict)
                                  or (isinstance(result.get("sessionId"), str)
                                      and result["sessionId"] != requested)):
                message.pop("result", None)
                message["error"] = {
                    "code": -32002,
                    "message": f"Hermes session {requested} not found; not resumed",
                }
            elif error is None:
                options = build_options(result)
                if isinstance(result.get("sessionId"), str):
                    self.cache_options(result["sessionId"], options)
                elif isinstance(requested, str):
                    self.cache_options(requested, options)
                merged = self.session_options(result.get("sessionId") or requested)
                if merged:
                    result["configOptions"] = merged
        elif method == "session/set_model" and error is None:
            option = self.configs.get(info.get("sessionId"), {}).get("model")
            if option is not None:
                option["currentValue"] = info.get("value")
            message["result"] = {"configOptions": self.session_options(info.get("sessionId"))}
        elif method == "session/set_mode" and error is None:
            option = self.configs.get(info.get("sessionId"), {}).get("mode")
            if option is not None:
                option["currentValue"] = info.get("value")
            message["result"] = {"configOptions": self.session_options(info.get("sessionId"))}

    def input(self, message: dict) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        if "id" in message and method == "session/set_config_option":
            config_id = params.get("configId")
            session = params.get("sessionId")
            value = params.get("value")
            if config_id == "model":
                downstream = {"jsonrpc": "2.0", "id": message["id"],
                              "method": "session/set_model",
                              "params": {"sessionId": session, "modelId": value}}
                with self.lock:
                    self.sent[str(message["id"])] = ("session/set_model",
                                                    {"sessionId": session, "value": value})
            elif config_id == "mode":
                downstream = {"jsonrpc": "2.0", "id": message["id"],
                              "method": "session/set_mode",
                              "params": {"sessionId": session, "modeId": value}}
                with self.lock:
                    self.sent[str(message["id"])] = ("session/set_mode",
                                                    {"sessionId": session, "value": value})
            else:
                self.emit({"jsonrpc": "2.0", "id": message["id"], "error": {
                    "code": -32602,
                    "message": f"unsupported config option {config_id!r}: Hermes accepts an "
                               "unknown configId silently, so it is refused here"}})
                return
        elif method == "session/resume":
            downstream = dict(message)
            downstream["method"] = "session/load"
            with self.lock:
                self.sent[str(message.get("id"))] = ("session/load",
                                                    {"sessionId": params.get("sessionId")})
        else:
            downstream = message
            if "id" in message and isinstance(method, str):
                with self.lock:
                    self.sent[str(message["id"])] = (
                        "session/load" if method == "session/load" else method,
                        {"sessionId": params.get("sessionId")})
        self.child.stdin.write(json.dumps(downstream, ensure_ascii=False) + "\n")
        self.child.stdin.flush()


def main() -> int:
    binary = os.environ.get("HERMES_BIN") or "hermes"
    env = {key: value for key, value in os.environ.items()
           if key not in ("HERMES_YOLO_MODE", "HERMES_ACCEPT_HOOKS")}
    child = subprocess.Popen([binary, "--yolo", "acp"], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=None, text=True, env=env)
    adapter = Adapter(child)
    closing = threading.Event()

    def stop(signum, frame):
        code = child.poll()
        raise SystemExit(code if code is not None and code >= 0 else 128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def pump():
        try:
            adapter.native_output()
        finally:
            # Native EOF must reach the holder even while its stdin is open.
            child.wait()
            if not closing.is_set():
                os.kill(os.getpid(), signal.SIGTERM)

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    try:
        for line in sys.stdin:
            adapter.input(json.loads(line))
    finally:
        closing.set()
        try:
            child.stdin.close()
        except BrokenPipeError:
            pass
        try:
            child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        reader.join(timeout=1)
    return child.returncode


if __name__ == "__main__":
    sys.exit(main())
