# Sideagent nodes — Opus agreement on the outer resolution (#255)

Reviewer: Claude Code Opus (extra high), same joint duty and native context. Written
2026-10-04. Agreement on `sideagent-nodes-final-reconciliation.md` only. No code, test, live
action, issue, ledger or design-file change. Nothing here accepts a candidate; the seven
requirements and the final integrated outer + Opus review stay pending.

**Later note, same duty.** `lifecycle-closure-agreement.md` is now the consolidated delivery
boundary and governs where it differs from this file. Superseded here: in 4A, "the carrier
confirms only the covered inputs" (a checkpoint with an omitted input is partial, never
verified complete); in 4B, the two-consecutive bound (withdrawn) and the role-wide block for
an unverified node end (now per input; only a typed service failure blocks the role). Source:
`dispatch-ownership-agreement.md` section 8.4 and the consolidated file, sections 3C and 4.

## 1. Verdict

**I agree with all five resolutions and with the I-3 adjustment.** I withdraw one item of my
own proposal (section 3). Three points are not yet implementable as worded through the
existing carrier and state paths; each has a named gap and a small correction (section 4).
None reopens the direction.

## 2. Agreed, as the outer wrote them

1. **I-1.** A sourced Host business write through the existing state tool is the trigger. The
   tool derives `host_revision`. It is acknowledged only by a verified checkpoint. A failed
   admission consumes nothing. A later concurrent Host write stays pending. No node per
   generic Host turn. Transcription of a named Host turn stays possible and is no longer a
   precondition.
2. **C-1.** The scoped `AGENTS.md` exception is authorized; no further owner question. The
   carrier builds the existing exact `start`/`stop` as an argument list, never shell text.
3. **I-4 / I-5.** Index locator in the recipe; node identity and result in the existing carrier
   records and the current checkpoint; one progressively loaded node reference that replaces
   the obsolete paragraphs.
4. **Identity.** Stable role name, new holder and native conversation per node, as a
   Sideagent-role convention only. Every stop, checkpoint, relay confirmation and late-write
   check binds the exact node holder.
5. **Checkpoint.** Explicit and source-correlated; end-turn is only the signal to inspect it;
   a task wait can complete a node while the task stays open; an omitted input is never
   silently acknowledged.
6. **I-3 adjustment.** No blanket "Host must rewrite the binding after any failed node".
   Uncertain actions close by reconciling receipts at existing boundaries. No repeated cold
   start against the same unresolved failure or a known hold. One explicit checkpoint
   reminder at most. Business writes never clear a hold.
7. **Adoption and QA.** The old-holder tracked-child limit, the R7–R11 mapping, measured
   permission latency with no bypass, and the added focused cases.

## 3. Withdrawn from my proposal

I proposed matching the record-backed worker identity on the Sideagent role's
`(platform, session, repo)`. **Withdrawn; the outer's exact rule is sufficient.**

- A node's stop can only sweep groups that node tracks: its own agent's descendants, plus
  lines in the session's spawn record.
- An earlier node's worker is never a descendant of a later node. On spawn-record platforms it
  is recognized by its own spawn line (pid, group, spawn time). On ZCode, with no spawn lines,
  a later node never tracks it at all.
- So "exact holder instance in the worker's recorded dispatcher" united with "verified spawn
  line" covers every reachable case. The role-wide match added nothing and did widen
  ownership.

One place still addresses by name alone: Runner `stop` takes the expected holder instance as
an option, not a requirement. The carrier and every recovery stop of the bound session must
pass it.

## 4. Remaining corrections

### A. Fixed-batch accounting and the Host-request ack need two tool-kept stamps

**Gap.** Resolutions 1 and 5 require a mechanical check of coverage links and of which Host
writes are acknowledged. Today a record carries `rev`, `source` (one value, overwritten) and
`writer` (role and session name only). Nothing records which Host write a record is waiting
on, or which node last touched it. With only that, a checkpoint can settle a batch by listing
any existing record, and a Host request can be acknowledged without its record being looked
at. Both are what resolution 5 forbids.

**Smallest adjustment** (state tool only; no queue, no new record kind):

- On a Host business write, stamp the record with the file revision (`host_rev`), and keep
  the file-level `host_revision` already agreed.
- On a Sideagent write, stamp the record with the caller's holder instance.
- The checkpoint carries an explicit input map: each batch input → one or more state record
  or index item ids, marked `applied` or `retained`. A bare file path does not count.
- Verification, all mechanical:
  - every event in the carrier's batch log appears in the map;
  - every record whose `host_rev` lies between the last ack and the batch's Host revision
    appears in the map;
  - an `applied` record bears this node's holder stamp; a `retained` record is currently open
    (task not done, decision pending, hold or alert present);
  - the checkpoint names this batch and this holder.
- **Ack value.** The Host revision read when the batch was selected, not the file revision
  at checkpoint time. That is what keeps a write made during the node pending. The checkpoint
  echoes the batch id the carrier issued, so the ack survives a carrier restart.
- **Omitted input.** Named in the single reminder. If still omitted, the carrier confirms
  only the covered inputs and hands the omitted one to the Host once. It is not cycled to
  another node, so one bad input cannot drive repeated cold starts.

**QA consequence.** Add: a checkpoint that omits one event; one that lists an untouched record
as `applied`; one for another batch; a Host write during the node; a failed node followed by
no further Host write. Expected: nothing unaccounted is confirmed, the ack does not move on
failure, the later write starts exactly one further node.

### B. I-3 needs its resume rule stated mechanically

**Gap.** The resolution says an explicit re-arm, when needed, uses "the existing lifecycle
recovery operation" that identifies cause, evidence and controller. No such operation exists
by that name, and the carrier cannot classify service faults. Left open, the implementer must
choose between two things the outer excludes: resuming on any next trigger, which becomes a
storm because the unacknowledged request is still pending, or my earlier blanket block.

**Smallest adjustment.** Four outcomes, each decided from receipts the carrier already holds:

| Outcome | Inputs | New nodes | Closed by |
|---|---|---|---|
| Uncertain: start, relay, checkpoint or stop result unknown | Retained | None while open | Receipts and records re-read at existing boundaries; verified completion continues with no Host turn |
| Stop unconfirmed or residual present | Retained | None; no competing writer | Holder gone and no residual, shown mechanically; one durable warning meanwhile |
| Node ended unverified: no checkpoint after the reminder, turn cancelled, holder gone | That batch to the Host once | Allowed for new inputs; a second consecutive unverified end blocks | — |
| Typed refusal or failure: start refused, turn failed | That batch to the Host once | Blocked | A Host-only binding write that names this failure's id and its evidence |

- The failure id is what the carrier puts in its durable warning. The binding write must
  repeat it exactly, so a re-arm proves the controller saw this failure. A binding write
  without it, and every business write, resumes nothing.
- The Delegator is not a state writer. Its route is the existing one: restore or direct the
  Host, or the direct tool path.
- Holds are untouched by any of this. The block is the carrier's; a hold is still lifted only
  by its own evidence.
- "Two consecutive" is my suggested bound; the outer may set another number. Without some
  bound, a flaky runtime costs one cold start per new input indefinitely.

**QA consequence.** Add: a stop that confirms late resumes automation with no Host turn; a
typed start refusal stays blocked across new events and across a Host business write; the
named binding write resumes it; the hold record is unchanged throughout.

### C. A child start still in progress is outside any preservation guarantee

**Evidence.** `repaired-live-qa-42c3b83b.md`, receipts 77, 78, 87, 91: a genuine ZCode Sideagent
was exact-stopped while a foreground public `start` was mid-flight. The child ended
`holder_lost`. The Sideagent's recorded child groups held only its own backend, and the stop
swept nothing. So the child was not lost through the tracked-group sweep, and the R9 identity
repair, though still required, would not have saved it. The tracked native/tool branch remains
natively unverified on both cleanup paths, as that report states.

**Smallest adjustment** (wording and one checkpoint rule, no new mechanism):

- State the guarantee as: a worker whose start has returned its receipt survives a node stop.
  A start still running does not.
- Normal rotation already stops only after a verified checkpoint and an idle turn, so a
  foreground start cannot be running. The node reference says: finish every dispatch command
  and hold its receipt before the checkpoint; never leave one running in the background.
- Under correction A, a dispatch item with no start receipt must be mapped `retained` as
  unknown. The next node or the Host reconciles it by exact session identity before any
  replay.
- An abnormal stop (revocation, urgent stop, failed node) may lose such a child. That is
  recorded uncertainty, not preservation.

**QA consequence.** The live A/B loop asserts workers crossing node stops only after their
start receipts exist. Add one abnormal stop during a child start: the child's loss appears as
an unknown item, is reconciled by identity, and is not blindly re-dispatched. Keep the native
tracked-group check (a dispatch running across a node end) on ZCode and one other runtime as
an open required item.

## 5. Evidence boundaries reconciled

- **Repaired live QA (`42c3b83b`).** Usable as native evidence for: cancelled relay returned to
  the Host; direct replacement confirmed only by the exact holder and turn; public
  `rebind-host` from a real replacement Host; actual-shaped migration. Not evidence for:
  tracked native/tool preservation, a dead Sideagent with a live worker, an active tool
  through a rebind, R10, any F17 bound, or any commit after `42c3b83b`. Its ZCode findings
  (no child-record variable, stale explicit Host overrides, wrapper build skew) are the
  constraints a carrier-run start must be tested against.
- **Native timer (`outer-native-timer-evidence.json`).** Shows the real hourly configuration
  and two hourly triggers. It does not show any other cadence, and its body is the current
  installed entry, not the candidate's locator sentence, so candidate template adoption and
  drift repair remain unevidenced. Nodes add no timer and change no cadence; this evidence
  neither supports nor constrains them.

## 6. The checks you asked for

| Check | Result |
|---|---|
| Same-name ownership widening | None after section 3. One name-only path to close: `stop` without the expected holder |
| Generic Host-turn trigger | None. The Host turn end is only where the carrier compares revisions |
| New queue | None. Host requests are per-record stamps, not a list |
| New timer | None. Liveness of the one active node and re-offer of an undelivered turn-end use the holders' existing 15 s tick |
| New ledger | None. Batch and phases in the carrier's existing event log; only the current checkpoint in state |
| Retry storm | Closed by A (an omitted input goes to the Host once) and B (typed failure blocks; consecutive bound) |
| Business write clears a hold | Not possible: resume needs the binding write naming the failure id; holds keep their own evidence rule |
| Implementable through existing paths | Yes, with the stamps in A and the resume rule in B |

## 7. Reconciled with the dispatch-ownership agreement

`dispatch-ownership-agreement.md` recommends that the Host author and select, the tool carry
instructions and result locators verbatim, and the Sideagent collect and reclaim. If the
outer adopts it, this agreement stands with these adjustments and no change of direction:

- **Triggers narrow.** There is no Host "dispatch request" for a node. The Host-write trigger
  remains for applying verdicts, reclaim, cancellation and owner constraint changes.
- **Tool-written facts are not Host business writes.** What `execute` or `collect` records on
  the Host's behalf must not advance the Host revision in correction A.
- **Nodes start no workers.** Correction C then describes the exception, not the routine. The
  same exposure moves to the Host stop, which today sweeps workers the Host started; the
  dispatch agreement names that change. The R9 code is still required and is reused there.
- **Coverage fits.** A returned-result event is covered by the locators `collect` writes under
  the node's holder stamp: a mechanical `applied` link, with no Sideagent-written result text.
- **Node prompt and reference.** A node is told to collect, reconcile, hold, warn and reclaim.
  It is not told to compose assignments or summarize results.

If the outer keeps Sideagent dispatch instead, sections 1–6 apply unchanged.

## 8. Not established

- Everything above is by reading and by the delivered reports. I ran nothing for this
  agreement.
- What ends a half-started child when its starter is stopped (receipts 77–91) is not isolated.
- `e602281a` and the uncommitted R9–R11/P3/F17 work have not had my delta review.
