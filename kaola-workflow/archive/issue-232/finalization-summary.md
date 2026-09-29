# Finalization summary — issue #232

## Delivered

- Added ACP layer preparation guidance to the existing runtime-aware installation flow. It reuses the selected runtime result, checks actual ACP components against verified versions, respects independent update boundaries, configures only ACP communication, and reports readiness with concrete prerequisite recovery actions.
- Unified README installation guidance into one short link. The shared platform guidance and executable DSH harness inspection now live in `docs/api.md`; the DSH platform manifest and generated references point to that section.
- Updated the stale issue-118 assertion to the current wording while retaining fresh-session behavior for new work and same-assignment-only resume coverage.

## Candidate

- Branch: `workflow/issue-232`
- Candidate commit: `ab76f42f` (`docs: point DSH harness check to API guide`), rebased onto current main `bdb21696` (the #231 sink).
- Delegator final review: PASS for the prior candidate `910706d9`; this candidate contains only the authorized #231 integration and generated-reference correction after that review.

## Evidence locations

- Final validation receipt: `.cache/final-validation.md` in this run folder, bound to the candidate worktree hash recorded there.
- Focused contract coverage: `tests/contract/test-issue-118-seat-cap.py`.
- Installation guidance and DSH harness evidence: `docs/api.md`.
- Final candidate diff: `git diff bdb21696..ab76f42f`.

## Known failures or unverified scope

- No runtime installation or live ACP communication was performed; this issue prepares installation-time guidance only.
- The full validation suite was not run, per the accepted scoped-check instruction. No focused check failed.
- No release, tag, or machine installation action was performed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- README.md
- docs/api.md
- platforms/dsh.yaml
- skills/dsh-kaola-project-runner/references/acp.md
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- tests/contract/test-issue-118-seat-cap.py

## Follow-Up Items

- #233 already exists with a non-empty body and was OPEN before the sink. The minimal test assertion correction is included in this candidate. After the merge is verified, post the resolving commit and the existing 18/18 result on #233, then close it; do not create or claim a duplicate issue.

## Final readiness

ARCHIVED AFTER FINAL GIT GATE — Delegator final review passed, the rebased integration delta is scoped, and the affected checks pass. The merge sink and issue closeout remain to be recorded by the standard finalize transaction.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-232/.cache/final-validation.md
- kaola-workflow/archive/issue-232/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-232/finalization-summary.md
- kaola-workflow/archive/issue-232/mission-ledger.jsonl
- kaola-workflow/archive/issue-232/workflow-state.md
