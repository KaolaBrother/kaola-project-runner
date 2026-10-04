# #255 lifecycle closure — Opus consolidated agreement

Reviewer: Claude Code Opus (extra high), same joint design duty and native context.
Revision 2, 2026-10-04: integrates the four public-research reports and their Host verdicts,
the latest owner and Delegator decisions, and candidate `a090de20`.

This is a design agreement. It is **not** a final review PASS, authorizes no implementation
and accepts no candidate. No code, test, live actor, forge or ledger change was made for it.
The seven requirements and the final integrated outer and Opus review remain open.

**Delivery boundary.** This file governs. Earlier reports stay as sources and are superseded
where they differ: `sideagent-nodes-review.md`, `sideagent-nodes-agreement.md`,
`dispatch-ownership-agreement.md` (section 8 holds the return and reclaim check). The research
originals under `public-research/` are untouched. `review.md` is historical and unchanged.

## 1. Verdict

**I agree with the outer's consolidated design and with the owner's latest decisions.** The
research changes no direction. It supplies nine small rules worth stating, confirms most of
the design as standard practice, and names mechanisms that must not be copied. Three of my
own earlier statements are corrected (section 5). One design decision is still open
(section 10).

Until a supported adoption exists, the installed flow stays as it is.

## 2. What is fact, what is proposal

| Status | Scope |
|---|---|
| Implemented and unit-tested on `a090de20` (71 lifecycle checks; Host accepted it as a bounded repair, not final) | Keyed state records, verdict and attention (R7, R11), retirement with seats in every shape and handoff (R8), relay with exact turn-end and lost-end return (R10), one relay deadline (F17), Sideagent stop keeping its workers (R9), `rebind-host`, v1→v2 migration, `execute`/`collect` for research, QA and report |
| Native evidence, `42c3b83b` only, reusable only on unchanged behavior | Cancelled relay returned to the Host; direct Sideagent replacement; `rebind-host` keeping holder and agent; actual-shaped migration; exact stops with no residual. Hourly native timer configuration and two triggers |
| Observed on the installed flow during the research fan-out (not the candidate) | Host queried candidates, chose four Worker presets on four runtimes, dispatched through `execute`, collected, judged the originals, exact-stopped all four with no residual |
| Proposed here, not implemented | Node mode; Host-authored dispatch with core plus scope assembly; tool-written state link; per-seat disposition; deliverable facts; worker turn-end retention; implementation scope in `execute`; worker-keeping Host stop |
| Unverified natively | Survival of a child whose start is in progress; full tracked native and tool topology on both cleanup paths; an active tool through a rebind; the relay and R8 paths changed since `42c3b83b`; old-holder adoption; the candidate timer template; any cadence other than hourly; everything in node mode |

I read `a090de20` only through its delivery and Host verdict. Code lines cited in my earlier
reports are from `6610669c` and earlier.

## 3. The three boundary decisions

The owner and Delegator accepted A and B for final consolidation. They are restated here in
their final form; C is corrected.

### A. Implementation assignments through the same entry — scoped

- **Today.** `execute` accepts `research`, `qa`, `report` and refuses anything marked as
  mutation. Implementation work goes by direct `start` and `send` under `issue-dispatch.md`.
- **Decision.** One added implementation scope that does what the others do: start if
  absent, one send, index row, state link. The item carries its `task_id`; an issue number is
  optional.
- **Never.** No claim, worktree, ledger, finalize or forge action. The worker runs its own
  Workflow and keeps all of that.
- **One owner per issue** stays with the worker's Workflow claim. The tool adds no check.
  Read-only review and QA helpers for the same issue remain ordinary items.
- **No new validator.** Session naming stays Host policy. Write-path conflicts use the
  existing `resources` declaration.
- **Replaced together:** the scope list and refusal text in `dispatch-collect.md`; the act of
  dispatch in `issue-dispatch.md` (naming and one-issue-per-run stay); the Host-addressed
  direct start/send instructions for issue work; the tests asserting the refusal. Standalone
  Platform Runner use and degraded recovery stay direct.

### B. Host continuity keeps workers; default and final stop unchanged

- **Today.** A holder's stop sweeps the inner sessions its agent recorded. Only Sideagent
  roles are exempt, and no stop option says "keep workers". A ZCode Host writes no spawn
  lines, so its workers already survive; a spawn-record Host sweeps the workers it started.
- **Decision.** One explicit stop intent that keeps dispatched workers, used only by a Host
  `drain-restart` and by the stop that replaces or adopts a Host, dead-holder cleanup included.
- **Identity.** A worker is kept, adopted or stopped only by its `holder_instance_id`, proven
  by a verified spawn line or by the worker's own record naming this exact holder as
  dispatcher. The ACP session id and the native resume id are context facts and never stand in
  for it. A resumed context with a new holder does not show the old incarnation survived.
- **No continuation record is added.** Existing records already express a Host replacement:
  duties sit in state and belong to the Host role, each seat's `rebind-host` receipt names the
  old and new Host, and the worker's `dispatcher` stays historical.
- **Unchanged.** A stop without the intent behaves as today on every role. Final closeout
  reclaims each worker by its own exact stop first.
- **Limit.** The guarantee covers a worker whose start has returned its receipt.

### C. Recovery: who acts, with which existing command

No numeric threshold, no routine Host re-arm, no re-probing of a known hold. A cause is
cleared by its own evidence.

| State | Noticed by | Acts | Existing command or path |
|---|---|---|---|
| Start, relay, checkpoint or stop result unknown | Carrier | Carrier | Re-read record, receipts and state at the next existing boundary |
| Node stop unconfirmed or residual present | Carrier, one warning | Mechanical once the holder is gone and nothing remains; otherwise Host as an exception, or a restored controller | Runner `status`, `stop` with the expected holder |
| Node start refused by a local build or configuration fact | Carrier, one exception | A human fixes the install; the carrier re-reads that local fact at a later trigger | The start's own local pre-spawn decision; no service contact |
| Node start refused, or node turn failed, on an account or service condition (auth, quota, rate, adapter, service) | Carrier, one exception | Host applies the existing class rule: hold with evidence, binding `failed`; auth goes to the user. **Nothing is retried or pre-flighted while the hold stands** | `state update --kind holds`, `state update --section sideagent` |
| Resume after that hold | Host, or a restored controller on the direct path | Same runtime: lift the hold by its evidence, binding active again naming the failure. Other runtime: a new authorized recipe | `state retire --kind holds --evidence`, `state update --section sideagent` |
| Node ended with no checkpoint, a partial one, or its holder gone | Carrier | Those inputs become the Host's, once each, and are not sent to another node. New inputs still start a node | Existing Host-owned return |
| Role revoked or ended | Host write | Carrier stops the node and starts none | `state update --section sideagent` |
| Host busy | — | Nothing; events stay staged | — |
| Host dead or replaced | Delegator at inquiry | Delegator restores the one Host; successor re-anchors each seat by its recorded holder and adopts from index and receipts | Host recovery, B's stop intent, `rebind-host`, `collect`, `state check` |
| Worker start or send unknown | Tool, as `unknown` | Host re-runs the same plan, or a node reconciles | `execute` with the same index, `collect` |
| Worker return missed | Index still `in-flight` | Next node, Host pass or inquiry | `collect` |
| Worker stop unknown or residual | Node records it | Cleanup stays a duty; the seat is not counted free; the grant is untouched | Runner `stop`, `status` |
| Write conflict; old writer overwrite | State tool | Writer merges and retries; Host re-adopts | Exit 3; `state migrate`, `collect` |

"The same unresolved cause" is per input for a node that did not account for it, and per role
only for an account or service failure. A restored controller does not inherit a dead
carrier's memory; a binding left `failed` is the durable block. A business write never
touches the binding, so it resumes nothing and clears no hold.

## 4. Material corrections to the consolidated proposal

1. **Per-seat disposition is missing.** The verdict is one per task, and the index
   `acceptance` is only ever `pending`. The research run shows it: all four rows still read
   `pending` after the Host accepted them. The Host records, per assignment, accepted, repair
   or cancelled with the next duty: finalize, reclaim, or handoff. A cancellation names
   whether closeout comes first. A node stops a seat only on that record, by exact holder.
2. **No atomicity across index, state and external effects.** Within one file, identity and
   intent land in one write, and the index already publishes rows before any start. Across
   files and effects the rule is reconciliation: the state link is rebuilt from the index on
   every `collect` and `execute`. Only derived views are rebuilt (Host view, Delegator view,
   the task's dispatch and result link). State records, index rows and receipts are
   authoritative and are never regenerated or deleted as recovery.
3. **A missed worker wake.** A worker's turn-end event is not retained when the carrier is
   unreachable. Either retain and re-offer it on the worker holder's existing tick, as
   permission wakes are, or state the delay as up to one inquiry interval.
4. **Deliverable facts follow what was declared.** *Corrected from revision 1.* A deliverable
   may be a file, the capture itself, or a remote source. `collect` records the locator and,
   for a declared file, whether it is present. A missing declared file is an evidence gap
   shown with the returned item. It is not a transport failure, not a task failure and not a
   retirement gate; the Host judges. No item is required to declare a file. The Host view
   carries locators and status only; the stored reply excerpt stays out or is marked truncated.
5. **Inquiry needs one progress fact:** the last verified checkpoint in state, beside the open
   duties.
6. **Checkpoint truth.** A checkpoint that omits an input is partial and never recorded as
   verified complete. Covered inputs settle one by one; omitted ones stay unconfirmed and go
   to the Host. The Host-revision ack does not pass an omitted Host change.
7. **Pending predicate, stated once.** An input is pending for the node role when its Host
   revision is greater than the revision acknowledged by the last verified checkpoint.
   Tool-written facts never advance that revision, so a mechanical write cannot trigger a node.
8. **Contract and budget.** The scoped `AGENTS.md` exception still has to be written, and node
   guidance needs its own reference file.

Text to replace in one pass by the implementer: `design.md` §2, §4, §6, §7, §9;
`dispatch-collect.md` "Sideagent … picks count, exact presets, assignments";
`lifecycle-state.md` Roles, Sideagent binding and Events; the issue-body sentence "Sideagent
owns routine dispatch/collection/reclaim".

## 5. Material delta from revision 1 and earlier reports

Changed in this revision:

- **Table C.** Revision 1 let the carrier re-run `preflight` after any refused start. That
  could re-probe a known account or service hold. Now only a local build or configuration fact
  is re-read; an account or service cause is a hold and is left alone.
- **Correction 4.** Revision 1 said a missing `output` "keeps the item open" and asked for size
  and digest. Now it is an evidence gap on a returned item, tied to the declared deliverable.
- **Decision B** gains the explicit holder-identity rule and drops any need for a continuation
  record.
- **Corrections 2 and 7** are new wording from the research. Section 6 is new.

Withdrawn earlier and still withdrawn: the two-consecutive-failure bound; "any failed node
blocks until the Host rewrites the binding"; a partial checkpoint counted as complete; worker
identity matched on the Sideagent role name; worker preservation on every Host stop; "one
worker run per issue" as a tool rule.

## 6. Public research: borrow now, already covered, defer

Sources: `public-research/checkpoint-state.md` (LangGraph, two papers),
`durable-returns.md` (Temporal, Step Functions, outbox), `fanout.md` (Argo Workflows),
`reclaim.md` (Kubernetes, two papers), each with its retrieval notes and Host verdict. They
are analogies. None verifies the candidate.

**Borrow now.** Each is a rule or wording on existing fields, with one QA case. None adds a
store, a nonce, an enum or a stage.

| Rule | From | Lands in | QA case |
|---|---|---|---|
| The pending predicate; a bookkeeping write is not a new duty | LangGraph `versions_seen` and its bump guard | Correction 7 | A tool-only write starts no node; a crash between write and ack leaves the input pending |
| Two identities, named: transport or turn (event id, request id, prompt fingerprint, cursor) and assignment (item id; repo, preset, session, prompt hash; task revision). A replay attaches; a deliberate re-dispatch is a new item and needs its own authority | Temporal request id against Update id | Dispatch reference wording | Same send twice gives one row; the same assignment dispatched again gives a new row |
| Report the stage actually evidenced. An admitted send whose worker then died is not `not-run`; known effects stay, the rest is `unknown` | Temporal update stages | Status wording; existing row fields | Send admitted, state write lost: the row shows the start evidence and `unknown`, and reconcile completes it once |
| Ownership by exact incarnation | Temporal task-token trap; Kubernetes owner UID | Decision B | Same session name under another holder is not kept, re-anchored or stopped |
| Result received is its own fact, apart from process end and from acceptance | LangGraph pending writes; Argo `TaskResultSynced` | Corrections 1 and 4 | Process ended, no collected result: the item stays open; durable record alone gives no verdict |
| Results by locator, never inline; a declared file that is missing is a gap | Argo output size limit | Correction 4 | Capture-only item is valid; missing declared file shows as a gap and the Host can still judge |
| A cancellation carries its intent: closeout first, or reclaim now | Argo stop against terminate | Correction 1 | One of five cancelled: siblings untouched; stop requested is not seat free |
| A restored or migrated context does not re-perform an effect; a retry with a different target or text is a new action | ACRFence replay-or-fork | Recovery and migration wording; existing assignment identity | After migration an already-sent item is not sent again; a changed prompt is a new item |
| A stated durability boundary | LangGraph durability modes; outbox | Correction 2 | Context dies between effect and write: recovery reports unknown, not done and not absent |

**Already covered.** Corroborated; nothing to add.

- Durable record before any consumer (Temporal signals): the carrier logs before delivery.
- Reconcile by identity, never replace the whole file (LangGraph upserts): keyed records.
- Identity fixed before effects; a retry attaches (Temporal with-start, conflict policy).
- Settled is not "all replies arrived"; unstarted items stay accounted (Temporal, Argo
  `Pending`): `not-run` rows and the task's `wait`.
- Typed outcomes kept apart (Argo): `failed`, `unknown`, `not-run`.
- Missed events recovered at existing boundaries and the inquiry (Kubernetes resync, Step
  Functions heartbeat). No timer.
- Acceptance, occupancy and process survival are separate; a missing locator proves no stop
  (Kubernetes orphaning): R8 on `a090de20`.
- The current view excludes superseded records, which remain at their source (Mnemosyne).
- Adoption guarded by a fresh exact identity (Kubernetes controller refs): `rebind-host` with
  the expected holder.
- Late events refused against retired identities (Temporal): tombstones. They are capped at
  64; beyond that the index and receipts carry the identity.

**Defer or do not adopt.** Each would add a mechanism the owner excluded, or was narrowed by a
Host verdict.

- A behavioral-version stamp and a fixed drain window (LangGraph): no established need;
  schema id, holder features and task revision exist.
- "Maintenance may only propose" (Mnemosyne): the Sideagent and tools do record mechanical
  facts and apply recorded dispositions. Only business acceptance is the Host's.
- All dependents' evidence inline before retirement: it duplicates results. Keep resolvable
  pointers.
- Rebuilding everything from receipts, or a disposable index (Temporal replay).
- A "not ready" transport classifier and any attempt counter (Temporal).
- Prerequisite expression engines, fail-fast, parallelism schedulers, semaphores, wait queues
  (Argo). The Host owns dependencies.
- Owner graphs, finalizers, selector adoption, retry or drop cutoffs, resync timers
  (Kubernetes).
- A committed-transition log and projection store, conflict scopes (Mnemosyne); an analyzer at
  the tool boundary (ACRFence); TTL or prune tooling (LangGraph); a transaction store to force
  atomicity (outbox).

**What the fan-out itself showed** (installed flow, receipts in `public-research/`):

- The owner's sequence worked on the existing research scope across four runtimes, with exact
  stops and no residual.
- The plan declared neither `task_id` nor `output`. The index therefore holds no deliverable
  locator; the Host found each report by the name in its own prompt.
- `acceptance` is still `pending` on all four rows after the Host's verdicts.
- Three of four stored excerpts are exactly 480 characters, with no truncation mark in the row.
- One worker raised six permission requests in seven minutes, each answered by the Host.

## 7. Responsibility matrix, implementable form

| Boundary | Decides | Tool or carrier records | Needs building |
|---|---|---|---|
| Intake, change | Host | Task with its revision; Host-revision stamp | Stamp |
| Candidate query | Host, when useful | `project` candidates; unknown stays unknown | Nothing |
| Plan | Host: scopes, exact text, presets | Item identity before effects; task revision; prompt hash; declared deliverable | Core plus scope assembly; revision on the row |
| Start, send | Tool | Per item: admitted, not-run, failed, unknown, with the stage evidenced | State link; implementation scope (A) |
| Return | Worker supplies the original | Exact turn, holder, capture start, deliverable facts | `collect` to state; wake retention |
| Busy or idle Host | Host | Attention keyed to the locators | Digest over locators; pointers in the Host view |
| Judgment | Host, reading the original | Per-seat disposition and next duty, mirrored to the item | Correction 1 |
| Closeout | Host names it; Workflow owner does it | Linked receipts; no ledger copy | Nothing more |
| Reclaim | Node applies the recorded mandate end | Stopped under the recorded holder, no residual; otherwise open cleanup | Stop outcome on the assignment |
| Retire | Tool checks facts | Tombstone with source pointers, or handoff to a current task | Present on `a090de20` |
| Node | Carrier, mechanically | Batch, phases, verified or partial checkpoint | Node mode |
| Supervision | Delegator | Reads state; last verified checkpoint | Correction 5 |

Fan-out is this row set per item. A batch is settled when every item is resolved or handed to
a named continuing duty.

## 8. Smallest affected surfaces

- `scripts/kaola-dispatch.py`: `execute` (implementation scope, core plus scope assembly, task
  revision, state link); `collect` (state link rebuilt each call, deliverable facts); state
  tool (per-seat disposition, Host-revision and holder stamps, checkpoint action, pointer-only
  attention, two check codes).
- `scripts/kaola-acp-holder.py`: the carrier's node action; turn-end retention; the
  worker-keeping stop intent; one feature flag.
- `scripts/kaola-acp.py`: the stop intent on `stop` and inside `drain-restart`; the same rule
  on the dead-holder path.
- Guidance through `render-skills.py`: main Skill role sentences; `dispatch-collect.md`,
  `lifecycle-state.md`, `issue-dispatch.md`; one node reference with its budget entry; the
  Delegator inquiry reference.
- Project text: the scoped `AGENTS.md` exception; `design.md` and the HTML artifact;
  `docs/api.md`, `docs/conventions.md`, `docs/zcode-host.md`; CHANGELOG with the seat-restart
  statement.

Not needed: a queue, a timer, a ledger, a record kind, a writer role for the carrier, a
nonce, a lifecycle enum, a score, an approval step, a mandatory-artifact gate, or any numeric
retry policy.

## 9. Focused QA

Fixtures reuse the existing harnesses. Native runs are required where process ownership or
wake behavior is the claim. The QA cases in the section 6 table are part of this list.

| Scenario | Fixture | Native |
|---|---|---|
| Single dispatch; mixed Worker fan-out; partial admission | Sent text equals core plus scope; one row per item; re-run starts nothing twice | One implementation item and one research fan-out through the entry |
| Busy Host return; idle wake; missed wake | Staged until the Host's turn end; lost turn-end found by `collect` | Result returned while the Host works; Host woken with pointers only |
| Original instructions and results | No Sideagent-written text needed to wake the Host; truncation marked | Host reads the artifact, capture or remote source at the recorded locator |
| Multi-round repair | Existing R7 tests; a Host-written repair item | One real second round |
| Closeout and reclaim | Disposition gates the stop; finalize pending keeps the seat; residual keeps the duty; grant unchanged | Reclaim one finished seat while a sibling runs |
| Interleaved fresh nodes | A and B across three nodes; fixed batch; partial checkpoint; tool write starts no node | Two consecutive nodes on ZCode and on one other runtime |
| Permission, capacity, holds | Existing admission tests; a held role gets no start and no pre-flight across repeated triggers | Permission-wake delay measured on a permission-heavy runtime |
| Interrupted operation; migration | Each row of table C; index-to-state rebuild; existing migration tests | Abnormal stop during a child start: loss recorded and reconciled, including the Host's own `execute` when its turn is cancelled |
| Duplicate, late, old holder | Existing relay tests; stale node write refused; late event after retirement refused | — |
| Host replacement | Stop with the intent keeps workers by exact holder; default stop sweeps as before | Spawn-record Host and ZCode Host, then `rebind-host` with a tool live |
| Sideagent adoption | Old-holder tracked-group refusal | Disposable fixture |

Limits to carry into the report of those runs: native evidence so far is for `42c3b83b`; the
mid-start loss is evidenced and its cause is an untested hypothesis; the tracked topology and
an active tool through a rebind are unverified; timer evidence is the hourly configuration
only and stays separate; no cadence changes and no new timer.

## 10. Open decision and what is not established

**One design decision is open: who answers worker permission wakes in node mode.**

- Agreed so far: they go to the node, and the delay is measured.
- New fact: the fan-out showed one worker raising six in seven minutes. In node mode that is
  up to six cold starts for one worker, each blocking it meanwhile.
- The alternative inside existing mechanisms is to leave permission wakes Host-owned, as the
  installed flow does. That trades Host interruptions at its turn boundaries for fewer nodes.
- I recommend keeping the agreed route and letting the native measurement decide. It is the
  owner's and outer's choice, because it moves work between the Host and the Sideagent.

Not established:

- Whether any consumer relies on today's sweep during a Host replacement.
- Which start-refusal reasons are local facts and which are account or service conditions; the
  implementer must take this from the existing reason codes.
- The real cold-start cost per node and the added Host effort per dispatch.
- The exact guidance sentences decision A replaces.
- Anything in `a090de20` beyond its delivery and Host verdict.
