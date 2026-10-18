# Sideagent nodes, results and Host continuity

`S` is the `state` command of [lifecycle-state.md](lifecycle-state.md);
`execute` and `collect` are in [dispatch-collect.md](dispatch-collect.md).

## Implementation items

`scope: implementation` is the only scope that admits `mutation: true`.
`execute` claims nothing, makes no worktree and touches no forge: the worker's
Workflow owns that. Each item sends either its own `prompt` exactly, or the
plan's `core` (with `core_revision`) plus the item's `worker_scope`, joined by
one blank line; never both. The index row's `prompt_source` keeps the kind,
core revision and `sha256:` of core, scope and sent prompt.

With `--state FILE`, an item's `task_id` adds its id to that task's
`dispatch` (writer `tool:execute`, no Host revision); an unknown task is
`evidence.task_note`. A hold naming the item's `preset` (or `presets`) makes
it `not-run` / `on-hold` before any Runner call: a known hold is not probed
again. An exactly reconciled prior item stays reconciled.

## Results

A `collect` result has `excerpt` (480 characters) with `excerpt_truncated`
and `reply_chars`; `turn` (holder, prompt fingerprint); `locator` (the Runner
`capture` argv `--since <dispatch cursor> --full --inline` and the event log);
`output` with its `kind`: `file` (a path, or `{"path": ...}`; checked for
presence), `capture` (the reply itself), `remote` (a URL) or `description`
(text with spaces); an explicit `{"kind": ...}` wins; and `gaps`:
`reply-text-absent`, `capture-truncated`, `output-absent` (a file only). A gap is evidence,
not a transport failure. Read the full reply through `locator` before a
verdict. A new return resets `acceptance` to `pending` and keeps the earlier
value as `prior_acceptance`.

## Per-assignment dispositions

Task `dispositions` maps item id to `accepted`, `repair`, `cancelled`,
`superseded` or `handed-off`. It is Host-owned like `verdict`, which stays the
task-level judgment. `$S update --kind tasks ... --index I` mirrors them to the
index `acceptance` with `acceptance_source`. After a task verdict, an item of
that task without a disposition becomes `undecided` with a note, never left
`pending`. A mirror error is reported; the state write stands.

## Host revision

Each Host business write raises the file's `host_revision` and stamps the
record. Tool and Sideagent writes keep `host_revision` and stamp `writer_holder`. The
Sideagent view lists `pending_host_changes`: `host:<kind>/<id>@<rev>`,
`host:section/<name>@<rev>`. A settled record leaves the file. It creates
no retirement input or stored tombstone.

## Node mode

Bind `--section sideagent` with `"mode": "node"` and
`"recipe": {"runner": "<absolute Runner file>", "argv": ["start", "--repo",
"<root>", "--session", "<bound name>", "--role", "sideagent", ...]}` (the
checkout `kaola-tmux.sh` takes the platform before `start`), without
`--continue` or `--resume` (optional absolute `state_tool`: `kaola-dispatch.py`
when not beside the holder or in the sibling Skill).
`runner`/`state_tool` name a pinned source (installed Skill root or verified
accepted checkout), never a mutable dev checkout. Worker returns and terminations are not node inputs: they reach the Host at
its next idle boundary as without a binding, and the Host reads the original. A Host
holder advertising `sideagent-node/1` selects current Host business changes
past the handled revision. `host-compact-maintenance/1` also selects a pending
recovery input, at the same safe boundary after the Host turn ends. It starts one fresh node from that argv (no
shell), sends one prompt with the batch id, Host revision range and role
limits (source pointers only, no restated result, dispatch or judgment;
exact-stop only a Host-recorded reclaim), and reads the node's
checkpoint at its turn end. A turn end alone acknowledges nothing. A missing
Runner, failed start or unadmitted batch moves the node to the next eligible
Worker preset in id order, skipping a `computer-use-only` role, never back. A refused recipe or empty
chain reaches both views and wakes the Host once. An idle binding with no owed input stays quiet.
With the shared current-input selector, retirement alone starts or sends no
node and advances no checkpoint revision when no input remains. A node whose
startup finishes after its input disappears is exact-stopped after the Host
turn ends. An assigned batch keeps its range and
checkpoint. Older bundles keep revision-only selection.

For ordinary Host business inputs, the node writes once:

Use selected input ids verbatim. Task ids read as recovery sources are not extra
inputs; a recovery-only batch has no business entries.

```bash
$S checkpoint --writer sideagent --source B --batch B --through-host-revision R \
  --entries '[{"input":"<id>","applied":["tasks/t1"]},{"input":"<id>","retained":"tasks/t2"}]'
```

`applied` names current records this node's holder wrote.
A Host decision row is `retained`, or `retired:decisions/<id>` when the row is gone, never `applied`.
For an input whose record was removed, `retired:<kind>/<id>` names that
absence; it stores no retirement record. Host `retire --kind decisions --id ID --absent --evidence E` closes a decision id with no row. `retained` names a current record with `next`, `owner` or `wait`,
or a Host `section/<name>`. The
result is `maintenance.last_checkpoint`; `last_verified` moves only when every
input settled. An input the Host rewrote during the batch is
`superseded`. Unsettled inputs go to the Host once, in one
`maintenance-returned` alert, and are never sent to another node.

For `recovery#N`, use only `input`, `checked`, `unavailable` and optional `applied`;
never `retained`. Put each scope in `checked` or `unavailable`, never both.
See [duty-reconcile.md](duty-reconcile.md) for the scoped recovery entry.

After a verified batch the carrier wakes the Host once, at its next idle
boundary, only when an attention item is a record this node wrote and the
Host view's attention differs both from what the Host last saw and from the
batch's start; otherwise it stays quiet. A partial or
missing checkpoint, one whose `through` is below the batch's range, a refused
batch, a failed start or a lost node reaches the Host once with the unhandled
range; the carrier then exact-stops the node by holder and resends that range
only on a Host recovery request. A failed start or refused batch starts no further node until
the binding changes. After `sideagent_node_stop_unconfirmed` no node starts
while that holder process still runs. A Host stop in any mode also stops its
own node, a start in flight included. A replaced node's late write is
`binding-superseded`. The next owed input starts a node
at a Host turn end or the existing idle tick. No new timer runs.

## Completed Host compaction

The carrier registers one tool-owned `maintenance.recovery_input` and monotonic
`recovery_seq` from an original, session-bound completed HOST signal before reload
routing. Worker signals, startup replay and PreCompact register nothing. Native
Skill reload stays independent. A request uses the same path without a business
write. Read [duty-reconcile.md](duty-reconcile.md) for sources, checkpoint and recovery.

## Host continuity stop

`stop` or `drain-restart` with `--preserve-dispatched-workers` on a Host whose
holder advertises `preserve-dispatched/1` keeps each worker tree that Host
dispatched (spawn line or a worker record naming its holder) on a cooperative
or dead-holder stop; other children are still swept. An older live holder
refuses with `preserve-unsupported` and stops nothing: `drain-restart` it at
idle first. The successor then runs each seat's `rebind-host`. A start still in
flight is not covered: reconcile it. Default stop and final close-out are
unchanged; close-out reclaims workers one by one first.

## Idle wake

A worker's undelivered `idle` wake to its Host is kept like a permission wake
and re-sent when the Host is reachable; a newer one replaces it and a stop
drops it.

Shown live: Codex and ZCode.
