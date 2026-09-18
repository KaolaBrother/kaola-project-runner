# Goal: ZCode Host worker-event admission/confirmation race + confirmed-event retry dedup (Issue #90)

Scope: `scripts/kaola-acp-holder.py` event-confirmation path only, focused contract tests,
minimal docs/evidence. ACP only. Worktree
`/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-90`,
branch `workflow/issue-90`, base `1f01b3c`.
Do NOT finalize/archive/sink/push/close: stop at a frozen candidate SHA for owner ACCEPT.
Never touch the concurrent #75 (`kaola-workflow/bundle-75/`) or #81 (`kaola-workflow/issue-81/`)
candidates, worktrees, or branches.

Measured defect (base `1f01b3c`, `scripts/kaola-acp-holder.py`):
- `_deliver_worker_events()` calls `op_prompt(wait=False)` and only AFTERWARD assigns
  `item["prompt_fingerprint"]` and `overflow_inflight_generation`/`_fingerprint`.
  `op_prompt` starts `_await_prompt` before returning, so an immediate Host response runs
  `on_prompt_response -> _worker_event_turn_end(fingerprint, "turn_completed")` first; it finds
  no match, sets `was_notification = False`, and re-enters `_deliver_worker_events()`.
  Result: two Host prompts for one event, first turn never confirmed. Same for overflow.
- `op_worker_event()` dedups only against `pending_worker_events`; a confirmed item has been
  removed, so a retry of the same deterministic `event_id` re-stages and re-prompts.

## 1. Deterministic RED on base 1f01b3c
- item: Write the focused in-process contract test (real `Holder` + stub agent, the
  `tests/contract/test-issue-65-steer-race.py` wrapper pattern; no sleeps, no shipped test hook)
  covering: fast-response detailed event, fast-response overflow full-check generation, confirmed
  `event_id` retry, plus the must-not-regress cases (genuinely unconfirmed resume still
  redelivers; busy host still stages; failed prompt still retriable; distinct new event still
  delivered). Prove it RED on unmodified `scripts/kaola-acp-holder.py` and capture raw output.
- status: done
- dispatched: self (I hold the acceptance meaning; the interleaving was measured here)
- result: `tests/contract/test-issue-90-event-confirmation-race.py` (9 tests, in-process real
  `Holder` + stub agent, `arm_instant_host()` answers the first admitted prompt before its caller
  gets the receipt). RED on unmodified `scripts/kaola-acp-holder.py` at base `1f01b3c`:
  **8 of 9 FAIL**, only `test_the_carrier_op_stays_a_zcode_host_capability` passes.
  Raw: `kaola-workflow/issue-90/red-issue-90.log`.

## 2. Minimal atomic fix
- item: In `scripts/kaola-acp-holder.py` only, make admission and association atomic using the
  existing `worker_events_lock` and existing event/Holder facts: install the staged
  `prompt_fingerprint` and the overflow in-flight generation BEFORE `op_prompt`, rolling back
  exactly our own registration when admission fails; add confirmed-`event_id` retry dedup derived
  from the existing `worker_event_confirmed` log facts. No scheduler, no second ledger, no broad
  gate, no permission auto-approval, no history rewrite. Then GREEN with raw output.
- status: done
- dispatched: self
- result: `scripts/kaola-acp-holder.py` only. (a) new module helper `prompt_fingerprint(text)` is
  the single prompt identity, used by both `op_prompt` and the carrier; (b)
  `_deliver_worker_events()` claims that fingerprint for the staged events and the overflow
  in-flight generation UNDER `worker_events_lock` BEFORE `op_prompt`, and
  `_release_worker_event_claim()` drops exactly its own claim when admission fails; (c) new
  bounded `confirmed_worker_events` (cap `HEARTBEAT_CONFIRMED_MEMORY = 8 * HEARTBEAT_EVENT_CAP`)
  fed by `_worker_event_turn_end` and rebuilt in `_restore_worker_events` from the existing
  `worker_event_confirmed` log records, so `op_worker_event` answers a confirmed retry
  `{"duplicate": true, "confirmed": true}`. GREEN: 9/9 OK.

## 3. Affected inventory and full verification
- item: Focused ZCode heartbeat/host/ACP contract tests plus the new test,
  `./scripts/render-skills.py --check`, full `./scripts/validate.sh`, `git diff --check`.
  Record raw receipts under `kaola-workflow/issue-90/`.
- status: done
- dispatched: self
- result: Focused PASS: `test-zcode-heartbeat-contract.py` 15/15 (302 checks),
  `test-issue-65-steer-race.py`, `test-issue-65-host-contract.py`, `test-zcode-host-contract.py`,
  `test-zcode-acp-contract.py`, `test-issue-70-binding-fact.py`, `test-issue-76-permission-wake.py`,
  `test-issue-68-heartbeat-snapshot.py`. One pre-existing fixture needed the new carrier field:
  `bare_holder()` bypasses `__init__` and enumerates carrier state by hand, so it now also sets
  `confirmed_worker_events = {}` — a fixture update, no assertion weakened.
  `./scripts/render-skills.py --check` PASS (after the required `--write`: the generated Skills
  mirror `scripts/kaola-acp-holder.py`; all nine mirrors verified byte-identical).
  Full `./scripts/validate.sh` **exit 0**, no FAILED/SKIPPED. `git diff --check` clean.
  New test registered in `scripts/validate.sh` (`python_suites_all` + lane b).
  Raw: `kaola-workflow/issue-90/validate-issue-90.log`, `green-issue-90.log`.

## 4. Minimal docs and frozen candidate
- item: Only the documentation the changed behavior actually makes wrong (holder carrier comments
  / `docs/` if it states the ordering). Commit on `workflow/issue-90`, freeze the exact candidate
  SHA, capture `git diff` and `git show --stat`.
- status: done
- dispatched: self
- result: `docs/zcode-host.md` "Confirmation and resume" now states the pre-admission claim and the
  confirmed-retry duplicate answer; `CHANGELOG.md` Unreleased entry added. Candidate frozen at
  **`19c04cc96a68af9b20e4973163e2fad91f183235`** on `workflow/issue-90` (parent `1f01b3c`),
  15 files, +1077/-80. Not pushed, not closed.
  Raw: `kaola-workflow/issue-90/candidate-19c04cc.diff`, `candidate-19c04cc.stat`.

## 5. Independent review of the frozen candidate
- item: Clean-context review of the exact frozen SHA for correctness, deadlock/lock-ordering, test
  custody, and scope creep. Findings return to me for the verdict; then report to the owner for
  outer independent acceptance. No finalize/archive/sink/push/close.
- status: done
- dispatched: two `code-reviewer` subagents on `19c04cc`, different cuts — (a) correctness /
  concurrency / lock ordering; (b) test custody, evidence honesty, scope, docs, cross-worker safety.
- result: **(b) found no defect** and independently reproduced the RED/GREEN claim; it also proved by
  mutation that four properties were unpinned (resume rebuild of the confirmed memory, the
  `confirmed` reply flag, the memory bound, the release helper's ownership rule) — all now pinned.
  **(a) found a real regression, which I reproduced myself**: the pre-admission claim keyed on the
  prompt fingerprint, which identifies the TEXT, not the delivery. Two concurrent deliveries build
  the same text, so the one refused `prompt-in-progress` released the claim of the turn that had
  just won admission — 2 prompts and no confirmation, the exact Issue #90 symptom, on an interleave
  the base handled correctly. Verdict: accepted, candidate `19c04cc` rejected.

## 6. Repair the concurrency regression and re-freeze
- item: Replace the pre-claim/rollback design with a single `worker_events_lock` hold spanning
  snapshot, admission, and marking; delete `_release_worker_event_claim` and the helper that existed
  only to serve the pre-claim; add the concurrency guard the suite was missing; correct the docs.
- status: done
- dispatched: self
- result: `_deliver_worker_events` now holds the existing lock across snapshot -> `_heartbeat_payload`
  -> `op_prompt` -> marking -> the `worker_event_delivered` append, and marks only after a successful
  admission, so there is no rollback to get wrong and a second delivery finds the events already
  marked. `worker_event_delivered` inside the hold also restores the documented
  `worker_event -> delivered -> confirmed` order on an instant answer. `_release_worker_event_claim`
  and `prompt_fingerprint()` deleted (net holder change vs base: +108/-26 lines).
  The instant-answer test harness now delivers the response on its own thread, as production does.
  New guard `test_two_deliveries_cannot_be_inside_the_admission_window_together` is deterministic in
  BOTH directions: **12/12 FAIL against `19c04cc`, 12/12 PASS here** (an earlier no-rendezvous
  version caught it only 1/15 and was discarded).
  Suite 13 tests: base `1f01b3c` 10 RED, `19c04cc` 2 RED, candidate **13/13 OK**.
  Focused suites PASS (`test-zcode-heartbeat-contract.py` 15/15, 302 checks). render `--check` PASS,
  all nine mirrors byte-identical. Full `./scripts/validate.sh` **exit 0**. `git diff --check` clean.
  **Frozen candidate: `71173bc52738ece82b8c2fb80a3328edf3a3aa04`.**
  Raw: `candidate-71173bc.diff`, `candidate-71173bc.stat`, `red-green-issue-90.log`,
  `validate-issue-90.log`.

## 7. Re-review of the repaired candidate
- item: Re-review `71173bc`, focused on the new exposure of holding `worker_events_lock` across
  `op_prompt`.
- status: done
- dispatched: resumed the `i90-correctness` reviewer on `71173bc`.
- result: SUPERSEDED. The outer owner's own review landed first and decided acceptance, so that
  review turn was canceled; its earlier committed work is preserved in history. Outer review did
  confirm the P1 fast-response / concurrent-admission fix and the lock order.

## 8. Outer verdict on 71173bc: NOT ACCEPTED - remove the 256-id dedup exception
- item: The Issue body requires a confirmed `event_id` retry to be ignored, with no "unless more
  than N confirmations since" exception. At 257 confirmed ids retained in the event log,
  `_restore_worker_events` evicts the oldest from the in-memory index and a retry of that
  still-logged id re-stages and re-prompts the Host. Docs also narrowed the promise to "recent 256",
  conflicting with the Issue body and the dispatch template's unconditional duplicate contract.
  Correction must keep the bounded hot cache but resolve a miss against the retained
  `worker_event_confirmed` log truth - no new durable ledger, scheduler, unbounded memory, or broad
  gate - and preserve at-least-once plus rotation semantics.
- status: done
- dispatched: self
- result: Reproduced failure-first on `71173bc` before changing code: **1 of 17 FAIL**
  (`test_a_confirmed_retry_is_ignored_past_the_hot_cache_bound`, via the resume path the review
  named). Fix: `op_worker_event` now asks `_was_worker_event_confirmed()`, which answers from the
  cache and, once `confirmed_worker_events_evicted` is set, falls back to the
  `worker_event_confirmed` records the cache was built from; a hit is cached, and a holder that
  never exceeds the bound never scans. The promise is now exactly as wide as the RETAINED log - the
  same horizon that already bounds resume redelivery - and a confirmation rotation has dropped makes
  the event deliverable again, keeping at-least-once. Docs and CHANGELOG restate that bound.
  Four new tests: confirmed retry past the bound ignored; a genuinely new event past the bound still
  delivered; an unconfirmed event past the bound still resumes; a confirmation the log no longer
  holds is deliverable again. `bare_holder` gained the new field (fixture init, no assertion
  weakened).
  Suite 17 tests: base `1f01b3c` RED (9 failures, 5 errors), `71173bc` 1 RED, candidate **17/17 OK**.
  Focused suites PASS (`test-zcode-heartbeat-contract.py` 15/15, 302 checks). render `--check` PASS,
  nine mirrors byte-identical. Full `./scripts/validate.sh` **exit 0**. `git diff --check` clean.
  **Frozen candidate: `31fb66589c61c69fe9bfb09f0549171c9b49a50c`.** Awaiting outer ACCEPT; nothing
  pushed, closed, archived, or sunk.
  Raw: `candidate-31fb665.diff`, `candidate-31fb665.stat`, `red-green-issue-90.log`,
  `validate-issue-90.log`.

## 9. Outer verdict on 31fb665: NOT ACCEPTED - two retained-log semantics gaps
- item: (1) `_was_worker_event_confirmed` returned true from the hot cache without checking whether
  rotation had dropped that confirmation; `_rotate` advances `EventLog.oldest`, and the existing
  rotation test never exercised an id actually in the cache. Needs a deterministic failure-first
  test that confirms an id, rotates past its confirmation in the SAME running Holder, retries it and
  sees delivery, while a retained confirmed id stays a duplicate; minimal cache invalidation on
  oldest-cursor advance (or per-id cursor if simpler), falling back to the retained log, no fixed-id
  horizon. (2) `_worker_event_turn_end` removed pending and remembered confirmed under
  `worker_events_lock` but appended `worker_event_confirmed` only after releasing it, so a retry
  could be answered confirmed before the record existed and a crash in the gap lost the only durable
  truth. Append before exposing/removing, under the existing lock, keeping lock ordering and event
  order. Do not weaken the fast-response/concurrent tests.
- status: done
- dispatched: self
- result: Reproduced failure-first on `31fb665` before changing code: **2 of 19 FAIL**.
  (1) Each cache entry now carries the event-log cursor its confirmation was recorded at; a hit is
  evidence only while that cursor is still >= `oldest_cursor()`, otherwise the entry is dropped, the
  cache is marked partial, and the lookup falls back to the `worker_event_confirmed` records like
  any other miss. Per-id cursor was the simpler of the two options the review allowed. No fixed-id
  horizon remains.
  (2) The confirmation is appended inside the existing `worker_events_lock`, before the events leave
  the pending list and before the cache can answer from them;
  `worker_event_overflow_confirmed` moved under the same lock for the same reason. Recorded order
  unchanged; lock order is still `worker_events_lock` -> `EventLog.lock`, which
  `_deliver_worker_events` already used for `worker_event_delivered`.
  Discrimination is **monotone** on one suite of 19: `1f01b3c` 16 RED, `19c04cc` 5, `71173bc` 3,
  `31fb665` 2, candidate **19/19 OK** - and the fast-response and concurrent-admission guards still
  fail on `19c04cc`, so nothing earlier was weakened.
  Focused suites PASS (`test-zcode-heartbeat-contract.py` 15/15, 302 checks). render `--check` PASS,
  nine mirrors byte-identical. Full `./scripts/validate.sh` **exit 0**. `git diff --check` clean.
  **Frozen candidate: `c5155e5668d225eb5dbf209205679af4d9abea51`.** Stopped for outer review; not
  finalized, archived, sunk, pushed, or closed.
  Raw: `candidate-c5155e5.diff`, `candidate-c5155e5.stat`, `red-green-issue-90.log`,
  `validate-issue-90.log`.
