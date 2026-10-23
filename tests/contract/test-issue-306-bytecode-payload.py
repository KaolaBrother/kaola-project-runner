#!/usr/bin/env python3
"""Issue #306: git-ignored Python bytecode is not Skill payload.

A checkout with ``__pycache__/*.pyc`` under ``skills/*/scripts/`` passes
``render-skills.py --check``. ``install-local.sh`` then installs without
deleting that bytecode. A non-bytecode extra file still fails both gates.
``--verify-install`` and the host-bundle verifier use the same exclusion.

Issue #407: the fixture is a real Git checkout, not a plain copy. A pinned
bridge can only be verified against a checkout (the pin names a commit,
demands ancestry of HEAD, and bounds the P-R delta), so the fixture commits
a content stage R and a pin P and exercises ``--check`` at both stages; this
keeps the suite green in the post-release pinned window without weakening
pin verification.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
COPY_IGNORE = shutil.ignore_patterns(
    ".git", ".kw", "__pycache__", "*.pyc", "*.pyo", "node_modules",
    "kaola-workflow", "docs",
)
ORCHESTRATOR = "kaola-project-runner"
WORKER = "grok-kaola-project-runner"
PYC_NAME = "kaola-compact-recovery.cpython-313.pyc"
PYC_REL = f"scripts/__pycache__/{PYC_NAME}"


def run(argv: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.pop("PYTHONDONTWRITEBYTECODE", None)
    if env:
        merged.update(env)
    return subprocess.run(argv, cwd=cwd, env=merged, text=True, capture_output=True)


def render_check(root: Path) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "-B", str(root / "scripts" / "render-skills.py"), "--check"], root)


def render_write(root: Path) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "-B", str(root / "scripts" / "render-skills.py"), "--write"], root)


def verify_install(root: Path, skills: Path) -> subprocess.CompletedProcess[str]:
    return run(
        [sys.executable, "-B", str(root / "scripts" / "render-skills.py"),
         "--verify-install", str(skills)],
        root,
    )


def git(root: Path, *args: str) -> str:
    # Issue #80: git >=2.47 `commit`/`merge`/`rebase` spawn a detached `maintenance run --auto`
    # child that repacks and rewrites .git after the command returns, racing TemporaryDirectory
    # teardown into Errno 66. Fixture git calls disable it; gc.auto=0 does not gate this spawn.
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "maintenance.auto",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    completed = run(["git", "-C", str(root), *args], root, env)
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def set_stage(root: Path, stage: str, commit: str | None = None, label: str | None = None) -> None:
    data: dict[str, object] = {"stage": stage}
    if commit is not None:
        data["commit"] = commit
    if label is not None:
        data["label"] = label
    (root / "templates" / "grok-bot" / "accepted-revision.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )


def content_checkout(root: Path) -> str:
    """Make the copy a real Git checkout and return its content-stage commit R.

    The copy is re-rendered at the content stage before its first commit, so the
    fixture is the same whether the project itself currently sits at a content or a
    pinned stage.
    """
    set_stage(root, "content")
    written = render_write(root)
    if written.returncode != 0:
        raise AssertionError(f"content-stage --write failed: {written.stderr}")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "content")
    return git(root, "rev-parse", "HEAD")


def pin_to(root: Path, content: str) -> None:
    """Commit the pin P naming the checkout's own content commit R."""
    set_stage(root, "pinned", commit=content, label="issue-306 fixture pin")
    written = render_write(root)
    if written.returncode != 0:
        raise AssertionError(f"pinned-stage --write failed: {written.stderr}")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "pin")


def plant_bytecode(root: Path) -> dict[Path, bytes]:
    """Bytecode under two Skill script trees, plus a loose ``.pyc`` and a note inside the cache."""
    planted: dict[Path, bytes] = {}
    specs = (
        (ORCHESTRATOR, PYC_NAME, b"orchestrator-bytecode"),
        (ORCHESTRATOR, "kaola-compact-recovery.cpython-313.pyo", b"orchestrator-opt"),
        (WORKER, "runtime.cpython-313.pyc", b"worker-bytecode"),
    )
    for skill, name, body in specs:
        path = root / "skills" / skill / "scripts" / "__pycache__" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        planted[path] = body
    note = root / "skills" / ORCHESTRATOR / "scripts" / "__pycache__" / "notes.txt"
    note.write_text("inside cache\n", encoding="utf-8")
    planted[note] = note.read_bytes()
    loose = root / "skills" / ORCHESTRATOR / "scripts" / "loose.pyc"
    loose.write_bytes(b"loose-bytecode")
    planted[loose] = loose.read_bytes()
    return planted


class BytecodePayload(unittest.TestCase):
    def test_entry_points_suppress_bytecode_writes(self) -> None:
        wrapper = (PROJECT / "skills" / WORKER / "scripts" / "runtime-tmux.sh").read_text(encoding="utf-8")
        grok_wrapper = (PROJECT / "skills" / WORKER / "scripts" / "grok-tmux.sh").read_text(encoding="utf-8")
        tmux = (PROJECT / "scripts" / "kaola-tmux.sh").read_text(encoding="utf-8")
        dispatch = (PROJECT / "scripts" / "kaola-dispatch.py").read_text(encoding="utf-8")
        self.assertIn("export PYTHONDONTWRITEBYTECODE=1\n", wrapper)
        self.assertIn("export PYTHONDONTWRITEBYTECODE=1\n", grok_wrapper)
        self.assertIn("export PYTHONDONTWRITEBYTECODE=1\n", tmux)
        self.assertIn("sys.dont_write_bytecode = True", dispatch)
        self.assertIn("kaola-compact-recovery.py", dispatch)

    def test_check_and_install_ignore_bytecode_and_reject_a_real_extra_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kaola-issue-306-") as temporary:
            tmp = Path(temporary)
            copy = tmp / "repo"
            shutil.copytree(PROJECT, copy, ignore=COPY_IGNORE)
            content = content_checkout(copy)
            home = tmp / "home"
            home.mkdir()

            plant_bytecode(copy)
            checked = render_check(copy)
            self.assertEqual(
                checked.returncode, 0,
                f"--check rejected bytecode at the content stage:\n{checked.stderr}\n{checked.stdout}",
            )
            self.assertIn("content stage, unpinned", checked.stdout)
            self.assertNotIn(PYC_NAME, checked.stderr)
            self.assertNotIn("notes.txt", checked.stderr)
            self.assertNotIn("loose.pyc", checked.stderr)

            # --write regenerates the Skill trees wholesale, so the planted bytecode
            # does not survive the pin write; runtime debris lands again afterwards.
            pin_to(copy, content)
            planted = plant_bytecode(copy)
            checked = render_check(copy)
            self.assertEqual(
                checked.returncode, 0,
                f"--check rejected bytecode at the pinned stage:\n{checked.stderr}\n{checked.stdout}",
            )
            self.assertIn(f"pinned at {content[:12]}, pin verified", checked.stdout)
            self.assertNotIn(PYC_NAME, checked.stderr)
            self.assertNotIn("notes.txt", checked.stderr)
            self.assertNotIn("loose.pyc", checked.stderr)

            verified = verify_install(copy, copy / "skills")
            self.assertEqual(
                verified.returncode, 0,
                f"--verify-install rejected bytecode:\n{verified.stderr}",
            )
            self.assertNotIn("unexpected", verified.stderr)

            dest = tmp / "dest" / "skills"
            installed = run(
                ["bash", str(copy / "scripts" / "install-local.sh"),
                 "--skills-dir", str(dest), "--method", "copy", "--platform", "grok",
                 "--no-bin-links"],
                copy,
                {"HOME": str(home), "CODEX_HOME": str(home / "codex"),
                 "PYTHON_BIN": sys.executable, "TMPDIR": str(tmp)},
            )
            self.assertEqual(
                installed.returncode, 0,
                f"install refused a bytecode checkout:\n{installed.stderr}\n{installed.stdout}",
            )
            self.assertIn("verify:", installed.stdout)
            self.assertNotIn("unexpected", installed.stderr)
            for path, body in planted.items():
                self.assertTrue(path.is_file(), f"install deleted {path}")
                self.assertEqual(path.read_bytes(), body, f"install rewrote {path}")
            self.assertFalse((dest / WORKER / "scripts" / "__pycache__").exists())
            self.assertFalse((dest / ORCHESTRATOR / "scripts" / "__pycache__").exists())
            self.assertTrue((dest / WORKER / "SKILL.md").is_file())

            extra = copy / "skills" / ORCHESTRATOR / "scripts" / "not-payload.txt"
            extra.write_text("real extra\n", encoding="utf-8")
            named = copy / "skills" / ORCHESTRATOR / "__pycache__"
            named.write_text("not a cache directory\n", encoding="utf-8")
            rejected = render_check(copy)
            self.assertNotEqual(rejected.returncode, 0, "--check accepted a real extra file")
            self.assertIn("unexpected scripts/not-payload.txt", rejected.stderr)
            self.assertIn("unexpected __pycache__", rejected.stderr)
            self.assertNotIn(PYC_NAME, rejected.stderr)
            self.assertNotIn("notes.txt", rejected.stderr)
            # The pinned stage still verifies; only the real extra file is rejected.
            self.assertNotIn("pin:", rejected.stderr)
            skewed = verify_install(copy, copy / "skills")
            self.assertNotEqual(skewed.returncode, 0)
            self.assertIn("not-payload.txt", skewed.stderr)
            self.assertNotIn(PYC_NAME, skewed.stderr)

            dest2 = tmp / "dest2" / "skills"
            refused = run(
                ["bash", str(copy / "scripts" / "install-local.sh"),
                 "--skills-dir", str(dest2), "--method", "copy", "--platform", "grok",
                 "--no-bin-links"],
                copy,
                {"HOME": str(home), "CODEX_HOME": str(home / "codex"),
                 "PYTHON_BIN": sys.executable, "TMPDIR": str(tmp)},
            )
            self.assertNotEqual(refused.returncode, 0, "install accepted a real extra file")
            self.assertIn("do not match their templates", refused.stderr)
            self.assertIn("not-payload.txt", refused.stderr)
            self.assertFalse(dest2.exists(), "pre-check wrote a destination after refusing")
            for path, body in planted.items():
                self.assertEqual(path.read_bytes(), body)

    def test_host_bundle_verifier_ignores_bytecode_only(self) -> None:
        verifier = PROJECT / "scripts" / "kaola-grok-bot-verify.py"
        with tempfile.TemporaryDirectory(prefix="kaola-issue-306-host-") as temporary:
            bundle = Path(temporary) / "grok-bot"
            shutil.copytree(PROJECT / "hosts" / "grok-bot", bundle)
            cache = bundle / "__pycache__"
            cache.mkdir()
            (cache / "bridge.cpython-313.pyc").write_bytes(b"bytecode")
            (bundle / "loose.pyo").write_bytes(b"opt")
            clean = run([sys.executable, "-B", str(verifier), str(bundle), "--repo", str(PROJECT)], PROJECT)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertNotIn("cpython", clean.stderr)
            self.assertNotIn("loose.pyo", clean.stderr)

            (bundle / "extra.txt").write_text("real extra\n", encoding="utf-8")
            dirty = run([sys.executable, "-B", str(verifier), str(bundle), "--repo", str(PROJECT)], PROJECT)
            self.assertNotEqual(dirty.returncode, 0)
            self.assertIn("extra.txt", dirty.stderr)
            self.assertNotIn("cpython", dirty.stderr)

            (bundle / "extra.txt").unlink()
            shutil.rmtree(cache)
            (bundle / "loose.pyo").unlink()
            (bundle / "__pycache__").write_text("not a directory\n", encoding="utf-8")
            named = run([sys.executable, "-B", str(verifier), str(bundle), "--repo", str(PROJECT)], PROJECT)
            self.assertNotEqual(named.returncode, 0, "a file named __pycache__ was ignored")
            self.assertIn("__pycache__", named.stderr)

    def test_dispatch_recovery_import_writes_no_bytecode(self) -> None:
        """The observed writer: dispatch imports kaola-compact-recovery.py in place."""
        with tempfile.TemporaryDirectory(prefix="kaola-issue-306-dispatch-") as temporary:
            tmp = Path(temporary)
            isolated = tmp / "scripts"
            isolated.mkdir()
            for name in ("kaola-dispatch.py", "kaola-record-contract.py",
                         "kaola-compact-recovery.py", "kaola-acp-paths.py"):
                shutil.copy2(PROJECT / "scripts" / name, isolated / name)
            repo = tmp / "repo"
            (repo / ".kaola").mkdir(parents=True)
            state = repo / ".kaola" / "heartbeat-prompt.json"
            state.write_text(json.dumps({
                "schema": "kaola-heartbeat-prompt/2", "revision": 1,
                "state": {"project": {"code": "T", "repo": str(repo)}},
            }), encoding="utf-8")
            holder = "h306" + "0" * 12
            digest = hashlib.sha256(str(repo).encode()).hexdigest()[:16]
            record_dir = tmp / "records" / "zcode" / "zcode-T-host" / digest
            record_dir.mkdir(parents=True)
            (record_dir / "record.json").write_text(json.dumps({
                "platform": "zcode", "session": "zcode-T-host",
                "session_role": "host", "acp_session_id": "original-host",
                "holder_instance_id": holder, "repo": str(repo),
            }), encoding="utf-8")
            event = {
                "cursor": 1, "kind": "compact_reload_detected",
                "holder": holder, "role": "host",
                "signal": {"method": "session/update",
                           "params": {"sessionId": "original-host",
                                      "update": {"sessionUpdate": "compaction_update",
                                                 "status": "completed",
                                                 "compactionId": "occ-306"}}},
            }
            (record_dir / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
            env = {
                "KAOLA_ACP_DISPATCHER": json.dumps({
                    "holder_instance_id": holder, "platform": "zcode",
                    "repo": str(repo), "session": "zcode-T-host",
                }),
                "KAOLA_ACP_RECORD_ROOT": str(tmp / "records"),
            }
            out = run(
                [sys.executable, str(isolated / "kaola-dispatch.py"), "state",
                 "recovery-input", "--file", str(state), "--source", "fixture",
                 "--kind", "host-compaction", "--signal-cursor", "1"],
                tmp, env,
            )
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn('"result": "written"', out.stdout)
            written = list(isolated.rglob("*.pyc")) + list(isolated.rglob("*.pyo"))
            self.assertEqual(written, [], f"recovery import wrote bytecode: {written}")
            self.assertEqual(list(isolated.rglob("__pycache__")), [])


if __name__ == "__main__":
    unittest.main()
