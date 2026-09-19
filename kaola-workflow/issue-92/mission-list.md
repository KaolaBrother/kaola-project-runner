# Issue #92 — ZCode Host: a permission_required wake must survive a temporarily absent Host

Run: worktree `/Volumes/WorkspaceA/ylminiserver/workspace/kaola-project-runner/.kw/worktrees/issue-92`,
branch `workflow/issue-92`, base `aa5fdad`. Scope is the lost `permission_required` wake only:
holder/Host existing event paths, the minimal control-plane prompt wording, focused tests and docs.
Ordinary `idle`/`terminated`, unbound workers and non-ZCode Hosts stay unchanged.

- item: Establish the failure-first reproduction as a contract test —
  bound worker + ZCode Host, Host force-stopped, `session/request_permission` raised while the
  Host socket is gone, then the SAME authorized Host restarts. Assert the recovered wake arrives
  exactly once, plus the repeated-delivery, resolved/worker-exited-stale, permit-then-idle and
  busy-Host cases. Must FAIL on `aa5fdad`.
  status: done
  dispatched: self
  result: `tests/contract/test-issue-92-permission-wake-recovery.py`.
    Baseline FAIL at aa5fdad: `evidence/00-baseline-failure.log` — 8 arming checks hold (host
    stopped, prompt admitted, turn_active true, activity_hint waiting, carrier receipt
    `host-unreachable`), then the retained-wake check times out.
    Baseline LOSS proof: `evidence/01-baseline-loss-probe.{py,log}` — 90 s after the SAME
    authorized Host restarts, `host_staged_worker_events: []`, `host_delivered: []`,
    `host_prompts: []`, `worker_carrier_sends_total: 1`, `worker_turn_active: true`.
- item: Implement the minimal existing recovery trigger in `scripts/kaola-acp-holder.py`: retain the
  undelivered `permission_required` carrier event (original `event_cursor` preserved so the Host's
  existing `event_id` dedup makes a repeat free) and re-attempt it from the holder's existing
  watchdog tick while the request is still live. No new thread, scheduler, registry or ledger; no
  auto-approval; locator + `request_id` only.
  status: done
  dispatched: self
  result: `scripts/kaola-acp-holder.py` (+131/-3). `_carrier_send` split out of
    `_notify_heartbeat_host_now`; `undelivered_wakes` + `_retain_undelivered_wake`,
    `_wake_stale_reason`, `_undelivered_wake_facts`, `_flush_undelivered_wakes`; the flush is
    called from the existing 15 s `idle_watcher` tick; `op_state` gains
    `undelivered_worker_events`. New event kinds: `heartbeat_carrier_undelivered`,
    `heartbeat_carrier_recovered`, `heartbeat_carrier_dropped`.
    All 6 new tests PASS: `evidence/10-issue-92-contract.log`.
- item: Dock the fact in the control-plane surface (README / CHANGELOG / generated Skill source as
  the byte budgets allow), re-render, and run the full focused set: the new test, the #76/#90/#88
  neighbours, `render-skills.py --check`, `validate.sh`. Freeze the candidate SHA and record raw
  receipts.
  status: done
  dispatched: self
  result: README + CHANGELOG + `templates/orchestrator/references/heartbeat-skeleton.txt`.
    `zcode-host-dispatch.md` deliberately untouched — 8174/8192 B and its sentences are pinned by
    the #65/#70 contract tests; the recovery is transparent to the Host and the existing "decide it
    from the worker's live `pending_permissions`" wording already covers a vanished request.
    Re-rendered (`--write` then `--check` PASS). Neighbours #76/#90/#88/#65/zcode-heartbeat PASS
    (`evidence/11-*.log`). New suite registered in `validate.sh` (replay list + lane b).
    First frozen candidate 6c9e3a3; full validate.sh EXIT=0 (`evidence/21-*.log`).
- item: Hand the frozen candidate to an independent review, read the findings against the diff, and
  hold the verdict. No finalize/archive/sink, no issue close, no main push before the outer ACCEPT.
  status: done
  dispatched: three rounds of `code-reviewer` children, each on an exact frozen SHA — round 1: two
    cuts on 6c9e3a3 (production correctness + trust boundary; test custody vs the acceptance text);
    round 2: one cut on the repair 3b6b616; round 3: one cut on the repair f2d141c. Findings came
    back to me and I held the verdict against the diff each time.
  result: My verdict at the time was ACCEPT-pending-outer on f2d141c. **The outer review then
    REJECTED f2d141c**; see the mission below. This result stands as written — it is the record of
    what I concluded before that verdict, and it was wrong about the candidate being ready.
    Round 1 found three real defects I had introduced (unvalidated peer reply killed the agent
    reader thread and wedged the worker; retry-on-any-error made a queue-full receipt a 15 s Host
    storm; weak/vacuous test assertions) — fixed in 3b6b616, both regression tests proven to FAIL on
    6c9e3a3 (`evidence/02-prev-candidate-regression.log`). Round 2 found three more (the no-cap test
    pinned nothing, proven by mutation — `evidence/04-no-cap-mutation-probe.{sh,log}`; `unknown-op`
    was wrongly settled, a wake 3b6b616 would have LOST; absence of an `error` key read as delivery
    and a false recovery logged) — fixed in f2d141c. Round 3: no defects.
    Merge compatibility with the new `main` (`cf8a5ec`, another session's #75) simulated in a
    detached worktree: `evidence/30-merge-simulation-validate.log`, EXIT=0.
- item: OUTER REVIEW REJECTED f2d141c. Repair the two named correctness defects in
  `scripts/kaola-acp-holder.py` minimally — (1) an accepted Host receipt must carry the EXACT
  `event_id` sent, with a mismatch or blank keeping the wake owed and emitting no `recovered`;
  (2) permission settlement, worker exit, or a stop racing an in-flight retry must not stage or
  prompt a stale permission — with deterministic failure-first tests that fail on f2d141c. Same
  event id, no new scheduler/registry/auto-approval. Also: the outer review found evidence paths
  cited by this branch's commit prose absent from the tree; make those paths real or correct the
  claims.
  status: done
  dispatched: self. A new mission, not an edit of the one above: an outer verdict is a custody
    change, and mission 4's result stays as the record of what I concluded before it.
  result: CODE CANDIDATE `0ed31b76c68368127506446b7fa355bd69bccc00`; the frozen tip is the docs
    commit that follows it.
    Defect 1: `worker_event_id()` derives the id the Host builds from the same four fields, and
    `_carrier_send` accepts only an exact match — blank, another worker's, a different cursor and a
    different kind now all stay owed as `host-reply-invalid`, with no `recovered` emitted.
    Defect 2: `_carrier_send` takes a `still_owed` predicate re-read immediately before the socket
    write; an offer that lost its reason is aborted BEFORE the bytes go out and recorded as
    `heartbeat_carrier_dropped`. `op_stop` sets `stop_requested` before cancelling permissions, so
    `stopping` joins `permission-settled` and `agent-exited` — the reason vocabulary is now four.
    Failure-first custody: both new tests FAIL on f2d141c —
    `evidence/05-f2d141c-outer-defect-regression.log`.
    Also fixed a harness defect that would have hidden defect 2: the test peer counted a bare
    connect as an offer.
    Evidence claims: the run's raw evidence is now COMMITTED under `kaola-workflow/issue-92/`, so
    every path this branch's commit messages cite resolves at the frozen SHA. `*.log` is gitignored
    and needed `git add -f`.
    14/14 suite (`evidence/14-issue-92-contract-r4.log`), render --check PASS, validate.sh EXIT=0 in
    413 s (`evidence/24-validate-r4.log`), `git diff --check` clean.
    STILL NOT DONE and deliberately so: Workflow finalize, archive, sink, issue close, main push.

- item: OUTER RE-REVIEW REJECTED f5bb239 — a remaining High race, and a missing claim record. The
  reviewer reproduced, on f5, a peer that takes the offer, withholds its receipt while a real
  settlement empties `pending_permissions`, then answers with the exact receipt: result
  `pending={}`, `undelivered={}`, `heartbeat_carrier_recovered`, one offer delivered. The pre-write
  `still_owed` check cannot make check+send+Host-staging atomic, so the README/CHANGELOG "never
  sent" claim was false. Resolve honestly against the Issue acceptance, distinguish carrier delivery
  from a live pending approval, pin the Host-side freshness obligation, and put the real
  `workflow-state.md` in the frozen tree.
  status: done
  dispatched: self. A new mission: an outer verdict is a custody change, and the result above stays
    as the record of what I concluded before it.
  result: Reproduced the race on my own tree FIRST (`evidence/07-post-write-race-probe.{py,log}`)
    and confirmed the reviewer exactly. No atomic boundary was attempted — it is unreachable across
    this transport without a withdrawal op and Host-side un-staging, which is new surface and the
    wrong trade for a Host that must re-verify freshness anyway.
    Withdrew the false claim: the "never sent" sentence is REMOVED from README and CHANGELOG, not
    softened, and the pre-write test is renamed to what it really proves
    (`test_a_wake_that_dies_before_the_write_is_not_sent`).
    Kept the two facts apart: a delivery whose request died in flight is now recorded as
    `heartbeat_carrier_delivered_stale` with the reason that overtook it and the Host's own receipt,
    never as `heartbeat_carrier_recovered`.
    Pinned the Host side, which is where safety can actually live: the heartbeat prompt now also
    says an arriving event is only a locator that may already have been settled in flight, and
    `test_the_host_contract_requires_fresh_verification` pins five obligations on the generated
    surfaces plus the behaviour — acting on a stale locator is refused with `no-pending-permission`.
    At-least-once and the `event_id` dedup are untouched.
    Failure-first custody: both new tests FAIL on f5bb239 —
    `evidence/06-f5bb239-rerereview-regression.log`.
    Claim record: `workflow-state.md` copied byte-for-byte from the existing main-root record
    (sha256 `123fa0ab…`, verified identical). Nothing authored or edited; no foreign run touched.
    Verification: 16/16 suite (`evidence/15-issue-92-contract-r5.log`), render --check PASS.
    Full `validate.sh` for this candidate is the OUTER verification's exit 0, not a run of mine —
    both of my attempts were killed by session teardown with no exit status, and
    `evidence/25-validate-r5-RESULT.md` records that provenance rather than dressing a truncated log
    up as a pass.
    STILL NOT DONE and deliberately so: Workflow finalize, archive, sink, issue close, main push,
    rebase.

## Record-keeping correction (2026-09-19)

Missions 1, 3 and 4 were carried out in order, but their `status`/`result` lines were never
actually written to this file: the edits used an unchecked string replace that silently matched
nothing, and I did not verify the file afterwards. The results above were reconstructed from the
branch history and the raw logs in `evidence/`, both of which are contemporaneous. Nothing
previously recorded here has been altered — mission 2's result is exactly as first written, and
mission 4's superseded verdict is preserved rather than corrected in place. This is the same class
of defect the outer review found in the commit prose: a claim recorded without checking that what
it named was really there.
