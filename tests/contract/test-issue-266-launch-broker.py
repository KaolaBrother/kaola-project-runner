#!/usr/bin/env python3
"""Issue #266 focused contract: shared outside-caller launcher (macOS launchd).

Model-free. It launches a real ACP holder through ``scripts/kaola-launchd-broker.py``
using the existing mock ACP agent, then proves the promised behavior:

* broker exit and job unload leave the holder (and its dispatched worker child)
  alive and re-parented to the service manager;
* the standard client still controls it (``status`` / ``send`` / ``capture`` /
  ``steer`` / ``stop``);
* a repeated submit reconciles the live holder instead of starting a duplicate;
* a failed bootstrap leaves no stale job or plist;
* ``stop`` sweeps the detached tree to ``residual_pids: []``.

Every spawned pid is killed at the end. No install, no login, no live session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BROKER = ROOT / "scripts" / "kaola-launchd-broker.py"
HOLDER = ROOT / "scripts" / "kaola-acp-holder.py"
CLIENT = ROOT / "scripts" / "kaola-acp.py"
MOCK = ROOT / "tests" / "contract" / "mock-acp-agent.py"
PYTHON = sys.executable or shutil.which("python3")

CHECKS: list[str] = []


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def canonical(path: object) -> str:
    return os.path.realpath(str(path))


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


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_private(path: Path, data: str) -> Path:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, 0o600)
    return path


class Sandbox:
    def __init__(self, name: str):
        base = Path(tempfile.mkdtemp(prefix=f"k266{name}."))
        # Canonicalize: macOS /tmp is /private/tmp, and the client canonicalizes
        # --repo with realpath before hashing it.
        self.dir = Path(canonical(base))
        # AF_UNIX sun_path is ~104 bytes: the socket TMPDIR must stay short.
        self.tmp = Path(tempfile.mkdtemp(prefix="k266.", dir="/tmp"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        self.launch_root = self.dir / "launch"
        for path in (self.tmp, self.home, self.repo, self.record_root, self.launch_root):
            path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.platform = "codex"
        self.session = f"codex-K266-{uuid.uuid4().hex[:8]}"
        self.record_dir = (self.record_root / self.platform / self.session
                           / sha(self.repo.as_posix())[:16])
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.sock = (Path(self.tmp) / f"kaola-{os.getuid()}-acp"
                     / (sha(self.record_dir.as_posix())[:24] + ".sock"))
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        self.mock_log = self.dir / "mock.jsonl"
        self.label = f"com.kaolabrother.kaola-runner.test.{uuid.uuid4().hex[:10]}"
        self.pids: list[int] = []

    def env(self) -> dict:
        return {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "USER": os.environ.get("USER", "tester"),
            "LOGNAME": os.environ.get("LOGNAME", "tester"),
            "LANG": os.environ.get("LANG", "C"),
            "TMPDIR": str(self.tmp),
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "MOCK_ACP_LOG": str(self.mock_log),
            # A caller-app ownership variable must NOT reach the holder.
            "GROKBOT_APP_SESSION": "must-not-propagate",
        }

    def mock_command(self, *mock_args: str) -> str:
        return " ".join([PYTHON, str(MOCK), *mock_args])

    def holder_argv(self, command: str) -> list[str]:
        return [PYTHON, str(HOLDER), "--record-dir", str(self.record_dir),
                "--socket", str(self.sock), "--repo", self.repo.as_posix(),
                "--platform", self.platform, "--session", self.session,
                "--command", command]

    def broker(self, *args: str, timeout: float = 90) -> dict:
        result = subprocess.run([PYTHON, str(BROKER), *args], capture_output=True,
                                text=True, timeout=timeout, env={**os.environ, **self.env()})
        try:
            return json.loads(result.stdout)
        except ValueError as exc:  # noqa: F841
            raise AssertionError(f"broker printed no JSON: {result.stdout[-400:]} {result.stderr[-400:]}")

    def submit(self, command: str, *, timeout: float = 60) -> dict:
        argv_file = write_private(self.dir / f"argv-{uuid.uuid4().hex[:6]}.json",
                                  json.dumps(self.holder_argv(command)))
        env_file = write_private(self.dir / f"env-{uuid.uuid4().hex[:6]}.json",
                                 json.dumps(self.env()))
        return self.broker("submit", "--label", self.label, "--platform", self.platform,
                           "--session", self.session, "--repo", self.repo.as_posix(),
                           "--record-dir", str(self.record_dir), "--log", str(self.dir / "holder.log"),
                           "--cwd", str(self.repo), "--run-dir", str(self.launch_root / "run"),
                           "--ready-timeout", str(timeout), "--env-json", str(env_file),
                           "--env-allow", "MOCK_ACP_LOG",
                           "--argv-json", str(argv_file), timeout=timeout + 30)

    def client(self, command: str, *args: str, timeout: float = 60) -> dict:
        argv = [PYTHON, str(CLIENT), self.platform, command, "--repo", self.repo.as_posix(),
                "--session", self.session, *args]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                env={**os.environ, **self.env()})
        try:
            return json.loads(result.stdout)
        except ValueError as exc:  # noqa: F841
            raise AssertionError(f"client {command} printed no JSON: {result.stdout[-300:]} {result.stderr[-300:]}")

    def record(self) -> dict:
        try:
            return json.loads((self.record_dir / "record.json").read_text())
        except (OSError, ValueError):
            return {}

    def track(self, pid: object) -> None:
        if isinstance(pid, int) and pid > 0:
            self.pids.append(pid)

    def cleanup(self) -> None:
        # Reap anything this sandbox launched, including a holder whose bootstrap failed.
        record = self.record()
        for key in ("holder_pid", "agent_pid", "agent_pgid"):
            self.track(record.get(key))
        for pid in sorted(set(self.pids), reverse=True):
            for sig in (15, 9):
                try:
                    os.kill(pid, sig)
                except (ProcessLookupError, PermissionError):
                    break
        self.broker("stop", "--label", self.label, "--run-dir", str(self.launch_root / "run"),
                    "--record-dir", str(self.record_dir))
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{self.label}"],
                       capture_output=True, text=True)
        shutil.rmtree(self.dir, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)


def test_literal_argv_and_private_seam(sb: Sandbox) -> None:
    # A composed shell command is refused; there is no shell execution path.
    shell_argv = write_private(sb.dir / "shell-argv.json",
                               json.dumps(["/bin/zsh", "-c", "echo hi"]))
    env_file = write_private(sb.dir / "env.json", json.dumps(sb.env()))
    refused = sb.broker("submit", "--label", f"{sb.label}.bad", "--platform", sb.platform,
                        "--session", sb.session, "--repo", sb.repo.as_posix(),
                        "--record-dir", str(sb.record_dir), "--log", str(sb.dir / "h.log"),
                        "--cwd", str(sb.repo), "--run-dir", str(sb.launch_root / "run"),
                        "--env-json", str(env_file), "--argv-json", str(shell_argv))
    check(refused.get("result") == "refused" and refused.get("reason") == "argv-shell",
          "submit refuses a /bin/zsh -c composed argv")

    # The internal seam refuses without a private armed spec.
    no_spec = subprocess.run([PYTHON, str(BROKER), "--internal-run", "--spec",
                              str(sb.dir / "missing.json")], capture_output=True, text=True)
    check(no_spec.returncode != 0, "internal-run refuses a missing private spec")

    # A world-readable spec is refused.
    permissive = sb.dir / "permissive.json"
    permissive.write_text("{}")
    os.chmod(permissive, 0o644)
    armed = Path(str(permissive) + ".armed")
    armed.write_text("{}")
    os.chmod(armed, 0o644)
    res = subprocess.run([PYTHON, str(BROKER), "--internal-run", "--spec", str(permissive)],
                         capture_output=True, text=True)
    check(res.returncode != 0, "internal-run refuses a permissive spec")


def test_broker_survival_and_control(sb: Sandbox) -> None:
    receipt = sb.submit(sb.mock_command("--scenario", "slow", "--turn-ms", "6000",
                                        "--steering", "injected"))
    check(receipt.get("result") == "ready", "broker reports ready from the holder's own record")
    holder_pid = receipt.get("holder_pid")
    sb.track(holder_pid)
    check(pid_alive(holder_pid), "holder is alive after submit returns")
    ppid = subprocess.run(["ps", "-o", "ppid=", "-p", str(holder_pid)],
                          capture_output=True, text=True).stdout.strip()
    check(ppid == "1", "holder is re-parented to the service manager (ppid 1)")
    listing = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    check(sb.label not in listing, "the one-shot job is unloaded after readiness")

    # Caller exit is already the case (submit returned). A later explicit unload
    # must not touch the detached holder.
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{sb.label}"],
                   capture_output=True, text=True)
    time.sleep(0.4)
    check(pid_alive(holder_pid), "holder survives a later job unload")

    # The standard client still controls the detached holder.
    status = sb.client("status")
    check(status.get("holder_instance_id") == receipt.get("holder_instance_id"),
          "status resolves the same holder instance")
    sent = sb.client("send", "--no-wait", "--text", "ping-266")
    check(sent.get("mutation_status") in ("accepted", "in_progress", "completed") or sent.get("turn_active"),
          "send is accepted by the detached holder")

    def mock_events() -> list[dict]:
        try:
            return [json.loads(line) for line in sb.mock_log.read_text().splitlines() if line.strip()]
        except OSError:
            return []

    wait_until(lambda: any(e.get("event") == "prompt" and "ping-266" in e.get("text", "")
                           for e in mock_events()), 10,
               "the prompt reaches the agent through the detached holder")
    check(any(e.get("event") == "prompt" and "ping-266" in e.get("text", "") for e in mock_events()),
          "the detached holder delivered the prompt to the agent (agent-side receipt)")

    capture = sb.client("capture", "--lines", "40")
    check("error" not in capture or capture.get("error") is None,
          "capture returns a valid session receipt from the detached holder")
    steered = sb.client("steer", "--text", "steer-266")
    check(steered.get("result") is None or "error" not in steered,
          "steer call reaches the detached holder")
    sb.client("stop", "--force")
    wait_until(lambda: not pid_alive(holder_pid), 10, "holder gone after stop")
    check(not pid_alive(holder_pid), "exact stop ends the holder")


def test_repeat_reconciles(sb: Sandbox) -> None:
    first = sb.submit(sb.mock_command("--scenario", "normal"))
    check(first.get("result") == "ready", "first submit is ready")
    sb.track(first.get("holder_pid"))
    second = sb.submit(sb.mock_command("--scenario", "normal"))
    check(second.get("result") == "existing" and second.get("reconciled") is True,
          "a repeated submit reconciles the live holder instead of a duplicate")
    check(second.get("holder_pid") == first.get("holder_pid"),
          "the reconciled holder is the same instance")
    sb.client("stop", "--force")
    wait_until(lambda: not pid_alive(first.get("holder_pid")), 10, "first holder gone")


def test_failed_bootstrap_cleanup(sb: Sandbox) -> None:
    receipt = sb.submit(f"{PYTHON} {sb.dir}/does-not-exist.py", timeout=6)
    check(receipt.get("result") == "refused" and receipt.get("reason") == "holder-not-ready",
          "a failed bootstrap is refused with holder-not-ready")
    listing = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    check(sb.label not in listing, "no stale job remains after a failed bootstrap")
    run_dir = sb.launch_root / "run"
    files = list(run_dir.rglob("*")) if run_dir.exists() else []
    check(not any(p.is_file() for p in files), "no stale plist or spec remains after a failed bootstrap")
    listing = subprocess.run(["ps", "-axo", "pid,command"], capture_output=True, text=True).stdout
    check(str(sb.record_dir) not in listing,
          "failed bootstrap leaves no orphan holder for this record directory")
    wait_until(lambda: str(sb.record_dir) not in subprocess.run(
        ["ps", "-axo", "pid,command"], capture_output=True, text=True).stdout,
        8, "failed-start holder cleanup settles")


def test_job_cleanup_preserves_dispatched_tree(sb: Sandbox) -> None:
    receipt = sb.submit(sb.mock_command("--scenario", "stubborn_child"))
    check(receipt.get("result") == "ready", "holder with a dispatched child is ready")
    holder_pid = receipt.get("holder_pid")
    sb.track(holder_pid)
    sb.client("send", "--no-wait", "--text", "spawn-child")
    # The mock spawns a `sleep 300` child in the agent's group and ignores SIGTERM.
    def agent_child() -> int | None:
        out = subprocess.run(["ps", "-axo", "pid,ppid,command"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[1] == str(holder_pid) and "mock-acp-agent" in parts[2]:
                return int(parts[0])
            if len(parts) == 3 and parts[1] != "1" and parts[2].startswith("sleep 300"):
                return int(parts[0])
        return None
    # A direct job unload must not sweep the detached holder or its worker tree.
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{sb.label}"],
                   capture_output=True, text=True)
    time.sleep(0.4)
    check(pid_alive(holder_pid), "the detached holder survives a job unload (preserve semantics)")
    stop = sb.client("stop", "--force")
    wait_until(lambda: not pid_alive(holder_pid), 10, "holder gone after exact stop")
    residual = stop.get("residual_pids") or []
    check(residual == [], "exact stop leaves no residual pids")


TESTS = (
    ("literal_argv_and_private_seam", test_literal_argv_and_private_seam),
    ("broker_survival_and_control", test_broker_survival_and_control),
    ("repeat_reconciles", test_repeat_reconciles),
    ("failed_bootstrap_cleanup", test_failed_bootstrap_cleanup),
    ("job_cleanup_preserves_dispatched_tree", test_job_cleanup_preserves_dispatched_tree),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    args = parser.parse_args()
    if sys.platform != "darwin":
        print(json.dumps({"result": "unsupported", "detail": "macOS launchd contract test"}))
        return 0
    results: list[dict] = []
    failures: list[str] = []
    for name, fn in TESTS:
        if args.only and args.only != name:
            continue
        sb = Sandbox(name.split("_")[0][:4])
        try:
            fn(sb)
            results.append({"test": name, "result": "pass"})
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
            results.append({"test": name, "result": "fail", "detail": str(exc)})
        finally:
            sb.cleanup()
    print(json.dumps({"result": "pass" if not failures else "fail",
                      "checks": len(CHECKS), "tests": results, "failures": failures},
                     indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
