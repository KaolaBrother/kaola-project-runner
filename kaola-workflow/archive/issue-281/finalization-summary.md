# Finalization summary — issue #281 (DDD phase 2: C4 retire seam fixtures)

## Delivered

Contract fixtures only, for the measured seam gaps G1, G2, G3, G4, G7, and G8 in
`docs/ddd/packs/c4-state-retire.md`. No product behaviour change.

- `tests/contract/test-issue-255-lifecycle-state.py`
  - `StateTool.test_a_v1_file_is_legacy_format_on_retire` (G1)
  - `StateTool.test_retire_names_record_missing_and_evidence_required` (G2)
  - `ConsolidatedDispatch.test_retire_reads_the_index_execute_and_collect_wrote` (G7)
- `tests/contract/test-issue-259-record-contract.py`
  - `RecordContract.test_an_accepted_task_without_cite_is_cite_required` (G3)
  - `RecordContract.test_a_pending_reclaim_stone_is_kept_and_blocks_its_id` (G4)
  - `RecordContract.test_index_mirror_error_is_reported_after_retire_writes` (G8)
- `docs/ddd/packs/c4-state-retire.md` — closed seams name those tests and the fixture
  commit; the Evidence section records the six oracle bites. G5, G6, and G9 stay
  `suite: none` for issue #286.

## Candidate

- Accepted pre-rebase candidate `1290f3f633ff5e69f33b1a198a3681d897194fb4`
  (fixtures `7815e0b43c3143851631d437e7ce872697c23bb0`, pack lines
  `9bd6a2eadaf6afdefb454ec54b2a2c3b7f9865d6`, oracle bites
  `1290f3f633ff5e69f33b1a198a3681d897194fb4`). Host verdict: **ACCEPTED**.
- Rebased onto `origin/main` `60e9e71726569b050c1b16a9ff432d20de533519` with no
  conflicts. Published tip of the implementation:
  `876176e0d4dacc21ef8aebfc0f85fb80c2d250f4` (oracle bites), parent
  `a39470c1c9a1d9f99e60965882bdc17be02d27ee` (pack lines), parent
  `a6d07aaebd4fa4333db22b3571e028d45796781e` (fixtures).
- The pack still cites the accepted pre-rebase fixture hash `7815e0b4`; rebase
  replayed that text unchanged.

## Evidence locations

- `docs/ddd/packs/c4-state-retire.md` — suite lines and ## Evidence oracle bites.
- Direct suite logs: `/tmp/kpr-281-rebase-255.txt` (131 tests, 74.408s, OK) and
  `/tmp/kpr-281-rebase-259.txt` (63 tests, 29.885s, OK).
- Run folder `.cache/final-validation.md`.

## Known failures or unverified scope

- `./scripts/validate.sh --suite` for both suites still exits 1 at the inherited
  stale protected pin `3de9f61afbfa` (`render-skills.py --check` before the suite
  body). The pin was not edited. Suite results above are direct `python3` runs.
- G5, G6, and G9 remain open for issue #286. No product defect was exposed by
  the fixtures.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "2e7bcbb5a86bad5471078730dd75802dd84d1c37a82e754d1a8aa0e03b60c6d2" != current code-tree hash "b5aaedaa83a64ca9263d55a3366894dafa81bb470b2b8fcedc7e91bbb1a7c9c6" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/ddd/packs/c4-state-retire.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-259-record-contract.py

## Follow-up issues

- Filed: none. G5, G6, and G9 already belong to open issue #286.

## Final status

- Ready for the guarded merge sink onto `origin/main`.

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
- kaola-workflow/archive/issue-281/finalization-summary.md
