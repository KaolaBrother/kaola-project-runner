#!/usr/bin/env python3
"""Issue #33 contract: ``session_meta.configOptions`` reports current native truth.

After a successful ``session/set_config_option`` or a native
``config_option_update`` notification, observe/status must surface the
native-returned configOptions (its ``currentValue`` evidence), not the stale
initialization snapshot. Failed, timed-out, or fact-free responses must never
fabricate current configuration; new/load/resume keep their own native
response truth. The established baseline stays visible as
``initial_config_options``.

Fixtures are driven through ``MOCK_ACP_CONFIG`` (see mock-acp-agent.py).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CLI = PROJECT / "scripts" / "kaola-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-acp-agent.py"

CONFIG_ENV = "MOCK_ACP_CONFIG"
# opencode resolves to the CLI-native opening model: no implicit preset or
# mode-skip set_config_option calls, so fixtures fully control native state.
PLATFORM = "opencode"


def wait_for(predicate, timeout: float, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


def options(model: str, mode: str = "agent") -> list[dict]:
    """Native-shaped configOptions carrying ``currentValue`` evidence."""
    return [
        {"id": "model", "name": "Model", "type": "select",
         "currentValue": model,
         "options": [{"value": model, "name": model}]},
        {"id": "mode", "name": "Mode", "type": "select",
         "currentValue": mode,
         "options": [{"value": mode, "name": mode}]},
    ]


def current_value(option_list, option_id: str):
    for option in option_list or []:
        if isinstance(option, dict) and option.get("id") == option_id:
            return option.get("currentValue")
    return None


class Issue33ConfigMetaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CLI.is_file():
            raise AssertionError(f"missing ACP CLI at {CLI}")
        if not MOCK.is_file():
            raise AssertionError(f"missing mock agent at {MOCK}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="kaola-acp-i33-")
        cls.root = Path(cls._tmp.name)
        cls.repo = cls.root / "repo"
        cls.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=cls.repo, check=True)
        cls.record_root = cls.root / "records"
        cls.mock_log = cls.root / "mock-events.jsonl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.session = f"i33-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self._started = False

    def tearDown(self) -> None:
        if self._started:
            self.cli("stop", "--force", check=False, timeout=15)

    # -- helpers -------------------------------------------------------------

    def env(self, config: dict | None = None, pages: list[dict] | None = None) -> dict[str, str]:
        env = dict(os.environ)
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["MOCK_ACP_LOG"] = str(self.mock_log)
        if config is not None:
            env[CONFIG_ENV] = json.dumps(config)
        else:
            env.pop(CONFIG_ENV, None)
        if pages is not None:
            env["MOCK_ACP_LIST_PAGES"] = json.dumps(pages)
        else:
            env.pop("MOCK_ACP_LIST_PAGES", None)
        return env

    def mock_command(self, caps: str = "") -> str:
        parts = f"{sys.executable} {MOCK} --scenario normal"
        if caps:
            parts += f" --caps {caps}"
        return parts

    def cli(self, command: str, *args: str, check: bool = True, timeout: float = 30,
            caps: str = "", config: dict | None = None,
            pages: list[dict] | None = None) -> dict:
        argv = [
            sys.executable, str(CLI), PLATFORM, command,
            "--repo", str(self.repo), "--session", self.session,
            "--command", self.mock_command(caps),
            *args,
        ]
        result = subprocess.run(
            argv, capture_output=True, text=True, env=self.env(config, pages), timeout=timeout
        )
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            self.fail(
                f"kaola-acp {command} did not emit a JSON receipt\n"
                f"rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
            )
        if check and "error" in receipt:
            self.fail(f"kaola-acp {command} returned error {receipt['error']}\nreceipt={receipt}")
        return receipt

    def start(self, *args: str, caps: str = "", config: dict | None = None,
              pages: list[dict] | None = None) -> dict:
        receipt = self.cli("start", *args, caps=caps, config=config, pages=pages)
        self._started = True
        return receipt

    def record_dir(self) -> Path:
        repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(repo.encode("utf-8")).hexdigest()[:16]
        return self.record_root / PLATFORM / self.session / digest

    def record(self) -> dict:
        try:
            return json.loads((self.record_dir() / "record.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def holder_sock(self) -> Path:
        directory = self.record_dir()
        digest = hashlib.sha256(str(directory).encode("utf-8")).hexdigest()[:24]
        return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"

    def holder_op(self, op: str, params: dict, timeout: float = 15) -> dict:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            connection.settimeout(timeout)
            connection.connect(str(self.holder_sock()))
            payload = json.dumps({
                "op": op,
                "request_id": secrets.token_hex(8),
                "params": params,
            }).encode("utf-8") + b"\n"
            connection.sendall(payload)
            buffer = bytearray()
            while True:
                data = connection.recv(65536)
                if not data:
                    break
                buffer.extend(data)
                if b"\n" in buffer:
                    line, _, _ = buffer.partition(b"\n")
                    return json.loads(line.decode("utf-8"))
            if buffer:
                return json.loads(buffer.decode("utf-8"))
            return {"error": {"code": "holder-closed"}}
        finally:
            connection.close()

    def set_config(self, config_id: str, value, timeout: float = 15) -> dict:
        return self.holder_op(
            "set_config_option",
            {"config_id": config_id, "value": value},
            timeout=timeout,
        )

    def observed_options(self, command: str = "observe") -> list:
        receipt = self.cli(command, check=False)
        return (receipt.get("session_meta") or {}).get("configOptions") or []

    # -- tests ---------------------------------------------------------------

    def test_initial_new_config_is_current_baseline(self) -> None:
        baseline = options(model="init-model", mode="read-only")
        self.start(config={"new": baseline})
        obs = self.cli("observe")
        meta = obs.get("session_meta") or {}
        self.assertEqual(meta.get("configOptions"), baseline)
        self.assertEqual(obs.get("initial_config_options"), baseline)
        self.assertTrue(meta.get("sessionId"))
        status = self.cli("status")
        self.assertEqual(
            (status.get("session_meta") or {}).get("configOptions"), baseline)

    def test_successful_set_reports_native_not_requested(self) -> None:
        baseline = options(model="init-a", mode="read-only")
        native_b = options(model="native-b", mode="agent")
        self.start(config={"new": baseline,
                           "set_result": {"configOptions": native_b}})
        sid = self.cli("observe").get("acp_session_id")
        result = self.set_config("model", "requested-b")
        self.assertIsNone(result.get("error"), f"set failed: {result}")
        self.assertEqual(result.get("configured"), True)
        # the receipt attests the native currentValue, not the requested value
        self.assertEqual(result.get("current_value"), "native-b")
        for command in ("observe", "status"):
            receipt = self.cli(command)
            meta = receipt.get("session_meta") or {}
            self.assertEqual(meta.get("configOptions"), native_b,
                             f"{command} did not report native current options")
            self.assertEqual(receipt.get("initial_config_options"), baseline)
            self.assertEqual(receipt.get("acp_session_id"), sid)
            self.assertEqual(meta.get("sessionId"), sid)
        record = self.record()
        self.assertEqual(
            (record.get("session_meta") or {}).get("configOptions"), native_b)
        self.assertEqual(record.get("initial_config_options"), baseline)

    def test_start_model_flows_to_observe(self) -> None:
        baseline = options(model="init-default", mode="read-only")
        native_b = options(model="native-b", mode="agent")
        # Issue #119 (H2): an explicit opencode --model the agent does not then
        # report is refused and stopped (test-issue-119-host-entry.py), so this
        # flow requests the value the agent reports; the init-default baseline
        # still proves the post-set state is what reaches observe.
        receipt = self.start(
            "--model", "native-b",
            config={"new": baseline,
                    "set_result": {"configOptions": native_b}})
        configured = {
            entry.get("config_id"): entry
            for entry in receipt.get("configured_options") or []
        }
        self.assertEqual((configured.get("model") or {}).get("current_value"), "native-b")
        obs = self.cli("observe")
        self.assertEqual(
            current_value((obs.get("session_meta") or {}).get("configOptions"), "model"),
            "native-b")
        self.assertEqual(obs.get("initial_config_options"), baseline)

    def test_config_option_update_notification_updates_meta(self) -> None:
        baseline = options(model="init-a", mode="agent")
        native_b = options(model="native-b", mode="agent")
        notify_c = options(model="notify-c", mode="bypass")
        self.start(config={"new": baseline,
                           "set_result": {"configOptions": native_b},
                           "set_notify": notify_c})
        result = self.set_config("model", "wanted-b")
        self.assertIsNone(result.get("error"), f"set failed: {result}")
        landed = wait_for(
            lambda: current_value(self.observed_options(), "model") == "notify-c",
            8,
        )
        self.assertTrue(landed, "config_option_update notification never reached observe")
        obs = self.cli("observe")
        self.assertEqual((obs.get("session_meta") or {}).get("configOptions"), notify_c)
        self.assertEqual(obs.get("initial_config_options"), baseline)
        record = self.record()
        self.assertEqual(
            (record.get("session_meta") or {}).get("configOptions"), notify_c)

    def test_failed_set_keeps_prior_proven_state(self) -> None:
        baseline = options(model="init-a", mode="agent")
        self.start(config={"new": baseline,
                           "set_error": {"code": -32000, "message": "set refused"}})
        result = self.set_config("model", "wanted-b")
        self.assertEqual((result.get("error") or {}).get("code"), "config-option-failed")
        obs = self.cli("observe")
        meta = obs.get("session_meta") or {}
        self.assertEqual(meta.get("configOptions"), baseline)
        self.assertNotEqual(current_value(meta.get("configOptions"), "model"), "wanted-b")
        self.assertEqual(obs.get("initial_config_options"), baseline)

    def test_missing_result_facts_no_fabrication(self) -> None:
        baseline = options(model="init-a", mode="agent")
        self.start(config={"new": baseline, "set_result": {}})
        result = self.set_config("model", "wanted-b")
        self.assertIsNone(result.get("error"), f"set failed: {result}")
        self.assertNotIn("current_value", result)
        obs = self.cli("observe")
        meta = obs.get("session_meta") or {}
        # the fact-free response leaves the last proven state untouched
        self.assertEqual(meta.get("configOptions"), baseline)
        self.assertNotEqual(current_value(meta.get("configOptions"), "model"), "wanted-b")

    def test_timeout_keeps_prior_proven_state(self) -> None:
        baseline = options(model="init-a", mode="agent")
        self.start(config={"new": baseline, "set_drop": True})
        result = self.set_config("model", "wanted-b", timeout=30)
        self.assertEqual((result.get("error") or {}).get("code"), "config-option-timeout")
        obs = self.cli("observe")
        self.assertEqual((obs.get("session_meta") or {}).get("configOptions"), baseline)
        self.assertEqual(obs.get("initial_config_options"), baseline)

    def test_resume_reports_native_config_truth(self) -> None:
        resume_options = options(model="resume-model", mode="agent")
        pages = [{"sessions": [{
            "sessionId": "resume-target",
            "updatedAt": "2026-09-13T00:00:00.000Z",
            "cwd": str(self.repo),
        }]}]
        receipt = self.start(
            "--resume", "resume-target",
            caps="resume", config={"resume": resume_options}, pages=pages)
        self.assertEqual(receipt.get("acp_session_id"), "resume-target")
        obs = self.cli("observe")
        meta = obs.get("session_meta") or {}
        self.assertEqual(meta.get("configOptions"), resume_options)
        self.assertEqual(meta.get("sessionId"), "resume-target")
        self.assertEqual(obs.get("initial_config_options"), resume_options)

    def test_absent_config_options_not_invented(self) -> None:
        native_x = options(model="native-x", mode="agent")
        self.start(config={"new": None,
                           "set_result": {"configOptions": native_x}})
        obs = self.cli("observe")
        meta = obs.get("session_meta") or {}
        self.assertNotIn("configOptions", meta)
        self.assertIsNone(obs.get("initial_config_options"))
        result = self.set_config("model", "wanted-x")
        self.assertIsNone(result.get("error"), f"set failed: {result}")
        obs = self.cli("observe")
        self.assertEqual((obs.get("session_meta") or {}).get("configOptions"), native_x)
        self.assertIsNone(obs.get("initial_config_options"))


if __name__ == "__main__":
    unittest.main()
