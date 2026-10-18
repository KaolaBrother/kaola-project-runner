#!/usr/bin/env python3
"""Issue #347: read-only Command Code usage probe for the dsh/commandcode tier.

Fixtures use obvious fake keys and identity strings. No test contacts
api.commandcode.ai or reads the operator's dsh home.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[2]
QUOTA_PATH = PROJECT / "scripts" / "kaola-quota.py"
MODEL = "commandcode/deepseek/deepseek-v4.1-flash"
OPENCODE_MODEL = "opencode-go/deepseek-v4.1-flash"
FAKE_KEY = "fixture-commandcode-key-347-not-secret"
OTHER_KEY = "fixture-commandcode-other-347-not-secret"
EMAIL = "identity-email-347@example.test"
USER_ID = "user_IDENTITY_347"
ORG_ID = "org_IDENTITY_347"
PRICE_ID = "price_IDENTITY_347"
SUB_ID = "sub_IDENTITY_347"
META_USER = "uuid-identity-347"
FIVE_RESET_MS = 1761010554000
WEEKLY_RESET_MS = 1792855740040
FIVE_RESET = "2025-10-21T01:35:54Z"
WEEKLY_RESET = "2026-10-24T15:29:00Z"
PERIOD_END = "2026-11-17T15:23:56Z"
IDENTITY = (EMAIL, USER_ID, ORG_ID, PRICE_ID, SUB_ID, META_USER, FAKE_KEY, OTHER_KEY)


def load_quota():
    spec = importlib.util.spec_from_file_location("kaola_quota_347", QUOTA_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def credits_body() -> dict[str, Any]:
    return {
        "email": EMAIL,
        "userId": USER_ID,
        "orgId": ORG_ID,
        "priceId": PRICE_ID,
        "credits": {
            "monthlyCredits": 40,
            "purchasedCredits": 3,
            "freeCredits": 1,
            "belowThreshold": False,
        },
        "windowLimits": {
            "limited": True,
            "exceeded": None,
            "fiveHour": {
                "used": 9, "cap": 10, "exceeded": False, "resetAt": FIVE_RESET_MS,
            },
            "weekly": {
                "used": 1, "cap": 35, "exceeded": False, "resetAt": WEEKLY_RESET_MS,
            },
        },
        "sandboxAccess": True,
        "sandboxMinutes": {"usedMinutes": 4, "limitMinutes": 9, "resetAt": FIVE_RESET_MS},
    }


def subscription_body(plan_id: str = "individual-goat", grant: float | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": SUB_ID,
        "status": "active",
        "userId": USER_ID,
        "orgId": ORG_ID,
        "priceId": PRICE_ID,
        "email": EMAIL,
        "metadata": {"commandCodeUserId": META_USER, "fbp": "fb-identity-347"},
        "planId": plan_id,
        "currentPeriodStart": "2026-10-17T15:23:56.000Z",
        "currentPeriodEnd": "2026-11-17T15:23:56.000Z",
        "cancelAtPeriodEnd": False,
    }
    if grant is not None:
        data["grant"] = grant
    return {"success": True, "data": data}


def summary_body() -> dict[str, Any]:
    return {
        "totalCount": 5,
        "totalCost": 1.25,
        "totalTokens": 40345,
        "totalTokensIn": 40000,
        "email": EMAIL,
        "userId": USER_ID,
        "periodBasis": "billing-period",
        "daily": [{"email": EMAIL}],
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler name
        server = self.server
        path = self.path.split("?", 1)[0]
        server.hits.append(path)  # type: ignore[attr-defined]
        server.auths.append(self.headers.get("Authorization"))  # type: ignore[attr-defined]
        scenario = server.scenario  # type: ignore[attr-defined]
        if path == "/alpha/whoami" or scenario == "timeout":
            if scenario == "timeout":
                import time
                time.sleep(2.0)
            self._send(500, {"error": "not-used", "email": EMAIL})
            return
        if path == "/alpha/billing/credits":
            self._send(*self._credits(scenario))
            return
        if path == "/alpha/billing/subscriptions":
            self._send(*self._subscriptions(scenario))
            return
        if path == "/alpha/usage/summary":
            self._send(*self._summary(scenario))
            return
        self._send(404, {"error": "unknown", "email": EMAIL})

    def _credits(self, scenario: str) -> tuple[int, dict[str, Any]]:
        if scenario == "401":
            return 401, {"error": "unauthorized", "email": EMAIL, "userId": USER_ID}
        if scenario == "403":
            return 403, {"error": "upgrade_required", "email": EMAIL, "userId": USER_ID, "orgId": ORG_ID}
        if scenario == "429":
            return 429, {"error": "rate_limit", "email": EMAIL}
        if scenario == "500":
            return 503, {"error": "upstream", "email": EMAIL, "priceId": PRICE_ID}
        if scenario == "shape":
            return 200, {"email": EMAIL, "userId": USER_ID, "credits": {"monthlyCredits": 1}}
        return 200, credits_body()

    def _subscriptions(self, scenario: str) -> tuple[int, dict[str, Any]]:
        if scenario in ("sub_fail", "summary_only_fail"):
            if scenario == "sub_fail":
                return 500, {"error": "subscription down", "email": EMAIL, "orgId": ORG_ID}
        if scenario == "sub_fail":
            return 500, {"error": "subscription down", "email": EMAIL}
        if scenario == "unknown_plan":
            return 200, subscription_body("not-a-published-plan")
        if scenario == "explicit_grant":
            return 200, subscription_body("individual-goat", grant=12)
        if scenario == "summary_only_fail":
            return 200, subscription_body()
        if scenario == "credits_only":
            return 404, {"error": "missing", "email": EMAIL}
        return 200, subscription_body()

    def _summary(self, scenario: str) -> tuple[int, dict[str, Any]]:
        if scenario in ("sub_fail", "summary_only_fail", "credits_only"):
            return 500, {"error": "summary down", "email": EMAIL, "userId": USER_ID}
        return 200, summary_body()

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


class Loopback:
    def __init__(self, scenario: str) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.scenario = scenario  # type: ignore[attr-defined]
        self.server.hits = []  # type: ignore[attr-defined]
        self.server.auths = []  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "Loopback":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()


class CommandCodeUsageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quota = load_quota()
        if not hasattr(cls.quota, "probe_commandcode_usage"):
            raise AssertionError(
                "probe_commandcode_usage is missing; the Command Code probe is not on this tree"
            )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kaola-i347-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.dsh = Path(self.tmp.name) / "dsh"
        self.home.mkdir()
        self.dsh.mkdir()
        self.env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self.home),
            "DSH_HOME": str(self.dsh),
        }

    def _probe_env(self) -> dict[str, str]:
        env = dict(self.env)
        if env.get("COMMANDCODE_API_KEY", "").strip():
            return env
        for path in (self.dsh / ".env", self.dsh / ".credentials.yaml"):
            if path.is_file() and "COMMANDCODE_API_KEY" in path.read_text(encoding="utf-8"):
                return env
        env["COMMANDCODE_API_KEY"] = FAKE_KEY
        return env

    def probe(self, scenario: str, **extra: Any) -> dict[str, Any]:
        captured = io.StringIO()
        handler = logging.Handler()
        handler.emit = lambda record: captured.write(record.getMessage() + "\n")  # type: ignore[method-assign]
        root = logging.getLogger()
        root.addHandler(handler)
        previous = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                with Loopback(scenario) as server:
                    result = self.quota.probe_commandcode_usage(
                        model=MODEL,
                        timeout=extra.pop("timeout", 2.0),
                        env=self._probe_env(),
                        base_url=server.base,
                        **extra,
                    )
                    self.server = server
            self.captured = captured.getvalue()
        finally:
            os.chdir(previous)
            root.removeHandler(handler)
        return result

    def assert_secret_free(self, result: dict[str, Any], *extra: str) -> None:
        blob = self.captured + json.dumps(result)
        for secret in (*IDENTITY, *extra):
            self.assertNotIn(secret, blob, secret)

    def assert_non_ok(self, result: dict[str, Any], status: str, reason: str) -> None:
        self.assertEqual(result["status"], status)
        self.assertEqual(result["platform"], "dsh")
        self.assertEqual(result["packageId"], "dsh:commandcode")
        self.assertEqual(result["provider"], "commandcode")
        self.assertEqual(result["model"], MODEL)
        self.assertIsNone(result["quota"])
        self.assertEqual(result["windows"], {})
        self.assertEqual(result["reason"], reason)
        self.assertNotIn("credits", result)
        self.assertNotIn("plan", result)
        self.assertNotIn("period", result)
        self.assert_secret_free(result)

    def test_credits_ok(self) -> None:
        result = self.probe("credits_only")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["packageId"], "dsh:commandcode")
        self.assertEqual(result["provider"], "commandcode")
        self.assertEqual(set(result["windows"]), {"5h", "weekly", "monthly"})
        five = result["windows"]["5h"]
        self.assertEqual(five["used"], 9)
        self.assertEqual(five["limit"], 10)
        self.assertEqual(five["used_percent"], 90.0)
        self.assertEqual(five["remaining_percent"], 10.0)
        self.assertAlmostEqual(five["remaining_fraction"], 0.1)
        self.assertEqual(five["reset_at"], FIVE_RESET)
        self.assertIs(five["exceeded"], False)
        weekly = result["windows"]["weekly"]
        self.assertEqual(weekly["reset_at"], WEEKLY_RESET)
        self.assertEqual(weekly["used_percent"], 2.86)
        self.assertEqual(weekly["remaining_percent"], 97.14)
        self.assertEqual(result["quota"]["window"], "5h")
        self.assertEqual(result["credits"], {"monthly": 40, "purchased": 3, "free": 1})
        self.assertIsNone(result["windows"]["monthly"]["limit"])
        self.assertNotIn("plan", result)
        self.assertNotIn("period", result)
        self.assertNotIn("sandboxAccess", json.dumps(result))
        self.assert_secret_free(result)
        self.assertNotIn("/alpha/whoami", self.server.server.hits)  # type: ignore[attr-defined]

    def test_subscription_ok(self) -> None:
        result = self.probe("ok")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"], {"id": "individual-goat", "period_end": PERIOD_END})
        monthly = result["windows"]["monthly"]
        self.assertEqual(monthly["limit"], 70.0)
        self.assertEqual(monthly["used"], 30.0)
        self.assertEqual(monthly["reset_at"], PERIOD_END)
        self.assertAlmostEqual(monthly["remaining_fraction"], 40 / 70)
        self.assertEqual(monthly["remaining_percent"], 57.14)
        self.assertEqual(monthly["used_percent"], 42.86)
        self.assertEqual(result["period"], {"spend": 1.25, "requests": 5, "tokens": 40345})
        self.assertEqual(result["quota"]["window"], "5h")
        self.assert_secret_free(result)
        self.assertEqual(
            [hit for hit in self.server.server.hits if hit == "/alpha/whoami"],  # type: ignore[attr-defined]
            [],
        )

    def test_subscription_fail(self) -> None:
        result = self.probe("sub_fail")
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("plan", result)
        self.assertNotIn("period", result)
        self.assertIsNone(result["windows"]["monthly"]["limit"])
        self.assertIn("5h", result["windows"])
        self.assertIn("weekly", result["windows"])
        self.assert_secret_free(result)

    def test_summary_fail_omits_period(self) -> None:
        result = self.probe("summary_only_fail")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"]["id"], "individual-goat")
        self.assertNotIn("period", result)
        self.assertEqual(result["windows"]["monthly"]["limit"], 70.0)
        self.assert_secret_free(result)

    def test_unknown_plan_does_not_invent_limit(self) -> None:
        result = self.probe("unknown_plan")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["plan"]["id"], "not-a-published-plan")
        self.assertIsNone(result["windows"]["monthly"]["limit"])
        self.assertIsNone(result["windows"]["monthly"]["used_percent"])
        self.assert_secret_free(result)

    def test_explicit_subscription_grant_wins(self) -> None:
        result = self.probe("explicit_grant")
        self.assertEqual(result["windows"]["monthly"]["limit"], 12)
        self.assertEqual(result["plan"]["id"], "individual-goat")
        self.assert_secret_free(result)

    def test_key_missing(self) -> None:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = self.quota.probe_commandcode_usage(
                model=MODEL,
                timeout=0.2,
                env=self.env,
                base_url="http://127.0.0.1:9",
            )
        self.captured = captured.getvalue()
        self.assert_non_ok(result, "key_missing", "COMMANDCODE_API_KEY is not set")

    def test_key_env_precedes_files(self) -> None:
        (self.dsh / ".env").write_text(f"COMMANDCODE_API_KEY={OTHER_KEY}\n", encoding="utf-8")
        self.env["COMMANDCODE_API_KEY"] = FAKE_KEY
        result = self.probe("credits_only")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(self.server.server.auths[0], f"Bearer {FAKE_KEY}")  # type: ignore[attr-defined]
        self.assert_secret_free(result)

    def test_key_dotenv_precedes_credentials(self) -> None:
        (self.dsh / ".env").write_text(
            f"# comment\nexport COMMANDCODE_API_KEY=\"{FAKE_KEY}\"\n",
            encoding="utf-8",
        )
        (self.dsh / ".credentials.yaml").write_text(
            f"version: 1\nrefs:\n  COMMANDCODE_API_KEY: {OTHER_KEY}\n",
            encoding="utf-8",
        )
        result = self.probe("credits_only")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(self.server.server.auths[0], f"Bearer {FAKE_KEY}")  # type: ignore[attr-defined]
        self.assert_secret_free(result)

    def test_key_from_credentials_refs(self) -> None:
        (self.dsh / ".credentials.yaml").write_text(
            "version: 1\nrefs:\n  OPENCODE_API_KEY: not-the-commandcode-key\n"
            f"  COMMANDCODE_API_KEY: '{FAKE_KEY}'\n",
            encoding="utf-8",
        )
        result = self.probe("credits_only")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(self.server.server.auths[0], f"Bearer {FAKE_KEY}")  # type: ignore[attr-defined]
        self.assertNotIn("not-the-commandcode-key", json.dumps(result) + self.captured)
        self.assert_secret_free(result)

    def test_http_401(self) -> None:
        result = self.probe("401")
        self.assert_non_ok(result, "unavailable", "http 401")
        self.assertEqual(self.server.server.hits, ["/alpha/billing/credits"])  # type: ignore[attr-defined]

    def test_http_403_upgrade_required(self) -> None:
        result = self.probe("403")
        self.assert_non_ok(result, "unavailable", "upgrade_required")

    def test_http_429(self) -> None:
        result = self.probe("429")
        self.assert_non_ok(result, "unavailable", "http 429")

    def test_http_5xx(self) -> None:
        result = self.probe("500")
        self.assert_non_ok(result, "unavailable", "http 503")

    def test_timeout(self) -> None:
        result = self.probe("timeout", timeout=0.2)
        self.assert_non_ok(result, "unavailable", "timeout")

    def test_shape_changed(self) -> None:
        result = self.probe("shape")
        self.assert_non_ok(result, "unavailable", "response shape changed")

    def test_zero_reset_at_is_null(self) -> None:
        body = credits_body()
        body["windowLimits"]["fiveHour"]["resetAt"] = 0
        raw = json.dumps(body).encode()

        class Once(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:  # noqa: N802
                path = self.path.split("?", 1)[0]
                if path == "/alpha/billing/credits":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                self.send_response(404)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, fmt: str, *args: Any) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Once)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        host, port = server.server_address[:2]
        env = dict(self.env)
        env["COMMANDCODE_API_KEY"] = FAKE_KEY
        result = self.quota.probe_commandcode_usage(
            model=MODEL, timeout=2.0, env=env, base_url=f"http://{host}:{port}",
        )
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["windows"]["5h"]["reset_at"])
        self.assertEqual(result["windows"]["weekly"]["reset_at"], WEEKLY_RESET)

    def test_identity_fields_absent(self) -> None:
        result = self.probe("ok")
        self.assert_secret_free(result)
        self.assertNotIn("userId", json.dumps(result))
        self.assertNotIn("orgId", json.dumps(result))
        self.assertNotIn("priceId", json.dumps(result))
        self.assertNotIn("email", json.dumps(result))

    def test_key_absent_from_output_and_log(self) -> None:
        self.env["COMMANDCODE_API_KEY"] = FAKE_KEY
        result = self.probe("ok")
        self.assertEqual(result["status"], "ok")
        self.assert_secret_free(result)
        self.assertNotIn(FAKE_KEY, self.captured)
        before = set(self.dsh.iterdir())
        self.assertEqual(before, set())

    def test_probe_writes_nothing(self) -> None:
        before = set(Path(self.tmp.name).rglob("*"))
        self.probe("credits_only")
        after = set(Path(self.tmp.name).rglob("*"))
        self.assertEqual(after, before)

    def test_package_binding_is_strict(self) -> None:
        dsh = self.quota.load_catalog("dsh", PROJECT / "scripts")
        opencode = self.quota.load_catalog("opencode", PROJECT / "scripts")
        self.assertEqual(
            self.quota.resolve_model(dsh, MODEL),
            {"packageId": "dsh:commandcode", "status": "mapped"},
        )
        self.assertEqual(
            self.quota.resolve_model(dsh, OPENCODE_MODEL),
            {"packageId": "dsh:opencode-go", "status": "mapped"},
        )
        self.assertEqual(
            self.quota.resolve_model(opencode, OPENCODE_MODEL),
            {"packageId": "opencode:opencode-go", "status": "mapped"},
        )
        self.assertEqual(
            self.quota.resolve_model(opencode, MODEL)["packageId"],
            None,
        )
        result = self.probe("ok")
        self.assertEqual(result["packageId"], "dsh:commandcode")
        self.assertNotIn("opencode", result["packageId"])

    def test_opencode_and_antigravity_unchanged(self) -> None:
        payload = {
            "status": "SUCCESS",
            "command": {"data": {"groups": [{
                "name": "Gemini Models",
                "buckets": [
                    {
                        "id": "gemini-weekly",
                        "name": "Weekly",
                        "remaining_fraction": 0.9455534815788269,
                        "reset_time": "2026-10-21T07:35:54Z",
                    },
                    {
                        "id": "gemini-5h",
                        "name": "5 hour",
                        "remaining_fraction": 0.9279,
                        "reset_time": "2026-10-14T22:35:54Z",
                    },
                ],
            }]}},
        }
        parsed = self.quota.parse_antigravity_usage(json.dumps(payload), model="gemini-4-argon-medium")
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["platform"], "antigravity")
        self.assertEqual(parsed["packageId"], "antigravity:account")
        self.assertEqual(parsed["selected_group"], "Gemini Models")
        self.assertEqual(parsed["quota"]["window"], "weekly")
        self.assertEqual(parsed["quota"]["used"], 5.44)
        self.assertEqual(parsed["quota"]["limit"], 100.0)
        self.assertEqual(parsed["quota"]["remaining_percent"], 94.56)
        self.assertEqual(parsed["quota"]["reset_at"], "2026-10-21T07:35:54Z")
        self.assertEqual(parsed["windows"]["5h"]["bucket_id"], "gemini-5h")
        cli = self._cli("--platform", "dsh", "--model", OPENCODE_MODEL, "--probe")
        self.assertEqual(cli.returncode, 0, cli.stderr)
        usage = json.loads(cli.stdout)["usage"]
        self.assertEqual(usage["status"], "unsupported")
        self.assertEqual(
            usage["error"],
            "live CLI probe in kaola-quota.py is only implemented for antigravity (got dsh)",
        )
        self.assertNotIn("windows", usage)
        antigravity = self._cli("--platform", "antigravity", "--model", "gemini-4-argon-medium")
        self.assertEqual(antigravity.returncode, 0, antigravity.stderr)
        catalog = json.loads(antigravity.stdout)
        self.assertNotIn("usage", catalog)
        self.assertEqual(catalog["packages"][0]["id"], "antigravity:account")

    def test_cli_key_missing_and_unrelated_exit_codes(self) -> None:
        missing = self._cli("--platform", "dsh", "--model", MODEL, "--probe")
        self.assertEqual(missing.returncode, 0, missing.stderr)
        usage = json.loads(missing.stdout)["usage"]
        self.assertEqual(usage["status"], "key_missing")
        self.assertIsNone(usage["quota"])
        self.assertEqual(usage["windows"], {})
        plain = self._cli("--platform", "dsh", "--model", OPENCODE_MODEL)
        self.assertEqual(plain.returncode, 0, plain.stderr)
        body = json.loads(plain.stdout)
        self.assertNotIn("usage", body)
        self.assertEqual(body["resolved"]["packageId"], "dsh:opencode-go")
        grok = self._cli("--platform", "grok")
        self.assertEqual(grok.returncode, 0, grok.stderr)

    def _cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "DSH_HOME": str(self.dsh),
            "KAOLA_LAUNCH_BACKEND": "direct",
        }
        return subprocess.run(
            [sys.executable, str(QUOTA_PATH), *args],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            cwd=self.tmp.name,
        )


if __name__ == "__main__":
    unittest.main()
