#!/usr/bin/env python3
"""Issue #79 - ZCode 3.12+ ACP app-server compatibility, hermetic.

Drives `scripts/kaola-zcode-acp.py` against `fake-zcode-312-app-server.py`,
which mirrors the strictness measured in the installed 3.12.3 bundle. No
installed ZCode, no login, no account, no network and no real credential are
used: the only "secret" is the fixture value inside `fixtures/`.

Covers what the pre-change adapter could not do:
  * resolve the bundled provider table from the verified entry and inject BOTH
    provider-config env names, never an inherited value;
  * create a session with no model channel and select the model afterwards on
    the `account:*` provider;
  * push the account/entitlement snapshot in the shape `G6n` accepts;
  * answer `interaction/requestProviderRuntimeHeaders` with the strict union;
  * keep the credential out of every ACP byte and every log byte;
  * still drive a pre-3.12 backend through the old overlay path.
"""

from __future__ import annotations

import json
import os
import queue
import stat
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ADAPTER = PROJECT / "scripts" / "kaola-zcode-acp.py"
FAKE_312 = PROJECT / "tests" / "contract" / "fake-zcode-312-app-server.py"
FAKE_LEGACY = PROJECT / "tests" / "contract" / "fake-zcode-app-server.py"
FIXTURES = PROJECT / "tests" / "contract" / "fixtures"
DESKTOP_CONFIG_FIXTURE = FIXTURES / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = FIXTURES / "zcode-coding-plan-cache.json"
DESKTOP_CONFIG = json.loads(DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"))
CODING_PLAN_ID = "builtin:bigmodel-coding-plan"
ACCOUNT_ID = "account:bigmodel-individual-coding-plan"
FIXTURE_SECRET = DESKTOP_CONFIG["provider"][CODING_PLAN_ID]["options"]["apiKey"]

# A rules-only bundled table, same shape and revision as the shipped one.
BUILTIN_TABLE = {
    "schemaVersion": 1,
    "revision": 28,
    "config": {
        "providerConfigRules": {
            "templateRules": [],
            "providerRules": [{
                "providerId": ACCOUNT_ID,
                "providerName": "BigModel Individual Coding Plan",
                "config": {
                    "group": "bigmodel-family",
                    "builtinModelIds": ["GLM-5.3", "GLM-5.3-Flash"],
                    "access": {"type": "zhipu-account",
                               "mode": "individual-coding-plan",
                               "accountType": "bigmodel"},
                    "api": {"type": "anthropic-messages",
                            "baseUrl": "https://open.bigmodel.cn/api/anthropic"},
                },
            }],
        },
        "modelConfigRules": {},
    },
}

# Same rule ordering the shipped table uses: a generic rule then a specific one,
# later matches overriding earlier, tested as `^(?:<modelMatch>)$` case-insensitively.
BUILTIN_TABLE_WITH_RULES = json.loads(json.dumps(BUILTIN_TABLE))
BUILTIN_TABLE_WITH_RULES["config"]["modelConfigRules"] = {
    "modelRules": [
        {"modelMatch": ".*",
         "config": {"optionSpecs": {"reasoningLevel": {"values": ["disabled", "enabled"]}}}},
        {"modelMatch": r".*glm-5\.3(?:-flash)?(?:[.\-:/\[].*)?",
         "config": {"optionSpecs": {"reasoningLevel": {"values": ["low", "high", "max"]}}}},
    ],
}

POISON = "/tmp/i79-inherited-must-not-be-used/zcode-builtin.json"


def load_adapter():
    import importlib.util
    spec = importlib.util.spec_from_file_location("kaola_zcode_acp_79", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Driver:
    """Minimal ACP driver: adapter subprocess + sandboxed HOME + fake entry."""

    def __init__(self, tmp: Path, modern: bool = True, scenario: str = "basic",
                 bundled: bool = True, expect_key: str | None = None,
                 desktop_config: dict | str | None = None) -> None:
        self.tmp = tmp
        self.cwd = tmp / "workspace"
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.record_path = tmp / "record.json"
        self.home = tmp / "home"
        (self.home / ".zcode" / "v2").mkdir(parents=True, exist_ok=True)
        if desktop_config is None:
            registry = DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8")
        elif isinstance(desktop_config, str):
            registry = desktop_config
        else:
            registry = json.dumps(desktop_config)
        if registry != "ABSENT":
            (self.home / ".zcode" / "v2" / "config.json").write_text(registry, encoding="utf-8")
        (self.home / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        # The personal provider config is only ever referenced by path.
        (self.home / ".zcode" / "v2" / "provider_config.json").write_text("{}\n", encoding="utf-8")

        self.entry_dir = tmp / "bundle"
        self.entry_dir.mkdir(parents=True, exist_ok=True)
        self.builtin_path = self.entry_dir / "provider" / "zcode-builtin.json"
        if bundled:
            self.builtin_path.parent.mkdir(parents=True, exist_ok=True)
            self.builtin_path.write_text(json.dumps(BUILTIN_TABLE_WITH_RULES), encoding="utf-8")
        self.shim = self._write_shim(modern, scenario)

        env = {
            "HOME": str(self.home),
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "PYTHONUNBUFFERED": "1",
            "LANG": "C",
            # An inherited, unowned value that must never reach the child.
            "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": POISON,
            "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": POISON,
        }
        if expect_key:
            env["FAKE_ZCODE_EXPECT_KEY"] = expect_key
        self.messages: list[dict] = []
        self.queue: queue.Queue = queue.Queue()
        self.proc = subprocess.Popen(
            [sys.executable, str(ADAPTER), "--zcode-entry", str(self.shim),
             "--zcode-node", sys.executable, "--cwd", str(self.cwd)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(self.cwd), env=env)
        self.stderr_bytes = bytearray()
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _write_shim(self, modern: bool, scenario: str) -> Path:
        fake = FAKE_312 if modern else FAKE_LEGACY
        shim = self.entry_dir / "zcode.py"
        extra = ""
        if not modern:
            extra = (f"os.environ['FAKE_ZCODE_RPC_LOG'] = {str(self.tmp / 'rpc.jsonl')!r}\n")
        shim.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(self.record_path)!r}\n"
            + extra +
            f"sys.argv = [{str(fake)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(fake)!r}, run_name='__main__')\n",
            encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        return shim

    def _read_stdout(self) -> None:
        for raw in self.proc.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                self.messages.append(msg)
                self.queue.put(msg)

    def _read_stderr(self) -> None:
        for chunk in iter(lambda: self.proc.stderr.read(4096), b""):
            if not chunk:
                break
            self.stderr_bytes.extend(chunk)

    def request(self, rid, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            payload["params"] = params
        self.proc.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
        self.proc.stdin.flush()

    def wait_for(self, pred, timeout: float = 20.0):
        deadline = time.monotonic() + timeout
        for msg in list(self.messages):
            if pred(msg):
                return msg
        while time.monotonic() < deadline:
            try:
                msg = self.queue.get(timeout=0.05)
            except queue.Empty:
                if self.proc.poll() is not None:
                    break
                continue
            if pred(msg):
                return msg
        for msg in list(self.messages):
            if pred(msg):
                return msg
        return None

    def wait_result(self, rid, timeout: float = 20.0):
        return self.wait_for(lambda m: m.get("id") == rid, timeout)

    def record(self) -> dict:
        try:
            return json.loads(self.record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def stderr_text(self) -> str:
        return bytes(self.stderr_bytes).decode("utf-8", "replace")

    def stdout_text(self) -> str:
        return "\n".join(json.dumps(m) for m in self.messages)

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=10)
        for pipe in (self.proc.stdout, self.proc.stderr):
            try:
                pipe.close()
            except OSError:
                pass

    def new_session(self, rid=1):
        self.request(rid, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        self.wait_result(rid)
        self.request(rid + 1, "session/new", {"cwd": str(self.cwd), "mcpServers": []})
        return self.wait_result(rid + 1)

    def prompt(self, sid: str, rid: int = 10, text: str = "hello"):
        """Drive one turn. The backend is created lazily on first real use, so
        nothing reaches the child until a prompt is sent."""
        self.request(rid, "session/prompt", {
            "sessionId": sid, "prompt": [{"type": "text", "text": text}]})
        return self.wait_result(rid)


class TempCase(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory(prefix="i79-")
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def driver(self, **kw) -> Driver:
        drv = Driver(self.tmp, **kw)
        self.addCleanup(drv.close)
        return drv


class TestBundledProviderConfigResolution(TempCase):
    """The path must come from the verified entry, never from the parent env."""

    def test_resolves_candidates_in_order(self):
        m = load_adapter()
        base = self.tmp / "b"
        (base / "provider").mkdir(parents=True)
        entry = base / "zcode.cjs"
        entry.write_text("", encoding="utf-8")
        first = base / "provider" / "zcode-builtin.json"
        first.write_text("{}", encoding="utf-8")
        self.assertEqual(m.resolve_builtin_provider_config(str(entry)), str(first))

    def test_resolves_shipped_app_layout_one_level_up(self):
        """The layout the CLI's own five-level-up probe misses."""
        m = load_adapter()
        res = self.tmp / "Resources"
        (res / "glm").mkdir(parents=True)
        (res / "config" / "provider").mkdir(parents=True)
        entry = res / "glm" / "zcode.cjs"
        entry.write_text("", encoding="utf-8")
        table = res / "config" / "provider" / "zcode-builtin.json"
        table.write_text("{}", encoding="utf-8")
        self.assertEqual(m.resolve_builtin_provider_config(str(entry)), str(table))

    def test_absent_table_resolves_to_none(self):
        m = load_adapter()
        entry = self.tmp / "lonely" / "zcode.cjs"
        entry.parent.mkdir(parents=True)
        entry.write_text("", encoding="utf-8")
        self.assertIsNone(m.resolve_builtin_provider_config(str(entry)))

    def test_both_env_names_or_neither(self):
        m = load_adapter()
        base = self.tmp / "c"
        (base / "provider").mkdir(parents=True)
        entry = base / "zcode.cjs"
        entry.write_text("", encoding="utf-8")
        (base / "provider" / "zcode-builtin.json").write_text("{}", encoding="utf-8")
        env = m.build_child_env(str(entry))
        self.assertIn(m.BUILTIN_PROVIDER_CONFIG_ENV, env)
        self.assertIn(m.PERSONAL_PROVIDER_CONFIG_ENV, env)
        # No table -> neither name is set.
        lonely = self.tmp / "d" / "zcode.cjs"
        lonely.parent.mkdir(parents=True)
        lonely.write_text("", encoding="utf-8")
        env2 = m.build_child_env(str(lonely))
        self.assertNotIn(m.BUILTIN_PROVIDER_CONFIG_ENV, env2)
        self.assertNotIn(m.PERSONAL_PROVIDER_CONFIG_ENV, env2)

    def test_inherited_value_never_reaches_the_child(self):
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        msg = drv.new_session()
        self.assertIsNotNone(msg)
        drv.prompt(msg["result"]["sessionId"])
        rec = drv.record()
        self.assertEqual(rec.get("builtin_env"), str(drv.builtin_path))
        self.assertNotEqual(rec.get("builtin_env"), POISON)
        self.assertNotEqual(rec.get("personal_env"), POISON)
        self.assertTrue(rec.get("builtin_env_exists"))
        self.assertEqual(
            rec.get("personal_env"),
            str(drv.home / ".zcode" / "v2" / "provider_config.json"))


class TestModernTurn(TempCase):
    def sid(self, drv: Driver) -> str:
        msg = drv.new_session()
        self.assertIsNotNone(msg, "session/new returned nothing")
        self.assertNotIn("error", msg, f"session/new failed: {msg}")
        return msg["result"]["sessionId"]

    def test_create_carries_no_model_and_set_model_follows(self):
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        sid = self.sid(drv)
        res = drv.prompt(sid)
        self.assertIsNotNone(res, "no prompt result")
        rec = drv.record()

        # 3.12+ create has no model channel at all.
        self.assertNotIn("runtimeModel", rec.get("create_params") or {})
        self.assertNotIn("model", rec.get("create_params") or {})

        # Selection happens afterwards, on the account provider, without
        # touching the user's workspace defaults.
        set_model = rec.get("set_model") or {}
        self.assertEqual(set_model.get("model", {}).get("providerId"), ACCOUNT_ID)
        self.assertEqual(set_model.get("model", {}).get("modelId"), "GLM-5.3")
        self.assertIs(set_model.get("persistAsWorkspaceLastUsed"), False)
        # 3.12+ refuses a Coding Plan selection with no explicit reasoning level.
        self.assertIn(set_model["model"].get("options", {}).get("reasoningLevel"),
                      ("low", "high", "max"))

    def test_reasoning_levels_come_from_the_bundled_table(self):
        m = load_adapter()
        self.assertEqual(m.account_reasoning_levels(BUILTIN_TABLE_WITH_RULES, "GLM-5.3"),
                         ["low", "high", "max"])
        # A model the specific rule does not match falls back to the generic one.
        self.assertEqual(m.account_reasoning_levels(BUILTIN_TABLE_WITH_RULES, "some-other"),
                         ["disabled", "enabled"])

    def test_account_snapshot_matches_installed_validator(self):
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        drv.prompt(self.sid(drv))
        push = drv.record().get("account_push") or {}
        self.assertTrue(str(push.get("revision") or "").strip())
        based = push.get("basedOnZCodeBuiltinRevision") or ""
        self.assertTrue(based.startswith("zcode-builtin:28:"),
                        f"unexpected builtin revision {based!r}")
        entry = (push.get("providers") or {}).get(ACCOUNT_ID) or {}
        self.assertEqual(entry.get("builtinModelIds"), ["GLM-5.3", "GLM-5.3-Flash"])
        self.assertEqual(entry.get("access"), {"type": "zhipu-account", "entitled": True})
        # The state fields the installed 3.12.3 schema actually requires,
        # measured live: availability enum + entitled + current.
        state = (push.get("states") or {}).get(ACCOUNT_ID) or {}
        self.assertIs(state.get("current"), True)
        self.assertIs(state.get("entitled"), True)
        self.assertIn(state.get("availability"),
                      ("available", "pending", "unavailable", "unknown"))
        # No credential travels in the snapshot.
        self.assertNotIn(FIXTURE_SECRET, json.dumps(push))

    def test_builtin_revision_hashes_the_path_not_the_bytes(self):
        m = load_adapter()
        import hashlib
        table = self.tmp / "t.json"
        table.write_text(json.dumps(BUILTIN_TABLE), encoding="utf-8")
        got = m.builtin_revision_string(BUILTIN_TABLE, str(table))
        want_digest = hashlib.sha256(str(table).encode("utf-8")).hexdigest()
        self.assertEqual(got, f"zcode-builtin:28:{want_digest}")
        # Same bytes at a different path must give a different revision.
        other = self.tmp / "other.json"
        other.write_text(json.dumps(BUILTIN_TABLE), encoding="utf-8")
        self.assertNotEqual(got, m.builtin_revision_string(BUILTIN_TABLE, str(other)))

    def test_runtime_headers_answered_and_turn_completes(self):
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        sid = self.sid(drv)
        res = drv.prompt(sid)
        self.assertIsNotNone(res)
        rec = drv.record()
        self.assertTrue(rec.get("headers_answer_ok"),
                        f"headers rejected: {rec.get('headers_problem')}")
        self.assertEqual((res.get("result") or {}).get("stopReason"), "end_turn")

    def test_mid_session_model_switch_uses_the_account_path(self):
        """An Agent switching model mid-session must not fall back to the
        pre-3.12 overlay: 3.12+ rejects `runtimeModel` outright and requires an
        explicit reasoning level."""
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        sid = self.sid(drv)
        drv.prompt(sid)
        drv.request(20, "session/set_config_option", {
            "sessionId": sid, "configId": "model",
            "value": f"{CODING_PLAN_ID}\\GLM-5.3-Flash"})
        res = drv.wait_result(20)
        self.assertIsNotNone(res, "set_config_option returned nothing")
        self.assertNotIn("error", res, f"model switch failed: {json.dumps(res)}")
        sent = drv.record().get("set_model") or {}
        self.assertNotIn("runtimeModel", sent)
        self.assertEqual(sent.get("model", {}).get("providerId"), ACCOUNT_ID)
        self.assertEqual(sent.get("model", {}).get("modelId"), "GLM-5.3-Flash")
        self.assertIn(sent["model"].get("options", {}).get("reasoningLevel"),
                      ("low", "high", "max"))
        self.assertIs(sent.get("persistAsWorkspaceLastUsed"), False)

    def test_mid_session_switch_still_refuses_a_foreign_provider(self):
        """The one-Coding-Plan boundary is unchanged by the account path."""
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        sid = self.sid(drv)
        drv.prompt(sid)
        drv.request(21, "session/set_config_option", {
            "sessionId": sid, "configId": "model",
            "value": "builtin:someone-else\\GLM-5.3"})
        res = drv.wait_result(21)
        self.assertIsNotNone(res)
        self.assertIn("error", res, f"expected a refusal, got {json.dumps(res)}")
        self.assertNotIn(FIXTURE_SECRET, json.dumps(res))

    def test_credential_never_appears_in_acp_or_logs(self):
        drv = self.driver(modern=True, expect_key=FIXTURE_SECRET)
        sid = self.sid(drv)
        drv.prompt(sid)
        self.assertNotIn(FIXTURE_SECRET, drv.stdout_text())
        self.assertNotIn(FIXTURE_SECRET, drv.stderr_text())

    def test_refuses_a_model_the_plan_does_not_offer(self):
        m = load_adapter()
        release = BUILTIN_TABLE
        choice = {"provider_id": CODING_PLAN_ID, "model_ids": ["GLM-9-not-in-plan"]}
        with self.assertRaises(m.RuntimeError_):
            m.build_account_config(choice, release, "/tmp/x.json")

    def test_headers_refused_for_a_foreign_provider(self):
        """A provider we did not authorize gets a negative answer, not the key."""
        m = load_adapter()
        agent = m.ZCodeAcpAgent.__new__(m.ZCodeAcpAgent)
        agent.account = {"account_id": ACCOUNT_ID, "model_ids": ["GLM-5.3"],
                         "params": {}}
        answer = agent.runtime_headers_answer({"providerId": "account:someone-else"})
        self.assertIs(answer["headersApplied"], False)
        self.assertNotIn("requestAuth", answer)


class TestMissingCredentialsAndRegistry(TempCase):
    def _refuses_at_first_use(self, drv: Driver) -> None:
        msg = drv.new_session()
        self.assertIsNotNone(msg, "session/new returned nothing")
        sid = msg["result"]["sessionId"]
        res = drv.prompt(sid)
        self.assertIsNotNone(res, "prompt returned nothing")
        self.assertIn("error", res, f"expected a fail-closed error, got {json.dumps(res)}")
        # The refusal never leaks a credential.
        self.assertNotIn(FIXTURE_SECRET, json.dumps(res))

    def test_absent_desktop_registry_fails_closed(self):
        self._refuses_at_first_use(self.driver(modern=True, desktop_config="ABSENT"))

    def test_plan_without_credential_fails_closed(self):
        config = json.loads(DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"))
        config["provider"][CODING_PLAN_ID]["options"]["apiKey"] = ""
        self._refuses_at_first_use(self.driver(modern=True, desktop_config=config))


class TestLegacyBackendStillWorks(TempCase):
    """A pre-3.12 backend must keep working through the old overlay path."""

    def test_legacy_backend_uses_the_runtime_model_overlay(self):
        drv = self.driver(modern=False, bundled=True)
        drv.request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        drv.wait_result(1)
        drv.request(2, "session/new", {"cwd": str(drv.cwd), "mcpServers": []})
        msg = drv.wait_result(2)
        self.assertIsNotNone(msg, "legacy session/new returned nothing")
        self.assertNotIn("error", msg, f"legacy path failed: {msg}")
        res = drv.prompt(msg["result"]["sessionId"])
        self.assertIsNotNone(res, "legacy prompt returned nothing")
        overlays = drv.record().get("overlays") or []
        self.assertTrue(overlays, "legacy backend received no runtimeModel overlay")
        self.assertEqual(overlays[0]["providerId"], CODING_PLAN_ID)


if __name__ == "__main__":
    unittest.main(verbosity=1)
