# Finalization summary — issue-320

## Delivered

Fix for #320 (review gap G4): every wake failure mode carries a
recovery route and a readable record.

- **(i) Spawn failure**: a holder that cannot spawn the deliver child
  writes a `failed` receipt row (`error: spawn-failed`) through the
  same receipts file, so `status.last_receipt` shows it.
- **(ii) `wake-spawn-failed` route** replaces the misleading
  session-restart text: "the wake was not attempted; run
  `delegator-webhook test`; if that delivers, continue the inquiry
  now."
- **(iii) Stamp recursion**: `stamp` walks a nested
  `delegator_death_wake` including `sent: false` as a failure; the
  nested spawn-failed gets the correct route.
- **(iv) Record-root mismatch**: the status scan's `scan: incomplete`
  now carries `reason: record-root-mismatch`, so the existing route
  attaches.
- **(v) Receipt-write failure**: the deliver child prints one stderr
  line; the holder copies its stderr into the event log (bounded,
  replacing DEVNULL).
- **(vi) Unresolvable project**: recorded as a holder event (not a
  fallback receipts file — the honest choice, stated).
- **Bonus**: a death-wake lock/log `OSError` returns
  `death-wake-unrecorded` with a route instead of silently omitting
  the key.
- Tests: `test-issue-320-wake-diagnostics.py` (7 cases, 476 lines) —
  one per mode plus the OSError case.
- `docs/api.md` (+86) — the diagnostics routes; CHANGELOG Unreleased —
  **Seats: restart required** (holder changed).

## Candidate

- Implementation commit `727f366e` on `workflow/issue-320` (worktree
  `.kw/worktrees/issue-320`, base `7602a613`). Implemented by the
  `grok/default` seat `grok-KPR-i320-wake-diag`; reviewed and
  finalized by the Host.

## Evidence

- Host diff review (this run): all six modes plus the bonus have
  routes/readers; the spawn-failed route corrects the wrong restart
  text; stderr capture is bounded.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-320-wake-diagnostics.py`
  (new), `test-issue-299-delegator-webhook.py`,
  `test-issue-309-recovery-routes.py`,
  `test-issue-302-delegator-wake-gate.py`, `test-issue-271-dispatch-help.py`,
  `test-progressive-disclosure.py` (logs `/tmp/kpr-i320-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `b1b5316974ebd43b…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- The sink rebases onto the #321-advanced main (kaola-acp death-wake
  overlap with #319 expected); the Host integrates and re-verifies.
  Full inventory after the last merge. No release.

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
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-320-wake-diagnostics.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-320/finalization-summary.md
