#!/usr/bin/env python3
"""Issue #416: Hermes Agent (`hermes`) as the twelfth worker, offline only.

Every protocol fact is exercised offline against
``fake-hermes-acp-agent.py`` (built from the #415/#416 source-read surface):
the launch argv carries ``--yolo`` and never ``--accept-hooks`` and the
caller's ``HERMES_YOLO_MODE``/``HERMES_ACCEPT_HOOKS`` never reach the child;
``initialize`` loses ``sessionCapabilities.resume`` but keeps
``loadSession``; ``model``/``mode`` ``configOptions`` are synthesized from
``models``/``modes``; ``session/set_config_option`` for them becomes
``session/set_model``/``session/set_mode`` with real Hermes errors surfaced,
any other configId refused locally; a busy second prompt passes through; a
resume of an unknown id is refused -32002 instead of reporting a fresh
session; the uncredentialed path is ``login-required`` end to end; and the
manifest/static pins hold (verbatim profile, default+max Worker tiers, the
shipped adapter, unmeasured fields, no ``worker_grants``).
"""

from __future__ import annotations

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
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / "scripts"
WRAPPER = SCRIPTS / "kaola-hermes-acp.py"
MOCK = PROJECT / "tests" / "contract" / "fake-hermes-acp-agent.py"
MANIFEST = PROJECT / "platforms" / "hermes.yaml"
CLI = SCRIPTS / "kaola-acp.py"
SKILL = PROJECT / "skills" / "hermes-kaola-project-runner"

PROFILE = ("Fast, low-cost worker for self-contained tasks with clear goals, boundaries, "
           "acceptance criteria; strong at 3D and frontend; one-pass complete features; "
           "iterative validation, self-repair. Review each output; split long chain.")


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        matched = __import__("re").match(r'^([a-z_]+):\s*"(.*)"\s*$', line)
        if matched:
            values[matched.group(1)] = json.loads(f'"{matched.group(2)}"')
    return values


def hermes_grant_rows(node: Any, where: str) -> list[str]:
    """Hermes preset ids inside any `*grants` list (worker/elite/expert/Host rows)."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith("grants") and isinstance(value, list):
                for row in value:
                    if not isinstance(row, dict):
                        continue
                    listed = row.get("preset_ids")
                    ids = [row.get("id"), row.get("preset"),
                           *(listed if isinstance(listed, list) else [])]
                    found += [f"{where}.{key}: {i}" for i in ids
                              if isinstance(i, str) and i.startswith("hermes/")]
            found += hermes_grant_rows(value, f"{where}.{key}")
    elif isinstance(node, list):
        for value in node:
            found += hermes_grant_rows(value, where)
    return found


def hermetic_env(**extra: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("KAOLA_", "FAKE_HERMES", "HERMES_"))}
    env.update(extra)
    return env


class Wrapper:
    """An ACP client over the adapter's stdio, with the mock hermes behind it."""

    def __init__(self, test: unittest.TestCase, scenario: str = "ok",
                 extra_env: dict[str, str] | None = None) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-i416-")
        test.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cwd = root / "work"
        self.cwd.mkdir()
        self.log = root / "hermes.jsonl"
        env = hermetic_env(HERMES_BIN=str(MOCK), FAKE_HERMES_SCENARIO=scenario,
                           FAKE_HERMES_LOG=str(self.log), HOME=str(root))
        env.update(extra_env or {})
        self.proc = subprocess.Popen([sys.executable, str(WRAPPER)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, env=env)
        self.responses: dict[int, dict] = {}
        self.notifications: list[dict] = []
        self.cond = threading.Condition()
        self._next = 0
        threading.Thread(target=self._read, daemon=True).start()
        test.addCleanup(self.close)

    def _read(self) -> None:
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            with self.cond:
                if "id" in message and "method" not in message:
                    self.responses[message["id"]] = message
                else:
                    self.notifications.append(message)
                self.cond.notify_all()

    def send(self, method: str, params: dict | None = None) -> int:
        self._next += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self._next,
                                          "method": method, "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        return self._next

    def wait(self, rid: int, timeout: float = 20.0) -> dict:
        deadline = time.monotonic() + timeout
        with self.cond:
            while rid not in self.responses:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise AssertionError(f"no response to request {rid}")
                self.cond.wait(left)
            return self.responses[rid]

    def call(self, method: str, params: dict | None = None, timeout: float = 20.0) -> dict:
        return self.wait(self.send(method, params), timeout)

    def updates(self, kind: str) -> list[dict]:
        with self.cond:
            return [n["params"]["update"] for n in self.notifications
                    if n.get("method") == "session/update"
                    and n["params"]["update"].get("sessionUpdate") == kind]

    def spawns(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [e for e in map(json.loads, self.log.read_text().splitlines())
                if e["event"] == "spawn"]

    def requests(self, method: str | None = None) -> list[dict]:
        if not self.log.exists():
            return []
        events = [e for e in map(json.loads, self.log.read_text().splitlines())
                  if e["event"] == "request"]
        if method is not None:
            events = [e for e in events if e["method"] == method]
        return events

    def new_session(self) -> str:
        self.call("initialize", {"protocolVersion": 1})
        reply = self.call("session/new", {"cwd": str(self.cwd), "mcpServers": []})
        assert "result" in reply, reply
        return reply["result"]["sessionId"]

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        for stream in (self.proc.stdout, self.proc.stderr):
            if stream is not None:
                stream.close()


class LaunchAndCapabilities(unittest.TestCase):
    def test_launch_argv_is_yolo_acp_without_accept_hooks_or_caller_env(self) -> None:
        w = Wrapper(self, extra_env={"HERMES_YOLO_MODE": "never",
                                     "HERMES_ACCEPT_HOOKS": "1"})
        w.call("initialize", {"protocolVersion": 1})
        spawn = w.spawns()[0]
        argv = spawn["argv"]
        self.assertIn("--yolo", argv)
        self.assertIn("acp", argv)
        self.assertNotIn("--accept-hooks", argv)
        self.assertIs(spawn["env_yolo_mode"], False)
        self.assertIs(spawn["env_accept_hooks"], False)

    def test_initialize_drops_resume_but_keeps_loadsession(self) -> None:
        w = Wrapper(self)
        result = w.call("initialize", {"protocolVersion": 1})["result"]
        caps = result["agentCapabilities"]
        self.assertNotIn("resume", caps["sessionCapabilities"])
        self.assertIs(caps["loadSession"], True)
        self.assertIn("load", caps["sessionCapabilities"])
        self.assertIn("fork", caps["sessionCapabilities"])
        self.assertIn("list", caps["sessionCapabilities"])

    def test_session_new_synthesizes_model_and_mode_options(self) -> None:
        w = Wrapper(self)
        w.call("initialize", {"protocolVersion": 1})
        result = w.call("session/new", {"cwd": str(w.cwd)})["result"]
        options = {o["id"]: o for o in result["configOptions"]}
        self.assertEqual(sorted(options), ["mode", "model"])
        self.assertEqual(options["model"]["type"], "select")
        self.assertEqual(options["model"]["currentValue"], "deepseek:deepseek-flash")
        self.assertEqual(options["mode"]["currentValue"], "ask")
        self.assertIn("deepseek:deepseek-flash",
                      [o["value"] for o in options["model"]["options"]])
        self.assertIn("dont_ask", [o["value"] for o in options["mode"]["options"]])
        # The mock itself never advertised configOptions.
        self.assertNotIn("configOptions", result["models"])
        self.assertEqual(w.requests("session/set_config_option"), [])


class ConfigOptionTranslation(unittest.TestCase):
    def test_model_write_becomes_set_model_and_echoes_options(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        reply = w.call("session/set_config_option", {
            "sessionId": sid, "configId": "model", "value": "deepseek:deepseek-pro"})
        options = {o["id"]: o for o in reply["result"]["configOptions"]}
        self.assertEqual(options["model"]["currentValue"], "deepseek:deepseek-pro")
        sent = w.requests("session/set_model")
        self.assertEqual(sent[-1]["params"],
                         {"sessionId": sid, "modelId": "deepseek:deepseek-pro"})
        # The mock never saw a set_config_option for model or mode.
        self.assertEqual(w.requests("session/set_config_option"), [])

    def test_mode_write_becomes_set_mode_and_the_update_refreshes_cache(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        reply = w.call("session/set_config_option", {
            "sessionId": sid, "configId": "mode", "value": "dont_ask"})
        options = {o["id"]: o for o in reply["result"]["configOptions"]}
        self.assertEqual(options["mode"]["currentValue"], "dont_ask")
        sent = w.requests("session/set_mode")
        self.assertEqual(sent[-1]["params"],
                         {"sessionId": sid, "modeId": "dont_ask"})
        # The mock's current_mode_update notification is forwarded unchanged.
        self.assertTrue(any(u.get("currentModeId") == "dont_ask"
                            for u in w.updates("current_mode_update")))
        # A later model write echoes the mode the update refreshed.
        reply = w.call("session/set_config_option", {
            "sessionId": sid, "configId": "model", "value": "deepseek:deepseek-flash"})
        options = {o["id"]: o for o in reply["result"]["configOptions"]}
        self.assertEqual(options["mode"]["currentValue"], "dont_ask")

    def test_hermes_errors_surface_verbatim(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        reply = w.call("session/set_config_option", {
            "sessionId": sid, "configId": "model", "value": "deepseek:no-such"})
        self.assertEqual(reply["error"]["code"], -32602)
        self.assertIn("model not found", reply["error"]["message"])
        self.assertEqual(reply["error"]["data"], {"modelId": "deepseek:no-such"})

        # -32603 while a turn is busy.
        hold = w.send("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "hold 2"}]})
        time.sleep(0.3)
        reply = w.call("session/set_config_option", {
            "sessionId": sid, "configId": "model", "value": "deepseek:deepseek-pro"})
        self.assertEqual(reply["error"]["code"], -32603)
        w.wait(hold)

    def test_other_config_ids_are_refused_locally(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        reply = w.call("session/set_config_option", {
            "sessionId": sid, "configId": "reasoning_effort", "value": "high"})
        self.assertEqual(reply["error"]["code"], -32602)
        self.assertIn("reasoning_effort", reply["error"]["message"])
        self.assertIn("silently", reply["error"]["message"])
        self.assertEqual(w.requests("session/set_config_option"), [])


class ResumeAndPrompt(unittest.TestCase):
    def test_resume_of_unknown_id_is_refused_and_never_forwarded_as_resume(self) -> None:
        w = Wrapper(self)
        w.call("initialize", {"protocolVersion": 1})
        reply = w.call("session/resume", {"sessionId": "hermes-session-999"})
        self.assertEqual(reply["error"]["code"], -32002)
        self.assertIn("hermes-session-999", reply["error"]["message"])
        self.assertIn("not resumed", reply["error"]["message"])
        self.assertEqual(w.requests("session/resume"), [])
        self.assertEqual(w.requests("session/load")[-1]["params"]["sessionId"],
                         "hermes-session-999")

    def test_load_of_unknown_id_is_refused_and_known_id_loads_options(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        unknown = w.call("session/load", {"sessionId": "hermes-session-999"})
        self.assertEqual(unknown["error"]["code"], -32002)
        loaded = w.call("session/load", {"sessionId": sid})
        options = {o["id"]: o for o in loaded["result"]["configOptions"]}
        self.assertEqual(options["model"]["currentValue"], "deepseek:deepseek-flash")
        self.assertEqual(loaded["result"]["sessionId"], sid)

    def test_busy_second_prompt_passes_through(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        hold = w.send("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "hold 2"}]})
        time.sleep(0.3)
        reply = w.call("session/prompt",
                       {"sessionId": sid, "prompt": [{"type": "text", "text": "second"}]},
                       timeout=5)
        self.assertEqual(reply["result"]["stopReason"], "end_turn")
        self.assertTrue(any("Queued for the next turn" in
                            (u.get("content") or {}).get("text", "")
                            for u in w.updates("agent_message_chunk")))
        self.assertEqual(len(w.requests("session/prompt")), 2)
        w.wait(hold)


class LoginRequired(unittest.TestCase):
    def test_uncredentialed_session_new_is_the_32000_login_text(self) -> None:
        w = Wrapper(self, scenario="uncredentialed")
        w.call("initialize", {"protocolVersion": 1})
        error = w.call("session/new", {"cwd": str(w.cwd)})["error"]
        self.assertEqual(error["code"], -32000)
        self.assertIn("hermes acp --setup", error["message"])
        self.assertIn("hermes model", error["message"])
        self.assertIn("no resolved provider credential", error["message"])

    def test_authenticate_null_result_becomes_32000(self) -> None:
        w = Wrapper(self, scenario="uncredentialed")
        w.call("initialize", {"protocolVersion": 1})
        reply = w.call("authenticate", {"methodId": "hermes-setup"})
        self.assertEqual(reply["error"]["code"], -32000)
        self.assertIn("hermes acp --setup", reply["error"]["message"])


class EndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kaola-i416-e2e-")
        root = Path(os.path.realpath(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.home = root / "home"
        self.home.mkdir()
        self.hermes_home = root / "hermes-home"
        self.hermes_home.mkdir()
        self.records = root / "records"
        self.log = root / "hermes.jsonl"
        self.session = f"i416-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self.addCleanup(self.force_stop)

    def force_stop(self) -> None:
        try:
            self.acp("stop", "--force", timeout=30)
        except Exception:      # noqa: BLE001 - cleanup must never mask the test result
            pass

    def acp(self, command: str, *args: str, scenario: str = "ok",
            timeout: float = 120) -> dict[str, Any]:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home),
               "KAOLA_ACP_RECORD_ROOT": str(self.records), "KAOLA_LAUNCH_BACKEND": "direct",
               "HERMES_BIN": str(MOCK), "HERMES_HOME": str(self.hermes_home),
               "FAKE_HERMES_SCENARIO": scenario, "FAKE_HERMES_LOG": str(self.log)}
        result = subprocess.run(
            [sys.executable, str(CLI), "hermes", command, "--repo", str(self.repo),
             "--session", self.session, "--command", f"{sys.executable} {WRAPPER}", *args],
            capture_output=True, text=True, timeout=timeout, env=env)
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command}: rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}")

    def test_uncredentialed_start_is_login_required(self) -> None:
        receipt = self.acp("start", scenario="uncredentialed")
        self.assertEqual(receipt["error"]["code"], "login-required", receipt)
        self.assertIn("hermes acp --setup", receipt["error"]["message"])

    def test_credentialed_start_applies_model_and_mode_then_stops(self) -> None:
        receipt = self.acp("start")
        self.assertEqual(receipt["state"], "ready", receipt)
        applied = receipt["config_application"]
        self.assertEqual(applied["model"]["applied"], True, applied)
        self.assertEqual(applied["model"]["value"], "deepseek:deepseek-flash")
        self.assertEqual(applied["model"].get("requested_id"), "deepseek/deepseek-flash")
        self.assertEqual(applied["mode"]["applied"], True, applied)
        self.assertEqual(applied["mode"]["value"], "dont_ask")
        self.assertEqual(applied["effort"]["applied"], False, applied)
        self.assertEqual(applied["effort"]["reason"], "no-advertised-config-option")
        stopped = self.acp("stop")
        self.assertIs(stopped.get("stopped"), True, stopped)
        # KPR wrote nothing under $HERMES_HOME.
        self.assertEqual(list(self.hermes_home.iterdir()), [])


class StaticPins(unittest.TestCase):
    def test_manifest_tiers_profile_and_worker_class(self) -> None:
        values = manifest_values()
        self.assertEqual(values["named_tiers"], "max")
        self.assertEqual(values["default_model_class"], "Worker")
        self.assertEqual(values["max_model_class"], "Worker")
        self.assertEqual(values["default_model_name"], "DeepSeek V4.1 Flash 1017")
        self.assertEqual(values["default_model_id"], "deepseek/deepseek-flash")
        self.assertEqual(values["default_model_effort"], "high")
        self.assertEqual(values["max_model_id"], "deepseek/deepseek-flash")
        self.assertEqual(values["max_model_effort"], "max")
        self.assertEqual(values["default_model_profile"], PROFILE)
        self.assertEqual(values["max_model_profile"],
                         "Escalation level: use it when the Hermes Agent default "
                         "(DeepSeek V4.1 Flash 1017 high) cannot solve the task.")
        self.assertNotIn("_model_roles", "".join(values))
        self.assertNotIn("switch", "".join(values))

    def test_manifest_unmeasured_fields_stay_honest(self) -> None:
        values = manifest_values()
        for key in ("acp_quirks", "acp_verified_versions", "quit_text"):
            self.assertIn("unmeasured", values[key], key)
        self.assertEqual(values["native_steering"], "unknown")
        self.assertEqual(values["acp_steer_method"], "")
        self.assertEqual(values["acp_effort_config_id"], "")
        self.assertEqual(values["acp_fast_config_id"], "")
        self.assertEqual(values["acp_init_meta"], "")
        self.assertEqual(values["acp_wrapper_pin"], "")
        self.assertEqual(values["host_skill_entry"], "")
        self.assertEqual(values["continue_syntax"], "unsupported")
        self.assertEqual(values["acp_env_allowlist"], "HERMES_HOME")
        self.assertEqual(values["acp_login_requires_pty"], "true")

    def test_worker_list_includes_both_hermes_presets(self) -> None:
        profiles = (PROJECT / "skills" / "kaola-project-runner" / "references"
                    / "worker-profiles.md").read_text(encoding="utf-8")
        self.assertIn("`hermes/default`", profiles)
        self.assertIn("`hermes/max`", profiles)
        catalog = (PROJECT / "skills" / "kaola-project-runner" / "references"
                   / "profile-catalog.md").read_text(encoding="utf-8")
        self.assertIn("`hermes/default` | DeepSeek V4.1 Flash 1017 | effort=high", catalog)
        self.assertIn(PROFILE, catalog)

    def test_the_skill_ships_the_adapter(self) -> None:
        self.assertTrue((SKILL / "scripts" / "kaola-hermes-acp.py").is_file())
        self.assertEqual(
            (SKILL / "scripts" / "kaola-hermes-acp.py").read_bytes(), WRAPPER.read_bytes())

    def test_no_hermes_worker_grant_exists_anywhere_tracked(self) -> None:
        # Grant rows live in tracked JSON authorization records; a schema
        # field name in generated scripts is not a grant.
        listed = subprocess.run(
            ["git", "-C", str(PROJECT), "ls-files", "-z", "--", "*.json", "*.jsonl"],
            capture_output=True, text=True, check=True).stdout.split("\0")
        found: list[str] = []
        for name in filter(None, listed):
            text = (PROJECT / name).read_text(encoding="utf-8", errors="replace")
            for doc in (text.splitlines() if name.endswith(".jsonl") else [text]):
                try:
                    found += hermes_grant_rows(json.loads(doc), name)
                except ValueError:
                    continue
        self.assertEqual(found, [])

    def test_grant_scan_detects_hermes_grant_rows(self) -> None:
        # The guard must see real rows, so it cannot pass vacuously.
        sample = {"authorization": {
            "worker_grants": [{"preset_ids": ["hermes/default"], "count": 1}],
            "grants": [{"id": "hermes/max", "state": "granted", "count": 1},
                       {"id": "dsh/default", "count": 1}]},
            "fields": ["worker_grants", "elite_grants"]}
        self.assertEqual(sorted(hermes_grant_rows(sample, "x")),
                         ["x.authorization.grants: hermes/max",
                          "x.authorization.worker_grants: hermes/default"])

    def test_registration_facts(self) -> None:
        acp = load("kaola-acp")
        self.assertIn("hermes", acp.PLATFORMS)
        self.assertEqual(acp.ACP_SKIP_MODE["hermes"], "dont_ask")
        self.assertEqual(acp.BRIDGE_BINARY_ENV["hermes"], "HERMES_BIN")
        self.assertEqual(acp.HOST_SKILL_ENTRIES["hermes"], "")
        self.assertEqual(acp.SURVEY_RUNTIMES["hermes"],
                         ("Hermes Agent", "hermes", "HERMES_BIN"))
        self.assertNotIn("hermes", getattr(acp, "HOST_SKILL_DISCOVERY_DIRS", {}))
        locate = load("kaola-locate")
        self.assertIn("hermes", locate.WORKER_IDS)
        quota = load("kaola-quota")
        self.assertIn("hermes", quota.PLATFORM_ORDER)


if __name__ == "__main__":
    unittest.main()
