# Finalization Summary — issue-117

## Delivered
Droid presets corrected (Droid slot only): default is Auto (`auto`, no effort pin; PTY settings overlay `{"model":"auto"}`, ACP applies `model=auto` explicitly); `--tier upgrade` is Kimi K3 Max (`kimi-k3`, `reasoning_effort=max`); the alternative tier is deleted so `--tier alternative` is the typed `tier-not-declared` refusal on both transports. All kimi-k2.7 / "no K2.8 nearest kin" narrative removed from launch_summary and current docs.

## Files Changed
platforms/droid.yaml, scripts/adapters/droid.sh, skills/droid-kaola-project-runner/** (generated), tests/contract/{fake-droid-acp-agent,test-droid-acp-contract,test-generated-skills,test-issue-111-model-tiers}.py, docs/api.md, README.md, CHANGELOG.md. Commits 6a1f657 (candidate) + d470e5a (docs/api.md one-sentence amendment).

## Test Coverage
test-droid-acp-contract.py and test-issue-111-model-tiers.py re-pointed to default auto / upgrade kimi-k3 max / alternative refused; fake agent keeps kimi-k2.7-code in its catalog so the refusal is proven tier-based.

## Validation
- `./scripts/validate.sh` full plain run exit 0, 0 FAIL/ERROR at 6a1f657 (validate-117.log).
- At d470e5a (differs from 6a1f657 only in docs/api.md, 2 lines): `./scripts/render-skills.py --check` PASS budgets OK; test-droid-acp-contract.py OK; test-issue-111-model-tiers.py OK; test-generated-skills.py PASS (KAOLA_* scrubbed).
- Direct probe (Mission 2): ACP + PTY default auto/no effort, upgrade kimi-k3/max, alternative tier-not-declared.
- Host self-verification: PASS on all seven checks (scope isolation, tier fields, narrative removal, render --check, both focused suites, validate log).
- Fable final review: PASS (one docs flag, resolved by d470e5a).
- Record: .cache/final-validation.md, verdict pass, validated_candidate_hash 792c3aab576f341568c9985106eeaaf075c619aee46744a29058240252fb2744.

## Changed Paths
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
- (docs, source-scope omitted by finalize) CHANGELOG.md, README.md, docs/api.md

## Issue walk
- Target 1 default=auto, no effort, applied explicitly on ACP → manifest/adapter + droid ACP contract test + probe.
- Target 2 core=K3 Max in upgrade, core ≠ default → upgrade_* fields + #111 tier test + probe.
- Target 3 alternative deleted, typed refusal, narrative removed → empty alt_* keys, refusal tests on both transports, launch_summary/docs scan.
- Acceptance: render --check PASS; grok-golden and other platforms unchanged (diff scope droid-only); validate exit 0; no writes to ~/.factory, ~/.dsh, ~/.zcode.

## Documentation Docking
DOCKED — see .cache/doc-docking.md.

## Follow-Up Items
None.

## Status
READY — close #117.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-117/.cache/doc-docking.md
- kaola-workflow/archive/issue-117/.cache/final-validation.md
- kaola-workflow/archive/issue-117/.cache/mirror-digest.json
- kaola-workflow/archive/issue-117/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-117/finalization-summary.md
- kaola-workflow/archive/issue-117/mission-list.md
- kaola-workflow/archive/issue-117/workflow-state.md
