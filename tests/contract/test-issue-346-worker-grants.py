#!/usr/bin/env python3
"""Issue #346: Worker presets are explicit grants. No grant means no Workers.

Fail-on-main at 79770ab7: the default pool still authorizes every Worker
preset, so each case below exits non-zero before the grant rule lands.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
PLATFORMS = PROJECT / "platforms"
DISPATCH = SCRIPTS / "kaola-dispatch.py"
HOLDER = SCRIPTS / "kaola-acp-holder.py"

WORKER = "zcode/default"
OTHER = "dsh/default"
ELITE = "codex/default"
EXPERT = "codex/astra"
PAST = "2020-01-01T00:00:00+00:00"
FUTURE = "2099-01-01T00:00:00+00:00"
NONE = "No Worker grants. There are no Workers until the owner grants some."


def _env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("KAOLA_")}
    env["KAOLA_LAUNCH_BACKEND"] = "direct"
    return env


def load_holder():
    spec = importlib.util.spec_from_file_location("holder_issue_346", HOLDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WorkerGrants(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i346-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / ".kaola").mkdir()
        self.env = _env()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_delegator(self, authorization: dict) -> Path:
        path = self.repo / ".kaola" / "delegator-heartbeat.json"
        path.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": 1,
            "updated_at": "2026-10-18T00:00:00+00:00",
            "authorization": authorization,
        }), encoding="utf-8")
        return path

    def write_host(self, authorization: dict | None = None) -> Path:
        path = self.repo / ".kaola" / "heartbeat-prompt.json"
        path.write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2",
            "host_revision": 1,
            "body": json.dumps({"view": "host"}),
            "state": {"authorization": authorization or {"grants": []}},
        }), encoding="utf-8")
        return path

    def dispatch(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(DISPATCH), *args],
            capture_output=True, text=True, timeout=60, env=self.env)

    def execute(self, presets: list[str], host_grants: list | None = None) -> dict:
        plan = self.root / "plan.json"
        items = [
            {"item_id": f"i{index}", "preset": preset, "session": f"seat{index}", "prompt": "bounded"}
            for index, preset in enumerate(presets)
        ]
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(self.repo), "items": items,
        }), encoding="utf-8")
        auth = self.root / "auth.json"
        auth.write_text(json.dumps({"grants": host_grants or []}), encoding="utf-8")
        live = self.root / "live.json"
        live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": []}), encoding="utf-8")
        proc = self.dispatch([
            "execute", "--dry-run", "--plan", str(plan), "--authorization", str(auth),
            "--platforms", str(PLATFORMS), "--live", str(live),
        ])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        return {row["item_id"]: row for row in payload["items"]}

    def project(self) -> dict:
        auth = self.root / "auth.json"
        if not auth.exists():
            auth.write_text(json.dumps({"grants": []}), encoding="utf-8")
        proc = self.dispatch([
            "project", "--authorization", str(auth), "--repo", str(self.repo),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def view(self) -> dict:
        proc = self.dispatch([
            "delegator", "view", "--file", str(self.repo / ".kaola" / "delegator-heartbeat.json"),
            "--repo", str(self.repo), "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def reasons(self, presets: list[str]) -> dict[str, str]:
        rows = self.execute(presets)
        return {rows[f"i{index}"]["preset"]: rows[f"i{index}"]["reason"] for index in range(len(presets))}

    def test_ungranted_worker_is_a_typed_refusal_and_starts_nothing(self) -> None:
        self.write_delegator({"dispatch_enabled": True, "elite_grants": [], "expert_task_grants": []})
        rows = self.execute([WORKER, "dsh/commandcode"])
        for row in rows.values():
            self.assertEqual(row["status"], "not-run")
            self.assertEqual(row["reason"], "no-worker-grant")
            self.assertNotIn("argv", row)
            evidence = row["evidence"]
            self.assertEqual(evidence["preset"], row["preset"])
            self.assertIn("No Worker grant", evidence["detail"])
            self.assertIn(row["preset"], evidence["detail"])
        ids = {item["id"] for item in self.project()["candidates"]}
        self.assertNotIn(WORKER, ids)
        self.assertNotIn("dsh/commandcode", ids)

    def test_named_grant_dispatches_that_preset_only(self) -> None:
        self.write_delegator({"worker_grants": [{
            "preset_ids": [WORKER], "count": 2, "state": "granted",
        }]})
        reasons = self.reasons([WORKER, OTHER])
        self.assertEqual(reasons[WORKER], "dry-run")
        self.assertEqual(reasons[OTHER], "no-worker-grant")
        ids = {item["id"] for item in self.project()["candidates"] if item["class"] == "Worker"}
        self.assertEqual(ids, {WORKER})

    def test_expired_grant_is_refused(self) -> None:
        self.write_delegator({"worker_grants": [{
            "preset_ids": [WORKER], "count": 2, "state": "granted", "expires": PAST,
        }]})
        row = self.execute([WORKER])["i0"]
        self.assertEqual(row["status"], "not-run")
        self.assertEqual(row["reason"], "worker-grant-expired")
        self.assertIn(WORKER, row["evidence"]["detail"])
        self.assertIn("expired", row["evidence"]["detail"].lower())
        self.assertNotIn("argv", row)

    def test_numeric_count_is_enforced(self) -> None:
        self.write_delegator({"worker_grants": [{
            "preset_ids": [WORKER], "count": 1, "state": "granted",
        }]})
        rows = self.execute([WORKER, WORKER])
        self.assertEqual(rows["i0"]["reason"], "dry-run")
        self.assertEqual(rows["i1"]["status"], "not-run")
        self.assertEqual(rows["i1"]["reason"], "count")
        self.assertNotIn("argv", rows["i1"])

    def test_explicit_unlimited_named_and_all_worker_skip_the_count(self) -> None:
        self.write_delegator({"worker_grants": [{
            "preset_ids": [WORKER], "count": "unlimited", "state": "granted",
        }]})
        named = self.execute([WORKER, WORKER, WORKER, WORKER])
        self.assertTrue(all(row["reason"] == "dry-run" for row in named.values()))
        self.write_delegator({
            "worker_grants": [{
                "scope": "all-worker-presets", "count": "unlimited", "state": "granted",
            }],
            "elite_grants": [],
            "expert_task_grants": [],
        })
        wide = self.execute([WORKER, OTHER, "dsh/commandcode", "opencode/default", WORKER])
        self.assertTrue(all(row["reason"] == "dry-run" for row in wide.values()))
        for label, body in (
            ("missing", {"preset_ids": [WORKER], "state": "granted"}),
            ("null", {"preset_ids": [WORKER], "count": None, "state": "granted"}),
            ("malformed", {"preset_ids": [WORKER], "count": "many", "state": "granted"}),
            ("bool", {"preset_ids": [WORKER], "count": True, "state": "granted"}),
        ):
            self.write_delegator({"worker_grants": [body], "elite_grants": [], "expert_task_grants": []})
            refused = self.execute([WORKER, WORKER, WORKER])
            with self.subTest(label=label):
                self.assertTrue(all(row["reason"] != "dry-run" for row in refused.values()), refused)
                self.assertTrue(all(row["status"] == "not-run" for row in refused.values()))
                self.assertTrue(all(row["evidence"].get("count") != "unlimited" for row in refused.values()))

    def test_unlimited_does_not_override_an_exclusion_or_authorize_elite_or_expert(self) -> None:
        self.write_delegator({
            "worker_grants": [{
                "scope": "all-worker-presets", "count": "unlimited", "state": "granted",
            }],
            "exclusions": [WORKER],
            "elite_grants": [],
            "expert_task_grants": [],
        })
        rows = self.execute([WORKER, OTHER, ELITE, EXPERT])
        self.assertEqual(rows["i0"]["reason"], "excluded")
        self.assertEqual(rows["i0"]["status"], "not-run")
        self.assertEqual(rows["i1"]["reason"], "dry-run")
        self.assertNotEqual(rows["i2"]["reason"], "dry-run")
        self.assertEqual(rows["i2"]["status"], "not-run")
        self.assertNotEqual(rows["i3"]["reason"], "dry-run")
        self.assertEqual(rows["i3"]["status"], "not-run")
        self.write_delegator({
            "worker_grants": [{
                "preset_ids": [ELITE, EXPERT], "count": "unlimited", "state": "granted",
            }],
            "elite_grants": [],
            "expert_task_grants": [],
        })
        named = self.execute([ELITE, EXPERT, WORKER])
        self.assertNotEqual(named["i0"]["reason"], "dry-run")
        self.assertNotEqual(named["i1"]["reason"], "dry-run")
        self.assertEqual(named["i2"]["reason"], "no-worker-grant")

    def test_expired_unlimited_is_refused(self) -> None:
        self.write_delegator({"worker_grants": [{
            "scope": "all-worker-presets", "count": "unlimited", "state": "granted", "expires": PAST,
        }]})
        row = self.execute([WORKER])["i0"]
        self.assertEqual(row["status"], "not-run")
        self.assertEqual(row["reason"], "worker-grant-expired")
        self.assertIn("expired", row["evidence"]["detail"].lower())
        self.assertNotIn("argv", row)
        self.write_delegator({"worker_grants": [{
            "preset_ids": [WORKER], "count": "unlimited", "state": "granted", "expires": FUTURE,
        }]})
        self.assertEqual(self.execute([WORKER])["i0"]["reason"], "dry-run")

    def test_view_lists_worker_grants_and_does_not_derive_a_pool(self) -> None:
        self.write_delegator({"worker_grants": [{
            "preset_ids": [WORKER], "count": "unlimited", "state": "granted", "expires": FUTURE,
        }]})
        viewed = self.view()
        auth = viewed["authorization"]
        self.assertNotIn("worker_pool", auth)
        self.assertNotIn("worker_pool", viewed.get("seats") or {})
        grants = auth["worker_grants"]
        self.assertEqual(grants[0]["preset_ids"], [WORKER])
        self.assertEqual(grants[0]["count"], "unlimited")
        self.assertNotIsInstance(grants[0]["count"], int)
        self.assertEqual(grants[0]["expires"], FUTURE)
        self.assertEqual(grants[0]["coverage"], "named-presets")
        self.assertIn("named presets", auth["worker_grant_statement"])
        self.assertIn("unlimited", auth["worker_grant_statement"])
        self.assertNotIn("worker_pool", viewed["seats"])
        seats = viewed["seats"]
        self.assertEqual(seats["worker_grants"][0]["count"], "unlimited")
        self.assertIn("named presets", seats["worker_grant_statement"])

        self.write_delegator({"worker_grants": [{
            "scope": "all-worker-presets", "count": "unlimited", "state": "granted",
        }]})
        all_view = self.view()
        row = all_view["authorization"]["worker_grants"][0]
        self.assertEqual(row["scope"], "all-worker-presets")
        self.assertEqual(row["coverage"], "all-worker-presets")
        self.assertEqual(row["count"], "unlimited")
        self.assertIn("all Worker presets", all_view["authorization"]["worker_grant_statement"])
        self.assertNotIn("worker_pool", all_view["authorization"])
        self.assertNotIn("worker_pool", all_view["seats"])

        self.write_delegator({"dispatch_enabled": True})
        empty = self.view()
        self.assertEqual(empty["authorization"]["worker_grants"], [])
        self.assertIn(NONE, empty["authorization"]["worker_grant_statement"])
        self.assertIn(NONE, empty["seats"]["worker_grant_statement"])
        self.assertNotIn("worker_pool", empty["seats"])

    def test_legacy_default_pool_yields_zero_workers(self) -> None:
        path = self.write_delegator({
            "dispatch_enabled": True,
            "worker_pool": [WORKER, OTHER, "dsh/commandcode"],
            "elite_grants": [],
            "expert_task_grants": [],
        })
        self.assertEqual(self.reasons([WORKER, OTHER, "dsh/commandcode"]), {
            WORKER: "no-worker-grant",
            OTHER: "no-worker-grant",
            "dsh/commandcode": "no-worker-grant",
        })
        viewed = self.view()
        self.assertEqual(viewed["authorization"]["worker_grants"], [])
        self.assertIn(NONE, viewed["authorization"]["worker_grant_statement"])
        self.assertIn("legacy worker_pool", viewed["authorization"]["worker_grant_statement"])
        self.assertNotIn("worker_pool", viewed["seats"])
        proc = self.dispatch(["delegator", "migrate", "--file", str(path)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        planned = json.loads(proc.stdout)
        self.assertEqual(planned["result"], "planned")
        stored = planned["state"]["authorization"]
        self.assertNotIn("worker_grants", stored)
        self.assertNotIn("worker_pool", stored)
        self.assertTrue(any("worker_pool" in item for item in planned["dropped"]))

    def test_sideagent_chain_uses_only_granted_workers_and_fails_once(self) -> None:
        holder = load_holder()
        self.write_host()
        self.write_delegator({"dispatch_enabled": True})
        carrier = holder.Holder.__new__(holder.Holder)
        carrier.args = argparse.Namespace(repo=str(self.repo))
        carrier.node = {}
        carrier.events = []
        binding = {
            "platform": "zcode",
            "session": "side-346",
            "recipe": {
                "runner": "/bin/echo",
                "argv": ["zcode", "start", "--repo", str(self.repo), "--session", "side-346",
                         "--role", "sideagent"],
            },
        }
        self.assertIsNone(carrier._node_fallback(binding, "zcode", "start-failed"))
        self.assertEqual(len(carrier.events), 1)
        self.assertTrue(carrier.events[0]["exhausted"])
        self.assertEqual(carrier.events[0]["chain"], [])
        self.assertNotIn("to", carrier.events[0])

        self.write_delegator({"worker_grants": [{
            "preset_ids": ["opencode/default"], "count": 1, "state": "granted",
        }]})
        carrier.events.clear()
        carrier.node = {}
        chain = carrier._node_chain(binding, ["zcode"])
        self.assertEqual([item["preset"] for item in chain], ["opencode/default"])
        moved = carrier._node_fallback(binding, "zcode", "start-failed")
        self.assertIsNotNone(moved)
        self.assertEqual(moved["platform"], "opencode")
        self.assertEqual(carrier.events[-1]["to"], "opencode/default")
        self.assertEqual(carrier.events[-1]["chain"], ["opencode/default"])
        self.assertNotIn("zcode/default", carrier.events[-1]["chain"])


if __name__ == "__main__":
    unittest.main()
