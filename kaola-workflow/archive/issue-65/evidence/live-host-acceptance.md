# Issue #65 — live ZCode Host acceptance (2026-09-18)

The owner's bar for the Host contract: a **real ZCode Host**, using only the
generated Skill and its reference, dispatches a worker, ends its turn, is woken
by the worker's event, and reads the worker's real reply. No harness calls the
Runner on the Host's behalf and no rules are added verbally.

Setup: scratch repo `/tmp/kw-i65-e2e/repo`, Skills installed with
`install-local.sh --skills-dir /tmp/kw-i65-e2e/repo/.zcode/skills --method copy
--platform zcode,codex` (workspace install only — no global install, nothing
outside that scratch repo). Host `zcode-kaola-i65host` (ZCode 0.16.5, GLM Coding
Plan). Worker `codex-kaola-i65worker`. Receipts: `evidence/live-host/`.

The **only** thing given to the Host was one bootstrap prompt: its own
`platform`/`session`/`repo`, where the main Skill and the Codex worker Skill are
installed, the worker's Runner session name, the task text, and "Follow the Skill
for how to wait." Everything else came from the generated Skill.

## Beat 1 — dispatch, then end the turn (`stop_reason: end_turn`)

The Host, in its own words:

> "…passed my own identity on the start command, and the receipt echoed it back —
> `heartbeat_host: {platform: zcode, session: zcode-kaola-i65host, repo:
> /private/tmp/kw-i65-e2e/repo}` with a live socket — so the binding is confirmed
> and its turn-end will wake this session."
>
> "`send --no-wait --text 'Reply with exactly one line: WORKER-DONE-65'`. The
> receipt shows `outcome: in_progress` and `mutation_status: in_progress` … —
> accepted and running, not finished."
>
> "`/tmp/kw-i65-e2e/repo/.kaola/heartbeat-prompt.json` now carries the rendered
> `body` …"
>
> "Per the Skill, I now end this reply — ending the turn is the wait; no sleep,
> polling, or stop is needed."

It bound the carrier, checked the receipt, dispatched non-blocking, read the
acceptance honestly, maintained the one heartbeat prompt, and ended the turn. No
sleep, no poll, no blocking wait, no stop/cancel to manufacture waiting.

## The carrier chain (host holder event log, verbatim cursors)

| cursor | event |
|---|---|
| 179 | `worker_event` staged — `codex/codex-kaola-i65worker/idle/18`, `reason: outcome=turn_completed stop_reason=end_turn` (**staged while the Host turn was still active**) |
| 312 | `worker_event_delivered` at the turn boundary, `heartbeat_maintained: true`, source `.kaola/heartbeat-prompt.json` |
| 468 | `worker_event` staged — `terminated/20`, `reason: exit_code=0` (**staged while beat 2 was active**) |
| 521 | `worker_event_confirmed` `idle/18` (after beat 2 completed) |
| 522 | `worker_event_delivered` `terminated/20` |
| 597 | `worker_event_confirmed` `terminated/20` |

The worker holder's own log shows the matching sends
(`heartbeat_carrier_sent`, `staged: true`) for both events. Busy staging,
turn-boundary delivery, and confirm-after-completion all held twice, live.

## Beat 2 — woken by the `idle` event, read the worker's real reply

> "The worker's turn ended. Per the dispatch reference, the notification isn't
> the reply — I'll read what actually happened via the Codex Runner before
> judging"
>
> "Delivery verified. The `agent_message_chunk` events (cursors 10–15, one
> message id, phase `final_answer`) concatenate to exactly `WORK` + `ER` + `-D` +
> `ONE` + `-` + `65` = **`WORKER-DONE-65`** — a single message, single line,
> nothing else."
>
> "per the Skill, idle is not keep-alive, so I'm stopping the exact owned
> session"

The Host used the event's own worker identity with that worker's Runner Skill,
read the actual transcript rather than trusting the notification, and only then
accepted.

## Beat 3 — woken by the `terminated` event, closed out without inventing work

> "the event (`terminated/20`, `reason: exit_code=0`) matches the stop receipt I
> recorded last pass exactly. A fresh `status` read shows `state: stopped`,
> `agent_alive: false`, no residual processes and no child process groups"
>
> "**No work dispatched** — there is no authorization for new tasks, and
> inventing work or restarting a session would violate it."

## One real defect this run found

The Host reported: *"this wrapper is platform-pinned, so the reference's
`"$W" codex start …` is invoked here as `runtime-tmux.sh start …`."* It was
right — an installed Skill's `scripts/runtime-tmux.sh` takes no platform
argument, and my reference examples carried one. Fixed in
`templates/orchestrator/references/zcode-host-dispatch.md.tmpl` (all five
examples, plus an explicit sentence that these commands take no platform
argument) and pinned by
`tests/contract/test-issue-65-host-contract.py::test_reference_binds_the_carrier_with_a_runnable_example`.

## Close-out

`stop` on the Host returned `residual_pids: []`; the worker was already
`state: stopped`. Nothing outside `/tmp/kw-i65-e2e` was written, no global
install happened, and no pre-existing session was touched.
