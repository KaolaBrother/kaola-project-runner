# Fable design review — issue #270

Reviewer: Claude Code Fable 5.1, owner-appointed. Input: research v5 @ `9fc830d1`, six worker originals, dot's analysis. Official pages fetched 2026-10-07. Not acceptance.

## 1. Critique of the "small common core + optional modules" direction

Direction and guardrails are sound; the risks are in what "small" silently absorbs.

**R1. "Current-state projection" is the scheduler back door.** If the core computes frontier, eligibility or "blocked", it owns a decision and is a second scheduler. Improvement: the core stores revisioned facts and serves reads; projections (frontier, dispatch view, Elite summary) stay in consumer code. Test: the core has no vocabulary for `eligible`, `blocked`, `frontier`, `priority`.

**R2. Compatibility layer = second parser for KW.** KW's five artifacts are multi-writer and partly Agent-authored prose (audit §5.2). A compat layer that re-models them must track claim.js/sink-pr.js forever. Improvement: register KW artifacts as *pointers* (path, kind, owner, digest, revision, verified_at), never re-parse or rewrite them, and allow a declared multi-writer kind instead of claiming a single-writer property KW lacks.

**R3. Install vs runtime-off is the wrong boundary; the real one is three states.** KPR already runs without KW. The unresolved cases are *installed-inactive* and *absent-with-orphan-namespace*: define absent / installed-inactive / active per module, and for an unowned namespace mark it, never delete it, never validate it against an absent contract.

**R4. Cross-process is the whole problem, and the references don't solve it.** Pi is in-process single-writer; Paseo/DSH/T3 are single-daemon-owned stores. KPR's topology is Host + Sideagent node + KW scripts + bridge + holder writing concurrently. The core must keep the existing `StateLock`+`os.replace` paths and be measured under that concurrency.

**R5. Embedded DB is dual-write by construction.** Git evidence must survive, so any non-file store needs projections back into Git. Count dual-write and backup/secret handling as fixed costs in dot's comparison, not tie-breakers.

**R6. The three observed failures justify two schema deltas, not a core.** Fact freshness (`verified_at` + authority) and dependency kind (start / acceptance / informational) are small typed-field additions to existing records. Do them first; if they fix the CAD and AI cases, the core must be justified on query/identity/version alone.

**R7. Event store scope must be enforced by type, not prose.** T3-style sequenced events suit worker/dispatch receipts but are a history store; exclude authorization kinds at the schema level so prohibited bookkeeping cannot re-enter via an "events" table.

**R8. Secrets: namespace isolation is necessary, not sufficient.** Enforce at the write path (DSH-style redaction to presence markers, refuse writes containing secret roles) and drill it (§3e).

**R9. Version negotiation needs a refuse/degrade rule.** Paseo's `requirements.paseo` semver and Restate's journal-mismatch error both detect and name a mid-run code/contract change rather than silently continuing. Pick the default now (§4).

## 2. Official-source verification of §5.4 (Restate vs Temporal replay)

The v5 contrast (Temporal full replay from the beginning vs Restate resume at the suspension point) is overstated. Both re-execute deterministic code, skipping recorded steps.

**Restate re-executes the handler and replays the journal.** Request lifecycle (https://docs.restate.dev/guides/request-lifecycle.md): "The service receives the retry request and restarts the execution of the handler." "Whenever the handler performs an action on the Restate context... the SDK checks the journal for the last recorded result. If it finds a previous result, it skips executing that action and uses the recorded result instead." "Execution then resumes by replaying the journal up to the suspension point." Determinism is required: Durable Steps (https://docs.restate.dev/develop/ts/journaling-results): "Non-deterministic operations (database calls, HTTP requests, UUID generation) must be wrapped to ensure deterministic replay." Error RT0016 (https://docs.restate.dev/references/errors): "Journal mismatch detected when replaying the invocation: the handler generated a sequence of journal entries... that doesn't exactly match the recorded journal", caused by code changes without a new deployment or non-deterministic code. Suspension is a resource optimisation (https://docs.restate.dev/foundations/key-concepts: FaaS suspend "without paying for wait time"), not a different recovery model.

**Temporal does not always replay from the beginning.** Workflows (https://docs.temporal.io/workflows.md): "It starts the Workflow code from the beginning, replays the Event History step by step" but "Temporal doesn't always have to start from the beginning if the state is cached." Sticky Execution (https://docs.temporal.io/sticky-execution): "Workers cache the state of the Workflow they execute"; sticky is "the default behavior"; on Workflow Task failure the cache entry is evicted. History is bounded (https://docs.temporal.io/workflow-execution/event.md): warning after 10,240 Events, termination above 51,200 Events; Continue-As-New (https://docs.temporal.io/workflow-execution/continue-as-new.md) starts "a fresh history that picks up where your last one left off."

**Corrected §5.4 statement:** both engines use *re-execution of deterministic code against a durable log, skipping recorded results*; both require wrapping side effects (Activity / `ctx.run`); both push external idempotency outward (v5 already says this correctly). Real differences: log scope (per-workflow history vs per-invocation journal), steady-state replay avoidance (Temporal sticky cache vs Restate suspend-then-replay), explicit history bounds (Temporal numeric limits; no Restate journal limit found on cited pages, unverified), and version-skew naming. KPR lesson: KW's receipt-based step skipping is the same family; the missing piece is *mismatch detection* on code/contract change.

## 3. Validation proposal for the narrow pilot

Scope: read/identity layer over existing artifacts (KPR schemas owned; KW artifacts as pointers). No new store, no scheduler.

Invariants: every read returns a revision and `verified_at`; no torn reads; writes only through existing locked paths; no eligibility vocabulary in the core; no authorization-history kind in any schema; KW artifact bytes untouched by the core.

Drills (≥3 combinations not used for tuning; outcomes judged, not JSON validity):
- a. Concurrency: Host + Sideagent node + KW claim + bridge send in one second; revisions monotonic, no lost update.
- b. Crash: `kill -9` mid claim transaction and mid sink step; resume skips done steps and names the interrupted one.
- c. Stale fact (CAD regression): forge reopen after a local done snapshot; the existing no-eligible boundary re-verifies before deciding.
- d. Dependency kind (AI regression): acceptance-only dependency must not block start.
- e. Secret canary: plant a token in env/auth; after a full cycle grep artifacts, receipts, Git objects: zero hits.
- f. Version skew: v0.9.1 reader vs pilot writer and reverse; migration interrupted then rerun; mismatch refuses with named id and revision.
- g. Module states: KW absent, installed-inactive, active; standalone Platform Runner path byte-identical.
- h. Bookkeeping recurrence: read-only snapshot diff after N heartbeats shows no handled rows or history relocation.
Measures: correct completion, elapsed time, rework, user interventions, resources vs the v0.9.1 baseline on VRPAI/CAD. Run R6's two schema deltas alone first; report whether they close c and d without the core.

## 4. Owner value choices required before design freeze

1. Is files+Git the only durable evidence store, or is a non-Git store acceptable with Git projections (accepting dual-write)?
2. May KW remain multi-writer with Agent-authored artifacts, or is cross-repo KW change in scope?
3. Is any resident service acceptable outside the KPR Host loop (the no-resident rule covers only the Host)?
4. Is a sequenced event store for worker/dispatch receipts allowed given the authorization-history prohibition, and where is the type-level line?
5. Default on KPR↔KW contract version mismatch: refuse or degrade?
6. Which of the three observed failures (stale forge fact, dependency kind, Host self-research) lands first.
7. Dependency posture: pattern-only borrowing vs taking dependencies (Pi experimental, Restate BSL 1.1).
8. Acceptable added heartbeat latency for freshness re-checks.

— End (Host records; reviewer does not self-finalize).
