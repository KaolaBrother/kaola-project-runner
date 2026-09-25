# Host: dispatch, end the turn, wake on worker events

Host beat: [host-startup.md](host-startup.md). Outer start: Kaola-Delegator
(`kaola-delegator`).

## Three identities, never interchangeable

Runner session (what `--session` takes, chosen at `start`), ACP session id
(`acp_session_id` in receipts) and native session id (`sess_…`, for `--resume`)
are different things. A `sess_…` value is never a Runner session name. Never
guess a session name. `holder_pid` is a fourth fact that proves nothing without
`holder_instance_id`.

Each installed Skill's `scripts/runtime-tmux.sh` is platform-pinned, so the
commands below take **no** platform argument.

## One Host beat

### Start a worker from this Host

```bash
W="/abs/path/to/codex-kaola-project-runner/scripts/runtime-tmux.sh"
WORK_REPO="/abs/path/to/project"      # the worker's repo
"$W" start --repo "$WORK_REPO" --session codex-KT-i274-parser
```

Run `start` from your own session: it binds the worker to you and refuses
(`result: refused`, `reason: heartbeat-host-…`, exit 1) instead of starting
unbound. The binding derives from `KAOLA_ACP_DISPATCHER`; an explicit
`KAOLA_ACP_HEARTBEAT_HOST` that differs refuses `heartbeat-host-conflict`. A PTY request is refused on every command
(`transport-pty-retired`): the Runner is ACP-only. Worker names
are issue-scoped: `<platform>-<CODE>-i<ISSUE>-<purpose>`.

Count before every `start`: live owned sessions, ACP holders included -
identity-verified (`list --repo` rows with `identity: verified`, the holder
answering with its recorded `holder_instance_id`); a PID alone is not a seat. At
the hard cap: stop-before-start (main Skill step 2). A different task is a new
session (main Skill §Ending a run).

### Read the binding in force, new worker or reused

```json
"heartbeat_host_known": true,
"heartbeat_host": {"platform":"zcode","session":"zcode-KT-orchestrator-main","repo":"…","socket":"…"},
"heartbeat_host_source": "dispatcher",
"dispatcher": {"holder_instance_id":"…","platform":"zcode","repo":"…","session":"zcode-KT-orchestrator-main"}
```

`heartbeat_host` is the running holder's own binding; `heartbeat_host_requested`
is only the request; `observe` reports the binding any time.

- `"error": {"code": "session-exists"}` — you reused a live holder, which keeps
  its binding.

### A stale seat is not a dispatch target

Before `send` or `steer`, read `status`. `stale: true` means a restart-required
file this seat loaded now differs on disk: `kaola-acp-holder.py`,
`kaola-zcode-acp.py`, `scripts/adapters/`, or the platform manifest
(`stale_reasons`, `restart_files`). That is the same set as the release-note
operator test. `reported_drift` may list `pin-drift`, `cli-drift`
(`kaola-acp.py`, `kaola-tmux.sh`), `quota-drift` (`kaola-quota.py`),
`recorded-path-missing` (a recorded script path no longer exists), or
`install-root-mismatch` (the seat's install tree moved or was re-rooted);
those do not block. `baseline_exempt` is
true only for a direct checkout start; a `~/.local/bin` start is not exempt.
Do not dispatch a `stale: true` seat. An operator-confirmed exception on that
one `send`/`steer` is the orchestrator's own call; there is no flag.
There is still no rebind. `drain-restart --continue` or `--resume ID` checks
start refusals first, waits for idle, exact-stops, and starts again carrying
the recorded model/effort/tier/fast. Run it from this Host so the new start
adopts your instance. `seats_naming_previous_instance` names seats still bound
to the old Host; they are not edited in place.

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
report as main Skill §Report says, then **end your reply normally**.

There is no "wait mode" command to call. Ending the turn *is* the wait. Do not
`sleep`, poll in a loop, or hold this turn open with a blocking `wait` — an
active Host turn is exactly what keeps events undelivered. Do not `stop` or
`cancel` yourself or an in-flight worker to manufacture a wake-up.

### When an event wakes you

The next beat is an ordinary prompt: first line `/kaola-project-runner`,
then `kaola-host-notify/1`, one JSON object per event —

```json
{"event_cursor":19,"event_id":"codex/codex-KT-i274-parser/idle/19","kind":"idle",
 "platform":"codex","repo":"/abs/path/to/project","session":"codex-KT-i274-parser",
 "reason":"outcome=turn_completed stop_reason=end_turn"}
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
same assignment); once accepted, exact-`stop` that seat this beat (main Skill
step 5). Update the heartbeat prompt, and end the turn.

`kind` is `idle` when the worker's turn ended (`reason`
`outcome=<turn_completed|turn_failed> stop_reason=<…>`) and `terminated` when
its process exited (`exit_code=N` or `exit_signal=N`); a finished turn is a full trigger, and you never kill a
worker to be notified. `permission_required` is a bound worker's agent raising
`session/request_permission` mid-turn — a wake, not an idle; the ordinary
`idle` still arrives at turn end. The event carries only `request_id`:
decide it from the worker's live `pending_permissions` — inside existing
authorization or escalated to the user.

## Workers and the notification carrier

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
