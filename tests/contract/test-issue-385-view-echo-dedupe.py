#!/usr/bin/env python3
"""Issue #385: view echo dedupe by the current prompt's normalized fingerprint.

The reproduced defect had two directions in one predicate
(``scripts/kaola-acp-holder.py`` before this change):

* an agent ``user_message_chunk`` echo with a ``messageId`` skipped the
  prompt check and became a second ``user`` row;
* an echo with no ``messageId`` whose text was whitespace-normalized was
  concatenated onto the delivered prompt row, so the row no longer equaled
  what was sent; and
* the check matched *every historical prompt* with an exact-or-substring
  test, so a chunk that merely contained an old prompt was dropped, and a
  chunk that was a substring of the current prompt was dropped too.

The adjudicated repair keeps one prompt identity: the whitespace-normalized
fingerprint of the *current* prompt. A ``messageId`` is not an exemption. A
chunk that is a proper prefix of that prompt is held as a chunked-echo
candidate; a following chunk either completes the echo (both dropped) or
proves different text, in which case the candidate flushes as its own row at
the next boundary. The prompt row itself is internally marked and can never
be extended by a chunk. Prompt identity and chunk classification share the
projection lock, so admission cannot re-key an in-flight classification.
The holder passes the raw fingerprint of the turn the update arrived under;
an old prompt's late echo is therefore not dropped against a newer prompt.

The raw ``events.jsonl`` ``session_update`` line is deliberately untouched
(#384 replay constraint): dedupe is projection-only. ``messageId`` and
``clientMessageId`` keep their existing two-layer identity.

``LegacyViewProjection`` reconstructs the pre-fix logic from ``0a62cfae`` and
is used for the required pre-fix counter-proofs; it is test code, not a
second implementation.

Run: python3 tests/contract/test-issue-385-view-echo-dedupe.py -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOLDER = REPO / "scripts" / "kaola-acp-holder.py"
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"

_spec = importlib.util.spec_from_file_location("kaola_acp_holder_i385", HOLDER)
assert _spec is not None and _spec.loader is not None
holder_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(holder_module)


def user_chunk(text: str, message_id: str | None = None) -> dict:
    update = {
        "sessionUpdate": "user_message_chunk",
        "content": {"type": "text", "text": text},
    }
    if message_id is not None:
        update["messageId"] = message_id
    return update


def tool_call(tool_id: str = "tool-1") -> dict:
    return {"sessionUpdate": "tool_call", "toolCallId": tool_id, "title": "Read"}


def user_rows(projection) -> list[dict]:
    return [row for row in projection.snapshot()["messages"]
            if row["role"] == "user"]


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class LegacyViewProjection:
    """The pre-#385 projection logic, kept only to prove the old failure.

    Copied in behavior from ``0a62cfae``: historical prompt texts are kept
    forever, the prompt match is exact-or-substring and only runs when
    ``messageId`` is null, and a non-echo chunk with no id appends to the open
    prompt row.
    """

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self._prompt_texts: list[str] = []
        self._open_message: dict | None = None

    def add_user_from_prompt(self, text: str, cursor: int) -> None:
        self._prompt_texts.append(text)
        self._open_message = None
        self._add("user", text, None, cursor, None)

    def apply_user(self, text: str, message_id: str | None, cursor: int) -> None:
        if message_id is None and any(
            text == previous or text in previous or previous in text
            for previous in self._prompt_texts
            if previous
        ):
            return
        self._add("user", text, message_id, cursor, None)

    def _add(self, role: str, text: str, message_id: str | None, cursor: int,
             received_at: float | None) -> None:
        if message_id is not None:
            for message in reversed(self.messages):
                if message["role"] == role and message["messageId"] == message_id:
                    message["text"] += text
                    return
        else:
            open_message = self._open_message
            if (open_message is not None and self.messages
                    and self.messages[-1] is open_message
                    and open_message["role"] == role
                    and open_message["messageId"] is None):
                open_message["text"] += text
                return
        message = {"role": role, "text": text, "messageId": message_id,
                   "cursor": cursor, "received_at": received_at}
        self.messages.append(message)
        self._open_message = message

    def user_rows(self) -> list[dict]:
        return [row for row in self.messages if row["role"] == "user"]


class CurrentPromptEchoTests(unittest.TestCase):
    """The fixed projection, in process, with no ACP agent or socket."""

    def setUp(self) -> None:
        self.projection = holder_module.ViewProjection()

    def prompt(self, text: str, cursor: int) -> None:
        self.projection.add_user_from_prompt(text, cursor)

    def test_messageid_echo_is_dropped_not_exempted(self) -> None:
        self.prompt("message id echo prompt", 1)
        self.projection.apply(
            user_chunk("message id echo prompt", "echo-msg-1"), 2, 10.0)
        rows = user_rows(self.projection)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["text"], "message id echo prompt")
        self.assertIsNone(rows[0]["messageId"])

    def test_whitespace_normalized_echo_is_dropped(self) -> None:
        self.prompt("alpha beta\n\ngamma delta", 1)
        self.projection.apply(user_chunk("alpha beta gamma delta"), 2, 10.0)
        rows = user_rows(self.projection)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["text"], "alpha beta\n\ngamma delta")

    def test_echo_dedupe_keeps_client_message_id_identity(self) -> None:
        self.projection.add_user_from_prompt(
            "identity prompt", 1, client_message_id="client-1")
        self.projection.apply(user_chunk("identity prompt", "echo-1"), 2)
        rows = user_rows(self.projection)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["clientMessageId"], "client-1")
        self.assertEqual(
            self.projection.snapshot()["turns"][0]["clientMessageId"], "client-1")

    def test_exact_echo_without_messageid_is_still_dropped(self) -> None:
        self.prompt("plain exact echo line", 1)
        self.projection.apply(user_chunk("plain exact echo line"), 2, 10.0)
        self.assertEqual(len(user_rows(self.projection)), 1)

    def test_old_prompt_echo_is_not_dropped_after_a_new_prompt(self) -> None:
        """False-positive direction 1: history equality must not apply."""
        self.prompt("old prompt", 1)
        self.projection.end_turn(10.0, 2, "turn_completed", "end_turn")
        self.prompt("new prompt", 3)
        self.projection.apply(user_chunk("old prompt"), 4, 11.0)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows],
                         ["old prompt", "new prompt", "old prompt"])
        self.assertEqual(rows[-1]["cursor"], 4)

    def test_substring_chunk_is_not_dropped(self) -> None:
        """False-positive direction 2: substring matching is too broad."""
        self.prompt("Fix the login redirect loop.", 1)
        self.projection.apply(user_chunk("login"), 2, 10.0)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows],
                         ["Fix the login redirect loop.", "login"])

    def test_longer_chunk_containing_the_prompt_is_not_dropped(self) -> None:
        self.prompt("abc", 1)
        self.projection.apply(user_chunk("abcdef"), 2, 10.0)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows], ["abc", "abcdef"])

    def test_unknown_chunk_opens_its_own_row(self) -> None:
        self.prompt("hello", 1)
        self.projection.apply(user_chunk("world"), 2, 12.5)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows], ["hello", "world"])
        self.assertEqual(rows[0]["text"], "hello")
        self.assertEqual(rows[1]["cursor"], 2)
        self.assertEqual(rows[1]["received_at"], 12.5)

    def test_unknown_messageid_chunk_keeps_its_identity(self) -> None:
        self.prompt("hello", 1)
        self.projection.apply(user_chunk("world", "unrelated-1"), 2, 12.5)
        rows = user_rows(self.projection)
        self.assertEqual(len(rows), 2, rows)
        self.assertIsNone(rows[0]["messageId"])
        self.assertEqual(rows[1]["messageId"], "unrelated-1")

    def test_chunked_echo_prefixes_are_dropped(self) -> None:
        self.prompt("alpha beta gamma", 1)
        for index, text in enumerate(("alpha ", "beta ", "gamma"), start=2):
            self.projection.apply(user_chunk(text), index, 10.0 + index)
        rows = user_rows(self.projection)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["text"], "alpha beta gamma")

    def test_chunked_echo_with_messageid_is_dropped(self) -> None:
        self.prompt("one two three", 1)
        for index, text in enumerate(("one ", "two ", "three"), start=2):
            self.projection.apply(user_chunk(text, "echo-1"), index, 10.0 + index)
        self.assertEqual(len(user_rows(self.projection)), 1)

    def test_chunked_echo_completes_across_normalized_whitespace(self) -> None:
        self.prompt("alpha beta\n\ngamma delta", 1)
        self.projection.apply(user_chunk("alpha beta "), 2)
        self.projection.apply(user_chunk("gamma   delta"), 3)
        self.assertEqual(len(user_rows(self.projection)), 1)

    def test_prefix_candidate_flushes_at_turn_end(self) -> None:
        self.prompt("alpha beta", 1)
        self.projection.apply(user_chunk("alpha "), 2, 10.0)
        self.assertEqual(len(user_rows(self.projection)), 1, "held as a candidate")
        self.projection.end_turn(11.0, 3, "turn_completed", "end_turn")
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows], ["alpha beta", "alpha "])
        self.assertEqual(rows[1]["cursor"], 2)
        self.assertEqual(rows[1]["received_at"], 10.0)

    def test_prefix_candidate_flushes_before_a_tool_call(self) -> None:
        self.prompt("alpha beta", 1)
        self.projection.apply(user_chunk("alpha "), 2, 10.0)
        self.projection.apply(tool_call(), 3, 10.5)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows], ["alpha beta", "alpha "])
        tools = self.projection.snapshot()["tools"]
        self.assertEqual(tools[0]["toolCallId"], "tool-1")

    def test_prefix_candidate_flushes_on_a_new_prompt(self) -> None:
        self.prompt("alpha beta", 1)
        self.projection.apply(user_chunk("alpha "), 2, 10.0)
        self.prompt("gamma delta", 3)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows],
                         ["alpha beta", "alpha ", "gamma delta"])

    def test_diverging_candidate_is_flushed_before_a_new_identity(self) -> None:
        self.prompt("alpha beta", 1)
        self.projection.apply(user_chunk("alpha "), 2, 10.0)
        self.projection.apply(user_chunk("gamma", "other-1"), 3, 10.5)
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows],
                         ["alpha beta", "alpha ", "gamma"])
        self.assertEqual(rows[1]["messageId"], None)
        self.assertEqual(rows[2]["messageId"], "other-1")

    def test_explicit_foreign_prompt_identity_is_never_an_echo(self) -> None:
        self.prompt("alpha beta", 1)
        self.projection.apply(user_chunk("alpha beta"), 2, prompt_identity="")
        rows = user_rows(self.projection)
        self.assertEqual([row["text"] for row in rows], ["alpha beta", "alpha beta"])

    def test_another_prompts_identity_is_never_an_echo(self) -> None:
        self.prompt("alpha beta", 1)
        self.projection.apply(user_chunk("alpha beta"), 2,
                              prompt_identity="sha256:not-this-prompt")
        self.assertEqual(len(user_rows(self.projection)), 2)


class PreFixCounterProofTests(unittest.TestCase):
    """Run the reconstructed pre-fix logic and the fix on the same input."""

    def setUp(self) -> None:
        self.legacy = LegacyViewProjection()
        self.fixed = holder_module.ViewProjection()

    def test_pre_fix_messageid_echo_created_a_second_row(self) -> None:
        self.legacy.add_user_from_prompt("message id echo prompt", 1)
        self.legacy.apply_user("message id echo prompt", "echo-msg-1", 2)
        self.assertEqual(len(self.legacy.user_rows()), 2)
        self.fixed.add_user_from_prompt("message id echo prompt", 1)
        self.fixed.apply(user_chunk("message id echo prompt", "echo-msg-1"), 2)
        self.assertEqual(len(user_rows(self.fixed)), 1)

    def test_pre_fix_normalized_echo_concatenated_onto_the_prompt(self) -> None:
        self.legacy.add_user_from_prompt("alpha beta\n\ngamma delta", 1)
        self.legacy.apply_user("alpha beta gamma delta", None, 2)
        old = self.legacy.user_rows()
        self.assertEqual(len(old), 1)
        self.assertEqual(old[0]["text"],
                         "alpha beta\n\ngamma deltaalpha beta gamma delta")
        self.fixed.add_user_from_prompt("alpha beta\n\ngamma delta", 1)
        self.fixed.apply(user_chunk("alpha beta gamma delta"), 2)
        new = user_rows(self.fixed)
        self.assertEqual([row["text"] for row in new], ["alpha beta\n\ngamma delta"])

    def test_pre_fix_substring_chunk_was_dropped(self) -> None:
        self.legacy.add_user_from_prompt("Fix the login redirect loop.", 1)
        self.legacy.apply_user("login", None, 2)
        self.assertEqual(len(self.legacy.user_rows()), 1)
        self.fixed.add_user_from_prompt("Fix the login redirect loop.", 1)
        self.fixed.apply(user_chunk("login"), 2)
        self.assertEqual([row["text"] for row in user_rows(self.fixed)],
                         ["Fix the login redirect loop.", "login"])

    def test_pre_fix_old_prompt_echo_was_dropped(self) -> None:
        self.legacy.add_user_from_prompt("old prompt", 1)
        self.legacy.add_user_from_prompt("new prompt", 2)
        self.legacy.apply_user("old prompt", None, 3)
        self.assertEqual([row["text"] for row in self.legacy.user_rows()],
                         ["old prompt", "new prompt"])
        self.fixed.add_user_from_prompt("old prompt", 1)
        self.fixed.add_user_from_prompt("new prompt", 2)
        self.fixed.apply(user_chunk("old prompt"), 3)
        self.assertEqual([row["text"] for row in user_rows(self.fixed)],
                         ["old prompt", "new prompt", "old prompt"])


class LockWindowTests(unittest.TestCase):
    """Prompt identity and echo classification are one critical section."""

    def test_admission_cannot_rekey_an_in_flight_classification(self) -> None:
        projection = holder_module.ViewProjection()
        projection.add_user_from_prompt("alpha beta", 1)
        entered = threading.Event()
        release = threading.Event()
        admitted = threading.Event()
        errors: list[BaseException] = []
        original = projection._classify_user_chunk_locked

        def gated(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise AssertionError("classification gate never released")
            return original(*args, **kwargs)

        projection._classify_user_chunk_locked = gated

        def apply_echo() -> None:
            try:
                projection.apply(user_chunk("alpha beta"), 2)
            except BaseException as exc:  # noqa: BLE001 - reported below
                errors.append(exc)

        def admit_prompt() -> None:
            try:
                projection.add_user_from_prompt("new prompt", 3)
            except BaseException as exc:  # noqa: BLE001 - reported below
                errors.append(exc)
            finally:
                admitted.set()

        echo_thread = threading.Thread(target=apply_echo)
        echo_thread.start()
        self.assertTrue(entered.wait(5), "classification never entered")
        prompt_thread = threading.Thread(target=admit_prompt)
        prompt_thread.start()
        try:
            # add_user_from_prompt must wait for the classification window;
            # if it did not, the echo could be re-keyed to "new prompt".
            self.assertFalse(admitted.wait(0.25),
                             "prompt admission escaped the classification lock window")
        finally:
            release.set()
        echo_thread.join(10)
        prompt_thread.join(10)
        self.assertFalse(errors, errors)
        rows = user_rows(projection)
        self.assertEqual([row["text"] for row in rows], ["alpha beta", "new prompt"])


class EventLogRetentionTests(unittest.TestCase):
    """The real holder still writes the raw echo to events.jsonl (#384)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i385-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "kpr385@example.invalid"],
                       cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "kpr385"],
                       cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("kpr385\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.repo, check=True)
        self.project = os.path.realpath(str(self.repo))
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session = ("grok-w385-"
                        f"{self._testMethodName.replace('_', '-')[:40]}-{os.getpid()}")
        self.started = False
        self.prompt = "Fix the login redirect loop."

    def tearDown(self) -> None:
        if self.started:
            self.cli("stop", "--force", check=False, timeout=30)
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

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["HOME"] = str(self.home)
        return env

    def cli(self, command: str, *args: str, check: bool = True,
            timeout: float = 60) -> tuple[int, dict]:
        argv = [
            sys.executable, str(CLI), "grok", command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", f"{sys.executable} {MOCK} --scenario watch_projection",
            *args,
        ]
        proc = subprocess.run(argv, capture_output=True, text=True,
                              env=self.env(), timeout=timeout)
        try:
            receipt = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command} did not emit JSON: "
                      f"stdout={proc.stdout!r} stderr={proc.stderr!r}")
        if check:
            self.assertNotIn("error", receipt,
                             f"{command} failed: {receipt.get('error')}")
        return proc.returncode, receipt

    def record_dir(self) -> Path:
        digest = hashlib.sha256(self.project.encode("utf-8")).hexdigest()[:16]
        return self.record_root / "grok" / self.session / digest

    def test_echo_is_deduped_in_view_but_retained_in_the_event_log(self) -> None:
        self.cli("start")
        self.started = True
        self.cli("send", "--text", self.prompt, "--no-wait")

        def emitted():
            _, view = self.cli("view")
            if any(row.get("role") == "assistant"
                   for row in view.get("messages") or []):
                return view
            return None

        view = wait_for(emitted, 20, "watch_projection stream to emit")
        rows = [row for row in view.get("messages") or [] if row.get("role") == "user"]
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["text"], self.prompt)
        self.assertIsNone(rows[0]["messageId"])

        events_path = self.record_dir() / "events.jsonl"
        self.assertTrue(events_path.is_file(), events_path)
        events = [json.loads(line) for line in
                  events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        echoes = [
            event for event in events
            if event.get("kind") == "session_update"
            and (event.get("update") or {}).get("sessionUpdate") == "user_message_chunk"
            and ((event.get("update") or {}).get("content") or {}).get("text") == self.prompt
        ]
        self.assertEqual(len(echoes), 1, events)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
