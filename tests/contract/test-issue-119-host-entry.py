#!/usr/bin/env python3
"""Issue #119: non-ZCode ACP runtimes as Hosts - contract.

Offline and deterministic: real holder processes and the real Runner CLI
against a small fake ACP agent (no real CLI, login, or network). Covers:

* AC1 - the carrier's first line is the Host platform's measured
  ``host_skill_entry`` and its second line names ``(<runtime_name> Host)``;
  the ZCode carrier is byte-identical to main 5122468 (fixed digest).
* AC2 - a worker dispatched by a non-ZCode Host binds to it and its idle
  event reaches that Host as a carrier prompt; an entry-less dispatcher
  (codex today) still starts unbound without refusal.
* AC3 (H1) - no Host-only model table: a Host-named start resolves exactly
  what a worker-named start on the same platform resolves.
* AC9 - #73 canonical root, #104's three refusals, and #105 build skew apply
  to a non-ZCode Host too.
* H2 - an explicit OpenCode --model/--effort the agent does not report is a
  typed refusal with the session stopped; nothing is substituted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "kaola-acp.py"
TMUX = ROOT / "scripts" / "kaola-tmux.sh"
PYTHON = sys.executable
DISPATCHER_ENV = "KAOLA_ACP_DISPATCHER"
HEARTBEAT_HOST_ENV = "KAOLA_ACP_HEARTBEAT_HOST"
PLATFORMS = ("claude-code", "codex", "cursor-cli", "devin", "droid", "dsh", "grok",
             "kimi-cli", "opencode", "zcode")
# sha256 of the ZCode carrier the main 5122468 holder builds for
# ZCODE_SNAPSHOT_EVENTS at repo /nonexistent-119 with no heartbeat prompt file.
ZCODE_CARRIER_SHA256 = "8e8294760493aa6e8f62505792d553e5e5d086c73e64133816fe8bdd3f5ebd98"
ZCODE_SNAPSHOT_EVENTS = [
    {"event_id": "e1", "kind": "idle", "platform": "claude-code",
     "session": "claude-code-KPR-i119-w", "repo": "/nonexistent-119",
     "reason": "turn_completed", "event_cursor": 7},
]

FAKE_AGENT = r'''#!/usr/bin/env python3
import json, os, sys
LOG = os.environ.get("FAKE119_LOG", "")
IGNORE = os.environ.get("FAKE119_IGNORE_MODEL") == "1"
state = {"model": "native/opening", "effort": "default"}
def options():
    return [{"id": "model", "name": "Model", "category": "model", "type": "select",
             "currentValue": state["model"], "options": []},
            {"id": "effort", "name": "Effort", "category": "thought_level", "type": "select",
             "currentValue": state["effort"], "options": []}]
def send(m):
    sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()
for raw in sys.stdin.buffer:
    line = raw.decode("utf-8", "replace").strip()
    if not line:
        continue
    msg = json.loads(line)
    rid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": 1,
              "agentCapabilities": {}, "authMethods": [], "agentInfo": {"name": "fake119"}}})
    elif method == "session/new":
        send({"jsonrpc": "2.0", "id": rid, "result": {"sessionId": "fake119-s",
              "configOptions": options()}})
    elif method == "session/set_config_option":
        key = {"model": "model", "effort": "effort"}.get(params.get("configId"))
        if key and not (IGNORE and key == "model"):
            state[key] = params.get("value")
        send({"jsonrpc": "2.0", "id": rid, "result": {"configOptions": options()}})
    elif method == "session/prompt":
        text = "".join(b.get("text", "") for b in params.get("prompt") or [])
        if LOG:
            with open(LOG, "a", encoding="utf-8") as h:
                h.write(json.dumps({"prompt": text}) + "\n")
        send({"jsonrpc": "2.0", "method": "session/update", "params": {
              "sessionId": "fake119-s", "update": {"sessionUpdate": "agent_message_chunk",
              "content": {"type": "text", "text": "ok"}}}})
        send({"jsonrpc": "2.0", "id": rid, "result": {"stopReason": "end_turn"}})
    elif method == "session/close":
        send({"jsonrpc": "2.0", "id": rid, "result": {}})
    elif rid is not None:
        send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601,
              "message": "unsupported: " + str(method)}})
'''

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def manifest(platform: str) -> dict[str, str]:
    result = {}
    for raw in (ROOT / "platforms" / f"{platform}.yaml").read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.startswith("#"):
            key, _, value = raw.partition(":")
            result[key.strip()] = json.loads(value.strip())
    return result


def pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


class Sandbox:
    def __init__(self, label: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kpr119-{label}-"))
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c",
                        "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"], check=True)
        self.home = self.dir / "home"
        self.home.mkdir()
        self.record_root = self.dir / "records"
        self.agent = self.dir / "fake119.py"
        self.agent.write_text(FAKE_AGENT, encoding="utf-8")
        self.agent.chmod(0o755)
        self.started: list[tuple[str, str, Path]] = []
        # tmux only: the real platform CLIs stay off PATH so nothing probes them.
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        tmux = shutil.which("tmux")
        if tmux:
            (self.bin / "tmux").symlink_to(tmux)

    def env(self, **overrides: str | None) -> dict[str, str]:
        base = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home), "LANG": "C",
                "TMPDIR": tempfile.gettempdir(), "PYTHONUNBUFFERED": "1",
                "KAOLA_ACP_RECORD_ROOT": str(self.record_root)}
        for key, value in overrides.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        return base

    def invoke(self, platform: str, command: str, *args: str, session: str,
               cli: Path = CLI, **env: str | None):
        argv = [PYTHON, str(cli), platform, command, "--repo", str(self.repo),
                "--session", session, *args]
        if command == "start":
            argv += ["--command", f"{PYTHON} {self.agent}"]
            self.started.append((platform, session, cli))
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(**env), timeout=120)
        payload = None
        lines = (result.stdout or "").strip().splitlines()
        if lines:
            try:
                payload = json.loads(lines[-1])
            except ValueError:
                payload = None
        return result, payload

    def cli(self, platform: str, command: str, *args: str, session: str, **env):
        result, payload = self.invoke(platform, command, *args, session=session, **env)
        if not isinstance(payload, dict):
            raise AssertionError(f"{command} printed no receipt: {result.stderr[-600:]}")
        return payload

    def record_dir(self, platform: str, session: str) -> Path:
        digest = hashlib.sha256(os.path.realpath(self.repo).encode()).hexdigest()[:16]
        return self.record_root / platform / session / digest

    def record(self, platform: str, session: str) -> dict:
        return json.loads((self.record_dir(platform, session) / "record.json").read_text())

    def dispatcher(self, platform: str, session: str) -> dict:
        record = self.record(platform, session)
        return {"holder_instance_id": record["holder_instance_id"], "platform": platform,
                "repo": record["repo"], "session": session}

    def cleanup(self) -> None:
        for platform, session, cli in self.started:
            try:
                self.invoke(platform, "stop", "--force", session=session, cli=cli)
            except Exception:
                pass
        shutil.rmtree(self.dir, ignore_errors=True)


def bare_holder(module, platform: str, entry: str | None, name: str | None):
    holder = object.__new__(module.Holder)
    holder.args = type("Args", (), {"platform": platform, "repo": "/nonexistent-119",
                                    "session": "host", "host_entry": entry,
                                    "host_name": name})()
    # The constructor's own derivation, without an agent process.
    derived = entry if entry is not None else (
        module.HOST_SKILL_ENTRY if platform == "zcode" else "")
    holder.host_entry = derived
    holder.host_name = name or ("ZCode" if platform == "zcode" else platform)
    return holder


def test_manifest_entries_are_the_code_table() -> None:
    acp = load(CLI, "kaola_acp_119")
    for platform in PLATFORMS:
        declared = manifest(platform)["host_skill_entry"]
        check(acp.HOST_SKILL_ENTRIES[platform] == declared,
              f"{platform}: HOST_SKILL_ENTRIES equals the manifest host_skill_entry")
        check(platform in acp.HOST_SKILL_DISCOVERY_DIRS,
              f"{platform}: measured Skill discovery roots are declared")
    check(set(acp.HOST_SKILL_ENTRIES) == set(PLATFORMS) == set(acp.PLATFORMS),
          "the entry table covers exactly the ten platforms")
    check(acp.HOST_SKILL_ENTRIES["zcode"] == "/kaola-project-runner",
          "ZCode keeps /kaola-project-runner")
    check(acp.HOST_SKILL_ENTRIES["kimi-cli"] == "/skill:kaola-project-runner ",
          "kimi-cli's measured entry keeps its trailing space (the command ends at a space)")
    check(acp.HOST_SKILL_ENTRIES["codex"] == "",
          "codex has no entry until a turn-level trigger is measured")
    matrix = (ROOT / "templates" / "orchestrator" / "references" /
              "host-entry-matrix.md").read_text(encoding="utf-8")
    for platform in PLATFORMS:
        check(f"| {platform} |" in matrix, f"{platform} has a host-entry-matrix row")


def test_zcode_carrier_is_byte_identical() -> None:
    holder_module = load(ROOT / "scripts" / "kaola-acp-holder.py", "holder_119_zc")
    for entry, name in ((None, None), ("/kaola-project-runner", "ZCode")):
        holder = bare_holder(holder_module, "zcode", entry, name)
        text, _meta = holder._heartbeat_payload(ZCODE_SNAPSHOT_EVENTS)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        check(digest == ZCODE_CARRIER_SHA256,
              f"ZCode carrier is byte-identical to 5122468 (entry={entry!r}, {digest})")


def test_carrier_first_lines_per_platform() -> None:
    holder_module = load(ROOT / "scripts" / "kaola-acp-holder.py", "holder_119_pp")
    for platform in PLATFORMS:
        facts = manifest(platform)
        entry = facts["host_skill_entry"]
        if not entry:
            continue
        holder = bare_holder(holder_module, platform, entry, facts["runtime_name"])
        text, _meta = holder._heartbeat_payload(ZCODE_SNAPSHOT_EVENTS)
        lines = text.split("\n")
        check(lines[0] == entry, f"{platform}: carrier line 1 is its host_skill_entry")
        check(f"({facts['runtime_name']} Host)" in lines[1],
              f"{platform}: carrier line 2 names ({facts['runtime_name']} Host)")
        if platform != "zcode":
            check("ZCode" not in text, f"{platform}: its carrier never says ZCode")


def wait_for(predicate, timeout: float, label: str):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError(f"timed out: {label}")


def test_non_zcode_host_binds_and_receives_carrier() -> None:
    sandbox = Sandbox("carrier")
    try:
        log = sandbox.dir / "host-prompts.jsonl"
        host = "cursor-cli-KPR-orchestrator-t119"
        started = sandbox.cli("cursor-cli", "start", session=host, FAKE119_LOG=str(log))
        check(started.get("state") == "ready", f"cursor-cli Host starts ({started.get('error')})")
        check(sandbox.record("cursor-cli", host).get("host_skill_entry") == "/kaola-project-runner",
              "the Host holder records its manifest entry")
        dispatcher = sandbox.dispatcher("cursor-cli", host)
        worker = "claude-code-KPR-i119-worker"
        receipt = sandbox.cli("claude-code", "start", session=worker,
                              **{DISPATCHER_ENV: json.dumps(dispatcher)})
        fact = receipt.get("heartbeat_host") or {}
        check(receipt.get("state") == "ready" and receipt.get("heartbeat_host_source") == "dispatcher"
              and fact.get("platform") == "cursor-cli" and fact.get("session") == host
              and receipt.get("heartbeat_host_known") is True,
              f"AC2: the worker binds to the non-ZCode Host ({receipt.get('heartbeat_host_source')}, {fact})")
        sent = sandbox.cli("claude-code", "send", "--text", "work", session=worker)
        check(sent.get("error") is None, f"worker turn runs ({sent.get('error')})")
        prompts = wait_for(lambda: [json.loads(line)["prompt"] for line in
                                    (log.read_text().splitlines() if log.exists() else [])],
                           30, "carrier prompt reaches the Host agent")
        lines = prompts[-1].split("\n")
        check(lines[0] == "/kaola-project-runner", f"AC1: live carrier line 1 is the entry ({lines[0]!r})")
        check("(Cursor CLI Host)" in lines[1], f"AC1: live carrier line 2 names the Host ({lines[1]!r})")
        check(f'"session": "{worker}"' in prompts[-1], "the carrier names the worker")
        events = wait_for(lambda: [e for e in (sandbox.cli("cursor-cli", "capture", "--lines", "500",
                                                           session=host).get("events") or [])
                                   if e.get("kind") == "worker_event_confirmed"],
                          30, "Host confirms the delivered carrier")
        check(bool(events), "Host event log confirms the carrier turn")
        stop = sandbox.cli("claude-code", "stop", session=worker)
        check(stop.get("stopped") is True, "exact worker stop")
        status = sandbox.cli("cursor-cli", "status", session=host)
        check(status.get("agent_alive") is True, "the Host stays live after the worker stop")
        host_stop = sandbox.cli("cursor-cli", "stop", "--force", session=host)
        check(host_stop.get("residual_pids") == [], "Host stop leaves no residue")
    finally:
        sandbox.cleanup()


def test_entryless_dispatcher_and_non_zcode_refusals() -> None:
    """AC2 (entry-less row) and AC9 (#104 refusals on a non-ZCode Host)."""
    sandbox = Sandbox("refusals")
    try:
        host = "grok-KPR-orchestrator-t119"
        check(sandbox.cli("grok", "start", session=host).get("state") == "ready", "grok Host starts")
        dispatcher = sandbox.dispatcher("grok", host)

        worker = "claude-code-KPR-i119-nocarrier"
        receipt = sandbox.cli("claude-code", "start", session=worker,
                              **{DISPATCHER_ENV: json.dumps(dict(dispatcher, platform="codex",
                                                                 session="codex-KPR-orchestrator-x"))})
        check(receipt.get("state") == "ready"
              and receipt.get("heartbeat_host_source") == "dispatcher-no-carrier"
              and receipt.get("heartbeat_host") is None,
              "an entry-less (codex) dispatcher still starts unbound, not refused")
        sandbox.cli("claude-code", "stop", session=worker)

        # #104 refusal 1: a non-ZCode dispatcher whose holder is not the live one.
        result, refused = sandbox.invoke(
            "claude-code", "start", session="claude-code-KPR-i119-stale",
            **{DISPATCHER_ENV: json.dumps(dict(dispatcher, holder_instance_id="0" * 32))})
        check(result.returncode == 1 and (refused or {}).get("reason") == "heartbeat-host-unresolved"
              and refused.get("mutation_performed") is False,
              f"AC9 #104: stale non-ZCode dispatcher refuses ({refused})")
        # #104 refusal 2: explicit target that is not the dispatching Host.
        other = {"platform": "grok", "session": "grok-KPR-orchestrator-other",
                 "repo": str(sandbox.repo)}
        result, refused = sandbox.invoke(
            "claude-code", "start", session="claude-code-KPR-i119-conflict",
            **{DISPATCHER_ENV: json.dumps(dispatcher), HEARTBEAT_HOST_ENV: json.dumps(other)})
        check(result.returncode == 1 and (refused or {}).get("reason") == "heartbeat-host-conflict",
              f"AC9 #104: explicit target conflicting with a non-ZCode dispatcher refuses ({refused})")
        # #104 refusal 3: PTY under a non-ZCode Host.
        pty = subprocess.run(
            ["bash", str(TMUX), "claude-code", "start", "--repo", str(sandbox.repo),
             "--session", "claude-code-KPR-i119-pty", "--transport", "pty"],
            capture_output=True, text=True, timeout=60,
            env=sandbox.env(**{DISPATCHER_ENV: json.dumps(dispatcher)}))
        pty_receipt = json.loads(pty.stdout.strip().splitlines()[-1]) if pty.stdout.strip() else {}
        check(pty.returncode == 1 and pty_receipt.get("reason") == "heartbeat-host-pty-unsupported",
              f"AC9 #104: PTY under a non-ZCode Host refuses ({pty_receipt})")
        # #73: a non-ZCode Host start outside the canonical root refuses.
        elsewhere = sandbox.dir / "other"
        elsewhere.mkdir()
        subprocess.run(["git", "init", "-q", str(elsewhere)], check=True)
        canon = subprocess.run(
            ["bash", str(TMUX), "grok", "start", "--repo", str(sandbox.repo),
             "--session", "grok-KPR-orchestrator-t119b"],
            capture_output=True, text=True, timeout=60,
            env=sandbox.env(KAOLA_PROJECT_RUNNER_CANONICAL_REPO=os.path.realpath(elsewhere)))
        canon_receipt = json.loads(canon.stdout.strip().splitlines()[-1]) if canon.stdout.strip() else {}
        check(canon.returncode != 0 and str(canon_receipt.get("reason", "")).startswith("canonical-root"),
              f"AC9 #73: a non-ZCode Host outside the canonical root refuses ({canon_receipt})")
        sandbox.cli("grok", "stop", "--force", session=host)
    finally:
        sandbox.cleanup()


def test_non_zcode_host_build_skew_refuses() -> None:
    """AC9 #105: a Host-named start on a Host-capable platform, run from an
    installed Skill tree, compares that platform's measured discovery roots."""
    sandbox = Sandbox("skew")
    try:
        tree = sandbox.dir / "installed" / "droid-kaola-project-runner"
        shutil.copytree(ROOT / "skills" / "droid-kaola-project-runner", tree)
        cli = tree / "scripts" / "kaola-acp.py"
        stale = sandbox.home / ".factory" / "skills" / "claude-code-kaola-project-runner"
        (stale / "scripts").mkdir(parents=True)
        for name in ("kaola-acp.py", "kaola-acp-holder.py", "kaola-tmux.sh"):
            shutil.copy2(ROOT / "scripts" / name, stale / "scripts" / name)
        (stale / "scripts" / "kaola-acp.py").write_bytes(
            (ROOT / "scripts" / "kaola-acp.py").read_bytes() + b"\n# older\n")
        host = "droid-KPR-orchestrator-t119"
        result, refused = sandbox.invoke("droid", "start", session=host, cli=cli)
        check(result.returncode == 1 and (refused or {}).get("reason") == "worker-skill-build-skew"
              and refused.get("worker_skill_skew_count") == 1
              and not sandbox.record_dir("droid", host).exists(),
              f"AC9 #105: skewed ~/.factory worker Skill refuses the droid Host ({refused})")
        worker = "droid-KPR-i119-worker"
        receipt = sandbox.cli("droid", "start", session=worker, cli=cli)
        check(receipt.get("state") == "ready",
              "a worker-named droid start is not a Host and is not compared")
        sandbox.invoke("droid", "stop", "--force", session=worker, cli=cli)
    finally:
        sandbox.cleanup()


def test_host_resolves_like_worker_h1() -> None:
    """AC3: no Host-only model table or manifest field; same selection path."""
    scripts = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "scripts").glob("*.py"))
    constants = set(re.findall(r"\b([A-Z_]+_HOST_(?:MODEL_ID|EFFORT))\b", scripts))
    check(constants <= {"ZCODE_HOST_MODEL_ID", "ZCODE_HOST_EFFORT"},
          f"no new *_HOST_MODEL_ID/_HOST_EFFORT constants ({sorted(constants)})")
    render = load(ROOT / "scripts" / "render-skills.py", "render_119")
    hostish = {key for key in render.REQUIRED if "host" in key}
    check(hostish == {"host_skill_entry"}, f"the only Host manifest field is the entry ({hostish})")
    sandbox = Sandbox("h1")
    try:
        keys = ("model_selection", "resolved_runtime_model_id", "resolved_parameters",
                "config_application", "requested_tier")
        for platform in PLATFORMS:
            if platform == "zcode":
                continue  # its Host pin equals the default preset (test-issue-111-model-tiers)
            receipts = []
            for session in (f"{platform}-KPR-orchestrator-h1", f"{platform}-KPR-i119-h1"):
                receipt = sandbox.cli(platform, "start", "--tier", "default", session=session)
                check(receipt.get("state") == "ready", f"{platform} {session} starts")
                receipts.append({key: receipt.get(key) for key in keys})
                sandbox.cli(platform, "stop", "--force", session=session)
            check(receipts[0] == receipts[1],
                  f"{platform}: Host start resolves exactly the worker default ({receipts})")
    finally:
        sandbox.cleanup()


def test_opencode_explicit_selection_h2() -> None:
    sandbox = Sandbox("h2")
    try:
        plain = sandbox.cli("opencode", "start", session="opencode-KPR-i119-plain")
        check(plain.get("state") == "ready"
              and plain.get("effective_selection") == {"effective_model": "native/opening",
                                                       "effective_effort": "default"},
              f"no --model: the agent's own opening selection is reported ({plain.get('effective_selection')})")
        sandbox.cli("opencode", "stop", "--force", session="opencode-KPR-i119-plain")
        wanted = ("--model", "opencode-go/deepseek-v4.1-flash", "--effort", "max")
        honored = sandbox.cli("opencode", "start", *wanted, session="opencode-KPR-i119-ok")
        check(honored.get("state") == "ready" and honored.get("result") is None
              and honored.get("effective_selection") == {
                  "effective_model": "opencode-go/deepseek-v4.1-flash", "effective_effort": "max"},
              f"an honored explicit selection starts ({honored.get('effective_selection')})")
        sandbox.cli("opencode", "stop", "--force", session="opencode-KPR-i119-ok")
        session = "opencode-KPR-i119-ignored"
        result, refused = sandbox.invoke("opencode", "start", *wanted, session=session,
                                         FAKE119_IGNORE_MODEL="1")
        refused = refused or {}
        check(result.returncode == 1 and refused.get("result") == "refused"
              and refused.get("reason") == "explicit-selection-unverified"
              and refused.get("mutation_performed") is False
              and refused.get("host_session_stopped") is True
              and refused.get("holder_alive") is False
              and (refused.get("effective_selection") or {}).get("effective_model") == "native/opening",
              f"H2: an ignored explicit model is refused and stopped ({refused})")
        record = sandbox.record_dir("opencode", session) / "record.json"
        holder_pid = json.loads(record.read_text()).get("holder_pid") if record.exists() else None
        check(not pid_alive(holder_pid), "H2: no holder keeps running with another model")
    finally:
        sandbox.cleanup()


TESTS = [
    test_manifest_entries_are_the_code_table,
    test_zcode_carrier_is_byte_identical,
    test_carrier_first_lines_per_platform,
    test_non_zcode_host_binds_and_receives_carrier,
    test_entryless_dispatcher_and_non_zcode_refusals,
    test_non_zcode_host_build_skew_refuses,
    test_host_resolves_like_worker_h1,
    test_opencode_explicit_selection_h2,
]


def main() -> int:
    failures = 0
    for test in TESTS:
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"test-issue-119-host-entry: {len(TESTS) - failures}/{len(TESTS)} tests, {len(CHECKS)} checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
