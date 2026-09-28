# Finalization Summary — Issue #211 (Recovery Run)

## Delivered

Completed the reopened cost-wording scope. `platforms/dsh.yaml`, `platforms/devin.yaml`, and `platforms/opencode.yaml` now contain the exact owner-approved default profile strings without per-profile cost adjectives. Renderer-owned README, profile catalog, Worker profile, and generated platform surfaces are synchronized. The earlier Cursor CLI refinement and retained Grok CLI wording were already merged at `ad15fc78` and were left unchanged in this run.

Implementation commit: `e40b93c9a1ae023098f8fed9c307db92c207c65b` on `workflow/issue-211`.

## Files Changed

- `platforms/dsh.yaml`, `platforms/devin.yaml`, `platforms/opencode.yaml`
- `README.md`
- `skills/kaola-project-runner/references/profile-catalog.md`
- `skills/kaola-project-runner/references/worker-profiles.md`
- `skills/dsh-kaola-project-runner/scripts/platform.yaml`
- `skills/devin-kaola-project-runner/scripts/platform.yaml`
- `skills/opencode-kaola-project-runner/scripts/platform.yaml`
- Ten generated `skills/*-kaola-project-runner/scripts/main-skill-build.json` records refreshed by the renderer
- `CHANGELOG.md`

The existing pre-expansion archive at `kaola-workflow/archive/issue-211/` remains intact and describes that earlier run. This recovery run is separately archived by Workflow.

## Test Coverage

- `./scripts/render-skills.py --write` — exit 0; generated outputs synchronized; budgets OK.
- `./scripts/render-skills.py --check` — PASS; budgets OK. The final-validation receipt binds this command to candidate tree hash `146b8ba1a9d335946bbf263d1efbf1c9b633735d511b0f1e0814644353d6cba5`.
- Focused Python assertions against baseline `ad15fc78` — PASS: 20 logical profiles counted; exactly the three authorized profile values changed; all 17 other profiles and all other manifest bytes unchanged; exact rendered rows and generated platform copies verified; Cursor/Grok rows, Worker class guidance, budget ceilings, and frozen `grok-golden` verified unchanged.
- `git diff --check` — PASS.
- Host acceptance independently verified the three exact source strings, rendered README/catalog rows with no cost wording residue, surviving distinct Cursor/Grok rows, Worker profile synchronization, both-part changelog entry, and renderer budget check.
- `./scripts/validate.sh` was not run; it was optional for this wording-only change. Live ACP smoke and model probes were not run because no transport or runtime behavior changed. The npm edition chains are not applicable to this non-npm repository; the consumer final-validation receipt records the focused renderer command.
- No release, tag, or installation was performed.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- README.md
- platforms/devin.yaml
- platforms/dsh.yaml
- platforms/opencode.yaml
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/platform.yaml
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/platform.yaml
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/references/profile-catalog.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/platform.yaml
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json

## Documentation Docking

DOCKED. See `.cache/doc-docking.md` for the checked surfaces and no-impact decisions.

## Follow-Up Items

None.

## Readiness

Ready for the authorized merge sink, Issue #211 closure, separate recovery-run archive, and worktree/branch cleanup. No release, tag, or installation is authorized.

## Sink Recovery

The first `sink-merge --sink` attempt stopped before mutation with `archive_authority_ambiguous`: the prior pre-expansion archive and this recovery archive share the project slug and branch. The recovery archive remains intact. A fresh all-pending sink journal is bound to this run's claim timestamp, branch head, and exact archive destination so the sink can resume this run without replaying any earlier run's steps.

## Sink Findings

post_rebase_tests: skipped

archive_collision: kaola-workflow/archive/issue-211/ already existed, so this run was archived to kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/ instead. The pre-existing directory was left exactly where it was — a SECOND archive standing for this project, no part of this one. What it holds, and whether the repository tracks it at all, is not recorded here: read it before treating this archive as the run's whole record.

archived_paths:
- kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/.cache/doc-docking.md
- kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/.cache/final-validation.md
- kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/finalization-summary.md
- kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/mission-ledger.jsonl
- kaola-workflow/archive/issue-211.archived-2026-09-28T05-53-52-520Z/workflow-state.md
