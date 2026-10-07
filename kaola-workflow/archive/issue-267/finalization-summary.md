# Finalization summary — issue 267

## Delivered

Tool-kept task-failure rejection count that actually fires on repeated failures, per root's
six-point semantics, delivered through the issue-264 tree (no commits on this branch; tip stays at
`dad228e4`): the count and old binding are kept on unknown-order repairs with a typed
`pending: "binding"` duty (never masked), typed binding = dispatch item + unique delivery receipt +
review cycle together, real responsibility handoff (one verified index transition) resets the
segment with a `same-assignment` next repair, and catalog-declared effort order governs any
effort reset — which no current catalog declares, so the reset-on-effort path is not implemented
and is documented as such. Product code: `scripts/kaola-dispatch.py` (`apply_task_rejection`,
`_incoming_binding`, `_submission_relation`, `_declared_effort_order`), record-contract allowlist
in `scripts/kaola-record-contract.py`, Host guidance in
`templates/orchestrator/references/task-failure.md`. Contract: 29 tests in
`tests/contract/test-issue-267-rejection-count.py` including closed-contract mixed-version
refusal. Working reports: `/tmp/kpr-i267-mask-fix-report.md`, `/tmp/kpr-i267-gap3-report.md`,
`/tmp/kpr-i267-effort3-report.md`.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "e245d6e6625b6128aafde1b7fcdd77a7d63072a2e1e1d7765f128e938bf0ce85" != current code-tree hash "13d011d104abcbc1c01f20c5833f491a55ff06abdcb07cb9b8465f9e9fd805f9" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- scripts/kaola-dispatch.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/task-failure.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/inquiry-report.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/task-failure.md
- tests/contract/test-issue-118-seat-cap.py
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-267-rejection-count.py

## Known limitations

The automatic effort-raise reset is unavailable (no declaration field exists; not merely unused).
Escalation text and count are visible on Host view, Delegator brief and attention surfaces; no
second ledger was added.

## Follow-Up Items

None filed.

## Readiness

Accepted (root's five counter-review rounds concluded; final integrated acceptance rode the 264
candidate). Issue closes through the issue-264 merge sink (recorded set
259,263,264,265,266,267,268). No separate sink; this branch has no commits of its own.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

