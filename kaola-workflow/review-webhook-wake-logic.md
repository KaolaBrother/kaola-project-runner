# Review: Delegator webhook wake logic (main @ 8739ad9e)

Read-only expert review, 2026-10-14, requested by the Delegator (owner Yanlei, per-task
permission). Scope: `scripts/kaola-acp-holder.py`, `scripts/kaola-acp.py`,
`scripts/kaola-recovery-routes.py`, the Delegator Skill reference
`templates/kaola-delegator/references/webhook-wake.md`, `docs/api.md`, the contract tests under
`tests/contract/`, GitHub issues #299, #302, #307, #311 (incl. the post-close comment of
2026-10-13 15:48Z, point 4), #314, #315, and the draft `/tmp/i316.md`. No code was changed,
no issue filed, nothing installed or released. This file is the only write.

All `file:line` citations are against commit `8739ad9e` in this checkout. `holder` means
`scripts/kaola-acp-holder.py`, `acp` means `scripts/kaola-acp.py`, `routes` means
`scripts/kaola-recovery-routes.py`. `kaola-dispatch.py` and `kaola-record-contract.py` contain
no wake logic; the record contract only supplies `seat_exempt_record` (used by the all-idle
scan through `holder:802-806`).

Version lineage (CHANGELOG): #299 → v0.9.5; #302 → v0.9.7; #305 → v0.9.8; #307 → v0.9.9;
#311 (+#309 routes) → v0.9.10; #314 and #315 → Unreleased on main.

---

## (a) Rule table — every wake trigger and suppression as implemented

Notation: `state/state_detail/reason` is the payload triple sent by `_delegator_wake`
(`holder:3350-3407`). Every holder-side wake is gated by `session_role == "host"`
(`holder:3362-3363`) and by the closed reason vocabulary (`holder:291-304`, `holder:3364-3365`;
sender copy `acp:6351-6364`, enforced at `acp:6849-6850`).

### A. Independent triggers (never pass through the turn-end predicate)

| # | Trigger | Condition | Code location | state / detail / reason | Issue |
|---|---|---|---|---|---|
| A1 | Permission required | New `session/request_permission` id (`is_new`) on a Host holder | `holder:2718-2737` (wake at 2737) | `blocked` / `permission_required` / `permission_required` | #299 |
| A2 | Turn failed | `on_prompt_response` outcome `turn_failed` (JSON-RPC error that is not -32800, or systemError mapped by #173) | `holder:2874-2879` | `error` / `turn_failed` / `turn_failed` | #299, #302 |
| A3 | Agent exited | `on_agent_exit` with `not stop_requested` and state not in (`starting`, `error`) | `holder:2951-2953` | `error` / `agent_exit` / `agent_exited` | #299 |
| A4 | Boot failure | `run()` boot result has `error` and holder was not already ready | `holder:6797-6806` (wake at 6806) | `error` / `boot_failure` / `boot_failure` | #299 |
| A5 | Exact stop | `op_stop` after `state = "stopped"`; spawned `inline=True` so the child holds its payload before the reply | `holder:6376-6380` (wake at 6380) | `stopped` / `exact_stop` / `exact_stop` | #299 |
| A6 | Death recovery (start) | `command_start` replaces a dead or pid-reused Host record whose `agent_pid`/`agent_pgid` are both dead | `acp:5529-5536` (gate 5529-5531, wake 5534-5536) → `recover_host_death_wake` `acp:2083-2148` | `error` / `holder_lost` / `holder_lost` | #299 (843902e2) |
| A7 | Death recovery (dead-holder stop) | `force_kill_from_record` after the sweep; pid-reused branch too | `acp:2629-2632`, `acp:2701-2704` | same as A6 | #299 |
| A8 | Death recovery (status scan) | `delegator-webhook status` on an enabled, valid entry walks `*/*/*/record.json`; eligible = Host role, not `stopped`, same project, holder pid dead, agent pid and pgid dead | `acp:7106-7112` → `_webhook_attach_holder_lost` `acp:6986-7000` → `_webhook_scan_holder_lost` `acp:6957-6983`, eligibility `acp:6936-6954` | same as A6 | #311 |
| A9 | Death dedupe | One `delegator_death_wake` event per `holder_instance_id` under `delegator-death-wake.lock`; a second caller gets `already-recovered`; event cursor = new `event_seq` | `acp:2105-2122` | — | #299, #311 |
| A10 | All-idle re-check after node stop | Confirmed Sideagent node stop → `_maybe_delegator_all_idle()` | `holder:4710-4715` → `holder:3438-3462` | `end_turn` / `end_turn` / `all-idle` | #305 |
| A11 | All-idle re-check after last worker stop | A dispatched worker's `terminated` carrier event, with that session ignored once | `holder:5273-5274` → `holder:3438-3462` | same as A10 | #305 |
| A12 | Re-check suppressions | Not Host; `stop_requested` or state `stopping`/`stopped`; a turn active or a queued after-turn steer; last outcome not completed/canceled; any working seat (which also clears the latch) | `holder:3449-3461` | — | #305, #307 |

### B. Gated turn-end predicate (`delegator_turn_wake_reason`, `holder:360-459`; caller `holder:3310-3348`; invoked at `holder:2880-2896`)

Inputs gathered by `_delegator_turn_end_reason`: staged undelivered worker events / unconfirmed
overflow and undelivered host-view `attention` rows (`holder:3274-3308`), open registered
`state.decisions` rows with owner `delegator`/`user` (`holder:314-340`, merged only when no seat
works, `holder:3321-3322`), `live_seats` from the all-idle scan (`holder:3317`),
`self_continuing` (`holder:3335`), and `all_idle_due = not _all_idle_woken` (`holder:3336-3337`).

| # | Rule | Condition | Code location | reason emitted | Issue |
|---|---|---|---|---|---|
| B0 | Only completed / unrequested-cancel turns enter | outcome ∈ {`turn_completed`, `turn_canceled`}; a cancel under `stop_requested` is covered by A5 | `holder:2880-2881`, `holder:429-432` | — | #299, #302 |
| B1 | Self-continuation suppresses | next beat already admitted (`turn.active`) or `_delegator_followups > 0` (after-turn steer queued, `holder:5549-5554`) | `holder:433-434` | none | #302 |
| B2 | No working seat: attention first | `not live_seats` and `classify_delegator_attention(rows + decisions)` is not None | `holder:440-443` | `question_waiting` (decisions/host-decision), `delivery_review` (tasks/awaiting-verdict, delivery-open, verdict-missing), else `needs_decision` incl. `registered-decision` (`holder:343-357`) | #315 |
| B3 | No working seat, Delegator turn, latch set | `prompt_source == "delegator"` and `not all_idle_due` | `holder:444-445` | none | #307 |
| B4 | No working seat, otherwise | self turn, or Delegator turn with latch clear (e.g. it stopped the last seat) | `holder:446` | `all-idle` via `_emit_delegator_all_idle` (`holder:2892-2894`, latch `holder:3420-3436`) | #302 owner rule, #307, #315 fallback |
| B5 | Working seat, Delegator turn suppresses | `prompt_source == "delegator"` (socket `prompt` or steer; `handle_request` strips a client's `_prompt_source` claim `holder:6601-6605`; admission default `holder:3139-3147`) | `holder:447-448` | none | #302 |
| B6 | Working seat, self turn, attention | undelivered attention rows (fingerprint ≠ `host_attention_seen`) | `holder:449-451` | as B2 | #302 |
| B7 | Working seat, self turn, stopped with pending | staged undelivered worker events / unconfirmed overflow, or `stop_reason` ∈ {`max_tokens`, `max_turn_requests`, `length`} (`holder:306`) | `holder:452-454` | `host_stopped_pending` | #302 |
| B8 | Working seat, self turn, refusal | `stop_reason == "refusal"` | `holder:455-456` | `needs_decision` | #302 |
| B9 | Working seat, self turn, unrequested cancel | outcome `turn_canceled` | `holder:457-458` | `needs_decision` | #302 |
| B10 | Clean idle with a working seat | none of the above | `holder:459` | none | #302 |
| B11 | `state_detail` on turn-end wakes | agent `stopReason` verbatim if it matches `[A-Za-z0-9_.:-]{1,64}` (`holder:288`), else `other`; absent on a cancel reads `cancelled` | `holder:2884-2891` | — | #299 |

### C. All-idle scan and episode latch

| # | Rule | Condition | Code location | Issue |
|---|---|---|---|---|
| C1 | Live-seat scan | `ps` rows containing `kaola-acp-holder` whose own `record.json` names this holder instance as `dispatcher` and whose `holder_pid` matches the row | `holder:809-868` (dispatcher match 864-867) | #302, #303 |
| C2 | Seat-exempt skip | `session_role` ∈ `SEAT_EXEMPT_ROLES` (`sideagent`, legacy `sidekick`) via record contract | `holder:851-852`, `holder:802-806` | #303, #305 |
| C3 | Not-working states | record `state` ∈ {`agent_exited`, `stopping`, `stopped`} | `holder:696`, `holder:853-854` | #305 |
| C4 | Turn-state rule | `seat_turn_blocks_all_idle`: no `last_prompt` key → idle; `last_prompt` not a dict → blocks (unknown); no `mutation_status` key → idle; `completed`/`not_started` → idle; `in_progress`/`accepted` → blocks; anything else (incl. `unknown`, null) → blocks | `holder:706-745`, sets `holder:701-703`, call `holder:855-856` | #314 |
| C5 | Ignore-once | `ignore_sessions` drops the just-terminated worker whose record may still say `ready` | `holder:857-858`, `holder:5274` | #305 |
| C6 | Latch set | `_emit_delegator_all_idle` takes the claim before the detached spawn; second call in the same episode returns False (no POST) | `holder:3420-3436` | #305, #307 |
| C7 | Latch clear (only "working-again" facts) | a re-check that still sees a working non-exempt seat (`holder:3459-3460`); a non-exempt worker `terminated` (`holder:3478-3488`, exempt check `holder:3464-3476`); a self turn that admitted new worker events (`holder:5050-5054`) | `holder:3409-3418` | #307 |
| C8 | Latch NOT cleared | a Delegator-admitted turn, a self turn without new worker events (compaction reload `holder:4981`, project notice `holder:4833`), node termination | `holder:3148-3152`, `holder:3483-3488` | #307 |
| C9 | No time throttle anywhere | — | `holder:3436`, docstrings | #302 |

### D. Sender side (`kaola-acp.py delegator-webhook deliver`, detached child)

| # | Rule | Condition / value | Code location | Issue |
|---|---|---|---|---|
| D1 | Detached child per wake | `Popen(... start_new_session=True)`, payload on stdin, stdout/stderr → DEVNULL; non-inline path `proc.wait()`s in a daemon thread and discards the exit status; spawn exception → one event `delegator_wake_spawn_failed` with the exception class only | `holder:3377-3407` (wait 3395-3396; spawn-failed 3399) | #299 |
| D2 | Payload validation | exact key sets for three shipped shapes; `state` ∈ {end_turn, blocked, error, stopped, test}; reason in vocabulary; invalid → exit 1 and a `failed`/`invalid-payload` receipt only when `project` resolves to a directory | `acp:6807-6853`, `acp:7078-7092`, `acp:7047-7054` | #299, #304 |
| D3 | Config lookup | `~/.config/kaola/delegator-webhook.json` (or `KAOLA_DELEGATOR_WEBHOOK_CONFIG`), entry by `realpath(project)`; config error → `failed` (`config-mode`/`invalid-config`); absent or `enabled != true` → `skipped`/`not-configured` | `acp:6860-6877` | #299 |
| D4 | Dedupe claim | `(holder_instance_id, event_seq)` claimed under the receipts flock BEFORE any network attempt; kept after success AND after final failure; bounded to 256 pairs; claim-file failure → deliver anyway; duplicate → `skipped`/`duplicate`, no POST | `acp:6879-6897`, `acp:6761-6788`, limit `acp:6299` | #302 |
| D5 | Timeout | 12 s per attempt; a timeout is final (never retried) | `acp:6304`, `acp:6646-6649` | #302 |
| D6 | Retry set | `connection` errors, HTTP 5xx, and HTTP 400/408/429; backoff 1 s, 2 s, 4 s; max 4 attempts | `acp:6305-6310`, `acp:6638-6652`, loop `acp:6900-6919` | #302, #311 (400 added) |
| D7 | Final 4xx | 401, 403, 404 and every other 4xx not in D6 → final on attempt 1; `redirect-refused` final | `acp:6650-6652`, `acp:6620-6621` | #302, #311 |
| D8 | Receipt rows | one row per attempt, written before the backoff sleep; fields `ts,state,state_detail,session,holder_instance_id,event_seq,result,attempt,max_attempts,http_status,error,response_body,response_body_truncated,response_headers,elapsed_ms,final` (+`reason` on delivered/failed, `skip_reason` on skipped); `failed` rows are stamped with a #309 route | `acp:6655-6695` (stamp 6693-6694), ring of 32 `acp:6728-6743` | #299, #304, #309, #311 |
| D9 | Redacted error body | on `http-status` only: read ≤ 8192 B, replace URL/key (and percent-encoded forms) with `[redacted]`, store ≤ 512 chars, allowlisted headers (`content-type, retry-after, www-authenticate, x-request-id, x-correlation-id`) cut at 200 chars | `acp:6327-6336`, `acp:6555-6599` | #311 |
| D10 | Receipt-write failure | swallowed entirely ("deliver must never crash the detached child") | `acp:6746-6754` | #299 |
| D11 | Exit code | 0 on delivered/skipped, 1 otherwise — but the holder never reads it (D1) | `acp:7097` | — |

---

## (b) Gap list

Severity: **High** = a wake the owner rules require is lost with no defined recovery;
**Medium** = lost or wrong wake in a narrower case, or a failure with no route; **Low** = a
spurious wake or a diagnostic hole. Every fix below is a PROPOSAL only.

### G1 — A Delegator-admitted turn end wakes nobody when nobody is reading (High; this is #311 point 4 / `/tmp/i316.md`)

**Evidence.** `holder:447-448` returns `None` for every `prompt_source == "delegator"` turn
while a seat works, and `holder:444-445` returns `None` for such a turn with no working seat
once the episode latch is set. The holder records nothing about whether the turn's result was
taken by anyone:

- `send --no-wait` returns `in_progress` at admission (`holder:3202-3216`) and no process ever
  waits for the end of that turn. This is the **canonical** Delegator form in the generated
  Skill references: `templates/kaola-delegator/references/snapshot.md:86` and
  `references/handoff.md.tmpl:110` both say `send ... --no-wait`. So "unconsumed" is the normal
  case for a Grok Bot Delegator, not an edge case.
- `send --wait --timeout N` returns `prompt_timeout` (`holder:3226-3230`); the later turn end
  is evaluated with the same `delegator` source and stays silent.
- A `--wait` caller that died: the reply `sendall` (`holder:6676`) raises and is swallowed by
  `except (OSError, ValueError): return` (`holder:6687-6688`). No event, no receipt.
- The wake decision runs in the reader thread (`holder:2882`) before the waiting caller is even
  notified, so today's predicate cannot know consumption even in principle.

The VRPCadCore sequence in #311 point 4 (three `send` relays, three clean `end_turn`s, no
receipt after event_seq 8099, 75 min idle with queued work and free seats) is exactly what
these lines produce: with a working seat → B5; with none and the latch set → B3. The `#302`
test `test_delegator_send_does_not_wake` (`tests/contract/test-issue-302-delegator-wake-gate.py:564`)
and `test_delegator_sends_to_an_idle_host_do_not_wake_again` (`:1006`) assert this silence
using `--wait` callers that do consume; no test covers `--no-wait`, a timed-out waiter, or a
dead waiter.

**Proposed fix (proposal only).** Make "the Delegator already has this result" a recorded
fact instead of an assumption, as the draft says, but define it precisely:

1. At admission store `turn["wait"] = bool(params.get("wait", True))` and
   `turn["result_taken"] = None`.
2. For `wait=False`: the turn is unconsumed by construction; at turn end run the normal
   predicate as if `prompt_source == "self"` (so a registered decision is still
   `needs_decision`, a length stop is still `host_stopped_pending`, a clean end with a working
   seat becomes the new reason `delegator_turn_unconsumed`, and the no-seat case keeps the
   `all-idle` latch semantics).
3. For `wait=True`: on `prompt_timeout` return mark `result_taken = False`; on the normal
   return path, decide in `serve_connection` after `sendall` succeeds (`holder:6676`) →
   `result_taken = True`, on `OSError` → `False`. Defer the gated turn-end decision for a
   Delegator `wait=True` turn until that mark lands (or the connection is gone), then evaluate
   once. A consumed turn keeps today's rules exactly (B3/B5). This keeps #302/#307 intact for
   the case they were written for.
4. Add `delegator_turn_unconsumed` to both closed vocabularies (`holder:291-304`,
   `acp:6351-6364`), the `docs/api.md` reason table, `webhook-wake.md` ("That list is every
   wake"), and `test_mapping` in the #302 test.

**Owner value choice this creates.** With the Skill's canonical `--no-wait`, rule 2 yields one
wake per Delegator relay turn end. That is #311 point 4's literal request and it is bounded
(one per turn, dedupe on `event_seq`, latch untouched), but it is the opposite of #302's
"a turn end caused by the Delegator's own send does not wake". Either accept one wake per
unconsumed relay, or change the Skill's canonical relay to `send --wait --timeout <n>` so a
short relay is consumed in-line and only the overflow wakes. Decide before implementing.

### G2 — A final failed delivery is a lost wake with no re-offer (High; answers point 3)

**Evidence.** After the attempt loop ends with `final: true` and `result: failed`
(`acp:6905-6919`), the claim for `(holder_instance_id, event_seq)` stays (`acp:6763-6766`
docstring, `acp:6783`), so the same event can never be POSTed again; the child's exit status 1
goes to DEVNULL and the holder discards `proc.wait()` (`holder:3395-3396`); if the wake was
`all-idle` the latch was set before the spawn (`holder:3431-3434`) and nothing clears it until a
working-again fact, so the transition is gone for the whole episode; no owed-wake state exists
on the Delegator side (contrast the worker→Host `undelivered_wakes` re-offer at
`holder:3630-3715`, which is deliberately Host-only). The #309 route on the row
(`routes:139` for `http-status`, `:77` `connection`, `:345` `timeout`) says "Report result ...
Do not retry a final receipt and do not POST by hand. Stay heartbeat-only when test does not
wake the routine." That text is addressed to a reader, but the only reader who will see it is
the cron fallback inquiry, up to one `cadence.interval_minutes` later (`docs/api.md:956-960`,
example 120 min), and neither `webhook-wake.md` nor `inquiry-report.md` tells that inquiry to
treat `status.last_receipt.result == "failed"` as a missed wake (grep: `inquiry-report.md` has
no `last_receipt`/`status --project` instruction; `webhook-wake.md:72-75` covers only the
self-configuration `test` failure).

**Proposed fix (proposal only).**

- Route text, split by class and finality (`routes` table): `http-status` 401/403 → "rotate
  the sender key (webhook-wake.md step 7), then `test`"; 404 → "reconfigure the URL, then
  `test`"; final 400/408/429/5xx, `connection`, `timeout` → "this wake is lost until the cron
  fallback; on that inquiry run `status`, then `observe`/`capture` for the recorded Host and the
  full standard inquiry; run `test` once — if it delivers, the endpoint is back and nothing else
  is owed; if not, stay heartbeat-only and report". Keep non-final rows unstamped or stamped
  "retrying" (today `_stamp_recovery` runs on every `failed` row including the three non-final
  ones, `acp:6693-6694`, with text that says "do not retry a final receipt").
- Delegator Skill: add one sentence to the canonical inquiry: "If `status.last_receipt` is
  `failed` and `final`, treat it as a missed wake and run the whole inquiry; do not conclude
  'nothing new' from an empty webhook run."
- Optional, owner's call because it touches the signal shape: let the next deliver of any later
  event from the same holder include `missed_event_seq` (read from the receipts file by the
  child), so the next successful wake carries the fact that one was lost. This widens
  `_webhook_payload_ok`'s closed key set (`acp:6341-6347`) and all three shapes must stay
  accepted. I would not add a holder-side re-offer loop: it is the "new timer" the owner
  excluded.

### G3 — Holder death with the agent process still alive never produces `holder_lost` from `start` or `status` (Medium)

**Evidence.** `command_start` returns `holder_lost_receipt` BEFORE the death wake when
`agent_pgid` or `agent_pid` is alive (`acp:5529-5531`); the status scan excludes the same case
(`acp:6952-6953`, documented `docs/api.md:949-951`). Only a dead-holder `stop`
(`force_kill_from_record`, `acp:2629-2632`) kills the agent and then wakes. So after a holder
SIGKILL whose ACP agent child survives (it is a separate process; whether it exits on stdin EOF
depends on the agent), the Delegator gets no `holder_lost` until it, or the owner, runs `stop`.
`test_sigkilled_host_holder_recovered_on_next_start` (`tests/contract/test-issue-299-delegator-webhook.py:1349`)
uses the mock agent, which exits on EOF, so this case is untested. The route for the
`holder-lost` outcome (`routes:119`) does tell the caller to exact-stop, which closes the loop
only once someone is there to read it.

**Proposed fix.** Let the status scan (and `command_start`) emit the death wake when the holder
pid is dead regardless of agent liveness, with `state_detail` `holder_lost` and the live agent
pids in the start/stop receipt (never in the payload). The agent-alive guard exists to protect
record replacement, not the wake; splitting those two decisions keeps #311 point 3 honest.

### G4 — Wake failure modes with no route and no reader (Medium; answers point 4 in detail)

| Mode | What happens now | Evidence | Route? |
|---|---|---|---|
| Holder cannot spawn the deliver child | one event `delegator_wake_spawn_failed` with the exception class; no receipt row; nothing reads this event (repo-wide grep: no consumer outside the holder) | `holder:3399-3402` | **No** |
| Death-recovery spawn failure | nested `{"sent": false, "reason": "spawn-failed", "error": "<class>"}` under `delegator_death_wake`; `stamp` recurses only into `holder_lost` (`routes:429-431`) and `_failure` does not recognise `sent: false`, so the nested dict gets no route; the only `spawn-failed` row in the table (`routes:305`) describes a session restart, which is the wrong action for a wake-child failure | `acp:2144-2146` | **No** (and the nearest existing route is misleading) |
| Death-recovery lock/log OSError | `recover_host_death_wake` returns `None`; the start/stop/status receipt simply omits `delegator_death_wake` | `acp:2121-2122` | **No** (silent) |
| Status scan `RecordRootMismatch` | `holder_lost.scan = "incomplete"` with no `reason`; `_failure` requires `scan == "skipped"` + `reason`, so not stamped | `acp:6965-6967`, `routes:_failure` | **No** |
| Receipt-write failure | swallowed; POST may have succeeded with no evidence; `status.last_receipt` goes stale | `acp:6746-6754` | **No** (by design, but invisible) |
| Deliver with unresolvable `project` (dir removed/renamed) | exit 1 to DEVNULL, no receipt anywhere | `acp:7093-7095`, `acp:7047-7054` | **No** |

**Proposed fix.** (i) Have the holder write a `failed` receipt row (`error: "spawn-failed"`)
through the same receipts file when the child cannot be spawned, so `status.last_receipt`
shows it; (ii) add a `wake-spawn-failed` route ("the wake was not attempted; run
`delegator-webhook test`; if that delivers, continue the inquiry now"); (iii) make `stamp`
recurse into `delegator_death_wake` and treat `sent: false` as a failure; (iv) give
`scan: "incomplete"` a `reason: "record-root-mismatch"` so the existing `routes:261` row
attaches; (v) on receipt-write failure, at least print one line to the child's stderr and
let the holder capture stderr into its event log instead of DEVNULL (`holder:3386-3387`).

### G5 — A Delegator-requested cancel of a Host self turn can wake `needs_decision` (Low)

**Evidence.** `op_cancel` / `op_steer_interrupt` (`holder:5755`, `holder:6041`) end the running
turn with outcome `turn_canceled` and `stop_requested` false. If that turn was a self turn
(worker-event beat) and a seat works, the predicate reaches `holder:457-458` and reports
`needs_decision` with `state_detail: cancelled`, although the Delegator itself asked for the
cancel and is about to send the follow-up. `_delegator_followups` covers only the after-turn
steer queue (`holder:5549-5554`), not the interrupt path. Not covered by a test; verify with
`steer --steer-mode interrupt` on a self turn.

**Proposed fix.** Mark a cancel that arrived through the socket (`op_cancel`,
`op_steer_interrupt`) on the turn (`turn["cancel_source"] = "delegator"`) and treat it like a
Delegator-sourced turn end in the predicate.

### G6 — With a working seat, attention and decisions registered during a Delegator turn never wake (Low; same root as G1)

**Evidence.** `holder:447-448` precedes `holder:449-451`, and decisions are merged only when no
seat works (`holder:3321-3322`). Under the "Delegator present" assumption this is intended
(#302, #315 test `test_active_seat_keeps_current_behavior`); under `--no-wait` it is G1 again.
The G1 fix (evaluate an unconsumed turn as `self`) resolves it; no separate change.

### G7 — A pending registered decision re-wakes on every later silent self turn end (Low, informational)

**Evidence.** B2 is not latched (`holder:440-443`; #315 says the latch must not suppress it) and
`open_registered_decision_rows` returns every still-pending row (`holder:314-340`). With no
working seat, each self turn end (compaction reload, project notice) re-sends `needs_decision`
with a new `event_seq`. Few turns happen in that state, so this is a bounded repeat, but it is a
repeat the #302 rule "never twice for the same event" did not anticipate. If it shows up in
receipts, latch B2 on the decision ids (fingerprint of the pending set), cleared when the set
changes.

### G8 — Route text does not distinguish auth failures (Low; part of point 3)

`routes:139` gives one text for every `http-status`. 401 (bare key, documented at
`webhook-wake.md:39-40`) and 403 need a key rotation, 404 a URL fix, and an exhausted 400 a
probe; see G2 for the split.

---

## Assessment of `/tmp/i316.md`

**Does the gap exist on current main?** Yes, confirmed at `holder:444-448` and the absence of
any consumption fact (`holder:3202-3230`, `holder:6676-6688`). It is stronger than the draft
states: because the generated Delegator references use `send --no-wait` as the canonical relay
form, every canonical relay turn end is unconsumed today, not only the detached/dead-caller
cases. The "caller returned, detached or died" wording should be widened to "no live `wait`
caller consumed the final receipt, including `--no-wait` admission and `prompt_timeout`".

**Is the draft rule correct?** The direction is right and matches the owner rules: it does not
return to "wake on every turn end" (#302), and it leaves the all-idle once-per-episode latch
alone (#307). Three corrections:

1. *Consumption cannot be observed where the decision is made today.* The predicate runs in
   `on_prompt_response` before the waiter sends the reply. The implementation must either defer
   the Delegator-turn decision until the reply path reports success/failure, or decide at
   admission for `wait=False`. Without that, "consumed receipt" is a label with nothing to set
   it.
2. *Reason precedence.* An unconsumed Delegator turn should be classified like a self turn
   (attention / registered decision → `needs_decision` etc., length stop → `host_stopped_pending`,
   refusal → `needs_decision`) and only fall through to `delegator_turn_unconsumed` for the clean
   case; otherwise a registered decision at the end of such a turn is reported with the weaker
   reason. With no working seat the existing B2–B4 order already does the right thing; the new
   reason is only needed for the working-seat branch (B5).
3. *Vocabulary lockstep.* The new reason must be added in both closed sets, the docs table and
   `webhook-wake.md`, or the sender refuses the payload (`acp:6849-6850`) and the holder never
   sends it (`holder:3364-3365`).

**Is it complete?** Not yet: it omits the `--no-wait` norm and the `prompt_timeout` case; it
does not say what happens to the all-idle latch (answer: nothing — leave it); it does not
mention the steer-interrupt path (G5); and it does not state the owner value choice (one wake
per unconsumed relay vs. switching the canonical relay to `--wait`).

**Regression risk against #302 / #307.** Low for `--wait` callers that consume: B3/B5 are
unchanged for them, the latch is untouched, event_seq dedupe still applies. For `--no-wait`
callers the behaviour changes by design: one wake per relay turn end. The #307 five-messages
scenario stays quiet only if the Delegator uses `--wait` for those sends; with `--no-wait` it
would produce five bounded wakes, each for a result nobody read. That is a product decision,
not a regression in the mechanism, but it must be made explicitly. Risk of double wakes: none
as long as the unconsumed decision is taken once per turn (guard it with the turn's
`request_id`, as the response matching already does at `holder:2810-2813`).

**`idle_with_queue`.** I recommend not adding it in the holder. The holder has no notion of a
queue or of free seats: it reads only the host-view `attention` list and `state.decisions`
(`holder:3274-3308`), and "free seats" needs the Delegator's grant counts. Judging "queue
non-empty and seats free" in the holder adds a second scheduling judgment to a transport
component, which the project contract forbids (Project Runner Skills "only identify, start,
capture, send, read, and stop"). With no working seat the `all-idle` fallback already covers
"idle with a queue" once per episode. The uncovered case is "some seats working, more ready
work, Host ended its turn without dispatching", which is a Host duty; if the owner wants the
Delegator nudged there, the cheapest honest path is a typed host-view attention row written by
the state tool (e.g. `kind: tasks, why: dispatch-ready`), which already classifies as
`needs_decision` at `holder:355-356` with no new reason and no holder change — but note that
`host_attention_seen` only advances when a self turn delivers worker events (`holder:5056`),
so such a row would re-wake at each turn end until retired; that fingerprint update would need
to move to "whenever a wake was emitted for it".

**Proposed tests.** The three in the draft are necessary but not sufficient. Add: `--no-wait`
send → one wake at turn end; `--wait --timeout` that expires, turn ends later → one wake;
`--wait` caller killed mid-wait → one wake; `--wait` consumed → no wake and latch unchanged;
unconsumed turn with a pending registered decision → `needs_decision`, not the generic reason;
the #307 five-sends sequence in both modes with the expected counts; `test_mapping` extended
with the new reason; and a steer-interrupt on a self turn (G5) to pin whichever behaviour is
chosen.

---

## Point 3 — HTTP 400 with no retry remaining: what happens now, and the recovery route

**Sequence on current main.** Attempt 1 → 400 → `_webhook_retryable` true (`acp:6310`,
`acp:6650-6652`) → receipt row (`result: failed`, `attempt: 1`, `final: false`,
`error: http-status`, `http_status: 400`, redacted `response_body` ≤ 512 chars,
`response_body_truncated`, allowlisted `response_headers`, plus the #309 `route` text from
`routes:139`) → sleep 1 s → attempt 2 → same → sleep 2 s → attempt 3 → same → sleep 4 s →
attempt 4 → `final: true` because `attempt == DELEGATOR_WEBHOOK_MAX_ATTEMPTS` (`acp:6905-6906`).
Four rows, ≈ 7 s plus four round trips, each written before its sleep (`acp:6915`). The child
exits 1 (`acp:7097`).

**Wake-side state afterwards.** The claim is kept (D4), so that `event_seq` can never be
re-POSTed. The holder learned nothing (D1). If the reason was `all-idle`, `_all_idle_woken`
stays true (`holder:3431-3434`) until a working-again fact; a registered decision would still
re-wake at the next turn end (B2, G7), but a clean all-idle will not. Nothing retries later;
nothing alerts; `delegator-webhook status` will show the failed row as `last_receipt`
(`acp:7032`) only when someone runs it.

**Recovery route today.** Only the cron fallback inquiry (at most one `cadence.interval_minutes`,
`docs/api.md:956-960`), and only if that inquiry reads status/observe/capture anyway. The route
text attached to the row is correct but assumes a reader and does not distinguish 400 from
401/403/404.

**Recommended route (per the #309 principle, proposal).** See G2 and G8: a defined next
command per class (`test` probe for exhausted 400/5xx/connection/timeout, key rotation + `test`
for 401/403, URL reconfigure + `test` for 404), an explicit "treat a final failed
`last_receipt` as a missed wake and run the full inquiry" sentence in the Delegator Skill, and
optionally a `missed_event_seq` fact on the next successful wake. No holder-side timer.

---

## Point 4 — coverage check: does every wake failure mode carry a route or a self-route?

| Failure mode | Receipt / record | Route attached? | Verdict |
|---|---|---|---|
| Delivery failure, retries exhausted (connection, 5xx, 400/408/429) | 4 `failed` rows, last `final: true` | `routes:77` / `:139` on every failed row | Route exists, but reaches a reader only via the cron fallback (G2) |
| Timeout (final on attempt 1) | 1 `failed` row | `routes:345` | Same caveat as above |
| 4xx final (401/403/404/other) | 1 `failed` row with redacted body | `routes:139` (generic) | Route exists; does not name key rotation / URL fix (G8) |
| Dedupe skip | `skipped`/`duplicate`, `result` in SUCCESS → not stamped | `routes:94` only if a reader looks it up | OK by design (not a failure) |
| Not configured / disabled | `skipped`/`not-configured`, not stamped | `routes:234-235`; `webhook-wake.md` self-configuration | OK |
| Invalid config / config mode | `failed` | `routes:181`, `:71` | OK |
| Invalid payload | `failed`/`invalid-payload` when project resolves; otherwise nothing | `routes:186` | OK when project resolves; **no record** otherwise (G4) |
| Redirect refused | `failed` final | `routes:270` | OK |
| Holder spawn failure | event `delegator_wake_spawn_failed` only | **none** | **Gap** (G4) |
| Death-recovery spawn failure | nested `sent: false, reason: spawn-failed` | **not stamped**; nearest row misleading | **Gap** (G4) |
| Death-recovery lock/log OSError | key omitted | **none** | **Gap** (G4) |
| Death scan record-root mismatch | `scan: incomplete`, no reason | **not stamped** | **Gap** (G4) |
| Holder dead, agent alive | `outcome: holder_lost` receipt from start/status | `routes:119` (exact-stop then resume) | Route exists for the caller; **no wake** (G3) |
| Receipt-write failure | nothing | **none** | **Gap** (G4) |
| Delegator-turn end unconsumed | nothing | **none** | **Gap** (G1) |

---

## Things I could not verify

- Live VRPCadCore evidence for #311 point 4 (receipts file, which `send` form and timeout the
  bridge used at 19:24/19:47/22:30, whether a seat had an active turn). The code analysis shows
  silence under both branches, so the conclusion does not depend on it.
- Whether real ACP agents (claude, codex, zcode) exit on holder death; G3's severity depends on
  it. The mock agent in the test does.
- `gh issue view --comments` was refused for a missing `read:project` scope; I read all issue
  bodies and comments through `gh api repos/:owner/:repo/issues/N` and `/comments` instead, so
  nothing was skipped, including the #311 comment of 2026-10-13T15:48:14Z.
- I did not run `./scripts/validate.sh` or any test (read-only task); test coverage statements
  come from reading the test files at this commit.
- KPM mirror issues (#123, #180, #181 on kaola-project-manager) were not read.
