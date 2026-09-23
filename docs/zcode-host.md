# ZCode Host (Issue #62)

Phase 1 of Issue #62 makes ZCode a first-class **Host** of the Project Runner
Skills: a consuming runtime that natively discovers and loads the generated
Skills, plus the generic ACP entry that lets any external ACP client drive
Runner sessions end to end. Phase 2 adds the event-driven heartbeat carrier
(see below); the live real-run E2E remains a separate frontier.

## The two faces of ZCode

- **Worker platform** (`--platform zcode`): ZCode.app is one of the ten
  worker target CLIs a Runner session controls. Unchanged by this phase.
- **Native skill-directory Host** (`--runtime zcode`): the host discovery
  form. `./scripts/install-local.sh --runtime zcode --method copy` installs
  the generated Skills into `$HOME/.zcode/skills`, sibling `kaola-project-runner`
  plus the ten `<platform>-kaola-project-runner` workers. A **workspace**
  skills destination — `.zcode/skills` and `.agents/skills` are both
  live-verified default discovery roots — is the same payload reached
  through the explicit `--skills-dir /abs/path`, because
  `--skills-dir` accepts any absolute destination parent. The layouts are
  the same Skill payload; only the discovery root differs.

## The generic ACP entry

```text
external ACP client
   -> Runner session (one named holder, process group, record root)
       -> kaola-zcode-acp.py adapter over explicit app-server --stdio
           -> ZCode.app backend (native sess_* session)
```

- ZCode is ACP-only: the manifest `default_transport` is `acp`.
- The adapter resolves both ZCode paths exactly (`KAOLA_ZCODE_ENTRY` /
  `KAOLA_ZCODE_NODE`), never PATH, and fails closed before spawning.
- Every Runner receipt is `schema_version 3` and carries the Runner **session
  name**; the ACP session id is on the start receipt; the native id appears in
  the identity update below.
- Prompts reach the backend as transported content only (the repo's security
  boundary: literal/bracketed-paste, never shell eval). This phase adds no
  executable-prompt behavior.

### Session identity

The three layers stay separately trackable:

| Layer | Where it appears |
| --- | --- |
| Runner session name | every `kaola-acp` receipt (`session`) |
| ACP session id | start receipt `acp_session_id`; `session/new` result |
| Native `sess_*` id | one `session/update {sessionUpdate: native_session_identity, acpSessionId, nativeSessionId}` emitted on materialize/resume; `session/load` returns `{sessionId, configOptions}` |

The identity update is credential-free and emitted once per materialize and
once per faithful resume, so an external client and the holder's event log can
map the Runner session to the resumable native id.

### Resuming a native session's model (3.12+)

A faithful `--resume sess_*` keeps the session's own Coding Plan selection. On
3.12+ that selection is not reachable as settings: `session/read` answers with a
message list and no top-level `settings` at all, so the adapter reads the model
off the transcript itself — `messages[i].info.model = {providerId, modelId}` on
`session/read`, or the same pair flattened to `info.modelId` / `info.providerId`
on `session/messages` — and takes the newest entry carrying a complete pair, by
`info.time.created` rather than array position. A resumed app-server also starts
with an empty provider registry, so the plan is re-registered through the same
`provider/updateAccountConfig` push and `account:*` `session/setModel` selection
a fresh session uses; there is no `runtimeModel` key on that path, which 3.12+
rejects outright.

Nothing is substituted. A transcript with no usable model, a model the enabled
plan does not offer, or a model belonging to another account fails the resume
closed without reaching `session/setModel` — the plan default is never selected
on the user's behalf and the account is never switched. A resume that fails for
an ordinary reason reports that reason: an unknown or already-deleted native
session answers `-32004 Session not found`, and the pre-3.12 `runtimeModel`
overlay is retried only when the backend actually asks for it with
`Model config is missing`.

Because a resumed session reports its real provider, the model option it
advertises as `currentValue` is account-qualified
(`account:<plan>\<model>`). Both that id and the desktop-registry
`builtin:*` id name the one enabled Coding Plan and both round-trip through
`session/set_config_option`; any other provider, including a different account,
is still refused.

## Nested Host → Worker isolation (contract)

Phase 1 establishes the isolation **contract** and verifies it with an offline
test harness that starts outer and inner Runner sessions from the test
process:

```text
outer ZCode Host session (holder A, pgid A)
   outer agent / harness starts -> inner Runner session B (holder B, pgid B)
       -> inner ZCode adapter -> inner app-server
```

- **Process isolation.** Holder/agent at every layer leads its own process
  group; an inner stop terminates only the inner group and never reaches the
  outer Host.
- **Record isolation.** Every session has its own record-root entry
  (`records/<platform>/<session>/<repo-digest>`).
- **Exact outer sweep.** When a nested start runs inside an outer holder's
  agent (the same mechanism the Claude Code bridge already uses), the outer
  holder's `KAOLA_ACP_CHILD_RECORD` names a `children.jsonl`; the nested
  `kaola-acp start` appends the inner holder's `{pid, pgid, spawned_at}` there
  and adds a `child_record` fact to its start receipt. The outer `stop` sweeps
  only identity-checked recorded inner groups (`swept_child_pgids`,
  `residual_pids`), so it still finds the inner holder after the outer agent
  died first (holder-lost `stop --force` → `swept_pgids`).
- **Trust boundary.** `KAOLA_ACP_CHILD_RECORD` is the write handle to a holder
  record. Only a holder sets it for its own agent, and the ZCode adapter does
  **not** forward it into the app-server child (it is absent from the adapter's
  env allowlist), so an external agent child never gains a write handle to
  another holder's record.

Real model-driven dispatch — a ZCode Host that actually delegates a turn to a
Worker through the Runner — is **not** claimed by this phase. It is deferred
to a strictly controlled live E2E, because it must be exercised inside the real
Agent interaction, never emulated by executing prompts as shell commands.

## Credential and config boundary (unchanged)

The adapter copies only its `ENV_ALLOWLIST` (HOME, PATH, TMPDIR, LANG, locale
names, USER, LOGNAME, SHELL, TZ, TERM) plus the explicit
`KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` runtime facts to the native child. The
denied credential names (`ANTHROPIC_*`, `OPENAI_API_KEY`, `ZCODE_*`
credential/remote/hub names) and the child-record write handle never reach any
ZCode process. The plan credential reaches the app-server in memory only and
never appears in Runner receipts or records: on a pre-3.12 app-server it rides
the in-memory Coding Plan provider overlay inside the sandboxed descriptor, and
on ZCode 3.12+ it is handed over per model request in the adapter's answer to
`interaction/requestProviderRuntimeHeaders`, for the one authorized provider
only. The two provider-config names ZCode 3.12+ needs
(`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE`, `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE`)
are derived from the verified entry rather than inherited, so an unowned value
in the parent environment can never steer the child at a foreign provider
table.

## Event-driven heartbeat (Phase 2)

A ZCode Host session has no periodic heartbeat carrier: no Routine, no cron,
no sleep loop, and no new scheduler, daemon, port, or second agent-stdin
writer anywhere in the chain. Worker events are the only trigger:

```text
worker agent terminated / worker turn ended (one idle episode)
  / new pending session/request_permission (one permission_required)
  -> worker holder's existing on_agent_exit / turn-end /
     request-permission paths
     -> one socket op `worker_event` to the ZCode Host holder
        (an UNDELIVERED permission_required is retained and re-offered from
         the holder's existing 15s idle_watcher tick - no new thread, loop,
         scheduler or deadline; Issue #92)
        -> bounded in-memory staging list (cap 32 detailed events, deduped by event id)
           -> if a later event cannot stage: one full-check generation in the
              same event log (not a 33rd detailed line)
           -> one ordinary session/prompt through op_prompt
              (the normal admission path; prompt-in-progress is never bypassed)
```

- **Arming (mechanical since Issue #104).** The Host's holder names itself to
  its agent through `KAOLA_ACP_DISPATCHER` (identity only:
  `holder_instance_id`, `platform`, `repo`, `session`; the ZCode bridge
  forwards this one name and still not `KAOLA_ACP_CHILD_RECORD`). A worker
  `start` run inside that agent derives `KAOLA_ACP_HEARTBEAT_HOST` from it,
  verifies the Host holder is live (record present, `holder_pid` alive,
  same `holder_instance_id`, admin socket on disk), resolves the socket, and
  hands the target plus socket to the worker holder; the receipt says
  `heartbeat_host_source: "dispatcher"`. If any check fails the start is
  refused (`result: refused`, `reason: heartbeat-host-unresolved`, exit 1)
  and nothing is created; an explicit variable naming a *different* Host
  than the dispatcher is `heartbeat-host-conflict`. An explicit
  `KAOLA_ACP_HEARTBEAT_HOST` still works as before (`source: "explicit"`,
  fail closed with a usage error on a self-referential or malformed
  target); a start under a dispatcher, or naming a target, whose platform
  has no measured `host_skill_entry` (no shipped platform since Issue #126) is refused
  `host-entry-unsupported` (Issue #122), as is a Host-named start on that
  platform; a start under no holder
  at all is `none` and unbound, exactly as before. Runner dispatch is
  ACP-only for every caller (Issue #130): a `--transport pty` request is refused
  `transport-pty-retired`, which absorbs the former #104 reason
  `heartbeat-host-pty-unsupported`. Transitional: a
  Host whose holder started on an older build never set the fact, so its
  workers land on `none` (unbound, not refused) until that Host is
  restarted on the new build.
- **The binding fact (Issue #70).** The holder carries the target it really
  adopted in its own `state` and `record.json`, so `start`, `observe` and
  `status` report the running fact rather than the caller's input: a target, an
  explicit `null` for an ordinary unbound worker, or `heartbeat_host_known:
  false` for a holder or record written before the field existed (unknown is
  never reported as unbound). The `start` receipt keeps what it asked for
  separately in `heartbeat_host_requested`. A live holder's binding is fixed at
  its start: a later environment change, a `send`, or a repeat `start` (which
  returns `session-exists` together with the binding in force) cannot alter it,
  and there is no rebind operation — recovery is the existing exact
  `stop`/`start` at a safe idle point. A worker started before automatic
  binding (`heartbeat_host: null`) wakes nobody, so the Host reads its
  in-flight result inside the beat with the existing bounded `wait --timeout`
  (a recovery exception, not the ordinary event wait and not a poll loop),
  then exact-stops and restarts it at that idle point; the new `start` binds
  by itself. Only a refused `start` or a session that is gone is reported as
  an exception with the decision it needs.
  A `start` receipt with no `heartbeat_host_source` key **at all** is a
  different fact from `heartbeat_host_known: false`: the worker Skill copy
  that ran that `start` predates Issue #104, so it ignored the dispatcher
  fact entirely. Treat it as a pre-#104 worker — exact-stop it, report the
  install as the blocker, and refresh the install before dispatching again
  (Issue #105).
- **Events.** `terminated` fires once from the worker holder's existing
  `on_agent_exit` path, before the exit bookkeeping, so an exact stop waits
  out the send; `idle` fires once per ended turn with the agent still alive
  (`outcome` `turn_completed`/`turn_failed`), so the next idle episode needs a
  new worker turn. `permission_required` (Issue #76) fires once per *new*
  `session/request_permission` pending key — a wake, not an idle and not the
  turn's end: the request's `request_id` is the only locator the event
  carries (title, options, and tool input never travel; the Host reads them
  from the worker's own `pending_permissions` receipt and decides inside
  existing authorization or escalates), a re-sent request id stays one wake,
  and the ordinary turn-end `idle` still arrives after the request settles.
  The 600s `idle_watcher` stays a non-business exit timer and is never a
  heartbeat event, though Issue #92 does re-offer an undelivered
  `permission_required` from that same tick.
- **Undelivered permission wakes (Issue #92).** A pending permission keeps the
  worker turn ACTIVE, so no turn-end `idle` will ever carry it: if the bound
  Host holder is not listening when it is raised, that single send is the only
  chance the carrier gets. The worker holder therefore RETAINS an undelivered
  `permission_required` and re-offers it, with the ORIGINAL `event_cursor` so
  the deterministic `event_id` is unchanged and a repeat meets the existing
  dedup. It is owed only while the Host never took it - `host-unreachable`,
  `host-closed`, `host-reply-invalid`, `unknown-op`; any receipt the Host
  produced settles it, refusal included. There is no attempt cap and no
  expiry: the wake lives as long as the request it locates. `observe`/`status`
  report what is still owed as `undelivered_worker_events` (locator, attempts,
  last error).
- **A delivered wake is not a live approval (Issue #92).** Staleness is
  re-read immediately before the bytes go out, so a request settled, an agent
  exited, or a stop begun BEFORE the write aborts that offer
  (`heartbeat_carrier_dropped`). That narrows the window and does not close
  it: check, write, and the Host's own staging are three steps across two
  processes, so a settlement landing AFTER the write still leaves the Host
  holding a locator for a request that is gone. That case is recorded as
  `heartbeat_carrier_delivered_stale` - carrying the reason and the Host's own
  receipt - and never as `heartbeat_carrier_recovered`. What keeps it safe is
  the Host side, not the carrier: the event is a LOCATOR, so re-read the
  worker's live `pending_permissions` before acting, ignore a vanished request
  idempotently, and approve nothing from the event itself. A stale approval
  attempt is refused with `no-pending-permission`.
- **Payload.** One literal prompt: the native Skill entry
  `/kaola-project-runner` as its own first line (Issue #94 — the holder
  prepends it; the `body` never carries it), then fixed structured event
  metadata (one JSON object per event: id, kind, platform, session, repo,
  reason, event cursor,
  and `request_id` when the kind carries one),
  the current **full** heartbeat prompt body read at delivery time from
  `<repo>/.kaola/heartbeat-prompt.json` — the single file the ZCode Host agent
  owns; after each worker terminated/idle notification it settles the next step
  and rewrites the file as the next beat's snapshot, keeping only the
  constraints still in force per the drop/keep subtraction rule in the main
  Skill's `references/heartbeat-skeleton.md` (Issue #68), so the next heartbeat
  pass carries that refreshed state (fingerprint and byte count are
  supplementary) — and one instruction to perform a single full pass per
  `PROJECT_RUNNER_HEARTBEAT_V2`. No worker raw output travels with it. The
  file is read once and capped at 65536 bytes (Issue #87): an ordinary file
  under that size is delivered complete; a larger file is not truncated into
  a look-alike body — the worker event still wakes with the named defect
  (`file exceeds 65536 bytes` plus rewrite guidance) and
  `heartbeat_body_error` on `worker_event_delivered`. An absent prompt file
  delivers an explicit fallback trigger context instead; a file that exists
  but carries no usable `body` string (Issue #66: wrong field name, wrong
  type, empty, or unparseable JSON) delivers the same fallback **plus** the
  named defect - `heartbeat prompt source: <path> present but UNUSABLE -
  <defect>` in the prompt and `heartbeat_body_error` in the host holder's
  `worker_event_delivered` entry - so a Host cannot mistake a mis-written
  file for a maintained prompt. Delivery is never blocked by it.
- **Busy host and overflow (Issue #87).** While a turn is active the host
  holder stages up to 32 detailed events and flushes them as one batched
  prompt at the next completed turn boundary; a notification turn that fails
  or is canceled leaves its events staged for the next healthy boundary. No
  retry loop and no raw send. The 33rd detailed event is still
  `worker-event-queue-full` and is not staged as a 33rd line; the holder
  records one monotonic full-check generation (`worker_event_overflow`) in
  the existing event log — increment and append under the same lock — and
  includes `kaola-host-notify/overflow-full-check` in the next heartbeat so
  the Host inspects every authorized worker's real status and pending
  approvals. If the detailed queue is already full and the Host is idle,
  that overflow delivers the full-check immediately. That signal reminds
  only: it does not approve or refuse permissions. Overflow during a
  notification is a later generation and still needs the following wake.
  There is no lossless 33rd detailed replay and no second queue.
- **Confirmation and resume.** The host turn completing after the
  notification confirms the detailed events and, when present, the
  full-check generation snapped at delivery (`worker_event_overflow_confirmed`).
  Admitting the prompt and marking the events and overflow generation it
  carried are one hold of the carrier's lock — the same lock the turn-end
  callback takes. A Host that answers immediately therefore waits there and
  then finds a fully marked notification turn, instead of concluding the turn
  was not a notification and sending the same events again; and two deliveries
  racing over one staged list cannot both admit, because the second finds the
  events already marked. Marking only follows a successful admission, so a
  prompt that is refused or never written leaves nothing to undo and its events
  stay staged. A confirmed `event_id` offered again is answered `duplicate`
  (with `confirmed`) and does not re-prompt the Host. A bounded in-memory index
  of recently confirmed ids answers that, but only as a cache over those
  records: each entry carries the cursor its confirmation was written at, and an
  entry whose record rotation has dropped stops being evidence, because the
  holder can no longer show it. A miss, or an entry that has aged out of the
  retained log, is resolved against the `worker_event_confirmed` records
  themselves. The answer therefore holds for as long as the event log still
  retains the confirmation — the same horizon that already bounds resume
  redelivery, not a fixed number of ids. Only confirmed ids are suppressed: a genuinely unconfirmed event is
  redelivered as before, and once rotation has dropped a confirmation the holder
  has no record of it anywhere and that event is deliverable again, which keeps
  the carrier at-least-once rather than silently dropping it.
  Stage, delivery, and confirmation are recorded in the host holder's
  existing event log, and the confirmation is written before the events leave
  the pending list — the log is the only persistence, so nothing observes an
  event as confirmed before the record that proves it exists. `start --resume` (the `session/load` path, also after
  exact `stop`) rebuilds the pending detailed list from that log
  (at-least-once for those ≤32 events) and restores a full-check when the
  max overflow generation exceeds the max confirmed generation, even if a
  late gen1 line follows gen2. Current generation is seeded at least the
  confirmed generation so rotation that dropped older overflow facts cannot
  rewind the counter. A later event beyond the cap is not promised as a
  detailed line after resume.
- **The Host must end its turn (Issue #65).** Staging only clears at a turn
  boundary, so a Host that holds its turn open with `sleep`, a poll loop, or a
  blocking `wait` is exactly what keeps its own events undelivered. The
  post-dispatch contract is therefore: start workers from the Host's own
  session (the binding is derived and verified by the script), read the
  receipt's `heartbeat_host` fact, dispatch with
  `send --no-wait` and read the acceptance receipt (`in_progress` is accepted,
  not finished), settle the rest of the beat, update the one
  `.kaola/heartbeat-prompt.json`, then end the reply naturally — there is no
  "wait mode" command, because ending the turn *is* the wait. A Host awaiting
  in-flight workers or open close-out is not a stoppable idle worker, and the
  outer Agent must not send it "continue". On the worker side the authorized
  count is a hard cap on live worker processes, ACP holders included: the Host
  counts before every `start` and stops one seat first at the cap
  (stop-before-start), and exact-stops a seat in the beat its delivery is
  accepted. The generated main Skill carries
  these rules, and
  `skills/kaola-project-runner/references/zcode-host-dispatch.md` carries the
  runnable role-by-role procedure (outer Agent, Host, worker/carrier).
- **Never steering.** A worker event is delivered as an ordinary prompt at a
  turn boundary and is never converted into a mid-turn `steer`; `steer` is a
  separate Agent-chosen tool (Issue #65) that does not touch this wake path.
- **ZCode-only.** The `worker_event` op answers `worker-event-unsupported` on
  any non-zcode holder, and the CLI refuses non-ZCode and self targets.
  Other hosts' periodic carriers, the shared main Skill policy, and the
  `PROJECT_RUNNER_HEARTBEAT_V2` skeleton stay one unchanged set; the only
  Skill change is the minimal ZCode-host override that documents the carrier
  and its prompt file.

## Two startup flows (Issue #66)

The main Skill opens with two short entry points, and only the second involves
any of the machinery above:

- **Ordinary worker supervision** — the controlling Agent dispatches and accepts
  from its own session. No Host, no `KAOLA_ACP_HEARTBEAT_HOST`, no heartbeat
  prompt file, and no added gate; blocking `send` stays a normal way to wait.
- **Orchestrator (ZCode Host) supervision** — an outer Agent starts a named
  ZCode Host that loads the main Skill and supervises workers on event-driven
  beats. `skills/kaola-project-runner/references/host-startup.md` carries the
  outer startup order (recover, start at the canonical root, hand over the
  identity/plan/authorization the Host cannot discover, read its startup
  receipt, verify it against the project's existing Project Plan and the Host's
  real tool evidence rather than its self-claim, then keep the Host while
  delivery/acceptance/close-out is open and stop it exactly afterwards), the
  Host's own beat (prepare a valid `body` before the first dispatch, bind per
  `start` and check the receipt, dispatch `--no-wait`, end the turn as the
  wait), and which record holds roles, progress, current state, and facts.

No role parameter, launcher, state machine, config system, scheduler, or
approval gate was added for either flow.

## The native Skill entry, including across compaction (Issue #94)

Every turn-opening prompt to a ZCode Host — the first handoff, a resume or
attach update `send`, a worker-event notification, and the round after any
compaction — opens with `/kaola-project-runner` on its own first line. ZCode
keeps each enabled Skill's metadata visible to the model per request
(injected alongside the `AGENTS.md` prefix, outside the history compaction
rewrites) and instructs it to invoke `/<skill-name>` through the Skill tool,
so the first line produces a native `Skill` tool_call that loads the body
while the rest of the prompt is handled normally. A busy `steer` guide is
different by construction: the holder forwards it into the already-running
turn verbatim (the Issue #65/#81 transport), so it produces no new prompt
and no new `Skill` tool_call — the running turn keeps the Skill body it
loaded at its own first line, and no re-invocation is claimed or required
there. The composite `steer --steer-mode interrupt` is different again: its
cancel-then-resend creates a genuinely new turn and carries the Agent's
text verbatim on every session — it is not a Host recovery entry and adds
no entry line, so do not use it to open a Host round unless the caller
supplies `/kaola-project-runner` as the steering text's own first line.
Verified live on ZCode 3.12.3 with the repo adapter 0.3.3:

- Real GLM model: `/kaola-project-runner` produces a native `Skill`
  tool_call; a manual `/compact` then `/kaola-project-runner` produces a
  **new** `Skill` tool_call returning a Skill-body marker — not a manual
  `read` of a `SKILL.md` path.
- Command plus trailing prompt text: the `Skill` tool_call fires and the
  rest of the prompt is handled normally — the exact form the notification
  envelope uses (`kaola-acp-holder` prepends the line; the Host's
  `heartbeat-prompt.json` `body` never carries it).
- Real `trigger:"auto"` compactions (isolated mock provider, declared small
  `contextWindow`, scratch `HOME`): the request after each completed
  compaction still carries the `/<skill-name>` invocation rule and the
  `kaola-project-runner` skill metadata on the wire.
- Discovery roots (Issue #94 review fix): the installed 3.12.3 binary
  resolves workspace `.zcode/skills` and `.agents/skills`, user
  `~/.zcode/skills` and `~/.agents/skills`, plus both roots on ancestor
  directories up to the workspace boundary — the defaults. Configured
  roots add more: `skills.roots` in `~/.zcode/cli/config.json` is passed
  to the skills service as `extraRoots`, and `plugins.dirs` in the same
  file makes the runtime scan a plugin dir's `skills/`; a scratch-HOME
  live probe injected the `kaola-project-runner` metadata from each
  `.agents/skills` root, from a `skills.roots` root (`file:` at the
  configured dir), and `kpr-extra:kaola-project-runner` (loadable as
  `kaola-project-runner`) from a configured plugin dir.
- Composite interrupt steer (Issue #94 re-review): the holder's
  `--steer-mode interrupt` resend carries the Agent's text verbatim on a
  genuinely new turn — contract-tested end-to-end on a Host-shaped
  session and an ordinary worker alike; it is not a Host recovery entry.

The discovery precondition is the install: the generated
`kaola-project-runner` Skill must sit where the Host session discovers
skills — default roots `<repo>/.zcode/skills/`, `<repo>/.agents/skills/`,
`~/.zcode/skills/`, or `~/.agents/skills/` (ancestor-directory roots are
also scanned; configured `skills.roots` and `plugins.dirs` roots scan
too; plugin cache roots are a separate mechanism). A `--skills-dir` outside every
discovered root — default or configured — still works for an agent that
reads the file itself, but a ZCode Host does not read the file; if a
beat's `capture`
shows no `Skill` tool_call, the install is wrong — fix it, never substitute
a manual read.

### Refreshing the install is part of every pin upgrade (Issue #105)

Registering an accepted checkout does **not** refresh an installed Skill
tree. A ZCode Host started from the newly accepted checkout while
`~/.zcode/skills` still holds the previous build dispatches workers whose
`start` runs the *old* copy, and that copy carries no automatic binding: the
worker opens unbound and exits 0. Every pin bump therefore ends with:

1. Register the accepted checkout (the existing pin flow, unchanged).
2. From that accepted checkout, `./scripts/install-local.sh --runtime zcode
   --method copy` (a project with a workspace `.zcode/skills` or
   `.agents/skills` root installs there with the matching `--skills-dir`).
3. Verify alignment mechanically from the accepted checkout. `--verify-install`
   compares every generated Skill present under the destination against a fresh
   render of this checkout — every byte, `SKILL.md` prose and `references/`
   included — and prints one JSON receipt (`result: aligned|refused`,
   `reason: skill-install-skew`, a per-file `skew` list naming each `stale` /
   `missing` / `unexpected` path with both 12-hex digests), exiting 1 on any
   skew. It is read-only and skips a Skill that is not installed, so a partial
   install verifies cleanly:

   ```bash
   A=/abs/path/to/accepted-checkout
   ( cd "$A" && ./scripts/render-skills.py --verify-install "$HOME/.zcode/skills" )
   ```

   Every `.kaola-install-receipts/*.json` `source` must still name the accepted
   checkout — that is provenance, not content:

   ```bash
   grep -h '"source"' "$HOME/.zcode/skills"/.kaola-install-receipts/*.json
   ```

4. Restart what still runs the old code. A live holder is never hot-replaced:
   workers exact-`stop` and `start` again at an idle point (the recovery rule
   above), and a Host started on an older build needs the same treatment.

A Host `start` now refuses this skew mechanically instead of trusting the
step: run from an installed Skill tree, it hashes the shared worker scripts in
every Skill directory under the four default discovery roots and answers
`{"result": "refused", "reason": "worker-skill-build-skew"}` with exit 1 and
nothing created (`worker_skill_skew` names the differing paths). A passing
`start` reports `worker_skill_build` and `worker_skill_roots`. A default
discovery root that exists but cannot be listed makes that comparison
impossible, so the same `start` refuses it by name —
`{"result": "refused", "reason": "worker-skill-root-unreadable"}` with the root
in `worker_skill_unreadable_roots` and `detail` (Issue #106); a permission
problem is never a raw traceback. Residuals the start check does not cover:
roots ZCode reaches only through ancestor directories, `skills.roots` or
`plugins.dirs`; a checkout invocation of `scripts/kaola-acp.py`, which has no
Skill build to compare and reports both fields `null`; and an already running
holder, which keeps the code it started with either way.

The main Skill ships no scripts, so the same `start` compares it against the
build record every worker Skill carries (`scripts/main-skill-build.json`,
Issue #121): any `kaola-project-runner` Skill in those roots with a different
recorded file is refused as
`{"result": "refused", "reason": "main-skill-build-skew"}` with exit 1 and
nothing created (`main_skill_skew` names the path and both builds). The start
only detects it; reinstall that root or remove the stale copy.

At most one live Host serves a canonical root (Issue #132). A Host-named start
is refused as `{"result": "refused", "reason": "host-exists"}` with exit 1 and
nothing created while another Host-named holder of that root may be live:
it passes the identity check (record, live PID, answering socket, matching
`holder_instance_id`), answers under another instance (`mismatch`), or is
silent while its argv names the record or cannot be read. `existing_host` is
attached when verified, exact-stopped and proven gone first when dead or
silent, and reported for a human on `mismatch`. A Host that fails
the check is exact-stopped and proven gone before its replacement starts, and
every Delegator reach-out asks the Host to sweep the repo's holders first
(`references/host-startup.md`, "Repo sweep").

The runtime scan stays scripts-only, but prose is no longer manual: a worker
Skill copy carries only its own rendered prose, so it cannot know another
platform's `SKILL.md`, and the accepted checkout is the one place every Skill's
render is available. `--verify-install` (Issue #107) therefore compares the
whole installed tree — `SKILL.md` and `references/` included, main Skill and
worker Skills alike — against that render, replacing the step-3 manual
`diff -rq`. It reports the same default roots and shares their residual: it only
verifies the root it is pointed at.

Skew has two directions and they are not symmetric. An old Host with a new
worker Skill is the Issue #104 transitional case: the Host never sets the
dispatcher fact, so its workers start unbound rather than refused, and
restarting the Host fixes it. A new Host with an old worker Skill is this
one: the fact is set and ignored, which is why the Host start refuses first.

Boundaries held: no project `AGENTS.md` block is planted, ordinary Agents
in a consuming repo carry no Host recovery instruction, and no hook,
plugin, command registry, scheduler, polling loop, role classifier,
session marker, cursor ledger, or state machine was added. The superseded Issue #75 design (durable `AGENTS.md`
carrier, per-send carrier text, manual `SKILL.md` reread) is removed from
the generated Skill; its runtime findings stay true and are kept in
`references/zcode-native-skill-entry.md`: ZCode 0.16.5/3.12.3 has no
compaction hook (`SessionStart` fires on `startup`/`resume` only), no
compaction reaches the ACP stream (`observe`/`capture` show none,
`context_usage` stays null), `/compact` and the `session/compact` RPC write
the same `compaction`/`context_compaction` `part` rows, auto-compaction
writes the same rows, and a read-only `part`-table cursor stays an optional
diagnostic — never a per-send gate. Not verified: real-model behaviour
after a genuine auto-compaction (the catalog GLM models are 1M-window, so
forcing one is beyond bounded cost), any compact-specific ACP event,
because none exists, and a `Skill` tool_call from a busy `steer` guide —
steer forwards the guide into the running turn and no re-invocation is
claimed there (the interrupt resend's first line is contract-tested; its
`Skill` tool_call follows the same verified entry mechanism).

## The Host's model is a dispatch requirement (Issue #108)

A ZCode Host is the control plane: its model and effort are dispatch
requirements, not preferences. A `start` whose Runner session name has the
documented Host shape `zcode-<PROJECT_CODE>-orchestrator-<purpose>`
(`templates/kaola-delegator/references/handoff.md`) therefore enforces
**GLM 5.3 at effort `max`** mechanically, on a fresh start and `--resume`
alike:

- An explicit `--model`/`--effort` that contradicts the requirement is a
  typed pre-mutation refusal — `{"result": "refused", "reason":
  "host-model-mismatch"}`, exit 1, nothing created (no record directory, no
  holder socket) — and `host_selection` names the required
  and requested values. An absent selection is never refused: the pin
  supplies it.
- Once the session reports ready, the pin is applied through the ordinary
  ACP config options (`model`, `thought`) and then **verified**: a fresh
  holder `state` read must advertise model `…\GLM-5.3` and thoughtLevel
  `max` as `currentValue`. A session that cannot prove the pair — for
  example a Coding Plan that does not offer GLM 5.3 — is stopped on the
  spot and the start is refused: `{"result": "refused", "reason":
  "host-model-unverified"}` with `host_session_stopped`, `residual_pids`,
  `holder_alive`, and the effective values it actually found.
- A passing start reports `host_selection` — required, requested, applied,
  and verified effective values — so the receipt itself is the evidence.

The discriminator is the session-name shape, not a flag, so forgetting an
opt-in marker cannot open a wrong-model Host. Every new Host is started
under the standard name; a live nonstandard Host (`zcode-kaola-host`) is
attached in place and never re-`start`ed — it keeps the selection its own
start proved, and upgrading it means exact-stop plus a fresh
standard-named start. The issue-worker marker `-i<digits>-` wins over a
purpose token that happens to contain "orchestrator", so an ordinary worker
is never pinned. The check lives in the ACP `start` path, the only one.

## Verification

- `python3 tests/contract/test-zcode-acp-contract.py` — adapter contract, env
  boundary, session identity, load result, and the Issue #65 rule that a
  concurrent `session/prompt` is refused `-32010` instead of stealing the
  running turn's request id.
- `python3 tests/contract/test-issue-65-host-contract.py` — the generated Host
  event-wait wording and its reference: identity bootstrap, carrier binding and
  receipt check, non-blocking dispatch, ending the turn instead of sleeping, and
  reading results by worker identity and cursor.
- `python3 tests/contract/test-zcode-host-contract.py` — two-layer real-holder
  isolation contract (harness-driven), holder-lost sweep, child-record append.
- `python3 tests/contract/test-zcode-heartbeat-contract.py` — the Phase 2
  carrier: terminated/idle delivery with the full current prompt body, busy
  staging and boundary flush, bounded deduped queue, 33rd-event full-check
  (later overflow still wakes, idle-full delivers now, restore takes max
  generation, exact-stop resume, remind-only), 64KiB prompt-file bound,
  ZCode-only gates, and no periodic trigger without worker events. Also the
  Issue #106 unreadable-root refusal and the Issue #108 Host model pin:
  explicit mismatch refused before anything exists, absent selection pinned
  to GLM 5.3 + max and verified, an unprovable pin stopped and refused, and
  worker names never pinned.
- `bash tests/contract/test-installer-runtimes.sh` — `--runtime zcode` and
  workspace `.zcode/skills` installs.
- `python3 tests/contract/test-issue-51-runner-integration.py` — ZCode worker
  offline Runner integration (unchanged).
- `python3 scripts/render-skills.py --check` — generated Skills in sync.
- `python3 tests/contract/test-generated-skills.py` — Issue #107: an installed
  Skills tree is verified against this render byte-for-byte, prose included.
- `python3 scripts/render-skills.py --verify-install /abs/skills-root` —
  Issue #107: the same verification as a subcommand.
