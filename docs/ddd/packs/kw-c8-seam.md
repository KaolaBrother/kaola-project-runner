---
pack_schema: kaola-ddd-pack/1
id: kw-c8-seam
status: current
owner: host
context_primary: kw-model/C8-kw-bridge
contexts_touched: kw-model/kw-run-lifecycle, kw-model/kw-validation
baseline_commit: 21ec9a3754aaaecd25350ae995f4704ab9ea441e
related_issues: 279, 280, 284, 277, 270
---

# Pack — the KPR <-> Kaola-Workflow seam (C8, ADR-7 "one contract with two named views")

Work unit: the read-only engineering seam between KPR (`kaola-project-runner`) and
Kaola-Workflow (KW). KPR's control-plane Host reads KW run records; KW owns their schema and
their write. ADR-7 frames the shared part as **one contract with two named views** — the
alignment target is a contract per shared artifact, not a merge of implementations.

This pack is written from KW source **read-only**. No KW file is written, branched or run
mutating. Q1 (is KW one context or several) is resolved in
[`../context-map.md`](../context-map.md); this pack uses the candidate context names that section
introduces.

**Citation convention.** KPR paths are written unprefixed and are relative to this repository
(e.g. `templates/orchestrator/references/issue-dispatch.md`). Every Kaola-Workflow path is written
with a `KW/` prefix and is NOT a path in this repository: it lives in the Kaola-Workflow checkout
read read-only at `16cab12d41cd72818c40f3773068145b35f3f776`, e.g.
`KW/scripts/kaola-workflow-claim.js:1-16`. KPR-side design records used here:
`docs/designs/ddd-component-2026-10-07/design.md` (the optional DDD component, `kaola-ddd/1`) and
`kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/design.md` plus
`kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/adr.md` (the component cut and ADR-7).

Context names follow [`../context-map.md`](../context-map.md): `<candidate grouping>/<component>`.
`kw-model/C8-kw-bridge` is the KPR-side component that faces KW. The seam reaches two KW candidate
contexts: `kw-model/kw-run-lifecycle` (the ledger and claim records) and
`kw-model/kw-validation` (the tree-digest views).

## Vocabulary

| Term | Meaning in this unit | Defined at |
|---|---|---|
| C8 / KW bridge | The KPR component that faces KW. Its one implemented form today is the control-plane Host reading KW artifacts read-only; no shared process, schema or store is created. | `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/design.md:33`, `docs/designs/ddd-component-2026-10-07/design.md:146-147` |
| "one contract with two named views" | ADR-7's rule: a shared artifact gets ONE contract with named views, not one function or two divergent implementations. Its current instance is KW's code-tree digest pair (finalize gate vs landable record). | `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/adr.md:35-38` |
| mission ledger | KW's run coordination record: one JSON object per line, keys `n`/`name`/`details`/`status`; the run's sole coordination record, written by the run's Main Orchestrator. | `KW/scripts/kaola-workflow-adaptive-schema.js:58-68`, `KW/docs/decisions/0027-the-mission-ledger.md:31-47` |
| `{n,status}` projection | KPR's read of the ledger: `done` lines / total lines, plus the `failed`/`blocked` rows. It never opens `details` except to decide one mission. | `templates/orchestrator/references/issue-dispatch.md:63-69` |
| claim / `workflow-state.md` | KW's claim/sink/liveness record, written once at claim and patched only for sink and terminal closure. Carries `issue_number` and the claim identity block. | `KW/docs/workflow-state-contract.md:119-122`, `KW/docs/workflow-state-contract.md:243-284` |
| `claim_repository_id` / `issue_number` | The identity pair KPR checks before showing issue progress. | `templates/orchestrator/references/issue-dispatch.md:52-53`, `KW/scripts/kaola-workflow-adaptive-schema.js:129` |
| `codeTreeHash` / `computeCodeTreeHash` | KW's finalize-gate code-tree hash. Canonical for the gate; read from the shared kernel by both producer and gate. | `KW/scripts/kaola-workflow-adaptive-schema.js:1124` |
| `computeLandableTreeDigest` | KW's SEPARATE landable-tree digest over the same visibility band, a different algorithm that yields a different value. Recording it as the candidate hash buys `final_validation_stale`. | `KW/scripts/kaola-workflow-validation-runner.js:554`, `KW/scripts/kaola-workflow-validation-runner.js:1167-1172` |
| "stale" (collision) | Same word, three models: `lane_bucket: stale` (resume age), `chains_stale` (chain receipt vs head), `final_validation_stale` (candidate-hash vs tree). Listed because the pack must not coin a synonym across them. | `KW/scripts/kaola-workflow-adaptive-schema.js:292`, `KW/scripts/kaola-workflow-adaptive-schema.js:1244`, `KW/scripts/kaola-workflow-adaptive-schema.js:1461` |
| "receipt" (collision) | Same word, several schemas in KW: chain receipt, sink receipt, closure receipt, global-contract receipt. The C8 seam names only the ones it reads/aligns. | `KW/scripts/kaola-workflow-adaptive-schema.js:867-870`, `KW/scripts/kaola-workflow-closure-contract.js:5-11`, `KW/scripts/kaola-workflow-global-contract.js:12` |
| read-only | The direction rule: "the Runner never writes" any KW artifact. | `templates/orchestrator/references/issue-dispatch.md:60-61` |

## Inputs and outputs

| Direction | Artifact | Schema / version | Owner of the format |
|---|---|---|---|
| in | KW mission ledger `<canonical-root>/kaola-workflow/.ledger/issue-<N>.jsonl` | one JSON object per line; keys exactly `n`/`name`/`details`/`status`; `status` ∈ `todo`/`in-flight`/`done`/`failed`/`blocked` | KW (the global Workflow contract); KPR reads only (`KW/scripts/kaola-workflow-adaptive-schema.js:58-68`) |
| in | KW `workflow-state.md` | flat claim/sink/liveness blocks; `issue_number`, `claim_repository_id`, branch/worktree, closure facts | KW (claim scripts); KPR reads only (`KW/docs/workflow-state-contract.md:243-284`) |
| in | KPR rendered surfaces that carry the read | `kaola-project-runner` Skill references rendered from `templates/orchestrator/` | KPR (`templates/orchestrator/references/issue-dispatch.md`, `templates/orchestrator/references/host-startup.md.tmpl:135-146`, `docs/architecture.md:274`, `docs/issue-dispatch-display.md`) |
| out | KPR progress projection | stdout only: `done / total` + `(n,status)` for `failed`/`blocked`; absent ledger → `unknown` | KPR, display only, never stored (`templates/orchestrator/references/issue-dispatch.md:63-69`) |
| design-intent (not built) | the ADR-7 aligned tree-digest contract "one contract with two named views" | not yet specified; today two KW-side digests with distinct semantics | KW owns both views; the reconciliation text is P4 (#277) design (`kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/adr.md:35-38`, `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/design.md:18`) |

## Invariants

- **I1 — The ledger has one writer, and it is not KPR.** Boundary: the ledger file. KW's Main
  Orchestrator writes it at three moments; KPR only reads.
  `templates/orchestrator/references/issue-dispatch.md:60-61`;
  `KW/docs/decisions/0027-the-mission-ledger.md:44-47`.
- **I2 — Ledger shape is fixed.** Boundary: the ledger file. Keys exactly
  `n`/`name`/`details`/`status` in that order; no header or goal line; `status` from a closed set.
  `KW/scripts/kaola-workflow-adaptive-schema.js:67-68`.
- **I3 — The ledger lives only in the main checkout.** Boundary: main checkout vs child worktree.
  Gitignored, never mirrored into a worktree; at archive it moves to
  `kaola-workflow/archive/<project>/mission-ledger.jsonl`.
  `KW/docs/workflow-state-contract.md:105-118`.
- **I4 — Progress is a count, not a lifecycle verdict.** Boundary: KPR display vs KW lifecycle.
  An absent file is `unknown`; a missing file or all-terminal lines alone prove neither archive,
  finalize-in-progress, nor a reason to wait. `templates/orchestrator/references/issue-dispatch.md:63`,
  `templates/orchestrator/references/issue-dispatch.md:77-81`.
- **I5 — Identity precedes progress.** Boundary: KPR dispatch naming vs KW claim identity. The
  claimed `workflow-state.md` `issue_number` must equal the dispatch name's `ISSUE` under the same
  repository identity. `templates/orchestrator/references/issue-dispatch.md:52-53`.
- **I6 — KW is untouched.** Boundary: repository ownership. KW keeps claim, ledger, worktree and
  finalize; the seam adds no shared-schema write, no KW change, no new KW state.
  `docs/designs/ddd-component-2026-10-07/design.md:146-147`,
  `docs/designs/ddd-component-2026-10-07/design.md:197-201`.
- **I7 — Two views keep distinct semantics until reconciled.** Boundary: KW validation. ADR-7
  aligns the code-tree digests to one contract with two named views; it does not erase the second
  function, and the digest pair stays deliberately different algorithms.
  `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/adr.md:35-38`; `KW/scripts/kaola-workflow-validation-runner.js:1167-1172`.

## Dependency contracts

Each bullet is one seam: provider → consumer, contract version, and the suite or gap. A suite is
named only where a KPR suite's assertion exercises the seam; anywhere else is a gap.

- KW mission-ledger writer → KPR Host read-only `{n,status}` projection. Contract version: the
  schema is owned by the global Workflow contract; KPR states "the global Workflow contract. The
  Runner never writes." suite: test-issue-133-mission-ledger.py
- KW ledger shape/location → KPR: absent is `unknown`, no Markdown Mission List fallback, the repo
  ignores `kaola-workflow/.ledger/`, archive moves to
  `kaola-workflow/archive/<project>/mission-ledger.jsonl`. suite: test-issue-133-mission-ledger.py
- KW claim identity (`workflow-state.md` `issue_number` / `claim_repository_id`) → KPR dispatch
  naming and its unknown-fallback cases. suite: test-issue-72-session-naming.py
- KW ledger + `workflow-state.md` reload after compaction → KPR compact-recovery payload (which
  must teach reading both records and "do not re-intake, re-claim, restart").
  suite: test-issue-75-codex-compact-hook.py
- KPR read-only discipline (the Runner never writes a KW artifact). suite: test-issue-133-mission-ledger.py
- KW code-tree digest views → the ADR-7 "one contract with two named views" alignment.
  suite: none (gap: the digest pair (`computeCodeTreeHash` vs `computeLandableTreeDigest`) is
  KW-internal; no KPR suite asserts any KPR/KW digest alignment, and the reconciliation contract
  text is P4 (#277) design only — `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/adr.md:35-38`)
- KW claim/sink/liveness fields (branch, worktree, sink mode, closure) → KPR lifecycle judgment:
  KPR judges finalize/archive/cleanup "from Workflow and forge records and the responsible owner".
  suite: none (gap: no KPR suite exercises a real KW `workflow-state.md`; the rule is asserted as
  text only, `test-issue-133-mission-ledger.py`, and no live consumer UAT is run here)

## Acceptance

Observable outcomes. Each is asserted by the suite named in the matching contract bullet unless
marked as a gap.

- Reading a present ledger prints `done / total` and flags `failed`/`blocked` rows
  (`1 / 3 [(3, 'blocked')]` in the fixture). Asserted by `test-issue-133-mission-ledger.py`.
- An absent ledger prints `unknown` and never `0 / 0`, with no Mission List fallback. Asserted by
  `test-issue-133-mission-ledger.py`.
- No KPR surface keeps a Mission List, and the repository ignores `kaola-workflow/.ledger/`.
  Asserted by `test-issue-133-mission-ledger.py`.
- The compact-recovery payload names `workflow-state.md` and
  `kaola-workflow/.ledger/issue-<n>.jsonl`. Asserted by `test-issue-75-codex-compact-hook.py`.
- The dispatch display references `claim_repository_id` and `issue_number` and every unknown
  fallback. Asserted by `test-issue-72-session-naming.py`.
- No KPR code writes any KW artifact. Stated as rule text and asserted as text
  (`test-issue-133-mission-ledger.py`); no behavioural suite proves it for every path (gap).
- One aligned digest contract with a named finalize-gate view and landable-record view. Not
  delivered: gap, P4 (#277) design only.

## Expected-change surface

Planning information only. Legitimate work outside it is coordinated with the owner, never refused.

- KPR: `templates/orchestrator/references/issue-dispatch.md`,
  `templates/orchestrator/references/host-startup.md.tmpl`, `docs/architecture.md`,
  `docs/issue-dispatch-display.md`, and this pack. Suites: `test-issue-133-mission-ledger.py`,
  `test-issue-72-session-naming.py`, `test-issue-75-codex-compact-hook.py`.
- KW (read-only for this unit): the ledger contract and its constants
  (`KW/scripts/kaola-workflow-adaptive-schema.js`), `workflow-state.md` fields, and ADR 0027.
  Any of these changing is a KW-owned event; this pack only refreshes citations.
- P1 module moves (#275–#277) may relocate the KPR surfaces above; the pack's owner then refreshes
  the citations. The pack never blocks a move (`docs/designs/ddd-component-2026-10-07/design.md:197-201`).

## Evolution

- **Refresh** when KW moves the ledger path, keys, statuses or `workflow-state.md` identity fields;
  when a KPR rendered surface that carries the read moves. A stale pack is an advisory finding for
  its owner, never a block.
- **Replace the digest gap** when #277 lands the aligned tree-digest contract: the "one contract
  with two named views" bullet gains a real suite or contract reference.
- **Split signal** if KPR ever needs to WRITE a KW record: that would be a new contract on both
  sides, not a widening of this read-only pack.
- **Retire** this pack if KPR no longer consumes any KW read contract (unlikely) or if KW withdraws
  the ledger/Runner contract (`KW/docs/decisions/0027-the-mission-ledger.md:55-64`).
- A finer split of KW's internal contexts does not change this pack: every seam here stays in
  `kw-run-lifecycle` or `kw-validation`.

## Evidence

- KW commit read read-only: `16cab12d41cd72818c40f3773068145b35f3f776` (`main`, clean tree).
  Files read: `KW/README.md:72-217`, `KW/AGENTS.md`, `KW/docs/architecture.md`,
  `KW/docs/workflow-state-contract.md`, `KW/docs/decisions/0016-the-substrate-bookkeeping-over-gates.md`,
  `KW/docs/decisions/0017-the-mission-list.md`, `KW/docs/decisions/0022-machine-global-workflow-contract.md`,
  `KW/docs/decisions/0027-the-mission-ledger.md`, `KW/docs/decisions/0030-forge-and-engineering-lifecycle.md`,
  `KW/docs/api.md:33-62`, `KW/scripts/kaola-workflow-adaptive-schema.js:1-115`,
  `KW/scripts/kaola-workflow-adaptive-schema.js:275-360`,
  `KW/scripts/kaola-workflow-adaptive-schema.js:838-917`,
  `KW/scripts/kaola-workflow-adaptive-schema.js:1118-1157`,
  `KW/scripts/kaola-workflow-validation-runner.js:545-590`,
  `KW/scripts/kaola-workflow-validation-runner.js:1160-1189`,
  `KW/scripts/kaola-workflow-claim.js:1-16`, `KW/scripts/kaola-workflow-classifier.js:430-476`,
  `KW/scripts/kaola-workflow-sink-merge.js:1-16`, `KW/scripts/kaola-workflow-sink-pr.js:1-20`,
  `KW/scripts/kaola-workflow-closure-contract.js:1-13`,
  `KW/scripts/kaola-workflow-install-manifest.js:1-16`,
  `KW/scripts/kaola-workflow-global-contract.js:1-16`.
- KPR commit: `21ec9a3754aaaecd25350ae995f4704ab9ea441e` (this pack's `baseline_commit`, current
  `origin/main`; the pack was rebased onto it). Design: `docs/designs/ddd-component-2026-10-07/design.md`
  (§3, §7), `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/design.md` (§2, §3 C8, §7),
  `kpm/docs/history/kpr/docs/designs/modular-core-2026-10-07/adr.md` (ADR-7). Research:
  `kpm/docs/history/kpr/docs/research/modular-architecture-and-unified-data-2026-10-07.md` §3. Phase 1:
  `docs/ddd/README.md`, `docs/ddd/context-map.md`, `docs/ddd/packs/c4-state-retire.md`.
- KPR suites read for seam coverage: `test-issue-133-mission-ledger.py`, `test-issue-72-session-naming.py`,
  `test-issue-75-codex-compact-hook.py`. No other suite references the KW ledger or `workflow-state.md`
  as a KPR read.
- Checker (`kaola-ddd-check/1`, merged in #282): `python3 scripts/kaola-ddd-pack.py check --repo .`
  reports `result: ok` with `counts: {ok: 3, invalid: 0, unsupported: 0}` — `kw-c8-seam`,
  `c4-state-retire` and `c1-exact-stop` each `ok` with no findings.
- Q1 evidence (language, invariants, change coupling) is recorded in
  [`../context-map.md`](../context-map.md).

Mirror citations: `kpm/…` paths = github.com/KaolaBrother/kaola-project-manager at fixed commit a13c6d6f264cf965ca45a07670dbf46cd1eb1e5f, subpath history/kpr/ — duplicate KPR source copies retired 2026-10-07; full mapping in `docs/kpm-transfer/HANDOFF.md`.
