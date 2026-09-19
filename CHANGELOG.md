# Changelog

## Unreleased

- **Kimi Code CLI 2.0.1 ACP compatibility reverified.** An isolated live run
  confirmed `initialize`, session creation, model/thinking/YOLO selection, a
  completed prompt, exact stop, and resume of the same native session with
  prior context. The four candidate native steering methods still return
  `-32601`, so the explicit interrupt-and-continue path remains the supported
  steering fallback. This updates the versioned capability description only;
  no transport behaviour changes.

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
