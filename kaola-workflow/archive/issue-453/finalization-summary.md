# Issue #453 finalization

## Delivered

Candidate: 1f62c1a8c228cc1a125cb1a31d1ea2c2da14f9c3. An unavailable selected Sideagent binding or recipe records the owed recovery input, reason and evidence with existing rearm and coalescing, without staging an unactionable Host node wake. The record callback follows the existing empty-queue path. Genuine node failures and worker returns retain attention delivery.

New returned-input instructions tell the Host to read original receipts and current holds and grants, retain the blocker and its owner, and repair or request a bounded check only when permitted and conditions have changed. Existing stored rows are not migrated; their older wording remains separate under the existing coalescing contract. KPM #1024 is a separate consumer-side rule; this delivery does not establish consumer adoption.

Host acceptance: PASS explicitly given for candidate 1f62c1a8, including the two-recovery-sequence no-node-event regression, focused results, restart determination and no-migration limitation. No holds were lifted and no live adoption was performed.

Evidence: `./scripts/render-skills.py --write` and `--check` passed; `--check --require-pinned` refused the unsaveable delta. `PATH=/opt/homebrew/bin:$PATH /opt/homebrew/bin/bash ./scripts/validate.sh --suite test-issue-324-wake-fixes.py --suite test-issue-421-retire-recovery.py --suite test-issue-255-lifecycle-state.py` produced 10/10 and 45/45 passes, and one obsolete expectation failure in #255; after correcting that test expectation, `PATH=/opt/homebrew/bin:$PATH /opt/homebrew/bin/bash ./scripts/validate.sh --suite test-issue-255-lifecycle-state.py` passed 178/178. `/Users/ylpromax5/miniforge3/bin/python3.13 tests/contract/test-issue-437-sideagent-hb-skew.py RearmTests` passed. Operator diff against aad898369c7794ee7d095ee335d9f138be61e54e includes holder and dispatch scripts; CHANGELOG states Seats: restart required.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
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
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-324-wake-fixes.py
- tests/contract/test-issue-421-retire-recovery.py

## Follow-Up Items

No new follow-up filed. KPM #1024 remains separate. No live integration or consumer adoption is claimed.

## Readiness

Host accepted; ready for merge sink, issue closure and archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-453/.cache/final-validation.md
- kaola-workflow/archive/issue-453/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-453/finalization-summary.md
- kaola-workflow/archive/issue-453/mission-ledger.jsonl
- kaola-workflow/archive/issue-453/workflow-state.md
