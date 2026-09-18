# Command and Contract Reference

## Renderer

```text
scripts/render-skills.py --write
scripts/render-skills.py --check
```

`--write` deterministically rebuilds nine managed worker Skill directories plus
`skills/kaola-project-runner/` from `templates/orchestrator/` (control plane; not a tenth
platform) and the Grok Bot host bundle `hosts/grok-bot/`: `kaola-project-runner.md` (the one
thin bridge Skill, from `templates/grok-bot/bridge.md.tmpl` and `accepted-revision.json`; at
the pinned stage it carries the accepted 40-hex commit and its label or release, the locator
command, and the two canonical entry paths, and no canonical content), `bridge.json`
(fingerprint manifest: `stage`, `saveable`, name, resolved description, `accepted_commit`,
`release`, `label`, bytes, file/body sha256; at the content stage `accepted_commit`, `release`,
and `label` are `null` and `saveable` is `false`), and `INSTALL.md` (from
`templates/grok-bot/INSTALL.md.tmpl`). `accepted-revision.json` declares a stage: `content`
(the content commit R; the bridge carries an explicit "none yet" line and `bridge.json` says
`saveable: false`) or `pinned` (the pin commit P; `commit` = R plus exactly one of `release`
`vX.Y.Z` or `label`). At the pinned stage the renderer runs the pin gate against the Git
checkout (`pin: …` findings: commit missing, not an ancestor of HEAD, not a content-stage
commit, lacks `scripts/kaola-locate.py` or an entry path, release tag not at R, the tree
differs from R by a path other than `accepted-revision.json` and the three generated
`hosts/grok-bot/` products, or the bridge differs by more than the one accepted-revision
line; a label that looks like a release tag or begins with "release" is refused) and
`--require-pinned` fails on a content-stage file; the same gate runs from
`kaola-grok-bot-verify.py --repo [--require-pinned]`. Every product is measured against
`templates/budgets.json` first; an over-budget Skill, reference, description, bridge, or guide
is reported as `budget: <surface> is N B > M B (<key>)` and nothing is written (an unverifiable
pin is likewise never written). `--check` returns nonzero for any missing, stale,
or unexpected file, Skill directory, or host bundle file. Manifest values are JSON strings in a
flat YAML subset parsed without an external dependency. Transport fields are `default_transport`,
Transport fields are `default_transport`,
`acp_env_allowlist`, `acp_login_requires_pty`, `acp_init_meta`, `acp_model_config_id`,
`acp_effort_config_id`, `acp_fast_config_id`, `acp_fast_values`, `acp_model_map`, and
`acp_effort_config_id`, `acp_mode_config_id`, `acp_fast_config_id`, `acp_fast_values`, `acp_model_map`, and
`clientCapabilities._meta` during `initialize` — Cursor's `parameterizedModelPicker=true` makes
its ACP surface advertise separate `model`/`effort`/`fast` options with base model IDs and string
`"true"`/`"false"` fast values. `acp_model_map` is an optional `picker-id=acp-option-value;...`
list mapping resolved PTY model IDs onto the ACP model value the agent advertises for the same
model; an effort encoded in the picker ID suffix travels through the effort option and Fast
through `acp_fast_values`-converted values, so semantics are never substituted — an unmapped ID
is sent literally and a rejection is reported as a limitation. Model-selection fields are
`default_model_name`/`default_model_id`/`default_model_parameters`/`default_model_effort`,
`upgrade_model_name`/`upgrade_model_id`/`upgrade_model_parameters`/`upgrade_model_effort`, and
`fast_support`/`fast_summary`. They render as `DEFAULT_TRANSPORT`,
`ACP_COMMAND`, `ACP_QUIRKS`, and `ACP_LOGIN_REQUIRES_PTY` template variables.

An `acp_command` word may start with `$SKILL_DIR/scripts/` to name a file shipped inside the
Skill (Claude Code: `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`;
ZCode: `python3 $SKILL_DIR/scripts/kaola-zcode-acp.py`).
`kaola-acp.py` resolves that prefix to an absolute path before anything is spawned — against its
own `scripts/` directory in an installed Skill, else against the checkout layout whose `vendor/`
sits one level up — and reports the result as `bridge` (`relative`, `path`, `layout`
`skill|checkout`, `present`, `sha256`, `upstream_pin` from `acp_wrapper_pin`,
`verified_versions`) on `preflight` and `start`. A token that resolves to no file is
`error.code` `acp-bridge-missing` and nothing is spawned; there is no PATH lookup and no
download. For the Claude Code platform the Runner also resolves the exact runtime binary the way
PTY does (`CLAUDE_BIN`, else the first PATH match) and passes it to the bridge as
`CLAUDE_ACP_CLAUDE_BIN`, reporting it as `runtime_binary` (`env`, `path`, `absolute`, `present`,
`passed_as`, and on `preflight` the `--version` line); a non-absolute or missing value makes the
bridge fail closed (`session/new`, `session/resume`, and `session/prompt` return JSON-RPC
`-32603`) rather than search PATH. For ZCode the Runner never searches PATH: `preflight` and
`start` fail closed unless `KAOLA_ZCODE_ENTRY` and `KAOLA_ZCODE_NODE` are both explicit
absolute files (the adapter then launches `app-server --stdio` with `ELECTRON_RUN_AS_NODE=1`
and an allowlisted child environment, and hands the desktop App's enabled GLM Coding Plan
provider to the app-server in memory as the protocol's `runtimeModel` overlay, read from
`~/.zcode/v2/config.json` read-only; Start Plan and pay-as-you-go providers are refused,
`~/.zcode/cli/config.json` is never written, and the credential never reaches receipts). The
`start`/`preflight` receipt's `agent_info._meta.zcode` carries the secret-free provider facts
(`providerId`, `baseURL`, `planCacheStatus`, `modelIds`, `rejectedProviders`). ZCode's default
transport is `acp`; `--transport pty` is dispatchable only as a known-unsupported diagnostic
entry, because the bundled runtime has no terminal UI and headless `--prompt` requires
`~/.zcode/cli/config.json`. Login happens in the ZCode desktop App. The
renderer copies `dist/index.js`, `dist/DERIVATION.json`,
`LICENSE`, and `UPSTREAM.md` from `vendor/claude-code-acp/` into the Claude Code worker only,
and copies `scripts/kaola-zcode-acp.py` into the ZCode worker only;
no other worker, the orchestrator, or a host bundle receives them. The bridge persists its ACP
session → native Claude session id map (ids, cwd, timestamps; no prompts, no credentials) in
`~/.claude-code-acp/sessions.json`, or under `CLAUDE_ACP_STATE_DIR` when set; the Runner
inherits the operator's value and sets none itself, so `start --continue` sees every Runner
session on the machine. Per-turn temp files go under `CLAUDE_ACP_RUNTIME_DIR` (default the
system temp dir) and are removed per turn and on stop.

## Installer

```text
scripts/install-local.sh [--runtime NAME | --skills-dir ABS_PATH]
                         [--method link|copy] [--platform ID[,ID...]]
                         [--no-orchestrator]
                         [--bin-links | --no-bin-links] [--uninstall]
```

Platform IDs are `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, `codex`, `zcode`, and `droid`.
Omit `--platform` for all nine workers. `--platform` never selects the main Skill;
`kaola-project-runner` is not a platform ID. The orchestrator is installed for every `--runtime`
and `--skills-dir` destination unless `--no-orchestrator` is passed. Every selected destination is
preflighted before mutation; foreign paths are never replaced.

Droid's executable override is `DROID_BIN`. Its ACP command is the native
`droid exec --output-format acp`; no bridge or translator is used. Droid defaults to Auto Model
(`model=auto`) and full bypass (`autonomy_level=auto-high`) on ACP, while PTY uses
`--skip-permissions-unsafe` plus a process-scoped `--settings` overlay. The supported
`--permission-mode` values are `bypassPermissions|low|medium|high|manual`; PTY maps them to
`--skip-permissions-unsafe`, `--auto <level>`, or no flag, and ACP maps them to
`auto-high|auto-low|auto-medium|auto-high|normal` through `acp_mode_config_id: autonomy_level`.
ACP model, reasoning-effort, and autonomy options use config IDs `model`, `reasoning_effort`, and
`autonomy_level`. Droid has no model/effort upgrade tier and no separate Fast toggle; effort is
passed only when explicitly requested.

`--runtime` selects a verified consuming-runtime destination: `codex` →
`${CODEX_HOME:-$HOME/.codex}/skills`, `claude-code` → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`,
`cursor` → `$HOME/.cursor/skills`, `devin` → `${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills`,
`zcode` → `$HOME/.zcode/skills` (ZCode Host install; the live-verified discovery form is the
workspace `.zcode/skills`, which `--skills-dir` covers — see [ZCode host](zcode-host.md)),
`--runtime grok-bot` (and `grokbot`) is refused: Grok Bot is a bridge host with no installer
destination (see [Grok Bot host](grok-bot-host.md)). `--runtime grok` is not a host alias;
`--platform grok` is the Grok CLI worker.
`--skills-dir` is a mutually exclusive explicit absolute destination (project-local paths included).
With neither flag the legacy Codex destination is used. `--method copy` (default) stages an
identical standalone copy on the destination filesystem and records a per-Skill receipt at
`<skills-dir>/.kaola-install-receipts/<skill>.json` (outside the generated payload). `--method link`
is an explicit development choice that creates exact owned symlinks to this checkout. An owned
source symlink migrates to a copy when reinstalled with the default or `--method copy`. An
unchanged owned copy is a no-op. Python `__pycache__`/bytecode is ignored when comparing
the generated payload with the receipt. A receipt-owned copy with payload drift is
diagnosed and atomically repaired on reinstall; its previous bytes remain in a
reported sibling `.drift.*` directory for Agent inspection. This is not a
runtime execution gate or permission lock. A `.generated` marker without a
valid receipt is not replacement or delete authority. `--uninstall` still
refuses to delete a modified copy and affects only the selected destination
and selected owned Skills.

`--bin-links` additionally manages owned `$HOME/.local/bin/kaola-acp` / `kaola-acp-holder` symlinks
to this repository's scripts. It defaults on only for the Codex runtime destination; uninstall
leaves shared links alone unless `--bin-links` is passed explicitly, and removes only exact-owned
links.

## Locator and host-target attestation

```text
scripts/kaola-locate.py register --target local|cloud --expect-revision SHA [--bin-dir DIR]
scripts/kaola-locate.py [receipt] [--target local|cloud] [--expect-revision SHA] [--bin-dir DIR]
                        [--project ABS_PATH] [--worker ID] [--session NAME]
kaola-project-runner-locate ...          # the registered bin link, same arguments
```

`register` validates first and links second: origin, the required expected revision, the
clean state, the link path, and the receipt path are all checked before anything is touched,
and a refusal (`origin-mismatch`, `origin-form-unsupported`, `revision-mismatch`, `dirty`,
`expect-revision-required`, `expect-revision-not-40-hex`, `foreign-locator-link`, `locator-path-occupied`,
`registration-path-occupied`) leaves an existing link and registration receipt unchanged
(`locator.changed: false`, `registration.changed: false`). Only a clean, matching checkout
links `kaola-project-runner-locate` in the owner-chosen `--bin-dir` (default: the link's own
directory when run through the link, else the installer's `$HOME/.local/bin`, the same
convention as `--bin-links`) to this checkout's `scripts/kaola-locate.py`, replacing a link
that already points at some `scripts/kaola-locate.py` (re-registration after moving a
checkout; `locator.replaced: true`), and then atomically writes the registration receipt
`.kaola-project-runner-locate.json` beside the link
(`kaola-project-runner-locator-registration/1`: resolved `root`, declared `target`, `host`
kernel + hashed fingerprint, `accepted_revision` (always a 40-hex commit, so a moved HEAD is
`registration-stale`; a receipt without one is `locator-registration-unreadable`); no
hostname, username field, or credential; device-local, never in any Skill). The origin is accepted only in an explicit
`https://`, `ssh://`, or scp `host:path` form and normalised to `github.com/Owner/repo`
without userinfo or port; a bare `github.com/Owner/repo`, `http://`, or local-path origin is
`origin-form-unsupported`, and so is a malformed value with a second `@` in its host or a
`?` query or `#` fragment (`origin: null`; no fragment of the value is echoed). The receipt form prints one bounded JSON line
(`kaola-project-runner-locator/1`, ≤ 4 KB): `target` (the kind as declared by the caller,
echoed and never inferred), `host` (kernel + hashed hostname fingerprint), `root` (real local
path, normalised origin, HEAD, `clean`, `revision_match`), `registration` (receipt path,
`present`, recorded target and accepted revision, `fingerprint_match`, `target_match`,
`root_match`, `revision_current`), and, when given, `project` (real local path, top level,
origin), `worker` (id, script path under the same root, `under_root`, `executable`), `session`
(name, `present`: presence on the tmux server reachable from the locator only, not existence
elsewhere and not ownership). A declared `--target` requires the registration receipt
(`locator-not-registered`, `locator-registration-unreadable`) and every recorded fact must
match (`host-fingerprint-mismatch`, `target-mismatch`, `registration-root-mismatch`,
`registration-stale` when HEAD is no longer the registered accepted revision); a plain
discovery call without `--target` tolerates an absent receipt but still refuses a mismatching
one. `result` is `ok` (exit 0) or `refused` (exit 1) with `reasons`; `--target` is required
when any of `--project`, `--worker`, `--session` is given. Revision and clean facts are what
the host's Git reports (index tricks or a tampered `.git` on a trusted host are outside this
boundary; no content hashing). Git runs with `GIT_TERMINAL_PROMPT=0`; no credential is read,
printed, hashed, or forwarded; paths in the receipt are local evidence and never enter an
account Skill.

## tmux core

```text
scripts/kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID] \
  [--tier default|upgrade] [--model ID --effort low|medium|high|xhigh|max] [--fast on|off]
scripts/kaola-tmux.sh PLATFORM observe   --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM status    --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM capture   --repo ABS_PATH --session NAME [--lines N]
scripts/kaola-tmux.sh PLATFORM send      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--text TEXT]
scripts/kaola-tmux.sh PLATFORM key       --repo ABS_PATH --session NAME \
  [--if-snapshot ID] --key NAME
scripts/kaola-tmux.sh PLATFORM answer    --repo ABS_PATH --session NAME \
  [--decision-id ID] [--if-snapshot ID] --replace-editor [--text TEXT]
scripts/kaola-tmux.sh PLATFORM stop      --repo ABS_PATH --session NAME \
  [--if-snapshot ID] [--force]
```

`--repo` must resolve to the exact Git top-level. A linked worktree is a valid Git top-level on
both PTY and ACP and is not a transport refusal; preferring the consuming project's canonical
project root is Agent guidance, so a Workflow child worktree is not required as `--repo`.
Asking the CLI to invoke `workflow-next` is an Agent-selected prompt, not a Runner
operation. Session names match
`[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`. Without `--text`, `send` reads non-empty stdin.

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`,
`CURSOR_AGENT_BIN`, `DEVIN_BIN`, and `DROID_BIN`. Test/embedding overrides are `TMUX_BIN`, `PYTHON_BIN`, `PS_BIN`, and
`KAOLA_START_TIMEOUT`; `GROK_START_TIMEOUT` remains a Grok-only compatibility alias.

## Transport selection

Every command accepts `--transport acp|pty`. Without an override, the platform manifest selects the default. ACP dispatches to `kaola-acp.py`; PTY retains the nested-relay path. Receipts report the selected/default transports, alternatives, and whether selection came from `manifest-default` or `caller-override`. ACP supports `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, `view`, and local `follow`; an ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded to `capture_receipt_bytes` by dropping its oldest `events`/`tool_calls` and adding `truncated` (`list`, `kept`, `dropped`, `total`, `stream_bytes`, `stream_sha256` of the untruncated one-JSON-line-per-entry stream, `hint`), while `capture --full` is the explicit unbounded request; `--model`, `--effort`, and `--fast` map through the manifest config-option IDs and apply in model → effort → Fast order. For Claude Code's vendored bridge a `permit` answer settles only the reported `tool_call` status (the `claude -p` child takes no `--permission-prompt-tool`, so it cannot gate or resume the child). `permit` / `cancel` / `stop` settle each permission `request_id` at most once (same holder lock as prompt admission); a second settler on that id is `error.code` `unknown-request` and does not write another JSON-RPC result to agent stdin. Each holder process mints an opaque random `holder_instance_id` at construction — immutable for that process, never restored from `record.json` or the native session id, never derived from the PID — and exposes it on `record.json`, `status`/`observe`/`start` receipts, `kaola-acp-list/1` rows, and top-level on every `kaola-acp-view/1` payload (view plus follow snapshot/delta/heartbeat). `permit`, `cancel`, and the `key escape`→cancel alias accept optional `--expected-holder-instance-id VALUE`; when supplied — including an explicit empty value — the holder compares it against its own id under the settlement lock before any permission settlement, pending-permission cancellation, turn mutation, or outbound cancel, even when no permission/turn is active. A mismatch returns `error.code` `holder-instance-mismatch` with `expected_holder_instance_id` and the actual `holder_instance_id` inside the error object plus top-level `mutation_status` `not_started` and `mutation_performed` `false`; nothing is written to the agent. Omitting the flag keeps legacy unbound behavior. The binding is Runner envelope only and is never forwarded into native ACP method params.

Codex `--permission-mode` values are the same literal IDs on both transports but not the same semantics. ACP passes the ID through to the upstream adapter's `mode` option: `read-only` is upstream display name "Ask for approval" (workspace-write sandbox + on-request approval — workspace file writes are permitted without a permission request), `agent` is "Approve for me" (auto_review reviewer), `agent-full-access` is "Full access". PTY maps the same IDs to strict `--sandbox read-only|workspace-write|danger-full-access` plus `--ask-for-approval on-request|never`; OS-level read-only exists only via `--transport pty`. ACP does not claim equivalent enforcement. Start receipts surface the adapter's own display names/descriptions as factual evidence in `configured_options[*].option_name` / `option_description` / `value_name` / `value_description` when the adapter returns them.

ACP `observe`/`status` report `session_meta.configOptions` as the latest native-attested option list, not the launch snapshot. The `session/new`/`session/resume`/`session/load` result is the baseline (also surfaced as `initial_config_options`); a successful `session/set_config_option` result replaces the list wholesale, and `config_option_update` notifications for the same session refresh it. `configured_options[*].current_value` carries the adapter's native `currentValue` when returned — proof is the native response, never the requested value. Failed or timed-out updates and responses without usable config facts leave the last proven configuration untouched.

The ZCode adapter (Issue #62) reports three separately trackable session identities: the Runner session name (on every receipt), the ACP session id, and the native `sess_*` id. Once a backend session is materialized or faithfully resumed the adapter emits one credential-free `session/update {sessionUpdate: native_session_identity, acpSessionId, nativeSessionId}` notification, and `session/load` returns the adopted `sessionId` plus its `configOptions` so the holder's record and every receipt track which native session was loaded. Nested Host→Worker isolation is a process/session contract (separate process groups, separate record roots; the outer exact stop sweeps recorded inner sessions); the explicit runtime facts `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` are forwarded to a nested ZCode child, while the holder's `KAOLA_ACP_CHILD_RECORD` write handle and the denied credential names are never forwarded. See [ZCode host](zcode-host.md).

Human watch is not an L0 receipt. `kaola-acp list [--platform P] [--repo ROOT]` is the only command without a required platform positional or `--repo`; stdout is one `kaola-acp-list/1` object of live holders. `kaola-acp <platform> view --repo ROOT --session NAME [--since CURSOR]` stdout is one `kaola-acp-view/1` object. `kaola-acp <platform> follow --repo ROOT --session NAME [--since CURSOR] [--format text]` keeps the Unix socket open and writes NDJSON `{kind:snapshot|delta|heartbeat|eof|error}` lines; snapshot/delta payloads reuse `kaola-acp-view/1`. After the first `follow` op that FD is read-only (`prompt`/`permit`/`cancel`/`stop` reply `kind=error` and must use another short connection). A slow follower whose queue exceeds 256 lines gets `follow-dropped` and disconnects; other followers, `view`, and agent stdio continue. Killing the follow CLI does not stop holder/agent. Agent exit emits `kind=eof`, after which the holder closes that connection and the CLI exits; a dead holder emits `kind=error` `holder-lost`. View caps are enforced, not only flagged: thinking keeps an 8 KiB tail, one tool's content is clipped to 32 KiB, the timeline keeps the newest 200 messages, and a view over 256 KiB drops its oldest tools then oldest messages (`truncated=true`). Chunks without `messageId` join the previous same-role message until a tool call, new prompt, or turn end. `--format text` joins message/tool titles into tty text (not a TUI). Runtime facts use `error.code` in `holder-lost` / `holder-unreachable` / `no-session`. `kaola-tmux.sh PLATFORM view` prints `{"schema":"kaola-acp-view/1","error":{"code":"view-unsupported","message":"view is not a pty/tmux command; use kaola-acp"}}` and does not fall back to PTY; `follow` is likewise `follow-unsupported`. `install-local.sh --bin-links` (default on for the Codex runtime destination) also installs owned `$HOME/.local/bin/kaola-acp`, `kaola-acp-holder`, and `kaola-project-runner-locate` symlinks.

## Observation schema

`observe` returns evidence for the controlling agent. Ordinary PTY `observe`/`status` receipts
are bounded by `capture_receipt_bytes` (`kaola-observation.py bound_observation`): over budget,
`raw_current_frame` keeps its newest whole lines, then `child_processes` its first entries, and
`truncated.fields` records each bounded field's kept/total size or counts and the sha256 of
the full value; `snapshot_id` and `pane_revision` are computed from the full frame before
bounding. The budget is measured on the emitted line (newline included) and applied last:
`status`/`start` add `result` (and `legacy_ownership` for grok) inside `status-view` before
its bound, and a receipt bounded twice (build, then status-view) merges its `truncated`
block, keeping every original total, count, and digest and lowering only the kept figures. ACP `observe`/`status` receipts are bounded the same way by `bound_state_receipt`
in `kaola-acp.py`, on their own larger `state_receipt_bytes` budget (256 KiB, Issue #64:
a realistic platform `session_meta` — Devin's is ~70 KB — and the stored `record`
(~142 KB) stay whole, so `session_meta.configOptions` `currentValue` remains readable;
only larger structures are summarised) (`record`, `initial_config_options`, `session_meta`, `capabilities`,
`agent_info` summarised by size and sha256; `pending_permissions` keeps its newest entries).
Only `capture --full` is unbounded. Schema version 3 includes `snapshot_id`,
`pane_revision`, `raw_current_frame`, exact ownership and pane facts, runtime child/process evidence,
relay input/output facts, Git reporting facts, and compatibility editor/activity/approval/decision
signals. Those compatibility fields are advisory evidence for the controlling agent; generic
`send`/`stop` never consume them as semantic authority.

### `steer` — Agent-chosen steering of a running turn (Issue #65)

`steer --repo ABS_PATH --session NAME [--text TEXT | --stdin] [--steer-mode native|interrupt]
[--timeout SECONDS] [--cancel-timeout SECONDS]` delivers one Agent-chosen message to the turn that is
**already running** on that exact session. It is a tool the controlling Agent decides to use, never a
Runner policy, and it reuses the same session/repo routing as `send`: no scheduler, no second stdin
writer, and no second lifecycle. Its scope is the **ACP channel only** — over `pty` it answers
`steer-unsupported-transport`, since a mid-turn terminal write is an ordinary keystroke stream whose
meaning only the native UI decides.

Every platform has a usable path inside ACP, and the Agent picks which one:

- `--steer-mode native` uses the platform's own mid-turn entry and exists only where that entry
  really does. The manifest is the single source of truth: `native_steering` is `supported`,
  `unsupported` or `unknown` (an uninvestigated surface stays `unknown` and never masquerades as
  `unsupported`), `acp_steer_method` carries the entry and may be non-empty only when
  `native_steering` is `supported`, and `steering_summary` records the versioned evidence. Today
  `claude-code` (the vendored bridge's `claude --input-format stream-json` stdin, exposed as
  `_session/steering`) and `codex` (`_session/steering`, advertised at `initialize` under
  `_meta.steering`) qualify; the other seven have no such entry on their ACP surface at the pinned
  versions.
- `--steer-mode interrupt` is the composite and works on every platform: cancel the running turn,
  confirm it actually stopped, then send the text **once** as the next prompt on the same ACP
  session, so the conversation keeps its context. It is interrupted-then-continued, never injection —
  the running turn is ended, and work it already did (files written, commands run) is not undone.
- With no `--steer-mode`, a native platform uses `native`, and a platform without a native entry
  **refuses** with `steer-mode-required`, `available_steer_modes: ["interrupt"]`, and writes nothing.
  The Runner never interrupts a worker on its own initiative, and never silently degrades from
  `native` to `interrupt` after a failure or a timeout.
- A session whose `start` never negotiated an ACP session id cannot be prompted or
  steered at all: `send`, `steer` and the composite refuse with `no-acp-session`,
  `outcome: no_session`, `mutation_performed: false` and nothing written, rather
  than sending a frame with a null `sessionId` and reporting `in_progress` or
  `steer_consumed: true` for text no session received.

`steer_outcome` with `steer_consumed` and `steer_confirmation` carries the whole claim:

| `steer_outcome` | `steer_consumed` | `steer_confirmation` | Meaning |
|---|---|---|---|
| `injected` | `true` | `agent-confirmed` | the agent acknowledged that the running turn took it |
| `written` | `null` | `write-only` | flushed into the running turn's input, which this platform acknowledges in no way |
| `interrupted_and_resent` | `true` | `cancel-confirmed` | composite: the turn was cancelled and confirmed stopped, then this text ran as the next turn |
| `resent_without_interrupt` | `true` | `no-turn-to-interrupt` | composite: the turn had already ended on its own, so nothing was interrupted |
| `started_new_turn` | `true` | `agent-confirmed` | the agent opened a separate turn this holder does not track — not injection |
| `not_consumed` | `false` | `none` | nothing was written |
| `unsupported` | `false` | `none` | no native entry on this platform or transport |
| `rejected` | `false` | `none` | the agent refused; `error.detail` carries its reason |
| `unknown` | `null` | `none` | undecided — the Runner never resends blindly |

`mutation_performed` describes the steer itself, while `mutation_status` stays the running turn's.
The interrupted or steered turn keeps its own request id, output and terminal state: the native path
reports `turn_request_id`, `turn_request_id_after` and `turn_request_id_preserved`; the composite
reports `cancelled_turn_request_id`, `cancelled_turn_stop_reason` and a distinct
`new_turn_request_id`, plus `side_effects_possible: true`, because interrupting is not undoing. Both
report `steer_method`, `steer_request_id`, `steer_fingerprint`, `turn_prompt_fingerprint` and the raw
`steer_response`.

The composite's cancel is bound to the exact turn it targeted (`expected_request_id`), because
turns also start from worker events on another connection thread: if the targeted turn is replaced
before it can be interrupted, nothing is cancelled and nothing is sent (`steer-turn-changed`,
outcome `unknown`). The same applies if a different turn is admitted between the confirmed cancel
and the send — the text is not written and the outcome is `not_consumed`. The new turn's id comes
from the send's own admission, never from whatever turn happens to be running afterwards.

Two refusals protect against a double dispatch. An unconfirmed cancel sends **nothing**
(`steer-cancel-unconfirmed`, outcome `unknown`): a turn that will not confirm it stopped can never
receive a second prompt, and the Agent must `observe` before deciding — the Runner does not retry.
And an idle session is never natively steered: the holder refuses before writing, because some agents
answer an idle steering call by starting a detached turn (Codex 1.11.0 returns `startedNewTurn` even
when the request carries `idleBehavior: "promptRequired"`). The steering text is sent at most once in
either mode. A holder started before this release has no `steer` op and cannot gain one without a
restart, which answers `steer-holder-outdated` with nothing written.


The `relay` object reports relay epoch/process/socket, runtime child PID/PGID/path/start fingerprint,
child input/output offsets, streaming output digest, resize revision, bracketed-paste mode, and terminal
fence facts. `snapshot_id` is opaque correlation evidence. Any changed fact may produce a different
identifier, but that change is reported and never independently blocks an agent-directed action.

An absent or legacy-direct session may have no snapshot. Legacy direct sessions remain observable,
with `relay.managed: false` and `relay-required` in advisory `evidence_flags`; the agent decides how
to proceed from the available transport capabilities.

## Status compatibility

Commands return neutral JSON keys including `result`, `platform`, `runtime`, `session`, `repo`,
`present`, `owned`, `platform_match`, `repo_match`, `tui_detected`, `activity`,
`runtime_session_id`, pane identity, and Git branch/HEAD/cleanliness/ahead/behind. Grok additionally
returns `grok_tui` as a compatibility alias. Status also reports `process_match` and the observed
`pane_process`; a TUI is not accepted unless the live process matches the exact resolved runtime
binary at argv[0] or interpreter argv[1], except Kimi's exact `kimi-code` plus `node` product identity.
The Grok compatibility wrapper preserves `grok_version`, `project_root`, `grok_tui`, and legacy
ownership aliases. `status.activity` equals `status.activity_hint` for compatibility, but both are
advisory and excluded from action guards.

Preflight reports runtime binary/version, optional Workflow capability discovery, recurring evidence,
project materialization evidence, and an adapter-specific summary. Missing Workflow carriers,
configuration health, or materialization does not block the CLI communication channel.

Preflight also resolves the declared Runner default without starting a session. `start` gives an
explicit user model/effort precedence; otherwise `--tier default|upgrade` selects the manifest preset
(`default` when `--tier` is omitted). A bare `--model` wins over the tier preset and does not inherit
its effort; `--effort` only applies to the model selected in the same request. Model IDs that already
encode effort or Fast variants get no invented extra effort/configuration calls. `--fast` defaults to
`off`; `--fast on` is the per-run opt-in and is applied through the platform's native mechanism (Codex
ACP `fast-mode` configId / PTY `-c service_tier`, Cursor parameterized `fast` option or
`-fast`-style model variants, Claude process-scoped `--settings '{"fastMode": ...}'` passed
verbatim — the native CLI determines model support and effective reports `unknown` without
native evidence). Where no
native mechanism or advertised fast variant exists, the request is reported `resolved_fast:
"unsupported"`, never silently claimed. `--resume`/`--continue` without tier/model/effort preserves the
saved native session selection (`resume-preserved`); supplying any of them re-applies that selection.
There is no automatic escalation based on complexity, failures, or elapsed time. Catalog output is
reported as evidence and never rewrites or blocks the declared exact model literal. Actual mismatch,
catalog absence, or unreadable evidence never disables generic communication.

Model evidence under `model` includes `requested_model_source`, `requested_model_name`,
`requested_tier`, `requested_fast`, `resolved_runtime_model_id`, `resolved_parameters`,
`resolved_fast`, `actual_runtime_model_id`, `actual_parameters`, tri-state `model_verified`,
`model_mismatch_reason`, and structured provenance. ACP `start` receipts additionally carry
`model_selection` and per-option `config_application` receipts; a rejected or unadvertised
`set_config_option` is reported as a limitation and leaves the session usable.

Droid's default is Auto Model (`auto`) with no effort pin; `--tier upgrade` mirrors the default
and is a no-op. Effort is passed only when explicitly selected. Its native ACP mode option is
manifest-driven as `acp_mode_config_id: autonomy_level`; the default bypass value is
`auto-high`, and there is no bridge or translator.

## Agent-directed transport results

Every transport action verifies the exact session/repository/pane/relay/child identity and performs one
direct relay transfer. It does not quiesce the CLI, acquire a lease, fence the terminal, or create a
later-output barrier. `send` and `stop` do not require a snapshot. If legacy `--if-snapshot` is supplied,
the compact receipt returns it only as `based_on_snapshot`; a changed frame does not return
`stale-snapshot`. No generic action branches on editor, activity, approval, decision, worker count,
coordinate, prose, Git, Workflow, or later-output-barrier interpretations.

`send` returns the transferred payload fingerprint plus `mutation_performed:true`. If the relay reply
is lost or a partial write cannot be excluded, `mutation_performed` is `null`, never falsely `false`.
`key` accepts `up`, `down`, `left`, `right`, `enter`, `escape`, `tab`, `backtab`, or `space`; it sends
only that key's exact bytes, adds no Enter, and returns `result:key-sent` plus `payload_fingerprint`.
The controlling Agent owns the choice and meaning of the key.
`answer --replace-editor` is a capability-specific whole-editor transfer; Claude Code is the only v1
replacement capability, while other adapters report `answer-unsupported`. Decision IDs, revisions,
and any legacy later-output barriers are evidence for the agent and do not become generic follow-up
gates.

Before a follow-up, the controlling agent reads the raw frame and chooses how to handle any retained
draft, approval, output, login/trust, or decision surface. The Runner does not decide that choice.
After send/key, the agent observes/captures the response and, when applicable, verifies durable
Workflow/Git/forge state.

Input payloads reject CR, ESC, DEL, every other C0/C1 control except LF/TAB, invalid raw control
bytes, and embedded paste delimiters before any child PTY write. LF/TAB are accepted only when the
relay attests bracketed-paste mode. Send and Claude answer attest the exact transferred payload
fingerprint. Answer also attests clear-editor.

Ordinary and force stop do not require a snapshot. A successful force
stop reports `result: stopped`, `action: force-stop`, and terminal `final_state`; it cannot target a
session that the current transport cannot mechanically reach, and it is not emitted until the original
child/group and every exact fingerprint-tracked escaped descendant are absent.

Stop releases only the exactly-owned runtime: the PTY child/relay/tmux session, or — on ACP — a
`session/close` when the adapter advertises that capability followed by holder/agent exit, with
residual processes reported. The holder also notes process groups the agent spawned outside its
own group (for example the Claude bridge's detached `claude -p` children) from two sources: the
process tree when a turn is first accepted and again when stop begins (while the agent is alive to
be their parent), and the agent's own spawn record. The holder hands every agent
`KAOLA_ACP_CHILD_RECORD=<record dir>/children.jsonl`; the Claude bridge appends
`{pid, pgid, spawned_at, binary}` there synchronously at each spawn, before any child output can
be forwarded, so a child whose bridge died before its first `session/update` is still identified;
the variable is stripped from the child's own environment, so the CLI and the tools it runs never
see the path. The file is trusted exactly like `record.json` (same-user writable, under the record
root); the holder rewrites it at each agent start keeping only entries whose identity still holds.
Noted groups are recorded as `agent_child_pgids` with the member pids and start times seen
(`agent_child_groups`); after the agent group the holder sweeps every recorded group in which a
recorded member is still alive under its recorded start time, or under a start time at or before
its recorded spawn and within five seconds of it (SIGTERM, grace, SIGKILL), so a reused pid or group id is never
signalled; the stop receipt lists the signalled groups as `swept_child_pgids` and `residual_pids`
covers them. A holder-lost `stop --force` applies the same identity checks to `record.json` and
`children.jsonl`, SIGKILLs the live members of the recorded agent group plus the confirmed child
groups at once, and reports those groups as `swept_pgids`; a recorded normal stop reads as
`stopped` only when none of them is
alive. Stopping never deletes CLI history, session records, or work artifacts,
and no completion signal (`end_turn`, idle frame, successful receipt) triggers or gates it. Resume is
a separate Agent choice: `--resume <native-session-id>` (ACP `session/resume`/`session/load` per
advertised capability, or the platform's PTY flag) or `--continue` for the platform's latest
conversation; a missing identifier never blocks `stop`, and unsupported resume never blocks a fresh
`start`. The Runner performs no automatic shutdown, fallback, re-prompt, or Workflow continuation.
After a recorded normal ACP stop, `status`/`observe` report `outcome: stopped`,
`state: stopped`, `stopped: true`, and `residual_pids: []` when the recorded
holder, agent, and process group are absent. Unexpected holder death or remaining
process evidence continues to report `holder-lost`; other commands do not gain a
successful terminal receipt from this read-only distinction.

## Adapter interface

Each adapter declares identity, display name, executable, environment override, recurring support,
quit text, answer capability, and declared default-model facts. It implements `adapter_preflight`,
`adapter_build_launch`, `adapter_prepare_model_environment`,
`adapter_detect_tui`, `adapter_activity_hint`, `adapter_observe_frame`, and
`adapter_extract_session_id`. Adapters contain platform facts only and must not evaluate runtime- or
user-produced shell text. Starting a CLI does not invoke a Workflow materializer.

Claude, Cursor, and OpenCode painted placeholders and cursor coordinates are preserved as visible
evidence but never become input-origin authority.

Structural adapter facts describe visible chrome and compatibility hints for Agent review; they do
not decide input readiness or Workflow completion. Cursor CLI start does not call a Workflow
materializer or mutate `.cursor`; installed/global/project command surfaces are reported only.
