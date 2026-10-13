# Webhook wake

A webhook wakes you when the Host holder decides you must act. It does not
wake on every turn end. A model or a prompt never sends it. The owner pastes
the URL and the sender key into the masked secret input once.

## One Delegator timer

Grok Bot cannot put a webhook listener and a cron listener in one routine.
For each project you own ONE webhook routine and AT MOST ONE low-frequency
cron fallback routine (for example every 120 minutes in the `cadence`
window). This pair is your single Delegator timer. The timer handoff rule
([snapshot.md](snapshot.md#timer-handoff)) applies to the two routines
together. Never keep a second webhook routine or a second cron routine for
the same project. Both routines use the exact canonical timer body
([inquiry-report.md](inquiry-report.md#native-timer)), so each wake runs the
standard inquiry. Record the pair in `timer_owner`: `native_timer_id` (cron
routine), `webhook_routine_id` and `wake_mode` `webhook+heartbeat`.
Heartbeat-only is `wake_mode` `heartbeat`; an absent `wake_mode` is
heartbeat-only.

## Commands

Run these on the bound target (Grok Bot: after locate). `$PLATFORM` is the
recorded Host platform. `$LABEL` is your stable agent label, for example
`grok-bot:KPR`. Each command writes one JSON receipt. No receipt contains the
URL or the sender key.

```bash
HOOK="python3 <skills>/$PLATFORM-kaola-project-runner/scripts/kaola-acp.py delegator-webhook"
$HOOK status --project "$PROJECT"
$HOOK configure --project "$PROJECT" --owner-agent "$LABEL" \
  --url-env URL_VAR [--key-env KEY_VAR] (--key-header NAME [--key-prefix TEXT] | --key-in-url)
$HOOK test --project "$PROJECT"
$HOOK remove --project "$PROJECT" --owner-agent "$LABEL"
```

`<skills>` is the sibling Skill directory, or the bridge's `ROOT/skills`.

## Self-configuration

1. **Discover.** Run `status`. If `configured` and `enabled` are true,
   `owner_agent` is your label and `last_test.result` is `delivered`, the
   webhook is ready. Do nothing more.
2. **Create the wake pair.** One webhook routine for this project. Make the
   existing heartbeat the low-frequency cron fallback, or keep it if it is
   already low. No third routine. Both bodies are the canonical timer body.
3. **Get the URL and the sender key without seeing them.** Ask the owner once
   to paste the routine's webhook URL and sender key into the masked secret
   input. Never ask in chat. They arrive as environment variables; use them
   only by name. Ask how the panel attaches the key (header plus prefix, or
   a key already in the URL). Do not guess. Grok Bot, verified 2026-10-10:
   `--key-header Authorization --key-prefix 'Bearer '`. A bare key is HTTP 401.
4. **Configure.** Pass values by variable name, stdin, or a mode `0600` file
   you own. Never put a value on a command line and never echo it.
   `--url-env URL_VAR [--key-env KEY_VAR]`, or `--stdin` / `--input-file PATH`
   with `{"url","sender_key"}`. Delete the file after `configure`.
   Attachment: `--key-header NAME [--key-prefix TEXT]`, or `--key-in-url`.
   If the target cannot read the variables, stop and report that blocker.
5. **Verify.** Run `test`. It sends one signal with `state` `test`. Confirm
   that YOUR webhook routine woke with that test signal. Then record
   `timer_owner.wake_mode` `webhook+heartbeat` and `webhook_routine_id` with
   `delegator update` ([inquiry-report.md](inquiry-report.md)). A `delivered`
   receipt without a wake of your routine is not success.
6. **Own only your entry.** The machine config holds one entry for each
   project root. `configure` refuses an entry that has a different
   `owner_agent`. Use `--replace-owner OLD_LABEL` only after the timer handoff
   retired that agent's routines.
7. **Rotate or remove.** If the routine is deleted or the key rotates, do
   steps 2 to 5 again. `remove` deletes only your own project entry.
8. **Failure.** If the owner declines the secret input, `test` fails, or your
   routine did not wake, stay heartbeat-only (`wake_mode` `heartbeat`, normal
   `cadence`). Report the exact blocker (receipt `result`, `http_status`,
   `error`, truncated `response_body`). A failed receipt carries `route` or
   `self_route`. Do not retry blindly.

A Host holder sends this hook only after a seat restart on a build that has
it. If `test` delivers but turns write no receipts, the holder is older than
the hook. Restart needs its own authorization
([host-platforms.md](host-platforms.md#kpr-updates)).

## On a wake

The payload is a signal, not evidence. Re-read receipts before you act.
Schema `kaola-delegator-wake/1`: `project`, `session`, `holder_instance_id`,
`event_seq`, `state` (`end_turn`, `blocked`, `error`, `stopped`, `test`),
`state_detail`, `reason`, `ts` (UTC). No transcript, prompt, diff, or secret.
`reason` is `permission_required`, `turn_failed`, `agent_exited`,
`boot_failure`, `exact_stop`, `holder_lost`, `all-idle`, `question_waiting`,
`delivery_review`, `needs_decision`, `host_stopped_pending`, or `test`.
That list is every wake. `state_detail` is `host_initiated` for an explicit
Host wake, otherwise the stop reason or a fixed token such as `exact_stop`.

Two rules are the core. (1) All-ended: Host idle, no follow-up, no active
seat turn. One `all-idle` per episode. A carried latch and your turn do not
suppress it. A live `send --wait` holds it until return. The same
episode does not wake again. Your send does not open the next one. A working
non-exempt seat, a non-exempt worker stop, or a self turn with worker events
does. (2) `kaola-acp.py $PLATFORM wake --repo "$PROJECT" --session "$SESSION"
--reason REASON` fires then, even while a seat works. `REASON` is
`needs_decision`, `question_waiting`, or `delivery_review`. `state`
`end_turn`, `state_detail` `host_initiated`. The latch does not block it.
Each call is a new `event_seq`. A stuck seat is this call. No timer. A
crash stays `holder_lost`. A delivery failure is not a wake.

Permission, failure, exit, boot, exact stop, and `holder_lost` stay. A
pending Delegator decision wakes `needs_decision` only from `state.decisions`
(`owner` `delegator` or `user`). A `.kaola/run` file or turn text does not.
The latch does not block it, including the turn after a compaction reload.
A length stop or refusal while a seat works stays `host_stopped_pending` or
`needs_decision`. No wake when the Host continues, or when your send ends
during a seat turn unless the Host called `wake`. Only an active turn is
working. A Sideagent is not a seat. A confirmed node stop or the last worker
`terminated` re-checks one `all-idle` when owed. No time throttle.

A dead holder with no signal gets one `error`/`holder_lost` wake for that
`holder_instance_id` and a new `event_seq`. `start` or a dead-holder `stop`
sends it. The cron fallback sends it with no new Host start: each inquiry
runs `$HOOK status --project "$PROJECT"`. `test` does not scan. `status`
wakes a Host record of this project when the holder pid is dead and
`state` is not `stopped`, even if the agent lives, via the same sender
and `delegator_death_wake` dedupe. A live holder pid, reused or not, waits for
`start` or `stop`. Nothing else polls. The wait is one `cadence.interval_minutes` (example
120 minutes). `status` does not read that interval and does not schedule itself.

On each wake, re-read the Accepted line, locate, attest the session, and
read `status`, `observe`, and `capture`. Then run the standard inquiry. If
`project` or `session` is not your recorded `host`, report it and do not act.

Dedupe is `holder_instance_id` + `event_seq`. The sender drops a second POST.
A handled wake causes no action. Duplicate and out-of-order wakes are
harmless; `watch` prevents a second relay. `blocked` is one owned
permission. One attempt waits 12 s. A timeout is not retried. Connection
errors and HTTP 400, 408, 429, and 5xx are retried. 401, 403, 404, and any
other 4xx are final. An HTTP error stores a truncated `response_body` and
headers `content-type`, `retry-after`, `www-authenticate`, `x-request-id`,
`x-correlation-id`. The URL and the sender key never appear in a receipt.
Receipts: `<repo>/.kaola/delegator-webhook-receipts.json` (last 32).
