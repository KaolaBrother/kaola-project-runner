#!/usr/bin/env python3
"""Issue #295: the Delegator seat summary reads the admission ceiling.

`state view --role delegator`, `delegator view`, and `project --seats` share
one seat summary. It lists Elite and Expert grants from the Delegator
ceiling, a shared group once, a Delegator-granted preset the Host grants
omit as host-grant-missing, and admissible Worker presets in worker_pool
without counting them as seats.
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
        self.assertEqual(listed_ids(seats), EXPECTED_IDS)
        groups = group_index(seats)
        pair = groups["grant:cursor-cli/default,devin/fable"]
        self.assertEqual(pair["authorized_count"], 2)
        self.assertEqual(sorted(row["id"] for row in pair["presets"]),
                         ["cursor-cli/default", "devin/fable"])
        self.assertEqual(seats["authorized_total"], 6)
        self.assertEqual(seats["worker_pool"], ["devin/default"])
        self.assertEqual(seats["expert_authorization"], "present")
        astra = next(row for group in seats["groups"] for row in group["presets"]
                     if row["id"] == "codex/astra")
        self.assertEqual(astra["lifetime"], "standing")
        for group in seats["groups"]:
            self.assertNotIn("devin/default", [row["id"] for row in group["presets"]])

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
        self.assertEqual(summary["authorized_total"], 6)
        self.assertEqual(summary["worker_pool"], ["devin/default"])
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
        self.assertEqual(seats["authorized_total"], 6)

        code, project = run_dispatch([
            "project", "--seats", "--repo", str(self.repo),
            "--authorization", str(self.host_file), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, project)
        self.assertEqual(project["summary"]["authorized_total"], 6)
        self.assertEqual(group_index(project["summary"])["codex/astra"]["unavailable"],
                         [{"id": "codex/astra", "reason": "host-grant-missing"}])

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
