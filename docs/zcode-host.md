# ZCode Host (Issue #62)

Phase 1 of Issue #62 makes ZCode a first-class **Host** of the Project Runner
Skills: a consuming runtime that natively discovers and loads the generated
Skills, plus the generic ACP entry that lets any external ACP client drive
Runner sessions end to end. Phase 2 adds the event-driven heartbeat carrier
(see below); the live real-run E2E remains a separate frontier.

## The two faces of ZCode

- **Worker platform** (`--platform zcode`): ZCode.app is one of the nine
  worker target CLIs a Runner session controls. Unchanged by this phase.
- **Native skill-directory Host** (`--runtime zcode`): the host discovery
  form. `./scripts/install-local.sh --runtime zcode --method copy` installs
  the generated Skills into `$HOME/.zcode/skills`, sibling `kaola-project-runner`
  plus the nine `<platform>-kaola-project-runner` workers. A **workspace**
  `.zcode/skills` destination — the live-verified discovery layout — is the
  same payload reached through the explicit `--skills-dir /abs/path`, because
  `--skills-dir` accepts any absolute destination parent. The two layouts are
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
        -> bounded in-memory staging list (cap 32 detailed events, deduped by event id)
           -> if a later event cannot stage: one full-check generation in the
              same event log (not a 33rd detailed line)
           -> one ordinary session/prompt through op_prompt
              (the normal admission path; prompt-in-progress is never bypassed)
```

- **Arming.** The ZCode Host agent exports `KAOLA_ACP_HEARTBEAT_HOST`
  (`{"platform": "zcode", "session": ..., "repo": ...}`) when starting each
  worker. `kaola-acp start` validates it (ZCode-only, fail closed: a
  non-ZCode, self-referential, or malformed target is a usage error before
  anything spawns), resolves the host holder's deterministic socket, and hands
  the resolved target plus its socket to the worker holder.
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
  `stop`/`start` at a safe idle point. Because an unbound worker wakes nobody,
  the guidance has the Host recover that case itself, with operations it already
  has: when the unbound worker is its only wake source it reads the in-flight
  result inside the beat with the existing bounded `wait --timeout` (a recovery
  exception, explicitly not the ordinary event wait and not a poll loop), then
  rebinds by exact `stop`/`start`. Recording the duty in the heartbeat body is
  bookkeeping, not a trigger; per-worker reading and rebinding is not delegated
  outward, and only a recovery that cannot be completed is reported as an
  exception with the decision it needs. The rebinding `start --resume` needs a
  real native id: for ZCode that `sess_*` is reported in the session's own
  `native_session_identity` update (lazily, at materialisation) and is never
  copied into `session_meta`, so the guidance sources it from that event and
  forbids substituting `acp_session_id` or `--continue`.
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
  heartbeat event.
- **Payload.** One literal prompt: fixed structured event metadata (one JSON
  object per event: id, kind, platform, session, repo, reason, event cursor,
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
  post-dispatch contract is therefore: bind `KAOLA_ACP_HEARTBEAT_HOST` per
  worker `start`, check the receipt's `heartbeat_host` fact on every worker
  including reused ones, dispatch with
  `send --no-wait` and read the acceptance receipt (`in_progress` is accepted,
  not finished), settle the rest of the beat, update the one
  `.kaola/heartbeat-prompt.json`, then end the reply naturally — there is no
  "wait mode" command, because ending the turn *is* the wait. A Host awaiting
  in-flight workers or open close-out is not a stoppable idle worker, and the
  outer Agent must not send it "continue". The generated main Skill carries
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

## Context compaction recovery (Issue #75)

ZCode 0.16.5 has no compaction hook: `SessionStart` fires only on `startup`
and `resume`, the hook event enum carries no compact event, and nothing about
compaction reaches the ACP session stream — `observe`/`capture` expose no
compaction field and `context_usage` stays null. Recovery is a
Host/Skill-layer carrier, verified live on ZCode 3.12.3:

- **Trigger.** A `session/prompt` whose text is `/compact` routes through the
  runtime's normal turn-command path into a real manual compaction, persisted
  as `compaction` and `context_compaction` rows in `db.sqlite`'s `part` table
  with `trigger:"manual"`, `auto:false` — verified against a live session.
  The runtime also exposes a programmatic `session/compact` RPC that produces
  the identical record family mid-run (verified live); it is not reachable
  through the adapter's fixed method dispatch today. Auto-compaction writes
  the same record family — verified live on an isolated MOCK provider with a
  declared small `contextWindow` (personal-provider model rule, scratch
  `HOME` only): real `trigger:"auto"` / `compactReason:"context_limit"` /
  `phase:"pre_request"` / `status:"completed"` part rows committed by the
  installed runtime. Both catalog models report a 1M context window, so
  auto-compaction on a real GLM account stays beyond bounded cost.
- **Carrier.** The controlling Agent puts the recovery carrier —
  `references/zcode-compact-recovery.md` inside the installed main Skill —
  once at the head of the next prompt to the compacted Host. Verified:
  post-compact, the model executed a real `read` of the installed Skill and
  quoted the reload marker planted in its payload (`KPR-SKILL-RELOAD-7931`
  in the experiment; `KPR-SKILL-RELOAD-V1` ships in the reference).
- **Detection honesty.** An Agent-requested compaction is self-evident; any
  other compaction is silent in the ACP stream. A read-only `part`-table
  cursor on `db.sqlite` confirms it (verified live: the rows are committed
  synchronously) but stays a diagnostic the Agent may run — never a per-send
  transport gate, a cursor ledger, or a hooks/config change. A
  `UserPromptSubmit` hook could carry recovery too — live-verified in
  isolated scope (project `plugins.dirs` + plugin `hooks/hooks.json`, zero
  user-global writes): the hook fires on every prompt, a read-only `part`
  cursor detects the episode, and the injected `additionalContext` made the
  model re-read the Skill after both `/compact` and `session/compact`. It
  adds a process per prompt and runtime state under `$ZCODE_PLUGIN_DATA`;
  adoption is a boundary decision for outer review, not shipped here.
- **Durable prefix.** Workspace `AGENTS.md` content is resolved once per
  session into the per-request context prefix — outside the history
  compaction rewrites — verified live: an AGENTS-only marker was still
  quoted after a real `/compact`, and a standing "reload the Skill if its
  text is gone" instruction drove a real `read` plus the reload marker
  with no carrier in the prompt. That makes a planted AGENTS block the
  trigger-agnostic carrier — verified end-to-end for `trigger:"auto"` too:
  on the MOCK-provider session, every conversation inference after each
  real auto-compaction still carried the `# agentsMd` section and the
  standing instruction on the wire. SessionStart/hook `additionalContext`
  lands in history instead and is not durable. Adoption is a boundary
  decision for outer review, not shipped here.

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
  ZCode-only gates, and no periodic trigger without worker events.
- `bash tests/contract/test-installer-runtimes.sh` — `--runtime zcode` and
  workspace `.zcode/skills` installs.
- `python3 tests/contract/test-issue-51-runner-integration.py` — ZCode worker
  offline Runner integration (unchanged).
- `python3 scripts/render-skills.py --check` — generated Skills in sync.
