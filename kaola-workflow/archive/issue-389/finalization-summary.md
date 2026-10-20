# Finalization Summary — issue-389

## Delivered

`worktree-guard` and the runner-owned worktree removal now warn and continue on
recoverable cwd findings instead of blocking. The receipt gains `warnings[]`
(`{code, path, detail, recovery}`); `result` keeps `clear | occupied |
unverifiable | refused`, while the exit code carries the action: `0` proceeds,
`3` is the one cwd hard block (a live process cwd inside the worktree AND
uncommitted changes), and `2` is `refused`. A live cwd alone or a recorded
`tool_cwd` with no process is `occupied-cwd-recoverable`; an unreadable probe is
`cwd-unverifiable`; both warnings carry the repair/recheck command.

The same rule governs `worktree-remove` and the W1 backstop sweep: the two cwd
keep reasons are gone, a failed own-cwd relocation warns and continues, the
removal runs, and the post-check recreates an empty placeholder when a live cwd
was inside. A merely unverifiable post-check adds no placeholder and never
undoes the removal. The sweep receipt carries the same `warnings[]`. The
`cwd-occupied` recovery route names the live-cwd-plus-uncommitted condition.

`docs/api.md` freezes the new receipt/exit contract. The Host guidance template
and its generated Skills state the recoverable-live-cwd behavior.
`tests/contract/test-issue-374-worktree-guard-contract.py` and
`tests/contract/test-issue-369-worktree-guard.py` cover the hard block, the
warning-only cases and the recovery text.

Audit result: the #369/#373 holder cwd repair and the #378 notice fix introduce
no blocking behavior; their only effects are notices and recorded duties. The
one retained cwd hard block is a live process cwd plus uncommitted changes; the
sweep's existing `uncommitted-changes` keep is the corresponding pre-existing
data-loss guard.

## Candidate

Branch `workflow/issue-389` at `ce64c454`, rebased from the accepted
`15189308` onto current main `549a1f27` (contains merged #378). The rebase kept
the `CHANGELOG.md` Unreleased union (#373/#375/#377/#378/#389) and the #378
validate inventory line. `./scripts/render-skills.py --write` produced no
further changes on the rebased tree; `--check` is PASS.

Changed surface: `CHANGELOG.md`, `docs/api.md`, `scripts/kaola-cwd-guard.py`,
`scripts/kaola-dispatch.py`, `scripts/kaola-recovery-routes.py`,
`templates/orchestrator/references/workflow-worktree.md`, the two contract
suites, and the render-generated worker Skills and build metadata.

## Evidence

- Host acceptance of #389 for candidate `15189308` (owner message): warnings[]
  contract, the one hard block, warning-only occupancy, the 7-case #374 suite,
  the 8-case #369 guard suite, the complete audit table, the 8-suite subset and
  render PASS.
- Rebased affected suites, exit 0, log `/tmp/kpr-389-rebased-suites.log`:
  `test-issue-374-worktree-guard-contract.py`,
  `test-issue-369-worktree-guard.py`,
  `test-issue-369-cwd-vanished.py`,
  `test-issue-369-holder-cwd-repair.py`,
  `test-issue-309-recovery-routes.py`,
  `test-issue-271-dispatch-help.py`,
  `test-issue-348-backstop-sweep.py`,
  `test-issue-275-core-contracts.py`,
  `test-issue-378-cwd-notice-delivery.py`,
  `test-issue-264-validate-lane-integrity.py`.
- Prior accepted candidate evidence before the rebase:
  `/tmp/kpr-389-suites-final2.log` (8 affected suites, exit 0).
- `./scripts/render-skills.py --check`: PASS (budgets OK, content stage).
  `kaola-grok-bot-verify`: PASS in the validate run.
- Final validation record: `.cache/final-validation.md` binds the rebased
  candidate tree to the exact affected-suite command, verdict `pass`.

## Known failures or unverified scope

- A full `./scripts/validate.sh` inventory was not run; the affected subset
  above is the binding evidence for this change.
- The Kaola-Workflow consumer side (K2: treat the guard's warning-only answers
  as proceed) is handled in parallel in the Kaola-Workflow repository and is
  not part of this candidate. The KPR contract states exit 0 = proceed.
- `#388` is still active in its own worktree; this run does not touch it.
- No release, tag, install, or cloud action was performed. No other Host was
  restarted.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-cwd-guard.py
- scripts/kaola-dispatch.py
- scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/workflow-worktree.md
- skills/kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-cwd-guard.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/workflow-worktree.md
- tests/contract/test-issue-369-worktree-guard.py
- tests/contract/test-issue-374-worktree-guard-contract.py

## Follow-Up Items

- Kaola-Workflow K2 consumes the new `warnings[]`/exit-code contract; KPR did
  not change the KW repository.
- The `#378` notice fix is merged on main; this run audited its in-flight diff
  and found no blocking behavior.

## Readiness

Ready for the merge sink. The accepted implementation, the rebased contract
suites and render check are green; no unresolved blocking finding remains for
#389.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-389/.cache/final-validation.md
- kaola-workflow/archive/issue-389/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-389/finalization-summary.md
- kaola-workflow/archive/issue-389/mission-ledger.jsonl
- kaola-workflow/archive/issue-389/workflow-state.md
