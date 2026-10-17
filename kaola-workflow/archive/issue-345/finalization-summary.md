# Finalization Summary — issue-345

## Delivered

Issue #345: dsh gains a `commandcode` tier, Command Code DeepSeek V4.1 Flash, and that tier is a default-authorized Worker-pool member.

- `platforms/dsh.yaml` adds named tier `commandcode`. Runner id `commandcode/deepseek/deepseek-v4.1-flash`. Display name `DeepSeek V4.1 Flash (Command Code)`. Class Worker. The same Fast implementation profile as `dsh/default`. Effort `max` through ACP `reasoning_effort`.
- A `--tier commandcode` start sends the compact ACP model wire `["commandcode","deepseek/deepseek-v4.1-flash"]`. A space after the comma is an unknown option. `dsh/default` stays `["opencode-go","deepseek-v4.1-flash"]` with `reasoning_effort=max`.
- Static quota package `commandcode` (windows `5h`, `weekly`, `monthly`) and provider prefix `commandcode`. No live `/alpha` probe, no shim, and no KPM mirror. `scripts/adapters/dsh.sh` matches the manifest. The operator route, never written by the Runner, is `COMMANDCODE_API_KEY` at `https://api.commandcode.ai/provider/v1`.
- Because the class is Worker, the tier is a default-authorized pool member and needs no grant row. The exact pool is `claude-code/haiku`, `codex/luna`, `devin/default`, `dsh/commandcode`, `dsh/default`, `opencode/default`, `zcode/default`. `worker_pool_members()` sorts that list by preset id. `codex/luna` and `zcode/default` stay pool members. Antigravity is not added.
- Docs, README, CHANGELOG, and generated `skills/` come from the manifest plus `./scripts/render-skills.py --write`. The current unreleased CHANGELOG section says `Seats: restart required` because this change touches `platforms/dsh.yaml` and `scripts/adapters/dsh.sh`. The #344 start-brief item itself does not change the operator restart set. The grok-bot bridge stays content-stage and unpinned.
- Contract coverage: `tests/contract/test-issue-345-dsh-commandcode.py` and `tests/contract/test-issue-345-worker-pool.py`, plus the preset, quota, and pool pins those commits updated.

## Candidate

Branch `workflow/issue-345`, parent local `main` `276cda38`.

- `664c7631` — `feat: add the dsh/commandcode tier (#345)`
- `c1145143` — `fix: list dsh/commandcode in the exact Worker pool (#345)`

Acceptance candidate: `c1145143`. Worktree clean. Not pushed. This finalize does not add an implementation commit.

Host acceptance: ACCEPTED. The pre-merge full gate on this commit is green.

## Evidence

- Full inventory `./scripts/validate.sh` (no `--suite`), worktree clean at `c1145143`: 125 suites, exit 0, wall 1433.37 s. Log: `/tmp/kpr-run/full-validate-345-c1145143.log` (`VALIDATE_EXIT=0`, `validate: candidate: c1145143 (clean)`). `render-skills: PASS` is inside that run. The same commit is still the worktree HEAD, so that voucher is reused and the suite is not re-run.
- Scratch start/send/stop receipts: `/tmp/i345-scratch/{start,send,stop}.stdout`. Start ready, compact wire, `reasoning_effort` max, effective max; send `final_text` OK; stop `residual_pids` empty.
- Fail-on-main voucher, unfixed `276cda38`: `/tmp/i345-pool-fail-on-main.txt` (`EXIT:1`).
- Mission ledger `kaola-workflow/.ledger/issue-345.jsonl`: both missions `done`. Those lines are not rewritten.

## Known failures and unverified scope

- No known product failure on `c1145143`.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue #345. Do not add a GitHub comment. Do not release, tag, install, or open a new issue. Keep-open is that deferral. Offline mode makes no forge call, so the claim label is not released here.
- Post-merge `./scripts/render-skills.py --write` and `--check` run on local main after the sink. No validate suite is re-run; the full gate already passed on this same commit.
- The prior Host session `grok-KPR-i345-dsh-commandcode` stopped after `holder-not-ready` twice. This finalize does not start or resume that session.

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
- docs/zcode-host.md
- platforms/dsh.yaml
- scripts/adapters/dsh.sh
- scripts/render-skills.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/SKILL.md
- skills/dsh-kaola-project-runner/references/platform.md
- skills/dsh-kaola-project-runner/scripts/adapters/dsh.sh
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-148-quota-packages.py
- tests/contract/test-issue-218-preset-ids.py
- tests/contract/test-issue-324-wake-fixes.py
- tests/contract/test-issue-336-node-turn-refusal.py
- tests/contract/test-issue-345-dsh-commandcode.py
- tests/contract/test-issue-345-worker-pool.py
- tests/contract/test-issue-98-dsh-acp.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing was filed.

## Readiness

Host accepted the change. The full-gate voucher on `c1145143` is reused. Local merge-sink and archive proceed. Issue #345 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #345

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-345/.cache/final-validation.md
- kaola-workflow/archive/issue-345/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-345/finalization-summary.md
- kaola-workflow/archive/issue-345/mission-ledger.jsonl
- kaola-workflow/archive/issue-345/workflow-state.md
