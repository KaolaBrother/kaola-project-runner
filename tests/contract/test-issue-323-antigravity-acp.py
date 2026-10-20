#!/usr/bin/env python3
"""Issue #323: Antigravity (`agy`) as the eleventh worker, through an in-repo ACP adapter.

agy ships no ACP server, so ``scripts/kaola-antigravity-acp.py`` bridges ACP to
agy's headless stream-json protocol. Every protocol fact is exercised offline
against ``mock-agy.py`` (built from agy's headless documentation, the real
unsigned-account sample and the live one-turn/two-turn/resume run recorded on
the issue); the live run itself is acceptance evidence, not part of this suite.
The suite pins:

* the wrapper protocol: initialize, session/new, a streamed turn with tool
  events, two turns on one process, model and mode changes replacing the child,
  resume with ``--conversation``, cancel through SIGINT, exact close;
* the effort rule: ``--effort`` is never passed, so a model slug that already
  carries its effort cannot be double-applied;
* login states: an unsigned or ineligible account is the recoverable
  ``login-required`` refusal through the real holder, with the verify URL in
  the receipt, and a generic start failure is never mislabeled as one;
* the manifest, registrations and the five KT answers that are facts of code
  (survey presence, quota package, preset id, runtime id).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
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
WRAPPER = SCRIPTS / "kaola-antigravity-acp.py"
MOCK = PROJECT / "tests" / "contract" / "mock-agy.py"
MANIFEST = PROJECT / "platforms" / "antigravity.yaml"
CLI = SCRIPTS / "kaola-acp.py"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^([a-z_]+):\s*"(.*)"\s*$', line)
        if match:
            values[match.group(1)] = json.loads(f'"{match.group(2)}"')
    return values


def hermetic_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("KAOLA_", "MOCK_AGY", "AGY_")) or (k == "KAOLA_LAUNCH_BACKEND" and v == "direct")}
    env.update(extra)
    return env


class Wrapper:
    """An ACP client over the wrapper's stdio, with the mock agy behind it."""

    def __init__(self, test: unittest.TestCase, scenario: str = "ok", window: str = "3",
                 binary: str | None = None, extra_env: dict[str, str] | None = None) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-i323-")
        test.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cwd = root / "work"
        self.cwd.mkdir()
        self.log = root / "agy.jsonl"
        env = hermetic_env(AGY_BIN=binary or str(MOCK), MOCK_AGY_SCENARIO=scenario,
                           MOCK_AGY_LOG=str(self.log), KAOLA_ANTIGRAVITY_START_WINDOW=window,
                           HOME=str(root))
        env.update(extra_env or {})
        self.proc = subprocess.Popen([sys.executable, str(WRAPPER), "--cwd", str(self.cwd)],
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
                msg = json.loads(line)
            except ValueError:
                continue
            with self.cond:
                if "id" in msg and "method" not in msg:
                    self.responses[msg["id"]] = msg
                else:
                    self.notifications.append(msg)
                self.cond.notify_all()

    def send(self, method: str, params: dict | None = None) -> int:
        self._next += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self._next, "method": method,
                                          "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        return self._next

    def wait(self, rid: int, timeout: float = 20.0) -> dict:
        deadline = time.monotonic() + timeout
        with self.cond:
            while rid not in self.responses:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise AssertionError(f"no response to request {rid}; stderr={self.stderr_tail()}")
                self.cond.wait(left)
            return self.responses[rid]

    def call(self, method: str, params: dict | None = None, timeout: float = 20.0) -> dict:
        return self.wait(self.send(method, params), timeout)

    def updates(self, kind: str) -> list[dict]:
        with self.cond:
            return [n["params"]["update"] for n in self.notifications
                    if n.get("method") == "session/update"
                    and n["params"]["update"].get("sessionUpdate") == kind]

    def spawns(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [e["argv"] for e in map(json.loads, self.log.read_text().splitlines()) if e["event"] == "spawn"]

    def events(self, name: str) -> list[dict]:
        if not self.log.exists():
            return []
        return [e for e in map(json.loads, self.log.read_text().splitlines()) if e["event"] == name]

    def stderr_tail(self) -> str:
        return ""

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


class WrapperProtocol(unittest.TestCase):
    def test_initialize_advertises_resume_close_and_steering(self) -> None:
        w = Wrapper(self)
        result = w.call("initialize", {"protocolVersion": 1})["result"]
        caps = result["agentCapabilities"]
        self.assertEqual(result["protocolVersion"], 1)
        self.assertEqual(result["authMethods"], [])
        self.assertIs(caps["sessionCapabilities"]["resume"], True)
        self.assertIs(caps["sessionCapabilities"]["close"], True)
        self.assertNotIn("list", caps["sessionCapabilities"])
        self.assertIs(caps["loadSession"], False)
        self.assertEqual(result.get("_meta", {}).get("steering"), {"supported": True})

    def test_session_new_spawns_the_documented_argv_without_effort(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        self.assertTrue(sid.startswith("antigravity-"))
        argv = w.spawns()[0]
        self.assertEqual(argv[:4], ["--input-format", "stream-json", "--output-format", "stream-json"])
        self.assertEqual(argv[argv.index("--print-timeout") + 1], "0s")
        self.assertEqual(argv[argv.index("--model") + 1], "gemini-4-argon-medium")
        self.assertNotIn("--effort", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)
        self.assertNotIn("--conversation", argv)
        self.assertNotIn("-p", argv)

    def test_session_new_reports_options_and_announces_the_native_conversation(self) -> None:
        w = Wrapper(self)
        w.call("initialize", {"protocolVersion": 1})
        result = w.call("session/new", {"cwd": str(w.cwd)})["result"]
        options = {o["id"]: o for o in result["configOptions"]}
        self.assertEqual(sorted(options), ["mode", "model"])
        self.assertEqual(options["model"]["currentValue"], "gemini-4-argon-medium")
        self.assertEqual(options["mode"]["currentValue"], "default")
        self.assertEqual([o["value"] for o in options["mode"]["options"]], ["default", "bypassPermissions"])
        self.assertIn("gemini-4-argon-low", [o["value"] for o in options["model"]["options"]])
        self.assertEqual(result["_meta"]["antigravity"]["start_probe"], "init")
        identity = w.updates("native_session_identity")
        self.assertEqual(len(identity), 1)
        self.assertRegex(identity[0]["nativeSessionId"], UUID)
        self.assertEqual(identity[0]["acpSessionId"], result["sessionId"])

    def test_nested_init_payload_is_read_too(self) -> None:
        w = Wrapper(self, scenario="nested-init")
        w.new_session()
        self.assertRegex(w.updates("native_session_identity")[0]["nativeSessionId"], UUID)

    def test_a_turn_streams_text_and_tool_events_and_ends(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        reply = w.call("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "hello"}]})
        self.assertEqual(reply["result"]["stopReason"], "end_turn")
        meta = reply["result"]["_meta"]["antigravity"]
        self.assertEqual((meta["agy_status"], meta["num_turns"]), ("SUCCESS", 1))
        text = "".join(u["content"]["text"] for u in w.updates("agent_message_chunk"))
        self.assertEqual(text, "echo: hello")          # the user_input echo is not agent output
        call = w.updates("tool_call")[0]
        self.assertEqual((call["title"], call["kind"], call["status"]), ("run_command", "execute", "in_progress"))
        self.assertEqual(call["rawInput"], {"command": "ls"})
        done = w.updates("tool_call_update")[0]
        self.assertEqual((done["toolCallId"], done["status"]), (call["toolCallId"], "completed"))
        self.assertEqual(done["content"][0]["content"]["text"], "file.txt")
        self.assertEqual(w.events("user")[0]["content"], "hello")

    def test_a_failed_tool_is_reported_failed(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        w.call("session/prompt", {"sessionId": sid, "prompt": "toolfail"})
        self.assertEqual(w.updates("tool_call_update")[0]["status"], "failed")

    def test_unstreamed_response_is_not_lost(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        w.call("session/prompt", {"sessionId": sid, "prompt": "nostream please"})
        text = "".join(u["content"]["text"] for u in w.updates("agent_message_chunk"))
        self.assertEqual(text, "echo: nostream please")

    def test_two_turns_share_one_process_and_one_conversation(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        first = w.call("session/prompt", {"sessionId": sid, "prompt": "one"})["result"]
        second = w.call("session/prompt", {"sessionId": sid, "prompt": "two"})["result"]
        self.assertEqual(len(w.spawns()), 1)
        self.assertEqual([e["content"] for e in w.events("user")], ["one", "two"])
        self.assertEqual(second["_meta"]["antigravity"]["num_turns"], 2)
        self.assertEqual(first["_meta"]["antigravity"]["conversation_id"],
                         second["_meta"]["antigravity"]["conversation_id"])

    def test_model_and_mode_changes_replace_the_child_before_the_next_prompt(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        for config, value in (("mode", "bypassPermissions"), ("model", "gemini-4-argon-low")):
            reply = w.call("session/set_config_option", {"sessionId": sid, "configId": config, "value": value})
            self.assertIn("result", reply, reply)
        self.assertEqual(len(w.spawns()), 1, "a change alone must not spawn")
        w.call("session/prompt", {"sessionId": sid, "prompt": "first"})
        argv = w.spawns()[1]
        self.assertEqual(argv[argv.index("--model") + 1], "gemini-4-argon-low")
        self.assertIn("--dangerously-skip-permissions", argv)
        self.assertNotIn("--effort", argv)
        self.assertNotIn("--conversation", argv, "no conversation exists before the first result")
        w.call("session/set_config_option", {"sessionId": sid, "configId": "model", "value": "gemini-4-argon-medium"})
        w.call("session/prompt", {"sessionId": sid, "prompt": "second"})
        argv = w.spawns()[2]
        self.assertEqual(argv[argv.index("--model") + 1], "gemini-4-argon-medium")
        self.assertEqual(argv[argv.index("--conversation") + 1],
                         w.updates("native_session_identity")[-1]["nativeSessionId"])

    def test_the_identity_announced_at_start_is_replaced_after_a_respawn(self) -> None:
        """Live agy: the start child is replaced before the first prompt (mode is
        applied after session/new), so its conversation id is provisional and the
        LAST native_session_identity is the resumable one."""
        w = Wrapper(self)
        sid = w.new_session()
        first = w.updates("native_session_identity")[-1]["nativeSessionId"]
        w.call("session/set_config_option", {"sessionId": sid, "configId": "mode", "value": "bypassPermissions"})
        w.call("session/prompt", {"sessionId": sid, "prompt": "hi"})
        ids = [u["nativeSessionId"] for u in w.updates("native_session_identity")]
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[-1])
        self.assertEqual(ids[0], first)

    def test_every_spawn_across_a_session_omits_effort(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        for value in ("gemini-4-argon-low", "claude-opus-5-5-high", "gpt-oss-120b-medium"):
            w.call("session/set_config_option", {"sessionId": sid, "configId": "model", "value": value})
            w.call("session/prompt", {"sessionId": sid, "prompt": value})
        self.assertGreaterEqual(len(w.spawns()), 4)
        self.assertFalse([a for a in w.spawns() if "--effort" in a])

    def test_option_validation(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        for params in ({"configId": "mode", "value": "plan"}, {"configId": "model", "value": "bad model!"},
                       {"configId": "effort", "value": "high"}, {"configId": "model", "value": ""}):
            reply = w.call("session/set_config_option", {"sessionId": sid, **params})
            self.assertEqual(reply["error"]["code"], -32602, params)

    def test_resume_uses_conversation_and_adopts_the_native_id(self) -> None:
        w = Wrapper(self)
        w.call("initialize", {"protocolVersion": 1})
        conversation = "3f2a9c1e-0b7d-4e55-9a41-1c2d3e4f5a6b"
        reply = w.call("session/resume", {"sessionId": conversation, "cwd": str(w.cwd)})["result"]
        self.assertEqual(reply["sessionId"], conversation)
        argv = w.spawns()[0]
        self.assertEqual(argv[argv.index("--conversation") + 1], conversation)
        turn = w.call("session/prompt", {"sessionId": conversation, "prompt": "again"})["result"]
        self.assertEqual(turn["_meta"]["antigravity"]["conversation_id"], conversation)
        self.assertRegex(json.dumps(w.updates("native_session_identity")), conversation)

    def test_resume_refuses_a_malformed_id_before_spawning(self) -> None:
        w = Wrapper(self)
        w.call("initialize", {"protocolVersion": 1})
        for bad in ("", "../x", "a b"):
            reply = w.call("session/resume", {"sessionId": bad})
            self.assertEqual(reply["error"]["code"], -32602)
        self.assertEqual(w.spawns(), [])

    def test_cancel_sends_sigint_and_resumes_next_turn_with_conversation(self) -> None:
        """Real agy 1.3.5 emits status ERROR with error: interrupted and exits 1 on
        SIGINT, persisting the conversation; the next prompt respawns with --conversation."""
        w = Wrapper(self)
        sid = w.new_session()
        conv = w.updates("native_session_identity")[-1]["nativeSessionId"]
        pending = w.send("session/prompt", {"sessionId": sid, "prompt": "hang"})
        deadline = time.monotonic() + 10
        while not w.events("user") and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.2)
        w.call("session/cancel", {"sessionId": sid})
        reply = w.wait(pending)
        self.assertEqual(reply["result"]["stopReason"], "cancelled")
        meta = reply["result"]["_meta"]["antigravity"]
        self.assertEqual(meta["agy_status"], "ERROR")
        self.assertEqual(meta["agy_error"], "interrupted")
        self.assertEqual(meta["conversation_id"], conv)
        self.assertEqual(len(w.events("sigint")), 1)
        again = w.call("session/prompt", {"sessionId": sid, "prompt": "after cancel"})
        self.assertEqual(again["result"]["stopReason"], "end_turn")
        respawn_argv = w.spawns()[-1]
        self.assertIn("--conversation", respawn_argv)
        self.assertEqual(respawn_argv[respawn_argv.index("--conversation") + 1], conv)

    def test_cancel_also_handles_documented_interrupted_status(self) -> None:
        w = Wrapper(self, scenario="legacy-interrupted")
        sid = w.new_session()
        pending = w.send("session/prompt", {"sessionId": sid, "prompt": "hang"})
        deadline = time.monotonic() + 10
        while not w.events("user") and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.2)
        w.call("session/cancel", {"sessionId": sid})
        reply = w.wait(pending)
        self.assertEqual(reply["result"]["stopReason"], "cancelled")
        self.assertEqual(reply["result"]["_meta"]["antigravity"]["agy_status"], "INTERRUPTED")

    def test_mid_turn_steering_writes_user_event_and_coalesces_turn_on_same_process(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        pending = w.send("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": "slow turn 1"}]})
        deadline = time.monotonic() + 10
        while not w.events("user") and time.monotonic() < deadline:
            time.sleep(0.02)
        steer = w.call("_session/steering", {
            "sessionId": sid,
            "prompt": [{"type": "text", "text": "steered follow-up"}],
            "_meta": {"steering": {"idleBehavior": "promptRequired", "expectedTurnId": pending}},
        })
        self.assertEqual(steer["result"], {"outcome": "written", "confirmation": "write-only"})
        reply = w.wait(pending)
        self.assertEqual(reply["result"]["stopReason"], "end_turn")
        self.assertEqual(reply["result"]["_meta"]["antigravity"]["num_turns"], 2)
        self.assertEqual(len(w.spawns()), 1, "mid-turn steer must not restart agy")
        self.assertEqual([e["content"] for e in w.events("user")], ["slow turn 1", "steered follow-up"])
        text = "".join(u["content"]["text"] for u in w.updates("agent_message_chunk"))
        self.assertEqual(text, "echo: slow turn 1echo: steered follow-up")
        tool_ids = [u["toolCallId"] for u in w.updates("tool_call")]
        self.assertEqual(len(tool_ids), 2)
        self.assertNotEqual(tool_ids[0], tool_ids[1], "coalesced segments must have distinct toolCallIds")

    def test_steering_idle_or_mismatched_turn_returns_prompt_required_without_writing(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        idle = w.call("_session/steering", {
            "sessionId": sid,
            "prompt": [{"type": "text", "text": "idle steer"}],
            "_meta": {"steering": {"idleBehavior": "promptRequired"}},
        })
        self.assertEqual(idle["result"]["outcome"], "promptRequired")
        self.assertEqual(idle["result"]["confirmation"], "none")
        self.assertEqual(w.events("user"), [])
        pending = w.send("session/prompt", {"sessionId": sid, "prompt": "hang"})
        deadline = time.monotonic() + 10
        while not w.events("user") and time.monotonic() < deadline:
            time.sleep(0.02)
        wrong = w.call("_session/steering", {
            "sessionId": sid,
            "prompt": [{"type": "text", "text": "wrong turn"}],
            "_meta": {"steering": {"expectedTurnId": pending + 99}},
        })
        self.assertEqual(wrong["result"]["outcome"], "promptRequired")
        self.assertEqual([e["content"] for e in w.events("user")], ["hang"])
        w.call("session/cancel", {"sessionId": sid})
        self.assertEqual(w.wait(pending)["result"]["stopReason"], "cancelled")

    def test_steering_refuses_leading_slash_without_interrupting_running_turn(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        pending = w.send("session/prompt", {"sessionId": sid, "prompt": "slow keep going"})
        deadline = time.monotonic() + 10
        while not w.events("user") and time.monotonic() < deadline:
            time.sleep(0.02)
        bad = w.call("_session/steering", {
            "sessionId": sid,
            "prompt": [{"type": "text", "text": "/model"}],
        })
        self.assertEqual(bad["error"]["code"], -32602)
        self.assertIn("slash command", bad["error"]["message"])
        reply = w.wait(pending)
        self.assertEqual(reply["result"]["stopReason"], "end_turn")
        self.assertEqual([e["content"] for e in w.events("user")], ["slow keep going"])

    def test_a_second_prompt_while_running_is_refused_not_overwritten(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        pending = w.send("session/prompt", {"sessionId": sid, "prompt": "hang"})
        time.sleep(0.5)
        busy = w.call("session/prompt", {"sessionId": sid, "prompt": "second"})
        self.assertEqual(busy["error"]["code"], -32010)
        w.call("session/cancel", {"sessionId": sid})
        self.assertEqual(w.wait(pending)["result"]["stopReason"], "cancelled")

    def test_a_leading_slash_is_refused_before_anything_is_written(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        for text in ("/model", "  /compact", "/kaola-project-runner"):
            reply = w.call("session/prompt", {"sessionId": sid, "prompt": text})
            self.assertEqual(reply["error"]["code"], -32602, text)
            self.assertIn("slash command", reply["error"]["message"])
        self.assertEqual(w.events("user"), [])
        ok = w.call("session/prompt", {"sessionId": sid, "prompt": "plain /not/leading"})
        self.assertEqual(ok["result"]["stopReason"], "end_turn")

    def test_close_ends_the_child_by_closing_stdin(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        self.assertEqual(w.call("session/close", {"sessionId": sid})["result"], {})
        deadline = time.monotonic() + 10
        while not w.events("stdin-closed") and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(len(w.events("stdin-closed")), 1)

    def test_unadvertised_methods_are_refused(self) -> None:
        w = Wrapper(self)
        sid = w.new_session()
        for method in ("session/list", "session/load", "session/set_mode"):
            self.assertEqual(w.call(method, {"sessionId": sid})["error"]["code"], -32601, method)

    def test_turn_error_statuses_are_not_success(self) -> None:
        for scenario, code in (("error-turn", -32603), ("waiting", -32603)):
            with self.subTest(scenario=scenario):
                w = Wrapper(self, scenario=scenario)
                sid = w.new_session()
                reply = w.call("session/prompt", {"sessionId": sid, "prompt": "x"})
                self.assertEqual(reply["error"]["code"], code, reply)
        w = Wrapper(self, scenario="error-turn")
        sid = w.new_session()
        message = w.call("session/prompt", {"sessionId": sid, "prompt": "x"})["error"]["message"]
        self.assertIn("invalid model selection", message)
        self.assertNotIn("login required", message)

    def test_child_death_mid_turn_is_an_error_naming_unknown_effects(self) -> None:
        w = Wrapper(self, scenario="die-mid")
        sid = w.new_session()
        reply = w.call("session/prompt", {"sessionId": sid, "prompt": "x"})
        self.assertEqual(reply["error"]["code"], -32603)
        self.assertIn("effects are unknown", reply["error"]["message"])
        self.assertIn("exit 1", reply["error"]["message"])
        self.assertEqual(reply["error"]["data"]["antigravity"]["agy_exit"], 1)

    def test_replacing_a_child_never_fails_the_new_prompt(self) -> None:
        """The replaced child's exit must not be read as the new turn dying."""
        w = Wrapper(self)
        sid = w.new_session()
        for i in range(3):
            w.call("session/set_config_option", {"sessionId": sid, "configId": "model",
                                                 "value": ("gemini-4-argon-low", "gemini-4-argon-high", "gemini-4-argon-medium")[i]})
            reply = w.call("session/prompt", {"sessionId": sid, "prompt": f"turn {i}"})
            self.assertEqual(reply["result"]["stopReason"], "end_turn", reply)


class LoginStates(unittest.TestCase):
    def test_unsigned_account_is_the_recoverable_login_required_error(self) -> None:
        w = Wrapper(self, scenario="unsigned")
        w.call("initialize", {"protocolVersion": 1})
        error = w.call("session/new", {"cwd": str(w.cwd)})["error"]
        # The holder maps -32000 and any message containing "auth" to login-required.
        self.assertEqual(error["code"], -32000)
        self.assertIn("auth", error["message"].lower())
        login = error["data"]["login"]
        self.assertEqual(login["kind"], "not-signed-in")
        self.assertIn("`agy`", login["recovery"])
        self.assertIsNone(login["verify_url"])
        self.assertEqual(error["data"]["antigravity"]["agy_status"], "ERROR")
        self.assertEqual(error["data"]["antigravity"]["agy_exit"], 1)

    def test_ineligible_account_carries_the_browser_verify_url(self) -> None:
        w = Wrapper(self, scenario="ineligible")
        w.call("initialize", {"protocolVersion": 1})
        error = w.call("session/new", {"cwd": str(w.cwd)})["error"]
        self.assertEqual(error["code"], -32000)
        login = error["data"]["login"]
        self.assertEqual(login["kind"], "account-not-eligible")
        self.assertEqual(login["verify_url"], "https://accounts.example.test/verify?session=abc123")
        self.assertIn("Verify URL: https://accounts.example.test/verify?session=abc123", error["message"])
        self.assertNotIn("..", error["message"])

    def test_a_generic_start_failure_is_not_mislabeled_as_login(self) -> None:
        w = Wrapper(self, scenario="crash")
        w.call("initialize", {"protocolVersion": 1})
        error = w.call("session/new", {"cwd": str(w.cwd)})["error"]
        self.assertEqual(error["code"], -32603)
        self.assertNotIn("auth", error["message"].lower())
        self.assertIn("boom", error["message"])
        self.assertNotIn("login", error["data"])

    def test_refusal_discards_the_session_and_the_child(self) -> None:
        w = Wrapper(self, scenario="unsigned")
        w.call("initialize", {"protocolVersion": 1})
        w.call("session/new", {"cwd": str(w.cwd)})
        reply = w.call("session/prompt", {"sessionId": "antigravity-1", "prompt": "x"})
        self.assertEqual(reply["error"]["code"], -32602)       # unknown session
        self.assertEqual(w.events("user"), [])

    def test_a_quiet_child_is_kept_and_its_late_refusal_surfaces_on_the_turn(self) -> None:
        """If agy emits nothing at start (init may arrive only with the first
        turn), session/new still succeeds after the window and the refusal is
        reported as the turn's login-required error."""
        w = Wrapper(self, scenario="lazy-unsigned", window="0.4")
        w.call("initialize", {"protocolVersion": 1})
        result = w.call("session/new", {"cwd": str(w.cwd)})["result"]
        self.assertEqual(result["_meta"]["antigravity"]["start_probe"], "quiet")
        error = w.call("session/prompt", {"sessionId": result["sessionId"], "prompt": "x"})["error"]
        self.assertEqual(error["code"], -32000)
        self.assertEqual(error["data"]["login"]["kind"], "not-signed-in")

    def test_lazy_init_still_works_when_signed_in(self) -> None:
        w = Wrapper(self, scenario="lazy", window="0.4")
        sid = w.new_session()
        reply = w.call("session/prompt", {"sessionId": sid, "prompt": "hi"})
        self.assertEqual(reply["result"]["stopReason"], "end_turn")
        self.assertRegex(w.updates("native_session_identity")[0]["nativeSessionId"], UUID)

    def test_classification_table(self) -> None:
        module = load("kaola-antigravity-acp")
        cases = (
            ("Eligibility check failed: Your current account is not eligible", "", "account-not-eligible"),
            ("authentication failed or timed out", "Error: authentication required. Run 'agy' to log in", "not-signed-in"),
            ("authentication failed or timed out", "", "auth-failed-or-timed-out"),
            ("invalid model selection (--model x)", "", None),
            ("", "panic: nil pointer", None),
        )
        for error, stderr, kind in cases:
            with self.subTest(error=error, stderr=stderr):
                result = module.classify_login(error, stderr)
                self.assertEqual(result["kind"] if result else None, kind)

    def test_redaction_never_breaks_json_framing(self) -> None:
        module = load("kaola-antigravity-acp")
        for text in ('token=abc123def"', "Bearer abcdefghijklmnop", "ya29.a0AfH6SMBxyz", "api_key=sk-12345\\"):
            cleaned = module.redact(text)
            self.assertNotIn("abc123def", cleaned)
            json.dumps(cleaned)


class FailClosed(unittest.TestCase):
    def run_wrapper(self, **env: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(WRAPPER)], input="", capture_output=True, text=True,
                              timeout=30, env=hermetic_env(HOME=tempfile.gettempdir(), **env))

    def test_missing_absolute_binary_fails_closed(self) -> None:
        result = self.run_wrapper(AGY_BIN="/nonexistent/agy-323")
        self.assertEqual(result.returncode, 2)
        self.assertIn("fail-closed", result.stderr)

    def test_unfindable_bare_name_fails_closed(self) -> None:
        result = self.run_wrapper(AGY_BIN="agy-not-on-any-path-323", PATH="/usr/bin:/bin")
        self.assertEqual(result.returncode, 2)

    def test_invalid_print_timeout_falls_back_to_the_unit_form(self) -> None:
        w = Wrapper(self, extra_env={"KAOLA_ANTIGRAVITY_PRINT_TIMEOUT": "120"})   # a bare number is rejected by agy
        w.new_session()
        argv = w.spawns()[0]
        self.assertEqual(argv[argv.index("--print-timeout") + 1], "0s")

    def test_valid_print_timeout_override_is_passed_with_its_unit(self) -> None:
        w = Wrapper(self, extra_env={"KAOLA_ANTIGRAVITY_PRINT_TIMEOUT": "15m"})
        w.new_session()
        argv = w.spawns()[0]
        self.assertEqual(argv[argv.index("--print-timeout") + 1], "15m")


class SourceBoundaries(unittest.TestCase):
    """The deliberate non-capabilities, asserted on the code rather than described."""

    def setUp(self) -> None:
        self.source = WRAPPER.read_text(encoding="utf-8")
        self.code = re.sub(r'""".*?"""', "", self.source, flags=re.S)
        self.code = "\n".join(line.split("#", 1)[0] for line in self.code.splitlines())

    def test_never_touches_the_gemini_home(self) -> None:
        self.assertNotIn(".gemini", self.code)
        self.assertNotIn("expanduser", self.code)
        self.assertNotIn("Path.home", self.code)

    def test_no_network_login_or_catalog_client(self) -> None:
        for forbidden in ("import socket", "import urllib", "import http", "requests", "agy-acp",
                          '"models"', "'models'"):
            self.assertNotIn(forbidden, self.code, forbidden)
        # The one child ever spawned is the streaming agy; no login or model-list run.
        self.assertEqual(self.code.count("subprocess.Popen"), 1)
        self.assertNotIn("subprocess.run", self.code)

    def test_effort_flag_is_never_built(self) -> None:
        self.assertNotIn('"--effort"', self.code)
        self.assertNotIn("'--effort'", self.code)

    def test_the_only_binary_is_the_runner_resolved_agy_bin(self) -> None:
        self.assertIn('os.environ.get("AGY_BIN")', self.code)
        self.assertNotIn("shell=True", self.code)
        self.assertNotIn("os.system", self.code)


class ManifestAndRegistrations(unittest.TestCase):
    def setUp(self) -> None:
        self.values = manifest_values()
        self.acp = load("kaola-acp")

    def test_kt_item_1_runtime_id_and_display_name(self) -> None:
        self.assertEqual(self.values["id"], "antigravity")
        self.assertEqual(self.values["runtime_name"], "Antigravity")
        self.assertEqual(self.values["skill_name"], "antigravity-kaola-project-runner")
        self.assertEqual((self.values["binary_name"], self.values["binary_env"]), ("agy", "AGY_BIN"))
        self.assertIn("antigravity", self.acp.PLATFORMS)
        self.assertEqual(self.acp.PLATFORMS, tuple(sorted(self.acp.PLATFORMS)))

    def test_kt_item_2_two_tiers_and_effort_rule(self) -> None:
        self.assertEqual(self.values["default_model_id"], "gemini-4-argon-medium")
        self.assertEqual(self.values["default_model_name"], "Gemini 4 Argon")
        self.assertEqual(self.values["default_model_effort"], "medium")
        # Issue #390: the Argon tiers are general implementation workers and
        # must never review; antigravity/opus keeps its #343 wording.
        self.assertEqual(self.values["default_model_profile"],
                         "Strong implementation worker for well-scoped build tasks: features, UI and 3D, "
                         "frontend and backend code, refactors, and tests. Sometimes reports work, files, "
                         "or results that do not exist, so every output must be independently reviewed by "
                         "another seat before it is accepted. Never use as a reviewer, verifier, or for "
                         "acceptance decisions.")
        self.assertEqual(self.values["named_tiers"], "xhigh,opus")
        self.assertEqual(self.values["xhigh_model_id"], "gemini-4-argon-high")
        self.assertEqual(self.values["xhigh_model_name"], "Gemini 4 Argon")
        self.assertEqual(self.values["xhigh_model_effort"], "high")
        self.assertEqual(self.values["xhigh_model_class"], "Elite")
        self.assertEqual(self.values["xhigh_model_profile"],
                         "Higher-effort Argon tier for harder or larger implementation tasks; slower and "
                         "uses more quota. Same limits: every output must be independently reviewed by "
                         "another seat before it is accepted, and it must never be used as a reviewer, "
                         "verifier, or for acceptance decisions.")
        self.assertEqual(self.values["opus_model_id"], "claude-opus-5-5-high")
        self.assertEqual(self.values["opus_model_name"], "Claude Opus 5.5")
        self.assertEqual(self.values["opus_model_parameters"], "effort=high (encoded in model ID)")
        self.assertEqual(self.values["opus_model_effort"], "high")
        self.assertEqual(self.values["opus_model_class"], "Elite")
        self.assertEqual(self.values["opus_model_profile"],
                         "Strong at UI and 3D design implementation only; Opus level for UI and 3D work that "
                         "needs more depth than the Argon tiers. Do not use for any other task (research, design "
                         "docs, review, backend, debugging, investigation).")
        for tier in ("default", "xhigh"):
            profile = self.values[f"{tier}_model_profile"]
            self.assertIn("independently reviewed by another seat", profile, tier)
            self.assertIn("reviewer, verifier, or for acceptance decisions", profile, tier)
            self.assertNotIn("Do not use for any other task", profile, tier)
            for broad in ("generalist", "long context", "parallel agent", "architecture",
                          "root-cause", "final-quality", "Escalation level"):
                self.assertNotIn(broad, profile, tier)
        self.assertTrue(self.values["opus_model_profile"].startswith(
            "Strong at UI and 3D design implementation only"), "opus")
        # Effort rides the slug: the manifest declares no effort option, so the
        # Runner cannot apply the preset effort a second time.
        self.assertEqual(self.values["acp_effort_config_id"], "")
        self.assertEqual(self.values["acp_model_map"], "")
        self.assertEqual(self.values["fast_support"], "none")
        render = load("render-skills")
        parsed = render.parse_manifest(MANIFEST)
        self.assertEqual(render.preset_id(parsed, "default"), "antigravity/default")
        self.assertEqual(render.preset_id(parsed, "xhigh"), "antigravity/xhigh")
        self.assertEqual(render.preset_id(parsed, "opus"), "antigravity/opus")
        adapter = (SCRIPTS / "adapters" / "antigravity.sh").read_text(encoding="utf-8")
        for line in ('ADAPTER_DEFAULT_MODEL_ID="gemini-4-argon-medium"', 'ADAPTER_NAMED_TIERS="xhigh,opus"',
                     'ADAPTER_XHIGH_MODEL_ID="gemini-4-argon-high"',
                     'ADAPTER_OPUS_MODEL_NAME="Claude Opus 5.5"',
                     'ADAPTER_OPUS_MODEL_ID="claude-opus-5-5-high"',
                     'ADAPTER_OPUS_MODEL_EFFORT="high"'):
            self.assertIn(line, adapter)
        self.assertEqual(load("kaola-antigravity-acp").DEFAULT_MODEL, "gemini-4-argon-medium")

    def test_kt_item_3_survey_presence_for_installed_but_unsigned_in(self) -> None:
        """Survey runs no binary, so an installed CLI is `present` whether or not
        the account is signed in; sign-in is the ACP probe's `login_required`."""
        with tempfile.TemporaryDirectory(prefix="kaola-i323-survey-") as tmp:
            marker = Path(tmp) / "agy-was-executed"
            fake = Path(tmp) / "bin" / "agy"
            fake.parent.mkdir()
            fake.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            env = hermetic_env(PATH=f"{fake.parent}:/usr/bin:/bin", HOME=tmp, SHELL="/bin/sh")
            env.pop("AGY_BIN", None)
            out = subprocess.run([sys.executable, str(CLI), "survey", "--platform", "antigravity"],
                                 capture_output=True, text=True, timeout=60, env=env)
            row = json.loads(out.stdout)["platforms"][0]
            self.assertEqual(row["platform"], "antigravity")
            self.assertEqual((row["status"], row["installed"]), ("present", True))
            self.assertEqual(Path(row["path"]).name, "agy")
            self.assertFalse(marker.exists(), "survey must not run the platform binary")

    def test_kt_item_4_quota_package(self) -> None:
        quota = load("kaola-quota")
        catalog = quota.load_catalog("antigravity", SCRIPTS)
        self.assertEqual(catalog.public_packages(),
                         [{"id": "antigravity:account", "name": "Account", "windows": ["5h", "weekly"], "binds_models": True}])
        self.assertEqual(catalog.rule["kind"], "single")
        for model in ("gemini-4-argon-medium", "gemini-4-argon-high", "gemini-4-argon-low",
                      "claude-opus-5-5-high", "gpt-oss-120b-medium"):
            self.assertEqual(quota.resolve_model(catalog, model),
                             {"packageId": "antigravity:account", "status": "mapped"}, model)

        # Issue #329: both verified tiers (antigravity/default = gemini-4-argon-medium
        # and antigravity/xhigh = gemini-4-argon-high) map to the "Gemini Models"
        # quota group (`gemini-weekly` + `gemini-5h`), while 3p models map to
        # "Claude and GPT models" (`3p-weekly` + `3p-5h`).
        for scenario_name in ("ok", "inner-json"):
            for tier_model in ("gemini-4-argon-medium", "gemini-4-argon-high"):
                probed = quota.probe_antigravity_usage(
                    binary=str(MOCK),
                    model=tier_model,
                    env=hermetic_env(MOCK_AGY_SCENARIO=scenario_name),
                )
                self.assertEqual(probed["status"], "ok", (scenario_name, tier_model))
                self.assertEqual(probed["packageId"], "antigravity:account")
                self.assertEqual(probed["selected_group"], "Gemini Models")
                self.assertEqual(set(probed["windows"]), {"5h", "weekly"})
                self.assertEqual(probed["quota"]["window"], "weekly")
                self.assertAlmostEqual(probed["quota"]["remaining_fraction"], 0.9455534815788269, places=6)
                self.assertEqual(probed["quota"]["used"], 5.44)
                self.assertEqual(probed["quota"]["limit"], 100.0)
                self.assertEqual(probed["quota"]["remaining_percent"], 94.56)
                self.assertEqual(probed["quota"]["reset_at"], "2026-10-21T07:35:54Z")
                self.assertEqual(probed["windows"]["5h"]["bucket_id"], "gemini-5h")
                self.assertEqual(probed["windows"]["5h"]["used"], 7.21)
                self.assertEqual(probed["windows"]["5h"]["remaining_percent"], 92.79)
                self.assertEqual(probed["windows"]["5h"]["reset_at"], "2026-10-14T22:35:54Z")

        probed_3p = quota.probe_antigravity_usage(
            binary=str(MOCK),
            model="claude-opus-5-5-high",
            env=hermetic_env(MOCK_AGY_SCENARIO="ok"),
        )
        self.assertEqual(probed_3p["status"], "ok")
        self.assertEqual(probed_3p["selected_group"], "Claude and GPT models")
        self.assertEqual(probed_3p["quota"]["bucket_id"], "3p-weekly")
        self.assertEqual(probed_3p["quota"]["used"], 0.0)
        self.assertEqual(probed_3p["quota"]["remaining_percent"], 100.0)

        for unsigned_scenario in ("unsigned", "unsigned-oauth-wait"):
            unsigned = quota.probe_antigravity_usage(
                binary=str(MOCK),
                model="gemini-4-argon-medium",
                timeout=5.0,
                env=hermetic_env(MOCK_AGY_SCENARIO=unsigned_scenario),
            )
            self.assertEqual(unsigned["status"], "login_required", unsigned_scenario)
            self.assertIsNone(unsigned["quota"])

        ineligible = quota.probe_antigravity_usage(
            binary=str(MOCK),
            model="gemini-4-argon-high",
            env=hermetic_env(MOCK_AGY_SCENARIO="ineligible"),
        )
        self.assertEqual(ineligible["status"], "unavailable")
        self.assertIsNone(ineligible["quota"])

    def test_not_a_host_and_stream_json_steering(self) -> None:
        self.assertEqual(self.values["host_skill_entry"], "")
        self.assertEqual(self.acp.HOST_SKILL_ENTRIES["antigravity"], "")
        self.assertFalse(self.acp.host_capable("antigravity"))
        self.assertEqual((self.values["native_steering"], self.values["acp_steer_method"]),
                         ("supported", "_session/steering"))
        self.assertNotIn("steering_delivery", self.values)
        for token in ("_session/steering", "user", "write-only", "promptRequired", "--steer-mode interrupt"):
            self.assertIn(token, self.values["steering_summary"], token)

    def test_permission_default_is_the_one_skip_flag(self) -> None:
        self.assertEqual(self.acp.ACP_SKIP_MODE["antigravity"], "bypassPermissions")
        self.assertEqual(self.values["acp_mode_config_id"], "mode")
        self.assertEqual(self.acp.BRIDGE_BINARY_ENV["antigravity"], "AGY_BIN")
        self.assertIn("--dangerously-skip-permissions", self.values["permission_summary"])

    def test_survey_table_mirrors_the_manifest(self) -> None:
        self.assertEqual(self.acp.SURVEY_RUNTIMES["antigravity"], ("Antigravity", "agy", "AGY_BIN"))

    def test_verified_versions_claim_only_the_measured_live_scope(self) -> None:
        self.assertIn("live-one-turn-two-turn-resume-steer-cancel-usage", self.values["acp_verified_versions"])
        self.assertNotIn("steer-and-cancel-unverified", self.values["acp_verified_versions"])
        self.assertIn("provisional", self.values["acp_quirks"])
        self.assertIn("/usage", self.values["acp_quirks"])

    def test_the_wrapper_ships_inside_the_worker_skill_only(self) -> None:
        skill = PROJECT / "skills" / "antigravity-kaola-project-runner" / "scripts"
        self.assertEqual((skill / "kaola-antigravity-acp.py").read_bytes(), WRAPPER.read_bytes())
        for other in (PROJECT / "skills").iterdir():
            if other.name != "antigravity-kaola-project-runner" and other.is_dir():
                self.assertFalse((other / "scripts" / "kaola-antigravity-acp.py").exists(), other.name)


class RealRunnerIntegration(unittest.TestCase):
    """The whole path through kaola-acp.py and the real holder, over the mock agy."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-i323-run-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.home = root / "home"
        self.home.mkdir()
        self.records = root / "records"
        self.log = root / "agy.jsonl"
        self.session = f"i323-{self._testMethodName.lower()}-{os.getpid()}"[:79]
        self.scenario = "ok"
        # A refused start still leaves an error-state holder; stop every session.
        self.addCleanup(self.force_stop)

    def force_stop(self) -> None:
        try:
            self.acp("stop", "--force", timeout=30)
        except Exception:      # noqa: BLE001 - cleanup must never mask the test result
            pass

    def acp(self, command: str, *args: str, scenario: str | None = None, timeout: float = 90) -> dict[str, Any]:
        # A clean environment: the ambient dispatcher and Host identity of whoever
        # runs the suite must not reach this Runner.
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home),
               "KAOLA_ACP_RECORD_ROOT": str(self.records), "KAOLA_LAUNCH_BACKEND": "direct",
               "AGY_BIN": str(MOCK), "MOCK_AGY_SCENARIO": scenario or self.scenario,
               "MOCK_AGY_LOG": str(self.log), "KAOLA_ANTIGRAVITY_START_WINDOW": "3"}
        result = subprocess.run(
            [sys.executable, str(CLI), "antigravity", command, "--repo", str(self.repo),
             "--session", self.session, "--command", f"{sys.executable} {WRAPPER}", *args],
            capture_output=True, text=True, timeout=timeout, env=env)
        try:
            return json.loads(result.stdout)
        except ValueError:
            self.fail(f"{command}: rc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}")

    def spawns(self) -> list[list[str]]:
        return [e["argv"] for e in map(json.loads, self.log.read_text().splitlines()) if e["event"] == "spawn"]

    def test_unsigned_start_is_login_required_with_a_self_route(self) -> None:
        receipt = self.acp("start", scenario="unsigned")
        self.assertEqual(receipt["error"]["code"], "login-required", receipt)
        self.assertEqual(receipt["state"], "error")
        self.assertIn("agy", receipt["error"]["message"])
        self.assertIn("sign in", receipt["self_route"])
        self.assertIn("Do not retry credentials", receipt["self_route"])

    def test_ineligible_start_names_the_browser_verify_url_in_the_receipt(self) -> None:
        receipt = self.acp("start", scenario="ineligible")
        self.assertEqual(receipt["error"]["code"], "login-required", receipt)
        self.assertIn("https://accounts.example.test/verify?session=abc123", receipt["error"]["message"])
        self.assertIn("self_route", receipt)

    def test_preflight_reports_login_required_without_failing(self) -> None:
        receipt = self.acp("preflight", scenario="unsigned")
        self.assertIs(receipt.get("login_required"), True, receipt)
        self.assertNotIn("error", receipt)

    def test_generic_failure_is_not_login_required(self) -> None:
        receipt = self.acp("start", scenario="crash")
        self.assertEqual(receipt["error"]["code"], "acp-session-failed", receipt)
        self.assertNotIn("self_route", receipt)

    def test_one_turn_two_turn_stop_and_resume(self) -> None:
        started = self.acp("start")
        self.assertEqual(started["state"], "ready", started)
        applied = started["config_application"]
        self.assertEqual(applied["model"], {"applied": True, "config_id": "model", "value": "gemini-4-argon-medium"})
        self.assertEqual(applied["mode"]["value"], "bypassPermissions")
        # The preset effort is baked into the slug; no effort option exists to apply it twice,
        # and the accepted slug carries it, so it is applied through the model ID (Issue #331).
        self.assertEqual(applied["effort"], {"applied": True, "applied_via": "model-id", "value": "medium"})
        first = self.acp("send", "--text", "hello agy", "--timeout", "30")
        self.assertEqual((first["outcome"], first["stop_reason"], first["final_text"]),
                         ("turn_completed", "end_turn", "echo: hello agy"))
        second = self.acp("send", "--text", "second turn", "--timeout", "30")
        self.assertEqual(second["final_text"], "echo: second turn")
        spawns = [argv for argv in self.spawns() if "--input-format" in argv]
        self.assertTrue(all("--effort" not in argv for argv in spawns))
        turn_child = spawns[-1]
        self.assertIn("--dangerously-skip-permissions", turn_child)
        stopped = self.acp("stop")
        self.assertIs(stopped.get("stopped"), True, stopped)
        native = [json.loads(line)["update"]["nativeSessionId"]
                  for path in self.records.rglob("events.jsonl") for line in path.read_text().splitlines()
                  if "nativeSessionId" in line]
        self.assertTrue(native and all(re.match(UUID, n) for n in native))
        resumed = self.acp("start", "--resume", native[-1])
        self.assertEqual(resumed["state"], "ready", resumed)
        self.assertEqual(resumed["acp_session_id"], native[-1])
        third = self.acp("send", "--text", "after resume", "--timeout", "30")
        self.assertEqual(third["final_text"], "echo: after resume")
        resume_child = [argv for argv in self.spawns() if "--conversation" in argv][-1]
        self.assertEqual(resume_child[resume_child.index("--conversation") + 1], native[-1])
        self.assertNotIn("--effort", resume_child)

    def test_xhigh_tier_selects_the_high_slug_without_effort(self) -> None:
        started = self.acp("start", "--tier", "xhigh")
        self.assertEqual(started["state"], "ready", started)
        self.assertEqual(started["config_application"]["model"]["value"], "gemini-4-argon-high")
        self.assertEqual(started["config_application"]["effort"],
                         {"applied": True, "applied_via": "model-id", "value": "high"})
        self.acp("send", "--text", "hi", "--timeout", "30")
        child = [argv for argv in self.spawns() if "--input-format" in argv][-1]
        self.assertEqual(child[child.index("--model") + 1], "gemini-4-argon-high")
        self.assertNotIn("--effort", child)

    def test_opus_tier_selects_claude_opus_5_5_high_without_effort(self) -> None:
        started = self.acp("start", "--tier", "opus")
        self.assertEqual(started["state"], "ready", started)
        self.assertEqual(started["config_application"]["model"],
                         {"applied": True, "config_id": "model", "value": "claude-opus-5-5-high"})
        self.assertEqual(started["config_application"]["effort"],
                         {"applied": True, "applied_via": "model-id", "value": "high"})
        self.acp("send", "--text", "hi opus", "--timeout", "30")
        child = [argv for argv in self.spawns() if "--input-format" in argv][-1]
        self.assertEqual(child[child.index("--model") + 1], "claude-opus-5-5-high")
        self.assertNotIn("--effort", child)

    def test_mid_turn_steer_and_interrupt_steer_end_to_end(self) -> None:
        self.assertEqual(self.acp("start")["state"], "ready")
        idle = self.acp("steer", "--text", "later")
        self.assertEqual(idle.get("steer_outcome"), "not_consumed", idle)       # idle steer is never written
        self.assertEqual(idle.get("steer_reason"), "no-active-turn")

        sent = self.acp("send", "--no-wait", "--text", "slow first")
        self.assertEqual(sent.get("outcome"), "in_progress", sent)
        steered = self.acp("steer", "--text", "steered second")
        self.assertEqual(steered.get("steer_method"), "_session/steering", steered)
        self.assertEqual(steered.get("steer_outcome"), "written", steered)
        self.assertEqual(steered.get("steer_confirmation"), "write-only", steered)
        self.assertIs(steered.get("turn_request_id_preserved"), True, steered)
        self.assertEqual(steered.get("turn_request_id_after"), sent["turn_request_id"])
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            obs = self.acp("observe")
            if not obs.get("turn_active"):
                break
            time.sleep(0.05)
        self.assertEqual(obs["last_prompt"]["stop_reason"], "end_turn", obs)
        captured = self.acp("capture")
        self.assertEqual(captured.get("final_text"), "echo: slow firstecho: steered second", captured)

        hung = self.acp("send", "--no-wait", "--text", "hang")
        self.assertEqual(hung.get("outcome"), "in_progress", hung)
        time.sleep(0.15)
        interrupted = self.acp("steer", "--steer-mode", "interrupt", "--text", "after interrupt")
        self.assertEqual(interrupted.get("steer_mode"), "interrupt", interrupted)
        self.assertEqual(interrupted.get("steer_outcome"), "interrupted_and_resent", interrupted)
        self.assertIs(interrupted.get("steer_consumed"), True, interrupted)
        self.assertEqual(interrupted.get("steer_confirmation"), "cancel-confirmed", interrupted)
        self.assertEqual(interrupted.get("cancelled_turn_request_id"), hung["turn_request_id"])
        self.assertEqual(interrupted.get("cancelled_turn_stop_reason"), "cancelled")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            obs = self.acp("observe")
            if not obs.get("turn_active"):
                break
            time.sleep(0.05)
        self.assertEqual(self.acp("capture").get("final_text"), "echo: after interrupt")
        resume_child = [argv for argv in self.spawns() if "--conversation" in argv]
        self.assertTrue(resume_child, "interrupt+resend must respawn agy with --conversation")


if __name__ == "__main__":
    unittest.main()
