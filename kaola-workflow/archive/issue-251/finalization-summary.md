# Issue #251 finalization summary

## Delivered

Added the on-demand public-research reference and reachable pointers from the main Runner dispatch entry, substantive task-failure guidance, and QA planning guidance. Regenerated Skill copies and build manifests through the existing renderer. Doc impact: documentation and template guidance only.

## Candidate

Accepted implementation commits, unamended:
- 01ad8b0355ea03d7eb7dd684dab364087872bb98; parent bb4832bfb64b9a6a972cc1964b92c1ef7b1d9ecc; feat: add public-research reference with failure and QA pointers (#251).
- 7bc7c62b8a133ef45e269158ba925a3dfe53dfa3; parent 01ad8b0355ea03d7eb7dd684dab364087872bb98; docs: link public research from main Runner entry (#251).

Branch: workflow/issue-251. Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-251.
Claim digest: cec65e099515adb6d92bcf8045554fb2f9d820dd68a834fe503a8de103ab79dd.
Session marker: s-28805-mus51hrd. Same existing issue-251 claim; no replacement claim.

## Acceptance

The Host explicitly accepted this replay in the current conversation and authorized installed Kaola-Workflow finalization for issue 251. The recorded merge sink and issue closure are authorized. All three mission-ledger outcomes are done.

The accepted template, rendered main Skill and public-research/failure/QA references match the previously accepted delivery. Preservation checks against bb4832bf confirmed #246 wait and role wording, including every Host assignment using --no-wait; scripts/kaola-acp.py and generated copies; #250 holds; and tests/contract/test-issue-244-dispatch.py still expecting start-timeout at the hang assertion. Budget ceilings remain 17408 and 8192. No implementation bytes changed after validation.

## Evidence

On candidate 7bc7c62b8a133ef45e269158ba925a3dfe53dfa3:
- Each replay regenerated outputs with ./scripts/render-skills.py --write; renderer-owned build conflicts were replaced from sources, never hand-merged.
- ./scripts/render-skills.py --check exited 0, budgets OK.
- env -u FORCE_COLOR -u CLICOLOR_FORCE NO_COLOR=1 CLICOLOR=0 ./scripts/validate.sh > /tmp/kpr-251-replay-validate.log 2>&1 exited 0. Durable log: .cache/replay-validation.log. The installed recorder binds the reused verdict to this candidate in .cache/final-validation.md.
- Main Skill: 17306/17408 bytes. All 50 rendered references <=8192 bytes. Near-ceiling references: Runner dispatch-collect 8142, heartbeat-skeleton 8088, zcode-host-dispatch 8185, host-startup 8181; Delegator handoff 8185.
- The mission ledger records source equality, preservation checks, commits, and prior outcomes; finalization archives it without changing done lines.
- .cache/resume-receipt.json records the installed resume command from the issue worktree: resumed false, reason no active workflow project, exit 1. The existing main-resident state/ledger identify this claim; continue it without asserting resumed true or creating a replacement.

## Known limitations and unverified scope

Live decision behavior remains unverified. No research task was invented and no new live research/smoke exercise was performed. Validation named a watchdog SKIP on Bash 3.2; the suites ran unwatched and the full script exited 0. Historical missing-main-pointer failure on 07dfaf31 was resolved by the accepted main-entry pointer and replay; it does not describe the final candidate.

Protected commits remain unamended. Do not edit kaola-workflow/archive/issue-246 or untracked docs/harness-acp-*.md. No install, release, or tag is authorized or performed.

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
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/public-research.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/task-failure.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/public-research.md
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/task-failure.md

## Follow-Up Items

None discovered in this documentation-only replay. Live decision behavior is an explicit unverified boundary, not a fabricated research assignment or follow-up issue.

## Final Readiness

Ready for the authorized installed finalization and merge sink. Publication, issue closure, archive, and cleanup must be established from lifecycle receipts and final remote/local checks.

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
- kaola-workflow/archive/issue-251/.cache/final-validation.md
- kaola-workflow/archive/issue-251/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-251/.cache/resume-receipt.json
- kaola-workflow/archive/issue-251/finalization-summary.md
- kaola-workflow/archive/issue-251/mission-ledger.jsonl
- kaola-workflow/archive/issue-251/workflow-state.md
