#!/usr/bin/env python3
"""Issue #75: the Codex SessionStart(compact) recovery carrier is merge-safe.

kaola-codex-compact-hook.py owns exactly one entry in the CONSUMING
project's ``.codex/hooks.json`` (``kaola-project-runner:compact-context``)
plus its asset copies under ``<repo>/.codex/kaola-project-runner/hooks/``.
The project layer is what lets two projects coexist: project A's binding
can never overwrite project B's, and uninstalling B leaves A untouched.
Foreign entries -- Workflow-owned, user-owned, anything -- keep their JSON
content untouched (the file is re-serialized canonically on write;
byte-level formatting is not promised), and a malformed hooks.json is
refused before any write. These tests run the real script against
throwaway project directories only; no user-global config is touched.
"""

from __future__ import annotations

import json
import os
import shlex
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


HOST_SESSION_ID = "0192b5f4-0000-7000-8000-0000000000aa"


def run_hook(*cli: str, stdin: str | None = None) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *cli],
        capture_output=True,
        text=True,
        input=stdin,
        timeout=60,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert lines, f"{cli} produced no receipt: {proc.stderr}"
    receipt = json.loads(lines[-1])
    receipt["_rc"] = proc.returncode
    receipt["_stderr"] = proc.stderr
    return receipt


def install(repo: Path, session_id: str = HOST_SESSION_ID) -> dict:
    return run_hook(
        "install",
        "--project-root", str(repo),
        "--session-id", session_id,
    )


def uninstall(repo: Path) -> dict:
    return run_hook("uninstall", "--project-root", str(repo))


def hooks_path(repo: Path) -> Path:
    return repo / ".codex" / "hooks.json"


def hooks_dir(repo: Path) -> Path:
    return repo / ".codex" / "kaola-project-runner" / "hooks"


def hook_input(repo: Path, **overrides) -> str:
    """The official SessionStart command-hook stdin shape (binary-verified)."""
    event = {
        "session_id": HOST_SESSION_ID,
        "transcript_path": "/t/rollout.jsonl",
        "cwd": str(repo),
        "hook_event_name": "SessionStart",
        "source": "compact",
        "model": "gpt-5-codex",
        "permission_mode": "default",
    }
    event.update(overrides)
    return json.dumps(event)


def hooks_doc(repo: Path) -> dict:
    path = hooks_path(repo)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def session_entries(repo: Path) -> list:
    return (hooks_doc(repo).get("hooks") or {}).get("SessionStart") or []


def our_entries(repo: Path) -> list:
    return [
        e for e in session_entries(repo)
        if isinstance(e, dict) and e.get("id") == ENTRY_ID
    ]


def installed_command(repo: Path) -> str:
    return our_entries(repo)[0]["hooks"][0]["command"]


def run_installed(repo: Path, stdin: str) -> subprocess.CompletedProcess:
    """Run the exact installed hook command the way Codex would."""
    return subprocess.run(
        ["/bin/sh", "-c", installed_command(repo)],
        capture_output=True, text=True, input=stdin, timeout=30,
    )


class CodexCompactHookContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i75-repo.")
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.repo = Path(os.path.realpath(self.repo))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def seed_foreign(self, repo: Path | None = None) -> dict:
        repo = repo or self.repo
        doc = {
            "hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "/bin/true"}], "id": "user-owned:pre-bash"}],
                "SessionStart": [FOREIGN_WORKFLOW, FOREIGN_OTHER],
            }
        }
        path = hooks_path(repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return doc

    def test_fresh_install_creates_entry_and_assets(self) -> None:
        receipt = install(self.repo)
        self.assertEqual(receipt["result"], "ok")
        self.assertEqual(receipt["_rc"], 0)
        entries = our_entries(self.repo)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["matcher"], "compact")
        handler = entry["hooks"][0]
        self.assertEqual(handler["type"], "command")
        emitter = hooks_dir(self.repo) / "kaola-codex-compact-hook.py"
        self.assertEqual(
            handler["command"], f"python3 {shlex.quote(str(emitter))} emit"
        )
        self.assertEqual(handler["timeout"], 5)
        payload = hooks_dir(self.repo) / "compact-recovery.md"
        self.assertTrue(payload.is_file())
        self.assertEqual(payload.read_bytes(), PAYLOAD_SOURCE.read_bytes())
        self.assertTrue(emitter.is_file())
        self.assertEqual(emitter.read_bytes(), SCRIPT.read_bytes())
        binding = json.loads(
            (hooks_dir(self.repo) / "binding.json").read_text()
        )
        self.assertEqual(
            binding,
            {
                "session_id": HOST_SESSION_ID,
                "project_root": os.path.realpath(self.repo),
            },
        )

    def test_install_requires_host_binding(self) -> None:
        """Install without the designated-Host binding refuses, no writes."""
        for cli in (
            ("install", "--project-root", str(self.repo)),
            ("install", "--session-id", HOST_SESSION_ID),
            ("install",),
        ):
            receipt = run_hook(*cli)
            self.assertEqual(receipt["result"], "refused", cli)
            self.assertNotEqual(receipt["_rc"], 0, cli)
        self.assertFalse((self.repo / ".codex").exists())

    def test_install_preserves_foreign_entries(self) -> None:
        self.seed_foreign()
        receipt = install(self.repo)
        self.assertEqual(receipt["result"], "ok")
        session = session_entries(self.repo)
        self.assertEqual(len(session), 3)
        self.assertIn(FOREIGN_WORKFLOW, session)
        self.assertIn(FOREIGN_OTHER, session)
        doc = hooks_doc(self.repo)
        pre = doc["hooks"]["PreToolUse"]
        self.assertEqual(pre[0]["id"], "user-owned:pre-bash")

    def test_reinstall_is_idempotent(self) -> None:
        self.seed_foreign()
        install(self.repo)
        first = hooks_path(self.repo).read_bytes()
        receipt = install(self.repo)
        second = hooks_path(self.repo).read_bytes()
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(receipt["changed"])
        self.assertEqual(first, second)
        self.assertEqual(len(our_entries(self.repo)), 1)

    def test_two_phase_bootstrap_covers_first_session(self) -> None:
        """prepare before Host start (inert), bind after — first compact covered.

        Hooks load at session start, so the entry must exist before the Host
        launches; the session id can only be bound afterwards, and binding
        must not touch the loaded hooks.json.
        """
        receipt = run_hook("prepare", "--project-root", str(self.repo))
        self.assertEqual(receipt["result"], "ok")
        self.assertIsNone(receipt["session_id"])
        binding = json.loads((hooks_dir(self.repo) / "binding.json").read_text())
        self.assertEqual(
            binding,
            {"session_id": None, "project_root": os.path.realpath(self.repo)},
        )
        self.assertEqual(len(our_entries(self.repo)), 1)
        payload = (
            hooks_dir(self.repo) / "compact-recovery.md"
        ).read_text(encoding="utf-8")

        # Inert: any session id emits nothing — including the eventual Host's.
        inert = run_installed(self.repo, hook_input(self.repo))
        self.assertEqual(inert.returncode, 0, inert.stderr)
        self.assertEqual(inert.stdout, "")
        self.assertFalse(
            run_hook("status", "--project-root", str(self.repo))["bound"]
        )

        # Host started; its real session id becomes known. bind touches ONLY
        # binding.json — the loaded entry must stay byte-identical.
        before = hooks_path(self.repo).read_bytes()
        bound = run_hook(
            "bind", "--project-root", str(self.repo),
            "--session-id", HOST_SESSION_ID,
        )
        self.assertEqual(bound["result"], "ok")
        self.assertTrue(bound["changed"])
        self.assertEqual(hooks_path(self.repo).read_bytes(), before)
        self.assertTrue(
            run_hook("status", "--project-root", str(self.repo))["bound"]
        )

        fired = run_installed(self.repo, hook_input(self.repo))
        self.assertEqual(fired.stdout, payload)
        worker = run_installed(
            self.repo,
            hook_input(self.repo, session_id="ffffffff-0000-0000-0000-0000000000ee"),
        )
        self.assertEqual(worker.stdout, "")

    def test_bind_refuses_without_prepare(self) -> None:
        """bind never creates the entry — it only rebinds a prepared one."""
        receipt = run_hook(
            "bind", "--project-root", str(self.repo),
            "--session-id", HOST_SESSION_ID,
        )
        self.assertEqual(receipt["result"], "refused")
        self.assertNotEqual(receipt["_rc"], 0)
        self.assertFalse((self.repo / ".codex").exists())

    def test_bind_refuses_malformed_or_null_config(self) -> None:
        """bind still validates config shape before writing binding.json."""
        self.seed_foreign()
        path = hooks_path(self.repo)
        for doc in ({"hooks": None}, "{not json"):
            path.write_text(
                doc if isinstance(doc, str) else json.dumps(doc),
                encoding="utf-8",
            )
            before = path.read_bytes()
            receipt = run_hook(
                "bind", "--project-root", str(self.repo),
                "--session-id", HOST_SESSION_ID,
            )
            self.assertEqual(receipt["result"], "refused", doc)
            self.assertNotEqual(receipt["_rc"], 0, doc)
            self.assertEqual(path.read_bytes(), before, doc)
            self.assertFalse(
                (self.repo / ".codex" / "kaola-project-runner").exists(), doc
            )

    def test_reinstall_rebinds_session_without_touching_entry(self) -> None:
        """Rebinding is a data-file change: the reviewed entry stays stable."""
        install(self.repo)
        before = hooks_path(self.repo).read_bytes()
        new_id = "00000000-0000-0000-0000-0000000000ff"
        receipt = install(self.repo, session_id=new_id)
        self.assertEqual(receipt["result"], "ok")
        self.assertTrue(receipt["changed"])
        self.assertEqual(hooks_path(self.repo).read_bytes(), before)
        binding = json.loads(
            (hooks_dir(self.repo) / "binding.json").read_text()
        )
        self.assertEqual(binding["session_id"], new_id)
        bound = run_installed(self.repo, hook_input(self.repo, session_id=new_id))
        self.assertNotEqual(bound.stdout, "")
        stale = run_installed(self.repo, hook_input(self.repo))
        self.assertEqual(stale.stdout, "")

    def test_two_projects_coexist_and_uninstall_is_local(self) -> None:
        """Project A/B each bind their own Host; removing B never harms A."""
        repo_b = Path(self.tmp.name) / "repo-b"
        repo_b.mkdir()
        repo_b = Path(os.path.realpath(repo_b))
        sid_a = "0192b5f4-0000-7000-8000-0000000000aa"
        sid_b = "0192b5f4-0000-7000-8000-0000000000bb"
        self.seed_foreign()
        self.seed_foreign(repo_b)
        self.assertEqual(install(self.repo, session_id=sid_a)["result"], "ok")
        self.assertEqual(install(repo_b, session_id=sid_b)["result"], "ok")

        bind_a = json.loads((hooks_dir(self.repo) / "binding.json").read_text())
        bind_b = json.loads((hooks_dir(repo_b) / "binding.json").read_text())
        self.assertEqual(bind_a["session_id"], sid_a)
        self.assertEqual(bind_b["session_id"], sid_b)
        self.assertEqual(bind_a["project_root"], os.path.realpath(self.repo))
        self.assertEqual(bind_b["project_root"], os.path.realpath(repo_b))

        payload = PAYLOAD_SOURCE.read_text(encoding="utf-8")
        proc_a = run_installed(self.repo, hook_input(self.repo, session_id=sid_a))
        self.assertEqual(proc_a.stdout, payload)
        proc_b = run_installed(repo_b, hook_input(repo_b, session_id=sid_b))
        self.assertEqual(proc_b.stdout, payload)
        cross = run_installed(repo_b, hook_input(repo_b, session_id=sid_a))
        self.assertEqual(cross.stdout, "")

        gone = uninstall(repo_b)
        self.assertEqual(gone["result"], "ok")
        self.assertFalse((repo_b / ".codex" / "kaola-project-runner").exists())
        self.assertEqual(
            session_entries(repo_b), [FOREIGN_WORKFLOW, FOREIGN_OTHER]
        )
        still = run_installed(self.repo, hook_input(self.repo, session_id=sid_a))
        self.assertEqual(still.stdout, payload)
        self.assertEqual(len(our_entries(self.repo)), 1)

    def test_uninstall_removes_only_ours(self) -> None:
        self.seed_foreign()
        install(self.repo)
        receipt = uninstall(self.repo)
        self.assertEqual(receipt["result"], "ok")
        self.assertEqual(receipt["removed_entries"], 1)
        session = session_entries(self.repo)
        self.assertEqual(session, [FOREIGN_WORKFLOW, FOREIGN_OTHER])
        self.assertFalse((self.repo / ".codex" / "kaola-project-runner").exists())
        again = uninstall(self.repo)
        self.assertEqual(again["result"], "ok")
        self.assertEqual(again["removed_entries"], 0)

    def test_uninstall_leaves_no_residue_when_only_ours(self) -> None:
        """A hooks.json that held only our entry is removed with .codex."""
        install(self.repo)
        self.assertTrue(hooks_path(self.repo).exists())
        receipt = uninstall(self.repo)
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(hooks_path(self.repo).exists())
        self.assertFalse((self.repo / ".codex").exists())

    def test_malformed_hooks_json_is_refused_not_clobbered(self) -> None:
        path = hooks_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        before = path.read_bytes()
        for action in ("install", "uninstall", "status"):
            receipt = run_hook(action, "--project-root", str(self.repo))
            self.assertEqual(receipt["result"], "refused", action)
            self.assertNotEqual(receipt["_rc"], 0, action)
        self.assertEqual(path.read_bytes(), before)

    def test_null_shapes_refused_before_any_write(self) -> None:
        """JSON-null `hooks` / `hooks.SessionStart` are malformed config.

        Refusal must be atomic: no payload, no emitter, no binding, no
        re-serialized hooks.json — the file stays byte-identical.
        """
        for doc in (
            {"hooks": None},
            {"hooks": {"SessionStart": None}},
        ):
            path = hooks_path(self.repo)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc), encoding="utf-8")
            before = path.read_bytes()
            receipt = install(self.repo)
            self.assertEqual(receipt["result"], "refused", doc)
            self.assertNotEqual(receipt["_rc"], 0, doc)
            self.assertEqual(path.read_bytes(), before, doc)
            self.assertFalse(
                (self.repo / ".codex" / "kaola-project-runner").exists(), doc
            )
            refused = uninstall(self.repo)
            self.assertEqual(refused["result"], "refused", doc)
            self.assertEqual(path.read_bytes(), before, doc)

    def test_status_is_read_only(self) -> None:
        receipt = run_hook("status", "--project-root", str(self.repo))
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(receipt["installed"])
        self.assertFalse((self.repo / ".codex").exists())

    def test_emit_only_for_bound_host(self) -> None:
        """Host-only filter: payload leaves stdout only on exact match."""
        install(self.repo)
        payload = (
            hooks_dir(self.repo) / "compact-recovery.md"
        ).read_text(encoding="utf-8")

        bound = run_installed(self.repo, hook_input(self.repo))
        self.assertEqual(bound.returncode, 0, bound.stderr)
        self.assertEqual(bound.stdout, payload)

        worker = run_installed(
            self.repo,
            hook_input(self.repo, session_id="ffffffff-0000-0000-0000-0000000000ee"),
        )
        self.assertEqual(worker.returncode, 0, worker.stderr)
        self.assertEqual(worker.stdout, "")

        other_repo = run_installed(
            self.repo, hook_input(self.repo, cwd="/tmp/kpr-i75-elsewhere")
        )
        self.assertEqual(other_repo.returncode, 0, other_repo.stderr)
        self.assertEqual(other_repo.stdout, "")

    def test_emit_only_for_compact_source(self) -> None:
        install(self.repo)
        for source in ("startup", "resume", "clear"):
            proc = run_installed(self.repo, hook_input(self.repo, source=source))
            self.assertEqual(proc.returncode, 0, source)
            self.assertEqual(proc.stdout, "", source)
        non_hook = run_installed(
            self.repo, hook_input(self.repo, hook_event_name="UserPromptSubmit")
        )
        self.assertEqual(non_hook.returncode, 0)
        self.assertEqual(non_hook.stdout, "")

    def test_emit_malformed_stdin_is_silent(self) -> None:
        install(self.repo)
        for bad in ("", "not json", "[1,2]", '{"session_id": 5}', "null"):
            proc = run_installed(self.repo, bad)
            self.assertEqual(proc.returncode, 0, bad)
            self.assertEqual(proc.stdout, "", bad)

    def test_emit_missing_or_bad_binding_is_silent(self) -> None:
        install(self.repo)
        binding = hooks_dir(self.repo) / "binding.json"
        for bad in ("not json", "null", "[]", '{"session_id": 1}'):
            binding.write_text(bad, encoding="utf-8")
            proc = run_installed(self.repo, hook_input(self.repo))
            self.assertEqual(proc.returncode, 0, bad)
            self.assertEqual(proc.stdout, "", bad)
        binding.unlink()
        proc = run_installed(self.repo, hook_input(self.repo))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_metachar_root_command_quotes_and_only_reads(self) -> None:
        """A project path with shell metacharacters cannot alter execution."""
        evil = Path(self.tmp.name) / "odd \"q\" $(touch PWNED)'s"
        evil.mkdir()
        evil = Path(os.path.realpath(evil))
        receipt = install(evil)
        self.assertEqual(receipt["result"], "ok")
        command = installed_command(evil)
        self.assertIn("'", command)
        emitter = hooks_dir(evil) / "kaola-codex-compact-hook.py"
        parts = shlex.split(command)
        self.assertEqual(parts, ["python3", str(emitter), "emit"])
        proc = subprocess.run(
            ["/bin/sh", "-c", command],
            capture_output=True, text=True, input=hook_input(evil), timeout=30,
            cwd=self.tmp.name,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = hooks_dir(evil) / "compact-recovery.md"
        self.assertEqual(proc.stdout, payload.read_text(encoding="utf-8"))
        for root, _dirs, files in os.walk(self.tmp.name):
            self.assertNotIn("PWNED", files, f"side effect in {root}")

    def test_no_backup_copy_of_config_is_made(self) -> None:
        """Foreign config may carry secrets — never duplicated into backups.

        A secret-bearing foreign hooks.json is preserved in place (entry
        content untouched); no hooks.json.kaola-backup-* or other copy of its
        content is ever created — on install, re-install, or uninstall.
        """
        secret = "sk-test-foreign-secret-0000"
        doc = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [{"type": "command", "command": secret}],
                        "id": "user-owned:secret-entry",
                    }
                ]
            }
        }
        path = hooks_path(self.repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

        install(self.repo)
        install(self.repo)  # re-install / idempotent path
        receipt = uninstall(self.repo)
        self.assertEqual(receipt["removed_entries"], 1)

        copies = []
        for f in (self.repo / ".codex").rglob("*"):
            if f.is_file() and secret in f.read_text(
                encoding="utf-8", errors="replace"
            ):
                copies.append(f)
        self.assertEqual(copies, [path])
        self.assertEqual(
            list((self.repo / ".codex").glob("hooks.json.kaola-backup-*")), []
        )
        remaining = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            remaining["hooks"]["SessionStart"][0]["hooks"][0]["command"],
            secret,
        )

    def test_prepare_preserves_existing_binding(self) -> None:
        """prepare → bind Host → prepare must never silently unbind."""
        install(self.repo)
        before = (hooks_dir(self.repo) / "binding.json").read_bytes()
        receipt = run_hook("prepare", "--project-root", str(self.repo))
        self.assertEqual(receipt["result"], "ok")
        self.assertTrue(receipt["binding_preserved"])
        self.assertEqual(receipt["session_id"], HOST_SESSION_ID)
        self.assertEqual(
            (hooks_dir(self.repo) / "binding.json").read_bytes(), before
        )
        payload = (
            hooks_dir(self.repo) / "compact-recovery.md"
        ).read_text(encoding="utf-8")
        fired = run_installed(self.repo, hook_input(self.repo))
        self.assertEqual(fired.stdout, payload)

    def test_prepare_refuses_ambiguous_binding(self) -> None:
        """An unclassifiable binding is refused before any write."""
        root = os.path.realpath(self.repo)
        for bad in (
            "not json",
            "[]",
            '{"session_id": 5, "project_root": "%s"}' % root,
            '{"session_id": "%s", "project_root": "/elsewhere"}'
            % HOST_SESSION_ID,
            # bound-looking shapes that can never match: no project_root,
            # empty id, whitespace-only id
            '{"session_id": "%s"}' % HOST_SESSION_ID,
            '{"session_id": "", "project_root": "%s"}' % root,
            '{"session_id": "   ", "project_root": "%s"}' % root,
        ):
            binding = hooks_dir(self.repo) / "binding.json"
            binding.parent.mkdir(parents=True, exist_ok=True)
            binding.write_text(bad, encoding="utf-8")
            receipt = run_hook("prepare", "--project-root", str(self.repo))
            self.assertEqual(receipt["result"], "refused", bad)
            self.assertNotEqual(receipt["_rc"], 0, bad)
            self.assertEqual(binding.read_text(encoding="utf-8"), bad, bad)
            self.assertFalse(hooks_path(self.repo).exists(), bad)
            binding.unlink()

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

    def test_proof_detail_exists_for_each_installed_skill(self) -> None:
        """The block's proof detail must live in a file each Skill ships.

        Regression pin for the Delegator-path defect: the durable block and
        per-send carrier must not send a kaola-delegator Host to quote a
        marker inside references/zcode-compact-recovery.md — the generated
        kaola-delegator ships no such file. Its checkable detail lives in
        references/handoff.md.
        """
        blocks = self.ref.split("```text")
        self.assertGreaterEqual(len(blocks), 3, "durable block + carrier")
        durable = blocks[1]
        carrier = blocks[2]

        # kaola-project-runner path: named file exists in the generated
        # surface and carries the reload marker.
        self.assertIn("kaola-project-runner", durable)
        self.assertIn("references/zcode-compact-recovery.md", durable)
        runner_ref = (
            PROJECT
            / "skills"
            / "kaola-project-runner"
            / "references"
            / "zcode-compact-recovery.md"
        )
        self.assertTrue(runner_ref.is_file())
        self.assertIn("KPR-SKILL-RELOAD-V1", runner_ref.read_text())

        # kaola-delegator path: the block points at references/handoff.md —
        # a file the Delegator genuinely ships — and names its checkable
        # detail. A delegator is never sent to zcode-compact-recovery.md.
        for text, name in ((durable, "durable block"), (carrier, "carrier")):
            self.assertIn("kaola-delegator", text, name)
            self.assertIn("references/handoff.md", text, name)
            self.assertIn("orchestrator-main", text, name)
            self.assertNotIn(
                "kaola-delegator's references/zcode-compact-recovery.md",
                text,
                name,
            )

        # Generated-surface check when the Delegator ships on this branch
        # (it lands via main's #74/#86 — absent before rebase).
        for cand in (
            PROJECT / "skills" / "kaola-delegator" / "references" / "handoff.md",
            PROJECT
            / "templates"
            / "kaola-delegator"
            / "references"
            / "handoff.md.tmpl",
        ):
            if cand.is_file():
                self.assertIn(
                    "orchestrator-main", cand.read_text(encoding="utf-8"), cand
                )

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
