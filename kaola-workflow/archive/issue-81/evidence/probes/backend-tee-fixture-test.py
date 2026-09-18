#!/usr/bin/env python3
"""Issue #81: fixture proof that backend-tee.py's persisted evidence is a
strict whitelist — ID hashes, finite enums, bounded counts, text hashes —
and that fake secrets planted in EVERY would-be field (and in stderr-like
input) can never appear in persisted JSON.

Asserts:
  1. fake secrets / tokens / raw ids / raw text NEVER appear in any record;
  2. non-JSON and unknown lines reduce to {kind, bytes} — count-only;
  3. whitelisted records carry ONLY the finite field set, all IDs hashed;
  4. the sendText/steerQueued/steerDrained chain still binds same-turn,
     same-text, same-command end to end via stable SHA-256.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "backend_tee", os.path.join(HERE, "backend-tee.py"))
tee = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tee)

STEER_TEXT = "Abandon everything and reply with exactly: STEERED-81-FIXTURE"
FAKE_SECRET = "sk-FAKESECRET-DO-NOT-LEAK-0123456789abcdef"
FAKE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.FAKE.PAYLOAD-SIGNATURE-0000"
FAKE_BEARER = "Bearer sk-live-abc123def456ghi789"
TURN = "turn_fixture_aaa111"
CMD = "kpr-steer-fixture01"
PENDING = "queue_kpr-steer-fixture01"
MSG = "msg_fixture_injected1"


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


failures = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS" if cond else "FAIL"), name, detail)
    if not cond:
        failures.append(name)


# --- adversarial lines: a fake secret planted in EVERY would-be field -----

lines = {
    # Account-shaped JSON carrying credential material — count-only.
    "secret_json": json.dumps({
        "id": 3, "method": "session/create",
        "params": {"apiKey": {"source": "inline", "value": FAKE_SECRET},
                   "authorization": FAKE_BEARER,
                   "credential": "nested-" + FAKE_SECRET}}),
    # A v4 command RESPONSE — not whitelisted, so secrets inside reduce.
    "ack_with_secret": json.dumps({
        "id": 6, "result": {"status": "accepted",
                            "inputId": FAKE_SECRET, "token": FAKE_TOKEN}}),
    # A stderr-shaped line (what a noisy backend would print) with a secret.
    "stderr_like": (f"[app-server] ERROR auth failed for {FAKE_SECRET} "
                    f"token={FAKE_TOKEN} retrying"),
    # A non-JSON blob with a secret.
    "nonjson_secret": f"<<<raw backend blob {FAKE_SECRET} not json>>>",
    # sendText with secrets planted in EVERY id field + an unknown field.
    "cmd": json.dumps({
        "id": 6, "method": "v4/command",
        "params": {"commandId": CMD, "clientId": "kaola-zcode-acp",
                   "sessionId": FAKE_SECRET, "type": "sendText",
                   "issuedAt": 1789766000000,
                   "apiKey": FAKE_SECRET,
                   "payload": {"text": STEER_TEXT,
                               "requestedDelivery": "guide",
                               "expectedTurnId": TURN,
                               "secretField": FAKE_TOKEN}}}),
    # steerQueued with secrets in every id slot + unknown fields.
    "queued": json.dumps({
        "method": "session/event",
        "params": {"sessionId": "sess_fixture", "seq": 41,
                   "type": "turn.steerQueued",
                   "payload": {
                       "inputId": CMD, "queryId": FAKE_SECRET,
                       "pendingInputId": PENDING,
                       "input": STEER_TEXT, "inputPreview": STEER_TEXT,
                       "inputSize": len(STEER_TEXT),
                       "targetTurnId": TURN, "queueLength": 1,
                       "delivery": "guide",
                       "authHeader": FAKE_BEARER,
                       "intent": {"sourceCommandId": CMD,
                                  "queueItemId": FAKE_SECRET,
                                  "clientId": "kaola-zcode-acp",
                                  "kind": "sendText", "text": STEER_TEXT,
                                  "requestedDelivery": "guide",
                                  "admittedDelivery": "guide",
                                  "unexpectedField": FAKE_SECRET}}}}),
    # steerDrained with secrets in every id slot + unknown fields.
    "drained": json.dumps({
        "method": "session/event",
        "params": {"sessionId": "sess_fixture", "seq": 87,
                   "type": "turn.steerDrained",
                   "payload": {
                       "injectedMessageIds": [MSG, FAKE_SECRET],
                       "pendingInputIds": [PENDING, FAKE_TOKEN],
                       "queryIds": [CMD, FAKE_SECRET],
                       "targetTurnId": TURN,
                       "drainedInputs": [{
                           "messageId": MSG, "pendingInputId": PENDING,
                           "text": STEER_TEXT, "delivery": "guide",
                           "secretId": FAKE_TOKEN,
                           "intent": {"sourceCommandId": CMD,
                                      "text": STEER_TEXT,
                                      "password": FAKE_SECRET}}],
                       "accountBlob": FAKE_TOKEN}}}),
}

recs = {
    name: tee.summarize("out" if name == "cmd" else "in", line)
    for name, line in lines.items()
}

# --- 1. no secret / raw text / raw id anywhere in ANY record ---------------

everything = json.dumps(list(recs.values()), ensure_ascii=False)
for name, marker in [
        ("fake secret", FAKE_SECRET), ("fake token", FAKE_TOKEN),
        ("fake bearer", FAKE_BEARER), ("steer text", STEER_TEXT),
        ("raw turn id", TURN), ("raw command id", CMD),
        ("raw pending id", PENDING), ("raw message id", MSG)]:
    check(f"no {name} in any record", marker not in everything)
check("no unexpectedField/secretField/accountBlob keys",
      all(k not in everything for k in
          ("unexpectedField", "secretField", "accountBlob",
           "apiKey", "authorization", "credential", "authHeader",
           "password", "secretId", "queueItemId", "sessionId",
           "clientId", "inputSize", "queueLength", '"seq":', '"id":')))

# --- 2. reduction kinds: count-only, never content -------------------------

for name, want in (("secret_json", "other"), ("ack_with_secret", "other"),
                   ("stderr_like", "nonjson"), ("nonjson_secret", "nonjson")):
    rec = recs[name]
    check(f"{name} -> {want}", rec["kind"] == want)
    check(f"{name} carries only dir/kind/bytes",
          set(rec) == {"dir", "kind", "bytes"}, str(sorted(rec)))
    check(f"{name} bytes is a bounded count",
          isinstance(rec["bytes"], int) and rec["bytes"] > 0)

# --- 3. whitelisted fields only, all ids hashed ----------------------------

cmd = recs["cmd"]
check("sendText kind", cmd["kind"] == "v4/command.sendText")
check("sendText fields", set(cmd) == {
    "dir", "kind", "commandId_sha256", "expectedTurnId_sha256",
    "requestedDelivery", "text_sha256"}, str(sorted(cmd)))
check("sendText commandId hash", cmd["commandId_sha256"] == sha(CMD))
check("sendText expectedTurnId hash",
      cmd["expectedTurnId_sha256"] == sha(TURN))
check("sendText requestedDelivery enum", cmd["requestedDelivery"] == "guide")
check("sendText text hash", cmd["text_sha256"] == sha(STEER_TEXT))

EVENT_FIELDS = {
    "dir", "kind", "targetTurnId_sha256", "commandId_sha256",
    "sourceCommandIds_sha256", "queryIds_sha256", "pendingInputId_sha256",
    "pendingInputIds_sha256", "injectedMessageIds_sha256", "delivery",
    "admittedDelivery", "text_sha256s"}

q = recs["queued"]
check("queued kind", q["kind"] == "turn.steerQueued")
check("queued fields", set(q) == EVENT_FIELDS, str(sorted(q)))
check("queued commandId hash correlates",
      q["commandId_sha256"] == sha(CMD))
check("queued targetTurnId hash", q["targetTurnId_sha256"] == sha(TURN))
check("queued pendingInputId hash",
      q["pendingInputId_sha256"] == sha(PENDING))
check("queued delivery enum", q["delivery"] == "guide")
check("queued admittedDelivery enum", q["admittedDelivery"] == "guide")
check("queued carries the steer text hash",
      q["text_sha256s"] == [sha(STEER_TEXT)])

d = recs["drained"]
check("drained kind", d["kind"] == "turn.steerDrained")
check("drained fields", set(d) == EVENT_FIELDS, str(sorted(d)))
check("drained targetTurnId hash", d["targetTurnId_sha256"] == sha(TURN))
check("drained sourceCommandIds hashes correlate",
      d["sourceCommandIds_sha256"] == [sha(CMD)])
check("drained queryIds hashes correlate",
      sha(CMD) in (d["queryIds_sha256"] or []))
check("drained injectedMessageIds are hashes only",
      set(d["injectedMessageIds_sha256"]) == {sha(MSG), sha(FAKE_SECRET)})
check("drained pendingInputIds are hashes only",
      set(d["pendingInputIds_sha256"]) == {sha(PENDING), sha(FAKE_TOKEN)})
check("drained carries the steer text hash",
      d["text_sha256s"] == [sha(STEER_TEXT)])

# --- 4. the chain binds same-turn same-text same-command by hash -----------

check("chain: same commandId hash end-to-end",
      cmd["commandId_sha256"] == q["commandId_sha256"] == sha(CMD)
      and sha(CMD) in d["sourceCommandIds_sha256"])
check("chain: expectedTurn == queued turn == drained turn (hashes)",
      cmd["expectedTurnId_sha256"] == q["targetTurnId_sha256"]
      == d["targetTurnId_sha256"] == sha(TURN))
check("chain: same text hash end-to-end",
      cmd["text_sha256"] == q["text_sha256s"][0] == d["text_sha256s"][0])
check("chain: pending id admitted then drained (hashes)",
      q["pendingInputId_sha256"] in d["pendingInputIds_sha256"])

print()
if failures:
    print(f"{len(failures)} FAILURES")
    sys.exit(1)
print("ALL FIXTURE CHECKS PASS — persisted evidence is hash-only whitelist "
      "and the steer chain binds commandId + turn + text-hash end to end.")
