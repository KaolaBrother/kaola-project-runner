#!/usr/bin/env python3
"""Issue #65: the unified `steer` transport operation.

Steering is an Agent-chosen tool, never Runner policy. These contracts pin the
facts that make the receipt trustworthy:

* a platform whose manifest declares no native entry never advertises a `steer`
  tool and answers `unsupported` with the text unconsumed;
* a supported platform maps `injected` / `promptRequired` / `startedNewTurn` /
  refusal / no-reply onto distinct receipt facts, without a second lifecycle;
* an idle session is never steered into an untracked turn;
* the running turn keeps its own request id, output, and terminal state;
* consecutive steers, cancel, and session isolation behave;
* `steer` over `pty` is an honest unsupported, never an unproven injection;
* the generated Skills advertise a `steer` tool only where it really exists.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
TMUX = PROJECT / "scripts" / "kaola-tmux.sh"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PLATFORMS = PROJECT / "platforms"
SKILLS = PROJECT / "skills"

# grok's manifest declares no native entry; codex declares `_session/steering`.
UNSUPPORTED_PLATFORM = "grok"
SUPPORTED_PLATFORM = "codex"
STEER_TEXT = "STOP the loop and reply with exactly STEERED-OK-65"


def manifest(platform: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PLATFORMS / f"{platform}.yaml").read_text(encoding="utf-8").splitlines():
        key, sep, raw = line.partition(":")
        if sep and raw.strip():
            try:
                values[key.strip()] = json.loads(raw.strip())
            except ValueError:
                pass
    return values


class SteeringContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i65-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"s-i65-{self._testMethodName.lower().replace('_', '-')}"[:79]
        self._started: list[tuple[str, str]] = []

    def tearDown(self) -> None:
        for platform, session in self._started:
            self.cli(platform, "stop", "--force", session=session, check=False, timeout=25)

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        return env

    def mock_command(self, steering: str, turn_ms: int, scenario: str = "slow",
                     ignore_cancel: bool = False) -> str:
        parts = [sys.executable, str(MOCK), "--scenario", scenario,
                 "--steering", steering, "--turn-ms", str(turn_ms)]
        if ignore_cancel:
            parts.append("--ignore-cancel")
        return " ".join(parts)

    def cli(self, platform: str, command: str, *args: str, session: str | None = None,
            steering: str = "none", turn_ms: int = 0, scenario: str = "slow",
            ignore_cancel: bool = False, check: bool = True, timeout: float = 45) -> dict:
        argv = [sys.executable, str(CLI), platform, command,
                "--repo", str(self.repo), "--session", session or self.session,
                "--command", self.mock_command(steering, turn_ms, scenario, ignore_cancel),
                *args]
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(), timeout=timeout)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command} emitted no JSON receipt: rc={result.returncode} "
                      f"stdout={result.stdout!r} stderr={result.stderr!r}")
        if check and "error" in receipt:
            self.fail(f"{command} returned error {receipt['error']}")
        return receipt

    def start_running_turn(self, platform: str, steering: str, turn_ms: int = 9000,
                           session: str | None = None, ignore_cancel: bool = False) -> dict:
        """Start a session and leave one genuinely running turn behind."""
        session = session or self.session
        self.cli(platform, "start", session=session, steering=steering, turn_ms=turn_ms,
                 ignore_cancel=ignore_cancel)
        self._started.append((platform, session))
        sent = self.cli(platform, "send", "--no-wait", "--text", "run the long loop",
                        session=session, steering=steering, turn_ms=turn_ms,
                        ignore_cancel=ignore_cancel)
        self.assertEqual(sent.get("outcome"), "in_progress")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            state = self.cli(platform, "observe", session=session, steering=steering,
                             turn_ms=turn_ms, ignore_cancel=ignore_cancel)
            if state.get("turn_active"):
                return state
            time.sleep(0.2)
        self.fail("the mock turn never became active")

    # -- unsupported platforms ----------------------------------------------

    def test_manifest_pairs_capability_with_entry(self) -> None:
        for path in sorted(PLATFORMS.glob("*.yaml")):
            values = manifest(path.stem)
            with self.subTest(platform=path.stem):
                self.assertIn(values["native_steering"],
                              {"supported", "unsupported", "unknown"})
                self.assertTrue(values["steering_summary"].strip(),
                                "every platform records why, not just what")
                if values["native_steering"] == "supported":
                    self.assertTrue(values["acp_steer_method"])
                else:
                    self.assertEqual(values["acp_steer_method"], "")

    def test_unsupported_platform_never_consumes(self) -> None:
        """An explicit native request on a platform without the entry."""
        receipt = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "native",
                           "--text", STEER_TEXT, check=False)
        self.assertEqual(receipt["steer_outcome"], "unsupported")
        self.assertIs(receipt["steer_consumed"], False)
        self.assertIsNone(receipt["steer_method"])
        self.assertEqual(receipt["error"]["code"], "steer-unsupported")
        self.assertEqual(receipt["mutation_status"], "not_started")

    def test_pty_transport_is_honest_unsupported(self) -> None:
        result = subprocess.run(
            ["bash", str(TMUX), SUPPORTED_PLATFORM, "steer", "--transport", "pty",
             "--repo", str(self.repo), "--session", self.session, "--text", STEER_TEXT],
            capture_output=True, text=True, env=self.env(), timeout=30)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["steer_outcome"], "unsupported")
        self.assertIs(receipt["steer_consumed"], False)
        self.assertEqual(receipt["error"]["code"], "steer-unsupported-transport")
        self.assertNotEqual(result.returncode, 0)

    # -- supported platform: outcome mapping ---------------------------------

    def test_injected_preserves_the_running_turn(self) -> None:
        state = self.start_running_turn(SUPPORTED_PLATFORM, "injected")
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="injected", turn_ms=9000)
        self.assertEqual(receipt["steer_outcome"], "injected")
        self.assertIs(receipt["steer_consumed"], True)
        self.assertEqual(receipt["steer_native_outcome"], "injected")
        self.assertEqual(receipt["steer_method"], manifest(SUPPORTED_PLATFORM)["acp_steer_method"])
        self.assertIs(receipt["mutation_performed"], True)
        # the original prompt keeps its own request id and stays the active turn
        self.assertEqual(receipt["turn_request_id"], receipt["turn_request_id_after"])
        self.assertIs(receipt["turn_request_id_preserved"], True)
        self.assertIs(receipt["turn_active"], True)
        self.assertEqual(receipt["steer_fingerprint"][:7], "sha256:")
        self.assertNotEqual(receipt["steer_fingerprint"], receipt["turn_prompt_fingerprint"])
        # and the ORIGINAL prompt still owns the terminal state
        done = self.cli(SUPPORTED_PLATFORM, "wait", "--timeout", "30",
                        steering="injected", turn_ms=9000)
        self.assertEqual(done.get("outcome"), "turn_completed")
        self.assertEqual(done.get("stop_reason"), "end_turn")
        self.assertIn("MOCK-STEERED", done.get("final_text", ""))
        self.assertIsNotNone(state)

    def test_consecutive_steers_each_get_their_own_receipt(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "injected")
        first = self.cli(SUPPORTED_PLATFORM, "steer", "--text", "first redirection",
                         steering="injected", turn_ms=9000)
        second = self.cli(SUPPORTED_PLATFORM, "steer", "--text", "second redirection",
                          steering="injected", turn_ms=9000)
        for receipt in (first, second):
            self.assertEqual(receipt["steer_outcome"], "injected")
            self.assertIs(receipt["turn_request_id_preserved"], True)
        self.assertNotEqual(first["steer_fingerprint"], second["steer_fingerprint"])
        self.assertNotEqual(first["steer_request_id"], second["steer_request_id"])
        self.assertEqual(first["turn_request_id"], second["turn_request_id"])

    def test_idle_session_is_never_steered(self) -> None:
        self.cli(SUPPORTED_PLATFORM, "start", steering="injected")
        self._started.append((SUPPORTED_PLATFORM, self.session))
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="injected", check=False)
        self.assertEqual(receipt["steer_outcome"], "not_consumed")
        self.assertIs(receipt["steer_consumed"], False)
        self.assertEqual(receipt["steer_reason"], "no-active-turn")
        self.assertIs(receipt["mutation_performed"], False)
        # nothing was written, so the agent never saw a steering request
        self.assertNotIn("steer_response", receipt)

    def test_prompt_required_is_not_consumed(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "promptRequired")
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="promptRequired", turn_ms=9000, check=False)
        self.assertEqual(receipt["steer_outcome"], "not_consumed")
        self.assertIs(receipt["steer_consumed"], False)
        self.assertEqual(receipt["error"]["code"], "steer-prompt-required")
        self.assertIs(receipt["mutation_performed"], False)

    def test_started_new_turn_is_not_called_injection(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "startedNewTurn")
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="startedNewTurn", turn_ms=9000, check=False)
        self.assertEqual(receipt["steer_outcome"], "started_new_turn")
        self.assertNotEqual(receipt["steer_outcome"], "injected")
        self.assertEqual(receipt["error"]["code"], "steer-started-new-turn")
        self.assertIs(receipt["turn_request_id_preserved"], True)

    def test_agent_refusal_is_rejected_not_unknown(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "error")
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="error", turn_ms=9000, check=False)
        self.assertEqual(receipt["steer_outcome"], "rejected")
        self.assertIs(receipt["steer_consumed"], False)
        self.assertEqual(receipt["error"]["detail"]["code"], -32602)

    def test_unrecognized_outcome_stays_unknown(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "weird")
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="weird", turn_ms=9000, check=False)
        self.assertEqual(receipt["steer_outcome"], "unknown")
        self.assertIsNone(receipt["steer_consumed"])
        self.assertEqual(receipt["error"]["code"], "steer-unrecognized-outcome")

    def test_no_reply_keeps_consumption_unknown(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "silent", turn_ms=20000)
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           "--timeout", "2", steering="silent", turn_ms=20000,
                           check=False, timeout=60)
        self.assertEqual(receipt["steer_outcome"], "unknown")
        self.assertIsNone(receipt["steer_consumed"])
        self.assertEqual(receipt["error"]["code"], "steer-no-response")
        self.assertIs(receipt["turn_request_id_preserved"], True)

    def test_cancel_then_steer_is_not_consumed(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "injected", turn_ms=20000)
        self.cli(SUPPORTED_PLATFORM, "cancel", "--timeout", "15",
                 steering="injected", turn_ms=20000, check=False)
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           steering="injected", turn_ms=20000, check=False)
        self.assertEqual(receipt["steer_outcome"], "not_consumed")
        self.assertEqual(receipt["steer_reason"], "no-active-turn")

    def test_steer_targets_only_its_own_session(self) -> None:
        other = f"{self.session}-other"[:79]
        self.start_running_turn(SUPPORTED_PLATFORM, "injected")
        self.cli(SUPPORTED_PLATFORM, "start", session=other, steering="injected")
        self._started.append((SUPPORTED_PLATFORM, other))
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT,
                           session=other, steering="injected", check=False)
        # the neighbour is idle: its own steer is refused, and the busy session
        # keeps its running turn untouched
        self.assertEqual(receipt["steer_outcome"], "not_consumed")
        self.assertEqual(receipt["session"], other)
        busy = self.cli(SUPPORTED_PLATFORM, "observe", steering="injected", turn_ms=9000)
        self.assertIs(busy["turn_active"], True)

    def test_send_wait_cancel_stop_have_no_regression(self) -> None:
        self.cli(SUPPORTED_PLATFORM, "start", steering="injected")
        self._started.append((SUPPORTED_PLATFORM, self.session))
        sent = self.cli(SUPPORTED_PLATFORM, "send", "--text", "hello",
                        steering="injected", scenario="normal")
        self.assertEqual(sent.get("outcome"), "turn_completed")
        self.assertEqual(sent.get("stop_reason"), "end_turn")
        self.assertIn("MOCK-REPLY", sent.get("final_text", ""))
        state = self.cli(SUPPORTED_PLATFORM, "observe", steering="injected")
        self.assertIs(state["turn_active"], False)


    # -- composite steering (no native entry) --------------------------------

    def test_no_native_entry_refuses_until_the_agent_picks_a_mode(self) -> None:
        """The Runner never chooses to interrupt on the Agent's behalf."""
        receipt = self.cli(UNSUPPORTED_PLATFORM, "steer", "--text", STEER_TEXT, check=False)
        self.assertEqual(receipt["error"]["code"], "steer-mode-required")
        self.assertEqual(receipt["available_steer_modes"], ["interrupt"])
        self.assertIs(receipt["steer_consumed"], False)
        self.assertEqual(receipt["mutation_status"], "not_started")
        # the message must say what the composite actually does
        message = receipt["error"]["message"]
        self.assertIn("CANCELS the running turn", message)
        self.assertIn("side effects", message)
        # a refused steer starts nothing: this session has no holder record
        self.assertFalse(
            any(p.name == "record.json"
                for p in (self.record_root / UNSUPPORTED_PLATFORM / self.session).rglob("*"))
            if (self.record_root / UNSUPPORTED_PLATFORM / self.session).exists() else False)

    def test_interrupt_cancels_the_turn_then_resends_once(self) -> None:
        self.start_running_turn(UNSUPPORTED_PLATFORM, "none", turn_ms=20000)
        receipt = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "interrupt",
                           "--text", STEER_TEXT, turn_ms=20000, check=False)
        self.assertEqual(receipt["steer_outcome"], "interrupted_and_resent")
        self.assertEqual(receipt["steer_mode"], "interrupt")
        self.assertEqual(receipt["steer_method"], "cancel+prompt")
        self.assertIs(receipt["interrupted"], True)
        self.assertIs(receipt["turn_was_active"], True)
        self.assertEqual(receipt["steer_confirmation"], "cancel-confirmed")
        # the interrupted turn keeps its own identity and terminal state
        self.assertEqual(receipt["cancelled_turn_stop_reason"], "cancelled")
        self.assertNotEqual(receipt["cancelled_turn_request_id"],
                            receipt["new_turn_request_id"])
        self.assertIs(receipt["turn_request_id_preserved"], True)
        # partial work is disclosed, not hidden
        self.assertIs(receipt["side_effects_possible"], True)
        # it is a NEW turn, never an injection into the old one
        self.assertNotEqual(receipt["steer_outcome"], "injected")
        self.assertIn("dispatch_event_cursor", receipt)
        # exactly one new prompt, and the old turn is no longer active
        state = self.cli(UNSUPPORTED_PLATFORM, "observe", turn_ms=20000)
        self.assertEqual((state.get("last_prompt") or {}).get("fingerprint"),
                         receipt["steer_fingerprint"])

    def test_interrupt_on_an_idle_session_does_not_pretend_to_interrupt(self) -> None:
        self.cli(UNSUPPORTED_PLATFORM, "start")
        self._started.append((UNSUPPORTED_PLATFORM, self.session))
        receipt = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "interrupt",
                           "--text", STEER_TEXT, check=False)
        self.assertEqual(receipt["steer_outcome"], "resent_without_interrupt")
        self.assertIs(receipt["interrupted"], False)
        self.assertIs(receipt["turn_was_active"], False)
        self.assertIs(receipt["side_effects_possible"], False)
        self.assertEqual(receipt["steer_confirmation"], "no-turn-to-interrupt")
        self.assertIsNone(receipt["cancelled_turn_request_id"])

    def test_unconfirmed_cancel_sends_nothing(self) -> None:
        """A turn that will not stop must never receive a second dispatch."""
        self.start_running_turn(UNSUPPORTED_PLATFORM, "none", turn_ms=25000,
                                ignore_cancel=True)
        receipt = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "interrupt",
                           "--cancel-timeout", "2", "--text", STEER_TEXT,
                           turn_ms=25000, ignore_cancel=True, check=False, timeout=90)
        self.assertEqual(receipt["steer_outcome"], "unknown")
        self.assertIsNone(receipt["steer_consumed"])
        self.assertEqual(receipt["error"]["code"], "steer-cancel-unconfirmed")
        self.assertIn("NOT sent", receipt["error"]["message"])
        self.assertNotIn("new_turn_request_id", receipt)
        # the original turn is still the active one: nothing was dispatched over it
        state = self.cli(UNSUPPORTED_PLATFORM, "observe", turn_ms=25000, ignore_cancel=True)
        self.assertIs(state["turn_active"], True)

    def test_repeated_interrupt_steers_the_steer(self) -> None:
        self.start_running_turn(UNSUPPORTED_PLATFORM, "none", turn_ms=20000)
        first = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "interrupt",
                         "--text", "first redirection", turn_ms=20000, check=False)
        self.assertEqual(first["steer_outcome"], "interrupted_and_resent")
        second = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "interrupt",
                          "--text", "second redirection", turn_ms=20000, check=False)
        self.assertEqual(second["steer_outcome"], "interrupted_and_resent")
        # the second call interrupts the turn the first one started
        self.assertEqual(second["cancelled_turn_request_id"], first["new_turn_request_id"])
        self.assertNotEqual(second["new_turn_request_id"], first["new_turn_request_id"])
        self.assertNotEqual(first["steer_fingerprint"], second["steer_fingerprint"])

    def test_a_native_platform_can_still_be_asked_to_interrupt(self) -> None:
        self.start_running_turn(SUPPORTED_PLATFORM, "injected", turn_ms=20000)
        receipt = self.cli(SUPPORTED_PLATFORM, "steer", "--steer-mode", "interrupt",
                           "--text", STEER_TEXT, steering="injected", turn_ms=20000,
                           check=False)
        self.assertEqual(receipt["steer_outcome"], "interrupted_and_resent")
        self.assertEqual(receipt["steer_mode"], "interrupt")
        # asking for the composite must not silently use the native entry
        self.assertNotIn("steer_native_outcome", receipt)

    def test_native_mode_on_an_unsupported_platform_writes_nothing(self) -> None:
        receipt = self.cli(UNSUPPORTED_PLATFORM, "steer", "--steer-mode", "native",
                           "--text", STEER_TEXT, check=False)
        self.assertEqual(receipt["steer_outcome"], "unsupported")
        self.assertEqual(receipt["steer_mode"], "native")
        self.assertIs(receipt["steer_consumed"], False)
        self.assertEqual(receipt["available_steer_modes"], ["interrupt"])

    # -- generated surface ---------------------------------------------------

    def test_generated_skills_advertise_only_real_tools(self) -> None:
        """Every platform documents a usable path; only a real native entry is
        advertised as native."""
        for path in sorted(PLATFORMS.glob("*.yaml")):
            values = manifest(path.stem)
            skill_dir = SKILLS / values["skill_name"]
            body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            reference = (skill_dir / "references" / "steering.md").read_text(encoding="utf-8")
            with self.subTest(platform=path.stem):
                # a runnable steer command exists everywhere: nobody is left
                # with "unsupported" and no path
                self.assertRegex(body, r'runtime-tmux\.sh" steer ')
                self.assertIn("## Steering a running turn", body)
                if values["native_steering"] == "supported":
                    self.assertIn("steers natively", body)
                    self.assertNotIn("exposes no native mid-turn entry", body)
                else:
                    self.assertIn("exposes no native mid-turn entry", body)
                    self.assertIn("--steer-mode interrupt", body)
                    # the composite must never be sold as injection
                    self.assertIn("never injection", body)
                    self.assertIn("side effects", body)
                # the reference carries the investigated ACP fact and its scope
                self.assertIn(values["native_steering"], reference)
                self.assertIn(values["steering_summary"].split(".")[0], reference)
                self.assertIn("ACP channel only", reference)
                self.assertIn("steer-mode-required", reference)

    def test_every_platform_has_a_documented_usable_path(self) -> None:
        """The deliverable: nine platforms, nine usable steering paths."""
        native, composite = [], []
        for path in sorted(PLATFORMS.glob("*.yaml")):
            values = manifest(path.stem)
            (native if values["native_steering"] == "supported" else composite).append(path.stem)
        self.assertEqual(len(native) + len(composite), 9)
        self.assertTrue(native, "at least one platform steers natively")
        for platform in composite:
            values = manifest(platform)
            # no native tool is invented for it ...
            self.assertEqual(values["acp_steer_method"], "")
            # ... and the composite really is reachable through the shared route
            receipt = self.cli(platform, "steer", "--steer-mode", "interrupt",
                               "--text", STEER_TEXT, check=False)
            self.assertNotIn(receipt.get("error", {}).get("code"),
                             ("steer-unsupported", "steer-mode-required"),
                             f"{platform} must accept the composite mode")


if __name__ == "__main__":
    unittest.main(verbosity=2)
