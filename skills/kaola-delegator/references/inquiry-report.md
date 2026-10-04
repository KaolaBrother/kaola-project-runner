# Inquiry report and native timer

Both files stay at `<repo>/.kaola/` on the bound target, under the same paths
on every runtime. The Host lifecycle state is read through the Project Runner
state tool, never written by you:

```bash
STATE="python3 <skills>/kaola-project-runner/scripts/kaola-dispatch.py state"
$STATE view --role delegator --file "$PROJECT/.kaola/heartbeat-prompt.json" --repo "$PROJECT"
$STATE timer --repo "$PROJECT" --target local|cloud --entry '<this Skill entry line>' \
  --body-file <the native timer body read back>
```

`<skills>` is the sibling Skill directory, or the bridge's `ROOT/skills`.
A v1 file (`kaola-heartbeat-prompt/1`) has no Delegator view: audit its
`body` as before and ask the Host for `state migrate` at a safe point.

## Native timer

The timer body is exactly the Skill entry line plus one locator sentence:

`Kaola-Delegator inquiry: read <repo>/.kaola/delegator-heartbeat.json on target <target> and run the loaded Skill's standard inquiry.`

Frequency, window and day boundaries live in `cadence`; set the native fields
from it. At each inquiry, read the timer back where its API allows and run
`timer`. On `mismatch`, correct the timer, read it back, then continue this
inquiry. If it cannot be read back, report that plainly. This check never
delays an urgent stop, never stops in-flight work and never blocks an
unrelated user task.

## Fixed report

Pass valid evidence forward; recheck only changed facts or gaps. Every inquiry
report has these five parts, in order. An empty part says
“none”; a missing source is named.

1. User special requirements, listed in full from the `AGENTS.md` region
   (`user_requirements`). New owner direction replaces a conflicting old
   requirement; a received message is not proof it was adopted.
2. Special situations: holds, alerts (`watch`, `warn`, `severe`), major
   pending decisions and `unverified` items. Every unresolved one is reported
   again each time, coalesced, never escalated by elapsed time alone. With a
   node-mode Sideagent, `maintenance.last_verified` (batch, node, time) beside
   open duties shows whether maintenance still progresses; a
   `maintenance-returned` alert is the Host's to resolve.
3. Tasks in progress (`doing`).
4. Tasks to do (`todo`).
5. This round's outcomes and next steps.

## What stays yours

You confirm user decisions, relay changes to the Host, and recover the Host by
the existing handoff rules. You do not record Host verdicts, choose workers or
edit records. A missing Expert grant the Host asks for is a decision for the
user; a busy granted seat is a capacity wait, not a request. If the Host and
its Sideagent both fail, recover the Host first; the Host replaces its
Sideagent. A request from the Host reaches you only at your next read; there
is no faster carrier.
