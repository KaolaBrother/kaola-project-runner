# Finalization Summary — bundle-116

## Delivered
The ZCode adapter's key-scoped output-limit scan (`OUTPUT_LIMIT_REASON_KEYS`, #113) also reads `stopReason` / `stop_reason`, so a `turn.completed` carrying ZCode's ModelComplete field reports `max_tokens` instead of `end_turn`. Matching stays key-scoped: prose quoting `max_tokens` stays `end_turn`; an explicit cancel still reports `cancelled`.

## Files Changed
- scripts/kaola-zcode-acp.py (keys added)
- skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py (render --write, byte-identical)
- tests/contract/fake-zcode-app-server.py (scenarios completed_stop_{camel,snake,prose,cancel})
- tests/contract/test-zcode-acp-contract.py (three contract tests)
- CHANGELOG.md (## Unreleased entry, adjacent to #115's)

## Test Coverage
`test_completed_stop_reason_key_reports_max_tokens` (camel + snake subtests; failed pre-fix with 'end_turn' != 'max_tokens'), `test_completed_prose_quoting_the_token_stays_end_turn`, `test_cancel_still_wins_over_a_completed_stop_reason`.

## Validation
- Candidate 6a1eca6 rebased onto origin/main f2b3bc1 → f924ca8 (one CHANGELOG ## Unreleased conflict; kept both #115 and #116 bullets).
- `./scripts/render-skills.py --check` → PASS on f924ca8.
- `./scripts/validate.sh` plain run on f924ca8 (post-#115 scrub removed the six inherited Host KAOLA_* names) → exit 0, 0 failed, sweep residual_pids []. Log: validate-f924ca8.log.
- Host acceptance: self-verification passed (three new tests pass; only failure was the known pre-#115 env leak, resolved by the rebase). Fable final review: PASS (byte-identical generated copy, discriminating tests, no scope creep, accurate CHANGELOG).
- Record: .cache/final-validation.md, verdict pass, validated_candidate_hash 4d4203d814fc33340db991f4714ed5453c2c5d9b3ccc0178d2b5df8313de5bfa.
- Pre-rebase evidence kept: kpr-116-validate-inherited.log (exit 1, known #115 cases only), kpr-116-validate-stripped.log (exit 0).

## Changed Paths
- CHANGELOG.md
- scripts/kaola-zcode-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-zcode-acp.py
- tests/contract/fake-zcode-app-server.py
- tests/contract/test-zcode-acp-contract.py

## Issue walk
- "finish-reason key set omits stopReason" → keys added; camel subtest.
- snake_case variant → snake subtest.
- "must not regress key-scoped matching / cancel" → prose and cancel tests.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
None.

## Status
READY — close #116.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-116/.cache/doc-docking.md
- kaola-workflow/archive/bundle-116/.cache/final-validation.md
- kaola-workflow/archive/bundle-116/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-116/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-116/finalization-summary.md
- kaola-workflow/archive/bundle-116/mission-list.md
- kaola-workflow/archive/bundle-116/workflow-state.md
