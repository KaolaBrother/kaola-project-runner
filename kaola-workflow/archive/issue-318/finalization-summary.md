# Finalization summary — issue-318

## Delivered

Fix for #318 (review gaps G2 + G8): a final failed webhook delivery
carries a class-split recovery route, and the Delegator inquiry treats
a final failed `last_receipt` as a missed wake.

- `scripts/kaola-recovery-routes.py` / `scripts/kaola-acp.py`: the
  stamp on a final `failed` row is split by class — final 401/403 →
  rotate the sender key (webhook-wake.md step 7), then `test`; final
  404 → reconfigure the URL, then `test`; final 400/408/429/5xx, a
  final `connection`, a `timeout`, and any other final `http-status` →
  the lost-wake route ("this wake was lost; run `status`, then
  `observe`/`capture` for the recorded Host and the full standard
  inquiry; run `test` once — if it delivers, nothing else is owed;
  otherwise stay heartbeat-only and report"). **Non-final (retrying)
  rows carry no route** — the misleading "do not retry a final
  receipt" text on in-flight attempts is gone.
- `templates/kaola-delegator/references/inquiry-report.md` (rendered):
  "If `status.last_receipt` is `failed` and `final`, treat it as a
  missed wake and run the whole inquiry; never conclude 'nothing new'
  from an empty webhook run." (One neutral budget reword of the
  language section to pay for it.)
- `missed_event_seq`: **skipped** (the issue's optional item; not
  trivial, would widen the payload key set — per the Delegator brief's
  default).
- No holder-side re-offer timer. Holder unchanged — Seats: restart not
  required (per-call CLIs only).
- Tests: `test-issue-299-delegator-webhook.py` — final 401/403/404
  carry their specific routes, non-final rows unstamped; the rendered
  inquiry reference contains the missed-wake instruction. `302` and
  `309` suites updated for the stamp/table changes.

## Candidate

- Implementation commit `8bf6327d` on `workflow/issue-318` (worktree
  `.kw/worktrees/issue-318`, base `8739ad9e`). Implemented by the
  `grok/default` seat `grok-KPR-i318-lost-wake`; reviewed and finalized
  by the Host.

## Evidence

- Host diff review (this run): route split exactly per the issue
  (covers G8); non-final unstamped verified; missed_event_seq honestly
  skipped; no timer.
- `./scripts/render-skills.py --check` — PASS.
- Affected suites, all exit 0: `test-issue-299-delegator-webhook.py`
  (updated), `test-issue-302-delegator-wake-gate.py`,
  `test-issue-309-recovery-routes.py`, `test-issue-271-dispatch-help.py`,
  `test-progressive-disclosure.py` (logs `/tmp/kpr-i318-*.log`).
- `.cache/final-validation.md`: verdict `pass`, candidate hash
  `a85195d95efe217f…`.
- Worker seat exact-stopped after acceptance (`state: stopped`).

## Known failures / unverified scope

- #317 lands separately (holder side); full inventory after the last of
  the three. No release (owner releases).

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
- scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/inquiry-report.md
- tests/contract/test-issue-299-delegator-webhook.py
- tests/contract/test-issue-302-delegator-wake-gate.py
- tests/contract/test-issue-309-recovery-routes.py

## Follow-Up Items

- None.

## Final readiness

Ready: candidate reviewed, affected scope green, validation recorded.
Proceed to sink (merge) and archive.
