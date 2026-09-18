# Issue #87 — finalization summary

Run: `issue-87` · Issue: **#87** · Branch: `workflow/issue-87` · Sink: merge to `main`
Outer ACCEPT: `e591db6c1b26416a7cf232baec3e2c3ab38e6abf` (2026-09-19)
Rebased candidate: `06091ca176cc2a9e68d99933cf36098176801767` onto origin/main
`db7939e6fc9ce0d3d2c090e60b44a701660d77dd` (issue-86 sink). Product bytes are
the accepted holder/tests/docs plus CHANGELOG coexistence with #86.

## Delivered

ZCode Host heartbeat carrier still stages at most 32 detailed worker events.
A later event returns `worker-event-queue-full` and is not a 33rd detailed
line. The existing event log records one monotonic full-check generation so
the next heartbeat inspects authorized workers' real status and pending
approvals (remind only; never auto-approve). A notification confirms only
the generation snapped at delivery; overflow during that turn needs the next
wake. Idle Host with a full detailed queue delivers the full-check from the
overflow itself. Restore takes max overflow/confirmed generations and seeds
current generation at least the confirmed generation so rotated logs cannot
rewind the counter. `.kaola/heartbeat-prompt.json` is one 65536-byte read;
oversized files are a named defect, never a truncated-looking body, and
still wake.

No new queue, scheduler, timed heartbeat, quota system, ZCode adapter, or
Delegator change. `templates/grok-golden/` frozen.

## Files Changed

13 tracked paths (`git diff --name-only origin/main...HEAD` at `06091ca`):

`CHANGELOG.md`, `docs/zcode-host.md`, `scripts/kaola-acp-holder.py`,
nine generated `skills/*/scripts/kaola-acp-holder.py`,
`tests/contract/test-zcode-heartbeat-contract.py`.

Holder vs `db7939e`: +164 / −31.

## Test Coverage

`tests/contract/test-zcode-heartbeat-contract.py` — **15/15 tests, 302
checks** on `06091ca`, including: 33rd-event full-check on a busy Host
(later overflow still wakes, remind-only); exact stop/resume redelivery;
oversized prompt file not injected; restore max generation on reordered
log; idle-full overflow delivers now; restore seeds generation from
confirmed gen2 after rotation then new overflow is gen 3 and delivers.

Baseline red: silent queue-full (`f39d940`); restore gen=1 on reordered log
(`1791f6d`); idle overflow not delivered (`1791f6d`); restore gen=0 after
confirmed-only rotation (`abedeb6`).

## Validation

Recorded receipt: `verdict: pass`, `validated_candidate_hash`
`85ee1cded41385aa5f59435fd1d34e3e8b79fc934d3c40e0ffffd9bd90337827`.
Exact command (from candidate worktree `.kw/worktrees/issue-87` at `06091ca`):
`./scripts/validate.sh` exit 0 (`evidence/validate-rebase-db7939e/validate.sh.log`;
heartbeat 15/15 302 checks; `test-issue-86-delegator-quota.py` 46 checks).
`./scripts/render-skills.py --check` PASS. `git diff --check` clean.
`run-chains.js`: `refuse/chains_config_missing` (consumer repo).

Acceptance legs: automated contract + full `validate.sh`. Not executed:
live ZCode model session, Grok Bot UAT.

## Changed Paths

Finalize `--check` reported implementation `changed_paths` (holder copies +
heartbeat tests). Full product diff vs `origin/main` at `06091ca` also
includes `CHANGELOG.md` and `docs/zcode-host.md`:

`CHANGELOG.md`, `docs/zcode-host.md`, `scripts/kaola-acp-holder.py`,
`skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py`,
`skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py`,
`tests/contract/test-zcode-heartbeat-contract.py`.

## Documentation Docking

`kaola-workflow/issue-87/.cache/doc-docking.md` — **DOCKED**.
`docs/zcode-host.md` and `CHANGELOG.md` state the real guarantees. README
index already links `zcode-host.md`. No API/architecture/setup edits.

## Follow-Up Items

None filed. Co-active #75 / #81 / #88 were not touched. #81 remains in
review in its own worktree.

## Readiness

Ready to close #87, archive `kaola-workflow/issue-87`, and merge-sink
`workflow/issue-87` onto `main`. No release/tag.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-87/.cache/doc-docking.md
- kaola-workflow/archive/issue-87/.cache/final-validation.md
- kaola-workflow/archive/issue-87/.cache/mirror-digest.json
- kaola-workflow/archive/issue-87/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-87/evidence/candidate-sha.txt
- kaola-workflow/archive/issue-87/evidence/validate-1791f6d/validate.sh.exit
- kaola-workflow/archive/issue-87/evidence/validate-order-safety/validate.sh.exit
- kaola-workflow/archive/issue-87/evidence/validate-rebase-db7939e/validate.sh.exit
- kaola-workflow/archive/issue-87/evidence/validate-rotation-seed/validate.sh.exit
- kaola-workflow/archive/issue-87/evidence/validate/render-check.exit
- kaola-workflow/archive/issue-87/evidence/validate/validate.sh.exit
- kaola-workflow/archive/issue-87/evidence/verification.md
- kaola-workflow/archive/issue-87/finalization-summary.md
- kaola-workflow/archive/issue-87/mission-list.md
- kaola-workflow/archive/issue-87/workflow-state.md
