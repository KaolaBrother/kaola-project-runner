# Documentation docking — issue-203

status: DOCKED
candidate: 84b2b5ab (workflow/issue-203)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| docs/api.md | DOCKED | the old "status/observe carry no request provenance" sentence is replaced by the Issue #203 `start_evidence` contract: which receipt fields persist, the inheritance rule, `start_evidence_recorded`/`start_evidence_error`, old records staying readable (commit 84b2b5ab); field names copied from the code, not invented |
| CHANGELOG.md | DOCKED | Unreleased entry states the holder change and "Seats: restart required" (commit 84b2b5ab) |
| templates/SKILL.md.tmpl (+ generated worker SKILL.md) | no-impact | its selection sentence (start reports config_application/effective_selection; observe/status show configOptions currentValue) stays true — the new field adds to it and does not contradict it; the file is the parallel #204 run's surface, so it was left alone by the ownership boundary |
| README.md, docs/architecture.md, docs/conventions.md, docs/zcode-host.md | no-impact | grep for start_selection/effective_selection/model_selection finds nothing; no documented status/observe field list to update |
| templates/grok-golden/ | untouched | frozen |
| skills/, hosts/grok-bot/ | regenerated only | skills/*/scripts copies of kaola-acp.py and kaola-acp-holder.py; hosts unchanged; render --check PASS |
