#!/usr/bin/env python3
"""Issue #119 M0 probe: fresh ACP session per call; send one prompt; record
available commands, tool calls, and reply text. Standalone starts only."""
import json, subprocess, sys, time
RUN = "/tmp/kpr119-run.sh"
REPO = "/private/tmp/kpr119-scratch"

def run(platform, action, session, *extra):
    out = subprocess.run([RUN, platform, action, "--repo", REPO, "--session", session, *extra],
                         capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except ValueError:
        return {"raw_stdout": out.stdout[-2000:], "raw_stderr": out.stderr[-2000:], "rc": out.returncode}

def probe(platform, session, text, start_extra=(), wait=240):
    rec = {"platform": platform, "session": session, "prompt": text}
    st = run(platform, "start", session, *start_extra)
    rec["start"] = {k: st.get(k) for k in ("state", "error", "result", "reason", "acp_session_id",
                                            "resolved_runtime_model_id", "raw_stderr")}
    rec["agent_info"] = (st.get("transport") or {}).get("agent_info")
    try:
        if st.get("state") != "ready":
            return rec
        time.sleep(3)
        snd = run(platform, "send", session, "--text", text)
        rec["send"] = {k: snd.get(k) for k in ("error", "stop_reason", "turn_outcome")}
        deadline = time.time() + wait
        while time.time() < deadline:
            s = run(platform, "status", session)
            if not s.get("turn_active"):
                break
            time.sleep(4)
        cap = run(platform, "capture", session, "--lines", "5000")
        cmds, tools, reply = [], [], []
        for e in cap.get("events", []):
            u = e.get("update") or {}
            kind = u.get("sessionUpdate")
            if kind == "available_commands_update":
                cmds = [c.get("name") for c in u.get("availableCommands", [])]
            elif kind in ("tool_call", "tool_call_update"):
                tools.append({"cursor": e.get("cursor"), "kind": kind, "title": u.get("title"),
                              "toolKind": u.get("kind"), "rawInput": u.get("rawInput"),
                              "status": u.get("status")})
            elif kind == "agent_message_chunk":
                reply.append((u.get("content") or {}).get("text", ""))
            elif e.get("kind") == "turn_ended":
                rec["turn_ended"] = {"cursor": e.get("cursor"), "outcome": e.get("outcome"),
                                     "stop_reason": e.get("stop_reason")}
        rec["available_commands"] = cmds
        rec["tool_calls"] = tools
        rec["reply"] = "".join(reply)
        rec["event_cursor"] = cap.get("event_cursor")
    finally:
        sp = run(platform, "stop", session)
        rec["stop"] = {k: sp.get(k) for k in ("stopped", "residual_pids", "error")}
    return rec

if __name__ == "__main__":
    platform, session, text = sys.argv[1], sys.argv[2], sys.argv[3]
    extra = sys.argv[4:]
    print(json.dumps(probe(platform, session, text, extra), ensure_ascii=False, indent=1))
