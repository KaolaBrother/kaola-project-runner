# Documentation docking — issue-204

status: DOCKED
candidate: f0cd8715 (workflow/issue-204, merge of main 34560d5d)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| CHANGELOG.md | DOCKED | Unreleased entry states the explicit-tier-selection and receipt-reconciliation change (commits 4af3686b/ac7ab398); reordered above the #203 entry so newest lands first, no release section touched |
| templates/orchestrator/SKILL.md.tmpl, templates/SKILL.md.tmpl, templates/orchestrator/references/{host-startup,zcode-host-dispatch}.md.tmpl (+ generated kaola-project-runner and worker SKILL.md/references) | DOCKED | this run's own primary surface; wording verified against the issue's 7 acceptance cases in-conversation before commit |
| docs/api.md | no-impact | grep for `model_selection`/`config_application`/`effective_selection`/`start_evidence` (the fields this run's reference text cites) shows #203 kept the same field names and only added `start_evidence` as an additional status/observe carrier — this run's text still reads the `start` receipt's own fields, unchanged by #203; no rewrite needed |
| README.md | no-impact | the `--tier`/default-resolution table (~line 558-574) documents the CLI's own omitted-tier mechanism, which this run did not change; it does not state Host dispatch policy, so it does not contradict the new Host guidance |
| docs/architecture.md, docs/conventions.md, docs/zcode-host.md | no-impact | grep for "Use Runner default start" / "names that preset" finds nothing outside the edited templates |
| templates/grok-golden/ | untouched | frozen |
| skills/, hosts/grok-bot/ | regenerated only | `render-skills.py --write`/`--check` PASS after the #203 resync; grok-bot bridge unchanged (content stage, unpinned, 2555 B) |
