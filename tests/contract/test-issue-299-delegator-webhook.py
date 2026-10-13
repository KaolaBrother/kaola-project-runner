#!/usr/bin/env python3
"""Issue #299: Delegator webhook wake.

Contract coverage, all offline:

- the ``delegator-webhook`` CLI on ``kaola-acp.py`` (configure/status/test/
  remove/deliver), its config modes and ownership rules, secret-free receipts;
- the Host holder's detached wake child: ``end_turn``, ``blocked``,
  ``stopped`` and the skipped/failed short receipts, through a real holder
  driving ``mock-acp-agent.py``;
- the record contract's ``timer_owner.wake_mode``/``webhook_routine_id``;
- Issue #304: a delivered or failed attempt receipt carries the wake
  ``reason``, a skip carries ``skip_reason`` and no ``reason``, ``status``
  still parses an old receipts file, and a v0.9.5/v0.9.6 payload with no
  ``reason`` (and the earlier shape that also omits ``state_detail``) delivers.

Every test pins ``KAOLA_DELEGATOR_WEBHOOK_CONFIG`` (and HOME) to a temp path —
the real ``~/.config/kaola`` is never touched. The webhook endpoint is a
loopback ``http.server`` only.
"""

from __future__ import annotations

import json
import os
import secrets
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
DISPATCH = REPO / "scripts" / "kaola-dispatch.py"
MOCK = REPO / "tests" / "contract" / "mock-acp-agent.py"

SENTINEL_URL_MARK = "SENTINEL-URL-9f3ac"
SENTINEL_KEY = "SENTINEL-KEY-4c2e1"
HEADER_NAME = "X-Kaola-Wake-Key"
HEADER_PREFIX = "WAKE "

PAYLOAD_KEYS = {"schema", "project", "session", "holder_instance_id",
                "event_seq", "state", "state_detail", "reason", "ts"}
ATTEMPT_RECEIPT_KEYS = {"ts", "state", "state_detail", "session",
                        "holder_instance_id", "event_seq", "result",
                        "attempt", "max_attempts",
                        "http_status", "error", "elapsed_ms", "final",
                        "response_body", "response_body_truncated",
                        "response_headers"}


def wait_for(predicate, timeout: float, label: str, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"timeout: {label}")


class Endpoint:
    """Loopback sink. ``sleep_seconds`` delays the response. ``/err`` answers
    500, ``/redirect`` answers 302, ``/status/<code>`` answers that code,
    anything else 200. An HTTP error writes ``error_body`` plus a small
    allowlisted header set and one unlisted header."""

    def __init__(self, sleep_seconds: float = 0.0):
        self.posts: list[dict] = []
        self.sleep_seconds = sleep_seconds
        self.error_body = b'{"error":"nope"}'
        self.error_headers = {
            "Content-Type": "application/json",
            "Retry-After": "3",
            "X-Request-Id": "req-311",
            "X-Unlisted": "ignore-me",
        }
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
                code = 200
                if self.path.startswith("/err"):
                    code = 500
                elif self.path.startswith("/redirect"):
                    code = 302
                elif self.path.startswith("/status/"):
                    token = self.path.split("/", 2)[-1].split("?", 1)[0]
                    try:
                        code = int(token)
                    except ValueError:
                        code = 200
                self.send_response(code)
                payload = b""
                if code >= 400:
                    payload = outer.error_body
                    for name, value in outer.error_headers.items():
                        self.send_header(name, value)
                elif code in (301, 302, 303, 307, 308):
                    self.send_header("Location", "/hook")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if payload:
                    self.wfile.write(payload)

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
        # Exact stop wakes a detached deliver child. Its receipt replace can
        # recreate a file under .kaola while this tree is being removed.
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

    def _url_config(self, url: str) -> None:
        self.write_config({self.project: {
            "url": url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})

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

    def holder_record(self) -> dict:
        base = self.record_root / "grok" / self.session
        return json.loads(
            next(base.rglob("record.json")).read_text(encoding="utf-8"))

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

    def sigkill_session(self) -> dict:
        """SIGKILL the recorded holder and agent; returns the dead record."""
        record = self.holder_record()
        for pid in (record.get("holder_pid"), record.get("agent_pid")):
            if isinstance(pid, int) and pid > 0:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        wait_for(lambda: self.pid_dead(record.get("holder_pid"))
                 and self.pid_dead(record.get("agent_pid")),
                 5, "session processes dead")
        return record

    def posts_with_detail(self, detail: str) -> list[dict]:
        return [p for p in (self.endpoint.posts if self.endpoint else [])
                if (p["body"] or {}).get("state_detail") == detail]


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

    def test_concurrent_configure_loses_no_entry(self) -> None:
        # Eight configures for eight projects, each a different owner: the
        # sidecar flock is held across read -> ownership check -> write, so
        # every entry survives.
        count = 8
        jobs = []
        for index in range(count):
            proj = self.root / f"proj-{index}"
            proj.mkdir()
            owner = f"agent-{index}"
            jobs.append((proj, owner, subprocess.Popen(
                [sys.executable, str(CLI), "delegator-webhook", "configure",
                 "--project", str(proj), "--owner-agent", owner,
                 "--stdin", "--key-in-url"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=self.env(), text=True)))
        for proj, owner, proc in jobs:
            out, err = proc.communicate(
                json.dumps({"url": "https://hooks.example.invalid/wake",
                            "sender_key": None}), timeout=30)
            self.assertEqual(proc.returncode, 0, f"{owner}: {err}")
            self.assertEqual(json.loads(out)["result"], "configured", out)
        stored = self.config_doc()["projects"]
        for proj, owner, _ in jobs:
            root = os.path.realpath(str(proj))
            self.assertIn(root, stored)
            self.assertEqual(stored[root]["owner_agent"], owner)


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
        self.assertEqual(set(receipt), ATTEMPT_RECEIPT_KEYS | {"reason"})
        self.assertEqual(receipt["reason"], "test")
        self.assertNotIn("skip_reason", receipt)
        self.assertEqual(receipt["http_status"], 200)
        self.assertIsNone(receipt["error"])
        self.assertIsNone(receipt["response_body"])
        self.assertIs(receipt["response_body_truncated"], False)
        self.assertIsNone(receipt["response_headers"])
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
                   "event_seq": 3, "state": "end_turn", "state_detail": None,
                   "reason": "host_stopped_pending",
                   "ts": "2026-01-01T00:00:00Z"}
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0)
        [receipt] = self.receipts()
        self.assertEqual((receipt["result"], receipt["skip_reason"]),
                         ("skipped", "not-configured"))
        self.assertNotIn("reason", receipt)
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
        self.assertEqual(self.receipts()[-1]["skip_reason"], "not-configured")
        self.assertNotIn("reason", self.receipts()[-1])
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
        self.assertEqual(last["reason"], "host_stopped_pending")
        self.assertNotIn("skip_reason", last)
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
                   "event_seq": 1, "state": "test", "state_detail": "test",
                   "reason": "test",
                   "ts": "2026-01-01T00:00:00Z"}
        code, out = self.hook_json("test", "--project", str(self.repo))
        self.assertNotEqual(code, 0)
        self.assertEqual(len(out["receipts"]), 4)
        self.assertTrue(all(r["error"] == "http-status" and r["http_status"] == 500
                            for r in out["receipts"]))
        self.assertTrue(all(r["reason"] == "test" and "skip_reason" not in r
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
                             "state": "end_turn", "state_detail": None,
                             "reason": "host_stopped_pending",
                             "ts": "2026-01-01T00:00:00Z"})
        self.assertNotEqual(proc.returncode, 0)
        last = self.receipts()[-4:]
        self.assertTrue(all(r["error"] == "connection" for r in last))
        self.assertTrue(all(r["reason"] == "host_stopped_pending" for r in last))

    def test_deliver_refuses_non_signal_payload(self) -> None:
        self.endpoint = Endpoint()
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        base = {"schema": "kaola-delegator-wake/1", "project": self.project,
                "session": "s1", "holder_instance_id": "h1", "event_seq": 1,
                "state": "end_turn", "state_detail": "end_turn",
                "reason": "host_stopped_pending",
                "ts": "2026-01-01T00:00:00Z"}
        bad_payloads = []
        for mutate in (lambda p: p.update(extra="x"),
                       lambda p: p.pop("ts"),
                       lambda p: p.pop("schema"),
                       lambda p: p.pop("holder_instance_id"),
                       lambda p: p.pop("event_seq"),
                       # reason without state_detail is not a shipped shape
                       lambda p: p.pop("state_detail"),
                       lambda p: p.update(reason="not_a_reason"),
                       lambda p: p.update(reason="bad token"),
                       lambda p: p.update(schema="kaola-delegator-wake/2"),
                       lambda p: p.update(state="ping"),
                       lambda p: p.update(event_seq=True),
                       lambda p: p.update(event_seq="1"),
                       lambda p: p.update(state_detail=123),
                       lambda p: p.update(state_detail="with space")):
            payload = dict(base)
            mutate(payload)
            bad_payloads.append(payload)
        for payload in bad_payloads + [[], "x"]:
            proc = self.deliver(payload)
            self.assertEqual(proc.returncode, 1)
        self.assertFalse(self.endpoint.posts)
        invalid = [r for r in self.receipts()
                   if r.get("error") == "invalid-payload"]
        self.assertEqual(len(invalid), len(bad_payloads))
        self.assertTrue(all(r["result"] == "failed" and r["final"]
                            for r in invalid))
        # a payload whose project does not resolve records nothing
        proc = self.deliver({"project": str(self.root / "no-such-dir")})
        self.assertEqual(proc.returncode, 1)
        self.assertFalse((self.root / "no-such-dir" / ".kaola").exists())
        # the valid shape still delivers
        proc = self.deliver(dict(base))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.endpoint.posts[-1]["body"], base)

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
                                     "event_seq": 0, "state": "test", "state_detail": "test",
                                     "reason": "test",
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
                                 "state": "end_turn", "state_detail": None,
                                 "reason": "host_stopped_pending",
                                 "ts": "2026-01-01T00:00:00Z"})
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        receipts = self.receipts()
        self.assertEqual(len(receipts), 32)
        self.assertEqual(receipts[0]["event_seq"], 4)
        self.assertEqual(receipts[-1]["event_seq"], 35)
        self.assertTrue(all(item["reason"] == "host_stopped_pending"
                            and "skip_reason" not in item for item in receipts))
        # receipt atomic writes leave no stray temp files in .kaola
        kaola_dir = self.repo / ".kaola"
        self.assertFalse(list(kaola_dir.glob("*.tmp")))

    def test_delivered_failed_and_skipped_receipt_fields(self) -> None:
        self.endpoint = Endpoint()
        self._url_config(self.endpoint.url)
        payload = {"schema": "kaola-delegator-wake/1", "project": self.project,
                   "session": "s1", "holder_instance_id": "h1", "event_seq": 11,
                   "state": "end_turn", "state_detail": "end_turn",
                   "reason": "delivery_review", "ts": "2026-01-01T00:00:00Z"}
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        delivered = self.receipts()[-1]
        self.assertEqual(delivered["result"], "delivered")
        self.assertEqual(delivered["reason"], "delivery_review")
        self.assertNotIn("skip_reason", delivered)
        self.assertEqual(set(delivered), ATTEMPT_RECEIPT_KEYS | {"reason"})

        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["schema"], "kaola-delegator-webhook-status/1")
        self.assertEqual(status["last_receipt"]["reason"], "delivery_review")
        self.assertEqual(status["last_receipt"]["result"], "delivered")
        self.assertIsNone(status["last_test"])
        self.assertIn("receipts_path", status)

        code, tested = self.hook_json("test", "--project", str(self.repo))
        self.assertEqual((code, tested["result"]), (0, "delivered"), tested)
        self.assertEqual(tested["receipts"][0]["reason"], "test")
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["schema"], "kaola-delegator-webhook-status/1")
        self.assertEqual(status["last_test"]["result"], "delivered")
        self.assertEqual(status["last_test"]["state"], "test")
        self.assertEqual(status["last_test"]["reason"], "test")
        self.assertNotIn("skip_reason", status["last_test"])

        self.endpoint.posts.clear()
        proc = self.deliver(payload)
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(self.endpoint.posts)
        duplicate = self.receipts()[-1]
        self.assertEqual(duplicate["result"], "skipped")
        self.assertEqual(duplicate["skip_reason"], "duplicate")
        self.assertNotIn("reason", duplicate)
        self.assertEqual(set(duplicate), ATTEMPT_RECEIPT_KEYS | {"skip_reason"})

        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": False, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        skipped_payload = dict(payload)
        skipped_payload["event_seq"] = 12
        proc = self.deliver(skipped_payload)
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(self.endpoint.posts)
        skipped = self.receipts()[-1]
        self.assertEqual(skipped["skip_reason"], "not-configured")
        self.assertNotIn("reason", skipped)

        self._url_config(f"http://127.0.0.1:{self.endpoint.port}/status/401")
        failed_payload = dict(payload)
        failed_payload["event_seq"] = 13
        failed_payload["reason"] = "turn_failed"
        proc = self.deliver(failed_payload)
        self.assertEqual(proc.returncode, 1)
        failed = self.receipts()[-1]
        self.assertEqual(failed["result"], "failed")
        self.assertEqual(failed["reason"], "turn_failed")
        self.assertEqual(failed["http_status"], 401)
        self.assertEqual(failed["attempt"], 1)
        self.assertIs(failed["final"], True)
        self.assertEqual(failed["response_body"], '{"error":"nope"}')
        self.assertIs(failed["response_body_truncated"], False)
        self.assertEqual(failed["response_headers"]["content-type"], "application/json")
        self.assertEqual(failed["response_headers"]["retry-after"], "3")
        self.assertEqual(failed["response_headers"]["x-request-id"], "req-311")
        self.assertNotIn("x-unlisted", failed["response_headers"])
        self.assertNotIn("skip_reason", failed)
        self.assertEqual(self.endpoint.posts[-1]["body"]["reason"], "turn_failed")
        self.assertEqual(len(self.endpoint.posts), 1)

    def test_status_reads_pre_304_receipts_unchanged(self) -> None:
        path = self.receipts_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "schema": "kaola-delegator-webhook-receipts/1",
            "limit": 32,
            "receipts": [
                {
                    "ts": "2026-10-11T00:00:00Z", "state": "test",
                    "state_detail": "test", "session": None,
                    "holder_instance_id": "test-old", "event_seq": 0,
                    "result": "delivered", "attempt": 1, "max_attempts": 4,
                    "http_status": 200, "error": None, "elapsed_ms": 3,
                    "final": True,
                },
                {
                    "ts": "2026-10-11T00:00:01Z", "state": "end_turn",
                    "state_detail": None, "session": "s1",
                    "holder_instance_id": "h1", "event_seq": 1,
                    "result": "skipped", "reason": "not-configured",
                    "attempt": 0, "max_attempts": 4, "http_status": None,
                    "error": None, "elapsed_ms": 0, "final": True,
                },
            ],
        }
        path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        path.chmod(0o600)
        before = path.read_bytes()
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["schema"], "kaola-delegator-webhook-status/1")
        self.assertEqual(status["last_test"]["result"], "delivered")
        self.assertEqual(status["last_test"]["state"], "test")
        self.assertNotIn("reason", status["last_test"])
        self.assertNotIn("skip_reason", status["last_test"])
        self.assertEqual(status["last_receipt"]["result"], "skipped")
        self.assertEqual(status["last_receipt"]["reason"], "not-configured")
        self.assertNotIn("skip_reason", status["last_receipt"])
        self.assertEqual(path.read_bytes(), before)

    def test_old_shape_payload_delivers_malformed_is_refused(self) -> None:
        self.endpoint = Endpoint()
        self._url_config(self.endpoint.url)
        v096 = {
            "schema": "kaola-delegator-wake/1", "project": self.project,
            "session": "s1", "holder_instance_id": "h-old", "event_seq": 3626,
            "state": "end_turn", "state_detail": "end_turn",
            "ts": "2026-10-11T10:58:00Z",
        }
        proc = self.deliver(v096)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.endpoint.posts[-1]["body"], v096)
        self.assertNotIn("reason", self.endpoint.posts[-1]["body"])
        receipt = self.receipts()[-1]
        self.assertEqual(receipt["result"], "delivered")
        self.assertIn("reason", receipt)
        self.assertIsNone(receipt["reason"])
        self.assertNotIn("skip_reason", receipt)
        self.assertEqual(receipt["state_detail"], "end_turn")

        null_detail = dict(v096)
        null_detail["state_detail"] = None
        null_detail["event_seq"] = 3627
        proc = self.deliver(null_detail)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.endpoint.posts[-1]["body"], null_detail)
        self.assertIsNone(self.receipts()[-1]["reason"])
        self.assertIsNone(self.receipts()[-1]["state_detail"])

        early = {key: value for key, value in v096.items() if key != "state_detail"}
        early["event_seq"] = 3635
        proc = self.deliver(early)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.endpoint.posts[-1]["body"], early)
        self.assertNotIn("state_detail", self.endpoint.posts[-1]["body"])
        receipt = self.receipts()[-1]
        self.assertEqual(receipt["result"], "delivered")
        self.assertIsNone(receipt["reason"])
        self.assertIsNone(receipt["state_detail"])

        self._url_config(f"http://127.0.0.1:{self.endpoint.port}/status/404")
        failed = dict(v096)
        failed["event_seq"] = 3639
        proc = self.deliver(failed)
        self.assertEqual(proc.returncode, 1)
        failed_receipt = self.receipts()[-1]
        self.assertEqual(failed_receipt["result"], "failed")
        self.assertIsNone(failed_receipt["reason"])
        self.assertEqual(failed_receipt["error"], "http-status")
        self.assertEqual(failed_receipt["http_status"], 404)
        self.assertEqual(failed_receipt["attempt"], 1)
        self.assertIs(failed_receipt["final"], True)
        self.assertNotIn("skip_reason", failed_receipt)
        self.assertNotIn("reason", self.endpoint.posts[-1]["body"])

        self._url_config(self.endpoint.url)
        posts_before = len(self.endpoint.posts)
        base = dict(v096)
        base["reason"] = "delivery_review"
        base["state_detail"] = "end_turn"
        base["event_seq"] = 3700
        for key in ("schema", "holder_instance_id", "event_seq"):
            bad = dict(base)
            bad.pop(key)
            proc = self.deliver(bad)
            self.assertEqual(proc.returncode, 1, key)
        self.assertEqual(len(self.endpoint.posts), posts_before)
        refused = [item for item in self.receipts()
                   if item.get("error") == "invalid-payload"]
        self.assertEqual(len(refused), 3)
        self.assertTrue(all(
            item["result"] == "failed" and item["reason"] == "delivery_review"
            and "skip_reason" not in item for item in refused))

        # A previous shape that also lacks schema is refused, and the receipt
        # records the honest absent reason.
        bare = dict(early)
        bare.pop("schema")
        bare["event_seq"] = 3701
        proc = self.deliver(bare)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(len(self.endpoint.posts), posts_before)
        self.assertEqual(self.receipts()[-1]["error"], "invalid-payload")
        self.assertIsNone(self.receipts()[-1]["reason"])

    def test_http_400_retries_and_stores_a_redacted_truncated_body(self) -> None:
        import urllib.parse
        self.endpoint = Endpoint()
        key = "sek/311"
        url = f"http://127.0.0.1:{self.endpoint.port}/status/400"
        encoded = urllib.parse.quote(key, safe="")
        self.write_config({self.project: {
            "url": url, "sender_key": key,
            "sender_key_attachment": {"style": "header", "name": HEADER_NAME,
                                      "prefix": "Bearer "},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        self.endpoint.error_body = f"{url} {key} {encoded} ".encode() + (b"B" * 700)
        self.endpoint.error_headers["X-Request-Id"] = key
        self.endpoint.error_headers["Www-Authenticate"] = "Bearer " + key
        payload = {"schema": "kaola-delegator-wake/1", "project": self.project,
                   "session": "s1", "holder_instance_id": "h-400", "event_seq": 40,
                   "state": "error", "state_detail": "turn_failed",
                   "reason": "turn_failed", "ts": "2026-01-01T00:00:00Z"}
        proc = self.deliver(payload, timeout=30)
        self.assertNotEqual(proc.returncode, 0)
        matching = [item for item in self.receipts() if item.get("event_seq") == 40]
        self.assertEqual(len(matching), 4)
        self.assertTrue(all(item["http_status"] == 400 and item["error"] == "http-status"
                            for item in matching))
        self.assertIs(matching[0]["final"], False)
        self.assertIs(matching[-1]["final"], True)
        self.assertEqual(len(self.endpoint.posts), 4)
        for item in matching:
            blob = json.dumps(item)
            self.assertIs(item["response_body_truncated"], True)
            self.assertEqual(len(item["response_body"]), 512)
            self.assertIn("[redacted]", item["response_body"])
            self.assertNotIn(key, blob)
            self.assertNotIn(encoded, blob)
            self.assertNotIn(url, blob)
            self.assertEqual(item["response_headers"]["x-request-id"], "[redacted]")
            self.assertEqual(item["response_headers"]["www-authenticate"], "Bearer [redacted]")
            self.assertNotIn("x-unlisted", item["response_headers"])
        raw = self.receipts_path().read_text(encoding="utf-8")
        self.assertNotIn(key, raw)
        self.assertNotIn(encoded, raw)
        self.assertNotIn(url, raw)


class HolderLostStatus(WebhookCase):
    """Issue #311: ``delegator-webhook status`` is the holder-lost detector.

    ``test`` does not scan. A skipped scan does not write the death event.
    """

    def dead_pid(self) -> int:
        for _ in range(5):
            proc = subprocess.Popen(["/bin/sleep", "0"])
            proc.wait(timeout=5)
            try:
                os.kill(proc.pid, 0)
            except ProcessLookupError:
                return proc.pid
            except PermissionError:
                continue
        self.fail("could not observe a dead pid")

    def write_record(self, session: str, *, role: str = "host", state: str = "ready",
                     pid: int | None = None, agent_pid: int | None = None) -> Path:
        directory = self.record_root / "zcode" / session / "abcd"
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "repo": self.project,
            "session": session,
            "platform": "zcode",
            "session_role": role,
            "holder_instance_id": "hid-" + session,
            "holder_pid": self.dead_pid() if pid is None else pid,
            "state": state,
        }
        if agent_pid is not None:
            record["agent_pid"] = agent_pid
        (directory / "record.json").write_text(json.dumps(record), encoding="utf-8")
        return directory

    def death_lines(self, directory: Path) -> list[dict]:
        path = directory / "events.jsonl"
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if isinstance(item, dict) and item.get("kind") == "delegator_death_wake":
                rows.append(item)
        return rows

    def test_status_wakes_a_dead_host_once_through_the_mock(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        session = "zcode-i311-orchestrator-main"
        directory = self.write_record(session)
        self.write_record("zcode-i311-worker", role="elite")
        self.write_record("zcode-i311-stopped", state="stopped")
        self.write_record("zcode-i311-agent-alive", agent_pid=os.getpid())
        self.write_record("zcode-i311-live-holder", pid=os.getpid())
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        holder_lost = status["holder_lost"]
        self.assertEqual(holder_lost["scan"], "complete")
        self.assertEqual(holder_lost["leg"], "delegator-webhook status")
        self.assertEqual(len(holder_lost["wakes"]), 1, holder_lost)
        wake = holder_lost["wakes"][0]
        self.assertEqual(wake["session"], session)
        self.assertEqual(wake["holder_instance_id"], "hid-" + session)
        self.assertTrue(wake["delegator_death_wake"]["sent"], wake)
        post = wait_for(
            lambda: next((item for item in self.endpoint.posts
                          if (item["body"] or {}).get("reason") == "holder_lost"), None),
            15, "holder_lost POST")
        body = post["body"]
        self.assertEqual(body["state"], "error")
        self.assertEqual(body["state_detail"], "holder_lost")
        self.assertEqual(body["reason"], "holder_lost")
        self.assertEqual(body["holder_instance_id"], "hid-" + session)
        self.assertEqual(body["session"], session)
        self.assertEqual(set(body), PAYLOAD_KEYS)
        self.assertEqual(len(self.death_lines(directory)), 1)
        code, again = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        second = again["holder_lost"]["wakes"][0]["delegator_death_wake"]
        self.assertFalse(second["sent"])
        self.assertEqual(second["reason"], "already-recovered")
        time.sleep(0.4)
        lost = [item for item in self.endpoint.posts
                if (item["body"] or {}).get("reason") == "holder_lost"]
        self.assertEqual(len(lost), 1)
        raw = json.dumps(status) + json.dumps(again) + self.receipts_path().read_text(encoding="utf-8")
        self.assertNotIn(SENTINEL_KEY, raw)
        self.assertNotIn(self.endpoint.url, raw)

    def test_skipped_scan_and_test_do_not_consume_the_death_event(self) -> None:
        session = "zcode-i311-orchestrator-later"
        directory = self.write_record(session)
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(status["holder_lost"]["scan"], "skipped")
        self.assertEqual(status["holder_lost"]["reason"], "not-enabled")
        self.assertEqual(status["holder_lost"]["wakes"], [])
        self.assertFalse((directory / "events.jsonl").exists())
        self.endpoint = Endpoint()
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": False, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(status["holder_lost"]["reason"], "not-enabled")
        self.assertFalse((directory / "events.jsonl").exists())
        code, tested = self.hook_json("test", "--project", str(self.repo))
        self.assertNotEqual(code, 0)
        self.assertNotIn("holder_lost", tested)
        self.assertEqual(tested["result"], "skipped")
        self.assertFalse((directory / "events.jsonl").exists())
        self._url_config(self.endpoint.url)
        code, status = self.hook_json("status", "--project", str(self.repo))
        self.assertEqual(status["holder_lost"]["scan"], "complete")
        self.assertTrue(status["holder_lost"]["wakes"][0]["delegator_death_wake"]["sent"])
        wait_for(lambda: any((item["body"] or {}).get("reason") == "holder_lost"
                             for item in self.endpoint.posts),
                 15, "holder_lost POST after enable")
        self.assertEqual(len(self.death_lines(directory)), 1)


def socket_probe_closed_port() -> int:
    import socket as _socket
    sock = _socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class HolderWakes(WebhookCase):
    def test_turn_end_delivers_one_signal(self) -> None:
        # No worker is live, so the Delegator's own send wakes all-idle.
        # Exact stop still wakes, and it carries the signal shape.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("turn")
        code, sent = self.send("--wait")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        idle = wait_for(
            lambda: next((p for p in self.endpoint.posts
                          if (p["body"] or {}).get("reason") == "all-idle"), None),
            10, "all-idle POST")
        self.assertEqual(idle["body"]["state"], "end_turn")
        code, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.session = None
        receipt = wait_for(
            lambda: next((r for r in self.receipts()
                          if r.get("state") == "stopped"), None),
            15, "stopped delivered receipt")
        self.assertEqual(receipt["result"], "delivered")
        posts = wait_for(
            lambda: [p for p in self.endpoint.posts
                     if (p["body"] or {}).get("state") == "stopped"],
            5, "stopped POST")
        self.assertEqual(len(posts), 1)
        body = posts[0]["body"]
        self.assertEqual(set(body), PAYLOAD_KEYS)
        self.assertEqual(body["schema"], "kaola-delegator-wake/1")
        self.assertEqual(body["project"], self.project)
        self.assertEqual(body["session"], "grok-w299-orchestrator-turn")
        self.assertEqual(body["state_detail"], "exact_stop")
        self.assertEqual(body["reason"], "exact_stop")
        self.assertIsInstance(body["event_seq"], int)
        self.assertIsInstance(body["holder_instance_id"], str)
        self.assertRegex(body["ts"], r"^\d{4}-\d{2}-\d{2}T")

    def test_unconfigured_skips_without_network(self) -> None:
        self.endpoint = Endpoint()
        self.start_host("skip")
        code, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.session = None
        receipt = wait_for(lambda: self.receipts()[-1] if self.receipts() else None,
                           15, "skipped receipt")
        self.assertEqual((receipt["result"], receipt["skip_reason"]),
                         ("skipped", "not-configured"))
        self.assertNotIn("reason", receipt)
        self.assertEqual(receipt["state"], "stopped")
        self.assertFalse(self.endpoint.posts)

    def test_unreachable_never_blocks_the_holder(self) -> None:
        # Exact stop is the wake. A dead port retries in the background; stop
        # itself returns immediately.
        closed = socket_probe_closed_port()
        self.write_config({self.project: {
            "url": f"http://127.0.0.1:{closed}/hook", "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        self.start_host("down")
        started = time.monotonic()
        code, stopped = self.acp("stop")
        elapsed = time.monotonic() - started
        self.assertTrue(stopped.get("stopped"), stopped)
        self.assertLess(elapsed, 2.5, "stop was held by webhook delivery")
        self.session = None
        first = wait_for(
            lambda: next((r for r in self.receipts()
                          if r.get("state") == "stopped"
                          and r.get("result") == "failed"), None),
            6, "first failed attempt receipt")
        self.assertEqual(first["attempt"], 1)
        self.assertIs(first["final"], False)
        self.assertEqual(first["error"], "connection")
        # A response between the old 3 s timeout and the 12 s timeout is one
        # delivery and no retry. Stop still returns immediately.
        self.endpoint = Endpoint(sleep_seconds=4.0)
        self.write_config({self.project: {
            "url": self.endpoint.url, "sender_key": None,
            "sender_key_attachment": {"style": "url"},
            "enabled": True, "owner_agent": "agent-A",
            "updated_at": "2026-01-01T00:00:00Z"}})
        self.start_host("slow")
        started = time.monotonic()
        code, stopped = self.acp("stop")
        elapsed = time.monotonic() - started
        self.assertTrue(stopped.get("stopped"), stopped)
        self.assertLess(elapsed, 2.5, "stop was held by webhook delivery")
        self.session = None
        delivered = wait_for(
            lambda: next((r for r in self.receipts()
                          if r.get("state") == "stopped"
                          and r.get("result") == "delivered"), None),
            15, "slow endpoint delivered")
        self.assertEqual(delivered["attempt"], 1)
        self.assertIs(delivered["final"], True)
        self.assertIsNone(delivered["error"])
        posts = [p for p in self.endpoint.posts
                 if (p["body"] or {}).get("state") == "stopped"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["body"]["reason"], "exact_stop")

    def test_no_secret_leaks_into_records_or_output(self) -> None:
        self.endpoint = Endpoint()
        url = f"{self.endpoint.url}?mark={SENTINEL_URL_MARK}"
        code, out = self.configure(url, key=None, attachment=("--key-in-url",))
        self.assertEqual(code, 0, out)
        self.start_host("leak")
        code, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        wait_for(lambda: any(r.get("state") == "stopped" for r in self.receipts()),
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
        self.assertEqual(blocked["state_detail"], "permission_required")
        blocked_post = wait_for(
            lambda: next((p for p in self.endpoint.posts
                          if (p["body"] or {}).get("state") == "blocked"), None),
            5, "blocked POST")
        self.assertEqual(blocked_post["body"]["reason"], "permission_required")
        # The completing turn has no live seat, so it wakes all-idle. Exact
        # stop still wakes on its own.
        _, obs = self.acp("observe", scenario="permission_gate")
        pending = obs.get("pending_permissions") or []
        self.assertTrue(pending, obs)
        _, permit = self.acp("permit", "--request-id",
                             str(pending[0]["request_id"]),
                             "--option", pending[0]["options"][0]["id"],
                             scenario="permission_gate")
        wait_for(lambda: self.acp("status", scenario="permission_gate")[1].get(
            "turn_active") is False, 15, "turn ended after permit")
        idle = wait_for(
            lambda: next((p for p in self.endpoint.posts
                          if (p["body"] or {}).get("reason") == "all-idle"), None),
            10, "all-idle POST")
        self.assertEqual(idle["body"]["state_detail"], "end_turn")
        # stop: the inline spawn hands the payload off before the reply
        code, stopped = self.acp("stop", scenario="permission_gate")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.session = None  # already stopped
        stopped_receipt = wait_for(
            lambda: next((r for r in self.receipts()
                          if r.get("state") == "stopped"), None),
            15, "stopped receipt")
        self.assertEqual(stopped_receipt["state_detail"], "exact_stop")
        states = {(p["body"] or {}).get("state") for p in self.endpoint.posts}
        self.assertIn("blocked", states)
        self.assertIn("stopped", states)
        details = {(p["body"] or {}).get("state"): (p["body"] or {}).get("state_detail")
                   for p in self.endpoint.posts}
        self.assertEqual(details["blocked"], "permission_required")
        self.assertEqual(details["stopped"], "exact_stop")

    def test_sigkilled_host_holder_recovered_on_next_start(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("killstart")
        code, sent = self.send("--wait")
        self.assertEqual(sent.get("outcome"), "turn_completed", sent)
        wait_for(lambda: any((p["body"] or {}).get("reason") == "all-idle"
                             for p in self.endpoint.posts),
                 10, "all-idle before kill")
        dead = self.sigkill_session()
        dead_id = dead["holder_instance_id"]
        # the next start replaces the dead record: one holder_lost wake
        code, receipt = self.acp("start")
        self.assertEqual(receipt.get("session_role"), "host", receipt)
        wake = receipt.get("delegator_death_wake")
        self.assertIsNotNone(wake, receipt)
        self.assertTrue(wake["sent"], wake)
        self.assertEqual(wake["holder_instance_id"], dead_id)
        post = wait_for(
            lambda: (self.posts_with_detail("holder_lost") or [None])[-1],
            15, "holder_lost POST")
        body = post["body"]
        self.assertEqual(body["state"], "error")
        self.assertEqual(body["reason"], "holder_lost")
        self.assertEqual(body["holder_instance_id"], dead_id)
        self.assertEqual(set(body), PAYLOAD_KEYS)
        self.assertIsInstance(body["event_seq"], int)
        # a clean stop sends the new holder's own "stopped"; a later start
        # recovers nothing further for the dead id (exactly once)
        code, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        wait_for(lambda: any((p["body"] or {}).get("state") == "stopped"
                             for p in self.endpoint.posts),
                 15, "stopped POST")
        code, receipt = self.acp("start")
        self.assertNotIn("delegator_death_wake", receipt)
        self.assertEqual(len(self.posts_with_detail("holder_lost")), 1)

    def test_sigkilled_host_holder_recovered_on_dead_stop(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("killstop")
        dead = self.sigkill_session()
        dead_id = dead["holder_instance_id"]
        # dead-holder stop: force_kill_from_record fires the recovery before
        # the record is rewritten to stopped
        code, receipt = self.acp("stop")
        self.assertTrue(receipt.get("stopped"), receipt)
        wake = receipt.get("delegator_death_wake")
        self.assertIsNotNone(wake, receipt)
        self.assertTrue(wake["sent"], wake)
        wait_for(lambda: self.posts_with_detail("holder_lost"),
                 15, "holder_lost POST")
        # a second stop sees the stopped record — no second wake, no key
        code, receipt = self.acp("stop", check=False)
        self.assertNotIn("delegator_death_wake", receipt)
        # and a later start recovers nothing either
        code, receipt = self.acp("start")
        self.assertNotIn("delegator_death_wake", receipt)
        time.sleep(0.5)
        lost = self.posts_with_detail("holder_lost")
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0]["body"]["reason"], "holder_lost")
        self.assertTrue(all((p["body"] or {}).get("holder_instance_id") == dead_id
                            for p in lost))

    def test_non_host_or_clean_stop_not_recovered(self) -> None:
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        # a cleanly stopped Host holder signalled itself — no holder_lost
        self.start_host("cleanstop")
        code, stopped = self.acp("stop")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.assertNotIn("delegator_death_wake", stopped)
        # a non-Host (worker-named) dead holder gets no recovery wake either
        self.session = "grok-i299-worker-dead"
        code, receipt = self.acp("start", check=False)
        self.assertEqual(receipt.get("session_role"), "elite", receipt)
        self.sigkill_session()
        code, receipt = self.acp("stop", check=False)
        self.assertNotIn("delegator_death_wake", receipt)
        time.sleep(0.5)
        self.assertFalse(self.posts_with_detail("holder_lost"))

    def test_stop_reason_detail_carried(self) -> None:
        # No seat is live. The first Delegator send is the one all-idle
        # transition and carries the agent's stop reason as state_detail.
        # Later sends in that idle episode do not wake, whatever the stop
        # reason was (Issue #307). Exact stop still wakes on its own.
        self.endpoint = Endpoint()
        code, out = self.configure(self.endpoint.url)
        self.assertEqual(code, 0, out)
        self.start_host("reason", scenario="stop_reason")
        self.acp("send", "--text", "end_turn", "--wait", scenario="stop_reason")
        post = wait_for(
            lambda: next((p for p in self.endpoint.posts
                          if (p["body"] or {}).get("reason") == "all-idle"), None),
            10, "all-idle POST")
        self.assertEqual(post["body"]["state"], "end_turn")
        self.assertEqual(post["body"]["state_detail"], "end_turn")
        for text in ("max_tokens", "refusal", "cancelled", "not a token"):
            self.acp("send", "--text", text, "--wait", scenario="stop_reason")
        time.sleep(0.5)
        self.assertEqual(
            [p["body"]["reason"] for p in self.endpoint.posts], ["all-idle"])
        code, stopped = self.acp("stop", scenario="stop_reason")
        self.assertTrue(stopped.get("stopped"), stopped)
        self.session = None
        post = wait_for(
            lambda: next((p for p in self.endpoint.posts
                          if (p["body"] or {}).get("reason") == "exact_stop"), None),
            10, "exact_stop POST")
        self.assertEqual(post["body"]["state_detail"], "exact_stop")


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
