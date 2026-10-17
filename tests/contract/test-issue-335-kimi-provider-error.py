#!/usr/bin/env python3
"""Issue #335: a kimi-cli turn_failed must carry a provider-error summary.

kimi-cli 2.2.0 answers an auth failure as JSON-RPC -32000. The message is
either real text or the upstream ``[object Object]`` stringification, so the
ACP text can be empty of the provider error that ``wire.jsonl`` still has.

The fake ACP agent (this file, ``--mock-agent``) drives that shape. The suite
plants a kimi wire under ``KIMI_CODE_HOME`` and checks the holder record:

  (a) a provider error on wire.jsonl is copied, redacted, onto the durable
      ``turn_ended`` event and ``record.json`` ``turn_error``;
  (b) a missing wire, or a wire with no provider error, degrades to an
      explicit unavailable marker and does not invent ``provider.auth_error``;
  (c) secrets in the message and in ``details`` stay out of both records.

A usable ACP message is kept and is not replaced by the wire.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "scripts" / "kaola-acp.py"
MOCK_AGENT = REPO / "tests" / "contract" / "mock-acp-agent.py"

SECRET = "sk-LIVEKEY99999999"
SECRET_COOKIE = "rawsecret-335-COOKIE"
SECRET_KEY = "rawsecret-335-KEY"
USAGE = "403 You've reached your 5-hour usage limit."
USABLE_ACP = "Authentication required: " + USAGE
TAIL = "TAILMARKER335"
OLDER = "429 older-limit-should-lose"
INTERRUPTED = "403 interrupted-draft-should-lose"


def kimi_workdir_key(work_dir: str) -> str:
    """Same formula as kimi-cli 2.2.0 ``encodeWorkDirKey`` (not realpath)."""
    normalized = work_dir.replace("\\", "/").rstrip("/")
    name = normalized.rsplit("/", 1)[-1] if normalized else ""
    slug = re.sub(r"[^a-z0-9._-]+", "-", name.lower())
    slug = re.sub(r"^-+|-+$", "", slug)
    slug = slug[:40]
    slug = re.sub(r"^-+|-+$", "", slug)
    if slug in ("", ".", ".."):
        slug = "workspace"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"wd_{slug}_{digest}"


def _wire_lines() -> list[str]:
    """Oldest first. The latest structured provider error must win."""
    message = (
        f"{USAGE} Authorization: Bearer {SECRET} "
        f"Cookie: sid={SECRET_COOKIE} api_key={SECRET_KEY} "
        + ("x" * 500)
        + TAIL
    )
    rows = [
        {"type": "turn.step.retrying", "errorName": "APIConnectionError",
         "errorMessage": "terminated"},
        {"type": "turn.ended", "reason": "failed", "agentId": "main",
         "error": {"code": "provider.rate_limit", "message": OLDER,
                   "details": {"statusCode": 429}}},
        {"type": "turn.step.interrupted", "reason": "failed", "agentId": "main",
         "message": f"[provider.auth_error] {INTERRUPTED}"},
        {"type": "turn.ended", "reason": "failed", "agentId": "main",
         "turnId": 7, "durationMs": 12,
         "error": {
             "code": "provider.auth_error",
             "message": message,
             "name": "APIStatusError",
             "retryable": False,
             "details": {
                 "statusCode": 403,
                 "Authorization": f"Bearer {SECRET}",
                 "api_key": SECRET_KEY,
                 "requestId": None,
             },
         }},
    ]
    return [json.dumps(row, ensure_ascii=False) for row in rows]


def _run_mock(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acp-error", default="object",
                        choices=("object", "empty", "usable"))
    args, _ = parser.parse_known_args(argv)
    spec = importlib.util.spec_from_file_location("mock_acp_base_335", MOCK_AGENT)
    assert spec is not None and spec.loader is not None
    mock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mock)
    agent = mock.MockAgent(scenario="normal", caps=set(), turn_ms=0, flood_bytes=0)
    orig_on_prompt = agent.on_prompt

    def on_prompt(request_id: Any, params: dict[str, Any]) -> None:
        text = " ".join(
            part.get("text", "")
            for part in params.get("prompt", [])
            if isinstance(part, dict)
        )
        if "KAOLA_335_OK" in text:
            orig_on_prompt(request_id, params)
            return
        agent.begin_turn(request_id, params.get("sessionId", ""))
        if args.acp_error == "usable":
            error: dict[str, Any] = {"code": -32000, "message": USABLE_ACP}
        elif args.acp_error == "empty":
            error = {"code": -32000, "message": ""}
        else:
            error = {"code": -32000, "message": "[object Object]"}
        mock.respond(request_id, error=error)
        with agent.lock:
            agent.active_turn = None

    agent.on_prompt = on_prompt
    return agent.serve()


if __name__ == "__main__" and "--mock-agent" in sys.argv:
    index = sys.argv.index("--mock-agent")
    raise SystemExit(_run_mock(sys.argv[index + 1:]))


class KimiProviderErrorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i335-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.kimi_home = self.root / "kimi-home"
        self.kimi_home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.record_root = self.root / "records"
        self.record_root.mkdir()
        self.session: str | None = None

    def tearDown(self) -> None:
        if self.session:
            self.acp("stop", "--force", check=False, timeout=30)
        self.tmp.cleanup()

    def env(self) -> dict[str, str]:
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("KAOLA_") or key == "KAOLA_LAUNCH_BACKEND"
        }
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy",
                    "https_proxy", "all_proxy", "KAOLA_ACP_DISPATCHER"):
            env.pop(key, None)
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["HOME"] = str(self.home)
        env["KIMI_CODE_HOME"] = str(self.kimi_home)
        return env

    def command(self, acp_error: str) -> str:
        return (f"{sys.executable} {Path(__file__).resolve()} --mock-agent "
                f"--acp-error {acp_error}")

    def acp(self, command: str, *args: str, acp_error: str = "object",
            check: bool = True, timeout: float = 60) -> tuple[int, dict[str, Any]]:
        argv = [
            sys.executable, str(CLI), "kimi-cli", command,
            "--repo", str(self.repo), "--session", self.session or "",
            "--command", self.command(acp_error), *args,
        ]
        proc = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(), timeout=timeout,
        )
        try:
            receipt = json.loads(proc.stdout)
        except ValueError:
            self.fail(f"kaola-acp {command} not JSON: {proc.stdout!r} stderr={proc.stderr!r}")
        if check:
            self.assertNotIn("error", receipt, f"{command} failed: {receipt.get('error')}")
            self.assertNotEqual(receipt.get("result"), "refused", f"{command} refused: {receipt}")
        return proc.returncode, receipt

    def start(self, suffix: str, acp_error: str) -> dict[str, Any]:
        self.session = f"kimi-cli-w335-{suffix}"
        _, receipt = self.acp("start", acp_error=acp_error)
        self.assertTrue(receipt.get("acp_session_id"), receipt)
        return self.holder_record()

    def holder_record(self) -> dict[str, Any]:
        base = self.record_root / "kimi-cli" / (self.session or "")
        return json.loads(next(base.rglob("record.json")).read_text(encoding="utf-8"))

    def record_dir(self) -> Path:
        base = self.record_root / "kimi-cli" / (self.session or "")
        return next(base.rglob("record.json")).parent

    def events(self) -> list[dict[str, Any]]:
        path = self.record_dir() / "events.jsonl"
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def serialized(self) -> str:
        directory = self.record_dir()
        parts = [(directory / "record.json").read_text(encoding="utf-8")]
        for path in sorted(directory.glob("events.jsonl*")):
            parts.append(path.read_text(encoding="utf-8"))
        return "\n".join(parts)

    def plant_wire(self, record: dict[str, Any], lines: list[str] | None) -> Path:
        repo = record["repo"]
        session_id = record["acp_session_id"]
        self.assertIsInstance(repo, str)
        self.assertIsInstance(session_id, str)
        path = (self.kimi_home / "sessions" / kimi_workdir_key(repo) / session_id
                / "agents" / "main" / "wire.jsonl")
        path.parent.mkdir(parents=True)
        if lines is not None:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def failed_turn(self) -> dict[str, Any]:
        _, receipt = self.acp("send", "--text", "quota check", "--wait", check=False)
        self.assertEqual(receipt.get("outcome"), "turn_failed", receipt)
        self.assertIsNone(receipt.get("stop_reason"), receipt)
        ended = [row for row in self.events() if row.get("kind") == "turn_ended"]
        self.assertEqual(len(ended), 1, ended)
        self.assertEqual(ended[0].get("outcome"), "turn_failed")
        self.assertIsNone(ended[0].get("stop_reason"))
        return ended[0]

    def assert_no_secrets(self) -> None:
        blob = self.serialized()
        for secret in (SECRET, SECRET_COOKIE, SECRET_KEY, "LIVEKEY99999999"):
            self.assertNotIn(secret, blob)

    def test_wire_provider_error_is_recorded_and_redacted(self) -> None:
        record = self.start("wire", "object")
        self.plant_wire(record, _wire_lines())
        ended = self.failed_turn()
        error = ended.get("error")
        self.assertIsInstance(error, dict, ended)
        self.assertEqual(error.get("source"), "kimi-wire")
        self.assertEqual(error.get("code"), "provider.auth_error")
        self.assertEqual(error.get("status"), 403)
        message = error.get("message")
        self.assertIsInstance(message, str)
        self.assertIn("5-hour usage limit", message)
        self.assertIn("<redacted>", message)
        self.assertNotIn(TAIL, message)
        self.assertNotIn(OLDER, message)
        self.assertNotIn(INTERRUPTED, message)
        self.assertLessEqual(len(message), 400)
        stored = self.holder_record()
        self.assertEqual(stored.get("turn_error"), error)
        self.assertIsNone(stored.get("fatal_error"))
        self.assertEqual(stored.get("state"), "ready")
        self.assert_no_secrets()

        _, ok = self.acp("send", "--text", "KAOLA_335_OK", "--wait")
        self.assertEqual(ok.get("outcome"), "turn_completed", ok)
        ended_all = [row for row in self.events() if row.get("kind") == "turn_ended"]
        self.assertEqual(
            [row.get("outcome") for row in ended_all],
            ["turn_failed", "turn_completed"],
            ended_all,
        )
        self.assertEqual(ended_all[0].get("error"), error)
        self.assertNotIn("error", ended_all[1])
        self.assertIsNone(self.holder_record().get("turn_error"))
        self.assert_no_secrets()

    def test_missing_or_barren_wire_degrades(self) -> None:
        self.start("missing", "empty")
        ended = self.failed_turn()
        error = ended.get("error")
        self.assertEqual(error, {
            "source": "unavailable",
            "code": "provider-error-unavailable",
            "message": "no provider error available",
            "reason": "wire-missing",
        })
        self.assertEqual(self.holder_record().get("turn_error"), error)
        self.assertIsNone(self.holder_record().get("fatal_error"))
        self.assertNotIn("provider.auth_error", self.serialized())
        self.acp("stop", "--force", check=False)
        self.session = None

        record = self.start("barren", "object")
        path = self.plant_wire(record, None)
        path.write_text(
            "this is not json\n"
            "{\"type\":\"turn.step.retrying\",\"errorMessage\":\"terminated\"}\n"
            "{\"type\":\"turn.ended\",\"reason\":\"failed\"}\n",
            encoding="utf-8",
        )
        ended = self.failed_turn()
        error = ended.get("error")
        self.assertEqual(error.get("source"), "unavailable")
        self.assertEqual(error.get("code"), "provider-error-unavailable")
        self.assertEqual(error.get("message"), "no provider error available")
        self.assertEqual(error.get("reason"), "wire-no-provider-error")
        self.assertEqual(self.holder_record().get("turn_error"), error)
        self.assertIsNone(self.holder_record().get("fatal_error"))
        self.assertEqual(self.holder_record().get("state"), "ready")
        self.assertNotIn("provider.auth_error", self.serialized())

    def test_wire_lookup_falls_back_without_escaping(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "holder_issue_335", REPO / "scripts" / "kaola-acp-holder.py")
        assert spec is not None and spec.loader is not None
        holder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(holder)
        repo = str(self.repo.resolve())
        bucket = kimi_workdir_key(repo)
        probe = type("Probe", (), {})()
        probe.args = type("Args", (), {"repo": repo, "platform": "kimi-cli"})()
        probe.acp_session_id = "mock-session-9"
        previous = os.environ.get("KIMI_CODE_HOME")
        os.environ["KIMI_CODE_HOME"] = str(self.kimi_home)
        try:
            alt = (self.kimi_home / "sessions" / bucket / "session_mock-session-9"
                   / "agents" / "main" / "wire.jsonl")
            alt.parent.mkdir(parents=True)
            alt.write_text(
                '{"type":"turn.ended","error":{"code":"provider.auth_error","message":"403 alt"}}\n',
                encoding="utf-8",
            )
            path, reason = holder.Holder._kimi_wire_file(probe)
            self.assertEqual(path, alt)
            self.assertEqual(reason, "")
            exact = self.kimi_home / "sessions" / bucket / "mock-session-9"
            exact.mkdir()
            path, reason = holder.Holder._kimi_wire_file(probe)
            self.assertIsNone(path)
            self.assertEqual(reason, "wire-missing")
            probe.acp_session_id = "../outside"
            outside = self.kimi_home / "outside" / "agents" / "main" / "wire.jsonl"
            outside.parent.mkdir(parents=True)
            outside.write_text("secret-outside\n", encoding="utf-8")
            path, reason = holder.Holder._kimi_wire_file(probe)
            self.assertIsNone(path)
            self.assertEqual(reason, "wire-missing")
        finally:
            if previous is None:
                os.environ.pop("KIMI_CODE_HOME", None)
            else:
                os.environ["KIMI_CODE_HOME"] = previous

    def test_usable_acp_text_wins_over_wire(self) -> None:
        record = self.start("acp", "usable")
        self.plant_wire(record, _wire_lines())
        ended = self.failed_turn()
        error = ended.get("error")
        self.assertEqual(error.get("source"), "acp")
        self.assertEqual(error.get("status"), 403)
        self.assertIn("5-hour usage limit", error.get("message") or "")
        self.assertNotIn("provider.auth_error", json.dumps(error))
        self.assertNotIn(OLDER, self.serialized())
        self.assertNotIn(SECRET, self.serialized())
        self.assertEqual(self.holder_record().get("turn_error"), error)
        self.assertIsNone(self.holder_record().get("fatal_error"))


if __name__ == "__main__":
    unittest.main()
