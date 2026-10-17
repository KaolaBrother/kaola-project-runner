# Finalization Summary — issue-342

## Delivered

Issue #342: a Devin default start reads ACP `thought_level` as the effective effort and verifies
the argv model. `devin/default` resolves effort `max`. `model_verified` is true only when the argv
model and that thought level both match the resolved selection. The ACP model `currentValue`
(often `swe-2-high`) stays `advertised_model` and is not compared. A missing thought level stays
unknown. `opus-fusion` and `fable` do not send `thought_level` and are not verified from it.
The verdict is evidence only and does not refuse the start. The model is never set through ACP.

- `platforms/devin.yaml`: `acp_effort_config_id: thought_level`, `default_model_effort: max`,
  parameters `effort=max via ACP option thought_level`. Fusion and fable efforts stay empty.
  Quirks describe the thought-level readback.
- `scripts/adapters/devin.sh`: `ADAPTER_DEFAULT_MODEL_EFFORT=max`. Fusion and fable stay empty.
- `scripts/kaola-acp.py`: `argv_thought_verification()` runs after `apply_argv_model()`. It returns
  a verdict only when the model was applied via argv, `effort_config_id` is `thought_level`, the
  expected model id is non-empty and does not contain `-sidekick-`, an expected effort is
  resolved, and `thought_level` `currentValue` is a non-empty string.
- `docs/api.md`, `CHANGELOG.md` Unreleased (`Seats: restart required`). Generated `skills/` and
  the unpinned grok-bot content stage come from `./scripts/render-skills.py --write`.
  `templates/grok-bot/accepted-revision.json` is `stage: content` so that render can write after
  the v0.9.15 pin. The pin returns at the next release.
- New suite `tests/contract/test-issue-342-devin-thought-level.py`, registered in both
  `scripts/validate.sh` lists. Adjacent expectations updated in `test-acp-contract.py`,
  `test-issue-111-model-tiers.py`, and `test-issue-237-model-display.py`.

## Candidate

Branch `workflow/issue-342`, implementation commit `974b54f4a289cbff674eafe3b2fee9d0ada90e7f`
(`fix: read Devin thought_level as default effort and verify the argv model (#342)`), 43 files,
+1217/−177, parent `23f36f27`. Not pushed.

Host acceptance: ACCEPTED. Diff review passed. Live scratch receipt on the issue shows
`effective_model swe-2-max`, thought `max`, `model_verified true`, and an exact stop. Host re-ran
`./scripts/render-skills.py --check` and suites test-issue-342, test-issue-340, test-issue-338,
test-acp-contract, test-issue-111, and test-issue-237 on this commit; all green.

## Evidence

- Live start receipt for session `devin-KPR-i342-scratch` (devin 3000.11.92, tier default,
  `KAOLA_LAUNCH_BACKEND=direct`), commented at
  https://github.com/KaolaBrother/kaola-project-runner/issues/342#issuecomment-6227942075.
  Exact stop: `residual_pids []`.
- Fail-on-main before the product change: `/tmp/kpr-i342-fail-on-main.log`, exit 1
  (10 tests, 5 failures, 5 errors).
- Worker suites on the candidate, each via `./scripts/validate.sh --suite <name>`, exit 0:
  test-issue-342-devin-thought-level.py (10), test-issue-111-model-tiers.py (25),
  test-issue-237-model-display.py (11), test-issue-218 (17), test-issue-340-devin-argv-model.py (5),
  test-issue-338-preset-effort-max.py (3), test-acp-contract.py (87).
  `./scripts/render-skills.py --write` and `--check` exit 0 on the candidate before the commit.
- Host re-run on the clean commit `974b54f4`: render `--check` PASS; the six suites above except
  test-issue-218, all green.
- Recorded validation (`.cache/final-validation.md`) binds this worktree to that Host-confirmed
  command.

## Known failures and unverified scope

- No known product failures.
- Whole-inventory `./scripts/validate.sh` was not run. Host will run it on idle main after every
  seat stops, and will push and close issue #342 only after that run is green.
- Host boundary for this finalize: merge into local main only. Do not push. Do not close issue
  #342. Do not add another GitHub comment. Do not release, tag, install, or open a new issue.
  Keep-open is that deferral, not leftover product scope.
- Post-merge `./scripts/render-skills.py --write`, `--check`, and
  `./scripts/validate.sh --suite test-issue-264-validate-lane-integrity.py` run on local main
  after the sink. Their results are recorded in the user report, not in this pre-sink candidate
  record.
- The grok-bot bridge on this branch is content-stage and unpinned. The next release owns the pin.

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
- hosts/grok-bot/INSTALL.md
- hosts/grok-bot/bridge.json
- hosts/grok-bot/kaola-delegator.md
- platforms/devin.yaml
- scripts/adapters/devin.sh
- scripts/kaola-acp.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/grok-bot/accepted-revision.json
- tests/contract/test-acp-contract.py
- tests/contract/test-issue-111-model-tiers.py
- tests/contract/test-issue-237-model-display.py
- tests/contract/test-issue-342-devin-thought-level.py

## Follow-Up Items

- None filed. No run-discovered defect requires a new issue. `searched:` not applicable; nothing
  was filed.

## Readiness

Host accepted `974b54f4`. Validation is recorded pass. Local merge-sink and archive proceed.
Issue #342 stays open. Publication to the remote waits for the Host.

## Finalize Findings

### claim_release_skipped_offline

This finalize released no claim: KAOLA_WORKFLOW_OFFLINE=1, so the release returned before making any forge call. Nothing local records whether this run was ever claimed online, so this does not assert the artifacts are there — but IF the claim was posted, the `workflow:in-progress` label and the `kw:claim` marker comment are still on the issues below. The marker expires after 24h; the label does not, and either one blocks a later claim of that issue until it is removed.

Issues whose claim release was skipped:

- #342

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-342/.cache/final-validation.md
- kaola-workflow/archive/issue-342/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-342/finalization-summary.md
- kaola-workflow/archive/issue-342/mission-ledger.jsonl
- kaola-workflow/archive/issue-342/workflow-state.md
