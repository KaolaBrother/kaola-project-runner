# Issue 238 — Host escalation after substantive worker task failure

## Delivered

One compact Host policy for a worker that substantively fails an engineering task. The authoritative text is `templates/orchestrator/references/task-failure.md`: trigger, Worker failure, Elite failure, and no-recovery, plus the seven acceptance cases. The normal decision path links it from Project Runner steps 2 and 5. The `failed` ledger line, the wake path, and the heartbeat keep list point at that policy and do not restate it. Confirmed quota and account failures stay on their existing rules.

Because HEAD was the v0.6.14 pin, the content stage was reopened so the renderer could accept the orchestrator change. The Grok Bot bridge and guide carry the unpinned placeholder only. No release, tag, install, or CHANGELOG release section.

## Candidate

7f3de9d3d49edb86cbf34013d1df7a2351766e1e, workflow/issue-238.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-238

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host judged the pre-commit diff (22 files, +90/−82, plus the two new policy files in the commit) against the issue scope. This finalize commits that same tree as 7f3de9d3.

Host reruns, all green, and the worker's full suite reused as sufficient evidence:
- `./scripts/render-skills.py --check` — PASS (content stage, budgets OK)
- policy source and generated `task-failure.md` bytes match
- progressive-disclosure test OK
- `./scripts/validate.sh` — exit 0 (12 validate-skill PASS, kaola-grok-bot-verify PASS, no FAILED or SKIPPED)

Delegator, platform, adapter, and holder sources had zero diff. Protected files, including untracked `docs/harness-acp-compat-2026-10-01.md`, were not staged or deleted. The v0.6.14 tag was not moved.

## Known failures or unverified scope

No remaining failure in the accepted checks. No live failure injection. No release, tag, install, or CHANGELOG release section, by the Host boundary for this run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/issue-dispatch.md
- skills/kaola-project-runner/references/task-failure.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/issue-dispatch.md
- templates/orchestrator/references/task-failure.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl

## Follow-Up Items

None.

## Readiness

Ready to merge and close issue #238.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-238/.cache/final-validation.md
- kaola-workflow/archive/issue-238/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-238/finalization-summary.md
- kaola-workflow/archive/issue-238/mission-ledger.jsonl
- kaola-workflow/archive/issue-238/workflow-state.md
