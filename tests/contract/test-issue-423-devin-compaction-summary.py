#!/usr/bin/env python3
"""Issue #423: a Devin compaction signal requires a non-empty ``summary``.

Measured fact (docs/evidence/issue-423-devin-compaction-census.md): Devin
3000.11.92 emits summary-less ``_cognition.ai/compaction`` started/completed
notification pairs on ordinary agent steps with no context reduction. Only a
``completed`` notification whose ``params.summary`` is a non-empty string is a
real compaction; the 84 measured summary-carrying completions were all real
compactions and every summary-less completion without a context-window switch
left the context untouched.

Two layers, both offline and deterministic:

* ``scripts/kaola-compact-recovery.py`` accepts a Devin ``completed``
  notification only when ``params.summary`` is a non-blank string, in both the
  raw JSON-RPC and the ``events.jsonl`` record shapes.
* ``scripts/kaola-acp-holder.py`` fed a summary-less started/completed pair
  through its real notification entry records no ``compact_reload_detected``,
  no ``compact_reload_delivered``, calls ``op_prompt`` zero times, and leaves
  the reload tracker with no pending obligation; the same holder fed a
  summary-carrying completion detects and delivers exactly once.

No model session, no real CLI, no login, and no network.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HELPER = PROJECT / "scripts" / "kaola-compact-recovery.py"
HOLDER_SCRIPT = PROJECT / "scripts" / "kaola-acp-holder.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUMMARY = ("Full conversation history saved at /tmp/history_x.md.\n"
           "Summary:\n<summary>\n1. Request and Intent: ...</summary>")


def devin_notification(session_id: str, status: str, **extra):
    params = {"sessionId": session_id, "status": status}
    params.update(extra)
    return {"method": "_cognition.ai/compaction", "params": params}


def devin_record(session_id: str, status: str, **extra):
    note = devin_notification(session_id, status, **extra)
    return {"kind": "notification", "method": note["method"],
            "params": note["params"]}


class DevinSummaryClassifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cr = load_module("kaola_compact_recovery_423", HELPER)

    def test_summary_less_completed_is_rejected_both_forms(self) -> None:
        # The measured ordinary-step shape: started/completed, no summary.
        for form in (devin_notification("glowing-mandrill", "completed"),
                     devin_record("glowing-mandrill", "completed")):
            with self.subTest(form=form):
                self.assertIsNone(self.cr.classify(form))
                self.assertIsNone(self.cr.classify(form, "devin"))

    def test_non_string_or_blank_summary_is_rejected(self) -> None:
        for summary in ("", "   ", None, 123, {}):
            for builder in (devin_notification, devin_record):
                message = builder("s1", "completed", summary=summary)
                with self.subTest(summary=summary, builder=builder.__name__):
                    self.assertIsNone(self.cr.classify(message))

    def test_started_with_summary_is_rejected(self) -> None:
        self.assertIsNone(self.cr.classify(
            devin_notification("s1", "started", summary=SUMMARY)))
        self.assertIsNone(self.cr.classify(
            devin_record("s1", "started", summary=SUMMARY)))

    def test_completed_with_summary_is_a_signal_both_forms(self) -> None:
        expected = self.cr.CompactSignal("devin-compaction", "s1", None)
        for form in (devin_notification("s1", "completed", summary=SUMMARY),
                     devin_record("s1", "completed", summary=SUMMARY)):
            with self.subTest(form=form):
                self.assertEqual(self.cr.classify(form), expected)
                self.assertEqual(self.cr.classify(form, "devin"), expected)


class DevinSummaryHolderTests(unittest.TestCase):
    """A real in-process Devin holder, worker role, no live turn."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.holder = load_module("kaola_acp_holder_423", HOLDER_SCRIPT)

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def devin_worker(self):
        """A ready worker holder with an established session and a live agent."""
        session = "glowing-mandrill"
        record_dir = self.root / "devin" / session / "digest0123456789ab"
        record_dir.mkdir(parents=True)
        args = argparse.Namespace(
            record_dir=str(record_dir),
            socket=str(self.root / f"{session}.sock"),
            platform="devin", session=session, repo=str(self.root),
            init_meta="", command="stub", session_role="worker",
            host_entry="", resume=None, use_continue=False)
        seat = self.holder.Holder(args)
        seat.session_role = "worker"
        seat.state = "ready"
        seat.stop_requested = False
        seat.acp_session_id = session
        seat.turn["active"] = False
        # A live agent without a real process: delivery checks proc is not
        # None and the exit event is unset; write_record reads the pid.
        seat.agent.proc = types.SimpleNamespace(pid=987654)
        self.prompts = []
        seat.op_prompt = self.record_prompt
        return seat

    def record_prompt(self, params):
        self.prompts.append(params)
        return {"outcome": "in_progress", "mutation_performed": True,
                "turn_request_id": "req-self-1",
                "prompt_fingerprint": "sha256:x"}

    def event_rows(self, seat) -> list[dict]:
        path = Path(seat.record_dir) / "events.jsonl"
        rows = []
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def events_of(self, seat, kind: str) -> list[dict]:
        return [row for row in self.event_rows(seat) if row.get("kind") == kind]

    def test_summary_less_pair_triggers_no_reload(self) -> None:
        seat = self.devin_worker()
        # The negative is only meaningful when the compact module is loaded.
        self.assertIsNotNone(self.holder.compact_module())
        session = seat.acp_session_id
        # The real notification entry: ``on_agent_notification`` observes every
        # non-``session/update`` method through ``_observe_compact_signal``.
        seat.on_agent_notification(devin_notification(session, "started"))
        seat.on_agent_notification(devin_notification(session, "completed"))
        self.assertEqual(self.events_of(seat, "compact_reload_detected"), [])
        self.assertEqual(self.events_of(seat, "compact_reload_delivered"), [])
        self.assertEqual(self.prompts, [])
        self.assertTrue(seat.compact_reload is None
                        or not seat.compact_reload.pending)

    def test_completed_with_summary_detects_and_delivers_once(self) -> None:
        seat = self.devin_worker()
        self.assertIsNotNone(self.holder.compact_module())
        seat.on_agent_notification(
            devin_notification(seat.acp_session_id, "completed",
                               summary=SUMMARY))
        detected = self.events_of(seat, "compact_reload_detected")
        delivered = self.events_of(seat, "compact_reload_delivered")
        self.assertEqual(len(detected), 1, self.event_rows(seat))
        self.assertEqual(detected[0].get("source"), "devin-compaction")
        self.assertEqual(len(delivered), 1, self.event_rows(seat))
        self.assertEqual(len(self.prompts), 1)
        self.assertEqual(self.prompts[0].get("_prompt_source"), "self")


if __name__ == "__main__":
    unittest.main()
