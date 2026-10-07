# Finalization Summary — issue-288

## Delivered

`project --seats` resolves the preset for a live seat started directly through a platform Runner, using the sibling Runner's verified status records when the dispatch index has no assignment. An explicit `--skills-root` remains authoritative, and dispatch-index assignment identity and direct-start fallback behavior are unchanged.

## Candidate

Implementation commit `4660b227ab3263778874fdb765b56fed2914d41c` on `workflow/issue-288`, rebased onto `origin/main` at `836bc41cbd5f60a0404695ac8426840b926327ed`. The implementation commit contains only `scripts/kaola-dispatch.py`, its generated `skills/**` copies, `tests/contract/test-issue-244-dispatch.py`, and `CHANGELOG.md`.

The `CHANGELOG.md` Unreleased section carries `Seats: restart required` for its combined #278/#287/#288 contents because #278 and #287 change the holder. The #288 dispatch-view change alone does not require restarting seats.

## Evidence

- Host acceptance recorded by the user: `test-issue-244-dispatch.py` ran 80 tests successfully, including the direct-seat preset test, and `render-skills.py --check` passed.
- Rebased candidate validation: `/Users/ylmacstudio/.local/bin/bash ./scripts/validate.sh --suite test-issue-244-dispatch.py` — exit 0, 80 tests passed.
- Rebased candidate generated-output check: `python3 ./scripts/render-skills.py --check` — exit 0.
- Final-validation receipt: `kaola-workflow/issue-288/.cache/final-validation.md`; recorded from the candidate worktree and bound to `5621fd54149b493c2952220bc7ec22aac952cd803ecee83d8ecf03aaf03d56b0`.
- The validation harness skipped its watchdog because the detected system Bash is 3.2.57; the suite and checks themselves completed successfully.

## Known failures / unverified scope

No failures in the affected suite or render check. No live platform ACP session was exercised; direct-start attribution is covered by the contract test. The whole validation inventory was not run because the affected suite passed and the task stop boundary is suite-scoped.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-dispatch.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-244-dispatch.py

## Follow-Up Items

None identified in this run.

## Final readiness

Host acceptance and final candidate validation are recorded. Ready to finalize with merge sink and close issue #288.

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
- kaola-workflow/archive/issue-288/.cache/final-validation.md
- kaola-workflow/archive/issue-288/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-288/finalization-summary.md
- kaola-workflow/archive/issue-288/mission-ledger.jsonl
- kaola-workflow/archive/issue-288/workflow-state.md
