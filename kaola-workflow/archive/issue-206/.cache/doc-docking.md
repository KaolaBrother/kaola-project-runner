# Documentation docking — issue-206

status: DOCKED
candidate: 5e35d924 (workflow/issue-206, merge of main 273c1314 after #205 landed)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| README.md | DOCKED | reorganized in usage order (f1243180); Worker classes section, class-grouped generated catalog (20 rows, class column), Authorization by class / Choosing a worker / Seat binding and switching (0a30b33b); 55 relative links + anchors resolve |
| CHANGELOG.md | DOCKED | one Unreleased #206 entry for the consolidated scope; notes the non-empty `platforms/` diff means the next release operator test reads `Seats: restart required`; no release section touched |
| templates/orchestrator/** (SKILL, worker-profiles, new profile-catalog, host-startup, zcode-host-dispatch, qa-evidence, heartbeat-skeleton) + templates/SKILL.md.tmpl | DOCKED | this run's primary Host surface; regenerated skills/ |
| templates/kaola-delegator/** (SKILL, host-platforms) | DOCKED | Delegator class extraction and grant relay; #205 KPR-update text integrated at re-sync |
| docs/architecture.md, docs/zcode-host.md | DOCKED | pool sentence replaced with Worker/Elite/Expert wording (test-118 regex still satisfied) |
| docs/api.md, docs/conventions.md | no-impact | no preset-class, pool, or profile statements; release-note rule unchanged |
| platforms/*.yaml | DOCKED | canonical `<tier>_model_class` + four approved profile corrections; model/id/effort/parameters unchanged |
| templates/grok-golden/ | untouched | frozen |
| skills/, hosts/grok-bot/ | regenerated only | render --check PASS, budgets OK; bridge unchanged (2555 B, content stage) |
