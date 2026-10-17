# Finalization Summary — issue-346

## Delivered

Issue #346: a Worker preset runs only after an explicit owner grant. No Worker grants means no Workers.

- `worker_grants` on `kaola-delegator-heartbeat/1` is a list. A row is exactly `preset_ids` or `scope: all-worker-presets`, with `count` a nonnegative integer or the literal `unlimited`, optional `expires`, and `state` granted, paused, or revoked. Missing or malformed `count` refuses that class and never becomes unlimited.
- An exclusion vetoes every authorization, including unlimited and all-Worker scope. Unlimited never authorizes Elite or Expert.
- A legacy `worker_pool` is not migrated into grants. A well-formed leftover pool is removed and yields zero Workers. The owner re-specifies grants.
- Host dispatch refuses an unauthorized Worker with `no-worker-grant` or `worker-grant-expired`, status `not-run`, and starts no seat. A numeric count is enforced. Only an explicit unlimited grant that covers that preset skips the count check.
- Sideagent maintenance candidates are only granted Worker presets, sorted by id. None granted fails once and returns. `zcode/default` is no longer a privileged first choice.
- `dsh/commandcode` stays a Worker-class catalog tier and is usable only after a grant, the same as every other Worker preset. The published 0.9.17 #345 bullet is corrected in place. Sections below 0.9.17 are unchanged.
- Docs, README, CHANGELOG, and generated `skills/` come from the templates plus `./scripts/render-skills.py --write`. The grok-bot bridge stays content-stage and unpinned. Seats: restart required.

## Candidate

Branch `workflow/issue-346`, parent local `main` `79770ab71b55f847f6904beefa7737ce940e6d37`.

- `3088c46f74bbb2d83badd5c64083a68e22ea7a2e` — `feat: require an explicit Worker grant (#346)`

Acceptance candidate: `3088c46f74bbb2d83badd5c64083a68e22ea7a2e`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED. The pre-merge full gate on this commit is green.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `3088c46f`: 126 suites, exit 0, wall 1478.54 s. Log: `/tmp/kpr-run/full-validate-346-3088c46f.log` (`validate: candidate: 3088c46f (clean)`, `VALIDATE_EXIT=0`). `render-skills: PASS` is inside that run. `test-issue-255-lifecycle-state.py` elapsed 113.941 s inside the same exit 0. The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- Mission ledger `kaola-workflow/.ledger/issue-346.jsonl`: both missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `3088c46f`. The Host gate included the 255 suite and exited 0. An earlier local exit 1 on `test_sent_recovery_checkpoint_keeps_later_signal_and_exact_reclaims_first_node` is not the acceptance evidence.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #346. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run; the full gate already passed on this same commit.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- docs/api.md
- docs/architecture.md
- docs/dispatch-collect.md
- docs/zcode-host.md
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- scripts/kaola-acp-holder.py
- scripts/kaola-dispatch.py
- scripts/kaola-record-contract.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/SKILL.md
- skills/antigravity-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/antigravity-kaola-project-runner/scripts/kaola-record-contract.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/SKILL.md
- skills/claude-code-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/claude-code-kaola-project-runner/scripts/kaola-record-contract.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/SKILL.md
- skills/codex-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/codex-kaola-project-runner/scripts/kaola-record-contract.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/devin-kaola-project-runner/scripts/kaola-record-contract.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/droid-kaola-project-runner/scripts/kaola-record-contract.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/dsh-kaola-project-runner/scripts/kaola-record-contract.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/SKILL.md
- skills/grok-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/grok-kaola-project-runner/scripts/kaola-record-contract.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/handoff.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-delegator/references/inquiry-report.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/dispatch-collect.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kaola-project-runner/scripts/kaola-dispatch.py
- skills/kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/SKILL.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-record-contract.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/SKILL.md
- skills/opencode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/opencode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/SKILL.md
- skills/zcode-kaola-project-runner/scripts/kaola-acp-holder.py
- skills/zcode-kaola-project-runner/scripts/kaola-record-contract.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/SKILL.md.tmpl
- templates/grok-bot/accepted-revision.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/kaola-delegator/references/inquiry-report.md
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/dispatch-collect.md
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-244-dispatch.py
- tests/contract/test-issue-259-record-contract.py
- tests/contract/test-issue-295-delegator-seats.py
- tests/contract/test-issue-324-wake-fixes.py
- tests/contract/test-issue-345-worker-pool.py
- tests/contract/test-issue-346-worker-grants.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing was filed.

## Readiness

Host accepted the change. The full-gate voucher on `3088c46f` is reused. Local merge-sink and archive proceed. Issue #346 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #346

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-346/.cache/final-validation.md
- kaola-workflow/archive/issue-346/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-346/finalization-summary.md
- kaola-workflow/archive/issue-346/mission-ledger.jsonl
- kaola-workflow/archive/issue-346/workflow-state.md
