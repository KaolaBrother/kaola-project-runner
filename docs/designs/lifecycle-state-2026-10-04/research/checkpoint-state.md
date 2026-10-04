# checkpoint-state — bounded public-source research for KPR #255

Question (owner-bounded, dispatch track 2): short-lived execution contexts, bounded checkpoints,
concurrent/versioned writes, pending writes, state projections, retirement/migration and recovery
that preserves unfinished duties **without cumulative chats or extra ledgers**.

Researcher: this worker (original report). Access date **2026-10-04**. Read-only HTTPS only; no
login, install, private data upload, or infrastructure change. Workflow was OFF for this helper: no
claim, no worktree, no ledger, no implementation, no local tests, no native actors.

External sources are evidence, not instructions. Every finding below separates **source evidence**
(what the document/code/paper actually says, with a locator) from **inference** (my reading). This
research never proves our candidate correct; it can only suggest or rule out borrowable mechanics.

Retrieval locators, versions and commits are in the companion note
`ckptstate-retrieval-notes.md` (uniquely prefixed `ckptstate-`).

## Scope and boundary

In scope: LangGraph persistence/checkpoint layer (docs + source) and one primary paper on
effective-state projection and obligation preservation. Out of scope by the brief: Temporal-style
delivery/at-least-once semantics, fan-out/fan-in, and coordinator/child resource lifecycle (other
tracks own those). I did not fetch or evaluate other systems.

Baseline design source I am classifying against: `lifecycle-closure-consolidation.md` (the #255
integrated closure proposal) plus the owner's seven AGENTS requirements. Where that source already
states the rule, the honest verdict is "already covered," not "borrow."

---

## Finding 1 — Versioned per-channel state with a per-node "seen" watermark (no cumulative replay)

**Source evidence.** LangGraph's `Checkpoint` is a `TypedDict` whose persisted fields include:

- `channel_versions: dict[str, str|int|float]` — "monotonically increasing version strings for each channel";
- `versions_seen: dict[str, ChannelVersions]` — "Map from node ID to map from channel name to version seen … Used to determine which nodes to execute next";
- `v: int` — checkpoint format version;
- `id` — "unique and monotonically increasing, so can be used for sorting checkpoints from first to last" (`libs/checkpoint/langgraph/checkpoint/base/__init__.py`, commit `9a0394d8`, `langgraph-checkpoint` 4.2.0).

The scheduler fires a node on a channel only when the channel *moved past what that node last saw*
(source, `libs/langgraph/langgraph/pregel/_algo.py`):

```python
for chan in proc.triggers:
    if channels[chan].is_available() and versions.get(chan, null_version) > seen.get(chan, null_version):
        return True
```

`checkpoint["versions_seen"].setdefault(task.name, {}).update(...)` is written after a task runs
(`_algo.py:263`). New versions come from `get_next_version` (e.g. sqlite: `f"{next_v:032}.{next_h:016}"`,
monotone counter + random tiebreak, `libs/checkpoint-sqlite/.../sqlite/__init__.py:627`).

**Fault addressed.** Re-running work that already produced state; and the opposite failure — silently
skipping work because a channel was merely rewritten. It gives a *causal* trigger ("this consumer
has not seen this update") rather than "everything since step 0."

**Versus inference.** Evidence: the fields and the `>` comparison exist as quoted. Inference: this is
a per-consumer watermark, so correctness does not require loading or replaying the whole history —
a node is either caught up or not. The doc confirms the design intent: per-task writes "are what
enable pending writes recovery: if another node in the same super-step fails, the successful nodes'
writes are already durable and don't need to be re-run on resume" (`checkpointers.md`).

**KPR/KW fit and mismatch.**
- Fit: our #255 node model already says "Source Host revision is acknowledged only up to the selected
  batch revision; later writes remain pending" and "checkpoint is verified against input identity and
  source." A watermark per consumer is exactly that idea made mechanical.
- Mismatch: LangGraph versions *state channels*, and a node's "seen" map is keyed by node name. We
  should not import a channel/version engine or a new store. Our equivalent is the existing receipts
  + revision stamps; the open gap (if any) is that today the *comparison rule* may be implicit.
- Danger the source itself documents: a version bump that only stores a snapshot is *not* a write, so
  `_mark_bumps_seen` / `versions_seen_without_bumps` exist purely to stop a bump from re-firing
  subscribers and re-running a node (`_checkpoint.py`). Translation: if we ever bump a "revision"
  for bookkeeping, we must not let that bump look like a new duty to a consumer.

**Smallest borrowable idea.** State, in one line, the comparison rule the design already implies:
*an item is pending for a reader iff its source revision is greater than the revision that reader
last acknowledged.* Do not add a counter for the Host and do not store a second history.

**Concrete local edge-case QA.** Stamp a task at revision R; have a node acknowledge R; then write a
bookkeeping-only bump to the same record without changing any duty. Assert the node does **not**
re-open the task, and that a genuine duty change at R+1 **does** open it. Then crash the node between
write and acknowledge and assert the task is still pending (not silently "seen").

**Classification: borrow now (as an explicit, testable rule — not as new storage).** The design
already contains the intent; the borrow is making the predicate explicit so it can be QA'd.

---

## Finding 2 — Writes are idempotent upserts keyed by a natural composite key; there is no whole-file replace

**Source evidence.** Postgres schema and write path (`libs/checkpoint-postgres/.../postgres/base.py`):

```sql
CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL, task_id TEXT NOT NULL, idx INTEGER NOT NULL, ...
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx));
```

and the write is an upsert, not an insert-or-fail and not a replace:

```sql
INSERT INTO checkpoint_writes (...) VALUES (...)
ON CONFLICT (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) DO UPDATE SET channel=..., type=..., blob=...;
```

`checkpoint_blobs` upserts keyed by `(thread_id, checkpoint_ns, channel, version)` with
`DO NOTHING`; `checkpoints` upserts keyed by `(thread_id, checkpoint_ns, checkpoint_id)`
(`DO UPDATE SET checkpoint, metadata`). Storing a checkpoint returns `(thread_id, checkpoint_ns,
checkpoint_id)`; the *parent* id is carried separately (`parent_checkpoint_id`).

**Fault addressed.** A retried or duplicated write either double-applies or clobbers a concurrent
update. The composite key makes replay idempotent; `DO NOTHING` on the versioned blob makes "the same
version" a singleton; per-row keys mean one writer cannot erase another row it does not own.

**Versus inference.** Evidence: the exact keys and conflict clauses are quoted from the pinned
commit. Inference: this is what makes "record intent first, reconcile exact target and receipt"
safe — a reconciled retry converges on the same row instead of appending a second fact. Note the
docs explicitly warn custom savers *not* to strip unknown metadata fields because LangGraph adds new
ones in minor releases ("Store `metadata` in full — do not strip unknown keys", `checkpointers.md`):
forward-compatible readers, backward-compatible writers.

**KPR/KW fit and mismatch.**
- Fit: our closure already requires "no whole-file replacement" and "compare revisions and reconcile."
  This is the concrete, proven shape of that rule.
- Mismatch: we are not a database and should not adopt keys, tables, or an ORM. The transferable part
  is the *identity discipline*: one fact = one stable identity; a repeated write of the same identity
  is a no-op or an update, never a new fact.
- Additional caution from the same source: `delete_for_runs` and `prune` carry explicit warnings that
  deleting ancestor rows can silently break reconstruction of a surviving record
  (`base/__init__.py`, `prune` docstring). Retirement is not free even in a mature system.

**Smallest borrowable idea.** Make the fact identity explicit and stable *before* the external effect
(already a design line), and require the reconcile step to converge on that identity rather than
append. For our file/markdown state, the equivalent of an upsert is: reconcile by identity, rewrite
that entry in place, never regenerate the whole store.

**Concrete local edge-case QA.** Simulate a duplicated dispatch receipt for the same item: assert the
second reconcile updates the same task entry and does not create a second duty or a second "started"
line. Then simulate two writers touching two *different* items concurrently: assert neither write
removes the other item. Finally, assert that a reader which does not understand a newly added field
still loads the record (forward compatibility).

**Classification: already covered in intent; borrow now only as an explicit reconcile-by-identity
rule with the two QA cases.** The design says "no whole-file replacement"; the source shows the
minimal correct shape.

---

## Finding 3 — Pending writes: durable partial results so a failed branch is not recomputed

**Source evidence.** `put_writes` "Store intermediate writes linked to a checkpoint (i.e. pending
writes)"; `get_tuple` returns `pending_writes`. Docs (`checkpointers.md`): "As each node within a
super-step finishes, its outputs are written to the checkpointer's `checkpoint_writes` table as task
entries linked to the in-progress checkpoint… if another node in the same super-step fails, the
successful nodes' writes are already durable and don't need to be re-run on resume. The full state
snapshot is then committed once the super-step completes." Resuming is by the same `thread_id` +
`checkpoint_id`; `Command(resume=...)` continues the interrupted node.

**Fault addressed.** Crash/loss between "some branches finished" and "the step is committed" causing
completed work to be redone (and, for non-idempotent branches, double-applied).

**Versus inference.** Evidence: the table, method, and doc paragraph. Inference: this is the closest
structural analogue to our "partial admission" / "partial return" rule — the durable unit is the
*item's* finished result, committed before the batch is settled. Two boundaries the source is honest
about and we must mirror: (a) a resumed *node* restarts from the top of the node function, so code
and side effects before the pause run again — idempotency is the caller's duty ("Re-execution and
idempotency", `graph-api.md`: "Use idempotency keys, upserts, or read-before-write checks"); (b)
pending writes are not full snapshots, so time travel only resumes from committed checkpoint
boundaries.

**KPR/KW fit and mismatch.**
- Fit: our matrix says a batch "is settled when every item is resolved or explicitly handed to an
  identifiable continuing duty, never merely when all replies arrive." Per-item durable result is
  exactly that.
- Mismatch: LangGraph's "pending write" is a *write to state by a node*, automatically recorded by
  the runtime. Ours must remain **evidence-driven**: a worker's original result and locator are
  recorded, and the Host still owns the semantic verdict. Do not let "the return was durably
  recorded" be read as "the task is accepted" — that is precisely the confusion the design forbids
  ("Host verdict pending even if notice delivered").
- The idempotency lesson is real and transferable: our repair/replay of a partially-executed item
  must tolerate the pre-effect code running again.

**Smallest borrowable idea.** Keep the durable unit equal to the **item result**, written once at the
boundary where it becomes true, and treat the batch/super-step commit as a derived projection — not
as the thing that makes results real. Write down that replay of an interrupted item is idempotent.

**Concrete local edge-case QA.** Admit three items; complete two; interrupt before the batch is
settled. Assert the two completed items are not re-dispatched and not re-tallied, the third is
visibly unfinished, and no acceptance/verdict was inferred from mere write durability. Then replay
the interrupted item's start and assert the second attempt converges on the same item identity
(per Finding 2).

**Classification: borrow now.** This directly hardens the existing "partial admission / preserve
partial outcomes" language and closes an ambiguity ("recorded" vs "accepted").

---

## Finding 4 — Bounded checkpoints and bounded storage: durability modes plus explicit pruning, with a named hazard

**Source evidence.**

- Durability modes (`checkpointers.md`): `"exit"` persists only when execution exits (so "you cannot
  recover from system failures mid-execution"); `"async"` persists while the next step runs with "a
  small risk that LangGraph does not write checkpoints if the process crashes"; `"sync"` persists
  "synchronously before the next step starts." This is a *deliberate, named* trade of durability
  against cost — not an accident.
- Storage growth is acknowledged and given a fix: "Over long conversations, checkpoints accumulate…
  **Prune old checkpoints periodically or set a retention policy**… Consider adding a cron job to
  delete checkpoints older than N days" (`persistence.md`).
- The retire API surface is explicit and small: `delete_thread` ("Both checkpoint rows and write rows
  must be deleted"), `delete_for_runs`, `copy_thread`, `prune(thread_ids, strategy="keep_latest"|"delete")`.
- The hazard is documented in the source, not hidden: a naive `"keep_latest"` prune "can sever that
  chain: the surviving 'latest' checkpoint is rarely a snapshot point itself, so its delta channels
  would silently reconstruct as empty (**no error raised**)". Safe options given: preserve ancestors
  up to the last snapshot; force a fresh snapshot on the kept record before deleting ancestors; or
  skip pruning. (`base/__init__.py` `prune` docstring; same warning in `checkpointers.md` §Delta
  channel support.)
- Store-side TTL exists separately (`TTLConfig` with `default_ttl` / `refresh_on_read`,
  `store/base/__init__.py`; `tests/test_ttl.py` shows `sweep_ttl()` and read-refresh behavior) —
  i.e. *cross-thread* long-term memory has its own retention knob, distinct from thread checkpoints.

**Fault addressed.** Unbounded growth of history, and the silent-corruption failure mode of naive
deletion. Note the crucial admission: pruning *can fail silently* if the retained record depends on
deleted ancestors — the exact class of "obsolete-record retirement loses an unfinished duty" risk in
our design.

**Versus inference.** Evidence: quoted policy, API, and warning. Inference: two distinct knobs are
being modeled — *how much you persist during a run* (durability) and *how long you keep it after*
(retention) — and mature code keeps them separate. Our design currently speaks mostly about
retirement of duties; it does not clearly name a bounded-history/durability policy.

**KPR/KW fit and mismatch.**
- Fit: owner requirement 2 ("retire resolved responsibilities and reference history without losing
  pending duties") and the closure's "Retire: current task removed only with terminal evidence or
  explicit continuing owner/handoff. History stays at source."
- Mismatch: we must not add a cron pruner, a TTL subsystem, or a background sweeper — that would be a
  new scheduler, explicitly forbidden. And "history stays at source" already means we are not the
  history store, which is stronger than a retention policy.
- What is genuinely missing and cheap: an honest statement of **our durability boundary** (what is
  durably true at which moment, and what is knowingly at risk if a context dies mid-write), and the
  rule that retirement must verify the retained record still has everything a later reader needs
  before anything is removed — mirroring the "walk back to a snapshot before pruning" option.

**Smallest borrowable idea.** Add one named durability-boundary sentence (what survives a mid-write
context death and what does not) and one retirement precondition: *do not remove a record until every
still-live dependent has its needed evidence inline.* No new tooling.

**Concrete local edge-case QA.** (a) Kill a context between "external effect" and "state write" and
assert the recovery path reports **unknown**, not done and not absent. (b) Retire a resolved task and
assert every pending dependent still reads its evidence. (c) Attempt to retire a record whose evidence
only existed in a now-removed ancestor and assert retirement is refused with a concrete warning rather
than silently succeeding (this is the "no error raised" failure from the source, inverted into a guard).

**Classification: borrow now (the durability-boundary statement and the retirement precondition);
defer anything resembling TTL/prune tooling** — it would duplicate the existing receipts/index and
could become a second lifecycle owner.

---

## Finding 5 — Migration across a clean context: version stamped at start + add-then-remove, and state that outlives a code swap

**Source evidence.** LangGraph applies the *latest* graph to every thread, including resumed ones
("Unlike workflow engines that pin a run to the version of code it started with, LangGraph applies the
latest graph immediately to *every* thread… bug fixes propagate to in-flight conversations"). It then
categorizes breakage (`backward-compatibility.md`):

- *Technical*: renaming/removing a **node** while a thread is parked there fails on resume; renaming/
  removing a **state key** older checkpoints contain; tightening a field (Optional→required) breaks
  old checkpoints.
- *Business*: mechanically valid but semantically different — the recommended pattern is to "record
  the relevant *behavioral version* on the state at thread start, then branch on it with a conditional
  edge," and it "only works if you set the version *at thread start*, before any branch that needs to
  be versioned."
- Graph-migration summary (`graph-api.md`): whole-topology change is safe for *finished* threads;
  for interrupted threads all topology changes are supported *except* rename/remove of a node; adding
  and removing state keys has "full backwards and forwards compatibility"; renamed keys lose saved
  state; incompatible type changes may break old threads.

A concrete, tested migration exists in the repo: `libs/checkpoint-sqlite/tests/test_delta_channel_migration.py`
drives a thread under the old channel type, swaps the annotation to the new type on the same thread,
and asserts every settled pre-migration boundary round-trips exactly (the new reader must recognize the
old plain stored value as a valid seed). The Postgres adapter keeps an ordered `MIGRATIONS` list where
"the position of the migration in the list is the version number," including an explicit no-op entry
added solely to keep numbering correct, and a one-line forward-compat upgrade (`ADD COLUMN IF NOT
EXISTS task_path TEXT NOT NULL DEFAULT ''`).

**Fault addressed.** Upgrade breaks in-flight work; old readers cannot read new records, or new readers
misread old records; repeated/interrupted migration.

**Versus inference.** Evidence: quoted guarantees, the version-at-start pattern, and the *tested*
migration. Inference: the two load-bearing ideas are (i) stamp the behavioral version where the record
is *created*, never later, and (ii) make readers tolerant of both shapes (add-then-remove, defaults for
new fields) rather than performing a big-bang rewrite. The repo's own explicit no-op migration entry is
evidence that migration *numbering* is a real, separate concern from migration *content*.

**KPR/KW fit and mismatch.**
- Fit: owner requirement 7 asks for "a repeatable update convention and tested migration path from
  supported previous versions, preserving effective grants, duties, in-flight work and unresolved
  exceptions," covering "interrupted/repeated migration, compatible readers/holders."
- Mismatch: LangGraph's "apply latest code to every thread" is convenient but is *not* automatically
  what we want — our design already leans the other way ("A later change affects only related unstarted
  work or explicit correction; admitted old work remains visible"). Adopting LangGraph's live-upgrade
  stance wholesale would silently change admitted in-flight work. So: borrow the *version-at-start +
  tolerant reader* mechanics; reject the "latest code rewrites everything" stance.
- Also note the honest boundary LangGraph states: it "does not maintain a search index over thread
  state," so it cannot easily answer "is anything parked on the old version?" We have the same class of
  gap; the design should say what the reader/holder must do when it cannot enumerate affected work.

**Smallest borrowable idea.** Stamp an explicit *behavioral version* on each admitted duty/grant at
creation time, define a bounded deprecation window for readers (new fields optional, old fields kept
one drain cycle), and write one tested migration scenario for a clean-context swap. Nothing more.

**Concrete local edge-case QA.** (a) Create a duty with version V1; upgrade the reader to V2; assert
the old duty still loads and completes under its V1 semantics, while a new duty is stamped V2. (b) Run
the migration twice (interrupted then repeated) and assert the result is unchanged and no duty is lost
or duplicated. (c) Point a V1 reader at a record containing a V2-only field and assert it ignores the
unknown field rather than failing. (d) Rename a field only after a drain cycle and assert no in-flight
duty loses its data.

**Classification: borrow now.** This is the strongest direct answer to owner requirement 7 and is
already partially implied; the borrow is the creation-time stamp plus the tolerant-reader rule plus a
tested scenario.

---

## Finding 6 — State projection and obligation containment (primary paper)

**Source evidence.** *Mnemosyne: Agentic Transaction Processing for Validating and Repairing
AI-generated Workflows*, arXiv:2607.00269v3 (v3 2026-08-31). Mechanism, quoted from the paper:

- Four planes: "the **proposal plane**… the **admission plane**, where deterministic validators decide
  whether a candidate may become truth; the **commit plane**, where admitted transitions are durably
  appended; and the **projection plane**, where current effective state is materialized for future
  admission."
- Durable substrate: "The committed-transition log (CTL) is the source of committed truth:
  tenant-scoped, versioned, and logically append-only, it stores admitted transitions, compensation
  and supersession records, and ACR lifecycle records, so later transitions may supersede earlier ones
  **without erasing the fact that they were admitted**. **StateView** projects current truth from CTL
  by replaying only effective records (not compensated, superseded, or invalidated, with dependency
  chains intact); **admission reads StateView, never raw history**."
- Active contract records: "a durable obligation in CTL with trigger, guard, continuation, compensation,
  and expiry. A watcher proposes readiness; admission records it; only then may the continuation
  propose a remedy. **No stage writes domain truth directly.**"
- The obligation-continuation path is: "a contract's create → watch → readiness proposal → admit
  readiness → resume," and readiness/remedy outputs "may only propose, never mutate CTL or StateView."
- Measured results relevant to us: ObligationBench "baselines let wakeups mutate domain state directly
  (12 and 16 unauthorized mutations); ATP admits the lifecycle transition, routes each continuation
  output through ordinary admission, and commits **zero** unauthorized domain mutations."
  CompensationProjectionBench: projection baselines "project ineffective history as current truth
  (seven StateView mismatches), while ATP keeps StateView the projection of effective committed records
  only, with **zero** mismatches." A "12-scenario interruption stress test rejects every stale recovery
  candidate without losing observations or producing invalid commits." SerialAdmissionBench: 80
  concurrent proposals over a shared capacity object → ATP admits only the 32 valid ones "through a
  serialized boundary and yields a serial-equivalent history." StorageSubstrateBench: duplicate, stale,
  and malformed storage attempts — the unconstrained log commits all 64 invalid attempts, ATP "rejects
  all 64 and preserves projection."

**Fault addressed.** (i) Retired/superseded records reappearing as current truth; (ii) an autonomous
watcher or continuation ("wakeup") mutating durable state directly, bypassing review; (iii) concurrent
writers producing a non-serial-equivalent history; (iv) duplicate/stale/malformed storage attempts
corrupting the projection. All four are on our #255 fault list.

**Versus inference.** Evidence: the plane separation, the CTL-vs-StateView rule, the ACR lifecycle, and
the measured counts are quoted/paraphrased from the paper. Inference: "projection is a *derived view of
effective records only*" is precisely our "batch summary is a derived view of item references, not a
copy of results," and "no stage writes domain truth directly" is our "Sideagent records locators/
identities/duties, not semantic acceptance." The paper is a *proposal with an executable artifact*;
its guarantees are conditional on stated assumptions (e.g. "declared conflict scopes are correct and
complete… Hidden conflicts outside the declared scopes are outside the guarantee"), and it is not
independent replication. I am not treating its theorem as proof about our system.

**KPR/KW fit and mismatch.**
- Fit (strong): the split between **append-only committed truth** and a **derived current projection**
  read by the gate maps one-to-one onto our "existing receipts/index remain authoritative" + "batch
  summary is a derived view." The ACR "trigger/guard/continuation" shape maps onto "unfinished duty
  with a continuing owner/handoff," and its rule that a continuation may only *propose* is exactly the
  boundary we need between Sideagent (records) and Host (judges).
- Mismatch: Mnemosyne *adds* a committed-transition log and a materialized StateView — i.e. a second
  durable store. The owner brief explicitly forbids a second framework/ledger, and our design says
  "no second framework or ledger." So we must take the **separation of concerns (authoritative facts
  vs derived projection, proposal vs commit)** and *not* the substrate. Their conflict-scope mechanism
  is also a real cost (declared scopes must be complete) that we should not underestimate.
- Also: their guarantees depend on a deterministic admission gate. Our admission is a Host judgment,
  which is deliberately not deterministic. We can borrow the *shape* (nothing becomes current truth
  without an admitted decision) but not the guarantee.

**Smallest borrowable idea.** Two sentences we may already believe but should state as invariants:
(1) *only facts admitted by the responsible owner appear in the current projection; superseded or
retired records remain discoverable at their source but are excluded from "current";* (2) *a watcher/
maintenance node may propose a change to a duty's lifecycle but may never write the duty's truth or
the current projection directly.* Both are compatible with using existing receipts as authority.

**Concrete local edge-case QA.** (a) Supersede a duty with a corrected one: assert the projection shows
only the corrected duty, while the superseded one is still findable at its source and does not
reappear as pending. (b) Have the maintenance node attempt to mark a duty done directly: assert it can
only emit a proposal and that nothing changes until the Host verdict exists. (c) Run two writers on
overlapping items and assert the resulting projection equals some serial order of the admitted facts.
(d) Feed the projection a duplicate/stale/malformed record and assert it is rejected or flagged, never
folded silently into the current total.

**Classification: borrow now (the two invariants, as restated against our existing authority model);
defer (the CTL/StateView substrate, conflict scopes, and the theorem).** The invariants are cheap and
directly close owner requirements 2 and 3; the substrate would violate "no second ledger."

---

## Finding 7 — Restoration is a semantic hazard, not a free undo (primary paper)

**Source evidence.** *ACRFence: Preventing Semantic Rollback Attacks in Agent Checkpoint-Restore*,
arXiv:2603.20625v1 (2026-03-21). The paper's premise: frameworks advise making tool calls "safe to
retry," but "this advice assumes that a retried call will be identical to the original… a retried call
[that] fails for LLM agents, which re-synthesize subtly different requests after restore." It names
two classes — **Action Replay** and **Authority Resurrection** — and defines ACRFence as recording
irreversible tool effects and enforcing **replay-or-fork** semantics on restore: equivalent call →
replay the recorded response; semantically different call → block and require an explicit new branch;
reuse of a consumed credential → warn before the call. Reported experiments: with stateless token
validation all token-reuse attempts succeeded (2/2); with a server-side revocation list all were
rejected. The authors are explicit that the mitigation itself was **not implemented** in the paper and
that the analyzer introduces its own failure modes.

**Fault addressed.** A restored/rewound context re-performing an irreversible external action, or
reusing an authorization that was already consumed, because state and external world have diverged.

**Versus inference.** Evidence: the attack classes, the replay-or-fork rule, and the measured token
results. Inference: this is the sharpest source I found for why "recover across a clean context" must
not mean "rewind the world." Our design already separates business task / grant / occupancy state
("A dead runtime does not erase a task. A completed task does not revoke a reusable grant") and says
"never assume absence proves no previous mutation" — this paper supplies the *adversarial* framing and
a concrete consumer-side requirement (consumption must be recorded server-side, not inferred from
context).

**KPR/KW fit and mismatch.**
- Fit: strongly supports our "record intent first, reconcile exact target and receipt" and "grant
  remains distinct" rules, and our requirement that stop/reclaim be attempted-and-verified rather than
  assumed.
- Mismatch: ACRFence inserts an LLM analyzer at the tool boundary. That is a new actor and a new
  semantic judgment point; our design deliberately routes semantic judgment to the Host. Also its
  threat model (malicious insider rewinding) is broader than ours. We should take the *invariant*
  (effect must stay consumed; a divergent retry is not the same action) and not the proxy/LLM.
- Honest limitation: the paper validates the attacks but not the mitigation, so it is evidence for the
  *risk*, not for a specific guard's effectiveness.

**Smallest borrowable idea.** One invariant for the migration/recovery convention: *a restored or
migrated context must not re-perform an irreversible effect or re-consume an authorization; where the
new context cannot prove the effect's state, it must record the uncertainty and escalate rather than
proceed.*

**Concrete local edge-case QA.** Simulate a clean-context migration of a duty that had already
performed its external effect. Assert the migrated context does **not** re-perform the effect, marks
the effect state as unknown/consumed-with-evidence, and routes the decision to the Host. Separately,
assert that a retried start/send with a *different* target than the original is treated as a divergent
action, not as replay of the original.

**Classification: borrow now (the invariant, into the migration/recovery convention).** Cheap, and it
closes a real gap in "repeated migration" wording.

---

## Summary table

| # | Mechanism | Source (pin) | Classification | One-line reason |
|---|---|---|---|---|
| 1 | Per-consumer version watermark | LangGraph 4.2.0 @`9a0394d8` | borrow now (rule only) | design already implies it; make the predicate explicit/testable |
| 2 | Idempotent upsert by stable identity | LangGraph postgres @`9a0394d8` | borrow now (rule + QA) | "no whole-file replace" needs a concrete shape |
| 3 | Durable per-item pending writes | LangGraph docs+source | borrow now | hardens "preserve partial outcomes"; separates recorded from accepted |
| 4 | Durability modes + bounded retention | LangGraph docs/source | borrow the boundary statement; **defer** pruning/TTL tooling | a pruner/TTL would be a new scheduler/store — forbidden |
| 5 | Version-at-start + add-then-remove migration | LangGraph backward-compat doc + tested migration | borrow now | direct answer to owner requirement 7; reject live-rewrites-everything stance |
| 6 | Authoritative facts vs derived projection; proposal-only maintenance | Mnemosyne arXiv:2607.00269v3 | borrow the two invariants; **defer** the CTL/StateView substrate | substrate would be a second ledger |
| 7 | Replay-or-fork / consumed authority stays consumed | ACRFence arXiv:2603.20625v1 | borrow now (invariant) | closes a gap in repeated/interrupted migration |

## What I could not establish (knowledge/access gaps)

- **No search tool.** The web-search tool returned `DeepSeek search has no API key`, so source discovery
  relied on direct URLs and the arXiv API. It is possible other directly relevant primary sources were
  never surfaced. This is an access gap, not a negative finding.
- **Docs are unversioned.** The LangGraph doc pages carry no release marker; I pinned behavior to a
  specific commit of the code (2026-10-03) and to PyPI `langgraph-checkpoint==4.2.0`. A later docs page
  may differ from that commit; the commit is the material version here.
- **DeltaChannel is documented as beta** ("API and on-disk representation may change"), so the
  prune/snapshot hazard I cite is a moving target and its storage details should be treated as
  unstable.
- **Papers are not replications.** Mnemosyne is the authors' own artifact; its theorems are conditional
  on stated assumptions and its benchmarks are self-run. ACRFence explicitly does not implement or
  evaluate its mitigation. Neither can establish anything about our candidate.
- I did **not** run any local implementation test, native actor, or live system: per the brief, research
  never proves our candidate correct.

## Limits of this report

Original research input only. Host authors dispatch and judges these results; Sideagent records
locators/identities/duties, not semantic acceptance. Existing receipts/index/Workflow remain
authoritative; no second framework or ledger is proposed. The sole implementation owner later updates
project docs. This report does not self-finalize and does not claim any finding has been adopted.

No `HUMAN_DECISION_REQUIRED` gate is raised: every borrow above is either a restatement of an existing
design rule or a small local test/QA addition inside the already-granted #255 research scope. Nothing
here proposes new authority, a new framework, or new infrastructure.
