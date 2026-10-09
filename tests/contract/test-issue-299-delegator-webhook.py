#!/usr/bin/env python3
"""Issue #299: Delegator webhook wake.

Contract coverage, all offline:

- the ``delegator-webhook`` CLI on ``kaola-acp.py`` (configure/status/test/
  remove/deliver), its config modes and ownership rules, secret-free receipts;
- the Host holder's detached wake child: ``end_turn``, ``blocked``,
  ``stopped`` and the skipped/failed short receipts, through a real holder
  driving ``mock-acp-agent.py``;
- the record contract's ``timer_owner.wake_mode``/``webhook_routine_id``.

Every test pins ``KAOLA_DELEGATOR_WEBHOOK_CONFIG`` (and HOME) to a temp path —
the real ``~/.config/kaola`` is never touched. The webhook endpoint is a
loopback ``http.server`` only.
"""

from __future__ import annotations

import json
import os
import secrets
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
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"

SENTINEL_URL_MARK = "SENTINEL-URL-9f3ac"
SENTINEL_KEY = "SENTINEL-KEY-4c2e1"
HEADER_NAME = "X-Kaola-Wake-Key"
HEADER_PREFIX = "WAKE "

PAYLOAD_KEYS = {"schema", "project", "session", "holder_instance_id",
                "event_seq", "state", "ts"}
ATTEMPT_RECEIPT_KEYS = {"ts", "state", "session", "holder_instance_id",
                        "event_seq", "result", "attempt", "max_attempts",
                        "http_status", "error", "elapsed_ms", "final"}


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class Endpoint:
    """Loopback sink. ``/slow`` sleeps past the 3 s attempt timeout,
    ``/err`` answers 500, ``/redirect`` answers 302, anything else 200."""

    def __init__(self, sleep_seconds: float = 0.0):
        self.posts: list[dict] = []
        self.sleep_seconds = sleep_seconds
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                if outer.sleep_seconds:
                    time.sleep(outer.sleep_seconds)
                try:
                    body = json.loads(raw)
                except ValueError:
                    body = None
                outer.posts.append({"path": self.path,
                                    "headers": dict(self.headers),
                                    "body": body})
                if self.path.startswith("/err"):
                    self.send_response(500)
                elif self.path.startswith("/redirect"):
                    self.send_response(302)
                    self.send_header("Location", "/hook")
                else:
                    self.send_response(200)
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


class WebhookCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="kpr-i299-")
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
        self.tmp.cleanup()

    # -- helpers -------------------------------------------------------------

    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("KAOLA_") or key == "KAOLA_LAUNCH_BACKEND"}
        env["KAOLA_LAUNCH_BACKEND"] = "direct"
        env["KAOLA_ACP_RECORD_ROOT"] = str(self.record_root)
        env["KAOLA_DELEGATOR_WEBHOOK_CONFIG"] = str(self.config)
        env["HOME"] = str(self.home)
        if extra:
            env.update(extra)
        return env

    def hook(self, *args: str, stdin: str | None = None,
             extra_env: dict[str, str] | None = None,
             timeout: float = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), "delegator-webhook", *args],
            capture_output=True, text=True, input=stdin,
            env=self.env(extra_env), timeout=timeout)

    def hook_json(self, *args: str, **kwargs) -> tuple[int, dict]:
        proc = self.hook(*args, **kwargs)
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError:
            self.fail(f"delegator-webhook stdout not JSON: {proc.stdout!r} "
                      f"stderr={proc.stderr!r}")

    def configure(self, url: str, key: str | None = SENTINEL_KEY,
                  owner: str = "agent-A",
                  attachment: tuple[str, ...] = ("--key-header", HEADER_NAME,
                                                 "--key-prefix", HEADER_PREFIX),
                  source: str = "stdin", **kwargs) -> tuple[int, dict]:
        args = ["configure", "--project", str(self.repo), "--owner-agent", owner,
                *attachment]
        stdin = None
        extra_env = kwargs.pop("extra_env", None)
        if source == "stdin":
            args.append("--stdin")
            stdin = json.dumps({"url": url, "sender_key": key})
        elif source == "env":
            extra_env = dict(extra_env or {})
            extra_env["I299_URL"] = url
            if key is not None:
                extra_env["I299_KEY"] = key
                args += ["--url-env", "I299_URL", "--key-env", "I299_KEY"]
            else:
                args += ["--url-env", "I299_URL"]
        elif source == "file":
            input_file = self.root / "input.json"
            input_file.write_text(json.dumps({"url": url, "sender_key": key}))
            input_file.chmod(0o600)
            args += ["--input-file", str(input_file)]
        return self.hook_json(*args, stdin=stdin, extra_env=extra_env)

    def write_config(self, projects: dict, mode: int = 0o600) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text(json.dumps(
            {"schema": "kaola-delegator-webhook/1", "projects": projects}))
        self.config.chmod(mode)

    def config_doc(self) -> dict:
        return json.loads(self.config.read_text(encoding="utf-8"))

    def receipts(self) -> list[dict]:
        path = self.repo / ".kaola" / "delegator-webhook-receipts.json"
        if not path.is_file():
            return []
        return json.loads(path.read_text(encoding="utf-8")).get("receipts", [])

    def receipts_path(self) -> Path:
        return self.repo / ".kaola" / "delegator-webhook-receipts.json"

    def deliver(self, payload: dict, **kwargs) -> subprocess.CompletedProcess:
        return self.hook("deliver", stdin=json.dumps(payload), **kwargs)

    # -- holder helpers -------------------------------------------------------

    def mock_command(self, scenario: str = "normal") -> str:
        return f"{sys.executable} {MOCK} --scenario {scenario}"

    def acp(self, command: str, *args: str, check: bool = True,
            timeout: float = 60, scenario: str = "normal") -> tuple[int, dict]:
        argv = [sys.executable, str(CLI), "grok", command,
                "--repo", str(self.repo), "--session", self.session,
                "--command", self.mock_command(scenario), *args]
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

    def start_host(self, suffix: str, scenario: str = "normal") -> str:
        # The standard Host name; note the project code cannot contain the
        # -i<digits>- worker marker, so "w299" not "i299".
        self.session = f"grok-w299-orchestrator-{suffix}"
        _, receipt = self.acp("start", scenario=scenario)
        self.assertEqual(receipt.get("session_role"), "host", receipt)
        return self.session

    def send(self, *extra: str, scenario: str = "normal") -> tuple[int, dict]:
        return self.acp("send", "--text", "wake me", *extra,
                        scenario=scenario)

    def wait_receipt(self, state: str, timeout: float = 15.0) -> dict:
        return wait_for(
            lambda: [r for r in self.receipts() if r.get("state") == state],
            timeout, f"receipt state={state}")


class ConfigureAndStatus(WebhookCase):
    def test_status_unconfigured_then_configure_then_remove(self) -> None:
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["schema"], "kaola-delegator-webhook-status/1")
        self.assertIs(status["configured"], False)
        self.assertIsNone(status["config_mode"])
        self.assertIsNone(status["fingerprint"])
        self.assertNotIn(SENTINEL_KEY, json.dumps(status))

        code, out = self.configure("https://hooks.example.invalid/wake")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["result"], "configured")
        self.assertTrue(out["configured"])
        self.assertTrue(out["sender_key_present"])
        self.assertEqual(out["owner_agent"], "agent-A")
        self.assertEqual(out["sender_key_attachment"],
                         {"style": "header", "name": HEADER_NAME,
                          "prefix": HEADER_PREFIX, "prefix_set": True})
        self.assertRegex(out["fingerprint"] or "", r"^[0-9a-f]{12}$")
        self.assertNotIn("hooks.example.invalid", json.dumps(out))
        self.assertNotIn(SENTINEL_KEY, json.dumps(out))

        mode = self.config.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
        self.assertEqual(self.config.parent.stat().st_mode & 0o777, 0o700)

        code, out = self.hook_json("remove", "--project", str(self.repo),
                                   "--owner-agent", "agent-B")
        self.assertNotEqual(code, 0)
        self.assertEqual(out["reason"], "entry-owned-by-other-agent")
        self.assertEqual(out["owner_agent"], "agent-A")
        code, out = self.hook_json("remove", "--project", str(self.repo),
                                   "--owner-agent", "agent-A")
        self.assertEqual(out["result"], "removed")
        self.assertNotIn(self.project, self.config_doc()["projects"])
        code, out = self.hook_json("remove", "--project", str(self.repo),
                                   "--owner-agent", "agent-A")
        self.assertEqual((code, out["result"]), (0, "absent"))

    def test_input_sources_and_refusals(self) -> None:
        url = "https://hooks.example.invalid/wake"
        # env source
        code, out = self.configure(url, source="env")
        self.assertEqual((code, out["result"]), (0, "configured"), out)
        # file source
        code, out = self.configure(url, source="file")
        self.assertEqual((code, out["result"]), (0, "configured"), out)
        # 0644 input file refused
        bad = self.root / "bad-input.json"
        bad.write_text(json.dumps({"url": url, "sender_key": SENTINEL_KEY}))
        bad.chmod(0o644)
        proc = self.hook("configure", "--project", str(self.repo),
                         "--owner-agent", "agent-A", "--input-file", str(bad),
                         "--key-header", HEADER_NAME)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("regular file owned by you", proc.stdout)
        # no input source, non-TTY
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A",
                                   "--key-header", HEADER_NAME)
        self.assertNotEqual(code, 0)
        self.assertEqual(out["reason"], "input-required")
        # bad header name
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A", "--stdin",
                                   "--key-header", "Bad Header",
                                   stdin=json.dumps(
                                       {"url": url, "sender_key": "k"}))
        self.assertNotEqual(code, 0)
        self.assertIn("RFC7230", out["detail"])
        # reserved header name
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A", "--stdin",
                                   "--key-header", "Host",
                                   stdin=json.dumps(
                                       {"url": url, "sender_key": "k"}))
        self.assertNotEqual(code, 0)
        # http to non-loopback refused
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A", "--stdin",
                                   "--key-in-url",
                                   stdin=json.dumps(
                                       {"url": "http://10.0.0.9/hook",
                                        "sender_key": None}))
        self.assertNotEqual(code, 0)
        self.assertIn("https", out["detail"])
        # sender_key with --key-in-url refused
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A", "--stdin",
                                   "--key-in-url",
                                   stdin=json.dumps(
                                       {"url": url, "sender_key": "k"}))
        self.assertNotEqual(code, 0)
        self.assertIn("absent", out["detail"])
        # no attachment refused; both refused
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A", "--stdin",
                                   stdin=json.dumps(
                                       {"url": url, "sender_key": "k"}))
        self.assertNotEqual(code, 0)
        # second input source refused
        code, out = self.hook_json("configure", "--project", str(self.repo),
                                   "--owner-agent", "agent-A", "--stdin",
                                   "--url-env", "I299_URL", "--key-in-url",
                                   stdin=json.dumps({"url": url}))
        self.assertNotEqual(code, 0)
        # a non-directory --project refuses
        code, out = self.hook_json("status", "--project", str(self.root / "nope"))
        self.assertNotEqual(code, 0)
        self.assertEqual(out["reason"], "invalid-input")

    def test_multi_project_ownership(self) -> None:
        other = self.root / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        other_root = os.path.realpath(str(other))
        url = "https://hooks.example.invalid/wake"
        code, out = self.configure(url, owner="agent-A")
        self.assertEqual(code, 0, out)
        code, out = self.hook_json(
            "configure", "--project", str(other), "--owner-agent", "agent-B",
            "--stdin", "--key-in-url",
            stdin=json.dumps({"url": url + "?k=1", "sender_key": None}))
        self.assertEqual(code, 0, out)
        # B cannot reconfigure A's entry
        code, out = self.hook_json(
            "configure", "--project", str(self.repo), "--owner-agent", "agent-B",
            "--stdin", "--key-in-url",
            stdin=json.dumps({"url": url + "?k=2", "sender_key": None}))
        self.assertNotEqual(code, 0)
        self.assertEqual(out["reason"], "entry-owned-by-other-agent")
        self.assertEqual(out["owner_agent"], "agent-A")
        # --replace-owner names the exact old label
        code, out = self.hook_json(
            "configure", "--project", str(self.repo), "--owner-agent", "agent-B",
            "--replace-owner", "agent-X",
            "--stdin", "--key-in-url",
            stdin=json.dumps({"url": url + "?k=2", "sender_key": None}))
        self.assertEqual(out["reason"], "entry-owned-by-other-agent")
        code, out = self.hook_json(
            "configure", "--project", str(self.repo), "--owner-agent", "agent-B",
            "--replace-owner", "agent-A",
            "--stdin", "--key-in-url",
            stdin=json.dumps({"url": url + "?k=2", "sender_key": None}))
        self.assertEqual((code, out["result"]), (0, "configured"), out)
        self.assertEqual(self.config_doc()["projects"][self.project]["owner_agent"],
                         "agent-B")
        # B's other project entry survived byte content
        self.assertEqual(self.config_doc()["projects"][other_root]["owner_agent"],
                         "agent-B")
        self.assertEqual(self.config_doc()["projects"][other_root]["url"],
                         url + "?k=1")
        # same-owner rotation overwrites
        code, out = self.configure(url + "?rotated=1", owner="agent-B",
                                   attachment=("--key-in-url",), key=None)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.config_doc()["projects"][self.project]["url"],
                         url + "?rotated=1")
        # remove deletes only the named entry
        code, out = self.hook_json("remove", "--project", str(self.repo),
                                   "--owner-agent", "agent-B")
        self.assertEqual(out["result"], "removed")
        self.assertNotIn(self.project, self.config_doc()["projects"])
        self.assertIn(other_root, self.config_doc()["projects"])


class DeliveryCli(WebhookCase):
    def test_delivered_header_and_url_forms(self) -> None:
        self.endpoint = Endpoint()
        # header form
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        code, out = self.hook_json("test", "--project", str(self.repo))
        self.assertEqual((code, out["result"]), (0, "delivered"), out)
        self.assertEqual(out["schema"], "kaola-delegator-webhook-test/1")
        self.assertEqual(len(out["receipts"]), 1)
        receipt = out["receipts"][0]
        self.assertEqual(set(receipt) - {"reason"}, ATTEMPT_RECEIPT_KEYS)
        self.assertEqual(receipt["http_status"], 200)
        self.assertIsNone(receipt["error"])
        self.assertTrue(receipt["final"])
        self.assertEqual(receipt["state"], "test")
        post = wait_for(lambda: self.endpoint.posts[-1] if self.endpoint.posts
                        else None, 5, "POST arrived")
        self.assertEqual(post["headers"].get(HEADER_NAME),
                         HEADER_PREFIX + SENTINEL_KEY)
        self.assertEqual(post["body"]["schema"], "kaola-delegator-wake/1")
        self.assertEqual(set(post["body"]), PAYLOAD_KEYS)
        # receipts file on disk, 0600, no secrets inside
        raw = self.receipts_path().read_bytes()
        self.assertEqual(self.receipts_path().stat().st_mode & 0o777, 0o600)
        self.assertNotIn(SENTINEL_KEY.encode(), raw)
        self.assertNotIn(self.endpoint.url.encode(), raw)
        # url form: key travels inside the URL, no extra header
        key_url = f"{self.endpoint.url}?sender_key={SENTINEL_KEY}"
        code, out = self.configure(key_url, key=None,
                                   attachment=("--key-in-url",))
        self.assertEqual(code, 0, out)
        self.endpoint.posts.clear()
        code, out = self.hook_json("test", "--project", str(self.repo))
        self.assertEqual((code, out["result"]), (0, "delivered"), out)
        post = wait_for(lambda: self.endpoint.posts[-1] if self.endpoint.posts
                        else None, 5, "POST arrived")
        self.assertIn(SENTINEL_KEY, post["path"])
        self.assertNotIn(HEADER_NAME, post["headers"])

    def test_not_configured_disabled_and_bad_mode(self) -> None:
        self.endpoint = Endpoint()
        payload = {"schema": "kaola-delegator-wake/1", "project": self.project,
                   "session": "s1", "holder_instance_id": "h1",
                   "event_seq": 3, "state": "end_turn",
                   "ts": "2026-01-01T00:00:00Z"}
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0)
        [receipt] = self.receipts()
        self.assertEqual((receipt["result"], receipt["reason"]),
                         ("skipped", "not-configured"))
        self.assertFalse(self.endpoint.posts)
        # enabled: false — same skip
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": SENTINEL_KEY,
            "sender_key_attachment": {"style": "header", "name": HEADER_NAME},
            "enabled": False, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.receipts()[-1]["result"], "skipped")
        self.assertFalse(self.endpoint.posts)
        # a group-readable config fails as config-mode with no POST
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": SENTINEL_KEY,
            "sender_key_attachment": {"style": "header", "name": HEADER_NAME},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}}, mode=0o644)
        proc = self.deliver(payload)
        self.assertNotEqual(proc.returncode, 0)
        last = self.receipts()[-1]
        self.assertEqual((last["result"], last["error"]), ("failed", "config-mode"))
        self.assertFalse(self.endpoint.posts)

    def test_retry_policy_and_redirect_refusal(self) -> None:
        self.endpoint = Endpoint()
        # 500: retried to max_attempts
        self.write_config({self.project: {
            "url": f"http://127.0.0.1:{self.endpoint.port}/err",
            "sender_key": None, "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        payload = {"schema": "kaola-delegator-wake/1", "project": self.project,
                   "session": "s1", "holder_instance_id": "h1",
                   "event_seq": 1, "state": "test", "ts": "2026-01-01T00:00:00Z"}
        code, out = self.hook_json("test", "--project", str(self.repo))
        self.assertNotEqual(code, 0)
        self.assertEqual(len(out["receipts"]), 4)
        self.assertTrue(all(r["error"] == "http-status" and r["http_status"] == 500
                            for r in out["receipts"]))
        self.assertTrue(out["receipts"][-1]["final"])
        # redirect: refused without retry
        self.write_config({self.project: {
            "url": f"http://127.0.0.1:{self.endpoint.port}/redirect",
            "sender_key": None, "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        code, out = self.hook_json("test", "--project", str(self.repo))
        self.assertNotEqual(code, 0)
        self.assertEqual(len(out["receipts"]), 1)
        self.assertEqual(out["receipts"][0]["error"], "redirect-refused")
        # non-retryable 4xx: one attempt, final
        closed = socket_probe_closed_port()
        self.write_config({self.project: {
            "url": f"http://127.0.0.1:{closed}/hook",
            "sender_key": None, "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        proc = self.deliver({"schema": "kaola-delegator-wake/1",
                             "project": self.project, "session": "s1",
                             "holder_instance_id": "h1", "event_seq": 2,
                             "state": "end_turn", "ts": "2026-01-01T00:00:00Z"})
        self.assertNotEqual(proc.returncode, 0)
        last = self.receipts()[-4:]
        self.assertTrue(all(r["error"] == "connection" for r in last))

    def test_receipt_ring_bound_and_deliver_argv(self) -> None:
        self.endpoint = Endpoint(sleep_seconds=4.0)
        url = f"{self.endpoint.url}?k={SENTINEL_URL_MARK}"
        self.write_config({self.project: {
            "url": url, "sender_key": SENTINEL_KEY,
            "sender_key_attachment": {"style": "header", "name": HEADER_NAME,
                                      "prefix": HEADER_PREFIX},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        # the detached child's argv must carry no secret and no holder name
        proc = subprocess.Popen([sys.executable, str(CLI),
                                 "delegator-webhook", "deliver"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                env=self.env())
        assert proc.stdin is not None
        proc.stdin.write(json.dumps({"schema": "kaola-delegator-wake/1",
                                     "project": self.project, "session": "s1",
                                     "holder_instance_id": "h1",
                                     "event_seq": 0, "state": "test",
                                     "ts": "2026-01-01T00:00:00Z"}).encode())
        try:
            argv = subprocess.run(["ps", "-o", "command=", "-p", str(proc.pid)],
                                  capture_output=True, text=True).stdout
            self.assertIn("delegator-webhook", argv)
            self.assertIn("deliver", argv)
            for sentinel in (SENTINEL_URL_MARK, SENTINEL_KEY, url):
                self.assertNotIn(sentinel, argv)
            self.assertNotIn("kaola-acp-holder", argv)
        finally:
            try:
                proc.stdin.close()
            except OSError:
                pass
            proc.kill()
            proc.wait()
        # ring bound: 36 attempts keep the last 32
        self.endpoint.stop()
        self.endpoint = Endpoint()
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        for seq in range(36):
            proc = self.deliver({"schema": "kaola-delegator-wake/1",
                                 "project": self.project, "session": "s1",
                                 "holder_instance_id": "h1", "event_seq": seq,
                                 "state": "end_turn",
                                 "ts": "2026-01-01T00:00:00Z"})
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        receipts = self.receipts()
        self.assertEqual(len(receipts), 32)
        self.assertEqual(receipts[0]["event_seq"], 4)
        self.assertEqual(receipts[-1]["event_seq"], 35)


def socket_probe_closed_port() -> int:
    import socket as _socket
    sock = _socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class HolderWakes(WebhookCase):
    def test_turn_end_delivers_one_signal(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("turn")
        code, sent = self.send("--wait")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        receipt = wait_for(
            lambda: next((r for r in self.receipts()
                          if r.get("state") == "end_turn"), None),
            15, "end_turn delivered receipt")
        self.assertEqual(receipt["result"], "delivered")
        posts = wait_for(
            lambda: [p for p in self.endpoint.posts
                     if (p["body"] or {}).get("state") == "end_turn"],
            5, "end_turn POST")
        self.assertEqual(len(posts), 1)
        body = posts[0]["body"]
        self.assertEqual(set(body), PAYLOAD_KEYS)
        self.assertEqual(body["schema"], "kaola-delegator-wake/1")
        self.assertEqual(body["project"], self.project)
        self.assertEqual(body["session"], self.session)
        self.assertIsInstance(body["event_seq"], int)
        self.assertIsInstance(body["holder_instance_id"], str)
        self.assertRegex(body["ts"], r"^\d{4}-\d{2}-\d{2}T")

    def test_unconfigured_skips_without_network(self) -> None:
        self.endpoint = Endpoint()
        self.start_host("skip")
        code, sent = self.send("--wait")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        receipt = wait_for(lambda: self.receipts()[-1] if self.receipts() else None,
                           15, "skipped receipt")
        self.assertEqual((receipt["result"], receipt["reason"]),
                         ("skipped", "not-configured"))
        self.assertEqual(receipt["state"], "end_turn")
        self.assertFalse(self.endpoint.posts)

    def test_unreachable_never_blocks_the_holder(self) -> None:
        # a dead port: the child retries in the background; the send is not
        # held by the delivery path (well under the 3 s attempt timeout)
        closed = socket_probe_closed_port()
        self.write_config({self.project: {
            "url": f"http://127.0.0.1:{closed}/hook", "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        self.start_host("down")
        started = time.monotonic()
        code, sent = self.send("--wait")
        elapsed = time.monotonic() - started
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        self.assertLess(elapsed, 2.5, "send was held by webhook delivery")
        wait_for(lambda: any(r.get("state") == "end_turn"
                             and r.get("result") == "failed"
                             for r in self.receipts()),
                 15, "failed connection receipt")
        self.assertTrue(any(r.get("error") == "connection"
                            for r in self.receipts()))
        # a slow endpoint: same non-blocking shape, timeout classification
        self.endpoint = Endpoint(sleep_seconds=4.0)
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        started = time.monotonic()
        code, sent = self.send("--wait")
        elapsed = time.monotonic() - started
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        self.assertLess(elapsed, 3.0, "send was held by webhook delivery")
        wait_for(lambda: any(r.get("error") == "timeout" for r in self.receipts()),
                 20, "timeout receipt")

    def test_no_secret_leaks_into_records_or_output(self) -> None:
        self.endpoint = Endpoint()
        url = f"{self.endpoint.url}?mark={SENTINEL_URL_MARK}"
        code, out = self.configure(url, key=None, attachment=("--key-in-url",))
        self.assertEqual(code, 0, out)
        self.start_host("leak")
        self.send("--wait")
        wait_for(lambda: any(r.get("state") == "end_turn" for r in self.receipts()),
                 15, "delivered receipt")
        surfaces = {"receipts": self.receipts_path().read_bytes()}
        _, status = self.hook_json("status", "--project", str(self.repo))
        surfaces["status"] = json.dumps(status).encode()
        _, test_out = self.hook_json("test", "--project", str(self.repo))
        surfaces["test"] = json.dumps(test_out).encode()
        for op in ("status", "observe", "capture"):
            _, receipt = self.acp(op, check=False)
            surfaces[op] = json.dumps(receipt).encode()
        record_dir = self.record_root / "grok" / self.session
        records = list(record_dir.rglob("record.json"))
        self.assertTrue(records)
        for path in records:
            surfaces[str(path)] = path.read_bytes()
        events = list(record_dir.rglob("events.jsonl"))
        for path in events:
            surfaces[str(path)] = path.read_bytes()
        for name, blob in surfaces.items():
            for sentinel in (SENTINEL_URL_MARK, SENTINEL_KEY):
                self.assertNotIn(sentinel.encode(), blob,
                                 f"{sentinel} leaked into {name}")
        self.assertRegex(status["fingerprint"], r"^[0-9a-f]{12}$")
        self.assertIs(status["sender_key_present"], False)  # key lives in the url
        self.assertTrue(status["configured"])

    def test_blocked_and_stopped_wakes(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("perm", scenario="permission_gate")
        code, sent = self.send("--no-wait", scenario="permission_gate")
        blocked = wait_for(
            lambda: next((r for r in self.receipts()
                          if r.get("state") == "blocked"), None),
            15, "blocked receipt")
        self.assertEqual(blocked["result"], "delivered")
        # resolve the pending permission so the turn can end
        _, obs = self.acp("observe", scenario="permission_gate")
        pending = obs.get("pending_permissions") or []
        self.assertTrue(pending, obs)
        _, permit = self.acp("permit", "--request-id",
                             str(pending[0]["request_id"]),
                             "--option", pending[0]["options"][0]["id"],
                             scenario="permission_gate")
        wait_for(lambda: any(r.get("state") == "end_turn"
                             for r in self.receipts()),
                 15, "end_turn receipt")
        # stop: the inline spawn hands the payload off before the reply
        code, stopped = self.acp("stop", scenario="permission_gate")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.session = None  # already stopped
        wait_for(lambda: any(r.get("state") == "stopped" for r in self.receipts()),
                 15, "stopped receipt")
        states = {(p["body"] or {}).get("state") for p in self.endpoint.posts}
        self.assertIn("blocked", states)
        self.assertIn("stopped", states)


class RecordContractWakeMode(WebhookCase):
    def delegator_file(self) -> Path:
        path = self.repo / ".kaola" / "delegator-heartbeat.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(
            {"schema": "kaola-delegator-heartbeat/1", "revision": 0}))
        return path

    def update(self, path: Path, set_value: dict, revision: int) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(DISPATCH), "delegator", "update",
             "--file", str(path), "--writer", "delegator", "--source", "evt",
             "--expect-revision", str(revision), "--set", json.dumps(set_value)],
            capture_output=True, text=True, env=self.env())
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError:
            self.fail(f"delegator update not JSON: {proc.stdout!r} "
                      f"stderr={proc.stderr!r}")

    def test_wake_mode_accepted_and_refused(self) -> None:
        path = self.delegator_file()
        code, out = self.update(path, {"timer_owner": {
            "platform": "grok", "native_timer_id": "cron-1",
            "wake_mode": "webhook+heartbeat", "webhook_routine_id": "r1"}}, 0)
        self.assertEqual((code, out["result"]), (0, "written"), out)
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["timer_owner"]["wake_mode"], "webhook+heartbeat")
        self.assertEqual(stored["timer_owner"]["webhook_routine_id"], "r1")
        code, out = self.update(path, {"timer_owner": {
            "platform": "grok", "native_timer_id": "cron-1",
            "wake_mode": "push"}}, 1)
        self.assertNotEqual(code, 0)
        self.assertEqual(out["result"], "refused")
        self.assertTrue(any(b["path"] == "timer_owner.wake_mode"
                            for b in out.get("blockers", [])), out)
        # the refused write left the file unchanged
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["timer_owner"]["wake_mode"], "webhook+heartbeat")
        # delegator view shows both fields
        proc = subprocess.run(
            [sys.executable, str(DISPATCH), "delegator", "view",
             "--file", str(path)],
            capture_output=True, text=True, env=self.env())
        view = json.loads(proc.stdout)
        self.assertEqual(view["timer_owner"]["wake_mode"], "webhook+heartbeat")
        self.assertEqual(view["timer_owner"]["webhook_routine_id"], "r1")


if __name__ == "__main__":
    unittest.main()
