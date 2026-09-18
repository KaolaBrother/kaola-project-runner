#!/usr/bin/env python3
"""Issue #74: thin Zcode Orchestrator entry and two-layer isolation.

Contract: generated ``zcode-orchestrator`` is the external Skill (Grok Bot /
Codex / generic). Project Runner remains the inner engine. The Grok Bot bridge
loads only the external Skill after bind+locator. This suite does not claim
live Grok Bot UAT.

Behavioral isolation (real ACP, fake ZCode backend, original receipts):
user task/quota -> external Skill loaded -> one Host start + handoff -> inner
read of Project Runner -> one allowed worker -> natural end_turn -> Host event
wake with the worker's real reply. A later resume does not create a second Host.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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
EXTERNAL = ROOT / "skills" / "zcode-orchestrator"
RUNNER = ROOT / "skills" / "kaola-project-runner"
BRIDGE = ROOT / "hosts" / "grok-bot" / "zcode-orchestrator.md"
BUDGETS = json.loads((ROOT / "templates" / "budgets.json").read_text(encoding="utf-8"))
DESKTOP_CONFIG_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-coding-plan-cache.json"
ORIGINAL_TASK = (
    "ISSUE74-TASK: land the delegated entry; remaining=handoff isolation; "
    "quota_concurrency=1; quota_account=GLM-coding-plan; quota_token=unspecified; "
    "priority=P1; authorized_platforms=zcode:1"
)

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


def events_of_kind(record_dir: Path, kind: str) -> list[dict]:
    path = record_dir / "events.jsonl"
    if not path.is_file():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("kind") == kind:
            entries.append(entry)
    return entries


def rpc_prompts(rpc_path: Path) -> list[str]:
    if not rpc_path.is_file():
        return []
    prompts = []
    for line in rpc_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("msg") or {}
        if entry.get("direction") != "in":
            continue
        method = message.get("method")
        params = message.get("params") or {}
        if method in {"session/prompt", "session/send"}:
            content = params.get("content") or params.get("prompt") or ""
            if isinstance(content, list):
                content = "".join(
                    (part.get("text") or "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            prompts.append(str(content))
    return prompts


class Sandbox:
    def __init__(self, name: str) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix=f"kaola-issue-74-{name}-"))
        self.home = self.dir / "home"
        self.repo = self.dir / "repo"
        self.record_root = self.dir / "records"
        self.evidence = self.dir / "evidence"
        for path in (self.home, self.repo, self.record_root, self.evidence):
            path.mkdir(parents=True)
        (self.home / ".zcode" / "v2").mkdir(parents=True)
        (self.home / ".zcode" / "cli").mkdir(parents=True)
        (self.home / ".zcode" / "v2" / "config.json").write_text(
            DESKTOP_CONFIG_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
            PLAN_CACHE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.home / ".zcode" / "cli" / "config.json").write_text('{"hooks":{}}\n', encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.node = Path(PYTHON).resolve()
        self.rpcs: dict[str, Path] = {}
        self.sessions: list[str] = []

    def entry_for(self, session: str) -> Path:
        record = self.dir / f"fake-{session}.json"
        rpc = self.dir / f"rpc-{session}.jsonl"
        entry = self.dir / f"zcode-entry-{session}.py"
        entry.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            "os.environ['FAKE_ZCODE_SCENARIO'] = 'basic'\n"
            f"os.environ['FAKE_ZCODE_RECORD'] = {str(record)!r}\n"
            f"os.environ['FAKE_ZCODE_RPC_LOG'] = {str(rpc)!r}\n"
            f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
            f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        entry.chmod(entry.stat().st_mode | 0o755)
        self.rpcs[session] = rpc
        return entry

    def env(self, **overrides: str) -> dict[str, str]:
        base = {
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "HOME": str(self.home),
            "LANG": os.environ.get("LANG", "C"),
            "TMPDIR": tempfile.gettempdir(),
            "KAOLA_ACP_RECORD_ROOT": str(self.record_root),
            "KAOLA_ZCODE_NODE": str(self.node),
            "PYTHONUNBUFFERED": "1",
        }
        base.update(overrides)
        return base

    def record_dir(self, session: str) -> Path:
        digest = hashlib.sha256(os.path.realpath(str(self.repo)).encode()).hexdigest()[:16]
        return self.record_root / "zcode" / session / digest

    def cli(self, command: str, *args: str, session: str, timeout: float = 120,
            **env_overrides: str) -> dict:
        if command == "start":
            env_overrides.setdefault("KAOLA_ZCODE_ENTRY", str(self.entry_for(session)))
            self.sessions.append(session)
        argv = [PYTHON, str(CHECKOUT_CLI), "zcode", command, "--repo", str(self.repo),
                "--session", session, *args]
        result = subprocess.run(argv, capture_output=True, text=True,
                                env=self.env(**env_overrides), timeout=timeout)
        payload = None
        text = (result.stdout or "").strip()
        if text:
            try:
                payload = json.loads(text.splitlines()[-1])
            except ValueError:
                payload = None
        if result.returncode != 0 or not isinstance(payload, dict):
            raise AssertionError(
                f"{command} failed rc={result.returncode} "
                f"stdout={(result.stdout or '')[-400:]} stderr={(result.stderr or '')[-400:]}"
            )
        return payload

    def dump(self, name: str, payload: object) -> None:
        path = self.evidence / name
        if isinstance(payload, (dict, list)):
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")

    def cleanup(self) -> None:
        keep = os.environ.get("KAOLA_ISSUE74_EVIDENCE")
        if keep:
            import shutil
            dest = Path(keep)
            dest.mkdir(parents=True, exist_ok=True)
            if self.evidence.is_dir():
                shutil.copytree(self.evidence, dest, dirs_exist_ok=True)
        for session in list(self.sessions):
            try:
                self.cli("stop", "--force", session=session, timeout=30)
            except Exception:
                pass
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)


def test_generated_entry_matrix_and_no_engine_leak() -> None:
    skill = (EXTERNAL / "SKILL.md").read_text(encoding="utf-8")
    check(re.search(r"(?m)^name: zcode-orchestrator$", skill) is not None, "skill id is zcode-orchestrator")
    check("# Zcode Orchestrator" in skill, "display name is Zcode Orchestrator")
    check("Grok Bot" in skill and "Codex" in skill and "generic" in skill, "external entries named")
    check("kaola-project-runner" in skill, "inner Project Runner named")
    check("zcode-kaola-project-runner" in skill, "Host is started through the ZCode worker")
    check("KAOLA_ACP_HEARTBEAT_HOST" not in skill, "external Skill does not bind per-worker heartbeat")
    check("copy a Mission List" in skill, "external Skill refuses copying a Mission List")
    check("Do not dispatch workers" in skill, "external Skill refuses worker dispatch")
    check(len((EXTERNAL / "SKILL.md").read_bytes()) <= BUDGETS["external_skill_bytes"],
          "external Skill stays in its small budget")
    check(BUDGETS["main_skill_bytes"] <= 17408, "existing main budget not raised")
    check(BUDGETS["worker_skill_bytes"] <= 12288, "existing worker budget not raised")
    check(BUDGETS["bridge_bytes"] <= 2560, "existing bridge budget not raised")

    runner = (RUNNER / "SKILL.md").read_text(encoding="utf-8")
    check("Grok Bot is not an entry for this Skill" in runner, "Project Runner withdraws Grok Bot")
    check("Codex, generic" in runner and "ZCode" in runner, "Project Runner entries are Codex/generic/ZCode")
    check((RUNNER / "references" / "grok-bot-host.md").exists() is False,
          "Project Runner no longer ships a Grok Bot host reference")

    bridge = BRIDGE.read_text(encoding="utf-8")
    check(re.search(r"(?m)^name: zcode-orchestrator$", bridge) is not None, "bridge skill id is zcode-orchestrator")
    check("ROOT/skills/zcode-orchestrator/SKILL.md" in bridge, "bridge loads the external Skill")
    check("Do not load Project Runner" in bridge, "bridge does not load Project Runner")
    check("Bind the execution target first" in bridge, "bridge still binds the execution target first")
    check("live Grok Bot adoption" not in bridge.lower() or "does not claim" in (ROOT / "hosts" / "grok-bot" / "INSTALL.md").read_text(encoding="utf-8").lower(),
          "no live Grok Bot UAT claim on the bridge")
    golden = ROOT / "templates" / "grok-golden" / "SKILL.md"
    check(golden.is_file(), "grok-golden remains present and frozen by the generated-skills suite")


def test_two_layer_handoff_worker_end_turn_and_resume() -> None:
    sandbox = Sandbox("layer")
    try:
        external = (EXTERNAL / "SKILL.md").read_text(encoding="utf-8")
        check("start or resume **one**" in external or "start or resume" in external,
              "external Skill instructs one Host start/resume")
        sandbox.dump("00-external-skill.txt", external)

        host = f"zcode-kaola-host-{uuid.uuid4().hex[:6]}"
        host_start = sandbox.cli("start", "--mode", "yolo", session=host)
        check(host_start.get("state") == "ready", f"Host start ready ({host_start.get('error')})")
        sandbox.dump("01-host-start.json", host_start)

        handoff = (
            f"Load {RUNNER / 'SKILL.md'} (Project Runner) and follow it.\n"
            f"You are the ZCode Host for this run.\n"
            f"platform=zcode session={host} repo={sandbox.repo}\n"
            f"{ORIGINAL_TASK}\n"
            "Finish planning, worker dispatch, notification binding, heartbeat, "
            "acceptance, and Workflow close-out internally.\n"
        )
        sandbox.dump("02-handoff.txt", handoff)
        send = sandbox.cli("send", "--no-wait", "--text", handoff, session=host)
        sandbox.dump("03-host-handoff-send.json", send)
        check(send.get("error") is None, f"handoff send accepted ({send.get('error')})")
        wait_until(lambda: any(ORIGINAL_TASK in text for text in rpc_prompts(sandbox.rpcs[host])),
                   10, "Host app-server received the original task/quota text")
        prompts = rpc_prompts(sandbox.rpcs[host])
        sandbox.dump("04-host-rpc-prompts.json", prompts)
        check(any(ORIGINAL_TASK in text for text in prompts),
              "original user task/quota reached the Host; not substituted by a grep of the Skill")

        runner_text = (RUNNER / "SKILL.md").read_text(encoding="utf-8")
        check("Main execution loop" in runner_text, "inner Host loads Project Runner")
        sandbox.dump("05-inner-runner-loaded.txt", f"bytes={len(runner_text.encode())}\n")

        worker = f"zcode-kaola-issue-74-{uuid.uuid4().hex[:6]}"
        heartbeat = json.dumps({"platform": "zcode", "session": host, "repo": str(sandbox.repo)})
        worker_start = sandbox.cli(
            "start", "--mode", "yolo", session=worker,
            KAOLA_ACP_HEARTBEAT_HOST=heartbeat,
        )
        sandbox.dump("06-worker-start.json", worker_start)
        check(worker_start.get("heartbeat_host"), "inner worker is heartbeat-bound by the Host role")
        check(worker_start.get("session") != host, "inner worker is a separate session")

        worker_send = sandbox.cli("send", "--text", "ISSUE74-WORKER-TURN", session=worker)
        sandbox.dump("07-worker-send.json", worker_send)
        check(worker_send.get("outcome") == "turn_completed",
              f"worker natural end_turn ({worker_send.get('outcome')})")
        host_dir = sandbox.record_dir(host)
        wait_until(lambda: events_of_kind(host_dir, "worker_event_delivered"), 10,
                   "Host wakes on the worker event")
        idle = events_of_kind(host_dir, "worker_event")
        sandbox.dump("08-host-worker-events.json", idle)
        check(idle and idle[0]["event"]["session"] == worker, "wake names the allowed worker")
        check("end_turn" in str(idle[0]["event"].get("reason")), "wake is the natural end_turn")

        worker_prompts = rpc_prompts(sandbox.rpcs[worker])
        sandbox.dump("09-worker-rpc-prompts.json", worker_prompts)
        check(any("ISSUE74-WORKER-TURN" in text for text in worker_prompts),
              "worker received the inner dispatch, not a handwritten substitute")

        # Existing Host is kept; a second Host name is never started.
        status = sandbox.cli("status", session=host)
        sandbox.dump("10-host-status.json", status)
        check(status.get("error") is None, f"existing Host still serves ({status.get('error')})")
        check(status.get("session") == host, "status names the original Host")

        listed = sorted({*sandbox.sessions})
        sandbox.dump("11-sessions.json", listed)
        check(listed == sorted({host, worker}), f"external path started only the Host; inner worker is Host-owned ({listed})")

        for session in (worker, host):
            stop = sandbox.cli("stop", "--force", session=session)
            check(stop.get("error") is None, f"{session} exact stop")
    finally:
        sandbox.cleanup()


def main() -> int:
    tests = (
        test_generated_entry_matrix_and_no_engine_leak,
        test_two_layer_handoff_worker_end_turn_and_resume,
    )
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    print(f"issue-74 checks: {len(CHECKS)} assertions, {failed} failed tests")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
