# Issue #81 — Implementation & validation (M6/M7)

Candidate commit: `6d0002adf7a6c4aad783283eb161ea67dd51587a`
(`feat(zcode): native mid-turn steering via the v4 command surface (Issue #81)`).
Base: `18db64bbb96650621201e19be431def0e3b97559` — origin/main after the #85
sink (unchanged; #85's resume ordering preserved).
Candidate diff for independent review:
`evidence/candidate-6d0002adf7a6c4aad783283eb161ea67dd51587a.diff` (2676
lines). Supersedes `67ee287`, `01f6acc`, `8816309`, `e8359e8`, `a7e39c2`,
`0a4790e`, and `e09f9b9` (`67ee287`/`01f6acc`/`a7e39c2`/`0a4790e`/`e09f9b9`
NOT ACCEPTED — §4a/§4b/§4e/§4f/§4g; `8816309` needed the post-#84 rebase —
§4c; `e8359e8` needed the post-#85 rebase — §4d). Review-fix deltas:
`evidence/review-fix-67ee287-to-01f6acc.diff`,
`evidence/review-fix-01f6acc-to-8816309.diff`,
`evidence/review-fix-8816309-to-e8359e8.diff`,
`evidence/review-fix-e8359e8-to-a7e39c2.diff`,
`evidence/review-fix-a7e39c2-to-0a4790e.diff`,
`evidence/review5/review-fix-0a4790e-to-e09f9b9.diff`, and
`evidence/review6/review-fix-e09f9b9-to-6d0002a.diff` (139 lines: the
fail-safe budget knob plus its failure-first tests). Adapter-only delta:
`evidence/review6/adapter-delta-e09f9b9-to-6d0002a.diff` (36 lines).

## 1. What was implemented

`scripts/kaola-zcode-acp.py` — the existing `_session/steering` ACP method now
runs the proven v4 path on the existing transport (no second lifecycle,
scheduler, registry, retry loop, or stdin writer):

- Lazy `v4/conversation/subscribe{topic:conversation/<backend>, connectionId,
  clientMode:"desktop-continuous"}` on first steer — the live-proven
  configuration whose publisher emits steer events on `session/event`.
- `v4/command{commandId:"kpr-steer-<uuid12>", clientId, sessionId,
  type:"sendText", payload:{text, requestedDelivery:"guide",
  expectedTurnId?}, issuedAt}` — the per-command guide entry proven live (G1),
  with a per-turn `expectedTurnId` CAS when the running turn's id is known.
- `session.active_turn_id` is learned from `turn.started`'s params-level
  `turnId` on the existing event flow and cleared in `finish_turn`. It can lag
  the prompt acknowledgement on the backend reader thread, so the steer path
  waits a bounded 2 s for it before sending; a build that never reports it
  simply sends without the CAS — but then no queue/drain pair can ever be
  confirmed same-turn, so `injected` becomes unreachable (§4b).
- A per-session steer ledger (single in-flight; a second steer while armed is
  refused `-32000`) records `turn.steerQueued` / `turn.steerDrained` events,
  correlated by `inputId`/`queryId`/`intent.sourceCommandId` == our
  `commandId`, and — only when the admitted `pendingInputId` is a nonempty
  known id — `pendingInputIds`/`drainedInputs[].pendingInputId` equality
  (a `None == None` match never counts as ours, §4a).
- `finish_turn` sets `turn_ended` and wakes the ledger, so a turn boundary
  decides a pending steer instead of leaking it.

Outcome ladder (all decided by events, never by the ack — the measured trap
reports `result.delivery:"queue"` even for admitted guide input):

- `injected` — only when a matching `turn.steerQueued` and
  `turn.steerDrained` name the SAME `targetTurnId`, that id equals the turn
  the steer targeted (`expectedTurnId`, which must be KNOWN — §4b), the
  admission itself reported `guide` delivery (a `queue`/`admittedDelivery`
  admission can never be this turn's guide injection even when a drain names
  our message — §4e), AND a `messageId` provably belonging to THIS input —
  the `drainedInputs[]` item correlated by `pendingInputId` or exact
  `intent.sourceCommandId` — appears in `injectedMessageIds` (a batch that
  injected someone else's message is not our injection — §4e). Response
  includes `targetTurnId`, `pendingInputId`, `injectedMessageIds`.
- `queued` — `steerQueued` admitted `delivery:"queue"`, or a guide admission
  whose turn ended before the boundary. Durable: the text surfaces later.
- `written` — guide admission still pending when the 20 s drain window ends
  (live drains were measured ~50–70 s; the holder's steer timeout is 30 s, so
  the adapter cannot hold every response for the boundary — `written` is the
  honest "admitted for this turn, drain unobserved").
- `promptRequired` — no running turn (`idleBehavior:"promptRequired"` from the
  holder); nothing touches the backend.
- `unknown` — ack accepted but no steer evidence, a drain without its
  admission, a drain into a different `targetTurnId`, an empty or
  unattributable `injectedMessageIds`, a queue admission paired with a drain,
  a self-consistent queue/drain pair arriving while the backend never named
  the running turn (§4b), OR a `v4` call whose ack timed out / transport
  failed (§4e — the request may have been staged server-side, so the outcome
  is undecided and forbids a blind resend; `sendUncertain:true` marks the
  reply). Reasons name the exact gap.
- JSON-RPC `-32601` — a pre-0.16 backend lacking the v4 surface → holder maps
  `unsupported`. Explicit business rejections (`status:"rejected"`, or a
  definitive server-side error response) surface `-32000` with `reasonCode`
  in `data` → holder maps `rejected`. A timed-out / transport-failed `v4`
  call is NOT a rejection — it falls into the undecided path above.

`scripts/kaola-acp-holder.py` — `native:"queued"` maps to
`steer_outcome:"not_consumed"`, `steer_consumed:false`, error `steer-queued`,
`mutation_performed:true` (a durable admission, not a clean nothing-happened).
`written`, `promptRequired`, `unknown`, `unsupported`, `rejected` reuse the
existing #65 mappings unchanged. `--steer-mode interrupt` untouched.

`platforms/zcode.yaml` — `native_steering:"supported"`,
`acp_steer_method:"_session/steering"`, honest summary (ack trap, same-turn
requirement, queued/unknown/rejected/unsupported boundaries, interrupt
fallback). `CHANGELOG.md` entry under Unreleased. Generated Skills regenerated
through `render-skills.py --write` only.

## 2. Hermetic coverage (`tests/contract/`)

`fake-zcode-app-server.py` gained the v4 surface with live-verbatim shapes:
ack `{status:"accepted", result:{type:"inputAccepted", delivery:"queue",
inputId:<commandId>}}` — the trap preserved; `turn.steerQueued` /
`turn.steerDrained` payloads matching live field layout (`targetTurnId` inside
payload, `turnId` at params level on `turn.started`); the `expectedTurnId`
CAS enforced (`expected_turn_mismatch` rejection); scenarios `steer_guide`,
`steer_queue`, `steer_turnend`, `steer_xturn` (queued targets turn A, drain
names turn B), `steer_phantom` (adversarial: our queued omits `pendingInputId`,
an unrelated drain item also omits it yet names our turn with nonempty
`injectedMessageIds`), `steer_guide_nopid` (drain correlated only by
`intent.sourceCommandId`), `steer_noexpect` (adversarial: `turn.started`
carries no `turnId`, then a queue/drain pair agrees on a successor-turn id —
§4b), `steer_mixed` (adversarial: guide admission, then a drain batch holding
our input p1→m1 AND an unrelated p2→m2 while `injectedMessageIds` names only
m2 — §4e), `steer_qdrain` (adversarial: queue admission plus a same-turn
drain naming our messageId, both staged before the ack so the ledger holds
both — §4e), `steer_timeout_staged` (v4/command ack withheld entirely — a
client-side timeout — while a `steerQueued{queue}` had already been staged
server-side — §4e), `steer_timeout_silent` (ack withheld, no events — the
request may or may not have arrived — §4e), `steer_race_end` (the target
turn completes inside the subscribe ack — no successor — §4f),
`steer_race_replaced` (the target completes and a backend-side successor
`turn.started` arrives inside the subscribe — §4f), `steer_exit_staged` /
`steer_exit_silent` (the app-server process exits after a possibly-staged
command — §4f), `steer_slow_subscribe` / `steer_slow_exchange` (phases that
overrun the steer deadline — §4f), `steer_silent`, `steer_reject`,
`steer_unsupported`.

`test-zcode-acp-contract.py` — 21 adapter-level + 14 holder-level steer
tests, written failure-first (the phantom, noexpect, mixed, qdrain, both
timeout legs, both race legs, both process-death legs, both deadline legs,
and the process-death receipt were each re-verified red against the
respective pre-fix adapter — see §4a/§4b/§4e/§4f): injected only on the
full same-turn chain; `expectedTurnId` asserted on the wire and equal to
the drained `targetTurnId`; queue→not_consumed+mutation_performed;
turn-end→not_consumed; reject→rejected; silent→unknown; cross-turn
drain→unknown (never injected); missing-pending-id unrelated drain→never
injected; sourceCommandId-only drain→still injected; unknown turn identity
+ matched successor-turn pair→unknown (never injected), with the CAS-less
send asserted on the wire; mixed drain where only someone else's messageId
was injected→unknown (never injected); queue admission + same-turn
drain→unknown (never injected); lost ack + staged queue→`queued` result
(never an error); lost ack + silence→`unknown` result with
`sendUncertain:true` (never an error, never `rejected` at the receipt);
target ended before send→no `v4/command` on the wire and
promptRequired-style non-consumed result; backend-side successor→no
`v4/command` on the wire at all; expired deadline→command never sent;
process death→`queued`/`unknown`+`sendUncertain` and the receipt reads
`steer-undecided`, never `rejected`; `-32601`→unsupported;
idle→promptRequired with zero v4 traffic;
`stopReason:"end_turn"` preserved on the steered turn.

## 3. Validation results on the frozen candidate

All run on `6d0002a` (except the red runs, which ran against `0a4790e` and
`e09f9b9` by design — see §4f/§4g):

- `./scripts/render-skills.py --check`: PASS (9 workers + orchestrator +
  grok-bot bridge, budgets OK).
- `python3 -m unittest tests.contract.test-zcode-acp-contract`: **71 tests,
  ~190 s, OK** — 36 steer/knob tests (22 adapter-level + 14 holder-level)
  plus the static budget-parse table; the §4f and §4g legs were each
  verified red on `0a4790e`/`e09f9b9` first.
- `python3 -m unittest tests.contract.test-issue-84-zcode-native-resume`:
  **18 tests, OK** — the #84 merge is preserved intact.
- `python3 tests/contract/test-issue-85-zcode-resume-advertised-model.py`:
  **7 tests, OK** — the #85 fail-closed announce ordering is preserved.
- `python3 tests/contract/test-issue-74-kaola-delegator.py`: **151
  assertions, 0 failed** — #74 Delegator behaviour preserved.
- `./scripts/validate.sh`: **PASS, unmitigated, exit 0** — every suite OK,
  zero real FAILED/SKIPPED, zero residual processes in the final sweep (the
  log shows the 71-test contract suite plus the #74, #84, and #85 suites
  green inside it).
- `evidence/probes/backend-tee-fixture-test.py`: **49 checks, all PASS**
  (raw output: `evidence/review5/tee-fixture-output.txt`) — fake secrets
  planted in every would-be ID field, ID array, unknown field, and a
  stderr-shaped line can never appear in persisted tee JSON; whitelisted
  records carry only the finite field set with all IDs as SHA-256 hashes.
- `evidence/live6-adapter/` — **fresh byte-bound live proof on `6d0002a`**
  (re-run out of honesty although the §4g knob fix leaves default behavior
  byte-equivalent — `STEER_TOTAL_BUDGET` still resolves to exactly 26.0
  when the env override is unset). The integrated adapter itself, against
  real ZCode.app 3.12.3 in a disposable repo through the hardened backend
  tee, returned mid-turn `{outcome:"injected",
  confirmation:"agent-confirmed", pendingInputId:"queue_kpr-steer-34ce…",
  targetTurnId:"turn_c2b4…", injectedMessageIds:["msg_mu7j…"]}` and the
  model answered `STEERED-ADAPTER-81-OK`. Backend-level evidence in
  `live6-adapter/backend-tee.jsonl` + `backend-evidence.json` shows the
  real `v4/command sendText` → `turn.steerQueued` → `turn.steerDrained`
  chain correlated entirely by SHA-256 fingerprints — commandId, turn,
  pending-input, and text hashes all match end to end, all five
  cross-checks pass. Zero raw ids/text/stderr in the persisted tee (stderr
  → DEVNULL; unknown lines `{kind,bytes}` count-only). Adapter terminated
  cleanly; zero residual processes; no credential values persisted.
  (`live5-adapter/` remains as the equivalent proof on `e09f9b9`.)

## 4a. Outer-review fix — `67ee287` → `01f6acc` (NOT ACCEPTED → fixed)

Outer review of `67ee287` found a concrete false-positive path in
`record_steer_drained`: when the steerQueued event omitted `pendingInputId`,
the ledger's `pending_id` stayed `None`, and
`any(item.get("pendingInputId") == pending_id ...)` then matched an unrelated
drained item that also omits the field. With the same `targetTurnId` and
nonempty `injectedMessageIds` the adapter could report this steer `injected`.

Fix (the outer-specified minimal form): drain correlation now requires either
the exact `intent.sourceCommandId == command_id` on a drained item, or — only
when `pending_id` is a nonempty known id — a `pendingInputIds` /
`drainedInputs[].pendingInputId` match. `None == None` can never count as
ours; the same-turn/`injectedMessageIds` result ladder is unchanged.

Adversarial coverage added: `steer_phantom` emits our queued event without
`pendingInputId`, then an unrelated drain into our `targetTurnId` carrying
`injectedMessageIds` — pre-fix adapter reports `injected` (re-verified red:
the test was run against `git checkout HEAD -- scripts/kaola-zcode-acp.py`
and failed with `outcome:"injected"`); post-fix it is ignored and the honest
outcome is `queued`/`not_consumed`. `steer_guide_nopid` proves the fix does
not over-block: a drain correlated only by `intent.sourceCommandId` still
reports `injected`. Real v4 evidence and existing semantics untouched.

## 4b. Outer-review fix — `01f6acc` → `8816309` (NOT ACCEPTED → fixed)

Second independent finding on `67ee287` (still present in `01f6acc`): when
`turn.started` never yields a `turnId` inside the bounded 2 s wait,
`expected_turn_id` stays `None` and the `v4/command` is sent without the
`expectedTurnId` CAS — allowed by design (no hard gate). If the originally
running turn then ended and a successor turn received the guide input,
`steerQueued` and `steerDrained` could agree on that successor's
`targetTurnId` with nonempty `injectedMessageIds`, and the lenient clause
`(expected is None or drained_turn == expected)` reported `injected` — a
claim about the steered turn that the evidence could not support.

Fix (the outer-specified minimal form): `same_turn` now requires `expected`
to be KNOWN — a self-consistent queue/drain pair can never be confirmed
same-turn when the backend never named the running turn. The ladder reports
`unknown` with a reason naming the exact gap ("the backend never named the
turn running when the steer was sent, so the drain cannot be proven to
belong to the targeted turn"); `steer-undecided` preserves the
do-not-resend-blindly semantics and the result still discloses the drain's
`targetTurnId`. The send itself is unchanged — no gate added.

Adversarial coverage added: `steer_noexpect` emits `turn.started` without a
params-level `turnId`, then a queue/drain pair agreeing on a successor-turn
id (`<turn>_later`) with nonempty `injectedMessageIds`. Pre-fix adapter
reports `injected` (re-verified red: run against
`git checkout HEAD -- scripts/kaola-zcode-acp.py`, failed with
`outcome:"injected"`); post-fix the outcome is `unknown`, and the test
asserts the `sendText` really left without `expectedTurnId`. The normal
`steer_guide` injected path is unaffected — on 3.12.3 `turn.started` always
carries `turnId` (live-proven), so the CAS applies and same-turn injection
still reports `injected`.

## 4c. Post-#84 rebase — `8816309` → `e8359e8`, and byte-bound live proof

Outer review of `8816309` passed the 55 focused tests, renderer/diff-check,
and both false-`injected` fixes, but held ACCEPT because #84 changed the
same adapter. The worktree was rebased onto `f39d940` (origin/main tip =
verified baseline `8d7d00a` + the #84 archive-evidence commit). The adapter
auto-merged: #84's native-resume machinery (`session/messages` transcript
derivation, `push_account_config`/`select_account_model` resume path,
account-qualified model round-trip) and #74's Delegator-adjacent adapter
behaviour coexist untouched with the steer code — verified by
`test-issue-84` (18 tests) and `test-issue-74` (151 assertions) on the
rebased tree. The only conflict was `CHANGELOG.md` (resolved: #81 entry
first, landed entries following; `git range-diff` shows zero code delta).

Live proof byte-bound to the integrated adapter (the earlier `live/` and
`live2/` proofs were probe-script runs against the raw backend — not the
adapter): `evidence/probes/live-adapter-steer.py` drove
`scripts/kaola-zcode-acp.py` itself (worktree bytes = `e8359e8`) against the
real ZCode.app 3.12.3 app-server in a disposable repo
(`kaola-workflow/issue-81/evidence/live3-adapter/`):

- `session/new` → `session/prompt` on a turn built from eight short Bash
  calls (an injection boundary every few seconds — the earlier 40 s
  single-call loop only offered one boundary near its end).
- `_session/steering` mid-turn → adapter lazily subscribed v4, sent
  `sendText{requestedDelivery:"guide", expectedTurnId}`, and the backend
  admitted + drained it: result `{"outcome":"injected",
  "confirmation":"agent-confirmed",
  "targetTurnId":"turn_69a8d991-e287-43d6-b46f-87aa17b12da3",
  "pendingInputId":"queue_kpr-steer-ed41de502f6e",
  "injectedMessageIds":["msg_mu7ceg8v_5cf0e0e5-..."]}` — real backend-issued
  turn/message/queue ids that only exist because the adapter processed real
  `steerQueued`/`steerDrained` events. The ack's `delivery:"queue"` trap was
  not consulted (the outcome ladder never reads it).
- The model's reply chunks end with `STEERED-ADAPTER-81-OK` — the steer text
  was genuinely consumed mid-turn; `session/prompt` completed
  `stopReason:"end_turn"`.
- Teardown: `session/cancel` answered, adapter terminated, zero residual
  processes under the run's root; raw NDJSON contains no credential values
  (the only key-shaped matches are token-count field names).

Raw artifacts: `live3-adapter/raw-ndjson.jsonl` (full ACP traffic,
redaction-filtered) and `live3-adapter/report.json`.

## 4d. Post-#85 rebase — `e8359e8` → `a7e39c2`, and live-proof byte binding

#85 (accepted and sunk before this rebase) changed the same adapter: the
fail-closed resume no longer advertises the rejected model —
`hydrate_settings(session, announce=)` split into `announce_settings()`,
and the resume path now announces only after `reregister_provider`
establishes the selection. The worktree rebased onto `18db64b`; the adapter
auto-merged (only `CHANGELOG.md` conflicted, resolved as before). #85's
ordering and the #81 steer path coexist untouched — verified by
`test-issue-85` (7 tests) on the rebased tree.

Byte-binding of the live3 proof to this candidate (the outer's condition
for not re-running live): `adapter-delta-e8359e8-to-a7e39c2.diff` is the
complete adapter diff between the live3-proven `e8359e8` and `a7e39c2` —
exactly 3 hunks, +19/−3, all #85's resume-announce ordering
(`hydrate_settings` signature at ~L1282, `announce_settings()` at ~L1342,
the resume-path call ordering at ~L2082). None intersect the steering path
(`translate_event` ~L1419, `finish_turn` ~L1534, `record_steer_*`
~L1566–1608, `on_session_steering` ~L1610+, the expected-turn CAS ~L1769).
The steering production bytes are therefore identical between the two SHAs:
the `injected` verdict in `live3-adapter/report.json` binds to the steering
semantics at `a7e39c2` by construction, not by analogy — and `git
range-diff` (`review-fix-e8359e8-to-a7e39c2.diff`, 14 lines) shows the #81
patch itself changed only in CHANGELOG position. No live re-run was needed;
none is claimed.

## 4e. Outer-review fix — `a7e39c2` → `0a4790e` (NOT ACCEPTED → fixed)

The third independent review rejected `a7e39c2` on three concrete defects,
all in the outcome-decision layer:

1. **Mixed drain attribution.** `record_steer_drained` proved only that SOME
   drained item belonged to this steer; the ladder then trusted ANY nonempty
   `injectedMessageIds`. With `drainedInputs=[ours(p1→m1), other(p2→m2)]` and
   `injectedMessageIds=[m2]`, it reported `injected` — someone else's
   injection. Fix: the recorder now keeps the items that correlate by exact
   `intent.sourceCommandId` or a nonempty known `pendingInputId`, and stores
   `our_injected_ids` — the subset of THEIR `messageId`s present in
   `injectedMessageIds`. `injected` requires that subset nonempty; an empty
   subset falls to `unknown` with a reason naming that injected ids "name
   other inputs; no drained item's messageId is provably this input's".
2. **Queue admission must never report guide-injected.** The wait loop's
   early break on `admittedDelivery:"queue"` was racy — a drain already in
   the ledger took the drained branch, which never checked the admission's
   delivery. `injected` now additionally requires the admission to report
   `guide` (`intent.admittedDelivery` or top-level `delivery`); anything else
   yields `unknown` with a reason naming the delivery.
3. **ACK timeout / transport uncertainty was a false rejection.** Every
   non-`-32601` `RuntimeError_` — including `zcode call timed out:
   v4/command` — surfaced `-32000`, which the holder maps to
   `rejected`/`steer_consumed=false`, even though the server may already
   have staged `turn.steerQueued`. A timeout now sets `send_uncertain` and
   falls into the same event-evidence wait: a staged admission still reports
   `queued`; silence reports `unknown` with `sendUncertain:true` and a
   do-not-resend reason. A definitive error response (the server evaluated
   and refused) still surfaces `-32000`/`rejected`; `-32601` still maps
   `unsupported`. No retry, no second state machine. A new
   `STEER_TOTAL_BUDGET` (26 s) caps the whole exchange under the holder's
   30 s steer timeout so a 15 s send timeout can never push the reply past
   the holder's deadline.

**Failure-first (raw red preserved in `evidence/review3/red-a7e39c2.txt`)** —
all seven new tests failed on `a7e39c2` before the fix:

- `steer_mixed` → adapter `injected`, holder `steer_outcome:"injected"`
  (defect 1).
- `steer_qdrain` → adapter `injected`, holder `steer_outcome:"injected"`
  (defect 2 — the drain won the race against the early break).
- `steer_timeout_staged` / `steer_timeout_silent` → adapter `-32000
  "zcode call timed out: v4/command"`, holder `steer_outcome:"rejected"`
  (defect 3 — exactly the false rejection the review predicted).

Post-fix green: adapter `steer_mixed`/`steer_qdrain`/`steer_timeout_silent`
→ `unknown`, `steer_timeout_staged` → `queued` (+`sendUncertain`); holder
receipts → `steer_outcome:"unknown"`, `steer_consumed:null`,
`steer-undecided` — never `injected`, never `rejected`. Full suite: **62
tests OK**. #85's resume ordering preserved (7 tests OK). Because the fix
changed steering production bytes, a FRESH integrated-adapter live proof
was run — `live4-adapter/` (§3): real `injected` on `0a4790e` with real
`targetTurnId`/`pendingInputId`/`injectedMessageIds` and the model
consuming `STEERED-ADAPTER-81-OK`.

## 4f. Outer-review fix — `0a4790e` → `e09f9b9` (NOT ACCEPTED → fixed)

The fourth independent review rejected `0a4790e` on three reproducible P1s
plus an evidence gap:

1. **Turn-change race** — the expected-turn wait could learn a successor's
   `active_turn_id` after the original target ended, so `v4/command` went
   out with `expectedTurnId=<successor>` (or CAS-less). Fix: capture the
   target `turn_request_id` at steer entry; the expected-turn wait now also
   breaks when the target dies or a backend-side successor turn appears;
   immediately before send, `session.turn_request_id`/`active_turn_id` are
   rechecked and any mismatch aborts without sending — no text is ever
   addressed to a successor turn. Both shapes covered: ended-no-successor
   (`steer_race_end`) and backend-side successor (`steer_race_replaced`,
   where the fake emits `turn.started{B}` inside the subscribe because the
   adapter's synchronous dispatch means no second ACP prompt can arrive
   mid-steer).
2. **`STEER_TOTAL_BUDGET` applied only after prior phases** — subscribe
   15 s + turn-id wait + command 15 s could push the total past the
   holder's 30 s. Fix: one deadline computed at steer start; every phase
   (subscribe, expected-turn wait, command exchange, drain wait) receives
   only the remaining budget; the command is never sent after the
   deadline. `KAOLA_ZCODE_STEER_BUDGET` exists solely so hermetic tests can
   compress the deadline deterministically.
3. **App-server death after a possibly-processed command mapped to
   `rejected`** — backend death synthesizes `{"code":-32000,"message":
   "zcode app-server exited"}` through the same `slot["error"]` path as a
   business rejection. Fix: `BackendTransportError` distinguishes
   death/timeout/write-loss from explicit server rejection; transport loss
   now falls into the same event-evidence wait and resolves
   `queued`/`unknown`+`sendUncertain`, never `rejected`, never resent.
   Explicit `status:"rejected"`/definitive error → `rejected`; `-32601` →
   `unsupported`.
4. **Evidence gap → hardened backend tee** — earlier live proofs recorded
   the ACP wrapper, not the backend `sendText`/queued/drained chain.
   `evidence/probes/backend-tee.py` now interposes on `--zcode-node` and
   persists a strict finite whitelist only: event kind, `_sha256` ID
   fingerprints (arrays capped at 32 items, scalars at 4096 chars),
   finite `guide`/`queue` delivery enums, byte counts, and text hashes.
   Backend stderr goes to `subprocess.DEVNULL` — never forwarded, logged,
   or persisted; unknown JSON and non-JSON lines reduce to
   `{kind,bytes}` count-only. The fixture
   (`backend-tee-fixture-test.py`, 49 checks) plants fake secrets in every
   would-be ID field, ID array, unknown field, and a stderr-shaped line
   and proves none can appear in persisted JSON while the chain still
   binds commandId+turn+text end to end.

**Failure-first (raw red preserved in
`evidence/review4/red-0a4790e.txt`)** — all seven legs failed on `0a4790e`:
`steer_race_end`/`steer_race_replaced` sent `v4/command` after the target
ended (the replaced leg sent `expectedTurnId: turn_sess_fake1_1` — the
successor — exactly the reviewer's reproduction); both `steer_exit_*` legs
surfaced `'error'` where staged-queue must stay undecided; the slow-
subscribe leg sent after the deadline; the slow-exchange leg measured
`elapsed=31.06s > 30s`; and the holder receipt for process death read
`steer_outcome:"rejected"`. Post-fix: all seven green plus every
pre-existing leg — **69 tests OK**.

Because the fix changed steering production bytes, a FRESH
integrated-adapter live proof was run through the hardened tee —
`live5-adapter/` (§3): real `injected` on `e09f9b9` with the full
hash-correlated backend chain and the model consuming
`STEERED-ADAPTER-81-OK`.

## 4g. Outer-review fix — `e09f9b9` → `6d0002a` (NOT ACCEPTED → fixed)

The fifth independent review found the test-only env override
`KAOLA_ZCODE_STEER_BUDGET` was an unvalidated production input:
`KAOLA_ZCODE_STEER_BUDGET=invalid python3 scripts/kaola-zcode-acp.py
--help` crashed at import (`ValueError`, reproduced verbatim in
`evidence/review6/red-e09f9b9.txt`), and any value >30 s would defeat the
holder-safe 26 s deadline.

Fix — minimal, no new config layer: `_steer_budget_seconds(raw)` resolves
the override fail-safe. Invalid, non-finite (`nan`/`±inf`/`1e309`), and
non-positive input returns the 26 s default; any valid value is capped at
26 s so the total steer exchange can never outlive the holder's 30 s. The
compressed deterministic test path is unchanged (`=5` still works).

**Failure-first** — both new checks are red on `e09f9b9` (raw preserved):
`test_steer_budget_env_is_fail_safe_and_bounded` fails because
`_steer_budget_seconds` does not exist, and
`test_invalid_budget_env_still_starts_and_steers` fails because the
adapter process dies at import (`wait_result(1)` → `None`). Post-fix:
both green, and `invalid`/`nan`/`inf`/`-5`/`0`/`100`/`1e9` all exit 0 at
`--help`. The static table drives 27 hostile values through the parser
asserting every result is finite, positive, and ≤26 s — no value can
crash the module or exceed the holder budget.

Adapter delta (`evidence/review6/adapter-delta-e09f9b9-to-6d0002a.diff`,
36 lines) is exactly `import math` + the helper + the constant — the
steer-path semantics are byte-identical, and `STEER_TOTAL_BUDGET` still
resolves to exactly 26.0 at the real default. Per the review's own
criterion (behavior byte-equivalent for the actual default) the live5
proof carried over, but live6 (`evidence/live6-adapter/`) was run anyway
for an uncontested byte-bound proof on `6d0002a`: real `injected`,
full hash-correlated chain, model consumed the codeword. **71 contract
tests OK**, `render-skills.py --check` PASS, `validate.sh` PASS
unmitigated exit 0.

## 4. Environmental note (resolved by rebase, not by this diff)

Before the rebase, `validate.sh` failed at
`test-issue-49-grok-bot-host.py::test_content_stage…` — `OSError: [Errno 66]
Directory not empty: <tmp>/repo/.git` during `TemporaryDirectory` teardown.
Independently root-caused here before #80 landed: `git commit`'s detached
`git maintenance run --auto` child (`repack --write-midx`) outlives teardown
(`GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=gc.autoDetach GIT_CONFIG_VALUE_0=false`
→ 3/3 pass; reproduces with this entire diff stashed). Issue #80 fixed it in
the fixtures (`maintenance.auto=false`); #83 fixed the lane-abort masking;
#82 fixed the fixture holder residue the sweep was killing. On the rebased
candidate the unmitigated suite is green.

## 5. Boundaries kept

- No edits outside the #81 surface; `templates/grok-golden/` untouched;
  `skills/` only through the renderer; `kaola-acp.py`, `kaola-tmux.sh`,
  holder lifecycle unchanged.
- No scheduler/registry/retry/stdin-writer added; steer rides the existing
  backend connection and `session/event` stream.
- No credentials read, copied, logged, or persisted; no global/user ZCode
  config touched; no other worktrees/sessions touched.
- Not finalized, archived, or sunk — awaiting outer ACCEPT on `6d0002a`.
