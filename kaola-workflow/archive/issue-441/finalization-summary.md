# Issue #441 finalization summary

## Delivered

- Require the current bound node holder and agent to be live, and check the checkpoint caller's ancestry against the recorded node agent. Copied environment IDs alone cannot establish origin (`caller-origin-unverified`).
- Consume each admitted batch once: reject a previously written or settled batch as `batch-consumed`; preserve the existing carrier receipt, prompt, identity and range checks.
- Stabilize the #255 build-skew test using the recorded node-started event, instead of sampling the transient starting phase; retain the count and cleared-latch checks.
- Document behavior and mark Seats: restart required in CHANGELOG. No fleet installation or seat restart was performed; rollout remains owner/Delegator-gated.

## Candidate and acceptance

Implementation commit: `eab3eab8175abef0d93debca01866351943e60bd`. Host acceptance: PASS, explicitly given after review of the native carrier path, refusal matrix, timing adjudication and test stabilization. Dispatch SHA-256 `96fdf53b9210f68d83486bd0e6324af80a6db51be5ab1ae9c4e52f06a2695a97` matches `native-proof.json`.

## Evidence and limitations

- `native-proof.json`: checkout-direct ZCode carrier started real Devin node `303f9c8dd8e16ee087866da3ae177666`, admitted batch `b-bf9b270a4cdc`, native candidate checkpoint `verified: true` through revision 3, settled and exact-stopped. Both isolated test sessions ended with no residual processes. A copied stopped-node ID and settled-batch replay was refused `batch-consumed` with state SHA-256 unchanged.
- Isolated refusal matrix: host `writer-refused`, anonymous `node-identity-required`, superseded node `binding-superseded`, fake batch `batch-unverified`; live sibling copied identity `caller-origin-unverified`.
- `PATH=/opt/homebrew/bin:/Users/ylpromax5/miniforge3/bin:/usr/bin:/bin ./scripts/validate.sh --suite test-issue-255-lifecycle-state.py`: PASS 178/178 on standalone retry (`/tmp/kpr441-stabilized-255-retry.log`). The prior run failed a separate next-recovery-batch timeout; that case passed individually on main and candidate. Prior candidate suite build-skew failures also occurred on main and were stabilized test-side. Preserve this history; no claim of universal timing freedom.
- Earlier affected subset: #168 5/5, #244 80/80, #349 44/44; #437 direct invocation 2/2 (not in suite inventory); `./scripts/render-skills.py --check` PASS.
- Four post-stabilization paired case runs: candidate 4/4 pass; baseline main 1/4 pass with transient-phase failures. The test calls `recovery-input`, not checkpoint validation. Instrumented calls: main median 135.36 ms (14 samples), candidate 128.57 ms (16 samples); small process-level sample does not rule out smaller or environment-specific timing differences. Run evidence and paired logs at `.kw/worktrees/issue-441/.kaola/i441-native-proof/REPORT.md`, while present; the durable native and timing summary is `native-proof.json`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/kaola-dispatch.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/duty-reconcile.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-349-checkpoint-verb.py

## Follow-Up Items

None required by the accepted scope. Runtime rollout and restarts remain owner/Delegator-gated.

## Final readiness

PASS — Host accepted the candidate and authorized merge, issue closure and archive. No deployment or install is authorized by this finalization.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-441/.cache/final-validation.md
- kaola-workflow/archive/issue-441/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-441/finalization-summary.md
- kaola-workflow/archive/issue-441/mission-ledger.jsonl
- kaola-workflow/archive/issue-441/native-proof.json
- kaola-workflow/archive/issue-441/workflow-state.md
