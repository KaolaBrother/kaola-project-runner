# Issue #87 freeze (post non-ACCEPT of abedeb6)

Candidate: `e591db6c1b26416a7cf232baec3e2c3ab38e6abf`
Branch: `workflow/issue-87`
Worktree: `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-87`
Parent: `abedeb6fda9090510978099361859a0b8bcba2b8`
Branch base: `18db64bbb96650621201e19be431def0e3b97559`
origin/main at freeze: `db7939e6fc9ce0d3d2c090e60b44a701660d77dd` (issue-86 sink; this candidate was not rebased onto it)

Previous freeze `abedeb6` was not ACCEPT (rotation rewind). This tip seeds restored current generation at least the confirmed generation.

## Rotation P1

Rotated EventLog can keep `worker_event_overflow_confirmed` generation=2 while older `worker_event_overflow` records are gone. Restore then set `overflow_generation=0`, `confirmed=2`. The next overflow incremented 0→1; `1>2` was false, so no full-check.

Fix: after scanning the log, `overflow_generation = max(overflow_generation, overflow_confirmed)`. No second state machine.

Deterministic test: log contains only confirmed gen2; restore; fill 32; new overflow must be generation 3 and deliver.

Baseline red on `abedeb6`: restore generation=0 (`evidence/baseline-red/issue-87-rotation-seed.log`).

## Holder line delta vs 18db64b

`scripts/kaola-acp-holder.py`: **+164 / −31**

## Validation on `e591db6`

- Heartbeat contract **15/15, 302 checks**
- `render --check` PASS (`evidence/validate-rotation-seed/render-check.log`)
- `validate.sh` exit 0 (`evidence/validate-rotation-seed/validate.sh.log`)
- `git diff --check` clean

## Not done

No finalize, sink, close, or push. Waiting for outer ACCEPT of `e591db6c1b26416a7cf232baec3e2c3ab38e6abf`.
