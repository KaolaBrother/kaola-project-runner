# Durable returns & durable obligations — public-source research

Branch 1 of the #255 research fan-out. Question: how do mature durable-execution systems handle
asynchronous returns — busy/dead coordinator, at-least-once delivery, exact correlation, unknown
start/send, deduplication, replay — while keeping process/event completion separate from semantic
business acceptance? Primary source: Temporal official docs + `temporalio/temporal` server source;
comparison: AWS Step Functions task-token callbacks and the transactional-outbox pattern.
All retrievals, URLs, commits, and verbatim snippets: `durable-returns-sources.md` (same dir).
Access date 2026-10-04. "Evidence" below = read source/docs; "inference" = my mapping to KPR/KW.

**Headline:** Temporal converges on the same shape as the consolidated design — durable record
before any consumer, at-least-once + explicit dedup identities, process stages kept strictly
separate from business outcome. The most valuable borrowables are *vocabulary and boundary
sharpness* (named receipt stages; two distinct dedup layers; stable vs attempt-scoped correlation),
not machinery. One real mismatch found: Temporal's fail-fast attempt counter conflicts with the
design's "no arbitrary retry count" — borrow the named not-ready signal, not the number.

## Findings

### F1 — Signal = durable mailbox; record precedes any consumer (busy/dead coordinator)
- **Mechanism/evidence:** `service.proto` — a signal "results in a `WORKFLOW_EXECUTION_SIGNALED`
  event recorded in the history and a workflow task being created." Source
  `service/history/api/signalworkflow/api.go` (main, fetched 2026-10-04): handler appends
  `AddWorkflowExecutionSignaledEvent` to history inside the mutable-state update, then returns
  `CreateWorkflowTask` — the event is durable *before* any worker sees it. Docs: signals usable
  when "Clients don't depend on the Worker being available"; messages processed "in the order they
  were received" once a worker runs.
- **Fault addressed:** receiver busy/down/dead, or sender dies right after send — the message is
  held by the service, not by either process. Dead coordinator never loses what it already acked.
- **Fit:** exactly the design's "Worker return — tool receives event... Host verdict pending even
  if notice delivered" and "source receipts/index recover state". **Mismatch:** Temporal's
  durability is a central service; KPR's is an atomic file write at the tool boundary — same role,
  weaker ordering across concurrent writers.
- **Smallest borrowable idea:** define the receipt-of-record as the durable tool write; nothing
  downstream (notice delivery, Host liveness) may determine whether a return "exists".
- **Edge QA:** deliver a worker return while the Host seat is stopped → item must be pending-verdict
  after Host restart, without worker resend.
- **Class: already covered** (design states it; Temporal corroborates the shape is standard).

### F2 — Executor death: timeout → redelivery → replay from history (no in-memory recovery)
- **Mechanism/evidence:** tasks doc — every state-changing event schedules a Workflow Task; worker
  replays *entire history* to reconstruct state; crash → another worker picks up the task. Workflow
  Task Timeout default 10s exists "primarily... to recognize whether a Worker has gone down so that
  the Workflow Execution can be recovered on a different Worker." Stale responder gets NOT_FOUND;
  service already rescheduled ("threw away the result"). Workflow Task failure ≠ Workflow Execution
  failure: task failures retry forever, execution stays Open.
- **Fault addressed:** executor dies mid-handling; late/stale answer from a superseded attempt.
- **Fit:** dead Host/Sideagent/node → replacement rebuilds obligations from receipts/index —
  "replacement Host safely reanchors". Corroborates receipts-as-rebuild-source and the design's
  process-failure vs task-failure split.
- **Smallest borrowable idea:** any derived projection must be rebuildable from receipts alone —
  treat the projection as a cache, never the source.
- **Edge QA:** delete the derived index/projection in a fixture, rebuild from receipts, diff the
  resulting open-duty set — must be identical.
- **Class: already covered**; adds a cheap invariant test.

### F3 — Two distinct dedup layers: transport-retry id vs business idempotency key
- **Mechanism/evidence:** handling-messages doc — retried client calls deduped automatically by
  `request_id` (proto comment: "Used to de-dupe sent signals"); Updates additionally deduped
  server-side by caller-settable Update ID; Signals have **no** server business dedup — "use a
  custom idempotency key that you send as part of your own signal inputs". Loyalty guide:
  "Temporal delivers Signals at least once."
- **Fault addressed:** (a) mechanical retry duplication — caller can't tell if first attempt
  landed; (b) semantic duplication — two genuinely different calls carrying the same business
  intent.
- **Fit:** design's "undelivered or duplicate notices... exact assignment/turn/revision binding".
  **Mismatch:** KPR must implement both layers at the tool apply boundary; no service does it.
- **Smallest borrowable idea:** name the two layers separately — a per-send nonce that dedupes
  transport retries, versus the stable assignment/revision identity that dedupes business
  resubmission. Same id must not serve both: a deliberate re-dispatch *should* create a new item.
- **Edge QA:** (a) replay the identical send → mechanically deduped, one item; (b) resubmit the
  same assignment as a new dispatch → new item bound to new revision, old dedup cannot suppress it.
- **Class: borrow now** — design implies the distinction; making it explicit prevents a common
  conflation bug (treating a retry as a new dispatch, or a new dispatch as a retry).

### F4 — Staged request lifecycle: Admitted / Accepted / Completed / Rejected — vs business verdict
- **Mechanism/evidence:** SDK enum docs — ADMITTED = "admitted by the server... does not wait for
  any sort of acknowledgement from a worker"; ACCEPTED = "passed validation on a worker" (and is
  persisted into history); COMPLETED = handler executed. On timeout the server "returns actual
  stage reached" — honest partial readback. Source `updateworkflow/api.go`: not running → same
  Update ID re-`Find`s the recorded outcome (`Noop`) — replayed request sees the *same* result.
- **Fault addressed:** a receipt that doesn't say *how far* the request actually got — "received"
  vs "durable obligation recorded" vs "handler finished" are different facts with different
  recovery duties.
- **Fit:** maps 1:1 onto the design's chain — send receipt (admitted) → tool-recorded durable item
  (accepted) → worker processed return (completed) → **Host verdict (semantic acceptance — a stage
  no transport can produce)**. Temporal even hard-separates Rejected (validator) from failure.
- **Smallest borrowable idea:** receipts name their stage explicitly; an interrupted operation
  reports the actual stage reached, never the stage requested.
- **Edge QA:** fixture where send returns transport-OK but the durable item write crashed → must
  read back as "unknown/failed", not admitted; reconcile then completes it once.
- **Class: borrow now (vocabulary refinement)** — design has "admitted, not-run, failed or unknown";
  Temporal shows the accepted-vs-admitted gap is where most reconcile bugs live.

### F5 — Exact correlation: pin to the incarnation, not just the business ID
- **Mechanism/evidence:** `updateworkflow/api.go` — request may carry `firstExecutionRunId`;
  mismatch → `ErrWorkflowExecutionNotFound` (same Workflow ID, different chain → refused, not
  silently applied). Async completion accepts Task Token (unique *per attempt*) or Activity ID +
  Workflow ID; doc warns retries invalidate tokens — recommends the stable identity across crashes.
- **Fault addressed:** late/duplicate write landing on the wrong incarnation of the same logical
  task; a token captured before a crash pointing at a dead attempt.
- **Fit:** "stale events cannot settle the new task/holder or resurrect retired duties."
- **Smallest borrowable idea:** every cross-crash correlation value = durable stable identity
  (assignment + revision + current holder/attempt). Attempt-scoped tokens only *inside* one live
  turn; the reconcile path always re-derives them from stable identity.
- **Edge QA:** revive an old holder and let it emit a late write under the same assignment id →
  rejected/ignored with evidence; the current attempt's obligations untouched.
- **Class: borrow now (sharpening)** — the "attempt-scoped token dies on retry" failure mode is a
  named, documented trap worth stating in the design's crash-between-effect-and-write row.

### F6 — Unknown start/send: atomic with-start vs non-atomic + reconcile-by-identity
- **Mechanism/evidence:** sending-messages doc — Signal-With-Start **is** atomic (exists → signal;
  absent → start + signal, one op). Update-With-Start is **explicitly not**: "If the Update can't
  be delivered... a new Workflow Execution will still start. The SDKs will retry... no guarantee."
  Reconcile = same Update ID attaches to the existing Update; design-patterns doc: use "a stable,
  business-meaningful updateId when you want a retried Update-with-Start to attach... instead of
  starting duplicate work."
- **Fault addressed:** crash between start and send — did it happen? Naive retry duplicates.
- **Fit:** "record intent first, reconcile exact target and receipt; never assume absence proves no
  previous mutation." Temporal's answer: even where atomicity exists, the stable ID chosen *before*
  the external effect is what makes reconcile an attach instead of a duplicate.
- **Smallest borrowable idea:** keep the item/assignment identity minted before any external effect
  and treat "attach to what exists" as the canonical retry — exactly the design's rule; Temporal
  confirms a mature system ships the non-atomic variant and reconciles the same way.
- **Edge QA:** kill between holder-start and send-write → reconcile finds the started holder +
  recorded intent, completes the send once; no second holder, no second item.
- **Class: already covered** — strong corroboration, including the honest non-atomic case.

### F7 — Idempotent start: uniqueness constraint + conflict policy
- **Mechanism/evidence:** workflowid-runid doc — at most one Open execution per Workflow ID;
  ConflictPolicy FAIL → "Workflow execution already started", USE_EXISTING → returns the existing
  Run ID; ReusePolicy governs closed IDs. `request_id` on start dedupes retried start calls.
- **Fault addressed:** double-start from retry/double-submit.
- **Fit:** "one issue has one implementation/Workflow owner"; USE_EXISTING = attach semantics for
  adoption/recovery of a live seat.
- **Smallest borrowable idea:** the "already exists" path should *return the existing identity*, not
  just fail — adoption flows reuse it.
- **Edge QA:** dispatch same item twice → second call resolves to attach/observe of the first.
- **Class: already covered.**

### F8 — Separate the notify channel from the result channel (failure-retry asymmetry)
- **Mechanism/evidence:** activity-execution doc's own guidance — if the external system's notify
  step fails silently under async-completion, retry waits out the *long* Start-To-Close (a week in
  their example); a short-timeout notify + Signal return channel retries in a minute.
- **Fault addressed:** binding the wait-for-result to the same unit as the dispatch/notify makes a
  failed notify invisible until the whole return window expires.
- **Fit:** design already splits dispatch item vs return event vs verdict. This is the named fault
  that split prevents.
- **Smallest borrowable idea:** the dispatch/notify leg should fail visibly on its own short
  boundary, independent of how long the worker may legitimately take to return.
- **Edge QA:** holder accepts the send but dies before producing a turn → item shows
  failed/not-run at the send boundary promptly, not "waiting" until a global deadline.
- **Class: already covered;** the failure mode is worth quoting when the design is challenged.

### F9 — Stale-token trap: volatile correlation survives a crash boundary
- **Mechanism/evidence:** activity-execution doc — "an Activity might fail after passing its
  current Task Token to a remote service, but before returning the complete async error, leaving
  that service with a Task Token that's no longer valid." Fix: hand over Activity ID + Workflow ID.
- **Fault addressed:** crash between handing a correlation value to a remote party and recording
  the intent → the remote holds a key that decodes to nothing.
- **Fit:** KW "crash between effect and state write" — same row, documented trap.
- **Smallest borrowable idea:** audit every value passed across a holder boundary: if it would be
  invalid after one retry/restart, pair it with the stable assignment identity or replace it.
- **Edge QA:** crash after "hand locator to holder" but before "record intent" → restart reconcile
  must resolve the holder by stable identity, not by any ephemeral handle.
- **Class: borrow now (audit checklist item)** — cheap, concrete, matches an existing design row.

### F10 — Settled ≠ all replies arrived: wait on *obligations*, not arrivals
- **Mechanism/evidence:** handling-messages doc — await `AllHandlersFinished` before completing/
  continuing; Abandon policy leaves waiting Update clients with NotFound errors.
- **Fault addressed:** unit completes while in-flight handlers still owe someone an answer.
- **Fit:** "A batch is settled when every item is resolved or explicitly handed to an identifiable
  continuing duty, never merely when all replies arrive." Identical rule.
- **Smallest borrowable idea:** deliberate abandonment still needs a recorded disposition *because
  someone may be waiting on it* — an abandoned in-flight duty must produce an explicit verdict/
  handoff, not silence.
- **Edge QA:** cancel one fan-out item whose result another duty awaits → explicit cancelled
  verdict recorded; the awaiting duty sees it, not a dangling wait.
- **Class: already covered;** the waiting-party consequence is a nice sharpening to state.

### F11 — Fail the *request* fast when the target is stuck (no counter transplant)
- **Mechanism/evidence:** `updateworkflow/api.go` — `WorkflowTaskAttempt >=
  failUpdateWorkflowTaskAttemptCount` → `NewWorkflowNotReady("Unable to perform workflow execution
  update due to Workflow Task in failed state")`. The update call fails; the workflow is unharmed.
- **Fault addressed:** pushing requests into a persistently failing target silently queues them
  and delays feedback; a stuck target should reject new work fast with a named condition.
- **Fit:** design's "concrete warning and recovery route; do not repeatedly cold-start for the same
  unresolved cause." **Mismatch:** the design explicitly forbids new numerical policies — borrow
  the *signal* (not-ready surfaced at the send boundary), not the attempt-count threshold.
- **Smallest borrowable idea:** when existing evidence already marks a target persistently failing,
  the send receipt should carry a named "target not ready" failure instead of a silent queued
  state — reusing existing failure marks, not a new counter.
- **Edge QA:** wedge a holder (simulated repeated task failure) → next send is receipted
  failed/not-ready with the existing evidence; no unbounded queue, no invented retry budget.
- **Class: borrow now (signal only) / defer the mechanism** — the counter itself is a design-rule
  conflict.

### F12 — Bounded dedup & mailbox state
- **Mechanism/evidence:** `registry.go checkTotalLimit` — FailedPrecondition when total updates hit
  the cap, message literally advising "duplicate updates share an Update ID so the server can
  deduplicate them"; docs: ~2,000 updates/run, SuggestContinueAsNew at 90%; loyalty guide bounds
  `processed_event_ids` to ~last 1,000 + external store.
- **Fault addressed:** dedup bookkeeping itself growing unbounded inside the same record space as
  live state.
- **Fit:** "durable attention coalesced by actual result revision" bounds growth; history stays at
  source.
- **Smallest borrowable idea:** dedup/attention sets are bounded and keyed to live items; retired
  items' dedup entries retire with them (history remains in receipts).
- **Edge QA:** N repeated returns under one item → one duty; dedup footprint bounded regardless
  of N.
- **Class: already covered** (bounded by design); exact numeric caps are a defer-by-irrelevance.

### F13 — Comparable system: Step Functions `.waitForTaskToken` — same convergent pattern
- **Mechanism/evidence:** AWS docs — task emits a token (`$$.Task.Token`) and pauses; external
  system calls `SendTaskSuccess`/`SendTaskFailure`/`SendTaskHeartbeat` with the token; default wait
  unbounded to a 1-year quota, `HeartbeatSeconds` recommended so a missing callback fails as
  `States.Timeout`. Token restricted to same-account principals.
- **Fault addressed:** async external completion — correlation token + explicit completion call +
  liveness bound on the wait.
- **Fit:** convergent validation of "durable wait + correlated return + bounded staleness route".
  **Mismatch:** token-only correlation — Temporal itself documents why stable identity beats it
  across retries (F9).
- **Smallest borrowable idea:** every durable wait needs a bounded staleness/liveness route —
  KW's is the existing Delegator inquiry + stale-duty evidence, not a per-item timer.
- **Edge QA:** worker dies mid-task → next inquiry surfaces the stale duty within its cadence,
  with identity and evidence intact.
- **Class: already covered** (second mature-system corroboration).

### F14 — Transactional outbox: intent and state in *one* atomic write
- **Mechanism/evidence:** microservices.io pattern page (literature/design claim, not measured) —
  message stored in the DB in the same transaction as the business update; relay publishes
  at-least-once; "a message consumer must be idempotent, perhaps by tracking the IDs of the
  messages that it has already processed"; relay can double-publish after crashing between publish
  and record.
- **Fault addressed:** state committed but intent never recorded (or vice versa) — the
  write-then-effect gap.
- **Fit:** design's "record intent first" — the outbox's sharper form is *atomically with* the
  state change it motivates. For a file-based state tool: one write carries both.
- **Smallest borrowable idea:** wherever an external effect is motivated by a state change, the
  intent marker and the state stamp land in the same atomic write — never two sequential writes.
- **Edge QA:** crash-injection fixture between "state updated" and "intent written" → on recovery,
  presence of the state change must imply presence of the intent; no orphan effect.
- **Class: borrow now (wording check)** — verify the implementation's "intent first" is actually
  "intent atomically with", not a separate earlier write that can itself be lost.

## Negative / notable findings

- **Temporal punts on signal business-dedup entirely** — docs say use your own key in the payload.
  Even the mature system leaves semantic dedup to the application boundary; KPR's tool-boundary
  dedup is not a gap.
- **Update-With-Start ships knowingly non-atomic** — documented, warned, reconciled by stable ID.
  "Intent + reconcile" over "pretend atomicity" is the field-proven pattern.
- **Rejected validator updates leave zero workflow trace** — opposite pole from KPR's explicit
  per-item failure receipts. Temporal hides rejection from *workflow state* but still reports it to
  the caller; KPR correctly wants the rejection fact recorded. Different need, compatible.
- **Signal ordering = "order received" per workflow** — relies on a single receiver loop. KPR has
  multiple concurrent writers and *no* global arrival order — ordering must come from recorded
  revisions/stamps, never arrival. Already the design's rule; worth flagging as the one place an
  arrival-order assumption would silently break.
- **Dedup scope is per-run; Continue-As-New drops it** — Temporal tells you to carry
  `processed_ids` + `pending_events` across the boundary yourself. Analog: handoff/reopen of a task
  must explicitly carry unprocessed inputs to the new owner — design's "explicit continuing
  owner/handoff" + node input-coverage check already does this; corroborated.
- **Late signal to a closed workflow → `ErrWorkflowCompleted`** (source-verified), while a repeated
  update on a closed workflow *attaches to the recorded outcome*. Borrow nuance: a late duplicate
  return on a retired/settled task should resolve to the recorded verdict (idempotent read), while
  a late *new* event on a retired task is an explicit conflict — two different terminal policies.

## Classification summary

- **Borrow now:** (a) named staged receipts — transport-admitted / durable-recorded / processed /
  business-verdict — plus "report actual stage reached" on interruption (F4); (b) explicit two-layer
  dedup — transport nonce vs business identity (F3); (c) stable-vs-attempt-scoped correlation audit
  (F5, F9); (d) intent-atomically-with-state write (F14); (e) named "target not ready" send failure
  reusing existing evidence, *without* a counter (F11); (f) terminal-duplicate attach semantics —
  return recorded outcome vs explicit conflict (negative findings).
- **Already covered (corroborated):** durable-record-before-consumer mailbox (F1), rebuild-from-
  receipts (F2), stable identity before effects + reconcile-by-attach (F6, F7), separate notify and
  return channels (F8), settled≠arrivals + recorded disposition for waits (F10), bounded coalesced
  attention (F12), bounded staleness route via existing inquiry (F13).
- **Defer / mismatch:** numeric attempt thresholds (F11 mechanism — conflicts with "no arbitrary
  retry count"); exact numeric dedup caps; any central-service semantics — all KPR equivalents must
  remain boundary mechanics on the existing receipts/index, not new infrastructure.

## Sources

Primary: docs.temporal.io pages `tasks`, `handling-messages`, `sending-messages`,
`encyclopedia/workflow-message-passing`, `activity-execution`, `workflow-execution/workflowid-runid`,
`design-patterns/*` (current docs, accessed 2026-10-04); temporalio source
`service/history/api/signalworkflow/api.go` (main, fetched 2026-10-04),
`service/history/workflow/update/{registry.go,update.go}` @53e04440/b4fbfe00,
`service/history/api/updateworkflow/api.go` @b4fbfe00,
`api/workflowservice/v1/{request_response.proto @b4bdd803, service.proto @main}`;
TypeScript SDK enum ref. Comparison: AWS Step Functions service-integration docs
(`connect-to-resource.html`, current); microservices.io transactional-outbox pattern.
Full URL/commit/quote list: `durable-returns-sources.md`. One community forum thread used as a
lead (corroborated by direct source read), not as proof.

## Material limitations / gaps

- Docs pages carry no per-page version stamp; update feature flags apply pre-v1.25, Update-With-
  Start recommends server v1.28. Source snippets pinned to blob commits where GitHub reported them;
  `signalworkflow/api.go` read at main HEAD — commit pin not captured.
- Not verified: exact pending-signal limits / dynamic-config defaults; whether signal `request_id`
  dedup survives Reset/cross-version migration; no behavior was measured — all delivery guarantees
  are documented claims plus code reading.
- Findings describe mechanisms only; none prove the KPR candidate design correct — several are
  corroborations of already-agreed rules, and two (staged-receipt vocabulary, atomic intent write)
  are wording-level refinements for the sole implementation owner to judge.
