# Finalization summary — issue 447

## Delivered

Host acceptance: PASS, explicitly granted after GREEN credentialed ACP verification. Candidate `c37edd1e68af958b372500ca93907995a28d13d7` records DSH 0.2.1-rc.5 with agent deepseek-harness-acp/0.0.1, protocol 1 and the operator-declared OpenCode Go route condition. The existing API-key path was used under the owner decision owner-dsh-via-opencode-creds-20261101; no separate credential request or account change. The earlier #442 owner-provided-credentials framing is corrected by that decision.

Sandboxed acquisition and isolated home, start, observe, credentialed send, capture and exact stop are recorded in `evidence/`; the response was KPR447_OK and stop left no residual processes. The isolated credential environment copy was removed after the run. No fleet installation or persistent PATH change. Against R `3d67cf6976381e75ea6a73ee62f88df73c43d5a8`, agent identity, protocol and route condition match. The rc.5 pin and generated output, CHANGELOG Seats line, and stale assertion update are included.

Untested: list/resume, other ACP methods and providers, and complete protocol conformance. The lifecycle result does not claim those paths.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- platforms/dsh.yaml
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- tests/contract/test-issue-98-dsh-acp.py

## Follow-Up Items

None identified by this scoped run. The untested paths above remain outside its acceptance.

## Readiness

Host accepted the candidate and authorized merge, issue closure and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-447/.cache/final-validation.md
- kaola-workflow/archive/issue-447/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-447/evidence/bootstrap-stop.json
- kaola-workflow/archive/issue-447/evidence/bootstrap.json
- kaola-workflow/archive/issue-447/evidence/bootstrap2.json
- kaola-workflow/archive/issue-447/evidence/capture.json
- kaola-workflow/archive/issue-447/evidence/observe.json
- kaola-workflow/archive/issue-447/evidence/send.json
- kaola-workflow/archive/issue-447/evidence/start.json
- kaola-workflow/archive/issue-447/evidence/status.json
- kaola-workflow/archive/issue-447/evidence/stop.json
- kaola-workflow/archive/issue-447/evidence/verdict.md
- kaola-workflow/archive/issue-447/evidence/version.txt
- kaola-workflow/archive/issue-447/finalization-summary.md
- kaola-workflow/archive/issue-447/mission-ledger.jsonl
- kaola-workflow/archive/issue-447/workflow-state.md
