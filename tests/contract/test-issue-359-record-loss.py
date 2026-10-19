#!/usr/bin/env python3
"""Issue #359: holder record-directory loss wakes the Delegator.

Contract coverage, all offline except loopback HTTP:

- ``start`` registers the host in ``<repo>/.kaola/host-registry.json``;
- deleting the whole record directory (and socket) while the holder lives
  turns ``status`` into ``record-lost`` (not ``no-session``), lists the row
  under ``list --repo``'s ``records_lost``, and makes
  ``delegator-webhook status`` emit exactly one ``error``/``holder_lost``
  wake with ``state_detail`` ``record_lost`` — repeated scans report
  ``already-recovered`` and never POST again;
- ``start`` refuses ``record-lost-orphan`` while the argv-verified orphan
  holder lives, and ``stop`` without ``--force`` refuses ``record-lost``;
- ``stop --force`` sweeps the orphan (argv-verified), reports
  ``stopped``/``holder_lost``/``record_lost``, and retires the row;
- ``start --resume`` on the recorded ``acp_session_id`` is the executable
  recovery path and re-registers a fresh ``holder_instance_id``;
- a clean ``stop`` removes the row, so a later ``status`` reports no loss;
- a dead holder with its record intact still takes the classic
  ``delegator_death_wake`` path and is not flagged ``record_lost``.

Every test pins ``KAOLA_DELEGATOR_WEBHOOK_CONFIG``, ``KAOLA_ACP_RECORD_ROOT``
and HOME to temp paths — the real ``~/.config/kaola`` and ``/tmp`` record
roots are never touched. The webhook endpoint is a loopback http.server.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class Endpoint:
    """Loopback sink: every POST is recorded and answered 200."""

    def __init__(self) -> None:
        self.posts: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw)
                except ValueError:
                    body = None
                outer.posts.append({"path": self.path, "body": body})
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/hook"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class RecordLossCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i359-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.project = os.path.realpath(str(self.repo))
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.config = self.root / "cfg" / "delegator-webhook.json"
        self.endpoint: Endpoint | None = None
        self.session: str | None = None

    def tearDown(self) -> None:
        if self.session:
            self.acp("stop", "--force", check=False, timeout=30)
        if self.endpoint:
            self.endpoint.stop()
        # A detached deliver child may still write a receipt under .kaola
        # while this tree is removed; retry past that window.
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

    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_") or key == "KAOLA_LAUNCH_BACKEND"}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["KAOLA_DELEGATOR_WEBHOOK_CONFIG"] = str(self.config)
        env["MOCK_ACP_RESUME_ANY"] = "1"
        env["HOME"] = str(self.home)
        if extra:
            env.update(extra)
        return env

    def hook_json(self, *args: str, stdin: str | None = None,
                  timeout: float = 30) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(CLI), "delegator-webhook", *args],
            capture_output=True, text=True, input=stdin,
            env=self.env(), timeout=timeout)
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError:
            self.fail(f"delegator-webhook stdout not JSON: {proc.stdout!r} "
                      f"stderr={proc.stderr!r}")

    def configure(self) -> None:
        self.endpoint = Endpoint()
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps({
            "schema": "kaola-delegator-webhook/1",
            "projects": {self.project: {
                "url": self.endpoint.url, "sender_key": None,
                "sender_key_attachment": {"style": "url"},
                "enabled": True, "owner_agent": "agent-359",
                "updated_at": "2026-01-01T00:00:00Z"}},
        }))
        self.config.chmod(0o600)

    def mock_command(self) -> str:
        return f"{sys.executable} {MOCK} --scenario normal --caps resume,close"

    def acp(self, command: str, *args: str, check: bool = True,
            timeout: float = 60) -> tuple[int, dict]:
        argv = [sys.executable, str(CLI), "grok", command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", self.mock_command(), *args]
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

    def start_host(self) -> dict:
        self.session = "grok-w359-orchestrator-loss"
        _, receipt = self.acp("start")
        self.assertEqual(receipt.get("session_role"), "host", receipt)
        return receipt

    def record_dir(self) -> Path:
        base = self.record_root / "grok" / self.session
        dirs = [p.parent for p in base.rglob("record.json")]
        self.assertTrue(dirs, f"no record.json under {base}")
        return dirs[0]

    def registry_row(self) -> dict | None:
        path = self.repo / ".kaola" / "host-registry.json"
        if not path.is_file():
            return None
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = (doc.get("hosts") or {}).get(f"grok/{self.session}")
        return rows if isinstance(rows, dict) else None

    def wipe_record(self) -> Path:
        directory = self.record_dir()
        shutil.rmtree(directory)
        # The record socket lives under a separate fixed root; drop it too so
        # the holder is truly unreachable, matching the incident.
        record = self.registry_row() or {}
        candidate = record.get("socket_path")
        if candidate:
            try:
                Path(candidate).unlink()
            except OSError:
                pass
        return directory

    def scan(self) -> dict:
        _, receipt = self.hook_json("status", "--project", self.project)
        self.assertEqual(receipt.get("holder_lost", {}).get("scan"), "complete",
                         receipt.get("holder_lost"))
        return receipt

    def posts_with_detail(self, detail: str) -> list[dict]:
        return [p for p in (self.endpoint.posts if self.endpoint else [])
                if isinstance(p.get("body"), dict)
                and p["body"].get("state_detail") == detail]

    def pid_dead(self, pid) -> bool:
        if not isinstance(pid, int) or pid <= 0:
            return True
        try:
            os.kill(pid, 0)
            return False
        except ProcessLookupError:
            return True
        except PermissionError:
            return False

    # -- tests ---------------------------------------------------------------

    def test_start_registers_row(self) -> None:
        receipt = self.start_host()
        row = self.registry_row()
        self.assertIsNotNone(row, "host-registry.json must register the host")
        assert row is not None
        self.assertEqual(row.get("platform"), "grok")
        self.assertEqual(row.get("session"), self.session)
        self.assertEqual(row.get("repo"), self.project)
        self.assertEqual(row.get("holder_instance_id"),
                         receipt.get("holder_instance_id"))
        self.assertEqual(row.get("holder_pid"), receipt.get("holder_pid"))
        self.assertTrue(isinstance(row.get("record_dir"), str))
        self.assertTrue(Path(row["record_dir"]).is_dir())
        self.assertIsInstance(row.get("registered_at"), str)

    def test_record_loss_wakes_once_and_recovers(self) -> None:
        self.configure()
        started = self.start_host()
        holder_instance_id = started["holder_instance_id"]
        holder_pid = started["holder_pid"]
        acp_session_id = started.get("acp_session_id")
        row = self.registry_row()
        self.assertIsNotNone(row)
        assert row is not None
        record_dir = Path(row["record_dir"])

        # Wipe the record dir and socket; the holder stays alive as an orphan.
        self.wipe_record()
        self.assertFalse(record_dir.exists())
        self.assertFalse(self.pid_dead(holder_pid))

        # status reports record-lost with the recovery facts, not no-session.
        _, status = self.acp("status", check=False)
        self.assertEqual(status.get("error", {}).get("code"), "record-lost",
                         status)
        lost = status.get("record_lost")
        self.assertIsInstance(lost, dict, status)
        assert isinstance(lost, dict)
        self.assertTrue(lost.get("holder_pid_alive"), lost)
        self.assertEqual(lost.get("holder_pid"), holder_pid)
        self.assertIn("--force", lost.get("orphan_sweep", ""), lost)
        self.assertIn("--resume", lost.get("resume", ""), lost)

        # list --repo surfaces the loss even though rows are empty.
        proc = subprocess.run(
            [sys.executable, str(CLI), "list", "--repo", str(self.repo)],
            capture_output=True, text=True, env=self.env(), timeout=30)
        listing = json.loads(proc.stdout)
        self.assertEqual(listing.get("rows"), [])
        lost_rows = listing.get("records_lost") or []
        self.assertEqual(len(lost_rows), 1, listing)
        self.assertEqual(lost_rows[0].get("session"), self.session)
        self.assertTrue(lost_rows[0].get("holder_pid_alive"))
        self.assertEqual(lost_rows[0].get("holder_instance_id"),
                         holder_instance_id)

        # The scan emits the one record-loss wake.
        scan = self.scan()
        lost_list = scan["holder_lost"].get("record_lost", {}).get("lost") or []
        self.assertEqual(len(lost_list), 1, scan["holder_lost"])
        finding = lost_list[0]
        self.assertEqual(finding.get("holder_instance_id"), holder_instance_id)
        self.assertTrue(finding.get("holder_pid_alive"))
        self.assertTrue(finding.get("delegator_death_wake", {}).get("sent"),
                        finding)
        self.assertEqual(finding.get("delegator_death_wake", {}).get("event_seq"),
                         0, finding)
        wake_posts = wait_for(lambda: self.posts_with_detail("record_lost")
                              or None, 10, "record_lost wake POST")
        assert wake_posts is not None
        self.assertEqual(len(wake_posts), 1)
        body = wake_posts[0]["body"]
        self.assertEqual(body.get("schema"), "kaola-delegator-wake/1")
        self.assertEqual(body.get("state"), "error")
        self.assertEqual(body.get("reason"), "holder_lost")
        self.assertEqual(body.get("event_seq"), 0)
        self.assertEqual(body.get("holder_instance_id"), holder_instance_id)
        self.assertEqual(body.get("session"), self.session)
        self.assertEqual(body.get("project"), self.project)

        # A repeated scan reports already-recovered and never POSTs again.
        scan2 = self.scan()
        lost2 = scan2["holder_lost"].get("record_lost", {}).get("lost") or []
        self.assertEqual(len(lost2), 1, scan2["holder_lost"])
        self.assertEqual(
            lost2[0].get("delegator_death_wake", {}).get("reason"),
            "already-recovered", lost2[0])
        time.sleep(0.5)
        self.assertEqual(len(self.posts_with_detail("record_lost")), 1)

        # start refuses while the argv-verified orphan is alive.
        _, refused = self.acp("start", check=False)
        self.assertEqual(refused.get("result"), "refused", refused)
        self.assertEqual(refused.get("reason"), "record-lost-orphan", refused)
        self.assertEqual(refused.get("holder_pid"), holder_pid)
        # The refusal does not re-send the wake.
        self.assertEqual(
            refused.get("delegator_death_wake", {}).get("reason"),
            "already-recovered", refused)

        # A plain stop refuses record-lost and does not signal the orphan.
        _, stop = self.acp("stop", check=False)
        self.assertEqual(stop.get("error", {}).get("code"), "record-lost", stop)
        self.assertFalse(self.pid_dead(holder_pid))

        # stop --force sweeps the orphan, reports holder_lost, retires the row.
        _, forced = self.acp("stop", "--force", check=False)
        self.assertTrue(forced.get("stopped"), forced)
        self.assertTrue(forced.get("holder_lost"), forced)
        self.assertTrue(forced.get("record_lost"), forced)
        wait_for(lambda: self.pid_dead(holder_pid), 5, "orphan holder dead")
        self.assertIsNone(self.registry_row(), "row retired after sweep")

        # The scan is clean now.
        scan3 = self.scan()
        self.assertEqual(scan3["holder_lost"].get("record_lost", {}).get("lost"),
                         [], scan3["holder_lost"])

        # Executable recovery: start --resume on the recorded native id.
        self.assertTrue(acp_session_id, started)
        _, resumed = self.acp("start", "--resume", acp_session_id)
        self.assertEqual(resumed.get("state"), "ready", resumed)
        self.assertNotEqual(resumed.get("holder_instance_id"),
                            holder_instance_id, resumed)
        new_row = self.registry_row()
        self.assertIsNotNone(new_row, "resume re-registers")
        assert new_row is not None
        self.assertEqual(new_row.get("holder_instance_id"),
                         resumed.get("holder_instance_id"))

        # A clean stop retires the row and reports no loss afterwards.
        _, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.assertIsNone(self.registry_row())
        scan4 = self.scan()
        self.assertEqual(scan4["holder_lost"].get("record_lost", {}).get("lost"),
                         [], scan4["holder_lost"])
        self.session = None

    def test_dead_holder_record_present_is_not_record_lost(self) -> None:
        """Regression: the classic dead-holder wake still fires and the
        surviving record keeps the row out of the record_lost report."""
        self.configure()
        started = self.start_host()
        holder_pid = started["holder_pid"]
        record = self.record_dir()
        record_json = json.loads((record / "record.json").read_text())
        for pid in (record_json.get("holder_pid"), record_json.get("agent_pid")):
            if isinstance(pid, int) and pid > 0:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        wait_for(lambda: self.pid_dead(holder_pid), 5, "holder dead")

        scan = self.scan()
        wakes = scan["holder_lost"].get("wakes") or []
        self.assertEqual(len(wakes), 1, scan["holder_lost"])
        self.assertTrue(wakes[0].get("delegator_death_wake", {}).get("sent"),
                        wakes[0])
        self.assertEqual(
            scan["holder_lost"].get("record_lost", {}).get("lost"), [],
            scan["holder_lost"])
        wait_for(lambda: self.posts_with_detail("holder_lost") or None,
                 10, "holder_lost wake POST")
        self.session = None  # already dead; tearDown's stop would be noise

    def test_clean_stop_removes_row_no_wake(self) -> None:
        """A recorded stop retires the row, so no later scan can mistake the
        ended host for record loss."""
        self.configure()
        self.start_host()
        self.assertIsNotNone(self.registry_row())
        _, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.assertIsNone(self.registry_row())
        scan = self.scan()
        self.assertEqual(scan["holder_lost"].get("record_lost", {}).get("lost"),
                         [], scan["holder_lost"])
        self.assertEqual(self.posts_with_detail("record_lost"), [])
        self.session = None


if __name__ == "__main__":
    unittest.main()
