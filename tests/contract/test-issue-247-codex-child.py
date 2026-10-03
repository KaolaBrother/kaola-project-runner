#!/usr/bin/env python3
"""Issue #247: a Codex manifest launch's child is absolute CODEX_PATH.

The adapter version, the requested CLI, and the launched child's package
version stay separate facts. PATH is not copied into CODEX_PATH. An explicit
--command keeps the previous launch. Offline: no npx and no Codex binary.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
PLATFORMS = PROJECT / "platforms"


def load_acp():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("kaola_acp_issue247", CLI)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CodexChildPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acp = load_acp()
        self.manifest = self.acp.load_manifest("codex")

    def args(self, **overrides):
        values = {"platform": "codex", "manifest": self.manifest,
                  "agent_command_given": False}
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_manifest_keeps_the_three_facts_apart(self) -> None:
        self.assertEqual(
            self.manifest["acp_command"],
            "npx --yes --package @agentclientprotocol/codex-acp@2.0.1 codex-acp",
        )
        self.assertNotIn("@openai/codex@", self.manifest["acp_command"])
        self.assertEqual(self.manifest["acp_wrapper_pin"], "2.0.1")
        self.assertEqual(self.manifest["acp_requested_cli"], "0.160.0")
        versions = dict(part.split("=", 1)
                        for part in self.manifest["acp_verified_versions"].split(";"))
        self.assertEqual(versions["adapter"], "2.0.1")
        self.assertEqual(versions["cli"], "0.160.0")
        self.assertNotIn("requested_cli", versions)

    def test_absolute_codex_path_is_kept_and_path_is_not_consulted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "codex-0.160"
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)
            decoy = Path(directory) / "bin"
            decoy.mkdir()
            (decoy / "codex").write_text("#!/bin/sh\n", encoding="utf-8")
            (decoy / "codex").chmod(0o755)
            env = {"PATH": f"{decoy}{os.pathsep}/usr/bin", "CODEX_PATH": str(binary)}
            with mock.patch.dict(os.environ, env, clear=True):
                child = self.acp.agent_environment(self.args())
            self.assertEqual(child["CODEX_PATH"], str(binary))
            self.assertNotIn(str(decoy / "codex"), child["CODEX_PATH"])

    def test_relative_codex_path_is_dropped_on_a_manifest_launch(self) -> None:
        with mock.patch.dict(os.environ, {"CODEX_PATH": "codex", "PATH": "/usr/bin"}, clear=True):
            child = self.acp.agent_environment(self.args())
        self.assertNotIn("CODEX_PATH", child)

    def test_an_explicit_command_does_not_require_or_rewrite_codex_path(self) -> None:
        with mock.patch.dict(os.environ, {"CODEX_PATH": "codex"}, clear=True):
            child = self.acp.agent_environment(self.args(agent_command_given=True))
        self.assertEqual(child["CODEX_PATH"], "codex")
        self.assertIsNone(self.acp.codex_child_error(self.args(agent_command_given=True)))

    def test_missing_codex_path_refuses_before_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            env = {k: v for k, v in os.environ.items()
                   if k not in {"CODEX_PATH", "KAOLA_ACP_COMMAND"} and not k.startswith("KAOLA_")}
            env["PATH"] = "/usr/bin:/bin"
            result = subprocess.run(
                [sys.executable, str(CLI), "codex", "start", "--repo", str(repo),
                 "--session", "codex-kaola-247-offline"],
                capture_output=True, text=True, env=env, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["error"]["code"], "codex-child-path")
        self.assertFalse(receipt["mutation_performed"])
        self.assertEqual(receipt["mutation_status"], "not_started")
        self.assertNotIn("holder_pid", receipt)
        self.assertNotIn("npx", result.stderr)

    def test_child_package_comes_from_the_app_server_process_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "node_modules" / "@openai" / "codex"
            binary = root / "bin" / "codex.js"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            (root / "package.json").write_text(
                json.dumps({"name": "@openai/codex", "version": "0.160.0"}),
                encoding="utf-8")
            vendor = root.parent / "codex-darwin-arm64"
            vendor.mkdir()
            (vendor / "package.json").write_text(
                json.dumps({"name": "@openai/codex-darwin-arm64",
                            "version": "0.160.0-darwin-arm64"}),
                encoding="utf-8")
            rows = {
                10: (1, "npx codex-acp"),
                11: (10, f"node {binary} app-server"),
                12: (11, f"{vendor / 'codex'} app-server"),
            }
            chosen = self.acp.codex_binary_from_table(rows, 10)
            self.assertEqual(chosen, str(binary))
            self.assertEqual(self.acp.codex_package_at(chosen), ("@openai/codex", "0.160.0"))


if __name__ == "__main__":
    unittest.main()
