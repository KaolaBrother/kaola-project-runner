#!/usr/bin/env python3
"""Issue #266 focused contract: shared outside-caller launcher (helper level).

Model-free. It launches a real ACP holder through ``scripts/kaola-launchd-broker.py``
with the existing mock ACP agent, and proves:

* broker exit and job unload leave the detached holder alive (re-parented);
* the standard client still controls it (status/send/capture/steer/stop);
* repeat submit reconciles the verified holder; a foreign record/PID is rejected;
* a concurrent running job for the session is reconciled, never killed;
* a failed bootstrap cleans up its own holder and leaves no stale job or file;
* the spawned holder is recorded in the outer agent's child record;
* failed-start and preserve semantics with raw per-operation evidence.

Every spawned pid is killed at the end. No install, no login, no live session.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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


def load_broker_module():
    spec = importlib.util.spec_from_file_location("kaola_launchd_broker", BROKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_private(path: Path, data: str) -> Path:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, 0o600)
    return path


class Sandbox:
    def __init__(self, name: str, space: bool = False):
        base = Path(tempfile.mkdtemp(prefix=f"k266{name}."))
        self.dir = Path(canonical(base))
        self.tmp = Path(tempfile.mkdtemp(prefix="k266.", dir="/tmp"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / ("re cords" if space else "records")
        self.launch_base = self.dir / "launch-base"
        for path in (self.home, self.repo, self.record_root, self.launch_base):
            path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.platform = "codex"
        self.session = f"codex-K266-{uuid.uuid4().hex[:8]}"
        self.record_dir = (self.record_root / self.platform / self.session
                           / sha(self.repo.as_posix())[:16])
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.sock = (Path("/tmp") / f"kaola-{os.getuid()}-acp"
                     / (sha(self.record_dir.as_posix())[:24] + ".sock"))
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        self.label = LABEL_PREFIX + sha(f"{self.platform}\0{self.session}\0{self.repo.as_posix()}")[:16]
        self.mock_log = self.dir / "mock.jsonl"
        self.child_record = self.dir / "children.jsonl"
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
            "GROKBOT_APP_SESSION": "must-not-propagate",
        }

    def mock_command(self, *mock_args: str) -> str:
        return " ".join([PYTHON, str(MOCK), *mock_args])

    def holder_argv(self, command: str) -> list[str]:
        return [PYTHON, str(HOLDER), "--record-dir", str(self.record_dir),
                "--socket", str(self.sock), "--repo", self.repo.as_posix(),
                "--platform", self.platform, "--session", self.session,
                "--command", command]

    def broker(self, *args: str, timeout: float = 90, env: dict | None = None) -> dict:
        result = subprocess.run([PYTHON, str(BROKER), *args], capture_output=True,
                                text=True, timeout=timeout,
                                env=(env if env is not None else self.env()))
        try:
            return json.loads(result.stdout)
        except ValueError as exc:  # noqa: F841
            raise AssertionError(f"broker printed no JSON: {result.stdout[-400:]} {result.stderr[-400:]}")

    def submit(self, command: str, *, timeout: float = 60, child_record: bool = False,
               backend: str | None = None) -> dict:
        argv_file = write_private(self.dir / f"argv-{uuid.uuid4().hex[:6]}.json",
                                  json.dumps(self.holder_argv(command)))
        args = ["submit", "--platform", self.platform, "--session", self.session,
                "--repo", self.repo.as_posix(), "--record-dir", str(self.record_dir),
                "--log", str(self.dir / "holder.log"), "--cwd", str(self.repo),
                "--run-base", str(self.launch_base), "--ready-timeout", str(timeout),
                "--env-allow", "MOCK_ACP_LOG", "--argv-json", str(argv_file)]
        if backend:
            args += ["--backend", backend]
        if child_record:
            args += ["--child-record", str(self.child_record)]
        return self.broker(*args, timeout=timeout + 30)

    def stop(self) -> dict:
        return self.broker("cleanup", "--platform", self.platform, "--session", self.session,
                           "--repo", self.repo.as_posix(), "--run-base", str(self.launch_base),
                           "--record-dir", str(self.record_dir))

    def client(self, command: str, *args: str, timeout: float = 60) -> dict:
        argv = [PYTHON, str(CLIENT), self.platform, command, "--repo", self.repo.as_posix(),
                "--session", self.session, *args]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                env=self.env())
        try:
            return json.loads(result.stdout)
        except ValueError as exc:  # noqa: F841
            raise AssertionError(f"client {command} printed no JSON: {result.stdout[-300:]} {result.stderr[-300:]}")

    def record(self) -> dict:
        try:
            return json.loads((self.record_dir / "record.json").read_text())
        except (OSError, ValueError):
            return {}

    def mock_events(self) -> list[dict]:
        try:
            return [json.loads(line) for line in self.mock_log.read_text().splitlines() if line.strip()]
        except OSError:
            return []

    def track(self, pid: object) -> None:
        if isinstance(pid, int) and pid > 0:
            self.pids.append(pid)

    def cleanup(self) -> None:
        record = self.record()
        for key in ("holder_pid", "agent_pid", "agent_pgid"):
            self.track(record.get(key))
        for pid in sorted(set(self.pids), reverse=True):
            for sig in (15, 9):
                try:
                    os.kill(pid, sig)
                except (ProcessLookupError, PermissionError):
                    break
        self.stop()
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{self.label}"],
                       capture_output=True, text=True)
        shutil.rmtree(self.dir, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)


# ------------------------------------------------------------------ helper-level tests


def test_literal_argv_structure(sb: Sandbox) -> None:
    module = load_broker_module()
    # A shell argv is refused (first element is a shell).
    wrote = write_private(sb.dir / "shell-argv.json", json.dumps(["/bin/zsh", "-c", "echo hi"]))
    refused = sb.broker("submit", "--platform", sb.platform, "--session", sb.session,
                        "--repo", sb.repo.as_posix(), "--record-dir", str(sb.record_dir),
                        "--log", str(sb.dir / "h.log"), "--cwd", str(sb.repo),
                        "--run-base", str(sb.launch_base), "--argv-json", str(wrote))
    check(refused.get("reason") == "argv-shell", "submit refuses a shell-first argv",
          receipt=refused)
    # A non-holder argv is refused by the known-structure check.
    wrote = write_private(sb.dir / "svc-argv.json", json.dumps([PYTHON, "-m", "http.server"]))
    refused = sb.broker("submit", "--platform", sb.platform, "--session", sb.session,
                        "--repo", sb.repo.as_posix(), "--record-dir", str(sb.record_dir),
                        "--log", str(sb.dir / "h.log"), "--cwd", str(sb.repo),
                        "--run-base", str(sb.launch_base), "--argv-json", str(wrote))
    check(refused.get("reason") == "argv-not-holder",
          "submit refuses an argv that is not the holder structure", receipt=refused)
    # The private seam refuses a missing/permissive spec.
    res = subprocess.run([PYTHON, str(BROKER), "--internal-run", "--spec",
                          str(sb.dir / "missing.json")], capture_output=True, text=True)
    check(res.returncode != 0, "internal-run refuses a missing private spec")
    permissive = sb.dir / "p.json"
    permissive.write_text("{}")
    os.chmod(permissive, 0o644)
    armed = Path(str(permissive) + ".armed")
    armed.write_text("{}")
    os.chmod(armed, 0o644)
    res = subprocess.run([PYTHON, str(BROKER), "--internal-run", "--spec", str(permissive)],
                         capture_output=True, text=True)
    check(res.returncode != 0, "internal-run refuses a permissive spec")


def test_foreign_identity_rejected(sb: Sandbox) -> None:
    module = load_broker_module()
    # A foreign live PID with a matching-looking but identity-less record is not a holder.
    fake = subprocess.Popen(["sleep", "300"])
    sb.track(fake.pid)
    write_private(sb.record_dir / "record.json", json.dumps({
        "platform": sb.platform, "session": sb.session, "repo": sb.repo.as_posix(),
        "holder_pid": fake.pid, "state": "ready"}))
    check(module.verified_holder(sb.record_dir, sb.platform, sb.session, sb.repo.as_posix()) is None,
          "verified_holder rejects a foreign PID with no holder/ACP identity",
          fake_pid=fake.pid, record=sb.record())
    # submit does not reconcile that foreign record; it launches a real holder.
    receipt = sb.submit(sb.mock_command("--scenario", "normal"))
    check(receipt.get("result") == "ready", "submit launches a real holder over a foreign record",
          receipt=receipt)
    check(receipt.get("holder_pid") != fake.pid, "the new holder is not the foreign PID")
    sb.track(receipt.get("holder_pid"))
    check(pid_alive(fake.pid), "the foreign PID was not signalled or killed")
    sb.client("stop", "--force")
    wait_until(lambda: not pid_alive(receipt.get("holder_pid")), 10, "holder gone")


def test_reconcile_and_running_job(sb: Sandbox) -> None:
    first = sb.submit(sb.mock_command("--scenario", "normal"))
    check(first.get("result") == "ready", "first submit is ready")
    sb.track(first.get("holder_pid"))
    second = sb.submit(sb.mock_command("--scenario", "normal"))
    check(second.get("result") == "existing" and second.get("reconciled") is True,
          "a repeated submit reconciles the verified holder")
    check(second.get("holder_pid") == first.get("holder_pid"),
          "the reconciled holder is the same instance")
    sb.client("stop", "--force")
    wait_until(lambda: not pid_alive(first.get("holder_pid")), 10, "first holder gone")

    # A concurrent running job for this session is not killed or overwritten.
    plist = sb.dir / "concurrent.plist"
    plist.write_bytes(__import__("plistlib").dumps({
        "Label": sb.label, "ProgramArguments": ["/bin/sleep", "300"],
        "RunAtLoad": True, "KeepAlive": False}))
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)],
                   capture_output=True, text=True)
    try:
        wait_until(lambda: sb.label in subprocess.run(["launchctl", "list"], capture_output=True,
                                                      text=True).stdout, 5, "concurrent job loaded")
        refused = sb.submit(sb.mock_command("--scenario", "normal"), timeout=5)
        check(refused.get("reason") == "launch-in-progress",
              "submit refuses rather than killing a concurrent running job", receipt=refused)
        listing = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
        check(sb.label in listing, "the concurrent job is still loaded and alive")
    finally:
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{sb.label}"],
                       capture_output=True, text=True)


def test_survival_control_and_child_record(sb: Sandbox) -> None:
    receipt = sb.submit(sb.mock_command("--scenario", "slow", "--turn-ms", "6000",
                                        "--steering", "injected"), child_record=True)
    check(receipt.get("result") == "ready", "broker reports ready from the verified holder")
    holder_pid = receipt.get("holder_pid")
    sb.track(holder_pid)
    ppid = subprocess.run(["ps", "-o", "ppid=", "-p", str(holder_pid)],
                          capture_output=True, text=True).stdout.strip()
    check(ppid == "1", "holder is re-parented to the service manager (ppid 1)", holder_pid=holder_pid)
    check(sb.label not in subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout,
          "the one-shot job is unloaded after readiness")

    # The spawned holder is in the outer agent's child record (dispatcher ownership).
    entries = [json.loads(l) for l in sb.child_record.read_text().splitlines() if l.strip()] \
        if sb.child_record.exists() else []
    check(any(e.get("pid") == holder_pid and e.get("pgid") == holder_pid for e in entries),
          "the outside holder is recorded in the outer child record", child_record=entries)

    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{sb.label}"],
                   capture_output=True, text=True)
    time.sleep(0.4)
    check(pid_alive(holder_pid), "holder survives a later job unload")

    status = sb.client("status")
    check(status.get("holder_instance_id") == receipt.get("holder_instance_id"),
          "status resolves the same holder instance", status_instance=status.get("holder_instance_id"))
    sent = sb.client("send", "--no-wait", "--text", "ping-266")
    check(sent.get("mutation_status") in ("accepted", "in_progress", "completed") or sent.get("turn_active"),
          "send is accepted by the detached holder", send=sent.get("mutation_status"))
    wait_until(lambda: any(e.get("event") == "prompt" and "ping-266" in e.get("text", "")
                           for e in sb.mock_events()), 10, "the prompt reaches the agent")
    check(any(e.get("event") == "prompt" and "ping-266" in e.get("text", "") for e in sb.mock_events()),
          "the detached holder delivered the prompt to the agent (agent-side receipt)")
    capture = sb.client("capture", "--lines", "40")
    check(not capture.get("error"), "capture returns a valid session receipt", capture_error=capture.get("error"))
    steered = sb.client("steer", "--text", "steer-266")
    check(not steered.get("error"), "the steer call is not an error receipt", steer=steered)
    wait_until(lambda: any(e.get("event") == "steering" and "steer-266" in e.get("text", "")
                           for e in sb.mock_events()), 10, "the steer reaches the agent")
    stop = sb.client("stop", "--force")
    check("residual_pids" in stop and stop["residual_pids"] == [],
          "exact stop proves no residual pids", stop={k: stop.get(k) for k in ("stopped", "residual_pids")})
    wait_until(lambda: not pid_alive(holder_pid), 10, "holder gone after stop")


def test_failed_start_cleanup(sb: Sandbox) -> None:
    receipt = sb.submit(f"{PYTHON} {sb.dir}/does-not-exist.py", timeout=6)
    check(receipt.get("reason") == "holder-not-ready", "a failed start is refused",
          receipt=receipt)
    check(sb.label not in subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout,
          "no stale job remains after a failed start")
    wait_until(lambda: str(sb.record_dir) not in subprocess.run(
        ["ps", "-axo", "pid,command"], capture_output=True, text=True).stdout,
        8, "failed-start holder/agent group is gone")
    check(str(sb.record_dir) not in subprocess.run(
        ["ps", "-axo", "pid,command"], capture_output=True, text=True).stdout,
        "failed start leaves no orphan holder or agent")
    check(not (sb.record_dir / "launch.broker.json").exists(),
          "the readiness receipt is consumed, not left behind")
    base = sb.launch_base
    stale = list(base.rglob("spec.json")) + list(base.rglob("*.plist"))
    check(stale == [], "no stale spec or plist remains", stale=[str(p) for p in stale])


def test_spaces_in_record_path(sb: Sandbox) -> None:
    check(" " in str(sb.record_dir), "the record path under test contains a space",
          record_dir=str(sb.record_dir))
    receipt = sb.submit(sb.mock_command("--scenario", "normal"))
    check(receipt.get("result") == "ready",
          "a record path with a space still reaches a verified ready holder", receipt=receipt)
    holder_pid = receipt.get("holder_pid")
    sb.track(holder_pid)
    check(pid_alive(holder_pid), "the holder with a spaced record path is alive")
    sb.client("stop", "--force")
    wait_until(lambda: not pid_alive(holder_pid), 10, "spaced-path holder gone")


def test_systemd_user_refusal(sb: Sandbox) -> None:
    receipt = sb.submit(sb.mock_command("--scenario", "normal"), backend="systemd-user", timeout=5)
    check(receipt.get("result") == "refused"
          and receipt.get("reason") == "launch-backend-unsupported",
          "a forced systemd-user backend on macOS refuses cleanly, with no OS call",
          receipt=receipt)
    check(receipt.get("holder_may_exist") is False,
          "the refusal reports no holder may exist")
    stale = list(sb.launch_base.rglob("*"))
    check(stale == [], "the refused backend leaves no run-dir artifact", stale=[str(p) for p in stale])


def test_recovery_source_probes(sb: Sandbox) -> None:
    module = load_broker_module()

    class FakeProc:
        pid = 2 ** 30
        def poll(self): return 0
        def wait(self, timeout=None): return 0

    original_socket = module.socket_op
    module.socket_op = lambda *a, **k: {}
    try:
        result = module._stop_owned_holder(Path("/nonexistent.sock"), "inst", FakeProc())
    finally:
        module.socket_op = original_socket
    check(result["holder_may_exist"] is True and result["host_session_stopped"] is False
          and result["residual_pids"] is None,
          "an absent stop reply keeps native/worker custody unknown", result=result)

    label = module.label_for(sb.platform, sb.session, sb.repo.as_posix())
    run_dir = sb.launch_base / label
    attempt = run_dir / "attempt-fixture"
    attempt.mkdir(parents=True, exist_ok=True)
    (attempt / "spec.json").write_text("{}")
    original_state = module.os_job_state
    original_owns = module.os_job_owns
    try:
        module.os_job_state = lambda backend, label: "unknown"
        module.os_job_owns = lambda *a: False
        reason = None
        try:
            module.do_cleanup(argparse.Namespace(backend="launchd", platform=sb.platform,
                              session=sb.session, repo=sb.repo.as_posix(),
                              run_base=str(sb.launch_base), record_dir=str(sb.record_dir)))
        except module.BrokerError as exc:
            reason = exc.code
        check(reason == "job-state-unknown",
              "cleanup leaves an unknown manager state untouched", reason=reason)
        check(attempt.exists(), "cleanup keeps attempt evidence on an unknown state")

        module.os_job_state = lambda backend, label: "exited"
        reason = None
        try:
            module.do_cleanup(argparse.Namespace(backend="launchd", platform=sb.platform,
                              session=sb.session, repo=sb.repo.as_posix(),
                              run_base=str(sb.launch_base), record_dir=str(sb.record_dir)))
        except module.BrokerError as exc:
            reason = exc.code
        check(reason == "job-not-owned",
              "cleanup does not unload a nonowned exited job", reason=reason)

        # Absent manager with the SAME matching live native agent: cleanup must not
        # erase the sole failed-attempt evidence.
        agent = subprocess.Popen(["sleep", "300"])
        sb.track(agent.pid)
        write_private(sb.record_dir / "record.json", json.dumps({
            "platform": sb.platform, "session": sb.session, "repo": sb.repo.as_posix(),
            "holder_pid": 2 ** 30, "agent_pid": agent.pid, "agent_pgid": agent.pid,
            "state": "ready"}))
        module.os_job_state = lambda backend, label: "absent"
        reason = None
        try:
            module.do_cleanup(argparse.Namespace(backend="launchd", platform=sb.platform,
                              session=sb.session, repo=sb.repo.as_posix(),
                              run_base=str(sb.launch_base), record_dir=str(sb.record_dir)))
        except module.BrokerError as exc:
            reason = exc.code
        check(reason == "attempt-unresolved",
              "cleanup keeps a failed attempt whose native agent is alive", reason=reason)
        check(attempt.exists(), "cleanup keeps the unresolved attempt artifact")

        # After the exact identities are gone, cleanup removes the artifact.
        os.kill(agent.pid, 9)
        wait_until(lambda: not pid_alive(agent.pid), 5, "fixture agent gone")
        cleaned = module.do_cleanup(argparse.Namespace(
            backend="launchd", platform=sb.platform, session=sb.session,
            repo=sb.repo.as_posix(), run_base=str(sb.launch_base),
            record_dir=str(sb.record_dir)))
        check(cleaned.get("result") == "cleaned" and not attempt.exists()
              and cleaned.get("unresolved_effect") is False,
              "cleanup removes the attempt after the exact identities are gone", cleaned=cleaned)
    finally:
        module.os_job_state = original_state
        module.os_job_owns = original_owns


def test_live_agent_custody(sb: Sandbox) -> None:
    """A dead recorded holder with a live recorded native agent stays unresolved."""
    module = load_broker_module()
    agent = subprocess.Popen(["sleep", "300"])
    sb.track(agent.pid)
    write_private(sb.record_dir / "record.json", json.dumps({
        "platform": sb.platform, "session": sb.session, "repo": sb.repo.as_posix(),
        "holder_pid": 2 ** 30, "agent_pid": agent.pid, "agent_pgid": agent.pid,
        "state": "ready"}))
    check(module._own_holder_effect_remains(sb.record_dir, sb.platform, sb.session,
                                            sb.repo.as_posix()) is True,
          "a live recorded native agent keeps the own effect unresolved")
    original_state = module.os_job_state
    original_owns = module.os_job_owns
    module.os_job_state = lambda backend, label: "absent"
    module.os_job_owns = lambda *a: False
    try:
        unresolved, state = module._reconcile_failed_attempt(
            "launchd", "fixture-label", sb.dir / "spec.json",
            argparse.Namespace(ready_timeout=1.0), sb.record_dir, sb.platform,
            sb.session, sb.repo.as_posix())
    finally:
        module.os_job_state = original_state
        module.os_job_owns = original_owns
    check(unresolved is True and state == "absent",
          "reconcile keeps the attempt unresolved when the native agent is alive",
          unresolved=unresolved, state=state)
    # With both recorded identities dead, the effect is resolved.
    os.kill(agent.pid, 9)
    wait_until(lambda: not pid_alive(agent.pid), 5, "fixture agent gone")
    check(module._own_holder_effect_remains(sb.record_dir, sb.platform, sb.session,
                                            sb.repo.as_posix()) is False,
          "both recorded identities dead resolves the own effect")


TESTS = (
    ("literal_argv_structure", test_literal_argv_structure, False),
    ("foreign_identity_rejected", test_foreign_identity_rejected, False),
    ("reconcile_and_running_job", test_reconcile_and_running_job, False),
    ("survival_control_and_child_record", test_survival_control_and_child_record, False),
    ("failed_start_cleanup", test_failed_start_cleanup, False),
    ("spaces_in_record_path", test_spaces_in_record_path, True),
    ("systemd_user_refusal", test_systemd_user_refusal, False),
    ("recovery_source_probes", test_recovery_source_probes, False),
    ("live_agent_custody", test_live_agent_custody, False),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--evidence-out")
    args = parser.parse_args()
    if sys.platform != "darwin":
        print(json.dumps({"result": "unsupported", "detail": "macOS launchd contract test"}))
        return 0
    results: list[dict] = []
    failures: list[str] = []
    for name, fn, space in TESTS:
        if args.only and args.only != name:
            continue
        sb = Sandbox(name.split("_")[0][:4], space=space)
        try:
            fn(sb)
            results.append({"test": name, "result": "pass"})
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
            results.append({"test": name, "result": "fail", "detail": str(exc)})
        finally:
            sb.cleanup()
    payload = {"result": "pass" if not failures else "fail", "checks": len(CHECKS),
               "tests": results, "failures": failures, "evidence": EVIDENCE}
    if args.evidence_out:
        Path(args.evidence_out).write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
