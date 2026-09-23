#!/usr/bin/env python3
import glob, hashlib, importlib.util, json, os, sys
E = sys.argv[1]
W = "/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-126"
spec = importlib.util.spec_from_file_location("h", f"{W}/scripts/kaola-acp-holder.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def manifest(p):
    out = {}
    for raw in open(f"{W}/platforms/{p}.yaml"):
        if raw.strip():
            k, _, v = raw.partition(":"); out[k.strip()] = json.loads(v.strip())
    return out
HOME = "/tmp/kpr126-home"
res = {}
for p in sys.argv[2:]:
    d = f"{E}/{p}" if os.path.isdir(f"{E}/{p}") else E; s = json.load(open(f"{d}/summary.json"))
    repo, worker = s["repo"], s["worker"]
    wp = worker.split("-KPR-")[0]
    D = f"{HOME}/.codex/skills/{wp}-kaola-project-runner/scripts/runtime-tmux.sh"
    ev = [json.loads(l) for l in open(f"{d}/host-events.jsonl")]
    since = s.get("handoff_dispatch_cursor") or 0
    ev = [e for e in ev if (e.get("cursor") or 0) >= since]
    staged = [e for e in ev if e.get("kind") == "worker_event"]
    delivered = [e for e in ev if e.get("kind") == "worker_event_delivered"]
    confirmed = [e for e in ev if e.get("kind") == "worker_event_confirmed"]
    ends = [e["cursor"] for e in ev if e.get("kind") == "turn_ended"]
    # the beat body in effect at the first delivery = the one the driver wrote
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
    fact = manifest(p)
    first = delivered[0] if delivered else None
    match = None; lines = None
    if first:
        ev_obj = [e["event"] for e in staged if e["event"]["event_id"] in first["event_ids"]]
        h = object.__new__(m.Holder)
        h.args = type("A", (), {"platform": p, "repo": repo, "session": s["host"]})()
        h.host_entry = fact["host_skill_entry"]; h.host_name = fact["runtime_name"]
        path = f"{repo}/.kaola/heartbeat-prompt.json"; cur = open(path).read()
        open(path, "w").write(json.dumps({"schema": "kaola-heartbeat-prompt/1", "body": beat}, indent=2))
        try:
            text, meta = h._heartbeat_payload(ev_obj)
        finally:
            open(path, "w").write(cur)
        fp = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
        match = fp == first.get("prompt_fingerprint")
        lines = text.split("\n")[:2]
        open(f"{d}/carrier-rebuilt.txt", "w").write(text)
    wrec = glob.glob(f"/tmp/kpr126-records/{wp}/{worker}/*/record.json")
    wr = json.load(open(wrec[0])) if wrec else {}
    wstat = json.load(open(f"{d}/5-worker-status.json"))
    hb = json.load(open(f"{repo}/.kaola/heartbeat-prompt.json")).get("body")
    res[p] = {
        "host_start": s["host_start"], "host_stop": s["host_stop"],
        "worker_bound_to": wr.get("heartbeat_host"),
        "carrier_delivered": [(e["cursor"], e["event_ids"]) for e in delivered],
        "carrier_confirmed": [(e["cursor"], e["event_ids"]) for e in confirmed],
        "turn_end_cursors": ends,
        "carrier_fingerprint_match": match, "carrier_lines_1_2": lines,
        "worker_state_after": wstat.get("state"),
        "driver_had_to_stop_worker": "worker_cleanup_stop" in s,
        "heartbeat_file_body_now": hb,
    }
json.dump(res, open(f"{E}/uat.json", "w"), indent=1, ensure_ascii=False)
for p, r in res.items():
    b = r["worker_bound_to"] or {}
    print(f"{p:12s} start={r['host_start'].get('state')} bound={b.get('platform')}/{b.get('session')} "
          f"delivered={[c for c,_ in r['carrier_delivered']]} confirmed={[c for c,_ in r['carrier_confirmed']]} "
          f"ends={r['turn_end_cursors']} fp_match={r['carrier_fingerprint_match']} lines={r['carrier_lines_1_2']} "
          f"worker={r['worker_state_after']} driver_stop={r['driver_had_to_stop_worker']} hb={r['heartbeat_file_body_now']!r} "
          f"host_stop={r['host_stop']}")
