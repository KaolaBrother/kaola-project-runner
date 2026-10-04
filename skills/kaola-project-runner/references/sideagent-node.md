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
`output` (a local path is checked for presence, a URL is not); and `gaps`:
`reply-text-absent`, `capture-truncated`, `output-absent`. A gap is evidence,
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
record. Tool and Sideagent writes raise nothing and stamp `writer_holder`. The
Sideagent view lists `pending_host_changes`: `host:<kind>/<id>@<rev>`,
`host:section/<name>@<rev>` and `host:retired/<kind>/<id>@<rev>`.

## Node mode

Bind `--section sideagent` with `"mode": "node"` and
`"recipe": {"runner": "<absolute Runner file>", "argv": ["start", "--repo",
"<root>", "--session", "<bound name>", "--role", "sideagent", ...]}` (the
checkout `kaola-tmux.sh` takes the platform before `start`), without
`--continue` or `--resume` (an optional absolute `state_tool` names
`kaola-dispatch.py` when it is not beside the holder or in the sibling Skill). A Host holder advertising `sideagent-node/1` then
starts one fresh node per batch from that argv (no shell), sends it one prompt
with the batch id, its worker events and Host revision range, and reads the
node's checkpoint at that node's turn end. A turn end alone acknowledges
nothing. A refused recipe is logged once and the Host keeps the events.

The node writes once:

```bash
$S checkpoint --writer sideagent --source B --batch B --through-host-revision R \
  --entries '[{"input":"<id>","applied":["tasks/t1"]},{"input":"<id>","retained":"tasks/t2"}]' \
  [--events '["<event id>", ...]']
```

`applied` names current records, or `retired:<kind>/<id>`, that this node's
holder wrote. `retained` names a current record with `next`, `owner` or `wait`,
or a Host `section/<name>`. Older or foreign evidence settles nothing. The
result is `maintenance.last_checkpoint`; `last_verified` moves only when every
input settled. `acked_host_revision` never passes an unsettled change; a later
Host write stays pending. Unsettled inputs go to the Host once, in one
`maintenance-returned` alert, and are never sent to another node.

The carrier stays quiet after a verified batch and hands the rest to the Host
once after a partial or missing one, then exact-stops the node by holder. A
failed start starts no further node. After `sideagent_node_stop_unconfirmed`
the Host keeps new events while that node's holder process still runs; once it
is gone, the next input starts a fresh node. A replaced node's late
write is `binding-superseded`. There is no timer: the next eligible input
starts the next node through the existing event and idle tick.

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

Unproven until live runs: node mode across ZCode and another runtime, process
survival through a real Host replacement, and the OpenCode permission path.
