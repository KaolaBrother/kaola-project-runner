# Issue #81 — Mission 4: live v4 steering verification on the real ZCode 3.12.3

Date: 2026-09-19. Machine: this Mac. Desktop ZCode **3.12.3** (build 3.12.3.7463,
`dev.zcode.app`), bundled CLI reports 0.16.5. Entry
`/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`, node
`/opt/homebrew/bin/node`, spawned as `node <entry> app-server --stdio` — the
same NDJSON channel the Runner adapter already drives.

Two isolated disposable Git repos, two app-server processes, both created and
stopped by this run: `/tmp/kpr-i81-live/repo` (`git init`, fixture `15a75f3`,
session `sess_65701998-…`) and `/tmp/kpr-i81-live2/repo` (session
`sess_ea58ef9a-…`). Not this repository, not any user project, not the #79 test
session. No global ZCode config was modified, no existing ZCode session was
touched, no credential was copied/decrypted/printed (leak check below).

Probe code: `evidence/probes/v4-steer-probe.py` (run 1), `v4-steer-probe2.py`
(run 2). Raw NDJSON: `evidence/live/raw-ndjson.jsonl`,
`evidence/live2/raw-ndjson.jsonl`; derived reports: `report.json` beside each.

## VERDICT: native v4 mid-turn steering is REAL on 3.12.3 — both entries work

| Leg | Path | Evidence | Outcome |
|---|---|---|---|
| G1 | per-command `sendText{requestedDelivery:"guide"}` — **no session mutation** | `turn.steerQueued{delivery:"guide"}→turn.steerDrained{injectedMessageIds}` on the SAME `targetTurnId`; turn completed `STEERED-G1-81-OK` | **injected** |
| G2 | CAS `setFollowupMode{guide}` then plain `sendText` (upstream path) | CAS `{status:"accepted"}` first try at correct `baseRevision`; same steer event pair; turn completed `STEERED-G2-81-OK` | **injected** |
| B (run 1) | mid-turn `sendText{requestedDelivery:"queue"}` | `turn.steerQueued{delivery:"queue", intent.admittedDelivery:"queue"}`; NO `steerDrained`; turn completed `DONE-SECOND-81` | **queued, not injected** |
| A-accidental (run 1) | steer sendText while followupMode=queue (CAS had failed) | `turn.steerQueued{delivery:"queue"}`; no drain; turn completed `DONE-FIRST-81` | **queued, not injected** |
| C | `setFollowupMode` without CAS fields; `sendText` to bogus session | `{status:"rejected", reasonCode:"proto.invalidPayload"}` / `"proto.sessionNotFound"` | **rejected** |

## The injected leg, raw

`turn.steerQueued` (session/event, seq 5):

```json
{"targetTurnId":"turn_a3774f10-f83d-4a4f-b114-d819cf98c613","delivery":"guide",
 "queueLength":1,"pendingInputId":"queue_i81-sendText-9-7c1b2233",
 "inputPreview":"Abandon the loop now and reply with exactly: STEERED-G1-81-OK",
 "intent":{…,"admittedDelivery":"guide"}}
```

`turn.steerDrained` (session/event, seq 57 — same `targetTurnId`):

```json
{"injectedMessageIds":["msg_mu76tmoz_a49f9ccb-222f-4b37-ab1b-8602897a2218"],
 "pendingInputIds":["queue_i81-sendText-9-7c1b2233"],
 "drainedInputs":[{"pendingInputId":"queue_i81-sendText-9-7c1b2233",
   "messageId":"msg_mu76tmoz_…","text":"Abandon the loop now and reply with exactly: STEERED-G1-81-OK",
   "delivery":"guide",
   "intent":{…,"requestedDelivery":"guide","admittedDelivery":"guide","queuePosition":0}}]}
```

`turn.completed` for that same turn:

```json
{"response":"STEERED-G1-81-OK","toolCallCount":1,"duration":65910,"resultType":"success"}
```

The running turn abandoned its 10-step shell loop and obeyed the steer — the
instruction was consumed **inside** the turn, not queued behind it. The G2 leg
repeats the same chain through the CAS path (`turn_530e207d`, injected
`msg_mu76v2d1`, response `STEERED-G2-81-OK`).

## The trap, measured — the sendText result LIES about delivery

Every steer sendText ack returned:

```json
{"commandId":"…","status":"accepted","revisionAtDecision":N,
 "result":{"type":"inputAccepted","delivery":"queue","inputId":"…"}}
```

— `"delivery":"queue"` even when the admitted delivery was `"guide"`. The
bundle reading explains why (`zIs` maps `admission.kind==="queued"` →
`"queue"`), and the live runs prove it: the result field alone cannot
distinguish guide-queued from plain-queued. **The truthful fields are the
events:** `turn.steerQueued.delivery` / `intent.admittedDelivery` /
`intent.fallbackReasonCode`, and `turn.steerDrained.injectedMessageIds` +
`targetTurnId`. A Runner implementation that reports `injected` from the
command ack would be a false positive — exactly what the issue forbids.

## Receipt-grade outcomes, mapped to the #65 vocabulary

- **injected**: `v4/command` ack `status:"accepted"` + `turn.steerQueued`
  `{delivery:"guide", targetTurnId:T}` + `turn.steerDrained`
  `{targetTurnId:T, injectedMessageIds:[…]}` while `T` is the active turn.
  Confirmation level: **agent-confirmed** — the runtime itself reports the
  injection, stronger than Codex's `injected` or Claude's `written`.
- **queued (not consumed)**: `turn.steerQueued{delivery:"queue"}` /
  `intent.admittedDelivery:"queue"`, no `steerDrained` into the active turn;
  input persists as a queue item for a later turn. Guide can also fall back:
  `intent.admittedDelivery:"queue"` + `fallbackReasonCode` (bundle:
  `guide.attachmentsUnsupported`; upstream README: not steerable / queue
  already non-empty).
- **rejected**: ack `status:"rejected"|"stale"` with `reasonCode`
  (`proto.invalidPayload`, `proto.sessionNotFound`, `proto.missingBaseRevision`,
  `proto.staleRevision`, `proto.staleLogEpoch`, `fault.command.inputRejected`,
  `guard.stopTargetChanged`); also steer-level rejects (`turn_not_steerable`,
  `expected_turn_mismatch`, `empty_input`, `input_too_large`).
- **unknown**: no ack / no events / lost reply — the existing holder mapping
  already covers this; never resend.

## CAS and revision facts (live)

- `setFollowupMode` is an `i4t` CAS command: needs **both** `baseRevision` and
  `baseLogEpoch` (`"CAS commands require baseRevision and baseLogEpoch"`).
- Sources of the current revision, all observed live: `session/send` /
  `session/setModel` results (`stateRevision`), `session.updated` session
  events, v4 frame deltas `patch.revision`, and `revisionAtDecision` in any
  command ack. Initial `v4/conversation/subscribe` snapshot carries
  `revision:0` — the subscribe-time value, NOT the live one; stale retries must
  re-read (upstream retries ≤3×).
- `baseLogEpoch` = subscribe `ack.logEpoch` (`"mu76sjm3-f8ja7lv9"` this run);
  `s4t` commands additionally CAS on it (`proto.staleLogEpoch`).
- `v4/conversation/subscribe` `{topic:"conversation/<sid>",connectionId,
  clientMode:"desktop-continuous"}` → `{ack:{subscriptionId,mode,logEpoch}}`;
  frames arrive as `v4/conversation/frame` `{wireVersion:3,kind:"complete",
  topic,subscriptionId,frame:{…,payload:{kind:"snapshot"|"deltas"}}}`.
- **`turn.steerQueued`/`turn.steerDrained` DO arrive on the existing
  `session/event` channel** (`deliveryKind:"desktop-continuous"`) — the v3
  subscription the adapter already holds. A v4 frame subscription is needed
  only for snapshot/deltas (CAS baseRevision tracking), not for the steer
  events themselves.

## Bootstrap used (documented in #79 evidence, replicated in the probe)

`provider/updateAccountConfig` (8 `zhipu-account` providers, entitlement only
for `account:bigmodel-individual-coding-plan`) → `session/create{workspace,
mode:"yolo"}` → `session/setModel{account:bigmodel-individual-coding-plan/
GLM-5.3-Flash, options:{reasoningLevel:"low"}, persistAsWorkspaceLastUsed:false}`
→ `session/subscribe{deliveryKind:"desktop-continuous"}` →
`v4/conversation/subscribe`. Server→client
`interaction/requestProviderRuntimeHeaders` answered
`{headersApplied:true, requestAuth:{apiKey}}` with the plan key read from
`~/.zcode/v2/config.json` in memory — never printed; raw logs show
`<redacted-credential>`.

## Isolation & cleanup

- `session/close → {"closed":true}` on both sessions; both app-server processes
  terminated; `pgrep -f 'zcode.cjs app-server'` → **0 residual**.
- No writes under `~/.zcode` observed; `persistAsWorkspaceLastUsed:false`.
- Leak check: plan apiKey absent from every evidence file; the one place it
  transited (the runtime-headers answer) is `<redacted-credential>` in the log.
- No other run's session, worktree, tmux, or test artifact was touched; the
  #79 live session was not used or needed.

## What this does NOT yet prove

- Behaviour when the turn is **not steerable** (`turn_not_steerable` reject) or
  when guide **falls back** (`fellBack`/`admittedDelivery:"queue"` +
  `fallbackReasonCode`) — bundle-documented, not live-observed.
- `expectedTurnId` CAS on steer submission — bundle-documented, untested.
- Multi-steer, turn-end race, and disconnect paths — the holder's existing
  receipt semantics cover the reporting side.
- Whether `app-server` (no `--stdio`) differs — irrelevant: the Runner spawns
  `--stdio`.
