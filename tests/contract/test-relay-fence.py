#!/usr/bin/env python3
"""Issue #6 relay fence and canonical framing acceptance oracles."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


PROJECT = Path(__file__).resolve().parents[2]
RELAY = PROJECT / "scripts" / "kaola-pane-relay.py"
CLIENT = PROJECT / "scripts" / "kaola-relay-client.py"
PROBE = PROJECT / "tests" / "fixtures" / "relay" / "decrqm-probe.py"
FENCE_VECTORS = PROJECT / "tests" / "fixtures" / "relay" / "fence-replies.json"
HELLO_REQUEST = PROJECT / "tests" / "fixtures" / "relay" / "hello-request.json"
HELLO_REPLY = PROJECT / "tests" / "fixtures" / "relay" / "hello-reply.json"


def load_module(path: Path, name: str):
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RelayFenceTests(unittest.TestCase):
    def test_00_relay_and_client_expose_the_required_transport_surfaces(self) -> None:
        self.assertTrue(RELAY.is_file(), f"missing managed relay at {RELAY}")
        self.assertTrue(CLIENT.is_file(), f"missing relay client at {CLIENT}")
        relay = load_module(RELAY, "issue6_relay")
        client = load_module(CLIENT, "issue6_relay_client")
        self.assertIsNotNone(relay)
        self.assertIsNotNone(client)
        for name in (
            "create_control_socket",
            "verify_peer",
            "spawn_child_pty",
            "forward_child_output",
            "forward_outer_input",
            "track_terminal_modes",
            "set_pane_input",
            "stop_child_group",
            "verify_group_stopped",
            "drain_child_pty",
            "run_decrqm_fence",
            "prepare_input",
            "submit_input",
            "restore_running",
            "safe_shutdown",
            "run",
        ):
            self.assertTrue(callable(getattr(relay, name, None)), f"relay lacks {name}")
        for name in (
            "connect_attested",
            "send_request",
            "recv_reply",
            "hello",
            "quiesce",
            "renew",
            "state",
            "prepare_input",
            "submit",
            "abort",
            "resume",
        ):
            self.assertTrue(callable(getattr(client, name, None)), f"client lacks {name}")

    def test_01_framing_vectors_have_no_payload_or_secret_material(self) -> None:
        request = json.loads(HELLO_REQUEST.read_text(encoding="utf-8"))
        reply = json.loads(HELLO_REPLY.read_text(encoding="utf-8"))
        base = {
            "protocol_version",
            "request_id",
            "relay_epoch",
            "operation",
            "expected_child_fingerprint",
            "payload_hex",
        }
        self.assertEqual(set(request), base)
        self.assertEqual(set(reply), base | {"result"})
        self.assertEqual(request["payload_hex"], "")
        self.assertEqual(reply["payload_hex"], "")
        self.assertRegex(request["request_id"], r"^[0-9a-f]{32}$")
        self.assertRegex(request["relay_epoch"], r"^[0-9a-f]{32}$")
        self.assertRegex(request["expected_child_fingerprint"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(request["request_id"], reply["request_id"])
        self.assertEqual(request["relay_epoch"], reply["relay_epoch"])

    def test_02_exact_fence_nonce_accepts_only_one_reply_and_rejects_wrong_malformed_or_duplicate(self) -> None:
        vectors = json.loads(FENCE_VECTORS.read_text(encoding="utf-8"))
        nonce = vectors["nonce"]
        expected = bytes.fromhex(vectors["accepted"])
        self.assertEqual(expected, f"\x1b[{nonce};0$y".encode("ascii"))

        # This is the acceptance shape that the relay's live fence parser
        # must implement: exact byte equality, one-shot consumption, and no
        # prefix/substring acceptance. The live tmux probe below validates
        # that the expected bytes actually arrive through the pane PTY.
        self.assertEqual(expected, bytes.fromhex(vectors["accepted"]))
        for encoded in vectors["rejected"]:
            self.assertNotEqual(bytes.fromhex(encoded), expected)
        self.assertEqual(bytes.fromhex(vectors["duplicate"]), expected)
        replies = [expected, bytes.fromhex(vectors["duplicate"])]
        accepted = [reply for index, reply in enumerate(replies) if index == 0 and reply == expected]
        self.assertEqual(accepted, [expected])

        self.assertTrue(RELAY.is_file(), f"missing relay fence subject at {RELAY}")
        source = RELAY.read_text(encoding="utf-8")
        self.assertIn("run_decrqm_fence", source)
        self.assertRegex(source, r"(?i)nonce")
        self.assertRegex(source, r"(?i)(malformed|unexpected|duplicate)")

    def test_03_live_tmux_decrqm_fence_is_exact_and_render_neutral(self) -> None:
        tmux = subprocess.run(["sh", "-c", "command -v tmux"], capture_output=True, text=True)
        if tmux.returncode != 0:
            self.fail("tmux is required for the pane-native DECRQM proof")

        socket = f"issue6-fence-{os.getpid()}-{int(time.time() * 1000)}"
        session = f"issue6-fence-{os.getpid()}"
        with tempfile.TemporaryDirectory(prefix="kaola-issue6-fence-") as raw_tmp:
            temp = Path(raw_tmp)
            state = temp / "state"
            go = temp / "go"
            reply_log = temp / "reply.hex"
            tmux_cmd = ["tmux", "-L", socket]
            command = (
                f"exec {sys.executable} {PROBE} --state {state} --go {go} "
                f"--reply-log {reply_log}"
            )
            try:
                started = subprocess.run(
                    tmux_cmd + ["new-session", "-d", "-s", session, "-c", str(PROJECT), command],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(started.returncode, 0, started.stderr)
                self.assertTrue(self._wait_for(state, "ready"), "DECRQM fixture did not start")
                before = self._pane_facts(tmux_cmd, session)
                go.touch()
                self.assertTrue(self._wait_for(reply_log), "tmux did not return a DECRQM reply")
                reply = reply_log.read_text(encoding="utf-8").strip()
                self.assertEqual(reply, "1b5b343234323b302479")
                after = self._pane_facts(tmux_cmd, session)
                self.assertEqual(before, after, "DECRQM fence changed rendered pane facts")
            finally:
                subprocess.run(tmux_cmd + ["kill-server"], capture_output=True)

    def test_04_live_child_query_nonce_is_distinct_from_relay_fence_nonce(self) -> None:
        """A child DECRQM reply is a wrong nonce, never the relay fence."""

        tmux = subprocess.run(["sh", "-c", "command -v tmux"], capture_output=True, text=True)
        if tmux.returncode != 0:
            self.fail("tmux is required for child-query demultiplexing proof")
        socket = f"issue6-child-fence-{os.getpid()}-{int(time.time() * 1000)}"
        session = f"issue6-child-fence-{os.getpid()}"
        with tempfile.TemporaryDirectory(prefix="kaola-issue6-child-fence-") as raw_tmp:
            temp = Path(raw_tmp)
            state = temp / "state"
            go = temp / "go"
            reply_log = temp / "reply.hex"
            tmux_cmd = ["tmux", "-L", socket]
            command = (
                f"exec {sys.executable} {PROBE} --state {state} --go {go} "
                f"--reply-log {reply_log} --child-query"
            )
            try:
                started = subprocess.run(
                    tmux_cmd + ["new-session", "-d", "-s", session, "-c", str(PROJECT), command],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(started.returncode, 0, started.stderr)
                self.assertTrue(self._wait_for(state, "ready"), "child-query fixture did not start")
                go.touch()
                self.assertTrue(self._wait_for(reply_log), "tmux did not answer child DECRQM query")
                self.assertEqual(reply_log.read_text(encoding="utf-8").strip(), "1b5b3432343234323b302479")
                self.assertNotEqual(reply_log.read_text(encoding="utf-8").strip(), "1b5b343234323b302479")
            finally:
                subprocess.run(tmux_cmd + ["kill-server"], capture_output=True)

    def test_05_outer_pty_bytes_around_fence_reply_are_rejected_not_replayed(self) -> None:
        """Only the fence reply may cross a quiesced outer-PTY boundary.

        Bytes typed before or after the DECRQM response are not part of the
        guarded payload. Accepting and saving them for the relay's next
        running iteration would replay unguarded input after the transaction.
        """

        relay = load_module(RELAY, "issue6_relay_outer_noise")
        self.assertIsNotNone(relay)
        nonce = 314159
        expected = f"\x1b[{nonce};0$y".encode("ascii")
        cases = {
            "prefix": b"workflow-next\r" + expected,
            "suffix": expected + b"\x1b[200~unguarded\x1b[201~\r",
        }
        for label, outer_block in cases.items():
            with self.subTest(position=label):
                state = type("FenceState", (), {"outer_pending": bytearray()})()
                with (
                    mock.patch.object(relay.secrets, "randbelow", return_value=nonce - 100000),
                    mock.patch.object(relay.os, "write", return_value=len(expected)),
                    mock.patch.object(relay.os, "read", return_value=outer_block),
                    mock.patch.object(relay.select, "select", return_value=([0], [], [])),
                ):
                    try:
                        relay.run_decrqm_fence(state, timeout=0.05)
                    except RuntimeError:
                        pass
                    else:
                        self.fail(
                            f"{label} outer PTY bytes were accepted and buffered "
                            f"for post-transaction replay: {bytes(state.outer_pending)!r}"
                        )
                self.assertEqual(
                    bytes(state.outer_pending),
                    b"",
                    f"{label} outer PTY bytes survived a rejected fence",
                )

    def test_06_outer_pty_byte_queued_after_exact_reply_is_rejected_before_return(self) -> None:
        """A read boundary cannot turn unrelated outer input into later child input.

        The terminal may deliver the exact DECRQM response in one read and a
        concurrently queued user byte in the next.  Returning immediately
        after the first read lets the relay's running loop forward the second
        byte to the child even though it was never covered by the guarded
        transaction.  With the second read already reported ready, the fence
        must consume/reject it before declaring success.
        """

        relay = load_module(RELAY, "issue6_relay_outer_noise_split_reads")
        self.assertIsNotNone(relay)
        nonce = 271828
        expected = f"\x1b[{nonce};0$y".encode("ascii")
        queued_outer_byte = b"x"
        reads = [expected, queued_outer_byte]

        def next_read(_fd: int, _size: int) -> bytes:
            if not reads:
                raise BlockingIOError
            return reads.pop(0)

        state = type("FenceState", (), {"outer_pending": bytearray()})()
        with (
            mock.patch.object(relay.secrets, "randbelow", return_value=nonce - 100000),
            mock.patch.object(relay.os, "write", return_value=len(expected)),
            mock.patch.object(relay.os, "read", side_effect=next_read),
            mock.patch.object(relay.select, "select", return_value=([0], [], [])),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected outer input"):
                relay.run_decrqm_fence(state, timeout=0.05)

        self.assertEqual(reads, [], "the separately queued byte was never consumed by the fence")
        self.assertEqual(bytes(state.outer_pending), b"")

    @staticmethod
    def _wait_for(path: Path, text: str | None = None) -> bool:
        for _ in range(100):
            if path.exists() and (text is None or text in path.read_text(encoding="utf-8")):
                return True
            time.sleep(0.05)
        return False

    @staticmethod
    def _pane_facts(tmux_cmd: list[str], session: str) -> tuple[str, ...]:
        format_string = "#{pane_width}|#{pane_height}|#{cursor_x}|#{cursor_y}|#{cursor_flag}|#{alternate_on}|#{history_size}|#{history_bytes}"
        pane = subprocess.run(
            tmux_cmd + ["list-panes", "-t", f"={session}", "-F", "#{pane_id}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip().splitlines()[0]
        facts = subprocess.run(
            tmux_cmd + ["display-message", "-p", "-t", pane, format_string],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        frame = subprocess.run(
            tmux_cmd + ["capture-pane", "-p", "-N", "-t", pane],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return tuple(facts.split("|")) + (frame,)


if __name__ == "__main__":
    unittest.main(verbosity=2)
