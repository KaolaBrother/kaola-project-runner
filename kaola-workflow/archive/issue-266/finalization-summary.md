# Finalization summary — issue 266

## Delivered

Outside-caller Host/seat holder launching for Grok Bot on `workflow/issue-266` (tip `cfa491dd`,
fully contained in the cycle candidate `e1ff6d486c16d89c65473ac19ff316811abad3ac`): the shared
macOS launchd broker launcher `scripts/kaola-launchd-broker.py` with the env allowlist security
boundary (PASS_ALWAYS/PASS_PROXY/PASS_KAOLA) never disabled, real refusal/custody proofs,
attempt-bound rollback and cleanup, truthful partial/custody outcomes, native-agent custody and
exact-identity evidence, and cleanup that keeps unresolved failed-attempt effects. Contract
coverage: `tests/contract/test-issue-266-launch-broker.py` and
`test-issue-266-launch-broker-composed.py` (real launchd launches, holder pids re-parented to
launchd, exact stop, empty residual pid sets).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- scripts/kaola-launchd-broker.py
- tests/contract/test-issue-266-launch-broker-composed.py
- tests/contract/test-issue-266-launch-broker.py

## Known limitations

macOS launchd only; Linux/other-OS launch paths, GUI/TCC, logout/reboot and parent-death
combinations remain unverified outside the tested classes.

## Follow-Up Items

None filed.

## Readiness

Accepted after three Host-review repair rounds; issue closes through the issue-264 merge sink
(recorded set 259,263,264,265,266,267,268). No separate sink for this branch.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

