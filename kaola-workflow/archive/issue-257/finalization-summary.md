# Finalization Summary — Issue #257

## Delivered

Accepted candidate: 7d21beaac7b24c35c3ea3f8ecb8850994782f12b (branch workflow/issue-257, base
main eb7f5b17). The owner accepted this exact commit.

`kaola-acp-view/1` gains per-turn timing and answered-permission outcomes, built from facts the
holder already records. The schema name is unchanged and every field is additive:

- `messages[].received_at`: the time the message's first chunk arrived, equal to that chunk's
  `events.jsonl` `ts`. It is `null` for the prompt message the holder wrote itself.
- `turn.started_at` / `turn.ended_at`, and `turns[]` with `started_at`, `ended_at`, `outcome`,
  `stop_reason`, `start_cursor`, `end_cursor` (max 200 entries).
- `answered_permissions[]`: `request_id`, `title`, `tool_call_id`, `options`,
  `chosen_option`, `outcome` (approved/denied/cancelled/unknown), `answered_at`, `cursor`
  (max 200 entries).

Source change: scripts/kaola-acp-holder.py, with the 10 skills/*/scripts copies regenerated.
Documentation: docs/api.md and docs/acp-watch/list-view.md. Fixture:
tests/contract/fixtures/kaola-acp-view-1.sample.json. Contract tests:
tests/contract/test-acp-watch-contract.py and tests/contract/test-acp-follow-contract.py.
Following the repository's content/pin convention, templates/grok-bot/accepted-revision.json
returned to the content stage and the three hosts/grok-bot/ products were regenerated. No
re-pin, tag, publish, install, or CHANGELOG section was made.

Evidence (reused because it matches the candidate's bytes): /tmp/kpr-i257-view-delivery.md,
/tmp/kpr-i257-watch.log (16 tests OK), /tmp/kpr-i257-follow.log (12 tests OK),
/tmp/kpr-i257-validate.log (validate.sh exit 1). `render-skills.py --check` PASS before and
after the commit.

## Known failures or unverified scope

- `./scripts/validate.sh` exits 1. Its only failure is
  `test-issue-162-upgrade-safety.py::test_release_note_rule_and_no_rebind_wording`, which
  expects `## Unreleased` in CHANGELOG.md. It fails identically on the unmodified base
  eb7f5b17. The owner directed that neither the test nor the CHANGELOG be changed in this run.
  The final validation record therefore states `verdict: fail` for that exact command.
- Live per-platform ACP smoke tests were not run; only the mock-agent contract tests ran.
- Running seats keep their old holder and emit the new fields only after a restart.

## Validation

classification: final_validation_failed
green: false
mode: final-validation

.cache/final-validation.md does not record `verdict: pass` (column 0) — the agent's own validation did not pass (found verdict: fail)

.cache/final-validation.md is present but does not record `verdict: pass` (column 0). The agent's own validation did not pass — remediate and re-record, or fix the failing checks before finalize.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/acp-watch/list-view.md
- docs/api.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- templates/grok-bot/accepted-revision.json
- tests/contract/fixtures/kaola-acp-view-1.sample.json
- tests/contract/test-acp-follow-contract.py
- tests/contract/test-acp-watch-contract.py

## Follow-Up Items

- filed: #258 (P2), "validate.sh fails on main: test-issue-162 requires a '## Unreleased'
  CHANGELOG heading that v0.9.0 release prep removed". Confirmed open with a non-empty body
  (1879 chars).

## Readiness

Ready for archive and merge sink. Closure decision: close #257 on the verified merge.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-reverify-2026-10-01.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-257/.cache/final-validation.md
- kaola-workflow/archive/issue-257/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-257/finalization-summary.md
- kaola-workflow/archive/issue-257/mission-ledger.jsonl
- kaola-workflow/archive/issue-257/workflow-state.md
