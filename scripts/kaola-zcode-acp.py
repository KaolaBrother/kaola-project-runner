#!/usr/bin/env python3
"""Runner-owned ACP adapter for the native ZCode stdio app-server.

Speaks ACP (newline-delimited JSON-RPC) to the Kaola Runner on stdin/stdout and
the private ZCode Protocol to an explicitly resolved `app-server --stdio` child.

Issue #51 selection gate, Gate 2: the active community adapter
`william0wang/zcode-acp` could not be reduced to the Runner-required surface
(its quota, task-index, goal-loop and sandbox code is imported *by* the core
handlers), so this is a Runner-owned translation written against that project's
`docs/PROTOCOL.md` as reference. See `third_party/zcode-acp/UPSTREAM.md`.

Deliberate non-capabilities, enforced here and asserted by the contract suite:

* no credential or config read - never opens ``~/.zcode/v2/config.json``,
  ``~/.zcode/v2/credentials.json`` or ``~/.config/zcode-acp/config.json``;
* no auth environment injection - the child env is built from a strict
  allowlist, so ``ANTHROPIC_API_KEY`` and friends are never forwarded and the
  native runtime resolves its own Coding Plan login;
* no config rewrite, no ``tasks-index.sqlite`` write;
* no network, no quota client, no remote hub, no listener, no daemon, no TUI,
  no sandbox. This module imports no socket, http, urllib or sqlite3.

The ZCode runtime path is explicit and fails closed: there is no PATH search,
no registry install and no filesystem discovery.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import threading
from typing import Any

ADAPTER_NAME = "kaola-zcode-acp"
ADAPTER_VERSION = "0.1.0"

# Environment names that must never reach the ZCode child. The child env is
# built from ENV_ALLOWLIST, so these are already excluded by construction;
# DENIED_ENV is the explicit, testable statement of that boundary.
DENIED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "ZCODE_API_KEY",
    "ZCODE_BASE_URL",
    "ZCODE_MODEL",
    "ZCODE_PROVIDER",
    "ZCODE_CREDENTIAL_SECRET",
    "ZCODE_BIGMODEL_USAGE_API_KEY",
    "ZCODE_BIGMODEL_USAGE_QUOTA_URL",
    "ZCODE_ACP_REMOTE",
    "ZCODE_ACP_REMOTE_TOKEN",
    "ZCODE_ACP_HUB_HOST",
    "ZCODE_ACP_HUB_PORT",
)

# Only these names are copied from the parent environment. HOME is required so
# the native runtime can find its own login; the adapter itself never reads
# anything under it.
ENV_ALLOWLIST = (
    "HOME",
    "PATH",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "USER",
    "LOGNAME",
    "SHELL",
    "TZ",
    "TERM",
)

# Protocol-documented backend modes / thought levels. These are vocabulary,
# not a catalog read from the user's config.
MODE_CHOICES = (
    ("plan", "Plan"),
    ("build", "Build"),
    ("edit", "Edit"),
    ("yolo", "Yolo"),
    ("auto", "Auto"),
)
THOUGHT_CHOICES = (
    ("low", "Low"),
    ("high", "High"),
    ("max", "Max"),
)

STDOUT_LOCK = threading.Lock()


def log(message: str) -> None:
    """Diagnostics go to stderr only; stdout is the ACP channel."""
    sys.stderr.write(f"[{ADAPTER_NAME}] {message}\n")
    sys.stderr.flush()


# --------------------------------------------------------------------------
# Explicit, fail-closed runtime resolution
# --------------------------------------------------------------------------


class RuntimeError_(Exception):
    """Raised when the explicit ZCode runtime cannot be honoured."""


def resolve_runtime(entry: str | None, node: str | None) -> tuple[str, str]:
    """Resolve the ZCode entry script and its node runtime, or fail closed.

    Both values must be explicit and must already exist. No PATH lookup, no
    glob, no registry install, no download.
    """
    entry = entry or os.environ.get("KAOLA_ZCODE_ENTRY") or ""
    node = node or os.environ.get("KAOLA_ZCODE_NODE") or ""
    if not entry:
        raise RuntimeError_(
            "no explicit ZCode entry: pass --zcode-entry or set KAOLA_ZCODE_ENTRY"
        )
    if not node:
        raise RuntimeError_(
            "no explicit ZCode node runtime: pass --zcode-node or set KAOLA_ZCODE_NODE"
        )
    if not os.path.isabs(entry) or not os.path.isabs(node):
        raise RuntimeError_("ZCode entry and node runtime must be absolute paths")
    if not os.path.isfile(entry):
        raise RuntimeError_(f"ZCode entry is not a file: {entry}")
    if not os.path.isfile(node):
        raise RuntimeError_(f"ZCode node runtime is not a file: {node}")
    if not os.access(node, os.X_OK):
        raise RuntimeError_(f"ZCode node runtime is not executable: {node}")
    return entry, node


def build_child_env() -> dict[str, str]:
    """Build the child environment from a strict allowlist.

    ELECTRON_RUN_AS_NODE is set because the shipped ZCode runtime is the
    Electron binary acting as node; it also keeps the desktop UI from starting.
    """
    env = {k: os.environ[k] for k in ENV_ALLOWLIST if k in os.environ}
    for name in DENIED_ENV:
        env.pop(name, None)
    env["ELECTRON_RUN_AS_NODE"] = "1"
    leaked = sorted(n for n in DENIED_ENV if n in env)
    if leaked:  # unreachable by construction; kept as an enforced invariant
        raise RuntimeError_(f"denied env leaked into child: {leaked}")
    return env


# --------------------------------------------------------------------------
# ZCode Protocol client
# --------------------------------------------------------------------------


class ZCodeBackend:
    """Talks the private ZCode Protocol to an `app-server --stdio` child."""

    def __init__(self, entry: str, node: str, cwd: str, on_event, on_request):
        self.entry = entry
        self.node = node
        self.cwd = cwd
        self.on_event = on_event
        self.on_request = on_request
        self.proc: subprocess.Popen | None = None
        self._next_id = 0
        self._pending: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._writer_lock = threading.Lock()

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [self.node, self.entry, "app-server", "--stdio"],
            cwd=self.cwd,
            env=build_child_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        atexit.register(self.stop)
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            self._dispatch(msg)
        # Backend died: fail every in-flight call rather than hang.
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for slot in pending:
            slot["error"] = {"code": -32000, "message": "zcode app-server exited"}
            slot["event"].set()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        if "method" in msg and "id" in msg:
            self.on_request(msg)
            return
        if "method" in msg:
            self.on_event(msg)
            return
        rid = msg.get("id")
        with self._lock:
            slot = self._pending.pop(rid, None)
        if slot is None:
            return
        slot["result"] = msg.get("result")
        slot["error"] = msg.get("error")
        slot["event"].set()

    def _write(self, msg: dict[str, Any]) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError_("zcode app-server is not running")
        data = json.dumps(msg).encode("utf-8") + b"\n"
        with self._writer_lock:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()

    def call(self, method: str, params: dict[str, Any], timeout: float = 120.0) -> Any:
        with self._lock:
            self._next_id += 1
            rid = self._next_id
            slot: dict[str, Any] = {"event": threading.Event()}
            self._pending[rid] = slot
        self._write({"id": rid, "method": method, "params": params})
        if not slot["event"].wait(timeout):
            with self._lock:
                self._pending.pop(rid, None)
            raise RuntimeError_(f"zcode call timed out: {method}")
        if slot.get("error"):
            raise RuntimeError_(f"zcode error for {method}: {slot['error']}")
        return slot.get("result")

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"method": method, "params": params})

    def respond(self, request_id: Any, result: Any) -> None:
        self._write({"id": request_id, "result": result})

    def stop(self) -> None:
        """Terminate the child process group and leave no stray process."""
        proc = self.proc
        self.proc = None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                proc.terminate()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


# --------------------------------------------------------------------------
# Tool-kind mapping
# --------------------------------------------------------------------------

TOOL_KINDS = {
    "Bash": "execute",
    "BashOutput": "execute",
    "Read": "read",
    "Write": "edit",
    "Edit": "edit",
    "MultiEdit": "edit",
    "NotebookEdit": "edit",
    "Glob": "search",
    "Grep": "search",
    "WebFetch": "fetch",
    "WebSearch": "fetch",
}


def tool_kind(name: str) -> str:
    return TOOL_KINDS.get(name, "other")


TOOL_STATUS = {
    "scheduled": "pending",
    "started": "in_progress",
    "progress": "in_progress",
    "result": "completed",
    "error": "failed",
}


# --------------------------------------------------------------------------
# ACP agent
# --------------------------------------------------------------------------


class Session:
    def __init__(self, acp_id: str, cwd: str, mode: str):
        self.acp_id = acp_id
        self.cwd = cwd
        self.mode = mode
        self.model_id: str | None = None
        self.provider_id: str | None = None
        self.thought: str | None = None
        self.backend_id: str | None = None
        self.subscribed = False
        self.hydrated = False
        self.turn_request_id: Any = None
        self.cancelled = False
        self.tools: dict[str, dict[str, Any]] = {}


class ZCodeAcpAgent:
    def __init__(self, entry: str, node: str, default_cwd: str, default_mode: str):
        self.entry = entry
        self.node = node
        self.default_cwd = default_cwd
        self.default_mode = default_mode
        self.sessions: dict[str, Session] = {}
        self.by_backend: dict[str, Session] = {}
        self.backend: ZCodeBackend | None = None
        self.lock = threading.Lock()
        self._next_out_id = 0
        self._out_pending: dict[Any, dict[str, Any]] = {}
        self._session_seq = 0

    # -- ACP wire ---------------------------------------------------------

    def send(self, msg: dict[str, Any]) -> None:
        data = json.dumps(msg).encode("utf-8") + b"\n"
        with STDOUT_LOCK:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    def respond(self, rid: Any, result: Any = None, error: Any = None) -> None:
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": rid}
        if error is not None:
            msg["error"] = error
        else:
            msg["result"] = result
        self.send(msg)

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def update(self, session: Session, update: dict[str, Any]) -> None:
        self.notify("session/update", {"sessionId": session.acp_id, "update": update})

    def request_client(self, method: str, params: dict[str, Any], timeout: float = 600.0):
        """Send an ACP request to the client and block for its response."""
        with self.lock:
            self._next_out_id += 1
            rid = f"zc-{self._next_out_id}"
            slot: dict[str, Any] = {"event": threading.Event()}
            self._out_pending[rid] = slot
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        if not slot["event"].wait(timeout):
            with self.lock:
                self._out_pending.pop(rid, None)
            return None
        return slot.get("result")

    # -- backend plumbing -------------------------------------------------

    def ensure_backend(self) -> ZCodeBackend:
        if self.backend is None:
            self.backend = ZCodeBackend(
                self.entry, self.node, self.default_cwd, self.on_backend_event,
                self.on_backend_request,
            )
            self.backend.start()
        return self.backend

    def materialize(self, session: Session) -> str:
        """Create and subscribe the backend session on first real use."""
        backend = self.ensure_backend()
        if session.backend_id is None:
            workspace = {"workspacePath": session.cwd, "workspaceKey": session.cwd}
            result = backend.call(
                "session/create", {"workspace": workspace, "mode": session.mode}
            ) or {}
            backend_id = (result.get("session") or {}).get("sessionId")
            if not backend_id:
                raise RuntimeError_("zcode session/create returned no sessionId")
            session.backend_id = backend_id
            with self.lock:
                self.by_backend[backend_id] = session
        if not session.subscribed:
            backend.call(
                "session/subscribe",
                {
                    "sessionId": session.backend_id,
                    "deliveryKind": "desktop-continuous",
                    "includeSnapshot": False,
                    "afterSeq": 0,
                },
            )
            session.subscribed = True
        self.hydrate_settings(session)
        return session.backend_id

    def hydrate_settings(self, session: Session) -> None:
        """Read native mode/model/thought. Never invent a substitute model."""
        if session.hydrated or session.backend_id is None or self.backend is None:
            return
        try:
            state = self.backend.call("session/read", {"sessionId": session.backend_id}) or {}
        except RuntimeError_:
            session.hydrated = True
            return
        settings = state.get("settings") or {}
        mode = (settings.get("mode") or {}).get("current")
        if isinstance(mode, str) and mode:
            session.mode = mode
        model = (settings.get("model") or {}).get("current") or {}
        if isinstance(model, dict):
            model_id = model.get("modelId")
            if isinstance(model_id, str) and model_id:
                session.model_id = model_id
            provider_id = model.get("providerId")
            if isinstance(provider_id, str) and provider_id:
                session.provider_id = provider_id
        thought = (settings.get("thoughtLevel") or {}).get("current")
        if isinstance(thought, str) and thought:
            session.thought = thought
        session.hydrated = True
        self.update(session, {
            "sessionUpdate": "config_option_update",
            "configOptions": self.config_options(session),
        })
        self.update(session, {
            "sessionUpdate": "current_mode_update",
            "currentModeId": session.mode,
        })

    def config_options(self, session: Session) -> list[dict[str, Any]]:
        mode_option: dict[str, Any] = {
            "id": "mode",
            "name": "Mode",
            "type": "select",
            "currentValue": session.mode,
            "options": [{"value": value, "name": name} for value, name in MODE_CHOICES],
        }
        thought_option: dict[str, Any] = {
            "id": "thoughtLevel",
            "name": "Thought level",
            "type": "select",
            "options": [{"value": value, "name": name} for value, name in THOUGHT_CHOICES],
        }
        if session.thought:
            thought_option["currentValue"] = session.thought
        model_option: dict[str, Any] = {
            "id": "model",
            "name": "Model",
            "type": "select",
            "options": [],
        }
        if session.model_id:
            model_value = (
                f"{session.provider_id}\\{session.model_id}"
                if session.provider_id else session.model_id
            )
            model_option["currentValue"] = model_value
            model_option["options"] = [{"value": model_value, "name": session.model_id}]
        return [mode_option, model_option, thought_option]

    @staticmethod
    def parse_model_value(value: str) -> dict[str, str]:
        """ACP config value -> backend model ref. No config.json lookup."""
        if "\\" in value:
            provider_id, model_id = value.split("\\", 1)
            if provider_id and model_id:
                return {"providerId": provider_id, "modelId": model_id}
        return {"modelId": value}

    # -- backend -> ACP ---------------------------------------------------

    def on_backend_event(self, msg: dict[str, Any]) -> None:
        if msg.get("method") != "session/event":
            return
        params = msg.get("params") or {}
        with self.lock:
            session = self.by_backend.get(params.get("sessionId"))
        if session is None:
            return
        etype = params.get("type")
        payload = params.get("payload") or {}
        try:
            self.translate_event(session, etype, payload)
        except Exception as exc:  # never let one event kill the stream
            log(f"event translation failed ({etype}): {exc}")

    def translate_event(self, session: Session, etype: str, payload: dict[str, Any]) -> None:
        if etype == "model.streaming":
            kind = payload.get("kind")
            delta = payload.get("delta") or ""
            if kind == "text_delta" and delta:
                self.update(session, {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": delta},
                })
            elif kind == "reasoning_delta" and delta:
                self.update(session, {
                    "sessionUpdate": "agent_thought_chunk",
                    "content": {"type": "text", "text": delta},
                })
            elif kind == "tool_call":
                call_id = payload.get("toolCallId")
                if call_id:
                    session.tools[call_id] = {
                        "toolName": payload.get("toolName") or "",
                        "input": payload.get("input"),
                    }
            return

        if etype == "tool.updated":
            self.translate_tool(session, payload)
            return

        if etype == "session.updated":
            usage = payload.get("usage")
            if usage:
                self.update(session, {"sessionUpdate": "usage_update", "usage": usage})
            return

        if etype == "turn.completed":
            usage = payload.get("usage")
            if usage:
                self.update(session, {"sessionUpdate": "usage_update", "usage": usage})
            stop = "cancelled" if session.cancelled else "end_turn"
            self.finish_turn(session, stop, usage)
            return

        if etype == "turn.failed":
            error = payload.get("error") or {}
            self.update(session, {
                "sessionUpdate": "agent_message_chunk",
                "content": {
                    "type": "text",
                    "text": f"[zcode turn failed] {error.get('message', 'unknown error')}",
                },
            })
            self.finish_turn(session, "cancelled" if session.cancelled else "refusal", None)
            return

        if etype == "turn.terminal":
            self.finish_turn(session, "cancelled" if session.cancelled else "end_turn", None)
            return

    def translate_tool(self, session: Session, payload: dict[str, Any]) -> None:
        kind = payload.get("kind")
        if kind == "batch":
            for item in payload.get("items") or []:
                self.translate_tool(session, item)
            return
        call_id = payload.get("toolCallId")
        if not call_id:
            return
        cached = session.tools.setdefault(call_id, {})
        name = payload.get("toolName") or cached.get("toolName") or ""
        if name:
            cached["toolName"] = name
        update: dict[str, Any] = {
            "sessionUpdate": "tool_call",
            "toolCallId": call_id,
            "title": name or call_id,
            "kind": tool_kind(name),
            "status": TOOL_STATUS.get(kind, "in_progress"),
        }
        content = []
        for field in ("stdoutTail", "stderrTail", "output", "result"):
            value = payload.get(field)
            if isinstance(value, str) and value:
                content.append({"type": "text", "text": value})
        if kind == "error":
            message = payload.get("message") or (payload.get("error") or {}).get("message")
            if message:
                content.append({"type": "text", "text": str(message)})
        if content:
            update["content"] = content
        self.update(session, update)

    def finish_turn(self, session: Session, stop: str, usage: Any) -> None:
        with self.lock:
            rid = session.turn_request_id
            session.turn_request_id = None
        if rid is None:
            return
        result: dict[str, Any] = {"stopReason": stop}
        if usage:
            result["usage"] = usage
        session.cancelled = False
        self.respond(rid, result)

    def on_backend_request(self, msg: dict[str, Any]) -> None:
        """Backend asks us something: bridge it to the ACP client."""
        threading.Thread(target=self._handle_backend_request, args=(msg,), daemon=True).start()

    def _handle_backend_request(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        params = msg.get("params") or {}
        rid = msg.get("id")
        backend = self.backend
        if backend is None:
            return
        # CLI 0.16.5 asks this during session/create, before the backend id
        # is registered. Answer with protocol defaults; never read Settings.
        if method == "session/requestRuntimePreferences":
            backend.respond(rid, {
                "nativeSearchEnhancementsEnabled": True,
                "memoryEnabled": False,
                "askUserQuestionAutoResolutionEnabled": True,
                "modelContextBudgetStrategy": "preflight-v1",
            })
            return
        # Never supply credential/header values. Native login owns auth.
        if method in (
            "interaction/requestOfficialMcpAuthHeaders",
            "interaction/requestProviderRuntimeHeaders",
        ):
            backend.respond(rid, {})
            return
        with self.lock:
            session = self.by_backend.get(params.get("sessionId"))
        if session is None:
            if method == "interaction/requestPermission":
                backend.respond(rid, {"optionId": "deny"})
            else:
                backend.respond(rid, {})
            return

        if method == "interaction/requestPermission":
            options = params.get("options") or [
                {"optionId": "allow", "kind": "allow_once", "name": "Allow once"},
                {"optionId": "deny", "kind": "deny_once", "name": "Deny"},
            ]
            answer = self.request_client("session/request_permission", {
                "sessionId": session.acp_id,
                "toolCall": {
                    "toolCallId": params.get("toolCallId"),
                    "title": params.get("toolName") or "tool",
                    "kind": tool_kind(params.get("toolName") or ""),
                    "status": "pending",
                },
                "options": options,
            })
            backend.respond(rid, self._permission_answer(answer, options))
            return

        if method == "interaction/requestUserInput":
            schema = params.get("schema") or {}
            if schema.get("interaction") == "plan_approval":
                plan_text = (params.get("input") or {}).get("plan") or ""
                self.update(session, {
                    "sessionUpdate": "plan",
                    "entries": [{"content": plan_text, "priority": "medium", "status": "pending"}],
                })
                options = [
                    {"optionId": "approve", "kind": "allow_once", "name": "Approve plan"},
                    {"optionId": "reject", "kind": "reject_once", "name": "Reject plan"},
                ]
                answer = self.request_client("session/request_permission", {
                    "sessionId": session.acp_id,
                    "toolCall": {
                        "toolCallId": params.get("toolCallId"),
                        "title": "Plan approval",
                        "kind": "other",
                        "status": "pending",
                    },
                    "options": options,
                })
                chosen = self._permission_answer(answer, options).get("optionId")
                backend.respond(rid, {"approved": chosen == "approve"})
                return
            # AskUserQuestion: surface the questions, let the client choose.
            questions = params.get("questions") or []
            options = []
            for question in questions:
                for opt in question.get("options") or []:
                    options.append({
                        "optionId": str(opt.get("value")),
                        "kind": "allow_once",
                        "name": str(opt.get("label")),
                    })
            if not options:
                backend.respond(rid, {"cancelled": True})
                return
            answer = self.request_client("session/request_permission", {
                "sessionId": session.acp_id,
                "toolCall": {
                    "toolCallId": params.get("toolCallId"),
                    "title": (questions[0].get("question") if questions else "Question") or "Question",
                    "kind": "other",
                    "status": "pending",
                },
                "options": options,
            })
            chosen = self._permission_answer(answer, options).get("optionId")
            backend.respond(rid, {"answers": [chosen]} if chosen else {"cancelled": True})
            return

        backend.respond(rid, {})

    @staticmethod
    def _permission_answer(answer: Any, options: list[dict[str, Any]]) -> dict[str, Any]:
        """Normalise an ACP permission reply; anything unclear denies."""
        deny = {"optionId": next(
            (o["optionId"] for o in options if str(o.get("kind", "")).startswith(("deny", "reject"))),
            "deny",
        )}
        if not isinstance(answer, dict):
            return deny
        outcome = answer.get("outcome")
        if isinstance(outcome, dict):
            if outcome.get("outcome") == "selected" and outcome.get("optionId"):
                return {"optionId": outcome["optionId"]}
            return deny
        if answer.get("optionId"):
            return {"optionId": answer["optionId"]}
        return deny

    # -- ACP method handlers ---------------------------------------------

    def on_initialize(self, rid: Any, params: dict[str, Any]) -> None:
        self.respond(rid, {
            "protocolVersion": 1,
            "agentCapabilities": {
                "loadSession": True,
                "sessionCapabilities": {"list": True, "resume": True, "close": True},
                "promptCapabilities": {"embeddedContext": True},
            },
            "authMethods": [],
            "agentInfo": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        })

    def on_session_new(self, rid: Any, params: dict[str, Any]) -> None:
        cwd = params.get("cwd") or self.default_cwd
        with self.lock:
            self._session_seq += 1
            acp_id = f"zcode-{self._session_seq}"
            session = Session(acp_id, cwd, self.default_mode)
            self.sessions[acp_id] = session
        self.respond(rid, {
            "sessionId": acp_id,
            "configOptions": self.config_options(session),
        })

    def on_session_load(self, rid: Any, params: dict[str, Any]) -> None:
        """Adopt an existing backend session id (ACP load/resume)."""
        acp_id = params.get("sessionId") or ""
        cwd = params.get("cwd") or self.default_cwd
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            session = Session(acp_id, cwd, self.default_mode)
            with self.lock:
                self.sessions[acp_id] = session
            if acp_id.startswith("sess_"):
                backend = self.ensure_backend()
                workspace = {"workspacePath": cwd, "workspaceKey": cwd}
                backend.call("session/resume", {"sessionId": acp_id, "workspace": workspace})
                session.backend_id = acp_id
                with self.lock:
                    self.by_backend[acp_id] = session
                backend.call("session/subscribe", {
                    "sessionId": acp_id,
                    "deliveryKind": "desktop-continuous",
                    "includeSnapshot": False,
                    "afterSeq": 0,
                })
                session.subscribed = True
                self.hydrate_settings(session)
        self.respond(rid, {})

    def on_session_list(self, rid: Any, params: dict[str, Any]) -> None:
        backend = self.ensure_backend()
        workspace = {"workspacePath": self.default_cwd, "workspaceKey": self.default_cwd}
        result = backend.call("session/list", {"workspace": workspace}) or {}
        sessions = []
        for item in result.get("sessions") or []:
            sessions.append({
                "sessionId": item.get("sessionId"),
                "title": item.get("title") or "",
            })
        self.respond(rid, {"sessions": sessions})

    def on_session_prompt(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        text = self._prompt_text(params.get("prompt"))
        try:
            backend_id = self.materialize(session)
        except RuntimeError_ as exc:
            self.respond(rid, error={"code": -32000, "message": str(exc)})
            return
        with self.lock:
            session.turn_request_id = rid
            session.cancelled = False
        try:
            self.ensure_backend().call(
                "session/send", {"sessionId": backend_id, "content": text}
            )
        except RuntimeError_ as exc:
            with self.lock:
                session.turn_request_id = None
            self.respond(rid, error={"code": -32000, "message": str(exc)})

    @staticmethod
    def _prompt_text(prompt: Any) -> str:
        if isinstance(prompt, str):
            return prompt
        parts = []
        for block in prompt or []:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "\n".join(p for p in parts if p)

    def on_session_cancel(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is not None and session.backend_id:
            session.cancelled = True
            try:
                self.ensure_backend().notify("session/stop", {"sessionId": session.backend_id})
            except RuntimeError_ as exc:
                log(f"cancel failed: {exc}")
        if rid is not None:
            self.respond(rid, {})

    def on_session_close(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.pop(acp_id, None)
            if session is not None and session.backend_id:
                self.by_backend.pop(session.backend_id, None)
        if session is not None and session.backend_id:
            try:
                self.ensure_backend().call("session/close", {"sessionId": session.backend_id})
            except RuntimeError_ as exc:
                log(f"close failed: {exc}")
        self.respond(rid, {})

    def on_set_mode(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        mode = params.get("modeId") or params.get("mode") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        session.mode = mode or session.mode
        if session.backend_id or mode:
            backend_id = self.materialize(session)
            self.ensure_backend().call(
                "session/setMode", {"sessionId": backend_id, "mode": session.mode}
            )
        self.update(session, {"sessionUpdate": "current_mode_update", "currentModeId": session.mode})
        self.update(session, {
            "sessionUpdate": "config_option_update",
            "configOptions": self.config_options(session),
        })
        self.respond(rid, {"configOptions": self.config_options(session)})

    def on_set_config_option(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        config_id = params.get("configId") or params.get("config_id") or ""
        value = params.get("value")
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        if value is None or not isinstance(value, (str, int, float, bool)):
            self.respond(rid, error={"code": -32602, "message": f"invalid value for {config_id}"})
            return
        text = str(value)
        try:
            backend_id = self.materialize(session)
            if config_id == "mode":
                session.mode = text
                self.ensure_backend().call(
                    "session/setMode", {"sessionId": backend_id, "mode": session.mode}
                )
                self.update(session, {
                    "sessionUpdate": "current_mode_update",
                    "currentModeId": session.mode,
                })
            elif config_id == "model":
                model = self.parse_model_value(text)
                # Native login owns auth. Never attach apiKey / runtimeModel overlays.
                self.ensure_backend().call(
                    "session/setModel",
                    {
                        "sessionId": backend_id,
                        "model": model,
                        "persistAsWorkspaceLastUsed": False,
                    },
                )
                session.model_id = model.get("modelId")
                session.provider_id = model.get("providerId")
            elif config_id in ("thought", "thoughtLevel", "thought_level"):
                session.thought = text
                self.ensure_backend().call(
                    "session/setThoughtLevel",
                    {"sessionId": backend_id, "thoughtLevel": session.thought},
                )
            else:
                self.respond(
                    rid,
                    error={"code": -32602, "message": f"unsupported config option {config_id}"},
                )
                return
        except RuntimeError_ as exc:
            self.respond(rid, error={"code": -32000, "message": str(exc)})
            return
        options = self.config_options(session)
        self.update(session, {"sessionUpdate": "config_option_update", "configOptions": options})
        self.respond(rid, {"configOptions": options})

    # -- main loop --------------------------------------------------------

    def handle(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        rid = msg.get("id")

        if method is None and rid is not None:
            with self.lock:
                slot = self._out_pending.pop(rid, None)
            if slot is not None:
                slot["result"] = msg.get("result")
                slot["event"].set()
            return

        handlers = {
            "initialize": self.on_initialize,
            "session/new": self.on_session_new,
            "session/load": self.on_session_load,
            "session/resume": self.on_session_load,
            "session/list": self.on_session_list,
            "session/prompt": self.on_session_prompt,
            "session/cancel": self.on_session_cancel,
            "session/close": self.on_session_close,
            "session/set_mode": self.on_set_mode,
            "session/setMode": self.on_set_mode,
            "session/set_config_option": self.on_set_config_option,
        }
        if method == "authenticate":
            # The native runtime owns its own login; nothing to do here.
            self.respond(rid, {})
            return
        handler = handlers.get(method or "")
        if handler is None:
            if rid is not None:
                self.respond(rid, error={"code": -32601, "message": f"method not found: {method}"})
            return
        try:
            handler(rid, msg.get("params") or {})
        except RuntimeError_ as exc:
            if rid is not None:
                self.respond(rid, error={"code": -32000, "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            if rid is not None:
                self.respond(rid, error={"code": -32603, "message": f"internal error: {exc}"})

    def run(self) -> int:
        for raw in sys.stdin.buffer:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                self.handle(msg)
        if self.backend is not None:
            self.backend.stop()
        return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="ACP adapter for the native ZCode app-server")
    parser.add_argument("--zcode-entry", default=None, help="absolute path to zcode.cjs")
    parser.add_argument("--zcode-node", default=None, help="absolute path to the node/Electron runtime")
    parser.add_argument("--cwd", default=None, help="workspace path for ZCode sessions")
    parser.add_argument("--mode", default="yolo", help="ZCode permission mode")
    args = parser.parse_args(argv)

    try:
        entry, node = resolve_runtime(args.zcode_entry, args.zcode_node)
    except RuntimeError_ as exc:
        log(f"fail-closed: {exc}")
        return 2

    cwd = args.cwd or os.getcwd()
    if not os.path.isdir(cwd):
        log(f"fail-closed: workspace is not a directory: {cwd}")
        return 2

    agent = ZCodeAcpAgent(entry, node, cwd, args.mode)
    try:
        return agent.run()
    except KeyboardInterrupt:
        if agent.backend is not None:
            agent.backend.stop()
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
