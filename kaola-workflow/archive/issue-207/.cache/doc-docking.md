# Documentation docking — issue-207

status: DOCKED
candidate: 3720111d (workflow/issue-207, based on main 61f75a68)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| README.md | DOCKED | new "Quota exhaustion" subsection under Select workers (before "Authorization before a new Host"): confirmed-vs-ambiguous evidence, shared pool, Host→one ZCode / already-ZCode asks, Expert/Elite/Worker, no replacement asks, no login |
| CHANGELOG.md | DOCKED | one Unreleased #207 entry; states `Seats: restart not required` for this change (operator-test paths untouched) |
| templates/orchestrator/** (SKILL pointer, references/quota-packages.md §Confirmed exhaustion, worker-profiles pointer) | DOCKED | Host-side recovery by class; regenerated skills/ |
| templates/kaola-delegator/** (SKILL pointer, references/host-brick.md §Quota-exhausted Host) | DOCKED | Delegator-side Host replacement; regenerated skills/ |
| docs/architecture.md, docs/zcode-host.md, docs/api.md, docs/conventions.md | no-impact | no quota-exhaustion recovery, login-recovery or Host-replacement-by-class statements (grep exhaust/relogin/bricked outside protected docs: 1 hit, docs/api.md Droid Core catalog fact "after Standard Usage is exhausted" — a pool fact, not recovery guidance); quota-packages CLI contract unchanged |
| platforms/*.yaml, scripts/ | untouched | no transport, CLI, permission or model change |
| templates/grok-golden/, hosts/grok-bot/, templates/budgets.json | untouched | frozen / bridge unchanged 2555 B / budgets not raised |
| skills/ | regenerated only | render --check PASS, budgets OK |
