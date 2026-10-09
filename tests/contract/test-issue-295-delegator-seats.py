#!/usr/bin/env python3
"""Issue #295: the Delegator seat summary reads the admission ceiling.

`state view --role delegator`, `delegator view`, and `project --seats` share
one seat summary. It lists Elite and Expert grants from the Delegator
ceiling, a shared group once, a Delegator-granted preset the Host grants
omit as host-grant-missing, and admissible Worker presets in worker_pool.
Issue #297: a Worker-class preset with a counted owner grant is a seat; the
uncounted default Worker pool is not.
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
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")

EXPECTED_IDS = {"claude-code/default", "codex/default", "cursor-cli/default",
                "devin/fable", "claude-code/fable", "codex/astra"}


def run_dispatch(args: list[str]) -> tuple[int, dict]:
    env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args], capture_output=True, text=True, timeout=60, env=env)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


def delegator_auth(expert_rows: list[dict] | None = None) -> dict:
    return {
        "dispatch_enabled": True,
        "elite_grants": [
            {"preset_id": "claude-code/default", "count": 1, "state": "granted"},
            {"preset_id": "codex/default", "count": 1, "state": "granted"},
            {"preset_ids": ["cursor-cli/default", "devin/fable"], "count": 2,
             "state": "granted"},
        ],
        "expert_task_grants": expert_rows if expert_rows is not None else [
            {"preset_id": "devin/fable", "count": 1, "state": "granted",
             "lifetime": "task"},
            {"preset_id": "claude-code/fable", "count": 1, "state": "granted",
             "lifetime": "task", "expires": FUTURE},
            {"preset_id": "codex/astra", "count": 1, "state": "granted",
             "lifetime": "standing"},
        ],
        "worker_pool": ["devin/default"],
    }


def host_grants(drop: set[str] | None = None) -> list[dict]:
    grants = [
        {"id": "claude-code/default", "state": "granted", "count": 1},
        {"id": "codex/default", "state": "granted", "count": 1},
        {"preset_ids": ["cursor-cli/default", "devin/fable"], "state": "granted",
         "count": 2},
        {"id": "claude-code/fable", "state": "granted", "count": 1,
         "lifetime": "task", "expires": FUTURE},
        {"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"},
        {"id": "devin/default", "state": "granted", "count": 1},
    ]
    drop = drop or set()
    return [grant for grant in grants
            if grant.get("id") not in drop
            and not drop.intersection(grant.get("preset_ids") or [])]


def host_state(repo: Path, grants: list[dict]) -> dict:
    return {
        "schema": "kaola-heartbeat-prompt/2",
        "revision": 0,
        "host_revision": 1,
        "updated_at": "2026-10-08T00:00:00+00:00",
        "state": {
            "project": {"repo": str(repo), "goal": "issue 295 seat view fixture"},
            "authorization": {"grants": grants},
            "sideagent": None,
            "recovery": {},
            "unverified": {},
            "tasks": {},
            "holds": {},
            "alerts": {},
            "decisions": {},
            "maintenance": {},
        },
    }


def group_index(seats: dict) -> dict[str, dict]:
    return {group["group"]: group for group in seats.get("groups") or []}


def listed_ids(seats: dict) -> set[str]:
    return {row["id"] for group in seats.get("groups") or [] for row in group["presets"]}


class DelegatorSeats(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i295-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.repo = self.repo.resolve()
        self.live = Path(self.tmp.name) / "live.json"
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": []}),
                             encoding="utf-8")
        self.host_file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.delegator_file = self.repo / ".kaola" / "delegator-heartbeat.json"
        self.write_host(host_grants())
        self.write_delegator(delegator_auth())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_host(self, grants: list[dict]) -> None:
        self.host_file.write_text(json.dumps(host_state(self.repo, grants)),
                                  encoding="utf-8")

    def write_delegator(self, auth: dict) -> None:
        self.delegator_file.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": 1,
            "updated_at": "2026-10-08T00:00:00+00:00",
            "authorization": auth,
        }), encoding="utf-8")

    def assert_base_seats(self, seats: dict) -> None:
        self.assertEqual(listed_ids(seats), EXPECTED_IDS | {"devin/default"})
        groups = group_index(seats)
        pair = groups["grant:cursor-cli/default,devin/fable"]
        self.assertEqual(pair["authorized_count"], 2)
        self.assertEqual(sorted(row["id"] for row in pair["presets"]),
                         ["cursor-cli/default", "devin/fable"])
        self.assertEqual(seats["authorized_total"], 7)
        self.assertEqual(seats["worker_pool"], [])
        self.assertEqual(seats["expert_authorization"], "present")
        worker = groups["devin/default"]
        self.assertEqual(worker["authorized_count"], 1)
        self.assertEqual(worker["presets"],
                         [{"id": "devin/default", "class": "Worker", "count": 1,
                           "default_model": "swe-2-max", "default_effort": ""}])
        astra = next(row for group in seats["groups"] for row in group["presets"]
                     if row["id"] == "codex/astra")
        self.assertEqual(astra["lifetime"], "standing")

    def test_state_view_delegator_lists_expert_grants(self) -> None:
        code, out = run_dispatch([
            "state", "view", "--role", "delegator", "--file", str(self.host_file),
            "--repo", str(self.repo), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        self.assert_base_seats(out["seats"])

    def test_project_seats_summary_matches(self) -> None:
        code, out = run_dispatch([
            "project", "--seats", "--repo", str(self.repo),
            "--authorization", str(self.host_file), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        summary = out["summary"]
        self.assertEqual(summary["authorized_total"], 7)
        self.assertEqual(summary["worker_pool"], [])
        self.assertEqual(
            sorted((group["group"], group["authorized_count"],
                    tuple(sorted(row["id"] for row in group["presets"])))
                   for group in summary["groups"]),
            sorted((group["group"], group["authorized_count"],
                    tuple(sorted(row["id"] for row in group["presets"])))
                   for group in self.state_view_seats()["groups"]),
        )

    def state_view_seats(self) -> dict:
        code, out = run_dispatch([
            "state", "view", "--role", "delegator", "--file", str(self.host_file),
            "--repo", str(self.repo), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        return out["seats"]

    def test_delegator_view_host_and_fallback(self) -> None:
        args = ["delegator", "view", "--file", str(self.delegator_file),
                "--repo", str(self.repo), "--live", str(self.live),
                "--platforms", str(PLATFORMS)]
        code, out = run_dispatch(args)
        self.assertEqual(code, 0, out)
        self.assert_base_seats(out["seats"])

        self.host_file.unlink()
        code, out = run_dispatch(args)
        self.assertEqual(code, 0, out)
        seats = out["seats"]
        self.assertNotIn("duplicate grant",
                         " ".join(seats.get("unknown_reasons") or []))
        self.assertEqual(listed_ids(seats), EXPECTED_IDS)
        groups = group_index(seats)
        self.assertEqual(groups["grant:cursor-cli/default,devin/fable"]["authorized_count"], 2)
        self.assertEqual(seats["authorized_total"], 6)
        self.assertEqual(seats["worker_pool"], ["devin/default"])

    def test_delegator_grant_host_omits_is_host_grant_missing(self) -> None:
        self.write_host(host_grants(drop={"codex/astra"}))
        code, out = run_dispatch([
            "state", "view", "--role", "delegator", "--file", str(self.host_file),
            "--repo", str(self.repo), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        seats = out["seats"]
        groups = group_index(seats)
        self.assertIn("codex/astra", groups)
        self.assertEqual(groups["codex/astra"]["authorized_count"], 1)
        self.assertEqual(groups["codex/astra"]["unavailable"],
                         [{"id": "codex/astra", "reason": "host-grant-missing"}])
        self.assertEqual(groups["codex/astra"]["idle_available"], 0)
        self.assertEqual(seats["authorized_total"], 7)

        code, project = run_dispatch([
            "project", "--seats", "--repo", str(self.repo),
            "--authorization", str(self.host_file), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, project)
        self.assertEqual(project["summary"]["authorized_total"], 7)
        self.assertEqual(group_index(project["summary"])["codex/astra"]["unavailable"],
                         [{"id": "codex/astra", "reason": "host-grant-missing"}])

    def test_uncounted_worker_host_grant_stays_pool(self) -> None:
        grants = [dict(grant) for grant in host_grants()]
        for grant in grants:
            if grant.get("id") == "devin/default":
                grant.pop("count", None)
        self.write_host(grants)
        seats = self.state_view_seats()
        self.assertNotIn("devin/default", listed_ids(seats))
        self.assertEqual(seats["worker_pool"], ["devin/default"])
        self.assertEqual(seats["authorized_total"], 6)

    def test_excluded_worker_seat_shows_unavailable(self) -> None:
        auth = delegator_auth()
        auth["exclusions"] = ["devin/default"]
        self.write_delegator(auth)
        seats = self.state_view_seats()
        worker = group_index(seats)["devin/default"]
        self.assertEqual(worker["authorized_count"], 1)
        self.assertEqual(worker["unavailable"],
                         [{"id": "devin/default", "reason": "excluded"}])
        self.assertEqual(worker["idle_available"], 0)
        self.assertEqual(seats["authorized_total"], 7)

    def test_worker_grant_above_empty_ceiling_pool_is_omitted(self) -> None:
        auth = delegator_auth()
        auth["worker_pool"] = []
        self.write_delegator(auth)
        seats = self.state_view_seats()
        self.assertNotIn("devin/default", listed_ids(seats))
        self.assertEqual(seats["worker_pool"], [])
        self.assertEqual(seats["authorized_total"], 6)

    def test_counted_delegator_worker_row_is_a_seat(self) -> None:
        auth = delegator_auth()
        auth["elite_grants"].append(
            {"preset_id": "devin/default", "count": 1, "state": "granted"})
        self.write_delegator(auth)
        self.write_host(host_grants(drop={"devin/default"}))
        seats = self.state_view_seats()
        worker = group_index(seats)["devin/default"]
        self.assertEqual(worker["authorized_count"], 1)
        self.assertEqual(worker["presets"][0]["class"], "Worker")
        self.assertNotIn({"id": "devin/default", "reason": "host-grant-missing"},
                         worker["unavailable"])
        self.assertEqual(seats["authorized_total"], 7)
        self.assertEqual(seats["worker_pool"], [])

    def test_worker_seats_match_project_grant_groups(self) -> None:
        self.write_host([
            {"id": "grok/default", "state": "granted", "count": 2},
            {"id": "cursor-cli/default", "state": "granted", "count": 2},
            {"id": "droid/default", "state": "granted", "count": 1},
            {"id": "devin/default", "state": "granted", "count": 1},
            {"preset_ids": ["claude-code/default", "claude-code/opus-xhigh"],
             "state": "granted", "count": 1, "shared_seat": "claude-shared"},
        ])
        for auth in (None, {
            "dispatch_enabled": True,
            "elite_grants": [
                {"preset_id": "grok/default", "count": 2, "state": "granted"},
                {"preset_id": "cursor-cli/default", "count": 2, "state": "granted"},
                {"preset_id": "droid/default", "count": 1, "state": "granted"},
                {"preset_ids": ["claude-code/default", "claude-code/opus-xhigh"],
                 "count": 1, "state": "granted"},
            ],
            "worker_pool": ["devin/default"],
        }):
            if auth is None:
                self.delegator_file.unlink()
            else:
                self.write_delegator(auth)
            code, project = run_dispatch([
                "project", "--seats", "--repo", str(self.repo),
                "--authorization", str(self.host_file), "--live", str(self.live),
                "--platforms", str(PLATFORMS),
            ])
            self.assertEqual(code, 0, project)
            groups: dict[str, int] = {}
            for row in project["grants"]:
                count = row.get("count")
                if row.get("state") != "granted" or not isinstance(count, int):
                    continue
                key = row.get("shared_seat") or row["id"]
                groups[key] = max(groups.get(key, 0), count)
            self.assertEqual(sum(groups.values()), 7)
            self.assertEqual(project["summary"]["authorized_total"], 7)
            self.assertEqual(self.state_view_seats()["authorized_total"], 7)

    def test_shared_expert_choice_without_expert_row_stays_out(self) -> None:
        expert_rows = [row for row in delegator_auth()["expert_task_grants"]
                       if row["preset_id"] != "devin/fable"]
        self.write_delegator(delegator_auth(expert_rows=expert_rows))
        code, out = run_dispatch([
            "state", "view", "--role", "delegator", "--file", str(self.host_file),
            "--repo", str(self.repo), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        seats = out["seats"]
        self.assertNotIn("devin/fable", listed_ids(seats))
        groups = group_index(seats)
        pair = groups["grant:cursor-cli/default,devin/fable"]
        self.assertEqual(pair["authorized_count"], 2)
        self.assertEqual([row["id"] for row in pair["presets"]], ["cursor-cli/default"])


if __name__ == "__main__":
    unittest.main()
