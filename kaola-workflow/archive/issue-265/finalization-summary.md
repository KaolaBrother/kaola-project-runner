# Finalization summary — issue 265

## Delivered

Continuous-improvement guidance and scoped validation with timing on `workflow/issue-265` (tip
`d415abab`, fully contained in the cycle candidate `e1ff6d486c16d89c65473ac19ff316811abad3ac`):
bounded `--suite` selection and per-suite timing in `scripts/validate.sh` with the
`TestValidateSuiteSelection` contract in `tests/contract/test-issue-101-validate-watchdog.py`,
repair of interrupted validate cleanup (stop owned writers before sweep), and the integrated
qa-evidence guidance in `templates/orchestrator/references/qa-evidence.md`.

## Validation

classification: chains_green
green: true
mode: final-validation

agent validation recorded and bound to this tree

## Changed Paths

Files this branch changed outside the kaola-workflow/ run-state band:

- AGENTS.md
- README.md
- docs/conventions.md
- scripts/validate.sh
- skills/claude-code-kaola-project-runner/scripts/main-skill-build.json
- skills/codex-kaola-project-runner/scripts/main-skill-build.json
- skills/cursor-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/devin-kaola-project-runner/scripts/main-skill-build.json
- skills/droid-kaola-project-runner/scripts/main-skill-build.json
- skills/dsh-kaola-project-runner/scripts/main-skill-build.json
- skills/grok-kaola-project-runner/scripts/main-skill-build.json
- skills/kaola-project-runner/SKILL.md
- skills/kaola-project-runner/references/qa-evidence.md
- skills/kimi-cli-kaola-project-runner/scripts/main-skill-build.json
- skills/opencode-kaola-project-runner/scripts/main-skill-build.json
- skills/zcode-kaola-project-runner/scripts/main-skill-build.json
- templates/orchestrator/SKILL.md.tmpl
- templates/orchestrator/references/qa-evidence.md
- tests/contract/test-issue-101-validate-watchdog.py

## Known limitations

Timing figures are wall-clock receipts, not budgets; `--suite` selection covers registered suites
only (lane integrity is separately locked by the 264 lane-integrity suite added later in the
cycle).

## Follow-Up Items

None filed.

## Readiness

Accepted within scope; issue closes through the issue-264 merge sink (recorded set
259,263,264,265,266,267,268). No separate sink for this branch.

## Finalize Findings

### residue_unattributed

The residue mirror did not copy the paths below out of the main checkout: this run's HEAD does not contain them. Presence in main, an untracked status, or a neighboring file this run committed is not evidence they belong to this run. Nothing was copied, staged, committed, deleted, reverted or relocated — they remain in the main checkout. Read them before the sink runs: commit what belongs to the run, leave what does not.

Paths left in the main checkout:

- docs/harness-acp-codex-160-live-2026-10-03.md
- docs/harness-acp-compat-2026-10-01.md
- docs/harness-acp-compat-2026-10-03.md
- docs/harness-acp-compat-2026-10-06.md
- docs/harness-acp-reverify-2026-10-01.md

