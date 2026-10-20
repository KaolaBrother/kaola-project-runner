#!/usr/bin/env python3
"""Issue #377: collect resolves a platform Runner through the defined fallback
roots, retries a stored runner-missing row with a bounded count, and reports a
gone session as unknown/session-gone.

Behavioral: the real CLI runs against fake runtime-tmux.sh receipts. The test
does not import collect_one, and it never edits the checkout's generated
Skills. The fourth platform set (devin, dsh, droid, opencode) uses codex as
the control whose Runner is present under the ordinary --skills-root.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "kaola-dispatch.py"
ROUTES = REPO / "scripts" / "kaola-recovery-routes.py"
PLATFORMS = ("codex", "devin", "dsh", "droid", "opencode")
BOUND = 3

FAKE_RUNNER = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path

    argv = sys.argv[1:]
    command = argv[0]
    session = argv[argv.index("--session") + 1]
    platform = Path(__file__).resolve().parents[1].name.removesuffix("-kaola-project-runner")
    with Path(os.environ["FAKE_LOG"]).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "platform": platform, "command": command, "session": session,
            "script": str(Path(__file__).resolve()), "argv": argv,
        }) + "\\n")
    if session == os.environ.get("FAKE_NO_SESSION"):
        print(json.dumps({"error": {"code": "no-session"}}))
        raise SystemExit(0)
    repo = os.environ["FAKE_REPO"]
    if command == "status":
        print(json.dumps({
            "repo": repo, "session": session,
            "holder_instance_id": "holder-" + session,
            "prompt_fingerprint": "fp-" + session,
            "turn_active": False, "turn_outcome": "turn_completed",
            "stop_reason": "end_turn", "mutation_status": "completed",
        }))
    elif command == "capture":
        print(json.dumps({"events": [{"role": "assistant", "text": "report from " + platform}]}))
    else:
        print(json.dumps({"result": "refused", "error": {"code": "unexpected-command"}}))
        raise SystemExit(1)
    """
)


def install_fake(root: Path, platforms: tuple[str, ...] | list[str]) -> None:
    for platform in platforms:
        dest = root / f"{platform}-kaola-project-runner" / "scripts"
        dest.mkdir(parents=True, exist_ok=True)
        script = dest / "runtime-tmux.sh"
        script.write_text(FAKE_RUNNER, encoding="utf-8")
        script.chmod(0o755)


def copy_entry(checkout: Path) -> Path:
    scripts = checkout / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ("kaola-dispatch.py", "kaola-record-contract.py", "kaola-acp-paths.py",
                 "kaola-recovery-routes.py", "kaola-session-names.py"):
        shutil.copy2(REPO / "scripts" / name, scripts / name)
    return scripts / "kaola-dispatch.py"


def load_routes():
    spec = importlib.util.spec_from_file_location("kaola_recovery_routes_i377", ROUTES)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RunnerFallback(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.incomplete = self.root / "incomplete"
        install_fake(self.incomplete, ["codex"])
        self.full = self.root / "full"
        install_fake(self.full, list(PLATFORMS))
        self.log = self.root / "runner.log"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("KAOLA_")}
        self.env.update(FAKE_REPO=str(self.repo), FAKE_LOG=str(self.log),
                        KAOLA_DISPATCH_RUNNER_TIMEOUT="20")

    def item(self, platform: str, status: str = "in-flight", **extra) -> dict:
        session = f"{platform}-KPR-i377-a"
        row = {
            "item_id": f"{platform}-item", "preset": f"{platform}/default",
            "platform": platform, "session": session, "repo": str(self.repo),
            "holder_instance_id": f"holder-{session}",
            "prompt_fingerprint": f"fp-{session}", "prompt_sha256": f"fp-{session}",
            "status": status, "acceptance": "pending",
        }
        row.update(extra)
        return row

    def index(self, items: list[dict]) -> Path:
        path = self.root / "dispatch-index.json"
        path.write_text(json.dumps({
            "schema": "kaola-dispatch-index/1", "repo": str(self.repo), "items": items,
        }), encoding="utf-8")
        return path

    def collect(self, entry: Path, index: Path, skills: Path) -> dict:
        proc = subprocess.run(
            [sys.executable, str(entry), "collect", "--index", str(index),
             "--skills-root", str(skills)],
            capture_output=True, text=True, env=self.env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def read_index(self, index: Path) -> dict[str, dict]:
        data = json.loads(index.read_text(encoding="utf-8"))
        return {row["item_id"]: row for row in data["items"]}

    def calls(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [json.loads(line) for line in
                self.log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def checkout(self) -> Path:
        checkout = self.root / "checkout"
        copy_entry(checkout)
        return checkout

    def test_incomplete_root_uses_checkout_skills_fallback(self) -> None:
        checkout = self.checkout()
        install_fake(checkout / "skills", list(PLATFORMS))
        entry = checkout / "scripts" / "kaola-dispatch.py"
        index = self.index([self.item(platform) for platform in PLATFORMS])
        payload = self.collect(entry, index, self.incomplete)
        rows = {row["item_id"]: row for row in payload["items"]}
        for platform in PLATFORMS:
            row = rows[f"{platform}-item"]
            self.assertEqual(row["status"], "returned", row)
            self.assertEqual(row["reason"], "collected", row)
            self.assertEqual(row["result"]["excerpt"], f"report from {platform}")
        for platform in PLATFORMS[1:]:
            evidence = rows[f"{platform}-item"]["evidence"]["runner"]
            self.assertEqual(evidence["source"], "checkout-skills")
            self.assertEqual(
                Path(evidence["path"]).resolve(),
                (checkout / "skills" / f"{platform}-kaola-project-runner"
                 / "scripts" / "runtime-tmux.sh").resolve(),
            )
        codex = rows["codex-item"]["evidence"]["runner"]
        self.assertEqual(codex["source"], "skills-root")
        self.assertEqual(
            Path(codex["path"]).resolve(),
            (self.incomplete / "codex-kaola-project-runner"
             / "scripts" / "runtime-tmux.sh").resolve(),
        )
        self.assertEqual({call["platform"] for call in self.calls()}, set(PLATFORMS))
        self.assertTrue(all(call["command"] in {"status", "capture"} for call in self.calls()))

    def test_dispatch_skill_root_is_the_second_fallback(self) -> None:
        installed = self.root / "installed-skills"
        entry = copy_entry(installed / "kaola-project-runner")
        install_fake(installed, ["dsh"])
        index = self.index([self.item("dsh")])
        payload = self.collect(entry, index, self.root / "empty")
        row = payload["items"][0]
        self.assertEqual(row["status"], "returned", row)
        evidence = row["evidence"]["runner"]
        self.assertEqual(evidence["source"], "dispatch-skill-root")
        self.assertEqual(
            Path(evidence["path"]).resolve(),
            (installed / "dsh-kaola-project-runner"
             / "scripts" / "runtime-tmux.sh").resolve(),
        )

    def test_stored_runner_missing_row_recovers_on_next_collect(self) -> None:
        checkout = self.checkout()
        (checkout / "skills").mkdir()
        entry = checkout / "scripts" / "kaola-dispatch.py"
        index = self.index([self.item(platform) for platform in PLATFORMS])
        first = {row["item_id"]: row for row in
                 self.collect(entry, index, self.incomplete)["items"]}
        self.assertEqual(first["codex-item"]["status"], "returned")
        for platform in PLATFORMS[1:]:
            row = first[f"{platform}-item"]
            self.assertEqual(row["status"], "unknown", row)
            self.assertEqual(row["reason"], "runner-missing", row)
            self.assertEqual(row["runner_missing_attempts"], 1, row)
            self.assertEqual(row["runner_missing_limit"], BOUND, row)
            self.assertIsNone(row["evidence"]["runner"]["path"])
        second = {row["item_id"]: row for row in
                  self.collect(entry, index, self.full)["items"]}
        for platform in PLATFORMS[1:]:
            row = second[f"{platform}-item"]
            self.assertEqual(row["status"], "returned", row)
            self.assertEqual(row["reason"], "collected", row)
            self.assertEqual(row["evidence"]["runner"]["source"], "skills-root")
            self.assertNotIn("runner_missing_attempts", row)
            self.assertNotIn("runner_missing_exhausted", row)
        disk = self.read_index(index)
        self.assertEqual(
            {disk[f"{platform}-item"]["status"] for platform in PLATFORMS},
            {"returned"},
        )
        for platform in PLATFORMS[1:]:
            self.assertNotIn("runner_missing_attempts", disk[f"{platform}-item"])
            self.assertNotIn("runner_missing_limit", disk[f"{platform}-item"])

    def test_runner_missing_retry_is_bounded_and_names_the_route(self) -> None:
        checkout = self.checkout()
        (checkout / "skills").mkdir()
        entry = checkout / "scripts" / "kaola-dispatch.py"
        empty = self.root / "empty"
        row = self.item("devin", status="unknown", reason="runner-missing",
                        runner_missing_attempts=BOUND - 1)
        index = self.index([row])
        first = self.collect(entry, index, empty)["items"][0]
        self.assertEqual(first["status"], "unknown")
        self.assertEqual(first["reason"], "runner-missing")
        self.assertEqual(first["runner_missing_attempts"], BOUND)
        self.assertTrue(first["runner_missing_exhausted"])
        route = load_routes().lookup("runner-missing")
        self.assertEqual(route[0], "route")
        self.assertEqual(first["recovery"], route[1])
        second = self.collect(entry, index, empty)["items"][0]
        self.assertEqual(second["status"], "unknown")
        self.assertEqual(second["reason"], "runner-missing")
        self.assertEqual(second["runner_missing_attempts"], BOUND)
        self.assertTrue(second["runner_missing_exhausted"])
        self.assertEqual(second["recovery"], route[1])
        self.assertEqual(self.calls(), [])
        install_fake(empty, ["devin"])
        third = self.collect(entry, index, empty)["items"][0]
        self.assertEqual(third["status"], "returned")
        self.assertEqual(third["evidence"]["runner"]["source"], "skills-root")
        self.assertNotIn("runner_missing_attempts", third)
        self.assertNotIn("runner_missing_exhausted", third)

    def test_gone_session_is_unknown_session_gone(self) -> None:
        self.env["FAKE_NO_SESSION"] = "devin-KPR-i377-a"
        index = self.index([self.item("devin")])
        payload = self.collect(SCRIPT, index, self.full)
        row = payload["items"][0]
        self.assertEqual(row["status"], "unknown")
        self.assertEqual(row["reason"], "session-gone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
