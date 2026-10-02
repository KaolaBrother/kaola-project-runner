# Issue 244 — Capability summary, Sidekick, and dispatch/collect

## Delivered

The Host can project eligible candidates and admit one bounded research, QA, or report plan through the existing platform Runners. A matching unknown delivery is not started or sent again. An already-admitted session that is gone stays on its prior status with reason `session-gone`. Dry-run and an out-of-scope plan do not replace the index. A blocked retry keeps the matching assignment's status and records the attempt as `blocked_attempt`. The capability summary lists eligible preset ids and does not infer capabilities from profile wording.

`scripts/kaola-dispatch.py` and the generated copy are the same bytes. The Grok Bot bridge is the unpinned content stage. No tag, GitHub release, or pin commit.

## Candidate

827bbdc09fea745cce9855a4f5ca9cd6c808e197, workflow/issue-244.
Worktree: /Users/ylmacstudio/Workspace/kaola-project-runner/.kw/worktrees/issue-244
Baseline: 9d0ffca2e51054908e08369de6f0795a88a6515b.
Dispatch entry sha256: 37938ddd3f3306353480c9140dbd0c8de711c9224570591896c5beb20ba50e4d.

## Evidence and acceptance

Outer personal final acceptance: PASS. `/tmp/kpr-fanout-design-20261003/outer-final-acceptance.md`.

Opus v3r2 affected-surface re-review: PASS. `/tmp/kpr-i244-claude-v3review-r2.md`.

Host gate6: PASS. `/tmp/kpr-i244-validate-gate6.log`. `./scripts/validate.sh` on these bytes: render/budget/bridge PASS, dispatch contract 37 OK, holder-binding 4 OK, `residual_pids: []`.

Protected untracked files `docs/harness-acp-compat-2026-10-01.md`, `docs/harness-acp-reverify-2026-10-01.md`, and `docs/harness-acp-compat-2026-10-03.md` were not staged, copied, or deleted. `templates/grok-golden/` was not edited. `templates/grok-bot/accepted-revision.json` stays at stage `content`; the Host owns the later pin.

## Known failures or unverified scope

No failure on this candidate. Retained limits, not new work: the dispatch reference does not state that an out-of-scope plan writes no index; collection after a disappeared session can report `failed` / `turn-failed` with explicit no-session evidence; an unexpected internal exception can still produce a less complete admission-error row. No ordinary-path replay remains. No tag, GitHub release, or pin.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/README.md
- docs/api.md
- docs/dispatch-collect.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/kaola-acp.py
- scripts/kaola-dispatch.py
- scripts/render-skills.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-244-holder-prompt-binding.py
- tests/contract/test-progressive-disclosure.py

## Follow-Up Items

None. No run-discovered defect was filed.

## Readiness

Ready to merge locally and close issue #244. Do not tag, publish, or pin. The Host owns the v0.7.0 release after this merge is on main.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-244/.cache/final-validation.md
- kaola-workflow/archive/issue-244/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-244/finalization-summary.md
- kaola-workflow/archive/issue-244/mission-ledger.jsonl
- kaola-workflow/archive/issue-244/qa/host-bounded-live-qa-plan.md
- kaola-workflow/archive/issue-244/qa/isolated-candidate-bytes.md
- kaola-workflow/archive/issue-244/qa/superseded-live-qa-plan.md
- kaola-workflow/archive/issue-244/repair-round-record.md
- kaola-workflow/archive/issue-244/workflow-state.md
