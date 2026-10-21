#!/usr/bin/env python3
"""Issue #372: retire an outcome-absent collect once its session is stopped.

The real failure: an accepted-done task kept a collected status with
``outcome: null`` (the seat was read while a later prompt was queued), its
status read had already recorded ``error_code: no-session``, and
``kaola-acp list --include-dead`` listed the session as ``stopped`` under the
recorded holder. ``stale_collect_session_gone`` counted that row as still
listed, so the task could never retire; ``state check`` still advertised the
retire command its own route refused.

This suite pins the Host-adjudicated shape: the no-session gate is gone (the
i241 status-less shape now retires), a stopped row under the recorded holder
counts as gone (strict: every row for the session must be stopped and carry
that holder), a mid-queue collect records its turn facts, and both
``state check`` emitters refuse to print a command ``open_dispatch`` would
reject. It also covers the session-gone reason on the dead-holder route
(#377's new branch).
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for _name in CALLER_ENV:
    os.environ.pop(_name, None)

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1}]}
CITE = json.dumps({"path": "README.md", "locator": "README.md"})
ROUTE = "stale-collect session-gone route"
ROUTE_KEY = "stale-collect-session-gone"
SESSION = "devin-KGIT-i360-modeenv"
HOLDER = "holder-i360"
ITEM = "i360-modeenv"


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args]
        if args[:2] != [sys.executable, str(SCRIPT)] else args,
        capture_output=True, text=True,
        env=env if env is not None else {k: v for k, v in os.environ.items()
                                         if k not in CALLER_ENV},
        timeout=60,
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def execute(command: str) -> tuple[int, dict]:
    return run(shlex.split(command))


class Fixture:
    """The issue shape: one accepted-done task, one index row, one live row."""

    def __init__(self, root: Path, *, collect_outcome=None,
                 collect_mutation: str = "accepted",
                 live_state: str = "stopped", live_holder=HOLDER,
                 live_rows: list[dict] | None = None,
                 with_collect: bool = True, include_status: bool = True,
                 status_error: str | None = "no-session",
                 reason: str = "fingerprint-differs") -> None:
        self.repo = root / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.index = self.repo / "dispatch-index.json"
        self.live = self.repo / "live.json"
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1",
                         "--project", json.dumps({"code": "KGIT", "goal": "ship"}),
                         "--authorization", json.dumps(AUTH)])
        assert code == 0, out
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "t1", "--set",
                         json.dumps({"stage": "done", "goal": "g",
                                     "verdict": {"value": "accepted"},
                                     "dispatch": [ITEM],
                                     "dispositions": {ITEM: "accepted"}})])
        assert code == 0, out
        self.rev = str(self.doc()["state"]["tasks"]["t1"]["rev"])
        evidence: dict = {}
        if include_status:
            status = {"exit_code": 0, "holder_instance_id": None, "repo": str(self.repo)}
            if status_error is not None:
                status["error_code"] = status_error
            evidence["status"] = status
        if with_collect:
            evidence["collect_status"] = {
                "holder_instance_id": HOLDER,
                "mutation_status": collect_mutation,
                "outcome": collect_outcome,
                "prompt_fingerprint": "sha256:later-queued",
                "repo": str(self.repo),
                "result": None,
            }
        row = {"item_id": ITEM, "task_id": "t1", "status": "unknown",
               "reason": reason, "session": SESSION,
               "holder_instance_id": HOLDER, "platform": "devin", "repo": str(self.repo),
               "prompt_fingerprint": "sha256:original-send",
               "evidence": evidence}
        self.index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": [row],
        }), encoding="utf-8")
        if live_rows is None:
            live_row = {"session": SESSION, "state": live_state, "platform": "devin",
                        "repo": str(self.repo)}
            if live_holder is not None:
                live_row["holder_instance_id"] = live_holder
            live_rows = [live_row]
        self.live.write_text(json.dumps({
            "schema": "kaola-acp-list/1", "rows": live_rows,
        }), encoding="utf-8")
        self.index_before = self.index.read_bytes()
        self.file_before = self.file.read_bytes()

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def retire(self) -> tuple[int, dict]:
        return run(["state", "retire", "--file", str(self.file), "--writer", "host",
                    "--source", "s", "--kind", "tasks", "--id", "t1",
                    "--expect-rev", self.rev, "--evidence", "original close-out evidence",
                    "--cite", CITE, "--index", str(self.index), "--live", str(self.live)])

    def check(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "check", "--file", str(self.file), *extra])

    def task_gone(self) -> bool:
        return "t1" not in self.doc()["state"].get("tasks", {})


class StaleCollectRetire(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i372-")
        self.addCleanup(self.tmp.cleanup)
        self.case = 0

    def fixture(self, **kwargs) -> Fixture:
        self.case += 1
        root = Path(self.tmp.name) / f"case-{self.case}"
        root.mkdir()
        return Fixture(root, **kwargs)

    # -- retire route -----------------------------------------------------

    def test_outcome_absent_collect_with_stopped_matching_holder_retires(self) -> None:
        fx = self.fixture()
        code, out = fx.retire()
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "written")
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], ROUTE_KEY)
        self.assertEqual(entry["live"], "stopped")
        self.assertEqual(entry["reason"], "fingerprint-differs")
        self.assertEqual(entry["collect_status"], "unknown")
        self.assertEqual(entry["holder_instance_id"], HOLDER)
        self.assertEqual(entry["evidence"], "original close-out evidence")
        self.assertTrue(fx.task_gone())
        self.assertFalse(fx.doc()["state"].get("retired"))
        self.assertEqual(fx.index.read_bytes(), fx.index_before)

    def test_continuation_control_keeps_its_own_route(self) -> None:
        fx = self.fixture(collect_outcome="stopped", collect_mutation="completed")
        code, out = fx.retire()
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertNotIn("route", entry)
        self.assertEqual(entry["reason"], "fingerprint-differs")
        self.assertEqual(fx.index.read_bytes(), fx.index_before)
        self.assertTrue(fx.task_gone())

    def test_live_non_stopped_session_refuses(self) -> None:
        fx = self.fixture(live_state="ready")
        code, out = fx.retire()
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn(ROUTE, out["detail"])
        self.assertIn("still live", out["detail"])
        self.assertFalse(fx.task_gone())
        self.assertEqual(fx.file.read_bytes(), fx.file_before)
        self.assertEqual(fx.index.read_bytes(), fx.index_before)

    def test_stopped_foreign_holder_refuses(self) -> None:
        fx = self.fixture(live_holder="holder-other")
        code, out = fx.retire()
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("foreign holder", out["detail"])
        self.assertIn("holder-other", out["detail"])
        self.assertFalse(fx.task_gone())
        self.assertEqual(fx.file.read_bytes(), fx.file_before)
        self.assertEqual(fx.index.read_bytes(), fx.index_before)

    def test_mixed_holder_rows_strictly_refuse(self) -> None:
        own = {"session": SESSION, "state": "stopped", "platform": "devin"}
        # The dead-holder route would accept one matching row among foreign
        # ones; this route must not.
        fx = self.fixture()
        fx.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": [
            {**own, "repo": str(fx.repo), "holder_instance_id": HOLDER},
            {**own, "repo": str(fx.repo), "holder_instance_id": "holder-foreign"},
        ]}), encoding="utf-8")
        code, out = fx.retire()
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("foreign holder", out["detail"])
        self.assertFalse(fx.task_gone())

        # A stopped row that names no holder is not the recorded holder either.
        fx = self.fixture()
        fx.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": [
            {**own, "repo": str(fx.repo)},
        ]}), encoding="utf-8")
        code, out = fx.retire()
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("foreign holder", out["detail"])
        self.assertFalse(fx.task_gone())

    def test_status_less_collect_retires_on_the_same_route(self) -> None:
        # i241: the status read predates the no-session error shape. The old
        # gate dropped the row; collected proof and the stopped holder decide.
        fx = self.fixture(include_status=False)
        code, out = fx.retire()
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], ROUTE_KEY)
        self.assertEqual(entry["live"], "stopped")
        self.assertTrue(fx.task_gone())

    def test_old_no_session_guard_shape_now_retires(self) -> None:
        # Replaces test-issue-354's test_guard_collect_without_no_session_
        # stays_unknown: an error-code-less status row with live absent is now
        # the same named route, not permanent residue.
        fx = self.fixture(status_error=None, live_rows=[])
        code, out = fx.retire()
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], ROUTE_KEY)
        self.assertEqual(entry["live"], "absent")
        self.assertTrue(fx.task_gone())
        self.assertEqual(fx.index.read_bytes(), fx.index_before)

    def test_session_gone_row_retires_on_the_dead_holder_route(self) -> None:
        # #377's new unknown reason: no collected proof and a stopped row under
        # the recorded holder. The dead-holder route now owns it.
        fx = self.fixture(with_collect=False, reason="session-gone")
        code, out = fx.retire()
        self.assertEqual(code, 0, out)
        entry = out["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["reason"], "session-gone")
        self.assertEqual(entry["live"], "stopped")
        self.assertNotIn("route", entry)
        self.assertTrue(fx.task_gone())

    # -- collect evidence -------------------------------------------------

    def _fake_runner(self, root: Path) -> Path:
        skills = root / "skills"
        dest = skills / "devin-kaola-project-runner" / "scripts"
        dest.mkdir(parents=True)
        script = dest / "runtime-tmux.sh"
        script.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import json, os, sys

            argv = sys.argv[1:]
            session = argv[argv.index("--session") + 1]
            print(json.dumps({
                "repo": os.environ["FAKE_REPO"], "session": session,
                "holder_instance_id": os.environ["FAKE_HOLDER"],
                "prompt_fingerprint": "sha256:later-queued",
                "mutation_status": "accepted",
                "turn_active": True, "turn_outcome": None, "stop_reason": None,
                "result": None,
            }))
            """), encoding="utf-8")
        script.chmod(0o755)
        return skills

    def test_mid_queue_collect_records_turn_facts(self) -> None:
        root = Path(self.tmp.name) / "collect"
        repo = root / "consumer"
        (repo / ".kaola").mkdir(parents=True)
        (repo / "README.md").write_text("evidence\n", encoding="utf-8")
        skills = self._fake_runner(root)
        index = repo / "dispatch-index.json"
        index.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(repo), "items": [{
                "item_id": ITEM, "preset": "devin/default", "platform": "devin",
                "session": SESSION, "repo": str(repo), "holder_instance_id": HOLDER,
                "prompt_fingerprint": "sha256:original-send",
                "prompt_sha256": "sha256:original-send",
                "status": "in-flight", "acceptance": "pending", "task_id": "t1",
            }],
        }), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        env.update(FAKE_REPO=str(repo), FAKE_HOLDER=HOLDER)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "collect", "--index", str(index),
             "--skills-root", str(skills)],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        row = json.loads(proc.stdout)["items"][0]
        self.assertEqual(row["status"], "unknown")
        self.assertEqual(row["reason"], "fingerprint-differs")
        collect = row["evidence"]["collect_status"]
        self.assertEqual(collect["prompt_fingerprint"], "sha256:later-queued")
        self.assertEqual(collect["mutation_status"], "accepted")
        self.assertIsNone(collect["outcome"])
        self.assertIs(collect["turn_active"], True)
        self.assertIsNone(collect["turn_outcome"])
        self.assertIsNone(collect["stop_reason"])
        self.assertNotIn("receipt_fingerprint", collect)

    # -- state check emission points -------------------------------------

    def _emitted(self, out: dict) -> dict[str, dict]:
        return {row["code"]: row for row in out.get("problems") or []
                if row.get("id") == "t1"
                and row.get("code") in ("done-not-retired", "state-bloat")}

    def test_state_check_omits_a_refused_command_from_both_emitters(self) -> None:
        fx = self.fixture(live_state="ready")
        code, out = fx.check("--index", str(fx.index), "--live", str(fx.live))
        self.assertEqual(code, 0, out)
        emitted = self._emitted(out)
        self.assertEqual(set(emitted), {"done-not-retired", "state-bloat"}, out)
        for row in emitted.values():
            self.assertFalse(row.get("command"), row)
            self.assertIn("No runnable retire command", row["detail"])
            self.assertIn("still live", row["detail"])
            self.assertNotIn("state retire", row["detail"])
        terminal = [row for row in out["diagnosis"]["terminal"] if row.get("id") == "t1"]
        self.assertEqual(len(terminal), 1, out)
        self.assertEqual(terminal[0]["command"], "")

    def test_state_check_without_index_and_live_explains_the_inputs(self) -> None:
        fx = self.fixture()
        code, out = fx.check()
        self.assertEqual(code, 0, out)
        emitted = self._emitted(out)
        self.assertEqual(set(emitted), {"done-not-retired", "state-bloat"}, out)
        for row in emitted.values():
            self.assertFalse(row.get("command"), row)
            self.assertIn("No runnable retire command", row["detail"])
            self.assertIn("--index and --live", row["detail"])
            self.assertNotIn("state retire", row["detail"])
        self.assertEqual(out["unchecked"], ["index", "live"])

    def test_state_check_keeps_runnable_commands_for_non_task_rows(self) -> None:
        fx = self.fixture()
        code, out = run(["state", "update", "--file", str(fx.file), "--writer", "host",
                         "--source", "evt", "--kind", "alerts", "--id", "resolved-row",
                         "--set", json.dumps({"level": "watch", "summary": "handled",
                                              "inputs": {}})])
        self.assertEqual(code, 0, out)
        doc = fx.doc()
        doc["state"]["decisions"]["settled-row"] = {
            "owner": "user", "question": "ship?", "status": "settled",
            "evidence": "owner said yes", "rev": 1, "source": "evt", "writer": "host",
        }
        fx.file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        code, out = fx.check()
        self.assertEqual(code, 0, out)
        rows = {row["id"]: row for row in out.get("problems") or []
                if row.get("code") == "state-bloat"}
        for ident in ("resolved-row", "settled-row"):
            self.assertIn(ident, rows, out)
            self.assertIn("state", rows[ident]["command"])
            self.assertIn("retire", rows[ident]["command"])
            self.assertNotIn("No runnable retire command", rows[ident]["detail"])
            ran, removed = execute(rows[ident]["command"])
            self.assertEqual(ran, 0, removed)
        doc = fx.doc()
        self.assertNotIn("resolved-row", doc["state"].get("alerts") or {})
        self.assertNotIn("settled-row", doc["state"].get("decisions") or {})

    def test_state_check_emits_the_run_command_for_the_fixed_shape(self) -> None:
        fx = self.fixture()
        code, out = fx.check("--index", str(fx.index), "--live", str(fx.live))
        self.assertEqual(code, 0, out)
        emitted = self._emitted(out)
        self.assertEqual(set(emitted), {"done-not-retired", "state-bloat"}, out)
        for row in emitted.values():
            self.assertIn("state", row["command"])
            self.assertIn("retire", row["command"])
            self.assertIn(str(fx.index), row["command"])
            self.assertIn(str(fx.live), row["command"])
        ran, removed = execute(emitted["state-bloat"]["command"])
        self.assertEqual(ran, 0, removed)
        entry = removed["value"]["reconciled_dispatch"][0]
        self.assertEqual(entry["route"], ROUTE_KEY)
        self.assertEqual(entry["live"], "stopped")
        self.assertTrue(fx.task_gone())


if __name__ == "__main__":
    unittest.main(verbosity=2)
