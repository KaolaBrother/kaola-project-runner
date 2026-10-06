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

You own the Delegator file. Use its tool for reads and writes:

```bash
TOOL="<skills>/kaola-project-runner/scripts/kaola-dispatch.py"
FILE="$PROJECT/.kaola/delegator-heartbeat.json"
python3 "$TOOL" delegator view --file "$FILE"
python3 "$TOOL" delegator migrate --file "$FILE"
# After you reconcile all blocked grants and pending duties from their sources:
python3 "$TOOL" delegator migrate --file "$FILE" --write
python3 "$TOOL" delegator update --file "$FILE" --writer delegator --source '<source>' \
  --expect-revision <current revision> --set '<typed current change>'
```

For an old untyped file, plan the upgrade before `--write`. Keep applicable unresolved
owner duties in typed `watch` rows with original source references. A handled
row leaves stored `watch`: `update --expect-revision REV --source ORIGINAL
--set '{"watch":{"ID":null}}'`. `adopted` or `settled` with original effect
evidence also removes it; `sent` remains pending. Do not move settled text to
another field. An absent row is not created. An unresolved unclassified matter
keeps original evidence on the current decision/reconciliation route.
Use exact preset ids and integer counts; no standalone aggregate or Worker pool cap.
Migration removes only null or provably redundant legacy limits. Conflicting or
total-only intent needs original owner reconciliation and a sourced, revision-bound
null removal through the existing update; never expand authority silently. Do not infer counts or switch
permission from a condition. The plan gives each blocked path, its allowed
form, and recovery. A refusal leaves the file unchanged. Normal updates write
the same closed `kaola-delegator-heartbeat/1` form. `execute` reports an old
schema as a migration observation. Existing Host work and legacy transport
continue. Installation and live migration need their own authorization.

## User-facing writing

Ordinary user questions, progress replies and inquiry reports use the recorded
reply language (`project.user_language`); an unset value keeps the existing
conversation preference. Agent-to-agent messages and documentation keep their
own language. The style standard sets style, not language; it does not force
English.

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
   requirement; a received message is not proof it was adopted. Include one
   concise `seats` summary for the user: Elite/Expert exact preset ids, counts,
   Expert task/standing lifetime, occupied linked tasks and idle available
   capacity. Count each shared tier group once (Claude one; Droid count two
   when granted). Working, idle-but-unreclaimed, reserved, held/faulted and
   unknown are distinct; `ready` alone proves none of them. Unknown is not free.
   Missing Expert authorization says “none”. Derive totals from grant/shared counts
   and occupancy; keep service/quota/fault restrictions in their proper roles. Host/Sideagent and
   Pool seats are exempt. The view derives these facts from current grants,
   dispatch/task links and fresh Runner records. Keep no occupancy table in
   either JSON. External QA target capacity needs its original resource receipt.
   Host reads the same `project --seats` facts only when needed for dispatch;
   there is no compulsory Host report or added injection. Missing facts stay
   explicit; `--live`, `--index` and `--availability` accept existing receipts.
2. Special situations: holds, alerts (`watch`, `warn`, `severe`), major
   pending decisions and `unverified` items. Every unresolved one is reported
   again each time, coalesced, never escalated by elapsed time alone. With a
   node-mode Sideagent, `maintenance.last_verified` (batch, node, time) beside
   open duties shows whether maintenance still progresses; a
   `maintenance-returned` alert is the Host's to resolve. The view also shows
   pending Host changes and `maintenance.recovery_input`/`recovery_seq`. Correlate
   an owed batch, failed/missing recipe, checkpoint or stop with original receipts.
   Ask the sole Host for bounded reconciliation from those sources; it can call
   `state recovery-input --kind request` without a new business revision. Keep your
   recovery watch until scoped action evidence. Equal sequence, elapsed time or
   generic `last_verified` alone proves neither failure nor settlement. Reuse a
   justified in-flight node; do not control workers or request an all-state audit.
3. Tasks in progress (`doing`).
4. Tasks to do (`todo`).
5. This round's outcomes and next steps.

## What stays yours

You confirm user decisions, relay changes to the Host, and recover the Host by
the existing handoff rules. You do not record Host verdicts, choose workers or
edit Host records. A missing Expert grant the Host asks for is a decision for the
user; a busy granted seat is a capacity wait, not a request. If the Host and
its Sideagent both fail, recover the Host first; the Host replaces its
Sideagent. A request from the Host reaches you only at your next read; there
is no faster carrier.

Current authorization stores one grouped count, choices and switch permission.
Choices alone do not permit switching. Derive Class/defaults and capabilities
from the matched catalog, grants/default pool, exclusions, holds and availability;
unknown stays explicit. Store only owner overrides. Remove settled grants and
relays; keep active exclusions, pause reopening and exact stop/handoff duties.
Keep the current objective and source pointers, not adoption history or copied
Skill rules. AGENTS user requirements remain the source. Ambiguous legacy
count/switch intent needs original evidence and owner recovery before migration.
