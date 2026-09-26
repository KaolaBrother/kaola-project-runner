#!/usr/bin/env python3
"""Issue #162: build identity, stale seats, skew on every start, drain-restart.

Issue #163: a drain-restart that proceeds with mode neither recorded nor
passed applies and reports the platform default a fresh start applies.

Issue #181: the effective permission mode is recorded once, at the start that
applies it; drain-restart no longer re-derives a default, refuses a busy seat
immediately instead of polling, and reads adoption from the new start's own
dispatcher instead of scanning other seats.

Offline only. Holders are the mock ACP agent under an isolated HOME and
record root, and each one is force-stopped before the temporary directory
is removed. No platform CLI is launched.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
HOLDER = PROJECT / "scripts" / "kaola-acp-holder.py"
LOCATE = PROJECT / "scripts" / "kaola-locate.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)


class UpgradeSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git_init(self.repo)
        self.started: list[tuple[str, str]] = []
        self.agent = (
            f"{PYTHON} {MOCK} --scenario normal --caps resume,load,list,close"
        )

    def tearDown(self) -> None:
        for platform, session in self.started:
            self.run_cli(platform, "stop", "--force", session=session, check=False)
        self.tmp.cleanup()

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin",
            "TMPDIR": str(self.root),
            "KAOLA_ACP_RECORD_ROOT": str(self.records),
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
        }
        base.update(extra)
        return base

    def run_cli(self, platform: str, command: str, *args: str, session: str,
                check: bool = True, env: dict[str, str] | None = None,
                argv0: Path | None = None, agent: str | None = None
                ) -> tuple[subprocess.CompletedProcess, dict]:
        program = str(argv0 or CLI)
        argv = [PYTHON, program, platform, command, "--repo", str(self.repo),
                "--session", session, *args]
        if command in ("start", "drain-restart"):
            argv += ["--command", agent or self.agent]
            self.started.append((platform, session))
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env or self.env(), timeout=90,
        )
        payload: dict = {}
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            payload = json.loads(lines[-1])
        if check and result.returncode != 0:
            self.fail(f"{command} exited {result.returncode}: {payload or result.stderr[-800:]}")
        return result, payload

    def test_sibling_modules_are_loaded_at_import(self) -> None:
        holder = load_module(HOLDER, "holder162")
        self.assertIsNotNone(holder._RUNNER_IDENTITY)
        self.assertIsNot(holder._QUOTA, None)
        self.assertNotEqual(holder._QUOTA, False)
        paths = holder._RUNNER_IDENTITY["script_paths"]
        self.assertIn("kaola-quota.py", paths)
        self.assertIn("kaola-acp-holder.py", paths)
        self.assertEqual(len(holder._RUNNER_IDENTITY["runner_build"]), 12)
        quota_sha = paths["kaola-quota.py"]["sha256"]
        self.assertEqual(quota_sha, __import__("hashlib").sha256(
            (HOLDER.parent / "kaola-quota.py").read_bytes()).hexdigest())

    def test_record_and_status_carry_build_identity(self) -> None:
        _result, started = self.run_cli(
            "codex", "start", session="codex-KPR-i162-identity")
        self.assertEqual(started.get("state"), "ready", started)
        _result, status = self.run_cli(
            "codex", "status", session="codex-KPR-i162-identity")
        self.assertEqual(len(status.get("runner_build") or ""), 12, status)
        self.assertIsInstance(status.get("script_paths"), dict)
        self.assertIn("kaola-acp-holder.py", status["script_paths"])
        self.assertRegex(status["script_paths"]["kaola-acp-holder.py"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("stale", status)
        self.assertIs(status["stale"], False, status.get("stale_reasons"))
        listed = subprocess.run(
            [PYTHON, str(CLI), "list", "--repo", str(self.repo), "--record-root", str(self.records)],
            capture_output=True, text=True, env=self.env(), timeout=30, check=True,
        )
        rows = json.loads(listed.stdout)
        match = [row for row in rows["rows"] if row["session"] == "codex-KPR-i162-identity"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["runner_build"], status["runner_build"])
        self.assertIs(match[0]["stale"], False)

    def _installed_cli(self, platform: str = "codex") -> Path:
        tree = self.root / "installed" / f"{platform}-kaola-project-runner"
        shutil.copytree(PROJECT / "skills" / f"{platform}-kaola-project-runner", tree)
        return tree / "scripts" / "kaola-acp.py"

    def test_stale_marks_only_the_restart_required_set(self) -> None:
        session = "codex-KPR-i162-stale"
        cli = self._installed_cli()
        self.run_cli("codex", "start", session=session, argv0=cli)
        holder = cli.parent / "kaola-acp-holder.py"
        cli_file = cli.parent / "kaola-acp.py"
        original_holder = holder.read_bytes()
        # A CLI-file change is reported and does not mark the seat stale.
        cli_file.write_bytes(cli_file.read_bytes() + b"\n# cli only\n")
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], False, status)
        self.assertIn("cli-drift", status.get("reported_drift"), status)
        # The holder file changing is the restart-required stale mark.
        holder.write_bytes(original_holder + b"\n# holder changed\n")
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], True, status)
        self.assertIn("restart-required", status["stale_reasons"])
        self.assertIn("kaola-acp-holder.py", status.get("restart_files") or [])
        _result, stopped = self.run_cli(
            "codex", "stop", "--force", session=session, argv0=cli)
        self.assertTrue(stopped.get("stopped") or stopped.get("state") == "stopped"
                        or stopped.get("residual_pids") == [], stopped)

    def test_a_stale_flagged_seat_still_transports_send_and_steer(self) -> None:
        """Issue #178: the send/steer staleness gate is removed."""
        session = "codex-KPR-i178-stale"
        cli = self._installed_cli()
        slow = (f"{PYTHON} {MOCK} --scenario slow "
                "--steering injected --turn-ms 9000")
        self.run_cli("codex", "start", session=session, argv0=cli, agent=slow)
        holder = cli.parent / "kaola-acp-holder.py"
        holder.write_bytes(holder.read_bytes() + b"\n# holder changed\n")
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], True, status)
        _result, sent = self.run_cli(
            "codex", "send", "--no-wait", "--text", "run the long loop",
            session=session, argv0=cli)
        self.assertEqual(sent.get("outcome"), "in_progress", sent)
        deadline = time.monotonic() + 10
        state: dict = {}
        while time.monotonic() < deadline:
            _result, state = self.run_cli("codex", "observe", session=session, argv0=cli)
            if state.get("turn_active"):
                break
            time.sleep(0.2)
        self.assertTrue(state.get("turn_active"), "the mock turn never became active")
        _result, steered = self.run_cli(
            "codex", "steer", "--text", "STOP the loop and reply STEERED-OK",
            session=session, argv0=cli)
        self.assertEqual(steered.get("steer_outcome"), "injected", steered)
        self.assertIs(steered.get("steer_consumed"), True, steered)
        _result, still = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(still["stale"], True, still)
        self.assertIn("restart-required", still["stale_reasons"])
        self.assertIn("kaola-acp-holder.py", still.get("restart_files") or [])
        self.assertIn("reported_drift", still)

    def test_delegator_handoff_shape_delivers_to_a_stale_host_seat(self) -> None:
        """Issue #178: the Delegator handoff needs no flag or remedy text."""
        session = "zcode-KPR-i178-host"
        cli = self._installed_cli("zcode")
        live = self.env(KAOLA_ZCODE_ENTRY=str(cli), KAOLA_ZCODE_NODE="/bin/sh")
        self.run_cli("zcode", "start", session=session, argv0=cli, env=live)
        holder = cli.parent / "kaola-acp-holder.py"
        holder.write_bytes(holder.read_bytes() + b"\n# holder changed\n")
        _result, status = self.run_cli("zcode", "status", session=session, argv0=cli, env=live)
        self.assertIs(status["stale"], True, status)
        # The exact handoff.md.tmpl command shape: "$ZCODE" send with
        # --no-wait --text.
        result = subprocess.run(
            [str(cli.parent / "runtime-tmux.sh"), "send", "--repo", str(self.repo),
             "--session", session, "--no-wait", "--text", "<handoff>"],
            capture_output=True, text=True,
            env=self.env(PYTHON_BIN=PYTHON), timeout=60)
        receipt = json.loads((result.stdout or "").strip().splitlines()[-1])
        self.assertEqual(result.returncode, 0, receipt)
        self.assertEqual(receipt.get("outcome"), "in_progress", receipt)

    def test_quota_only_drift_is_restart_required_in_status_and_list(self) -> None:
        """Issue #179 reverses #166: the holder pins kaola-quota.py at startup."""
        session = "codex-KPR-i179-quota"
        cli = self._installed_cli()
        self.run_cli("codex", "start", session=session, argv0=cli)
        quota = cli.parent / "kaola-quota.py"
        quota.write_bytes(quota.read_bytes() + b"\n# quota only\n")

        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], True, status)
        self.assertEqual(status.get("stale_reasons"), ["restart-required"], status)
        self.assertEqual(status.get("restart_files"), ["kaola-quota.py"], status)

        listed = subprocess.run(
            [PYTHON, str(CLI), "list", "--repo", str(self.repo),
             "--record-root", str(self.records)],
            capture_output=True, text=True, env=self.env(), timeout=30, check=True,
        )
        rows = json.loads(listed.stdout)
        match = [row for row in rows["rows"] if row["session"] == session]
        self.assertEqual(len(match), 1)
        self.assertIs(match[0]["stale"], True, match[0])
        self.assertEqual(match[0].get("stale_reasons"), ["restart-required"], match[0])

    def test_legacy_record_without_a_quota_entry_is_silent(self) -> None:
        """A record that never captured kaola-quota.py stays silent.

        Issue #179: the quota file is restart-required now, but a record with
        no quota entry has nothing to compare, so a changed quota file that was
        never recorded is simply absent from restart_files - not a new value.
        """
        acp = load_module(CLI, "acp166legacy")
        cli = self._installed_cli()
        quota = cli.parent / "kaola-quota.py"
        quota.write_bytes(quota.read_bytes() + b"\n# quota changed after legacy record\n")
        holder = cli.parent / "kaola-acp-holder.py"
        holder_digest = __import__("hashlib").sha256(holder.read_bytes()).hexdigest()

        fresh = acp.seat_freshness({
            "runner_build": holder_digest[:12],
            "accepted_revision": "a" * 40,
            "script_paths": {
                "kaola-acp-holder.py": {
                    "path": str(holder),
                    "sha256": holder_digest,
                },
            },
        })
        self.assertIs(fresh["stale"], False, fresh)
        self.assertEqual(fresh["reported_drift"], ["pin-drift"] if fresh["pin"] else [], fresh)

    def test_worker_start_and_local_bin_see_build_skew(self) -> None:
        stale = self.home / ".codex" / "skills" / "claude-code-kaola-project-runner" / "scripts"
        stale.mkdir(parents=True)
        for name in ("kaola-acp.py", "kaola-acp-holder.py", "kaola-tmux.sh"):
            target = stale / name
            shutil.copy2(PROJECT / "scripts" / name, target)
        (stale / "kaola-acp.py").write_bytes(
            (PROJECT / "scripts" / "kaola-acp.py").read_bytes() + b"\n# older\n")
        result, refused = self.run_cli(
            "codex", "start", session="codex-KPR-i162-worker", check=False)
        # A direct checkout invocation is the development path: no baseline.
        self.assertEqual(refused.get("state"), "ready", refused)
        self.assertIsNone(refused.get("worker_skill_build"), refused)
        self.run_cli("codex", "stop", "--force", session="codex-KPR-i162-worker")

        local_bin = self.home / ".local" / "bin"
        local_bin.mkdir(parents=True)
        link = local_bin / "kaola-acp"
        link.symlink_to(CLI)
        result, refused = self.run_cli(
            "codex", "start", session="codex-KPR-i162-local",
            check=False, argv0=link)
        self.assertEqual(result.returncode, 1, refused)
        self.assertEqual(refused.get("reason"), "worker-skill-build-skew", refused)
        self.assertIs(refused.get("mutation_performed"), False)

    def test_pin_drift_is_reported_not_stale_without_a_skill_difference(self) -> None:
        acp = load_module(CLI, "acp162pin")
        previous = os.environ.get("HOME")
        previous_path = os.environ.get("PATH")
        os.environ["HOME"] = str(self.home)
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            pin_dir = self.home / ".local" / "bin"
            pin_dir.mkdir(parents=True)
            (pin_dir / ".kaola-project-runner-locate.json").write_text(json.dumps({
                "schema": "kaola-project-runner-locator-registration/1",
                "accepted_revision": "a" * 40,
            }), encoding="utf-8")
            digest = __import__("hashlib").sha256(
                (PROJECT / "scripts" / "kaola-acp.py").read_bytes()).hexdigest()
            fresh = acp.seat_freshness({
                "runner_build": digest[:12],
                "accepted_revision": "b" * 40,
                "script_paths": {
                    "kaola-acp.py": {"path": str(CLI), "sha256": digest},
                    "kaola-acp-holder.py": {
                        "path": str(HOLDER),
                        "sha256": __import__("hashlib").sha256(HOLDER.read_bytes()).hexdigest(),
                    },
                    "kaola-tmux.sh": {
                        "path": str(PROJECT / "scripts" / "kaola-tmux.sh"),
                        "sha256": __import__("hashlib").sha256(
                            (PROJECT / "scripts" / "kaola-tmux.sh").read_bytes()).hexdigest(),
                    },
                },
            })
            self.assertEqual(fresh["pin"], "a" * 40)
            chosen = self.root / "chosen-bin"
            chosen.mkdir()
            os.symlink("/bin/echo", chosen / "kaola-project-runner-locate")
            (chosen / ".kaola-project-runner-locate.json").write_text(json.dumps({
                "accepted_revision": "c" * 40,
            }), encoding="utf-8")
            os.environ["PATH"] = f"{chosen}:/usr/bin:/bin"
            via_path = acp.seat_freshness({
                "runner_build": digest[:12],
                "accepted_revision": "b" * 40,
                "script_paths": {
                    "kaola-acp-holder.py": {
                        "path": str(HOLDER),
                        "sha256": __import__("hashlib").sha256(HOLDER.read_bytes()).hexdigest(),
                    },
                },
            })
            self.assertEqual(via_path["pin"], "c" * 40)
            self.assertIs(via_path["stale"], False, via_path)
        finally:
            if previous is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = previous
            if previous_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = previous_path
        self.assertIs(fresh["stale"], False, fresh)
        self.assertIn("pin-drift", fresh["reported_drift"])
        self.assertEqual(fresh["stale_reasons"], [])

    def test_baseline_exempt_follows_the_start_not_the_resolved_path(self) -> None:
        """A ~/.local/bin link resolves into the checkout. That seat still blocks."""
        _result, checkout = self.run_cli("codex", "start", session="codex-KPR-i162-checkout")
        self.assertIs(checkout.get("baseline_exempt"), True, checkout)
        local_bin = self.home / ".local" / "bin"
        local_bin.mkdir(parents=True)
        link = local_bin / "kaola-acp"
        link.symlink_to(CLI)
        _result, via_bin = self.run_cli(
            "codex", "start", session="codex-KPR-i162-bin", argv0=link)
        self.assertEqual(via_bin.get("state"), "ready", via_bin)
        self.assertIs(via_bin.get("baseline_exempt"), False, via_bin)
        _result, status = self.run_cli(
            "codex", "status", session="codex-KPR-i162-bin", argv0=link)
        self.assertIs(status.get("baseline_exempt"), False, status)
        self.assertIs(status.get("stale"), False, status)

        copy = self.root / "looks-like-checkout" / "scripts" / "kaola-acp-holder.py"
        copy.parent.mkdir(parents=True)
        original = HOLDER.read_bytes()
        copy.write_bytes(original)
        acp = load_module(CLI, "acp162exempt")
        recorded = __import__("hashlib").sha256(original).hexdigest()
        facts = {
            "runner_build": recorded[:12],
            "accepted_revision": "d" * 40,
            "baseline_exempt": False,
            "script_paths": {
                "kaola-acp-holder.py": {"path": str(copy), "sha256": recorded},
            },
        }
        copy.write_bytes(original + b"\n# changed\n")
        blocked = acp.seat_freshness(facts)
        self.assertIs(blocked["stale"], True, blocked)
        self.assertIn("restart-required", blocked["stale_reasons"])
        facts["baseline_exempt"] = True
        reported = acp.seat_freshness(facts)
        self.assertIs(reported["stale"], False, reported)
        self.assertIn("checkout-drift", reported["reported_drift"])

    def test_drain_restart_replaces_the_process_and_adopts_the_new_host(self) -> None:
        host = "codex-KPR-orchestrator-t162"
        worker = "codex-KPR-i162-adopt"
        _result, first = self.run_cli("codex", "start", session=host)
        self.assertEqual(first.get("state"), "ready", first)
        dispatcher_a = {
            "holder_instance_id": first["holder_instance_id"],
            "platform": "codex",
            "repo": first["repo"],
            "session": host,
        }
        # resolve_repo canonicalizes. The start receipt's repo is the canonical path.
        _result, worker_start = self.run_cli(
            "codex", "start", session=worker,
            env=self.env(KAOLA_ACP_DISPATCHER=json.dumps(dispatcher_a)))
        self.assertEqual(worker_start.get("state"), "ready", worker_start)
        self.assertEqual(
            (worker_start.get("dispatcher") or {}).get("holder_instance_id"),
            dispatcher_a["holder_instance_id"], worker_start)
        old_pid = worker_start["holder_pid"]
        resume = worker_start["acp_session_id"]
        self.run_cli("codex", "stop", "--force", session=host)
        _result, second = self.run_cli("codex", "start", session=host)
        self.assertEqual(second.get("state"), "ready", second)
        self.assertNotEqual(second["holder_instance_id"], first["holder_instance_id"])
        dispatcher_b = dict(dispatcher_a, holder_instance_id=second["holder_instance_id"])
        result, restarted = self.run_cli(
            "codex", "drain-restart", "--resume", resume, session=worker,
            env=self.env(
                KAOLA_ACP_DISPATCHER=json.dumps(dispatcher_b),
                MOCK_ACP_RESUME_ANY="1",
            ))
        self.assertEqual(restarted.get("action"), "drain-restart", restarted)
        self.assertEqual(restarted.get("state"), "ready", restarted)
        self.assertNotEqual(restarted.get("holder_pid"), old_pid)
        self.assertFalse(_pid_alive(old_pid))
        adoption = restarted.get("adoption") or {}
        self.assertIs(adoption.get("adopted_on_restart"), True, adoption)
        self.assertEqual(
            (adoption.get("dispatcher") or {}).get("holder_instance_id"),
            second["holder_instance_id"])
        self.assertEqual(restarted.get("previous_holder_instance_id"), worker_start["holder_instance_id"])

    def test_drain_restart_refuses_without_resume_or_continue(self) -> None:
        result, receipt = self.run_cli(
            "codex", "drain-restart", session="codex-KPR-i162-mode", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt.get("reason"), "drain-restart-mode-required")
        self.assertIs(receipt.get("mutation_performed"), False)

    def test_locate_refuses_a_copied_zcode_path_before_preflight(self) -> None:
        missing = str(self.root / "no-such-zcode-entry.js")
        node = self.root / "node-bin"
        node.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        node.chmod(node.stat().st_mode | stat.S_IXUSR)
        env = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin",
            "KAOLA_ZCODE_ENTRY": missing,
            "KAOLA_ZCODE_NODE": str(node),
        }
        completed = subprocess.run(
            [PYTHON, str(LOCATE), "--worker", "codex"],
            capture_output=True, text=True, env=env, cwd=str(PROJECT), timeout=30,
        )
        receipt = json.loads(completed.stdout)
        self.assertNotIn("zcode-runtime-invalid", receipt.get("reasons") or [])
        self.assertEqual(receipt["zcode_runtime"]["entry"], "not-a-file")
        self.assertNotIn("acp-runtime-missing", json.dumps(receipt))

        unset = subprocess.run(
            [PYTHON, str(LOCATE), "--worker", "zcode"],
            capture_output=True, text=True,
            env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"},
            cwd=str(PROJECT), timeout=30,
        )
        unset_receipt = json.loads(unset.stdout)
        self.assertNotIn("zcode-runtime-unset", unset_receipt.get("reasons") or [])
        self.assertIsNone(unset_receipt["zcode_runtime"]["ok"])
        launch = subprocess.run(
            [PYTHON, str(LOCATE), "--worker", "zcode", "--intent", "start"],
            capture_output=True, text=True,
            env={"HOME": str(self.home), "PATH": "/usr/bin:/bin",
                 "KAOLA_ZCODE_ENTRY": missing, "KAOLA_ZCODE_NODE": str(node)},
            cwd=str(PROJECT), timeout=30,
        )
        launch_receipt = json.loads(launch.stdout)
        self.assertIn("zcode-runtime-invalid", launch_receipt.get("reasons") or [])
        resume = subprocess.run(
            [PYTHON, str(LOCATE), "--worker", "zcode", "--intent", "resume"],
            capture_output=True, text=True,
            env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"},
            cwd=str(PROJECT), timeout=30,
        )
        self.assertIn("zcode-runtime-unset", json.loads(resume.stdout).get("reasons") or [])

    def test_busy_drain_restart_leaves_the_seat_running(self) -> None:
        session = "codex-KPR-i162-busy"
        hang = f"{PYTHON} {MOCK} --scenario hang_until_cancel --caps resume,load,list,close"
        started = self.run_cli("codex", "start", session=session, agent=hang)[1]
        self.assertEqual(started.get("state"), "ready", started)
        self.run_cli("codex", "send", "--no-wait", "--text", "stay busy", session=session)
        result, receipt = self.run_cli(
            "codex", "drain-restart", "--resume", started["acp_session_id"],
            "--timeout", "1", session=session, check=False, agent=hang)
        self.assertEqual(result.returncode, 1, receipt)
        self.assertEqual(receipt.get("reason"), "drain-not-idle", receipt)
        self.assertIs(receipt.get("mutation_performed"), False)
        # #184: the refusal names the activity the holder reported, so a busy
        # seat is distinguishable from a lost holder. This holder is alive with
        # a turn running and no pending permission, so the hint is "busy".
        self.assertEqual(receipt.get("activity_hint"), "busy", receipt)
        self.assertEqual(receipt.get("turn_active"), True, receipt)
        self.assertEqual(receipt.get("state"), "ready", receipt)
        self.assertTrue(_pid_alive(started["holder_pid"]))

    def test_drain_restart_refuses_while_the_agent_exit_window_is_open(self) -> None:
        """#184: an exited agent whose state flip has not landed is not idle.

        ``on_agent_exit`` notifies the bound Host *before* setting
        ``agent_exited`` (up to HEARTBEAT_NOTIFY_TIMEOUT), so a seat can be
        ``state == "ready"`` with the agent already dead. Main refused this
        drain-restart; a busy check that only looks at ``state`` would stop and
        restart the seat instead. The host end of the worker's bound socket is
        replaced by one that accepts the notification and never answers, which
        holds that window open for the whole drain-restart.
        """
        host = "codex-KPR-i184-host"
        session = "codex-KPR-i184-window"
        host_started = self.run_cli("codex", "start", session=host)[1]
        self.assertEqual(host_started.get("state"), "ready", host_started)
        dispatcher = {
            "holder_instance_id": host_started["holder_instance_id"],
            "platform": "codex", "repo": host_started["repo"], "session": host,
        }
        worker = self.run_cli(
            "codex", "start", session=session,
            env=self.env(KAOLA_ACP_DISPATCHER=json.dumps(dispatcher), MOCK_ACP_RESUME_ANY="1"))[1]
        self.assertEqual(worker.get("state"), "ready", worker)
        socket_path = (worker.get("heartbeat_host") or {}).get("socket")
        self.assertTrue(socket_path, worker)
        # The bound host is stopped, so nothing else answers this socket, and a
        # listener that never replies takes its place.
        self.run_cli("codex", "stop", "--force", session=host)
        os.unlink(socket_path) if os.path.exists(socket_path) else None
        slow_host = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        slow_host.bind(socket_path)
        slow_host.listen(1)
        accepted: list[socket.socket] = []

        def accept_and_hold() -> None:
            try:
                connection, _ = slow_host.accept()
                accepted.append(connection)
            except OSError:
                pass

        threading.Thread(target=accept_and_hold, daemon=True).start()
        try:
            # Kill the agent while the holder is idle. The holder sees the exit
            # on its own wait thread and blocks in the Host notification before
            # flipping state, which leaves state == "ready" with a dead agent.
            os.kill(worker["agent_pid"], signal.SIGKILL)
            self.assertTrue(self._await_agent_exit_window(session, accepted),
                            "the agent-exit window never opened")
            result, receipt = self.run_cli(
                "codex", "drain-restart", "--resume", worker["acp_session_id"],
                session=session, check=False)
            self.assertEqual(result.returncode, 1, receipt)
            self.assertEqual(receipt.get("reason"), "drain-not-idle", receipt)
            self.assertIs(receipt.get("mutation_performed"), False, receipt)
            self.assertEqual(receipt.get("state"), "ready", receipt)
            self.assertTrue(_pid_alive(worker["holder_pid"]),
                            "the exit window took the seat down")
        finally:
            for connection in accepted:
                connection.close()
            slow_host.close()

    def test_drain_restart_refuses_skew_before_stopping(self) -> None:
        session = "codex-KPR-i162-skewstop"
        started = self.run_cli("codex", "start", session=session)[1]
        pid = started["holder_pid"]
        stale = self.home / ".codex" / "skills" / "claude-code-kaola-project-runner" / "scripts"
        stale.mkdir(parents=True)
        for name in ("kaola-acp.py", "kaola-acp-holder.py", "kaola-tmux.sh"):
            shutil.copy2(PROJECT / "scripts" / name, stale / name)
        (stale / "kaola-acp.py").write_bytes((stale / "kaola-acp.py").read_bytes() + b"\n# older\n")
        local_bin = self.home / ".local" / "bin"
        local_bin.mkdir(parents=True)
        link = local_bin / "kaola-acp"
        link.symlink_to(CLI)
        result, receipt = self.run_cli(
            "codex", "drain-restart", "--resume", started["acp_session_id"],
            session=session, check=False, argv0=link)
        self.assertEqual(result.returncode, 1, receipt)
        self.assertEqual(receipt.get("reason"), "worker-skill-build-skew", receipt)
        self.assertIs(receipt.get("mutation_performed"), False)
        self.assertTrue(_pid_alive(pid), receipt)

    def test_host_drain_restart_no_longer_scans_for_seats_on_the_old_instance(self) -> None:
        host = "codex-KPR-orchestrator-t162b"
        worker = "codex-KPR-i162-named"
        first = self.run_cli("codex", "start", session=host)[1]
        dispatcher = {
            "holder_instance_id": first["holder_instance_id"],
            "platform": "codex",
            "repo": first["repo"],
            "session": host,
        }
        self.run_cli(
            "codex", "start", session=worker,
            env=self.env(KAOLA_ACP_DISPATCHER=json.dumps(dispatcher)))
        restarted = self.run_cli(
            "codex", "drain-restart", "--resume", first["acp_session_id"],
            session=host, env=self.env(MOCK_ACP_RESUME_ANY="1"))[1]
        self.assertEqual(restarted.get("state"), "ready", restarted)
        # Issue #181: adoption is a direct read of the new start's own
        # dispatcher; the extra command_list scan over other seats is gone, so
        # the receipt no longer carries seats_naming_previous_instance. The
        # worker's binding is unchanged by the host's restart.
        self.assertNotIn("seats_naming_previous_instance", restarted)
        _path, worker_record = self._record("codex", worker)
        self.assertEqual(
            (worker_record.get("dispatcher") or {}).get("holder_instance_id"),
            dispatcher["holder_instance_id"], worker_record)

    def test_release_note_rule_and_no_rebind_wording(self) -> None:
        conventions = (PROJECT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py "
            "scripts/kaola-quota.py scripts/adapters platforms",
            conventions,
        )
        self.assertIn("Seats: restart required", conventions)
        self.assertIn("Seats: restart not required", conventions)
        changelog = (PROJECT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## Unreleased", changelog)
        self.assertIn("**Seats: restart required.**", changelog)
        host_doc = (PROJECT / "docs" / "zcode-host.md").read_text(encoding="utf-8")
        self.assertIn("there is no rebind operation", host_doc)
        self.assertIn("A live holder is never hot-replaced", host_doc)
        self.assertIn("drain-restart", host_doc)
        skill = (PROJECT / "templates" / "orchestrator" / "SKILL.md.tmpl").read_text(encoding="utf-8")
        self.assertIn("no rebind", skill)

    def _record(self, platform: str, session: str) -> tuple[Path, dict]:
        matches = sorted(self.records.glob(f"{platform}/{session}/*/record.json"))
        self.assertEqual(len(matches), 1, matches)
        record = json.loads(matches[0].read_text(encoding="utf-8"))
        return matches[0], record

    def _drop_start_selection(self, platform: str, session: str) -> None:
        """A pre-#162 seat: the live record has no start_selection key."""
        path, record = self._record(platform, session)
        self.assertIsInstance(record.get("start_selection"), dict, record)
        del record["start_selection"]
        path.write_text(json.dumps(record), encoding="utf-8")

    def _await_agent_exit_window(self, session: str, accepted: list) -> bool:
        """Wait until the agent is dead but the holder state flip has not landed.

        ``on_agent_exit`` notifies the bound Host before ``agent_exited`` is
        set, so while that notify is blocked the holder still reports
        ``state == "ready"`` with a dead agent - the #184 window. The exact
        shape matters: an idle turn, so the window is reachable only through
        the agent-exit rule and not through the turn or pending rule.
        """
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if accepted:
                state = self.run_cli("codex", "status", session=session, check=False)[1]
                if (state.get("agent_alive") is False
                        and state.get("state") == "ready"
                        and state.get("turn_active") is False
                        and not (state.get("pending_permissions") or [])):
                    return True
            time.sleep(0.05)
        return False

    def _restart(self, platform: str, session: str, resume: str, *args: str):
        return self.run_cli(
            platform, "drain-restart", "--resume", resume, *args,
            session=session, env=self.env(MOCK_ACP_RESUME_ANY="1"),
        )

    def test_drain_restart_legacy_seat_carries_platform_default_mode(self) -> None:
        session = "claude-code-KPR-i163-legacy"
        started = self.run_cli(
            "claude-code", "start", "--mode", "plan", session=session)[1]
        self.assertEqual(started.get("state"), "ready", started)
        self.assertEqual(
            (started.get("config_application") or {}).get("mode", {}).get("value"),
            "plan", started)
        self._drop_start_selection("claude-code", session)
        restarted = self._restart(
            "claude-code", session, started["acp_session_id"],
            "--model", "opus", "--effort", "high")[1]
        self.assertEqual(restarted.get("state"), "ready", restarted)
        # Issue #181: drain-restart no longer re-derives a platform default; the
        # effective mode is decided once, at the start that applies it. The
        # restart reports that value in the receipt's start_selection too, so a
        # pre-#162 seat is never under-reported as mode: null.
        self.assertEqual(
            (restarted.get("start_selection") or {}).get("mode"),
            "bypassPermissions", restarted)
        applied = (restarted.get("config_application") or {}).get("mode") or {}
        self.assertIs(applied.get("applied"), True, restarted)
        self.assertEqual(applied.get("config_id"), "mode", restarted)
        self.assertEqual(applied.get("value"), "bypassPermissions", restarted)
        _path, record = self._record("claude-code", session)
        self.assertEqual(
            (record.get("start_selection") or {}).get("mode"), "bypassPermissions", record)

    def test_drain_restart_explicit_mode_wins_over_platform_default(self) -> None:
        session = "claude-code-KPR-i163-explicit"
        started = self.run_cli(
            "claude-code", "start", "--mode", "plan", session=session)[1]
        self.assertEqual(started.get("state"), "ready", started)
        self._drop_start_selection("claude-code", session)
        restarted = self._restart(
            "claude-code", session, started["acp_session_id"],
            "--model", "opus", "--mode", "acceptEdits")[1]
        self.assertEqual(restarted.get("state"), "ready", restarted)
        self.assertEqual(
            (restarted.get("start_selection") or {}).get("mode"), "acceptEdits", restarted)
        applied = (restarted.get("config_application") or {}).get("mode") or {}
        self.assertEqual(applied.get("value"), "acceptEdits", restarted)
        self.assertNotEqual(applied.get("value"), "bypassPermissions")

    def test_drain_restart_recorded_mode_wins_over_platform_default(self) -> None:
        session = "claude-code-KPR-i163-recorded"
        started = self.run_cli(
            "claude-code", "start", "--mode", "plan", session=session)[1]
        self.assertEqual(started.get("state"), "ready", started)
        _path, record = self._record("claude-code", session)
        self.assertEqual((record.get("start_selection") or {}).get("mode"), "plan", record)
        restarted = self._restart(
            "claude-code", session, started["acp_session_id"],
            "--model", "opus", "--effort", "high")[1]
        self.assertEqual(restarted.get("state"), "ready", restarted)
        self.assertEqual(
            (restarted.get("start_selection") or {}).get("mode"), "plan", restarted)
        applied = (restarted.get("config_application") or {}).get("mode") or {}
        self.assertEqual(applied.get("value"), "plan", restarted)
        self.assertNotEqual(applied.get("value"), "bypassPermissions")

    def test_drain_restart_legacy_seat_still_refuses_without_model_selection(self) -> None:
        session = "claude-code-KPR-i163-refuse"
        started = self.run_cli("claude-code", "start", session=session)[1]
        self.assertEqual(started.get("state"), "ready", started)
        pid = started["holder_pid"]
        self._drop_start_selection("claude-code", session)
        result, receipt = self.run_cli(
            "claude-code", "drain-restart", "--resume", started["acp_session_id"],
            session=session, check=False, env=self.env(MOCK_ACP_RESUME_ANY="1"))
        self.assertEqual(result.returncode, 1, receipt)
        self.assertEqual(receipt.get("reason"), "drain-restart-selection-unknown", receipt)
        self.assertIs(receipt.get("mutation_performed"), False, receipt)
        self.assertIn("--model/--effort/--tier/--fast", receipt.get("detail") or "")
        self.assertNotIn("--permission-mode", receipt.get("detail") or "")
        self.assertTrue(_pid_alive(pid), receipt)

    def test_drain_restart_droid_legacy_seat_uses_its_own_default_mode(self) -> None:
        session = "droid-KPR-i163-legacy"
        started = self.run_cli("droid", "start", "--mode", "normal", session=session)[1]
        self.assertEqual(started.get("state"), "ready", started)
        self._drop_start_selection("droid", session)
        restarted = self._restart(
            "droid", session, started["acp_session_id"], "--model", "auto")[1]
        self.assertEqual(restarted.get("state"), "ready", restarted)
        # Issue #181: as above, the effective default mode is reported in the
        # restart's selection and applied by droid as its autonomy_level option.
        self.assertEqual(
            (restarted.get("start_selection") or {}).get("mode"), "auto-high", restarted)
        applied = (restarted.get("config_application") or {}).get("mode") or {}
        self.assertIs(applied.get("applied"), True, restarted)
        self.assertEqual(applied.get("config_id"), "autonomy_level", restarted)
        self.assertEqual(applied.get("value"), "auto-high", restarted)

    def _raw(self, platform: str, command: str, session: str, *args: str,
             env: dict[str, str] | None = None):
        """A command whose argv this test composes itself, so it can spell flags
        the way argparse accepts them rather than the way run_cli does."""
        if command in ("start", "drain-restart"):
            self.started.append((platform, session))
        result = subprocess.run(
            [PYTHON, str(CLI), platform, command, "--repo", str(self.repo),
             "--session", session, *args],
            capture_output=True, text=True, env=env or self.env(), timeout=90,
        )
        lines = (result.stdout or "").strip().splitlines()
        return result, (json.loads(lines[-1]) if lines else {})

    def test_start_records_the_effective_mode_not_the_raw_flag(self) -> None:
        """Issue #181 acceptance 1: one default-fill site, at the start."""
        for platform, expected in (("claude-code", "bypassPermissions"),
                                   ("droid", "auto-high")):
            session = f"{platform}-KPR-i181-effective"
            started = self.run_cli(platform, "start", session=session)[1]
            self.assertEqual(started.get("state"), "ready", started)
            _path, record = self._record(platform, session)
            self.assertEqual(
                (record.get("start_selection") or {}).get("mode"), expected, record)

    def test_drain_restart_keeps_an_abbreviated_command_and_explicit_mode(self) -> None:
        """Issue #181 acceptance 3, on the one command where explicitness is read.

        ``--com=AGENT`` is an abbreviation-with-equals spelling of ``--command``.
        The deleted ``sys.argv`` scan only matched the literal ``--command``, so
        it took both the command and the explicit mode for absent and
        re-resolved them: the seat then came up on the manifest command, not the
        caller's agent. argparse's ``None``-ness sees both, so the restart keeps
        the caller's agent and applies the explicit mode over the recorded one.
        """
        session = "claude-code-KPR-i181-spelling"
        _result, started = self._raw("claude-code", "start", session, "--command", self.agent)
        self.assertEqual(started.get("state"), "ready", started)
        result, restarted = self._raw(
            "claude-code", "drain-restart", session,
            "--resume", started["acp_session_id"],
            "--com=" + self.agent, "--mode", "acceptEdits", "--model=opus",
            env=self.env(MOCK_ACP_RESUME_ANY="1"))
        self.assertEqual(result.returncode, 0, restarted)
        self.assertEqual(restarted.get("state"), "ready", restarted)
        applied = (restarted.get("config_application") or {}).get("mode") or {}
        self.assertEqual(applied.get("value"), "acceptEdits", restarted)

    def test_drain_restart_revives_a_cleanly_stopped_seat(self) -> None:
        """A stopped seat is restartable, not a ``drain-not-idle`` refusal.

        The ``no-session`` guard lets a record whose holder is dead and whose
        state is ``stopped`` through on purpose: there is nothing to drain, so
        the restart is just the ``start`` below. Reading idle state from that
        dead holder answers ``holder lost`` and would refuse the seat the guard
        deliberately admitted.
        """
        session = "claude-code-KPR-i181-stopped"
        started = self.run_cli("claude-code", "start", session=session)[1]
        self.assertEqual(started.get("state"), "ready", started)
        self.run_cli("claude-code", "stop", "--force", session=session)
        self.assertFalse(_pid_alive(started["holder_pid"]))
        restarted = self.run_cli(
            "claude-code", "drain-restart", "--resume", started["acp_session_id"],
            session=session, check=False, env=self.env(MOCK_ACP_RESUME_ANY="1"))[1]
        self.assertEqual(restarted.get("state"), "ready", restarted)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


if __name__ == "__main__":
    unittest.main()
