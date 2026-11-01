# Finalization summary: issue 440

## Delivered

Candidate 630d9221a71f2a41e93411551db70ba1d1f0f647, accepted by Host (PASS). The sink rebase onto current main conflicted only in CHANGELOG.md with the #441 and #444 unreleased bullets. That conflict was resolved by keeping those bullets and the #440 bullet. Rebased commit d0a182aec68aa700b7f4c0fadd8d5ca06b910c33. Kimi CLI native ACP pin moves from cli=2.2.0;protocol=1 to cli=2.4.1;protocol=1. Private @moonshot-ai/acp-server 0.0.2 is byte-identical at 2.2.0 and 2.4.1 and is not a pin. There is no public adapter and no declared CLI range. acp_wrapper_pin stays empty. Client capabilities stay terminal:false,fs:false.

Quirks record the measured 2.4.1 behavior: prompt failures session.stale and session.occupied are JSON-RPC -32600 with data.code; the stale text says to close and reopen and KPR does not replay the prompt. A second client's resume or load while a live client holds the session is resume-failed, JSON-RPC -32603 Internal error, with data.details saying the session is in use by another Kimi Code CLI instance. KPR does not evict, take over the lock, or set KIMI_CODE_SESSION_LOCK=0. After the holder exits, resume of the same native id succeeds.

scripts/kaola-acp-holder.py summary_from_acp copies a non-empty string data.code onto engine_code and keeps the numeric JSON-RPC code. It does not retry or evict. CHANGELOG Unreleased states Seats: restart required.

Sandbox receipts (direct backend, isolated KIMI_CODE_HOME, absolute 2.4.1 command, fleet kimi left at 2.2.0): start, observe, send, capture, and exact-stop; occupied resume refused at -32603 with no eviction; post-release resume of the same id; stale prompt -32600 session.stale with no replay; loader prompt and reopen both completed; exact-stops left residual pids empty.

Evidence: kaola-workflow/issue-440/evidence/upstream-verdict.md and kaola-workflow/issue-440/evidence/receipts.md.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- platforms/kimi-cli.yaml
- scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/references/acp.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/platform.yaml
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- tests/contract/test-issue-335-kimi-provider-error.py

## Follow-Up Items

None. No new defect was filed.

## Unverified

Prompt-path session.occupied was source-mapped and not hit live. Cancellation, permission, and compact were not exercised on 2.4.1. The README host-capability row stays the earlier Kimi CLI 2.1.1 measurement. Fleet install was not performed.

## Readiness

Accepted by Host. Ready for merge sink, issue close, and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-440/.cache/final-validation.md
- kaola-workflow/archive/issue-440/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-440/evidence/capture-owner.err
- kaola-workflow/archive/issue-440/evidence/capture-owner.json
- kaola-workflow/archive/issue-440/evidence/capture.err
- kaola-workflow/archive/issue-440/evidence/capture.json
- kaola-workflow/archive/issue-440/evidence/observe-after-occupied.err
- kaola-workflow/archive/issue-440/evidence/observe-after-occupied.json
- kaola-workflow/archive/issue-440/evidence/observe.err
- kaola-workflow/archive/issue-440/evidence/observe.json
- kaola-workflow/archive/issue-440/evidence/preflight.err
- kaola-workflow/archive/issue-440/evidence/preflight.json
- kaola-workflow/archive/issue-440/evidence/receipts.md
- kaola-workflow/archive/issue-440/evidence/send-alpha.err
- kaola-workflow/archive/issue-440/evidence/send-alpha.json
- kaola-workflow/archive/issue-440/evidence/send-beta.err
- kaola-workflow/archive/issue-440/evidence/send-beta.json
- kaola-workflow/archive/issue-440/evidence/send-reopened.err
- kaola-workflow/archive/issue-440/evidence/send-reopened.json
- kaola-workflow/archive/issue-440/evidence/send-sleep.err
- kaola-workflow/archive/issue-440/evidence/send-sleep.json
- kaola-workflow/archive/issue-440/evidence/send.err
- kaola-workflow/archive/issue-440/evidence/send.json
- kaola-workflow/archive/issue-440/evidence/start-direct.err
- kaola-workflow/archive/issue-440/evidence/start-direct.json
- kaola-workflow/archive/issue-440/evidence/start-occupied.err
- kaola-workflow/archive/issue-440/evidence/start-occupied.json
- kaola-workflow/archive/issue-440/evidence/start-reopen.err
- kaola-workflow/archive/issue-440/evidence/start-reopen.json
- kaola-workflow/archive/issue-440/evidence/start-stale-loader.err
- kaola-workflow/archive/issue-440/evidence/start-stale-loader.json
- kaola-workflow/archive/issue-440/evidence/start.err
- kaola-workflow/archive/issue-440/evidence/start.json
- kaola-workflow/archive/issue-440/evidence/stop-kpr440e.err
- kaola-workflow/archive/issue-440/evidence/stop-kpr440e.json
- kaola-workflow/archive/issue-440/evidence/stop-kpr440f.err
- kaola-workflow/archive/issue-440/evidence/stop-kpr440f.json
- kaola-workflow/archive/issue-440/evidence/stop-launchd.err
- kaola-workflow/archive/issue-440/evidence/stop-launchd.json
- kaola-workflow/archive/issue-440/evidence/stop-occupied-client.err
- kaola-workflow/archive/issue-440/evidence/stop-occupied-client.json
- kaola-workflow/archive/issue-440/evidence/stop-stale-client.err
- kaola-workflow/archive/issue-440/evidence/stop-stale-client.json
- kaola-workflow/archive/issue-440/evidence/upstream-verdict.md
- kaola-workflow/archive/issue-440/finalization-summary.md
- kaola-workflow/archive/issue-440/mission-ledger.jsonl
- kaola-workflow/archive/issue-440/workflow-state.md
