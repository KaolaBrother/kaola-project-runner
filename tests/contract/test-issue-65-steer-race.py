#!/usr/bin/env python3
"""Issue #65: turn attribution across the composite steer's cancel window.

These drive the REAL `Holder` in-process with a stubbed agent connection, so the
interleavings are arranged exactly rather than slept for: no production test
hook, nothing about test waiting shipped in the generated Skills.

The defect class: `self.turn` is REPLACED when a new prompt is admitted, so any
fact read from `self.turn` after the operation's own lock hold can already
belong to a different turn. Connections are served on separate threads and a
ZCode Host worker event starts prompts of its own, so turn A ending and turn B
taking over inside that window is ordinary, not exotic.
"""

from __future__ import annotations

import argparse
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HOLDER_PATH = PROJECT / "scripts" / "kaola-acp-holder.py"

spec = importlib.util.spec_from_file_location("kaola_acp_holder", HOLDER_PATH)
holder_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(holder_module)


class StubProc:
    pid = 4242


class StubAgent:
    """Just enough agent for admission, cancel and settlement."""

    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
        self.exit_code = None
        self.exit_signal = None
        self.stderr_pump = None
        self.malformed_lines = 0
        self.pending_out: dict[int, str] = {}
        self.sent: list[dict] = []
        self.next_id = 0
        self.on_cancel = None
        self.release_wait = threading.Event()

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(self.next_id)] = method
        self.sent.append({"method": method, "id": self.next_id, "params": params})
        return self.next_id

    def send_message(self, message: dict) -> None:
        self.sent.append(message)
        if message.get("method") == "session/cancel" and self.on_cancel is not None:
            self.on_cancel()

    def wait_response(self, request_id, timeout):
        # The holder's `_await_prompt` thread parks here; these tests settle
        # turns explicitly through `on_prompt_response`.
        self.release_wait.wait(timeout if timeout else 30)
        return None

    def prompts_sent(self) -> list[dict]:
        return [m for m in self.sent if m.get("method") == "session/prompt"]

    def cancels_sent(self) -> list[dict]:
        return [m for m in self.sent if m.get("method") == "session/cancel"]


class SteerRaceContract(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i65-race-")
        root = Path(self._tmp.name)
        args = argparse.Namespace(
            record_dir=str(root / "record"), socket=str(root / "h.sock"),
            platform="grok", session="race-session", repo=str(root),
            init_meta="", command="stub",
        )
        self.holder = holder_module.Holder(args)
        self.agent = StubAgent()
        self.holder.agent = self.agent
        self.holder.acp_session_id = "ses-race"
        self.holder.state = "ready"

    def tearDown(self) -> None:
        self.agent.release_wait.set()
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------------

    def start_turn(self, text: str) -> tuple[dict, dict]:
        receipt = self.holder.op_prompt({"text": text, "wait": False})
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)
        return receipt, self.holder.turn

    def settle(self, request_id, stop_reason: str = "end_turn") -> None:
        self.holder.on_prompt_response(request_id, {"result": {"stopReason": stop_reason}})

    # -- the send's id is its own --------------------------------------------

    def test_a_send_reports_the_request_id_from_its_own_admission(self) -> None:
        """Nothing downstream should have to ask `self.turn` who it just was."""
        first, _turn = self.start_turn("A")
        self.assertIsNotNone(first.get("turn_request_id"))
        self.settle(first["turn_request_id"])
        second, _ = self.start_turn("B")
        # the earlier receipt still names its own turn, and B is a different one
        self.assertNotEqual(first["turn_request_id"], second["turn_request_id"])
        self.assertEqual(self.holder.turn["request_id"], second["turn_request_id"])

    def test_a_late_answer_cannot_settle_the_turn_running_now(self) -> None:
        first, turn_a = self.start_turn("A")
        self.settle(first["turn_request_id"], "cancelled")
        second, turn_b = self.start_turn("B")
        # A's answer arriving late must not end B
        self.holder.on_prompt_response(first["turn_request_id"],
                                       {"result": {"stopReason": "end_turn"}})
        self.assertTrue(turn_b["active"], "B must still be running")
        self.assertEqual(self.holder.turn["request_id"], second["turn_request_id"])

    # -- cancel: receipt belongs to the turn it cancelled --------------------

    def test_cancel_receipt_describes_its_own_turn_when_another_takes_over(self) -> None:
        """A ends and B takes over while the cancel is in flight."""
        first, turn_a = self.start_turn("A")
        outcome: dict = {}

        def swap_turns() -> None:
            # Runs once `session/cancel` has gone out. Holding `turn_cond` keeps
            # the cancelling thread out until B is the current turn, which is the
            # interleaving that used to produce B's receipt under A's name.
            with self.holder.turn_cond:
                self.settle(first["turn_request_id"], "cancelled")
                self.start_turn("B")

        def run_cancel() -> None:
            receipt, sent, snapshot = self.holder.cancel_turn(turn_a, 5)
            outcome.update({"receipt": receipt, "sent": sent, "snapshot": snapshot})

        self.agent.on_cancel = lambda: threading.Thread(target=swap_turns).start()
        worker = threading.Thread(target=run_cancel)
        worker.start()
        worker.join(20)
        self.assertFalse(worker.is_alive(), "cancel_turn never returned")

        receipt, snapshot = outcome["receipt"], outcome["snapshot"]
        self.assertTrue(outcome["sent"])
        # A's own terminal facts, not B's
        self.assertEqual(snapshot["request_id"], first["turn_request_id"])
        self.assertEqual(snapshot["stop_reason"], "cancelled")
        self.assertFalse(snapshot["active"])
        self.assertFalse(snapshot["is_current"], "B is the current turn by now")
        self.assertEqual(receipt.get("stop_reason"), "cancelled")
        self.assertEqual(receipt.get("outcome"), "turn_canceled")
        # exactly one cancel went out, and B was never prompted away
        self.assertEqual(len(self.agent.cancels_sent()), 1)
        self.assertTrue(self.holder.turn["active"], "B must still be running")

    def test_cancel_bound_to_a_replaced_turn_sends_nothing(self) -> None:
        first, turn_a = self.start_turn("A")
        self.settle(first["turn_request_id"], "cancelled")
        second, _turn_b = self.start_turn("B")
        receipt, sent, snapshot = self.holder.cancel_turn(turn_a, 5)
        self.assertEqual(receipt.get("outcome"), "turn-changed")
        self.assertFalse(sent)
        self.assertFalse(receipt.get("cancel_sent"))
        self.assertEqual(receipt.get("request_id"), second["turn_request_id"])
        self.assertEqual(self.agent.cancels_sent(), [])
        self.assertTrue(self.holder.turn["active"], "B must be untouched")

    # -- the composite -------------------------------------------------------

    def test_composite_reports_the_turn_it_targeted_when_b_takes_over(self) -> None:
        """A stops because of us, but B owns the session before we can send."""
        first, _turn_a = self.start_turn("A")

        def swap_turns() -> None:
            with self.holder.turn_cond:
                self.settle(first["turn_request_id"], "cancelled")
                self.start_turn("B")

        self.agent.on_cancel = lambda: threading.Thread(target=swap_turns).start()
        receipt = self.holder.op_steer_interrupt(
            {"text": "stop and do X instead", "cancel_timeout": 5})

        self.assertEqual(receipt.get("error", {}).get("code"), "steer-turn-changed")
        self.assertEqual(receipt.get("steer_outcome"), "unknown")
        self.assertIsNone(receipt.get("steer_consumed"))
        self.assertIsNone(receipt.get("new_turn_request_id"))
        # A's facts, reported as A's
        self.assertEqual(receipt.get("cancelled_turn_request_id"), first["turn_request_id"])
        self.assertEqual(receipt.get("cancelled_turn_stop_reason"), "cancelled")
        # the cancel really did go out, and the receipt says so
        self.assertIs(receipt.get("cancel_sent"), True)
        self.assertIs(receipt.get("side_effects_possible"), True)
        # exactly one prompt was ever written: A's. The steering text was not.
        self.assertEqual(len(self.agent.prompts_sent()), 2, "A and B only")
        self.assertTrue(self.holder.turn["active"], "B must still be running")

    def test_composite_new_turn_id_is_its_own_send(self) -> None:
        """The ordinary success path still attributes the new turn correctly."""
        first, _turn_a = self.start_turn("A")
        self.agent.on_cancel = lambda: self.settle(first["turn_request_id"], "cancelled")
        receipt = self.holder.op_steer_interrupt(
            {"text": "stop and do X instead", "cancel_timeout": 5})
        self.assertEqual(receipt.get("steer_outcome"), "interrupted_and_resent")
        self.assertIs(receipt.get("cancel_sent"), True)
        self.assertEqual(receipt.get("cancelled_turn_request_id"), first["turn_request_id"])
        self.assertEqual(receipt.get("cancelled_turn_stop_reason"), "cancelled")
        new_id = receipt.get("new_turn_request_id")
        self.assertIsNotNone(new_id)
        self.assertNotEqual(new_id, first["turn_request_id"])
        # it is the id this send was admitted with, and it is the running turn
        self.assertEqual(self.holder.turn["request_id"], new_id)
        self.assertEqual(self.agent.prompts_sent()[-1]["id"], new_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
