#!/usr/bin/env python3
"""Issue #437: a Sideagent outage must not stay silent.

Three honest surfaces:
- ``state recovery-input --rearm`` (carrier caller): a fresh same-class
  failure refreshes the blocking ``maintenance-returned`` alert instead of
  returning ``unchanged`` behind the dedupe.
- ``seat_freshness`` reports ``main-skill-build-skew`` when the build a seat
  started with differs from the installed record's build: a matching disk pin
  no longer masks a stale in-process Host.
- The holder-side skew no-latch cooldown and retry-after-alignment live in
  ``test-issue-255-lifecycle-state.py`` (HolderNodeMode harness).
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "kaola-dispatch.py"
CLI = SCRIPT.with_name("kaola-acp.py")
CALLER_ENV = ("KAOLA_ACP_DISPATCHER", "KAOLA_ACP_HEARTBEAT_HOST", "KAOLA_ACP_RECORD_ROOT")


def run(args: list[str], env: dict[str, str] | None = None) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env=env or {k: v for k, v in os.environ.items() if k not in CALLER_ENV})
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError as exc:
        raise AssertionError(f"not JSON ({exc}): {proc.stdout}\n{proc.stderr}") from exc


def load_module(path: Path, tag: str):
    spec = importlib.util.spec_from_file_location(f"kpr_{tag}_437", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RearmTests(unittest.TestCase):
    def setUp(self) -> None:
        import hashlib
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i437-")
        self.repo = Path(self.tmp.name) / "consumer"
        (self.repo / ".kaola").mkdir(parents=True)
        self.file = self.repo / ".kaola" / "heartbeat-prompt.json"
        self.records = Path(self.tmp.name) / "records"
        session = "zcode-KT-orchestrator-main"
        digest = hashlib.sha256(str(self.repo).encode()).hexdigest()[:16]
        directory = self.records / "zcode" / session / digest
        directory.mkdir(parents=True)
        holder = "fixture-host-437"
        (directory / "record.json").write_text(json.dumps(
            {"platform": "zcode", "session": session, "repo": str(self.repo),
             "holder_instance_id": holder, "session_role": "host"}), encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if k not in CALLER_ENV}
        self.env["KAOLA_ACP_DISPATCHER"] = json.dumps(
            {"holder_instance_id": holder, "platform": "zcode", "repo": str(self.repo),
             "session": session})
        self.env["KAOLA_ACP_RECORD_ROOT"] = str(self.records)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def doc(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def test_a_repeated_same_class_failure_rearms_the_blocking_alert(self) -> None:
        code, out = run(["state", "init", "--file", str(self.file), "--writer", "host", "--source",
                         "turn-1", "--project", json.dumps({"code": "KT", "goal": "ship"}),
                         "--authorization", json.dumps({"grants": []})], self.env)
        self.assertEqual(code, 0, out)
        argv = ["state", "recovery-input", "--file", str(self.file),
                "--source", "carrier-maintenance-failure", "--fail", "main-skill-build-skew",
                "--input", "batch:702", "--evidence", "/tmp/events.jsonl#1"]
        code, first = run(argv, self.env)
        self.assertEqual(code, 0, first)
        alert = self.doc()["state"]["alerts"].get("maintenance-returned")
        self.assertIsNotNone(alert, "the fresh failure surfaces the blocking alert")
        self.assertEqual(alert["writer"], "tool:carrier")
        rev = alert["rev"]
        code, deduped = run(argv, self.env)
        self.assertEqual((code, deduped.get("result")), (0, "unchanged"), deduped)
        code, rearmed = run([*argv, "--rearm"], self.env)
        self.assertEqual(code, 0, rearmed)
        self.assertEqual(rearmed.get("result"), "rearmed", rearmed)
        alert = self.doc()["state"]["alerts"]["maintenance-returned"]
        self.assertEqual(alert["rev"], rev + 1, "one refreshed row, not a second alert")
        self.assertIn("batch:702", alert["inputs"], "the input keeps its identity")
        self.assertEqual(len(alert["inputs"]), 1, "no duplicate input rows")


class FreshnessBuildSkewTests(unittest.TestCase):
    def test_a_matching_pin_does_not_mask_a_stale_in_process_build(self) -> None:
        acp = load_module(CLI, "acp437")
        acp.registration_pin = lambda: "a" * 40
        acp._baseline_record_build = lambda: "bbbbbbbbbbbb"
        facts = {"runner_build": "cccccccccccc", "accepted_revision": "a" * 40,
                 "script_paths": {}, "baseline_exempt": True}
        fresh = acp.seat_freshness(facts)
        self.assertEqual(fresh["pin"], "a" * 40)
        self.assertIn("loaded-build-skew", fresh["reported_drift"], fresh)
        aligned = acp.seat_freshness({**facts, "runner_build": "bbbbbbbbbbbb"})
        self.assertNotIn("loaded-build-skew", aligned["reported_drift"], aligned)
        acp._baseline_record_build = lambda: None
        self.assertNotIn("loaded-build-skew",
                         acp.seat_freshness({**facts})["reported_drift"],
                         "without a readable record nothing is claimed")
        self.assertIn("loaded-build-skew", acp.REPORTED_DRIFT_VALUES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
