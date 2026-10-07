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
| `kw-model` | `C8-kw-bridge` (KW itself is external) | a separate domain model; internal context count unverified |
| `consumer-*` | VRPAI, CAD (external) | `[ASSUMPTION]`, source not read |

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
- **Open question:** CORE identity, C1, C2 and C3 are grouped by vocabulary only. Their invariants
  and change coupling have not been recorded.

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
  the two retire seams. Phase 4's second pack, or a C6 pack, would be the place to check.

## build-install — `candidate`

- **Evidence so far:** none collected in phase 1. The only input is the vocabulary listed in
  baseline §4 (manifest, `provides`/`requires`, budget, pin, install-verify) and the C7 row of
  the modular-core design (`docs/designs/modular-core-2026-10-07/design.md:32`, `:51`).
- **Open question:** is C7 a separate language, or build tooling that only carries the other
  groupings' schemas? No pack touches it yet.

## kw-model — `candidate` (separate model; context count unverified)

- **Evidence so far:**
  - Separate ownership and artifacts: `workflow-state.md`, the ledger, `chain-receipt.json`
    (`docs/designs/modular-core-2026-10-07/design.md:33`, `:52`).
  - Multi-writer step receipts and a dual code-tree digest, unlike KPR's single-writer state
    file (baseline §4, from in-repo research; KW source not read).
- **Candidate relationship:** Customer-Supplier / Published Language with in-process translation
  at C8 (baseline §4).
- **Open question:** Q1 — is KW one context or several? This is resolved in phase 5 (#284),
  reading KW source read-only. It is never a precondition for KPR packs or B0.

## consumer-* (VRPAI, CAD) — `candidate`, `[ASSUMPTION]`

- **Evidence so far:** none from source. Every statement in baseline §4 is an assumption.
- **Open question:** Q2 — do their bridges expose a Published Language or an ad-hoc field set?
  This is resolved in phase 6 (#285), as analysis of existing bridge evidence only.

## Change log

Git history is the change log. This map keeps no history section.
