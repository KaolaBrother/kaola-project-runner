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
import time
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
    if "slow" in content:
        time.sleep(0.45)
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
    if SCENARIO == "legacy-interrupted":
        emit({"event": "result", "result": {
            "conversation_id": CONVERSATION, "status": "INTERRUPTED", "response": "",
            "error": "", "duration_seconds": 0, "num_turns": TURNS, "usage": {}}})
        return
    # Real agy 1.3.5 (Issue #328): SIGINT cancels the root NotifyContext,
    # emits an ERROR result with `error: "interrupted"` carrying the persisted
    # conversation_id, writes `error: interrupted` to stderr, and exits 1.
    emit({"event": "result", "result": {
        "conversation_id": CONVERSATION, "status": "ERROR", "response": "",
        "error": "interrupted", "duration_seconds": 0, "num_turns": TURNS, "usage": {}}})
    sys.stderr.write("error: interrupted\n")
    sys.stderr.flush()
    sys.exit(1)


USAGE_COMMAND_DATA = {
    "description": "Within each group, models share a weekly limit and a 5-hour limit.",
    "groups": [
        {
            "name": "Gemini Models",
            "description": "Models within this group: Gemini Flash, Gemini Pro",
            "buckets": [
                {
                    "id": "gemini-weekly",
                    "name": "Weekly Limit Remaining",
                    "window": "weekly",
                    "remaining_fraction": 0.9455534815788269,
                    "reset_time": "2026-10-21T07:35:54Z",
                },
                {
                    "id": "gemini-5h",
                    "name": "Five Hour Limit Remaining",
                    "window": "5h",
                    "remaining_fraction": 0.9279129505157471,
                    "reset_time": "2026-10-14T22:35:54Z",
                },
            ],
        },
        {
            "name": "Claude and GPT models",
            "description": "Models within this group: Claude Opus, Claude Sonnet, GPT-OSS",
            "buckets": [
                {
                    "id": "3p-weekly",
                    "name": "Weekly Limit Remaining",
                    "window": "weekly",
                    "remaining_fraction": 1,
                    "reset_time": "2026-10-21T18:50:58Z",
                },
                {
                    "id": "3p-5h",
                    "name": "Five Hour Limit Remaining",
                    "window": "5h",
                    "remaining_fraction": 1,
                    "reset_time": "2026-10-14T23:50:58Z",
                },
            ],
        },
    ],
}

USAGE_SUMMARY_LEGACY = {
    "groups": [
        {
            "group": "Gemini Models",
            "buckets": [
                {
                    "id": "gemini-weekly",
                    "label": "Weekly",
                    "remaining_fraction": 0.9455534815788269,
                    "reset_time": "2026-10-21T07:35:54Z",
                },
                {
                    "id": "gemini-5h",
                    "label": "5-Hour",
                    "remaining_fraction": 0.9279129505157471,
                    "reset_time": "2026-10-14T22:35:54Z",
                },
            ],
        },
        {
            "group": "Claude and GPT models",
            "buckets": [
                {
                    "id": "3p-weekly",
                    "label": "Weekly",
                    "remaining_fraction": 1,
                    "reset_time": "2026-10-21T18:50:58Z",
                },
                {
                    "id": "3p-5h",
                    "label": "5-Hour",
                    "remaining_fraction": 1,
                    "reset_time": "2026-10-14T23:50:58Z",
                },
            ],
        },
    ]
}


def handle_prompt_slash(prompt: str) -> int:
    if SCENARIO == "unsigned":
        emit(ERROR_UNSIGNED)
        sys.stderr.write(
            "Authentication required. Please visit the URL to log in:\n"
            "  https://accounts.google.com/o/oauth2/v2/auth?mock=1\n"
            "Error: authentication required. Run 'agy' to log in, then retry.\n"
            "error: authentication failed or timed out\n"
        )
        sys.stderr.flush()
        return 1
    if SCENARIO == "unsigned-oauth-wait":
        def _abort_oauth(signum, frame) -> None:
            log({"event": "sigint-oauth"})
            emit(ERROR_UNSIGNED)
            sys.stderr.write("error: authentication failed or timed out\n")
            sys.stderr.flush()
            sys.exit(1)

        signal.signal(signal.SIGINT, _abort_oauth)
        sys.stderr.write(
            "Authentication required. Please visit the URL to log in:\n"
            "  https://accounts.google.com/o/oauth2/v2/auth?mock=1\n"
        )
        sys.stderr.flush()
        time.sleep(30.0)
        return 1
    if SCENARIO == "ineligible":
        emit(ERROR_INELIGIBLE)
        sys.stderr.write("error: Eligibility check failed\n")
        sys.stderr.flush()
        return 1
    if SCENARIO == "inner-json":
        emit({
            "conversation_id": "",
            "status": "SUCCESS",
            "response": json.dumps(USAGE_SUMMARY_LEGACY, indent=2),
            "duration_seconds": 0.72,
            "num_turns": 0,
            "usage": {},
        })
        return 0
    emit({
        "conversation_id": "",
        "status": "SUCCESS",
        "response": (
            "Gemini Models\tWeekly Limit Remaining\t94%\t2026-10-21T07:35:54Z\n"
            "Gemini Models\tFive Hour Limit Remaining\t92%\t2026-10-14T22:35:54Z\n"
            "Claude and GPT models\tWeekly Limit Remaining\t100%\t2026-10-21T18:50:58Z\n"
            "Claude and GPT models\tFive Hour Limit Remaining\t100%\t2026-10-14T23:50:58Z\n"
        ),
        "duration_seconds": 0,
        "num_turns": 0,
        "usage": {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, "cache_read_tokens": 0, "total_tokens": 0},
        "command": {"name": "usage", "data": USAGE_COMMAND_DATA},
    })
    return 0


def main() -> int:
    global TURNS
    log({"event": "spawn", "argv": ARGV, "scenario": SCENARIO})
    prompt_arg = flag("-p") or flag("--prompt")
    if prompt_arg in ("/usage", "/quota") and flag("--output-format") == "json":
        return handle_prompt_slash(prompt_arg)
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
            TURNS += 1
            step(1, "ACTIVE", step_type="agent_response", text_delta="working")
            signal.pause()
            continue
        normal_turn(content)
    log({"event": "stdin-closed"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
