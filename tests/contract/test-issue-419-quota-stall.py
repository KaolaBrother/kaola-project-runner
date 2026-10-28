#!/usr/bin/env python3
"""Issue #419: the seat stale-quota rule.

A seat with no quota/credit feedback sufficient to reply inside 5h has its grant
row auto-revoked in durable authorization (owner decision
``owner-seat-stale-quota-revoke-5h-20261028``; no tombstone, no auto-restore).
Feedback inside the window attaches a typed ``quota_hold`` whose expiry is the
same revoke. The rule is mechanical: collect index transitions and ``--usage``
envelopes are the only facts, the machine marks are reduce-only, and agent
patches cannot forge or strip the clock/hold.

Pure-function legs call ``quota_verdicts`` with an explicit ``now``; CLI legs
use times relative to real now and tmp fixtures only.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
PLATFORMS = REPO / "platforms"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for name in CALLER_ENV:
    os.environ.pop(name, None)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


DISPATCH = load("kaola_dispatch_419", SCRIPT)
RULE_ID = DISPATCH.QUOTA_RULE_ID
T0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
WINDOW = timedelta(seconds=DISPATCH.QUOTA_WINDOW_S)
HOLD = timedelta(seconds=DISPATCH.QUOTA_HOLD_S)


def ts(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stall(member: str, at: datetime = T0, kind: str = "no-reply",
          evidence: list | None = None) -> dict:
    return {"stall_at": ts(at), "kind": kind, "member": member,
            "evidence": evidence if evidence is not None else ["ix#i1"]}


def hold(member: str, until: datetime, stall_at: datetime = T0,
         feedback: str = "vendor-time", feedback_at: datetime | None = None) -> dict:
    return {"until": ts(until), "stall_at": ts(stall_at),
            "feedback_at": ts(feedback_at or stall_at), "feedback": feedback,
            "member": member, "rule": RULE_ID, "evidence": ["ix#i1", "u.json"]}


FAKE_RUNNER = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    spec = json.loads(Path(os.environ["FAKE_SPEC"]).read_text())
    argv = sys.argv[1:]
    command = argv[0]
    session = argv[argv.index("--session") + 1]
    row = spec["sessions"][session]
    print(json.dumps(row[command]))
    """
)


def run(args: list[str], env: dict | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        env=env if env is not None else
        {key: value for key, value in os.environ.items() if key not in CALLER_ENV},
        timeout=60,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def install_fake(root: Path, platforms: list[str]) -> None:
    for platform in platforms:
        dest = root / f"{platform}-kaola-project-runner" / "scripts"
        dest.mkdir(parents=True, exist_ok=True)
        script = dest / "runtime-tmux.sh"
        script.write_text(FAKE_RUNNER, encoding="utf-8")
        script.chmod(0o755)


AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1},
                   {"id": "zcode/default", "state": "granted", "count": 1}]}
DELEGATOR_AUTH = {
    "dispatch_enabled": True,
    "elite_grants": [{"preset_id": "codex/default", "count": 1, "state": "granted"},
                     {"preset_id": "zcode/default", "count": 1, "state": "granted"}],
    "worker_grants": [{"preset_ids": ["devin/default"], "count": 1, "state": "granted"}],
}


def grants_of(doc: dict) -> list:
    return (doc.get("state") or {}).get("authorization", {}).get("grants") or []


def row_ids(row: dict) -> list[str]:
    ids = row.get("preset_ids")
    if isinstance(ids, list) and ids:
        return list(ids)
    for key in ("id", "preset_id"):
        if isinstance(row.get(key), str):
            return [row[key]]
    return []


def find_row(rows: list, member: str) -> dict | None:
    return next((row for row in rows if isinstance(row, dict) and member in row_ids(row)),
                None)


class Fixture:
    """One tmp repo with both durable records under .kaola/."""

    def __init__(self, root: Path, auth: dict | None = None,
                 delegator_auth: dict | None = None) -> None:
        repo = root / "consumer"
        (repo / ".kaola").mkdir(parents=True)
        self.repo = repo.resolve()
        self.host_file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.delegator_file = self.repo / ".kaola" / "delegator-heartbeat.json"
        code, out = run(["state", "init", "--file", str(self.host_file),
                         "--writer", "host", "--source", "turn-1",
                         "--project", json.dumps({"code": "QS", "goal": "quota"}),
                         "--authorization", json.dumps(auth if auth is not None else AUTH)])
        assert code == 0, out
        self.write_delegator(delegator_auth if delegator_auth is not None else DELEGATOR_AUTH)

    def write_delegator(self, auth: dict) -> None:
        self.delegator_file.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": 1,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "authorization": auth,
        }), encoding="utf-8")

    def host(self) -> dict:
        return json.loads(self.host_file.read_text(encoding="utf-8"))

    def delegator(self) -> dict:
        return json.loads(self.delegator_file.read_text(encoding="utf-8"))

    def delegator_rows(self, collection: str = "elite_grants") -> list:
        return (self.delegator().get("authorization") or {}).get(collection) or []

    def write_host_raw(self, doc: dict) -> None:
        self.host_file.write_text(json.dumps(doc), encoding="utf-8")

    def write_delegator_raw(self, doc: dict) -> None:
        self.delegator_file.write_text(json.dumps(doc), encoding="utf-8")

    def set_host_member(self, member: str, key: str, value: dict | None) -> None:
        doc = self.host()
        for row in grants_of(doc):
            if member in row_ids(row):
                if value is None:
                    row.pop(key, None)
                else:
                    row[key] = value
        self.write_host_raw(doc)

    def set_delegator_member(self, member: str, key: str, value: dict | None,
                             collection: str = "elite_grants") -> None:
        doc = self.delegator()
        for row in (doc.get("authorization") or {}).get(collection) or []:
            if member in row_ids(row):
                if value is None:
                    row.pop(key, None)
                else:
                    row[key] = value
        self.write_delegator_raw(doc)

    def state_update_auth(self, grants: list, writer: str = "host") -> tuple[int, dict]:
        return run(["state", "update", "--file", str(self.host_file), "--writer", writer,
                    "--source", "patch", "--section", "authorization",
                    "--expect-revision", str(self.host()["revision"]),
                    "--set", json.dumps({"grants": grants})])

    def delegator_update(self, patch: dict) -> tuple[int, dict]:
        return run(["delegator", "update", "--file", str(self.delegator_file),
                    "--writer", "delegator", "--source", "patch",
                    "--expect-revision", str(self.delegator()["revision"]),
                    "--set", json.dumps(patch)])

    def state_check(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "check", "--file", str(self.host_file), *extra])

    def delegator_view(self, *extra: str) -> tuple[int, dict]:
        return run(["delegator", "view", "--file", str(self.delegator_file), *extra])


class PureVerdicts(unittest.TestCase):
    """quota_verdicts called directly with an explicit now."""

    def test_a1_stall_window_is_half_open(self) -> None:
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_stall": stall("codex/default")},
                {"id": "zcode/default", "state": "granted", "count": 1}]
        new, marks = DISPATCH.quota_verdicts(rows, [], T0 + WINDOW - timedelta(seconds=1))
        self.assertEqual(marks, [])
        self.assertIn("quota_stall", new[0])
        new, marks = DISPATCH.quota_verdicts(rows, [], T0 + WINDOW)
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["id"], "zcode/default")
        self.assertEqual(marks[0]["action"], "revoke")
        self.assertEqual(marks[0]["cause"], "no-quota-feedback")
        self.assertEqual(marks[0]["member"], "codex/default")

    def test_a2b_reply_closes_no_reply_stall(self) -> None:
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_stall": stall("codex/default")}]
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "reply", "member": "codex/default", "evidence": "ix#i2"}],
            T0 + timedelta(hours=1))
        self.assertNotIn("quota_stall", new[0])
        self.assertNotIn("quota_hold", new[0])
        self.assertEqual(marks[0]["action"], "close")

    def test_a2d_account_and_paused_close_stall(self) -> None:
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_stall": stall("codex/default")}]
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "account", "member": "codex/default", "evidence": "u"}],
            T0 + timedelta(hours=1))
        self.assertNotIn("quota_stall", new[0])
        self.assertEqual(marks[0]["action"], "close")
        paused = [{"id": "codex/default", "state": "paused", "count": 1,
                   "quota_stall": stall("codex/default")}]
        new, marks = DISPATCH.quota_verdicts(paused, [], T0 + timedelta(hours=1))
        self.assertNotIn("quota_stall", new[0])
        self.assertTrue(all(mark["action"] == "close" for mark in marks))

    def test_a3_exhausted_with_vendor_time_holds(self) -> None:
        now = T0 + timedelta(hours=1)
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_stall": stall("codex/default")}]
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "exhausted", "member": "codex/default",
                    "evidence": "u.json", "vendor_time": True}], now)
        held = new[0]["quota_hold"]
        self.assertEqual(held["feedback"], "vendor-time")
        self.assertEqual(held["until"], ts(now + HOLD))
        self.assertEqual(held["rule"], RULE_ID)
        self.assertNotIn("quota_stall", new[0])
        self.assertEqual(marks[0]["action"], "hold")
        # A machine hold never moves on later facts.
        newer, marks2 = DISPATCH.quota_verdicts(
            new, [{"kind": "reply", "member": "codex/default", "evidence": "ix#i9"}],
            now + timedelta(hours=1))
        self.assertEqual(marks2, [])
        self.assertEqual(newer[0]["quota_hold"], held)

    def test_a3b_exhausted_without_time_limits_then_holds(self) -> None:
        now = T0 + timedelta(hours=1)
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_stall": stall("codex/default")}]
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "exhausted", "member": "codex/default", "evidence": "u.json"}], now)
        self.assertEqual(new[0]["quota_stall"]["kind"], "limit")
        self.assertEqual([mark["action"] for mark in marks], ["limit"])
        self.assertEqual(new[0]["quota_stall"]["stall_at"], ts(T0))
        new2, marks2 = DISPATCH.quota_verdicts(
            new, [{"kind": "reply", "member": "codex/default", "evidence": "ix#i3"}],
            now + timedelta(hours=1))
        self.assertEqual(new2[0]["quota_hold"]["feedback"], "reply")
        self.assertEqual(marks2[0]["action"], "hold")
        new3, _m3 = DISPATCH.quota_verdicts(
            rows, [{"kind": "exhausted", "member": "codex/default", "evidence": "u.json"}], now)
        new4, marks4 = DISPATCH.quota_verdicts(
            new3, [{"kind": "quota-ok", "member": "codex/default", "evidence": "u2.json"}],
            now + timedelta(hours=1))
        self.assertEqual(new4[0]["quota_hold"]["feedback"], "quota-ok")
        self.assertEqual(marks4[0]["action"], "hold")
        # quota-ok closes a no-reply stall outright (not a quota matter).
        new5, marks5 = DISPATCH.quota_verdicts(
            rows, [{"kind": "quota-ok", "member": "codex/default", "evidence": "u2.json"}], now)
        self.assertNotIn("quota_stall", new5[0])
        self.assertEqual(marks5[0]["action"], "close")

    def test_a4_feedback_window_edge(self) -> None:
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_stall": stall("codex/default")}]
        now = T0 + WINDOW - timedelta(seconds=1)
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "reply", "member": "codex/default",
                    "evidence": "ix#i2", "at": ts(T0 + WINDOW - timedelta(seconds=1))}], now)
        # a limit stall + reply -> hold; this stall is no-reply -> close.
        self.assertNotIn("quota_stall", new[0])
        limit_rows = [{"id": "codex/default", "state": "granted", "count": 1,
                       "quota_stall": stall("codex/default", kind="limit")}]
        new, marks = DISPATCH.quota_verdicts(
            limit_rows, [{"kind": "reply", "member": "codex/default",
                          "evidence": "ix#i2", "at": ts(T0 + WINDOW - timedelta(seconds=1))}],
            now)
        self.assertEqual(marks[0]["action"], "hold")
        # at exactly stall_at + window the clock is already due: revoke.
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "reply", "member": "codex/default", "evidence": "ix#i2"}],
            T0 + WINDOW)
        self.assertEqual(marks[0]["action"], "revoke")

    def test_a5_hold_expiry(self) -> None:
        until = T0 + timedelta(hours=6)
        rows = [{"id": "codex/default", "state": "granted", "count": 1,
                 "quota_hold": hold("codex/default", until)}]
        new, marks = DISPATCH.quota_verdicts(rows, [], until - timedelta(seconds=1))
        self.assertEqual(marks, [])
        self.assertIn("quota_hold", new[0])
        new, marks = DISPATCH.quota_verdicts(rows, [], until)
        self.assertEqual(marks[0]["action"], "revoke")
        self.assertEqual(marks[0]["cause"], "quota-hold-expired")
        self.assertEqual(new, [])

    def test_a6_revoked_row_writes_nothing(self) -> None:
        rows = [{"id": "zcode/default", "state": "granted", "count": 1}]
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "reply", "member": "codex/default", "evidence": "ix"},
                    {"kind": "quota-ok", "member": "codex/default", "evidence": "u"}],
            T0 + timedelta(hours=9))
        self.assertEqual(marks, [])
        self.assertEqual(new, rows)

    def test_a10_group_row_removed_whole(self) -> None:
        rows = [{"preset_ids": ["codex/default", "zcode/default"], "state": "granted",
                 "count": 2, "quota_stall": stall("codex/default")},
                {"id": "devin/default", "state": "granted", "count": 1}]
        new, marks = DISPATCH.quota_verdicts(rows, [], T0 + WINDOW)
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["id"], "devin/default")
        self.assertEqual(marks[0]["action"], "revoke")

    def test_a11_no_facts_no_verdict(self) -> None:
        rows = [{"id": "codex/default", "state": "granted", "count": 1}]
        new, marks = DISPATCH.quota_verdicts(rows, [], T0)
        self.assertEqual(marks, [])
        self.assertEqual(new, rows)

    def test_a12_exhausted_on_never_stalled_row_opens_nothing(self) -> None:
        rows = [{"id": "codex/default", "state": "granted", "count": 1}]
        new, marks = DISPATCH.quota_verdicts(
            rows, [{"kind": "exhausted", "member": "codex/default",
                    "evidence": "u", "vendor_time": True}], T0)
        self.assertEqual(marks, [])
        self.assertNotIn("quota_stall", new[0])

    def test_a13_marks_only_reduce(self) -> None:
        before = [{"id": "codex/default", "state": "granted", "count": 1,
                   "quota_stall": stall("codex/default")},
                  {"id": "zcode/default", "state": "granted", "count": 2}]
        new, _ = DISPATCH.quota_verdicts(before, [], T0 + WINDOW)
        for row in new:
            self.assertIn(row, before)


class CollectFacts(unittest.TestCase):
    """A2: index transitions during collect open/close the machine clock."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i419-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skills = self.root / "skills"
        install_fake(self.skills, ["codex", "zcode"])
        self.env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        self.spec_path = self.root / "spec.json"

    def fixture(self) -> Fixture:
        root = self.root / f"case-{len(list(self.root.glob('case-*')))}"
        return Fixture(root)

    def use_spec(self, sessions: dict) -> None:
        self.spec_path.write_text(json.dumps({"sessions": sessions}))
        self.env["FAKE_SPEC"] = str(self.spec_path)

    def collect(self, index: Path, *extra: str) -> tuple[int, dict]:
        return run(["collect", "--index", str(index), "--skills-root", str(self.skills),
                    *extra], self.env)

    def item(self, name: str, preset: str, session: str, **extra) -> dict:
        row = {"item_id": name, "platform": preset.split("/")[0], "preset": preset,
               "session": session, "holder_instance_id": "h-1",
               "prompt_fingerprint": f"fp-{name}", "status": "in-flight"}
        row.update(extra)
        return row

    def status(self, repo: Path, session: str, **extra) -> dict:
        row = {"repo": str(repo), "session": session, "holder_instance_id": "h-1",
               "prompt_fingerprint": None, "mutation_status": "completed",
               "turn_active": False, "turn_outcome": "turn_completed",
               "stop_reason": "end_turn"}
        row.update(extra)
        return row

    def test_collect_turn_failed_opens_stall_in_both_records(self) -> None:
        fx = self.fixture()
        session = "codex-KPR-i419-stall"
        status = self.status(fx.repo, session, turn_outcome="turn_failed",
                             prompt_fingerprint="fp-a")
        self.use_spec({session: {"status": status, "capture": {"events": []}}})
        index = self.root / "index.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(fx.repo),
            "items": [self.item("a", "codex/default", session)]}))
        code, out = self.collect(index)
        self.assertEqual(code, 0, out)
        marks = [mark for mark in out["quota_marks"] if mark["action"] == "open"]
        self.assertEqual({mark["record"] for mark in marks}, {"host", "delegator"})
        host_row = find_row(grants_of(fx.host()), "codex/default")
        self.assertEqual(host_row["quota_stall"]["kind"], "no-reply")
        self.assertEqual(host_row["quota_stall"]["member"], "codex/default")
        self.assertEqual(host_row["quota_stall"]["evidence"], [f"{index}#a"])
        delegator_row = find_row(fx.delegator_rows(), "codex/default")
        self.assertEqual(delegator_row["quota_stall"]["kind"], "no-reply")
        # The marks stay out of the index file.
        self.assertNotIn("quota_marks", json.loads(index.read_text()))

    def test_collect_non_failure_outcomes_open_no_stall(self) -> None:
        for label, status_extra, extra_receipt in (
                ("canceled", {"turn_outcome": "turn_canceled"}, {}),
                ("exited", {"turn_outcome": "process_exited"}, {}),
                ("refused", {"result": "refused", "turn_outcome": None,
                             "mutation_status": "completed"}, {}),
                ("unknown", {"turn_outcome": "unknown", "mutation_status": "unknown"}, {})):
            fx = self.fixture()
            session = f"codex-KPR-i419-{label}"
            status = self.status(fx.repo, session, **status_extra)
            self.use_spec({session: {"status": status, "capture": {"events": []}, **extra_receipt}})
            index = self.root / f"index-{label}.json"
            index.write_text(json.dumps({
                "schema": "kaola-dispatch-index/1", "repo": str(fx.repo),
                "items": [self.item(label, "codex/default", session)]}))
            code, out = self.collect(index)
            self.assertEqual(code, 0, (label, out))
            self.assertEqual(out["quota_marks"], [], label)
            self.assertNotIn("quota_stall", find_row(grants_of(fx.host()), "codex/default"), label)

    def test_collect_reply_closes_stall(self) -> None:
        fx = self.fixture()
        now = datetime.now(timezone.utc)
        fx.set_host_member("codex/default", "quota_stall", stall("codex/default", now))
        fx.set_delegator_member("codex/default", "quota_stall", stall("codex/default", now))
        session = "codex-KPR-i419-reply"
        status = self.status(fx.repo, session, prompt_fingerprint="fp-r")
        capture = {"events": [{"role": "assistant", "text": "done"}]}
        self.use_spec({session: {"status": status, "capture": capture}})
        index = self.root / "index-reply.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(fx.repo),
            "items": [self.item("r", "codex/default", session,
                                prompt_fingerprint="fp-r")]}))
        code, out = self.collect(index)
        self.assertEqual(code, 0, out)
        self.assertTrue(any(mark["action"] == "close" for mark in out["quota_marks"]))
        self.assertNotIn("quota_stall", find_row(grants_of(fx.host()), "codex/default"))
        self.assertNotIn("quota_stall", find_row(fx.delegator_rows(), "codex/default"))

    def test_collect_host_role_item_opens_no_stall(self) -> None:
        fx = self.fixture()
        session = "codex-KPR-i419-hostrole"
        status = self.status(fx.repo, session, turn_outcome="turn_failed",
                             prompt_fingerprint="fp-h")
        self.use_spec({session: {"status": status, "capture": {"events": []}}})
        index = self.root / "index-host.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(fx.repo),
            "items": [self.item("h", "codex/default", session, session_role="host",
                                prompt_fingerprint="fp-h")]}))
        code, out = self.collect(index)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["quota_marks"], [])
        self.assertNotIn("quota_stall", find_row(grants_of(fx.host()), "codex/default"))


class UsageEnvelopes(unittest.TestCase):
    """--usage envelope classification and member-pool matching."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i419-usage-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._pool_member: str | None = None
        self._pool: str | None = None
        self._unmapped: str | None = None
        catalog = DISPATCH.catalog_from_files(DISPATCH.platform_paths(SCRIPT, str(PLATFORMS)))
        caches: dict = {}
        for preset in sorted(catalog):
            pool = DISPATCH.quota_member_pool(preset, catalog, caches)
            if pool and self._pool_member is None:
                self._pool_member, self._pool = preset, pool
            if pool is None and self._unmapped is None and "/" in preset:
                self._unmapped = preset
        self.catalog = catalog

    def usage_file(self, name: str, usage: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(usage), encoding="utf-8")
        return path

    def test_envelope_classification(self) -> None:
        ok = {"status": "ok", "windows": {"5h": {"remaining_fraction": 0.9}}}
        self.assertEqual(DISPATCH.quota_classify_envelope(ok), ("quota-ok", False))
        ex = {"status": "ok", "windows": {"5h": {"remaining_fraction": 0.0,
                                                 "reset_at": "2026-01-01T06:00:00Z"}}}
        self.assertEqual(DISPATCH.quota_classify_envelope(ex), ("exhausted", True))
        ex2 = {"status": "ok", "windows": {"weekly": {"exceeded": True, "reset_at": None}}}
        self.assertEqual(DISPATCH.quota_classify_envelope(ex2), ("exhausted", False))
        self.assertEqual(DISPATCH.quota_classify_envelope({"status": "login_required"}),
                         ("account", False))
        self.assertIsNone(DISPATCH.quota_classify_envelope({"status": "unavailable"}))
        self.assertIsNone(DISPATCH.quota_classify_envelope({"status": "key_missing"}))

    def test_exhausted_envelope_with_reset_holds_stall(self) -> None:
        if not self._pool_member:
            self.skipTest("no mapped preset in this manifest set")
        fx = Fixture(self.root / "mapped", auth={
            "grants": [{"id": self._pool_member, "state": "granted", "count": 1}]},
            delegator_auth={"elite_grants": [
                {"preset_id": self._pool_member, "count": 1, "state": "granted"}]})
        now = datetime.now(timezone.utc)
        fx.set_host_member(self._pool_member, "quota_stall", stall(self._pool_member, now))
        fx.set_delegator_member(self._pool_member, "quota_stall", stall(self._pool_member, now))
        usage = self.usage_file("usage.json", {"usage": {
            "packageId": self._pool, "status": "ok",
            "windows": {"5h": {"remaining_fraction": 0.0,
                               "reset_at": "2027-01-01T00:00:00Z"}}}})
        code, out = fx.state_check("--usage", str(usage))
        self.assertEqual(code, 0, out)
        self.assertTrue(any(mark["action"] == "hold" and mark["feedback"] == "vendor-time"
                            for mark in out["quota_marks"]))
        held = find_row(grants_of(fx.host()), self._pool_member)["quota_hold"]
        until = datetime.strptime(held["until"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        feedback = datetime.strptime(
            held["feedback_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertEqual((until - feedback).total_seconds(), DISPATCH.QUOTA_HOLD_S)
        # Repeat beat: no write (revisions unchanged).
        rev_host = fx.host()["revision"]
        rev_del = fx.delegator()["revision"]
        code, out2 = fx.state_check("--usage", str(usage))
        self.assertEqual(code, 0, out2)
        self.assertEqual(out2["quota_marks"], [])
        self.assertTrue(out2["read_only"])
        self.assertEqual(fx.host()["revision"], rev_host)
        self.assertEqual(fx.delegator()["revision"], rev_del)

    def test_unmapped_preset_matches_no_envelope(self) -> None:
        # A preset absent from the catalog resolves no model and no pool, so no
        # envelope can ever apply to it. If a manifest preset is unmapped, cover
        # it too.
        members = ["noplatform/default"] + ([self._unmapped] if self._unmapped else [])
        for member in members:
            fx = Fixture(self.root / f"unmapped-{member.replace('/', '-')}", auth={
                "grants": [{"id": member, "state": "granted", "count": 1}]},
                delegator_auth={"elite_grants": [
                    {"preset_id": member, "count": 1, "state": "granted"}]})
            fx.set_host_member(member, "quota_stall",
                               stall(member, datetime.now(timezone.utc)))
            usage = self.usage_file(f"usage-{member.replace('/', '-')}.json", {
                "packageId": "unrelated-pool", "status": "ok",
                "windows": {"5h": {"remaining_fraction": 0.0, "reset_at": None}}})
            code, out = fx.state_check("--usage", str(usage))
            self.assertEqual(code, 0, out)
            self.assertEqual(out["quota_marks"], [], member)
            self.assertIn("quota_stall", find_row(grants_of(fx.host()), member), member)


class HookBeats(unittest.TestCase):
    """A1/A5/A14: the beat entry points apply the machine marks."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i419-hooks-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, name: str, **kwargs) -> Fixture:
        return Fixture(self.root / name, **kwargs)

    def test_state_check_applies_due_revoke_both_records(self) -> None:
        fx = self.fixture("due")
        past = ts(datetime.now(timezone.utc) - WINDOW - timedelta(seconds=1))
        fx.set_host_member("codex/default", "quota_stall",
                           stall("codex/default", datetime.now(timezone.utc) - WINDOW
                                 - timedelta(seconds=1)))
        fx.set_delegator_member("codex/default", "quota_stall",
                                stall("codex/default", datetime.now(timezone.utc)
                                      - WINDOW - timedelta(seconds=1)))
        before_host = grants_of(fx.host())
        code, out = fx.state_check()
        self.assertEqual(code, 0, out)
        self.assertFalse(out["read_only"])
        causes = {mark["cause"] for mark in out["quota_marks"] if mark["action"] == "revoke"}
        self.assertEqual(causes, {"no-quota-feedback"})
        self.assertEqual({mark["record"] for mark in out["quota_marks"]
                          if mark["action"] == "revoke"}, {"host", "delegator"})
        after_host = grants_of(fx.host())
        self.assertIsNone(find_row(after_host, "codex/default"))
        self.assertIsNone(find_row(fx.delegator_rows(), "codex/default"))
        # Every other row is byte-equal.
        self.assertEqual([row for row in before_host if "codex/default" not in row_ids(row)],
                         after_host)
        # The warn alert names the removed row, the cause, and the rule.
        alerts = fx.host()["state"].get("alerts") or {}
        alert = alerts.get("quota-revoked-codex-default")
        self.assertIsNotNone(alert)
        self.assertEqual(alert["level"], "warn")
        self.assertEqual(alert["writer"], "quota-rule")
        self.assertEqual(alert["source"], RULE_ID)
        self.assertIn("no-quota-feedback", alert["summary"])
        self.assertIn(RULE_ID, alert["summary"])
        # No second beat writes again.
        code, out2 = fx.state_check()
        self.assertEqual(code, 0, out2)
        self.assertTrue(out2["read_only"])
        self.assertEqual(out2["quota_marks"], [])

    def test_delegator_view_applies_due_revoke(self) -> None:
        fx = self.fixture("dview")
        fx.set_delegator_member("codex/default", "quota_stall",
                                stall("codex/default", datetime.now(timezone.utc)
                                      - WINDOW - timedelta(seconds=1)))
        code, out = fx.delegator_view()
        self.assertEqual(code, 0, out)
        self.assertTrue(any(mark["action"] == "revoke" and mark["record"] == "delegator"
                            for mark in out["quota_marks"]))
        self.assertIsNone(find_row(fx.delegator_rows(), "codex/default"))

    def test_execute_applies_before_admission_and_dry_run_withholds(self) -> None:
        fx = self.fixture("exec")
        skills = self.root / "exec-skills"
        install_fake(skills, ["codex"])
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        due = datetime.now(timezone.utc) - WINDOW - timedelta(seconds=1)
        fx.set_host_member("codex/default", "quota_stall", stall("codex/default", due))
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(fx.repo),
            "items": [{"item_id": "seat", "preset": "codex/default",
                       "session": "codex-KPR-i419-seat", "prompt": "go"}]}))
        # Dry run: nothing written, the due seat is withheld and reported.
        code, out = run(["execute", "--plan", str(plan), "--authorization",
                         str(fx.host_file), "--platforms", str(PLATFORMS),
                         "--skills-root", str(skills), "--dry-run"], env)
        self.assertEqual(code, 0, out)
        self.assertTrue(any(mark["action"] == "revoke" for mark in out["quota_marks_due"]))
        item = next(row for row in out["items"] if row["item_id"] == "seat")
        self.assertEqual(item["reason"], "quota-revoked")
        self.assertIsNotNone(find_row(grants_of(fx.host()), "codex/default"))
        # Non-dry-run persists the revoke before admission.
        code, out = run(["execute", "--plan", str(plan), "--authorization",
                         str(fx.host_file), "--platforms", str(PLATFORMS),
                         "--skills-root", str(skills)], env)
        self.assertEqual(code, 0, out)
        self.assertIsNone(find_row(grants_of(fx.host()), "codex/default"))
        item = next(row for row in out["items"] if row["item_id"] == "seat")
        self.assertEqual(item["reason"], "quota-revoked")

    def test_no_facts_no_write(self) -> None:
        fx = self.fixture("quiet")
        rev_host = fx.host()["revision"]
        code, out = fx.state_check()
        self.assertEqual(code, 0, out)
        self.assertTrue(out["read_only"])
        self.assertEqual(out["quota_marks"], [])
        self.assertEqual(fx.host()["revision"], rev_host)


class HoldExpiryBeats(unittest.TestCase):
    """A5: a machine hold expires into the same revoke in both records."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i419-hold-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_hold_expiry_revokes_both_records(self) -> None:
        fx = Fixture(self.root / "hold")
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        stall_at = past - WINDOW
        member_hold = hold("codex/default", past, stall_at=stall_at,
                           feedback_at=stall_at + timedelta(hours=1))
        fx.set_host_member("codex/default", "quota_hold", member_hold)
        fx.set_delegator_member("codex/default", "quota_hold", member_hold)
        code, out = fx.state_check()
        self.assertEqual(code, 0, out)
        causes = {mark["cause"] for mark in out["quota_marks"] if mark["action"] == "revoke"}
        self.assertEqual(causes, {"quota-hold-expired"})
        self.assertIsNone(find_row(grants_of(fx.host()), "codex/default"))
        self.assertIsNone(find_row(fx.delegator_rows(), "codex/default"))
        self.assertIn("quota-revoked-codex-default", fx.host()["state"].get("alerts") or {})

    def test_unexpired_hold_survives(self) -> None:
        fx = Fixture(self.root / "hold-open")
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        fx.set_host_member("codex/default", "quota_hold",
                           hold("codex/default", future,
                                stall_at=future - HOLD - timedelta(hours=1),
                                feedback_at=future - HOLD))
        rev = fx.host()["revision"]
        code, out = fx.state_check()
        self.assertEqual(code, 0, out)
        self.assertTrue(out["read_only"])
        self.assertIsNotNone(find_row(grants_of(fx.host()), "codex/default"))
        self.assertEqual(fx.host()["revision"], rev)


class AgentWriteGuards(unittest.TestCase):
    """A6/A7: agent writes cannot forge or strip the machine members."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i419-guard-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_patch_adding_row_with_members_refused(self) -> None:
        fx = Fixture(self.root / "add")
        rows = grants_of(fx.host()) + [{"id": "opencode/default", "state": "granted",
                                        "count": 1,
                                        "quota_hold": hold("opencode/default", T0)}]
        code, out = fx.state_update_auth(rows)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "invalid-input")
        self.assertIn("quota", out["detail"])
        self.assertIsNone(find_row(grants_of(fx.host()), "opencode/default"))

    def test_patch_changing_member_refused(self) -> None:
        fx = Fixture(self.root / "change")
        held = hold("codex/default", T0 + HOLD)
        fx.set_host_member("codex/default", "quota_hold", held)
        rows = grants_of(fx.host())
        for row in rows:
            if "codex/default" in row_ids(row):
                row["quota_hold"] = dict(held, feedback="reply")
        code, out = fx.state_update_auth(rows)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "invalid-input")
        stored = find_row(grants_of(fx.host()), "codex/default")
        self.assertEqual(stored["quota_hold"]["feedback"], "vendor-time")

    def test_patch_omitting_members_preserves_them(self) -> None:
        fx = Fixture(self.root / "omit")
        fx.set_host_member("codex/default", "quota_stall", stall("codex/default", datetime.now(timezone.utc)))
        rows = grants_of(fx.host())
        patch_rows = [{key: value for key, value in row.items()
                       if key not in ("quota_stall", "quota_hold")} for row in rows]
        for row in patch_rows:
            if "codex/default" in row_ids(row):
                row["count"] = 3
        code, out = fx.state_update_auth(patch_rows)
        self.assertEqual(code, 0, out)
        stored = find_row(grants_of(fx.host()), "codex/default")
        self.assertEqual(stored["quota_stall"]["kind"], "no-reply")
        self.assertEqual(stored["count"], 3)

    def test_init_with_members_refused(self) -> None:
        root = self.root / "init"
        repo = root / "consumer"
        (repo / ".kaola").mkdir(parents=True)
        auth = {"grants": [{"id": "codex/default", "state": "granted", "count": 1,
                            "quota_stall": stall("codex/default")}]}
        code, out = run(["state", "init", "--file",
                         str(repo / ".kaola" / "heartbeat-prompt.json"),
                         "--writer", "host", "--source", "t",
                         "--authorization", json.dumps(auth)])
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "invalid-input")

    def test_delegator_update_guards(self) -> None:
        fx = Fixture(self.root / "dguard")
        fx.set_delegator_member("codex/default", "quota_hold",
                                hold("codex/default", T0 + HOLD))
        rows = fx.delegator_rows()
        for row in rows:
            if "codex/default" in row_ids(row):
                row["quota_hold"] = dict(row["quota_hold"], feedback="reply")
        code, out = fx.delegator_update({"authorization": {"elite_grants": rows}})
        self.assertEqual(code, 2, out)
        self.assertEqual(out["reason"], "invalid-input")
        stored = find_row(fx.delegator_rows(), "codex/default")
        self.assertEqual(stored["quota_hold"]["feedback"], "vendor-time")
        # Adding a row carrying a member is refused too.
        added = list(fx.delegator_rows()) + [
            {"preset_id": "opencode/default", "count": 1, "state": "granted",
             "quota_stall": stall("opencode/default")}]
        code, out = fx.delegator_update({"authorization": {"elite_grants": added}})
        self.assertEqual(code, 2, out)
        # Omitting the member on the same-identity row carries it forward.
        clean = [{key: value for key, value in row.items()
                  if key not in ("quota_stall", "quota_hold")}
                 for row in fx.delegator_rows()]
        for row in clean:
            if "codex/default" in row_ids(row):
                row["count"] = 5
        code, out = fx.delegator_update({"authorization": {"elite_grants": clean}})
        self.assertEqual(code, 0, out)
        stored = find_row(fx.delegator_rows(), "codex/default")
        self.assertIn("quota_hold", stored)
        self.assertEqual(stored["count"], 5)

    def test_readd_after_revoke_is_a_clean_row(self) -> None:
        fx = Fixture(self.root / "readd")
        due = datetime.now(timezone.utc) - WINDOW - timedelta(seconds=1)
        fx.set_host_member("codex/default", "quota_stall", stall("codex/default", due))
        code, out = fx.state_check()
        self.assertEqual(code, 0, out)
        self.assertIsNone(find_row(grants_of(fx.host()), "codex/default"))
        rows = grants_of(fx.host()) + [{"id": "codex/default", "state": "granted",
                                        "count": 1}]
        code, out = fx.state_update_auth(rows)
        self.assertEqual(code, 0, out)
        stored = find_row(grants_of(fx.host()), "codex/default")
        self.assertNotIn("quota_stall", stored)
        self.assertNotIn("quota_hold", stored)

    def test_removing_row_takes_members(self) -> None:
        fx = Fixture(self.root / "remove")
        fx.set_host_member("codex/default", "quota_stall", stall("codex/default", datetime.now(timezone.utc)))
        rows = [row for row in grants_of(fx.host())
                if "codex/default" not in row_ids(row)]
        code, out = fx.state_update_auth(rows)
        self.assertEqual(code, 0, out)
        self.assertIsNone(find_row(grants_of(fx.host()), "codex/default"))


class MemberShape(unittest.TestCase):
    """Schema legs: validators refuse malformed members; migrate preserves."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i419-shape-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.record = load("kaola_record_419", REPO / "scripts" / "kaola-record-contract.py")

    def auth_blockers(self, grants: list) -> list:
        return self.record.authorization_blockers({"grants": grants})

    def test_malformed_members_refused(self) -> None:
        good = {"id": "codex/default", "state": "granted", "count": 1}
        bad_cases = [
            dict(good, quota_stall=dict(stall("codex/default"), stall_at="not-a-time")),
            dict(good, quota_stall=dict(stall("codex/default"), extra="x")),
            dict(good, quota_stall=stall("other/preset")),
            dict(good, quota_hold=dict(hold("codex/default", T0), rule="wrong")),
            dict(good, quota_stall=stall("codex/default"),
                 quota_hold=hold("codex/default", T0)),
            dict(good, quota_hold=dict(hold("codex/default", T0), feedback="nope")),
            dict(good, quota_stall=stall("codex/default", evidence=[])),
        ]
        for grant in bad_cases:
            self.assertTrue(self.auth_blockers([grant]), grant)
        self.assertEqual(self.auth_blockers(
            [dict(good, quota_stall=stall("codex/default"))]), [])
        self.assertEqual(self.auth_blockers(
            [dict(good, quota_hold=hold("codex/default", T0 + HOLD))]), [])

    def test_delegator_member_shape_refused(self) -> None:
        auth = {"elite_grants": [{"preset_id": "codex/default", "count": 1,
                                  "state": "granted", "quota_stall": stall("other/x")}]}
        self.assertTrue(self.record.delegator_authorization_blockers(auth))
        auth["elite_grants"][0]["quota_stall"] = stall("codex/default")
        self.assertEqual(self.record.delegator_authorization_blockers(auth), [])

    def test_migrate_preserves_members(self) -> None:
        member = stall("codex/default")
        out, blockers, _dropped = self.record.migrate_authorization_limits(
            {"grants": [{"id": "codex/default", "state": "granted", "count": 1,
                         "quota_stall": member}]})
        self.assertEqual(blockers, [])
        self.assertEqual(out["grants"][0]["quota_stall"], member)

    def test_state_migrate_accepts_members(self) -> None:
        fx = Fixture(self.root / "mig")
        fx.set_host_member("codex/default", "quota_stall", stall("codex/default", datetime.now(timezone.utc)))
        code, out = fx.state_check()
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
