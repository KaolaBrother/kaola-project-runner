# Documentation docking — issue-213

status: DOCKED
candidate: 3827a56d (workflow/issue-213, rebased onto main 0e952dc6)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| templates/orchestrator/SKILL.md.tmpl | DOCKED (the change) | intro names Host as QA owner beside KW lifecycle ownership; step 3 separates assignment acceptance from project QA with pending unrun checks; step 4 marks finalize/doc docking as lifecycle facts, not QA PASS; Report lists pending QA items |
| templates/orchestrator/references/qa-evidence.md | DOCKED (the change) | Ownership + When-to-check sections, Redundancy trimmed, two new examples; #214's Local-availability/Sol-first computer-use "Who" guidance preserved verbatim through the re-sync |
| templates/orchestrator/references/doc-maintenance.md | DOCKED (the change) | doc accuracy is Host QA judgment; docking record is lifecycle evidence; shared docs checked together at delivery boundary; misleading instructions fixed when they matter |
| templates/orchestrator/references/heartbeat-skeleton.txt | DOCKED | pending integration QA/doc check slot + keep-list entry; #208/#68/#72 pinned tokens intact |
| README.md | DOCKED | Runner-vs-Agent section explains Host QA/doc ownership, pending aggregate checks, KW lifecycle boundary |
| CHANGELOG.md | DOCKED | one Unreleased #213 entry, `Seats: restart not required` (operator-test paths untouched) |
| skills/** | regenerated | `render-skills.py --write` then `--check` PASS, budgets OK (main 17398/17408, qa-evidence 7642/8192) |
| templates/kaola-delegator/** | no-impact | Delegator periodic pace feedback preserved unchanged; it is not a second QA owner |
| worker-profiles.md.tmpl, profile-catalog, quota-packages | untouched | #214's surfaces |
| scripts/, platforms/, templates/budgets.json, templates/grok-golden/, hosts/grok-bot/ | untouched | no transport/CLI/model/budget change; grok-golden frozen |
| docs/architecture.md, docs/api.md, docs/conventions.md, docs/zcode-host.md | no-impact | no API, architecture, setup or transport change; QA ownership lives in the shipped Skill references and README |
| AGENTS.md | no-impact | no new durable project fact or command |
