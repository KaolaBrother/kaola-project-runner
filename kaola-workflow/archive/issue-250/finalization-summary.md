# Finalization summary — issue-250

## Delivered

Owner-accepted prompt wording only: two replacements in templates/orchestrator/SKILL.md.tmpl and one paragraph immediately before Inquiry commands in templates/kaola-delegator/references/snapshot.md, plus normal generated Skill text/build manifests. Holds keep source/action scope; blocked duties retain next action and reopening condition in existing heartbeat values; assignment-local retry bounds do not pause the project and worker replacement does not reset attempt limits. The existing Delegator inquiry names the specific missing action/condition without selecting a worker, implementation route or retry. Existing #249 reconciliation is preserved.

Original accepted commit: bf6341a8bba45e009af1f3125779557bf89afbaf, unamended; original parent: 65da3996088d681687af7b600d16f6cbaf92b488. Owner accepted this wording and explicitly authorized rebase and installed Workflow finalization.

Rebased implementation tip: 4f90b832645bc327e4f84d004f5cd39dfb2b4df3, based on d5f2881ffe893ea88ba757812d5766334cc666e0. No template/script source conflicts. The only conflicts at both commits were ten generated main-skill-build.json manifests, regenerated with renderer --write (exit 0) and staged as generated files only. The two templates and their corresponding generated text are byte-identical to accepted bf6341a8. No fourth edit, extra mechanism or budget increase.

Main Skill: 17336/17408 bytes (72 spare); Delegator snapshot: 7204/8192 bytes (988 spare). Existing room for #246 is preserved. Documentation impact is those normal templates and generated text only; no CHANGELOG release section.

## Acceptance and evidence

acceptance.md records the owner's acceptance and bounded scope. qa/rebase.txt records original/rebased commit facts and conflict resolution. qa/post-rebase-validate.log and qa/post-rebase-validate.exit record exactly one ./scripts/validate.sh invocation after rebase, exit 0. qa/post-rebase-results.md records the result and limitations. The installed validation recorder bound verdict pass to candidate code-tree hash c8f72e871d8106faff25ebefad5924eb30e1636a66f0c593238fbb44bc68d692 in .cache/final-validation.md; its recorder exited 0.

The current-main timeout test passed with expected start-timeout unchanged. #250 authored no runtime, assertion or fixture edit. The previous parent-reproduced 0.2s status-timeout mismatch is retained in the existing QA record as historical evidence, not claimed as a product fix. All earlier QA evidence is preserved rather than rewritten.

The 86 Bash <4 watchdog skip receipts remain skips; no watchdog coverage is claimed. No live Agent behavior proof or historical timer-delivery proof is added by this documentation run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl

## Follow-Up Items

#246 remains separate and unimplemented here, with the accepted entry byte room retained. Bash >=4 watchdog supervision remains unexercised in this Bash 3.2 environment. No new run-discovered product defect or forge reorganization is filed; the earlier timeout observation is not relabeled as a #250 defect/fix.

## Readiness

The owner-accepted three edits are ready for the authorized normal Workflow close, archive and merge sink. Final closure/publication/cleanup truth belongs to the lifecycle receipts. No release, tag, artifact publication, shared-root install, heartbeat JSON rewrite or session stop is performed.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-250/.cache/final-validation.md
- kaola-workflow/archive/issue-250/acceptance.md
- kaola-workflow/archive/issue-250/finalization-summary.md
- kaola-workflow/archive/issue-250/mission-ledger.jsonl
- kaola-workflow/archive/issue-250/qa/budget.exit
- kaola-workflow/archive/issue-250/qa/delegator-skill.exit
- kaola-workflow/archive/issue-250/qa/diff-check.exit
- kaola-workflow/archive/issue-250/qa/final-budget.exit
- kaola-workflow/archive/issue-250/qa/final-diff-check.exit
- kaola-workflow/archive/issue-250/qa/final-host-contract.exit
- kaola-workflow/archive/issue-250/qa/final-main-skill.exit
- kaola-workflow/archive/issue-250/qa/final-orchestrator-contract.exit
- kaola-workflow/archive/issue-250/qa/final-render-check.exit
- kaola-workflow/archive/issue-250/qa/grok-bot-verify.exit
- kaola-workflow/archive/issue-250/qa/issue-unchanged.exit
- kaola-workflow/archive/issue-250/qa/main-skill.exit
- kaola-workflow/archive/issue-250/qa/post-rebase-results.md
- kaola-workflow/archive/issue-250/qa/post-rebase-validate.exit
- kaola-workflow/archive/issue-250/qa/prompt-review.md
- kaola-workflow/archive/issue-250/qa/rebase.txt
- kaola-workflow/archive/issue-250/qa/render-check.exit
- kaola-workflow/archive/issue-250/qa/results.md
- kaola-workflow/archive/issue-250/qa/sizes.txt
- kaola-workflow/archive/issue-250/qa/validate.exit
- kaola-workflow/archive/issue-250/workflow-state.md
