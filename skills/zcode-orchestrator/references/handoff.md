# One Host handoff

Read this when starting or resuming the ZCode Host. Every command is the
installed ZCode Runner; no new tool, scheduler, or heartbeat.

```bash
ZCODE="<skills>/zcode-kaola-project-runner/scripts/runtime-tmux.sh"
PROJECT="/abs/path/to/consumer-project"   # as the user authorized it
HOST="zcode-kaola-host"                   # exact existing name if one exists
```

`<skills>` is the sibling Skill directory on this host, or `ROOT/skills` after
the Grok Bot bridge has bound a target and located ROOT. Never search the
filesystem for it.

## Recover, then one session

1. Read existing run records and live Runner sessions. Resume an existing Host
   for this work (`start --resume` when a native id is known, else
   `--continue`). Do not start a second Host, and do not rename, restart, or
   cancel the one already running.
2. If none exists:

   ```bash
   "$ZCODE" start --repo "$PROJECT" --session "$HOST"
   ```

   Confirm the receipt: ready, and `session`/`repo`/`acp_session_id` are the
   identity you meant.
3. One non-blocking handoff. Do not set `KAOLA_ACP_HEARTBEAT_HOST`. Do not
   start any other platform.

   ```bash
   "$ZCODE" send --repo "$PROJECT" --session "$HOST" --no-wait --text '<handoff>'
   ```

## Handoff text

Give the Host only what it cannot discover plus the extracted authorization.
Keep concurrency, account quota, and token budget as three numbers.

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

A later quota or priority update is another `--no-wait` send to this same Host,
replacing those fields only.

## Afterward

`observe` / `capture` this Host to read delivery. Relay user changes here.
Escalate only an unrecoverable human decision. Do not `stop` a Host that still
has in-flight workers or open close-out. Exact `stop` is for this Host session
after those duties end, never for inner workers.
