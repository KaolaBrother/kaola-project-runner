#!/usr/bin/env python3
"""Issue #65 round 2: does `claude --input-format stream-json` ACKNOWLEDGE an
injected mid-turn user message, or only accept the bytes?

Dumps EVERY raw stdout line with its arrival time, so the reply to
"is there a native consumption confirmation?" rests on the wire, not on a
successful `write()`. Also probes the two failure shapes the reviewer named:
a steer written after the turn's `result`, and a steer written into a stdin
that is closing.

Isolated: one `claude` child in its own scratch cwd.
"""
import json, os, subprocess, sys, threading, time

CWD = "/tmp/kw-i65-ack/scratch"
os.makedirs(CWD, exist_ok=True)
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/kw-i65-ack/ack.json"
MODE = sys.argv[2] if len(sys.argv) > 2 else "midturn"

args = ["claude", "-p", "--input-format", "stream-json",
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", "bypassPermissions", "--model", "sonnet"]
proc = subprocess.Popen(args, cwd=CWD, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, bufsize=1)
raw = []
t0 = time.time()
threading.Thread(target=lambda: [raw.append((round(time.time() - t0, 3), l.rstrip("\n")))
                                 for l in proc.stdout], daemon=True).start()
err = []
threading.Thread(target=lambda: err.extend(proc.stderr.readlines()), daemon=True).start()

def user_msg(text):
    return json.dumps({"type": "user", "message": {"role": "user",
            "content": [{"type": "text", "text": text}]}}) + "\n"

def parsed():
    out = []
    for ts, l in list(raw):
        l = l.strip()
        if l.startswith("{"):
            try: out.append((ts, json.loads(l)))
            except ValueError: pass
    return out

rec = {"mode": MODE, "argv": args}
LONG = ("Use the Bash tool to run these commands ONE AT A TIME, each in its own "
        "separate tool call, never batched: `sleep 5 && echo step-1`, then "
        "`sleep 5 && echo step-2`, and so on up through step-10. Print a "
        "one-line comment after each. Do not stop early.")
STEER = "STOP the loop now and reply with exactly one line: ACK-PROBE-65"

proc.stdin.write(user_msg(LONG)); proc.stdin.flush()

# wait for the turn to be genuinely underway (first tool_use)
deadline = time.time() + 90
while time.time() < deadline:
    if any(b.get("type") == "tool_use"
           for _, e in parsed() if e.get("type") == "assistant"
           for b in (e.get("message") or {}).get("content") or []):
        break
    time.sleep(0.2)
rec["tool_seen_at_s"] = round(time.time() - t0, 3)

if MODE == "after_result":
    # wait for the turn to settle first, then steer into a finished turn
    while time.time() < deadline and not any(e.get("type") == "result" for _, e in parsed()):
        time.sleep(0.2)

steer_at = time.time()
rec["steer_written_at_s"] = round(steer_at - t0, 3)
rec["lines_before_steer"] = len(raw)
try:
    proc.stdin.write(user_msg(STEER)); proc.stdin.flush()
    rec["write_error"] = None
except Exception as exc:                      # noqa: BLE001 - recording the shape
    rec["write_error"] = repr(exc)

if MODE == "close_race":
    time.sleep(0.05)
    try:
        proc.stdin.close()
        rec["close_error"] = None
    except Exception as exc:                  # noqa: BLE001
        rec["close_error"] = repr(exc)

# drain
end = time.time() + 200
while time.time() < end:
    if MODE == "after_result":
        if sum(1 for _, e in parsed() if e.get("type") == "result") >= 2:
            break
    elif any(e.get("type") == "result" for _, e in parsed()):
        time.sleep(3)
        break
    time.sleep(0.3)

events = parsed()
rec["result_events"] = [
    {"at_s": ts, "subtype": e.get("subtype"), "num_turns": e.get("num_turns"),
     "result_head": str(e.get("result"))[:160]}
    for ts, e in events if e.get("type") == "result"]
rec["event_types_after_steer"] = [
    {"at_s": ts, "type": e.get("type"), "subtype": e.get("subtype"),
     "head": json.dumps(e, ensure_ascii=False)[:260]}
    for ts, e in events if ts >= round(steer_at - t0, 3)][:40]
rec["steer_text_echoed"] = any("ACK-PROBE-65" in json.dumps(e, ensure_ascii=False)
                               for ts, e in events if ts >= round(steer_at - t0, 3)
                               and e.get("type") == "user")
rec["any_user_event_after_steer"] = [
    json.dumps(e, ensure_ascii=False)[:400]
    for ts, e in events if ts >= round(steer_at - t0, 3) and e.get("type") == "user"][:6]
rec["stderr_tail"] = "".join(err)[-400:]
rec["raw_line_count"] = len(raw)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump({"summary": rec,
               "raw": [{"t": ts, "line": l[:4000]} for ts, l in raw]},
              fh, ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False, indent=1)[:3000])
try:
    proc.stdin.close(); proc.terminate(); proc.wait(timeout=5)
except Exception:
    proc.kill()
