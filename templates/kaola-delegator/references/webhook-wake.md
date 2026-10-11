# Webhook wake

A webhook wakes you when the Host holder decides you must act, so you do not
wait for the next heartbeat. It does not wake on every turn end. The Host
holder sends the signal. A model or a prompt never sends it. Configure it
yourself with this procedure. The only owner action is to paste the URL and
the sender key into the masked secret input one time.

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
   Owner-verified for Grok Bot (live, 2026-10-10): routine webhooks
   authenticate with `Authorization: Bearer <key>`, so configure with
   `--key-header Authorization --key-prefix 'Bearer '`; a bare key without
   the prefix gets HTTP 401.
4. **Configure.** Give the values by variable name, from stdin, or from a file.
   Never put a value on a command line and never echo it.
   - Variable names: `--url-env URL_VAR [--key-env KEY_VAR]`.
   - Stdin: `--stdin`, with one JSON object `{"url": ..., "sender_key": ...}`
     made by a tool that does not put the values in a process argument list.
   - File: `--input-file PATH`, the same JSON, mode `0600`, owned by you.
     Delete the file after `configure`.
   Attachment: `--key-header NAME [--key-prefix TEXT]`, or `--key-in-url`
   with no sender key. For a Grok Bot routine use
   `--key-header Authorization --key-prefix 'Bearer '` (step 3). If the
   bound target cannot read the secret variables, stop and report that
   blocker.
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

The payload is a signal, not evidence. Re-read receipts before you act. It
has `schema` `kaola-delegator-wake/1`, `project`, `session`,
`holder_instance_id`, `event_seq`, `state` (`end_turn`, `blocked`, `error`,
`stopped` or `test`), `state_detail`, `reason` and `ts` (UTC). It has no
transcript, prompt, diff or secret. `reason` names why you were woken:
`permission_required`, `turn_failed`, `agent_exited`, `boot_failure`,
`exact_stop`, `holder_lost`, `all-idle`, `question_waiting`,
`delivery_review`, `needs_decision`, `host_stopped_pending`, or `test`.
`state_detail` is separate from `reason`: the agent's stop reason on
`end_turn`, else `permission_required`, `turn_failed`, `agent_exit`,
`boot_failure`, `holder_lost`, `exact_stop`, or `test`.

You are not woken when the Host ends a turn and continues by itself. You are
not woken when the turn end is your own send or steer and a worker seat is
still working. You are woken with `all-idle` when the Host goes idle and no
dispatched seat is still working, whether or not pending work is recorded. You
are also woken for a permission, a failure, an agent exit, a failed boot, an
exact stop, a recovered holder death, a waiting question, a delivery that
needs review, a decision, or a Host that stopped with pending work while a
seat is still working. A clean idle turn with a seat still working does not wake
you. A Sideagent node is not a seat, and a holder in `agent_exited`,
`stopping`, or `stopped` is not working.
After the Host's last turn, confirmed `sideagent_node_stopped` or the last
worker's `terminated` re-checks one non-blocking `all-idle` (`state`
`end_turn`, `state_detail` `end_turn`) when the Host is idle and no seat is
working. A live seat, an active turn, a follow-up, an unconfirmed node stop,
or exact stop does not. One episode, one wake. No time throttle.

If a Host holder dies without a signal, the next `start` or `stop` of that
session sends one `error` wake with `reason` `holder_lost`, the dead
`holder_instance_id` and a new `event_seq`. That recovered wake is not a
duplicate.

On each wake: re-read the Accepted line, locate, attest the session, and
read `status`, `observe`, and `capture`. The payload does not prove those
facts. Then run the standard inquiry. If `project` or `session` is not your
recorded `host`, report it and do not act on it.

Dedupe on `holder_instance_id` + `event_seq`. The sender drops a second POST
of that pair. A wake you already handled causes no action. Duplicate and
out-of-order wakes are harmless; `watch` rules prevent a second relay.
`blocked` is one owned permission. The cron fallback finds a lost delivery.
One attempt waits 12 s. A timeout is not
retried. Connection errors, HTTP 5xx, 408 and 429 are retried. Receipts are
in `<repo>/.kaola/delegator-webhook-receipts.json` (the last 32).
