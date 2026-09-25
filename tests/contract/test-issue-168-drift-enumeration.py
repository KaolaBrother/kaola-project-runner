#!/usr/bin/env python3
"""Issue #168: every reported_drift value is enumerated on one stale seat.

The five non-blocking drift values (#162, #165, #166) all surface together
through ``seat_freshness``'s ``reported_drift``, beside the ``stale``,
``stale_reasons``, and ``restart_files`` facts (#178 removed the refusal
that used to name them in its detail).
"""

from __future__ import annotations

import importlib.util
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


class DriftEnumerationTests(unittest.TestCase):
    def test_one_stale_seat_reports_all_five_drift_values(self) -> None:
        acp = load_module(CLI, "acp168")
        # The locator registration pin, isolated from this machine's own.
        acp.registration_pin = lambda: "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            # One recorded tree that is not the expected install root: changed
            # cli/quota/holder digests and one path that no longer resolves. A
            # SKILL.md beside scripts/ keeps it an install tree, not a checkout.
            moved = Path(tmp) / "moved-root" / "scripts"
            moved.mkdir(parents=True)

            def recorded(name: str) -> dict:
                return {"path": str(moved / name), "sha256": "0" * 64}

            for name in ("kaola-acp.py", "kaola-quota.py", "kaola-acp-holder.py"):
                (moved / name).write_bytes(b"changed on disk\n")
            (moved.parent / "SKILL.md").write_text("skill\n", encoding="utf-8")
            facts = {
                "runner_build": "a" * 12,
                "accepted_revision": "b" * 40,
                "script_paths": {
                    "kaola-acp.py": recorded("kaola-acp.py"),
                    "kaola-quota.py": recorded("kaola-quota.py"),
                    "kaola-acp-holder.py": recorded("kaola-acp-holder.py"),
                    "kaola-tmux.sh": recorded("gone/kaola-tmux.sh"),
                },
            }
            fresh = acp.seat_freshness("codex", str(Path(tmp) / "repo"), facts)
        self.assertEqual(sorted(fresh["reported_drift"]), sorted(DRIFT_VALUES))
        self.assertIs(fresh["stale"], True, fresh)
        self.assertEqual(fresh["stale_reasons"], ["restart-required"])
        self.assertEqual(fresh["restart_files"], ["kaola-acp-holder.py"])
        self.assertEqual(fresh["missing_files"], ["kaola-tmux.sh"])


if __name__ == "__main__":
    unittest.main()
