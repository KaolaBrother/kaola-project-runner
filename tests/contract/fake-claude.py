#!/usr/bin/env python3
"""Offline stand-in for the `claude` CLI used by the Issue #50 bridge harness.

Records one JSON line per launch to ``$FAKE_CLAUDE_RECORD``: argv, cwd, pid,
process group, the *names* of environment variables (never their values), the
value of the harness canary ``KAOLA_FAKE_CANARY`` only, and whether the two
API credential variables were present. Then it emits a minimal
``--output-format stream-json`` conversation.

Issue #65: the bridge drives every streaming turn with ``--input-format
stream-json`` and no positional prompt, so the first user message arrives as one
JSON line on stdin. A second such line while the turn is still running is a
native mid-turn steer; this stand-in echoes it into the same turn and into the
single ``result``, exactly as the real CLI absorbs it.

``FAKE_CLAUDE_MODE`` (or a ``[mode]`` prefix on the prompt text): ``echo``
(default) answers and exits; ``permission`` first emits a
``permission_request`` line; ``hang`` starts a ``sleep`` grandchild and
blocks until killed; ``fail`` announces its session id and exits 1 like a
CLI that could not serve the turn; ``failresume`` does the same only when
``--resume`` is passed, so the fresh fallback after a failed resume really
serves its turn; ``resumefailhang`` fails on ``--resume`` and hangs on the
fresh fallback turn, so that fallback can be cancelled while it runs;
``silent`` starts the ``sleep`` grandchild and blocks without writing a
single line, so the bridge never forwards a ``session/update`` for the turn.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid

RECORD = os.environ.get("FAKE_CLAUDE_RECORD")
MODES = ("echo", "permission", "hang", "fail", "failresume", "resumefailhang", "silent")


def option(argv, flag):
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv):
            return argv[index + 1]
    return None


def read_stream_message(stream):
    """One ``--input-format stream-json`` user message line; "" at EOF."""
    line = stream.readline()
    while line:
        line = line.strip()
        if line:
            try:
                message = json.loads(line)
            except ValueError:
                return ""
            blocks = ((message.get("message") or {}).get("content")) or []
            return "\n".join(
                block.get("text", "") for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            )
        line = stream.readline()
    return ""


def collect_steers(stream, sink):
    """Every later stdin message is a mid-turn steer for the running turn."""
    while True:
        text = read_stream_message(stream)
        if not text:
            return
        sink.append(text)


def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    argv = sys.argv[1:]
    # Read-only probes the Runner issues before any turn (preflight version
    # fact, model-policy alias catalog): answer like the CLI and record nothing.
    if argv == ["--version"]:
        print("9.9.9 (fake Claude Code)")
        return 0
    if "--help" in argv:
        print("Usage: claude [options] [command] [prompt]\n\nOptions:\n"
              "  --model <model>  Model alias ('opus', 'sonnet', 'fable') or full name\n"
              "  --effort <effort>  low, medium, high, xhigh, or max\n"
              "  --permission-mode <mode>\n  --settings <file-or-json>\n"
              "  -r, --resume [sessionId]\n  -c, --continue\n  -p, --print\n"
              "  --output-format <format>\n  --verbose")
        return 0
    stream_input = "stream-json" == option(argv, "--input-format")
    steers: list[str] = []
    if stream_input:
        prompt = read_stream_message(sys.stdin)
        threading.Thread(target=collect_steers, args=(sys.stdin, steers), daemon=True).start()
    else:
        prompt = option(argv, "-p") or ""
    mode = os.environ.get("FAKE_CLAUDE_MODE", "echo")
    for candidate in MODES:
        if prompt.startswith(f"[{candidate}]"):
            mode = candidate
    resume = option(argv, "--resume")
    session_id = resume or str(uuid.uuid4())
    mcp_config = option(argv, "--mcp-config")
    entry = {
        "argv0": os.path.realpath(sys.argv[0]),
        "argv": argv,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "pgid": os.getpgid(0),
        "ppid": os.getppid(),
        "env_keys": sorted(os.environ),
        "canary": os.environ.get("KAOLA_FAKE_CANARY"),
        "has_api_key": "ANTHROPIC_API_KEY" in os.environ,
        "has_auth_token": "ANTHROPIC_AUTH_TOKEN" in os.environ,
        "mode": mode,
        "session_id": session_id,
        "mcp_config": mcp_config,
        "mcp_config_exists": bool(mcp_config) and os.path.isfile(mcp_config),
    }
    grandchild = None
    # ``resumefailhang`` only hangs on the fresh fallback leg; on its failing
    # ``--resume`` leg it must exit at once without a grandchild, or the
    # inherited stdout pipe stays open and no reader ever sees the exit.
    hang_like = mode in ("hang", "silent") or (mode == "resumefailhang" and not resume)
    if hang_like:
        # The real CLI handles SIGTERM and exits with status 143 (128 + 15)
        # instead of dying by signal; a bridge must treat that as a cancel,
        # never as an expired session to resume afresh.
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        grandchild = subprocess.Popen(["sleep", "300"])
        entry["grandchild_pid"] = grandchild.pid
    if RECORD:
        with open(RECORD, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    if mode == "silent":
        time.sleep(300)
        return 0
    emit({"type": "system", "subtype": "init", "session_id": session_id, "model": "fake-model"})
    if mode == "fail" or (mode in ("failresume", "resumefailhang") and resume):
        sys.stderr.write("fake claude: cannot serve this turn\n")
        return 1
    if mode in ("hang", "resumefailhang"):
        emit({"type": "assistant", "session_id": session_id,
              "message": {"content": [{"type": "text", "text": "hanging"}]}})
        time.sleep(300)
        return 0
    if mode == "permission":
        emit({"type": "permission_request", "session_id": session_id, "tool_name": "Bash",
              "tool_input": {"command": "echo hi"}, "permission_id": "perm-1"})
    emit({"type": "assistant", "session_id": session_id,
          "message": {"content": [{"type": "text", "text": f"echo:{prompt}"}]}})
    # A steer that arrived while this turn was running joins THIS turn: one
    # result event, carrying the redirection the running turn absorbed.
    if stream_input and os.environ.get("FAKE_CLAUDE_STEER_WAIT_MS"):
        deadline = time.time() + int(os.environ["FAKE_CLAUDE_STEER_WAIT_MS"]) / 1000.0
        while time.time() < deadline and not steers:
            time.sleep(0.02)
    text = f"echo:{prompt}"
    for steer in list(steers):
        emit({"type": "assistant", "session_id": session_id,
              "message": {"content": [{"type": "text", "text": f"steered:{steer}"}]}})
        text = f"{text}|steered:{steer}"
    emit({"type": "result", "subtype": "success", "result": text,
          "session_id": session_id})
    return 0


if __name__ == "__main__":
    sys.exit(main())
