# Finalization Summary — issue-422

## Delivered

A declared test-lane receipt fails closed when stdout and stderr are both empty. Exit 0 is recorded and is not proof the suite ran.

- Gate: `certify_test_lane_receipt` in `scripts/kaola-acp.py`, called from `_emit_receipt` before the recovery stamp. Refusal code `noop-test-lane`. `error.evidence` records `test_lane`, `exit_code`, `stdout_sha256`, `stderr_sha256`, `duration_ms`, `min_duration_ms`, and `checks`.
- Route: `noop-test-lane` in `scripts/kaola-recovery-routes.py`.
- Floor: 50 ms (`TEST_LANE_MIN_DURATION_MS`), applied only together with empty output. The noop receipts were 7–9 ms with the empty digest. A one-test lane on this machine was about 28–44 ms and still produced output, so a floor above the 7–9 ms band would refuse a fast real lane. Empty output refuses at any duration. A duration under 50 ms is recorded as `sub-floor-duration` on that empty receipt. A lane that produced output certifies at any speed.
- Contract suite `tests/contract/test-issue-422-noop-receipt-guard.py`, 11 tests, registered in `python_suites_all` and `python_suites_b`.
- Docs: `docs/api.md` section "Test-lane receipt certification (Issue #422)".

## Candidate

`workflow/issue-422` @ `7c2a41e0c62fdf036b6261af115282befdb75e49` (implementation `04399a2c7a756e20d4a136a826c576f0f619f1a9`, base `a25267c1`).

## Acceptance

Host verdict ACCEPTED. Independent check on `04399a2c` + `7c2a41e0`: operator restart-set diff empty, golden and `.kaola` untouched, render --check PASS, `test-issue-422-noop-receipt-guard` 11/11, lane-integrity 264 green. Gate design accepted: empty stdout and stderr refuse at any duration; a sub-50 ms duration records `sub-floor-duration` on the empty receipt; output-producing lanes certify regardless of speed; exit 0 is recorded and is not proof; the refusal is typed and carries evidence.

## Evidence

- Recorded validation: `.cache/final-validation.md`.
- Docking record: `kaola-workflow/issue-422/doc-docking.md` (candidate `04399a2c7a756e20d4a136a826c576f0f619f1a9`).

## Known failures or unverified scope

- Whole inventory was not run. Focused suites only.
- No live seat re-measurement of a consumer test lane.
- `Seats: restart not required`. `scripts/kaola-acp.py` and `scripts/kaola-recovery-routes.py` are outside the operator restart set.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- docs/api.md
- scripts/kaola-acp.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
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
- skills/hermes-kaola-project-runner/scripts/kaola-acp.py
- skills/hermes-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
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
- tests/contract/test-issue-422-noop-receipt-guard.py

## Follow-Up Items

- None filed.

## Final readiness

Ready: accepted, all missions done, merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-422/.cache/final-validation.md
- kaola-workflow/archive/issue-422/doc-docking.md
- kaola-workflow/archive/issue-422/finalization-summary.md
- kaola-workflow/archive/issue-422/mission-ledger.jsonl
- kaola-workflow/archive/issue-422/workflow-state.md
