#!/usr/bin/env python3
"""Issue #65: the ZCode Host post-dispatch event-wait contract, as generated.

The delivery here is instruction an Agent can act on without reading Python:
the outer Agent must hand the Host its real Runner identity and keep the Host
while workers are in flight; a worker `start` run from the Host binds itself
(Issue #104, `KAOLA_ACP_HEARTBEAT_HOST` derived from the holder's dispatcher
fact) and the Host reads the receipt's binding fact, dispatches non-blocking,
updates the one heartbeat prompt, then ends the turn naturally instead of
sleeping or polling;
and after an event it must read the worker's real reply through that worker's
own Skill. These contracts pin that wording into the generated surface, so a
template edit cannot quietly drop it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
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
ACP_CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"


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

    def test_reference_starts_the_worker_from_the_host_with_a_runnable_example(self) -> None:
        # Issue #104: the binding is mechanical; the reference shows the start
        # without the variable and the receipt that proves the source.
        self.assertNotIn("KAOLA_ACP_HEARTBEAT_HOST='{", self.ref)
        self.assertIn('"heartbeat_host_source": "dispatcher"', self.ref)
        self.assertIn('"session":"zcode-kaola-host"', self.ref)
        self.assertIn("start --repo", self.ref)
        # Issue #130: the Host-only PTY refusal is absorbed by the universal one.
        self.assertIn("transport-pty-retired", self.ref)
        self.assertNotIn("heartbeat-host-pty-unsupported", self.ref)
        # the installed wrapper is platform-pinned: a platform argument in these
        # examples is a real error a live Host will hit (and did, on 2026-09-18)
        self.assertNotIn('"$W" codex ', self.ref)
        self.assertNotIn('"$ZC" zcode ', self.ref)
        self.assertIn("take **no** platform argument", self.ref)
        self.assertIn('"heartbeat_host"', self.ref)
        # Issue #70 superseded "a missing key means unbound": the key is always
        # present, so the reference must teach the fact and its unknown case.
        self.assertIn("`heartbeat_host` is the running holder's own binding", self.ref)
        self.assertIn("heartbeat_host_known", self.ref)

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
        self.assertIn("observe --repo", self.ref)
        # the anchor must precede the output; the turn-end cursor never does
        self.assertIn('--since "$DISPATCH_EVENT_CURSOR"', self.ref)

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
        # Issue #70: the start receipt separates what was asked for from the
        # binding the holder really adopted, which is read back from its state.
        self.assertIn('receipt["heartbeat_host_requested"] = heartbeat_host', acp)
        self.assertIn('receipt["heartbeat_host_source"] = resolution["source"]', acp)
        self.assertIn("attach_binding_fact(receipt, state)", acp)
        self.assertIn('"kaola-host-notify/1', holder)
        self.assertIn('".kaola" / "heartbeat-prompt.json"', holder.replace('"', '"'))
        self.assertIn("<<<heartbeat-prompt", holder)
        # events only reach an idle host, through the ordinary prompt path
        self.assertIn('return {"delivered": False, "reason": "prompt-in-progress"}', holder)
        self.assertIn('WORKER_EVENT_KINDS = ("terminated", "idle", "permission_required")',
                      holder)
        # and a worker event is never converted into a steer
        self.assertNotIn('op_steer(self._heartbeat', holder)


class CursorAnchorBehaviour(unittest.TestCase):
    """Issue #65 round 2: the cursor a Host must read a reply from.

    A worker event carries the cursor at TURN END, which is *after* the reply.
    `capture --since <event_cursor>` therefore skips the very reply being
    accepted. This runs a real holder against the mock agent and proves both
    halves: the turn-end cursor loses the reply, and the dispatch receipt's
    `dispatch_event_cursor` keeps it.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i65-cursor-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"s-i65-cursor-{os.getpid()}"
        self._started = False

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=25)

    def cli(self, command: str, *args: str, check: bool = True, timeout: float = 45) -> dict:
        argv = [sys.executable, str(ACP_CLI), "grok", command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", " ".join([sys.executable, str(MOCK), "--scenario", "normal"]),
                *args]
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)
        receipt = json.loads(result.stdout)
        if check and "error" in receipt:
            self.fail(f"{command} failed: {receipt['error']}")
        return receipt

    @staticmethod
    def assistant_text(capture: dict) -> str:
        """Every assistant chunk the capture receipt carries, in one string."""
        blob = json.dumps(capture, ensure_ascii=False)
        return blob

    def test_turn_end_cursor_loses_the_reply_and_dispatch_cursor_keeps_it(self) -> None:
        self.cli("start")
        self._started = True
        dispatched = self.cli("send", "--no-wait", "--text", "say the codeword")
        self.assertEqual(dispatched["outcome"], "in_progress")
        # the anchor a Host must keep, and the fingerprint that identifies the turn
        self.assertIn("dispatch_event_cursor", dispatched)
        dispatch_cursor = dispatched["dispatch_event_cursor"]
        fingerprint = dispatched["prompt_fingerprint"]
        self.assertIsInstance(dispatch_cursor, int)

        done = self.cli("wait", "--timeout", "30")
        self.assertEqual(done.get("outcome"), "turn_completed")
        reply = done.get("final_text") or ""
        self.assertIn("MOCK-REPLY", reply)

        state = self.cli("observe")
        # what a worker event would carry: the cursor at turn end
        turn_end_cursor = state["event_cursor"]
        self.assertGreater(turn_end_cursor, dispatch_cursor)
        self.assertEqual((state.get("last_prompt") or {}).get("fingerprint"), fingerprint)

        from_turn_end = self.cli("capture", "--since", str(turn_end_cursor))
        from_dispatch = self.cli("capture", "--since", str(dispatch_cursor))

        # the documented-correct anchor keeps the reply ...
        self.assertIn("MOCK-REPLY", self.assistant_text(from_dispatch),
                      "the dispatch cursor must still contain the reply")
        # ... and the turn-end cursor does not: that is the defect the Host
        # guidance must never reproduce.
        self.assertNotIn("MOCK-REPLY", self.assistant_text(from_turn_end),
                         "a turn-end cursor cannot be used as a --since anchor")

        # the bounded fallback for a Host with no anchor still finds it
        recent = self.cli("capture", "--lines", "200")
        self.assertIn("MOCK-REPLY", self.assistant_text(recent))

    def test_reference_never_uses_the_event_cursor_as_a_since_anchor(self) -> None:
        ref = REF.read_text(encoding="utf-8")
        self.assertNotIn("--since 19", ref, "the event cursor is not a --since value")
        self.assertIn("DISPATCH_EVENT_CURSOR", ref)
        self.assertIn("--lines 200", ref, "a Host with no anchor needs the bounded fallback")
        flat = re.sub(r"\s+", " ", ref)
        self.assertIn("event_cursor` is the end of the turn, not the start", flat)
        self.assertIn("last_prompt.fingerprint", flat)


if __name__ == "__main__":
    unittest.main(verbosity=2)
