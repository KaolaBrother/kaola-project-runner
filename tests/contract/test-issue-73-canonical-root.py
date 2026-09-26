#!/usr/bin/env python3
"""Issue #73: the Orchestrator canonical-root binding and instance-exact stop.

Two independent guarantees, both proven before any side effect exists:

A. ``scripts/kaola-tmux.sh`` is the one entrypoint every platform already
   passes through. When — and only when — the invocation
   declares Project Runner Orchestrator context by exporting
   ``KAOLA_PROJECT_RUNNER_CANONICAL_REPO``, a new ``start`` uses that bound
   root: an omitted ``--repo`` is completed from it, an explicit ``--repo``
   must resolve exactly to it, and an explicit different path — including a
   linked worktree of the same repository — is refused with a typed receipt
   before a process or record exists. Standalone invocations
   and legacy original-locator close-out keep today's behavior.

B. ``stop`` carries ``expected_holder_instance_id`` end to end, so a holder
   that is no longer the instance the Agent verified refuses the stop before
   any stop side effect instead of killing a same-named replacement.

PTY is retired (Issue #130), so every case runs over ACP. A start the guard
accepts is stopped downstream, before any agent is spawned, by an unverifiable
dispatcher fact: kaola-acp.py refuses it as ``heartbeat-host-unresolved`` and
that receipt carries the root the guard passed through. A guarded refusal must
therefore be the *canonical-root* refusal, and an accepted start must reach the
ACP resolver's refusal instead. That contrast is what distinguishes the guard
from a generic error. The live ACP starts use the offline mock agent or a
spawn that cannot succeed, and each force-stops its own holder.
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
TMUX_CLI = PROJECT / "scripts" / "kaola-tmux.sh"
ACP_CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"

# Enough for a typed refusal; a refusal that needs more than this is prose.
REFUSAL_RECEIPT_BYTES = 4096
CANONICAL_KEY = "KAOLA_PROJECT_RUNNER_CANONICAL_REPO"
DISPATCHER_KEY = "KAOLA_ACP_DISPATCHER"

CODEX_PLATFORM = "codex"
ACP_PLATFORM = "grok"
# No Host record exists for this holder id, so kaola-acp.py refuses any start
# carrying it before a holder or agent exists (heartbeat-host-unresolved).
def unverifiable_dispatcher(repo: Path) -> str:
    return json.dumps({"holder_instance_id": "0" * 32, "platform": "zcode",
                       "repo": str(repo), "session": "zcode-kaola-host"})


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


class CanonicalRootFixture(unittest.TestCase):
    """One main checkout, two linked worktrees of it, and an unrelated repo."""

    @classmethod
    def setUpClass(cls) -> None:
        if not TMUX_CLI.is_file():
            raise AssertionError(f"missing entrypoint at {TMUX_CLI}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i73-")
        cls.root = Path(cls._tmp.name).resolve()

        cls.main_repo = cls.root / "project"
        cls.main_repo.mkdir()
        git("init", "-q", "-b", "main", cwd=cls.main_repo)
        git("config", "user.email", "t@example.invalid", cwd=cls.main_repo)
        git("config", "user.name", "t", cwd=cls.main_repo)
        (cls.main_repo / "README.md").write_text("i73\n", encoding="utf-8")
        git("add", "README.md", cwd=cls.main_repo)
        git("commit", "-qm", "seed", cwd=cls.main_repo)
        git("remote", "add", "origin",
            "https://github.com/KaolaBrother/kaola-project-runner.git",
            cwd=cls.main_repo)

        # Two linked worktrees of the SAME repository, exactly the #274 shape.
        cls.child_a = cls.main_repo / ".kw" / "worktrees" / "issue-73-tests"
        cls.child_b = cls.main_repo / ".kw" / "worktrees" / "issue-73-prod"
        for child, branch in ((cls.child_a, "wt-a"), (cls.child_b, "wt-b")):
            git("worktree", "add", "-q", "-b", branch, str(child), cwd=cls.main_repo)

        # An unrelated repository and a subdirectory that is not a Git root.
        cls.other_repo = cls.root / "other"
        cls.other_repo.mkdir()
        git("init", "-q", "-b", "main", cwd=cls.other_repo)
        cls.subdir = cls.main_repo / "sub" / "dir"
        cls.subdir.mkdir(parents=True)
        cls.plain_dir = cls.root / "plain"
        cls.plain_dir.mkdir()

        # A symlink whose realpath is the canonical root.
        cls.symlink = cls.root / "project-link"
        cls.symlink.symlink_to(cls.main_repo)

        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"i73-{self._testMethodName.lower().replace('_', '-')}"[:79]

    # -- helpers ------------------------------------------------------------

    def run_cli(self, platform: str, command: str, *args: str,
                bound: str | None, transport: str | None = None,
                env_extra: dict[str, str] | None = None,
                timeout: float = 60) -> subprocess.CompletedProcess:
        # Issue #104/#182: each case declares its own binding facts, and no
        # inherited KAOLA_* binding survives into the fixture.
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        if bound is not None:
            env[CANONICAL_KEY] = bound
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        # No case may reach a real CLI: an agent spawn, if one happens, fails.
        env["KAOLA_ACP_COMMAND"] = "/bin/false"
        if env_extra:
            env.update(env_extra)
        argv = [str(TMUX_CLI), platform, command, "--session", self.session, *args]
        if transport is not None:
            argv += ["--transport", transport]
        return subprocess.run(argv, capture_output=True, text=True, env=env,
                              timeout=timeout)

    def receipt(self, result: subprocess.CompletedProcess) -> dict:
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail("expected a JSON receipt\n"
                      f"rc={result.returncode}\n"
                      f"stdout={result.stdout!r}\nstderr={result.stderr!r}")

    def assert_refused(self, result: subprocess.CompletedProcess, reason: str,
                       action: str = "start") -> dict:
        receipt = self.receipt(result)
        self.assertNotEqual(result.returncode, 0, f"refusal must exit nonzero: {receipt}")
        self.assertEqual(receipt.get("result"), "refused", receipt)
        self.assertEqual(receipt.get("reason"), reason, receipt)
        self.assertEqual(receipt.get("action"), action, receipt)
        self.assertIs(receipt.get("mutation_performed"), False, receipt)
        self.assertEqual(receipt.get("mutation_status"), "not_started", receipt)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), REFUSAL_RECEIPT_BYTES,
                             "a typed refusal receipt stays bounded")
        self.assert_no_side_effect()
        return receipt

    def assert_no_side_effect(self) -> None:
        """No record or socket was created for this session."""
        if self.record_root.is_dir():
            for path in self.record_root.glob(f"*/{self.session}/*"):
                self.fail(f"refusal left a record behind: {path}")

    def assert_passed_guard(self, result: subprocess.CompletedProcess) -> None:
        """The invocation was not stopped by the canonical-root guard."""
        blob = result.stdout + result.stderr
        self.assertNotIn("canonical-root", blob,
                         f"guard refused an invocation it must accept: {blob[:2000]!r}")

    def run_stopped_start(self, platform: str, *args: str,
                          bound: str | None) -> subprocess.CompletedProcess:
        """A start that, once past the guard, kaola-acp.py refuses before spawning."""
        return self.run_cli(platform, "start", *args, bound=bound, env_extra={
            DISPATCHER_KEY: unverifiable_dispatcher(self.main_repo)})

    def assert_reached_acp_start(self, result: subprocess.CompletedProcess) -> dict:
        """The guard let a start through to the ACP resolver, which refused it
        before any holder, agent, or record existed."""
        self.assert_passed_guard(result)
        return self.assert_refused(result, "heartbeat-host-unresolved")

    def assert_accepted_under_binding(self, result: subprocess.CompletedProcess,
                                      expected_repo: str | None = None) -> dict:
        """The guard accepted (and completed) the root: the downstream ACP
        refusal carries the bound root it passed through."""
        receipt = self.assert_reached_acp_start(result)
        self.assertEqual(receipt.get("canonical_repo"), str(self.main_repo), receipt)
        if expected_repo is not None:
            self.assertEqual(receipt.get("repo"), expected_repo, receipt)
        return receipt


class TestRunnerDispatch(CanonicalRootFixture):
    """Issue #104's shell PTY gate (N6-N6d) is absorbed by Issue #130's
    unconditional transport-pty-retired refusal, proven in
    test-issue-130-pty-retired.py. What stays here: the canonical-root guard
    still refuses drift under a dispatcher, and an accepted start reaches the
    ACP resolver."""

    def test_a_drifted_root_keeps_its_own_refusal_under_a_dispatcher(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.child_a),
                                        bound=str(self.main_repo))
        self.assert_refused(result, "canonical-root-mismatch")

    def test_acp_start_under_a_dispatcher_passes_the_shell_to_the_acp_resolver(self) -> None:
        """An ACP start reaches kaola-acp.py, whose own resolver refuses this
        unverifiable dispatcher (no Host record) with the typed ACP reason and
        exit 1, creating nothing."""
        result = self.run_stopped_start(ACP_PLATFORM, "--repo", str(self.main_repo), bound=None)
        receipt = self.assert_reached_acp_start(result)
        self.assertEqual(result.returncode, 1, receipt)
        self.assertEqual(receipt.get("heartbeat_host_source"), "dispatcher", receipt)
        self.assertEqual(receipt.get("dispatcher", {}).get("session"), "zcode-kaola-host", receipt)
        self.assertIn("record is missing", receipt.get("detail", ""), receipt)
        self.assertNotIn("canonical_repo", receipt)


class TestBindingCompletesAndAccepts(CanonicalRootFixture):

    def test_omitted_repo_is_completed_from_the_binding(self) -> None:
        """No --repo at all: the bound root is used, not the current directory."""
        result = self.run_stopped_start(CODEX_PLATFORM, bound=str(self.main_repo))
        self.assert_accepted_under_binding(result, expected_repo=str(self.main_repo))

    def test_explicit_repo_equal_to_the_binding_is_accepted(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.main_repo),
                                        bound=str(self.main_repo))
        self.assert_accepted_under_binding(result, expected_repo=str(self.main_repo))

    def test_symlink_spelling_resolving_to_the_binding_is_accepted(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.symlink),
                                        bound=str(self.main_repo))
        self.assert_accepted_under_binding(result, expected_repo=str(self.main_repo))

    def test_binding_spelled_through_a_symlink_accepts_the_real_root(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.main_repo),
                                        bound=str(self.symlink))
        self.assert_accepted_under_binding(result, expected_repo=str(self.main_repo))

    def test_dotted_path_spelling_resolving_to_the_binding_is_accepted(self) -> None:
        spelling = str(self.main_repo / "sub" / "..") + "/./"
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", spelling,
                                        bound=str(self.main_repo))
        self.assert_accepted_under_binding(result, expected_repo=str(self.main_repo))


class TestBindingRefusesDrift(CanonicalRootFixture):

    def test_child_worktree_of_the_same_repository_is_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.child_a),
                                        bound=str(self.main_repo))
        receipt = self.assert_refused(result, "canonical-root-mismatch")
        self.assertEqual(receipt.get("canonical_repo"), str(self.main_repo), receipt)
        self.assertEqual(receipt.get("repo"), str(self.child_a), receipt)

    def test_second_child_worktree_is_refused_too(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.child_b),
                                        bound=str(self.main_repo))
        self.assert_refused(result, "canonical-root-mismatch")

    def test_unrelated_repository_is_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.other_repo),
                                        bound=str(self.main_repo))
        self.assert_refused(result, "canonical-root-mismatch")

    def test_explicit_acp_transport_is_refused_by_the_same_shared_guard(self) -> None:
        result = self.run_cli(ACP_PLATFORM, "start", "--repo", str(self.child_a),
                              bound=str(self.main_repo), transport="acp")
        receipt = self.assert_refused(result, "canonical-root-mismatch")
        self.assertEqual(receipt.get("platform"), ACP_PLATFORM, receipt)
        self.assertEqual((receipt.get("transport") or {}).get("selected"), "acp", receipt)

    def test_refusal_happens_before_the_acp_agent_is_launched(self) -> None:
        marker = self.root / f"launched-{self.session}"
        result = self.run_cli(
            ACP_PLATFORM, "start", "--repo", str(self.child_b),
            bound=str(self.main_repo),
            env_extra={"KAOLA_ACP_COMMAND": f"/bin/sh -c 'touch {marker}; sleep 30'"},
        )
        self.assert_refused(result, "canonical-root-mismatch")
        self.assertFalse(marker.exists(), "the refused start spawned an agent process")


class TestInvalidBinding(CanonicalRootFixture):

    def test_binding_that_is_not_a_git_root_is_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.main_repo),
                                        bound=str(self.subdir))
        self.assert_refused(result, "canonical-root-invalid")

    def test_binding_outside_any_repository_is_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.main_repo),
                                        bound=str(self.plain_dir))
        self.assert_refused(result, "canonical-root-invalid")

    def test_missing_binding_path_is_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.main_repo),
                                        bound=str(self.root / "does-not-exist"))
        self.assert_refused(result, "canonical-root-invalid")

    def test_relative_binding_is_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.main_repo),
                                        bound="project")
        self.assert_refused(result, "canonical-root-invalid")

    def test_invalid_binding_is_refused_even_when_repo_is_omitted(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, bound=str(self.plain_dir))
        self.assert_refused(result, "canonical-root-invalid")


class TestPreservedBehavior(CanonicalRootFixture):
    """Standalone Runner use and legacy close-out must not regress."""

    def test_standalone_start_in_a_child_worktree_is_not_refused(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.child_a),
                                        bound=None)
        self.assert_reached_acp_start(result)

    def test_standalone_acp_start_in_a_child_worktree_is_not_refused(self) -> None:
        # This is the one case in this class that reaches a real ACP start, so
        # it is the one that creates a holder. A holder never exits merely
        # because its agent is gone -- it stays up so that outcome stays
        # readable, here in state `error`, since the `/bin/false` this fixture
        # configures does not exist on macOS and the spawn fails -- so nothing
        # reaps it unless this test does. Register the stop before the start: a
        # start that raises must still be cleaned up, and stop must run while
        # the record it rewrites still exists, since tearDownClass removes the
        # whole tree (Issue #77).
        self.addCleanup(lambda: self.run_cli(
            ACP_PLATFORM, "stop", "--force", "--repo", str(self.child_b),
            bound=None, timeout=60))
        result = self.run_cli(ACP_PLATFORM, "start", "--repo", str(self.child_b),
                              bound=None)
        self.assert_passed_guard(result)

    def test_standalone_omitted_repo_still_fails_as_before(self) -> None:
        """Without a binding there is nothing to complete from: unchanged error."""
        result = self.run_cli(ACP_PLATFORM, "start", bound=None)
        self.assert_passed_guard(result)
        self.assertIn("--repo must be an existing absolute path",
                      result.stdout + result.stderr)

    def test_empty_binding_is_not_orchestrator_context(self) -> None:
        result = self.run_stopped_start(CODEX_PLATFORM, "--repo", str(self.child_a),
                                        bound="")
        self.assert_reached_acp_start(result)

    def test_legacy_worktree_rooted_session_can_still_be_stopped(self) -> None:
        """Close-out by the verified original locator survives the binding."""
        result = self.run_cli(CODEX_PLATFORM, "stop", "--repo", str(self.child_a),
                              bound=str(self.main_repo))
        self.assert_passed_guard(result)

    def test_legacy_worktree_rooted_session_can_still_be_observed(self) -> None:
        result = self.run_cli(CODEX_PLATFORM, "observe", "--repo", str(self.child_a),
                              bound=str(self.main_repo))
        self.assert_passed_guard(result)

    def test_legacy_acp_session_can_still_be_captured(self) -> None:
        result = self.run_cli(ACP_PLATFORM, "capture", "--repo", str(self.child_a),
                              bound=str(self.main_repo))
        self.assert_passed_guard(result)


class TestBoundRootReachesTheWorkerRecord(CanonicalRootFixture):
    """A live ACP dispatch through the shared entrypoint, on the mock agent.

    This is the end-to-end form of acceptance criteria 1 and 2: the Orchestrator
    names no ``--repo`` at all and the started worker's record and receipt still
    carry the bound canonical root, never the directory the caller happened to
    run from.
    """

    def acp_start_env(self) -> dict[str, str]:
        return {"KAOLA_ACP_COMMAND": f"{sys.executable} {MOCK} --scenario normal"}

    def test_started_worker_record_carries_the_bound_root(self) -> None:
        result = self.run_cli(
            ACP_PLATFORM, "start", bound=str(self.main_repo),
            env_extra=self.acp_start_env(), timeout=90,
        )
        receipt = self.receipt(result)
        self.addCleanup(lambda: self.run_cli(
            ACP_PLATFORM, "stop", "--force", "--repo", str(self.main_repo),
            bound=str(self.main_repo),
            env_extra=self.acp_start_env(), timeout=60))
        self.assertNotIn("error", receipt, receipt)
        self.assertEqual(receipt.get("repo"), str(self.main_repo), receipt)

        digest = hashlib.sha256(str(self.main_repo).encode("utf-8")).hexdigest()[:16]
        record_path = (self.record_root / ACP_PLATFORM / self.session / digest
                       / "record.json")
        self.assertTrue(record_path.is_file(), f"no worker record at {record_path}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record.get("repo"), str(self.main_repo), record)

    def test_dispatch_into_a_child_worktree_creates_no_worker_record(self) -> None:
        result = self.run_cli(
            ACP_PLATFORM, "start", "--repo", str(self.child_a),
            bound=str(self.main_repo),
            env_extra=self.acp_start_env(), timeout=90,
        )
        self.assert_refused(result, "canonical-root-mismatch")
        for digest_dir in (self.record_root / ACP_PLATFORM).glob("*/*"):
            self.fail(f"the refused dispatch left a record at {digest_dir}")


class TestStopInstanceProtection(unittest.TestCase):
    """B: stop refuses an instance the Agent did not verify, before side effects."""

    @classmethod
    def setUpClass(cls) -> None:
        if not MOCK.is_file():
            raise AssertionError(f"missing mock agent at {MOCK}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-i73-stop-")
        cls.root = Path(cls._tmp.name).resolve()
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"i73stop-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False

    def tearDown(self) -> None:
        if self._started:
            self.acp("stop", "--force", check=False, timeout=20)

    def acp(self, command: str, *args: str, check: bool = True,
            timeout: float = 40) -> dict:
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        argv = [sys.executable, str(ACP_CLI), "grok", command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", f"{sys.executable} {MOCK} --scenario normal", *args]
        result = subprocess.run(argv, capture_output=True, text=True, env=env,
                                timeout=timeout)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"no JSON receipt for {command}\nrc={result.returncode}\n"
                      f"stdout={result.stdout!r}\nstderr={result.stderr!r}")
        if check and "error" in receipt:
            self.fail(f"{command} returned {receipt['error']}")
        if check and receipt.get("result") == "refused":
            self.fail(f"{command} refused: {receipt.get('reason')}: {receipt.get('detail')}")
        return receipt

    def start(self) -> dict:
        receipt = self.acp("start")
        self._started = True
        return receipt

    def live_instance_id(self) -> str:
        state = self.acp("observe")
        instance = (state.get("record") or {}).get("holder_instance_id") \
            or state.get("holder_instance_id")
        self.assertTrue(instance, f"no holder_instance_id in {state}")
        return instance

    def test_stop_with_a_foreign_instance_id_is_refused_with_no_side_effect(self) -> None:
        self.start()
        live = self.live_instance_id()
        receipt = self.acp("stop", "--expected-holder-instance-id",
                           "0" * 32, check=False)
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-instance-mismatch", receipt)
        self.assertIs(receipt.get("mutation_performed"), False, receipt)
        self.assertEqual(receipt.get("mutation_status"), "not_started", receipt)
        # Zero side effect: the same holder instance is still serving.
        self.assertEqual(self.live_instance_id(), live,
                         "a refused stop must leave the holder untouched")
        state = self.acp("observe")
        self.assertNotIn(state.get("state"), ("stopping", "stopped"),
                         f"a refused stop moved the holder state: {state.get('state')}")

    def test_stop_with_the_verified_instance_id_stops(self) -> None:
        self.start()
        receipt = self.acp("stop", "--expected-holder-instance-id",
                           self.live_instance_id())
        self.assertIs(receipt.get("stopped"), True, receipt)
        self._started = False

    def test_stop_without_an_expected_instance_keeps_todays_behavior(self) -> None:
        self.start()
        receipt = self.acp("stop")
        self.assertIs(receipt.get("stopped"), True, receipt)
        self._started = False

    def test_force_stop_also_honors_the_instance_check(self) -> None:
        self.start()
        live = self.live_instance_id()
        receipt = self.acp("stop", "--force", "--expected-holder-instance-id",
                           "f" * 32, check=False)
        error = receipt.get("error") or {}
        self.assertEqual(error.get("code"), "holder-instance-mismatch", receipt)
        self.assertEqual(self.live_instance_id(), live)

    def test_shared_entrypoint_forwards_the_expected_instance_to_stop(self) -> None:
        self.start()
        live = self.live_instance_id()
        env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["KAOLA_ACP_COMMAND"] = f"{sys.executable} {MOCK} --scenario normal"
        result = subprocess.run(
            [str(TMUX_CLI), "grok", "stop", "--repo", str(self.repo),
             "--session", self.session, "--transport", "acp",
             "--expected-holder-instance-id", "1" * 32],
            capture_output=True, text=True, env=env, timeout=40,
        )
        receipt = json.loads(result.stdout)
        self.assertEqual((receipt.get("error") or {}).get("code"),
                         "holder-instance-mismatch", receipt)
        self.assertEqual(self.live_instance_id(), live)


if __name__ == "__main__":
    unittest.main(verbosity=2)
