# Finalization summary — issue-143 (#143)

## Delivered
Cursor `--tier upgrade` preset replaced: Claude Fable 5.1 High (`claude-fable-5-1-high`) →
**Claude Opus 5.5 High** (`claude-opus-5-5-high`), mapped by `acp_model_map` onto the live picker
base id `claude-opus-5-5`, effort `high` applied through the model's advertised `effort` option.
Default (`grok-4.7-xhigh`), alt tier, `acp_verified_versions`, and Devin are unchanged.

## Files Changed
platforms/cursor-cli.yaml; scripts/adapters/cursor-cli.sh; generated
skills/cursor-cli-kaola-project-runner/{SKILL.md,references/platform.md,scripts/platform.yaml,scripts/adapters/cursor-cli.sh};
tests/contract/test-acp-contract.py; tests/contract/test-generated-skills.py;
tests/contract/mock-acp-agent.py; CHANGELOG.md.

## Test Coverage
- test-acp-contract.py `test_cursor_upgrade_tier_maps_opus_base_id`: upgrade tier applies
  `model=claude-opus-5-5`, `effort=high` via config id `effort`, `fast=false`; requested id
  `claude-opus-5-5-high`. `test_cursor_manifest_maps_only_base_ids` allows `{grok-4.7, claude-opus-5-5}`.
- mock-acp-agent.py: Cursor picker advertises `claude-opus-5-5` with its measured `effort` option.
- test-generated-skills.py: Cursor upgrade name/id allowlisted as declared model facts.
- test-issue-111-model-tiers.py: no Cursor rows — unchanged (Host-accepted no-op).

## Validation
- `./scripts/render-skills.py --write` then `--check` — PASS rc=0 (budgets OK)
- `./scripts/validate.sh` — rc=0 on the 3f1caf8 tree (log validate-143.log); independently re-run rc=0 by the Host
- `git diff --check 3306d2c` — clean
- Record: .cache/final-validation.md, validated_candidate_hash 55c7604fe55d…
- Host acceptance: ACCEPTED at 3f1caf8 (2026-09-23).
- Not executed in this run: post-merge live `--tier upgrade` receipt (`resolved_model=claude-opus-5-5-high`,
  `effective_model=claude-opus-5-5`, `effective_effort=high`) — owned by the Host after sink + install refresh.
  Pre-change live measurement (issue body, 2026-09-23): `--model claude-opus-5-5 --effort high` landed
  `effective_model=claude-opus-5-5`, `effective_effort=high`, `effort_config_id=effort`.

## Changed Paths
- CHANGELOG.md
- platforms/cursor-cli.yaml
- scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/SKILL.md
- skills/cursor-cli-kaola-project-runner/references/platform.md
- skills/cursor-cli-kaola-project-runner/scripts/adapters/cursor-cli.sh
- skills/cursor-cli-kaola-project-runner/scripts/platform.yaml
- tests/contract/mock-acp-agent.py
- tests/contract/test-acp-contract.py
- tests/contract/test-generated-skills.py

## Issue walk
- upgrade_model_name/id/parameters/effort → platforms/cursor-cli.yaml (parameters/effort already matched).
- acp_model_map entry swap, grok entries unchanged → manifest + base-id test.
- adapter ADAPTER_UPGRADE_MODEL_ID (+ NAME) → scripts/adapters/cursor-cli.sh.
- re-rendered skills via render-skills.py --write → --check PASS.
- contract tests + CHANGELOG → listed above.
- acp_verified_versions unchanged → confirmed in diff.
- Acceptance live probe → Host-owned post-merge (see Validation).

## Documentation Docking
.cache/doc-docking.md — DOCKED.

## Follow-Up Items
None filed. No run-discovered defect.

## Status
READY — accepted; finalize + merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-143/.cache/doc-docking.md
- kaola-workflow/archive/issue-143/.cache/final-validation.md
- kaola-workflow/archive/issue-143/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-143/finalization-summary.md
- kaola-workflow/archive/issue-143/mission-ledger.jsonl
- kaola-workflow/archive/issue-143/workflow-state.md
