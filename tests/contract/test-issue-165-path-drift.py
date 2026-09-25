#!/usr/bin/env python3
"""Issue #165: a removed or moved recorded path is reported by name.

Follow-up N3 from #162 review round 2. #162 recorded absolute ``script_paths``
and reported byte drift, but a recorded path that no longer resolves (the
checkout moved or was deleted) went unreported. ``status``/``list`` name
``recorded-path-missing``. It is evidence only: it never sets ``stale`` and
never gates transport. Issue #179 dropped the ``install-root-mismatch``
condition this issue also added: a moved checkout is this same fact.

Offline only. Holders are the mock ACP agent under an isolated HOME and record
root, and each one is force-stopped before the temporary directory is removed.
No platform CLI is launched.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
LOCATE = PROJECT / "scripts" / "kaola-locate.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)


class PathDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git_init(self.repo)
        self.started: list[tuple[str, str]] = []
        self.agent = (
            f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"
        )

    def tearDown(self) -> None:
        for platform, session in self.started:
            self.run_cli(platform, "stop", "--force", session=session, check=False)
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
        }
        base.update(extra)
        return base

    def run_cli(self, platform: str, command: str, *args: str, session: str,
                check: bool = True, env: dict[str, str] | None = None,
                argv0: Path | None = None, agent: str | None = None
                ) -> tuple[subprocess.CompletedProcess, dict]:
        program = str(argv0 or CLI)
        argv = [PYTHON, program, platform, command, "--repo", str(self.repo),
                "--session", session, *args]
        if command in ("start", "drain-restart"):
            argv += ["--command", agent or self.agent]
            self.started.append((platform, session))
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env or self.env(), timeout=90,
        )
        payload: dict = {}
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            payload = json.loads(lines[-1])
        if check and result.returncode != 0:
            self.fail(f"{command} exited {result.returncode}: {payload or result.stderr[-800:]}")
        return result, payload

    def run_list(self, argv0: Path) -> dict:
        listed = subprocess.run(
            [PYTHON, str(argv0), "list", "--repo", str(self.repo),
             "--record-root", str(self.records)],
            capture_output=True, text=True, env=self.env(), timeout=30, check=True,
        )
        return json.loads(listed.stdout)

    def _installed_cli(self, platform: str, dirname: str | None = None) -> Path:
        """A copy of a real platform Skill tree; return its ``scripts/kaola-acp.py``.

        ``dirname`` defaults to the conventional install name
        (``<platform>-kaola-project-runner``).
        """
        tree = self.root / "installed" / (dirname or f"{platform}-kaola-project-runner")
        shutil.copytree(PROJECT / "skills" / f"{platform}-kaola-project-runner", tree)
        return tree / "scripts" / "kaola-acp.py"

    def row_for(self, payload: dict, session: str) -> dict:
        match = [row for row in payload["rows"] if row["session"] == session]
        self.assertEqual(len(match), 1, payload)
        return match[0]

    def test_recorded_path_missing_is_reported_by_status_and_list(self) -> None:
        """A recorded runner path that no longer resolves is named, not silent."""
        session = "codex-KPR-i165-missing"
        cli = self._installed_cli("codex")
        _result, started = self.run_cli("codex", "start", session=session, argv0=cli)
        self.assertEqual(started.get("state"), "ready", started)
        _result, before = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIn("kaola-tmux.sh", before.get("script_paths") or {}, before)
        self.assertNotIn("recorded-path-missing", before.get("reported_drift") or [], before)
        # The checkout moved away: one recorded path no longer resolves - a
        # missing path yields no digest and is neither "changed" nor
        # "unchanged" for the byte comparison.
        (cli.parent / "kaola-tmux.sh").unlink()
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIn("recorded-path-missing", status.get("reported_drift") or [], status)
        self.assertIn("kaola-tmux.sh", status.get("missing_files") or [], status)
        # It is evidence only: no block, no stale.
        self.assertIs(status.get("stale"), False, status.get("stale_reasons"))
        self.assertEqual(status.get("stale_reasons"), [])

        row = self.row_for(self.run_list(cli), session)
        self.assertIn("recorded-path-missing", row.get("reported_drift") or [], row)
        self.assertIn("kaola-tmux.sh", row.get("missing_files") or [], row)
        self.assertIs(row.get("stale"), False, row)

    def test_seat_freshness_names_a_missing_recorded_path_without_blocking(self) -> None:
        """A recorded path that no longer resolves is named, and never blocks.

        Issue #179 removed the install-root-mismatch condition: a moved or
        deleted recorded path is this same fact, and an in-place reinstall is
        already the byte comparison.
        """
        acp = load_module(CLI, "acp165unit")
        project_scripts = PROJECT / "scripts"
        holder_sha = hashlib.sha256(
            (project_scripts / "kaola-acp-holder.py").read_bytes()).hexdigest()
        missing_facts = {
            "runner_build": holder_sha[:12],
            "script_paths": {
                "kaola-acp-holder.py": {
                    "path": str(project_scripts / "kaola-acp-holder.py"),
                    "sha256": holder_sha,
                },
                "kaola-tmux.sh": {
                    "path": str(self.root / "gone" / "kaola-tmux.sh"),
                    "sha256": "0" * 64,
                },
            },
        }
        missing = acp.seat_freshness(missing_facts)
        self.assertIn("recorded-path-missing", missing["reported_drift"])
        self.assertEqual(missing["missing_files"], ["kaola-tmux.sh"])
        self.assertIs(missing["stale"], False)

    def test_locate_module_untouched_by_this_issue(self) -> None:
        """Regression guard: the locator contract is not the surface this issue changes."""
        locate = load_module(LOCATE, "locate165")
        self.assertTrue(hasattr(locate, "registration_facts"))
        self.assertFalse(hasattr(locate, "seat_freshness"))


if __name__ == "__main__":
    unittest.main()
