# Issue #47 finalization

## Delivered

The main Project Runner Skill prefers the run's selected, authorized Kaola Workflow sync/merge when a PR is not required, and does not open a PR merely for handoff when that sink is suitable. If PRs exist, actionable ones take contested suitable capacity while other authorized work continues in parallel across permitted CLIs. A blocked PR keeps an owner and next action without a global hold. Existing acceptance, explicit PR requests, branch protection, stop-intake, selected sink, and write ownership stay in force. Heartbeat carries one compact reminder. No quota, queue, dashboard, state machine, transport change, or hard gate.

## Files Changed

`templates/orchestrator/SKILL.md.tmpl`, `templates/orchestrator/references/heartbeat-skeleton.txt`, generated `skills/kaola-project-runner/SKILL.md` and `skills/kaola-project-runner/references/heartbeat-skeleton.md`, `tests/contract/test-issue-41-orchestrator.py`, `README.md`, `docs/architecture.md`, `docs/conventions.md`, `CHANGELOG.md`.

## Test Coverage

One focused Issue #47 check covers (a) selected authorized Workflow sync/merge when a PR is unnecessary, (b) actionable-PR priority with permitted-CLI parallel work and blocked-PR ownership, (c) heartbeat reflection and worker isolation. Pre-existing Issue #41/#44 tests are unchanged.

## Validation

PASS at `0264b534f245dd8a8210d03245e92dfed97dcb8c`: `./scripts/render-skills.py --check && ./scripts/validate.sh && git diff --check main...HEAD && git diff --check`, exit 0. Receipt: `.cache/final-validation.md`, candidate hash `a10b4642a458478791c0705aeb83d70dc40e4199bfeeb5c2f8fa040a0bfad798`. Live seven-platform tmux smoke was not rerun; this issue is orchestrator guidance, not transport start/send/read/stop. Host wake-up is out of scope. Pre-existing ACP suite `ResourceWarning: unclosed file` noise is unchanged.

Issue #47 acceptance:

- Selected authorized Workflow sync/merge when a PR is not required; no PR merely for handoff — Skill `## Delivery`, heartbeat reminder, README/CHANGELOG, focused test clause (a).
- Actionable open PR gets contested capacity; other authorized work continues on permitted CLIs — Skill, heartbeat, focused test clause (b).
- Blocked PR retains owner and next action without a global hold — Skill and the same test.
- Concise orchestrator instruction; no quota/queue/dashboard/transport/state machine/hard gate — 8-line Skill section; worker isolation; empty worker/golden diff; existing #41/#44 engine prohibitions unchanged.
- Documentation consistency; transport and wake-up out of scope — `.cache/doc-docking.md` DOCKED.

## Changed Paths

Recorded after finalize `--check`.

## Documentation Docking

DOCKED in `.cache/doc-docking.md`.

## Follow-Up Items

None filed. User requested v0.2.2 after #47 closes; the controlling Agent will perform and verify that release after this sink. Not a defect and not a new issue.

## Readiness

Ready for Workflow archive, issue closure, and merge sink. Do not open a PR. Do not create the v0.2.2 tag in this session.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-47/.cache/doc-docking.md
- kaola-workflow/archive/bundle-47/.cache/final-validation.md
- kaola-workflow/archive/bundle-47/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-47/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-47/delivery-report.md
- kaola-workflow/archive/bundle-47/finalization-summary.md
- kaola-workflow/archive/bundle-47/mission-list.md
- kaola-workflow/archive/bundle-47/workflow-state.md
