# Issue #65 — live ZCode Host acceptance, round 3 (2026-09-18, corrected Skill)

Re-run of the Host acceptance on the **corrected** generated Skill, so the
round-2 cursor fix is proven by a real Host and not only by a contract test.
The first acceptance (`live-host-acceptance.md`) ran against the reference that
told the Host to read from the *turn-end* cursor; this one ran against the
corrected reference.

Setup: scratch repo `/private/tmp/kw-i65-e2e2/repo`; Skills installed with
`install-local.sh --skills-dir /tmp/kw-i65-e2e2/repo/.zcode/skills --method copy
--platform zcode,codex` (workspace install only, no global install). Host
`zcode-kaola-i65host2` (ZCode 0.16.5, GLM Coding Plan). Worker
`codex-kaola-i65worker2` (Codex, gpt-5.6-sol high). Receipts: `live-host2/`,
full Host event log `live-host2/host-events.jsonl` (467 events).

The Host was given one bootstrap prompt: its own platform/session/repo, where
the two Skills are installed, the worker session name, the task, and "Follow the
Skill for how to wait." Nothing else. The task asked the worker for **three**
exact lines (`OPAL-65-ALPHA` / `OPAL-65-BRAVO` / `OPAL-65-CHARLIE`), so a Host
reading from the wrong anchor would come back empty-handed.

## What the Host did, in its own words

Beat 1 — dispatch, then end the turn:

> "the two anchors I need for verification — `prompt_fingerprint`
> `sha256:328bb6…9dbb6c` and `dispatch_event_cursor: 6` (reply must be read from
> before this cursor)"
>
> "The start receipt echoes `heartbeat_host` naming me (`zcode-kaola-i65host2`)
> with a live socket — the wake path is bound."
>
> "Dispatch is accepted and running: `outcome: in_progress` (accepted, not done)"
>
> "Ending my turn now — that ending **is** the wait."

Beat 2 — woken by the worker event, reads the real reply **from the dispatch
anchor**:

> "The worker's turn-end event woke me (`idle`,
> `outcome=turn_completed stop_reason=end_turn`). The notification is not the
> reply … then `capture --since 6` from my dispatch anchor (**the event's cursor
> 35 marks the turn's *end*, so the reply sits below it**)"
>
> "`last_prompt.fingerprint` equals my dispatch fingerprint … Reassembling the
> worker's assistant message … yields exactly `OPAL-65-ALPHA` / `OPAL-65-BRAVO` /
> `OPAL-65-CHARLIE` — three lines, nothing before or after"

That sentence is the round-2 finding, stated by a live Host from the corrected
reference alone: the worker event's `event_cursor` is the end of the turn, and
`dispatch_event_cursor` is the pre-reply anchor. It then stopped the worker
(exit 0, no residual processes) and closed out; the `terminated` event woke it
once more and it correctly invented no new work.

## The carrier chain (Host holder event log, verbatim cursors)

| cursor | event |
|---|---|
| 208 | `worker_event` staged — `codex/codex-kaola-i65worker2/idle/35`, `reason: outcome=turn_completed stop_reason=end_turn` |
| 258 | `worker_event_delivered` at the turn boundary, `heartbeat_maintained: true` |
| 341 | `worker_event` staged — `terminated/37`, `reason: exit_code=0` (while beat 2 was active) |
| 387 | `worker_event_confirmed` `idle/35` (after beat 2 completed) |
| 388 | `worker_event_delivered` `terminated/37` |
| 467 | `worker_event_confirmed` `terminated/37` |

Busy staging, turn-boundary delivery, and confirm-after-completion held twice
again. `stop` on the Host: `stopped: true`, `residual_pids []`.
