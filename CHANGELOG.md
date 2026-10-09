# Changelog

Every release section states whether running seats must restart. The operator
test is `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/kaola-record-contract.py scripts/adapters platforms scripts/kaola-acp-paths.py`
(see `docs/conventions.md`).

## Unreleased

Seats: restart required

- **Shared tier group plus a tier-specific extra seat (Issue #296).** One
  grouped grant can now say `count` (the shared pool for every tier in the
  group) and `extra_seats` (extra seats for named member presets only). The
  per-runtime total is `count` plus those extras. Claude Code example:
  `claude-code/default`, `claude-code/sonnet`, and `claude-code/fable` with
  `count` 1 and `extra_seats` `{"claude-code/default": 1}` is 2 live seats.
  Default may use 2. Sonnet and fable stay at 1. Host `state update` and
  `delegator update` both accept that one row. A preset listed once in
  `elite_grants` and once in `expert_task_grants` is the Expert permission,
  not a duplicate seat; two rows in one list are still refused. Raising the
  shared `count` to 2 still grants any mix of two, including two sonnets.
  A `shared-occupied` refusal names each occupying `session` and
  `holder_instance_id`. The dispatch CLI is per-call, so the next `execute`
  admits against this field without a seat restart. Seats still restart:
  the holder pins `kaola-record-contract.py`, and `extra_seats` is a new
  field on that contract.

## 0.9.4 — 2026-10-09 (counted worker seats, absent decision retire)

Seats: restart not required

- **Delegator seat summary counts counted Worker grants (Issue #297).** A
  Worker-class preset with a counted owner grant — a Host grant `count`, or a
  counted Delegator `elite_grants` row admitted by `worker_pool` — is now a
  seat group in `state view --role delegator`, `delegator view` and
  `project --seats` `summary`, counting toward `authorized_total` and
  `idle_available_total`; the uncounted default Worker pool is still not a
  seat and stays in `worker_pool`. The Delegator ceiling still applies: a
  blocked Worker grant shows `unavailable` with its reason, and
  above-ceiling, revoked, or a missing `worker_pool` key omits it.
  `authorized_total` now matches the `project --seats` grant groups, and a
  Delegator-stated Worker count also narrows that Worker's admission count
  through `ceiling_count`. Dispatch CLI only; no template, adapter or holder
  change.
- **Host `state retire --absent` closes a decision that was never a row (Issue #298).**
  `state retire --kind decisions --id ID --absent --evidence E [--outcome R]`
  is a Host-only receipt for an id with no current decision row:
  `{kind, id, outcome, absent_at_retire: true, evidence, at, host_revision}`.
  `host_revision` rises like any Host business write, so the caller can cite
  it. The file stores no row, stone, or tombstone. `--absent` on a current
  decision is refused and names the normal retire. Without `--absent`, an
  absent id stays `record-missing` and the file is unchanged. Holds, alerts,
  and tasks take no `--absent`. `retired:decisions/ID` on a node checkpoint
  is unchanged. This is the dispatch CLI plus the shipped reference copy.
  Seats: restart not required. The state tool is a per-call CLI, and the
  operator-test paths (holder, bridge, quota, protocol) are untouched.

## 0.9.3 — 2026-10-08 (state record roots, node record roots, expert ceiling, delegator seats)

Seats: restart required

- **State tool finds fixed-root holder records (Issue #292).** `state
  checkpoint` and `state update` by node Sideagents whose holder record lives
  in the fixed `/tmp/kaola-<uid>` root were refused `binding-superseded`: the
  state tool still resolved records through the caller's `TMPDIR` /
  `XDG_RUNTIME_DIR`, which runtimes like ZCode do not forward the same way.
  The state tool now resolves caller, carrier and node records through the
  shared #278 path helper across the fixed and legacy roots, and the
  orchestrator package ships `kaola-acp-paths.py` beside it. The checkpoint
  fix takes effect on the next state-tool call after install (the state tool
  is a per-call CLI); restart at a safe boundary only refreshes the holder's
  pinned record contract. An explicit `KAOLA_ACP_RECORD_ROOT` keeps its
  scoped view.
- **Host carrier finds its node across record roots (Issue #293).** A
  node-mode Host carrier looked up its bound Sideagent node's record only
  under the Host's own record root, while the node start resolved across
  all roots and could land in a legacy `TMPDIR` or the fixed root. The Host
  then saw no live node, started it again, was refused `session-exists`,
  marked the live node failed and left the holder orphaned and
  unreclaimable. The carrier now resolves the node record across every
  record root with its own root first, and a verified `session-exists`
  refusal adopts the live holder it dispatched itself — reclaimed later by
  an exact stop — or defers to a live node another holder dispatched until
  that holder is gone. Restart the Host at a safe boundary to load the new
  holder.
- **Delegator ceiling admits granted Expert seats and Elite time windows
  (Issue #294).** `delegator_ceiling` counted only `elite_grants`, so a
  Delegator Expert grant such as `codex/astra` was refused `above-ceiling`
  at `execute` admission. Expert grants are now part of that ceiling:
  `task` (the default) or `standing`, with their own `expires`. A shared
  seat group has one count across its tiers. An Expert choice in that group
  still needs its own task or standing grant, or it is `above-ceiling`. An
  Expert lifetime or expiry limits only that Expert choice. Elite grants are
  a time window ending at `expires`, usable for any task until then. A
  readable Elite window is no
  longer `ceiling-incomplete` when `lifetime` is outside `task` and
  `standing` (`claude-code/fable`). This entry is the dispatch CLI only.
  Seats: restart not required. The section restart still comes from the
  holder changes above.
- **Delegator seat view lists Expert grants (Issue #295).** `state view
  --role delegator`, `delegator view`, and the `project --seats` summary
  omitted `expert_task_grants` presets such as `codex/astra`, so
  `authorized_total` was too low and `expert_authorization` read `none`.
  The summary now uses the same admission ceiling reading as `execute`:
  Expert grants appear in their groups, a shared group is counted once, a
  Delegator-granted preset the Host grants omit is listed
  `host-grant-missing` (authorized, not available), and admissible
  Worker-pool presets are listed in `worker_pool` without counting as
  seats. The `delegator view` fallback no longer reports a legal
  elite/expert grant overlap as a duplicate grant. This entry is the
  dispatch CLI only. Seats: restart not required. The section restart
  still comes from the holder changes above.

## 0.9.2 — 2026-10-08 (list identity, package closure, fixed record roots, retire fail-closed, per-input settlement, seat preset resolution, dead-holder stop, multi-index retire)

Seats: restart required

- **Caller-independent ACP discovery (Issue #278).** New record and socket
  paths use fixed per-UID roots under `/tmp`, independent of `TMPDIR` and
  `XDG_RUNTIME_DIR`. Runner and locator find live v0.9.1 holders across legacy
  roots without moving records; Host uniqueness includes those roots. Locator
  worker session presence now reads ACP records for all ten platforms.
  A legacy-root lookup that cannot establish absence reports
  `record-root-mismatch`. Restart at a safe boundary to load the new holder
  path helper; existing holders remain readable in place.
- **State retire fails closed on unreadable inputs (Issue #286).** `state
  retire` refuses an index that is not this project's
  `kaola-dispatch-index/1` — a missing, wrong, or foreign schema or repo is
  the typed refusal `index-unidentified`, no bytes written — and names an
  open duty for any dispatch-item status outside the known closed values
  (`returned`, `failed`, `not-run`) and the documented `in-flight`/`unknown`.
  A `--live` input that does not declare `kaola-acp-list/1` — missing or
  other schema — is refused as `live-unidentified`, in `state check` and
  `state migrate` too. The index mirror applies the same closed-status
  coverage and records an identity mismatch in `index_mirror.error`. Retire
  help and the `$LIVE` doc name `kaola-dispatch-index/1` and
  `list --repo --include-dead` rows. This entry alone is state tooling only;
  the section restart comes from the #278 holder change.
- **Per-input maintenance settlement (Issue #287).** `state update --kind alerts
  --evidence checkpoint:B --set '{"inputs":{"ID":null}}'` removes one handled
  `maintenance-returned` input when the recorded node checkpoint settled it or
  verified its failed `batch:` range; unrelated inputs stay unchanged. Absent,
  unproven and stale removals refuse (`input-missing`, `input-unproven`,
  `conflict`) without a write and name the exact command. A checkpoint can no
  longer settle a returned input its batch did not carry. The holder now sends
  pending Host changes, including a failed batch's range, with a Host recovery
  request, so recovery needs no fake business write. Restart Host seats at a
  safe boundary to load the holder change.
- **Direct-seat preset attribution (Issue #288).** `project --seats` now uses
  sibling Runner status records to resolve the applied model and effort when
  a live seat was started directly and no dispatch-index assignment exists.
  The seat query infers the installed Runner root when `--skills-root` is
  omitted; explicit roots remain authoritative.
- **Dead-holder stop keeps the expected-holder check (Issue #289).** A `stop`
  whose holder pid is already dead, including the `holder-unreachable` race,
  refuses a foreign `--expected-holder-instance-id` with the same
  `holder-instance-mismatch` receipt as a silent live holder
  (`mutation_status: not_started`, `mutation_performed: false`) and writes one
  `holder_instance_mismatch` event. The record and processes stay unchanged.
  A matching id, or none, still sweeps the identity-verified recorded groups
  without `--force`. The silent live `--force` path writes that same event.
  This change is `scripts/kaola-acp.py` only, outside the operator test in
  `docs/conventions.md` (`scripts/kaola-acp.py` is not in that diff). A running
  seat loads the Runner on the next `stop`, so this change is `Seats: restart
  not required`. The Unreleased section stays `Seats: restart required` because
  #278 changed the holder path helper.
- **Multi-index dispatch close-out (Issue #290).** `state retire --kind
  tasks` accepts a repeatable `--index`, so a done+accepted task whose items
  were dispatched by more than one `execute` run (separate
  `kaola-dispatch-index/1` files) retires once every item is closed and every
  seat is stopped. Every supplied file must still pass the index identity
  check, and every dispatch ref must be found in exactly one supplied index:
  a ref in no file is still named open, and a ref in two files is refused.
  The index mirror writes each supplied file. No hand-merged index, forced
  removal or tombstone. This entry alone is state tooling only; the section
  restart comes from the #278 holder change.

## 0.9.1 — 2026-10-07 (compaction recovery, steer adaptations, launch broker, task-failure count, selection continuity)

Seats: restart required

The changed launch resolution and input parsing run in the client. Since
v0.9.0 the holder, the ZCode bridge, and the eight platform manifests
have changed; see the operator test in docs/conventions.md.

- **Turn timing and answered permissions (Issue #257).** `kaola-acp-view/1`
  receipts expose turn timing and answered permissions.
- **Bounded routine-state contract (Issue #259).** Routine heartbeat records
  are typed, key-allowlisted records validated by the new
  `scripts/kaola-record-contract.py` on every `kaola-dispatch.py state`
  write; closed-contract writers without the allowlist refuse instead of
  guessing, and delivery-open content hashes cover rejection counts and
  escalation.
- **Delegator writing rule (Issue #262).** Minimal ASD-STE100-inspired
  product writing guidance loads on Delegator entry; the language field is
  optional.
- **Noninterrupting steer adaptations (Issue #263).** Grok and OpenCode V2
  steer adapters, exact OpenCode binary binding without proxy changes, DSH
  native steer exposure and later-turn delivery, and pending-delivery
  identity that guards old holders. All ten platforms now steer natively
  with the composite path intact.
- **Post-compaction recovery (Issue #264).** Compaction-completed detection
  per runtime, a bounded installed-Skill reread/use recovery path, the new
  `scripts/kaola-compact-recovery.py` and
  `scripts/kaola-project-compact-notice.py`, and the ZCode bridge mapping
  that reloads the full Skill body after a native compaction.
- **Scoped validation with timing (Issue #265).** `./scripts/validate.sh
  --suite <name>` runs one registered suite with per-suite timing; an
  interrupted validate stops owned writers before its sweep.
- **Outside-caller holder launcher (Issue #266).** The new
  `scripts/kaola-launchd-broker.py` launches Host/seat holders through
  macOS launchd outside the caller's environment behind a fixed environment
  allowlist (`PASS_ALWAYS`/`PASS_PROXY`/`PASS_KAOLA`), with attempt-bound
  rollback and truthful partial/custody outcomes.
- **Task-failure rejection count (Issue #267).** The state tool keeps the
  current owner's rejection count at the verdict transition: a counted
  repair needs the dispatch item, a unique delivery receipt and the review
  cycle together; an unordered repair carries a visible `pending-binding`
  duty instead of masking; a proven responsibility handoff resets the
  segment. The automatic effort-raise reset is not implemented — no catalog
  declares an effort order.
- Codex manifest launches use an explicit absolute `CODEX_PATH`, or resolve
  `CODEX_BIN` then PATH and supply the absolute executable to the adapter.
  An invalid explicit child path still fails before spawn. The error gives
  the setup steps (Issue #260, item 7).
- Invalid Runner arguments return a JSON `invalid-input` receipt and exit
  nonzero. The rejected call reports `not_started` and `mutation_performed:
  false`; earlier calls keep their original mutation state. Prompt files can
  be sent through stdin. `--text-file` remains unsupported (Issue #260, item 8).
- Allow two Droid sessions across `droid/default`, `droid/opus`, and `droid/core` to use the shared two-seat pool.
- A bare `--continue` or `--resume` still sends no model or effort override.
  `selection_continuity` compares the fresh ACP readback with the prior applied
  selection. A difference is reported and is not called preserved. Explicit
  `--model`, `--effort`, or `--tier` still re-applies that selection. Why a
  loaded session differs stays unproven (Issue #268).

## 0.9.0 — 2026-10-05 (lifecycle state and OpenCode managed permissions)

Seats: restart required

The holder and platform diffs are not empty: `platforms/opencode.yaml`
changes the OpenCode launch policy (below), and `scripts/kaola-acp-holder.py` advertises
`holder_features` (`heartbeat-state/2`, `sideagent-relay/1`, `sideagent-node/1`,
`preserve-dispatched/1`), reads a lifecycle
state file up to 1 MiB, relays worker events to a bound Sideagent, and keeps
the whole process tree (holder, native agent, tools) of each worker a
Sideagent dispatched when that Sideagent stops. A running seat keeps the holder it
started with. Restart the Host holder at a safe point, then run
`state migrate --write --live` to record it as the carrier. Healthy workers
are not restarted for migration. Retire a Sideagent started on an older holder
only after the workers it started have ended, because its stop still sweeps
them (`docs/conventions.md#state-format-updates-and-migration`). The release tag names content commit R. Its separate follow-up pin commit P
makes the Grok Bot bridge saveable and names R; use the verified pinned main
checkout for the bridge. No installation or running-seat restart was performed
while publishing this release.

- **Lifecycle state tool (Issue #255).** `kaola-dispatch.py state`
  (`init`, `update`, `retire`, `view`, `check`, `timer`, `migrate`) maintains
  `.kaola/heartbeat-prompt.json` at schema `kaola-heartbeat-prompt/2`. Tasks,
  holds, alerts and decisions are keyed records changed by JSON merge patch
  with a per-record revision; a stale write exits 3 with the current value and
  the unapplied change. Only `host` and the bound `sideagent` may write. A
  Sideagent copy of a Host verdict names the Host turn and is shown back to the
  Host until it writes that task. Finished records retire to capped
  tombstones; a late update of a retired id is refused. The `body` is now a
  generated Host view, bounded at 64 KiB; the tool refuses instead of
  truncating. `snapshot` no longer overwrites a v2 file (`state-managed`).
- **State migration (Issue #255).** `state migrate` reads a v1 file and plans
  the v2 structure without writing; `--write` keeps the raw v1 file once,
  maps `active`/`pending` to tasks, keeps recovery pointers, lists unknown
  keys and unassociated index rows as `unverified`, and records the live Host
  holder as the carrier. A repeat reports `current`. It resets no task,
  replays no dispatch and restarts no session. See
  `docs/conventions.md#state-format-updates-and-migration`.
- **Dispatch roles (Issue #255).** `execute` records the real dispatcher apart
  from the notify target, copies plan `task_id`, `output` and `requires` to the
  index, and refuses an item whose stated `requires` does not match
  (`requirement-unmet`). Only the one bound maintenance Sideagent is outside
  `elite_cap` and preset counts (`seat_exempt`); other Sideagent-role items
  count as workers. A worker the bound Sideagent starts reports to the
  Sideagent's live Host (`heartbeat_host_source: sideagent-host`).
- **Skill guidance (Issue #255).** Project Runner gains
  `references/lifecycle-state.md` (roles, commands, records, touchpoints,
  verdict transcription, Sideagent replacement, events, size and migration).
  Kaola-Delegator gains `references/inquiry-report.md` (the delegator view,
  the exact native timer sentence and its `timer` check, and the five-part
  report).
- **Host carrier re-anchor (Issue #255).** New Runner command `rebind-host`,
  run from inside the live replacement Host, moves an existing seat's carrier
  to that Host through the holder op `rebind_heartbeat_host`. The seat's
  holder, agent process and native session stay; held permission wakes follow.
  It refuses a caller that is not the live Host holder, a seat with no carrier,
  and another repo. A Sideagent whose record names no Host dispatches through
  the ordinary dispatcher rows again instead of being refused.
- **Repairs from joint review (Issue #255).** A Sideagent stop spares every
  worker holder's process tree it dispatched, nested or not, also when its
  holder is already dead. Relay is confirmed only by the matching Sideagent
  holder's completed turn; a failed or cancelled turn, a replaced Sideagent or
  a dead one returns its events to the Host. A worker counts as the
  Sideagent's by its spawn line or by its own live record naming that
  Sideagent holder as `dispatcher` (the ZCode bridge forwards no spawn-record
  variable). A Sideagent turn end settles its relays before queue admission,
  so a full queue cannot refuse the completion that drains it; a later turn
  end past a relay's dispatch cursor returns a relay whose own end was lost to
  the Host (`turn-end-missing`). One 1 s deadline bounds each whole relay
  round trip. The bound Sideagent never takes or waits for a worker shared seat. Migration
  keeps one task per v1 assignment with its fields, invents no stage, binds no
  Sideagent without proof, refuses unknown schemas and alerts on an overwritten
  raw copy. A later `repair`/`partial` verdict asks the Host again
  (`prior_verdict`), and every later repair result changes the attention
  digest while a metadata-only rewrite stays quiet. Retirement needs an
  accepted or cancelled verdict, closed dispatch items, and every seat the
  task names (migrated assignments included) shown stopped in the live rows;
  a missing row or a row of another holder keeps the duty (`done-seat-open`),
  whichever seat shape recorded that holder, and `retire --handoff T` moves
  the seats (with their holders and evidence) and dispatch to a continuing
  task instead. A task at `closeout` or `done` without an accepted, partial or
  cancelled verdict stays under `attention` (`verdict-missing`). A `host`
  write from a caller whose record names no role is traced
  `(role unverified)`. A v1 pending key with no v1 meaning stays inert under
  the task's `legacy`. A Sideagent decision settlement needs the Host turn and evidence. Section
  writes keep their source, omitted text is marked, a worker cannot write as
  Host or Sideagent, and a retired fault id reopens only on a later
  observation.
- **Implementation dispatch and exact results (Issue #255).** `execute` accepts
  `scope: implementation`, the only scope that admits `mutation: true`; it still
  claims nothing and calls no forge. An item sends its own `prompt` or the
  plan's `core` (with `core_revision`) plus its `worker_scope`, and the index
  row's `prompt_source` records the hashes. `--state` links each item to its
  task's `dispatch` as a tool write and skips any preset under a recorded hold
  (`not-run` / `on-hold`, no Runner call). `collect` results name the exact
  turn, a full-capture locator, the declared output's kind (`file`, checked for
  presence; `capture`, `remote` or `description`, so a sentence describing the
  reply is never `output-absent`) and explicit gaps, and mark the
  480-character excerpt as truncated with the full reply length; a new return
  keeps the earlier acceptance as `prior_acceptance`. `execute`, `collect` and
  the disposition mirror write the index under one file lock and merge by item
  and field, so a Host disposition recorded during a running `collect` stands.
- **Pre-started seats and dispatch guidance (Issue #255).** `execute` admits a
  fresh item whose named session is already live and unprompted (same repo,
  platform and preset, identity verified by its status receipt) as that seat
  instead of refusing it `count`: caps and shared seats are judged against the
  other live rows, nothing starts again and the first prompt goes to that
  holder. A refused attempt with no holder no longer makes the retry
  `assignment-unbound`. The main Skill and Host dispatch reference now route
  every planned dispatch of all four scopes through `execute`; direct Runner
  `start`/`send` is the standalone, degraded or same-assignment recovery path.
- **Per-assignment dispositions and Host revision (Issue #255).** Task
  `dispositions` record the Host's decision per item; `update --index` mirrors
  them onto the index, and an item left without one after a task verdict is
  `undecided`. Only Host business writes raise `host_revision`; other writes
  stamp `writer_holder`.
- **Sideagent nodes (Issue #255).** With `sideagent.mode: "node"` and a
  recorded Runner `recipe`, worker returns and terminations still reach the
  Host at its next idle boundary, and the Host holder starts one fresh node
  only for the Host business changes of an ended Host turn (one turn's writes
  are one batch; tool and Sideagent writes start none). It settles the batch
  only from that node's `state checkpoint` (input-by-input accounting against
  records it wrote or duties still owned; an input the Host rewrote meanwhile
  is superseded by the next batch, not returned) and exact-stops the node. A
  verified batch wakes the Host once when a record the node wrote changed the
  Host view's attention, and stays quiet otherwise; a partial or missing checkpoint, a checkpoint range
  below the sent batch, a refused batch, a failed start or a lost node reaches
  the Host once naming the unhandled range (`maintenance-returned` for
  unsettled inputs) and is not re-sent. A failed start or unconfirmed stop
  starts no further node. The node prompt states its role limits: source
  pointers only, no restated result, no dispatch or Host decision. The last
  verified checkpoint shows in the Host and Delegator views.
- **Host continuity stop (Issue #255).** `stop` and `drain-restart` accept
  `--preserve-dispatched-workers` for a Host: its proven dispatched worker
  trees survive, cooperatively and after holder death; an older live holder
  refuses with `preserve-unsupported`. The default stop is unchanged.
- **Idle wake retention (Issue #255).** A worker's undelivered `idle` wake to
  its Host is kept and re-sent when the Host is reachable, as permission wakes
  already were; a newer one replaces it.
- **Dispatch ownership guidance (Issue #255).** The main Skill, its
  lifecycle and dispatch references, the Host heartbeat skeleton and the design
  record now say the Host picks presets, writes assignments, runs
  `execute`/`collect` and judges original results; tools record the facts and
  fresh Sideagent nodes reconcile meaningful batches without authoring or
  allocating work. An existing persistent Sideagent binding keeps its recorded
  workers and relay behavior.
- **A worker is not its own sessions' Host (Issue #255).** A session that a
  worker (any established role other than `host`) starts is no longer bound to
  that worker as its heartbeat carrier (`heartbeat_host_source:
  "dispatcher-not-host"`, `dispatcher` still recorded); the worker supervises
  by waiting. Before, the worker received full Host heartbeat passes, loaded
  Project Runner, accepted and stopped its own child and started a
  maintenance node. Such a holder also never relays to a Sideagent or starts a
  node at its own turn ends. Explicit `KAOLA_ACP_HEARTBEAT_HOST` bindings and
  unknown-role dispatchers are unchanged.
- **A stopped node is a gone holder (Issue #255).** A holder whose stop reply
  cannot be delivered (the caller gave up waiting) still exits. Before, it
  lingered with a `stopped` record until the 10-minute idle exit and kept
  owning the session. The Host carrier counts a node stopped only once its
  holder process is gone. Before, a late confirmation read the `stopped`
  record, the next fresh node start was refused `session-exists`, and that
  one failure turned node mode off for the carrier.
- **A Host stop ends its own node (Issue #255).** In every stop mode the Host
  holder starts no new node, waits up to 8 s for a node start in flight, and
  exact-stops its running node. Before, stopping the last worker and then the
  Host (the usual close-out order) left the node that the worker's
  `terminated` event had started running with no carrier: no spawn line or
  agent sweep reaches a holder-started node, and a preserving stop spared it
  as a dispatched worker.
- **Verified live on Codex and ZCode fixtures:** a missing node checkpoint
  returning its input to the Host, an unconfirmed node stop starting no
  competing node, worker trees surviving a preserving Host stop and a
  replacement Host's per-seat `rebind-host` while the worker's tool still ran,
  and a model-driven Codex Host with a Codex node binding: two concurrent
  workers judged from their originals and reclaimed, worker returns straight
  to the Host, one node per ended Host turn, one Host wake for a node-written
  decision and a quiet verified batch after it.
- **Not yet verified live:** a checkpoint range below its batch (tested with
  a fake node only), node mode beyond Codex and ZCode,
  per-platform process preservation beyond Codex and ZCode,
  relay across holder death, native timer read-back on each outer platform,
  and state size on a real project. `rebind-host` moves only the carrier: each
  seat needs its own call, its `dispatcher` still names the old Host, and
  events staged in a dead Host need the adoption pass. A default stop of a
  ZCode Host does not sweep the workers it started (the bridge forwards no
  spawn-record variable); stop them exactly.
- **OpenCode managed native policy (Issue #256).** Fresh managed OpenCode V2
  launches select a process-only native build full-access policy through
  `OPENCODE_CONFIG` when no existing config source or explicit mode is
  supplied. Existing global/project configuration (including non-permission
  config), supplied native config, resume/continue and custom commands
  suppress the default. Explicit `--permission-mode plan` selects the native
  plan agent. Model/provider/effort selection and explicit permission
  decisions are unchanged. No shared configuration is edited; this applies to
  newly started processes only. Verified CLI 2.0.22 uses ACP protocol 1; V1
  compatibility is not claimed.

### Acceptance and upgrade limits

The exact implementation candidate `86d19f69` passed the outer personal and
Claude Opus Extra High seven-requirement review. Matching full validation
completed with 105 lifecycle and 74 dispatch tests, plus retained native
Host/node/two-worker and OpenCode ACP evidence. Release preparation changes
only these notes and the generated bridge pin, not the reviewed runtime.

The four inquiry cadences have configuration/test coverage; only the existing
hourly outer timer was live-observed. Model-driven Host/node coverage is Codex,
with additional Codex/ZCode continuity cases; other platform node/preserve-stop
paths and real consuming-project migration remain unverified. Completed tasks
need explicit retirement and exact seat cleanup. In qa6 a malformed task
`evidence` value was refused and corrected before Host-written dispatch links;
this was not automatic tool link repair. Bounded capture gaps still require
reading original results through their locators. See the archived #255
finalization summary for all accepted limitations and the conventions for
safe holder replacement and idempotent state migration.

### Recovered historical notes

The following older entries were stranded in a second Changelog/Unreleased
block. They are preserved here as history, not newly implemented in v0.9.0.
The rest of that appended block duplicated existing release entries and has
been removed.

- **Expose Host, Sidekick, Expert, Elite, and Worker session identity (Issue #245).**
  `session_role` is an additive field on the holder record and on `list`,
  `status`/`observe`, and `view`/`follow`. Values are `host`, `sidekick`,
  `expert`, `elite`, `worker`, or `null`. A standard Host name is `host`.
  `--role sidekick` is the only role flag. The three Classes come only from
  the preset that start actually selected. Custom `--model`, an unproven
  resume, and an unknown class stay `null` and are not labeled Worker.
  `host_class` is unchanged. A dispatch plan `role` other than exact
  `sidekick` stays index metadata and does not refuse the item. Only
  `sidekick` is forwarded as start `--role sidekick`. The shared
  `kaola-tmux.sh` start parser accepts `--role` and forwards it to
  `kaola-acp.py`. Recovery does not change a live session's role.
  Occupancy stays catalog-Class-based. A running seat keeps the holder
  it started with, so that seat emits the field only after it is replaced
  (`Seats: restart required` for the field; this issue does not restart
  seats). Kaola Terminal's UI is unchanged. The Grok Bot bridge returns to
  the content stage (`saveable: false`) so this content can pass the pin
  gate; the next pin is a separate commit and is not part of this issue.

- **Pause an unusable account seat and route login recovery to the user (Issue #216).**
  The Delegator `host-brick` reference and the Project Runner `quota-packages` reference now
  separate three causes from existing receipts, captures and events, and the Delegator
  Host-recovery section is renamed "Limit-failed Host". A **limit failure** — explicit quota
  exhaustion, a reached rate limit, or a stated reset/window/account limit — reuses the existing
  #207 class handoff unchanged (non-ZCode limited Host to one ZCode Host; already-ZCode or
  inoperable fallback, and the Expert class, to the user; Elite safely reclaimed with run-seat
  revocation and handed to another already-authorized Elite; Worker handed to another suitable
  Worker; no suitable replacement asks the user), and the full class table is not duplicated in
  the Host prompts. An **authentication or account-access failure** — `login expired`,
  `authentication required`, revoked/invalid credentials, `account disabled`, or an equivalent
  refusal — pauses only the affected seat: task, worktree/ledger locator, valid output and exact
  Runner identity are preserved, no new work is bound to it, it is exact-stopped at the existing
  safe boundary once the failed turn settles and marked temporarily paused in the run's
  authorization/heartbeat snapshot — a pause, not the grant revocation of a limit failure — the
  exact runtime message and seat go to the user for account repair or direction, no other seat is
  silently substituted, and unrelated authorized work continues; for the Host itself the
  Delegator preserves the frontier and in-flight worker ownership with no automatic #207 Host
  switch. A session that is **still connecting or awaiting a reply**, and any bare 429, timeout or
  network error without an explicit limiting reason, is not a failed seat: the cause stays unknown,
  observation continues at the existing cadence, and a persistent blocker is escalated with
  evidence rather than labeled quota or authentication. No cause ever logs in — no attempt, retry
  or delegation of login, logout/login cycling, credential refresh or replacement, account
  switching, or billing change, and no secrets in chat. A paused seat resumes only after the user
  confirms access restored and directs continuation, through the existing receipts and task
  records, with no duplicate claim or lost valid work. Guidance and reference prose only; the
  operator-test paths are untouched (`Seats: restart not required`).

## 0.8.2 — 2026-10-04 (OpenCode DeepSeek advertisement)

Seats: restart required

The operator diff from v0.8.1 to this release
(`git diff v0.8.1..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is not empty. `platforms/opencode.yaml` records that OpenCode 2.0.22 publishes
later providers after `session/new`, and that start waits, bounded, until the
live option list advertises the requested model id and then sets it, with no
substitution. The holder, ZCode bridge, quota catalog, and adapters are
unchanged in that diff. A running seat keeps the platform and script bytes it
started with, so restart a seat before this selection behavior applies. This
content commit leaves the Grok Bot bridge at the unpinned content stage
(`saveable: false`); the bridge is pinned in the release's follow-up pin
commit.

- **Set OpenCode DeepSeek V4.1 Flash after the provider is advertised (Issue #254).**
  OpenCode 2.0.22 returns from `session/new` before provider discovery. The
  first model list is only `opencode/*`; `opencode-go/deepseek-v4.1-flash`
  appears on a later update. Setting that id before the advertisement returns
  JSON-RPC -32602 and leaves `opencode/fledge-alpha-free`. When the platform is
  OpenCode and the option is model, start waits at most 8 seconds until the
  live option list contains the requested id, then sets it once. A value that
  never appears is still sent once at the deadline. No other model is
  substituted. The default stays `opencode-go/deepseek-v4.1-flash`.
- **Record the DSH version-probe catalog gap (Issue #254).** The dsh
  `--version` catalog probe can report catalog-missing while the live ACP
  catalog lists the model. That probe now records `catalog_probe.reporting_gap`
  `version-probe-does-not-list-acp-models`. The resolution state and candidate
  id are unchanged. The gap is not applied to OpenCode's catalog probe.

## 0.8.1 — 2026-10-04 (blocked_attempt stamp)

Seats: restart not required

The operator diff from v0.8.0 to this release
(`git diff v0.8.0..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is empty: the holder, ZCode bridge, quota catalog, adapters, and platform
manifests are unchanged. Running seats keep the bytes they started with and may
stay up. This content commit leaves the Grok Bot bridge at the unpinned content
stage (`saveable: false`); the bridge is pinned in the release's follow-up pin
commit.

- **Stamp blocked_attempt only for a real block (Issue #253).** `execute`
  `publish()` writes `evidence.blocked_attempt` only when a blocked row exists.
  It no longer stamps placeholder reason `missing` because publish runs before
  the executor. A regression fixture reads the dispatch index after that first
  publish. An uninterrupted admission still clears a real earlier stamp.
  `collect` `publish()` does not write the stamp.

## 0.8.0 — 2026-10-04 (breadth work, standing Expert grants)

Seats: restart required

The operator diff from v0.7.0 to this release
(`git diff v0.7.0..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is not empty. `scripts/kaola-acp-holder.py` adds session-role handling.
`platforms/claude-code.yaml`, `platforms/codex.yaml`, and `platforms/devin.yaml`
change: the Expert profiles say an explicit task or standing grant, and Codex
launches adapter `@agentclientprotocol/codex-acp@2.0.1` with the child CLI
selected by an absolute `CODEX_PATH` at requested CLI 0.160.0. The ZCode
bridge, quota catalog, and adapters are unchanged in that diff. A running seat
keeps the holder and platform bytes it started with, so restart a seat before
those bytes apply. This content commit leaves the Grok Bot bridge at the
unpinned content stage (`saveable: false`); the bridge is pinned in the
release's follow-up pin commit.

- **Spread breadth work across fitting Worker presets (Issue #252).** The
  dispatch entry now prefers spreading useful parallel gathering, independent
  research, counterexample or critique, edge-exploration and verification items
  as evenly as reasonably possible across fitting Worker-Class presets instead
  of one habitual runtime. Fit, authority and real limits come first, with no
  invented work and no fixed per-runtime quota. No router or schema is added;
  `execute` and `collect` already run items in parallel. The entry also states
  that a rejected re-execution keeps correlation and adds
  `evidence.blocked_attempt` with only the reason.
- **Standing Expert grants (Issue #252).** An Expert grant may carry optional
  `lifetime` (`task`, the default, or `standing`) and `expires` (an ISO-8601
  instant with an offset). A task grant still ends with its task; a standing
  grant lets the Host invoke that Expert preset within its stated scope, count
  and limits without asking again until the owner revokes it or it expires,
  and exact-stopping a finished session does not revoke it. A standing grant
  exists only when the owner said so. `project` withholds an Expert grant as
  `lifetime-unreadable`, `expiry-unreadable` or `expired`, and `execute`
  reports the same reason as `not-run`. Elite and Worker rows are unchanged.
  Expert profile text in `platforms/` now reads "only under an explicit task
  or standing grant"; the Host class text, worker profiles, heartbeat
  skeleton and Kaola-Delegator snapshot guidance follow.

## 0.7.0 — 2026-10-03 (capability summary, Sidekick, dispatch/collect)

Seats: restart required

The operator diff from v0.6.18 to this release
(`git diff v0.6.18..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is not empty: `scripts/kaola-acp-holder.py` refuses a `prompt` when
`--expected-holder-instance-id` is present and does not match that holder.
Omitting the flag keeps the previous unbound send. A running seat keeps the
holder bytes it started with, so restart a seat before a bound send can be
enforced. The ZCode bridge, quota catalog, adapters, and platform manifests
are unchanged. This content commit returns the Grok Bot bridge to the
unpinned content stage (`saveable: false`); the bridge is pinned in the
release's follow-up pin commit.

- **Routine context and dispatch projection (Issue #244).** The heartbeat no
  longer carries a profile row per authorized preset. It keeps the three Class
  meanings, a compact capability summary compressed from the profile text of
  presets that are actually authorized and locally present, and durable grants
  (exact preset id, count, structured shared seat, exclusions, owner special
  requirements). The summary states those profiles' own distinctions, such as
  planning and review versus implementation. It is not Class booleans and not
  a hardcoded computer-use list. At a dispatch decision,
  `scripts/kaola-dispatch.py project` projects each eligible candidate. Unknown
  availability stays visible and is not advertised as a capability, a mismatch,
  or a new refusal. No capability-tag taxonomy, ranking, or second model
  registry is added.
- **One dispatch/collect entry (Issue #244).** `execute` admits an adopted
  research, QA, or report plan — one item or a bounded fan-out — through the
  existing platform Runners. A `--no-wait` admission is `in-flight`, not a
  result. `collect` later reads one status and, for a completed matching turn,
  one capture, and can return a finished item while a slower sibling stays
  `in-flight`. The Host remains the acceptance owner. Applied selection is read
  from `config_application`, including nested start evidence; a timeout or an
  unreadable receipt is `unknown`, and an unapplied value is not reported as
  applied. A fresh start's holder is stored and passed as
  `--expected-holder-instance-id` on the send. Recovery binds repo, session,
  preset, holder, and prompt sha256; fingerprint equality alone does not count
  as already dispatched. An authorization `elite_cap` stays in force when the
  plan omits `seat_cap`; a plan cap may only tighten it. Live seats from fresh
  Runner facts occupy that cap and shared seats. Owner special requirements
  beat item overrides. The index is correlation only and is rewritten as each
  item completes. `snapshot` writes the heartbeat file so the nested `body` is
  one JSON object. Production mutation fan-out, a pipeline language, and
  automatic choose-and-dispatch are outside this scope.
- **On-demand Sidekick (Issue #244).** Default preset `zcode/default`, or
  another authorized and locally available preset the owner selects. It may
  draft a plan, synthesize evidence, identify gaps, and do explicitly scoped
  light work. It does not control other workers, grant permission, accept the
  product, or run a scheduling loop. Helper wording now allows bounded
  cross-worker preparation while one Host still owns scheduling and acceptance.

## 0.6.18 — 2026-10-02 (lifecycle guidance placement; execution Opus presets high)

Seats: restart required

The operator diff from v0.6.17 to this release
(`git diff v0.6.17..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is not empty this release: the four platform manifests `platforms/claude-code.yaml`,
`platforms/cursor-cli.yaml`, `platforms/devin.yaml`, and `platforms/droid.yaml` and their four
matching adapter scripts changed (+18/−18), raising four execution Opus 5.5 preset efforts from
medium to high. Platforms are holder-pinned at startup, so a running seat keeps the preset bytes
it started with; restart a seat to pick up the new presets. The Grok Bot bridge is pinned in the
release's follow-up pin commit.

- **Lifecycle guidance at the step that uses it (Issue #242).** Four reviewed placement edits
  move existing orchestrator guidance to where it is used: the QA-read trigger joins Decide and
  dispatch; the fresh-start/same-assignment and same-beat-stop sentences join Release and report;
  the not-an-idle-Host rule gets its own paragraph; and step 5 gains the heading "Reclaim seats
  and report". No rule text was added or removed — apart from the heading and two punctuation
  joins the bytes are unchanged; references, Delegator, renderer and budgets untouched. Host
  entry 16527 -> 16539 B (+12).
- **Execution Opus 5.5 presets raised from medium to high (Issue #243).** `claude-code/default`
  launches Opus 5.5 at effort=high; `cursor-cli/opus` uses the existing high variant
  `claude-opus-5-5-high` (effort high encoded in the model ID, with the parameterized ACP
  mapping to the base model preserved); `droid/opus` applies `claude-opus-5-5` at
  `reasoning_effort=high`; and `devin/opus-fusion` uses
  `fusion-claude-opus-5-5-high-sidekick-swe-2-medium` (main Opus 5.5 high, SWE-2 sidekick
  medium) in the preset and the native launch argv. Preset IDs, classes, profiles, counts,
  permissions, packages and Fast policy are unchanged; `claude-code/opus-xhigh` stays xhigh and
  thinking-only; this is not a global medium replacement — explicit user overrides, supported
  effort values, old-version history, and the SWE-2 sidekick remain medium; display names stay
  separate from effort and Fusion component semantics are preserved (no top-level uniform
  effort). New starts use the updated defaults while ordinary resume keeps the saved
  model/effort unless explicitly overridden, and historical Devin #190/#197 medium observations
  stay historical. Generated Skills, catalogs, README and API docs are synced through the
  renderer, and six new contract tests cover the four resolutions plus explicit-effort overrides
  and the medium-variant split.

## 0.6.17 — 2026-10-02 (dispatch selection grounded in the current heartbeat)

Seats: restart not required

The operator diff from v0.6.16 to this release
(`git diff v0.6.16..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is empty: the holder, ZCode bridge, quota catalog, adapters, and platform
manifests are unchanged. Running seats keep the bytes they started with and may
stay up; this release changes Skill prompt content only. The Grok Bot bridge is
pinned in the release's follow-up pin commit.

- **Selection grounded at the decision point (Issue #241).** The Decide and
  dispatch step now says each clear task goes to a suitable authorized worker
  "chosen from the current heartbeat authorization and rows by owner direction,
  class responsibility, profile/task fit and capacity; past dispatch or success
  informs that choice, never replaces it" — so a new selection reads the
  current authorization instead of repeating the last seat, while routine
  repair, resume, finalize and safe-idle switch ownership are unchanged. The
  duplicated Choose-by sentence in the always-loaded Authorization section is
  removed; the delegation principle, Class grants, the heartbeat eligibility
  pointer and the intake/grant-change catalog-row trigger stay, and
  worker-profiles remains the detailed policy home. Host entry +61 B (16,527 of
  17,408); references and heartbeat unchanged; no ceiling raised.

## 0.6.16 — 2026-10-01 (delegation by profile fit, Worker-preferred parallel QA)

Seats: restart not required

The operator diff from v0.6.15 to this release
(`git diff v0.6.15..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is empty: the holder, ZCode bridge, quota catalog, adapters, and platform
manifests are unchanged. Running seats keep the bytes they started with and may
stay up; this release changes Skill prompt content only. The Grok Bot bridge is
pinned in the release's follow-up pin commit.

- **Delegation by profile fit (Issue #240).** The Host entry now carries one
  principle: delegate substantial planning, design or review to an available
  authorized seat when its profile or the owner's task-specific judgment makes
  it a better fit than the Host's own known model/preset — routine routing
  stays local, with no mandatory consultant stage and no universal model
  ranking (the Choosing ban now reads "Do not keep a universal model
  ranking"). Helpers "may plan, design, research, inspect" in the task list;
  parallel splitting is warranted when independent parts gain real time or
  coverage; the Worker class does "simpler, bounded work";
  `claude-code/opus-xhigh` is clarified as plans/designs/reviews but does not
  implement.
- **Worker-preferred parallel QA and the QA-read rule (Issue #240).** The QA
  guidance's Who section now prefers suitable available Worker-Class seats for
  exploratory checks and heavy or long-running test runs, chosen per scope by
  profile fit rather than one habitual runtime, with a fitting authorized
  Elite when the pool lacks a needed capability; exploratory checks fix their
  question, scope and stopping point, not their route or findings. The main
  entry now explicitly requires reading the QA reference before planning,
  assigning or judging QA, unless the current version is already in context.
  Host entry +318 B (headroom 942), worker-profiles +32 B, QA reference +445
  B, heartbeat unchanged; no ceiling raised.

## 0.6.15 — 2026-10-01 (Host task-failure escalation policy, role-scoped prompts)

Seats: restart not required

The operator diff from v0.6.14 to this release
(`git diff v0.6.14..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is empty: the holder, ZCode bridge, quota catalog, adapters, and platform
manifests are unchanged. Running seats keep the bytes they started with and may
stay up; this release changes Skill prompt content only. The Grok Bot bridge is
pinned in the release's follow-up pin commit.

- **Host escalation policy after substantive worker task failure (Issue
  #238).** A new compact reference (`references/task-failure.md`) guides the
  Host when a worker substantively fails an engineering task: the trigger is
  judged on concrete evidence (core objective unreachable, approach disproved,
  or repair no longer making meaningful progress - no fixed retry count,
  timer, or classifier; routine repair stays with the current worker). Worker
  failure prefers a fitting already-authorized Elite, else another eligible
  Worker with a materially different approach; Elite failure first raises
  effort on the same model when runtime, authorization, and owner restrictions
  allow, else reassigns to another fitting already-authorized Elite before
  any request for new authorization; with no eligible recovery the Host
  reports the gap and asks. A task may move to a different authorized
  seat/runtime through existing lifecycle operations - only a bound seat
  cannot hot-switch. Handoff preserves the original issue/run, valid work and
  evidence under one writer, recording only the failure evidence, attempted
  approach, preserved locator, and what the next owner does differently;
  `failed`/`done` mission lines are never rewritten.
- **Role-scoped Agent prompts (Issue #239).** Each Agent surface now carries
  only what its current role and task need, per the agreed minimum design:
  the Delegator inquiry snapshot is self-contained (exact recorded Host
  session, turn-opening Skill entry for idle sends and composite interrupts,
  Grok attestation before guarded commands) without the full startup handoff
  manual; `host-brick.md` decides Host replacement on a local
  confirmed-limit trigger; `quota-packages.md` keeps the concise actionable
  #207/#216 seat-failure rule (confirmed limit only; authentication pauses
  and asks; a revoked Elite stays revoked) with the downstream API
  exposition moved to `docs/api.md`; the main Skill replaces the worker
  roster with the Skill-directory rule, merges dispatch notes into step 2,
  and keeps the stop/pause authority; worker Skills drop delivery-adjacent
  advice while keeping operation parameters and receipts. Generated UTF-8
  bytes drop across the measured prompt surfaces (Host entry 17,407→16,148;
  quota guidance 8,155→3,222; worker entry 11,362→10,330 per platform) with
  no budget raised and no authorization, transport, or lifecycle behavior
  changed.

## 0.6.14 — 2026-09-30 (Codex ACP pair 0.159.2 / 2.0.1 for GPT-6.1 Sol)

Seats: restart required

The operator diff from v0.6.13 to this release
(`git diff v0.6.13..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
changes `platforms/codex.yaml`: `acp_command` moves from
`@openai/codex@0.158.0` + `@agentclientprotocol/codex-acp@2.0.0` to
`@openai/codex@0.159.2` + `@agentclientprotocol/codex-acp@2.0.1`, and
`acp_verified_versions` now records the actually tested pair
(`cli=0.159.2;adapter=2.0.1;protocol=1`, `acp_wrapper_pin` `2.0.1`).
Running seats keep the bytes they started with and must restart after
installing this release. The Grok Bot bridge is pinned in the release's
follow-up pin commit.

- **Codex ACP compatibility with GPT-6.1 Sol.** The previously pinned pair
  (0.158.0 / 2.0.0) rejected `gpt-6.1-sol` with an invalid-params error and
  left the old effective model selected. The new pair was live-tested over ACP:
  `gpt-6.1-sol` with effort high applied, the exact prompt returned
  `SOL61_ACP_OK`, zero tools or files changed, and the disposable session was
  exact-stopped with no residual processes. Model, profile, and effort choices
  are unchanged; the other nine platforms are unchanged and keep their
  existing pins.

## 0.6.13 — 2026-09-30 (Codex Sol 6.1 profile alignment)

Seats: restart required

The operator diff from v0.6.12 to this release
(`git diff v0.6.12..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
changes `platforms/codex.yaml` (profile wording only; the holder, bridge, and
quota catalog are unchanged). Running seats keep the bytes they started with
and must restart after installing this release. The Grok Bot bridge is pinned
in the release's follow-up pin commit.

- **Codex Sol 6.1 profile alignment.** The `codex/default` preset profile now
  reads "All-round execution worker, strong at exploring directions, finding
  problems, and review; good at UI and 3D visual work, with computer-use
  capability." Model id `gpt-6.1-sol`, effort high, and the Elite class are
  unchanged; README, the profile catalog, and the generated platform rows
  agree. Luna and Astra are unchanged.

## 0.6.12 — 2026-09-30 (complete install through ACP preparation, model name/effort separation, Sol 6.1)

Seats: restart required

The operator diff from v0.6.11 to this release
(`git diff v0.6.11..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is non-empty. Changed paths are `platforms/claude-code.yaml`,
`platforms/codex.yaml`, `platforms/devin.yaml`,
`scripts/adapters/claude-code.sh`, `scripts/adapters/codex.sh`,
`scripts/adapters/devin.sh`, `scripts/kaola-acp-holder.py`, and
`scripts/kaola-quota.py`. Running seats keep the bytes they started with and
must restart after installing this release. The Grok Bot bridge is pinned in
the release's follow-up pin commit.

- **Complete installation through actual ACP preparation (Issue #236).**
  Every installation entry — the README install sections, the Grok Bot
  installation/update guide, and `install-local.sh`'s successful-install
  footer — routes completion through
  `docs/api.md#acp-layer-preparation-during-install` instead of stopping at
  Skill payload verification: a compact per-runtime result row
  (component, loaded versions, verified record, action, readiness), one survey
  per installation where `--runtime` only selects the Skill destination,
  absent unrequested runtimes reported as skipped rather than an install
  obligation, and unknown survey states resolved by rerunning the survey in
  the correct bound-target launch environment. Between releases the Grok Bot
  accepted revision now moves through its normal content stage (unpinned,
  not saveable) so renderer checks stay green on a moving main.
- **Consumer model display names separated from effort (Issue #237).**
  Downstream consumers such as Kaola Terminal read a model identity without
  parsing prose or native IDs: the preset catalog carries `<w>_model_name`,
  `<w>_model_id`, `<w>_model_effort`, and optional `<w>_model_components`
  (Devin fusion presets split main/sidekick efforts), and receipts carry
  `model_display`, `requested_effort`, `resolved_effort`, `applied_effort`,
  `current_effort`, plus `view.model.current` — a same-object live
  name/native-id/effort pair labeled `catalog-declared` that never proves a
  request was applied. A known direct model selection (for example
  `codex --model gpt-6-luna`) resolves its declared name without preset
  assignment or preset effort; unknown IDs stay unnamed with the raw ID
  preserved; preserved resumes keep historical launch facts historical.
- **Codex default Sol is GPT-6.1 Sol (Issue #237 follow-up).**
  `codex/default` names GPT-6.1 Sol with native id `gpt-6.1-sol`, effort
  unchanged at high; declared ACP display-name mapping is preserved and the
  profile wording corrected. Luna and Astra are unchanged.

## 0.6.11 — 2026-09-29 (Host closeout clarity, scoped pause adoption, DSH doc link)

Seats: restart required

The operator diff from v0.6.10 to this release
(`git diff v0.6.10..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
changes `platforms/dsh.yaml` (documentation-link correction only; the holder,
bridge, and quota catalog are unchanged). Running seats keep the bytes they
started with and must restart after installing this release. The Grok Bot
bridge is pinned in the release's follow-up pin commit.

- **Host closeout ownership and scoped pause adoption (Issue #235).** An
  explicit owner instruction may keep simple authorized release/install
  mechanics Host-owned without a mandatory new issue or worker; the duplicate
  Self-execute defaults row is removed and the Allowed CLIs row references the
  Authorization section, which retains "No authorized task: ask; start no
  worker or heartbeat." A pause is conditional on an explicit owner
  stop/pause instruction, scoped to the named actions, with unrelated
  authorized work continuing; ordinary inquiry, guidance, heartbeat or review
  feedback is not a pause trigger. Owner-confirmed current availability
  supersedes prior quota exhaustion; a passed reset does not prove every
  limiting window recovered or restore a revoked Elite grant. A permission
  event for an owned seat needs no additional full repository sweep, and the
  Delegator relays explicit owner model/seat choices without inventing
  allocation or constraints.
- **DSH installed-package documentation link (Issue #235).** The single
  `platforms/dsh.yaml` `acp_quirks` cross-reference that rendered as a broken
  `../../../docs/api.md` link inside the installed dsh Skill now points to the
  canonical public repository documentation URL; the generated dsh Skill
  package passes its self-containment link checks again.

## 0.6.10 — 2026-09-29 (Claude profile redesign, dsh ACP harness check)

Seats: restart required

The operator diff from v0.6.9 to this release
(`git diff v0.6.9..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is non-empty. Changed paths are `platforms/claude-code.yaml`,
`platforms/codex.yaml`, `platforms/cursor-cli.yaml`, `platforms/devin.yaml`,
`platforms/droid.yaml`, `platforms/dsh.yaml`, and
`scripts/adapters/claude-code.sh`.
`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, and
`scripts/kaola-quota.py` are unchanged. Running seats keep the bytes they
started with and must restart after installing this release. Codex
`acp_command`, `acp_wrapper_pin`, and `acp_verified_versions` move to CLI
0.158.0 and `@agentclientprotocol/codex-acp` 2.0.0 (Issue #226). dsh keeps
`acp_command` `dsh --profile acp` and an empty `acp_wrapper_pin`;
`acp_verified_versions` records CLI 0.1.7-rc.2 under the operator-declared
opencode-go route (Issue #227). The other eight worker platforms keep their
v0.6.9 `acp_command`, `acp_wrapper_pin`, and `acp_verified_versions` and are
intentionally not re-pinned. The Grok Bot bridge is pinned in the release's
follow-up pin commit.

- **Claude Code Sonnet and Opus task profiles (Issue #228).** Preset ids stay
  `claude-code/sonnet` and `claude-code/default` (`sonnet` and `opus` remain the
  native model aliases). `claude-code/sonnet` is Elite at effort `high`, with the
  profile "All-round execution worker, well suited to well-scoped work." It
  leaves the Worker pool. The five remaining Worker presets stay
  default-authorized and outside the general worker cap. Sonnet uses the
  existing Elite grant (preset and count): no default seat and no
  preset-specific cap. `claude-code/default` stays Elite at effort `xhigh`,
  with the profile "Plans and reviews difficult, complex work and handles deep
  reasoning tasks; does not perform implementation." That limit is this
  preset's profile. Fable is unchanged. No ordinary Opus or Sonnet seat is
  granted. A resume that does not name a tier, model, or effort keeps the
  native selection. Issue #230 moves that thinking-only role from
  `claude-code/default` to `claude-code/opus-xhigh`.

- **Claude Code Opus Medium default and Opus Extra High (Issue #230).**
  `claude-code/default` is Opus 5.5 (native alias `opus`) at effort `medium`,
  Elite, and implements: "All-round execution worker, especially strong at
  complex execution work and UI and 3D visual implementation." It stays the
  runtime and Host fallback when no tier is chosen. Named tier `opus-xhigh`
  (`claude-code/opus-xhigh`, display Opus Extra High, the same native alias
  `opus`, effort `xhigh`, Elite) is thinking-only: "Plans, designs, and reviews
  difficult, complex work and handles deep reasoning tasks, with particular
  strength in UI and 3D visual design and review; does not perform
  implementation." The preset ID is not the model alias. Both presets use the
  existing `opus` subscription map entry. `claude-code/sonnet` stays Elite at
  effort `high`: "All-round execution worker, well suited to well-scoped work,
  especially UI and 3D visual implementation." Fable is unchanged. This split
  does not add a seat and does not retarget a live resume. A resume or continue
  that does not name a tier, model, or effort keeps the native selection.
  `droid/opus` and `cursor-cli/opus` stay Elite at medium, with the profile
  "All-round execution worker, especially strong at complex execution work and
  UI and 3D visual implementation." `devin/opus-fusion` stays Elite at medium,
  with the profile "All-round execution worker, especially strong at complex
  execution work." Devin Fable is unchanged. These three profile edits add no
  seat.

- **dsh ACP harness version check at install (Issue #231).** README Install
  and begin now shows how to read the loaded `@deepseek-ai/dsh-acp-app` and
  `@deepseek-ai/dsh-acp` versions instead of `agentInfo`. The verified
  harness is 0.1.7-rc.2. The launcher pins the harness to its own version, so
  an older harness needs a whole-dsh upgrade that the user decides. Only the
  dsh `acp_quirks` wording changed; there is no code or protocol change.

## 0.6.9 — 2026-09-29 (quota mappings, heartbeat authorization rows, permission wording)

Seats: restart required

The operator diff from v0.6.8 to this release
(`git diff v0.6.8..<this release> -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`)
is non-empty. Changed paths are `scripts/kaola-quota.py`,
`platforms/cursor-cli.yaml`, `platforms/droid.yaml`, `platforms/dsh.yaml`,
`platforms/opencode.yaml`, `platforms/zcode.yaml`, `scripts/adapters/dsh.sh`,
and `scripts/adapters/opencode.sh`. `scripts/kaola-acp-holder.py` and
`scripts/kaola-zcode-acp.py` are unchanged. The holder pins the quota catalog
at startup (Issue #162), so running seats keep the bytes they started with and
must restart after installing this release. The Grok Bot bridge is pinned in
the release's follow-up pin commit. The ten worker platforms keep their v0.6.8
`acp_command`, `acp_wrapper_pin`, and `acp_verified_versions`; those adapter
pins are intentionally not bumped in this release.

- **Quota model-package mappings and DeepSeek display names (Issue #222).**
  Cursor CLI's Grok 4.7 family (`grok-4.7`, `grok-4.7-xhigh`,
  `grok-4.7-xhigh-fast`) now maps to the `cursor-models` package; the Claude
  Opus family stays `other-models`, and `auto` / `default` stay
  `cursor-models`. Droid's static preset knowledge maps `auto` and
  `claude-opus-5-5` to Standard and `kimi-k3` to Core when the native
  `billingPool` is missing, null, or empty; a present native value still wins,
  and an unknown present value stays unmapped. ZCode's bare model id `GLM-5.3`
  maps to `bigmodel-coding-plan` (provider-qualified routes unchanged), and
  that package's display name is GLM Coding Plan. dsh and OpenCode display
  names are shortened to DeepSeek V4.1 Flash; launch model ids, preset ids,
  and the OpenCode Go package name are unchanged.
- **Heartbeat authorization carries Class definitions and eligible rows (Issue #223).**
  The Host heartbeat `authorization` object now directly carries the shared
  Expert, Elite, and Worker Class definitions and one row per locally
  available, currently authorized preset: exact id, class, the catalog's
  one-line profile verbatim, and grant, count, and state. A source pointer may
  name where those facts come from and does not replace them. The definitions
  grant no seats by themselves; eligible rows are the dispatchable set.
- **Worker-pool access is permission, and revocation stays durable (Issue #224).**
  The six Worker-pool presets are default-authorized permission, not a
  preference over a suitable authorized Elite preset. They stay outside the
  live-process cap; Elite still needs an explicit grant and Expert still needs
  per-task permission. Paused, revoked, and excluded presets remain recorded
  inside `authorization` when they are omitted from eligible rows. Compaction
  or recovery does not restore a revoked grant; restoration is only by owner
  reauthorization.

## 0.6.8 — 2026-09-28 (Host and Delegator state, authorization, QA, and installation)

Seats: restart required

The operator diff from v0.6.7 includes holder and platform changes. Running
seats keep the bytes they started with; restart them after installing this
release. The Grok Bot bridge is pinned in the release's follow-up pin commit.

- **Release validation (Issue #221).** The permission-default contract now checks
  detailed dsh sandbox and permission-wake facts in the architecture and API
  documentation where Issue #220 moved them, while retaining the README's
  pre-dispatch default checks. This changes test expectations only.

- **README user-path cleanup (Issue #220).** Documentation only. The front page now
  follows purpose → entry → install/use → worker selection → user/Agent
  responsibilities → further docs: the ACP/tmux probe note near installation, the dsh
  sandbox/probe narrative, per-platform bridge/translator launch internals, and the
  steering receipt vocabulary moved out of the README — the dsh sandbox-inheritance
  constraint into `docs/architecture.md` and the permission-wake semantics into
  `docs/api.md`, while the rest was already documented in the per-platform references
  and command reference, which the README now links briefly. User decisions kept:
  actionable install/start commands, concise platform caveats needed before dispatch
  (dsh full-access default and API-key precondition, Droid full bypass, ZCode entry
  variables), the complete ten-runtime/twenty-preset catalog, authorization
  statements, and safety-relevant choices. No behavior, Skill prompt, grant,
  installer, release, or test-framework change. Seats: restart not required.
- **Use canonical `<runtime>/<tier>` preset IDs in seat authorization surfaces (Issue #218).**
  Guidance and notation only. The generated catalog rows — the README preset catalog, the
  installed `profile-catalog.md`, the Worker-pool membership line, and each platform Runner's
  `references/platform.md` preset bullets — now carry each preset's stable ID
  `<platform id>/<tier>` (the exact 20: Elite 11, Worker 6, Expert 3) derived from the same
  `platforms/<id>.yaml` rows that render the model name, native launch ID, parameters, Class
  and profile; there is no second registry, and a declaration change regenerates the rows. A
  downstream authorization row (Delegator `delegator-heartbeat.json` snapshot spec, Host
  heartbeat `authorization` body per the #217 skeleton, authorization-change relays, and the
  handoff example's `authorized_platforms=<preset_id:count, ...>`) names a granted, paused, or
  revoked seat by that exact ID — so `cursor-cli/default` vs `grok/default` and
  `claude-code/default` vs `claude-code/sonnet` never blur — while count, Class grant
  lifetime, cap, quota units, seat identity and switch authorization stay separate facts, the
  six Worker presets remain one default-authorized pool entry (exclusions name exact IDs), and
  an optional `special_requirements` appears only when the owner actually supplied a deviation
  (`{"effort":"high"}`, `{"task_scope":"visual QA"}`); absent means none, an effort requirement
  changes only effort, a task scope only narrows coverage, and an unappliable requirement is
  reported rather than silently matched to a nearby ID. The catalog teaches that the ID names
  a configured preset, not proof of the actually-running model (Droid Auto and Devin ACP
  display drift), and at `start` the declared `--tier` with its requested/applied receipt
  still governs: the ID is state notation, not a new CLI flag, transport gate, capability
  inference, or authorization change. New focused suite
  `tests/contract/test-issue-218-preset-ids.py`. Seats: restart not required.
- **Keep Host and Delegator heartbeats as compact current-state JSON (Issue #217).** Fixed
  method stays in the installed Skills; each recurring prompt's mutable state is one JSON object.
  The Host `<repo>/.kaola/heartbeat-prompt.json` `body` now holds only that object — `project`
  (repo, short code, goal, stop boundary), `authorization` (effective grants, exclusions, quotas
  in their original units, one current value each), `active` (each in-flight or actionable
  issue/task with exact session, candidate, next action, evidence pointer), `pending` (unsettled
  QA, documentation, acceptance, finalize, cleanup or decision duties with scope, owner, evidence
  or gap, delivery boundary), and only nonstandard `recovery` pointers — with no header line,
  prose, Skill text, mission-ledger copy, test list or history. The field meanings live in
  `references/heartbeat-skeleton.md`; the existing carrier still supplies the native Skill entry,
  worker-event metadata and envelope unchanged. On each natural beat the Host reconciles the
  object with fresh forge, Workflow and Runner facts and replaces it whole: a closed issue leaves
  `active`, a changed grant replaces the old value, and unresolved cross-issue QA stays one
  `pending` entry until an evidence-backed Host verdict. Independent QA scopes may run in
  parallel on suitable authorized seats under one Host verdict; an integrated-candidate check
  waits for that candidate. The Delegator's state is one JSON object in the one newly authorized
  file `<repo>/.kaola/delegator-heartbeat.json` on the bound execution target, the same path for
  every outer runtime (Grok Bot reaches it through its existing locator): `project`, exact `host`
  locator verified by fresh Runner `status`, `authorization` a safe handoff needs, `watch`, `stop`
  (Kaola-Delegator `references/snapshot.md`, moved out of `host-platforms.md`). Its existing
  scheduled prompt stays static — Skill entry and project locator — and the existing native timer
  stays the only scheduler. The same object carries one fixed, platform-neutral schedule:
  `cadence` (timezone, start/end local time, interval), `timer_owner` (outer platform and native
  timer id), `day_start` (`reconcile_then_open_intake`: refresh Host identity, authorization,
  backlog and in-flight work before new claims open) and `day_end`
  (`pause_new_claims_keep_inflight`: at the final beat, e.g. 22:00 Asia/Shanghai, the Host stops
  new issue claims only while in-flight work and workers keep running; `confirmed` needs both the
  Host's acknowledgment and claim records showing no new claim after the cutoff, never send
  admission alone), each with a `state` and evidence pointers rather than history. An optional
  `final_stop` appears only when the owner sets a terminal boundary for the Delegator itself; the
  daily pause is never a Host stop or completion. Any outer platform rebuilds its own native timer
  from `cadence`, retiring the previous `timer_owner` timer before the replacement takes over and
  reporting an uncontrollable old timer instead of polling twice. The Host acknowledges a daily
  pause, records it in `authorization`, and opens no new claim until intake reopens. Each
  inquiry reads the file, audits the Host `body`, relays one concrete correction and replaces
  stale facts; a missing or unreadable file is reported and rebuilt from owner, Runner and forge
  records before any `start`, never read as blank authorization. Each file has one writer: the
  Delegator never writes the Host carrier (its old "maintain a heartbeat" prohibition now names
  the Host heartbeat) and the Host never writes the Delegator file; owner changes reach the Host
  as separate messages. Host startup no longer ends the `body` with the sweep line; the reply
  still does. No other new file, ledger, parser, scheduler, validator or transport; budgets
  unchanged. Guidance and templates only; the operator-test paths are untouched
  (`Seats: restart not required`).
- **Verify scoped installs, clean owned stale Skills, and recover build-skew refusals (Issue #215).**
  `render-skills.py --verify-install` now separates present-file alignment from expected-set
  completeness: a root holding only `kaola-project-runner` reports `incomplete` with the absent
  worker Skills in `missing` instead of claiming alignment, receipt-owned names this checkout no
  longer generates surface as `obsolete_owned`, foreign paths are reported as `unmanaged` and
  never counted as findings, and `--expect NAMES` verifies a deliberately scoped set under
  `scope: filtered` without presenting the root as complete. `install-local.sh` refuses before
  any write when the checkout's own `render-skills.py --check` fails (run
  `./scripts/render-skills.py --write` first), verifies every requested payload after writing and
  exits nonzero if one did not land, and reports a filtered request as `scope: filtered` with the
  unselected siblings' states — never as a complete-root upgrade. Obsolete receipt-owned copies
  are retired only when no other referrer remains and the bytes still match the receipt;
  modified, co-owned, foreign, and unreceipted paths are preserved and named with an owner-safe
  next action. With `--bin-links`, helper links report their actual target, build digest, and
  referrers separately from Skill alignment; a usable link to another accepted checkout is kept
  and reported `helper not upgraded` with its owner-safe transition route rather than being
  silently retargeted. The `worker-skill-build-skew` and `main-skill-build-skew` refusal routes
  are now owner-aware — the owning runtime's `--runtime NAME` route where the root is a runtime
  destination or a receipt records one, the generic `--skills-dir` route only where nothing owns
  the root — and carry the matching `--verify-install` command, prefer a complete-root refresh
  when siblings are stale, name the Delegator/operator handoff for a Host that cannot install,
  and gate retry on `mutation_status=not_started`. The operator-test paths
  (`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`,
  `scripts/adapters`, `platforms`) are untouched (`Seats: restart not required`); installed worker
  Skills carry the updated `kaola-acp.py`, so existing installs show the usual build-skew refresh
  route rather than requiring a seat restart.
- **Let the Host own adaptive QA and documentation coverage across issue deliveries (Issue #213).**
  Paired with Kaola-Workflow #1111. The Project Runner Host is the one quality owner: it decides
  what evidence is needed, who supplies it, whether it suffices, and when project-level QA and
  documentation accuracy are checked, from actual change scope, risk, integration state, and the
  user's delivery boundary — no fixed interval, issue count, mandatory separate reviewer, or extra
  QA seat. Workers supply their actual outcome, relevant checks, and affected documentation
  changes; task acceptance judges that assignment and is not a claim that project QA is complete.
  An aggregate check not yet run stays pending among the heartbeat's existing unfinished duties
  (never PASS because an issue closed), related issues may share one bounded integration QA/doc
  pass, and a concrete uncertainty, high-risk gap, or explicit request justifies an earlier bounded
  check. Valid evidence for unaffected behavior is reused, changed behavior invalidates only
  affected evidence, and binding project/user checks stay binding while redundant optional
  coverage may be reduced. Kaola-Workflow keeps claims, recovery, delivery, merge, closure,
  archive, and cleanup; a successful finalize or documentation docking is a lifecycle fact, not QA
  PASS, and where the installed finalize still requires its validation/docking artifacts they are
  produced honestly, never bypassed or fabricated. Updated the main Skill intro and steps 3–4, the
  `qa-evidence` and `doc-maintenance` references, the heartbeat skeleton's pending-duty slot, and
  the README; the Kaola-Delegator's periodic pace feedback is unchanged. No new QA ledger, schema,
  timer, or gate. Guidance only: transport, CLI, and model surfaces are unchanged and the
  operator-test paths are untouched (`Seats: restart not required`).
- **Expose installed local choices and add Codex Luna computer-use guidance (Issue #214).** The full supported-runtime catalog stays in the README; Delegator and Host choices require bound-target runtime discovery plus a matching installed Runner preset, then current authorization. Host profile context loads only applicable rows. Computer interaction prefers explicitly authorized, locally available Codex default, then eligible Worker-pool luna; visual review remains separate. Luna's owner-provided profile now names computer-use capability. Profile and prompt guidance only (Seats: restart not required).

- **Correct three contract-suite expectations left stale by #204's wording trim (Issue #209).**
  `test-issue-65-host-contract.py`'s `test_reference_starts_the_worker_from_the_host_with_a_runnable_example`
  now expects "the running holder's binding" (4af3686b dropped "own" from that sentence in
  `zcode-host-dispatch.md.tmpl`) and `test_reference_keeps_turn_end_and_exit_as_equal_triggers`'s
  regex now expects `` `exit_code=N`/`exit_signal=N` `` (4af3686b changed the separator from
  " or " to "/" in the same reference). `test-issue-162-upgrade-safety.py`'s
  `test_release_note_rule_and_no_rebind_wording` now pins "replace it with `drain-restart` at
  idle" in `templates/orchestrator/SKILL.md.tmpl` — 4af3686b deleted that file's only "no rebind"
  sentence outright rather than rewording it, and no other line in that file says "rebind", so the
  assertion now pins the equivalent current wording instead of text the source no longer carries.
  Test-side only: no template, reference, or budget byte count changed. `Seats: restart not
  required`.
- **Coordinate Host finalize safeguards with the Kaola-Workflow foreign-residue fix (Issue #212).**
  The Project Runner `workflow-worktree` reference gains a "Foreign files and finalize safeguards"
  section for the open upstream finalize defect (Kaola-Workflow #1110, unresolved pending a
  verified fixed-version adoption) that can mirror a foreign untracked file from the main checkout
  into a delivered finalize tree, as recurred in #192, #194, and #206. When a known foreign or
  protected file or an upstream finalize limitation affects the current run, the Host conveys that
  concrete constraint to the finalizing worker through existing task/run records; the finalizing
  worker reads the existing Workflow preview/finalization receipts, preserves unrelated files, and
  reports ownership ambiguity or a blocked sink honestly instead of deleting, staging, or adopting
  them; the Host reuses those receipts and the candidate diff to confirm known protected paths
  stayed out of the delivered candidate/archive and any temporary protection was restored, with
  concrete mismatches returned to the responsible worker. The affected run keeps its narrow
  `.git/info/exclude` protection as a temporary, project-specific measure with byte-exact
  restoration on completion or interruption and coordinated shared edits; it retires only after an
  authorized fixed-version adoption plus bounded consumer evidence, never merely because an issue
  closed. No ownership table, scan schedule, classifier, filter, second acceptance engine, or
  duplicate test run. Guidance only: transport, CLI, and model surfaces are unchanged and the
  operator-test paths are untouched (`Seats: restart not required`).
- **Consolidate repeated prompt guidance and retire conflicting lifecycle instructions (Issue #208).**
  The heartbeat skeleton now carries only project identity/authorization, task and worker locators,
  the frontier, open decisions/close-out and recovery pointers; the naming, one-issue, dispatch,
  acceptance, stop and report rules it used to restate live once in the main Skill the carrier
  loads every beat (the #205 one-time reconciliation after a Skill update moved there too). The
  seat lifecycle is stated once in main Skill step 5: acceptance authorizes the candidate's pending
  finalize, an accepted seat keeps only the finalize/cleanup duties it owns and is exact-stopped
  once it owns none or the seat is abandoned; the Host dispatch and QA references point there. The
  issue-dispatch reference no longer infers archive, finalize or waiting from a missing ledger or
  all-terminal missions. The Host startup ban on hand-reading `SKILL.md` is ZCode-scoped, so the
  Codex compact hook's installed-Skill reread stays valid; probe history moved to
  `docs/host-entry-evidence.md`; documentation maintenance points to the Workflow finalize
  contract for docking/archive/cleanup. Prompt/reference change only; the operator-test paths are
  untouched (`Seats: restart not required`).
- **Refine Cursor CLI’s profile and remove repeated per-profile cost wording (Issue #211).** Its Grok 4.7 `default` profile describes investigating unfamiliar problems, exploring solution paths, and autonomously carrying them through implementation for long-running, adaptive work. The DSH, Devin, and OpenCode `default` profiles no longer repeat cost wording already supplied by their Classes. Profile wording only; the operator-test surface is untouched (`Seats: restart not required`).

- **Recover confirmed quota exhaustion by Host and worker class, never by login (Issue #207).**
  Delegator and Host guidance now acts only on confirmed exhaustion — explicit runtime/provider
  error or usage evidence — while a generic 429, authentication error, timeout, transient failure,
  or reset-window metadata alone stays reported evidence, and a runtime shown to share the
  exhausted pool is not fresh quota. An exhausted non-ZCode Host is replaced by one ZCode Host
  through the existing exact-stop/new-Host handoff carrying grants, issues, valid evidence, worker
  ownership and pending close-out; an already-ZCode Host, or a fallback that cannot operate, goes
  to the user. An Expert task is preserved and escalated; an Elite seat is reclaimed, loses its
  grant for this run, and hands its task to another already-authorized Elite; a Worker task moves
  to another suitable Worker preset without cycling an exhausted shared pool; no suitable
  replacement means asking the user. Delegator and Host never attempt, retry, or delegate login,
  credential refresh, or account switching. Details live in the existing Delegator
  `references/host-brick.md` and Project Runner `references/quota-packages.md`, with pointers from
  both entry Skills and `worker-profiles.md`. Prompt/reference change only: no registry, watcher,
  retry loop, classifier, quota engine, or probe; transport, CLI, permission, and model surfaces
  are unchanged and the `platforms/` operator-test paths are untouched (`Seats: restart not
  required` for this change).
- **Expert, Worker and Elite preset classes; README reorganized around usage (Issue #206).**
  Every runtime/preset now carries one owner-defined operating class in its platform manifest
  (`<tier>_model_class`, validated at render): **Expert** (Claude Code `fable`, Codex `astra`,
  Devin `fable`) does complex thinking only — analysis, design, objective decomposition, review
  judgments, no concrete implementation — and needs explicit user permission for each task, with
  the Host reclaiming the seat at completion and no reuse from a completed task; **Worker** (the
  existing six default-authorized pool presets) is cheaper and generally weaker, for simpler
  bounded work, with the pool's cap exemption unchanged; **Elite** (the other eleven presets) is
  the main execution workforce under existing explicit grants. The Host's worker guidance now
  chooses by current authorization → class responsibility → profile/task fit → capacity, and a
  Host keeps only its authorized profile rows in context: the Worker rows plus granted Elite rows
  and an active approved Expert task, fetched by exact row from a new generated
  `references/profile-catalog.md` rather than the whole table, updating only changed rows later.
  Kaola-Delegator extracts and relays grants per class instead of catalog tables. The old
  Expert-grant reuse allowance and the "no heavy execution" wording are replaced. Three approved
  profile corrections: Grok CLI and Cursor CLI `default` drop "but prone to looping", Devin
  `default` drops "but somewhat slow", and Codex `luna` now says "good reasoning for its class".
  README now follows actual usage order — choose an entry, install and begin, select workers
  (runtimes, classes, and a class-grouped catalog of all ten runtimes and twenty presets with
  model, effort/parameters, and the full profile), authorization by class, what users specify
  versus what agents own, daily use, and a short agent section — and the catalog is a generated
  region that `scripts/render-skills.py --check` keeps in sync with the manifests. Implementation
  internals and history moved off the front page to the Skills, `docs/`, and this changelog. No
  model, effort, Fast, transport, or Host model-selection change; the `platforms/` diff is
  class and profile text only, but it is non-empty, so the release operator test for the next
  release reads `Seats: restart required`.
- **Make Host worker selection explicit and verify existing start receipts before dispatch (Issue
  #204).** A fresh Host-managed worker start now expresses the selected authorized configuration
  explicitly — `--tier <selected-preset>`, including `--tier default` when default is the actual
  choice — and lets the manifest resolve that preset's model/effort; an explicit authorized
  model/effort override keeps its own existing precedence instead. Before the first send, the Host
  reads that start's own receipt and reconciles `model_selection`/`config_application`/
  `effective_selection` against the originally authorized selection, not the command's own resolved
  default, interpreting aliases and stale echoes through existing platform evidence. A seat
  demonstrably outside the intended grant gets no project work: an unused seat is exact-stopped and
  restarted with the intended configuration, and a working seat keeps its existing safe stop/resume
  or `drain-restart` route, with the correction carrying the intended preset explicitly. Resume
  semantics are unchanged: a legitimate same-assignment resume still preserves its saved authorized
  model/effort. The shared Platform Runner wording now also clarifies that an existing grant —
  including the default-authorized pool — authorizes preset selection without a fresh user naming.
  Prompt/reference correction only: no new receipt format, authorization registry, CLI flag,
  transport classifier, model probe, or dispatch service.

- **Launch model evidence stays readable in `status`/`observe` (Issue #203).** `start` now hands
  its selection/application evidence (`model_selection`, `config_application`,
  `effective_selection` with launch-argv versus advertised values, `fast`, and the existing
  known/unknown verification facts) to the holder, which keeps it as `start_evidence` in the
  session record across its whole-record rewrites and returns it from `status`/`observe`. A resume
  of the same native session (matched by `acp_session_id`, never by Runner name) keeps the prior
  evidence as `start_evidence.inherited`; anything else stays unknown. Native resume selection,
  raw `start_selection`, drain-restart, and refusals are unchanged. Changes
  `scripts/kaola-acp-holder.py` (new `record_start_evidence` op): Seats: restart required for a
  running seat to keep this evidence; an older holder just reports `start_evidence_recorded: false`.

- **Relay the pool-vs-limited-seat capability policy in Host and Delegator guidance (Issue #202).**
  The Host worker-profiles reference and the Kaola-Delegator host-platforms guidance both now state
  the owner's operating heuristic: the six-preset autonomous pool is cheaper and generally weaker
  than the individually authorized limited seats outside it, so the pool exists for useful uncapped
  parallel throughput; for a complex or critical task, prefer a stronger authorized limited seat
  when available, then pick the specific worker by profile/task fit. This is a heuristic, not a
  benchmark or a claim that every limited seat wins every task, and it does not mean a pool member
  can only do narrow work — the pool's GLM and SWE-2 presets already carry substantial and
  full-cycle tasks. The Delegator relays this policy; it does not itself judge task fit or dispatch.
  No change to pool membership, the concurrency-cap exemption, model/effort, seat-binding, or
  permissions.

## 0.6.7 — 2026-09-28 (OpenCode default preset and sixth pool preset, six worker profiles, skew recovery routes, Devin advertised model)

Seats: restart required

The operator test
`git diff v0.6.6 v0.6.7 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
is not empty: it reports `platforms/claude-code.yaml`, `platforms/codex.yaml`, `platforms/devin.yaml`,
`platforms/dsh.yaml`, `platforms/opencode.yaml`, `platforms/zcode.yaml`, and
`scripts/adapters/opencode.sh` (#200 pins the OpenCode default model and rewrites the six
owner-stated worker profile lines; #197 rewrites the Devin `acp_quirks` model-advertising clause).
`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, and the other
nine `scripts/adapters/*.sh` are byte-identical to v0.6.6. The note is `Seats: restart required`
because the operator test is non-empty: a seat started on v0.6.6 keeps the platform facts it started
with, and its OpenCode `default` preset pins no model, so starting that preset from the stale tree
keeps the #200 `provider.no-route` failure. Run `install-local.sh` for every runtime you use, then
restart seats: the worker profile lines render into `references/worker-profiles.md`, the worker
platform facts, and the Host, Delegator, and README wording, so every worker's
`main-skill-build.json` moves, a Host start from a stale install refuses `main-skill-build-skew`,
and any other platform's stale worker Skills refuse `worker-skill-skew`.
`templates/grok-bot/accepted-revision.json` is at the content stage for this release's content
commit; the pin commit that follows names the v0.6.7 tag.

- **OpenCode default preset, sixth autonomous pool preset, six worker profiles (Issue #200).**
  OpenCode `--tier default` now explicitly selects `opencode-go/deepseek-v4.1-flash` (the
  provider-qualified ID already recorded as a real OpenCode 2.0.11 round trip in
  `docs/host-entry-evidence.md`) with no Runner effort override; a no-model start previously
  advertised `opencode/deepseek-v4.1-flash` and failed `provider.no-route`. That OpenCode
  default pair joins the default-authorized inexpensive pool as its sixth preset, with the same
  authorization and general-concurrency exemption as the existing five; other OpenCode models
  still require their own authorization. The six owner-stated worker profiles (Claude Code
  sonnet, Codex luna, ZCode default, Devin default, OpenCode, dsh) replace the previous
  one-line profile facts in the six platform manifests and render into
  `worker-profiles.md`, the Host and Delegator wording, and README without changing any other
  preset's model, effort, or Fast parameters.
- **Skew refusals name their recovery route (Issue #198).** `main-skill-build-skew` and
  `worker-skill-build-skew` keep their typed `not_started` shape and fields; their `detail` now
  names each affected root's existing installer route from the accepted checkout
  (`install-local.sh --skills-dir ROOT --platform PLATFORM`, plus `--no-orchestrator` for worker
  skew), states its ownership effect (receipt-owned copies only, existing referrers kept, the
  `generic` referrer added, `kaola-delegator` planned for main skew, a runtime referrer's own
  `--runtime NAME` install as the owner route), says an owned obsolete duplicate is withdrawn with
  that route plus `--uninstall` rather than deleted by hand, and names a renamed copy no installer
  manages for its owner. `worker-skill-root-unreadable` no longer suggests removing the root, and a
  `drain-stop-failed` after the exact stop was sent says to inspect `status` and `residual_pids`
  before another `drain-restart`. `host-exists` already directs attaching `existing_host` and is
  unchanged. Nothing is deleted, retried, or started automatically.
- **Devin's advertised model is not its running model (Issue #197).** The Devin platform note
  no longer claims the ACP model `currentValue` always stays `swe-2-high`: the option does
  not echo, and need not list, the `--model` a tier launches, so an `opus-fusion` seat can
  advertise the `-high` fusion id while Devin's native session store records the `-medium`
  preset it launched. Start receipts already separate the request, the argv application
  (`config_application.model.applied_via: "argv"`), and the ACP echo
  (`effective_selection.advertised_model`). The actual model stays `unknown`
  (`actual_runtime_model_id: null`) because the Runner reads no native store. A regression now
  locks both tiers to that outcome, and receipts and behavior are unchanged. `platforms/devin.yaml`
  changed, so the release operator test is non-empty.

## 0.6.6 — 2026-09-27 (quota reset windows, Droid shared Skill root, Host QA and pacing, five-preset worker pool)

Seats: restart required

The operator test
`git diff v0.6.5 v0.6.6 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
is not empty: it reports `scripts/kaola-quota.py` and all ten `platforms/*.yaml` (#192 adds
`windows` to every `quota_packages` row and a second Kimi package, and rewrites the catalog's
`windows` docstrings; #195 adds "Very low-cost" to the ZCode `default` profile).
`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, and `scripts/adapters/` are
byte-identical to v0.6.5. The note is `Seats: restart required` because the operator test is
non-empty and the holder pins the quota catalog at startup (#162): a seat started on v0.6.5 keeps
the old catalog and platform facts. Run `install-local.sh` for every runtime you use, then restart
seats: the main Skill and every worker's `kaola-quota.py` and `platform.yaml` changed, so every
worker's `main-skill-build.json` moves, a Host start from a stale install refuses
`main-skill-build-skew`, and any other platform's stale worker Skills refuse
`worker-skill-skew`. Droid users rerun `--runtime droid` to move to `~/.agents/skills` (#193).
`templates/grok-bot/accepted-revision.json` is back at the content stage for this release's
content commit; the pin commit that follows names the v0.6.6 tag.

- **Five worker presets are default-authorized under an authorized project task (Issue
  #195).** The Host may dispatch Claude Code `sonnet`, Codex `luna`, dsh `default`, Devin
  `default`, and ZCode `default` from the exact list in `references/worker-profiles.md`
  without per-seat, per-preset, or priority-order approval, and those seats neither consume
  nor are limited by the general worker concurrency cap. Every other runtime/preset still
  needs explicit authorization, prior grants stay valid, and actual quota/resource limits
  still apply; a runtime's `default` tier alone never qualifies. Reports show pool seats as
  live, exempt from `live N / authorized M` accounting. Operator-diff fact:
  `platforms/zcode.yaml` `default_model_profile` only.

- **Droid installs into the shared `~/.agents/skills` (Issue #193).** `--runtime droid`
  now joins `kimi-cli` and `dsh` in `$HOME/.agents/skills`, a documented Droid user root
  that Droid reads in the same bucket as `~/.factory/skills`, where same-name Skills are
  invalid. The same run withdraws only the `droid` reference from the retired
  `~/.factory/skills`: a copy only droid referred to is removed, a copy another runtime
  still refers to is kept with a duplicate-name warning, and a droid-only copy with edited
  bytes or a same-name directory without a receipt refuses the run before any write.
  Personal Skills are never touched; `--runtime droid --uninstall` withdraws from both
  roots. A pre-ledger receipt counts droid only in `~/.factory/skills`, where droid wrote
  it. Every other runtime keeps its current root, and the kimi-cli dual-root contract is
  unchanged. Existing installs move only when an operator reruns `--runtime droid`.

- **Host QA distinct from testing, evidenced redundancy, and adaptive verification
  cadence (Issue #194).** Testing executes checks; QA judges whether the product and its
  evidence satisfy the task and whether the verification work itself stays proportionate.
  The Host reuses sufficient recorded evidence by default and assigns a bounded,
  proportionate check when an in-scope user-facing outcome is undemonstrated, evidenced
  verification redundancy needs simplifying, or the user explicitly requests
  exploratory/user-flow/release QA — usually the original owner, not automatically a new
  seat: one short pointer in main-loop step 3 to the new `references/qa-evidence.md`
  (who, brief, return, reading a failure, redundancy/adaptive-cadence, compact
  CLI/UI/docs-only examples). Kaola-Delegator's existing follow-up cadence also compares
  outcomes, blockers, and repeated testing/QA against prior checks and relays one new
  pacing note when warranted, marking stall uncertainty; it still does not dispatch
  workers, copy the ledger, or re-run acceptance. No permanent QA seat,
  ledger, scoring table, or new scheduler.

- **Quota packages declare their reset windows (Issue #192).** `kaola-acp packages` no
  longer reports `windows: null` for every package: each row lists its confirmed reset
  windows from `5h`, `weekly`, and `monthly` (several may apply), `[]` means verified to
  have no time-based reset, and `null` remains only where the period is not established
  (Claude Code `extra_usage`, Devin `overage`, OpenCode `zen`). Weekly: Claude Code,
  Codex, Devin `max`, Grok; monthly: both Cursor packages; weekly + monthly: Droid `core`,
  dsh and OpenCode `opencode-go`; 5h + weekly + monthly: Droid `standard` (Factory's
  documented rolling windows); 5h: ZCode and OpenCode ZhipuAI coding plans; `[]`: Droid
  `extra_usage`. Kimi's two plans are told apart: `kimi-cli:managed` (weekly + monthly)
  and the new `kimi-cli:managed_monthly` (monthly only, `binds_models: false`, so model
  resolution is unchanged). The field names windows only, not amounts or reset times
  (`docs/api.md`); `references/quota-packages.md` adds the display rule (show weekly or
  monthly when a plan has one, 5h only when it has neither). Operator-diff fact: every
  `platforms/*.yaml` `quota_packages` and the `scripts/kaola-quota.py` docstrings; no
  catalog logic changed.

## 0.6.5 — 2026-09-27 (runtime-specific named tiers, worker profiles, identity-proven force stop)

Seats: restart required

The operator test
`git diff v0.6.4 v0.6.5 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
is not empty: it reports all ten `platforms/*.yaml` and all ten `scripts/adapters/*.sh`
(#188 replaces the `upgrade`/`alt` tier keys with `named_tiers` and per-tier keys, #190 adds
`<tier>_model_profile` and sets the Cursor, Droid, and Devin Opus presets to effort `medium`).
`scripts/kaola-acp-holder.py`, `scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, the
vendored bridge, and the Grok Bot bridge content are byte-identical to v0.6.4. The note is
`Seats: restart required` because the operator test is non-empty: a seat started on v0.6.4 holds
the old platform facts and tier set, and `upgrade`/`alternative` no longer resolve. Run
`install-local.sh` for every runtime you use, then restart seats: `scripts/kaola-acp.py` and the
worker and main Skills changed, so every worker's `main-skill-build.json` moves, a Host start from
a stale install refuses `main-skill-build-skew`, and any other platform's stale worker Skills
refuse `worker-skill-skew` (#162). `drain-restart` on a seat whose record carries `upgrade` or
`alternative` refuses `tier-not-declared` before it stops anything; pass an explicit declared
`--tier` (for example `--tier default`) to name the restart.

- **Worker profiles and per-seat model switching (Issue #190).** Every preset carries one
  user-defined line, `<tier>_model_profile` in its manifest (OpenCode unset), rendered into
  Project Runner's `references/worker-profiles.md`, which the Host, Kaola-Delegator and README
  read on demand. Guidance, not measured capability: the profile lines themselves change no model
  ID, effort, Fast, or `start` behavior (the Opus effort change is the next entry). Seats stay
  bound; only the user's explicit grant for a particular seat lets the Host select or switch that
  seat's model/preset within the same agent runtime, never across runtimes, with no new flow.
  Operator-diff fact: every `platforms/*.yaml` gains the profile keys.
- **Opus presets at effort `medium` (Issue #190, owner correction to #188).** Cursor `opus` is
  `claude-opus-5-5-medium` (mapped to `claude-opus-5-5`, effort via the `effort` option; the
  `-high` id stays mapped for explicit use), Droid `opus` is `reasoning_effort` `medium`, and
  Devin `opus-fusion` is `fusion-claude-opus-5-5-medium-sidekick-swe-2-medium` (SWE-2 sidekick
  still medium; this id is not yet spawn-measured). Defaults, Claude Code `default` (high), other
  tiers, Fast, and explicit `--model`/`--effort` precedence are unchanged; an explicit effort is
  a runtime parameter, not a model or seat switch grant. Operator-diff fact: `platforms/`
  cursor-cli, droid, devin and `scripts/adapters/` cursor-cli, droid, devin change.
- **`stop --force` never sweeps a reused agent process group (Issue #191).** Before signalling a
  dead or unreachable holder's recorded `agent_pgid`, force stop (and the validate sweep) now
  requires the group's live leader to be the recorded agent, matched exactly on its recorded
  `agent_started` second. A record without `agent_started` (from before #132) or a group whose
  leader is gone proves nothing, because macOS reuses a pgid once its group empties: its live
  members are not signalled, only this seat's `record.json` is retired, and the receipt reports
  `pgid_identity: "unverified"` with `pgid_identity_unverified` (`code: pgid-identity-unverified`,
  `live_members`, `signalled: false`). The reused-holder-PID branch retires only the record it
  read. Normal stop through a live holder and verified child-group sweeps are unchanged.
  This issue changes only `scripts/kaola-acp.py` and `scripts/kaola-acp-sweep.py`; the holder,
  bridge, quota catalog, adapters, and platforms are untouched by it.
- **Project Runner and Kaola-Delegator scheduling wording trimmed (Issue #189).** A clear task
  goes directly to a suitable authorized worker; split or parallelize only when the work needs it,
  and the authorized count is a ceiling, not a target to fill (replaces "dispatch every suitable
  match" at every heartbeat). Acceptance no longer requires a distinct verifier by default: the
  Host judges the worker's actual diff and run records against the currently effective global
  Workflow rules, reuses sufficient same-candidate evidence, and returns only concrete gaps for
  repair. Kaola-Delegator follows up at the user's agreed cadence. Hard cap,
  stop-before-start, acceptance-before-finalize, and close-out duties are unchanged; no new
  mechanism. `templates/grok-bot/accepted-revision.json` returns to the content stage.
- **Runtime-specific named tiers; `upgrade` retired (Issue #188).** Only `--tier default` is
  common; each platform lists its own names in `named_tiers` (README table). Claude Code
  `fable`/`sonnet`, Codex `astra`/`luna`, Cursor `opus`, Devin `opus-fusion`/`fable`, Droid new
  `opus` (`claude-opus-5-5`, effort `medium` since #190) plus `core`, Kimi `kimi-k2-8` (was
  `alternative`); dsh, Grok, OpenCode, ZCode are default only. `upgrade` and `alternative` have no
  alias: they, and a seat record carrying them in `drain-restart`, are `tier-not-declared`
  refusals. Defaults, model IDs, effort, Fast, and explicit `--model`/`--effort` precedence are
  unchanged; display names drop the effort suffix, which is shown separately. Operator-diff fact:
  every `platforms/*.yaml` and `scripts/adapters/*.sh` changes.

## 0.6.4 — 2026-09-27 (any supported CLI Host for Kaola-Delegator, resumable Claude Code native id)

Seats: restart required

The operator test
`git diff v0.6.3 v0.6.4 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
is not empty: it reports exactly one file, `platforms/claude-code.yaml`, whose `acp_quirks`
gains the #186 sourcing clause (a fresh seat's `acp_session_id` is process-local; `--resume`
takes `native_session_identity.nativeSessionId`). `scripts/kaola-acp-holder.py`,
`scripts/kaola-zcode-acp.py`, `scripts/kaola-quota.py`, and `scripts/adapters/` are
byte-identical to v0.6.3. The note is `Seats: restart required` because the operator test is
non-empty, and because the vendored Claude Code bridge changed underneath it: a seat started on
v0.6.3 has the old bridge and platform facts in memory, and a Host started from a stale install
is refused before it can dispatch. Run `install-local.sh` for every runtime you use, then
restart seats: the rebuild moves the main Skill build id in every worker's
`main-skill-build.json` (#187 installed-Skill change), so a Host start from a stale install
refuses `main-skill-build-skew`, and any other platform's stale worker Skills refuse
`worker-skill-skew` (#162).

- **Kaola-Delegator selects any supported CLI Host, not only ZCode (Issue #187; history #74, #119, #122, #126).**
  The Host platform is chosen apart from the authorized worker platforms; the Delegator then uses
  that platform's own Runner, its `host_skill_entry` as the first prompt line (codex
  `$kaola-project-runner`, kimi-cli with its trailing space), the standard
  `<platform>-<PROJECT_CODE>-orchestrator-<purpose>` name, and its native resume id, from the new
  rendered `references/host-platforms.md` (one row per `platforms/<id>.yaml`). One live Host per
  canonical root, exact stop, and the Grok Bot co-location attestation (now
  `--worker <Host platform>`) are unchanged. `install-local.sh` installs `kaola-delegator` on
  Codex and generic destinations whatever `--platform` selects; a first install no longer needs
  `zcode` in `--platform` (the Host-runtime leftover rule of #160 is unchanged). Startup proof is
  platform-specific (E1 or E2, `docs/host-entry-evidence.md`); isolated codex-acp 1.13.1 E2 probes
  answered `SKILL-NOT-LOADED`, recorded as that narrow fact, and no unconditional tool_call rule
  follows from it. **Seats: restart required.** Installed Skills change — the Delegator, plus two
  main-Skill sentences that move the main Skill build id in every worker's
  `main-skill-build.json` — so reinstall before a Host start or it refuses
  `main-skill-build-skew`. No holder, bridge, quota, adapter, or platform-manifest byte changed
  by this issue.
  **Grok Bot account-side live UAT remains unverified for v0.6.4.** The account bridge content is
  byte-identical to v0.6.3 and no live Grok Bot delegation (locate → load Kaola-Delegator →
  any-platform Host start) was executed for this release; only the structural verifier PASS and
  the `--worker <Host platform>` attestation change are evidenced. This is not a claim that all
  ten platforms' current live UAT was re-run.

- **claude-code seats now publish `native_session_identity` (the native Claude UUID) on a seat's first turn, fresh or resumed (Issue #186).**
  A fresh seat's recorded `acp_session_id` is bridge-process-local and can never be resumed after
  a stop: `--resume` uses the newest `native_session_identity.nativeSessionId`, readable with
  `capture` — a later event supersedes an earlier one, since a resume-failure fallback replaces
  the conversation. The vendored bridge emits the update in the ZCode shape on the first turn
  (fresh, resumed by native id, or cancelled) and on the fallback conversation, de-duplicated per
  announced id, preferring the announced id on a cancelled fallback turn and never clearing a
  binding for an empty id; the change is recorded in `vendor/claude-code-acp/UPSTREAM.md` and
  `dist/` was rebuilt (`kaola-dist.py --check` clean). **Seats: restart required.** The operator
  test is non-empty (`platforms/claude-code.yaml`), and a running Claude Code seat keeps the old
  vendored bridge until it restarts. Contract coverage:
  `tests/contract/test-issue-186-claude-native-identity.py`.

## 0.6.3 — 2026-09-26 (seat build tracking and drain-restart, Codex systemError turns, droid model verification)

Seats: restart required

The operator test
`git diff v0.6.2 v0.6.3 -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
reports only `scripts/kaola-acp-holder.py`: build identity, the eager quota import,
and the idle stop (#162), boot-death ordering (#174), Codex `systemError` turns
(#173), and the single sibling import (#184). The ZCode bridge, `kaola-quota.py`,
the adapters, the platform manifests, and the Grok Bot bridge content are
byte-identical to v0.6.2. Run `install-local.sh` for every runtime you use before
you restart seats: a start from an installed Skill tree or from `~/.local/bin` on
any platform now refuses `worker-skill-skew` when that platform's installed worker
Skills differ (#162). A seat started before this release recorded no build
(`reported_drift` names `build-unrecorded`) and never reports `stale`, so restart it
deliberately. It also recorded no start selection, so `drain-restart` on it needs
`--model`, `--effort`, `--tier`, or `--fast`.

Net surface against v0.6.2 (several entries below are refined by later entries in
this same release): `drain-restart` is a new command; `stale`, `stale_reasons`,
`restart_files`, `missing_files`, and `reported_drift` are `status`/`list` facts
only and never refuse `send` or `steer`; there is no `--confirm-stale` flag; the
emitted `reported_drift` values are `REPORTED_DRIFT_VALUES` in
`scripts/kaola-acp.py` (`install-root-mismatch` and `quota-drift` never shipped in
a release); and `kaola-locate.py --intent` accepts only `start` and `resume`.

- **Contract suites no longer inherit the seat's `KAOLA_*` environment (Issue #182).**
  A focused loop run from a dispatched seat inherits `KAOLA_ACP_HEARTBEAT_HOST` and
  `KAOLA_ACP_DISPATCHER` naming different holders; every suite that built its command
  env from `os.environ` copied them into the spawned `kaola-acp.py`, whose `start` was
  then refused `heartbeat-host-conflict` pre-spawn while the suites' error-only
  receipt checks passed the typed refusal, so the failure surfaced later as
  `no-session`. The 14 affected suites now build the command env as
  `{k: v for k, v in os.environ.items() if not k.startswith("KAOLA_")}` and set their
  own fixtures back (the #176 / `test-issue-98-dsh-acp.py` pattern); ten helpers also
  fail on `result == "refused"` when `check=True`, so a refusal surfaces at the
  command that was refused. `test-issue-130-pty-retired.py` is fixed transitively
  through `test-acp-contract.py`, and `test-zcode-acp-contract.py` measures the
  runtime fallback with `KAOLA_ZCODE_*` absent. Each touched suite now passes both
  from a dispatched seat and under `./scripts/validate.sh`, which already dropped the
  namespace (#115).
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty: only `tests/contract/` files changed.

- **A Codex turn that dies in `threadStatus systemError` is recorded `turn_failed`, and its worker events stay staged (Issue #173).**
  When a Codex backend became unreachable, every Host turn began with an automatic
  compaction that failed: the ACP stream reported `session_info_update`
  `_meta.codex.threadStatus {type: systemError}` and then an error
  `agent_message_chunk`, but codex-acp 1.13.1 still answered
  `{stopReason: "end_turn"}`. The holder recorded `turn_ended
  outcome=turn_completed stop_reason=end_turn`, `_worker_event_turn_end`
  confirmed the events the notification turn had delivered, and the Host sat idle
  with finished workers and no `status`/`observe` field showing the failure. The
  holder now reads the one structured failure signal the adapter puts on the wire:
  during an active turn of this session, a `_meta.codex.threadStatus` of
  `systemError` marks the turn, and the prompt response is recorded `turn_failed`
  while `stop_reason` stays verbatim (`end_turn`), per the #113 contract. The
  events the failed turn delivered stay unconfirmed and redeliver at the next
  healthy boundary, with a new event, or on resume; `status`/`observe` then report
  `turn_outcome: turn_failed` and `send`/`wait` receipts carry
  `error.code: agent-system-error` with the `threadStatus`. The last status in the
  turn wins, so a turn that recovers stays healthy; `willRetry` reconnect attempts
  do not fail a turn; `fatal_error` is untouched (a `systemError` is per-turn and
  recoverable, not a sticky start verdict); and no new status field or adapter
  capability is added. Every non-codex platform and every healthy codex turn
  (whose final status is `idle`) is receipt-identical to before.
  **Seats: restart required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is not empty: `scripts/kaola-acp-holder.py` changed (the turn-outcome detection),
  so a running seat only picks up the new holder bytes by restarting. Contract
  coverage: `tests/contract/test-issue-173-codex-system-error-turn.py`,
  `tests/contract/test-issue-90-event-confirmation-race.py`.


- **One installed-Skill scan per `drain-restart`, and one imported sibling in the holder (Issue #184).**
  `drain-restart` decided the pre-spawn refusals and then called `start`, which decided
  them again, so a single restart walked the installed Skill roots twice. `command_start`
  now accepts a decision the caller already computed, and `drain-restart` hands over the
  one it made before it stopped anything, so the scan happens once. The holder's
  `SIBLING_MODULES` tuple, its loop, and the `if name == "kaola-quota.py"` branch inside it
  collapse to the single sibling that loop ever loaded. Nothing observable changes: the
  pre-stop state pre-read, its idle predicate, and both the `drain-not-idle` and
  `drain-stop-failed` refusals are unchanged, and the consolidated receipts were compared
  key-by-key against the previous build across the busy, unreachable-holder,
  exited-but-ready, both stop-timeout, and success paths.
  **Seats: restart required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is not empty: `scripts/kaola-acp-holder.py` changed (the sibling import), so a running
  seat only picks up the new holder bytes by restarting. Contract coverage:
  `tests/contract/test-issue-162-upgrade-safety.py`,
  `tests/contract/test-issue-164-pre-spawn-bridge-facts.py`,
  `tests/contract/test-issue-168-drift-enumeration.py`.

- **Droid's `model_verified` is verified from the agent's own current-model echo (Issue #185).**
  Droid's `model_verified` was always `unknown`: its only read-only catalog probe is
  `droid --version` (no readable model catalog), and `session_meta.models.currentModelId` is a
  frozen `session/new` snapshot a later `session/set_config_option` never refreshes. Neither can
  verify a selection. The live evidence Droid does give is its own post-set
  `config_option_update` echo: the holder mirrors it into
  `session_meta.configOptions[model].currentValue`, and `start` reads it back through
  `effective_selection`. On Droid only, `start` now derives the verdict from that echo -
  `true` when the echoed model equals the resolved selection (the echoed `reasoning_effort` is
  compared only when the Runner pinned an effort), `false` with `actual-model-mismatch:<id>` on a
  mismatch, and `unknown` when unreadable or when a preserved resume has no Runner target -
  and records `model_evidence_provenance.actual.source` as `acp-config-echo`. On a launch-argv
  start (`effective_model_source: "launch-argv"`) the verdict compares the agent's echoed
  `advertised_model`, never the argv value the Runner supplied, so an argv model the agent never
  adopted verifies `false`. The verdict is
  reported evidence, never a start gate; every other platform stays `unknown`, since its
  advertised value can be launch-argv derived or stale (Issue #140).
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty: only the per-call CLI (`scripts/kaola-acp.py`), its rendered copies, docs, and tests
  changed. Contract coverage: `tests/contract/test-droid-acp-contract.py`.

- **One default-fill site, explicit flags by argparse `None`, and a slimmed `drain-restart` (Issue #181, following the bba3733..fe480d3 architecture review).**
  `command_start` now records the *effective* permission mode (`--mode`, else
  the platform `ACP_SKIP_MODE` default) in the holder's `start_selection`, so a
  fresh `start` without `--mode` records what it applied -
  `bypassPermissions` for claude-code, `auto-high` for droid - while a
  platform with no default (`dsh`, `cursor-cli`, `opencode`) still records
  `null`. The second fill site #163 added to `apply_recorded_selection` is
  gone, along with the third copy of the same table in `kaola-tmux.sh`, which
  duplicated `ACP_SKIP_MODE` exactly; that layer now forwards only an explicit
  `--mode`. `_selection_explicit` no longer re-reads `sys.argv`, which missed
  prefix abbreviations and the `--flag=value` form: every selection flag,
  including `--fast`, defaults to `None`, so explicitness is `None`-ness and
  argparse's own parsing decides. An absent `--fast` still means off.
  `drain-restart` gives up its 0.2 s idle poll: a live holder gets one idle
  read followed by its already-atomic `require_idle` stop, a busy seat gets an
  immediate `drain-not-idle` refusal, and retry timing stays with the Agent. A
  seat whose holder is already gone has nothing to drain, so it restarts
  without an idle read and is never refused for idleness. The restart's
  receipt reports the mode the new start actually applied, so a pre-#162 seat
  that recorded no mode is no longer shown as `mode: null`. Its post-`start`
  scan over `command_list` is gone, leaving `adoption` as
  a direct read of the new start's own `dispatcher`. The locator's no-op
  `--intent` values (`status`, `send`, `stop`, `observe`) are removed; only
  `start`/`resume` were ever read.
  **Seats: restart required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  reports `scripts/kaola-acp-holder.py`: the unused `KAOLA_ACCEPTED_REVISION`
  environment scrubs are removed, and nothing in the repository ever set that
  variable - the accepted revision travels as holder argv. A running holder
  must restart to pick up the new file.

- **`pre_spawn_refusal` is the single start-decision site (Issue #180, superseding #171 and resolving #172).**
  `command_start`'s five refusal branches repeating its checks could never
  fire and are deleted; it returns the alignments and heartbeat resolution
  it computed for `command_start` to reuse, so every installed Skill root
  is hashed once per `start` (a `drain-restart` scans twice: the pre-stop
  decision plus the post-stop start). The refusal path drops the
  `--version` probe: a refused `start`/`drain-restart` never waits on the
  runtime binary and keeps its bridge and runtime-binary facts minus
  `version`; `preflight` still reports `version`.
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty: only the per-call CLI, its rendered copies, and tests changed.
- **`docs/api.md` names the field that carries the current model selection, and the droid model preset is confirmed applied on every start (Issue #183).**
  Owner-requested check: droid seats must run the first-class `auto`
  routing, not the CLI default promo `gpt-5.6-sol`. Direct ACP probes
  (droid 0.225.1) plus the code settle it: KPR applies
  `session/set_config_option model=auto` at every droid start, on the worker
  path and on a droid seat named as a Host alike - the only session-name
  condition in the apply loop is the ZCode-only Host model pin, which changes
  nothing for droid. The earlier `gpt-5.6-sol` reading came from
  `record.json` snapshots taken before the preset: `initial_config_options`
  and `session_meta.models.currentModelId` are both `session/new` snapshots
  that a set never refreshes. `docs/api.md` now says so and names the
  current-selection fields, `session_meta.configOptions[model].currentValue`
  (`status`/`observe`) and `effective_selection.effective_model` (`start`).
  It also records the protocol limitation: ACP 0.225.1 shows which model is
  *selected* but carries no per-turn attribution, so it cannot prove which
  model *served* a turn; the probe measured the selection holding across
  three prompts with no revert. The target is the catalog's Auto Model entry
  (`modelId` `auto`, display name "Auto Model"); pinning any specific model
  (`gpt-5.6-sol`, `claude-*`, or otherwise) and the CLI default are both
  rejected as fallbacks. No production code changed. The droid contract suite
  now reads the selection back from the agent's own
  `config_option_update` echo - the only read-back ACP 0.225.1 gives for a
  set, since the set result is an empty `{}` and the `session/new` `models`
  snapshot is never refreshed - and asserts the echoed `model` `currentValue`
  is exactly `auto` on the worker path, on a droid seat named as a Host, and
  after three prompts (the persistence probe-2 measured live: one set, three
  prompts, zero reverts). Fixing those assertions exposed a mock-fidelity
  bug: `tests/contract/fake-droid-acp-agent.py`'s `option_current` patched
  only the changed option against the frozen `CONFIG_OPTIONS` constant, so a
  later `autonomy_level` set re-emitted the stale `gpt-5.6-sol` and masked
  the model. The mock now merges the session's live state, matching live
  0.225.1, where a later unrelated set keeps the previously selected model.
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty for this change: it touches only `docs/api.md`, `CHANGELOG.md`,
  and the droid contract suite. Contract coverage:
  `tests/contract/test-droid-acp-contract.py`.

- **The `reported_drift` vocabulary is one code constant, `install-root-mismatch` and `quota-drift` are gone, and `kaola-quota.py` is restart-required (Issue #179).**
  `REPORTED_DRIFT_VALUES` in `scripts/kaola-acp.py` is the single place the
  emitted set lives; every `reported_drift` append is a member, and the prose
  surfaces (`docs/api.md`, the worker status paragraph, the ZCode Host
  dispatch reference) now name the field instead of listing values, so no
  prose list can diverge from the code. `install-root-mismatch` and its
  `_expected_install_tree` comparison are removed: the tree of whichever CLI
  copy runs `list` is not this seat's expected root, and a moved or deleted
  checkout is already `recorded-path-missing` while an in-place reinstall is
  already the byte comparison. The unused `seat_freshness` `repo` and
  `installed` parameters and the `recorded_root`/`install_root` receipt keys
  are gone. `quota-drift` is dropped because `kaola-quota.py` becomes
  restart-required: the holder pins that catalog at startup (Issue #162), so a
  running seat only picks up its new bytes by restarting, while the per-call
  CLI re-imports it every call and would otherwise stamp `view` with the old
  code and `observe`/`status` with the new. This **reverses #166's
  quota-only "restart not required" for future releases**: a release that
  changes `kaola-quota.py` is now `Seats: restart required`, and a
  non-exempt seat reports `stale: true` with
  `restart_files: ["kaola-quota.py"]` (an exempt checkout seat reports
  `checkout-drift`). A contract test asserts every holder `SIBLING_MODULES`
  entry is restart-required. No `cli-drift`/`quota-drift` merge and no
  changed-file list on `cli-drift`.
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty for this change: the new classification runs in the per-call CLI,
  and live holders already record `kaola-quota.py` in `script_paths`, so
  running seats pick up the new reporting immediately - the file set in the
  operator test changed, but no holder, bridge, adapter, or protocol bytes
  did. A seat whose `kaola-quota.py` already differs on disk will now report
  `stale: true` with `restart_files: ["kaola-quota.py"]`.
  Contract coverage: `tests/contract/test-issue-168-drift-enumeration.py`,
  `tests/contract/test-issue-165-path-drift.py`,
  `tests/contract/test-issue-162-upgrade-safety.py`.
- **The #65 Host-contract suite drops a dispatched seat's inherited `KAOLA_*` bindings before it starts its fixture session (Issue #176).**
  `test-issue-65-host-contract.py` failed intermittently in this environment
  with `no-session` on `send`: run as a focused loop from a dispatched seat,
  its `start` inherited the seat's `KAOLA_ACP_HEARTBEAT_HOST` +
  `KAOLA_ACP_DISPATCHER` and was refused `heartbeat-host-conflict` before
  anything was spawned, identically on the unmodified base `2e18946`. A typed
  refusal reports `result: "refused"` with no `error`, so the suite's own
  check passed the refused start and the failure surfaced only later at
  `send` as `no-session` - the anchor behavior under test never got its
  start. The suite now drops the inherited `KAOLA_*` namespace and sets the
  one fixture it needs (the rule `validate.sh` applies to every suite, and
  the `test-issue-98-dsh-acp.py` pattern), and its `cli()` fails a typed
  refusal at the command that was refused. Not a boot race and not resolved
  by #174's ordering fix: a pre-spawn refusal never reaches the boot. No
  script changed. Evidence: 12/12 green focused runs at rest and 12/12 while
  a full `validate.sh` ran concurrently (0/12 before the fix), and the full
  `validate.sh` green at rest and under that load
  (/tmp/kpr-i176-loop-rest.log, /tmp/kpr-i176-loop-fixed-rest.log,
  /tmp/kpr-i176-loop-fixed-load.log, /tmp/kpr-i176-validate.log).
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`
  is empty: only the contract test changed.
- **A stale seat still transports: the seat-stale send/steer gate and `--confirm-stale` are removed (Issue #178).**
  `stale`, `stale_reasons`, `restart_files`, and `reported_drift` stay pure
  `status`/`list` facts. The #162 refusal blocked previously working
  automation (the holder loads its modules at startup, so an old holder is
  internally consistent); the do-not-dispatch-a-stale-seat policy stays in
  the orchestrator template as an operator-confirmed exception with no flag,
  and `kaola-tmux.sh` drops `--confirm-stale`. The Delegator handoff command
  shape delivers to a stale Host seat with no flag or remedy text. Contract
  coverage: `tests/contract/test-issue-162-upgrade-safety.py` and
  `tests/contract/test-issue-168-drift-enumeration.py`.
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty: only per-call CLI files, templates, and docs changed.
- **A boot-time agent death is reported as the failed start it is, never as an initialize timeout (Issue #174).**
  `test-issue-98-dsh-acp.py::test_a_confined_boot_write_failure_names_its_cause`
  flaked under load: the receipt came back `acp-initialize-timeout` (once the
  state `agent_exited`) instead of the expected `acp-initialize-failed` naming
  the confined-boot cause, identically on the unmodified base. The agent's
  fast boot death raced three sequential observations of it. A request whose
  frame was never written (the agent already dying at the send) had its slot
  popped by `send_request`, and `on_agent_exit` cleared `pending_out` while
  resolving it, so `wait_response`'s slot lookup missed and the death read as
  a timeout it was not; `on_agent_exit` published or clobbered
  `state = "agent_exited"` around `run()`'s verdict, which a start's
  terminal-state wait could read instead of `error` + `fatal_error`; and
  `start_failure_facts` read the stderr ring before the exit was observed, so
  the cause-carrying tail could be empty. A failed frame write is now
  remembered on the connection and classifies the boot as
  `acp-initialize-failed`; the exit resolves still-pending requests in place
  (each waiter pops its own slot) and never touches the boot verdict states;
  and the stderr tail is read only after the exit is observed, under the grace
  an agent gets to exit after its stdin closes. No retry, harness, or knob was
  added, the test is unchanged and not skipped, and the mock-agent admission
  contract (`pending_out` membership as "the frame was written") is unchanged.
  **Seats: restart required.** This change is in `scripts/kaola-acp-holder.py`
  and its rendered copies; the operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is not empty.
- **`command_start` no longer repeats the host-entry and host-exists checks `pre_spawn_refusal` already made (Issue #169).**
  Since #164 `command_start` calls `pre_spawn_refusal` first on the same args
  in the same process, so the repeated Issue #122 (host-entry-unsupported)
  and Issue #132 (host-exists) guards that followed it could never fire. Each
  guard and its rationale now live once, in `pre_spawn_refusal`; `command_start`
  keeps a one-line note naming what already returned. Dead-code removal: no
  behavior change, and the existing #122/#132 contract coverage
  (`tests/contract/test-issue-119-host-entry.py`,
  `tests/contract/test-issue-74-kaola-delegator.py`) stays green.
  **Seats: restart not required.** Only the dead code in `kaola-acp.py` and its
  rendered copies changed; the operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty.
- **Drift enumerations name every `reported_drift` value (Issue #168).**
  The seat-stale refusal, the worker status paragraph, and the ZCode Host
  dispatch reference now name pin-drift, cli-drift, quota-drift,
  recorded-path-missing (a recorded script path no longer exists), and
  install-root-mismatch (the seat's install tree moved or was re-rooted).
  Seat behavior is unchanged. Contract coverage:
  `tests/contract/test-issue-168-drift-enumeration.py`.
  **Seats: restart not required.** The operator test
  `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/kaola-quota.py scripts/adapters platforms`
  is empty: this change is refusal prose, reference text, and the rendered copies of those texts.
- **`kaola-quota.py`-only drift is reported without marking seats stale (Issue #166).**
  `status` and `list` report `quota-drift` when a recorded quota digest changes;
  legacy records without a quota digest remain silent, and the documented
  skill-difference staleness contract is unchanged. **Seats: restart not required.**
- **Rename the pin-drift contract test to match its non-stale assertion (Issue #167).**
- **A removed or moved recorded path, or a reinstall under a different root, is reported by name (Issue #165).**
  #162 recorded absolute `script_paths` and flagged byte drift, but a recorded
  path that no longer resolves (the checkout moved or was deleted) yields no
  digest, so it was neither "changed" nor "unchanged" and went unreported;
  a seat reinstalled under a different root also said nothing. `status` and
  `list` now name `recorded-path-missing` (with the names in `missing_files`)
  and `install-root-mismatch` (with `recorded_root` and `install_root`) in the
  existing `reported_drift` vocabulary. The root comparison is per platform:
  the expected tree is the seat's OWN `skills/<platform>-kaola-project-runner`
  sibling when this CLI runs from an installed Skill tree, so the documented
  Host sweep that runs `list` from one platform's tree does not falsely flag a
  seat of another platform, and a genuinely re-rooted seat still is. Both
  conditions are evidence only: they never set `stale` and never gate
  transport. The holder, ZCode bridge, and protocol are unchanged. Contract
  coverage: `tests/contract/test-issue-165-path-drift.py`.
  **Seats: restart not required.** Only `kaola-acp.py` reporting changed; the
  operator test `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms` is empty.
- **Running seats record their build and accepted revision; status and list flag drift; a skewed seat is not dispatched; drain-restart replaces the process at idle (Issue #162).**
  The holder writes `runner_build`, `accepted_revision`, and `script_paths`
  into its record and state at startup, and loads `kaola-quota.py` then so a
  later `install-local` directory swap cannot mix two builds in one process.
  `status` and `list` report that build. `stale` blocks `send`/`steer` only
  for the release-note restart set (holder, ZCode bridge, adapters, platform
  manifest). Pin drift and CLI-file drift (`kaola-acp.py`, `kaola-tmux.sh`)
  are reported and do not refuse. A holder-identical pin bump does not refuse
  sends. `baseline_exempt` is true only for a direct checkout invocation;
  a `~/.local/bin` start is not exempt, because that link resolves into the
  checkout. The #105/#121 build-skew check runs on every platform's `start`,
  including worker starts and starts via `~/.local/bin`. `send` and `steer`
  refuse `seat-stale` unless `--confirm-stale` is passed. `drain-restart
  --resume`/`--continue` runs start's pre-spawn refusals before it stops,
  then waits for idle, exact-stops, and starts a new holder carrying the
  recorded model, effort, tier, and fast. It is not a rebind, and a live
  holder is still never hot-replaced. A refusal after that stop reports
  `mutation_performed: true`. `kaola-locate.py` reports `zcode_runtime` on
  every receipt and refuses `zcode-runtime-invalid` or `zcode-runtime-unset`
  only for `--worker zcode --intent start|resume`, before preflight's
  `acp-runtime-missing`.
  **Seats: restart required.** This release changes the holder (build identity
  and eager sibling import) and the stop request (`require_idle`). Operator
  test: `git diff OLD NEW -- scripts/kaola-acp-holder.py scripts/kaola-zcode-acp.py scripts/adapters platforms`.

- **Pre-spawn `acp-bridge-missing` and `acp-runtime-missing` refusals carry preflight's bridge facts (Issue #164).**
  `preflight`, `start`, and `drain-restart` share one bridge-file and ZCode-runtime
  presence decision. A pre-spawn refusal still leaves `mutation_status` `not_started`
  and `mutation_performed` false, and a drain-restart refusal still carries `action`
  and `start_selection`. The receipt's `bridge` / `runtime_binary` facts match
  preflight, including a runtime `--version` only when that binary is already an
  absolute executable. This does not change the holder, the ZCode bridge, or the
  ACP protocol.

- **`drain-restart` applies and reports the platform default permission mode when none was recorded or passed (Issue #163).**
  When mode is neither recorded nor passed, the restart applies and reports the
  same permission mode a fresh start applies. An explicit mode still wins, and
  a recorded mode still wins over that default. The
  `drain-restart-selection-unknown` refusal is unchanged for model, effort,
  tier, and fast. This does not change the holder, the ZCode bridge, or the
  ACP protocol.

## 0.6.2 — 2026-09-25 (kimi-cli dual root, Delegator owner-preserving refresh, api runtime table)

- **`install-local.sh` refreshes an owned `kaola-delegator` leftover under a Host root that must not install it (Issue #160).**
  A `--runtime zcode` (or any non-Codex/generic Host runtime) install never introduces
  `kaola-delegator`, but if an **owned** copy already sits under the Host root — left by an
  earlier `--skills-dir` / generic install — a reinstall left it stale (neither updated nor
  removed), so it could stay on an older build while `kaola-project-runner` and the worker
  pin advanced. Control-plane planning now refreshes an already-owned Delegator's **content**
  on a Host-runtime reinstall without registering the Host runtime as an owner: referrers
  stay exactly as recorded, so the copy's lifetime stays tied to its original referrers
  (e.g. `generic`), the documented `--skills-dir ~/.zcode/skills --uninstall` remediation
  still removes it after a refresh, and zcode alone can never keep it alive. A same-build
  reinstall is a no-op, a foreign unowned tree or a foreign/broken symlink is refused before
  any write (like any other foreign Skill path), and `--no-orchestrator` skips this planning
  entirely. The fresh-install `no_external` default is unchanged. Contract coverage:
  `tests/contract/test-installer-runtimes.sh` pins the default (fresh `--runtime zcode` and
  `claude-code` never introduce the Delegator) plus owner-preserving refresh under both
  roots (referrers stay `[generic]`), the no-op, the zcode uninstall that keeps the copy
  both with and without a prior refresh, the generic-removal remediation after a refresh,
  the foreign tree and foreign/broken-symlink refusals, and the `--no-orchestrator`
  untouched leftover.

- **`--runtime kimi-cli` dual-installs into both Kimi Code user Skill roots (Issue #159).**
  Kimi Code CLI scans `~/.agents/skills` and `${KIMI_CODE_HOME:-~/.kimi-code}/skills`, but
  `install-local.sh` wrote only the shared root, so a pin/Host refresh that followed the
  matrix could leave Kimi Code without Runner Skills. `--runtime kimi-cli` now installs and
  uninstalls BOTH roots, each with its own receipts set: the referrers ledger records
  `kimi-cli` in every root it owns (the shared root keeps its Skills while `dsh` still refers
  to them, and a kimi-cli uninstall also withdraws the kimi-specific root, whose only
  referrer is kimi-cli). Every destination is planned read-only before any write, so a
  refusal in either root still aborts the whole run before the first byte lands. The host
  entry matrix, `docs/host-entry-evidence.md`, and the #105 build-skew scan
  (`kaola-acp.py` `HOST_SKILL_DISCOVERY_DIRS`) now cover both roots, with the Issue #119
  lineage re-measured for Kimi Code 2.0.2+ (upstream skill-location docs retrieved
  2026-09-24; the installed binary on the maintainer Mac Studio is 2.0.2). Contract coverage:
  `tests/contract/test-installer-runtimes.sh` asserts both documented roots receive the
  install and the referrers ledger covers both; `test-issue-123-shared-refs.py` T-a1/T-a2
  assert the dual-root refer semantics and T-b1 asserts the kimi-specific root is a #105
  scan root.

- **`docs/api.md` install-local runtime table reflects the kimi-cli dual root (Issue #161).**
  The `--runtime` destination list now maps `kimi-cli` to both `$HOME/.agents/skills` (shared
  with `dsh`) and `${KIMI_CODE_HOME:-$HOME/.kimi-code}/skills`, each with its own receipt set,
  and the reference-counting note states that a pre-ledger receipt in the Kimi-specific root
  counts as referenced by `kimi-cli` alone, so a kimi-cli `--uninstall` withdraws its
  reference from both roots (the shared root keeps its Skills for `dsh`). Documentation only;
  installer behavior is the #159 change above.

## 0.6.1 — 2026-09-24 (codex pin refresh, Skill prompt trim, dsh refusal wording)

- **Pink harness-compat 2026-09-24 class 2: Codex pins 0.156.1 / codex-acp 1.13.1, zcode-acp
  0.47.x precheck, batched CLI records (Issue #153).** `platforms/codex.yaml` moves to the
  Pink report pins — `acp_command` pins `@openai/codex@0.156.1` +
  `@agentclientprotocol/codex-acp@1.13.1`, `acp_verified_versions` to
  `cli=0.156.1;adapter=1.13.1;protocol=1`, `acp_wrapper_pin` to `1.13.1` — a record-only pin:
  no local CLI was upgraded and no live ACP run backs it. The #145 acp_quirks note that npm
  `@openai/codex@0.156.1` could not be installed on the 2026-09-23 measuring network is
  superseded: the pin now follows the 2026-09-24 Pink class-2 report, and the dated 2026-09-23
  CODEX_PATH measurement (codex-cli 0.156.0 on adapter 1.13.0) stays a dated fact. Hardcoded
  copies of the old pins move with it: `test-runner-v2.py`, `test-issue-22-bypass-all-approvals.py`,
  the `test-acp-contract.py` comment, and the host-entry-matrix codex row (its E2/D3 evidence
  was measured on 1.13.0; the row now names the pinned 1.13.1 with that provenance). The
  zcode-acp 0.47.x precheck (usage_update, compaction busy-window) is recorded in
  `docs/harness-acp-compat-2026-09-24.md`: upstream 0.47.x (through v0.47.10) holds prompts
  during auto-compact and reports the compaction window busy for both auto and manual
  `/compact` so prompts queue instead of erroring, and `usage_update` reports context occupancy
  only — verified from upstream release notes and source, no live run. ZCode
  `acp_verified_versions` stays `cli=0.16.9`: the generated zcode ACP reference sits at 8179 of
  its 8192-byte budget, so the platform record keeps its 2026-09-22 phrasing and the precheck
  conclusion lives in the evidence doc. Same-commit optional records, none separately
  verified: kimi-cli `cli=2.1.0`, opencode `cli=2.0.15` (its steering summary now names 2.0.15
  as the un-probed record while keeping the 2.0.11 initialize observation), claude-code
  `cli=2.1.280`, droid `cli=0.225.1` (live `droid --version` on the dev machine). Dated
  measurements and the fixtures that model them keep the versions they were measured on. No
  release was cut and `~/.dsh` is untouched.

- **Skill prompts: accuracy fixes, budget relief, and evidence moved to docs (Issues #156, #157).**
  The Project Runner, Kaola-Delegator, and ten worker Skills land the #156 review. Accuracy: every
  platform with a `host_skill_entry` is an event-driven Host, and Codex's own timer serves only a
  non-Host Codex supervisor (main Skill and heartbeat skeleton). Any `install-local.sh --runtime`
  or `--skills-dir` installs the main Skill. The binding derives from `KAOLA_ACP_DISPATCHER`
  (`heartbeat-host-conflict` on a differing explicit target). The event `reason` formats and the
  Host example name (`zcode-KT-orchestrator-main`) are corrected. Worker Skills now state the
  `permit [--request-id ID] --option OPTION_ID` form (omitting `--option` answers cancelled),
  the default `--permission-mode` per platform (new manifest keys `permission_summary` and
  `login_summary`), and the issue-scoped and canonical-root `SESSION`/`REPO` examples. Every
  `launch_summary` now names the ACP command in place of PTY-era argv. Measurement history moves out of the
  loaded references into `docs/host-entry-evidence.md` (Host entry matrix and ZCode native entry),
  `docs/issue-dispatch-display.md` (consumer progress display), and `docs/zcode-host.md`
  (pre-binding holder recovery). The in-flight bundle-run grandfather clause and the legacy Grok
  Bot Project Runner entry clause are retired. The heartbeat skeleton keeps its intake,
  stop-boundary, and close-out lines, because a non-Host Codex timer carrier is not shown to
  reload the main Skill. No budget ceiling was raised. Loaded prompt bytes drop by about 10.8 KB
  in Project Runner, 0.5 KB in Kaola-Delegator, and 56 KB across the ten workers.

- **Worker Skill prompts: codex measurement narrative leaves the loaded quirks (Issue #157).**
  `platforms/codex.yaml` `acp_quirks` no longer carries the dated measurement narrative; the
  facts stay recorded here: the 2026-09-23 `CODEX_PATH=/opt/homebrew/bin/codex` run (codex-cli
  0.156.0 on codex-acp 1.13.0) applied `gpt-6-sol`/`high` with `high` read back, the `medium`
  discriminator, and `gpt-6-astra`/`high` (0.5.9, Issue #145); the 0.156.1/1.13.1 pins follow the
  2026-09-24 Pink class-2 report as a record-only pin with no local CLI upgrade and no live run on
  1.13.1 (Issue #153, above). The loaded quirk keeps only that the pins are record-only.

- **dsh: an invalid `--permission-mode` refusal names the flag the Agent passed (Issue #158).**
  `kaola-tmux.sh start --platform dsh --permission-mode VALUE` with a value outside the dsh set
  now refuses with `--permission-mode for dsh must be one of read-only, workspace-write,
  danger-full-access or bypassPermissions` instead of naming `kaola-acp.py`'s internal `--mode`
  flag, which the wrapper forwards the Agent's value to. The accepted value set is unchanged; the
  dsh contract test (`test-issue-98-dsh-acp.py`) pins the new wording and the vendored worker
  copies of `kaola-acp.py` are regenerated.

- **Studio ZCode 3.14.3 adapter fitness recorded: no pin or adapter change (Issue #154).** The
  2026-09-24 investigation against the Pink zcode-acp 0.47.x desk targets (compact busy windows,
  `usage_update`, boot-resume handshake) concluded verdict A: ZCode.app 3.14.3 still bundles CLI
  0.16.9, so `acp_verified_versions cli=0.16.9;adapter=kaola-zcode-acp;protocol=1` and the
  reference pin `80aa4e2` stay. The Runner adapter keeps refusing a second prompt during a running
  turn (`prompt-in-progress`) rather than adding a queue layer, and zcode receipts keep
  `context_usage {used: null, size: null}` because the zcode wire carries no occupancy fields.
  Evidence lives in the issue's verdict comment; no behavior changed in this release.
## 0.6.0 — 2026-09-24 (quota packages, ten-platform wording, prerequisite-tolerant validation)

- **Read-only quota catalog queries: `kaola-acp packages` / `model-package` (Issue #148).**
  `kaola-acp packages [--platform P] [--installed-only]` lists every platform's quota packages
  from `platforms/*.yaml` (rows `{id, name, windows, binds_models}`, ids `<platform>:<token>`,
  `windows` null until a release seeds one); `kaola-acp model-package --platform P --model ID`
  resolves the package or answers `status: unmapped` with `packageId: null` — an id the rule
  does not name never gets a guessed package (droid's `billingPool` is read from a live row,
  codex's `absent` default is `primary`, provider-prefix platforms honor `gaps`). Both commands
  start no agent, open no session, create no holder or record, and spend no quota; a usage
  error exits 2. Verified id mappings ship seeded: claude-code `default`/`opus`/`sonnet`/
  `haiku` → `subscription`, `fable` → `scoped-weekly`; cursor-cli `auto` and the live picker's
  advertised wire id `default` → `cursor-models`, `grok-4.7` family and `claude-opus-5-5` family
  → `other-models`; unknown ids → unmapped. Contract: `docs/api.md` §Quota packages and the
  Project Runner `references/quota-packages.md`.

- **ACP quota stamps on observe/status/view receipts (Issue #148).** `observe` and `status`
  stamp model leaves on the emitted receipt copy only — the model `configOptions` entry
  (including one nested group), `session_meta.models.availableModels`, `session_meta
  .availableModels`, and `initial_config_options` — setting `quotaPool` to the qualified id for
  a mapped leaf, or `quotaPool: null` plus `quotaPoolStatus: "unmapped"` for one that is not;
  `view` adds `models.availableModels` and the model `options` from a copy. Stored
  `session_meta` and `record.json` stay the native ACP payload. Live-verified on Mac Studio:
  cursor-cli Auto/`default` stamps `cursor-cli:cursor-models`, and every model leaf across the
  droid and cursor-cli seats carried a stamp or an explicit unmapped marker — zero silent
  blanks.

- **Ten platforms everywhere a user looks (Issues #150, #152).** The main orchestrator Skill,
  its description, `install-local.sh --help`, `kaola-grok-bot-verify.py` prose, and the host
  docs (`docs/codex-host.md`, `docs/zcode-host.md`) now say ten platforms — dsh became the
  tenth in #98; the rendered tree and docs carry no user-visible "nine" count anymore.

- **Version-tolerant contract suite (Issue #151).** `./scripts/validate.sh` no longer fails on a
  machine that lacks a dev-machine prerequisite: the python 3.9 pathlib probe rows
  (`test-issue-51-runner-integration.py`), the tmux rows (`test-zcode-heartbeat-contract.py`),
  and the bash-4 `mapfile`/`BASHPID` watchdog rows (`validate-watchdog.sh`,
  `test-issue-101-validate-watchdog.py`) skip with printed, named receipts when the
  prerequisite is absent and run unchanged where it is present — assertions are not weakened.
  The prerequisites are documented in `README.md` and `AGENTS.md`. Full-suite green on a
  machine missing all three (Mac Studio: exit 0, 7 receipted skips).

- **Studio Codex compaction-hook evidence archived (Issue #149).** The measured outcome — the
  user-level SessionStart(compact) hook does not fire for ACP compaction, so Host recovery
  keeps relying on the turn-opening Skill entry — is recorded in the issue's Studio evidence;
  no behavior changed in this release.

## 0.5.9 — 2026-09-23 (codex Host admission patch release)

- **Codex can be a Project Runner Host (Issue #126).** Codex's measured Host entry is its `$`
  Skill mention, `$kaola-project-runner` (`host_skill_entry` in `platforms/codex.yaml` and the
  `HOST_SKILL_ENTRIES` table). Before this, codex had no entry and was refused as a Host
  (`host-entry-unsupported`, Issue #122). A Host-named codex `start`, a worker a codex Host
  dispatches, and a heartbeat target naming codex are now admitted; the carrier opens with
  `$kaola-project-runner` and names `(Codex CLI Host)`. The entry was measured live on 2026-09-23
  (codex-acp 1.13.0, gpt-6-sol/high, under a shadow `HOME` that held only this build and an
  isolated record root). The entry loaded the Skill with no tool call, and the same question
  without it answered `SKILL-NOT-LOADED`. In the deep test, the handoff turn and the turn woken by
  a worker event both quoted the loaded Skill without reading it. The worker bound to the codex
  Host, the Host exact-stopped it, and the sweep found nothing left. The Issue #122 rule is
  unchanged: any platform without an entry still fails closed. Its tests now use an installed
  copy with codex's entry emptied. The heartbeat skeleton now says every Host (not only ZCode)
  rewrites `.kaola/heartbeat-prompt.json`; Codex's own timer carrier is for a Codex that is not a
  Host. Pass the `$` entry single-quoted or via `--stdin`, because in double quotes a shell expands
  `$kaola`.

- **Codex start no longer fails early on a slow `session/new` (Issue #146).** The holder waited a
  fixed 15 s for the `session/new` answer, and live Codex sometimes answered after ~18 s: the
  start failed with `acp-session-timeout` even though the session would have come up (the late
  answer showed up as `orphan_response`). An optional manifest key, `acp_session_new_timeout`
  (seconds, up to 600), now sets this wait per platform for `start` and the `preflight` probe.
  The client start window (20 s) and the probe bound (60 s) grow by the amount it exceeds 15 s,
  so they keep the margins they had over the default wait. Codex declares `60`. Every other
  platform declares nothing and keeps 15 s / 20 s / 60 s exactly. The holder still reports no
  answer in time as `acp-session-timeout`, and a late answer is still not adopted. No new gate
  or retry was added.

- **Read-only installed-platforms survey: `kaola-acp survey` (Issue #147).** A new host-wide
  command answers which platform CLIs are installed, as one `kaola-acp-survey/1` object with a
  row per platform (`status` `present` | `absent` | `unknown`, `path`, `source`,
  `process_path`, `login_path`) plus the `login_env` fact. Binaries resolve on the invoking PATH
  and in the login environment (one non-interactive `SHELL -l -c` from a fresh minimal
  environment), so a narrow-PATH app subprocess sees login-shell installs such as Codex CLI and
  OpenCode. It starts no agent, opens no ACP session, creates no holder or record, and runs no
  platform binary; `unknown` marks a row the login environment could not settle. ZCode keeps
  its explicit `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` rule. `kaola-acp list` is unchanged.

- **cursor-cli upgrade tier is now Claude Opus 5.5 High (Issue #143).** `--tier upgrade` selects
  `claude-opus-5-5-high` (was `claude-fable-5-1-high`); `acp_model_map` maps it onto the live
  picker base id `claude-opus-5-5`, and `high` is applied through the model's advertised `effort`
  option, as measured live on 2026-09-23 (`effective_model=claude-opus-5-5`,
  `effective_effort=high`, `effort_config_id=effort`). The default tier (`grok-4.7-xhigh`) and
  `acp_verified_versions` are unchanged; Devin's Fable presets are a different platform and are
  untouched.

- **devin tiers are two fusions: upgrade = Opus 5.5 High fusion, fable = Fable 5.1 High fusion
  (Issue #144).** `--tier upgrade` selects `fusion-claude-opus-5-5-high-sidekick-swe-2-medium`
  ("Fusion High (Opus 5.5 High + SWE-2 Medium)", was the Fable fusion) because Devin has no pure
  Opus 5.5 High (pure Opus 5.5 is medium only). `--tier fable` stays declared but now selects
  `fusion-claude-fable-5-1-high-sidekick-swe-2-medium` ("Fusion High (Fable 5.1 High + SWE-2
  Medium)") through `acp_command_alt`; the pure `claude-fable-5-1-high` preset is retired. Both
  ids were spawn-measured on cli 3000.11.1 on 2026-09-23 (ready session, `effective_model` from
  launch argv). The also-measured `fusion-gpt-6-astra-high-sidekick-swe-2-medium` is documented
  only and wired to no tier. The default tier (`swe-2-max`) and `acp_verified_versions` are
  unchanged.
- **codex default tier is now GPT-6 Sol (Issue #142).** `--tier default` selects `gpt-6-sol`
  (was `gpt-5.6-sol`/`high`). The pinned ACP surface applies it through the plain `model` option
  even though the pre-apply catalog omits it (measured live on 2026-09-23: `applied: true`,
  `currentValue gpt-6-sol`, name "6 Sol"). Under `gpt-6-sol` the adapter advertises no effort
  option (`reasoning_effort` is rejected `-32602` for both `high` and `medium`), so the preset
  sends no effort (`no Runner effort override`); an explicit `--effort` stays a limitation
  receipt. The upgrade tier (`gpt-6-astra`/`high`), `acp_verified_versions`, and the npx pins are
  unchanged. The no-effort finding held only for the old 1.11.0 adapter; the Issue #145 correction
  below supersedes it.
- **codex default tier is GPT-6 Sol High on codex-acp 1.13.0 (Issue #145, Owner correction of
  #142).** `--tier default` now selects `gpt-6-sol` with `effort=high`. The #142 no-effort result
  was specific to the old pinned surface: codex-acp derives effort options from the selected
  model, and the 1.11.0 bundled codex 0.153.4 catalog did not know `gpt-6-sol`. Measured live on
  2026-09-23 without a turn: on `npx @openai/codex@0.155.1` + `@agentclientprotocol/codex-acp@1.13.0`
  the model option lists `gpt-6-sol` before any apply and, under it, `reasoning_effort` offers
  `low`/`medium`/`high`/`xhigh`/`max`/`ultra`; `high` applies (`effective_model=gpt-6-sol`,
  `effective_effort=high`, `effort_config_id=reasoning_effort`), and a `medium` probe read back
  `medium`, proving the set is applied, not a config default. The upgrade tier
  (`gpt-6-astra`/`high`) applies on the same surface. `acp_command` moves to those pins,
  `acp_verified_versions` to `cli=0.155.1;adapter=1.13.0;protocol=1`, and `acp_wrapper_pin` to
  `1.13.0`; the adapter still advertises `_meta.steering.supported=true` (source check; live
  steering was measured on 1.11.0). A `CODEX_PATH` override was also live-measured on adapter
  1.13.0 (Owner ruling, 2026-09-23): `CODEX_PATH=/opt/homebrew/bin/codex` (codex-cli 0.156.0, the live
  Homebrew binary) applies `gpt-6-sol`/`high` (effective read-back `high`), the `medium` discriminator,
  and `gpt-6-astra`/`high` for the upgrade tier. The pinned npx default stays `@openai/codex@0.155.1`:
  npm `@openai/codex@0.156.1` could not be installed through the measuring network (two bounded
  attempts stalled), so no portable 0.156.1 pin is claimed. Codex Host entry and Host model pin stay
  with #126.

## 0.5.8 — 2026-09-23 (latest-CLI tier landing release)

- **devin tier presets land again on Devin CLI 3000.11.1 via spawn argv (Issue #140).** The 11.1
  ACP `model` option offers only 76 catalog values and rejects every preset with `-32602`, so the
  session silently ran `swe-2-high`. `platforms/devin.yaml` now declares per-tier
  `acp_command_default`/`_upgrade`/`_alt` (`devin acp --model <preset id>`); the presets themselves
  are unchanged (`swe-2-max`, `fusion-claude-fable-5-1-high-sidekick-swe-2-medium`,
  `claude-fable-5-1-high`) and `acp_verified_versions` moves to `cli=3000.11.1`. `kaola-acp.py`
  picks the spawn command as `--command` > `KAOLA_ACP_COMMAND` > the tier command > `acp_command`,
  the tier command only when the tier preset selects the model (an explicit `--model` or a
  preserved resume keeps the base). A model the spawn argv already carries is not re-sent as an
  option: `config_application.model.applied_via: argv`, and `effective_selection` reports it with
  `effective_model_source: launch-argv` beside the agent's stale `advertised_model`. The keys are
  optional in `render-skills.py`; the other nine platforms are unchanged.

- **Sticky-cwd Host brick: prevention and recovery procedure (Issue #137).** Project Runner's
  `workflow-worktree.md` tells a Host never to `cd` into paths Workflow finalize or sink move or
  remove (`.kw/worktrees/`, `kaola-workflow/issue-N/`) — use absolute paths, `git -C`, or a
  subshell, and return to the project root before finalize or sink; subagents follow the same
  rule, and a bricked Host reports `brick` and stops. A new Delegator reference
  `host-brick.md` gives the outer Agent the recovery: exact-stop that Host, start a new
  standard-named Host at the project root, and continue from existing project records; no
  in-Skill resume until one is proven live.

- **Grok Bot pin hygiene: one pin per machine, superseded pins refused (Issue #138).** The
  locator's registration receipt is the machine's one pin. `kaola-project-runner-locate
  --expect-revision E` where E is a proper ancestor of the registered accepted revision adds
  `expect-revision-superseded` beside `revision-mismatch`; `register` refuses such an E as
  `accepted-revision-superseded` before touching the link or receipt, so a remembered stale
  revision can no longer roll a machine back. Rollback stays an owner act: remove the receipt,
  then `register`. The bridge step 2 now says `<accepted>` is the Skill's own line, never a
  memory, and the Delegator's Grok Bot co-location attestation no longer passes
  `--expect-revision` (the receipt's `registration-stale` already binds HEAD to the machine's
  pin), so no commit pin travels into the Delegator or Host.

- **cursor-cli default tier lands Grok 4.7 Extra High again on Cursor CLI ≥ 2026.09.18 (Issue #135).**
  Cursor's effort option id follows the selected model (`reasoning_effort` for Grok 4.7, `effort`
  for Claude Fable 5.1), so `acp_effort_config_id` is now an ordered `;` candidate list
  (`reasoning_effort;effort`) resolved against the options the agent advertises after the model
  apply; with none advertised the first is sent literally. Receipts add
  `config_application.effort.candidates`/`advertised` and `effective_selection.effort_config_id`.
  `acp_verified_versions` records `cli=2026.09.18-9a7762b`.

## 0.5.7 — 2026-09-22

- **One live Host per repo, and a repo sweep on every Delegator reach-out (Issue #132).** A
  Host-named `start` now refuses `host-exists` (exit 1, nothing created) while another Host-named
  holder of the same canonical root may be live. Live means the identity check: record present,
  holder PID alive, admin socket answering, and the socket's `holder_instance_id` equal to the
  record's. A silent holder whose argv still names its record (initializing or wedged) also holds
  the root until it is exact-stopped. A PID alone is no longer treated as liveness. `session-exists` requires that check (or a PID whose argv still
  names the record); a reused PID is replaced without a signal. `stop --force` signals a
  live-but-unreachable holder only when its argv anchors it to the record; for a reused PID it sweeps
  only the dead holder's identity-checked groups and then retires the record. A holder started
  under another spelling of the record root is found through the socket its own argv names and
  stopped over it, never signalled. Holders now record `agent_started`, and a dead holder's agent
  group is swept only while its live leader still has that start time. A dead holder's force stop marks the record `stopped` once nothing is left.
  `kaola-acp-list/1` rows add `identity`, `host_class`, `dispatcher`, and the `heartbeat_host`
  binding, and `--include-dead` opts into dead records; the default view is unchanged. The
  Delegator's One Host rule and handoff now spell out attach-or-exact-stop-and-prove-gone before any
  start and carry a `sweep=` line in every prompt; the Host's `host-startup.md` gains the repo
  sweep table (keep / stop / report). New checks live in `test-acp-contract.py` and
  `test-issue-74-kaola-delegator.py`.

- **Breaking: the PTY transport is retired; the Runner is ACP-only (Issue #130, owner ruling
  2026-09-22).** Any command given `--transport pty` is now refused from its arguments alone,
  before the manifest, Git, the canonical-root binding (#73) or the dispatcher checks (#104) are
  read, and nothing is created (no process, holder, record or session). The refusal is one JSON
  line, exit 1: `reason: transport-pty-retired`, `mutation_performed: false`, `mutation_status:
  not_started`, `transport: {"requested":"pty","supported":["acp"]}`, and a `detail` that says to
  re-run without `--transport` (or with `--transport acp`). `--transport acp` is still accepted and
  does nothing; any other value exits 1 with `--transport must be acp`.
  - Receipts: the `transport` block is now exactly `{"selected":"acp"}`, plus the ACP probe fields
    a command already added. The `default`, `alternatives` and `reason` keys are gone.
    `schema_version` stays 3, so a consumer that reads `transport.selected` is unaffected.
  - Manifests: the `default_transport` key is removed. The renderer now rejects it as an
    unexpected key, so `render-skills.py --check` fails closed if it comes back.
    `acp_login_requires_pty` keeps its name; the Skill text now says login is a human act in a
    native terminal, outside the Runner.
  - Retired reasons: `heartbeat-host-pty-unsupported` (#104) and `steer-unsupported-transport`
    (#65) are replaced by `transport-pty-retired`. The ACP start's tmux name-collision probe and its
    `transport-mismatch` error are removed.
  - Removed files: `scripts/kaola-observation.py`, `kaola-pane-relay.py`, `kaola-relay-client.py`,
    `kaola-relay-protocol.py`, `templates/references/transport.md.tmpl`, and the tmux/relay branch
    of `kaola-tmux.sh`. Worker Skills no longer ship `references/transport.md` or those four
    scripts. `kaola-tmux.sh` and `runtime-tmux.sh` keep their names, and `scripts/adapters/*.sh`
    still supply the `preflight` base facts. The 25 PTY-only test suites and their fixtures are
    deleted, and the third `validate.sh` lane (`test-model-policy.sh`) is removed.
  - Lost capabilities, with no Runner replacement: Codex OS-level read-only, which existed only on
    PTY (ACP `read-only` is upstream on-request approval, not an OS sandbox); OpenCode skip-all
    (PTY `--auto`), so on ACP `permit` settles each request; native keys, menus and editor
    replacement (`answer --replace-editor`), with only `key escape` left as ACP cancel; and the
    ZCode PTY "diagnostic entry", which never opened a session anyway. To watch a session, use
    `kaola-acp list`, `view` or `follow`.
  - Model evidence: `status`/`observe` no longer carry request provenance
    (`requested_model_source`, `model_selection`, `resolved_*`), which is now only on the
    `start`/`preflight` receipt; `status` keeps the agent's own
    `session_meta.configOptions[].currentValue`. `actual_runtime_model_id` and `actual_parameters`
    are always `null` and `model_verified` is always `unknown`
    (`actual-model-evidence-not-yet-read`), so the actual selection is `effective_selection` on
    `start`. The PTY launch carriers (Codex `-c service_tier`, Cursor `-fast` picker variants,
    OpenCode `OPENCODE_CONFIG_CONTENT`) are gone and ACP
    config options carry the selection. The Issue #8 guarantees (hostile id verbatim and never
    executed, unavailable model verbatim and not a gate, user override, mismatch as evidence,
    `unknown` when unreadable) are now asserted over ACP in `test-issue-130-pty-retired.py`
    (`ModelPolicyOnAcp`), replacing the deleted `test-model-policy.sh`.
  - Migration: stop every existing PTY session **with the old build before upgrading**, or end it
    with `tmux kill-session`. After the upgrade, `stop --transport pty` is refused like every other
    PTY request and touches nothing. After merging, re-run `./scripts/render-skills.py --write &&
    ./scripts/install-local.sh` on every install root, because Host start refuses worker and
    main-Skill build skew (#105/#121).
  - Scope: this does not reopen or revise #128. It removes the lane and fakes #128 added by
    deleting what they tested, which follows from the policy. The #128 entry below describes the
    gate as it was when #128 merged.
- **The Host reads the Workflow mission ledger instead of a Mission List (Issue #133).** Issue
  progress now comes from `<canonical-root>/kaola-workflow/.ledger/issue-<N>.jsonl`: one JSON
  line per mission with keys `n`, `name`, `details`, `status` (`todo | in-flight | done | failed |
  blocked`). The run's Workflow Main Orchestrator is the only writer; the Host reads the
  `{n,status}` projection read-only and reports `done` lines over total. An absent file is
  `unknown`. An all-terminal (`done`/`failed`) ledger that is still present means finalize is in
  progress while the forge issue is OPEN, and a forgotten archive (stuck; reported with its owner)
  once the issue is CLOSED or the run is already archived. The Markdown Mission List is retired on the Runner side with no fallback reader, and
  every template, rendered Skill, and test fixture that kept one now names the ledger. This
  repository ignores `kaola-workflow/.ledger/`. The contract matches Kaola-Workflow#1089, which
  owns the writer side. New suite `test-issue-133-mission-ledger.py`.

- **`validate.sh` now runs the model-policy and lifecycle contract suites (Issue #128).** Both
  suites were outside the gate and had gone red on main without anyone noticing. Every failure was
  a stale fixture; no product behavior changed. The lifecycle inventory now lists the
  `references/steering.md` reference (added in #65) and its template, and its roster now includes
  the `dsh` worker it had never covered. The model-policy fixtures now use the #111 Kimi default
  (`Kimi K3 Max`, `kimi-code/k3`). The OpenCode fake now reads the caller model from
  `OPENCODE_CONFIG_CONTENT`, the channel the V2 adapter uses (#112), and a new check requires that
  channel and forbids `--model`/`--variant` in argv. The Droid fake no longer splits a
  settings model that contains spaces. `test-lifecycle-contract.py` joins the first Python lane.
  `test-model-policy.sh` (~300 s, tmux-driven) runs as a third concurrent lane, and the lane
  runner now picks `bash` for `.sh` suites.

- **Recorded CLI versions follow the 2026-09-22 harness-compat check (Issue #129).** ZCode
  `acp_verified_versions` is now `cli=0.16.9`. The installed ZCode.app 3.14.1 bundles that CLI.
  ZCode `acp_quirks` also names upstream `william0wang/zcode-acp` v0.46.6 (turnId and
  permissions) as the newer protocol reference. The adapter still follows the `80aa4e2` pin. The
  record now says to check the actual CLI version before the next live run. Claude Code moves to
  `cli=2.1.278` and Droid to `cli=0.223.0`. These values are records only. None of them comes
  from a live ACP run, and no local CLI was upgraded. At start the Runner still reports the
  launched `--version` next to the record without gating on it. Dated measurements and the
  fixtures that model them keep the versions they were measured on (ZCode 0.16.5, Claude 2.1.272,
  Droid 0.220.0).

- **Grok 4.7 is the default for the `grok` and `cursor-cli` workers (Issue #127).** Both CLIs now
  offer Grok 4.7. `grok` default and upgrade are `grok-4.7` (Grok 4.7 Extra High) on Grok CLI 1.0.40.
  The Cursor 4.7 picker IDs lost the old `cursor-` prefix, so the `cursor-cli` default is
  `grok-4.7-xhigh` (Fast off), not `cursor-grok-4.7-xhigh`. `acp_model_map` maps
  `grok-4.7-xhigh` and `grok-4.7-xhigh-fast` to the ACP model value `grok-4.7`. The Cursor TUI
  footer is now `Grok 4.7 256K Extra High` (no `Cursor` prefix, a context token). The model-policy
  parser reads that form and reports `grok-4.7-{effort}[-fast]`. It also recognizes the footer
  when the `Cursor Agent` header has scrolled away. Cursor `acp_verified_versions` is now
  `cli=2026.09.15-d2fe57e`. Dated live-smoke records, decisions, released entries and the raw
  2026.08.25 Cursor frame fixture keep their 4.6 facts.

- **dsh starts with full access by default, so a dsh worker can run inside a dsh Host (Issue
  #120, Host ruling).** dsh advertises no ACP mode option. Its permission mode is the launch
  variable `DSH_PERMISSION_MODE`, and dsh's own default `workspace-write` runs the shell tool
  under Seatbelt. A dsh `start` now launches with `DSH_PERMISSION_MODE=danger-full-access` (no
  sandbox, approval `never`), the same full-access default as every other platform's measured
  bypass. A caller's own `DSH_PERMISSION_MODE` or `--mode` wins: `read-only`, `workspace-write`
  and `danger-full-access` are accepted, `bypassPermissions` maps to `danger-full-access`, and
  any other value is refused before anything spawns. `--mode` on dsh therefore no longer errors
  `config-option-unavailable`. The start receipt's `config_application.mode` records `applied_via:
  env`, the value and its `source` (`runner-default`, `caller-env` or `caller-mode`). The
  manifest and README no longer claim that outside-workspace writes "run unattended with no
  approval gate to skip". The #98 probe behind that claim wrote to `/tmp`, which is inside the
  sandbox's writable set.

- **A Runner started from inside a macOS Seatbelt sandbox reports why start failed and can still
  stop (Issue #120).** A dsh Host runs its shell tool under Seatbelt (`DSH_PERMISSION_MODE` default
  `workspace-write`), and every holder and agent started from that shell inherits it. A nested
  `dsh --profile acp` then dies at boot with `EPERM` rewriting `$DSH_HOME/profiles/acp/cordis.yml`,
  and the #119 receipt said only `acp-initialize-failed` / `agent-exited`. A failed ACP start now
  adds the agent's `stderr_tail` and `seatbelt_confined` (`true` / `false`, `null` off macOS) to
  `error`. The setuid `/bin/ps` cannot run under Seatbelt at all, so the holder's `stop` crashed
  (`holder-closed`) and left the worker running. When `ps` cannot run, the holder and CLI now read
  the same process columns from libproc; stop then reports `stopped: true` and the real
  `residual_pids`. Nothing changes when `ps` runs.

- **A stale main Skill in a Host's discovery roots is refused at Host start (Issue #121).** The
  #105 build-skew check compared only worker Skills, so an older `kaola-project-runner` main Skill
  in a user root (seen on cursor-cli) was loaded instead of the Host's build without any report.
  Every worker Skill now carries the main Skill's build record, `scripts/main-skill-build.json`,
  and a Host `start` that passes the worker check compares every Skill directory named
  `kaola-project-runner` in its `SKILL.md` frontmatter (renamed backups included) in the same
  roots. A difference is the typed refusal `reason: main-skill-build-skew` (exit 1, nothing
  created): `main_skill_skew` and `detail` name each stale path with its installed and expected
  build. The Runner never rewrites a user root; reinstall that root or remove the copy. A passing
  Host `start` reports `main_skill_build`.
- **Runtimes install and uninstall independently: shared blocks are counted by reference
  (Issue #123).** `kimi-cli` and `dsh` still share `~/.agents/skills`. Each Skill receipt now
  lists its `referrers`, and `--method link` writes a receipt too. Installing a build that is
  already in place only records a reference (`refer:`). A different build updates the one shared
  copy and keeps every referrer, so the #105 build check stays aligned across roots; its scan
  scope is unchanged. `--uninstall` withdraws only this runtime's reference and keeps the Skill
  (`kept:`) while another runtime still uses it. Receipts written before this change count as
  used by every runtime mapped to that root. The three `~/.local/bin` links (`kaola-acp`,
  `kaola-acp-holder`, `kaola-project-runner-locate`) share one sidecar ledger,
  `.kaola-project-runner-bin-links.json`. A default `--runtime codex` install now references an
  existing link that points to a usable executable (for example, one from an accepted checkout)
  instead of aborting the whole install with `refusing to replace existing symlink`; a dangling
  link is still refused. `--uninstall --bin-links` keeps a link while another runtime or checkout
  refers to it. It keeps the locator link while the Grok Bot registration receipt exists, and the
  installer never writes that receipt. Uninstall no longer exits nonzero on a link another checkout
  made. The main Skill's ordinary-worker example now uses a `<skills root>` placeholder instead
  of `~/.zcode/skills`.
- **An entry-less platform cannot be a Host (Issue #122, owner ruling: fail closed).** A platform
  whose `host_skill_entry` is empty (today codex) is refused in every Host role with the typed
  receipt `reason: host-entry-unsupported` (`detail` names the platform and the empty entry,
  `mutation_performed: false`, exit 1) before any record, socket, or holder exists: a Host-named
  `start` on it, a worker `start` it dispatches (`heartbeat_host_source: dispatcher-no-carrier`,
  previously an unbound start), and a start whose `KAOLA_ACP_HEARTBEAT_HOST` names it (previously a
  usage error). No plain-text first-line fallback exists. The holder's `worker_event` refusal stays
  as depth, and codex as an ordinary worker is unchanged. Admission is measuring the entry and
  filling the manifest.
- **Droid Core is the third tier, not the upgrade (Issue #125, correcting #117).** #117 put Kimi
  K3 Max into Droid's `upgrade_*` slot, but Droid Core is a separate tier below the default, not a
  stronger one. Kimi K3 Max (`kimi-k3` at `reasoning_effort=max`) moves to `alt_*` as
  `--tier core` (`alt_tier_label: core`). `--tier upgrade` now resolves to the
  same Auto preset as `default` (no stronger Droid tier is established; the Kimi CLI precedent
  allows upgrade to equal the default). The default stays `auto`, and the deleted alternative /
  `kimi-k2.7-code` tier is not restored.
- **Grok sessions record the CLI build they actually ran (Issue #124).** Grok's `initialize`
  returns no `agentInfo`, so a grok ACP `start` now stores the launched binary's `--version`
  line as `cli_version` (`path`, `version`, `verified_versions`) in `record.json`, holder state,
  and the start receipt's `transport`. It is recorded, never enforced: a mismatch still starts.
  A live ACP smoke on grok 1.0.40 (start/send/read/cancel/stop: `end_turn`, `cancelled`, exit 0,
  no residual pids; steering entries still `-32601`) moves `acp_verified_versions` and the
  steering summary from cli 1.0.25 to 1.0.40.
- **Non-ZCode ACP runtimes can host Project Runner (Issue #119).** Every platform manifest gains
  `host_skill_entry`: the measured first line that opens each Host turn. It is filled only from
  live trigger evidence in a fresh ACP session, plus a negative control.
  `/kaola-project-runner` is measured for zcode, claude-code, cursor-cli, grok, devin, droid, dsh
  and opencode; kimi-cli uses `/skill:kaola-project-runner ` (the trailing space ends Kimi's
  command name). Codex stays empty because its turns were blocked by an account usage limit. The
  heartbeat carrier opens with the Host's own entry and names `(<runtime_name> Host)`; the ZCode
  carrier is byte-identical to before. A worker dispatched by any Host with an entry binds to it
  (#104), and an entry-less dispatcher still starts unbound. Carrier-target validation, the
  holder's `worker_event` op, and #105's build-skew check follow the entry. For a Host-named
  start on those platforms, #105 compares that platform's measured Skill roots. A Host start
  resolves model/tier exactly like a worker start; the only Host model constants are still the
  ZCode ones. Every ACP `start` receipt reports the agent's own `effective_selection`. On
  opencode, an explicit `--model`/`--effort` the agent does not report is refused
  (`explicit-selection-unverified`) and the session is stopped. Measured on OpenCode 2.0.11, the
  ACP default resolves the configured `opencode-go/deepseek-v4.1-flash` under provider `opencode`
  (`provider.no-route`) and does not inherit the TUI's `max` effort. The explicit
  `--model opencode-go/deepseek-v4.1-flash --effort max` works. The installer gains
  `--runtime grok-cli|droid|opencode|kimi-cli|dsh`, each installing to a measured root.
  `--runtime grok` is still refused and now points to `grok-cli`. New reference
  `host-entry-matrix.md` and new suite `tests/contract/test-issue-119-host-entry.py`. The
  #33/#74/#90/#94 heartbeat tests now pin the per-platform entry instead of ZCode-only.

- **Not in this release: Codex as a Host (Issue #126, open).** `platforms/codex.yaml` keeps
  `host_skill_entry: ""`, so a Codex Host start still fails closed (#122). Codex remains a worker
  and a consuming runtime; measuring its Host entry is left to #126.

## 0.5.6 — 2026-09-21

- **The authorized worker count is a hard cap on live processes; a finished seat is stopped, not
  kept (Issue #118).** Finished seats stayed alive after acceptance and the Host read them as
  idle capacity, exceeding the authorized count and chaining later tasks into stale contexts.
  The Project Runner main Skill, heartbeat skeleton, ZCode Host dispatch and issue dispatch
  references now say: the count bounds live worker processes, ACP holders included, until each
  `stop` receipt; at the cap, stop one seat before starting any new one (stop-before-start); the
  only legal idle seat is a delivery awaiting acceptance, and the Host exact-stops it in the beat
  acceptance finishes or the seat is abandoned (a rejected delivery's repair stays the same
  assignment); a new or different task gets a new session, with `--resume`/`--continue` only for
  recovering the same assignment; each beat reports `live N / authorized M` per platform and the
  seats stopped. No quota system, ledger, or scheduler is added — the cap is the authorized count,
  read from existing receipts. Kaola-Delegator and `host-startup.md` are unchanged. New suite
  `tests/contract/test-issue-118-seat-cap.py`; `test-issue-41-orchestrator.py` no longer requires
  "leave capacity idle" and now requires stop-before-start.

- **The preflight receipt carries the adapter's base fields again (Issue #114).** Every platform
  defaults to the `acp` transport, so `kaola-tmux.sh PLATFORM preflight` handed off to
  `kaola-acp.py` before the adapter's preflight ever ran, and the receipt held only the ACP and
  model-policy fields — `result`, `runtime`, `runtime_version`, `runtime_binary` and `detail` never
  appeared (including #112's OpenCode `loopback=direct|excluded|ensured`). The `--transport pty`
  path was never affected. The acp preflight now also runs the adapter's preflight and adds those
  fields to the ACP receipt, which keeps precedence on any shared key; `result` is `ready`, or
  `error` when the ACP receipt carries an `error`. A missing native binary is reported as
  `runtime_version: unknown` with a `detail` naming the override variable — evidence, not a gate.

- **Droid presets corrected: default is Auto again, Kimi K3 Max is the upgrade, and the alternative
  tier is gone (Issue #117).** #111 pinned Droid's default to Kimi K3 Max, mirrored the same pair
  into `upgrade`, and added a `kimi-k2.7-code` alternative tier. The default is back to the
  first-class catalog id `auto` (Auto Model) with no effort pin — PTY writes it into the
  process-scoped `--settings` overlay and ACP applies `model=auto` explicitly, because the native
  currentValue is not `auto`. `--tier upgrade` is now the distinct Kimi K3 Max slot (`kimi-k3` at
  `reasoning_effort=max`). Droid declares no third tier, so `--tier alternative` is the typed
  `tier-not-declared` refusal on both transports instead of selecting `kimi-k2.7-code`.

- **`./scripts/validate.sh` is hermetic against a dispatching Host's environment (Issue #115).** A
  worker seat a live ZCode Host dispatched inherits the Host's binding variables
  (`KAOLA_ACP_HEARTBEAT_HOST`, `KAOLA_ACP_HEARTBEAT_HOST_SOCKET`, `KAOLA_ACP_DISPATCHER`,
  `KAOLA_ZCODE_ENTRY`, `KAOLA_ZCODE_NODE`, `KAOLA_CLAUDE_PROFILE_REQUIRED`), and fixture starts that
  copy the environment then bound to the real Host, failing `test-issue-73-canonical-root.py`
  (`heartbeat-host-conflict`) and `test-zcode-acp-contract.py` as if the product had regressed.
  validate.sh now drops every inherited `KAOLA_*` name before any suite runs — except its own
  `KAOLA_VALIDATE_*` knobs — and prints the removed names on one
  `validate: scrubbed inherited env: ...` line (`none` when clean). Suites keep setting the
  `KAOLA_*` fixtures they need themselves; seats no longer strip names by hand.
- **ZCode adapter also reads `stopReason` / `stop_reason` as an output-limit finish reason (Issue
  #116).** The key-scoped scan behind the #113 `max_tokens` terminal knew only `finishReason`,
  `finish_reason`, `rawFinishReason` and `raw_finish_reason`. ZCode's internal ModelComplete event
  already names its field `stopReason`, so a build that projects it onto `turn.completed` would have
  reported an output-token stop as `end_turn` and made it uncountable again. The gap is latent — the
  strict `turn.completed` wire schema carries no finish reason today and `turn.failed` remains the
  observed carrier — and matching stays key-scoped: prose that merely quotes `max_tokens` is still
  `end_turn`, and an explicit cancel still reports `cancelled`.


- **OpenCode adapter upgraded to OpenCode V2 `2.0.11` (Issue #112).** The local CLI moved to the V2
  line, which rejects the V1 launch outright: `opencode <repo> --mini --auto` now answers
  `Unrecognized flag: --mini in command opencode`, and top-level `--model` and `--variant` are gone
  the same way. The PTY launch becomes **`opencode <repo> --auto`** — `--auto` survives as a
  top-level V2 flag, so the documented PTY bypass is intact — while an explicit caller model no
  longer rides argv. `mini` is a subcommand on V2 and cannot carry this launch: it accepts neither a
  directory nor `--auto`.

  The reported hard blocker — every ACP session method answering
  `-32603 ... {"errorName":"ClientError"}` while `initialize` succeeded — turned out **not** to be an
  authentication fault. Its cause is a forward proxy with no loopback exclusion: V2 reaches its own
  server over loopback HTTP, and with `HTTP_PROXY` set and `NO_PROXY` unset that hop was handed to
  the proxy. Excluding loopback alone turns `ClientError` into a live session, and also restores
  `opencode service status`, `models` and `auth list`, which means the separately reported "wedged
  managed service" was never wedged. Upstream fixed this class on the V1 line
  (`anomalyco/opencode#31096`) but the V2 ACP adapter was copied rather than ported (#35457, open),
  so it regressed. When a forward proxy (`HTTP_PROXY`/`HTTPS_PROXY`, either case) is set, the
  Runner now appends any missing `127.0.0.1`/`localhost` to `NO_PROXY`/`no_proxy` **in the opencode
  child's environment only**: the ACP child through `kaola-acp.py` `agent_environment()`, and the
  PTY child through the adapter's `-e` channel. The PTY path needs it too, because a tmux server the
  Runner starts from a proxied shell inherits the proxy, and the V2 TUI was measured hanging at
  "Starting background server...". Operator entries are extended in place and never removed or
  reordered, `*` counts as already excluded, nothing changes without a forward proxy, and the
  Runner's own environment is never modified. `adapter_preflight` reports
  `loopback=direct|excluded|ensured` for what the child actually sees, and `acp_env_allowlist` gains
  `NO_PROXY`. No classifier, retry or waiting layer was added.

  With the transport unblocked, the facts that were previously unverifiable are now measured on
  2.0.11 rather than inherited from 1.18.x. A full `initialize → session/new → session/prompt →
  session/close` round trip passes, so `acp_verified_versions` becomes `cli=2.0.11;protocol=1`.
  **There is still no ACP skip-all**, and that is now a measurement: `session/request_permission`
  offers exactly `allow_once`, `allow_always` and `reject_once`, and `session/new` advertises only
  the `model`/`effort`/`mode` config options. `acp_model_config_id` and `acp_effort_config_id` keep
  their values — `effort` is live on V2 with `low/high/max/default` — so the per-model `variants`
  array is a catalog shape, not a replacement for the flat config id. `OPENCODE_CONFIG_CONTENT` is
  written in the V2 shape the official migration guide documents (`agents.build.model` with the
  variant folded in after `#`) and is recorded as ignored by 2.0.11 itself (upstream #50236, which
  names this exact version). Finally, the V2 TUI footer reads `ctrl+p commands` where 1.18.x read
  `ctrl+p cmd`; since `cmd` is not a substring of `commands`, TUI detection and the activity hint had
  both silently stopped matching, and both are fixed and re-verified against a live pane.

- **Five platforms' model presets re-pointed at live-verified ids (Issue #111).** Every id below
  was read from the live ACP catalog on 2026-09-21 (`initialize` → `session/new` → `configOptions`,
  read-only, session closed immediately); no user configuration was written. Kimi CLI's default
  becomes **Kimi K3 Max** (`kimi-code/k3` at `thinking=max`) — a composition, since the catalog
  carries no "Max" in any display name — and the previous default `kimi-code/kimi-for-coding`
  ("K2.8 Preview") moves to the new alternative tier. Droid's default becomes the same
  composition through its own first-class catalog id, `kimi-k3` at `reasoning_effort=max`, so
  `acp_model_map` stays empty and nothing is hardcoded; its alternative tier is `kimi-k2.7-code`,
  the nearest Kimi-family analogue because Droid's 51-model catalog carries no K2.8 at all. dsh
  becomes a model-selecting platform for the first time, defaulting to
  `opencode-go/deepseek-v4.1-flash` — note that "DeepSeek V4.1 Flash (OpenCode Go)" is a
  Runner-side display name and the catalog's own is the bare lowercase `deepseek-v4.1-flash`, and
  that the similarly spelled `deepseek-official/deepseek-flash` (displayed "DeepSeek-V41-Flash")
  is a different route. ZCode's `default_model_*` is pinned to **GLM-5.3 at `thought=max`**,
  generalising the Issue #108 Host gate to the ordinary preset path so a plain worker start lands
  on the same pair; a test asserts the manifest equals `ZCODE_HOST_MODEL_ID`/`ZCODE_HOST_EFFORT`
  so the two do not become separate sources of truth. Devin gains a third preset without losing
  either existing one. Both transports are re-pointed together: `platforms/*.yaml` feeds the ACP
  path and `scripts/adapters/*.sh` feeds the PTY path, and a new test makes them agree.

- **A third, optional model preset per platform (Issue #111).** `--tier` was a closed two-value
  vocabulary. A platform may now declare one further preset under **its own word** —
  `alt_tier_label` plus `alt_model_name`/`alt_model_id`/`alt_model_parameters`/`alt_model_effort`
  in the manifest — so Kimi CLI and Droid offer `--tier alternative` and Devin offers
  `--tier fable`, while the other seven platforms declare none and show no trace of the slot in
  their generated Skills. The slot is all-or-nothing: a label without a model, a model without a
  label, or a label shadowing `default`/`upgrade` is a render-time error. Because the template
  engine has no conditional syntax, the prose renders through computed `TIER_BLOCK` and
  `ALT_TIER_LINE` blocks (the established `steering_block()` pattern) rather than an
  unconditional template sentence, with the detail spent in `references/platform.md` where there
  is room — an unconditional `SKILL.md` sentence would have overflowed `worker_skill_bytes` on
  cursor-cli first. **Asking a platform for a tier it does not declare is a typed refusal**
  (`{"result": "refused", "reason": "tier-not-declared"}`, exit 1, `available_tiers` named,
  nothing spawned or written) on the ACP path and a named `die` on the PTY path — never a silent
  fallback to `default`. Two latent defects surfaced and were fixed with it: `kaola-model-policy.py`
  rejected a `runner-<tier>` selection source with an argparse usage error because the vocabulary
  was a closed four-value list, and the shell's refusal message doubled the tier label.

- **ZCode output-token-limit stops are now visible as ACP `max_tokens` (Issue #113).** When a
  ZCode turn ends on its output ceiling, the app auto-continues three times and then fails the
  turn with `model_output_limit_exceeded`. The adapter used to collapse that terminal into
  `refusal` (or `end_turn`), so the stop appeared in no Runner receipt and could only be found in
  ZCode's own database. The adapter now reports **ACP `stopReason: "max_tokens"`** for a
  `turn.failed` carrying `model_output_limit_exceeded` (as `error.code` or
  `error.attribution.providerErrorCode`), and for a finish reason of `length` or the raw
  `max_tokens` / `max_output_tokens` / `model_context_window_exceeded`. An explicit cancel still
  reports `cancelled`, and ordinary failures and completions keep `refusal` and `end_turn`. The
  holder records the reason verbatim: in the turn receipt, in `record.json`
  `last_prompt.stop_reason`, and in a new `events.jsonl` `turn_ended` line
  (`outcome`, `stop_reason`, `prompt_fingerprint`) written at every turn end, so a stop that a
  later prompt supersedes still leaves a trace. A contract-test gate against the fake ZCode
  app-server pins the translation, with negative controls, and fails on the previous adapter.
  This is observability only: no model, effort or output-ceiling setting changed.

## 0.5.4 — 2026-09-20

- **An unreadable ZCode discovery root is a typed refusal, not a traceback (Issue #106).** The
  Issue #105 build-skew scan listed each default discovery root with `root.iterdir()` and `is_file()`
  without handling `OSError`, so a permission-denied or otherwise unlistable root (for example a
  `chmod 000` `~/.agents/skills`) made a ZCode `start` die with a Python traceback and exit 1 — no
  typed receipt, no actionable message. A root that exists but cannot be listed now makes the same
  comparison impossible and answers `{"result": "refused", "reason": "worker-skill-root-unreadable"}`
  with exit 1 and nothing created, naming every unreadable root in `worker_skill_unreadable_roots`
  and in `detail`. The refusal keeps the Issue #105 shape (`result: refused`,
  `mutation_performed: false`, `mutation_status: not_started`) and applies to all ten generated
  worker copies.

- **Installed-Skill prose skew is mechanically verified instead of diffed by hand (Issue #107).**
  The Issue #105 scan hashes only the shared worker scripts, so a stale main Skill
  (`kaola-project-runner/SKILL.md` + references) or stale worker `SKILL.md` prose in an installed
  tree was caught only by the manual step-3 `diff -rq`. `render-skills.py --verify-install DIR` now
  compares every generated Skill present under `DIR` against a fresh render of the accepted
  checkout — every byte, `SKILL.md` and `references/` included — and prints one JSON receipt
  (`result: aligned|refused`, `reason: skill-install-skew`, a `skew` list naming each `stale` /
  `missing` / `unexpected` path with both 12-hex digests), exiting 1 on any skew. It is read-only,
  skips a Skill that is not installed so a partial install verifies cleanly, and replaces the manual
  `diff -rq` in `docs/zcode-host.md`. The runtime `start` scan stays scripts-only because a worker
  Skill copy carries only its own rendered prose; the accepted checkout is the one place every
  Skill's render is available. `skills.roots` / `plugins.dirs` / `extraRoots` remain out of scope.

- **A ZCode Host's model is a dispatch requirement, not a preference (Issue #108).** The
  control plane must run GLM 5.3 at effort `max`, and nothing enforced that: a Host `start`
  could take the plan's first-listed model at a default thought level and silently continue.
  A `start` whose Runner session name has the documented Host shape
  `zcode-<PROJECT_CODE>-orchestrator-<purpose>` now enforces the pair mechanically. An
  explicit `--model`/`--effort` that contradicts it is a typed pre-mutation refusal —
  `{"result": "refused", "reason": "host-model-mismatch"}`, exit 1, nothing created — with
  `host_selection` naming required and requested values; an absent selection is pinned,
  not refused. Once the session reports ready the pin is applied through the ordinary ACP
  config options (`model`, `thought`) and verified against the holder's own advertised
  `currentValue`s; a session that cannot prove the pair — for example a Coding Plan that
  does not offer GLM 5.3 — is stopped and the start is refused
  (`host-model-unverified`, with `host_session_stopped`, `residual_pids`, `holder_alive`,
  and the effective values found). A passing start reports `host_selection` — required,
  requested, applied, and verified effective values — on a fresh start and `--resume`
  alike. The discriminator is the session-name shape, not a flag: an opt-in marker can be
  forgotten, which is exactly the silent wrong-model start this removes. The issue-worker
  marker `-i<digits>-` wins over a purpose token containing "orchestrator", so an ordinary
  worker is never pinned; a live nonstandard Host (`zcode-kaola-host`) is attached in
  place and never re-`start`ed, and PTY sessions never reach the ACP-only check.

## 0.5.3 — 2026-09-20

- **A pin upgrade is not finished until the Skill install is refreshed, and a Host `start` now
  refuses the skew (Issue #105).** Registering an accepted checkout does not touch
  `~/.zcode/skills`: a ZCode Host started from the new checkout while the installed worker Skills
  are the previous build dispatches workers whose `start` runs the *old* copy, and that copy has
  no Issue #104 binding — the worker opens unbound and exits 0, so the mechanical guarantee fails
  silently. Every pin bump now ends with `./scripts/install-local.sh --runtime zcode --method copy`
  from the accepted checkout, a file-by-file alignment check, and a restart of whatever still runs
  the old code; `docs/zcode-host.md` carries the four steps and the verification command, and
  `AGENTS.md`'s release rule already requires the per-platform check. As the backstop when the step
  is skipped, a ZCode `start` run from an installed Skill tree hashes `kaola-acp.py`,
  `kaola-acp-holder.py`, `kaola-tmux.sh` (and `kaola-zcode-acp.py` where both sides ship it) in
  every Skill directory under the four default ZCode discovery roots and refuses
  `{"result": "refused", "reason": "worker-skill-build-skew"}` with exit 1 before anything is
  created — no record directory, no socket, no holder — naming the differing paths with both
  12-hex digests in `worker_skill_skew`. A passing `start` reports `worker_skill_build` and
  `worker_skill_roots`; both are `null` when the CLI ran from a repository checkout, which has no
  Skill build to be the baseline. Skew has two directions and only one is new: an *old* Host with
  a *new* worker Skill stays the Issue #104 transitional case (unbound, not refused, fixed by
  restarting the Host). The Host prose adds one rule: a `start` receipt with no
  `heartbeat_host_source` key at all is a pre-#104 worker Skill — exact-stop it and refresh the
  install rather than reading it as an ordinary unbound worker. Roots reached only through
  ancestor directories, `skills.roots`, or `plugins.dirs` are a documented residual.

## 0.5.2 — 2026-09-20

- **Worker binding on the Project Runner dispatch path is mechanical (Issue #104, design
  Issue #99).** Every holder now names itself to the agent it hosts through one identity fact,
  `KAOLA_ACP_DISPATCHER` (`holder_instance_id`, `platform`, `repo`, `session`; the ZCode bridge
  forwards it and still never forwards `KAOLA_ACP_CHILD_RECORD`). A worker `start` run inside a
  ZCode Host derives `KAOLA_ACP_HEARTBEAT_HOST` from that fact, verifies the Host holder is live
  (record, `holder_pid`, same `holder_instance_id`, admin socket), and binds; the receipt reports
  `heartbeat_host_source` (`none` / `explicit` / `dispatcher` / `dispatcher-no-carrier`) and
  `dispatcher`. Three typed pre-mutation refusals, `result: refused` with exit 1 and nothing
  created: `heartbeat-host-unresolved` (the named Host holder is not live),
  `heartbeat-host-conflict` (an explicit variable names a different Host than the dispatcher),
  and `heartbeat-host-pty-unsupported` (Runner dispatch is ACP-only: a `--transport pty` start
  under any dispatcher, or with only the canonical-root export, is refused by `kaola-tmux.sh`).
  Standalone starts, explicit-variable starts, and every existing PTY session are unchanged.
  Host prose shrinks accordingly: the main Skill, `zcode-host-dispatch.md`, `host-startup.md`,
  the Kaola-Delegator Skill and its handoff no longer instruct a manual bind or a per-worker
  binding check. Transitional: a ZCode Host whose holder started on an older build never set
  the fact, so its workers start unbound (not refused) until that Host is restarted on this build.

- **The `kimi-cli` process and TUI matchers accept the Kimi Code 2.x pane-command shape
  (Issue #103).** Kimi Code 2.x ships as a Node SEA standalone Mach-O, so the tmux pane command
  (kernel `p_comm`) is `kimi`, not `node`, while the rewritten process title is still exactly
  `kimi-code`. `adapter_process_matches` and `adapter_detect_tui` now accept `kimi` alongside the
  legacy `node`, with both conditions still required and both still exact. Version stamps move to
  `cli=2.0.2` only where that was verified live on this machine.

- **`locate --worker zcode --session` reports ACP holder aliveness beside the tmux-only
  `session.present` (Issue #102).** `session.present` comes from `tmux has-session` alone, so a
  live ZCode Host — an ACP holder with no same-named tmux session — read as `present=false`
  and looked like a Host that was down. The locator now also reads the one holder record that
  `kaola-acp status` reads, at the same exact path, and adds `session.acp_holder_alive`: `true`
  when that record names a live `holder_pid`, `false` when the record is absent, unreadable, or
  names a dead pid, and `null` when no `--project` checkout is named so the path cannot be formed.
  One exact path, no scan, no new registry, no schema version; tmux-only workers and calls without
  `--worker` keep a byte-identical `session = {name, present}`.

- **`install-local.sh` carries no here-document or here-string, and every validate suite runs
  under a watchdog (Issue #101).** A `./scripts/validate.sh` run hung inside `place_staged`:
  bash 5.3 serves a here-document body that fits `HEREDOC_PIPESIZE` through a pipe the forked
  child fills before exec, and under pipe-KVA pressure macOS hands out a 512-byte pipe, so a
  1066-byte body blocks in `write()` forever — the Issue #78 shape. All eleven feed sites are
  now structural: the six `python3 -` feeds became `python3 -c '<same program>' <same argv>`,
  the usage text is printed with `printf`, and the four `read <<<` here-strings read from a process
  substitution; programs, argv order, exit codes, and error strings are unchanged, and `--help`
  output is byte-identical. Alongside it, `scripts/validate-watchdog.sh` wraps every suite with a
  600 s budget: on a trip it records the process tree, `lsof -p`, and a `/usr/bin/sample` of the
  deepest childless process to a receipt that survives cleanup, kills the tree deepest-first,
  names the receipt in the `FAILED` line, and exits 124. macOS ships no `timeout(1)`.

## 0.5.1 — 2026-09-20

- **dsh (DeepSeek Harness) is the tenth worker platform, ACP only (Issue #98).** `dsh` ships its
  own automation-only ACP v1 stdio server, `dsh --profile acp`, so the Runner binds to it directly
  with no bridge, proxy, or translator: `platforms/dsh.yaml` plus `scripts/adapters/dsh.sh` and the
  roster registrations are the whole change. No transport *mechanism* was added — the holder
  already branches on `agentCapabilities.sessionCapabilities.resume` and already sends `configId` —
  but two shared receipt bugs that only dsh's shapes expose are fixed with it, and those change
  receipts on every platform; see the end of this entry. dsh negotiates
  `protocolVersion 1` as `deepseek-harness-acp/0.0.1` and advertises
  `sessionCapabilities {close, list, resume}`, so the holder's existing capability branch already
  takes `session/resume`; `session/load`, `session/set_mode`, `session/delete`, `session/fork` and
  `terminal/*` all answer `-32601`. Three platform facts are recorded rather than papered over.
  **There is no `--continue`:** `session/list` entries carry only `sessionId` and `cwd` with no
  `updatedAt`, so no latest session can be determined, and the manifest says `unsupported` instead
  of advertising a flag. **There is no PTY transport:** no terminal UI exists for dsh, so
  `--transport pty` is a diagnostic entry, not a fallback or a login channel. **There is no
  approval gate:** dsh's ACP composition never sends `session/request_permission` — two live
  tool-using turns, including a bash write to an absolute path outside the session workspace, ran
  unattended with the client never consulted — so unlike OpenCode this is not "no skip-all", it is
  nothing to skip, and README and the manifest say so. One operator precondition is documented
  rather than worked around: the shipped `acp` bundle pins the `deepseek-official` route and
  ignores the user's own default-model setting, so a session can start `ready` and still fail its
  first `session/prompt` with `no API key for provider route "deepseek-official"`; supply
  `DEEPSEEK_API_KEY` or pass `--model` to select a credentialed route through the existing
  `set_config_option` path. Because dsh's model option values are JSON-encoded `[provider, model]`
  arrays serialized as strings, `acp_model_map` carries the shipped catalog keyed by plain ids.
  That exposed the first shared bug: `acp_value_params()` read a value bracketed end to end as a
  trailing `[k=v,...]` descriptor and invented a `declared` map from the array's elements. It now
  declines a value that opens with the bracket — a descriptor qualifies a base value and can never
  be the whole value — and Cursor's genuine `grok-4.6[effort=high,fast=true]` still parses. The
  second: dsh is the first platform whose select options are **grouped** by provider, and the
  holder read `value` off the group entry, so the preflight probe reported one nameless choice per
  group and the `set_config_option` receipt lost its `value_name`/`value_description`. A new
  `config_option_values()` expands one level of grouping and both sites use it; on flat-option
  platforms the only change is that an entry carrying no `value` is omitted instead of reported as
  `null`. Native steering is unsupported (all four candidate methods `-32601`), and the existing composite
  `--steer-mode interrupt` needs no raised timeout: `session/cancel` settles the running turn in
  about 0.01 s with `stopReason: cancelled`. Nothing under `$DSH_HOME` is ever written — creating
  an `acp` profile with `--from-default-profile` is an operator act the Runner does not perform —
  and the adapter's preflight only reads that home to report whether the profile exists.

## 0.5.0 — 2026-09-19

- **Codex installs a user-level `SessionStart(compact)` recovery entry, so an outer
  Codex Delegator recovers from any repository (Issue #97).** The Issue #75 hook lived
  only in a consuming project's `.codex/hooks.json`, bound to one Host session at one
  canonical root; an outer Codex Agent that loaded the installed `kaola-delegator`
  delegates from whatever repository it is in, so after a compaction it could not be
  told to re-read the Skill, and installing the Delegator installed no hook at all.
  `./scripts/install-local.sh --runtime codex` (and the legacy no-flag Codex default)
  now merges one Runner-owned entry, `kaola-project-runner:user-compact-context`, into
  `${CODEX_HOME:-~/.codex}/hooks.json` with private asset copies under
  `${CODEX_HOME:-~/.codex}/kaola-project-runner/hooks/`, whenever the control-plane
  Skills are in the plan. Its `user-emit` prints a short conditional payload (about
  1.2 KB) on every `SessionStart(compact)`: a session already using `kaola-delegator`
  or `kaola-project-runner` completely re-reads that installed Skill and continues
  from current authorization, live ACP/Runner receipts, and Git/worktree/Workflow/Issue
  records; every other session does nothing, and no role or project is ever inferred
  from the working directory. There is no binding table, session registry, cwd map, or
  heartbeat. Merge is by owned id and idempotent; the Kaola Workflow user hook and
  user-owned entries are preserved, never echoed or copied; no backup copy is made; a
  malformed user `hooks.json` is refused during installer planning, before the first
  Skill write. `--no-orchestrator` skips the entry, `--uninstall` removes only it,
  and `--skills-dir` or any other runtime never touches a `hooks.json`. Coexistence
  with the legacy project-level entry: `user-emit` stays silent exactly when the
  session's cwd holds a Runner project entry bound to that same session and root — the
  predicate the project `emit` fires on — so one compaction never carries two Runner
  blocks; migration is an explicit per-repository `uninstall --project-root`, and the
  project actions are unchanged for direct Hosts. The installer and the docs say
  plainly that Codex still requires the owner to review and trust the new entry in
  `/hooks` and loads hooks at session start, so recovery is not active before the
  install, while untrusted, or in the installing session. Verified live in an isolated
  `CODEX_HOME` preset with the Workflow hook and a user-owned entry: real `/compact`
  runs in two unrelated scratch repositories re-read the installed Delegator Skill
  (real `CommandExecution` after the `compacted` record) and contacted no Host, an
  ordinary session received the block and took no action, a Project Runner session
  re-read its Skill, and a repository with a bound legacy project entry received the
  project block and not the user block; the `/hooks` review and trust flow was
  captured on codex-cli 0.153.4 and the compaction runs on 0.153.4/0.155.1.
  Contract: `tests/contract/test-issue-97-codex-user-compact-hook.py` and new
  `test-installer-runtimes.sh` cases.

## 0.4.0 — 2026-09-19

- **`./scripts/validate.sh` no longer has to be run with the canonical-root binding
  unset (Issue #96).** Two contract classes start a worker through
  `scripts/kaola-tmux.sh` against their own throwaway repository, but built the child
  environment from a bare `dict(os.environ)`. An operator shell that is itself bound as
  a Project Runner control plane therefore leaked `KAOLA_PROJECT_RUNNER_CANONICAL_REPO`
  into those starts, and the Issue #73 guard refused them — correctly — before the mock
  ACP agent was spawned. Because a refusal receipt carries `result`/`reason` and no
  `error`, the suites' `assertIsNone(receipt.get("error"))` passed and the run died one
  line later on an unrelated `FileNotFoundError` for the mock log, or on `[] is not true`
  and `no-session`. Both suites now drop the binding, which is what
  `test-issue-73-canonical-root.py` and `test-issue-88-permission-defaults.py` already
  did, and each start asserts the receipt is not `refused` first, so a future refusal
  reports its own receipt instead of a misleading downstream error. This is a test-harness
  change only: the Issue #73 guard is untouched, production Runner commands still require
  the binding, and nothing is unset globally.

- **One unhandleable agent message no longer kills the ACP holder's reader thread
  (Issue #95).** `AgentConnection._read_loop` called `on_agent_message` unguarded, so the
  first exception that escaped a handler ended the thread while the agent process stayed
  alive: every later `session/update` was dropped, every later JSON-RPC response was never
  resolved, the turn stayed `active` forever, and nothing said so. Issue #92 removed the one
  trigger then known; the structure that turned any such exception into a silent, permanent
  wedge remained, and a malformed `session/update` still reached it. The reader now
  scopes a handler failure to the message that caused it and keeps reading, so what follows
  is delivered normally. The failure is recorded as an `agent_message_error` event and counted
  in `status` and the holder record as `agent_message_errors`. It is a failure, not a success:
  the message is not answered, not retried, and never approved on the agent's behalf, so an
  unanswered agent request stays unanswered and the controlling Agent decides from `status`.
  The event carries locator facts only — method, JSON-RPC id, exception class, and the
  innermost frame; the raw message and the exception's own text are both withheld because
  either can quote agent payload. There is no new thread, restart, watchdog, scheduler, or
  retry mechanism.

- **Kimi Code CLI 2.0.1 ACP compatibility reverified.** An isolated live run
  confirmed `initialize`, session creation, model/thinking/YOLO selection, a
  completed prompt, exact stop, and resume of the same native session with
  prior context. The four candidate native steering methods still return
  `-32601`, so the explicit interrupt-and-continue path remains the supported
  steering fallback. This updates the versioned capability description only;
  no transport behaviour changes.
- **A pending-approval wake survives a temporarily absent ZCode Host (Issue #92).**
  Issue #76 gave a bound worker one `permission_required` carrier send per new
  pending request. That send was the only chance the wake ever got: a pending
  permission keeps the worker turn ACTIVE, so no turn-end `idle` follows it, and
  when the bound Host holder was not listening the send recorded
  `host-unreachable` in the worker's own log and nothing else happened — a Host
  that later restarted was told nothing, forever. The worker holder now RETAINS
  an undelivered `permission_required` and re-offers it from the watchdog tick it
  already runs. There is no new thread, scheduler, registry, ledger, or transport
  gate, and no retry deadline to outlive: the wake lives exactly as long as the
  request it locates, so a Host absent far longer than any single attempt still
  gets it when it comes back. The retry reuses the ORIGINAL `event_cursor`, so
  the deterministic `event_id` is unchanged and a repeat is answered by the
  existing Issue #90 dedup rather than prompting the Host twice or asking for a
  second approval. What is owed is decided by whether the Host ever TOOK the
  event, not by an error-code allowlist: `host-unreachable`, `host-closed`,
  `host-reply-invalid`, and `unknown-op` (a Host holder too old to know the op)
  all mean it was never taken, and each can still come good when the Host comes
  back. Anything else is the Host's own answer and settles the debt, including a
  refusal it made knowing what it refused — re-offering a `worker-event-queue-full`
  answer would drive the Host's overflow full-check every tick instead of
  recovering the wake. Delivery is proved positively: `op_worker_event` names the
  event it took on every accepting path, so a reply that carries neither a usable
  error code nor an `event_id` leaves the wake owed rather than silently retiring
  it, and a reply that is not a receipt at all becomes a `host-reply-invalid`
  carrier failure instead of raising on the agent reader thread that sent it.
  An accepting receipt must name the event that was actually SENT: `event_id` is
  deterministic, so a blank one, somebody else's, or one for a different cursor
  or kind leaves the wake owed rather than retiring it while claiming a
  recovery. And a wake that stops being owed while an offer is already in
  flight — a `permit` settling it, the agent exiting, a stop beginning — is
  re-checked immediately before the bytes go out, as late as the transport
  allows; `stopping` joins `permission-settled` and `agent-exited` as a reason a
  wake ends. That NARROWS the window and does not close it: check, write and the
  Host's own staging are three steps across two processes, so a settlement
  landing after the write still leaves the Host holding an event whose request
  is gone. No claim is made that such a wake is never sent. Instead the two
  facts are kept apart — carrier delivery is not a live approval: a delivery
  whose request died in flight is recorded as `heartbeat_carrier_delivered_stale`
  with the reason that overtook it and the Host's own receipt, never as
  `heartbeat_carrier_recovered`. Safety comes from the Host side, which the
  dispatch reference and heartbeat prompt already require and now pin by test:
  the event is a LOCATOR, the Host re-reads the worker's live
  `pending_permissions` before acting, a vanished request is ignored
  idempotently, and nothing is ever approved from the event itself. A wake whose
  request was settled, or whose worker agent exited, BEFORE the offer is written
  is dropped as stale and never becomes a prompt; one settled after the write is
  a stale delivery the Host does see, and what protects it there is that
  re-observation plus the ordinary `no-pending-permission` refusal on any stale
  approval. Only the exact locator and `request_id`
  travel — never a title, option, tool input, command, or credential — and the
  event still approves nothing: the Host decides `permit`/reject inside its own
  authorization, after which the ordinary turn-end `idle` arrives as before.
  `observe`/`status` now report `undelivered_worker_events` so the debt is
  visible instead of silent. Ordinary `idle`/`terminated` sends stay one-shot,
  unbound workers and non-ZCode Hosts are untouched. Hermetic contract tests
  cover the absent-host recovery on Host restart, the repeated offer, the
  settled and agent-exited stale drops, the busy Host staging then flushing, and
  the unchanged idle/unbound paths.
- **ZCode Host loads Project Runner through the native `/kaola-project-runner`
  Skill invocation on every turn-opening prompt (Issue #94).** First
  handoff, resume or attach update `send`, worker-event notification, and
  the round after any compaction share one entry: the command as the
  prompt's own first line, resolved through ZCode's Skill tool against the
  installed `kaola-project-runner` Skill. A busy `steer` guide is forwarded
  into the running turn verbatim — it keeps the already-loaded context and
  is not a new `Skill` invocation. The composite `steer --steer-mode
  interrupt` resends on a genuinely new turn but is not a Host recovery
  entry — it carries the Agent's text verbatim on every session and adds
  no entry line, so a caller that uses it to open a Host round supplies
  `/kaola-project-runner` itself. Verified install-time default discovery
  roots on ZCode 3.12.3: `<repo>/.zcode/skills/`, `<repo>/.agents/skills/`,
  `~/.zcode/skills/`, `~/.agents/skills/` (plus both roots on ancestor
  directories; configured `skills.roots` and `plugins.dirs` roots scan
  too — a plugin skill surfaces as `<plugin>:<skill>` and stays loadable
  by its plain name). The host holder prepends that line to the
  `kaola-host-notify/1` envelope; the Host's `heartbeat-prompt.json` `body`
  still carries only the working prompt — never the entry line or the Skill
  body. This replaces the Issue #75 compact-recovery path: no durable
  `AGENTS.md` block is planted in consuming projects, ordinary Agents carry
  no Host recovery instruction, and no role filtering, compaction
  detection, or manual `SKILL.md` reread is required. Verified live on
  ZCode 3.12.3 / adapter 0.3.3: `/kaola-project-runner` produces a native
  `Skill` tool_call, a real `/compact` then the command produces a new one,
  command-plus-trailing-text beats invoke the Skill and process the text,
  and post-auto-compaction requests (isolated mock provider) still carry
  the skill metadata on the wire. `references/zcode-compact-recovery.md` is
  superseded by `references/zcode-native-skill-entry.md`; its runtime facts
  (no compact hook, silent ACP compaction, `part`-table rows) are kept
  there. Not verified: real-model behaviour after a genuine auto-compaction
  (1M-window catalog models), any compact-specific ACP event, and a `Skill`
  tool_call from a busy `steer` guide — none is claimed there.

- **Native mid-turn steering on ZCode 3.12+ through the v4 command surface,
  event-proven on the installed 3.12.3 (Issue #81).** The retired `session/steer`
  surface was correctly declared unsupported (Issue #65), but 3.12+ moved the
  capability rather than removing it: `v4/command sendText` with
  `requestedDelivery:"guide"` is admitted as a guide input and injected at the
  next tool/message boundary *inside the running turn*. The adapter now answers
  the existing `_session/steering` ACP method through that path: it primes
  `v4/conversation/subscribe` lazily on first steer (the publisher whose steer
  events ride the existing `session/event` stream), sends `sendText` with a
  per-turn `expectedTurnId` CAS learned from `turn.started`, and waits a bounded
  window for the evidence. The outcome is decided by the events alone — the
  sendText ack is a measured trap (`result.delivery` reads `"queue"` even for an
  admitted guide input) — so `injected` is reported only when
  `turn.steerQueued{delivery:"guide"}` and `turn.steerDrained{injectedMessageIds}`
  name the same `targetTurnId`, and that turn is provably the one the steer
  targeted (when the backend never names the running turn, an otherwise-matching
  pair reports `unknown`, not `injected`). Queue-only admission maps to
  `not_consumed` with `mutation_performed` true (the text is durably queued for
  a later turn), a turn-end race or silence maps to `unknown`, a platform
  rejection surfaces its `reasonCode`, and a pre-0.16 backend's `-32601` reports
  `unsupported`. No second lifecycle, scheduler, or stdin writer is added;
  `--steer-mode interrupt` remains the explicit fallback. Hermetic contract
  tests cover guide/drain, queue-only, rejection, silence, turn-end race,
  cross-turn and unattributable drains that must never claim `injected`, and
  the missing-v4-surface build.

- **ZCode Host confirms the notification it just delivered, and a confirmed worker event
  is not re-prompted (Issue #90).** The carrier used to mark its staged events and snap
  the overflow generation only *after* `session/prompt` was admitted, so a Host that
  answered inside that window ran the turn-end callback against an unmarked turn:
  it confirmed nothing and delivered the same events — and the same full-check
  generation — a second time. Admission and the marking of what it delivered are now one
  hold of the existing worker-event lock, so the callback waits and sees a marked turn,
  and two deliveries racing over the same staged events cannot both admit. Marking only
  follows a successful admission, so a refused prompt leaves nothing to undo. One worker
  event is one Host prompt and one confirmation.
  A retry of an already confirmed deterministic `event_id` is answered as a duplicate
  instead of being staged and delivered again: a bounded in-memory index answers the
  ordinary case — as a cache, not as truth: each entry carries the cursor its
  confirmation was recorded at, so an entry whose record rotation has dropped stops
  answering and falls back with every other miss to the `worker_event_confirmed`
  records themselves. The answer holds for as long as the event log retains the
  confirmation rather than for a fixed number of ids. That confirmation is now
  written before the events leave the pending list, so a retry is never answered
  against a fact that is not durable yet. Busy-host staging, failed-notification restaging, cap-32
  overflow, and at-least-once resume of genuinely unconfirmed events are unchanged.
  No scheduler, no second queue or ledger, no new gate.

- **ZCode Host heartbeat overflow wakes a full check instead of dropping the 33rd event
  (Issue #87).** The carrier still stages at most 32 detailed worker events. A later
  event still returns `worker-event-queue-full` and is not a 33rd detailed line; the
  host holder records one monotonic full-check generation in the existing event log
  and puts it on the next heartbeat so the Host inspects authorized workers' real
  status and pending approvals. A notification confirms only the generation it
  delivered; overflow during that turn still needs the next wake. If the Host is
  already idle with a full detailed queue, the overflow delivers that full-check
  immediately. Restore takes the max overflow and confirmed generations so a late
  gen1 line cannot hide an unconfirmed gen2, and seeds current generation at least
  the confirmed generation so rotation cannot rewind the counter. The signal
  reminds only and does not
  approve permissions. Exact `stop` then `start --resume` restores an unconfirmed
  generation. Reading `.kaola/heartbeat-prompt.json` is capped at
  65536 bytes: an oversized file is a named defect, is never injected as a
  truncated-looking body, and still delivers the worker wake. No new queue,
  scheduler, timed heartbeat, or quota system.

- **An unspecified token quota is no longer an extra hard start gate for
  Kaola-Delegator (Issue #86).** Issue #74 requires a new ZCode Host to hold
  current authorization before `start` and forbids fusing quota units. The
  shared Delegator prompt had turned that second rule into "all three quota
  units are mandatory figures": the Skill collected "quota as separate
  concurrency, account, and token figures", handoff step 4 demanded "account
  and token quota as separate figures", and the handoff text said the three
  "stay three numbers". An outer Agent given worker platforms, counts,
  concurrency, an account quota, priority, the stop boundary, and the canonical
  project path therefore still refused to start, for want of a separate token
  cap. Quota now travels in the units the user actually gave: a unit the user
  never gave is not a missing key value, it is carried as `unspecified` and
  does not block the start, and `unspecified` is explicitly not unlimited. Unit
  non-fusion, no guessing, no stale reuse, no blank Host, still-ask on a
  genuinely missing or ambiguous value, and no re-ask on a live Host are all
  unchanged. Prompt-only: no new schema, state file, quota engine, or transport
  gate. `reference_bytes` had 3 bytes of headroom and the budget is a locked
  invariant, so the handoff edit is net-negative (8189 -> 8186 B rendered),
  funded by two lossless rewordings that drop no rule; the fuller statement
  lives in `SKILL.md` (3824 -> 4010 B of 4096).

- **A failed-closed native `sess_*` resume no longer advertises the rejected
  model (Issue #85).** `hydrate_settings()` used to emit its
  `session/update {sessionUpdate: config_option_update}` — including a model
  `currentValue` naming the persisted selection — before
  `reregister_provider()` validated the recovered pair, so a resume that then
  failed closed had already advertised an option for a model that was refused
  and never took effect. The resume path now announces the session's
  mode/model/thought only after the selection is established: a refused resume
  emits no config advertisement at all, while a successful one still
  advertises the accepted model exactly once. Fail-closed semantics are
  unchanged — nothing is substituted, the backend still sees no
  `session/setModel`, on 3.12+ and on the pre-3.12 overlay path alike.

- **The permission default is stated per platform, and the OpenCode steering evidence carries its
  own version (Issue #88).** The main Runner Skill's `Defaults` table said "Existing Runner default
  bypass start", which reads as a guarantee for all nine platforms. It is not one: Claude Code,
  Codex, Devin, Droid, Kimi and ZCode apply an advertised ACP skip-all option at start, Cursor and
  Grok carry only a launch flag with `acp_mode_config_id` empty, and OpenCode's ACP surface
  advertises no skip-all at all. The row now reads as a per-platform default, and the surrounding
  paragraph states one general rule -- with no verified ACP skip-all a permission request may still
  arise -- rather than naming a single platform, so Cursor and Grok are covered too. It surfaces
  through the existing `permission_required` carrier event and is settled with `permit`; README
  carries the per-platform roster. Neither `docs/api.md` nor `README.md` pins which platforms steer
  natively or how many do not; both now send the reader to `native_steering` in
  `platforms/<id>.yaml`, and the composite `--steer-mode interrupt` stays an explicitly chosen
  option on every platform. Wording only: no adapter, scheduling or approval-mechanism change, no
  auto-approval, no new gate. Separately, `platforms/opencode.yaml` declared
  `acp_verified_versions cli=1.18.29` while its `steering_summary` reported a JSON-RPC `-32601`
  probe run on 1.18.17. OpenCode's `native_steering` is now `unknown` rather than `unsupported`, so
  the manifest, the generated Skill and every `steer` receipt agree: the 1.18.17 result stays in the
  summary as history, the worker Skill says no native entry has been *verified* instead of
  asserting one does not exist, and `steer` answers `steer_outcome: unknown` with
  `steer-capability-unknown` and "absence is not established". `unknown` was already a first-class
  manifest value and receipt outcome; only the wording that contradicted it changed. Behaviour is
  untouched -- the bare `steer` still refuses with `available_steer_modes: ["interrupt"]`, the
  composite stays explicitly chosen with no auto-degrade, no probe engine was added, and the eight
  other platforms' steer receipts are byte-identical.
- **Native `sess_*` resume keeps the session's own Coding Plan model on ZCode 3.12+ (Issue #84).**
  A faithful `--resume sess_*` failed outright with `resume-failed` / "resumed session reports no
  persisted model", because five things were wrong at once on the 3.12 wire. `session/read` on
  3.12.3 returns `{"messages": [...]}` and no top-level `settings` at all, so `hydrate_settings()`
  -- which only read `settings.model.current` -- never saw a model; the sibling `session/messages`
  serves the same list with flat `info.modelId`/`info.providerId` keys and was never consulted.
  `reregister_provider()` then compared the persisted provider against the desktop-registry id
  (`builtin:bigmodel-coding-plan`) although a real persisted session names the account provider
  (`account:bigmodel-individual-coding-plan`), sent `session/setModel` with a top-level
  `runtimeModel` key that 3.12 rejects with a ZodError, and ran against a provider registry that
  `_resume_backend_session()` never populated, because `provider/updateAccountConfig` was only
  pushed on the fresh-session path. The resume path now reads the persisted model out of whichever
  transcript shape the backend serves -- newest entry by `info.time.created`, not by array
  position -- and re-registers through the same `push_account_config()` +
  `select_account_model()` the fresh-session path already used. Separately,
  `_resume_backend_session()` retried `session/resume` with the pre-3.12 `runtimeModel` overlay
  after *any* failure, so an unknown or already-deleted session was reported as
  `Unrecognized key: "runtimeModel"` instead of its real reason; it now retries only on the
  pre-3.12 `Model config is missing` signal, exactly as `session/create` already did, and a
  missing session reports `-32004 Session not found`. Nothing is substituted: a persisted model
  outside the enabled plan, or belonging to another account, still fails closed without ever
  calling `setModel`, and the plan default is never selected on the user's behalf.
  `reregister_provider()`'s pre-3.12 overlay branch is unchanged; the only pre-3.12 behaviour that
  narrows is that a backend asking for the resume overlay must now say so with the same
  `Model config is missing` signal `session/create` already required.
  One consequence of a resumed session reporting its real provider is that the model option it
  advertises as `currentValue` is now account-qualified, and `session/set_config_option` only
  accepted the desktop-registry `builtin:*` id — so a client that echoed back the very value it
  had just been handed was provider-refused. Either id for the one enabled Coding Plan now
  round-trips, and the account path records the provider the turn actually runs on rather than
  whichever of the two ids the client typed. The one-Coding-Plan boundary is unchanged: any other
  provider, including another account, still fails closed without reaching `session/setModel`. Verified on real ZCode.app 3.12.3 / CLI 0.16.5 over ACP in an
  isolated repo: one native session, a real turn, an exact holder stop
  (`residual_pids: []`), `--resume sess_6fe8bc2d-...`, then a second real turn that answered on
  `account:bigmodel-individual-coding-plan\GLM-5.3` and quoted its own first reply back. Resuming
  that same session with the pre-fix adapter still fails, on the same machine.
- **Kaola-Delegator treats native resume after exact stop as
  backend-dependent (Issue #74).** After `stop`, try attested `--resume` of
  that `sess_*` first. Do not assume `session/close` always spends the id.
  A new Host is allowed only after proven resume failure and complete
  authorization. Issue #84's live resume proof is a separate issue and is
  not merged here.

- **Kaola-Delegator Host stop and live attach bind the receipt holder
  (Issue #74).** Exact `stop` passes the existing Runner
  `--expected-holder-instance-id` from the start/`status` receipt. A
  `holder-instance-mismatch` (H1 replaced by H2 on the same session name)
  is refused; re-read `status`. Live attach compares `holder_instance_id`,
  not repo+session name alone. Fake ACP isolation is not outer A→B; missing
  authorization non-start stays documentation-only. A filtered
  `--platform` reinstall/uninstall on Codex/generic no longer leaves a
  stale `kaola-delegator` after a full install. Existing budgets were not
  raised.

- **Kaola-Delegator checks the first Host beat against independent facts
  (Issue #74).** Start-receipt identity is not enough. After the first
  `end_turn`, compare the Project Plan and current authorization with Host
  file-read or work-product evidence and the first worker dispatch receipt
  (`heartbeat_host`, issue-scoped worker name, authorized platforms). Do not
  trust the Host's self-description. Mismatch or missing evidence: correct on
  that Host; do not accept completion. No new script, gate, ledger, or budget.

- **Kaola-Delegator recovers a live Host from canonical repo, standard Runner
  session name, and existing status/receipts (Issue #74).** There is no
  required `.kaola/delegator-host.json`. Agent B attaches the same ACP Host in
  place; a uniquely recorded nonstandard live name is adopted; ambiguous
  location does not start a second Host. A Git worktree is not an ACP id. If
  the Host is confirmed stopped, try attested `--resume` of that `sess_*`
  first; native resume after `session/close` is backend-dependent. On proven
  failure, a new standard-named Host is a new ACP session continued from
  Git / Workflow / Issue records, only after current authorization is
  complete; missing key values block start, not only later dispatch. The
  unproven ZCode.app 3.12.3 `runtimeModel` create fallback and swallowed
  `setModel` retry are not in this candidate. Fake tests are not a live
  ZCode model-session proof. Issue #84 is not merged here.
  Grok Bot, after the account bridge, attests each Host
  status/start/resume/send/stop with the existing locator `--project`
  `--worker zcode` `--session` (exact live name) and refuses `refused`;
  Codex and generic do not. Existing budgets were not raised.

- **Kaola-Delegator is the external delegation Skill; Grok Bot is no longer a
  Project Runner host (Issue #74).** The generated Skill `kaola-delegator`
  (display name Kaola-Delegator) is a thin shared core for Grok Bot, Codex,
  and generic Skill-directory hosts: it extracts task, progress, authorized
  platforms, quota (concurrency/account/token kept separate), priority, and
  project context, then starts or resumes one ZCode Host through the existing
  ZCode Runner. Project Runner (`kaola-project-runner`) remains the inner
  engine and is loaded by that Host. The Grok Bot account Skill is now
  `hosts/grok-bot/kaola-delegator.md`; it still binds the execution target
  and runs the device-local locator, then loads only the external Skill. Grok
  CLI and the other eight platform workers are unchanged. Existing budgets were
  not raised; `external_skill_bytes` 4096 is the new small ceiling for this
  Skill. This repository does not claim live Grok Bot UAT. In-flight sessions
  that still use the old Grok Bot Project Runner entry are not renamed,
  restarted, or cancelled. README opens with four entry tiers (Kaola-Delegator,
  Project Runner, Platform Runner, Workflow Next); AGENTS.md keeps the short
  principles and points at README.

- **Standalone ACP contract suites now stop the sessions they start (Issue #82).**
  `Issue34ModelSelectionAcpTests` starts codex/cursor-cli/devin holders but the
  shared fixture's `tearDown` always stopped the default grok session, so a
  standalone `test-acp-contract.py` run silently leaked 14 holder/mock-agent
  pairs; `test_view_accept_then_close_uses_frozen_runtime_code` replaced the
  holder's socket with a stub listener, so teardown's `stop --force` got
  `holder-unreachable` and left that holder and its agent running. Teardown now
  stops the platform the fixture actually started, the socket-replaced holder
  is reclaimed by the existing `kaola-acp-sweep.py` bounded to that test's own
  record directory (matched by its `--record-dir` argv, never a bare pid), and
  every fixture class asserts zero of its own holders or mock agents survive.
  Production stop/lifecycle behavior is unchanged.
- **Codex hosts recover through `SessionStart(compact)`, and the orchestrator
  gains a documentation-maintenance boundary (Issue #75).** A Codex host Agent
  using Project Runner (or Kaola-Delegator) can no longer be assumed to hold
  the Skill text after context compaction. The new
  `scripts/kaola-codex-compact-hook.py` installs, reports, and removes exactly
  one Runner-owned entry - `kaola-project-runner:compact-context` - in the
  consuming project's `.codex/hooks.json`, matched by id so Workflow-owned and
  other foreign entries keep their JSON content untouched (the file is
  re-serialized canonically, so byte-level formatting is not promised). The
  project layer is deliberate: a single user-global hooks.json could hold only
  one project binding, while per-project config lets any number of designated
  Hosts coexist and keeps uninstall strictly local; nothing writes
  `${CODEX_HOME}` or `~/.codex`. `install` requires `--session-id` +
  `--project-root` binding the exact designated Host session into
  `binding.json`, and the installed command runs a copied `emit` action that
  reads the binding plus the official hook stdin
  (`session_id`/`cwd`/`hook_event_name`/`source`) and prints the payload only
  for `SessionStart(compact)` on that bound session at that root — ordinary
  Worker sessions and other repositories emit nothing, and re-installing
  rebinds without touching the reviewed hook entry. For first-session
  coverage a two-phase form exists: `prepare` writes the entry and assets
  with an inert binding BEFORE the Host starts (hooks load at session
  start), then `bind` writes only `binding.json` once the designated session
  id is known — in the Codex host's own shell `CODEX_SESSION_ID`/
  `CODEX_THREAD_ID` equal that hook-input `session_id`. Re-running `prepare`
  never silently unbinds: a `binding.json` is preserved byte-for-byte only
  when it holds a non-empty `session_id` AND this project's canonical
  `project_root` (`binding_preserved`); an id without the matching root, an
  empty/whitespace id, or any other unclassifiable shape is refused before
  any write. The hook command quotes
  its path with `shlex.quote` so a metacharacter-bearing project root cannot
  alter execution, the payload, emitter, and binding copies live under
  `<project_root>/.codex/kaola-project-runner/hooks/`, no backup copy of
  `hooks.json` is ever made — foreign content, which may carry credentials,
  stays only in the file it already lived in — and a malformed file,
  including JSON-null `hooks` or `hooks.SessionStart`, is refused before any
  write rather than clobbered or crashed on. `status` never writes and
  never echoes a matched entry's `command` or arbitrary config into its
  receipt — safe metadata only, since such content could carry a
  credential; its `bound` flag is true only for a non-empty `session_id`
  whose `project_root` equals this project's canonical root.
  `--project-root` must name an existing directory, and the filesystem
  root, the user home directory, and the effective `CODEX_HOME` layer are
  refused before any write, so a mistaken `--project-root $HOME` can never
  write `~/.codex/hooks.json`; `install`/`bind` refuse a missing or blank
  `--session-id`. The same containment is enforced inside the project:
  before any read, write, or delete the real paths of `.codex`, the
  Runner-owned asset parents, and each owned leaf (`hooks.json`,
  `compact-recovery.md`, the emitter copy, `binding.json`) are resolved,
  and a symlink escaping the canonical project root (such as `.codex` or a
  `binding.json` pointing into `CODEX_HOME`) is refused — writes are
  atomic-replace but reads follow symlinks, so leaf links are checked too;
  symlinks staying inside the project remain legal. The short payload only
  re-points the host: confirm role, fully re-read the installed Skill, recover
  authorization/heartbeat/run records - never re-intake, re-claim, or
  re-dispatch. Verified in an isolated real `/compact`: the injected context
  reached the model before its next turn while the existing Workflow hook
  fired alongside. Separately, the orchestrator template gains
  `references/doc-maintenance.md`: workers judge per-issue documentation
  impact at dispatch, acceptance reuses the Workflow documentation docking
  (no second ledger or gate), `AGENTS.md` carries only verified durable facts
  per ADR 0023, and post-sink verification syncs in-flight Agents at a safe
  point without per-beat doc scans. ZCode gets the equivalent through the
  Skill instead of a hook: its 0.16.5 `SessionStart` has no `compact` call
  site and no compact event exists, so
  `references/zcode-compact-recovery.md` carries the recovery text the
  controlling Agent puts once at the head of the next prompt to a compacted
  Host — verified live on 3.12.3 to make the model re-read the installed
  Skill (see `docs/zcode-host.md`). The durable block and per-send carrier
  ask for a checkable detail that exists in whichever Skill is in use —
  `references/zcode-compact-recovery.md`'s reload marker for
  `kaola-project-runner`, or the Host naming convention inside
  `references/handoff.md` for `kaola-delegator` — never a file the Skill
  does not ship. No ZCode config, hook, transport gate, or ledger is added
  for it.

- **A failing `./scripts/validate.sh` suite no longer hides the rest of its lane (Issue #83).**
  `run_suite_lane` returned on the first failing suite, so every suite ordered
  after it in that lane never ran and never left a log; the ordered replay then
  died under `set -e` on the first missing log — one `FAILED:` line, a replay
  truncated before even the logs that did exist, and a bare
  `cat: ... No such file or directory` instead of a list of untested suites.
  Each lane now runs every suite and reports `FAILED:` per failure before
  exiting nonzero, and the replay prints `SKIPPED: <suite> (no log; execution
  status unknown)` for any suite that left no log instead of aborting on a cat
  error. Green-path output is unchanged, and
  `tests/contract/test-issue-83-lane-failure-visibility.py` drives the real
  lane block with stub suites to keep both halves of that contract honest.

- **`./scripts/validate.sh` is green on a clean checkout again (Issue #80).**
  `tests/contract/test-issue-49-grok-bot-host.py` died in `TemporaryDirectory`
  teardown with `OSError: [Errno 66] Directory not empty: <tmp>/repo/.git`
  after all 43 assertions passed: git >=2.47's `commit`/`merge`/`rebase` (and
  `receive-pack` on push) spawn a detached `maintenance run --auto` child that
  keeps repacking and rewriting `.git` while `rmtree` removes it, and the first
  failing suite then aborted a whole validation lane, hiding every suite after
  it. The fixtures now run every git call with `maintenance.auto=false`, and
  the bare origin carries `receive.autogc=false` because the push transport
  strips the config environment before `git-receive-pack` starts. No assertion
  changed, no `ignore_cleanup_errors`, no sleeps.

- **ZCode 3.12+ app-server compatibility, proven by a live model turn (Issue #79).**
  The Runner-owned adapter still spoke the v0.39-era private protocol, and the
  installed ZCode 3.12.3 build contains no `runtimeModel` at all, so a turn could
  not start. Three independent breaks were fixed. The shipped 3.12.x entry cannot
  locate its own bundled provider table -- it probes `<entryDir>/provider/` and a
  five-levels-up path that fits the source tree but not the `.app`, where the table
  sits one level up -- so `app-server` exited 1 before serving anything; the adapter
  now resolves that table from the already-verified entry and injects both
  `ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` and `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`
  (both or neither, derived rather than inherited, so an unowned parent value can
  never steer the child). The 3.12+ provider registry starts empty because the
  app-server bootstrap omits its `standalone` option, which is what produced
  `Select a model before continuing`; the one enabled Coding Plan is now registered
  through `provider/updateAccountConfig`, the session is created with no model
  channel, and the model is selected on the `account:*` provider through
  `session/setModel` with an explicit `options.reasoningLevel` and
  `persistAsWorkspaceLastUsed` false. And `interaction/requestProviderRuntimeHeaders`
  was answered with `{}`, which cannot satisfy the strict response union and failed
  every turn; it now carries the credential for the one authorized provider and
  refuses any other. The CLI version string is `0.16.5` on both the working 3.11.2
  baseline and the broken 3.12.3, so no version gate is possible: the protocol is
  chosen by the backend's own error, and a pre-3.12 app-server keeps the
  `runtimeModel` path. The one-enabled-Coding-Plan policy, fail-closed refusals and
  redaction are unchanged, the credential stays in memory, and nothing is written
  under `~/.zcode`. Verified live against desktop 3.12.3 in an isolated repo: start
  with mode `yolo` applied, explicit selection, a real model reply, then exact stop
  with no residual process.

- **The shared tmux entrypoint no longer deadlocks against its own pipe under
  machine load (Issue #78).** Bash writes a here-document body up to 4096 bytes
  into a pipe from the forked child *before* `exec`, so that one process holds
  both ends and nothing drains it; macOS hands out 512-byte pipes once
  system-wide pipe memory is under pressure, and a larger body then blocks in
  `write()` forever. The stuck process has not `exec`ed yet, so it wears
  `kaola-tmux.sh`'s own argv, owns no children, and survives the SIGKILL a
  caller's timeout aims at its parent -- which is why a refused `start` could
  consume a whole 60 s budget and leave an orphan behind, while an accepted one
  passed. `scripts/kaola-tmux.sh` now carries no here-document and no
  here-string at all: Python programs go in with `-c`, and `read` is fed by a
  process substitution whose writer drains concurrently. Receipts, usage text,
  and every refusal reason are unchanged, and a contract test keeps the rule
  from regressing.

- **A bound worker's pending permission now wakes the ZCode Host mid-turn
  (Issue #76).** A worker whose agent raises `session/request_permission`
  records the pending request and wakes only its own wait - the turn stays
  active, so a Host notified only at turn end could wait on an idle that never
  comes. The worker holder now sends one `permission_required` worker event
  per new pending permission key over the existing carrier: an idle Host is
  delivered immediately, a busy one at its next completed turn boundary, and a
  retransmitted request id stays one wake. The event carries only the
  normalized `request_id` locator - title, options, tool input and
  credentials never travel; the Host reads the request from the worker's own
  `pending_permissions` receipt, treats an already-settled request as nothing
  to do, and `permit`s only inside existing authorization, escalating anything
  else to the user. The event approves nothing; the ordinary turn-end `idle`
  still arrives after the request settles. Unbound and standalone workers are
  unchanged, and no scheduler, second queue, or automatic decision exists.

- **An Orchestrator binds one canonical project root, and an exact stop is bound to
  the holder instance it verified (Issue #73).** Dispatching a worker with `--repo`
  pointing at a Workflow child worktree made one project look like several
  downstream, because a linked worktree is its own Git top-level and the Runner
  faithfully recorded it. A Project Runner Orchestrator now exports
  `KAOLA_PROJECT_RUNNER_CANONICAL_REPO` once at setup. The one entrypoint both
  transports and all nine platforms already pass through resolves that binding and
  the requested `--repo` with `realpath`, requires the binding to be a Git
  top-level, completes an omitted `--repo` from it, and on `start` compares the two
  exactly: a different root - a linked worktree of the same repository included -
  returns a typed `canonical-root-mismatch` refusal, and an unusable binding
  returns `canonical-root-invalid`, both with `mutation_performed: false` before
  any process, tmux session or record exists. An accepted dispatch reports
  `canonical_repo`. Separately, `stop` now carries the existing
  `--expected-holder-instance-id` through to the holder, which checks it before
  anything is requested, cancelled or written, so a same-named session rebuilt by a
  later holder instance is refused instead of stopped. Without the export nothing
  changes: standalone starts, existing sessions, and close-out of a legacy
  worktree-rooted session by its own `--repo` behave exactly as before. No
  registry, lock, daemon or multi-host arbitration; with the check mechanical the
  orchestrator Skill payload drops 186 bytes.

- **A worker's notification binding is reported as the holder's own fact, and a
  missed one is recovered inside the Runner (Issue #70).** A ZCode Host wakes
  only through workers actually bound to it, but the `start` receipt used to
  echo the caller's own `KAOLA_ACP_HEARTBEAT_HOST` input, so a missed or foreign
  binding looked exactly like a correct one. The holder now carries the target it
  really adopted in its own state and record, and `start`, `observe` and `status`
  report that running fact: a target, an explicit `null` for an ordinary unbound
  worker - which stays legal and ungated - or `heartbeat_host_known: false` for a
  holder or record older than the field, which is unknown and never reported as
  unbound. What a `start` asked for stays separate in `heartbeat_host_requested`,
  and a reuse that returns `session-exists` answers with the binding in force, so
  a later environment change, a `send`, or a repeated `start` can no longer look
  like a rebinding. The ZCode Host guidance verifies that fact on every worker it
  starts, reuses or adopts, and recovers a missed binding itself: it keeps the
  in-flight work, reads the result in that beat with the existing bounded
  `wait --timeout` when the unbound worker is its only wake source (a recovery
  exception, never the ordinary event wait and never a poll loop), then rebinds by
  exact `stop`/`start` and verifies the fact again; only a recovery it cannot
  complete goes out as an exception naming the decision needed, and a note in the
  heartbeat body is bookkeeping, not a wake-up. `--resume` there needs a real
  native id, which for ZCode is reported in the session's own
  `native_session_identity` event rather than `session_meta`. No new rebind
  operation, scheduler, timer or global gate; no byte budget raised.
- **Issue-backed dispatches are named for their issue, and one run claims one
  issue (Issue #72).** Every new issue-backed ACP worker dispatch now picks its
  real open GitHub issue before starting anything and names the Runner session
  `<platform>-<PROJECT>-i<ISSUE>-<unique-purpose>` - for example
  `droid-KT-i274-parser` - where `PROJECT` is the stable ASCII short code the
  consuming project's rendered heartbeat declares beside its canonical
  repository identity. The field order and the literal `i` delimiter are fixed,
  an issue is never read out of the purpose token or any other substring, and
  the name is verified in the start receipt and reused on later heartbeat
  dispatches and same-issue restarts. A Workflow run claims one real issue: no
  bundle claim, branch, child worktree, Mission List, or Runner session spans
  several, while several workers may collaborate on the same issue and share
  that issue run's Mission List under distinct names and distinct native
  sessions. The orchestrator Host itself, transport-only diagnostics, and
  genuinely issue-less tasks carry no issue number, and none is ever invented.
  Downstream, the association means **issue-run progress - completed Mission
  List items over total** - shared by every verified session on that host,
  repository, and issue; it never predicts when one ACP process finishes, and
  `all missions done` does not by itself mean review, finalize, merge, or issue
  close-out happened. A missing or malformed name, a repository mismatch, no
  active run, or two active runs for one issue fall back to unknown rather than
  being guessed from mtime, newest file, `session_marker`, worktree location, or
  the native ACP id. This is control-plane scheduling policy only: the nine
  worker Skills gained no classifier, the existing 1-80 `--session` syntax stays
  the only validator, no registry, daemon, or Workflow state field was added, no
  byte budget was raised, and running sessions - including names predating the
  rule - are neither renamed nor restarted to adopt it.

- **ZCode ACP tool cards persist path/line only, never a command (Issue #67).**
  `rawInput`/`locations` copy top-level path and line fields the app-server
  already named. Plaintext `command` is not forwarded; execute cards keep
  kind/title/status without claiming a command transcript. No generic
  sanitizer was added.
- **ZCode ACP tool evidence is a bounded path/command receipt (Issue #67).**
  `rawInput` copies only top-level path and truncated `command` fields, with a
  1536-byte / depth-1 cap. Nested blobs and extra keys are dropped. Registered
  adapter secrets in copied strings are redacted; arbitrary command text is not
  a full credential scrub. Holder `events.jsonl` is covered by the same bound.
- **The #49 host-invariance probe no longer spends product budget (Issue #71).**
  It now applies equal-length canonical edits instead of appending 59 B, so
  `templates/budgets.json` `main_skill_bytes` 17408 is the ceiling
  `render-skills.py --check` already reports. No budget was raised.
- **ZCode ACP `tool_call` updates forward the app-server `input` (Issue #67).**
  Live CLI 0.16.5 `model.streaming` `tool_call` already names `file_path` /
  `command`; the translator was caching that object and dropping it. The same
  update the holder records now carries a redacted `rawInput` and, when a
  path-like key is present, `locations`. No path is invented, `inputRef` is
  not followed, and credentials stay scrubbed. Verification guidance in
  `references/host-startup.md` matches that fact. No byte budget was raised.
- **The heartbeat carries only the constraints that are still in force (Issue
  #68).** The heartbeat is the working prompt itself, and the main Skill now
  states which trigger delivers it on which host: Codex and Grok Bot from their
  own timer system, a ZCode Host from each worker return or existing worker
  event. No shared path or schema is imposed, no timer is added to ZCode, and no
  event mechanism is forced on Codex or Grok Bot. The prompt is an
  effective-now snapshot rather than a change log: a user-confirmed quota,
  priority, platform, model or concurrency change replaces the old value and is
  re-planned in the **same** beat instead of the next one, and concurrency,
  account quota and token budget stay three separate numbers. Each beat rewrites
  the prompt through an explicit subtraction rule - superseded values, void
  plans, repeated narration, inert completed items and transient failures are
  dropped, while in-flight locators (session, worktree, Issue/PR), unfinished
  delivery, acceptance, sync and cleanup duties with their owners, open
  decisions and the minimum recovery pointer are kept - so no two contradictory
  quotas can coexist. Removing a line from the heartbeat is not deleting
  evidence and never rewrites a completed Mission's result. A lowered quota is
  not by itself a cancellation of in-flight work, and a platform failure or
  measured exhaustion is evidence, not authorization to switch platforms. No
  schema, quota ledger, scheduler, cleanup script, retry or auto-cancel
  mechanism was added, and no byte budget was raised.
- **Two startup flows, one startup receipt (Issue #66).** The main Skill now
  opens with two short entry points: ordinary worker supervision (unchanged —
  no Host obligation, no event binding, no added gate) and Orchestrator (ZCode
  Host) supervision, whose startup order, startup receipt, record separation
  and keep-versus-stop rule live in the new on-demand
  `references/host-startup.md`. Roles, authorization and the lifecycle
  boundary are read from the project's existing Project Plan or authorized task
  plan; no second plan, role parameter, launcher, state machine, config system,
  scheduler, or approval gate is introduced, and the flows reuse
  `start`/`send --no-wait`/`observe`/`capture`/`stop`, the existing
  `KAOLA_ACP_HEARTBEAT_HOST` receipt echo and the worker-event carrier.
- **A defective heartbeat prompt file is reported, not hidden (Issue #66).**
  `<repo>/.kaola/heartbeat-prompt.json` present but carrying no usable `body`
  string (wrong field name, wrong type, empty, unparseable, or bytes that are
  not UTF-8) used to deliver the same "none maintained" text as an absent file,
  which let a Host believe a prompt written under another field name was in
  effect. The delivered notification now names the file and the actual defect
  and the host holder logs `heartbeat_body_error`. One read supplies both the
  verdict and the body, so the body that passed the checks is the body
  delivered; delivery itself is unchanged, and the heartbeat-skeleton reference
  now names the `body` field.
- **Every platform can now be steered mid-run, and the receipt says exactly how
  (Issue #65).** A unified `steer` operation joins `send`/`wait`/`cancel`/`stop`
  on the same exact session/repo routing — no scheduler, no second stdin writer,
  no second lifecycle. Its scope is the ACP channel; over `pty` it is an honest
  `steer-unsupported-transport` rather than an unproven injection claim. The
  Agent chooses between two modes. `--steer-mode native` uses the platform's own
  mid-turn entry and exists where that entry really does: **Claude Code** and
  **Codex**. `--steer-mode interrupt` is the composite available everywhere — it
  cancels the running turn, confirms it actually stopped, and sends the text
  once as the next prompt on the same ACP session, so the conversation keeps its
  context. All nine platforms were verified live on the real installed CLIs
  through the generated Skill's own script: the steering instruction asked for a
  codeword planted in the first prompt, and the reply carried it back.
- **Steering never overstates what happened (Issue #65).** `steer_outcome`,
  `steer_consumed`, and `steer_confirmation` keep `injected` (the agent
  acknowledged consumption), `written` (flushed into a running turn on a
  platform that acknowledges nothing), `interrupted_and_resent`,
  `resent_without_interrupt`, `started_new_turn`, `not_consumed`, `unsupported`,
  `rejected`, and `unknown` apart. The composite is reported as
  interrupted-then-continued with `side_effects_possible`, never as injection,
  and the interrupted turn keeps its own request id, output, and terminal state
  next to a distinct `new_turn_request_id`. Nothing degrades silently: a
  platform without a native entry refuses a bare `steer` with
  `steer-mode-required` instead of interrupting on its own, an unconfirmed
  cancel sends nothing at all (`steer-cancel-unconfirmed`, outcome `unknown`, no
  blind retry), an idle session is never natively steered, a holder whose `start`
  never negotiated an ACP session id refuses `send` and `steer` outright with
  `no-acp-session` instead of writing a null-session frame and calling it
  `in_progress`, and a holder started before this release answers
  `steer-holder-outdated` having written nothing.
  `native_steering` also distinguishes `unknown` from `unsupported`, so an
  uninvestigated surface is never recorded as a proven absence.
- **Cancels are bound to the turn object they targeted (Issue #65).** `cancel` accepts
  an `expected_request_id`, and the composite steer uses it. Connections are
  served on separate threads and worker events start turns of their own, so a
  turn that ends on its own can be replaced between a caller's snapshot and its
  cancel — the cancel would then hit the newcomer while the receipt still named
  the old turn, and the steering text would be dispatched onto a turn nobody
  asked to interrupt. Now nothing is cancelled and nothing is sent: the outcome
  is `unknown` with `steer-turn-changed`. The wait is bound the same way, so a
  receipt never describes a different turn than the one it cancelled, and a
  dispatched turn's id comes from its own admission rather than from whatever is
  running afterwards. The binding is to the turn object, which is replaced and
  never reset in place, so the admission check, the outbound cancel, the wait
  and the receipt are all taken from that one turn while the lock is held —
  nothing downstream re-reads the current turn. `cancel_sent` distinguishes "we
  cancelled nothing" from "we asked the target to stop and cannot confirm what
  followed", and `side_effects_possible` is reported honestly for both. A late
  answer to a finished turn can no longer settle the turn running now.
- **The Claude Code bridge gained the native channel it was missing
  (Issue #65).** The vendored bridge now drives every streaming turn with
  `claude -p --input-format stream-json` and writes the prompt to an open
  stdin — the CLI's own mid-turn steering channel — and serves
  `_session/steering`, advertising it at the `initialize` top-level
  `_meta.steering`. The turn still ends on the CLI's `result`, which closes
  stdin, so the one-subprocess-per-turn lifetime is unchanged; as a side effect
  the prompt text no longer appears in the process argument list at all.
- **ZCode: engine-capable, protocol-surface unsupported — steered by the
  composite, and one real bug fixed (Issue #65).** ZCode 0.16.5 has a turn-steer
  queue internally but does not expose it on the `app-server --stdio` protocol
  the Runner drives (no steer method, a `.strict()` `session/send` schema with no
  delivery field, and a hard `-32010` while a turn is active), so it is steered
  through `--steer-mode interrupt` like the other six. Probing that surface also exposed a defect in
  our own adapter: `kaola-zcode-acp.py` overwrote the active turn's request id
  when a second prompt arrived, orphaning the original request and handing its
  completion to the newcomer. It now refuses the concurrent prompt with the same
  `-32010`, so one turn keeps one request id.
- **The ZCode Host post-dispatch contract is now operating instructions
  (Issue #65).** The generated main Skill states the action rules — hand the Host
  its real Runner identity, bind `KAOLA_ACP_HEARTBEAT_HOST` per worker `start`
  and check the receipt's `heartbeat_host`, dispatch with `send --no-wait` and
  read the acceptance, update the one `.kaola/heartbeat-prompt.json`, then end
  the turn naturally instead of sleeping, polling, or blocking — and a Host
  awaiting in-flight workers is explicitly not a stoppable idle worker. The new
  on-demand reference `references/zcode-host-dispatch.md` carries the runnable
  role-by-role procedure for the outer Agent, the Host, and the worker/carrier,
  including how to read a worker's real reply by its own identity and event
  cursor. Nothing here needs the Python source to be read.

## 0.3.5 — 2026-09-18

- **validate wall time cut with zero coverage loss.** The 24 contract suites in
  `./scripts/validate.sh` no longer run as one serial list: they run as two
  balanced lanes (each suite runs the identical command it ran serially, with
  its output replayed in the original order afterwards, and its per-suite log
  under the validate-owned `TMPDIR` root so the Issue #63 exit sweep still
  covers exactly this invocation's holders). Follow-suite teardown also closes
  its `follow` CLI pipes, removing the `ResourceWarning: unclosed file` noise
  from the run.
- **ZCode-host Skill ties heartbeat-prompt maintenance to worker events.**
  After each worker terminated/idle notification the host agent settles the next
  step, then updates `.kaola/heartbeat-prompt.json` — project info, pace, plans,
  coordination — so the next heartbeat pass carries the refreshed state
  (`templates/orchestrator/SKILL.md.tmpl`, regenerated into the shipped main
  Skill, and `docs/zcode-host.md`).
- **Bounded ACP `observe`/`status` receipts now fit real session state (Issue #64).**
  The ordinary `observe`/`status` receipt budget rises from 64 KiB (the capture
  budget) to its own `state_receipt_bytes` limit of 256 KiB in
  `templates/budgets.json` and `scripts/kaola-acp.py`: a realistic platform
  `session_meta` (Devin's is ~70.6 KB) and the stored `record` (~142.5 KB)
  now stay whole, so `session_meta.configOptions` `currentValue` — the
  configured model, e.g. `swe-2-max` — is readable from ordinary receipts
  instead of being swallowed by the whole-field `{omitted, bytes, sha256}`
  placeholder. The bound itself is preserved: a structure over 256 KiB is
  still summarised exactly as before with byte size and sha256 attestation,
  capture receipts and the PTY bound keep the unchanged 64 KiB
  `capture_receipt_bytes`, and `--full` and credential hygiene are untouched.
- **Interrupted validate runs no longer leak ACP holders (Issue #63).**
  `./scripts/validate.sh` now runs its suites under one validate-owned
  `TMPDIR` root and sweeps that root on exit, interrupt, and terminate
  through the new `scripts/kaola-acp-sweep.py`: an interrupted or early-failed
  run stops exactly the holders it spawned (matched by their
  `--record-dir`/`--socket` under that root, via the same admin-socket
  `stop` op a normal teardown uses) instead of leaving them re-parented to
  launchd with their mock agents. Foreign and concurrent runs hold their own
  random roots and are never matched or signaled.

## 0.3.4 — 2026-09-17

- **Event-driven heartbeat for a ZCode Host (Issue #62, Phase 2).** A ZCode
  Host session now has an event-driven heartbeat carrier instead of a periodic
  one: it registers no Routine, cron, or sleep loop, and no new daemon, port,
  scheduler, or second agent-stdin writer exists. A worker started with
  `KAOLA_ACP_HEARTBEAT_HOST` naming the host session notifies the ZCode Host
  holder from the worker holder's existing agent-exit and turn-end paths
  (`terminated`; one `idle` episode per ended turn with the agent alive — the
  600s idle watcher stays a non-business exit timer). The host holder stages
  events in one bounded in-memory list (cap 32, deduped by event id), records
  stage/delivery/confirmation in its existing event log, and delivers one
  ordinary `session/prompt` through the normal admission path: a busy host
  flushes at the next completed turn boundary, and `start --resume` redelivers
  unconfirmed events, so nothing is silently dropped. The delivered prompt is
  literal text — fixed structured event metadata plus the current full
  heartbeat prompt body read at delivery time from the consuming project's
  `.kaola/heartbeat-prompt.json` (fingerprint supplementary), plus one
  instruction to run a single full `PROJECT_RUNNER_HEARTBEAT_V2` pass; no
  worker raw output travels with it. The carrier is ZCode-Host-only: the op is
  refused on other platforms' holders and the CLI fails closed on non-ZCode
  and self targets. Other hosts' periodic heartbeats, the shared main Skill
  policy, and the heartbeat skeleton stay one unchanged set (the only Skill
  change is the minimal ZCode-host override documenting the carrier). See
  `docs/zcode-host.md`.

- **ZCode Host lifecycle foundation (Issue #62, Phase 1).** ZCode is now both a
  worker platform and a native skill-directory Host: `--runtime zcode` installs
  to `~/.zcode/skills`, and the live-verified workspace `.zcode/skills`
  discovery form works through `--skills-dir`. The generic external-ACP-client →
  ZCode Host → Project Runner → Worker entry reports distinguishable session
  identities: the adapter emits a credential-free `native_session_identity`
  update carrying the ACP session id and the native `sess_*` id the backend
  materialized/resumed, and `session/load` returns the adopted id plus its
  config options. Nested Host→Worker isolation reuses the holder child-record
  mechanism: a ZCode Host turn that starts an inner Worker (including another
  ZCode) records the inner holder into the outer holder's `children.jsonl`
  (runner-internal `KAOLA_ACP_CHILD_RECORD` env, forwardable as a fact, never a
  credential), so an inner stop never reaches the outer Host and the outer stop
  sweeps only recorded inner sessions — even after the outer agent died first
  (holder-lost `stop --force`). Credential boundaries and the denied-name env
  list are unchanged. See `docs/zcode-host.md`.

## 0.3.3 — 2026-09-17

- **Droid CLI worker platform (Issue #58).** Droid is now the ninth worker platform, using the
  native `droid exec --output-format acp` agent by default and the native tmux TUI as an explicit
  PTY fallback. Both transports default to Auto Model and bypass permissions: ACP applies
  `model=auto` and `autonomy_level=auto-high`, while PTY uses `--skip-permissions-unsafe` with a
  process-scoped `--settings` overlay that never writes `~/.factory`. Droid has no model or effort
  upgrade tier; reasoning effort is passed only when explicitly called. The new
  `acp_mode_config_id` manifest key makes ACP mode/permission option IDs manifest-driven while
  preserving byte-identical behavior for existing platforms. Orchestrator budgets were
  re-measured for the ninth roster entry, and live ACP/PTY verification, resume, bypass, and
  zero-residue evidence is recorded in `docs/droid-live-verification-2026-09-17.md`.

## 0.3.2 — 2026-09-16

- **Grok Bot bridge pin refreshed** (Issue #57). After the #53 and #56 changes
  were accepted on `main`, a new content/pin pair replaced the stale pre-#56
  target. The pin remains a separate branch so its machine-checked four-file
  delta is not mixed with Workflow archive commits; one thin private Skill is
  still the account-facing artifact. No account write or Marketplace publication
  is implied by this release.

- **Claude Code ACP bridge robustness edges** (Issue #53, follow-up to the #50 reviews). The
  vendored bridge removes its `.tmp` sibling when the session record cannot be renamed into
  place, and clears the per-session cancel flag when a turn starts so a `session/cancel` that
  lands between one turn's child exit and the next turn cannot report the next turn as
  `cancelled` or turn a genuine `--resume` failure into a cancel. The ACP holder now notes the
  process groups the agent spawned outside its own group (the bridge's detached `claude -p`
  children) while the agent is alive, records them as `agent_child_pgids`, and sweeps them on
  `stop` (`swept_child_pgids`, covered by `residual_pids`); a holder-lost `stop --force` sweeps
  the recorded groups too (`swept_pgids`). The bridge additionally appends each child's pid,
  group, and spawn time to the holder-named `KAOLA_ACP_CHILD_RECORD` file synchronously at spawn,
  so a child whose bridge died before forwarding its first line is still found (identity checked
  against the live start time, read from `ps` under `LC_ALL=C` so a non-English locale cannot blank
  the match); the variable never reaches the `claude` child or its tools, and the holder compacts
  the record to still-live entries at each agent start. `stop --force` is exercised offline for a healthy bridge, a bridge
  killed before its own shutdown, holder plus bridge gone, and both of those before the child's
  first output. Documented that
  `permit` under this bridge settles only the reported `tool_call` status because the `claude -p`
  child has no stdin and no `--permission-prompt-tool`.

- **Grok Bot install and UAT no longer depend on an impossible account-UI check** (Issue #56).
  The account Skill list (Settings > Plugins > Yours) does not expose an account-private Skill
  and a 1:1 Bot chat has no `/` discovery, so the guide's "verify the list shows exactly one
  Skill and `/` offers it" step could never be satisfied. That gate is gone, and the
  agent-facing guide and shared host reference now carry no account-UI discussion at all: only
  the one native save, the execution-target binding, the locator and load, the read-only
  preflight, and the real-use boundary. The attestation and worker `preflight` are stated to
  establish placement on the bound target, not live use; a real-use smoke on one session stays
  separately authorized and is never part of installation. Accepted `SKILL_EXPOSURE: PASS` is
  not reopened. Delivery is unchanged — one thin account Skill, no Marketplace, no second
  Skill, no new installation step — and `docs/grok-bot-host.md` records the reason once.

- **Root-start plus in-session Workflow is the ordinary ownership default** (Issue #52).
  For Workflow-backed work, start the runtime worker at the consuming project's canonical
  project root and ask that CLI to invoke `workflow-next` so its Workflow creates or
  recovers the child worktree. Linked-worktree starts and existing-run recovery stay
  Agent decisions on both PTY and ACP; adapters do not gain a `.kw/worktrees` refusal.

## 0.3.1 — 2026-09-16

- **Managed Skill install drift is advisory and repairable** (Issue #54).
  Runtime-generated Python bytecode no longer makes a receipt-owned installed
  copy look modified. A normal reinstall detects real payload drift, restores
  the generated Skill atomically, reports the exact path, and keeps the prior
  copy at a recoverable `.drift.*` sibling for Agent inspection. It does not
  add a runtime gate or make Skill directories read-only. Foreign paths remain
  outside the installer's ownership; uninstall still protects modified copies.

## 0.3.0 — 2026-09-16

- **ZCode default transport is ACP; PTY is unsupported by the bundled runtime** (Issue #51,
  Mission 4, owner correction 2, 2026-09-16). The shipped ZCode runtime cannot open a
  terminal UI (`Cannot find package '@zcode/tui'`) and headless `--prompt` requires
  `~/.zcode/cli/config.json`, so PTY is a product limitation, not a Runner defect, and the
  PTY live fallback is no longer an acceptance gate. `platforms/zcode.yaml` now has
  `default_transport: acp` and `acp_login_requires_pty: false`; login happens in the ZCode
  desktop App. Explicit `--transport pty` stays dispatchable only as a known-unsupported
  diagnostic entry; documentation and tests no longer promise it as a login or fallback
  channel. The flip was accepted only after a real Coding Plan ACP start/send/capture/stop
  on the default transport with no secret in any output, zero residual processes, and a
  clean repository (recorded in the bundle-51 UAT record).
  Same change, orchestrator review finding on `1d08a71`: only `respond(error)` and `log()`
  were redacted, while `session/update` notifications built from backend events
  (`model.streaming` text, `tool.updated` output, `turn.failed` messages) reached ACP stdout
  unredacted; a backend that echoes the inline credential inside an event payload could leak
  it into receipts and event logs. Redaction now happens once at the single outbound boundary
  (`send()`), covering results, errors, notifications and client requests without altering
  ordinary text; fake scenario `echo_events` reproduces the leak and is red on `1d08a71`.
  Cancel reporting is unchanged and honest: the stop is acknowledged at once, the native
  runtime finishes the in-flight response, and the Runner reports `cancel-unconfirmed` until
  the turn actually reports cancelled.
- **ZCode ACP bridges the desktop Coding Plan provider in memory** (Issue #51, Mission 4
  owner correction, 2026-09-16). Headless CLI 0.16.5 `app-server` fails `session/create`
  with `Model config is missing` because it resolves providers from `~/.zcode/cli/config.json`
  while the desktop App keeps the logged-in providers under `~/.zcode/v2/`. The adapter now
  reads `~/.zcode/v2/config.json` read-only, selects the one `enabled` `*-coding-plan`
  provider (Start Plan providers need the desktop captcha flow headlessly and are refused;
  plain pay-as-you-go providers are refused so no turn bills outside the plan), and passes it
  to the app-server as the protocol's own `runtimeModel` overlay (`apiKey: {source: "inline"}`,
  the desktop App's mechanism) on `session/create`, on `session/resume` as a fallback after a
  faithful resume, and on `session/setModel`. The credential never appears in ACP output,
  logs, receipts or on disk; `~/.zcode/cli/config.json` is never written; no auth environment
  is injected. `agentInfo._meta.zcode` reports secret-free provider facts (id, label, baseURL,
  plan-cache status, model ids, rejected providers). `session/set_config_option model` lists
  the provider's models and refuses any other provider. Contract suite grows to 19 tests with a
  desktop-registry fixture; the fake app-server now rejects a create without the overlay.
  Three live findings repaired in the same change: `session/stop` is sent as a request (the
  CLI fast-paths only requests past its processing queue), `session/list` converts native
  epoch-millisecond timestamps to RFC 3339 so `start --continue` can pick the latest native
  session, and a faithful `session/resume` is followed by a `session/setModel` re-registration
  of the same provider with the session's persisted model (a fresh app-server otherwise answers
  `ZCODE_RUNTIME_MODEL_UNAVAILABLE` on the next send). Live UAT on the recording Mac: sentinel,
  provider/model identity (`builtin:bigmodel-coding-plan\GLM-5.3`), yolo read-only tool,
  `--continue`/`--resume` with conversation memory, two isolated concurrent sessions, exact stop
  with zero residue, and private-file identity all pass; cancel is acknowledged immediately but
  CLI 0.16.5 finishes the in-flight model response before reporting the turn (native latency,
  measured without the Runner); the bundled runtime cannot open its TUI (`Cannot find package
  '@zcode/tui'`) and headless `--prompt` needs `~/.zcode/cli/config.json`, so the PTY fallback
  gate could not pass on that Mac, so this intermediate candidate kept
  `default_transport: pty`; the later owner correction above moved it to ACP. Independent review
  round 1 (five should-fix, no blocker) closed in the same change: backend error objects and
  stderr diagnostics are redacted of the plan credential (a backend that echoes request
  input can no longer leak it onto the ACP channel); a failed `session/load` unregisters
  the session instead of letting a later prompt silently create a new one; a resumed
  session whose persisted model cannot be read fails closed instead of taking the provider
  default; a registry with two enabled Coding Plans fails closed (`HUMAN_DECISION_REQUIRED`)
  instead of picking dict order; the overlay builder never substitutes a model; the
  resume-with-overlay fallback is now covered by a fake scenario; and the tier preset names
  no longer embed a device-specific model. Contract suite 23/23.
- **ZCode skip-all permission mode is yolo on ACP and PTY** (Issue #51, Mission 4
  owner correction). Installed CLI 0.16.5 `--help` lists `--mode` as Permission
  mode (`build|edit|plan|yolo`, default yolo for `--prompt`); the packaged
  engine states "Yolo mode bypasses permission prompts" and maps
  `bypassPermissions`/`dontAsk` to `yolo`. PTY no-flag start now passes
  `--mode yolo`; ACP skip-all remains `yolo`. This intermediate candidate
  still defaulted to PTY; the later owner correction above moved it to ACP.
- **ZCode ACP live protocol repair** (Issue #51, Mission 4). CLI 0.16.5 asks
  `session/requestRuntimePreferences` during `session/create`; the adapter now
  answers protocol defaults and never reads Settings or forwards auth headers.
  At that point default transport stayed PTY: headless `app-server` required an
  explicit model provider in `~/.zcode/cli/config.json` (superseded by the
  in-memory Coding Plan bridging entry above).
- **ZCode as the eighth CLI worker platform** (Issue #51, Mission 3). Adds
  `platforms/zcode.yaml` and `scripts/adapters/zcode.sh`, generates
  `zcode-kaola-project-runner` from the shared worker template, and reuses the
  existing ACP holder with schema-v3 receipts. ACP command is Skill-relative
  `python3 $SKILL_DIR/scripts/kaola-zcode-acp.py` (the Runner-owned translator
  from Mission 2; `william0wang/zcode-acp` remains a protocol reference only).
  The renderer ships that adapter only inside the ZCode worker. Runtime paths
  are explicit `KAOLA_ZCODE_ENTRY` + `KAOLA_ZCODE_NODE` and fail closed; there is
  no PATH search for `zcode`. Default transport stays PTY; `--transport acp` is
  available; login remains a PTY act. `acp_env_allowlist` is empty. Offline
  harness: `tests/contract/test-issue-51-runner-integration.py`.
- **Claude Code ACP through a vendored, pinned bridge; ACP is now Claude Code's default
  transport** (Issue #50, Missions 1–4; the live subscription gate passed on the recording Mac on
  2026-09-16 and `--transport pty` stays the explicit fallback and login channel; the round-1
  review fixes exempt the rendered bundle copy from whitespace checks via a root `.gitattributes`,
  add `git diff --check` to `validate.sh`, refuse path escapes in the Skill-relative token, write
  the bridge session store atomically, and document `~/.claude-code-acp/sessions.json`). A live finding
  fixed in the fork: the CLI exits 143 on SIGTERM, which upstream's resume fallback treated as an
  expired session — a cancelled `--resume` turn was re-run as a fresh conversation and the
  persisted session id was cleared; the fork now reports `cancelled` and keeps the id, and a
  cancelled first turn persists the id the CLI announced. `vendor/claude-code-acp/`
  vendors `harukitosa/claude-code-acp` at commit `6c20f2802e390c80b0542247c6b9738e11efdc11`
  (MIT, `LICENSE` verbatim, `UPSTREAM.md` with the complete modification list and a hashed
  upstream inventory) with a committed single-file `dist/index.js` bundle whose derivation
  `kaola-dist.py --check` re-verifies offline. Fork changes: an exact absolute Claude binary
  (`CLAUDE_ACP_CLAUDE_BIN`/`CLAUDE_BIN`, never PATH), per-session `mode`/`model`/`effort`/`fast`
  options mapped onto every `claude -p` subprocess, native `session/list`/`session/resume`,
  process-group cancel and shutdown, credential stripping with everything else inherited, masked
  logs, and per-turn temp cleanup. The Claude Code manifest now runs
  `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`: `kaola-acp.py` resolves the
  `$SKILL_DIR/scripts/` prefix to an absolute path (installed Skill, else checkout layout;
  `acp-bridge-missing` when neither exists), passes the Runner-resolved exact `claude` path to the
  bridge, and reports `bridge`/`runtime_binary` facts on `preflight`/`start`; the renderer ships
  the bundle, its derivation record, `LICENSE`, and `UPSTREAM.md` inside the Claude Code worker
  only. Two offline harnesses (`tests/contract/test-issue-50-claude-acp-bridge.py`,
  `tests/contract/test-issue-50-runner-integration.py`) drive the bridge and the real Runner
  entry points against `tests/contract/fake-claude.py` with no network and no account. The npm
  registry package of the same name and `npx` are never referenced; PTY stays the explicit
  fallback and the login channel.
- **Pre-UAT bounding correction** (Issue #49 final delta review of R2/P2; Mission 10; fresh
  content commit R3 and pin commit P3). PTY `kaola-observation.py bound_observation` is now
  idempotent and monotone: the status/start path bounds twice (`build`, then `status-view`), and
  the second bound merges the existing `truncated` block instead of replacing it, so the original
  `child_processes` total/count/sha256 and `raw_current_frame` total/sha256 survive while the
  newest frame lines and the process excerpt stay. The wrapper fields `result` and (grok)
  `legacy_ownership` are added inside `status-view` before its bound, so the emitted `status`/
  `start` line, newline included, stays within `capture_receipt_bytes` even on a 400-column pane;
  ACP `bound_state_receipt`/`bound_capture_receipt` measure the emitted line the same way and
  record a summary before cutting its field, so no summary entry can push a receipt over. Tests:
  repeated bounding, the real build-to-status path with 1 500 child processes and 400×320 frames,
  final wrapper serialization, ACP pending-permission limits. `kaola-locate.py register` now
  requires `--expect-revision` (`expect-revision-required`; a receipt without a 40-hex accepted
  revision is `locator-registration-unreadable`), and origins with a second `@` in the host or a
  `?`/`#` query or fragment are `origin-form-unsupported` with nothing echoed. Budgets and
  `templates/grok-golden/` unchanged.
- **Pre-UAT closure of the Issue #49 re-review notes** (Mission 9; fresh content commit R2
  and pin commit P2). Ordinary `observe`/`status` receipts are now really bounded on both
  transports by the shared `capture_receipt_bytes` budget: PTY through
  `kaola-observation.py bound_observation` (newest `raw_current_frame` lines and first
  `child_processes` entries kept; `truncated.fields` with kept/total sizes and sha256;
  `snapshot_id`/`pane_revision` from the full frame), ACP through `bound_state_receipt` in
  `kaola-acp.py` (large structures summarised by size and sha256; `pending_permissions` keeps
  its newest entries); only `capture --full` stays unbounded (behavioural tests, including a
  live private-tmux path). `kaola-locate.py register` now requires `--target local|cloud` and,
  after validating, atomically writes a credential-free device-local registration receipt
  `.kaola-project-runner-locate.json` beside the owner-chosen link (resolved root, declared
  target, host fingerprint, accepted revision, schema); every later call compares the running
  host fingerprint, declared target, root, and HEAD with it and fails closed
  (`locator-not-registered`, `host-fingerprint-mismatch`, `target-mismatch`,
  `registration-root-mismatch`, `registration-stale`); a refused registration leaves link and
  receipt unchanged. Origins are accepted only in explicit `https://`, `ssh://`, or scp forms
  (`origin-form-unsupported` for a bare `github.com/...` or local path). The pin gate now
  machine-enforces the P delta (only `accepted-revision.json` plus the three generated
  `hosts/grok-bot/` products; bridge diff exactly the accepted-revision line), so a rebased,
  squashed, or `main`-merged pair fails `--require-pinned`; a label may not masquerade as a
  release. Docs: never rebase/squash an accepted R/P pair (fresh R/P when `main` moves),
  release = tag at R then P after the tag, rollback = new pin naming an older R; cloud
  registration passes `--target cloud --expect-revision R`; session field is presence on the
  reachable tmux server only; `bridge.json` content-stage null fields; trusted-host Git-index
  edge cases stated as bounded; UAT registers into an owner-selected bin directory on PATH and
  says how to restore the installer-managed link. Budgets and `templates/grok-golden/` unchanged.
- **Grok Bot bridge: honest two-commit content/pin model** (Issue #49 review of `fb65c51`,
  Mission 8). `templates/grok-bot/accepted-revision.json` now declares a `stage`: `content`
  (the content commit R; the bridge carries an explicit "none yet" line, `bridge.json` says
  `saveable: false`) or `pinned` (the pin commit P that follows R; `commit` = R plus exactly one
  of `release` or a plain-text `label`). At the pinned stage `render-skills.py --check`/`--write`
  and `kaola-grok-bot-verify.py --repo` run a pin gate against the Git checkout (R exists, is an
  ancestor of HEAD, is a content-stage commit, holds `scripts/kaola-locate.py`,
  `skills/kaola-project-runner/SKILL.md`, and every worker `SKILL.md` + `runtime-tmux.sh`; a
  named release is a tag at R); `--require-pinned` is the gate for P. The bridge is saved from P
  and every execution target is checked out clean and detached at R; the Mac `main` checkout may
  hold untracked Workflow records, so UAT uses an owner-selected clean checkout or worktree.
- **Locator hardening and honest attestation wording.** `kaola-locate.py register` validates
  origin, optional `--expect-revision`, clean state, and the link path before it touches
  anything; a refused registration leaves an existing locator unchanged. `--target` is documented
  as the Agent's declaration (echoed, never inferred; compare `host.fingerprint` with the value
  recorded at registration), `session.present` as tmux presence only (ownership is the worker
  preflight's proof), and `root.path`/`project.path` as real local paths that never enter the
  account Skill.
- **Bounded ordinary ACP capture.** `kaola-acp.py capture` without `--full` now applies the
  shared `capture_receipt_bytes` budget: the oldest `events`/`tool_calls` are dropped and a
  `truncated` block records kept/dropped/total counts, the untruncated stream's byte size and
  sha256, and the `--full` hint (behavioural test against the mock ACP agent).
- **Adapter and test tightening.** The `grok-bot` adapter's product functions take no platform
  manifest (the guide uses `<platform id>` instead of the first worker); drift tests assert the
  baseline render succeeds before mutating; the script-source and wrong-move heuristics exempt a
  sentence only where a negation precedes the matched phrase. Budgets unchanged.
- **Progressive disclosure** is now a locked, platform-neutral invariant with measured byte
  budgets (`templates/budgets.json`: discovery descriptions ≤ 320 chars, main Skill ≤ 16 KB,
  each worker ≤ 12 KB, each reference ≤ 8 KB, Grok Bot bridge ≤ 2.5 KB, guide ≤ 8 KB, locator
  receipt ≤ 4 KB, ordinary capture receipt ≤ 64 KB). `render-skills.py --check`/`--write`
  refuse any over-budget product and name the surface and size; `tests/contract/
  test-progressive-disclosure.py` proves the activation boundaries structurally (main embeds
  no worker, each worker is separate, references are linked and never inlined, scripts are
  executed and never read, no product is a substring of another). Ordinary PTY `capture` is a
  bounded receipt (newest bytes plus a truncation marker carrying the sha256 of the whole
  stream, via `kaola-observation.py bound-text`); an explicit `capture --full` stays unbounded.
- **Grok Bot** host reduced to **one thin bridge Skill** (Issue #49 owner corrections,
  2026-09-16; research `NO_SUPPORTED_PATH` for automated account-Skill creation). The eight
  single-Markdown account Skills, `private-skills.json`, the Local Computer runtime copy,
  `--runtime grok-bot`, `KAOLA_GROK_BOT_HOME`, and `scripts/kaola-grok-bot-package.py` are
  **removed**. `render-skills.py` now emits only `hosts/grok-bot/kaola-project-runner.md` (the
  bridge, from `templates/grok-bot/bridge.md.tmpl` + `accepted-revision.json`),
  `bridge.json` (fingerprints, accepted commit/release), and `INSTALL.md` (one account write,
  first configuration, read-only Mac UAT). The bridge names the repository, expected origin,
  accepted 40-hex revision, the locator command, and the two canonical entry paths; it binds
  the execution target first (Local Computer or cloud Agent Computer), never assumes one
  target can reach the other, never installs or updates the Mac from the cloud, and loads only
  the main Skill and one selected worker from the verified checkout on that target. New
  `scripts/kaola-locate.py` is the device-local locator and fail-closed host-target
  attestation (`kaola-project-runner-locate`, a re-registerable bin link following the
  installer's `--bin-links` convention): bounded receipt with target kind, host fingerprint,
  ROOT identity (normalised origin, HEAD, clean), consumer project identity, worker script
  under the same ROOT, exact session; refuses cross-host paths, origin/revision mismatch,
  dirty trees, and never handles credentials. `kaola-grok-bot-verify.py` proves the bridge
  shape, budgets, absence of canonical/path/credential content, manifest identity, and (with
  `--repo`) generated state. Docs, orchestrator Hosts section, and
  `references/grok-bot-host.md` describe the bridge flow, target binding, attestation, and the
  read-only Local Computer UAT boundary. Still seven platforms; `templates/grok-golden/`
  frozen. See [Grok Bot host](docs/grok-bot-host.md).

## 0.2.3 — 2026-09-15

- Every Project Runner heartbeat now matches authorized idle workers to executable work that can
  safely run in parallel. Suitable work is dispatched without creating busywork or expanding
  authorization merely to fill capacity.

## 0.2.2 — 2026-09-15

- Main orchestrator Skill `kaola-project-runner` (issue #47): prefer the selected authorized
  Workflow sync/merge when a PR is not required; a PR is not opened merely for handoff when
  that sink is suitable. If PRs exist, advance actionable ones first on contested suitable
  capacity; other authorized work continues in parallel across permitted CLIs. A blocked PR
  keeps an owner and next action without a global hold.

## 0.2.1 — 2026-09-14

- Default local install is now an owned standalone copy (issue #46). `--method link` remains
  the explicit maintainer/development choice. Owned source links migrate to copies; foreign paths
  and modified copies stay protected. The main Skill tells consumer-project agents to keep
  authorization, heartbeat, and run facts in the consuming project and to treat the Project Runner
  checkout, templates, generated files, and installed Skill payload as read-only unless a human
  assigned Project Runner development.

- Main orchestrator Skill `kaola-project-runner` (issue #44): completion stops leftover idle
  owned sessions including ACP (idle is not keep-alive). A stop boundary such as "run until
  5pm" / "until done" / "until CONDITION" blocks new tasks and new issues; time-up is not
  drop-everything. The default end of a run still finishes in-hand issues, merges
  worktrees/branches with no leftover branch tails, and leaves the workspace clean per Kaola
  Workflow. Only an explicit "stop here, continue later" skips that cleanup and may leave
  recovery-preserving unfinished branches.

## 0.2.0 — 2026-09-14

- Generated main orchestrator Skill `kaola-project-runner` (display name Project Runner, issue #41).
  It is a control-plane Skill rendered from `templates/orchestrator/` through the existing
  `--write`/`--check` byte inventory, not an eighth platform: no platform manifest or transport
  adapter. The installer puts it on every `--runtime` / `--skills-dir` destination; `--platform`
  still filters workers only; `--no-orchestrator` skips the main Skill. Worker Skills remain
  transport-only, with an optional pointer to the main Skill name. `templates/grok-golden/` is
  unchanged.

- Fixed the main Skill description YAML encoding so descriptions containing colon-space load
  correctly in standard YAML parsers; added regression coverage. Removed an expired credential
  from the current archived repository URL (published history is unchanged).

- ACP `permit`/`cancel` (and the `key escape`→cancel alias) accept an optional
  `--expected-holder-instance-id` binding (issue #39). Each holder process mints an opaque
  random `holder_instance_id` at construction — immutable for that process, never restored
  from `record.json` or the native session id, never derived from the PID — exposed on
  `record.json`, `status`/`observe`/`start` receipts, `kaola-acp-list/1` rows, and top-level
  on every `kaola-acp-view/1` payload (view plus follow snapshot/delta/heartbeat). When
  supplied — including an explicit empty value — the holder compares it under the settlement
  lock before any permission settlement, pending-permission cancellation, turn mutation, or
  outbound cancel, even when no permission/turn is active. A mismatch returns `error.code`
  `holder-instance-mismatch` with `expected_holder_instance_id` and the actual
  `holder_instance_id` in the error object plus `mutation_status` `not_started` /
  `mutation_performed` `false`, writing nothing to the agent. Omitting the flag keeps legacy
  unbound behavior; the value is Runner envelope only and is never forwarded into native ACP
  method params.

## 0.1.0 — 2026-09-14

- Per-run model presets and explicit Fast opt-in across all seven platforms (issue #34). Every
  manifest now declares `default` and `upgrade` presets: Claude Opus High → Fable High, Codex
  `gpt-5.6-sol`/`high` → `gpt-6-astra`/`high`, Grok 4.6 xhigh (upgrade identical), OpenCode keeps the
  CLI-native opening model on both tiers (no Runner override), Kimi `kimi-for-coding`/`max` → `k3`/`max`,
  Cursor `cursor-grok-4.6-xhigh` → `claude-fable-5-1-high`, Devin `swe-2-max` → the Fusion High combo
  model. Selection precedence: explicit `--model` wins, then `--tier`, then the default preset; a bare
  `--model` does not inherit preset effort, and effort/Fast-encoded model IDs get no invented extra
  configuration calls. `start`/`preflight` accept `--tier default|upgrade` and `--fast on|off` on both
  transports — ACP applies model → effort → Fast through manifest `acp_*_config_id` options (Codex adds
  `fast-mode`) and PTY uses native argv/`-c service_tier`/env mechanisms; `--fast on` is opt-in only and
  reports `resolved_fast: "unsupported"` where no native mechanism or advertised fast variant exists.
  Claude Code applies Fast through a process-scoped `--settings '{"fastMode": ...}'` launch pin —
  `false` by default and `true` on explicit opt-in, passed verbatim; the native CLI determines
  model support, effective reports `unknown` without native evidence, and the selected model is
  never changed to satisfy Fast.
  `--resume`/`--continue` without selection flags now preserves the saved native session selection
  (`resume-preserved`) instead of re-applying the preset; supplying any selection flag re-applies it.
  Receipts carry `model_selection`, `requested_tier`/`requested_fast`/`resolved_fast`, and per-option
  `config_application` records; a rejected or unadvertised `set_config_option` is a reported
  limitation, never a session failure or transport gate, and nothing escalates models automatically.
  Manifests may declare `acp_init_meta` (`key=value` pairs sent as `clientCapabilities._meta`
  during `initialize`): Cursor negotiates `parameterizedModelPicker=true`, which makes its ACP
  surface advertise separate `model`/`effort`/`fast` options — base model IDs, effort
  `low..xhigh`, and fast `"true"`/`"false"` strings — instead of fixed variant descriptors.
  `acp_model_map` (`picker-id=acp-option-value;...`) then decomposes resolved PTY picker IDs onto
  the advertised model value for the same model while the ID's effort suffix travels through the
  effort option and Fast through `acp_fast_values`-converted fast values — Cursor resolves
  `cursor-grok-4.6-xhigh` to `model=grok-4.6`, `effort=xhigh`, `fast=false` exactly, and
  `claude-fable-5-1-high` to `claude-fable-5-1`/`high`/`false`. Fast conversion is
  platform-specific (`acp_fast_values`: Cursor `off=false,on=true`; Codex keeps `off`/`on`). The
  `fast` receipt's `effective` now reflects proven native state only: a rejected fast config option
  or an unapplied fast-variant model ID reports `unknown`, and an applied model value's own
  descriptor (`[..,fast=true]`) is reported as the effective evidence with any request conflict
  noted — never a false on/off. ACP `preflight` additionally reports `advertised_config_options`
  (id, type, current value, and allowed values) from `session/new`.

- ACP `observe`/`status` `session_meta.configOptions` now reports the current native
  configuration instead of the initialization snapshot: successful
  `session/set_config_option` results and `config_option_update` notifications merge the
  native-returned option list, `configured_options[*].current_value` attests the adapter's
  reported `currentValue`, and the session-establishment baseline stays visible as
  `initial_config_options`. Failed, timed-out, or fact-free responses never fabricate
  current configuration (#33).

- The Skills are now runtime-neutral Agent Skills (issue #36): SKILL.md frontmatter and universal
  instructions use generic controlling-Agent wording (Codex-specific display metadata stays in the
  optional `agents/openai.yaml`), and every invocation example resolves the installed Skill's
  absolute `"$SKILL_DIR/scripts/runtime-tmux.sh"` path so a copied Skill works outside the
  checkout, under destinations containing spaces, and without repository scripts or global
  `kaola-acp` links. `install-local.sh` gains `--runtime codex|claude-code|cursor|devin` for
  verified consuming-runtime skill directories, `--skills-dir ABS_PATH` for arbitrary destinations
  (mutually exclusive), `--method link|copy` for symlink development installs versus standalone
  copies with per-Skill ownership/content receipts under
  `<skills-dir>/.kaola-install-receipts/` (identical owned content is a no-op; only unmodified
  owned installations are replaced or removed; edits and foreign paths are preserved), and
  `--bin-links` control over the optional `$HOME/.local/bin/kaola-acp*` helper links — on by
  default only for the Codex runtime destination and never removed by an ordinary uninstall.
  `scripts/validate.sh` now validates the Agent Skills format with the repository-owned
  `scripts/validate-skill.py` instead of an external Codex-installed validator, and the whole
  suite runs under a temporary HOME without `.codex` or `CODEX_HOME`.

- ACP status/observe now report a recorded, fully exited normal stop as `stopped`,
  preserving `holder-lost` for unexpected loss or remaining process evidence (#32).

- All Skills now carry the same end-of-delegation and resume guidance (issue #30): a finished
  reply (`end_turn`, idle frame, successful receipt) is never task completion; when delegated
  work is delivered the Agent is recommended — never forced — to `stop` exactly-owned runtime
  resources (PTY child/relay/tmux; ACP `session/close` plus holder/agent exit), while keeping
  already-available resume facts such as the native session ID. `stop` never deletes history;
  missing identifiers never block it; resume stays the Agent's choice among
  `--resume <native-id>`, `--continue`, or a fresh session with existing records. Guidance is
  prompt-level only — no automatic shutdown, watchdog, completion classifier, or mandatory
  checkpoint was added, and platform resume claims stay limited to each platform's verified
  capability.

- Codex CLI is the seventh platform (issue #28). Default transport is ACP over the pinned
  `npx --yes --package @openai/codex@0.153.4 --package @agentclientprotocol/codex-acp@1.11.0
  codex-acp` adapter; `--transport pty` runs `codex --cd <repo> --no-alt-screen`. Runner default
  model is `gpt-5.6-luna` at `low` reasoning effort, applied on both transports unless the
  caller passes `--model`/`--effort` (ACP configIds `model` / `reasoning_effort`; PTY
  `--model` / `-c model_reasoning_effort`). Permission modes map `read-only` / `agent` /
  `agent-full-access` to the same ACP mode ids; PTY maps them to `read-only`+`on-request`,
  `workspace-write`+`on-request`, `danger-full-access`+`never`. Default is
  `agent-full-access`. The ACP mode IDs are upstream pass-through — `read-only` is Codex's
  native "Ask for approval" (workspace-write + on-request; permits workspace writes), `agent`
  is "Approve for me" (auto_review) — while PTY `read-only` is a strict OS read-only sandbox;
  `configured_options` receipts carry the adapter's own display names/descriptions as
  evidence. ACP capability detection now treats an advertised `{}` object as
  supported, and `continue` follows `session/list` `nextCursor` across all cwd-filtered pages
  before selecting the latest `updatedAt` (compared as RFC3339 instants; missing/invalid
  timestamps and distinct IDs at equal instants report factual ambiguity; duplicate
  identities across pages collapse). `CODEX_PATH` selects the Codex binary for the ACP
  adapter; no global Codex config is written. `cancel` now returns its turn receipt when the
  client omits `--timeout` instead of losing the reply to a handler crash.

- ACP watch projection now holds up on real sessions: chunks without `messageId` (all Grok
  chunks) join one message instead of one row per token; thinking tail, tool content, timeline,
  and whole-view caps are enforced in memory and on the wire (`truncated=true`), with the newest
  tools/messages kept; `EventLog` caches the oldest cursor instead of re-reading every event file
  on each `view`/follow fan-out. `follow` closes after `eof` and the CLI exits; a follower that
  attaches after agent exit gets snapshot then `eof`; `--format text` prints each message/tool
  once. Schemas `kaola-acp-view/1` and `kaola-acp-list/1` are unchanged.

- ACP holder `permit` / `cancel` / `stop` now settle each permission `request_id` at most once
  under the same lock as prompt admission (issue #25). A second settler on that id is the
  structured fact `unknown-request` and does not write another JSON-RPC result to agent stdin.
  `session/cancel` is unchanged. L0 `send --wait` keys are unchanged.

- OpenCode default ACP start stays `opencode acp` with no skip-all (issue #24). There is no
  measured ACP skip; PTY `--auto` via `--transport pty` is the documented bypass. Do not invent
  auto-permit or `OPENCODE_PERMISSION` skip.

- Implemented ACP Watch `list`/`view` (issue #26): host-wide `kaola-acp list [--platform P]
  [--repo ROOT]` emits `kaola-acp-list/1`; `kaola-acp <platform> view --repo … --session …
  [--since CURSOR]` emits typed `kaola-acp-view/1`. EventLog reloads max cursor from live plus
  rotated `.jsonl.1–.3`. `install-local.sh` installs owned `$HOME/.local/bin/kaola-acp` and
  `kaola-acp-holder` symlinks. L0 `send --wait` keys are unchanged. `kaola-tmux.sh … view`
  returns `view-unsupported`.

- Implemented ACP Watch local `follow` (issue #27): `kaola-acp <platform> follow --repo …
  --session … [--since CURSOR] [--format text]` streams NDJSON `snapshot`/`delta`/`heartbeat`/
  `eof`/`error` on a long-lived Unix connection. Snapshot/delta reuse `kaola-acp-view/1`.
  The follow FD is read-only after the first op; a 256-line per-follower queue drop emits
  `follow-dropped` without pausing agent stdio. Killing follow does not stop holder/agent.
  `kaola-tmux.sh … follow` returns `follow-unsupported`.

- Documented the ACP Watch Surface design freeze (`docs/acp-watch/`, issues #25/#26/#27):
  human `list`/`view`/`follow` beside the existing holder, at-most-once permit, no HTTP/SSE
  and no second agent-stdio client. #25, #26, and #27 are implemented.

- Default `start` now enables each platform's measured skip-all permission mode on both
  ACP and PTY (issue #22): Claude `--permission-mode bypassPermissions` / ACP `mode=bypassPermissions`,
  Devin PTY `--permission-mode dangerous` and ACP `mode=bypass`, Kimi PTY `--auto` and ACP `mode=yolo`,
  Cursor `--yolo` (including `cursor-agent --yolo acp`), OpenCode PTY `--auto`, Grok PTY
  `--always-approve` and ACP `grok agent --always-approve stdio`. OpenCode ACP has no skip
  argv (`opencode acp` rejects `--auto`). Workspace-trust flags are unchanged and are not this
  bypass. `permit` stays available when an agent still emits `request_permission`.

- Promoted the Runner v2 dual-transport design to v0.3 (implementation baseline) from the PoC
  results: native-ACP platforms (Grok, Kimi, Cursor, Devin, OpenCode) default to `acp`, Claude
  Code stays `pty`; `--continue` resumes via `session/load` from the session record; permission
  gating stays mock-verified with a conditional live acceptance; production work is split into
  manifest/template (A), dispatch/packaging (B), and per-platform live verification (C). Moved the
  issue #7 / #8 design records from the repository root into `docs/decisions/`.

- Added a prototype ACP transport alongside the tmux/pty path (issue #15 PoC):
  `scripts/kaola-acp.py` + `scripts/kaola-acp-holder.py` drive `grok agent stdio` and
  `kimi acp` sessions with blocking `send --wait` receipts, `permit`, `cancel`, and
  schema-v3 `mutation_status` facts. Not wired into manifests or the installer; see
  `docs/poc-acp-transport-2026-09-11.md` for measured results (~12× fewer tokens per
  session cycle than the pty path).

- Added Devin CLI as the sixth Project Runner platform, with deterministic Skill generation and
  local installation, Adaptive model selection and runtime verification, `auto` permission-mode
  launch, direct prompt/key transport, exact continue/resume/stop support, honest unsupported and
  session-ID feedback, and evidence-only activity, model, usage, and snapshot observations.

- Added optional Kaola Workflow advice to all five Runner Skills: suggest task-appropriate startup,
  finalization supervision, delivery verification, and task-owned cleanup while the Agent retains
  every orchestration choice and Runner transport remains unchanged.

- Replaced normal relay quiesce/prepare/fence/submit transactions with live observation and one direct
  PTY transfer for send, answer, key, and graceful stop. Action receipts are compact, legacy relays
  require an Agent-selected exact-session restart, and uncertain partial writes remain truthfully
  unknown instead of blocking the task behind recovery metadata.
- Simplified Runner transport for Issue #9: model catalogs, visible editor/activity evidence, and
  changed observations are reported to the controlling Agent instead of blocking communication.
  Cursor launch no longer materializes project files, and force stop now ends only the exact owned
  tmux session without process classification or descendant sweeps.
- Reduced validation to direct start, send, read, connection, and exact-stop proof; unusually long
  Runner procedures are treated as overengineering evidence and must be simplified. The default
  validator no longer runs the historical fake-runtime matrix.

- Added verified per-run main-model selection for all five runtimes: explicit user override first,
  otherwise a declared Runner default, with catalog resolution, literal launch parameters,
  actual-model evidence, resume re-verification, and no global-config mutation or communication gate.

- Reframed all five active Project Runner Skills as communication-only drivers. Bare invocation no
  longer implies `workflow-next`, task-mode selection, a 15-minute heartbeat, lifecycle classification,
  Cursor command materialization, or any other orchestration policy.
- Added Agent-selected native key transport (`up/down/left/right/enter/escape/tab/backtab/space`) with
  exact byte fingerprints. Kimi 0.39.1 was revalidated end-to-end through Runner-only
  trust-selection, prompt delivery, reply readback, and exact-session shutdown.
- Made optional Kaola carriers, runtime health, and Cursor authority/materialization preflight facts
  advisory so missing Workflow setup cannot block starting a usable CLI communication channel.

- Made interaction evidence-first across Grok, Claude Code, OpenCode, Kimi CLI, and Cursor CLI:
  raw frames and exact tmux/process/relay facts go to the controlling agent, while coordinates,
  fixed placeholders, editor/activity/approval labels, and worker counts no longer authorize or
  block generic send/stop. Skills now teach observe, agent decision, prompt transfer, response
  reading, retained-draft recovery, and durable Workflow verification.
- Removed evidence-derived hard gates from agent-directed transport. `send` and `stop` no longer
  require a snapshot; a caller-supplied old observation is reported through `action_time_snapshot`
  and `observation_changed:true` instead of `stale-snapshot` refusal. Later-output barriers, draft,
  approval, activity, process counts, Git, and Workflow interpretations remain evidence only.
- Removed the Cursor `cursor_x=2` input-origin blocker and the equivalent coordinate authority from
  shared placeholder interpretation. Added the real Cursor v2026.08.25 x=0 frame as evidence.
- Made mutation-refusal recovery receipts truthful: `restored:true` now requires proof of resumed
  child/process group, restored pane input, a responsive relay, and released lease;
  otherwise the receipt reports `restored:false` with explicit evidence.
- Added schema-v2 observations and a managed nested-PTY relay that record independent
  editor/approval/visible-work facts, byte/input/output/resize revisions, recovery evidence, and
  Claude whole-editor replacement receipts without turning those facts into runtime state authority.
- Added exact outer-PTY fence outcomes without replay, escaped-descendant containment, and pre-write
  terminal-control reporting with bracketed-paste-only LF/TAB handling. Prepared send/answer payloads
  retain byte-level fingerprint receipts across real newlines, TABs, and terminal soft wraps.
- Consolidated all five generated Skills on the shared relay control plane while keeping Grok's
  live-proven prompts, task modes, scheduling, claim handoff, lifecycle, and golden source bytes
  unchanged; generated transport wording is applied through an exact reversible overlay.
- Made the legacy Grok validation use its own explicitly numbered tmux server, so a user's
  `base-index` and `pane-base-index` cannot change the verdict.
- Made Claude Code decisions, approval surfaces, retained editors, and later-output barriers visible
  to the controlling agent without blocking that agent's chosen follow-up transport.
- Made execution cadence caller-controlled across every runner Skill; runtime-native recurring
  support no longer gates an outer Codex heartbeat or scheduler.
- Added the live-proven Claude Code launch profile, stable tmux pane targeting, dynamic-title TUI
  detection, and native approval classification.
- Initialized Kaola-Workflow documentation structure.
