# Lifecycle state

`<project>/.kaola/heartbeat-prompt.json` (`kaola-heartbeat-prompt/2`) holds
current tasks, authorization, Sideagent binding, holds, alerts and decisions.
`body` is the generated Host view. Write through `kaola-dispatch.py
state` for revision checks. Keep references and current duties here, never a
copied backlog, ledger, or history.

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

`S="python3 $SKILL_DIR/scripts/kaola-dispatch.py state". Writes take
(`--file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host|sideagent
--source "<event, receipt or Host turn>"`.

- `$S init [--project JSON] [--authorization JSON]`: Host only; refuses an
  existing file (migrate it).
- `$S update --kind tasks|holds|alerts|decisions --id ID --set PATCH
  [--expect-rev N]`: JSON merge patch of one record (`null` deletes a key;
  `@path` reads a file). An existing record needs `--expect-rev`; a stale one
  exits 3 with `current` and `unapplied`. `--coalesce` counts a repeated alert.
- `$S update --section project|authorization|sideagent|recovery|unverified
  --expect-revision N --set PATCH`: first three Host-only.
- `$S retire --kind K --id ID --expect-rev N --evidence REF [--outcome T]
  [--index I ... --live L] [--handoff TASK]`: needs verdict `accepted` or
  `cancelled`, items closed, seats stopped, or handed off. `L` is
  `list --repo --include-dead` rows; repeat `--index`, each ref in one file.
- `$S view --role host|sideagent|delegator [--repo ROOT]` (read-only).
- `$S checkpoint`, `update --index`: [sideagent-node.md](sideagent-node.md).
- `$S check [--index I] [--live L] [--repo R]`: read-only. Problems include
  `doing-untraced`, `done-not-retired`, `transcription-unechoed`,
  `sideagent-not-live`, `carrier-unproven`, `state-bloat`. `state-bloat`
  lists accepted-done and cancelled tasks, settled decisions, alerts whose
  `inputs` is empty, and shell tasks (evidence is only `retired:tasks/ID`,
  duty fields empty). Each names kind, id, rev, and a `state retire`
  command. A large row is a hint in `diagnosis`, not a gate. `done-not-retired`
  stays watch until `maintenance.handled_host_revision` covers it, then
  warns without refusing writes. `carrier-unproven` names `state migrate
  --live`. A row lacking `rev` is `record-versionless` and names the
  `migrate` plan; `--write` assigns `rev 1`. Check stores nothing.
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
  use `retire --expect-rev REV --evidence ORIGINAL`.
- `decisions` (`owner` `host|delegator|user`, `question`): open owner answers.
  A Delegator decision is a row here (`owner` `delegator` or `user`, `status`
  `pending`). The runner reads `state.decisions` and wakes `needs_decision`.
  A note only in `.kaola/run/*.md` or turn text does not. Host settles
  with `update --set status/evidence ORIGINAL` or `retire --evidence ORIGINAL`.
  A Sideagent copy needs `--host-turn` and stays pending Host adoption. No row:
  `retire --kind decisions --id ID --absent --evidence E` (receipt; stores nothing).

Views use the stored current collection. Keep no handled row elsewhere.
Unfinished effects stay current duties. A stopped process does not finish a
task. Refusals name id, revision and the removal command. Do not create an
absent row. Unresolved evidence stays on the current decision route. Unknown
is not resolved.

## Touchpoints

Update at dispatch (`doing`), result/verdict, goal/grant/fault change, recovery
and closeout. `check` detects omissions. Link each result to its task goal and
next action or sourced blocker.

## Host verdicts

`verdict.value` (`accepted|partial|repair|cancelled`) and the Host-owned task
fields (`goal`, `scope`, `acceptance`, `needs`, `depends`, `source`,
`keep_open`) are Host decisions. The Sideagent records one only with
`--host-turn <the Host turn it copies>`; the next Host view lists it under
`attention` until the Host writes that task. Partial acceptance keeps the
unfinished scope open; a `repair` or `partial` task moved back to `review`
keeps that verdict as `prior_verdict`. A `closeout` or `done` task without
`accepted`, `partial` or `cancelled` stays under `attention` (`verdict-missing`).

## Sideagent binding

The Host starts the Sideagent, then sets `--section sideagent`
`{"platform","session","preset","state":"active"}`; it may add
`holder_instance_id` once. To replace, the Host marks `replacing` or `failed`,
starts a successor, and binds it. The successor continues from state and
receipts and replays no admitted work. A stop spares workers it dispatched. A
superseded seat's late write is `binding-superseded`. The Host repairs a failed
Sideagent record. If both fail, the Delegator recovers the Host first.

## Events

`execute` records the real dispatcher (`KAOLA_ACP_DISPATCHER`) apart from the
notify target. Workers report to the live Host holder (`sideagent-host`). A
Host advertising `sideagent-relay/1` relays them to the bound Sideagent and
wakes the Host only when attention changed. A dead, failed, or cancelled turn
returns them. Delivery is at-least-once. `"mode": "node"` keeps events with
the Host ([sideagent-node.md](sideagent-node.md)). After
`--preserve-dispatched-workers`, the new Host runs `rebind-host` for that seat
only. `unknown-op`: `drain-restart` the seat at idle.

## Size

Repeats update the same id; do not append a second row. A settled record leaves
the file in that same write. An old revision gets `record-retired`. Never drop
an open duty to fit. No field length cap and no truncation. A row over 1536
bytes is only a check hint: rewrite that same id. The Host view is bounded at
64 KiB (`host-view-too-large`). The file may reach 1 MiB only with a recorded
`carrier` advertising `heartbeat-state/2`, else 64 KiB (`carrier-limit`). An
unknown row whose collected outcome is absent, whose status evidence is
`no-session`, and whose live session is absent, retires on the stale-collect
session-gone route and writes no index bytes.

## Migration

After a Skill update, at a safe point, run `$S migrate --index I --live L`;
without `--write` it only plans. With `--write`, each v1 `active` row becomes
a `doing` task, `pending` keeps its stated stage or stays `todo`, and
`recovery.protected_untracked` stays for a list of strings. Other
legacy names leave. Unknown keys become `unverified`
locators. A critical mapping writes nothing. Do not write
`heartbeat-prompt.v1-<sha12>.json`. `state-overwritten` is not raised from
those copies. Hash-named copies are not deleted or trusted. An unknown schema
is refused. A clean repeat reports `current`. Migration grants nothing.

Live: Codex and ZCode, `rebind-host`.
