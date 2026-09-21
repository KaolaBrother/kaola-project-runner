#!/usr/bin/env python3
"""Issue #123: shared blocks are reference-counted, so one runtime installs or
uninstalls alone without touching what another runtime still uses.

Runs the real ``scripts/install-local.sh`` inside a shadow ``HOME`` (never the
real user roots) and drives an installed worker Skill's own
``scripts/runtime-tmux.sh`` against a small fake ACP agent. Covers the Fable
acceptance cases from the issue's review comment:

* T-a1 - kimi-cli and dsh share ``~/.agents/skills``; whichever installs
  second only records a reference (``refer``), in either order, and leaves
  every shared file's bytes and mtime alone.
* T-a2 - with both installed, uninstalling one leaves the shared Skills and
  receipts in place (referrers shrink to the other) and the other runtime's
  start/observe/send/capture/stop chain still works; uninstalling the second
  then removes the Skills and the receipt directory. Both directions.
* T-a3 - an older build installed by dsh is updated in place when kimi-cli
  installs a newer one, every referrer is kept, and the #105 build comparison
  from either installed Skill finds no skew (a dsh Host start is not refused).
* T-c1 - existing ``~/.local/bin`` helper links that resolve to a usable
  executable are referenced, not refused, by a default ``--runtime codex``
  install; a dangling link is still refused before anything is written.
* T-c2 - ``--uninstall --bin-links`` keeps a link while another checkout's
  runtime still refers to it or, for the locator, while the Grok Bot
  registration receipt exists (which is never written); it removes a link only
  once nothing refers to it.
* T-b1 - every runtime's install root is one of the roots the #105 gate of
  that platform scans (the scan scope itself is unchanged).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "install-local.sh"
PYTHON = sys.executable
SHARED = ".agents/skills"
RECEIPTS = ".kaola-install-receipts"
LEDGER = ".kaola-project-runner-bin-links.json"
REGISTRATION = ".kaola-project-runner-locate.json"
BIN_LINKS = ("kaola-acp", "kaola-acp-holder", "kaola-project-runner-locate")

FAKE_AGENT = r'''#!/usr/bin/env python3
import json, sys
state = {"mode": "default"}
def options():
    return [{"id": "mode", "name": "Mode", "category": "mode", "type": "select",
             "currentValue": state["mode"],
             "options": [{"value": "default", "name": "Default"}, {"value": "yolo", "name": "YOLO"}]}]
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
              "agentCapabilities": {}, "authMethods": [], "agentInfo": {"name": "fake123"}}})
    elif method == "session/new":
        send({"jsonrpc": "2.0", "id": rid, "result": {"sessionId": "fake123-s",
              "configOptions": options()}})
    elif method == "session/set_config_option":
        if params.get("configId") == "mode":
            state["mode"] = params.get("value")
        send({"jsonrpc": "2.0", "id": rid, "result": {"configOptions": options()}})
    elif method == "session/prompt":
        send({"jsonrpc": "2.0", "method": "session/update", "params": {
              "sessionId": "fake123-s", "update": {"sessionUpdate": "agent_message_chunk",
              "content": {"type": "text", "text": "pong-123"}}}})
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


class Sandbox:
    """A shadow HOME, a consuming git repo, a record root, and a fake agent."""

    def __init__(self, label: str):
        self.dir = Path(tempfile.mkdtemp(prefix=f"kpr123-{label}-")).resolve()
        self.home = self.dir / "home"
        self.home.mkdir()
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c",
                        "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"], check=True)
        self.agent = self.dir / "fake123.py"
        self.agent.write_text(FAKE_AGENT, encoding="utf-8")
        self.agent.chmod(0o755)
        self.started: list[tuple[Path, str]] = []

    @property
    def shared(self) -> Path:
        return self.home / SHARED

    @property
    def bin(self) -> Path:
        return self.home / ".local" / "bin"

    def env(self, **extra: str) -> dict[str, str]:
        base = {"PATH": f"{Path(PYTHON).parent}:/usr/bin:/bin", "HOME": str(self.home),
                "LANG": "C", "TMPDIR": tempfile.gettempdir(), "PYTHONUNBUFFERED": "1",
                "KAOLA_ACP_RECORD_ROOT": str(self.dir / "records")}
        tmux = shutil.which("tmux")
        if tmux:
            base["PATH"] += ":" + str(Path(tmux).parent)
        base.update(extra)
        return base

    def install(self, *args: str, installer: Path = INSTALLER, expect: int = 0,
                **extra: str) -> str:
        result = subprocess.run(["bash", str(installer), *args], capture_output=True,
                                text=True, env=self.env(**extra), timeout=300)
        output = result.stdout + result.stderr
        if result.returncode != expect:
            raise AssertionError(f"install {' '.join(args)} rc={result.returncode}: {output[-1500:]}")
        return output

    def runner(self, skill: Path, command: str, *args: str, session: str) -> dict:
        """One documented Skill verb through the installed Skill's own entry."""
        entry = skill / "scripts" / "runtime-tmux.sh"
        if command == "start":
            # Registered before the start so a failed start still gets force-stopped.
            self.started.append((skill, session))
        result = subprocess.run(
            ["bash", str(entry), command, "--repo", str(self.repo), "--session", session, *args],
            capture_output=True, text=True, timeout=120,
            env=self.env(KAOLA_ACP_COMMAND=f"{PYTHON} {self.agent}"))
        lines = (result.stdout or "").strip().splitlines()
        try:
            return json.loads(lines[-1])
        except (IndexError, ValueError):
            raise AssertionError(f"{command} printed no receipt (rc={result.returncode}): "
                                 f"{result.stdout[-600:]} {result.stderr[-600:]}")

    def cleanup(self) -> None:
        for skill, session in self.started:
            entry = skill / "scripts" / "runtime-tmux.sh"
            # The Skill may already be uninstalled; the checkout CLI stops the same record.
            argv = (["bash", str(entry), "stop"] if entry.is_file() else
                    [PYTHON, str(ROOT / "scripts" / "kaola-acp.py"),
                     skill.name.removesuffix("-kaola-project-runner"), "stop"])
            try:
                subprocess.run([*argv, "--repo", str(self.repo), "--session", session, "--force"],
                               capture_output=True, timeout=60, env=self.env())
            except Exception:  # noqa: BLE001 - best effort
                pass
        shutil.rmtree(self.dir, ignore_errors=True)


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    """Every shared Skill file (receipts excluded) -> (sha256, mtime_ns)."""
    found: dict[str, tuple[str, int]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] == RECEIPTS or "__pycache__" in relative.parts:
            continue
        if path.is_file() and not path.is_symlink():
            found[str(relative)] = (hashlib.sha256(path.read_bytes()).hexdigest(),
                                    path.stat().st_mtime_ns)
    return found


def receipts(root: Path) -> dict[str, dict]:
    directory = root / RECEIPTS
    if not directory.is_dir():
        return {}
    return {path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))}


def installed_skills(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir()
                  if path.name.endswith("kaola-project-runner") or path.name == "kaola-delegator")


def worker_chain(sandbox: Sandbox, platform: str) -> None:
    """start / observe / send / capture / stop through the installed Skill."""
    skill = sandbox.shared / f"{platform}-kaola-project-runner"
    session = f"{platform}-KPR-i123-worker"
    started = sandbox.runner(skill, "start", session=session)
    check(started.get("state") == "ready" and not started.get("error"),
          f"{platform}: start from the shared Skill is ready ({started.get('error')})")
    observed = sandbox.runner(skill, "observe", session=session)
    check(observed.get("agent_alive") is True, f"{platform}: observe sees a live agent")
    sent = sandbox.runner(skill, "send", "--text", "ping", session=session)
    check(sent.get("error") is None, f"{platform}: send runs a turn ({sent.get('error')})")
    captured = sandbox.runner(skill, "capture", "--lines", "200", session=session)
    check("pong-123" in json.dumps(captured), f"{platform}: capture reads the reply")
    stopped = sandbox.runner(skill, "stop", session=session)
    check(stopped.get("stopped") is True, f"{platform}: exact stop")


def alignment(sandbox: Sandbox, platform: str) -> dict:
    """#105 worker_skill_alignment as loaded from the installed Skill tree."""
    cli = sandbox.shared / f"{platform}-kaola-project-runner" / "scripts" / "kaola-acp.py"
    program = ("import importlib.util, json, sys\n"
               "spec = importlib.util.spec_from_file_location('kaola_acp', sys.argv[1])\n"
               "module = importlib.util.module_from_spec(spec)\n"
               "spec.loader.exec_module(module)\n"
               "print(json.dumps(module.worker_skill_alignment(sys.argv[2], sys.argv[3])))\n")
    result = subprocess.run([PYTHON, "-c", program, str(cli), str(sandbox.repo), platform],
                            capture_output=True, text=True, env=sandbox.env(), timeout=60)
    if result.returncode != 0:
        raise AssertionError(f"alignment probe failed: {result.stderr[-800:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def make_checkout(path: Path, older: bool = False) -> Path:
    """A second checkout: the installer, bin-link sources, and generated Skills.
    ``older`` appends a byte to every worker Skill's kaola-acp.py - another build."""
    (path / "scripts").mkdir(parents=True)
    for name in ("install-local.sh", "kaola-acp.py", "kaola-acp-holder.py", "kaola-locate.py",
                 "kaola-codex-compact-hook.py"):
        shutil.copy2(ROOT / "scripts" / name, path / "scripts" / name)
    shutil.copytree(ROOT / "templates" / "codex-host", path / "templates" / "codex-host")
    shutil.copytree(ROOT / "skills", path / "skills",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if older:
        for cli in (path / "skills").glob("*/scripts/kaola-acp.py"):
            cli.write_bytes(cli.read_bytes() + b"\n# older build\n")
    return path / "scripts" / "install-local.sh"


def test_a1_second_install_only_refers() -> None:
    for first, second in (("kimi-cli", "dsh"), ("dsh", "kimi-cli")):
        sandbox = Sandbox(f"a1-{first}")
        try:
            sandbox.install("--runtime", first)
            before = snapshot(sandbox.shared)
            skills = installed_skills(sandbox.shared)
            check(len(skills) == 11, f"T-a1 {first}: all Skills installed ({skills})")
            output = sandbox.install("--runtime", second)
            check(output.count("refer: ") == len(skills)
                  and "install: " not in output and "update: " not in output,
                  f"T-a1 {first}->{second}: every Skill is referred, none reinstalled ({output[-400:]})")
            check(snapshot(sandbox.shared) == before,
                  f"T-a1 {first}->{second}: shared bytes and mtimes unchanged")
            refs = {name: data.get("referrers") for name, data in receipts(sandbox.shared).items()}
            check(set(refs) == set(skills) and all(v == ["dsh", "kimi-cli"] for v in refs.values()),
                  f"T-a1 {first}->{second}: every receipt lists both referrers ({refs})")
        finally:
            sandbox.cleanup()


def test_a2_one_sided_uninstall_keeps_the_other_working() -> None:
    for leaving, staying in (("kimi-cli", "dsh"), ("dsh", "kimi-cli")):
        sandbox = Sandbox(f"a2-{leaving}")
        try:
            sandbox.install("--runtime", "dsh")
            sandbox.install("--runtime", "kimi-cli")
            before = snapshot(sandbox.shared)
            output = sandbox.install("--runtime", leaving, "--uninstall")
            check("uninstalled: " not in output and f"still referenced by {staying}" in output,
                  f"T-a2 uninstall {leaving}: nothing removed, each Skill kept for {staying}")
            check(snapshot(sandbox.shared) == before,
                  f"T-a2 uninstall {leaving}: {staying}'s Skills keep bytes and mtimes")
            refs = {name: data.get("referrers") for name, data in receipts(sandbox.shared).items()}
            check(len(refs) == 11 and all(v == [staying] for v in refs.values()),
                  f"T-a2 uninstall {leaving}: receipts remain with referrers [{staying}] ({refs})")
            worker_chain(sandbox, staying)
            output = sandbox.install("--runtime", staying, "--uninstall")
            check(installed_skills(sandbox.shared) == [] and not (sandbox.shared / RECEIPTS).exists(),
                  f"T-a2 uninstall {staying} last: Skills and receipt directory removed ({output[-300:]})")
        finally:
            sandbox.cleanup()


def test_a3_other_build_updates_in_place_and_stays_aligned() -> None:
    sandbox = Sandbox("a3")
    try:
        old_installer = make_checkout(sandbox.dir / "old-checkout", older=True)
        sandbox.install("--runtime", "dsh", installer=old_installer)
        old_cli = sandbox.shared / "dsh-kaola-project-runner" / "scripts" / "kaola-acp.py"
        check(old_cli.read_bytes().endswith(b"# older build\n"), "T-a3: dsh installed the older build")
        output = sandbox.install("--runtime", "kimi-cli")
        # Only the worker Skills differ in that build; the main Skill is the same build.
        check(output.count("update: ") == 10 and output.count("refer: ") == 1
              and "refer: " + str(sandbox.shared / "kaola-project-runner") in output,
              f"T-a3: a different build updates the shared copies ({output[-400:]})")
        check(old_cli.read_bytes() == (ROOT / "skills" / "dsh-kaola-project-runner" / "scripts"
                                       / "kaola-acp.py").read_bytes(),
              "T-a3: the shared dsh Skill now carries the new build")
        refs = {name: data.get("referrers") for name, data in receipts(sandbox.shared).items()}
        check(all(v == ["dsh", "kimi-cli"] for v in refs.values()),
              f"T-a3: the update keeps the dsh referrer ({refs})")
        for platform in ("dsh", "kimi-cli"):
            result = alignment(sandbox, platform)
            check(result["applies"] is True and result["skew"] == [],
                  f"T-a3: #105 alignment from the installed {platform} Skill has no skew ({result['skew'][:2]})")
        skill = sandbox.shared / "dsh-kaola-project-runner"
        host = sandbox.runner(skill, "start", session="dsh-KPR-orchestrator-t123")
        check(host.get("state") == "ready" and host.get("reason") != "worker-skill-build-skew",
              f"T-a3: a dsh Host start is not refused for build skew ({host.get('reason') or host.get('error')})")
        sandbox.runner(skill, "stop", "--force", session="dsh-KPR-orchestrator-t123")
    finally:
        sandbox.cleanup()


def preset_links(sandbox: Sandbox, checkout: Path) -> None:
    """Helper links made by another checkout before the ledger existed."""
    (checkout / "scripts").mkdir(parents=True)
    sandbox.bin.mkdir(parents=True)
    for name, source in zip(BIN_LINKS, ("kaola-acp.py", "kaola-acp-holder.py", "kaola-locate.py")):
        stub = checkout / "scripts" / source
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(0o755)
        (sandbox.bin / name).symlink_to(stub)


def ledger(sandbox: Sandbox) -> dict:
    path = sandbox.bin / LEDGER
    return json.loads(path.read_text(encoding="utf-8"))["links"] if path.exists() else {}


def test_c1_usable_link_is_referred_dangling_refused() -> None:
    sandbox = Sandbox("c1")
    try:
        other = sandbox.dir / "accepted"
        preset_links(sandbox, other)
        codex_home = str(sandbox.home / ".codex")
        output = sandbox.install("--runtime", "codex", "--platform", "grok", CODEX_HOME=codex_home)
        check(output.count("refer: ") == 3 and "refusing" not in output,
              f"T-c1: a default codex install refers to all three usable links ({output[-500:]})")
        for name, source in zip(BIN_LINKS, ("kaola-acp.py", "kaola-acp-holder.py", "kaola-locate.py")):
            check(os.readlink(sandbox.bin / name) == str(other / "scripts" / source),
                  f"T-c1: {name} still points at the other checkout")
        refs = ledger(sandbox)
        mine = {"runtime": "codex", "checkout": str(ROOT)}
        check(all(mine in refs[name]["referrers"] and
                  {"runtime": "legacy", "checkout": str(other)} in refs[name]["referrers"]
                  for name in BIN_LINKS),
              f"T-c1: the ledger records codex@<this checkout> beside the link's creator ({refs})")
        check((sandbox.home / ".codex" / "skills" / "grok-kaola-project-runner").is_dir(),
              "T-c1: the rest of the install went ahead")
    finally:
        sandbox.cleanup()
    sandbox = Sandbox("c1-dangling")
    try:
        sandbox.bin.mkdir(parents=True)
        (sandbox.bin / "kaola-acp").symlink_to(sandbox.dir / "gone" / "kaola-acp.py")
        output = sandbox.install("--runtime", "codex", "--platform", "grok", expect=1,
                                 CODEX_HOME=str(sandbox.home / ".codex"))
        check("refusing to replace existing symlink" in output,
              f"T-c1: a dangling link is refused ({output[-300:]})")
        check(not (sandbox.home / ".codex" / "skills").exists() and not (sandbox.bin / LEDGER).exists(),
              "T-c1: the refusal happens before any write")
    finally:
        sandbox.cleanup()


def test_c2_uninstall_keeps_referenced_links() -> None:
    sandbox = Sandbox("c2")
    try:
        codex_home = str(sandbox.home / ".codex")
        sandbox.install("--runtime", "codex", "--platform", "grok", CODEX_HOME=codex_home)
        other_installer = make_checkout(sandbox.dir / "other-checkout")
        other_root = str(other_installer.parent.parent)
        output = sandbox.install("--skills-dir", str(sandbox.dir / "other-skills"), "--platform",
                                 "grok", "--bin-links", installer=other_installer)
        check(output.count("refer: ") == 3, f"T-c2: a second checkout refers to the links ({output[-400:]})")
        output = sandbox.install("--runtime", "codex", "--platform", "grok", "--uninstall",
                                 "--bin-links", CODEX_HOME=codex_home)
        check(all((sandbox.bin / name).is_symlink() for name in BIN_LINKS)
              and output.count(f"still referenced by generic@{other_root}") == 3,
              f"T-c2: this checkout's uninstall keeps links the other checkout refers to ({output[-500:]})")
        check(all(ledger(sandbox)[name]["referrers"] == [{"runtime": "generic", "checkout": other_root}]
                  for name in BIN_LINKS), "T-c2: only this checkout's reference was withdrawn")
        output = sandbox.install("--skills-dir", str(sandbox.dir / "other-skills"), "--platform",
                                 "grok", "--uninstall", "--bin-links", installer=other_installer)
        check(not any((sandbox.bin / name).is_symlink() for name in BIN_LINKS)
              and not (sandbox.bin / LEDGER).exists(),
              f"T-c2: the last referrer's uninstall removes links and ledger ({output[-400:]})")
    finally:
        sandbox.cleanup()
    sandbox = Sandbox("c2-locator")
    try:
        codex_home = str(sandbox.home / ".codex")
        sandbox.install("--runtime", "codex", "--platform", "grok", CODEX_HOME=codex_home)
        registration = sandbox.bin / REGISTRATION
        registration.write_text(json.dumps({"schema": "kaola-project-runner-locate-registration/1",
                                            "root": str(ROOT), "target": "local"}) + "\n",
                                encoding="utf-8")
        stamp = (registration.read_bytes(), registration.stat().st_mtime_ns)
        output = sandbox.install("--runtime", "codex", "--platform", "grok", "--uninstall",
                                 "--bin-links", CODEX_HOME=codex_home)
        check(not (sandbox.bin / "kaola-acp").is_symlink()
              and not (sandbox.bin / "kaola-acp-holder").is_symlink(),
              "T-c2 locator: unreferenced kaola-acp links are removed")
        check((sandbox.bin / "kaola-project-runner-locate").is_symlink()
              and "Grok Bot locator registration" in output,
              f"T-c2 locator: the registration receipt keeps the locator link ({output[-400:]})")
        check((registration.read_bytes(), registration.stat().st_mtime_ns) == stamp,
              "T-c2 locator: the registration receipt is never written")
    finally:
        sandbox.cleanup()


def test_b1_install_roots_are_scanned_by_the_105_gate() -> None:
    spec = importlib.util.spec_from_file_location("kaola_acp_123", ROOT / "scripts" / "kaola-acp.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = Path(tempfile.mkdtemp(prefix="kpr123-b1-"))
    try:
        platform_for = {"cursor": "cursor-cli", "grok-cli": "grok"}
        for runtime in ("codex", "claude-code", "cursor", "devin", "zcode", "grok-cli", "droid",
                        "opencode", "kimi-cli", "dsh"):
            result = subprocess.run(["bash", "-c", 'eval "$(sed -n "/^runtime_skills_dir()/,/^}/p" "$1")"; '
                                     'runtime_skills_dir "$2"', "_", str(INSTALLER), runtime],
                                    capture_output=True, text=True,
                                    env={"PATH": "/usr/bin:/bin", "HOME": str(home)})
            relative = str(Path(result.stdout.strip()).relative_to(home))
            scanned = module.HOST_SKILL_DISCOVERY_DIRS[platform_for.get(runtime, runtime)]
            check(relative in scanned, f"T-b1: {runtime} install root {relative} is scanned by #105 ({scanned})")
    finally:
        shutil.rmtree(home, ignore_errors=True)


TESTS = [
    test_a1_second_install_only_refers,
    test_a2_one_sided_uninstall_keeps_the_other_working,
    test_a3_other_build_updates_in_place_and_stays_aligned,
    test_c1_usable_link_is_referred_dangling_refused,
    test_c2_uninstall_keeps_referenced_links,
    test_b1_install_roots_are_scanned_by_the_105_gate,
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
    print(f"test-issue-123-shared-refs: {len(TESTS) - failures}/{len(TESTS)} tests, {len(CHECKS)} checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
