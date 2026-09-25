#!/usr/bin/env python3
"""Issue #51 Mission 3: offline Runner integration of ZCode as the eighth worker.

Drives real ``kaola-acp.py`` (checkout layout and the generated Skill once it
exists) plus ``kaola-tmux.sh`` dispatch (ACP only, Issue #130). The backend is
``tests/contract/fake-zcode-app-server.py``, never an installed ZCode.app.
No network, no account, no PATH search for ``zcode``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "zcode-kaola-project-runner"
CHECKOUT_CLI = ROOT / "scripts" / "kaola-acp.py"
SKILL_CLI = SKILL / "scripts" / "kaola-acp.py"
ADAPTER_SRC = ROOT / "scripts" / "kaola-zcode-acp.py"
SHELL_ADAPTER = ROOT / "scripts" / "adapters" / "zcode.sh"
TMUX = ROOT / "scripts" / "kaola-tmux.sh"
RENDERER = ROOT / "scripts" / "render-skills.py"
INSTALLER = ROOT / "scripts" / "install-local.sh"
LOCATOR = ROOT / "scripts" / "kaola-locate.py"
MANIFEST = ROOT / "platforms" / "zcode.yaml"
FAKE = ROOT / "tests" / "contract" / "fake-zcode-app-server.py"
PROBE = ROOT / "tests" / "contract" / "hooks" / "zcode-probe"
ACP_TOKEN = "$SKILL_DIR/scripts/kaola-zcode-acp.py"
PYTHON = sys.executable or shutil.which("python3")
DENIED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "ZCODE_API_KEY",
    "ZCODE_BASE_URL",
    "ZCODE_MODEL",
    "ZCODE_PROVIDER",
    "ZCODE_CREDENTIAL_SECRET",
    "ZCODE_BIGMODEL_USAGE_API_KEY",
    "ZCODE_BIGMODEL_USAGE_QUOTA_URL",
    "ZCODE_ACP_REMOTE",
    "ZCODE_ACP_REMOTE_TOKEN",
    "ZCODE_ACP_HUB_HOST",
    "ZCODE_ACP_HUB_PORT",
)
# The desktop provider registry (`v2/config.json`) and plan cache are the two
# read-only exceptions (Issue #51 owner correction); everything else stays shut.
FORBIDDEN_OPEN_MARKERS = (
    "/.zcode/cli/",
    "credentials.json",
    "setting.json",
    "tasks-index.sqlite",
    "telemetry-state.json",
    "/.zcode/v2/certs",
    "zcode-acp/config.json",
)
DESKTOP_CONFIG_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-coding-plan-cache.json"
FIXTURE_SECRET = json.loads(DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"))["provider"][
    "builtin:bigmodel-coding-plan"]["options"]["apiKey"]

CHECKS: list[str] = []

# Issue #151: the zcode-probe monkeypatches os.open, and python 3.9's pathlib
# binds its accessor functions as methods, so a probe-loaded child that opens
# a Path dies with "open() takes at most 3 positional arguments (4 given)"
# before the adapter can report ready. Python >= 3.10 dropped that accessor.
# The rows that drive a real probe-loaded adapter child skip with a counted,
# named receipt when the prerequisite is absent; on python >= 3.10 they run
# unchanged (detection, not weakening).
PYTHON_GE_3_10 = sys.version_info >= (3, 10)
PYTHON_RECEIPT = (
    "prerequisite missing: python >= 3.10 - the probe's os.open monkeypatch "
    f"is incompatible with python {sys.version_info.major}.{sys.version_info.minor} "
    "pathlib _NormalAccessor (open() takes at most 3 positional arguments "
    "(4 given))"
)


def prerequisite(condition: bool, receipt: str):
    """Issue #151: mark a test row with an explicit skip receipt when its
    dev-machine prerequisite is absent. main() prints and counts the receipt;
    with the prerequisite present the row runs unchanged."""
    def mark(test):
        if not condition:
            test.__skip_receipt__ = receipt
        return test
    return mark


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    out = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
    ).stdout.strip()
    return bool(out) and not out.startswith("Z")


def wait_until(predicate, timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timeout: {label}")


def parse_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition(":")
            result[key.strip()] = json.loads(value.strip())
    return result


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Sandbox:
    """Isolated Runner environment: HOME, repo, record root, explicit fake runtime."""

    def __init__(self, name: str, scenario: str = "basic"):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-i51-{name}-"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        self.trap_dir = self.dir / "path-trap"
        self.trap_hit = self.dir / "path-trap-hit"
        self.open_log = self.dir / "opens.jsonl"
        self.fake_record = self.dir / "fake-record.json"
        self.scenario = scenario
        for path in (self.home, self.repo, self.record_root, self.trap_dir):
            path.mkdir(parents=True)
        (self.home / ".zcode" / "v2").mkdir(parents=True)
        (self.home / ".config" / "zcode-acp").mkdir(parents=True)
        (self.home / ".zcode" / "cli").mkdir(parents=True)
        (self.home / ".zcode" / "v2" / "config.json").write_text(
            DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "credentials.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "setting.json").write_text("{}\n", encoding="utf-8")
        (self.home / ".zcode" / "v2" / "tasks-index.sqlite").write_bytes(b"")
        (self.home / ".zcode" / "cli" / "config.json").write_text('{"hooks":{}}\n', encoding="utf-8")
        (self.home / ".config" / "zcode-acp" / "config.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        trap = self.trap_dir / "zcode"
        trap.write_text(f"#!/bin/sh\ntouch '{self.trap_hit}'\nexit 97\n", encoding="utf-8")
        trap.chmod(trap.stat().st_mode | stat.S_IXUSR)
        self.entry = self._write_entry()
        self.node = Path(PYTHON).resolve()
        self.canary = f"canary-{uuid.uuid4()}"
        self.sessions: list[tuple[Path, str]] = []

    def _write_entry(self) -> Path:
        entry = self.dir / f"zcode-entry-{self.scenario}.py"
        entry.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {self.scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(self.fake_record)!r}\n"
            f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        entry.chmod(entry.stat().st_mode | stat.S_IXUSR)
        return entry

    def env(self, *, with_runtime: bool = True, **overrides: str | None) -> dict[str, str]:
        base = {
            "PATH": f"{self.trap_dir}:{os.environ.get('PATH', '')}",
            "HOME": str(self.home),
            "LANG": os.environ.get("LANG", "C"),
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "PYTHONPATH": str(PROBE),
            "PYTHONUNBUFFERED": "1",
            "ZCODE_OPEN_LOG": str(self.open_log),
            "KAOLA_FAKE_CANARY": self.canary,
        }
        for name in DENIED_ENV:
            base[name] = f"must-not-forward-{name}"
        if with_runtime:
            base["KAOLA_ZCODE_ENTRY"] = str(self.entry)
            base["KAOLA_ZCODE_NODE"] = str(self.node)
        for key, value in overrides.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        return base

    def session(self) -> str:
        return f"zcode-kaola-i51-{uuid.uuid4().hex[:8]}"

    def invoke(
        self,
        entry: Path,
        command: str,
        *args: str,
        session: str | None = None,
        timeout: float = 60,
        with_runtime: bool = True,
        **env_overrides: str | None,
    ) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        argv = [PYTHON, str(entry), "zcode", command, "--repo", str(self.repo)]
        if session:
            argv += ["--session", session]
            if command == "start":
                self.sessions.append((entry, session))
        argv += list(args)
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            env=self.env(with_runtime=with_runtime, **env_overrides),
            timeout=timeout,
        )
        payload = None
        text = (result.stdout or "").strip()
        if text:
            try:
                payload = json.loads(text.splitlines()[-1])
            except ValueError:
                payload = None
        return result, payload

    def cli(
        self,
        entry: Path,
        command: str,
        *args: str,
        session: str | None = None,
        timeout: float = 60,
        with_runtime: bool = True,
        **env_overrides: str | None,
    ) -> dict:
        result, payload = self.invoke(
            entry, command, *args, session=session, timeout=timeout,
            with_runtime=with_runtime, **env_overrides,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"{command} exit {result.returncode}: {(result.stderr or '')[-800:]}"
            )
        if not isinstance(payload, dict):
            raise AssertionError(
                f"{command} printed no JSON receipt: {(result.stdout or '')[-400:]} "
                f"{(result.stderr or '')[-400:]}"
            )
        return payload

    def tmux(self, *args: str, with_runtime: bool = True) -> tuple[int, dict | None, str]:
        result = subprocess.run(
            ["bash", str(TMUX), "zcode", *args],
            capture_output=True,
            text=True,
            env=self.env(with_runtime=with_runtime),
            timeout=60,
        )
        payload = None
        text = (result.stdout or "").strip()
        if text:
            try:
                payload = json.loads(text.splitlines()[-1])
            except ValueError:
                payload = None
        return result.returncode, payload, (result.stderr or "")

    def fake(self) -> dict:
        if not self.fake_record.is_file():
            return {}
        return json.loads(self.fake_record.read_text(encoding="utf-8"))

    def open_entries(self) -> list[str]:
        if not self.open_log.is_file():
            return []
        return [
            line.strip()
            for line in self.open_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def cleanup(self) -> None:
        for entry, session in self.sessions:
            subprocess.run(
                [
                    PYTHON, str(entry), "zcode", "stop",
                    "--repo", str(self.repo), "--session", session, "--force",
                ],
                capture_output=True,
                env=self.env(),
                timeout=30,
            )
        fake_pid = self.fake().get("pid")
        if pid_alive(fake_pid):
            try:
                os.kill(int(fake_pid), 9)
            except OSError:
                pass
        shutil.rmtree(self.dir, ignore_errors=True)


def test_manifest_renderer_and_inventory() -> None:
    check(MANIFEST.is_file(), "platforms/zcode.yaml exists")
    manifest = parse_manifest(MANIFEST)
    check(manifest["id"] == "zcode", "manifest id is zcode")
    check(manifest["skill_name"] == "zcode-kaola-project-runner", "skill_name is zcode-kaola-project-runner")
    check("default_transport" not in manifest, "default_transport is gone: every worker is ACP-only (Issue #130)")
    command = manifest["acp_command"]
    check(ACP_TOKEN in command, "acp_command is Skill-relative to kaola-zcode-acp.py")
    lowered = command.lower()
    check(
        all(token not in lowered for token in ("npx", "npm", "registry", "latest")),
        "acp_command names neither registry nor npm/npx/latest",
    )
    check(manifest["acp_login_requires_pty"] == "false", "login is a desktop-App act; PTY is unsupported")
    allow = manifest["acp_env_allowlist"]
    check(allow in ("", "[]") or allow.split(",") == [""], "acp_env_allowlist is empty")
    check(manifest["acp_model_config_id"] == "model", "acp_model_config_id is model")
    effort = manifest.get("acp_effort_config_id") or ""
    check(effort in ("", "thought"), "thought/effort id is thought if present")
    check(SHELL_ADAPTER.is_file(), "scripts/adapters/zcode.sh exists")

    acp = load_module(CHECKOUT_CLI, "kaola_acp_i51")
    check("zcode" in acp.PLATFORMS, "kaola-acp.py accepts platform zcode")
    check("grok-bot" not in acp.PLATFORMS, "Grok Bot remains not a worker")
    check(acp.ACP_SKIP_MODE.get("zcode") == "yolo", "skip-all mode vocabulary is yolo")
    locate = load_module(LOCATOR, "kaola_locate_i51")
    check("zcode" in locate.WORKER_IDS, "locator --worker zcode is a supported worker id")
    check("grok-bot" not in locate.WORKER_IDS, "locator does not treat grok-bot as a worker")

    shipped = SKILL / "scripts" / "kaola-zcode-acp.py"
    check(shipped.is_file(), "generated ZCode worker ships scripts/kaola-zcode-acp.py")
    check(
        shipped.read_bytes() == ADAPTER_SRC.read_bytes(),
        "generated adapter is byte-identical to repo scripts/kaola-zcode-acp.py",
    )
    others = [
        path for path in (ROOT / "skills").iterdir()
        if path.is_dir() and path.resolve() != SKILL.resolve()
    ]
    for package in others:
        check(
            not (package / "scripts" / "kaola-zcode-acp.py").exists(),
            f"{package.name} does not ship kaola-zcode-acp.py",
        )
        check(
            "zcode-acp" not in " ".join(
                p.as_posix() for p in package.rglob("*") if "zcode-acp" in p.as_posix()
            ),
            f"{package.name} ships no third_party/zcode-acp tree",
        )
    host = ROOT / "hosts" / "grok-bot"
    if host.is_dir():
        for product in host.rglob("*"):
            if not product.is_file():
                continue
            rel = product.relative_to(host).as_posix()
            check("kaola-zcode-acp.py" not in rel, f"host product path {rel} is not the ZCode adapter")
            check("zcode-acp" not in rel, f"host product path {rel} is not a zcode-acp tree")
            try:
                text = product.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            check("kaola-zcode-acp.py" not in text, f"host product {rel} does not embed the adapter")
    result = subprocess.run([PYTHON, str(RENDERER), "--check"], capture_output=True, text=True)
    check(result.returncode == 0, f"render-skills.py --check passes: {result.stderr.strip()}")


def test_fail_closed_without_explicit_runtime() -> None:
    sandbox = Sandbox("failclosed")
    try:
        result, payload = sandbox.invoke(
            CHECKOUT_CLI, "preflight", with_runtime=False
        )
        combined = (result.stderr or "") + (result.stdout or "")
        check("invalid choice" not in combined, "zcode is a known ACP platform")
        failed = result.returncode != 0 or (
            isinstance(payload, dict) and payload.get("error") is not None
        )
        check(failed, "preflight without KAOLA_ZCODE_ENTRY/NODE fails closed")
        check(not sandbox.trap_hit.exists(), "preflight did not execute a PATH zcode trap")
        check(sandbox.fake() == {}, "preflight without explicit runtime spawned no app-server")

        session = sandbox.session()
        result, payload = sandbox.invoke(
            CHECKOUT_CLI, "start", session=session, with_runtime=False
        )
        failed = result.returncode != 0 or (
            isinstance(payload, dict) and payload.get("error") is not None
        )
        check(failed, "start without KAOLA_ZCODE_ENTRY/NODE fails closed")
        if isinstance(payload, dict):
            check(
                payload.get("state") != "ready" and payload.get("acp_session_id") in (None, ""),
                "start without explicit runtime did not report a ready session",
            )
        check(not sandbox.trap_hit.exists(), "start did not execute a PATH zcode trap")
        check(sandbox.fake() == {}, "start without explicit runtime spawned no app-server")

        result, payload = sandbox.invoke(
            CHECKOUT_CLI, "preflight",
            KAOLA_ZCODE_ENTRY="zcode.cjs",
            KAOLA_ZCODE_NODE=str(sandbox.node),
        )
        failed = result.returncode != 0 or (
            isinstance(payload, dict) and payload.get("error") is not None
        )
        check(failed, "non-absolute KAOLA_ZCODE_ENTRY fails closed")
        check(not sandbox.trap_hit.exists(), "relative entry did not fall back to PATH zcode")

        missing = str(sandbox.dir / "nowhere" / "zcode.cjs")
        result, payload = sandbox.invoke(
            CHECKOUT_CLI, "start", session=sandbox.session(),
            KAOLA_ZCODE_ENTRY=missing,
            KAOLA_ZCODE_NODE=str(sandbox.node),
        )
        failed = result.returncode != 0 or (
            isinstance(payload, dict) and payload.get("error") is not None
        )
        check(failed, "missing KAOLA_ZCODE_ENTRY file fails closed")
        check(sandbox.fake() == {}, "missing entry spawned no app-server")

        result, payload = sandbox.invoke(
            CHECKOUT_CLI, "preflight",
            KAOLA_ZCODE_ENTRY=str(sandbox.entry),
            KAOLA_ZCODE_NODE="python3",
        )
        failed = result.returncode != 0 or (
            isinstance(payload, dict) and payload.get("error") is not None
        )
        check(failed, "non-absolute KAOLA_ZCODE_NODE fails closed")
        check(not sandbox.trap_hit.exists(), "PATH zcode trap never ran during fail-closed cases")
    finally:
        sandbox.cleanup()


@prerequisite(PYTHON_GE_3_10, PYTHON_RECEIPT)
def test_start_send_cancel_stop_schema_v3() -> None:
    check(SKILL_CLI.is_file(), "generated Skill kaola-acp.py exists")
    sandbox = Sandbox("turns", scenario="basic")
    try:
        session = sandbox.session()
        receipt = sandbox.cli(SKILL_CLI, "start", "--mode", "yolo", session=session)
        check(receipt.get("schema_version") == 3, "start receipt is schema_version 3")
        check(receipt.get("error") is None and receipt.get("state") == "ready",
              f"start reaches ready ({receipt.get('error')})")
        check(receipt.get("acp_session_id"), "start reports an ACP session id")
        applied = receipt.get("config_application") or {}
        mode = applied.get("mode") or {}
        if mode.get("applied"):
            check(mode.get("value") == "yolo", "start applies skip-all mode yolo")
        transport = receipt.get("transport") or {}
        auth = transport.get("auth_methods")
        if auth is not None:
            check(auth == [], "initialize advertises authMethods=[]")
        agent = transport.get("agent_info") or {}
        if agent:
            check(agent.get("name") == "kaola-zcode-acp", "ACP agent is kaola-zcode-acp")

        receipt = sandbox.cli(SKILL_CLI, "send", "--text", "hello", session=session)
        check(receipt.get("schema_version") == 3, "send receipt is schema_version 3")
        check(
            receipt.get("outcome") in ("turn_completed", "completed")
            or receipt.get("mutation_status") == "completed",
            f"send completes a turn ({receipt.get('outcome')} {receipt.get('error')})",
        )
        blob = json.dumps(receipt)
        check("hello" in blob and "from zcode" in blob, "prompt streaming carries fake final text")
        record = sandbox.fake()
        check(record.get("argv", [])[:2] == ["app-server", "--stdio"],
              "adapter spawned app-server --stdio against the fake")
        env_names = record.get("env_names") or []
        leaked = [name for name in DENIED_ENV if name in env_names]
        check(leaked == [], f"denied env names absent from ZCode app-server child: {leaked}")
        check(not sandbox.trap_hit.exists(), "PATH zcode never ran")

        forbidden = [
            entry for entry in sandbox.open_entries()
            if any(marker in entry for marker in FORBIDDEN_OPEN_MARKERS)
        ]
        check(forbidden == [], f"adapter opened no credential/CLI-config files: {forbidden}")
        registry_writes = [
            entry for entry in sandbox.open_entries()
            if "/.zcode/v2/" in entry and not entry.endswith(":mode=r")
        ]
        check(registry_writes == [], f"desktop registry opened read-only only: {registry_writes}")
        overlays = record.get("overlays") or []
        check(bool(overlays) and overlays[0].get("method") == "session/create",
              "session/create carried the in-memory runtimeModel overlay")
        check(all(o.get("providerId") == "builtin:bigmodel-coding-plan" for o in overlays),
              "overlay names the enabled GLM Coding Plan provider only")
        check(all(o.get("apiKeySource") == "inline" and o.get("apiKeyValue") == FIXTURE_SECRET
                  for o in overlays),
              "plan credential reached the app-server in memory (inline union)")
        meta = ((agent.get("_meta") or {}).get("zcode") or {})
        check(meta.get("plan") == "coding-plan" and meta.get("providerId") == "builtin:bigmodel-coding-plan",
              "start receipt agent_info carries secret-free Coding Plan provider facts")
        check(meta.get("planCacheStatus") == "available", "plan cache status reported as available")
        record_blob = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sandbox.record_root.rglob("*") if path.is_file()
        )
        check(FIXTURE_SECRET not in json.dumps(receipt) and FIXTURE_SECRET not in blob
              and FIXTURE_SECRET not in record_blob,
              "plan credential never appears in receipts or Runner records")
        cli_config = sandbox.home / ".zcode" / "cli" / "config.json"
        check(cli_config.read_text(encoding="utf-8") == '{"hooks":{}}\n',
              "~/.zcode/cli/config.json untouched")
        tcp = [
            entry for entry in sandbox.open_entries()
            if entry.startswith("socket.connect:(")
        ]
        check(tcp == [], f"adapter made no TCP socket.connect: {tcp}")

        status = sandbox.cli(SKILL_CLI, "status", session=session)
        check(status.get("schema_version") == 3, "status receipt is schema_version 3")
        check(status.get("acp_session_id") == receipt.get("acp_session_id") or status.get("error") is None,
              "status reports the same session")
    finally:
        sandbox.cleanup()

    hanging = Sandbox("cancel", scenario="slow")
    try:
        session = hanging.session()
        start = hanging.cli(SKILL_CLI, "start", "--mode", "yolo", session=session)
        check(start.get("error") is None, f"slow-scenario start reaches ready ({start.get('error')})")
        sent = hanging.cli(SKILL_CLI, "send", "--text", "hang", "--no-wait", session=session)
        check(
            sent.get("outcome") in ("in_progress", "turn_started")
            or sent.get("mutation_status") == "in_progress"
            or sent.get("error") is None,
            "a long prompt is accepted without waiting",
        )
        wait_until(lambda: bool(hanging.fake().get("pid")), 15, "slow fake app-server launched")
        fake_pid = hanging.fake().get("pid")
        check(pid_alive(fake_pid), "fake app-server is running during the hung turn")
        cancelled = hanging.cli(SKILL_CLI, "cancel", session=session)
        check(
            cancelled.get("outcome") in ("turn_canceled", "cancelled", "canceled", "cancel-unconfirmed")
            or cancelled.get("stop_reason") in ("cancelled", "canceled")
            or cancelled.get("error") is None,
            f"cancel settles the turn ({cancelled.get('outcome')} {cancelled.get('error')})",
        )
        # Cancel stops the turn; the long-lived app-server stays until session stop
        # so load/resume remains possible. Process cleanup is the stop gate below.
        status = hanging.cli(SKILL_CLI, "status", session=session)
        holder_pid, agent_pid = status.get("holder_pid"), status.get("agent_pid")
        stopped = hanging.cli(SKILL_CLI, "stop", session=session)
        check(stopped.get("schema_version") == 3, "stop receipt is schema_version 3")
        check(stopped.get("error") is None, f"stop succeeds ({stopped.get('error')})")
        residuals = stopped.get("residual_pids")
        if residuals is not None:
            check(residuals == [], "stop reports no residual pids")
        wait_until(
            lambda: not pid_alive(holder_pid) and not pid_alive(agent_pid) and not pid_alive(fake_pid),
            8,
            "holder, adapter, and fake app-server exited",
        )
        check(not hanging.trap_hit.exists(), "PATH zcode never ran during cancel/stop")
    finally:
        hanging.cleanup()


def test_transport_dispatch_is_acp_only() -> None:
    """Issue #130: --transport pty is refused with the typed transport-pty-retired
    receipt; --transport acp and no override both reach kaola-acp.py."""
    sandbox = Sandbox("dispatch")
    try:
        session = sandbox.session()
        code, payload, stderr = sandbox.tmux(
            "status", "--repo", str(sandbox.repo), "--session", session, "--transport", "pty"
        )
        check("unknown platform" not in stderr, "kaola-tmux.sh accepts platform zcode")
        check(code != 0 and isinstance(payload, dict), f"--transport pty is refused with a receipt ({stderr[-300:]})")
        if isinstance(payload, dict):
            check(payload.get("reason") == "transport-pty-retired", f"--transport pty is transport-pty-retired ({payload})")
            check(payload.get("transport") == {"requested": "pty", "supported": ["acp"]}, "refusal names acp as the only transport")
        code, payload, stderr = sandbox.tmux(
            "status", "--repo", str(sandbox.repo), "--session", session, "--transport", "acp"
        )
        check("unknown platform" not in stderr, "--transport acp is dispatched for zcode")
        if isinstance(payload, dict) and payload.get("transport"):
            check(payload["transport"].get("selected") == "acp", "--transport acp reaches kaola-acp.py")
        code, payload, stderr = sandbox.tmux(
            "status", "--repo", str(sandbox.repo), "--session", session
        )
        if isinstance(payload, dict) and payload.get("transport"):
            check(payload["transport"] == {"selected": "acp"}, "no override reaches kaola-acp.py")
        identity = SHELL_ADAPTER.read_text(encoding="utf-8")
        check(
            re.search(r'ADAPTER_ID="zcode"', identity) is not None,
            "shell adapter declares ADAPTER_ID=zcode",
        )
    finally:
        sandbox.cleanup()


@prerequisite(PYTHON_GE_3_10, PYTHON_RECEIPT)
def test_skip_all_mode_is_yolo_on_acp() -> None:
    """CLI 0.16.5 --help: --mode is Permission mode, values build|edit|plan|yolo,
    default yolo for --prompt. Packaged PermissionService: 'Yolo mode bypasses
    permission prompts'. ACP skip-all is yolo."""
    acp = load_module(CHECKOUT_CLI, "kaola_acp_i51_mode")
    check(acp.ACP_SKIP_MODE.get("zcode") == "yolo", "ACP_SKIP_MODE zcode is yolo")
    tmux = TMUX.read_text(encoding="utf-8")
    # Issue #181: the per-platform default lives once, in ACP_SKIP_MODE. The
    # tmux entry forwards only an explicit --permission-mode, so it carries no
    # zcode mode case; the behavioural check below proves the default lands.
    check(
        re.search(r"\bzcode\) acp_args\+=\(--mode yolo\)", tmux) is None,
        "the tmux entry no longer repeats the platform mode table",
    )
    check("permission_mode_given" in tmux, "tmux forwards an explicit mode")
    adapter_src = ADAPTER_SRC.read_text(encoding="utf-8")
    check(
        re.search(r'add_argument\("--mode".*default="yolo"', adapter_src) is not None,
        "ACP adapter argparse default mode is yolo",
    )
    sandbox = Sandbox("skip-all")
    try:
        session = sandbox.session()
        receipt = sandbox.cli(SKILL_CLI, "start", session=session)
        applied = (receipt.get("config_application") or {}).get("mode") or {}
        check(
            applied.get("applied") is True and applied.get("value") == "yolo",
            f"ACP start without caller --mode applies yolo ({applied})",
        )
    finally:
        sandbox.cleanup()


def test_installer_knows_zcode_and_rejects_zcode_bot() -> None:
    sandbox = Sandbox("install")
    try:
        dest = sandbox.dir / "skills-dest"
        dest.mkdir()
        env = sandbox.env()
        env["HOME"] = str(sandbox.home)
        refused = subprocess.run(
            [
                "bash", str(INSTALLER),
                "--skills-dir", str(dest),
                "--platform", "zcode-bot",
                "--method", "copy",
                "--no-orchestrator",
                "--no-bin-links",
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=30,
        )
        check(refused.returncode != 0, "unknown platform zcode-bot is refused")
        check(
            "unknown platform" in (refused.stderr + refused.stdout),
            "zcode-bot reports unknown platform",
        )
        grok_bot = subprocess.run(
            [
                "bash", str(INSTALLER),
                "--skills-dir", str(dest),
                "--platform", "grok-bot",
                "--method", "copy",
                "--no-orchestrator",
                "--no-bin-links",
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=30,
        )
        check(grok_bot.returncode != 0, "--platform grok-bot remains invalid")

        installed = subprocess.run(
            [
                "bash", str(INSTALLER),
                "--skills-dir", str(dest),
                "--platform", "zcode",
                "--method", "copy",
                "--no-orchestrator",
                "--no-bin-links",
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=60,
        )
        check(installed.returncode == 0, f"install-local.sh --platform zcode succeeds: {installed.stderr[-400:]}")
        copied = dest / "zcode-kaola-project-runner" / "scripts" / "kaola-zcode-acp.py"
        check(copied.is_file(), "sandbox copy install includes the ZCode adapter")
        check(
            copied.read_bytes() == ADAPTER_SRC.read_bytes(),
            "installed adapter matches repo scripts/kaola-zcode-acp.py",
        )
        uninstalled = subprocess.run(
            [
                "bash", str(INSTALLER),
                "--skills-dir", str(dest),
                "--platform", "zcode",
                "--no-orchestrator",
                "--no-bin-links",
                "--uninstall",
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=30,
        )
        check(uninstalled.returncode == 0, f"zcode uninstalls cleanly: {uninstalled.stderr[-400:]}")
        check(
            not (dest / "zcode-kaola-project-runner").exists(),
            "uninstall removes the zcode Skill copy",
        )
    finally:
        sandbox.cleanup()


def main() -> int:
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failures = 0
    skips = 0
    for test in tests:
        receipt = getattr(test, "__skip_receipt__", None)
        if receipt is not None:
            skips += 1
            print(f"SKIP {test.__name__} ({receipt})")
            continue
        before = len(CHECKS)
        try:
            test()
            print(f"PASS {test.__name__} ({len(CHECKS) - before} checks)")
        except Exception as exc:  # noqa: BLE001 - report every failure, keep running
            failures += 1
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(
        f"test-issue-51-runner-integration: {len(tests) - failures - skips}/{len(tests)} tests, "
        f"{skips} skipped (prerequisite receipts), {len(CHECKS)} checks"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
