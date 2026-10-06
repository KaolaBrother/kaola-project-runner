#!/usr/bin/env python3
"""Issue #266 composed proof: the real Runner entry with the outside launcher.

This runs the real ``command_start`` in a scratch export of the accepted base
with the integration patch applied (set ``K266_COMPOSED_ROOT`` to that export).
It is model-free: the claude-code adapter points at the existing ``fake-claude``
bridge. It proves the composed candidate, not the helper alone:

* a Host holder starts through the outside launcher and is re-parented;
* a Worker dispatched by that Host is recorded in the Host's child record and
  also starts outside the caller;
* a job unload does not erase that ownership or sweep the Worker;
* the Host stop with ``--preserve-dispatched-workers`` keeps the Worker;
* the later exact Worker stop leaves no residual.

All spawned pids are killed at the end. No install, no login, no live session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

SCRATCH = Path(os.environ.get("K266_COMPOSED_ROOT", "")).resolve() if os.environ.get("K266_COMPOSED_ROOT") else None
ROOT = SCRATCH or Path(__file__).resolve().parents[2]
ENTRY = ROOT / "scripts" / "claude-code-tmux.sh"
FAKE = ROOT / "tests" / "contract" / "fake-claude.py"
MOCK = ROOT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable or shutil.which("python3")
LABEL_PREFIX = "com.kaolabrother.kaola-runner.launch."

CHECKS: list[str] = []
EVIDENCE: list[dict] = []


def check(condition: bool, label: str, **evidence) -> None:
    EVIDENCE.append({"check": label, "ok": bool(condition), **evidence})
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def canonical(path: object) -> str:
    return os.path.realpath(str(path))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pid_alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool(out) and not out.upper().startswith("Z")


def wait_until(predicate, timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timeout: {label}")


class Sandbox:
    def __init__(self):
        self.dir = Path(canonical(tempfile.mkdtemp(prefix="k266comp.")))
        self.tmp = Path(tempfile.mkdtemp(prefix="k266.", dir="/tmp"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        self.state = self.dir / "state"
        self.runtime = self.dir / "runtime"
        for path in (self.home, self.repo, self.record_root, self.state, self.runtime):
            path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.pids: list[int] = []

    def env(self, **extra: str) -> dict:
        base = {
            "PATH": f"{ROOT}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "HOME": str(self.home), "LANG": os.environ.get("LANG", "C"),
            "TMPDIR": str(self.tmp), "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "CLAUDE_ACP_STATE_DIR": str(self.state), "CLAUDE_ACP_RUNTIME_DIR": str(self.runtime),
            "CLAUDE_BIN": str(FAKE), "KAOLA_CLAUDE_PROFILE_REQUIRED": "true",
        }
        base.update(extra)
        return base

    def cli(self, command: str, session: str, *args: str, timeout: float = 90,
            **extra: str) -> dict:
        argv = ["bash", str(ENTRY), command, "--repo", str(self.repo), "--session", session,
                *args]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                env=self.env(**extra))
        try:
            return json.loads(result.stdout)
        except ValueError as exc:  # noqa: F841
            raise AssertionError(f"{command} printed no JSON: {result.stdout[-400:]} {result.stderr[-400:]}")

    def tmux(self, platform: str, command: str, session: str, *args: str, timeout: float = 90,
             **extra: str) -> dict:
        argv = ["bash", str(ROOT / "scripts" / "kaola-tmux.sh"), platform, command,
                "--repo", str(self.repo), "--session", session, *args]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                env=self.env(**extra))
        try:
            return json.loads(result.stdout)
        except ValueError as exc:  # noqa: F841
            raise AssertionError(f"{platform} {command} printed no JSON: "
                                 f"{result.stdout[-400:]} {result.stderr[-400:]}")

    def record_dir(self, session: str, platform: str = "claude-code") -> Path:
        return (self.record_root / platform / session / sha(self.repo.as_posix())[:16])

    def record(self, session: str, platform: str = "claude-code") -> dict:
        try:
            return json.loads((self.record_dir(session, platform) / "record.json").read_text())
        except (OSError, ValueError):
            return {}

    def track(self, pid: object) -> None:
        if isinstance(pid, int) and pid > 0:
            self.pids.append(pid)

    def cleanup(self, sessions: list[str]) -> None:
        for session in sessions:
            for platform in ("claude-code", "opencode"):
                self.track(self.record(session, platform).get("holder_pid"))
        out = subprocess.run(["ps", "-axo", "pid,command"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and str(self.record_root) in parts[1] and parts[0].isdigit():
                self.track(int(parts[0]))
        for pid in sorted(set(self.pids), reverse=True):
            for sig in (15, 9):
                try:
                    os.kill(pid, sig)
                except (ProcessLookupError, PermissionError):
                    break
        shutil.rmtree(self.dir, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)


def label_for(session: str, repo: str) -> str:
    return LABEL_PREFIX + sha(f"claude-code\0{session}\0{repo}")[:16]


def rollback_source_check() -> None:
    """The repaired rejected-configuration rollback must not raise on proc=None."""
    import ast
    text = (ROOT / "scripts" / "kaola-acp.py").read_text()
    tree = ast.parse(text)
    function = next((node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "stop_started_holder"), None)
    check(function is not None, "the composed source exposes stop_started_holder")
    module = ast.Module(body=[function], type_ignores=[])
    globs = {"subprocess": subprocess, "os": os, "signal": signal,
             "pid_alive": lambda pid: False,
             "socket_request": lambda *a, **k: {"stopped": True, "residual_pids": []},
             "Path": Path}
    exec(compile(module, "<stop_started_holder>", "exec"), globs)  # noqa: S102
    result = globs["stop_started_holder"](Path("/nonexistent.sock"), None, 4242)
    check(result.get("host_session_stopped") is True and result.get("residual_pids") == []
          and result.get("holder_alive") is False,
          "stop_started_holder(proc=None) returns honest facts without an exception", result=result)


def _residual_for(record_dir: Path) -> list[str]:
    out = subprocess.run(["ps", "-axo", "pid,command"], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if str(record_dir) in line]


def _identity_gone(sb: Sandbox, session: str, platform: str = "claude-code") -> bool:
    """The recorded exact holder and agent identities exist and are both gone."""
    record = sb.record(session, platform)
    holder_pid = record.get("holder_pid")
    agent_pid = record.get("agent_pid")
    if not isinstance(holder_pid, int) or not isinstance(agent_pid, int):
        return False  # missing identities cannot prove no residual
    return not pid_alive(holder_pid) and not pid_alive(agent_pid)


def required_child_record_failure() -> None:
    """A required child-record write failure must not claim a nested success."""
    sb = Sandbox()
    session = f"claude-code-K266cust-{uuid.uuid4().hex[:6]}"
    bad = sb.dir / "child-dir"          # a directory: append must fail
    bad.mkdir()
    try:
        receipt = sb.cli("start", session, KAOLA_ACP_CHILD_RECORD=str(bad), timeout=150)
        code = (receipt.get("error") or {}).get("code")
        check(code == "child-record-failed",
              "a required child-record write failure refuses through the real entry",
              receipt=receipt)
        check(receipt.get("mutation_status") in ("not_started", "unknown"),
              "the custody failure reports truthful mutation state",
              mutation=receipt.get("mutation_status"))
        wait_until(lambda: _identity_gone(sb, session), 8,
                   "the failed nested launch leaves no holder or agent")
        check(_identity_gone(sb, session),
              "the recorded exact holder and agent identities are gone after the custody rollback")
        status = sb.cli("status", session, timeout=30)
        check(status.get("state") != "ready",
              "the custody rollback leaves no ready session",
              status={k: status.get(k) for k in ("state", "error")})
    finally:
        sb.cleanup([session])


def _opencode_shim(sb: Sandbox) -> Path:
    bin_dir = sb.dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shim = bin_dir / "opencode"
    shim.write_text("#!/bin/sh\nexec " + PYTHON + " " + str(MOCK) + " --caps strict-config \"$@\"\n")
    shim.chmod(0o755)
    return bin_dir


def configuration_refusal_rollback() -> None:
    """The real opencode entry must refuse an unverified explicit selection."""
    sb = Sandbox()
    bin_dir = _opencode_shim(sb)
    session = f"opencode-K266-{uuid.uuid4().hex[:6]}"
    try:
        receipt = sb.tmux("opencode", "start", session, "--model", "gpt-6.1-sol",
                          "--effort", "xhigh", timeout=180,
                          PATH=f"{bin_dir}:{ROOT}:{os.environ.get('PATH', '/usr/bin:/bin')}")
        code = receipt.get("reason") or (receipt.get("error") or {}).get("code")
        check(code == "explicit-selection-unverified",
              "the real opencode entry refuses an unverified explicit selection", receipt=receipt)
        check(receipt.get("mutation_status") in ("not_started", "unknown"),
              "the refusal reports truthful mutation state", mutation=receipt.get("mutation_status"))
        wait_until(lambda: _identity_gone(sb, session, "opencode"), 8,
                   "the refused configuration leaves no holder or agent")
        check(_identity_gone(sb, session, "opencode"),
              "the recorded exact holder and agent identities are gone after the refusal")
    finally:
        sb.cleanup([session])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-out")
    parser.add_argument("--only", choices=["child_record", "config_refusal"])
    args = parser.parse_args()
    if sys.platform != "darwin":
        print(json.dumps({"result": "unsupported", "detail": "macOS composed proof"}))
        return 0
    if not ENTRY.is_file():
        print(json.dumps({"result": "unsupported", "detail": f"missing {ENTRY}"}))
        return 0
    text = (ROOT / "scripts" / "kaola-acp.py").read_text()
    if "--launch-backend" not in text:
        print(json.dumps({"result": "unsupported",
                          "detail": "composed root has no --launch-backend; set K266_COMPOSED_ROOT"}))
        return 0

    if args.only:
        failures: list[str] = []
        try:
            if args.only == "child_record":
                required_child_record_failure()
            else:
                configuration_refusal_rollback()
        except AssertionError as exc:
            failures.append(str(exc))
        payload = {"result": "pass" if not failures else "fail", "checks": len(CHECKS),
                   "only": args.only, "failures": failures, "evidence": EVIDENCE, "root": str(ROOT)}
        if args.evidence_out:
            Path(args.evidence_out).write_text(json.dumps(payload, indent=2, sort_keys=True))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if failures else 0

    sb = Sandbox()
    host = "claude-code-K266-orchestrator-main"
    worker = f"claude-code-K266work-{uuid.uuid4().hex[:6]}"
    sessions = [host, worker]
    failures: list[str] = []
    try:
        rollback_source_check()
        # The normal Host entry: NO launch-backend flag. The shared path must
        # select the outside launcher by default.
        host_start = sb.cli("start", host)
        host_pid = host_start.get("holder_pid")
        sb.track(host_pid)
        check(host_start.get("state") == "ready",
              "the normal Host entry starts ready through the outside launcher",
              receipt={k: host_start.get(k) for k in ("state", "holder_pid", "holder_instance_id")})
        host_ppid = subprocess.run(["ps", "-o", "ppid=", "-p", str(host_pid)],
                                   capture_output=True, text=True).stdout.strip()
        check(host_ppid == "1", "the Host holder is re-parented to the service manager", host_pid=host_pid)
        check(sb.record(host).get("session_role") == "host",
              "the Host session records the Host role", role=sb.record(host).get("session_role"))
        check(sb.record(host).get("start_selection", {}).get("launch_backend") in ("auto", "launchd"),
              "the normal Host entry records the outside backend",
              selection=sb.record(host).get("start_selection"))
        holder_env = subprocess.run(["ps", "eww", "-o", "command=", "-p", str(host_pid)],
                                    capture_output=True, text=True).stdout
        check("KAOLA_LAUNCH_BACKEND=" in holder_env,
              "the Host holder exports KAOLA_LAUNCH_BACKEND for its seats")

        # The Host dispatches a Worker: the outer agent environment carries the
        # Host's child record. The Worker passes NO explicit flag and no injected
        # backend, so it must use the shared normal path too.
        child_record = sb.record_dir(host) / "children.jsonl"
        worker_start = sb.cli("start", worker,
                              KAOLA_ACP_CHILD_RECORD=str(child_record),
                              **{"KAOLA_ACP_DISPATCHER": json.dumps({
                                  "holder_instance_id": host_start.get("holder_instance_id"),
                                  "platform": "claude-code", "repo": str(sb.repo), "session": host})})
        worker_pid = worker_start.get("holder_pid")
        sb.track(worker_pid)
        check(worker_start.get("state") == "ready", "the dispatched Worker starts ready outside the caller",
              receipt={k: worker_start.get(k) for k in ("state", "holder_pid", "holder_instance_id")})
        worker_ppid = subprocess.run(["ps", "-o", "ppid=", "-p", str(worker_pid)],
                                     capture_output=True, text=True).stdout.strip()
        check(worker_ppid == "1", "the Worker uses the shared normal path and is re-parented",
              worker_pid=worker_pid)
        check(sb.record(worker).get("start_selection", {}).get("launch_backend") in ("auto", "launchd"),
              "the Worker records the outside backend with no flag",
              selection=sb.record(worker).get("start_selection"))
        entries = [json.loads(l) for l in child_record.read_text().splitlines() if l.strip()] \
            if child_record.exists() else []
        check(any(e.get("pid") == worker_pid for e in entries),
              "the Worker is recorded in the Host's child record (dispatcher ownership)",
              child_record=entries)

        # A job unload must not erase ownership or sweep the detached Worker.
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{label_for(worker, str(sb.repo))}"],
                       capture_output=True, text=True)
        time.sleep(0.4)
        check(pid_alive(worker_pid), "the Worker survives a job unload")

        # Host stop with preserve-dispatched-workers keeps the Worker.
        host_stop = sb.cli("stop", host, "--force", "--preserve-dispatched-workers")
        check("residual_pids" in host_stop and host_stop["residual_pids"] == [],
              "the Host stop leaves no residual", stop={k: host_stop.get(k) for k in ("stopped", "residual_pids")})
        wait_until(lambda: not pid_alive(host_pid), 10, "Host holder gone")
        check(pid_alive(worker_pid), "the preserved Worker still runs after the Host stop")

        # Later exact Worker stop: no residual.
        worker_stop = sb.cli("stop", worker, "--force")
        check("residual_pids" in worker_stop and worker_stop["residual_pids"] == [],
              "the later exact Worker stop leaves no residual",
              stop={k: worker_stop.get(k) for k in ("stopped", "residual_pids")})
        wait_until(lambda: not pid_alive(worker_pid), 10, "Worker holder gone")

        # The real entry's deliberate failure paths.
        required_child_record_failure()
        configuration_refusal_rollback()
    except AssertionError as exc:
        failures.append(str(exc))
    finally:
        sb.cleanup(sessions)

    payload = {"result": "pass" if not failures else "fail", "checks": len(CHECKS),
               "failures": failures, "evidence": EVIDENCE, "root": str(ROOT)}
    if args.evidence_out:
        Path(args.evidence_out).write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
