# Finalization summary — issue-125

## Delivered
Issue #125 (correcting #117): Droid Core is the third tier, not the upgrade.
- `platforms/droid.yaml` + `scripts/adapters/droid.sh` (ACP and PTY paths agree): default = Auto Model `auto` (unchanged); upgrade = Auto Model `auto`, no effort pin (same as default, Kimi precedent); `alt_tier_label: core` = Kimi K3 Max, `kimi-k3` at `reasoning_effort=max`; k2.7 / `alternative` not restored.
- launch_summary and generated Droid Skill no longer say upgrade = K3 Max.
- No new tier mechanism and no new gate: reuses the #111 `alt_tier_label` slot.
- Host acceptance: PASS (Host verdict 2026-09-21, candidate 72986ec, no repair round).

## Files Changed
Commit 72986ec on workflow/issue-125: platforms/droid.yaml, scripts/adapters/droid.sh, rendered skills/droid-kaola-project-runner/{SKILL.md,references/platform.md,scripts/adapters/droid.sh,scripts/platform.yaml}, tests/contract/{test-droid-acp-contract.py,test-issue-111-model-tiers.py,test-generated-skills.py,fake-droid-acp-agent.py}, README.md, docs/api.md, CHANGELOG.md.

## Test Coverage
- Mapping: test-issue-111-model-tiers.py::test_droid_core_is_the_third_tier_and_upgrade_stays_auto (alt core = K3 Max/kimi-k3/max; upgrade == default == auto); LIVE_PRESETS droid alt = core; manifest/adapter agreement test covers both transports.
- ACP behavior (fake Droid agent): test-droid-acp-contract.py::test_core_tier_applies_kimi_k3_max (model=kimi-k3, reasoning_effort=max, source runner-core), ::test_upgrade_tier_is_auto_like_default (model=auto, no effort), ::test_core_preset_effort_is_applied_exactly_once; refusals list `[default, upgrade, core]`.
- Refusal kept: test_droid_refuses_its_deleted_alternative_tier (ACP + PTY).
- Summary wording: test_droid_launch_summary_names_auto_default_and_no_alternative.
- Not run: live droid re-run (Host accepted: kimi-k3 at max already accepted live on droid 0.220.0).

## Validation
- `./scripts/render-skills.py --check && ./scripts/validate.sh` → rc=0 on 72986ec (evidence/validate.log, no FAIL lines, residual_pids []); recorded in .cache/final-validation.md, verdict pass, validated_candidate_hash ecb71ef03a23….
- run-chains: not applicable (consumer repo without package.json; gate is the recorded final validation).

## Changed Paths
finalize --check reported changed_paths (10, source-scoped; CHANGELOG.md, README.md, docs/api.md are docs and not listed):
- platforms/droid.yaml
- scripts/adapters/droid.sh
- skills/droid-kaola-project-runner/SKILL.md
- skills/droid-kaola-project-runner/references/platform.md
- skills/droid-kaola-project-runner/scripts/adapters/droid.sh
- skills/droid-kaola-project-runner/scripts/platform.yaml
- tests/contract/fake-droid-acp-agent.py
- tests/contract/test-droid-acp-contract.py
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-111-model-tiers.py

## Documentation Docking
DOCKED — .cache/doc-docking.md (CHANGELOG.md, README.md, docs/api.md updated; historical design doc kept).

## Follow-Up Items
- None filed. Boundary: no change to ~/.dsh or any user config, nor #117–#124.

## Status
Ready: accepted, validated, docked. Issue #125 closes with the merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-125/.cache/doc-docking.md
- kaola-workflow/archive/issue-125/.cache/final-validation.md
- kaola-workflow/archive/issue-125/.cache/mirror-digest.json
- kaola-workflow/archive/issue-125/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-125/finalization-summary.md
- kaola-workflow/archive/issue-125/mission-list.md
- kaola-workflow/archive/issue-125/workflow-state.md
