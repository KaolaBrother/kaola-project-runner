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
ZCode process. The in-memory Coding Plan provider overlay carries the plan
credential to the app-server only, inside the sandboxed descriptor, and it
never appears in Runner receipts or records.

## Event-driven heartbeat (Phase 2)

A ZCode Host session has no periodic heartbeat carrier: no Routine, no cron,
no sleep loop, and no new scheduler, daemon, port, or second agent-stdin
writer anywhere in the chain. Worker events are the only trigger:

```text
worker agent terminated / worker turn ended (one idle episode)
  -> worker holder's existing on_agent_exit / turn-end path
     -> one socket op `worker_event` to the ZCode Host holder
        -> bounded in-memory staging list (cap 32, deduped by event id)
           -> one ordinary session/prompt through op_prompt
              (the normal admission path; prompt-in-progress is never bypassed)
```

- **Arming.** The ZCode Host agent exports `KAOLA_ACP_HEARTBEAT_HOST`
  (`{"platform": "zcode", "session": ..., "repo": ...}`) when starting each
  worker. `kaola-acp start` validates it (ZCode-only, fail closed: a
  non-ZCode, self-referential, or malformed target is a usage error before
  anything spawns), resolves the host holder's deterministic socket, echoes a
  `heartbeat_host` fact on the start receipt, and passes both env facts to the
  worker holder.
- **Events.** `terminated` fires once from the worker holder's existing
  `on_agent_exit` path, before the exit bookkeeping, so an exact stop waits
  out the send; `idle` fires once per ended turn with the agent still alive
  (`outcome` `turn_completed`/`turn_failed`), so the next idle episode needs a
  new worker turn. The 600s `idle_watcher` stays a non-business exit timer and
  is never a heartbeat event.
- **Payload.** One literal prompt: fixed structured event metadata (one JSON
  object per event: id, kind, platform, session, repo, reason, event cursor),
  the current **full** heartbeat prompt body read at delivery time from
  `<repo>/.kaola/heartbeat-prompt.json` — the single file the ZCode Host agent
  maintains and overwrites on change (fingerprint and byte count are
  supplementary) — and one instruction to perform a single full pass per
  `PROJECT_RUNNER_HEARTBEAT_V2`. No worker raw output travels with it. A
  missing or unreadable prompt file delivers an explicit fallback trigger
  context instead.
- **Busy host.** While a turn is active the host holder stages events and
  flushes them as one batched prompt at the next completed turn boundary; a
  notification turn that fails or is canceled leaves its events staged for the
  next healthy boundary. No retry loop, no raw send, no event loss.
- **Confirmation and resume.** The host turn completing after the
  notification confirms it. Stage, delivery, and confirmation are recorded in
  the host holder's existing event log (`worker_event`,
  `worker_event_delivered`, `worker_event_confirmed`); `start --resume` (the
  `session/load` path) rebuilds the pending list from that log and redelivers
  everything unconfirmed — at-least-once, with the heartbeat pass itself as
  the dedup authority, so resume never silently drops an event.
- **ZCode-only.** The `worker_event` op answers `worker-event-unsupported` on
  any non-zcode holder, and the CLI refuses non-ZCode and self targets.
  Other hosts' periodic carriers, the shared main Skill policy, and the
  `PROJECT_RUNNER_HEARTBEAT_V2` skeleton stay one unchanged set; the only
  Skill change is the minimal ZCode-host override that documents the carrier
  and its prompt file.

## Verification

- `python3 tests/contract/test-zcode-acp-contract.py` — adapter contract, env
  boundary, session identity, load result.
- `python3 tests/contract/test-zcode-host-contract.py` — two-layer real-holder
  isolation contract (harness-driven), holder-lost sweep, child-record append.
- `python3 tests/contract/test-zcode-heartbeat-contract.py` — the Phase 2
  carrier: terminated/idle delivery with the full current prompt body, busy
  staging and boundary flush, bounded deduped queue, resume redelivery,
  ZCode-only gates, and no periodic trigger without worker events.
- `bash tests/contract/test-installer-runtimes.sh` — `--runtime zcode` and
  workspace `.zcode/skills` installs.
- `python3 tests/contract/test-issue-51-runner-integration.py` — ZCode worker
  offline Runner integration (unchanged).
- `python3 scripts/render-skills.py --check` — generated Skills in sync.
