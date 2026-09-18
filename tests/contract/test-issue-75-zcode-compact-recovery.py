#!/usr/bin/env python3
"""Issue #75: the shipped ZCode compact-recovery reference is honest.

The only live-verified *durable* carrier is a short standing instruction a
project owner authorizes into the consuming project's ``AGENTS.md`` before
the Host session starts; the per-send carrier covers known compactions and
cannot alone cover the automatic same-turn case. These tests pin the
shipped text's contract: a reusable marker-free block, recovery that
re-reads the Skill in use and never re-dispatches, explicit evidence
levels, and the boundaries the mechanism must never cross.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
REF = (PROJECT / "templates" / "orchestrator" / "references"
       / "zcode-compact-recovery.md")
HOST_STARTUP = (PROJECT / "templates" / "orchestrator" / "references"
                / "host-startup.md.tmpl")

TEXT = REF.read_text(encoding="utf-8")
STARTUP_TEXT = HOST_STARTUP.read_text(encoding="utf-8")


def durable_block() -> str:
    """The fenced reusable block following the durable-carrier heading."""
    m = re.search(r"durable carrier — reusable block.*?```text\n(.*?)```",
                  TEXT, re.S)
    assert m, "reference must ship the reusable durable block"
    return m.group(1)


class TestDurableBlock(unittest.TestCase):
    def test_owner_authorized_pre_session(self):
        self.assertIn("owner-authorized", TEXT)
        self.assertRegex(TEXT, r"before (the Host )?session starts?")

    def test_block_is_marker_free_and_parameterized(self):
        block = durable_block()
        # no fixed cross-project marker/schema in the reusable text
        for experiment_id in ("KPR-AGENTS-DURABLE", "KPR-PREFIX-CARRIER",
                              "KPR-SKILL-RELOAD-7931", "KPR-SKILL-RELOAD-8842",
                              "KPR-ZCODE-RECOVERY"):
            self.assertNotIn(experiment_id, block)
        # the only fill-in is the installed Skill path
        self.assertIn("<installed SKILL.md path>", block)

    def test_block_recovers_without_redispatch(self):
        block = durable_block()
        self.assertIn("re-read", block)
        self.assertIn("authorization", block)
        self.assertIn("heartbeat", block)
        self.assertRegex(block, r"(?s)never.*re-dispatch")

    def test_block_serves_runner_and_delegator(self):
        self.assertIn("kaola-project-runner", TEXT)
        self.assertIn("kaola-delegator", TEXT)

    def test_role_contrast_scopes_to_host(self):
        # one Runner per project: the block names the designated Host and
        # explicitly tells ordinary Workers to pass over it
        block = durable_block()
        self.assertIn("designated", block)
        self.assertRegex(block, r"(?i)ordinary workers?.*(ignore|pass over)")
        self.assertRegex(block, r"(?i)never makes a worker into a runner")
        self.assertNotIn("every agent", block.lower())

    def test_reload_proof_stays_inside_skill_payload(self):
        # the proof marker is Skill-internal, so any project can adopt the
        # same block without registering a marker
        self.assertIn("KPR-SKILL-RELOAD-V1", TEXT)
        self.assertIn("reload marker inside", durable_block())


class TestPerSendCarrier(unittest.TestCase):
    def test_carrier_still_shipped(self):
        self.assertIn("KPR-ZCODE-RECOVERY-V1", TEXT)
        self.assertIn("never re-intake, re-claim, restart sessions, "
                      "or re-dispatch", TEXT)

    def test_per_send_carrier_scoped_to_host(self):
        # the prompt carrier targets the designated Host session only
        self.assertIn("designated ZCode Project", TEXT)
        self.assertRegex(TEXT, r"(?i)never an ordinary worker")

    def test_send_alone_is_not_durable(self):
        self.assertRegex(TEXT, r"cannot prove the automatic same-turn")


class TestEvidenceHonesty(unittest.TestCase):
    def test_auto_compaction_recorded_as_wire_verified(self):
        self.assertIn('trigger:"auto"', TEXT)
        self.assertIn("MOCK", TEXT)
        self.assertIn("on the wire", TEXT)

    def test_real_glm_auto_marked_unverified(self):
        m = re.search(r"Not verified:(.*?)\n\n", TEXT, re.S)
        assert m, "reference must keep an explicit not-verified list"
        self.assertIn("GLM", m.group(1))
        self.assertIn("auto", m.group(1))

    def test_manual_glm_marked_verified(self):
        m = re.search(r"Verified live .*?:(.*?)Not verified", TEXT, re.S)
        assert m
        self.assertIn("GLM", m.group(1))
        self.assertIn("/compact", m.group(1))


class TestBoundaries(unittest.TestCase):
    def test_never_writes_consuming_agents(self):
        self.assertRegex(TEXT, r"never writes a consuming project.s "
                             r"`AGENTS\.md`")

    def test_no_hook_polling_or_gate(self):
        for banned in ("polling", "global hook"):
            self.assertIn(banned, TEXT)  # named as forbidden
        self.assertIn("transport-only", TEXT)
        self.assertRegex(TEXT, r"never a\s+transport gate")

    def test_startup_points_at_durable_carrier(self):
        self.assertIn("AGENTS.md", STARTUP_TEXT)
        self.assertIn('trigger:"auto"', STARTUP_TEXT)
        self.assertIn("owner-authorized", STARTUP_TEXT)
        self.assertIn("automatic same-turn", STARTUP_TEXT)


if __name__ == "__main__":
    unittest.main()
