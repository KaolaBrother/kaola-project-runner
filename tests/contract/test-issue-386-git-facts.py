#!/usr/bin/env python3
"""Issue #386: receipt Git facts are command-scoped, not unconditional.

Every CLI receipt used to run ``git rev-parse --abbrev-ref HEAD`` and
``git status --porcelain`` even for the high-frequency ``send --no-wait``,
``steer`` and ``permit`` calls. On a repository with many untracked files the
``status`` invocation dominates the latency, while those receipts have no
contract that consumes the Git evidence.

This suite pins the adjudicated minimal repair:

* ``send --no-wait``, ``steer`` and ``permit`` omit ``git`` by default and do
  not call the Git helper at all;
* a waiting ``send`` keeps the Issue #25 L0 receipt shape, including ``git``;
  an omitted wait that resolves to blocking counts as waiting;
* ``status`` (and the other schema-3 receipts) are unchanged;
* ``--git-facts`` / ``--no-git-facts`` explicitly override either default, and
  ``kaola-tmux.sh`` forwards both;
* the eight refusal helpers that called ``base_receipt`` and then discarded
  ``git`` skip the helper instead of computing it first.

Pre-fix counter-proof: run this file in a checkout of the base commit
``f3964ff0``. ``test_default_omission_never_runs_git_facts`` and
``test_explicit_include_git_false_skips_helper`` fail there because
``base_receipt`` always computes and emits ``git`` and has no ``include_git``
parameter; the live ``--git-facts``/``--no-git-facts`` cases fail because the
base parser rejects the flags. The suite's own default-omission cases are the
pre-fix regression proof.

Run: python3 tests/contract/test-issue-386-git-facts.py -v
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
TMUX = PROJECT / "scripts" / "kaola-tmux.sh"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class ReceiptPolicyUnitTests(unittest.TestCase):
    """The decision table itself, without a holder or a real repository."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module(CLI, "kaola_acp_i386")

    def receipt(self, command: str, *, wait=None, resolved=None,
                explicit=None, include_git=None) -> tuple[dict, int]:
        args = argparse.Namespace(
            platform="grok", session="i386-policy", command=command,
            wait=wait, git_facts=explicit,
        )
        if resolved is not None:
            args.resolved_wait = resolved
        with patch.object(
            self.module, "git_facts",
            return_value={"branch": "workflow/issue-386", "dirty": False},
        ) as mocked:
            if include_git is None:
                receipt = self.module.base_receipt(args, "/tmp/i386-repo")
            else:
                receipt = self.module.base_receipt(
                    args, "/tmp/i386-repo", include_git=include_git)
        return receipt, mocked.call_count

    def test_default_omission_never_runs_git_facts(self) -> None:
        # The resolved no-wait send, steer and permit are the high-frequency
        # receipts. Both the field and the two-subprocess cost must be gone.
        for command, wait, resolved in (
            ("send", False, False),
            ("send", None, False),
            ("steer", None, None),
            ("permit", None, None),
        ):
            with self.subTest(command=command, wait=wait, resolved=resolved):
                receipt, calls = self.receipt(
                    command, wait=wait, resolved=resolved)
                self.assertNotIn("git", receipt)
                self.assertEqual(calls, 0)

    def test_wait_and_state_receipts_keep_git_facts(self) -> None:
        # send --wait (explicit or resolved) preserves the L0 shape; status is
        # the state-verification receipt and is deliberately unchanged.
        for command, wait, resolved in (
            ("send", True, True),
            ("send", None, True),
            ("status", None, None),
            ("observe", None, None),
        ):
            with self.subTest(command=command, wait=wait, resolved=resolved):
                receipt, calls = self.receipt(
                    command, wait=wait, resolved=resolved)
                self.assertEqual(receipt.get("git"),
                                 {"branch": "workflow/issue-386", "dirty": False})
                self.assertEqual(calls, 1)

    def test_explicit_flags_override_the_default_in_both_directions(self) -> None:
        cases = (
            (("send",), {"wait": False, "resolved": False, "explicit": True}, True),
            (("send",), {"wait": True, "resolved": True, "explicit": False}, False),
            (("steer",), {"explicit": True}, True),
            (("permit",), {"explicit": True}, True),
            (("status",), {"explicit": False}, False),
        )
        for (command,), kwargs, expected in cases:
            with self.subTest(command=command, **kwargs):
                receipt, calls = self.receipt(command, **kwargs)
                self.assertEqual("git" in receipt, expected)
                self.assertEqual(calls, 1 if expected else 0)

    def test_explicit_include_git_false_skips_helper(self) -> None:
        # The eight refusal helpers use this parameter instead of computing
        # git and then calling pop("git").
        receipt, calls = self.receipt("start", include_git=False)
        self.assertNotIn("git", receipt)
        self.assertEqual(calls, 0)
        receipt, calls = self.receipt("start", include_git=True)
        self.assertIn("git", receipt)
        self.assertEqual(calls, 1)


class GitFactsCliContract(unittest.TestCase):
    """End-to-end receipts against the mock ACP agent."""

    @classmethod
    def setUpClass(cls) -> None:
        if not CLI.is_file():
            raise AssertionError(f"missing ACP CLI at {CLI}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i386-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        stem = self._testMethodName.lower().replace("_", "-")
        self.session = f"i386-{stem}-{os.getpid()}"[:79]
        self._started: list[tuple[str, str]] = []

    def tearDown(self) -> None:
        for platform, session in self._started:
            self.cli(platform, "stop", "--force", session=session,
                     check=False, timeout=25)

    # -- helpers -------------------------------------------------------------

    def env(self) -> dict[str, str]:
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("KAOLA_")
            or (key == "KAOLA_LAUNCH_BACKEND" and value == "direct")
        }
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        return env

    def mock_command(self, scenario: str, steering: str, turn_ms: int) -> str:
        return " ".join([
            sys.executable, str(MOCK),
            "--scenario", scenario,
            "--steering", steering,
            "--turn-ms", str(turn_ms),
        ])

    def cli(self, platform: str, command: str, *args: str,
            session: str | None = None, scenario: str = "normal",
            steering: str = "none", turn_ms: int = 0,
            check: bool = True, timeout: float = 45) -> dict:
        argv = [
            sys.executable, str(CLI), platform, command,
            "--repo", str(self.repo), "--session", session or self.session,
            "--command", self.mock_command(scenario, steering, turn_ms),
            *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"{command} emitted no JSON receipt: rc={result.returncode}\n"
                f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if check and "error" in receipt:
            self.fail(f"{command} returned error {receipt['error']}")
        if check and receipt.get("result") == "refused":
            self.fail(f"{command} refused: {receipt.get('reason')}: {receipt.get('detail')}")
        return receipt

    def tmux(self, command: str, *args: str, timeout: float = 45) -> dict:
        argv = [
            "bash", str(TMUX), "grok", command,
            "--repo", str(self.repo), "--session", self.session, *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout
        )
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-tmux.sh {command} emitted no JSON receipt: rc={result.returncode}\n"
                f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
            )

    def start(self, platform: str = "grok", session: str | None = None,
              **kwargs) -> dict:
        receipt = self.cli(platform, "start", session=session, **kwargs)
        self._started.append((platform, session or self.session))
        return receipt

    def assert_git_facts(self, receipt: dict) -> None:
        self.assertIn("git", receipt)
        self.assertEqual(set(receipt["git"]), {"branch", "dirty"})
        self.assertIsInstance(receipt["git"]["dirty"], bool)

    # -- live contracts ------------------------------------------------------

    def test_send_no_wait_omits_git_and_git_facts_opts_in(self) -> None:
        self.start()
        receipt = self.cli("grok", "send", "--text", "hello", "--no-wait")
        self.assertEqual(receipt.get("outcome"), "in_progress")
        self.assertNotIn("git", receipt)
        wait_for(
            lambda: not self.cli("grok", "observe").get("turn_active"),
            5, "first no-wait turn to finish",
        )

        opted_in = self.cli(
            "grok", "send", "--text", "hello again", "--no-wait", "--git-facts")
        self.assert_git_facts(opted_in)

    def test_send_wait_keeps_git_and_no_git_facts_opts_out(self) -> None:
        self.start()
        # Omitted wait resolves to the standalone blocking default, so it is a
        # waiting send and keeps the pre-existing L0 shape.
        omitted = self.cli("grok", "send", "--text", "omitted")
        self.assertEqual(omitted.get("wait_selection", {}).get("wait"), True)
        self.assert_git_facts(omitted)

        explicit = self.cli("grok", "send", "--text", "explicit", "--wait")
        self.assertEqual(explicit.get("wait_selection", {}).get("source"), "explicit")
        self.assert_git_facts(explicit)

        opted_out = self.cli(
            "grok", "send", "--text", "opted out", "--wait", "--no-git-facts")
        self.assertNotIn("git", opted_out)

    def test_status_keeps_git_and_no_git_facts_opts_out(self) -> None:
        self.start()
        receipt = self.cli("grok", "status")
        self.assert_git_facts(receipt)

        opted_out = self.cli("grok", "status", "--no-git-facts")
        self.assertNotIn("git", opted_out)

    def test_steer_omits_git_and_git_facts_opts_in(self) -> None:
        platform = "codex"
        self.start(platform=platform, scenario="slow", steering="injected",
                   turn_ms=15000)
        sent = self.cli(platform, "send", "--text", "run the long loop",
                        "--no-wait", scenario="slow", steering="injected",
                        turn_ms=15000)
        self.assertEqual(sent.get("outcome"), "in_progress")
        wait_for(
            lambda: self.cli(platform, "observe", scenario="slow",
                             steering="injected", turn_ms=15000).get("turn_active"),
            10, "mock turn became active",
        )

        steer = self.cli(platform, "steer", "--text", "redirect", scenario="slow",
                         steering="injected", turn_ms=15000)
        self.assertEqual(steer.get("steer_outcome"), "injected")
        self.assertNotIn("git", steer)

        opted_in = self.cli(
            platform, "steer", "--text", "redirect again", "--git-facts",
            scenario="slow", steering="injected", turn_ms=15000)
        self.assertEqual(opted_in.get("steer_outcome"), "injected")
        self.assert_git_facts(opted_in)

    def test_permit_omits_git_and_git_facts_opts_in(self) -> None:
        self.start(scenario="multi_permission")
        sent = self.cli(
            "grok", "send", "--text", "needs permits", "--no-wait",
            scenario="multi_permission")
        self.assertEqual(sent.get("outcome"), "in_progress")
        pending = wait_for(
            lambda: self.cli("grok", "observe",
                             scenario="multi_permission").get("pending_permissions"),
            10, "pending permissions appear",
        )
        ids = [str(entry["request_id"]) for entry in pending]
        self.assertGreaterEqual(len(ids), 2, pending)

        first = self.cli(
            "grok", "permit", "--request-id", ids[0], "--option", "allow",
            scenario="multi_permission")
        self.assertNotIn("git", first)

        second = self.cli(
            "grok", "permit", "--request-id", ids[1], "--option", "allow",
            "--git-facts", scenario="multi_permission")
        self.assert_git_facts(second)

    def test_tmux_forwards_both_overrides(self) -> None:
        # No session is needed: the point is that the shell entrypoint does not
        # reject or drop the new flags before the ACP CLI sees them.
        status = self.tmux("status")
        self.assert_git_facts(status)

        suppressed = self.tmux("status", "--no-git-facts")
        self.assertNotIn("git", suppressed)

        opted_in = self.tmux(
            "send", "--text", "hello", "--no-wait", "--git-facts")
        self.assert_git_facts(opted_in)


if __name__ == "__main__":
    unittest.main(verbosity=2)
