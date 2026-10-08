#!/usr/bin/env python3
"""Issue #292: the state tool resolves holder records across the fixed root
and legacy roots through the shared #278 path helper.

A node Sideagent under a runtime that forwards TMPDIR but not
KAOLA_ACP_RECORD_ROOT runs `kaola-dispatch.py state ...`; the pre-fix lookup
read only the caller-TMPDIR root, found no record, and refused a bound node's
checkpoint as `binding-superseded`. These tests run the real CLI as a
subprocess with a scrubbed environment against records planted in the fixed
root, a legacy TMPDIR root, neither, and an explicit override.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts" / "kaola-dispatch.py"
spec = importlib.util.spec_from_file_location(
    "paths292", PROJECT / "scripts" / "kaola-acp-paths.py")
acp_paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acp_paths)

FIXED = acp_paths.default_root()
LEGACY_BASE = f"kaola-{os.getuid()}"


def scrubbed_env(tmpdir: str, dispatcher: dict | None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("KAOLA_") and k != "XDG_RUNTIME_DIR"}
    env["TMPDIR"] = tmpdir
    if dispatcher is not None:
        env["KAOLA_ACP_DISPATCHER"] = json.dumps(dispatcher)
    return env


class StateRecordRoot(unittest.TestCase):
    SESSION = f"zcode-I292-{os.getpid()}-node"
    HOST_SESSION = f"codex-I292-{os.getpid()}-host"
    HOST_HOLDER = "host-i292"
    NODE_HOLDER = "node-i292"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i292-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.repo_text = str(self.repo.resolve())
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.planted = []
        self.addCleanup(self.remove_planted)

    def remove_planted(self) -> None:
        # Only this test's unique session trees; never anything else under a
        # shared root.
        for root in self.planted:
            session_dir = root / "zcode" / self.SESSION
            shutil.rmtree(session_dir, ignore_errors=True)
            for parent in (session_dir.parent,):
                try:
                    parent.rmdir()
                except OSError:
                    pass

    def node_record(self) -> dict:
        return {
            "session_role": "sideagent",
            "state": "ready",
            "platform": "zcode",
            "session": self.SESSION,
            "repo": self.repo_text,
            "holder_instance_id": self.NODE_HOLDER,
            "holder_pid": os.getpid(),
            "dispatcher": {
                "holder_instance_id": self.HOST_HOLDER,
                "platform": "codex",
                "session": self.HOST_SESSION,
                "repo": self.repo_text,
            },
        }

    def plant(self, root: Path) -> Path:
        directory = root / "zcode" / self.SESSION / self.digest()
        acp_paths.prepare_record_directory(directory, root)
        (directory / "record.json").write_text(json.dumps(self.node_record()))
        self.planted.append(root)
        return directory

    def digest(self) -> str:
        import hashlib
        return hashlib.sha256(self.repo_text.encode()).hexdigest()[:16]

    def run_state(self, *args: str, env: dict[str, str]) -> tuple[int, dict]:
        proc = subprocess.run([sys.executable, str(SCRIPT), "state", *args],
                              capture_output=True, text=True, env=env, timeout=30)
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError as exc:
            raise AssertionError(
                f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc

    def caller_env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = scrubbed_env(str(self.base / "tmpdir"), {
            "holder_instance_id": self.NODE_HOLDER, "platform": "zcode",
            "repo": self.repo_text, "session": self.SESSION})
        env.update(extra or {})
        (self.base / "tmpdir").mkdir(exist_ok=True)
        return env

    def init_bound(self) -> None:
        env = scrubbed_env(str(self.base / "tmpdir"), None)
        (self.base / "tmpdir").mkdir(exist_ok=True)
        code, out = self.run_state(
            "init", "--file", str(self.file), "--writer", "host", "--source", "turn-1",
            "--project", json.dumps({"code": "I292", "goal": "record root"}),
            "--authorization", json.dumps({"grants": [
                {"id": "zcode/default", "state": "granted", "count": 1}]}), env=env)
        self.assertEqual(code, 0, out)
        code, out = self.run_state(
            "update", "--file", str(self.file), "--writer", "host", "--source", "bind",
            "--section", "sideagent", "--expect-revision", str(self.doc()["revision"]),
            "--set", json.dumps({"platform": "zcode", "session": self.SESSION,
                                 "state": "active", "mode": "node"}), env=env)
        self.assertEqual(code, 0, out)

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def checkpoint(self, env: dict[str, str]) -> tuple[int, dict]:
        return self.run_state(
            "checkpoint", "--file", str(self.file), "--writer", "sideagent",
            "--source", "b-1", "--batch", "b-1",
            "--through-host-revision", str(self.doc()["host_revision"]),
            "--entries", "[]", env=env)

    def test_checkpoint_finds_the_node_record_in_the_fixed_root(self) -> None:
        self.init_bound()
        self.plant(FIXED)
        code, out = self.checkpoint(self.caller_env())
        self.assertEqual(code, 0, out)
        self.assertEqual(out.get("result"), "written", out)

    def test_checkpoint_finds_the_node_record_in_a_legacy_tmpdir_root(self) -> None:
        self.init_bound()
        legacy = self.base / "tmpdir" / LEGACY_BASE
        self.plant(legacy)
        code, out = self.checkpoint(self.caller_env())
        self.assertEqual(code, 0, out)
        self.assertEqual(out.get("result"), "written", out)

    def test_checkpoint_without_any_record_is_refused(self) -> None:
        self.init_bound()
        code, out = self.checkpoint(self.caller_env())
        self.assertNotEqual(code, 0, out)
        self.assertEqual(out.get("reason"), "binding-superseded", out)

    def test_view_reports_a_node_running_from_the_fixed_root(self) -> None:
        self.init_bound()
        self.plant(FIXED)
        doc = self.doc()
        doc["carrier"] = {"capability": "heartbeat-state/2",
                          "holder_instance_id": self.HOST_HOLDER,
                          "platform": "codex", "session": self.HOST_SESSION}
        self.file.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.run_state("view", "--file", str(self.file), "--role", "host",
                                 env=scrubbed_env(str(self.base / "tmpdir"), None))
        self.assertEqual(code, 0, out)
        self.assertEqual(out.get("sideagent_maintenance"), "a node is running", out)

    def test_explicit_record_root_keeps_its_scoped_view(self) -> None:
        self.init_bound()
        self.plant(FIXED)
        elsewhere = self.base / "elsewhere-records"
        elsewhere.mkdir()
        code, out = self.checkpoint(
            self.caller_env({"KAOLA_ACP_RECORD_ROOT": str(elsewhere)}))
        self.assertNotEqual(code, 0, out)
        self.assertEqual(out.get("reason"), "binding-superseded", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
