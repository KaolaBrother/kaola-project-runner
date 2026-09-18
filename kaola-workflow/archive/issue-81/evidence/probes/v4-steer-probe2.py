#!/usr/bin/env python3
"""Issue #81 — live probe v2: prove/refute v4 GUIDE injection on ZCode 3.12.3.

Run 1 established: v4 channel live on the same stdio pipe, queue delivery
works and does NOT inject, rejections are clean (proto.invalidPayload /
proto.sessionNotFound / proto.staleRevision). Its CAS failed only because the
probe sent baseRevision:0 — the snapshot itself is revision 0 at subscribe;
the live revision climbs via state.updated deltas and *Revision fields in v3
results. This run tracks revisions properly and tests BOTH guide entries:

  Leg G1: mid-turn sendText{requestedDelivery:"guide"} (no session mutation).
  Leg G2: CAS setFollowupMode{guide, baseRevision, baseLogEpoch} then plain
          mid-turn sendText (the upstream zcode-provider path).
  Leg C : rejections re-verified in this raw log.

Verdict evidence required (not string matching): turn.steerQueued
{delivery:"guide"} followed by turn.steerDrained {targetTurnId == running turn,
injectedMessageIds} while that turn is active, then the turn's own
turn.completed response showing the steer instruction was obeyed.
"""

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid

ENTRY = "/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs"
NODE = "/opt/homebrew/bin/node"
BUILTIN_TABLE = "/Applications/ZCode.app/Contents/Resources/config/provider/zcode-builtin.json"
HOME = os.environ.get("HOME", "")
PERSONAL_CFG = os.path.join(HOME, ".zcode", "v2", "provider_config.json")
DESKTOP_CFG = os.path.join(HOME, ".zcode", "v2", "config.json")
PLAN_CACHE = os.path.join(HOME, ".zcode", "v2", "coding-plan-cache.json")

LEGACY_PROVIDER_ID = "builtin:bigmodel-coding-plan"
ACCOUNT_PROVIDER_ID = "account:bigmodel-individual-coding-plan"
MODEL_ID = "GLM-5.3-Flash"
REASONING = "low"

SECRET_VALUES = set()


def register_secret(v):
    if isinstance(v, str) and len(v) >= 8:
        SECRET_VALUES.add(v)


def redact(x):
    if isinstance(x, str):
        for s in SECRET_VALUES:
            if s in x:
                x = x.replace(s, "<redacted-credential>")
        return x
    if isinstance(x, dict):
        return {k: redact(v) for k, v in x.items()}
    if isinstance(x, list):
        return [redact(v) for v in x]
    return x


def scan_revision(obj, seen):
    """Pull any *revision* counter out of a result/notification payload."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("revision", "stateRevision", "revisionAtDecision",
                         "snapshotRevision") and isinstance(v, int):
                    found.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    if found:
        seen[0] = max(seen[0], max(found))


class Backend:
    def __init__(self, cwd, raw_log):
        env = {k: os.environ[k] for k in
               ("HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "USER",
                "LOGNAME", "SHELL", "TZ", "TERM") if k in os.environ}
        env["ELECTRON_RUN_AS_NODE"] = "1"
        env["ZCODE_BUILTIN_PROVIDER_CONFIG_FILE"] = BUILTIN_TABLE
        env["ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"] = PERSONAL_CFG
        self.proc = subprocess.Popen(
            [NODE, ENTRY, "app-server", "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, cwd=cwd, env=env, text=True)
        self.next_id = 1
        self.pending = {}
        self.events = queue.Queue()
        self.raw = raw_log
        self.lock = threading.Lock()
        self.revision = [0]
        self.log_epoch = None
        self.api_key = None
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
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
            scan_revision(msg.get("result"), self.revision)
            scan_revision(msg.get("params"), self.revision)
            mid = msg.get("id")
            if mid is not None and ("result" in msg or "error" in msg):
                with self.lock:
                    waiter = self.pending.pop(str(mid), None)
                if waiter:
                    waiter.put(msg)
            elif msg.get("method"):
                if mid is not None and str(mid).startswith("server-"):
                    self._server_request(msg)
                else:
                    self.events.put(msg)

    def _server_request(self, msg):
        if msg.get("method") == "interaction/requestProviderRuntimeHeaders":
            p = msg.get("params") or {}
            provider = p.get("providerId") or (
                (p.get("modelSelection") or {}).get("providerId"))
            if provider == ACCOUNT_PROVIDER_ID and self.api_key:
                result = {"headersApplied": True,
                          "requestAuth": {"apiKey": self.api_key}}
            else:
                result = {"headersApplied": False,
                          "errorMessage": f"probe cannot serve auth for {provider!r}"}
            self._send_raw({"id": msg["id"], "result": result})
        else:
            self._send_raw({"id": msg["id"],
                            "error": {"code": -32601, "message": "probe: not implemented"}})

    def _send_raw(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        self._log({"sent": obj})

    def _log(self, obj):
        self.raw.write(json.dumps(redact(obj), ensure_ascii=False) + "\n")
        self.raw.flush()

    def call(self, method, params=None, timeout=60):
        rid = self.next_id
        self.next_id += 1
        waiter = queue.Queue()
        with self.lock:
            self.pending[str(rid)] = waiter
        self._send_raw({"id": rid, "method": method, "params": params or {}})
        try:
            return waiter.get(timeout=timeout)
        except queue.Empty:
            return {"id": rid, "error": {"code": "probe-timeout",
                                         "message": f"no reply to {method} in {timeout}s"}}

    def drain_events(self, seconds):
        end = time.time() + seconds
        out = []
        while time.time() < end:
            try:
                out.append(self.events.get(timeout=max(0.05, end - time.time())))
            except queue.Empty:
                break
        return out

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
    if msg.get("method") != "session/event":
        return None, None
    p = msg.get("params") or {}
    return p.get("type"), p.get("payload") or {}


def is_frame(msg):
    if msg.get("method") != "v4/conversation/frame":
        return None
    return (msg.get("params") or {}).get("frame")


def load_plan_key():
    cfg = json.load(open(DESKTOP_CFG))
    key = (((cfg.get("provider") or {}).get(LEGACY_PROVIDER_ID) or {})
           .get("options") or {}).get("apiKey")
    if not isinstance(key, str) or not key:
        raise SystemExit("probe: no enabled coding-plan apiKey")
    register_secret(key)
    return key


def build_account_snapshot():
    table = json.load(open(BUILTIN_TABLE))
    rules = [r for r in (table["config"]["providerConfigRules"].get("providerRules") or [])
             if (r.get("config") or {}).get("access", {}).get("type") == "zhipu-account"]
    entitled_builtin = set()
    try:
        cache = json.load(open(PLAN_CACHE))
        for pid, item in ((cache.get("entryStatus") or {}).get("items") or {}).items():
            if isinstance(item, dict) and item.get("status") == "available":
                entitled_builtin.add(pid)
    except (OSError, ValueError):
        pass
    cfg = json.load(open(DESKTOP_CFG))
    for pid, p in (cfg.get("provider") or {}).items():
        if pid.startswith("builtin:") and p.get("enabled") is True \
                and (p.get("options") or {}).get("apiKey"):
            entitled_builtin.add(pid)
    providers, states = {}, {}
    for r in rules:
        pid = r["providerId"]
        acc = r["config"]["access"]
        family, mode = acc.get("accountType"), acc.get("mode")
        legacy = f"builtin:{family}-{'coding-plan' if mode == 'individual-coding-plan' else mode}"
        entitled = legacy in entitled_builtin
        providers[pid] = {"builtinModelIds": r["config"].get("builtinModelIds"),
                          "access": {"type": "zhipu-account", "entitled": entitled}}
        states[pid] = {"availability": "available" if entitled else "unavailable",
                       "entitled": entitled, "current": entitled}
    resolved = os.path.realpath(BUILTIN_TABLE)
    digest = hashlib.sha256(resolved.encode()).hexdigest()
    return {"revision": f"account:probe:{int(time.time() * 1000)}",
            "basedOnZCodeBuiltinRevision": f"zcode-builtin:{table.get('revision', 0)}:{digest}",
            "providers": providers, "states": states}


def summarize_events(events):
    out = []
    for m in events:
        t, p = sev(m)
        if t:
            e = {"session_event": t}
            for k in ("targetTurnId", "delivery", "queueLength", "pendingInputId",
                      "pendingInputIds", "injectedMessageIds", "turnNumber",
                      "inputPreview", "reasonCode", "resultType", "turnPhase",
                      "response", "stateRevision"):
                if isinstance(p, dict) and k in p:
                    v = p[k]
                    e[k] = (v[:200] + "…") if isinstance(v, str) and len(v) > 200 else v
            if isinstance(p, dict) and isinstance(p.get("intent"), dict):
                e["intent_delivery"] = p["intent"].get("delivery")
                e["intent_admittedDelivery"] = p["intent"].get("admittedDelivery")
                e["intent_fallbackReasonCode"] = p["intent"].get("fallbackReasonCode")
            if isinstance(p, dict) and isinstance(p.get("drainedInputs"), list):
                e["drainedInputs"] = [
                    {k: d.get(k) for k in ("pendingInputId", "messageId", "delivery", "text")}
                    for d in p["drainedInputs"]]
            if isinstance(p, dict) and isinstance(p.get("error"), dict):
                e["error"] = {k: p["error"].get(k) for k in ("message", "code")}
            out.append(e)
            continue
        fr = is_frame(m)
        if fr is not None:
            pl = fr.get("payload") or {}
            e = {"v4_frame": (m.get("params") or {}).get("topic"), "kind": pl.get("kind")}
            snap = pl.get("snapshot")
            if isinstance(snap, dict):
                e["snapshot_revision"] = snap.get("revision")
                e["snapshot_logEpoch"] = snap.get("logEpoch")
            deltas = pl.get("deltas")
            if isinstance(deltas, list):
                e["delta_ops"] = [d.get("op") for d in deltas if isinstance(d, dict)]
                revs = [d.get("patch", {}).get("revision") for d in deltas
                        if isinstance(d, dict) and isinstance(d.get("patch"), dict)]
                e["delta_revisions"] = [r for r in revs if r is not None]
            out.append(e)
            continue
        out.append({"other_notification": m.get("method")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    raw = open(os.path.join(args.out, "raw-ndjson.jsonl"), "w", encoding="utf-8")
    report = {"legs": {}, "verdicts": {}}
    be = Backend(args.repo, raw)
    be.api_key = load_plan_key()

    report["bootstrap"] = {}
    r = be.call("provider/updateAccountConfig", build_account_snapshot(), timeout=30)
    report["bootstrap"]["updateAccountConfig"] = r.get("result", r.get("error"))
    r = be.call("session/create", {
        "workspace": {"workspacePath": args.repo, "workspaceKey": args.repo},
        "mode": "yolo"}, timeout=60)
    sid = ((r.get("result") or {}).get("session") or {}).get("sessionId")
    report["bootstrap"]["session/create"] = {"sessionId": sid, "error": r.get("error")}
    if not sid:
        json.dump(report, open(os.path.join(args.out, "report.json"), "w"), indent=2)
        sys.exit(2)
    r = be.call("session/setModel", {
        "sessionId": sid,
        "model": {"providerId": ACCOUNT_PROVIDER_ID, "modelId": MODEL_ID,
                  "options": {"reasoningLevel": REASONING}},
        "persistAsWorkspaceLastUsed": False}, timeout=30)
    report["bootstrap"]["session/setModel"] = {
        "ok": "error" not in r, "stateRevision": be.revision[0]}
    r = be.call("session/subscribe", {
        "sessionId": sid, "deliveryKind": "desktop-continuous",
        "includeSnapshot": False, "afterSeq": 0}, timeout=30)
    report["bootstrap"]["session/subscribe"] = {"ok": "error" not in r}
    conn = f"i81-{uuid.uuid4()}"
    r = be.call("v4/conversation/subscribe", {
        "topic": f"conversation/{sid}", "connectionId": conn,
        "clientMode": "desktop-continuous"}, timeout=30)
    ack = (r.get("result") or {}).get("ack") or {}
    report["bootstrap"]["v4/conversation/subscribe"] = ack
    be.log_epoch = ack.get("logEpoch")
    be.drain_events(1.5)  # let the snapshot frame land

    def v4command(ctype, payload, sid_=None, base_rev=None, base_epoch=None):
        env = {"commandId": f"i81-{ctype}-{be.next_id}-{uuid.uuid4().hex[:8]}",
               "clientId": "i81-probe",
               "sessionId": sid_ if sid_ is not None else sid,
               "type": ctype, "payload": payload,
               "issuedAt": int(time.time() * 1000)}
        if base_rev is not None:
            env["baseRevision"] = base_rev
        if base_epoch is not None:
            env["baseLogEpoch"] = base_epoch
        return be.call("v4/command", env, timeout=60)

    # --- Leg C: rejections -------------------------------------------------
    legc = {}
    r = v4command("setFollowupMode", {"mode": "guide"})
    legc["setFollowupMode_no_cas"] = r.get("result", r.get("error"))
    r = v4command("sendText", {"text": "bogus"}, sid_="sess_does_not_exist")
    legc["sendText_bogus_session"] = r.get("result", r.get("error"))
    report["legs"]["C_rejections"] = legc

    def run_turn(prompt):
        be.call("session/send", {"sessionId": sid, "content": prompt}, timeout=30)
        msg, _ = be.wait_for(lambda m: sev(m)[0] == "turn.started", 45)
        return sev(msg)[1] if msg else None

    def observe_turn_end(timeout=150):
        msg, seen = be.wait_for(
            lambda m: sev(m)[0] in ("turn.completed", "turn.failed", "turn.terminal"),
            timeout)
        return (sev(msg) if msg else None), seen

    # --- Turn 1 + Leg G1: per-command requestedDelivery:"guide" -------------
    g1 = {}
    t1 = run_turn("Use the shell tool to run this exact loop: "
                  "for i in 1 2 3 4 5 6 7 8 9 10; do echo g1step-$i; sleep 4; done. "
                  "When the loop finishes, reply with exactly: DONE-TURN1-81. "
                  "Do not reply before the loop finishes.")
    g1["turn_started"] = t1
    if not t1:
        g1["fatal"] = "turn1 never started"
        report["legs"]["G1_requestedDelivery_guide"] = g1
        json.dump(report, open(os.path.join(args.out, "report.json"), "w"), indent=2)
        sys.exit(3)
    be.drain_events(8)
    g1["revision_before_steer"] = be.revision[0]
    r = v4command("sendText", {"text": "Abandon the loop now and reply with exactly: "
                                     "STEERED-G1-81-OK",
                               "requestedDelivery": "guide"})
    g1["steer_sendText_ack"] = r.get("result", r.get("error"))
    end, seen1 = observe_turn_end(160)
    g1["turn_end"] = end
    g1["event_summary"] = summarize_events(seen1)
    be.drain_events(1.5)
    report["legs"]["G1_requestedDelivery_guide"] = g1

    # --- Turn 2 + Leg G2: CAS setFollowupMode then plain sendText -----------
    g2 = {}
    t2 = run_turn("Use the shell tool to run this exact loop: "
                  "for i in 1 2 3 4 5 6 7 8 9 10; do echo g2step-$i; sleep 4; done. "
                  "When the loop finishes, reply with exactly: DONE-TURN2-81. "
                  "Do not reply before the loop finishes.")
    g2["turn_started"] = t2
    if t2:
        be.drain_events(6)
        cas = []
        for attempt in range(4):
            r = v4command("setFollowupMode", {"mode": "guide"},
                          base_rev=be.revision[0], base_epoch=be.log_epoch)
            ack = r.get("result", r.get("error"))
            cas.append({"attempt": attempt, "baseRevision": be.revision[0],
                        "baseLogEpoch": be.log_epoch, "ack": ack})
            if not isinstance(ack, dict) or ack.get("status") != "stale":
                break
            # revision moved under us; wait a beat and retry with the reported one
            rad = ack.get("revisionAtDecision")
            if isinstance(rad, int):
                be.revision[0] = max(be.revision[0], rad)
            be.drain_events(1.0)
        g2["setFollowupMode_cas"] = cas
        r = v4command("sendText", {"text": "Abandon the loop now and reply with "
                                         "exactly: STEERED-G2-81-OK"})
        g2["steer_sendText_ack"] = r.get("result", r.get("error"))
        end, seen2 = observe_turn_end(160)
        g2["turn_end"] = end
        g2["event_summary"] = summarize_events(seen2)
        be.drain_events(1.5)
    else:
        g2["fatal"] = "turn2 never started"
    report["legs"]["G2_cas_guide"] = g2

    # --- teardown -----------------------------------------------------------
    r = be.call("session/close", {"sessionId": sid}, timeout=20)
    report["teardown"] = {"session/close": r.get("result", r.get("error"))}
    be.proc.terminate()
    try:
        be.proc.wait(timeout=10)
        report["teardown"]["proc"] = "terminated"
    except subprocess.TimeoutExpired:
        be.proc.kill()
        report["teardown"]["proc"] = "killed"
    raw.close()
    json.dump(report, open(os.path.join(args.out, "report.json"), "w"),
              indent=2, default=str)
    print(json.dumps({"sessionId": sid, "out": args.out}, indent=2))


if __name__ == "__main__":
    main()
