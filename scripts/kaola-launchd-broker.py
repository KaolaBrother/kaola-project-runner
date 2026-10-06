#!/usr/bin/env python3
"""Shared outside-caller launcher for the Runner ACP holder (issue #266).

The Runner normally spawns the holder as a child of whatever shell ran
``runtime-tmux.sh start``. When that shell belongs to a desktop app, the holder
is a descendant of the app and can die with the app. This helper launches the
holder under the per-user service manager instead:

* **submit** starts a one-shot, per-user job whose only work is the internal
  startup and exit. The holder is spawned with ``start_new_session``, so it is
  re-parented to the service manager and survives the caller and the short-lived
  job.
* **internal-run** is that job body. It validates a private, mode-600 armed spec,
  builds the holder environment from an explicit minimal map, spawns the holder
  with a literal argv, verifies the holder's own socket/record identity,
  best-effort records the child identity, and exits.
* **cleanup** removes this session's owned leftover job/run dir. It never
  unloads a running job; the Runner owns holder stop.

Hard rules:

* ProgramArguments is a literal argv list. No shell, no ``-c``, no ``eval``.
* The internal path is refused unless a private armed spec (mode 600, owner uid)
  exists. There is no environment-variable or other global authority bypass.
* Readiness is the holder's own socket/record identity. A matching string plus a
  live PID is not ownership, and no process-table text is reconstructed.
* The holder environment is an explicit minimal map: named runtime/config/dispatch
  keys, declared manifest keys, proxy, and login-lookup keys only. The full
  inherited environment and credentials never reach a plist or a log.
* ``KeepAlive`` is false; there is no login/boot/crash restart and no separate
  scheduler or registry.
* The job PID is never treated as the holder PID.
* OS operations are isolated: macOS uses launchd, Linux uses a user systemd
  transient unit, other systems refuse. No silent fallback to the caller.
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

SCHEMA = "kaola-launch-broker/3"
NONCE_BYTES = 16
DEFAULT_READY_TIMEOUT = 90.0
RECORD_NAME = "record.json"
RECEIPT_NAME = "launch.broker.json"
LABEL_PREFIX = "com.kaolabrother.kaola-runner.launch."
UNIT_PREFIX = "kaola-runner-launch-"

# The only environment names that may reach the holder. Everything else from the
# caller is dropped: no caller-app ownership variable and no unlisted credential.
PASS_ALWAYS = ("HOME", "USER", "LOGNAME", "SHELL", "PATH", "TMPDIR", "LANG", "LC_ALL")
PASS_PROXY = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "no_proxy", "all_proxy")
# Named Runner keys only. A blanket ``KAOLA_*`` would forward unrelated or caller
# app bindings; manifest keys travel through ``--env-allow``.
PASS_KAOLA = frozenset({
    "KAOLA_ACP_RECORD_ROOT", "KAOLA_ACP_DISPATCHER", "KAOLA_ACP_CHILD_RECORD",
    "KAOLA_ACP_HEARTBEAT_HOST", "KAOLA_ACP_HEARTBEAT_HOST_SOCKET",
    "KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE", "KAOLA_PROJECT_RUNNER_CANONICAL_REPO",
    "KAOLA_LAUNCH_BACKEND", "KAOLA_CLAUDE_PROFILE_REQUIRED",
})
SHELL_BASENAMES = {"sh", "bash", "zsh", "dash", "fish", "ksh", "tcsh", "csh"}
HOLDER_FLAGS = ("--record-dir", "--socket", "--repo", "--platform", "--session", "--command")


class BrokerError(Exception):
    """A refusal with a stable code, an actionable message, and spawn honesty."""

    def __init__(self, code: str, message: str, spawned: bool = False, **facts: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.spawned = spawned
        self.facts = facts

    def receipt(self) -> dict:
        out = {"schema": SCHEMA, "result": "refused", "reason": self.code,
               "detail": self.message, "holder_may_exist": bool(self.spawned), **self.facts}
        if self.spawned:
            out["recovery"] = ("An own holder or native agent may still run. Exact-stop this "
                               "session through the Runner, or re-run broker cleanup after the "
                               "manager state is readable.")
        return out


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
    """Keep only the minimal, named environment for the holder."""
    extra = extra_keys or set()
    kept: dict[str, str] = {}
    for key, value in env.items():
        if not isinstance(value, str):
            continue
        if (key in PASS_ALWAYS or key in PASS_PROXY or key in PASS_KAOLA or key in extra):
            kept[key] = value
    return kept


def argv_option(argv: list[str], flag: str) -> str | None:
    """The literal value token of ``flag`` in an argv list (never a text split)."""
    for index, token in enumerate(argv):
        if token == flag and index + 1 < len(argv):
            return argv[index + 1]
    return None


def validate_holder_argv(argv: list[str], record_dir: Path, socket: Path, platform: str,
                         session: str, repo: str) -> None:
    """Validate the exact internal holder invocation and its argument bindings.

    This parses the literal argv list (spaces in a path are one token) and
    compares each named binding to the expected value. It is not a token
    blacklist and it never reconstructs text from the process table.
    """
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise BrokerError("argv-empty", "the holder argv must be a non-empty literal list")
    if os.path.basename(argv[0]) in SHELL_BASENAMES:
        raise BrokerError("argv-shell", f"the holder argv must not start a shell ({argv[0]})")
    if len(argv) < 2 or os.path.basename(argv[1]) != "kaola-acp-holder.py":
        raise BrokerError("argv-not-holder",
                          "the holder argv must name kaola-acp-holder.py as its second element")
    expected = {"--record-dir": str(record_dir), "--socket": str(socket), "--repo": repo,
                "--platform": platform, "--session": session}
    for flag, want in expected.items():
        got = argv_option(argv, flag)
        if got is None:
            raise BrokerError("argv-incomplete", f"the holder argv must carry {flag}")
        if flag in ("--record-dir", "--socket"):
            if os.path.realpath(got) != os.path.realpath(want):
                raise BrokerError("argv-binding", f"{flag} does not name the expected path")
        elif got != want:
            raise BrokerError("argv-binding", f"{flag} does not name the expected value")
    if argv_option(argv, "--command") is None:
        raise BrokerError("argv-incomplete", "the holder argv must carry --command")


# --------------------------------------------------------------------------- identity


def sock_path_for(record_dir: Path) -> Path:
    return (Path(tempfile.gettempdir()) / f"kaola-{owner_uid()}-acp"
            / (sha(str(record_dir))[:24] + ".sock"))


def socket_op(sock: Path, op: str, params: dict, timeout: float = 5.0) -> dict:
    import socket as _socket
    connection = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect(str(sock))
        payload = json.dumps({"op": op, "request_id": secrets.token_hex(8),
                              "params": params}).encode("utf-8") + b"\n"
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


def socket_state(sock: Path, timeout: float = 5.0) -> dict:
    return socket_op(sock, "state", {}, timeout)


def verified_holder(record_dir: Path, platform: str, session: str, repo: str,
                    expect_pid: int | None = None) -> dict | None:
    """The holder record plus its own live socket identity, or None.

    A matching stored string and a live PID are necessary but not sufficient.
    Only the holder itself answers its socket with the record's instance id, so
    that reply is the ownership proof; the PID must agree with the record.
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


# --------------------------------------------------------------------------- job identity / OS


def label_for(platform: str, session: str, repo: str) -> str:
    return LABEL_PREFIX + sha(f"{platform}\0{session}\0{repo}")[:16]


def unit_for(label: str) -> str:
    return label.replace(LABEL_PREFIX, UNIT_PREFIX)


def run_dir_for(base: Path, label: str) -> Path:
    return base / label


def default_run_base() -> Path:
    return Path.home() / ".kaola-runner" / "launchd"


def backend_for(force: str | None = None) -> tuple[str, str]:
    """Return (backend, detail). Never silently falls back to a direct spawn."""
    if force and force != "auto":
        if force == "launchd" and sys.platform != "darwin":
            return "unsupported", "launchd requires macOS"
        if force == "systemd-user":
            if not (sys.platform.startswith("linux") and shutil.which("systemctl")
                    and shutil.which("systemd-run")):
                return "unsupported", "the user systemd manager is not available here"
        return force, "forced by caller"
    if sys.platform == "darwin":
        return "launchd", "macOS"
    if sys.platform.startswith("linux"):
        if shutil.which("systemctl") and shutil.which("systemd-run"):
            return "systemd-user", "linux"
        return "unsupported", "systemctl/systemd-run is not on PATH"
    return "unsupported", f"no supported service manager for {sys.platform}"


def launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/launchctl", *args], capture_output=True, text=True, timeout=30)


def systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=30)


def os_job_state(backend: str, label: str) -> str:
    """running | exited | absent for the owned job/unit, per the active backend."""
    if backend == "launchd":
        result = launchctl("list")
        if result.returncode != 0:
            return "unknown"
        out = result.stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[2] == label:
                return "running" if parts[0].isdigit() else "exited"
        return "absent"
    if backend == "systemd-user":
        result = systemctl("is-active", unit_for(label))
        state = result.stdout.strip()
        if state in ("active", "activating", "reloading"):
            return "running"
        if state in ("inactive", "failed", "deactivating"):
            return "exited"
        # A manager error or unknown phrase is never a verified absence.
        return "unknown"
    return "absent"


def os_job_owns(backend: str, label: str, spec_path: Path) -> bool:
    """Whether the loaded owned job/unit names this attempt's private spec.

    This is the ownership receipt: the spec path is per-attempt, so only the
    attempt that wrote it can own the loaded job.
    """
    marker = str(spec_path)
    if backend == "launchd":
        out = launchctl("print", f"gui/{owner_uid()}/{label}").stdout
        return marker in out
    if backend == "systemd-user":
        result = systemctl("show", unit_for(label), "-p", "ExecStart")
        return marker in result.stdout
    return False


def os_bootstrap(backend: str, label: str, plist_path: Path, spec_path: Path) -> None:
    if backend == "launchd":
        if not label.startswith(LABEL_PREFIX):
            raise BrokerError("label-foreign", f"refuse to bootstrap a foreign label: {label}")
        domain = f"gui/{owner_uid()}"
        state = os_job_state(backend, label)
        if state == "running":
            raise BrokerError("launch-in-progress",
                              "a job for this exact session is already running; reconcile it",
                              spawned=True, label=label)
        # An exited job is handled by do_submit with this attempt's identity.
        result = launchctl("bootstrap", domain, str(plist_path))
        if result.returncode != 0:
            state = os_job_state(backend, label)
            raise BrokerError("bootstrap-failed",
                              f"launchctl bootstrap failed: {result.stderr.strip() or result.stdout.strip()}",
                              spawned=(state != "absent"), label=label, os_state=state)
        return
    if backend == "systemd-user":
        # Explicit lifetime policy: KillMode=process leaves the detached holder
        # (its own session) alive when the transient unit stops. This is a
        # designed policy, unmeasured on macOS.
        result = subprocess.run(
            ["systemd-run", "--user", "--collect", "--property=KillMode=process",
             "--unit", unit_for(label), "--description",
             f"Kaola Runner holder launch {label}", sys.executable,
             os.path.realpath(__file__), "--internal-run", "--spec", str(spec_path)],
            capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            state = os_job_state("systemd-user", label)
            raise BrokerError("bootstrap-failed",
                              f"systemd-run failed: {result.stderr.strip() or result.stdout.strip()}",
                              spawned=(state != "absent"), label=label, os_state=state)
        return
    raise BrokerError("launch-backend-unsupported", f"no OS operation for backend {backend}")


def os_unload(backend: str, label: str) -> None:
    if backend == "launchd":
        if label.startswith(LABEL_PREFIX):
            launchctl("bootout", f"gui/{owner_uid()}/{label}")
    elif backend == "systemd-user":
        systemctl("stop", unit_for(label))
        systemctl("reset-failed", unit_for(label))


def os_wait_stopped(backend: str, label: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if os_job_state(backend, label) != "running":
            return
        time.sleep(0.1)


# --------------------------------------------------------------------------- spawn / terminate


def terminate_owned(proc: subprocess.Popen) -> None:
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


# --------------------------------------------------------------------------- submit


def do_internal_run(spec_path: Path) -> dict:
    """Job body: validated private seam, spawn the holder, verify, record, exit."""
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
                             Path(spec["socket"]), spec["platform"], spec["session"], spec["repo"])
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
                "holder_may_exist": False, "job_pid": proc.pid}
    child_entry, child_error = _record_child(spec, verified["record"].get("holder_pid"))
    if spec.get("child_record") and child_error is not None:
        # A requested custody record that cannot be written is a failed nested
        # launch. Stop this exact holder through the existing identity path and
        # reap our own child, so the native agent group is reclaimed too.
        stop = _stop_owned_holder(Path(spec["socket"]),
                                  verified["record"].get("holder_instance_id"), proc)
        receipt = {"schema": SCHEMA, "result": "refused", "reason": "child-record-failed",
                   "child_record_error": child_error, **stop}
    else:
        receipt = ready_facts(verified)
        receipt.update({"schema": SCHEMA, "result": "ready", "label": spec.get("label"),
                        "job_pid": proc.pid})
        if child_entry is not None:
            receipt["child_record"] = child_entry
    # The receipt carries the custody outcome; a write failure must not strand a
    # ready holder, but submit then cannot gate on it and reconciles instead.
    try:
        write_private_atomic(record_dir / RECEIPT_NAME, json.dumps(receipt, sort_keys=True).encode())
    except OSError:
        pass
    return receipt


def _stop_owned_holder(sock: Path, instance: str | None, proc: subprocess.Popen) -> dict:
    """Stop this attempt's holder by identity, then reap its own Popen child.

    Clean requires a positive stop reply with an actual empty residual list and a
    reaped child. A missing/refused reply, a null residual, or a live holder keeps
    the native/worker custody unknown: the native agent has its own group, so a
    reaped holder alone is not proof of no residual.
    """
    params: dict = {"force": True}
    if instance:
        params["expected_holder_instance_id"] = instance
    reply = socket_op(sock, "stop", params, 30.0)
    reply = reply if isinstance(reply, dict) else {}
    terminate_owned(proc)
    residual = reply.get("residual_pids")
    stopped = reply.get("stopped") is True
    clean = stopped and isinstance(residual, list) and residual == [] and not pid_alive(proc.pid)
    return {
        "holder_may_exist": not clean,
        "host_session_stopped": stopped,
        "residual_pids": residual,
        "holder_alive": pid_alive(proc.pid),
    }


def _record_child(spec: dict, holder_pid: object) -> tuple[dict | None, str | None]:
    path = spec.get("child_record")
    if not path:
        return None, None
    if not isinstance(holder_pid, int) or holder_pid <= 0:
        return None, "the holder pid is not known"
    entry = {"pid": holder_pid, "pgid": holder_pid, "spawned_at": int(time.time() * 1000)}
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError as exc:
        return None, str(exc)
    return entry, None


def do_submit(args: argparse.Namespace) -> dict:
    record_dir = Path(args.record_dir)
    platform, session, repo = args.platform, args.session, args.repo
    existing = verified_holder(record_dir, platform, session, repo)
    if existing is not None:
        return {"schema": SCHEMA, "result": "existing", "reconciled": True, **ready_facts(existing)}

    backend, detail = backend_for(args.backend)
    if backend == "unsupported":
        raise BrokerError("launch-backend-unsupported",
                          f"no supported outside-caller launch backend here ({detail}). "
                          "Start the Host from an independent terminal on this target, "
                          "or pass the direct backend explicitly.", backend=detail)

    label = label_for(platform, session, repo)
    run_dir = run_dir_for(Path(args.run_base) if args.run_base else default_run_base(), label)

    # Reconcile, never kill, a concurrent or partial start for this exact session.
    if os_job_state(backend, label) == "running":
        verified = wait_verified(record_dir, platform, session, repo, float(args.ready_timeout))
        if verified is not None:
            return {"schema": SCHEMA, "result": "existing", "reconciled": True, **ready_facts(verified)}
        raise BrokerError("launch-in-progress",
                          "a job for this exact session is already running; reconcile it",
                          spawned=True, label=label)

    argv = list(args.argv or [])
    socket = Path(args.socket) if args.socket else sock_path_for(record_dir)
    validate_holder_argv(argv, record_dir, socket, platform, session, repo)
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
    spec = {"schema": SCHEMA, "nonce": nonce, "label": label, "argv": argv, "env": env,
            "cwd": args.cwd or "/", "log": args.log, "record_dir": str(record_dir),
            "socket": str(socket), "platform": platform, "session": session, "repo": repo,
            "child_record": args.child_record or "", "ready_timeout": args.ready_timeout}
    if args.argv_json:
        remove_quiet(Path(args.argv_json))
    bootstrapped = False
    unresolved = False
    try:
        # Pre-bootstrap: an exited job is unloaded only when this attempt owns it.
        state = os_job_state(backend, label)
        if state == "exited":
            if os_job_owns(backend, label, spec_path):
                os_unload(backend, label)
            else:
                raise BrokerError("job-occupied",
                                  "an exited job for this session is not owned by this attempt; "
                                  "reconcile it", label=label, os_state=state)
        write_private_exclusive(spec_path, json.dumps(spec, sort_keys=True).encode())
        write_private_exclusive(armed_path, json.dumps({"schema": SCHEMA, "nonce": nonce}).encode())
        if backend == "launchd":
            plist_core = {k: env[k] for k in ("HOME", "USER", "LOGNAME", "PATH", "LANG", "TMPDIR", "SHELL")
                          if k in env}
            plist = {"Label": label,
                     "ProgramArguments": [sys.executable, os.path.realpath(__file__),
                                          "--internal-run", "--spec", str(spec_path)],
                     "RunAtLoad": True, "KeepAlive": False, "ProcessType": "Interactive",
                     "WorkingDirectory": str(args.cwd or "/"),
                     "EnvironmentVariables": plist_core,
                     "StandardOutPath": str(args.log), "StandardErrorPath": str(args.log)}
            write_private_exclusive(plist_path, plistlib.dumps(plist))
        os_bootstrap(backend, label, plist_path, spec_path)
        bootstrapped = True
        # Gate on the internal receipt: it carries the required custody outcome.
        receipt = wait_receipt_file(record_dir, float(args.ready_timeout))
        if receipt is None:
            state = os_job_state(backend, label)
            raise BrokerError("holder-not-ready",
                              "the internal startup wrote no outcome inside the window",
                              spawned=(state != "absent"), label=label, os_state=state)
        if receipt.get("result") == "refused":
            raise BrokerError(receipt.get("reason") or "launch-refused",
                              receipt.get("child_record_error") or "the internal startup refused",
                              spawned=bool(receipt.get("holder_may_exist")), label=label)
        verified = wait_verified(record_dir, platform, session, repo, 5.0,
                                 expect_pid=receipt.get("holder_pid"))
        if verified is None:
            state = os_job_state(backend, label)
            raise BrokerError("holder-not-ready",
                              "the reported holder is not a verified live holder",
                              spawned=(state != "absent"), label=label, os_state=state)
        if os_job_owns(backend, label, spec_path):
            os_wait_stopped(backend, label, 5.0)
            os_unload(backend, label)
        return {"schema": SCHEMA, "result": "ready", "reconciled": False,
                "label": label, "backend": backend, **ready_facts(verified)}
    except BrokerError as exc:
        unresolved, state = _reconcile_failed_attempt(backend, label, spec_path, args,
                                                      record_dir, platform, session, repo)
        if not exc.spawned and (unresolved or verified_holder(record_dir, platform, session, repo)):
            exc.spawned = True
        raise
    except Exception as exc:
        # An unexpected failure (for example a private-file write error) still
        # reconciles and never claims a clean effect it cannot prove.
        unresolved, state = _reconcile_failed_attempt(backend, label, spec_path, args,
                                                      record_dir, platform, session, repo)
        if verified_holder(record_dir, platform, session, repo) is not None:
            unresolved = True
        raise BrokerError("launch-failed", f"{type(exc).__name__}: {exc}",
                          spawned=unresolved) from exc
    finally:
        remove_quiet(record_dir / RECEIPT_NAME)
        if not unresolved:
            remove_quiet(attempt)
            try:
                if not any(run_dir.iterdir()):
                    remove_quiet(run_dir)
            except OSError:
                pass


def wait_receipt_file(record_dir: Path, timeout: float) -> dict | None:
    """The internal startup's own outcome receipt, ready or refused."""
    deadline = time.monotonic() + max(timeout, 1.0)
    while time.monotonic() < deadline:
        receipt = read_json(record_dir / RECEIPT_NAME)
        if receipt.get("result") in ("ready", "refused"):
            return receipt
        time.sleep(0.05)
    return None


def _reconcile_failed_attempt(backend: str, label: str, spec_path: Path,
                              args: argparse.Namespace, record_dir: Path, platform: str,
                              session: str, repo: str) -> tuple[bool, str]:
    """Bound a failed attempt's cleanup to its own job/holder.

    Returns (unresolved, state). Unresolved is True when the exact effect cannot
    be established, so the caller keeps the attempt evidence and reports an
    unknown outcome. Never unloads a job this attempt cannot prove it owns, and
    never declares clean from a job unload alone while an own holder effect
    remains.
    """
    remains = _own_holder_effect_remains(record_dir, platform, session, repo)
    if backend == "unsupported":
        return remains, "absent"
    state = os_job_state(backend, label)
    owns = os_job_owns(backend, label, spec_path) if state in ("running", "exited") else False
    if owns:
        os_wait_stopped(backend, label, float(args.ready_timeout) + 10.0)
        os_unload(backend, label)
        return _own_holder_effect_remains(record_dir, platform, session, repo), state
    if state in ("running", "exited", "unknown"):
        return True, state
    return remains, state


def _own_holder_effect_remains(record_dir: Path, platform: str, session: str, repo: str) -> bool:
    """Whether this exact session's recorded holder OR native agent is alive.

    The native agent runs in its own group, so a dead holder alone does not prove
    no residual. Missing recorded identities are unknown, never a clean claim.
    """
    record = read_json(record_dir / RECORD_NAME)
    if not record or record.get("platform") != platform or record.get("session") != session:
        return False
    if record.get("repo") != repo:
        return False
    return (pid_alive(record.get("holder_pid"))
            or pid_alive(record.get("agent_pid"))
            or pid_alive(record.get("agent_pgid")))


def do_cleanup(args: argparse.Namespace) -> dict:
    """Remove only this session's proven completed own attempt artifacts.

    A running job, an unknown manager state, or an exited job this session's
    attempts do not own is left untouched. The manager is never unloaded on a
    guess, and a nonowned or concurrent resource is preserved.
    """
    backend, _ = backend_for(args.backend)
    label = label_for(args.platform, args.session, args.repo)
    run_dir = run_dir_for(Path(args.run_base) if args.run_base else default_run_base(), label)
    if backend != "unsupported":
        state = os_job_state(backend, label)
        if state == "running":
            raise BrokerError("job-running",
                              "the one-shot job for this session is still running; stop the holder "
                              "through the Runner first", label=label)
        if state == "unknown":
            raise BrokerError("job-state-unknown",
                              "the service-manager state is unreadable; the owned job and its "
                              "artifacts stay untouched", label=label)
        if state == "exited":
            owned = any(os_job_owns(backend, label, spec)
                        for spec in run_dir.glob("attempt-*/spec.json"))
            if not owned:
                raise BrokerError("job-not-owned",
                                  "an exited job for this session is not owned by a recorded "
                                  "attempt; leave it", label=label)
            os_unload(backend, label)
    # Remove only attempt dirs no loaded job references any more.
    removed = 0
    if run_dir.exists():
        for attempt in sorted(run_dir.glob("attempt-*")):
            if backend != "unsupported" and os_job_owns(backend, label, attempt / "spec.json"):
                continue
            remove_quiet(attempt)
            removed += 1
        try:
            if not any(run_dir.iterdir()):
                remove_quiet(run_dir)
        except OSError:
            pass
    return {"schema": SCHEMA, "result": "cleaned", "label": label, "attempts_removed": removed}


# --------------------------------------------------------------------------- cli


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Outside-caller holder launcher (issue #266)")
    parser.add_argument("--internal-run", action="store_true")
    parser.add_argument("--spec")
    parser.add_argument("mode", nargs="?", choices=["submit", "cleanup"])
    parser.add_argument("--platform")
    parser.add_argument("--session")
    parser.add_argument("--repo")
    parser.add_argument("--record-dir")
    parser.add_argument("--socket")
    parser.add_argument("--log")
    parser.add_argument("--cwd")
    parser.add_argument("--run-base")
    parser.add_argument("--ready-timeout", type=float, default=DEFAULT_READY_TIMEOUT)
    parser.add_argument("--backend", default="auto", help="auto | launchd | systemd-user")
    parser.add_argument("--child-record")
    parser.add_argument("--argv-json")
    parser.add_argument("--env-allow", action="append", default=[])
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
        if ns.mode == "cleanup":
            print(json.dumps(do_cleanup(ns), sort_keys=True))
            return 0
        if ns.mode != "submit":
            raise BrokerError("mode-required", "choose submit or cleanup")
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
