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


def test_recovery_is_internal_bounded_and_only_exceptions_go_outward() -> None:
    """A Host whose only worker is unbound cannot wake itself, so "write it in
    the heartbeat body and end the turn" is a stall. The Runner recovers that
    itself, with operations it already has - one bounded ``wait`` to read the
    in-flight result, then exact stop/start to rebind - and only an unresolvable
    exception goes out to the Agent that delegated to it. No timer, no poll
    loop, no rebind operation, nothing cancelled."""
    import re

    ref = (ROOT / "skills" / "kaola-project-runner" / "references"
           / "zcode-host-dispatch.md").read_text(encoding="utf-8")
    startup = (ROOT / "skills" / "kaola-project-runner" / "references"
               / "host-startup.md").read_text(encoding="utf-8")
    flat_ref = re.sub(r"\s+", " ", ref)
    flat_startup = re.sub(r"\s+", " ", startup)

    # Issue #104: the binding is mechanical, so the reference keeps only the
    # transitional case (a worker started before automatic binding) and the
    # same recovery: bounded read, then exact stop/start at the idle point.
    check("A worker started before automatic binding shows `heartbeat_host: null`" in flat_ref,
          "the reference scopes a null binding to the pre-change worker")
    check("read its in-flight result with the bounded `wait --timeout <seconds>`" in flat_ref,
          "the reference reuses the existing bounded wait to read the in-flight result")
    check("the recovery exception, never the ordinary wait or a poll loop" in flat_ref,
          "the bounded read is scoped as an exception, not the event wait")
    check("then exact `stop` and `start` it at that idle point" in flat_ref,
          "rebinding stays the existing exact stop/start")
    check("A refused `start`, or a session that is gone, is the exception you report "
          "with the decision you need" in flat_ref,
          "only an unresolvable case is reported outward")
    check("binds the worker to you and refuses" in flat_ref,
          "the reference says the start binds by itself and refuses instead of starting unbound")
    check("Exceptions reach you; worker handling does not" in flat_startup
          and "Do not take that over session by session" in flat_startup,
          "startup keeps per-worker handling inside the Host")
    # the superseded outward hand-off must be gone
    check("Tell the outer controlling Agent, in this reply, which session to read"
          not in flat_ref,
          "the per-worker hand-off to the delegating Agent no longer stands")
    check("Take back what the Host hands you" not in flat_startup,
          "startup no longer tells the outer Agent to take over the worker")


def test_zcode_native_resume_id_comes_from_the_identity_event() -> None:
    """``--resume`` is only honest with a real native id, and for ZCode that id
    is not in ``session_meta``: the translator reports ``sess_…`` in the
    session's own ``native_session_identity`` update once it materialises. The
    value is taken from the raw event here and then actually used to resume, so
    this is the behaviour, not the wording."""
    import re

    sandbox = Sandbox("issue70-native-id")
    try:
        worker = sandbox.session()
        start = sandbox.start(worker, "basic")
        check(str(start.get("acp_session_id") or "").startswith("zcode-"),
              f"a new ZCode session holds the bridge id ({start.get('acp_session_id')})")
        sandbox.cli("send", "--text", "materialise the native session", session=worker)

        events = hb.read_events(sandbox.record_dir(worker))
        identities = [entry for entry in events
                      if (entry.get("update") or {}).get("sessionUpdate")
                      == "native_session_identity"]
        check(bool(identities), "the holder's event log carries the identity update")
        native = (identities[-1].get("update") or {}).get("nativeSessionId") or ""
        check(native.startswith("sess_"),
              f"the identity event names the native session id ({native})")

        observed = sandbox.cli("observe", session=worker)
        meta = json.dumps(observed.get("session_meta") or {})
        check(native not in meta,
              f"the native id is absent from session_meta, as documented ({meta[:120]})")
        check(observed.get("acp_session_id") != native,
              "the ACP session id is not the native id and cannot stand in for it")

        # capture is the operation the guidance names for reading that event.
        captured = sandbox.cli("capture", "--since", "0", session=worker)
        check(native in json.dumps(captured),
              "capture surfaces the identity event a Host must read")

        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "the session stops before the resume")
        resumed = sandbox.cli("start", "--mode", "yolo", "--resume", native,
                              session=worker, scenario="basic")
        check(resumed.get("error") is None and resumed.get("state") == "ready",
              f"the id taken from the event really resumes ({resumed.get('error')})")
        sandbox.cli("stop", session=worker)

        ref = (ROOT / "skills" / "kaola-project-runner" / "references"
               / "zcode-host-dispatch.md").read_text(encoding="utf-8")
        startup = (ROOT / "skills" / "kaola-project-runner" / "references"
                   / "host-startup.md").read_text(encoding="utf-8")
        flat_ref = re.sub(r"\s+", " ", ref)
        flat_startup = re.sub(r"\s+", " ", startup)
        # Issue #104 (design #99 §f.2): the sourcing rule is written once, in
        # host-startup; the dispatch reference no longer repeats it.
        check("ZCode reports its `sess_…` in that session's own `native_session_identity` event"
              in flat_startup and "no native id at all" in flat_startup,
              "the startup reference sources the native id from the identity event")
        check("rather than passing `acp_session_id` or `--continue`" in flat_startup,
              "the startup reference forbids substituting another id")
        check("only once the session has run a turn" in flat_startup
              and "No verified id means no `--resume`" in flat_startup,
              "startup carries the platform sourcing rule")
        check("`sess_…`" not in flat_ref or "native_session_identity" not in flat_ref,
              "the dispatch reference does not carry a second copy of the sourcing rule")
    finally:
        sandbox.cleanup()


def test_worker_examples_use_issue_scoped_names() -> None:
    """Issue #72's contract: an issue-backed worker session is named
    ``<platform>-<CODE>-i<ISSUE>-<purpose>``. This reference is copied
    literally by Hosts, so every worker example in it must obey the rule; the
    Host's own name stays project-level until Issue #74 settles it."""
    import re

    ref_path = (ROOT / "skills" / "kaola-project-runner" / "references"
                / "zcode-host-dispatch.md")
    ref = ref_path.read_text(encoding="utf-8")
    pattern = re.compile(r"^[a-z0-9-]+-[A-Z]{2,6}-i\d+-[a-z0-9-]+$")

    sessions = re.findall(r"--session (\S+)", ref)
    check(bool(sessions), "the reference shows worker commands with --session")
    bad = [name for name in sessions if not pattern.match(name)]
    check(not bad, f"every --session example is issue-scoped (offenders: {bad})")

    check("codex-kaola-feature-a" not in ref,
          "the pre-Issue #72 worker example name is gone")
    worker = sessions[0]
    check(f'"session":"{worker}"' in ref and f'"event_id":"codex/{worker}/idle/19"' in ref,
          f"the event example names the same issue-scoped worker ({worker})")
    check("`<platform>-<CODE>-i<ISSUE>-<purpose>`" in ref,
          "the reference states the rule, so the example reads as a pattern")
    # Deliberate, recorded exception: the Host example is project-level for now.
    check('"session":"zcode-kaola-host"' in ref and not pattern.match("zcode-kaola-host"),
          "the Host example stays project-level pending Issue #74")


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
