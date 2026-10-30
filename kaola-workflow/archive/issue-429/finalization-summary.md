# Finalization Summary — issue-429

## Delivered

Host accepted the bounded implementation of #428 on 2026-10-30, explicitly accepting the pre-existing baseline red suites and the unverified live integration duty. The integrated candidate is `2e39dbf67d7e4535dc799ca665daeee7efc29c69`, containing implementation `c7f86a50` and main `526cb7cb`. The original carrier event and current node prompt now bind every maintenance checkpoint, its through revision and selected recovery; scoped accounting, hard refusal and carrier settlement are verified by isolated fixtures. Relevant recovery routes, canonical guidance, generated Skills and the restart note were updated. Frozen `templates/grok-golden/` was unchanged.

Baseline real-CLI fixture: the ordinary forged batch returned written/verified=true and moved acked/handled to 2/2 while recovery remained pending. Candidate regression tests refuse such forged or reused batches with byte-identical state. Five new tests: `MaintenanceCheckpoint.test_direct_forged_maintenance_batches_do_not_write`, `MaintenanceCheckpoint.test_native_receipt_mismatches_refuse_without_writes`, `MaintenanceCheckpoint.test_reused_native_id_on_later_direct_turn_is_refused`, `MaintenanceCheckpoint.test_sent_recovery_requires_matching_flag_and_omission_is_partial`, and `HolderNodeMode.test_admitted_ordinary_batch_checkpoints_and_carrier_settles`.

## Evidence and acceptance boundaries

On integrated candidate `2e39dbf67d7e4535dc799ca665daeee7efc29c69`, controlled Bash 5.3 / Python 3.13 selected inventory: #255 176 tests, FAIL (24 failures, 3 errors); #292 5 PASS; #412 31 PASS; #309 9 tests, FAIL (1 failure); #421 45 PASS; #425 26 PASS; #426 53 PASS; #427 21 PASS. Failure/error names and order are identical to clean baseline `8294d17d` (24 failures, 3 errors and one #309 failure; no new failures). Host independently compared `8294d17d`, `526cb7cb`, and `c7f86a50`. Original selected-run log `/tmp/kpr429-merge-2e39dbf6.log` is ephemeral; this summary records the durable result. The `.cache/final-validation.md` receipt truthfully records `verdict: fail`, not green.

`./scripts/render-skills.py --write` and `--check` passed at the integrated candidate. Check output:

```text
render-skills: PASS (12 workers + kaola-project-runner + kaola-delegator + grok-bot host: 1 bridge skill, 2555 B, content stage, unpinned (not saveable); budgets OK)
```

The Host accepted bounded implementation with two explicit unresolved duties: baseline contract-suite debt remains in open #430, and affected live ACP Host/node start → send → read → checkpoint → stop integration was not authorized or run. Neither is a PASS. No whole inventory, Cursor/cursor-cli, Fable, live installation, tag or release. KW and shared KPR were read-only. `CHANGELOG.md` states Seats: restart required.

## Validation

classification: final_validation_failed
green: false
mode: final-validation

.cache/final-validation.md does not record `verdict: pass` (column 0) — the agent's own validation did not pass (found verdict: fail)

.cache/final-validation.md is present but does not record `verdict: pass` (column 0). The agent's own validation did not pass — remediate and re-record, or fix the failing checks before finalize.

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- docs/conventions.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/hermes-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/hermes-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/hermes-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/duty-reconcile.md
- skills/kaola-project-runner/references/sideagent-node.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/references/duty-reconcile.md
- templates/orchestrator/references/sideagent-node.md
- tests/contract/test-issue-255-lifecycle-state.py
- tests/contract/test-issue-292-state-record-root.py
- tests/contract/test-issue-309-recovery-routes.py

## Follow-Up Items

Existing #430 — https://github.com/KaolaBrother/kaola-project-runner/issues/430 — confirmed OPEN with nonempty body; baseline debt remains open and was not modified by this run. Live ACP integration remains an explicit unverified duty for an appropriately authorized owner; no separate acceptance result is inferred.

## Final readiness

Host accepted bounded scope and explicitly directed finalize, sink and #429 closure. The known validation failures and live obligation remain as above; the lifecycle may proceed without describing them as passed.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #429

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-429/.cache/final-validation.md
- kaola-workflow/archive/issue-429/finalization-summary.md
- kaola-workflow/archive/issue-429/mission-ledger.jsonl
- kaola-workflow/archive/issue-429/workflow-state.md
