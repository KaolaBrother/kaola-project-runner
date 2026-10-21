# Finalization Summary — Issue #380

## Delivered

Implemented and fixed KPR #380 on `workflow/issue-380`: `send` and `steer` accept
`--client-message-id` and admit it idempotently.

- A 64-entry FIFO admission ledger keyed by id + op + text fingerprint + ACP
  session. Same admission replays the original receipt (`idempotent_replay`,
  `replay_of_turn_request_id`, original `dispatch_event_cursor` when present,
  `holder_instance_id`); a different op/text/session is a clean
  `client-message-id-conflict`.
- Prompt lookup/write/register is one admission critical section; a native
  steer rechecks the ledger in the admission lock and reserves after its frame
  is written; a composite interrupt reserves at entry. A concurrent same-id
  request replays the reservation instead of writing a second frame.
- Reservation tokens commit the final receipt in place, so settlement never
  reorders the FIFO and a late final receipt cannot overwrite a newer admission
  that reused the id after eviction. A clean no-write withdraws its reservation
  and restores the receipt it displaced when it is still the newest entry.
- Restart-unknown refuses an id/text matching `record.last_prompt`; the
  composite checks this itself before reserving or cancelling. The guard is
  narrow: a different text or an older id after a newer prompt is a new
  admission, with no cross-restart full-id conflict protection.
- `view` echoes conditional `clientMessageId` on the prompt's `messages[]` row
  and `turns[]` row; `record.last_prompt.client_message_id` keeps it.
- `op_steer`/`op_steer_interrupt` validate `expected_holder_instance_id` at
  entry before any replay/conflict answer; the CLI forwards only an explicit
  binding and the interrupt follow-up prompt carries the verified holder id.
- `docs/api.md`, `CHANGELOG.md`, `scripts/validate.sh` and the generated Skill
  copies are updated; the template byte budgets are unchanged.

Candidate: `f4400d2d692ca86befd8fe9ef465c32e8acfdf3f` on `workflow/issue-380`;
parent `90a20a3853456de8aa2826bfe05e4e9dd791a3b4` (base `18ac991b`). No tag,
release, publish, install, or KPM-side operation was performed.

## Acceptance Evidence

- Host acceptance of `f4400d2d`: diff reviewed, clean-tip `render --check` PASS,
  `test-issue-380-client-message-id` (20 cases) and
  `test-issue-379-receipt-mutation` exit 0 with no residual processes.
- Independent review: `/tmp/kpr380rev/REVIEW.md` (F1-F5 raised and fixed).
- Fixed-code reviewer probes: `/tmp/kpr380rev-fixed/probes.json`,
  `/tmp/kpr380rev-fixed/composite-restart.json`.
- Clean-tip focused log: `/tmp/kpr380-fix-clean.log` (candidate `f4400d2d`
  clean; 380 50.6 s, 379 11.0 s).
- Same final bytes affected-suite log: `/tmp/kpr380-fix-validation.log`
  (65/263/309/255/264 pass).
- Before/after duplicate-turn comparison: `/tmp/kpr380-after.json` and
  `/tmp/kpr380-evidence/repro.json`.

## Known Failures and Unverified Scope

- No full-inventory `validate.sh` run; the Host-run focused suites and the
  finalization validation command cover the changed interfaces.
- No live external platform UAT was performed; the contract suites use the
  mock ACP agent.
- `scripts/kaola-acp-holder.py` is in the operator restart set, so a running
  holder keeps the old admission behavior until it restarts.

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
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
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
- tests/contract/test-issue-380-client-message-id.py

## Follow-Up Items

- No new follow-up issue was filed by this run.
- Holder restart remains an operational note; `scripts/kaola-acp.py` is
  per-call and takes effect with installation.
- No release, tag, publish, or install is part of this finalization.

Final readiness: ready. Merge sink to `main`, close #380 with the Host-supplied
closing comment, archive under `kaola-workflow/archive/issue-380/`, and remove
the run worktree.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-380/.cache/final-validation.md
- kaola-workflow/archive/issue-380/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-380/finalization-summary.md
- kaola-workflow/archive/issue-380/mission-ledger.jsonl
- kaola-workflow/archive/issue-380/workflow-state.md
