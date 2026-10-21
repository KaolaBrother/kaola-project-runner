#!/usr/bin/env python3
"""Issue #384: view disclosure for dropped rows, cursor gaps and truncation.

The view stays the compacted snapshot (no delta/replay was implemented here).
This suite pins the additive disclosure that makes its losses unambiguous:

* ``messages_dropped`` counts in-process message rows removed by the timeline
  and byte caps;
* ``truncation.rows.messages.timeline`` / ``.bytes`` / ``.restart`` name each
  drop class and its reason, with a restart boundary instead of an invented
  count: prompt admission has no complete prompt text or uniform
  prompt-turn-start rebuild evidence (some agent-initiated turns do record
  ``turn_started``), and this change adds no replay;
* the same gap floor covers row losses outside ``messages[]``: dropped tool
  cards use their internal first-seen cursor, and dropped turns and answered
  permissions use their own cursors;
* ``earliest_cursor`` is the first cursor present in the returned messages;
* ``cursor_gap`` covers both an event-log gap and missing projection rows;
* ``truncated_event_log`` and ``truncated_rows`` split the former single
  ``truncated`` signal; the legacy boolean remains the union of all previous
  signals, including thinking-tail and tool-content caps, which the two new
  booleans do not cover.

The first timeline case is the pre-fix counter-proof: before this change the
payload had no count/earliest fields and reported ``cursor_gap=false`` for a
mid-history cursor even though the projection had already lost its oldest 11
rows. ``test_pre_fix_shape_had_only_a_boolean`` reconstructs that old shape
from the new payload and asserts it cannot answer either question.

Run: python3 tests/contract/test-issue-384-view-disclosure.py -v
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"

_spec = importlib.util.spec_from_file_location("kaola_acp_holder_i384", HOLDER)
assert _spec is not None and _spec.loader is not None
holder_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(holder_module)

NEW_TOP_LEVEL = {
    "messages_dropped",
    "earliest_cursor",
    "cursor_gap_reasons",
    "truncated_event_log",
    "truncated_rows",
    "truncation",
}


class ViewDisclosureTests(unittest.TestCase):
    """In-process holders; no ACP agent or socket is started."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i384-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session_seq = 0
        saved = {key: value for key, value in os.environ.items()
                 if key.startswith("KAOLA_")}
        self.saved_env = saved
        for key in list(saved):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key in list(os.environ):
            if key.startswith("KAOLA_"):
                os.environ.pop(key, None)
        os.environ.update(self.saved_env)
        self.tmp.cleanup()

    def make_holder(self, suffix: str):
        self.session_seq += 1
        session = f"grok-w384-{suffix}-{self.session_seq}"
        digest = hashlib.sha256(str(self.repo).encode("utf-8")).hexdigest()[:16]
        record_dir = self.record_root / "grok" / session / digest
        record_dir.mkdir(parents=True)
        args = argparse.Namespace(
            record_dir=str(record_dir), socket=None, platform="grok",
            session=session, repo=str(self.repo), init_meta="", command="stub",
            resume=None, use_continue=False, session_role="worker",
            host_entry=None, accepted_revision="", start_selection="",
            baseline_exempt="", cli_version="",
        )
        holder = holder_module.Holder(args)
        holder.state = "ready"
        return holder

    @staticmethod
    def append_events(holder, count: int) -> None:
        for _ in range(count):
            holder.events.append({"kind": "session_update"})

    def test_timeline_cap_discloses_count_earliest_and_row_gap(self) -> None:
        """Pre-fix counter-proof: 211 rows become 200 and the old view said nothing."""
        holder = self.make_holder("timeline")
        self.append_events(holder, 5)
        for index in range(211):
            holder.projection.add_user_from_prompt(
                f"row-{index}", index + 1, 1.0 + index)

        view = holder.op_view({"since": 1})
        self.assertEqual(len(view["messages"]), holder_module.TIMELINE_MAX)
        self.assertEqual(view["messages_dropped"], 11)
        self.assertEqual(view["earliest_cursor"], 12)
        self.assertTrue(view["cursor_gap"])
        self.assertEqual(view["cursor_gap_reasons"], ["rows"])
        self.assertFalse(view["truncated_event_log"])
        self.assertTrue(view["truncated_rows"])
        self.assertTrue(view["truncated"])
        messages = view["truncation"]["rows"]["messages"]
        self.assertEqual(messages["kept"], 200)
        self.assertEqual(messages["timeline"],
                         {"dropped": 11, "reason": "timeline-cap"})
        self.assertEqual(messages["bytes"],
                         {"dropped": 0, "reason": "view-bytes"})
        self.assertEqual(messages["restart"],
                         {"dropped": 0, "reason": "holder-restart",
                          "boundary_cursor": None})

        # Without --since there is no cursor_gap, but the loss is still visible.
        full = holder.op_view({})
        self.assertFalse(full["cursor_gap"])
        self.assertEqual(full["messages_dropped"], 11)
        self.assertEqual(full["earliest_cursor"], 12)
        self.assertTrue(full["truncated_rows"])

    def test_byte_cap_discloses_bytes_drop_and_raises_earliest_cursor(self) -> None:
        holder = self.make_holder("bytes")
        self.append_events(holder, 5)
        holder.projection.add_user_from_prompt("prompt", 1, 1.0)
        for index in range(4):
            holder.projection.apply({
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "x" * 120000},
                "messageId": f"big-{index}",
            }, index + 2, 2.0)

        view = holder.op_view({"since": 1})
        self.assertLessEqual(
            len(json.dumps(view, ensure_ascii=False).encode("utf-8")),
            holder_module.VIEW_BYTES,
        )
        self.assertEqual(len(view["messages"]), 2)
        self.assertEqual(view["messages_dropped"], 3)
        self.assertEqual(view["earliest_cursor"], 4)
        self.assertTrue(view["cursor_gap"])
        self.assertEqual(view["cursor_gap_reasons"], ["rows"])
        self.assertFalse(view["truncated_event_log"])
        self.assertTrue(view["truncated_rows"])
        self.assertFalse(any(row["role"] == "user" for row in view["messages"]))
        self.assertEqual(
            view["truncation"]["rows"]["messages"]["bytes"],
            {"dropped": 3, "reason": "view-bytes"},
        )
        self.assertEqual(
            view["truncation"]["rows"]["messages"]["timeline"]["dropped"], 0)
        self.assertEqual(view["truncation"]["rows"]["messages"]["kept"], 2)

    def test_restart_discloses_unknown_drop_and_projection_gap(self) -> None:
        first = self.make_holder("restart")
        self.append_events(first, 5)
        first.projection.add_user_from_prompt("before restart", 1, 1.0)
        first.projection.apply({
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "reply"},
            "messageId": "reply-1",
        }, 2, 2.0)
        self.assertEqual(first.events.cursor, 5)

        # A new holder process keeps the event cursor but starts with an empty
        # projection. No replay is claimed: the count of old rows is unknown.
        second = self.make_holder_like(first, "restart-resumed")
        resumed = second.op_view({})
        self.assertEqual(resumed["event_cursor"], 5)
        self.assertEqual(resumed["messages"], [])
        self.assertIsNone(resumed["earliest_cursor"])
        self.assertEqual(resumed["messages_dropped"], 0)
        self.assertFalse(resumed["cursor_gap"])
        self.assertFalse(resumed["truncated_event_log"])
        self.assertTrue(resumed["truncated_rows"])
        restart = resumed["truncation"]["rows"]["messages"]["restart"]
        self.assertIsNone(restart["dropped"])
        self.assertEqual(restart["reason"], "holder-restart")
        self.assertEqual(restart["boundary_cursor"], 5)

        # Cursor 1 is inside the lost projection range; the event log itself
        # starts at 1, so only the row class can explain this gap.
        at_one = second.op_view({"since": 1})
        self.assertTrue(at_one["cursor_gap"])
        self.assertEqual(at_one["cursor_gap_reasons"], ["rows"])
        self.assertFalse(at_one["truncated_event_log"])
        # The client already holds rows through the reset boundary; no gap.
        self.assertFalse(second.op_view({"since": 5})["cursor_gap"])

        second.projection.add_user_from_prompt("after restart", 6, 3.0)
        second.projection.apply({
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "new"},
            "messageId": "reply-2",
        }, 7, 4.0)
        after = second.op_view({"since": 5})
        self.assertEqual([row["cursor"] for row in after["messages"]], [6, 7])
        self.assertEqual(after["earliest_cursor"], 6)
        self.assertFalse(after["cursor_gap"])
        self.assertTrue(second.op_view({"since": 1})["cursor_gap"])

    def make_holder_like(self, first, suffix: str):
        """Construct a second holder against the first one's exact record dir."""
        self.session_seq += 1
        args = argparse.Namespace(
            record_dir=str(first.record_dir), socket=None, platform="grok",
            session=first.args.session, repo=str(self.repo), init_meta="",
            command="stub", resume=None, use_continue=False,
            session_role="worker", host_entry=None, accepted_revision="",
            start_selection="", baseline_exempt="", cli_version="",
        )
        holder = holder_module.Holder(args)
        holder.state = "ready"
        return holder

    def test_turn_only_timeline_drop_contributes_its_boundary(self) -> None:
        holder = self.make_holder("turn-boundary")
        for index in range(211):
            holder.projection.start_agent_turn(
                holder.events.append({"kind": "turn_started"}), float(index))
        view = holder.op_view({"since": 1})
        self.assertEqual(view["messages_dropped"], 0)
        self.assertEqual(view["truncation"]["rows"]["turns"]["dropped"], 11)
        self.assertEqual(view["turns"][0]["start_cursor"], 12)
        self.assertTrue(view["truncated_rows"])
        self.assertFalse(view["truncated_event_log"])
        self.assertTrue(view["cursor_gap"])
        self.assertEqual(view["cursor_gap_reasons"], ["rows"])
        # The floor is the oldest surviving turn cursor: inside it gaps, at
        # and after it the complete new-row window starts.
        self.assertTrue(holder.op_view({"since": 11})["cursor_gap"])
        self.assertFalse(holder.op_view({"since": 12})["cursor_gap"])
        self.assertFalse(holder.op_view({"since": 13})["cursor_gap"])

    def test_answer_only_timeline_drop_contributes_its_boundary(self) -> None:
        holder = self.make_holder("answer-boundary")
        for index in range(211):
            holder.projection.add_answered_permission({
                "request_id": str(index),
                "cursor": holder.events.append({"kind": "permission_answered"}),
                "answered_at": float(index),
                "title": "fixture",
                "tool_call_id": None,
                "options": [],
                "chosen_option": None,
                "outcome": "cancelled",
            })
        view = holder.op_view({"since": 1})
        self.assertEqual(view["messages_dropped"], 0)
        self.assertEqual(
            view["truncation"]["rows"]["answered_permissions"]["dropped"], 11)
        self.assertEqual(view["answered_permissions"][0]["cursor"], 12)
        self.assertTrue(view["truncated_rows"])
        self.assertFalse(view["truncated_event_log"])
        self.assertTrue(view["cursor_gap"])
        self.assertEqual(view["cursor_gap_reasons"], ["rows"])
        self.assertTrue(holder.op_view({"since": 11})["cursor_gap"])
        self.assertFalse(holder.op_view({"since": 12})["cursor_gap"])
        self.assertFalse(holder.op_view({"since": 13})["cursor_gap"])

    def test_tool_only_bytes_drop_uses_internal_cursor_boundary(self) -> None:
        holder = self.make_holder("tool-boundary")
        for index in range(12):
            holder.projection.apply({
                "sessionUpdate": "tool_call",
                "toolCallId": str(index),
                "content": [{"type": "text", "text": "x" * 30000}],
            }, holder.events.append({"kind": "session_update"}))
        view = holder.op_view({"since": 1})
        dropped = view["truncation"]["rows"]["tools"]["dropped"]
        self.assertGreater(dropped, 1)
        self.assertEqual(dropped + len(view["tools"]), 12)
        self.assertEqual(view["messages_dropped"], 0)
        self.assertTrue(view["truncated_rows"])
        self.assertFalse(view["truncated_event_log"])
        self.assertTrue(view["cursor_gap"])
        self.assertEqual(view["cursor_gap_reasons"], ["rows"])
        self.assertLessEqual(
            len(json.dumps(view, ensure_ascii=False).encode("utf-8")),
            holder_module.VIEW_BYTES,
        )
        # Tool cards have no public cursor; the projection keeps the internal
        # first-seen boundary the public gap is derived from.
        first_retained = str(view["tools"][0]["toolCallId"])
        floor = holder.projection.tool_cursors[first_retained]
        self.assertEqual(floor, 5)
        self.assertTrue(holder.op_view({"since": floor - 1})["cursor_gap"])
        self.assertFalse(holder.op_view({"since": floor})["cursor_gap"])
        self.assertFalse(holder.op_view({"since": floor + 1})["cursor_gap"])

    def test_event_log_gap_and_row_gap_are_separate_classes(self) -> None:
        holder = self.make_holder("classes")
        self.append_events(holder, 5)
        event_only = holder.op_view({"since": 0})
        self.assertTrue(event_only["cursor_gap"])
        self.assertEqual(event_only["cursor_gap_reasons"], ["event-log"])
        self.assertTrue(event_only["truncated_event_log"])
        self.assertFalse(event_only["truncated_rows"])
        self.assertEqual(event_only["truncation"]["event_log"]["oldest_cursor"], 1)

        for index in range(211):
            holder.projection.add_user_from_prompt(
                f"row-{index}", index + 1, 1.0 + index)
        rows_only = holder.op_view({"since": 1})
        self.assertTrue(rows_only["cursor_gap"])
        self.assertEqual(rows_only["cursor_gap_reasons"], ["rows"])
        self.assertFalse(rows_only["truncated_event_log"])
        self.assertTrue(rows_only["truncated_rows"])

        both = holder.op_view({"since": 0})
        self.assertTrue(both["cursor_gap"])
        self.assertEqual(both["cursor_gap_reasons"], ["event-log", "rows"])
        self.assertTrue(both["truncated_event_log"])
        self.assertTrue(both["truncated_rows"])

    def test_truncated_stays_the_union_while_split_flags_stay_specific(self) -> None:
        holder = self.make_holder("split")
        holder.projection.add_user_from_prompt("hello", 1, 1.0)
        clean = holder.op_view({})
        self.assertFalse(clean["truncated"])
        self.assertFalse(clean["truncated_event_log"])
        self.assertFalse(clean["truncated_rows"])
        self.assertEqual(clean["messages_dropped"], 0)
        self.assertEqual(clean["earliest_cursor"], 1)
        self.assertEqual(clean["cursor_gap_reasons"], [])

        holder.projection.apply({
            "sessionUpdate": "agent_thought_chunk",
            "content": {"type": "text",
                        "text": "t" * (holder_module.THINKING_TAIL_CHARS * 2)},
            "messageId": "thought",
        }, 2)
        clipped = holder.op_view({})
        self.assertTrue(clipped["truncated"])
        self.assertFalse(clipped["truncated_event_log"])
        self.assertFalse(clipped["truncated_rows"])
        self.assertEqual(clipped["messages_dropped"], 0)

    def test_pre_fix_shape_had_only_a_boolean(self) -> None:
        """The old payload could not say how many rows or where they began."""
        holder = self.make_holder("prefix")
        self.append_events(holder, 5)
        for index in range(211):
            holder.projection.add_user_from_prompt(
                f"row-{index}", index + 1, 1.0 + index)
        view = holder.op_view({"since": 1})
        legacy = {key: value for key, value in view.items()
                  if key not in NEW_TOP_LEVEL}
        # Pre-fix cursor_gap was exactly the event-log comparison; project the
        # split flag back to that old value instead of reusing the new union.
        legacy["cursor_gap"] = view["truncated_event_log"]
        # This is exactly the pre-fix signal set for a mid-history cursor:
        # truncated=true, cursor_gap=false, and no count or earliest cursor.
        self.assertTrue(legacy["truncated"])
        self.assertFalse(legacy["cursor_gap"])
        self.assertNotIn("messages_dropped", legacy)
        self.assertNotIn("earliest_cursor", legacy)
        self.assertNotIn("truncation", legacy)
        # The same view now answers both questions.
        self.assertEqual(view["messages_dropped"], 11)
        self.assertEqual(view["earliest_cursor"], 12)
        self.assertEqual(
            view["truncation"]["rows"]["messages"]["timeline"],
            {"dropped": 11, "reason": "timeline-cap"},
        )


if __name__ == "__main__":
    unittest.main()
