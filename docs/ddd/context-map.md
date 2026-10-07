---
map_schema: kaola-ddd-map/1
owner: host
baseline_commit: 8b3779c9c9c76e03f6794b5bf5cf6ffb76bd27c0
related_issues: 279, 280, 284, 285
---

# KPR candidate context map (`kaola-ddd-map/1`)

This is a working tool. Brandolini calls a context map "a working tool that allows us to map a
fuzzy situation" (baseline §1). It is not a boundary decision and not a gate.

**Every grouping here is `candidate`.** A grouping becomes `observed` only once this map records
evidence of all three of the following (design §2.2):

- its language;
- its invariants/consistency boundaries;
- its change coupling.

No grouping meets that bar yet. Labels such as core, supporting and generic are hypotheses about
product value (baseline §4), not technical layers. `owner` means content responsibility only
(design §2, revision 2). It is not a lock and not an approval step.

The components C1–C8 and CORE are defined in
[`docs/designs/modular-core-2026-10-07/design.md`](../designs/modular-core-2026-10-07/design.md):26-33.
They are measured function seams, **not** bounded contexts. A component may sit in one grouping
and still be a separate consistency boundary there.

## Names packs use

A pack names contexts as `<grouping>/<component>`, for example
`orchestration-state/C4-state`. `context_primary` is where most of the change lands.
`contexts_touched` lists every other component boundary the unit crosses, including components
in the same grouping. Two components in one language are still two stores, locks or schemas, and
a unit crossing them still needs a contract for each seam. Listing a boundary never forbids a
change to it.

| Grouping (candidate) | Component names | Hypothesis label |
|---|---|---|
| `session-runtime` | `CORE-identity`, `C1-lifecycle`, `C2-adapters`, `C3-events` | core (reliable ACP session lifecycle) |
| `orchestration-state` | `C4-state`, `C5-dispatch`, `C6-recovery` | supporting, possibly a differentiator |
| `build-install` | `C7-render-install` | generic |
| `kw-model` | `C8-kw-bridge` (the KPR-side bridge) plus KW's own candidate contexts `kw-run-lifecycle`, `kw-validation`, `kw-install-editions` | Q1 resolved: KW is several candidate contexts, not one (see the section below) |
| `consumer-*` | VRPAI, CAD (external) | bridge record read in phase 6; consumer domain model still `[ASSUMPTION]` |

## session-runtime — `candidate`

- **Evidence so far:**
  - Vocabulary: holder, `holder_instance_id`, session, receipt, `state` ∈
    {`starting`, `ready`, `agent_exited`, `stopping`, `stopped`, `error`} (`scripts/kaola-acp.py:841-843`),
    `residual_pids`, event cursor.
  - Its own record store (record roots, `kaola-acp-list/1`, `scripts/kaola-acp.py:838`).
  - Its own meaning of **retire**: `retire_record` moves a session's `record.json` aside
    (`scripts/kaola-acp.py:2194-2203`). This differs from the orchestration-state meaning (below).
    That is one concrete language difference, measured in phase 1.
- **Seam with orchestration-state** (pilot pack, C1 → C4):
  - C4 reads C1's `state: stopped` and `holder_instance_id` verbatim, with no translation
    (`scripts/kaola-dispatch.py:4859-4883`).
  - The contract is weak at the producer edge: gap G9 in
    [`packs/c4-state-retire.md`](packs/c4-state-retire.md#dependency-contracts). The default
    `list` omits a stopped seat, so only `list --include-dead` proves a stop to `state retire`,
    and no suite crosses that edge.
- **Second pack, C1 exact stop** ([`packs/c1-exact-stop.md`](packs/c1-exact-stop.md), at
  `4c30b71d`, source identical to `8b3779c9`):
  - C1 and CORE-identity invariants are now recorded: an exact stop is refused before any change
    (I1), and only identity-proven processes are signalled (I2).
  - The C1 "retire" meaning is confirmed again (`scripts/kaola-acp.py:2194-2203`).
  - "stopped" has more than one meaning inside C1. The meaning of the receipt key depends on
    the path, and the record `state` is a separate use (pack I4).
  - New seam gaps: S1/S2, where the dead-holder stop skips the instance check and sweeps
    without `--force` (measured), and S3, where the C1 → C3 mismatch event is unasserted.
- **Open question:** C2 and C3 are still grouped by vocabulary only. C1's invariants are in the
  second pack. Change coupling has not been recorded for any session-runtime component.

## orchestration-state — `candidate`

- **Evidence so far:** see the pilot pack. Vocabulary: record, task, hold, alert, decision,
  `rev`/`revision`/`host_revision`, StateRefusal, verdict, stage, dispatch, `acceptance`,
  disposition, seat, handoff, cite. The invariants are I1–I12 in
  [`packs/c4-state-retire.md`](packs/c4-state-retire.md#invariants).
- **Q3 — do C4 (state) and C5 (dispatch) share one language? Result: yes.** They share one
  language but have two consistency boundaries. Evidence at `8b3779c9`:
  1. *Shared terms, same meaning.*
     - A C5 index row's `task_id` is a C4 task id (`scripts/kaola-dispatch.py:4926`, `:5178`).
     - A C4 task's `dispatch` holds C5 `item_id`s (`:4891-4892`).
     - `session` and `holder_instance_id` are the same identities on both sides
       (`:4918`, `:4926-4935`).
     - `accepted` and `cancelled` mean the same Host judgment in the C4 verdict
       (`VERDICTS`, `:102`) and in the C5 row `acceptance` (`:5184-5199`).
  2. *No translation at the seam.*
     - C4 code reads the C5 `status` vocabulary (`COVERAGE`, `:83`) directly (`:4913`, `:5184`).
     - C4 code writes C5 rows directly: `mirror_task` sets `acceptance` and an
       `acceptance_source` pointer back to the C4 task and rev (`:5169-5200`).
     - There is no anti-corruption or mapping layer. Both live in one module,
       `scripts/kaola-dispatch.py`.
  3. *Two consistency boundaries, not two languages.* The stores, locks and schemas are separate:
     - `heartbeat-prompt.json` + `StateLock` + `kaola-heartbeat-prompt/2`
       (`:92`, `:3556-3574`);
     - the dispatch index + `IndexLock` + `kaola-dispatch-index/1` (`:2784`, `:1605`).

     There is no cross-store transaction: the mirror runs after the state write and reports its
     own failure (`:5152-5166`). In DDD terms these are two aggregates inside one candidate
     context (baseline §2), and the pack still lists C5 as a touched boundary.
  4. *Inconsistencies found are defects inside one language, not a second meaning.*
     - The two C4 readers of C5 `status` disagree on what counts as closed. A deny-list is used
       at `:4913`; an allow-list at `:5184`.
     - Retire's index reader skips the schema/repo identity check that the other index readers
       enforce (`:4906` vs `:605-607`, `:3143`, `:3932`).
     - `TASK_STAGES` is defined twice (`:100` and `scripts/kaola-record-contract.py:156`).

     Pilot gaps G5/G6 measure the first two.
  - *Not measured:* change coupling. Co-change at file level is uninformative because C4 and C5
    share one file. Function-level co-change history was not analysed.
- **Open question:** C6 (recovery) writes into the same state file (the C4 namespace) and uses
  `recovery#<seq>` inputs (pilot I9). Is C6 the same language too? It was not examined beyond
  the two retire seams. Phase 4's second pack crosses C6 only at the carrier's node reclaim
  (`c1-exact-stop` I7) and did not examine C6's language. A C6 pack is still the place to check.

## build-install — `candidate`

- **Evidence so far:** none collected in phase 1. The only input is the vocabulary listed in
  baseline §4 (manifest, `provides`/`requires`, budget, pin, install-verify) and the C7 row of
  the modular-core design (`docs/designs/modular-core-2026-10-07/design.md:32`, `:51`).
- **Open question:** is C7 a separate language, or build tooling that only carries the other
  groupings' schemas? No pack touches it yet.

## kw-model — `candidate` (Q1 resolved: several candidate contexts, not one)

Q1 — *is KW one context or several?* **Result: several candidate contexts, not one.** Evidence is
a read-only source pass over Kaola-Workflow at `16cab12d41cd72818c40f3773068145b35f3f776` (`main`,
clean tree). All three parties the map requires are recorded below. The grouping stays `candidate`:
the exact internal count is not settled, and KW's change coupling is entangled through a shared
kernel (see "not settled" below).

- **Language — distinct vocabularies, with concrete collisions.**
  - *Run lifecycle (claim + ledger + delivery):* claim, project, `workflow-state.md`, worktree,
    branch, lane bucket (`mine`/`live`/`stale`/`ambiguous`), `session_marker`, `claim_ts`,
    `main_root`, resume, `run_posture`, sink mode (`merge`/`pr`), mission,
    `n`/`name`/`details`/`status`, frontier
    (`KW scripts/kaola-workflow-classifier.js:430-476`,
    `KW scripts/kaola-workflow-adaptive-schema.js:58-68`,
    `KW docs/workflow-state-contract.md:243-303`).
  - *Validation/evidence:* chain, edition chain, `.cache/chain-receipt.json`, `codeTreeHash`,
    `computeCodeTreeHash` vs `computeLandableTreeDigest`, candidate binding, `repo_kind`, and the
    typed findings `chains_green`/`chains_stale`/`chains_empty`/`chains_red`/`chains_waived`/
    `final_validation_*` (`KW scripts/kaola-workflow-adaptive-schema.js:1124`,
    `KW scripts/kaola-workflow-validation-runner.js:554`, `:1167-1172`,
    `KW docs/architecture.md:198-248`).
  - *Install/editions:* global contract, runtime-adapter registry, edition, forge, carrier, managed
    region, routing surface, install receipt, `REMOTE_REQUIRED`
    (`KW scripts/kaola-workflow-global-contract.js:9-13`, `KW docs/architecture.md:41-72`,
    `KW docs/decisions/0022-machine-global-workflow-contract.md`).
  - *Collisions (same word, different model — the DDD boundary signal):* **`stale`** is
    `lane_bucket: stale` (resume age, `adaptive-schema.js:292`) AND `chains_stale` (chain receipt
    vs head, `:1244`) AND `final_validation_stale` (candidate hash vs tree, `:1461`). **`receipt`**
    names chain receipt, sink receipt (`adaptive-schema.js:867-870`), closure receipt
    (`closure-contract.js:5-11`) and global-contract receipt (`global-contract.js:12`). KW's own
    kernel splits durable artifacts into four record classes
    `plan`/`claim-sink`/`evidence`/`forge` (`adaptive-schema.js:839`).
- **Invariants / consistency boundaries — separate and separately enforced.**
  - Ledger: one writer (the Main Orchestrator), keys exactly `n`/`name`/`details`/`status` in
    order, three write moments, `done`/`failed` immutable, main-checkout-only, never mirrored
    (`KW docs/decisions/0027-the-mission-ledger.md:31-47`;
    `KW scripts/kaola-workflow-adaptive-schema.js:1664-1715`; KW suite `test-issue-1089-mission-ledger.js`).
  - Claim/sink state: a flat claim/sink/liveness record written at claim and patched only for sink
    and closure (`KW docs/workflow-state-contract.md:243-284`).
  - Durable-kernel ruling: every project-folder artifact is classified
    `record`/`derivable`/`preference`; every `record` write must use the atomic replace
    (`KW docs/workflow-state-contract.md:12-94`; `KW scripts/kaola-workflow-adaptive-schema.js:838-911`;
    KW suite `test-kernel-conformance.js`).
  - Also separate: bundle coherence (`workflow-state-contract.md:336-345`), archive completeness
    and its one hard stop (`:184-221`), the validation freshness band that excludes docs/run state
    (`architecture.md:211-218`), and the release gate (`architecture.md:232-248`).
- **Change coupling — measured, and entangled.**
  - Co-change over the last 250 commits touching `KW scripts/`: `kaola-workflow-claim.js` 42,
    `kaola-workflow-adaptive-schema.js` 17, `sink-pr.js` 13, `sink-merge.js` 11,
    `install-manifest.js` 7, `global-contract.js` 5; `validation-runner.js` 2, `run-chains.js` 1,
    `classifier.js` 0. The highest pair is `adaptive-schema.js` + `claim.js` (9).
  - `kaola-workflow-adaptive-schema.js` is the byte-identical cross-edition drift anchor: every
    constant shared by a producer and a consumer lives there (`adaptive-schema.js:4-19`), and
    `edition-sync.js` materializes it verbatim into the plugin trees
    (`KW docs/conventions.md:142`). That is a Shared Kernel, and it is what keeps the three
    candidate areas from being independent.
  - Counter-evidence to a clean split, recorded not hidden: `kaola-workflow-claim.js` is a
    7806-line monolith that already owns selection, claim, status, worktree, finalization, archive
    and release, so the split is real in *language and invariants* but not clean in *code*.

**Candidate KW contexts (all `candidate`; the exact count is not settled):**

| Candidate context | Language sketch | Consistency boundaries |
|---|---|---|
| `kw-model/kw-run-lifecycle` | claim, project/run, worktree, branch, lane bucket, `workflow-state.md`, mission ledger, finalize, sink, archive, closure | ledger single-writer; claim/sink/liveness; bundle coherence; archive completeness |
| `kw-model/kw-validation` | chain, edition chain, chain receipt, candidate binding, tree digests, `repo_kind`, findings | candidate-bound receipt; freshness band; release gate |
| `kw-model/kw-install-editions` | global contract, runtime adapters, edition, forge, carrier, routing, install receipt | one authoring source; byte-identical kernel; batch preflight; receipt-bound install/uninstall |

**C8 seam relationship (Customer-Supplier / Published Language, read-only).** KPR's control-plane
Host reads the KW mission ledger `{n,status}` projection and inspects `workflow-state.md`;
`kw-model/C8-kw-bridge` is the KPR-side component that faces it. KW owns the schema (the global
Workflow contract) and the write; KPR never writes. Every seam maps to a KPR suite or a named gap
in [`packs/kw-c8-seam.md`](packs/kw-c8-seam.md).

**Not settled, and what would settle it.** The *direction* (several, not one) is evidenced; the
exact split is not. What would settle it: (1) a KW-side model/ownership statement naming its
subsystems; (2) **function-level** (not file-level) co-change, since the `claim.js` monolith
inflates file-level co-change between areas that are not really one model; (3) measuring each
area's change rate as it is extracted out of `claim.js`. Not split out here: the forge/backlog
selection shares the run's `issue`/`claim` language and the same owning script, so it stays inside
`kw-run-lifecycle`; a finer claim-record vs ledger vs delivery split is possible but is not
separated by a language change today.

## consumer-* (VRPAI, CAD) — `candidate`

- **Evidence so far (phase 6, #285; read-only bridge evidence only, no consumer write):** see
  [`cases/vrpai-cad-analysis.md`](cases/vrpai-cad-analysis.md).
  - The outer consumer bridge's own record is a **published** language. Both projects declare
    `schema: kaola-delegator-heartbeat/1`; KPR owns that versioned, closed schema
    (`scripts/kaola-record-contract.py:22`, `:1416`, `:1472-1476`) and exercises it
    (`tests/contract/test-issue-259-record-contract.py`, read at source; suite not executed here —
    see the case §7). The two projects' optional fields differ but are all schema-allowed.
  - The consumer's **semantic payload** is ad-hoc. CAD's governance content that the owner forbids
    outside typed state was carried in prose
    (`vrpcadcore/.kaola/e2s1-d1c7-confirmation-20261006/delivery-log.md:283`;
    [`docs/cad-recurrence-diagnosis-2026-10-07.md`](../cad-recurrence-diagnosis-2026-10-07.md);
    issue #269), with no version or schema.
  - The separate VRPAI↔CAD `cad.execution-envelope.review.20261006` /
    `cad.runtime-receipt.review.20261006` wire contract is a Published-Language **proposal**
    technically confirmed for later docking, but explicitly "not a registered or negotiated
    production protocol"
    (`vrpcadcore/.kaola/crossproj-wire-contract-confirmation-20261006/decision.md:39`).
- **Q2 — do the VRPAI/CAD bridges expose a Published Language? Result: a published envelope with
  an ad-hoc semantic layer.** The bridge record is published and enforced; consumer meaning is not.
  The VRPAI↔CAD cross-project contract is a documented language *proposal*, not a negotiated one.
- **Counter-example verdict (this case's output):** a context pack **does not apply** at this seam.
  It would duplicate the existing enforced schema, and — because a pack never carries authority —
  it cannot affect the prose-relocation gap. The method's simplified form (a short
  vocabulary/invariant note, or nothing) is the fit.
- **Still open:** the consumer's internal domain model (revision identity, task semantics) was not
  read at source in phase 6, so `consumer-*` remains a **candidate** on `[ASSUMPTION]` for
  language/invariants/change coupling. No `observed` label is claimed.

## Change log

Git history is the change log. This map keeps no history section.
