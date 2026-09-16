# Finalization summary — bundle-52 (Issue #52)

Candidate: `291feb71bc9c6da8b4779fb8945ebe0e2ac775f7` on `workflow/bundle-52`, based on `main` `07a84dc2188b7c511b1dba57ee83094fa5992400`. Sink: merge. Closure decision: close #52 after the controlling Agent accepted this frozen candidate (2026-09-16). Do not publish a release. Do not touch `issue-53`, `issue-56`, their worktrees, or PR #55.

## Delivered

Ordinary Workflow-backed work starts the runtime worker at the consuming project's canonical Git root and asks that CLI's main conversation to invoke installed `workflow-next`, so the worker's Workflow creates or recovers the child worktree. Linked-worktree starts, outer preparation, and existing-run recovery remain Agent decisions on both PTY and ACP. Adapters and runtime scripts have no hardcoded `.kw/worktrees` refusal. Path shape is not a security boundary.

## Files Changed

Templates: `templates/orchestrator/SKILL.md.tmpl`, `templates/orchestrator/references/workflow-worktree.md`, `templates/SKILL.md.tmpl`, `templates/references/transport.md.tmpl`. Generated Skills and the new orchestrator reference. Docs: README, architecture, conventions, API, docs index, AGENTS, CHANGELOG. Tests: `tests/contract/test-issue-52-workflow-worktree.py` plus `scripts/validate.sh` registration. `hosts/grok-bot/` and `templates/grok-golden/` unchanged.

## Test Coverage

- `tests/contract/test-issue-52-workflow-worktree.py`: 9/9 on the frozen candidate (template/doc consistency, no `.kw/worktrees` refusal, PTY and ACP accept a linked worktree Git top-level, behavioral-example wording).
- Full `./scripts/validate.sh` on `291feb71`: exit 0, including renderer check, generated-skill acceptance, orchestrator/progressive-disclosure/Grok Bot host suites, and Issue #50/#51 integration.
- `./scripts/render-skills.py --check`: PASS. `git diff --check origin/main...HEAD`: clean.

## Issue statement coverage

- Orchestrator and worker guidance state root-start plus in-session Workflow consistently: templates, generated Skills, README/docs/AGENTS; tests pin the markers.
- Linked-worktree starts, outer preparation, existing-bundle recovery are Agent decisions rather than transport gates: stated in orchestrator reference, worker Skill, README; `authorizes_gate` scan and adapter scan.
- No hardcoded `.kw/worktrees` refusal: transport-script scan; linked worktree `--repo` accepted by `kaola-tmux.sh` Git-root check and `kaola-acp.py resolve_repo`.
- Behavioral examples: README and `workflow-worktree.md` Normal path and Evidence-backed exception; this run itself started at the canonical root and let Workflow create `.kw/worktrees/bundle-52`.
- Concurrent sessions: documented for multiple exact sessions at one canonical root with distinct Workflow worktrees.
- PTY and ACP identical decision authority: stated and tested.
- Receipts remain bounded facts; Workflow records remain lifecycle evidence: no new receipt fields or transport classification.
- Migration of a session already in a child worktree is advisory: documented.
- Non-goals held: no `runtime-tmux.sh` rejection, no Workflow-mode classifier, no Grok Bot host UAT (Issue #56).

## Validation

Consumer has no `test:kaola-workflow:*` chains (`chains_config_missing`). From the candidate worktree, `./scripts/validate.sh` exited 0 and `./scripts/render-skills.py --check` passed. `.cache/final-validation.md` records `verdict: pass`, `validation_command: ./scripts/validate.sh`, `validated_candidate_hash: 01ebb9e3d08ba0a48a5f0b41fbb00090dfe88f9c7a88135c4e1c479faea9506a`. `finalize --check --json`: `ok=true`, `validation=chains_green`, `reasons=[]`, `dirty_paths=[]`.

## Changed Paths

`finalize --check` scoped `changed_paths` to:

AGENTS.md; `scripts/validate.sh`; generated Claude/Codex/Cursor/Devin/Grok/Kimi/OpenCode/ZCode worker `SKILL.md` and `references/transport.md`; orchestrator `SKILL.md` and `references/workflow-worktree.md`; `templates/SKILL.md.tmpl`; `templates/orchestrator/SKILL.md.tmpl`; `templates/orchestrator/references/workflow-worktree.md`; `templates/references/transport.md.tmpl`; `tests/contract/test-issue-52-workflow-worktree.py`.

README.md, docs/README.md, docs/api.md, docs/architecture.md, docs/conventions.md and CHANGELOG.md are in the candidate commit and were inspected and docked; they were not listed in the transaction `changed_paths` array. The transaction array is the authoritative scoped finding.

## Documentation Docking

`.cache/doc-docking.md`: DOCKED. README, architecture, conventions, API, AGENTS and CHANGELOG describe the actual default. No further public-behavior edits. Unreleased changelog stays unreleased; this run does not tag or publish.

## Acceptance legs

- Automated/local: PASS on frozen `291feb71`.
- Independent controlling-Agent diff/test review: accepted 2026-09-16.
- Manual/live tmux smoke: not required for this documentation/template change; the live Workflow claim of this run is the normal-path behavioral example.
- Unexecuted: no release, installer republish, or Grok Bot host UAT.

## Follow-Up Items

None filed. Issue #56 continues to own Grok Bot host install/UAT. Issue #53 remains a separate active run. Stale PR #55 is out of scope.

## Readiness

READY for the Workflow finalize transaction, archive, merge sink, and Issue #52 closure. No release.

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/bundle-52/.cache/doc-docking.md
- kaola-workflow/archive/bundle-52/.cache/final-validation.md
- kaola-workflow/archive/bundle-52/.cache/mirror-digest.json
- kaola-workflow/archive/bundle-52/.cache/origin/selection-record.json
- kaola-workflow/archive/bundle-52/delivery.md
- kaola-workflow/archive/bundle-52/finalization-summary.md
- kaola-workflow/archive/bundle-52/mission-list.md
- kaola-workflow/archive/bundle-52/workflow-state.md
