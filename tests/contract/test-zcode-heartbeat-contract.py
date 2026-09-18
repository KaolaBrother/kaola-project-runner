#!/usr/bin/env python3
"""Issue #62 Phase 2: event-driven heartbeat for a ZCode Host — contract.

Deterministic and offline (the phase-1 harness pattern): real holder
processes, the real Runner CLI, and the hermetic fake ZCode app-server. The
ZCode Host session's own holder is the event carrier:

* a worker started with ``KAOLA_ACP_HEARTBEAT_HOST`` naming the ZCode Host
  session notifies that host holder from its existing agent-exit and
  turn-end paths (worker terminated / one idle episode per ended turn);
* the host holder stages events in one bounded in-memory list, records
  stage/delivery/confirmation in its existing event log, and delivers one
  normal ACP ``session/prompt`` through the ordinary admission path (never a
  raw send) as soon as its turn is idle, flushing at the next completed turn
  boundary when busy;
* the delivered prompt carries fixed structured event metadata plus the
  current FULL heartbeat prompt body, read at delivery time from the file the
  ZCode Host agent maintains at ``<repo>/.kaola/heartbeat-prompt.json``;
* unconfirmed events are redelivered after ``start --resume``; the carrier is
  ZCode-Host-only (a non-ZCode holder rejects the op, the CLI refuses a
  non-ZCode or self target) and registers no periodic scheduler anywhere.

No real ZCode install, no login, no network, and no live model-driven
dispatch (that is the separate E2E frontier).
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
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
HEARTBEAT_EVENT_CAP = 32

# A minimal ACP agent used only to prove the non-ZCode boundary: a holder for
# another platform must reject the worker_event op outright.
FAKE_ACP_AGENT = (
    "#!/usr/bin/env python3\n"
    "import json, sys\n"
    "def send(m):\n"
    "    sys.stdout.write(json.dumps(m) + '\\n'); sys.stdout.flush()\n"
    "for raw in sys.stdin.buffer:\n"
    "    line = raw.decode('utf-8', 'replace').strip()\n"
    "    if not line:\n"
    "        continue\n"
    "    msg = json.loads(line)\n"
    "    rid, method = msg.get('id'), msg.get('method')\n"
    "    if method == 'initialize':\n"
    "        send({'jsonrpc': '2.0', 'id': rid, 'result': {\n"
    "            'protocolVersion': 1, 'agentCapabilities': {}, 'authMethods': [],\n"
    "            'agentInfo': {'name': 'fake-acp-agent'}}})\n"
    "    elif method == 'session/new':\n"
    "        send({'jsonrpc': '2.0', 'id': rid, 'result': {'sessionId': 'fake-s1'}})\n"
    "    elif method == 'session/prompt':\n"
    "        send({'jsonrpc': '2.0', 'method': 'session/update', 'params': {\n"
    "            'sessionId': 'fake-s1', 'update': {'sessionUpdate': 'agent_message_chunk',\n"
    "            'content': {'type': 'text', 'text': 'ok'}}}})\n"
    "        send({'jsonrpc': '2.0', 'id': rid, 'result': {'stopReason': 'end_turn'}})\n"
    "    elif method in ('session/close', 'session/set_config_option'):\n"
    "        send({'jsonrpc': '2.0', 'id': rid, 'result': {'configOptions': []}})\n"
    "    elif rid is not None:\n"
    "        send({'jsonrpc': '2.0', 'id': rid, 'error': {\n"
    "            'code': -32601, 'message': 'unsupported: ' + str(method)}})\n"
)

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
        time.sleep(0.05)
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


class Sandbox:
    """Isolated Runner environment for a ZCode Host + Worker chain."""

    def __init__(self, name: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-zcode-heartbeat-{name}-"))
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
        self.records: dict[tuple[str, str], Path] = {}
        self.rpcs: dict[tuple[str, str], Path] = {}
        self.sessions: list[str] = []

    def entry_for(self, scenario: str, session: str) -> Path:
        key = (scenario, session)
        if key in self.entries:
            return self.entries[key]
        # The fake record and rpc log are per SESSION (a resumed holder spawns
        # a fresh fake that appends to the same log); only the entry script
        # differs per scenario.
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
        return f"zcode-hb-{uuid.uuid4().hex[:8]}"

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
              heartbeat_host: dict | None = None) -> dict:
        env_overrides: dict[str, str | None] = {}
        if heartbeat_host is not None:
            env_overrides[HEARTBEAT_HOST_ENV] = json.dumps(heartbeat_host)
        receipt = self.cli("start", "--mode", "yolo", session=session_name,
                           scenario=scenario, **env_overrides)
        check(receipt.get("error") is None and receipt.get("state") == "ready",
              f"{session_name} start reaches ready ({receipt.get('error')})")
        return receipt

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
        for platform, session in list(self.sessions):
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


def assert_delivered_notification(sandbox: Sandbox, host: str, content: str,
                                  event_ids: list[str], body: str) -> None:
    """The delivered prompt is one literal text: fixed metadata, the event
    lines, the current full heartbeat body verbatim, and the one-pass
    instruction per PROJECT_RUNNER_HEARTBEAT_V2."""
    check("kaola-host-notify/1" in content, "notification payload carries its schema marker")
    check("<<<heartbeat-prompt" in content and "heartbeat-prompt>>>" in content,
          "notification payload delimits the heartbeat body verbatim")
    check(body in content, "notification payload carries the FULL current heartbeat body verbatim")
    check("PROJECT_RUNNER_HEARTBEAT_V2" in content,
          "notification payload demands one pass per the canonical heartbeat skeleton")
    for event_id in event_ids:
        check(event_id in content, f"notification payload carries structured event {event_id}")


def test_terminated_event_delivers_full_body_and_confirms() -> None:
    sandbox = Sandbox("terminated")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        host_start = sandbox.start(host, "basic")
        body_v1 = "HEARTBEAT V1: recover authorization, dispatch verified work, close out."
        sandbox.write_prompt_file(body_v1)
        worker_start = sandbox.start(
            worker, "basic",
            heartbeat_host={"platform": "zcode", "session": host, "repo": str(sandbox.repo)})

        fact = worker_start.get("heartbeat_host") or {}
        check(fact.get("platform") == "zcode" and fact.get("session") == host
              and fact.get("repo") == os.path.realpath(str(sandbox.repo)),
              f"armed start receipt carries the heartbeat_host fact ({fact})")
        check(fact.get("socket") == str(holder_socket(sandbox.record_dir(host))),
              f"heartbeat_host fact names the host holder socket ({fact.get('socket')})")

        # The worker agent terminates (exact stop). The stop receipt returns
        # only after the carrier finished, so the chain is deterministic.
        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "worker stop receipt is terminal")
        check(stop.get("residual_pids") == [], f"worker stop leaves no residue ({stop.get('residual_pids')})")

        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event"), 10,
                   "terminated worker event reaches the host holder")
        staged = events_of_kind(host_dir, "worker_event")[0]["event"]
        check(staged["kind"] == "terminated" and staged["session"] == worker
              and staged["platform"] == "zcode",
              f"staged event is the worker termination ({staged})")
        check(str(staged["reason"]).startswith("exit_"), f"termination carries its reason ({staged})")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "host holder delivers the notification prompt")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_confirmed"), 10,
                   "host turn completing confirms the notification")

        delivered = events_of_kind(host_dir, "worker_event_delivered")[0]
        confirmed = events_of_kind(host_dir, "worker_event_confirmed")[0]
        event_id = staged["event_id"]
        check(delivered["event_ids"] == [event_id],
              f"delivery names exactly the staged event ({delivered['event_ids']})")
        check(confirmed["event_ids"] == [event_id],
              f"confirmation names the delivered event ({confirmed['event_ids']})")
        check(delivered.get("heartbeat_maintained") is True,
              "delivery read the maintained heartbeat prompt file")

        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == 1, f"the notification is the only host prompt ({len(sends)} sends)")
        content = sends[0]
        assert_delivered_notification(sandbox, host, content, [event_id], body_v1)
        check(hashlib.sha256(content.encode("utf-8")).hexdigest()
              == str(delivered["prompt_fingerprint"]).split(":", 1)[-1],
              "delivered prompt fingerprint matches the literal text the app-server received")

        carrier = [entry for entry in read_events(sandbox.record_dir(worker))
                   if entry.get("kind") == "heartbeat_carrier_sent"]
        check(carrier and carrier[0]["receipt"].get("delivered") is True,
              f"worker holder logged the carrier receipt ({carrier[:1]})")

        blob = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                         for path in sandbox.record_root.rglob("*") if path.is_file())
        check(FIXTURE_SECRET not in blob, "plan credential absent from all Runner records")
        check(FIXTURE_SECRET not in content, "plan credential absent from the delivered payload")

        # No periodic trigger: with no further worker event, no further prompt.
        time.sleep(1.5)
        check(len(rpc_sends(sandbox.rpcs[host])) == 1,
              "no worker event means no further heartbeat prompt (no periodic carrier)")
        check(len(events_of_kind(host_dir, "worker_event_delivered")) == 1,
              "no duplicate delivery without a new worker event")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_idle_episode_reads_prompt_body_at_delivery_time() -> None:
    sandbox = Sandbox("idle")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        worker_start = sandbox.start(
            worker, "basic",
            heartbeat_host={"platform": "zcode", "session": host, "repo": str(sandbox.repo)})
        body_v1 = "HEARTBEAT V1: idle-pass body."
        sandbox.write_prompt_file(body_v1)

        # One worker turn ends with the agent alive: one idle episode.
        first = sandbox.cli("send", "--text", "run task one", session=worker)
        check(first.get("outcome") == "turn_completed", f"worker turn completed ({first.get('outcome')})")
        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "idle episode delivers into the same host session")
        idle_event = events_of_kind(host_dir, "worker_event")[0]["event"]
        check(idle_event["kind"] == "idle" and idle_event["session"] == worker,
              f"staged event is the worker idle episode ({idle_event})")
        check("stop_reason=end_turn" in idle_event["reason"],
              f"idle reason carries the turn stop reason ({idle_event['reason']})")

        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == 1, f"one idle notification delivered ({len(sends)} sends)")
        assert_delivered_notification(sandbox, host, sends[0], [idle_event["event_id"]], body_v1)
        check("hello from zcode" not in sends[0],
              "the notification never carries unrestricted raw worker output")

        # The host agent overwrites the same file; the NEXT event must use it.
        body_v2 = "HEARTBEAT V2: refreshed idle-pass body with new duties."
        sandbox.write_prompt_file(body_v2)
        second = sandbox.cli("send", "--text", "run task two", session=worker)
        check(second.get("outcome") == "turn_completed", "second worker turn completed")
        wait_until(lambda: len(events_of_kind(host_dir, "worker_event_delivered")) >= 2, 10,
                   "second idle episode delivers")
        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == 2, f"exactly one prompt per idle episode ({len(sends)} sends)")
        assert_delivered_notification(sandbox, host, sends[1],
                                      [events_of_kind(host_dir, "worker_event")[1]["event"]["event_id"]],
                                      body_v2)
        check(body_v1 not in sends[1], "the next event uses the refreshed prompt body")

        staged_all = [entry["event"] for entry in events_of_kind(host_dir, "worker_event")]
        ids = [event["event_id"] for event in staged_all]
        check(len(set(ids)) == 2, f"each idle episode is delivered once, deduped by id ({ids})")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("residual_pids") == [], f"{session} stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_busy_host_stages_then_flushes_after_turn_completed() -> None:
    sandbox = Sandbox("busy")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "permission")
        worker_start = sandbox.start(
            worker, "basic",
            heartbeat_host={"platform": "zcode", "session": host, "repo": str(sandbox.repo)})
        body = "HEARTBEAT BUSY: staged flush body."
        sandbox.write_prompt_file(body)

        # The host is mid-turn (the fake asks a permission and waits): a raw
        # prompt send would hit prompt-in-progress, so the event must stage.
        sandbox.cli("send", "--no-wait", "--text", "host busy turn", session=host)
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "host turn is busy waiting on a permission")
        check((sandbox.cli("status", session=host).get("turn_active")) is True,
              "host turn is active while the notification arrives")

        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "worker terminated while the host was busy")
        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event"), 10,
                   "terminated event stages on the busy host holder")
        carrier = [entry for entry in read_events(sandbox.record_dir(worker))
                   if entry.get("kind") == "heartbeat_carrier_sent"]
        check(carrier and carrier[0]["receipt"].get("staged") is True
              and carrier[0]["receipt"].get("delivered") is not True,
              f"carrier receipt reports staging, not delivery ({carrier[:1]})")
        check(not events_of_kind(host_dir, "worker_event_delivered"),
              "no delivery while the host turn is active")
        check(len(rpc_sends(sandbox.rpcs[host])) == 1,
              "no prompt reached the busy host app-server besides the busy turn")

        # The busy turn completes; the staged event flushes after that boundary.
        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "staged event flushes at the completed turn boundary")
        staged = events_of_kind(host_dir, "worker_event")[0]["event"]
        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == 2, f"the notification flushed as the next host prompt ({len(sends)} sends)")
        assert_delivered_notification(sandbox, host, sends[1], [staged["event_id"]], body)

        # The notification turn itself asks a permission in this scenario;
        # answering it completes the pass and confirms the event.
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "notification turn asks its permission")
        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_confirmed"), 10,
                   "completed notification turn confirms the event")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_bounded_queue_dedup_and_single_batch_flush() -> None:
    sandbox = Sandbox("queue")
    try:
        host = sandbox.session()
        sandbox.start(host, "permission")
        body = "HEARTBEAT QUEUE: batch flush body."
        sandbox.write_prompt_file(body)
        sandbox.cli("send", "--no-wait", "--text", "host busy turn", session=host)
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "host turn is busy waiting on a permission")
        host_dir = sandbox.record_dir(host)
        sock = holder_socket(host_dir)

        def fabricate(index: int) -> dict:
            return {"schema": "kaola-worker-event/1", "kind": "idle", "platform": "codex",
                    "session": f"work-{index}", "repo": os.path.realpath(str(sandbox.repo)),
                    "reason": "outcome=turn_completed stop_reason=end_turn",
                    "event_cursor": 100 + index}

        for index in range(HEARTBEAT_EVENT_CAP):
            receipt = holder_op(sock, "worker_event", fabricate(index))
            check(receipt.get("staged") is True and receipt.get("error") is None,
                  f"event {index} stages while the host is busy ({receipt})")
        overflow = holder_op(sock, "worker_event", fabricate(999))
        check((overflow.get("error") or {}).get("code") == "worker-event-queue-full",
              f"the staging list is bounded ({overflow})")
        duplicate = holder_op(sock, "worker_event", fabricate(0))
        check(duplicate.get("duplicate") is True and duplicate.get("error") is None,
              f"a repeated event id is deduped, not requeued ({duplicate})")
        invalid = holder_op(sock, "worker_event", {"kind": "bogus", "platform": "codex",
                                                   "session": "w", "repo": "/x",
                                                   "reason": "r", "event_cursor": 1})
        check((invalid.get("error") or {}).get("code") == "worker-event-invalid",
              f"an unknown event kind is rejected ({invalid})")
        check(len(events_of_kind(host_dir, "worker_event")) == HEARTBEAT_EVENT_CAP,
              "exactly the bounded set of events is staged")

        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "busy boundary flushes the staged batch")
        delivered = events_of_kind(host_dir, "worker_event_delivered")[0]
        check(len(delivered["event_ids"]) == HEARTBEAT_EVENT_CAP,
              f"one prompt flushes the whole bounded batch ({len(delivered['event_ids'])})")
        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == 2, f"the batch is a single host prompt ({len(sends)} sends)")
        expected_ids = [fabricate(index)["session"] for index in range(HEARTBEAT_EVENT_CAP)]
        check(all(name in sends[1] for name in expected_ids),
              "the batch prompt carries every staged event's structured line")
        assert_delivered_notification(sandbox, host, sends[1], delivered["event_ids"][:1], body)

        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "notification turn asks its permission")
        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_confirmed"), 10,
                   "completed batch turn confirms every event")
        check(len(events_of_kind(host_dir, "worker_event_confirmed")[0]["event_ids"])
              == HEARTBEAT_EVENT_CAP, "the whole batch is confirmed at once")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_carrier_is_zcode_host_only() -> None:
    sandbox = Sandbox("zcodeonly")
    try:
        host = sandbox.session()
        sandbox.start(host, "basic")

        # The CLI fails closed on a non-ZCode target, a self target, and junk.
        bad_target = sandbox.session()
        result, _ = sandbox.invoke(
            "start", "--mode", "yolo", session=bad_target, scenario="basic",
            **{HEARTBEAT_HOST_ENV: json.dumps(
                {"platform": "claude-code", "session": host, "repo": str(sandbox.repo)})})
        check(result.returncode != 0 and "ZCode" in (result.stderr or ""),
              f"non-ZCode heartbeat target is refused at start ({result.returncode})")
        check(not sandbox.record_dir(bad_target).exists(),
              "a refused target starts no holder")

        self_target = sandbox.session()
        result, _ = sandbox.invoke(
            "start", "--mode", "yolo", session=self_target, scenario="basic",
            **{HEARTBEAT_HOST_ENV: json.dumps(
                {"platform": "zcode", "session": self_target, "repo": str(sandbox.repo)})})
        check(result.returncode != 0 and "own session" in (result.stderr or ""),
              "a session cannot be its own heartbeat host (loop guard)")
        result, _ = sandbox.invoke(
            "start", "--mode", "yolo", session=sandbox.session(), scenario="basic",
            **{HEARTBEAT_HOST_ENV: "not-json"})
        check(result.returncode != 0, "malformed heartbeat target env is refused")

        # A holder for another platform rejects the op outright.
        fake_agent = sandbox.dir / "fake-acp-agent.py"
        fake_agent.write_text(FAKE_ACP_AGENT, encoding="utf-8")
        fake_agent.chmod(fake_agent.stat().st_mode | 0o755)
        other = f"hb-other-{uuid.uuid4().hex[:8]}"
        receipt = sandbox.cli("start", "--command", f"{PYTHON} {fake_agent}",
                              session=other, scenario=None, platform="claude-code")
        check(receipt.get("state") == "ready", f"non-ZCode holder starts ({receipt.get('error')})")
        other_dir = sandbox.record_dir(other, platform="claude-code")
        rejection = holder_op(holder_socket(other_dir), "worker_event",
                              {"schema": "kaola-worker-event/1", "kind": "idle",
                               "platform": "zcode", "session": "w", "repo": "/x",
                               "reason": "r", "event_cursor": 1})
        check((rejection.get("error") or {}).get("code") == "worker-event-unsupported",
              f"a non-ZCode host holder rejects the carrier op ({rejection})")
        stop = sandbox.cli("stop", "--force", session=other, platform="claude-code")
        check(stop.get("residual_pids") == [], "non-ZCode holder stop leaves no residue")
        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_resume_redelivers_unconfirmed_events() -> None:
    sandbox = Sandbox("resume")
    try:
        host = sandbox.session()
        host_start = sandbox.start(host, "permission")
        body = "HEARTBEAT RESUME: redelivery body."
        sandbox.write_prompt_file(body)
        sandbox.cli("send", "--no-wait", "--text", "host busy turn", session=host)
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "host turn is busy waiting on a permission")
        host_dir = sandbox.record_dir(host)

        event = {"schema": "kaola-worker-event/1", "kind": "idle", "platform": "codex",
                 "session": "work-resume", "repo": os.path.realpath(str(sandbox.repo)),
                 "reason": "outcome=turn_completed stop_reason=end_turn", "event_cursor": 7}
        staged_receipt = holder_op(holder_socket(host_dir), "worker_event", event)
        check(staged_receipt.get("staged") is True, f"event staged on the busy host ({staged_receipt})")

        # The holder and its agent die with the event staged but unconfirmed.
        os.kill(int(host_start["holder_pid"]), signal.SIGKILL)
        os.kill(int(host_start["agent_pid"]), signal.SIGKILL)
        wait_until(lambda: not pid_alive(int(host_start["holder_pid"]))
                   and not pid_alive(int(host_start["agent_pid"])), 8, "holder and agent died")
        check(not events_of_kind(host_dir, "worker_event_confirmed"),
              "the staged event was never confirmed")

        sends_before = len(rpc_sends(sandbox.rpcs[host]))
        resumed = sandbox.cli("start", "--mode", "yolo", "--resume",
                              str(host_start["acp_session_id"]), session=host, scenario="basic")
        check(resumed.get("state") == "ready", f"host session resumes ({resumed.get('error')})")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_restored"), 10,
                   "resume restores the unconfirmed event")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "resume redelivers the unconfirmed event")
        restored = events_of_kind(host_dir, "worker_event_restored")[0]
        check(event["session"] in " ".join(restored["event_ids"]),
              f"the restored ids name the staged event ({restored['event_ids']})")

        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == sends_before + 1,
              f"exactly one redelivered notification after resume ({len(sends)} vs {sends_before})")
        delivered = events_of_kind(host_dir, "worker_event_delivered")[-1]
        assert_delivered_notification(sandbox, host, sends[-1], delivered["event_ids"], body)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_confirmed"), 10,
                   "redelivered notification turn confirms the event")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "resumed host stop leaves no residue")
    finally:
        sandbox.cleanup()


def load_holder_module():
    """The real holder module, imported for its pure prompt-file predicate."""
    import importlib.util
    path = ROOT / "scripts" / "kaola-acp-holder.py"
    spec = importlib.util.spec_from_file_location("kaola_acp_holder_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue_66_defective_prompt_file_reports_its_defect() -> None:
    """Issue #66: a heartbeat prompt file that exists but carries no usable
    ``body`` is reported as the defect it is. The audited Host had written
    ``prompt``; "none maintained" hid that, so the Host believed its full
    prompt was in effect. Visibility only: the event is still delivered."""
    module = load_holder_module()
    read_body = module.heartbeat_prompt_body
    sandbox = Sandbox("defect-unit")
    try:
        path = sandbox.repo.joinpath(*PROMPT_FILE_RELPATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        check(read_body(path) == (None, None),
              "an absent file is the honest fallback, not a defect")
        path.write_text("{not json", encoding="utf-8")
        body, defect = read_body(path)
        check(body is None and "not valid JSON" in (defect or ""),
              f"unparseable JSON is named ({defect})")
        path.write_text('["body"]', encoding="utf-8")
        check("not an object" in (read_body(path)[1] or ""), "a non-object payload is named")
        path.write_text('{"body": 7}', encoding="utf-8")
        check("not a string" in (read_body(path)[1] or ""), "a non-string body is named")
        path.write_text('{"body": ""}', encoding="utf-8")
        check("empty string" in (read_body(path)[1] or ""), "an empty body is named")
        path.write_text('{"prompt": "x", "schema": "s"}', encoding="utf-8")
        wrong_field = read_body(path)[1] or ""
        check('no "body" field' in wrong_field and "prompt" in wrong_field,
              f"a wrong field name is named with the fields present ({wrong_field})")
        # Hostile bytes: not valid UTF-8 at all. Reported, never raised.
        path.write_bytes(b'{"body": "\xff\xfe broken"}')
        body, defect = read_body(path)
        check(body is None and defect is not None and "unreadable" in defect,
              f"undecodable bytes are reported, not raised ({defect})")
        # A directory in the file's place is an OSError, not a crash.
        alt = sandbox.repo / ".kaola" / "as-a-dir.json"
        alt.mkdir(parents=True, exist_ok=True)
        body, defect = read_body(alt)
        check(body is None and defect is not None,
              f"an unreadable path is reported, not raised ({defect})")
        path.write_text('{"body": "real"}', encoding="utf-8")
        check(read_body(path) == ("real", None), "a usable body comes back with no defect")

        # One read, not check-then-reread: the body that passed the checks is
        # the body returned, so a rewrite cannot slip between the two.
        reads: list[str] = []
        original = type(path).read_bytes

        def counting(self, *args, **kwargs):
            reads.append(str(self))
            return original(self, *args, **kwargs)

        type(path).read_bytes = counting
        try:
            body, defect = read_body(path)
        finally:
            type(path).read_bytes = original
        check(len(reads) == 1 and reads[0] == str(path),
              f"the helper reads the prompt file exactly once ({reads})")
        check((body, defect) == ("real", None), "that single read supplies the body itself")
    finally:
        sandbox.cleanup()

    sandbox = Sandbox("defect")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        # The audited real-world mistake: the working prompt written under
        # `prompt` instead of `body`.
        mistyped = "HEARTBEAT UNDER THE WRONG FIELD: dispatch, accept, close out."
        path = sandbox.repo.joinpath(*PROMPT_FILE_RELPATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1",
                                    "prompt": mistyped}), encoding="utf-8")
        sandbox.start(worker, "basic",
                      heartbeat_host={"platform": "zcode", "session": host,
                                      "repo": str(sandbox.repo)})
        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "worker stop receipt is terminal")

        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "a defective prompt file still delivers the worker event")
        delivered = events_of_kind(host_dir, "worker_event_delivered")[0]
        check(delivered.get("heartbeat_maintained") is False,
              "a defective file is not reported as a maintained prompt")
        error = str(delivered.get("heartbeat_body_error") or "")
        check('no "body" field' in error and "prompt" in error,
              f"the delivery log names the actual defect ({error})")

        content = rpc_sends(sandbox.rpcs[host])[0]
        check("present but UNUSABLE" in content,
              "the notification says the file exists and is unusable")
        check("No maintained heartbeat prompt was found" not in content
              and "none maintained at" not in content,
              "the notification no longer claims there is no file")
        check('"body"' in content and str(path) in content,
              "the notification names the file and the field to fix")
        check(mistyped not in content,
              "text under the wrong field is never passed off as the prompt body")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_issue_66_unarmed_worker_stays_ungated() -> None:
    """Issue #66: an ordinary worker - no Host, no binding - gains no gate.
    Issue #70: its start receipt says so explicitly - a known, null binding -
    blocking send still works, and its holder never runs the carrier."""
    sandbox = Sandbox("unarmed")
    try:
        worker = sandbox.session()
        start = sandbox.start(worker, "basic")
        check(start.get("heartbeat_host_known") is True
              and start.get("heartbeat_host") is None
              and start.get("heartbeat_host_requested") is None,
              "an unarmed start reports a known, unbound fact "
              f"({start.get('heartbeat_host')}, known={start.get('heartbeat_host_known')})")
        reply = sandbox.cli("send", "--text", "ordinary blocking dispatch", session=worker)
        check(reply.get("error") is None and reply.get("outcome") == "turn_completed",
              f"blocking send on an unbound worker still completes ({reply.get('outcome')})")
        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "an unbound worker stops normally")
        worker_dir = sandbox.record_dir(worker)
        check(not events_of_kind(worker_dir, "heartbeat_carrier_sent"),
              "an unbound worker holder never runs the event carrier")
    finally:
        sandbox.cleanup()


def test_canonical_heartbeat_spec_stays_one_set() -> None:
    skeleton = ROOT / "templates" / "orchestrator" / "references" / "heartbeat-skeleton.txt"
    text = skeleton.read_text(encoding="utf-8")
    check("PROJECT_RUNNER_HEARTBEAT_V2" in text, "the canonical skeleton keeps its version marker")
    # Issue #68: the skeleton now names which host's trigger delivers the heartbeat
    # (Codex/Grok Bot timer vs ZCode Host worker events), so the host name itself is
    # no longer the tell. The one-set invariant is that the carrier is still specified
    # once: the event-carrier mechanism only in the Skill, the prompt path only here.
    check("KAOLA_ACP_HEARTBEAT_HOST" not in text,
          "the ZCode event-carrier mechanism is specified in the Skill, not re-specified in the skeleton")
    check(text.count(".kaola/heartbeat-prompt.json") == 1,
          "the ZCode prompt carrier is named exactly once in the skeleton (one set)")
    check("ZCode Host 更新项目根 `.kaola/heartbeat-prompt.json`" in text,
          "the skeleton scopes that carrier to the ZCode Host and leaves other hosts their own")
    rendered = sorted((ROOT / "skills" / "kaola-project-runner").glob("**/heartbeat-skeleton*"))
    check(len(rendered) == 1, f"the orchestrator package carries exactly one skeleton ({rendered})")

    skill = (ROOT / "skills" / "kaola-project-runner" / "SKILL.md").read_text(encoding="utf-8")
    check("KAOLA_ACP_HEARTBEAT_HOST" in skill,
          "the shared Skill documents the ZCode event-carrier override")
    check(skill.count("KAOLA_ACP_HEARTBEAT_HOST") == 1,
          "the override appears once; no duplicated second spec")
    check("30 minutes unless specified" in skill,
          "other hosts' default periodic heartbeat wording is unchanged")
    check(len(skill.encode("utf-8")) <= 17408, "the main Skill stays within its byte budget")

    grok_golden = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", "templates/grok-golden"],
        capture_output=True,
    )
    check(grok_golden.returncode == 0, "templates/grok-golden stays frozen")
    drifted = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--",
         "templates/orchestrator/references/heartbeat-skeleton.txt"],
        capture_output=True,
    )
    check(drifted.returncode == 0, "the canonical skeleton template has no uncommitted drift")


def main() -> int:
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failures = 0
    for test in tests:
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report every failure, keep running
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(
        f"test-zcode-heartbeat-contract: {len(tests) - failures}/{len(tests)} tests, "
        f"{len(CHECKS)} checks"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
