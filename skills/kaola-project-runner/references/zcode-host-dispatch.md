# Host: dispatch, end the turn, wake on worker events

Startup: [host-startup.md](host-startup.md); outer start: `kaola-delegator`.

## Three identities, never interchangeable

Runner session (`--session`), ACP session id (`acp_session_id`) and native
session id (`sess_…`, `--resume`) differ. A `sess_…` value is never a Runner
session name; never guess one. `holder_pid` is a fourth fact that proves nothing
without `holder_instance_id`.

Platform-pinned wrappers take **no** platform argument.

## One Host beat

### Start a worker from this Host

```bash
W="/abs/path/to/codex-kaola-project-runner/scripts/runtime-tmux.sh"
WORK_REPO="/abs/path/to/project"
"$W" start --repo "$WORK_REPO" --session codex-KT-i274-parser --tier luna
```

Run `start` from your own session: it binds the worker to you and refuses
(`result: refused`, `reason: heartbeat-host-…`, exit 1) instead of starting
unbound. The binding derives from `KAOLA_ACP_DISPATCHER`; an explicit
`KAOLA_ACP_HEARTBEAT_HOST` that differs refuses `heartbeat-host-conflict`. PTY
is refused (`transport-pty-retired`): ACP-only. Worker names
are issue-scoped: `<platform>-<CODE>-i<ISSUE>-<purpose>`.

Count before every `start`: live owned sessions, ACP holders included -
identity-verified (`list --repo` rows with `identity: verified`, the holder
answering with its recorded `holder_instance_id`); a PID alone is not a seat.
Worker-class pool seats (worker-profiles.md) are outside the count. At
the hard cap: stop-before-start (main Skill step 2).

### Read the binding in force, new worker or reused

```json
"heartbeat_host_known": true,
"heartbeat_host": {"platform":"zcode","session":"zcode-KT-orchestrator-main","repo":"…","socket":"…"},
"heartbeat_host_source": "dispatcher",
"dispatcher": {"holder_instance_id":"…","platform":"zcode","repo":"…","session":"zcode-KT-orchestrator-main"}
```

`heartbeat_host` is the running holder's binding; `heartbeat_host_requested`
is only the request; `observe` reports it any time.

- `"error": {"code": "session-exists"}` — you reused a live holder, which keeps
  its binding.

Before the first send, match `model_selection`/`config_application`/
`effective_selection` against the selected preset, not the command's default;
aliases read through this platform's evidence, and `applied: true` isn't
proof. Outside grant: exact-stop an unused seat and start the intended
`--tier`; a working seat uses drain-restart below, correcting explicitly.

### A stale seat is not a dispatch target

Before `send` or `steer`, read `status`. `stale: true` means a restart-required
file this seat loaded now differs on disk: `kaola-acp-holder.py`,
`kaola-zcode-acp.py`, `kaola-quota.py`, `scripts/adapters/`, or the platform
manifest (`stale_reasons`, `restart_files`). `reported_drift` lists report-only drift codes and is non-blocking.
Do not dispatch a `stale: true` seat. An operator-confirmed exception on that
one `send`/`steer` is the orchestrator's own call; there is no flag or
rebind. `drain-restart --continue` or `--resume ID` checks
start refusals first, refuses `drain-not-idle` at once if the seat is busy
(leaving it up - you own the retry), otherwise exact-stops the idle seat and
starts again carrying the recorded model/effort/tier/fast. Run it from this
Host so the new start adopts your instance. Nothing scans other seats: the
`adoption` fact is the new start's own dispatcher.

### Dispatch without blocking

Host sends use `--no-wait`: direct Runner/Workflow, outside dispatch/collect,
continuation, repair and finalize. Omission is nonblocking only for proven live
Host ownership; `wait_selection` reports why. Flags win; standalone blocks.

```bash
"$W" send --repo "$WORK_REPO" --session codex-KT-i274-parser --no-wait --text '<the task>'
```

`--no-wait` returns admission: `"outcome": "in_progress"`,
`"mutation_status": "in_progress"` — running — not finished, and not correct. An error (`prompt-in-progress`, `agent-not-running`) dispatched nothing;
`prompt_timeout`/missing receipt means consumption unknown: `observe` before resending.

**Keep** `prompt_fingerprint` (the dispatched turn) and
`dispatch_event_cursor` (before its output).

### Finish the beat, then end your turn

Finish this beat; if current facts/duties changed, update the heartbeat at
`<project>/.kaola/heartbeat-prompt.json` through `state` (`body`: the Host view),
report as main Skill §Report says, then **end your reply normally**.

There is no "wait mode" command to call. Ending the turn *is* the wait. Do not
`sleep`, poll in a loop, or hold this turn open with a blocking `wait` — an
active Host turn keeps events undelivered. Background commands do not end the turn. Do not `stop` or
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
what happened with the event's own `platform`/`session`/`repo` using the
`observe`/`capture` commands below. Open that platform's Runner Skill again
only when its procedure is no longer in context, or for `permit` syntax.

**`event_cursor` is the end of the turn, not the start** — `19` is where that
turn ended, so `capture --since <event_cursor>` sees only carrier and title
updates. Read from an earlier anchor:

```bash
# dispatch receipt's cursor, before the reply existed
"$W" observe --repo "$WORK_REPO" --session codex-KT-i274-parser
"$W" capture --repo "$WORK_REPO" --session codex-KT-i274-parser --since "$DISPATCH_EVENT_CURSOR"
# no anchor (resumed Host): never --since <event_cursor>
"$W" capture --repo "$WORK_REPO" --session codex-KT-i274-parser --lines 200
```

Confirm you read the turn you dispatched: `observe`'s
`last_prompt.fingerprint` must equal the dispatch receipt's `prompt_fingerprint`,
and `turn_outcome`/`stop_reason` must show it finished. No assistant text
means the window was wrong — widen it. Then accept, send a routine repair, or task-failure, and keep or exact-`stop` the seat per main Skill step 5.
Update changed facts/duties; no full JSON reload after Runner returns. End the turn.

`kind` is `idle` when the worker's turn ended (`reason`
`outcome=<turn_completed|turn_failed> stop_reason=<…>`) and `terminated` when
its process exited (`exit_code=N`/`exit_signal=N`); a finished turn is a
full trigger — never kill a worker to be notified. `permission_required` is a bound worker's agent raising
`session/request_permission` mid-turn — a wake, not an idle; the ordinary
`idle` still arrives at turn end. The event carries only `request_id`, a
locator that approves nothing: decide it from the worker's live
`pending_permissions` (ignore a vanished request) — inside existing
authorization or escalated to the user.

## Workers and the notification carrier

A worker owns delivery and never fabricates events or writes your stdin; do not duplicate the carrier.

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

Steering (where supported) is separate and doesn't alter this wake path.
