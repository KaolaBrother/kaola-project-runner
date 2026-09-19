# Full `./scripts/validate.sh` for the r5 candidate — where the exit status comes from

## My own runs: no exit receipt, and they do not count

I attempted the full suite twice in this worktree. Both were killed by session
teardown, not by a test failure, and neither produced an exit status:

- attempt 1 — no captured exit at all;
- attempt 2 — `25-validate-r5-INCOMPLETE-terminated.log`, 801 bytes, ends at
  `Terminated: 15` inside `tests/contract/test-installer-runtimes.sh`. The
  explicit exit-receipt footer I wrapped the run in was never reached, which is
  exactly why it is absent from that file.

A truncated log with no exit line is not evidence that the suite passed, and it
is not presented as any. The file is kept under a name that says so.

## The authoritative result: the outer verification's run

The outer verification ran `./scripts/validate.sh` in this same worktree and
reported **exit 0**, including the 16/16 Issue #92 contract suite and the
renderer check. I was asked not to rerun it, so that is the result of record for
this candidate, and it is theirs — not a run I performed.

## What I did run and can vouch for directly

- `python3 tests/contract/test-issue-92-permission-wake-recovery.py` — **16/16**,
  `15-issue-92-contract-r5.log`.
- `./scripts/render-skills.py --check` — PASS, budgets OK.
- Failure-first custody on the rejected `f5bb239`:
  `06-f5bb239-rerereview-regression.log`.
- The outer re-review's own race, reproduced then corrected:
  `07-post-write-race-probe.{py,log}`.

Earlier full-suite runs in this run's history, each with a captured exit 0, are
`20`/`21`/`22`/`23`/`24-validate-*.log` and the merge simulation `30-*.log`; they
cover the candidate up to `f5bb239`, not the r5 changes on top of it.
