#!/usr/bin/env python3
"""Reproduce the outer re-review's race on the CURRENT tree.

The peer receives the offer, withholds its receipt, a REAL settlement removes the
request from pending_permissions, and only then does the peer answer with the
exact event_id. The pre-write still_owed check has already passed.
"""
import importlib.machinery, importlib.util, json, sys, threading
from pathlib import Path

checkout = Path(sys.argv[1]).resolve()
loader = importlib.machinery.SourceFileLoader(
    "i92", str(checkout / "tests/contract/test-issue-92-permission-wake-recovery.py"))
spec = importlib.util.spec_from_loader("i92", loader)
m = importlib.util.module_from_spec(spec); loader.exec_module(m)

hm = m.load_holder_module()
key = "zc-1"
params = m.carrier_params(key)
stub = m.CarrierOnlyHolder(hm, key)
import tempfile
sock = Path(tempfile.mkdtemp(prefix="kaola-i92-race-")) / "peer.sock"
stub.heartbeat_host = dict(stub.heartbeat_host, socket=str(sock))

offered = threading.Event()
release = threading.Event()
exact = ('{"event_id":"%s","staged":true,"pending":1}\n' % m.expected_event_id(params)).encode()

def responder(index, request):
    offered.set()          # the Host now HAS the event
    release.wait(10)       # ... settlement happens here ...
    return exact           # ... and only now does the receipt come home

def settle_when_offered():
    offered.wait(10)
    stub.pending_permissions.pop(key, None)   # a real permit
    release.set()

stub.retain(params, {"error": {"code": "host-unreachable"}})
t = threading.Thread(target=settle_when_offered, daemon=True); t.start()
with m.FakePeer(sock, responder) as peer:
    stub.flush()
    offers = peer.count()
t.join(5)

print(json.dumps({
    "peer_offers": offers,
    "pending_permissions": dict(stub.pending_permissions),
    "undelivered_wakes": {k: {"attempts": v["attempts"]} for k, v in stub.undelivered_wakes.items()},
    "recorded_kinds": [e["kind"] for e in stub.recorded],
    "records": stub.recorded,
}, indent=2, default=str))
