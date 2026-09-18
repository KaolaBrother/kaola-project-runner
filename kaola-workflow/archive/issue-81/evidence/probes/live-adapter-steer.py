#!/usr/bin/env python3
"""Issue #81: bounded real v4 steer against the INTEGRATED adapter bytes.

The earlier live proofs (live/, live2/) drove the raw backend with a probe
script — they proved the v4 surface but are not byte-bound to the adapter.
This driver runs the worktree's `scripts/kaola-zcode-acp.py` itself against
the real ZCode.app 3.12.3 app-server in a disposable repo:

    adapter --zcode-entry <zcode.cjs> --zcode-node <node> --cwd <repo>
      <- initialize / session/new / session/prompt / _session/steering
      -> ACP results + session/event steer events

The prompt asks for many SHORT Bash calls so the turn offers an injection
boundary every few seconds; the drain should land inside the adapter's
bounded window -> `injected`. If the backend is slow, `written` with the
drain observed later in the raw event log is the honest fallback — the
outcome is whatever the adapter reports from events, never the ack.

Credential hygiene: the adapter reads ~/.zcode itself; this driver never
opens config files. Everything persisted passes `redact()` first, and the
log is additionally scanned for key-shaped fields before being kept.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

ADAPTER = os.environ.get(
    "KPR_ADAPTER",
    "/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner"
    "/.kw/worktrees/issue-81/scripts/kaola-zcode-acp.py")
ENTRY = "/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"
NODE = "/opt/homebrew/bin/node"
TEE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "backend-tee.py")

SECRET_KEYS = re.compile(
    r"apiKey|api_key|secret|token|authorization|password|credential", re.I)
BEARER = re.compile(r"(?i)(bearer\s+|sk-|key-|token[=:]\s*)[A-Za-z0-9_\-]{8,}")


def redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if SECRET_KEYS.search(str(k)) and isinstance(v, str) and v:
                out[k] = f"<redacted:{len(v)}>"
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str) and len(obj) > 16 and BEARER.search(obj):
        return "<redacted-string>"
    return obj


class AdapterProc:
    def __init__(self, repo: str, raw_log, node: str = NODE) -> None:
        env = {
            "HOME": os.environ.get("HOME", ""),
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "LANG": "C",
            "PYTHONUNBUFFERED": "1",
            "TMPDIR": tempfile.gettempdir(),
        }
        self.proc = subprocess.Popen(
            [sys.executable, ADAPTER,
             "--zcode-entry", ENTRY, "--zcode-node", node,
             "--cwd", repo],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=repo, env=env, text=True)
        self.next_id = 0
        self.pending: dict[str, queue.Queue] = {}
        self.events: queue.Queue = queue.Queue()
        self.lock = threading.Lock()
        self.raw = raw_log
        self.stderr_lines: list[str] = []
        threading.Thread(target=self._read_out, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()

    def _read_out(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                self._log({"raw_unparsed": line})
                continue
            self._log(msg)
            mid = msg.get("id")
            if mid is not None and ("result" in msg or "error" in msg):
                with self.lock:
                    waiter = self.pending.pop(str(mid), None)
                if waiter:
                    waiter.put(msg)
            elif msg.get("method"):
                self.events.put(msg)

    def _read_err(self):
        for line in self.proc.stderr:
            self.stderr_lines.append(line.rstrip("\n"))

    def _log(self, obj):
        self.raw.write(json.dumps(redact(obj), ensure_ascii=False) + "\n")
        self.raw.flush()

    def call(self, method, params=None, timeout=90):
        waiter: queue.Queue = queue.Queue()
        with self.lock:
            self.next_id += 1
            rid = self.next_id
            self.pending[str(rid)] = waiter
        self.proc.stdin.write(
            json.dumps({"id": rid, "method": method,
                        "params": params or {}}) + "\n")
        self.proc.stdin.flush()
        self._log({"sent": {"id": rid, "method": method,
                            "params": params or {}}})
        try:
            return waiter.get(timeout=timeout)
        except queue.Empty:
            return {"id": rid,
                    "error": {"code": "driver-timeout",
                              "message": f"no reply to {method} in {timeout}s"}}

    def wait_for(self, pred, timeout):
        end = time.time() + timeout
        seen = []
        while time.time() < end:
            try:
                msg = self.events.get(timeout=max(0.05, end - time.time()))
            except queue.Empty:
                break
            seen.append(msg)
            if pred(msg):
                return msg, seen
        return None, seen


def sev(msg):
    if msg.get("method") != "session/update":
        return None, None
    p = msg.get("params") or {}
    upd = p.get("update") or {}
    return upd.get("sessionUpdate"), upd


LOOP_PROMPT = (
    "Run each of these commands as a SEPARATE Bash tool call, one after "
    "another, waiting for each to finish before starting the next: "
    "`sleep 4; echo step-1`, then `sleep 4; echo step-2`, then "
    "`sleep 4; echo step-3`, then `sleep 4; echo step-4`, then "
    "`sleep 4; echo step-5`, then `sleep 4; echo step-6`, then "
    "`sleep 4; echo step-7`, then `sleep 4; echo step-8`. "
    "When all eight steps have finished, reply with exactly: DONE-TURN-81. "
    "Do not reply before all steps finish.")
STEER_TEXT = "Abandon the remaining steps and reply with exactly: STEERED-ADAPTER-81-OK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    raw = open(os.path.join(args.out, "raw-ndjson.jsonl"), "w", encoding="utf-8")
    report: dict = {"adapter": ADAPTER, "repo": args.repo}

    # Stage the whitelist-only backend tee: it sits where the adapter expects
    # `node`, spawns the real app-server, and writes backend-tee.jsonl with
    # only the whitelisted steer fields + hashes (see backend-tee.py and its
    # fixture test). Raw stdio forwarding is in-memory only.
    shim = os.path.join(args.out, "backend-tee.py")
    shutil.copyfile(TEE, shim)
    os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP)
    tee_log = os.path.join(args.out, "backend-tee.jsonl")
    with open(os.path.join(args.out, "backend-tee-config.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"real_node": NODE, "log": tee_log}, fh)
    drv = AdapterProc(args.repo, raw, node=shim)

    r = drv.call("initialize", {"protocolVersion": 1}, timeout=20)
    report["initialize"] = r.get("result", r.get("error"))
    r = drv.call("session/new", {"cwd": args.repo, "mcpServers": []}, timeout=90)
    report["session/new"] = r.get("result", r.get("error"))
    sid = ((r.get("result") or {}).get("sessionId"))
    if not sid:
        report["fatal"] = "session/new returned no sessionId"
        json.dump(report, open(os.path.join(args.out, "report.json"), "w"),
                  indent=2, default=str)
        return 2

    # The prompt rides a background thread: session/prompt stays pending
    # until the turn ends, exactly like the holder's send.
    prompt_reply: dict = {}
    def do_prompt():
        prompt_reply.update(drv.call(
            "session/prompt",
            {"sessionId": sid,
             "prompt": [{"type": "text", "text": LOOP_PROMPT}]},
            timeout=300))
    threading.Thread(target=do_prompt, daemon=True).start()

    # Wait for the turn to actually be running before steering.
    msg, seen = drv.wait_for(
        lambda m: sev(m)[0] not in (None, "available_commands_update"), 60)
    report["first_update"] = sev(msg)[0] if msg else None
    time.sleep(4)  # let the first Bash call get going

    steer = drv.call("_session/steering", {
        "sessionId": sid,
        "prompt": [{"type": "text", "text": STEER_TEXT}],
        "_meta": {"steering": {"idleBehavior": "promptRequired"}},
    }, timeout=60)
    report["steer_reply"] = steer.get("result", steer.get("error"))

    # Collect everything until the prompt resolves (turn end), then a tail.
    end = time.time() + 240
    tail_events = []
    while time.time() < end and not prompt_reply:
        try:
            tail_events.append(drv.events.get(timeout=1.0))
        except queue.Empty:
            pass
    time.sleep(2)
    while True:
        try:
            tail_events.append(drv.events.get(timeout=0.3))
        except queue.Empty:
            break
    report["prompt_reply"] = prompt_reply.get("result", prompt_reply.get("error"))

    # Every session/update the adapter forwarded — the raw steer events are
    # consumed by the adapter's ledger, so `targetTurnId`/`injectedMessageIds`
    # surface through the _session/steering result, not as update kinds.
    report["session_updates"] = [
        ((m.get("params") or {}).get("update") or {})
        for m in ([msg] if msg else []) + seen + tail_events
        if isinstance(m, dict)][:60]

    r = drv.call("session/cancel", {"sessionId": sid}, timeout=15)
    report["session/cancel"] = r.get("result", r.get("error"))
    drv.proc.stdin.close()
    drv.proc.terminate()
    try:
        drv.proc.wait(timeout=10)
        report["teardown"] = "terminated"
    except subprocess.TimeoutExpired:
        drv.proc.kill()
        report["teardown"] = "killed"
    report["stderr_tail"] = drv.stderr_lines[-20:]
    raw.close()

    # Backend-level evidence: distill the whitelist-only tee log into the
    # steer chain (subscribe coverage + command + queued + drained) and
    # cross-check it against the adapter's own _session/steering result.
    steer_fp = hashlib.sha256(STEER_TEXT.encode()).hexdigest()[:16]
    records, other_count, nonjson_count = [], 0, 0
    if os.path.isfile(tee_log):
        for line in open(tee_log, encoding="utf-8"):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("kind") == "other":
                other_count += 1
            elif rec.get("kind") == "nonjson":
                nonjson_count += 1
            else:
                records.append(rec)
    evidence = {
        "steer_text_sha256": steer_fp,
        "sendText": [r for r in records
                     if r.get("kind") == "v4/command.sendText"],
        "steerQueued": [r for r in records
                        if r.get("kind") == "turn.steerQueued"],
        "steerDrained": [r for r in records
                         if r.get("kind") == "turn.steerDrained"],
        "other_lines": other_count,
        "nonjson_lines": nonjson_count,
    }
    cmd = evidence["sendText"][-1] if evidence["sendText"] else {}
    q = evidence["steerQueued"][-1] if evidence["steerQueued"] else {}
    d = evidence["steerDrained"][-1] if evidence["steerDrained"] else {}
    result = report.get("steer_reply") or {}
    # The tee persists only SHA-256 fingerprints, so the adapter result's raw
    # ids are hashed with the same function before comparison.
    rid = {k: (hashlib.sha256(v.encode()).hexdigest()[:16]
               if isinstance(v, str) else None)
           for k, v in (("targetTurnId", result.get("targetTurnId")),
                        ("pendingInputId", result.get("pendingInputId")))}
    result_msg_hashes = {hashlib.sha256(m.encode()).hexdigest()[:16]
                         for m in (result.get("injectedMessageIds") or [])}
    evidence["cross_check"] = {
        "commandId_end_to_end": bool(
            cmd.get("commandId_sha256")
            and cmd.get("commandId_sha256") == q.get("commandId_sha256")
            and (cmd.get("commandId_sha256")
                 in (d.get("sourceCommandIds_sha256") or [])
                 or cmd.get("commandId_sha256")
                 in (d.get("queryIds_sha256") or []))),
        "same_turn_end_to_end": bool(
            cmd.get("expectedTurnId_sha256")
            and cmd.get("expectedTurnId_sha256")
            == q.get("targetTurnId_sha256") == d.get("targetTurnId_sha256")),
        "same_text_hash_end_to_end": bool(
            cmd.get("text_sha256") == steer_fp
            and steer_fp in (q.get("text_sha256s") or [])
            and steer_fp in (d.get("text_sha256s") or [])),
        "pending_id_admitted_then_drained": bool(
            q.get("pendingInputId_sha256")
            and q.get("pendingInputId_sha256")
            in (d.get("pendingInputIds_sha256") or [])),
        "adapter_result_matches": bool(
            rid["targetTurnId"]
            and rid["targetTurnId"] == d.get("targetTurnId_sha256")
            and rid["pendingInputId"]
            and rid["pendingInputId"] == q.get("pendingInputId_sha256")
            and result_msg_hashes
            <= set(d.get("injectedMessageIds_sha256") or [])),
    }
    with open(os.path.join(args.out, "backend-evidence.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"chain": evidence, "records": records}, fh,
                  indent=1, ensure_ascii=False)

    out = os.path.join(args.out, "report.json")
    json.dump(report, open(out, "w"), indent=2, default=str)
    # Defensive credential scan of everything we are about to keep — the ACP
    # wrapper log AND the whitelist-only tee/evidence artifacts.
    blob = json.dumps(report)
    for kept in ("raw-ndjson.jsonl", "backend-tee.jsonl",
                 "backend-evidence.json"):
        kept_path = os.path.join(args.out, kept)
        if os.path.isfile(kept_path):
            blob += open(kept_path).read()
    hits = [m for m in SECRET_KEYS.finditer(blob)]
    print(json.dumps({
        "sessionId": sid,
        "steer_outcome": (report.get("steer_reply") or {}).get("outcome"),
        "teardown": report.get("teardown"),
        "backend_chain": evidence.get("cross_check"),
        "secret_field_mentions_in_log": len(hits),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
