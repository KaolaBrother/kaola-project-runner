# Finalization Summary — issue #223

## Delivered

The Host heartbeat `authorization` now directly carries eligible worker Class
and profile context, through the existing source templates only (no new
schema, registry, scheduler, dispatch gate, appendix, or parallel state file):

- `templates/orchestrator/references/heartbeat-skeleton.txt`: the "rows or
  pointer" wording is removed. `authorization` must contain `classes` (the
  three shared Expert/Elite/Worker definitions, written once; they grant no
  seats) and `rows` (one per locally available, currently authorized preset:
  exact id, class, catalog one-line profile verbatim, grant/count/state). A
  pointer may name the source but never replaces them. Expert rows only with a
  task grant; excluded/unavailable presets not listed or dispatchable; the
  Droid seat recorded once, not split per tier; one row per pool preset, not
  per process; default pool authorization is permission, not preference over
  suitable authorized Elite; owner priority once; rebuild at intake/recovery,
  update only on actual grant/profile/install/state change, no per-beat or
  per-dispatch rescan, no full-catalog injection, no history. The compact
  example shows `classes` plus an Elite `droid/opus` row (shared Droid seat)
  and a Worker `claude-code/sonnet` row with catalog-exact profiles.
- `templates/orchestrator/references/worker-profiles.md.tmpl` and
  `templates/orchestrator/SKILL.md.tmpl`: the heartbeat holds the rows and
  Class definitions directly; pool default stated as permission, not
  preference. Minor wording trims kept byte budgets unchanged.
- `templates/kaola-delegator/references/snapshot.md`: the inquiry audits that
  the Host `authorization` holds the definitions and ID/Class/profile rows,
  corrects through the same Host, and never writes Host JSON, copies rows, or
  selects workers.
- `tests/contract/test-issue-218-preset-ids.py`: the one obsolete example
  assertion replaced by a focused rows/definitions test.

## Candidate

`workflow/issue-223` at `5e601cdbe5fe6149cc4bf103965c42f8cf4337d4` (base
`8b9de792`). Host acceptance received for this exact commit.

## Evidence

- `./scripts/render-skills.py --check`: PASS, budgets OK (main Skill
  17395/17408 B, worker-profiles 8176/8192 B, heartbeat-skeleton 7894/8192 B).
- `python3 tests/contract/test-issue-218-preset-ids.py`: 15/15 OK.
- `./scripts/validate.sh`: rc=0 (worker run and independent Host rerun); log
  `/tmp/kpr-223-validate.log`.
- Semantic QA: generated `heartbeat-skeleton.md` contains each of the three
  definitions exactly once, Elite and Worker example rows whose class/profile
  match `profile-catalog.md`, and no pointer phrase.
- Recorded evidence: `kaola-workflow/issue-223/.cache/final-validation.md`.

## Known failures / unverified scope

- bash 3.2 on this machine: validate.sh watchdog skipped with named receipts
  (#151).
- Grok Bot bridge renders "unpinned (not saveable)", identical on `main`
  before this change; a pin is a release-time duty (v0.6.9), not part of #223.
- No live Host heartbeat was rewritten by this run; populating the live
  snapshot is Host operation, not product change.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/worker-profiles.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/worker-profiles.md.tmpl
- tests/contract/test-issue-218-preset-ids.py

## Follow-Up Items

None filed. The outer Delegator audit of the integrated #222+#223 candidate
and the v0.6.9 release (pins, Seats statement) remain owner-scheduled per the
issue's delivery boundary.

## Final readiness

Ready: accepted by Host; merge sink, close #223, archive.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-223/.cache/final-validation.md
- kaola-workflow/archive/issue-223/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-223/finalization-summary.md
- kaola-workflow/archive/issue-223/mission-ledger.jsonl
- kaola-workflow/archive/issue-223/workflow-state.md
