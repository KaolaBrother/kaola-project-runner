# Finalization summary — issue 268

## Delivered

Four-fact selection continuity against silent model/effort drift on bare ACP continuation,
delivered through the issue-264 tree (no commits on this branch; tip stays at `dad228e4`):
`recorded_selection` / `applied_configuration` / fresh effective readback (`acp-config-echo`) /
`prior_applied_selection` history, with `prior_settings_preserved` true only on proven equal
readback, per-axis native readback, a `most_recent_live` slot owning holder identity and time, and
no intention-guessing (explicit flags update the baseline only on verified readback). Boundary
fixes A/B keep preserved-settings claims only on proven continuity, with the live native sample
`i268-b-delta` binding through dispatch index locators. Contract: 26 tests in
`tests/contract/test-issue-268-selection-continuity.py`.

## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "e245d6e6625b6128aafde1b7fcdd77a7d63072a2e1e1d7765f128e938bf0ce85" != current code-tree hash "bc4d5a0afc9c5c3130e30359a831528babbf565cd92fc146a1599f4dd770cfbe" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-acp.py
- scripts/validate.sh
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-268-selection-continuity.py

## Known limitations

Legacy sessions without continuity records keep their no-continuity semantics; cross-platform
automatic recognition of drift is not claimed.

## Follow-Up Items

None filed.

## Readiness

Accepted (root's A/B boundary rounds concluded; final integrated acceptance rode the 264
candidate). Issue closes through the issue-264 merge sink (recorded set
259,263,264,265,266,267,268). No separate sink; this branch has no commits of its own.

## Finalize Findings

### residue_unattributed

The `chore: finalize` commit did NOT carry the paths below. Worktree paths whose directories this run never committed are left in the worktree. Main-checkout paths this run's HEAD does not contain were not copied. Nothing was committed, deleted, reverted or relocated. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths not attributed to this run:

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

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

