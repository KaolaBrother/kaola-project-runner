#!/usr/bin/env python3
"""Issue #388: only a host-role holder receives the Host heartbeat carrier.

The defect: ``kaola-acp.py`` handed ``--host-entry`` to every holder, whatever
the seat's role, and the holder's worker-event delivery chose the Host carrier
whenever that entry was non-empty. A worker/Expert self-prompt therefore opened
``/kaola-project-runner`` and asked for a full heartbeat pass.

This suite pins both guards:

* the payload seam - a dsh/devin holder whose role is worker or expert, even
  when a legacy start armed it with a Host entry, receives the compact
  ``kaola-worker-notify/1`` notice for a staged ``cwd_repaired`` and an
  ordinary worker event; a host-role holder still receives
  ``kaola-host-notify/1`` with the heartbeat body;
* the start seam - a real dsh/devin worker or Expert start omits
  ``--host-entry`` from the holder argv and records an empty
  ``host_skill_entry``, while a Host start keeps both.

The Sideagent node is checked as its own convention: an explicit ``sideagent``
holder gets the same compact worker notice for its own staged events, and its
Host-authored batch prompt is the separate ``kaola-sideagent-relay/1`` path -
never the Host carrier.
"""

from __future__ import annotations

import argparse
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

PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
HOLDER_PATH = PROJECT / "scripts" / "kaola-acp-holder.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"

# The payload tests never contact a Host binding or a sideagent state file.
os.environ.pop("KAOLA_ACP_HEARTBEAT_HOST", None)
os.environ.pop("KAOLA_ACP_HEARTBEAT_HOST_SOCKET", None)
os.environ.pop("KAOLA_ACP_DISPATCHER", None)

spec = importlib.util.spec_from_file_location("kaola_acp_holder_i388", HOLDER_PATH)
holder_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(holder_module)

HOST_ENTRY = "/kaola-project-runner"


class StubProc:
    pid = 3880


class StubAgent:
    """Prompt admission only; no turn is answered here."""

    def __init__(self) -> None:
        self.proc = StubProc()
        self.exited = threading.Event()
        self.exit_code = None
        self.exit_signal = None
        self.stderr_pump = None
        self.malformed_lines = 0
        self.handler_errors = 0
        self.pending_out: dict[int, str] = {}
        self.sent: list[dict] = []
        self.next_id = 0
        self.release_wait = threading.Event()

    def send_request(self, method: str, params: dict) -> int:
        self.next_id += 1
        self.pending_out[holder_module.normalize_id(self.next_id)] = method
        self.sent.append({"method": method, "id": self.next_id, "params": params})
        return self.next_id

    def send_message(self, message: dict) -> None:
        self.sent.append(message)

    def wait_response(self, request_id, timeout):
        self.release_wait.wait(timeout if timeout else 30)
        return None

    def prompts_sent(self) -> list[dict]:
        return [item for item in self.sent if item.get("method") == "session/prompt"]


class PayloadSelection(unittest.TestCase):
    """The delivery seam chooses by role, not by ``host_entry`` presence."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i388-payload-")
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()

    def tearDown(self) -> None:
        if getattr(self, "agent", None) is not None:
            self.agent.release_wait.set()
        self._tmp.cleanup()

    def holder(self, platform: str, role: str | None, entry: str) -> "holder_module.Holder":
        args = argparse.Namespace(
            record_dir=str(self.root / f"record-{platform}-{role}-{bool(entry)}"),
            socket=str(self.root / "holder.sock"),
            platform=platform,
            session=f"{platform}-KPR-i388-{role or 'unknown'}",
            repo=str(self.repo),
            init_meta="",
            command="stub",
            host_entry=entry,
            host_name=platform,
            session_role=role,
            resume=False,
            use_continue=False,
        )
        holder = holder_module.Holder(args)
        self.agent = StubAgent()
        holder.agent = self.agent
        holder.acp_session_id = f"acp-{platform}-388"
        holder.state = "ready"
        holder.heartbeat_host = None
        # The relay is not under test; keep the delivery decision isolated.
        holder._relay_pass = lambda: {}
        return holder

    @staticmethod
    def stage(holder: "holder_module.Holder", kind: str, cursor: int,
              session: str | None = None, **extra) -> dict:
        event = {
            "schema": holder_module.WORKER_EVENT_SCHEMA,
            "event_id": f"{holder.args.platform}/{holder.args.session}/{kind}/{cursor}",
            "kind": kind,
            "platform": holder.args.platform,
            "session": session or holder.args.session,
            "repo": holder.args.repo,
            "reason": extra.pop("reason", f"outcome=turn_completed cursor={cursor}"),
            "event_cursor": cursor,
            "staged_at": 1.0,
            **extra,
        }
        holder.pending_worker_events.append(event)
        return event

    def deliver(self, holder: "holder_module.Holder") -> tuple[dict, str]:
        receipt = holder._deliver_worker_events()
        self.assertIs(receipt.get("delivered"), True, receipt)
        prompts = self.agent.prompts_sent()
        self.assertEqual(len(prompts), 1, prompts)
        return receipt, prompts[0]["params"]["prompt"][0]["text"]

    def assert_worker_notice(self, text: str, platform: str) -> None:
        first = text.splitlines()[0]
        self.assertTrue(first.startswith("kaola-worker-notify/1:"), first)
        self.assertIn(f"{platform} session", first)
        self.assertNotIn("kaola-host-notify/1", text)
        self.assertNotIn("<<<heartbeat-prompt", text)
        self.assertNotIn("Perform exactly one full Project Runner heartbeat pass", text)
        self.assertNotIn(HOST_ENTRY, text,
                         "a worker notice must not open the Host control-plane Skill")
        self.assertIn('"kind": "cwd_repaired"', text)
        self.assertIn('"kind": "idle"', text)

    def test_dsh_and_devin_worker_and_expert_get_the_compact_notice(self) -> None:
        for platform in ("dsh", "devin"):
            for role in ("worker", "expert"):
                for entry in (HOST_ENTRY, ""):
                    with self.subTest(platform=platform, role=role, entry=bool(entry)):
                        holder = self.holder(platform, role, entry)
                        # A cwd repair is holder-owned; the ordinary event is
                        # an inbound worker event. Both ride one self prompt.
                        self.stage(holder, "cwd_repaired", 1, host_owned=True,
                                   reason="the repaired tool cwd was <root>/gone")
                        self.stage(holder, "idle", 2, session="codex-w-1")
                        _, text = self.deliver(holder)
                        self.assert_worker_notice(text, platform)

    def test_legacy_entry_on_a_worker_or_expert_never_reaches_the_carrier(self) -> None:
        # The exact live #388 shape: session_role says worker/expert, while the
        # spawn argv still carries the Host entry. The role guard wins.
        for platform, role in (("dsh", "worker"), ("devin", "expert")):
            with self.subTest(platform=platform, role=role):
                holder = self.holder(platform, role, HOST_ENTRY)
                self.stage(holder, "cwd_repaired", 3, host_owned=True)
                _, text = self.deliver(holder)
                self.assertEqual(text.splitlines()[0],
                                 f"kaola-worker-notify/1: {platform} session "
                                 f"{platform}-KPR-i388-{role}")
                self.assertNotIn("heartbeat carrier", text)

    def test_host_role_still_receives_the_full_carrier(self) -> None:
        for platform in ("dsh", "devin"):
            with self.subTest(platform=platform):
                holder = self.holder(platform, "host", HOST_ENTRY)
                self.stage(holder, "cwd_repaired", 4, host_owned=True)
                self.stage(holder, "idle", 5, session="codex-w-2")
                _, text = self.deliver(holder)
                lines = text.splitlines()
                self.assertEqual(lines[0], HOST_ENTRY)
                self.assertEqual(
                    lines[1],
                    f"kaola-host-notify/1: event-driven heartbeat carrier ({platform} Host)")
                self.assertIn("<<<heartbeat-prompt", text)
                self.assertIn("Perform exactly one full Project Runner heartbeat pass", text)
                self.assertNotIn("kaola-worker-notify/1", text)
                self.assertIn('"kind": "cwd_repaired"', text)
                self.assertIn('"kind": "idle"', text)

    def test_sideagent_holder_gets_the_compact_notice_and_its_node_batch_is_separate(self) -> None:
        # A node-mode Sideagent has its own Host-authored batch prompt. Its own
        # staged events must still never become a Host carrier self-prompt.
        holder = self.holder("dsh", "sideagent", HOST_ENTRY)
        self.stage(holder, "cwd_repaired", 6, host_owned=True)
        self.stage(holder, "idle", 7, session="codex-w-3")
        _, text = self.deliver(holder)
        self.assert_worker_notice(text, "dsh")
        batch = holder._node_prompt("b-i388", 0, 0)
        self.assertTrue(batch.startswith(f"{holder_module.RELAY_SCHEMA}:"), batch)
        self.assertNotIn("kaola-host-notify/1", batch)
        self.assertNotIn("kaola-worker-notify/1", batch)


class StartArgv(unittest.TestCase):
    """The CLI start seam: non-Host holders are started without the entry."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i388-start-")
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.record_root = self.root / "records"
        self.started: list[tuple[str, str, str]] = []

    def tearDown(self) -> None:
        for platform, session, repo in self.started:
            self.cli(platform, "stop", "--force", session=session, check=False,
                     repo=repo)
        time.sleep(0.2)
        self._tmp.cleanup()

    def env(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_")}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        return env

    def cli(self, platform: str, command: str, *args: str, session: str,
            check: bool = True, repo: str | None = None) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), platform, command,
             "--repo", repo or str(self.repo), "--session", session, *args],
            capture_output=True, text=True, env=self.env(), timeout=90,
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command} rc={result.returncode} stdout={result.stdout!r} "
                      f"stderr={result.stderr!r}")
        if check:
            self.assertNotIn("error", receipt, receipt)
            self.assertNotEqual(receipt.get("result"), "refused", receipt)
        return receipt

    def start(self, platform: str, session: str, command: str, *args: str) -> dict:
        receipt = self.cli(platform, "start", "--command", command, *args, session=session)
        self.started.append((platform, session, str(self.repo)))
        return receipt

    def record(self, platform: str, session: str) -> dict:
        found = list(self.record_root.rglob("record.json"))
        for path in found:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("platform") == platform and data.get("session") == session:
                return data
        self.fail(f"no record for {platform}/{session}; found {found}")

    def holder_argv(self, pid: int) -> str:
        result = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            capture_output=True, text=True,
        )
        text = result.stdout.strip()
        if result.returncode != 0 or not text:
            self.fail(f"cannot read holder argv for pid {pid}: rc={result.returncode} "
                      f"stdout={result.stdout!r} stderr={result.stderr!r}")
        return text

    def assert_role_and_entry(self, platform: str, session: str, role: str,
                              carrier: bool) -> dict:
        record = self.record(platform, session)
        self.assertEqual(record.get("session_role"), role, record)
        if carrier:
            self.assertEqual(record.get("host_skill_entry"), HOST_ENTRY, record)
        else:
            self.assertEqual(record.get("host_skill_entry"), "", record)
        argv = self.holder_argv(record["holder_pid"])
        if carrier:
            self.assertIn("--host-entry", argv)
        else:
            self.assertNotIn("--host-entry", argv,
                             "a non-Host start must not pass the Host entry")
        return record

    def mock(self, scenario: str = "normal", *extra: str) -> str:
        parts = [sys.executable, str(MOCK), "--scenario", scenario, *extra]
        return " ".join(parts)

    def test_dsh_worker_start_omits_host_entry(self) -> None:
        session = f"dsh-KPR-i388-worker-{os.getpid()}"
        self.start("dsh", session, self.mock(), "--tier", "default")
        self.assert_role_and_entry("dsh", session, "worker", carrier=False)

    def test_devin_worker_and_expert_starts_omit_host_entry(self) -> None:
        worker = f"devin-KPR-i388-worker-{os.getpid()}"
        expert = f"devin-KPR-i388-expert-{os.getpid()}"
        self.start("devin", worker,
                   self.mock("normal", "--caps", "strict-config", "--model", "swe-2-max"),
                   "--tier", "default", "--mode", "agent")
        self.assert_role_and_entry("devin", worker, "worker", carrier=False)
        self.start("devin", expert,
                   self.mock("normal", "--caps", "strict-config", "--model",
                             "fusion-claude-fable-5-1-high-sidekick-swe-2-medium"),
                   "--tier", "fable", "--mode", "agent")
        self.assert_role_and_entry("devin", expert, "expert", carrier=False)

    def test_host_start_still_passes_and_records_the_entry(self) -> None:
        for platform in ("dsh", "devin"):
            with self.subTest(platform=platform):
                # One live Host per repository; each platform gets its own.
                self.repo = self.root / f"host-repo-{platform}"
                self.repo.mkdir()
                subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
                session = f"{platform}-KPR-orchestrator-rolecheck-{os.getpid()}"
                if platform == "devin":
                    self.start(
                        platform, session,
                        self.mock("normal", "--caps", "strict-config",
                                  "--model", "swe-2-max"),
                        "--tier", "default", "--mode", "agent")
                else:
                    self.start(platform, session, self.mock(), "--tier", "default")
                self.assert_role_and_entry(platform, session, "host", carrier=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
