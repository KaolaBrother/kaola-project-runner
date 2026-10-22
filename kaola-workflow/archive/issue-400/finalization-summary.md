# Finalization Summary — Issue #400

## Delivered

Fixed #400 on `workflow/issue-400`: a cwd placeholder directory that is already
gone no longer re-emits `tool_cwd_placeholder_left` on every cleanup and no
longer pins its claim forever. The reported vrpai path
(`.kw/worktrees/i1888-oldtip/sdk/typescript`) now follows the
`_cwd_resume_reconcile` startup semantics on cleanup: `_cwd_placeholder_drop`
plus `_cwd_forget_placeholder_path`, one record write, no event and no duty.
The rmdir race rechecks `os.path.isdir` in the exception and takes the same
silent path.

A placeholder that is genuinely still non-empty keeps its claim and records
`cwd-placeholder-not-empty` once per `(code, path)`; `_cwd_error_set` now writes
the record only when that duty is new or changed, and cleanup appends the event
only on a new duty, so repeated cleanups are no-ops. Emptying it lets the next
cleanup remove it with `tool_cwd_placeholder_removed`, release the claim and
clear the duty; a later recurrence reports once again.

The run adds `tests/contract/test-issue-400-placeholder-lifecycle.py` (4 cases:
missing path, rmdir race, repeated non-empty cleanup then empty removal and
recurrence, and a previously reported placeholder that disappears) and its row
in both `scripts/validate.sh` inventories beside `test-issue-378`.
`CHANGELOG.md` gains an `Unreleased` section with `Fixes #400` and
`Seats: restart required`; the holder is in the operator restart set and this
change does not install. The 11 generated worker Skill copies of the holder
were re-rendered from the source.

The branch also carries the standard post-release content-cycle unpin
`9d40a587` (the four Grok Bot pin paths; precedent `7b94ab81`), a release-cycle
state change rather than issue behavior. No #399 file, worktree or branch was
touched.

Candidate: `78661449` on `workflow/issue-400`, base `b57eca17` (v0.9.24 pin).
Host acceptance: independent review verdict PASS with 0 must-fix and 3
non-blocking nits (unused `exc` variable, one harmless duplicate record write
when a duty is first created, and the pre-existing stale-last pattern); no
change was required.

## Evidence

- Pre-fix counter-proof: the new suite run against
  `git show b57eca17:scripts/kaola-acp-holder.py` fails all 4 cases (5 repeated
  `tool_cwd_placeholder_left` events for missing/non-empty paths, a phantom
  event for the rmdir race, and a second event after out-of-band disappearance).
- Post-fix suite: 4/4 tests PASS in 0.036 s.
- Reproducer after fix: `[] None placeholder still tracked: []`.
- Final focused validation, run from the candidate tree at `78661449`, exit 0:
  `./scripts/validate.sh --suite test-issue-369-cwd-vanished.py --suite test-issue-369-worktree-guard.py --suite test-issue-369-holder-cwd-repair.py --suite test-issue-378-cwd-notice-delivery.py --suite test-issue-393-cwd-carrier.py --suite test-issue-400-placeholder-lifecycle.py`
  - `SUBSET RUN (6 of 161 suites)`, PASS, wall 221.016 s, `residual_pids: []`.
  - `test-issue-369-cwd-vanished.py` 4/4; `test-issue-369-worktree-guard.py`
    8/8; `test-issue-369-holder-cwd-repair.py` 23/23;
    `test-issue-378-cwd-notice-delivery.py` 5/5;
    `test-issue-393-cwd-carrier.py` 6/6;
    `test-issue-400-placeholder-lifecycle.py` 4/4.
  - `render-skills.py --check` and every Skill validation PASS.
  - Log: `/tmp/kpr400-validate.log`.
- Validation record:
  `kaola-workflow/issue-400/.cache/final-validation.md`, validated candidate
  hash `42ebe7e9284b0b8a268914c8b75aca57ff407f171f2cfc6f30216fe61dcdc6f0`.

## Known failures or unverified scope

- The focused run is a 6-suite subset, not whole-inventory coverage.
- No live external-platform UAT was run: the change is holder-local cwd-state
  logic on an already-covered transport path, and the adjacent #369/#378/#393
  real-holder suites passed.
- Running holders keep the old cleanup loop until they restart; the
  `Unreleased` section states `Seats: restart required`. This change does not
  install.
- The content-cycle unpin moves the checkout to the content stage; the next
  release will re-pin it in the standard R/P pair.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- templates/grok-bot/accepted-revision.json
- tests/contract/test-issue-400-placeholder-lifecycle.py

## Documentation Docking

DOCKED — `CHANGELOG.md` `Unreleased` records the #400 behavior, the new
contract suite and the restart boundary. No `docs/api.md`, template or budget
change was needed: the cleanup state machine is internal and the existing
#369/#373/#378 documentation already describes the surrounding cwd contract.

## Follow-Up Items

- No new follow-up issue was filed by this run. The 3 non-blocking review nits
  do not require a change and are not filed as issues.
- No release, tag, publish, install, or KPM-side operation is part of this
  finalization.

Final readiness: ready. Merge sink to `main`, verify publication, close #400,
archive under `kaola-workflow/archive/issue-400/`, and remove the run worktree
and branch.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-400/.cache/final-validation.md
- kaola-workflow/archive/issue-400/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-400/finalization-summary.md
- kaola-workflow/archive/issue-400/mission-ledger.jsonl
- kaola-workflow/archive/issue-400/workflow-state.md
