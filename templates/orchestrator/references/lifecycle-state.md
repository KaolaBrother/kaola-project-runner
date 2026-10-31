# Lifecycle state

`<project>/.kaola/heartbeat-prompt.json` (`kaola-heartbeat-prompt/2`) holds
current tasks, authorization, Sideagent binding, holds, alerts and decisions.
`body` is the generated Host view. Write through `kaola-dispatch.py
state` for revision checks. Keep current duties and references, not backlog, ledger or history.

## Roles

- Host: goal, task split, needed abilities, dependencies, preset choice,
  assignment text, `execute`/`collect`, reading original results, acceptance
  and closeout decisions, and recovery. It may do simple authorized work.
- Tools record dispatch, result and holder facts; no node restates them.
- Sideagent: one maintenance role per project, outside every Class seat; a
  fresh node per meaningful batch. It reconciles current duties/conflicts and exact-stops finished workers. It assigns, grants
  and accepts nothing. Launches use bypass permissions; residual prompts and user decisions stay pending.
- Research, QA and implementation helpers count as authorized items.
- Workers never write state (`writer-refused`).

No synchronous Sideagent round trip. Coalesce updates and reuse evidence.
The Host gets outcomes, capacity and decisions.

## Commands

`S="python3 $SKILL_DIR/scripts/kaola-dispatch.py state". Writes take
(`--file "$PROJECT/.kaola/heartbeat-prompt.json" --writer host|sideagent
--source "<event, receipt or Host turn>"`.

- `$S init [--project JSON] [--authorization JSON]`: Host only; refuses an
  existing file.
- `$S update --kind tasks|holds|alerts|decisions --id ID --set PATCH
  [--expect-rev N]`: JSON merge patch of one record (`null` deletes a key;
  `@path` reads a file). An existing record needs `--expect-rev`; a stale one
  exits 3 with `current` and `unapplied`. `--coalesce` counts a repeated alert.
  Unchanged duty facts do not write.
- `$S update --kind tasks --id ID --expect-rev N --live L --cite CITE --set
  '{"verdict":{"value":"accepted"|"cancelled"}}'`: Host terminal write, also
  the Workflow finalize duty write. The row leaves in that revision. The
  receipt keeps `outcome`, `cite`, and any dispatch ref the index does not
  show (`unknown`). It does not store `stage` `done`, a tombstone, or a
  completion list, and it does not rewrite the index. `keep_open` does not
  keep the row. An unreadable live list, a live seat, an index item of this
  task at status `unknown`, or a `closeout` row that still has `next` refuses
  and leaves the previous stage. A missing index is not rebuilt.
- `$S update --section project|authorization|sideagent|recovery|unverified
  --expect-revision N --set PATCH`: first three Host-only.
- `$S retire --kind K --id ID --expect-rev N --evidence REF [--outcome T]
  [--index I ... --live L] [--stop-evidence J] [--handoff TASK]`: needs
  verdict `accepted`/`cancelled`, items closed, seats stopped or handed off.
  `L`: `list --repo --include-dead` rows; repeat `--index`, each ref in one
  file. Absent seats need typed `J` (Host, accepted-done). See [Lifecycle recovery and continuity](lifecycle-recovery.md) for never-indexed refs.
- `$S view --role host|sideagent|delegator [--repo ROOT]` (read-only).
- `$S checkpoint`, `update --index`: [sideagent-node.md](sideagent-node.md).
- `$S check [--index I] [--live L] [--repo R]`: read-only. Problems:
  `doing-untraced`, `done-not-retired`, `field-too-large`, `disposition-orphan`,
  `transcription-unechoed`, `sideagent-not-live`, `sideagent-failed`,
  `carrier-unproven`, `state-bloat`.
  `state-bloat` lists accepted-done/cancelled tasks, settled decisions, empty-`inputs`
  alerts, and shell tasks (evidence only `retired:tasks/ID`, duty fields
  empty). Each names kind, id, rev and its `state retire` command when
  runnable; a large row is a `diagnosis` hint, not a gate.
  `done-not-retired` stays watch until `maintenance.handled_host_revision`
  covers it, then warns without refusing writes. That coverage does not clear
  the finding, and it does not clear `field-too-large` or `disposition-orphan`.
  `carrier-unproven` names
  `state migrate --live`. A row lacking `rev` is `record-versionless`:
  open rows name `migrate` (`--write` assigns rev 1); closed rows name
  `retire --expect-rev 0 --evidence`.
- `$S migrate [--index I] [--live L] [--repo R] [--write]`; `$S timer`
  is the Delegator's.

## Records

- `tasks` (stable id; `stage` `todo|doing|review|closeout|done`, `goal`):
  `source`, `scope`, `needs`, `depends`, `acceptance`, `keep_open`, `wait`,
  `dispatch` (index item ids), `evidence`, `next`, `verdict`, `dispositions`
  (per item). A repair keeps the task id; one returned branch is not
  completion. Tasks need no issue; Workflow owners keep claim/ledger/finalize.
  The writer never stores `stage` `done` (`stage-done-refused`). A Host
  terminal write (`verdict` `accepted` or `cancelled` and exactly one cite)
  deletes the row in that revision. A legacy `done` row stays until that
  write or Sideagent retire. A real closeout duty stays `closeout` with its
  owner, ref, and one `next` (`wait` when a blocker is present). `next` is
  one current action; `wait` is one present blocker or absent. Every string
  value on a task, hold, alert, or decision, including nested values and
  array elements, is at most 512 UTF-8 bytes. `project` and `authorization`
  are outside that bound. A string the write sets must land within that
  bound or be removed (`field-too-large`, with `path`, `bytes`, `limit`);
  it is not truncated. An untouched over-limit value stays for `check`.
  After a write, each `dispositions` key names that task's merged `dispatch`
  (`disposition-orphan`); `null` removes an orphan key, and clearing
  `dispatch` while a disposition remains is the same refusal. An orphan the
  write does not touch stays for `check`. Settling an id already on the task
  removes its ref and disposition in the same write.
- `holds` (`scope`, `reason`): active restrictions with `evidence`, `impact`,
  `owner`, `resume_when`, `next`. A hold keeps the grant.
- `alerts` (`level` `watch|warn|severe`, `summary`): applicable unresolved
  exceptions. Read, acknowledged or in progress is not resolved. Once
  handled: `retire --expect-rev REV --evidence ORIGINAL`.
- `decisions` (`owner` `host|delegator|user`, `question`): open owner answers.
  A Delegator decision is a row (`owner` `delegator`/`user`, `status`
  `pending`). The runner reads `state.decisions` and wakes `needs_decision`.
  A note only in `.kaola/run/*.md` or turn text does not. Host settles
  with `update --set status/evidence ORIGINAL` or `retire --evidence ORIGINAL`.
  A Sideagent copy needs `--host-turn` and stays pending Host adoption. No row:
  `retire --kind decisions --id ID --absent --evidence E` (receipt; stores nothing).

Views use the stored current collection. Keep no handled row elsewhere.
Unfinished effects stay current duties. A stopped process does not finish a task. Refusals name id, revision and the removal command. Do not create an
absent row. Unresolved evidence stays on the current decision route. Unknown
is not resolved.

## Host verdicts

`verdict.value` (`accepted|partial|repair|cancelled`) and the Host-owned task
fields (`goal`, `scope`, `acceptance`, `needs`, `depends`, `source`,
`keep_open`) are Host decisions. The Sideagent records one only with
`--host-turn <its Host turn>`; the next Host view lists it under
`attention` until the Host writes that task. Partial acceptance keeps the
unfinished scope open; a `repair`/`partial` task moved back to `review`
keeps that verdict as `prior_verdict`. A `closeout`/`done` task without
`accepted`/`partial`/`cancelled` stays under `attention` (`verdict-missing`).

## Recovery and continuity

[Lifecycle recovery and continuity](lifecycle-recovery.md) covers Sideagent
binding and `binding-superseded`, event relay (`sideagent-relay/1`), size and
migration. The Host carrier advertises `heartbeat-state/2` for the larger
limit (`carrier-limit`); Host view refusal is `host-view-too-large`. An old
revision of a removed row is `record-retired`. Migrating
never writes `heartbeat-prompt.v1-<sha12>.json`; unmapped facts stay `unverified`.
See [sideagent-node.md](sideagent-node.md) for node-mode checkpoints.
