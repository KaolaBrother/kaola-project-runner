#!/usr/bin/env python3
"""Issue #95: an exception raised while handling one agent message must not
kill ``AgentConnection._read_loop``.

At the base commit the call ``self.holder.on_agent_message(message)`` runs
unguarded inside the reader loop, so the first escaping exception ends the
thread while the agent process stays alive: every later ``session/update`` is
dropped, every later JSON-RPC response is never resolved, and the turn stays
``active`` forever.

The mock agent's ``handler_raises`` scenario emits, in order:

1. a ``session/update`` notification whose ``params`` is a JSON array — legal
   JSON-RPC by-position params that the client's handler reads as an object,
   so it raises ``AttributeError`` inside ``on_agent_message``;
2. a well-formed ``agent_message_chunk`` carrying ``MOCK-REPLY after handler
   failure``;
3. the JSON-RPC response that ends the prompt turn.

That array payload is one reachable trigger, not the contract. The contract is
the boundary: (2) and (3) must still arrive, the failure on (1) must be visible
in ``status`` and in the event log, and neither the raw message nor the
exception's own text may be written there.
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


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"

# Planted in the unhandleable message's params by the mock scenario. It stands
# in for anything an agent payload may carry: it must never reach a receipt,
# the record, or the event log.
PAYLOAD_SECRET = "kaola-i95-payload-secret"
FOLLOWING_TEXT = "MOCK-REPLY after handler failure"
# scripts/kaola-acp-holder.py CANCEL_GRACE is 5.0: a wedged reader can never
# observe the cancel, so a baseline non-force stop settles no sooner than that
# (measured 5.2 s). A boundary-held reader ends the turn before the stop, so
# the stop skips the wait entirely (measured well under 1 s). The bound sits
# between the two with margin on both sides rather than on either floor.
STOP_SETTLED_SECONDS = 3.0


class ReaderExceptionBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CLI.is_file():
            raise AssertionError(f"missing ACP CLI at {CLI}")
        if not MOCK.is_file():
            raise AssertionError(f"missing mock agent at {MOCK}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i95-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"i95-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        # Issue #77: a holder never self-exits, so the force stop is registered
        # before the start that could create one.
        self.addCleanup(lambda: self.cli("stop", "--force", check=False, timeout=30))

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 60) -> dict:
        argv = [
            sys.executable, str(CLI), "grok", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", f"{sys.executable} {MOCK} --scenario handler_raises",
            *args,
        ]
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env, timeout=timeout
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp {command} emitted no JSON receipt\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\n"
                f"stderr={result.stderr!r}"
            )
        if check and "error" in receipt:
            self.fail(f"kaola-acp {command} returned error {receipt['error']}")
        return receipt

    def record_dir(self) -> Path:
        digest = hashlib.sha256(
            os.path.realpath(str(self.repo)).encode("utf-8")
        ).hexdigest()[:16]
        return self.record_root / "grok" / self.session / digest

    def events(self) -> list[dict]:
        path = self.record_dir() / "events.jsonl"
        if not path.is_file():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # -- the contract ---------------------------------------------------------

    def test_reader_survives_one_failed_message(self) -> None:
        self.cli("start")
        receipt = self.cli("send", "--text", "go", "--timeout", "20", timeout=60)

        # 1. The response that follows the failure still resolves the turn.
        self.assertEqual(receipt.get("outcome"), "turn_completed", receipt)
        self.assertEqual(receipt.get("stop_reason"), "end_turn", receipt)
        # 2. The well-formed update that follows the failure is not dropped.
        self.assertIn(FOLLOWING_TEXT, receipt.get("final_text") or "", receipt)

        # 3. The failure is a failure, counted and named, not silence.
        status = self.cli("status")
        self.assertGreaterEqual(status.get("agent_message_errors", 0), 1, status)
        failures = [e for e in self.events() if e.get("kind") == "agent_message_error"]
        self.assertTrue(failures, "no agent_message_error event was recorded")
        self.assertEqual(failures[0].get("method"), "session/update", failures[0])
        self.assertEqual(failures[0].get("error_type"), "AttributeError", failures[0])
        self.assertTrue(failures[0].get("at"), failures[0])

        # 4. Nothing approves or acknowledges the message that failed.
        answered = [
            e for e in self.events()
            if e.get("kind") in ("request_permission", "permission_answered")
        ]
        self.assertEqual(answered, [], "a failed message must not become an answer")

        # 5. The raw payload never reaches a durable surface.
        record = (self.record_dir() / "record.json").read_text(encoding="utf-8")
        log = (self.record_dir() / "events.jsonl").read_text(encoding="utf-8")
        for name, blob in (("status", json.dumps(status)), ("send receipt",
                           json.dumps(receipt)), ("record.json", record),
                           ("events.jsonl", log)):
            self.assertNotIn(PAYLOAD_SECRET, blob, f"{name} leaked the raw payload")

    def test_exact_stop_settles_without_force(self) -> None:
        self.cli("start")
        self.cli("send", "--text", "go", "--timeout", "20", timeout=60)
        started = time.monotonic()
        stopped = self.cli("stop", timeout=60)
        elapsed = time.monotonic() - started
        self.assertNotIn("error", stopped, stopped)
        # A wedged reader leaves the turn active, so the baseline non-force
        # stop cannot settle before it has waited out CANCEL_GRACE. With the
        # boundary the turn has already ended and the stop is prompt.
        self.assertLess(elapsed, STOP_SETTLED_SECONDS, f"stop took {elapsed:.1f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
