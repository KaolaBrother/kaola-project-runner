# Startup: ordinary worker flow, Host flow, and the startup receipt

Read this when choosing between the two entry points, when an outer Agent starts
a ZCode Orchestrator (Host), or when a Host session is doing its own startup.
Every command is the installed form; no platform argument, no new tool.

```bash
WORKER="$HOME/.zcode/skills/codex-kaola-project-runner/scripts/runtime-tmux.sh"
HOSTRUN="$HOME/.zcode/skills/zcode-kaola-project-runner/scripts/runtime-tmux.sh"
PROJECT="/abs/path/to/project"     # the consuming project's canonical Git root
```

## A. Ordinary worker supervision

You keep authorization, dispatch, acceptance and close-out in your own session.
Nothing below in this file applies: no event binding, no heartbeat file, no Host.

```bash
"$WORKER" start   --repo "$PROJECT" --session codex-KT-i274-parser
"$WORKER" send    --repo "$PROJECT" --session codex-KT-i274-parser --text '<the task>'
"$WORKER" observe --repo "$PROJECT" --session codex-KT-i274-parser
"$WORKER" capture --repo "$PROJECT" --session codex-KT-i274-parser --lines 200
"$WORKER" stop    --repo "$PROJECT" --session codex-KT-i274-parser
```

That one exact name is the issue-scoped dispatch name of
[issue-dispatch.md](issue-dispatch.md): the platform id, the consuming project's declared
heartbeat short code, `i` plus the real issue number, and a purpose token. All five
operations use it unchanged.

Check each receipt: a `start` without a ready session started nothing, a `send`
`error` dispatched nothing, and a `prompt_timeout` or missing receipt leaves
consumption **unknown** — `observe` establishes the fact before anything is
re-sent. Blocking `send` is a normal, supported way to wait here.

## B. Outer Agent: starting a Host

1. **Recover first.** Read the project's run records, Git/forge state and live
   Runner sessions. An existing Host, claim or dispatch is resumed, never
   re-created; do not claim or start a second one for the same work.
2. **Start the Host at the canonical project root** under an exact name, and
   confirm from the receipt that this session is ready and is the identity you
   meant (`session`, `repo`, `acp_session_id`).

   ```bash
   "$HOSTRUN" start --repo "$PROJECT" --session zcode-kaola-host
   ```

3. **Hand over what a Host cannot discover** in one non-blocking prompt: its own
   `platform`/`session`/`repo`; the main Skill directory it must load and whether
   that is the installed release or a candidate checkout; the path of the existing
   Project Plan or already-authorized task plan; the authorized platforms and
   count; whether it may implement itself; the acceptance and finalize boundary;
   and the existing runs and worker session names.

   ```bash
   "$HOSTRUN" send --repo "$PROJECT" --session zcode-kaola-host --no-wait --text '<handover>'
   ```

4. **Read the startup receipt, then verify it against evidence.** The Host's own
   claim of having loaded the Skill is not evidence, and its tool record may show
   only that read and execute calls happened when `locations`/`rawInput` are
   absent; the translator forwards those fields only when the app-server `input`
   already named a path or command as a bounded receipt (registered secrets
   redacted; not a full-input scrub), and never invents a path - so
   check what does not depend on its
   prose: the roles, authorization and lifecycle boundary against the plan file
   you read yourself; quotes it could only produce from that plan and this
   reference; and the artifacts this procedure leaves behind (a
   `.kaola/heartbeat-prompt.json` with a usable `body`, a start receipt echoing
   `heartbeat_host`, a `--no-wait` dispatch receipt, a turn that ended with no
   sleep, poll or stop). A wrong role, a missing authorization or a contradiction
   is corrected before any dispatch; unauthorized, it stays idle.
5. **Verify the first real event loop**: a bound worker `start`, a `--no-wait`
   dispatch, the Host's turn ending on its own, and a `kaola-host-notify/1` pass
   arriving from a worker event. A background blocking `send` that returns to a
   human or outer Agent is not that loop and does not prove it.
6. **Keep, then stop.** A Host that ended its turn with workers in flight or with
   delivery, acceptance or close-out open is not idle: keep it and send no
   "continue" — its next beat is a worker event. Stop it exactly, by name, once
   delivery, acceptance, Workflow finalize/archive/sink and cleanup are verified.

## C. The Host's own startup and beat

Load the main Skill, read the plan and the project's recovery records, and answer
with a short startup receipt: role, authorization (platforms, count, implement or
supervise-only), lifecycle target and stop boundary, where those facts came from,
whether notification binding is in place, and every unresolved conflict. Then,
**before the first dispatch**, write the working heartbeat prompt to
`<project>/.kaola/heartbeat-prompt.json` as JSON with a non-empty string field
named exactly `body` (see `references/heartbeat-skeleton.md`). Any other field
name leaves the delivered notification carrying a reported defect instead of your
prompt — read that line in the notification and fix the file.

The beat itself - per-worker `KAOLA_ACP_HEARTBEAT_HOST` binding and its receipt
check, non-blocking dispatch, the `dispatch_event_cursor` reading anchor, ending
the turn as the wait, and reading the worker's real reply when an event wakes you
- is one procedure, written once in
[zcode-host-dispatch.md](zcode-host-dispatch.md). Follow it from there rather
than from a second copy.

## D. Which record holds what

| Record | Holds |
|---|---|
| Project Plan / authorized task plan | roles, authorization, lifecycle and stop boundary |
| Workflow Mission List | engineering progress and delivery per run |
| `.kaola/heartbeat-prompt.json` `body` | current identity, binding, run paths, next step |
| Runner receipts and holder events | what actually happened |

Keep them separate: no second plan is generated, no project history is rewritten,
and the heartbeat body is not a copy of the Mission List. A `done`/`todo`
contradiction goes back to the record's owner; the Runner never rules work
complete. Report which main-Skill payload was loaded when a candidate checkout
and an installed release both exist.
