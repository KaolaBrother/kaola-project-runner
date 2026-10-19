# Finalization summary — issue-311

## Delivered

Fix for #311: webhook receipts diagnose 4xx failures, transient 400s
retry, and a lost Host wakes the Delegator without a new start.

- `scripts/kaola-acp.py`:
  - HTTP error receipts store a **truncated, redacted** response body
    (configured secrets, including quoted forms, replaced with
    `[redacted]`; a body read cap) plus an **allowlisted** response
    header set with per-header length limits. The config URL/key can
    never appear in a receipt.
  - Retry policy (supersedes #302's 400-final rule, noted in code):
    connection errors and HTTP **400/408/429/5xx** retry with backoff;
    401/403/404 and other 4xx stay final on attempt 1.
  - `delegator-webhook status` scans the project's Host record, detects
    a dead/holder-lost Host, and sends the existing `holder_lost` wake
    through the existing sender with the existing dedupe — the Delegator
    cron inquiry leg runs it, bounded by `cadence.interval_minutes`, so
    the ~5h silent gap of the VRPCadCore case is covered without a new
    Host start.
- Tests: `test-issue-299-delegator-webhook.py` (+231) — body/header
  redaction and truncation, the new retry matrix (400/408/429 retry,
  401/403/404 final), the status-driven holder_lost wake with cadence
  bound and dedupe; `test-issue-302-delegator-wake-gate.py` adjusted to
  the superseding retry rule.
- `docs/api.md` (+107) and the Delegator Skill reference via render;
  CHANGELOG Unreleased entry with an honest Seats/restart line
  (per-call CLI + cron-leg behavior; no seat restart required).

## Candidate

- Implementation commit `216a6272` on `workflow/issue-311` (worktree
  `.kw/worktrees/issue-311`, base `4cb1acc7`). Implemented by the
  `grok/default` seat `grok-KPR-i311-webhook-diag`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): redaction paths verified (secret
  replacement incl. quoted forms, body/header caps); retry set exactly
  the issue's; the detection leg reuses the existing wake sender and is
  cadence-bounded; #302-era tests updated, not deleted.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-299-delegator-webhook.py`
  (updated), `test-issue-302-delegator-wake-gate.py`,
  `test-issue-271-dispatch-help.py`, `test-ddd-pack.py`,
  `test-issue-255-lifecycle-state.py` (logs `/tmp/kpr-i311-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `41a1bb016b7658cf…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory after the last of the four issues, per the run plan.
  No release or install in this run (owner approval required).

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
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/webhook-wake.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-299-delegator-webhook.py
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

- kaola-project-manager mirror comment on KaolaBrother/kaola-project-manager#173 after
  merge (owner instruction: comment only).

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-311/finalization-summary.md
