#!/usr/bin/env python3
"""Runner-owned ACP adapter for the Antigravity CLI (`agy`) headless stream protocol.

Speaks ACP (newline-delimited JSON-RPC) to the Kaola Runner on stdin/stdout and
agy's official headless protocol to one long-lived child per ACP session:

    agy --input-format stream-json --output-format stream-json
        --print-timeout 0s --model SLUG [--dangerously-skip-permissions]
        [--conversation ID]

agy ships no ACP server and the third-party ``agy-acp`` package is deliberately
not used (Issue #323). Protocol facts this adapter relies on, from agy's
headless documentation and agy 1.3.5 itself:

* stdin: one ``{"event":"user","message":{"content":"..."}}`` line per turn;
  closing stdin ends the session cleanly; a ``control_request``, a slash command
  or a non-text block ends it with an ERROR result (there is no native steer);
* stdout: one ``init`` (carries the conversation id), ``step_update`` events
  (``ACTIVE``/``DONE``, ``text_delta``, ``tool_info``) and one ``result`` per
  turn with ``status`` SUCCESS, ERROR, CANCELED, INTERRUPTED, INVALID, WAITING
  or RUNNING;
* an unsigned account makes agy print a single ERROR ``result`` and exit 1
  within about a second, before ``init`` and before any user event; a signed-in
  but ineligible account fails the same way with an ``Eligibility check
  failed ... verify your account in your browser`` error. Both become the
  recoverable ACP ``login-required`` state here, never a crash.

Effort and model. agy bakes effort into the model slug
(``gemini-4-argon-{low,medium,high}``) and also has an ``--effort`` flag whose
interaction with a suffixed slug could not be measured without an eligible
account. The adapter therefore passes ``--model SLUG`` only and never
``--effort``, so effort cannot be applied twice.

Deliberate non-capabilities, asserted by the contract suite: nothing under
``~/.gemini`` is read or written, no network client, no login attempt, no
credential handling, no ``agy models`` call, no PATH search beyond the
Runner-resolved ``AGY_BIN``.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Any

ADAPTER_NAME = "kaola-antigravity-acp"
ADAPTER_VERSION = "0.1.0"

DEFAULT_MODEL = "gemini-4-argon-medium"
# The catalog `agy models` printed on agy 1.3.5 (2026-10-14). A slug outside it
# is still accepted: agy answers an unknown model with `invalid model selection`,
# and a stale catalog must never block a working model.
MODEL_CHOICES = (
    ("gemini-4-argon-medium", "Gemini 4 Argon (Medium)"),
    ("gemini-4-argon-high", "Gemini 4 Argon (High)"),
    ("gemini-4-argon-low", "Gemini 4 Argon (Low)"),
    ("gemini-3.8-flash-high", "Gemini 3.8 Flash (High)"),
    ("gemini-3.8-flash-medium", "Gemini 3.8 Flash (Medium)"),
    ("gemini-3.8-flash-low", "Gemini 3.8 Flash (Low)"),
    ("claude-opus-5-5-low", "Claude Opus 5.5 (Low)"),
    ("claude-opus-5-5-medium", "Claude Opus 5.5 (Medium)"),
    ("claude-opus-5-5-high", "Claude Opus 5.5 (High)"),
    ("claude-sonnet-5-5-low", "Claude Sonnet 5.5 (Low)"),
    ("claude-sonnet-5-5-medium", "Claude Sonnet 5.5 (Medium)"),
    ("claude-sonnet-5-5-high", "Claude Sonnet 5.5 (High)"),
    ("gpt-oss-120b-medium", "GPT-OSS 120B (Medium)"),
)
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
# Headless agy has no approval prompt; it soft-denies shell commands unless the
# call is auto-approved, so the Runner's skip-all default maps to the one flag.
MODE_DEFAULT = "default"
MODE_BYPASS = "bypassPermissions"
MODE_CHOICES = (
    (MODE_DEFAULT, "Request review (agy default)"),
    (MODE_BYPASS, "Bypass permissions (--dangerously-skip-permissions)"),
)
CONVERSATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")
PRINT_TIMEOUT_PATTERN = re.compile(r"^\d+(ms|s|m|h)$")
DEFAULT_PRINT_TIMEOUT = "0s"  # a bare number is rejected by agy; 0 is no limit
# How long session/new waits for `init` or an early refusal. An unsigned
# account is refused in about 1 s; a child still quiet after this window is
# kept and any later refusal arrives as the turn's error. Below the holder's
# shared 15 s session/new wait.
START_WINDOW = 5.0
STDERR_TAIL = 4096
OUTPUT_CAP = 4096
URL_PATTERN = re.compile(r"https?://[^\s\"'<>)\]]+")
SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"ya29\.[A-Za-z0-9._-]+"),
    re.compile(r"(?i)((?:[a-z0-9_-]*(?:api[_-]?key|token|secret|password))=)[^\s&\"'\\]+"),
)

STDOUT_LOCK = threading.Lock()

ELIGIBILITY = re.compile(r"eligib|verify your account", re.I)
NOT_SIGNED_IN = re.compile(r"authentication required|log in|login|sign in|not authenticated|unauthenticated", re.I)
AUTH_AMBIGUOUS = re.compile(r"authentication failed|timed out waiting for auth|auth.*timed out", re.I)


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.lastindex else "") + "[redacted]", text)
    return text


def log(message: str) -> None:
    sys.stderr.write(f"{ADAPTER_NAME}: {redact(message)}\n")
    sys.stderr.flush()


class AgyError(Exception):
    """A typed failure carrying its JSON-RPC error."""

    def __init__(self, code: int, message: str, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.data = data or {}

    def rpc(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": str(self)}
        if self.data:
            error["data"] = self.data
        return error


def classify_login(error_text: str, stderr_text: str) -> dict[str, Any] | None:
    """The recoverable sign-in state behind an agy refusal, or None.

    `kind` separates what the human must do. Eligibility wins because agy words
    that failure with "sign in"-like text too; a plain "authentication failed or
    timed out" is ambiguous (it can be a transient network failure), so it is
    reported as such and never as a proven missing login.
    """
    text = f"{error_text}\n{stderr_text}"
    url_match = URL_PATTERN.search(text)
    url = url_match.group(0).rstrip(".,;:") if url_match else None
    if url is not None and len(url) > 2048:
        url = None
    if ELIGIBILITY.search(text):
        kind = "account-not-eligible"
        route = ("Open the verify URL in a browser as the account owner and finish agy's account "
                 "verification, then rerun start." if url else
                 "Verify the account in a browser as the account owner (run `agy` once to get the "
                 "link), then rerun start.")
    elif NOT_SIGNED_IN.search(text):
        kind = "not-signed-in"
        route = "Run `agy` in a terminal and sign in as the account owner, then rerun start."
    elif AUTH_AMBIGUOUS.search(text):
        kind = "auth-failed-or-timed-out"
        route = ("Run `agy` once to confirm sign-in. If it is already signed in this can be a "
                 "transient network failure: retry the start safely before declaring the account bad.")
    else:
        return None
    return {"kind": kind, "verify_url": url, "recovery": route}


def agy_failure(error_text: str, stderr_text: str, code: int | None,
                status: str | None, during: str) -> AgyError:
    """The ACP error for an agy refusal: login-required, else a generic failure.

    Only a sign-in refusal uses -32000: the holder turns -32000/-32001 and any
    message containing "auth" into `login-required` at session/new, so a generic
    failure must use another code or it would be mislabeled.
    """
    error_text = redact((error_text or "").strip())
    stderr_text = redact((stderr_text or "").strip())
    login = classify_login(error_text, stderr_text)
    meta = {"antigravity": {"agy_status": status, "agy_exit": code, "during": during}}
    if login is not None:
        stderr_lines = stderr_text.splitlines()
        text = error_text or (stderr_lines[-1] if stderr_lines else "")
        message = (f"login required: Antigravity authentication refused ({login['kind']}): "
                   f"{text[:300].rstrip('.')}. Recovery: {login['recovery']}")
        if login["verify_url"]:
            message += f" Verify URL: {login['verify_url']}"
        return AgyError(-32000, message, {**meta, "login": login})
    detail = error_text or stderr_text[-400:] or "no error text"
    return AgyError(-32603, f"agy failed during {during}"
                    + (f" (exit {code})" if code is not None else "") + f": {detail[:400]}", meta)


def tool_kind(name: str) -> str:
    lowered = (name or "").lower()
    for words, kind in (
        (("read", "view", "cat", "open"), "read"),
        (("write", "edit", "replace", "patch", "create"), "edit"),
        (("run", "shell", "bash", "command", "exec"), "execute"),
        (("grep", "search", "find", "glob", "list"), "search"),
        (("fetch", "web", "browse", "http"), "fetch"),
    ):
        if any(word in lowered for word in words):
            return kind
    return "other"


def cap(text: Any, limit: int = OUTPUT_CAP) -> str:
    value = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, default=str)
    return value if len(value) <= limit else value[:limit] + "…[truncated]"


class Child:
    """One agy process: reader threads, stderr tail, startup facts."""

    def __init__(self, argv: list[str], env: dict[str, str], cwd: str, signature: tuple,
                 on_event, on_exit) -> None:
        self.argv = argv
        self.signature = signature
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1, env=env, cwd=cwd)
        self.ready = threading.Event()   # `init` seen, or the process ended
        self.dead = threading.Event()
        self.initialized = False
        self.early: dict[str, Any] | None = None   # a result before any turn (startup refusal)
        self.stderr: collections.deque[str] = collections.deque()
        self._stderr_chars = 0
        self._on_event = on_event
        self._on_exit = on_exit

    def start(self) -> None:
        """Readers start only after the owner registered this child, so the
        first event (init) can never be judged against an unregistered child."""
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def alive(self) -> bool:
        return self.proc.poll() is None

    def stderr_text(self) -> str:
        return "".join(self.stderr)[-STDERR_TAIL:]

    def _read_stdout(self) -> None:
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    log(f"non-JSON stdout line ignored ({len(line)} chars)")
                    continue
                if isinstance(obj, dict):
                    self._on_event(self, obj)
        finally:
            self.proc.wait()
            self.dead.set()
            self.ready.set()
            self._on_exit(self)

    def _read_stderr(self) -> None:
        for line in self.proc.stderr:
            self.stderr.append(line)
            self._stderr_chars += len(line)
            while self._stderr_chars > STDERR_TAIL * 2 and len(self.stderr) > 1:
                self._stderr_chars -= len(self.stderr.popleft())

    def write(self, obj: dict[str, Any]) -> None:
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def interrupt(self) -> None:
        try:
            self.proc.send_signal(signal.SIGINT)
        except (OSError, ProcessLookupError):
            pass

    def stop(self) -> None:
        """Documented clean end: close stdin, then escalate."""
        try:
            self.proc.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            self.proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


class Session:
    def __init__(self, acp_id: str, cwd: str, conversation_id: str | None = None,
                 persisted: bool = False) -> None:
        self.acp_id = acp_id
        self.cwd = cwd
        self.model = DEFAULT_MODEL
        self.mode = MODE_DEFAULT
        self.conversation_id = conversation_id
        self.persisted = persisted           # a conversation exists: respawn uses --conversation
        self.announced: str | None = None
        self.child: Child | None = None
        self.turn_rid: Any = None
        self.cancelled = False
        self.streamed = False
        self.tools: dict[str, str] = {}


class AntigravityAcpAgent:
    def __init__(self, binary: str, default_cwd: str, print_timeout: str, start_window: float) -> None:
        self.binary = binary
        self.default_cwd = default_cwd
        self.print_timeout = print_timeout
        self.start_window = start_window
        self.sessions: dict[str, Session] = {}
        self.lock = threading.RLock()
        self._seq = 0

    # -- ACP wire ---------------------------------------------------------

    def send(self, msg: dict[str, Any]) -> None:
        data = redact(json.dumps(msg, ensure_ascii=False)).encode("utf-8") + b"\n"
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

    def update(self, session: Session, update: dict[str, Any]) -> None:
        self.send({"jsonrpc": "2.0", "method": "session/update",
                   "params": {"sessionId": session.acp_id, "update": update}})

    # -- options ----------------------------------------------------------

    def config_options(self, session: Session) -> list[dict[str, Any]]:
        models = [{"value": slug, "name": name} for slug, name in MODEL_CHOICES]
        if session.model not in {slug for slug, _ in MODEL_CHOICES}:
            models.append({"value": session.model, "name": session.model})
        return [
            {"id": "mode", "name": "Mode", "type": "select", "currentValue": session.mode,
             "options": [{"value": value, "name": name} for value, name in MODE_CHOICES]},
            {"id": "model", "name": "Model", "type": "select", "currentValue": session.model,
             "options": models},
        ]

    # -- child lifecycle --------------------------------------------------

    def child_argv(self, session: Session) -> list[str]:
        # Never --effort: effort is part of the model slug (see module docstring).
        argv = [self.binary, "--input-format", "stream-json", "--output-format", "stream-json",
                "--print-timeout", self.print_timeout, "--model", session.model]
        if session.mode == MODE_BYPASS:
            argv.append("--dangerously-skip-permissions")
        if session.persisted and session.conversation_id:
            argv += ["--conversation", session.conversation_id]
        return argv

    def ensure_child(self, session: Session) -> Child:
        """A live child whose model and mode match the session, spawning or
        replacing one when they do not. A replacement resumes the conversation
        only once one exists; before the first result there is nothing to resume."""
        signature = (session.model, session.mode)
        with self.lock:
            child = session.child
            if child is not None and child.alive() and child.signature == signature:
                return child
            session.child = None
        if child is not None:
            child.stop()
        fresh = Child(self.child_argv(session), os.environ.copy(), session.cwd, signature,
                      lambda c, obj, s=session: self.on_child_event(s, c, obj),
                      lambda c, s=session: self.on_child_exit(s, c))
        with self.lock:
            session.child = fresh
        fresh.start()
        return fresh

    def await_ready(self, child: Child) -> str:
        """'init', 'early' (a refusal result or exit), or 'quiet' (window over)."""
        deadline = time.monotonic() + self.start_window
        while time.monotonic() < deadline:
            if child.early is not None or child.dead.is_set():
                return "early"
            if child.initialized:
                return "init"
            child.ready.wait(0.05)
        return "early" if child.early is not None or child.dead.is_set() else (
            "init" if child.initialized else "quiet")

    def start_check(self, session: Session, during: str) -> str:
        child = self.ensure_child(session)
        state = self.await_ready(child)
        if state != "early":
            return state
        # A refusal result is followed by exit; give the exit a moment so the
        # exit code and stderr are complete before they are reported.
        child.dead.wait(1.5)
        early = child.early or {}
        error = agy_failure(str(early.get("error") or ""), child.stderr_text(),
                            child.proc.poll(), early.get("status"), during)
        self.discard_child(session)
        raise error

    def discard_child(self, session: Session) -> None:
        with self.lock:
            child, session.child = session.child, None
        if child is not None:
            child.stop()

    # -- agy -> ACP -------------------------------------------------------

    def on_child_event(self, session: Session, child: Child, obj: dict[str, Any]) -> None:
        name = obj.get("event")
        payload = obj.get(name) if isinstance(obj.get(name), dict) else obj
        if name == "init":
            conversation = payload.get("conversation_id") or obj.get("conversation_id")
            with self.lock:
                if session.child is not child:
                    return
                if isinstance(conversation, str) and CONVERSATION_PATTERN.fullmatch(conversation):
                    session.conversation_id = conversation
                child.initialized = True
                announce = session.conversation_id != session.announced
                session.announced = session.conversation_id
            child.ready.set()
            if announce and session.conversation_id:
                self.update(session, {"sessionUpdate": "native_session_identity",
                                      "acpSessionId": session.acp_id,
                                      "nativeSessionId": session.conversation_id})
        elif name == "step_update":
            if session.child is child:
                self.translate_step(session, payload)
        elif name == "result":
            with self.lock:
                current = session.child is child
                active = session.turn_rid is not None
            if not current:
                return
            if active:
                self.finish_turn(session, payload)
            else:
                child.early = payload      # a refusal before any turn
                child.ready.set()

    def translate_step(self, session: Session, step: dict[str, Any]) -> None:
        with self.lock:
            if session.turn_rid is None:
                return
        step_type = step.get("step_type")
        state = step.get("state")
        if step_type == "tool" or isinstance(step.get("tool_info"), dict):
            self.translate_tool(session, step, state)
            return
        delta = step.get("text_delta")
        if isinstance(delta, str) and delta and step_type != "user_input":
            session.streamed = True
            self.update(session, {"sessionUpdate": "agent_message_chunk",
                                  "content": {"type": "text", "text": delta}})

    def translate_tool(self, session: Session, step: dict[str, Any], state: Any) -> None:
        info = step.get("tool_info") if isinstance(step.get("tool_info"), dict) else {}
        name = str(step.get("tool_name") or info.get("name") or "tool")
        call_id = f"{step.get('conversation_id') or session.conversation_id or session.acp_id}:{step.get('step_index')}"
        if call_id not in session.tools:
            session.tools[call_id] = name
            call: dict[str, Any] = {"sessionUpdate": "tool_call", "toolCallId": call_id, "title": name,
                                    "kind": tool_kind(name),
                                    "status": "in_progress" if state != "DONE" else "completed"}
            if info.get("parameters") is not None:
                raw = info["parameters"]
                call["rawInput"] = raw if len(json.dumps(raw, default=str)) <= OUTPUT_CAP else cap(raw)
            self.update(session, call)
        if state != "DONE":
            return
        failure = info.get("error") if isinstance(info.get("error"), dict) else None
        done: dict[str, Any] = {"sessionUpdate": "tool_call_update", "toolCallId": call_id,
                                "status": "failed" if failure else "completed"}
        text = cap(failure.get("message") if failure else info.get("output"))
        if failure or info.get("output") is not None:
            done["content"] = [{"type": "content", "content": {"type": "text", "text": text}}]
        self.update(session, done)

    def finish_turn(self, session: Session, payload: dict[str, Any]) -> None:
        status = str(payload.get("status") or "")
        conversation = payload.get("conversation_id")
        with self.lock:
            rid = session.turn_rid
            session.turn_rid = None
            cancelled = session.cancelled
            session.cancelled = False
            streamed = session.streamed
            session.tools = {}
            if isinstance(conversation, str) and conversation:
                session.conversation_id = conversation
                session.persisted = True
        if rid is None:
            return
        meta = {"antigravity": {"agy_status": status, "conversation_id": session.conversation_id,
                                "num_turns": payload.get("num_turns"),
                                "duration_seconds": payload.get("duration_seconds"),
                                "usage": payload.get("usage")}}
        response = payload.get("response")
        if status == "SUCCESS":
            if not streamed and isinstance(response, str) and response:
                self.update(session, {"sessionUpdate": "agent_message_chunk",
                                      "content": {"type": "text", "text": response}})
            self.respond(rid, {"stopReason": "end_turn", "_meta": meta})
        elif status in ("CANCELED", "INTERRUPTED"):
            self.respond(rid, {"stopReason": "cancelled", "_meta": meta})
        elif status == "ERROR":
            threading.Thread(target=self.respond_error, args=(session, rid, payload, status),
                             daemon=True).start()
        else:
            # INVALID, WAITING, RUNNING or an unknown status: no terminal success.
            self.respond(rid, error=AgyError(
                -32603, f"agy ended the turn with status {status or 'missing'}: "
                        f"{redact(str(payload.get('error') or 'no terminal state reached'))[:300]}",
                meta).rpc())

    def respond_error(self, session: Session, rid: Any, payload: dict[str, Any], status: str) -> None:
        """Answer an ERROR turn. A sign-in refusal is followed by the child's exit
        and its stderr, which classify the refusal, so wait for them (off the
        reader thread, which is the one that sets `dead`)."""
        error_text = str(payload.get("error") or "")
        child = session.child
        if child is not None and (ELIGIBILITY.search(error_text) or NOT_SIGNED_IN.search(error_text)
                                  or AUTH_AMBIGUOUS.search(error_text)):
            child.dead.wait(1.5)
        stderr = child.stderr_text() if child is not None else ""
        self.respond(rid, error=agy_failure(error_text, stderr, None, status, "the turn").rpc())

    def on_child_exit(self, session: Session, child: Child) -> None:
        with self.lock:
            # A child that was replaced, discarded or closed already left
            # session.child; its exit says nothing about the current turn.
            if session.child is not child:
                return
            session.child = None
            rid = session.turn_rid
            if rid is None:
                return
            session.turn_rid = None
            cancelled = session.cancelled
            session.cancelled = False
        if cancelled:
            self.respond(rid, {"stopReason": "cancelled",
                               "_meta": {"antigravity": {"agy_exit": child.proc.returncode}}})
            return
        self.respond(rid, error=agy_failure(
            "", child.stderr_text(), child.proc.returncode, None,
            "the turn (agy exited before a result; the turn's effects are unknown)").rpc())

    # -- ACP handlers -----------------------------------------------------

    def on_initialize(self, rid: Any, params: dict[str, Any]) -> None:
        self.respond(rid, {
            "protocolVersion": 1,
            "agentCapabilities": {
                "loadSession": False,
                "sessionCapabilities": {"resume": True, "close": True},
                "promptCapabilities": {},
            },
            "authMethods": [],
            "agentInfo": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        })

    def new_session(self, cwd: str, conversation: str | None = None) -> Session:
        with self.lock:
            self._seq += 1
            acp_id = conversation or f"antigravity-{self._seq}"
            session = Session(acp_id, cwd, conversation, persisted=conversation is not None)
            self.sessions[acp_id] = session
        return session

    def on_session_new(self, rid: Any, params: dict[str, Any]) -> None:
        session = self.new_session(params.get("cwd") or self.default_cwd)
        try:
            probe = self.start_check(session, "session start")
        except AgyError as error:
            self.drop(session)
            self.respond(rid, error=error.rpc())
            return
        self.respond(rid, {"sessionId": session.acp_id,
                           "configOptions": self.config_options(session),
                           "_meta": {"antigravity": {"conversation_id": session.conversation_id,
                                                     "start_probe": probe}}})

    def on_session_resume(self, rid: Any, params: dict[str, Any]) -> None:
        conversation = params.get("sessionId") or ""
        if not isinstance(conversation, str) or not CONVERSATION_PATTERN.fullmatch(conversation):
            self.respond(rid, error={"code": -32602, "message": "session/resume needs an agy conversation id"})
            return
        with self.lock:
            existing = self.sessions.get(conversation)
        if existing is not None:
            self.respond(rid, {"sessionId": existing.acp_id,
                               "configOptions": self.config_options(existing)})
            return
        session = self.new_session(params.get("cwd") or self.default_cwd, conversation)
        try:
            probe = self.start_check(session, "session resume")
        except AgyError as error:
            self.drop(session)
            self.respond(rid, error=error.rpc())
            return
        self.respond(rid, {"sessionId": session.acp_id,
                           "configOptions": self.config_options(session),
                           "_meta": {"antigravity": {"conversation_id": session.conversation_id,
                                                     "start_probe": probe}}})

    def drop(self, session: Session) -> None:
        with self.lock:
            self.sessions.pop(session.acp_id, None)

    @staticmethod
    def prompt_text(prompt: Any) -> str:
        if isinstance(prompt, str):
            return prompt
        parts = []
        for block in prompt or []:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "\n".join(part for part in parts if part)

    def on_session_prompt(self, rid: Any, params: dict[str, Any]) -> None:
        acp_id = params.get("sessionId") or ""
        with self.lock:
            session = self.sessions.get(acp_id)
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {acp_id}"})
            return
        text = self.prompt_text(params.get("prompt"))
        if not text.strip():
            self.respond(rid, error={"code": -32602, "message": "empty prompt"})
            return
        if text.lstrip().startswith("/"):
            # agy runs a leading-slash stream message as a CLI command and ends the
            # whole session (ERROR result, exit 2). Refused before any write.
            self.respond(rid, error={"code": -32602, "message":
                "agy treats a leading '/' in stream input as a slash command and ends the session; "
                "nothing was sent. Resend the text without a leading slash."})
            return
        with self.lock:
            if session.turn_rid is not None:
                self.respond(rid, error={"code": -32010,
                                         "message": "a prompt is already running for this session",
                                         "data": {"activeRequestId": session.turn_rid}})
                return
            session.turn_rid = rid
            session.cancelled = False
            session.streamed = False
            session.tools = {}
        try:
            child = self.ensure_child(session)
            child.write({"event": "user", "message": {"content": text}})
        except (OSError, ValueError) as exc:
            with self.lock:
                if session.turn_rid == rid:
                    session.turn_rid = None
                else:
                    return    # the exit path already answered this prompt
            self.respond(rid, error={"code": -32603,
                                     "message": f"agy stdin was not writable: {exc}"})

    def on_session_cancel(self, rid: Any, params: dict[str, Any]) -> None:
        with self.lock:
            session = self.sessions.get(params.get("sessionId") or "")
            child = session.child if session is not None else None
            if session is not None and session.turn_rid is not None and child is not None:
                session.cancelled = True
            else:
                child = None
        if child is not None:
            child.interrupt()      # agy answers SIGINT with an INTERRUPTED result
        if rid is not None:
            self.respond(rid, {})

    def on_session_close(self, rid: Any, params: dict[str, Any]) -> None:
        with self.lock:
            session = self.sessions.pop(params.get("sessionId") or "", None)
            child = session.child if session is not None else None
            if session is not None:
                session.child = None
        if child is not None:
            child.stop()
        self.respond(rid, {})

    def on_set_config_option(self, rid: Any, params: dict[str, Any]) -> None:
        with self.lock:
            session = self.sessions.get(params.get("sessionId") or "")
        config_id = params.get("configId") or params.get("config_id") or ""
        value = params.get("value")
        if session is None:
            self.respond(rid, error={"code": -32602, "message": f"unknown session {params.get('sessionId')}"})
            return
        if not isinstance(value, str) or not value:
            self.respond(rid, error={"code": -32602, "message": f"invalid value for {config_id}"})
            return
        if config_id == "model":
            if not MODEL_PATTERN.fullmatch(value):
                self.respond(rid, error={"code": -32602, "message": f"invalid model id {value!r}"})
                return
            session.model = value      # takes effect when the next prompt replaces the child
        elif config_id == "mode":
            if value not in {mode for mode, _ in MODE_CHOICES}:
                self.respond(rid, error={"code": -32602, "message": f"unsupported mode {value!r}"})
                return
            session.mode = value
        else:
            self.respond(rid, error={"code": -32602, "message": f"unsupported config option {config_id}"})
            return
        options = self.config_options(session)
        self.update(session, {"sessionUpdate": "config_option_update", "configOptions": options})
        self.respond(rid, {"configOptions": options})

    def handle(self, msg: dict[str, Any]) -> None:
        method = msg.get("method")
        rid = msg.get("id")
        if method is None:
            return      # a response to a request this adapter never sends
        handlers = {
            "initialize": self.on_initialize,
            "session/new": self.on_session_new,
            "session/resume": self.on_session_resume,
            "session/prompt": self.on_session_prompt,
            "session/cancel": self.on_session_cancel,
            "session/close": self.on_session_close,
            "session/set_config_option": self.on_set_config_option,
        }
        if method == "authenticate":
            self.respond(rid, {})      # agy owns its login; nothing to do here
            return
        handler = handlers.get(method)
        if handler is None:
            if rid is not None:
                self.respond(rid, error={"code": -32601, "message": f"method not found: {method}"})
            return
        try:
            handler(rid, msg.get("params") or {})
        except Exception as exc:  # pragma: no cover - defensive
            if rid is not None:
                self.respond(rid, error={"code": -32603, "message": f"internal error: {exc}"})

    def stop_all(self) -> None:
        with self.lock:
            children = [s.child for s in self.sessions.values() if s.child is not None]
            for session in self.sessions.values():
                session.child = None
        for child in children:
            child.stop()

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
        self.stop_all()
        return 0


def resolve_binary(value: str | None) -> str:
    """The Runner-resolved AGY_BIN: an absolute executable, or a bare name found on PATH."""
    name = value or "agy"
    if os.path.isabs(name):
        if os.path.isfile(name) and os.access(name, os.X_OK):
            return name
        raise FileNotFoundError(f"AGY_BIN is not an executable file: {name}")
    found = shutil.which(name)
    if not found:
        raise FileNotFoundError(f"agy executable not found: {name}")
    return found


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="ACP adapter for the Antigravity CLI headless stream protocol")
    parser.add_argument("--cwd", default=None, help="workspace path for agy sessions")
    args = parser.parse_args(argv)
    try:
        binary = resolve_binary(os.environ.get("AGY_BIN"))
    except FileNotFoundError as exc:
        log(f"fail-closed: {exc}")
        return 2
    cwd = args.cwd or os.getcwd()
    if not os.path.isdir(cwd):
        log(f"fail-closed: workspace is not a directory: {cwd}")
        return 2
    timeout = os.environ.get("KAOLA_ANTIGRAVITY_PRINT_TIMEOUT") or DEFAULT_PRINT_TIMEOUT
    if not PRINT_TIMEOUT_PATTERN.fullmatch(timeout):
        log(f"invalid KAOLA_ANTIGRAVITY_PRINT_TIMEOUT {timeout!r}; using {DEFAULT_PRINT_TIMEOUT}")
        timeout = DEFAULT_PRINT_TIMEOUT
    try:
        window = float(os.environ.get("KAOLA_ANTIGRAVITY_START_WINDOW") or START_WINDOW)
    except ValueError:
        window = START_WINDOW
    window = min(max(window, 0.2), 12.0)
    agent = AntigravityAcpAgent(binary, cwd, timeout, window)

    def terminate(signum, frame):
        agent.stop_all()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    return agent.run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
