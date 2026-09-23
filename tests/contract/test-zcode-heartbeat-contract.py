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
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
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
OVERFLOW_FULL_CHECK_MARK = "kaola-host-notify/overflow-full-check"

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

    def entry_for(self, scenario: str, session: str,
                  entry_env: dict[str, str] | None = None) -> Path:
        key = (scenario, session)
        if key in self.entries:
            return self.entries[key]
        # The fake record and rpc log are per SESSION (a resumed holder spawns
        # a fresh fake that appends to the same log); only the entry script
        # differs per scenario. ``entry_env`` is set inside the fake's own
        # process (after the bridge allowlist), never through the holder.
        record = self.dir / f"fake-{session}.json"
        rpc = self.dir / f"rpc-{session}.jsonl"
        entry = self.dir / f"zcode-entry-{scenario}-{session}.py"
        extra = "".join(f"os.environ[{name!r}] = {value!r}\n"
                        for name, value in sorted((entry_env or {}).items()))
        entry.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(record)!r}\n"
            f"os.environ['FAKE_ZCODE_RPC_LOG'] = {str(rpc)!r}\n"
            + extra +
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
               timeout: float = 120, cli_path: Path | None = None,
               **env_overrides: str | None) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        # ``cli_path`` runs an installed Skill tree's own copy instead of the
        # checkout CLI (Issue #105 compares installed copies against the tree
        # the running CLI came from, which a checkout invocation does not have).
        argv = [PYTHON, str(cli_path or CHECKOUT_CLI), platform, command, "--repo", str(self.repo)]
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
            cli_path: Path | None = None, **env_overrides: str | None) -> dict:
        result, payload = self.invoke(
            command, *args, session=session, scenario=scenario, platform=platform,
            timeout=timeout, cli_path=cli_path, **env_overrides,
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
        shutil.rmtree(self.dir, ignore_errors=True)


def fabricate_event(sandbox: Sandbox, index: int, *, kind: str = "idle",
                    session: str | None = None, request_id: str | None = None,
                    reason: str | None = None) -> dict:
    event = {
        "schema": "kaola-worker-event/1",
        "kind": kind,
        "platform": "codex",
        "session": session or f"work-{index}",
        "repo": os.path.realpath(str(sandbox.repo)),
        "reason": reason or "outcome=turn_completed stop_reason=end_turn",
        "event_cursor": 100 + index,
    }
    if request_id is not None:
        event["request_id"] = request_id
    return event


def assert_overflow_full_check(content: str) -> None:
    check(OVERFLOW_FULL_CHECK_MARK in content,
          "overflow delivery names the full-check marker")
    check("inspect every authorized worker's real status and pending approvals"
          in content,
          "overflow delivery requires a full status and pending-approval check")
    check("Remind only; do not approve or refuse permissions from this signal"
          in content,
          "overflow delivery reminds only and does not auto-approve")


def assert_delivered_notification(sandbox: Sandbox, host: str, content: str,
                                  event_ids: list[str], body: str) -> None:
    """The delivered prompt is one literal text: the native Skill entry line,
    fixed metadata, the event lines, the current full heartbeat body verbatim,
    and the one-pass instruction per PROJECT_RUNNER_HEARTBEAT_V2."""
    first_line = content.split("\n", 1)[0]
    check(first_line == "/kaola-project-runner",
          f"notification payload opens with the native Skill entry line (got {first_line!r})")
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


def entryless_cli(sandbox, platform: str) -> Path:
    """Issue #126: every shipped platform has a measured Host entry, so the
    Issue #122 fail-closed rows run on an installed copy of ``platform``'s
    worker Skill with codex's entry emptied (the pre-#126 shipped state): its
    code table always, and its manifest when the tree is codex's own."""
    tree = sandbox.dir / "installed" / f"{platform}-kaola-project-runner"
    if not tree.exists():
        shutil.copytree(ROOT / "skills" / f"{platform}-kaola-project-runner", tree)
        edits = [("kaola-acp.py", '"codex": "$kaola-project-runner",', '"codex": "",')]
        if platform == "codex":
            edits.append(("platform.yaml", 'host_skill_entry: "$kaola-project-runner"',
                          'host_skill_entry: ""'))
        for name, old, new in edits:
            path = tree / "scripts" / name
            text = path.read_text(encoding="utf-8")
            check(text.count(old) == 1, f"fixture: {platform} {name} carries the codex entry once")
            path.write_text(text.replace(old, new), encoding="utf-8")
    return tree / "scripts" / "kaola-acp.py"


def test_carrier_needs_host_skill_entry() -> None:
    """Issue #119: the carrier is open to every platform with a measured Host
    Skill entry; a platform without one (an emptied-entry fixture since
    Issue #126 admitted codex) still fails closed."""
    sandbox = Sandbox("zcodeonly")
    try:
        host = sandbox.session()
        sandbox.start(host, "basic")

        # The CLI fails closed on an entry-less target, a self target, and junk.
        bad_target = sandbox.session()
        result, refused = sandbox.invoke(
            "start", "--mode", "yolo", session=bad_target, scenario="basic",
            cli_path=entryless_cli(sandbox, "zcode"),
            **{HEARTBEAT_HOST_ENV: json.dumps(
                {"platform": "codex", "session": host, "repo": str(sandbox.repo)})})
        refused = refused or {}
        check(result.returncode == 1 and refused.get("reason") == "host-entry-unsupported"
              and refused.get("mutation_performed") is False
              and "codex" in (refused.get("detail") or ""),
              f"Issue #122: entry-less heartbeat target is a typed refusal ({refused})")
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

        # A holder for an entry-less platform rejects the op outright.
        fake_agent = sandbox.dir / "fake-acp-agent.py"
        fake_agent.write_text(FAKE_ACP_AGENT, encoding="utf-8")
        fake_agent.chmod(fake_agent.stat().st_mode | 0o755)
        other = f"hb-other-{uuid.uuid4().hex[:8]}"
        codex_cli = entryless_cli(sandbox, "codex")
        receipt = sandbox.cli("start", "--command", f"{PYTHON} {fake_agent}",
                              session=other, scenario=None, platform="codex", cli_path=codex_cli)
        check(receipt.get("state") == "ready", f"entry-less holder starts ({receipt.get('error')})")
        other_dir = sandbox.record_dir(other, platform="codex")
        rejection = holder_op(holder_socket(other_dir), "worker_event",
                              {"schema": "kaola-worker-event/1", "kind": "idle",
                               "platform": "zcode", "session": "w", "repo": "/x",
                               "reason": "r", "event_cursor": 1})
        check((rejection.get("error") or {}).get("code") == "worker-event-unsupported",
              f"an entry-less host holder rejects the carrier op ({rejection})")
        stop = sandbox.cli("stop", "--force", session=other, platform="codex", cli_path=codex_cli)
        check(stop.get("residual_pids") == [], "entry-less holder stop leaves no residue")
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
        original_open = Path.open
        original_read_bytes = Path.read_bytes

        def counting_open(self, *args, **kwargs):
            if str(self) == str(path):
                reads.append("open")
            return original_open(self, *args, **kwargs)

        def counting_read_bytes(self, *args, **kwargs):
            if str(self) == str(path):
                reads.append("read_bytes")
            return original_read_bytes(self, *args, **kwargs)

        Path.open = counting_open  # type: ignore[method-assign]
        Path.read_bytes = counting_read_bytes  # type: ignore[method-assign]
        try:
            body, defect = read_body(path)
        finally:
            Path.open = original_open  # type: ignore[method-assign]
            Path.read_bytes = original_read_bytes  # type: ignore[method-assign]
        check(len(reads) == 1 and reads[0] in {"open", "read_bytes"},
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
        # Issue #104 P6: no dispatcher and no variable is source "none".
        check(start.get("heartbeat_host_source") == "none" and start.get("dispatcher") is None,
              f"an unarmed start names its source as none ({start.get('heartbeat_host_source')})")
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


def test_issue_87_overflow_full_check_on_busy_host() -> None:
    """Issue #87: the 33rd event is not a 33rd detailed line; the next
    heartbeat is a full-check. Overflow during that notification is a later
    generation and still needs the following wake. The carrier never
    auto-approves."""
    sandbox = Sandbox("overflow")
    try:
        host = sandbox.session()
        sandbox.start(host, "permission")
        body = "HEARTBEAT OVERFLOW: full-check body."
        sandbox.write_prompt_file(body)
        sandbox.cli("send", "--no-wait", "--text", "host busy turn", session=host)
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "host turn is busy waiting on a permission")
        host_dir = sandbox.record_dir(host)
        sock = holder_socket(host_dir)

        for index in range(HEARTBEAT_EVENT_CAP):
            receipt = holder_op(sock, "worker_event", fabricate_event(sandbox, index))
            check(receipt.get("staged") is True and receipt.get("error") is None,
                  f"event {index} stages while the host is busy ({receipt})")

        first = holder_op(sock, "worker_event", fabricate_event(
            sandbox, 32, kind="permission_required", session="work-pending-87",
            request_id="req-87-pending",
            reason="session/request_permission pending"))
        check((first.get("error") or {}).get("code") == "worker-event-queue-full",
              f"the 33rd detailed event is still refused as queue-full ({first})")
        check(first.get("overflow_full_check") is True,
              f"the queue-full receipt records the recoverable full-check ({first})")
        check(len(events_of_kind(host_dir, "worker_event")) == HEARTBEAT_EVENT_CAP,
              "exactly 32 detailed events remain staged")
        check(events_of_kind(host_dir, "worker_event_overflow"),
              "the existing event log keeps the overflow fact")

        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "busy boundary flushes the bounded batch plus the full-check")
        delivered = events_of_kind(host_dir, "worker_event_delivered")[0]
        check(len(delivered["event_ids"]) == HEARTBEAT_EVENT_CAP,
              f"one prompt still flushes only the 32 detailed events ({len(delivered['event_ids'])})")
        check(delivered.get("overflow_full_check") is True,
              f"delivery records the overflow full-check ({delivered})")
        sends = rpc_sends(sandbox.rpcs[host])
        check(len(sends) == 2, f"the batch plus full-check is a single host prompt ({len(sends)} sends)")
        assert_delivered_notification(sandbox, host, sends[1], delivered["event_ids"][:1], body)
        assert_overflow_full_check(sends[1])

        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "notification turn asks its permission")
        later = holder_op(sock, "worker_event", fabricate_event(
            sandbox, 33, kind="terminated", session="work-done-87", reason="exit_0"))
        check((later.get("error") or {}).get("code") == "worker-event-queue-full",
              f"overflow during the notification is still queue-full ({later})")
        check(len(events_of_kind(host_dir, "worker_event_overflow")) >= 2,
              "a later overflow is another fact in the same event log")

        sandbox.cli("permit", "--option", "allow", session=host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_overflow_confirmed"), 10,
                   "the notification confirms only the generation it delivered")
        wait_until(lambda: len(events_of_kind(host_dir, "worker_event_delivered")) >= 2, 10,
                   "the later overflow still wakes the next heartbeat")
        second = events_of_kind(host_dir, "worker_event_delivered")[1]
        check(second.get("overflow_full_check") is True,
              f"the next wake still carries the full-check ({second})")
        assert_overflow_full_check(rpc_sends(sandbox.rpcs[host])[-1])

        answered = [entry for entry in events_of_kind(host_dir, "permission_answered")
                    if entry.get("request_id") == "req-87-pending"]
        check(not answered, f"the carrier does not auto-approve ({answered})")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_issue_87_overflow_survives_stop_and_resume() -> None:
    """Issue #87: unconfirmed overflow facts in the existing event log are
    rebuilt after exact Host stop and ``start --resume``."""
    sandbox = Sandbox("overflow-resume")
    try:
        host = sandbox.session()
        host_start = sandbox.start(host, "permission")
        body = "HEARTBEAT OVERFLOW RESUME: redelivery body."
        sandbox.write_prompt_file(body)
        sandbox.cli("send", "--no-wait", "--text", "host busy turn", session=host)
        wait_until(lambda: (sandbox.cli("status", session=host).get("pending_permissions") or []),
                   15, "host turn is busy waiting on a permission")
        host_dir = sandbox.record_dir(host)
        sock = holder_socket(host_dir)

        for index in range(HEARTBEAT_EVENT_CAP):
            receipt = holder_op(sock, "worker_event", fabricate_event(sandbox, index))
            check(receipt.get("staged") is True, f"event {index} staged ({receipt})")
        for index in (32, 33):
            overflow = holder_op(sock, "worker_event", fabricate_event(sandbox, index))
            check((overflow.get("error") or {}).get("code") == "worker-event-queue-full",
                  f"overflow {index} is queue-full ({overflow})")
        check(len(events_of_kind(host_dir, "worker_event_overflow")) >= 2,
              "each overflow is a fact in the event log before stop")
        check(not events_of_kind(host_dir, "worker_event_overflow_confirmed"),
              "the overflow full-check is unconfirmed at stop")

        native_id = host_start.get("acp_session_id")
        stop = sandbox.cli("stop", session=host)
        check(stop.get("stopped") is True, f"exact host stop is terminal ({stop})")
        check(stop.get("residual_pids") == [],
              f"exact host stop leaves no residue ({stop.get('residual_pids')})")
        check(not events_of_kind(host_dir, "worker_event_overflow_confirmed"),
              "exact stop does not confirm the overflow in place of resume")

        sends_before = len(rpc_sends(sandbox.rpcs[host]))
        resumed = sandbox.cli("start", "--mode", "yolo", "--resume",
                              str(native_id), session=host, scenario="basic")
        check(resumed.get("state") == "ready", f"host session resumes ({resumed.get('error')})")
        wait_until(lambda: any(
            entry.get("overflow_full_check") is True
            for entry in events_of_kind(host_dir, "worker_event_delivered")), 10,
                   "resume redelivers the unconfirmed overflow full-check")
        content = rpc_sends(sandbox.rpcs[host])[-1]
        check(len(rpc_sends(sandbox.rpcs[host])) == sends_before + 1,
              "resume adds one notification")
        assert_overflow_full_check(content)
        assert_delivered_notification(
            sandbox, host, content,
            events_of_kind(host_dir, "worker_event_delivered")[-1]["event_ids"][:1],
            body)

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "resumed host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_issue_87_oversized_heartbeat_prompt_is_not_injected() -> None:
    """Issue #87: an oversized heartbeat-prompt.json is a named defect, never
    a truncated-looking body, and the worker event still wakes."""
    module = load_holder_module()
    bound = getattr(module, "HEARTBEAT_PROMPT_MAX_BYTES", None)
    check(bound == 65536, f"the prompt-file read is capped at 64KiB ({bound})")
    read_body = module.heartbeat_prompt_body
    sandbox = Sandbox("oversize-unit")
    try:
        path = sandbox.repo.joinpath(*PROMPT_FILE_RELPATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        marker = "ISSUE87-OVERSIZE-TOKEN-" + uuid.uuid4().hex
        payload = json.dumps({"schema": "kaola-heartbeat-prompt/1",
                              "body": ("A" * bound) + marker}, ensure_ascii=False)
        path.write_text(payload, encoding="utf-8")
        body, defect = read_body(path)
        check(body is None and defect is not None and str(bound) in defect,
              f"an oversized file is a named defect ({body!r}, {defect})")
        check(marker not in (defect or ""),
              "oversized bytes are not passed off as the defect")

        ordinary = "ISSUE87-ORDINARY-COMPLETE-BODY"
        path.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1",
                                    "body": ordinary}), encoding="utf-8")
        reads: list[str] = []
        original_open = Path.open

        def counting_open(self, *args, **kwargs):
            if str(self) == str(path):
                reads.append("open")
            return original_open(self, *args, **kwargs)

        Path.open = counting_open  # type: ignore[method-assign]
        try:
            body, defect = read_body(path)
        finally:
            Path.open = original_open  # type: ignore[method-assign]
        check(reads == ["open"] and (body, defect) == (ordinary, None),
              f"one bounded read still returns the complete ordinary body ({reads})")
    finally:
        sandbox.cleanup()

    sandbox = Sandbox("oversize-live")
    try:
        host = sandbox.session()
        worker = sandbox.session()
        sandbox.start(host, "basic")
        marker = "ISSUE87-LIVE-OVERSIZE-" + uuid.uuid4().hex
        path = sandbox.repo.joinpath(*PROMPT_FILE_RELPATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": "kaola-heartbeat-prompt/1",
                                    "body": ("B" * bound) + marker}), encoding="utf-8")
        sandbox.start(worker, "basic",
                      heartbeat_host={"platform": "zcode", "session": host,
                                      "repo": str(sandbox.repo)})
        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "worker stop receipt is terminal")
        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "an oversized prompt file still delivers the worker event")
        content = rpc_sends(sandbox.rpcs[host])[0]
        check(marker not in content, "oversized body bytes never enter the Host prompt")
        check("present but UNUSABLE" in content and str(bound) in content,
              "the notification names the oversized-file defect")
        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
    finally:
        sandbox.cleanup()


class MemoryEventLog:
    """In-memory EventLog stand-in for restore-order tests. ``read_since``
    returns the recorded list as-is, including out-of-order generations."""

    def __init__(self, entries: list[dict] | None = None):
        self.entries = list(entries or [])

    def read_since(self, cursor, limit):  # noqa: ARG002 - EventLog signature
        return list(self.entries)

    def append(self, event: dict) -> int:
        self.entries.append(dict(event))
        return len(self.entries)


def bare_holder(module, entries: list[dict] | None = None, *,
                pending: list[dict] | None = None):
    """Real ``Holder`` restore/overflow methods, no agent process."""
    holder = object.__new__(module.Holder)
    holder.worker_events_lock = threading.Lock()
    holder.events = MemoryEventLog(entries)
    holder.pending_worker_events = list(pending or [])
    holder.overflow_generation = 0
    holder.overflow_confirmed_generation = 0
    holder.overflow_inflight_generation = None
    holder.overflow_inflight_fingerprint = None
    holder.confirmed_worker_events = {}
    holder.confirmed_worker_events_partial = False
    holder.turn = {"active": False}

    class Agent:
        proc = object()
        exited = threading.Event()

    holder.agent = Agent()
    holder.args = type("Args", (), {"platform": "zcode", "repo": "/nonexistent",
                                    "session": "host"})()
    holder.host_entry = module.HOST_SKILL_ENTRY
    holder.host_name = "ZCode"
    return holder


def test_issue_87_restore_takes_max_generation_when_log_is_reordered() -> None:
    """Issue #87 P1: overflow gen2 can land in the log before a late gen1.
    Restore must keep generation 2 pending after gen1 was already confirmed."""
    module = load_holder_module()
    holder = bare_holder(module, [
        {"kind": "worker_event_delivered", "event_ids": [],
         "overflow_full_check": True, "overflow_generation": 1},
        {"kind": "worker_event_overflow_confirmed", "generation": 1},
        {"kind": "worker_event_overflow", "generation": 2},
        {"kind": "worker_event_overflow", "generation": 1},
    ])
    delivered: list[dict] = []
    holder._deliver_worker_events = (  # type: ignore[method-assign]
        lambda: delivered.append({"overflow_full_check": True}) or {
            "delivered": True, "overflow_full_check": True})
    holder._restore_worker_events()
    check(holder.overflow_generation == 2,
          f"restore keeps the max overflow generation ({holder.overflow_generation})")
    check(holder.overflow_confirmed_generation == 1,
          f"restore keeps confirmed generation 1 ({holder.overflow_confirmed_generation})")
    check(holder.overflow_generation > holder.overflow_confirmed_generation,
          "unconfirmed gen2 full-check remains pending")
    check(delivered == [{"overflow_full_check": True}],
          f"restore delivers the pending full-check ({delivered})")


def test_issue_87_idle_full_queue_overflow_delivers_now() -> None:
    """Issue #87: a full detailed queue on an idle Host must not wait for a
    later worker event; the overflow itself triggers full-check delivery."""
    module = load_holder_module()
    pending = [{"event_id": f"codex/work-{index}/idle/{100 + index}",
                "kind": "idle", "platform": "codex", "session": f"work-{index}",
                "repo": "/x", "reason": "end_turn", "event_cursor": 100 + index}
               for index in range(HEARTBEAT_EVENT_CAP)]
    holder = bare_holder(module, pending=pending)
    prompts: list[dict] = []

    def fake_prompt(params):
        prompts.append(params)
        return {"outcome": "in_progress", "prompt_fingerprint": "fp-idle-full"}

    holder.op_prompt = fake_prompt  # type: ignore[method-assign]
    overflow = holder.op_worker_event({
        "kind": "terminated", "platform": "codex", "session": "work-33",
        "repo": "/x", "reason": "exit_0", "event_cursor": 133,
    })
    check((overflow.get("error") or {}).get("code") == "worker-event-queue-full",
          f"the 33rd event is still queue-full ({overflow})")
    check(overflow.get("overflow_full_check") is True,
          f"the idle overflow records a full-check ({overflow})")
    check(overflow.get("delivered") is True,
          f"idle overflow delivers the full-check immediately ({overflow})")
    check(len(prompts) == 1, f"one prompt is admitted now, not later ({prompts})")
    check(OVERFLOW_FULL_CHECK_MARK in str(prompts[0].get("text") or ""),
          "the immediate prompt is the full-check")
    check(len(holder.events.entries) >= 1 and any(
        entry.get("kind") == "worker_event_overflow" for entry in holder.events.entries),
          "the overflow fact is in the event log")


def test_issue_87_restore_seeds_generation_from_confirmed_after_rotation() -> None:
    """Issue #87: rotated EventLog may keep confirmed generation=2 while older
    overflow records are gone. Restore must seed current generation at least
    that confirmed value so the next overflow still delivers a full-check."""
    module = load_holder_module()
    holder = bare_holder(module, [
        {"kind": "worker_event_overflow_confirmed", "generation": 2},
    ])
    holder._restore_worker_events()
    check(holder.overflow_confirmed_generation == 2,
          f"restore sees confirmed generation 2 ({holder.overflow_confirmed_generation})")
    check(holder.overflow_generation >= 2,
          f"restore seeds current generation at least confirmed ({holder.overflow_generation})")
    check(not any(entry.get("kind") == "worker_event_restored"
                  for entry in holder.events.entries),
          "a fully confirmed generation does not redeliver")

    holder.pending_worker_events = [
        {"event_id": f"codex/work-{index}/idle/{100 + index}",
         "kind": "idle", "platform": "codex", "session": f"work-{index}",
         "repo": "/x", "reason": "end_turn", "event_cursor": 100 + index}
        for index in range(HEARTBEAT_EVENT_CAP)]
    prompts: list[dict] = []

    def fake_prompt(params):
        prompts.append(params)
        return {"outcome": "in_progress", "prompt_fingerprint": "fp-rot"}

    holder.op_prompt = fake_prompt  # type: ignore[method-assign]
    overflow = holder.op_worker_event({
        "kind": "terminated", "platform": "codex", "session": "work-rot",
        "repo": "/x", "reason": "exit_0", "event_cursor": 200,
    })
    check((overflow.get("error") or {}).get("code") == "worker-event-queue-full",
          f"the next event is still queue-full ({overflow})")
    check(overflow.get("generation") == 3,
          f"new overflow continues from confirmed generation 2 ({overflow})")
    check(overflow.get("delivered") is True and overflow.get("overflow_full_check") is True,
          f"the continued generation still delivers a full-check ({overflow})")
    check(OVERFLOW_FULL_CHECK_MARK in str(prompts[0].get("text") or "") if prompts else False,
          "the delivered prompt is the full-check")


def test_issue_94_interrupt_steer_resends_verbatim_on_every_session() -> None:
    """Issue #94 re-review: `steer --steer-mode interrupt` resends on a NEW
    turn but is NOT a Host recovery entry — the holder sends the Agent's
    text verbatim on every session, infers no Host identity from literal
    prompt content, and nothing is created or restored across a restart.
    A caller wanting the resend to open a Host round supplies the entry
    line itself."""
    sandbox = Sandbox("i94-interrupt")
    try:
        host = sandbox.session()
        host_start = sandbox.start(host, "slow")
        # A Host-shaped session — an admitted prompt opened with the native
        # entry line — still gets a byte-verbatim resend: no prepend, no
        # marker. `slow` keeps the turn active so the composite cancels for real.
        sandbox.cli("send", "--no-wait", "--text",
                    "/kaola-project-runner\nI94-HOST-BODY", session=host)
        steer = sandbox.cli("steer", "--steer-mode", "interrupt",
                            "--text", "I94-STEER-BODY", session=host)
        check(steer.get("steer_outcome") == "interrupted_and_resent",
              f"the running turn was really interrupted and resent ({steer.get('steer_outcome')})")
        check("host_skill_entry_prepended" not in steer,
              f"no prepend receipt exists ({steer})")
        sends = rpc_sends(sandbox.rpcs[host])
        check(sends[-1] == "I94-STEER-BODY",
              f"the resend is byte-verbatim even on a Host-shaped session ({sends[-1][:80]!r})")

        # A caller that supplies the entry line gets it back unchanged —
        # transport is verbatim in both directions, never inferred.
        sandbox.cli("send", "--no-wait", "--text", "I94-BUSY-2", session=host)
        steer2 = sandbox.cli("steer", "--steer-mode", "interrupt",
                             "--text", "/kaola-project-runner\nI94-ROUND",
                             session=host)
        check(steer2.get("steer_outcome") == "interrupted_and_resent",
              f"an explicit-entry resend also interrupts ({steer2.get('steer_outcome')})")
        sends = rpc_sends(sandbox.rpcs[host])
        check(sends[-1] == "/kaola-project-runner\nI94-ROUND",
              f"a caller-supplied entry passes through unchanged ({sends[-1][:80]!r})")

        # Restart boundary: stop, resume, interrupt again — the resend is
        # still verbatim; no implicit Host marker exists to lose or restore.
        sandbox.cli("stop", "--force", session=host)
        resumed = sandbox.cli("start", "--mode", "yolo", "--resume",
                              str(host_start["acp_session_id"]),
                              session=host, scenario="slow")
        check(resumed.get("state") == "ready", f"host resumes ({resumed.get('error')})")
        sandbox.cli("send", "--no-wait", "--text", "I94-AFTER-RESUME",
                    session=host)
        steer3 = sandbox.cli("steer", "--steer-mode", "interrupt",
                             "--text", "I94-POST-RESTART", session=host)
        check(steer3.get("steer_outcome") == "interrupted_and_resent",
              f"post-restart interrupt resends ({steer3.get('steer_outcome')})")
        sends = rpc_sends(sandbox.rpcs[host])
        check(sends[-1] == "I94-POST-RESTART",
              f"after stop/resume the resend is still verbatim ({sends[-1][:80]!r})")

        worker = sandbox.session()
        sandbox.start(worker, "slow")
        sandbox.cli("send", "--no-wait", "--text", "I94-WORKER-BODY",
                    session=worker)
        wsteer = sandbox.cli("steer", "--steer-mode", "interrupt",
                             "--text", "I94-WORKER-STEER", session=worker)
        check(wsteer.get("steer_outcome") == "interrupted_and_resent",
              f"the worker interrupt also resends ({wsteer.get('steer_outcome')})")
        wsends = rpc_sends(sandbox.rpcs[worker])
        check(wsends[-1] == "I94-WORKER-STEER",
              f"an ordinary worker resend is verbatim ({wsends[-1][:80]!r})")

        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stop leaves no residue")
        worker_stop = sandbox.cli("stop", "--force", session=worker)
        check(worker_stop.get("residual_pids") == [], "worker stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_canonical_heartbeat_spec_stays_one_set() -> None:
    skeleton = ROOT / "templates" / "orchestrator" / "references" / "heartbeat-skeleton.txt"
    text = skeleton.read_text(encoding="utf-8")
    check("PROJECT_RUNNER_HEARTBEAT_V2" in text, "the canonical skeleton keeps its version marker")
    # Issue #68/#74: the skeleton names which host's trigger delivers the heartbeat
    # (Codex timer vs ZCode Host worker events; Grok Bot does not load this Skill).
    # The one-set invariant is that the carrier is still specified once: the
    # event-carrier mechanism only in the Skill, the prompt path only here.
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
    check("Codex 由其定时系统触发投递" in text, "Codex keeps its timer trigger")
    check("Grok Bot 不加载本 Skill" in text, "Grok Bot is not a Project Runner heartbeat host")
    rendered_text = rendered[0].read_text(encoding="utf-8")
    check("PROJECT_RUNNER_HEARTBEAT_V2" in rendered_text, "the generated skeleton matches the canonical marker")


# ---------------------------------------------------------------------------
# Issue #104: mechanical KAOLA_ACP_HEARTBEAT_HOST binding on the dispatch path
# (design: kaola-workflow/archive/issue-99/evidence/heartbeat-auto-bind-design.md
# §a.2 resolution table, §a.3 verification, §b failure shape, §e cases).

DISPATCHER_ENV = "KAOLA_ACP_DISPATCHER"


def host_record(sandbox: Sandbox, session: str) -> dict:
    return json.loads((sandbox.record_dir(session) / "record.json").read_text(encoding="utf-8"))


def dispatcher_of(sandbox: Sandbox, session: str, **override: str) -> dict:
    """The identity fact a holder sets for its agent (design §a.1)."""
    record = host_record(sandbox, session)
    fact = {"holder_instance_id": record["holder_instance_id"], "platform": "zcode",
            "repo": record["repo"], "session": session}
    fact.update(override)
    return fact


def expected_fact(sandbox: Sandbox, host: str) -> dict:
    return {"platform": "zcode", "session": host, "repo": os.path.realpath(str(sandbox.repo)),
            "socket": str(holder_socket(sandbox.record_dir(host)))}


def refused_start(sandbox: Sandbox, worker: str, reason: str, label: str,
                  platform: str = "zcode", **env: str | None) -> dict:
    """A refused start: exit 1, typed receipt, and nothing created (design §b)."""
    result, payload = sandbox.invoke("start", "--mode", "yolo", session=worker,
                                     scenario="basic", platform=platform, **env)
    check(result.returncode == 1, f"{label}: refusal exits 1 ({result.returncode}: {result.stderr[-300:]})")
    check(isinstance(payload, dict) and payload.get("result") == "refused"
          and payload.get("reason") == reason and payload.get("action") == "start",
          f"{label}: typed refusal {reason} ({payload})")
    check(payload.get("mutation_performed") is False
          and payload.get("mutation_status") == "not_started",
          f"{label}: refusal performed no mutation")
    check(payload.get("platform") == platform and payload.get("session") == worker
          and "transport" in payload and "detail" in payload,
          f"{label}: refusal names the worker and carries transport/detail")
    worker_dir = sandbox.record_dir(worker, platform=platform)
    check(not worker_dir.exists(), f"{label}: refusal wrote no record")
    check(not holder_socket(worker_dir).exists(), f"{label}: refusal opened no socket")
    check(len(json.dumps(payload).encode("utf-8")) <= 4096, f"{label}: refusal receipt stays bounded")
    return payload


def test_issue_104_dispatcher_refusals_open_nothing() -> None:
    """Design §e N1-N5, N7 and the second form of N8: a provable dispatcher
    whose Host holder cannot be bound is refused before anything exists."""
    sandbox = Sandbox("i104-refuse")
    try:
        host_a = sandbox.session()
        host_b = sandbox.session()
        sandbox.start(host_a, "basic")
        sandbox.start(host_b, "basic")
        dispatcher_a = dispatcher_of(sandbox, host_a)

        # N1: dispatcher names a ZCode session that has no record at all.
        ghost = sandbox.session()
        receipt = refused_start(
            sandbox, sandbox.session(), "heartbeat-host-unresolved", "N1",
            **{DISPATCHER_ENV: json.dumps(dict(dispatcher_a, session=ghost))})
        check("record is missing" in receipt.get("detail", ""),
              f"N1: detail names the missing record ({receipt.get('detail')})")
        check(receipt.get("heartbeat_host_source") == "dispatcher"
              and (receipt.get("dispatcher") or {}).get("session") == ghost
              and (receipt.get("heartbeat_host_requested") or {}).get("session") == ghost,
              "N1: refusal reports the source, the dispatcher, and the derived request")

        # N3: the record is live but belongs to a different holder instance.
        receipt = refused_start(
            sandbox, sandbox.session(), "heartbeat-host-unresolved", "N3",
            **{DISPATCHER_ENV: json.dumps(dict(dispatcher_a, holder_instance_id="0" * 32))})
        check("holder_instance_id" in receipt.get("detail", ""),
              f"N3: detail names the instance mismatch ({receipt.get('detail')})")

        # N4: record live, admin socket file gone.
        sock = holder_socket(sandbox.record_dir(host_a))
        aside = sock.with_suffix(".aside")
        os.rename(sock, aside)
        try:
            receipt = refused_start(
                sandbox, sandbox.session(), "heartbeat-host-unresolved", "N4",
                **{DISPATCHER_ENV: json.dumps(dispatcher_a)})
        finally:
            os.rename(aside, sock)
        check("socket is missing" in receipt.get("detail", ""),
              f"N4: detail names the missing socket ({receipt.get('detail')})")

        # N5: dispatcher is live Host A, the explicit variable names live Host B.
        receipt = refused_start(
            sandbox, sandbox.session(), "heartbeat-host-conflict", "N5",
            **{DISPATCHER_ENV: json.dumps(dispatcher_a),
               HEARTBEAT_HOST_ENV: json.dumps({"platform": "zcode", "session": host_b,
                                               "repo": str(sandbox.repo)})})
        check(receipt.get("heartbeat_host_source") == "explicit"
              and (receipt.get("heartbeat_host_requested") or {}).get("session") == host_b,
              "N5: the conflict receipt shows the explicit request that lost")
        check(not events_of_kind(sandbox.record_dir(host_a), "worker_event")
              and not events_of_kind(sandbox.record_dir(host_b), "worker_event"),
              "N5: neither Host holder received anything")

        # A dispatcher value that is not the holder's fact shape is not a
        # standalone start either.
        receipt = refused_start(sandbox, sandbox.session(), "heartbeat-host-unresolved",
                                "malformed", **{DISPATCHER_ENV: "not-json"})
        check("not valid JSON" in receipt.get("detail", ""), "malformed dispatcher is named")

        # N7: the dispatcher is this worker's own session: today's die, exit 2.
        own = sandbox.session()
        result, _ = sandbox.invoke(
            "start", "--mode", "yolo", session=own, scenario="basic",
            **{DISPATCHER_ENV: json.dumps(dict(dispatcher_a, session=own))})
        check(result.returncode == 2 and "own session" in (result.stderr or ""),
              f"N7: self-reference stays a usage error ({result.returncode})")
        check(not sandbox.record_dir(own).exists(), "N7: nothing created")

        # N2 / N8 second form: the dispatching Host holder is dead.
        record_path = sandbox.record_dir(host_a) / "record.json"
        kept = record_path.read_text(encoding="utf-8")
        stop = sandbox.cli("stop", "--force", session=host_a)
        check(stop.get("residual_pids") == [], "host A stops cleanly")
        if not record_path.exists():
            record_path.write_text(kept, encoding="utf-8")
        receipt = refused_start(
            sandbox, sandbox.session(), "heartbeat-host-unresolved", "N2",
            **{DISPATCHER_ENV: json.dumps(dispatcher_a)})
        check("not alive" in receipt.get("detail", ""),
              f"N2: detail names the dead holder ({receipt.get('detail')})")
        host_stop = sandbox.cli("stop", "--force", session=host_b)
        check(host_stop.get("residual_pids") == [], "host B stops cleanly")
    finally:
        sandbox.cleanup()


def test_issue_104_explicit_and_no_carrier_rows() -> None:
    """Design §e P4, P5, P7: the explicit variable equal to the dispatcher
    binds as before; an entry-less dispatcher (Issue #119: not merely non-ZCode;
    an emptied-entry fixture since Issue #126 admitted codex) refuses
    host-entry-unsupported (Issue #122 fail-closed); a
    reused live holder keeps its binding and exact stop/start binds."""
    sandbox = Sandbox("i104-rows")
    try:
        host = sandbox.session()
        sandbox.start(host, "basic")
        dispatcher = dispatcher_of(sandbox, host)

        # P4
        worker = sandbox.session()
        receipt = sandbox.cli(
            "start", "--mode", "yolo", session=worker, scenario="basic",
            **{DISPATCHER_ENV: json.dumps(dispatcher),
               HEARTBEAT_HOST_ENV: json.dumps({"platform": "zcode", "session": host,
                                               "repo": str(sandbox.repo)})})
        check(receipt.get("state") == "ready" and receipt.get("heartbeat_host_source") == "explicit"
              and receipt.get("heartbeat_host") == expected_fact(sandbox, host)
              and (receipt.get("dispatcher") or {}).get("session") == host,
              f"P4: explicit target equal to the dispatcher binds as explicit ({receipt.get('error')})")
        sandbox.cli("stop", session=worker)

        # P5 (Issue #122: fail-closed, no longer an unbound start)
        worker = sandbox.session()
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", session=worker, scenario="basic",
            cli_path=entryless_cli(sandbox, "zcode"),
            **{DISPATCHER_ENV: json.dumps(dict(dispatcher, platform="codex",
                                               session="codex-host"))})
        receipt = receipt or {}
        check(result.returncode == 1 and receipt.get("reason") == "host-entry-unsupported"
              and receipt.get("heartbeat_host_source") == "dispatcher-no-carrier"
              and receipt.get("mutation_performed") is False
              and (receipt.get("dispatcher") or {}).get("platform") == "codex"
              and not sandbox.record_dir(worker).exists(),
              f"P5: an entry-less dispatcher refuses before spawn ({receipt})")

        # P7: a worker started before the change (no dispatcher, unbound).
        worker = sandbox.session()
        first = sandbox.start(worker, "basic")
        check(first.get("heartbeat_host") is None and first.get("heartbeat_host_source") == "none",
              "P7: the pre-change worker is unbound")
        result, again = sandbox.invoke(
            "start", "--mode", "yolo", session=worker, scenario="basic",
            **{DISPATCHER_ENV: json.dumps(dispatcher)})
        check(result.returncode == 0 and (again.get("error") or {}).get("code") == "session-exists",
              f"P7: repeated start on the live holder is session-exists ({again})")
        check(again.get("heartbeat_host") is None and again.get("heartbeat_host_known") is True
              and again.get("heartbeat_host_source") == "dispatcher"
              and (again.get("dispatcher") or {}).get("session") == host,
              "P7: session-exists reports the reused null binding beside what a fresh start would do")
        stop = sandbox.cli("stop", session=worker)
        check(stop.get("stopped") is True, "P7: exact stop at idle")
        rebound = sandbox.cli("start", "--mode", "yolo", session=worker, scenario="basic",
                              **{DISPATCHER_ENV: json.dumps(dispatcher)})
        check(rebound.get("state") == "ready"
              and rebound.get("heartbeat_host_source") == "dispatcher"
              and rebound.get("heartbeat_host") == expected_fact(sandbox, host),
              f"P7: the new start binds by itself ({rebound.get('error')})")
        sandbox.cli("stop", session=worker)
        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stops cleanly")
    finally:
        sandbox.cleanup()


def host_settled(sandbox: Sandbox, host: str) -> None:
    """Every staged wake delivered and confirmed, and the Host turn ended, so
    the next dispatch prompt is admitted rather than colliding with a wake."""
    host_dir = sandbox.record_dir(host)

    def settled() -> bool:
        staged = {e["event"]["event_id"] for e in events_of_kind(host_dir, "worker_event")}
        confirmed: set[str] = set()
        for entry in events_of_kind(host_dir, "worker_event_confirmed"):
            confirmed.update(entry.get("event_ids") or [])
        if staged - confirmed:
            return False
        return sandbox.cli("status", session=host).get("turn_active") is False

    wait_until(settled, 30, f"host {host} settles its wakes")


def nested_receipts(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_issue_104_start_inside_host_agent_binds_mechanically() -> None:
    """Design §e P1, P2, P3, P8, P9 and the first form of N8, end to end: the
    Host holder names itself to its agent, the ZCode bridge forwards that fact
    (and still not the child-record handle), and a `start` the agent runs
    with NO variable binds the worker back to the Host; its idle and its
    permission wake both reach the Host. Unsetting the fact inside the agent
    is the documented residual (§d.2): unbound, not refused."""
    sandbox = Sandbox("i104-nested")
    try:
        host = sandbox.session()
        worker = f"claude-hb-{uuid.uuid4().hex[:8]}"
        worker_zc = sandbox.session()
        worker_unset = f"claude-hb-{uuid.uuid4().hex[:8]}"
        fake_agent = sandbox.dir / "fake-acp-agent.py"
        fake_agent.write_text(FAKE_ACP_AGENT, encoding="utf-8")
        fake_agent.chmod(fake_agent.stat().st_mode | 0o755)
        out = sandbox.dir / "nested.jsonl"
        permission_entry = sandbox.entry_for("permission", worker_zc)
        common = [str(CHECKOUT_CLI)]
        argvs = [
            # turn 1 (P1): a Claude Code ACP worker, no variable, no record root env
            [PYTHON, *common, "claude-code", "start", "--repo", str(sandbox.repo),
             "--session", worker, "--record-root", str(sandbox.record_root),
             "--command", f"{PYTHON} {fake_agent}"],
            # turn 2 (P3): a ZCode worker whose fake raises a permission
            ["env", f"KAOLA_ZCODE_ENTRY={permission_entry}", PYTHON, *common, "zcode", "start",
             "--repo", str(sandbox.repo), "--session", worker_zc, "--mode", "yolo",
             "--record-root", str(sandbox.record_root)],
            # turn 3 (N8 first form): the only mechanical source removed
            ["env", "-u", DISPATCHER_ENV, PYTHON, *common, "claude-code", "start", "--repo",
             str(sandbox.repo), "--session", worker_unset, "--record-root",
             str(sandbox.record_root), "--command", f"{PYTHON} {fake_agent}"],
        ]
        sandbox.entry_for("nested_start", host, entry_env={
            "FAKE_ZCODE_NESTED_ARGV": json.dumps(argvs), "FAKE_ZCODE_NESTED_OUT": str(out)})
        sandbox.start(host, "nested_start")
        sandbox.write_prompt_file("HEARTBEAT: issue 104 mechanical binding.")
        host_dir = sandbox.record_dir(host)
        record = host_record(sandbox, host)

        # P8/P9: the holder set the fact and the bridge forwarded it, not the handle.
        env_names = sandbox.fake(sandbox.records[host]).get("env_names") or []
        check(DISPATCHER_ENV in env_names and "KAOLA_ACP_CHILD_RECORD" not in env_names,
              f"P9: the bridge forwards the identity fact and drops the write handle ({env_names})")

        # P1: the Host agent runs the worker start itself.
        sandbox.sessions.append(("claude-code", worker))
        # Issue #105 acceptance: this is the worker's FIRST start, not a
        # restart - nothing of it exists yet - and it must bind by itself.
        check(not sandbox.record_dir(worker, platform="claude-code").exists(),
              "P1: the worker has no prior record, so this is its first start")
        turn = sandbox.cli("send", "--text", "NESTED:0 dispatch worker", session=host)
        check(turn.get("outcome") == "turn_completed", f"host turn 1 completes ({turn.get('outcome')})")
        entries = nested_receipts(out)
        check(len(entries) == 1 and entries[0].get("returncode") == 0,
              f"P1: nested start exited 0 ({entries and entries[0].get('stderr', '')[-400:]})")
        expected_dispatcher = {"holder_instance_id": record["holder_instance_id"],
                               "platform": "zcode", "repo": record["repo"], "session": host}
        check(entries[0].get("dispatcher") == json.dumps(expected_dispatcher, sort_keys=True),
              f"P8: the agent saw the holder's exact sort_keys identity fact ({entries[0].get('dispatcher')})")
        nested = json.loads(entries[0]["stdout"].strip().splitlines()[-1])
        check(nested.get("state") == "ready" and nested.get("error") is None,
              f"P1: worker started ready ({nested.get('error')})")
        check(nested.get("heartbeat_host") == expected_fact(sandbox, host)
              and nested.get("heartbeat_host_known") is True
              and nested.get("heartbeat_host_source") == "dispatcher"
              and (nested.get("dispatcher") or {}).get("session") == host,
              f"P1: worker bound to the Host mechanically ({nested.get('heartbeat_host')}, "
              f"source={nested.get('heartbeat_host_source')})")
        check(nested.get("heartbeat_host_requested") == expected_fact(sandbox, host),
              "P1: the derived request equals the adopted fact")
        worker_dir = sandbox.record_dir(worker, platform="claude-code")
        stored = json.loads((worker_dir / "record.json").read_text(encoding="utf-8"))
        check(stored.get("heartbeat_host") == expected_fact(sandbox, host),
              "P1: the worker record stores the same target")
        observed = sandbox.cli("observe", session=worker, platform="claude-code")
        check(observed.get("heartbeat_host") == expected_fact(sandbox, host),
              "P1: observe agrees")

        # P2: the worker's turn end wakes the Host with the ordinary idle.
        reply = sandbox.cli("send", "--text", "work", session=worker, platform="claude-code")
        check(reply.get("outcome") == "turn_completed", f"worker turn completes ({reply.get('outcome')})")
        wait_until(lambda: any(e["event"]["session"] == worker
                               for e in events_of_kind(host_dir, "worker_event")), 15,
                   "P2: the Host holder receives the worker idle")
        staged = [e["event"] for e in events_of_kind(host_dir, "worker_event")
                  if e["event"]["session"] == worker][0]
        check(staged["kind"] == "idle" and staged["platform"] == "claude-code"
              and staged["event_id"] == f"claude-code/{worker}/idle/{staged['event_cursor']}",
              f"P2: idle event id names the worker ({staged})")
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 15,
                   "P2: the Host delivers the wake")

        # P3: a ZCode worker started the same way raises a permission; the wake
        # reaches the Host and permit settles it.
        sandbox.sessions.append(("zcode", worker_zc))
        host_settled(sandbox, host)
        turn = sandbox.cli("send", "--text", "NESTED:1 dispatch zcode worker", session=host)
        check(turn.get("outcome") == "turn_completed", f"host turn 2 completes ({turn.get('outcome')})")
        entries = nested_receipts(out)
        check(len(entries) == 2 and entries[1].get("returncode") == 0,
              f"P3: nested zcode start exited 0 ({entries[1].get('stderr', '')[-400:]})")
        nested_zc = json.loads(entries[1]["stdout"].strip().splitlines()[-1])
        check(nested_zc.get("heartbeat_host_source") == "dispatcher"
              and nested_zc.get("heartbeat_host") == expected_fact(sandbox, host),
              "P3: the ZCode worker is bound mechanically too")
        send = sandbox.cli("send", "--no-wait", "--text", "do work", session=worker_zc)
        check(send.get("outcome") == "in_progress", "P3: worker prompt admitted")
        wait_until(lambda: (sandbox.cli("status", session=worker_zc).get("pending_permissions")
                            or []), 15, "P3: worker waits on a permission")
        request_id = sandbox.cli("status", session=worker_zc)["pending_permissions"][0]["request_id"]
        wait_until(lambda: any(e["event"]["kind"] == "permission_required"
                               and e["event"]["session"] == worker_zc
                               for e in events_of_kind(host_dir, "worker_event")), 15,
                   "P3: permission_required reaches the Host")
        wake = [e["event"] for e in events_of_kind(host_dir, "worker_event")
                if e["event"]["kind"] == "permission_required"][0]
        check(str(wake.get("request_id")) == str(request_id),
              f"P3: the wake carries the request id ({wake.get('request_id')})")
        permit = sandbox.cli("permit", "--option", "allow", session=worker_zc)
        check(permit.get("permitted") is not None, f"P3: permit settles ({permit.get('error')})")
        wait_until(lambda: any(e["event"]["kind"] == "idle" and e["event"]["session"] == worker_zc
                               for e in events_of_kind(host_dir, "worker_event")), 15,
                   "P3: the ordinary idle follows the permit")

        # N8 first form: inside the Host agent, the only mechanical source is
        # unset. This is the documented residual: unbound, not refused.
        sandbox.sessions.append(("claude-code", worker_unset))
        host_settled(sandbox, host)
        turn = sandbox.cli("send", "--text", "NESTED:2 dispatch without fact", session=host)
        check(turn.get("outcome") == "turn_completed", "host turn 3 completes")
        entries = nested_receipts(out)
        check(len(entries) == 3 and entries[2].get("returncode") == 0
              and entries[2].get("dispatcher") == json.dumps(expected_dispatcher, sort_keys=True),
              "N8: the agent still had the fact; only the nested command dropped it")
        unset = json.loads(entries[2]["stdout"].strip().splitlines()[-1])
        check(unset.get("state") == "ready" and unset.get("heartbeat_host") is None
              and unset.get("heartbeat_host_source") == "none" and unset.get("dispatcher") is None,
              f"N8: without the fact the start is a plain unbound start, not a refusal "
              f"({unset.get('heartbeat_host_source')})")

        for platform, name in (("claude-code", worker), ("claude-code", worker_unset),
                               ("zcode", worker_zc)):
            stop = sandbox.cli("stop", "--force", session=name, platform=platform)
            check(stop.get("residual_pids") == [], f"{name} stops cleanly")
        host_stop = sandbox.cli("stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "host stops cleanly")
    finally:
        sandbox.cleanup()


WORKER_SKILL_SCRIPTS = ("kaola-acp.py", "kaola-acp-holder.py", "kaola-tmux.sh")


def install_worker_skill(root: Path, name: str) -> Path:
    """A minimal installed worker Skill: what the Issue #105 comparison looks
    for is a Skill directory shipping ``scripts/kaola-acp.py``."""
    skill = root / name
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    for script in WORKER_SKILL_SCRIPTS:
        shutil.copy2(ROOT / "scripts" / script, skill / "scripts" / script)
    return skill


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def test_issue_105_worker_skill_build_skew_refuses_before_spawn() -> None:
    """Issue #105: a ZCode Host `start` run from an installed Skill tree refuses
    before anything exists when the worker Skills its agent would load are a
    different build, because those copies are what carry the Issue #104
    binding. Aligned copies start normally and report what was compared; an
    empty root is not skew; and a checkout invocation answers `null` (unknown,
    never "aligned") because it has no Skill build to be the baseline."""
    sandbox = Sandbox("i105-skew")
    try:
        host_tree = sandbox.dir / "installed" / "zcode-kaola-project-runner"
        shutil.copytree(ROOT / "skills" / "zcode-kaola-project-runner", host_tree)
        host_cli = host_tree / "scripts" / "kaola-acp.py"
        build = sha12(ROOT / "scripts" / "kaola-acp.py")
        check(sha12(host_cli) == build,
              "the rendered ZCode Skill ships this checkout's kaola-acp.py verbatim")

        roots = sandbox.home / ".zcode" / "skills"
        stale = install_worker_skill(roots, "claude-code-kaola-project-runner")
        install_worker_skill(roots, "codex-kaola-project-runner")
        stale_script = stale / "scripts" / "kaola-acp.py"
        aligned_bytes = stale_script.read_bytes()
        stale_script.write_bytes(aligned_bytes + b"\n# an older build\n")

        # 1. Skew refuses, exit 1, and opens nothing.
        refused_session = sandbox.session()
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", session=refused_session, scenario="basic",
            cli_path=host_cli)
        check(result.returncode == 1, f"skew start exits 1 ({result.returncode})")
        check(isinstance(receipt, dict) and receipt.get("result") == "refused"
              and receipt.get("reason") == "worker-skill-build-skew"
              and receipt.get("mutation_performed") is False,
              f"skew is a typed refusal ({receipt})")
        check(receipt.get("worker_skill_build") == build
              and receipt.get("worker_skill_skew_count") == 1,
              f"the refusal names this build and one skewed file ({receipt.get('worker_skill_build')}, "
              f"{receipt.get('worker_skill_skew_count')})")
        entry = (receipt.get("worker_skill_skew") or [{}])[0]
        check(entry.get("path") == str(stale_script) and entry.get("file") == "kaola-acp.py"
              and entry.get("expected") == build and entry.get("installed") != build,
              f"the skewed copy is named with both digests ({entry})")
        record_dir = sandbox.record_dir(refused_session)
        check(not record_dir.exists() and not holder_socket(record_dir).exists(),
              "the refused start created no record directory and no holder socket")
        check(subprocess.run(["tmux", "has-session", "-t", f"={refused_session}"],
                             capture_output=True).returncode != 0,
              "the refused start created no tmux session")

        # 2. The same command with the copy restored starts and reports what it
        #    compared, so `status` reconciliation has the fact.
        stale_script.write_bytes(aligned_bytes)
        aligned_session = sandbox.session()
        receipt = sandbox.cli("start", "--mode", "yolo", session=aligned_session,
                              scenario="basic", cli_path=host_cli)
        check(receipt.get("error") is None and receipt.get("state") == "ready",
              f"the aligned start reaches ready ({receipt.get('error')})")
        check(receipt.get("worker_skill_build") == build
              and receipt.get("worker_skill_roots") == [
                  {"root": str(roots),
                   "skills": ["claude-code-kaola-project-runner",
                              "codex-kaola-project-runner"]}],
              f"the start reports the build and the roots it compared "
              f"({receipt.get('worker_skill_roots')})")
        stop = sandbox.cli("stop", "--force", session=aligned_session, cli_path=host_cli)
        check(stop.get("residual_pids") == [], "the aligned host stops cleanly")

        # 3. A discovery root with no worker Skill in it is not skew.
        shutil.rmtree(stale)
        shutil.rmtree(roots / "codex-kaola-project-runner")
        empty_session = sandbox.session()
        receipt = sandbox.cli("start", "--mode", "yolo", session=empty_session,
                              scenario="basic", cli_path=host_cli)
        check(receipt.get("state") == "ready" and receipt.get("worker_skill_roots") == []
              and receipt.get("worker_skill_build") == build,
              f"no installed worker Skill is not skew ({receipt.get('worker_skill_roots')})")
        stop = sandbox.cli("stop", "--force", session=empty_session, cli_path=host_cli)
        check(stop.get("residual_pids") == [], "the empty-root host stops cleanly")

        # 4. A checkout invocation has no Skill build to compare: unknown.
        install_worker_skill(roots, "claude-code-kaola-project-runner")
        checkout_session = sandbox.session()
        receipt = sandbox.cli("start", "--mode", "yolo", session=checkout_session,
                              scenario="basic")
        check(receipt.get("state") == "ready"
              and receipt.get("worker_skill_build") is None
              and receipt.get("worker_skill_roots") is None,
              f"a checkout start answers unknown, not aligned "
              f"({receipt.get('worker_skill_build')})")
        stop = sandbox.cli("stop", "--force", session=checkout_session)
        check(stop.get("residual_pids") == [], "the checkout host stops cleanly")
    finally:
        sandbox.cleanup()


def test_issue_106_unreadable_discovery_root_is_a_typed_refusal() -> None:
    """Issue #106: an existing default ZCode discovery root that cannot be
    listed makes the Issue #105 comparison impossible, so a Host `start` refuses
    it by name with nothing created - never a raw traceback. The refusal is the
    Issue #105 shape: ``result: refused``, exit 1, ``mutation_performed: false``
    and the unreadable root in both the detail and a dedicated field."""
    sandbox = Sandbox("i106-unreadable")
    blocked = sandbox.home / ".agents" / "skills"
    try:
        host_tree = sandbox.dir / "installed" / "zcode-kaola-project-runner"
        shutil.copytree(ROOT / "skills" / "zcode-kaola-project-runner", host_tree)
        host_cli = host_tree / "scripts" / "kaola-acp.py"
        blocked.mkdir(parents=True)
        (blocked / "some-worker").mkdir()
        os.chmod(blocked, 0o000)
        if os.geteuid() == 0:
            # root ignores the mode bits, so there is nothing to prove here.
            check(True, "running as root; chmod-000 unreadable-root probe skipped")
            return
        session = sandbox.session()
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", session=session, scenario="basic",
            cli_path=host_cli)
        check("Traceback" not in (result.stderr or ""),
              f"the unreadable root is not a traceback ({(result.stderr or '')[-300:]})")
        check(result.returncode == 1, f"unreadable-root start exits 1 ({result.returncode})")
        check(isinstance(receipt, dict) and receipt.get("result") == "refused"
              and receipt.get("reason") == "worker-skill-root-unreadable"
              and receipt.get("mutation_performed") is False
              and receipt.get("mutation_status") == "not_started",
              f"the unreadable root is a typed refusal ({receipt})")
        check(receipt.get("worker_skill_unreadable_roots") == [str(blocked)],
              f"the refusal names the unreadable root "
              f"({receipt.get('worker_skill_unreadable_roots')})")
        check(str(blocked) in (receipt.get("detail") or ""),
              f"the refusal detail names the unreadable root ({receipt.get('detail')})")
        record_dir = sandbox.record_dir(session)
        check(not record_dir.exists() and not holder_socket(record_dir).exists(),
              "the refused start created no record directory and no holder socket")
        check(subprocess.run(["tmux", "has-session", "-t", f"={session}"],
                             capture_output=True).returncode != 0,
              "the refused start created no tmux session")
    finally:
        if blocked.is_dir():
            os.chmod(blocked, 0o755)
        sandbox.cleanup()


def host_session_name(suffix: str) -> str:
    """The documented Host session name shape the Issue #108 pin keys on."""
    return f"zcode-KPR-orchestrator-{suffix}"


def record_config_current(record_dir: Path, option_id: str) -> object:
    """The holder-recorded currentValue for one advertised config option."""
    record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))
    options = ((record.get("session_meta") or {}).get("configOptions")) or []
    for option in options:
        if isinstance(option, dict) and option.get("id") == option_id:
            return option.get("currentValue")
    return None


def test_issue_108_host_requires_glm53_max() -> None:
    """Issue #108: a Host-shaped ZCode start must run GLM 5.3 at effort max.

    An explicit contradicting --model/--effort is a typed pre-mutation
    refusal that creates nothing; an absent one is pinned and then verified
    against the holder's own advertised config state; a session that cannot
    prove the required selection is stopped and refused; and an ordinary
    worker name is never pinned.
    """
    sandbox = Sandbox("i108-host-model")
    try:
        host = host_session_name("main")

        # 1. An explicit wrong model is refused before anything exists.
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", "--model", "GLM-5.3-Flash",
            session=host, scenario="basic")
        check("Traceback" not in (result.stderr or ""),
              f"the model mismatch is not a traceback ({(result.stderr or '')[-300:]})")
        check(result.returncode == 1, f"the model mismatch exits 1 ({result.returncode})")
        check(isinstance(receipt, dict) and receipt.get("result") == "refused"
              and receipt.get("reason") == "host-model-mismatch"
              and receipt.get("mutation_performed") is False
              and receipt.get("mutation_status") == "not_started",
              f"the model mismatch is a typed refusal ({receipt})")
        fact = receipt.get("host_selection") or {}
        check(fact.get("required_model") == "GLM-5.3"
              and fact.get("required_effort") == "max"
              and fact.get("requested_model") == "GLM-5.3-Flash",
              f"the refusal names required and requested values ({fact})")
        record_dir = sandbox.record_dir(host)
        check(not record_dir.exists() and not holder_socket(record_dir).exists(),
              "the refused start created no record directory and no holder socket")
        check(subprocess.run(["tmux", "has-session", "-t", f"={host}"],
                             capture_output=True).returncode != 0,
              "the refused start created no tmux session")

        # 2. An explicit wrong effort — and a qualified wrong model — refuse
        #    the same way.
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", "--effort", "high",
            session=host, scenario="basic")
        check(result.returncode == 1 and receipt.get("reason") == "host-model-mismatch",
              f"the effort mismatch is refused ({receipt and receipt.get('reason')})")
        check(not sandbox.record_dir(host).exists(),
              "the effort refusal still created no record directory")
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", "--model",
            "account:bigmodel-individual-coding-plan\\GLM-5.3-Flash",
            session=host, scenario="basic")
        check(result.returncode == 1 and receipt.get("reason") == "host-model-mismatch",
              f"a provider-qualified non-GLM-5.3 model is refused "
              f"({receipt and receipt.get('reason')})")
        check(not sandbox.record_dir(host).exists(),
              "the qualified-model refusal still created no record directory")

        # 3. An absent selection is corrected: the pin lands GLM 5.3 + max and
        #    the receipt proves it from the holder's advertised state.
        receipt = sandbox.cli("start", "--mode", "yolo", session=host, scenario="basic")
        check(receipt.get("error") is None and receipt.get("state") == "ready",
              f"the pinned Host start reaches ready ({receipt.get('error')})")
        fact = receipt.get("host_selection") or {}
        check(fact.get("verified") is True
              and fact.get("required_model") == "GLM-5.3"
              and fact.get("required_effort") == "max"
              and fact.get("requested_model") is None
              and fact.get("requested_effort") is None
              and fact.get("applied_model") == "GLM-5.3"
              and fact.get("applied_effort") == "max"
              and fact.get("effective_effort") == "max"
              and str(fact.get("effective_model") or "").endswith("\\GLM-5.3"),
              f"the start receipt proves the enforced selection ({fact})")
        application = receipt.get("config_application") or {}
        check(application.get("model", {}).get("applied") is True
              and application["model"].get("value") == "GLM-5.3"
              and application.get("effort", {}).get("applied") is True
              and application["effort"].get("value") == "max",
              f"the config application shows the pin was sent ({application})")
        check(record_config_current(sandbox.record_dir(host), "thoughtLevel") == "max",
              "the holder record proves effective effort max")
        stop = sandbox.cli("stop", "--force", session=host)
        check(stop.get("residual_pids") == [], "the pinned host stops cleanly")

        # 4. The correct explicit selection passes with the same evidence.
        host_ok = host_session_name("explicit")
        receipt = sandbox.cli(
            "start", "--mode", "yolo", "--model", "GLM-5.3", "--effort", "max",
            session=host_ok, scenario="basic")
        fact = receipt.get("host_selection") or {}
        check(receipt.get("state") == "ready" and fact.get("verified") is True
              and fact.get("requested_model") == "GLM-5.3"
              and fact.get("requested_effort") == "max",
              f"an explicit GLM-5.3 + max start is verified ({fact})")
        stop = sandbox.cli("stop", "--force", session=host_ok)
        check(stop.get("residual_pids") == [], "the explicit host stops cleanly")

        # 5. A resumed Host keeps its transcript but the pin still lands.
        host_resume = host_session_name("resume")
        receipt = sandbox.cli(
            "start", "--mode", "yolo", "--resume", "sess_i108persisted",
            session=host_resume, scenario="basic")
        fact = receipt.get("host_selection") or {}
        check(receipt.get("state") == "ready" and fact.get("verified") is True
              and fact.get("effective_effort") == "max"
              and str(fact.get("effective_model") or "").endswith("\\GLM-5.3"),
              f"a resumed Host is corrected to GLM-5.3 + max ({fact})")
        stop = sandbox.cli("stop", "--force", session=host_resume)
        check(stop.get("residual_pids") == [], "the resumed host stops cleanly")

        # 6. A plan that does not offer GLM 5.3 cannot satisfy the pin: the
        #    just-created session is stopped and the start is refused.
        config_path = sandbox.home / ".zcode" / "v2" / "config.json"
        desktop = json.loads(config_path.read_text(encoding="utf-8"))
        del desktop["provider"]["builtin:bigmodel-coding-plan"]["models"]["GLM-5.3"]
        config_path.write_text(json.dumps(desktop), encoding="utf-8")
        host_plan = host_session_name("noglm")
        result, receipt = sandbox.invoke(
            "start", "--mode", "yolo", session=host_plan, scenario="basic")
        check(result.returncode == 1, f"an unverifiable Host exits 1 ({result.returncode})")
        check(isinstance(receipt, dict) and receipt.get("result") == "refused"
              and receipt.get("reason") == "host-model-unverified"
              and receipt.get("host_session_stopped") is True
              and receipt.get("holder_alive") is False
              and receipt.get("residual_pids") == []
              and receipt.get("mutation_performed") is False,
              f"an unprovable pin refuses with the session stopped ({receipt})")
        fact = receipt.get("host_selection") or {}
        check(fact.get("verified") is False
              and str(fact.get("effective_model") or "").endswith("\\GLM-5.3-Flash"),
              f"the refusal names the effective wrong selection ({fact})")
        stopped = json.loads(
            (sandbox.record_dir(host_plan) / "record.json").read_text(encoding="utf-8"))
        check(stopped.get("state") == "stopped" and not pid_alive(stopped.get("holder_pid")),
              "the refused Host left only a stopped record")
    finally:
        sandbox.cleanup()


def test_issue_108_worker_names_are_never_pinned() -> None:
    """Issue #108 boundary: the *Host gate* is scoped to the standard Host
    name, and an issue-worker name that merely contains "orchestrator" in its
    purpose is still a worker.

    Issue #111 changed what a worker lands on but not this boundary. The
    ordinary ZCode preset now declares GLM 5.3 at thought=max, so a worker does
    reach the same pair -- through `runner-default` preset resolution, which any
    caller can override with `--model`/`--effort`. What must stay absent is the
    Host machinery: no `host_selection` fact, and therefore no refusal and no
    stop-on-unverified. The softer default underneath the hard gate, exactly as
    the issue describes; the two agreeing is asserted in
    tests/contract/test-issue-111-model-tiers.py.
    """
    sandbox = Sandbox("i108-worker")
    try:
        worker = sandbox.session()
        receipt = sandbox.cli("start", "--mode", "yolo", session=worker, scenario="basic")
        check(receipt.get("state") == "ready" and "host_selection" not in receipt,
              f"a worker start carries no Host selection pin ({receipt.get('host_selection')})")
        selection = receipt.get("model_selection") or {}
        check(selection.get("source") == "runner-default" and selection.get("tier") == "default",
              f"the worker's selection is the ordinary preset ({selection})")
        application = receipt.get("config_application") or {}
        effort = application.get("effort") or {}
        check(effort.get("applied") is True and effort.get("value") == "max",
              f"the preset effort reached the worker ({effort})")
        check(record_config_current(sandbox.record_dir(worker), "thoughtLevel") == "max",
              "the worker runs the preset thought level")
        stop = sandbox.cli("stop", "--force", session=worker)
        check(stop.get("residual_pids") == [], "the worker stops cleanly")

        workerish = "zcode-KPR-i42-orchestrator-fix"
        receipt = sandbox.cli("start", "--mode", "yolo", session=workerish, scenario="basic")
        check(receipt.get("state") == "ready" and "host_selection" not in receipt,
              f"the -i<issue>- marker keeps the name a worker ({receipt.get('host_selection')})")
        check(record_config_current(sandbox.record_dir(workerish), "thoughtLevel") == "max",
              "the issue-worker takes the preset, not the Host pin")
        stop = sandbox.cli("stop", "--force", session=workerish)
        check(stop.get("residual_pids") == [], "the issue-worker stops cleanly")

        # A worker is still free to choose otherwise; the Host is not.
        explicit = sandbox.session()
        receipt = sandbox.cli("start", "--mode", "yolo", "--effort", "high",
                              session=explicit, scenario="basic")
        check("host_selection" not in receipt and receipt.get("result") != "refused",
              f"an explicit worker effort is not refused ({receipt.get('reason')})")
        check(record_config_current(sandbox.record_dir(explicit), "thoughtLevel") == "high",
              "an explicit worker effort still wins over the preset")
        stop = sandbox.cli("stop", "--force", session=explicit)
        check(stop.get("residual_pids") == [], "the explicit worker stops cleanly")
    finally:
        sandbox.cleanup()


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
