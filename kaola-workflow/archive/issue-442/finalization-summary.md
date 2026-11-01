# Finalization summary — issue 442

## Delivered

One sandboxed DSH 0.2.1-rc.5 ACP validation round, with NOT-GREEN adoption verdict. Host accepted this evidence-only deliverable on 2026-11-01. Recommend retaining the rc.2 pin in platforms/dsh.yaml; no pin, product code, fleet install or PATH change was made. Documentation impact: none.

## Candidate and evidence

Candidate branch workflow/issue-442, based on c537c74e; comparison baseline Accepted R 3d67cf6976381e75ea6a73ee62f88df73c43d5a8. See evidence/verdict.md and bounded Runner receipts in evidence/. Sandboxed rc.5 initialized as deepseek-harness-acp/0.0.1, protocol 1. Start, observe, send, capture and exact-stop were exercised; send ended turn_failed because the selected deepseek-official route lacked an API key. Stock and copied-patch opencode-go model selection returned -32602. Successful model response, credentialed operator route, list/resume and complete protocol conformance remain unverified. Copied patch rejection does not establish its cause.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

none outside the kaola-workflow/ run-state band.

## Follow-Up Items

A credentialed operator-declared opencode-go round needs owner-provided DeepSeek/OpenCode-Go credentials. Supplying credentials is an owner decision, not a code gap. No new defect issue is asserted by this result.

## Readiness

Host acceptance: PASS for the NOT-GREEN verdict and evidence. Ready for merge sink and closure as explicitly authorized; no adoption is approved.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-442/.cache/final-validation.md
- kaola-workflow/archive/issue-442/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-442/evidence/capture.json
- kaola-workflow/archive/issue-442/evidence/observe.json
- kaola-workflow/archive/issue-442/evidence/send.json
- kaola-workflow/archive/issue-442/evidence/start-direct.json
- kaola-workflow/archive/issue-442/evidence/start-fallback.json
- kaola-workflow/archive/issue-442/evidence/start-route.json
- kaola-workflow/archive/issue-442/evidence/start-sandbox.json
- kaola-workflow/archive/issue-442/evidence/start.json
- kaola-workflow/archive/issue-442/evidence/status-after-stop.json
- kaola-workflow/archive/issue-442/evidence/stop.json
- kaola-workflow/archive/issue-442/evidence/verdict.md
- kaola-workflow/archive/issue-442/finalization-summary.md
- kaola-workflow/archive/issue-442/mission-ledger.jsonl
- kaola-workflow/archive/issue-442/workflow-state.md
