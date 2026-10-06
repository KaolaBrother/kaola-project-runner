#!/usr/bin/env python3
"""Issue #259: closed current-state contract, migration, and injection.

These cases sit on the existing state tool and ACP CLI. They do not add a
second QA framework. The shared-seat case records the current admission
result; it does not change that admission.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"
PLATFORMS = REPO / "platforms"
PYTHON = sys.executable
CITE = '{"path":"README.md","locator":"README.md"}'
CLASS_SENTENCES = {
    "Expert": "Expert is the stored grant sentence for this project.",
    "Elite": "Elite is the stored grant sentence for this project.",
    "Worker": "Worker is the stored grant sentence for this project.",
}
DEVIN_SCOPE = "devin/default account west only; do not widen this hold to the project"


CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST",
              "KAOLA_ACP_HEARTBEAT_HOST_SOCKET", "KAOLA_ACP_CHILD_RECORD")


def run_dispatch(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [PYTHON, str(DISPATCH), *args], capture_output=True, text=True, timeout=60,
        env=env or {key: value for key, value in os.environ.items() if key not in CALLER_ENV})
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
    return proc.returncode, payload


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RecordContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i259-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        (self.repo / "README.md").write_text("retire evidence\n", encoding="utf-8")
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.delegator = self.repo / ".kaola" / "delegator-heartbeat.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def state(self, *args: str) -> tuple[int, dict]:
        return run_dispatch(["state", *args])

    def init(self, authorization: dict | None = None) -> None:
        auth = authorization or {
            "grants": [{"id": "codex/default", "state": "granted", "count": 1}],
        }
        if any(grant.get("shared_seat") for grant in auth.get("grants", [])):
            contract = load_module(REPO / "scripts/kaola-record-contract.py", "grouped_fixture_contract")
            auth, blockers, _ = contract.migrate_authorization_limits(auth)
            self.assertEqual(blockers, [], "positive fixture group must have one consistent owner count")
        code, out = self.state(
            "init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
            "--project", json.dumps({"code": "KT", "goal": "close the selected issues", "repo": str(self.repo)}),
            "--authorization", json.dumps(auth))
        self.assertEqual(code, 0, out)

    def test_unknown_nested_key_refuses_without_mutation(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--set",
            json.dumps({"stage": "todo", "goal": "repair", "narrative": "old story"}))
        self.assertEqual(out["reason"], "invalid-input", out)
        self.assertIn("path", out)
        self.assertIn("recovery", out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--set", json.dumps({"stage": "todo", "goal": "repair"}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["goal"], "repair")

    def test_grant_counts_admit_six_without_aggregate_and_refuse_each_excess(self) -> None:
        grants = [{"id": preset, "state": "granted", "count": 1}
                  for preset in ("grok/default", "cursor-cli/default", "codex/default")]
        grants += [{"preset_ids": ["droid/default", "droid/opus", "droid/core"], "shared_seat": "droid",
                    "count": 2, "state": "granted", "model_switch": True},
                   {"preset_ids": ["claude-code/default", "claude-code/opus-xhigh", "claude-code/sonnet"],
                    "shared_seat": "claude-code", "count": 1, "state": "granted", "model_switch": True,
                    "special_requirements": {"claude-code/opus-xhigh": {"task_scope": "thinking and review only"}}}]
        self.init({"grants": grants})
        live = self.repo / "live.json"; live.write_text('{"rows":[]}')
        ids = ["grok/default", "cursor-cli/default", "codex/default", "droid/default", "droid/opus",
               "claude-code/default", "droid/core", "codex/default", "claude-code/sonnet"]
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({"scope": "research", "repo": str(self.repo), "items": [
            {"item_id": str(index), "preset": preset, "session": preset.split('/')[0] + '-KT-' + str(index),
             "prompt": "bounded original task"} for index, preset in enumerate(ids[:6])]}))
        args = ["execute", "--plan", str(plan), "--authorization", str(self.file),
                "--platforms", str(PLATFORMS), "--live", str(live), "--dry-run"]
        code, result = run_dispatch(args); self.assertEqual(code, 0, result)
        rows = {row["item_id"]: row for row in result["items"]}
        self.assertEqual([rows[str(i)]["reason"] for i in range(6)], ["dry-run"] * 6)
        expanded = json.loads(plan.read_text())
        expanded["items"] += [{"item_id": str(index), "preset": preset, "session": preset.split("/")[0] + "-KT-" + str(index), "prompt": "bounded excess"} for index, preset in enumerate(ids) if index >= 6]
        plan.write_text(json.dumps(expanded)); code, result = run_dispatch(args); self.assertEqual(code, 0, result)
        rows = {row["item_id"]: row for row in result["items"]}
        self.assertEqual([rows[str(i)]["reason"] for i in (6, 7, 8)], ["shared-occupied", "count", "resource-conflict"])
        self.assertNotIn("effective_cap", result)
        before = self.file.read_bytes()
        for key in ("elite_cap", "total_cap", "worker_pool_cap", "model_switches", "classes", "capability_summary"):
            code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner",
                                   "--section", "authorization", "--expect-revision", str(self.doc()["revision"]),
                                   "--set", json.dumps({key: 4}))
            self.assertEqual(code, 2, out); self.assertEqual(self.file.read_bytes(), before)
        legacy_plan = json.loads(plan.read_text()); legacy_plan["seat_cap"] = 4; plan.write_text(json.dumps(legacy_plan))
        code, out = run_dispatch(args); self.assertEqual(code, 2, out)
        self.assertIn("plan.seat_cap", out["detail"])

    def test_group_authority_propagates_switch_exclusions_catalog_and_current_duties(self) -> None:
        choices = ["droid/default", "droid/opus", "droid/core"]
        grant = {"preset_ids": choices, "shared_seat": "droid", "count": 1, "state": "granted", "model_switch": False,
                 "special_requirements": {"droid/opus": {"task_scope": "original review only"}}}
        self.init({"grants": [grant], "exclusions": ["zcode/default"]})
        self.update("tasks", "reclaim", {"stage": "doing", "goal": "exact original reclaim",
                                          "session": "droid-KT-original", "holder_instance_id": "exact-holder", "next": "Host exact stop"})
        availability = self.repo / ".kaola" / "dispatch-availability.json"
        availability.write_text(json.dumps({"present": choices + ["zcode/default"], "absent": ["droid/core"]}))
        def project():
            code, out = run_dispatch(["project", "--authorization", str(self.file), "--platforms", str(PLATFORMS),
                                      "--availability", str(availability)])
            self.assertEqual(code, 0, out); return out
        out = project(); self.assertNotIn("zcode/default", out["capability_summary"]["presets"])
        self.assertNotIn("droid/core", out["capability_summary"]["presets"])
        self.assertFalse(next(row for row in out["candidates"] if row["id"] == choices[0])["model_switch"])
        grant.update(count=2, model_switch=True)
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner-change",
                               "--section", "authorization", "--expect-revision", str(self.doc()["revision"]),
                               "--set", json.dumps({"grants": [grant], "exclusions": []}))
        self.assertEqual(code, 0, out)
        stored = self.doc()["state"]["authorization"]
        self.assertEqual(stored, {"grants": [grant], "exclusions": []})
        out = project(); rows = {row["id"]: row for row in out["candidates"]}
        self.assertEqual(rows[choices[0]]["count"], 2); self.assertTrue(rows[choices[0]]["model_switch"])
        self.assertIn("zcode/default", out["capability_summary"]["presets"])
        self.assertEqual(rows["droid/opus"]["special_requirements"], {"task_scope": "original review only"})
        code, host = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, host); self.assertEqual(host["catalog"]["classes"].keys(), {"Elite", "Expert", "Worker"})
        self.assertEqual(host["capability"]["presets"], out["capability_summary"]["presets"])
        self.assertIsInstance(host["capability"]["catalog_source"], str)
        self.assertEqual(len(host["capability"]["catalog_sha256"]), 64)
        unknown = sum(row["availability"] == "unknown" for row in rows.values())
        self.assertGreater(unknown, 0)
        self.assertLess(unknown, len(rows))
        self.assertEqual(host["capability"]["text"], f"availability unknown: {unknown} of {len(rows)} eligible presets")
        self.assertEqual(host["capability"]["catalog_source"], str(PLATFORMS))
        before_layout = self.file.read_bytes()
        installed = Path(self.tmp.name) / "layout" / "skills"
        for manifest in sorted(PLATFORMS.glob("*.yaml")):
            target = installed / f"{manifest.stem}-kaola-project-runner" / "scripts" / "platform.yaml"
            target.parent.mkdir(parents=True)
            target.write_bytes(manifest.read_bytes())
        entry = installed / "kaola-project-runner" / "scripts" / "kaola-dispatch.py"
        entry.parent.mkdir(parents=True)
        entry.touch()
        module = load_module(DISPATCH, "installed_layout_projection")
        with unittest.mock.patch.object(module, "__file__", str(entry)):
            paths = module.platform_paths(entry, None)
            self.assertEqual(len(paths), 10)
            projected = module.host_view(self.doc(), self.file)["capability"]
        self.assertEqual(projected["catalog_source"], str(installed.resolve()))
        self.assertEqual(projected["catalog_sha256"], hashlib.sha256(b"".join(p.read_bytes() for p in paths)).hexdigest())
        self.assertEqual(projected["presets"], host["capability"]["presets"])
        self.assertEqual(projected["text"], host["capability"]["text"])
        availability.unlink()
        code, host_unknown = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, host_unknown)
        eligible = len(host_unknown["capability"]["presets"])
        self.assertEqual(host_unknown["capability"]["text"], f"availability unknown: {eligible} of {eligible} eligible presets")
        self.assertEqual(self.file.read_bytes(), before_layout)
        self.assertEqual(len(json.loads(self.doc()["body"])["authorization"]["grants"]), 3)
        grant["state"] = "revoked"
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner-revoke",
                               "--section", "authorization", "--expect-revision", str(self.doc()["revision"]),
                               "--set", json.dumps({"grants": [grant, {"id": "zcode/default", "count": 1, "state": "revoked"}]}))
        self.assertEqual(code, 0, out)
        auth = self.doc()["state"]["authorization"]; self.assertEqual(auth["grants"], [])
        self.assertEqual(auth["exclusions"], ["zcode/default"]); self.assertNotIn("revoked", auth)
        self.assertEqual(self.doc()["state"]["tasks"]["reclaim"]["holder_instance_id"], "exact-holder")

    def test_legacy_capacity_and_group_conflicts_stay_actionable_migration_repeats(self) -> None:
        self.init()
        code, out = self.update("tasks", "active-work", {"stage": "doing", "goal": "pending original task", "next": "read original result", "holder_instance_id": "original"})
        self.assertEqual(code, 0, out)
        original = self.doc()
        for auth, path in [({"elite_cap": 4}, "authorization.elite_cap"),
                           ({"elite_cap": 1, "grants": [{"id": "codex/default", "count": 2, "state": "granted"}]}, "authorization.elite_cap"),
                           ({"worker_pool_cap": 1, "grants": []}, "authorization.worker_pool_cap"),
                           ({"grants": [{"id": "droid/default", "count": 1, "shared_seat": "droid", "state": "granted"},
                                        {"id": "droid/opus", "count": 2, "shared_seat": "droid", "state": "granted"}]}, "authorization.grants.droid"),
                           ({"grants": [{"preset_ids": ["droid/default", "droid/opus"], "count": 2, "shared_seat": "droid", "state": "granted"},
                                        {"preset_ids": ["droid/core"], "count": 2, "shared_seat": "droid", "state": "granted", "special_requirements": {"droid/core": {"task_scope": "original narrow scope"}}}]}, "authorization.grants.droid"),
                           ({"grants": [{"id": "codex/default", "count": 1, "state": "granted", "model_switch": False}],
                             "model_switches": ["codex/default"]}, "authorization.model_switches")]:
            doc = json.loads(json.dumps(original)); doc["state"]["authorization"] = auth
            self.file.write_text(json.dumps(doc)); before = self.file.read_bytes()
            code, out = self.state("migrate", "--file", str(self.file), "--write")
            self.assertEqual(code, 2, out); self.assertEqual(self.file.read_bytes(), before)
            self.assertIn(path, [row["path"] for row in out["blockers"]])
            if path in ("authorization.elite_cap", "authorization.worker_pool_cap"):
                key = path.split(".")[-1]
                self.assertIn("state update", out["blockers"][0]["recovery"])
                code, recovery = self.state("update", "--file", str(self.file), "--writer", "host",
                    "--source", "original-owner-revoked-limit", "--section", "authorization",
                    "--expect-revision", str(doc["revision"]), "--set", json.dumps({key: None}))
                self.assertEqual(code, 0, recovery)
                self.assertEqual(self.doc()["state"]["authorization"].get("grants", []), auth.get("grants", []))
                self.assertEqual(self.doc()["state"]["tasks"], original["state"]["tasks"])
                code, repeat = self.state("migrate", "--file", str(self.file), "--write")
                self.assertEqual((code, repeat["result"]), (0, "current"), repeat)
        contract = load_module(REPO / "scripts/kaola-record-contract.py", "authority_conflicts_982")
        for stronger in ("revoked", "excluded"):
            auth = {"grants": [{"id": "codex/default", "state": stronger, "count": 1}], "paused": ["codex/default"]}
            prepared, blockers, _ = contract.migrate_authorization_limits(auth)
            self.assertIn("authorization.paused", [row["path"] for row in blockers])
            self.assertEqual(prepared["grants"][0]["state"], stronger)
            self.file.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1", "body": json.dumps({"authorization": auth})}))
            before = self.file.read_bytes()
            code, blocked = self.state("migrate", "--file", str(self.file), "--write")
            self.assertEqual(code, 2, blocked)
            self.assertEqual(self.file.read_bytes(), before)
        overlap = {"grants": [{"id": "droid/opus", "count": 1, "state": "granted"},
                              {"preset_ids": ["droid/default", "droid/opus"], "count": 2, "state": "granted"}]}
        self.assertIn("duplicate preset droid/opus", str(contract.authorization_blockers(overlap)))
        self.assertIn("duplicate preset droid/opus", str(contract.migrate_authorization_limits(overlap)[1]))
        self.file.write_text(json.dumps(original))
        code, overlap_write = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner",
            "--section", "authorization", "--expect-revision", str(self.doc()["revision"]), "--set", json.dumps(overlap))
        self.assertEqual(code, 2, overlap_write)
        doc = json.loads(json.dumps(original))
        doc["state"]["authorization"] = {"elite_cap": 1, "classes": CLASS_SENTENCES,
            "capability_summary": {"presets": ["codex/default", "grok/default"]},
            "paused": ["droid/default", "droid/opus"], "revoked": ["zcode/default"],
            "model_switches": ["droid/default", "droid/opus"], "grants": [
                {"id": ident, "count": 2, "shared_seat": "droid", "state": "granted"} for ident in ("droid/default", "droid/opus")]}
        self.file.write_text(json.dumps(doc)); before = self.file.read_bytes()
        code, out = self.state("migrate", "--file", str(self.file)); self.assertEqual(code, 2, out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
            "--source", "original-owner-revoked-limit", "--section", "authorization",
            "--expect-revision", str(doc["revision"]), "--set", '{"elite_cap":null}')
        self.assertEqual(code, 0, out)
        self.assertIn("authorization.classes derived from catalog/grants", out["removed"])
        code, out = self.state("migrate", "--file", str(self.file), "--write"); self.assertEqual(code, 0, out)
        after = self.file.read_bytes(); auth = self.doc()["state"]["authorization"]
        self.assertEqual(len(auth["grants"]), 1); self.assertTrue(auth["grants"][0]["model_switch"])
        self.assertEqual(auth["grants"][0]["state"], "paused")
        self.assertEqual(auth["exclusions"], ["zcode/default"])
        self.assertEqual(set(auth), {"grants", "exclusions"}); self.assertEqual(self.doc()["state"]["tasks"]["active-work"], original["state"]["tasks"]["active-work"])
        code, out = self.state("migrate", "--file", str(self.file), "--write"); self.assertEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), after)

        legacy_auth = {"elite_cap": 4, "classes": CLASS_SENTENCES,
                       "grants": [{"id": "codex/default", "state": "granted"}]}
        legacy_body = {"project": {"code": "KT"}, "authorization": legacy_auth,
                       "active": [{"ref": "original", "session": "codex-KT-original", "next": "read result"}]}
        self.file.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1", "body": json.dumps(legacy_body)}))
        before = self.file.read_bytes()
        code, refusal = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 2, refusal)
        self.assertEqual(self.file.read_bytes(), before)
        # Revision and role checks apply before the only allowed pre-migration removal.
        code, refusal = self.state("update", "--file", str(self.file), "--writer", "sideagent", "--source", "owner",
            "--section", "authorization", "--expect-revision", "0", "--set", '{"elite_cap":null}')
        self.assertEqual((code, refusal["reason"]), (2, "host-only"), refusal)
        self.assertEqual(self.file.read_bytes(), before)
        code, refusal = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner",
            "--section", "authorization", "--expect-revision", "1", "--set", '{"elite_cap":null}')
        self.assertEqual((code, refusal["reason"]), (3, "conflict"), refusal)
        self.assertEqual(self.file.read_bytes(), before)
        code, recovered = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "original-owner-revoked-limit",
            "--section", "authorization", "--expect-revision", "0", "--set", '{"elite_cap":null}')
        self.assertEqual(code, 0, recovered)
        stored_body = json.loads(self.doc()["body"])
        self.assertEqual(stored_body["authorization"], {k: v for k, v in legacy_auth.items() if k != "elite_cap"})
        self.assertEqual(stored_body["active"], legacy_body["active"])
        code, migrated = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, migrated["result"]), (0, "migrated"), migrated)
        self.assertNotIn("count", self.doc()["state"]["authorization"]["grants"][0])
        code, view = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertIn({"id": "codex/default", "reason": "count-unreadable"}, view["capability"]["withheld"])
        self.assertIn("original", self.doc()["state"]["tasks"])
        code, repeat = self.state("migrate", "--file", str(self.file))
        self.assertEqual((code, repeat["result"]), (0, "current"), repeat)

    def test_delegator_group_pause_expiry_and_resolved_relay_preserve_current_duties(self) -> None:
        self.init({"grants": [{"preset_ids": ["droid/default", "droid/opus"], "count": 2, "state": "granted"}]})
        self.delegator.write_text(json.dumps({"schema": "kaola-delegator-heartbeat/1", "revision": 0,
            "project": {"goal": "current objective", "user_language": "zh-TW"},
            "authorization": {"worker_pool": ["zcode/default"], "exclusions": ["zcode/default"],
                "elite_grants": [{"preset_ids": ["droid/default", "droid/opus"], "count": 2,
                    "state": "paused", "switch_authorization": False,
                    "special_requirements": {"droid/opus": {"task_scope": "authorized review"}}}],
                "expert_task_grants": [{"preset_id": "codex/astra", "count": 1, "lifetime": "standing",
                    "expires": "2000-01-01T00:00:00Z"}]},
            "watch": {"stop": {"kind": "recovery", "status": "open", "source": "original-expiry",
                    "next": "exact-stop original holder", "locator": "original-holder"},
                "reopen": {"kind": "decision", "status": "pending", "detail": "service hold",
                    "source": "original-owner", "next": "owner confirms reopening"},
                "relay": {"kind": "relay", "status": "pending", "source": "owner-change", "next": "confirm adoption"}}}))
        args = ["delegator", "migrate", "--file", str(self.delegator)]
        before = self.delegator.read_bytes()
        code, plan = run_dispatch(args); self.assertEqual(code, 0, plan)
        self.assertEqual(self.delegator.read_bytes(), before)
        code, out = run_dispatch(args + ["--write"]); self.assertEqual(code, 0, out)
        current = json.loads(self.delegator.read_text())
        self.assertEqual(current["authorization"]["expert_task_grants"], [])
        self.assertEqual(current["watch"]["stop"]["locator"], "original-holder")
        after = self.delegator.read_bytes()
        code, out = run_dispatch(args + ["--write"]); self.assertEqual(code, 0, out)
        self.assertEqual(self.delegator.read_bytes(), after)
        live = self.repo / "live.json"; live.write_text('{"rows":[]}')
        index = self.repo / "index.json"; index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": []}))
        availability = self.repo / "availability.json"
        availability.write_text(json.dumps({"present": ["droid/default", "droid/opus"]}))
        view_args = ["delegator", "view", "--file", str(self.delegator), "--repo", str(self.repo),
                     "--platforms", str(PLATFORMS), "--live", str(live), "--index", str(index), "--availability", str(availability)]
        code, view = run_dispatch(view_args); self.assertEqual(code, 0, view)
        self.assertEqual(view["seats"]["expert_authorization"], "none")
        self.assertEqual(view["seats"]["idle_available_total"], 0)
        self.assertEqual(view["authorization"]["elite_grants"][0]["special_requirements"]["droid/opus"]["task_scope"], "authorized review")
        patch = {"authorization": {"elite_grants": [{**current["authorization"]["elite_grants"][0], "state": "granted"}]},
                 "watch": {"relay": {"status": "adopted", "evidence": "original-host-adoption"}}}
        code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "owner-reopening-and-adoption", "--expect-revision", str(current["revision"]), "--set", json.dumps(patch)])
        self.assertEqual(code, 0, out)
        stored = json.loads(self.delegator.read_text())
        self.assertNotIn("relay", stored["watch"])
        self.assertEqual(set(stored["watch"]), {"stop", "reopen"})
        self.assertEqual(stored["project"]["user_language"], "zh-TW")
        self.assertEqual(stored["authorization"]["exclusions"], ["zcode/default"])
        code, view = run_dispatch(view_args); self.assertEqual(code, 0, view)
        self.assertEqual(view["seats"]["idle_available_total"], 2)
        self.assertEqual(view["seats"]["authorized_total"], 2)
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "duplicate-switch", "--expect-revision", str(stored["revision"]), "--set",
            json.dumps({"authorization": {"model_switches": ["droid/default"]}})])
        self.assertEqual(code, 2, out); self.assertEqual(self.delegator.read_bytes(), before)

        worker_pause = {"schema": "kaola-delegator-heartbeat/1", "revision": 0,
            "authorization": {"worker_pool": ["zcode/default", "dsh/default"], "paused": ["zcode/default"]},
            "watch": {"reopen": {"kind": "recovery", "status": "open", "source": "original-pause",
                                  "next": "owner reopening decision", "locator": "original-owner-pause"}}}
        self.delegator.write_text(json.dumps(worker_pause))
        before = self.delegator.read_bytes()
        for argv in (["migrate", "--write"], ["update", "--writer", "delegator", "--source", "ordinary-progress",
                                               "--expect-revision", "0", "--set", '{"project":{"goal":"ship"}}']):
            code, refusal = run_dispatch(["delegator", *argv, "--file", str(self.delegator)])
            self.assertEqual(code, 2, refusal)
            self.assertIn("authorization.paused", [row["path"] for row in refusal["blockers"]])
            self.assertEqual(self.delegator.read_bytes(), before)
        code, recovered = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "original-owner-pause", "--expect-revision", "0", "--set",
            '{"authorization":{"exclusions":["zcode/default"]}}'])
        self.assertEqual(code, 0, recovered)
        self.assertIn("authorization.paused -> current grants/exclusions", recovered["removed"])
        saved = json.loads(self.delegator.read_text())
        self.assertEqual(saved["authorization"]["exclusions"], ["zcode/default"])
        self.assertEqual(saved["watch"], worker_pause["watch"])
        saved["authorization"]["elite_grants"] = [{"preset_id": "codex/default", "count": 1, "class": "Elite"}]
        self.delegator.write_text(json.dumps(saved))
        code, migrated = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 0, migrated)
        self.assertIn("authorization.elite_grants[0].class derived from catalog", migrated["dropped"])
        self.assertNotIn("class", json.loads(self.delegator.read_text())["authorization"]["elite_grants"][0])

    def update(self, kind: str, ident: str, patch: dict, *args: str) -> tuple[int, dict]:
        return self.state("update", "--file", str(self.file), "--writer", "host", "--source", "original-source",
                          "--kind", kind, "--id", ident, "--set", json.dumps(patch), *args)

    def test_current_exception_resolution_repeated_cli_views_and_newer_recovery(self) -> None:
        self.init()
        self.update("tasks", "actual-work", {"stage": "doing", "goal": "pending-goal-marker",
                                            "dispatch": ["original-admission"], "next": "read actual result"})
        self.update("tasks", "pending-stop-handoff", {"stage": "doing", "goal": "preserve original reclaim duty",
            "session": "codex-KT-original", "holder_instance_id": "original-holder",
            "dispatch": ["original-stop-link"], "next": "verify exact stop or confirmed current handoff"})
        pending_tasks = self.doc()["state"]["tasks"]
        dispatch = load_module(REPO / "scripts/kaola-dispatch.py", "retirement_reconciliation_988")
        doc = self.doc()
        doc["state"]["maintenance"] = {"recovery_seq": 9, "recovery_input": {
            "seq": 9, "kind": "request", "source": "original-inquiry", "occurrence_id": "original-inquiry",
            "holder": "original-holder", "at": "2026-10-06T00:00:00Z", "evidence": "original-inquiry-receipt"}}
        self.file.write_text(json.dumps(doc))
        pending = self.doc()["state"]["maintenance"]
        grants = self.doc()["state"]["authorization"]
        ids = ("droid-shared-capacity", "record-contract-design-index-gone",
               "writing-guidance-retire-unmet", "maintenance-returned")
        for cycle in range(2):
            for ident in ids:
                marker = f"handled-marker-{cycle}-{ident}"
                patch = {"level": "warn", "summary": marker, "owner": "host", "evidence": "README.md"}
                code, out = self.update("alerts", ident, patch)
                self.assertEqual(code, 0, out)
                code, out = self.update("alerts", ident, {"ack": True}, "--expect-rev", "1")
                self.assertEqual(code, 0, out)
                self.assertIn(ident, self.doc()["state"]["alerts"], "acknowledged is not handled")
                before = self.file.read_bytes()
                code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source",
                                       "original-owner-disposition", "--kind", "alerts", "--id", ident,
                                       "--expect-rev", "1", "--evidence", "README.md")
                self.assertEqual(code, 3, out)
                self.assertEqual(self.file.read_bytes(), before, "stale clear cannot remove a newer row")
                code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source",
                                       "original-owner-disposition", "--kind", "alerts", "--id", ident,
                                       "--expect-rev", "2", "--evidence", "README.md")
                self.assertEqual(code, 0, out)
                # The original operation is the resolution proof; absence is
                # intentional current-only storage, not a missing tombstone.
                receipt = out
                self.assertEqual((receipt["value"]["kind"], receipt["value"]["id"], receipt["value"]["outcome"]),
                                 ("alerts", ident, "resolved"))
                self.assertNotIn(ident, self.doc()["state"]["alerts"])
                self.assertFalse(self.doc()["state"].get("retired"))
                retired_revision = receipt["host_revision"]
                self.assertEqual(dispatch.host_changes(self.doc(), retired_revision - 1, retired_revision), {})
                self.assertNotIn(marker, self.file.read_text())
                for role in ("host", "sideagent", "delegator"):
                    code, view = self.state("view", "--file", str(self.file), "--role", role,
                                            "--repo", str(self.repo))
                    self.assertEqual(code, 0, view)
                    self.assertNotIn(marker, json.dumps(view))
                self.assertNotIn(marker, self.doc()["body"])
                code, out = self.update("alerts", ident, patch, "--expect-rev", "2")
                self.assertNotEqual(code, 0, out)
                self.assertIn("Do not create", out["recovery"])
                self.assertIn(f"alerts/{ident}", out["recovery"])
                self.assertNotIn("omits --expect-rev", out["recovery"])
            self.update("decisions", "owner-answer", {"owner": "user", "question": "answer-marker",
                                                      "status": "pending"})
            before = self.file.read_bytes()
            code, out = self.update("decisions", "owner-answer", {"status": "settled"}, "--expect-rev", "1")
            self.assertNotEqual(code, 0, out)
            self.assertEqual(self.file.read_bytes(), before)
            code, out = self.update("decisions", "owner-answer", {"status": "settled", "answer": "yes",
                                                                  "evidence": "original-user-answer"}, "--expect-rev", "1")
            self.assertEqual(code, 0, out)
            self.assertNotIn("owner-answer", self.doc()["state"]["decisions"])
            self.assertNotIn("answer-marker", self.file.read_text())
        self.update("alerts", "maintenance-returned", {"level": "warn", "summary": "new-recovery-marker",
                                                       "inputs": {"recovery#9": {"why": "checkpoint-missing"}}})
        before = self.file.read_bytes()
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "old-return",
                               "--kind", "alerts", "--id", "maintenance-returned", "--expect-rev", "1",
                               "--evidence", "old-judged-checkpoint")
        self.assertEqual(out["reason"], "retire-unmet", out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(self.doc()["state"]["maintenance"], pending)
        self.assertEqual(self.doc()["state"]["authorization"], grants)
        self.assertEqual(self.doc()["state"]["tasks"], pending_tasks)
        self.assertEqual(self.doc()["state"]["tasks"]["actual-work"]["dispatch"], ["original-admission"])
        self.assertIn("pending-goal-marker", self.file.read_text())

    def test_refusal_names_current_clear_and_absent_terminal_is_not_created(self) -> None:
        self.init()
        self.update("alerts", "handled", {"level": "watch", "summary": "actual current fault"})
        before = self.file.read_bytes()
        code, out = self.update("alerts", "handled", {"resolved": True}, "--expect-rev", "1")
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertIn("alerts/handled", out["recovery"])
        self.assertIn("--expect-rev 1", out["recovery"])
        self.assertIn("state retire", out["recovery"])
        self.assertIn("ORIGINAL_HANDLED_EVIDENCE", out["recovery"])
        self.assertNotIn("rehome", out["recovery"])
        code, out = self.update("decisions", "absent", {"owner": "host", "question": "past",
                                                      "status": "settled", "evidence": "past"})
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertIn("Do not create", out["recovery"])
        code, out = self.update("alerts", "handled", {"next": {"history": "past"}}, "--expect-rev", "1")
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)
        for patch in ({"evidence": [{"past": "history"}]},
                      {"inputs": {"old-input": {"why": "past", "history": "resolved narrative"}}}):
            code, out = self.update("alerts", "handled", patch, "--expect-rev", "1")
            self.assertNotEqual(code, 0, out)
            self.assertEqual(self.file.read_bytes(), before)
        self.delegator.write_text(json.dumps({"revision": 4, "watch": {}}))
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                                  "--source", "original-effect", "--expect-revision", "4", "--set",
                                  '{"watch":{"absent":{"kind":"relay","status":"adopted","evidence":"effect"}}}'])
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.assertIn("Do not create", out["blockers"][0]["recovery"])

    def test_terminal_migration_repeats_preserve_pending_adoption_and_grants(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["decisions"] = {
            "past": {"owner": "user", "question": "handled-history-marker", "status": "settled", "evidence": "answer", "rev": 1},
            "adoption": {"owner": "host", "question": "adopt original answer", "status": "settled", "evidence": "answer",
                         "transcribed": {"host_turn": "original-turn", "fields": ["status"]}, "rev": 1},
            "pending": {"owner": "user", "question": "still pending", "status": "pending", "rev": 1}}
        self.file.write_text(json.dumps(doc))
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertNotIn("handled-history-marker", self.file.read_text())
        self.assertNotIn("past", self.doc()["state"]["decisions"])
        self.assertEqual(self.doc()["state"]["decisions"]["adoption"]["status"], "pending")
        self.assertIn("transcribed-check", self.doc()["body"])
        self.assertIn("pending", self.doc()["state"]["decisions"])
        before = self.file.read_bytes()
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)
        doc = self.doc()
        doc["state"]["decisions"]["unknown"] = {"owner": "user", "question": "unknown answer", "status": "settled", "rev": 1}
        self.file.write_text(json.dumps(doc))
        before = self.file.read_bytes()
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertIn("Unknown is not resolved", out["blockers"][0]["recovery"])
        self.delegator.write_text(json.dumps({"revision": 0, "watch": {
            "latest": {"status": "settled", "report": "unverified original matter"}}}))
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 2, out)
        self.assertEqual(self.delegator.read_bytes(), before, "a terminal token alone is not original effect evidence")

    def test_ended_eligibility_leaves_grants_without_restoring_pool_or_losing_work(self) -> None:
        self.init()
        self.update("tasks", "pending-stop", {"stage": "doing", "goal": "exact reclaim", "dispatch": ["original"]})
        revision = self.doc()["revision"]
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner-revocation",
                               "--section", "authorization", "--expect-revision", str(revision), "--set",
                               json.dumps({"grants": [{"id": "codex/default", "state": "revoked", "count": 1},
                                                      {"id": "codex/astra", "state": "granted", "count": 1,
                                                       "expires": "2000-01-01T00:00:00Z"},
                                                      {"id": "droid/default", "state": "granted", "count": 2}]}))
        self.assertEqual(code, 0, out)
        auth = self.doc()["state"]["authorization"]
        self.assertNotIn("codex/default", [g["id"] for g in auth["grants"]])
        self.assertNotIn("codex/astra", [g["id"] for g in auth["grants"]])
        self.assertNotIn("revoked", auth)
        self.assertNotIn("capability_summary", auth)
        self.assertEqual(self.doc()["state"]["tasks"]["pending-stop"]["dispatch"], ["original"])
        self.assertNotIn("classes", auth)
        dispatch = load_module(DISPATCH, "partial_catalog_revocation_982")
        with unittest.mock.patch.object(dispatch, "catalog_from_files", return_value={}):
            limited = dispatch.current_authorization({"revoked": ["zcode/default", "future/default"],
                "grants": [{"id": "unknown/worker", "state": "revoked", "count": 1}]})
        self.assertEqual(limited["exclusions"], ["future/default", "unknown/worker", "zcode/default"])
        self.assertEqual(limited["grants"], [])
        self.delegator.write_text(json.dumps({"revision": 0, "authorization": {
            "revoked": ["codex/default", "codex/astra"], "worker_pool": ["codex/default", "codex/luna"],
            "expert_task_grants": [{"preset_id": "codex/astra", "count": 1}],
            "elite_grants": [{"preset_ids": ["codex/default", "droid/default"], "count": 2}]},
            "watch": {"stop": {"kind": "recovery", "status": "open", "source": "original-revocation",
                               "next": "verify exact stop", "locator": "original-holder"}}}))
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 0, out)
        saved = json.loads(self.delegator.read_text())
        self.assertEqual(saved["authorization"]["worker_pool"], ["codex/default", "codex/luna"])
        self.assertIn("codex/default", saved["authorization"]["exclusions"])
        self.assertNotIn("revoked", saved["authorization"])
        self.assertEqual(saved["authorization"]["expert_task_grants"], [])
        self.assertEqual(saved["authorization"]["elite_grants"], [{"preset_ids": ["droid/default"], "count": 2}])
        self.assertEqual(saved["watch"]["stop"]["locator"], "original-holder")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.delegator.read_bytes(), before)

    def test_delegator_seat_summary_groups_live_task_states_cap_and_no_host_cycle(self) -> None:
        grants = [{"id": f"claude-code/{tier}", "state": "granted", "count": 1, "shared_seat": "claude-code"}
                  for tier in ("default", "opus-xhigh", "sonnet")]
        grants += [{"id": f"droid/{tier}", "state": "granted", "count": 2, "shared_seat": "droid"}
                   for tier in ("default", "opus", "core")]
        grants += [{"id": "codex/default", "state": "granted", "count": 1},
                   {"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"},
                   {"id": "codex/luna", "state": "granted", "count": 3}]
        self.init({"grants": [{"preset_ids": [g["id"] for g in grants[:3]], "count": 1, "state": "granted", "shared_seat": "claude-code"}, {"preset_ids": [g["id"] for g in grants[3:6]], "count": 2, "state": "granted", "shared_seat": "droid"}] + grants[6:]})
        self.update("tasks", "real-review", {"stage": "doing", "goal": "read original review", "dispatch": ["original-review"]})
        self.update("tasks", "reclaim", {"stage": "doing", "goal": "exact reclaim", "session": "droid-KPR-returned",
                                          "holder_instance_id": "droid-original"})
        self.delegator.write_text(json.dumps({"schema": "kaola-delegator-heartbeat/1", "revision": 0,
            "authorization": {"elite_grants": [
                {"preset_ids": [g["id"] for g in grants if g["id"].startswith("claude-code/")], "count": 1},
                {"preset_ids": [g["id"] for g in grants if g["id"].startswith("droid/")], "count": 2},
                {"preset_id": "codex/default", "count": 1},
                {"preset_id": "codex/astra", "count": 1, "lifetime": "standing"}]}, "watch": {}}))
        def live(preset, session, holder, mutation, **extra):
            return {"repo": str(self.repo), "identity": "verified", "state": "ready", "preset": preset,
                    "platform": preset.split("/")[0], "session": session, "holder_instance_id": holder,
                    "mutation_status": mutation, **extra}
        live_file = self.repo / "live.json"
        live_file.write_text(json.dumps({"rows": [
            live("claude-code/opus-xhigh", "claude-code-KPR-review", "claude-original", "in_progress"),
            live("droid/core", "droid-KPR-returned", "droid-original", "completed"),
            live("codex/astra", "codex-KPR-reserved", "astra-original", "not_started"),
            live("codex/default", "codex-KPR-host", "host-original", "in_progress", session_role="host"),
            live("droid/default", "droid-KPR-side", "side-original", "in_progress", session_role="sideagent"),
            live("codex/luna", "codex-KPR-pool", "pool-original", "in_progress")]}))
        index = self.repo / ".kaola" / "dispatch-index.json"
        index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": [
            {"item_id": "original-review", "task_id": "real-review", "repo": str(self.repo), "status": "in-flight",
             "session": "claude-code-KPR-review", "holder_instance_id": "claude-original", "preset": "claude-code/opus-xhigh"}]}))
        availability = self.repo / "available.json"
        availability.write_text(json.dumps({"present": [g["id"] for g in grants]}))
        flags = ["--live", str(live_file), "--index", str(index), "--availability", str(availability)]
        before = {p: p.read_bytes() for p in (self.file, self.delegator, index)}
        code, view = self.state("view", "--file", str(self.file), "--role", "delegator", *flags)
        self.assertEqual(code, 0, view)
        summary = view["seats"]
        groups = summary["groups"]
        claude = next(g for g in groups if any(p["id"] == "claude-code/default" for p in g["presets"]))
        droid = next(g for g in groups if any(p["id"] == "droid/default" for p in g["presets"]))
        self.assertEqual((claude["authorized_count"], droid["authorized_count"]), (1, 2))
        self.assertEqual(len(claude["presets"]), 3)
        self.assertEqual(claude["occupied"][0]["tasks"], ["real-review"])
        self.assertEqual(claude["occupied"][0]["state"], "working")
        self.assertEqual(droid["occupied"][0]["state"], "idle-but-unreclaimed")
        self.assertEqual(droid["idle_available"], 1)
        self.assertEqual(summary["occupied_elite_expert"], 3)
        self.assertEqual(summary["authorized_total"], 5)
        self.assertEqual(summary["idle_available_total"], 2, "derive capacity from shared grants, never sum tier rows")
        self.assertNotIn("elite_cap", summary)
        expert = next(g for g in groups if any(p["id"] == "codex/astra" for p in g["presets"]))
        self.assertEqual(expert["presets"][0]["lifetime"], "standing")
        self.assertEqual((expert["occupied"][0]["state"], expert["idle_available"]), ("reserved", 0))
        self.assertNotIn("codex/luna", json.dumps(groups))
        code, own = run_dispatch(["delegator", "view", "--file", str(self.delegator), *flags])
        self.assertEqual(code, 0, own)
        for key in ("groups", "expert_authorization", "occupied", "idle_available_total", "authorized_total"):
            self.assertEqual(own["seats"][key], summary[key])
        code, on_demand = run_dispatch(["project", "--seats", "--repo", str(self.repo), "--authorization", str(self.file), *flags])
        self.assertEqual(code, 0, on_demand)
        self.assertEqual(on_demand["summary"]["groups"], groups)
        code, host = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, host)
        self.assertNotIn("seats", host, "Host has no compulsory seat reporting cycle or injection")
        self.assertNotIn("seats", json.loads(self.doc()["body"]))
        self.assertEqual(before, {p: p.read_bytes() for p in before}, "reporting stores no occupancy or history")
        self.update("holds", "actual-fault", {"scope": "droid-only", "reason": "original service refusal",
                                               "presets": ["droid/default", "droid/opus", "droid/core"], "evidence": "original-refusal"})
        rows = json.loads(live_file.read_text())
        rows["rows"][0]["mutation_status"] = "unknown"
        live_file.write_text(json.dumps(rows))
        code, view = self.state("view", "--file", str(self.file), "--role", "delegator", *flags)
        self.assertEqual(code, 0, view)
        claude = next(g for g in view["seats"]["groups"] if any(p["id"] == "claude-code/default" for p in g["presets"]))
        droid = next(g for g in view["seats"]["groups"] if any(p["id"] == "droid/default" for p in g["presets"]))
        self.assertEqual(claude["occupied"][0]["state"], "unknown")
        self.assertIsNone(claude["idle_available"])
        self.assertEqual(droid["occupied"][0]["state"], "held/faulted")
        self.assertEqual(droid["idle_available"], 0)
        self.assertEqual(len(droid["unavailable"]), 3)

    def test_delegator_missing_expert_and_unknown_sources_do_not_imply_free_seats(self) -> None:
        self.init()
        missing = self.repo / "missing-live.json"
        before = self.file.read_bytes()
        code, view = self.state("view", "--file", str(self.file), "--role", "delegator", "--live", str(missing))
        self.assertEqual(code, 0, view)
        self.assertEqual(view["seats"]["expert_authorization"], "none")
        self.assertIn("live-source-unavailable", view["seats"]["unknown_reasons"])
        self.assertIsNone(view["seats"]["idle_available_total"])
        self.assertIsNone(view["seats"]["groups"][0]["idle_available"])
        self.assertEqual(self.file.read_bytes(), before)
        self.file.unlink()  # no Host fallback masks the Delegator projection
        self.delegator.write_text(json.dumps({"schema": "kaola-delegator-heartbeat/1", "revision": 0,
            "authorization": {"elite_grants": [{"preset_id": "codex/default", "count": 2,
                "special_requirements": "thinking and review only"}]}}))
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertEqual(code, 0, view)
        self.assertEqual(view["seats"]["authorized_total"], 2)
        self.assertEqual(json.loads(self.delegator.read_text())["authorization"]["elite_grants"][0]["special_requirements"],
                         "thinking and review only")

    def test_catalog_class_definitions_are_derived_without_stored_copies(self) -> None:
        self.init({"grants": [{"preset_ids": ["droid/default", "droid/opus"], "count": 2, "state": "granted"}]})
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, out)
        self.assertEqual(set(out["catalog"]["classes"]), {"Expert", "Elite", "Worker"})
        self.assertNotIn("classes", self.doc()["state"]["authorization"])
        self.assertEqual(out["capability"]["shared_seats"][0]["count"], 2)
        self.assertIn("sha256", out["catalog"])
        code, side = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, side)
        self.assertNotIn("classes", side["state"]["authorization"])

    def test_shared_seat_group_keeps_grant_count_two(self) -> None:
        """Owner grant count is 2. One live seat leaves one place in that pool."""
        dispatch = load_module(DISPATCH, "kpr_i259_dispatch")
        grants = [
            {"id": "droid/default", "state": "granted", "count": 2, "shared_seat": "droid"},
            {"id": "droid/opus", "state": "granted", "count": 2, "shared_seat": "droid"},
            {"id": "droid/core", "state": "granted", "count": 2, "shared_seat": "droid"},
        ]
        self.assertEqual({grant["count"] for grant in grants}, {2})
        catalog = {grant["id"]: {"class": "Elite", "platform": "droid"} for grant in grants}
        rows = [{
            "session": "droid-KT-one", "state": "ready", "platform": "droid",
            "preset": "droid/default", "repo": str(self.repo),
        }]
        used_count, _seats, occupied, unnamed = dispatch.live_occupancy(
            rows, str(self.repo), catalog, grants)
        self.assertEqual(occupied, {"droid": 1})
        self.assertEqual(dispatch.shared_seat_capacities(grants), {"droid": 2})
        self.assertEqual(used_count["droid/default"], 1)
        item = {
            "preset": "droid/opus", "_shared_seat": "droid", "_count": 2,
            "_shared_capacity": 2, "_platform": "droid", "_pool": True,
        }
        self.assertIsNone(
            dispatch.held_refusal(item, used_count, occupied, unnamed, grants, catalog))
        occupied["droid"] = 2
        self.assertEqual(
            dispatch.held_refusal(item, used_count, occupied, unnamed, grants, catalog),
            "shared-occupied")

    def test_stage_warning_clears_only_on_a_sourced_stage(self) -> None:
        body = {"project": {"code": "KT"}, "authorization": {"grants": []},
                "pending": [{"duty": "apply the named repair", "owner": "Host"}]}
        self.file.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1", "body": json.dumps(body)}),
                             encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertIn("duty-1-stage", self.doc()["state"]["unverified"])
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
            "--kind", "tasks", "--id", "duty-1", "--expect-rev", "1",
            "--set", json.dumps({"stage": "doing"}))
        self.assertEqual(code, 0, out)
        self.assertIn("duty-1-stage", self.doc()["state"]["unverified"])
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "host-turn",
            "--kind", "tasks", "--id", "duty-1", "--expect-rev", "2",
            "--set", json.dumps({"stage": "doing", "next": "apply the repair"}))
        self.assertEqual(code, 0, out)
        self.assertNotIn("duty-1-stage", self.doc()["state"]["unverified"])

    def test_closed_task_leaves_and_pending_goal_stays(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "done-one",
                   "--set", json.dumps({"stage": "done", "goal": "finished note",
                                        "verdict": {"value": "accepted"}}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "open-one",
                   "--set", json.dumps({"stage": "doing", "goal": "apply repair", "next": "seat the repair"}))
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "done-one", "--expect-rev", "1", "--evidence", "reviewed",
            "--cite", CITE)
        self.assertEqual(code, 0, out)
        state = self.doc()["state"]
        self.assertNotIn("done-one", state["tasks"])
        self.assertEqual(state["tasks"]["open-one"]["goal"], "apply repair")
        self.assertEqual(out["value"]["cite"]["path"], "README.md")
        self.assertNotIn("evidence", out["value"])
        self.assertFalse(state.get("retired"))

    def test_devin_hold_scope_is_not_shortened(self) -> None:
        self.init()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "holds", "--id", "devin-west",
            "--set", json.dumps({"preset": "devin/default", "scope": DEVIN_SCOPE, "owner": "host",
                                 "reason": "account limit"}))
        self.assertEqual(code, 0, out)
        view = json.loads(self.doc()["body"])
        shown = view["holds"][0]
        self.assertEqual(shown["preset"], "devin/default")
        self.assertEqual(shown["scope"], DEVIN_SCOPE)

    def test_later_dispatch_batch_keeps_the_live_ref(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t1",
                   "--set", json.dumps({"stage": "doing", "goal": "g", "dispatch": ["first-live"]}))
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--expect-rev", "1",
            "--set", json.dumps({"dispatch": ["second-batch"]}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["dispatch"], ["first-live", "second-batch"])

    def test_repair_result_keeps_the_delivery_goal_open(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t1",
                   "--set", json.dumps({"stage": "review", "goal": "close the selected issues",
                                        "next": "review the research"}))
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "host-turn-2",
            "--kind", "tasks", "--id", "t1", "--expect-rev", "1",
            "--set", json.dumps({"verdict": {"value": "repair", "why": "named repair remains"},
                                 "next": "seat the named repair"}))
        self.assertEqual(code, 0, out)
        task = self.doc()["state"]["tasks"]["t1"]
        self.assertEqual(task["goal"], "close the selected issues")
        self.assertEqual(task["next"], "seat the named repair")
        why = [row["why"] for row in json.loads(self.doc()["body"])["attention"] if row["id"] == "t1"]
        self.assertIn("delivery-open", why)

    def test_sideagent_idle_binding_is_not_a_missing_binding(self) -> None:
        self.init()
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertIn("no binding", out["sideagent_maintenance"])
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-node",
                                        "preset": "zcode/default", "state": "active", "mode": "node"}))
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertIn("idle binding is not missing", out["sideagent_maintenance"])

    def test_delegator_relay_tokens_and_a_prose_status_blocks_the_write(self) -> None:
        self.delegator.write_text(json.dumps({
            "project": {"goal": "close the selected issues"},
            "host": {"platform": "codex", "session": "codex-KT-host"},
            "authorization": {"elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus", "droid/core"],
                "count": 2, "class": "Elite",
            }]},
            "watch": {
                "relay-1": {"relay_status": "Pending the design note", "summary": "hand off"},
            },
        }), encoding="utf-8")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(out["result"], "blocked", out)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.delegator.write_text(json.dumps({
            "revision": 0,
            "project": {"goal": "close the selected issues"},
            "authorization": {"elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus", "droid/core"],
                "count": 2, "class": "Elite",
            }]},
            "watch": {"relay-1": {"kind": "relay", "status": "pending", "summary": "hand off",
                                  "next": "host adopts"}},
        }), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "host record", "--expect-revision", "0",
            "--set", json.dumps({"watch": {"relay-1": {"status": "adopted", "next": "repair seated",
                                                       "evidence": "host:tasks/t1"}}})])
        self.assertEqual(code, 0, out)
        self.assertNotIn("relay-1", json.loads(self.delegator.read_text())["watch"])

    def test_cleanup_keeps_pending_duties_and_does_not_delete_hash_copies(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["open-one"] = {
            "stage": "todo", "goal": "still open", "rev": 1, "writer": "host", "source": "s"}
        doc["state"]["recovery"] = {
            "legacy": {"protected_untracked": ["notes/local.txt"], "completion_evidence": "old prose"},
            "migration": {"raw": "heartbeat-prompt.v1-aaaaaaaaaaaa.json"},
        }
        doc["state"]["retired"] = [{
            "kind": "tasks", "id": "old", "outcome": "accepted", "at": "2026-10-05T00:00:00+00:00",
            "evidence": "do not keep this prose", "cite": {"path": "README.md", "locator": "README.md"},
        }]
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        stale = self.file.with_name("heartbeat-prompt.v1-aaaaaaaaaaaa.json")
        stale.write_text("unique-old-bytes", encoding="utf-8")
        code, out = self.state("backups", "--file", str(self.file))
        self.assertEqual(code, 0, out)
        self.assertFalse(out["deleted"])
        self.assertFalse(out["backups"][0]["trusted"])
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        state = self.doc()["state"]
        self.assertEqual(state["tasks"]["open-one"]["goal"], "still open")
        self.assertEqual(state["recovery"]["protected_untracked"], ["notes/local.txt"])
        self.assertNotIn("legacy", state["recovery"])
        self.assertFalse(state.get("retired"))
        self.assertIn("retired.tasks/old", out["removed"])
        self.assertEqual(stale.read_text(encoding="utf-8"), "unique-old-bytes")
        self.assertFalse(list(self.file.parent.glob("heartbeat-prompt.v2-*.json")))

    def test_malformed_hold_stays_visible_and_timer_mismatch_does_not_block_stop(self) -> None:
        self.init()
        self.file.write_text(json.dumps(self.doc()), encoding="utf-8")
        doc = self.doc()
        doc["state"]["holds"]["partial"] = {"reason": "unreadable hold", "rev": 1}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["holds"][0]["id"], "partial")
        code, timer = self.state(
            "timer", "--repo", str(self.repo), "--target", "local", "--entry", "/kaola-delegator",
            "--body", "not the locator")
        self.assertEqual(timer["result"], "mismatch")
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "owner stop",
            "--section", "project", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"stop": "owner stop now"}))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.doc()["state"]["project"]["stop"], "owner stop now")

    def test_v090_execute_reads_the_new_file_both_ways(self) -> None:
        auth = {

            "grants": [
                {"id": "codex/default", "state": "granted", "count": 1},
                {"id": "zcode/default", "state": "paused", "count": 1},
            ],

        }
        self.init(auth)
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t-live",
                   "--set", json.dumps({"stage": "doing", "goal": "keep the seat",
                                        "dispatch": ["i-hold"]}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "holds", "--id", "devin-west",
                   "--set", json.dumps({"preset": "codex/default", "scope": DEVIN_SCOPE,
                                        "owner": "host", "reason": "account"}))
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(self.repo.resolve()),
            "items": [
                {"item_id": "i-hold", "preset": "codex/default", "session": "codex-KT-i259-hold",
                 "prompt": "held", "task_id": "t-live"},
                {"item_id": "i-pause", "preset": "zcode/default", "session": "zcode-KT-i259-pause",
                 "prompt": "paused", "task_id": "t-live"},
                {"item_id": "i-missing", "preset": "zcode/default", "session": "zcode-KT-i259-miss",
                 "prompt": "missing", "task_id": "t-missing"},
            ],
        }), encoding="utf-8")
        direct = self.repo / "auth.json"
        direct.write_text(json.dumps(auth), encoding="utf-8")
        old = Path(self.tmp.name) / "v090-dispatch.py"
        old.write_bytes(subprocess.check_output(["git", "show", "v0.9.0:scripts/kaola-dispatch.py"]))
        current_auth = self.execute(DISPATCH, plan, self.file, None)
        current_state = self.execute(DISPATCH, plan, direct, self.file)
        old_auth = self.execute(old, plan, self.file, None)
        old_state = self.execute(old, plan, direct, self.file)
        for label, payload in (("current-auth", current_auth), ("current-state", current_state),
                               ("v090-auth", old_auth), ("v090-state", old_state)):
            self.assertEqual(payload["returncode"], 0, label)
        self.assertEqual(self.facts(current_auth), self.facts(old_auth))
        self.assertEqual(self.facts(current_state), self.facts(old_state))
        auth_facts = {row["item_id"]: row for row in self.facts(current_auth)}
        state_facts = {row["item_id"]: row for row in self.facts(current_state)}
        for item_id in ("i-hold", "i-pause", "i-missing"):
            self.assertEqual(auth_facts[item_id]["reason"], state_facts[item_id]["reason"])
            self.assertEqual(auth_facts[item_id]["holds"], state_facts[item_id]["holds"])
            self.assertEqual(auth_facts[item_id]["task_id"], state_facts[item_id]["task_id"])
        facts = state_facts
        self.assertEqual(facts["i-hold"]["reason"], "on-hold")
        self.assertEqual(facts["i-hold"]["holds"], ["devin-west"])
        self.assertEqual(facts["i-pause"]["reason"], "paused")
        self.assertIsNone(facts["i-pause"].get("task_note"))
        self.assertIn("t-missing", facts["i-missing"]["task_note"])
        previous = Path(self.tmp.name) / "previous-255-reader"
        previous.mkdir()
        for name in ("kaola-dispatch.py", "kaola-record-contract.py"):
            (previous / name).write_bytes(subprocess.check_output(["git", "show", f"1acf4b12:{'scripts/' + name}"], cwd=REPO))
        grouped = json.loads(self.file.read_text())
        grouped["state"]["authorization"] = {"grants": [{"preset_ids": ["droid/default", "droid/opus"],
                                                           "count": 2, "state": "granted"}]}
        self.file.write_text(json.dumps(grouped))
        sentinel = self.file.read_bytes()
        proc = subprocess.run([sys.executable, str(previous / "kaola-dispatch.py"), "project", "--authorization", str(self.file),
                               "--platforms", str(PLATFORMS)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("each grant needs a string id", proc.stdout)
        code, matching = run_dispatch(["project", "--authorization", str(self.file), "--platforms", str(PLATFORMS)])
        self.assertEqual(code, 0, matching)
        self.assertEqual(next(row for row in matching["candidates"] if row["id"] == "droid/opus")["count"], 2)
        self.assertEqual(self.file.read_bytes(), sentinel, "reader recovery never rewrites the grants")

    def test_delegator_ceiling_narrows_new_dispatch_and_keeps_a_live_row(self) -> None:
        auth = {

            "grants": [
                {"id": "codex/default", "state": "granted", "count": 1},
                {"id": "claude-code/default", "state": "granted", "count": 1},
                {"id": "droid/default", "state": "granted", "count": 4, "shared_seat": "droid"},
                {"id": "droid/opus", "state": "granted", "count": 4, "shared_seat": "droid"},
                {"id": "droid/core", "state": "granted", "count": 4, "shared_seat": "droid"},
            ],

        }
        self.init(auth)
        prompt = "keep the live seat"
        digest = "sha256:" + hashlib.sha256(prompt.encode()).hexdigest()
        plan = self.repo / "ceiling-plan.json"
        plan.write_text(json.dumps({
            "scope": "research", "repo": str(self.repo.resolve()),
            "items": [
                {"item_id": "live-codex", "preset": "codex/default", "session": "codex-live",
                 "prompt": prompt},
                {"item_id": "new-claude", "preset": "claude-code/default", "session": "claude-new",
                 "prompt": "outside the ceiling"},
                {"item_id": "third-droid", "preset": "droid/core", "session": "droid-c",
                 "prompt": "third shared seat"},
            ],
        }), encoding="utf-8")
        index = self.repo / ".kaola" / "dispatch-index.json"
        index.write_text(json.dumps({"schema": "kaola-dispatch-index/1", "items": [{
            "item_id": "live-codex", "preset": "codex/default", "session": "codex-live",
            "status": "in-flight", "holder_instance_id": "holder-live",
            "prompt_sha256": digest, "repo": str(self.repo.resolve()),
        }]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text(json.dumps({"rows": [
            {"preset": "droid/default", "session": "droid-a", "repo": str(self.repo.resolve()),
             "state": "running"},
            {"preset": "droid/opus", "session": "droid-b", "repo": str(self.repo.resolve()),
             "state": "running"},
        ]}), encoding="utf-8")
        base = ["execute", "--plan", str(plan), "--authorization", str(self.file),
                "--platforms", str(PLATFORMS), "--index", str(index), "--live", str(live), "--dry-run"]
        code, open_host = run_dispatch(base)
        self.assertEqual(code, 0, open_host)
        open_rows = {row["item_id"]: row for row in open_host["items"]}
        self.assertNotEqual(open_rows["new-claude"]["reason"], "above-ceiling")
        (self.repo / ".kaola" / "delegator-heartbeat.json").write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "authorization": {
                "elite_grants": [
                    {"preset_ids": ["droid/default", "droid/opus", "droid/core"], "count": 2},
                    {"preset_id": "codex/default", "count": 1, "state": "revoked"},
                ],

                "worker_pool": ["zcode/default"],

            },
        }), encoding="utf-8")
        code, limited = run_dispatch(base)
        self.assertEqual(code, 0, limited)
        self.assertNotIn("effective_cap", limited)
        rows = {row["item_id"]: row for row in limited["items"]}
        self.assertEqual(rows["new-claude"]["status"], "not-run")
        self.assertEqual(rows["new-claude"]["reason"], "above-ceiling")
        self.assertEqual(rows["third-droid"]["status"], "not-run")
        self.assertEqual(rows["third-droid"]["reason"], "shared-occupied")
        self.assertEqual(rows["live-codex"]["status"], "in-flight")
        self.assertEqual(rows["live-codex"]["evidence"]["pending_duty"], "stop")
        self.assertEqual(index.read_text(encoding="utf-8").count("live-codex"), 1)

    def test_ceiling_respects_live_pool_group_count_and_owner_limits(self) -> None:
        def rows(auth: dict, delegator_auth: dict, live_rows: list, items: list) -> dict:
            self.file.unlink(missing_ok=True)
            self.init(auth)
            (self.repo / ".kaola" / "delegator-heartbeat.json").write_text(json.dumps({
                "schema": "kaola-delegator-heartbeat/1",
                "authorization": delegator_auth,
            }), encoding="utf-8")
            plan = self.repo / "ceiling-plan.json"
            plan.write_text(json.dumps({
                "scope": "research", "repo": str(self.repo.resolve()), "items": items,
            }), encoding="utf-8")
            live = self.repo / "live.json"
            live.write_text(json.dumps({"rows": live_rows}), encoding="utf-8")
            code, out = run_dispatch([
                "execute", "--plan", str(plan), "--authorization", str(self.file),
                "--platforms", str(PLATFORMS), "--live", str(live), "--dry-run"])
            self.assertEqual(code, 0, out)
            return {row["item_id"]: row for row in out["items"]}

        classes = dict(CLASS_SENTENCES)
        pool = rows(
            { "grants": []},
            {"worker_pool": ["dsh/default", "zcode/default"],
             "elite_grants": []},
            [{"preset": "dsh/default", "platform": "dsh", "session": "dsh-existing",
              "repo": str(self.repo.resolve()), "state": "running"}],
            [{"item_id": "zcode-new", "preset": "zcode/default", "session": "zcode-new",
              "prompt": "new worker"}],
        )
        with self.subTest("default-worker-permission"):
            self.assertEqual(pool["zcode-new"]["status"], "not-run")
            self.assertEqual(pool["zcode-new"]["reason"], "dry-run")
            self.assertIn("argv", pool["zcode-new"])

        counted = rows(
            {  "grants": [
                {"id": "codex/default", "state": "granted"}]},
            {"worker_pool": [],  "elite_grants": [
                {"preset_id": "codex/default", "count": 1}]},
            [],
            [{"item_id": "codex-a", "preset": "codex/default", "session": "codex-a", "prompt": "one"},
             {"item_id": "codex-b", "preset": "codex/default", "session": "codex-b", "prompt": "two"}],
        )
        with self.subTest("missing-host-count"):
            self.assertEqual([counted["codex-a"]["reason"], counted["codex-b"]["reason"]], ["dry-run", "count"])

        grouped = rows(
            {  "grants": [
                {"id": "droid/default", "state": "granted", "count": 4},
                {"id": "droid/opus", "state": "granted", "count": 4},
                {"id": "droid/core", "state": "granted", "count": 4}]},
            {"worker_pool": [],  "elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus", "droid/core"],
                "count": 2, "switch_authorization": True}]},
            [{"preset": "droid/default", "platform": "droid", "session": "droid-existing-a",
              "repo": str(self.repo.resolve()), "state": "running"},
             {"preset": "droid/opus", "platform": "droid", "session": "droid-existing-b",
              "repo": str(self.repo.resolve()), "state": "running"}],
            [{"item_id": "droid-new", "preset": "droid/core", "session": "droid-new", "prompt": "third"}],
        )
        with self.subTest("grouped-count"):
            self.assertEqual(grouped["droid-new"]["status"], "not-run")
            self.assertEqual(grouped["droid-new"]["reason"], "shared-occupied")
            self.assertNotIn("argv", grouped["droid-new"])

        switched = rows(
            {   "grants": [
                {"id": "codex/default", "state": "granted", "count": 1, "model_switch": True}]},
            {"elite_grants": [{"preset_id": "codex/default", "count": 1, "switch_authorization": False}]},
            [],
            [{"item_id": "codex-switch", "preset": "codex/default", "session": "codex-switch",
              "prompt": "switch", "overrides": {"model": "gpt-other"}}],
        )
        with self.subTest("switch"):
            self.assertEqual(switched["codex-switch"]["reason"], "model-switch-unauthorized")

        limited = rows(
            {  "grants": [
                {"id": "codex/default", "state": "granted", "count": 1},
                {"id": "claude-code/default", "state": "granted", "count": 1}]},
            {"elite_grants": [
                {"preset_id": "codex/default", "count": 1, "special_requirements": {"effort": "max"}},
                {"preset_id": "claude-code/default", "count": 1, "special_requirements": "owner limit"},
            ]},
            [],
            [{"item_id": "codex-effort", "preset": "codex/default", "session": "codex-effort",
              "prompt": "effort", "overrides": {"effort": "low"}},
             {"item_id": "claude-text", "preset": "claude-code/default", "session": "claude-text",
              "prompt": "text"}],
        )
        with self.subTest("owner-limits"):
            self.assertEqual(limited["codex-effort"]["reason"], "override-conflicts-owner")
        self.assertEqual(limited["claude-text"]["reason"], "ceiling-incomplete")
        self.assertEqual(limited["claude-text"]["evidence"]["special_requirements"], "owner limit")
        self.assertEqual(limited["claude-text"]["evidence"]["presets"], ["claude-code/default"])
        self.assertEqual(limited["claude-text"]["evidence"]["source"], ".kaola/delegator-heartbeat.json")
        self.assertEqual(limited["claude-text"]["evidence"]["field"],
                         "authorization.elite_grants[1].special_requirements")
        self.assertEqual(limited["claude-text"]["evidence"]["role"], "host")
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["state"]["authorization"]["grants"], [
            {"id": "codex/default", "state": "granted", "count": 1},
            {"id": "claude-code/default", "state": "granted", "count": 1},
        ])

        lifetime = rows(
            {  "grants": [
                {"id": "codex/astra", "state": "granted", "count": 1, "lifetime": "standing"},
                {"id": "codex/default", "state": "granted", "count": 1}]},
            {"elite_grants": [
                {"preset_id": "codex/astra", "count": 1, "lifetime": "task"},
                {"preset_id": "codex/default", "count": 1, "lifetime": "until Friday"},
            ]},
            [],
            [{"item_id": "astra-task", "preset": "codex/astra", "session": "codex-astra", "prompt": "task"},
             {"item_id": "codex-prose", "preset": "codex/default", "session": "codex-prose", "prompt": "prose"}],
        )
        with self.subTest("lifetime"):
            self.assertEqual(lifetime["astra-task"]["reason"], "dry-run")
            self.assertEqual(lifetime["astra-task"]["evidence"]["lifetime"], "task")
        self.assertEqual(lifetime["codex-prose"]["reason"], "ceiling-incomplete")
        self.assertEqual(lifetime["codex-prose"]["evidence"]["lifetime"], "until Friday")
        self.assertEqual(lifetime["codex-prose"]["evidence"]["presets"], ["codex/default"])
        self.assertEqual(lifetime["codex-prose"]["evidence"]["role"], "host")
        self.assertNotIn("revoked", json.loads(self.file.read_text(encoding="utf-8"))["state"]["authorization"])

    def execute(self, script: Path, plan: Path, authorization: Path, state: Path | None) -> dict:
        argv = [PYTHON, str(script), "execute", "--plan", str(plan), "--authorization", str(authorization),
                "--platforms", str(PLATFORMS), "--dry-run"]
        if state is not None:
            argv.extend(["--state", str(state)])
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        try:
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError as exc:
            raise AssertionError(f"{script.name} not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc
        payload["returncode"] = proc.returncode
        payload["stderr"] = proc.stderr
        return payload

    def facts(self, payload: dict) -> list[dict]:
        rows = []
        for item in payload.get("items") or []:
            evidence = item.get("evidence") or {}
            rows.append({
                "item_id": item.get("item_id"),
                "reason": item.get("reason"),
                "holds": item.get("holds"),
                "task_id": item.get("task_id"),
                "task_note": (evidence.get("task_note") if isinstance(evidence, dict) else None),
            })
        return rows

    def test_v090_holder_injects_stored_body_and_the_new_holder_projects(self) -> None:
        self.init()
        doc = self.doc()
        doc["body"] = "STORED-BODY-SENTINEL"
        doc["state"]["tasks"]["t1"] = {
            "stage": "doing", "goal": "projected-goal-marker", "rev": 1, "writer": "host", "source": "s"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        old_path = Path(self.tmp.name) / "v090-holder.py"
        old_path.write_bytes(subprocess.check_output(["git", "show", "v0.9.0:scripts/kaola-acp-holder.py"]))
        old = load_module(old_path, "kpr_i259_v090_holder")
        old_body, old_defect = old.heartbeat_prompt_body(self.file)
        self.assertEqual((old_body, old_defect), ("STORED-BODY-SENTINEL", None))
        new = load_module(HOLDER, "kpr_i259_holder")
        new_body, new_defect = new.heartbeat_prompt_body(self.file)
        self.assertIsNone(new_defect)
        self.assertNotIn("STORED-BODY-SENTINEL", new_body or "")
        self.assertIn("projected-goal-marker", new_body or "")
        self.assertIn(CLASS_SENTENCES["Elite"], new_body or "")

    def test_a_migrate_note_is_not_a_seat_and_a_session_name_still_needs_live(self) -> None:
        self.init()
        note = "no in-flight seats (v1 note, stopped)"
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "migrate-note",
            "--kind", "tasks", "--id", "noted", "--set",
            json.dumps({"stage": "done", "goal": "close the note", "verdict": {"value": "accepted"},
                        "sessions": [note]}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "retire-note",
            "--kind", "tasks", "--id", "noted", "--expect-rev", "1", "--evidence", "note is not a seat",
            "--cite", CITE)
        self.assertEqual(code, 0, out)
        self.assertNotIn("noted", self.doc()["state"]["tasks"])
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "real-seat",
            "--kind", "tasks", "--id", "seated", "--set",
            json.dumps({"stage": "done", "goal": "close the seat", "verdict": {"value": "accepted"},
                        "sessions": ["codex-KT-real"]}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "retire-seat",
            "--kind", "tasks", "--id", "seated", "--expect-rev", "1", "--evidence", "needs the live row",
            "--cite", CITE)
        self.assertEqual(out["reason"], "retire-unmet", out)
        self.assertIn("--live", out["detail"])
        self.assertIn("seated", self.doc()["state"]["tasks"])

    def test_settled_task_and_retirement_leave_the_routine_view(self) -> None:
        """A node checkpoint must not return an already accepted task or its
        retirement as maintenance-returned, and that stopped row leaves the view."""
        self.init()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
            "--section", "sideagent", "--expect-revision", "1", "--set",
            json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "design",
            "--kind", "tasks", "--id", "design-1", "--set",
            json.dumps({"stage": "done", "goal": "stopped design row", "verdict": {"value": "accepted"}}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "host-retire",
            "--kind", "tasks", "--id", "design-1", "--expect-rev", "1",
            "--evidence", "accepted design row", "--cite", CITE)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["cite"]["path"], "README.md")
        self.assertFalse(self.doc()["state"].get("retired"))
        ident = "host:tasks/design-1@1"
        doc = self.doc()
        doc["state"].setdefault("alerts", {})["maintenance-returned"] = {
            "level": "warn", "owner": "host", "summary": "1 maintenance input(s) not applied by a node",
            "inputs": {ident: {"why": "is not a retirement by this node", "batch": "old"},
                       "host:tasks/design-1@1": {"why": "not-in-batch", "batch": "old"}},
            "rev": 1, "source": "old", "writer": "sideagent", "writer_holder": "node-0"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, pending = self.state("view", "--file", str(self.file), "--role", "sideagent")
        self.assertEqual(code, 0, pending)
        entries = []
        for item in pending["pending_host_changes"]:
            if "design-1" in item:
                entries.append({"input": item, "applied": ["retired:tasks/design-1"]})
            elif item.startswith("host:section/"):
                name = item.split("/", 2)[1].split("@", 1)[0]
                entries.append({"input": item, "retained": f"section/{name}"})
            else:
                body = item[len("host:"):].split("@", 1)[0]
                entries.append({"input": item, "retained": body})
        entries.append({"input": "host:tasks/design-1@1", "applied": ["retired:tasks/design-1"]})
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({
            "holder_instance_id": "node-1", "platform": "zcode", "repo": str(self.repo),
            "session": "zcode-KT-sideagent"})
        code, out = run_dispatch([
            "state", "checkpoint", "--file", str(self.file), "--writer", "sideagent",
            "--source", "b-settled", "--batch", "b-settled",
            "--through-host-revision", str(self.doc()["host_revision"]),
            "--entries", json.dumps(entries)], env)
        self.assertEqual(code, 0, out)
        returned = out["value"]["returned_to_host"]
        self.assertFalse([key for key in returned if "design-1" in key], returned)
        self.assertNotIn("maintenance-returned", self.doc()["state"].get("alerts") or {})
        view = json.loads(self.doc()["body"])
        self.assertNotIn("design-1", [row.get("id") for row in view.get("tasks") or []])
        self.assertNotIn("design-1", json.dumps(view.get("alerts")))
        self.assertNotIn("maintenance-returned", [row.get("id") for row in view.get("attention") or []])

    def test_delegator_migration_keeps_duties_and_blocks_unmapped_text(self) -> None:
        self.delegator.write_text(json.dumps({
            "revision": 2,
            "project": {"goal": "close the selected issues", "user_language": "zh"},
            "host": {"platform": "codex", "session": "codex-KT-host"},
            "day_start": {"action": "reconcile_then_open_intake", "state": "pending", "evidence": "owner-day"},
            "day_end": {"action": "pause_new_claims_keep_inflight", "state": "confirmed",
                        "host_ack": "host-ack", "claim_check": "none"},
            "final_stop": "stop at the owner boundary",
            "authorization": {"elite_grants": [{
                "preset_ids": ["droid/default", "droid/opus"], "count": 2, "class": "Elite",
                "lifetime": "task", "special_requirements": "owner limit",
            }]},
            "watch": {"relay-1": {
                "kind": "relay", "status": "pending", "summary": "owner constraint",
                "detail": "pending relay text", "evidence": "owner msg 3", "next": "host adopts",
                "report": {},
            }},
        }), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual((code, out["result"]), (0, "migrated"), out)
        doc = json.loads(self.delegator.read_text(encoding="utf-8"))
        self.assertEqual(doc["project"]["user_language"], "zh")
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertEqual(view["project"]["user_language"], "zh")
        self.assertEqual(doc["day_start"]["evidence"], "owner-day")
        self.assertEqual(doc["day_end"]["host_ack"], "host-ack")
        self.assertEqual(doc["final_stop"], "stop at the owner boundary")
        self.assertEqual(doc["authorization"]["elite_grants"][0]["special_requirements"], "owner limit")
        self.assertEqual(doc["watch"]["relay-1"]["detail"], "pending relay text")
        self.assertIn("watch.relay-1.report", out["dropped"])
        self.delegator.write_text(json.dumps({
            "revision": 1,
            "watch": {"relay-1": {"kind": "relay", "status": "pending", "narrative": "unmapped owner text",
                                  "next": "deliver"}},
        }), encoding="utf-8")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator)])
        self.assertEqual(out["result"], "blocked", out)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.assertTrue(any("narrative" in item.get("path", "") for item in out["blockers"]))

    def test_delegator_update_and_view_are_closed(self) -> None:
        self.delegator.write_text(json.dumps({
            "revision": 0, "project": {"goal": "close the selected issues"},
            "authorization": {"elite_grants": [{"preset_ids": ["droid/default"], "count": 2, "class": "Elite"}]},
            "watch": {"relay-1": {"kind": "relay", "status": "pending", "summary": "text", "next": "send"}},
        }), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 0, out)
        self.assertNotIn("user_language", json.loads(self.delegator.read_text(encoding="utf-8"))["project"])
        revision = json.loads(self.delegator.read_text(encoding="utf-8"))["revision"]
        before = self.delegator.read_bytes()
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "s", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-2": {"kind": "journal", "status": "Pending note"}}})])
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.delegator.read_bytes(), before)
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "s", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-1": {"status": "adopted", "next": "done"}}})])
        self.assertNotEqual(code, 0, out)
        self.assertIn("evidence", out["detail"])
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "s", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-1": {"status": "sent", "next": "wait for host"}}})])
        self.assertEqual(code, 0, out)
        revision = json.loads(self.delegator.read_text(encoding="utf-8"))["revision"]
        code, out = run_dispatch([
            "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
            "--source", "host record", "--expect-revision", str(revision),
            "--set", json.dumps({"watch": {"relay-1": {"status": "adopted", "evidence": "host:tasks/t1"}}})])
        self.assertEqual(code, 0, out)
        doc = json.loads(self.delegator.read_text(encoding="utf-8"))
        doc["authorization"]["secret_grant"] = "no"
        doc["journal"] = ["hand"]
        self.delegator.write_text(json.dumps(doc), encoding="utf-8")
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertEqual(code, 0, view)
        self.assertNotIn("secret_grant", json.dumps(view["authorization"]))
        self.assertTrue(any(item["path"] == "authorization.secret_grant" for item in view["unknown"]))
        self.assertTrue(any(item["path"] == "journal" for item in view["unknown"]))

    def test_delegator_authorization_shapes_agree_and_refuse_without_writes(self) -> None:
        dispatch = load_module(DISPATCH, "kpr_repair_shapes")
        base = {"schema": "kaola-delegator-heartbeat/1", "revision": 0,
                "authorization": {"worker_pool": ["zcode/default"], "elite_grants": [
                                      {"preset_id": "codex/default", "count": 1},
                                      {"preset_id": "claude-code/default", "count": 1}]},
                "watch": {"relay": {"kind": "relay", "status": "pending", "detail": "owner condition", "next": "deliver"}}}
        cases = [({"worker_pool_cap": "owner condition"}, "authorization.worker_pool_cap", "Worker"),
                 ({"elite_cap": True}, "authorization.elite_cap", "Elite"),
                 ({"revoked": "codex/default"}, "authorization.revoked", "all"),
                 ({"paused": {}}, "authorization.paused", "all"),
                 ({"exclusions": [True]}, "authorization.exclusions", "all"),
                 ({"elite_grants": [None]}, "authorization.elite_grants[0]", "Elite")]
        for field, value in (("count", True), ("count", -1), ("switch_authorization", "only at owner boundary"),
                             ("preset_ids", "codex/default")):
            grant = {"preset_id": "codex/default", "count": 1, field: value}
            cases.append(({"elite_grants": [grant, {"preset_id": "claude-code/default", "count": 1}]},
                          f"authorization.elite_grants[0].{field}", "codex"))
        for patch, path, scope in cases:
            with self.subTest(path=path):
                self.delegator.write_text(json.dumps(base), encoding="utf-8")
                before = self.delegator.read_bytes()
                code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator),
                                          "--writer", "delegator", "--source", "owner", "--expect-revision", "0",
                                          "--set", json.dumps({"authorization": patch})])
                self.assertEqual(code, 2, out)
                self.assertEqual(self.delegator.read_bytes(), before)
                self.assertIn(path, [error["path"] for error in out["blockers"]])
                doc = json.loads(json.dumps(base))
                doc["authorization"].update(patch)
                self.delegator.write_text(json.dumps(doc), encoding="utf-8")
                before = self.delegator.read_bytes()
                code, migration = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
                self.assertEqual(code, 2, migration)
                self.assertEqual(self.delegator.read_bytes(), before)
                self.assertIn(path, [error["path"] for error in migration["blockers"]])
                ceiling, error = dispatch.delegator_ceiling(str(self.repo))
                if scope == "all":
                    self.assertEqual(error["path"], path)
                else:
                    self.assertIsNone(error)
                    preset = "zcode/default" if scope == "Worker" else "codex/default"
                    self.assertEqual(dispatch.ceiling_block(ceiling, preset, "Worker" if scope == "Worker" else "Elite"),
                                     "ceiling-unreadable")
                    evidence = (ceiling["problem_evidence"].get(preset)
                                or ceiling.get("worker_problem" if scope == "Worker" else "elite_problem"))
                    self.assertEqual(evidence["path"], path)
                    self.assertIn("allowed", evidence)
                    self.assertIn("recovery", evidence)
                    unaffected = ("zcode/default", "Worker") if scope == "Elite" else ("claude-code/default", "Elite")
                    self.assertIsNone(dispatch.ceiling_block(ceiling, *unaffected))
                self.assertEqual(json.loads(self.delegator.read_text())["watch"]["relay"]["detail"], "owner condition")

    def test_bad_grant_keeps_inflight_duty_and_unrelated_dispatch(self) -> None:
        self.init({  "grants": [
            {"id": "codex/default", "state": "granted", "count": 1},
            {"id": "claude-code/default", "state": "granted", "count": 1}]})
        prompt = "continue assigned work"
        index = self.repo / "index.json"
        index.write_text(json.dumps({"items": [{"item_id": "live", "preset": "codex/default", "session": "codex-live",
                                                "status": "in-flight", "holder_instance_id": "own-holder",
                                                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                                                "repo": str(self.repo)}]}), encoding="utf-8")
        plan = self.repo / "plan.json"
        plan.write_text(json.dumps({"repo": str(self.repo), "scope": "qa", "mutation": False, "items": [
            {"item_id": "live", "preset": "codex/default", "session": "codex-live", "prompt": prompt},
            {"item_id": "new", "preset": "claude-code/default", "session": "claude-new", "prompt": "inspect"}]}), encoding="utf-8")
        live = self.repo / "live.json"
        live.write_text('{"rows": []}', encoding="utf-8")
        args = ["execute", "--plan", str(plan), "--authorization", str(self.file), "--platforms", str(PLATFORMS),
                "--index", str(index), "--live", str(live), "--dry-run"]
        # The untyped file reports migration without a new legacy transport gate.
        self.delegator.write_text('{"authorization": {}}', encoding="utf-8")
        code, old = run_dispatch(args)
        self.assertEqual(code, 0, old)
        self.assertEqual(old["observations"][0]["code"], "delegator-migration-needed")
        self.delegator.write_text(json.dumps({"schema": "kaola-delegator-heartbeat/1", "authorization": {
            "elite_grants": [{"preset_id": "codex/default", "count": 1, "switch_authorization": "owner condition"},
                             {"preset_id": "claude-code/default", "count": 1}]}}), encoding="utf-8")
        code, out = run_dispatch(args)
        self.assertEqual(code, 0, out)
        rows = {row["item_id"]: row for row in out["items"]}
        self.assertEqual(rows["live"]["status"], "in-flight")
        self.assertEqual(rows["live"]["holder_instance_id"], "own-holder")
        self.assertEqual(rows["live"]["evidence"]["pending_duty"], "reclaim")
        self.assertEqual(rows["new"]["reason"], "dry-run")
        self.assertIn("argv", rows["new"])

    def test_pending_legacy_text_requires_rehome_and_normal_update_removes_settled_bags(self) -> None:
        for field in ("latest_owner_change", "latest", "report"):
            with self.subTest(field=field):
                doc = {"schema": "kaola-delegator-heartbeat/1", "revision": 0,
                       "watch": {"r": {"kind": "relay", "status": "pending", "next": "deliver", field: "unique owner text"}}}
                self.delegator.write_text(json.dumps(doc), encoding="utf-8")
                before = self.delegator.read_bytes()
                for args in (["migrate", "--write"], ["update", "--writer", "delegator", "--source", "owner",
                                                     "--expect-revision", "0", "--set", '{"project":{"goal":"ship"}}']):
                    code, out = run_dispatch(["delegator", *args, "--file", str(self.delegator)])
                    self.assertEqual(code, 2, out)
                    self.assertEqual(self.delegator.read_bytes(), before)
                    self.assertIn(f"watch.r.{field}", [item["path"] for item in out["blockers"]])
                code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                                          "--source", "owner", "--expect-revision", "0", "--set",
                                          json.dumps({"watch": {"r": {field: None, "detail": "unique owner text"}}})])
                self.assertEqual(code, 0, out)
                self.assertEqual(json.loads(self.delegator.read_text())["watch"]["r"]["detail"], "unique owner text")
        self.delegator.write_text(json.dumps({"schema": "kaola-delegator-heartbeat/1", "revision": 0,
                                               "watch": {"latest": {"status": "adopted", "report": "unique owner text"}}}),
                                  encoding="utf-8")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                                  "--source", "owner", "--expect-revision", "0", "--set", '{"project":{"goal":"ship"}}'])
        self.assertEqual(code, 2, out)
        self.assertEqual(self.delegator.read_bytes(), before)
        doc = {"schema": "kaola-delegator-heartbeat/1", "revision": 0, "watch": {
            "r": {"status": "adopted", "evidence": "host:tasks/current", "report": {"past": True}},
            "latest": {"status": "settled", "evidence": "original-settlement", "report": "past text"}}}
        self.delegator.write_text(json.dumps(doc), encoding="utf-8")
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertNotIn("past text", json.dumps(view))
        self.assertNotIn("latest", [item["id"] for item in view["watch"]])
        code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                                  "--source", "owner", "--expect-revision", "0", "--set", '{"project":{"goal":"ship"}}'])
        self.assertEqual(code, 0, out)
        doc = json.loads(self.delegator.read_text())
        self.assertNotIn("r", doc["watch"])
        self.assertNotIn("latest", doc["watch"])
        self.assertEqual(doc["watch"], {})
        before = self.delegator.read_bytes()
        for _ in range(2):
            code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
            self.assertEqual(code, 0, out)
            self.assertEqual(self.delegator.read_bytes(), before)

    def test_watch_alias_text_stays_blocked_when_status_is_added(self) -> None:
        for alias in ("relay_status", "relay", "state"):
            for has_status in (False, True):
                with self.subTest(alias=alias, has_status=has_status):
                    text = f"Owner condition in {alias}: keep the repair pending."
                    duty = {"kind": "relay", alias: text, "source": "owner-message-7",
                            "summary": "deliver the repair", "next": "Host adopts"}
                    if has_status:
                        duty["status"] = "open"
                    doc = {"schema": "kaola-delegator-heartbeat/1", "revision": 7,
                           "source": "owner-message-7", "watch": {"repair": duty},
                           "authorization": { "elite_grants": [{
                               "preset_ids": ["droid/default", "droid/opus", "droid/core"],
                               "count": 2, "class": "Elite"}]}}
                    self.delegator.write_text(json.dumps(doc), encoding="utf-8")
                    before = self.delegator.read_bytes()
                    for args in (["migrate", "--write"],
                                 ["update", "--writer", "delegator", "--source", "owner-message-7",
                                  "--expect-revision", "7", "--set", '{"watch":{"repair":{"status":"open"}}}']):
                        code, out = run_dispatch(["delegator", *args, "--file", str(self.delegator)])
                        self.assertEqual(code, 2, out)
                        self.assertEqual(self.delegator.read_bytes(), before)
                        problem = next(row for row in out["blockers"]
                                       if row["path"] == f"watch.repair.{alias}")
                        self.assertIn("watch/repair", problem["recovery"])
                        self.assertIn("--expect-revision 7", problem["recovery"])
                        self.assertIn("current decision/reconciliation route", problem["recovery"])
                        self.assertNotIn("rehome", problem["recovery"])
                    code, out = run_dispatch([
                        "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                        "--source", "owner-message-7", "--expect-revision", "7", "--set",
                        json.dumps({"watch": {"repair": {alias: None, "status": "open",
                                                         "evidence": "owner-message-7"}}})])
                    self.assertEqual(code, 0, out)
                    saved = json.loads(self.delegator.read_text())
                    self.assertEqual(saved["watch"]["repair"]["evidence"], "owner-message-7")
                    self.assertEqual(saved["watch"]["repair"]["source"], duty["source"])
                    self.assertEqual(saved["source"], doc["source"])
                    self.assertEqual(saved["authorization"], doc["authorization"])

        # Each non-token alias needs its own path, also with a valid status.
        self.delegator.write_text(json.dumps({"revision": 0, "watch": {"repair": {
            "kind": "relay", "status": "open", "relay_status": "owner condition",
            "relay": {"condition": "not a token"}, "state": 3}}}), encoding="utf-8")
        before = self.delegator.read_bytes()
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 2, out)
        self.assertEqual(self.delegator.read_bytes(), before)
        self.assertEqual({row["path"] for row in out["blockers"]},
                         {"watch.repair.relay_status", "watch.repair.relay", "watch.repair.state"})

    def test_watch_alias_tokens_keep_pending_data_and_status_precedence(self) -> None:
        record = load_module(REPO / "scripts" / "kaola-record-contract.py", "kpr_i259_aliases")
        for alias in ("relay_status", "relay", "state"):
            for token in ("pending", "sent", "adopted", "open", "settled", "blocked"):
                for has_status in (False, True):
                    with self.subTest(alias=alias, token=token, has_status=has_status):
                        duty = {alias: token, "source": "owner-message-7", "summary": "pending repair",
                                "detail": "keep the owner condition", "next": "Host adopts",
                                "evidence": "host:tasks/repair"}
                        if has_status:
                            duty["status"] = "open"
                        normalized, blockers, _ = record.delegator_migrated({"watch": {"repair": duty}})
                        self.assertFalse(blockers)
                        if not has_status and token in ("adopted", "settled"):
                            self.assertNotIn("repair", normalized["watch"])
                            continue
                        kept = normalized["watch"]["repair"]
                        self.assertEqual(kept["status"], "open" if has_status else token)
                        for field in ("source", "summary", "detail", "next", "evidence"):
                            self.assertEqual(kept[field], duty[field])

    def test_release_named_typed_duty_is_preserved_with_adoption_guards(self) -> None:
        for status in ("pending", "sent", "open", "blocked", "adopted", "settled"):
            with self.subTest(status=status):
                duty = {"kind": "recovery", "status": status, "source": "owner-release",
                        "summary": "release remains a current duty", "next": "Host judges readiness",
                        "evidence": "host:tasks/release"}
                self.delegator.write_text(json.dumps({"revision": 0, "watch": {
                    "release": duty, "repair": {"kind": "relay", "status": "pending", "next": "deliver"}}}),
                    encoding="utf-8")
                code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
                self.assertEqual(code, 0, out)
                self.assertEqual("watch.release" in out["dropped"], status in ("adopted", "settled"))
                code, out = run_dispatch([
                    "delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                    "--source", "owner-release", "--expect-revision", "0", "--set", '{"project":{"goal":"ship"}}'])
                self.assertEqual(code, 0, out)
                saved = json.loads(self.delegator.read_text())
                if status in ("adopted", "settled"):
                    self.assertNotIn("release", saved["watch"])
                else:
                    self.assertEqual(saved["watch"]["release"], duty)
                self.assertEqual(saved["watch"]["repair"]["status"], "pending")
                code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
                self.assertEqual(code, 0, view)
                shown = [row for row in view["watch"] if row["id"] == "release"]
                self.assertEqual(shown, [] if status in ("adopted", "settled") else [{"id": "release", **duty}])
                before = self.delegator.read_bytes()
                code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
                self.assertEqual(code, 0, out)
                self.assertEqual(self.delegator.read_bytes(), before)
        for duty in ({"report": "unmapped owner condition"},
                     {"kind": "relay", "status": "adopted", "summary": "not proven adopted"}):
            self.delegator.write_text(json.dumps({"revision": 0, "watch": {"release": duty}}), encoding="utf-8")
            before = self.delegator.read_bytes()
            code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
            self.assertEqual(code, 2, out)
            self.assertEqual(self.delegator.read_bytes(), before)
            self.assertTrue(any(row["path"].startswith("watch.release") for row in out["blockers"]))

    def test_delegator_view_keeps_current_closed_operating_fields(self) -> None:
        fields = {
            "stop": {"boundary": "owner boundary", "state": "pending", "evidence": "owner-stop"},
            "cadence": {"timezone": "Asia/Taipei", "start_local": "09:00", "end_local": "18:00",
                        "interval_minutes": 5},
            "entry": {"skill": "kaola-delegator", "target": "device-local", "timer_template": "canonical"},
            "timer_owner": {"platform": "codex", "native_timer_id": "timer-7", "state": "active"},
            "source": "owner-message-7",
        }
        self.delegator.write_text(json.dumps({"revision": 0, **fields}), encoding="utf-8")
        code, out = run_dispatch(["delegator", "migrate", "--file", str(self.delegator), "--write"])
        self.assertEqual(code, 0, out)
        before = self.delegator.read_bytes()
        code, view = run_dispatch(["delegator", "view", "--file", str(self.delegator)])
        self.assertEqual(code, 0, view)
        self.assertEqual(self.delegator.read_bytes(), before)
        for key, value in fields.items():
            self.assertEqual(view[key], value)
        record = load_module(REPO / "scripts" / "kaola-record-contract.py", "kpr_i259_view_fields")
        self.assertEqual(record.delegator_file_view({"stop": "owner boundary"})["stop"], "owner boundary")
        malformed = json.loads(json.dumps(fields))
        for key in ("stop", "cadence", "entry", "timer_owner"):
            malformed[key]["raw"] = {"history": "PRIVATE-UNMAPPED-TEXT"}
        malformed["cadence"]["interval_minutes"] = True
        malformed["entry"]["target"] = ["PRIVATE-UNMAPPED-TEXT"]
        malformed["source"] = {"history": "PRIVATE-UNMAPPED-TEXT"}
        view = record.delegator_file_view(malformed)
        self.assertNotIn("PRIVATE-UNMAPPED-TEXT", json.dumps(view))
        self.assertNotIn("interval_minutes", view["cadence"])
        self.assertNotIn("target", view["entry"])
        self.assertNotIn("source", view)
        self.assertEqual({row["path"] for row in view["unknown"]},
                         {"stop.raw", "cadence.raw", "entry.raw", "timer_owner.raw",
                          "cadence.interval_minutes", "entry.target", "source"})

    def test_capability_summary_closure_refuses_writes_and_keeps_legacy_duties(self) -> None:
        self.init({"grants": [{"id": "droid/opus", "count": 2, "shared_seat": "droid", "state": "granted"}]})
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner-7",
                               "--kind", "tasks", "--id", "repair", "--set",
                               json.dumps({"stage": "doing", "goal": "apply repair", "wait": "owner condition",
                                           "next": "Host judges"}))
        self.assertEqual(code, 0, out)
        original = self.doc()
        before = self.file.read_bytes()
        for key, value in (("text", "UNMAPPED-OWNER-CONDITION"),
                           ("notes", {"condition": "UNMAPPED-OWNER-CONDITION"})):
            with self.subTest(key=key):
                code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "owner-7",
                                       "--section", "authorization", "--expect-revision", str(original["revision"]), "--set",
                                       json.dumps({"capability_summary": {key: value}}))
                self.assertEqual(code, 2, out)
                self.assertEqual(out["path"], "authorization.capability_summary")
                self.assertIn("rehome", out["recovery"])
                self.assertEqual(self.file.read_bytes(), before)
                legacy = json.loads(json.dumps(original))
                legacy["state"]["authorization"]["capability_summary"] = {"presets": ["droid/opus"], key: value}
                self.file.write_text(json.dumps(legacy), encoding="utf-8")
                sentinel = self.file.read_bytes()
                code, view = self.state("view", "--file", str(self.file), "--role", "host")
                self.assertEqual(code, 0, view)
                self.assertEqual(self.file.read_bytes(), sentinel)
                self.assertIn(f"state.authorization.capability_summary.{key}",
                              [row["path"] for row in view["unknown"]])
                self.assertNotIn("UNMAPPED-OWNER-CONDITION", json.dumps(view))
                self.assertEqual(view["authorization"]["grants"], original["state"]["authorization"]["grants"])
                self.assertIn("unknown", view["capability"])
                self.assertEqual(next(task for task in view["tasks"] if task["id"] == "repair")["wait"],
                                 "owner condition")
                for write in (False, True):
                    code, out = self.state("migrate", "--file", str(self.file), *(["--write"] if write else []))
                    self.assertEqual(code, 2, out)
                    self.assertFalse(out["writes"])
                    self.assertIn("authorization.capability_summary",
                                  [row["path"] for row in out["blockers"]])
                    self.assertEqual(self.file.read_bytes(), sentinel)
                # Restore only this test fixture; no product mapping is inferred.
                self.file.write_bytes(before)
        code, out = self.state("migrate", "--file", str(self.file))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "current")
        self.assertEqual(self.file.read_bytes(), before)

    def test_shared_skeleton_uses_owner_count_without_a_project_grant(self) -> None:
        text = (REPO / "templates/orchestrator/references/heartbeat-skeleton.txt").read_text()
        example = json.loads(next(line.removeprefix("例：") for line in text.splitlines() if line.startswith("例：")))
        contract = load_module(REPO / "scripts/kaola-record-contract.py", "skeleton_contract_955")
        auth = example["authorization"]
        self.assertEqual(contract.authorization_blockers(auth), [])
        self.assertEqual(auth["grants"][0]["count"], 2)
        self.assertEqual(auth["grants"][0]["preset_ids"], ["droid/default", "droid/opus", "droid/core"])
        self.assertFalse(auth["grants"][0]["model_switch"])
        self.assertNotIn("elite_cap", auth)
        self.assertNotIn("classes", auth)

    def test_delegator_open_nested_bags_refuse_without_writes(self) -> None:
        for patch, path in [({"entry": {"report": {"past": True}}}, "entry.report"),
                            ({"timer_owner": {"raw": []}}, "timer_owner.raw"),
                            ({"source": {"history": "past"}}, "source"),
                            ({"authorization": {"sideagent": {"report": "past"}}}, "authorization.sideagent.report")]:
            with self.subTest(path=path):
                self.delegator.write_text('{"schema":"kaola-delegator-heartbeat/1","revision":0}', encoding="utf-8")
                before = self.delegator.read_bytes()
                code, out = run_dispatch(["delegator", "update", "--file", str(self.delegator), "--writer", "delegator",
                                          "--source", "owner", "--expect-revision", "0", "--set", json.dumps(patch)])
                self.assertEqual(code, 2, out)
                self.assertEqual(self.delegator.read_bytes(), before)
                self.assertIn(path, [item["path"] for item in out["blockers"]])

    def test_retire_mirrors_original_verdict_without_hiding_open_dispatch(self) -> None:
        self.init()
        index = self.repo / "index.json"
        live = self.repo / "live.json"
        live.write_text('{"rows": []}', encoding="utf-8")
        rows = [{"item_id": "closed", "task_id": "done", "status": "returned", "acceptance": "pending"},
                {"item_id": "open", "task_id": "done", "status": "in-flight", "acceptance": "accepted"},
                {"item_id": "unknown", "task_id": "done", "status": "unknown"},
                {"item_id": "unaccepted", "task_id": "missing", "status": "returned", "acceptance": "pending"},
                {"item_id": "bad-acceptance", "task_id": "missing", "status": "returned", "acceptance": "unreadable"}]
        index.write_text(json.dumps({"items": rows}), encoding="utf-8")
        code, out = self.state("update", "--file", str(self.file), "--writer", "host", "--source", "accepted",
                               "--kind", "tasks", "--id", "done", "--set",
                               json.dumps({"stage": "done", "goal": "deliver the accepted result",
                                           "verdict": {"value": "accepted"}, "dispatch": ["closed"]}))
        self.assertEqual(code, 0, out)
        original = self.doc()["state"]["tasks"]["done"]
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host", "--source", "accepted",
                               "--kind", "tasks", "--id", "done", "--expect-rev", "1", "--evidence", "stopped and accepted",
                               "--cite", CITE, "--index", str(index), "--live", str(live))
        self.assertEqual(code, 0, out)
        after = {row["item_id"]: row for row in json.loads(index.read_text())["items"]}
        self.assertEqual(after["closed"]["acceptance"], "accepted")
        self.assertEqual(after["closed"]["acceptance_source"]["task_rev"], original["rev"])
        self.assertEqual(after["closed"]["acceptance_source"]["host_revision"], original["host_revision"])
        for row in rows[1:]:
            self.assertEqual(after[row["item_id"]], row)
        self.assertFalse(self.doc()["state"].get("retired"))
        code, out = self.state("check", "--file", str(self.file), "--index", str(index))
        missing = {row["id"] for row in out["problems"] if row["code"] == "dispatch-task-missing"}
        self.assertEqual(missing, {"open", "unknown", "unaccepted", "bad-acceptance"})

        # A settled continuation can differ from the initial prompt. The
        # Host disposition and exact reclaim settle the duty, not collect.
        item = {"item_id": "initial", "task_id": "continued", "status": "unknown",
                "reason": "fingerprint-differs", "acceptance": "pending",
                "session": "codex-KT-continued", "holder_instance_id": "worker-1",
                "platform": "codex", "repo": str(self.repo),
                "evidence": {"collect_status": {"holder_instance_id": "worker-1",
                    "repo": str(self.repo), "mutation_status": "completed", "outcome": "stopped"}}}
        stopped = {"session": item["session"], "holder_instance_id": "worker-1",
                   "platform": "codex", "repo": str(self.repo), "state": "stopped"}
        code, out = self.state("update", "--file", str(self.file), "--writer", "host",
                               "--source", "original result and continuation custody",
                               "--kind", "tasks", "--id", "continued", "--set", json.dumps({
                                   "stage": "done", "goal": "settled research", "dispatch": ["initial"],
                                   "verdict": {"value": "accepted"},
                                   "dispositions": {"initial": "accepted"}}))
        self.assertEqual(code, 0, out)
        baseline = self.file.read_bytes()
        for change in ("no-disposition", "in-flight", "unknown-effect", "foreign-holder",
                       "foreign-repo", "wrong-task", "unrelated-unknown", "missing-stop", "live",
                       "missing-repo", "foreign-collected-holder", "sideagent"):
            with self.subTest(change=change):
                self.file.write_bytes(baseline)
                doc = self.doc()
                candidate = json.loads(json.dumps(item))
                current_live = dict(stopped)
                if change == "no-disposition":
                    doc["state"]["tasks"]["continued"].pop("dispositions")
                elif change == "in-flight":
                    candidate["status"] = "in-flight"
                elif change == "unknown-effect":
                    candidate["evidence"]["collect_status"]["mutation_status"] = "unknown"
                elif change == "foreign-holder":
                    current_live["holder_instance_id"] = "foreign"
                elif change == "foreign-repo":
                    current_live["repo"] = str(self.repo / "foreign")
                elif change == "wrong-task":
                    candidate["task_id"] = "another"
                elif change == "unrelated-unknown":
                    candidate["reason"] = "holder-mismatch"
                elif change == "live":
                    current_live["state"] = "running"
                elif change == "missing-repo":
                    current_live.pop("repo")
                elif change == "foreign-collected-holder":
                    candidate["evidence"]["collect_status"]["holder_instance_id"] = "foreign"
                self.file.write_text(json.dumps(doc), encoding="utf-8")
                index.write_text(json.dumps({"items": [candidate]}), encoding="utf-8")
                live.write_text(json.dumps({"rows": [] if change == "missing-stop" else [current_live]}),
                                encoding="utf-8")
                before_state, before_index = self.file.read_bytes(), index.read_bytes()
                code, out = self.state("retire", "--file", str(self.file), "--writer",
                    "sideagent" if change == "sideagent" else "host",
                    "--source", "original accepted continuation and exact reclaim",
                    "--kind", "tasks", "--id", "continued", "--expect-rev", "1",
                    "--evidence", "original Host result, custody and exact stop", "--cite", CITE,
                    "--index", str(index), "--live", str(live))
                self.assertEqual(code, 2, out)
                self.assertEqual(out["reason"], "retire-unmet", out)
                self.assertEqual(self.file.read_bytes(), before_state)
                self.assertEqual(index.read_bytes(), before_index)
        self.file.write_bytes(baseline)
        index.write_text(json.dumps({"items": [item]}), encoding="utf-8")
        live.write_text(json.dumps({"rows": [stopped]}), encoding="utf-8")
        before_index = index.read_bytes()
        code, out = self.state("retire", "--file", str(self.file), "--writer", "host",
            "--source", "original accepted continuation and exact reclaim",
            "--kind", "tasks", "--id", "continued", "--expect-rev", "1",
            "--evidence", "original Host result, custody and exact stop", "--cite", CITE,
            "--index", str(index), "--live", str(live))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["reconciled_dispatch"][0]["item_id"], "initial")
        self.assertEqual(out["value"]["reconciled_dispatch"][0]["collect_status"], "unknown")
        self.assertEqual(index.read_bytes(), before_index)
        self.assertNotIn("continued", self.doc()["state"]["tasks"])
        self.assertFalse(self.doc()["state"].get("retired"))
        for role in ("host", "sideagent", "delegator"):
            code, view = self.state("view", "--file", str(self.file), "--role", role)
            self.assertEqual(code, 0, view)
            self.assertNotIn("continued", json.dumps(view))

    def test_capability_keeps_worker_pool_presets_from_catalog_and_grants(self) -> None:
        self.init({"grants": [{"id": "droid/opus", "count": 2, "state": "granted"}]})
        code, view = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, view)
        self.assertIn("droid/opus", view["capability"]["presets"])
        self.assertIn("zcode/default", view["capability"]["presets"])
        self.assertNotIn("classes", self.doc()["state"]["authorization"])
        self.assertIn("Worker", view["catalog"]["classes"])

    def test_nested_types_are_refused_and_bytes_stay(self) -> None:
        self.init()
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1",
            "--set", json.dumps({"stage": "todo", "goal": "g", "next": {"history": [{"turn": 1}]}}))
        self.assertNotEqual(code, 0, out)
        self.assertIn("path", out)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--section", "sideagent", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-node", "state": "active",
                                 "narrative": "free"}))
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)

    def test_cleanup_names_removals_and_legacy_refusal_says_how(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["t1"] = {
            "stage": "doing", "goal": "keep", "next": "continue", "legacy": {"note": "old"},
            "rev": 1, "writer": "host", "source": "s",
        }
        doc["state"]["recovery"] = {"legacy": {"completion_evidence": "old"}, "v1_host": {"session": "x"}}
        doc["state"]["unverified"] = {"t1-stage": {"summary": "old warning", "locator": "pending[0]"}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "t1", "--expect-rev", "1", "--set", json.dumps({"next": "still open"}))
        self.assertNotEqual(code, 0, out)
        self.assertIn("state migrate", out.get("recovery", ""))
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        removed = " ".join(out.get("removed") or [])
        self.assertIn("tasks.t1.legacy", removed)
        self.assertIn("recovery.legacy", removed)
        self.assertIn("recovery.v1_host", removed)
        self.assertIn("unverified.t1-stage", removed)
        self.assertEqual(self.doc()["state"]["tasks"]["t1"]["goal"], "keep")
        self.assertNotIn("t1-stage", self.doc()["state"].get("unverified") or {})

    def test_cancelled_seat_and_keep_open_stay_unaccounted(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "live-cancel",
                   "--set", json.dumps({"stage": "doing", "goal": "stop the seat",
                                        "next": "stop codex-KT-live", "sessions": ["codex-KT-live"],
                                        "verdict": {"value": "cancelled"}}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "kept",
                   "--set", json.dumps({"stage": "done", "goal": "still open", "keep_open": True,
                                        "next": "new obligation", "verdict": {"value": "accepted"}}))
        code, pending = self.state("view", "--file", str(self.file), "--role", "sideagent")
        entries = [{"input": item, "retained": item[len("host:"):].split("@", 1)[0]}
                   for item in pending["pending_host_changes"] if item.startswith("host:section/")]
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({
            "holder_instance_id": "node-1", "platform": "zcode", "repo": str(self.repo),
            "session": "zcode-KT-sideagent"})
        code, out = run_dispatch([
            "state", "checkpoint", "--file", str(self.file), "--writer", "sideagent",
            "--source", "open-duties", "--batch", "open-duties",
            "--through-host-revision", str(self.doc()["host_revision"]),
            "--entries", json.dumps(entries)], env)
        self.assertEqual(code, 0, out)
        returned = out["value"]["returned_to_host"]
        self.assertTrue(any("live-cancel" in key for key in returned), returned)
        self.assertTrue(any(key.startswith("host:tasks/kept@") for key in returned), returned)
        self.assertFalse(out["value"]["verified"])

    def test_explicit_verdict_reconciles_an_accepted_prior_without_losing_duties(self) -> None:
        self.init()
        verdict = {"value": "accepted", "by": "host", "why": "the current design is accepted"}
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "accepted-design",
            "--kind", "tasks", "--id", "design", "--set", json.dumps({
                "stage": "done", "goal": "deliver the design", "verdict": verdict,
                "evidence": ["original-design", "unresolved-final-review"],
                "next": "finish the integrated review", "wait": "outer and Opus", "keep_open": True,
                "dispatch": ["design-review"], "dispositions": {"design-review": "accepted"}}))
        self.assertEqual(code, 0, out)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "pending-duty",
            "--kind", "decisions", "--id", "final-review", "--set",
            json.dumps({"owner": "host", "question": "accept the integrated candidate?"}))
        self.assertEqual(code, 0, out)
        doc = self.doc()
        doc["state"]["tasks"]["design"]["prior_verdict"] = {
            "value": "partial", "by": "host", "why": "the prior review is pending"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "same-process-fact",
            "--kind", "tasks", "--id", "design", "--expect-rev", "1", "--set", '{"wait":"outer and Opus"}')
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["prior_verdict"], doc["state"]["tasks"]["design"]["prior_verdict"])
        before = self.doc()["state"]
        for revision in (2, 3):
            code, out = self.state(
                "update", "--file", str(self.file), "--writer", "host", "--source", "same-authoritative-verdict",
                "--kind", "tasks", "--id", "design", "--expect-rev", str(revision),
                "--set", json.dumps({"verdict": verdict}))
            self.assertEqual(code, 0, out)
            self.assertNotIn("prior_verdict", out["value"])
            for key, value in before["tasks"]["design"].items():
                if key not in ("prior_verdict", "rev", "updated_at", "source", "writer", "host_revision"):
                    self.assertEqual(out["value"][key], value, key)
            self.assertEqual({k: v for k, v in self.doc()["state"].items() if k != "tasks"},
                             {k: v for k, v in before.items() if k != "tasks"})
            self.assertTrue(any(row["id"] == "final-review" for row in json.loads(self.doc()["body"])["attention"]))

    def test_legacy_verdict_notes_migrate_without_losing_open_prior_text(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"] = {
            "current": {"stage": "doing", "goal": "finish the repair", "rev": 1,
                        "verdict": {"value": "partial", "by": "host", "note": "keep final review open"},
                        "evidence": ["original-review"], "next": "complete QA"},
            "open": {"stage": "review", "goal": "review the repair", "rev": 1,
                     "prior_verdict": {"value": "repair", "by": "host", "why": "retain current evidence",
                                       "note": "resolve the second review duty"},
                     "wait": "Host review", "evidence": ["unresolved-source"]}}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        code, view = self.state("view", "--file", str(self.file), "--role", "host")
        self.assertEqual(code, 0, view)
        self.assertEqual([row["path"] for row in view["unknown"]],
                         ["state.tasks.current.verdict.note", "state.tasks.open.prior_verdict.note"])
        self.assertEqual(self.file.read_bytes(), before)
        for slot, key, value in (("prior_verdict", "note", ["unmapped"]),
                                 ("prior_verdict", "why", {"unmapped": "current"})):
            invalid = json.loads(before)
            invalid["state"]["tasks"]["open"][slot][key] = value
            self.file.write_text(json.dumps(invalid), encoding="utf-8")
            sentinel = self.file.read_bytes()
            code, out = self.state("migrate", "--file", str(self.file), "--write")
            self.assertEqual((code, out["result"]), (2, "blocked"), out)
            self.assertEqual(out["blockers"][0]["path"], "tasks.open.prior_verdict.note")
            self.assertEqual(self.file.read_bytes(), sentinel)
        self.file.write_bytes(before)
        removed = ["tasks.current.verdict.note mapped to tasks.current.verdict.why",
                   "tasks.open.prior_verdict.note mapped to tasks.open.prior_verdict.why"]
        code, plan = self.state("migrate", "--file", str(self.file))
        self.assertEqual((code, plan["result"]), (0, "planned"), plan)
        self.assertEqual(plan["report"]["removed"], removed)
        self.assertEqual(self.file.read_bytes(), before)
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["removed"], removed)
        expected = json.loads(before)["state"]
        expected.pop("retired", None)  # Existing cleanup removes this empty list.
        expected["tasks"]["current"]["verdict"]["why"] = expected["tasks"]["current"]["verdict"].pop("note")
        prior = expected["tasks"]["open"]["prior_verdict"]
        prior["why"] += "\n" + prior.pop("note")
        self.assertEqual(self.doc()["state"], expected)
        migrated = self.file.read_bytes()
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual((code, out["result"]), (0, "current"), out)
        self.assertEqual(self.file.read_bytes(), migrated)
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "sideagent", "--source", "same-process-fact",
            "--kind", "tasks", "--id", "open", "--expect-rev", "1", "--set", '{"wait":"Host review"}')
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["prior_verdict"], prior)
        self.assertNotIn("verdict", out["value"])
        self.assertTrue(any(row["id"] == "open" and row["why"] == "awaiting-verdict"
                            for row in json.loads(self.doc()["body"])["attention"]))

    def test_explicit_legacy_verdict_update_clears_prior_after_role_and_cas_checks(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["legacy"] = {
            "stage": "done", "goal": "deliver the design", "rev": 1,
            "verdict": {"value": "accepted", "by": "host", "note": "final integrated review remains open"},
            "prior_verdict": {"value": "partial", "by": "host", "note": "earlier review is pending"},
            "evidence": ["original-design", "pending-review"], "next": "finish integrated QA",
            "wait": "outer and Opus", "dispatch": ["design-seat"], "keep_open": True}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        patch = {"verdict": {"note": None, "why": "final integrated review remains open"}}
        for writer, revision, proposed, extra, reason in (
                ("host", "0", patch, (), "conflict"),
                ("worker", "1", patch, (), "writer-refused"),
                ("sideagent", "1", patch, (), "host-turn-required"),
                ("host", "1", {"verdict": {"note": None, "value": "invalid"}}, (), "invalid-input"),
                ("host", "1", {"verdict": {"note": "invalid new legacy key"}}, (), "invalid-input"),
                ("host", "1", {"prior_verdict": None}, (), "invalid-input")):
            code, out = self.state(
                "update", "--file", str(self.file), "--writer", writer, "--source", "refusal-case",
                "--kind", "tasks", "--id", "legacy", "--expect-rev", revision, "--set", json.dumps(proposed), *extra)
            self.assertNotEqual(code, 0, out)
            self.assertEqual(out["reason"], reason)
            self.assertEqual(self.file.read_bytes(), before)
        for writer in ("host", "sideagent"):
            with self.subTest(writer=writer):
                self.file.write_bytes(before)
                extra = ("--host-turn", "host-legacy-review-2") if writer == "sideagent" else ()
                code, out = self.state(
                    "update", "--file", str(self.file), "--writer", writer, "--source", "explicit-current-verdict",
                    "--kind", "tasks", "--id", "legacy", "--expect-rev", "1", "--set", json.dumps(patch), *extra)
                self.assertEqual(code, 0, out)
                task = out["value"]
                self.assertNotIn("prior_verdict", task)
                self.assertNotIn("note", task["verdict"])
                self.assertEqual(task["verdict"]["why"], doc["state"]["tasks"]["legacy"]["verdict"]["note"])
                for key, value in doc["state"]["tasks"]["legacy"].items():
                    if key not in ("prior_verdict", "verdict", "rev"):
                        self.assertEqual(task[key], value, key)
                self.assertEqual(self.doc()["state"]["authorization"], doc["state"]["authorization"])
                if writer == "sideagent":
                    self.assertEqual(task["transcribed"], {"host_turn": "host-legacy-review-2", "fields": ["verdict"]})
                    self.assertTrue(any(row["why"] == "transcribed-check" and row["host_turn"] == "host-legacy-review-2"
                                        for row in json.loads(self.doc()["body"])["attention"]))

    def test_verdict_null_is_refused_without_losing_open_prior(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["open"] = {
            "stage": "review", "goal": "review the repair", "rev": 1,
            "prior_verdict": {"value": "repair", "by": "host", "why": "keep the pending instruction"},
            "evidence": ["pending-source"], "wait": "Host review"}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        before = self.file.read_bytes()
        for writer, extra, reason in (("host", (), "invalid-input"),
                                      ("sideagent", ("--host-turn", "host-null-2"), "invalid-input"),
                                      ("sideagent", (), "host-turn-required")):
            code, out = self.state(
                "update", "--file", str(self.file), "--writer", writer, "--source", "null-case",
                "--kind", "tasks", "--id", "open", "--expect-rev", "1", "--set", '{"verdict":null}', *extra)
            self.assertEqual((code, out["reason"]), (2, reason), out)
            self.assertEqual(self.file.read_bytes(), before)
            if reason == "invalid-input":
                self.assertEqual(out["path"], "tasks.open.verdict")
                self.assertIn("keep the verdict", out["recovery"])

    def test_node_process_write_does_not_change_delivery_open(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-sideagent", "state": "active"}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "t3",
                   "--set", json.dumps({"stage": "review", "goal": "close the selected issues",
                                        "next": "review the research"}))
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "host-turn",
                   "--kind", "tasks", "--id", "t3", "--expect-rev", "1",
                   "--set", json.dumps({"verdict": {"value": "repair", "why": "named repair remains"},
                                        "next": "seat the named repair"}))
        first = [row for row in json.loads(self.doc()["body"])["attention"] if row["why"] == "delivery-open"]
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_DISPATCHER"] = json.dumps({
            "holder_instance_id": "node-1", "platform": "zcode", "repo": str(self.repo),
            "session": "zcode-KT-sideagent"})
        code, out = run_dispatch([
            "state", "update", "--file", str(self.file), "--writer", "sideagent",
            "--source", "stop confirmed", "--kind", "tasks", "--id", "t3", "--expect-rev", "2",
            "--set", json.dumps({"wait": "codex-KT-repair stopped"})], env)
        self.assertEqual(code, 0, out)
        second = [row for row in json.loads(self.doc()["body"])["attention"] if row["why"] == "delivery-open"]
        self.assertEqual(first, second)
        self.assertEqual(self.doc()["state"]["tasks"]["t3"]["goal"], "close the selected issues")

    def _bind_node(self) -> str:
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "bind",
                   "--section", "sideagent", "--expect-revision", "1",
                   "--set", json.dumps({"platform": "zcode", "session": "zcode-KT-node", "state": "active",
                                        "mode": "node"}))
        doc = self.doc()
        doc["carrier"] = {
            "capability": "heartbeat-state/2",
            "holder_instance_id": "host-1",
            "platform": "codex",
            "session": "codex-KT-host",
        }
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        return hashlib.sha256(str(self.file.resolve().parent.parent).encode("utf-8")).hexdigest()[:16]

    def _node_record(self, *, pid: int, repo: str | None = None, host: str = "host-1",
                     role: str = "sideagent") -> dict:
        bound = repo if repo is not None else str(self.file.resolve().parent.parent)
        return {
            "session_role": role,
            "state": "ready",
            "platform": "zcode",
            "session": "zcode-KT-node",
            "repo": bound,
            "holder_pid": pid,
            "dispatcher": {
                "holder_instance_id": host,
                "platform": "codex",
                "session": "codex-KT-host",
                "repo": bound,
            },
        }

    def test_node_running_follows_the_bound_record(self) -> None:
        self.init()
        digest = self._bind_node()
        root = self.repo / "records"
        env = {key: value for key, value in os.environ.items() if key not in CALLER_ENV}
        env["KAOLA_ACP_RECORD_ROOT"] = str(root)
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertEqual(code, 0, out)
        self.assertIn("no node is running", out["sideagent_maintenance"])
        foreign = root / "zcode" / "zcode-KT-node" / "digest" / "record.json"
        foreign.parent.mkdir(parents=True)
        foreign.write_text(json.dumps(self._node_record(pid=os.getpid())), encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertIn("no node is running", out["sideagent_maintenance"])
        record = root / "zcode" / "zcode-KT-node" / digest / "record.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps(self._node_record(pid=os.getpid(), host="other-host")),
                          encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertIn("no node is running", out["sideagent_maintenance"])
        record.write_text(json.dumps(self._node_record(pid=os.getpid(), repo="/other/repo")),
                          encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertIn("no node is running", out["sideagent_maintenance"])
        dead = subprocess.Popen([PYTHON, "-c", "pass"])
        dead.wait()
        record.write_text(json.dumps(self._node_record(pid=dead.pid)), encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertIn("no node is running", out["sideagent_maintenance"])
        record.write_text(json.dumps(self._node_record(pid=os.getpid())), encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertEqual(out["sideagent_maintenance"], "a node is running")
        doc = self.doc()
        doc.pop("carrier")
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertIn("no node is running", out["sideagent_maintenance"])

    def test_node_running_uses_the_process_temp_dir(self) -> None:
        self.init()
        digest = self._bind_node()
        scratch = Path(self.tmp.name) / "process-temp"
        scratch.mkdir()
        env = {key: value for key, value in os.environ.items()
               if key not in CALLER_ENV and key not in ("KAOLA_ACP_RECORD_ROOT", "XDG_RUNTIME_DIR")}
        env["TMPDIR"] = str(scratch)
        record = (scratch / f"kaola-{os.getuid()}" / "zcode" / "zcode-KT-node" / digest / "record.json")
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps(self._node_record(pid=os.getpid())), encoding="utf-8")
        code, out = run_dispatch(["state", "view", "--file", str(self.file), "--role", "host"], env)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["sideagent_maintenance"], "a node is running")

    def test_timer_without_a_body_is_unavailable(self) -> None:
        code, out = self.state("timer", "--repo", str(self.repo), "--target", "local",
                               "--entry", "/kaola-delegator")
        self.assertEqual(out["result"], "unavailable")
        self.assertNotEqual(out["result"], "mismatch")

    def test_a_fabricated_cite_is_refused_and_a_real_path_is_kept(self) -> None:
        self.init()
        self.state("update", "--file", str(self.file), "--writer", "host", "--source", "s",
                   "--kind", "tasks", "--id", "done-one",
                   "--set", json.dumps({"stage": "done", "goal": "finished", "verdict": {"value": "accepted"}}))
        before = self.file.read_bytes()
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "done-one", "--expect-rev", "1", "--evidence", "not a commit",
            "--cite", '{"commit":"abcdef1","path":"README.md"}')
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertIn("invent", out["detail"])
        code, out = self.state(
            "retire", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "done-one", "--expect-rev", "1", "--evidence", "README.md",
            "--cite", CITE)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["value"]["cite"]["path"], "README.md")
        self.assertNotIn("commit", out["value"]["cite"])
        self.assertFalse(self.doc()["state"].get("retired"))

    def test_delegator_role_view_uses_locators(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["holds"]["h1"] = {
            "reason": "quota", "narrative": "secret prose", "rev": 1, "writer": "host", "source": "s",
        }
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state("view", "--file", str(self.file), "--role", "delegator", "--repo", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertNotIn("secret prose", json.dumps(out["special"]["holds"]))
        self.assertTrue(any(item["path"] == "state.holds.h1.narrative" for item in out["unknown"]))

    def test_owner_stop_is_not_blocked_by_the_legacy_bound(self) -> None:
        self.init()
        doc = self.doc()
        doc["state"]["tasks"]["pad"] = {
            "stage": "todo", "goal": "x" * 70000, "rev": 1, "writer": "host", "source": "s",
        }
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "pad", "--expect-rev", "1", "--set", json.dumps({"next": "continue"}))
        self.assertEqual(out["reason"], "carrier-limit", out)
        self.assertIn("owner stop", out["recovery"])
        before = self.file.read_bytes()
        code, out = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "owner",
            "--section", "project", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"stop": "stop at the owner boundary"}))
        self.assertEqual(code, 0, out)
        self.assertNotEqual(self.file.read_bytes(), before)
        self.assertEqual(self.doc()["state"]["project"]["stop"], "stop at the owner boundary")
        self.assertEqual(self.doc()["state"]["tasks"]["pad"]["goal"], "x" * 70000)

    def test_a_failed_write_removes_its_temp_file(self) -> None:
        spec = importlib.util.spec_from_file_location("kpr_dispatch_259", DISPATCH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        target = self.repo / "atomic.json"
        target.write_text("original\n", encoding="utf-8")
        real = Path.write_text

        def fail_temp(path: Path, *args: object, **kwargs: object) -> int:
            if path.name.endswith(".tmp"):
                raise OSError("disk")
            return real(path, *args, **kwargs)

        with unittest.mock.patch.object(Path, "write_text", fail_temp):
            with self.assertRaises(OSError):
                module.atomic_write(target, "new\n")
        self.assertFalse(target.with_name("atomic.json.tmp").exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "original\n")

    def test_an_oversized_migrated_record_still_accepts_an_owner_stop(self) -> None:
        body = {
            "project": {"code": "KT", "goal": "keep the open duty"},
            "authorization": {"grants": []},
            "active": [
                {"ref": f"row-{n}", "session": f"codex-KT-i{n}-x", "evidence": "e" * 900}
                for n in range(80)
            ],
        }
        self.file.write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/1", "body": json.dumps(body),
        }), encoding="utf-8")
        code, out = self.state("migrate", "--file", str(self.file), "--write")
        self.assertEqual(code, 0, out)
        self.assertGreater(self.file.stat().st_size, 65536)
        self.assertIsNone(self.doc().get("carrier"))
        revision = str(self.doc()["revision"])
        code, stopped = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "owner",
            "--section", "project", "--expect-revision", revision,
            "--set", json.dumps({"stop": "stop at the owner boundary"}))
        self.assertEqual(code, 0, stopped)
        self.assertEqual(self.doc()["state"]["project"]["stop"], "stop at the owner boundary")
        task_id = next(iter(self.doc()["state"]["tasks"]))
        code, ordinary = self.state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", task_id, "--expect-rev", "1",
            "--set", json.dumps({"next": "continue"}))
        self.assertEqual(ordinary["reason"], "carrier-limit", ordinary)
        self.assertIn("owner stop", ordinary["recovery"])

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))


class RealAcpInjection(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i259-acp-", dir="/tmp")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.records = self.root / "records"
        self.repo = self.root / "repo"
        self.home.mkdir()
        self.records.mkdir()
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        (self.repo / ".kaola").mkdir()
        self.log = self.root / "mock.jsonl"
        self.started: list[str] = []
        self.agent = f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"

    def tearDown(self) -> None:
        for session in self.started:
            self.cli("stop", "--force", session=session, check=False)
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
            "MOCK_ACP_LOG": str(self.log),
        }
        base.update(extra)
        return base

    def cli(self, command: str, *args: str, session: str, check: bool = True,
            env: dict[str, str] | None = None) -> dict:
        argv = [PYTHON, str(CLI), "codex", command, "--repo", str(self.repo), "--session", session, *args]
        if command == "start":
            argv.extend(["--command", self.agent])
            self.started.append(session)
        proc = subprocess.run(argv, capture_output=True, text=True, env=env or self.env(), timeout=90)
        payload: dict = {}
        for line in reversed((proc.stdout or "").splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            break
        if check and proc.returncode != 0:
            self.fail(f"{command} exited {proc.returncode}: {payload or proc.stderr[-800:]}")
        payload["_returncode"] = proc.returncode
        return payload

    def test_start_send_observe_stop_injects_the_projected_view(self) -> None:
        state = self.repo / ".kaola" / "heartbeat-prompt.json"
        code, out = run_dispatch([
            "state", "init", "--file", str(state), "--writer", "host", "--source", "turn-1",
            "--project", json.dumps({"code": "KT", "goal": "close the selected issues"}),
            "--authorization", json.dumps({
                                           "grants": [{"id": "codex/default", "state": "granted", "count": 1}]})])
        self.assertEqual(code, 0, out)
        run_dispatch([
            "state", "update", "--file", str(state), "--writer", "host", "--source", "s",
            "--kind", "tasks", "--id", "repair-1",
            "--set", json.dumps({"stage": "doing", "goal": "projected-goal-marker",
                                 "next": "seat the named repair"})])
        for cycle in range(2):
            code, out = run_dispatch([
                "state", "update", "--file", str(state), "--writer", "host", "--source", "original-fault",
                "--kind", "alerts", "--id", "handled-fault", "--set",
                json.dumps({"level": "warn", "summary": "REMOVED-EXCEPTION-SENTINEL"})])
            self.assertEqual(code, 0, out)
            code, out = run_dispatch([
                "state", "retire", "--file", str(state), "--writer", "host", "--source", "original-disposition",
                "--kind", "alerts", "--id", "handled-fault", "--expect-rev", "1",
                "--evidence", "original-handled-receipt"])
            self.assertEqual(code, 0, out)
            self.assertNotIn("REMOVED-EXCEPTION-SENTINEL", state.read_text())
        doc = json.loads(state.read_text(encoding="utf-8"))
        doc["body"] = "STORED-BODY-SENTINEL"
        state.write_text(json.dumps(doc), encoding="utf-8")
        host = "codex-KPR-i259-host"
        worker = "codex-KPR-i259-work"
        started = self.cli("start", session=host)
        self.assertEqual(started.get("state"), "ready", started.get("error") or started)
        target = json.dumps({"platform": "codex", "session": host, "repo": str(self.repo)})
        self.cli("start", session=worker, env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        sent = self.cli("send", "--text", "advance the named repair", session=worker,
                        env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        self.assertIn(sent.get("outcome") or sent.get("turn_outcome"),
                      ("turn_completed", "in_progress", "idle"), sent.get("error") or sent.get("state"))
        observed = self.cli("observe", session=worker, env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        self.assertEqual(observed.get("turn_outcome"), "turn_completed", observed.get("error"))
        deadline = time.monotonic() + 15
        text = ""
        while time.monotonic() < deadline:
            text = self.log.read_text(encoding="utf-8") if self.log.exists() else ""
            if "projected-goal-marker" in text and "kaola-host-notify/1" in text:
                break
            time.sleep(0.2)
        self.assertIn("projected-goal-marker", text)
        self.assertNotIn("classes", json.loads(state.read_text())["state"]["authorization"])
        self.assertNotIn("STORED-BODY-SENTINEL", text)
        self.assertNotIn("REMOVED-EXCEPTION-SENTINEL", text)
        host_observe = self.cli("observe", session=host)
        self.assertTrue(host_observe)
        stopped = self.cli("stop", "--force", session=worker, env=self.env(KAOLA_ACP_HEARTBEAT_HOST=target))
        self.assertTrue(stopped.get("stopped") or stopped.get("state") == "stopped"
                        or stopped.get("residual_pids") == [])
        host_stopped = self.cli("stop", "--force", session=host)
        self.assertTrue(host_stopped.get("stopped") or host_stopped.get("state") == "stopped"
                        or host_stopped.get("residual_pids") == [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
