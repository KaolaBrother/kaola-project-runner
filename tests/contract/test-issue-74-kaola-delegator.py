#!/usr/bin/env python3
"""Issue #74: thin Kaola-Delegator entry and fake-ACP isolation.

Contract: generated ``kaola-delegator`` is the external Skill (Grok Bot /
Codex / generic). Project Runner remains the inner engine. The Grok Bot bridge
loads only the external Skill after bind+locator. This suite does not claim
live Grok Bot UAT.

``test_fake_acp_host_worker_event_and_live_status`` drives the real Runner ACP
holder against ``fake-zcode-app-server.py``. That is a low-level Host/worker
chain, not an outer Delegator Agent A→B. Authentic live A→B receipts (real
ZCode 3.12.3, Devin worker, event wake, Agent B attach) are
``kaola-workflow/issue-74/evidence/live-ab-44a17b9/`` and are not reproduced
here.
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
EXTERNAL = ROOT / "skills" / "kaola-delegator"
RUNNER = ROOT / "skills" / "kaola-project-runner"
BRIDGE = ROOT / "hosts" / "grok-bot" / "kaola-delegator.md"
BUDGETS = json.loads((ROOT / "templates" / "budgets.json").read_text(encoding="utf-8"))
DESKTOP_CONFIG_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-desktop-config.json"
PLAN_CACHE_FIXTURE = ROOT / "tests" / "contract" / "fixtures" / "zcode-coding-plan-cache.json"
ORIGINAL_TASK = (
    "ISSUE74-TASK: land the delegated entry; remaining=handoff isolation; "
    "quota_concurrency=1; quota_account=1 job; quota_token=10000 tokens; "
    "priority=P1; authorized_platforms=zcode:1; "
    "delivery_stop_boundary=test-receipts-only; stop this Host at end"
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


def native_session_id_from_events(record_dir: Path) -> str | None:
    path = record_dir / "events.jsonl"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        blob = json.dumps(entry)
        if "nativeSessionId" not in blob and "native_session_identity" not in blob:
            continue
        update = (
            (entry.get("event") or {}).get("update")
            or entry.get("update")
            or entry.get("event")
            or {}
        )
        native_id = (
            (update.get("nativeSessionId") if isinstance(update, dict) else None)
            or entry.get("nativeSessionId")
        )
        if not native_id:
            match = re.search(r"sess_[A-Za-z0-9_-]+", blob)
            if match:
                native_id = match.group(0)
        if native_id:
            return str(native_id)
    return None


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
            allow_error: bool = False, **env_overrides: str) -> dict:
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
        if allow_error and isinstance(payload, dict):
            return payload
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
    skill_one = re.sub(r"\s+", " ", skill)
    check(re.search(r"(?m)^name: kaola-delegator$", skill) is not None, "skill id is kaola-delegator")
    check("# Kaola-Delegator" in skill, "display name is Kaola-Delegator")
    check("Grok Bot" in skill and "Codex" in skill and "generic" in skill, "external entries named")
    check("kaola-project-runner" in skill, "inner Project Runner named")
    # Issue #187: the Host is started through the selected platform's Runner.
    check("`<platform>-kaola-project-runner`" in skill, "Host is started through its platform Runner")
    platforms_doc = (EXTERNAL / "references" / "host-platforms.md").read_text(encoding="utf-8")
    check("| zcode (`ZCode`) | `zcode-kaola-project-runner` |" in platforms_doc,
          "the ZCode Runner is one selectable Host row")
    check("KAOLA_ACP_HEARTBEAT_HOST" not in skill, "external Skill does not bind per-worker heartbeat")
    check("copy a mission ledger" in skill_one, "external Skill refuses copying a mission ledger")
    check("Do not dispatch workers" in skill_one, "external Skill refuses worker dispatch")
    check("not executable" in skill, "missing selected Runner is a hard stop")
    check("attested native id" in skill_one and "`sess_*`" in platforms_doc,
          "Skill names attested native resume; zcode's is sess_*")
    handoff_doc = (EXTERNAL / "references" / "handoff.md").read_text(encoding="utf-8")
    handoff_one = re.sub(r"\s+", " ", handoff_doc)
    check("Never use `--continue`" in handoff_doc, "handoff forbids --continue guessing")
    check("else `--continue`" not in handoff_doc, "handoff does not recommend --continue as fallback")
    check('HOST="$PLATFORM-<PROJECT_CODE>-orchestrator-main"' in handoff_doc
          and "`zcode-<PROJECT_CODE>-orchestrator-<purpose>`" in platforms_doc,
          "standard Host session name")
    check("acp_session_id" in handoff_doc and "native_session_identity" in platforms_doc,
          "three identities are sourced separately")
    check("delegator-host.json" not in handoff_doc and "delegator-host.json" not in skill,
          "no Delegator continuation pointer file")
    check("prompt-in-progress" in handoff_doc, "busy send is not claimed delivered")
    check("```text\n<host_skill_entry>\n" in handoff_doc,
          "handoff text opens with the platform's native Skill entry as its own first line")
    check("Load " not in handoff_doc.split("```text", 1)[1].split("```", 1)[0],
          "handoff text no longer tells the Host to Load a SKILL.md path")
    check("E1 `Skill` tool_call or E2 quote" in handoff_one,
          "first-beat check requires the platform's E1/E2 startup evidence")
    check("No `AGENTS.md` block or manual `SKILL.md` read" in handoff_one,
          "handoff states the AGENTS.md block is not the carrier")
    check("later updates alike" in handoff_one,
          "later updates reuse the same native entry line")
    check("status --repo" in handoff_one, "live recover uses existing Runner status")
    check("A Git worktree is not an ACP session id" in handoff_one
          or "A Git worktree is not an ACP id" in skill_one,
          "worktree is not treated as an ACP id")
    check("uniquely name a live Host" in handoff_one, "recorded nonstandard live name is adopted")
    check("Ambiguous location: report and do not start" in handoff_one,
          "ambiguous location does not start a second Host")
    check("That is a new ACP session" in handoff_one, "failed resume starts a new ACP session")
    check("try attested `--resume`" in handoff_one or "try attested --resume" in handoff_one,
          "handoff tries attested native resume first after exact stop")
    check("backend-dependent" in handoff_one,
          "native sess_* after stop is capability-dependent, not an absolute spend")
    check("that id then disappears" not in handoff_one,
          "handoff does not claim exact stop always spends sess_*")
    check("Issue #84" not in handoff_doc and "issue-84" not in handoff_doc,
          "handoff does not treat Issue #84 as merged here")
    check("not automatically awakened by inner Host activity" in handoff_one,
          "Afterward warns the outer Agent is not auto-woken by inner Host activity")
    check("quota_token=unspecified" not in ORIGINAL_TASK,
          "fixture token quota is explicit, not unspecified")
    check("quota_account=GLM-coding-plan" not in ORIGINAL_TASK,
          "fixture account quota is a figure, not an account name")
    check("quota_token=1-short-task" not in ORIGINAL_TASK,
          "fixture token quota is a token figure, not a task count")
    check("quota_account=1 job" in ORIGINAL_TASK,
          "fixture names a numeric account quota")
    check("quota_token=10000 tokens" in ORIGINAL_TASK,
          "fixture names a numeric token budget")
    check("delivery_stop_boundary=" in ORIGINAL_TASK,
          "fixture names a delivery/stop boundary")
    # Issue #157 (KD-R3): handoff step 4 points at SKILL §Extract once, the authority.
    check("reuse a stale quota" in skill_one
          and "authorization per SKILL §Extract once" in handoff_one,
          "new Host does not guess stale quota")
    check("authorization **before** `start`" in handoff_one
          or "authorization before `start`" in handoff_one,
          "new Host authorization is required before start")
    check("Do not open a blank Host" in handoff_one or "Do not open a blank Host" in skill_one,
          "new Host is not started blank then filled later")
    check("already-started empty Host" not in handoff_one,
          "handoff no longer allows starting a blank Host first")
    check("apply only the user's latest change" in handoff_one,
          "live Host does not re-ask the full authorization set")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_one = re.sub(r"\s+", " ", readme)
    check("do not `start`" in readme,
          "README forbids start when authorization is missing")
    check("only after current authorization is complete" in readme_one,
          "README requires complete authorization before a new Host start")
    adapter = (ROOT / "scripts" / "kaola-zcode-acp.py").read_text(encoding="utf-8")
    generated_adapter = (
        ROOT / "skills" / "zcode-kaola-project-runner" / "scripts" / "kaola-zcode-acp.py"
    ).read_text(encoding="utf-8")
    check("def apply_coding_plan_model" not in adapter,
          "canonical adapter has no overlay-less setModel fallback")
    check("def apply_coding_plan_model" not in generated_adapter,
          "generated adapter copy has no overlay-less setModel fallback")
    check("setModel after overlay-less create" not in adapter,
          "adapter does not swallow overlay-less setModel errors")
    check("There is no Delegator continuation file" in skill_one,
          "Skill forbids a dedicated continuation file")
    check("even if its recorded name is not the new form" in skill_one,
          "Skill adopts a live Host with a nonstandard name")
    check("Grok Bot account bridge" in skill_one, "Skill gates locator attestation to the Grok Bot bridge")
    check("--worker \"$PLATFORM\"" in handoff_one and "--session \"$HOST\"" in handoff_doc,
          "Grok Bot Host ops attest with locator --worker <Host platform> and exact session")
    check("--project \"$PROJECT\"" in handoff_doc, "Grok Bot Host ops attest with locator --project")
    check("kaola-project-runner-locate" in handoff_doc, "Grok Bot Host ops use the existing locator command")
    check("--expect-revision" not in handoff_doc and "--expect-revision" not in handoff_one,
          "Grok Bot Host ops carry no commit pin: the receipt binds HEAD (Issue #138)")
    check("Refuse any `refused` receipt" in handoff_one, "Grok Bot path refuses a refused locator receipt")
    check("Codex and generic" in handoff_one and "skip this" in handoff_one,
          "Codex and generic hosts are not given the locator")
    check("uniquely adopted live nonstandard name" in handoff_one,
          "adopted live Host attests the real exact session")
    check("Do not trust the Host's self-description" in handoff_one,
          "first-beat check does not trust Host self-description")
    check("After the first Host beat" in handoff_doc, "handoff has a first-beat verification step")
    check("heartbeat-prompt.json" in handoff_doc, "first-beat check names the heartbeat work product")
    check("first worker dispatch receipt" in handoff_one, "first-beat check uses the first dispatch receipt")
    # Issue #104: the per-worker binding is mechanical (the script refuses an
    # unbound dispatch-path start), so the Delegator no longer re-checks it.
    check("echo `heartbeat_host`" not in handoff_one and "echo heartbeat_host" not in handoff_one,
          "first-beat check no longer asks the Delegator to verify per-worker binding")
    check("KAOLA_ACP_HEARTBEAT_HOST" not in handoff_doc,
          "the handoff reference no longer names the per-worker variable")
    check("issue-scoped worker name" in handoff_one, "first-beat check requires an issue-scoped worker name")
    check("do not accept completion" in handoff_one, "mismatch is not accepted as complete")
    check("No new script, gate, ledger, or store" in handoff_one,
          "first-beat check adds no script, gate, ledger, or store")
    check("do not trust the Host's self-description" in skill_one,
          "Skill points at the first-beat check")
    check("do not accept completion" in skill_one, "Skill refuses to accept a mismatched first beat")
    check("--expected-holder-instance-id" in handoff_doc,
          "Host stop passes existing Runner --expected-holder-instance-id")
    check("holder-instance-mismatch" in handoff_one,
          "a different holder on the same session name is refused, not stopped")
    # Issue #157 (KD-A2): the undefined "H1" is named as the recorded Host instance.
    check("holder_instance_id" in handoff_one and "it is not the recorded Host instance" in handoff_one
          and "H1" not in handoff_one,
          "live attach re-verifies holder_instance_id, not repo+session name alone")
    check("`--expected-holder-instance-id`" in skill_one
          or "--expected-holder-instance-id" in skill,
          "Skill names the existing holder-instance stop flag")
    host_startup = (RUNNER / "references" / "host-startup.md").read_text(encoding="utf-8")
    check("Do not start the Host from this file" in host_startup,
          "outer start stays in Delegator, not a second host-startup procedure")
    check("Read the startup receipt, then verify it against evidence" not in host_startup,
          "old long Outer Agent startup-receipt procedure is not restored")
    check(len((EXTERNAL / "SKILL.md").read_bytes()) <= BUDGETS["external_skill_bytes"],
          "external Skill stays in its small budget")
    check(len((EXTERNAL / "references" / "handoff.md").read_bytes()) <= BUDGETS["reference_bytes"],
          "handoff stays in the existing reference budget")
    check(BUDGETS["main_skill_bytes"] <= 17408, "existing main budget not raised")
    check(BUDGETS["worker_skill_bytes"] <= 12288, "existing worker budget not raised")
    check(BUDGETS["bridge_bytes"] <= 2560, "existing bridge budget not raised")

    runner = (RUNNER / "SKILL.md").read_text(encoding="utf-8")
    check("Grok Bot is not an entry for this Skill" in runner, "Project Runner withdraws Grok Bot")
    # Issue #157 (PR-C4): any installer runtime or --skills-dir installs it;
    # Host admission is the entry matrix, not a hand-written runtime list.
    check("Any `install-local.sh --runtime`, or\n`--skills-dir`" in runner
          and "Host\nadmission per platform is [host-entry-matrix.md]" in runner,
          "Project Runner installs through any installer runtime; Host admission per matrix")
    check((RUNNER / "references" / "grok-bot-host.md").exists() is False,
          "Project Runner no longer ships a Grok Bot host reference")

    bridge = BRIDGE.read_text(encoding="utf-8")
    check(re.search(r"(?m)^name: kaola-delegator$", bridge) is not None, "bridge skill id is kaola-delegator")
    check("ROOT/skills/kaola-delegator/SKILL.md" in bridge, "bridge loads the external Skill")
    check("Do not load Project Runner" in bridge, "bridge does not load Project Runner")
    check("--worker zcode" not in bridge, "thin bridge does not carry the Host locator worker id")
    check("Grok Bot co-location attestation" in bridge, "bridge points at the Skill's Grok Bot co-location step")
    check("refuse `refused`" in bridge.lower(), "bridge refuses a refused locator receipt")
    check("Bind the execution target first" in bridge, "bridge still binds the execution target first")
    check("live Grok Bot adoption" not in bridge.lower() or "does not claim" in (ROOT / "hosts" / "grok-bot" / "INSTALL.md").read_text(encoding="utf-8").lower(),
          "no live Grok Bot UAT claim on the bridge")
    golden = ROOT / "templates" / "grok-golden" / "SKILL.md"
    check(golden.is_file(), "grok-golden remains present and frozen by the generated-skills suite")


def test_fake_acp_host_worker_event_and_live_status() -> None:
    sandbox = Sandbox("layer")
    try:
        external = (EXTERNAL / "SKILL.md").read_text(encoding="utf-8")
        sandbox.dump("00-external-skill.txt", external)

        host = f"zcode-KPR-orchestrator-{uuid.uuid4().hex[:6]}"
        check(host.startswith("zcode-KPR-orchestrator-"), "Host uses standard orchestrator session name")
        host_start = sandbox.cli("start", "--mode", "yolo", session=host)
        check(host_start.get("state") == "ready", f"Host start ready ({host_start.get('error')})")
        sandbox.dump("01-host-start.json", host_start)
        # Recover facts from the start receipt / later status — not a project
        # pointer file. Do not harvest native sess_* from events here.
        receipt_ids = {
            "canonical_repo": str(sandbox.repo),
            "platform": "zcode",
            "session": host,
            "acp_session_id": host_start.get("acp_session_id"),
            "native_session_id": None,
            "holder_instance_id": host_start.get("holder_instance_id"),
            "session_meta": host_start.get("session_meta"),
        }
        sandbox.dump("01b-start-receipt-ids.json", receipt_ids)
        check(receipt_ids["session"] == host, "start receipt stores the Runner session name")
        check(receipt_ids["acp_session_id"], "start receipt stores acp_session_id")
        check(receipt_ids["holder_instance_id"], "start receipt stores holder instance")
        check(receipt_ids["native_session_id"] is None,
              "start receipt does not invent native sess_*")
        check(receipt_ids.get("session_meta") != receipt_ids["acp_session_id"],
              "session_meta is not used as a stand-in for acp_session_id")
        check(not (sandbox.repo / ".kaola" / "delegator-host.json").exists(),
              "isolation does not write a Delegator pointer file")

        live_before_prompt = sandbox.cli("status", session=host)
        sandbox.dump("01c-live-attach-before-prompt.json", live_before_prompt)
        check(live_before_prompt.get("error") is None,
              f"Agent B live-attaches before native id ({live_before_prompt.get('error')})")
        check(live_before_prompt.get("session") == host, "live attach names the original Host")

        handoff = (
            "/kaola-project-runner\n"
            f"You are the ZCode Host for this run.\n"
            f"platform=zcode session={host} repo={sandbox.repo}\n"
            f"{ORIGINAL_TASK}\n"
            "Finish planning, worker dispatch, heartbeat, acceptance, and Workflow "
            "close-out internally.\n"
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

        filled_native = native_session_id_from_events(sandbox.record_dir(host))
        receipt_ids["native_session_id"] = filled_native
        sandbox.dump("01d-ids-after-handoff.json", receipt_ids)
        # Fake may emit identity at start. Recording it after the first prompt
        # is not proof of real-ZCode lazy timing or of start --resume.

        runner_text = (RUNNER / "SKILL.md").read_text(encoding="utf-8")
        check("Main execution loop" in runner_text, "inner Host loads Project Runner")
        sandbox.dump("05-inner-runner-loaded.txt", f"bytes={len(runner_text.encode())}\n")

        worker = f"zcode-KPR-i74-{uuid.uuid4().hex[:6]}"
        # Issue #104: no variable is set. The worker start carries only the
        # identity fact the Host holder hands its agent (read here from the
        # Host record), and the script derives and verifies the binding.
        host_record = json.loads((sandbox.record_dir(host) / "record.json").read_text(encoding="utf-8"))
        dispatcher = json.dumps({"holder_instance_id": host_record["holder_instance_id"],
                                 "platform": "zcode", "repo": host_record["repo"],
                                 "session": host}, sort_keys=True)
        worker_start = sandbox.cli(
            "start", "--mode", "yolo", session=worker,
            KAOLA_ACP_DISPATCHER=dispatcher,
        )
        sandbox.dump("06-worker-start.json", worker_start)
        check(worker_start.get("heartbeat_host"), "inner worker is heartbeat-bound mechanically")
        check(worker_start.get("heartbeat_host_source") == "dispatcher",
              f"binding source is the dispatcher, not a variable ({worker_start.get('heartbeat_host_source')})")
        check(worker_start.get("session") != host, "inner worker is a separate session")
        bound = worker_start.get("heartbeat_host") or {}
        check(bound.get("session") == host,
              "first dispatch receipt heartbeat_host.session is this Host")
        check(str(sandbox.repo) in str(bound.get("repo") or ""),
              "first dispatch receipt heartbeat_host.repo is this project")
        check(worker.startswith("zcode-KPR-i74-"),
              "first worker uses an issue-scoped name, not the Host")

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

        sandbox.dump("12-resume-boundary.txt", (
            "fake-zcode-app-server is not a production ZCode backend and this "
            "test is not an outer Delegator Agent A→B.\n"
            "It proves Runner ACP live status on the original Host and that a "
            "second Host name is not started while it lives.\n"
            "Authentic live A→B (real ZCode 3.12.3, Devin worker, event wake, "
            "Agent B attach) is kaola-workflow/issue-74/evidence/live-ab-44a17b9/.\n"
            "Fake must not impersonate that path or start --resume sess_*.\n"
        ))
        check("not an outer Delegator Agent A→B" in
              (sandbox.evidence / "12-resume-boundary.txt").read_text(encoding="utf-8"),
              "fake isolation is labeled as not outer A→B")

        mismatch = sandbox.cli(
            "stop", "--force",
            "--expected-holder-instance-id", "0" * 32,
            session=host, allow_error=True,
        )
        sandbox.dump("12b-stop-holder-mismatch.json", mismatch)
        err = mismatch.get("error") or {}
        check(err.get("code") == "holder-instance-mismatch",
              f"stop with a foreign holder id is refused ({err})")
        still = sandbox.cli("status", session=host)
        check(still.get("error") is None, "refused stop leaves the live Host")
        check(still.get("holder_instance_id") == receipt_ids["holder_instance_id"],
              "refused stop did not replace the holder")

        stop_worker = sandbox.cli("stop", "--force", session=worker)
        check(stop_worker.get("error") is None, "worker exact stop")
        stop_host = sandbox.cli(
            "stop", "--force",
            "--expected-holder-instance-id", str(receipt_ids["holder_instance_id"]),
            session=host,
        )
        check(stop_host.get("error") is None, "Host stop with receipt holder id")
    finally:
        sandbox.cleanup()


def test_adopt_nonstandard_live_host_without_second_start() -> None:
    sandbox = Sandbox("adopt")
    try:
        old = f"zcode-KPR-legacy-{uuid.uuid4().hex[:6]}"
        check(re.match(r"zcode-[A-Za-z0-9]+-orchestrator-", old) is None,
              "legacy name is not the new Host form")
        start = sandbox.cli("start", "--mode", "yolo", session=old)
        check(start.get("state") == "ready", f"legacy Host start ready ({start.get('error')})")
        recorded = {
            "canonical_repo": str(sandbox.repo),
            "platform": "zcode",
            "session": old,
            "acp_session_id": start.get("acp_session_id"),
            "holder_instance_id": start.get("holder_instance_id"),
        }
        sandbox.dump("13-old-host-receipt.json", recorded)
        status = sandbox.cli("status", session=old)
        sandbox.dump("14-old-host-status.json", status)
        check(status.get("error") is None, f"live attach on nonstandard name ({status.get('error')})")
        check(status.get("session") == old, "adopted locator keeps the recorded session name")
        listed = sorted({*sandbox.sessions})
        sandbox.dump("15-old-host-sessions.json", listed)
        check(listed == [old], "no second Host started because the new HOST name was missing")
        stop = sandbox.cli("stop", "--force", session=old)
        check(stop.get("error") is None, "exact stop of adopted Host")
        sandbox.dump("16-stopped-new-host-boundary.txt", (
            "stopped Host; fake backend is not production --resume evidence; "
            "post-stop new Host identity is measured in "
            "test_new_standard_host_after_confirmed_stop\n"
        ))
    finally:
        sandbox.cleanup()


def test_existing_locator_accepts_zcode_host_full_attestation() -> None:
    """The Grok Bot Host path names this existing locator form.

    This subprocess is not a Grok Bot Agent. Missing-authorization non-start
    remains a documentation contract.
    """
    sandbox = Sandbox("locate")
    try:
        host = "zcode-KPR-orchestrator-main"
        locate = ROOT / "scripts" / "kaola-locate.py"
        good = subprocess.run(
            [PYTHON, str(locate), "receipt", "--target", "local",
             "--project", str(sandbox.repo), "--worker", "zcode", "--session", host],
            capture_output=True, text=True, timeout=30,
        )
        payload = json.loads((good.stdout or "").strip().splitlines()[-1])
        sandbox.dump("30-locator-zcode-host.json", payload)
        check((payload.get("worker") or {}).get("id") == "zcode",
              "existing locator accepts --worker zcode")
        check((payload.get("session") or {}).get("name") == host,
              "existing locator attests the exact Host session")
        check((payload.get("project") or {}).get("on_this_host") is True,
              "existing locator attests the consumer project on this host")
        if payload.get("result") == "refused":
            check(isinstance(payload.get("reasons"), list) and payload["reasons"],
                  "a refused locator receipt carries reasons the Skill must honor")

        bad = subprocess.run(
            [PYTHON, str(locate), "receipt", "--target", "local",
             "--project", str(sandbox.repo), "--worker", "bogus", "--session", host],
            capture_output=True, text=True, timeout=30,
        )
        bad_payload = json.loads((bad.stdout or "").strip().splitlines()[-1])
        sandbox.dump("31-locator-bogus-worker.json", bad_payload)
        check(bad_payload.get("result") == "refused", "unknown worker is refused")
        check("worker-unknown" in (bad_payload.get("reasons") or []),
              "unknown worker reason is worker-unknown")

        adopted = "zcode-KPR-legacy-live"
        adopted_run = subprocess.run(
            [PYTHON, str(locate), "receipt", "--target", "local",
             "--project", str(sandbox.repo), "--worker", "zcode", "--session", adopted],
            capture_output=True, text=True, timeout=30,
        )
        adopted_payload = json.loads((adopted_run.stdout or "").strip().splitlines()[-1])
        sandbox.dump("32-locator-adopted-session.json", adopted_payload)
        check((adopted_payload.get("session") or {}).get("name") == adopted,
              "locator attests the exact adopted live session, not a synthesized standard name")
        sandbox.dump("33-locator-not-agent.txt", (
            "locator subprocess is not a Grok Bot Agent run; "
            "Skill still requires refuse of a refused receipt\n"
        ))
    finally:
        sandbox.cleanup()


def test_missing_authorization_non_start_is_documentation_only() -> None:
    """Missing-auth non-start is a Skill/README contract, not measured here.

    This test starts no Host. A green result does not prove an outer Agent
    withheld start. Fake ACP cannot impersonate that judgment.
    """
    skill = (EXTERNAL / "SKILL.md").read_text(encoding="utf-8")
    handoff = (EXTERNAL / "references" / "handoff.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check("Do not open a blank Host" in skill or "Do not open a blank Host" in handoff,
          "documentation forbids starting a blank Host")
    check("authorization **before** `start`" in handoff
          or "authorization before `start`" in handoff
          or "confirmed before `start`" in skill,
          "documentation requires authorization before start")
    check("do not `start`" in readme, "README forbids start when authorization is missing")
    marker = {
        "contract": (
            "missing, conflicting, or expired key authorization: ask the "
            "user; do not start; do not open a blank Host"
        ),
        "issue_comment": "5730908734",
        "measured": False,
        "coverage": "untested",
        "reason": (
            "no harness executes an outer Agent's Skill judgment; a "
            "handwritten skip-start script would impersonate that Agent"
        ),
        "not_claimed": (
            "this suite does not prove an outer Agent withheld start; "
            "a PASS here is documentation presence only"
        ),
    }
    check(marker["measured"] is False, "missing-auth non-start is not claimed measured")
    check(marker["coverage"] == "untested", "missing-auth non-start is labeled untested")


def test_new_standard_host_after_confirmed_stop() -> None:
    """Confirmed stop then a new standard Host after authorization is on disk.

    Fake ACP/holder identity change is the measured branch. Fake is not a
    real ZCode model-session or sess_* --resume proof. Authorization facts
    are written before every start; the later send is a first handoff, not
    a substitute for pre-start authorization. Missing-auth non-start is
    not measured here (see test_missing_authorization_non_start_is_documentation_only).
    """
    sandbox = Sandbox("newhost")
    try:
        ledger = sandbox.repo / "kaola-workflow" / ".ledger"
        ledger.mkdir(parents=True)
        auth = ledger / "issue-74.jsonl"
        auth.write_text(
            json.dumps({"n": 1, "name": "isolation remaining=handoff isolation",
                        "details": ORIGINAL_TASK, "status": "in-flight"},
                       ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        check(auth.is_file() and ORIGINAL_TASK in auth.read_text(encoding="utf-8"),
              "complete authorization is on disk before the first start")
        host = f"zcode-KPR-orchestrator-{uuid.uuid4().hex[:6]}"
        check(host.startswith("zcode-KPR-orchestrator-"),
              "new-Host path uses the standard orchestrator session name")

        first = sandbox.cli("start", "--mode", "yolo", session=host)
        sandbox.dump("20-first-host.json", first)
        first_ids = {
            "session": host,
            "acp_session_id": first.get("acp_session_id"),
            "holder_instance_id": first.get("holder_instance_id"),
            "pid": first.get("pid"),
        }
        check(first.get("state") == "ready", f"first Host start ready ({first.get('error')})")
        check(first_ids["acp_session_id"] and first_ids["holder_instance_id"],
              "first Host receipts include ACP and holder ids")

        stop = sandbox.cli(
            "stop", "--force",
            "--expected-holder-instance-id", str(first_ids["holder_instance_id"]),
            session=host,
        )
        sandbox.dump("21-first-stop.json", stop)
        check(stop.get("error") is None, f"first Host exact stop ({stop.get('error')})")

        dead = sandbox.cli("status", session=host, allow_error=True)
        sandbox.dump("22-status-after-stop.json", dead)
        stopped = (
            dead.get("state") == "stopped"
            or dead.get("outcome") == "stopped"
            or dead.get("agent_alive") is False
            or dead.get("error") is not None
        )
        check(stopped, f"status after stop is not a live Host ({dead})")

        check(auth.is_file() and ORIGINAL_TASK in auth.read_text(encoding="utf-8"),
              "complete authorization is still on disk before the second start")
        second = sandbox.cli("start", "--mode", "yolo", session=host)
        sandbox.dump("23-second-host.json", second)
        check(second.get("state") == "ready", f"new Host start ready ({second.get('error')})")
        check(second.get("session") == host, "new Host reuses the standard session name")
        check(second.get("holder_instance_id") != first_ids["holder_instance_id"],
              "new Host has a new holder instance")
        if first_ids["pid"] and second.get("pid"):
            check(second.get("pid") != first_ids["pid"],
                  "new Host is a new holder process")
        sandbox.dump("23b-identity-delta.json", {
            "first": first_ids,
            "second": {
                "session": host,
                "acp_session_id": second.get("acp_session_id"),
                "holder_instance_id": second.get("holder_instance_id"),
                "pid": second.get("pid"),
            },
            "acp_session_id_string_reused": (
                first_ids["acp_session_id"] == second.get("acp_session_id")
            ),
            "same_acp_session": False,
            "note": (
                "zcode-N is per holder process. Reused acp_session_id string "
                "plus a new holder_instance_id is a new ACP session, not the "
                "stopped one."
            ),
        })
        check(second.get("acp_session_id"), "new Host has an ACP session id")

        live = sandbox.cli("status", session=host)
        sandbox.dump("24-second-status.json", live)
        check(live.get("error") is None, f"new Host is live ({live.get('error')})")
        check(live.get("holder_instance_id") == second.get("holder_instance_id"),
              "live status names the new holder, not the stopped one")
        check(live.get("acp_session_id") == second.get("acp_session_id"),
              "live status names the new holder's ACP session")
        check(live.get("holder_instance_id") != first_ids["holder_instance_id"],
              "live attach must not treat H2 as H1")

        orchestrators = sorted({name for name in sandbox.sessions if "-orchestrator-" in name})
        sandbox.dump("25-orchestrator-names.json", orchestrators)
        check(orchestrators == [host],
              f"only one orchestrator session name is live ({orchestrators})")

        send = sandbox.cli("send", "--no-wait", "--text", ORIGINAL_TASK, session=host)
        sandbox.dump("26-new-host-handoff.json", send)
        check(send.get("error") is None,
              f"first handoff after authorized start admitted ({send.get('error')})")

        stop2 = sandbox.cli(
            "stop", "--force",
            "--expected-holder-instance-id", str(second.get("holder_instance_id")),
            session=host,
        )
        check(stop2.get("error") is None, "new Host exact stop with receipt holder id")
    finally:
        sandbox.cleanup()


def test_one_host_per_repo_refuses_host_exists() -> None:
    """Issue #132 T1/T2/T5/T8/T13: one identity-verified Host per canonical
    root. A second Host-named start - a Delegator's, or a Host dispatch that
    names a Host - refuses host-exists before anything exists; a Host that
    fails the identity check does not block its replacement; list rows carry
    the binding a sweep tells this Host's seats from a predecessor's by."""
    sandbox = Sandbox("onehost")
    try:
        def raw_start(platform: str, session: str, **env: str):
            argv = [PYTHON, str(CHECKOUT_CLI), platform, "start", "--repo", str(sandbox.repo),
                    "--session", session, "--mode", "yolo"]
            # Registered before the start so cleanup stops it even when a
            # refusal this test expects does not happen.
            sandbox.sessions.append(session)
            if platform == "zcode":
                env.setdefault("KAOLA_ZCODE_ENTRY", str(sandbox.entry_for(session)))
            else:
                argv += ["--command", f"{PYTHON} {FAKE}"]
            result = subprocess.run(argv, capture_output=True, text=True,
                                    env=sandbox.env(**env), timeout=120)
            return result.returncode, json.loads(result.stdout.strip().splitlines()[-1])

        def rows(*extra: str) -> list[dict]:
            result = subprocess.run([PYTHON, str(CHECKOUT_CLI), "list", "--repo", str(sandbox.repo),
                                     *extra], capture_output=True, text=True,
                                    env=sandbox.env(), timeout=60)
            return json.loads(result.stdout)["rows"]

        def holders_named(session: str) -> list[str]:
            table = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True)
            return [line for line in table.stdout.splitlines()
                    if "kaola-acp-holder" in line and f"--session {session} " in line]

        host = "zcode-KPR-orchestrator-one"
        first = sandbox.cli("start", "--mode", "yolo", session=host)
        check(first.get("state") == "ready", f"first Host ready ({first.get('error')})")
        dispatcher = json.dumps({"holder_instance_id": first["holder_instance_id"],
                                 "platform": "zcode", "repo": os.path.realpath(sandbox.repo),
                                 "session": host}, sort_keys=True)
        worker = "zcode-KPR-i132-seat"
        seat = sandbox.cli("start", "--mode", "yolo", session=worker,
                           KAOLA_ACP_DISPATCHER=dispatcher)
        check(seat.get("heartbeat_host", {}).get("session") == host, "worker bound to the Host")

        second = "zcode-KPR-orchestrator-two"
        code, refused = raw_start("zcode", second)
        sandbox.dump("30-host-exists.json", refused)
        check(code == 1, f"T1: a second Host start exits 1 ({code})")
        check(refused.get("result") == "refused" and refused.get("reason") == "host-exists",
              f"T1: second Host start refuses host-exists ({refused})")
        existing = refused.get("existing_host") or {}
        check(existing.get("session") == host
              and existing.get("holder_instance_id") == first["holder_instance_id"],
              f"T1: existing_host names the live Host by its instance ({existing})")
        for key in ("result", "reason", "action", "platform", "session", "repo",
                    "existing_host", "mutation_performed"):
            check(key in refused, f"T13: host-exists receipt carries {key}")
        check(refused.get("action") == "start" and refused.get("mutation_performed") is False
              and refused.get("mutation_status") == "not_started",
              "T13: host-exists has the typed pre-mutation refusal shape")
        check(not (sandbox.record_root / "zcode" / second).exists(),
              "T1: no record directory for the refused Host")
        check(holders_named(second) == [], "T1: no holder process for the refused Host")

        code, dispatched = raw_start("claude-code", "claude-code-KPR-orchestrator-three",
                                     KAOLA_ACP_DISPATCHER=dispatcher)
        check(code == 1 and dispatched.get("reason") == "host-exists"
              and (dispatched.get("existing_host") or {}).get("session") == host,
              f"T5: a Host dispatch naming a Host refuses host-exists ({dispatched})")
        check(not (sandbox.record_root / "claude-code").exists(),
              "T5: the refusal comes before any record or spawn")

        listed = {row["session"]: row for row in rows()}
        sandbox.dump("31-list.json", listed)
        check(listed.get(host, {}).get("identity") == "verified"
              and listed[host].get("host_class") is True, "the live Host row verifies as a Host")
        row = listed.get(worker) or {}
        check(row.get("identity") == "verified" and row.get("host_class") is False,
              f"T8: the seat row verifies as a worker ({row})")
        check((row.get("dispatcher") or {}).get("holder_instance_id") == first["holder_instance_id"],
              f"T8: the seat row names its dispatching Host instance ({row.get('dispatcher')})")
        check((row.get("heartbeat_host") or {}).get("session") == host,
              "T8: the seat row carries its recorded binding")

        # Review F1: a live Host that cannot answer yet (initializing) or any
        # more (wedged) still holds the root; only a dead or reused PID frees it.
        socket_path = sandbox.record_dir(host) / "holder.sock"
        real_socket = Path(os.path.realpath(socket_path))
        real_socket.unlink()
        code, silent = raw_start("zcode", second)
        check(code == 1 and silent.get("reason") == "host-exists"
              and (silent.get("existing_host") or {}).get("identity") == "unreachable",
              f"F1: a silent anchored Host still refuses a second Host ({silent})")

        # T2: the Host dies without a stop; its record stays and fails the check.
        os.kill(first["holder_pid"], signal.SIGKILL)
        wait_until(lambda: not pid_alive(first["holder_pid"]), 10, "Host holder is gone")
        dead = {row["session"]: row for row in rows("--include-dead")}
        check(dead.get(host, {}).get("identity") == "dead", f"T2: the dead Host row reads dead")
        code, replacement = raw_start("zcode", second)
        sandbox.dump("32-replacement.json", replacement)
        check(code == 0 and replacement.get("state") == "ready",
              f"T2: a dead Host row does not trigger host-exists ({replacement})")
        after = {row["session"]: row for row in rows()}
        verified_hosts = {row["holder_instance_id"] for row in after.values()
                          if row.get("host_class") and row.get("identity") == "verified"}
        check(verified_hosts == {replacement["holder_instance_id"]},
              "T2: exactly one verified Host after the replacement")
        check((after.get(worker, {}).get("dispatcher") or {}).get("holder_instance_id")
              not in verified_hosts,
              "T8: the seat's dispatcher is no live Host - a predecessor's seat, report not kill")
    finally:
        sandbox.cleanup()


def main() -> int:
    tests = (
        test_generated_entry_matrix_and_no_engine_leak,
        test_fake_acp_host_worker_event_and_live_status,
        test_adopt_nonstandard_live_host_without_second_start,
        test_existing_locator_accepts_zcode_host_full_attestation,
        test_missing_authorization_non_start_is_documentation_only,
        test_new_standard_host_after_confirmed_stop,
        test_one_host_per_repo_refuses_host_exists,
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
