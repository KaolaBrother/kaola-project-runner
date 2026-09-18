# ZCode Host: dispatch, end the turn, wake on worker events

Read this when a ZCode Host session supervises workers, or when an outer Agent
starts one. It is operating instructions for three roles, with the exact flags
and receipt fields the scripts really use. Nobody has to read Python to use it.

## Three identities, never interchangeable

| Name | What it is | Where it comes from |
|---|---|---|
| Runner session | the name you pass to every `--session` | you choose it at `start` |
| ACP session id | the bridge's id for this conversation | `acp_session_id` in receipts |
| native session id | the CLI's own conversation id (`sess_…`) | `session_meta`, for `--resume` |

A `sess_…` value is never a Runner session name. Never guess a session name.

Each installed Skill's `scripts/runtime-tmux.sh` is already pinned to its own
platform, so the commands below take **no** platform argument — the repository's
`scripts/kaola-tmux.sh PLATFORM ...` form is the development entry, not this one.

## 1. Outer controlling Agent — starting the Host

Start the Host like any worker, then hand it its own identity in the first
prompt. A Host cannot discover its Runner name, and no environment variable
carries it in:

```bash
ZC="/abs/path/to/zcode-kaola-project-runner/scripts/runtime-tmux.sh"
HOST_REPO="/abs/path/to/project"
"$ZC" start --repo "$HOST_REPO" --session zcode-kaola-host
"$ZC" send --repo "$HOST_REPO" --session zcode-kaola-host --text \
'You are the Project Runner Host for this project. Load the installed
kaola-project-runner Skill. Your own Runner identity is exactly:
platform=zcode session=zcode-kaola-host repo='"$HOST_REPO"'
Authorized workers: <list>. Dispatch them, then end your turn and wait for
worker events. Read references/zcode-host-dispatch.md before dispatching.'
```

The Host is itself an ACP thread; being an orchestrator changes none of that.

**A Host that returns `end_turn` has finished this beat, not the project.** While
it has in-flight workers or undelivered acceptance and close-out duties, it is
not an idle worker: keep its holder running and do not `stop` it. The next beat
is triggered by a worker event — do not send "continue"; a manual nudge
duplicates work. You still own supervision and the final lifecycle decision.

## 2. ZCode Host Agent — one beat

### Bind the notification target on every worker `start`

`KAOLA_ACP_HEARTBEAT_HOST` is read by the **worker's** `start` command, and only
there. It is a JSON object naming *you*, the Host. It is not inherited; set it
explicitly for that one command:

```bash
W="/abs/path/to/codex-kaola-project-runner/scripts/runtime-tmux.sh"
WORK_REPO="/abs/path/to/project"
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

— followed by your own heartbeat prompt body verbatim between
`<<<heartbeat-prompt` and `heartbeat-prompt>>>`.

**The notification is not the worker's reply and is not a success verdict.** Use
the event's own `platform`, `session`, and `repo` with that platform's Runner
Skill to read what actually happened:

```bash
"$W" observe --repo "$WORK_REPO" --session codex-kaola-feature-a
"$W" capture --repo "$WORK_REPO" --session codex-kaola-feature-a --since 19
```

Then accept, ask for a fix, dispatch more work, update the same heartbeat
prompt, and end the turn again.

`kind` is `idle` when the worker's turn ended and `terminated` when its process
exited. A finished turn is a full trigger — never kill a worker to be notified.

## 3. Workers and the notification carrier

The worker Agent owns its delivery; it never fabricates events and never writes
to your stdin. The worker's own holder sends the event over the Host holder's
existing admin socket. Do not ask a worker to notify you, and do not send a
second prompt that duplicates the carrier.

Delivery rules you can rely on:

- Busy Host: the event is staged and delivered at your next turn boundary. It is
  never injected mid-turn, and a worker event is never turned into steering.
- A worker that finished before your turn ended is handled by the same staging,
  so the race cannot skip or double-dispatch it.
- Duplicate `event_id`s collapse; several events pending at one boundary arrive
  in one prompt, each carrying the full current body.
- Confirmation follows the notification turn *completing*. After a resume,
  unconfirmed events are redelivered at least once — make each pass idempotent
  rather than assuming exactly-once.
- Dispatch failure, unknown acceptance, or a missing `heartbeat_host` binding
  means you are **not** reliably event-driven: handle it in this beat or record
  the recovery duty explicitly before ending the turn.

Human or controlling-Agent steering (`steer`, where the platform supports it) is
a separate, Agent-chosen tool. It does not replace or alter this wake path.
