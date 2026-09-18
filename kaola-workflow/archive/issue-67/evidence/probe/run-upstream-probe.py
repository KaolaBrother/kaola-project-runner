#!/usr/bin/env python3
"""Isolated live probe: ZCode app-server tool payload vs translated ACP tool_call.

Does not use tmux, does not touch other sessions, does not print credentials.
"""

from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner")
WT = ROOT / ".kw" / "worktrees" / "issue-67"
ADAPTER = WT / "scripts" / "kaola-zcode-acp.py"
EVIDENCE = ROOT / "kaola-workflow" / "issue-67" / "evidence"
PROBE_DIR = EVIDENCE / "probe"
ENTRY = "/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"
NODE = "/opt/homebrew/bin/node"
MARKER_LINE = "kpr-issue-67-marker-a1f3"


def wait_for(pred, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = pred()
        if value:
            return value
        time.sleep(0.05)
    return pred()


def pids_with_cwd(cwd: str) -> list[int]:
    found = []
    proc = Path("/proc")
    if proc.is_dir():
        return found
    try:
        out = subprocess.check_output(["ps", "-ax", "-o", "pid=,command="], text=True)
    except (OSError, subprocess.CalledProcessError):
        return found
    needle = str(cwd)
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_s, cmd = line.split(None, 1)
        except ValueError:
            continue
        if "kaola-zcode-acp.py" in cmd and needle in cmd:
            found.append(int(pid_s))
            continue
        if "app-server" in cmd and needle in cmd:
            found.append(int(pid_s))
    return found


def main() -> int:
    if not ADAPTER.is_file():
        print("missing adapter", ADAPTER, file=sys.stderr)
        return 2
    if not os.path.isfile(ENTRY) or not os.access(NODE, os.X_OK):
        print("missing explicit ZCode runtime", file=sys.stderr)
        return 2

    sentinel = EVIDENCE / "live-sentinel"
    if sentinel.exists():
        for child in sentinel.iterdir():
            if child.is_file():
                child.unlink()
    sentinel.mkdir(parents=True, exist_ok=True)
    marker = sentinel / "MARKER.txt"
    marker.write_text(MARKER_LINE + "\nsecond line\n", encoding="utf-8")
    dump_path = EVIDENCE / "live" / "zcode-upstream-events.json"
    acp_path = EVIDENCE / "live" / "zcode-acp-tool-calls.json"
    dump_path.parent.mkdir(parents=True, exist_ok=True)

    env = {
        "HOME": os.environ.get("HOME", ""),
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "LANG": os.environ.get("LANG", "C"),
        "LC_ALL": os.environ.get("LC_ALL", "C"),
        "USER": os.environ.get("USER", ""),
        "LOGNAME": os.environ.get("LOGNAME", ""),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "PYTHONPATH": str(PROBE_DIR),
        "PYTHONUNBUFFERED": "1",
        "NO_COLOR": "1",
        "KAOLA_ZCODE_UPSTREAM_DUMP": str(dump_path),
        "KAOLA_PROBE_MARKER": str(marker),
        "KAOLA_PROBE_SENTINEL": str(sentinel),
        "KAOLA_ZCODE_ENTRY": ENTRY,
        "KAOLA_ZCODE_NODE": NODE,
    }
    for name in ("FORCE_COLOR", "CLICOLOR_FORCE"):
        env.pop(name, None)

    proc = subprocess.Popen(
        [
            sys.executable, str(ADAPTER),
            "--zcode-entry", ENTRY,
            "--zcode-node", NODE,
            "--cwd", str(sentinel),
            "--mode", "yolo",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(sentinel),
        env=env,
        start_new_session=True,
    )
    messages: list[dict] = []
    q: queue.Queue = queue.Queue()
    stderr_bytes = bytearray()

    def read_stdout() -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                messages.append(msg)
                q.put(msg)

    def read_stderr() -> None:
        assert proc.stderr is not None
        for chunk in iter(lambda: proc.stderr.read(4096), b""):
            if not chunk:
                break
            stderr_bytes.extend(chunk)

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()

    def send(msg: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(msg).encode("utf-8") + b"\n")
        proc.stdin.flush()

    def request(rid, method: str, params=None) -> None:
        payload = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = params
        send(payload)

    def wait_result(rid, timeout: float):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for msg in list(messages):
                if msg.get("id") == rid and ("result" in msg or "error" in msg):
                    return msg
            try:
                q.get(timeout=0.05)
            except queue.Empty:
                if proc.poll() is not None:
                    break
        for msg in list(messages):
            if msg.get("id") == rid and ("result" in msg or "error" in msg):
                return msg
        return None

    outcome = {
        "entry": ENTRY,
        "node": NODE,
        "sentinel": str(sentinel),
        "marker_basename": marker.name,
        "adapter": str(ADAPTER),
    }
    try:
        request(1, "initialize", {
            "protocolVersion": 1,
            "clientCapabilities": {"fs": False, "terminal": False},
            "clientInfo": {"name": "kpr-issue-67-probe", "version": "0"},
        })
        init = wait_result(1, 30)
        outcome["initialize"] = {
            "ok": bool(init and "result" in (init or {})),
            "agent": ((init or {}).get("result") or {}).get("agentInfo", {}).get("name"),
            "error": (init or {}).get("error"),
        }
        if not outcome["initialize"]["ok"]:
            raise RuntimeError("initialize failed")

        request(2, "session/new", {"cwd": str(sentinel), "mcpServers": []})
        created = wait_result(2, 60)
        result = (created or {}).get("result") or {}
        session_id = result.get("sessionId")
        outcome["session_new"] = {
            "ok": bool(session_id),
            "error": (created or {}).get("error"),
            "has_session": bool(session_id),
        }
        if not session_id:
            raise RuntimeError("session/new failed")

        request(3, "session/set_config_option", {
            "sessionId": session_id, "configId": "mode", "value": "yolo",
        })
        wait_result(3, 15)

        prompt = (
            "Read the file named MARKER.txt in the current workspace. "
            "Reply with only its first line. Do not run Bash. "
            "Do not read any other file."
        )
        request(4, "session/prompt", {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": prompt}],
        })

        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            # auto-allow permission prompts if they appear
            for msg in list(messages):
                if msg.get("method") == "session/request_permission" and "id" in msg:
                    if msg.get("_answered"):
                        continue
                    msg["_answered"] = True
                    send({
                        "jsonrpc": "2.0",
                        "id": msg.get("id"),
                        "result": {"outcome": {"outcome": "selected", "optionId": "allow"}},
                    })
            done = None
            for msg in list(messages):
                if msg.get("id") == 4 and ("result" in msg or "error" in msg):
                    done = msg
                    break
            if done:
                outcome["prompt"] = {
                    "ok": "result" in done,
                    "stopReason": (done.get("result") or {}).get("stopReason"),
                    "error": done.get("error"),
                }
                break
            if proc.poll() is not None:
                outcome["prompt"] = {"ok": False, "error": "adapter exited"}
                break
            time.sleep(0.05)
        else:
            outcome["prompt"] = {"ok": False, "error": "timeout"}

        tools = []
        texts = []
        for msg in messages:
            if msg.get("method") != "session/update":
                continue
            update = (msg.get("params") or {}).get("update") or {}
            su = update.get("sessionUpdate")
            if su in ("tool_call", "tool_call_update"):
                tools.append({
                    "sessionUpdate": su,
                    "keys": sorted(update.keys()),
                    "toolCallId": update.get("toolCallId"),
                    "title": update.get("title"),
                    "kind": update.get("kind"),
                    "status": update.get("status"),
                    "locations": update.get("locations"),
                    "rawInput_present": "rawInput" in update,
                    "rawInput_keys": sorted((update.get("rawInput") or {}).keys())
                    if isinstance(update.get("rawInput"), dict) else None,
                    "content_present": "content" in update,
                })
            elif su == "agent_message_chunk":
                text = ((update.get("content") or {}).get("text") or "")
                if text:
                    texts.append(text)
        outcome["acp_tool_calls"] = tools
        outcome["assistant_text"] = "".join(texts)[:400]
        outcome["assistant_has_marker"] = MARKER_LINE in "".join(texts)

        request(5, "session/close", {"sessionId": session_id})
        wait_result(5, 15)
    finally:
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
        stderr_text = stderr_bytes.decode("utf-8", "replace")
        # never persist stderr if it still contains an obvious long token-looking blob
        outcome["adapter_exit"] = proc.returncode
        outcome["stderr_len"] = len(stderr_text)
        outcome["stderr_has_redacted"] = "<redacted-credential>" in stderr_text

    # sitecustomize atexit should have flushed; if not, wait briefly
    wait_for(lambda: dump_path.is_file(), 2)
    upstream = {}
    if dump_path.is_file():
        upstream = json.loads(dump_path.read_text(encoding="utf-8"))
    outcome["upstream_n"] = upstream.get("n")
    streaming_tool = []
    tool_updated = []
    for ev in upstream.get("events") or []:
        if ev.get("channel") == "session/event" and ev.get("type") == "model.streaming":
            if (ev.get("payload") or {}).get("kind") == "tool_call":
                streaming_tool.append(ev.get("payload"))
        if ev.get("channel") == "session/event" and ev.get("type") == "tool.updated":
            tool_updated.append(ev.get("payload"))
        if ev.get("channel") == "interaction/requestPermission":
            outcome.setdefault("permission_requests", []).append({
                "toolName": ev.get("toolName"),
                "input_present": ev.get("input_present"),
                "input_keys": ev.get("input_keys"),
            })
    outcome["upstream_streaming_tool_calls"] = streaming_tool
    outcome["upstream_tool_updated"] = tool_updated
    outcome["upstream_any_input"] = any(
        (p or {}).get("input_present") for p in streaming_tool + tool_updated
    )
    leftover = pids_with_cwd(str(sentinel))
    outcome["leftover_pids"] = leftover
    acp_path.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": bool(outcome.get("prompt", {}).get("ok")),
        "upstream_any_input": outcome.get("upstream_any_input"),
        "streaming_n": len(streaming_tool),
        "tool_updated_n": len(tool_updated),
        "acp_tool_n": len(tools),
        "assistant_has_marker": outcome.get("assistant_has_marker"),
        "leftover": leftover,
        "dump": str(dump_path),
        "acp": str(acp_path),
    }))
    return 0 if leftover == [] else 1


if __name__ == "__main__":
    sys.exit(main())
