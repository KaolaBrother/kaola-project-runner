#!/usr/bin/env python3
"""Shared outside-caller launcher for the Runner ACP holder (issue #266).

The Runner normally spawns the holder as a child of whatever shell ran
``runtime-tmux.sh start``. When that shell belongs to a desktop app, the holder
is a descendant of the app and can die with the app. This helper launches the
holder under the per-user service manager instead:

* **submit** builds a one-shot, per-user job whose only job is to run the
  internal startup and exit. The holder is spawned with ``start_new_session``,
  so it is re-parented to the service manager and survives the caller, the
  short-lived job, and a later job unload.
* **internal-run** is that job body. It validates a private, mode-600 armed spec,
  builds the holder environment from an explicit map only, spawns the holder
  with a literal argv, waits for the holder's own ``ready`` record, writes a
  readiness receipt, and exits.
* **stop** unloads only the owned job and removes its files.

Hard rules implemented here:

* ProgramArguments is a literal argv list. No shell, no ``-c``, no ``eval``.
* The internal path is refused unless a private armed spec (mode 600, owner uid)
  exists. There is no environment-variable or other global authority bypass.
* The holder environment is an explicit minimal map. The full inherited
  environment and credentials are never written to the plist or any log.
* ``KeepAlive`` is false; there is no login/boot/crash restart and no separate
  scheduler or registry.
* The job PID is never treated as the holder PID. Readiness comes from the
  holder's own record.

macOS (launchd) is implemented. Linux user systemd and other systems have a
measured disposition; see ``backend_for``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "kaola-launch-broker/1"
NONCE_BYTES = 16
DEFAULT_READY_TIMEOUT = 90.0
RECORD_NAME = "record.json"
RECEIPT_NAME = "launch.broker.json"

# The only environment names that may reach the holder. Everything else from the
# caller is dropped, so no caller-app ownership variable and no unlisted
# credential is forwarded. ``KAOLA_*`` carries dispatcher/child ownership.
PASS_ALWAYS = (
    "HOME", "USER", "LOGNAME", "SHELL", "PATH", "TMPDIR", "LANG", "LC_ALL",
)
PASS_PROXY = (
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
)
SHELL_BASENAMES = {"sh", "bash", "zsh", "dash", "fish", "ksh", "tcsh", "csh"}


class BrokerError(Exception):
    """A refusal with a stable code and an actionable message."""

    def __init__(self, code: str, message: str, **facts: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.facts = facts

    def receipt(self) -> dict:
        return {"schema": SCHEMA, "result": "refused", "reason": self.code,
                "detail": self.message, **self.facts}


# --------------------------------------------------------------------------- util


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


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def owner_uid() -> int:
    return os.getuid()


def assert_secure_file(path: Path) -> None:
    """Refuse a spec/armed file that is not a private, owned, regular file."""
    try:
        st = path.lstat()
    except OSError as exc:
        raise BrokerError("spec-missing", f"private spec is not present: {path}") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise BrokerError("spec-not-regular", f"private spec is not a regular file: {path}")
    if st.st_uid != owner_uid():
        raise BrokerError("spec-foreign-owner", f"private spec is not owned by this user: {path}")
    if stat.S_IMODE(st.st_mode) & 0o077:
        raise BrokerError("spec-permissive", f"private spec mode is not 600: {path}")


def run_dir_for(base: Path, label: str) -> Path:
    return base / label


# --------------------------------------------------------------------------- env


def filter_env(env: dict, extra_keys: set[str] | None = None) -> dict:
    """Keep only the minimal, allowed environment for the holder."""
    extra = extra_keys or set()
    kept: dict[str, str] = {}
    for key, value in env.items():
        if not isinstance(value, str):
            continue
        if key in PASS_ALWAYS or key in PASS_PROXY or key.startswith("KAOLA_") or key in extra:
            kept[key] = value
    return kept


def check_literal_argv(argv: list[str]) -> None:
    """Refuse any composed shell command or prompt on the launch path."""
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise BrokerError("argv-empty", "ProgramArguments must be a non-empty literal argv list")
    first = os.path.basename(argv[0])
    if first in SHELL_BASENAMES:
        raise BrokerError("argv-shell", f"ProgramArguments must not start a shell ({first}); "
                                        "pass a literal argv list, never a composed command")
    for item in argv:
        if item in ("-c", "-lc", "-ic", "/bin/zsh", "/bin/bash", "/bin/sh"):
            raise BrokerError("argv-shell-flag", f"ProgramArguments must not contain {item!r}")


# --------------------------------------------------------------------------- holder record


def holder_record(record_dir: Path) -> dict:
    return read_json(record_dir / RECORD_NAME)


def holder_ready(record: dict, platform: str, session: str, repo: str) -> bool:
    """Ready means the holder's own record says ready with a live holder pid."""
    if not record:
        return False
    if record.get("platform") != platform or record.get("session") != session:
        return False
    if record.get("repo") != repo:
        return False
    if record.get("state") != "ready":
        return False
    return pid_alive(record.get("holder_pid"))


def ready_facts(record: dict) -> dict:
    return {
        "holder_pid": record.get("holder_pid"),
        "holder_instance_id": record.get("holder_instance_id"),
        "acp_session_id": record.get("acp_session_id"),
        "agent_pid": record.get("agent_pid"),
        "platform": record.get("platform"),
        "session": record.get("session"),
        "repo": record.get("repo"),
        "state": record.get("state"),
    }


# --------------------------------------------------------------------------- macOS launchd backend


def launchd_label(platform: str, session: str, repo: str) -> str:
    token = sha(f"{platform}\0{session}\0{repo}")[:16]
    return f"com.kaolabrother.kaola-runner.launch.{token}"


def launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/launchctl", *args], capture_output=True, text=True, timeout=30)


def launchd_bootstrap(label: str, plist_path: Path) -> None:
    domain = f"gui/{owner_uid()}"
    # Drop any stale job with this exact label first (owned label only).
    launchctl("bootout", f"{domain}/{label}")
    result = launchctl("bootstrap", domain, str(plist_path))
    if result.returncode != 0:
        raise BrokerError("bootstrap-failed",
                          f"launchctl bootstrap failed: {result.stderr.strip() or result.stdout.strip()}",
                          label=label, plist=str(plist_path))


def launchd_bootout(label: str) -> None:
    launchctl("bootout", f"gui/{owner_uid()}/{label}")


def launchd_job_running(label: str) -> bool:
    """True when the labeled job is currently running (a live PID column)."""
    out = launchctl("list").stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == label:
            return parts[0].isdigit()
    return False


def wait_job_stopped(label: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not launchd_job_running(label):
            return
        time.sleep(0.1)


# --------------------------------------------------------------------------- systemd / other


def systemd_user_available() -> tuple[bool, str]:
    """Measured availability of a user systemd domain; no fallback is implied."""
    if not shutil.which("systemctl"):
        return False, "systemctl is not on PATH"
    try:
        result = subprocess.run(["systemctl", "--user", "is-system-running"],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"systemctl --user probe failed: {exc}"
    # "running", "degraded", "maintenance" all mean a live user manager.
    if result.stdout.strip() in ("running", "degraded", "maintenance"):
        return True, result.stdout.strip()
    return False, result.stdout.strip() or result.stderr.strip() or "no user manager"


def backend_for(force: str | None = None) -> tuple[str, str]:
    """Return (backend, detail). Never silently falls back to a direct spawn."""
    if force:
        return force, "forced by caller"
    if sys.platform == "darwin":
        return "launchd", "macOS"
    if sys.platform.startswith("linux"):
        ok, detail = systemd_user_available()
        return ("systemd-user" if ok else "unsupported"), detail
    return "unsupported", f"no supported service manager for {sys.platform}"


# --------------------------------------------------------------------------- submit


def _run_dir(args: argparse.Namespace) -> Path:
    base = Path(args.run_dir) if args.run_dir else (Path.home() / ".kaola-runner" / "launchd")
    return run_dir_for(base, args.label)


def _write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def _write_private_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + "." + secrets.token_hex(4) + ".tmp")
    _write_private(tmp, data)
    os.replace(tmp, path)


def _read_spec_file(path: Path, armed: Path) -> dict:
    assert_secure_file(path)
    assert_secure_file(armed)
    spec = read_json(path)
    armed_data = read_json(armed)
    if spec.get("schema") != SCHEMA or armed_data.get("schema") != SCHEMA:
        raise BrokerError("spec-schema", "private spec schema mismatch")
    if not spec.get("nonce") or spec.get("nonce") != armed_data.get("nonce"):
        raise BrokerError("spec-nonce", "private spec nonce mismatch")
    argv = spec.get("argv")
    check_literal_argv(list(argv or []))
    return spec


def terminate_owned(proc: subprocess.Popen) -> None:
    """Kill the exact process group this job spawned (start_new_session => pgid == pid)."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and proc.poll() is None:
        time.sleep(0.05)
    if proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    try:
        proc.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        pass


def do_internal_run(spec_path: Path) -> dict:
    """Job body: validated private seam, spawn the holder, wait, write receipt."""
    armed = Path(str(spec_path) + ".armed")
    try:
        spec = _read_spec_file(spec_path, armed)
    except BrokerError as exc:
        sys.stderr.write(json.dumps(exc.receipt()) + "\n")
        return exc.receipt()
    # Consume the armed marker and the spec before spawning: one use only.
    for path in (armed, spec_path):
        try:
            path.unlink()
        except OSError:
            pass
    argv = list(spec["argv"])
    env = {k: v for k, v in (spec.get("env") or {}).items() if isinstance(v, str)}
    # Replace the whole environment with the explicit minimal map. This removes
    # any launchd- or caller-injected variable that is not on the allowlist.
    os.environ.clear()
    os.environ.update(env)
    log_path = Path(spec["log"])
    cwd = spec.get("cwd") or "/"
    record_dir = Path(spec["record_dir"])
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                start_new_session=True, env=env, cwd=cwd)
    ready = wait_ready(record_dir, spec["platform"], spec["session"], spec["repo"],
                       float(spec.get("ready_timeout") or DEFAULT_READY_TIMEOUT))
    if ready is None:
        # Failed start cleanup: this job owns the holder it just spawned, and no
        # receipt was issued, so terminate that exact process group.
        terminate_owned(proc)
        return {"schema": SCHEMA, "result": "refused", "reason": "holder-not-ready",
                "job_pid": proc.pid}
    receipt = ready_facts(ready)
    receipt.update({"schema": SCHEMA, "result": "ready", "label": spec.get("label"),
                    "job_pid": proc.pid})
    _write_private_atomic(record_dir / RECEIPT_NAME, json.dumps(receipt, sort_keys=True).encode())
    return receipt


def wait_ready(record_dir: Path, platform: str, session: str, repo: str,
               timeout: float) -> dict | None:
    deadline = time.monotonic() + max(timeout, 1.0)
    while time.monotonic() < deadline:
        record = holder_record(record_dir)
        if holder_ready(record, platform, session, repo):
            return record
        time.sleep(0.05)
    return None


def wait_receipt(record_dir: Path, platform: str, session: str, repo: str,
                 timeout: float) -> dict | None:
    """Wait for the internal-run receipt, so the job body has finished its work."""
    deadline = time.monotonic() + max(timeout, 1.0)
    while time.monotonic() < deadline:
        receipt = read_json(record_dir / RECEIPT_NAME)
        if (receipt.get("result") == "ready"
                and receipt.get("holder_pid")
                and pid_alive(receipt.get("holder_pid"))):
            record = holder_record(record_dir)
            if holder_ready(record, platform, session, repo):
                return receipt
        time.sleep(0.05)
    return None


def do_submit(args: argparse.Namespace) -> dict:
    argv = list(args.argv or [])
    check_literal_argv(argv)
    backend, detail = backend_for(args.backend)
    if backend == "unsupported":
        raise BrokerError("launch-backend-unsupported",
                          f"no supported outside-caller launch backend here ({detail}). "
                          "Start the Host from an independent terminal on this target, "
                          "or use the direct backend explicitly.", backend=detail)
    if backend == "systemd-user":
        raise BrokerError("launch-backend-unmeasured",
                          "the user systemd backend is designed but not measured on this host; "
                          "start the Host from an independent terminal on this target.",
                          backend=detail)

    record_dir = Path(args.record_dir)
    # Reconcile before any new job: a live ready holder is the session.
    existing = holder_record(record_dir)
    if holder_ready(existing, args.platform, args.session, args.repo):
        return {"schema": SCHEMA, "result": "existing", "reconciled": True,
                "label": args.label, **ready_facts(existing)}

    run_dir = _run_dir(args)
    run_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(run_dir, 0o700)
    label = args.label
    spec_path = run_dir / "spec.json"
    armed_path = Path(str(spec_path) + ".armed")
    plist_path = run_dir / "job.plist"

    env = filter_env(dict(args.env_from or {}), set(args.env_allow or []))
    if "PATH" not in env:
        env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")
    if "HOME" not in env:
        env["HOME"] = str(Path.home())
    nonce = secrets.token_hex(NONCE_BYTES)
    spec = {
        "schema": SCHEMA, "nonce": nonce, "label": label,
        "argv": argv, "env": env, "cwd": args.cwd or "/", "log": args.log,
        "record_dir": str(record_dir), "platform": args.platform,
        "session": args.session, "repo": args.repo,
        "ready_timeout": args.ready_timeout,
    }
    _write_private(spec_path, json.dumps(spec, sort_keys=True).encode())
    _write_private(armed_path, json.dumps({"schema": SCHEMA, "nonce": nonce}).encode())

    self_path = os.path.realpath(__file__)
    # The plist carries only the non-secret core environment. The full filtered
    # environment lives in the mode-600 spec and is never written to the plist.
    plist_core = {k: env[k] for k in ("HOME", "USER", "LOGNAME", "PATH", "LANG", "TMPDIR", "SHELL")
                  if k in env}
    plist = {
        "Label": label,
        "ProgramArguments": [sys.executable, self_path, "--internal-run", "--spec", str(spec_path)],
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
        "WorkingDirectory": str(args.cwd or "/"),
        "EnvironmentVariables": plist_core,
        "StandardOutPath": str(args.log),
        "StandardErrorPath": str(args.log),
    }
    _write_private(plist_path, plistlib.dumps(plist))

    try:
        launchd_bootstrap(label, plist_path)
        receipt = wait_receipt(record_dir, args.platform, args.session, args.repo,
                               float(args.ready_timeout))
        if receipt is None:
            raise BrokerError("holder-not-ready", "holder did not reach ready inside the window",
                              label=label)
        # The one-shot job wrote its receipt. Unload the job; the detached holder stays.
        launchd_bootout(label)
        facts = {k: receipt.get(k) for k in ("holder_pid", "holder_instance_id", "acp_session_id",
                                             "agent_pid", "platform", "session", "repo", "state")}
        return {"schema": SCHEMA, "result": "ready", "reconciled": False,
                "label": label, "backend": backend, **facts}
    except BrokerError:
        # Let the job body finish its own failed-start cleanup before unloading,
        # so a bootout cannot interrupt that cleanup and leak a holder.
        wait_job_stopped(label, float(args.ready_timeout) + 10.0)
        launchd_bootout(label)
        raise
    finally:
        # Failed or successful, keep no stale job or plist history.
        for path in (plist_path, spec_path, armed_path):
            try:
                path.unlink()
            except OSError:
                pass


def do_stop(args: argparse.Namespace) -> dict:
    launched = False
    if sys.platform == "darwin":
        launchd_bootout(args.label)
        launched = True
    run_dir = _run_dir(args)
    shutil.rmtree(run_dir, ignore_errors=True)
    return {"schema": SCHEMA, "result": "stopped", "label": args.label, "job_unloaded": launched}


def do_status(args: argparse.Namespace) -> dict:
    record_dir = Path(args.record_dir)
    record = holder_record(record_dir)
    if holder_ready(record, args.platform, args.session, args.repo):
        return {"schema": SCHEMA, "result": "ready", **ready_facts(record)}
    receipt = read_json(record_dir / RECEIPT_NAME)
    return {"schema": SCHEMA, "result": "not-ready", "record": bool(record),
            "receipt": receipt or None}


# --------------------------------------------------------------------------- cli


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Outside-caller holder launcher (issue #266)")
    parser.add_argument("--internal-run", action="store_true",
                        help="private one-shot job body; requires --spec")
    parser.add_argument("--spec")
    parser.add_argument("mode", nargs="?", choices=["submit", "stop", "status"])
    parser.add_argument("--label")
    parser.add_argument("--platform")
    parser.add_argument("--session")
    parser.add_argument("--repo")
    parser.add_argument("--record-dir")
    parser.add_argument("--log")
    parser.add_argument("--cwd")
    parser.add_argument("--run-dir")
    parser.add_argument("--ready-timeout", type=float, default=DEFAULT_READY_TIMEOUT)
    parser.add_argument("--backend", help="force a backend (launchd|systemd-user|direct)")
    parser.add_argument("--env-json", help="path to a JSON env map (mode 600) merged as the base")
    parser.add_argument("--env-allow", action="append", default=[],
                        help="extra environment key to allow (repeatable)")
    parser.add_argument("--argv-json", help="path to a JSON argv list (mode 600); literal argv")
    ns = parser.parse_args(argv)

    try:
        if ns.internal_run:
            if not ns.spec:
                raise BrokerError("spec-required", "--internal-run requires --spec")
            receipt = do_internal_run(Path(ns.spec))
            print(json.dumps(receipt, sort_keys=True))
            return 0 if receipt.get("result") == "ready" else 1

        if not ns.label:
            raise BrokerError("label-required", "--label is required")
        if ns.mode in ("stop", "status") and ns.label:
            if ns.mode == "stop":
                print(json.dumps(do_stop(ns), sort_keys=True))
                return 0
            print(json.dumps(do_status(ns), sort_keys=True))
            return 0

        # submit
        for name in ("platform", "session", "repo", "record_dir", "log"):
            if not getattr(ns, name):
                raise BrokerError("argument-required", f"--{name.replace('_','-')} is required for submit")
        argv_list: list[str] = []
        if ns.argv_json:
            assert_secure_file(Path(ns.argv_json))
            argv_list = json.loads(Path(ns.argv_json).read_text(encoding="utf-8"))
        env_from = dict(os.environ)
        if ns.env_json:
            assert_secure_file(Path(ns.env_json))
            env_from = json.loads(Path(ns.env_json).read_text(encoding="utf-8"))
        ns.argv = argv_list
        ns.env_from = env_from
        receipt = do_submit(ns)
        print(json.dumps(receipt, sort_keys=True))
        return 0 if receipt.get("result") in ("ready", "existing") else 1
    except BrokerError as exc:
        print(json.dumps(exc.receipt(), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
