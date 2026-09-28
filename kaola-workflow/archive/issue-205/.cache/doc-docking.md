# Documentation Docking - issue-205

status: DOCKED
candidate: 632e0ed2 (workflow/issue-205, resynced from main 9ce7e672)

## Checked against the AGENTS.md documentation map

| Surface | Result | Reason |
|---|---|---|
| `templates/kaola-delegator/SKILL.md.tmpl`, `templates/kaola-delegator/references/host-platforms.md.tmpl`, and generated Delegator Skills | DOCKED | The concise update pointer and its detailed existing reference are the shipped guidance; wording covers all five issue requirements and four acceptance cases. |
| `templates/orchestrator/references/heartbeat-skeleton.txt` and generated heartbeat reference | DOCKED | It updates the existing effective-now snapshot rule and preserves current seat, restriction, frontier, and in-flight locator facts; no new heartbeat mechanism was added. |
| `README.md` | no-impact | The entry layers, setup, installation, and user workflow are unchanged. |
| `CHANGELOG.md` | no-impact | No release or tag is part of this run; the changed Skill content is generated from the templates and this run does not create a release entry. |
| `docs/api.md` | no-impact | No API, protocol, receipt field, or transport behavior changed. |
| `docs/conventions.md` | no-impact | No release or repository convention changed. |
| `docs/architecture*.md` and `docs/zcode-host.md` | no-impact | No runtime architecture, transport, or Host lifecycle mechanism changed. |
| `AGENTS.md` | no-impact | Commands, setup, validation policy, and project constraints are unchanged. |
| `templates/grok-golden/` and `hosts/grok-bot/` | untouched / regenerated unchanged | Frozen golden content was untouched; `render-skills.py --write` reports the bridge at 2555 B, content stage, unpinned, unchanged. |

No invented signatures, fields, or schemas. No release, install, or tag.
