# One Host handoff

Outer Agents start, continue, or restore the project's one ZCode Host here.
Project Runner inside that Host owns workers, heartbeat, and close-out. No new
tool, queue, registry, or scheduler.

```bash
ZCODE="<skills>/zcode-kaola-project-runner/scripts/runtime-tmux.sh"
PROJECT="/abs/path/to/consumer-project"          # bound canonical Git root
HOST="zcode-<PROJECT_CODE>-orchestrator-main"    # e.g. zcode-KPR-orchestrator-main
RECORD="$PROJECT/.kaola/delegator-host.json"     # current pointer only
```

`<skills>` is the sibling Skill directory, or `ROOT/skills` after the Grok Bot
bridge located ROOT. If `$ZCODE` is missing, stop: this Skill is not executable
without the ZCode Runner. Never search the filesystem for it.

`<PROJECT_CODE>` is the project's established short code. Ask once if none is
recorded. Inner workers keep `<platform>-<PROJECT_CODE>-i<ISSUE>-<purpose>`
(#72). The Host name is not an Issue worker and does not use `i0`.

Three identities stay separate, from real receipts, never synthesized:

| Field | Source | Use |
|---|---|---|
| Runner `--session` | you choose it (`$HOST`) | live attach, observe, send, stop |
| `acp_session_id` | ACP `session/new` on the start receipt | ACP bridge id |
| native `sess_*` | `session/update` `native_session_identity.nativeSessionId` | `start --resume` after the holder stopped |

`session_meta` does not automatically hold `sess_*`. Read the Host event log or
observe output for `native_session_identity`. After a successful start or
restore, write `$RECORD` with those three fields plus target, `$PROJECT`,
`platform=zcode`, and any holder-instance facts the start receipt already
named. Keep only the current pointer.

## Recover

1. Bind the same execution target and `$PROJECT`. Read `$RECORD` and live
   Runner sessions for `$HOST`.
2. **Live Host** (exact platform/repo/session still serves): do not `start`.
   Continue communication on that locator. Changing the outer Agent does not
   stop the Host, start a second Host, or replay the first handoff.
3. **Stopped Host** with an attested native `sess_*` in `$RECORD`: restore
   only that context:

   ```bash
   "$ZCODE" start --repo "$PROJECT" --session "$HOST" --resume "$NATIVE_SESS"
   ```

   Then update `$RECORD` if the holder instance changed. Never use `--continue`
   to guess a same-directory worker.
4. Missing, mismatched, or unattested `sess_*` is cannot-resume: report and
   wait. Do not create a new Host and call it continuation.
5. No Host yet: start once at the canonical root under `$HOST`. Confirm
   `session`/`repo`/`acp_session_id`, then wait for `native_session_identity`
   before writing `$RECORD`.

Do not rename, restart, or cancel an in-flight Host to adopt this Skill.

## First handoff and later updates

Do not set `KAOLA_ACP_HEARTBEAT_HOST`. Do not start any other platform.

Idle Host: `send` is enough. `--no-wait` means admitted, not delivered, and not
project complete. A first Host `end_turn` is only that beat finishing.

Busy Host (`prompt-in-progress` / turn active): do not claim a `--no-wait` send
was consumed. Use the ZCode Runner's existing `steer` when that is the chosen
update, or keep the user change undelivered until a safe idle send. `unknown`
or `not_consumed` is not a resend. Never invent a queue.

```bash
"$ZCODE" send --repo "$PROJECT" --session "$HOST" --no-wait --text '<handoff>'
"$ZCODE" observe --repo "$PROJECT" --session "$HOST"
"$ZCODE" capture --repo "$PROJECT" --session "$HOST" --lines 200
```

Handoff text (concurrency, account quota, and token budget stay three numbers):

```text
Load <skills>/kaola-project-runner/SKILL.md (Project Runner) and follow it.
You are the ZCode Host for this run.
platform=zcode session=<HOST> repo=<PROJECT>
goal=<user goal>
done=<already done>
remaining=<remaining work>
authorized_platforms=<id:count, ...>
quota_concurrency=<n>
quota_account=<as given>
quota_token=<as given>
priority=<as given>
delivery_stop_boundary=<as given>
project_context=<canonical root and other given facts>
Finish planning, worker dispatch, notification binding, heartbeat, acceptance,
and Workflow close-out internally. Do not wait for the outer Agent to bind
workers, paths, scheduling, or heartbeat. Missing authorization stays missing:
do not expand it.
```

## Afterward

Read delivery with `observe` / `capture` on this Host. The outer session is not
woken automatically. Escalate only an unrecoverable human decision. Do not
`stop` the Host while workers, acceptance, or Workflow close-out remain; Host
`stop` sweeps recorded inner processes. Exact `stop` uses the same `$PROJECT`
and `$HOST` after those duties end, never inner workers.
