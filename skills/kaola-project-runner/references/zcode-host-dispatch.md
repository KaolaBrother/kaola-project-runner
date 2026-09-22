# ZCode Host: dispatch, end the turn, wake on worker events

Host beat: [host-startup.md](host-startup.md). Outer start: Kaola-Delegator
(`kaola-delegator`).

## Three identities, never interchangeable

Runner session (what `--session` takes, chosen at `start`), ACP session id
(`acp_session_id` in receipts) and native session id (`sess_…`, for `--resume`)
are different things. A `sess_…` value is never a Runner session name. Never
guess a session name.

Each installed Skill's `scripts/runtime-tmux.sh` is platform-pinned, so the
commands below take **no** platform argument.

## 2. ZCode Host Agent — one beat

### Start a worker from this Host

```bash
W="/abs/path/to/codex-kaola-project-runner/scripts/runtime-tmux.sh"
WORK_REPO="/abs/path/to/project"      # the worker's repo
"$W" start --repo "$WORK_REPO" --session codex-KT-i274-parser
```

Run `start` from your own session: it binds the worker to you and refuses
(`result: refused`, `reason: heartbeat-host-…`, exit 1) instead of starting
unbound. A PTY request is refused on every command
(`transport-pty-retired`): the Runner is ACP-only. Worker names
are issue-scoped: `<platform>-<CODE>-i<ISSUE>-<purpose>`.

Count before every `start`: live owned sessions from `status`/`observe`
receipts, ACP holders included. At the authorized count (a hard cap), exact-`stop`
one seat first. A different task is a new session, never a prompt chained
into a finished seat.

### Read the binding in force, new worker or reused

```json
"heartbeat_host_known": true,
"heartbeat_host": {"platform":"zcode","session":"zcode-kaola-host","repo":"…","socket":"…"},
"heartbeat_host_source": "dispatcher",
"dispatcher": {"holder_instance_id":"…","platform":"zcode","repo":"…","session":"zcode-kaola-host"}
```

`heartbeat_host` is the running holder's own binding; `heartbeat_host_requested`
is only the request; `observe` reports the binding any time.

- `heartbeat_host_known: false` — a holder or record older than the field:
  unknown; treat it as unbound.
- No `heartbeat_host_source` key at all — the worker Skill copy that ran this
  `start` predates automatic binding. Exact-`stop` it, report `BLOCKED` with the
  install as the cause, and dispatch again only after it is refreshed.
- `"error": {"code": "session-exists"}` — you reused a live holder, which keeps
  its binding; a `null` there predates automatic binding.

### A worker without a binding

A worker started before automatic binding shows `heartbeat_host: null`: read
its in-flight result with the bounded `wait --timeout <seconds>` (the recovery
exception, never the ordinary wait or a poll loop), then exact `stop` and
`start` it at that idle point. A refused `start`, or a session that is gone, is
the exception you report with the decision you need. Never auto-cancel, re-send
work you cannot show was dropped, switch platform, or stop the Host to force a
wake-up.

### Dispatch without blocking

```bash
"$W" send --repo "$WORK_REPO" --session codex-KT-i274-parser --no-wait --text '<the task>'
```

`--no-wait` returns once the prompt is admitted: `"outcome": "in_progress"`,
`"mutation_status": "in_progress"` — **accepted and running — not finished, and
not correct**. An `error` (`prompt-in-progress`, `agent-not-running`) dispatched
nothing; a `prompt_timeout` or missing receipt leaves consumption unknown —
establish it with `observe` before re-sending.

**Keep two values**: `prompt_fingerprint`, the turn you dispatched, and
`dispatch_event_cursor`, the cursor *before* it produced anything.

### Finish the beat, then end your turn

Do the rest of this beat, update the heartbeat prompt at
`<project>/.kaola/heartbeat-prompt.json` (`body`: project facts, pace, plans),
report per platform `live N / authorized M` and the seats stopped this beat,
then **end your reply normally**.

There is no "wait mode" command to call. Ending the turn *is* the wait. Do not
`sleep`, poll in a loop, or hold this turn open with a blocking `wait` — an
active Host turn is exactly what keeps events undelivered. Do not `stop` or
`cancel` yourself or an in-flight worker to manufacture a wake-up.

### When an event wakes you

The next beat is an ordinary prompt: first line `/kaola-project-runner`,
then `kaola-host-notify/1`, one JSON object per event —

```json
{"event_cursor":19,"event_id":"codex/codex-KT-i274-parser/idle/19","kind":"idle",
 "platform":"codex","repo":"/abs/path/to/project","reason":"turn-end","session":"codex-KT-i274-parser"}
```

— then your heartbeat body verbatim between `<<<heartbeat-prompt` and
`heartbeat-prompt>>>`.

**The notification is not the worker's reply and is not a success verdict.** Read
what happened with the event's own `platform`/`session`/`repo` and that Skill.

**`event_cursor` is the end of the turn, not the start** — `19` is where that
turn ended, so `capture --since <event_cursor>` sees only carrier and title
updates. Read from an earlier anchor:

```bash
# the dispatch receipt's cursor, from before the reply existed
"$W" observe --repo "$WORK_REPO" --session codex-KT-i274-parser
"$W" capture --repo "$WORK_REPO" --session codex-KT-i274-parser --since "$DISPATCH_EVENT_CURSOR"
# no anchor (resumed/adopted Host): never --since <event_cursor>
"$W" capture --repo "$WORK_REPO" --session codex-KT-i274-parser --lines 200
```

Confirm you read the turn you dispatched: `observe`'s
`last_prompt.fingerprint` must equal the dispatch receipt's `prompt_fingerprint`,
and `turn_outcome`/`stop_reason` must show it finished. No assistant text
means the window was wrong — widen it. Then accept or send the repair (the
same assignment); once accepted, exact-`stop` that seat in this same beat,
before ending the turn. Update the heartbeat prompt, and end the turn.

`kind` is `idle` when the worker's turn ended and `terminated` when its
process exited; a finished turn is a full trigger, and you never kill a
worker to be notified. `permission_required` is a bound worker's agent raising
`session/request_permission` mid-turn — a wake, not an idle; the ordinary
`idle` still arrives at turn end. The event carries only `request_id`:
decide it from the worker's live `pending_permissions` — inside existing
authorization or escalated to the user.

## 3. Workers and the notification carrier

The worker Agent owns its delivery; it never fabricates events and never writes
to your stdin — its holder sends the event over your holder's admin socket.
Never ask a worker to notify you or duplicate the carrier.

Delivery rules you can rely on:

- Busy Host: the event is staged and delivered at your next turn boundary, never
  injected mid-turn, and a worker event is never turned into steering. One that
  finished before your turn ended stages the same way: the race can neither
  skip nor double-dispatch.
- Duplicate `event_id`s collapse; several pending events arrive in one prompt
  with the full current body.
- Confirmation follows the notification turn *completing*; after a resume,
  unconfirmed events are redelivered at least once — keep each pass idempotent.
- Dispatch failure or unknown acceptance means you are **not** reliably
  event-driven: recover it this beat, or report the exception.

Steering (`steer`, where supported) is a separate tool and does not alter this
wake path.
