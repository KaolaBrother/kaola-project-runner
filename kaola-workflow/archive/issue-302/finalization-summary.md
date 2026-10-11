# Finalization summary — issue-302

## Delivered

Fix for #302 plus the owner's 16:49 addendum: the Delegator webhook wakes
only when something actually needs the Delegator, and never twice for the
same event.

- `scripts/kaola-acp-holder.py`: a closed `DELEGATOR_WAKE_REASONS`
  vocabulary and `delegator_turn_wake_reason(...)` gate the turn-end wake.
  Wakes: host stopped with pending work (length stops →
  `host_stopped_pending`), permission pending (`permission_required`),
  refusal/decision needed, error/failure/agent exit/boot failure, exact
  stop, death recovery, and — per the addendum — `all-idle` when the Host
  goes idle and no holder dispatched by this Host is still live
  (`holders_dispatched_by(holder_instance_id)`, regardless of recorded
  pending work). No wake: self-continuing turn ends (next beat already
  admitted), turn ends caused by the Delegator's own resume/steer/send,
  and clean idle while a live seat works. No time-based throttling or
  coalescing anywhere.
- `scripts/kaola-acp.py`: `DELEGATOR_WEBHOOK_TIMEOUT` 3 s → **12 s** (in
  the required 10–15 s range); a client timeout is **never retried** (it
  may already have been accepted — retrying risks double delivery);
  retries are connection errors, HTTP 5xx, 408 and 429 only, bounded.
  Sender-side dedupe: `_webhook_claim_event` claims
  `holder_instance_id + event_seq` before the POST; a claimed pair never
  posts twice; skipped/invalid attempts do not consume a claim; a
  death-recovery wake carries a new event_seq so it delivers. The payload
  gains the `reason` field (kaola-delegator-wake/1 compatible).
- Reconciliation with the #299 21:57 rule: every stop that truly needs
  the Delegator still wakes (permission, error, exit, boot failure, exact
  stop, recovered death); the line is "does the Delegator need to act",
  not "fewer wakes" — stated in docs and asserted by tests.
- Tests: `tests/contract/test-issue-302-delegator-wake-gate.py` (13
  cases, 453 lines, mock HTTP endpoint): reason mapping per stop path;
  slow endpoint (between the old 3 s and the new 12 s) → exactly one
  delivery; timeout → no retry + failure receipt; connection/5xx →
  bounded retry; duplicate event → one POST; recovery seq delivers;
  skipped/invalid does not consume the claim; Delegator-caused turn end →
  no wake; zero live seats → `all-idle` wake; live seat + nothing owed →
  no wake; self-continuing turn → no wake until the Host really stops;
  refusal → decision wake; permission/failure/exit/boot still wake;
  killed holder recovered once. The 299 suite updated for the new policy.
- Docs: `docs/api.md` (+154 lines across both commits) and
  `skills/kaola-delegator/references/webhook-wake.md` (wake conditions,
  reason vocabulary, all-idle, timeout/retry/dedupe policy); CHANGELOG
  Unreleased — **Seats: restart required** (holder hook changed).

## Candidate

- Commits `73aec1bc` (wake gate + policy) and `f73dda6d` (all-idle
  addendum) on `workflow/issue-302` (worktree `.kw/worktrees/issue-302`,
  base `0b7e0ac0`). Implemented by the `grok/default` seat
  `grok-KPR-i302-wake-gate`; reviewed and finalized by the Host.

## Evidence

- Host diff review (this run): every required matrix case verified
  present and green; the #299 rule preserved; the owner's live webhook
  config untouched (tests use the env-overridable temp config path only).
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-302-delegator-wake-gate.py`
  (new), `test-issue-299-delegator-webhook.py` (updated),
  `test-issue-255-lifecycle-state.py`, `test-issue-271-dispatch-help.py`,
  `test-issue-273-list-identity.py`, `test-issue-289-dead-holder-stop.py`,
  `test-ddd-pack.py`, `test-issue-130-pty-retired.py`
  (logs `/tmp/kpr-i302-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `33910d0e4029b30b…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory runs before the release content commit, per the owner
  order. Release v0.9.7 follows this merge. No live-webhook verification
  (owner boundary); the owner's routine will observe the new policy after
  install.

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
- scripts/validate.sh
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
- tests/contract/mock-acp-agent.py
- tests/contract/test-issue-299-delegator-webhook.py
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
