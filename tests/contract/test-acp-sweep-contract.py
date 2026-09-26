#!/usr/bin/env python3
"""Issue #63 contract: an interrupted validate run sweeps exactly its own
ACP holders and touches nothing else.

An interrupted or early-exited ``scripts/validate.sh`` used to leak every
holder its suites had spawned: holders are started with
``start_new_session`` (no signal to the validate process group reaches
them) and the per-test ``stop --force`` teardown never ran. The fix runs
the suites under one validate-owned ``TMPDIR`` root and sweeps that root on
EXIT/INT/TERM through ``scripts/kaola-acp-sweep.py``.

This suite proves the sweep through the real code path: it starts real
holders via ``kaola-acp.py start`` (mock agent, no real CLI) with their
record root and TMPDIR under a test-owned root, issues no stop — precisely
the state an interrupted run leaves behind — then runs the sweep for that
root and asserts zero survivors while a holder under a second root, standing
in for a foreign or concurrent run, stays alive and keeps serving its admin
socket. It also proves the no-holder early-exit path (a render --check
failure exits before any suite runs) is a clean no-op, and pins the
validate.sh wiring: the validate-owned TMPDIR root, the EXIT/INT/TERM trap,
and the sweep-before-removal order.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
SWEEP = PROJECT / "scripts" / "kaola-acp-sweep.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
VALIDATE = PROJECT / "scripts" / "validate.sh"

# AF_UNIX sun_path is ~104 bytes on macOS; a root must leave room for the
# kaola-<uid>-acp/<24 hex>.sock tail under it.
SUN_PATH_BUDGET = 104
SOCKET_TAIL = len(f"/kaola-{os.getuid()}-acp/") + len("0" * 24 + ".sock")


def _load_sweep_module() -> Any:
    """Import the sweep script (hyphenated name) to reuse its ps-based
    zombie-safe liveness check, exactly as the sweep itself sees processes."""
    spec = importlib.util.spec_from_file_location("kaola_acp_sweep", SWEEP)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SWEEP_MODULE = _load_sweep_module()


def short_root(prefix: str) -> Path:
    """A fresh temp root short enough that an ACP admin socket under it stays
    within the sun_path budget; /tmp first, the default tempdir as fallback."""
    for base in ("/tmp", tempfile.gettempdir()):
        if len(base) + 1 + len(prefix) + 10 + SOCKET_TAIL > SUN_PATH_BUDGET - 4:
            continue
        try:
            return Path(tempfile.mkdtemp(prefix=prefix, dir=base))
        except OSError:
            continue
    raise AssertionError("no writable temp base keeps ACP sockets under sun_path")


def process_gone(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return True
    return SWEEP_MODULE.process_gone(pid)


def wait_gone(pid: Any, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process_gone(pid):
            return True
        time.sleep(0.05)
    return process_gone(pid)


def start_holder(root: Path, name: str) -> dict:
    """Start one real holder through the ``kaola-acp.py start`` code path
    (mock agent), with its record root and TMPDIR — the fixture temp roots
    and the shared kaola-<uid>-acp socket dir both follow TMPDIR — under the
    given root: exactly how validate.sh's suites spawn holders."""
    repo = root / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    session = f"swpt-{name}-{os.getpid()}"
    env = {k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}
    env["TMPDIR"] = str(root)
    env["KAOLA_ACP_RECORD_ROOT"] = str(root / "records")
    env["MOCK_ACP_LOG"] = str(root / "mock-events.jsonl")
    command = " ".join([sys.executable, str(MOCK), "--scenario", "normal"])
    argv = [
        sys.executable, str(CLI), "grok", "start",
        "--repo", str(repo), "--session", session, "--command", command,
    ]
    result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=90)
    try:
        receipt = json.loads(result.stdout)
    except ValueError:
        raise AssertionError(
            f"start did not emit a JSON receipt\nrc={result.returncode}\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        ) from None
    if "error" in receipt:
        raise AssertionError(f"start returned error {receipt['error']}\nreceipt={receipt}")
    if receipt.get("state") != "ready":
        raise AssertionError(f"holder did not reach ready state\nreceipt={receipt}")
    return receipt


def holder_socket(root: Path, receipt: dict) -> Path:
    """The admin socket path kaola-acp.py derives for this start: the digest
    of the canonical repo's record directory, under the root's
    kaola-<uid>-acp socket dir (sock_path_for_directory, mirrored)."""
    repo = os.path.realpath(str(root / "repo"))
    directory = (
        root / "records" / receipt["platform"] / receipt["session"]
        / hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
    )
    digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:24]
    return root / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"


class AcpSweepContractTests(unittest.TestCase):
    def sweep_root(self, root: Path) -> dict:
        """Run the sweep exactly as validate.sh's trap does; the root is
        removed afterwards exactly as the trap removes it."""
        result = subprocess.run(
            [sys.executable, str(SWEEP), "--root", str(root)],
            capture_output=True, text=True, timeout=180,
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"sweep did not emit a JSON receipt\nrc={result.returncode}\n"
                f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        self.assertEqual(
            result.returncode, 0, f"sweep exited nonzero\nreceipt={receipt}"
        )
        shutil.rmtree(root, ignore_errors=True)
        return receipt

    def test_interrupted_run_leaves_zero_holders_of_its_own_root(self) -> None:
        root_a = short_root("kaola-swp-a.")
        root_b = short_root("kaola-swp-b.")
        self.addCleanup(self.sweep_root, root_a)
        self.addCleanup(self.sweep_root, root_b)
        own = start_holder(root_a, "own")
        foreign = start_holder(root_b, "foreign")
        # The interrupted-run state: no stop was ever issued, so both holders
        # and both mock agents live on, detached from this process group.
        self.assertFalse(process_gone(own["holder_pid"]))
        self.assertFalse(process_gone(own["agent_pid"]))
        self.assertFalse(process_gone(foreign["holder_pid"]))
        self.assertFalse(process_gone(foreign["agent_pid"]))

        receipt = self.sweep_root(root_a)
        # Exact scope: only this root's holder matched, stopped through the
        # admin-socket stop op a normal teardown uses, with no residue.
        self.assertEqual(receipt["matched_pids"], [own["holder_pid"]])
        self.assertEqual(len(receipt["results"]), 1)
        self.assertEqual(receipt["results"][0]["via"], "socket")
        self.assertFalse(receipt["results"][0]["force_killed"])
        self.assertEqual(receipt["residual_pids"], [])
        self.assertIn(own["agent_pid"], receipt["swept_groups"])
        self.assertTrue(wait_gone(own["holder_pid"]), "own holder survived the sweep")
        self.assertTrue(wait_gone(own["agent_pid"]), "own mock agent survived the sweep")

        # Scope exactness: the other root's holder and agent survive, and its
        # admin socket still serves — a foreign or concurrent run is untouched.
        self.assertFalse(process_gone(foreign["holder_pid"]))
        self.assertFalse(process_gone(foreign["agent_pid"]))
        state = SWEEP_MODULE.KAOLA_ACP.socket_request(
            holder_socket(root_b, foreign), "state", {}, 5.0
        )
        self.assertNotIn("error", state)
        self.assertEqual(state.get("state"), "ready")

        # Sweeping its own root clears the foreign stand-in as well: every
        # invocation owns exactly its own root.
        foreign_receipt = self.sweep_root(root_b)
        self.assertEqual(foreign_receipt["matched_pids"], [foreign["holder_pid"]])
        self.assertEqual(foreign_receipt["residual_pids"], [])
        self.assertTrue(wait_gone(foreign["holder_pid"]))
        self.assertTrue(wait_gone(foreign["agent_pid"]))

    def test_sweep_without_holders_is_a_clean_noop(self) -> None:
        # The early-exit path before any suite ran (render --check failure):
        # the trap sweep must be a clean, successful no-op.
        empty = short_root("kaola-swp-e.")
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        receipt = self.sweep_root(empty)
        self.assertEqual(receipt["matched_pids"], [])
        self.assertEqual(receipt["results"], [])
        self.assertEqual(receipt["residual_pids"], [])

    def test_validate_sh_wires_the_exit_sweep(self) -> None:
        text = VALIDATE.read_text(encoding="utf-8")
        # One validate-owned, short, flat TMPDIR root for the whole run.
        self.assertIn('validate_tmp="$(mktemp -d "/tmp/kaola-val.XXXXXX")"', text)
        self.assertIn('export TMPDIR="$validate_tmp"', text)
        # The sweep runs on exit, interrupt, and terminate.
        self.assertIn("trap cleanup EXIT", text)
        self.assertIn("trap 'exit 130' INT", text)
        self.assertIn("trap 'exit 143' TERM", text)
        # Only this invocation's root is ever passed to the sweep, and the
        # sweep runs before that root is removed.
        self.assertIn('kaola-acp-sweep.py" --root "$validate_tmp"', text)
        self.assertLess(
            text.index("kaola-acp-sweep.py"),
            text.index('rm -rf "$validate_tmp"'),
            "the sweep must run before its root is removed",
        )
        # The sweep suite itself is registered in the run it protects.
        self.assertIn("test-acp-sweep-contract.py", text)


if __name__ == "__main__":
    unittest.main()
