#!/usr/bin/env python3
"""Issue #380: a client message id makes send/steer replayable after a lost receipt.

The reproduced defect: two identical `send` calls in one idle window admit two
turns; the second receipt only carries `duplicate_warning`, and `view` has no
client-supplied identity on either user row. This suite pins the minimum
admission ledger:

* the same id + same op + same text + same ACP session replays the original
  admission receipt (``idempotent_replay``, ``replay_of_turn_request_id``, the
  original ``dispatch_event_cursor`` and ``holder_instance_id``) and creates no
  second user row or turn;
* the same id with a different op/text/session is a clean conflict;
* only a successful write is registered - a clean no-write (idle steer,
  unsupported holder) stays retryable;
* the ledger keeps 64 entries FIFO, so the 65th admission evicts the oldest id;
* a restart cannot replay, and the last prompt's own id/text is refused as
  ``client-message-id-restart-unknown`` instead of being admitted again;
* no id keeps the old receipts/view shape, including the duplicate-turn
  behaviour and ``duplicate_warning``;
* an old live holder is refused before the wire with the idle drain-restart
  route;
* the id is validated in the holder (non-empty, <=200 UTF-8 bytes, no C0/C1
  controls), and only send/steer accept the CLI flag;
* the #379 mutation wrapper does not flatten a replayed unknown steer to false;
* ``op_steer`` / ``op_steer_interrupt`` reject a foreign expected holder at
  entry, the CLI steer forwards only an explicit binding, and the composite
  follow-up prompt carries the holder identity.

Run: python3 tests/contract/test-issue-380-client-message-id.py -v
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "kaola-acp.py"
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class ClientMessageIdCase(unittest.TestCase):
    """Real CLI + real holder + mock ACP agent, one temp project per test."""

    platform = "grok"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i380-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "kpr380@example.invalid"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "kpr380"],
                       cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("kpr380\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.repo, check=True)
        self.project = os.path.realpath(str(self.repo))
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session = (f"{self.platform}-w380-"
                        f"{self._testMethodName.replace('_', '-')[:40]}")
        self.mock_log = self.root / "mock-events.jsonl"
        self.started = False
        self.extra: list[subprocess.Popen] = []

    def tearDown(self) -> None:
        if self.started:
            self.cli("stop", "--force", check=False, timeout=30)
        for proc in self.extra:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
        last_error: OSError | None = None
        for _ in range(25):
            try:
                self.tmp.cleanup()
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.2)
        if last_error is not None:
            raise last_error

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["HOME"] = str(self.home)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        return env

    def mock_command(self, scenario: str = "normal", *args: str) -> str:
        return " ".join([sys.executable, str(MOCK), "--scenario", scenario, *args])

    def argv(self, command: str, *args: str, scenario: str = "normal",
             mock_args: tuple[str, ...] = (), platform: str | None = None
             ) -> list[str]:
        return [
            sys.executable, str(CLI), platform or self.platform, command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(scenario, *mock_args), *args,
        ]

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 60, scenario: str = "normal",
            mock_args: tuple[str, ...] = (), platform: str | None = None
            ) -> tuple[int, dict]:
        argv = self.argv(command, *args, scenario=scenario,
                         mock_args=mock_args, platform=platform)
        proc = subprocess.run(argv, capture_output=True, text=True,
                              env=self.env(), timeout=timeout)
        try:
            receipt = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command} not JSON: {proc.stdout!r} "
                      f"stderr={proc.stderr!r}")
        if check:
            self.assertNotIn("error", receipt,
                             f"{command} failed: {receipt.get('error')}")
            self.assertNotEqual(receipt.get("result"), "refused",
                                f"{command} refused: {receipt}")
        return proc.returncode, receipt

    def start(self, scenario: str = "normal", *args: str,
              mock_args: tuple[str, ...] = (), platform: str | None = None) -> dict:
        _, receipt = self.cli("start", *args, scenario=scenario,
                              mock_args=mock_args, platform=platform)
        self.started = True
        return receipt

    def record_path(self) -> Path:
        digest = hashlib.sha256(self.project.encode("utf-8")).hexdigest()[:16]
        return (self.record_root / self.platform / self.session / digest
                / "record.json")

    def read_record(self) -> dict:
        return json.loads(self.record_path().read_text(encoding="utf-8"))

    def write_record(self, record: dict) -> None:
        self.record_path().write_text(
            json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    def view(self) -> dict:
        _, receipt = self.cli("view")
        return receipt

    def user_rows(self, view: dict) -> list[dict]:
        return [row for row in view.get("messages") or []
                if row.get("role") == "user"]

    def wait_idle(self, timeout: float = 20) -> dict:
        def done():
            view = self.view()
            turns = view.get("turns") or []
            if turns and turns[-1].get("ended_at") is not None:
                return view
            return None
        return wait_for(done, timeout, "turn to settle")

    def holder_id(self) -> str:
        return self.read_record()["holder_instance_id"]

    def dead_holder(self) -> subprocess.Popen:
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"])
        self.extra.append(proc)
        return proc

    # -- CLI surface ---------------------------------------------------------

    def test_only_send_and_steer_accept_the_flag(self) -> None:
        self.start()
        for command, args in (("view", ()), ("status", ()),
                              ("capture", ("--lines", "10"))):
            rc, receipt = self.cli(command, *args, "--client-message-id", "x",
                                   check=False)
            self.assertEqual(rc, 1, receipt)
            self.assertEqual(receipt.get("reason"), "invalid-input")
            self.assertEqual(receipt["error"]["code"], "invalid-input")
            self.assertIs(receipt["mutation_performed"], False)
            self.assertEqual(receipt["mutation_status"], "not_started")

    # -- replay and conflict -------------------------------------------------

    def test_same_id_and_text_replays_without_a_second_turn(self) -> None:
        self.start()
        text = "same text after a lost receipt"
        _, first = self.cli("send", "--text", text, "--no-wait",
                            "--client-message-id", "m-1")
        self.assertEqual(first["outcome"], "in_progress")
        self.assertEqual(first["client_message_id"], "m-1")
        self.assertIs(first["mutation_performed"], True)
        first_turn = first["turn_request_id"]
        first_cursor = first["dispatch_event_cursor"]
        holder = self.holder_id()

        # The receipt can be lost while the turn is still active. The resend
        # must replay, not hit the busy refusal and not open a second turn.
        _, replay = self.cli("send", "--text", text, "--no-wait",
                             "--client-message-id", "m-1")
        self.assertIs(replay.get("idempotent_replay"), True)
        self.assertEqual(replay["replay_of_turn_request_id"], first_turn)
        self.assertEqual(replay["dispatch_event_cursor"], first_cursor)
        self.assertEqual(replay["holder_instance_id"], holder)
        self.assertEqual(replay["client_message_id"], "m-1")
        self.assertIs(replay["mutation_performed"], True)
        self.assertNotIn("error", replay)

        view = self.view()
        rows = self.user_rows(view)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["clientMessageId"], "m-1")
        self.assertEqual(len(view.get("turns") or []), 1)
        self.assertEqual(view["turns"][0]["clientMessageId"], "m-1")
        self.assertEqual(view["turns"][0]["start_cursor"], first_cursor)

        view = self.wait_idle()
        self.assertEqual(len(self.user_rows(view)), 1)
        self.assertEqual(len(view.get("turns") or []), 1)
        self.assertEqual(self.read_record()["last_prompt"]["client_message_id"],
                         "m-1")

        # A completed send's lost receipt is still the same admission: the
        # replay describes the original write, not the turn's later state.
        _, after = self.cli("send", "--text", text, "--wait", "--timeout", "20",
                            "--client-message-id", "m-1")
        self.assertIs(after.get("idempotent_replay"), True)
        self.assertEqual(after["dispatch_event_cursor"], first_cursor)
        self.assertIs(after["mutation_performed"], True)
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 1)
        self.assertEqual(len(view.get("turns") or []), 1)

    def test_same_id_different_text_or_op_conflicts(self) -> None:
        self.start()
        _, first = self.cli("send", "--text", "first message", "--no-wait",
                            "--client-message-id", "m-1")
        self.wait_idle()

        _, conflict = self.cli("send", "--text", "second message", "--no-wait",
                               "--client-message-id", "m-1", check=False)
        self.assertEqual(conflict["error"]["code"],
                         "client-message-id-conflict")
        self.assertEqual(conflict["outcome"],
                         "client_message_id_conflict")
        self.assertIs(conflict["mutation_performed"], False)
        self.assertEqual(conflict["mutation_status"], "not_started")
        self.assertEqual(conflict["client_message_id"], "m-1")
        self.assertEqual(conflict["conflicting_op"], "prompt")
        self.assertTrue(conflict.get("route") or conflict.get("self_route"))

        # Same text under the same id but a different op is also a conflict;
        # the idle steer reaches the ledger check before its no-turn refusal.
        _, conflict = self.cli("steer", "--text", "first message", "--timeout",
                               "2", "--client-message-id", "m-1", check=False)
        self.assertEqual(conflict["error"]["code"],
                         "client-message-id-conflict")
        self.assertEqual(conflict["conflicting_op"], "prompt")
        self.assertIs(conflict["mutation_performed"], False)

        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 1)
        self.assertEqual(len(view.get("turns") or []), 1)
        self.assertEqual(view["turns"][0]["start_cursor"],
                         first["dispatch_event_cursor"])

    # -- unchanged legacy path ----------------------------------------------

    def test_no_id_keeps_the_duplicate_turn_behaviour(self) -> None:
        self.start()
        text = "no id, unchanged"
        _, first = self.cli("send", "--text", text, "--wait", "--timeout", "20")
        self.assertNotIn("client_message_id", first)
        self.assertNotIn("idempotent_replay", first)
        _, second = self.cli("send", "--text", text, "--wait", "--timeout", "20")
        self.assertNotIn("client_message_id", second)
        self.assertEqual(second["duplicate_warning"]["code"],
                         "duplicate-prompt-warning")

        view = self.view()
        rows = self.user_rows(view)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("clientMessageId" not in row for row in rows))
        self.assertEqual(len(view.get("turns") or []), 2)
        self.assertTrue(all("clientMessageId" not in turn
                            for turn in view.get("turns") or []))
        self.assertNotIn("client_message_id", self.read_record()["last_prompt"])

    # -- bounded ledger and restart -----------------------------------------

    def test_eviction_makes_the_oldest_id_admissible_again(self) -> None:
        self.start()
        first_cursor = None
        for index in range(1, 66):
            _, receipt = self.cli(
                "send", "--text", f"eviction text {index}", "--wait",
                "--timeout", "20", "--client-message-id", f"id-{index}")
            if index == 1:
                first_cursor = receipt.get("dispatch_event_cursor")
        # The 65th registration dropped id-1, so it is a new message now.
        _, again = self.cli("send", "--text", "eviction text 1", "--wait",
                            "--timeout", "20", "--client-message-id", "id-1")
        self.assertNotIn("idempotent_replay", again)
        self.assertIsNone(again.get("replay_of_turn_request_id"))
        self.assertIs(again["mutation_performed"], True)
        self.assertNotEqual(again.get("dispatch_event_cursor"), first_cursor)
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 66)
        self.assertEqual(len(view.get("turns") or []), 66)
        self.assertEqual(view["turns"][0]["start_cursor"], first_cursor)

    def test_restart_same_id_and_text_refuses_restart_unknown(self) -> None:
        self.start()
        text = "a send before the holder restarted"
        self.cli("send", "--text", text, "--wait", "--timeout", "20",
                 "--client-message-id", "r-1")
        self.assertEqual(self.read_record()["last_prompt"]["client_message_id"],
                         "r-1")
        self.cli("stop", "--force")
        self.started = False
        self.start()

        _, refused = self.cli("send", "--text", text, "--no-wait",
                              "--client-message-id", "r-1", check=False)
        self.assertEqual(refused["error"]["code"],
                         "client-message-id-restart-unknown")
        self.assertEqual(refused["outcome"],
                         "client_message_id_restart_unknown")
        self.assertIs(refused["restart_unknown"], True)
        self.assertIs(refused["mutation_performed"], False)
        self.assertEqual(refused["mutation_status"], "not_started")
        self.assertEqual(refused["previous_prompt"]["client_message_id"], "r-1")
        self.assertIn("self_route", refused)
        self.assertIn("not retained", refused["self_route"])
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 0)
        self.assertEqual(len(view.get("turns") or []), 0)

        # A genuinely different message is not blocked by the old text.
        _, admitted = self.cli("send", "--text", text, "--no-wait",
                               "--client-message-id", "r-2")
        self.assertEqual(admitted["outcome"], "in_progress")
        self.assertNotIn("idempotent_replay", admitted)
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 1)
        self.assertEqual(self.user_rows(view)[0]["clientMessageId"], "r-2")

    # -- steer: null retention and clean no-write ---------------------------

    def test_steer_replay_preserves_unknown_mutation(self) -> None:
        self.platform = "dsh"
        self.session = f"dsh-w380-{self._testMethodName.replace('_', '-')[:40]}"
        self.start(scenario="normal",
                   mock_args=("--steering", "silent", "--turn-ms", "4000"))
        _, admitted = self.cli("send", "--text", "turn one", "--no-wait")
        _, first = self.cli("steer", "--text", "steer me", "--timeout", "0.5",
                            "--client-message-id", "s-1", check=False)
        self.assertEqual(first["steer_outcome"], "unknown")
        self.assertIsNone(first["mutation_performed"])
        self.assertEqual(first["client_message_id"], "s-1")

        _, replay = self.cli("steer", "--text", "steer me", "--timeout", "0.5",
                             "--client-message-id", "s-1", check=False)
        self.assertIs(replay.get("idempotent_replay"), True)
        # #379's wrapper must leave an explicit unknown steer alone.
        self.assertIsNone(replay["mutation_performed"])
        self.assertEqual(replay["steer_outcome"], "unknown")
        self.assertEqual(replay["replay_of_turn_request_id"],
                         first["turn_request_id"])
        self.assertEqual(replay["client_message_id"], "s-1")
        events = [json.loads(line) for line in
                  self.mock_log.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
        self.assertEqual(len([event for event in events
                              if event.get("event") == "steering"]), 1)

    def test_inflight_steer_resend_replays_without_a_second_write(self) -> None:
        self.platform = "dsh"
        self.session = f"dsh-w380-{self._testMethodName.replace('_', '-')[:40]}"
        self.start(scenario="normal",
                   mock_args=("--steering", "silent", "--turn-ms", "5000"))
        self.cli("send", "--text", "turn one", "--no-wait")
        argv = self.argv("steer", "--text", "slow steer", "--timeout", "3",
                         "--client-message-id", "inflight-1",
                         scenario="normal", mock_args=("--steering", "silent"))
        slow = subprocess.Popen(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                env=self.env())
        try:
            def steer_sent():
                if not self.mock_log.exists():
                    return None
                events = [json.loads(line) for line in
                          self.mock_log.read_text(encoding="utf-8").splitlines()
                          if line.strip()]
                return next((event for event in events
                             if event.get("event") == "steering"), None)
            wait_for(steer_sent, 10, "first steer frame")
            # The native answer is still pending; this must replay the
            # reservation instead of writing a second steer.
            _, duplicate = self.cli(
                "steer", "--text", "slow steer", "--timeout", "0.5",
                "--client-message-id", "inflight-1", check=False)
            self.assertIs(duplicate.get("idempotent_replay"), True)
            self.assertEqual(duplicate["outcome"], "steer_in_progress")
            self.assertIsNone(duplicate["mutation_performed"])
            self.assertEqual(duplicate["steer_outcome"], "written")
            out, err = slow.communicate(timeout=30)
            self.assertEqual(slow.returncode, 0, (out, err))
            first = json.loads(out) if out.strip() else {}
            self.assertEqual(first.get("steer_outcome"), "unknown", (out, err))
            self.assertIsNone(first.get("mutation_performed"))
            events = [json.loads(line) for line in
                      self.mock_log.read_text(encoding="utf-8").splitlines()
                      if line.strip()]
            self.assertEqual(len([event for event in events
                                  if event.get("event") == "steering"]), 1)
            # The reservation is replaced by the final unknown receipt, so a
            # later resend replays the settled judgement, not the placeholder.
            _, after = self.cli("steer", "--text", "slow steer",
                                "--timeout", "0.5",
                                "--client-message-id", "inflight-1", check=False)
            self.assertIs(after.get("idempotent_replay"), True)
            self.assertEqual(after["steer_outcome"], "unknown")
            self.assertIsNone(after["mutation_performed"])
        finally:
            if slow.poll() is None:
                slow.kill()
                slow.wait(timeout=5)

    def test_clean_no_write_steer_is_not_registered(self) -> None:
        self.start()
        _, idle = self.cli("steer", "--text", "retry me", "--timeout", "2",
                           "--client-message-id", "s-2", check=False)
        self.assertEqual(idle["outcome"], "no-active-turn")
        self.assertIs(idle["mutation_performed"], False)
        # Nothing was written, so the same id is still available as a prompt.
        _, admitted = self.cli("send", "--text", "retry me", "--no-wait",
                               "--client-message-id", "s-2")
        self.assertEqual(admitted["outcome"], "in_progress")
        self.assertNotIn("idempotent_replay", admitted)
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 1)
        self.assertEqual(self.user_rows(view)[0]["clientMessageId"], "s-2")

    def test_steer_interrupt_attaches_its_id_and_replays(self) -> None:
        self.platform = "dsh"
        self.session = f"dsh-w380-{self._testMethodName.replace('_', '-')[:40]}"
        self.start(scenario="normal",
                   mock_args=("--steering", "silent", "--turn-ms", "5000"))
        self.cli("send", "--text", "first turn", "--no-wait")
        _, interrupt = self.cli(
            "steer", "--steer-mode", "interrupt", "--text", "second turn",
            "--timeout", "20", "--client-message-id", "i-1")
        self.assertEqual(interrupt["outcome"],
                         "steer_interrupted_and_resent")
        self.assertIs(interrupt["mutation_performed"], True)
        self.assertEqual(interrupt["client_message_id"], "i-1")
        new_turn = interrupt["new_turn_request_id"]

        view = self.view()
        rows = self.user_rows(view)
        self.assertEqual([row.get("clientMessageId") for row in rows],
                         [None, "i-1"])
        self.assertEqual([turn.get("clientMessageId")
                          for turn in view.get("turns") or []],
                         [None, "i-1"])

        _, replay = self.cli(
            "steer", "--steer-mode", "interrupt", "--text", "second turn",
            "--timeout", "20", "--client-message-id", "i-1")
        self.assertIs(replay.get("idempotent_replay"), True)
        self.assertEqual(replay["replay_of_turn_request_id"], new_turn)
        self.assertEqual(replay["new_turn_request_id"], new_turn)
        self.assertIs(replay["mutation_performed"], True)
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 2)
        self.assertEqual(len(view.get("turns") or []), 2)
        events = [json.loads(line) for line in
                  self.mock_log.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
        self.assertEqual(len([event for event in events
                              if event.get("event") == "session_cancel"]), 1)

    # -- id validation -------------------------------------------------------

    def test_client_message_id_validation(self) -> None:
        self.start()
        cases = [
            ("", "client-message-id-empty"),
            ("x" * 201, "client-message-id-invalid"),
            ("tab\there", "client-message-id-invalid"),
            ("c1-\u0085-control", "client-message-id-invalid"),
        ]
        for value, code in cases:
            _, receipt = self.cli("send", "--text", f"text {code}", "--no-wait",
                                  "--client-message-id", value, check=False)
            self.assertEqual(receipt["error"]["code"], code, (value, receipt))
            self.assertIs(receipt["mutation_performed"], False)
            self.assertEqual(receipt["mutation_status"], "not_started")
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 0)
        self.assertEqual(len(view.get("turns") or []), 0)

        # The bound is bytes, not characters: 100 two-byte chars are accepted.
        boundary = "\u00e9" * 100
        _, admitted = self.cli("send", "--text", "boundary", "--no-wait",
                               "--client-message-id", boundary)
        self.assertEqual(admitted["client_message_id"], boundary)
        view = self.view()
        self.assertEqual(len(self.user_rows(view)), 1)
        self.assertEqual(self.user_rows(view)[0]["clientMessageId"], boundary)

    # -- old holder and expected holder -------------------------------------

    def test_live_old_holder_refuses_before_the_wire(self) -> None:
        self.start()
        self.cli("stop", "--force")
        self.started = False
        record = self.read_record()
        record["holder_features"] = [
            feature for feature in record.get("holder_features") or []
            if feature != "client-message-id/1"]
        sleeper = self.dead_holder()
        record["holder_pid"] = sleeper.pid
        self.write_record(record)

        rc, refused = self.cli("send", "--text", "old holder", "--no-wait",
                               "--client-message-id", "old-1", check=False)
        self.assertEqual(rc, 0)
        self.assertEqual(refused["error"]["code"],
                         "client-message-id-unsupported")
        self.assertEqual(refused["outcome"],
                         "client_message_id_unsupported")
        self.assertIs(refused["mutation_performed"], False)
        self.assertEqual(refused["mutation_status"], "not_started")
        self.assertIn("drain-restart", refused["route"])
        self.assertEqual(refused["holder_instance_id"],
                         record["holder_instance_id"])
        self.assertIsNone(sleeper.poll(), "the sleeper must not be signalled")

    def test_expected_holder_is_checked_at_steer_entries(self) -> None:
        self.start()
        self.cli("send", "--text", "running turn", "--no-wait")
        wrong = "not-this-holder"

        _, steer = self.cli("steer", "--text", "x", "--timeout", "2",
                            "--expected-holder-instance-id", wrong,
                            check=False)
        self.assertEqual(steer["error"]["code"], "holder-instance-mismatch")
        self.assertIs(steer["mutation_performed"], False)
        self.assertEqual(steer["mutation_status"], "not_started")
        self.assertEqual(steer["error"]["holder_instance_id"],
                         self.holder_id())
        self.assertNotIn("cancel_sent", steer)

        _, interrupt = self.cli(
            "steer", "--steer-mode", "interrupt", "--text", "x",
            "--expected-holder-instance-id", wrong, check=False)
        self.assertEqual(interrupt["error"]["code"],
                         "holder-instance-mismatch")
        self.assertIs(interrupt["mutation_performed"], False)
        self.assertEqual(interrupt["mutation_status"], "not_started")
        self.assertNotIn("cancel_sent", interrupt)
        self.assertEqual(len(self.view().get("turns") or []), 1)

        # The composite's own follow-up prompt carries the verified holder id.
        source = HOLDER.read_text(encoding="utf-8")
        section = source.split("def op_steer_interrupt", 1)[1]
        section = section.split("def cancel_turn", 1)[0]
        self.assertIn('"expected_holder_instance_id": self.holder_instance_id',
                      section)


if __name__ == "__main__":
    unittest.main(verbosity=2)
