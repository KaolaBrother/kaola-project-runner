#!/usr/bin/env python3
"""Offline stand-in for the `claude` CLI used by the Issue #50 bridge harness.

Records one JSON line per launch to ``$FAKE_CLAUDE_RECORD``: argv, cwd, pid,
process group, the *names* of environment variables (never their values), the
value of the harness canary ``KAOLA_FAKE_CANARY`` only, and whether the two
API credential variables were present. Then it emits a minimal
``--output-format stream-json`` conversation.

``FAKE_CLAUDE_MODE`` (or a ``[mode]`` prefix on the prompt text): ``echo``
(default) answers and exits; ``permission`` first emits a
``permission_request`` line; ``hang`` starts a ``sleep`` grandchild and
blocks until killed.
"""

import json
import os
import signal
import subprocess
import sys
import time
import uuid

RECORD = os.environ.get("FAKE_CLAUDE_RECORD")
MODES = ("echo", "permission", "hang")


def option(argv, flag):
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv):
            return argv[index + 1]
    return None


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
    if mode == "hang":
        # The real CLI handles SIGTERM and exits with status 143 (128 + 15)
        # instead of dying by signal; a bridge must treat that as a cancel,
        # never as an expired session to resume afresh.
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        grandchild = subprocess.Popen(["sleep", "300"])
        entry["grandchild_pid"] = grandchild.pid
    if RECORD:
        with open(RECORD, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    emit({"type": "system", "subtype": "init", "session_id": session_id, "model": "fake-model"})
    if mode == "hang":
        emit({"type": "assistant", "session_id": session_id,
              "message": {"content": [{"type": "text", "text": "hanging"}]}})
        time.sleep(300)
        return 0
    if mode == "permission":
        emit({"type": "permission_request", "session_id": session_id, "tool_name": "Bash",
              "tool_input": {"command": "echo hi"}, "permission_id": "perm-1"})
    emit({"type": "assistant", "session_id": session_id,
          "message": {"content": [{"type": "text", "text": f"echo:{prompt}"}]}})
    emit({"type": "result", "subtype": "success", "result": f"echo:{prompt}",
          "session_id": session_id})
    return 0


if __name__ == "__main__":
    sys.exit(main())
