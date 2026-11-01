# Issue 439 finalization

## Delivered

Candidate 434d9348 fixes DROID_BIN selection for native ACP, regenerates Skills and adds a contract test and CHANGELOG entry. Host acceptance PASS explicitly covers the fix and the NOT GREEN convergence verdict. Droid verified pin remains at R (CLI 0.225.1, protocol 1); no fleet installation or pin adoption.

Evidence: droid-validation.md and transient `/tmp/kpr-439-droid/fixed-*.json` and `steer.json`. The native candidate self-identified as 1.1.0; default and exact core/max turns and native-ID resume passed on the tested account. Installed 0.241.1 is a separate control. On 1.1.0 busy native steer was rejected -32600 and not consumed; original turn completed and exact stops reported no residual PIDs. Other accounts, 0.249.0 Studio, 0.251.0 and after-turn delivery remain unverified. Generated Skill direct invocation was refused due to installed build skew; live proof used the worktree source entry without modifying installations.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/hermes-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-droid-acp-contract.py

## Follow-Up Items

Filed [#446](https://github.com/KaolaBrother/kaola-project-runner/issues/446), P2, confirmed open with nonempty body: assess/correct the 1.1.0 busy-turn steering regression or obtain explicit evidence-based acceptance before convergence. Correction and verdict recorded in [#439 comment](https://github.com/KaolaBrother/kaola-project-runner/issues/439#issuecomment-6552811901).

## Readiness

Host accepted the bounded fix and NOT GREEN verdict on 2026-11-01; ready to merge, close and archive. Convergence is not accepted.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-439/.cache/final-validation.md
- kaola-workflow/archive/issue-439/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-439/droid-validation.md
- kaola-workflow/archive/issue-439/finalization-summary.md
- kaola-workflow/archive/issue-439/mission-ledger.jsonl
- kaola-workflow/archive/issue-439/workflow-state.md
