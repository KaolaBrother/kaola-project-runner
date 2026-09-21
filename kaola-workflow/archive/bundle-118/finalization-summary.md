# Finalization Summary — bundle-118 (Issue #118)

## Delivered
The authorized worker count is a hard cap on live worker processes (ACP holders included) until each
`stop` receipt; stop-before-start at the cap; the only legal idle seat is a delivery awaiting
acceptance, exact-stopped in the beat acceptance finishes; a new/different task gets a new session
(`--resume`/`--continue` only for the same assignment); each beat reports `live N / authorized M`
per platform and seats stopped. No quota system, ledger, or scheduler.

## Files Changed
16 files, +322/-74 (candidate c337c86, rebased onto origin/main 042f856 as 5ff59b2; only CHANGELOG
Unreleased conflicted — resolved keeping #118, #114, #117, #115, #116 entries).

## Test Coverage
- New `tests/contract/test-issue-118-seat-cap.py` (18 tests): OK on candidate; 30 subtest failures on base 34aaeae (discrimination).
- `tests/contract/test-issue-41-orchestrator.py` amended: fails on base output, OK on candidate.

## Validation
- `./scripts/render-skills.py --check` PASS on 5ff59b2; budgets OK (main Skill 17391/17408 B, heartbeat skeleton 8155/8192 B — unchanged from c337c86).
- `./scripts/validate.sh` on c337c86: exit 0, 0 FAILED (log archived as validate-118.log).
- Post-rebase tree differs from c337c86 by #114's `scripts/kaola-tmux.sh` (+ 10 generated copies) and `tests/contract/test-acp-contract.py`, so a full re-run was made: `./scripts/validate.sh` on 5ff59b2 exit 0, 0 FAILED, 8m03s (log archived as validate-118-rebased.log).
- Acceptance: Host self-verification PASS; Fable final review PASS (five semantics, placement table, all three acceptance criteria, discrimination verified on base, template-generated parity zero-diff).
- Live tmux smoke: not applicable — docs/contract-only change to the orchestrator Skill; no transport code changed.

## Issue walk (#118)
- Seat count = hard live-process cap: main Skill + skeleton + zcode-host-dispatch + issue-dispatch; test-issue-118.
- Stop-before-start: same surfaces; test-issue-118 + amended test-issue-41.
- Only idle = awaiting acceptance; exact-stop on acceptance: same surfaces; test-issue-118.
- New task = new session: same surfaces; test-issue-118.

## Changed Paths
scripts/render-skills.py, scripts/validate.sh, skills/kaola-project-runner/SKILL.md,
skills/kaola-project-runner/references/{heartbeat-skeleton,issue-dispatch,zcode-host-dispatch}.md,
templates/orchestrator/SKILL.md.tmpl, templates/orchestrator/references/{heartbeat-skeleton.txt,
issue-dispatch.md,zcode-host-dispatch.md.tmpl}, tests/contract/test-issue-118-seat-cap.py,
tests/contract/test-issue-41-orchestrator.py (finalize --check; source-scoped, omits docs:
README.md, docs/architecture.md, docs/zcode-host.md, CHANGELOG.md).

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
None. Main Skill budget headroom is 17 B and skeleton 37 B — later edits must replace, not append (recorded fact, not a defect).

## Status
READY

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-118/.cache/doc-docking.md
- kaola-workflow/archive/bundle-118/.cache/final-validation.md
- kaola-workflow/archive/bundle-118/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-118/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-118/finalization-summary.md
- kaola-workflow/archive/bundle-118/mission-list.md
- kaola-workflow/archive/bundle-118/workflow-state.md
