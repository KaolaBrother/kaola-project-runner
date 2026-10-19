# Failed Host resume

Use this when a Host session cannot be resumed: a timeout on a huge session,
`resume-failed`, `holder-lost`, an unowned exited launchd job, or a similar
refusal. Do not stay stuck retrying that session.

## 1. Fresh session

Exact-stop the old session when a holder or job may still exist, then attest.
This build does not auto-reap an unowned exited job. Issue #308's automatic
reap is not in this build.

```bash
"$RUNNER" stop --repo "$PROJECT" --session "$HOST" --expected-holder-instance-id "$HOLDER_ID"
```

`$HOLDER_ID` is `holder_instance_id` from `status`. Attest with the same
locator call the bridge already uses (`kaola-project-runner-locate`, or
`scripts/kaola-locate.py` on this checkout).

A fresh Host is `start` without `--resume`, and only after the current
authorization (handoff Recover step 4). Say that this is a new ACP session
and a new holder. Do not retry the dead session.

A dsh Host session keeps the permission preset it was born with: the resume
receipt reports `config_application.mode.applied: false` with
`reason: resumed-session-permission` and the session's recorded values under
`effective`. A session born confined (`workspace-write`) stays confined no
matter how it is resumed — gaining full access takes this fresh-session path
with a handoff summary, never another resume.

```bash
"$RUNNER" start --repo "$PROJECT" --session "$HOST" --no-wait --text '<handoff>'
```

A start with no brief only brings the seat up. `$RUNNER` is `runtime-tmux.sh` beside `kaola-acp.py`.

## 2. Hand the new Host the previous session

Build the summary from receipts that already exist. Include goals, decisions,
in-flight tasks, live seats and their holders, and pending items.

```bash
"$RUNNER" status --repo "$PROJECT" --session "$HOST"
"$RUNNER" capture --repo "$PROJECT" --session "$HOST" --lines 200
python3 "${RUNNER%/*}/kaola-acp.py" list --repo "$PROJECT" --include-dead
STATE="python3 <skills>/kaola-project-runner/scripts/kaola-dispatch.py state"
$STATE view --role delegator --file "$PROJECT/.kaola/heartbeat-prompt.json" --repo "$PROJECT"
TOOL="<skills>/kaola-project-runner/scripts/kaola-dispatch.py"
python3 "$TOOL" delegator view --file "$PROJECT/.kaola/delegator-heartbeat.json"
```

`<skills>` is the sibling Skill directory, or the bridge's `ROOT/skills`.
`delegator view` returns user requirements, holds, alerts, decisions, doing,
todo, sideagent, and pending host changes. `list --include-dead` names live
and dead rows.

## Live seats

The new Host re-adopts live seats. Never re-claim, re-dispatch, or redo them.
A live row has `host_class` and `identity: verified`. `host-exists` means
attach `existing_host`. Adopt a uniquely named live row the same way. Do not
rename it. Do not start a second Host for it.
