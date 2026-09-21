# Finalization summary — issue-121

## Delivered
#121: a stale `kaola-project-runner` main Skill in a Host's discovery roots is now refused at Host
`start` (`main-skill-build-skew`, exit 1, nothing created, user roots untouched) instead of silently
shadowing the Host's build. Every worker Skill carries `scripts/main-skill-build.json` (per-file
sha256 of the rendered main Skill + 12-hex build); after the #105 worker gate passes, every Skill
directory whose SKILL.md frontmatter is `name: kaola-project-runner` in the platform's
`HOST_SKILL_DISCOVERY_DIRS` (repo and home) must match every recorded file. Passing Host starts
report `main_skill_build`.

## Files Changed
Commit a75cb23: scripts/render-skills.py, scripts/kaola-acp.py, skills/*/scripts/kaola-acp.py (render),
skills/*/scripts/main-skill-build.json (new, render), skills/kaola-project-runner/references/{host-entry-matrix,host-startup}.md
(render), templates/orchestrator/references/{host-entry-matrix.md,host-startup.md.tmpl},
tests/contract/test-issue-119-host-entry.py, docs/api.md, docs/zcode-host.md, CHANGELOG.md.

## Test Coverage
tests/contract/test-issue-119-host-entry.py::test_issue_121_main_skill_build_skew_refuses (8 checks,
temp repo + shadow HOME): aligned → ready with main_skill_build == record build; stale SKILL.md in
~/.factory/skills + renamed `.bak` copy missing a file in <repo>/.agents/skills → refused, count 2,
both paths, detail names path + both builds + install-local.sh repair, no record dir, stale copies
untouched; worker-named start not compared. #105 regressions: test_non_zcode_host_build_skew_refuses,
test-zcode-heartbeat-contract 23/23 (472 checks), test-issue-123-shared-refs 6/6.

## Acceptance
- Automated: `./scripts/render-skills.py --check` PASS; `./scripts/validate.sh` rc=0 at a75cb23
  (log archived as validate.log). test-issue-119-host-entry 10/10, 143 checks.
- Outer acceptance: Host review PASS on candidate a75cb23 (2026-09-22).
- Not executed: live per-platform tmux smoke (this change adds a pre-spawn read-only gate; covered by
  real-CLI contract tests with a fake ACP agent).
- Issue statement walk: "Measured" stale main Skill on cursor-cli → covered by the refusal (roots are
  HOST_SKILL_DISCOVERY_DIRS for every Host-capable platform, cursor-cli included); "#105 compares only
  worker Skills" → main Skill now compared; "Hypothesis" (SKILL.md digest vs Host build across
  HOST_SKILL_DISCOVERY_DIRS) → implemented, extended to every recorded file of the main Skill.

## Validation
final-validation.md: verdict pass, command `./scripts/render-skills.py --check && ./scripts/validate.sh`,
validated_candidate_hash 8cbbacfac84a8237c89fa3edaa6da5dbdfecdbe7990ec00b08cdab81120077ea.
run-chains: chains_config_missing (consumer repo; gate is the recorded final-validation.md).

## Changed Paths
finalize --check changed_paths (source-scoped; docs/api.md, docs/zcode-host.md, CHANGELOG.md also changed in a75cb23):
scripts/kaola-acp.py, scripts/render-skills.py, skills/{10 workers}/scripts/kaola-acp.py,
skills/{10 workers}/scripts/main-skill-build.json, skills/kaola-project-runner/references/host-entry-matrix.md,
skills/kaola-project-runner/references/host-startup.md, templates/orchestrator/references/host-entry-matrix.md,
templates/orchestrator/references/host-startup.md.tmpl, tests/contract/test-issue-119-host-entry.py. dirty_paths: [].

## Documentation Docking
.cache/doc-docking.md — DOCKED.

## Follow-Up Items
None filed. Deployment consequences recorded by the Host as designed behavior: (1) a Host on this
build refuses until an older main Skill root on this Mac is reinstalled; (2) a main-Skill-only change
now changes every worker Skill's record file (not its #105-compared scripts).

## Readiness
READY — closure decision: close #121.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-121/.cache/doc-docking.md
- kaola-workflow/archive/issue-121/.cache/final-validation.md
- kaola-workflow/archive/issue-121/.cache/mirror-digest.json
- kaola-workflow/archive/issue-121/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-121/finalization-summary.md
- kaola-workflow/archive/issue-121/mission-list.md
- kaola-workflow/archive/issue-121/workflow-state.md
