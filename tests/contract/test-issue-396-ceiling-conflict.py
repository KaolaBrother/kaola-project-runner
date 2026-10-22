#!/usr/bin/env python3
"""Issue #396: an Expert special_requirements conflict is not swallowed.

A Host flat grant and the Delegator ceiling can both state
``special_requirements`` for the same preset. When the literal values
disagree, ``apply_ceiling_to_grants()`` records ``ceiling-incomplete`` in
``ceiling["problems"]``. Elite admission reads that map and withholds the
preset. The Expert fast path returned None before reading it, so the same
conflict admitted an Expert seat, and ``execute`` used the same path.

These cases pin the symmetry at the CLI boundary: the conflict is reported for
Expert (project/withheld, seats/unavailable, execute/not-run), the conflict
free Expert path still admits, and the Elite behavior stays unchanged.
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
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"
PLATFORMS = REPO / "platforms"
PYTHON = sys.executable
EXPERT = "claude-code/fable"
ELITE = "claude-code/opus-xhigh"
HOST_TEXT = {"task_scope": "Host authorization owner text"}
DELEGATOR_TEXT = {"task_scope": "Delegator ceiling owner text"}
_NO_GRANT = object()


def run_dispatch(args: list[str]) -> tuple[int, dict]:
    # Scratch fixtures own every KAOLA_* fact; do not inherit the caller's.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("KAOLA_")}
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args], capture_output=True, text=True,
        timeout=60, env=env)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


class CeilingConflict(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i396-")
        root = Path(self.tmp.name)
        self.repo = (root / "consumer").resolve()
        (self.repo / ".kaola").mkdir(parents=True)
        self.auth = root / "auth.json"
        self.live = root / "live.json"
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": []}),
                             encoding="utf-8")
        self.delegator = self.repo / ".kaola" / "delegator-heartbeat.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_ceiling(self, *, elite: dict | None | object = _NO_GRANT,
                      expert: dict | None | object = _NO_GRANT) -> None:
        """Write the Delegator row; None means a grant with no special_requirements."""
        authorization = {"elite_grants": [], "expert_task_grants": [],
                         "worker_grants": []}
        if elite is not _NO_GRANT:
            grant = {"preset_id": ELITE, "count": 1, "state": "granted"}
            if elite is not None:
                grant["special_requirements"] = elite
            authorization["elite_grants"].append(grant)
        if expert is not _NO_GRANT:
            grant = {"preset_id": EXPERT, "count": 1, "state": "granted",
                     "lifetime": "standing"}
            if expert is not None:
                grant["special_requirements"] = expert
            authorization["expert_task_grants"].append(grant)
        self.delegator.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": 1,
            "updated_at": "2026-10-22T00:00:00+00:00",
            "authorization": authorization,
        }), encoding="utf-8")

    def write_auth(self, grants: list[dict]) -> None:
        self.auth.write_text(json.dumps({"grants": grants}), encoding="utf-8")

    def host_grant(self, preset: str, special: dict | None) -> dict:
        grant = {"id": preset, "count": 1, "state": "granted"}
        if preset == EXPERT:
            grant["lifetime"] = "standing"
        if special is not None:
            grant["special_requirements"] = special
        return grant

    def project(self, *extra: str) -> tuple[int, dict]:
        return run_dispatch([
            "project", *extra, "--repo", str(self.repo),
            "--authorization", str(self.auth), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])

    def execute(self, preset: str) -> tuple[int, dict]:
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research",
            "repo": str(self.repo),
            "items": [{"item_id": "seat-1", "preset": preset,
                       "session": "seat-1", "prompt": "review"}],
        }), encoding="utf-8")
        return run_dispatch([
            "execute", "--plan", str(plan), "--authorization", str(self.auth),
            "--live", str(self.live), "--platforms", str(PLATFORMS), "--dry-run",
        ])

    def withheld_reasons(self, out: dict) -> dict[str, str]:
        return {row["id"]: row["reason"] for row in out.get("withheld") or []}

    def seat_row(self, out: dict, preset: str) -> dict:
        for group in out.get("summary", {}).get("groups") or []:
            for row in group.get("presets") or []:
                if row["id"] == preset:
                    return group
        raise AssertionError(f"{preset} not listed in {out.get('summary')}")

    def unavailable_reasons(self, group: dict) -> dict[str, str]:
        return {row["id"]: row["reason"] for row in group.get("unavailable") or []}

    def test_expert_conflict_is_withheld_like_elite(self) -> None:
        # Elite control: already reported before the fix, must stay reported.
        self.write_ceiling(elite=DELEGATOR_TEXT)
        self.write_auth([self.host_grant(ELITE, HOST_TEXT)])
        code, elite = self.project()
        self.assertEqual(code, 0, elite)
        self.assertEqual([row["id"] for row in elite.get("candidates") or []], [])
        self.assertEqual(self.withheld_reasons(elite)[ELITE], "ceiling-incomplete")

        # Expert: the same conflict must be reported, never admitted.
        self.write_ceiling(expert=DELEGATOR_TEXT)
        self.write_auth([self.host_grant(EXPERT, HOST_TEXT)])
        code, expert = self.project()
        self.assertEqual(code, 0, expert)
        self.assertEqual([row["id"] for row in expert.get("candidates") or []], [])
        self.assertEqual(self.withheld_reasons(expert)[EXPERT], "ceiling-incomplete")

    def test_expert_conflict_makes_the_seat_unavailable(self) -> None:
        self.write_ceiling(expert=DELEGATOR_TEXT)
        self.write_auth([self.host_grant(EXPERT, HOST_TEXT)])
        code, out = self.project("--seats")
        self.assertEqual(code, 0, out)
        group = self.seat_row(out, EXPERT)
        self.assertEqual(self.unavailable_reasons(group)[EXPERT], "ceiling-incomplete")
        self.assertEqual(group.get("idle_available"), 0)

    def test_execute_blocks_expert_conflict_with_both_sides(self) -> None:
        self.write_ceiling(expert=DELEGATOR_TEXT)
        self.write_auth([self.host_grant(EXPERT, HOST_TEXT)])
        code, out = self.execute(EXPERT)
        self.assertEqual(code, 0, out)
        row = out["items"][0]
        self.assertEqual(row["status"], "not-run")
        self.assertEqual(row["reason"], "ceiling-incomplete")
        self.assertEqual(row["evidence"]["special_requirements"],
                         {"host": HOST_TEXT, "delegator": DELEGATOR_TEXT})
        self.assertNotIn("argv", row)

    def test_execute_elite_conflict_is_unchanged(self) -> None:
        self.write_ceiling(elite=DELEGATOR_TEXT)
        self.write_auth([self.host_grant(ELITE, HOST_TEXT)])
        code, out = self.execute(ELITE)
        self.assertEqual(code, 0, out)
        row = out["items"][0]
        self.assertEqual(row["status"], "not-run")
        self.assertEqual(row["reason"], "ceiling-incomplete")
        self.assertEqual(row["evidence"]["special_requirements"],
                         {"host": HOST_TEXT, "delegator": DELEGATOR_TEXT})
        self.assertNotIn("argv", row)

    def test_expert_without_conflict_is_admitted(self) -> None:
        # Aligned literal text and no Delegator special at all are both clean.
        for name, ceiling_special, host_special in (
            ("aligned", HOST_TEXT, HOST_TEXT),
            ("absent", None, HOST_TEXT),
            ("no-special", DELEGATOR_TEXT, None),
        ):
            with self.subTest(name=name):
                self.write_ceiling(expert=ceiling_special)
                self.write_auth([self.host_grant(EXPERT, host_special)])
                code, out = self.project()
                self.assertEqual(code, 0, out)
                self.assertEqual([row["id"] for row in out.get("candidates") or []],
                                 [EXPERT])
                self.assertNotIn(EXPERT, self.withheld_reasons(out))

                code, run = self.execute(EXPERT)
                self.assertEqual(code, 0, run)
                row = run["items"][0]
                self.assertEqual(row["reason"], "dry-run")
                self.assertNotIn("ceiling-incomplete",
                                 json.dumps(row.get("evidence") or {}))


if __name__ == "__main__":
    unittest.main()
