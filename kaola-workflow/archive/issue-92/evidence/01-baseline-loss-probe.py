#!/usr/bin/env python3
"""Issue #92 baseline: show the wake is LOST, not merely un-retained.

Arms the exact measured state (bound worker pending on approval, ZCode Host
force-stopped), restarts the SAME authorized Host, then waits far past any
single carrier attempt and reports what the Host actually received.

Usage: python3 01-baseline-loss-probe.py /path/to/checkout
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

checkout = Path(sys.argv[1]).resolve()
mod_path = checkout / "tests" / "contract" / "test-issue-92-permission-wake-recovery.py"
spec = importlib.util.spec_from_file_location("i92", mod_path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

sandbox = m.Sandbox("baseline-loss")
try:
    host = sandbox.session()
    worker = sandbox.session()
    pending = m.arm_pending_wake_with_absent_host(sandbox, host, worker)
    worker_dir = sandbox.record_dir(worker)
    host_dir = sandbox.record_dir(host)
    print(json.dumps({"armed_request": pending}, sort_keys=True))
    print(json.dumps({"worker_carrier_receipts": [
        {"event_kind": e.get("event_kind"), "receipt": e.get("receipt")}
        for e in m.carrier_entries(worker_dir)]}, sort_keys=True))

    sandbox.start(host, "basic")
    print(f"host restarted: {host}")
    time.sleep(90)

    print(json.dumps({
        "worker_turn_active": sandbox.cli("status", session=worker).get("turn_active"),
        "worker_pending_permissions": sandbox.cli(
            "status", session=worker).get("pending_permissions"),
        "host_staged_worker_events": m.worker_event_entries(host_dir),
        "host_delivered": m.events_of_kind(host_dir, "worker_event_delivered"),
        "host_prompts": m.rpc_sends(sandbox.rpcs[host]),
        "worker_carrier_sends_total": len(m.carrier_entries(worker_dir)),
    }, sort_keys=True, indent=2))
finally:
    sandbox.cleanup()
