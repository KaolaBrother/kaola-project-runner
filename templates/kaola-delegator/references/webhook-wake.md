# Webhook wake

A webhook wakes you when the Host turn ends, so you do not wait for the next
heartbeat. The Host holder sends the signal. A model or a prompt never sends
it. Configure it yourself with this procedure. The only owner action is to
paste the URL and the sender key into the masked secret input one time.

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
2. **Create the wake pair.** Create your webhook routine for this project.
   Make your existing heartbeat the cron fallback at low frequency, or keep it
   if it is already low. Do not create a third routine. Set both routine
   bodies to the canonical timer body.
3. **Get the URL and the sender key without seeing them.** Ask the owner one
   time to paste the routine's webhook URL and sender key from the routine
   panel into the Grok Bot masked secret input. Never ask for them in chat.
   The values arrive as environment variables on the Grok Bot box. Use them
   only by variable name. Also ask how the routine panel attaches the sender
   key: a named header (copy the exact header name and any value prefix,
   for example `Bearer `), or a key that is already part of the URL. Take this
   format from the routine panel only. Do not guess a header name.
4. **Configure.** Give the values by variable name, from stdin, or from a file.
   Never put a value on a command line and never echo it.
   - Variable names: `--url-env URL_VAR [--key-env KEY_VAR]`.
   - Stdin: `--stdin`, with one JSON object `{"url": ..., "sender_key": ...}`
     made by a tool that does not put the values in a process argument list.
   - File: `--input-file PATH`, the same JSON, mode `0600`, owned by you.
     Delete the file after `configure`.
   Attachment: `--key-header NAME [--key-prefix TEXT]`, or `--key-in-url`
   with no sender key. If the bound target cannot read the secret variables,
   stop and report that blocker.
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
   `cadence`). Report the exact blocker to the owner (receipt `result`,
   `http_status`, `error`). Do not retry blindly.

A Host holder sends signals only after a seat restart on a KPR build that has
this hook. If `test` delivers but Host turns write no receipts, report that
the Host holder is older than the hook. A restart needs its own
authorization ([host-platforms.md](host-platforms.md#kpr-updates)).

## On a wake

The payload is a signal, not evidence. It has `schema`
`kaola-delegator-wake/1`, `project`, `session`, `holder_instance_id`,
`event_seq`, `state` (`end_turn`, `blocked`, `error`, `stopped` or `test`),
`state_detail` and `ts` (UTC). It has no transcript, prompt, diff or secret.
For `end_turn`, `state_detail` is the stop reason the agent reported, for
example `end_turn`, `max_tokens`, `max_turn_requests`, `refusal` or
`cancelled`. Otherwise it is `permission_required`, `turn_failed`,
`agent_exit`, `boot_failure`, `holder_lost`, `exact_stop` or `test`. An
owner question that the agent asks in its reply text arrives as `end_turn`.
If a Host holder dies without a signal, the next `start` or `stop` of that
session sends one `error` wake with `state_detail` `holder_lost`, the dead
`holder_instance_id` and a new `event_seq`.

On each wake: Grok Bot re-reads the bridge Accepted line and locates; then
attest the exact session and read the authoritative `status`, `observe` and
`capture` receipts. Then run the standard inquiry. If the payload `project`
or `session` is not your recorded `host`, it is not your Host: report it and
do not act on it.

Dedupe on `holder_instance_id` + `event_seq` against the receipt cursor. A
wake that is not newer than the receipts you already handled causes no
action. Duplicate and out-of-order wakes are harmless; the existing `watch`
rules prevent a second relay. `blocked` means the Host waits on a permission:
handle it as one owned permission event. The cron fallback finds a lost
delivery. Delivery receipts are in `<repo>/.kaola/delegator-webhook-receipts.json`
(the last 32 attempts).
