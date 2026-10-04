# Issue 253 finalization summary

## Delivered

`execute`'s `publish()` stamps `evidence.blocked_attempt` only when a real blocked row exists. A ready item that has not reached the executor no longer receives the placeholder reason `missing`. Prior status, reason, and correlation stay as they were. A real block still stamps. An uninterrupted admission still replaces that snapshot, so a real earlier stamp is cleared when the retry is admitted.

`collect`'s `publish()` does not write this stamp. It copies collected rows and sets `phase` to `collection`, so it was left unchanged.

The regression fixture reads the dispatch index after the first publish. The generated dispatch copy matches `scripts/kaola-dispatch.py`. The Grok Bot bridge stays at the unpinned content stage and is not saveable. No install, tag, release, or pin.

No tracked doc described the false pre-executor stamp. Those docs are unchanged.

## Candidate

Candidate: `2d616752492e79e25205d535ae1a7f7bb19244df`
Subject: `fix(dispatch): stamp blocked_attempt only for a real block`
Branch: `workflow/issue-253`
Worktree: `/Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-253`
Parent and baseline main at acceptance: `531ed487f60a95cfb4cd55e08e36f7a393acae66`

The Host accepted this commit. The stamp fix, the first-publish fixture, the generated dispatch copy, and the content-stage bridge return are unchanged. This close-out does not amend `2d616752`.

## Evidence

Reused, not rerun, and bound to this commit:

- `./scripts/validate.sh` exited 0. 54 unittest suites, Ran 1076, 54 OK, skipped 0. `FORCE_COLOR` and `CLICOLOR_FORCE` were unset. `NO_COLOR=1` and `CLICOLOR=0`.
- `python3 ./scripts/render-skills.py --check` exited 0. Content stage, unpinned, not saveable.

The binding is `.cache/final-validation.md`, recorded from the issue 253 worktree.

## Known failures or unverified scope

No failure on this candidate. No release, pin, or install is authorized, and none is performed. Issue 253 is the only issue this close-out may close.

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
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-244-dispatch.py

## Follow-Up Items

None. This run filed no follow-up. The measured defect is the change this candidate delivers.

## Readiness

Ready for the merge sink and close of issue 253 only.

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
- kaola-workflow/archive/issue-253/.cache/final-validation.md
- kaola-workflow/archive/issue-253/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-253/finalization-summary.md
- kaola-workflow/archive/issue-253/mission-ledger.jsonl
- kaola-workflow/archive/issue-253/workflow-state.md
