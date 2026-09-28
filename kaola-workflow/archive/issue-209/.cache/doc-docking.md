# Documentation docking — issue-209

status: DOCKED
candidate: 18056e3d (workflow/issue-209, rebased onto main 3bbdb373)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| CHANGELOG.md | DOCKED | one Unreleased #209 entry; states `Seats: restart not required` (operator-test paths untouched) |
| README.md | no-impact | no API, setup, or usage-flow change; nothing to reorder or add |
| docs/architecture.md, docs/zcode-host.md, docs/api.md, docs/conventions.md | no-impact | no behavior changed — three test assertions were corrected to match wording #204/#208 already shipped; the wording itself is untouched |
| templates/orchestrator/**, templates/kaola-delegator/**, templates/SKILL.md.tmpl | untouched | scope is test-side only; no template or reference edited (verified via `git diff --stat` on the delivered commit) |
| tests/contract/test-issue-65-host-contract.py, tests/contract/test-issue-162-upgrade-safety.py | DOCKED (the actual change) | 3 pinned-string assertions corrected to the current exact source wording; each still pins the same real behavior — not weakened or deleted |
| platforms/*.yaml, scripts/ | untouched | no transport, CLI, permission, or model change |
| templates/grok-golden/, hosts/grok-bot/, templates/budgets.json | untouched | frozen / bridge unchanged / budgets not touched |
| skills/ | untouched | no template changed, so no regeneration needed; `render-skills.py --check` PASS regardless |
