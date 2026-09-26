#!/usr/bin/env python3
"""Issue #186: a fresh Claude Code seat must publish its resumable native id.

A fresh seat's ACP id is minted per bridge process and dies with it, so a
``--resume`` that carries the recorded ``acp_session_id`` can only ever fail
(``resourceNotFound`` -> ``resume-failed``). The fix is a credential-free
``native_session_identity`` session update, in the shape ZCode already uses,
every time the bridge binds or changes the native Claude id.

These checks run offline against the vendored bridge and the real Runner CLI:
no network, no account, no real ``claude`` (``CLAUDE_BIN`` points at
``fake-claude.py``), a sandbox HOME, and a temporary ``KAOLA_ACP_RECORD_ROOT``
so no real seat record is read or written.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / "contract" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


bridge_mod = _load("kaola_issue50_bridge", "test-issue-50-claude-acp-bridge.py")
runner_mod = _load("kaola_issue50_runner", "test-issue-50-runner-integration.py")

Sandbox = bridge_mod.Sandbox
Bridge = bridge_mod.Bridge
check = bridge_mod.check
CHECKS = bridge_mod.CHECKS
ids_of = bridge_mod.ids_of
argv_value = bridge_mod.argv_value
wait_until = bridge_mod.wait_until
PYTHON = runner_mod.PYTHON
CHECKOUT_CLI = runner_mod.CHECKOUT_CLI


def identity_updates(bridge: Bridge) -> list[dict]:
    return ids_of(bridge, "native_session_identity")


def holder_events(sandbox, session: str) -> list[dict]:
    logs = list((sandbox.record_root / "claude-code" / session).glob("*/events.jsonl"))
    check(len(logs) == 1, f"{session}: exactly one holder event log ({len(logs)})")
    return [json.loads(line) for line in logs[0].read_text().splitlines() if line.strip()]


def raw_cli(sandbox, command: str, *args: str, session: str) -> dict:
    """Run a Runner command without asserting exit status (a refusal is data here).

    A `start` that refuses can still leave a holder behind, so it is registered
    for cleanup exactly like ``Sandbox.cli`` does; otherwise a failing case
    leaks a holder+node pair the removed record dir can no longer be stopped
    from (B2)."""
    argv = [PYTHON, str(CHECKOUT_CLI), "claude-code", command,
            "--repo", str(sandbox.repo), "--session", session, *args]
    if command == "start":
        sandbox.sessions.append((CHECKOUT_CLI, session))
    result = subprocess.run(argv, capture_output=True, text=True, env=sandbox.env(), timeout=60)
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise AssertionError(
            f"{command} printed no JSON receipt: {result.stdout[-400:]} {result.stderr[-400:]}"
        ) from exc


# ------------------------------------------------------------------- bridge level


def test_fresh_seat_publishes_its_native_id_exactly_once() -> None:
    """A fresh `session/new` plus one turn is where a client can first learn the
    resumable id, and a turn that keeps the same id must not repeat it."""
    sandbox = Sandbox("i186-fresh")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        sid = bridge.new_session()["sessionId"]
        bridge.prompt(sid, "first turn")
        native = sandbox.records()[0]["session_id"]
        wait_until(lambda: len(identity_updates(bridge)) == 1, 5.0, "first-turn identity update")
        identities = identity_updates(bridge)
        update = identities[0]
        check(update.get("acpSessionId") == sid and update.get("nativeSessionId") == native,
              f"the update names the ACP session and the id the CLI announced ({update})")
        check(len(sid) == 32 and sid != native,
              f"the ACP id is the process-local bridge id, never the native one ({sid} vs {native})")
        bridge.prompt(sid, "second turn")
        check(len(identity_updates(bridge)) == 1,
              "a resumed turn that keeps the same native id emits no duplicate update")
        bridge.stop()
        check(native not in bridge.stderr(), "the raw native id still never reaches a bridge log line")
    finally:
        sandbox.cleanup()


def test_resume_failure_fallback_announces_the_new_id() -> None:
    """The silent fresh fallback changes the native id mid-seat; the client must
    see the replacement, since the id it held just expired."""
    sandbox = Sandbox("i186-fallback")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        sid = bridge.new_session()["sessionId"]
        bridge.prompt(sid, "first turn")
        first = sandbox.records()[0]["session_id"]
        wait_until(lambda: len(identity_updates(bridge)) == 1, 5.0, "first identity update")
        result = bridge.prompt(sid, "[failresume] resume breaks")
        check(result["stopReason"] == "end_turn", "the failed resume turn is answered by a fresh conversation")
        check("Resume failed" in bridge.stderr(), "the bridge took the documented fresh-start fallback")
        records = sandbox.records()
        check(len(records) == 3 and "--resume" in records[1]["argv"] and "--resume" not in records[2]["argv"],
              "the fallback ran a fresh conversation after the failed --resume turn")
        second = records[2]["session_id"]
        check(second != first, "the fallback conversation has its own native id")
        wait_until(lambda: len(identity_updates(bridge)) == 2, 5.0, "second identity update")
        identities = identity_updates(bridge)
        check(identities[1].get("nativeSessionId") == second and identities[1].get("acpSessionId") == sid,
              f"the fallback emits a second identity with the new id ({identities[1]})")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_cancelled_fallback_turn_announces_the_new_id() -> None:
    """When the schema drift intervenes: the resume fails, the fallback starts a
    new conversation, and THAT turn is cancelled. The client must be told the
    fallback's id V, never the U its resume had already failed to reach (N1)."""
    sandbox = Sandbox("i186-fallback-cancel")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        sid = bridge.new_session()["sessionId"]
        bridge.prompt(sid, "first turn")
        first = sandbox.records()[0]["session_id"]
        wait_until(lambda: len(identity_updates(bridge)) == 1, 5.0, "first identity update")
        request_id = bridge.request_async("session/prompt", {
            "sessionId": sid,
            "prompt": [{"type": "text", "text": "[resumefailhang] fallback then hang"}],
        })
        # records[1] is the failing --resume turn, records[2] the fresh fallback.
        wait_until(lambda: len(sandbox.records()) >= 3
                   and sandbox.records()[2].get("grandchild_pid"), 15.0, "fallback turn running")
        fallback = sandbox.records()[2]
        check("--resume" not in fallback["argv"] and sandbox.records()[1]["argv"].count("--resume") == 1,
              "a fresh fallback conversation runs after the failed --resume turn")
        new_native = fallback["session_id"]
        check(new_native != first, "the fallback conversation has its own native id V")
        bridge.notify("session/cancel", {"sessionId": sid})
        response = bridge.wait(request_id, 15.0)
        check(response["result"]["stopReason"] == "cancelled", "the fallback turn reports cancelled")
        wait_until(lambda: len(identity_updates(bridge)) == 2, 5.0, "fallback identity update")
        latest = identity_updates(bridge)[1]
        check(latest.get("nativeSessionId") == new_native and latest.get("nativeSessionId") != first,
              f"the cancelled fallback announces V, not the failed U ({latest})")
        check(latest.get("acpSessionId") == sid, "the fallback identity still names its ACP session")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_cancelled_first_turn_publishes_the_announced_id() -> None:
    """A cancelled first turn is often the seat's only turn; the id the CLI
    announced must still reach the client."""
    sandbox = Sandbox("i186-cancel")
    try:
        bridge = Bridge(sandbox)
        bridge.initialize()
        sid = bridge.new_session()["sessionId"]
        request_id = bridge.request_async("session/prompt", {
            "sessionId": sid,
            "prompt": [{"type": "text", "text": "[hang] cancelled first turn"}],
        })
        wait_until(lambda: bool(sandbox.records()) and "grandchild_pid" in sandbox.records()[0],
                   10.0, "hanging claude recorded")
        bridge.notify("session/cancel", {"sessionId": sid})
        response = bridge.wait(request_id, 15.0)
        check(response["result"]["stopReason"] == "cancelled", "the first turn reports cancelled")
        native = sandbox.records()[0]["session_id"]
        wait_until(lambda: len(identity_updates(bridge)) == 1, 5.0, "cancelled-turn identity update")
        update = identity_updates(bridge)[0]
        check(update.get("nativeSessionId") == native and update.get("acpSessionId") == sid,
              f"a cancelled first turn still publishes the announced id ({update})")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_cancelled_resume_bound_first_turn_announces_the_id() -> None:
    """A resume-bound seat whose only turn is cancelled takes neither the
    continue success path nor the fallback; the cancel path must still publish
    its one {acpSessionId: U, nativeSessionId: U}."""
    sandbox = Sandbox("i186-resume-cancel")
    try:
        native = "1c9d2b44-6a7e-4f10-9c83-2d5e0a7b3f61"
        bridge = Bridge(sandbox)
        bridge.initialize()
        bridge.result("session/resume", {
            "sessionId": native, "cwd": str(sandbox.repo), "mcpServers": [],
        })
        request_id = bridge.request_async("session/prompt", {
            "sessionId": native,
            "prompt": [{"type": "text", "text": "[hang] cancelled resume first turn"}],
        })
        wait_until(lambda: bool(sandbox.records()) and "grandchild_pid" in sandbox.records()[0],
                   10.0, "hanging resume claude recorded")
        check(argv_value(sandbox.records()[0]["argv"], "--resume") == native,
              "the cancelled turn ran as a --resume of the bound id")
        bridge.notify("session/cancel", {"sessionId": native})
        response = bridge.wait(request_id, 15.0)
        check(response["result"]["stopReason"] == "cancelled", "the resume-bound turn reports cancelled")
        wait_until(lambda: len(identity_updates(bridge)) == 1, 5.0, "cancelled resume identity update")
        update = identity_updates(bridge)[0]
        check(update.get("acpSessionId") == native and update.get("nativeSessionId") == native,
              f"a cancelled resume-bound first turn publishes exactly one {native} identity ({update})")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_resume_bound_seat_announces_its_native_id_on_the_first_turn() -> None:
    """`session/resume` binds a native id before any turn, so the continue path
    is that seat's only chance to publish one (B1): it must emit exactly one
    {acpSessionId: U, nativeSessionId: U} and stay silent on later turns."""
    sandbox = Sandbox("i186-resumed")
    try:
        native = "5f2c4a1e-9d3b-4c7a-8e21-0b6d7f9a1c33"
        bridge = Bridge(sandbox)
        bridge.initialize()
        resumed = bridge.result("session/resume", {
            "sessionId": native, "cwd": str(sandbox.repo), "mcpServers": [],
        })
        check(resumed["sessionId"] == native, "session/resume binds the native id")
        check(not identity_updates(bridge),
              "binding alone emits no identity: the id must come with the first turn")
        bridge.prompt(native, "resume-bound first turn")
        check(sandbox.records()[0]["session_id"] == native, "the turn ran as a --resume of the bound id")
        check(argv_value(sandbox.records()[0]["argv"], "--resume") == native,
              "the fake CLI recorded --resume <native>")
        wait_until(lambda: len(identity_updates(bridge)) == 1, 5.0, "resume-bound identity update")
        update = identity_updates(bridge)[0]
        check(update.get("acpSessionId") == native and update.get("nativeSessionId") == native,
              f"a resume-bound first turn emits exactly one identity naming the native id ({update})")
        bridge.prompt(native, "resume-bound second turn")
        check(argv_value(sandbox.records()[1]["argv"], "--resume") == native, "the second turn resumes the same id")
        check(len(identity_updates(bridge)) == 1,
              "a further turn on the same native id emits no duplicate (dedupe branch)")
        bridge.stop()
    finally:
        sandbox.cleanup()


def test_holder_capture_exposes_the_id_and_resume_uses_it() -> None:
    """The holder records the update in the seat's own ``events.jsonl``, so
    `capture` carries it; the native id then resumes after a stop, while the
    recorded ``acp_session_id`` still cannot."""
    sandbox = runner_mod.Sandbox("i186-holder")
    try:
        session = sandbox.session()
        receipt = sandbox.cli(CHECKOUT_CLI, "start", session=session)
        check(receipt.get("error") is None and receipt["state"] == "ready",
              f"the fresh seat reaches ready ({receipt.get('error')})")
        acp_id = receipt["acp_session_id"]
        send = sandbox.cli(CHECKOUT_CLI, "send", "--text", "hello", session=session)
        check(send.get("final_text") == "echo:hello", f"a turn completes ({send.get('final_text')})")
        native = sandbox.records()[0]["session_id"]
        identities = [entry for entry in holder_events(sandbox, session)
                      if (entry.get("update") or {}).get("sessionUpdate") == "native_session_identity"]
        check(len(identities) == 1, f"the seat's events.jsonl carries exactly one identity update ({len(identities)})")
        update = identities[0]["update"]
        check(update.get("nativeSessionId") == native and update.get("acpSessionId") == acp_id,
              f"the recorded update pairs the ACP id with the native one ({update})")
        capture = sandbox.cli(CHECKOUT_CLI, "capture", "--since", "0", session=session)
        check(native in json.dumps(capture), "capture surfaces the identity update a Host must read")
        stop = sandbox.cli(CHECKOUT_CLI, "stop", session=session)
        check(stop.get("stopped") is True and stop.get("residual_pids") == [],
              "the seat stops cleanly before the resume")

        resumed_session = sandbox.session()
        resumed = sandbox.cli(CHECKOUT_CLI, "start", "--resume", native, session=resumed_session)
        check(resumed.get("error") is None and resumed.get("state") == "ready",
              f"start --resume takes the id capture exposed ({resumed.get('error')})")
        check(resumed.get("acp_session_id") == native,
              f"a resume-bound seat's acp_session_id is the native id ({resumed.get('acp_session_id')})")

        # B1: the resume-bound seat must publish its id on its first turn, or a
        # Host would have to discard history to drain-restart it.
        records_before = len(sandbox.records())
        sent = sandbox.cli(CHECKOUT_CLI, "send", "--text", "resumed turn", session=resumed_session)
        check(sent.get("final_text") == "echo:resumed turn", f"the resumed seat serves a turn ({sent.get('final_text')})")
        resumed_rec = sandbox.records()[records_before]
        check(argv_value(resumed_rec["argv"], "--resume") == native,
              "the artificial-reopen run really carried --resume <native>")
        resumed_ids = [entry for entry in holder_events(sandbox, resumed_session)
                       if (entry.get("update") or {}).get("sessionUpdate") == "native_session_identity"]
        check(len(resumed_ids) == 1, f"the resume-bound seat emits exactly one identity update ({len(resumed_ids)})")
        resumed_update = resumed_ids[0]["update"]
        check(resumed_update.get("nativeSessionId") == native and resumed_update.get("acpSessionId") == native,
              f"that update names the native id ({resumed_update})")
        resumed_capture = sandbox.cli(CHECKOUT_CLI, "capture", "--since", "0", session=resumed_session)
        check(native in json.dumps(resumed_capture), "capture on the resume-bound seat carries the id")
        sandbox.cli(CHECKOUT_CLI, "send", "--text", "resumed turn two", session=resumed_session)
        repeated = [entry for entry in holder_events(sandbox, resumed_session)
                    if (entry.get("update") or {}).get("sessionUpdate") == "native_session_identity"]
        check(len(repeated) == 1, f"a later turn repeats no identity update ({len(repeated)})")
        sandbox.cli(CHECKOUT_CLI, "stop", session=resumed_session)

        refused = raw_cli(sandbox, "start", "--resume", acp_id, session=sandbox.session())
        check((refused.get("error") or {}).get("code") == "resume-failed"
              and refused.get("state") != "ready",
              f"the recorded acp_session_id still cannot resume ({refused.get('error')})")
    finally:
        sandbox.cleanup()


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
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"test-issue-186: {len(CHECKS)} checks, {len(tests) - failures}/{len(tests)} tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
