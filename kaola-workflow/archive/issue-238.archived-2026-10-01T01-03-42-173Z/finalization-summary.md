# Issue 238 — review correction of the Host task-failure policy

## Delivered

The second run of issue #238 corrects the Host policy after review of `581a8ef9`. `templates/orchestrator/references/task-failure.md` keeps one policy body: the `## Cases` recital is gone, and engine, grant, Expert, and role prohibitions that `worker-profiles.md` already owns are links. Schema, scheduler, and second-heartbeat prohibitions stay in that body. The main Skill has one authoritative link at step 2; step 5, the wake path, and issue-dispatch use short references. A task may move to another already-authorized seat and runtime through existing lifecycle operations; only a bound seat cannot be hot-switched or have its runtime changed in place. An effort-only adjustment does not grant or require a model switch. If an owner's current restriction prevents raising effort, reassignment to another fitting already-authorized Elite remains a recovery before any request for new authorization.

## Candidate

cb6151a74d30ad657e47f05913ece38ac2fee9c1, workflow/issue-238.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-238

## Evidence and acceptance

Host ACCEPTANCE: PASS. The Host judged the actual diff against all four review items and independently measured the same generated UTF-8 bytes: main Skill 17368 (−39, headroom 40), wake 8162 (−29, headroom 30), heartbeat skeleton 8156 (unchanged), issue-dispatch 4733 (−79), task-failure 3765 (−1319). `## Cases` is 0 occurrences (1406 bytes removed). Budgets and `templates/grok-golden/` are unchanged. The v0.6.14 pin is untouched.

Host independent reruns:
- `./scripts/render-skills.py --check` — PASS (budgets OK)
- `python3 tests/contract/test-progressive-disclosure.py` — 15/15 OK

Worker checks on the same candidate bytes, reused:
- `python3 tests/contract/test-issue-118-seat-cap.py` — 18/18 OK

Protected files were not staged, including untracked `docs/harness-acp-compat-2026-10-01.md`. No release, tag, or install.

## Known failures or unverified scope

No remaining failure in the accepted checks. The full unrelated transport suite was not rerun. No live failure injection. No release, tag, install, or CHANGELOG release section.

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
- skills/kaola-project-runner/references/issue-dispatch.md
- skills/kaola-project-runner/references/task-failure.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/issue-dispatch.md
- templates/orchestrator/references/task-failure.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl

## Follow-Up Items

None. This is the same issue's review correction, not a new defect.

## Readiness

Ready for the merge sink, issue #238 closure, a separate archive for this run, and worktree/branch cleanup.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

