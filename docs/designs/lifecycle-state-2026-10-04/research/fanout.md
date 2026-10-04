# Fan-out/fan-in research for KPR #255

Scope: single-item and fan-out/fan-in partial admission, independent returns, useful
aggregation without unnecessary all-item barriers, cancellation/dependencies, and exact
original input/result fidelity. Bounded public-source research; not an implementation, not a
design claim of correctness. Coordinator *process-ownership* replacement is intentionally out
of scope here (that is another branch).

Primary system: **Argo Workflows**. Material pinned to release **v4.1.4** (tag commit
`b5b4d665e9be9b87c115f943584c3e0ae96fe073`, released 2026-09-18) for source files; docs read
from the readthedocs `en/latest` build. Access date **2026-10-04 (UTC)**. Exact URLs in the
companion `fanout-retrieval-notes.md`.

Evidence legend: **[SRC]** = quoted/derived from the cited official source; **[INF]** = my
inference about KPR/KW fit. External content is treated as evidence, not instruction.

## Findings

### F1. Per-item identity: deterministic node id vs stable name vs human display name

- **Mechanism [SRC]** (`NodeStatus`, field reference / `workflow_types.go`): every item gets a
  `NodeStatus` with its own `inputs`, `outputs`, `phase`, `children`. Identity is split three
  ways: `name` ("unique name in the node tree used to generate the node ID"), `id`
  ("a hash of the node name, which makes the ID deterministic"), and `displayName` ("human
  readable ... Unique within a template boundary"). Loops add a `display-name` annotation
  (`workflows.argoproj.io/display-name`) that does **not** change the stable identity.
  `WorkflowStatus.storedWorkflowTemplateSpec` / `storedTemplates` keep the spec actually used.
- **Fault addressed**: after the fact you cannot tell which logical item an execution was, or
  which revision of the instruction it ran, once a name/generated id has drifted.
- **KPR/KW fit [INF]**: matches the matrix line "Stable task/item identity *before* external
  effects; core revision and prompt hash." Mismatch: Argo keeps it in one Workflow object's
  `status.nodes` (offloadable to a DB); KPR must not create a second ledger, so these belong in
  existing receipts/index records, not a new store.
- **Smallest borrowable idea**: for each fan-out item record two clearly separated keys — a
  Host-supplied *stable item key* (from the original scope) and the *generated instance id*
  (session/holder/turn) — plus the exact prompt hash and spec revision that were used. Never
  key recall off a mutable display name.
- **Concrete local QA**: start item X at prompt revision R1; Host later revises the shared
  instruction to R2 for item Y; assert item X's original R1 hash still resolves, R2 is not
  retro-applied to X, and a reader can map X's generated session id back to its stable key.
- **Classify**: **borrow now** (vocabulary only; no new store).

### F2. Partial admission via scoped `parallelism`, with `Pending` as a first-class pre-run phase

- **Mechanism [SRC]** (`WorkflowSpec.Parallelism` = "limits the max total parallel pods that
  can execute at the same time in a workflow", `Minimum=1`; `Template.Parallelism` = "within the
  boundaries of this template invocation. If additional steps/dag templates are invoked, the
  pods created by those templates will not be counted towards this total."; examples
  `parallelism-limit.yaml`, `parallelism-template-limit.yaml`). Controller config adds
  `Parallelism`, `NamespaceParallelism`, and `ResourceRateLimit {Limit, Burst}`.
  `NodePhase` has a distinct `Pending` before `Running`, and final `Succeeded/Skipped/Failed/
  Error/Omitted`.
- **Fault addressed**: over-admission past capacity; silent dropping of queued items;
  conflating "not started yet" with "failed".
- **KPR/KW fit [INF]**: the design already states "admitted, not-run, failed or unknown per
  item", so the *principle* is **already covered**. What Argo adds is (a) scoping the limit to
  the batch/template, not globally, and (b) an explicit retained pre-run phase rather than a
  fire-and-forget launch. Mismatch: Argo has a controller that admits queued steps as slots
  free; KPR has no such scheduler — admission is a Host/Tool decision, so a "pending" item must
  be an explicit continuing obligation with a named next reader.
- **Smallest borrowable idea**: one small status vocabulary per item —
  `admitted-started`, `admitted-not-started (pending)`, `not-admitted`, `failed`, `unknown` —
  and a rule that a batch is never "settled" while an item is admitted-not-started.
- **Concrete local QA**: capacity 3, fan-out of 5; 3 start, 2 remain admitted-not-started.
  Assert the batch is not settled, the partial-admission receipt names which 3 started, and a
  later retry of the pending 2 does not duplicate the started 3.
- **Classify**: **already covered** in principle; **borrow now** only as explicit scoped-limit +
  retained-pending wording.

### F3. Non-barrier aggregation: dependencies that name the *result* required

- **Mechanism [SRC]** (Enhanced Depends, v2.9+; `dag-enhanced-depends.yaml`): `depends` uses
  operands `task.Succeeded|Failed|Errored|Skipped|Omitted|Daemoned`, plus `.AnySucceeded` /
  `.AllFailed` for loops, combined with `&& || !`. Default `dependencies` is equivalent to
  `task.Succeeded || task.Skipped || task.Daemoned` (i.e. "the whole set", a barrier). By
  contrast `depends: "task-1.AnySucceeded || task-2.AllFailed"` lets a downstream step proceed
  on a *declared subset* of results. `DAGTemplate.FailFast` defaults **true** ("stop scheduling
  new steps as soon as one DAG node is failed"); set `false` to run all branches to completion.
  `Template.FailFast` is the `withItems` analogue (default off unless set).
- **Fault addressed**: an unnecessary all-item barrier that blocks synthesis/closeout; one
  failed item discarding unrelated successful branches; treating "any failure" as whole-batch
  failure.
- **KPR/KW fit [INF]**: strongly matches "aggregate synthesis waits only on actual
  prerequisites", "partial acceptance never hides other branches", and "a batch is settled when
  every item is resolved or explicitly handed to a continuing duty, never merely when all
  replies arrive." Mismatch/limit: Argo's own *aggregate output* (`{{steps.loop.outputs.result}}`
  or `{{steps.loop.outputs.parameters}}`) IS a full barrier — it only materializes after the
  whole loop finishes. So the barrier-free gain comes from DAG-level `depends`, not from loop
  aggregation. KPR's summary is already specified as "a derived view of item references, not a
  copy of results", which is closer to the Argo DAG model than to loop aggregation.
- **Smallest borrowable idea**: let each aggregation/verdict declare its actual prerequisite
  predicate — at minimum "any usable result" and "all items terminal" — instead of defaulting
  to "all succeeded", and keep per-item terminal statuses so the other-branches view survives.
- **Concrete local QA**: 4-item fan-out, item 2 fails. Assert items 1/3/4 can still be accepted,
  the batch can be recorded "settled except item 2 (explicit continuing duty)", and an
  any-result aggregation evaluates without waiting on item 2's success.
- **Classify**: **borrow now** (prerequisite predicate); core principle **already covered**.

### F4. Explicit, typed failure tolerance per item (`continueOn` / `depends .Failed`)

- **Mechanism [SRC]** (`ContinueOn {Error, Failed}`, `continues()` matches only the matching
  terminal phase; `WorkflowStep.ContinueOn` / `DAGTask.ContinueOn`;
  `dag-continue-on-fail.yaml` uses `depends: "B.Failed && C"`). CEL rule: "cannot use
  'continueOn' when using 'depends'". `Skipped`/`Omitted` outputs referenced downstream
  "resolve to empty strings".
- **Fault addressed**: a failed branch aborting unrelated branches; conflating `Error`
  (non-exit-code fault) with `Failed` (non-zero exit); accidentally depending on a failed
  task's output.
- **KPR/KW fit [INF]**: matches "partial admission succeeds only for admitted items" and
  "partial acceptance never hides other branches." Mismatch: KPR does not auto-schedule
  downstream work from a failed item's outputs; the Host judges. The design's "no arbitrary
  retry count / no unbounded retry" is compatible with `continueOn` being explicit opt-in.
- **Smallest borrowable idea**: record failure as a typed *fact* (failed vs errored vs
  skipped/omitted) that downstream decisions can consume, rather than an implicit abort; keep
  the "missing result from a non-run item is an explicit gap, not an empty success" rule.
- **Concrete local QA**: mark one item `failed`; assert other items are untouched, the summary
  distinguishes failed vs errored, a skipped/omitted item is never counted as succeeded, and no
  automatic replacement/retry of the failed item occurs without a Host decision.
- **Classify**: **already covered** (typed terminal vocabulary); small wording borrow.

### F5. Cancellation: two modes plus selection by the *original input*

- **Mechanism [SRC]** (`workflow_types.go`): `ShutdownStrategy` = `Terminate | Stop | ""` with
  `ShouldExecute(isOnExitPod)`: `Terminate` → `false` (no exit handlers), `Stop` →
  `isOnExitPod` (exit handlers still run). CLI: `argo stop` "still run exit handlers" vs
  `argo terminate` "do not run any exit handlers". `argo stop` accepts
  `--node-field-selector inputs.parameters.<name>.value=<v>` ("selector of node to stop").
- **Fault addressed**: cancellation that silently looks like success; losing intended cleanup;
  inability to cancel one branch without killing siblings; no observed disposition.
- **KPR/KW fit [INF]**: matches "Host may terminate unnecessary branches with explicit
  cancellation; cancellation itself requires observed disposition" and "no silent extra grant."
  Mismatch: KPR's transport does not own an `onExit` runtime, so "run cleanup handlers" is the
  worker's/Workflow's own closeout, not something the transport can promise; KPR should record
  the *intent* (cleanup-required vs hard-stop) and require the observable stop receipt.
- **Smallest borrowable idea**: (a) two cancellation intents — *cooperative* (still expects
  closeout/duty handling) vs *hard stop*; (b) target a branch by its **original input value**,
  not by a generated/mutable name; (c) a "stop requested" state never equals "seat available".
- **Concrete local QA**: cancel item 3 of 5 mid-flight by its original input; assert items
  1/2/4/5 are unaffected, item 3 shows cancel-requested then a terminal stopped/no-residual
  observation, and a requested stop alone never marks the seat available.
- **Classify**: principle **already covered**; **borrow now** for select-by-original-input +
  two cancellation intents.

### F6. "Result received" is modelled separately from "process completed" and gates archive/GC

- **Mechanism [SRC]** (`workflow_types.go`): `NodeStatus.TaskResultSynced` = "used to determine
  if the node's output has been received". `NodeStatus.Completed()` = `Phase.Completed() &&
  synced`. `WorkflowStatus.TaskResultsCompletionStatus` = "tracks task result completion status
  (mapped by node ID). **Used to prevent premature archiving and garbage collection**"
  (`TaskResultsInProgress()`, `IsTaskResultIncomplete()`). `Fulfilled()` also treats
  `Skipped`/`Omitted` as fulfilled without a result.
- **Fault addressed**: archiving/GC/retire before the actual result is durably received;
  treating process exit as the result.
- **KPR/KW fit [INF]**: matches "process returns and reclaim individually", "Worker return ...
  exact turn/source/locators, no rewritten conclusion", and "no orphan resource inferred clean
  because JSON says done." Mismatch: Argo's flag mainly covers its agent/HTTP task results, not
  every node; KPR must not add a parallel store — record the received locator in existing
  receipts/index and gate removal on it.
- **Smallest borrowable idea**: a per-item "result-received" condition distinct from "process
  ended", and use it — not the process exit — to allow the item's removal/retire.
- **Concrete local QA**: worker process exits but the result event is delayed/lost; assert the
  item stays open (not retired/archived), because a result-received locator or an explicit
  continuing-duty handoff is required.
- **Classify**: concept **already covered**; **borrow now** as an explicit small gate flag.

### F7. Exact-fidelity has a size limit — large results must be referenced, not inlined

- **Mechanism [SRC]** (`handle-large-output-results.yaml` header comment): output parameters and
  "results" pass **between pods via annotations**; "Annotations have a size limit. If your
  output is larger than **256 kB**, you should use an artifact instead of a parameter." Also
  "the output of each iteration *must* be a valid JSON" for loop aggregation, else a JSON parse
  error.
- **Fault addressed**: silent truncation/loss of large results; aggregate parse failures.
- **KPR/KW fit [INF]**: matches "Missing/truncated result/artifact: retain explicit gap and
  source locator ... no invented summary as acceptance."
- **Smallest borrowable idea**: reference large results by locator rather than inlining; treat
  an oversized/missing inline result as an explicit gap the Host must resolve.
- **Concrete local QA**: return a result over the inline limit; assert KPR records a
  locator/gap and the Host requests evidence rather than accepting a truncated value.
- **Classify**: **borrow now** (one-line rule).

### F8. Bounded resource admission: ordered wait queue + bounded infra restarts (and a useful refusal)

- **Mechanism [SRC]** (synchronization.md + controller config): waiting workflows/templates sit
  in a queue ordered by `priority` (higher first) then creation timestamp; `ConfigMap`
  semaphores/mutexes cap concurrency; `ResourceRateLimit {Limit, Burst}` bounds pod-creation
  rate. `FailedPodRestart {Enabled, MaxRestarts default 3}` "prevents infinite restart loops."
  Crucially, on a dead controller: *pending* lock entries are bypassed after a heartbeat
  timeout, but **"Held locks are never taken by another Workflow, even if the controller is
  inactive. You must manually intervene to release a held lock."**
- **Fault addressed**: retry storms / thundering herd; a dead holder permanently blocking;
  non-deterministic admission order.
- **KPR/KW fit [INF]**: matches "capacity all busy retains capacity wait or explicit user
  decision", "no unbounded retry", and — importantly — the **negative** result corroborates
  "on hold never invents revocation" and "no seat declared available from requested stop alone":
  even a mature system refuses to auto-release a *held* lock and demands manual intervention.
  Mismatch: KPR has no global scheduler/lock DB; a rated/queued admission model is infrastructure
  KPR explicitly does not adopt. The design also says "no new numerical policy", so a restart
  count is not ours to introduce here.
- **Smallest borrowable idea**: only the ordering rule — a bounded-wait set with a deterministic,
  Host-declared order — and the confirming rule that a dead holder's held seat is **not**
  auto-freed without an explicit rule.
- **Concrete local QA**: capacity-1 with 3 items and explicit priorities; assert deterministic
  admission order and that a confirmed-dead holder's seat is not silently freed.
- **Classify**: **defer** (infrastructure/quota shape; belongs to recovery/reclaim, not fan-out);
  the held-lock refusal is **already covered** as corroboration.

## Classification summary (against `lifecycle-closure-consolidation.md`)

| # | Small idea | Class | Reason |
|---|---|---|---|
| F1 | Stable item key + generated instance id + pinned prompt hash/revision | borrow now | Design names the principle; needs the explicit two-key + hash wording in item records |
| F2 | Retained `admitted-not-started` phase; batch scoped limit | already covered | Matrix already lists "admitted, not-run, failed or unknown" |
| F3 | Aggregation declares its prerequisite (any-result / all-terminal) | borrow now | "waits only on actual prerequisites" is stated but not expressed as a per-aggregation predicate |
| F4 | Typed failed vs errored vs skipped/omitted; gaps not empty success | already covered | Typed terminal vocabulary + "no invented summary" already present |
| F5 | Cancellation by original input; two cancellation intents | borrow now | Observed-disposition principle covered; the *selector* and intent split are not |
| F6 | "Result-received" flag distinct from "process ended", gates retire | borrow now | Principle covered; an explicit gate condition is the small concrete addition |
| F7 | Large results by locator, not inline | borrow now | One-line rule consistent with existing gap handling |
| F8 | Deterministic waiting order; dead-holder held seat stays locked | defer / already covered | No scheduler in KPR; held-lock refusal already matches design |

No arbitrary quota was applied; research stopped once each sub-question had a supported answer.

## Material limitations

- Single system studied (Argo Workflows). Cross-system contrast (e.g. Airflow dynamic task
  mapping, Nextflow channels) was not researched for this report — a genuine coverage gap, not a
  negative finding.
- Docs were read from the `en/latest` readthedocs build (built from `main`); source files and
  examples were pinned to tag **v4.1.4** to keep the mechanisms version-exact. Where a mechanism
  is version-gated it is noted (e.g. Enhanced Depends v2.9+, `shutdown` strategy).
- No local tests, no native actors, no benchmark. Nothing here proves the KPR candidate correct;
  these are implementation analogies only.
- The per-node `inputs`/`outputs` "original fidelity" claim is read from the *field descriptions*;
  I did not execute a workflow to observe persistence across offload/archive. Treat the exact
  retention behavior as source-described, not measured.
