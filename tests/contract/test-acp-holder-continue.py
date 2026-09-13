#!/usr/bin/env python3
"""Issue #28 contract: shared holder capability detection and continue selection.

Codex advertises session capabilities as empty objects (``{}``), which are
valid support markers. ``--continue`` must follow ``session/list`` ``nextCursor``
pages and select the eligible session with the newest ``updatedAt`` rather than
trusting array order.

- unit: ``capability_supported`` presence semantics and ``latest_session``
  winner/tie/indeterminate selection
- integration: ``kaola-acp.py codex start --continue`` against the mock agent
  with ``--caps-objects`` and ``MOCK_ACP_LIST_PAGES`` fixtures
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
HOLDER_PATH = PROJECT / "scripts" / "kaola-acp-holder.py"

spec = importlib.util.spec_from_file_location("kaola_acp_holder", HOLDER_PATH)
holder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(holder)


class CapabilityDetectionTests(unittest.TestCase):
    def test_empty_object_capability_is_supported(self) -> None:
        self.assertTrue(holder.capability_supported({"resume": {}}, "resume"))

    def test_true_capability_is_supported(self) -> None:
        self.assertTrue(holder.capability_supported({"resume": True}, "resume"))

    def test_absent_capability_is_unsupported(self) -> None:
        self.assertFalse(holder.capability_supported({}, "resume"))

    def test_null_capability_is_unsupported(self) -> None:
        self.assertFalse(holder.capability_supported({"resume": None}, "resume"))

    def test_false_capability_is_unsupported(self) -> None:
        self.assertFalse(holder.capability_supported({"resume": False}, "resume"))

    def test_codex_shape_all_supported(self) -> None:
        caps = {"loadSession": True,
                "sessionCapabilities": {"resume": {}, "list": {}, "close": {}}}
        session_caps = caps["sessionCapabilities"]
        for key in ("resume", "list", "close"):
            self.assertTrue(holder.capability_supported(session_caps, key))
        self.assertTrue(holder.capability_supported(caps, "loadSession"))


class LatestSessionTests(unittest.TestCase):
    def test_out_of_order_picks_newest_updated_at(self) -> None:
        sessions = [
            {"sessionId": "new", "updatedAt": "2026-08-30T15:41:06.316Z"},
            {"sessionId": "old", "updatedAt": "2026-01-01T00:00:00.000Z"},
            {"sessionId": "mid", "updatedAt": "2026-05-05T05:05:05.000Z"},
        ]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["sessionId"], "new")
        self.assertEqual(candidates, [])

    def test_last_element_is_not_trusted(self) -> None:
        sessions = [
            {"sessionId": "older", "updatedAt": "2026-01-01T00:00:00.000Z"},
            {"sessionId": "newest", "updatedAt": "2026-12-31T00:00:00.000Z"},
            {"sessionId": "middle", "updatedAt": "2026-06-01T00:00:00.000Z"},
        ]
        latest, _ = holder.latest_session(sessions)
        self.assertEqual(latest["sessionId"], "newest")

    def test_tie_is_ambiguous(self) -> None:
        sessions = [
            {"sessionId": "a", "updatedAt": "2026-08-30T15:41:06.316Z"},
            {"sessionId": "b", "updatedAt": "2026-08-30T15:41:06.316Z"},
        ]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNone(latest)
        self.assertEqual(len(candidates), 2)

    def test_no_timestamps_is_indeterminate(self) -> None:
        sessions = [{"sessionId": "a"}, {"sessionId": "b"}]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNone(latest)
        self.assertEqual(len(candidates), 2)

    def test_offsets_compare_instants_not_strings(self) -> None:
        # "2026-09-13T10:00:00+08:00" sorts after "2026-09-13T03:00:00Z"
        # lexically but is the older instant (02:00Z < 03:00Z).
        sessions = [
            {"sessionId": "plus-eight", "updatedAt": "2026-09-13T10:00:00+08:00"},
            {"sessionId": "utc", "updatedAt": "2026-09-13T03:00:00Z"},
        ]
        latest, _ = holder.latest_session(sessions)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["sessionId"], "utc")

    def test_fractional_offsets_compare_instants(self) -> None:
        sessions = [
            {"sessionId": "a", "updatedAt": "2026-09-13T10:00:00.500+08:00"},
            {"sessionId": "b", "updatedAt": "2026-09-13T02:00:00.600Z"},
        ]
        latest, _ = holder.latest_session(sessions)
        self.assertEqual(latest["sessionId"], "b")

    def test_missing_timestamp_is_indeterminate(self) -> None:
        sessions = [
            {"sessionId": "dated", "updatedAt": "2026-08-30T15:41:06.316Z"},
            {"sessionId": "undated"},
        ]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNone(latest)
        self.assertEqual(
            sorted(e["sessionId"] for e in candidates), ["dated", "undated"])

    def test_invalid_timestamp_is_indeterminate(self) -> None:
        sessions = [
            {"sessionId": "dated", "updatedAt": "2026-08-30T15:41:06.316Z"},
            {"sessionId": "garbage", "updatedAt": "not-a-timestamp"},
        ]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNone(latest)
        self.assertEqual(len(candidates), 2)

    def test_naive_timestamp_is_not_an_instant(self) -> None:
        self.assertIsNone(holder.rfc3339_instant("2026-09-13T03:00:00"))
        sessions = [
            {"sessionId": "dated", "updatedAt": "2026-08-30T15:41:06.316Z"},
            {"sessionId": "naive", "updatedAt": "2026-09-13T03:00:00"},
        ]
        latest, _ = holder.latest_session(sessions)
        self.assertIsNone(latest)

    def test_duplicate_identity_never_creates_ambiguity(self) -> None:
        sessions = [
            {"sessionId": "same", "updatedAt": "2026-08-30T15:41:06.316Z"},
            {"sessionId": "same", "updatedAt": "2026-09-01T00:00:00.000Z"},
        ]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["sessionId"], "same")
        self.assertEqual(latest["updatedAt"], "2026-09-01T00:00:00.000Z")
        self.assertEqual(candidates, [])

    def test_duplicate_identity_with_missing_timestamp_still_resolves(self) -> None:
        sessions = [
            {"sessionId": "same", "updatedAt": "2026-09-01T00:00:00.000Z"},
            {"sessionId": "same"},
        ]
        latest, _ = holder.latest_session(sessions)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["sessionId"], "same")

    def test_distinct_ids_at_equal_instant_stay_ambiguous(self) -> None:
        sessions = [
            {"sessionId": "a", "updatedAt": "2026-09-13T03:00:00Z"},
            {"sessionId": "b", "updatedAt": "2026-09-13T11:00:00+08:00"},
        ]
        latest, candidates = holder.latest_session(sessions)
        self.assertIsNone(latest)
        self.assertEqual(len(candidates), 2)


class CodexContinueIntegrationTests(unittest.TestCase):
    """Drive ``kaola-acp.py codex`` against the mock agent with object caps."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-codex-continue-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"i28codex-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False
        if self.mock_log.is_file():
            self.mock_log.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=15)

    def env(self, pages: list[dict] | None = None) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        if pages is not None:
            env["MOCK_ACP_LIST_PAGES"] = json.dumps(pages)
        else:
            env.pop("MOCK_ACP_LIST_PAGES", None)
        return env

    def mock_command(self, caps: str = "load,resume,list,close") -> str:
        return (
            f"{sys.executable} {MOCK} --scenario normal "
            f"--caps {caps} --caps-objects"
        )

    def cli(self, command: str, *args: str, check: bool = True, timeout: float = 30,
            caps: str = "load,resume,list,close",
            pages: list[dict] | None = None) -> dict:
        argv = [
            sys.executable, str(CLI), "codex", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(caps),
            *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(pages), timeout=timeout
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp codex {command} did not emit a JSON receipt\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if check and "error" in receipt:
            self.fail(f"kaola-acp codex {command} returned error {receipt['error']}\nreceipt={receipt}")
        return receipt

    def read_mock_log(self) -> list[dict]:
        if not self.mock_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.mock_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def inbound_methods(self) -> list[str]:
        return [
            event.get("method")
            for event in self.read_mock_log()
            if event.get("event") == "inbound_frame" and event.get("method")
        ]

    def start(self, *args: str, caps: str = "load,resume,list,close",
              pages: list[dict] | None = None, check: bool = True) -> dict:
        receipt = self.cli("start", *args, check=check, caps=caps, pages=pages)
        self._started = True
        return receipt

    # -- {}-object capabilities ------------------------------------------------

    def test_object_caps_advertise_support_in_start_receipt(self) -> None:
        receipt = self.start()
        capabilities = (receipt.get("transport") or {}).get("capabilities") or {}
        session_caps = capabilities.get("sessionCapabilities") or {}
        self.assertEqual(session_caps.get("resume"), {})
        self.assertEqual(session_caps.get("list"), {})
        self.assertEqual(session_caps.get("close"), {})

    def test_object_caps_explicit_resume_uses_session_resume(self) -> None:
        pages = [{"sessions": [
            {"sessionId": "codex-rollout-1", "updatedAt": "2026-08-30T15:41:06.316Z",
             "cwd": str(self.repo)},
        ]}]
        receipt = self.start("--resume", "codex-rollout-1", pages=pages)
        self.assertIsNone(receipt.get("error"), f"resume failed: {receipt}")
        methods = self.inbound_methods()
        self.assertIn("session/resume", methods)
        self.assertNotIn("session/load", methods)
        self.assertEqual(receipt.get("acp_session_id"), "codex-rollout-1")

    def test_object_caps_close_sent_on_stop(self) -> None:
        self.start()
        stop = self.cli("stop", check=False)
        self._started = False
        self.assertIsNone(stop.get("error"), f"stop failed: {stop}")
        self.assertIn("session/close", self.inbound_methods())

    def test_configured_options_surface_upstream_display_names(self) -> None:
        receipt = self.start("--mode", "read-only")
        options = {
            entry.get("config_id"): entry
            for entry in receipt.get("configured_options") or []
        }
        mode = options.get("mode") or {}
        self.assertEqual(mode.get("value"), "read-only")
        self.assertEqual(mode.get("value_name"), "Ask for approval")
        self.assertEqual(
            mode.get("value_description"),
            "Always ask to edit external files and use the internet")
        self.assertEqual(mode.get("option_name"), "Mode")

    # -- paginated continue -----------------------------------------------------

    def test_continue_follows_next_cursor_and_picks_newest(self) -> None:
        pages = [
            {"sessions": [], "nextCursor": "page-2"},
            {"sessions": [
                {"sessionId": "s-mid", "updatedAt": "2026-05-01T00:00:00.000Z",
                 "cwd": str(self.repo)},
                {"sessionId": "s-newest", "updatedAt": "2026-08-30T15:41:06.316Z",
                 "cwd": str(self.repo)},
            ], "nextCursor": "page-3"},
            {"sessions": [
                {"sessionId": "s-old", "updatedAt": "2026-01-01T00:00:00.000Z",
                 "cwd": str(self.repo)},
            ]},
        ]
        receipt = self.start("--continue", pages=pages)
        self.assertIsNone(receipt.get("error"), f"continue failed: {receipt}")
        self.assertEqual(receipt.get("acp_session_id"), "s-newest")
        page_events = [
            event for event in self.read_mock_log()
            if event.get("event") == "session_list_page"
        ]
        self.assertEqual(len(page_events), 3)
        self.assertIn("session/resume", self.inbound_methods())

    def test_continue_empty_first_page_is_not_empty_history(self) -> None:
        pages = [
            {"sessions": [], "nextCursor": "cursor-1"},
            {"sessions": [
                {"sessionId": "s-only", "updatedAt": "2026-08-30T15:41:06.316Z",
                 "cwd": str(self.repo)},
            ]},
        ]
        receipt = self.start("--continue", pages=pages)
        self.assertIsNone(receipt.get("error"), f"continue failed: {receipt}")
        self.assertEqual(receipt.get("acp_session_id"), "s-only")

    def test_continue_ambiguous_reports_identity_evidence(self) -> None:
        pages = [
            {"sessions": [
                {"sessionId": "s-a", "updatedAt": "2026-08-30T15:41:06.316Z",
                 "cwd": str(self.repo)},
                {"sessionId": "s-b", "updatedAt": "2026-08-30T15:41:06.316Z",
                 "cwd": str(self.repo)},
            ]},
        ]
        receipt = self.start("--continue", pages=pages, check=False)
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "continue-ambiguous", receipt)
        candidate_ids = sorted(
            entry.get("sessionId") for entry in error.get("candidates") or []
        )
        self.assertEqual(candidate_ids, ["s-a", "s-b"])

    def test_continue_no_sessions_reports_empty(self) -> None:
        receipt = self.start("--continue", pages=[{"sessions": []}], check=False)
        self.assertEqual((receipt.get("error") or {}).get("code"), "continue-empty", receipt)

    def test_continue_compares_offsets_as_instants(self) -> None:
        pages = [{"sessions": [
            {"sessionId": "s-plus-eight", "updatedAt": "2026-09-13T10:00:00+08:00",
             "cwd": str(self.repo)},
            {"sessionId": "s-utc-newer", "updatedAt": "2026-09-13T03:00:00Z",
             "cwd": str(self.repo)},
        ]}]
        receipt = self.start("--continue", pages=pages)
        self.assertIsNone(receipt.get("error"), f"continue failed: {receipt}")
        self.assertEqual(receipt.get("acp_session_id"), "s-utc-newer")

    def test_continue_duplicate_identity_across_pages_resumes(self) -> None:
        pages = [
            {"sessions": [
                {"sessionId": "s-dup", "updatedAt": "2026-08-30T15:41:06.316Z",
                 "cwd": str(self.repo)},
            ], "nextCursor": "page-2"},
            {"sessions": [
                {"sessionId": "s-dup", "updatedAt": "2026-09-01T00:00:00.000Z",
                 "cwd": str(self.repo)},
            ]},
        ]
        receipt = self.start("--continue", pages=pages)
        self.assertIsNone(receipt.get("error"), f"continue failed: {receipt}")
        self.assertEqual(receipt.get("acp_session_id"), "s-dup")
        self.assertIn("session/resume", self.inbound_methods())

    def test_continue_missing_updated_at_reports_ambiguity(self) -> None:
        pages = [{"sessions": [
            {"sessionId": "s-dated", "updatedAt": "2026-08-30T15:41:06.316Z",
             "cwd": str(self.repo)},
            {"sessionId": "s-undated", "cwd": str(self.repo)},
        ]}]
        receipt = self.start("--continue", pages=pages, check=False)
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "continue-ambiguous", receipt)
        candidate_ids = sorted(
            entry.get("sessionId") for entry in error.get("candidates") or []
        )
        self.assertEqual(candidate_ids, ["s-dated", "s-undated"])


if __name__ == "__main__":
    unittest.main()
