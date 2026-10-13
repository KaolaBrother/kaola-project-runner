# Webhook wake

A webhook wakes you when the Host holder decides you must act. It does not
wake on every turn end. A model or a prompt never sends it. You configure it.
The owner pastes the URL and the sender key into the masked secret input
one time.

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
3. **Get the URL and the sender key without seeing them.** Ask the owner one
   time to paste the routine's webhook URL and sender key from the routine
   panel into the Grok Bot masked secret input. Never ask for them in chat.
   They arrive as environment variables. Use them only by variable name.
   Also ask how the panel attaches the key: a header name plus any prefix,
   or a key already in the URL. Do not guess.
   Owner-verified for Grok Bot (live, 2026-10-10): `Authorization: Bearer <key>`,
   so use `--key-header Authorization --key-prefix 'Bearer '`. A bare key
   gets HTTP 401.
4. **Configure.** Give the values by variable name, from stdin, or from a file.
   Never put a value on a command line and never echo it.
   - Variable names: `--url-env URL_VAR [--key-env KEY_VAR]`.
   - Stdin: `--stdin`, with one JSON object `{"url": ..., "sender_key": ...}`
     made by a tool that does not put the values in a process argument list.
   - File: `--input-file PATH`, the same JSON, mode `0600`, owned by you.
     Delete the file after `configure`.
   Attachment: `--key-header NAME [--key-prefix TEXT]`, or `--key-in-url`
   with no sender key. If the bound target cannot read the secret
   variables, stop and report that blocker.
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
   `error`, truncated `response_body`). Do not retry blindly.

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
That list is every wake. `state_detail` is not `reason`: the agent's stop
reason on `end_turn`, else `permission_required`, `turn_failed`, `agent_exit`,
`boot_failure`, `holder_lost`, `exact_stop`, or `test`.

No wake when the Host continues by itself, or when your send or steer ends
while a worker seat still works. `all-idle` is once per idle transition: the
Host is idle and no dispatched seat is working, pending work or not. A turn
you admitted does not open that episode and does not wake by itself, unless
it stops the last working seat. A self turn with no new worker event sends
no second `all-idle`. A Sideagent node is not a seat. A holder in
`agent_exited`, `stopping`, or `stopped` is not working. After the Host's
last turn, confirmed `sideagent_node_stopped` or the last worker's
`terminated` re-checks one non-blocking `all-idle` (`state` `end_turn`,
`state_detail` `end_turn`) when the Host is idle and no seat is working. A
live seat, an active turn, a follow-up, an unconfirmed node stop, or exact
stop does not. One episode, one wake. It re-opens when a non-exempt seat is
working, a non-exempt worker stops, or a self turn delivers worker events.
Your send does not re-open it. No time throttle.

A dead holder with no signal gets one `error`/`holder_lost` wake for that
`holder_instance_id` and a new `event_seq`. `start` or a dead-holder `stop`
sends it. The cron fallback sends it with no new Host start: each inquiry
runs `$HOOK status --project "$PROJECT"`. `test` does not scan. `status`
wakes a Host record of this project when the holder pid, agent pid, and
agent pgid are dead and `state` is not `stopped`, through the same sender
and `delegator_death_wake` dedupe. A live pid, reused or not, waits for
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
