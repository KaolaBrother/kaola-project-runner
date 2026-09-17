#!/usr/bin/env python3
"""Issue #62 Phase 1: ZCode Host lifecycle contract — session/process isolation.

The test harness starts a real outer Runner session (the ZCode Host) and then,
in the test process (the same role as the Host agent running a nested start),
explicitly starts a real inner ZCode Worker Runner session, setting the holder
child-record env to the outer record's ``children.jsonl`` exactly as an outer
holder would for its agent. This establishes the nested-isolation CONTRACT —
separate process groups, separate record roots, exact stop, recorded-inner
sweep — without ever executing a prompt as a shell command. Real
model-driven Host dispatch to a Worker is out of scope here and deferred to a
strictly controlled live E2E. No installed ZCode, no login, no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_CLI = ROOT / "scripts" / "kaola-acp.py"
FAKE = ROOT / "tests" / "contract" / "fake-zcode-app-server.py"
PYTHON = sys.executable

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
# Explicit runtime facts a nested ZCode worker may inherit are asserted per-child
# in test-zcode-acp-contract.py; the holder's child-record path is deliberately
# never forwarded (trust boundary) and is asserted there too.
DESKTOP_CONFIG_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-coding-plan-cache.json"
FIXTURE_SECRET = json.loads(DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"))["provider"][
    "builtin:bigmodel-coding-plan"]["options"]["apiKey"]

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


class Sandbox:
    """Isolated Runner environment for a two-layer ZCode chain (harness-driven)."""

    def __init__(self, name: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-zcode-host-{name}-"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        self.outer_fake = self.dir / "outer-fake.json"
        self.inner_fake = self.dir / "inner-fake.json"
        for path in (self.home, self.repo, self.record_root):
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
        self.outer_entry = self._write_entry("basic", self.outer_fake)
        self.inner_entry = self._write_entry("basic", self.inner_fake)
        self.node = Path(PYTHON).resolve()
        self.sessions: list[str] = []

    def _write_entry(self, scenario: str, record: Path) -> Path:
        entry = self.dir / f"zcode-entry-{scenario}.py"
        entry.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            f"os.environ['FAKE_ZCODE_SCENARIO'] = {scenario!r}\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(record)!r}\n"
            f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        entry.chmod(entry.stat().st_mode | 0o755)
        return entry

    def env(self, *, with_runtime: bool = True, **overrides: str | None) -> dict[str, str]:
        base = {
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "HOME": str(self.home),
            "LANG": os.environ.get("LANG", "C"),
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "PYTHONUNBUFFERED": "1",
        }
        for name in DENIED_ENV:
            base[name] = f"must-not-forward-{name}"
        if with_runtime:
            base["KAOLA_ZCODE_ENTRY"] = str(self.outer_entry)
            base["KAOLA_ZCODE_NODE"] = str(self.node)
        for key, value in overrides.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = value
        return base

    def session(self) -> str:
        return f"zcode-host-{uuid.uuid4().hex[:8]}"

    def record_dir(self, session: str) -> Path:
        # The Runner hashes the realpath of the repo root (resolve_repo) to
        # derive the per-session record directory ("/var" -> "/private/var").
        real_repo = os.path.realpath(str(self.repo))
        digest = hashlib.sha256(real_repo.encode("utf-8")).hexdigest()[:16]
        return self.record_root / "zcode" / session / digest

    def invoke(
        self,
        entry: Path,
        command: str,
        *args: str,
        session: str | None = None,
        timeout: float = 120,
        with_runtime: bool = True,
        **env_overrides: str | None,
    ) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        argv = [PYTHON, str(entry), "zcode", command, "--repo", str(self.repo)]
        if session:
            argv += ["--session", session]
            if command == "start":
                self.sessions.append(session)
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
        timeout: float = 120,
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

    def fake(self, path: Path) -> dict:
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return {}

    def cleanup(self) -> None:
        for session in list(self.sessions):
            try:
                self.invoke(CHECKOUT_CLI, "stop", "--force", session=session, timeout=30)
            except Exception:
                pass
        for path in (self.outer_fake, self.inner_fake):
            fake_pid = self.fake(path).get("pid")
            if pid_alive(fake_pid):
                try:
                    os.kill(int(fake_pid), signal.SIGKILL)
                except (OSError, TypeError):
                    pass
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)


def start_outer(sandbox: "Sandbox", outer: str) -> dict:
    """Start the outer ZCode Host session through the real Runner CLI."""
    receipt = sandbox.cli(CHECKOUT_CLI, "start", "--mode", "yolo", session=outer)
    check(receipt.get("error") is None and receipt.get("state") == "ready",
          f"outer Host start reaches ready ({receipt.get('error')})")
    check(receipt.get("acp_session_id"), "outer start exposes an ACP session id")
    return receipt


def start_inner(sandbox: "Sandbox", inner: str, outer: str) -> dict:
    """Start the inner ZCode Worker exactly as the outer Host agent would: the
    test harness (in the agent role) sets KAOLA_ACP_CHILD_RECORD to the outer
    record's children.jsonl, so the nested start appends the inner holder's
    identity there and the outer exact stop can sweep it."""
    children = sandbox.record_dir(outer) / "children.jsonl"
    receipt = sandbox.cli(
        CHECKOUT_CLI, "start", "--mode", "yolo", session=inner,
        KAOLA_ACP_CHILD_RECORD=str(children),
        KAOLA_ZCODE_ENTRY=str(sandbox.inner_entry),
    )
    check(receipt.get("error") is None and receipt.get("state") == "ready",
          f"inner Worker start reaches ready ({receipt.get('error')})")
    check(receipt.get("acp_session_id"), "inner start exposes an ACP session id")
    return receipt


def test_nested_two_layer_isolation_and_exact_stop() -> None:
    sandbox = Sandbox("nested")
    try:
        outer = sandbox.session()
        inner = sandbox.session()
        outer_start = start_outer(sandbox, outer)
        inner_start = start_inner(sandbox, inner, outer)
        outer_holder = outer_start.get("holder_pid")
        outer_agent = outer_start.get("agent_pid")
        inner_holder = inner_start.get("holder_pid")
        inner_agent = inner_start.get("agent_pid")
        check(all(isinstance(pid, int) and pid > 0 for pid in
                  (outer_holder, outer_agent, inner_holder, inner_agent)),
              "all four holders/agents have real pids")

        # Child record: the nested start appended the inner holder's identity
        # to the OUTER record's children.jsonl via the harness-provided env.
        child_record = inner_start.get("child_record") or {}
        check(child_record.get("recorded") is True, f"inner start recorded its holder ({child_record})")
        check(
            Path(str(child_record.get("path"))).resolve()
            == (sandbox.record_dir(outer) / "children.jsonl").resolve(),
            f"child record path is the outer children.jsonl ({child_record.get('path')})",
        )
        check(child_record.get("pid") == inner_holder, "child record names the inner holder pid")
        check(child_record.get("pgid") == inner_holder, "inner holder leads its own process group")
        children = sandbox.record_dir(outer) / "children.jsonl"
        lines = children.read_text(encoding="utf-8").splitlines()
        check(len(lines) == 1, f"outer children.jsonl has exactly one entry ({lines})")
        entry = json.loads(lines[0])
        check(entry == {"pid": inner_holder, "pgid": inner_holder,
                        "spawned_at": entry.get("spawned_at")}
              and isinstance(entry.get("spawned_at"), int),
              f"children.jsonl entry matches the inner holder ({entry})")

        # Process-group separation: every layer leads its own group.
        groups = {}
        for label, pid in (("outer-holder", outer_holder), ("outer-agent", outer_agent),
                           ("inner-holder", inner_holder), ("inner-agent", inner_agent)):
            try:
                groups[label] = os.getpgid(pid)
            except OSError:
                groups[label] = None
        check(all(g == pid for g, pid in zip(
            groups.values(), (outer_holder, outer_agent, inner_holder, inner_agent))),
            f"every layer leads its own process group ({groups})")
        check(len(set(groups.values())) == 4, f"four distinct process groups ({groups})")

        # Identity layers: separate named sessions with separate record roots.
        check(outer_start.get("session") == outer and inner_start.get("session") == inner,
              f"separate named Runner sessions ({outer_start.get('session')}, {inner_start.get('session')})")
        check(sandbox.record_dir(outer) != sandbox.record_dir(inner),
              "separate record-root entries per layer")

        # Credential/config boundary: the plan credential never appears in any
        # Runner receipt or record, and the nested start's CHILD_RECORD write
        # handle only ever names the outer children.jsonl. The per-child env
        # snapshot (explicit runtime facts forwarded, child-record write handle
        # and denied names never forwarded) is asserted exhaustively in
        # test-zcode-acp-contract.py with the same adapter code path.
        blob = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sandbox.record_root.rglob("*") if path.is_file()
        )
        check(FIXTURE_SECRET not in blob, "plan credential absent from all Runner records")
        check(FIXTURE_SECRET not in json.dumps(outer_start)
              and FIXTURE_SECRET not in json.dumps(inner_start),
              "plan credential absent from start receipts")
        check("KAOLA_ACP_CHILD_RECORD" not in json.dumps(outer_start)
              and "KAOLA_ACP_CHILD_RECORD" not in json.dumps(inner_start),
              "no receipt echoes the child-record env write handle")

        # Inner stop never reaches the outer Host.
        inner_stop = sandbox.cli(CHECKOUT_CLI, "stop", session=inner)
        check(inner_stop.get("error") is None, f"inner worker stops ({inner_stop.get('error')})")
        residuals = inner_stop.get("residual_pids")
        if residuals is not None:
            check(residuals == [], f"inner stop reports no residual pids ({residuals})")
        wait_until(lambda: not pid_alive(inner_holder) and not pid_alive(inner_agent),
                   8, "inner holder and adapter exited")
        check(pid_alive(outer_holder), "inner stop never touches the outer Host holder")
        check(pid_alive(outer_agent), "inner stop never touches the outer Host adapter")
        outer_status = sandbox.cli(CHECKOUT_CLI, "status", session=outer)
        check(outer_status.get("error") is None, f"outer Host still serves ({outer_status.get('error')})")

        # Outer stop leaves zero residue (recorded inner already gone).
        outer_stop = sandbox.cli(CHECKOUT_CLI, "stop", "--force", session=outer)
        check(outer_stop.get("error") is None, f"outer Host stops ({outer_stop.get('error')})")
        outer_residuals = outer_stop.get("residual_pids")
        if outer_residuals is not None:
            check(outer_residuals == [], f"outer stop reports no residual pids ({outer_residuals})")
        wait_until(lambda: not pid_alive(outer_holder) and not pid_alive(outer_agent),
                   8, "outer holder and adapter exited")
    finally:
        sandbox.cleanup()


def test_holder_lost_stop_force_sweeps_recorded_inner() -> None:
    sandbox = Sandbox("lost")
    try:
        outer = sandbox.session()
        inner = sandbox.session()
        outer_start = start_outer(sandbox, outer)
        inner_start = start_inner(sandbox, inner, outer)
        outer_holder = outer_start.get("holder_pid")
        inner_holder = inner_start.get("holder_pid")
        inner_agent = inner_start.get("agent_pid")
        wait_until(
            lambda: (sandbox.record_dir(outer) / "children.jsonl").is_file(),
            8, "outer children.jsonl written",
        )
        children = json.loads(
            (sandbox.record_dir(outer) / "children.jsonl").read_text(encoding="utf-8").splitlines()[0]
        )
        check(children["pid"] == inner_holder, "recorded child is the inner holder")

        # The outer Host holder dies first; the inner Worker is still alive and
        # only the child record identifies it for the exact sweep.
        os.kill(outer_holder, signal.SIGKILL)
        wait_until(lambda: not pid_alive(outer_holder), 5, "outer holder died")
        check(pid_alive(inner_holder), "inner holder survives the outer holder's death")

        stopped = sandbox.cli(CHECKOUT_CLI, "stop", "--force", session=outer)
        check(stopped.get("stopped") is True, "holder-lost stop reports stopped")
        check(stopped.get("holder_lost") is True, "stop detects the lost holder")
        swept = stopped.get("swept_pgids") or []
        check(inner_holder in swept, f"recorded inner holder group swept ({swept})")
        outer_record = sandbox.record_dir(outer) / "record.json"
        outer_agent_pgid = None
        if outer_record.is_file():
            try:
                outer_agent_pgid = json.loads(outer_record.read_text(encoding="utf-8")).get("agent_pgid")
            except ValueError:
                pass
        if isinstance(outer_agent_pgid, int) and outer_agent_pgid > 0:
            check(outer_agent_pgid in swept, f"orphaned outer adapter group swept too ({swept})")
        residuals = stopped.get("residual_pids")
        if residuals is not None:
            check(residuals == [], f"holder-lost sweep leaves no residual pids ({residuals})")
        wait_until(lambda: not pid_alive(inner_holder) and not pid_alive(inner_agent),
                   8, "recorded inner holder swept")
    finally:
        sandbox.cleanup()


def test_command_start_appends_child_record_when_env_present() -> None:
    sandbox = Sandbox("append")
    try:
        child = sandbox.dir / "children.jsonl"
        first = sandbox.session()
        second = sandbox.session()
        bare = sandbox.session()
        start1 = sandbox.cli(
            CHECKOUT_CLI, "start", "--mode", "yolo", session=first,
            KAOLA_ACP_CHILD_RECORD=str(child),
        )
        check(start1.get("error") is None and start1.get("state") == "ready",
              f"nested-flag start reaches ready ({start1.get('error')})")
        fact = start1.get("child_record") or {}
        check(fact.get("recorded") is True and fact.get("path") == str(child),
              f"start receipt carries the child_record fact ({fact})")
        check(fact.get("pid") == start1.get("holder_pid"), "receipt fact names the spawned holder")
        lines = child.read_text(encoding="utf-8").splitlines()
        check(len(lines) == 1, f"child record has one entry ({lines})")
        entry = json.loads(lines[0])
        check(entry == {"pid": fact["pid"], "pgid": fact["pgid"], "spawned_at": entry["spawned_at"]}
              and isinstance(entry["spawned_at"], int)
              and entry["pgid"] == entry["pid"],
              f"child record entry is exact ({entry})")

        start2 = sandbox.cli(
            CHECKOUT_CLI, "start", "--mode", "yolo", session=second,
            KAOLA_ACP_CHILD_RECORD=str(child),
        )
        check(start2.get("error") is None and start2.get("state") == "ready",
              f"second nested-flag start reaches ready ({start2.get('error')})")
        lines = child.read_text(encoding="utf-8").splitlines()
        check(len(lines) == 2, f"second start appends a second entry ({len(lines)} lines)")
        second_entry = json.loads(lines[1])
        check(second_entry["pid"] == start2.get("holder_pid")
              and second_entry["pid"] != entry["pid"],
              "second entry names the second holder only")

        # No env -> no child-record fact, no append.
        start3 = sandbox.cli(
            CHECKOUT_CLI, "start", "--mode", "yolo", session=bare,
            KAOLA_ACP_CHILD_RECORD=None,
        )
        check(start3.get("error") is None and start3.get("state") == "ready",
              f"bare start reaches ready ({start3.get('error')})")
        check("child_record" not in start3, "no child_record fact without the env")
        check(len(child.read_text(encoding="utf-8").splitlines()) == 2,
              "bare start appends nothing to the child record")
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
        f"test-zcode-host-contract: {len(tests) - failures}/{len(tests)} tests, "
        f"{len(CHECKS)} checks"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
