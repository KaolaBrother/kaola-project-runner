#!/usr/bin/env python3
"""Scriptable mock of agy's headless stream-json protocol (Issue #323).

Offline stand-in for the real `agy` binary: the live account is not verified, so
every protocol fact here is taken from agy's headless documentation and the one
real sample the unsigned account produced (a single ERROR `result` line, exit 1).
`MOCK_AGY_SCENARIO` selects behavior and `MOCK_AGY_LOG` names a JSONL file that
records each spawn argv, user event, SIGINT and stdin close.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import uuid

SCENARIO = os.environ.get("MOCK_AGY_SCENARIO", "ok")
LOG = os.environ.get("MOCK_AGY_LOG", "")
ARGV = sys.argv[1:]
LOCK = threading.Lock()


def log(entry: dict) -> None:
    if LOG:
        with open(LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")


def emit(obj: dict) -> None:
    with LOCK:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()


def flag(name: str) -> str | None:
    return ARGV[ARGV.index(name) + 1] if name in ARGV else None


CONVERSATION = flag("--conversation") or str(uuid.uuid4())
TURNS = 0
INITED = False

ERROR_UNSIGNED = {"conversation_id": "", "status": "ERROR", "response": "",
                  "error": "authentication failed or timed out", "duration_seconds": 0,
                  "num_turns": 0, "usage": {"total_tokens": 0}}
ERROR_INELIGIBLE = {"conversation_id": "", "status": "ERROR", "response": "",
                    "error": "Eligibility check failed: Your current account is not eligible for "
                             "Antigravity. Verify your account to continue. Please verify your account "
                             "in your browser: https://accounts.example.test/verify?session=abc123.",
                    "duration_seconds": 0, "num_turns": 0, "usage": {"total_tokens": 0}}


def init() -> None:
    global INITED
    if INITED:
        return
    INITED = True
    if SCENARIO == "nested-init":
        emit({"event": "init", "init": {"conversation_id": CONVERSATION, "cwd": os.getcwd(),
                                        "tools": [], "permission_mode": "request-review"}})
    else:
        emit({"event": "init", "conversation_id": CONVERSATION,
              "init": {"cwd": os.getcwd(), "tools": ["run_command"], "permission_mode": "request-review",
                       "model": flag("--model")}})


def refuse(error: dict, stderr: str, code: int = 1) -> None:
    emit({"event": "result", "result": error})
    sys.stderr.write(stderr + "\n")
    sys.stderr.flush()
    sys.exit(code)


def step(index: int, state: str, **fields) -> None:
    emit({"event": "step_update", "step_update": {"conversation_id": CONVERSATION,
                                                  "step_index": index, "state": state, **fields}})


def normal_turn(content: str) -> None:
    global TURNS
    TURNS += 1
    step(0, "ACTIVE", step_type="user_input", text_delta=content)
    step(0, "DONE", step_type="user_input")
    step(1, "ACTIVE", step_type="tool", tool_name="run_command",
         tool_info={"name": "run_command", "parameters": {"command": "ls"}})
    if "toolfail" in content:
        step(1, "DONE", step_type="tool", tool_name="run_command",
             tool_info={"name": "run_command", "error": {"type": "denied", "message": "soft-denied"}})
    else:
        step(1, "DONE", step_type="tool", tool_name="run_command",
             tool_info={"name": "run_command", "output": "file.txt"})
    if "nostream" not in content:
        step(2, "ACTIVE", step_type="agent_response", text_delta="echo: ")
        step(2, "ACTIVE", step_type="agent_response", text_delta=content)
        step(2, "DONE", step_type="agent_response")
    emit({"event": "result", "result": {
        "conversation_id": CONVERSATION, "status": "SUCCESS", "response": "echo: " + content,
        "duration_seconds": 0.1 * TURNS, "num_turns": TURNS,
        "usage": {"input_tokens": 3 * TURNS, "output_tokens": 2 * TURNS, "total_tokens": 5 * TURNS}}})


def on_sigint(signum, frame) -> None:
    log({"event": "sigint"})
    emit({"event": "result", "result": {
        "conversation_id": CONVERSATION, "status": "INTERRUPTED", "response": "",
        "error": "", "duration_seconds": 0, "num_turns": TURNS, "usage": {}}})


def main() -> int:
    log({"event": "spawn", "argv": ARGV, "scenario": SCENARIO})
    signal.signal(signal.SIGINT, on_sigint)
    if SCENARIO == "unsigned":
        refuse(ERROR_UNSIGNED, "Error: authentication required. Run 'agy' to log in, then retry.\n"
                               "error: authentication failed or timed out")
    if SCENARIO == "ineligible":
        refuse(ERROR_INELIGIBLE, "error: Eligibility check failed")
    if SCENARIO == "crash":
        sys.stderr.write("boom: panic: runtime error\n")
        return 3
    if SCENARIO not in ("lazy", "lazy-unsigned"):
        init()
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        message = json.loads(raw)
        content = (message.get("message") or {}).get("content", "")
        log({"event": "user", "content": content})
        if SCENARIO == "lazy-unsigned":
            refuse(ERROR_UNSIGNED, "Error: authentication required. Run 'agy' to log in, then retry.")
        init()
        if SCENARIO == "die-mid":
            sys.stderr.write("fatal: connection reset\n")
            return 1
        if SCENARIO == "error-turn":
            emit({"event": "result", "result": {
                "conversation_id": "", "status": "ERROR", "response": "",
                "error": 'invalid model selection (--model "x" --effort ""): unknown model',
                "duration_seconds": 0, "num_turns": 0, "usage": {}}})
            continue
        if SCENARIO == "waiting":
            emit({"event": "result", "result": {
                "conversation_id": CONVERSATION, "status": "WAITING", "response": "",
                "duration_seconds": 0, "num_turns": TURNS, "usage": {}}})
            continue
        if content == "hang":
            step(1, "ACTIVE", step_type="agent_response", text_delta="working")
            signal.pause()      # the SIGINT handler emits INTERRUPTED and the loop goes on
            continue
        normal_turn(content)
    log({"event": "stdin-closed"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
