# Lifecycle state

`<project>/.kaola/heartbeat-prompt.json` schema `kaola-heartbeat-prompt/2`
holds current tasks, the adopted authorization projection, the Sideagent
binding, holds, alerts and pending decisions. Its `body` is the generated Host
view, not a second source. Change it only through `state` in
`scripts/kaola-dispatch.py`; a hand edit skips revision checks. The Delegator
file, dispatch index, Runner receipts, Git, forge and Workflow keep their own
facts; state keeps references, current conclusions and next steps, never a
copied backlog, ledger or history.

## Roles

- Host: goal, task split, needed abilities, dependencies, preset choice,
  assignment text, `execute`/`collect`, reading original results, acceptance
  and closeout decisions; bootstrap, failure and urgent recovery. It may read,
  search, analyze and do simple authorized work itself.
- Tools record dispatch, result and holder facts; no node restates them.
- Sideagent: one maintenance role per project, outside every Class seat; a
  fresh node per meaningful batch. It reconciles duties, holds, alerts,
  conflicts and reclaim, and exact-stops finished workers. It assigns, grants
  and accepts nothing. Launches use bypass permissions; a residual prompt is an
  exception, and anything needing the user stays a pending `decisions` record.
- Research, QA or implementation helpers are counted, authorized items.
- Workers never write state (`writer-refused`).

No synchronous Sideagent round trip or approval stage per action: coalesce
related updates and reuse valid evidence. The Host gets outcomes, capacity and
pending decisions; evidence stays by reference.

## Commands

`S="python3 $SKILL_DIR/scripts/kaola-dispatch.py state"`. Every write takes
`--file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host|sideagent
--source "<event, receipt or Host turn>"`.

- `$S init [--project JSON] [--authorization JSON]`: Host only; refuses an
  existing file (migrate it).
- `$S update --kind tasks|holds|alerts|decisions --id ID --set PATCH
  [--expect-rev N]`: JSON merge patch of one record (`null` deletes a key;
  `@path` reads a file). An existing record needs `--expect-rev`; a stale one
  exits 3 with `current` and `unapplied`: merge by evidence and retry, never
  rewrite the file. `--coalesce` counts a repeated alert.
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
- `holds` (`scope`, `reason`): `evidence`, `impact`, `owner`, `resume_when`,
  `next`. A hold keeps the grant; no takeover or quota reset lifts it.
- `alerts` (`level` `watch|warn|severe`, `summary`): level by evidence and
  impact, never by elapsed time. Read, acknowledged or in progress is not
  resolved; a warning blocks no unrelated work.
- `decisions` (`owner` `host|delegator|user`, `question`): kept until
  `status: settled` with evidence (Sideagent: with `--host-turn`); a
  notification clears no duty.

Authorization, occupancy, task stage and service availability stay separate
facts. A stopped process deletes no task.

## Touchpoints

Update at existing events only: dispatch (task `doing`; plan items carry
`task_id`, `output`, optional `requires`), result and verdict, a material
goal, grant or fault change, recovery or adoption, and closeout. The inquiry
and `check` catch omissions. At a result or verdict, relate it to the task
goal and set the next authorized action or a sourced blocker. Confirming a
stop does not finish that goal. No goal score and no per-dispatch approval.

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
