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
import shutil
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
MODEL_POLICY_HELPER = SCRIPT_DIR / "kaola-model-policy.py"
FAST_VARIANT_SUFFIXES = ("-fast", "-priority")
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
PLATFORMS = ("claude-code", "codex", "cursor-cli", "devin", "grok", "kimi-cli", "opencode")
START_WAIT = 20.0
SESSION_PREFIX = "kaola"
# Issue #22: default start sets session/set_config_option configId=mode to each
# platform's measured skip-all value. Omitted platforms have no ACP mode skip
# (Grok: agent always-approve; Cursor/OpenCode: no skip-shaped mode value).
# Devin ACP `bypass` is not the PTY argv `dangerous`.
ACP_SKIP_MODE = {
    "claude-code": "bypassPermissions",
    "codex": "agent-full-access",
    "devin": "bypass",
    "kimi-cli": "yolo",
}


def die(message: str, code: int = 2) -> None:
    print(f"kaola-acp: {message}", file=sys.stderr)
    raise SystemExit(code)


def canonical_dir(path: str) -> str:
    return os.path.realpath(path)


def load_manifest(platform: str) -> dict[str, str]:
    candidates = (SCRIPT_DIR / "platform.yaml", SCRIPT_DIR.parent / "platforms" / f"{platform}.yaml")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        die(f"manifest not found for platform {platform}")
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            die(f"{path}:{number}: expected key: value")
        try:
            parsed = json.loads(value.strip())
        except json.JSONDecodeError:
            die(f"{path}:{number}: values must be JSON strings")
        if not isinstance(parsed, str):
            die(f"{path}:{number}: values must be JSON strings")
        result[key.strip()] = parsed
    if result.get("id") != platform or not result.get("acp_command"):
        die(f"invalid ACP manifest for platform {platform}")
    return result


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


def sock_path_for_directory(directory: Path) -> Path:
    """Short deterministic socket path; AF_UNIX sun_path is ~104 bytes on macOS."""
    digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:24]
    return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"


def sock_path(args: argparse.Namespace, repo: str) -> Path:
    return sock_path_for_directory(record_dir(args, repo))


LIST_SCHEMA = "kaola-acp-list/1"
VIEW_SCHEMA = "kaola-acp-view/1"
VIEW_RUNTIME_CODES = ("holder-lost", "holder-unreachable", "no-session")
HOLDER_STATES = {
    "starting", "ready", "agent_exited", "stopping", "stopped", "error",
}


def probe_socket_ok(path: Path) -> bool:
    if not path.exists():
        return False
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(0.5)
        connection.connect(str(path))
        return True
    except OSError:
        return False
    finally:
        connection.close()


def parse_list_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kaola-acp.py list")
    parser.add_argument("--platform", choices=PLATFORMS)
    parser.add_argument("--repo")
    parser.add_argument("--record-root")
    return parser.parse_args(argv)


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    root = record_root(args)
    repo_filter = resolve_repo(args.repo) if args.repo else None
    rows: list[dict[str, Any]] = []
    if not root.is_dir():
        return {"schema": LIST_SCHEMA, "rows": rows}
    for path in sorted(root.glob("*/*/*/record.json")):
        platform = path.parent.parent.parent.name
        session = path.parent.parent.name
        if platform not in PLATFORMS:
            continue
        if args.platform and platform != args.platform:
            continue
        if not SESSION_PATTERN.match(session):
            continue
        directory = path.parent
        record = read_record(directory)
        if not record:
            continue
        pid = record.get("holder_pid")
        if not pid_alive(pid):
            continue
        repo = record.get("repo")
        if not isinstance(repo, str):
            continue
        if repo_filter is not None and repo != repo_filter:
            continue
        pending = record.get("pending_permissions") or []
        last = record.get("last_prompt") or {}
        mutation = last.get("mutation_status") if isinstance(last, dict) else None
        if not isinstance(mutation, str) or not mutation:
            mutation = "not_started"
        cursor = record.get("event_cursor")
        if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
            cursor = 0
        state = record.get("state")
        if state not in HOLDER_STATES:
            state = str(state) if state is not None else "error"
        rows.append({
            "platform": record.get("platform") or platform,
            "session": record.get("session") or session,
            "repo": repo,
            "state": state,
            "holder_pid": pid,
            "agent_alive": bool(record.get("agent_alive")),
            "event_cursor": cursor,
            "mutation_status": mutation,
            "pending_count": len(pending) if isinstance(pending, list) else 0,
            "socket_ok": probe_socket_ok(sock_path_for_directory(directory)),
            "transport": "acp",
        })
    return {"schema": LIST_SCHEMA, "rows": rows}


def view_error(code: str, message: str) -> dict[str, Any]:
    return {"schema": VIEW_SCHEMA, "error": {"code": code, "message": message}}


def command_view(args: argparse.Namespace, repo: str, directory: Path) -> dict[str, Any]:
    sock = sock_path(args, repo)
    record = read_record(directory)
    if record is None:
        return view_error("no-session", "no ACP session record for this platform/session/repo")
    if not pid_alive(record.get("holder_pid")):
        return view_error("holder-lost", "holder process is not alive")
    if not sock.exists():
        if pid_alive(record.get("holder_pid")):
            return view_error("holder-unreachable", "holder alive but socket path is absent")
        return view_error("holder-lost", "holder process is not alive")
    params: dict[str, Any] = {}
    if args.since is not None:
        params["since"] = args.since
    response = socket_request(sock, "view", params, 15.0)
    err = response.get("error")
    if isinstance(err, dict):
        if not pid_alive(record.get("holder_pid")):
            return view_error("holder-lost", "holder process is not alive")
        code = err.get("code")
        if code in VIEW_RUNTIME_CODES:
            return view_error(str(code), str(err.get("message") or "view failed"))
        return view_error(
            "holder-unreachable",
            str(err.get("message") or "holder socket is unreachable"),
        )
    return response


def follow_error_line(code: str, message: str) -> dict[str, Any]:
    return {"kind": "error", "error": {"code": code, "message": message}}


class FollowTextPrinter:
    """Incremental tty join of message text and tool titles (not a TUI).

    Every snapshot/delta/heartbeat carries the whole ``kaola-acp-view/1``
    projection, so the printer remembers what it already wrote per message
    (keyed by cursor/role/messageId) and per tool, and prints only the new
    suffix or a changed tool status.
    """

    def __init__(self) -> None:
        self.printed: dict[tuple[Any, Any, Any], int] = {}
        self.tools: dict[str, Any] = {}
        self.open_key: tuple[Any, Any, Any] | None = None

    def _end_line(self) -> None:
        if self.open_key is not None:
            sys.stdout.write("\n")
            self.open_key = None

    def feed(self, event: dict[str, Any]) -> None:
        kind = event.get("kind")
        if kind in ("error", "eof"):
            self._end_line()
            print(json.dumps(event, ensure_ascii=False), flush=True)
            return
        if kind not in ("snapshot", "delta", "heartbeat"):
            return
        for message in event.get("messages") or []:
            if not isinstance(message, dict):
                continue
            text = str(message.get("text") or "")
            key = (message.get("cursor"), message.get("role"), message.get("messageId"))
            done = self.printed.get(key, 0)
            if len(text) <= done:
                continue
            if self.open_key != key:
                self._end_line()
                sys.stdout.write(f"{message.get('role') or 'message'}: ")
                self.open_key = key
            sys.stdout.write(text[done:])
            self.printed[key] = len(text)
        for tool in event.get("tools") or []:
            if not isinstance(tool, dict):
                continue
            tool_id = str(tool.get("toolCallId") or "")
            status = tool.get("status")
            if tool_id in self.tools and self.tools[tool_id] == status:
                continue
            self.tools[tool_id] = status
            self._end_line()
            title = tool.get("title") or tool_id
            suffix = f" [{status}]" if status else ""
            sys.stdout.write(f"tool: {title}{suffix}\n")
        sys.stdout.flush()


def emit_follow_line(raw: bytes, printer: FollowTextPrinter | None) -> str | None:
    """Print one holder line; return its ``kind`` when it parses."""
    text = raw.decode("utf-8", "replace")
    try:
        event = json.loads(text)
    except ValueError:
        event = None
    if printer is None or not isinstance(event, dict):
        print(text, flush=True)
    else:
        printer.feed(event)
    return event.get("kind") if isinstance(event, dict) else None


def command_follow(args: argparse.Namespace, repo: str, directory: Path) -> int:
    sock = sock_path(args, repo)
    record = read_record(directory)
    printer = FollowTextPrinter() if getattr(args, "format", "json") == "text" else None

    def emit_error(code: str, message: str) -> int:
        print(json.dumps(follow_error_line(code, message), ensure_ascii=False), flush=True)
        return 0

    if record is None:
        return emit_error("no-session", "no ACP session record for this platform/session/repo")
    if not pid_alive(record.get("holder_pid")):
        return emit_error("holder-lost", "holder process is not alive")
    if not sock.exists():
        if pid_alive(record.get("holder_pid")):
            return emit_error("holder-unreachable", "holder alive but socket path is absent")
        return emit_error("holder-lost", "holder process is not alive")

    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        try:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        except OSError:
            pass
        connection.connect(str(sock))
        params: dict[str, Any] = {}
        if args.since is not None:
            params["since"] = args.since
        payload = json.dumps({
            "op": "follow",
            "request_id": secrets.token_hex(8),
            "params": params,
        }).encode("utf-8") + b"\n"
        connection.sendall(payload)
        buffer = bytearray()
        while True:
            try:
                data = connection.recv(65536)
            except OSError:
                latest = read_record(directory) or record
                if not pid_alive(latest.get("holder_pid")):
                    emit_error("holder-lost", "holder process is not alive")
                return 0
            if not data:
                latest = read_record(directory) or record
                if not pid_alive(latest.get("holder_pid")):
                    emit_error("holder-lost", "holder process is not alive")
                break
            buffer.extend(data)
            while b"\n" in buffer:
                line, _, rest = buffer.partition(b"\n")
                buffer = bytearray(rest)
                if line.strip() and emit_follow_line(line, printer) == "eof":
                    return 0
    except OSError as exc:
        latest = read_record(directory) or record
        if not pid_alive(latest.get("holder_pid")):
            emit_error("holder-lost", "holder process is not alive")
        else:
            emit_error("holder-unreachable", str(exc))
    finally:
        try:
            connection.close()
        except OSError:
            pass
    return 0


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
            "default": args.manifest["default_transport"],
            "alternatives": ["pty"],
            "reason": args.transport_reason,
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
    # A recorded normal shutdown is not an unexpected connection loss. Only
    # status/observe use this terminal receipt; mutations retain their errors.
    ids = [record.get(key) for key in ("holder_pid", "agent_pid", "agent_pgid")]
    if (args.command in ("status", "observe") and record.get("state") == "stopped"
            and all(isinstance(pid, int) and pid > 0 for pid in ids)
            and not any(pid_alive(pid) for pid in ids)):
        members = subprocess.run(
            ["ps", "-axo", "pid=,pgid=,state="], capture_output=True, text=True
        )
        residual = []
        for line in members.stdout.splitlines():
            fields = line.split()
            if (len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit()
                    and int(fields[1]) == record["agent_pgid"]
                    and not fields[2].upper().startswith("Z")):
                residual.append(int(fields[0]))
        if members.returncode == 0 and not residual:
            receipt.update(outcome="stopped", state="stopped", stopped=True,
                           residual_pids=[], record=record)
            return receipt
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


def resolve_selection(args: argparse.Namespace, repo: str) -> dict[str, Any]:
    """Resolve tier/model/effort/Fast through the shared model-policy helper.

    Explicit --model wins over the selected tier preset; explicit --effort
    wins over the preset effort but only attaches to the model it was given
    with.  A resume/continue without tier/model/effort preserves the saved
    native session selection (no Runner model override).
    """
    manifest = args.manifest
    tier = args.tier or "default"
    preserve = bool(args.resume or args.use_continue) and not (
        args.model or args.effort or args.tier
    )
    if args.model:
        source = "user"
        requested = args.model
        candidate = args.model
        effort = args.effort or ""
    elif preserve:
        source = "resume-preserved"
        requested = "native saved session selection"
        candidate = ""
        effort = ""
    else:
        prefix = "upgrade" if tier == "upgrade" else "default"
        source = f"runner-{prefix}"
        requested = manifest.get(f"{prefix}_model_name") or ""
        candidate = manifest.get(f"{prefix}_model_id") or ""
        effort = args.effort or manifest.get(f"{prefix}_model_effort") or ""
    runtime_bin = (
        os.environ.get(manifest.get("binary_env") or "")
        or shutil.which(manifest.get("binary_name") or "")
        or manifest.get("binary_name")
        or ""
    )
    mechanism = {"config": "config", "model-variant": "model-suffix"}.get(
        manifest.get("fast_support") or "", "none"
    )
    policy: dict[str, Any] | None = None
    if MODEL_POLICY_HELPER.is_file():
        try:
            out = subprocess.run(
                [
                    sys.executable, str(MODEL_POLICY_HELPER), "resolve",
                    "--platform", args.platform, "--runtime-bin", runtime_bin,
                    "--repo", repo, "--source", source,
                    "--requested-name", requested, "--candidate-id", candidate,
                    "--effort", effort,
                    "--fast", "true" if args.fast == "on" else "false",
                    "--tier", tier, "--fast-mechanism", mechanism,
                ],
                capture_output=True, text=True, timeout=45,
            )
            if out.returncode == 0:
                policy = json.loads(out.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            policy = None
    if not isinstance(policy, dict):
        policy = {
            "requested_model_source": source,
            "requested_model_name": requested,
            "requested_tier": tier,
            "requested_fast": args.fast,
            "resolved_runtime_model_id": candidate,
            "resolved_runtime_model_display": None,
            "resolved_parameters": {"effort": effort} if effort else {},
            "resolved_fast": "unknown",
            "model_evidence_provenance": {
                "requested": {"source": source, "name": requested},
                "selection": {"source": source, "tier": tier},
                "resolution": {
                    "state": "policy-helper-unavailable",
                    "candidate_id": candidate or None,
                    "resolved_id": candidate or None,
                },
            },
        }
    return policy


def merge_policy_evidence(receipt: dict[str, Any], policy: dict[str, Any]) -> None:
    for key in (
        "requested_model_source", "requested_model_name", "requested_tier",
        "requested_fast", "resolved_runtime_model_id",
        "resolved_runtime_model_display", "resolved_parameters", "resolved_fast",
        "actual_runtime_model_id", "actual_parameters", "model_verified",
        "model_mismatch_reason", "model_evidence_provenance",
    ):
        if key in policy:
            receipt[key] = policy[key]
    receipt["model_selection"] = {
        "source": policy.get("requested_model_source"),
        "tier": policy.get("requested_tier"),
        "requested_name": policy.get("requested_model_name"),
        "resolved_model": policy.get("resolved_runtime_model_id") or None,
        "resolved_effort": (policy.get("resolved_parameters") or {}).get("effort"),
        "preserved": policy.get("requested_model_source") == "resume-preserved",
    }


def fast_report(args: argparse.Namespace, policy: dict[str, Any],
                applied_via: str, applied: bool, detail: str | None = None) -> dict[str, Any]:
    provenance_fast = (policy.get("model_evidence_provenance") or {}).get("fast") or {}
    report = {
        "requested": args.fast,
        "support": args.manifest.get("fast_support") or "none",
        "effective": policy.get("resolved_fast") or "unknown",
        "applied": applied,
        "applied_via": applied_via,
    }
    for key in ("conflict", "detail", "model_support"):
        if provenance_fast.get(key) is not None:
            report[key] = provenance_fast[key]
    if detail:
        report["detail"] = detail
    return report


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
    receipt["transport"]["advertised_config_ids"] = probe.pop("config_option_ids", None)
    receipt.update(probe)
    policy = resolve_selection(args, repo)
    merge_policy_evidence(receipt, policy)
    receipt["config_application"] = {
        "applied": False,
        "detail": "preflight is read-only; selection reported but not applied",
    }
    receipt["fast"] = fast_report(args, policy, "none", False)
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
        receipt["mutation_status"] = "not_started"
        receipt["mutation_performed"] = False
    elif state.get("state") != "ready":
        receipt["error"] = {"code": "start-incomplete", "state": state.get("state")}
    else:
        configured = []
        policy = resolve_selection(args, repo)
        merge_policy_evidence(receipt, policy)
        resolved_model = policy.get("resolved_runtime_model_id") or ""
        resolved_effort = (policy.get("resolved_parameters") or {}).get("effort") or ""
        application: dict[str, Any] = {}
        mode_value = args.mode or ACP_SKIP_MODE.get(args.platform)
        # Model first, then effort, then Fast — the ACP config order the
        # upstream adapter expects.
        option_pairs = [
            ("model", resolved_model, "acp_model_config_id"),
            ("effort", resolved_effort, "acp_effort_config_id"),
        ]
        for label, value, key in option_pairs:
            if not value:
                application[label] = {"applied": False, "reason": "no-resolved-value"}
                continue
            config_id = args.manifest.get(key or "")
            if not config_id:
                application[label] = {
                    "applied": False,
                    "reason": "no-advertised-config-option",
                    "manifest_key": key,
                    "value": value,
                }
                continue
            result = socket_request(sock, "set_config_option", {"config_id": config_id, "value": value}, 20.0)
            if result.get("error"):
                # A rejected option is a limitation receipt, not a session
                # failure — the agent stays usable on its own selection.
                application[label] = {"applied": False, "config_id": config_id,
                                      "value": value, "error": result["error"]}
                continue
            configured.append(result)
            application[label] = {"applied": True, "config_id": config_id, "value": value}
        # Fast rides the native config option when the agent advertises one;
        # model-variant platforms carry it in the resolved model ID instead.
        fast_id = args.manifest.get("acp_fast_config_id") or ""
        if "error" not in receipt:
            if fast_id:
                result = socket_request(
                    sock, "set_config_option",
                    {"config_id": fast_id, "value": args.fast}, 20.0,
                )
                if result.get("error"):
                    application["fast"] = {"applied": False, "config_id": fast_id,
                                           "value": args.fast, "error": result["error"]}
                    receipt["fast"] = fast_report(
                        args, policy, "acp-config", False,
                        detail="fast config option rejected",
                    )
                else:
                    configured.append(result)
                    application["fast"] = {"applied": True, "config_id": fast_id,
                                           "value": args.fast}
                    receipt["fast"] = fast_report(args, policy, "acp-config", True)
            else:
                via = "model-id" if any(
                    resolved_model.endswith(suffix) for suffix in FAST_VARIANT_SUFFIXES
                ) else "none"
                application["fast"] = {"applied": False, "reason": "no-advertised-config-option"}
                receipt["fast"] = fast_report(args, policy, via, via == "model-id")
        if mode_value and "error" not in receipt:
            if args.platform in ACP_SKIP_MODE:
                config_id = "mode"
            else:
                config_id = ""
            if not config_id:
                application["mode"] = {"applied": False, "reason": "no-advertised-config-option"}
                if args.mode:
                    receipt["error"] = {"code": "config-option-unavailable", "manifest_key": None}
            else:
                result = socket_request(sock, "set_config_option", {"config_id": config_id, "value": mode_value}, 20.0)
                if result.get("error"):
                    application["mode"] = {"applied": False, "config_id": config_id,
                                           "value": mode_value, "error": result["error"]}
                    receipt["error"] = result["error"]
                else:
                    configured.append(result)
                    application["mode"] = {"applied": True, "config_id": config_id,
                                           "value": mode_value}
        if configured:
            receipt["configured_options"] = configured
        receipt["config_application"] = application
        receipt.setdefault("fast", fast_report(args, policy, "none", False))
    return receipt


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        payload = command_list(parse_list_args(sys.argv[2:]))
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0

    parser = argparse.ArgumentParser(prog="kaola-acp.py")
    parser.add_argument("platform", choices=PLATFORMS)
    parser.add_argument("command", choices=[
        "preflight", "start", "send", "wait", "observe", "capture",
        "permit", "key", "answer", "cancel", "stop", "status", "view",
        "follow",
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
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--inline", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--tier", choices=("default", "upgrade"))
    parser.add_argument("--fast", choices=("on", "off"), default="off")
    parser.add_argument("--mode")
    parser.add_argument("--transport-reason", choices=("manifest-default", "caller-override"), default="manifest-default")
    args = parser.parse_args()

    args.manifest = load_manifest(args.platform)
    repo = resolve_repo(args.repo)
    if args.command != "preflight":
        if not args.session or not SESSION_PATTERN.match(args.session):
            die("invalid or missing --session name")
    args.agent_command = (
        args.agent_command
        or os.environ.get("KAOLA_ACP_COMMAND")
        or args.manifest["acp_command"]
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
    if args.command == "view":
        if directory is None:
            die("invalid or missing --session name")
        receipt = command_view(args, repo, directory)
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "follow":
        if directory is None:
            die("invalid or missing --session name")
        return command_follow(args, repo, directory)

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
