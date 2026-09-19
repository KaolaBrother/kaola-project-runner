#!/usr/bin/env python3
"""Issue #50 Mission 2: offline acceptance for the Runner integration of the
vendored Claude Code ACP bridge.

The bridge itself is covered by ``test-issue-50-claude-acp-bridge.py``. This
file drives the real Runner entry points -- ``kaola-acp.py`` from the checkout
layout and from the generated Skill, plus ``runtime-tmux.sh`` for transport
dispatch -- with no network, no account, and no real ``claude``: ``CLAUDE_BIN``
points at ``fake-claude.py``, HOME is a sandbox, credential variables must be
stripped, an unrelated canary must survive, and a PATH whose first ``claude``
is a trap must never fire.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "vendor" / "claude-code-acp"
SKILL = ROOT / "skills" / "claude-code-kaola-project-runner"
CHECKOUT_CLI = ROOT / "scripts" / "kaola-acp.py"
SKILL_CLI = SKILL / "scripts" / "kaola-acp.py"
RUNTIME = SKILL / "scripts" / "runtime-tmux.sh"
RENDERER = ROOT / "scripts" / "render-skills.py"
MANIFEST = ROOT / "platforms" / "claude-code.yaml"
FAKE = ROOT / "tests" / "contract" / "fake-claude.py"
UPSTREAM_COMMIT = "6c20f2802e390c80b0542247c6b9738e11efdc11"
ACP_COMMAND = "node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js"
VENDORED_FILES = ("dist/index.js", "dist/DERIVATION.json", "LICENSE")
PYTHON = sys.executable or shutil.which("python3")

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(out) and not out.startswith("Z")


def wait_until(predicate, timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timeout: {label}")


def flag(argv: list[str], name: str) -> str | None:
    if name in argv and argv.index(name) + 1 < len(argv):
        return argv[argv.index(name) + 1]
    return None


def parse_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition(":")
            result[key.strip()] = json.loads(value.strip())
    return result


class Sandbox:
    """One isolated Runner environment: HOME, repository, record root, bridge state."""

    def __init__(self, name: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-i50-{name}-"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        self.state = self.dir / "state"
        self.runtime_dir = self.dir / "runtime"
        self.trap_dir = self.dir / "path-trap"
        self.trap_hit = self.dir / "path-trap-hit"
        for path in (self.home, self.repo, self.record_root, self.state, self.runtime_dir, self.trap_dir):
            path.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        trap = self.trap_dir / "claude"
        trap.write_text(f"#!/bin/sh\ntouch '{self.trap_hit}'\nexit 97\n")
        trap.chmod(trap.stat().st_mode | stat.S_IXUSR)
        self.record = self.dir / "claude-launches.jsonl"
        self.canary = f"canary-{uuid.uuid4()}"
        self.sessions: list[tuple[Path, str]] = []

    def env(self, **overrides: str | None) -> dict[str, str]:
        base = {
            "PATH": f"{self.trap_dir}:{os.environ.get('PATH', '')}",
            "HOME": str(self.home),
            "LANG": os.environ.get("LANG", "C"),
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "CLAUDE_ACP_STATE_DIR": str(self.state),
            "CLAUDE_ACP_RUNTIME_DIR": str(self.runtime_dir),
            "CLAUDE_BIN": str(FAKE),
            "FAKE_CLAUDE_RECORD": str(self.record),
            "KAOLA_FAKE_CANARY": self.canary,
            "ANTHROPIC_API_KEY": f"fake-api-key-{uuid.uuid4()}",
            "ANTHROPIC_AUTH_TOKEN": f"fake-auth-token-{uuid.uuid4()}",
        }
        for key, value in overrides.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        return base

    def session(self) -> str:
        return f"claude-code-kaola-i50-{uuid.uuid4().hex[:8]}"

    def cli(self, entry: Path, command: str, *args: str, session: str | None = None,
            timeout: float = 60, **env_overrides: str | None) -> dict:
        argv = [PYTHON, str(entry), "claude-code", command, "--repo", str(self.repo)]
        if session:
            argv += ["--session", session]
            if command == "start":
                self.sessions.append((entry, session))
        argv += list(args)
        result = subprocess.run(argv, capture_output=True, text=True, env=self.env(**env_overrides), timeout=timeout)
        if result.returncode != 0:
            raise AssertionError(f"{command} exit {result.returncode}: {result.stderr[-800:]}")
        try:
            return json.loads(result.stdout)
        except ValueError as exc:
            raise AssertionError(f"{command} printed no JSON receipt: {result.stdout[-400:]} {result.stderr[-400:]}") from exc

    def runtime(self, *args: str) -> dict:
        result = subprocess.run(["bash", str(RUNTIME), *args], capture_output=True, text=True,
                                env=self.env(), timeout=60)
        try:
            return json.loads(result.stdout)
        except ValueError as exc:
            raise AssertionError(f"runtime-tmux.sh printed no JSON receipt: {result.stdout[-400:]} {result.stderr[-400:]}") from exc

    def records(self) -> list[dict]:
        if not self.record.is_file():
            return []
        return [json.loads(line) for line in self.record.read_text().splitlines() if line.strip()]

    def temp_residue(self) -> list[str]:
        return sorted(p.name for p in self.runtime_dir.iterdir())

    def cleanup(self) -> None:
        for entry, session in self.sessions:
            subprocess.run([PYTHON, str(entry), "claude-code", "stop", "--repo", str(self.repo),
                            "--session", session, "--force"], capture_output=True, env=self.env(), timeout=30)
        shutil.rmtree(self.dir, ignore_errors=True)


# --------------------------------------------------------------------------- tests


def test_manifest_and_generated_skill() -> None:
    manifest = parse_manifest(MANIFEST)
    check(manifest["acp_command"] == ACP_COMMAND, "acp_command is the Skill-relative vendored dist")
    check("npx" not in manifest["acp_command"] and "claude-agent-acp" not in manifest["acp_command"],
          "acp_command names neither npx nor the official wrapper")
    check("registry" not in manifest["acp_command"] and "npm" not in manifest["acp_command"],
          "acp_command carries no registry reference")
    check(manifest["acp_wrapper_pin"] == UPSTREAM_COMMIT, "acp_wrapper_pin is the upstream commit")
    versions = dict(part.split("=", 1) for part in manifest["acp_verified_versions"].split(";"))
    check(versions.get("bridge") == UPSTREAM_COMMIT[:7] and versions.get("protocol") == "1" and "cli" in versions,
          "acp_verified_versions records cli, bridge, and protocol")
    allow = manifest["acp_env_allowlist"].split(",")
    check(allow == ["CLAUDE_BIN", "CLAUDE_CONFIG_DIR"], "acp_env_allowlist is CLAUDE_BIN,CLAUDE_CONFIG_DIR")
    check("ANTHROPIC_API_KEY" not in manifest["acp_env_allowlist"], "acp_env_allowlist excludes the API key")
    check(manifest["acp_login_requires_pty"] == "true", "login stays a PTY act")
    check((manifest["acp_model_config_id"], manifest["acp_effort_config_id"], manifest["acp_fast_config_id"])
          == ("model", "effort", "fast"), "model/effort/fast config ids match the bridge's options")
    check(manifest["default_transport"] in ("pty", "acp"), "default_transport is a valid channel")
    for name in VENDORED_FILES:
        shipped = SKILL / "scripts" / "vendor" / "claude-code-acp" / name
        check(shipped.is_file() and shipped.read_bytes() == (VENDOR / name).read_bytes(),
              f"Claude worker ships vendored {name} byte-identical")
    skill_text = (SKILL / "SKILL.md").read_text()
    check(ACP_COMMAND in skill_text and f"Default transport: **{manifest['default_transport']}**" in skill_text,
          "Claude SKILL.md states the ACP command and the default transport")
    check(ACP_COMMAND in (SKILL / "references" / "acp.md").read_text(), "Claude acp.md states the ACP command")
    others = [p for p in (ROOT / "skills").iterdir() if p.is_dir() and p != SKILL]
    check(len(others) == 11, "eleven other generated packages (nine other workers + orchestrator + kaola-delegator)")
    for package in others:
        check(not (package / "scripts" / "vendor").exists(), f"{package.name} ships no vendored bridge")
        check("claude-code-acp" not in (package / "SKILL.md").read_text(), f"{package.name} SKILL.md does not mention the bridge")
    for product in (ROOT / "hosts" / "grok-bot").iterdir():
        check("claude-code-acp" not in product.read_text(errors="replace"), f"host product {product.name} does not mention the bridge")
    result = subprocess.run([PYTHON, str(RENDERER), "--check"], capture_output=True, text=True)
    check(result.returncode == 0, f"render-skills.py --check passes: {result.stderr.strip()}")


def test_preflight_facts_in_both_layouts() -> None:
    dist_hash = sha256(VENDOR / "dist" / "index.js")
    for entry, layout, expected in (
        (CHECKOUT_CLI, "checkout", VENDOR / "dist" / "index.js"),
        (SKILL_CLI, "skill", SKILL / "scripts" / "vendor" / "claude-code-acp" / "dist" / "index.js"),
    ):
        sandbox = Sandbox(f"preflight-{layout}")
        try:
            receipt = sandbox.cli(entry, "preflight")
            check(receipt.get("error") is None, f"{layout}: preflight succeeds ({receipt.get('error')})")
            bridge = receipt["bridge"]
            check(bridge["present"] and bridge["layout"] == layout and bridge["path"] == str(expected),
                  f"{layout}: preflight resolves the bridge to the {layout} dist")
            check(bridge["sha256"] == dist_hash and bridge["upstream_pin"] == UPSTREAM_COMMIT,
                  f"{layout}: preflight reports the dist hash and the upstream pin")
            binary = receipt["runtime_binary"]
            check(binary["path"] == str(FAKE) and binary["absolute"] and binary["present"]
                  and binary["env"] == "CLAUDE_BIN" and binary["passed_as"] == "CLAUDE_ACP_CLAUDE_BIN",
                  f"{layout}: preflight reports the exact claude path and how it reaches the bridge")
            check(str(binary.get("version", "")).startswith("9.9.9"), f"{layout}: preflight reports the claude version")
            transport = receipt["transport"]
            check(transport["agent_info"]["name"] == "claude-code-acp" and transport["protocol_version"] == 1,
                  f"{layout}: the vendored bridge answered initialize on protocol 1")
            check({"mode", "model", "effort", "fast"} <= set(transport["advertised_config_ids"]),
                  f"{layout}: the bridge advertises mode/model/effort/fast")
            check(receipt.get("login_required") is False, f"{layout}: no login gate is reported")
            check(not sandbox.trap_hit.exists() and sandbox.records() == [],
                  f"{layout}: preflight spawned no claude and never touched PATH")
        finally:
            sandbox.cleanup()


def test_fail_closed_without_exact_binary_or_bridge() -> None:
    sandbox = Sandbox("failclosed")
    try:
        missing = str(sandbox.dir / "nowhere" / "claude")
        receipt = sandbox.cli(CHECKOUT_CLI, "preflight", CLAUDE_BIN=missing)
        binary = receipt["runtime_binary"]
        check(binary["path"] == missing and binary["absolute"] and not binary["present"] and "version" not in binary,
              "missing CLAUDE_BIN is reported as absent, no version probe")
        check(receipt.get("error") is not None and "-32603" in json.dumps(receipt["error"]),
              "preflight session/new fails closed with the bridge's internal error")
        session = sandbox.session()
        receipt = sandbox.cli(CHECKOUT_CLI, "start", session=session, CLAUDE_BIN="claude")
        check(receipt.get("error") is not None and "-32603" in json.dumps(receipt["error"]),
              "start with a bare (non-absolute) CLAUDE_BIN fails closed")
        sandbox.cli(CHECKOUT_CLI, "stop", "--force", session=session, CLAUDE_BIN="claude")
        check(not sandbox.trap_hit.exists() and sandbox.records() == [], "no PATH fallback and no claude launch")

        island = sandbox.dir / "island-skill"
        shutil.copytree(SKILL, island, ignore=shutil.ignore_patterns("vendor"))
        island_cli = island / "scripts" / "kaola-acp.py"
        check(not (island / "scripts" / "vendor").exists(), "island Skill copy lacks the vendored bridge")
        receipt = sandbox.cli(island_cli, "preflight")
        check(receipt["error"]["code"] == "acp-bridge-missing" and receipt["bridge"]["present"] is False,
              "preflight without the vendored dist reports acp-bridge-missing")
        refused = sandbox.session()
        receipt = sandbox.cli(island_cli, "start", session=refused)
        check(receipt["error"]["code"] == "acp-bridge-missing" and receipt["mutation_status"] == "not_started",
              "start without the vendored dist refuses before spawning anything")
        check(not any(sandbox.record_root.glob(f"claude-code/{refused}/*/record.json")),
              "no holder record was created for the refused start")
        # Both shapes name files that exist, so only the refusal itself can satisfy the check.
        for escape in ("$SKILL_DIR/scripts/../scripts/kaola-acp.py", "$SKILL_DIR/scripts//etc/hosts"):
            receipt = sandbox.cli(CHECKOUT_CLI, "preflight", "--command", f"node {escape}")
            check(receipt["error"]["code"] == "acp-bridge-missing" and receipt["bridge"]["present"] is False,
                  f"a Skill-relative token never escapes the Skill: {escape}")
    finally:
        sandbox.cleanup()


def test_start_send_cancel_stop_through_generated_skill() -> None:
    sandbox = Sandbox("turns")
    try:
        session = sandbox.session()
        receipt = sandbox.cli(SKILL_CLI, "start", "--tier", "upgrade", "--mode", "bypassPermissions", session=session)
        check(receipt.get("error") is None and receipt["state"] == "ready", f"start reaches ready ({receipt.get('error')})")
        check(receipt["bridge"]["layout"] == "skill", "start resolved the bridge inside the generated Skill")
        applied = receipt["config_application"]
        check(applied["model"]["applied"] and applied["model"]["value"] == "fable", "Fable applied through the model option")
        check(applied["effort"]["applied"] and applied["effort"]["value"] == "high", "High applied through the effort option")
        check(applied["mode"]["applied"] and applied["mode"]["value"] == "bypassPermissions", "bypassPermissions applied through the mode option")
        check(applied["fast"]["applied"] and applied["fast"]["value"] == "off", "Fast off pinned through the fast option")
        sid = receipt["acp_session_id"]
        check(isinstance(sid, str) and sid, "start reports an ACP session id")

        receipt = sandbox.cli(SKILL_CLI, "send", "--text", "hello", session=session)
        check(receipt["outcome"] == "turn_completed" and receipt["mutation_status"] == "completed"
              and receipt["final_text"] == "echo:hello", "send --wait returns the turn's final text")
        first = sandbox.records()[0]
        argv = first["argv"]
        check(flag(argv, "--input-format") == "stream-json" and flag(argv, "--output-format") == "stream-json",
              "first turn is one streaming claude subprocess reading its prompt from stdin")
        check("hello" not in " ".join(argv), "the prompt text stays out of the argument list")
        check(flag(argv, "--model") == "fable" and flag(argv, "--effort") == "high", "first turn carries --model fable --effort high")
        check(flag(argv, "--permission-mode") == "bypassPermissions" and "--dangerously-skip-permissions" not in argv,
              "first turn carries the mapped --permission-mode and no skip flag")
        check(json.loads(flag(argv, "--settings") or "{}") == {"fastMode": False}, "first turn pins fastMode=false")
        check("--resume" not in argv and "--continue" not in argv, "first turn does not resume")
        check(first["cwd"] == os.path.realpath(sandbox.repo), "claude runs in the canonical repository")
        check(first["argv0"] == str(FAKE.resolve()), "the exact CLAUDE_BIN was spawned")
        check(not first["has_api_key"] and not first["has_auth_token"], "ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN are absent from claude's env")
        check(first["canary"] == sandbox.canary and "HOME" in first["env_keys"], "unrelated inherited variables reach claude")
        check("KAOLA_ACP_CHILD_RECORD" not in first["env_keys"],
              "the holder's child record path is not handed to claude (nor to the tools it spawns)")
        check(not sandbox.trap_hit.exists(), "PATH claude never ran")

        receipt = sandbox.cli(SKILL_CLI, "send", "--text", "again", session=session)
        check(receipt["final_text"] == "echo:again", "second send completes")
        second = sandbox.records()[1]
        check(flag(second["argv"], "--resume") == first["session_id"], "second turn resumes the claude session id from the first")
        check(flag(second["argv"], "--model") == "fable" and flag(second["argv"], "--permission-mode") == "bypassPermissions",
              "resume turn repeats the session's model and permission mode")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        check(status["acp_session_id"] == sid and status.get("error") is None, "status reports the same session")
        capture = sandbox.cli(SKILL_CLI, "capture", session=session)
        check("echo:again" in json.dumps(capture), "capture carries the latest final text")

        receipt = sandbox.cli(SKILL_CLI, "send", "--text", "[hang]long", "--no-wait", session=session)
        check(receipt["outcome"] == "in_progress" and receipt["mutation_status"] == "in_progress", "a long prompt is accepted without waiting")
        wait_until(lambda: len(sandbox.records()) >= 3 and sandbox.records()[2].get("grandchild_pid"), 15, "hanging claude launched")
        hanging = sandbox.records()[2]
        check(pid_alive(hanging["pid"]) and pid_alive(hanging["grandchild_pid"]), "claude and its grandchild are running")
        receipt = sandbox.cli(SKILL_CLI, "cancel", session=session)
        check(receipt["outcome"] == "turn_canceled" and receipt["stop_reason"] == "cancelled", "cancel settles the turn as cancelled")
        wait_until(lambda: not pid_alive(hanging["pid"]) and not pid_alive(hanging["grandchild_pid"]), 8, "cancel killed the process group")
        check(True, "cancel killed claude and its grandchild")

        status = sandbox.cli(SKILL_CLI, "status", session=session)
        holder_pid, agent_pid = status.get("holder_pid"), status.get("agent_pid")
        receipt = sandbox.cli(SKILL_CLI, "stop", session=session)
        check(receipt.get("error") is None and receipt.get("residual_pids") == [], "stop reports no residual pids")
        wait_until(lambda: not pid_alive(holder_pid) and not pid_alive(agent_pid), 8, "holder and bridge exited")
        check(True, "holder and bridge exited after stop")
        check(sandbox.temp_residue() == [], "no bridge temp file survives stop")
        check(not sandbox.trap_hit.exists(), "PATH claude never ran during the session")
    finally:
        sandbox.cleanup()


def test_force_stop_sweeps_detached_claude_groups() -> None:
    """`claude -p` runs detached in its own process group, outside the
    bridge's. Force stop must end it and report it whether the bridge is
    healthy, died before its own shutdown ran, or died together with the
    holder (record-based force stop)."""
    sandbox = Sandbox("force")
    try:
        def hanging_turn(index: int, label: str, mode: str = "hang", **env: str) -> tuple[str, dict]:
            session = sandbox.session()
            receipt = sandbox.cli(SKILL_CLI, "start", session=session, **env)
            check(receipt.get("error") is None and receipt["state"] == "ready", f"{label}: start reaches ready")
            receipt = sandbox.cli(SKILL_CLI, "send", "--text", f"[{mode}]{label}", "--no-wait", session=session)
            check(receipt["outcome"] == "in_progress", f"{label}: hanging prompt accepted")
            wait_until(lambda: len(sandbox.records()) > index and sandbox.records()[index].get("grandchild_pid"),
                       15, f"{label}: hanging claude launched")
            rec = sandbox.records()[index]
            check(pid_alive(rec["pid"]) and pid_alive(rec["grandchild_pid"]), f"{label}: claude and grandchild alive")
            status = sandbox.cli(SKILL_CLI, "status", session=session)
            check(rec["pgid"] != status["agent_pgid"], f"{label}: claude runs in its own process group outside the bridge's")
            if mode == "silent":
                # The child is running but has written nothing: no session/update
                # has reached the holder, so the turn is still only in_progress.
                time.sleep(0.5)
                status = sandbox.cli(SKILL_CLI, "status", session=session)
                check(status.get("mutation_status") == "in_progress" and status.get("turn_active") is True,
                      f"{label}: no session/update seen yet (turn still in_progress)")
                return session, rec
            wait_until(lambda: sandbox.cli(SKILL_CLI, "status", session=session).get("mutation_status") == "accepted",
                       10, f"{label}: turn accepted (first update seen)")
            # record.json is written right after the note; allow that write to land.
            wait_until(lambda: rec["pgid"] in sandbox.cli(SKILL_CLI, "status", session=session)["record"].get("agent_child_pgids", []),
                       10, f"{label}: the holder noted the claude group while the bridge was alive")
            check(True, f"{label}: the holder noted the claude group while the bridge was alive")
            return session, rec

        def expect_gone(rec: dict, label: str) -> None:
            wait_until(lambda: not pid_alive(rec["pid"]) and not pid_alive(rec["grandchild_pid"]), 8,
                       f"{label}: claude and grandchild ended")
            check(True, f"{label}: claude and its grandchild are gone")

        # A: force stop while the bridge is healthy and a turn is running.
        session, rec = hanging_turn(0, "healthy")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session)
        check(receipt.get("error") is None and receipt.get("stopped") is True, "healthy: force stop succeeds")
        check(receipt.get("residual_pids") == [], "healthy: force stop reports no residual pids")
        check(receipt.get("swept_child_pgids") == [], "healthy: the bridge ended its own claude group, nothing left to sweep")
        expect_gone(rec, "healthy")
        wait_until(lambda: not pid_alive(status["holder_pid"]) and not pid_alive(status["agent_pid"]), 8, "healthy: holder and bridge exited")

        # B: the bridge dies before its shutdown could stop the child; holder alive.
        session, rec = hanging_turn(1, "bridge-dead")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        os.kill(status["agent_pid"], signal.SIGKILL)
        wait_until(lambda: not pid_alive(status["agent_pid"]), 5, "bridge-dead: bridge killed")
        check(pid_alive(rec["pid"]) and pid_alive(rec["grandchild_pid"]), "bridge-dead: the claude group outlives the killed bridge")
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session)
        check(receipt.get("error") is None and receipt.get("residual_pids") == [], "bridge-dead: force stop reports no residual pids")
        check(rec["pgid"] in receipt.get("swept_child_pgids", []), "bridge-dead: the orphaned claude group was swept")
        expect_gone(rec, "bridge-dead")

        # C: holder and bridge both gone; the record carries the child groups.
        session, rec = hanging_turn(2, "holder-lost")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        for pid in (status["holder_pid"], status["agent_pid"]):
            os.kill(pid, signal.SIGKILL)
        wait_until(lambda: not pid_alive(status["holder_pid"]) and not pid_alive(status["agent_pid"]), 5, "holder-lost: holder and bridge killed")
        check(pid_alive(rec["pid"]) and pid_alive(rec["grandchild_pid"]), "holder-lost: the claude group outlives holder and bridge")
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session)
        check(receipt.get("holder_lost") is True and receipt.get("residual_pids") == [], "holder-lost: record-based force stop reports no residual pids")
        check(rec["pgid"] in receipt.get("swept_pgids", []), "holder-lost: the recorded claude group was swept")
        expect_gone(rec, "holder-lost")

        # D: the bridge dies after spawning claude but before the child's first
        # line, so no session/update ever reached the holder; holder alive.
        session, rec = hanging_turn(3, "silent-bridge-dead", mode="silent")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        os.kill(status["agent_pid"], signal.SIGKILL)
        wait_until(lambda: not pid_alive(status["agent_pid"]), 5, "silent-bridge-dead: bridge killed")
        check(pid_alive(rec["pid"]) and pid_alive(rec["grandchild_pid"]), "silent-bridge-dead: the silent claude group outlives the killed bridge")
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session)
        check(receipt.get("error") is None and receipt.get("residual_pids") == [], "silent-bridge-dead: force stop reports no residual pids")
        check(rec["pgid"] in receipt.get("swept_child_pgids", []), "silent-bridge-dead: the never-announced claude group was swept")
        expect_gone(rec, "silent-bridge-dead")

        # E: same, with the holder gone as well (record-based force stop).
        session, rec = hanging_turn(4, "silent-holder-lost", mode="silent")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        for pid in (status["holder_pid"], status["agent_pid"]):
            os.kill(pid, signal.SIGKILL)
        wait_until(lambda: not pid_alive(status["holder_pid"]) and not pid_alive(status["agent_pid"]), 5, "silent-holder-lost: holder and bridge killed")
        check(pid_alive(rec["pid"]) and pid_alive(rec["grandchild_pid"]), "silent-holder-lost: the silent claude group outlives holder and bridge")
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session)
        check(receipt.get("holder_lost") is True and receipt.get("residual_pids") == [], "silent-holder-lost: record-based force stop reports no residual pids")
        check(rec["pgid"] in receipt.get("swept_pgids", []), "silent-holder-lost: the never-announced claude group was swept")
        expect_gone(rec, "silent-holder-lost")

        # G/H: macOS `ps` localises `lstart` from the caller's locale; the holder
        # inherits it from `start`, the holder-lost path from `stop`. Identity
        # must still hold when either runs under a non-English locale.
        session, rec = hanging_turn(5, "silent-zh-holder", mode="silent", LC_ALL="zh_CN.UTF-8")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        os.kill(status["agent_pid"], signal.SIGKILL)
        wait_until(lambda: not pid_alive(status["agent_pid"]), 5, "silent-zh-holder: bridge killed")
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session)
        check(receipt.get("error") is None and receipt.get("residual_pids") == [], "silent-zh-holder: force stop reports no residual pids")
        check(rec["pgid"] in receipt.get("swept_child_pgids", []), "silent-zh-holder: a holder started under zh_CN still identifies the never-announced child")
        expect_gone(rec, "silent-zh-holder")

        session, rec = hanging_turn(6, "silent-de-holder-lost", mode="silent")
        status = sandbox.cli(SKILL_CLI, "status", session=session)
        for pid in (status["holder_pid"], status["agent_pid"]):
            os.kill(pid, signal.SIGKILL)
        wait_until(lambda: not pid_alive(status["holder_pid"]) and not pid_alive(status["agent_pid"]), 5, "silent-de-holder-lost: holder and bridge killed")
        receipt = sandbox.cli(SKILL_CLI, "stop", "--force", session=session, LC_ALL="de_DE.UTF-8")
        check(receipt.get("holder_lost") is True and receipt.get("residual_pids") == [], "silent-de-holder-lost: record-based force stop reports no residual pids")
        check(rec["pgid"] in receipt.get("swept_pgids", []), "silent-de-holder-lost: a stop under de_DE still identifies the never-announced child")
        expect_gone(rec, "silent-de-holder-lost")

        # F: a later start of the same session compacts the spawn record so only
        # entries whose identity still holds survive (the swept child's is gone).
        def spawn_record_lines() -> list[dict]:
            files = list((sandbox.record_root / "claude-code" / session).glob("*/children.jsonl"))
            check(len(files) == 1, "restart: the session has exactly one spawn record file")
            return [json.loads(line) for line in files[0].read_text().splitlines() if line.strip()]

        check(len(spawn_record_lines()) == 1, "restart: the swept silent child is still recorded before the restart")
        receipt = sandbox.cli(SKILL_CLI, "start", session=session)
        check(receipt.get("error") is None and receipt["state"] == "ready", "restart: the same session starts again")
        check(spawn_record_lines() == [], "restart: the stale spawn entry was dropped at agent start")
        receipt = sandbox.cli(SKILL_CLI, "send", "--text", "after-restart", session=session)
        check(receipt["final_text"] == "echo:after-restart", "restart: a turn completes")
        lines = spawn_record_lines()
        check([entry["pid"] for entry in lines] == [sandbox.records()[7]["pid"]],
              "restart: the spawn record holds exactly this instance's child")
        receipt = sandbox.cli(SKILL_CLI, "stop", session=session)
        check(receipt.get("error") is None and receipt.get("residual_pids") == [], "restart: stop reports no residual pids")
    finally:
        sandbox.cleanup()


def test_continue_and_resume_land_in_the_same_native_session() -> None:
    sandbox = Sandbox("resume")
    try:
        first_session = sandbox.session()
        receipt = sandbox.cli(SKILL_CLI, "start", session=first_session)
        check(receipt.get("error") is None, "fresh start succeeds")
        sandbox.cli(SKILL_CLI, "send", "--text", "one", session=first_session)
        native = sandbox.records()[0]["session_id"]
        sandbox.cli(SKILL_CLI, "stop", session=first_session)

        cont = sandbox.session()
        receipt = sandbox.cli(SKILL_CLI, "start", "--continue", session=cont)
        check(receipt.get("error") is None and receipt["acp_session_id"] == native, "start --continue selects the latest native session")
        check(receipt["model_selection"]["source"] == "resume-preserved", "continue preserves the saved selection")
        sandbox.cli(SKILL_CLI, "send", "--text", "two", session=cont)
        argv = sandbox.records()[1]["argv"]
        check(flag(argv, "--resume") == native and "--model" not in argv,
              "continued turn resumes the native session without a Runner model override")
        check(flag(argv, "--permission-mode") == "bypassPermissions", "continued turn still carries the permission mode")
        sandbox.cli(SKILL_CLI, "stop", session=cont)

        res = sandbox.session()
        receipt = sandbox.cli(SKILL_CLI, "start", "--resume", native, "--tier", "upgrade", session=res)
        check(receipt.get("error") is None and receipt["acp_session_id"] == native, "start --resume binds the named native session")
        sandbox.cli(SKILL_CLI, "send", "--text", "three", session=res)
        argv = sandbox.records()[2]["argv"]
        check(flag(argv, "--resume") == native and flag(argv, "--model") == "fable" and flag(argv, "--effort") == "high",
              "resumed turn with an explicit tier carries --resume plus the requested model/effort")
        sandbox.cli(SKILL_CLI, "stop", session=res)
        check(len({r["session_id"] for r in sandbox.records()}) == 1, "all three turns share one native session id")
        check(not sandbox.trap_hit.exists(), "PATH claude never ran")
    finally:
        sandbox.cleanup()


def test_pty_fallback_stays_explicit() -> None:
    sandbox = Sandbox("dispatch")
    try:
        default = parse_manifest(MANIFEST)["default_transport"]
        session = sandbox.session()
        receipt = sandbox.runtime("status", "--repo", str(sandbox.repo), "--session", session, "--transport", "pty")
        check(receipt["transport"]["selected"] == "pty" and receipt["transport"]["default"] == default,
              "--transport pty selects the PTY channel and reports the manifest default")
        receipt = sandbox.runtime("status", "--repo", str(sandbox.repo), "--session", session, "--transport", "acp")
        check(receipt["transport"]["selected"] == "acp" and receipt["error"]["code"] == "no-session",
              "--transport acp reaches kaola-acp.py")
        receipt = sandbox.runtime("status", "--repo", str(sandbox.repo), "--session", session)
        check(receipt["transport"]["selected"] == default and receipt["transport"]["reason"] == "manifest-default",
              "no override follows the manifest default")
    finally:
        sandbox.cleanup()


def main() -> int:
    if not shutil.which("node"):
        print("test-issue-50-runner-integration: node is required on PATH", file=sys.stderr)
        return 1
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report every failure, keep running
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(f"test-issue-50-runner-integration: {len(tests) - failures}/{len(tests)} tests, {len(CHECKS)} checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
