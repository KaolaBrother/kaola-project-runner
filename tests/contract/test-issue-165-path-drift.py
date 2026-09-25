#!/usr/bin/env python3
"""Issue #165: a removed or moved recorded path, or a reinstall under a
different root, is reported by name.

Follow-up N3 from #162 review round 2. #162 recorded absolute ``script_paths``
and reported byte drift, but a recorded path that no longer resolves (the
checkout moved or was deleted) and a seat whose recorded files live under a
different install root both went unreported. ``status``/``list`` now name
``recorded-path-missing`` and ``install-root-mismatch``. Both are evidence
only: they never set ``stale`` and never gate transport.

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
        (``<platform>-kaola-project-runner``) so sibling trees share one parent
        and the per-platform expected root resolves to a real path.
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
        self.assertNotIn("install-root-mismatch", before.get("reported_drift") or [], before)
        # The checkout moved away: one recorded path no longer resolves. The
        # root still matches (this same install), so only the missing file is
        # named - a missing path yields no digest and is neither "changed" nor
        # "unchanged" for the byte comparison.
        (cli.parent / "kaola-tmux.sh").unlink()
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIn("recorded-path-missing", status.get("reported_drift") or [], status)
        self.assertIn("kaola-tmux.sh", status.get("missing_files") or [], status)
        self.assertNotIn("install-root-mismatch", status.get("reported_drift") or [], status)
        # It is evidence only: no block, no stale.
        self.assertIs(status.get("stale"), False, status.get("stale_reasons"))
        self.assertEqual(status.get("stale_reasons"), [])

        row = self.row_for(self.run_list(cli), session)
        self.assertIn("recorded-path-missing", row.get("reported_drift") or [], row)
        self.assertIn("kaola-tmux.sh", row.get("missing_files") or [], row)
        self.assertIs(row.get("stale"), False, row)

    def test_install_root_mismatch_is_reported_by_status_and_list(self) -> None:
        """A seat whose own platform tree is genuinely re-rooted is named."""
        session = "codex-KPR-i165-reroot"
        # The seat was started from a different root than the one its own
        # platform is expected to live under now. Every recorded path still
        # resolves, so only the root difference is named.
        old_root = self.root / "old" / "codex-kaola-project-runner"
        shutil.copytree(PROJECT / "skills" / "codex-kaola-project-runner", old_root)
        old_cli = old_root / "scripts" / "kaola-acp.py"
        new_cli = self._installed_cli("codex")
        _result, started = self.run_cli("codex", "start", session=session, argv0=old_cli)
        self.assertEqual(started.get("state"), "ready", started)
        _result, status = self.run_cli("codex", "status", session=session, argv0=new_cli)
        self.assertIn("install-root-mismatch", status.get("reported_drift") or [], status)
        self.assertNotIn("recorded-path-missing", status.get("reported_drift") or [], status)
        self.assertNotEqual(status.get("recorded_root"), status.get("install_root"), status)
        self.assertEqual(status.get("recorded_root"), str(old_root.resolve()))
        self.assertEqual(status.get("install_root"),
                         str((self.root / "installed" / "codex-kaola-project-runner").resolve()))
        self.assertIs(status.get("stale"), False, status.get("stale_reasons"))

        # Issue #165 reviewer note 4: the list row carries both roots too.
        row = self.row_for(self.run_list(new_cli), session)
        self.assertIn("install-root-mismatch", row.get("reported_drift") or [], row)
        self.assertEqual(row.get("recorded_root"), str(old_root.resolve()), row)
        self.assertEqual(row.get("install_root"), status.get("install_root"), row)
        self.assertIs(row.get("stale"), False, row)

    def test_another_platforms_seat_is_not_flagged_by_a_sibling_tree(self) -> None:
        """The documented Host sweeps run ``list`` from ONE platform's tree.

        The expected root is the seat's OWN platform tree, so a claude-code
        seat listed from the zcode sibling tree is not a false mismatch.
        """
        session = "claude-code-KPR-i165-xplat"
        cc_cli = self._installed_cli("claude-code")
        zc_cli = self._installed_cli("zcode")
        _result, started = self.run_cli(
            "claude-code", "start", session=session, argv0=cc_cli)
        self.assertEqual(started.get("state"), "ready", started)
        expected_root = str(
            (self.root / "installed" / "claude-code-kaola-project-runner").resolve())

        own = self.row_for(self.run_list(cc_cli), session)
        sibling = self.row_for(self.run_list(zc_cli), session)
        for row in (own, sibling):
            self.assertNotIn("install-root-mismatch", row.get("reported_drift") or [], row)
            self.assertNotIn("recorded-path-missing", row.get("reported_drift") or [], row)
            self.assertEqual(row.get("recorded_root"), expected_root, row)
            self.assertEqual(row.get("install_root"), expected_root, row)
            self.assertIs(row.get("stale"), False, row)

    def test_seat_freshness_names_both_conditions_without_blocking(self) -> None:
        """The named conditions are exact, and neither sets ``stale``."""
        acp = load_module(CLI, "acp165unit")
        project_scripts = PROJECT / "scripts"
        holder_sha = hashlib.sha256(
            (project_scripts / "kaola-acp-holder.py").read_bytes()).hexdigest()
        # A recorded tree that is this install, with one recorded path removed.
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
        missing = acp.seat_freshness("codex", str(self.repo), missing_facts)
        self.assertIn("recorded-path-missing", missing["reported_drift"])
        self.assertEqual(missing["missing_files"], ["kaola-tmux.sh"])
        self.assertIs(missing["stale"], False)

        # A recorded tree other than this install, with every path present.
        moved_tree = self.root / "moved-root" / "scripts"
        moved_tree.mkdir(parents=True)
        moved = moved_tree / "kaola-acp-holder.py"
        moved.write_bytes((project_scripts / "kaola-acp-holder.py").read_bytes())
        reroot_facts = {
            "runner_build": holder_sha[:12],
            "script_paths": {
                "kaola-acp-holder.py": {"path": str(moved), "sha256": holder_sha},
            },
        }
        reroot = acp.seat_freshness("codex", str(self.repo), reroot_facts)
        self.assertIn("install-root-mismatch", reroot["reported_drift"])
        self.assertEqual(reroot["missing_files"], [])
        self.assertEqual(reroot["recorded_root"], str((self.root / "moved-root").resolve()))
        self.assertIs(reroot["stale"], False)

    def test_expected_root_follows_the_seats_own_platform(self) -> None:
        """Loaded from an installed tree, the expected root is the platform sibling.

        A claude-code seat recorded under the sibling claude-code tree is not a
        mismatch even though this zcode CLI runs from its own tree; a genuinely
        re-rooted claude-code seat still is.
        """
        cc_cli = self._installed_cli("claude-code")
        zc_cli = self._installed_cli("zcode")
        zc = load_module(zc_cli, "acp165xplat")
        cc_tree = (self.root / "installed" / "claude-code-kaola-project-runner").resolve()
        holder_sha = hashlib.sha256(
            (cc_cli.parent / "kaola-acp-holder.py").read_bytes()).hexdigest()
        facts = {
            "runner_build": holder_sha[:12],
            "script_paths": {
                "kaola-acp-holder.py": {
                    "path": str(cc_tree / "scripts" / "kaola-acp-holder.py"),
                    "sha256": holder_sha,
                },
            },
        }
        sibling = zc.seat_freshness("claude-code", str(self.repo), facts)
        self.assertNotIn("install-root-mismatch", sibling["reported_drift"], sibling)
        self.assertEqual(sibling["recorded_root"], str(cc_tree))
        self.assertEqual(sibling["install_root"], str(cc_tree))

        elsewhere = self.root / "elsewhere" / "scripts"
        elsewhere.mkdir(parents=True)
        moved = elsewhere / "kaola-acp-holder.py"
        moved.write_bytes((cc_cli.parent / "kaola-acp-holder.py").read_bytes())
        facts["script_paths"]["kaola-acp-holder.py"] = {
            "path": str(moved), "sha256": holder_sha,
        }
        reroot = zc.seat_freshness("claude-code", str(self.repo), facts)
        self.assertIn("install-root-mismatch", reroot["reported_drift"], reroot)
        self.assertEqual(reroot["install_root"], str(cc_tree))
        self.assertIs(reroot["stale"], False)

    def test_locate_module_untouched_by_this_issue(self) -> None:
        """Regression guard: the locator contract is not the surface this issue changes."""
        locate = load_module(LOCATE, "locate165")
        self.assertTrue(hasattr(locate, "registration_facts"))
        self.assertFalse(hasattr(locate, "seat_freshness"))


if __name__ == "__main__":
    unittest.main()
