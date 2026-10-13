# Finalization summary — issue-319

## Delivered

Fix for #319 (review gap G3): a `holder_lost` wake fires whenever the
holder pid is dead, even when the ACP agent child survives.

- `scripts/kaola-acp.py`: `delegator-webhook status` and
  `command_start` emit `holder_lost` when the holder pid is dead,
  **regardless of agent liveness** — the eligibility rule. The wake
  payload stays `state_detail: holder_lost` and does **not** carry
  agent pids. A live agent still blocks `start` from **replacing** the
  record (the safety guard kept for replacement only); the start/stop
  **receipt** keeps the live agent pids and the holder-lost route:
  exact-stop the orphaned agent, then resume or restart the Host with
  a fresh session plus summary.
- Tests: `test-issue-299-delegator-webhook.py` (+120) —
  `test_surviving_agent_wakes_holder_lost_and_start_keeps_the_record`
  (a real child that outlives its holder).
- `docs/api.md` (+50) and `webhook-wake.md` — the eligibility rule;
  CHANGELOG Unreleased — Seats: restart not required (per-call CLI).

## Candidate

- Implementation commit `433724d8` on `workflow/issue-319` (worktree
  `.kw/worktrees/issue-319`, base `3274575e`). Implemented by the
  `grok/default` seat `grok-KPR-i319-agent-alive`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): the eligibility-vs-replacement
  separation verified — wake on holder-dead, replacement blocked on
  agent-alive, pids only in receipts.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-299-delegator-webhook.py`
  (updated), `test-issue-302-delegator-wake-gate.py`,
  `test-issue-289-dead-holder-stop.py`, `test-issue-271-dispatch-help.py`
  (logs `/tmp/kpr-i319-*.log`). The 320 suite is absent on this base
  (pre-#320) and runs on the integrated tree after the sink.
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `f0741aca82de72ec…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The sink rebases onto the #320-advanced main (kaola-acp death-wake
  area overlap); the Host integrates and re-verifies. Full inventory
  after the merge. No release.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kaola-delegator/references/webhook-wake.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-299-delegator-webhook.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-319/finalization-summary.md
