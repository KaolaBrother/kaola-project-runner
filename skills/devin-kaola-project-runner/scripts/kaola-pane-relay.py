#!/usr/bin/env python3
"""Same-UID, attested nested-PTY relay for guarded tmux control."""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
import secrets
import select
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import termios
import time
from pathlib import Path
from typing import Any


def _load_protocol():
    path = Path(__file__).with_name("kaola-relay-protocol.py")
    spec = importlib.util.spec_from_file_location("kaola_relay_protocol_server", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("relay protocol unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROTOCOL = _load_protocol()
LEASE_SECONDS = 2.0
MAX_TRANSACTION_SECONDS = 5.0
FENCE_NAME = "decrqm-nonce-v1"


class RelayState:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.epoch = secrets.token_hex(16)
        self.pid = os.getpid()
        self.start_fingerprint = process_fingerprint(self.pid)
        self.child_pid = 0
        self.child_pgid = 0
        self.child_fingerprint = ""
        self.child_master = -1
        self.listener: socket.socket | None = None
        self.socket_path = ""
        self.connections: set[socket.socket] = set()
        self.connection_lease: dict[socket.socket, str] = {}
        self.lease_owner: socket.socket | None = None
        self.lease_id: str | None = None
        self.lease_deadline = 0.0
        self.transaction_deadline = 0.0
        self.mode = "starting"
        self.input_offset = 0
        self.output_offset = 0
        self.output_hash = hashlib.sha256()
        self.resize_revision = 0
        self.last_size: bytes | None = None
        self.bracketed_paste = False
        self.outer_pending = bytearray()
        self.prepared = False
        self.barrier: dict[str, Any] | None = None
        self.old_tty: list[Any] | None = None
        self.shutdown_started = False
        self.tracked_descendants: dict[int, str] = {}

    def facts(self) -> dict[str, Any]:
        # Remember owned descendants without changing their runtime state so
        # exact stop can still clean up processes that created a new session.
        _track_descendants(self, _descendant_states(self.child_pid))
        child_process = process_command(self.child_pid)
        rows = _process_rows()
        child_state = rows.get(self.child_pid, (0, ""))[1]
        return {
            "managed": True,
            "protocol_version": PROTOCOL.PROTOCOL_VERSION,
            "epoch": self.epoch,
            "pid": self.pid,
            "start_fingerprint": self.start_fingerprint,
            "socket_path": self.socket_path,
            "socket_owner_uid": os.getuid(),
            "socket_mode": "0600",
            "peer_pid_verified": True,
            "state": self.mode,
            "child_pid": self.child_pid,
            "child_pgid": self.child_pgid,
            "child_start_fingerprint": self.child_fingerprint,
            "child_runtime_path": os.path.realpath(self.args.runtime_path),
            "child_process": child_process,
            "child_process_state": child_state,
            "child_process_match": runtime_command_matches(child_process, self.args.runtime_path)
            or bool(self.args.exact_process_title and child_process == self.args.exact_process_title),
            "process_group_running": child_tree_running(self),
            "lease_active": self.lease_owner is not None,
            "child_input_offset": self.input_offset,
            "child_output_offset": self.output_offset,
            "child_output_digest": "sha256:" + self.output_hash.hexdigest(),
            "resize_revision": self.resize_revision,
            "bracketed_paste": self.bracketed_paste,
            "terminal_fence": FENCE_NAME,
        }


ACTIVE: RelayState | None = None


def process_command(pid: int) -> str:
    if pid <= 0:
        return ""
    result = subprocess.run(["ps", "-ww", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def process_fingerprint(pid: int) -> str:
    command = process_command(pid)
    started = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True).stdout.strip()
    material = f"{pid}\0{started}\0{command}".encode()
    return "sha256:" + hashlib.sha256(material).hexdigest()


def runtime_command_matches(command: str, expected: str) -> bool:
    expected_real = os.path.realpath(expected)
    words = command.split()
    return expected in words[:2] or expected_real in words[:2]


def create_control_socket(state: RelayState | None = None) -> socket.socket:
    if state is None:
        raise ValueError("relay state is required")
    root = Path(tempfile.gettempdir()) / f"kpr-{os.getuid()}"
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    path = root / f"{state.epoch}.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    os.chmod(path, 0o600)
    listener.listen(8)
    listener.setblocking(False)
    state.socket_path = str(path)
    state.listener = listener
    return listener


def verify_peer(connection: socket.socket) -> bool:
    if sys.platform == "darwin":
        uid = ctypes.c_uint()
        gid = ctypes.c_uint()
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) == 0:
            return uid.value == os.getuid()
        return False
    if hasattr(socket, "LOCAL_PEERCRED"):
        try:
            raw = connection.getsockopt(socket.SOL_LOCAL, socket.LOCAL_PEERCRED, 12)
            return struct.unpack("iii", raw)[1] == os.getuid()
        except (OSError, struct.error):
            pass
    if hasattr(socket, "SO_PEERCRED"):
        try:
            _pid, uid, _gid = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            return uid == os.getuid()
        except (OSError, struct.error):
            pass
    info = os.stat(connection.fileno())
    return info.st_uid == os.getuid()


def spawn_child_pty(state: RelayState | None = None) -> tuple[int, int]:
    if state is None:
        raise ValueError("relay state is required")
    pid, master = os.forkpty()
    if pid == 0:
        try:
            os.chdir(state.args.repo)
            os.execv(state.args.runtime_path, [state.args.runtime_path, *state.args.runtime_args])
        finally:
            os._exit(127)
    os.set_blocking(master, False)
    state.child_pid = pid
    state.child_pgid = pid
    state.child_master = master
    # `forkpty()` returns before the child necessarily reaches exec().  A
    # fingerprint captured in that gap names the transient fork image and
    # invalidates every later relay attestation once the real CLI appears.
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        command = process_command(pid)
        if runtime_command_matches(command, state.args.runtime_path) or bool(
            state.args.exact_process_title and command == state.args.exact_process_title
        ):
            break
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.01)
    state.child_fingerprint = process_fingerprint(pid)
    return pid, master


def track_terminal_modes(state: RelayState, data: bytes) -> None:
    if b"\x1b[?2004h" in data:
        state.bracketed_paste = True
    if b"\x1b[?2004l" in data:
        state.bracketed_paste = False


def forward_child_output(state: RelayState, data: bytes | None = None) -> int:
    if data is None:
        try:
            data = os.read(state.child_master, 65536)
        except BlockingIOError:
            return 0
    if not data:
        return 0
    track_terminal_modes(state, data)
    state.output_offset += len(data)
    state.output_hash.update(data)
    os.write(sys.stdout.fileno(), data)
    return len(data)


def _write_child(state: RelayState, data: bytes) -> None:
    view = memoryview(data)
    while view:
        try:
            count = os.write(state.child_master, view)
            view = view[count:]
        except BlockingIOError:
            select.select([], [state.child_master], [], 0.1)
    state.input_offset += len(data)


def forward_outer_input(state: RelayState, data: bytes | None = None) -> int:
    if data is None:
        try:
            data = os.read(sys.stdin.fileno(), 65536)
        except BlockingIOError:
            return 0
    if not data:
        return 0
    _write_child(state, data)
    return len(data)


def set_pane_input(state: RelayState, enabled: bool) -> None:
    action = "-e" if enabled else "-d"
    result = subprocess.run([state.args.tmux_bin, "select-pane", action, "-t", state.args.pane_id], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("tmux pane input transition failed")
    expected = "0" if enabled else "1"
    for _ in range(10):
        observed = subprocess.run(
            [state.args.tmux_bin, "display-message", "-p", "-t", state.args.pane_id, "#{pane_input_off}"],
            capture_output=True,
            text=True,
        )
        if observed.returncode == 0 and observed.stdout.strip() == expected:
            return
        time.sleep(0.01)
    raise RuntimeError("tmux pane input transition was not observable")


def _process_rows() -> dict[int, tuple[int, str]]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,state="], capture_output=True, text=True
    )
    rows: dict[int, tuple[int, str]] = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
            rows[int(fields[0])] = (int(fields[1]), fields[2])
    return rows


def _descendant_states(root_pid: int) -> dict[int, str]:
    rows = _process_rows()
    children: dict[int, list[int]] = {}
    for pid, (ppid, _state) in rows.items():
        children.setdefault(ppid, []).append(pid)
    found: dict[int, str] = {}
    pending = [root_pid]
    seen = {root_pid}
    while pending:
        parent = pending.pop()
        for pid in children.get(parent, []):
            if pid in seen:
                continue
            seen.add(pid)
            pending.append(pid)
            process_state = rows[pid][1]
            if not process_state.upper().startswith("Z"):
                found[pid] = process_state
    return found


def _track_descendants(state: RelayState, descendants: dict[int, str]) -> None:
    for pid in descendants:
        if pid not in state.tracked_descendants:
            fingerprint = process_fingerprint(pid)
            if fingerprint:
                state.tracked_descendants[pid] = fingerprint


def _signal_tracked(state: RelayState, signum: int) -> None:
    for pid, fingerprint in list(state.tracked_descendants.items()):
        if process_fingerprint(pid) != fingerprint:
            state.tracked_descendants.pop(pid, None)
            continue
        try:
            os.kill(pid, signum)
        except ProcessLookupError:
            state.tracked_descendants.pop(pid, None)


def stop_child_tree(state: RelayState) -> None:
    os.killpg(state.child_pgid, signal.SIGSTOP)
    stable = 0
    previous: set[int] | None = None
    for _ in range(50):
        descendants = _descendant_states(state.child_pid)
        _track_descendants(state, descendants)
        _signal_tracked(state, signal.SIGSTOP)
        current = _descendant_states(state.child_pid)
        group_states = [value for value in _group_states(state.child_pgid) if not value.startswith("Z")]
        stopped = (
            bool(group_states)
            and all(value.startswith("T") for value in group_states)
            and all(value.startswith("T") for value in current.values())
        )
        current_ids = set(current)
        if stopped and current_ids == previous:
            stable += 1
            if stable >= 2:
                return
        else:
            stable = 0
        previous = current_ids
        time.sleep(0.01)
    raise RuntimeError("child-tree-stop-failed")


def stop_child_group(state: RelayState) -> None:
    """Compatibility surface; containment now includes escaped descendants."""
    stop_child_tree(state)


def resume_child_tree(state: RelayState) -> None:
    try:
        os.killpg(state.child_pgid, signal.SIGCONT)
    except ProcessLookupError:
        pass
    _signal_tracked(state, signal.SIGCONT)


def _group_states(pgid: int) -> list[str]:
    result = subprocess.run(["ps", "-axo", "pgid=,state="], capture_output=True, text=True)
    states = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0].isdigit() and int(fields[0]) == pgid:
            states.append(fields[1])
    return states


def child_tree_running(state: RelayState) -> bool:
    group_states = [value for value in _group_states(state.child_pgid) if not value.startswith("Z")]
    if not group_states or any(value.startswith("T") for value in group_states):
        return False
    rows = _process_rows()
    for pid, fingerprint in list(state.tracked_descendants.items()):
        if process_fingerprint(pid) != fingerprint:
            continue
        process_state = rows.get(pid, (0, ""))[1]
        if not process_state or process_state.startswith("T"):
            return False
    return True


def verify_group_stopped(state: RelayState) -> bool:
    for _ in range(20):
        states = [value for value in _group_states(state.child_pgid) if not value.startswith("Z")]
        if states and all(value.startswith("T") for value in states):
            return True
        time.sleep(0.01)
    return False


def drain_child_pty(state: RelayState) -> None:
    quiet_since = time.monotonic()
    while time.monotonic() - quiet_since < 0.03:
        ready, _, _ = select.select([state.child_master], [], [], 0.01)
        if not ready:
            continue
        try:
            data = os.read(state.child_master, 65536)
        except BlockingIOError:
            continue
        if not data:
            return
        forward_child_output(state, data)
        quiet_since = time.monotonic()


def run_decrqm_fence(state: RelayState, timeout: float = 1.0) -> None:
    """Accept one exact nonce reply; malformed, unexpected, or duplicate replies fail."""
    nonce = secrets.randbelow(800000) + 100000
    query = f"\x1b[{nonce}$p".encode("ascii")
    expected = f"\x1b[{nonce};0$y".encode("ascii")
    os.write(sys.stdout.fileno(), query)
    deadline = time.monotonic() + timeout
    received = bytearray()
    while time.monotonic() < deadline:
        ready, _, _ = select.select([sys.stdin.fileno()], [], [], 0.05)
        if not ready:
            continue
        block = os.read(sys.stdin.fileno(), 4096)
        if not block:
            raise RuntimeError("terminal fence outer PTY closed")
        received.extend(block)
        position = received.find(expected)
        if position >= 0:
            before = bytes(received[:position])
            after = bytes(received[position + len(expected):])
            if expected in after:
                raise RuntimeError("duplicate terminal fence reply")
            if before or after:
                # Pane input was disabled before the transaction. Any other
                # outer-PTY byte was not covered by the caller's snapshot and
                # must neither authorize this fence nor survive for replay.
                state.outer_pending.clear()
                raise RuntimeError("unexpected outer input during terminal fence")
            # The exact reply may be delivered alone while an unrelated byte
            # is already queued as the next outer-PTY read. Check that queue
            # before declaring the fence complete; otherwise the main loop
            # could replay the unaccounted byte after the transaction resumes.
            ready, _, _ = select.select([sys.stdin.fileno()], [], [], 0)
            if ready:
                extra = os.read(sys.stdin.fileno(), 4096)
                state.outer_pending.clear()
                if not extra:
                    raise RuntimeError("terminal fence outer PTY closed")
                raise RuntimeError("unexpected outer input during terminal fence")
            return
        if b"$y" in received and expected not in received:
            raise RuntimeError("malformed or unexpected terminal fence reply")
    raise TimeoutError("terminal fence reply timed out")


def discard_outer_input(state: RelayState) -> None:
    """Discard bytes accumulated while tmux pane input was disabled."""
    state.outer_pending.clear()
    while True:
        ready, _, _ = select.select([sys.stdin.fileno()], [], [], 0)
        if not ready:
            return
        try:
            block = os.read(sys.stdin.fileno(), 65536)
        except BlockingIOError:
            return
        if not block:
            return


def reject_queued_outer_input(state: RelayState) -> None:
    ready, _, _ = select.select([sys.stdin.fileno()], [], [], 0)
    if not ready:
        return
    try:
        block = os.read(sys.stdin.fileno(), 65536)
    except BlockingIOError:
        return
    state.outer_pending.clear()
    if not block:
        raise RuntimeError("outer PTY closed before submit")
    raise RuntimeError("unexpected outer input before submit")


def prepare_input(state: RelayState, payload: bytes, clear_editor: bool = False) -> None:
    if clear_editor:
        _write_child(state, b"\x15")
    if state.bracketed_paste:
        _write_child(state, b"\x1b[200~" + payload + b"\x1b[201~")
    else:
        _write_child(state, payload)
    resume_child_tree(state)
    time.sleep(0.2)
    stop_child_tree(state)
    if not verify_group_stopped(state):
        raise RuntimeError("child group did not stop after prepare")
    drain_child_pty(state)
    run_decrqm_fence(state)
    state.prepared = True
    state.mode = "prepared"


def submit_input(state: RelayState) -> None:
    if not state.prepared:
        raise RuntimeError("input was not prepared")
    reject_queued_outer_input(state)
    _write_child(state, b"\r")
    resume_child_tree(state)
    # Keep a byte that races the final pre-submit check from becoming child
    # input. Pane input is still disabled during this discard.
    discard_outer_input(state)
    set_pane_input(state, True)
    state.prepared = False
    state.mode = "running"
    state.lease_id = None
    state.lease_owner = None


def send_input_direct(
    state: RelayState, payload: bytes, clear_editor: bool = False
) -> None:
    """Transfer one controller-selected prompt without pausing the child."""
    if not payload:
        raise RuntimeError("input must not be empty")
    if state.lease_owner is not None:
        raise RuntimeError("relay-busy")
    if clear_editor:
        _write_child(state, b"\x15")
    if state.bracketed_paste:
        _write_child(state, b"\x1b[200~" + payload + b"\x1b[201~")
    else:
        _write_child(state, payload)
    _write_child(state, b"\r")


def send_control_direct(state: RelayState, payload: bytes) -> None:
    """Transfer one controller-selected native key without pausing the child."""
    if not payload:
        raise RuntimeError("control input must not be empty")
    if state.lease_owner is not None:
        raise RuntimeError("relay-busy")
    _write_child(state, payload)


def send_control_input(state: RelayState, payload: bytes) -> None:
    """Send one controller-selected native key sequence without adding Enter."""
    if not payload:
        raise RuntimeError("control input must not be empty")
    reject_queued_outer_input(state)
    _write_child(state, payload)
    resume_child_tree(state)
    # Keep pane input fenced until bytes that raced the controller transaction
    # have been discarded. The relay assigns no meaning to the selected key.
    discard_outer_input(state)
    set_pane_input(state, True)
    state.prepared = False
    state.mode = "running"
    state.lease_id = None
    state.lease_owner = None
    state.lease_deadline = 0.0
    state.transaction_deadline = 0.0


def restore_running(state: RelayState) -> None:
    # All bytes queued while pane input was disabled are outside the caller's
    # snapshot. A refusal/timeout must not replay them after restoration.
    discard_outer_input(state)
    resume_child_tree(state)
    set_pane_input(state, True)
    for _ in range(50):
        if child_tree_running(state):
            break
        time.sleep(0.01)
    else:
        raise RuntimeError("child-tree-resume-unproved")
    state.prepared = False
    state.mode = "running"
    state.lease_id = None
    state.lease_owner = None
    state.lease_deadline = 0.0
    state.transaction_deadline = 0.0


def unlink_control_socket(state: RelayState) -> None:
    if state.socket_path:
        try:
            os.unlink(state.socket_path)
        except FileNotFoundError:
            pass


def safe_shutdown(state: RelayState) -> None:
    if state.shutdown_started:
        return
    state.shutdown_started = True
    if state.child_pgid > 0:
        _signal_tracked(state, signal.SIGTERM)
        try:
            os.killpg(state.child_pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            os.killpg(state.child_pgid, signal.SIGCONT)
        except ProcessLookupError:
            pass
        _signal_tracked(state, signal.SIGCONT)
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            tracked_alive = any(
                process_fingerprint(pid) == fingerprint
                for pid, fingerprint in state.tracked_descendants.items()
            )
            try:
                os.killpg(state.child_pgid, 0)
            except ProcessLookupError:
                if not tracked_alive:
                    break
            time.sleep(0.02)
        else:
            _signal_tracked(state, signal.SIGKILL)
            try:
                os.killpg(state.child_pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if state.listener is not None:
        state.listener.close()
    unlink_control_socket(state)
    if state.old_tty is not None:
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, state.old_tty)
        except termios.error:
            pass


def _reply(relay_state: RelayState, request: dict[str, Any], result: str, **facts: Any) -> dict[str, Any]:
    response = {
        "protocol_version": PROTOCOL.PROTOCOL_VERSION,
        "request_id": request.get("request_id"),
        "relay_epoch": relay_state.epoch,
        "operation": request.get("operation"),
        "expected_child_fingerprint": relay_state.child_fingerprint,
        "result": result,
    }
    response.update(facts)
    return response


def _validate_request(state: RelayState, request: dict[str, Any]) -> None:
    if request.get("protocol_version") != PROTOCOL.PROTOCOL_VERSION:
        raise ValueError("protocol-version-mismatch")
    if request.get("relay_epoch") != state.epoch:
        raise ValueError("relay-epoch-mismatch")
    if request.get("expected_child_fingerprint") != state.child_fingerprint:
        raise ValueError("child-fingerprint-mismatch")
    if not isinstance(request.get("request_id"), str):
        raise ValueError("request-id-required")


def _require_lease(state: RelayState, connection: socket.socket, request: dict[str, Any]) -> None:
    if state.lease_owner is not connection or request.get("lease_id") != state.lease_id:
        raise PermissionError("lease-mismatch")


def _quiesce(state: RelayState, connection: socket.socket) -> None:
    if state.lease_owner is not None:
        raise RuntimeError("relay-busy")
    set_pane_input(state, False)
    try:
        stop_child_tree(state)
        if not verify_group_stopped(state):
            raise RuntimeError("child-group-stop-failed")
        drain_child_pty(state)
        run_decrqm_fence(state)
    except Exception:
        restore_running(state)
        raise
    state.lease_owner = connection
    state.lease_id = secrets.token_hex(16)
    now = time.monotonic()
    state.lease_deadline = now + LEASE_SECONDS
    state.transaction_deadline = now + MAX_TRANSACTION_SECONDS
    state.mode = "quiesced"


def _handle(state: RelayState, connection: socket.socket, request: dict[str, Any], payload: bytes) -> dict[str, Any]:
    # Reporting-only bootstrap binds the same-UID socket and relay epoch before
    # disclosing the opaque child fingerprint needed by every later request.
    if request.get("operation") == "bootstrap-hello":
        if request.get("protocol_version") != PROTOCOL.PROTOCOL_VERSION or request.get("relay_epoch") != state.epoch or payload:
            raise ValueError("bootstrap-attestation-failed")
        return _reply(state, request, "bootstrap-hello", **state.facts())
    _validate_request(state, request)
    operation = request["operation"]
    if operation == "hello":
        return _reply(state, request, "hello", **state.facts())
    if operation == "quiesce":
        _quiesce(state, connection)
        return _reply(state, request, "quiesced", lease_id=state.lease_id, **state.facts())
    if operation == "renew":
        _require_lease(state, connection, request)
        # A verified controller that is still making progress may renew the
        # current bounded phase. Silence and disconnect recovery remain tied
        # to LEASE_SECONDS; MAX_TRANSACTION_SECONDS bounds the work window
        # after each authenticated progress checkpoint rather than the total
        # wall time of several expensive observation phases.
        now = time.monotonic()
        state.lease_deadline = now + LEASE_SECONDS
        state.transaction_deadline = now + MAX_TRANSACTION_SECONDS
        return _reply(state, request, "renewed", lease_id=state.lease_id)
    if operation == "state":
        if request.get("pane_revision") and request.get("frame_revision") and state.barrier:
            if state.output_offset == state.barrier["submitted_output_offset"]:
                state.barrier["state"] = "pending"
            elif request["frame_revision"] == state.barrier["prepared_frame_revision"]:
                state.barrier["state"] = "output-seen"
            else:
                state.barrier["state"] = "satisfied"
        public_barrier = None if state.barrier is None else {
            key: state.barrier[key]
            for key in ("receipt_id", "submitted_output_offset", "prepared_pane_revision", "state")
        }
        return _reply(
            state,
            request,
            "state",
            relay=state.facts(),
            barrier=public_barrier,
            direct_input=True,
        )
    if operation == "send-input":
        submitted_offset = state.output_offset
        payload_fingerprint = "sha256:" + hashlib.sha256(payload).hexdigest()
        clear_editor = bool(request.get("clear_editor"))
        send_input_direct(state, payload, clear_editor)
        return _reply(
            state,
            request,
            "input-sent",
            submitted_output_offset=submitted_offset,
            payload_fingerprint=payload_fingerprint,
            clear_editor=clear_editor,
        )
    if operation == "containment":
        _require_lease(state, connection, request)
        tracked = [
            {"pid": pid, "start_fingerprint": fingerprint}
            for pid, fingerprint in sorted(state.tracked_descendants.items())
            if process_fingerprint(pid) == fingerprint
        ]
        return _reply(state, request, "containment", tracked_descendants=tracked)
    if operation == "prepare-input":
        _require_lease(state, connection, request)
        prepare_input(state, payload, bool(request.get("clear_editor")))
        # Preparing input is a separately verified transaction phase.  Give
        # the controller a fresh bounded window to recapture the pane and
        # prove the editor bytes before submit; a dead/disconnected controller
        # still recovers through the short lease and the phase keeps a hard
        # upper bound.
        now = time.monotonic()
        state.lease_deadline = now + LEASE_SECONDS
        state.transaction_deadline = now + MAX_TRANSACTION_SECONDS
        return _reply(
            state,
            request,
            "prepared",
            lease_id=state.lease_id,
            relay=state.facts(),
            prepared_payload_fingerprint="sha256:" + hashlib.sha256(payload).hexdigest(),
            prepared_clear_editor=bool(request.get("clear_editor")),
        )
    if operation == "submit":
        _require_lease(state, connection, request)
        if request.get("receipt_id"):
            state.barrier = {
                "receipt_id": request["receipt_id"],
                "prepared_pane_revision": request["prepared_pane_revision"],
                "prepared_frame_revision": request["prepared_frame_revision"],
                "submitted_output_offset": state.output_offset,
                "state": "pending",
            }
        elif state.barrier and state.barrier.get("state") == "satisfied":
            state.barrier = None
        submitted_offset = state.output_offset
        submit_input(state)
        return _reply(state, request, "submitted", submitted_output_offset=submitted_offset, relay=state.facts())
    if operation == "send-control":
        submitted_offset = state.output_offset
        payload_fingerprint = "sha256:" + hashlib.sha256(payload).hexdigest()
        if state.lease_owner is None:
            send_control_direct(state, payload)
        else:
            _require_lease(state, connection, request)
            send_control_input(state, payload)
        return _reply(
            state,
            request,
            "control-sent",
            submitted_output_offset=submitted_offset,
            payload_fingerprint=payload_fingerprint,
            relay=state.facts(),
        )
    if operation in {"abort", "resume"}:
        _require_lease(state, connection, request)
        restore_running(state)
        return _reply(
            state,
            request,
            "resumed",
            relay=state.facts(),
            restoration_evidence={
                "child_resumed": True,
                "pane_input_restored": True,
                "relay_responsive": True,
                "process_group_running": True,
                "lease_released": True,
            },
        )
    if operation == "terminate":
        _require_lease(state, connection, request)
        set_pane_input(state, True)
        state.prepared = False
        state.lease_id = None
        state.lease_owner = None
        state.lease_deadline = 0.0
        state.transaction_deadline = 0.0
        state.mode = "terminating"
        # Stop accepting new controllers and remove the exact epoch endpoint
        # before the child can exit. Existing authorized connection bytes
        # remain valid on POSIX after unlink, while crash races cannot strand
        # a reachable or stale socket path.
        unlink_control_socket(state)
        _signal_tracked(state, signal.SIGTERM)
        try:
            os.killpg(state.child_pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            os.killpg(state.child_pgid, signal.SIGCONT)
        except ProcessLookupError:
            # Exiting between TERM and CONT is already the requested terminal
            # state, not an uncertain transport result.
            pass
        _signal_tracked(state, signal.SIGCONT)
        return _reply(state, request, "terminating")
    raise ValueError("unsupported-operation")


def _sync_size(state: RelayState) -> None:
    try:
        size = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
    except OSError:
        return
    if size == state.last_size:
        return
    fcntl.ioctl(state.child_master, termios.TIOCSWINSZ, size)
    state.last_size = size
    state.resize_revision += 1
    try:
        os.killpg(state.child_pgid, signal.SIGWINCH)
    except ProcessLookupError:
        pass


def _publish(state: RelayState) -> None:
    for key, value in (("KAOLA_PROJECT_RUNNER_RELAY_SOCKET", state.socket_path), ("KAOLA_PROJECT_RUNNER_RELAY_EPOCH", state.epoch)):
        result = subprocess.run([state.args.tmux_bin, "set-environment", "-t", f"={state.args.session}", key, value], capture_output=True)
        if result.returncode != 0:
            raise RuntimeError("could not publish relay endpoint")


def run(args: argparse.Namespace | None = None) -> int:
    global ACTIVE
    if args is None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--tmux-bin", required=True)
        parser.add_argument("--session", required=True)
        parser.add_argument("--pane-id", required=True)
        parser.add_argument("--repo", required=True)
        parser.add_argument("--runtime-path", required=True)
        parser.add_argument("--exact-process-title", default="")
        parser.add_argument("runtime_args", nargs=argparse.REMAINDER)
        args = parser.parse_args()
        if args.runtime_args[:1] == ["--"]:
            args.runtime_args = args.runtime_args[1:]
    state = RelayState(args)
    ACTIVE = state
    def _signal_exit(signum: int, _frame: Any) -> None:
        raise SystemExit(128 + signum)

    for caught_signal in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(caught_signal, _signal_exit)
    state.old_tty = termios.tcgetattr(sys.stdin.fileno())
    tty_attrs = list(state.old_tty)
    tty_attrs[3] &= ~(termios.ICANON | termios.ECHO)
    tty_attrs[6][termios.VMIN] = 1
    tty_attrs[6][termios.VTIME] = 0
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, tty_attrs)
    os.set_blocking(sys.stdin.fileno(), False)
    create_control_socket(state)
    run_decrqm_fence(state)
    spawn_child_pty(state)
    _sync_size(state)
    state.mode = "running"
    _publish(state)
    selector = selectors.DefaultSelector()
    selector.register(state.listener, selectors.EVENT_READ, "listener")
    selector.register(sys.stdin.fileno(), selectors.EVENT_READ, "outer")
    selector.register(state.child_master, selectors.EVENT_READ, "child")
    try:
        while True:
            _sync_size(state)
            now = time.monotonic()
            if state.lease_owner is not None and (now > state.lease_deadline or now > state.transaction_deadline):
                restore_running(state)
            try:
                waited, status = os.waitpid(state.child_pid, os.WNOHANG)
            except ChildProcessError:
                return 0
            if waited == state.child_pid:
                return os.waitstatus_to_exitcode(status)
            for key, _events in selector.select(0.05):
                if key.data == "listener":
                    connection, _ = state.listener.accept()
                    if not verify_peer(connection):
                        connection.close()
                        continue
                    connection.settimeout(5.0)
                    state.connections.add(connection)
                    selector.register(connection, selectors.EVENT_READ, "connection")
                elif key.data == "outer":
                    if state.mode == "running":
                        if state.outer_pending:
                            pending = bytes(state.outer_pending)
                            state.outer_pending.clear()
                            forward_outer_input(state, pending)
                        forward_outer_input(state)
                elif key.data == "child":
                    try:
                        if forward_child_output(state) == 0:
                            return 0
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            return 0
                        raise
                else:
                    connection = key.fileobj
                    try:
                        request, payload = PROTOCOL.recv_frame(connection)
                        try:
                            reply = _handle(state, connection, request, payload)
                        except Exception as exc:
                            if state.lease_owner is connection:
                                restore_running(state)
                            reply = _reply(state, request, str(exc))
                        PROTOCOL.send_frame(connection, reply)
                    except (EOFError, BrokenPipeError, ConnectionResetError, socket.timeout, ValueError):
                        selector.unregister(connection)
                        state.connections.discard(connection)
                        connection.close()
                        if state.lease_owner is connection:
                            restore_running(state)
    finally:
        safe_shutdown(state)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        if ACTIVE is not None:
            safe_shutdown(ACTIVE)
        print(f"kaola-pane-relay: {exc}", file=sys.stderr)
        raise SystemExit(2)
