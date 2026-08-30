# Finalization — Summary: issue-8

## Delivered

Established per-run main-model selection for Grok CLI, Claude Code, OpenCode, Kimi CLI, and Cursor CLI: explicit user override first, otherwise the repository-declared Runner default. Added readable-catalog resolution, literal argv construction, runtime-owned actual evidence, last-known evidence persistence, generated Skill parity, and the evidence-not-hardgate lifecycle boundary.

## Files Changed

Shared runtime scripts and observation schema; all five adapters/manifests; Skill templates, renderer, and generated Skills; model-policy behavioral acceptance; root documentation and Issue #8 design/live evidence.

## Test Coverage

`tests/contract/test-model-policy.sh` covers five platforms across default, user override, ambient saved picker, unavailable model, mismatch, unreadable evidence, new/continue/resume, malicious literal input, shell-preamble false positives, and scrolled-frame last-known evidence. The repository-wide validation surface also covers generated output, lifecycle, relay, PTY, guarded actions, terminal payloads, process identity, Grok isolation, and all adapters.

## Validation

Consumer validation receipt recorded `verdict: pass` for `python3 scripts/render-skills.py --write && python3 scripts/render-skills.py --check && git diff --check && ./scripts/validate.sh`, bound to candidate hash `a5230f277f1aec2460324170756bca69414a1f8476ae9fc9c1ad72b01f86bd46` in the Issue #8 worktree. Final output included `Issue #8 model-policy acceptance: PASS` and `Issue #1 acceptance: PASS`.

## Changed Paths

The finalize transaction will append its measured path inventory here.

## Mission List

All five missions are `done` with immutable PASS results: runtime measurement, independent baseline RED acceptance, shared/five-adapter implementation, generated/documentation docking, and repository-wide plus exact-tmux live validation.

## Documentation Docking

`kaola-workflow/issue-8/.cache/doc-docking.md` records `DOCKED`; public behavior, API, architecture, conventions, changelog, runtime limitations, side effects, and live evidence are represented with no `.env.example` impact.

## Run gaps

The sweep reported `sweptClasses: []`; no run-discovered defect requires a follow-up issue.

## Follow-Up Items

None. Claude backend execution can be re-smoked when an authenticated account is available, but Issue #8's authorized acceptance boundary was command receipt plus TUI model selection and this is not deferred implementation work.

## Status: ARCHIVED AFTER FINAL GIT GATE

## Sink Findings

post_rebase_tests: skipped

archived_paths:
- kaola-workflow/archive/issue-8/.cache/doc-docking.md
- kaola-workflow/archive/issue-8/.cache/doc-updater.md
- kaola-workflow/archive/issue-8/.cache/final-validation.md
- kaola-workflow/archive/issue-8/.cache/origin/selection-record.json
- kaola-workflow/archive/issue-8/.cache/run-gaps.json
- kaola-workflow/archive/issue-8/finalization-summary.md
- kaola-workflow/archive/issue-8/mission-list.md
- kaola-workflow/archive/issue-8/workflow-state.md
