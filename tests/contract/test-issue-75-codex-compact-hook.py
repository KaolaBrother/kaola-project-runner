#!/usr/bin/env python3
"""Issue #75: the Codex SessionStart(compact) recovery carrier is merge-safe.

kaola-codex-compact-hook.py owns exactly one hooks.json entry
(``kaola-project-runner:compact-context``) plus its payload copy. Foreign
entries -- Workflow-owned, user-owned, anything -- keep their JSON content
untouched (the file is re-serialized canonically on write; byte-level
formatting is not promised), and a malformed hooks.json is refused rather
than clobbered. These tests run the real script against throwaway CODEX_HOME
directories only.
"""

from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts" / "kaola-codex-compact-hook.py"
PAYLOAD_SOURCE = PROJECT / "templates" / "codex-host" / "compact-recovery.md"
ENTRY_ID = "kaola-project-runner:compact-context"

FOREIGN_WORKFLOW = {
    "matcher": "compact",
    "hooks": [{"type": "command", "command": 'cat "/x/workflow.md"', "timeout": 5}],
    "description": "foreign workflow entry",
    "id": "kaola-workflow:compact-context",
}
FOREIGN_OTHER = {
    "hooks": [{"type": "command", "command": "/bin/true"}],
    "id": "user-owned:startup-notes",
}


def run_hook(home: Path, action: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), action, "--codex-home", str(home)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert lines, f"{action} produced no receipt: {proc.stderr}"
    receipt = json.loads(lines[-1])
    receipt["_rc"] = proc.returncode
    receipt["_stderr"] = proc.stderr
    return receipt


def hooks_doc(home: Path) -> dict:
    path = home / "hooks.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def session_entries(home: Path) -> list:
    return (hooks_doc(home).get("hooks") or {}).get("SessionStart") or []


def our_entries(home: Path) -> list:
    return [
        e for e in session_entries(home)
        if isinstance(e, dict) and e.get("id") == ENTRY_ID
    ]


class CodexCompactHookContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i75-codex-home.")
        self.home = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def seed_foreign(self) -> dict:
        doc = {
            "hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "/bin/true"}], "id": "user-owned:pre-bash"}],
                "SessionStart": [FOREIGN_WORKFLOW, FOREIGN_OTHER],
            }
        }
        (self.home / "hooks.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return doc

    def test_fresh_install_creates_entry_and_payload(self) -> None:
        receipt = run_hook(self.home, "install")
        self.assertEqual(receipt["result"], "ok")
        self.assertEqual(receipt["_rc"], 0)
        entries = our_entries(self.home)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["matcher"], "compact")
        handler = entry["hooks"][0]
        self.assertEqual(handler["type"], "command")
        payload = self.home / "kaola-project-runner" / "hooks" / "compact-recovery.md"
        self.assertEqual(handler["command"], f"cat {shlex.quote(str(payload))}")
        self.assertEqual(handler["timeout"], 5)
        self.assertTrue(payload.is_file())
        self.assertEqual(payload.read_bytes(), PAYLOAD_SOURCE.read_bytes())

    def test_install_preserves_foreign_entries(self) -> None:
        self.seed_foreign()
        receipt = run_hook(self.home, "install")
        self.assertEqual(receipt["result"], "ok")
        session = session_entries(self.home)
        self.assertEqual(len(session), 3)
        self.assertIn(FOREIGN_WORKFLOW, session)
        self.assertIn(FOREIGN_OTHER, session)
        doc = hooks_doc(self.home)
        pre = doc["hooks"]["PreToolUse"]
        self.assertEqual(pre[0]["id"], "user-owned:pre-bash")

    def test_reinstall_is_idempotent(self) -> None:
        self.seed_foreign()
        run_hook(self.home, "install")
        first = (self.home / "hooks.json").read_bytes()
        receipt = run_hook(self.home, "install")
        second = (self.home / "hooks.json").read_bytes()
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(receipt["changed"])
        self.assertEqual(first, second)
        self.assertEqual(len(our_entries(self.home)), 1)

    def test_uninstall_removes_only_ours(self) -> None:
        self.seed_foreign()
        run_hook(self.home, "install")
        receipt = run_hook(self.home, "uninstall")
        self.assertEqual(receipt["result"], "ok")
        self.assertEqual(receipt["removed_entries"], 1)
        session = session_entries(self.home)
        self.assertEqual(session, [FOREIGN_WORKFLOW, FOREIGN_OTHER])
        payload = self.home / "kaola-project-runner" / "hooks" / "compact-recovery.md"
        self.assertFalse(payload.exists())
        again = run_hook(self.home, "uninstall")
        self.assertEqual(again["result"], "ok")
        self.assertEqual(again["removed_entries"], 0)

    def test_malformed_hooks_json_is_refused_not_clobbered(self) -> None:
        path = self.home / "hooks.json"
        path.write_text("{not json", encoding="utf-8")
        before = path.read_bytes()
        for action in ("install", "uninstall", "status"):
            receipt = run_hook(self.home, action)
            self.assertEqual(receipt["result"], "refused", action)
            self.assertNotEqual(receipt["_rc"], 0, action)
        self.assertEqual(path.read_bytes(), before)

    def test_status_is_read_only(self) -> None:
        receipt = run_hook(self.home, "status")
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(receipt["installed"])
        self.assertFalse((self.home / "hooks.json").exists())
        self.assertFalse((self.home / "kaola-project-runner").exists())

    def test_metachar_home_command_quotes_and_only_reads(self) -> None:
        """A CODEX_HOME with shell metacharacters cannot alter execution."""
        evil = Path(self.tmp.name) / "odd \"q\" $(touch PWNED)'s"
        receipt = run_hook(evil, "install")
        self.assertEqual(receipt["result"], "ok")
        command = our_entries(evil)[0]["hooks"][0]["command"]
        payload = evil / "kaola-project-runner" / "hooks" / "compact-recovery.md"
        self.assertEqual(command, f"cat {shlex.quote(str(payload))}")
        self.assertIn("'", command)
        proc = subprocess.run(
            ["/bin/sh", "-c", command],
            capture_output=True, text=True, timeout=15, cwd=self.tmp.name,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, payload.read_text(encoding="utf-8"))
        for root, _dirs, files in os.walk(self.tmp.name):
            self.assertNotIn("PWNED", files, f"side effect in {root}")

    def test_backup_is_written_0600(self) -> None:
        """The content-addressed backup mirrors config at 0600, not umask."""
        self.seed_foreign()
        run_hook(self.home, "install")
        backups = list(self.home.glob("hooks.json.kaola-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        receipt = run_hook(self.home, "uninstall")
        self.assertEqual(receipt["removed_entries"], 1)
        for backup in self.home.glob("hooks.json.kaola-backup-*"):
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)

    def test_payload_teaches_role_reload_and_no_repeat(self) -> None:
        text = PAYLOAD_SOURCE.read_text(encoding="utf-8")
        for needle in (
            "kaola-project-runner",
            "kaola-delegator",
            "workflow-state.md",
            "mission-list.md",
            "do not re-intake, re-claim, restart",
        ):
            self.assertIn(needle.lower(), text.lower())
        self.assertIn("KPR-COMPACT-RECOVERY", text)


class DocMaintenanceSurface(unittest.TestCase):
    """The doc-maintenance boundary renders into the orchestrator Skill."""

    def setUp(self) -> None:
        orch = PROJECT / "skills" / "kaola-project-runner"
        self.skill = (orch / "SKILL.md").read_text(encoding="utf-8")
        self.ref_path = orch / "references" / "doc-maintenance.md"
        self.ref = self.ref_path.read_text(encoding="utf-8")
        limits = json.loads(
            (PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8")
        )
        self.main_budget = limits["main_skill_bytes"]
        self.ref_budget = limits["reference_bytes"]

    def test_pointer_and_dispatch_duty_render(self) -> None:
        self.assertIn("the doc-impact call", self.skill)
        self.assertIn("doc-maintenance](references/doc-maintenance.md)", self.skill)
        self.assertRegex(self.skill, r"doc\s+docking")

    def test_reference_covers_all_four_duties(self) -> None:
        for needle in (
            "doc ledger",
            "second acceptance gate",
            "documentation docking",
            "ADR",
            "owner-authored",
            "safe boundary",
            "per-beat",
            "not a keyword match",
        ):
            self.assertIn(needle, self.ref)

    def test_budgets_hold(self) -> None:
        skill_path = PROJECT / "skills" / "kaola-project-runner" / "SKILL.md"
        self.assertLessEqual(skill_path.stat().st_size, self.main_budget)
        self.assertLessEqual(self.ref_path.stat().st_size, self.ref_budget)


class ZcodeCompactCarrierSurface(unittest.TestCase):
    """The ZCode Host/Skill-layer carrier renders into the orchestrator Skill.

    ZCode has no compact hook (verified: SessionStart fires on
    startup/resume only), so recovery rides the controlling Agent's next
    prompt. These tests pin the rendered carrier and the host-startup
    pointer that leads an Agent to it.
    """

    def setUp(self) -> None:
        orch = PROJECT / "skills" / "kaola-project-runner"
        self.ref_path = orch / "references" / "zcode-compact-recovery.md"
        self.ref = self.ref_path.read_text(encoding="utf-8")
        self.host_startup = (
            orch / "references" / "host-startup.md"
        ).read_text(encoding="utf-8")
        limits = json.loads(
            (PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8")
        )
        self.ref_budget = limits["reference_bytes"]

    def test_carrier_renders_with_markers_and_boundaries(self) -> None:
        for needle in (
            "KPR-ZCODE-RECOVERY-V1",
            "KPR-SKILL-RELOAD-V1",
            "never re-intake, re-claim, restart sessions, or re-dispatch",
            "never a per-send check, never a",
            "transport gate, never a cursor ledger",
            "UserPromptSubmit",
        ):
            self.assertIn(needle, self.ref)

    def test_host_startup_points_at_the_carrier(self) -> None:
        self.assertIn(
            "zcode-compact-recovery.md](zcode-compact-recovery.md)",
            self.host_startup,
        )
        self.assertIn("compacted mid-run", self.host_startup)

    def test_budget_holds(self) -> None:
        self.assertLessEqual(self.ref_path.stat().st_size, self.ref_budget)


if __name__ == "__main__":
    unittest.main()
