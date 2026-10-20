#!/usr/bin/env python3
"""Issue #375: installer drift backups live outside skill discovery roots.

The tests drive the real installer in a temporary HOME and the real
``installed_worker_skills`` / start path with a mock ACP agent. They prove:

* a copy-mode repair moves the previous Skill into the runner-owned quarantine
  and leaves no ``.drift.*`` sibling in the discovery root;
* an install also quarantines stale ``.drift`` / ``.old`` / ``.tmp`` siblings it
  owns, and records every original path in the quarantine manifest;
* a planted hidden backup with old scripts is reported as
  ``stale_install_backups`` with its quarantine route and never causes
  ``worker-skill-build-skew`` or blocks ``start``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
INSTALLER = PROJECT / "scripts" / "install-local.sh"
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable
WORKER = "zcode-kaola-project-runner"


def clean_env(home: Path, root: Path, **extra: str) -> dict[str, str]:
    env = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "TMPDIR": str(root),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "PYTHONUNBUFFERED": "1",
        "LANG": "C",
    }
    env.update(extra)
    return env


def make_fixture(root: Path) -> Path:
    """A minimal checkout that passes its own render/check and installs copies."""
    repo = root / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "skills").mkdir()
    shutil.copy2(INSTALLER, repo / "scripts" / "install-local.sh")
    (repo / "scripts" / "install-local.sh").chmod(0o755)
    render = repo / "scripts" / "render-skills.py"
    render.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n", encoding="utf-8")
    render.chmod(0o755)
    for name in (WORKER, "kaola-project-runner", "kaola-delegator"):
        skill = repo / "skills" / name
        (skill / "scripts").mkdir(parents=True)
        (skill / ".generated-by-kaola-project-runner").write_text(name + "\n", encoding="utf-8")
        (skill / "SKILL.md").write_text("# fixture Skill\n", encoding="utf-8")
        (skill / "scripts" / "kaola-acp.py").write_text(
            "#!/usr/bin/env python3\nprint('new')\n", encoding="utf-8")
    return repo


def run_installer(repo: Path, home: Path, root: Path, *args: str,
                  env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = clean_env(home, root)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(repo / "scripts" / "install-local.sh"), *args],
        capture_output=True, text=True, env=env, timeout=120,
    )


def hidden_backups(root: Path) -> list[Path]:
    return sorted(
        path for path in root.iterdir()
        if any(marker in path.name for marker in (".drift.", ".old.", ".tmp."))
    )


def quarantine_manifests(home: Path) -> list[dict]:
    rows: list[dict] = []
    base = home / ".local" / "state" / "kaola-project-runner" / "install-quarantine"
    for path in sorted(base.glob("run-*/manifest.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


class InstallerQuarantineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = make_fixture(self.root)
        self.skills = self.home / ".agents" / "skills"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install(self, *args: str) -> subprocess.CompletedProcess:
        return run_installer(
            self.repo, self.home, self.root,
            "--skills-dir", str(self.skills), "--method", "copy", "--no-bin-links",
            *args,
        )

    def test_repair_leaves_no_drift_backup_in_the_discovery_root(self) -> None:
        first = self.install("--platform", "zcode")
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        installed = self.skills / WORKER
        drifted = installed / "scripts" / "kaola-acp.py"
        drifted.write_text(drifted.read_text(encoding="utf-8") + "# drifted\n",
                           encoding="utf-8")

        # A leftover from an older install run is also cleared, not ignored.
        stale = self.skills / f".{WORKER}.drift.999"
        (stale / "scripts").mkdir(parents=True)
        (stale / "scripts" / "kaola-acp.py").write_text("old\n", encoding="utf-8")

        second = self.install("--platform", "zcode")
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertIn("quarantined:", second.stdout)
        self.assertIn("previous copy quarantined:", second.stdout)
        self.assertEqual(hidden_backups(self.skills), [])

        rows = quarantine_manifests(self.home)
        self.assertEqual(len(rows), 2, rows)
        originals = {row["original_path"] for row in rows}
        self.assertEqual(originals, {str(installed), str(stale)})
        reasons = {row["original_path"]: row["reason"] for row in rows}
        self.assertEqual(reasons[str(installed)], "repair")
        self.assertEqual(reasons[str(stale)], "stale install backup")
        for row in rows:
            self.assertTrue(Path(row["quarantine_path"]).exists(), row)
            self.assertIn(str(self.skills), row["root"], row)
        repaired = next(row for row in rows if row["reason"] == "repair")
        self.assertTrue(
            (Path(repaired["quarantine_path"]) / "scripts" / "kaola-acp.py")
            .read_text(encoding="utf-8").endswith("# drifted\n"),
            repaired,
        )

    def test_quarantine_stale_backups_is_the_recovery_command(self) -> None:
        backup = self.skills / ".x-kaola-project-runner.drift.123"
        (backup / "scripts").mkdir(parents=True)
        (backup / "scripts" / "kaola-acp.py").write_text("old\n", encoding="utf-8")
        result = run_installer(
            self.repo, self.home, self.root,
            "--quarantine-stale-backups", "--skills-dir", str(self.skills),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("quarantined:", result.stdout)
        self.assertIn("nothing was deleted", result.stdout)
        self.assertFalse(backup.exists())
        rows = quarantine_manifests(self.home)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["original_path"], str(backup))
        self.assertEqual(rows[0]["reason"], "stale install backup")


class StartSkewReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True,
                       capture_output=True)
        self.installed = self.root / "installed" / "codex-kaola-project-runner"
        shutil.copytree(PROJECT / "skills" / "codex-kaola-project-runner", self.installed)
        self.skills = self.home / ".codex" / "skills"
        self.backup = self.skills / ".x-kaola-project-runner.drift.123"
        (self.backup / "scripts").mkdir(parents=True)
        (self.backup / "scripts" / "kaola-acp.py").write_text("old\n", encoding="utf-8")
        (self.backup / "SKILL.md").write_text(
            "---\nname: x-kaola-project-runner\n---\n", encoding="utf-8")
        # A hidden copy of the main Skill must not reach the separate main-Skill
        # comparison either.
        self.main_backup = self.skills / ".kaola-project-runner.drift.124"
        self.main_backup.mkdir()
        (self.main_backup / "SKILL.md").write_text(
            "---\nname: kaola-project-runner\n---\n", encoding="utf-8")
        self.session = "codex-KPR-i375"
        self.started = False

    def tearDown(self) -> None:
        if self.started:
            self.run_cli("stop", "--force", check=False)
        self.tmp.cleanup()

    def env(self) -> dict[str, str]:
        return clean_env(
            self.home, self.root,
            KAOLA_ACP_RECORD_ROOT=str(self.records),
            KAOLA_LAUNCH_BACKEND="direct",
        )

    def run_cli(self, *args: str, check: bool = True) -> tuple[subprocess.CompletedProcess, dict]:
        argv = [PYTHON, str(self.installed / "scripts" / "kaola-acp.py"),
                "codex", *args, "--repo", str(self.repo), "--session", self.session]
        if args and args[0] in ("start", "drain-restart"):
            argv += ["--command",
                     f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"]
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(), timeout=120)
        payload: dict = {}
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            payload = json.loads(lines[-1])
        if check and result.returncode != 0:
            self.fail(f"{args}: {payload or result.stderr[-1000:]}")
        return result, payload

    def test_hidden_backup_is_reported_not_a_skew_refusal(self) -> None:
        result, started = self.run_cli("start")
        self.started = True
        self.assertEqual(result.returncode, 0, started)
        self.assertEqual(started.get("state"), "ready", started)
        self.assertIsNone(started.get("reason"), started)
        self.assertNotEqual(started.get("reason"), "worker-skill-build-skew", started)
        self.assertNotEqual(started.get("reason"), "main-skill-build-skew", started)
        self.assertEqual(started.get("stale_install_backups"),
                         [str(self.main_backup), str(self.backup)])
        self.assertEqual(started.get("stale_install_backup_count"), 2)
        self.assertEqual(started.get("stale_install_backup_roots"), [str(self.skills)])
        recovery = started.get("stale_install_backup_recovery") or ""
        self.assertIn("--quarantine-stale-backups", recovery)
        self.assertIn(str(self.skills), recovery)

        # The route's command really moves the reported backup.
        quarantine = subprocess.run(
            [str(INSTALLER), "--quarantine-stale-backups", "--skills-dir", str(self.skills)],
            capture_output=True, text=True, env=self.env(), timeout=60,
        )
        self.assertEqual(quarantine.returncode, 0, quarantine.stderr + quarantine.stdout)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.main_backup.exists())
        self.assertIn("quarantined:", quarantine.stdout)


if __name__ == "__main__":
    unittest.main()
