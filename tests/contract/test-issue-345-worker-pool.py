#!/usr/bin/env python3
"""Issue #345, retargeted by #346: dsh/commandcode is a Worker-class catalog preset.

The class list is seven preset ids. Each one, including ``dsh/commandcode``,
is usable only after an explicit Worker grant. ``codex/terra`` and
``zcode/default`` stay in that class. Antigravity stays out.
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
    "codex/terra",
    "devin/default",
    "dsh/commandcode",
    "dsh/default",
    "opencode/default",
    "zcode/default",
]
MEMBERS = ", ".join(f"`{preset}`" for preset in POOL)
SENTENCE = "Worker-class presets are exactly: " + MEMBERS + "."
HOST_SENTENCE = "The class is exactly: " + MEMBERS + "."


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
        self.assertIn(HOST_SENTENCE, host)
        self.assertIn(MEMBERS, api)
        self.assertIn("explicit Worker grant", profiles)
        self.assertIn("explicit grant", host)
        self.assertNotIn("default-authorized", profiles)
        self.assertNotIn("default-authorized", host)
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
        self.assertIn("explicit Worker grant", template)
        self.assertIn("explicit grant", delegator)
        self.assertNotIn("default-authorized", delegator)

    def test_commandcode_dispatches_only_after_an_explicit_grant(self) -> None:
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
            worker_ids = [item["id"] for item in project["candidates"] if item["class"] == "Worker"]
            self.assertEqual(worker_ids, [])
            self.assertNotIn("antigravity/default", worker_ids)

            granted = root / "granted.json"
            granted.write_text(json.dumps({"grants": [
                {"id": "dsh/commandcode", "state": "granted", "count": 1},
            ]}), encoding="utf-8")
            project = run(["project", "--authorization", str(granted),
                           "--platforms", str(PLATFORMS)])
            by_id = {item["id"]: item for item in project["candidates"]}
            commandcode = by_id["dsh/commandcode"]
            self.assertEqual(commandcode["class"], "Worker")
            self.assertEqual(commandcode["state"], "granted")
            self.assertFalse(commandcode["pool"])
            self.assertEqual(commandcode["count"], 1)
            self.assertNotIn("codex/terra", by_id)
            self.assertNotIn("zcode/default", by_id)

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
            self.assertNotIn("worker_pool", viewed["seats"])
            self.assertEqual(viewed["seats"]["worker_grants"], [])
            self.assertIn("No Worker grants", viewed["seats"]["worker_grant_statement"])
            self.assertIn("legacy worker_pool", viewed["authorization"]["worker_grant_statement"])
            seated = {row["id"] for group in viewed["seats"].get("groups") or []
                      for row in group.get("presets") or []}
            self.assertNotIn("dsh/commandcode", seated)
            stored = json.loads(delegator.read_text(encoding="utf-8"))["authorization"]
            self.assertEqual(stored["worker_pool"], POOL)
            self.assertNotIn("worker_grants", stored)
            for key in ("grants", "elite_grants", "expert_task_grants"):
                self.assertNotIn(key, stored)


if __name__ == "__main__":
    unittest.main()
