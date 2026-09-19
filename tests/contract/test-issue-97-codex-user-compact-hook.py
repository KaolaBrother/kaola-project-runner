#!/usr/bin/env python3
"""Issue #97 contract: the Codex USER-level compact-recovery entry.

An outer Codex Agent that uses the installed ``kaola-delegator`` delegates
projects from any repository, so the Issue #75 project-level entry (bound to
one Host session at one canonical root) cannot cover it. ``user-install``
merges exactly one Runner-owned entry into ``${CODEX_HOME:-~/.codex}/hooks.json``
whose ``user-emit`` prints a short CONDITIONAL payload on every
``SessionStart(compact)``. This suite pins:

- isolated CODEX_HOME with a preset Kaola Workflow user hook and a
  user-owned entry: install, reinstall, status, and uninstall change only the
  Runner-owned entry and assets; foreign entries and event lists are preserved
  byte-for-byte in content; no backup copy is ever made; malformed or
  null-shaped configuration is refused before any write;
- the user layer binds nothing: ``--project-root`` and ``--session-id`` are
  refused, and the project actions refuse ``--codex-home``;
- ``user-emit`` fires for ``SessionStart(compact)`` only, from any cwd, and is
  silent exactly when a legacy project-level Runner entry in the session's
  cwd is bound to that very session (the predicate the project ``emit`` fires
  on) -- so one compaction never carries two Runner blocks, while an unbound or
  other-session project entry still gets the user payload;
- the payload is conditional (already-using-the-Skill sessions re-read the
  installed Skill and continue from records; everyone else does nothing), never
  infers a role from cwd, and fits well inside Codex's default
  additionalContext threshold;
- ``status``/``user-status`` never echo a foreign entry's command.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts" / "kaola-codex-compact-hook.py"
USER_PAYLOAD_SOURCE = PROJECT / "templates" / "codex-host" / "compact-recovery-user.md"
USER_ENTRY_ID = "kaola-project-runner:user-compact-context"
PROJECT_ENTRY_ID = "kaola-project-runner:compact-context"

SECRET = "hunter2-do-not-echo"
FOREIGN_WORKFLOW = {
    "matcher": "compact",
    "hooks": [
        {
            "type": "command",
            "command": 'cat "/x/kaola-workflow-codex-compact-recovery.md"',
            "timeout": 5,
        }
    ],
    "description": "Inject the generated Codex compact-recovery prompt after context compaction",
    "id": "kaola-workflow:compact-context",
}
FOREIGN_USER = {
    "hooks": [{"type": "command", "command": f"/usr/bin/env TOKEN={SECRET} /bin/true"}],
    "id": "user-owned:startup-notes",
}
HOST_SESSION_ID = "0192b5f4-0000-7000-8000-0000000000aa"


def run_hook(*cli: str, stdin: str | None = None, env: dict | None = None) -> dict:
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *cli],
        capture_output=True,
        text=True,
        input=stdin,
        env=run_env,
        timeout=60,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert lines, f"{cli} produced no receipt: {proc.stderr}"
    receipt = json.loads(lines[-1])
    receipt["_rc"] = proc.returncode
    receipt["_stderr"] = proc.stderr
    receipt["_stdout"] = proc.stdout
    return receipt


def hook_input(cwd: Path, session_id: str = HOST_SESSION_ID, **overrides) -> str:
    """The official SessionStart command-hook stdin shape."""
    event = {
        "session_id": session_id,
        "transcript_path": "/t/rollout.jsonl",
        "cwd": str(cwd),
        "hook_event_name": "SessionStart",
        "source": "compact",
        "model": "gpt-5-codex",
        "permission_mode": "default",
    }
    event.update(overrides)
    return json.dumps(event)


class UserLayer(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i97.")
        base = Path(os.path.realpath(self.tmp.name))
        self.codex_home = base / "codex-home"
        self.codex_home.mkdir()
        self.hooks_path = self.codex_home / "hooks.json"
        self.assets = self.codex_home / "kaola-project-runner" / "hooks"
        self.repo = base / "repo"
        self.repo.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # -- helpers ----------------------------------------------------------

    def seed_foreign(self) -> dict:
        doc = {
            "hooks": {
                "PreToolUse": [],
                "SubagentStart": [],
                "SessionStart": [FOREIGN_WORKFLOW, FOREIGN_USER],
            }
        }
        self.hooks_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return doc

    def doc(self) -> dict:
        return json.loads(self.hooks_path.read_text(encoding="utf-8")) if self.hooks_path.exists() else {}

    def session_entries(self) -> list:
        return (self.doc().get("hooks") or {}).get("SessionStart") or []

    def ours(self) -> list:
        return [e for e in self.session_entries() if e.get("id") == USER_ENTRY_ID]

    def foreign(self) -> list:
        return [e for e in self.session_entries() if e.get("id") != USER_ENTRY_ID]

    def user(self, action: str, *extra: str) -> dict:
        return run_hook(action, "--codex-home", str(self.codex_home), *extra)

    def installed_command(self) -> str:
        return self.ours()[0]["hooks"][0]["command"]

    def run_installed(self, stdin: str) -> subprocess.CompletedProcess:
        """Run the exact installed hook command the way Codex would."""
        return subprocess.run(
            ["/bin/sh", "-c", self.installed_command()],
            capture_output=True, text=True, input=stdin, timeout=30,
        )

    def emit(self, stdin: str) -> str:
        return self.run_installed(stdin).stdout

    # -- AC1: isolated CODEX_HOME, only Runner-owned content changes -------

    def test_install_appends_ours_and_preserves_foreign(self) -> None:
        seeded = self.seed_foreign()
        receipt = self.user("user-install")
        self.assertEqual(receipt["result"], "ok", receipt)
        self.assertTrue(receipt["changed"])
        self.assertEqual(receipt["entry_id"], USER_ENTRY_ID)
        self.assertEqual(receipt["foreign_session_start"], 2)
        self.assertTrue(receipt["trust_review_required"])
        self.assertEqual(len(self.ours()), 1)
        self.assertEqual(self.foreign(), seeded["hooks"]["SessionStart"])
        doc = self.doc()
        self.assertEqual(doc["hooks"]["PreToolUse"], [])
        self.assertEqual(doc["hooks"]["SubagentStart"], [])
        entry = self.ours()[0]
        self.assertEqual(entry["matcher"], "compact")
        self.assertEqual(entry["hooks"][0]["type"], "command")
        self.assertTrue(entry["hooks"][0]["command"].endswith(" user-emit"))
        self.assertEqual(entry["hooks"][0]["timeout"], 5)
        self.assertEqual(
            (self.assets / "compact-recovery-user.md").read_bytes(),
            USER_PAYLOAD_SOURCE.read_bytes(),
        )
        self.assertEqual((self.assets / "kaola-codex-compact-hook.py").read_bytes(), SCRIPT.read_bytes())
        self.assertFalse((self.assets / "binding.json").exists(), "the user layer binds nothing")
        self.assertFalse((self.repo / ".codex").exists(), "no project layer is touched")

    def test_reinstall_is_idempotent_and_makes_no_backup(self) -> None:
        self.seed_foreign()
        self.assertEqual(self.user("user-install")["result"], "ok")
        before = self.hooks_path.read_bytes()
        receipt = self.user("user-install")
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(receipt["changed"])
        self.assertEqual(self.hooks_path.read_bytes(), before)
        self.assertEqual(len(self.ours()), 1)
        siblings = sorted(p.name for p in self.codex_home.iterdir())
        self.assertEqual(siblings, ["hooks.json", "kaola-project-runner"])

    def test_fresh_codex_home_gets_only_ours(self) -> None:
        receipt = self.user("user-install")
        self.assertEqual(receipt["result"], "ok")
        self.assertEqual(self.doc(), {"hooks": {"SessionStart": self.ours()}})

    def test_status_reports_without_echoing_commands(self) -> None:
        self.seed_foreign()
        receipt = self.user("user-status")
        self.assertEqual(receipt["result"], "ok")
        self.assertFalse(receipt["installed"])
        self.assertEqual(receipt["session_start_entries"], 2)
        self.assertEqual(self.session_entries(), [FOREIGN_WORKFLOW, FOREIGN_USER], "status never writes")
        self.user("user-install")
        receipt = self.user("user-status")
        self.assertTrue(receipt["installed"])
        self.assertTrue(receipt["payload_present"])
        self.assertTrue(receipt["emitter_present"])
        self.assertEqual(receipt["entry_hook_count"], 1)
        self.assertEqual(receipt["session_start_entries"], 3)
        for text in (receipt["_stdout"], receipt["_stderr"]):
            self.assertNotIn(SECRET, text)
            self.assertNotIn("kaola-workflow-codex-compact-recovery", text)
            self.assertNotIn("user-emit", text, "even our own command is not echoed")

    def test_uninstall_removes_only_ours(self) -> None:
        seeded = self.seed_foreign()
        self.user("user-install")
        receipt = self.user("user-uninstall")
        self.assertEqual(receipt["result"], "ok")
        self.assertTrue(receipt["changed"])
        self.assertEqual(receipt["removed_entries"], 1)
        self.assertTrue(receipt["payload_removed"])
        self.assertTrue(receipt["emitter_removed"])
        self.assertEqual(self.doc(), seeded)
        self.assertFalse((self.codex_home / "kaola-project-runner").exists())
        self.assertEqual(sorted(p.name for p in self.codex_home.iterdir()), ["hooks.json"])
        again = self.user("user-uninstall")
        self.assertEqual(again["result"], "ok")
        self.assertFalse(again["changed"])

    def test_uninstall_leaves_no_residue_when_only_ours(self) -> None:
        self.user("user-install")
        self.user("user-uninstall")
        self.assertEqual(list(self.codex_home.iterdir()), [])

    def test_uninstall_keeps_foreign_asset_siblings(self) -> None:
        # A foreign file inside our asset parent (e.g. another tool's copy)
        # keeps the directory alive; only our two leaves are removed.
        self.user("user-install")
        stray = self.codex_home / "kaola-project-runner" / "notes.txt"
        stray.write_text("keep me\n", encoding="utf-8")
        self.user("user-uninstall")
        self.assertTrue(stray.exists())
        self.assertFalse(self.assets.exists())

    def test_malformed_and_null_shapes_refused_before_any_write(self) -> None:
        cases = {
            "not json": "{nope",
            "top-level list": "[]",
            "hooks null": json.dumps({"hooks": None}),
            "hooks list": json.dumps({"hooks": []}),
            "SessionStart null": json.dumps({"hooks": {"SessionStart": None}}),
            "SessionStart object": json.dumps({"hooks": {"SessionStart": {}}}),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.hooks_path.write_text(text, encoding="utf-8")
                for action in ("user-install", "user-status", "user-uninstall"):
                    receipt = self.user(action)
                    self.assertEqual(receipt["result"], "refused", (label, action, receipt))
                    self.assertEqual(receipt["_rc"], 1)
                self.assertEqual(self.hooks_path.read_text(encoding="utf-8"), text)
                self.assertFalse((self.codex_home / "kaola-project-runner").exists())

    def test_user_layer_refuses_project_options_and_vice_versa(self) -> None:
        for extra in (("--project-root", str(self.repo)), ("--session-id", HOST_SESSION_ID)):
            with self.subTest(extra):
                receipt = self.user("user-install", *extra)
                self.assertEqual(receipt["result"], "refused")
                self.assertIn(extra[0], receipt["reasons"][0])
                self.assertFalse(self.hooks_path.exists())
        for action in ("status", "prepare", "uninstall"):
            with self.subTest(action):
                receipt = run_hook(action, "--project-root", str(self.repo), "--codex-home", str(self.codex_home))
                self.assertEqual(receipt["result"], "refused")
                self.assertIn("--codex-home", receipt["reasons"][0])
        self.assertFalse((self.repo / ".codex").exists())

    def test_codex_home_refusals(self) -> None:
        missing = run_hook("user-install", "--codex-home", str(self.codex_home / "absent"))
        self.assertEqual(missing["result"], "refused")
        self.assertIn("not a directory", missing["reasons"][0])
        home = run_hook("user-install", "--codex-home", str(Path.home()))
        self.assertEqual(home["result"], "refused")
        self.assertIn("user home directory", home["reasons"][0])
        root = run_hook("user-install", "--codex-home", "/")
        self.assertEqual(root["result"], "refused")
        self.assertIn("filesystem root", root["reasons"][0])
        # CODEX_HOME is the default when --codex-home is omitted.
        receipt = run_hook("user-status", env={"CODEX_HOME": str(self.codex_home)})
        self.assertEqual(receipt["result"], "ok")
        self.assertEqual(receipt["codex_home"], str(self.codex_home))

    def test_hooks_json_symlink_cannot_escape_codex_home(self) -> None:
        outside = Path(self.tmp.name) / "outside-hooks.json"
        outside.write_text(json.dumps({"hooks": {"SessionStart": [FOREIGN_USER]}}), encoding="utf-8")
        os.symlink(outside, self.hooks_path)
        receipt = self.user("user-install")
        self.assertEqual(receipt["result"], "refused")
        self.assertIn("outside the Codex home", receipt["reasons"][0])
        self.assertEqual(json.loads(outside.read_text(encoding="utf-8")), {"hooks": {"SessionStart": [FOREIGN_USER]}})
        self.assertFalse((self.codex_home / "kaola-project-runner").exists())

    # -- user-emit ------------------------------------------------------------

    def test_emit_fires_for_compact_from_any_cwd(self) -> None:
        self.seed_foreign()
        self.user("user-install")
        payload = USER_PAYLOAD_SOURCE.read_text(encoding="utf-8")
        other = Path(self.tmp.name) / "another-repo"
        other.mkdir()
        for cwd in (self.repo, other, self.codex_home):
            with self.subTest(str(cwd)):
                self.assertEqual(self.emit(hook_input(cwd)), payload)
                self.assertEqual(self.emit(hook_input(cwd, session_id="any-other-session")), payload)

    def test_emit_only_for_session_start_compact(self) -> None:
        self.user("user-install")
        for overrides in (
            {"source": "startup"},
            {"source": "resume"},
            {"source": "clear"},
            {"hook_event_name": "PreCompact", "source": "compact"},
            {"hook_event_name": "PostCompact", "source": "manual"},
        ):
            with self.subTest(overrides):
                proc = self.run_installed(hook_input(self.repo, **overrides))
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout, "")

    def test_emit_malformed_stdin_is_silent_and_exit_zero(self) -> None:
        self.user("user-install")
        for stdin in ("", "not json", "[]", "null", json.dumps({"source": "compact"})):
            with self.subTest(stdin):
                proc = self.run_installed(stdin)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout, "")

    def test_emit_defers_only_to_a_bound_legacy_project_entry(self) -> None:
        """Coexistence with the Issue #75 project layer: no double injection."""
        self.seed_foreign()
        self.user("user-install")
        payload = USER_PAYLOAD_SOURCE.read_text(encoding="utf-8")
        # prepare = entry present, binding inert -> the project emit is silent,
        # so the user layer must still speak.
        prepared = run_hook("prepare", "--project-root", str(self.repo))
        self.assertEqual(prepared["result"], "ok")
        self.assertEqual(self.emit(hook_input(self.repo)), payload)
        # bind this exact session -> the project emit fires, ours is silent.
        bound = run_hook("bind", "--project-root", str(self.repo), "--session-id", HOST_SESSION_ID)
        self.assertEqual(bound["result"], "ok")
        self.assertEqual(self.emit(hook_input(self.repo)), "")
        # the project emit itself does fire for that event: exactly one block.
        project_cmd = [
            e for e in json.loads((self.repo / ".codex" / "hooks.json").read_text())["hooks"]["SessionStart"]
            if e.get("id") == PROJECT_ENTRY_ID
        ][0]["hooks"][0]["command"]
        project_out = subprocess.run(
            ["/bin/sh", "-c", project_cmd], capture_output=True, text=True,
            input=hook_input(self.repo), timeout=30,
        ).stdout
        self.assertIn("KPR-COMPACT-RECOVERY-V1", project_out)
        self.assertNotIn("KPR-USER-COMPACT-RECOVERY", project_out)
        # another session in the same repo (a Worker) is not bound: ours speaks.
        self.assertEqual(self.emit(hook_input(self.repo, session_id="worker-session")), payload)
        # the bound session compacting in a different repository: ours speaks.
        elsewhere = Path(self.tmp.name) / "elsewhere"
        elsewhere.mkdir()
        self.assertEqual(self.emit(hook_input(elsewhere)), payload)
        # a subdirectory of the bound root is not the canonical root: ours speaks
        # (the project emit would not fire there either).
        sub = self.repo / "sub"
        sub.mkdir()
        self.assertEqual(self.emit(hook_input(sub)), payload)
        # removing the project entry (migration) hands recovery back to ours.
        run_hook("uninstall", "--project-root", str(self.repo))
        self.assertEqual(self.emit(hook_input(self.repo)), payload)

    def test_emit_ignores_a_project_entry_that_lost_its_binding_or_entry(self) -> None:
        self.user("user-install")
        payload = USER_PAYLOAD_SOURCE.read_text(encoding="utf-8")
        run_hook("install", "--project-root", str(self.repo), "--session-id", HOST_SESSION_ID)
        binding = self.repo / ".codex" / "kaola-project-runner" / "hooks" / "binding.json"
        # binding names another root -> the project emit would not fire.
        binding.write_text(json.dumps({"session_id": HOST_SESSION_ID, "project_root": "/elsewhere"}), encoding="utf-8")
        self.assertEqual(self.emit(hook_input(self.repo)), payload)
        # unreadable binding -> ours speaks.
        binding.write_text("{nope", encoding="utf-8")
        self.assertEqual(self.emit(hook_input(self.repo)), payload)
        # binding fine but the project entry was removed from hooks.json -> ours speaks.
        binding.write_text(json.dumps({"session_id": HOST_SESSION_ID, "project_root": str(self.repo)}), encoding="utf-8")
        (self.repo / ".codex" / "hooks.json").write_text(json.dumps({"hooks": {"SessionStart": [FOREIGN_WORKFLOW]}}), encoding="utf-8")
        self.assertEqual(self.emit(hook_input(self.repo)), payload)

    def test_emit_copy_is_self_contained(self) -> None:
        # The installed emitter reads the payload beside itself, never the
        # checkout: renaming the source template must not change what fires.
        self.user("user-install")
        expected = USER_PAYLOAD_SOURCE.read_bytes()
        proc = subprocess.run(
            [sys.executable, str(self.assets / "kaola-codex-compact-hook.py"), "user-emit"],
            capture_output=True, input=hook_input(self.repo).encode(), timeout=30,
            cwd=str(self.codex_home),
        )
        self.assertEqual(proc.stdout, expected)

    # -- payload ------------------------------------------------------------

    def test_payload_is_short_conditional_and_never_guesses_from_cwd(self) -> None:
        text = USER_PAYLOAD_SOURCE.read_text(encoding="utf-8")
        self.assertLess(len(text.encode("utf-8")), 2048, "well inside the default 2500-token additionalContext threshold")
        self.assertIn("KPR-USER-COMPACT-RECOVERY-V1", text)
        self.assertIn("<!-- KPR-USER-COMPACT-RECOVERY-START -->", text)
        self.assertIn("<!-- KPR-USER-COMPACT-RECOVERY-END -->", text)
        self.assertNotIn("KPR-COMPACT-RECOVERY-V1", text, "distinct from the project-level marker")
        for needle in (
            "only if this session was already using",
            "`kaola-delegator`",
            "`kaola-project-runner`",
            "Otherwise ignore it",
            "do not start delegation or project work",
            "never infer a role or a project from the working directory",
            "Completely re-read that installed Skill",
            "not from memory",
            "Continue from existing records only",
            "current authorization",
            "Runner `status` receipts",
            "Git, worktree, Workflow, and Issue",
            "Do not re-intake, re-claim, start a second Host, resend prompts, or",
            "re-dispatch in-flight work",
            "no binding table",
            "session registry, or heartbeat",
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
