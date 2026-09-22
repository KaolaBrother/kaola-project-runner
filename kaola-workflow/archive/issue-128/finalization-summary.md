# Finalization Summary — issue-128

## Delivered
#128: both out-of-gate contract suites green and mounted in `scripts/validate.sh`. All 21 reds were stale fixtures/expectations (zero product regression, zero assertion weakened):
- test-lifecycle-contract.py (9): inventory lacked `references/steering.md` (#65); also added `steering.md.tmpl` and the `dsh` roster entry (coverage 9→10 workers).
- test-model-policy.sh kimi-cli (6): fixture default predated #111 (now Kimi K3 Max / kimi-code/k3).
- test-model-policy.sh opencode (5): V2 adapter (#112) carries caller model via OPENCODE_CONFIG_CONTENT; the fake now reads it; new check `test_opencode_user_model_rides_config_not_argv`. Host-accepted note: real opencode 2.0.11 ignores that env (upstream #50236); the fixture covers the Runner channel + verified=true evidence path, not live model switching.
- test-model-policy.sh droid (1): fake `read -r` word-split a settings model with spaces → `\x1f` separator.
- validate.sh: lifecycle in lane A; model-policy (~300 s, tmux) as a concurrent lane C; `.sh` suites run via bash in an explicit branch (keeps #101's pinned python3 line); #83 harness defines `python_suites_c=()`.
Dated historical frames untouched.

## Files Changed
CHANGELOG.md; scripts/validate.sh; tests/contract/test-issue-83-lane-failure-visibility.py; tests/contract/test-lifecycle-contract.py; tests/contract/test-model-policy.sh (single commit 3a2c983, +64/−6).

## Test Coverage
Automated: validate.sh rc=0 564 s at 3a2c983 (includes both newly mounted suites PASS; evidence/validate.log); base 8819bc9 rc=0 583 s. Standalone: model-policy rc=0 302 s; lifecycle PASS. Baseline reds: evidence/model-policy-baseline.log (12), evidence/lifecycle-baseline.log (9). Two intermediate candidate validates under external load (syspolicyd ~75% CPU + a foreign cargo build) had timeout reds in untouched ACP suites; each re-run standalone green; ruled environmental by Host. Manual/UAT: none required (test-only + gate wiring). Live tmux smoke per platform: not applicable (no transport/adapter change).

## Acceptance
Host verdict PASS on 3a2c983 (2026-09-22): lane C mounting accepted over serial (+300 s steady cost); opencode verified=true channel coverage accepted.

## Issue walk (#128)
- "test-model-policy.sh 12 failures" → each classified and fixed; suite PASS in validate.
- "test-lifecycle-contract.py 9 failures" → fixed; PASS in validate.
- "neither in validate.sh" → both mounted (lanes A, C).
- "fix or retire each stale expectation, then decide validate.sh membership" → fixed, none retired; decision = mount, Host-accepted.
- The other 21 of the 23 out-of-gate files: not claimed by #128's remedy; no follow-up filed by this run (not measured).

## Documentation Docking
DOCKED — .cache/doc-docking.md.

## Follow-Up Items
None filed. (Load sensitivity of ACP timing suites under heavy external load is an environment observation, recorded in memory, not a measured defect of this change.)

## Validation
validation: chains_green (consumer repo: agent-recorded .cache/final-validation.md, verdict pass, validated_candidate_hash 58b898bde57d2b2d07cba94c9f68425153de76ce7dd5477353fa02031ddc174a, tree 3a2c983). run-chains: chains_config_missing (no test:kaola-workflow:* — expected for a consumer).

## Changed Paths
- scripts/validate.sh
- tests/contract/test-issue-83-lane-failure-visibility.py
- tests/contract/test-lifecycle-contract.py
- tests/contract/test-model-policy.sh
(transaction list is source-scoped; CHANGELOG.md is also in 3a2c983)

## Status
READY — accepted, validated, docked.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-128/.cache/doc-docking.md
- kaola-workflow/archive/issue-128/.cache/final-validation.md
- kaola-workflow/archive/issue-128/.cache/mirror-digest.json
- kaola-workflow/archive/issue-128/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-128/finalization-summary.md
- kaola-workflow/archive/issue-128/mission-list.md
- kaola-workflow/archive/issue-128/workflow-state.md
