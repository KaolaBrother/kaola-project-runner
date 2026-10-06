# Lifecycle state

`<project>/.kaola/heartbeat-prompt.json` (`kaola-heartbeat-prompt/2`) holds
current tasks, authorization, Sideagent binding, holds, alerts and decisions.
`body` is the generated Host view. Write through `scripts/kaola-dispatch.py
state` for revision checks. Other files retain their own authority; keep
references and current duties here, never copied backlog, ledger or history.

## Roles

- Host: goal, task split, needed abilities, dependencies, preset choice,
  assignment text, `execute`/`collect`, reading original results, acceptance
  and closeout decisions, including recovery. It may do simple authorized work.
- Tools record dispatch, result and holder facts; no node restates them.
- Sideagent: one maintenance role per project, outside every Class seat; a
  fresh node per meaningful batch. It reconciles current duties/conflicts and exact-stops finished workers. It assigns, grants
  and accepts nothing. Launches use bypass permissions; residual prompts and user decisions stay pending.
- Research, QA or implementation helpers are counted, authorized items.
- Workers never write state (`writer-refused`).

No synchronous Sideagent round trip. Coalesce updates and reuse evidence.
The Host gets outcomes, capacity and pending decisions.

## Commands

`S="python3 $SKILL_DIR/scripts/kaola-dispatch.py state"`. Every write takes
`--file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host|sideagent
--source "<event, receipt or Host turn>"`.

- `$S init [--project JSON] [--authorization JSON]`: Host only; refuses an
  existing file (migrate it).
- `$S update --kind tasks|holds|alerts|decisions --id ID --set PATCH
  [--expect-rev N]`: JSON merge patch of one record (`null` deletes a key;
  `@path` reads a file). An existing record needs `--expect-rev`; a stale one
  exits 3 with `current` and `unapplied`: reconcile and retry. `--coalesce` counts a repeated alert.
- `$S update --section project|authorization|sideagent|recovery|unverified
  --expect-revision N --set PATCH`: first three Host-only.
- `$S retire --kind K --id ID --expect-rev N --evidence REF [--outcome T]
  [--index I --live L] [--handoff TASK]`: a task needs verdict `accepted` or
  `cancelled`, its dispatch items closed and seats stopped, or handed to a
  continuing `TASK`.
- `$S view --role host|sideagent|delegator [--repo ROOT]` (read-only).
- `$S checkpoint`, `update --index`: [sideagent-node.md](sideagent-node.md).
- `$S check [--index I] [--live L] [--repo R]`: read-only problems such as
  `doing-untraced`, `done-not-retired`, `transcription-unechoed`,
  `sideagent-not-live`, `carrier-unproven`.
- `$S migrate [--index I] [--live L] [--repo R] [--write]`; `$S timer`
  is the Delegator's.

## Records

- `tasks` (stable id; `stage` `todo|doing|review|closeout|done`, `goal`):
  `source`, `scope`, `needs`, `depends`, `acceptance`, `keep_open`, `wait`,
  `dispatch` (index item ids), `evidence`, `next`, `verdict`, `dispositions`
  (per item). A repair keeps the task id; one returned branch is not
  completion. A task needs no issue; Workflow owners keep claim/ledger/finalize.
- `holds` (`scope`, `reason`): active restrictions with `evidence`, `impact`,
  `owner`, `resume_when`, `next`. A hold keeps the grant.
- `alerts` (`level` `watch|warn|severe`, `summary`): applicable unresolved
  exceptions. Read, acknowledged or in progress is not resolved. Once handled,
  use `retire --expect-rev REV --evidence ORIGINAL`; it removes the stored row.
- `decisions` (`owner` `host|delegator|user`, `question`): open owner answers.
  Host settles with `update --set status/evidence ORIGINAL` or, judged
  handled, `retire --evidence ORIGINAL`. A Sideagent copy needs
  `--host-turn`, stays pending Host adoption, never judges currentness.

Views and injected bodies use the stored current collection. Keep no
handled row or retrospective text in another field. Unfinished effects remain
concrete current duties. Revoked/expired grants leave eligibility; current stop
restrictions and live links stay. A stopped process does not finish a task.
Refusals give id, revision and removal command. Do not create an absent row. Keep genuinely unresolved original evidence on the
current decision/reconciliation route until its proper type is established.
Unknown is not resolved; Agents judge semantic currentness.

## Touchpoints

Update at dispatch (`doing`; plan: dispatch-collect),
result/verdict, goal/grant/fault change, recovery/adoption and closeout. Inquiry
and `check` detect omissions. Link each result/verdict to its task goal and
next action or sourced blocker; no goal score or per-dispatch approval.

## Host verdicts

`verdict.value` (`accepted|partial|repair|cancelled`) and the Host-owned task
fields (`goal`, `scope`, `acceptance`, `needs`, `depends`, `source`,
`keep_open`) are Host decisions. The Sideagent records one only with
`--host-turn <the Host turn it copies>`; the next Host view lists it under
`attention` until the Host writes that task. The Host corrects a wrong
transcription with its own `update` (also the bootstrap and degraded path).
Partial acceptance keeps the unfinished scope open; moving a `repair` or
`partial` task back to `review` keeps that verdict as `prior_verdict` and asks
again. A task at `closeout` or `done` without `accepted`, `partial` or
`cancelled` stays under `attention` (`verdict-missing`).

## Sideagent binding

The Host starts the Sideagent, then sets `--section sideagent`
`{"platform","session","preset","state":"active"}`; the started Sideagent may
add its own `holder_instance_id` once. A reply ending is not the duty's end. To
replace, the Host marks `replacing` or `failed`, starts a successor under a new
name and binds it; the successor continues from state, index and receipts and
replays no admitted work. A Sideagent stop spares each worker it dispatched
(spawn line or its record's `dispatcher`); a superseded seat's late write is
`binding-superseded`. The Host, not a failed Sideagent, repairs its record and
holds it. If both fail, the Delegator recovers the Host first.

## Events

`execute` records the real dispatcher (`KAOLA_ACP_DISPATCHER`) apart from the
notify target. Workers the bound Sideagent starts report to its live Host
holder (`sideagent-host`). A Host holder advertising `sideagent-relay/1` relays
them to the live bound Sideagent, which confirms at turn end and wakes the Host
only when attention changed; a busy Sideagent keeps them; a dead one, or a
failed or cancelled Sideagent turn, returns them to the Host. Delivery is
at-least-once, a wake hint: rebuild from index and receipts. `"mode": "node"`
keeps events with the Host; a node takes a turn's Host changes ([sideagent-node.md](sideagent-node.md)).
After a Host replacement (`--preserve-dispatched-workers`), the new Host runs
the seat's `rebind-host` from its own session: only that seat's carrier moves;
the worker runs on, its `dispatcher` still the old Host. Each seat (Sideagent
too) needs its own call; events staged in a dead Host need adoption.
`unknown-op`: `drain-restart` the seat at idle.

## Size

Repeats update the same id. A settled record leaves the file. An old revision gets `record-retired`. Never drop an open duty to fit. The Host view is
bounded at 64 KiB (`host-view-too-large`). The file may reach 1 MiB only with a
recorded `carrier` advertising `heartbeat-state/2`, else 64 KiB
(`carrier-limit`).

## Migration

After a Skill update, at a safe point, run `$S migrate --index I --live L`;
without `--write` it only plans. With `--write`, each v1 `active` row becomes
a `doing` task, `pending` keeps its stated stage or stays `todo`, and
`recovery.protected_untracked` stays when it is a list of strings. Other
legacy names leave and are not copied. Unknown keys become `unverified`
locators. A critical mapping writes nothing. Do not write
`heartbeat-prompt.v1-<sha12>.json`. `state-overwritten` is not raised from
those copies. Hash-named copies are not deleted or trusted. An unknown schema
is refused. A clean repeat reports `current`. Migration grants nothing.

Live on Codex and ZCode only: preserve stop, `rebind-host`. Unproven: relay
across holder death, timer read-back, real state size.
