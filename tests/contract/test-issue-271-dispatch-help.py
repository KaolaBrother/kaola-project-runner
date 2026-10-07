#!/usr/bin/env python3
"""Issue #271 D1/S1: the six dispatch CLI file-path flags carry JSON-file-path
help, and the flag contract is discoverable from --help alone (no reference
hop). Behavioral: the real --help output of the installed-entry script."""
from __future__ import annotations
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT / "scripts" / "kaola-dispatch.py"
FLAGS = ["--plan", "--authorization", "--availability", "--live", "--index", "--prior-index"]


class DispatchHelp(unittest.TestCase):
    def test_file_path_flags_advertise_json_file_path(self) -> None:
        for sub in ("execute", "project", "collect", "state retire", "state update"):
            out = subprocess.run(
                [sys.executable, str(SCRIPT), *sub.split(), "--help"],
                capture_output=True, text=True, check=True).stdout
            joined = " ".join(out.split())
            if sub == "execute":
                for flag in FLAGS:
                    self.assertIn(flag, joined)
                # the file-path help text itself
                self.assertGreaterEqual(joined.count("JSON file path"), 3)
            if sub == "project":
                self.assertIn("--authorization AUTHORIZATION JSON file path", joined)
            if sub == "collect":
                self.assertIn("--index INDEX JSON file path", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
