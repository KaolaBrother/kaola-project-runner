# Documentation docking — issue-217

| Checked | Result | Reason |
|---|---|---|
| `templates/orchestrator/references/heartbeat-skeleton.txt` (+ generated `heartbeat-skeleton.md`) | DOCKED | Host `body` is one current-state JSON object; field meanings; write-back rules; daily claim-pause acknowledgment |
| `templates/orchestrator/SKILL.md.tmpl`, `host-startup.md.tmpl`, `qa-evidence.md`, `zcode-host-dispatch.md.tmpl` (+ generated) | DOCKED | Carrier/body wording aligned; sweep line stays in the reply only; pending QA survives in `pending` |
| `templates/kaola-delegator/SKILL.md.tmpl`, `references/handoff.md.tmpl`, `references/host-platforms.md.tmpl`, new `references/snapshot.md` (+ generated) | DOCKED | One Delegator file `<repo>/.kaola/delegator-heartbeat.json`, static timer prompt, cadence/timer_owner/day_start/day_end/final_stop, timer handoff |
| `docs/zcode-host.md` | DOCKED | Heartbeat body description updated |
| `CHANGELOG.md` | DOCKED | Unreleased entry for #217, `Seats: restart not required` |
| `README.md`, `docs/architecture.md`, `docs/api.md` | no impact | No command, API, setup, or architecture change; guidance/templates only |
| `hosts/grok-bot/` | no impact | Bridge unchanged (2555 B); Grok Bot reaches the file through the existing locator |

Status: DOCKED
