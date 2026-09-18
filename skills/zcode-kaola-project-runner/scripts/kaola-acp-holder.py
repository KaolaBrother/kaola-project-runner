#!/usr/bin/env python3
"""Per-session ACP connection holder for the Runner v2 PoC (design §3.3/§7).

Spawned once per session by ``kaola-acp.py start``. Owns the agent's stdio,
runs the NDJSON JSON-RPC loop, keeps ``record.json`` / ``events.jsonl`` /
``stderr.log`` in the session record directory, and serves local NDJSON
requests on ``holder.sock``. Pure Python 3, macOS-compatible (no /proc, no
setsid binary).
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import hashlib
import json
import os
import queue
import secrets
import select
import shlex
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
IDLE_EXIT_SECONDS = 600
STDERR_RING = 64 * 1024
EVENT_LOG_MAX = 10 * 1024 * 1024
EVENT_LOG_KEEP = 3
CANCEL_GRACE = 5.0
# Issue #65: a native steering call answers inside the running turn; it never
# waits for the turn itself, so this bounds only the extension round trip.
STEER_TIMEOUT = 30.0
EXIT_GRACE = 5.0
TERM_GRACE = 3.0
SENSITIVE_KEYS = ("_API_KEY", "TOKEN", "Authorization")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_id(value: Any) -> str:
    return str(value)


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


PS_ENV = {**os.environ, "LC_ALL": "C"}


def process_table() -> list[tuple[int, int, int, str]]:
    """Live (non-zombie) processes as (pid, ppid, pgid, start time). ``ps``
    renders ``lstart`` in the caller's locale on macOS; pin C so the text is
    the ctime layout ``start_epoch`` parses and stays comparable between the
    holder that recorded it and a later CLI process under another locale."""
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,pgid=,state=,lstart="], capture_output=True, text=True,
        env=PS_ENV,
    )
    rows: list[tuple[int, int, int, str]] = []
    for line in result.stdout.splitlines():
        fields = line.split(None, 4)
        if len(fields) != 5 or not all(field.isdigit() for field in fields[:3]):
            continue
        if fields[3].upper().startswith("Z"):
            continue
        rows.append((int(fields[0]), int(fields[1]), int(fields[2]), fields[4].strip()))
    return rows


def child_groups(root_pid: int, root_pgid: int,
                 table: list[tuple[int, int, int, str]] | None = None) -> dict[int, dict[int, str]]:
    """Process groups that descendants of ``root_pid`` run in, other than
    ``root_pgid`` itself, as ``pgid -> {member pid: start time}``. An ACP
    agent that spawns its CLI detached (own process group) leaves it outside
    the agent's group, so the group signal and the residue sweep would never
    see it. The member identities let a later sweep tell the group from an
    unrelated one that reused the same id."""
    children: dict[int, list[tuple[int, int, str]]] = {}
    for pid, ppid, pgid, started in (table if table is not None else process_table()):
        children.setdefault(ppid, []).append((pid, pgid, started))
    found: dict[int, dict[int, str]] = {}
    seen: set[int] = set()
    stack = [root_pid]
    while stack:
        parent = stack.pop()
        for pid, pgid, started in children.get(parent, []):
            if pid in seen:
                continue
            seen.add(pid)
            stack.append(pid)
            if pgid != root_pgid:
                found.setdefault(pgid, {})[pid] = started
    return found


CHILD_RECORD_NAME = "children.jsonl"

# Issue #62 phase 2: the event-driven heartbeat carrier for a ZCode Host. A
# worker holder armed with KAOLA_ACP_HEARTBEAT_HOST (plus the CLI-resolved
# host socket) notifies the ZCode Host holder from its existing agent-exit
# and turn-end paths; the host holder stages events in one bounded in-memory
# list, records stage/delivery/confirmation in its own event log (the only
# persistence: no new store), and delivers one ordinary ``session/prompt``
# through the normal admission path - never a raw send, never a second stdin
# writer, never a periodic scheduler. Other hosts are untouched: the carrier
# op exists only for platform zcode.
HEARTBEAT_HOST_ENV = "KAOLA_ACP_HEARTBEAT_HOST"
HEARTBEAT_HOST_SOCKET_ENV = "KAOLA_ACP_HEARTBEAT_HOST_SOCKET"
HEARTBEAT_EVENT_CAP = 32
HEARTBEAT_NOTIFY_TIMEOUT = 5.0
HEARTBEAT_NOTIFY_GRACE = 6.0
WORKER_EVENT_SCHEMA = "kaola-worker-event/1"
WORKER_EVENT_KINDS = ("terminated", "idle")


def parse_heartbeat_host() -> dict[str, str] | None:
    """The armed carrier target, or None. The CLI already validated it and
    died on anything invalid; this re-checks the shape so a hand-spawned
    holder never carries a malformed target (disabled loudly, never fatal)."""
    raw = os.environ.get(HEARTBEAT_HOST_ENV) or ""
    if not raw:
        return None
    socket_path = os.environ.get(HEARTBEAT_HOST_SOCKET_ENV) or ""
    try:
        target = json.loads(raw)
    except ValueError:
        target = None
    if (not isinstance(target, dict) or target.get("platform") != "zcode"
            or not isinstance(target.get("session"), str) or not target["session"]
            or not isinstance(target.get("repo"), str) or not target["repo"]
            or not socket_path or not os.path.isabs(socket_path)):
        sys.stderr.write(f"[kaola-acp-holder] invalid {HEARTBEAT_HOST_ENV}: "
                         "heartbeat carrier disabled\n")
        return None
    return {"platform": "zcode", "session": target["session"],
            "repo": target["repo"], "socket": socket_path}
# ``ps lstart`` is truncated to the second and the agent records ``Date.now()``
# only after ``spawn`` returned, so a genuine child's start time is at or
# before its recorded time, by under a second plus the spawn latency. The
# window is a reuse guard, not a clock: matching a different process would
# need this pid to be freed and handed to a new process-group leader inside
# it, which sequential pid allocation cannot do in seconds. A process that
# started after the record (beyond one second of clock slack) is never the
# recorded child.
SPAWN_RECORD_TOLERANCE = 5.0
SPAWN_RECORD_SLACK = 1.0


def spawn_time_matches(started: float, spawned_ms: float) -> bool:
    """Whether a live start time (epoch seconds, second granularity) can be
    the child recorded at ``spawned_ms``."""
    delta = spawned_ms / 1000.0 - started
    return -SPAWN_RECORD_SLACK <= delta <= SPAWN_RECORD_TOLERANCE


def start_epoch(started: str) -> float | None:
    """``ps lstart`` text (ctime layout, second granularity) as epoch seconds."""
    try:
        return time.mktime(time.strptime(started, "%a %b %d %H:%M:%S %Y"))
    except ValueError:
        return None


def live_spawn_entries(path: Path, table: list[tuple[int, int, int, str]] | None = None
                       ) -> list[tuple[dict[str, Any], str]]:
    """Entries of the agent's spawn record (`KAOLA_ACP_CHILD_RECORD`, one JSON
    line per child: pid, pgid, spawned_at ms) whose identity still holds:
    that pid is alive in that group with a start time at or before the
    recorded spawn and within SPAWN_RECORD_TOLERANCE of it, so a reused pid
    is ignored.
    Each is returned with the live start time. This is what still identifies
    a child whose agent died before forwarding any output about it."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    by_pid = {pid: (pgid, started) for pid, _, pgid, started in (table or process_table())}
    live_entries: list[tuple[dict[str, Any], str]] = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        pid, pgid, spawned = entry.get("pid"), entry.get("pgid"), entry.get("spawned_at")
        if not (isinstance(pid, int) and isinstance(pgid, int) and isinstance(spawned, (int, float))):
            continue
        live = by_pid.get(pid)
        if live is None or live[0] != pgid:
            continue
        started = start_epoch(live[1])
        if started is None or not spawn_time_matches(started, spawned):
            continue
        live_entries.append((entry, live[1]))
    return live_entries


def spawn_recorded_groups(path: Path, table: list[tuple[int, int, int, str]] | None = None
                          ) -> dict[int, dict[int, str]]:
    """Child groups from the spawn record whose identity still holds, as
    ``pgid -> {member pid: start time}`` (see ``live_spawn_entries``)."""
    found: dict[int, dict[int, str]] = {}
    for entry, started in live_spawn_entries(path, table):
        found.setdefault(entry["pgid"], {})[entry["pid"]] = started
    return found


def compact_spawn_record(path: Path) -> None:
    """Rewrite the spawn record with only the entries whose identity still
    holds. Run before a new agent is spawned into this record directory: the
    file is append-only across agent instances, so this bounds it and leaves a
    still-live child of an earlier instance identifiable while dropping every
    entry that could only ever match a reused pid."""
    if not path.exists():
        return
    kept = [json.dumps(entry) for entry, _ in live_spawn_entries(path)]
    try:
        path.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
    except OSError:
        pass


def live_child_groups(groups: dict[int, dict[int, str]]) -> dict[int, list[int]]:
    """Recorded child groups whose identity still holds (a recorded member
    is alive with its recorded start time in that group), with their
    current live members."""
    table = process_table()
    by_pid = {pid: (pgid, started) for pid, _, pgid, started in table}
    live: dict[int, list[int]] = {}
    for pgid, members in groups.items():
        if any(by_pid.get(pid) == (pgid, started) for pid, started in members.items()):
            live[pgid] = [pid for pid, _, group, _ in table if group == pgid]
    return live


def group_members(pgid: int) -> list[int]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid=,state="], capture_output=True, text=True
    )
    members = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0].isdigit() and int(fields[1]) == pgid:
            if fields[2].upper().startswith("Z"):
                continue
            members.append(int(fields[0]))
    return members


def scrub(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if any(marker in str(key) for marker in SENSITIVE_KEYS):
                out[key] = "<redacted>"
            else:
                out[key] = scrub(item)
        return out
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


def capability_supported(container: dict, key: str) -> bool:
    """ACP capability presence means support: a present object (even ``{}``) or
    ``true`` is supported; absent, ``null``, or ``false`` is not."""
    value = container.get(key)
    return value is not None and value is not False


def rfc3339_instant(value: Any) -> float | None:
    """Parse an RFC3339 timestamp into a POSIX instant.

    Returns ``None`` when the value is absent, malformed, or carries no
    numeric offset — a naive timestamp is not an orderable instant.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.timestamp()


def latest_session(sessions: list[dict]) -> tuple[dict | None, list[dict]]:
    """Pick the eligible session with the newest ``updatedAt`` instant.

    Identical ``sessionId`` entries observed across pages collapse to one
    identity before selection; a repeated identity never creates ambiguity.
    A distinct eligible candidate with a missing or invalid ``updatedAt``
    makes the latest identity unknowable. Returns ``(entry, [])`` on a
    unique winner, ``(None, candidates)`` when indeterminate.
    """
    by_id: dict[str, dict] = {}
    for entry in sessions:
        if not isinstance(entry, dict):
            continue
        session_id = entry.get("sessionId")
        if not session_id:
            continue
        previous = by_id.get(session_id)
        if previous is None:
            by_id[session_id] = entry
            continue
        new_instant = rfc3339_instant(entry.get("updatedAt"))
        old_instant = rfc3339_instant(previous.get("updatedAt"))
        if new_instant is not None and (old_instant is None or new_instant > old_instant):
            by_id[session_id] = entry
    candidates = list(by_id.values())
    if not candidates:
        return None, []
    dated = [(rfc3339_instant(entry.get("updatedAt")), entry) for entry in candidates]
    if any(instant is None for instant, _entry in dated):
        return None, candidates
    best = max(instant for instant, _entry in dated)
    tied = [entry for instant, entry in dated if instant == best]
    if len(tied) != 1:
        return None, tied
    return tied[0], []


class EventLog:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.cursor = 0
        self.oldest: int | None = None
        self._restore_cursor()

    def _rotated_paths(self) -> list[Path]:
        paths = []
        for index in range(EVENT_LOG_KEEP, 0, -1):
            rotated = self.path.with_suffix(f".jsonl.{index}")
            if rotated.exists():
                paths.append(rotated)
        if self.path.exists():
            paths.append(self.path)
        return paths

    def _iter_entries(self):
        for path in self._rotated_paths():
            try:
                with open(path, encoding="utf-8") as handle:
                    for line in handle:
                        try:
                            entry = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(entry, dict):
                            yield entry
            except OSError:
                continue

    def _restore_cursor(self) -> None:
        """One scan of live + rotated files; max seeds cursor, min seeds oldest."""
        maximum = 0
        oldest: int | None = None
        for entry in self._iter_entries():
            cursor = entry.get("cursor")
            if isinstance(cursor, int) and not isinstance(cursor, bool):
                if cursor > maximum:
                    maximum = cursor
                if oldest is None or cursor < oldest:
                    oldest = cursor
        self.cursor = maximum
        self.oldest = oldest

    def oldest_cursor(self) -> int | None:
        """Cached; updated on append and rotation, never a per-call file scan."""
        return self.oldest

    def append(self, event: dict[str, Any]) -> int:
        with self.lock:
            self.cursor += 1
            if self.oldest is None:
                self.oldest = self.cursor
            entry = {"cursor": self.cursor, "ts": round(time.time(), 3), **scrub(event)}
            line = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            try:
                if self.path.exists() and self.path.stat().st_size > EVENT_LOG_MAX:
                    self._rotate()
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(line)
            except OSError:
                pass
            return self.cursor

    def _rotate(self) -> None:
        for index in range(EVENT_LOG_KEEP - 1, 0, -1):
            older = self.path.with_suffix(f".jsonl.{index}")
            newer = self.path.with_suffix(f".jsonl.{index + 1}")
            if older.exists():
                older.replace(newer)
        if self.path.exists():
            self.path.replace(self.path.with_suffix(".jsonl.1"))
        oldest: int | None = None
        for entry in self._iter_entries():
            cursor = entry.get("cursor")
            if isinstance(cursor, int) and not isinstance(cursor, bool):
                if oldest is None or cursor < oldest:
                    oldest = cursor
        self.oldest = oldest

    def read_since(self, cursor: int, limit: int | None) -> list[dict[str, Any]]:
        entries = []
        for entry in self._iter_entries():
            item_cursor = entry.get("cursor", 0)
            if isinstance(item_cursor, int) and not isinstance(item_cursor, bool) and item_cursor > cursor:
                entries.append(entry)
        entries.sort(key=lambda item: item.get("cursor", 0))
        if limit:
            return entries[:limit]
        return entries


class StderrPump:
    def __init__(self, stream, log_path: Path):
        self.stream = stream
        self.log_path = log_path
        self.ring = bytearray()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        try:
            while True:
                data = self.stream.read(65536)
                if not data:
                    return
                with self.lock:
                    self.ring.extend(data)
                    if len(self.ring) > STDERR_RING:
                        del self.ring[: len(self.ring) - STDERR_RING]
                try:
                    with open(self.log_path, "ab") as handle:
                        handle.write(data)
                except OSError:
                    pass
        except (OSError, ValueError):
            return

    def tail(self, count: int = 20) -> list[str]:
        with self.lock:
            text = bytes(self.ring).decode("utf-8", "replace")
        return text.splitlines()[-count:]


class AgentConnection:
    """Owns the agent process, its reader threads, and JSON-RPC state."""

    def __init__(self, holder: "Holder"):
        self.holder = holder
        self.proc: subprocess.Popen | None = None
        self.next_id = 0
        self.pending_out: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.reader: threading.Thread | None = None
        self.stderr_pump: StderrPump | None = None
        self.exited = threading.Event()
        self.exit_code: int | None = None
        self.exit_signal: int | None = None
        self.malformed_lines = 0
        self.unknown_updates = 0

    def spawn(self, command: str, cwd: str, env: dict[str, str] | None = None) -> None:
        argv = shlex.split(command)
        env = dict(os.environ if env is None else env)
        # Lets an agent that spawns detached children record their identity
        # at spawn so stop can find them even if the agent dies first. The
        # record survives agent instances; keep only entries still identifying
        # a live child before this instance starts appending to it.
        spawn_record = self.holder.record_dir / CHILD_RECORD_NAME
        compact_spawn_record(spawn_record)
        env["KAOLA_ACP_CHILD_RECORD"] = str(spawn_record)
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        self.stderr_pump = StderrPump(self.proc.stderr, self.holder.record_dir / "stderr.log")
        self.stderr_pump.start()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()
        threading.Thread(target=self._wait_loop, daemon=True).start()

    def _wait_loop(self) -> None:
        code = self.proc.wait() if self.proc else -1
        self.exit_code = code if code >= 0 else None
        self.exit_signal = -code if code < 0 else None
        self.exited.set()
        self.holder.on_agent_exit(code)

    def _read_loop(self) -> None:
        stream = self.proc.stdout
        while True:
            try:
                line = stream.readline()
            except (OSError, ValueError):
                break
            if not line:
                break
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            try:
                message = json.loads(text)
            except ValueError:
                self.malformed_lines += 1
                self.holder.events.append(
                    {"kind": "malformed_stdout", "head": text[:120]}
                )
                continue
            if not isinstance(message, dict):
                self.malformed_lines += 1
                continue
            self.holder.on_agent_message(message)

    # -- JSON-RPC out ---------------------------------------------------------

    def send_message(self, message: dict[str, Any]) -> bool:
        if self.proc is None or self.proc.stdin is None or self.exited.is_set():
            return False
        try:
            self.proc.stdin.write(canonical(message) + b"\n")
            self.proc.stdin.flush()
            return True
        except (OSError, ValueError):
            return False

    def send_request(self, method: str, params: dict[str, Any]) -> int:
        with self.lock:
            self.next_id += 1
            request_id = self.next_id
            slot = {"event": threading.Event(), "response": None}
            self.pending_out[normalize_id(request_id)] = slot
        written = self.send_message(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        if not written:
            with self.lock:
                self.pending_out.pop(normalize_id(request_id), None)
            slot["response"] = {"error": {"code": -32000, "message": "write failed"}}
            slot["event"].set()
        return request_id

    def wait_response(self, request_id: int, timeout: float | None) -> dict[str, Any] | None:
        key = normalize_id(request_id)
        with self.lock:
            slot = self.pending_out.get(key)
        if slot is None:
            return None
        slot["event"].wait(timeout)
        with self.lock:
            self.pending_out.pop(key, None)
        return slot["response"]

    def resolve_response(self, message: dict[str, Any]) -> None:
        key = normalize_id(message.get("id"))
        with self.lock:
            slot = self.pending_out.get(key)
        if slot is not None:
            slot["response"] = message
            slot["event"].set()
        else:
            self.holder.events.append({"kind": "orphan_response", "id": message.get("id")})

    def cancel_outbound(self, request_id: Any) -> bool:
        key = normalize_id(request_id)
        with self.lock:
            slot = self.pending_out.get(key)
        if slot is None:
            return False
        slot["response"] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32800, "message": "request cancelled by agent"},
        }
        slot["event"].set()
        return True


KNOWN_UPDATES = {
    "agent_message_chunk",
    "agent_thought_chunk",
    "tool_call",
    "tool_call_update",
    "plan",
    "available_commands_update",
    "current_mode_update",
    "config_option_update",
    "usage_update",
    "user_message_chunk",
}
THINKING_TAIL_CHARS = 8 * 1024
TOOL_VIEW_BYTES = 32 * 1024
VIEW_BYTES = 256 * 1024
TIMELINE_MAX = 200
VIEW_SCHEMA = "kaola-acp-view/1"
FOLLOW_QUEUE_CAP = 256
FOLLOW_HEARTBEAT_SECONDS = 5.0
FOLLOW_SNDBUF = 4096
FOLLOW_DROP_GRACE = 2.0
FOLLOW_WRITE_OPS = frozenset({"prompt", "steer", "permit", "cancel", "stop"})


def _as_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or "")
    if isinstance(value, list):
        return "".join(_as_text(item) for item in value)
    if isinstance(value, str):
        return value
    return ""


def _normalize_content_items(raw: Any) -> list[dict[str, Any]]:
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "text":
            out.append({"type": "text", "text": str(item.get("text") or "")})
        elif kind == "diff":
            old = item.get("oldText")
            out.append({
                "type": "diff",
                "path": str(item.get("path") or ""),
                "oldText": None if old is None else str(old),
                "newText": str(item.get("newText") or ""),
            })
        elif kind == "terminal":
            out.append({
                "type": "terminal",
                "terminalId": str(item.get("terminalId") or ""),
            })
    return out


def _cap_content_items(
    items: list[dict[str, Any]], budget: int
) -> tuple[list[dict[str, Any]], bool]:
    """Keep whole items while they fit ``budget`` bytes; clip the first overflow."""
    out: list[dict[str, Any]] = []
    used = 2  # list brackets; one comma per item after the first
    for item in items:
        size = len(canonical(item)) + (1 if out else 0)
        if used + size <= budget:
            out.append(item)
            used += size
            continue
        key = {"text": "text", "diff": "newText"}.get(item.get("type"))
        if key:
            raw = canonical(str(item.get(key) or ""))[1:-1]
            allow = budget - used - (size - len(raw))
            if allow > 0:
                clipped = dict(item)
                clipped[key] = raw[:allow].decode("utf-8", "ignore")
                out.append(clipped)
        return out, True
    return out, False


def _normalize_locations(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        line = item.get("line")
        if not isinstance(line, int) or isinstance(line, bool):
            line = None
        out.append({"path": "" if path is None else str(path), "line": line})
    return out


class ViewProjection:
    """In-memory compacted human projection; separate from L0 turn state."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.messages: list[dict[str, Any]] = []
        self.thinking_chars = 0
        self.thinking_text = ""
        self.thinking_message_id: str | None = None
        self.tools: dict[str, dict[str, Any]] = {}
        self.tool_order: list[str] = []
        self.plan: dict[str, Any] | None = None
        self.mode: dict[str, Any] | None = None
        self.commands: list[dict[str, Any]] | None = None
        self.usage: dict[str, Any] | None = None
        self.messages_dropped = False
        self._prompt_texts: list[str] = []
        # The last appended message; chunks without messageId append to it
        # until a tool call, a new prompt, or turn end closes it.
        self._open_message: dict[str, Any] | None = None

    def add_user_from_prompt(self, text: str, cursor: int) -> None:
        with self.lock:
            self._prompt_texts.append(text)
            self._open_message = None
            self._add_message_locked("user", text, None, cursor)

    def close_message(self) -> None:
        with self.lock:
            self._open_message = None

    def apply(self, update: dict[str, Any], cursor: int) -> None:
        variant = update.get("sessionUpdate", "unknown")
        with self.lock:
            if variant == "agent_message_chunk":
                message_id = update.get("messageId")
                if message_id is not None:
                    message_id = str(message_id)
                self._add_message_locked(
                    "assistant", _as_text(update.get("content")), message_id, cursor
                )
            elif variant == "user_message_chunk":
                text = _as_text(update.get("content"))
                message_id = update.get("messageId")
                if message_id is not None:
                    message_id = str(message_id)
                if message_id is None and any(
                    text == previous or text in previous or previous in text
                    for previous in self._prompt_texts
                    if previous
                ):
                    return
                self._add_message_locked("user", text, message_id, cursor)
            elif variant == "agent_thought_chunk":
                text = _as_text(update.get("content"))
                self.thinking_chars += len(text)
                self.thinking_text = (self.thinking_text + text)[-THINKING_TAIL_CHARS:]
                message_id = update.get("messageId")
                if message_id is not None:
                    self.thinking_message_id = str(message_id)
            elif variant in ("tool_call", "tool_call_update"):
                self._upsert_tool_locked(update)
            elif variant == "plan":
                entries = []
                for entry in update.get("entries") or []:
                    if not isinstance(entry, dict):
                        continue
                    priority = entry.get("priority")
                    status = entry.get("status")
                    entries.append({
                        "content": str(entry.get("content") or ""),
                        "priority": None if priority is None else str(priority),
                        "status": None if status is None else str(status),
                    })
                self.plan = {"entries": entries}
            elif variant == "current_mode_update":
                available = []
                for item in update.get("availableModes") or []:
                    if not isinstance(item, dict):
                        continue
                    available.append({
                        "id": str(item.get("id") or ""),
                        "name": str(item.get("name") or ""),
                    })
                current = update.get("currentModeId")
                self.mode = {
                    "current": None if current is None else str(current),
                    "available": available,
                }
            elif variant == "available_commands_update":
                commands = []
                raw = update.get("availableCommands")
                if raw is None:
                    raw = update.get("commands")
                for item in raw or []:
                    if not isinstance(item, dict):
                        continue
                    description = item.get("description")
                    commands.append({
                        "name": str(item.get("name") or ""),
                        "description": None if description is None else str(description),
                    })
                self.commands = commands
            elif variant == "usage_update":
                used = update.get("used")
                size = update.get("size")
                try:
                    self.usage = {"used": int(used), "size": int(size)}
                except (TypeError, ValueError):
                    pass

    def _add_message_locked(
        self, role: str, text: str, message_id: str | None, cursor: int
    ) -> None:
        if message_id is not None:
            for message in reversed(self.messages):
                if message["role"] == role and message["messageId"] == message_id:
                    message["text"] += text
                    return
        else:
            open_message = self._open_message
            if (
                open_message is not None
                and self.messages
                and self.messages[-1] is open_message
                and open_message["role"] == role
                and open_message["messageId"] is None
            ):
                open_message["text"] += text
                return
        message = {
            "role": role,
            "text": text,
            "messageId": message_id,
            "cursor": cursor,
        }
        self.messages.append(message)
        self._open_message = message
        if len(self.messages) > TIMELINE_MAX:
            del self.messages[: len(self.messages) - TIMELINE_MAX]
            self.messages_dropped = True

    def _upsert_tool_locked(self, update: dict[str, Any]) -> None:
        tool_id = update.get("toolCallId")
        if not tool_id:
            tool_id = f"anon-{len(self.tool_order)}"
        tool_id = str(tool_id)
        tool = self.tools.get(tool_id)
        if tool is None:
            tool = {
                "toolCallId": tool_id,
                "title": None,
                "kind": None,
                "status": None,
                "locations": [],
                "content": [],
                "truncated": False,
            }
            self.tools[tool_id] = tool
            self.tool_order.append(tool_id)
            self._open_message = None
        for field in ("title", "kind", "status"):
            if update.get(field) is not None:
                tool[field] = update[field]
        if "locations" in update and update.get("locations") is not None:
            tool["locations"] = _normalize_locations(update.get("locations"))
        if "content" in update and update.get("content") is not None:
            tool["content"], tool["truncated"] = _cap_content_items(
                _normalize_content_items(update.get("content")), TOOL_VIEW_BYTES
            )

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy({
                "messages": self.messages,
                "messages_dropped": self.messages_dropped,
                "thinking_chars": self.thinking_chars,
                "thinking_text": self.thinking_text,
                "thinking_message_id": self.thinking_message_id,
                "tools": [self.tools[tid] for tid in self.tool_order],
                "plan": self.plan,
                "mode": self.mode,
                "commands": self.commands,
                "usage": self.usage,
            })


def follow_error_event(code: str, message: str) -> dict[str, Any]:
    return {"kind": "error", "error": {"code": code, "message": message}}


class Follower:
    """Per-connection follow stream: bounded queue, dedicated writer, never agent stdin."""

    def __init__(self, holder: "Holder", connection: socket.socket, since: int | None):
        self.holder = holder
        self.connection = connection
        self.since = since
        self.queue: queue.Queue = queue.Queue(maxsize=FOLLOW_QUEUE_CAP)
        self.closed = threading.Event()
        self.dropped = threading.Event()
        self.offer_lock = threading.Lock()
        self.last_enqueued_cursor: int | None = None
        self.writer = threading.Thread(target=self._write_loop, daemon=True)

    def start(self) -> None:
        self.writer.start()

    def offer_snapshot(self, payload: dict[str, Any]) -> None:
        cursor = payload.get("event_cursor")
        if self.since is not None and isinstance(cursor, int) and cursor < self.since:
            return
        with self.offer_lock:
            if isinstance(cursor, int):
                self.last_enqueued_cursor = cursor
            self._offer_locked({"kind": "snapshot", **payload})

    def offer_delta(self, payload: dict[str, Any]) -> None:
        cursor = payload.get("event_cursor")
        if self.since is not None and isinstance(cursor, int) and cursor < self.since:
            return
        with self.offer_lock:
            if isinstance(cursor, int) and self.last_enqueued_cursor is not None:
                if cursor <= self.last_enqueued_cursor:
                    return
            if self._offer_locked({"kind": "delta", **payload}):
                if isinstance(cursor, int):
                    self.last_enqueued_cursor = cursor

    def offer_heartbeat(self, payload: dict[str, Any]) -> None:
        with self.offer_lock:
            self._offer_locked({"kind": "heartbeat", **payload})

    def offer_eof(self) -> None:
        with self.offer_lock:
            self._offer_locked({"kind": "eof"})

    def offer_error(self, code: str, message: str) -> None:
        with self.offer_lock:
            self._offer_locked(follow_error_event(code, message))

    def _offer_locked(self, event: dict[str, Any]) -> bool:
        if self.closed.is_set() or self.dropped.is_set():
            return False
        try:
            self.queue.put_nowait(event)
            return True
        except queue.Full:
            self._drop_locked()
            return False

    def _drop_locked(self) -> None:
        if self.dropped.is_set():
            return
        self.dropped.set()
        drop = follow_error_event(
            "follow-dropped", "follower queue exceeded 256 lines"
        )
        try:
            self.queue.put_nowait(drop)
        except queue.Full:
            pass

    def _write_loop(self) -> None:
        try:
            while not self.closed.is_set():
                if self.dropped.is_set():
                    self._emit_drop()
                    return
                try:
                    event = self.queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if event is None:
                    if self.dropped.is_set():
                        self._emit_drop()
                    return
                if not self._send(event):
                    if self.dropped.is_set():
                        self._emit_drop()
                    return
                if event.get("kind") == "eof":
                    return
                err = event.get("error")
                if event.get("kind") == "error" and isinstance(err, dict):
                    if err.get("code") == "follow-dropped":
                        return
        finally:
            self.closed.set()
            self.holder.unregister_follower(self)
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _emit_drop(self) -> None:
        payload = canonical(follow_error_event(
            "follow-dropped", "follower queue exceeded 256 lines"
        )) + b"\n"
        offset = 0
        deadline = time.monotonic() + FOLLOW_DROP_GRACE
        while offset < len(payload) and not self.closed.is_set():
            if time.monotonic() > deadline:
                return
            try:
                _, writable, _ = select.select([], [self.connection], [], 0.2)
                if not writable:
                    continue
                sent = self.connection.send(payload[offset:])
                if sent == 0:
                    return
                offset += sent
            except OSError:
                return

    def _send(self, event: dict[str, Any]) -> bool:
        payload = canonical(event) + b"\n"
        offset = 0
        while offset < len(payload):
            if self.closed.is_set() or self.dropped.is_set():
                return False
            try:
                _, writable, _ = select.select([], [self.connection], [], 0.2)
                if not writable:
                    continue
                sent = self.connection.send(payload[offset:])
                if sent == 0:
                    return False
                offset += sent
            except OSError:
                return False
        return True

    def close(self) -> None:
        if self.closed.is_set():
            return
        self.closed.set()
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def parse_init_meta(raw: str) -> dict[str, Any]:
    """Parse the --init-meta JSON object into clientCapabilities._meta entries.

    Some agents negotiate optional protocol surfaces through _meta (Cursor's
    parameterizedModelPicker advertises separate model/effort/fast config
    options instead of fixed variant descriptors).
    """
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


class Holder:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.init_meta = parse_init_meta(getattr(args, "init_meta", "") or "")
        self.record_dir = Path(args.record_dir)
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.events = EventLog(self.record_dir / "events.jsonl")
        self.record_path = self.record_dir / "record.json"
        self.socket_path = Path(args.socket) if args.socket else self.record_dir / "holder.sock"
        self.agent = AgentConnection(self)
        self.listener: socket.socket | None = None
        self.lock = threading.Lock()
        self.turn_cond = threading.Condition()
        self.state = "starting"
        self.stop_requested = False
        self.holder_instance_id = secrets.token_hex(16)
        self.acp_session_id: str | None = None
        self.session_meta: dict[str, Any] = {}
        self.initial_config_options: Any = None
        self.protocol_version: int | None = None
        self.agent_info: dict[str, Any] = {}
        self.capabilities: dict[str, Any] = {}
        self.auth_methods: list[dict[str, Any]] = []
        self.pending_permissions: dict[str, dict[str, Any]] = {}
        # Process groups the agent spawned outside its own group (for example
        # the Claude bridge's detached `claude -p` children), noted while the
        # agent is alive so stop can sweep them even after the agent is gone.
        self.agent_child_groups: dict[int, dict[int, str]] = {}
        self.swept_child_pgids: list[int] = []
        self.projection = ViewProjection()
        self.followers: list[Follower] = []
        self.followers_lock = threading.Lock()
        self.turn: dict[str, Any] = self._empty_turn()
        try:
            previous_record = json.loads(self.record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous_record = {}
        self.last_prompt: dict[str, Any] = previous_record.get("last_prompt") or {}
        self.fatal_error: dict[str, Any] | None = None
        self.record_lock = threading.Lock()
        self.last_activity = time.monotonic()
        self.agent_exited = threading.Event()
        # Event-driven heartbeat carrier (Issue #62 phase 2): this holder's
        # pending worker events when it is a ZCode Host session, or the armed
        # notify target when it is a worker of one.
        self.pending_worker_events: list[dict[str, Any]] = []
        self.worker_events_lock = threading.Lock()
        self.heartbeat_notify_lock = threading.Lock()
        self.heartbeat_host = parse_heartbeat_host()

    # -- record ---------------------------------------------------------------

    def _empty_turn(self) -> dict[str, Any]:
        return {
            "active": False,
            "request_id": None,
            "fingerprint": None,
            "written_at": None,
            "mutation_status": "not_started",
            "stop_reason": None,
            "outcome": None,
            "final_text": "",
            "final_text_truncated": False,
            "thinking_chars": 0,
            "tool_calls": {},
            "tool_order": [],
            "failed_tools": [],
            "started_at": None,
            "cancel_requested": False,
        }

    def write_record(self, **extra: Any) -> None:
        record = {
            "transport": "acp",
            "platform": self.args.platform,
            "session": self.args.session,
            "repo": self.args.repo,
            "holder_pid": os.getpid(),
            "holder_instance_id": self.holder_instance_id,
            "agent_pid": self.agent.proc.pid if self.agent.proc else None,
            "agent_pgid": self.agent.proc.pid if self.agent.proc else None,
            "agent_child_pgids": sorted(self.agent_child_groups),
            "agent_child_groups": {str(pgid): {str(pid): started for pid, started in members.items()}
                                   for pgid, members in sorted(self.agent_child_groups.items())},
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "acp_session_id": self.acp_session_id,
            "session_meta": self.session_meta,
            "initial_config_options": self.initial_config_options,
            "protocol_version": self.protocol_version,
            "agent_info": self.agent_info,
            "capabilities": self.capabilities,
            "state": self.state,
            "pending_permissions": list(self.pending_permissions.values()),
            "last_prompt": self.last_prompt,
            "event_cursor": self.events.cursor,
            "malformed_stdout_lines": self.agent.malformed_lines,
            "fatal_error": self.fatal_error,
            "created_at": getattr(self, "created_at", None),
            "updated_at": round(time.time(), 3),
            **extra,
        }
        with self.record_lock:
            tmp = self.record_path.with_name(f"record.{secrets.token_hex(4)}.tmp")
            tmp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            tmp.replace(self.record_path)

    # -- ACP lifecycle ----------------------------------------------------------

    def _apply_config_options(self, options: Any, source: str) -> bool:
        """Mirror a native ``configOptions`` payload into ``session_meta``.

        Only a well-formed list is usable native evidence; anything else leaves
        the previously attested state untouched so no value is fabricated.
        """
        if not isinstance(options, list):
            return False
        self.session_meta["configOptions"] = options
        self.events.append({
            "kind": "config_options_applied",
            "source": source,
            "option_count": len(options),
        })
        return True

    def initialize_agent(self, resume: str | None = None, use_continue: bool = False,
                         list_supported: bool = False) -> dict[str, Any]:
        command = self.args.command
        try:
            self.agent.spawn(command, self.args.repo)
        except (OSError, ValueError) as exc:
            return {"error": {"code": "acp-spawn-failed", "message": str(exc)}}
        self.write_record()
        capabilities = {"fs": {"readTextFile": False, "writeTextFile": False},
                        "terminal": False}
        if self.init_meta:
            capabilities["_meta"] = self.init_meta
        request_id = self.agent.send_request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "clientCapabilities": capabilities,
            },
        )
        response = self.agent.wait_response(request_id, 15.0)
        if response is None:
            return {"error": {"code": "acp-initialize-timeout", "message": "no initialize response"}}
        if "error" in response:
            return {"error": {"code": "acp-initialize-failed", "message": response["error"]}}
        result = response.get("result") or {}
        self.protocol_version = result.get("protocolVersion")
        self.agent_info = result.get("agentInfo") or {}
        self.capabilities = result.get("agentCapabilities") or {}
        self.auth_methods = result.get("authMethods") or []
        if self.protocol_version != PROTOCOL_VERSION:
            self.write_record()
            return {
                "error": {
                    "code": "acp-protocol-version-unsupported",
                    "message": f"agent negotiated protocolVersion={self.protocol_version}",
                    "agent_version": self.protocol_version,
                }
            }
        session_caps = self.capabilities.get("sessionCapabilities") or {}
        if resume is not None:
            if not capability_supported(session_caps, "resume") \
                    and not capability_supported(self.capabilities, "loadSession"):
                return {"error": {"code": "resume-unsupported", "message": "agent lacks resume/loadSession"}}
            method = "session/resume" if capability_supported(session_caps, "resume") else "session/load"
            request_id = self.agent.send_request(
                method, {"sessionId": resume, "cwd": self.args.repo, "mcpServers": []}
            )
            response = self.agent.wait_response(request_id, 15.0)
            if response is None or "error" in response:
                return {"error": {"code": "resume-failed", "message": json.dumps(response)}}
            self.session_meta = response.get("result") or {}
            self.initial_config_options = self.session_meta.get("configOptions")
            self.acp_session_id = self.session_meta.get("sessionId", resume)
        elif use_continue:
            if not capability_supported(session_caps, "list"):
                return {"error": {"code": "continue-unsupported", "message": "agent lacks session/list"}}
            sessions, list_error = self._list_repo_sessions()
            if list_error is not None:
                return {"error": list_error}
            if not sessions:
                return {"error": {"code": "continue-empty", "message": "no sessions to resume"}}
            latest, candidates = latest_session(sessions)
            if latest is None:
                return {"error": {
                    "code": "continue-ambiguous",
                    "message": "cannot determine the latest session from factual identity",
                    "candidates": [
                        {"sessionId": entry.get("sessionId"), "updatedAt": entry.get("updatedAt")}
                        for entry in candidates
                    ],
                }}
            return self.initialize_agent_resume(latest["sessionId"])
        else:
            request_id = self.agent.send_request(
                "session/new", {"cwd": self.args.repo, "mcpServers": []}
            )
            response = self.agent.wait_response(request_id, 15.0)
            if response is None:
                return {"error": {"code": "acp-session-timeout", "message": "no session/new response"}}
            if "error" in response:
                error = response["error"]
                if error.get("code") in (-32000, -32001) or "auth" in str(error.get("message", "")).lower():
                    if self.auth_methods:
                        auth_id = self.agent.send_request(
                            "authenticate", {"methodId": self.auth_methods[0]["id"]}
                        )
                        auth_response = self.agent.wait_response(auth_id, 30.0)
                        if auth_response and "error" not in auth_response:
                            return self.initialize_agent()
                    return {"error": {"code": "login-required", "message": error.get("message")}}
                return {"error": {"code": "acp-session-failed", "message": error}}
            self.session_meta = response.get("result") or {}
            self.initial_config_options = self.session_meta.get("configOptions")
            self.acp_session_id = self.session_meta.get("sessionId")
        self.state = "ready"
        self.write_record()
        return {"acp_session_id": self.acp_session_id, "agent_info": self.agent_info,
                "protocol_version": self.protocol_version, "capabilities": self.capabilities}

    def _list_repo_sessions(self) -> tuple[list[dict], dict | None]:
        """Collect all cwd-filtered sessions by following ``nextCursor`` pages."""
        collected: list[dict] = []
        seen_cursors: set[str] = set()
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"cwd": self.args.repo}
            if cursor:
                params["cursor"] = cursor
            request_id = self.agent.send_request("session/list", params)
            response = self.agent.wait_response(request_id, 15.0)
            if response is None or "error" in response:
                return [], {"code": "continue-list-failed", "message": json.dumps(response)}
            result = (response or {}).get("result") or {}
            collected.extend(
                entry for entry in (result.get("sessions") or [])
                if isinstance(entry, dict) and entry.get("sessionId")
            )
            cursor = result.get("nextCursor") or None
            if not cursor:
                return collected, None
            if cursor in seen_cursors:
                return collected, {"code": "continue-list-cursor-loop", "cursor": cursor}
            seen_cursors.add(cursor)

    def initialize_agent_resume(self, session_id: str) -> dict[str, Any]:
        session_caps = self.capabilities.get("sessionCapabilities") or {}
        if not capability_supported(session_caps, "resume") \
                and not capability_supported(self.capabilities, "loadSession"):
            return {"error": {"code": "resume-unsupported"}}
        method = "session/resume" if capability_supported(session_caps, "resume") else "session/load"
        request_id = self.agent.send_request(
            method, {"sessionId": session_id, "cwd": self.args.repo, "mcpServers": []}
        )
        response = self.agent.wait_response(request_id, 15.0)
        if response is None or "error" in response:
            return {"error": {"code": "resume-failed", "message": json.dumps(response)}}
        self.session_meta = response.get("result") or {}
        self.initial_config_options = self.session_meta.get("configOptions")
        self.acp_session_id = self.session_meta.get("sessionId", session_id)
        self.state = "ready"
        self.write_record()
        return {"acp_session_id": self.acp_session_id, "agent_info": self.agent_info,
                "protocol_version": self.protocol_version, "capabilities": self.capabilities}

    # -- inbound agent messages --------------------------------------------------

    def on_agent_message(self, message: dict[str, Any]) -> None:
        self.last_activity = time.monotonic()
        if "method" in message:
            if "id" in message:
                self.on_agent_request(message)
            else:
                self.on_agent_notification(message)
        else:
            self.agent.resolve_response(message)

    def on_agent_notification(self, message: dict[str, Any]) -> None:
        method = message["method"]
        params = message.get("params") or {}
        if method == "session/update":
            self.on_session_update(params)
        elif method == "$/cancel_request":
            cancelled = params.get("id")
            if cancelled is not None and self.agent.cancel_outbound(cancelled):
                self.events.append({"kind": "outbound_cancelled", "id": cancelled})
                return
            key = normalize_id(cancelled)
            if key in self.pending_permissions:
                self.pending_permissions.pop(key, None)
                self.events.append({"kind": "permission_cancelled", "request_id": cancelled})
                self.write_record()
                self.fanout_follow_delta()
            else:
                self.events.append({"kind": "cancel_request_unknown", "id": cancelled})
        else:
            self.events.append({"kind": "notification", "method": method, "params": params})

    def on_agent_request(self, message: dict[str, Any]) -> None:
        method = message["method"]
        request_id = message["id"]
        params = message.get("params") or {}
        if method == "session/request_permission":
            tool_call = params.get("toolCall") or {}
            entry = {
                "request_id": request_id,
                "title": tool_call.get("title") or params.get("title") or method,
                "tool_call_id": tool_call.get("toolCallId"),
                "options": [
                    {"id": opt.get("optionId"), "kind": opt.get("kind"), "label": opt.get("name")}
                    for opt in params.get("options") or []
                ],
            }
            self.pending_permissions[normalize_id(request_id)] = entry
            if self.turn["active"] and self.turn["mutation_status"] == "in_progress":
                self.turn["mutation_status"] = "accepted"
                self.note_agent_children()
            self.events.append({"kind": "request_permission", "request": entry})
            self.write_record()
            self.fanout_follow_delta()
            with self.turn_cond:
                self.turn_cond.notify_all()
            return
        self.agent.send_message(
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32601, "message": f"client does not implement {method}"}}
        )
        self.events.append({"kind": "unsupported_agent_request", "method": method})

    def on_session_update(self, params: dict[str, Any]) -> None:
        update = params.get("update") or {}
        variant = update.get("sessionUpdate", "unknown")
        turn = self.turn
        if turn["active"] and turn["mutation_status"] == "in_progress":
            turn["mutation_status"] = "accepted"
            self.note_agent_children()
        if variant == "agent_message_chunk":
            text = ((update.get("content") or {}).get("text")) or ""
            turn["final_text"] += text
        elif variant == "agent_thought_chunk":
            turn["thinking_chars"] += len(((update.get("content") or {}).get("text")) or "")
        elif variant in ("tool_call", "tool_call_update"):
            tool_id = update.get("toolCallId") or f"anon-{len(turn['tool_order'])}"
            known = variant == "tool_call_update" and tool_id in turn["tool_calls"]
            record = turn["tool_calls"].setdefault(
                tool_id, {"kind": update.get("kind"), "title": update.get("title"),
                          "status": update.get("status")}
            )
            for field in ("kind", "title", "status"):
                if update.get(field) is not None:
                    record[field] = update[field]
            if update.get("content") is not None:
                record["error_head"] = str(update.get("content"))[:200]
            if not known:
                turn["tool_order"].append(tool_id)
        elif variant == "usage_update":
            turn["context_usage"] = {"used": update.get("used"), "size": update.get("size")}
        elif variant == "config_option_update":
            if params.get("sessionId") in (None, self.acp_session_id):
                self._apply_config_options(
                    update.get("configOptions"), "config_option_update")
        elif variant not in KNOWN_UPDATES:
            self.agent.unknown_updates += 1
        self.projection.apply(update, self.events.cursor + 1)
        cursor = self.events.append({"kind": "session_update", "sessionId": params.get("sessionId"),
                                     "update": update})
        self.write_record()
        self.fanout_follow_delta()

    def on_prompt_response(self, request_id: int, response: dict[str, Any] | None) -> None:
        turn = self.turn
        if response is None or not turn["active"]:
            return
        if "error" in response:
            turn["error"] = response["error"]
            turn["outcome"] = (
                "turn_canceled" if (response["error"] or {}).get("code") == -32800
                else "turn_failed"
            )
        else:
            stop = (response.get("result") or {}).get("stopReason")
            turn["stop_reason"] = stop
            turn["outcome"] = "turn_canceled" if stop == "cancelled" else "turn_completed"
        turn["mutation_status"] = "completed"
        turn["active"] = False
        self.projection.close_message()
        outcome = turn["outcome"]
        if outcome in ("turn_completed", "turn_failed") and not self.agent.exited.is_set():
            # One business idle episode per ended turn with the agent alive;
            # the 600s idle_watcher stays a non-business exit timer.
            self._notify_heartbeat_host_now(
                "idle", f"outcome={outcome} stop_reason={turn.get('stop_reason')}")
        self.last_prompt = {
            "fingerprint": turn["fingerprint"],
            "written_at": turn["written_at"],
            "transport": "acp",
            "mutation_status": turn["mutation_status"],
            "stop_reason": turn["stop_reason"],
        }
        self.write_record()
        self.fanout_follow_delta()
        with self.turn_cond:
            self.turn_cond.notify_all()
        self._worker_event_turn_end(turn.get("fingerprint"), outcome)

    def on_agent_exit(self, code: int) -> None:
        reason = (f"exit_code={self.agent.exit_code}"
                  if self.agent.exit_code is not None
                  else f"exit_signal={self.agent.exit_signal}")
        # Before agent_exited: op_stop waits out the notify lock, so an exact
        # stop never kills a half-delivered worker-event notification.
        self._notify_heartbeat_host_now("terminated", reason)
        self.agent_exited.set()
        self.events.append({"kind": "process_exited", "code": self.agent.exit_code,
                            "signal": self.agent.exit_signal})
        turn = self.turn
        if turn["active"]:
            turn["outcome"] = "process_exited"
            turn["active"] = False
            self.last_prompt = {
                "fingerprint": turn["fingerprint"],
                "written_at": turn["written_at"],
                "transport": "acp",
                "mutation_status": turn["mutation_status"],
                "stop_reason": None,
            }
        for key, entry in list(self.pending_permissions.items()):
            self.pending_permissions.pop(key, None)
        self.projection.close_message()
        if self.state not in ("stopping", "stopped"):
            self.state = "agent_exited"
        with self.agent.lock:
            stranded = list(self.agent.pending_out.values())
            self.agent.pending_out.clear()
        for slot in stranded:
            if slot["response"] is None:
                slot["response"] = {"error": {"code": "agent-exited",
                                              "message": "agent process exited"}}
            slot["event"].set()
        self.write_record()
        self.fanout_follow_eof()
        with self.turn_cond:
            self.turn_cond.notify_all()

    # -- ops ---------------------------------------------------------------------

    def op_state(self) -> dict[str, Any]:
        turn = self.turn
        if turn["active"]:
            activity = "waiting" if self.pending_permissions else "busy"
        elif self.agent.exited.is_set():
            activity = "exited"
        else:
            activity = "idle"
        return {
            "state": self.state,
            "holder_pid": os.getpid(),
            "holder_instance_id": self.holder_instance_id,
            "agent_pid": self.agent.proc.pid if self.agent.proc else None,
            "agent_pgid": self.agent.proc.pid if self.agent.proc else None,
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "agent_exit_code": self.agent.exit_code,
            "acp_session_id": self.acp_session_id,
            "session_meta": self.session_meta,
            "initial_config_options": self.initial_config_options,
            "protocol_version": self.protocol_version,
            "agent_info": self.agent_info,
            "capabilities": self.capabilities,
            "pending_permissions": list(self.pending_permissions.values()),
            "activity_hint": activity,
            "last_prompt": self.last_prompt,
            "turn_active": turn["active"],
            "turn_outcome": turn.get("outcome"),
            "stop_reason": turn.get("stop_reason"),
            "mutation_status": turn.get("mutation_status"),
            "context_usage": turn.get("context_usage"),
            "event_cursor": self.events.cursor,
            "malformed_stdout_lines": self.agent.malformed_lines,
            "unknown_update_variants": self.agent.unknown_updates,
            "fatal_error": self.fatal_error,
        }

    def turn_receipt(self, wait_timeout: float | None = None,
                     max_final_chars: int = 4000) -> dict[str, Any]:
        turn = self.turn
        outcome = turn.get("outcome")
        mutation_status = turn.get("mutation_status") or "not_started"
        performed = {"completed": True, "accepted": True, "in_progress": True,
                     "not_started": False, "unknown": None}.get(mutation_status)
        final_text = turn.get("final_text") or ""
        truncated = False
        if len(final_text) > max_final_chars:
            final_text = final_text[:max_final_chars]
            truncated = True
        tools = list(turn["tool_calls"].values())
        failed = [t for t in tools if (t.get("status") or "") in ("failed", "error")]
        kinds: dict[str, int] = {}
        for tool in tools:
            kind = tool.get("kind") or "other"
            kinds[kind] = kinds.get(kind, 0) + 1
        receipt = {
            "acp_session_id": self.acp_session_id,
            "prompt_fingerprint": turn.get("fingerprint"),
            "outcome": outcome or ("in_progress" if turn["active"] else None),
            "stop_reason": turn.get("stop_reason"),
            "mutation_status": mutation_status,
            "mutation_performed": performed,
            "duration_ms": round((time.monotonic() - turn["started_at"]) * 1000)
            if turn.get("started_at") else None,
            "final_text": final_text,
            "final_text_truncated": truncated,
            "event_log_path": str(self.events.path) if truncated else None,
            "tool_calls": {"count": len(tools), "kinds": kinds, "failed": len(failed)},
            "side_effects": {
                "files_changed": sum(
                    1 for t in tools if (t.get("kind") or "") in ("edit", "write", "delete")
                ),
                "commands_run": sum(
                    1 for t in tools if (t.get("kind") or "") in ("execute", "shell")
                ),
            },
            "failed_tools": [
                {"title": t.get("title"), "kind": t.get("kind"),
                 "error_head": t.get("error_head")}
                for t in failed[:3]
            ],
            "thinking_chars": turn.get("thinking_chars", 0),
            "context_usage": turn.get("context_usage"),
            "pending_permissions": list(self.pending_permissions.values()),
            "event_cursor": self.events.cursor,
            "event_log_bytes": self.events.path.stat().st_size
            if self.events.path.exists() else 0,
        }
        if turn.get("error"):
            receipt["error"] = turn["error"]
            if self.agent.stderr_pump:
                receipt["error"]["stderr_tail"] = self.agent.stderr_pump.tail()
        return receipt

    def op_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.agent.exited.is_set() or self.agent.proc is None:
            return {"outcome": "process_exited", "mutation_status": "not_started",
                    "mutation_performed": False,
                    "error": {"code": "agent-not-running", "message": "agent process is not running"}}
        with self.lock:
            if self.turn["active"]:
                return {"error": {"code": "prompt-in-progress",
                                  "message": "a prompt turn is already active"},
                        "outcome": "in_progress", "mutation_status": self.turn["mutation_status"]}
            text = params.get("text") or ""
            fingerprint = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
            previous = self.last_prompt or {}
            self.turn = self._empty_turn()
            self.turn.update({
                "active": True,
                "fingerprint": fingerprint,
                "started_at": time.monotonic(),
            })
            duplicate = None
            if previous.get("fingerprint") == fingerprint:
                duplicate = {
                    "code": "duplicate-prompt-warning",
                    "previous_transport": previous.get("transport"),
                    "previous_written_at": previous.get("written_at"),
                    "previous_mutation_status": previous.get("mutation_status"),
                    "previous_stop_reason": previous.get("stop_reason"),
                }
            request_id = self.agent.send_request(
                "session/prompt",
                {
                    "sessionId": self.acp_session_id,
                    "prompt": [{"type": "text", "text": text}],
                },
            )
            if normalize_id(request_id) not in self.agent.pending_out:
                self.turn["active"] = False
                self.turn["mutation_status"] = "not_started"
                self.turn["outcome"] = "turn_failed"
                self.last_prompt = {
                    "fingerprint": fingerprint,
                    "written_at": None,
                    "transport": "acp",
                    "mutation_status": "not_started",
                    "stop_reason": None,
                }
                self.write_record()
                return {"outcome": "turn_failed", "mutation_status": "not_started",
                        "mutation_performed": False,
                        "error": {"code": "acp-write-failed", "message": "prompt frame was not written"}}
            self.turn["request_id"] = request_id
            self.turn["written_at"] = round(time.time(), 3)
            self.turn["mutation_status"] = "in_progress"
            self.last_prompt = {
                "fingerprint": fingerprint,
                "written_at": self.turn["written_at"],
                "transport": "acp",
                "mutation_status": "in_progress",
                "stop_reason": None,
            }
            self.projection.add_user_from_prompt(text, self.events.cursor)
            self.write_record()

        threading.Thread(
            target=self._await_prompt, args=(request_id,), daemon=True
        ).start()
        wait = params.get("wait", True)
        timeout = params.get("timeout")
        max_chars = params.get("max_final_chars", 4000)
        if not wait:
            return {"outcome": "in_progress", "mutation_status": "in_progress",
                    "mutation_performed": True, "prompt_fingerprint": fingerprint,
                    "duplicate_warning": duplicate, "acp_session_id": self.acp_session_id}
        deadline = time.monotonic() + timeout if timeout else None
        with self.turn_cond:
            while self.turn["active"]:
                remaining = (deadline - time.monotonic()) if deadline else 0.5
                if deadline and remaining <= 0:
                    break
                self.turn_cond.wait(timeout=max(remaining, 0.05))
                if deadline and time.monotonic() >= deadline and self.turn["active"]:
                    break
        if self.turn["active"]:
            return {**self.turn_receipt(max_final_chars=max_chars),
                    "outcome": "prompt_timeout",
                    "duplicate_warning": duplicate}
        receipt = self.turn_receipt(max_final_chars=max_chars)
        receipt["duplicate_warning"] = duplicate
        return receipt

    def _await_prompt(self, request_id: int) -> None:
        response = self.agent.wait_response(request_id, None)
        self.on_prompt_response(request_id, response)

    # -- event-driven heartbeat carrier (Issue #62 phase 2) --------------------

    def _notify_heartbeat_host_now(self, kind: str, reason: str) -> None:
        """One carrier send from this worker holder to the ZCode Host holder.

        Synchronous and bounded: the caller is an existing agent-exit or
        turn-end path, and ``op_stop`` waits out this lock before exiting, so
        an exact stop never kills a half-delivered event. The receipt (staged,
        delivered, or an honest error) is evidence in this holder's event log.
        """
        target = self.heartbeat_host
        if target is None:
            return
        params = {"schema": WORKER_EVENT_SCHEMA, "kind": kind,
                  "platform": self.args.platform, "session": self.args.session,
                  "repo": self.args.repo, "reason": reason,
                  "event_cursor": self.events.cursor}
        receipt: dict[str, Any] = {}
        with self.heartbeat_notify_lock:
            try:
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    connection.settimeout(HEARTBEAT_NOTIFY_TIMEOUT)
                    connection.connect(target["socket"])
                    connection.sendall(canonical(
                        {"op": "worker_event", "request_id": secrets.token_hex(8),
                         "params": params}) + b"\n")
                    buffer = bytearray()
                    while b"\n" not in buffer:
                        data = connection.recv(65536)
                        if not data:
                            break
                        buffer.extend(data)
                    line = buffer.partition(b"\n")[0]
                    if line.strip():
                        receipt = json.loads(line.decode("utf-8", "replace"))
                finally:
                    connection.close()
            except (OSError, ValueError) as exc:
                receipt = {"error": {"code": "host-unreachable", "message": str(exc)}}
        if not receipt:
            receipt = {"error": {"code": "host-closed",
                                 "message": "heartbeat host closed without a receipt"}}
        self.events.append({"kind": "heartbeat_carrier_sent", "event_kind": kind,
                            "reason": reason, "target_session": target["session"],
                            "receipt": receipt})

    def _heartbeat_payload(self, events: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        """One literal notification prompt: fixed structured event metadata,
        the current FULL heartbeat prompt body read at delivery time from the
        file the ZCode Host agent maintains in the consuming project, and the
        one-pass instruction. No worker raw output, no shell execution."""
        source = Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json"
        body: str | None = None
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("body"), str) and data["body"]:
                body = data["body"]
        except (OSError, ValueError):
            body = None
        maintained = body is not None
        if not maintained:
            body = (f"No maintained heartbeat prompt was found at {source}. Recover "
                    "authorization and field state from the consuming project records, "
                    "then run one full pass.")
        lines = [
            "kaola-host-notify/1: event-driven heartbeat carrier (ZCode Host)",
            "worker events (structured, one JSON object per line):",
        ]
        for event in events:
            lines.append(json.dumps(
                {key: event.get(key) for key in
                 ("event_id", "kind", "platform", "session", "repo", "reason",
                  "event_cursor")},
                ensure_ascii=False, sort_keys=True))
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if maintained:
            lines.append(f"heartbeat prompt source: {source} (fingerprint sha256:{digest}, "
                         f"{len(body.encode('utf-8'))} bytes)")
        else:
            lines.append(f"heartbeat prompt source: none maintained at {source} "
                         f"(fallback trigger context, sha256:{digest})")
        lines.append("heartbeat prompt body follows, verbatim:")
        lines.append("<<<heartbeat-prompt")
        lines.append(body)
        lines.append("heartbeat-prompt>>>")
        lines.append("Perform exactly one full Project Runner heartbeat pass - recover "
                     "authorization and field state, handle worker questions, dispatch "
                     "suitable authorized work, verify deliveries, and close out - per "
                     "PROJECT_RUNNER_HEARTBEAT_V2. This worker event is the only heartbeat "
                     "trigger; this ZCode Host registers no periodic carrier.")
        return "\n".join(lines), {"heartbeat_fingerprint": f"sha256:{digest}",
                                  "heartbeat_source": str(source),
                                  "heartbeat_maintained": maintained}

    def _deliver_worker_events(self) -> dict[str, Any]:
        """Deliver every staged event as one ordinary prompt through the
        normal admission path. A busy or dead-agent host keeps events staged
        for the next boundary or resume; nothing here bypasses op_prompt."""
        with self.worker_events_lock:
            staged = [item for item in self.pending_worker_events
                      if "prompt_fingerprint" not in item]
        if not staged:
            return {"delivered": False, "reason": "queue-empty"}
        if self.agent.proc is None or self.agent.exited.is_set():
            return {"delivered": False, "reason": "agent-not-running"}
        if self.turn["active"]:
            return {"delivered": False, "reason": "prompt-in-progress"}
        text, meta = self._heartbeat_payload(staged)
        prompt = self.op_prompt({"text": text, "wait": False})
        error = prompt.get("error")
        if error or prompt.get("outcome") != "in_progress":
            return {"delivered": False, "error": error or prompt}
        fingerprint = prompt.get("prompt_fingerprint")
        with self.worker_events_lock:
            for item in staged:
                item["prompt_fingerprint"] = fingerprint
        self.events.append({
            "kind": "worker_event_delivered",
            "event_ids": [item["event_id"] for item in staged],
            "prompt_fingerprint": fingerprint,
            **meta,
        })
        return {"delivered": True, "prompt_fingerprint": fingerprint,
                "count": len(staged)}

    def _worker_event_turn_end(self, fingerprint: Any, outcome: str | None) -> None:
        """At a turn boundary: confirm the events this turn delivered, then
        flush whatever staged meanwhile. A notification turn that did not
        complete leaves its events staged - no retry loop; the next healthy
        boundary, a newly staged event, or a resume redelivers them."""
        confirmed: list[str] = []
        was_notification = False
        with self.worker_events_lock:
            hit = [item for item in self.pending_worker_events
                   if fingerprint is not None
                   and item.get("prompt_fingerprint") == fingerprint]
            was_notification = bool(hit)
            if hit and outcome == "turn_completed":
                for item in hit:
                    self.pending_worker_events.remove(item)
                confirmed = [item["event_id"] for item in hit]
            elif hit:
                for item in hit:
                    item.pop("prompt_fingerprint", None)
        if confirmed:
            self.events.append({"kind": "worker_event_confirmed",
                                "event_ids": confirmed})
        if not was_notification or outcome == "turn_completed":
            if self.agent.proc is not None and not self.agent.exited.is_set():
                self._deliver_worker_events()

    def op_worker_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Carrier op on a ZCode Host holder: stage one worker event, then
        deliver when the host turn is already idle."""
        if self.args.platform != "zcode":
            return {"error": {"code": "worker-event-unsupported",
                              "message": "the event-driven heartbeat carrier is a ZCode "
                                         f"Host capability; this session's platform is "
                                         f"{self.args.platform}"}}
        kind = params.get("kind")
        platform = params.get("platform")
        session = params.get("session")
        repo = params.get("repo")
        reason = params.get("reason")
        cursor = params.get("event_cursor")
        if (kind not in WORKER_EVENT_KINDS or not isinstance(platform, str)
                or not platform or not isinstance(session, str) or not session
                or not isinstance(repo, str) or not repo
                or not isinstance(reason, str)
                or not isinstance(cursor, int) or isinstance(cursor, bool)):
            return {"error": {"code": "worker-event-invalid",
                              "message": "worker_event needs kind terminated|idle plus "
                                         "platform, session, repo, reason, and an integer "
                                         "event_cursor"}}
        event = {"schema": WORKER_EVENT_SCHEMA,
                 "event_id": f"{platform}/{session}/{kind}/{cursor}",
                 "kind": kind, "platform": platform, "session": session,
                 "repo": repo, "reason": reason, "event_cursor": cursor,
                 "staged_at": round(time.time(), 3)}
        with self.worker_events_lock:
            if any(item.get("event_id") == event["event_id"]
                   for item in self.pending_worker_events):
                return {"event_id": event["event_id"], "duplicate": True,
                        "pending": len(self.pending_worker_events)}
            if len(self.pending_worker_events) >= HEARTBEAT_EVENT_CAP:
                return {"error": {"code": "worker-event-queue-full",
                                  "capacity": HEARTBEAT_EVENT_CAP,
                                  "message": f"{HEARTBEAT_EVENT_CAP} worker events are "
                                             "already waiting for this host turn boundary"}}
            self.pending_worker_events.append(event)
            pending = len(self.pending_worker_events)
        self.events.append({"kind": "worker_event", "event": event})
        receipt: dict[str, Any] = {"event_id": event["event_id"], "staged": True,
                                   "pending": pending}
        if (not self.turn["active"] and self.agent.proc is not None
                and not self.agent.exited.is_set()):
            receipt.update(self._deliver_worker_events())
        return receipt

    def _restore_worker_events(self) -> None:
        """Resume redelivery: rebuild the pending list from this holder's own
        event log (staged without a matching confirmation) and deliver it into
        the resumed session. At-least-once; the heartbeat pass itself is the
        dedup authority, per the skeleton's recover step."""
        staged: list[dict[str, Any]] = []
        confirmed: set[str] = set()
        for entry in self.events.read_since(0, None):
            if entry.get("kind") == "worker_event":
                event = entry.get("event")
                if isinstance(event, dict) and isinstance(event.get("event_id"), str):
                    staged.append(event)
            elif entry.get("kind") == "worker_event_confirmed":
                ids = entry.get("event_ids")
                if isinstance(ids, list):
                    confirmed.update(item for item in ids if isinstance(item, str))
        pending: list[dict[str, Any]] = []
        seen: set[str] = set()
        for event in staged:
            if event["event_id"] in confirmed or event["event_id"] in seen:
                continue
            seen.add(event["event_id"])
            pending.append(event)
        if len(pending) > HEARTBEAT_EVENT_CAP:
            dropped = [event["event_id"] for event in pending[:-HEARTBEAT_EVENT_CAP]]
            pending = pending[-HEARTBEAT_EVENT_CAP:]
            self.events.append({"kind": "worker_event_overflow", "dropped": dropped,
                                "capacity": HEARTBEAT_EVENT_CAP})
        self.pending_worker_events = pending
        if pending:
            self.events.append({"kind": "worker_event_restored",
                                "event_ids": [event["event_id"] for event in pending]})
            self._deliver_worker_events()


    def op_wait(self, params: dict[str, Any]) -> dict[str, Any]:
        timeout = params.get("timeout")
        deadline = time.monotonic() + timeout if timeout else None
        with self.turn_cond:
            while self.turn["active"]:
                remaining = (deadline - time.monotonic()) if deadline else 0.5
                if deadline and remaining <= 0:
                    return {**self.turn_receipt(), "outcome": "prompt_timeout"}
                self.turn_cond.wait(timeout=max(remaining, 0.05))
        return self.turn_receipt()

    def _settle_pending_permission_locked(self, key: str, option: Any) -> dict[str, Any] | None:
        """Lookup pending → one JSON-RPC result → pop. Caller holds self.lock.

        Same lock as prompt admission. A missing/already-settled id returns None
        and must not write agent stdin again.
        """
        entry = self.pending_permissions.get(key)
        if entry is None:
            return None
        outcome = {"outcome": "cancelled"} if option in (None, "cancelled", "cancel") else {
            "outcome": "selected", "optionId": option
        }
        self.agent.send_message(
            {"jsonrpc": "2.0", "id": entry["request_id"], "result": {"outcome": outcome}}
        )
        self.pending_permissions.pop(key, None)
        return entry

    def _cancel_pending_permissions(self) -> None:
        """Cancel every still-pending permission at most once under self.lock."""
        with self.lock:
            for key in list(self.pending_permissions):
                self._settle_pending_permission_locked(key, "cancelled")

    def _holder_instance_mismatch(self, op: str, expected: Any) -> dict[str, Any]:
        self.events.append({"kind": "holder_instance_mismatch", "op": op,
                            "expected_holder_instance_id": expected})
        return {
            "error": {
                "code": "holder-instance-mismatch",
                "message": "expected holder instance does not match this holder process",
                "expected_holder_instance_id": expected,
                "holder_instance_id": self.holder_instance_id,
                "mutation_status": "not_started",
                "mutation_performed": False,
            },
            "mutation_status": "not_started",
            "mutation_performed": False,
        }

    def op_permit(self, params: dict[str, Any]) -> dict[str, Any]:
        request_id = params.get("request_id")
        option = params.get("option")
        expected = params.get("expected_holder_instance_id")
        with self.lock:
            if expected is not None and expected != self.holder_instance_id:
                return self._holder_instance_mismatch("permit", expected)
            pending = self.pending_permissions
            if not pending:
                return {"error": {"code": "no-pending-permission",
                                  "message": "no permission request is pending"}}
            if request_id is None:
                if len(pending) > 1:
                    return {"error": {"code": "request-id-required",
                                      "message": f"{len(pending)} permissions pending; --request-id required"}}
                request_id = next(iter(pending))
            key = normalize_id(request_id)
            entry = self._settle_pending_permission_locked(key, option)
            if entry is None:
                return {"error": {"code": "unknown-request",
                                  "message": f"no pending permission with id {request_id}"}}
            self.events.append({"kind": "permission_answered", "request_id": request_id,
                                "option": option})
            self.write_record()
            self.fanout_follow_delta()
            return {"permitted": request_id, "option": option,
                    "pending_permissions": list(pending.values())}

    def op_steer(self, params: dict[str, Any]) -> dict[str, Any]:
        """Issue #65: one native mid-turn steering request for this exact session.

        Steering is a transport operation the controlling Agent chooses, never a
        Runner policy. It reuses the running turn: it starts no second turn, adds
        no scheduler, and never becomes a second stdin writer. The receipt states
        one fact — whether this agent consumed the text into the running turn —
        and keeps that separate from whether the model actually followed it.
        """
        method = (params.get("method") or "").strip()
        text = params.get("text") or ""
        base: dict[str, Any] = {
            "steer_method": method or None,
            "steer_text_chars": len(text),
            "steer_fingerprint": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        if not method:
            return {**base, "steer_outcome": "unsupported", "steer_consumed": False,
                    "outcome": "steer_unsupported",
                    "mutation_status": self.turn.get("mutation_status"),
                    "mutation_performed": False,
                    "error": {"code": "steer-unsupported",
                              "message": "this platform exposes no native steering entry; "
                                         "the text was not consumed"}}
        if not text.strip():
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "outcome": "steer_rejected",
                    "error": {"code": "steer-empty", "message": "steer requires non-empty text"}}
        if self.agent.exited.is_set() or self.agent.proc is None:
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "outcome": "process_exited", "mutation_status": "unknown",
                    "mutation_performed": False,
                    "error": {"code": "agent-not-running",
                              "message": "agent process is not running"}}

        with self.lock:
            if not self.turn["active"]:
                # An idle steer is never written. Some agents answer an idle
                # steering call by starting a detached turn this holder would not
                # own (Codex 1.11.0 returns startedNewTurn), so the Agent gets an
                # honest not-consumed and decides whether to send a normal prompt.
                return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                        "steer_reason": "no-active-turn", "outcome": "no-active-turn",
                        "mutation_status": self.turn.get("mutation_status"),
                        "mutation_performed": False}
            turn_request_id_before = self.turn["request_id"]
            turn_fingerprint = self.turn["fingerprint"]
            steer_request_id = self.agent.send_request(
                method,
                {
                    "sessionId": self.acp_session_id,
                    "prompt": [{"type": "text", "text": text}],
                    # A compliant agent must not manufacture a detached turn when
                    # the turn settles between our check and its handler.
                    "_meta": {"steering": {"idleBehavior": "promptRequired"}},
                },
            )
            self.events.append({"kind": "steer_sent", "method": method,
                                "request_id": steer_request_id,
                                "turn_request_id": turn_request_id_before,
                                "fingerprint": base["steer_fingerprint"]})
        base["steer_request_id"] = steer_request_id
        base["turn_request_id"] = turn_request_id_before

        timeout = params.get("timeout")
        if timeout is None:
            timeout = STEER_TIMEOUT
        response = self.agent.wait_response(steer_request_id, timeout)

        if response is None:
            outcome, consumed, error = "unknown", None, {
                "code": "steer-no-response",
                "message": "no reply to the steering request before the timeout; "
                           "consumption is unknown — do not resend blindly"}
        elif "error" in response:
            detail = response.get("error") or {}
            if detail.get("code") == -32601:
                outcome, consumed = "unsupported", False
                error = {"code": "steer-unsupported",
                         "message": f"agent does not implement {method}", "detail": detail}
            else:
                outcome, consumed = "rejected", False
                error = {"code": "steer-rejected", "message": str(detail.get("message", "")),
                         "detail": detail}
        else:
            result = response.get("result") or {}
            native = result.get("outcome")
            base["steer_native_outcome"] = native
            error = None
            if native == "injected":
                outcome, consumed = "injected", True
            elif native == "startedNewTurn":
                # Honest naming: this is NOT injection into the running turn.
                outcome, consumed = "started_new_turn", True
                error = {"code": "steer-started-new-turn",
                         "message": "the agent started a separate turn this holder does not "
                                    "track; the running turn did not absorb the text"}
            elif native == "promptRequired":
                outcome, consumed = "not_consumed", False
                error = {"code": "steer-prompt-required",
                         "message": "the turn had already settled; send a normal prompt instead"}
            else:
                outcome, consumed = "unknown", None
                error = {"code": "steer-unrecognized-outcome",
                         "message": f"unrecognized steering outcome {native!r}"}

        with self.lock:
            turn_request_id_after = self.turn["request_id"]
            receipt = {
                **base,
                "steer_outcome": outcome,
                "steer_consumed": consumed,
                "steer_response": response,
                "turn_request_id_after": turn_request_id_after,
                "turn_request_id_preserved": (
                    turn_request_id_after in (turn_request_id_before, None)
                ),
                "turn_prompt_fingerprint": turn_fingerprint,
                "turn_active": self.turn["active"],
                "outcome": f"steer_{outcome}",
                "mutation_status": self.turn.get("mutation_status"),
                # This steer's own effect: `injected` wrote into the running
                # turn, anything else wrote nothing. The turn's own progress
                # stays in `mutation_status`.
                "mutation_performed": consumed,
            }
            if error:
                receipt["error"] = error
            self.events.append({"kind": "steer_result", "method": method,
                                "request_id": steer_request_id,
                                "steer_outcome": outcome,
                                "steer_consumed": consumed,
                                "turn_request_id_preserved": receipt["turn_request_id_preserved"]})
        return receipt

    def op_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        expected = params.get("expected_holder_instance_id")
        with self.lock:
            if expected is not None and expected != self.holder_instance_id:
                return self._holder_instance_mismatch("cancel", expected)
            if not self.turn["active"]:
                return {"outcome": "no-active-turn", "mutation_status": self.turn.get("mutation_status")}
            for key in list(self.pending_permissions):
                self._settle_pending_permission_locked(key, "cancelled")
            self.turn["cancel_requested"] = True
            self.agent.send_message(
                {"jsonrpc": "2.0", "method": "session/cancel",
                 "params": {"sessionId": self.acp_session_id}}
            )
        timeout = params.get("timeout")
        if timeout is None:
            timeout = CANCEL_GRACE
        deadline = time.monotonic() + timeout
        with self.turn_cond:
            while self.turn["active"]:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {**self.turn_receipt(), "outcome": "cancel-unconfirmed"}
                self.turn_cond.wait(timeout=remaining)
        return self.turn_receipt()

    def op_view(self, params: dict[str, Any]) -> dict[str, Any]:
        since = params.get("since")
        if since is not None:
            try:
                since = int(since)
            except (TypeError, ValueError):
                since = None
        proj = self.projection.snapshot()
        thinking_truncated = proj["thinking_chars"] > THINKING_TAIL_CHARS
        thinking = {
            "chars": proj["thinking_chars"],
            "text_tail": proj["thinking_text"][-THINKING_TAIL_CHARS:],
            "messageId": proj["thinking_message_id"],
        }
        tools = proj["tools"]
        tools_truncated = any(tool.get("truncated") for tool in tools)
        messages = proj["messages"]
        timeline_truncated = bool(proj["messages_dropped"])
        cursor_gap = False
        if isinstance(since, int):
            oldest = self.events.oldest_cursor()
            cursor_gap = oldest is not None and since < oldest
        pending = []
        for entry in self.pending_permissions.values():
            pending.append({
                "request_id": "" if entry.get("request_id") is None else str(entry.get("request_id")),
                "title": entry.get("title"),
                "tool_call_id": entry.get("tool_call_id"),
                "options": [
                    {
                        "optionId": opt.get("id"),
                        "name": opt.get("label"),
                        "kind": opt.get("kind"),
                    }
                    for opt in entry.get("options") or []
                ],
            })
        truncated = bool(
            thinking_truncated or tools_truncated or timeline_truncated or cursor_gap
        )
        payload = {
            "schema": VIEW_SCHEMA,
            "platform": self.args.platform,
            "session": self.args.session,
            "repo": self.args.repo,
            "state": self.state,
            "holder_pid": os.getpid(),
            "holder_instance_id": self.holder_instance_id,
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "event_cursor": self.events.cursor,
            "truncated": truncated,
            "cursor_gap": cursor_gap,
            "messages": messages,
            "thinking": thinking,
            "tools": tools,
            "plan": proj["plan"],
            "pending_permissions": pending,
            "mode": proj["mode"],
            "commands": proj["commands"],
            "usage": proj["usage"],
            "turn": {
                "mutation_status": self.turn.get("mutation_status") or "not_started",
                "outcome": self.turn.get("outcome"),
                "stop_reason": self.turn.get("stop_reason"),
                "active": bool(self.turn.get("active")),
            },
            "unparsed_update_count": self.agent.unknown_updates,
        }
        self._fit_view(payload)
        return payload

    @staticmethod
    def _fit_view(payload: dict[str, Any]) -> None:
        """Whole-view cap: drop oldest tools, then oldest messages, until it fits."""
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        if size <= VIEW_BYTES:
            return
        payload["truncated"] = True
        for key in ("tools", "messages"):
            items = payload[key]
            drop = 0
            while size > VIEW_BYTES and drop < len(items):
                size -= len(json.dumps(items[drop], ensure_ascii=False).encode("utf-8")) + 1
                drop += 1
            if drop:
                payload[key] = items[drop:]
            if size <= VIEW_BYTES:
                return

    def fanout_follow_delta(self) -> None:
        with self.followers_lock:
            if not self.followers:
                return
            payload = self.op_view({})
            for follower in list(self.followers):
                follower.offer_delta(payload)

    def fanout_follow_heartbeat(self) -> None:
        with self.followers_lock:
            if not self.followers:
                return
            payload = self.op_view({})
            for follower in list(self.followers):
                follower.offer_heartbeat(payload)

    def fanout_follow_eof(self) -> None:
        with self.followers_lock:
            followers = list(self.followers)
        for follower in followers:
            follower.offer_eof()

    def unregister_follower(self, follower: Follower) -> None:
        with self.followers_lock:
            self.followers = [item for item in self.followers if item is not follower]

    def start_follow(self, connection: socket.socket, params: dict[str, Any]) -> Follower:
        since = params.get("since")
        if since is not None:
            try:
                since = int(since)
            except (TypeError, ValueError):
                since = None
        follower = Follower(self, connection, since)
        try:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, FOLLOW_SNDBUF)
        except OSError:
            pass
        payload = self.op_view({"since": since} if since is not None else {})
        with self.followers_lock:
            follower.offer_snapshot(payload)
            if self.agent.exited.is_set():
                follower.offer_eof()
            self.followers.append(follower)
        follower.start()
        self.fanout_follow_delta()
        return follower

    def follow_heartbeat_loop(self) -> None:
        while True:
            time.sleep(FOLLOW_HEARTBEAT_SECONDS)
            try:
                self.fanout_follow_heartbeat()
            except Exception:
                continue

    def op_capture(self, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("full"):
            size = self.events.path.stat().st_size if self.events.path.exists() else 0
            result = {"level": "L3", "event_log_path": str(self.events.path),
                      "event_log_bytes": size}
            if params.get("inline"):
                result["events"] = self.events.read_since(0, params.get("limit"))
            return result
        if params.get("since") is not None:
            return {"level": "L2",
                    "events": self.events.read_since(int(params["since"]), params.get("limit")),
                    "event_cursor": self.events.cursor}
        if params.get("tools"):
            tools = [
                {"tool_call_id": tid, **self.turn["tool_calls"][tid]}
                for tid in self.turn["tool_order"]
            ]
            return {"level": "L1", "tool_calls": tools}
        if params.get("lines") is not None:
            return {"level": "L2",
                    "events": self.events.read_since(
                        max(0, self.events.cursor - int(params["lines"])), None),
                    "event_cursor": self.events.cursor}
        return {"level": "L0", **self.turn_receipt()}

    def op_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        force = bool(params.get("force"))
        self.stop_requested = True
        self.state = "stopping"
        self.write_record()
        self._cancel_pending_permissions()
        if not force:
            if self.turn["active"]:
                self.agent.send_message(
                    {"jsonrpc": "2.0", "method": "session/cancel",
                     "params": {"sessionId": self.acp_session_id}}
                )
                deadline = time.monotonic() + CANCEL_GRACE
                with self.turn_cond:
                    while self.turn["active"] and time.monotonic() < deadline:
                        self.turn_cond.wait(timeout=deadline - time.monotonic())
            session_caps = self.capabilities.get("sessionCapabilities") or {}
            if capability_supported(session_caps, "close") and self.acp_session_id and not self.agent.exited.is_set():
                request_id = self.agent.send_request(
                    "session/close", {"sessionId": self.acp_session_id}
                )
                self.agent.wait_response(request_id, CANCEL_GRACE)
            if self.agent.proc and self.agent.proc.stdin:
                try:
                    self.agent.proc.stdin.close()
                except OSError:
                    pass
                self.agent.exited.wait(EXIT_GRACE)
        residual = self._terminate_group(force)
        # Never kill a half-delivered worker-event notification on the way out.
        if self.heartbeat_notify_lock.acquire(timeout=HEARTBEAT_NOTIFY_GRACE):
            self.heartbeat_notify_lock.release()
        self.state = "stopped"
        self.write_record()
        result = {"stopped": True, "residual_pids": residual,
                  "swept_child_pgids": self.swept_child_pgids,
                  "agent_exit_code": self.agent.exit_code,
                  "agent_exit_signal": self.agent.exit_signal,
                  "mutation_status": self.turn.get("mutation_status"),
                  "_exit_after_reply": True}
        return result

    def note_agent_children(self) -> None:
        """Record the agent's out-of-group child groups: from the process tree
        while the agent is still alive to be their parent, and from the
        agent's own spawn record (written before any child output could be
        forwarded), which still identifies a child after the agent died."""
        proc = self.agent.proc
        if proc is None:
            return
        table = process_table()
        noted: dict[int, dict[int, str]] = {}
        if not self.agent.exited.is_set():
            try:
                pgid = os.getpgid(proc.pid)
            except OSError:
                pgid = proc.pid
            noted = child_groups(proc.pid, pgid, table)
        for child, members in spawn_recorded_groups(self.record_dir / CHILD_RECORD_NAME, table).items():
            noted.setdefault(child, {}).update(members)
        if not noted:
            return
        # Copy-on-write: the reader thread notes here while op threads iterate
        # the mapping in write_record/_terminate_group; rebinding a fresh dict
        # keeps every iteration on a stable object.
        merged = {child: dict(members) for child, members in self.agent_child_groups.items()}
        for child, members in noted.items():
            merged.setdefault(child, {}).update(members)
        self.agent_child_groups = merged

    def _terminate_group(self, force: bool) -> list[int]:
        proc = self.agent.proc
        if proc is None:
            return []
        self.note_agent_children()
        pgid = proc.pid
        try:
            pgid = os.getpgid(proc.pid)
        except OSError:
            pass
        if not self.agent.exited.is_set():
            try:
                os.killpg(pgid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            if not self.agent.exited.wait(TERM_GRACE):
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                self.agent.exited.wait(2.0)
        for member in group_members(pgid):
            if member != proc.pid and process_alive(member):
                try:
                    os.kill(member, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        # Groups the agent spawned outside its own (detached CLI children):
        # the agent normally stops them itself; whatever it left behind, or
        # could not reach because it died first, is terminated here. Only a
        # group whose recorded member identity still holds is touched.
        live = live_child_groups(self.agent_child_groups)
        self.swept_child_pgids = sorted(live)
        if live:
            for child in self.swept_child_pgids:
                try:
                    os.killpg(child, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
            members = [pid for pids in live.values() for pid in pids]
            deadline = time.monotonic() + TERM_GRACE
            while time.monotonic() < deadline and any(process_alive(pid) for pid in members):
                time.sleep(0.05)
            for child in self.swept_child_pgids:
                for member in group_members(child):
                    if process_alive(member):
                        try:
                            os.kill(member, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
        time.sleep(0.1)
        residual = [pid for pid in group_members(pgid) if process_alive(pid)]
        for child in self.swept_child_pgids:
            residual.extend(pid for pid in group_members(child)
                            if process_alive(pid) and pid not in residual)
        return residual

    def op_set_config_option(self, params: dict[str, Any]) -> dict[str, Any]:
        option_id = params.get("config_id")
        if not option_id or params.get("value") is None or not self.acp_session_id:
            return {"error": {"code": "invalid-config-option"}}
        request_id = self.agent.send_request("session/set_config_option", {
            "sessionId": self.acp_session_id,
            "configId": option_id,
            "value": params["value"],
        })
        response = self.agent.wait_response(request_id, 15.0)
        if response is None:
            return {"error": {"code": "config-option-timeout", "config_id": option_id}}
        if "error" in response:
            return {"error": {"code": "config-option-failed", "config_id": option_id, "detail": response["error"]}}
        evidence = {"config_id": option_id, "value": params["value"], "configured": True}
        result = response.get("result") or {}
        if self._apply_config_options(result.get("configOptions"), "set_config_option"):
            self.write_record()
        for option in result.get("configOptions") or []:
            if isinstance(option, dict) and option.get("id") == option_id:
                if option.get("name") is not None:
                    evidence["option_name"] = option["name"]
                if option.get("description") is not None:
                    evidence["option_description"] = option["description"]
                if option.get("currentValue") is not None:
                    evidence["current_value"] = option["currentValue"]
                for choice in option.get("options") or []:
                    if isinstance(choice, dict) and choice.get("value") == params["value"]:
                        if choice.get("name") is not None:
                            evidence["value_name"] = choice["name"]
                        if choice.get("description") is not None:
                            evidence["value_description"] = choice["description"]
                break
        return evidence

    # -- socket server ------------------------------------------------------------

    def handle_request(self, message: dict[str, Any]) -> dict[str, Any]:
        op = message.get("op")
        params = message.get("params") or {}
        if op == "state":
            return self.op_state()
        if op == "prompt":
            return self.op_prompt(params)
        if op == "steer":
            return self.op_steer(params)
        if op == "wait":
            return self.op_wait(params)
        if op == "permit":
            return self.op_permit(params)
        if op == "cancel":
            return self.op_cancel(params)
        if op == "capture":
            return self.op_capture(params)
        if op == "view":
            return self.op_view(params)
        if op == "worker_event":
            return self.op_worker_event(params)
        if op == "set_config_option":
            return self.op_set_config_option(params)
        if op == "stop":
            return self.op_stop(params)
        return {"error": {"code": "unknown-op", "message": f"unsupported op {op}"}}

    def serve_connection(self, connection: socket.socket) -> None:
        follower: Follower | None = None
        try:
            buffer = bytearray()
            while True:
                data = connection.recv(65536)
                if not data:
                    return
                buffer.extend(data)
                while b"\n" in buffer:
                    line, _, rest = buffer.partition(b"\n")
                    buffer = bytearray(rest)
                    if not line.strip():
                        continue
                    try:
                        message = json.loads(line.decode("utf-8"))
                    except ValueError:
                        if follower is not None:
                            follower.offer_error("bad-request", "invalid JSON")
                        else:
                            connection.sendall(b'{"error":{"code":"bad-request"}}\n')
                        continue
                    op = message.get("op") if isinstance(message, dict) else None
                    if follower is not None:
                        if op in FOLLOW_WRITE_OPS:
                            follower.offer_error(
                                "follow-readonly",
                                "follow connection is read-only; use a separate socket",
                            )
                        else:
                            follower.offer_error(
                                "follow-readonly",
                                f"unsupported op on follow connection: {op}",
                            )
                        continue
                    if op == "follow":
                        follower = self.start_follow(
                            connection, message.get("params") or {}
                        )
                        continue
                    response = self.handle_request(message)
                    exit_after = bool(response.pop("_exit_after_reply", False))
                    connection.sendall(canonical(response) + b"\n")
                    if exit_after:
                        connection.close()
                        os._exit(0)
        except (OSError, ValueError):
            return
        finally:
            if follower is not None:
                follower.close()
            try:
                connection.close()
            except OSError:
                pass

    def verify_peer(self, connection: socket.socket) -> bool:
        if sys.platform == "darwin":
            uid = ctypes.c_uint()
            gid = ctypes.c_uint()
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) == 0:
                return uid.value == os.getuid()
            return False
        if hasattr(socket, "SO_PEERCRED"):
            try:
                _pid, uid, _gid = struct.unpack(
                    "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                )
                return uid == os.getuid()
            except (OSError, struct.error):
                pass
        return os.stat(connection.fileno()).st_uid == os.getuid()

    def idle_watcher(self) -> None:
        while True:
            time.sleep(15)
            if self.agent.exited.is_set() and not self.turn["active"]:
                if time.monotonic() - self.last_activity > IDLE_EXIT_SECONDS:
                    self.state = "stopped"
                    self.write_record()
                    os._exit(0)

    def run(self) -> int:
        self.created_at = round(time.time(), 3)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.socket_path.parent, 0o700)
        if self.socket_path.exists() or self.socket_path.is_symlink():
            self.socket_path.unlink()
        self.listener.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        self.listener.listen(16)
        link = self.record_dir / "holder.sock"
        if link != self.socket_path:
            try:
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to(self.socket_path)
            except OSError:
                pass
        self.write_record(socket_path=str(self.socket_path))
        result = self.initialize_agent(
            resume=self.args.resume, use_continue=self.args.use_continue
        )
        if "error" in result:
            self.fatal_error = result["error"]
            self.state = "error"
            self.write_record()
            if result["error"].get("code") == "acp-protocol-version-unsupported":
                self._terminate_group(force=True)
            elif self.agent.proc and not self.agent.exited.is_set():
                pass
        elif self.args.resume or self.args.use_continue:
            # session/load resume: redeliver events the previous holder never
            # saw confirmed (Issue #62 phase 2).
            self._restore_worker_events()
        threading.Thread(target=self.idle_watcher, daemon=True).start()
        threading.Thread(target=self.follow_heartbeat_loop, daemon=True).start()
        while not self.stop_requested or self.listener:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                break
            if not self.verify_peer(connection):
                connection.close()
                continue
            threading.Thread(
                target=self.serve_connection, args=(connection,), daemon=True
            ).start()
        return 0


def run_probe(args: argparse.Namespace) -> int:
    """Short-lived preflight probe: spawn, initialize, session/new, close, exit."""
    env = dict(os.environ)
    env["NO_BROWSER"] = "true"
    result: dict[str, Any] = {"probe": True}
    try:
        argv = shlex.split(args.command)
        proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=args.repo, env=env, start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"probe": True, "error": {"code": "acp-spawn-failed",
                                                   "message": str(exc)}}))
        return 0
    pending: dict[str, dict[str, Any]] = {}
    next_id = [0]
    lock = threading.Lock()

    def send(method: str, params: dict[str, Any]) -> int:
        with lock:
            next_id[0] += 1
            rid = next_id[0]
            pending[str(rid)] = {"event": threading.Event(), "response": None}
        try:
            proc.stdin.write(canonical({"jsonrpc": "2.0", "id": rid,
                                        "method": method, "params": params}) + b"\n")
            proc.stdin.flush()
        except OSError:
            pass
        return rid

    def wait(rid: int, timeout: float) -> dict[str, Any] | None:
        slot = pending[str(rid)]
        slot["event"].wait(timeout)
        return slot["response"]

    def reader() -> None:
        while True:
            line = proc.stdout.readline()
            if not line:
                for slot in pending.values():
                    if slot["response"] is None:
                        slot["response"] = {"error": {"code": "probe-eof"}}
                        slot["event"].set()
                return
            try:
                message = json.loads(line.decode("utf-8", "replace"))
            except ValueError:
                continue
            if "id" in message and "method" not in message:
                slot = pending.get(str(message["id"]))
                if slot is None and isinstance(message["id"], int):
                    slot = pending.get(str(message["id"]))
                if slot:
                    slot["response"] = message
                    slot["event"].set()
            elif "id" in message:
                try:
                    proc.stdin.write(canonical(
                        {"jsonrpc": "2.0", "id": message["id"],
                         "error": {"code": -32601, "message": "unsupported"}}) + b"\n")
                    proc.stdin.flush()
                except OSError:
                    pass

    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(
        target=lambda: [proc.stderr.read(65536) for _ in iter(int, 1) if not proc.stderr.closed],
        daemon=True,
    ).start()
    capabilities = {"fs": {"readTextFile": False, "writeTextFile": False},
                    "terminal": False}
    init_meta = parse_init_meta(getattr(args, "init_meta", "") or "")
    if init_meta:
        capabilities["_meta"] = init_meta
    response = wait(send("initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "clientCapabilities": capabilities,
    }), 15.0)
    if response is None:
        result["error"] = {"code": "acp-initialize-timeout"}
    elif "error" in response:
        result["error"] = {"code": "acp-initialize-failed", "detail": response["error"]}
    else:
        init = response.get("result") or {}
        result["protocol_version"] = init.get("protocolVersion")
        result["agent_info"] = init.get("agentInfo") or {}
        caps = init.get("agentCapabilities") or {}
        session_caps = caps.get("sessionCapabilities") or {}
        result["capabilities"] = {
            "prompt": True,
            "cancel": True,
            "permission": True,
            "load_session": capability_supported(caps, "loadSession"),
            "resume": capability_supported(session_caps, "resume"),
            "list": capability_supported(session_caps, "list"),
            "close": capability_supported(session_caps, "close"),
            "set_config_option": True,
        }
        result["auth_methods"] = init.get("authMethods") or []
        if result["protocol_version"] != PROTOCOL_VERSION:
            result["error"] = {"code": "acp-protocol-version-unsupported",
                               "agent_version": result["protocol_version"]}
        else:
            response = wait(send("session/new", {"cwd": args.repo, "mcpServers": []}), 15.0)
            if response and "error" in response:
                message = str((response["error"] or {}).get("message", "")).lower()
                if "auth" in message or (response["error"] or {}).get("code") in (-32000, -32001):
                    result["login_required"] = True
                else:
                    result["error"] = {"code": "acp-session-failed",
                                       "detail": response["error"]}
            elif response:
                result["login_required"] = False
                session_result = response.get("result") or {}
                result["session_probe"] = session_result.get("sessionId")
                options = session_result.get("configOptions")
                if isinstance(options, list):
                    result["config_option_ids"] = [
                        option.get("id")
                        for option in options
                        if isinstance(option, dict) and option.get("id") is not None
                    ]
                    result["config_options"] = [
                        {
                            "id": option.get("id"),
                            "name": option.get("name"),
                            "type": option.get("type"),
                            "current": option.get("currentValue"),
                            "values": [
                                entry.get("value")
                                for entry in option.get("options") or []
                                if isinstance(entry, dict)
                            ],
                        }
                        for option in options
                        if isinstance(option, dict)
                    ]
                if result["capabilities"]["close"] and result.get("session_probe"):
                    wait(send("session/close",
                              {"sessionId": result["session_probe"]}), 5.0)
            else:
                result["error"] = {"code": "acp-session-timeout"}
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = proc.pid
    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=EXIT_GRACE)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=TERM_GRACE)
        except subprocess.TimeoutExpired:
            os.killpg(pgid, signal.SIGKILL)
    print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-dir")
    parser.add_argument("--socket")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--session", default="")
    parser.add_argument("--command", required=True)
    parser.add_argument("--resume")
    parser.add_argument("--continue", dest="use_continue", action="store_true")
    parser.add_argument("--init-meta", default="")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        return run_probe(args)
    holder = Holder(args)
    return holder.run()


if __name__ == "__main__":
    raise SystemExit(main())
