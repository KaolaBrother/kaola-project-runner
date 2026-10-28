#!/usr/bin/env python3
"""Issue #422: a declared test lane fails closed on a noop receipt.

Exit 0 is not proof the suite ran. Empty stdout and stderr refuse
certification. A duration under the floor refuses when output is also
empty, and the refusal names ``noop-test-lane`` and records the sha and
the duration that were seen. A lane that produced output still certifies.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def load():
    spec = importlib.util.spec_from_file_location("kaola_acp_issue_422", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoopReceiptGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acp = load()

    def certify(self, receipt: dict) -> dict:
        return self.acp.certify_test_lane_receipt(receipt)

    def test_floor_sits_above_the_observed_noop_band(self) -> None:
        self.assertEqual(self.acp.EMPTY_OUTPUT_SHA256, EMPTY)
        self.assertEqual(self.acp.EMPTY_OUTPUT_SHA256, hashlib.sha256(b"").hexdigest())
        # The noop receipts were 7–9 ms. 50 ms is above that band.
        self.assertEqual(self.acp.TEST_LANE_MIN_DURATION_MS, 50)
        self.assertGreater(self.acp.TEST_LANE_MIN_DURATION_MS, 9)

    def test_empty_output_pass_receipt_is_refused(self) -> None:
        original = {
            "test_lane": "m6b-sdk-unit",
            "outcome": "pass",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "duration_ms": 5000,
        }
        got = self.certify(original)
        self.assertEqual(original["outcome"], "pass")
        self.assertEqual(got["outcome"], "refused")
        self.assertEqual(got["error"]["code"], "noop-test-lane")
        self.assertEqual(got["error"]["evidence"]["checks"], ["empty-output"])
        self.assertEqual(got["error"]["evidence"]["stdout_sha256"], EMPTY)
        self.assertEqual(got["error"]["evidence"]["stderr_sha256"], EMPTY)
        self.assertNotIn("sub-floor-duration", got["error"]["evidence"]["checks"])

    def test_sub_floor_duration_receipt_is_refused(self) -> None:
        got = self.certify({
            "test_lane": "m6b-sdk-pins",
            "outcome": "pass",
            "exit": 0,
            "stdout_sha256": EMPTY,
            "stderr_sha256": "sha256:" + EMPTY,
            "duration_ms": 8,
        })
        evidence = got["error"]["evidence"]
        self.assertEqual(got["error"]["code"], "noop-test-lane")
        self.assertIn("sub-floor-duration", evidence["checks"])
        self.assertEqual(evidence["duration_ms"], 8)
        self.assertEqual(evidence["min_duration_ms"], 50)
        self.assertEqual(evidence["stdout_sha256"], EMPTY)
        self.assertEqual(evidence["stderr_sha256"], EMPTY)
        self.assertIn("duration_ms=8", got["error"]["message"])

    def test_exit_0_alone_is_refused_when_output_is_empty(self) -> None:
        got = self.certify({
            "kind": "test-lane",
            "lane": "m6b-sdk-unit",
            "exit_code": 0,
            "duration_ms": 4000,
        })
        self.assertEqual(got["outcome"], "refused")
        self.assertEqual(got["result"], "refused")
        self.assertEqual(got["error"]["evidence"]["exit_code"], 0)
        self.assertEqual(got["error"]["evidence"]["stdout_sha256"], EMPTY)
        self.assertEqual(got["error"]["evidence"]["stderr_sha256"], EMPTY)
        self.assertIn("empty-output", got["error"]["evidence"]["checks"])
        self.assertNotEqual(got["outcome"], "pass")

    def test_real_receipt_with_output_and_normal_duration_certifies(self) -> None:
        text = "Ran 12 tests\nOK\n"
        got = self.certify({
            "test_lane": "m6b-sdk-unit",
            "outcome": "pass",
            "exit_code": 0,
            "stdout": text,
            "stderr": "",
            "duration_ms": 2000,
        })
        self.assertEqual(got["outcome"], "pass")
        self.assertEqual(got["result"], "pass")
        self.assertNotIn("error", got)
        self.assertEqual(got["stdout_sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertNotEqual(got["stdout_sha256"], EMPTY)
        self.assertEqual(got["duration_ms"], 2000)

    def test_refusal_is_typed_and_carries_evidence(self) -> None:
        got = self.certify({
            "test_lane": "m6b-sdk-unit",
            "outcome": "pass",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "duration": 7,
        })
        error = got["error"]
        self.assertEqual(error["code"], "noop-test-lane")
        self.assertEqual(got["reason"], "noop-test-lane")
        evidence = error["evidence"]
        self.assertEqual(evidence["stdout_sha256"], EMPTY)
        self.assertEqual(evidence["stderr_sha256"], EMPTY)
        self.assertEqual(evidence["duration_ms"], 7)
        self.assertEqual(evidence["exit_code"], 0)
        self.assertEqual(evidence["test_lane"], "m6b-sdk-unit")
        self.assertIn("empty-output", evidence["checks"])
        self.assertIn("sub-floor-duration", evidence["checks"])
        self.assertIn(EMPTY, error["message"])

    def test_fast_lane_with_output_stays_certified(self) -> None:
        # Measured one-test and python3 -c runs finish under 50 ms and
        # still produce output. The floor must leave them certified.
        got = self.certify({
            "test_lane": "tiny-unittest",
            "outcome": "pass",
            "exit_code": 0,
            "stdout": "",
            "stderr": "Ran 1 test\nOK\n",
            "duration_ms": 30,
        })
        self.assertEqual(got["outcome"], "pass")
        self.assertNotIn("error", got)
        self.assertNotEqual(got["stderr_sha256"], EMPTY)

    def test_escaped_and_noop_shape_is_refused(self) -> None:
        got = self.certify({
            "test_lane": "m6b-sdk-unit",
            "outcome": "pass",
            "exit_code": 0,
            "command": "cd sdk/typescript &amp;&amp; npx vitest",
            "stdout": "",
            "stderr": "",
            "duration_ms": 9,
        })
        self.assertEqual(got["outcome"], "refused")
        self.assertEqual(got["error"]["code"], "noop-test-lane")
        self.assertEqual(got["command"], "cd sdk/typescript &amp;&amp; npx vitest")
        self.assertEqual(got["error"]["evidence"]["duration_ms"], 9)
        self.assertIn("sub-floor-duration", got["error"]["evidence"]["checks"])

    def test_emit_receipt_refuses_on_the_receipt_path(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.acp._emit_receipt({
                "test_lane": "m6b-sdk-pins",
                "outcome": "pass",
                "exit_code": 0,
                "stdout_sha256": EMPTY,
                "stderr_sha256": EMPTY,
                "duration_ms": 8,
            })
        printed = json.loads(buffer.getvalue())
        self.assertEqual(printed["error"]["code"], "noop-test-lane")
        self.assertEqual(printed["outcome"], "refused")
        self.assertIn("route", printed)
        self.assertIn("stdout_sha256", printed["route"])
        self.assertEqual(printed["error"]["evidence"]["duration_ms"], 8)

    def test_ordinary_receipt_without_a_test_lane_is_unchanged(self) -> None:
        receipt = {
            "outcome": "pass",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "duration_ms": 8,
        }
        self.assertIs(self.certify(receipt), receipt)

    def test_failed_lane_is_left_as_a_failure(self) -> None:
        receipt = {
            "test_lane": "m6b-sdk-unit",
            "outcome": "fail",
            "exit_code": 1,
            "stdout": "",
            "stderr": "",
            "duration_ms": 8,
        }
        self.assertIs(self.certify(receipt), receipt)


if __name__ == "__main__":
    unittest.main()
