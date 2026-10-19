# Sideagent nodes, results and Host continuity

`S` is the `state` command of [lifecycle-state.md](lifecycle-state.md);
`execute`/`collect` are in [dispatch-collect.md](dispatch-collect.md).

## Implementation items

`scope: implementation` is the only scope that admits `mutation: true`.
`execute` claims nothing, makes no worktree, touches no forge: the worker's
Workflow owns that. Each item sends its `prompt` exactly, or the
plan's `core` (with `core_revision`) plus its `worker_scope`, joined by
a blank line; never both. The index row's `prompt_source` keeps the kind,
core revision and `sha256:` of core, scope and sent prompt.

With `--state FILE`, an item's `task_id` adds its id to that task's
`dispatch` (writer `tool:execute`, no Host revision); an unknown task
lands in `evidence.task_note`. A hold naming the item's `preset`/`presets` makes
it `not-run`/`on-hold` before any Runner call and is not re-probed. A
reconciled prior item stays reconciled.

## Results

`collect` gives a 480-char `excerpt` with
`excerpt_truncated`/`reply_chars`; `turn` (holder, prompt fingerprint);
`locator` (the Runner `capture` argv `--since <cursor> --full --inline` and
the event log);
`output` with its `kind`: `file` (a path or `{"path": ...}`; checked
present), `capture` (the reply), `remote` (a URL) or
`description` (text); an explicit `{"kind":...}` wins; `gaps`:
`reply-text-absent`, `capture-truncated`, `output-absent` (file only). A gap is evidence,
not a transport failure. Read the full reply via `locator` before a
verdict. A new return resets `acceptance` to `pending` and keeps the earlier
value as `prior_acceptance`.

## Per-assignment dispositions

Task `dispositions` maps item id to `accepted`, `repair`, `cancelled`,
`superseded` or `handed-off`; Host-owned like `verdict`, the
task-level judgment. `$S update --kind tasks ... --index I` mirrors them to the
index `acceptance` with `acceptance_source`. After a task verdict, an item
without a disposition becomes `undecided` with a note, never left
`pending`. A mirror error is reported; the state write stands.

## Host revision

Each Host business write raises `host_revision` and stamps the record; tool
and Sideagent writes keep it and stamp `writer_holder`. The
Sideagent view lists `pending_host_changes`: `host:<kind>/<id>@<rev>`,
`host:section/<name>@<rev>`. A settled record leaves the file; no
retirement input or tombstone.

## Node mode

Bind `--section sideagent` with `"mode": "node"` and
`"recipe": {"runner": "<absolute Runner file>", "argv": ["start", "--repo",
"<root>", "--session", "<bound name>", "--role", "sideagent", ...]}` (checkout `kaola-tmux.sh`
takes the platform), without
`--continue`/`--resume` (optional absolute `state_tool`: `kaola-dispatch.py`
when not beside the holder or sibling Skill).
`runner`/`state_tool` name a pinned source (installed Skill root or
verified accepted checkout), never a mutable dev checkout.
Worker returns and terminations are not node inputs: the Host reads the
original at its idle boundary. A Host holder advertising
`sideagent-node/1` selects current Host business changes past the handled
revision; `host-compact-maintenance/1` adds a pending recovery input at the
same safe boundary after the Host turn ends. It starts one fresh node from
that argv (no shell), sends one prompt with batch id, Host revision range
and role limits (source pointers only, no restated result, dispatch or
judgment; exact-stop a recorded reclaim) and reads the node's checkpoint at its turn end; a turn end alone acknowledges nothing. A missing
Runner, failed start or unadmitted batch moves the node to the next eligible
Worker preset (`computer-use-only` skipped), never back; a
refused recipe or empty chain reaches both views, waking the Host. An
idle binding with no owed input stays quiet. Retirement alone starts or sends no node and advances no
checkpoint revision while no input remains. A node finishing startup after its input
disappears is exact-stopped after the Host turn ends. An assigned batch
keeps its range and checkpoint. Older bundles keep revision-only selection.

For ordinary Host business inputs the node writes once: selected input ids
verbatim; task ids read as recovery sources are not extra inputs, and a
recovery-only batch has none.

```bash
$S checkpoint --writer sideagent --source B --batch B --through-host-revision R \
  --entries '[{"input":"<id>","applied":["tasks/t1"]},{"input":"<id>","retained":"tasks/t2"}]'
```

`applied` names current records this node's holder wrote.
A Host decision row is `retained`, or `retired:decisions/<id>` when the row is gone, never `applied`.
A removed record's input names `retired:<kind>/<id>`; it stores no retirement
record. Host `retire --kind decisions --id ID --absent --evidence E` closes a decision id with no row. `retained` names a current record with `next`, `owner` or `wait`,
or a Host `section/<name>`.
The result is `maintenance.last_checkpoint`; `last_verified` moves only when every
input settled. An input the Host rewrote during the batch is
`superseded`. Unsettled inputs go to the Host once, in one
`maintenance-returned` alert, never sent to another node.

A `host:tasks/<id>@<rev>` the Host accepted done or cancelled retires in
the batch only when all hold: dispatch closed (`--index`
`.kaola/dispatch-index.json`, `--live` `kaola-acp.py list --repo <root>
--include-dead`) or `--handoff TASK` to the Host-recorded task, no `transcribed`, `wait`, `keep_open`, pending decision,
alert naming it or live session; accepted needs a `--cite`
the task records, retrievable. `retire --writer sideagent --kind tasks --id ID --expect-rev REV
--evidence I [--cite J] [--index X --live L]`, REV read
now. `conflict`: re-read, retry once, then `applied:["retired:tasks/ID"]`;
else `returned:"<reason>:<detail>"` - a third verb into
`returned_to_host`/`maintenance-returned`. Only the row leaves; cite, index
and Git keep evidence.

For `recovery#N`, use only `input`, `checked`, `unavailable` and optional `applied`;
never `retained`. Put each scope in `checked` or `unavailable`, never both.
See [duty-reconcile.md](duty-reconcile.md).

After a verified batch the carrier wakes the Host once, at its next idle
boundary, only when an attention item is a record this node wrote and the
Host view's attention differs  from what the Host last saw and the batch's
start; otherwise it stays quiet. A partial or
missing checkpoint, a `through` below the batch's range, a refused
batch, a failed start or a lost node reaches the Host with the unhandled
range; the carrier exact-stops the node and resends the range
only on a Host recovery request. A failed start or refused batch starts no further node until
the binding changes. After `sideagent_node_stop_unconfirmed` no node starts
while that holder process still runs. A Host stop in any mode stops its own
node, a start in flight included. A replaced node's late write is
`binding-superseded`. The next owed input starts a node
at a Host turn end or the existing idle tick. No new timer runs.

## Completed Host compaction

The carrier registers one tool-owned `maintenance.recovery_input` and a monotonic
`recovery_seq` from an original, session-bound completed HOST signal before reload
routing; worker signals, startup replay and PreCompact register nothing. Native
Skill reload stays independent; a request uses the same path without a business
write. See [duty-reconcile.md](duty-reconcile.md).

## Host continuity stop

`stop`/`drain-restart` with `--preserve-dispatched-workers` on a Host whose
holder advertises `preserve-dispatched/1` keeps each worker tree it
dispatched (spawn line or a worker record naming its holder) on a cooperative
or dead-holder stop; other children are swept. An older live holder
refuses `preserve-unsupported`, stops nothing: `drain-restart` at
idle first. The successor runs each seat's `rebind-host`. A start still in
flight is not covered: reconcile it. Default stop and final close-out are
unchanged; close-out reclaims workers one by one first.

An undelivered worker `idle` wake is kept like a permission wake, re-sent
when reachable; a newer replaces it, a stop drops it.

Live: Codex, ZCode.
