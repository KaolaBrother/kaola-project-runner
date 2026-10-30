# Sideagent nodes, results and Host continuity

`S` is the `state` command of [lifecycle-state.md](lifecycle-state.md);
`execute`/`collect` are in [dispatch-collect.md](dispatch-collect.md).

## Implementation items

`mutation: true` requires `scope: implementation`. The worker Workflow owns claim, worktree and forge. Each item sends its exact `prompt`, or the plan `core` (`core_revision`) plus `worker_scope`, joined by a blank line; never both. The index `prompt_source` keeps the kind, core revision and `sha256:` of core, scope and sent prompt.

With `--state FILE`, an item's `task_id` adds its id to that task's
`dispatch` (writer `tool:execute`, no Host revision); an unknown task
lands in `evidence.task_note`. A hold naming the item's `preset`/`presets` makes
it `not-run`/`on-hold` before any Runner call and is not re-probed. A
reconciled prior item stays reconciled.

## Results

`collect` gives a 480-char `excerpt`, `excerpt_truncated`/`reply_chars`; `turn` (holder, prompt fingerprint); `locator` (Runner `capture --since <cursor> --full --inline` argv and event log);
`output` with its `kind`: `file` (a path or `{"path": ...}`; checked
present), `capture` (the reply), `remote` (a URL) or
`description` (text); an explicit `{"kind":...}` wins; `gaps`:
`reply-text-absent`, `capture-truncated`, `output-absent` (file only). A gap is evidence, not a transport failure. Read the full reply via `locator` before a verdict. A new return resets `acceptance` to `pending`, keeping `prior_acceptance`.

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

On `state init` and startup, a record listing `sideagent-node/1` binds node mode: Delegator `authorization.sideagent.preset` if eligible, else the first eligible by id. Skip `computer-use-only`. An existing binding stays across resume and does not raise `host_revision`. Otherwise `sideagent` stays unset; `state check` reports `sideagent-default-unbound` with `state ensure-sideagent`. The next boundary retries.

Bind `--section sideagent` with `"mode": "node"` and `"recipe": {"runner": "<absolute Runner>", "argv": ["start", "--repo", "<root>", "--session", "<bound>", "--role", "sideagent", ...]}` (checkout `kaola-tmux.sh` takes the platform first). No `--continue`/`--resume`. Optional absolute `state_tool` when `kaola-dispatch.py` is not beside the holder or sibling Skill. `runner`/`state_tool` are a pinned Skill root or accepted checkout, never a mutable dev checkout.
Worker returns are not node inputs. A holder advertising `sideagent-node/1` selects Host business changes past the handled revision; `host-compact-maintenance/1` adds one pending recovery input after the Host turn. One fresh node per batch (no shell), one prompt (batch id, revision range, role limits: source pointers only; exact-stop a recorded reclaim), then the node's checkpoint. A turn end alone acknowledges nothing. A missing Runner, failed start or unadmitted batch moves forward to the next eligible Worker (`computer-use-only` skipped). A refused recipe or empty chain reaches both views and wakes the Host. An idle binding with nothing owed stays quiet. Retirement alone starts nothing and advances no checkpoint. A node whose input disappeared during startup is exact-stopped after the Host turn. An assigned batch keeps its range. Older bundles keep revision-only selection.

Every checkpoint requires its original admitted carrier batch, bound node, current prompt and sent through revision. Direct prompts and copied ids are not receipts. Write selected ordinary ids once; recovery-source task ids are not inputs. A recovery-only batch has none.

```bash
$S checkpoint --writer sideagent --source B --batch B --through-host-revision R \
  --entries '[{"input":"<id>","applied":["tasks/t1"]},{"input":"<id>","retained":"tasks/t2"}]'
```

`applied` names current records this node's holder wrote. A Host decision row is `retained`, or `retired:decisions/<id>` when the row is gone, never `applied`. A removed record's input is `retired:<kind>/<id>` and stores no retirement record. Host `retire --kind decisions --id ID --absent --evidence E` closes a decision id with no row. `retained` names a current record with `next`, `owner` or `wait`, or a Host `section/<name>`. The result is `maintenance.last_checkpoint`; `last_verified` moves only when every input settled. An input the Host rewrote during the batch is `superseded`. Unsettled inputs go to the Host once, in one `maintenance-returned` alert, never to another node.

A `host:tasks/<id>@<rev>` the Host accepted done or cancelled retires in the batch only when all hold: dispatch closed (`--index` `.kaola/dispatch-index.json`, `--live` `kaola-acp.py list --repo <root> --include-dead`) or `--handoff TASK` to the Host-recorded task, no `transcribed`, `wait`, `keep_open`, pending decision, alert naming it or live session; accepted needs a retrievable `--cite` the task records. `retire --writer sideagent --kind tasks --id ID --expect-rev REV --evidence I [--cite J] [--index X --live L]`, REV read now. `conflict`: re-read, retry once, then `applied:["retired:tasks/ID"]`; else `returned:"<reason>:<detail>"` into `returned_to_host`/`maintenance-returned`. Only the row leaves; cite, index and Git keep evidence.

For `recovery#N`, use only `input`, `checked`, `unavailable` and optional `applied`; never `retained`. Each scope is `checked` or `unavailable`, never both. See [duty-reconcile.md](duty-reconcile.md).

After a verified batch the carrier wakes the Host once, at its next idle boundary, only when an attention item is a record this node wrote and the Host view's attention differs from what the Host last saw and from the batch start; otherwise it stays quiet. A partial or missing checkpoint, a `through` below the range, a refused batch, a failed start or a lost node reaches the Host with the unhandled range; the carrier exact-stops the node and resends only on a Host recovery request. A failed start or refused batch starts no further node until the binding changes. After `sideagent_node_stop_unconfirmed` no node starts while that holder still runs. A Host stop in any mode stops its own node, a start in flight included. A replaced node's late write is `binding-superseded`. The next owed input starts a node at a Host turn end or the existing idle tick. No new timer runs.

## Completed Host compaction

The carrier registers one tool-owned `maintenance.recovery_input` and a monotonic
`recovery_seq` from an original, session-bound completed HOST signal before reload
routing; worker signals, startup replay and PreCompact register nothing. Native
Skill reload stays independent; a request uses the same path without a business
write. See [duty-reconcile.md](duty-reconcile.md).

## Host continuity stop

`stop`/`drain-restart` on a Host keeps each worker tree it dispatched (spawn
line or a worker record naming its holder) on a cooperative or dead-holder
stop; other children are swept. `--preserve-dispatched-workers` is accepted
and still gates an older live holder that does not advertise
`preserve-dispatched/1`, which refuses `preserve-unsupported` and stops
nothing: `drain-restart` at idle first. The successor runs each seat's
`rebind-host`. A start still in flight is not covered: reconcile it. Final
close-out reclaims workers one by one first.

An undelivered worker `idle` wake is kept like a permission wake, re-sent
when reachable; a newer replaces it, a stop drops it.

Live: Codex, ZCode.
