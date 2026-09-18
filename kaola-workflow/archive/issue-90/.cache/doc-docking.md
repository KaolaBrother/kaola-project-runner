# Documentation docking — issue-90 (candidate c5155e5668d225eb5dbf209205679af4d9abea51)

Checked against the AGENTS.md Documentation Map and the changed public behavior: the ZCode Host
worker-event carrier's admission/confirmation ordering and its confirmed-`event_id` duplicate
answer. No CLI surface, flag, command, environment variable, or installer destination changed.

| file | verdict | reason |
|---|---|---|
| `docs/zcode-host.md` | UPDATED | The carrier contract lives here. "Confirmation and resume" now states that admission and the marking of what it delivered are one lock hold; that the confirmation is written before the events leave the pending list; and that a confirmed `event_id` retry is answered `duplicate`/`confirmed` for as long as the event log RETAINS that confirmation — cache entries whose record has rotated away stop being evidence — rather than for a fixed number of ids. |
| `CHANGELOG.md` | UPDATED | One Unreleased entry describing the user-visible behavior: one worker event is one Host prompt and one confirmation; a confirmed retry does not re-prompt; the bound is the retained log; the confirmation is durable before it is answerable. |
| `README.md` | NO IMPACT | Four-tier entry, overview, and usage. Carries no worker-event carrier detail (`grep -n "worker_event\|worker-event" README.md` → no hits) and no entry-point or usage change to describe. |
| `docs/api.md` | NO IMPACT | Documents the `kaola-acp` CLI ops (`preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, `view`, `follow`) and the `heartbeat_host` receipt fields. `worker_event` is a holder-to-holder socket op with no CLI surface, and no documented CLI receipt field changed. |
| `docs/architecture.md` | NO IMPACT | Describes layering and the shared-template generation model, neither of which changed. |
| `templates/orchestrator/references/zcode-host-dispatch.md.tmpl` | NO IMPACT, VERIFIED CONSISTENT | States "Duplicate `event_id`s collapse" and "unconfirmed events are redelivered at least once — keep each pass idempotent". Both remain exactly true, and the candidate removes the fixed-256-id exception that had made the first of them conditional. The file is pinned by the Issue #65 contract and sits at its byte budget, so adding text here would be a regression, not docking. |
| `skills/**`, `hosts/grok-bot/**` | REGENERATED | Generated output; `./scripts/render-skills.py --write` then `--check` PASS, and all nine `skills/*/scripts/kaola-acp-holder.py` verified byte-identical to `scripts/kaola-acp-holder.py`. |

Signatures/receipt shapes transcribed from the implementation, not invented: the duplicate answer is
`{"event_id": ..., "duplicate": true, "confirmed": true, "pending": N}` (`scripts/kaola-acp-holder.py`,
`op_worker_event`); record kinds are `worker_event`, `worker_event_delivered`,
`worker_event_confirmed`, `worker_event_overflow`, `worker_event_overflow_confirmed`,
`worker_event_restored`.

DOCKED
