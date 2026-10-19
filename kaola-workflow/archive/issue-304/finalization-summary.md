# Finalization summary — issue-304

## Delivered

Fix for #304 plus the owner-directed version-skew check: webhook attempt
receipts record the wake reason, skip causes use their own key, and a
legitimate wake from a pre-upgrade holder is not lost across an install.

- `scripts/kaola-acp.py`:
  - `_webhook_attempt_receipt`: `delivered` and `failed` receipts always
    include `reason` — the payload's string wake reason, or `null` when
    the accepted payload carried none (never an invented token).
    `skipped` receipts carry `skip_reason` (`not-configured`,
    `duplicate`) and no `reason` key; readers ignore `skip_reason`
    unless `result` is `skipped`.
  - Payload validation: the key set is split into
    `DELEGATOR_WEBHOOK_PAYLOAD_CORE_KEYS` (the first #299 sender shape)
    and optional `state_detail`/`reason` (v0.9.6 / v0.9.7 additions), so
    a running pre-upgrade holder's payload (the kaola-project-manager evidence: events
    3626/3635/3639 refused `invalid-payload` during the v0.9.7 switch)
    delivers with an honest `reason: null`; genuinely malformed payloads
    (wrong schema, missing core identity keys) are still refused.
- Tests: `test-issue-299-delegator-webhook.py` extended with
  `test_delivered_failed_and_skipped_receipt_fields`,
  `test_status_reads_pre_304_receipts_unchanged` (backward-compatible
  status reads of pre-#304 receipts), and
  `test_old_shape_payload_delivers_malformed_is_refused`; the 302 suite
  adjusted to the receipt field change.
- `docs/api.md`: receipt schema (`reason`, `skip_reason`, honest null)
  and the payload compatibility rule; CHANGELOG Unreleased entry.

## Candidate

- Implementation commit `b05da4a6` on `workflow/issue-304` (worktree
  `.kw/worktrees/issue-304`, base `24b08d58`). Implemented by the
  `grok/default` seat `grok-KPR-i304-wake-receipt`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): receipt schema and tolerant validation
  verified against the issue's expected behavior and the kaola-project-manager evidence.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-299-delegator-webhook.py`
  (updated), `test-issue-302-delegator-wake-gate.py`,
  `test-issue-271-dispatch-help.py`, `test-ddd-pack.py`
  (logs `/tmp/kpr-i304-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `bb07ff687636d202…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- Full inventory at the v0.9.8 release boundary over the integrated
  candidate, per the run plan.

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
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-299-delegator-webhook.py
- tests/contract/test-issue-302-delegator-wake-gate.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-304/finalization-summary.md
