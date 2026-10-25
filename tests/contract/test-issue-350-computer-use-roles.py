#!/usr/bin/env python3
"""Issue #350: automatic Worker selection skips computer-use-only presets.

The role is a closed catalog value, not a preset name. Owner decision
``luna-research-ok-20261026`` removed ``luna_model_roles`` from ``codex/luna``,
so Luna is a selectable Worker again (research and computer-use). The skip
still reads the role: a fixture or later preset that sets
``computer-use-only`` is omitted from automatic selection, including the
Sideagent node chain.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import os
import shutil
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
CONTRACT = SCRIPTS / "kaola-record-contract.py"
PATHS = SCRIPTS / "kaola-acp-paths.py"
RENDER = SCRIPTS / "render-skills.py"

LUNA = "codex/luna"
ROLE = "computer-use-only"
DSH_CHAIN = ["claude-code/haiku", LUNA, "devin/default", "opencode/default", "zcode/default"]
OTHER_WORKERS = [
    "claude-code/haiku", "devin/default", "dsh/commandcode", "dsh/default",
    "opencode/default", "zcode/default",
]


def _scrub() -> dict[str, str]:
    saved = {key: os.environ[key] for key in list(os.environ) if key.startswith("KAOLA_")}
    for key in saved:
        del os.environ[key]
    os.environ["KAOLA_LAUNCH_BACKEND"] = "direct"
    return saved


def _restore(saved: dict[str, str]) -> None:
    for key in list(os.environ):
        if key.startswith("KAOLA_"):
            del os.environ[key]
    os.environ.update(saved)


def load_holder():
    spec = importlib.util.spec_from_file_location("holder_issue_350", HOLDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_render():
    spec = importlib.util.spec_from_file_location("render_issue_350", RENDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ComputerUseRoles(unittest.TestCase):
    def setUp(self) -> None:
        self.saved_env = _scrub()
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i350-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        (self.repo / ".kaola").mkdir(parents=True)
        self.holder = load_holder()

    def tearDown(self) -> None:
        self.tmp.cleanup()
        _restore(self.saved_env)

    def write_grant(self, extra: dict | None = None) -> None:
        auth = {
            "elite_grants": [],
            "exclusions": [],
            "expert_task_grants": [],
            "worker_grants": [
                {"preset_ids": [preset], "count": "unlimited", "state": "granted"}
                for preset in sorted(OTHER_WORKERS + [LUNA])
            ],
        }
        if extra:
            auth.update(extra)
        (self.repo / ".kaola" / "delegator-heartbeat.json").write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": 1,
            "updated_at": "2026-10-18T00:00:00+00:00",
            "authorization": auth,
            "project": {"user_language": "zh"},
            "watch": {},
        }), encoding="utf-8")
        (self.repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/2",
            "host_revision": 1,
            "revision": 1,
            "body": "{}",
            "state": {"authorization": {}},
        }), encoding="utf-8")

    def availability(self, absent: list[str]) -> None:
        (self.repo / ".kaola" / "dispatch-availability.json").write_text(
            json.dumps({"absent": absent}), encoding="utf-8")

    def carrier(self, tool: Path | None = None):
        holder = self.holder.Holder.__new__(self.holder.Holder)
        holder.args = argparse.Namespace(repo=str(self.repo))
        holder.node = {}
        holder.events = []
        holder._state_tool = lambda: str(tool or DISPATCH)
        return holder

    def binding(self) -> dict:
        return {
            "platform": "dsh",
            "session": "dsh-KT-sideagent-node",
            "recipe": {
                "runner": "/bin/echo",
                "argv": ["dsh", "start", "--repo", str(self.repo),
                         "--session", "dsh-KT-sideagent-node", "--role", "sideagent"],
            },
        }

    def project(self, platforms: Path | None = None, tool: Path | None = None) -> subprocess.CompletedProcess[str]:
        argv = [sys.executable, str(tool or DISPATCH), "project",
                "--authorization", str(self.repo / ".kaola" / "heartbeat-prompt.json"),
                "--repo", str(self.repo)]
        if platforms is not None:
            argv += ["--platforms", str(platforms)]
        availability = self.repo / ".kaola" / "dispatch-availability.json"
        if availability.is_file():
            argv += ["--availability", str(availability)]
        env = {key: value for key, value in os.environ.items() if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        return subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env)

    def test_dsh_turn_failure_skips_computer_use_only(self) -> None:
        self.write_grant()
        carrier = self.carrier()
        moved = carrier._node_fallback(self.binding(), "dsh", "turn-refused:turn_failed")
        self.assertIsNotNone(moved)
        event = carrier.events[-1]
        self.assertEqual(event["from"], "dsh")
        self.assertEqual(event["reason"], "turn-refused:turn_failed")
        self.assertEqual(event["chain"], DSH_CHAIN)
        self.assertEqual(event["to"], "claude-code/haiku")
        self.assertIn(LUNA, event["chain"])
        self.assertNotIn("codex/luna", inspect.getsource(self.holder.Holder._node_chain))
        self.assertIn(ROLE, inspect.getsource(self.holder.automatic_worker_barred))

    def test_absent_haiku_leads_with_luna(self) -> None:
        self.write_grant()
        self.availability(["claude-code/haiku"])
        chain = self.carrier()._node_chain(self.binding(), ["dsh"])
        presets = [row["preset"] for row in chain]
        self.assertEqual(presets, [LUNA, "devin/default", "opencode/default", "zcode/default"])
        self.assertEqual(presets[0], LUNA)

    def test_only_luna_takes_the_chain_when_other_workers_are_absent(self) -> None:
        self.write_grant()
        self.availability(OTHER_WORKERS)
        carrier = self.carrier()
        moved = carrier._node_fallback(self.binding(), "dsh", "turn-refused:turn_failed")
        self.assertIsNotNone(moved)
        event = carrier.events[-1]
        self.assertFalse(event.get("exhausted", False))
        self.assertEqual(event["chain"], [LUNA])
        self.assertEqual(event["to"], LUNA)
        projected = json.loads(self.project().stdout)
        workers = [row for row in projected["candidates"] if row["class"] == "Worker"]
        self.assertEqual([row["id"] for row in workers], [LUNA])
        self.assertEqual(workers[0].get("roles"), [])

    def test_fixture_role_is_excluded_without_naming_the_preset(self) -> None:
        tree = self.root / "checkout"
        (tree / "scripts").mkdir(parents=True)
        (tree / "platforms").mkdir()
        for source in (DISPATCH, CONTRACT, PATHS):
            shutil.copy2(source, tree / "scripts" / source.name)
        (tree / "platforms" / "futureplat.yaml").write_text(
            "\n".join([
                'id: "futureplat"',
                'named_tiers: "cu,luna"',
                'default_model_class: "Worker"',
                'default_model_profile: "General future worker."',
                'cu_model_class: "Worker"',
                'cu_model_roles: "computer-use-only"',
                'cu_model_profile: "Future computer-use only preset."',
                'luna_model_class: "Worker"',
                'luna_model_profile: "Named luna and still a general worker."',
                "",
            ]),
            encoding="utf-8",
        )
        self.write_grant({"worker_grants": [
            {"preset_ids": [preset], "count": "unlimited", "state": "granted"}
            for preset in ("futureplat/cu", "futureplat/default", "futureplat/luna")
        ]})
        tool = tree / "scripts" / "kaola-dispatch.py"
        projected = self.project(tree / "platforms", tool)
        self.assertEqual(projected.returncode, 0, projected.stdout + projected.stderr)
        rows = {row["id"]: row for row in json.loads(projected.stdout)["candidates"]}
        self.assertEqual(rows["futureplat/cu"]["roles"], [ROLE])
        self.assertEqual(rows["futureplat/luna"]["roles"], [])
        self.assertIn("futureplat/cu", rows)
        chain = self.carrier(tool)._node_chain(self.binding(), ["dsh"])
        presets = [row["preset"] for row in chain]
        self.assertEqual(presets, ["futureplat/default", "futureplat/luna"])
        self.assertNotIn("futureplat/cu", presets)

    def test_unknown_role_rejects_the_catalog_row(self) -> None:
        platforms = self.root / "bad-platforms"
        platforms.mkdir()
        (platforms / "futureplat.yaml").write_text(
            "\n".join([
                'id: "futureplat"',
                'named_tiers: ""',
                'default_model_class: "Worker"',
                'default_model_roles: "desktop-only"',
                'default_model_profile: "Bad role."',
                "",
            ]),
            encoding="utf-8",
        )
        self.write_grant()
        projected = self.project(platforms)
        self.assertNotEqual(projected.returncode, 0)
        detail = projected.stdout + projected.stderr
        self.assertIn("unknown model role", detail)
        self.assertIn("desktop-only", detail)
        self.assertIn("futureplat/default", detail)
        self.assertNotIn('"candidates"', detail)

    def test_explicit_dispatch_still_offers_luna(self) -> None:
        self.write_grant()
        projected = json.loads(self.project().stdout)
        luna = next(row for row in projected["candidates"] if row["id"] == LUNA)
        self.assertEqual(luna["class"], "Worker")
        self.assertEqual(luna["roles"], [])
        self.assertEqual(next(row["roles"] for row in projected["candidates"]
                              if row["id"] == "zcode/default"), [])
        withheld = {row["id"]: row["reason"] for row in projected["withheld"]}
        self.assertNotIn(LUNA, withheld)
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({
            "scope": "research",
            "repo": str(self.repo),
            "items": [{"item_id": "i0", "preset": LUNA, "session": "seat0", "prompt": "bounded"}],
        }), encoding="utf-8")
        auth = self.root / "auth.json"
        auth.write_text(json.dumps({"grants": []}), encoding="utf-8")
        live = self.root / "live.json"
        live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": []}), encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        proc = subprocess.run(
            [sys.executable, str(DISPATCH), "execute", "--dry-run", "--plan", str(plan),
             "--authorization", str(auth), "--platforms", str(PLATFORMS), "--live", str(live)],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        item = json.loads(proc.stdout)["items"][0]
        self.assertEqual(item["preset"], LUNA)
        self.assertEqual(item["reason"], "dry-run")
        self.assertEqual(item["status"], "not-run")

    def test_factory_luna_row_has_no_role_and_render_rejects_unknown(self) -> None:
        text = (PLATFORMS / "codex.yaml").read_text(encoding="utf-8")
        self.assertNotIn("luna_model_roles", text)
        for path in sorted(PLATFORMS.glob("*.yaml")):
            self.assertNotIn(ROLE, path.read_text(encoding="utf-8"), path.name)
        render = load_render()
        manifest = render.parse_manifest(PLATFORMS / "codex.yaml")
        self.assertNotIn("luna_model_roles", manifest)
        self.assertEqual(render.MODEL_ROLES, frozenset({ROLE}))
        bad = self.root / "codex.yaml"
        bad.write_text(text.rstrip() + '\nluna_model_roles: "desktop-only"\n', encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            render.parse_manifest(bad)
        self.assertIn("unknown model role", str(caught.exception))
        self.assertIn("desktop-only", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
