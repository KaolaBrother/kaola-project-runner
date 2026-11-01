# Issue 452 finalization summary

## Delivered

Candidate: c1176059664fe8ce7ba194f2b3e814797ce1040b. Host acceptance: PASS, explicitly provided in conversation for this candidate and its evidence.

The Host carrier wakes with the native Skill entry, structured event identity and cursors, the current state source locator and an event-scoped instruction to consume original receipts and obtain applicable facts. It no longer injects the full state body or commands an unconditional full pass. Missing and unusable sources remain explicit diagnostics; absent authority remains unknown. Source validity, fingerprint and attention metadata, coalescing, admission refusal retention, delivery markers, overflow recovery, and startup and compaction duties remain in their existing paths. No new state store or network mechanism was introduced.

Evidence: offline focused suites passed: heartbeat 24/24 (656 checks), role carrier 9/9 including source and admission refusal, cwd carrier 6/6, permission wake 5/5. The heartbeat and cwd suites ran against identical implementation bytes before test-only assertion/description changes; the updated role suite passed after those changes. Render write and check passed. `--require-pinned` refused the unsaveable delta (exit 1), preserving the release gate. Against v0.9.39, the operator diff includes scripts/kaola-acp-holder.py; CHANGELOG records Seats: restart required. See `.cache/final-validation.md` for recorded commands and candidate tree hash. No live adoption or performance measurement is claimed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-issue-388-role-carrier.py
- tests/contract/test-issue-393-cwd-carrier.py
- tests/contract/test-zcode-heartbeat-contract.py

## Follow-Up Items

No run-discovered defects requiring a new issue. KPM integration and adoption remain owned by the existing KPM mirror; this source repair does not establish live adoption.

## Readiness

Host accepted the exact candidate. Ready to merge, close issue 452, and archive. No holds lifted.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-452/.cache/final-validation.md
- kaola-workflow/archive/issue-452/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-452/finalization-summary.md
- kaola-workflow/archive/issue-452/mission-ledger.jsonl
- kaola-workflow/archive/issue-452/workflow-state.md
