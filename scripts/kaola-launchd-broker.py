#!/usr/bin/env python3
"""Shared outside-caller launcher for the Runner ACP holder (issue #266).

The Runner normally spawns the holder as a child of whatever shell ran
``runtime-tmux.sh start``. When that shell belongs to a desktop app, the holder
is a descendant of the app and can die with the app. This helper launches the
holder under the per-user service manager instead:

* **submit** starts a one-shot, per-user job whose only work is the internal
  startup and exit. The holder is spawned with ``start_new_session``, so it is
  re-parented to the service manager and survives the caller, the short-lived
  job, and a later job unload.
* **internal-run** is that job body. It validates a private, mode-600 armed spec,
  builds the holder environment from an explicit minimal map only, spawns the
  holder with a literal argv, verifies the holder's own socket/record identity,
  writes a readiness receipt, records the child identity for the outer agent's
  exact sweep, and exits.
* **stop** unloads only this session's owned job and removes its files.

Hard rules:

* ProgramArguments is a literal argv list. No shell, no ``-c``, no ``eval``.
* The internal path is refused unless a private armed spec (mode 600, owner uid)
  exists. There is no environment-variable or other global authority bypass.
* Readiness is the holder's own socket/record identity: matching stored strings,
  a live PID, the argv anchor, and the holder's own ``state`` reply. A live PID
  alone is never ownership.
* The holder environment is an explicit minimal map. The full inherited
  environment and credentials are never written to the plist or any log.
* ``KeepAlive`` is false; there is no login/boot/crash restart and no separate
  scheduler or registry.
* The job PID is never treated as the holder PID.
* The label and run directory are derived from the platform/session/repo, never
  taken as arbitrary caller input.

macOS (launchd) is implemented. Linux user systemd has a minimal adapter that is
unmeasured here; other systems refuse with an actionable recovery.
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
import tempfile
import time
from pathlib import Path

SCHEMA = "kaola-launch-broker/2"
NONCE_BYTES = 16
DEFAULT_READY_TIMEOUT = 90.0
RECORD_NAME = "record.json"
RECEIPT_NAME = "launch.broker.json"
LABEL_PREFIX = "com.kaolabrother.kaola-runner.launch."

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
ALLOWED_RUNTIME_SUFFIXES = ("-from-parent",)


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


def owner_uid() -> int:
    return os.getuid()


def pid_alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool(out) and not out.upper().startswith("Z")


def process_command(pid: object) -> str | None:
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        out = subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out or None


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def assert_secure_file(path: Path) -> None:
    try:
        st = path.lstat()
    except OSError as exc:
        raise BrokerError("spec-missing", f"private file is not present: {path}") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise BrokerError("spec-not-regular", f"private file is not a regular file: {path}")
    if st.st_uid != owner_uid():
        raise BrokerError("spec-foreign-owner", f"private file is not owned by this user: {path}")
    if stat.S_IMODE(st.st_mode) & 0o077:
        raise BrokerError("spec-permissive", f"private file mode is not 600: {path}")


def write_private_exclusive(path: Path, data: bytes) -> None:
    """Create a fresh mode-600 file; refuse if it already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def write_private_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + "." + secrets.token_hex(4) + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def remove_quiet(path: Path) -> None:
    try:
        (path.unlink() if path.is_file() or path.is_symlink() else shutil.rmtree(path))
    except OSError:
        pass


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


def validate_holder_argv(argv: list[str], record_dir: Path, platform: str,
                         session: str, repo: str) -> None:
    """Validate the known internal holder launch structure.

    This is not a token blacklist: the argv must be the Runner holder command,
    and every other argument is retained as safe literal data/config.
    """
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise BrokerError("argv-empty", "the holder argv must be a non-empty literal list")
    first = os.path.basename(argv[0])
    if first in SHELL_BASENAMES:
        raise BrokerError("argv-shell", f"the holder argv must not start a shell ({first})")
    second = os.path.basename(argv[1]) if len(argv) > 1 else ""
    if second != "kaola-acp-holder.py":
        raise BrokerError("argv-not-holder",
                          "the holder argv must name kaola-acp-holder.py as its second element")
    flat = " ".join(argv)
    for flag, expected in (("--record-dir", str(record_dir)), ("--platform", platform),
                           ("--session", session), ("--repo", repo)):
        if f" {flag} " not in f" {flat} ":
            raise BrokerError("argv-incomplete", f"the holder argv must carry {flag}")


# --------------------------------------------------------------------------- identity


def sock_path_for(record_dir: Path) -> Path:
    return (Path(tempfile.gettempdir()) / f"kaola-{owner_uid()}-acp"
            / (sha(str(record_dir))[:24] + ".sock"))


def socket_state(sock: Path, timeout: float = 5.0) -> dict:
    import socket as _socket
    connection = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect(str(sock))
        payload = json.dumps({"op": "state", "request_id": secrets.token_hex(8),
                              "params": {}}).encode("utf-8") + b"\n"
        connection.sendall(payload)
        buffer = bytearray()
        while True:
            data = connection.recv(65536)
            if not data:
                break
            buffer.extend(data)
            if b"\n" in buffer:
                line, _, _ = buffer.partition(b"\n")
                return json.loads(line.decode("utf-8"))
        return json.loads(buffer.decode("utf-8")) if buffer else {"error": {"code": "holder-closed"}}
    except (OSError, ValueError) as exc:
        return {"error": {"code": "holder-unreachable", "message": str(exc)}}
    finally:
        connection.close()


def argv_anchor(pid: int, record_dir: Path) -> bool:
    command = process_command(pid)
    if command is None or "kaola-acp-holder" not in command:
        return False
    marker = " --record-dir "
    if marker not in f" {command} ":
        return False
    tail = f" {command} ".split(marker, 1)[1]
    found = tail.split(" ", 1)[0] if " " in tail else tail.strip()
    return os.path.realpath(found) == os.path.realpath(str(record_dir))


def verified_holder(record_dir: Path, platform: str, session: str, repo: str,
                    expect_pid: int | None = None) -> dict | None:
    """The holder record plus its own live socket identity, or None.

    A matching stored string and a live PID are necessary but not sufficient: the
    live PID must anchor to this record directory and the holder's socket must
    answer with the same instance id.
    """
    record = read_json(record_dir / RECORD_NAME)
    if not record or record.get("platform") != platform or record.get("session") != session:
        return None
    if record.get("repo") != repo or record.get("state") != "ready":
        return None
    pid = record.get("holder_pid")
    if not pid_alive(pid):
        return None
    if expect_pid is not None and pid != expect_pid:
        return None
    if not argv_anchor(pid, record_dir):
        return None
    state = socket_state(sock_path_for(record_dir))
    if state.get("error") or state.get("holder_instance_id") != record.get("holder_instance_id"):
        return None
    if state.get("holder_pid") not in (None, pid):
        return None
    return {"record": record, "state": state}


def ready_facts(verified: dict) -> dict:
    record, state = verified["record"], verified["state"]
    return {
        "holder_pid": record.get("holder_pid"),
        "holder_instance_id": record.get("holder_instance_id"),
        "acp_session_id": state.get("acp_session_id", record.get("acp_session_id")),
        "agent_pid": record.get("agent_pid"),
        "platform": record.get("platform"),
        "session": record.get("session"),
        "repo": record.get("repo"),
        "state": record.get("state"),
    }


# --------------------------------------------------------------------------- job identity


def label_for(platform: str, session: str, repo: str) -> str:
    return LABEL_PREFIX + sha(f"{platform}\0{session}\0{repo}")[:16]


def run_dir_for(base: Path, label: str) -> Path:
    return base / label


def default_run_base() -> Path:
    return Path.home() / ".kaola-runner" / "launchd"


def launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/launchctl", *args], capture_output=True, text=True, timeout=30)


def job_state(label: str) -> str:
    """running | exited | absent, from launchctl's own list."""
    out = launchctl("list").stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == label:
            return "running" if parts[0].isdigit() else "exited"
    return "absent"


def launchd_bootstrap(label: str, plist_path: Path) -> None:
    if not label.startswith(LABEL_PREFIX):
        raise BrokerError("label-foreign", f"refuse to bootstrap a foreign label: {label}")
    domain = f"gui/{owner_uid()}"
    state = job_state(label)
    if state == "running":
        raise BrokerError("launch-in-progress",
                          "a job for this exact session is already running; reconcile it",
                          label=label)
    if state == "exited":
        launchctl("bootout", f"{domain}/{label}")
    result = launchctl("bootstrap", domain, str(plist_path))
    if result.returncode != 0:
        raise BrokerError("bootstrap-failed",
                          f"launchctl bootstrap failed: {result.stderr.strip() or result.stdout.strip()}",
                          label=label)


def launchd_bootout(label: str) -> None:
    if not label.startswith(LABEL_PREFIX):
        return
    launchctl("bootout", f"gui/{owner_uid()}/{label}")


def wait_job_stopped(label: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if job_state(label) != "running":
            return
        time.sleep(0.1)


# --------------------------------------------------------------------------- systemd / other


def systemd_user_available() -> tuple[bool, str]:
    if not shutil.which("systemctl") or not shutil.which("systemd-run"):
        return False, "systemctl/systemd-run is not on PATH"
    try:
        result = subprocess.run(["systemctl", "--user", "is-system-running"],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"systemctl --user probe failed: {exc}"
    if result.stdout.strip() in ("running", "degraded", "maintenance"):
        return True, result.stdout.strip()
    return False, result.stdout.strip() or result.stderr.strip() or "no user manager"


def backend_for(force: str | None = None) -> tuple[str, str]:
    """Return (backend, detail). Never silently falls back to a direct spawn."""
    if force and force != "auto":
        return force, "forced by caller"
    if sys.platform == "darwin":
        return "launchd", "macOS"
    if sys.platform.startswith("linux"):
        ok, detail = systemd_user_available()
        return ("systemd-user" if ok else "unsupported"), detail
    return "unsupported", f"no supported service manager for {sys.platform}"


# --------------------------------------------------------------------------- spawn / terminate


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


def wait_verified(record_dir: Path, platform: str, session: str, repo: str,
                  timeout: float, expect_pid: int | None = None) -> dict | None:
    deadline = time.monotonic() + max(timeout, 1.0)
    while time.monotonic() < deadline:
        verified = verified_holder(record_dir, platform, session, repo, expect_pid)
        if verified is not None:
            return verified
        time.sleep(0.05)
    return None


def wait_receipt(record_dir: Path, platform: str, session: str, repo: str,
                 timeout: float) -> dict | None:
    """Wait for this attempt's receipt, then re-verify the live holder identity."""
    deadline = time.monotonic() + max(timeout, 1.0)
    while time.monotonic() < deadline:
        receipt = read_json(record_dir / RECEIPT_NAME)
        if receipt.get("result") == "ready" and receipt.get("holder_instance_id"):
            verified = verified_holder(record_dir, platform, session, repo,
                                       receipt.get("holder_pid"))
            if verified is not None and verified["record"].get(
                    "holder_instance_id") == receipt.get("holder_instance_id"):
                return verified
        time.sleep(0.05)
    return None


# --------------------------------------------------------------------------- submit


def _run_dir(args: argparse.Namespace) -> Path:
    base = Path(args.run_base) if args.run_base else default_run_base()
    return run_dir_for(base, label_for(args.platform, args.session, args.repo))


def do_internal_run(spec_path: Path) -> dict:
    """Job body: validated private seam, spawn the holder, verify, write receipt."""
    armed = Path(str(spec_path) + ".armed")
    try:
        assert_secure_file(spec_path)
        assert_secure_file(armed)
        spec = read_json(spec_path)
        armed_data = read_json(armed)
        if spec.get("schema") != SCHEMA or armed_data.get("schema") != SCHEMA:
            raise BrokerError("spec-schema", "private spec schema mismatch")
        if not spec.get("nonce") or spec.get("nonce") != armed_data.get("nonce"):
            raise BrokerError("spec-nonce", "private spec nonce mismatch")
        validate_holder_argv(list(spec.get("argv") or []), Path(spec["record_dir"]),
                             spec["platform"], spec["session"], spec["repo"])
    except BrokerError as exc:
        sys.stderr.write(json.dumps(exc.receipt()) + "\n")
        return exc.receipt()
    for path in (armed, spec_path):
        remove_quiet(path)
    argv = list(spec["argv"])
    env = {k: v for k, v in (spec.get("env") or {}).items() if isinstance(v, str)}
    os.environ.clear()
    os.environ.update(env)
    log_path = Path(spec["log"])
    cwd = spec.get("cwd") or "/"
    record_dir = Path(spec["record_dir"])
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                start_new_session=True, env=env, cwd=cwd)
    verified = wait_verified(record_dir, spec["platform"], spec["session"], spec["repo"],
                             float(spec.get("ready_timeout") or DEFAULT_READY_TIMEOUT),
                             expect_pid=proc.pid)
    if verified is None:
        terminate_owned(proc)
        return {"schema": SCHEMA, "result": "refused", "reason": "holder-not-ready",
                "job_pid": proc.pid}
    receipt = ready_facts(verified)
    receipt.update({"schema": SCHEMA, "result": "ready", "label": spec.get("label"),
                    "job_pid": proc.pid})
    child = _record_child(spec, verified["record"].get("holder_pid"))
    if child is not None:
        receipt["child_record"] = child
    write_private_atomic(record_dir / RECEIPT_NAME, json.dumps(receipt, sort_keys=True).encode())
    return receipt


def _record_child(spec: dict, holder_pid: object) -> dict | None:
    """Append the spawned holder's identity to the outer agent's child record.

    This keeps dispatcher/child ownership across the outside launch, so the
    outer host's exact sweep and preserve-dispatched-worker duties still hold.
    """
    path = spec.get("child_record")
    if not path or not isinstance(holder_pid, int) or holder_pid <= 0:
        return None
    entry = {"pid": holder_pid, "pgid": holder_pid, "spawned_at": int(time.time() * 1000)}
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        return None
    return entry


def _systemd_submit(args: argparse.Namespace, spec_path: Path, label: str) -> None:
    unit = label.replace("com.kaolabrother.kaola-runner.launch.", "kaola-runner-launch-")
    result = subprocess.run(
        ["systemd-run", "--user", "--collect", "--unit", unit,
         "--description", f"Kaola Runner holder launch {args.session}",
         sys.executable, os.path.realpath(__file__), "--internal-run", "--spec", str(spec_path)],
        capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise BrokerError("bootstrap-failed",
                          f"systemd-run failed: {result.stderr.strip() or result.stdout.strip()}")


def do_submit(args: argparse.Namespace) -> dict:
    record_dir = Path(args.record_dir)
    platform, session, repo = args.platform, args.session, args.repo
    # Reconcile a verified live holder before any new job.
    existing = verified_holder(record_dir, platform, session, repo)
    if existing is not None:
        return {"schema": SCHEMA, "result": "existing", "reconciled": True,
                **ready_facts(existing)}

    backend, detail = backend_for(args.backend)
    if backend == "unsupported":
        raise BrokerError("launch-backend-unsupported",
                          f"no supported outside-caller launch backend here ({detail}). "
                          "Start the Host from an independent terminal on this target, "
                          "or pass the direct backend explicitly.", backend=detail)

    label = label_for(platform, session, repo)
    run_dir = run_dir_for(Path(args.run_base) if args.run_base else default_run_base(), label)

    # A concurrent or partial start for this exact session must be reconciled, not
    # killed or overwritten.
    if job_state(label) == "running":
        verified = wait_verified(record_dir, platform, session, repo, float(args.ready_timeout))
        if verified is not None:
            return {"schema": SCHEMA, "result": "existing", "reconciled": True,
                    **ready_facts(verified)}
        raise BrokerError("launch-in-progress",
                          "a job for this exact session is already running; reconcile it",
                          label=label)

    argv = list(args.argv or [])
    validate_holder_argv(argv, record_dir, platform, session, repo)
    env = filter_env(dict(args.env_from or {}), set(args.env_allow or []))
    if "PATH" not in env:
        env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")
    if "HOME" not in env:
        env["HOME"] = str(Path.home())

    run_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(run_dir, 0o700)
    attempt = run_dir / f"attempt-{secrets.token_hex(6)}"
    attempt.mkdir(mode=0o700)
    spec_path = attempt / "spec.json"
    armed_path = Path(str(spec_path) + ".armed")
    plist_path = attempt / "job.plist"
    nonce = secrets.token_hex(NONCE_BYTES)
    spec = {
        "schema": SCHEMA, "nonce": nonce, "label": label,
        "argv": argv, "env": env, "cwd": args.cwd or "/", "log": args.log,
        "record_dir": str(record_dir), "platform": platform,
        "session": session, "repo": repo, "child_record": args.child_record or "",
        "ready_timeout": args.ready_timeout,
    }
    if args.argv_json:
        # The caller-supplied literal argv file is consumed and removed here.
        remove_quiet(Path(args.argv_json))
    try:
        write_private_exclusive(spec_path, json.dumps(spec, sort_keys=True).encode())
        write_private_exclusive(armed_path, json.dumps({"schema": SCHEMA, "nonce": nonce}).encode())
        plist_core = {k: env[k] for k in ("HOME", "USER", "LOGNAME", "PATH", "LANG", "TMPDIR", "SHELL")
                      if k in env}
        plist = {
            "Label": label,
            "ProgramArguments": [sys.executable, os.path.realpath(__file__),
                                 "--internal-run", "--spec", str(spec_path)],
            "RunAtLoad": True, "KeepAlive": False, "ProcessType": "Interactive",
            "WorkingDirectory": str(args.cwd or "/"),
            "EnvironmentVariables": plist_core,
            "StandardOutPath": str(args.log), "StandardErrorPath": str(args.log),
        }
        write_private_exclusive(plist_path, plistlib.dumps(plist))
        try:
            if backend == "systemd-user":
                _systemd_submit(args, spec_path, label)
            else:
                launchd_bootstrap(label, plist_path)
            verified = wait_receipt(record_dir, platform, session, repo, float(args.ready_timeout))
            if verified is None:
                raise BrokerError("holder-not-ready",
                                  "holder did not reach a verified ready state inside the window",
                                  label=label)
            if backend == "launchd":
                wait_job_stopped(label, 5.0)
                launchd_bootout(label)
            return {"schema": SCHEMA, "result": "ready", "reconciled": False,
                    "label": label, "backend": backend, **ready_facts(verified)}
        except BrokerError:
            wait_job_stopped(label, float(args.ready_timeout) + 10.0)
            launchd_bootout(label)
            raise
    finally:
        remove_quiet(attempt)
        remove_quiet(record_dir / RECEIPT_NAME)
        try:
            if not any(run_dir.iterdir()):
                remove_quiet(run_dir)
        except OSError:
            pass


def do_stop(args: argparse.Namespace) -> dict:
    label = label_for(args.platform, args.session, args.repo)
    run_dir = run_dir_for(Path(args.run_base) if args.run_base else default_run_base(), label)
    unloaded = False
    if sys.platform == "darwin" and job_state(label) != "absent":
        launchd_bootout(label)
        wait_job_stopped(label, 5.0)
        unloaded = True
    remove_quiet(run_dir)
    return {"schema": SCHEMA, "result": "stopped", "label": label, "job_unloaded": unloaded}


# --------------------------------------------------------------------------- cli


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Outside-caller holder launcher (issue #266)")
    parser.add_argument("--internal-run", action="store_true",
                        help="private one-shot job body; requires --spec")
    parser.add_argument("--spec")
    parser.add_argument("mode", nargs="?", choices=["submit", "stop"])
    parser.add_argument("--platform")
    parser.add_argument("--session")
    parser.add_argument("--repo")
    parser.add_argument("--record-dir")
    parser.add_argument("--log")
    parser.add_argument("--cwd")
    parser.add_argument("--run-base")
    parser.add_argument("--ready-timeout", type=float, default=DEFAULT_READY_TIMEOUT)
    parser.add_argument("--backend", default="auto", help="auto | launchd | systemd-user")
    parser.add_argument("--child-record", help="outer agent child record to append this holder to")
    parser.add_argument("--argv-json", help="path to a JSON argv list (mode 600); consumed on use")
    parser.add_argument("--env-allow", action="append", default=[],
                        help="extra environment key to allow (repeatable)")
    ns = parser.parse_args(argv)

    try:
        if ns.internal_run:
            if not ns.spec:
                raise BrokerError("spec-required", "--internal-run requires --spec")
            receipt = do_internal_run(Path(ns.spec))
            print(json.dumps(receipt, sort_keys=True))
            return 0 if receipt.get("result") == "ready" else 1

        for name in ("platform", "session", "repo"):
            if not getattr(ns, name):
                raise BrokerError("argument-required", f"--{name} is required")

        if ns.mode == "stop":
            print(json.dumps(do_stop(ns), sort_keys=True))
            return 0

        if ns.mode != "submit":
            raise BrokerError("mode-required", "choose submit or stop")
        if not ns.record_dir or not ns.log:
            raise BrokerError("argument-required", "--record-dir and --log are required for submit")
        argv_list: list[str] = []
        if ns.argv_json:
            assert_secure_file(Path(ns.argv_json))
            argv_list = json.loads(Path(ns.argv_json).read_text(encoding="utf-8"))
        ns.argv = argv_list
        ns.env_from = dict(os.environ)
        receipt = do_submit(ns)
        print(json.dumps(receipt, sort_keys=True))
        return 0 if receipt.get("result") in ("ready", "existing") else 1
    except BrokerError as exc:
        print(json.dumps(exc.receipt(), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
