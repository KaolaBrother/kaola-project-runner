# Lifecycle state

`<project>/.kaola/heartbeat-prompt.json` schema `kaola-heartbeat-prompt/2`
holds current tasks, the adopted authorization projection, the Sideagent
binding, holds, alerts and pending decisions. Its `body` is the generated Host
view, not a second source. Change it only through `state` in
`scripts/kaola-dispatch.py`: a hand edit skips revision checks and can lose a
decision. The Delegator file, dispatch index, Runner receipts, Git, forge and
Workflow keep their own facts; state keeps references, current conclusions and
next steps, never a copied backlog, ledger or history.

## Roles

- Host: goal, task split, needed abilities, dependencies, acceptance and
  closeout decisions; bootstrap, failure and urgent recovery. It may read,
  search, analyze and do simple authorized work itself; not every action goes
  through the Sideagent.
- Sideagent: one bound maintenance seat per project, outside every Class seat.
  Inside current authorization, profiles and real capacity it selects presets,
  runs `execute`/`collect`, records results, holds and alerts, and exact-stops
  finished workers. It creates no grant or requirement and accepts nothing. It
  settles an ordinary confirmation only inside the exact assignment and tool
  policy; anything absent, ambiguous or needing the user stays a pending
  `decisions` record.
- Parallel research or QA helpers are worker items, authorized and counted.
- Workers never write state (`writer-refused`).

No synchronous Sideagent round trip or approval stage per action: coalesce
related updates and reuse valid evidence. The Host gets outcomes, capacity and
pending decisions; technical evidence stays reachable by reference.

## Commands

`S="python3 $SKILL_DIR/scripts/kaola-dispatch.py state"`. Every write takes
`--file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host|sideagent
--source "<event, receipt or Host turn>"`.

- `$S init [--project JSON] [--authorization JSON]`: Host only; an existing
  file is refused (migrate it).
- `$S update --kind tasks|holds|alerts|decisions --id ID --set PATCH
  [--expect-rev N]`: JSON merge patch of one record (`null` deletes a key;
  `@path` reads a file). An existing record needs `--expect-rev`; a stale one
  exits 3 with `current` and `unapplied`: merge by evidence and retry, never
  rewrite the file. `--coalesce` counts a repeated alert.
- `$S update --section project|authorization|sideagent|recovery|unverified
  --expect-revision N --set PATCH`: the first three are Host-only.
- `$S retire --kind K --id ID --expect-rev N --evidence REF [--outcome T]`.
- `$S view --role host|sideagent|delegator [--repo ROOT]` (read-only).
- `$S check [--index I] [--live L] [--repo R]`: read-only problems such as
  `doing-untraced`, `done-not-retired`, `transcription-unechoed`,
  `sideagent-not-live`, `carrier-unproven`.
- `$S migrate [--index I] [--live L] [--repo R] [--write]`; `$S timer`
  is the Delegator's.

## Records

- `tasks` (stable id; `stage` `todo|doing|review|closeout|done`, `goal`):
  `source`, `scope`, `needs`, `depends`, `acceptance`, `keep_open`, `wait`,
  `dispatch` (index item ids), `evidence`, `next`, `verdict`. A repair keeps the
  task id; one returned branch is not task completion. No issue, an adopted
  issue, or an issue kept open are all valid; Workflow owners keep
  claim/ledger/finalize.
- `holds` (`scope`, `reason`): `evidence`, `impact`, `owner`, `resume_when`,
  `next`. A hold keeps the grant. A successful takeover or a quota reset time
  does not lift it.
- `alerts` (`level` `watch|warn|severe`, `summary`): level by evidence and
  impact, never by elapsed time. Read, acknowledged or in progress is not
  resolved; a warning blocks no unrelated work.
- `decisions` (`owner` `host|delegator|user`, `question`): kept until
  `status: settled` with evidence. A notification clears no duty.

Authorization, occupancy, task stage and service availability stay separate
facts. A stopped process deletes no task; a hold revokes no grant.

## Touchpoints

Update at existing events only: dispatch (task `doing` and its `dispatch`
ids; plan items carry `task_id`, `output` and an optional `requires`), result
and verdict, a material goal, grant or fault change, recovery or adoption, and
closeout. The existing inquiry and `check` catch omissions.

## Host verdicts

`verdict.value` (`accepted|partial|repair|cancelled`) and the Host-owned task
fields (`goal`, `scope`, `acceptance`, `needs`, `depends`, `source`,
`keep_open`) are Host decisions. The Sideagent records one only with
`--host-turn <the Host turn it copies>`; the next Host view lists it under
`attention` until the Host writes that task. The Host corrects a wrong
transcription with its own `update`, which is also the bootstrap and degraded
path. Partial acceptance keeps the unfinished scope open.

## Sideagent binding

The Host starts the Sideagent, then sets `--section sideagent`
`{"platform","session","preset","state":"active"}`; the started Sideagent may
add its own `holder_instance_id` once. One reply ending is not the end of the
duty. To replace, the Host marks `replacing` or `failed`, starts a successor
under a new name and binds it; the successor continues from state, index and
receipts and replays no admitted work. A Sideagent stop spares Runner holders
it started; a superseded seat's late write is `binding-superseded`. A failed
Sideagent is never asked to repair its own record; the Host writes directly
and holds that runtime within Sideagent recovery. If both fail, the Delegator
recovers the Host first.

## Events

`execute` records the real dispatcher (`KAOLA_ACP_DISPATCHER`) apart from the
notify target. Workers the bound Sideagent starts report to its live Host
holder (`sideagent-host`). A Host holder advertising `sideagent-relay/1` relays
them to the live bound Sideagent, which confirms at turn end and wakes the
Host only when attention changed; a busy Sideagent keeps them, a dead one
falls back to the Host. Delivery is at-least-once and only a wake hint:
rebuild from index and receipts. A notify-target change never restarts a
healthy worker.

## Size

Repeats update the same id. Retire a task only once done or cancelled with
applicable closeout and confirmed seat stop; a capped tombstone keeps the
evidence, and a late event gets `record-retired`. Never drop an open duty to
fit. The Host view is bounded at 64 KiB (`host-view-too-large`). The file may
reach 1 MiB only after the live Host holder advertises `heartbeat-state/2`
and migration recorded it as `carrier`, else 64 KiB (`carrier-limit`).

## Migration

At the first load of an updated Skill, at a safe point, run `$S migrate` with
`--index` and `--live`; without `--write` it is a read-only plan. With
`--write`, v1 `active` becomes `doing` tasks keyed by `ref`, `pending` becomes
closeout/review duties, `recovery` is kept, unknown keys and unassociated
index rows become `unverified`, one live Sideagent row becomes the binding,
and the live Host holder's features become `carrier`. The raw v1 file is kept
once as `heartbeat-prompt.v1-<sha12>.json`; a conflicting raw copy or an
unreadable file is left untouched. A repeat reports `current`; after a Host
holder upgrade, `migrate --write --live` records the carrier. Migration resets
no task, replays no dispatch, re-plans nothing, re-asks no confirmed user
requirement and restarts no healthy session. Unknown or conflicting items
stay `unverified`, never a new grant.

Unproven until live runs: per-platform process preservation, cross-platform
carrier re-anchor, relay across holder death, native timer read-back and
real-project state size.
