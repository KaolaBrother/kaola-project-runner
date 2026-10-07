# Issue #284 finalization summary (DDD phase 5 — KW C8 seam pack)

## Delivered

Phase 5 of the optional DDD component (#284) — the KPR <-> Kaola-Workflow seam (C8, ADR-7
"one contract with two named views"):

- `docs/ddd/packs/kw-c8-seam.md` — `kaola-ddd-pack/1` pack: vocabulary, inputs/outputs,
  invariants, dependency contracts (4 seams mapped to existing KPR suites, 2 named gaps),
  acceptance, expected-change surface, evolution, evidence. Records the KW source read at
  `16cab12d`; all Kaola-Workflow citations use the `KW/` prefix.
- `docs/ddd/context-map.md` — the `kw-model` section rewritten with the Q1 evidence (language,
  invariants, change coupling); three candidate KW contexts named; the grouping stays
  `candidate`; the phase-4/6 rows merged from `origin/main` are preserved.

Q1 result: **KW is several candidate contexts, not one** — `kw-run-lifecycle`, `kw-validation`,
`kw-install-editions`; the exact split is left open with three settling conditions (a KW-side
model/ownership statement; function-level co-change; per-area change rate as areas leave
`claim.js`).

## Candidate

`a1fb5f0e` on `169dd49a`, rebased onto `origin/main` `21ec9a37`. `169dd49a` is the rebase of the
reviewed candidate `f846c940` (context-map conflict resolved keeping both sides' rows);
`a1fb5f0e` is the Host-requested repair of the pack's citations.

## Acceptance

Host **ACCEPTED** `a1fb5f0e` (Host re-ran main's checker against the worktree: result `ok`,
c1-exact-stop / c4-state-retire / kw-c8-seam all `ok`, 0 errors) and authorized guarded finalize.
Q1 answer, the seam table and the KW-at-`16cab12d` citations were accepted as reviewed earlier.

## Evidence

- Checker (`kaola-ddd-check/1`, merged in #282): `python3 scripts/kaola-ddd-pack.py check --repo .`
  → `result: ok`, `counts {ok: 3, invalid: 0, unsupported: 0}`; `kw-c8-seam`, `c4-state-retire`
  and `c1-exact-stop` each `ok` with no findings.
- Affected-scope validation (exit 0):
  `python3 scripts/kaola-ddd-pack.py check --repo . && python3 tests/contract/test-issue-133-mission-ledger.py && python3 tests/contract/test-issue-72-session-naming.py && python3 tests/contract/test-issue-75-codex-compact-hook.py`
  — direct suite runs: test-issue-133 6/6 OK, test-issue-72 16/16 OK, test-issue-75 37/37 OK.
- `./scripts/validate.sh --suite …` stops at the inherited stale Grok Bot pin `3de9f61a` before
  running any suite (known inherited condition; reported, not worked around). The cited suites were
  therefore run directly.
- Kaola-Workflow read read-only at `16cab12d41cd72818c40f3773068145b35f3f776` (`main`, clean);
  never written or branched. No consumer project written.
- `.cache/final-validation.md` recorded this worktree (`validated_candidate_hash` binds the
  rebased tree).

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "e2ad97bc7001d443714bb3db8c0e893e58ac07520caadbbe1fa9a51c598c7837" != current code-tree hash "5c0484e708526a46c1f60bca2e1c9cacb3d82bb321a4008589edf80f328ff939" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/ddd/context-map.md
- docs/ddd/packs/kw-c8-seam.md

## Follow-Up Items

- None filed by this run. The pack records two named seam gaps rather than filing them: the ADR-7
  "one contract with two named views" digest alignment is P4 (#277) design; and no suite exercises
  a real KW `workflow-state.md`. Neither is a defect in this issue's scope.

## Readiness

Ready to finalize and sink: candidate verified by the merged checker, affected suites green, KW
untouched, no protected path staged or modified.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-284/finalization-summary.md
