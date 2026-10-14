#!/usr/bin/env python3
"""Issue #325: a run of failed Delegator webhook deliveries.

The sender keeps one repeated-failure fact (window, count, one Host alert,
then the heartbeat path once the window passes) and stores final failures
apart from the 32-attempt ring. Tests talk to the loopback fixture from
``test-issue-299-delegator-webhook.py``. They pin
``KAOLA_DELEGATOR_WEBHOOK_CONFIG`` to a temp file and never read the real
webhook config. Proxy variables are dropped so this machine cannot answer
502 for 127.0.0.1.
"""

from __future__ import annotations

import calendar
import importlib.util
import json
import os
import subprocess
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ISSUE299 = HERE / "test-issue-299-delegator-webhook.py"
spec = importlib.util.spec_from_file_location("issue299_webhook_325", ISSUE299)
assert spec is not None and spec.loader is not None
issue299 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(issue299)

REPO = issue299.REPO
ONCE_NOTICE = (
    "When the routine webhook answers HTTP 400 for more than one event, "
    "tell the user once, with the window and the count."
)
PROXY_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
    "ALL_PROXY", "all_proxy",
)
for _proxy in PROXY_KEYS:
    os.environ.pop(_proxy, None)


def notice_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if "repeated-failure" in line]


class OutageCase(issue299.WebhookCase):
    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = super().env(extra)
        for key in PROXY_KEYS:
            env.pop(key, None)
        return env

    def payload(self, seq: int, *, state: str = "error") -> dict:
        if state == "error":
            detail, reason = "turn_failed", "turn_failed"
        else:
            detail, reason = None, "host_stopped_pending"
        return {
            "schema": "kaola-delegator-wake/1",
            "project": self.project,
            "session": "s1",
            "holder_instance_id": "h-325",
            "event_seq": seq,
            "state": state,
            "state_detail": detail,
            "reason": reason,
            "ts": "2026-01-01T00:00:00Z",
        }

    def use_status(self, code: int) -> None:
        self.endpoint = self.endpoint or issue299.Endpoint()
        self._url_config(f"http://127.0.0.1:{self.endpoint.port}/status/{code}")

    def use_ok(self) -> None:
        self.endpoint = self.endpoint or issue299.Endpoint()
        self._url_config(self.endpoint.url)

    def store(self) -> dict:
        return json.loads(self.receipts_path().read_text(encoding="utf-8"))

    def failure_run(self) -> dict:
        found = self.store().get("repeated_failure")
        self.assertIsInstance(found, dict)
        return found

    def fail_event(self, seq: int, code: int, timeout: float) -> "subprocess.CompletedProcess[str]":
        self.use_status(code)
        proc = self.deliver(self.payload(seq), timeout=timeout)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        return proc

    def succeed(self, seq: int) -> None:
        self.use_ok()
        proc = self.deliver(self.payload(seq, state="end_turn"), timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(notice_lines(proc.stderr), [])


class RepeatedFailure(OutageCase):
    def test_http_400_run_notices_the_host_once(self) -> None:
        self.endpoint = issue299.Endpoint()
        first = self.fail_event(1, 400, 45)
        self.assertEqual(notice_lines(first.stderr), [])
        rows = [item for item in self.receipts() if item.get("event_seq") == 1]
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(self.store()["failed_receipts"]), 1)
        self.assertIs(self.store()["failed_receipts"][0]["final"], True)
        self.assertEqual(self.store()["failed_receipts"][0]["http_status"], 400)
        opened = self.failure_run()
        self.assertEqual(opened["count"], 1)
        self.assertIs(opened["active"], False)
        self.assertIsNone(opened["host_notice"])
        self.assertIsNone(opened["user_notice"])
        self.assertIs(opened["window_passed"], False)
        self.assertIs(opened["heartbeat"]["applies"], False)
        self.assertEqual(rows[-1]["route"], issue299.LOST_WAKE_ROUTE)
        for item in rows[:-1]:
            self.assertNotIn("route", item)

        second = self.fail_event(2, 400, 45)
        cond = self.failure_run()
        expected = (
            "delegator-webhook: repeated-failure "
            f"window={cond['window_start']}..{cond['window_end']} "
            f"count=2 host-notice=once "
            "heartbeat-bound=7200s heartbeat-applies=false"
        )
        self.assertEqual(notice_lines(second.stderr), [expected])
        self.assertNotIn(self.endpoint.url, second.stderr)
        self.assertNotIn("http", expected)
        self.assertEqual(cond["schema"], "kaola-delegator-webhook-repeated-failure/1")
        self.assertEqual(cond["count"], 2)
        self.assertEqual(cond["min_count"], 2)
        self.assertEqual(cond["window_seconds"], 900)
        self.assertIs(cond["active"], True)
        self.assertEqual(cond["user_notice"], "once")
        self.assertEqual(cond["last_http_status"], 400)
        self.assertEqual(cond["last_error"], "http-status")
        self.assertEqual(cond["fallbacks"], ["retry", "receipt-route", "host-notice", "heartbeat"])
        self.assertIs(cond["host_notice"]["once"], True)
        self.assertEqual(cond["host_notice"]["kind"], "alert")
        self.assertEqual(cond["heartbeat"]["path"], "heartbeat")
        self.assertEqual(cond["heartbeat"]["bound_seconds"], 7200)
        self.assertIs(cond["heartbeat"]["applies"], False)
        self.assertIs(cond["window_passed"], False)
        emitted = cond["host_notice"]["emitted_at"]
        self.assertEqual(emitted, cond["window_end"])
        self.assertEqual(len(self.store()["failed_receipts"]), 2)

        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["repeated_failure"]["count"], 2)
        self.assertEqual(status["repeated_failure"]["window_start"], cond["window_start"])
        self.assertEqual(status["repeated_failure"]["window_end"], cond["window_end"])
        self.assertEqual(status["repeated_failure"]["user_notice"], "once")
        self.assertIs(status["repeated_failure"]["host_notice"]["once"], True)
        self.assertEqual(status["repeated_failure"]["heartbeat"]["bound_seconds"], 7200)
        self.assertEqual(status["failed_receipts_kept"], 2)
        self.assertIsNone(status["previous_repeated_failure"])
        self.assertNotIn("failed_receipts", status)
        self.assertEqual(status["last_receipt"]["event_seq"], 2)
        self.assertIs(status["last_receipt"]["final"], True)

        third = self.fail_event(3, 400, 45)
        self.assertEqual(notice_lines(third.stderr), [])
        later = self.failure_run()
        self.assertEqual(later["count"], 3)
        self.assertEqual(later["host_notice"]["count"], 3)
        self.assertEqual(later["host_notice"]["emitted_at"], emitted)
        self.assertNotEqual(later["window_end"], cond["window_end"])
        self.assertEqual(later["window_start"], cond["window_start"])
        self.assertFalse((self.repo / ".kaola" / "heartbeat-prompt.json").exists())

    def test_window_pass_arms_heartbeat_without_a_second_notice(self) -> None:
        self.endpoint = issue299.Endpoint()
        self.fail_event(1, 401, 15)
        second = self.fail_event(2, 401, 15)
        self.assertEqual(len(notice_lines(second.stderr)), 1)
        self.assertIn("heartbeat-applies=false", second.stderr)
        self.assertEqual(self.receipts()[-1]["route"], issue299.ROTATE_KEY_ROUTE)
        emitted = self.failure_run()["host_notice"]["emitted_at"]
        doc = self.store()
        end = doc["repeated_failure"]["window_end"]
        end_s = calendar.timegm(time.strptime(end, "%Y-%m-%dT%H:%M:%SZ"))
        doc["repeated_failure"]["window_start"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(end_s - 20 * 60))
        self.receipts_path().write_text(
            json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
            encoding="utf-8")
        third = self.fail_event(3, 401, 15)
        self.assertEqual(notice_lines(third.stderr), [])
        cond = self.failure_run()
        self.assertIs(cond["window_passed"], True)
        self.assertIs(cond["heartbeat"]["applies"], True)
        self.assertEqual(cond["heartbeat"]["bound_seconds"], 7200)
        self.assertEqual(cond["heartbeat"]["path"], "heartbeat")
        self.assertEqual(cond["count"], 3)
        self.assertEqual(cond["host_notice"]["emitted_at"], emitted)
        self.assertEqual(cond["user_notice"], "once")
        self.assertFalse((self.repo / ".kaola" / "heartbeat-prompt.json").exists())

    def test_unparseable_window_does_not_claim_the_heartbeat(self) -> None:
        self.endpoint = issue299.Endpoint()
        self.fail_event(1, 401, 15)
        self.fail_event(2, 401, 15)
        doc = self.store()
        doc["repeated_failure"]["window_start"] = "not-a-time"
        self.receipts_path().write_text(json.dumps(doc), encoding="utf-8")
        third = self.fail_event(3, 401, 15)
        self.assertEqual(notice_lines(third.stderr), [])
        cond = self.failure_run()
        self.assertIs(cond["window_passed"], False)
        self.assertIs(cond["heartbeat"]["applies"], False)
        self.assertEqual(cond["count"], 3)
        self.assertEqual(cond["heartbeat"]["bound_seconds"], 7200)

    def test_delivery_ends_the_run_and_a_skip_does_not(self) -> None:
        self.endpoint = issue299.Endpoint()
        self.fail_event(1, 401, 15)
        self.fail_event(2, 401, 15)
        self.write_config({})
        skipped = self.deliver(self.payload(3), timeout=15)
        self.assertEqual(skipped.returncode, 0, skipped.stderr)
        self.assertEqual(self.receipts()[-1]["skip_reason"], "not-configured")
        self.assertEqual(notice_lines(skipped.stderr), [])
        self.assertEqual(self.failure_run()["count"], 2)
        self.assertIs(self.failure_run()["active"], True)
        self.assertIsNone(self.failure_run()["ended_at"])

        self.succeed(4)
        ended = self.failure_run()
        self.assertIs(ended["active"], False)
        self.assertIsInstance(ended["ended_at"], str)
        self.assertIs(ended["heartbeat"]["applies"], False)
        self.assertEqual(ended["user_notice"], "once")
        self.assertIsNone(self.store().get("previous_repeated_failure"))

        quiet = self.fail_event(5, 401, 15)
        self.assertEqual(notice_lines(quiet.stderr), [])
        self.assertEqual(self.failure_run()["count"], 1)
        self.assertIs(self.failure_run()["active"], False)
        previous = self.store()["previous_repeated_failure"]
        self.assertEqual(previous["count"], 2)
        self.assertIs(previous["host_notice"]["once"], True)
        self.assertIs(previous["active"], False)

        again = self.fail_event(6, 401, 15)
        self.assertEqual(len(notice_lines(again.stderr)), 1)
        self.assertEqual(self.failure_run()["count"], 2)
        self.assertEqual(self.failure_run()["last_event"]["event_seq"], 6)
        self.assertEqual(self.store()["previous_repeated_failure"]["window_start"],
                         previous["window_start"])
        self.assertEqual(self.store()["previous_repeated_failure"]["last_event"]["event_seq"], 2)


class FailedReceiptRetention(OutageCase):
    def test_failed_receipts_survive_the_next_32_deliveries(self) -> None:
        self.endpoint = issue299.Endpoint()
        self.fail_event(1, 401, 15)
        self.fail_event(2, 401, 15)
        for seq in range(3, 36):
            self.succeed(seq)
        ring = self.receipts()
        self.assertEqual(len(ring), 32)
        self.assertTrue(all(item["result"] == "delivered" for item in ring))
        self.assertNotIn(1, [item["event_seq"] for item in ring])
        self.assertNotIn(2, [item["event_seq"] for item in ring])
        failed = self.store()["failed_receipts"]
        self.assertEqual([item["event_seq"] for item in failed], [1, 2])
        self.assertTrue(all(item["result"] == "failed" and item["final"] is True
                            and item["http_status"] == 401 for item in failed))
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["failed_receipts_kept"], 2)
        self.assertEqual(status["last_receipt"]["result"], "delivered")

    def test_failed_archive_drops_the_oldest_past_256(self) -> None:
        self.endpoint = issue299.Endpoint()
        rows = [{
            "ts": "2026-01-01T00:00:00Z",
            "result": "failed",
            "final": True,
            "error": "http-status",
            "http_status": 400,
            "holder_instance_id": "h-old",
            "event_seq": seq,
        } for seq in range(256)]
        path = self.receipts_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema": "kaola-delegator-webhook-receipts/1",
            "limit": 32,
            "failed_limit": 256,
            "receipts": [],
            "failed_receipts": rows,
        }), encoding="utf-8")
        self.fail_event(9000, 401, 15)
        failed = self.store()["failed_receipts"]
        self.assertEqual(len(failed), 256)
        seqs = [item["event_seq"] for item in failed]
        self.assertNotIn(0, seqs)
        self.assertIn(9000, seqs)
        self.assertEqual(seqs[0], 1)
        for seq in range(9001, 9034):
            self.succeed(seq)
        failed = self.store()["failed_receipts"]
        self.assertEqual(len(failed), 256)
        self.assertIn(9000, [item["event_seq"] for item in failed])
        self.assertEqual(len(self.receipts()), 32)
        self.assertTrue(all(item["result"] == "delivered" for item in self.receipts()))


class OnceNoticeStatement(unittest.TestCase):
    def test_once_notice_statement_is_wired(self) -> None:
        for name in ("webhook-wake.md", "inquiry-report.md"):
            template = REPO / "templates" / "kaola-delegator" / "references" / name
            rendered = REPO / "skills" / "kaola-delegator" / "references" / name
            text = template.read_text(encoding="utf-8")
            self.assertIn(ONCE_NOTICE, text, name)
            self.assertEqual(rendered.read_bytes(), template.read_bytes(), name)
            self.assertLessEqual(len(template.read_bytes()), 8192, name)
        wake = (REPO / "templates" / "kaola-delegator" / "references"
                / "webhook-wake.md").read_text(encoding="utf-8")
        self.assertIn("wakes `needs_decision` only from `state.decisions`", wake)
        self.assertIn("A `.kaola/run` file or turn text does not", wake)
        self.assertIn("including the turn after a compaction reload", wake)
        self.assertIn("Same `window_start`: do not repeat.", wake)
        inquiry = (REPO / "templates" / "kaola-delegator" / "references"
                   / "inquiry-report.md").read_text(encoding="utf-8")
        self.assertIn(issue299.MISSED_WAKE_INQUIRY, inquiry)
        api = (REPO / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertIn(ONCE_NOTICE, api)
        validate = (REPO / "scripts" / "validate.sh").read_text(encoding="utf-8")

        def array_body(name: str) -> str:
            start = validate.index(f"{name}=(")
            return validate[start:validate.index("\n)", start)]

        self.assertIn("test-issue-325-webhook-outage.py", array_body("python_suites_all"))
        self.assertIn("test-issue-325-webhook-outage.py", array_body("python_suites_b"))
        self.assertNotIn("test-issue-325-webhook-outage.py", array_body("python_suites_a"))


if __name__ == "__main__":
    unittest.main()
