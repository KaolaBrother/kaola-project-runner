#!/usr/bin/env python3
"""Issue #65: the ZCode Host post-dispatch event-wait contract, as generated.

The delivery here is instruction an Agent can act on without reading Python:
the outer Agent must hand the Host its real Runner identity and keep the Host
while workers are in flight; the Host must bind `KAOLA_ACP_HEARTBEAT_HOST` per
worker start and check the receipt, dispatch non-blocking, update the one
heartbeat prompt, then end the turn naturally instead of sleeping or polling;
and after an event it must read the worker's real reply through that worker's
own Skill. These contracts pin that wording into the generated surface, so a
template edit cannot quietly drop it.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SKILLS = PROJECT / "skills"
ORCH = SKILLS / "kaola-project-runner"
MAIN = ORCH / "SKILL.md"
REF = ORCH / "references" / "zcode-host-dispatch.md"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
ACP = PROJECT / "scripts" / "kaola-acp.py"
BUDGETS = json.loads((PROJECT / "templates" / "budgets.json").read_text(encoding="utf-8"))


class HostDispatchContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main_raw = MAIN.read_text(encoding="utf-8")
        cls.ref_raw = REF.read_text(encoding="utf-8")
        # Prose is hard-wrapped in the templates, so contracts match on the
        # sentence, not on where the renderer happened to break the line.
        cls.main = re.sub(r"\s+", " ", cls.main_raw)
        cls.ref = re.sub(r"\s+", " ", cls.ref_raw)

    # -- the reference exists, is disclosed on demand, and fits --------------

    def test_reference_is_generated_and_within_budget(self) -> None:
        self.assertTrue(REF.is_file(), "the Host procedure must ship as a reference")
        # a non-.tmpl reference would ship its {{TOKENS}} verbatim
        self.assertNotIn("{{", self.ref_raw)
        self.assertLessEqual(len(REF.read_bytes()), BUDGETS["reference_bytes"])
        self.assertLessEqual(len(MAIN.read_bytes()), BUDGETS["main_skill_bytes"])
        self.assertIn("references/zcode-host-dispatch.md", self.main,
                      "the main Skill must point at it conditionally")

    # -- the main Skill carries the action rules, not only the principle -----

    def test_main_skill_states_the_end_turn_rule(self) -> None:
        for fragment in (
            "KAOLA_ACP_HEARTBEAT_HOST",
            "heartbeat_host",
            "send --no-wait",
            "end the turn normally",
            ".kaola/heartbeat-prompt.json",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.main)
        # the prohibitions must be explicit, not implied
        rule = re.search(r"Never sleep, poll, blocking-`wait`[^.]*\.", self.main)
        self.assertIsNotNone(rule, "the main Skill must forbid sleep/poll/blocking wait")

    def test_main_skill_protects_a_waiting_host_from_idle_stop(self) -> None:
        self.assertIn("is not an idle worker", self.main)
        self.assertIn('send it no "continue"', self.main)

    # -- the reference is operational, with the real flags and fields --------

    def test_reference_distinguishes_the_three_identities(self) -> None:
        for fragment in ("Runner session", "ACP session id", "native session id",
                         "`sess_…` value is never a Runner session name"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.ref)

    def test_reference_binds_the_carrier_with_a_runnable_example(self) -> None:
        self.assertIn("KAOLA_ACP_HEARTBEAT_HOST='{\"platform\":\"zcode\"", self.ref)
        self.assertIn('"session":"zcode-kaola-host"', self.ref)
        self.assertIn("start --repo", self.ref)
        # the installed wrapper is platform-pinned: a platform argument in these
        # examples is a real error a live Host will hit (and did, on 2026-09-18)
        self.assertNotIn('"$W" codex ', self.ref)
        self.assertNotIn('"$ZC" zcode ', self.ref)
        self.assertIn("take **no** platform argument", self.ref)
        self.assertIn('"heartbeat_host"', self.ref)
        self.assertIn("No `heartbeat_host` key means this worker will never wake you",
                      self.ref)

    def test_reference_reads_the_dispatch_receipt_honestly(self) -> None:
        self.assertIn("--no-wait", self.ref)
        self.assertIn('"outcome": "in_progress"', self.ref)
        self.assertIn("not finished, and not correct", self.ref)
        self.assertIn("prompt-in-progress", self.ref)

    def test_reference_says_ending_the_turn_is_the_wait(self) -> None:
        self.assertIn("There is no \"wait mode\" command to call", self.ref)
        self.assertIn("Ending the turn *is* the wait", self.ref)
        self.assertIn("Do not `sleep`, poll in a loop", self.ref)
        self.assertIn("manufacture a wake-up", self.ref)

    def test_reference_reads_results_by_worker_identity_and_cursor(self) -> None:
        self.assertIn("kaola-host-notify/1", self.ref)
        self.assertIn('"event_cursor"', self.ref)
        self.assertIn("The notification is not the worker's reply", self.ref)
        self.assertIn("--since 19", self.ref)
        self.assertIn("observe --repo", self.ref)

    def test_reference_explains_the_carrier_semantics(self) -> None:
        for fragment in ("staged and delivered at your next turn boundary",
                         "never turned into steering",
                         "Duplicate `event_id`s collapse",
                         "redelivered at least once",
                         "never fabricates events"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.ref)

    def test_reference_keeps_turn_end_and_exit_as_equal_triggers(self) -> None:
        self.assertIn("`kind` is `idle` when the worker's turn ended and `terminated` when its "
                      "process exited", self.ref)
        self.assertIn("never kill a worker to be notified", self.ref)

    # -- the wording must still describe the real implementation -------------

    def test_documented_mechanics_match_the_scripts(self) -> None:
        holder = HOLDER.read_text(encoding="utf-8")
        acp = ACP.read_text(encoding="utf-8")
        self.assertIn('HEARTBEAT_HOST_ENV = "KAOLA_ACP_HEARTBEAT_HOST"', acp)
        self.assertIn('receipt["heartbeat_host"] = heartbeat_host', acp)
        self.assertIn('"kaola-host-notify/1', holder)
        self.assertIn('".kaola" / "heartbeat-prompt.json"', holder.replace('"', '"'))
        self.assertIn("<<<heartbeat-prompt", holder)
        # events only reach an idle host, through the ordinary prompt path
        self.assertIn('return {"delivered": False, "reason": "prompt-in-progress"}', holder)
        self.assertIn('WORKER_EVENT_KINDS = ("terminated", "idle")', holder)
        # and a worker event is never converted into a steer
        self.assertNotIn('op_steer(self._heartbeat', holder)


if __name__ == "__main__":
    unittest.main(verbosity=2)
