# Issue #431 finalization

## Delivered

Host accepted candidate `0e5c1c308dfbd5e38d553945478d6859b614719a`. Content merged into main as `6eeb4450385d5699333d994fac07258bf9b1db5c`, pushed and verified on origin/main. Host-only never-indexed settlement records verified anchors when supplied live rows are unique, stopped/dead and match; when a session is absent, all typed locators are required and the receipt says attested, never verified. Refusal preserves state bytes for missing or ambiguous anchors, foreign or indexed refs, invalid locators, active or mismatched sessions, and Sideagent use. No Workflow ledger is fabricated. #286 fixtures legally write review before planting legacy done on disk. CHANGELOG says Seats: restart required.

## Acceptance and evidence

Host independently accepted the final candidate and reported rerunning all ten suites; the HolderNodeMode direct-invocation timeout was reported reproduced on published main P, while the standard entry passed. This is the Host's accepted exception, not an assertion that the direct invocation passed. The worker's clean-HEAD standard subset run passed #255 176/176, #286 29/29, #292 5/5, #309 10/10, #412 31/31, #421 45/45, #425 26/26, #426 53/53, #427 21/21 and #431 9/9; its earlier #255 batch-wait timeout was followed by a full passing rerun. Evidence: `/tmp/kpr431-final-retry.log`, `/tmp/kpr431-final-head.log`, and issue comments. Merged main `./scripts/render-skills.py --check` passed, budgets OK. Consumer videos and Claude were not touched.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

none outside the kaola-workflow/ run-state band.

## Follow-Up Items

None identified within this run. Host accepted the direct-invocation timeout exception described above.

## Readiness

Accepted; publication verified. Close #431 and archive the complete ledger including prior failed attempts; sink to main.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-431/.cache/final-validation.md
- kaola-workflow/archive/issue-431/finalization-summary.md
- kaola-workflow/archive/issue-431/mission-ledger.jsonl
- kaola-workflow/archive/issue-431/workflow-state.md
