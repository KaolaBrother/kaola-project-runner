# Finalization Summary — issue 459

## Delivered

Release v0.9.41. Host acceptance: PASS.

- Tag `v0.9.41` (lightweight) at content commit R `b1253f21cefc3d45170b3f5d8bdeb7b127738eb3`.
- Pin commit P `2e05f4ceedef1b5416cfef9b664089c533086021` names R with release `v0.9.41`. `hosts/grok-bot/bridge.json` is `saveable: true`. The delta from R is the four pin files.
- Section line: `Seats: restart required`. The operator diff from `v0.9.40` to R is non-empty: `scripts/kaola-acp-holder.py`, `scripts/kaola-acp-paths.py`, `scripts/kaola-dispatch.py` and `scripts/kaola-record-contract.py`. `scripts/kaola-acp.py` also changed (#458) and is outside the operator path list.
- Wrapper pins already set stay in their manifests (Codex `2.5.0`, Claude bridge `6c20f28`, ZCode `80aa4e2c`). Empty `acp_wrapper_pin` stays intentional for antigravity, cursor-cli, devin, droid, dsh, grok, hermes, kimi-cli, and opencode. No platform is newly unpinned. No release step refused because issue #457 is open.

## Candidate

`workflow/issue-459` @ `2e05f4ceedef1b5416cfef9b664089c533086021` (content R `b1253f21cefc3d45170b3f5d8bdeb7b127738eb3`, base `1eb54f71ca4f70bd0201c8279eb5adbce30f1eba`).

## Acceptance

Host verdict PASS for tag at R `b1253f21`, bridge-only pin commit P `2e05f4ce` saveable naming R, the measured `Seats: restart required` line, the `--require-pinned` boundary, no SOP refusal on open #457, and pin verification complete.

## Evidence

- Recorded validation: `.cache/final-validation.md`.
- `python3 ./scripts/render-skills.py --check` PASS at content commit R before the pin.
- `python3 ./scripts/render-skills.py --check --require-pinned` refused the content stage (`pin: stage is content; --require-pinned demands a pinned, verified bridge`), then PASS at P.
- `python3 ./scripts/kaola-grok-bot-verify.py hosts/grok-bot --repo . --require-pinned` PASS at P.

## Known Failures and Unverified Scope

The full inventory was not run. Three-Mac Accepted install and Seats drain-restart stay with the Delegator after the tag. No seat restart in this run.

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

- Not filed. This release folds the accepted #458 change into v0.9.41 and pins the bridge. No new defect was found.

## Readiness

Host accepted `2e05f4ceedef1b5416cfef9b664089c533086021`. Ready for archive and the merge sink. The issue closes. The close note names the tag, R, P, the Seats line, and the pin verification.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-459/.cache/final-validation.md
- kaola-workflow/archive/issue-459/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-459/finalization-summary.md
- kaola-workflow/archive/issue-459/mission-ledger.jsonl
- kaola-workflow/archive/issue-459/workflow-state.md
