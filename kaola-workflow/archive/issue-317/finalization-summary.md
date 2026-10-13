# Finalization summary — issue-317

## Delivered

Fix for #317 per the owner's final decision updates (2026-10-14
00:44–00:47, comments on #317): the two-rule core wake model.

- **Rule 1 — automatic all-ended wake** (`bc31c303`): when the Host is
  idle, no follow-up is queued, and no seat has an active turn, the
  `all-idle` wake fires once per **new** all-ended episode. Real work
  arms the next episode (a working non-exempt seat, a non-exempt worker
  stop, or a self turn that delivers worker events); a Delegator send
  alone does not. A carried all-idle latch and the #302
  Delegator-origin rule cannot suppress it. A live `send --wait` /
  `op_wait` caller holds that one wake until the caller has left (no
  double wake). The same episode never wakes twice.
- **Rule 2 — Host-initiated wake** (`85ca4bf1`): `kaola-acp.py wake
  --reason` sends `needs_decision`, `question_waiting`, or
  `delivery_review` immediately — a working seat and the all-idle
  latch do not suppress it, each call is a new `event_seq`. The Host
  can wake the Delegator at any time (decision, grant, blocker,
  question) without waiting for all processes to end.
- The relay stays **`send --no-wait`** (the owner cancelled the
  `--wait` switch; no consumption tracking, no
  `delegator_turn_unconsumed` reason).
- Folding: permission/blocked, failure/exit/boot, exact stop, and
  `holder_lost` stay as genuinely different facts; the two core rules
  documented in `docs/api.md` (+26 in the second commit) and
  `webhook-wake.md` with the edge-case table (crash → #299 backfill;
  stuck seat → Host-initiated wake; delivery failure → #318).
- Tests: six new cases in `test-issue-302-delegator-wake-gate.py`
  (+321): carried latch wakes once per new episode; a completed seat
  opens one new episode; a live send waiter defers the one all-idle;
  the real host wakes once per all-ended episode; the Host wake fires
  while a seat works; the CLI wake does not wait for the seat.

## Candidate

- Commits `bc31c303` + `85ca4bf1` on `workflow/issue-317` (worktree
  `.kw/worktrees/issue-317`, base `8739ad9e`). Implemented by the
  `grok/default` seat `grok-KPR-i317-all-ended` (base turn + CONTINUE
  turn after the owner decision updates); reviewed and finalized by the
  Host.

## Evidence

- Host diff review (this run, both commits): episode arming exactly the
  owner's real-work facts; waiter-hold prevents double wakes; the CLI
  wake is unsuppressible and per-call `event_seq`'d; no relay change;
  genuinely different triggers kept.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-302-delegator-wake-gate.py`
  (updated), `test-issue-299-delegator-webhook.py`,
  `test-issue-255-lifecycle-state.py`, `test-zcode-heartbeat-contract.py`,
  `test-issue-315-decision-wake.py`, `test-issue-271-dispatch-help.py`,
  `test-progressive-disclosure.py` (logs `/tmp/kpr-i317-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `e83c5ed64ae750fa…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The sink rebases onto the #318/#316-advanced main (holder + wake
  docs overlap expected); integrated tree re-verified by the Host.
  Full inventory follows as the final gate. No release (owner
  releases).

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
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kaola-delegator/references/webhook-wake.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-302-delegator-wake-gate.py
- tests/contract/test-zcode-heartbeat-contract.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
