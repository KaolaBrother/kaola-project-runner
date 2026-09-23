#!/usr/bin/env python3
"""Issue #126 D3 deep test (method of #119) for one Host platform (shadow HOME, isolated records)."""
import hashlib, json, os, shutil, subprocess, sys, time
RUN = "/tmp/kpr126-run.sh"
HOME = "/tmp/kpr126-home"
RECORDS = "/tmp/kpr126-records"
ENTRY = {"kimi-cli": "/skill:kaola-project-runner ", "codex": "$kaola-project-runner"}
HOST_ARGS = {}
p = sys.argv[1]
out = sys.argv[2]
wp = sys.argv[3] if len(sys.argv) > 3 else "dsh"
os.makedirs(out, exist_ok=True)
repo = os.path.realpath(f"/private/tmp/kpr126-d3/{p}")
if os.path.exists(repo):
    shutil.rmtree(repo)
os.makedirs(repo + "/.kaola")
subprocess.run(["git", "init", "-q", repo], check=True)
subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                "--allow-empty", "-m", "i"], check=True)
host = f"{p}-KPR-orchestrator-d3"
worker = f"{wp}-KPR-i126-w{p.replace('-', '')}"
D = f"{HOME}/.codex/skills/{wp}-kaola-project-runner/scripts/runtime-tmux.sh"
entry = ENTRY.get(p, "/kaola-project-runner")
noread = ("Do not open, read, cat or grep any kaola-project-runner SKILL.md or reference "
          "file in this turn; quote only from the Skill body this prompt's first line loaded.")
beat = (f"Issue #126 deep test beat ({p} Host). Do exactly this, then end the turn:\n"
        f"1. Begin your reply by quoting verbatim the first sentence under the heading "
        f"\"Heartbeat\" of the loaded Project Runner Skill body. {noread}\n"
        f"2. Read the worker: `{D} status --repo {repo} --session {worker}` and "
        f"`{D} capture --repo {repo} --session {worker} --lines 40`; report its reply text.\n"
        f"3. Exact-stop that worker: `{D} stop --repo {repo} --session {worker}`; report the "
        f"receipt fields stopped and residual_pids.\n"
        f"4. Overwrite {repo}/.kaola/heartbeat-prompt.json with a JSON object whose \"body\" is "
        f"\"deep test complete; nothing to do.\".\n"
        f"5. End the turn. Start nothing else, do not wait, sleep or poll.")
json.dump({"schema": "kaola-heartbeat-prompt/1", "body": beat},
          open(repo + "/.kaola/heartbeat-prompt.json", "w"), indent=2)
handoff = (f"{entry}\n"
           f"You are the {p} Host for an Issue #126 deep test. Project root: {repo}. Authorization: "
           f"exactly 1 {wp} worker seat for this test, supervise-only, no Workflow, nothing irreversible.\n"
           f"Before anything else, quote verbatim the first sentence of the second paragraph under the "
           f"heading \"Two entry points\" of the loaded Project Runner Skill body. {noread}\n"
           f"Then in this turn: (1) start exactly one worker: `{D} start --repo {repo} --session {worker}` "
           f"(no model flags) and report its receipt fields heartbeat_host, heartbeat_host_known and "
           f"heartbeat_host_source; (2) dispatch: `{D} send --repo {repo} --session {worker} --no-wait "
           f"--text 'Reply with exactly DEEP-WORKER-OK and nothing else.'`; (3) end your turn without "
           f"waiting, sleeping or polling. The worker's turn end wakes you through the heartbeat carrier.")

def run(*args):
    r = subprocess.run([RUN, *args], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"raw_stdout": r.stdout[-1500:], "raw_stderr": r.stderr[-1500:], "rc": r.returncode}

def save(name, obj):
    json.dump(obj, open(f"{out}/{name}", "w"), indent=1, ensure_ascii=False)

digest = hashlib.sha256(repo.encode()).hexdigest()[:16]
host_log = f"{RECORDS}/{p}/{host}/{digest}/events.jsonl"
def events():
    try:
        return [json.loads(l) for l in open(host_log)]
    except OSError:
        return []

summary = {"platform": p, "host": host, "worker": worker, "repo": repo, "entry": entry}
start = run(p, "start", "--repo", repo, "--session", host, *HOST_ARGS.get(p, []))
save("1-host-start.json", start)
summary["host_start"] = {k: start.get(k) for k in ("state", "error", "result", "reason",
                         "requested_tier", "resolved_runtime_model_id", "effective_selection")}
try:
    if start.get("state") != "ready":
        raise SystemExit
    time.sleep(3)
    sent = run(p, "send", "--repo", repo, "--session", host, "--no-wait", "--text", handoff)
    save("2-handoff-send.json", sent)
    summary["handoff_dispatch_cursor"] = sent.get("dispatch_event_cursor")
    deadline = time.time() + 1500
    permissions = []
    while time.time() < deadline:
        ev = events()
        ends = [e for e in ev if e.get("kind") == "turn_ended"]
        confirmed = [e for e in ev if e.get("kind") == "worker_event_confirmed"]
        delivered = [e for e in ev if e.get("kind") == "worker_event_delivered"]
        st = run(p, "status", "--repo", repo, "--session", host)
        pend = st.get("pending_permissions") or []
        if pend:
            permissions.append(pend)
        settled = (len(ends) >= 2 and confirmed and len(confirmed) >= len(delivered)
                   and not st.get("turn_active"))
        if settled:
            time.sleep(20)  # a terminated event may open one more beat
            st = run(p, "status", "--repo", repo, "--session", host)
            ev2 = events()
            d2 = [e for e in ev2 if e.get("kind") == "worker_event_delivered"]
            c2 = [e for e in ev2 if e.get("kind") == "worker_event_confirmed"]
            if not st.get("turn_active") and len(c2) >= len(d2):
                break
        time.sleep(8)
    summary["timed_out"] = time.time() >= deadline
    summary["pending_permissions_seen"] = permissions[-1:] if permissions else []
finally:
    if os.path.exists(host_log):
        shutil.copy(host_log, f"{out}/host-events.jsonl")
    wst = run(wp, "status", "--repo", repo, "--session", worker)
    save("5-worker-status.json", wst)
    summary["worker_state_before_cleanup"] = wst.get("state")
    if wst.get("agent_alive"):
        summary["worker_cleanup_stop"] = run(wp, "stop", "--repo", repo, "--session", worker, "--force")
    hs = run(p, "stop", "--repo", repo, "--session", host)
    save("6-host-stop.json", hs)
    summary["host_stop"] = {k: hs.get(k) for k in ("stopped", "residual_pids", "error")}
    save("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False)[:1500])
