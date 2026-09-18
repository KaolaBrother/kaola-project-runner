#!/usr/bin/env python3
"""Issue #81 — isolated live probe: does ZCode 3.12.3 app-server --stdio expose
v4 native steering (guide) that a Runner adapter could consume?

Drives the REAL installed bundle directly over NDJSON stdio (the same channel
the Runner adapter uses), in a disposable git repo. No Runner production code
is used or modified; no credential is printed — the plan key is read from
~/.zcode/v2/config.json into memory only and registered for redaction.

Evidence legs:
  A. CAS setFollowupMode{guide} accepted, then mid-turn sendText ->
     turn.steerQueued{delivery:"guide"} + turn.steerDrained{injectedMessageIds}
     inside the SAME turn = injected.
  B. Mid-turn sendText{requestedDelivery:"queue"} -> queued, NOT drained into
     the running turn (queue, not injection).
  C. setFollowupMode WITHOUT baseRevision -> rejected (proto.* reasonCode), and
     sendText to a bogus sessionId -> proto.sessionNotFound = rejected leg.
Raw NDJSON + derived verdicts are written under --out (sanitized).
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


class Backend:
    """NDJSON stdio client for `zcode app-server --stdio`."""

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
        method = msg.get("method")
        params = msg.get("params") or {}
        if method == "interaction/requestProviderRuntimeHeaders":
            result = self.runtime_headers(params)
        else:
            self._send_raw({"id": msg["id"],
                            "error": {"code": -32601, "message": "probe: not implemented"}})
            return
        self._send_raw({"id": msg["id"], "result": result})

    def runtime_headers(self, params):
        # Answer the mandatory auth request for our coding-plan provider only.
        provider = params.get("providerId") or (
            (params.get("modelSelection") or {}).get("providerId"))
        if provider == ACCOUNT_PROVIDER_ID and self.api_key:
            return {"headersApplied": True, "requestAuth": {"apiKey": self.api_key}}
        return {"headersApplied": False,
                "errorMessage": f"probe cannot serve auth for {provider!r}"}

    api_key = None

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

    def drain_events(self, seconds, keep=None):
        """Collect notifications for `seconds`; return list."""
        end = time.time() + seconds
        out = []
        while time.time() < end:
            try:
                msg = self.events.get(timeout=max(0.05, end - time.time()))
            except queue.Empty:
                break
            out.append(msg)
            if keep and keep(msg):
                pass
        return out

    def wait_for(self, pred, timeout, desc=""):
        """Wait until a notification matching pred arrives; returns (msg, seen)."""
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
    """(type, payload) of a session/event notification, else (None, None)."""
    if msg.get("method") != "session/event":
        return None, None
    p = msg.get("params") or {}
    return p.get("type"), p.get("payload") or {}


def is_frame(msg):
    if msg.get("method") != "v4/conversation/frame":
        return None
    p = msg.get("params") or {}
    return p.get("frame") or {}


def load_plan_key():
    cfg = json.load(open(DESKTOP_CFG))
    providers = cfg.get("provider") or {}
    entry = providers.get(LEGACY_PROVIDER_ID) or {}
    key = ((entry.get("options") or {}).get("apiKey"))
    if not isinstance(key, str) or not key:
        raise SystemExit("probe: no enabled coding-plan apiKey in desktop registry")
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
    """Compact index of what the session emitted, for the evidence report."""
    out = []
    for m in events:
        t, p = sev(m)
        if t:
            entry = {"session_event": t}
            for k in ("targetTurnId", "delivery", "queueLength", "pendingInputId",
                      "injectedMessageIds", "turnNumber", "inputPreview",
                      "reasonCode", "resultType", "turnPhase", "message", "response"):
                if isinstance(p, dict) and k in p:
                    v = p[k]
                    entry[k] = (v[:160] + "…") if isinstance(v, str) and len(v) > 160 else v
            if isinstance(p, dict) and isinstance(p.get("error"), dict):
                entry["error"] = {k: p["error"].get(k) for k in ("message", "code")}
            if isinstance(p, dict) and isinstance(p.get("drainedInputs"), list):
                entry["drainedInputs"] = [
                    {k: d.get(k) for k in ("pendingInputId", "messageId", "delivery", "text")}
                    for d in p["drainedInputs"]]
            out.append(entry)
            continue
        fr = is_frame(m)
        if fr is not None:
            pl = fr.get("payload") or {}
            entry = {"v4_frame": (m.get("params") or {}).get("topic"),
                     "kind": pl.get("kind")}
            snap = pl.get("snapshot")
            if isinstance(snap, dict):
                entry["snapshot_revision"] = snap.get("revision")
                entry["snapshot_logEpoch"] = snap.get("logEpoch")
            ev = pl.get("event") or pl.get("updates") or pl.get("delta")
            if ev is not None:
                entry["payload_keys"] = list(pl.keys())
            out.append(entry)
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

    # --- bootstrap -------------------------------------------------------
    report["bootstrap"] = {}
    r = be.call("provider/updateAccountConfig", build_account_snapshot(), timeout=30)
    report["bootstrap"]["updateAccountConfig"] = r.get("result", r.get("error"))

    r = be.call("session/create", {
        "workspace": {"workspacePath": args.repo, "workspaceKey": args.repo},
        "mode": "yolo"}, timeout=60)
    session = (r.get("result") or {}).get("session") or {}
    sid = session.get("sessionId")
    report["bootstrap"]["session/create"] = {"sessionId": sid, "error": r.get("error")}
    if not sid:
        report["fatal"] = "session/create failed"
        json.dump(report, open(os.path.join(args.out, "report.json"), "w"), indent=2)
        sys.exit(2)

    r = be.call("session/setModel", {
        "sessionId": sid,
        "model": {"providerId": ACCOUNT_PROVIDER_ID, "modelId": MODEL_ID,
                  "options": {"reasoningLevel": REASONING}},
        "persistAsWorkspaceLastUsed": False}, timeout=30)
    report["bootstrap"]["session/setModel"] = r.get("result", r.get("error"))

    r = be.call("session/subscribe", {
        "sessionId": sid, "deliveryKind": "desktop-continuous",
        "includeSnapshot": False, "afterSeq": 0}, timeout=30)
    report["bootstrap"]["session/subscribe"] = r.get("result", r.get("error"))

    conn = f"i81-{uuid.uuid4()}"
    r = be.call("v4/conversation/subscribe", {
        "topic": f"conversation/{sid}", "connectionId": conn,
        "clientMode": "desktop-continuous"}, timeout=30)
    report["bootstrap"]["v4/conversation/subscribe"] = r.get("result", r.get("error"))

    # wait for the initial snapshot frame -> revision + logEpoch
    revision, log_epoch = 0, None
    deadline = time.time() + 8
    snapshot_frames = []
    while time.time() < deadline:
        msg, _ = be.wait_for(lambda m: is_frame(m) is not None, 2)
        if not msg:
            break
        fr = is_frame(msg)
        snapshot_frames.append(msg)
        snap = (fr.get("payload") or {}).get("snapshot") or {}
        if isinstance(snap.get("revision"), int):
            revision = snap["revision"]
            log_epoch = snap.get("logEpoch") or log_epoch
            if (fr.get("payload") or {}).get("kind") == "snapshot":
                break
    report["bootstrap"]["v4_snapshot"] = {"revision": revision, "logEpoch": log_epoch}

    def v4command(ctype, payload, sid_=None, base_rev=None, base_epoch=None):
        env = {"commandId": f"i81-{ctype}-{be.next_id}-{uuid.uuid4().hex[:8]}",
               "clientId": "i81-probe",
               "sessionId": sid_ if sid_ is not None else sid,
               "type": ctype, "payload": payload, "issuedAt": int(time.time() * 1000)}
        if base_rev is not None:
            env["baseRevision"] = base_rev
        if base_epoch is not None:
            env["baseLogEpoch"] = base_epoch
        return be.call("v4/command", env, timeout=60)

    # --- Leg C first (cheap rejections, no model needed) ------------------
    legc = {}
    r = v4command("setFollowupMode", {"mode": "guide"})  # NO baseRevision
    legc["setFollowupMode_no_baseRevision"] = r.get("result", r.get("error"))
    r = v4command("sendText", {"text": "bogus"}, sid_="sess_does_not_exist")
    legc["sendText_bogus_session"] = r.get("result", r.get("error"))
    report["legs"]["C_rejections"] = legc

    # --- Leg A: CAS guide + mid-turn steer --------------------------------
    lega = {}
    prompt1 = ("Use the shell tool to run this exact loop: "
               "for i in 1 2 3 4 5 6 7 8 9 10 11 12; do echo step-$i; sleep 3; done. "
               "When the loop finishes, reply with exactly: DONE-FIRST-81. "
               "Do not reply before the loop finishes.")
    r = be.call("session/send", {"sessionId": sid, "content": prompt1}, timeout=30)
    lega["session/send"] = r.get("result", r.get("error"))

    msg, _ = be.wait_for(lambda m: sev(m)[0] == "turn.started", 45, "turn.started")
    if not msg:
        lega["fatal"] = "turn never started"
        report["legs"]["A_guide"] = lega
        json.dump(report, open(os.path.join(args.out, "report.json"), "w"), indent=2)
        sys.exit(3)
    lega["turn_started"] = sev(msg)[1]
    turn1_id = lega["turn_started"].get("targetId") or lega["turn_started"].get("turnId")

    # let the turn demonstrably run (~2 shell steps)
    be.drain_events(7)

    # CAS setFollowupMode -> guide (retry on stale like upstream)
    cas_attempts = []
    for attempt in range(3):
        r = v4command("setFollowupMode", {"mode": "guide"},
                      base_rev=revision, base_epoch=log_epoch)
        ack = r.get("result", r.get("error"))
        cas_attempts.append({"attempt": attempt, "baseRevision": revision,
                             "baseLogEpoch": log_epoch, "ack": ack})
        if not isinstance(ack, dict) or ack.get("status") != "stale":
            break
        be.drain_events(1.5)
    lega["setFollowupMode_cas"] = cas_attempts

    # mid-turn steer text (no requestedDelivery: guide mode routes it)
    steer_text = ("Stop the loop immediately and reply with exactly: "
                  "STEERED-81-OK")
    r = v4command("sendText", {"text": steer_text})
    lega["steer_sendText_ack"] = r.get("result", r.get("error"))

    # observe until the turn completes (bounded)
    msg, seen1 = be.wait_for(
        lambda m: sev(m)[0] in ("turn.completed", "turn.failed", "turn.terminal"),
        150, "turn end")
    lega["turn_end"] = sev(msg) if msg else None
    lega["event_summary"] = summarize_events(seen1)
    be.drain_events(1.0)
    report["legs"]["A_guide"] = lega

    # --- Leg B: mid-turn queue delivery (control) --------------------------
    legb = {}
    prompt2 = ("Use the shell tool to run this exact loop: "
               "for i in 1 2 3 4 5 6 7 8; do echo loopb-$i; sleep 3; done. "
               "When the loop finishes, reply with exactly: DONE-SECOND-81. "
               "Do not reply before the loop finishes.")
    r = be.call("session/send", {"sessionId": sid, "content": prompt2}, timeout=30)
    legb["session/send"] = r.get("result", r.get("error"))
    msg, _ = be.wait_for(lambda m: sev(m)[0] == "turn.started", 45, "turn2.started")
    if msg:
        legb["turn2_started"] = sev(msg)[1]
        be.drain_events(5)
        r = v4command("sendText", {"text": "Reply with exactly: QUEUED-81-OK",
                                   "requestedDelivery": "queue"})
        legb["queue_sendText_ack"] = r.get("result", r.get("error"))
        # watch the rest of this turn + the start of the next
        msg, seen2 = be.wait_for(
            lambda m: sev(m)[0] in ("turn.completed", "turn.failed", "turn.terminal"),
            150, "turn2 end")
        legb["turn2_end"] = sev(msg) if msg else None
        # does the queued input start a NEW turn?
        msg, seen3 = be.wait_for(
            lambda m: sev(m)[0] in ("turn.started",), 30, "turn3.started")
        legb["queued_input_next_turn"] = sev(msg) if msg else None
        if msg:
            msg2, seen4 = be.wait_for(
                lambda m: sev(m)[0] in ("turn.completed", "turn.failed", "turn.terminal"),
                120, "turn3 end")
            legb["turn3_end"] = sev(msg2) if msg2 else None
            seen2 = seen2 + seen3 + seen4
        legb["event_summary"] = summarize_events(seen2)
    else:
        legb["fatal"] = "second turn never started"
    be.drain_events(1.0)
    report["legs"]["B_queue"] = legb

    # --- teardown ----------------------------------------------------------
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
    print(json.dumps({"sessionId": sid, "out": args.out,
                      "legs": {k: list(v.keys()) for k, v in report["legs"].items()}},
                     indent=2))


if __name__ == "__main__":
    main()
