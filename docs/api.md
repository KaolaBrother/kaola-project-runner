# Command and Contract Reference

## Renderer

```text
scripts/render-skills.py --write
scripts/render-skills.py --check
```

`--write` deterministically rebuilds seven managed worker Skill directories plus
`skills/kaola-project-runner/` from `templates/orchestrator/` (control plane; not an eighth
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
`acp_command`, `acp_client_capabilities`, `acp_quirks`, `acp_verified_versions`,
`acp_env_allowlist`, `acp_login_requires_pty`, `acp_init_meta`, `acp_model_config_id`,
`acp_effort_config_id`, `acp_fast_config_id`, `acp_fast_values`, `acp_model_map`, and
`acp_wrapper_pin`. `acp_init_meta` is an optional `key=value;...` list sent as
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
Skill (Claude Code: `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`).
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
`-32603`) rather than search PATH. The renderer copies `dist/index.js`, `dist/DERIVATION.json`,
`LICENSE`, and `UPSTREAM.md` from `vendor/claude-code-acp/` into the Claude Code worker only;
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

Platform IDs are `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, and `codex`.
Omit `--platform` for all seven workers. `--platform` never selects the main Skill;
`kaola-project-runner` is not a platform ID. The orchestrator is installed for every `--runtime`
and `--skills-dir` destination unless `--no-orchestrator` is passed. Every selected destination is
preflighted before mutation; foreign paths are never replaced.

`--runtime` selects a verified consuming-runtime destination: `codex` →
`${CODEX_HOME:-$HOME/.codex}/skills`, `claude-code` → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`,
`cursor` → `$HOME/.cursor/skills`, `devin` → `${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills`,
`--runtime grok-bot` (and `grokbot`) is refused: Grok Bot is a bridge host with no installer
destination (see [Grok Bot host](grok-bot-host.md)). `--runtime grok` is not a host alias;
`--platform grok` is the Grok CLI worker.
`--skills-dir` is a mutually exclusive explicit absolute destination (project-local paths included).
With neither flag the legacy Codex destination is used. `--method copy` (default) stages an
identical standalone copy on the destination filesystem and records a per-Skill receipt at
`<skills-dir>/.kaola-install-receipts/<skill>.json` (outside the generated payload). `--method link`
is an explicit development choice that creates exact owned symlinks to this checkout. An owned
source symlink migrates to a copy when reinstalled with the default or `--method copy`. An
unchanged owned copy is a no-op; only an unmodified owned installation is replaced or removed; a
`.generated` marker without a valid receipt is not delete authority. `--uninstall` affects only the
selected destination and selected owned Skills.

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

`--repo` must resolve to the exact Git top-level. Session names match
`[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`. Without `--text`, `send` reads non-empty stdin.

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`,
`CURSOR_AGENT_BIN`, and `DEVIN_BIN`. Test/embedding overrides are `TMUX_BIN`, `PYTHON_BIN`, `PS_BIN`, and
`KAOLA_START_TIMEOUT`; `GROK_START_TIMEOUT` remains a Grok-only compatibility alias.

## Transport selection

Every command accepts `--transport acp|pty`. Without an override, the platform manifest selects the default. ACP dispatches to `kaola-acp.py`; PTY retains the nested-relay path. Receipts report the selected/default transports, alternatives, and whether selection came from `manifest-default` or `caller-override`. ACP supports `preflight`, `start`, `send`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, `view`, and local `follow`; an ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded to `capture_receipt_bytes` by dropping its oldest `events`/`tool_calls` and adding `truncated` (`list`, `kept`, `dropped`, `total`, `stream_bytes`, `stream_sha256` of the untruncated one-JSON-line-per-entry stream, `hint`), while `capture --full` is the explicit unbounded request; `--model`, `--effort`, and `--fast` map through the manifest config-option IDs and apply in model → effort → Fast order. `permit` / `cancel` / `stop` settle each permission `request_id` at most once (same holder lock as prompt admission); a second settler on that id is `error.code` `unknown-request` and does not write another JSON-RPC result to agent stdin. Each holder process mints an opaque random `holder_instance_id` at construction — immutable for that process, never restored from `record.json` or the native session id, never derived from the PID — and exposes it on `record.json`, `status`/`observe`/`start` receipts, `kaola-acp-list/1` rows, and top-level on every `kaola-acp-view/1` payload (view plus follow snapshot/delta/heartbeat). `permit`, `cancel`, and the `key escape`→cancel alias accept optional `--expected-holder-instance-id VALUE`; when supplied — including an explicit empty value — the holder compares it against its own id under the settlement lock before any permission settlement, pending-permission cancellation, turn mutation, or outbound cancel, even when no permission/turn is active. A mismatch returns `error.code` `holder-instance-mismatch` with `expected_holder_instance_id` and the actual `holder_instance_id` inside the error object plus top-level `mutation_status` `not_started` and `mutation_performed` `false`; nothing is written to the agent. Omitting the flag keeps legacy unbound behavior. The binding is Runner envelope only and is never forwarded into native ACP method params.

Codex `--permission-mode` values are the same literal IDs on both transports but not the same semantics. ACP passes the ID through to the upstream adapter's `mode` option: `read-only` is upstream display name "Ask for approval" (workspace-write sandbox + on-request approval — workspace file writes are permitted without a permission request), `agent` is "Approve for me" (auto_review reviewer), `agent-full-access` is "Full access". PTY maps the same IDs to strict `--sandbox read-only|workspace-write|danger-full-access` plus `--ask-for-approval on-request|never`; OS-level read-only exists only via `--transport pty`. ACP does not claim equivalent enforcement. Start receipts surface the adapter's own display names/descriptions as factual evidence in `configured_options[*].option_name` / `option_description` / `value_name` / `value_description` when the adapter returns them.

ACP `observe`/`status` report `session_meta.configOptions` as the latest native-attested option list, not the launch snapshot. The `session/new`/`session/resume`/`session/load` result is the baseline (also surfaced as `initial_config_options`); a successful `session/set_config_option` result replaces the list wholesale, and `config_option_update` notifications for the same session refresh it. `configured_options[*].current_value` carries the adapter's native `currentValue` when returned — proof is the native response, never the requested value. Failed or timed-out updates and responses without usable config facts leave the last proven configuration untouched.

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
in `kaola-acp.py` (`record`, `initial_config_options`, `session_meta`, `capabilities`,
`agent_info` summarised by size and sha256; `pending_permissions` keeps its newest entries).
Only `capture --full` is unbounded. Schema version 3 includes `snapshot_id`,
`pane_revision`, `raw_current_frame`, exact ownership and pane facts, runtime child/process evidence,
relay input/output facts, Git reporting facts, and compatibility editor/activity/approval/decision
signals. Those compatibility fields are advisory evidence for the controlling agent; generic
`send`/`stop` never consume them as semantic authority.

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
residual processes reported. Stopping never deletes CLI history, session records, or work artifacts,
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
