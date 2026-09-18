#!/usr/bin/env python3
"""Replay one worker_event op on a ZCode Host holder socket.

Sends the byte-shape the worker holder's own carrier sends
(`_notify_heartbeat_host_now`): {"op": "worker_event", "request_id": hex,
"params": {schema, kind, platform, session, repo, reason, event_cursor}}.
Identical params reproduce the same event_id = platform/session/kind/cursor,
which is exactly what an at-least-once carrier re-send looks like to the host.
Prints the raw request and the holder's raw one-line receipt.
"""
import json
import secrets
import socket
import sys

sock_path, params_json = sys.argv[1], sys.argv[2]
params = json.loads(params_json)
params.setdefault("schema", "kaola-worker-event/1")
request = {"op": "worker_event", "request_id": secrets.token_hex(8),
           "params": params}
payload = json.dumps(request).encode("utf-8") + b"\n"
print("SEND:", payload.decode().strip())
connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    connection.settimeout(10.0)
    connection.connect(sock_path)
    connection.sendall(payload)
    buffer = bytearray()
    while b"\n" not in buffer:
        data = connection.recv(65536)
        if not data:
            break
        buffer.extend(data)
    print("RECV:", buffer.partition(b"\n")[0].decode("utf-8", "replace").strip())
finally:
    connection.close()
