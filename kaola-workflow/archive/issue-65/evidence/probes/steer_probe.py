#!/usr/bin/env python3
"""Issue #65 native mid-turn steering probe for one ACP agent.

Phase 1 (idle, no model spend): initialize + session/new, record every
steering-shaped advertisement, then call each candidate steering method while
the session is IDLE.  A -32601 means the entry does not exist; any other reply
means the entry exists and we learn its idle semantics.  Requests carry
`_meta.steering.idleBehavior = "promptRequired"` so a supporting agent answers
without starting a detached turn.

Phase 2 (--live, real model spend): start a deliberately long multi-tool turn,
and while it is genuinely running either call the discovered steering entry or
send a second ordinary `session/prompt`.  Classifies the outcome as
injected / started-new-turn / cancelled-original / rejected, and records whether
the ORIGINAL `session/prompt` keeps its own response attribution.

Isolation: owns only the child it spawns, in its own scratch cwd.  It never
touches tmux, any Kaola holder, any existing session, or any other project.
"""
import argparse, json, os, shlex, signal, subprocess, sys, threading, time

SENTINEL = "STEERED-OK-65"
LONG = ("Use your shell/bash tool to run these commands ONE AT A TIME, each in "
        "its own separate tool call, never batched: `sleep 4 && echo step-1`, "
        "then `sleep 4 && echo step-2`, and so on up through step-12. Print a "
        "one-line comment after each. Do not stop early, do not combine them.")
STEER = ("STOP. Abandon the step loop immediately. Do not run any more shell "
         f"commands. Reply with exactly one line: {SENTINEL}")
IDLE_PROBE = "ping"
CANDIDATES = ["_session/steering", "session/steering", "session/steer",
              "_session/steer"]


class Conn:
    def __init__(self, cmd, cwd, env):
        self.proc = subprocess.Popen(
            shlex.split(cmd), cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.msgs, self.err, self.lock = [], [], threading.Lock()
        self.answered = set()
        threading.Thread(target=self._pump, daemon=True).start()
        threading.Thread(
            target=lambda: self.err.extend(self.proc.stderr.readlines()),
            daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line.startswith("{"):
                try:
                    self.msgs.append((time.time(), json.loads(line)))
                except ValueError:
                    pass

    def send(self, obj):
        with self.lock:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()

    def call(self, rid, method, params, _meta=None):
        frame = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        if _meta:
            frame["params"]["_meta"] = _meta
        self.send(frame)

    def all(self):
        return list(self.msgs)

    def settled(self, rid):
        for ts, m in self.all():
            if m.get("id") == rid and ("result" in m or "error" in m):
                return ts, m
        return None, None

    def service(self):
        """Answer agent->client requests so a turn is never blocked on us."""
        for ts, m in self.all():
            if not m.get("method") or m.get("id") is None:
                continue
            if m["id"] in self.answered:
                continue
            self.answered.add(m["id"])
            meth = m.get("method", "")
            if "ermission" in meth:
                opts = ((m.get("params") or {}).get("options")) or []
                pick = next((o.get("optionId") for o in opts
                             if "allow" in str(o.get("kind", "")).lower()), None)
                if pick is None and opts:
                    pick = opts[0].get("optionId")
                self.send({"jsonrpc": "2.0", "id": m["id"],
                           "result": {"outcome": {"outcome": "selected",
                                                  "optionId": pick}}})
            else:
                self.send({"jsonrpc": "2.0", "id": m["id"],
                           "error": {"code": -32601,
                                     "message": "client capability disabled"}})

    def wait(self, rid, timeout):
        end = time.time() + timeout
        while time.time() < end:
            self.service()
            ts, m = self.settled(rid)
            if m:
                return ts, m
            time.sleep(0.15)
        return None, None

    def tool_updates(self):
        n = 0
        for _, m in self.all():
            if m.get("method") == "session/update":
                u = ((m.get("params") or {}).get("update")) or {}
                if "tool_call" in str(u.get("sessionUpdate")):
                    n += 1
        return n

    def texts(self):
        out = []
        for ts, m in self.all():
            if m.get("method") != "session/update":
                continue
            u = ((m.get("params") or {}).get("update")) or {}
            c = u.get("content") or {}
            if isinstance(c, dict) and c.get("type") == "text":
                out.append((ts, c.get("text", "")))
        return out

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--env", default="")
    ap.add_argument("--meta", default="")
    ap.add_argument("--mode", default="")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--budget", type=float, default=300.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--hard-timeout", type=float, default=420.0)
    a = ap.parse_args()

    if a.hard_timeout > 0:
        def _bail(_sig, _frm):
            sys.stderr.write("hard-timeout reached\n")
            os._exit(124)
        signal.signal(signal.SIGALRM, _bail)
        signal.alarm(int(a.hard_timeout))

    cwd = os.path.join("/tmp/kw-issue65-probe", f"scratch-{a.id}")
    os.makedirs(cwd, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "HOME", "USER", "SHELL", "LANG", "TMPDIR", "TERM")}
    for pair in filter(None, a.env.split(",")):
        k, _, v = pair.partition("=")
        env[k] = v if v else os.environ.get(k, "")

    rec = {"id": a.id, "cmd": a.cmd, "probed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "live": a.live}
    c = Conn(a.cmd, cwd, env)
    t0 = time.time()
    init_params = {"protocolVersion": 1,
                   "clientCapabilities": {
                       "fs": {"readTextFile": False, "writeTextFile": False},
                       "terminal": False}}
    if a.meta:
        init_params["clientCapabilities"]["_meta"] = json.loads(a.meta)
    init_params["_meta"] = {"steering": {"supported": True}}
    c.call(1, "initialize", init_params)
    _, m = c.wait(1, 90)
    if not m or "result" not in m:
        rec["fatal"] = "initialize failed"
        rec["initialize"] = m
        return dump(rec, c, a)
    r = m["result"]
    rec["agent_info"] = r.get("agentInfo")
    rec["protocol_version"] = r.get("protocolVersion")
    rec["init_meta"] = r.get("_meta")
    caps = r.get("agentCapabilities") or {}
    rec["agent_capabilities"] = caps
    rec["steering_advertised"] = {
        "top_level_meta_steering": (r.get("_meta") or {}).get("steering"),
        "capabilities_meta_steering": (caps.get("_meta") or {}).get("steering"),
        "session_capabilities": caps.get("sessionCapabilities"),
    }
    blob = json.dumps(r, ensure_ascii=False).lower()
    rec["steering_word_in_initialize"] = "steer" in blob

    c.call(2, "session/new", {"cwd": cwd, "mcpServers": []})
    _, m = c.wait(2, 120)
    if not m or "result" not in m:
        rec["fatal"] = "session/new failed"
        rec["session_new"] = m
        return dump(rec, c, a)
    sid = m["result"]["sessionId"]
    rec["session_id"] = sid

    if a.mode:
        c.call(3, "session/set_mode", {"sessionId": sid, "modeId": a.mode})
        c.wait(3, 30)

    # ---- phase 1: idle method discovery (no model spend) -------------------
    rec["idle_entry_probe"] = {}
    live_entry = None
    rid = 100
    for method in CANDIDATES:
        rid += 1
        c.call(rid, method,
               {"sessionId": sid, "prompt": [{"type": "text", "text": IDLE_PROBE}]},
               _meta={"steering": {"idleBehavior": "promptRequired"}})
        _, resp = c.wait(rid, 30)
        entry = {"response": resp}
        if resp is None:
            entry["verdict"] = "no-reply"
        elif "result" in resp:
            entry["verdict"] = "present"
            live_entry = live_entry or method
        else:
            code = (resp.get("error") or {}).get("code")
            entry["verdict"] = "absent" if code == -32601 else "present-errored"
            if code != -32601:
                live_entry = live_entry or method
        rec["idle_entry_probe"][method] = entry
    rec["native_entry"] = live_entry
    rec["idle_probe_elapsed_s"] = round(time.time() - t0, 2)

    if not a.live:
        return dump(rec, c, a)

    # ---- phase 2: real long turn + mid-turn steer ---------------------------
    c.call(10, "session/prompt",
           {"sessionId": sid, "prompt": [{"type": "text", "text": LONG}]})
    p_sent = time.time()
    end = time.time() + 150
    while time.time() < end and c.tool_updates() < 2:
        c.service()
        if c.settled(10)[1]:
            break
        time.sleep(0.3)
    rec["tool_updates_before_steer"] = c.tool_updates()
    rec["turn_active_at_steer"] = c.settled(10)[1] is None
    rec["steer_offset_s"] = round(time.time() - p_sent, 2)

    steer_ts = None
    if live_entry:
        c.call(20, live_entry,
               {"sessionId": sid, "prompt": [{"type": "text", "text": STEER}]})
        ts, resp = c.wait(20, 90)
        rec["steer_method"] = live_entry
        rec["steer_response"] = resp
        steer_ts = ts or time.time()
    else:
        c.call(21, "session/prompt",
               {"sessionId": sid, "prompt": [{"type": "text", "text": STEER}]})
        rec["steer_method"] = "session/prompt (second ordinary prompt)"
        steer_ts = time.time()
        rec["second_prompt_sent_s"] = round(steer_ts - p_sent, 2)

    end = time.time() + max(60.0, a.budget - (time.time() - t0))
    while time.time() < end:
        c.service()
        d10 = c.settled(10)[1]
        d21 = c.settled(21)[1]
        if d10 and (live_entry or d21):
            break
        if d10 and time.time() - p_sent > a.budget * 0.8:
            break
        time.sleep(0.4)

    def settle(i):
        ts, m = c.settled(i)
        if not m:
            return None
        return {"at_s": round(ts - p_sent, 2), "result": m.get("result"),
                "error": m.get("error")}

    rec["prompt10_settle"] = settle(10)
    rec["prompt21_settle"] = settle(21)
    texts = c.texts()
    joined = "".join(t for _, t in texts)
    rec["sentinel_seen"] = SENTINEL in joined
    s10 = rec["prompt10_settle"]
    before = "".join(t for ts, t in texts
                     if s10 and (ts - p_sent) <= s10["at_s"])
    after_steer_before_settle = "".join(
        t for ts, t in texts
        if steer_ts and ts >= steer_ts and s10 and (ts - p_sent) <= s10["at_s"])
    rec["sentinel_before_prompt10_settled"] = SENTINEL in before
    rec["sentinel_after_steer_and_before_settle"] = SENTINEL in after_steer_before_settle
    rec["tool_updates_total"] = c.tool_updates()
    rec["tool_updates_after_steer"] = sum(
        1 for ts, m in c.all()
        if steer_ts and ts >= steer_ts and m.get("method") == "session/update"
        and "tool_call" in str((((m.get("params") or {}).get("update")) or {})
                               .get("sessionUpdate")))
    rec["tail_text"] = joined[-400:]

    stop10 = ((s10 or {}).get("result") or {}).get("stopReason")
    if rec["sentinel_after_steer_and_before_settle"] and stop10 == "end_turn":
        rec["classification"] = "injected-into-running-turn"
    elif stop10 == "cancelled":
        rec["classification"] = "second-message-cancelled-original-turn"
    elif rec["prompt21_settle"] and not rec["sentinel_before_prompt10_settled"]:
        rec["classification"] = "queued-to-next-turn"
    elif rec["prompt21_settle"] and (rec["prompt21_settle"].get("error")):
        rec["classification"] = "rejected"
    else:
        rec["classification"] = "inconclusive"

    c.call(99, "session/cancel", {"sessionId": sid})
    time.sleep(1)
    return dump(rec, c, a)


def dump(rec, c, a):
    rec["stderr_tail"] = "".join(c.err)[-600:]
    c.close()
    text = json.dumps(rec, indent=2, ensure_ascii=False)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
