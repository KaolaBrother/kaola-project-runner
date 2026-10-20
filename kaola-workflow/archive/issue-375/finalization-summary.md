# Finalization Summary — issue-375

## Delivered

Installer drift backups no longer remain in Skill discovery roots. `scripts/install-local.sh` moves a
`repair` / `relink-drift` previous copy into a runner-owned quarantine run instead of
`<root>/.<name>.drift.<pid>`: the default is
`${XDG_STATE_HOME:-$HOME/.local/state}/kaola-project-runner/install-quarantine` (override
`KAOLA_PROJECT_RUNNER_QUARANTINE`), one timestamped `run-<UTC>-<pid>` directory per install, with a
`manifest.jsonl` recording `original_path`, `quarantine_path`, `root`, `skill`, `reason`, and `ts`.
Every normal install also moves stale catalog-owned `.*.drift.*` / `.*.old.*` / `.*.tmp.*` siblings
out of the roots it is about to write before it writes, prints each destination, and deletes
nothing. The explicit recovery is
`./scripts/install-local.sh --quarantine-stale-backups --skills-dir ROOT` (or `--runtime NAME`),
which performs only that move and installs no Skill.

`scripts/kaola-acp.py` excludes hidden installer backups from `installed_worker_skills()` and the
main-Skill comparison, so a planted `.x-kaola-project-runner.drift.123` with old scripts produces
neither `worker-skill-build-skew` nor `main-skill-build-skew` and never blocks `start` on its own.
A start that finds backups reports `stale_install_backups`, `stale_install_backup_count`,
`stale_install_backup_roots`, and `stale_install_backup_recovery`.
`scripts/kaola-recovery-routes.py` defines the `stale-install-backup` route plus the two installer
quarantine refusal routes. `docs/api.md` documents the quarantine, manifest, recovery command and
start fields; `CHANGELOG.md` Unreleased carries the #375 entry and states
`Seats: restart not required`.

The new `tests/contract/test-issue-375-install-quarantine.py` has three tests: temp-HOME copy
install → modified copy → repair leaves no `.drift.*` in the discovery root while the quarantine
manifest preserves the previous bytes; a seeded `.zcode-kaola-project-runner.drift.999` is moved by
the next install; and a planted `.x-kaola-project-runner.drift.123` plus a hidden main-Skill backup
start successfully with `stale_install_backups` and the route. `test-installer-runtimes.sh` now
asserts the quarantined location, and the suite is registered in `scripts/validate.sh`.

## Candidate

Branch `workflow/issue-375` at `ac6fa6a2`, rebased from `18ba9623` onto current main `ad332e62`
(which contains merged #374 and #377). The rebase resolved the `CHANGELOG.md` Unreleased union
(#377, #374, #375) and kept both #374 and #375 suites in the `scripts/validate.sh` inventory.
Generated Skill copies were re-rendered after the rebase and `./scripts/render-skills.py --check`
passes. The Grok Bot bridge remains at the unpinned content stage on main.

## Evidence

- Host acceptance of `18ba9623` in conversation: issue #375 PASS after review of the quarantine,
  manifest, automatic cleanup, `--quarantine-stale-backups` recovery, `is_install_backup`
  exclusion, `stale_install_backups` non-blocking report, recovery route, 3/3 contract tests, and
  the pre-rebase full gate (`/tmp/kpr375-full-validate3.log`, 141 suites, exit 0).
- Rebased full gate on `ac6fa6a2`: `./scripts/validate.sh` exit 0,
  `REBASED_VALIDATE_RC=0`, 143 suites, total wall 2356.3 s, log
  `/tmp/kpr375-full-validate-rebased.log`.
- Affected suites on the candidate: `test-issue-375-install-quarantine.py` 3/3,
  `test-issue-309-recovery-routes.py` 8/8, `test-installer-migration.sh` PASS,
  `test-installer-runtimes.sh` PASS; the full gate also covers
  `test-issue-162-upgrade-safety.py`, `test-issue-215-install-truthfulness.py`,
  `test-issue-236-install-completion.py`, `test-issue-119-host-entry.py`, and
  `test-issue-147-installed-survey.py`.
- Final validation record: `kaola-workflow/issue-375/.cache/final-validation.md`,
  verdict `pass`, `validation_command: ./scripts/validate.sh`, code-tree hash
  `e03bd643ec2d1891f6c94de7dacab7f283b30ee1b5ed3b958e9f1752545a7cbb`.
- Fixture cleanup: the two reported mock fixture PIDs 58526 and 58570 were already not alive, and
  `/tmp/kaola-val.Lbiutw` was already absent. No other PID or directory was touched.

## Known failures or unverified scope

- Earlier pre-rebase full runs competed with other agents' validation inventories; only
  timing-sensitive suites (`test-issue-255-lifecycle-state.py`,
  `test-issue-299-delegator-webhook.py`, `test-issue-341-agent-initiated-turn.py`) failed under
  that load and each passed on an individual rerun. The rebased full gate above ran with no
  failure.
- No release, tag, install, cloud action, or live platform seat restart was performed.
- Quarantine runs are not auto-pruned; old `run-*` directories may be removed by the operator after
  inspection. The installer never deletes the moved content itself.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/api.md
- scripts/install-local.sh
- scripts/kaola-acp.py
- scripts/kaola-recovery-routes.py
- scripts/validate.sh
- skills/antigravity-kaola-project-runner/scripts/kaola-acp.py
- skills/antigravity-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/antigravity-kaola-project-runner/scripts/main-skill-build.json
- skills/claude-code-kaola-project-runner/scripts/kaola-acp.py
- skills/claude-code-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/kaola-acp.py
- skills/codex-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/cursor-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/kaola-acp.py
- skills/devin-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/kaola-acp.py
- skills/droid-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/kaola-acp.py
- skills/dsh-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/kaola-acp.py
- skills/grok-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-acp.py
- skills/kimi-cli-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/kaola-acp.py
- skills/opencode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/kaola-acp.py
- skills/zcode-kaola-project-runner/scripts/kaola-recovery-routes.py
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- tests/contract/test-installer-runtimes.sh
- tests/contract/test-issue-375-install-quarantine.py

## Follow-Up Items

None.

## Status

READY — merge to main, close #375, archive.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-375/.cache/final-validation.md
- kaola-workflow/archive/issue-375/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-375/finalization-summary.md
- kaola-workflow/archive/issue-375/mission-ledger.jsonl
- kaola-workflow/archive/issue-375/workflow-state.md
