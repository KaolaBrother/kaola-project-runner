# Finalization Summary — issue #224

## Delivered

Scoped wording repair of the two #223 audit findings. No new schema, state
engine, or prompt wall. No install, tag, release, or CHANGELOG edit.

- `templates/orchestrator/SKILL.md.tmpl` Defaults "Allowed CLIs": the six
  Worker-pool presets are default-authorized permission (no per-seat, count, or
  priority approval; outside the cap). Elite needs an explicit grant. Expert
  needs per-task permission. Default pool authorization is permission, not a
  preference over suitable authorized Elite. The old "dispatches the Worker
  pool" routing sentence is gone. The Count row keeps "Named CLI without a
  count: one; it bounds live processes." The redundant tail "Pool presets need
  no count and sit outside it." moved into that Allowed CLIs cell so the main
  Skill stays at the locked 17408 B ceiling. Authorization still says the six
  presets are default-authorized outside that cap.
- `templates/orchestrator/references/heartbeat-skeleton.txt`: excluded or
  unavailable presets are omitted from eligible `rows` only and are not
  dispatchable. Paused, revoked, and excluded facts stay compactly inside
  `authorization`. Compaction or recovery cannot restore a revoked grant;
  restoration is only by owner reauthorization.

Generated `skills/kaola-project-runner/SKILL.md`, `heartbeat-skeleton.md`, and
the ten worker `main-skill-build.json` stamps follow that render.

## Candidate

`workflow/issue-224` at `1460771f858b7d1ea9ad7635508f70bb1dea1a5e` (base
`543b50d8`). Host acceptance received for this exact commit.

## Evidence

- `./scripts/render-skills.py --check`: PASS, budgets OK (main Skill
  17408/17408 B, heartbeat-skeleton 8047/8192 B). Host independently
  re-verified the same command on this commit.
- Focused contract rerun on the changed surfaces: 225 tests OK
  (`test-progressive-disclosure`, `test-issue-218-preset-ids`,
  `test-issue-118-seat-cap`, `test-issue-68-heartbeat-snapshot`,
  `test-issue-72-session-naming`, `test-issue-65-host-contract`,
  `test-issue-88-permission-defaults`, `test-issue-94-zcode-native-skill-entry`,
  `test-issue-41-orchestrator`, `test-zcode-heartbeat-contract`,
  `test-issue-49-grok-bot-host`). No assertion text changed.
- Recorded evidence: `kaola-workflow/issue-224/.cache/final-validation.md`
  (`verdict: pass`, command `./scripts/render-skills.py --check`).
- `kaola-workflow-run-chains.js --project issue-224`: `chains_config_missing`
  (no `package.json` `test:kaola-workflow:*` scripts). Consumer gate is the
  recorded final-validation file.

## Known failures / unverified scope

- `./scripts/validate.sh` was not rerun. The issue limited this run to the
  affected surfaces; #222/#223 suite evidence is reused for the rest.
- Grok Bot bridge still renders "unpinned (not saveable)", unchanged from
  `main`. A pin, tag, release, and CHANGELOG entry stay owner-gated for
  v0.6.9 and are outside #224.
- No install (`install-local.sh` not authorized).

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
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt

## Follow-Up Items

None filed. No run-discovered defect. v0.6.9 release work remains the
separately owner-gated item already named by #224, not a new issue.

## Final readiness

Ready: accepted by Host; merge sink, close #224, archive.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-compat-2026-09-25.md
- docs/harness-acp-compat-2026-09-26.md
- docs/harness-acp-compat-2026-09-29.md

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-224/.cache/final-validation.md
- kaola-workflow/archive/issue-224/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-224/finalization-summary.md
- kaola-workflow/archive/issue-224/mission-ledger.jsonl
- kaola-workflow/archive/issue-224/workflow-state.md
