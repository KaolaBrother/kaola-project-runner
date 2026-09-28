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
  means none); `watch` (open progress/decisions, source pointers); `stop`.
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
Skill entry and project locator. Each inquiry: read the file, verify `host` by
fresh Runner `status`, audit the Host `body`, send one concrete correction,
replace stale facts. Missing or unreadable: report, then recover from owner,
Runner and forge records before any `start`; never blank authorization.

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

## Timer handoff

Any outer platform reads this file on the bound target and sets its existing
native timer from `cadence`. On handoff read `timer_owner`, retire the previous
timer before the new one takes over (never two live Delegators), then update
`timer_owner` once verified. If the old timer cannot be controlled, report that
instead of polling twice. A schedule change updates this file and that one
timer together.
