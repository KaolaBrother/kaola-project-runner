#!/usr/bin/env python3
"""Issue #92: a ``permission_required`` wake survives a temporarily absent Host.

Contract companion to test-issue-76-permission-wake.py — same offline harness:
real holder processes, the real Runner CLI, hermetic fakes. #76 proved the wake
exists; this file proves it is not silently lost when the bound ZCode Host holder
is not listening at the moment the worker raises it.

The lost-wake shape: the worker turn stays active while approval is pending, so
no turn-end ``idle`` will ever come; the single #76 carrier send records
``host-unreachable`` in the worker's own log and nothing else happens. A Host
that later restarts is told nothing.

What this file pins:

* the undelivered ``permission_required`` is RETAINED by the worker holder and
  re-attempted from the holder's existing watchdog tick — there is no finite
  retry window, so a Host absent far longer than any single attempt still gets
  the wake when it comes back;
* the recovered event reuses the ORIGINAL ``event_cursor``, so its deterministic
  ``event_id`` is the same one the Host would have seen: a repeat is answered by
  the existing Issue #90 dedup, never a second Host prompt or a second approval;
* a request that was settled, or a worker whose agent exited, before the Host
  returns is dropped as stale and never wakes the Host;
* after the recovered wake the Host permits within its own authorization and the
  ordinary turn-end ``idle`` still follows;
* a Host that is busy when the wake recovers stages it and flushes at its next
  completed turn boundary;
* ordinary ``idle``/``terminated`` carrier sends stay one-shot, and an unbound
  worker still sends nothing.

No real ZCode install, no login, no network, no auto-approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import threading
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_CLI = ROOT / "scripts" / "kaola-acp.py"
FAKE = ROOT / "tests" / "contract" / "fake-zcode-app-server.py"
PYTHON = sys.executable

DESKTOP_CONFIG_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-coding-plan-cache.json"
FIXTURE_SECRET = json.loads(DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"))["provider"][
    "builtin:bigmodel-coding-plan"]["options"]["apiKey"]

HEARTBEAT_HOST_ENV = "KAOLA_ACP_HEARTBEAT_HOST"
PROMPT_FILE_RELPATH = (".kaola", "heartbeat-prompt.json")

# What the fake ZCode `permission` scenario puts INSIDE the request: the raw
# tool input and the option label. Neither may ever leave the worker's own
# receipts, recovered wake included.
LEAK_COMMAND = "ls -la"
LEAK_OPTION = "Allow once"

ALLOWED_EVENT_KEYS = {"schema", "event_id", "kind", "platform", "session", "repo",
                      "reason", "event_cursor", "request_id", "staged_at"}

# The holder's existing watchdog tick is the retry trigger; a recovery window of
# a few ticks keeps the test honest without inventing a faster private clock.
RECOVERY_TIMEOUT = 75.0

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def wait_until(predicate, timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    raise AssertionError(f"timeout: {label}")


def holder_socket(record_dir: Path) -> Path:
    """The holder's deterministic socket path (kaola-acp.sock_path_for_directory)."""
    digest = hashlib.sha256(str(record_dir).encode("utf-8")).hexdigest()[:24]
    return Path(tempfile.gettempdir()) / f"kaola-{os.getuid()}-acp" / f"{digest}.sock"


def holder_op(sock: Path, op: str, params: dict, timeout: float = 15.0) -> dict:
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect(str(sock))
        payload = json.dumps({"op": op, "request_id": f"t-{uuid.uuid4().hex[:8]}",
                              "params": params}).encode("utf-8") + b"\n"
        connection.sendall(payload)
        buffer = bytearray()
        while b"\n" not in buffer:
            data = connection.recv(65536)
            if not data:
                break
            buffer.extend(data)
        line = buffer.partition(b"\n")[0]
        return json.loads(line.decode("utf-8")) if line.strip() else {}
    finally:
        connection.close()


def read_events(record_dir: Path) -> list[dict]:
    path = record_dir / "events.jsonl"
    if not path.is_file():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entries.append(json.loads(line))
        except ValueError:
            pass
    return entries


def events_of_kind(record_dir: Path, kind: str) -> list[dict]:
    return [entry for entry in read_events(record_dir) if entry.get("kind") == kind]


def rpc_sends(rpc_path: Path) -> list[str]:
    """Every prompt the fake app-server received, as literal content text."""
    if not rpc_path.is_file():
        return []
    sends = []
    for line in rpc_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("msg") or {}
        if entry.get("direction") == "in" and message.get("method") == "session/send":
            sends.append(str((message.get("params") or {}).get("content") or ""))
    return sends


def carrier_entries(record_dir: Path, event_kind: str | None = None) -> list[dict]:
    entries = [entry for entry in read_events(record_dir)
               if entry.get("kind") == "heartbeat_carrier_sent"]
    if event_kind is not None:
        entries = [entry for entry in entries if entry.get("event_kind") == event_kind]
    return entries


def worker_event_entries(record_dir: Path) -> list[dict]:
    return [entry["event"] for entry in events_of_kind(record_dir, "worker_event")]


def failed_carrier(record_dir: Path, event_kind: str) -> list[dict]:
    return [entry for entry in carrier_entries(record_dir, event_kind)
            if (entry.get("receipt") or {}).get("error")]


class FakePeer:
    """Something bound at the absent Host's own socket path.

    The worker resolves its carrier target once, at start, from the Host's
    deterministic record directory - so binding here is how a test decides what
    a carrier send actually gets back: a reply that is not a receipt, a refusal
    the Host itself would record, or a forwarded round trip to a real Host
    holder whose first reply is lost on the way home.

    ``responder(index, request_bytes)`` returns the bytes to answer with, or
    None to hang up without answering.
    """

    def __init__(self, path: Path, responder):
        self.path = Path(path)
        self.responder = responder
        self.requests: list[bytes] = []
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.server: socket.socket | None = None

    def __enter__(self) -> "FakePeer":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() or self.path.is_symlink():
            self.path.unlink()
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.path))
        os.chmod(self.path, 0o600)
        self.server.listen(8)
        threading.Thread(target=self._serve, daemon=True).start()
        return self

    def _serve(self) -> None:
        while not self.stop.is_set():
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            try:
                buffer = bytearray()
                while b"\n" not in buffer:
                    data = connection.recv(65536)
                    if not data:
                        break
                    buffer.extend(data)
                request = bytes(buffer.partition(b"\n")[0])
                with self.lock:
                    index = len(self.requests)
                    self.requests.append(request)
                reply = self.responder(index, request)
                if reply is not None:
                    connection.sendall(reply)
            except OSError:
                pass
            finally:
                try:
                    connection.close()
                except OSError:
                    pass

    def count(self) -> int:
        with self.lock:
            return len(self.requests)

    def __exit__(self, *exc: object) -> None:
        self.stop.set()
        if self.server is not None:
            try:
                self.server.close()
            except OSError:
                pass
        try:
            self.path.unlink()
        except OSError:
            pass


class Sandbox:
    """Isolated Runner environment for a ZCode Host + Worker chain."""

    def __init__(self, name: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-perm-recover-{name}-"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        for path in (self.home, self.repo, self.record_root):
            path.mkdir(parents=True)
        (self.home / ".zcode" / "v2").mkdir(parents=True)
        (self.home / ".zcode" / "cli").mkdir(parents=True)
        (self.home / ".zcode" / "v2" / "config.json").write_text(
            DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "credentials.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "cli" / "config.json").write_text('{"hooks":{}}\n', encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.node = Path(PYTHON).resolve()
        self.entries: dict[tuple[str, str], Path] = {}
        self.records: dict[str, Path] = {}
        self.rpcs: dict[str, Path] = {}
        self.sessions: list[tuple[str, str]] = []

    def entry_for(self, scenario: str, session: str) -> Path:
        key = (scenario, session)
        if key in self.entries:
            return self.entries[key]
        record = self.dir / f"fake-{session}.json"
        rpc = self.dir / f"rpc-{session}.jsonl"
        entry = self.dir / f"zcode-entry-{scenario}-{session}.py"
        entry.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(record)!r}\n"
            f"os.environ['FAKE_ZCODE_RPC_LOG'] = {str(rpc)!r}\n"
            f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        entry.chmod(entry.stat().st_mode | 0o755)
        self.entries[key] = entry
        self.records[session] = record
        self.rpcs[session] = rpc
        return entry

    def env(self, **overrides: str | None) -> dict[str, str]:
        base = {
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "HOME": str(self.home),
            "LANG": os.environ.get("LANG", "C"),
            "TMPDIR": tempfile.gettempdir(),
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "KAOLA_ZCODE_NODE": str(self.node),
            "PYTHONUNBUFFERED": "1",
        }
        for key, value in overrides.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        return base

    def session(self) -> str:
        return f"zcode-pr-{uuid.uuid4().hex[:8]}"

    def record_dir(self, session: str, platform: str = "zcode") -> Path:
        real_repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(real_repo.encode("utf-8")).hexdigest()[:16]
        return self.record_root / platform / session / digest

    def invoke(self, command: str, *args: str, session: str | None = None,
               scenario: str | None = None, platform: str = "zcode",
               timeout: float = 120,
               **env_overrides: str | None) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        argv = [PYTHON, str(CHECKOUT_CLI), platform, command, "--repo", str(self.repo)]
        if session:
            argv += ["--session", session]
            if command == "start":
                self.sessions.append((platform, session))
        if scenario is not None and session is not None:
            env_overrides.setdefault(
                "KAOLA_ZCODE_ENTRY", str(self.entry_for(scenario, session)))
        argv += list(args)
        result = subprocess.run(
            argv, capture_output=True, text=True,
            env=self.env(**env_overrides), timeout=timeout,
        )
        payload = None
        text = (result.stdout or "").strip()
        if text:
            try:
                payload = json.loads(text.splitlines()[-1])
            except ValueError:
                payload = None
        return result, payload

    def cli(self, command: str, *args: str, session: str | None = None,
            scenario: str | None = None, platform: str = "zcode", timeout: float = 120,
            **env_overrides: str | None) -> dict:
        result, payload = self.invoke(
            command, *args, session=session, scenario=scenario, platform=platform,
            timeout=timeout, **env_overrides,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"{command} exit {result.returncode}: {(result.stderr or '')[-800:]}")
        if not isinstance(payload, dict):
            raise AssertionError(
                f"{command} printed no JSON receipt: {(result.stdout or '')[-400:]} "
                f"{(result.stderr or '')[-400:]}")
        return payload

    def start(self, session_name: str, scenario: str, *,
              platform: str = "zcode", heartbeat_host: dict | None = None,
              extra_env: dict[str, str] | None = None) -> dict:
        env_overrides: dict[str, str | None] = dict(extra_env or {})
        if heartbeat_host is not None:
            env_overrides[HEARTBEAT_HOST_ENV] = json.dumps(heartbeat_host)
        receipt = self.cli("start", "--mode", "yolo", session=session_name,
                           scenario=scenario, platform=platform, **env_overrides)
        check(receipt.get("error") is None and receipt.get("state") == "ready",
              f"{session_name} start reaches ready ({receipt.get('error')})")
        return receipt

    def host_binding(self, host: str) -> dict:
        return {"platform": "zcode", "session": host, "repo": str(self.repo)}

    def write_prompt_file(self, body: str) -> None:
        path = self.repo.joinpath(*PROMPT_FILE_RELPATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema": "kaola-heartbeat-prompt/1",
            "body": body,
            "fingerprint": "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "updated_at": int(time.time() * 1000),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake(self, path: Path) -> dict:
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return {}

    def cleanup(self) -> None:
        for platform, session in list(dict.fromkeys(self.sessions)):
            try:
                self.invoke("stop", "--force", session=session, platform=platform,
                            timeout=30)
            except Exception:
                pass
        for record in list(self.records.values()):
            fake_pid = self.fake(record).get("pid")
            if pid_alive(fake_pid):
                try:
                    os.kill(int(fake_pid), signal.SIGKILL)
                except (OSError, TypeError):
                    pass
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)


def arm_pending_wake_with_absent_host(sandbox: Sandbox, host: str, worker: str,
                                      host_scenario: str = "basic") -> dict:
    """Bring the chain to the exact failure state the issue measured.

    Host up, worker bound to it, host force-stopped, then the worker raises
    ``session/request_permission``: the turn stays active, no idle exists, and
    the one carrier send fails. Returns the worker's pending request entry.
    """
    sandbox.start(host, host_scenario)
    sandbox.write_prompt_file("HEARTBEAT V1: recovered permission wake body.")
    sandbox.start(worker, "permission", heartbeat_host=sandbox.host_binding(host))

    stop = sandbox.cli("stop", "--force", session=host)
    check(stop.get("residual_pids") == [], "the host stops cleanly before the request")

    send = sandbox.cli("send", "--no-wait", "--text", "do work", session=worker)
    check(send.get("outcome") == "in_progress",
          f"worker prompt admitted with the host absent ({send.get('outcome')})")
    wait_until(lambda: (sandbox.cli("status", session=worker).get("pending_permissions")
                        or []), 20, "worker is waiting on a permission")
    status = sandbox.cli("status", session=worker)
    check(status.get("turn_active") is True,
          "worker turn is still active while pending — no turn end will come")
    check(status.get("activity_hint") == "waiting",
          f"worker reports waiting ({status.get('activity_hint')})")
    worker_dir = sandbox.record_dir(worker)
    wait_until(lambda: failed_carrier(worker_dir, "permission_required"), 20,
               "the single carrier send records the absent host")
    failure = failed_carrier(worker_dir, "permission_required")[0]
    code = ((failure.get("receipt") or {}).get("error") or {}).get("code")
    check(code in ("host-unreachable", "host-closed"),
          f"the carrier receipt is an honest absent-host error ({code})")
    check(len(carrier_entries(worker_dir, "idle")) == 0,
          "no idle was invented to carry the wake")
    return (status.get("pending_permissions") or [])[0]


def test_absent_host_recovers_the_wake_on_restart() -> None:
    """The measured loss, then the recovery: a Host absent for longer than any
    single send attempt still receives exactly one actionable wake."""
    sandbox = Sandbox("restart")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        pending = arm_pending_wake_with_absent_host(sandbox, host, worker)
        request_id = pending.get("request_id")
        worker_dir = sandbox.record_dir(worker)
        host_dir = sandbox.record_dir(host)

        # The wake is RETAINED, not lost: the worker says so in its own log and
        # in its live state, and it keeps saying so while the host stays away.
        wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_undelivered"), 20,
                   "the worker records the undelivered permission wake")
        undelivered = events_of_kind(worker_dir, "heartbeat_carrier_undelivered")
        check(len(undelivered) == 1
              and undelivered[0].get("event_kind") == "permission_required"
              and str(undelivered[0].get("request_id")) == str(request_id),
              f"the retained wake names the pending request ({undelivered})")
        held = sandbox.cli("status", session=worker).get("undelivered_worker_events")
        check(isinstance(held, list) and len(held) == 1
              and held[0].get("kind") == "permission_required"
              and str(held[0].get("request_id")) == str(request_id),
              f"live status reports the wake still owed to the host ({held})")
        blob = json.dumps(held, sort_keys=True)
        check(LEAK_COMMAND not in blob and LEAK_OPTION not in blob
              and FIXTURE_SECRET not in blob,
              "the retained wake holds no request detail or credential")

        # The absence outlasts several attempts. Nothing silently gives up, and
        # nothing is delivered anywhere while the host is gone.
        time.sleep(35)
        still = sandbox.cli("status", session=worker).get("undelivered_worker_events") or []
        check(len(still) == 1 and still[0].get("attempts", 0) >= 2,
              f"the wake is still owed after repeated attempts ({still})")
        attempts_while_absent = still[0]["attempts"]
        check(sandbox.cli("status", session=worker).get("turn_active") is True,
              "the worker turn is still blocked on approval")
        check(not worker_event_entries(host_dir),
              "nothing was staged anywhere while the host was absent")

        # The SAME authorized host comes back. No operator observes the worker.
        sandbox.start(host, "basic")
        sends_before = len(rpc_sends(sandbox.rpcs[host]))
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"),
                   RECOVERY_TIMEOUT,
                   "the restarted host receives the recovered permission wake")
        staged = worker_event_entries(host_dir)
        check(len(staged) == 1, f"exactly one worker event staged ({len(staged)})")
        event = staged[0]
        check(event["kind"] == "permission_required" and event["session"] == worker
              and event["platform"] == "zcode",
              f"the recovered event is the permission wake ({event})")
        check(str(event.get("request_id")) == str(request_id),
              f"the recovered event locates the same request ({event.get('request_id')})")
        check(set(event) <= ALLOWED_EVENT_KEYS,
              f"the recovered event carries only locating metadata ({sorted(event)})")
        check(event["event_cursor"] == undelivered[0].get("event_cursor"),
              "the recovery reuses the ORIGINAL event cursor, so the event id is stable")

        recovered = events_of_kind(worker_dir, "heartbeat_carrier_recovered")
        check(len(recovered) == 1
              and str(recovered[0].get("request_id")) == str(request_id)
              and recovered[0].get("attempts", 0) > attempts_while_absent,
              f"the worker records the recovery and what it took ({recovered})")
        check(not (sandbox.cli("status", session=worker).get("undelivered_worker_events")),
              "nothing is owed to the host once the wake lands")

        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == sends_before + 1,
              f"the recovered wake delivered as exactly one host prompt ({len(sends)})")
        content = sends[-1]
        check("kaola-host-notify/1" in content and event["event_id"] in content,
              "the delivered prompt carries the recovered permission event line")
        check(str(request_id) in content, "the delivered prompt carries the request locator")
        check(LEAK_COMMAND not in content and LEAK_OPTION not in content
              and FIXTURE_SECRET not in content,
              "no request detail, option text, or credential reaches the host prompt")

        # The wake approved nothing: the worker is still blocked, and the host
        # decides inside its own authorization. permit then yields normal idle.
        check(sandbox.cli("status", session=worker).get("turn_active") is True,
              "the recovered wake approved nothing; the worker still waits")
        permit = sandbox.cli("permit", "--option", "allow", session=worker)
        check(permit.get("permitted") is not None,
              f"the host permits after the recovered wake ({permit.get('error')})")
        wait_until(lambda: len(worker_event_entries(host_dir)) == 2, 30,
                   "the ordinary turn-end idle still arrives after the recovered wake")
        second = worker_event_entries(host_dir)[1]
        check(second["kind"] == "idle" and second["session"] == worker,
              f"the second event is the real turn-end idle ({second})")
        check(second["event_cursor"] > event["event_cursor"],
              "the recovered wake precedes the turn-end idle in worker event order")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_recovered_wake_is_not_prompted_twice() -> None:
    """A repeat of the same request is answered by the existing dedup: the
    stable event id means a second offer is a duplicate, not a second prompt
    and not a second approval."""
    sandbox = Sandbox("dedup")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        pending = arm_pending_wake_with_absent_host(sandbox, host, worker)
        request_id = pending.get("request_id")
        host_dir = sandbox.record_dir(host)

        sandbox.start(host, "basic")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"),
                   RECOVERY_TIMEOUT, "the restarted host receives the recovered wake")
        event = worker_event_entries(host_dir)[0]
        sends_after_recovery = len(rpc_sends(sandbox.rpcs[host]))

        # Re-offer the very same carrier payload the worker would retry with.
        sock = holder_socket(host_dir)
        params = {"schema": "kaola-worker-event/1", "kind": "permission_required",
                  "platform": "zcode", "session": worker,
                  "repo": os.path.realpath(str(sandbox.repo)),
                  "reason": event["reason"], "event_cursor": event["event_cursor"],
                  "request_id": event.get("request_id")}
        receipt = holder_op(sock, "worker_event", params)
        check(receipt.get("duplicate") is True and receipt.get("staged") is not True,
              f"the repeated wake is a deduped duplicate ({receipt})")
        check(receipt.get("event_id") == event["event_id"],
              "the repeat resolves to the same deterministic event id")
        time.sleep(3)
        check(len(rpc_sends(sandbox.rpcs[host])) == sends_after_recovery,
              "the repeat produced no second host prompt")
        check(len(worker_event_entries(host_dir)) == 1,
              "the repeat staged no second event")
        check(len(sandbox.cli("status", session=worker).get("pending_permissions") or []) == 1,
              "the repeat approved nothing; one request is still pending")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_settled_request_is_stale_and_never_wakes_the_host() -> None:
    """Resolved before recovery: the worker drops the wake, and a host that
    still acts on the locator is told the request is gone."""
    sandbox = Sandbox("settled")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        pending = arm_pending_wake_with_absent_host(sandbox, host, worker)
        request_id = pending.get("request_id")
        worker_dir = sandbox.record_dir(worker)
        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_undelivered"), 20,
                   "the worker retains the undelivered wake")

        # Settled locally while the host is still away.
        permit = sandbox.cli("permit", "--option", "allow", session=worker)
        check(permit.get("permitted") is not None,
              f"the pending request settles while the host is away ({permit.get('error')})")

        sandbox.start(host, "basic")
        wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_dropped"),
                   RECOVERY_TIMEOUT, "the stale wake is dropped instead of delivered")
        dropped = events_of_kind(worker_dir, "heartbeat_carrier_dropped")
        check(len(dropped) == 1 and dropped[0].get("reason") == "permission-settled"
              and str(dropped[0].get("request_id")) == str(request_id),
              f"the drop names the settled request ({dropped})")
        time.sleep(5)
        check(not [e for e in worker_event_entries(host_dir)
                   if e["kind"] == "permission_required"],
              "no permission wake ever reached the restarted host")
        check(not (sandbox.cli("status", session=worker).get("undelivered_worker_events")),
              "nothing is still owed to the host")

        # A host acting on the stale locator is refused, never auto-approved.
        again = sandbox.invoke("permit", "--request-id", str(request_id),
                               "--option", "allow", session=worker)[1] or {}
        code = (again.get("error") or {}).get("code")
        check(code in ("no-pending-permission", "unknown-request"),
              f"the stale locator is refused, not re-approved ({again})")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_exited_worker_wake_is_stale() -> None:
    """The worker's agent dies before the host returns: the wake is moot and
    must not wake the host with a request nobody can answer."""
    sandbox = Sandbox("exited")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        arm_pending_wake_with_absent_host(sandbox, host, worker)
        worker_dir = sandbox.record_dir(worker)
        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_undelivered"), 20,
                   "the worker retains the undelivered wake")

        agent_pid = sandbox.cli("status", session=worker).get("agent_pid")
        check(pid_alive(agent_pid), f"the worker agent is alive before the kill ({agent_pid})")
        os.kill(int(agent_pid), signal.SIGKILL)
        wait_until(lambda: sandbox.cli("status", session=worker).get("agent_alive") is False,
                   30, "the worker agent is gone")

        sandbox.start(host, "basic")
        wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_dropped"),
                   RECOVERY_TIMEOUT, "the wake of an exited worker is dropped")
        dropped = events_of_kind(worker_dir, "heartbeat_carrier_dropped")
        check(len(dropped) == 1 and dropped[0].get("reason") == "agent-exited",
              f"the drop names the exited agent ({dropped})")
        time.sleep(5)
        check(not [e for e in worker_event_entries(host_dir)
                   if e["kind"] == "permission_required"],
              "no permission wake reached the restarted host")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_busy_host_stages_the_recovered_wake() -> None:
    """The host is back but mid-turn: the recovered wake stages and flushes at
    the next completed turn boundary, exactly like a fresh one."""
    sandbox = Sandbox("busy")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        arm_pending_wake_with_absent_host(sandbox, host, worker, host_scenario="permission")
        host_dir = sandbox.record_dir(host)

        # Wait for a retry to land first: that pins the watchdog phase, so the
        # host has a whole tick to become busy in rather than whatever was left
        # of one. Without this the wake can deliver into the ~0.5s start window.
        wait_until(lambda: (sandbox.cli("status", session=worker)
                            .get("undelivered_worker_events") or [{}])[0]
                   .get("attempts", 0) >= 2, 40, "a retry attempt has just been made")
        sandbox.start(host, "permission")
        sandbox.cli("send", "--no-wait", "--text", "host busy turn", session=host)
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions")
                            or []), 20, "the restarted host is busy on its own turn")
        sends_before = len(rpc_sends(sandbox.rpcs[host]))

        wait_until(lambda: events_of_kind(host_dir, "worker_event"), RECOVERY_TIMEOUT,
                   "the recovered wake stages on the busy host")
        staged = worker_event_entries(host_dir)
        check(len(staged) == 1 and staged[0]["kind"] == "permission_required",
              f"the staged event is the recovered permission wake ({staged})")
        check(not events_of_kind(host_dir, "worker_event_delivered"),
              "no delivery while the host turn is active")
        check(len(rpc_sends(sandbox.rpcs[host])) == sends_before,
              "no prompt reached the busy host besides its own turn")

        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 30,
                   "the staged wake flushes at the completed turn boundary")
        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == sends_before + 1,
              f"the recovered wake flushed as the next host prompt ({len(sends)})")
        check(staged[0]["event_id"] in sends[-1] and "permission_required" in sends[-1],
              "the flushed prompt carries the recovered permission event line")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_idle_and_unbound_paths_are_unchanged() -> None:
    """Scope guard: an ordinary turn-end ``idle`` whose host is away stays a
    one-shot send, and an unbound worker still sends nothing at all."""
    sandbox = Sandbox("scope")
    try:
        host = sandbox.session()
        bound = sandbox.session()
        unbound = sandbox.session()
        sandbox.start(host, "basic")
        sandbox.write_prompt_file("HEARTBEAT V1: scope guard body.")
        sandbox.start(bound, "basic", heartbeat_host=sandbox.host_binding(host))
        sandbox.cli("stop", "--force", session=host)

        result = sandbox.cli("send", "--text", "plain work", session=bound)
        check(result.get("outcome") == "turn_completed",
              f"the bound worker's ordinary turn completes ({result.get('outcome')})")
        bound_dir = sandbox.record_dir(bound)
        wait_until(lambda: failed_carrier(bound_dir, "idle"), 20,
                   "the ordinary idle records the absent host")
        check(not events_of_kind(bound_dir, "heartbeat_carrier_undelivered"),
              "an ordinary idle is not retained for recovery")
        check(not (sandbox.cli("status", session=bound).get("undelivered_worker_events")),
              "an ordinary idle owes the host nothing")

        sandbox.start(unbound, "permission")
        sandbox.cli("send", "--no-wait", "--text", "do work", session=unbound)
        wait_until(lambda: (sandbox.cli("status", session=unbound).get("pending_permissions")
                            or []), 20, "the unbound worker waits on its permission")
        unbound_dir = sandbox.record_dir(unbound)
        check(not carrier_entries(unbound_dir),
              "an unbound worker sends nothing anywhere")
        check(not events_of_kind(unbound_dir, "heartbeat_carrier_undelivered"),
              "an unbound worker retains nothing either")
        check(not (sandbox.cli("status", session=unbound).get("undelivered_worker_events")),
              "an unbound worker owes nothing")

        for session in (bound, unbound):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_a_reply_that_is_not_a_receipt_never_wedges_the_worker() -> None:
    """Whatever is bound at the host socket is not trusted to answer in the
    receipt shape. A reply that is not one must become an honest carrier
    failure — it must not raise on the agent reader thread that sent it, which
    would leave the turn active forever with no way back."""
    sandbox = Sandbox("badreply")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        sandbox.write_prompt_file("HEARTBEAT V1: malformed carrier reply body.")
        sandbox.start(worker, "permission", heartbeat_host=sandbox.host_binding(host))
        sandbox.cli("stop", "--force", session=host)
        worker_dir = sandbox.record_dir(worker)
        host_dir = sandbox.record_dir(host)

        # Two different non-receipt shapes: a JSON object whose `error` is a
        # string, and a reply that is not an object at all.
        replies = [b'{"error":"boom"}\n', b'"not-a-receipt"\n']
        with FakePeer(holder_socket(host_dir),
                      lambda index, _r: replies[min(index, 1)]) as peer:
            send = sandbox.cli("send", "--no-wait", "--text", "do work", session=worker)
            check(send.get("outcome") == "in_progress", "worker prompt admitted")
            wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_undelivered"),
                       25, "the non-receipt reply is recorded as a carrier failure")
            undelivered = events_of_kind(worker_dir, "heartbeat_carrier_undelivered")
            check(undelivered[0].get("error") == "host-reply-invalid",
                  f"the failure names the bad reply ({undelivered[0]})")
            check(peer.count() >= 1, "the worker really did reach the peer")
            # Still owed, and still retrying past the second bad shape.
            wait_until(lambda: peer.count() >= 2, 40,
                       "the wake is re-offered despite the bad reply")
            held = sandbox.cli("status", session=worker).get("undelivered_worker_events")
            check(isinstance(held, list) and len(held) == 1,
                  f"the wake is still owed after a bad reply ({held})")

        # The real host comes back and takes the wake.
        sandbox.start(host, "basic")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"),
                   RECOVERY_TIMEOUT, "the restarted host receives the recovered wake")

        # The proof the reader thread survived: the worker still answers ACP.
        # A dead reader would leave the turn active forever after the permit.
        permit = sandbox.cli("permit", "--option", "allow", session=worker)
        check(permit.get("permitted") is not None,
              f"permit settles the request ({permit.get('error')})")
        wait_until(lambda: sandbox.cli("status", session=worker).get("turn_active") is False,
                   30, "the worker turn ends — its agent reader thread is alive")
        wait_until(lambda: any(e["kind"] == "idle"
                               for e in worker_event_entries(host_dir)), 30,
                   "the ordinary turn-end idle still arrives")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_a_host_answer_settles_the_debt_even_when_it_refuses() -> None:
    """The wake is owed only while the Host never answered.

    A refusal the Host produced for itself — `worker-event-queue-full` already
    schedules its own full pending-approval pass — must END the retry. Re-offering
    it every tick would drive the Host, not recover the wake.
    """
    sandbox = Sandbox("refused")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        sandbox.write_prompt_file("HEARTBEAT V1: refused carrier body.")
        sandbox.start(worker, "permission", heartbeat_host=sandbox.host_binding(host))
        sandbox.cli("stop", "--force", session=host)
        worker_dir = sandbox.record_dir(worker)

        refusal = (b'{"error":{"code":"worker-event-queue-full","capacity":32},'
                   b'"overflow_full_check":true,"generation":3,"pending":32}\n')
        # First offer hangs up (nothing was handed over, so the wake is owed);
        # every later offer is the Host's own refusal.
        with FakePeer(holder_socket(sandbox.record_dir(host)),
                      lambda index, _r: None if index == 0 else refusal) as peer:
            sandbox.cli("send", "--no-wait", "--text", "do work", session=worker)
            wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_undelivered"),
                       25, "the hung-up first offer leaves the wake owed")
            wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_dropped"),
                       40, "the Host's own refusal settles the debt")
            dropped = events_of_kind(worker_dir, "heartbeat_carrier_dropped")
            check(len(dropped) == 1 and dropped[0].get("reason") == "host-answered",
                  f"the drop names the Host's answer ({dropped})")
            check((dropped[0].get("receipt") or {}).get("overflow_full_check") is True,
                  f"the Host's own receipt is kept as evidence ({dropped[0]})")
            check(not (sandbox.cli("status", session=worker)
                       .get("undelivered_worker_events")),
                  "nothing is still owed once the Host has answered")

            # The storm test: no further offers, however long we wait.
            settled = peer.count()
            time.sleep(35)
            check(peer.count() == settled,
                  f"an answered wake is never re-offered ({settled} -> {peer.count()})")
            check(sandbox.cli("status", session=worker).get("turn_active") is True,
                  "the worker is still blocked; the refusal approved nothing")

        stop = sandbox.cli("stop", "--force", session=worker)
        check(stop.get("residual_pids") == [], "worker stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_a_lost_receipt_retries_into_the_hosts_own_dedup() -> None:
    """The real duplicate path, driven end to end through production code.

    The Host DID stage the wake, but the receipt never got home, so the worker
    still owes it. The retry it then makes — same params, same `event_cursor` —
    must land on the Host's existing dedup: one prompt, one pending request, no
    second approval.
    """
    sandbox = Sandbox("lostreceipt")
    try:
        bound = sandbox.session()
        live = sandbox.session()
        worker = sandbox.session()
        sandbox.start(bound, "basic")
        sandbox.write_prompt_file("HEARTBEAT V1: lost receipt body.")
        sandbox.start(worker, "permission", heartbeat_host=sandbox.host_binding(bound))
        sandbox.cli("stop", "--force", session=bound)
        # A real Host holder to forward to; the worker's carrier target stays
        # the socket path it resolved at start.
        sandbox.start(live, "basic")
        live_sock = holder_socket(sandbox.record_dir(live))
        worker_dir = sandbox.record_dir(worker)
        live_dir = sandbox.record_dir(live)

        def forward(index: int, request: bytes) -> bytes | None:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                connection.settimeout(15.0)
                connection.connect(str(live_sock))
                connection.sendall(request + b"\n")
                buffer = bytearray()
                while b"\n" not in buffer:
                    data = connection.recv(65536)
                    if not data:
                        break
                    buffer.extend(data)
            finally:
                connection.close()
            # The first receipt is lost on the way home: the Host staged it,
            # the worker never learned that.
            return None if index == 0 else bytes(buffer.partition(b"\n")[0]) + b"\n"

        with FakePeer(holder_socket(sandbox.record_dir(bound)), forward) as peer:
            sandbox.cli("send", "--no-wait", "--text", "do work", session=worker)
            wait_until(lambda: events_of_kind(live_dir, "worker_event_delivered"), 30,
                       "the host staged and delivered the wake it did receive")
            wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_undelivered"),
                       25, "the worker still owes the wake, its receipt was lost")
            staged_once = worker_event_entries(live_dir)
            prompts_once = len(rpc_sends(sandbox.rpcs[live]))
            check(len(staged_once) == 1 and prompts_once == 1,
                  f"the host saw it exactly once so far ({len(staged_once)}/{prompts_once})")

            wait_until(lambda: events_of_kind(worker_dir, "heartbeat_carrier_recovered"),
                       RECOVERY_TIMEOUT, "the retry reaches the host")
            recovered = events_of_kind(worker_dir, "heartbeat_carrier_recovered")
            receipt = recovered[0].get("receipt") or {}
            check(receipt.get("duplicate") is True and receipt.get("staged") is not True,
                  f"the retry landed on the host's own dedup ({receipt})")
            check(receipt.get("event_id") == staged_once[0]["event_id"],
                  f"the retry resolved to the SAME event id ({receipt.get('event_id')})")
            check(peer.count() >= 2, f"the retry really was a second offer ({peer.count()})")

            time.sleep(3)
            check(len(worker_event_entries(live_dir)) == 1,
                  "the retry staged no second event")
            check(len(rpc_sends(sandbox.rpcs[live])) == prompts_once,
                  "the retry produced no second host prompt")
            check(len(sandbox.cli("status", session=worker)
                      .get("pending_permissions") or []) == 1,
                  "the retry approved nothing; one request is still pending")

        for session in (worker, live):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_the_retention_has_no_retry_deadline() -> None:
    """Duration cannot prove the ABSENCE of a give-up cap, and the issue is
    explicit that a finite retry which can still silently lose the wake is not
    acceptance. Pin it structurally instead: the only reasons this holder stops
    owing a permission wake are the three that mean it is no longer owed."""
    source = (ROOT / "scripts" / "kaola-acp-holder.py").read_text(encoding="utf-8")
    region = source.split("def _retain_undelivered_wake")[1].split("\n    def _record_")[0]
    # Prose explaining the absence of a deadline is not a deadline: match the
    # code, with docstrings and comments removed.
    region = re.sub(r'"""(?:.|\n)*?"""', "", region)
    region = re.sub(r"(?m)#.*$", "", region)
    reasons = sorted(set(re.findall(r'"reason": "([a-z-]+)"', region))
                     | set(re.findall(r'return "([a-z-]+)"', region)))
    check(reasons == ["agent-exited", "host-answered", "permission-settled"],
          f"a wake is dropped only when it is no longer owed ({reasons})")
    check(not re.search(r"attempts\s*[<>]=?\s*\d", region),
          "no attempt count is ever compared against a threshold")
    check(not re.search(r"\b(deadline|expire|expires|expired|give_up|max_attempts|"
                        r"retry_limit|timeout_at)\b", region),
          "the retention holds no deadline, expiry, or attempt limit")
    check("CARRIER_UNDELIVERED_CODES" in region,
          "the retry condition is which END failed, not which error code it was")


TESTS = (
    test_absent_host_recovers_the_wake_on_restart,
    test_recovered_wake_is_not_prompted_twice,
    test_settled_request_is_stale_and_never_wakes_the_host,
    test_exited_worker_wake_is_stale,
    test_busy_host_stages_the_recovered_wake,
    test_idle_and_unbound_paths_are_unchanged,
    test_a_reply_that_is_not_a_receipt_never_wedges_the_worker,
    test_a_host_answer_settles_the_debt_even_when_it_refuses,
    test_a_lost_receipt_retries_into_the_hosts_own_dedup,
    test_the_retention_has_no_retry_deadline,
)


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    selected = [test for test in TESTS if not only or only in test.__name__]
    if not selected:
        print(f"no test matches {only!r}")
        return 2
    failures: list[str] = []
    for test in selected:
        CHECKS.clear()
        try:
            test()
        except BaseException as exc:  # noqa: BLE001 - every failure is reported
            # The checks that DID hold before the failure are the evidence of
            # what a baseline reproduces; print them before moving on. One
            # failing case must not hide the others from validate.sh.
            for label in CHECKS:
                print(f"  ok   {label}")
            print(f"FAIL {test.__name__} (after {len(CHECKS)} checks): "
                  f"{type(exc).__name__}: {exc}")
            failures.append(test.__name__)
            if isinstance(exc, KeyboardInterrupt):
                raise
            continue
        print(f"PASS {test.__name__} ({len(CHECKS)} checks)")
    if failures:
        print(f"FAIL: issue-92 permission wake recovery contract "
              f"({len(failures)}/{len(selected)} failed: {', '.join(failures)})")
        return 1
    print(f"PASS: issue-92 permission wake recovery contract "
          f"({len(selected)}/{len(TESTS)} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
