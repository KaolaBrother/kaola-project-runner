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
import importlib.util
import hashlib
import json
import os
import queue
import re
import secrets
import select
import shlex
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
IDLE_EXIT_SECONDS = 600
# Issue #278: shared paths also ship beside every generated worker Runner.
_paths_spec = importlib.util.spec_from_file_location(
    "kaola_acp_paths", Path(__file__).resolve().with_name("kaola-acp-paths.py"))
acp_paths = importlib.util.module_from_spec(_paths_spec)
_paths_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    _paths_spec.loader.exec_module(acp_paths)
finally:
    sys.dont_write_bytecode = _paths_bytecode

STDERR_RING = 64 * 1024
EVENT_LOG_MAX = 10 * 1024 * 1024
EVENT_LOG_KEEP = 3
CANCEL_GRACE = 5.0
# Bounds the receipt wait. A standard prompt can answer after a later step or
# turn. Its late reply remains in the existing event log; never resend on timeout.
STEER_TIMEOUT = 30.0
EXIT_GRACE = 5.0
TERM_GRACE = 3.0
# Issue #146: the shared session/new wait; a manifest `acp_session_new_timeout`
# overrides it per platform (codex measured past 15 s on live starts).
SESSION_NEW_TIMEOUT = 15.0
# Issue #203: ceiling for the start selection/application evidence a record keeps.
START_EVIDENCE_BYTES = 16384
SENSITIVE_KEYS = ("_API_KEY", "TOKEN", "Authorization")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_id(value: Any) -> str:
    return str(value)


def worker_event_id(params: dict[str, Any]) -> str:
    """The ``event_id`` the Host derives from these carrier params.

    The same four fields ``op_worker_event`` builds it from, so a worker can
    check that an accepting receipt names the event it actually sent instead of
    trusting any string that happens to be there (Issue #92).
    """
    return (f"{params.get('platform')}/{params.get('session')}"
            f"/{params.get('kind')}/{params.get('event_cursor')}")


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


class _BsdInfo(ctypes.Structure):
    """``struct proc_bsdinfo`` (``PROC_PIDTBSDINFO``), 136 bytes on macOS."""
    _fields_ = [("flags", ctypes.c_uint32), ("status", ctypes.c_uint32),
                ("xstatus", ctypes.c_uint32), ("pid", ctypes.c_uint32),
                ("ppid", ctypes.c_uint32), ("ids", ctypes.c_uint32 * 7),
                ("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32),
                ("nfiles", ctypes.c_uint32), ("pgid", ctypes.c_uint32),
                ("pjobc", ctypes.c_uint32), ("e_tdev", ctypes.c_uint32),
                ("e_tpgid", ctypes.c_uint32), ("nice", ctypes.c_int32),
                ("start_tvsec", ctypes.c_uint64), ("start_tvusec", ctypes.c_uint64)]


def libproc_ps(columns: list[str]) -> str | None:
    """``ps -axo <columns>`` text built from libproc, for the columns pid,
    ppid, pgid, state and lstart; ``None`` off macOS or when libproc is
    unreadable. Only processes this user may inspect are listed."""
    if sys.platform != "darwin":
        return None
    try:
        lib = ctypes.CDLL("/usr/lib/libproc.dylib")
        count = lib.proc_listallpids(None, 0)
        pids = (ctypes.c_int * (max(count, 0) + 256))()
        count = lib.proc_listallpids(pids, ctypes.sizeof(pids))
    except (OSError, AttributeError):
        return None
    if count <= 0:
        return None
    lines = []
    for pid in pids[:count]:
        info = _BsdInfo()
        size = ctypes.sizeof(info)
        if lib.proc_pidinfo(pid, 3, ctypes.c_uint64(0), ctypes.byref(info), size) != size:
            continue
        values = {"pid": str(pid), "ppid": str(info.ppid), "pgid": str(info.pgid),
                  "state": "Z" if info.status == 5 else "S",
                  "lstart": time.strftime("%a %b %e %H:%M:%S %Y",
                                          time.localtime(info.start_tvsec))}
        lines.append(" ".join(values[column] for column in columns))
    return "\n".join(lines) + "\n"


def run_ps(columns: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """``ps -axo <columns=...>``. Issue #120: under a Seatbelt profile (a dsh
    Host's shell tool) the setuid ``/bin/ps`` cannot exec at all, and the
    uncaught error killed ``stop`` mid-reply; the same columns then come from
    libproc. A table neither source can read has returncode 1."""
    argv = ["ps", "-axo", ",".join(f"{column}=" for column in columns)]
    try:
        return subprocess.run(argv, capture_output=True, text=True, env=env)
    except OSError as exc:
        text = libproc_ps(columns)
        return subprocess.CompletedProcess(argv, 1 if text is None else 0,
                                           stdout=text or "", stderr=str(exc))


def process_table() -> list[tuple[int, int, int, str]]:
    """Live (non-zombie) processes as (pid, ppid, pgid, start time). ``ps``
    renders ``lstart`` in the caller's locale on macOS; pin C so the text is
    the ctime layout ``start_epoch`` parses and stays comparable between the
    holder that recorded it and a later CLI process under another locale."""
    result = run_ps(["pid", "ppid", "pgid", "state", "lstart"], env=PS_ENV)
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
# writer, never a periodic scheduler. Issue #87: a 33rd detailed event is
# refused as queue-full and recorded as one monotonic full-check generation
# in that same log so the next heartbeat still wakes a real-status /
# pending-approval pass (remind only). Issue #119: any platform whose
# manifest declares a measured ``host_skill_entry`` can host; the carrier op is
# refused on a holder that was started without one.
HEARTBEAT_HOST_ENV = "KAOLA_ACP_HEARTBEAT_HOST"
HEARTBEAT_HOST_SOCKET_ENV = "KAOLA_ACP_HEARTBEAT_HOST_SOCKET"
# Issue #104 (design #99 §a.1): set by this holder for the agent it hosts.
# Identity only - holder_instance_id, platform, repo, session - so a nested
# `kaola-acp start` run by that agent can derive and verify its notification
# binding to this holder. Never a socket, record path, or pid.
DISPATCHER_ENV = "KAOLA_ACP_DISPATCHER"
HEARTBEAT_EVENT_CAP = 32
# Issue #92: the codes that mean the Host never TOOK the event - it was not
# listening, hung up, answered something that is not a worker_event receipt, or
# is an older build with no such op at all. Only these leave a permission wake
# owed, and each of them can still come good when the Host comes back. Any
# other receipt is the Host's own answer - it staged the event, recognised it
# as a duplicate, or refused it knowing what it refused - and an answered event
# is settled whether or not the answer was a yes. Of the refusals only
# `worker-event-queue-full` records anything Host-side, and what it records is
# the overflow full-check that drives a full pending-approval pass anyway.
CARRIER_UNDELIVERED_CODES = ("host-unreachable", "host-closed", "host-reply-invalid",
                            "unknown-op")
HEARTBEAT_NOTIFY_TIMEOUT = 5.0
IDLE_WAKE_KEY = "idle"
# Issue #255: the relay send runs under ``worker_events_lock``, which a worker's
# own carrier send waits on before its event is staged. A non-waiting prompt
# admission answers at once; bounding the relay well under the worker's 5 s
# carrier timeout keeps a slow Sideagent from timing out a worker idle (an
# unreachable Sideagent falls back to the Host). It is one deadline for the
# whole round trip (connect, send, every receive), so a peer that trickles
# bytes without a newline cannot extend it.
RELAY_SEND_TIMEOUT = 1.0
HEARTBEAT_NOTIFY_GRACE = 6.0
WORKER_EVENT_SCHEMA = "kaola-worker-event/1"
WORKER_EVENT_KINDS = ("terminated", "idle", "permission_required")
HEARTBEAT_DEFECT_CHARS = 200
# Injection bound for the Host-maintained prompt file. Not a second Skill
# budget: one read of at most this many bytes plus one, so an oversized file
# cannot dump an arbitrary body into session/prompt.
HEARTBEAT_PROMPT_MAX_BYTES = 65536
# Issue #255: a lifecycle-state file carries structured state beside its
# projected `body`. This holder reads that whole file within this bound and
# still injects at most HEARTBEAT_PROMPT_MAX_BYTES of `body`. It advertises the
# format in its record so the state tool writes past 64KiB only for a Host
# holder that can read it.
HEARTBEAT_STATE_FILE_MAX_BYTES = 1048576
HEARTBEAT_STATE_SCHEMA = "kaola-heartbeat-prompt/2"
HOLDER_FEATURES = ("heartbeat-state/2", "sideagent-relay/1", "preserve-dispatched/1", "steer-after-turn/1",
                   "sideagent-node/1", "project-compact-notice/1", "host-compact-maintenance/1")
# Issue #255 node mode: the Host carrier starts one fresh maintenance node per
# batch from the binding's exact Runner argv (never a shell string), and
# exact-stops it after its turn end. Bounds on that one start and stop only.
NODE_START_TIMEOUT = 180.0
NODE_STOP_CONFIRM_SECONDS = 30.0
# A carrier's own stop waits this long for a node start in flight and for the
# node stop, inside the Runner's 30 s stop request.
NODE_RECLAIM_SECONDS = 8.0
SIDEAGENT_ROLES = ("sideagent", "sidekick")
RELAY_SCHEMA = "kaola-sideagent-relay/1"
OVERFLOW_FULL_CHECK_MARK = "kaola-host-notify/overflow-full-check"
# Issue #94: every turn-opening prompt to a ZCode Host opens with the native
# Skill command on its own first line so the Skill tool reloads the Project
# Runner body for this turn - startup, resume, heartbeat, and post-compaction
# alike. A busy `steer` guide is forwarded into the running turn instead and
# is no new Skill invocation. The envelope owns this line; the Host's
# heartbeat `body` does not carry it. Issue #119: this is the ZCode value and
# the fallback for a holder spawned without --host-entry; every other platform
# hands its own measured manifest line through --host-entry.
HOST_SKILL_ENTRY = "/kaola-project-runner"
# Issue #90: how many recently confirmed worker event ids stay remembered, so a
# worker retrying the same deterministic event_id after a confirmed Host turn is
# answered as a duplicate instead of prompting the Host again. A retry follows
# its own notify timeout, not thousands of events later, and the event log that
# backs this memory rotates anyway.
HEARTBEAT_CONFIRMED_MEMORY = 8 * HEARTBEAT_EVENT_CAP



def parse_dispatcher() -> dict[str, str] | None:
    """The dispatching holder's identity this holder inherited, or None."""
    try:
        value = json.loads(os.environ.get(DISPATCHER_ENV) or "null")
    except ValueError:
        return None
    if not isinstance(value, dict):
        return None
    keys = ("holder_instance_id", "platform", "repo", "session")
    if not all(isinstance(value.get(key), str) and value[key] for key in keys):
        return None
    return {key: value[key] for key in keys}


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
    if (not isinstance(target, dict) or not isinstance(target.get("platform"), str)
            or not target["platform"]
            or not isinstance(target.get("session"), str) or not target["session"]
            or not isinstance(target.get("repo"), str) or not target["repo"]
            or not socket_path or not os.path.isabs(socket_path)):
        sys.stderr.write(f"[kaola-acp-holder] invalid {HEARTBEAT_HOST_ENV}: "
                         "heartbeat carrier disabled\n")
        return None
    return {"platform": target["platform"], "session": target["session"],
            "repo": target["repo"], "socket": socket_path}


def heartbeat_prompt_body(source: Path) -> tuple[str | None, str | None]:
    """``(body, defect)`` of :func:`read_heartbeat_file`."""
    _, body, defect = read_heartbeat_file(source)
    return body, defect


def attention_fingerprint(body: str | None) -> str | None:
    """Fingerprint of the projected Host view's `attention` list, or None
    for a body that is not a lifecycle-state projection."""
    try:
        view = json.loads(body or "")
    except ValueError:
        return None
    if not isinstance(view, dict) or view.get("view") != "host" or not isinstance(view.get("attention"), list):
        return None
    text = json.dumps(view["attention"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_heartbeat_file(source: Path) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """``(document, body, defect)`` from exactly ONE bounded read of the heartbeat prompt file.

    Issue #66: one read, so the body that was checked is the body that is
    delivered - a check-then-reread would let a rewrite between the two ship
    something the checks never saw. An absent file is not a defect, it is the
    honest fallback; anything else that cannot supply a prompt comes back as
    its real defect so the Host fixes the file instead of assuming its own
    prompt is in effect. Issue #87: oversized bytes are a named defect and are
    never injected, including as a truncated-looking body. Issue #255: the
    file read is capped at ``HEARTBEAT_STATE_FILE_MAX_BYTES`` so structured
    lifecycle state fits beside its projection, and the injected ``body``
    itself is still capped at ``HEARTBEAT_PROMPT_MAX_BYTES``.
    Read-only, bounded, never fatal.
    """
    try:
        with source.open("rb") as handle:
            raw = handle.read(HEARTBEAT_STATE_FILE_MAX_BYTES + 1)
    except FileNotFoundError:
        return None, None, None
    except OSError as exc:
        return None, None, f"unreadable: {getattr(exc, 'strerror', None) or exc}"[
            :HEARTBEAT_DEFECT_CHARS]
    if len(raw) > HEARTBEAT_STATE_FILE_MAX_BYTES:
        return None, None, (
            f"file exceeds {HEARTBEAT_STATE_FILE_MAX_BYTES} bytes; retire finished "
            f"records in {source.name} so its \"body\" stays at or under "
            f"{HEARTBEAT_PROMPT_MAX_BYTES} bytes. oversized bytes were not injected"
        )[:HEARTBEAT_DEFECT_CHARS]
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        return None, None, f"unreadable: {getattr(exc, 'strerror', None) or exc}"[
            :HEARTBEAT_DEFECT_CHARS]
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, None, f"not valid JSON: {exc}"[:HEARTBEAT_DEFECT_CHARS]
    if not isinstance(data, dict):
        return None, None, f'JSON {type(data).__name__}, not an object with a "body" field'
    if (data.get("schema") == HEARTBEAT_STATE_SCHEMA and isinstance(data.get("state"), dict)):
        record = _RECORD if _RECORD not in (None, False) else None
        if record is None or not hasattr(record, "injection_body"):
            return data, None, (
                "record contract is not loaded; the stored body was not injected"
            )[:HEARTBEAT_DEFECT_CHARS]
        projected, defect = record.injection_body(data, source)
        if defect:
            return data, None, defect[:HEARTBEAT_DEFECT_CHARS]
        if isinstance(projected, str) and projected:
            return data, projected, None
        return data, None, (
            "projected Host view is empty; the stored body was not injected"
        )[:HEARTBEAT_DEFECT_CHARS]
    if "body" not in data:
        present = ", ".join(sorted(key for key in data if isinstance(key, str))[:8])
        return data, None, (f'no "body" field (top-level fields present: {present or "none"})'
                            )[:HEARTBEAT_DEFECT_CHARS]
    value = data["body"]
    if not isinstance(value, str):
        return data, None, f'"body" is {type(value).__name__}, not a string'
    if not value:
        return data, None, '"body" is an empty string'
    if len(value.encode("utf-8")) > HEARTBEAT_PROMPT_MAX_BYTES:
        return data, None, (
            f"\"body\" exceeds {HEARTBEAT_PROMPT_MAX_BYTES} bytes; rewrite it as the "
            "projected Host view at or under that size. oversized bytes were not injected"
        )[:HEARTBEAT_DEFECT_CHARS]
    return data, value, None
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


HOLDER_RECORD_DIR_ARG = re.compile(r" --record-dir (.+?) --socket ")


def own_holder_record(pid: int) -> dict[str, Any] | None:
    """The record a live Runner holder ``pid`` writes under its own
    ``--record-dir``, only when that record names ``pid`` as its holder."""
    try:
        output = run_ps(["pid", "command"]).stdout
    except KeyError:
        return None
    for line in output.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or fields[0] != str(pid):
            continue
        match = HOLDER_RECORD_DIR_ARG.search(f" {fields[1]} ")
        if match is None:
            return None
        try:
            record = json.loads((Path(match.group(1)) / "record.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return record if isinstance(record, dict) and record.get("holder_pid") == pid else None
    return None


def worker_tree_groups(holder_pid: int, holder_pgid: int,
                       table: list[tuple[int, int, int, str]]) -> set[int]:
    """Every process group of one live Runner worker: the holder's own group,
    each group a live descendant runs in (the native agent leads its own
    session, its tools may too), and the agent and child groups the worker's
    own record attests while a recorded member identity still holds (a tool
    whose parent already exited is no longer a descendant)."""
    by_pid = {pid: (pgid, started) for pid, _, pgid, started in table}
    found = {holder_pgid, *child_groups(holder_pid, holder_pgid, table)}
    record = own_holder_record(holder_pid)
    if record is None:
        return found
    agent_pgid, agent_started = record.get("agent_pgid"), record.get("agent_started")
    leader = by_pid.get(agent_pgid) if isinstance(agent_pgid, int) else None
    if (leader is not None and leader[0] == agent_pgid
            and isinstance(agent_started, (int, float)) and not isinstance(agent_started, bool)):
        started = start_epoch(leader[1])
        if started is not None and abs(started - agent_started) <= SPAWN_RECORD_SLACK:
            found.add(agent_pgid)
    for child, members in (record.get("agent_child_groups") or {}).items():
        if str(child).isdigit() and any(
                str(pid).isdigit() and by_pid.get(int(pid)) == (int(child), started)
                for pid, started in (members or {}).items()):
            found.add(int(child))
    return found


def is_turn_end(event: dict[str, Any]) -> bool:
    """A Sideagent holder's turn-end idle naming its holder and turn."""
    return bool(event.get("kind") == "idle" and event.get("holder_instance_id")
                and event.get("turn_fingerprint"))


def holders_dispatched_by(holder_instance_id: Any) -> list[int]:
    """Live Runner holders whose own record (under the ``--record-dir`` of
    their own argv, naming them as ``holder_pid``) names this holder instance
    as their ``dispatcher``. That record field comes from the
    ``KAOLA_ACP_DISPATCHER`` the start inherited, which reaches a worker even
    where ``KAOLA_ACP_CHILD_RECORD`` does not (the ZCode bridge forwards only
    its allowlist)."""
    if not isinstance(holder_instance_id, str) or not holder_instance_id:
        return []
    try:
        output = run_ps(["pid", "command"]).stdout
    except KeyError:
        return []
    found = []
    for line in output.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or not fields[0].isdigit() or "kaola-acp-holder" not in fields[1]:
            continue
        match = HOLDER_RECORD_DIR_ARG.search(f" {fields[1]} ")
        if match is None:
            continue
        try:
            record = json.loads((Path(match.group(1)) / "record.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(record, dict):
            continue
        dispatcher = record.get("dispatcher")
        if (record.get("holder_pid") == int(fields[0]) and isinstance(dispatcher, dict)
                and dispatcher.get("holder_instance_id") == holder_instance_id):
            found.append(int(fields[0]))
    return found


def dispatched_worker_groups(path: Path, live: dict[int, list[int]],
                             table: list[tuple[int, int, int, str]] | None = None,
                             holder_instance_id: str | None = None) -> set[int]:
    """Issue #255: the groups of ``live`` that belong to a Runner worker this
    agent started. A worker counts by its exact spawn-record identity (only a
    Runner `start` writes that record; pid, pgid and spawn time must still
    hold) or by its own live record naming this holder instance as its
    dispatcher; its whole process tree is kept, never only the holder."""
    table = table if table is not None else process_table()
    by_pid = {pid: pgid for pid, _, pgid, _ in table}
    roots = {entry["pid"]: entry["pgid"] for entry, _ in live_spawn_entries(path, table)}
    for pid in holders_dispatched_by(holder_instance_id):
        if pid in by_pid:
            roots.setdefault(pid, by_pid[pid])
    found: set[int] = set()
    for pid, pgid in roots.items():
        found |= worker_tree_groups(pid, pgid, table)
    return found & set(live)


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
    result = run_ps(["pid", "pgid", "state"])
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


def config_option_choices(option: dict) -> list[dict]:
    """Every selectable leaf choice of an ACP ``select`` config option.

    An agent may present its choices flat or grouped: dsh's ``model`` option
    lists one entry per provider, each holding the real choices in its own
    nested ``options``. A group entry carries no ``value``, so reading one as a
    choice reports a nameless option per group instead of the routes the Agent
    can actually select. The ACP schema nests exactly one level
    (``SessionConfigSelectOptions`` is a list of options *or* a list of
    groups), so one level is expanded and a choice with no ``value`` is
    omitted rather than reported as null.
    """
    choices: list[dict] = []
    for entry in option.get("options") or []:
        if not isinstance(entry, dict):
            continue
        nested = entry.get("options")
        if isinstance(nested, list):
            choices.extend(
                member for member in nested
                if isinstance(member, dict) and member.get("value") is not None
            )
        elif entry.get("value") is not None:
            choices.append(entry)
    return choices


def config_option_values(option: dict) -> list[Any]:
    """Every selectable value of an ACP ``select`` config option."""
    return [choice["value"] for choice in config_option_choices(option)]


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

    def append(self, event: dict[str, Any], ts: float | None = None) -> int:
        """``ts`` lets a caller stamp the view with the same time this line gets."""
        with self.lock:
            self.cursor += 1
            if self.oldest is None:
                self.oldest = self.cursor
            stamp = round(time.time(), 3) if ts is None else ts
            entry = {"cursor": self.cursor, "ts": stamp, **scrub(event)}
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


def seatbelt_confined() -> bool | None:
    """Issue #120: whether this holder (and so every agent it spawns) runs under
    a macOS Seatbelt profile. Seatbelt is inherited by every descendant and no
    new session escapes it, so a worker started from a Host whose shell tool is
    confined (dsh's ``workspace-write``) cannot write outside that Host's
    writable roots. ``None`` off macOS or when ``sandbox_check`` is unreadable.
    A fact, never a gate."""
    if sys.platform != "darwin":
        return None
    try:
        check = ctypes.CDLL("/usr/lib/libSystem.B.dylib").sandbox_check
    except (OSError, AttributeError):
        return None
    check.restype = ctypes.c_int
    check.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    return bool(check(os.getpid(), None, 0))


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
        # Issue #174: a request frame write that failed. The exit it predicts
        # may not be observed yet, so a boot failure is classified and its
        # stderr drained from this fact plus the exit, never from a slot
        # lookup that races either.
        self.stdin_write_failed = False
        self.malformed_lines = 0
        self.unknown_updates = 0
        self.handler_errors = 0

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
        # Name this holder to its agent (identity only) so a Runner `start`
        # the agent runs binds its worker back here mechanically (Issue #104).
        env[DISPATCHER_ENV] = json.dumps(self.holder.dispatcher_identity(), sort_keys=True)
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
        # Issue #132: the agent's own start time as epoch seconds (``lstart``
        # text is local time, so it would not compare across time zones), so
        # a sweep of this record after the holder is gone can tell the agent's
        # process group from an unrelated group that reused its id.
        self.holder.agent_started = next(
            (start_epoch(started) for pid, _ppid, _pgid, started in process_table()
             if pid == self.proc.pid), None)
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
            try:
                self.holder.on_agent_message(message)
            except Exception as exc:  # noqa: BLE001
                # Issue #95: one message's handler failure is that message's
                # failure. Without this the thread ends here, the agent stays
                # alive, and every later update and response is dropped in
                # silence. The failure is recorded, never answered.
                self.handler_errors += 1
                self.holder.note_agent_message_error(message, exc)

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
        frame = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        written = self.send_message(frame)
        if method == "initialize":
            self.holder.events.append({"kind": "initialize_request", "request": frame, "written": written})
        if not written:
            # Issue #174: remember the write failure on the connection. The
            # popped slot's resolution never reaches a waiter, so a boot that
            # fails here is classified from this fact, not from the missed
            # lookup that would otherwise read as a timeout.
            self.stdin_write_failed = True
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
_QUOTA = None
_RECORD = None


def quota_module():
    """Sibling quota catalog, or None when this holder copy has no ``kaola-quota.py``.

    The module object is cached. Callers must not be the first import after
    ``install-local`` has swapped this directory: ``load_sibling_modules``
    runs at startup so the bytes are the ones this process began with.
    """
    global _QUOTA
    if _QUOTA is False:
        return None
    if _QUOTA is None:
        path = Path(__file__).resolve().parent / "kaola-quota.py"
        if not path.is_file():
            _QUOTA = False
            return None
        spec = importlib.util.spec_from_file_location("kaola_quota_holder", path)
        if spec is None or spec.loader is None:
            _QUOTA = False
            return None
        module = importlib.util.module_from_spec(spec)
        # A generated Skill must stay byte-identical to the render. Importing the
        # sibling catalog must not drop a __pycache__ next to it.
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        _QUOTA = module
    return _QUOTA


def compact_module():
    """Sibling compact-recovery module, or None when this copy lacks it.

    Issue #264. The module object is cached at startup by
    ``load_sibling_modules`` so the bytes are the ones this process began
    with. ``False`` means the sibling is absent, not that no signal arrived.
    """
    global _COMPACT
    if _COMPACT is False:
        return None
    if _COMPACT is None:
        path = Path(__file__).resolve().parent / COMPACT_MODULE
        if not path.is_file():
            _COMPACT = False
            return None
        spec = importlib.util.spec_from_file_location("kaola_compact_recovery_holder", path)
        if spec is None or spec.loader is None:
            _COMPACT = False
            return None
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        _COMPACT = module
    return _COMPACT


# The sibling modules this holder imports. ``install-local`` replaces the Skill
# directory with ``os.replace``; a later import would execute the replacement
# and mix two builds in one holder, so the bytes are pinned at startup.
QUOTA_MODULE = "kaola-quota.py"
RECORD_MODULE = "kaola-record-contract.py"
# Issue #264: recognize a completed context compaction and owe one Skill
# reread. The module is optional at load time so an older install still runs;
# the behavior needs it present beside the holder.
COMPACT_MODULE = "kaola-compact-recovery.py"
# Native TUI hooks do not establish ACP-owned recovery. Codex 0.160.1 with
# codex-acp 2.0.1 completed compaction without invoking those hooks; ACP must
# deliver the bounded reload. Add an owner only with actual ACP route proof.
NATIVE_COMPACT_RECOVERY_PLATFORMS = frozenset()
RUNNER_BUILD_FILES = (
    "kaola-acp-holder.py",
    "kaola-acp-paths.py",
    "kaola-compact-recovery.py",
    "kaola-zcode-acp.py",
    "kaola-opencode-acp.py",
    "kaola-dsh-acp.py",
    "kaola-dsh-steer.mjs",
    "kaola-opencode-steer.mjs",
    "kaola-acp.py",
    "kaola-quota.py",
    "kaola-record-contract.py",
    "kaola-tmux.sh",
    "platform.yaml",
)
_RUNNER_IDENTITY: dict[str, Any] | None = None
_COMPACT: Any = None


def _hex_revision(value: str) -> str | None:
    if len(value) == 40 and all(character in "0123456789abcdef" for character in value):
        return value
    return None


def _snapshot_file(found: dict[str, dict[str, str]], key: str, path: Path) -> None:
    try:
        data = path.read_bytes()
    except OSError:
        return
    found[key] = {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}


def capture_script_paths() -> dict[str, dict[str, str]]:
    """Absolute path and sha256 of the runner files beside this process, read now.

    Includes the restart-required set (holder, ZCode bridge, adapters, platform
    manifest) and the per-call CLI files, which are reported and do not by
    themselves require a restart.
    """
    script_dir = Path(__file__).resolve().parent
    found: dict[str, dict[str, str]] = {}
    for name in RUNNER_BUILD_FILES:
        _snapshot_file(found, name, script_dir / name)
    adapters = script_dir / "adapters"
    if adapters.is_dir():
        for path in sorted(adapters.glob("*.sh")):
            _snapshot_file(found, f"adapters/{path.name}", path)
    checkout = script_dir.parent
    if (checkout / "platforms").is_dir() and not (checkout / "SKILL.md").is_file():
        for path in sorted((checkout / "platforms").glob("*.yaml")):
            _snapshot_file(found, f"platforms/{path.name}", path)
    return found


def _import_sibling(name: str):
    """Load one sibling module from this process's directory. None when absent."""
    path = Path(__file__).resolve().parent / name
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(
        "kaola_holder_" + name[:-3].replace("-", "_"), path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # A generated Skill must stay byte-identical to the render. Importing a
    # sibling must not drop a __pycache__ next to it.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def load_sibling_modules() -> None:
    """Import the quota sibling and snapshot script bytes.

    Issue #162: a running holder must not import a sibling on a later request
    after ``install-local`` has swapped the directory. ``runner_build`` is the
    holder file this process executes, not the per-call CLI.
    """
    global _QUOTA, _RECORD, _COMPACT, _RUNNER_IDENTITY
    module = _import_sibling(QUOTA_MODULE)
    _QUOTA = module if module is not None else False
    record = _import_sibling(RECORD_MODULE)
    _RECORD = record if record is not None else False
    compact = _import_sibling(COMPACT_MODULE)
    _COMPACT = compact if compact is not None else False
    paths = capture_script_paths()
    primary = paths.get("kaola-acp-holder.py") or {}
    digest = primary.get("sha256") or ""
    _RUNNER_IDENTITY = {
        "runner_build": digest[:12] or None,
        "script_paths": paths,
    }


load_sibling_modules()


def runner_identity(accepted_revision: str = "") -> dict[str, Any]:
    """Build identity pinned at import, plus the accepted revision from argv.

    ``start`` passes ``--accepted-revision`` on the holder argv only. It is not
    exported to the agent. The script digests stay the startup snapshot.
    """
    pinned = _RUNNER_IDENTITY or {"runner_build": None, "script_paths": capture_script_paths()}
    return {
        "runner_build": pinned.get("runner_build"),
        "accepted_revision": _hex_revision(accepted_revision or ""),
        "script_paths": pinned.get("script_paths") or {},
    }
FOLLOW_QUEUE_CAP = 256
FOLLOW_HEARTBEAT_SECONDS = 5.0
FOLLOW_SNDBUF = 4096
FOLLOW_DROP_GRACE = 2.0
FOLLOW_WRITE_OPS = frozenset({"prompt", "steer", "steer_interrupt", "permit",
                              "cancel", "stop"})


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


def permission_options_view(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"optionId": opt.get("id"), "name": opt.get("label"), "kind": opt.get("kind")}
        for opt in entry.get("options") or []
    ]


def answered_permission_view(
    entry: dict[str, Any], option: Any, answered_at: float, cursor: int
) -> dict[str, Any]:
    """One answer this holder wrote to the agent. ``option`` None means cancelled.

    ``outcome`` reads the chosen option's ACP ``kind``: ``allow_*`` is approved,
    ``reject_*`` is denied. An option id the agent did not offer, or a kind
    outside those two families, is ``unknown``.
    """
    options = permission_options_view(entry)
    chosen = None
    outcome = "cancelled"
    if option is not None:
        chosen = next((opt for opt in options if opt["optionId"] == option), None)
        if chosen is None:
            chosen = {"optionId": str(option), "name": None, "kind": None}
        kind = str(chosen.get("kind") or "")
        outcome = ("approved" if kind.startswith("allow")
                   else "denied" if kind.startswith("reject") else "unknown")
    request_id = entry.get("request_id")
    return {
        "request_id": "" if request_id is None else str(request_id),
        "title": entry.get("title"),
        "tool_call_id": entry.get("tool_call_id"),
        "options": options,
        "chosen_option": copy.deepcopy(chosen),
        "outcome": outcome,
        "answered_at": answered_at,
        "cursor": cursor,
    }


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
        self.turns: list[dict[str, Any]] = []
        self.turns_dropped = False
        self.answered_permissions: list[dict[str, Any]] = []
        self.answered_dropped = False
        self._prompt_texts: list[str] = []
        # The last appended message; chunks without messageId append to it
        # until a tool call, a new prompt, or turn end closes it.
        self._open_message: dict[str, Any] | None = None

    def add_user_from_prompt(self, text: str, cursor: int, started_at: float | None = None) -> None:
        """The prompt opens a turn. Its message has no event-log line, so no ``received_at``."""
        with self.lock:
            self._prompt_texts.append(text)
            self._open_message = None
            self._add_message_locked("user", text, None, cursor, None)
            self.turns.append({
                "started_at": started_at,
                "ended_at": None,
                "outcome": None,
                "stop_reason": None,
                "start_cursor": cursor,
                "end_cursor": None,
            })
            if len(self.turns) > TIMELINE_MAX:
                del self.turns[: len(self.turns) - TIMELINE_MAX]
                self.turns_dropped = True

    def end_turn(self, ended_at: float, cursor: int, outcome: Any, stop_reason: Any) -> None:
        with self.lock:
            self._open_message = None
            if self.turns and self.turns[-1]["ended_at"] is None:
                self.turns[-1].update({
                    "ended_at": ended_at,
                    "outcome": outcome,
                    "stop_reason": stop_reason,
                    "end_cursor": cursor,
                })

    def add_answered_permission(self, answered: dict[str, Any]) -> None:
        with self.lock:
            self.answered_permissions.append(answered)
            if len(self.answered_permissions) > TIMELINE_MAX:
                del self.answered_permissions[: len(self.answered_permissions) - TIMELINE_MAX]
                self.answered_dropped = True

    def close_message(self) -> None:
        with self.lock:
            self._open_message = None

    def apply(self, update: dict[str, Any], cursor: int, received_at: float | None = None) -> None:
        variant = update.get("sessionUpdate", "unknown")
        with self.lock:
            if variant == "agent_message_chunk":
                message_id = update.get("messageId")
                if message_id is not None:
                    message_id = str(message_id)
                self._add_message_locked(
                    "assistant", _as_text(update.get("content")), message_id, cursor,
                    received_at,
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
                self._add_message_locked("user", text, message_id, cursor, received_at)
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
        self, role: str, text: str, message_id: str | None, cursor: int,
        received_at: float | None,
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
            "received_at": received_at,
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
                "turns": self.turns,
                "turns_dropped": self.turns_dropped,
                "answered_permissions": self.answered_permissions,
                "answered_dropped": self.answered_dropped,
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


# Sideagent session identity; retain sidekick for legacy records and callers.
SESSION_ROLES = frozenset({"host", "sideagent", "sidekick", "expert", "elite", "worker"})


def normalize_session_role(raw: Any) -> str | None:
    """Map a spawn value to one known role or null. Reject every other value."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("session-role")
    text = raw.strip().lower()
    if text in ("", "null", "none"):
        return None
    if text in SESSION_ROLES:
        return text
    raise ValueError(text)


class Holder:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.init_meta = parse_init_meta(getattr(args, "init_meta", "") or "")
        self.record_dir = Path(args.record_dir)
        # Runner layout has a shared root; direct custom holder fixtures may
        # instead supply the private record directory itself as their root.
        root = self.record_dir
        if (root.parent.name == args.session
                and root.parent.parent.name == args.platform):
            root = root.parent.parent.parent
        acp_paths.prepare_record_directory(self.record_dir, root)
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
        self.overflow_generation = 0
        self.overflow_confirmed_generation = 0
        self.overflow_inflight_generation: int | None = None
        self.overflow_inflight_fingerprint: Any = None
        # Issue #90: a bounded in-memory CACHE over this holder's own
        # `worker_event_confirmed` records, mapping each confirmed id to the
        # event-log cursor its newest confirmation was recorded at, so
        # `op_worker_event` can recognise a retry of an event a completed Host
        # turn already confirmed and removed from the pending list. Not a second
        # ledger - the event log stays the only persistence. The cursor is what
        # keeps a cache hit honest: once rotation has dropped that record the
        # holder can no longer show the confirmation, so the cache must stop
        # claiming it. A miss is resolved against the records themselves
        # whenever this cache is no longer their complete summary.
        self.confirmed_worker_events: dict[str, int] = {}
        self.confirmed_worker_events_partial = False
        # Issue #255: fingerprint of the Host-view `attention` last delivered
        # to this Host, so a bound Sideagent's routine turn end that changed
        # nothing needing a Host judgment does not wake the Host.
        self.host_attention_seen: str | None = None
        # Issue #264: one pending post-compaction reload and one scalar for the
        # last delivered occurrence. Not a queue, not a history store. The
        # inflight flag is a boolean, so an occurrence-less signal (Devin, Grok,
        # Kimi) still holds the slot; the id is evidence only.
        self.compact_reload = None
        # Opt-in project PreCompact notice; completion remains unconfirmed.
        self.compact_notice_pending: dict[str, Any] | None = None
        self.compact_reload_inflight = False
        self.compact_reload_inflight_id: str | None = None
        # Issue #264: the exact installed Skill file that this holder belongs to
        # (the platform worker Skill). A worker reload names this file, never
        # the Host control-plane entry.
        holder_script = Path(__file__).resolve()
        skill_root = holder_script.parent.parent
        skill_file = skill_root / "SKILL.md"
        self.installed_skill_path = str(skill_file) if skill_file.is_file() else None
        self.worker_events_lock = threading.Lock()
        self.heartbeat_notify_lock = threading.Lock()
        # Issue #92: the one worker event that cannot be re-derived later. A
        # pending permission keeps the turn ACTIVE, so no turn-end `idle` will
        # ever carry it; if the bound ZCode Host holder is not listening at the
        # moment it is raised, the single Issue #76 send is the only chance the
        # carrier ever gets and the wake is lost for good. Undelivered
        # `permission_required` events wait here, keyed by the request they
        # locate, and are re-offered from the holder's existing watchdog tick.
        # Not a second ledger and not a new scheduler: in-memory, no new thread,
        # and no finite give-up window - a wake lives exactly as long as the
        # request it belongs to and is dropped the moment that request stops
        # being answerable. Issue #255: a turn-end `idle` is held the same way
        # under one key, the newest turn replacing an older one, so a result
        # returned while the carrier is away still wakes the Host; it is
        # dropped only by an exact stop. `terminated` stays one-shot.
        self.undelivered_wakes: dict[str, dict[str, Any]] = {}
        self.undelivered_wakes_lock = threading.Lock()
        # Issue #255: the one maintenance node this carrier runs, in memory.
        self.node: dict[str, Any] = {}
        self.node_start: threading.Thread | None = None
        self.heartbeat_host = parse_heartbeat_host()
        self.dispatched_by = parse_dispatcher()
        # Issue #119: the turn-opening Skill entry line and display name this
        # holder carries as a Host. Empty entry = not a carrier Host.
        entry = getattr(args, "host_entry", None)
        if entry is None:
            entry = HOST_SKILL_ENTRY if args.platform == "zcode" else ""
        self.host_entry: str = entry
        self.host_name: str = (getattr(args, "host_name", None)
                               or ("ZCode" if args.platform == "zcode" else args.platform))
        # Issue #124: the launched CLI's own `--version` fact from `start`, for
        # a platform whose `initialize` returns no agentInfo; None elsewhere.
        try:
            cli_version = json.loads(getattr(args, "cli_version", "") or "null")
        except ValueError:
            cli_version = None
        self.cli_version: dict[str, Any] | None = (
            cli_version if isinstance(cli_version, dict) else None)
        # Issue #162: pinned at process start. write_record and op_state both
        # publish it so status/list can see which build this seat is running.
        # The revision and the start selection arrive on argv, not the agent env.
        self.runner_identity = runner_identity(getattr(args, "accepted_revision", "") or "")
        raw_selection = getattr(args, "start_selection", "") or ""
        try:
            parsed_selection = json.loads(raw_selection) if raw_selection else None
        except ValueError:
            parsed_selection = None
        self.start_selection = parsed_selection if isinstance(parsed_selection, dict) else None
        # Issue #245: spawn argv, already checked in main. A direct constructor
        # still normalizes; an unknown value does not start the agent.
        raw_role = getattr(args, "session_role", "")
        try:
            self.session_role = (
                raw_role if raw_role in SESSION_ROLES or raw_role is None
                else normalize_session_role(raw_role)
            )
        except ValueError as exc:
            raise SystemExit(2) from exc
        # Issue #203: the start's own selection/application evidence, handed in
        # once by `start` after it applied the config options. Held here so every
        # whole-record rewrite and every state reply carries it; None until then
        # and for a holder whose start never recorded it.
        self.start_evidence: dict[str, Any] | None = None
        # True only for a direct checkout invocation, which start does not
        # compare to installed Skills. A ~/.local/bin start resolves to the
        # same files and is not exempt; the parent passes the fact because
        # Path.resolve follows that link.
        flag = getattr(args, "baseline_exempt", "") or ""
        self.baseline_exempt = True if flag == "1" else False if flag == "0" else None

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
            # Issue #173: the turn's own structured failure, if the agent's
            # stream carried one (codex-acp `_meta.codex.threadStatus`). Cleared
            # to None by a later healthy status, so a recovered turn is healthy.
            "error": None,
            "final_text": "",
            "final_text_truncated": False,
            "thinking_chars": 0,
            "tool_calls": {},
            "tool_order": [],
            "failed_tools": [],
            "started_at": None,
            "ended_at": None,
            "cancel_requested": False,
        }

    def dispatcher_identity(self) -> dict[str, str]:
        """The four identity facts a nested start needs to bind to this holder."""
        return {
            "holder_instance_id": self.holder_instance_id,
            "platform": self.args.platform,
            "repo": self.args.repo,
            "session": self.args.session,
        }

    def write_record(self, **extra: Any) -> None:
        record = {
            "transport": "acp",
            "platform": self.args.platform,
            "session": self.args.session,
            "repo": self.args.repo,
            "holder_pid": os.getpid(),
            "socket_path": str(self.socket_path),
            "holder_instance_id": self.holder_instance_id,
            "runner_build": self.runner_identity["runner_build"],
            "accepted_revision": self.runner_identity["accepted_revision"],
            "script_paths": self.runner_identity["script_paths"],
            "start_selection": self.start_selection,
            "session_role": self.session_role,
            "start_evidence": self.start_evidence,
            "baseline_exempt": self.baseline_exempt,
            "agent_pid": self.agent.proc.pid if self.agent.proc else None,
            "agent_pgid": self.agent.proc.pid if self.agent.proc else None,
            "agent_started": getattr(self, "agent_started", None),
            "agent_child_pgids": sorted(self.agent_child_groups),
            "agent_child_groups": {str(pgid): {str(pid): started for pid, started in members.items()}
                                   for pgid, members in sorted(self.agent_child_groups.items())},
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "acp_session_id": self.acp_session_id,
            "session_meta": self.session_meta,
            "initial_config_options": self.initial_config_options,
            "protocol_version": self.protocol_version,
            "agent_info": self.agent_info,
            "cli_version": self.cli_version,
            "capabilities": self.capabilities,
            "holder_features": list(HOLDER_FEATURES),
            "state": self.state,
            # The target this holder really adopted at startup, or null for a
            # plain unbound worker. A surface without the key predates Issue #70
            # and is unknown, never evidence of being unbound.
            "heartbeat_host": self.heartbeat_host,
            # Issue #132: the Host holder that dispatched this one, from the
            # inherited KAOLA_ACP_DISPATCHER the start already verified, or
            # null for a start run under no holder. Its holder_instance_id
            # tells a live Host's own seats from a predecessor's.
            "dispatcher": getattr(self, "dispatched_by", None),
            "host_skill_entry": self.host_entry,
            "pending_permissions": list(self.pending_permissions.values()),
            "last_prompt": self.last_prompt,
            "event_cursor": self.events.cursor,
            "malformed_stdout_lines": self.agent.malformed_lines,
            "agent_message_errors": self.agent.handler_errors,
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
        if self.args.platform == "codex":
            capabilities["session"] = {"compaction": {}}
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
            if self.agent.stdin_write_failed:
                # Issue #174: the initialize frame was never written - the
                # agent was already dying when the send broke on its closed
                # stdin, and send_request pops the unwritten slot, so its
                # resolution never reaches this wait. That is a failed
                # start, not a timeout the agent never had the chance to
                # miss.
                return {"error": {"code": "acp-initialize-failed",
                                  "message": {"code": -32000, "message": "write failed"}}}
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
            # Issue #146: the platform's measured session/new latency sets this
            # wait (manifest `acp_session_new_timeout`, default 15 s).
            response = self.agent.wait_response(request_id, self.args.session_new_timeout)
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

    def note_agent_message_error(self, message: dict[str, Any],
                                 exc: BaseException) -> None:
        """Record a handler failure the reader refused to die on (Issue #95).

        Locator facts only: the method, the JSON-RPC id, the exception class,
        and the innermost frame. The message itself and ``str(exc)`` are both
        withheld because either can quote agent payload, which is where a
        credential would be; the frame is what makes the failure diagnosable
        without it. The message is not answered, not retried, and not counted
        as handled - an unanswered agent request stays unanswered, and the
        controlling Agent decides what to do from ``status``.

        Recording is best effort, not a guarantee: ``EventLog.append`` already
        absorbs an ``OSError``, so an unwritable or full log drops this line.
        The caller increments its counter BEFORE calling here, so ``status``
        still reports the failure when the line is the thing that is lost.
        """
        frames = traceback.extract_tb(exc.__traceback__)
        self.events.append({
            "kind": "agent_message_error",
            "method": message.get("method"),
            "id": message.get("id"),
            "error_type": type(exc).__name__,
            "at": f"{os.path.basename(frames[-1].filename)}:{frames[-1].lineno}"
                  if frames else None,
        })

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
            # Issue #264: Devin `_cognition.ai/compaction` and Grok
            # `_x.ai/session_notification` arrive as plain notifications.
            self._observe_compact_signal(message)

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
            key = normalize_id(request_id)
            is_new = key not in self.pending_permissions
            self.pending_permissions[key] = entry
            if self.turn["active"] and self.turn["mutation_status"] == "in_progress":
                self.turn["mutation_status"] = "accepted"
                self.note_agent_children()
            self.events.append({"kind": "request_permission", "request": entry})
            self.write_record()
            self.fanout_follow_delta()
            with self.turn_cond:
                self.turn_cond.notify_all()
            if is_new:
                # Issue #76: a bound worker blocked on approval cannot wait for
                # a turn-end idle that may never come. One wake per new pending
                # request; ``request_id`` is the only locator - title, options
                # and tool input stay in this worker's own receipts, and the
                # event approves nothing.
                self._notify_heartbeat_host_now(
                    "permission_required", "session/request_permission pending",
                    extra={"request_id": key})
                self._delegator_wake("blocked")
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
            if params.get("sessionId") in (None, self.acp_session_id):
                turn["context_usage"] = {"used": update.get("used"), "size": update.get("size")}
        elif variant == "config_option_update":
            if params.get("sessionId") in (None, self.acp_session_id):
                self._apply_config_options(
                    update.get("configOptions"), "config_option_update")
        elif variant not in KNOWN_UPDATES:
            self.agent.unknown_updates += 1
        # Issue #173: a SEPARATE `if`, deliberately not another `elif` - the
        # `session_info_update` variant must keep counting as unknown below, or
        # healthy receipts change. codex-acp 1.13.1 reports a failed turn only
        # here (`_meta.codex.threadStatus`), never in the prompt response, so
        # this is the only structured failure signal on the wire. Scoped to the
        # live turn of THIS session: another session's update is a sub-agent
        # child thread, and an update outside a turn belongs to no turn at all.
        # The LAST status in the turn wins, so a turn that recovers (idle) stays
        # healthy; only an explicit `systemError` marks it.
        if turn["active"] and params.get("sessionId") in (None, self.acp_session_id):
            thread_status = ((update.get("_meta") or {}).get("codex") or {}).get("threadStatus")
            if isinstance(thread_status, dict):
                turn["error"] = (
                    {"code": "agent-system-error", "threadStatus": thread_status["type"]}
                    if thread_status.get("type") == "systemError" else None
                )
        received_at = round(time.time(), 3)
        if variant != "usage_update" or params.get("sessionId") in (None, self.acp_session_id):
            self.projection.apply(update, self.events.cursor + 1, received_at)
        cursor = self.events.append({"kind": "session_update", "sessionId": params.get("sessionId"),
                                     "update": update}, ts=received_at)
        self.write_record()
        self.fanout_follow_delta()
        # Issue #264: recognize a completed compaction after it is durable.
        self._observe_compact_signal({"method": "session/update", "params": params})

    def on_prompt_response(self, request_id: int, response: dict[str, Any] | None) -> None:
        turn = self.turn
        if response is None or not turn["active"]:
            return
        if normalize_id(turn.get("request_id")) != normalize_id(request_id):
            # A late answer to a turn that is already over must not settle the
            # turn running now (Issue #65: same attribution boundary).
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
            # Issue #173: the agent answered `end_turn` even though the stream
            # carried a systemError (codex-acp maps a failed turn onto end_turn
            # when the AIR typed-failure capability is absent). `stop_reason`
            # stays verbatim - the log records what the agent sent (#113) - but
            # the outcome is the failure this holder actually observed.
            if stop == "cancelled":
                turn["outcome"] = "turn_canceled"
            elif turn.get("error"):
                turn["outcome"] = "turn_failed"
            else:
                turn["outcome"] = "turn_completed"
        turn["mutation_status"] = "completed"
        turn["active"] = False
        self.projection.close_message()
        outcome = turn["outcome"]
        # Issue #113: the turn's own stop reason, durable in the event log.
        # `record.json` only ever holds the LAST prompt, so a stop the next
        # prompt supersedes - an output-token maximum among them - would
        # otherwise leave nothing behind to count afterwards. Written verbatim:
        # whatever stopReason the agent reported is what the log says.
        turn["ended_at"] = round(time.time(), 3)
        end_cursor = self.events.append({"kind": "turn_ended", "outcome": outcome,
                                         "stop_reason": turn.get("stop_reason"),
                                         "prompt_fingerprint": turn.get("fingerprint")},
                                        ts=turn["ended_at"])
        self.projection.end_turn(turn["ended_at"], end_cursor, outcome, turn.get("stop_reason"))
        sideagent = self.session_role in SIDEAGENT_ROLES
        if ((outcome in ("turn_completed", "turn_failed") or (sideagent and outcome == "turn_canceled"))
                and not self.agent.exited.is_set()):
            # One business idle episode per ended turn with the agent alive;
            # the 600s idle_watcher stays a non-business exit timer.
            # Issue #255: a Sideagent's turn end (cancelled too) names its
            # holder, the turn and its outcome, so the Host holder settles
            # only the relay that turn carried, and only when it completed.
            extra = ({"holder_instance_id": self.holder_instance_id,
                      "turn_fingerprint": turn.get("fingerprint"), "turn_outcome": outcome}
                     if sideagent else None)
            self._notify_heartbeat_host_now(
                "idle", f"outcome={outcome} stop_reason={turn.get('stop_reason')}", extra)
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
        # Issue #299: the webhook wake mirrors the turn verdict. A canceled
        # turn under a requested stop is covered by op_stop's own "stopped".
        if outcome == "turn_failed":
            self._delegator_wake("error")
        elif outcome == "turn_completed" or (
                outcome == "turn_canceled" and not self.stop_requested):
            self._delegator_wake("end_turn")

    def on_agent_exit(self, code: int) -> None:
        reason = (f"exit_code={self.agent.exit_code}"
                  if self.agent.exit_code is not None
                  else f"exit_signal={self.agent.exit_signal}")
        # Before agent_exited: op_stop waits out the notify lock, so an exact
        # stop never kills a half-delivered worker-event notification.
        self._notify_heartbeat_host_now("terminated", reason)
        self.agent_exited.set()
        exited_at = round(time.time(), 3)
        exit_cursor = self.events.append({"kind": "process_exited", "code": self.agent.exit_code,
                                          "signal": self.agent.exit_signal}, ts=exited_at)
        turn = self.turn
        if turn["active"]:
            turn["outcome"] = "process_exited"
            turn["active"] = False
            turn["ended_at"] = exited_at
            self.projection.end_turn(exited_at, exit_cursor, "process_exited", None)
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
        # Issue #174: an exit during the boot is not a verdict. While the boot
        # has not produced one ("starting"), run() is about to publish the real
        # one, and once it has ("error") that verdict is final: either way,
        # rewriting it to "agent_exited" here let a start's terminal-state
        # wait read the intermediate or clobbered state instead of the
        # failure code. After the boot, an exit still becomes "agent_exited".
        if self.state not in ("stopping", "stopped", "starting", "error"):
            self.state = "agent_exited"
        # Issue #174: resolve the still-pending requests in place. Every slot
        # is popped by its own single waiter, and the reader thread is gone
        # with the agent, so clearing the dict could only race that waiter's
        # own lookup - a boot-time exit landing between the send and the wait
        # made the lookup miss and reported acp-initialize-timeout for a death
        # the holder had already resolved.
        with self.agent.lock:
            unanswered = list(self.agent.pending_out.values())
        for slot in unanswered:
            if slot["response"] is None:
                slot["response"] = {"error": {"code": "agent-exited",
                                              "message": "agent process exited"}}
            slot["event"].set()
        self.write_record()
        self.fanout_follow_eof()
        with self.turn_cond:
            self.turn_cond.notify_all()
        # Issue #299: an unrequested agent exit outside the boot window is an
        # error wake; the boot failure branch and op_stop carry their own.
        if not self.stop_requested and self.state not in ("starting", "error"):
            self._delegator_wake("error")

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
            "runner_build": self.runner_identity["runner_build"],
            "accepted_revision": self.runner_identity["accepted_revision"],
            "script_paths": self.runner_identity["script_paths"],
            "start_selection": self.start_selection,
            "session_role": self.session_role,
            "start_evidence": self.start_evidence,
            "baseline_exempt": self.baseline_exempt,
            "agent_pid": self.agent.proc.pid if self.agent.proc else None,
            "agent_pgid": self.agent.proc.pid if self.agent.proc else None,
            "agent_alive": bool(self.agent.proc and not self.agent.exited.is_set()),
            "agent_exit_code": self.agent.exit_code,
            "acp_session_id": self.acp_session_id,
            "session_meta": self.session_meta,
            "initial_config_options": self.initial_config_options,
            "protocol_version": self.protocol_version,
            "agent_info": self.agent_info,
            "cli_version": self.cli_version,
            "capabilities": self.capabilities,
            "heartbeat_host": self.heartbeat_host,
            "pending_permissions": list(self.pending_permissions.values()),
            # Issue #92: a wake this worker still owes its bound Host, so the
            # loss is observable instead of silent. Locator facts only.
            "undelivered_worker_events": self._undelivered_wake_facts(),
            "activity_hint": activity,
            "last_prompt": self.last_prompt,
            "turn_request_id": turn.get("request_id"),
            "compact_project_notice": (None if self.compact_notice_pending is None else {
                "prior_turn_request_id": self.compact_notice_pending["prior_turn_request_id"],
                "completion": "unconfirmed",
                "write_unknown": self.compact_notice_pending["write_unknown"]}),
            "turn_active": turn["active"],
            "turn_outcome": turn.get("outcome"),
            "stop_reason": turn.get("stop_reason"),
            "mutation_status": turn.get("mutation_status"),
            "context_usage": turn.get("context_usage"),
            "event_cursor": self.events.cursor,
            "malformed_stdout_lines": self.agent.malformed_lines,
            "unknown_update_variants": self.agent.unknown_updates,
            "agent_message_errors": self.agent.handler_errors,
            "fatal_error": self.fatal_error,
        }

    def turn_receipt(self, wait_timeout: float | None = None,
                     max_final_chars: int = 4000,
                     turn: dict[str, Any] | None = None) -> dict[str, Any]:
        # `self.turn` is REPLACED when a new prompt is admitted, never reset in
        # place, so holding the object is how a receipt stays bound to the turn
        # it describes even if another turn starts meanwhile (Issue #65).
        turn = self.turn if turn is None else turn
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

    def _no_acp_session(self) -> dict[str, Any] | None:
        """Issue #65: a session that never negotiated an ACP session id cannot be
        prompted, steered or cancelled.

        A failed `start` leaves `acp_session_id` None while the agent process is
        still alive, so the frame would be written with `"sessionId": null` and
        the caller would read `in_progress` - a dispatch that never happened.
        Worse, the composite steer would then report `steer_consumed: true` for
        text no session ever received. Refuse before writing anything.
        """
        if self.acp_session_id:
            return None
        return {"outcome": "no_session", "mutation_status": "not_started",
                "mutation_performed": False, "acp_session_id": None,
                "error": {"code": "no-acp-session",
                          "message": "this session has no ACP session id - `start` did not "
                                     "negotiate one, so nothing was written; read the start "
                                     "receipt's error and start the session again"}}

    def op_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.agent.exited.is_set() or self.agent.proc is None:
            return {"outcome": "process_exited", "mutation_status": "not_started",
                    "mutation_performed": False,
                    "error": {"code": "agent-not-running", "message": "agent process is not running"}}
        refusal = self._no_acp_session()
        if refusal is not None:
            return refusal
        with self.lock:
            expected = params.get("expected_holder_instance_id")
            if expected is not None and expected != self.holder_instance_id:
                return self._holder_instance_mismatch("prompt", expected)
            if self.stop_requested:
                return {"outcome": "stopping", "mutation_status": "not_started",
                        "mutation_performed": False,
                        "error": {"code": "stopping",
                                  "message": "this holder is stopping; the prompt was not started"}}
            if "expected_prior_turn_request_id" in params and (
                    self.turn.get("request_id") != params["expected_prior_turn_request_id"]
                    or self.acp_session_id != params.get("expected_acp_session_id")):
                return {"outcome": "prior_turn_changed", "mutation_status": "not_started",
                        "mutation_performed": False,
                        "active_turn_request_id": self.turn.get("request_id"),
                        "error": {"code": "steer-turn-changed",
                                  "message": "another turn or session replaced the targeted prior "
                                             "turn; nothing was written"}}
            if params.get("require_successful_prior_turn") and (
                    self.turn.get("outcome") != "turn_completed"
                    or self.turn.get("stop_reason") != "end_turn"
                    or self.turn.get("error")):
                return {"outcome": "prior_turn_unsuccessful", "mutation_status": "not_started",
                        "mutation_performed": False,
                        "error": {"code": "prior-turn-unsuccessful",
                                  "message": "the targeted turn did not end successfully"}}
            if self.turn["active"]:
                return {"error": {"code": "prompt-in-progress",
                                  "message": "a prompt turn is already active"},
                        "outcome": "in_progress", "mutation_performed": False,
                        "active_turn_request_id": self.turn.get("request_id"),
                        "mutation_status": self.turn["mutation_status"]}
            text = params.get("text") or ""
            # Read before anything is written: every event this turn produces
            # has a cursor strictly greater than this one.
            dispatch_cursor = self.events.cursor
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
            self.projection.add_user_from_prompt(text, self.events.cursor, self.turn["written_at"])
            self.write_record()

        threading.Thread(
            target=self._await_prompt, args=(request_id,), daemon=True
        ).start()
        wait = params.get("wait", True)
        timeout = params.get("timeout")
        max_chars = params.get("max_final_chars", 4000)
        if not wait:
            # Issue #65: `dispatch_event_cursor` is the anchor a non-blocking
            # caller needs later. A worker event carries the cursor at TURN END,
            # which is after the reply, so `capture --since <event_cursor>` would
            # skip the very reply being accepted. This cursor precedes the
            # turn's own output and is the correct `--since` value.
            return {"outcome": "in_progress", "mutation_status": "in_progress",
                    "mutation_performed": True, "prompt_fingerprint": fingerprint,
                    "duplicate_warning": duplicate, "acp_session_id": self.acp_session_id,
                    # Issue #65: this id comes from THIS call's admission, under
                    # the lock. Reading `self.turn` afterwards can pick up a turn
                    # someone else started.
                    "turn_request_id": request_id,
                    "dispatch_event_cursor": dispatch_cursor,
                    "event_cursor": self.events.cursor}
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
                    "dispatch_event_cursor": dispatch_cursor,
                    "duplicate_warning": duplicate}
        receipt = self.turn_receipt(max_final_chars=max_chars)
        receipt["duplicate_warning"] = duplicate
        receipt["dispatch_event_cursor"] = dispatch_cursor
        return receipt

    def _await_prompt(self, request_id: int) -> None:
        response = self.agent.wait_response(request_id, None)
        self.on_prompt_response(request_id, response)

    # -- event-driven heartbeat carrier (Issue #62 phase 2) --------------------

    def _notify_heartbeat_host_now(self, kind: str, reason: str,
                                   extra: dict[str, Any] | None = None) -> None:
        """One carrier send from this worker holder to the ZCode Host holder.

        Synchronous and bounded: the caller is an existing agent-exit or
        turn-end path, and ``op_stop`` waits out this lock before exiting, so
        an exact stop never kills a half-delivered event. The receipt (staged,
        delivered, or an honest error) is evidence in this holder's event log.
        ``extra`` adds locating metadata only (Issue #76: ``request_id``) -
        never request titles, options, tool input, or credentials.
        """
        target = self.heartbeat_host
        if target is None:
            return
        params = {"schema": WORKER_EVENT_SCHEMA, "kind": kind,
                  "platform": self.args.platform, "session": self.args.session,
                  "repo": self.args.repo, "reason": reason,
                  "event_cursor": self.events.cursor}
        if extra:
            params.update(extra)
        receipt = self._carrier_send(target, params)
        self.events.append({"kind": "heartbeat_carrier_sent", "event_kind": kind,
                            "reason": reason, "target_session": target["session"],
                            "receipt": receipt})
        if (kind in ("permission_required", "idle")
                and self._carrier_error_code(receipt) in CARRIER_UNDELIVERED_CODES):
            self._retain_undelivered_wake(params, receipt)
        elif kind == "idle":
            # A newer turn end the Host took supersedes any older held one.
            with self.undelivered_wakes_lock:
                self.undelivered_wakes.pop(IDLE_WAKE_KEY, None)

    def _delegator_wake(self, state: str, inline: bool = False) -> None:
        """Issue #299: fire the Delegator webhook signal for a Host holder.

        The payload is a signal only (identity + event_seq + state + ts). The
        detached ``kaola-acp.py delegator-webhook deliver`` child reads the
        config, validates, POSTs and writes receipts, so the holder never
        blocks on the network and the delivery survives holder exit. A spawn
        failure is one event-log line with the exception class name only.
        ``inline`` spawns without a thread or a wait for the op_stop path that
        exits right after its reply.
        """
        if self.session_role != "host":
            return
        payload = {
            "schema": "kaola-delegator-wake/1",
            "project": self.args.repo,
            "session": self.args.session,
            "holder_instance_id": self.holder_instance_id,
            "event_seq": self.events.cursor,
            "state": state,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        argv = [sys.executable,
                str(Path(__file__).resolve().with_name("kaola-acp.py")),
                "delegator-webhook", "deliver"]
        body = json.dumps(payload).encode("utf-8")

        def spawn(wait: bool) -> None:
            try:
                proc = subprocess.Popen(
                    argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True,
                    close_fds=True, cwd=self.args.repo)
                try:
                    assert proc.stdin is not None
                    proc.stdin.write(body)
                    proc.stdin.close()
                except OSError:
                    pass
                if wait:
                    proc.wait()
            except Exception as exc:
                try:
                    self.events.append({"kind": "delegator_wake_spawn_failed",
                                        "error": type(exc).__name__})
                except Exception:
                    pass

        if inline:
            spawn(wait=False)
        else:
            threading.Thread(target=spawn, args=(True,), daemon=True).start()

    def _carrier_send(self, target: dict[str, str], params: dict[str, Any],
                      still_owed: Any = None) -> dict[str, Any]:
        """One bounded carrier round trip, or an honest error receipt.

        ``params`` is passed through verbatim - a retry offers the SAME
        ``event_cursor``, so the Host's deterministic ``event_id`` and its
        existing duplicate handling are what keep a repeat from prompting twice.

        ``still_owed`` is re-read immediately before the bytes go out, which is
        as late as this transport allows. That NARROWS the window - it does not
        close it. Check, write, and the Host's own staging are three steps on
        two processes, so a settlement landing after the write still leaves the
        Host holding an event whose request is gone. The carrier cannot fix
        that; the Host re-reads the worker's live ``pending_permissions`` before
        acting, and the caller here records a late settlement honestly instead
        of calling the delivery a recovery (Issue #92, outer re-review).
        """
        receipt: dict[str, Any] = {}
        with self.heartbeat_notify_lock:
            try:
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    connection.settimeout(HEARTBEAT_NOTIFY_TIMEOUT)
                    connection.connect(target["socket"])
                    if still_owed is not None and not still_owed():
                        receipt = {"error": {
                            "code": "carrier-aborted",
                            "message": "the wake stopped being owed before it was sent"}}
                    else:
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
        # Whatever is bound at the host socket answered; it is not trusted to
        # have answered in the receipt shape. Callers read `error.code`, so a
        # reply that is not an object, or whose `error` is not an object, is
        # normalised here into an honest carrier failure rather than raising on
        # the agent reader thread that called us.
        error = receipt.get("error") if isinstance(receipt, dict) else receipt
        code = error.get("code") if isinstance(error, dict) else None
        # The receipt must name the event that was actually SENT. Any other
        # string - a blank one, a stale one, one for somebody else's event -
        # proves nothing about this wake and leaves it owed (Issue #92, outer
        # review).
        taken = (isinstance(receipt, dict)
                 and receipt.get("event_id") == worker_event_id(params))
        if not isinstance(receipt, dict) or (
                error is not None and not isinstance(error, dict)) or (
                not isinstance(code, str) and not taken):
            # Absence of an `error` key is not proof of delivery: `op_worker_event`
            # names the event it took on every accepting path (staged, duplicate,
            # confirmed duplicate), so a reply that names a different event, or
            # none, never proves this wake got through and must leave it owed.
            receipt = {"error": {
                "code": "host-reply-invalid",
                "message": "heartbeat host reply is not a worker_event receipt",
                "reply_head": str(receipt)[:HEARTBEAT_DEFECT_CHARS]}}
        return receipt

    @staticmethod
    def _carrier_error_code(receipt: dict[str, Any]) -> Any:
        """The receipt's error code, or None when the Host accepted the event."""
        error = receipt.get("error")
        return error.get("code") if isinstance(error, dict) else None

    def _retain_undelivered_wake(self, params: dict[str, Any],
                                 receipt: dict[str, Any]) -> None:
        """Hold a permission wake the bound Host never took (Issue #92).

        One entry per pending request, carrying the ORIGINAL carrier params so
        every later offer is the same event rather than a new one.
        """
        idle = params.get("kind") == "idle"
        key = IDLE_WAKE_KEY if idle else normalize_id(params.get("request_id"))
        error = self._carrier_error_code(receipt)
        with self.undelivered_wakes_lock:
            held = self.undelivered_wakes.get(key)
            if held is not None and not (
                    idle and held["params"]["event_cursor"] != params["event_cursor"]):
                held["last_error"] = error
                return
            self.undelivered_wakes[key] = {"params": params, "attempts": 1,
                                           "last_error": error, "logged_error": error}
        self.events.append({"kind": "heartbeat_carrier_undelivered",
                            "event_kind": params["kind"],
                            "request_id": params.get("request_id"),
                            "event_cursor": params["event_cursor"],
                            "error": error})

    def _wake_stale_reason(self, key: str) -> str | None:
        """Why this held wake is no longer worth waking a Host for, or None.

        The worker is the authority on its own pending list: a request the Host
        can no longer answer must never become a prompt, however long the Host
        was away.
        """
        if self.stop_requested:
            return "stopping"
        if key == IDLE_WAKE_KEY:
            # A returned result stays owed after the agent exits: the Host
            # verdict on it is still pending.
            return None
        if self.agent.exited.is_set() or self.agent_exited.is_set():
            return "agent-exited"
        if key not in self.pending_permissions:
            return "permission-settled"
        return None

    def _wake_still_owed(self, key: str) -> bool:
        """Re-read, never cached: is this wake worth sending RIGHT NOW?"""
        with self.undelivered_wakes_lock:
            if key not in self.undelivered_wakes:
                return False
        return self._wake_stale_reason(key) is None

    def _undelivered_wake_facts(self) -> list[dict[str, Any]]:
        """What this worker still owes its bound Host: locator facts only."""
        with self.undelivered_wakes_lock:
            return [{"kind": wake["params"]["kind"],
                     "request_id": wake["params"].get("request_id"),
                     "event_cursor": wake["params"]["event_cursor"],
                     "attempts": wake["attempts"],
                     "last_error": wake["last_error"]}
                    for wake in self.undelivered_wakes.values()]

    def _flush_undelivered_wakes(self) -> None:
        """Re-offer every permission wake the bound Host has not taken yet.

        Driven by the holder's existing watchdog tick - the one timer this
        process already runs - so there is no second scheduler and no retry
        deadline to outlive. A Host absent for an hour still gets the wake when
        it comes back, and a wake whose request died before the offer is written
        is dropped here rather than sent. A request that dies AFTER the write is
        past this point: the Host has it, the delivery is recorded as stale, and
        the Host's own re-read of the worker's live ``pending_permissions`` is
        what keeps it safe. Nothing approves anything; only the locator travels.
        """
        if self.heartbeat_host is None:
            return
        with self.undelivered_wakes_lock:
            held = list(self.undelivered_wakes.items())
        for key, wake in held:
            stale = self._wake_stale_reason(key)
            if stale is not None:
                with self.undelivered_wakes_lock:
                    if self.undelivered_wakes.pop(key, None) is None:
                        continue
                self.events.append({"kind": "heartbeat_carrier_dropped",
                                    "event_kind": wake["params"]["kind"],
                                    "request_id": wake["params"].get("request_id"),
                                    "event_cursor": wake["params"]["event_cursor"],
                                    "reason": stale})
                continue
            receipt = self._carrier_send(
                self.heartbeat_host, wake["params"],
                still_owed=lambda key=key: self._wake_still_owed(key))
            error = self._carrier_error_code(receipt)
            if error == "carrier-aborted":
                # Nothing was sent, so there is nothing for the Host to ignore.
                # Record why this wake ended, exactly as the pre-send check does.
                stale = self._wake_stale_reason(key) or (
                    "superseded" if key == IDLE_WAKE_KEY else "permission-settled")
                with self.undelivered_wakes_lock:
                    if self.undelivered_wakes.pop(key, None) is None:
                        continue
                self.events.append({"kind": "heartbeat_carrier_dropped",
                                    "event_kind": wake["params"]["kind"],
                                    "request_id": wake["params"].get("request_id"),
                                    "event_cursor": wake["params"]["event_cursor"],
                                    "reason": stale})
                continue
            owed = error in CARRIER_UNDELIVERED_CODES
            with self.undelivered_wakes_lock:
                current = self.undelivered_wakes.get(key)
                if current is None or current["params"] is not wake["params"]:
                    continue
                current["attempts"] += 1
                attempts = current["attempts"]
                previous = current["logged_error"]
                current["last_error"] = error
                if owed:
                    current["logged_error"] = error
                else:
                    self.undelivered_wakes.pop(key, None)
            record = {"event_kind": wake["params"]["kind"],
                      "request_id": wake["params"].get("request_id"),
                      "event_cursor": wake["params"]["event_cursor"],
                      "attempts": attempts}
            if error is None:
                # The bytes are out and the Host has the event. Whether an
                # APPROVAL is still waiting is a SEPARATE fact, and the round
                # trip is long enough for it to change. Re-read it now: a wake
                # that lost its request in flight was still delivered, and
                # saying so is not the same as saying it recovered one.
                stale_now = self._wake_stale_reason(key)
                if stale_now is None:
                    self.events.append({"kind": "heartbeat_carrier_recovered",
                                        **record, "receipt": receipt})
                else:
                    self.events.append({"kind": "heartbeat_carrier_delivered_stale",
                                        **record, "reason": stale_now,
                                        "receipt": receipt})
            elif not owed:
                # The Host answered and refused. It recorded that refusal for
                # itself - a queue-full receipt already schedules its own full
                # pending-approval pass - so re-offering it forever would drive
                # the Host, not recover the wake.
                self.events.append({"kind": "heartbeat_carrier_dropped",
                                    **record, "reason": "host-answered",
                                    "receipt": receipt})
            elif error != previous:
                # A long absence is not logged once per tick; a CHANGE in how
                # it is failing is the receipt worth keeping.
                self.events.append({"kind": "heartbeat_carrier_undelivered",
                                    **record, "error": error})

    def _record_overflow_full_check(self) -> int:
        """Bump the one full-check generation and log the fact.

        The 33rd detailed event is not staged. Resume rebuilds pending
        full-check from this log. Remind only; nothing here approves a
        permission.
        """
        with self.worker_events_lock:
            self.overflow_generation += 1
            generation = self.overflow_generation
            self.events.append({"kind": "worker_event_overflow",
                                "generation": generation})
        return generation

    def _heartbeat_payload(self, events: list[dict[str, Any]],
                           overflow_full_check: bool = False
                           ) -> tuple[str, dict[str, Any]]:
        """One literal notification prompt: fixed structured event metadata,
        the current FULL heartbeat prompt body read at delivery time from the
        file the ZCode Host agent maintains in the consuming project, and the
        one-pass instruction. No worker raw output, no shell execution."""
        source = Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json"
        # Issue #66: a file that exists but carries no usable `body` is a
        # different fact from no file at all, and silently reporting "none
        # maintained" let a Host believe a prompt it had written under another
        # field name was in effect. Name the defect; still deliver the event.
        # One read returns both, so the checked body is the delivered body.
        body, defect = heartbeat_prompt_body(source)
        maintained = body is not None
        if not maintained:
            if defect is not None:
                if ("stored body was not injected" in defect or "projected Host view" in defect
                        or "record contract" in defect):
                    body = (f"The heartbeat file at {source} uses schema kaola-heartbeat-prompt/2. "
                            f"{defect} Do not write a body string. Repair the structured state "
                            "with the state tool, then retry. This pass runs without the projection.")
                else:
                    body = (f"The heartbeat prompt file at {source} exists but carries no "
                            f"usable prompt: {defect}. This {self.host_name} Host session maintains "
                            'that file; write a JSON object whose "body" field is a '
                            "non-empty string holding the full working prompt, and treat "
                            "this pass as running without it. Recover authorization and "
                            "field state from the consuming project records, then run one "
                            "full pass.")
            else:
                body = (f"No maintained heartbeat prompt was found at {source}. Recover "
                        "authorization and field state from the consuming project records, "
                        "then run one full pass.")
        lines = [
            self.host_entry,
            f"kaola-host-notify/1: event-driven heartbeat carrier ({self.host_name} Host)",
            "worker events (structured, one JSON object per line):",
        ]
        for event in events:
            lines.append(json.dumps(
                {key: event[key] for key in
                 ("event_id", "kind", "platform", "session", "repo", "reason",
                  "event_cursor", "request_id")
                 if event.get(key) is not None},
                ensure_ascii=False, sort_keys=True))
        if overflow_full_check:
            lines.append(OVERFLOW_FULL_CHECK_MARK)
            lines.append(
                f"detailed worker-event queue is at capacity {HEARTBEAT_EVENT_CAP}; "
                "at least one later worker event was not staged as a detailed line.")
            lines.append(
                "This pass: inspect every authorized worker's real status and pending "
                "approvals from their own receipts. Remind only; do not approve or "
                "refuse permissions from this signal.")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if maintained:
            lines.append(f"heartbeat prompt source: {source} (fingerprint sha256:{digest}, "
                         f"{len(body.encode('utf-8'))} bytes)")
        elif defect is not None:
            lines.append(f"heartbeat prompt source: {source} present but UNUSABLE - "
                         f"{defect} (fallback trigger context, sha256:{digest})")
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
                     f"trigger; this {self.host_name} Host registers no periodic carrier.")
        meta: dict[str, Any] = {"heartbeat_fingerprint": f"sha256:{digest}",
                                "heartbeat_source": str(source),
                                "heartbeat_maintained": maintained}
        attention = attention_fingerprint(body) if maintained else None
        if attention is not None:
            meta["attention_fingerprint"] = attention
        if defect is not None:
            meta["heartbeat_body_error"] = defect
        if overflow_full_check:
            meta["overflow_full_check"] = True
        return "\n".join(lines), meta

    def _established_non_host(self) -> bool:
        """A recorded role other than Host. An unknown role keeps the Host
        carrier behaviour every earlier carrier had."""
        return getattr(self, "session_role", None) in SESSION_ROLES - {"host"}

    # -- bound Sideagent relay (Issue #255) -------------------------------------

    def _sideagent_relay_target(self) -> dict[str, Any] | None:
        """The bound maintenance Sideagent this Host holder relays routine
        worker events to, or None. The binding comes from the lifecycle state;
        the Sideagent's own live record and socket must prove it."""
        doc, body, _ = read_heartbeat_file(Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json")
        if not isinstance(doc, dict) or doc.get("schema") != HEARTBEAT_STATE_SCHEMA:
            return None
        state = doc.get("state")
        binding = state.get("sideagent") if isinstance(state, dict) else None
        if not isinstance(binding, dict) or binding.get("state") != "active":
            return None
        platform, session = binding.get("platform"), binding.get("session")
        if (not isinstance(platform, str) or not platform or not isinstance(session, str)
                or not session or session == self.args.session):
            return None
        directory = self._node_directory(platform, session)
        if directory is None:
            return None
        try:
            record = json.loads((directory / "record.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        holder = record.get("holder_instance_id") if isinstance(record, dict) else None
        if (not isinstance(record, dict) or record.get("session_role") not in SIDEAGENT_ROLES
                or record.get("repo") != self.args.repo or record.get("state") != "ready"
                or not isinstance(holder, str) or not holder
                or (binding.get("mode") != "node" and binding.get("holder_instance_id")
                    and binding["holder_instance_id"] != holder)
                or (binding.get("mode") == "node" and holder != self.node.get("holder"))
                or "sideagent-relay/1" not in (record.get("holder_features") or [])
                or not isinstance(record.get("holder_pid"), int)
                or not process_alive(record["holder_pid"])):
            return None
        sock = acp_paths.socket_path(directory)
        if not sock.exists():
            return None
        return {"platform": platform, "session": session, "holder_instance_id": holder,
                "socket": str(sock), "attention": attention_fingerprint(body)}

    def _relay_prompt(self, events: list[dict[str, Any]]) -> str:
        lines = [f"{RELAY_SCHEMA}: worker events relayed by the {self.host_name} Host holder "
                 f"{self.args.session}",
                 "worker events (structured, one JSON object per line):"]
        for event in events:
            lines.append(json.dumps(
                {key: event[key] for key in
                 ("event_id", "kind", "platform", "session", "repo", "reason",
                  "event_cursor", "request_id") if event.get(key) is not None},
                ensure_ascii=False, sort_keys=True))
        lines.append("As the bound maintenance Sideagent: read each related task and its real "
                     "receipts, update only the affected lifecycle records with the state tool, "
                     "and record anything that needs a Host judgment as a durable decision or "
                     "alert. Do not wait on the Host. The Host is woken when its view's attention "
                     "changes.")
        return "\n".join(lines)

    def _relay_send(self, target: dict[str, Any], text: str) -> dict[str, Any]:
        deadline = time.monotonic() + RELAY_SEND_TIMEOUT

        def remaining() -> float:
            left = deadline - time.monotonic()
            if left <= 0:
                raise socket.timeout("relay deadline passed")
            return left

        try:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                connection.settimeout(remaining())
                connection.connect(target["socket"])
                connection.settimeout(remaining())
                connection.sendall(canonical(
                    {"op": "prompt", "request_id": secrets.token_hex(8),
                     "params": {"text": text, "wait": False,
                                "expected_holder_instance_id": target["holder_instance_id"]}}) + b"\n")
                buffer = bytearray()
                while b"\n" not in buffer:
                    connection.settimeout(remaining())
                    data = connection.recv(65536)
                    if not data:
                        break
                    buffer.extend(data)
            finally:
                connection.close()
            receipt = json.loads(bytes(buffer.partition(b"\n")[0]).decode("utf-8", "replace"))
        except (OSError, ValueError) as exc:
            return {"error": {"code": "sideagent-unreachable", "message": str(exc)}}
        return receipt if isinstance(receipt, dict) else {"error": {"code": "sideagent-receipt-unreadable"}}

    def _confirm_events(self, items: list[dict[str, Any]], via: str) -> None:
        """Durable confirmation of events a relay settled. Caller holds
        ``worker_events_lock``."""
        if not items:
            return
        ids = [item["event_id"] for item in items]
        cursor = self.events.append({"kind": "worker_event_confirmed", "event_ids": ids, "via": via})
        for item in items:
            self.pending_worker_events.remove(item)
        self._remember_confirmed_worker_events({event_id: cursor for event_id in ids})

    def _settle_relays(self, ends: list[dict[str, Any]]) -> None:
        """Apply Sideagent turn ends to the relays they settle. Caller holds
        ``worker_events_lock``.

        The turn that carried a relay confirms it only when it completed; a
        failed or cancelled one returns it to the Host. A Sideagent runs one
        turn at a time, so a later turn end from the same holder, past the
        relay's own dispatch cursor, proves the carrying turn ended although
        its end never arrived: those events go back to the Host with the
        outcome unknown rather than staying marked for ever."""
        self._settle_node_batch(ends)
        ended = {(item["holder_instance_id"], item["turn_fingerprint"]): item.get("turn_outcome")
                 for item in ends}
        latest: dict[str, int] = {}
        for item in ends:
            cursor = item.get("event_cursor")
            if isinstance(cursor, int) and not isinstance(cursor, bool):
                holder = item["holder_instance_id"]
                latest[holder] = max(latest.get(holder, cursor), cursor)

        def turn_of(item: dict[str, Any]) -> tuple[Any, Any]:
            mark = item.get("relayed") or {}
            return mark.get("holder"), mark.get("fingerprint")

        def end_missing(item: dict[str, Any]) -> bool:
            mark = item.get("relayed") or {}
            cursor = mark.get("cursor")
            return (turn_of(item) not in ended and isinstance(cursor, int)
                    and latest.get(mark.get("holder"), cursor) > cursor)

        self._confirm_events([item for item in self.pending_worker_events
                              if "relayed" in item and ended.get(turn_of(item), "") == "turn_completed"],
                             "sideagent-relay")
        returned = [(item, str(ended[turn_of(item)])) for item in self.pending_worker_events
                    if "relayed" in item and turn_of(item) in ended]
        returned += [(item, "turn-end-missing") for item in self.pending_worker_events
                     if "relayed" in item and end_missing(item)]
        if returned:
            self.events.append({"kind": "worker_event_relay_returned",
                                "event_ids": [item["event_id"] for item, _ in returned],
                                "outcomes": sorted({outcome for _, outcome in returned})})
            for item, _ in returned:
                item.pop("relayed", None)
                item["host_owned"] = True

    def _relay_pass(self) -> dict[str, Any]:
        """Route routine worker events to the bound Sideagent, at least once.

        Caller holds ``worker_events_lock``. Events from other sessions go to
        the Sideagent; the Sideagent's own events stay with the Host. A relay
        is confirmed only by the end of the very turn that carried it: an idle
        event naming the same Sideagent holder and that turn's prompt
        fingerprint. Any other idle confirms nothing. A relay to a holder that
        is no longer the bound one moves to the current binding at once, so a
        direct replacement strands nothing. The Host is woken only when its
        view's attention changed since it last saw it. Without a provable live
        binding every event goes to the Host as before.
        """
        if self._established_non_host():
            # Every holder reaches here at its turn ends; a session known not
            # to be the Host never relays to a Sideagent or starts nodes.
            return {}
        binding = self._node_binding()
        if binding is not None:
            return self._node_relay_pass(binding)
        if self.session_role == "host" and not self.stop_requested:
            doc = self._lifecycle_state()
            recovery = self._node_recovery_pending(doc)
            through = self._node_host_pending(doc)
            if recovery or through is not None:
                self._maintenance_failure("binding-or-recipe-unavailable", through, recovery)
        if not self.pending_worker_events:
            return {}
        target = self._sideagent_relay_target()
        if target is None:
            for item in self.pending_worker_events:
                item.pop("relayed", None)
            return {}
        self._settle_relays([item for item in self.pending_worker_events if is_turn_end(item)])
        moved = [item for item in self.pending_worker_events
                 if (item.get("relayed") or {}).get("holder") not in (None, target["holder_instance_id"])]
        if moved:
            self.events.append({"kind": "worker_event_relay_transferred",
                                "event_ids": [item["event_id"] for item in moved],
                                "from_holders": sorted({item["relayed"]["holder"] for item in moved}),
                                "to_holder": target["holder_instance_id"],
                                "target_session": target["session"]})
            for item in moved:
                item.pop("relayed", None)
        own = [item for item in self.pending_worker_events if item.get("session") == target["session"]]
        if (any(item.get("kind") == "idle" for item in own)
                and target["attention"] is not None and target["attention"] == self.host_attention_seen):
            # Only a completed maintenance turn is quiet; a failed or
            # cancelled one reaches the Host.
            self._confirm_events([item for item in own if item.get("kind") == "idle"
                                  and item.get("turn_outcome") == "turn_completed"
                                  and "prompt_fingerprint" not in item], "sideagent-quiet")
        waiting = [item for item in self.pending_worker_events
                   if item.get("session") != target["session"] and "relayed" not in item
                   and "prompt_fingerprint" not in item and not item.get("host_owned")]
        result: dict[str, Any] = {"live": True, "session": target["session"]}
        if not waiting:
            return result
        receipt = self._relay_send(target, self._relay_prompt(waiting))
        error = receipt.get("error") if isinstance(receipt.get("error"), dict) else None
        if (error is None and receipt.get("outcome") == "in_progress"
                and isinstance(receipt.get("prompt_fingerprint"), str)):
            cursor = receipt.get("dispatch_event_cursor")
            for item in waiting:
                item["relayed"] = {"holder": target["holder_instance_id"],
                                   "fingerprint": receipt.get("prompt_fingerprint"),
                                   **({"cursor": cursor} if isinstance(cursor, int)
                                      and not isinstance(cursor, bool) else {})}
            self.events.append({"kind": "worker_event_relayed", "target_session": target["session"],
                                "target_holder": target["holder_instance_id"],
                                "event_ids": [item["event_id"] for item in waiting],
                                "prompt_fingerprint": receipt.get("prompt_fingerprint")})
            result["receipt"] = {"relayed": len(waiting), "target_session": target["session"]}
        elif error is not None and error.get("code") in ("prompt-in-progress", "stopping"):
            # Busy is not lost: its own turn end is the next delivery boundary.
            result["receipt"] = {"relayed": 0, "waiting": len(waiting), "reason": error["code"]}
        else:
            # Unreachable or refused: the Host keeps these events this pass.
            result = {"receipt": {"relayed": 0, "fallback": "host",
                                  "reason": (error or {}).get("code") or "relay-unadmitted"}}
            self.events.append({"kind": "worker_event_relay_failed", "target_session": target["session"],
                                "receipt": receipt})
        return result

    # -- maintenance nodes (Issue #255) ----------------------------------------

    def _lifecycle_state(self) -> dict[str, Any] | None:
        doc, _, _ = read_heartbeat_file(Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json")
        if not isinstance(doc, dict) or doc.get("schema") != HEARTBEAT_STATE_SCHEMA:
            return None
        return doc

    def _node_binding(self) -> dict[str, Any] | None:
        """The active node-mode binding with a usable recipe, or None. The
        recipe is the existing Runner argv for a fresh Sideagent start of the
        bound session in this project; a resume or continue is not fresh."""
        doc = self._lifecycle_state()
        state = doc.get("state") if doc else None
        binding = state.get("sideagent") if isinstance(state, dict) else None
        if not isinstance(binding, dict) or binding.get("mode") != "node" or binding.get("state") != "active":
            return None
        recipe = binding.get("recipe") if isinstance(binding.get("recipe"), dict) else {}
        runner, argv = recipe.get("runner"), recipe.get("argv")
        session = binding.get("session")
        problem = None
        if not isinstance(binding.get("platform"), str) or not binding["platform"]:
            problem = "binding must name the node platform"
        elif not isinstance(runner, str) or not os.path.isabs(runner) or not os.path.isfile(runner):
            problem = "recipe runner must be an existing absolute path"
        elif (not isinstance(argv, list) or not all(isinstance(part, str) for part in argv)
              or not argv or (argv[0] != "start" and argv[:2] != [binding["platform"], "start"])):
            # A platform Runner takes `start ...`; the checkout entrypoint
            # (`kaola-tmux.sh`) takes the bound platform first.
            problem = "recipe argv must be the Runner start argument list"
        elif not isinstance(session, str) or session == self.args.session or any(
                argv[i] == flag and (i + 1 >= len(argv) or argv[i + 1] != want)
                for i in range(len(argv)) for flag, want in
                (("--session", session), ("--repo", self.args.repo), ("--role", "sideagent"))):
            problem = "recipe must start the bound session in this project with --role sideagent"
        elif not all(flag in argv for flag in ("--session", "--repo", "--role")):
            problem = "recipe must name --session, --repo and --role sideagent"
        elif "--continue" in argv or "--resume" in argv:
            problem = "a node starts with a fresh native context; --continue/--resume are refused"
        if problem:
            key = json.dumps(recipe, sort_keys=True)
            if self.node.get("recipe_refused") != key:
                self.node["recipe_refused"] = key
                self.events.append({"kind": "sideagent_node_recipe_refused", "detail": problem})
            return None
        return binding

    def _node_host_pending(self, doc: dict[str, Any] | None, requested: bool = False) -> int | None:
        """The Host revision a new batch would select, when Host business
        changes are past both the last handled checkpoint and the last batch
        this carrier already sent. A Host-requested recovery batch selects
        every change past the handled checkpoint, so a failed batch's range
        stays selectable without a fake business write."""
        if not doc:
            return None
        current = doc.get("host_revision")
        maintenance = (doc.get("state") or {}).get("maintenance") or {}
        handled = maintenance.get("handled_host_revision") or 0
        returned = (((doc.get("state") or {}).get("alerts") or {}).get("maintenance-returned") or {}).get("inputs") or {}
        returned_through = max([0] + [row["host_revision_through"] for row in returned.values()
                                      if isinstance(row, dict) and isinstance(row.get("host_revision_through"), int)])
        after = int(handled) if isinstance(handled, int) else 0
        if not requested:
            after = max(after, self.node.get("sent_through") or 0, returned_through)
        if (isinstance(current, int) and not isinstance(current, bool)
                and current > after):
            selector = getattr(_RECORD, "host_changes", None)
            # Older holder bundles keep revision-only selection. No new
            # transport gate when the pinned sibling has no shared selector.
            if callable(selector) and not selector(doc, after, current):
                return None
            return current
        return None

    def _node_recovery_pending(self, doc: dict[str, Any] | None) -> dict[str, Any] | None:
        if self.session_role != "host":
            return None
        state = (doc or {}).get("state") or {}
        item = (state.get("maintenance") or {}).get("recovery_input")
        if not isinstance(item, dict) or not isinstance(item.get("seq"), int):
            return None
        ident = f"recovery#{item['seq']}"
        # A returned obligation stays visible. A scoped request creates the
        # next input; it does not replay a failed or unknown batch.
        returned = ((state.get("alerts") or {}).get("maintenance-returned") or {}).get("inputs") or {}
        if ident in returned or item["seq"] <= (self.node.get("recovery_sent") or 0):
            return None
        return item

    def _maintenance_tool(self, argv: list[str]) -> dict[str, Any]:
        tool = self._state_tool()
        if tool is None:
            return {"error": "state tool unavailable; Host must recover from the original receipt"}
        env = dict(os.environ)
        env[DISPATCHER_ENV] = json.dumps(self.dispatcher_identity(), sort_keys=True)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_dir.parent.parent.parent)
        try:
            run = subprocess.run([sys.executable, tool, "state", "recovery-input", "--file",
                                  str(Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json"), *argv],
                                 cwd=self.args.repo, env=env, stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True)
            try:
                value = json.loads(run.stdout)
            except ValueError:
                return {"error": "state entry unavailable", "exit": run.returncode,
                        "detail": "read original tool stderr; update the matching state tool at a safe boundary"}
            if run.returncode:
                return {"error": value, "exit": run.returncode}
            return value
        except (OSError, ValueError) as exc:
            return {"error": str(exc)}

    def _register_compact_maintenance(self, cursor: int) -> None:
        if self.stop_requested or self.session_role != "host":
            return
        self.node["registration_cursor"] = cursor
        if self.node.get("registration_active"):
            return
        self.node["registration_active"] = True
        def register():
            receipt = self._maintenance_tool(["--kind", "host-compaction", "--source", "completed-host-signal",
                                              "--signal-cursor", str(cursor)])
            with self.worker_events_lock:
                self.node.pop("registration_active", None)
                if "error" not in receipt:
                    self.events.append({"kind": "host_compact_maintenance_registered", "signal_cursor": cursor,
                                        "input": receipt.get("value")})
                    if self.node.get("registration_cursor") == cursor:
                        self.node.pop("registration_cursor", None)
                else:
                    self.events.append({"kind": "host_compact_maintenance_registration_failed",
                                        "signal_cursor": cursor, "receipt": receipt})
                    key = f"register:{cursor}"
                    if self.node.get("registration_reported") != key:
                        self.node["registration_reported"] = key
                        self._node_to_host(self.dispatcher_identity(),
                            f"Host compact maintenance registration failed; read {self.events.path}#{cursor}; "
                            "repair the state tool and request bounded reconciliation from this original signal")
            self._kick_worker_events()
        threading.Thread(target=register, daemon=True).start()

    def _maintenance_failure(self, why: str, through: Any = None,
                             recovery: dict[str, Any] | None = None, wake: bool = True) -> None:
        if self.session_role != "host":
            return
        doc = self._lifecycle_state()
        recovery = recovery or (self.node.get("recovery_input") if self.node.get("batch") else None)
        recovery = recovery or self._node_recovery_pending(doc)
        ident = f"recovery#{recovery['seq']}" if recovery else f"batch:{self.node.get('batch') or through}"
        if recovery is None and through is None and not self.node.get("batch"):
            return
        key = (ident, why)
        if self.node.get("failure_reported") == key:
            return
        self.node["failure_reported"] = key
        evidence = f"{self.events.path}#{self.events.cursor}"
        binding = (((doc or {}).get("state") or {}).get("sideagent") or self.dispatcher_identity())
        if wake:
            self._node_to_host(binding, f"maintenance {ident}: {why}; Host must reconcile original receipts, "
                                       "repair the binding and request a bounded check", record=False)
        def record_failure():
            receipt = self._maintenance_tool(["--source", "carrier-maintenance-failure", "--fail", why,
                                              "--input", ident, "--evidence", evidence,
                                              *(["--through-host-revision", str(through)]
                                                if isinstance(through, int) else [])])
            self.events.append({"kind": "sideagent_maintenance_failure_recorded", "input": ident,
                                "reason": why, "receipt": receipt})
            self._kick_worker_events()
        threading.Thread(target=record_failure, daemon=True).start()

    def _node_relay_pass(self, binding: dict[str, Any]) -> dict[str, Any]:
        """Node mode of the relay. Caller holds ``worker_events_lock``.

        Worker events are not node inputs: an ordinary return or termination
        reaches the Host at its next safe boundary, as with no binding, and
        the Host reads the original. A node batch is the Host business
        changes past the last handled checkpoint, selected only while the
        Host turn is not active, so one Host turn's writes make one batch.
        The carrier starts a fresh node, sends that range once, settles it
        from the node's own checkpoint at its turn end, and exact-stops it.
        A failed start or an unconfirmed stop starts nothing further until
        the binding or the old holder changes.
        """
        if self.stop_requested:
            # A stopping carrier starts and feeds no node it could not reclaim.
            return {}
        session = binding["session"]
        node = self.node
        if node.get("stop_unconfirmed"):
            old = node["stop_unconfirmed"]
            if not self._node_holder_alive(binding, old.get("holder")):
                self.events.append({"kind": "sideagent_node_stop_confirmed_late", "holder": old.get("holder")})
                node.pop("stop_unconfirmed", None)
        own = [item for item in self.pending_worker_events if item.get("session") == session]
        quiet = [item for item in own if item.get("node_quiet")
                 or (item.get("kind") == "terminated" and not item.get("host_owned")
                     and node.get("phase") in ("stopping", "stopped"))
                 or (is_turn_end(item) and item.get("holder_instance_id") in node.get("holders", [])
                     and not item.get("host_owned") and item.get("turn_fingerprint") != node.get("fingerprint"))]
        self._confirm_events([item for item in quiet if "prompt_fingerprint" not in item], "sideagent-node")
        for item in own:
            if item in self.pending_worker_events and not item.get("host_owned"):
                # A node's permission request, crash or unexplained turn end
                # is the Host's to see.
                if not (is_turn_end(item) and item.get("turn_fingerprint") == node.get("fingerprint")):
                    item["host_owned"] = True
        if node.get("phase") == "running" and node.get("batch") and self._sideagent_relay_target() is None:
            self.events.append({"kind": "sideagent_node_lost", "holder": node.get("holder"),
                                "batch": node["batch"]})
            self._node_to_host(binding, f"sideagent node {node.get('holder')} was lost during batch "
                                        f"{node['batch']}; {self._unhandled(node.get('sent_through'))}")
            node.update(phase="stopped", batch=None, fingerprint=None)
        failed = node.get("failed")
        fingerprint = json.dumps({key: binding.get(key) for key in ("session", "recipe", "since")},
                                 sort_keys=True)
        if failed and failed.get("binding") != fingerprint:
            node.pop("failed", None)
            failed = None
        result: dict[str, Any] = {"session": session}
        if failed or node.get("stop_unconfirmed"):
            # No competing writer and no retry storm.
            return result
        if node.get("phase") in ("starting", "stopping") or node.get("batch"):
            return result
        if self.turn["active"]:
            # Startup can finish during a newer Host turn. Wait for its end
            # before sending a batch or reclaiming an unassigned node.
            return result
        doc = self._lifecycle_state()
        through = self._node_host_pending(doc)
        recovery = self._node_recovery_pending(doc)
        target = self._sideagent_relay_target()
        if through is None and recovery is None:
            if (doc and isinstance(doc.get("host_revision"), int)
                    and not isinstance(doc["host_revision"], bool)
                    and callable(getattr(_RECORD, "host_changes", None))
                    and node.get("phase") == "running" and node.get("binding") == fingerprint
                    and not node.get("fingerprint") and target is not None):
                # Our fresh node finished startup after its current input
                # disappeared. No batch was sent. Exact-stop that holder;
                # no handled/acked revision or checkpoint proof is written.
                node.update(phase="stopping")
                threading.Thread(target=self._stop_node,
                                 args=(target["holder_instance_id"],), daemon=True).start()
            return result
        if target is None:
            old = self._node_record(binding) or {}
            old_holder = old.get("holder_instance_id")
            if old_holder and self._node_holder_alive(binding, old_holder):
                node["stop_unconfirmed"] = {"holder": old_holder}
                self._maintenance_failure("old-node-live", through, recovery)
                return result
            node.update(phase="starting", binding=fingerprint)
            self.node_start = threading.Thread(target=self._start_node, args=(binding, fingerprint),
                                               daemon=True)
            self.node_start.start()
            result["receipt"] = {"relayed": 0, "reason": "node-starting"}
            return result
        maintenance = ((doc or {}).get("state") or {}).get("maintenance") or {}
        handled = maintenance.get("handled_host_revision") or 0
        if through is None:
            through = self._node_host_pending(doc, requested=True) or int(handled)
        batch = "b-" + hashlib.sha256(json.dumps([target["holder_instance_id"], through, recovery])
                                      .encode("utf-8")).hexdigest()[:12]
        receipt = self._relay_send(target, self._node_prompt(batch, handled, through, recovery))
        error = receipt.get("error") if isinstance(receipt.get("error"), dict) else None
        if (error is None and receipt.get("outcome") == "in_progress"
                and isinstance(receipt.get("prompt_fingerprint"), str)):
            node.update(batch=batch, fingerprint=receipt["prompt_fingerprint"], sent_through=through,
                        attention_sent=target["attention"], recovery_input=recovery,
                        recovery_sent=(recovery or {}).get("seq", node.get("recovery_sent", 0)))
            self.events.append({"kind": "sideagent_node_batch", "batch": batch,
                                "target_holder": target["holder_instance_id"],
                                "host_revision_through": through, "host_holder": self.holder_instance_id,
                                "recovery_input": recovery,
                                "recovery_alerts": {ident: value for ident, value in
                                    (((doc or {}).get("state") or {}).get("alerts") or {}).get(
                                        "maintenance-returned", {}).get("inputs", {}).items()
                                    if ident.startswith("recovery#")},
                                "prompt_fingerprint": receipt["prompt_fingerprint"]})
            result["receipt"] = {"batch": batch, "target_session": session}
        else:
            reason = (error or {}).get("code") or "relay-unadmitted"
            self.events.append({"kind": "worker_event_relay_failed", "target_session": session,
                                "receipt": receipt})
            # Recorded once and not resent: the node is stopped and no other
            # starts until the binding changes.
            node.update(failed={"binding": fingerprint, "code": reason})
            self._maintenance_failure(reason, through, recovery, wake=False)
            self._node_to_host(binding, f"sideagent node {target['holder_instance_id']} did not admit "
                                        f"batch {batch} ({reason}); {self._unhandled(through)}")
            holder = target["holder_instance_id"]
            node.update(phase="stopping", batch=None, fingerprint=None)
            threading.Thread(target=self._stop_node, args=(holder,), daemon=True).start()
            result["receipt"] = {"relayed": 0, "reason": reason}
        return result

    def _unhandled(self, through: Any) -> str:
        maintenance = (((self._lifecycle_state() or {}).get("state") or {}).get("maintenance") or {})
        handled = maintenance.get("handled_host_revision") or 0
        handled = handled if isinstance(handled, int) else 0
        if isinstance(through, int) and through > handled:
            return f"host revision {handled + 1}..{through} not handled"
        return "no Host change left unhandled"

    def _node_to_host(self, binding: dict[str, Any], reason: str, record: bool = True) -> None:
        """Stage a node failure for the Host like a worker event: there is
        no node turn end to carry it, and an unknown outcome is the Host's to
        see. Caller holds ``worker_events_lock``."""
        if record and (self.node.get("batch") or self._node_host_pending(self._lifecycle_state()) is not None
                       or self._node_recovery_pending(self._lifecycle_state())):
            self._maintenance_failure(reason, self.node.get("sent_through") or
                                      self._node_host_pending(self._lifecycle_state()), wake=False)
        cursor = self.events.append({"kind": "sideagent_node_returned", "reason": reason})
        self.pending_worker_events.append({
            "schema": WORKER_EVENT_SCHEMA, "event_id": f"{binding['platform']}/{binding['session']}/node/{cursor}",
            "kind": "node", "platform": binding["platform"], "session": binding["session"],
            "repo": self.args.repo, "reason": reason, "event_cursor": cursor,
            "staged_at": round(time.time(), 3), "host_owned": True})

    def _node_prompt(self, batch: str, handled: Any, through: int, recovery: dict[str, Any] | None = None) -> str:
        lines = [f"{RELAY_SCHEMA}: maintenance node batch {batch} from the {self.host_name} Host holder "
                 f"{self.args.session}"]
        if isinstance(handled, int) and through > handled:
            lines.append(f"Host business changes: host revision {handled + 1}..{through}; "
                         "`state view --role sideagent` lists them as pending_host_changes. "
                         "Later Host changes are not in this batch.")
        state_file = Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json"
        tool = self._state_tool()
        state = (f"python3 {shlex.quote(tool)} state" if tool
                 else "python3 <Project Runner>/scripts/kaola-dispatch.py state")
        lines.append(f"State file: {state_file}. State tool: `{state} ... --file {shlex.quote(str(state_file))}`; "
                     f"`{state} view --role sideagent --file {shlex.quote(str(state_file))}` reads it.")
        lines.append("Checkpoint only this batch's selected input ids, verbatim. Task ids read as recovery "
                     "sources are not extra inputs. With no selected business changes, emit no business entries.")
        lines.append("For ordinary Host business inputs, read the related tasks and real receipts, "
                     "apply each input with the state tool or retain it at a current record that names "
                     "its next reader. `applied` names only current records this node's holder wrote "
                     "through an authorized state operation, or `retired:<kind>/<id>` for its authorized "
                     "removal. Use `retained` for an unchanged Host record with `next`, `owner` or `wait`; "
                     "do not rewrite it just for accounting. Record one checkpoint naming every input: "
                     f"`{state} checkpoint --file {shlex.quote(str(state_file))} --writer sideagent "
                     f"--source {batch} --batch {batch} --through-host-revision {through} "
                     f"--entries '[{{\"input\": ID, \"retained\": \"tasks/ID\" or \"section/NAME\"}}, ...]'`.")
        if recovery:
            lines.append(f"Recovery input recovery#{recovery['seq']}: {json.dumps(recovery, sort_keys=True)}. "
                         f"Use --recovery-seq {recovery['seq']} in this batch's checkpoint. Read original current "
                         f"sources: {Path(self.args.repo) / 'AGENTS.md'}, "
                         f"{Path(self.args.repo) / '.kaola/delegator-heartbeat.json'}, Workflow state and "
                         "the main checkout's immutable mission ledger; task dispatch locators lead to the "
                         f"original index and Runner records under {self.record_dir.parent.parent.parent}. "
                         "Check current goal/grants (authorization), pending decisions/duties (duties), and "
                         "task-dispatch-result-reclaim links (links). Record one entry with input recovery#N, "
                         "checked:{authorization:[original refs],duties:[original refs],links:[original refs]}, "
                         "and unavailable:{scope:reason} for a scope whose originals cannot be read. "
                         "A recovery entry accepts only input, checked, unavailable and optional applied; "
                         "never retained. Put each scope in checked or unavailable, never both. "
                         "Unavailable originals stay Host recovery obligations; empty sources cannot PASS. "
                         "Related recovery alerts may be checked in separate scoped entries; do not clear "
                         "unread, newer or unrelated alert inputs. Preserve original Host retirement references.")
        lines.append("Role limits: you are a maintenance node, not the Host or a worker. Records you write "
                     "carry source pointers (record ids, receipt or log paths, event ids), never a restated, "
                     "summarized or judged worker result; the Host reads originals. Do not dispatch, start "
                     "or send to any session; exact-stop only a finished worker whose reclaim the Host "
                     "recorded. Do not author or allocate tasks, and grant, accept, "
                     "retire or decide nothing the Host has not recorded. Put anything that needs a Host "
                     "judgment in a decision or alert owned by the Host. Do not wait for workers or the "
                     "Host. Checkpoint once, report any partial result in your final reply, then end "
                     "the turn; the carrier stops this node. Do not write a second empty or replayed "
                     "checkpoint or prolong the turn with script-source investigation.")
        return "\n".join(lines)

    def _state_tool(self) -> str | None:
        """The Project Runner state tool beside this holder: the source
        checkout keeps it in the same directory, an installed Skill set in
        the sibling `kaola-project-runner` Skill."""
        binding = (((self._lifecycle_state() or {}).get("state") or {}).get("sideagent") or {})
        named = (binding.get("recipe") or {}).get("state_tool") if isinstance(binding, dict) else None
        here = Path(__file__).resolve().parent
        for candidate in ([Path(named)] if isinstance(named, str) and os.path.isabs(named) else []) + [
                here / "kaola-dispatch.py", here.parent.parent / "kaola-project-runner" / "scripts" / "kaola-dispatch.py"]:
            if candidate.is_file():
                return str(candidate)
        return None

    def _settle_node_batch(self, ends: list[dict[str, Any]]) -> None:
        """At the turn end that carried a node batch, settle the batch from
        that node's own checkpoint. Caller holds ``worker_events_lock``.

        The node's turn end reaches the Host (once, at its safe boundary)
        when the checkpoint is missing or partial, or when the node changed
        the Host view's attention, with a record it wrote, to something the
        Host has not seen. A verified batch that changed no attention stays
        quiet."""
        node = self.node
        if not node.get("batch"):
            return
        for end in ends:
            if (end.get("holder_instance_id") != node.get("holder")
                    or end.get("turn_fingerprint") != node.get("fingerprint")):
                continue
            doc, body, _ = read_heartbeat_file(Path(self.args.repo) / ".kaola" / "heartbeat-prompt.json")
            doc = doc if isinstance(doc, dict) and doc.get("schema") == HEARTBEAT_STATE_SCHEMA else None
            last = (((doc or {}).get("state") or {}).get("maintenance") or {}).get("last_checkpoint")
            ours = (isinstance(last, dict) and last.get("batch") == node["batch"]
                    and (last.get("node") or {}).get("holder_instance_id") == node["holder"])
            covered = ((last.get("host_revision") or {}).get("through") if ours else None)
            sent = node.get("sent_through") or 0
            # The range comes from the node's own flag; the batch it was sent
            # is the carrier's fact. An omitted or lowered range left Host
            # changes unhandled, which the next batch would not re-select.
            short_range = ours and not (isinstance(covered, int) and covered >= sent)
            recovery = node.get("recovery_input")
            recovery_covered = (not recovery or (ours and (last.get("recovery") or {}).get("input") == recovery
                                and f"recovery#{recovery['seq']}" in (last.get("settled") or [])))
            verified = bool(ours and last.get("verified") and not short_range and recovery_covered
                            and end.get("turn_outcome") == "turn_completed")
            attention = attention_fingerprint(body) if doc else None
            changed = (verified and attention is not None and attention != node.get("attention_sent")
                       and attention != self.host_attention_seen
                       and self._node_wrote_attention(doc, body, node["holder"]))
            if verified and not changed:
                end["node_quiet"] = True
            else:
                end["host_owned"] = True
                if changed:
                    detail = "verified; Host attention changed"
                elif short_range:
                    detail = (f"checkpoint partial: host revision "
                              f"{(covered if isinstance(covered, int) else 0) + 1}..{sent} not handled")
                else:
                    detail = "checkpoint partial" if ours else "checkpoint missing"
                end["reason"] = f"{end.get('reason')} maintenance batch {node['batch']} {detail}"
            self.events.append({"kind": "sideagent_node_settled", "batch": node["batch"],
                                "holder": node["holder"], "checkpoint": "verified" if verified
                                else "partial" if ours else "missing",
                                "host_revision_through": sent,
                                **({"checkpoint_through": covered} if ours else {}),
                                "host_woken": bool(end.get("host_owned")),
                                **({"attention_changed": True} if changed else {})})
            if not verified:
                self._maintenance_failure("checkpoint-partial" if ours else "checkpoint-missing", sent,
                                          recovery, wake=False)
            holder = node["holder"]
            node.update(phase="stopping", batch=None, fingerprint=None)
            threading.Thread(target=self._stop_node, args=(holder,), daemon=True).start()

    @staticmethod
    def _node_wrote_attention(doc: dict[str, Any] | None, body: str | None, holder: str) -> bool:
        """Whether a Host-view attention item is a record this node wrote.
        The Host's own writes during the batch change attention too, and are
        not news to it."""
        try:
            rows = json.loads(body or "").get("attention")
        except (ValueError, AttributeError):
            return False
        state = (doc or {}).get("state") or {}
        for row in rows if isinstance(rows, list) else []:
            records = state.get(row.get("kind")) if isinstance(row, dict) else None
            record = records.get(row.get("id")) if isinstance(records, dict) else None
            if isinstance(record, dict) and record.get("writer_holder") == holder:
                return True
        return False

    def _node_directory(self, platform: str, session: str) -> Path | None:
        """The node session's record directory. Its holder may have written
        under any record root (legacy TMPDIR, fixed or live-holder roots), so
        the lookup spans every root with this Host's own root first."""
        try:
            return acp_paths.find_directory(platform, session, self.args.repo,
                                            self.record_dir.parent.parent.parent,
                                            all_roots=True)
        except acp_paths.RecordRootMismatch:
            return None

    def _node_record(self, binding: dict[str, Any]) -> dict[str, Any] | None:
        directory = self._node_directory(binding["platform"], binding["session"])
        if directory is None:
            return None
        try:
            record = json.loads((directory / "record.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return record if isinstance(record, dict) else None

    def _node_holder_alive(self, binding: dict[str, Any], holder: Any) -> bool:
        # The process, not the record state: a holder that wrote "stopped"
        # but still runs owns the session, and a fresh start is refused.
        record = self._node_record(binding)
        return bool(record and record.get("holder_instance_id") == holder
                    and isinstance(record.get("holder_pid"), int) and process_alive(record["holder_pid"]))

    def _start_node(self, binding: dict[str, Any], fingerprint: str) -> None:
        recipe = binding["recipe"]
        env = dict(os.environ)
        for key in (HEARTBEAT_HOST_ENV, HEARTBEAT_HOST_SOCKET_ENV, "KAOLA_ACP_CHILD_RECORD"):
            env.pop(key, None)
        env[DISPATCHER_ENV] = json.dumps(self.dispatcher_identity(), sort_keys=True)
        receipt: Any = None
        code: Any = None
        try:
            run = subprocess.run([recipe["runner"], *recipe["argv"]], cwd=self.args.repo, env=env,
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                 timeout=NODE_START_TIMEOUT)
            code = run.returncode
            for line in reversed(run.stdout.splitlines()):
                try:
                    receipt = json.loads(line)
                    break
                except ValueError:
                    continue
        except (OSError, subprocess.SubprocessError) as exc:
            receipt = {"error": {"code": "node-start-error", "message": str(exc)}}
        holder = receipt.get("holder_instance_id") if isinstance(receipt, dict) else None
        ok = (code == 0 and isinstance(holder, str) and holder
              and (receipt.get("result") not in ("refused", "failed")))
        with self.worker_events_lock:
            if ok:
                self.node.update(phase="running", holder=holder, batch=None, fingerprint=None)
                self.node.setdefault("holders", []).append(holder)
                del self.node["holders"][:-8]
                self.events.append({"kind": "sideagent_node_started", "holder": holder,
                                    "session": binding["session"]})
            else:
                error = receipt.get("error") if isinstance(receipt, dict) else None
                live_holder: Any = None
                record = self._node_record(binding) or {}
                pid = record.get("holder_pid")
                if (isinstance(error, dict) and error.get("code") == "session-exists"
                        and error.get("identity") == "verified"
                        and pid == error.get("holder_pid")
                        and process_alive(pid)
                        and record.get("repo") == self.args.repo
                        and record.get("session_role") in SIDEAGENT_ROLES
                        and isinstance(record.get("holder_instance_id"), str)
                        and record.get("holder_instance_id")):
                    live_holder = record["holder_instance_id"]
                if (live_holder and (record.get("dispatcher") or {}).get("holder_instance_id")
                        == self.holder_instance_id):
                    # The runner refused a session this carrier dispatched:
                    # adopt the verified live holder instead of orphaning it.
                    self.node.update(phase="running", holder=live_holder,
                                     batch=None, fingerprint=None)
                    self.node.setdefault("holders", []).append(live_holder)
                    del self.node["holders"][:-8]
                    self.events.append({"kind": "sideagent_node_adopted", "holder": live_holder,
                                        "session": binding["session"]})
                elif live_holder:
                    # A live verified node another holder dispatched: stop is
                    # unconfirmed until that holder is gone, then a start can
                    # proceed (the late-confirm path clears stop_unconfirmed).
                    self.node.update(phase="stopped", stop_unconfirmed={"holder": live_holder})
                    doc = self._lifecycle_state()
                    self._maintenance_failure("old-node-live", self._node_host_pending(doc),
                                              self._node_recovery_pending(doc))
                    self.events.append({"kind": "sideagent_node_start_refused_live",
                                        "holder": live_holder, "session": binding["session"]})
                else:
                    # One failure is recorded, not retried: a later start needs a
                    # changed binding or recipe from an authorized controller.
                    self.node.update(phase="stopped", failed={"binding": fingerprint, "code": code})
                    self.events.append({"kind": "sideagent_node_start_failed",
                                        "session": binding["session"], "code": code,
                                        "receipt": receipt if isinstance(receipt, dict) else None})
                    self._node_to_host(binding, f"sideagent node start failed (exit {code}); "
                                                f"{self._unhandled(self._node_host_pending(self._lifecycle_state()))}; "
                                                "no node starts until the binding or recipe changes")
        self._kick_worker_events()

    def _stop_node(self, holder: str, wait: float | None = None) -> None:
        wait = NODE_STOP_CONFIRM_SECONDS if wait is None else wait
        binding = self._node_binding() or {}
        receipt: dict[str, Any] = {}
        target = None
        if binding:
            record = self._node_record(binding)
            if record and record.get("holder_instance_id") == holder:
                directory = self._node_directory(binding["platform"], binding["session"])
                target = acp_paths.socket_path(directory) if directory is not None else None
        if target is not None:
            try:
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    connection.settimeout(wait)
                    connection.connect(str(target))
                    connection.sendall(canonical({"op": "stop", "request_id": secrets.token_hex(8),
                                                  "params": {"expected_holder_instance_id": holder}}) + b"\n")
                    buffer = bytearray()
                    while b"\n" not in buffer:
                        data = connection.recv(65536)
                        if not data:
                            break
                        buffer.extend(data)
                finally:
                    connection.close()
                line = bytes(buffer.partition(b"\n")[0])
                receipt = json.loads(line.decode("utf-8", "replace")) if line.strip() else {}
            except (OSError, ValueError) as exc:
                receipt = {"error": {"code": "node-stop-unreachable", "message": str(exc)}}
        deadline = time.monotonic() + wait
        alive = bool(binding) and self._node_holder_alive(binding, holder)
        while alive and time.monotonic() < deadline:
            time.sleep(0.5)
            alive = self._node_holder_alive(binding, holder)
        with self.worker_events_lock:
            if alive:
                self.node.update(phase="stopped", stop_unconfirmed={"holder": holder})
                self.events.append({"kind": "sideagent_node_stop_unconfirmed", "holder": holder,
                                    "receipt": receipt})
                self._maintenance_failure("stop-unconfirmed", self.node.get("sent_through"),
                                          self.node.get("recovery_input"))
            else:
                self.node.update(phase="stopped")
                self.events.append({"kind": "sideagent_node_stopped", "holder": holder,
                                    "receipt": {key: receipt.get(key) for key in ("stopped", "error")
                                                if key in receipt}})
        self._kick_worker_events()

    def _reclaim_node(self) -> None:
        """A node is this carrier's own per-batch session, not a dispatched
        worker: it ends with the carrier in every stop mode. Its start runs
        from this holder, not the agent, so no spawn line or agent sweep
        reaches it; a start still in flight is waited for first."""
        start = self.node_start
        if start is not None and start.is_alive():
            start.join(NODE_RECLAIM_SECONDS)
        with self.worker_events_lock:
            holder = self.node.get("holder") if self.node.get("phase") in ("running", "stopping") else None
            if holder:
                self.node.update(phase="stopping", batch=None, fingerprint=None)
        binding = self._node_binding() if holder is None and start is not None and start.is_alive() else None
        if binding:
            # Still starting: its record already names this carrier.
            record = self._node_record(binding) or {}
            if (record.get("dispatcher") or {}).get("holder_instance_id") == self.holder_instance_id:
                holder = record.get("holder_instance_id")
        if isinstance(holder, str) and holder:
            self._stop_node(holder, NODE_RECLAIM_SECONDS)

    # -- Issue #264: post-compaction Skill reread ---------------------------

    def op_compact_notice(self, params: dict[str, Any]) -> dict[str, Any]:
        """KPR local hook operation, never a vendor ACP method.

        The installed Droid and Cursor ACP paths put the ACP id in the
        native hook input. Only an exact project precompact hook can stage
        this conservative notice. It is not a completed-compaction signal.
        """
        def refuse(reason: str) -> dict[str, Any]:
            return {"notice_pending": False, "completion": "unconfirmed",
                    "mutation_performed": False, "reason": reason}

        event = {"droid": "PreCompact", "cursor-cli": "preCompact"}.get(self.args.platform)
        if event is None or params.get("hook_event_name") != event:
            return refuse("unsupported-project-hook")
        repo = str(Path(self.args.repo).resolve())
        if self.args.platform == "cursor-cli":
            data_root = Path(os.environ.get("CURSOR_DATA_DIR") or Path.home() / ".cursor")
            key = re.sub(r"[^a-zA-Z0-9]+", "-", repo).strip("-")
            hook_root = str(data_root / "projects" / key)
            root_matches = params.get("hook_workspace_roots") == [hook_root]
        else:
            root_matches = params.get("hook_cwd") == repo
        paths = params.get("task_skill_paths")
        platform_path = params.get("platform_skill_path")
        if (not isinstance(paths, list) or not paths or not isinstance(platform_path, str)
                or any(not isinstance(p, str) or not Path(p).is_absolute()
                       or not Path(p).is_file() for p in [platform_path, *paths])):
            return refuse("full-skill-paths-required")
        module = compact_module()
        if module is None:
            return refuse("no-compact-module")
        with self.worker_events_lock:
            with self.lock:
                if (self.state != "ready" or self.stop_requested
                        or self.agent.proc is None or self.agent.exited.is_set()):
                    return refuse("holder-not-ready")
                if (params.get("expected_holder_instance_id") != self.holder_instance_id
                        or not self.acp_session_id
                        or params.get("expected_acp_session_id") != self.acp_session_id
                        or params.get("hook_session_id") != self.acp_session_id
                        or params.get("project_root") != repo or not root_matches):
                    return refuse("hook-target-mismatch")
                prior = self.turn.get("request_id")
                if (not self.turn["active"] or prior is None
                        or params.get("expected_prior_turn_request_id") != prior):
                    return refuse("active-hook-turn-required")
                pending = self.compact_notice_pending
                if pending is not None:
                    # One current obligation. Never replace unknown admission
                    # or failed original work with a new hook's target.
                    same = pending["prior_turn_request_id"] == prior
                    return {"notice_pending": True, "completion": "unconfirmed",
                            "mutation_performed": False,
                            "new_notice_accepted": same,
                            "reason": "coalesced" if same else "prior-notice-unresolved"}
                if self.compact_reload is None:
                    self.compact_reload = module.CompactReloadTracker()
                self.compact_reload.observe(module.CompactSignal(
                    "project-precompact-notice", self.acp_session_id, None))
                self.compact_notice_pending = {
                    "prior_turn_request_id": prior,
                    "holder_instance_id": self.holder_instance_id,
                    "acp_session_id": self.acp_session_id,
                    "platform_skill_path": platform_path,
                    "task_skill_paths": list(paths), "write_unknown": False}
                # Record staging before a response can admit the reminder.
                self.events.append({"kind": "compact_project_notice", "completion": "unconfirmed",
                                    "session_id": self.acp_session_id, "turn_request_id": prior})
        return {"notice_pending": True, "notice_recorded": True,
                "completion": "unconfirmed", "acp_mutation_performed": False,
                "prior_turn_request_id": prior}

    def _attempt_compact_notice(self, notice: dict[str, Any]) -> dict[str, Any]:
        if notice["write_unknown"]:
            return {"delivered": False, "reason": "notice-write-unknown"}
        with self.lock:
            if (self.turn["active"] or self.turn.get("request_id") != notice["prior_turn_request_id"]
                    or self.turn.get("outcome") != "turn_completed"
                    or self.turn.get("stop_reason") != "end_turn" or self.turn.get("error")):
                return {"delivered": False, "reason": "notice-original-work-not-successful"}
        files = [notice["platform_skill_path"], *notice["task_skill_paths"]]
        text = ("A native PreCompact notice occurred during the prior work. "
                "Compaction completion is unconfirmed. Before you answer, call the available "
                "file read tool and read the full current installed applicable Skill files: "
                + json.dumps(files) + ". Do not use remembered or cached Skill content. "
                "Then continue the current task from its durable records. "
                "Do not restart completed work.")
        if self.session_role == "host":
            if not self.host_entry:
                return {"delivered": False, "reason": "notice-host-entry-absent"}
            text = self.host_entry + "\n" + text
        try:
            prompt = self.op_prompt({"text": text, "wait": False,
                                     "expected_holder_instance_id": notice["holder_instance_id"],
                                     "expected_acp_session_id": notice["acp_session_id"],
                                     "expected_prior_turn_request_id": notice["prior_turn_request_id"],
                                     "require_successful_prior_turn": True})
        except Exception:
            notice["write_unknown"] = True
            return {"delivered": False, "reason": "notice-write-unknown"}
        if (prompt.get("error") or prompt.get("outcome") != "in_progress"
                or prompt.get("mutation_performed") is not True):
            if (prompt.get("mutation_performed") is not False
                    or (prompt.get("error") or {}).get("code") == "acp-write-failed"):
                # A partial stdio write or lost admission response cannot be
                # replayed from a later boundary.
                notice["write_unknown"] = True
            return {"delivered": False, "reason": "notice-admission-unconfirmed",
                    "receipt": prompt}
        self.events.append({"kind": "compact_project_notice_admitted",
                            "completion": "unconfirmed", "read_use": "unverified",
                            "original_turn_request_id": notice["prior_turn_request_id"],
                            "turn_request_id": prompt.get("turn_request_id"),
                            "prompt_fingerprint": prompt.get("prompt_fingerprint")})
        return {"delivered": True, "prompt_fingerprint": prompt.get("prompt_fingerprint")}

    def _observe_compact_signal(self, message: dict[str, Any]) -> None:
        """Recognize one completed compaction and owe one installed-Skill reread.

        Only a real, session-bound, completed signal counts. A start, a
        failure, a token drop, or assistant prose never counts. A compact record
        that streams while this holder is still starting is resume/history
        replay, not a fresh completion, and is ignored. The pending flag
        coalesces repeats; the occurrence scalar suppresses an adjacent
        duplicate. Delivery waits for a safe boundary and never interrupts.
        """
        module = compact_module()
        if module is None:
            return
        if self.state != "ready":
            # ``session/load`` and ``session/resume`` may replay a completed
            # compaction record. Never turn history into a fresh reload.
            signal = module.classify(message, self.args.platform)
            if signal is not None:
                self.events.append({"kind": "compact_reload_replay_ignored",
                                    "source": signal.source, "state": self.state})
            return
        signal = module.classify(message, self.args.platform)
        if signal is None:
            return
        if not module.is_same_session(signal, self.acp_session_id):
            self.events.append({"kind": "compact_reload_foreign_session",
                                "source": signal.source,
                                "signal_session": signal.session_id})
            return
        with self.worker_events_lock:
            if self.compact_reload is None:
                self.compact_reload = module.CompactReloadTracker()
            if not self.compact_reload.observe(signal):
                return
        cursor = self.events.append({"kind": "compact_reload_detected",
                            "source": signal.source,
                            "occurrence_id": signal.occurrence_id,
                            "session_id": signal.session_id, "holder": self.holder_instance_id,
                            "role": self.session_role, "signal": message})
        self.write_record()
        if self.session_role == "host":
            self._register_compact_maintenance(cursor)
        self._deliver_compact_reload()

    def _deliver_compact_reload(self) -> dict[str, Any]:
        """Deliver the one pending reread prompt at a safe boundary.

        This reuses ``op_prompt`` and the session's own applicable Skill. A Host
        opens Project Runner through its measured ``host_entry``. Every other
        role names its own installed platform Skill and requires the active
        role/task Skill too, so a worker never opens the Host control-plane
        Skill. It never cancels, restarts, or replays. A busy turn or a dead
        agent keeps the flag for the next boundary.

        The existing ``worker_events_lock`` serializes the tracker. The inflight
        slot is a boolean because an occurrence-less signal must still hold it.
        One lock hold settles the obligation and clears the slot, so no later
        admission can slip into the gap.
        """
        module = compact_module()
        if module is None:
            return {"delivered": False, "reason": "no-compact-module"}
        with self.worker_events_lock:
            tracker = self.compact_reload
            if tracker is None or not tracker.pending:
                return {"delivered": False, "reason": "no-pending-reload"}
            if self.compact_reload_inflight:
                return {"delivered": False, "reason": "reload-inflight"}
            self.compact_reload_inflight = True
            occurrence = tracker.pending_id
            pending_seq = tracker.pending_seq
            self.compact_reload_inflight_id = occurrence
            notice = getattr(self, "compact_notice_pending", None)
        result: dict[str, Any] = {"delivered": False, "reason": "not-attempted"}
        settled = False
        try:
            result = self._attempt_compact_reload(module)
            settled = bool(result.get("delivered")
                           or result.get("reason") in
                           ("native-route-owned",))
        finally:
            with self.worker_events_lock:
                if settled:
                    # The sequence keeps a newer occurrence-less obligation
                    # pending even though its id is also None.
                    tracker.mark_delivered_occurrence(occurrence, pending_seq)
                    if (result.get("delivered")
                            and getattr(self, "compact_notice_pending", None) is notice):
                        self.compact_notice_pending = None
                self.compact_reload_inflight = False
                self.compact_reload_inflight_id = None
        return result

    def _attempt_compact_reload(self, module: Any) -> dict[str, Any]:
        """One bounded reload admission attempt. Caller holds the inflight slot."""
        if self.args.platform in NATIVE_COMPACT_RECOVERY_PLATFORMS:
            # This runtime already injects its own compact recovery. A second
            # ACP-driven reload would duplicate the working native path. Record
            # the fact and let the native path own the reread.
            self.events.append({"kind": "compact_reload_native_owned",
                                "platform": self.args.platform})
            return {"delivered": False, "reason": "native-route-owned"}
        notice = getattr(self, "compact_notice_pending", None)
        if notice is not None:
            return self._attempt_compact_notice(notice)
        if self.turn["active"]:
            return {"delivered": False, "reason": "prompt-in-progress"}
        if self.stop_requested or self.agent.proc is None or self.agent.exited.is_set():
            return {"delivered": False, "reason": "agent-not-running"}
        if self.session_role == "host":
            if not self.host_entry:
                # A Host with no measured entry has no automatic wake.
                self.events.append({"kind": "compact_reload_entry_absent"})
                return {"delivered": False, "reason": "host-entry-absent"}
            text = module.host_reload_prompt(self.host_entry)
        else:
            text = module.worker_reload_prompt(self.installed_skill_path)
            if self.installed_skill_path is None:
                text += (" The holder runs from source; the installed platform Skill file "
                         "location is not known here. Locate the current installed "
                         + self.args.platform + "-kaola-project-runner Skill through your "
                         "available Skill catalog or the active task records, then read "
                         "its full SKILL.md. Do not treat the source checkout directory "
                         "as an installed Skill file.")
        prompt = self.op_prompt({"text": text, "wait": False})
        if prompt.get("error") or prompt.get("outcome") != "in_progress":
            return {"delivered": False, "error": prompt.get("error") or prompt}
        self.events.append({"kind": "compact_reload_delivered",
                            "session_role": self.session_role,
                            "skill_path": (None if self.session_role == "host"
                                           else self.installed_skill_path),
                            "prompt_fingerprint": prompt.get("prompt_fingerprint")})
        return {"delivered": True,
                "prompt_fingerprint": prompt.get("prompt_fingerprint")}

    def _kick_worker_events(self) -> None:
        """Offer what is waiting at this new boundary: a node to the relay,
        anything the Host owns to an idle Host."""
        if self.stop_requested:
            return
        try:
            if not self.turn["active"] and self.agent.proc is not None and not self.agent.exited.is_set():
                self._deliver_worker_events()
            else:
                with self.worker_events_lock:
                    self._relay_pass()
        except Exception as exc:  # a node boundary must not take the holder down
            self.events.append({"kind": "sideagent_node_kick_failed", "error": str(exc)})
        self._deliver_compact_reload()

    def _deliver_worker_events(self) -> dict[str, Any]:
        """Deliver every staged event as one ordinary prompt through the
        normal admission path. A busy or dead-agent host keeps events staged
        for the next boundary or resume; nothing here bypasses op_prompt.

        Issue #90: admission and the marking of what it delivered are ONE hold
        of ``worker_events_lock``. ``op_prompt`` starts the turn's response
        thread before it returns, so a Host that answers at once runs
        ``_worker_event_turn_end`` - which takes this same lock - while this
        call is still inside it. The callback therefore waits and then sees a
        fully marked notification turn, instead of concluding there was none
        and delivering the same events a second time. The one hold is also what
        keeps two concurrent deliveries off the same staged events: the second
        finds them already marked and has nothing to send. Marking only after a
        successful admission means a refused prompt leaves nothing to undo. The
        lock order is ``worker_events_lock`` then ``self.lock`` (taken inside
        ``op_prompt``); no path takes them the other way round.
        """
        with self.worker_events_lock:
            relay = self._relay_pass()
            staged = [item for item in self.pending_worker_events
                      if "prompt_fingerprint" not in item and "relayed" not in item
                      and (item.get("host_owned") or not (
                          relay.get("live") and item.get("session") != relay.get("session")))]
            overflow_ready = (
                self.overflow_generation > self.overflow_confirmed_generation
                and self.overflow_inflight_generation is None)
            overflow_generation = self.overflow_generation
            if not staged and not overflow_ready:
                return {"delivered": False, "reason": "queue-empty",
                        **({"relay": relay["receipt"]} if relay.get("receipt") else {})}
            if self.agent.proc is None or self.agent.exited.is_set():
                return {"delivered": False, "reason": "agent-not-running"}
            if self.turn["active"]:
                return {"delivered": False, "reason": "prompt-in-progress"}
            text, meta = self._heartbeat_payload(staged, overflow_ready)
            prompt = self.op_prompt({"text": text, "wait": False})
            error = prompt.get("error")
            if error or prompt.get("outcome") != "in_progress":
                # Nothing was marked, so there is nothing to undo: the events
                # stay staged for the next boundary or a resume, exactly as a
                # refused or unwritten prompt always left them.
                return {"delivered": False, "error": error or prompt}
            fingerprint = prompt.get("prompt_fingerprint")
            self.host_attention_seen = meta.get("attention_fingerprint")
            for item in staged:
                item["prompt_fingerprint"] = fingerprint
            if overflow_ready:
                self.overflow_inflight_generation = overflow_generation
                self.overflow_inflight_fingerprint = fingerprint
            delivered: dict[str, Any] = {
                "kind": "worker_event_delivered",
                "event_ids": [item["event_id"] for item in staged],
                "prompt_fingerprint": fingerprint,
                **meta,
            }
            if overflow_ready:
                delivered["overflow_full_check"] = True
                delivered["overflow_generation"] = overflow_generation
            self.events.append(delivered)
        return {"delivered": True, "prompt_fingerprint": fingerprint,
                "count": len(staged), "overflow_full_check": bool(overflow_ready)}

    def _remember_confirmed_worker_events(self, confirmations: dict[str, int]) -> None:
        """Bounded, insertion-ordered cache of confirmed ids and the event-log
        cursor each confirmation was recorded at (Issue #90). The caller holds
        ``worker_events_lock``, or is the single-threaded resume."""
        for event_id, cursor in confirmations.items():
            self.confirmed_worker_events.pop(event_id, None)
            self.confirmed_worker_events[event_id] = cursor
        while len(self.confirmed_worker_events) > HEARTBEAT_CONFIRMED_MEMORY:
            self.confirmed_worker_events.pop(next(iter(self.confirmed_worker_events)))
            # From here on this cache is no longer the whole confirmed truth,
            # so a miss has to be checked against the records it was built from.
            self.confirmed_worker_events_partial = True

    def _was_worker_event_confirmed(self, event_id: str) -> bool:
        """Has a completed Host turn already confirmed this event (Issue #90)?

        The bounded cache answers the ordinary case outright. It is bounded, so
        a miss only means "not confirmed" while nothing has been evicted; past
        that the answer is the `worker_event_confirmed` records the cache was
        built from - the only place this holder persists anything. The promise
        is therefore exactly as wide as the RETAINED event log, the same horizon
        that already bounds resume redelivery, rather than the last N ids. A
        found id is cached so a repeated retry costs one lookup, not one scan.
        Caller holds ``worker_events_lock``.
        """
        cursor = self.confirmed_worker_events.get(event_id)
        if cursor is not None:
            oldest = self.events.oldest_cursor()
            if oldest is not None and cursor >= oldest:
                return True
            # Rotation dropped the record this entry summarised. The holder can
            # no longer show that confirmation, so the cache must not keep
            # answering from it - and it is no longer a complete summary.
            self.confirmed_worker_events.pop(event_id, None)
            self.confirmed_worker_events_partial = True
        if not self.confirmed_worker_events_partial:
            return False
        for entry in self.events.read_since(0, None):
            if entry.get("kind") != "worker_event_confirmed":
                continue
            ids = entry.get("event_ids")
            if isinstance(ids, list) and event_id in ids:
                self._remember_confirmed_worker_events(
                    {event_id: entry.get("cursor") or 0})
                return True
        return False

    def _worker_event_turn_end(self, fingerprint: Any, outcome: str | None) -> None:
        """At a turn boundary: confirm the events this turn delivered, then
        flush whatever staged meanwhile. A notification turn that did not
        complete leaves its events staged - no retry loop; the next healthy
        boundary, a newly staged event, or a resume redelivers them.

        Overflow confirmation is the generation snapped at delivery, not the
        current generation: overflow during this notification still needs
        the next wake.
        """
        confirmed: list[str] = []
        was_notification = False
        overflow_confirmed_generation: int | None = None
        with self.worker_events_lock:
            hit = [item for item in self.pending_worker_events
                   if fingerprint is not None
                   and item.get("prompt_fingerprint") == fingerprint]
            overflow_hit = bool(
                fingerprint is not None
                and self.overflow_inflight_fingerprint == fingerprint)
            was_notification = bool(hit) or overflow_hit
            if hit and outcome == "turn_completed":
                confirmed = [item["event_id"] for item in hit]
                # Issue #90: durable first. The event log is the only place this
                # holder persists anything, so the confirmation is recorded
                # before the events leave the pending list and before a retry
                # can be answered `confirmed` - never the other way round, where
                # a crash in between would drop the event and the proof with it.
                cursor = self.events.append({"kind": "worker_event_confirmed",
                                             "event_ids": confirmed})
                for item in hit:
                    self.pending_worker_events.remove(item)
                self._remember_confirmed_worker_events(
                    {event_id: cursor for event_id in confirmed})
            elif hit:
                for item in hit:
                    item.pop("prompt_fingerprint", None)
            if overflow_hit:
                if outcome == "turn_completed":
                    overflow_confirmed_generation = self.overflow_inflight_generation
                    if overflow_confirmed_generation is not None:
                        self.events.append(
                            {"kind": "worker_event_overflow_confirmed",
                             "generation": overflow_confirmed_generation})
                        self.overflow_confirmed_generation = overflow_confirmed_generation
                self.overflow_inflight_generation = None
                self.overflow_inflight_fingerprint = None
        if not was_notification or outcome == "turn_completed":
            if self.agent.proc is not None and not self.agent.exited.is_set():
                self._deliver_worker_events()
        # Issue #264: a compact completion that landed mid-turn is delivered
        # only now, at the turn boundary, and never inside the turn.
        self._deliver_compact_reload()

    def op_worker_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Carrier op on a Host holder: stage one worker event, then
        deliver when the host turn is already idle."""
        if not self.host_entry:
            return {"error": {"code": "worker-event-unsupported",
                              "message": "the event-driven heartbeat carrier needs a "
                                         "measured host Skill entry; this session's "
                                         f"platform {self.args.platform} declares none"}}
        kind = params.get("kind")
        platform = params.get("platform")
        session = params.get("session")
        repo = params.get("repo")
        reason = params.get("reason")
        cursor = params.get("event_cursor")
        request_id = params.get("request_id")
        if (kind not in WORKER_EVENT_KINDS or not isinstance(platform, str)
                or not platform or not isinstance(session, str) or not session
                or not isinstance(repo, str) or not repo
                or not isinstance(reason, str)
                or not isinstance(cursor, int) or isinstance(cursor, bool)
                or (request_id is not None
                    and (not isinstance(request_id, (str, int))
                         or isinstance(request_id, bool)))):
            return {"error": {"code": "worker-event-invalid",
                              "message": "worker_event needs kind "
                                         "terminated|idle|permission_required plus "
                                         "platform, session, repo, reason, and an integer "
                                         "event_cursor"}}
        event = {"schema": WORKER_EVENT_SCHEMA,
                 "event_id": f"{platform}/{session}/{kind}/{cursor}",
                 "kind": kind, "platform": platform, "session": session,
                 "repo": repo, "reason": reason, "event_cursor": cursor,
                 "staged_at": round(time.time(), 3)}
        if request_id is not None:
            event["request_id"] = request_id
        for key in ("holder_instance_id", "turn_fingerprint", "turn_outcome"):
            if isinstance(params.get(key), str) and params[key]:
                event[key] = params[key]
        with self.worker_events_lock:
            if self._was_worker_event_confirmed(event["event_id"]):
                # Issue #90: a completed Host turn already confirmed this exact
                # event and removed it from the pending list. `event_id` is
                # deterministic, so re-offering it is a retry of the same event,
                # not a new one; staging it again would prompt the Host twice.
                return {"event_id": event["event_id"], "duplicate": True,
                        "confirmed": True,
                        "pending": len(self.pending_worker_events)}
            if any(item.get("event_id") == event["event_id"]
                   for item in self.pending_worker_events):
                return {"event_id": event["event_id"], "duplicate": True,
                        "pending": len(self.pending_worker_events)}
            if is_turn_end(event):
                # Issue #255: a Sideagent turn end settles its relays before
                # admission, so a full queue never refuses the completion
                # that drains it.
                self._settle_relays([event])
            if len(self.pending_worker_events) >= HEARTBEAT_EVENT_CAP:
                queue_full = True
            else:
                queue_full = False
                self.pending_worker_events.append(event)
                pending = len(self.pending_worker_events)
        if queue_full:
            generation = self._record_overflow_full_check()
            receipt = {"error": {"code": "worker-event-queue-full",
                                 "capacity": HEARTBEAT_EVENT_CAP,
                                 "message": f"{HEARTBEAT_EVENT_CAP} worker events are "
                                            "already waiting for this host turn boundary"},
                       "overflow_full_check": True,
                       "generation": generation,
                       "pending": HEARTBEAT_EVENT_CAP}
            if (not self.turn["active"] and self.agent.proc is not None
                    and not self.agent.exited.is_set()):
                receipt.update(self._deliver_worker_events())
            return receipt
        self.events.append({"kind": "worker_event", "event": event})
        receipt: dict[str, Any] = {"event_id": event["event_id"], "staged": True,
                                   "pending": pending}
        if (not self.turn["active"] and self.agent.proc is not None
                and not self.agent.exited.is_set()):
            receipt.update(self._deliver_worker_events())
        elif self.turn["active"]:
            # A busy Host does not hold up routine events its Sideagent owns.
            with self.worker_events_lock:
                relay = self._relay_pass()
            if relay.get("receipt"):
                receipt["relay"] = relay["receipt"]
        return receipt

    @staticmethod
    def _overflow_generation_of(entry: dict[str, Any]) -> int | None:
        generation = entry.get("generation")
        if isinstance(generation, int) and not isinstance(generation, bool) and generation > 0:
            return generation
        return None

    def _restore_worker_events(self) -> None:
        """Resume redelivery: rebuild the pending list from this holder's own
        event log (staged without a matching confirmation) and deliver it into
        the resumed session. Detailed events remain at-least-once; pending
        full-check is last overflow generation minus last confirmed
        generation. Current generation is at least the confirmed
        generation, because rotation may drop older overflow records."""
        staged: list[dict[str, Any]] = []
        # Insertion-ordered so Issue #90's bounded retry cache keeps the most
        # recently confirmed ids, mapped to the cursor of the record that
        # confirmed them; membership tests read the same as a set.
        confirmed: dict[str, int] = {}
        overflow_generation = 0
        overflow_confirmed = 0
        compact_pending = {}
        for entry in self.events.read_since(0, None):
            kind = entry.get("kind")
            if (kind == "compact_reload_detected" and entry.get("role") == "host"
                    and entry.get("session_id") == self.acp_session_id):
                compact_pending[entry["cursor"]] = entry
            elif kind == "host_compact_maintenance_registered":
                through_cursor = entry.get("signal_cursor")
                if isinstance(through_cursor, int):
                    compact_pending = {cursor: signal for cursor, signal in compact_pending.items()
                                       if cursor > through_cursor}
            if kind == "worker_event":
                event = entry.get("event")
                if isinstance(event, dict) and isinstance(event.get("event_id"), str):
                    staged.append(event)
            elif kind == "worker_event_confirmed":
                ids = entry.get("event_ids")
                if isinstance(ids, list):
                    for event_id in ids:
                        if isinstance(event_id, str):
                            # re-insert so a re-confirmed id keeps the NEWEST
                            # position and cursor; plain `update` would keep the
                            # oldest of each.
                            confirmed.pop(event_id, None)
                            confirmed[event_id] = entry.get("cursor") or 0
            elif kind == "worker_event_overflow":
                generation = self._overflow_generation_of(entry)
                overflow_generation = (max(overflow_generation, generation)
                                       if generation is not None
                                       else overflow_generation + 1)
            elif kind == "worker_event_overflow_confirmed":
                generation = self._overflow_generation_of(entry)
                overflow_confirmed = (max(overflow_confirmed, generation)
                                      if generation is not None
                                      else overflow_confirmed + 1)
        pending: list[dict[str, Any]] = []
        seen: set[str] = set()
        for event in staged:
            if event["event_id"] in confirmed or event["event_id"] in seen:
                continue
            seen.add(event["event_id"])
            pending.append(event)
        # Rotated logs may drop older overflow facts while keeping a later
        # confirmation. Current generation cannot go backwards of confirmed.
        overflow_generation = max(overflow_generation, overflow_confirmed)
        if len(pending) > HEARTBEAT_EVENT_CAP:
            pending = pending[-HEARTBEAT_EVENT_CAP:]
            overflow_generation += 1
            self.events.append({"kind": "worker_event_overflow",
                                "generation": overflow_generation})
        if compact_pending and self.session_role == "host":
            self._register_compact_maintenance(max(compact_pending))
        self.pending_worker_events = pending
        self.confirmed_worker_events = {}
        self.confirmed_worker_events_partial = False
        self._remember_confirmed_worker_events(confirmed)
        self.overflow_generation = overflow_generation
        self.overflow_confirmed_generation = overflow_confirmed
        self.overflow_inflight_generation = None
        self.overflow_inflight_fingerprint = None
        overflow_pending = overflow_generation > overflow_confirmed
        if pending or overflow_pending:
            restored: dict[str, Any] = {
                "kind": "worker_event_restored",
                "event_ids": [event["event_id"] for event in pending],
            }
            if overflow_pending:
                restored["overflow_full_check"] = True
                restored["overflow_generation"] = overflow_generation
            self.events.append(restored)
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
        cancelled = option in (None, "cancelled", "cancel")
        outcome = {"outcome": "cancelled"} if cancelled else {
            "outcome": "selected", "optionId": option
        }
        written = self.agent.send_message(
            {"jsonrpc": "2.0", "id": entry["request_id"], "result": {"outcome": outcome}}
        )
        answered_at = round(time.time(), 3)
        self.pending_permissions.pop(key, None)
        if written:
            self.projection.add_answered_permission(
                answered_permission_view(entry, None if cancelled else option,
                                         answered_at, self.events.cursor))
        return {**entry, "answered_at": answered_at}

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
                                "option": option}, ts=entry["answered_at"])
            self.write_record()
            self.fanout_follow_delta()
            return {"permitted": request_id, "option": option,
                    "pending_permissions": list(pending.values())}

    def op_steer(self, params: dict[str, Any]) -> dict[str, Any]:
        """One noninterrupting input request for this exact session.

        Keep the original prompt owner. Native delivery can be processed in a
        later step or turn. Write, admission, completion and model adoption are
        separate facts. This operation never sends cancel or replays input.
        """
        method = (params.get("method") or "").strip()
        text = params.get("text") or ""
        standard_prompt = method == "session/prompt" and self.args.platform in ("devin", "droid")
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
                    "steer_confirmation": "none",
                    "error": {"code": "steer-unsupported",
                              "message": "this platform exposes no native steering entry; "
                                         "the text was not consumed"}}
        if not text.strip():
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "outcome": "steer_rejected", "steer_confirmation": "none",
                    "error": {"code": "steer-empty", "message": "steer requires non-empty text"}}
        if self.agent.exited.is_set() or self.agent.proc is None:
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "outcome": "process_exited", "mutation_status": "unknown",
                    "mutation_performed": False,
                    "steer_confirmation": "none",
                    "error": {"code": "agent-not-running",
                              "message": "agent process is not running"}}
        refusal = self._no_acp_session()
        if refusal is not None:
            return {**base, **refusal, "steer_outcome": "not_consumed",
                    "steer_consumed": False, "steer_confirmation": "none"}

        with self.lock:
            if not self.turn["active"]:
                # An idle steer is never written. Some agents answer an idle
                # steering call by starting a detached turn this holder would not
                # own (Codex 1.11.0 returns startedNewTurn), so the Agent gets an
                # honest not-consumed and decides whether to send a normal prompt.
                return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                        "steer_reason": "no-active-turn", "outcome": "no-active-turn",
                        "steer_confirmation": "none",
                        "mutation_status": self.turn.get("mutation_status"),
                        "mutation_performed": False}
            turn_request_id_before = self.turn["request_id"]
            turn_fingerprint = self.turn["fingerprint"]
            if params.get("delivery") == "after-turn":
                # The native ACP entry rejects or cancels concurrent prompts.
                # Wait on the existing completion condition, then use ordinary
                # prompt admission once. This is process-local pending input,
                # not native admission, a timer, or a restart/replay mechanism.
                original = self.turn
                session_id = self.acp_session_id
                queue_cursor = self.events.append({"kind": "steer_queued",
                    "confirmation": "holder-queued", "turn_request_id": turn_request_id_before,
                    "fingerprint": base["steer_fingerprint"]})
                def after_turn() -> None:
                    with self.turn_cond:
                        while original["active"] and not self.agent.exited.is_set():
                            self.turn_cond.wait()
                    original_result = {"request_id": original.get("request_id"),
                        "fingerprint": original.get("fingerprint"),
                        "outcome": original.get("outcome"),
                        "stop_reason": original.get("stop_reason"),
                        "final_text": original.get("final_text")}
                    if original.get("outcome") != "turn_completed":
                        sent = {"outcome": "prior_turn_not_completed",
                                "mutation_status": "not_started", "mutation_performed": False}
                    else:
                        # op_prompt refuses before writing if another prompt
                        # owns the slot or the holder is stopping. Preserve that
                        # receipt; never cancel that prompt or retry the write.
                        sent = self.op_prompt({"text": text, "wait": False,
                            "expected_holder_instance_id": self.holder_instance_id,
                            "expected_prior_turn_request_id": turn_request_id_before,
                            "expected_acp_session_id": session_id})
                    self.events.append({"kind": "steer_followup", "queue_cursor": queue_cursor,
                        "turn_request_id": turn_request_id_before,
                        "original_turn": original_result,
                        "fingerprint": base["steer_fingerprint"], "receipt": sent})
                threading.Thread(target=after_turn, daemon=True).start()
                return {**base, "steer_outcome": "queued", "steer_consumed": None,
                    "steer_confirmation": "holder-queued", "steer_queue_cursor": queue_cursor,
                    "steer_native_written": False, "turn_request_id": turn_request_id_before,
                    "turn_prompt_fingerprint": turn_fingerprint, "outcome": "steer_queued",
                    "mutation_status": original.get("mutation_status"), "mutation_performed": True,
                    "steer_reason": "pending input waits for prompt completion; read steer_followup "
                                    "for native write and session output for processing. A stopped "
                                    "holder loses pending input. No cancel or replay is sent"}
            request_params = {
                "sessionId": self.acp_session_id,
                "prompt": [{"type": "text", "text": text}],
                "_meta": {"steering": {"idleBehavior": "promptRequired"}},
            }
            if self.args.platform == "grok" and method == "_x.ai/interject":
                # Grok ignores idleBehavior and requires top-level text.
                request_params = {"sessionId": self.acp_session_id, "text": text}
            elif self.args.platform in ("opencode", "dsh"):
                request_params["_meta"]["steering"]["expectedTurnId"] = turn_request_id_before
            elif standard_prompt:
                # These installed ACP servers accept a second standard prompt
                # without transport cancellation. Do not invent an extension.
                request_params.pop("_meta")
            steer_request_id = self.agent.send_request(
                method,
                request_params,
            )
            if normalize_id(steer_request_id) not in self.agent.pending_out:
                return {**base, "steer_request_id": steer_request_id,
                        "steer_outcome": "not_consumed", "steer_consumed": False,
                        "steer_confirmation": "none", "outcome": "steer_write_failed",
                        "mutation_performed": False,
                        "error": {"code": "acp-write-failed", "message": "steer frame was not written"}}
            self.events.append({"kind": "steer_sent", "method": method,
                                "request_id": steer_request_id,
                                "turn_request_id": turn_request_id_before,
                                "fingerprint": base["steer_fingerprint"]})
        base["steer_request_id"] = steer_request_id
        base["turn_request_id"] = turn_request_id_before

        timeout = params.get("timeout")
        if timeout is None:
            timeout = STEER_TIMEOUT
        if standard_prompt:
            # Keep the pending reply after the caller's bounded wait. It must
            # not settle or replace the original prompt, including coalesced
            # replies or a reply that arrives after the original prompt ended.
            reply: dict[str, Any] = {}
            ready = threading.Event()

            def await_reply() -> None:
                response = self.agent.wait_response(steer_request_id, None)
                self.events.append({"kind": "steer_reply", "request_id": steer_request_id,
                                    "turn_request_id": turn_request_id_before,
                                    "fingerprint": base["steer_fingerprint"],
                                    "response": response})
                reply["response"] = response
                ready.set()

            threading.Thread(target=await_reply, daemon=True).start()
            ready.wait(timeout)
            response = reply.get("response")
        else:
            response = self.agent.wait_response(steer_request_id, timeout)

        if response is None:
            outcome, consumed, confirmation, error = "unknown", None, "none", {
                "code": "steer-no-response",
                "message": "no reply to the steering request before the timeout; "
                           "consumption is unknown — do not resend blindly"}
            if standard_prompt:
                outcome, confirmation = "written", "write-only"
                error = {"code": "steer-reply-pending",
                         "message": "the prompt frame was flushed; admission and processing are "
                                    "unconfirmed. Read capture events for its late steer_reply "
                                    "and session output. Do not resend blindly"}
        elif "error" in response:
            detail = response.get("error") or {}
            confirmation = "none"
            if detail.get("code") == -32601:
                outcome, consumed = "unsupported", False
                error = {"code": "steer-unsupported",
                         "message": f"agent does not implement {method}", "detail": detail}
            elif standard_prompt and detail.get("code") not in (-32600, -32602):
                outcome, consumed = "unknown", None
                error = {"code": "steer-prompt-failed", "detail": detail,
                         "message": "the additional prompt ended with an error; its effects "
                                    "are unconfirmed. Read session output and do not resend blindly"}
            else:
                outcome, consumed = "rejected", False
                error = {"code": "steer-rejected", "message": str(detail.get("message", "")),
                         "detail": detail}
        else:
            result = response.get("result") or {}
            if not isinstance(result, dict):
                result = {}
            if standard_prompt and isinstance(result.get("stopReason"), str):
                base["steer_stop_reason"] = result["stopReason"]
                result = {"outcome": "written", "confirmation": "prompt-completed",
                          "reason": "the additional prompt returned; read session output to judge processing"}
            if self.args.platform == "grok" and method == "_x.ai/interject":
                envelope = result.get("result") if isinstance(result, dict) else None
                if isinstance(envelope, dict) and envelope.get("status") == "queued" and not result.get("error"):
                    base["steer_native_status"] = "queued"
                    result = {"outcome": "written", "confirmation": "native-queued",
                              "reason": "Grok acknowledged the interject request; delivery and adoption are unconfirmed"}
            native = result.get("outcome")
            base["steer_native_outcome"] = native
            # What actually backs the claim. An agent that acknowledges
            # consumption reports `agent-confirmed`; a channel that can only
            # confirm the write says so, and the Runner must not upgrade it.
            confirmation = result.get("confirmation")
            base["steer_native_reason"] = result.get("reason")
            error = None
            if native == "injected":
                outcome, consumed = "injected", True
                confirmation = confirmation or "agent-confirmed"
            elif native == "written":
                # The text reached the running turn's input, but this platform
                # acknowledges nothing, so consumption stays undetermined.
                outcome, consumed = "written", None
                confirmation = confirmation or "write-only"
                error = {"code": "steer-write-only-confirmation",
                         "message": "the text was written into the running turn's input and "
                                    "the write was flushed without error, but this platform "
                                    "acknowledges no consumption - read the turn's own output "
                                    "to judge, and do not resend blindly"}
                if confirmation in ("native-queued", "native-admitted", "prompt-completed"):
                    error["message"] = ("the native entry answered the request; model processing "
                                        "and adoption need session output evidence. Processing may "
                                        "occur in a later step or turn. Do not resend blindly")
            elif native == "queued":
                # A later-turn queue is noninterrupting delivery. Admission
                # alone does not prove that the model processed its content.
                outcome, consumed = "written", None
                confirmation = confirmation or "agent-confirmed"
                error = {"code": "steer-queued",
                         "message": "the text was admitted to the session's follow-up "
                                    "queue; later processing is unconfirmed. Read session "
                                    "output and do not resend blindly"}
            elif native == "startedNewTurn":
                # Later-turn delivery is valid without cancellation. The
                # native reply confirms a separate turn, not model processing.
                outcome, consumed = "started_new_turn", None
                confirmation = confirmation or "agent-confirmed"
                base["steer_reason"] = ("the agent started a separate turn on this session; "
                    "this holder does not track that turn. Read session output for processing")
            elif native == "promptRequired":
                outcome, consumed = "not_consumed", False
                confirmation = confirmation or "none"
                error = {"code": "steer-prompt-required",
                         "message": "the turn had already settled or no turn was running; "
                                    "nothing was written - send a normal prompt instead"}
            elif native == "unknown":
                outcome, consumed = "unknown", None
                confirmation = confirmation or "none"
                error = {"code": "steer-undecided",
                         "message": "the write was issued but its fate is undecided; "
                                    "consumption is unknown - do not resend blindly"}
            else:
                outcome, consumed = "unknown", None
                confirmation = confirmation or "none"
                error = {"code": "steer-unrecognized-outcome",
                         "message": f"unrecognized steering outcome {native!r}"}

        with self.lock:
            turn_request_id_after = self.turn["request_id"]
            receipt = {
                **base,
                "steer_outcome": outcome,
                "steer_consumed": consumed,
                "steer_confirmation": confirmation,
                "steer_response": response,
                "turn_request_id_after": turn_request_id_after,
                "turn_request_id_preserved": (
                    turn_request_id_after in (turn_request_id_before, None)
                ),
                "turn_prompt_fingerprint": turn_fingerprint,
                "turn_active": self.turn["active"],
                "outcome": f"steer_{outcome}",
                "mutation_status": self.turn.get("mutation_status"),
                # This steer's own effect on the agent. `written` did reach the
                # running turn's input even though consumption is unconfirmed,
                # so it is not a clean "nothing happened".
                "mutation_performed": True if (
                    outcome in ("injected", "written", "started_new_turn")
                    # Issue #81: a queue admission is durable - the text will
                    # reach a later turn even though this turn never consumed it.
                    or base.get("steer_native_outcome") == "queued"
                ) else False if consumed is False else None,
            }
            if error:
                receipt["error"] = error
            self.events.append({"kind": "steer_result", "method": method,
                                "request_id": steer_request_id,
                                "steer_outcome": outcome,
                                "steer_consumed": consumed,
                                "turn_request_id_preserved": receipt["turn_request_id_preserved"]})
        return receipt

    def op_steer_interrupt(self, params: dict[str, Any]) -> dict[str, Any]:
        """Issue #65: the composite steering path, for an ACP session whose agent
        has no native mid-turn entry.

        This is **interrupted-then-continued**, never injection: cancel the
        running turn, confirm it really ended, then send the Agent's steering
        text once as the next turn on the same session, so the conversation
        keeps its context. It reuses the existing cancel and prompt operations -
        no scheduler, no second lifecycle, no retry loop.

        The Agent asks for this explicitly. It is never a fallback the Runner
        selects after a native attempt failed or timed out.

        Honesty rules this enforces:
        * the cancelled turn keeps its own request id and terminal state;
        * a turn that was already idle is not cancelled, and the receipt says so
          rather than pretending an interruption happened;
        * if the cancel is not confirmed, NOTHING is sent and the outcome is
          `unknown` - the Agent verifies before deciding;
        * the steering text is sent at most once, whatever the send returns;
        * the resend opens a new turn carrying the Agent's text verbatim.
          This composite path is NOT a Host recovery entry (Issue #94): it
          never infers a Host and never adds the native Skill entry line -
          a caller that wants the resend to open a Host round must include
          `/kaola-project-runner` as the text's own first line.
        """
        text = params.get("text") or ""
        base: dict[str, Any] = {
            "steer_mode": "interrupt",
            "steer_method": "cancel+prompt",
            "steer_text_chars": len(text),
            "steer_fingerprint": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        if not text.strip():
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "steer_confirmation": "none", "outcome": "steer_rejected",
                    "mutation_performed": False,
                    "error": {"code": "steer-empty", "message": "steer requires non-empty text"}}
        if self.agent.exited.is_set() or self.agent.proc is None:
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "steer_confirmation": "none", "outcome": "process_exited",
                    "mutation_status": "unknown", "mutation_performed": False,
                    "error": {"code": "agent-not-running",
                              "message": "agent process is not running"}}
        refusal = self._no_acp_session()
        if refusal is not None:
            # Without a session id there is no turn to interrupt and nowhere to
            # send the text: refusing here is what keeps `steer_consumed` honest.
            return {**base, **refusal, "steer_outcome": "not_consumed",
                    "steer_consumed": False, "steer_confirmation": "none",
                    "interrupted": None, "turn_was_active": False,
                    "side_effects_possible": False}

        with self.lock:
            # Hold the turn OBJECT, not just its id: `self.turn` is replaced when
            # a new prompt is admitted, so this is what keeps every later fact
            # bound to the turn the Agent targeted.
            target_turn = self.turn
            was_active = bool(target_turn["active"])
            cancelled_request_id = target_turn["request_id"] if was_active else None
            mutation_before = target_turn.get("mutation_status")
        base.update({
            "turn_was_active": was_active,
            "cancelled_turn_request_id": cancelled_request_id,
            "cancelled_turn_mutation_status_before": mutation_before,
        })

        if was_active:
            timeout = params.get("cancel_timeout")
            if timeout is None:
                timeout = params.get("timeout")
            # Bound to the exact turn object snapshotted above, and the facts
            # below come from the cancel's own locked snapshot of THAT turn -
            # never from `self.turn`, which by now may be somebody else's.
            cancel, cancel_sent, snapshot = self.cancel_turn(target_turn, timeout)
            base["cancel_receipt"] = {
                key: cancel.get(key) for key in
                ("outcome", "stop_reason", "mutation_status", "request_id",
                 "expected_request_id", "cancel_sent")
                if key in cancel
            }
            base["cancel_sent"] = cancel_sent
            still_active = bool(snapshot["active"])
            stop_reason = snapshot["stop_reason"]
            mutation_after = snapshot["mutation_status"]
            # A cancelled turn may already have written files, run commands, or
            # half-applied an edit, and a cancel that went out to a turn whose
            # end we could not confirm is no different. The Agent is told, not
            # reassured.
            side_effects = (mutation_after in ("in_progress", "unknown", "completed")
                            or mutation_before in ("in_progress", "unknown"))
            base.update({
                "cancelled_turn_stop_reason": stop_reason,
                "cancelled_turn_mutation_status": mutation_after,
                "side_effects_possible": side_effects,
            })
            if cancel.get("outcome") == "turn-changed":
                # The targeted turn was replaced before our cancel could go out.
                # Sending now would dispatch onto a turn nobody asked to steer.
                return {**base, "interrupted": None,
                        "steer_outcome": "unknown", "steer_consumed": None,
                        "steer_confirmation": "none", "outcome": "steer_turn_changed",
                        "mutation_status": mutation_after, "mutation_performed": None,
                        "current_turn_request_id": cancel.get("request_id"),
                        "error": {"code": "steer-turn-changed",
                                  "message": "the turn this steer targeted was replaced before it "
                                             "could be interrupted, so nothing was "
                                             + ("cancelled and " if not cancel_sent else "")
                                             + "the steering text was NOT sent; observe the "
                                               "session and decide again - do not resend blindly",
                                  "detail": cancel.get("error")}}
            if not snapshot["is_current"]:
                # Our turn did stop, but a different one already took the session.
                return {**base, "interrupted": True,
                        "steer_outcome": "unknown", "steer_consumed": None,
                        "steer_confirmation": "none", "outcome": "steer_turn_changed",
                        "mutation_status": mutation_after, "mutation_performed": None,
                        "error": {"code": "steer-turn-changed",
                                  "message": "the targeted turn stopped but another turn now owns "
                                             "the session, so the steering text was NOT sent; "
                                             "observe the session and decide again - do not "
                                             "resend blindly"}}
            if still_active or cancel.get("outcome") == "cancel-unconfirmed":
                # Nothing is sent onto a session whose previous turn may still be
                # running: that is how a duplicate dispatch happens.
                return {**base, "interrupted": None,
                        "steer_outcome": "unknown", "steer_consumed": None,
                        "steer_confirmation": "none", "outcome": "steer_cancel_unconfirmed",
                        "mutation_status": mutation_after, "mutation_performed": None,
                        "error": {"code": "steer-cancel-unconfirmed",
                                  "message": "the running turn did not confirm it stopped, so "
                                             "the steering text was NOT sent; verify the turn "
                                             "with observe before deciding - do not resend blindly"}}
            if not cancel_sent and cancel.get("outcome") == "no-active-turn":
                # Still our turn, but it finished on its own between the snapshot
                # and the cancel, so no cancel was ever sent. Claiming an
                # interruption here would be inventing one.
                base.update({
                    "interrupted": False,
                    "steer_confirmation": "no-turn-to-interrupt",
                    # Nothing was interrupted, so there is no partial work of
                    # ours to warn about; the turn's own end is reported above.
                    "side_effects_possible": False,
                })
            else:
                base["interrupted"] = True
                base["steer_confirmation"] = "cancel-confirmed"
        else:
            # The turn ended on its own between the Agent's decision and this
            # call. Nothing is interrupted; this is an ordinary next prompt.
            base.update({"interrupted": False, "side_effects_possible": False,
                         "steer_confirmation": "no-turn-to-interrupt",
                         "cancelled_turn_stop_reason": None,
                         "cancelled_turn_mutation_status": None})

        # Exactly one send, through the ordinary admission path, carrying the
        # Agent's text verbatim. This send opens a NEW turn; the composite
        # path is not a Host recovery entry (Issue #94) and adds no native
        # Skill entry line - the caller supplies it when wanted.
        prompt = self.op_prompt({"text": text, "wait": False})
        base["send_receipt"] = {
            key: prompt.get(key) for key in
            ("outcome", "mutation_status", "prompt_fingerprint",
             "dispatch_event_cursor", "event_cursor", "duplicate_warning")
            if key in prompt
        }
        send_error = prompt.get("error")
        if (send_error or {}).get("code") == "prompt-in-progress":
            # A different turn was admitted between the cancel and this send.
            # Nothing was written, and this steer is not that turn's.
            return {**base, "steer_outcome": "not_consumed", "steer_consumed": False,
                    "steer_confirmation": "none", "outcome": "steer_turn_changed",
                    "mutation_performed": False,
                    "current_turn_request_id": prompt.get("active_turn_request_id"),
                    "error": {"code": "steer-turn-changed",
                              "message": "a different turn started before the steering text could "
                                         "be sent, so nothing was sent; observe the session and "
                                         "decide again - do not resend blindly"}}
        if send_error or prompt.get("outcome") != "in_progress":
            failed_cleanly = prompt.get("mutation_status") == "not_started"
            return {**base,
                    "steer_outcome": "not_consumed" if failed_cleanly else "unknown",
                    "steer_consumed": False if failed_cleanly else None,
                    "outcome": "steer_send_failed",
                    "mutation_status": prompt.get("mutation_status"),
                    "mutation_performed": False if failed_cleanly else None,
                    "error": {"code": "steer-send-failed",
                              "message": "the turn was stopped but the steering text was not "
                                         "accepted as the next turn; it was sent once and is "
                                         "not resent here",
                              "detail": send_error or {"outcome": prompt.get("outcome")}}}

        # From the send's own atomic admission - not from `self.turn`, which by
        # now may already describe somebody else's turn.
        new_request_id = prompt.get("turn_request_id")
        receipt = {
            **base,
            "steer_outcome": "interrupted_and_resent" if base["interrupted"]
            else "resent_without_interrupt",
            # The text is running as its own turn. It was not injected into the
            # previous one, and this flag must not be read as injection.
            "steer_consumed": True,
            "new_turn_request_id": new_request_id,
            "new_prompt_fingerprint": prompt.get("prompt_fingerprint"),
            "dispatch_event_cursor": prompt.get("dispatch_event_cursor"),
            "turn_request_id_preserved": cancelled_request_id != new_request_id,
            "outcome": "steer_interrupted_and_resent" if base["interrupted"]
            else "steer_resent_without_interrupt",
            "mutation_status": prompt.get("mutation_status"),
            "mutation_performed": True,
        }
        self.events.append({"kind": "steer_interrupt",
                            "interrupted": base["interrupted"],
                            "cancelled_turn_request_id": cancelled_request_id,
                            "new_turn_request_id": new_request_id,
                            "fingerprint": base["steer_fingerprint"]})
        return receipt

    def cancel_turn(self, target: dict[str, Any] | None, timeout: float | None,
                    ) -> tuple[dict[str, Any], bool, dict[str, Any]]:
        """Cancel one exact turn and describe THAT turn.

        `target` is the turn object itself. `self.turn` is replaced - never reset
        in place - when a new prompt is admitted, so holding the object keeps the
        admission check, the outbound `session/cancel`, the wait and the receipt
        all bound to the same turn even though connections are served on separate
        threads and a worker event starts turns of its own (Issue #65).

        Returns `(receipt, cancel_sent, snapshot)`. The snapshot is taken under
        the lock from the target turn and is what a caller must report; nothing
        downstream may re-read `self.turn`, because by then it can already be
        somebody else's.
        """
        if target is None:
            target = self.turn
        with self.lock:
            if self.turn is not target:
                return ({"outcome": "turn-changed",
                         "request_id": self.turn.get("request_id"),
                         "expected_request_id": target.get("request_id"),
                         "turn_active": bool(self.turn["active"]),
                         "cancel_sent": False, "mutation_performed": False,
                         "error": {"code": "cancel-turn-changed",
                                   "message": "the turn this cancel was bound to is no longer the "
                                              "running turn, so nothing was cancelled"}},
                        False, self._turn_snapshot_locked(target))
            if not target["active"]:
                return ({"outcome": "no-active-turn",
                         "mutation_status": target.get("mutation_status"),
                         "cancel_sent": False},
                        False, self._turn_snapshot_locked(target))
            for key in list(self.pending_permissions):
                self._settle_pending_permission_locked(key, "cancelled")
            target["cancel_requested"] = True
            self.agent.send_message(
                {"jsonrpc": "2.0", "method": "session/cancel",
                 "params": {"sessionId": self.acp_session_id}}
            )
        if timeout is None:
            timeout = CANCEL_GRACE
        deadline = time.monotonic() + timeout
        with self.turn_cond:
            # Waiting on the captured object, so a newcomer can neither end this
            # wait early nor have its own end mistaken for this turn's.
            while target["active"]:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return ({**self.turn_receipt(turn=target),
                             "outcome": "cancel-unconfirmed", "cancel_sent": True},
                            True, self._turn_snapshot_locked(target))
                self.turn_cond.wait(timeout=remaining)
            # Built here, still holding the lock, from the target turn itself.
            return ({**self.turn_receipt(turn=target), "cancel_sent": True},
                    True, self._turn_snapshot_locked(target))

    def _turn_snapshot_locked(self, turn: dict[str, Any]) -> dict[str, Any]:
        """The facts a caller may report about one turn. Caller holds the lock."""
        return {
            "request_id": turn.get("request_id"),
            "active": bool(turn.get("active")),
            "stop_reason": turn.get("stop_reason"),
            "outcome": turn.get("outcome"),
            "mutation_status": turn.get("mutation_status"),
            "is_current": self.turn is turn,
        }

    def op_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        """Cancel the running turn.

        `expected_request_id` binds the operation to one turn: when the running
        turn is not that turn, nothing is sent and the outcome is `turn-changed`.
        """
        expected = params.get("expected_holder_instance_id")
        wanted = params.get("expected_request_id")
        with self.lock:
            if expected is not None and expected != self.holder_instance_id:
                return self._holder_instance_mismatch("cancel", expected)
            target = self.turn
            if wanted is not None and (not target["active"]
                                       or normalize_id(target.get("request_id"))
                                       != normalize_id(wanted)):
                return {"outcome": "turn-changed", "request_id": target.get("request_id"),
                        "expected_request_id": wanted,
                        "turn_active": bool(target["active"]),
                        "mutation_status": target.get("mutation_status"),
                        "mutation_performed": False, "cancel_sent": False,
                        "error": {"code": "cancel-turn-changed",
                                  "message": "the turn this cancel was bound to is no longer the "
                                             "running turn, so nothing was cancelled"}}
        receipt, _sent, _snapshot = self.cancel_turn(target, params.get("timeout"))
        return receipt

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
                "options": permission_options_view(entry),
            })
        truncated = bool(
            thinking_truncated or tools_truncated or timeline_truncated or cursor_gap
            or proj["turns_dropped"] or proj["answered_dropped"]
        )
        payload = {
            "schema": VIEW_SCHEMA,
            "platform": self.args.platform,
            "session": self.args.session,
            "session_role": self.session_role,
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
            "answered_permissions": proj["answered_permissions"],
            "mode": proj["mode"],
            "commands": proj["commands"],
            "usage": proj["usage"],
            "turn": {
                "mutation_status": self.turn.get("mutation_status") or "not_started",
                "outcome": self.turn.get("outcome"),
                "stop_reason": self.turn.get("stop_reason"),
                "active": bool(self.turn.get("active")),
                "started_at": self.turn.get("written_at"),
                "ended_at": self.turn.get("ended_at"),
            },
            "turns": proj["turns"],
            "unparsed_update_count": self.agent.unknown_updates,
        }
        models = self._quota_models()
        if models is not None:
            payload["models"] = models
        payload["model"] = self._view_model()
        self._fit_view(payload)
        return payload

    def _view_model(self) -> dict[str, Any]:
        """Launch facts stay historical. ``current`` is the live name, id, and effort.

        ``model_display`` is the start record. Do not pair it with ``current_effort``.
        ``current`` reads ``session_meta.configOptions`` only. A catalog name labels
        the live native id (``catalog-declared``) and does not prove a request was
        applied. A missing option or ``currentValue`` stays null. Inherited launch
        metadata is not a current observation. Devin's advertised model option stays
        the live id; the launch argv on ``effective_selection`` is not substituted.
        """
        evidence = self.start_evidence if isinstance(self.start_evidence, dict) else {}
        display = evidence.get("model_display")
        if not isinstance(display, dict):
            display = None
        selection = evidence.get("model_selection")
        selection = selection if isinstance(selection, dict) else {}
        application = evidence.get("config_application")
        application = application if isinstance(application, dict) else {}
        effective = evidence.get("effective_selection")
        effective = effective if isinstance(effective, dict) else {}
        current_effort = self._option_current(effective.get("effort_config_id"))
        return {
            "model_display": display,
            "requested_effort": evidence.get("requested_effort"),
            "resolved_effort": selection.get("resolved_effort"),
            "applied_effort": application.get("effort"),
            "current_effort": current_effort,
            "current": self._current_model(current_effort),
        }

    def _option_current(self, option_id: Any) -> str | None:
        """Live ``currentValue`` for one config option, or null when unreadable."""
        if not isinstance(option_id, str) or not option_id:
            return None
        meta = self.session_meta if isinstance(self.session_meta, dict) else {}
        options = meta.get("configOptions")
        if not isinstance(options, list):
            return None
        for option in options:
            if not isinstance(option, dict) or option.get("id") != option_id:
                continue
            value = option.get("currentValue")
            if isinstance(value, str) and value:
                return value
            return None
        return None

    def _current_model(self, effort: str | None) -> dict[str, Any]:
        """Name, native id, and effort from the live model and effort options."""
        native_id = None
        name = None
        module = quota_module()
        manifest = None
        if module is not None:
            try:
                manifest = module.read_manifest(
                    self.args.platform, Path(__file__).resolve().parent)
            except module.QuotaError:
                manifest = None
        if isinstance(manifest, dict) and module is not None:
            native_id = self._option_current(manifest.get("acp_model_config_id") or "")
            if native_id:
                name = module.declared_display_name(manifest, native_id)
        return {
            "name": name,
            "native_id": native_id,
            "effort": effort,
            "name_provenance": "catalog-declared" if name else None,
        }

    def _quota_models(self) -> dict[str, Any] | None:
        """Stamped model rows for the view payload. ``session_meta`` is not modified."""
        module = quota_module()
        if module is None:
            return None
        try:
            catalog = module.load_catalog(self.args.platform, Path(__file__).resolve().parent)
        except module.QuotaError:
            return {"availableModels": [], "options": []}
        return module.view_models(self.session_meta, catalog)

    @staticmethod
    def _fit_view(payload: dict[str, Any]) -> None:
        """Whole-view cap: drop oldest tools, messages, answers, then turns, until it fits."""
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        if size <= VIEW_BYTES:
            return
        payload["truncated"] = True
        for key in ("tools", "messages", "answered_permissions", "turns"):
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
        # Issue #73: check the bound instance before anything is requested,
        # cancelled, or written, so a refused stop leaves this holder and its
        # agent exactly as they were.
        expected = params.get("expected_holder_instance_id")
        if expected is not None and expected != self.holder_instance_id:
            with self.lock:
                return self._holder_instance_mismatch("stop", expected)
        # Issue #162: drain-restart asks for an idle stop. The check and the
        # claim share self.lock with op_prompt, so a prompt cannot start a turn
        # in the gap and then be cancelled by this stop.
        if params.get("require_idle"):
            with self.lock:
                pending = len(self.pending_permissions)
                busy = bool(
                    self.turn["active"] or pending or self.state not in ("ready", "agent_exited"))
                if busy:
                    return {"stopped": False, "idle": False, "state": self.state,
                            "turn_active": bool(self.turn["active"]),
                            "pending_permissions": pending}
                self.stop_requested = True
        else:
            self.stop_requested = True
        force = bool(params.get("force"))
        self.preserve_dispatched = bool(params.get("preserve_dispatched_workers"))
        self.state = "stopping"
        self.write_record()
        self._cancel_pending_permissions()
        self._reclaim_node()
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
        # Issue #299: inline spawn — this op exits right after its reply, so the
        # detached child must already hold its payload before we answer.
        self._delegator_wake("stopped", inline=True)
        result = {"stopped": True, "residual_pids": residual,
                  "swept_child_pgids": self.swept_child_pgids,
                  **({"spared_child_pgids": self.spared_child_pgids}
                     if getattr(self, "spared_child_pgids", None) else {}),
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
        if self.session_role in SIDEAGENT_ROLES or getattr(self, "preserve_dispatched", False):
            # Issue #255: a Sideagent's dispatched workers, and a Host's under
            # an explicit preserve intent, are their own Runner sessions with
            # their own exact stop; replacing the dispatcher must not end them
            # (holder, native agent, or its tools). Only other leftovers are
            # swept.
            spared = dispatched_worker_groups(self.record_dir / CHILD_RECORD_NAME, live,
                                              holder_instance_id=self.holder_instance_id)
            self.spared_child_pgids = sorted(spared)
            live = {pgid: members for pgid, members in live.items() if pgid not in spared}
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
                # Grouped options nest their real choices one level down, so
                # the selected value is found through the same flattening the
                # probe uses -- otherwise a grouped platform silently loses
                # value_name/value_description from its receipt.
                for choice in config_option_choices(option):
                    if choice.get("value") == params["value"]:
                        if choice.get("name") is not None:
                            evidence["value_name"] = choice["name"]
                        if choice.get("description") is not None:
                            evidence["value_description"] = choice["description"]
                break
        return evidence

    def op_record_start_evidence(self, params: dict[str, Any]) -> dict[str, Any]:
        """Keep the start receipt's selection/application evidence (Issue #203).

        Stored as given and written with the record, so later whole-record
        rewrites keep it. Bounded; nothing is sent to the agent.
        """
        evidence = params.get("evidence")
        if not isinstance(evidence, dict):
            return {"error": {"code": "invalid-start-evidence"}}
        size = len(json.dumps(evidence, sort_keys=True).encode("utf-8"))
        if size > START_EVIDENCE_BYTES:
            return {"error": {"code": "start-evidence-too-large", "bytes": size,
                              "limit": START_EVIDENCE_BYTES}}
        # Issue #245: start completes a resume-preserved role only after the
        # native session id is known. Absent key leaves the spawn value.
        updated_role = None
        if "session_role" in params:
            try:
                updated_role = normalize_session_role(params.get("session_role"))
            except ValueError:
                return {"error": {"code": "invalid-session-role"}}
        self.start_evidence = evidence
        if "session_role" in params:
            self.session_role = updated_role
            if isinstance(self.start_selection, dict):
                self.start_selection["session_role"] = updated_role
        self.write_record()
        return {"recorded": True}

    def op_rebind_heartbeat_host(self, params: dict[str, Any]) -> dict[str, Any]:
        """Issue #255: move this seat's carrier to a replacement Host in place.

        The CLI already proved the new target is the live Host holder of the
        same repo. The agent, its native session, and this holder instance
        stay; only where events go changes, and held wakes follow on the next
        watchdog tick. A seat started with no carrier stays without one.
        """
        expected = params.get("expected_holder_instance_id")
        if expected is not None and expected != self.holder_instance_id:
            with self.lock:
                return self._holder_instance_mismatch("rebind_heartbeat_host", expected)
        target = params.get("target")
        if (not isinstance(target, dict)
                or not all(isinstance(target.get(key), str) and target[key]
                           for key in ("platform", "session", "repo", "socket"))
                or not os.path.isabs(target["socket"])):
            return {"error": {"code": "invalid-heartbeat-host"}}
        previous = self.heartbeat_host
        if previous is None:
            return {"error": {"code": "no-heartbeat-host",
                              "message": "this seat was started with no Host carrier"}}
        if target["repo"] != previous["repo"]:
            return {"error": {"code": "heartbeat-host-foreign-repo",
                              "message": f"{target['repo']} is not {previous['repo']}"}}
        new = {key: target[key] for key in ("platform", "session", "repo", "socket")}
        with self.heartbeat_notify_lock:
            self.heartbeat_host = new
        self.events.append({"kind": "heartbeat_host_rebound",
                            "previous": {key: previous[key]
                                         for key in ("platform", "session", "repo")},
                            "target": {key: new[key] for key in ("platform", "session", "repo")},
                            "host_holder_instance_id": params.get("host_holder_instance_id")})
        self.write_record()
        return {"rebound": True, "previous_heartbeat_host": previous,
                "heartbeat_host": new, "holder_instance_id": self.holder_instance_id}

    # -- socket server ------------------------------------------------------------

    def handle_request(self, message: dict[str, Any]) -> dict[str, Any]:
        op = message.get("op")
        params = message.get("params") or {}
        if op == "state":
            return self.op_state()
        if op == "compact_notice":
            return self.op_compact_notice(params)
        if op == "prompt":
            return self.op_prompt(params)
        if op == "steer":
            return self.op_steer(params)
        if op == "steer_interrupt":
            return self.op_steer_interrupt(params)
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
        if op == "record_start_evidence":
            return self.op_record_start_evidence(params)
        if op == "rebind_heartbeat_host":
            return self.op_rebind_heartbeat_host(params)
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
                    try:
                        connection.sendall(canonical(response) + b"\n")
                    finally:
                        if exit_after:
                            # A stop whose caller already gave up still ends
                            # this holder; otherwise it lingers with a stopped
                            # record and keeps owning the session.
                            try:
                                connection.close()
                            except OSError:
                                pass
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
            # Issue #92: the holder's one existing tick also re-offers any
            # permission wake the bound Host has not taken yet. No new thread,
            # no new loop, no deadline - just this watchdog noticing that what
            # the Host is owed is still owed.
            try:
                self._flush_undelivered_wakes()
            except Exception:
                # The watchdog outlives any single retry; a broken flush must
                # not take the idle-exit timer down with it.
                pass
            if self.session_role == "host":
                try:
                    # Issue #255: the same tick offers new maintenance inputs
                    # to a node; it never re-delivers to the Host.
                    with self.worker_events_lock:
                        if self.node.get("registration_cursor") and not self.node.get("registration_active"):
                            self._register_compact_maintenance(self.node["registration_cursor"])
                        self._relay_pass()
                except Exception:
                    pass
            if self.agent.exited.is_set() and not self.turn["active"]:
                if time.monotonic() - self.last_activity > IDLE_EXIT_SECONDS:
                    self.state = "stopped"
                    self.write_record()
                    os._exit(0)

    def start_failure_facts(self, error: dict[str, Any]) -> dict[str, Any]:
        """Issue #120: a failed start carries the agent's own stderr tail and the
        holder's Seatbelt confinement. A nested dsh dies at boot with EPERM
        rewriting ``$DSH_HOME/profiles/acp/cordis.yml`` under a dsh Host's
        sandbox, and without these the receipt said only ``agent-exited``."""
        error = dict(error)
        pump = self.agent.stderr_pump
        if pump:
            # Issue #174: read the stderr ring only after the exit the
            # receipt reports has been observed. A frame write that broke
            # on a dying agent's closing stdin lands before waitpid is
            # observed and before the pump thread is ever scheduled, so the
            # tail could be read empty under load. A failed request write is
            # the exit-in-progress fact, so first wait for the observation
            # under the grace an agent gets to exit after its stdin closes,
            # then drain the last lines under the same grace (an agent child
            # can inherit stderr and hold EOF open past the exit).
            if self.agent.stdin_write_failed and not self.agent.exited.is_set():
                self.agent.exited.wait(EXIT_GRACE)
            if self.agent.exited.is_set():
                pump.thread.join(EXIT_GRACE)  # drain an exited agent's last lines
            tail = pump.tail()
            if tail:
                error["stderr_tail"] = tail
        error["seatbelt_confined"] = seatbelt_confined()
        return error

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
            self.fatal_error = self.start_failure_facts(result["error"])
            self.state = "error"
            self.write_record()
            self._delegator_wake("error")
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
        frame = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        written = False
        try:
            proc.stdin.write(canonical(frame) + b"\n")
            proc.stdin.flush()
            written = True
        except OSError:
            pass
        if method == "initialize":
            result["initialize_request"] = {"request": frame, "written": written}
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
    if args.platform == "codex":
        capabilities["session"] = {"compaction": {}}
    result["client_capabilities"] = capabilities
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
            response = wait(send("session/new", {"cwd": args.repo, "mcpServers": []}),
                            args.session_new_timeout)
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
                            "values": config_option_values(option),
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
    parser.add_argument("--session-new-timeout", type=float, default=SESSION_NEW_TIMEOUT)
    parser.add_argument("--host-entry", default=None)
    parser.add_argument("--host-name", default=None)
    parser.add_argument("--cli-version", default="")
    parser.add_argument("--accepted-revision", default="")
    parser.add_argument("--start-selection", default="")
    parser.add_argument("--session-role", default="")
    parser.add_argument("--baseline-exempt", default="")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    try:
        args.session_role = normalize_session_role(args.session_role)
    except ValueError:
        print("invalid --session-role", file=sys.stderr)
        return 2
    if args.probe:
        return run_probe(args)
    try:
        holder = Holder(args)
    except acp_paths.RecordRootUnsafe as exc:
        print(json.dumps({"result": "refused", "reason": "record-root-unsafe",
                          "error": {"code": "record-root-unsafe", "message": str(exc)},
                          "mutation_performed": False, "mutation_status": "not_started"}))
        return 1
    return holder.run()


if __name__ == "__main__":
    raise SystemExit(main())
