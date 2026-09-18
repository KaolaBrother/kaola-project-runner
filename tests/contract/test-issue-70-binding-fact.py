#!/usr/bin/env python3
"""Issue #70: the notification binding a worker holder really adopted.

A ZCode Host wakes only through workers it is actually bound to, so a receipt
that echoes the caller's own input proves nothing. These checks pin the three
honest answers the ACP surfaces now give — a target, an explicit ``null`` for
an ordinary unbound worker, and ``heartbeat_host_known: false`` for a record
written before the field existed — and prove the answer tracks the running
holder rather than the environment of a later command.

Deterministic and offline: the real Runner CLI, real holder processes, and the
hermetic fake ZCode app-server, reusing the Issue #62 phase-2 sandbox.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "kaola_zcode_heartbeat_contract",
    ROOT / "tests" / "contract" / "test-zcode-heartbeat-contract.py",
)
hb = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(hb)

Sandbox = hb.Sandbox
check = hb.check
CHECKS = hb.CHECKS
HEARTBEAT_HOST_ENV = hb.HEARTBEAT_HOST_ENV


def target_for(sandbox: Sandbox, host: str) -> dict:
    return {"platform": "zcode", "session": host, "repo": str(sandbox.repo)}


def expected_fact(sandbox: Sandbox, host: str) -> dict:
    """The resolved target the CLI validates and the holder adopts."""
    import os

    return {"platform": "zcode", "session": host,
            "repo": os.path.realpath(str(sandbox.repo)),
            "socket": str(hb.holder_socket(sandbox.record_dir(host)))}


def stored_record(sandbox: Sandbox, session: str) -> dict:
    path = sandbox.record_dir(session) / "record.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_binding_fact_is_the_holder_not_the_caller_environment() -> None:
    """A live holder keeps the target it was started with. A second ``start``
    carrying a different environment is refused as ``session-exists`` and must
    answer with the binding that is really in force, not the one just asked
    for — and the event still reaches the original Host."""
    sandbox = Sandbox("issue70-fact")
    try:
        host = sandbox.session()
        other_host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        sandbox.start(other_host, "basic")
        sandbox.write_prompt_file("HEARTBEAT: Issue #70 binding fact.")

        start = sandbox.start(worker, "basic", heartbeat_host=target_for(sandbox, host))
        want = expected_fact(sandbox, host)
        check(start.get("heartbeat_host_known") is True and start.get("heartbeat_host") == want,
              f"an armed start reports the holder's own binding ({start.get('heartbeat_host')})")
        check(start.get("heartbeat_host_requested") == want,
              "the same start separately records what it requested "
              f"({start.get('heartbeat_host_requested')})")
        check(start.get("state") == "ready" and start.get("acp_session_id"),
              "the armed start receipt keeps its existing readiness fields")

        observed = sandbox.cli("observe", session=worker)
        check(observed.get("heartbeat_host_known") is True
              and observed.get("heartbeat_host") == want,
              f"observe reports the same binding ({observed.get('heartbeat_host')})")
        check(stored_record(sandbox, worker).get("heartbeat_host") == want,
              "the holder's own record carries the binding it adopted")

        # A second start with a different host in the environment binds nothing.
        rebind = sandbox.cli(
            "start", "--mode", "yolo", session=worker, scenario="basic",
            **{HEARTBEAT_HOST_ENV: json.dumps(target_for(sandbox, other_host))})
        check((rebind.get("error") or {}).get("code") == "session-exists",
              f"a second start on a live session is refused ({rebind.get('error')})")
        check(rebind.get("heartbeat_host_known") is True
              and rebind.get("heartbeat_host") == want,
              "the refused start still reports the binding in force "
              f"({rebind.get('heartbeat_host')})")
        check(rebind.get("heartbeat_host_requested") == expected_fact(sandbox, other_host),
              "the refused start shows the target it asked for, distinct from the fact "
              f"({rebind.get('heartbeat_host_requested')})")

        # A send under the changed environment does not rebind either.
        reply = sandbox.cli("send", "--text", "work under a changed environment",
                            session=worker,
                            **{HEARTBEAT_HOST_ENV: json.dumps(target_for(sandbox, other_host))})
        check(reply.get("error") is None and reply.get("outcome") == "turn_completed",
              f"the worker still works normally ({reply.get('outcome')})")
        after = sandbox.cli("observe", session=worker)
        check(after.get("heartbeat_host") == want,
              f"the binding after that send is unchanged ({after.get('heartbeat_host')})")

        # Behaviour, not just fields: the turn-end event went to the original Host.
        host_dir = sandbox.record_dir(host)
        other_dir = sandbox.record_dir(other_host)
        hb.wait_until(lambda: hb.events_of_kind(host_dir, "worker_event"), 10,
                      "the idle event reaches the Host the holder is bound to")
        check(not hb.events_of_kind(other_dir, "worker_event"),
              "the Host named only in the later environment receives nothing")
    finally:
        sandbox.cleanup()


def test_unbound_is_explicit_and_a_pre_issue_70_record_is_unknown() -> None:
    """An ordinary unbound worker says so; a record written before this field
    existed reads as unknown and is never reported as unbound."""
    sandbox = Sandbox("issue70-unknown")
    try:
        worker = sandbox.session()
        sandbox.start(worker, "basic")
        live = sandbox.cli("observe", session=worker)
        check(live.get("heartbeat_host_known") is True and live.get("heartbeat_host") is None,
              f"an unbound live worker reports a known, null binding ({live})"[:200])

        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "the unbound worker stops normally")

        # An older holder wrote no such key. Strip it to read that record back.
        path = sandbox.record_dir(worker) / "record.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        check("heartbeat_host" in record, "the record under test carried the field")
        record.pop("heartbeat_host")
        path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")

        stale = sandbox.cli("observe", session=worker)
        check(stale.get("heartbeat_host_known") is False,
              f"a pre-Issue #70 record reads as unknown ({stale.get('heartbeat_host_known')})")
        check("heartbeat_host" not in stale,
              "an unknown binding is never reported as an unbound one "
              f"({stale.get('heartbeat_host')})")
    finally:
        sandbox.cleanup()


def test_rebinding_runs_through_the_existing_exact_stop_and_start() -> None:
    """The documented recovery for a missed or wrong binding: exact stop, then
    start again bound. No new rebind operation, and the new Host is the one
    that gets woken."""
    sandbox = Sandbox("issue70-rebind")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        sandbox.write_prompt_file("HEARTBEAT: Issue #70 recovery.")

        unbound = sandbox.start(worker, "basic")
        check(unbound.get("heartbeat_host") is None,
              "the worker starts unbound, as a missed binding would leave it")

        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True and stop.get("residual_pids") == [],
              f"the exact stop is terminal and leaves no residue ({stop.get('residual_pids')})")

        rebound = sandbox.start(worker, "basic", heartbeat_host=target_for(sandbox, host))
        want = expected_fact(sandbox, host)
        check(rebound.get("heartbeat_host") == want and rebound.get("heartbeat_host_known") is True,
              f"the replacement holder reports the new binding ({rebound.get('heartbeat_host')})")

        reply = sandbox.cli("send", "--text", "first task after rebinding", session=worker)
        check(reply.get("outcome") == "turn_completed",
              f"the rebound worker runs a normal turn ({reply.get('outcome')})")
        host_dir = sandbox.record_dir(host)
        hb.wait_until(lambda: hb.events_of_kind(host_dir, "worker_event"), 10,
                      "the rebound worker's turn end wakes the Host")
    finally:
        sandbox.cleanup()


def test_recovery_hands_the_wake_duty_over_instead_of_only_recording_it() -> None:
    """A Host whose only worker is unbound cannot wake itself, so "write it in
    the heartbeat body and end the turn" is a stall, not a wait. The generated
    guidance must hand the duty to the outer Agent - and say *blocked* when
    there is no one to hand it to - and the startup reference must state that
    the outer Agent takes it back."""
    import re

    ref = (ROOT / "skills" / "kaola-project-runner" / "references"
           / "zcode-host-dispatch.md").read_text(encoding="utf-8")
    startup = (ROOT / "skills" / "kaola-project-runner" / "references"
               / "host-startup.md").read_text(encoding="utf-8")
    flat_ref = re.sub(r"\s+", " ", ref)
    flat_startup = re.sub(r"\s+", " ", startup)

    check("Recording it in your heartbeat body wakes nobody" in flat_ref,
          "the reference denies that a recorded duty is a wake-up")
    check("Tell the outer controlling Agent, in this reply, which session to read"
          in flat_ref,
          "the reference hands the read-back duty to the outer Agent in the reply")
    check("no other confirmed wake source you are **blocked**" in flat_ref,
          "the reference calls the no-wake-source case blocked")
    check("hand the duty to the outer Agent and report it, before ending the turn"
          in flat_ref,
          "an unverified binding is handed over, not merely recorded")
    check("Take back what the Host hands you" in flat_startup
          and "that duty is yours" in flat_startup,
          "startup tells the outer Agent it owns the handed-back duty")
    check("A Host that reports itself blocked for want of a wake source stays blocked"
          in flat_startup,
          "startup says a blocked Host stays blocked until the outer Agent acts")
    # and the old, insufficient instruction is gone
    check("record in your heartbeat body that you must come back and read it yourself"
          not in flat_ref,
          "the record-only recovery step no longer stands alone")


def main() -> int:
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report every failure, keep running
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(f"test-issue-70-binding-fact: {len(tests) - failures}/{len(tests)} tests, "
          f"{len(CHECKS)} checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
