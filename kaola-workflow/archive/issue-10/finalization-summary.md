# Finalization Summary

## Delivered

- Removed the normal relay quiesce/prepare/fence/submit transaction that wedged live Claude and
  Cursor sessions.
- Replaced it with read-only live observation followed by one direct authenticated relay transfer.
- Kept exact-session, repository, pane, relay, child, payload, terminal-control, and exact-stop
  protections.
- Made unknown partial writes truthful with `mutation_performed:null` and made legacy relay restart
  an Agent-selected exact-session action.
- Applied the shared contract to all five active platform Skills without changing frozen Grok golden
  evidence or claiming unexecuted Kimi/OpenCode live success.

## Files Changed

- Shared relay/runtime: `scripts/kaola-pane-relay.py`, `scripts/kaola-tmux.sh`.
- Shared Skill contracts: `templates/SKILL.md.tmpl`, `templates/references/transport.md.tmpl`.
- Generated active Skills under `skills/*-kaola-project-runner/`.
- Direct-transport and compatibility acceptance under `tests/contract/` plus the integration runner.
- Current documentation: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/api.md`, and
  `docs/conventions.md`.

## Test Coverage

- Direct transport contract: 5/5 pass.
- Observation contract: 16/16 pass.
- Evidence-first, guarded action, terminal-control, long wrapped send, Claude decision, relay PTY,
  escaped-descendant, generic tmux, adapter, Cursor authority, process identity, Grok compatibility,
  Grok isolation, installer migration, and live-smoke adapter suites pass.
- Full acceptance reduced to three failure classes independently reproduced on clean `origin/main`:
  the existing Cursor lifecycle policy check, legacy force-stop wording check, and Issue #8 model
  policy suite. They are not Issue #10 regressions and were not used to broaden this change.

## Validation

- Final command: `./scripts/validate.sh` — PASS at commit `f6d2839`.
- Final candidate hash: `b4adafd02b80bf82813b9533db78ae1884e020c52fe27dda9a745c9b3dabd84d`.
- `templates/grok-golden/` tree hash remained
  `b181df535082e7598950b126094e88bf7a6c11af4e500dd0d2f55f8854fba8fd`.
- Review verdict: approve after correcting uncertain partial-write receipts.

## Changed Paths

- `scripts/`
- `templates/`
- `skills/`
- `tests/contract/`
- `tests/test-issue-1-acceptance.sh`
- `README.md`
- `CHANGELOG.md`
- `docs/`

## Mission List

4 done / 0 in-flight / 0 todo. Every dispatched mission has one immutable result.

## Documentation Docking

DOCKED. Current normative docs and all five generated active Skill references describe the direct
transport contract. Dated live-smoke reports remain historical evidence. Scheduler, recurring-loop,
and external Codex orchestration policy remain outside the Runner Skill.

## Run gaps

Gap sweep found no newly discovered independent causal class. The three full-suite failures are
pre-existing on `origin/main` and already outside this issue's measured change frontier.

## Follow-Up Items

- After sink, reinstall from stable main so local Skill symlinks resolve to merged bytes.
- Notify Codex thread `01a05662-89ed-7fe1-81d8-aa267bf2ee2a` to preserve completed work and adopt the
  new Skill without repeating tasks; if its existing relay is old, restart only that exact session at
  a safe Agent-selected mutation boundary.

## Final Readiness

READY FOR FINALIZE AND SINK.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-10/.cache/doc-docking.md
- kaola-workflow/archive/issue-10/.cache/doc-updater.md
- kaola-workflow/archive/issue-10/.cache/final-issue-comment.md
- kaola-workflow/archive/issue-10/.cache/final-validation.md
- kaola-workflow/archive/issue-10/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-10/.cache/run-gaps.json
- kaola-workflow/archive/issue-10/finalization-summary.md
- kaola-workflow/archive/issue-10/mission-list.md
- kaola-workflow/archive/issue-10/workflow-state.md
