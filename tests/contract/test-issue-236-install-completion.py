#!/usr/bin/env python3
"""Issue #236 checks that need no decision engine.

The installer footer semantics live in tests/contract/test-installer-runtimes.sh
(real installer runs). Guide wording is traced by the run report, not by phrase
assertions. What remains here exercises the actual documented DSH inspection
command against a fixture and reuses the archived #226 evidence for the Codex
pinned pair. Nothing installs a CLI, logs in, restarts a session, or opens a
live ACP connection.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
API = PROJECT / "docs" / "api.md"
CODEX_MANIFEST = PROJECT / "platforms" / "codex.yaml"
ISSUE_226 = PROJECT / "kaola-workflow" / "archive" / "issue-226" / "finalization-summary.md"


def documented_dsh_command() -> str:
    """The exact fenced command from the DSH section of docs/api.md."""
    text = API.read_text(encoding="utf-8")
    section = text.split("#### DSH loaded ACP harness", 1)[1]
    block = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
    assert block is not None
    return block.group(1)


class DocumentedCommandTest(unittest.TestCase):
    def test_dsh_documented_inspection_resolves_loaded_packages(self) -> None:
        command = documented_dsh_command()
        self.assertIn("node_modules/@deepseek-ai", command)
        with tempfile.TemporaryDirectory(prefix="kaola-236-dsh-") as tmp:
            root = Path(tmp)
            for name in ("dsh", "dsh-acp-app", "dsh-acp"):
                path = root / "node_modules" / "@deepseek-ai" / name / "package.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"name": f"@deepseek-ai/{name}",
                                            "version": "0.1.5-rc.3"}) + "\n",
                                encoding="utf-8")
            binary = root / "bin" / "dsh"
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
            env = dict(os.environ, DSH_BIN=str(binary))
            result = subprocess.run(["bash", "-c", command], capture_output=True,
                                    text=True, timeout=60, check=False, env=env,
                                    cwd=str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        found = dict(line.split(" ", 2)[:2] for line in result.stdout.splitlines())
        self.assertEqual(found, {"dsh": "0.1.5-rc.3", "dsh-acp-app": "0.1.5-rc.3",
                                 "dsh-acp": "0.1.5-rc.3"})


class CodexEvidenceTest(unittest.TestCase):
    def test_manifest_pin_matches_the_verified_226_pair(self) -> None:
        acp_command = ""
        for line in CODEX_MANIFEST.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip() == "acp_command":
                acp_command = value.strip()
                break
        self.assertIn("@openai/codex@0.158.0", acp_command)
        self.assertIn("@agentclientprotocol/codex-acp@2.0.0", acp_command)
        saved = ISSUE_226.read_text(encoding="utf-8")
        self.assertIn("@openai/codex` 0.158.0", saved)
        self.assertIn("@agentclientprotocol/codex-acp` 2.0.0", saved)


if __name__ == "__main__":
    unittest.main()
