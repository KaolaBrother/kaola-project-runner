#!/usr/bin/env python3
"""Issue #118: the authorized worker count is a hard cap on live processes.

Finished Claude Code seats stayed alive after their deliveries were accepted,
and the Host read them as keep-alive capacity: the authorized count was
exceeded by finished processes and later tasks were chained into sessions whose
context belonged to an earlier assignment. The Host-read text allowed that
reading ("Leave capacity idle", "Stop an idle exact session only when no
suitable authorized work is executable", "Only new authorized work restarts a
session once the idle ones were stopped").

This suite pins the replacement rule on every surface the Host reads each beat
(generated main Skill, heartbeat skeleton, ZCode Host dispatch reference, issue
dispatch reference), asserts the superseded sentences are gone, asserts the
one-sentence summaries in the maintainer docs, and asserts the rule did not
leak into the outer Agent's surfaces (host-startup and Kaola-Delegator), which
hand over the count as intake and never schedule.

The heartbeat skeleton uses typed tasks and tool views. The main Skill owns
the cap and stop rules; the skeleton does not repeat them.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "skills" / "kaola-project-runner"
SKILL = MAIN / "SKILL.md"
REFS = MAIN / "references"
DELEGATOR_TEMPLATES = ROOT / "templates" / "kaola-delegator"
DELEGATOR_SKILL = ROOT / "skills" / "kaola-delegator"


def flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def tree(root: Path) -> str:
    return " ".join(flat(p) for p in sorted(root.rglob("*")) if p.is_file())


SUPERSEDED = (
    "Leave capacity idle rather than invent work",
    "Stop an idle exact session only when no suitable authorized work is executable",
    "Only new authorized work restarts a session once the idle ones were stopped",
    "无合适工作则保持空闲",
    "没有合适工作的闲置会话才关闭",
)

# Sentences that carry the scheduling rule; none may appear on an outer surface.
SCHEDULING = (
    r"hard cap",
    r"stop-before-start",
    r"stop one seat before starting",
    r"awaiting acceptance",
    r"live N / authorized M",
    r"same assignment only",
)


class MainSkill(unittest.TestCase):
    def setUp(self) -> None:
        self.text = flat(SKILL)

    def test_count_is_a_hard_cap_on_live_processes_including_acp(self) -> None:
        self.assertRegex(self.text, r"count is a hard cap on live worker processes, ACP holders included")
        self.assertIn("a finished seat counts until its `stop` receipt", self.text)
        self.assertIn("Named CLI without a count: one; it bounds live processes.", self.text)

    def test_quota_reconciliation_keeps_no_quota_system(self) -> None:
        self.assertIn("Do not invent a quota system: the cap is that count", self.text)
        self.assertIn("open-ended concurrency is its own cap", self.text)

    def test_stop_before_start_at_the_cap(self) -> None:
        self.assertIn("At the hard cap, stop one seat before starting any new one (stop-before-start)", self.text)

    def test_only_legal_idle_is_awaiting_acceptance_then_stop_same_beat(self) -> None:
        self.assertIn("The only legal idle seat is one whose delivery is awaiting acceptance", self.text)
        # Issue #208: an accepted seat keeps the finalize/cleanup duties it
        # owns, and is exact-stopped once they finish or are handed off.
        self.assertIn("an accepted seat keeps only the finalize/cleanup duties it owns", self.text)
        self.assertRegex(self.text, r"Once it owns none \(done or explicitly handed off\) or the seat is "
                                    r"abandoned, exact-stop it in that same beat")
        self.assertIn("a rejected delivery's repair is the same assignment", self.text)

    def test_new_task_is_new_session_resume_is_same_assignment_only(self) -> None:
        self.assertIn(
            "New authorized work or another task gets a fresh `start` under a new standard name, "
            "never a finished seat",
            self.text,
        )
        self.assertIn("`--resume`/`--continue` recover the same assignment only", self.text)

    def test_report_carries_live_over_authorized(self) -> None:
        self.assertIn("report `live N / authorized M` and the seats stopped this beat", self.text)
        self.assertIn("N > M with no stop that beat violates the cap", self.text)

    def test_description_names_the_cap(self) -> None:
        self.assertIn("cap live workers at the authorized count", self.text)

    def test_superseded_sentences_are_gone(self) -> None:
        for sentence in SUPERSEDED:
            with self.subTest(sentence=sentence):
                self.assertNotIn(sentence, self.text)


class HeartbeatSkeleton(unittest.TestCase):
    def setUp(self) -> None:
        self.text = flat(REFS / "heartbeat-skeleton.md")

    def test_rule_is_deferred_to_the_main_skill(self) -> None:
        # The main Skill owns cap/stop policy. The example retains typed work.
        self.assertIn("不复述 Skill 规则", self.text)
        example = re.search(r"例：(\{.*\})", self.text)
        self.assertIsNotNone(example)
        body = json.loads(example.group(1))
        self.assertIsInstance(body["tasks"], list)
        ids = [task["id"] for task in body["tasks"]]
        self.assertTrue(ids)
        self.assertTrue(all(isinstance(ident, str) and ident for ident in ids))
        self.assertEqual(len(ids), len(set(ids)))
        for task in body["tasks"]:
            self.assertIn(task["stage"], {"todo", "doing", "review", "closeout", "done"})
            self.assertIsInstance(task["goal"], str)
        for old in ("active", "pending", "workers"):
            self.assertNotIn(old, body)
        for restated in ("达上限先精确 stop 一个再 start", "验收完成或放弃该席位的同一拍即精确 stop"):
            with self.subTest(restated=restated):
                self.assertNotIn(restated, self.text)

    def test_superseded_sentences_are_gone(self) -> None:
        for sentence in SUPERSEDED + ("之后有新授权工作才 start/--resume/--continue",):
            with self.subTest(sentence=sentence):
                self.assertNotIn(sentence, self.text)


class ZCodeHostDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.text = flat(REFS / "zcode-host-dispatch.md")

    def test_count_before_start(self) -> None:
        self.assertIn("Count before every direct `start`", self.text)
        # Issue #157 (§1.2): stop-before-start is stated once, in main Skill step 2.
        self.assertIn("At the hard cap: stop-before-start (main Skill step 2)", self.text)

    def test_stop_in_same_beat_after_acceptance(self) -> None:
        # Issue #157 (§1.2) / #208: the seat lifecycle is stated once, in main Skill step 5.
        self.assertIn("keep or exact-`stop` the seat per main Skill step 5", self.text)
        self.assertNotIn("once accepted, exact-`stop` that seat this beat", self.text)
        self.assertNotIn("Then accept, fix, or dispatch more", self.text)

    def test_finish_the_beat_reports_live_over_authorized(self) -> None:
        # Issue #157 (§1.2): `live N / authorized M` lives in main Skill §Report.
        self.assertIn("report as main Skill §Report says", self.text)


class IssueDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.text = flat(REFS / "issue-dispatch.md")

    def test_reassignment_is_stop_and_new_named_start(self) -> None:
        self.assertIn(
            "A worker reassigned to a different issue is exact-stopped and a new-named session is "
            "started - never a live rename and never a chained prompt",
            self.text,
        )
        self.assertNotRegex(self.text, r"reassigned to a different issue gets a new Runner session name")

    def test_resume_is_same_issue_recovery(self) -> None:
        self.assertIn("`--resume` stays same-issue recovery only", self.text)


class OuterSurfacesStayClean(unittest.TestCase):
    """Delegator and host-startup hand over the count; they never schedule."""

    def test_no_scheduling_rule_outside_the_host_read_surfaces(self) -> None:
        surfaces = {
            "host-startup.md": flat(REFS / "host-startup.md"),
            "templates/kaola-delegator": tree(DELEGATOR_TEMPLATES),
            "skills/kaola-delegator": tree(DELEGATOR_SKILL),
        }
        for name, text in surfaces.items():
            for pattern in SCHEDULING:
                with self.subTest(surface=name, pattern=pattern):
                    self.assertNotRegex(text, pattern)


class MaintainerDocs(unittest.TestCase):
    def test_each_doc_names_the_cap_and_stop_before_start(self) -> None:
        for rel in ("docs/architecture.md", "docs/zcode-host.md", "README.md"):
            with self.subTest(doc=rel):
                text = flat(ROOT / rel)
                self.assertRegex(
                    text,
                    r"authorized count[^.]{0,40}hard cap on live worker processes[^.]{0,200}stop-before-start",
                )

    def test_old_summaries_are_gone(self) -> None:
        self.assertNotIn("stops leftover idle owned sessions (including ACP)", flat(ROOT / "docs/architecture.md"))
        self.assertNotIn("Completion stops leftover idle owned sessions", flat(ROOT / "README.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
