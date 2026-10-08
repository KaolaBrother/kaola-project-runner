#!/usr/bin/env python3
"""Issue #294: Expert grants and Elite time windows at dispatch admission.

A shared seat group has one count. An Expert choice in that group still needs
its own task or standing grant. Elite grants are a time window ending at
expires. These cases use the dispatch CLI and do not write a seat view.
"""

from __future__ import annotations

import importlib.util
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
FUTURE = "2999-01-01T00:00:00Z"
PAST = "2000-01-01T00:00:00Z"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")


def run_dispatch(args: list[str]) -> tuple[int, dict]:
    env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args], capture_output=True, text=True, timeout=60, env=env)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


def load_dispatch():
    spec = importlib.util.spec_from_file_location("kpr_i294_dispatch", DISPATCH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExpertCeiling(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dispatch = load_dispatch()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i294-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.auth = self.repo / "auth.json"
        self.delegator = self.repo / ".kaola" / "delegator-heartbeat.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def item(self, item_id: str, preset: str) -> dict:
        return {"item_id": item_id, "preset": preset, "session": item_id, "prompt": "review"}

    def live(self, preset: str, session: str) -> dict:
        return {
            "preset": preset, "session": session, "platform": preset.split("/", 1)[0],
            "repo": str(self.repo.resolve()), "state": "running",
        }

    def write_auth(self, grants: list[dict]) -> None:
        self.auth.write_text(json.dumps({"grants": grants}), encoding="utf-8")

    def write_delegator(self, auth: dict) -> None:
        self.delegator.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "authorization": auth,
        }), encoding="utf-8")

    def ceiling(self) -> dict:
        ceiling, error = self.dispatch.delegator_ceiling(str(self.repo.resolve()), [])
        self.assertIsNone(error, error)
        self.assertIsNotNone(ceiling)
        return ceiling

    def execute(self, grants: list[dict], delegator: dict, items: list[dict],
                live_rows: list | None = None) -> tuple[dict, dict]:
        self.write_auth(grants)
        self.write_delegator(delegator)
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(self.repo.resolve()), "items": items,
        }), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [] if live_rows is None else live_rows}), encoding="utf-8")
        code, out = run_dispatch([
            "execute", "--plan", str(plan), "--authorization", str(self.auth),
            "--platforms", str(PLATFORMS), "--live", str(live), "--dry-run",
        ])
        self.assertEqual(code, 0, out)
        self.assertNotIn(
            "delegator-field-invalid",
            [row.get("code") for row in out.get("observations") or []],
        )
        return {row["item_id"]: row for row in out["items"]}, out

    def test_expert_grant_admits_and_view_flag_stays_above_ceiling(self) -> None:
        grants = [{"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"}]
        delegator = {
            "elite_grants": [],
            "expert_task_grants": [
                {"preset_id": "codex/astra", "count": 1, "lifetime": "standing", "expires": FUTURE},
            ],
        }
        rows, _ = self.execute(grants, delegator, [self.item("astra-stand", "codex/astra")])
        self.assertEqual(rows["astra-stand"]["status"], "not-run")
        self.assertEqual(rows["astra-stand"]["reason"], "dry-run")
        self.assertEqual(rows["astra-stand"]["evidence"]["lifetime"], "standing")

        ceiling = self.ceiling()
        self.assertIn("codex/astra", ceiling["expert_ids"])
        self.assertNotIn("codex/astra", ceiling["elite_ids"])
        self.assertIsNone(self.dispatch.ceiling_block(ceiling, "codex/astra", "Expert", expert_grants=True))
        # Seat summary keeps the default flag and still omits an expert-only preset.
        self.assertEqual(self.dispatch.ceiling_block(ceiling, "codex/astra", "Expert"), "above-ceiling")
        self.assertEqual(self.dispatch.ceiling_block(ceiling, "codex/astra", "Elite"), "above-ceiling")

        self.write_auth(grants)
        code, project = run_dispatch([
            "project", "--authorization", str(self.auth), "--platforms", str(PLATFORMS),
            "--repo", str(self.repo.resolve()),
        ])
        self.assertEqual(code, 0, project)
        self.assertIn("codex/astra", [row["id"] for row in project["candidates"]])
        self.assertNotIn("codex/astra", [row["id"] for row in project["withheld"]])

    def test_omitted_expert_lifetime_defaults_to_task(self) -> None:
        rows, _ = self.execute(
            [{"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"}],
            {"elite_grants": [], "expert_task_grants": [{"preset_id": "codex/astra", "count": 1}]},
            [self.item("astra-task", "codex/astra")],
        )
        self.assertEqual(rows["astra-task"]["reason"], "dry-run")
        self.assertEqual(rows["astra-task"]["evidence"]["lifetime"], "task")

    def test_expert_refusals_are_not_above_ceiling(self) -> None:
        host = [{"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"}]
        cases = (
            ("expired", {"expires": PAST, "lifetime": "standing"}, "expired"),
            ("prose", {"lifetime": "forever"}, "lifetime-unreadable"),
            ("unreadable", {"lifetime": "task", "expires": "next Friday"}, "expiry-unreadable"),
        )
        for name, fields, reason in cases:
            with self.subTest(name=name):
                rows, _ = self.execute(
                    host,
                    {"elite_grants": [], "expert_task_grants": [
                        {"preset_id": "codex/astra", "count": 1, **fields},
                    ]},
                    [self.item("astra-no", "codex/astra")],
                )
                self.assertEqual(rows["astra-no"]["reason"], reason)
                self.assertNotEqual(rows["astra-no"]["reason"], "above-ceiling")
                self.assertNotIn("argv", rows["astra-no"])

    def test_shared_group_one_count_and_separate_expert_clock(self) -> None:
        host = [
            {"id": "codex/default", "state": "granted", "count": 4},
            {"id": "codex/astra", "state": "granted", "count": 4, "lifetime": "standing"},
        ]
        group = {
            "preset_ids": ["codex/default", "codex/astra"],
            "count": 1,
            "expires": FUTURE,
        }
        granted = {
            "elite_grants": [group],
            "expert_task_grants": [{"preset_id": "codex/astra", "count": 1, "lifetime": "task"}],
        }
        both, _ = self.execute(host, granted, [
            self.item("elite-a", "codex/default"),
            self.item("expert-b", "codex/astra"),
        ])
        self.assertEqual(both["elite-a"]["reason"], "dry-run")
        self.assertNotIn("lifetime", both["elite-a"]["evidence"])
        self.assertEqual(both["expert-b"]["reason"], "shared-occupied")

        swapped, _ = self.execute(host, granted, [
            self.item("expert-a", "codex/astra"),
            self.item("elite-b", "codex/default"),
        ])
        self.assertEqual(swapped["expert-a"]["reason"], "dry-run")
        self.assertEqual(swapped["expert-a"]["evidence"]["lifetime"], "task")
        self.assertEqual(swapped["elite-b"]["reason"], "shared-occupied")

        occupied_elite, _ = self.execute(
            host, granted, [self.item("expert-live", "codex/astra")],
            [self.live("codex/default", "codex-live-elite")],
        )
        self.assertEqual(occupied_elite["expert-live"]["reason"], "shared-occupied")
        occupied_expert, _ = self.execute(
            host, granted, [self.item("elite-live", "codex/default")],
            [self.live("codex/astra", "codex-live-expert")],
        )
        self.assertEqual(occupied_expert["elite-live"]["reason"], "shared-occupied")

        missing, _ = self.execute(
            host,
            {"elite_grants": [group], "expert_task_grants": []},
            [self.item("elite-open", "codex/default"), self.item("expert-open", "codex/astra")],
        )
        self.assertEqual(missing["elite-open"]["reason"], "dry-run")
        self.assertEqual(missing["expert-open"]["reason"], "above-ceiling")

        prose, _ = self.execute(
            host,
            {"elite_grants": [{
                "preset_ids": ["codex/default", "codex/astra"],
                "count": 1,
                "lifetime": "forever",
            }]},
            [self.item("elite-prose", "codex/default"), self.item("expert-prose", "codex/astra")],
        )
        self.assertEqual(prose["elite-prose"]["reason"], "dry-run")
        self.assertNotEqual(prose["elite-prose"]["reason"], "ceiling-incomplete")
        self.assertEqual(prose["expert-prose"]["reason"], "lifetime-unreadable")
        self.assertEqual(prose["expert-prose"]["evidence"]["lifetime"], "forever")

        expired, _ = self.execute(
            host,
            {"elite_grants": [group], "expert_task_grants": [{
                "preset_id": "codex/astra", "count": 1, "lifetime": "standing", "expires": PAST,
            }]},
            [self.item("elite-clock", "codex/default"), self.item("expert-clock", "codex/astra")],
        )
        self.assertEqual(expired["elite-clock"]["reason"], "dry-run")
        self.assertEqual(expired["expert-clock"]["reason"], "expired")
        self.assertEqual(expired["expert-clock"]["evidence"]["expires"], PAST)

    def test_elite_window_and_fable_lifetime(self) -> None:
        host = [
            {"id": "codex/default", "state": "granted", "count": 1, "lifetime": "standing"},
            {"id": "claude-code/default", "state": "granted", "count": 1},
            {"id": "grok/default", "state": "granted", "count": 1},
            {"id": "claude-code/fable", "state": "granted", "count": 1, "lifetime": "standing"},
        ]
        opened, _ = self.execute(host, {"elite_grants": [
            {"preset_id": "codex/default", "count": 1, "lifetime": "task", "expires": FUTURE},
            {"preset_id": "claude-code/default", "count": 1, "expires": PAST},
            {"preset_id": "grok/default", "count": 1, "expires": "next Friday"},
            {"preset_id": "claude-code/fable", "count": 1, "lifetime": "window", "expires": FUTURE},
        ]}, [
            self.item("elite-window", "codex/default"),
            self.item("elite-past", "claude-code/default"),
            self.item("elite-bad", "grok/default"),
            self.item("fable-window", "claude-code/fable"),
        ])
        self.assertEqual(opened["elite-window"]["reason"], "dry-run")
        self.assertNotIn("lifetime", opened["elite-window"]["evidence"])
        self.assertEqual(opened["elite-past"]["reason"], "expired")
        self.assertNotEqual(opened["elite-past"]["reason"], "ceiling-incomplete")
        self.assertEqual(opened["elite-bad"]["reason"], "expiry-unreadable")
        self.assertEqual(opened["fable-window"]["reason"], "dry-run")
        self.assertNotEqual(opened["fable-window"]["reason"], "ceiling-incomplete")

        incomplete, _ = self.execute(
            host,
            {"elite_grants": [
                {"preset_id": "claude-code/fable", "count": 1, "lifetime": "window"},
            ]},
            [self.item("fable-prose", "claude-code/fable")],
        )
        self.assertEqual(incomplete["fable-prose"]["reason"], "ceiling-incomplete")
        self.assertEqual(incomplete["fable-prose"]["evidence"]["lifetime"], "window")
        self.assertEqual(incomplete["fable-prose"]["evidence"]["presets"], ["claude-code/fable"])

        ended, _ = self.execute(
            host,
            {"elite_grants": [
                {"preset_id": "claude-code/fable", "count": 1, "lifetime": "window", "expires": PAST},
            ]},
            [self.item("fable-past", "claude-code/fable")],
        )
        self.assertEqual(ended["fable-past"]["reason"], "expired")
        self.assertNotEqual(ended["fable-past"]["reason"], "ceiling-incomplete")
        self.assertEqual(ended["fable-past"]["evidence"]["expires"], PAST)

        grouped, _ = self.execute(
            [
                {"id": "claude-code/default", "state": "granted", "count": 2},
                {"id": "claude-code/fable", "state": "granted", "count": 2, "lifetime": "standing"},
            ],
            {
                "elite_grants": [{
                    "preset_ids": ["claude-code/default", "claude-code/fable"],
                    "count": 2,
                    "lifetime": "window",
                    "expires": FUTURE,
                }],
                "expert_task_grants": [
                    {"preset_id": "claude-code/fable", "count": 1, "lifetime": "task"},
                ],
            },
            [self.item("claude-seat", "claude-code/default"), self.item("fable-seat", "claude-code/fable")],
        )
        self.assertEqual(grouped["claude-seat"]["reason"], "dry-run")
        self.assertNotEqual(grouped["claude-seat"]["reason"], "ceiling-incomplete")
        self.assertEqual(grouped["fable-seat"]["reason"], "dry-run")
        self.assertEqual(grouped["fable-seat"]["evidence"]["lifetime"], "task")


if __name__ == "__main__":
    unittest.main()
