# Delegator snapshot

On every runtime the Delegator's one state file is
`<repo>/.kaola/delegator-heartbeat.json` on the bound target (Grok Bot: via its
locator); only it writes that file, and only the Host writes
`heartbeat-prompt.json`. One compact JSON object of current facts, never a
history:

- `project`; `host` (platform, exact `--session`, `holder_instance_id`,
  attested native id); `authorization` a safe handoff needs — each granted,
  paused, or revoked seat named by its exact catalog preset id
  (`<platform>/<tier>`, e.g. `cursor-cli/default` vs `grok/default`), with
  count, Class grant lifetime, cap, quota units, seat identity and switch
  authorization kept as separate facts, and an optional
  `special_requirements` only when the owner actually supplied one (absent
  means none); relay owner-explicit model/seat choices unchanged and infer no
  worker allocation or extra constraint; `watch` (open progress/decisions,
  source pointers); `stop`.
- `cadence`: `timezone`, `start_local`, `end_local`, `interval_minutes`
  (e.g. `Asia/Shanghai`, `08:00`, `22:00`, `120`).
- `timer_owner`: current outer `platform` and its `native_timer_id`.
- `day_start`: `action` `reconcile_then_open_intake`, `state`
  `pending|confirmed`, `evidence` pointer or null.
- `day_end`: `action` `pause_new_claims_keep_inflight`, `state`
  `pending|confirmed`, `host_ack` and `claim_check` pointers or null.
- `final_stop`: present only when the owner set a delivery boundary at which
  the Delegator itself ends.

The existing native timer is the only scheduler; its prompt stays static:
Skill entry and project locator. A full sweep is one Delegator inquiry; one
owned permission event needs no additional full sweep. Each inquiry of an
already-verified unchanged Host uses the commands below: read this file,
verify `host` by fresh Runner `status`, audit the Host `body` (its `authorization` holds the
three Class definitions, a compact capability summary, and durable grants named by exact preset id;
catalog profiles are not copied into that routine body),
send one correction with current values, replace stale facts. The correction
may carry `sweep=Delegator inquiry: list --repo, verify identity, stop orphans only, keep in-flight, report`.
Relay urgent owner stops immediately; never wait to consolidate other changes. Never write
the Host JSON, copy its rows here, or select workers. Missing or unreadable: report, then recover from owner,
Runner and forge records before any `start`; never blank authorization.
Start, resume, replace, or uncertain identity: [handoff.md](handoff.md).

Keep new owner requirements and source pointers in this snapshot or the issue
handoff, retaining an existing dated quote or pointer when available. During an
inquiry you may independently ask the sole Host in plain language for a bounded
omission check, supplying scope and source pointers; it reuses an in-flight check
or sufficient unchanged evidence, or assigns its authorized Sidekick per
`kaola-project-runner/references/duty-reconcile.md`.

## Inquiry commands

`$HOST` is the exact `--session` already recorded on this snapshot's `host` object. Do not construct `$PLATFORM-<PROJECT_CODE>-orchestrator-main` for an already-verified Host.

Idle `send`, and a composite `steer --steer-mode interrupt`, each open a new turn. That text starts with the selected platform's exact `host_skill_entry` as its own first line. Recover the line from the installed host-platforms row (`platforms/<id>.yaml`), including kimi-cli's trailing space and codex's `$` form single-quoted in a shell; do not add a registry. Native busy `steer` stays in the loaded turn and adds no entry. `--no-wait` admission is not delivery.

Grok Bot account bridge attests that exact session, without `--intent`, before `status`, `send`, and `stop`, and refuses any `refused` receipt. Codex and generic skip this.

```bash
PLATFORM="<recorded host platform id>"
RUNNER="<skills>/$PLATFORM-kaola-project-runner/scripts/runtime-tmux.sh"
PROJECT="/abs/path/to/consumer-project"
HOST="<exact --session recorded on this snapshot>"
kaola-project-runner-locate --target local|cloud \
  --project "$PROJECT" --worker "$PLATFORM" --session "$HOST"
```

`<skills>` is the sibling Skill directory, or the bridge's `ROOT/skills`. The locate command is the Grok Bot bridge only.

```bash
"$RUNNER" status --repo "$PROJECT" --session "$HOST"
"$RUNNER" observe --repo "$PROJECT" --session "$HOST"
"$RUNNER" capture --repo "$PROJECT" --session "$HOST" --lines 200
"$RUNNER" send --repo "$PROJECT" --session "$HOST" --no-wait --text '<host_skill_entry>
<correction>'
```

## Day boundary

First beat in the window (`day_start`): refresh Host identity, authorization,
open backlog and in-flight work, then let the Host open new claims only if
still authorized. Final beat (`day_end`): tell the same Host to stop new issue
claims for the day; its in-flight work and workers keep running. Confirm both
the Host's acknowledgment (`host_ack`) and claim records showing no new claim
after the cutoff (`claim_check`); send admission alone is not confirmation.
Unconfirmed: keep `pending`, report the specific gap, reconcile next beat.
The daily pause is never a Host stop or task completion. `final_stop` uses the
existing close-out and exact-stop rules; confirm the result before disabling
recurrence.

## Scoped owner pause

Only an explicit owner stop/pause naming affected actions triggers this
procedure; ordinary inquiry, guidance, heartbeat or review feedback does not.
Record the exact scope and permitted continuation in existing `stop`/`watch`
before another affected action; safe state updates, reporting, checkpointing
and reconciliation remain allowed. Preserve unrelated work. A release pause
covers installation even when called preparation; unrelated authorized
diagnosis continues. For an urgent stop, use the exact recorded Host. Idle `send` and busy
`steer --steer-mode interrupt` each open a new turn, so the stop text starts
with that same `host_skill_entry` line. Native busy `steer` does not. Grok Bot
attests that session before `send` or `stop`. Confirm Host
acknowledgment, the current heartbeat snapshot and cessation of affected
actions from `observe`/`capture` receipts. Admission, `injected`, or
`end_turn` alone is not adoption. If unconfirmed, report and reconcile without
blind resend. Cancellation is not instant or undo: record completed side
effects; do not roll them back automatically.

## Timer handoff

Any outer platform reads this file on the bound target and sets its existing
native timer from `cadence`. On handoff read `timer_owner`, retire the previous
timer before the new one takes over (never two live Delegators), then update
`timer_owner` once verified. If the old timer cannot be controlled, report that
instead of polling twice. A schedule change updates this file and that one
timer together.
