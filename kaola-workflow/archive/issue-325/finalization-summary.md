# Finalization Summary — issue-325

## Delivered

Grok worker `grok-KPR-i325-webhook-outage` (grok/default, dispatched by this ZCode Host after
haiku/dsh/opencode unavailability) fixed the unnoticed webhook-outage class in commit `6221d4b1`
on `workflow/issue-325` (base = main `0db89ebb`):

1. **Run-level repeated-failure condition** (\`kaola-delegator-webhook-repeated-failure/1\`): a run
   of final failed deliveries (≥2 final failures inside a 15-minute window) is kept in the receipt
   store and reported — a Host notice is raised **once**, and when the window passes the heartbeat
   path carries it with its own bound (no second notice, no new wake reason; the documented
   fallback order is retry → receipt-route → host-notice → heartbeat).
2. **Outage receipt retention**: each event's final failure is kept **apart from the 32-entry
   attempt ring** in \`failed_receipts\` with a 256 cap — the next 32 deliveries cannot erase a
   101-minute outage; the archive drops only the oldest past 256.
3. **Delegator-side once-notice statement**: wired in \`kaola-delegator/references/webhook-wake.md\`
   (and \`inquiry-report.md\`) — when the routine webhook answers 4xx for more than one event, the
   Delegator/heartbeat tells the user once, with the window and the count.
4. Rendered outputs regenerated (\`render-skills.py --check\` PASS); CHANGELOG Unreleased section
   added; \`docs/api.md\` documents the run schema and retention; \`test-issue-325-webhook-outage.py\`
   (7 tests) registered in both validate.sh lists.

## Candidate

Branch `workflow/issue-325`, single commit `6221d4b1` over main `0db89ebb`.
Recorder-bound hash: `256fa864c691ad64…`.

## Evidence

- Dispatch attempts: claude-code/haiku (zero work, account session limit until 22:50 Taipei),
  dsh/default and opencode/default (turn execution unavailable — every turn fails instantly with
  zero output, both seats exact-stopped; evidence in the mission ledger). Final dispatch on
  grok/default: fp `cea1fa88…`, cursor 37; turn completed end_turn (two turns; wrap-up verified
  the worktree records).
- Host review: diff verified against the three required outcomes; no wake-ordering or queue
  changes (webhook store + docs only; code comment "This does not add a wake reason").
- Host runs on the exact candidate: full inventory `./scripts/validate.sh` **rc=0** (proxies and
  ambient `KAOLA_ACP_DISPATCHER` unset); `render-skills.py --check` PASS; suites 325, 299, 302,
  309 green standalone.
- Validation record: `kaola-workflow/issue-325/.cache/final-validation.md` (verdict pass).

## Known failures and unverified scope

- No live webhook delivery against a real endpoint (mock-webhook fixtures only, per constraint:
  webhook config never read/printed/called).
- Running seats need a restart to pick up the CLI-side change; no install performed.

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
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-delegator/references/webhook-wake.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- templates/kaola-delegator/references/inquiry-report.md
- templates/kaola-delegator/references/webhook-wake.md
- tests/contract/test-issue-325-webhook-outage.py

## Follow-Up Items

- Worker-pool runtime unavailability (dsh/opencode instant turn failures) is an environment fact
  reported to the Delegator; no KPR issue filed without owner direction.
- searched: duplicate probe `gh issue list --state all --search "webhook 400 outage"` before the
  run → only #325 itself.

## Final readiness

Ready: candidate accepted (Host review + full inventory green on the candidate), validation
recorded pass, no tag/release/install performed.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-325/.cache/final-validation.md
- kaola-workflow/archive/issue-325/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-325/finalization-summary.md
- kaola-workflow/archive/issue-325/mission-ledger.jsonl
- kaola-workflow/archive/issue-325/workflow-state.md
