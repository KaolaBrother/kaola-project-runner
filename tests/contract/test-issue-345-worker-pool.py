#!/usr/bin/env python3
"""Issue #345: dsh/commandcode is a default-authorized Worker pool member.

The exact pool is seven preset ids. ``dsh/commandcode`` needs no grant row.
``codex/luna`` and ``zcode/default`` stay members. Antigravity stays out.
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

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
SKILLS = PROJECT / "skills"
PLATFORMS = PROJECT / "platforms"

POOL = [
    "claude-code/haiku",
    "codex/luna",
    "devin/default",
    "dsh/commandcode",
    "dsh/default",
    "opencode/default",
    "zcode/default",
]
MEMBERS = ", ".join(f"`{preset}`" for preset in POOL)
SENTENCE = "The Worker pool is exactly: " + MEMBERS + "."
DELEGATOR_SENTENCE = "The pool is exactly: " + MEMBERS + "."


def load_render():
    spec = importlib.util.spec_from_file_location(
        "render_skills_issue_345_pool", SCRIPTS / "render-skills.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExactWorkerPool(unittest.TestCase):
    def test_source_and_rendered_text_name_the_same_seven(self) -> None:
        render = load_render()
        manifests = [render.parse_manifest(path) for path in sorted(PLATFORMS.glob("*.yaml"))]
        self.assertEqual(render.worker_pool_members(manifests), MEMBERS)
        profiles = (SKILLS / "kaola-project-runner" / "references" / "worker-profiles.md").read_text(
            encoding="utf-8")
        host = (SKILLS / "kaola-delegator" / "references" / "host-platforms.md").read_text(
            encoding="utf-8")
        api = (PROJECT / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertIn(SENTENCE, profiles)
        self.assertIn(DELEGATOR_SENTENCE, host)
        self.assertIn(MEMBERS, api)
        self.assertIn("seven-preset", profiles)
        self.assertNotIn("six-preset", profiles)
        self.assertNotIn("antigravity/", SENTENCE)
        for preset in POOL:
            self.assertIn(f"`{preset}`", api)
        template = (PROJECT / "templates" / "orchestrator" / "references"
                    / "worker-profiles.md.tmpl").read_text(encoding="utf-8")
        delegator = (PROJECT / "templates" / "kaola-delegator" / "references"
                     / "host-platforms.md.tmpl").read_text(encoding="utf-8")
        self.assertIn("{{WORKER_POOL_MEMBERS}}", template)
        self.assertIn("{{WORKER_POOL_MEMBERS}}", delegator)
        self.assertIn("seven-preset", template)
        self.assertIn("Those seven", delegator)

    def test_dispatch_and_delegator_authorize_commandcode_without_a_grant(self) -> None:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_") or key == "KAOLA_LAUNCH_BACKEND"}
        env.pop("KAOLA_ACP_DISPATCHER", None)
        dispatch = SCRIPTS / "kaola-dispatch.py"
        with tempfile.TemporaryDirectory(prefix="kpr-i345-pool-") as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            auth = root / "auth.json"
            auth.write_text(json.dumps({"grants": []}), encoding="utf-8")
            live = root / "live.json"
            live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": []}),
                            encoding="utf-8")

            def run(args: list[str]) -> dict:
                proc = subprocess.run(
                    [sys.executable, str(dispatch), *args],
                    capture_output=True, text=True, timeout=60, env=env)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                return json.loads(proc.stdout)

            project = run(["project", "--authorization", str(auth),
                           "--platforms", str(PLATFORMS)])
            by_id = {item["id"]: item for item in project["candidates"]}
            commandcode = by_id["dsh/commandcode"]
            self.assertEqual(commandcode["class"], "Worker")
            self.assertEqual(commandcode["state"], "default-pool")
            self.assertTrue(commandcode["pool"])
            self.assertIsNone(commandcode["count"])
            self.assertNotIn("dsh/commandcode", json.loads(auth.read_text(encoding="utf-8"))["grants"])
            self.assertIn("codex/luna", by_id)
            self.assertIn("zcode/default", by_id)
            self.assertEqual(by_id["codex/luna"]["state"], "default-pool")
            self.assertEqual(by_id["zcode/default"]["state"], "default-pool")
            self.assertNotIn("antigravity/default",
                             [item["id"] for item in project["candidates"]
                              if item["class"] == "Worker" and item["pool"]])

            seats = run([
                "project", "--seats", "--repo", str(repo),
                "--authorization", str(auth), "--live", str(live),
                "--platforms", str(PLATFORMS),
            ])
            self.assertEqual(seats["summary"]["worker_pool"], POOL)

            # An omitted worker_pool is ceiling-incomplete, so the seat list
            # stays empty. Default authorization is the pool field itself:
            # the seven ids, with no elite/expert grant row. A counted grant
            # would become a seat and leave the pool.
            delegator = repo / ".kaola" / "delegator-heartbeat.json"
            delegator.parent.mkdir()
            delegator.write_text(json.dumps({
                "schema": "kaola-delegator-heartbeat/1",
                "revision": 1,
                "updated_at": "2026-10-18T00:00:00+00:00",
                "authorization": {"dispatch_enabled": True, "worker_pool": POOL},
            }), encoding="utf-8")
            viewed = run([
                "delegator", "view", "--file", str(delegator),
                "--repo", str(repo), "--live", str(live),
                "--platforms", str(PLATFORMS),
            ])
            self.assertEqual(viewed["seats"]["worker_pool"], POOL)
            seated = {row["id"] for group in viewed["seats"].get("groups") or []
                      for row in group.get("presets") or []}
            self.assertNotIn("dsh/commandcode", seated)
            stored = json.loads(delegator.read_text(encoding="utf-8"))["authorization"]
            self.assertEqual(stored["worker_pool"], POOL)
            for key in ("grants", "elite_grants", "expert_task_grants"):
                self.assertNotIn(key, stored)


if __name__ == "__main__":
    unittest.main()
