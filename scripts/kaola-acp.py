#!/usr/bin/env python3
"""Runner v2 ACP transport CLI for the PoC (issue #15).

Thin socket client: every command talks to the per-session holder process
(``kaola-acp-holder.py``) over ``holder.sock`` with newline-delimited JSON.
Receipts are ``schema_version: 3`` JSON on stdout; fact errors ride inside the
receipt as ``error: {code, message}`` while usage errors exit non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
HOLDER = SCRIPT_DIR / "kaola-acp-holder.py"
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
DEFAULT_COMMANDS = {
    "grok": "grok agent stdio",
    "kimi-cli": "kimi acp",
}
START_WAIT = 20.0
SESSION_PREFIX = "kaola"


def die(message: str, code: int = 2) -> None:
    print(f"kaola-acp: {message}", file=sys.stderr)
    raise SystemExit(code)


def canonical_dir(path: str) -> str:
    return os.path.realpath(path)


def resolve_repo(raw: str) -> str:
    if not raw or not raw.startswith("/") or not os.path.isdir(raw):
        die("--repo must be an existing absolute path")
    repo = canonical_dir(raw)
    result = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        die(f"not a Git repository: {repo}")
    git_root = canonical_dir(result.stdout.strip())
    if git_root != repo:
        die(f"--repo must name the Git root: {git_root}")
    return repo


def record_root(args: argparse.Namespace) -> Path:
    if args.record_root:
        return Path(args.record_root)
    env = os.environ.get("KAOLA_ACP_RECORD_ROOT")
    if env:
        return Path(env)
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(base) / f"kaola-{os.getuid()}"


def record_dir(args: argparse.Namespace, repo: str) -> Path:
    digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    return record_root(args) / args.platform / args.session / digest


def sock_path(args: argparse.Namespace, repo: str) -> Path:
    """Short deterministic socket path; AF_UNIX sun_path is ~104 bytes on macOS."""
    digest = hashlib.sha256(str(record_dir(args, repo)).encode("utf-8")).hexdigest()[:24]
    return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"


def read_record(directory: Path) -> dict[str, Any] | None:
    path = directory / "record.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def socket_request(sock_path: Path, op: str, params: dict[str, Any],
                   timeout: float | None) -> dict[str, Any]:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect(str(sock_path))
        payload = json.dumps({"op": op, "request_id": secrets.token_hex(8),
                              "params": params}).encode("utf-8") + b"\n"
        connection.sendall(payload)
        buffer = bytearray()
        while True:
            data = connection.recv(65536)
            if not data:
                break
            buffer.extend(data)
            if b"\n" in buffer:
                line, _, _ = buffer.partition(b"\n")
                return json.loads(line.decode("utf-8"))
        if buffer:
            return json.loads(buffer.decode("utf-8"))
        return {"error": {"code": "holder-closed", "message": "holder closed the connection"}}
    except (OSError, ValueError) as exc:
        return {"error": {"code": "holder-unreachable", "message": str(exc)}}
    finally:
        connection.close()


def git_facts(repo: str) -> dict[str, Any]:
    branch = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    dirty = subprocess.run(
        ["git", "-C", repo, "status", "--porcelain"],
        capture_output=True, text=True,
    )
    return {
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
    }


def base_receipt(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    return {
        "schema_version": 3,
        "platform": args.platform,
        "session": args.session,
        "repo": repo,
        "transport": {
            "selected": "acp",
            "default": "acp",
            "alternatives": ["pty"],
            "reason": "poc-default",
        },
        "git": git_facts(repo),
    }


def holder_lost_receipt(args: argparse.Namespace, repo: str,
                        record: dict[str, Any]) -> dict[str, Any]:
    receipt = base_receipt(args, repo)
    receipt["outcome"] = "holder_lost"
    last = record.get("last_prompt") or {}
    if last.get("written_at") and not last.get("stop_reason"):
        receipt["mutation_status"] = "unknown"
        receipt["mutation_performed"] = None
    else:
        receipt["mutation_status"] = last.get("mutation_status")
        receipt["mutation_performed"] = (
            None if receipt["mutation_status"] == "unknown"
            else receipt["mutation_status"] in ("completed", "accepted", "in_progress")
        )
    receipt["error"] = {
        "code": "holder-lost",
        "message": "holder process is not alive",
        "holder_pid": record.get("holder_pid"),
        "agent_pgid": record.get("agent_pgid"),
    }
    receipt["state"] = record.get("state")
    receipt["record"] = record
    return receipt


def op_or_holder_lost(args: argparse.Namespace, repo: str, directory: Path,
                      op: str, params: dict[str, Any],
                      timeout: float | None) -> dict[str, Any]:
    sock = sock_path(args, repo)
    record = read_record(directory)
    if record and not pid_alive(record.get("holder_pid")):
        if op == "stop":
            return force_kill_from_record(args, repo, record)
        return holder_lost_receipt(args, repo, record)
    if not sock.exists():
        if record is None:
            receipt = base_receipt(args, repo)
            receipt["error"] = {"code": "no-session",
                                "message": "no ACP session record for this platform/session/repo"}
            return receipt
        if pid_alive(record.get("holder_pid")):
            receipt = base_receipt(args, repo)
            receipt["error"] = {"code": "holder-socket-missing",
                                "message": "holder alive but socket path is absent",
                                "holder_pid": record.get("holder_pid")}
            receipt["record"] = record
            return receipt
        return holder_lost_receipt(args, repo, record)
    response = socket_request(sock, op, params, timeout)
    if response.get("error", {}).get("code") == "holder-unreachable":
        if record and not pid_alive(record.get("holder_pid")):
            if op == "stop":
                return force_kill_from_record(args, repo, record)
            return holder_lost_receipt(args, repo, record)
    receipt = base_receipt(args, repo)
    receipt.update(response)
    return receipt


def force_kill_from_record(args: argparse.Namespace, repo: str,
                           record: dict[str, Any]) -> dict[str, Any]:
    """stop --force path when the holder is already gone."""
    pgid = record.get("agent_pgid")
    receipt = base_receipt(args, repo)
    killed: list[int] = []
    if isinstance(pgid, int) and pgid > 0:
        members = subprocess.run(
            ["ps", "-axo", "pid=,pgid=,state="], capture_output=True, text=True
        )
        for line in members.stdout.splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[0].isdigit() and int(fields[1]) == pgid:
                if fields[2].upper().startswith("Z"):
                    continue
                pid = int(fields[0])
                try:
                    os.kill(pid, signal.SIGKILL)
                    killed.append(pid)
                except (ProcessLookupError, PermissionError):
                    pass
    leftover = []
    if isinstance(pgid, int) and pgid > 0:
        time.sleep(0.1)
        members = subprocess.run(
            ["ps", "-axo", "pid=,pgid=,state="], capture_output=True, text=True
        )
        for line in members.stdout.splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[0].isdigit() and int(fields[1]) == pgid:
                if not fields[2].upper().startswith("Z"):
                    leftover.append(int(fields[0]))
    receipt.update({
        "stopped": True,
        "holder_lost": True,
        "force_killed_pids": killed,
        "residual_pids": leftover,
        "mutation_status": "unknown"
        if (record.get("last_prompt") or {}).get("written_at")
        and not (record.get("last_prompt") or {}).get("stop_reason")
        else (record.get("last_prompt") or {}).get("mutation_status"),
    })
    sock = sock_path(args, repo)
    try:
        sock.unlink()
    except OSError:
        pass
    return receipt


def command_preflight(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    receipt = base_receipt(args, repo)
    result = subprocess.run(
        [sys.executable, str(HOLDER), "--probe", "--repo", repo,
         "--platform", args.platform, "--command", args.agent_command],
        capture_output=True, text=True, timeout=60,
    )
    try:
        probe = json.loads(result.stdout)
    except ValueError:
        receipt["error"] = {"code": "probe-failed", "message": result.stderr[-400:]}
        return receipt
    probe.pop("probe", None)
    receipt["transport"]["capabilities"] = probe.pop("capabilities", None)
    receipt["transport"]["protocol_version"] = probe.pop("protocol_version", None)
    receipt["transport"]["agent_info"] = probe.pop("agent_info", None)
    receipt["login_required"] = probe.pop("login_required", None)
    receipt["transport"]["auth_methods"] = probe.pop("auth_methods", [])
    receipt.update(probe)
    return receipt


def command_start(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    receipt = base_receipt(args, repo)
    directory = record_dir(args, repo)
    tmux = subprocess.run(
        ["tmux", "has-session", "-t", f"={args.session}"], capture_output=True
    )
    if tmux.returncode == 0:
        receipt["error"] = {
            "code": "transport-mismatch",
            "other_transport": "pty",
            "message": "a pty session with this name exists",
        }
        return receipt
    record = read_record(directory)
    if record:
        if pid_alive(record.get("holder_pid")):
            receipt["error"] = {"code": "session-exists",
                                "message": "a live ACP holder already owns this session",
                                "holder_pid": record.get("holder_pid"),
                                "acp_session_id": record.get("acp_session_id")}
            return receipt
        if pid_alive(record.get("agent_pgid")) or pid_alive(record.get("agent_pid")):
            receipt.update(holder_lost_receipt(args, repo, record))
            return receipt
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "holder.out.log"
    holder_argv = [
        sys.executable, str(HOLDER),
        "--record-dir", str(directory),
        "--socket", str(sock_path(args, repo)),
        "--repo", repo,
        "--platform", args.platform,
        "--session", args.session,
        "--command", args.agent_command,
    ]
    if args.resume:
        holder_argv += ["--resume", args.resume]
    if args.use_continue:
        holder_argv += ["--continue"]
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            holder_argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True,
        )
    sock = sock_path(args, repo)
    deadline = time.monotonic() + START_WAIT
    state: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        if sock.exists():
            state = socket_request(sock, "state", {}, 5.0)
            if "error" not in state or state.get("error", {}).get("code") != "holder-unreachable":
                if state.get("state") in ("ready", "error", "agent_exited"):
                    break
        if not pid_alive(proc.pid):
            break
        time.sleep(0.1)
    if state is None:
        record = read_record(directory) or {}
        receipt["error"] = {"code": "holder-start-timeout",
                            "message": "holder did not report within the start window",
                            "holder_pid": proc.pid}
        return receipt
    receipt.update({
        "holder_pid": state.get("holder_pid", proc.pid),
        "agent_pid": state.get("agent_pid"),
        "acp_session_id": state.get("acp_session_id"),
        "state": state.get("state"),
    })
    receipt["transport"]["protocol_version"] = state.get("protocol_version")
    receipt["transport"]["agent_info"] = state.get("agent_info")
    receipt["transport"]["capabilities"] = state.get("capabilities")
    if state.get("fatal_error"):
        receipt["error"] = state["fatal_error"]
    elif state.get("state") != "ready":
        receipt["error"] = {"code": "start-incomplete", "state": state.get("state")}
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(prog="kaola-acp.py")
    parser.add_argument("platform", choices=sorted(DEFAULT_COMMANDS) + ["mock"])
    parser.add_argument("command", choices=[
        "preflight", "start", "send", "wait", "observe", "capture",
        "permit", "key", "answer", "cancel", "stop", "status",
    ])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--session")
    parser.add_argument("--command", dest="agent_command")
    parser.add_argument("--record-root")
    parser.add_argument("--resume")
    parser.add_argument("--continue", dest="use_continue", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--wait", dest="wait", action="store_true", default=True)
    parser.add_argument("--no-wait", dest="wait", action="store_false")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--max-final-chars", type=int, default=4000)
    parser.add_argument("--request-id")
    parser.add_argument("--option")
    parser.add_argument("--key")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--lines", type=int)
    parser.add_argument("--tools", action="store_true")
    parser.add_argument("--since", type=int)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--inline", action="store_true")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    if args.command != "preflight":
        if not args.session or not SESSION_PATTERN.match(args.session):
            die("invalid or missing --session name")
    args.agent_command = (
        args.agent_command
        or os.environ.get("KAOLA_ACP_COMMAND")
        or DEFAULT_COMMANDS.get(args.platform)
    )
    if not args.agent_command:
        die(f"no ACP command for platform {args.platform} (use --command)")

    directory = record_dir(args, repo) if args.session else None

    if args.command == "preflight":
        receipt = command_preflight(args, repo)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "start":
        receipt = command_start(args, repo)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0

    timeout = args.timeout
    sock_timeout = (timeout + 30.0) if timeout else None

    if args.command == "send":
        text = args.text
        if args.stdin:
            text = sys.stdin.read()
        if not text:
            die("send requires --text or --stdin")
        receipt = op_or_holder_lost(
            args, repo, directory, "prompt",
            {"text": text, "wait": args.wait, "timeout": timeout,
             "max_final_chars": args.max_final_chars},
            sock_timeout,
        )
    elif args.command == "wait":
        receipt = op_or_holder_lost(
            args, repo, directory, "wait", {"timeout": timeout}, sock_timeout
        )
    elif args.command in ("observe", "status"):
        receipt = op_or_holder_lost(args, repo, directory, "state", {}, 10.0)
        record = read_record(directory)
        if record:
            receipt.setdefault("record", record)
    elif args.command == "capture":
        receipt = op_or_holder_lost(
            args, repo, directory, "capture",
            {"tools": args.tools, "since": args.since, "full": args.full,
             "lines": args.lines, "inline": args.inline},
            15.0,
        )
    elif args.command == "permit":
        receipt = op_or_holder_lost(
            args, repo, directory, "permit",
            {"request_id": args.request_id, "option": args.option}, 10.0,
        )
    elif args.command == "cancel":
        receipt = op_or_holder_lost(
            args, repo, directory, "cancel", {"timeout": timeout}, sock_timeout
        )
    elif args.command == "key":
        if args.key != "escape":
            receipt = base_receipt(args, repo)
            receipt["error"] = {"code": "key-unsupported",
                                "message": "acp transport supports only escape→cancel"}
        else:
            receipt = op_or_holder_lost(
                args, repo, directory, "cancel", {"timeout": timeout}, sock_timeout
            )
    elif args.command == "answer":
        receipt = base_receipt(args, repo)
        receipt["error"] = {"code": "answer-unsupported",
                            "message": "use send; --decision-id maps to permit --request-id"}
    elif args.command == "stop":
        receipt = op_or_holder_lost(
            args, repo, directory, "stop", {"force": args.force}, 30.0
        )
    else:
        die(f"unhandled command {args.command}")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
