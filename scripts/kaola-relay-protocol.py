#!/usr/bin/env python3
"""Length-delimited local protocol shared by the pane relay and its client."""

from __future__ import annotations

import json
import struct
from typing import Any


PROTOCOL_VERSION = 1
MAX_HEADER = 65536
MAX_PAYLOAD = 8 * 1024 * 1024


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def recv_exact(sock, count: int) -> bytes:
    blocks = bytearray()
    while len(blocks) < count:
        block = sock.recv(count - len(blocks))
        if not block:
            raise EOFError("relay connection closed")
        blocks.extend(block)
    return bytes(blocks)


def send_frame(sock, header: dict[str, Any], payload: bytes = b"") -> None:
    encoded = canonical_bytes(header)
    if len(encoded) > MAX_HEADER or len(payload) > MAX_PAYLOAD:
        raise ValueError("relay frame exceeds protocol limit")
    sock.sendall(struct.pack(">I", len(encoded)) + encoded + struct.pack(">Q", len(payload)) + payload)


def recv_frame(sock) -> tuple[dict[str, Any], bytes]:
    header_size = struct.unpack(">I", recv_exact(sock, 4))[0]
    if header_size > MAX_HEADER:
        raise ValueError("relay header exceeds protocol limit")
    header = json.loads(recv_exact(sock, header_size).decode("utf-8"))
    if not isinstance(header, dict):
        raise ValueError("relay header is not an object")
    payload_size = struct.unpack(">Q", recv_exact(sock, 8))[0]
    if payload_size > MAX_PAYLOAD:
        raise ValueError("relay payload exceeds protocol limit")
    return header, recv_exact(sock, payload_size)
