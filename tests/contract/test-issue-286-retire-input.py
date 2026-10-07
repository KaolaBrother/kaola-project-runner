#!/usr/bin/env python3
"""Issue #286: `state retire` fails closed on an unreadable dispatch-index
status and on unidentified index/live input (pilot gaps G5/G6/G9 from #280).

Retire proves a task's dispatched work ended from three inputs: the dispatch
index, each referenced item's `status`, and the live rows. On main each input
could fail open:

* G6 — `open_dispatch` treated any status outside `in-flight`/`unknown` as
  closed, so a row with no `status`, or a renamed status such as ``"inflight"``,
  proved closure. The index mirror in the same command kept the opposite rule:
  only `returned`/`failed`/`not-run` are closed.
* G5 — retire's index read and its mirror checked neither
  `kaola-dispatch-index/1` nor the index `repo`, unlike every other index
  reader, so another project's index proved closure.
* G9 — the live rows were read without checking `kaola-acp-list/1`, and the
  documented `$LIVE` source (`list --repo`) omits stopped seats by default.

Every ``test_regression_`` case here fails on current main and passes with the
fix. The ``test_guard_`` cases pin the already accepted retire paths that must
not change: bare fixtures with no declared identity stay readable, the closed
statuses retire, and the in-flight/unknown messages stay stable. A refused or
failed retire never writes a state byte.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
for name in CALLER_ENV:
    os.environ.pop(name, None)

AUTH = {"grants": [{"id": "codex/default", "state": "granted", "count": 1},
                   {"id": "zcode/default", "state": "granted", "count": 1}]}
CITE = '{"path":"README.md","locator":"README.md"}'
ACCEPTED = {"stage": "done", "goal": "g", "verdict": {"value": "accepted"}}


def run(args: list[str]) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env={k: v for k, v in os.environ.items() if k not in CALLER_ENV})
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


class RetireInput(unittest.TestCase):
    """One accepted task with one dispatched item and one stopped seat."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i286-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host",
                         "--source", "turn-1", "--project", json.dumps({"code": "KT", "goal": "ship"}),
                         "--authorization", json.dumps(AUTH)])
        self.assertEqual(code, 0, out)
        code, out = self.state("update", "--kind", "tasks", "--id", "t1", "--set",
                               json.dumps({**ACCEPTED, "dispatch": ["i1"]}))
        self.assertEqual(code, 0, out)
        self.index = self.repo / "index.json"
        self.live = self.repo / "live.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, action: str, *args: str) -> tuple[int, dict]:
        return run(["state", action, "--file", str(self.file), "--writer", "host",
                    "--source", "evt", *args])

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def state_bytes(self) -> bytes:
        return self.file.read_bytes()

    def live_rows(self, rows: list[dict]) -> Path:
        # The real producer form: `kaola-acp.py list` declares kaola-acp-list/1.
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}),
                             encoding="utf-8")
        return self.live

    def stopped_live(self) -> Path:
        return self.live_rows([{"session": "codex-KT-i1-a", "state": "stopped"}])

    def index_at(self, index: dict) -> Path:
        self.index.write_text(json.dumps(index), encoding="utf-8")
        return self.index

    def bare_index(self, **row_extra) -> Path:
        row = {"item_id": "i1", "session": "codex-KT-i1-a"}
        row.update(row_extra)
        return self.index_at({"items": [row]})

    def ident_index(self, **row_extra) -> Path:
        # The real producer form: execute and collect write schema and repo.
        row = {"item_id": "i1", "session": "codex-KT-i1-a"}
        row.update(row_extra)
        return self.index_at({"schema": "kaola-dispatch-index/1", "repo": str(self.repo),
                              "items": [row]})

    def retire(self, *extra: str) -> tuple[int, dict]:
        return run(["state", "retire", "--file", str(self.file), "--writer", "sideagent",
                    "--source", "s", "--kind", "tasks", "--id", "t1", "--expect-rev", "1",
                    "--evidence", "commit c1", "--cite", CITE, *extra])

    # G6 — one closed-status vocabulary, shared with the index mirror.

    def test_regression_an_absent_status_is_still_a_duty(self) -> None:
        self.ident_index()  # no status key at all
        self.stopped_live()
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("i1", out["detail"], out)
        self.assertIn("is not a known closed value", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "a refused retire writes no state byte")

    def test_regression_an_unrecognized_status_is_still_a_duty(self) -> None:
        self.ident_index(status="inflight")  # a renamed in-flight, known to no vocabulary
        self.stopped_live()
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), out)
        self.assertIn("'inflight'", out["detail"], out)
        self.assertIn("is not a known closed value", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "a refused retire writes no state byte")

    # G5 — the dispatch index is identified before it can prove any closure.

    def test_regression_a_foreign_repo_index_is_refused_unchanged(self) -> None:
        self.index_at({"schema": "kaola-dispatch-index/1", "repo": "/elsewhere", "items": [
            {"item_id": "i1", "status": "returned", "session": "codex-KT-i1-a"}]})
        self.stopped_live()
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("result"), "refused", out)
        self.assertEqual(out.get("reason"), "index-unidentified", out)
        self.assertIn("/elsewhere", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "an unidentified index writes no state byte")

    def test_regression_a_wrong_schema_index_is_refused_unchanged(self) -> None:
        self.index_at({"schema": "other/9", "repo": str(self.repo), "items": [
            {"item_id": "i1", "status": "returned", "session": "codex-KT-i1-a"}]})
        self.stopped_live()
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("reason"), "index-unidentified", out)
        self.assertIn("kaola-dispatch-index/1", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "an unidentified index writes no state byte")

    def test_regression_an_index_with_no_schema_is_refused_unchanged(self) -> None:
        self.index_at({"repo": str(self.repo), "items": [
            {"item_id": "i1", "status": "returned", "session": "codex-KT-i1-a"}]})
        self.stopped_live()
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("result"), "refused", out)
        self.assertEqual(out.get("reason"), "index-unidentified", out)
        self.assertIn("declares no schema", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "an unidentified index writes no state byte")

    def test_regression_an_index_with_no_repo_is_refused_unchanged(self) -> None:
        self.index_at({"schema": "kaola-dispatch-index/1", "items": [
            {"item_id": "i1", "status": "returned", "session": "codex-KT-i1-a"}]})
        self.stopped_live()
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("result"), "refused", out)
        self.assertEqual(out.get("reason"), "index-unidentified", out)
        self.assertIn("declares no repo", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "an unidentified index writes no state byte")

    def test_regression_the_mirror_leaves_a_foreign_index_unchanged(self) -> None:
        """The mirror runs after the state write lands (I12): a foreign index
        is reported in ``index_mirror.error`` and keeps its bytes, instead of
        receiving acceptance written by retirement."""
        code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                         "--source", "evt", "--kind", "tasks", "--id", "t2", "--set",
                         json.dumps(ACCEPTED)])
        self.assertEqual(code, 0, out)
        foreign = self.repo / "foreign-index.json"
        foreign.write_text(json.dumps({"schema": "other/9", "repo": "/elsewhere", "items": [
            {"item_id": "x1", "task_id": "t2", "status": "returned", "acceptance": "pending"}]}),
            encoding="utf-8")
        before = foreign.read_bytes()
        code, out = run(["state", "retire", "--file", str(self.file), "--writer", "sideagent",
                         "--source", "s", "--kind", "tasks", "--id", "t2", "--expect-rev", "1",
                         "--evidence", "commit c2", "--cite", CITE, "--index", str(foreign)])
        self.assertEqual(code, 0, out)  # the state write stands; the mirror reports
        mirror = out.get("index_mirror") or {}
        self.assertIn("index identity differs", mirror.get("error", ""), out)
        self.assertEqual(foreign.read_bytes(), before, "the mirror writes no foreign byte")
        self.assertNotIn("t2", self.doc()["state"]["tasks"])

    # G9 — the live input is identified (kaola-acp-list/1).

    def test_regression_an_unidentified_live_input_is_refused_unchanged(self) -> None:
        self.ident_index(status="returned")
        # A wrong file with usable rows: valid JSON, a declared schema that is
        # not kaola-acp-list/1, and rows main accepts as a stop.
        self.live.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "rows": [
            {"session": "codex-KT-i1-a", "state": "stopped"}]}), encoding="utf-8")
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("result"), "refused", out)
        self.assertEqual(out.get("reason"), "live-unidentified", out)
        self.assertIn("kaola-acp-list/1", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "an unidentified live input writes no state byte")

    def test_regression_a_live_input_with_no_schema_is_refused_unchanged(self) -> None:
        self.ident_index(status="returned")
        self.live.write_text(json.dumps({"rows": [  # bare rows: no schema at all
            {"session": "codex-KT-i1-a", "state": "stopped"}]}), encoding="utf-8")
        before = self.state_bytes()
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("result"), "refused", out)
        self.assertEqual(out.get("reason"), "live-unidentified", out)
        self.assertIn("declare no schema", out["detail"], out)
        self.assertEqual(self.state_bytes(), before, "an unidentified live input writes no state byte")

    def test_regression_check_identifies_the_live_input_too(self) -> None:
        """``live_rows_of`` is the one reader retire, check and migrate share:
        the identification holds wherever live rows are read."""
        self.live.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/2", "rows": [
            {"session": "codex-KT-i1-a", "state": "stopped"}]}), encoding="utf-8")
        code, out = run(["state", "check", "--file", str(self.file), "--live", str(self.live)])
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("reason"), "live-unidentified", out)

    # Guards — the already accepted retire paths stay unchanged.

    def test_guard_a_declared_index_and_closed_statuses_still_retire(self) -> None:
        for n, status in enumerate(("returned", "failed", "not-run")):
            ident, item = f"t2{n}", f"i2{n}"
            code, out = run(["state", "update", "--file", str(self.file), "--writer", "host",
                             "--source", "evt", "--kind", "tasks", "--id", ident, "--set",
                             json.dumps({**ACCEPTED, "dispatch": [item]})])
            self.assertEqual(code, 0, out)
            rev = str(self.doc()["state"]["tasks"][ident]["rev"])
            self.index.write_text(json.dumps({  # the form execute and collect write
                "schema": "kaola-dispatch-index/1", "repo": str(self.repo),
                "items": [{"item_id": item, "status": status, "session": f"codex-KT-{item}-a"}]}),
                encoding="utf-8")
            self.live_rows([{"session": f"codex-KT-{item}-a", "state": "stopped"}])
            code, out = run(["state", "retire", "--file", str(self.file), "--writer", "sideagent",
                             "--source", "s", "--kind", "tasks", "--id", ident, "--expect-rev", rev,
                             "--evidence", "commit c", "--cite", CITE,
                             "--index", str(self.index), "--live", str(self.live)])
            self.assertEqual(code, 0, (status, out))
            self.assertNotIn(ident, self.doc()["state"]["tasks"], status)

    def test_guard_in_flight_and_unknown_messages_are_stable(self) -> None:
        self.stopped_live()
        for status, fragment in (("in-flight", "i1 is in-flight"), ("unknown", "i1 is unknown")):
            self.ident_index(status=status)
            code, out = self.retire("--index", str(self.index), "--live", str(self.live))
            self.assertEqual((code, out.get("reason")), (2, "retire-unmet"), (status, out))
            self.assertIn(fragment, out["detail"], (status, out))

    def test_guard_a_declared_live_list_still_retires(self) -> None:
        """The real producer form: `kaola-acp.py list` output declares
        kaola-acp-list/1, so retire keeps reading it."""
        self.ident_index(status="returned")
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": [
            {"session": "codex-KT-i1-a", "state": "stopped"}]}), encoding="utf-8")
        code, out = self.retire("--index", str(self.index), "--live", str(self.live))
        self.assertEqual(code, 0, out)
        self.assertNotIn("t1", self.doc()["state"]["tasks"])


if __name__ == "__main__":
    unittest.main()
