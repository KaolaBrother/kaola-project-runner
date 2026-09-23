#!/usr/bin/env python3
import json, os, re, sys
E = sys.argv[1]
SKILL = "/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-126/skills/kaola-project-runner/SKILL.md"
body = open(SKILL).read()
A2 = "or your platform's measured entry"          # new-build-only, 2nd paragraph of "Two entry points"
A5 = "The heartbeat is the working prompt itself"  # new-build first sentence under "Heartbeat"
def norm(t): return re.sub(r"\s+", " ", t.replace("*", "").replace("`", "")).strip()
assert norm(A2) in norm(body) and norm(A5) in norm(body)
report = {}
for p in sys.argv[2:] or ["codex"]:
    d = f"{E}/{p}" if os.path.isdir(f"{E}/{p}") else E
    f = f"{d}/host-events.jsonl"
    if not os.path.exists(f):
        report[p] = {"error": "no host event log"}; continue
    ev = [json.loads(l) for l in open(f)]
    sm = json.load(open(f"{d}/summary.json")) if os.path.exists(f"{d}/summary.json") else {}
    since = sm.get("handoff_dispatch_cursor") or 0
    ev = [e for e in ev if (e.get("cursor") or 0) >= since]
    turns, cur = [], {"text": [], "tools": [], "first": None}
    for e in ev:
        u = e.get("update") or {}
        if cur["first"] is None: cur["first"] = e.get("cursor")
        if u.get("sessionUpdate") == "agent_message_chunk":
            cur["text"].append((u.get("content") or {}).get("text", ""))
        if u.get("sessionUpdate") in ("tool_call", "tool_call_update") and (u.get("title") or u.get("rawInput")):
            cur["tools"].append({"cursor": e.get("cursor"), "title": u.get("title"),
                                 "rawInput": u.get("rawInput")})
        if e.get("kind") == "turn_ended":
            cur["end"] = e.get("cursor"); cur["outcome"] = e.get("outcome")
            turns.append(cur); cur = {"text": [], "tools": [], "first": None}
    kinds = [(e.get("cursor"), e.get("kind"), e.get("event_ids") or (e.get("event") or {}).get("event_id"))
             for e in ev if str(e.get("kind", "")).startswith("worker_event")]
    def judge(t, anchor):
        text = "".join(t["text"])
        blob = json.dumps(t["tools"])
        reads = [x for x in t["tools"] if re.search(r"(?<![a-z-])kaola-project-runner/(SKILL\.md|references)", json.dumps(x))
                 or (("grep" in json.dumps(x).lower() or "search" in json.dumps(x).lower())
                     and "kaola-project-runner" in json.dumps(x) and "dsh-kaola" not in json.dumps(x))]
        def is_skill_tool(x):
            blob = json.dumps(x)
            if "runtime-tmux" in blob or "SKILL.md" in blob:
                return False
            named = re.search(r"(?<![a-z-])kaola-project-runner(?![a-z-])", blob)
            skillish = re.search(r"\bskill\b|Invoked skill", blob, re.I)
            return bool(named and skillish)
        e1 = [x for x in t["tools"] if is_skill_tool(x)]
        return {"cursor_range": [t["first"], t.get("end")], "outcome": t.get("outcome"),
                "anchor_quoted": norm(anchor) in norm(text), "skill_file_reads": reads,
                "e1_tool_calls": e1, "reply_excerpt": text[:700]}
    r = {"turns": len(turns), "worker_events": kinds}
    if turns: r["step2"] = judge(turns[0], A2)
    if len(turns) > 1: r["step5"] = judge(turns[1], A5)
    for name in ("summary.json",):
        if os.path.exists(f"{d}/{name}"): r["summary"] = json.load(open(f"{d}/{name}"))
    report[p] = r
json.dump(report, open(f"{E}/analysis.json", "w"), indent=1, ensure_ascii=False)
for p, r in report.items():
    s2, s5 = r.get("step2", {}), r.get("step5", {})
    def v(s):
        if not s: return "MISSING"
        clean_e2 = s["anchor_quoted"] and not s["skill_file_reads"]
        return (("E1 " if s["e1_tool_calls"] else "") + ("E2 " if clean_e2 else "") +
                ("anchor-but-read " if s["anchor_quoted"] and s["skill_file_reads"] else "") +
                ("no-anchor" if not s["anchor_quoted"] else "")).strip() + f" {s['cursor_range']}"
    print(f"{p:12s} turns={r.get('turns')} step2=[{v(s2)}] step5=[{v(s5)}] events={len(r.get('worker_events', []))} host_stop={(r.get('summary') or {}).get('host_stop')}")
