# Finalization summary — issue #285 (DDD phase 6: VRPAI/CAD analysis case)

## Delivered

- `docs/ddd/cases/vrpai-cad-analysis.md` — phase-6 Q2 analysis case, analysis only.
- `docs/ddd/context-map.md` — consumer section only (row + `consumer-*` grouping).

**Q2 result.** The VRPAI/CAD consumer bridge exposes a **published, versioned, closed**
`kaola-delegator-heartbeat/1` envelope (`scripts/kaola-record-contract.py:22`) **plus an ad-hoc
semantic/prose layer**; the separate VRPAI↔CAD `cad.execution-envelope.review.20261006` /
`cad.runtime-receipt.review.20261006` wire contract is a documentary **proposal**, not a negotiated
protocol.

**Counter-example verdict.** A context pack **does not apply** at this seam: it would restate an
already-enforced contract, and a pack never carries authority, so it cannot affect the
prose-relocation gap. The method's simplified form is the fit.

## Candidate

- Branch `workflow/issue-285`, commit `3f8d3f912fb2b051d444112c6bed987eb582bb6e`
  (parent main `4c30b71d`; 0 behind `origin/main` at finalize time).
- Host verdict on this candidate: **ACCEPTED** (docs-only; spot-checked
  `scripts/kaola-record-contract.py:22` and
  `vrpcadcore/.kaola/crossproj-wire-contract-confirmation-20261006/decision.md:39`; consumer model
  kept `[ASSUMPTION]`; suite marked not executed; no consumer file written).

## Evidence locations

- `docs/ddd/cases/vrpai-cad-analysis.md` §7 — KPR and consumer evidence read, with sha256 for the
  read-only consumer files.
- `docs/ddd/context-map.md` — `consumer-*` section.
- Run folder `.cache/final-validation.md` — recorded validation (below).

## Known failures or unverified scope

- `./scripts/render-skills.py --check` exits 1 on the **pre-existing** stale protected Grok Bot pin
  (`3de9f61a`; 93 identical `pin: P may differ from 3de9f61afbfa …` lines). Not caused by, and not
  fixed by, this change.
- The cited record-contract suite was **not executed here**: `./scripts/validate.sh --suite
  test-issue-259-record-contract` selects the suite but aborts at the mandatory render-check with
  exit 1, before any suite runs. Contract claims therefore rest on the source read at `4c30b71d`.
  Direct contract-suite runs were rejected (they inherit `KAOLA_ACP_*` and could touch live
  sessions) and were not retried.
- The consumer's internal domain model (revision identity, task semantics) remains `[ASSUMPTION]`.

## Validation

classification: final_validation_failed
green: false
mode: final-validation

.cache/final-validation.md does not record `verdict: pass` (column 0) — the agent's own validation did not pass (found verdict: fail)

.cache/final-validation.md is present but does not record `verdict: pass` (column 0). The agent's own validation did not pass — remediate and re-record, or fix the failing checks before finalize.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/ddd/cases/vrpai-cad-analysis.md
- docs/ddd/context-map.md

## Follow-Up Items

- None filed. The stale protected pin is a pre-existing, reported condition; this run did not file
  or modify it.

## Readiness

Review-ready candidate accepted; finalization pending the sink transaction. No consumer file was
written, and no consumer session, timer, orchestration, task graph or code was touched.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

