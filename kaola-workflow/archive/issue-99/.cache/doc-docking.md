# Documentation docking — issue-99

status: DOCKED
candidate: d300c7a (workflow/issue-99 == main; no source, template, script, or generated-Skill bytes changed)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| README.md | no-impact | design-only run; no public behaviour, command, or entry changed |
| CHANGELOG.md | no-impact | nothing user-visible shipped; the design itself lists the CHANGELOG line the implementation issue must add (design §f.7) |
| docs/api.md, docs/architecture.md, docs/zcode-host.md | no-impact now | the design names the exact paragraphs the implementation must update (§f.7); editing them before the mechanism exists would document behaviour that does not exist |
| templates/orchestrator/, templates/kaola-delegator/ | no-impact now | prose-reduction inventory is part of the design (§f.1–f.6), deliberately not applied: text must change together with the script behaviour it describes |
| templates/grok-golden/ | untouched | frozen |
| skills/, hosts/grok-bot/ | untouched | generated output; render --check PASS on the candidate |

## Run records

- `evidence/heartbeat-auto-bind-design.md` — the deliverable, accepted by the Host with the 2026-09-19 owner rulings recorded in place.
- `mission-list.md` — four items, all done.
