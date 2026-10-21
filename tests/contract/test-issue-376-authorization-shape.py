#!/usr/bin/env python3
"""Issue #376: `--authorization` is the Host object, not a Delegator heartbeat.

The Delegator heartbeat stores grants split as `elite_grants`,
`expert_task_grants` and `worker_grants`. That file is the dispatch ceiling,
read from `--repo`; it is not the Host authorization input. The shape guard
refuses it instead of normalizing it to an empty grant list and projecting
every ceiling-granted seat as `host-grant-missing`.

The Delegator seat view keeps its own split-to-flat conversion (T6/T7), and
valid flat Host authorization keeps its exclusions and shared-group behavior.
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


def delegator_authorization() -> dict:
    return {
        "dispatch_enabled": True,
        "elite_grants": [
            {"preset_ids": ["claude-code/default", "claude-code/opus-xhigh"],
             "count": 1, "state": "granted"},
            {"preset_id": "devin/opus-fusion", "count": 1, "state": "granted"},
        ],
        "expert_task_grants": [
            {"preset_id": "claude-code/fable", "count": 1, "state": "granted",
             "lifetime": "task"},
        ],
        "worker_grants": [
            {"preset_ids": ["dsh/default"], "count": 2, "state": "granted"},
            {"preset_ids": ["devin/default"], "count": 1, "state": "granted"},
        ],
        "exclusions": ["devin/opus-fusion"],
    }


def host_grants() -> list[dict]:
    return [
        {"preset_ids": ["claude-code/default", "claude-code/opus-xhigh"],
         "count": 1, "state": "granted"},
        {"id": "devin/opus-fusion", "count": 1, "state": "granted"},
        {"id": "claude-code/fable", "count": 1, "state": "granted",
         "lifetime": "task"},
        {"id": "dsh/default", "count": 2, "state": "granted"},
        {"id": "devin/default", "count": 1, "state": "granted"},
    ]


def host_state(repo: Path) -> dict:
    return {
        "schema": "kaola-heartbeat-prompt/2",
        "revision": 7,
        "host_revision": 3,
        "updated_at": "2026-10-21T00:00:00+00:00",
        "state": {
            "project": {"repo": str(repo), "goal": "issue 376 authorization shape fixture"},
            "authorization": {"grants": host_grants(),
                              "exclusions": ["devin/opus-fusion"]},
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
    return {row["id"] for group in seats.get("groups") or []
            for row in group["presets"]}


class AuthorizationShape(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i376-")
        root = Path(self.tmp.name)
        self.repo = root / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.repo = self.repo.resolve()
        self.live = root / "live.json"
        self.live.write_text(json.dumps({"schema": "kaola-acp-list/1", "rows": []}),
                             encoding="utf-8")
        self.host_file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.delegator_file = self.repo / ".kaola" / "delegator-heartbeat.json"
        self.split_file = self.repo / ".kaola" / "delegator-raw.json"
        self.plan = root / "plan.json"
        self.host_file.write_text(json.dumps(host_state(self.repo)), encoding="utf-8")
        self.delegator_file.write_text(json.dumps({
            "schema": "kaola-delegator-heartbeat/1",
            "revision": 3,
            "updated_at": "2026-10-21T00:00:00+00:00",
            "authorization": delegator_authorization(),
        }), encoding="utf-8")
        self.plan.write_text(json.dumps({
            "scope": "research",
            "repo": str(self.repo),
            "items": [],
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def project(self, *extra: str) -> tuple[int, dict]:
        return run_dispatch([
            "project", *extra,
            "--repo", str(self.repo), "--authorization", str(self.delegator_file),
            "--live", str(self.live), "--platforms", str(PLATFORMS),
        ])

    def assert_split_error(self, code: int, out: dict, *, both: bool = False) -> None:
        self.assertEqual(code, 2, out)
        self.assertEqual(out.get("result"), "error", out)
        self.assertEqual(out.get("reason"), "invalid-input", out)
        detail = out.get("detail") or ""
        self.assertIn("Delegator heartbeat", detail)
        self.assertIn("--authorization", detail)
        self.assertIn("Host heartbeat/authorization object", detail)
        self.assertIn("ceiling", detail)
        self.assertIn("state view --role delegator", detail)
        self.assertIn("delegator view", detail)
        if both:
            self.assertIn("both", detail)
            self.assertIn("refusing to choose one shape silently", detail)
        else:
            self.assertIn("refusing to normalize", detail)
            self.assertIn("empty grant list", detail)
        self.assertNotIn("summary", out)
        self.assertNotIn("candidates", out)

    def test_project_seats_rejects_split_authorization(self) -> None:
        code, out = self.project("--seats")
        self.assert_split_error(code, out)
        self.assertIn("authorization.elite_grants", out.get("detail") or "")

    def test_project_without_seats_rejects_split_authorization(self) -> None:
        code, out = run_dispatch([
            "project",
            "--repo", str(self.repo), "--authorization", str(self.delegator_file),
            "--live", str(self.live), "--platforms", str(PLATFORMS),
        ])
        self.assert_split_error(code, out)

    def test_split_input_without_repo_ceiling_still_errors(self) -> None:
        self.split_file.write_text(json.dumps({
            "authorization": delegator_authorization(),
        }), encoding="utf-8")
        self.delegator_file.unlink()
        code, out = run_dispatch([
            "project", "--seats", "--repo", str(self.repo),
            "--authorization", str(self.split_file), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assert_split_error(code, out)

    def test_execute_rejects_split_authorization_before_admission(self) -> None:
        code, out = run_dispatch([
            "execute", "--plan", str(self.plan),
            "--authorization", str(self.delegator_file),
            "--live", str(self.live), "--platforms", str(PLATFORMS),
        ])
        self.assert_split_error(code, out)

    def test_any_raw_split_key_is_rejected(self) -> None:
        for key in ("elite_grants", "expert_task_grants", "worker_grants"):
            with self.subTest(key=key):
                self.split_file.write_text(json.dumps({key: []}), encoding="utf-8")
                code, out = run_dispatch([
                    "project", "--seats", "--repo", str(self.repo),
                    "--authorization", str(self.split_file), "--live", str(self.live),
                    "--platforms", str(PLATFORMS),
                ])
                self.assertEqual(code, 2, out)
                self.assertIn("authorization." + key, out.get("detail") or "")

    def test_grants_and_split_keys_together_are_a_deterministic_error(self) -> None:
        for key in ("elite_grants", "expert_task_grants", "worker_grants"):
            with self.subTest(key=key):
                self.split_file.write_text(json.dumps({
                    "grants": [{"id": "dsh/default", "count": 1, "state": "granted"}],
                    key: [],
                }), encoding="utf-8")
                code, out = run_dispatch([
                    "project", "--seats", "--repo", str(self.repo),
                    "--authorization", str(self.split_file), "--live", str(self.live),
                    "--platforms", str(PLATFORMS),
                ])
                self.assert_split_error(code, out, both=True)
                self.assertIn("authorization." + key, out.get("detail") or "")

    def test_no_grants_and_no_split_key_stays_empty_not_an_error(self) -> None:
        self.delegator_file.unlink()
        self.split_file.write_text(json.dumps({}), encoding="utf-8")
        for extra in ((), ("--seats",)):
            with self.subTest(extra=extra):
                code, out = run_dispatch([
                    "project", *extra, "--repo", str(self.repo),
                    "--authorization", str(self.split_file), "--live", str(self.live),
                    "--platforms", str(PLATFORMS),
                ])
                self.assertEqual(code, 0, out)
                if extra:
                    self.assertEqual(out["summary"].get("groups"), [])
                else:
                    self.assertEqual(out.get("candidates"), [])
                    self.assertEqual(out.get("withheld"), [])

    def test_delegator_view_conversion_is_unchanged(self) -> None:
        state_code, state_out = run_dispatch([
            "state", "view", "--role", "delegator", "--file", str(self.host_file),
            "--repo", str(self.repo), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(state_code, 0, state_out)
        seats = state_out["seats"]
        self.assertEqual(listed_ids(seats), {
            "claude-code/default", "claude-code/opus-xhigh", "devin/opus-fusion",
            "claude-code/fable", "dsh/default", "devin/default"})
        self.assertEqual(seats["authorized_total"], 6)
        self.assertEqual(group_index(seats)[
            "grant:claude-code/default,claude-code/opus-xhigh"]["authorized_count"], 1)
        self.assertEqual(seats["worker_grants"][0]["preset_ids"], ["dsh/default"])
        self.assertEqual(seats["worker_grants"][0]["count"], 2)

        self.host_file.unlink()
        code, out = run_dispatch([
            "delegator", "view", "--file", str(self.delegator_file),
            "--repo", str(self.repo), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        fallback = out["seats"]
        self.assertEqual(listed_ids(fallback), listed_ids(seats))
        self.assertEqual(fallback["authorized_total"], 6)
        self.assertEqual(
            sorted((group["group"], group["authorized_count"])
                   for group in fallback["groups"]),
            sorted((group["group"], group["authorized_count"])
                   for group in seats["groups"]))
        self.assertNotIn("duplicate grant",
                         " ".join(fallback.get("unknown_reasons") or []))

    def test_exclusions_and_shared_group_are_unchanged(self) -> None:
        code, out = run_dispatch([
            "project", "--seats", "--repo", str(self.repo),
            "--authorization", str(self.host_file), "--live", str(self.live),
            "--platforms", str(PLATFORMS),
        ])
        self.assertEqual(code, 0, out)
        summary = out["summary"]
        self.assertEqual(summary["authorized_total"], 6)
        groups = group_index(summary)
        shared = groups["grant:claude-code/default,claude-code/opus-xhigh"]
        self.assertEqual(shared["authorized_count"], 1)
        self.assertEqual([row["id"] for row in shared["presets"]],
                         ["claude-code/default", "claude-code/opus-xhigh"])
        self.assertEqual(groups["devin/opus-fusion"]["unavailable"],
                         [{"id": "devin/opus-fusion", "reason": "excluded"}])

    def test_docs_state_the_authorization_contract(self) -> None:
        docs = (REPO / "docs/dispatch-collect.md").read_text(encoding="utf-8")
        template_path = REPO / "templates/orchestrator/references/dispatch-collect.md"
        template = template_path.read_text(encoding="utf-8")
        generated = (REPO / "skills/kaola-project-runner/references/dispatch-collect.md")
        self.assertEqual(template.encode("utf-8"), generated.read_bytes())
        self.assertLessEqual(len(template.encode("utf-8")), 8192)
        self.assertIn(".kaola/delegator-heartbeat.json", docs)
        self.assertIn("Delegator heartbeat", " ".join(docs.split()))
        for text in (docs, template, generated.read_text(encoding="utf-8")):
            flat = " ".join(text.split())
            self.assertIn("--authorization", flat)
            self.assertIn("ceiling", flat)
            self.assertIn("--repo", flat)
            self.assertIn("state view --role delegator", flat)
            self.assertIn("delegator view", flat)
            self.assertIn("grants", flat)
        self.assertIn("exit 2", docs)
        self.assertIn("empty grant list", docs)
        self.assertIn(("The Delegator file is the ceiling and the index is "
                       "correlation, not a ledger; read it from `--repo`, never "
                       "`--authorization`"),
                      template)


if __name__ == "__main__":
    unittest.main()
