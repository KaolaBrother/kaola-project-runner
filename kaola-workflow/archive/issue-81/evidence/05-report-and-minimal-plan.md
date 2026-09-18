# Issue #81 — evidence report & minimal implementation proposal (M5)

For the outer layer. **No production code touched; implementation is gated on
outer confirmation of the post-#79 main/SHA.**

## Verdict

**Native v4 mid-turn steering is supported and measurable on installed ZCode
3.12.3.** Both submission entries injected live into a running turn:

- `v4/command → sendText{requestedDelivery:"guide"}` — per-command, no session
  mutation, no CAS needed.
- `v4/command → setFollowupMode{mode:"guide"}` (CAS) + plain `sendText` — the
  upstream zcode-provider path.

Receipt-grade outcomes were all produced and are distinguishable from raw
events alone: injected (`turn.steerQueued{delivery:"guide"}→turn.steerDrained
{injectedMessageIds}`, same `targetTurnId`), queued (`steerQueued
{delivery:"queue"}`, no drain), rejected (`status:"rejected",reasonCode:…`),
unknown (absent ack/events). One measured trap: **the sendText ack's
`result.delivery` says `"queue"` even for admitted guide** — the events are the
only truthful source.

Evidence index:

| File | Content |
|---|---|
| `evidence/01-receipt-contract-and-steer-surface.md` | #65 receipt contract + current steer plumbing |
| `evidence/02-upstream-v4-facts.md` | upstream zcode-provider + zcode-acp verbatim facts |
| `evidence/03-installed-3123-v4-surface.md` | installed 3.12.3 bundle method table + schemas |
| `evidence/04-live-v4-steering-verification.md` | live verdict, raw excerpts, isolation/cleanup proof |
| `evidence/live{,2}/raw-ndjson.jsonl` + `report.json` | full sanitized wire logs |
| `evidence/probes/v4-steer-probe{,2}.py` | the isolated experiment code |

## Minimal implementation proposal (post-#79 sync only)

1. **`scripts/kaola-zcode-acp.py`** (sole #79-conflict file — edit only after
   #79 merges and outer supplies the new main/SHA):
   - Route `session/event` types `turn.steerQueued` / `turn.steerDrained` into a
     per-session steer ledger (they already flow on the v3 subscription the
     adapter holds).
   - New adapter method `_session/steering`: map the holder's
     `{prompt[0].text}` → `v4/command {command:"sendText", payload:{sessionId,
     text, requestedDelivery:"guide", expectedTurnId:<active turn id>,
     clientCommandId}}`; optionally ensure a `v4/conversation/subscribe` is
     primed at session materialize for revision/turn tracking (one call).
   - Correlate the command ack + steer events by `inputId`/`sourceCommandId`
     and return the existing result shape: `injected`/`agent-confirmed` only
     after `steerDrained` into the active turn; a new `queued` outcome when
     `admittedDelivery:"queue"`; `rejected` with reasonCode; `unknown` on
     absent evidence; `promptRequired` when no steerable turn.
   - `-32601`/absent v4 (older bundles) → honest `unsupported` (holder maps it
     already) — no version gate needed; `--steer-mode interrupt` stays the
     fallback for those builds.
2. **`scripts/kaola-acp-holder.py`** (~6 lines): map `native=="queued"` →
   `steer_outcome:"not_consumed"`, `steer_native_outcome:"queued"`, explicit
   reason — queue admission is durable but is NOT consumption of the running
   turn.
3. **`platforms/zcode.yaml`**: `native_steering:"supported"`,
   `acp_steer_method:"_session/steering"`, updated `steering_summary` noting
   the ≥0.16/desktop-3.12 boundary and the interrupt fallback; regenerate
   skills via `render-skills.py --write` + `--check`.
4. **`tests/contract/fake-zcode-app-server.py` + `test-zcode-acp-contract.py`**:
   fake v4/command guide/queue/reject legs; assert `injected` only with the
   drain event, `queued`≠injected, reject codes propagate.

Deliberately NOT touched: `kaola-acp.py` (manifest plumbing already generic),
`kaola-tmux.sh` (steer tool unchanged), templates, holder lifecycle/scheduler.

## Open details to nail at implementation time

- Whether `turn.steer*` events reach `session/event` without an active
  `v4/conversation/subscribe` (untested; subscribing at materialize is the
  cheap mitigation and also feeds revision tracking).
- Live behaviour of `turn_not_steerable`, guide-fallback
  (`fallbackReasonCode`), `expectedTurnId` CAS mismatch — bundle-documented;
  receipt mapping is already defined for them.
- Whether adapter should auto-prime `followupMode:"guide"` per session or stay
  per-command (current plan: per-command — no session mutation, no CAS).

## Status

Phase 1 (evidence) complete. Awaiting outer confirmation of the post-#79
main/SHA before any production edit; no finalize/archive/sink without outer
ACCEPT.
