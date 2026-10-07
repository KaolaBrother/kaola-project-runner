# Issue #277 finalization summary (P4 slice)

## Delivered

P4 of issue #277 — the Kaola-Workflow read-only original-index bridge, first stage:

- `docs/designs/modular-core-2026-10-07/p4-kw-readonly-index.md` — the P4 contract:
  indexable KW originals (KERNEL_ARTIFACT_REGISTRY records, both ledger locations,
  archive, roadmap), reference-only `{kind, path, sha256, schema_or_unknown}`, typed
  `present`/`absent`/`unsupported`, and the explicit reconciliation of the two named
  digest views (`computeCodeTreeHash` finalize-gate vs `computeLandableTreeDigest`
  landable-record) with KW file:line citations at KW `16cab12d`.
- `scripts/kaola-kw-index.py` — the read-only reader: typed index on stdout, writes
  nothing anywhere, no network, resolves the main checkout for the ledger band. Not
  wired into skills/, templates/, render, or Host dispatch (per-issue scope).
- `tests/contract/test-issue-277-kw-readonly-index.py` — 5-test suite, temp-dir
  fixtures only; registered in `scripts/validate.sh` (`python_suites_all`, lane A).
- Lane-integrity repair: `test-issue-278-record-root.py` assigned to lane B (it was
  in `python_suites_all` with no lane — the suite was red on main and never ran).

P5 (B0 pilot) is NOT part of this run and stays open on the issue.

## Acceptance

Host **ACCEPTED** `14319dd2` (P4 candidate), then authorized guarded finalize.
Rebased onto origin/main `50e950db` cleanly (no conflicts; #281's merge did not
touch validate.sh suite lines) — candidate is now `79c4423a`.

## Evidence

- Post-rebase, direct runs (validate.sh --suite stops at the inherited stale Grok
  Bot pin `3de9f61a` before reaching suites; known inherited blocker, not fixed):
  `python3 tests/contract/test-issue-277-kw-readonly-index.py` — 5/5 OK;
  `python3 tests/contract/test-issue-264-validate-lane-integrity.py` — 4/4 OK.
- Adjacent suites, direct runs: test-issue-133-mission-ledger.py 6/6 OK;
  test-issue-278-record-root.py 10/10 OK.
- Oracle bites (deliberate break → fail → revert, none committed): accept-any
  schema_version → unsupported-case FAIL; stray write in build_index → snapshot
  FAIL; record-view replica converged to '\n'-join → digest-divergence FAIL.
- Reader verified read-only on this repo (typed records; kaola-workflow tree
  byte-identical before/after) and the KW repo unchanged.
- `.cache/final-validation.md` recorded this tree
  (`validated_candidate_hash` binds the rebased worktree).

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "b506d516386cfcc84d8da7ada866120143299a3d01634f0fc75d22f8500caa31" != current code-tree hash "302a2630bb5d84c91fd09536289326bb9af254ba958a62dbbbac63f4907e667f" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/designs/modular-core-2026-10-07/p4-kw-readonly-index.md
- scripts/kaola-kw-index.py
- scripts/validate.sh
- tests/contract/test-issue-277-kw-readonly-index.py

## Follow-Up Items

- None filed by this run. P5 (B0 resident-core pilot) remains tracked on #277;
  cross-repo same-schema validators are a later P4 sub-stage.

## Readiness

P4 slice complete at `79c4423a` on `workflow/issue-277`, review-ready, acceptance
recorded, evidence in place. `issue_action: comment_keep_open` recorded — the
issue stays open for P5.

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
- kaola-workflow/archive/issue-277/finalization-summary.md
