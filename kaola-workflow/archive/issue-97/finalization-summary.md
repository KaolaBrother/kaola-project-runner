# Finalization Summary — Issue #97

Issue: #97 — Codex: install a user-level compact-recovery Hook with the Kaola Skills, covering the
cross-repository Delegator. Branch `workflow/issue-97`, candidate `c675835` (5 commits on top of
main `bfb2d35`), sink: merge.

## Delivered

- `scripts/kaola-codex-compact-hook.py`: user layer — `user-install` / `user-uninstall` /
  `user-status` (`install_blockers`) / `user-emit`, `--codex-home`; one Runner-owned entry
  `kaola-project-runner:user-compact-context` merged by id into `${CODEX_HOME:-~/.codex}/hooks.json`
  with asset copies under `<CODEX_HOME>/kaola-project-runner/hooks/`; `user-emit` prints the
  short conditional payload on every `SessionStart(compact)` and is silent exactly when a legacy
  project-level entry in the session cwd is bound to that same session and root; foreign entries
  preserved, never echoed or copied; malformed JSON and install blockers refused as receipts before
  any write; project-level actions unchanged.
- `templates/codex-host/compact-recovery-user.md`: the 1.2 KB conditional payload (re-read the
  installed `kaola-delegator` / `kaola-project-runner` Skill and continue from records; other
  sessions do nothing; no cwd role guess; no binding table/registry/heartbeat).
- `scripts/install-local.sh`: `--runtime codex` and the legacy Codex default install/uninstall the
  entry when control-plane Skills are in the plan; `--no-orchestrator`, `--skills-dir`, other
  runtimes never touch a `hooks.json`; refusals planned before the first Skill write; prints the
  receipt and the `/hooks` trust + next-session note.
- Docs: `docs/codex-host.md` (rewritten), `docs/api.md`, `README.md`, `docs/README.md`,
  `CHANGELOG.md` (Unreleased).

## Files Changed

`scripts/kaola-codex-compact-hook.py`, `scripts/install-local.sh`, `scripts/validate.sh`,
`templates/codex-host/compact-recovery-user.md`,
`tests/contract/test-issue-97-codex-user-compact-hook.py`,
`tests/contract/test-installer-runtimes.sh`, `tests/contract/test-installer-migration.sh`,
`docs/codex-host.md`, `docs/api.md`, `docs/README.md`, `README.md`, `CHANGELOG.md`.

## Test Coverage

- `tests/contract/test-issue-97-codex-user-compact-hook.py` (21 tests): isolated CODEX_HOME with
  preset Workflow + user-owned hooks — install appends ours and preserves foreign entries/lists,
  byte-identical idempotent reinstall with no backup, fresh home gets only ours, echo-safe status,
  uninstall removes only ours (residue-free, keeps foreign siblings), malformed/null shapes refused
  before any write for all three actions, cross-layer option refusals, empty `--codex-home`
  refused, codex-home refusals ($HOME, /, missing) and CODEX_HOME default, symlinked hooks.json
  escape refused, install blockers are receipts not tracebacks, `user-emit` fires on
  SessionStart(compact) only from any cwd, silent on malformed stdin, defers only to a bound legacy
  project entry (prepare-only, other session, other repo, subdirectory, lost binding/entry,
  migration uninstall all hand back to the user layer), emit modes silent on stray options, emitter
  copy self-contained, payload pins.
- `tests/contract/test-installer-runtimes.sh` (new `test_user_hook_*`): Codex install with foreign
  entries preserved and appended-after order, idempotent reinstall receipt + exact sibling list,
  legacy no-flag default, `--no-orchestrator`, `--skills-dir` (including under the Codex home) and
  four other runtimes never touch hooks.json, uninstall scope, only-ours uninstall leaves no
  hooks.json, partial `--no-orchestrator` uninstall keeps the hook, malformed hooks.json / asset-path
  collision / missing payload template abort before any Skill write.
- `tests/contract/test-installer-migration.sh`: fixture carries the hook tool (Codex destination
  cases keep passing). `tests/contract/test-issue-75-codex-compact-hook.py`: 37/37 unchanged.

## Validation

- `env -u KAOLA_PROJECT_RUNNER_CANONICAL_REPO ./scripts/validate.sh` on `c675835`: exit 0, 0 FAILED /
  0 SKIPPED (log: `evidence/validate-c675835.log`); earlier run on `6e8d6eb` also exit 0.
- `./scripts/render-skills.py --check`: PASS (no Skill template changed). `git diff --check`: clean.
- Recorded: `.cache/final-validation.md` (`verdict: pass`, `validated_candidate_hash`
  `9bda8b05…537f55`).
- Independent review (code-reviewer, clean context) of `6e8d6eb`: 0 blocker/major, 2 minor, 3 nit
  — all fixed in `c675835` and covered by new tests; verdict ACCEPT by the orchestrator after
  reading the diff, findings, and outputs.
- Live UAT (isolated CODEX_HOME, real codex-cli 0.153.4 → 0.155.1, `evidence/codex-user-compact-live/`
  with `FINDINGS.md`): trust flow through `/hooks` (3 new → trusted; later only the modified foreign
  entry re-flagged); ordinary session gets the block and takes no action; two outer Delegator
  sessions in two unrelated repos re-read the installed Delegator Skill after a real `/compact` and
  contact no Host; a Project Runner session re-reads its Skill (its final self-report was cut by the
  operator's `/quit`, `turn_aborted`; the re-read is in the rollout); a repo with a bound legacy
  project entry receives the project block and no user block. Not staged live: an automatic
  mid-turn compaction (same documented Codex path).
- Issue acceptance walk: AC1 (isolated home, only Runner-owned content changes, foreign kept,
  malformed refused) → Python + shell suites and the live install; AC2 (two unrelated repos, real
  compact, re-read; third ordinary session no delegation; single-project Project Runner recovers) →
  sessions A/B, C, D; AC3 (legacy project hook: no duplicate, none lost; trust and new-session
  facts recorded) → session E + contract deferral tests + docs; AC4 (scope limited to Codex
  install/recovery entry, tests, docs; no scheduler/classifier/ledger) → diff scope, no new
  mechanism beyond the entry and the deferral predicate.
- Side effect to record: the live run upgraded the machine's global codex-cli from 0.153.4 to
  0.155.1 (an Enter meant for the directory-trust prompt landed on Codex's update prompt; the
  update was allowed to finish). Rollback if unwanted: `npm install -g @openai/codex@0.153.4`.

## Changed Paths

Reported by `finalize --check` (source-scoped; docs are listed under Files Changed):
`scripts/install-local.sh`, `scripts/kaola-codex-compact-hook.py`, `scripts/validate.sh`,
`templates/codex-host/compact-recovery-user.md`, `tests/contract/test-installer-migration.sh`,
`tests/contract/test-installer-runtimes.sh`, `tests/contract/test-issue-97-codex-user-compact-hook.py`.

## Documentation Docking

`.cache/doc-docking.md`: DOCKED (codex-host.md rewritten; api.md, README.md, docs/README.md,
CHANGELOG.md updated; installer usage text; no impact elsewhere).

## Follow-Up Items

None. User instruction for this run: no follow-up issues; everything found was fixed inside this
issue. The user also asked for a minor release (v0.5.0) after close-out; that is a post-sink
release step, not a Mission List item.

## Readiness

READY — candidate `c675835` validated, reviewed, live-verified, docs docked; close #97 on merge.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-97/.cache/doc-docking.md
- kaola-workflow/archive/issue-97/.cache/final-validation.md
- kaola-workflow/archive/issue-97/.cache/mirror-digest.json
- kaola-workflow/archive/issue-97/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/00-first-session-hooks-need-review.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/01-hooks-review-browser.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/02-hooks-review-list.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/03-hooks-review-hook3-ours.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/04-hooks-after-trust.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/05-isolated-home-hooks-after-install.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/10-repoC-ordinary-after-compact.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/11-repoC-ordinary-probe.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/12-repoC-ordinary-rollout-extracts.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/20-repoA-second-session-startup.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/21-repoA-only-changed-foreign-hook-needs-review.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/22-repoA-turn1-delegator-read.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/23-repoA-probe-after-compact.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/24-repoA-delegator-rollout-extracts.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/30-repoB-delegator-compacted.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/30-repoB-delegator-probe.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/30-repoB-delegator-turn1.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/34-repoB-delegator-rollout-extracts.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/40-repoD-project-runner-compacted.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/40-repoD-project-runner-probe.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/40-repoD-project-runner-turn1.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/44-repoD-project-runner-rollout-extracts.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/50-repoE-legacy-prepare-receipt.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/51-repoE-project-hooks.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/52-repoE-project-hook-needs-review.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/53-repoE-bind-receipt-masked.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/54-repoE-status-after-bind.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/55-repoE-hooks-4-installed-4-active.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/56-repoE-turn1.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/57-repoE-legacy-bound-compacted.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/57-repoE-legacy-bound-probe.txt
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/58-repoE-legacy-bound-rollout-extracts.json
- kaola-workflow/archive/issue-97/evidence/codex-user-compact-live/FINDINGS.md
- kaola-workflow/archive/issue-97/finalization-summary.md
- kaola-workflow/archive/issue-97/mission-list.md
- kaola-workflow/archive/issue-97/workflow-state.md
