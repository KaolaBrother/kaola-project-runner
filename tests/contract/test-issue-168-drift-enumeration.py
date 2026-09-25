#!/usr/bin/env python3
"""Issue #168: the seat-stale refusal names every reported_drift value.

#162, #165, and #166 report five non-blocking drift values. The refusal
detail must name all five, including what the two path values mean.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"

DRIFT_VALUES = (
    "pin-drift",
    "cli-drift",
    "quota-drift",
    "recorded-path-missing",
    "install-root-mismatch",
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SeatStaleDriftEnumerationTests(unittest.TestCase):
    def test_seat_stale_refusal_names_all_five_drift_values(self) -> None:
        acp = load_module(CLI, "acp168")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "-q", str(repo)], check=True, capture_output=True)
            acp.read_record = lambda directory: {"present": True}
            acp.seat_freshness = lambda platform, repo, record: {
                "stale": True,
                "stale_reasons": ["restart-required"],
                "restart_files": ["kaola-acp-holder.py"],
                "reported_drift": [],
                "runner_build": "a" * 12,
                "accepted_revision": "b" * 40,
                "pin": None,
            }
            args = argparse.Namespace(
                platform="codex",
                session="codex-KPR-i168-drift",
                command="send",
                confirm_stale=False,
            )
            receipt = acp.refuse_if_stale(args, str(repo), Path(tmp))
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt.get("reason"), "seat-stale")
        detail = receipt.get("detail") or ""
        for value in DRIFT_VALUES:
            self.assertIn(value, detail, detail)
        self.assertIn("a recorded script path that no longer exists", detail)
        self.assertIn("an install tree that moved or was re-rooted", detail)
        self.assertIn("are reported and do not block", detail)


if __name__ == "__main__":
    unittest.main()
