# Changelog

## Unreleased

- **Claude Code ACP through a vendored, pinned bridge; ACP is now Claude Code's default
  transport** (Issue #50, Missions 1–3; the live subscription gate passed on the recording Mac on
  2026-09-16 and `--transport pty` stays the explicit fallback and login channel). A live finding
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
