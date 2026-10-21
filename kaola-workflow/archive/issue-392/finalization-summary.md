# Finalization Summary — issue-392

## Delivered

Issue #392 is fixed. A Host turn that ends while no seat is in a turn now wakes
the Delegator once with the new `host_turn_done` reason when that turn was
admitted without `--wait`, even if the same idle episode already sent
`all-idle`. Previously that path returned no wake and wrote no receipt, so the
Delegator never learned the second turn had ended.

`op_prompt` records `wait` on the turn; `delegator_turn_wake_reason` takes
`unconsumed` and returns `host_turn_done` only in the latched no-seat
Delegator branch; `_delegator_turn_end_reason` passes `not turn["wait"]`. Both
closed reason vocabularies (holder and CLI) now carry `host_turn_done`.
Preserved: `--wait` silence, self-turn `all-idle`, live-seat Delegator silence,
attention/decision precedence, the #317 carried-latch reset, and consecutive
`--wait` conversations. The `--wait` timeout/dead-caller deferred decision is
out of scope and documented as such.

Tests: `tests/contract/test-issue-392-host-turn-done-wake.py` (8 cases, real
CLI + holder + mock ACP agent + loopback endpoint) and the extended
`test-issue-302-delegator-wake-gate.py` (39 cases). Both are registered in
`scripts/validate.sh`. Docs: `docs/api.md`, the Delegator webhook reference,
and an Unreleased CHANGELOG entry with `Seats: restart required` for the
holder; the CLI copy takes effect on installation.

## Candidate

Branch `workflow/issue-392` at `295497cd` (`docs: correct the #392 restart-set
and --wait scope facts`), child of `8e992bf4` (the fix), based on `7a3793db`
(main after the issue-393 archive). The tip carries only the two review
documentation corrections; no tag, release, or install was made.

## Evidence

- Baseline reproduction at `7a3793db` with
  `/tmp/kpr392/tests/contract/test-issue-392-repro.py`: 5 tests, 2 failures
  (no wake and no receipt after the second `--no-wait` turn).
- Candidate focused gate:
  `bash .../scripts/validate.sh --suite test-issue-392-host-turn-done-wake
  --suite test-issue-302-delegator-wake-gate` → 8/8 and 39/39 passed.
- Related direct runs: `test-issue-315-decision-wake.py` 6/6,
  `test-issue-324-wake-fixes.py` 10/10, `test-issue-325-webhook-outage.py` 7/7.
- `./scripts/render-skills.py --check` PASS with budgets OK; generated Skills
  changed only through render.
- Independent review accepted engineering and the two documentation
  corrections; Host verdict accepted in conversation.
- Candidate-bound validation record:
  `kaola-workflow/issue-392/.cache/final-validation.md` (`verdict: pass`).

## Known failures or unverified scope

- The focused suites are a subset, not whole-inventory coverage. The Host owns
  the full `KAOLA_FULL_GATE=1` run.
- The `--wait` timeout and a caller that disappears are not decided by this
  change; `docs/api.md` states that boundary.
- The candidate suites were last executed immediately before the docs-only
  `295497cd`; that commit changes only `CHANGELOG.md` and `docs/api.md`.
- No live consumer-bridge UAT was run for this change. A running holder needs
  its restart; the CLI copy applies with installation.
- No tag, release, or install.

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
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
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
- tests/contract/test-issue-392-host-turn-done-wake.py

## Follow-Up Items

- None filed. The remaining G1 timeout/dead-caller decision is a documented
  scope boundary, not a new defect.

Readiness: accepted candidate; focused suites and renderer green; ready to
merge and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-392/.cache/final-validation.md
- kaola-workflow/archive/issue-392/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-392/finalization-summary.md
- kaola-workflow/archive/issue-392/mission-ledger.jsonl
- kaola-workflow/archive/issue-392/workflow-state.md
