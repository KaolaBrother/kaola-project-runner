# Issue #87 — ZCode heartbeat 满队列及过大正文仍可靠唤醒

Run: issue-87 · branch `workflow/issue-87` · worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-87`
Baseline: main `f39d940`. Singleton claim `--target-issue 87`. Do not touch
bundle-75 / issue-81 / bundle-85 / issue-86, the ZCode adapter, or Delegator.
No new queue, scheduler, timed heartbeat, or quota system. Outer ACCEPT is
required before finalize / sink / close.

## 1. Distinguishing contract tests, proven red on baseline
- item: Extend `tests/contract/test-zcode-heartbeat-contract.py` so a busy Host
  with 32 detailed events plus a 33rd pending-approval or completion event
  fails today's silent `worker-event-queue-full` drop; so an unconfirmed
  overflow/full-check signal that survives exact stop and `start --resume` is
  required; and so an oversized `.kaola/heartbeat-prompt.json` cannot enter the
  prompt as a truncated-looking body while the worker event still wakes. Run
  the suite on this worktree's unmodified holder and record the red.
- status: done
- dispatched: self; output lands in
  `.kw/worktrees/issue-87/tests/contract/test-zcode-heartbeat-contract.py`
  and baseline-red evidence under `kaola-workflow/issue-87/evidence/baseline-red/`
- result: Three new tests in `test-zcode-heartbeat-contract.py`. Unmodified
  holder on `f39d940` failed all three (`evidence/baseline-red/issue-87-new-tests.log`):
  queue-full receipt has no full-check; overflow is not in the event log; no
  `HEARTBEAT_PROMPT_MAX_BYTES`.

## 2. Minimal holder fix on the existing event carrier
- item: In `scripts/kaola-acp-holder.py` only, keep the 32 detailed-event cap;
  on overflow record a recoverable full-check signal in the existing event log
  and include it in the next heartbeat so the Host checks authorized workers'
  real status and pending approvals (remind only, never auto-approve). Bound
  the heartbeat-prompt file read; oversized files are a named defect plus
  recovery guidance, still delivered, never a truncated body passed off as
  complete. One read, latest usable body. Restore unconfirmed overflow on
  resume. Then prove the new tests green.
- status: done
- dispatched: self; output lands in
  `.kw/worktrees/issue-87/scripts/kaola-acp-holder.py` and green
  `tests/contract/test-zcode-heartbeat-contract.py` run log under
  `kaola-workflow/issue-87/evidence/`
- result: Holder keeps cap 32, records `worker_event_overflow` +
  `overflow_full_check` on the queue-full receipt, includes
  `kaola-host-notify/overflow-full-check` in the next prompt, confirms it
  separately, restores unconfirmed overflow on resume. Heartbeat file read
  is one `open` of at most 65536+1 bytes. Suite 12/12, 305 checks.

## 3. Document the real guarantee
- item: Correct `docs/zcode-host.md` so it no longer claims no-loss / unbounded
  full-body injection. State the 32-cap, overflow full-check, remind-only
  approvals, resume of unconfirmed overflow, and bounded prompt-file read as
  they actually behave. No new mechanism description beyond that.
- status: done
- dispatched: self; output lands in
  `.kw/worktrees/issue-87/docs/zcode-host.md` and a CHANGELOG Unreleased bullet
- result: `docs/zcode-host.md` no longer says no-event-loss. It states the
  32-cap, overflow/full-check, remind-only approvals, resume of unconfirmed
  overflow, and 65536-byte prompt-file bound. CHANGELOG Unreleased names the
  same guarantees.

## 4. Validate and freeze for outer review
- item: `./scripts/render-skills.py --write` for holder copies, then
  `--check`, `./scripts/validate.sh`, and `git diff --check` on the issue-87
  worktree. Commit the candidate, record the freeze SHA and original command
  evidence under `kaola-workflow/issue-87/evidence/`. Stop. Do not finalize,
  sink, close, or push.
- status: done
- dispatched: self; evidence lands under
  `kaola-workflow/issue-87/evidence/validate/` and a freeze SHA in
  `kaola-workflow/issue-87/evidence/candidate-sha.txt`
- result: Candidate `4a5eb22d891e629d1cb2f900f00bb16827e2cdc1` on
  `workflow/issue-87`. `render --check` PASS; `validate.sh` exit 0
  (heartbeat 12/12, 305 checks); `git diff --check` clean. Evidence in
  `kaola-workflow/issue-87/evidence/`. Stopped before finalize/sink/close.

## 5. Minimal core-invariant tests after outer non-ACCEPT
- item: Replace the #87 tests with a small set that only covers: 33rd event
  wakes the next beat's full check; overflow during that notification is not
  confirmed away; exact stop/resume redelivers unconfirmed full-check; the
  carrier never auto-approves; an oversized prompt file is not injected.
  No dropped-summary or overflow_id assertions. Prove they fail on silent
  drop / lost generation if the bloated restore is still wrong, then keep
  them as the acceptance set.
- status: done
- dispatched: self; output lands in
  `.kw/worktrees/issue-87/tests/contract/test-zcode-heartbeat-contract.py`
- result: Three core tests (33rd+later-generation, stop/resume, oversized
  not injected). Suite 12/12, 285 checks on the slim holder.

## 6. Converge the holder to one full-check generation
- item: In `scripts/kaola-acp-holder.py`, delete dropped lists, follow_on,
  random overflow ids, and the restore ID dictionary. Keep the 32 detailed
  queue and existing event log. One monotonic generation plus confirmed
  generation: each overflow logs a fact; a notification confirms only the
  generation snapped at delivery; later overflows need the next wake.
  Restart rebuilds pending iff last overflow generation exceeds last
  confirmed generation. Keep the 64KiB bounded single read.
- status: done
- dispatched: self; output lands in
  `.kw/worktrees/issue-87/scripts/kaola-acp-holder.py`
- result: `overflow_generation` / `overflow_confirmed_generation` /
  inflight snapshot only. No dropped list, follow_on, overflow_id. Restore
  is last overflow gen vs last confirmed gen.

## 7. Slim docs to the same invariants
- item: `docs/zcode-host.md` and the CHANGELOG bullet state only the 32-cap,
  generation full-check, remind-only, resume, and bounded read. No dropped
  history or second-queue wording.
- status: done
- dispatched: self; `docs/zcode-host.md` and CHANGELOG Unreleased
- result: Docs name generation snap-at-delivery, later overflow still
  wakes, 64KiB bound, remind-only.

## 8. Rebase onto 18db64b, validate, freeze
- item: Safe rebase of the issue-87 worktree onto origin/main `18db64b`.
  `render --write/--check`, `validate.sh`, `git diff --check`. One freeze
  SHA plus the actual `scripts/kaola-acp-holder.py` line delta vs 18db64b.
  No finalize.
- status: done
- dispatched: self; evidence under `kaola-workflow/issue-87/evidence/`
- result: Freeze `1791f6dc3afc96f745d4a33bc19da2ff8ea0c9bc` on `18db64b`.
  Holder `+154/−31` vs main. `render --check` PASS; `validate.sh` exit 0
  (heartbeat 12/12, 285 checks). No finalize.

## 9. Generation order-safety and idle-full delivery
- item: Deterministic regression: out-of-order event log (delivered gen1,
  confirmed gen1, overflow gen2, overflow gen1) must restore pending
  full-check at generation 2. Overflow increment and log append share one
  lock; restore takes max generation. When the detailed queue is full and
  the Host is idle, the overflow receipt itself must trigger full-check
  delivery. Keep the single generation scheme.
- status: done
- dispatched: self; tests in
  `tests/contract/test-zcode-heartbeat-contract.py`, holder in
  `scripts/kaola-acp-holder.py`
- result: Two new tests failed on `1791f6d` (restore gen=1; idle overflow
  not delivered) then passed. Append is under `worker_events_lock`; restore
  uses max; idle overflow calls `_deliver_worker_events`.

## 10. Validate and freeze
- item: `render --write/--check`, focused heartbeat suite, full
  `validate.sh`. New freeze SHA. No finalize.
- status: done
- dispatched: self; evidence under `kaola-workflow/issue-87/evidence/`
- result: Freeze `abedeb6fda9090510978099361859a0b8bcba2b8`. Heartbeat
  14/14, 295 checks; `validate.sh` exit 0. No finalize.

## 11. Seed restored generation at least confirmed (rotation)
- item: When rotated logs keep `worker_event_overflow_confirmed` generation=2
  but drop older overflow facts, restore must seed current generation to at
  least 2 so a new overflow becomes 3 and still delivers a full-check. One
  deterministic MemoryEventLog test; no second state machine. Then
  render/validate and freeze. No finalize.
- status: done
- dispatched: self; test in
  `tests/contract/test-zcode-heartbeat-contract.py`, seed in
  `scripts/kaola-acp-holder.py` `_restore_worker_events`
- result: Baseline red on `abedeb6` (restore generation=0). Seed
  `max(overflow, confirmed)` then new overflow is gen 3 and delivers.
  Freeze `e591db6c1b26416a7cf232baec3e2c3ab38e6abf`. Heartbeat 15/15,
  302 checks; `validate.sh` exit 0. No finalize.
