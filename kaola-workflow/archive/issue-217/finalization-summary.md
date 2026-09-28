# Finalization summary — issue-217

## Delivered

Issue #217 (Keep Host and Delegator heartbeats as structured current-state snapshots), commit
69b60f4d on `workflow/issue-217`, accepted by the Host. Four owner corrections are reflected:

1. Fixed procedure lives in the installed Skills; each recurring prompt is the Skill entry plus one
   compact current JSON object (`templates/orchestrator/references/heartbeat-skeleton.txt`,
   `templates/kaola-delegator/references/snapshot.md`).
2. The Host carrier stays `<repo>/.kaola/heartbeat-prompt.json` with its Skill entry, event metadata
   and envelope; only `body` changed (`project`, `authorization`, `active`, `pending`, `recovery`).
3. The Delegator's one state file is `<repo>/.kaola/delegator-heartbeat.json` on the bound target for
   every outer runtime (Grok Bot via the existing locator), one writer per file, static timer prompt.
4. The Delegator JSON carries `cadence`, `timer_owner`, `day_start` (`reconcile_then_open_intake`),
   `day_end` (`pause_new_claims_keep_inflight`; confirmed only by Host acknowledgment plus claim
   evidence, never send admission) and an owner-set optional `final_stop`; any outer platform rebuilds
   its one native timer from `cadence`, retiring the previous timer first. The Host acknowledges a
   daily pause and opens no new claim until intake reopens.

Acceptance read-through: context-flush recovery from current JSON plus source pointers; a changed
grant replaces the old value; unresolved cross-issue QA stays in `pending` until a Host verdict; a
closed issue leaves `active`; the Delegator timer prompt stays static.

## Files Changed

Templates: `templates/orchestrator/{SKILL.md.tmpl,references/heartbeat-skeleton.txt,references/host-startup.md.tmpl,references/qa-evidence.md,references/zcode-host-dispatch.md.tmpl}`;
`templates/kaola-delegator/{SKILL.md.tmpl,references/handoff.md.tmpl,references/host-platforms.md.tmpl,references/snapshot.md}`.
Generated: matching `skills/kaola-project-runner/`, `skills/kaola-delegator/` files and ten
`main-skill-build.json`. Docs: `CHANGELOG.md`, `docs/zcode-host.md`. Test:
`tests/contract/test-issue-74-kaola-delegator.py`.

## Test Coverage

- `tests/contract/test-issue-74-kaola-delegator.py`: 188 assertions, 0 failed (snapshot file, identity
  via Runner status, single writer, cadence/day boundary/timer handoff terms).
- `tests/contract/test-progressive-disclosure.py`: 15 OK (new reference linked; budgets).
- `./scripts/render-skills.py --check`: PASS (re-run by Host).
- `./scripts/validate.sh`: rc=0 on the committed tree (`/tmp/kpr217-validate.log`; bash 3.2 watchdog
  skips only; `residual_pids: []`).

Rendered sizes (base 4a89199d → after; budgets unchanged): Delegator SKILL 4085→4091/4096;
host-platforms 7510→7373/8192; snapshot.md new 2567/8192; handoff 8181→8190/8192; KPR SKILL
17406→17404/17408; heartbeat-skeleton 3850→5497/8192; Grok Bot bridge 2555/2560.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- CHANGELOG.md
- docs/zcode-host.md
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-delegator/SKILL.md
- skills/kaola-delegator/references/handoff.md
- skills/kaola-delegator/references/host-platforms.md
- skills/kaola-delegator/references/snapshot.md
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/heartbeat-skeleton.md
- skills/kaola-project-runner/references/host-startup.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kaola-project-runner/references/zcode-host-dispatch.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/kaola-delegator/SKILL.md.tmpl
- templates/kaola-delegator/references/handoff.md.tmpl
- templates/kaola-delegator/references/host-platforms.md.tmpl
- templates/kaola-delegator/references/snapshot.md
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/heartbeat-skeleton.txt
- templates/orchestrator/references/host-startup.md.tmpl
- templates/orchestrator/references/qa-evidence.md
- templates/orchestrator/references/zcode-host-dispatch.md.tmpl
- tests/contract/test-issue-74-kaola-delegator.py

## Documentation Docking

DOCKED — `.cache/doc-docking.md`.

## Follow-Up Items

None filed. `handoff.md` sits at 8190/8192 bytes; noted for future edits, not a defect.

## Readiness

Ready: Host acceptance recorded; no release, tag or install.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-217/.cache/doc-docking.md
- kaola-workflow/archive/issue-217/.cache/final-validation.md
- kaola-workflow/archive/issue-217/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-217/finalization-summary.md
- kaola-workflow/archive/issue-217/mission-ledger.jsonl
- kaola-workflow/archive/issue-217/workflow-state.md
