#!/usr/bin/env python3
"""Issue #162: build identity, stale seats, skew on every start, drain-restart.

Issue #163: a drain-restart that proceeds with mode neither recorded nor
passed applies and reports the platform default a fresh start applies.

Offline only. Holders are the mock ACP agent under an isolated HOME and
record root, and each one is force-stopped before the temporary directory
is removed. No platform CLI is launched.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
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

    def _installed_cli(self) -> Path:
        tree = self.root / "installed" / "codex-kaola-project-runner"
        shutil.copytree(PROJECT / "skills" / "codex-kaola-project-runner", tree)
        return tree / "scripts" / "kaola-acp.py"

    def test_stale_blocks_only_the_restart_required_set(self) -> None:
        session = "codex-KPR-i162-stale"
        cli = self._installed_cli()
        self.run_cli("codex", "start", session=session, argv0=cli)
        holder = cli.parent / "kaola-acp-holder.py"
        cli_file = cli.parent / "kaola-acp.py"
        original_holder = holder.read_bytes()
        # A CLI-file change is reported and does not refuse send or stop.
        cli_file.write_bytes(cli_file.read_bytes() + b"\n# cli only\n")
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], False, status)
        self.assertIn("cli-drift", status.get("reported_drift"), status)
        _result, sent = self.run_cli(
            "codex", "send", "--no-wait", "--text", "cli drift is not a block",
            session=session, argv0=cli)
        self.assertNotEqual(sent.get("reason"), "seat-stale", sent)
        # The holder file changing is the restart-required block.
        holder.write_bytes(original_holder + b"\n# holder changed\n")
        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], True, status)
        self.assertIn("restart-required", status["stale_reasons"])
        self.assertIn("kaola-acp-holder.py", status.get("restart_files") or [])
        result, refused = self.run_cli(
            "codex", "send", "--text", "do not dispatch", session=session,
            check=False, argv0=cli)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(refused.get("reason"), "seat-stale")
        self.assertIs(refused.get("mutation_performed"), False)
        _result, stopped = self.run_cli(
            "codex", "stop", "--force", session=session, argv0=cli)
        self.assertNotEqual(stopped.get("reason"), "seat-stale", stopped)
        self.assertTrue(stopped.get("stopped") or stopped.get("state") == "stopped"
                        or stopped.get("residual_pids") == [], stopped)

    def test_quota_only_drift_is_reported_and_not_stale_in_status_and_list(self) -> None:
        session = "codex-KPR-i166-quota"
        cli = self._installed_cli()
        self.run_cli("codex", "start", session=session, argv0=cli)
        quota = cli.parent / "kaola-quota.py"
        quota.write_bytes(quota.read_bytes() + b"\n# quota only\n")

        _result, status = self.run_cli("codex", "status", session=session, argv0=cli)
        self.assertIs(status["stale"], False, status)
        self.assertIn("quota-drift", status.get("reported_drift"), status)
        self.assertEqual(status.get("stale_reasons"), [], status)

        listed = subprocess.run(
            [PYTHON, str(CLI), "list", "--repo", str(self.repo),
             "--record-root", str(self.records)],
            capture_output=True, text=True, env=self.env(), timeout=30, check=True,
        )
        rows = json.loads(listed.stdout)
        match = [row for row in rows["rows"] if row["session"] == session]
        self.assertEqual(len(match), 1)
        self.assertIs(match[0]["stale"], False, match[0])
        self.assertIn("quota-drift", match[0].get("reported_drift"), match[0])

    def test_legacy_record_without_quota_digest_is_silent(self) -> None:
        acp = load_module(CLI, "acp166legacy")
        cli = self._installed_cli()
        quota = cli.parent / "kaola-quota.py"
        quota.write_bytes(quota.read_bytes() + b"\n# quota changed after legacy record\n")
        holder = cli.parent / "kaola-acp-holder.py"
        holder_digest = __import__("hashlib").sha256(holder.read_bytes()).hexdigest()

        fresh = acp.seat_freshness("codex", str(self.repo), {
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
        self.assertNotIn("quota-drift", fresh["reported_drift"], fresh)

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
            fresh = acp.seat_freshness("codex", str(self.repo), {
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
            via_path = acp.seat_freshness("codex", str(self.repo), {
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
            self.assertNotIn("quota-drift", via_path["reported_drift"], via_path)
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
        self.assertNotIn("quota-drift", fresh["reported_drift"], fresh)
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
        blocked = acp.seat_freshness("codex", str(self.repo), facts)
        self.assertIs(blocked["stale"], True, blocked)
        self.assertIn("restart-required", blocked["stale_reasons"])
        facts["baseline_exempt"] = True
        reported = acp.seat_freshness("codex", str(self.repo), facts)
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
        self.assertTrue(_pid_alive(started["holder_pid"]))

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

    def test_host_drain_restart_names_seats_still_on_the_old_instance(self) -> None:
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
        named = restarted.get("seats_naming_previous_instance") or []
        self.assertTrue(any(row.get("session") == worker for row in named), restarted)

    def test_release_note_rule_and_no_rebind_wording(self) -> None:
        conventions = (PROJECT / "docs" / "conventions.md").read_text(encoding="utf-8")
        self.assertIn(
            "git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py "
            "scripts/adapters platforms",
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
        self.assertIn("--confirm-stale", skill)
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
        selection = restarted.get("start_selection") or {}
        self.assertEqual(selection.get("mode"), "bypassPermissions", restarted)
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
        self.assertEqual(
            (restarted.get("start_selection") or {}).get("mode"), "auto-high", restarted)
        applied = (restarted.get("config_application") or {}).get("mode") or {}
        self.assertIs(applied.get("applied"), True, restarted)
        self.assertEqual(applied.get("config_id"), "autonomy_level", restarted)
        self.assertEqual(applied.get("value"), "auto-high", restarted)


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
