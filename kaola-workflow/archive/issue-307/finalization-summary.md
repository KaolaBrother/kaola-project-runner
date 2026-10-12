# Finalization summary — issue-307

## Delivered

Fix for #307: `all-idle` wakes once per busy→all-idle transition; a
Delegator-admitted turn neither opens an idle episode nor wakes by itself.

- `scripts/kaola-acp-holder.py`:
  - The every-turn `_note_delegator_working_again()` call (which cleared
    the once-per-episode latch for every new turn, including
    Delegator-sent ones — the KPM wake storm, event_seq 4382-4418) is
    removed from turn admission.
  - The latch now clears only on real "working again" facts: a dispatched
    non-exempt holder becomes working, a non-exempt worker terminates, or
    a self turn admits new worker events.
  - `delegator_turn_wake_reason`: the Delegator-origin check is gated on
    `all_idle_due` — a Delegator-admitted turn returns None (no wake)
    unless the transition is actually due, so the one transition wake
    still reports, including when that Delegator turn stops the last
    working seat.
  - Stale comments/docstrings claiming a Delegator-caused turn does not
    suppress the wake are corrected; `webhook-wake.md` states the
    once-per-transition semantics.
- Tests: `test-issue-302-delegator-wake-gate.py` extended with 4 cases —
  the KPM sequence (repeated Delegator sends to an idle Host with no
  live seat → no wake), a Delegator turn that stops the last working
  seat → exactly one `all-idle`, latched Delegator turn + quiet self
  turn → no wake, and a worker-event self turn re-opening the episode.
  All #302/#303/#304/#305 cases remain green (stop-time re-checks,
  dedupe, error/permission/exact-stop wakes).
- `docs/api.md` (+27); CHANGELOG Unreleased — **Seats: restart
  required** (holder changed).

## Candidate

- Implementation commit `de29e7d9` on `workflow/issue-307` (worktree
  `.kw/worktrees/issue-307`, base `d47e9251`). Implemented by the
  `grok/default` seat `grok-KPR-i307-once-idle`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): each hard owner rule (a)–(e) mapped to a
  passing test; the latch-clear facts are exactly the three real
  working-again facts.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-302-delegator-wake-gate.py`
  (updated), `test-issue-299-delegator-webhook.py`,
  `test-issue-255-lifecycle-state.py`,
  `test-issue-296-shared-tier-seats.py`, `test-issue-271-dispatch-help.py`,
  `test-zcode-heartbeat-contract.py` (logs `/tmp/kpr-i307-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `a6599eff900339ec…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory runs before the release content commit, per the owner
  order. Release v0.9.9 follows this merge.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kaola-delegator/references/webhook-wake.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-299-delegator-webhook.py
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
