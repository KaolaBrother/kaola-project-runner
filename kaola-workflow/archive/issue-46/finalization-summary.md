# Issue #46 finalization

## Delivered

Consumer runtime Skills install as owned standalone copies by default, severing the observed same-inode link to the Project Runner source. Explicit `--method link` remains a maintainer choice; an existing owned link migrates on default reinstall. The main Skill now tells consumer-project agents to keep authorization, heartbeat, and run facts in the consuming project and to treat the Project Runner checkout and installed Skill payload as read-only for consumer work. No new state machine, classifier, transport refusal, or hard gate was added.

## Files Changed

`scripts/install-local.sh`; `templates/orchestrator/SKILL.md.tmpl` and generated `skills/kaola-project-runner/SKILL.md`; `README.md`, `docs/api.md`, `docs/architecture.md`, `CHANGELOG.md`; focused installer and generated-Skill tests.

## Test Coverage

Default-copy inode separation, owned-link migration including legacy Grok root link, protection of foreign symlinks and modified copies, and main Skill consumer-project boundary. Duplicate #46 assertions in the older orchestrator test file were removed during review.

## Validation

PASS at `5cf5ab8ce520a005e22b12c310ff92fe1a49b544`: `./scripts/render-skills.py --check && ./scripts/validate.sh && git diff --check main...HEAD && git diff --check`, exit 0. Workflow receipt: `.cache/final-validation.md`, candidate hash `686dfc106b295fdcb61b959e46b4432bc15e8027fdeb09b9e7f0f4f9aa258103`. Live seven-platform tmux smoke was not rerun; this issue changes installation and main Skill guidance, not transport start/send/read/stop. Real local Codex and Devin link-to-copy migration remains a post-sink deployment check.

## Changed Paths

The finalize check reported `scripts/install-local.sh`, `skills/kaola-project-runner/SKILL.md`, `templates/orchestrator/SKILL.md.tmpl`, `tests/contract/test-generated-skills.py`, `tests/contract/test-installer-migration.sh`, and `tests/contract/test-installer-runtimes.sh` as changed implementation paths. README, API, architecture, and changelog changes are documented above.

## Documentation Docking

DOCKED in `.cache/doc-docking.md`.

## Follow-Up Items

No Issue #46 defect remains. Existing optional Codex `--bin-links` helper symlinks are unchanged and outside the observed Skill-payload edit path.

## Readiness

Ready for Workflow archive, issue closure, and merge sink; local installed-copy migration follows publication.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-46/.cache/cursor-delivery.md
- kaola-workflow/archive/issue-46/.cache/doc-docking.md
- kaola-workflow/archive/issue-46/.cache/final-validation.md
- kaola-workflow/archive/issue-46/.cache/mirror-digest.json
- kaola-workflow/archive/issue-46/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-46/.cache/review-verdict.md
- kaola-workflow/archive/issue-46/finalization-summary.md
- kaola-workflow/archive/issue-46/mission-list.md
- kaola-workflow/archive/issue-46/workflow-state.md
