# Finalization summary — issue-144 (#144)

## Delivered
Devin tier layout per the Owner decision (issue comment 5787317864):
- `default`: `swe-2-max` — unchanged.
- `upgrade`: **Fusion High (Opus 5.5 High + SWE-2 Medium)** — `fusion-claude-opus-5-5-high-sidekick-swe-2-medium`
  (was the Fable fusion), via `acp_command_upgrade` spawn argv. Devin has no pure Opus 5.5 High.
- `fable` (alt): **Fusion High (Fable 5.1 High + SWE-2 Medium)** — `fusion-claude-fable-5-1-high-sidekick-swe-2-medium`
  via `acp_command_alt`; the pure `claude-fable-5-1-high` preset is retired.
- Astra fusion `fusion-gpt-6-astra-high-sidekick-swe-2-medium`: measured, documented only (issue comments + CHANGELOG), no tier.
- `acp_verified_versions` unchanged.

## Files Changed
platforms/devin.yaml; scripts/adapters/devin.sh; generated
skills/devin-kaola-project-runner/{SKILL.md,references/acp.md,references/platform.md,scripts/platform.yaml,scripts/adapters/devin.sh};
tests/contract/test-issue-111-model-tiers.py; tests/contract/test-generated-skills.py; CHANGELOG.md; README.md.

## Test Coverage
- test-issue-111-model-tiers.py: Devin LIVE_PRESETS alt row = Fable fusion; TierAgentCommand DEVIN table
  (default/upgrade/fable commands, argv model = manifest id per tier); continue keeps the `fable` tier command;
  `test_a_platform_refuses_another_platforms_tier_word` (devin refuses `core`, available `[default, upgrade, fable]`);
  new `test_devin_fable_tier_selects_the_fable_fusion` (fable → alt → fusion id; no tier uses pure `claude-fable-5-1-high`);
  ManifestAndAdapterAgree covers adapter ADAPTER_ALT_* ↔ manifest.
- test-generated-skills.py: Devin leakage scrub removes exactly the two fusion ids and the retired pure id.
- test-acp-contract.py: no Devin preset rows affected (its Devin tests use swe-2-max only) — unchanged.

## Validation
- `./scripts/render-skills.py --check` — PASS rc=0 (budgets OK) on 6000d1e
- `./scripts/validate.sh` — rc=0 on 6000d1e: 40 suite runs, 283 `ok`, no FAIL/ERROR/RED/Traceback,
  kaola-grok-bot-verify PASS, sweep `residual_pids: []` (log validate-144.log); Host re-ran both rc=0 on 6000d1e
- `git diff --check main..HEAD` — clean
- Record: .cache/final-validation.md, validated_candidate_hash 1ad9da51ab99…
- Host acceptance: ACCEPTED at 6000d1e (2026-09-23).
- Not executed in this run: post-merge live `--tier upgrade` / `--tier fable` receipts
  (`effective_model` = the fusion id, `effective_model_source=launch-argv`) — Host-owned after sink + install refresh.
  Pre-change live spawn proofs for both fusion ids are in the issue body/comments (cli 3000.11.1, 2026-09-23).

## Changed Paths
- CHANGELOG.md
- README.md
- platforms/devin.yaml
- scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/SKILL.md
- skills/devin-kaola-project-runner/references/acp.md
- skills/devin-kaola-project-runner/references/platform.md
- skills/devin-kaola-project-runner/scripts/adapters/devin.sh
- skills/devin-kaola-project-runner/scripts/platform.yaml
- tests/contract/test-generated-skills.py
- tests/contract/test-issue-111-model-tiers.py

## Issue walk
- upgrade name/id/parameters + acp_command_upgrade → platforms/devin.yaml, adapter; test DEVIN table.
- Alt tier: body asked to retire it; Owner comment 5787317864 superseded that (comment wins) — fable restored as the
  Fable fusion, pure id retired → manifest/adapter/test rows + new fable-fusion test.
- acp_quirks reworded for the two fusion tiers → manifest, rendered acp.md.
- skills re-rendered → --check PASS.
- Tests + CHANGELOG → above; README/architecture/api docked (.cache/doc-docking.md).
- acp_verified_versions unchanged → confirmed in diff.
- Acceptance live `--tier upgrade` receipt → Host-owned post-merge (see Validation). Body's "--tier fable no longer
  advertised" is superseded by the Owner mapping (fable stays declared as the fusion).

## Documentation Docking
.cache/doc-docking.md — DOCKED.

## Follow-Up Items
None filed. No run-discovered defect.

## Status
READY — accepted; finalize + merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-144/.cache/doc-docking.md
- kaola-workflow/archive/issue-144/.cache/final-validation.md
- kaola-workflow/archive/issue-144/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-144/finalization-summary.md
- kaola-workflow/archive/issue-144/mission-ledger.jsonl
- kaola-workflow/archive/issue-144/workflow-state.md
