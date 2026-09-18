#!/usr/bin/env python3
"""Issue #76 isolated real-path probe.

Host: fake zcode app-server (no real zcode binary exists on this machine —
that limitation is inherent and recorded). Worker: the REAL `droid` binary
(`droid exec --output-format acp`) started in `--mode manual` (autonomy
`normal`) so a permission-gated tool call raises a real
session/request_permission. Asserts the bound Host receives a
permission_required event while the worker turn is still active, then the
ordinary idle after permit settles it.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path("/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/bundle-76")
CLI = ROOT / "scripts" / "kaola-acp.py"
FAKE = ROOT / "tests" / "contract" / "fake-zcode-app-server.py"
FIX = ROOT / "tests" / "contract" / "fixtures"
PYTHON = sys.executable
ENV = "KAOLA_ACP_HEARTBEAT_HOST"

work = Path(tempfile.mkdtemp(prefix="kaola-i76-real-"))
home_fake = work / "home-fake"
repo = work / "repo"
records = work / "records"
for p in (home_fake, repo, records):
    p.mkdir(parents=True)
(home_fake / ".zcode" / "v2").mkdir(parents=True)
(home_fake / ".zcode" / "cli").mkdir(parents=True)
(home_fake / ".zcode" / "v2" / "config.json").write_text(
    (FIX / "zcode-desktop-config.json").read_text())
(home_fake / ".zcode" / "v2" / "coding-plan-cache.json").write_text(
    (FIX / "zcode-coding-plan-cache.json").read_text())
(home_fake / ".zcode" / "v2" / "credentials.json").write_text("{}\n")
(home_fake / ".zcode" / "cli" / "config.json").write_text('{"hooks":{}}\n')
subprocess.run(["git", "init", "-q", str(repo)], check=True)
(repo / ".kaola").mkdir()
(repo / ".kaola" / "heartbeat-prompt.json").write_text(json.dumps(
    {"schema": "kaola-heartbeat-prompt/1", "body": "PROBE",
     "fingerprint": "sha256:" + hashlib.sha256(b"PROBE").hexdigest(),
     "updated_at": int(time.time() * 1000)}))

host = "zcode-i76-probe-host"
worker = "droid-i76-probe-worker"
rpc_log = work / "rpc-host.jsonl"
record = work / "fake-host.json"
entry = work / "zcode-entry.py"
entry.write_text(
    "#!/usr/bin/env python3\nimport os, runpy, sys\n"
    "os.environ['FAKE_ZCODE_SCENARIO'] = 'basic'\n"
    f"os.environ['FAKE_ZCODE_RECORD'] = {str(record)!r}\n"
    f"os.environ['FAKE_ZCODE_RPC_LOG'] = {str(rpc_log)!r}\n"
    f"sys.argv = [{str(FAKE)!r}, *sys.argv[1:]]\n"
    f"runpy.run_path({str(FAKE)!r}, run_name='__main__')\n")
entry.chmod(0o755)

results = []


def note(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}", flush=True)


def cli(platform, command, *args, session=None, fake_home=False, envx=None, timeout=180):
    argv = [PYTHON, str(CLI), platform, command, "--repo", str(repo)]
    if session:
        argv += ["--session", session]
    argv += list(args)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": str(home_fake) if fake_home else os.environ["HOME"],
        "LANG": "C", "TMPDIR": tempfile.gettempdir(),
        "KAOLA_ACP_RECORD_ROOT": str(records),
        "PYTHONUNBUFFERED": "1",
    }
    if fake_home:
        env["KAOLA_ZCODE_NODE"] = PYTHON
        env["KAOLA_ZCODE_ENTRY"] = str(entry)
    env.update(envx or {})
    r = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=timeout)
    out = (r.stdout or "").strip()
    payload = None
    if out:
        try:
            payload = json.loads(out.splitlines()[-1])
        except ValueError:
            pass
    return r, payload


def record_dir(session, platform):
    digest = hashlib.sha256(os.path.realpath(str(repo)).encode()).hexdigest()[:16]
    return records / platform / session / digest


def events_of(session, platform, kind):
    path = record_dir(session, platform) / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if kind in l]


def rpc_prompts():
    if not rpc_log.is_file():
        return []
    out = []
    for line in rpc_log.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        m = e.get("msg") or {}
        if e.get("direction") == "in" and m.get("method") == "session/send":
            out.append(str((m.get("params") or {}).get("content") or ""))
    return out


try:
    # 1. host up (fake zcode, idle)
    r, rec = cli("zcode", "start", "--mode", "yolo", session=host, fake_home=True)
    note("host start ready", rec and rec.get("state") == "ready", str(rec)[:200] if not (rec and rec.get("state") == "ready") else "")
    if not (rec and rec.get("state") == "ready"):
        print("host stderr:", (r.stderr or "")[-500:]); sys.exit(2)

    # 2. real droid worker, bound, manual autonomy
    bind = {"platform": "zcode", "session": host,
            "repo": os.path.realpath(str(repo))}
    r, rec = cli("droid", "start", "--mode", "manual", session=worker,
                 envx={ENV: json.dumps(bind)})
    note("real droid start ready", rec and rec.get("state") == "ready",
         str(rec)[:300] if not (rec and rec.get("state") == "ready") else "")
    if not (rec and rec.get("state") == "ready"):
        print("worker stderr:", (r.stderr or "")[-800:]); sys.exit(2)
    note("binding adopted", rec.get("heartbeat_host", {}).get("session") == host,
         json.dumps(rec.get("heartbeat_host"))[:160])

    # 3. send a prompt that must trigger a permission-gated tool call
    marker = work / "marker.txt"
    prompt = ("Use the shell/exec tool to run exactly this command: "
              f"touch {marker} — then reply with the word done.")
    r, rec = cli("droid", "send", "--no-wait", "--text", prompt, session=worker)
    note("dispatch admitted", rec and rec.get("outcome") == "in_progress",
         str(rec)[:300])

    # 4. wait for a real pending permission on the worker
    deadline = time.time() + 150
    status = {}
    while time.time() < deadline:
        _, status = cli("droid", "status", session=worker)
        if status.get("pending_permissions"):
            break
        if status.get("turn_active") is False and not status.get("pending_permissions"):
            # turn already over without a permission request
            pass
        time.sleep(2)
    pending = status.get("pending_permissions") or []
    note("real session/request_permission pending", bool(pending),
         json.dumps(pending)[:300])
    note("worker turn still active", status.get("turn_active") is True,
         f"turn_active={status.get('turn_active')}")

    if pending:
        # 5. host receives permission_required while worker turn is active
        deadline = time.time() + 30
        perm_events = []
        while time.time() < deadline:
            perm_events = [e for e in events_of(host, "zcode", "worker_event")
                           if "permission_required" in json.dumps(e)]
            if perm_events:
                break
            time.sleep(1)
        note("permission_required event on host", bool(perm_events),
             json.dumps(perm_events[-1])[:300] if perm_events else "")
        prompts = rpc_prompts()
        wake = [p for p in prompts if "permission_required" in p]
        note("delivered prompt carries permission_required", bool(wake),
             wake[-1][:200] if wake else "")
        rid = pending[0].get("request_id")
        note("event carries only the request_id locator",
             bool(wake) and str(rid) in wake[-1]
             and "touch" not in wake[-1] and "marker" not in wake[-1],
             "")

        # 6. permit it (allow-once style option if present)
        opt = None
        for o in pending[0].get("options") or []:
            if o.get("kind") in ("allow_once", "allow"):
                opt = o.get("option_id") or o.get("id")
                break
        args = ["--request-id", str(rid)]
        if opt:
            args += ["--option", str(opt)]
        r, rec = cli("droid", "permit", *args, session=worker)
        note("permit settles the request", rec and rec.get("permitted") is not None,
             str(rec)[:200])

        # 7. ordinary idle arrives after the turn ends
        deadline = time.time() + 120
        idle = []
        while time.time() < deadline:
            idle = [e for e in events_of(host, "zcode", "worker_event")
                    if '"idle"' in json.dumps(e)]
            if idle:
                break
            time.sleep(2)
        note("turn-end idle still arrives", bool(idle))
        note("marker file written by real droid", marker.is_file())
    else:
        _, st2 = cli("droid", "status", session=worker)
        print("final worker status:", json.dumps(st2)[:800])
        _, obs = cli("droid", "observe", session=worker)
        print("observe:", json.dumps(obs)[:800])

    for sess, plat in ((worker, "droid"), (host, "zcode")):
        r, rec = cli(plat, "stop", "--force", session=sess, fake_home=(plat == "zcode"))
        print(f"stop {sess}: residual={rec.get('residual_pids') if rec else r.returncode}")
except Exception as exc:  # noqa
    import traceback
    traceback.print_exc()
finally:
    print(f"\nartifacts: {work}")
    bad = [n for n, ok, _ in results if not ok]
    print("PROBE:", "PASS" if results and not bad else f"INCOMPLETE ({bad})")
