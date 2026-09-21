# Finalization summary — issue-129

## Delivered
Issue #129 (harness-compat 2026-09-22 class 2), candidate 3fd4672. Record-only; no live ACP run; no local CLI upgraded; `~/.dsh` untouched.
- ZCode `acp_verified_versions` cli 0.16.5 → 0.16.9. `acp_quirks` names upstream william0wang/zcode-acp v0.46.6 (turnId, permissions; tag bc240d3) as the newer protocol reference and adds "check the actual CLI version before the next live run". The `acp_wrapper_pin` stays 80aa4e2.
- Claude Code `acp_verified_versions` cli 2.1.272 → 2.1.278.
- Droid `acp_verified_versions` cli 0.220.0 → 0.223.0.
- OpenCode: N/A by Host ruling A. The repo has recorded V2 cli=2.0.11 since #112, and the V1 1.18.31 pin premise is stale. Recorded on the issue: https://github.com/KaolaBrother/kaola-project-runner/issues/129#issuecomment-5766638830
- Codex 0.155.1 + codex-acp 1.12.0: not changed by Host ruling. It is deferred to the #126 live entry measurement, where the pin and the record move together. Arranged by the Host on #126.

## Local facts (measured 2026-09-22 on this Mac, no gate)
- ZCode.app auto-updated to 3.14.1. A static read of the bundled glm/zcode.cjs shows CLI `0.16.9`, which equals the record.
- `claude --version` = 2.1.277, which differs from the record 2.1.278.
- `droid --version` = 0.220.0, which differs from the record 0.223.0 (npm has 0.223.0).
- At start the Runner reports the launched `--version` next to `acp_verified_versions` without gating.

## Files Changed
CHANGELOG.md; platforms/{zcode,claude-code,droid}.yaml; generated skills/{zcode,claude-code,droid}-kaola-project-runner/scripts/platform.yaml and skills/zcode-kaola-project-runner/references/acp.md.

## Test Coverage
No test pinned the changed record fields. The fixtures that model measured surfaces (fake droid 0.220.0 agentInfo, ZCode 0.16.5 parity fakes) keep their measured versions by design. Existing contract suites exercise the manifests through render and validate.

## Validation
- `./scripts/render-skills.py --write && --check`: PASS (budgets OK).
- `./scripts/validate.sh`: rc=0 on a tree identical to 3fd4672 (log: validate-candidate.log).
- final-validation.md verdict pass, validated_candidate_hash 71ce2b99…
- Acceptance legs: automated/local only. The issue explicitly excludes a live smoke ("不做单独 live 验证").

## Issue walk (#129)
- 必做1 OpenCode → N/A by Host ruling, with an issue comment.
- 必做2 ZCode 0.16.9 / 0.46.6 → satisfied (zcode.yaml plus note).
- 可选 Claude / Droid → satisfied. Codex → deferred to #126 by ruling.
- 验收 fields/docs/CHANGELOG, render and validate rc=0 → satisfied. No unrelated refactor, no CLI upgrade, no ~/.dsh change → satisfied.

## Changed Paths
platforms/claude-code.yaml, platforms/droid.yaml, platforms/zcode.yaml, skills/claude-code-kaola-project-runner/scripts/platform.yaml, skills/droid-kaola-project-runner/scripts/platform.yaml, skills/zcode-kaola-project-runner/references/acp.md, skills/zcode-kaola-project-runner/scripts/platform.yaml (source-scoped; CHANGELOG.md also changed)

## Documentation Docking
DOCKED — .cache/doc-docking.md

## Follow-Up Items
None filed. Codex pin and record → tracked on #126 by the Host. Pink compat expectation update → Host/Delegator relay.

## Status
READY — close #129 via merge sink.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-129/.cache/doc-docking.md
- kaola-workflow/archive/issue-129/.cache/final-validation.md
- kaola-workflow/archive/issue-129/.cache/mirror-digest.json
- kaola-workflow/archive/issue-129/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-129/finalization-summary.md
- kaola-workflow/archive/issue-129/mission-list.md
- kaola-workflow/archive/issue-129/workflow-state.md
