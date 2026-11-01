# Finalization Summary — issue 449

## Delivered

Release v0.9.38. Host acceptance: PASS.

- Tag `v0.9.38` (lightweight) at content commit R `35824954ee4d4c5ce323ee6d2e29e9fa22d975a9`.
- Pin commit P `ef8d197d95af229c9092472b923c1561b62e6839` names R with release `v0.9.38`. `hosts/grok-bot/bridge.json` is `saveable: true`. The delta from R is the four pin files.
- Section line: `Seats: restart required`. The operator diff from `v0.9.37` to R is non-empty: `platforms/antigravity.yaml`, `platforms/claude-code.yaml`, `platforms/dsh.yaml`, `platforms/grok.yaml`, `platforms/kimi-cli.yaml`, `scripts/kaola-acp-holder.py`, `scripts/kaola-dispatch.py`.
- Wrapper pins already set stay in their manifests (Codex `2.5.0`, Claude bridge `6c20f28`, ZCode `80aa4e2c`). Empty `acp_wrapper_pin` stays intentional for antigravity, cursor-cli, devin, droid, dsh, grok, hermes, kimi-cli, and opencode.

## Candidate

`workflow/issue-449` @ `ef8d197d95af229c9092472b923c1561b62e6839` (content R `35824954ee4d4c5ce323ee6d2e29e9fa22d975a9`, base `203ae38f3ef802e3d4d72cb0f738b24b36db5461`).

## Acceptance

Host verdict PASS for R `35824954` and pin commit P `ef8d197d`, the measured operator diff, the wrapper-pin record, render plus `--require-pinned`, and the green spot suites.

## Evidence

- Recorded validation: `.cache/final-validation.md`.
- `python3 ./scripts/render-skills.py --check --require-pinned` PASS at P.
- `python3 ./scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo . --require-pinned` PASS at P.
- `./scripts/validate.sh --suite test-issue-335-kimi-provider-error.py`: Ran 7 OK.
- `./scripts/validate.sh --suite test-issue-255-lifecycle-state.py`: Ran 178 OK.
- `./scripts/validate.sh --suite test-droid-acp-contract.py`: Ran 23 OK.
- `./scripts/validate.sh --suite test-issue-168-drift-enumeration.py`: Ran 5 OK.
- `tests/contract/test-issue-437-sideagent-hb-skew.py` is not an inventory suite. A direct run on P was Ran 2 OK.

## Known Failures and Unverified Scope

The full inventory was not run. Three-Mac installs stay with the Delegator after the tag. No seat restart in this run.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- templates/grok-bot/accepted-revision.json

## Follow-Up Items

- Not filed. `tests/contract/test-issue-437-sideagent-hb-skew.py` is outside `python_suites_all`, so `validate.sh --suite` refuses it. The direct run on P passed (Ran 2). The holder latch for that change is inside `test-issue-255-lifecycle-state.py`, which passed (Ran 178). The file was already on main before this release. This run does not open a new issue.

## Readiness

Host accepted `ef8d197d95af229c9092472b923c1561b62e6839`. Ready for archive and the merge sink. The issue closes. The close note names the tag, R, P, the Seats line, and the pin verification.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-449/.cache/final-validation.md
- kaola-workflow/archive/issue-449/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-449/finalization-summary.md
- kaola-workflow/archive/issue-449/mission-ledger.jsonl
- kaola-workflow/archive/issue-449/workflow-state.md
