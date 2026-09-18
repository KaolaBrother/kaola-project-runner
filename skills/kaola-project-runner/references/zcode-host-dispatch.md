# ZCode Host: dispatch, end the turn, wake on worker events

Read this when a ZCode Host session supervises workers, or when an outer Agent
starts one: operating instructions for three roles, with the exact flags and
receipt fields the scripts really use. No Python reading required.

Choosing between the two entry points, starting a Host, and the startup receipt an
outer Agent checks against the project's plan: [host-startup.md](host-startup.md).
This file is the beat itself.

## Three identities, never interchangeable

| Name | What it is | Where it comes from |
|---|---|---|
| Runner session | what every `--session` takes | you choose it at `start` |
| ACP session id | the bridge's id for this thread | `acp_session_id` in receipts |
| native session id | the CLI's own id (`sess_…`) | `session_meta`, for `--resume` |

A `sess_…` value is never a Runner session name. Never guess a session name.

Each installed Skill's `scripts/runtime-tmux.sh` is pinned to its own platform,
so the commands below take **no** platform argument; the repository's
`scripts/kaola-tmux.sh PLATFORM ...` form is the development entry, not this.

## 1. Outer controlling Agent — starting the Host

Starting a Host, the identity handover it cannot discover, and the startup
receipt to check against the project's plan are in
[host-startup.md](host-startup.md); they are not repeated here. What matters for
the beat: the Host's own `platform`/`session`/`repo` must reach it in that first
prompt, and it must be told to read this file before dispatching.

The Host is itself an ACP thread; being an orchestrator changes none of that.

**A Host that returns `end_turn` has finished this beat, not the project.** While
it has in-flight workers or open acceptance and close-out duties it is not an
idle worker: keep its holder and do not `stop` it. The next beat comes from a
worker event — do not send "continue", which duplicates work. You still own
supervision and the final lifecycle decision.

## 2. ZCode Host Agent — one beat

### Bind the notification target on every worker `start`

`KAOLA_ACP_HEARTBEAT_HOST` is read by the **worker's** `start` command, and only
there. It is a JSON object naming *you*, the Host. It is not inherited; set it
explicitly for that one command:

```bash
W="/abs/path/to/codex-kaola-project-runner/scripts/runtime-tmux.sh"
WORK_REPO="/abs/path/to/project"
HOST_REPO="/abs/path/to/project"      # the Host's own --repo
KAOLA_ACP_HEARTBEAT_HOST='{"platform":"zcode","session":"zcode-kaola-host","repo":"'"$HOST_REPO"'"}' \
  "$W" start --repo "$WORK_REPO" --session codex-kaola-feature-a
```

`platform` must be `zcode`, `session`/`repo` must be the Host's own, and it may
not name the worker's own session; anything else fails the start closed rather
than dropping the carrier silently. The worker's `--session` and `--repo` are
its own and are unrelated to the Host's.

**Check the receipt.** A bound start echoes the target back:

```json
"heartbeat_host": {"platform":"zcode","session":"zcode-kaola-host",
                   "repo":"/abs/path/to/project","socket":"…/…sock"}
```

No `heartbeat_host` key means this worker will never wake you. Fix the binding
before relying on events.

### Dispatch without blocking

```bash
"$W" send --repo "$WORK_REPO" --session codex-kaola-feature-a --no-wait --text '<the task>'
```

`--no-wait` returns as soon as the prompt is admitted:
`"outcome": "in_progress"`, `"mutation_status": "in_progress"`. That is
**accepted and running — not finished, and not correct**. Handle the other
outcomes instead of assuming success: an `error` (for example
`prompt-in-progress`, `agent-not-running`) means nothing was dispatched, and a
`prompt_timeout` or missing receipt leaves consumption unknown — establish the
fact with `observe` before re-sending anything.

**Keep two values from this receipt**: `prompt_fingerprint`, which identifies
the turn you dispatched, and `dispatch_event_cursor`, which is the worker's
event cursor *before* that turn produced anything. You need the cursor to read
the reply later.

### Finish the beat, then end your turn

Do the rest of this beat's executable work, update the one project heartbeat
prompt at `<project>/.kaola/heartbeat-prompt.json` (the `body` string: project
facts, pace, plans, coordination), report, and then **end your reply normally**.

There is no "wait mode" command to call. Ending the turn *is* the wait. Do not
`sleep`, poll in a loop, or call a blocking `wait` to hold this turn open — a
Host turn that stays active is exactly what keeps events undelivered. Do not
`stop` or `cancel` yourself or an in-flight worker to manufacture a wake-up.

### When an event wakes you

The next beat arrives as an ordinary prompt beginning
`kaola-host-notify/1`, with one JSON object per event —

```json
{"event_cursor":19,"event_id":"codex/codex-kaola-feature-a/idle/19","kind":"idle",
 "platform":"codex","repo":"/abs/path/to/project","reason":"turn-end","session":"codex-kaola-feature-a"}
```

Here `19` is where that worker's turn **ended**; the reply is below it.

— followed by your own heartbeat prompt body verbatim between
`<<<heartbeat-prompt` and `heartbeat-prompt>>>`.

**The notification is not the worker's reply and is not a success verdict.** Use
the event's own `platform`, `session`, and `repo` with that platform's Runner
Skill to read what actually happened.

**`event_cursor` is the end of the turn, not the start.** It is the worker's
cursor when the turn ended, so it sits *after* the reply: `capture --since
<event_cursor>` returns carrier and title updates and skips the very reply you
are accepting. Read from an anchor that precedes the output:

```bash
# the cursor your own dispatch receipt returned, from before the reply existed
"$W" observe --repo "$WORK_REPO" --session codex-kaola-feature-a
"$W" capture --repo "$WORK_REPO" --session codex-kaola-feature-a --since "$DISPATCH_EVENT_CURSOR"

# no anchor kept (resumed/adopted Host): bounded recent slice, never --since <event_cursor>
"$W" capture --repo "$WORK_REPO" --session codex-kaola-feature-a --lines 200
```

Confirm you are reading the turn you dispatched: `observe`'s
`last_prompt.fingerprint` must equal your dispatch receipt's
`prompt_fingerprint`, and `turn_outcome`/`stop_reason` must show it finished. A
capture with no assistant text means your window was wrong, not that the worker
said nothing — widen it and read again before judging.

Then accept, ask for a fix, dispatch more work, update the same heartbeat
prompt, and end the turn again.

`kind` is `idle` when the worker's turn ended and `terminated` when its process
exited. A finished turn is a full trigger; never kill a worker to be notified.

## 3. Workers and the notification carrier

The worker Agent owns its delivery; it never fabricates events and never writes
to your stdin. Its own holder sends the event over the Host holder's existing
admin socket. Do not ask a worker to notify you, and do not send a second prompt
that duplicates the carrier.

Delivery rules you can rely on:

- Busy Host: the event is staged and delivered at your next turn boundary. It is
  never injected mid-turn, and a worker event is never turned into steering.
- A worker that finished before your turn ended uses the same staging, so the
  race cannot skip or double-dispatch it.
- Duplicate `event_id`s collapse; several events pending at one boundary arrive
  in one prompt, each carrying the full current body.
- Confirmation follows the notification turn *completing*; after a resume,
  unconfirmed events are redelivered at least once, so make each pass
  idempotent rather than assuming exactly-once.
- Dispatch failure, unknown acceptance, or a missing `heartbeat_host` binding
  means you are **not** reliably event-driven: handle it in this beat or record
  the recovery duty explicitly before ending the turn.

Human or controlling-Agent steering (`steer`, where the platform supports it) is
a separate, Agent-chosen tool. It does not replace or alter this wake path.
