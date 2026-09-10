#!/usr/bin/env python3
"""Attested same-UID client for the Kaola nested-PTY pane relay."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import secrets
import socket
import struct
import sys
from pathlib import Path
from typing import Any


def _load_protocol():
    path = Path(__file__).with_name("kaola-relay-protocol.py")
    spec = importlib.util.spec_from_file_location("kaola_relay_protocol_client", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("relay protocol unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROTOCOL = _load_protocol()


class RelayConnection:
    def __init__(self, sock: socket.socket, relay_epoch: str, child_fingerprint: str):
        self.sock = sock
        self.relay_epoch = relay_epoch
        self.child_fingerprint = child_fingerprint

    def close(self) -> None:
        self.sock.close()

    def shutdown(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        finally:
            self.sock.close()


def _peer_pid(sock: socket.socket) -> int | None:
    if hasattr(socket, "LOCAL_PEERPID"):
        try:
            return struct.unpack("i", sock.getsockopt(socket.SOL_LOCAL, socket.LOCAL_PEERPID, 4))[0]
        except OSError:
            return None
    if hasattr(socket, "SO_PEERCRED"):
        try:
            return struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[0]
        except OSError:
            return None
    return None


def send_request(client: RelayConnection, operation: str, payload: bytes = b"", **facts: Any) -> str:
    request_id = secrets.token_hex(16)
    header = {
        "protocol_version": PROTOCOL.PROTOCOL_VERSION,
        "request_id": request_id,
        "relay_epoch": client.relay_epoch,
        "operation": operation,
        "expected_child_fingerprint": client.child_fingerprint,
    }
    header.update({key: value for key, value in facts.items() if value is not None})
    PROTOCOL.send_frame(client.sock, header, payload)
    return request_id


def recv_reply(client: RelayConnection, request_id: str | None = None) -> dict[str, Any]:
    header, payload = PROTOCOL.recv_frame(client.sock)
    if request_id is not None and header.get("request_id") != request_id:
        raise ValueError("relay request/reply identity mismatch")
    if payload:
        raise ValueError("relay reply unexpectedly carried payload")
    return header


def _request(client: RelayConnection, operation: str, payload: bytes = b"", **facts: Any) -> dict[str, Any]:
    return recv_reply(client, send_request(client, operation, payload, **facts))


def connect_attested(
    socket_path: str,
    relay_epoch: str,
    expected_child_fingerprint: str,
    pane_pid: int | None = None,
) -> RelayConnection:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect(socket_path)
    peer = _peer_pid(sock)
    if pane_pid is not None and peer is not None and peer != int(pane_pid):
        sock.close()
        raise PermissionError("relay peer PID does not match pane leader")
    client = RelayConnection(sock, relay_epoch, expected_child_fingerprint)
    reply = hello(client)
    if reply.get("result") != "hello" or reply.get("pid") != (int(pane_pid) if pane_pid is not None else reply.get("pid")):
        client.close()
        raise PermissionError("relay hello attestation failed")
    return client


def hello(client: RelayConnection) -> dict[str, Any]:
    return _request(client, "hello")


def quiesce(client: RelayConnection) -> dict[str, Any]:
    return _request(client, "quiesce")


def renew(client: RelayConnection, lease_id: str | None = None) -> dict[str, Any]:
    return _request(client, "renew", lease_id=lease_id)


def state(client: RelayConnection, pane_revision: str | None = None) -> dict[str, Any]:
    return _request(client, "state", pane_revision=pane_revision)


def prepare_input(client: RelayConnection, payload: bytes = b"", lease_id: str | None = None, clear_editor: bool = False) -> dict[str, Any]:
    return _request(client, "prepare-input", payload, lease_id=lease_id, clear_editor=bool(clear_editor))


def submit(client: RelayConnection, lease_id: str | None = None, **facts: Any) -> dict[str, Any]:
    return _request(client, "submit", lease_id=lease_id, **facts)


def abort(client: RelayConnection, lease_id: str | None = None) -> dict[str, Any]:
    return _request(client, "abort", lease_id=lease_id)


def resume(client: RelayConnection, lease_id: str | None = None) -> dict[str, Any]:
    return _request(client, "resume", lease_id=lease_id)


def _serve(args: argparse.Namespace) -> int:
    client = connect_attested(args.socket, args.epoch, args.child_fingerprint, args.relay_pid)
    try:
        for line in sys.stdin:
            command = json.loads(line)
            operation = command.pop("operation")
            payload = bytes.fromhex(command.pop("payload_hex", ""))
            try:
                reply = _request(client, operation, payload, **command)
            except Exception as exc:  # the controller receives a structured refusal
                reply = {"result": "client-error", "detail": str(exc)}
            print(json.dumps(reply, ensure_ascii=False, sort_keys=True), flush=True)
    finally:
        client.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--epoch", required=True)
    parser.add_argument("--child-fingerprint", required=True)
    parser.add_argument("--relay-pid", required=True, type=int)
    args = parser.parse_args()
    return _serve(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, OSError, ValueError, PermissionError) as exc:
        print(f"kaola-relay-client: {exc}", file=sys.stderr)
        raise SystemExit(2)
