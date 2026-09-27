# Finalization Summary — issue-198

## Delivered

Issue #198: explicit Runner refusals are actionable at the time they occur, using their existing receipts. `main-skill-build-skew` keeps its typed pre-mutation refusal (`result: refused`, exit 1, `mutation_performed: false`, `mutation_status: not_started`, `main_skill_skew` path/build fields, nothing created). Its `detail` now names each actual affected root and the existing installer route from the accepted checkout (`./scripts/install-local.sh --skills-dir ROOT --platform P`). It also states that route's ownership effect: only receipt-owned copies are replaced, existing referrers are kept, the `generic` referrer is added, `kaola-delegator` is planned, and a runtime referrer's own `--runtime NAME` install is the owner route. An owned obsolete duplicate is withdrawn with that route plus `--uninstall`, never deleted by hand. Renamed copies no installer manages are named for their owner. `worker-skill-build-skew` gives the same per-root route with the skewed copies' platforms and `--no-orchestrator`. `worker-skill-root-unreadable` no longer suggests deleting the root. A `drain-stop-failed` after the exact stop was sent (`mutation_status: completed`) now directs inspecting `status`/`residual_pids` before another drain-restart. `host-exists` already directs attaching `existing_host`, so it is unchanged. No Runner refusal expresses missing authority, so none was added. No classifier, gate, automatic retry/deletion/fallback, or install-time loading/dispatch validation was added.

Issue parts → evidence:
- Stale shared copy → main-skill-build-skew/not_started with actual path+builds and an ownership-aware, destination-specific route. Covered by test-issue-119 (`test_issue_121_main_skill_build_skew_refuses` route/renamed/uninstall checks) and the sandbox real-use demo /tmp/kpr198-qa2.GWQX (refusal → named route → same start ready).
- Retry after owned remedy; the refusal starts nothing → 0 records on refusal, then start ready (demos qa2/qa3).
- Other refusal wording uses its own facts: worker skew (test-119 AC9, test-162 skew_before_stopping), unreadable root (test-zcode-heartbeat i106), partial drain (test-162 `test_partial_drain_stop_directs_inspection_before_another_drain`). host-exists unchanged.
- No install-time Skill-loading/dispatch test, E2 gate, model-catalog gate, or blanket stop → none added (diff).

## Files Changed

scripts/kaola-acp.py; skills/*/scripts/kaola-acp.py (10 generated copies); docs/api.md; docs/zcode-host.md; CHANGELOG.md; tests/contract/test-issue-119-host-entry.py; tests/contract/test-issue-162-upgrade-safety.py; tests/contract/test-zcode-heartbeat-contract.py. Commits 0963c719, ec9f5a56.

## Test Coverage

Focused assertions on the changed wording (each fails on the old text) plus preserved refusal semantics; full validate.sh exit 0 on ec9f5a56 (see .cache/final-validation.md).

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/zcode-host.md
- scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- tests/contract/test-issue-119-host-entry.py
- tests/contract/test-issue-162-upgrade-safety.py
- tests/contract/test-zcode-heartbeat-contract.py

## Documentation Docking

DOCKED — see .cache/doc-docking.md.

## Follow-Up Items

None filed. Remaining uncertainty from the issue (duplicate-root discovery precedence) is unchanged and out of scope. Host acceptance of ec9f5a56 is recorded in the Host conversation.

## Readiness

Ready: Host-accepted ec9f5a56, validation pass, docs docked. Sink: merge into local main, close #198.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-198/.cache/doc-docking.md
- kaola-workflow/archive/issue-198/.cache/final-validation.md
- kaola-workflow/archive/issue-198/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-198/finalization-summary.md
- kaola-workflow/archive/issue-198/mission-ledger.jsonl
- kaola-workflow/archive/issue-198/workflow-state.md
