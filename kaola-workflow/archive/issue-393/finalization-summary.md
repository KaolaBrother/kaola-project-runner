# Finalization Summary — issue-393

## Delivered

Issue #393 is closed as not reproducible on the v0.9.23 tree. Seven current-code
reproduction variants (fresh worker with a legacy `--host-entry`, unknown role
with a legacy entry, resume-preserved, drain-restart, direct worker holder,
direct unknown-role holder, direct Host control) deliver only the compact
`kaola-worker-notify/1` notice to a non-Host holder; the only reproducing case
is the pre-#388 holder bytes from `f46e1d4e^`, which send the full
`kaola-host-notify/1` carrier with the heartbeat body and one-pass instruction.
The vrpai report matches a worker holder started before the #388 holder change
and not restarted; the v0.9.23 release notes already require that restart, and
`status.stale` reports the changed holder file.

The run adds `tests/contract/test-issue-393-cwd-carrier.py` (6 tests) and its
`scripts/validate.sh` inventory row. The suite exercises real holder processes,
a real linked worktree and an out-of-band `git worktree remove`; it fails on
the pre-#388 bytes and passes on the current bytes. No product behavior code
changed. The branch also carries the standard post-release content-cycle unpin
`7b94ab81` (the four Grok Bot pin paths; precedent `f37a1b54`, `ea3297e7`), which
is a release-cycle state change, not an issue fix.

## Candidate

Branch `workflow/issue-393` at `9195bbc3` (`docs: correct the issue 393
evidence facts`), on top of `3fb17cd4`, `97e8cc7c`, `2f390cbe`, `e4d5567b`,
`33a6387b`, `d959ab2b` and the content-cycle unpin `7b94ab81`, all based on
`be8a1ad9` (v0.9.23). The tip is the accepted candidate; Host acceptance
confirmed the four documentation corrections at `9195bbc3`. No tag, release or
install was made by this run.

## Evidence

- `kaola-workflow/issue-393/reproduction.md` — the variant matrix, the
  pre-#388 historical control, the path audit and the non-reproduction
  conclusion.
- `kaola-workflow/issue-393/validation.md` — the focused suite and renderer
  results.
- `kaola-workflow/issue-393/doc-docking.md` — documentation impact.
- `tests/contract/test-issue-393-cwd-carrier.py` — the regression suite:
  `./scripts/validate.sh --suite test-issue-393-cwd-carrier.py`, 6 tests OK,
  subset receipt 1 of 146, `residual_pids: []`.
- Related `./scripts/validate.sh --suite test-issue-388-role-carrier.py`
  passed (10.848 s).
- `./scripts/render-skills.py --check` PASS at the content stage.
- Host acceptance in conversation: engineering core accepted; the four
  documentation facts were corrected at `9195bbc3` and re-accepted.

## Known failures or unverified scope

- The vrpai worker holder's `runner_build` was not available in the issue. The
  decisive check remains the worker record: `runner_build=db475e966dc8`,
  `role=worker`, empty entry and `status.stale=false` would make this
  non-reproduction incomplete and is the stated reopen condition.
- The focus run is a subset, not whole-inventory coverage.
- The condition is a live pre-#388 seat, not a current-code defect; recovery is
  the release-required seat restart.
- No product code changed; no tag, release or install.

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
- scripts/validate.sh
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-393-cwd-carrier.py

## Follow-Up Items

- None filed by this run. No new defect was discovered during finalization; no
  duplicate probe issue is needed for the stale-seat condition.

Readiness: accepted candidate, focused suite and renderer green, ready to merge
and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-393/.cache/final-validation.md
- kaola-workflow/archive/issue-393/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-393/doc-docking.md
- kaola-workflow/archive/issue-393/finalization-summary.md
- kaola-workflow/archive/issue-393/mission-ledger.jsonl
- kaola-workflow/archive/issue-393/reproduction.md
- kaola-workflow/archive/issue-393/validation.md
- kaola-workflow/archive/issue-393/workflow-state.md
