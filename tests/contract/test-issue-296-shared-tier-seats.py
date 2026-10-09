#!/usr/bin/env python3
"""Issue #296: one shared tier group plus a tier-specific extra seat.

Re-checked at 06632a44, after #294 and #297. What current main still got wrong:

- The owner policy (1 seat shared by claude-code default/sonnet/fable, plus 1
  default-only seat) could not be written. Two rows for default were
  "one authoritative row per preset". `count` 2 on the shared group grants
  two of every tier, including sonnet and fable. `count` stays that pool.
- `delegator update` also refused fable listed once in the elite group and
  once in expert_task_grants. The ceiling reader already allowed that overlap.
- A shared-occupied refusal did not name the occupying session or
  holder_instance_id.
- The workaround (default count 2 on its own row, sonnet/fable shared count 1)
  still totals 3. On current main that workaround does admit a second default;
  this suite does not treat that admission as a bug.

`extra_seats` on the one grouped row is the tier-specific addition.
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
FUTURE = "2999-01-01T00:00:00Z"
PAST = "2000-01-01T00:00:00Z"
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")
DEFAULT = "claude-code/default"
SONNET = "claude-code/sonnet"
FABLE = "claude-code/fable"
GROUP = [DEFAULT, SONNET, FABLE]
SEAT = ",".join(sorted(GROUP))


def run_dispatch(args: list[str]) -> tuple[int, dict]:
    env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args], capture_output=True, text=True, timeout=60, env=env)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


def policy_grant(extra: dict | None = None, count: int = 1) -> dict:
    row = {"preset_ids": list(GROUP), "count": count, "state": "granted"}
    if extra is not None:
        row["extra_seats"] = extra
    return row


def ceiling_auth(extra: dict | None = None, count: int = 1, *, expert: bool = True,
                 expert_count: int = 1, expires: str = FUTURE) -> dict:
    elite = {"preset_ids": list(GROUP), "count": count, "state": "granted", "expires": expires}
    if extra is not None:
        elite["extra_seats"] = extra
    auth = {
        "dispatch_enabled": True,
        "elite_grants": [elite],
        "expert_task_grants": [],
    }
    if expert:
        auth["expert_task_grants"] = [{
            "preset_id": FABLE, "count": expert_count, "lifetime": "task", "state": "granted",
        }]
    return auth


class SharedTierSeats(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i296-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.repo = self.repo.resolve()
        self.auth = self.repo / "auth.json"
        self.delegator = self.repo / ".kaola" / "delegator-heartbeat.json"
        self.host = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.live = self.repo / "live.json"
        self.availability = self.repo / "availability.json"
        self.availability.write_text(json.dumps({"present": list(GROUP)}), encoding="utf-8")
        self.write_live([])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_live(self, rows: list[dict]) -> None:
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": rows}), encoding="utf-8")

    def write_auth(self, grants: list[dict]) -> None:
        self.auth.write_text(json.dumps({"grants": grants}), encoding="utf-8")

    def write_delegator(self, auth: dict, revision: int = 0) -> None:
        self.delegator.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": revision,
            "updated_at": "2026-10-08T00:00:00+00:00",
            "authorization": auth,
        }), encoding="utf-8")

    def live_row(self, preset: str, session: str, holder: str) -> dict:
        return {
            "preset": preset, "session": session, "platform": "claude-code",
            "repo": str(self.repo), "state": "running", "holder_instance_id": holder,
        }

    def item(self, item_id: str, preset: str) -> dict:
        return {"item_id": item_id, "preset": preset, "session": item_id, "prompt": "review"}

    def execute(self, grants: list[dict], delegator: dict | None, items: list[dict],
                live_rows: list[dict] | None = None) -> dict[str, dict]:
        self.write_auth(grants)
        if delegator is None:
            if self.delegator.exists():
                self.delegator.unlink()
        else:
            self.write_delegator(delegator)
        self.write_live([] if live_rows is None else live_rows)
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(self.repo), "items": items,
        }), encoding="utf-8")
        code, out = run_dispatch([
            "execute", "--plan", str(plan), "--authorization", str(self.auth),
            "--platforms", str(PLATFORMS), "--live", str(self.live), "--dry-run",
        ])
        self.assertEqual(code, 0, out)
        return {row["item_id"]: row for row in out["items"]}

    def seats(self, grants: list[dict], delegator: dict) -> dict:
        self.write_auth(grants)
        self.write_delegator(delegator)
        # Occupancy is unknown, and idle_available stays unset, until a current
        # host heartbeat exists. Its tasks are empty; grants come from --authorization.
        self.host.write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2",
            "revision": 0,
            "host_revision": 1,
            "updated_at": "2026-10-08T00:00:00+00:00",
            "state": {
                "project": {"repo": str(self.repo), "goal": "issue 296"},
                "authorization": {"grants": grants},
                "sideagent": None, "recovery": {}, "unverified": {},
                "tasks": {}, "holds": {}, "alerts": {}, "decisions": {}, "maintenance": {},
            },
        }), encoding="utf-8")
        code, out = run_dispatch([
            "project", "--seats", "--repo", str(self.repo),
            "--authorization", str(self.auth), "--live", str(self.live),
            "--availability", str(self.availability), "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        return out["summary"]

    def delegator_update(self, auth: dict, revision: int = 0) -> tuple[int, dict]:
        return run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "owner-claude-seats", "--expect-revision", str(revision),
            "--set", json.dumps({"authorization": auth}),
        ])

    def assert_occupied(self, row: dict, session: str, holder: str | None, preset: str,
                        limit: str | None = None) -> None:
        self.assertEqual(row["reason"], "shared-occupied", row)
        occupants = row["evidence"]["occupants"]
        self.assertIn(
            {"session": session, "holder_instance_id": holder, "preset": preset}, occupants, row)
        if limit is not None:
            self.assertEqual(row["evidence"]["limit"], limit)

    def test_delegator_update_accepts_one_row_and_refuses_a_second_elite_row(self) -> None:
        extra = {DEFAULT: 1}
        self.write_delegator({"elite_grants": [], "expert_task_grants": [], "dispatch_enabled": True})
        code, out = self.delegator_update(ceiling_auth(extra))
        self.assertEqual(code, 0, out)
        stored = json.loads(self.delegator.read_text())
        elite = stored["authorization"]["elite_grants"]
        self.assertEqual(len(elite), 1)
        self.assertEqual(elite[0]["count"], 1)
        self.assertEqual(elite[0]["extra_seats"], extra)
        self.assertEqual(stored["authorization"]["expert_task_grants"][0]["preset_id"], FABLE)
        code, view = run_dispatch([
            "delegator", "view", "--file", str(self.delegator), "--repo", str(self.repo),
            "--live", str(self.live), "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, view)
        self.assertEqual(view["authorization"]["elite_grants"][0]["extra_seats"], extra)
        self.assertEqual(view["seats"]["authorized_total"], 2)

        before = self.delegator.read_bytes()
        revision = stored["revision"]
        duplicate = ceiling_auth(extra)
        duplicate["elite_grants"].append(
            {"preset_id": DEFAULT, "count": 1, "state": "granted", "expires": FUTURE})
        code, refused = self.delegator_update(duplicate, revision)
        self.assertEqual(code, 2, refused)
        self.assertEqual(self.delegator.read_bytes(), before)
        text = json.dumps(refused)
        self.assertIn("one authoritative row per preset", text)
        self.assertIn(DEFAULT, text)

        third = ceiling_auth(extra)
        third["expert_task_grants"].append(
            {"preset_id": FABLE, "count": 1, "lifetime": "task", "state": "granted"})
        code, refused = self.delegator_update(third, revision)
        self.assertEqual(code, 2, refused)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.assertIn(FABLE, json.dumps(refused))

    def test_host_update_accepts_extra_seats_and_rejects_a_bad_shape(self) -> None:
        code, init = run_dispatch([
            "state", "init", "--file", str(self.host), "--writer", "host", "--source", "owner",
            "--project", json.dumps({"code": "KT", "goal": "claude seats", "repo": str(self.repo)}),
            "--authorization", json.dumps({"grants": [policy_grant({DEFAULT: 1})]}),
        ])
        self.assertEqual(code, 0, init)
        stored = json.loads(self.host.read_text())["state"]["authorization"]["grants"]
        self.assertEqual(stored, [policy_grant({DEFAULT: 1})])
        code, host = run_dispatch(["state", "view", "--file", str(self.host), "--role", "host"])
        self.assertEqual(code, 0, host)
        self.assertIn({"count": 2, "seat": SEAT}, host["capability"]["shared_seats"])

        revision = json.loads(self.host.read_text())["revision"]
        before = self.host.read_bytes()
        bad_shapes = (
            {"grants": [{"id": DEFAULT, "count": 1, "state": "granted", "extra_seats": {DEFAULT: 1}}]},
            {"grants": [policy_grant({"other/preset": 1})]},
            {"grants": [policy_grant({DEFAULT: 0})]},
            {"grants": [policy_grant({DEFAULT: True})]},
            {"grants": [{**policy_grant(), "extra_seats": [DEFAULT]}]},
            {"grants": [policy_grant({DEFAULT: 1}),
                        {"id": DEFAULT, "count": 1, "state": "granted"}]},
        )
        for patch in bad_shapes:
            with self.subTest(patch=patch):
                code, refused = run_dispatch([
                    "state", "update", "--file", str(self.host), "--writer", "host",
                    "--source", "owner", "--section", "authorization",
                    "--expect-revision", str(revision), "--set", json.dumps(patch),
                ])
                self.assertEqual(code, 2, refused)
                self.assertEqual(self.host.read_bytes(), before)

        code, written = run_dispatch([
            "state", "update", "--file", str(self.host), "--writer", "host", "--source", "owner",
            "--section", "authorization", "--expect-revision", str(revision),
            "--set", json.dumps({"grants": [policy_grant({DEFAULT: 1})]}),
        ])
        self.assertEqual(code, 0, written)
        grants = json.loads(self.host.read_text())["state"]["authorization"]["grants"]
        self.assertEqual(grants[0]["count"], 1)
        self.assertEqual(grants[0]["extra_seats"], {DEFAULT: 1})

    def test_seat_total_is_two_and_sonnet_fable_stay_at_one(self) -> None:
        extra = {DEFAULT: 1}
        summary = self.seats([policy_grant(extra)], ceiling_auth(extra))
        self.assertEqual(summary["authorized_total"], 2)
        self.assertEqual(len(summary["groups"]), 1)
        group = summary["groups"][0]
        self.assertEqual(group["authorized_count"], 2)
        self.assertEqual(group["idle_available"], 2)
        counts = {row["id"]: row for row in group["presets"]}
        self.assertEqual(counts[DEFAULT]["count"], 2)
        self.assertEqual(counts[DEFAULT]["class"], "Elite")
        self.assertNotIn("lifetime", counts[DEFAULT])
        self.assertEqual(counts[SONNET]["count"], 1)
        self.assertEqual(counts[FABLE]["count"], 1)
        self.assertEqual(counts[FABLE]["class"], "Expert")
        self.assertEqual(counts[FABLE]["lifetime"], "task")

        narrowed = self.seats([policy_grant(extra)], ceiling_auth(None))
        self.assertEqual(narrowed["authorized_total"], 1)
        self.assertEqual(narrowed["groups"][0]["authorized_count"], 1)

        wider_ceiling = self.seats([policy_grant(None)], ceiling_auth(extra))
        self.assertEqual(wider_ceiling["authorized_total"], 1)

    def test_admission_uses_the_per_runtime_total(self) -> None:
        extra = {DEFAULT: 1}
        grants = [policy_grant(extra)]
        ceiling = ceiling_auth(extra)

        both = self.execute(grants, ceiling, [self.item("d1", DEFAULT), self.item("d2", DEFAULT)])
        self.assertEqual(both["d1"]["reason"], "dry-run")
        self.assertEqual(both["d2"]["reason"], "dry-run")
        self.assertNotIn("lifetime", both["d1"]["evidence"])

        mixed = self.execute(grants, ceiling, [self.item("d1", DEFAULT), self.item("s1", SONNET)])
        self.assertEqual(mixed["d1"]["reason"], "dry-run")
        self.assertEqual(mixed["s1"]["reason"], "dry-run")

        with_fable = self.execute(grants, ceiling, [self.item("d1", DEFAULT), self.item("f1", FABLE)])
        self.assertEqual(with_fable["d1"]["reason"], "dry-run")
        self.assertEqual(with_fable["f1"]["reason"], "dry-run")
        self.assertEqual(with_fable["f1"]["evidence"]["lifetime"], "task")

        sonnet_fable = self.execute(grants, ceiling, [self.item("s1", SONNET), self.item("f1", FABLE)])
        self.assertEqual(sonnet_fable["s1"]["reason"], "dry-run")
        self.assert_occupied(sonnet_fable["f1"], "s1", None, SONNET, "shared-pool")

        two_sonnets = self.execute(grants, ceiling, [self.item("s1", SONNET), self.item("s2", SONNET)])
        self.assertEqual(two_sonnets["s1"]["reason"], "dry-run")
        self.assert_occupied(two_sonnets["s2"], "s1", None, SONNET, "shared-pool")

        two_fables = self.execute(grants, ceiling, [self.item("f1", FABLE), self.item("f2", FABLE)])
        self.assertEqual(two_fables["f1"]["reason"], "dry-run")
        self.assert_occupied(two_fables["f2"], "f1", None, FABLE, "shared-pool")

        third = self.execute(grants, ceiling, [
            self.item("d1", DEFAULT), self.item("d2", DEFAULT), self.item("d3", DEFAULT)])
        self.assertEqual(third["d1"]["reason"], "dry-run")
        self.assertEqual(third["d2"]["reason"], "dry-run")
        self.assert_occupied(third["d3"], "d1", None, DEFAULT, "runtime-total")
        self.assert_occupied(third["d3"], "d2", None, DEFAULT, "runtime-total")

        second = self.execute(
            grants, ceiling, [self.item("d2", DEFAULT)],
            [self.live_row(DEFAULT, "claude-live-default", "holder-default-1")])
        self.assertEqual(second["d2"]["reason"], "dry-run")

        sonnet_while_default = self.execute(
            grants, ceiling, [self.item("s1", SONNET)],
            [self.live_row(DEFAULT, "claude-live-default", "holder-default-1")])
        self.assertEqual(sonnet_while_default["s1"]["reason"], "dry-run")

        fable_while_sonnet = self.execute(
            grants, ceiling, [self.item("f1", FABLE)],
            [self.live_row(SONNET, "claude-live-sonnet", "holder-sonnet-1")])
        self.assert_occupied(fable_while_sonnet["f1"], "claude-live-sonnet", "holder-sonnet-1", SONNET, "shared-pool")

        sonnet_while_two = self.execute(
            grants, ceiling, [self.item("s1", SONNET)],
            [self.live_row(DEFAULT, "claude-live-a", "holder-a"),
             self.live_row(DEFAULT, "claude-live-b", "holder-b")])
        self.assert_occupied(sonnet_while_two["s1"], "claude-live-a", "holder-a", DEFAULT, "runtime-total")
        self.assert_occupied(sonnet_while_two["s1"], "claude-live-b", "holder-b", DEFAULT, "runtime-total")

        host_only = self.execute(
            grants, None, [self.item("d1", DEFAULT), self.item("d2", DEFAULT), self.item("s1", SONNET)])
        self.assertEqual(host_only["d1"]["reason"], "dry-run")
        self.assertEqual(host_only["d2"]["reason"], "dry-run")
        self.assert_occupied(host_only["s1"], "d1", None, DEFAULT, "runtime-total")

    def test_plain_shared_group_names_the_occupant_and_count_two_stays_a_pool(self) -> None:
        plain = self.execute(
            [policy_grant(None)], ceiling_auth(None), [self.item("s1", SONNET)],
            [self.live_row(DEFAULT, "claude-live-default", "holder-default-1")])
        self.assert_occupied(plain["s1"], "claude-live-default", "holder-default-1", DEFAULT)
        self.assertNotIn("limit", plain["s1"]["evidence"])

        pool = self.execute(
            [policy_grant(None, count=2)], ceiling_auth(None, count=2, expert_count=2),
            [self.item("s1", SONNET), self.item("s2", SONNET)])
        self.assertEqual([pool["s1"]["reason"], pool["s2"]["reason"]], ["dry-run", "dry-run"])
        mixed = self.execute(
            [policy_grant(None, count=2)], ceiling_auth(None, count=2, expert_count=2),
            [self.item("s1", SONNET), self.item("f1", FABLE)])
        self.assertEqual([mixed["s1"]["reason"], mixed["f1"]["reason"]], ["dry-run", "dry-run"])
        summary = self.seats([policy_grant(None, count=2)], ceiling_auth(None, count=2, expert_count=2))
        self.assertEqual(summary["authorized_total"], 2)
        counts = {row["id"]: row["count"] for row in summary["groups"][0]["presets"]}
        self.assertEqual(counts, {DEFAULT: 2, SONNET: 2, FABLE: 2})

    def test_workaround_default_two_plus_shared_pair_still_totals_three(self) -> None:
        grants = [
            {"id": DEFAULT, "count": 2, "state": "granted"},
            {"preset_ids": [SONNET, FABLE], "count": 1, "state": "granted"},
        ]
        ceiling = {
            "dispatch_enabled": True,
            "elite_grants": [
                {"preset_id": DEFAULT, "count": 2, "state": "granted", "expires": FUTURE},
                {"preset_ids": [SONNET, FABLE], "count": 1, "state": "granted", "expires": FUTURE},
            ],
            "expert_task_grants": [
                {"preset_id": FABLE, "count": 1, "lifetime": "task", "state": "granted"},
            ],
        }
        summary = self.seats(grants, ceiling)
        self.assertEqual(summary["authorized_total"], 3)

    def test_fable_without_expert_grant_stays_above_ceiling(self) -> None:
        rows = self.execute(
            [policy_grant({DEFAULT: 1})], ceiling_auth({DEFAULT: 1}, expert=False),
            [self.item("d1", DEFAULT), self.item("f1", FABLE)])
        self.assertEqual(rows["d1"]["reason"], "dry-run")
        self.assertEqual(rows["f1"]["reason"], "above-ceiling")

    def test_past_elite_window_blocks_default_not_the_expert_choice(self) -> None:
        rows = self.execute(
            [policy_grant({DEFAULT: 1})], ceiling_auth({DEFAULT: 1}, expires=PAST),
            [self.item("d1", DEFAULT), self.item("f1", FABLE)])
        self.assertEqual(rows["d1"]["reason"], "expired")
        self.assertEqual(rows["f1"]["reason"], "dry-run")
        self.assertEqual(rows["f1"]["evidence"]["lifetime"], "task")


if __name__ == "__main__":
    unittest.main()
