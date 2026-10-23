## Validation

classification: final_validation_stale
green: false
mode: final-validation

recorded validated_candidate_hash "bc0dd1cd6765d562eb72f1c96df87c17c6cc8d1646931aa1b58c18a0b6902527" != current code-tree hash "22e3bff2b06db38f8f17481b2293573f4493ee3aa53a3a9739b0636b45f1b061" — a relevant source/test/test-consumed file changed after the recorded validation; re-run the validation command and re-record final-validation.md with a fresh hash

A relevant source/test/test-consumed file changed after validation — or the record was written from a different checkout than this one. Re-run the validation command, then re-record with `kaola-workflow-validation-runner.js record --project <project> --verdict pass --command "<the validation command you ran>"`, invoked from the working tree you validated (the gate hashes the tree its own shell is in, and a linked worktree and main differ until the branch merges); never hand-patch the hash.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- finalization-summary.md
- tests/contract/test-issue-306-bytecode-payload.py

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-407/.cache/final-validation.md
- kaola-workflow/archive/issue-407/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-407/finalization-summary.md
- kaola-workflow/archive/issue-407/mission-ledger.jsonl
- kaola-workflow/archive/issue-407/workflow-state.md
