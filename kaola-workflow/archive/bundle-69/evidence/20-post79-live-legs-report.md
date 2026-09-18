# Issue #69 — Post-#79 live evidence report (legs A/B/C)

Candidate under test: `b40813f04f6c5faf00ef1866efe343dad4614253` (main after Issue #79
ZCode 3.12.3 ACP compatibility). Worktree `.kw/worktrees/bundle-69` fast-forwarded from
`3dd7e5eb5c4efe679ffbf4717307bf74866e5463` → `b40813f`, clean. Prior candidate `3dd7e5e`
remains the frozen SHA of the pre-#79 BLOCKED attempt (`00-diagnosis-report.md`); nothing
there is rewritten. This report is the post-#79 retry of the same three legs.

Runtime: ZCode desktop 3.12.3, CLI bundle 0.16.5, entry
`/Applications/ZCode.app/Contents/Resources/glm/zcode.cjs`, node
`/opt/homebrew/Cellar/node@24/24.18.0/bin/node`. Real provider path
`account:bigmodel-individual-coding-plan`, model `GLM-5.3`. No credentials copied, printed,
or persisted; all receipts are raw JSON sanitized by construction (adapter never emits them).

Pre-flight smoke (`.kw/verify-69-legs/smoke/`): start → real turn (`turn_completed`) →
exact stop `residual_pids: []` — post-#79 Runner path confirmed working before the legs.

---

## Leg A — real ACP `turn_failed` → idle/outcome=turn_failed → delivered → confirmed

Scratch: `.kw/verify-69-legs/legA/` (repo `legA/repo`, records `accefc5ae288d375`).
Host `zcode-kaola-i69a-host` (holder 80951, agent 80966, native `sess_59a7fe78-…`),
worker `zcode-kaola-i69a-worker` (holder 85752, agent 85764), ACP session `zcode-1`,
worker bound to host heartbeat socket.

Method: worker's app-server backend (sole child of its adapter, PID 85784) was killed
while the adapter stayed alive — a real backend crash, not a tool nonzero. The next
`send` hit the dead pipe:

- `06-worker-send-turnfailed.json`: `outcome: "turn_failed"`,
  ACP JSON-RPC error `{"code":-32603,"message":"internal error: [Errno 32] Broken pipe"}` —
  a genuine error response on the ACP `session/prompt` call (the holder `turn_failed` path),
  not a `refusal`/`end_turn` result.

Host event log (`zcode-kaola-i69a-host/events.jsonl`):

```
14 worker_event            zcode/zcode-kaola-i69a-worker/idle/13  outcome=turn_completed (baseline)
15 worker_event_delivered  idle/13
27 worker_event_confirmed  idle/13
28 worker_event            zcode/zcode-kaola-i69a-worker/idle/14  outcome=turn_failed
29 worker_event_delivered  idle/14
36 worker_event_confirmed  idle/14
37 worker_event            zcode/zcode-kaola-i69a-worker/terminated/15  exit_code=0
38 worker_event_delivered  terminated/15
44 worker_event_confirmed  terminated/15
45 process_exited
```

Stops: worker `07` and host `08` both `stopped:true, agent_exit_code:0,
residual_pids:[]`. **Leg A: live-proven.**

## Leg B — unconfirmed event redelivery after Host holder resume

Scratch: `.kw/verify-69-legs/legB/` (repo `legB/repo`, records `61a887d8f07c832a`).
Host `zcode-kaola-i69b-host`, worker `zcode-kaola-i69b-worker`,
ACP session `zcode-1`. Host native sessions: `sess_c1749222-…` (first materialization),
`sess_363a1429-…` (post-resume re-materialization).

Method: worker `idle` event staged while the host was mid-turn on a long count prompt;
host holder force-stopped before the notification turn could confirm the event; holder
restarted with `start --resume zcode-1`.

Host event log:

```
107 worker_event            zcode/zcode-kaola-i69b-worker/idle/19  outcome=turn_completed
108 process_exited          (holder force-stopped; idle/19 still unconfirmed)
109 worker_event_restored   ["zcode/zcode-kaola-i69b-worker/idle/19"]
110 worker_event_delivered  idle/19
129 worker_event_confirmed  idle/19
130 worker_event            zcode/zcode-kaola-i69b-worker/terminated/20
131 worker_event_delivered  terminated/20
139 worker_event_confirmed  terminated/20
140 process_exited
```

Receipts: `16-host-force-stop2` `stopped:true residual_pids:[]`;
`17-host-resume-zcode1` `state:ready acp_session_id:zcode-1`; `18-worker-stop`,
`19-host-stop` both `residual_pids:[]`. **Leg B: live-proven.**

Discarded attempt (kept for honesty): first try `idle/13` staged 46 → delivered 47 →
confirmed 58 before the stop landed (inter-call latency beat the ~4.4s notification
turn); it proved nothing and is not claimed.

## Leg C — duplicate event dedup, single consumption/ack

Scratch: `.kw/verify-69-legs/legC/` (repo `legC/repo`, records `adfef59454c34f07`).
Host `zcode-kaola-i69c-host` (holder 35525, agent 35527, native `sess_3c61121b-…`),
worker `zcode-kaola-i69c-worker` (holder 35785, agent 35787),
host socket `…/kaola-501-acp/d73b22f4276379322165e2c5.sock`.

Method: real worker `idle` event `zcode/zcode-kaola-i69c-worker/idle/14` staged on the
busy host (cursor 17), then the byte-identical carrier op (`op:"worker_event"`, same
kind/platform/session/repo/reason/event_cursor) was re-sent on the host's Unix socket
via `replay-worker-event.py`.

- `06-replay-duplicate.txt` raw reply:
  `{"duplicate":true,"event_id":"zcode/zcode-kaola-i69c-worker/idle/14","pending":1}` —
  rejected as duplicate; pending stayed 1 (no second staged event).
- Host log: exactly one lifecycle for the pending copy —
  `17 worker_event` → `150 worker_event_delivered` → `169 worker_event_confirmed`.
  One staging, one delivery, one acknowledgement.

Boundary check (same op sent again after confirmation):
`08-replay-post-confirm.txt` reply `{"staged":true,"delivered":true,…}` → second
lifecycle `170 worker_event` → `171 delivered` → `177 confirmed`. Dedup authority spans
the pending window only; an identical re-delivery after ack is a new occurrence
(at-least-once semantics). `terminated/15` chain 178→179→185.

Stops: `09-worker-stop`, `10-host-stop` both `stopped:true, agent_exit_code:0,
residual_pids:[]`. **Leg C: live-proven.**

## Product defect found during leg B (documented, unfixed, outside evidence scope)

Faithful native-session resume on real ZCode 3.12.3/0.16.5 fails inside the adapter:
`kaola-acp zcode resume` of `sess_c1749222-…` → `resume-failed: resumed session reports
no persisted model (session/read failed); refusing to substitute the provider default`.
Raw-wire probe (`09`/`10-probe-resume-read*.txt`, harness `probe-resume-read2.py`):
`session/resume` + `session/subscribe` + `session/read` all SUCCEED, but
`session/read` returns a message-list shape with no `settings` object, so
`hydrate_settings()` never recovers the persisted model
(`account:bigmodel-individual-coding-plan`/`GLM-5.3` is visible in message metadata,
unparsed) → `reregister_provider` fails closed. Legacy `session/setModel` +
`runtimeModel` → `ZodError Unrecognized key "runtimeModel"` (dead protocol confirmed on
a live resumed session); account-path `setModel` → `Provider Registry 中不存在 Model:
[object Object]` (provider never re-registered on the resume path). This is a real
adapter↔3.12+ resume gap — pre-3.12 protocol remnants in the resume path. It does not
affect leg B's verdict: the event-carrier guarantee under test (holder restart →
`_restore_worker_events` from the append-only log → redelivery → confirm) was proven on
the surviving `start --resume` path, which re-materializes a fresh native session.
Production code untouched; defect reported for triage under its own scope.

## Verdicts vs prior BLOCKED rows

| leg | pre-#79 (3dd7e5e) | post-#79 (b40813f) |
|---|---|---|
| A real turn_failed | BLOCKED (adapter could not materialize) | **live-proven** |
| B resume redelivery | BLOCKED (same wall) | **live-proven** |
| C duplicate dedup | BLOCKED (same wall) | **live-proven** |

All exact-stop receipts report `residual_pids: []`. No production file was modified;
only untracked `.kw/` scratch was written. Issue #65 archived evidence untouched.
