# Command and Contract Reference

## Renderer

```text
scripts/render-skills.py --write
scripts/render-skills.py --check
```

`--write` deterministically rebuilds ten managed worker Skill directories plus
`skills/kaola-project-runner/` from `templates/orchestrator/` (control plane; not an eleventh
platform), `skills/kaola-delegator/` from `templates/kaola-delegator/` (external
delegation Skill; not an eleventh platform), and the Grok Bot host bundle `hosts/grok-bot/`: `kaola-delegator.md` (the one
thin bridge Skill, from `templates/grok-bot/bridge.md.tmpl` and `accepted-revision.json`; at
the pinned stage it carries the accepted 40-hex commit and its label or release, the locator
command, and the one canonical entry path `ROOT/skills/kaola-delegator`, and no canonical content), `bridge.json`
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
flat YAML subset parsed without an external dependency. Transport fields are `acp_command`,
`acp_env_allowlist`, `acp_login_requires_pty`, `acp_init_meta`, `acp_model_config_id`,
`acp_effort_config_id`, `acp_mode_config_id`, `acp_fast_config_id`, `acp_fast_values`, `acp_model_map`, and
`clientCapabilities._meta` during `initialize` — Cursor's `parameterizedModelPicker=true` makes
its ACP surface advertise separate model/effort/fast options with base model IDs and string
`"true"`/`"false"` fast values; the model-scoped option set follows the selected model (Grok 4.7
advertises `reasoning_effort`, Claude Fable 5.1 `effort`). `acp_effort_config_id` is an ordered
`;` candidate list resolved against the options the agent advertises after the model apply; when
none is advertised the first candidate is sent literally, and a rejection stays a limitation
receipt. `acp_model_map` is an optional `picker-id=acp-option-value;...`
list mapping resolved catalog model IDs onto the ACP model value the agent advertises for the same
model; an effort encoded in the picker ID suffix travels through the effort option and Fast
through `acp_fast_values`-converted values, so semantics are never substituted — an unmapped ID
is sent literally and a rejection is reported as a limitation. `acp_command_default`,
`acp_command_upgrade`, and `acp_command_alt` are optional per-tier spawn commands (Issue #140; only
Devin declares them, as `devin acp --model <preset id>`): when the tier preset selects the model,
`kaola-acp.py` spawns that command instead of `acp_command`, while `--command`,
`KAOLA_ACP_COMMAND`, an explicit `--model`, or a preserved resume keep the base; an empty value, or
`acp_command_alt` without `alt_tier_label`, is rejected. `acp_session_new_timeout` is an optional
number of seconds in (0, 600] the holder waits for the `session/new` answer in `start` and the
`preflight` probe (Issue #146; absent keeps 15 s; only Codex declares it, `60`, because live Codex
answered after ~18 s). The client start window (20 s) and the probe bound (60 s) grow by the
amount it exceeds 15 s, keeping the margins they had over the default wait; the holder reports
no answer in time as `acp-session-timeout`. Model-selection fields are
`default_model_name`/`default_model_id`/`default_model_parameters`/`default_model_effort`,
`upgrade_model_name`/`upgrade_model_id`/`upgrade_model_parameters`/`upgrade_model_effort`,
`alt_tier_label`/`alt_model_name`/`alt_model_id`/`alt_model_parameters`/`alt_model_effort`, and
`fast_support`/`fast_summary`. The `alt_*` group is the optional third preset: `alt_tier_label`
carries the platform's own word for the tier (`alternative`, `fable`) and an empty label means
the platform declares no third tier, in which case the whole group must be empty and nothing
about it is rendered. It reaches the generated Skill through the computed `TIER_BLOCK`
(SKILL.md) and `ALT_TIER_LINE` (references/platform.md) blocks, never an unconditional
template sentence. They render as `ACP_COMMAND`, `ACP_QUIRKS`, and `ACP_LOGIN_REQUIRES_PTY`
template variables; `acp_login_requires_pty` only records whether login needs a native terminal —
login is a human act outside the Runner. The manifest key `default_transport` is removed
(Issue #130); the parser rejects it as an unexpected key, so `--check` fails closed if it returns.

An `acp_command` word may start with `$SKILL_DIR/scripts/` to name a file shipped inside the
Skill (Claude Code: `node $SKILL_DIR/scripts/vendor/claude-code-acp/dist/index.js`;
ZCode: `python3 $SKILL_DIR/scripts/kaola-zcode-acp.py`).
`kaola-acp.py` resolves that prefix to an absolute path before anything is spawned — against its
own `scripts/` directory in an installed Skill, else against the checkout layout whose `vendor/`
sits one level up — and reports the result as `bridge` (`relative`, `path`, `layout`
`skill|checkout`, `present`, `sha256`, `upstream_pin` from `acp_wrapper_pin`,
`verified_versions`) on `preflight` and `start`. A token that resolves to no file is
`error.code` `acp-bridge-missing` and nothing is spawned; there is no PATH lookup and no
download. For the Claude Code platform the Runner also resolves the exact runtime binary
(`CLAUDE_BIN`, else the first PATH match) and passes it to the bridge as
`CLAUDE_ACP_CLAUDE_BIN`, reporting it as `runtime_binary` (`env`, `path`, `absolute`, `present`,
`passed_as`, and on `preflight` the `--version` line); a non-absolute or missing value makes the
bridge fail closed (`session/new`, `session/resume`, and `session/prompt` return JSON-RPC
`-32603`) rather than search PATH. Grok's `initialize` returns no `agentInfo`, so a grok `start`
resolves the ACP command's first word on the agent's PATH, runs its `--version`, and records
`cli_version` (`path`, `version`, `verified_versions` from `acp_verified_versions`) in
`record.json`, holder state, and the start receipt's `transport` (Issue #124). It is a fact only:
a version that differs from the verified one, or an unreadable one, still starts. For ZCode the Runner never searches PATH: `preflight` and
`start` fail closed unless `KAOLA_ZCODE_ENTRY` and `KAOLA_ZCODE_NODE` are both explicit
absolute files (the adapter then launches `app-server --stdio` with `ELECTRON_RUN_AS_NODE=1`
and an allowlisted child environment, and hands the desktop App's enabled GLM Coding Plan
provider to the app-server in memory, read from `~/.zcode/v2/config.json` read-only. Which
in-memory mechanism applies depends on the installed app-server and is chosen by that
backend's own error, not a version gate: a pre-3.12 app-server takes the protocol's
`runtimeModel` overlay, while ZCode 3.12+ has removed `runtimeModel` and instead needs the
bundled provider table resolved next to the verified entry and injected as
`ZCODE_BUILTIN_PROVIDER_CONFIG_FILE` plus `ZCODE_PERSONAL_PROVIDER_CONFIG_FILE` (both or
neither, derived from that entry and never inherited), the plan registered through
`provider/updateAccountConfig`, the model selected on the `account:*` provider through
`session/setModel` with an explicit `options.reasoningLevel` and
`persistAsWorkspaceLastUsed: false`, and the credential supplied per model request through
`interaction/requestProviderRuntimeHeaders`. Start Plan and pay-as-you-go providers are
refused, `~/.zcode/cli/config.json` is never written, and the credential never reaches
receipts). The
`start`/`preflight` receipt's `agent_info._meta.zcode` carries the secret-free provider facts
(`providerId`, `baseURL`, `planCacheStatus`, `modelIds`, `rejectedProviders`). The bundled ZCode
runtime has no terminal UI; login happens in the ZCode desktop App. The
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

Platform IDs are `grok`, `claude-code`, `opencode`, `kimi-cli`, `cursor-cli`, `devin`, `codex`, `zcode`, `droid`, and `dsh`.
Omit `--platform` for all ten workers. `--platform` never selects the main Skill;
`kaola-project-runner` is not a platform ID. The orchestrator is installed for every `--runtime`
and `--skills-dir` destination unless `--no-orchestrator` is passed. Every selected destination is
preflighted before mutation; foreign paths are never replaced.

Droid's executable override is `DROID_BIN`. Its ACP command is the native
`droid exec --output-format acp`; no bridge or translator is used. Droid defaults to Auto Model
(`model=auto`) and full bypass (`autonomy_level=auto-high`). The supported
`--permission-mode` values are `bypassPermissions|low|medium|high|manual`; ACP maps them to
`auto-high|auto-low|auto-medium|auto-high|normal` through `acp_mode_config_id: autonomy_level`.
ACP model, reasoning-effort, and autonomy options use config IDs `model`, `reasoning_effort`, and
`autonomy_level`. Droid's default and upgrade presets are Auto (`auto`); its third tier `--tier core` is Kimi K3 Max
(`kimi-k3`, `reasoning_effort=max`), and it has no separate Fast toggle.

`--runtime` selects a verified consuming-runtime destination: `codex` →
`${CODEX_HOME:-$HOME/.codex}/skills`, `claude-code` → `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`,
`cursor` → `$HOME/.cursor/skills`, `devin` → `${DEVIN_CONFIG_DIR:-$HOME/.config/devin}/skills`,
`zcode` → `$HOME/.zcode/skills` (ZCode Host install; verified default discovery roots are the
workspace `.zcode/skills` and `.agents/skills`, which `--skills-dir` covers — see
[ZCode host](zcode-host.md)),
and (Issue #119, each measured as that CLI's Skill root) `grok-cli` → `$HOME/.grok/skills`,
`droid` → `$HOME/.factory/skills`, `opencode` → `$HOME/.config/opencode/skills`, and
`kimi-cli` / `dsh` → `$HOME/.agents/skills`; which platforms can run Project Runner as a Host,
and with which first line, is the `host_skill_entry` table in the main Skill's
`references/host-entry-matrix.md`.
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

Installed Skills are reference-counted shared blocks (Issue #123). Each receipt
(`kaola-project-runner-install/1`; `--method link` now writes one too, with `method: link` and no
`content_sha256`) carries `referrers`, the runtime ids using that Skill (`generic` for
`--skills-dir`). If the installed copy already matches this build, the install prints `refer:`
and only adds the reference. A copy from another build is updated in place (`update:`) and keeps
every referrer. `--uninstall`, including a Skill that is already absent, only removes this
runtime's id: while ids remain, the Skill and receipt stay (`kept: … (still referenced by …)`),
and when none remain the Skill is removed as before. A receipt without `referrers` predates the
ledger and counts as referenced by every runtime mapped to that root (`kimi-cli,dsh` for
`$HOME/.agents/skills`), so a guess never removes it.

`--bin-links` additionally manages the `$HOME/.local/bin/kaola-acp`, `kaola-acp-holder`, and
`kaola-project-runner-locate` symlinks to this repository's scripts. It defaults on only for the
Codex runtime destination; uninstall leaves the links alone unless `--bin-links` is passed
explicitly. They are counted by reference in the sidecar
`$HOME/.local/bin/.kaola-project-runner-bin-links.json` (`kaola-project-runner-bin-links/1`:
`links.<name>.target` and `referrers` of `{runtime, checkout}`). An existing link that resolves to
an executable file is referenced (`refer:`) and left pointing where it points. A link from before
the ledger records its creator as `{runtime: legacy, checkout: <checkout it resolves into>}`. A
dangling or non-executable link, or any non-symlink path, is still refused before anything is
written. `--uninstall --bin-links` removes this runtime-and-checkout reference, plus that
checkout's `legacy` entry. It unlinks a link only when no referrer remains and the link is this
checkout's own or the one recorded. The locator link is also kept while the Grok Bot
registration receipt `.kaola-project-runner-locate.json` exists beside it; the installer never
writes that receipt. A kept link is reported as `kept: … (…)`, and uninstall no longer exits
nonzero for a link another checkout made.

The Codex runtime destination (`--runtime codex`, or no destination flag) also installs one
Runner-owned user-level `SessionStart(compact)` recovery entry — id
`kaola-project-runner:user-compact-context` in `${CODEX_HOME:-$HOME/.codex}/hooks.json`, assets
under `${CODEX_HOME:-$HOME/.codex}/kaola-project-runner/hooks/` — whenever the control-plane Skills
are in the plan (Issue #97). `--no-orchestrator` skips it; `--uninstall` removes only that entry
and those assets; a generic `--skills-dir` destination and every other `--runtime` never touch a
`hooks.json`. Foreign entries are merged around by id and never changed, echoed, or copied; a
malformed user `hooks.json` is refused during planning, before the first Skill write. The
installer prints the hook receipt (`codex user hook: {…}`) and the trust note: Codex still asks
the owner to review and trust the new entry in `/hooks`, and hooks load at session start, so
recovery is not active in the session that ran the install. Direct actions:
`scripts/kaola-codex-compact-hook.py user-install|user-uninstall|user-status [--codex-home DIR]`;
the project-level `prepare|install|bind|uninstall|status --project-root ROOT` actions are
unchanged. See [Codex host](codex-host.md).

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
`registration-path-occupied`, `accepted-revision-superseded` when an existing receipt's
`accepted_revision` descends from the expected revision (rollback: remove the receipt first,
Issue #138)) leaves an existing link and registration receipt unchanged
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
`registration-stale` when HEAD is no longer the registered accepted revision), and an
`--expect-revision` that is a proper ancestor of the recorded accepted revision adds
`expect-revision-superseded` beside `revision-mismatch` (an unknown or unrelated one does not,
a descendant is only `revision-mismatch`); a plain
discovery call without `--target` tolerates an absent receipt but still refuses a mismatching
one. `result` is `ok` (exit 0) or `refused` (exit 1) with `reasons`; `--target` is required
when any of `--project`, `--worker`, `--session` is given. Revision and clean facts are what
the host's Git reports (index tricks or a tampered `.git` on a trusted host are outside this
boundary; no content hashing). Git runs with `GIT_TERMINAL_PROMPT=0`; no credential is read,
printed, hashed, or forwarded; paths in the receipt are local evidence and never enter an
account Skill.

## Runner entrypoint (`kaola-tmux.sh`)

The file keeps its historical name; it drives ACP only and starts no tmux session.

```text
scripts/kaola-tmux.sh PLATFORM preflight --repo ABS_PATH --session NAME
scripts/kaola-tmux.sh PLATFORM start     --repo ABS_PATH --session NAME [--continue | --resume ID] \
  [--tier default|upgrade|PLATFORM_TIER] [--model ID --effort low|medium|high|xhigh|max] [--fast on|off]
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

`--repo` must resolve to the exact Git top-level. A linked worktree is a valid Git top-level and
is not a transport refusal; preferring the consuming project's canonical
project root is Agent guidance, so a Workflow child worktree is not required as `--repo`.
Asking the CLI to invoke `workflow-next` is an Agent-selected prompt, not a Runner
operation. Session names match
`[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`. Without `--text`, `send` reads non-empty stdin.

`KAOLA_PROJECT_RUNNER_CANONICAL_REPO=<abs root>` declares Project Runner Orchestrator context. While
it is exported, `--repo` may be omitted and is completed from that root, and a `start` naming a
different root is refused with `{"result":"refused","reason":"canonical-root-mismatch"}` (or
`canonical-root-invalid` for an unusable binding) and `mutation_performed: false`, before anything
starts; accepted invocations add `canonical_repo` to the receipt. Other commands keep the `--repo`
they were given, so an existing session stays observable and exactly stoppable.

`--expected-holder-instance-id ID` binds `permit`, `cancel`, `key`, and `stop` to one ACP holder
instance. A mismatch returns `{"error":{"code":"holder-instance-mismatch"}}` with
`mutation_performed: false` and changes nothing, so a same-named session rebuilt by a later holder
is never stopped in place of the one the Agent verified.

Executable overrides are `GROK_BIN`, `CLAUDE_BIN`, `OPENCODE_BIN`, `KIMI_BIN`,
`CURSOR_AGENT_BIN`, `DEVIN_BIN`, and `DROID_BIN` (read by `preflight` for the runtime version
fact). The entrypoint's test/embedding override is `PYTHON_BIN`.

## Transport selection

ACP is the only transport (Issue #130). `--transport acp` is accepted as a no-op; `--transport pty` on any command is refused from the arguments alone, before the manifest, Git, the canonical-root binding (#73), or the dispatcher checks (#104) are read, and before any process, holder, record, or session exists. The refusal is one JSON line on stdout, exit 1:

```json
{"schema_version":3,"result":"refused","reason":"transport-pty-retired","action":"<command>","platform":"<id>","session":"<name>","repo":"<as given or empty>","detail":"PTY transport is retired (Issue #130); this Runner is ACP-only. Re-run without --transport (or with --transport acp).","mutation_performed":false,"mutation_status":"not_started","transport":{"requested":"pty","supported":["acp"]}}
```

Any other `--transport` value exits 1 with `--transport must be acp` on stderr. Every command dispatches to `kaola-acp.py`, and every schema-3 receipt's `transport` block is `{"selected":"acp"}` plus the ACP probe facts where a command adds them; the former `default`, `alternatives`, and `reason` keys are removed and `schema_version` stays 3. ACP supports `preflight`, `start`, `send`, `steer`, `wait`, `observe`, `capture`, `permit`, `cancel`, `stop`, `view`, and local `follow`; an ordinary `capture` receipt (`--lines`, `--since`, `--tools`) is bounded to `capture_receipt_bytes` by dropping its oldest `events`/`tool_calls` and adding `truncated` (`list`, `kept`, `dropped`, `total`, `stream_bytes`, `stream_sha256` of the untruncated one-JSON-line-per-entry stream, `hint`), while `capture --full` is the explicit unbounded request; `--model`, `--effort`, and `--fast` map through the manifest config-option IDs and apply in model → effort → Fast order. For Claude Code's vendored bridge a `permit` answer settles only the reported `tool_call` status (the `claude -p` child takes no `--permission-prompt-tool`, so it cannot gate or resume the child). `permit` / `cancel` / `stop` settle each permission `request_id` at most once (same holder lock as prompt admission); a second settler on that id is `error.code` `unknown-request` and does not write another JSON-RPC result to agent stdin. Each holder process mints an opaque random `holder_instance_id` at construction — immutable for that process, never restored from `record.json` or the native session id, never derived from the PID — and exposes it on `record.json`, `status`/`observe`/`start` receipts, `kaola-acp-list/1` rows, and top-level on every `kaola-acp-view/1` payload (view plus follow snapshot/delta/heartbeat). `permit`, `cancel`, and the `key escape`→cancel alias accept optional `--expected-holder-instance-id VALUE`; when supplied — including an explicit empty value — the holder compares it against its own id under the settlement lock before any permission settlement, pending-permission cancellation, turn mutation, or outbound cancel, even when no permission/turn is active. A mismatch returns `error.code` `holder-instance-mismatch` with `expected_holder_instance_id` and the actual `holder_instance_id` inside the error object plus top-level `mutation_status` `not_started` and `mutation_performed` `false`; nothing is written to the agent. Omitting the flag keeps legacy unbound behavior. The binding is Runner envelope only and is never forwarded into native ACP method params.

Codex `--permission-mode` values are literal upstream IDs, and their semantics are the upstream adapter's. ACP passes the ID through to the upstream adapter's `mode` option: `read-only` is upstream display name "Ask for approval" (workspace-write sandbox + on-request approval — workspace file writes are permitted without a permission request), `agent` is "Approve for me" (auto_review reviewer), `agent-full-access` is "Full access". ACP `read-only` is on-request approval, not an OS sandbox, and the Runner has no path to OS-level read-only (that existed only on the retired PTY transport). Start receipts surface the adapter's own display names/descriptions as factual evidence in `configured_options[*].option_name` / `option_description` / `value_name` / `value_description` when the adapter returns them.

ACP `observe`/`status` report `session_meta.configOptions` as the latest native-attested option list, not the launch snapshot. The `session/new`/`session/resume`/`session/load` result is the baseline (also surfaced as `initial_config_options`); a successful `session/set_config_option` result replaces the list wholesale, and `config_option_update` notifications for the same session refresh it. `configured_options[*].current_value` carries the adapter's native `currentValue` when returned — proof is the native response, never the requested value. Failed or timed-out updates and responses without usable config facts leave the last proven configuration untouched.

The ZCode adapter (Issue #62) reports three separately trackable session identities: the Runner session name (on every receipt), the ACP session id, and the native `sess_*` id. Once a backend session is materialized or faithfully resumed the adapter emits one credential-free `session/update {sessionUpdate: native_session_identity, acpSessionId, nativeSessionId}` notification, and `session/load` returns the adopted `sessionId` plus its `configOptions` so the holder's record and every receipt track which native session was loaded. Nested Host→Worker isolation is a process/session contract (separate process groups, separate record roots; the outer exact stop sweeps recorded inner sessions); the explicit runtime facts `KAOLA_ZCODE_ENTRY`/`KAOLA_ZCODE_NODE` are forwarded to a nested ZCode child, while the holder's `KAOLA_ACP_CHILD_RECORD` write handle and the denied credential names are never forwarded. See [ZCode host](zcode-host.md).

Human watch is not an L0 receipt. `kaola-acp list [--platform P] [--repo ROOT]` and `kaola-acp survey` (below) are the only commands without a required platform positional or `--repo`; stdout is one `kaola-acp-list/1` object of live holders; `--include-dead` (Issue #132) adds records whose holder PID is gone. Each row also carries `identity` (`verified` | `dead` | `unreachable` | `mismatch`: record, live PID, answering admin socket, and a `state` reply whose `holder_instance_id` equals the record's, probed with a 5 s bound), `host_class` (the standard Host name `<platform>-<CODE>-orchestrator-<purpose>`), `dispatcher` (the dispatching holder identity the holder inherited from `KAOLA_ACP_DISPATCHER`, or `null`), and the binding fact `heartbeat_host` / `heartbeat_host_known`. `kaola-acp <platform> view --repo ROOT --session NAME [--since CURSOR]` stdout is one `kaola-acp-view/1` object. `kaola-acp <platform> follow --repo ROOT --session NAME [--since CURSOR] [--format text]` keeps the Unix socket open and writes NDJSON `{kind:snapshot|delta|heartbeat|eof|error}` lines; snapshot/delta payloads reuse `kaola-acp-view/1`. After the first `follow` op that FD is read-only (`prompt`/`permit`/`cancel`/`stop` reply `kind=error` and must use another short connection). A slow follower whose queue exceeds 256 lines gets `follow-dropped` and disconnects; other followers, `view`, and agent stdio continue. Killing the follow CLI does not stop holder/agent. Agent exit emits `kind=eof`, after which the holder closes that connection and the CLI exits; a dead holder emits `kind=error` `holder-lost`. View caps are enforced, not only flagged: thinking keeps an 8 KiB tail, one tool's content is clipped to 32 KiB, the timeline keeps the newest 200 messages, and a view over 256 KiB drops its oldest tools then oldest messages (`truncated=true`). Chunks without `messageId` join the previous same-role message until a tool call, new prompt, or turn end. `--format text` joins message/tool titles into tty text (not a TUI). Runtime facts use `error.code` in `holder-lost` / `holder-unreachable` / `no-session`. `kaola-tmux.sh PLATFORM view` prints `{"error":{"code":"view-unsupported","message":"view is not a Runner command; use kaola-acp"},"schema":"kaola-acp-view/1"}`, exit 1; `follow` is likewise `follow-unsupported` (`"kind":"error"`). `install-local.sh --bin-links` (default on for the Codex runtime destination) also installs owned `$HOME/.local/bin/kaola-acp`, `kaola-acp-holder`, and `kaola-project-runner-locate` symlinks.

Installed platforms are a separate host-wide fact (Issue #147). `kaola-acp survey [--platform P] [--login-shell SHELL]` is read-only: it starts no agent, opens no ACP session, creates no holder, record, or record root, runs no platform binary (not even `--version`), and so spends no model turn. Its only child process is one non-interactive login shell (`SHELL -l -c`, stdin closed, bounded to 10 s and killed as a group on timeout), started from a fresh minimal environment (`HOME`, `SHELL`, `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `TERM=dumb`, plus `USER`/`LOGNAME`/`TMPDIR`/`LANG` when set), that prints its environment; the shell is `--login-shell`, else the account's login shell, else `$SHELL`, else `/bin/zsh`. A client with a narrow PATH (a GUI app subprocess) therefore sees what a new login sees. A `.zshrc`-only PATH edit is interactive-only and is not part of the login environment. Stdout is one `kaola-acp-survey/1` object, exit 0: `{schema, login_env, platforms}`. `login_env` is `{shell, shell_source: argument|account|SHELL|default, status: ok|unavailable, detail, path}` (`path` is the login PATH, `detail` says why it is unavailable). `platforms` has one row per platform in Runner order (`claude-code`, `codex`, `cursor-cli`, `devin`, `droid`, `dsh`, `grok`, `kimi-cli`, `opencode`, `zcode`; `--platform` keeps one), every row with the same keys: `platform`, `runtime_name`, `status` (`present` | `absent` | `unknown`), `installed` (`status == present`), `path` (the resolved executable or `null`), `source`, `binary`, `binary_env`, `requires_env`, `process_path`, and `login_path` (the manifest `binary_name` resolved on the invoking PATH and on the login PATH, each an executable path or `null`). `source` follows the Runner's launch order: `binary_env` (the manifest override in the invoking environment), `process_path`, `login_binary_env` (the same override exported by the login shell), then `login_path`. `absent` means neither environment resolves it; `unknown` means the invoking environment does not and the login environment could not be read, so absence is not established. ZCode keeps its launch rule: `binary` and `binary_env` are `null`, `requires_env` is `["KAOLA_ZCODE_ENTRY", "KAOLA_ZCODE_NODE"]`, and the row is `present` (`source` `process_env` or `login_env`, `path` the entry) only when both are absolute paths to an existing entry file and an executable runtime in one environment; a `zcode` on PATH or an installed application bundle is not probed. OpenCode Go is a provider route inside the `opencode` and `dsh` CLIs, not a separate binary, so those two rows carry it. `install-local.sh --bin-links` exposes the survey as `$HOME/.local/bin/kaola-acp survey`.

Quota packages are a separate read-only catalog (Issue #148). `kaola-acp packages [--platform P] [--installed-only] [--login-shell SHELL]` and `kaola-acp model-package --platform P --model ID` start no agent, open no session, create no holder or record, and spend no quota. Login environment is not required. `--installed-only` reuses the survey and keeps platforms whose `status` is `present`; only that flag runs the login shell. Stdout is one JSON object with sorted keys, exit 0. `packages` is `kaola-acp-packages/1`: `{schema, installed_only, platforms}` plus `login_env` only when `--installed-only`. Each platform row is `{platform, packages:[{id, name, windows, binds_models}]}`. `id` is `<platform>:<token>`; `windows` is null until seeded. `model-package` is `kaola-acp-model-package/1`: `{schema, platform, model, packageId, status}` where `status` is `mapped` or `unmapped` and `packageId` is the qualified id or null. A usage error exits 2. An id with no verified rule is unmapped, never a guessed package. Example, mapped: `{"model": "grok-4.7", "packageId": "grok:account", "platform": "grok", "schema": "kaola-acp-model-package/1", "status": "mapped"}`. Example, unmapped: `{"model": "claude-opus-5-5", "packageId": null, "platform": "droid", "schema": "kaola-acp-model-package/1", "status": "unmapped"}`. `observe`/`status` stamp model leaves on the emitted receipt only (`quotaPool` qualified id, or `quotaPool` null and `quotaPoolStatus` `unmapped`). `view` adds `models.availableModels` and `models.options` (the model config option only) from a copy. Stored `session_meta` and `record.json` stay the native ACP payload. The Project Runner reference is `references/quota-packages.md`.

## Observation schema

`observe` returns evidence for the controlling agent. ACP `observe`/`status` receipts are bounded by `bound_state_receipt`
in `kaola-acp.py`, on their own `state_receipt_bytes` budget (256 KiB, Issue #64:
a realistic platform `session_meta` — Devin's is ~70 KB — and the stored `record`
(~142 KB) stay whole, so `session_meta.configOptions` `currentValue` remains readable;
only larger structures are summarised) (`record`, `initial_config_options`, `session_meta`, `capabilities`,
`agent_info` summarised by size and sha256; `pending_permissions` keeps its newest entries).
Only `capture --full` is unbounded. Every schema-3 receipt carries `platform`, `session`, `repo`,
`transport` and Git reporting facts (`git`); these are evidence for the controlling agent and never
semantic authority for `send`/`stop`.

ACP receipts also report the notification binding in force (Issue #70). `start`, `observe`
and `status` carry `heartbeat_host`: the target the running holder really adopted, or `null`
for an ordinary unbound worker; a holder or record written before the field exists instead
answers `heartbeat_host_known: false` (unknown, never reported as unbound), and a receipt with
no session at all stays silent. `start` keeps what it asked for separately in
`heartbeat_host_requested`, and a `session-exists` start reports the reused holder's binding,
so a later environment change or a repeated `start` can never look like a rebinding.

A `start` receipt also says where its request came from (Issue #104): `heartbeat_host_source` is
`none` (no dispatching holder, no variable), `explicit` (`KAOLA_ACP_HEARTBEAT_HOST` given),
`dispatcher` (derived from the holder-set `KAOLA_ACP_DISPATCHER` identity fact: `holder_instance_id`,
`platform`, `repo`, `session`, echoed as `dispatcher`), or `dispatcher-no-carrier` (a dispatcher
whose platform has no measured `host_skill_entry`; since Issue #126 admitted codex, no shipped
platform). Issue #122: that row, an explicit
variable naming such a platform, and a Host-named `start` on it are refused `host-entry-unsupported`
(`detail` names the platform and the empty entry), exit 1, before anything exists. On the `dispatcher` path the script verifies the named Host holder is live
before anything exists and otherwise refuses with `{"result":"refused","reason":
"heartbeat-host-unresolved"}` (`detail` names the failed check), exit 1; an explicit variable naming a
different Host than the dispatcher is `heartbeat-host-conflict`. The former #104 reason
`heartbeat-host-pty-unsupported` is retired: a `--transport pty` request is now refused
`transport-pty-retired` for every caller, ahead of these checks. Every refusal carries `mutation_performed: false`; standalone starts are unchanged.

A ZCode `start` also checks, before anything is spawned, that the worker Skill copies its agent will
load are the same build as the Skill tree this CLI was loaded from (Issue #105). The Issue #104
binding lives in the copy a worker `start` executes, so a Host on a new build with an older installed
worker Skill dispatches unbound workers and exits 0. The check hashes `kaola-acp.py`,
`kaola-acp-holder.py`, `kaola-tmux.sh` (and `kaola-zcode-acp.py` where both sides ship it) in every
Skill directory under the four default ZCode discovery roots — `<repo>/.zcode/skills`,
`<repo>/.agents/skills`, `~/.zcode/skills`, `~/.agents/skills` — that contains
`scripts/kaola-acp.py`. Any difference is `{"result":"refused","reason":"worker-skill-build-skew"}`,
exit 1, nothing created; `worker_skill_skew` names the differing paths with both 12-hex digests and
`worker_skill_skew_count` the total. A passing `start` reports `worker_skill_build` (this build's
`kaola-acp.py` digest) and `worker_skill_roots` (each root and the Skill names compared), so `status`
reconciliation has the fact. Both are `null` when the CLI ran from a repository checkout rather than
an installed Skill tree: no Skill build to be the baseline, so the answer is unknown, not aligned.
Roots that ZCode reaches only through ancestor directories, `skills.roots`, or `plugins.dirs` are not
compared.

The main `kaola-project-runner` Skill ships no scripts, so the same Host `start` compares it separately
(Issue #121): every worker Skill carries the main Skill's build record, `scripts/main-skill-build.json`
(the per-file sha256 of the rendered main Skill and a 12-hex `build` over them). After the worker check
passes, every Skill directory in the same roots whose `SKILL.md` frontmatter is
`name: kaola-project-runner` (a renamed backup copy included) must have every recorded file with the
recorded digest; extra files are ignored. Any difference is
`{"result":"refused","reason":"main-skill-build-skew"}`, exit 1, nothing created and no root changed;
`main_skill_skew` lists each stale copy's `path`, `installed` and `expected` build and differing
`files`, `main_skill_skew_count` the total, and `detail` names the paths, both builds, and the repair
(re-run `install-local.sh` for that root or remove the copy). A passing Host `start` reports
`main_skill_build`, which is `null` when there is no record to compare (a checkout invocation or a
worker Skill built before the record).

One live Host per canonical root (Issue #132). Before anything else a Host-named `start` (any
platform, a `KAOLA_ACP_DISPATCHER`-dispatched one included) enumerates the other Host-named records
of the same canonical root and refuses `{"result":"refused","reason":"host-exists"}`, exit 1,
nothing created, unless every one is provably free: a dead holder PID, or a live PID that is
silent and whose argv is provably another process (compared as resolved paths; read through
`ps`, or `KERN_PROCARGS2` where a Seatbelt profile blocks `ps`). A row that passes the identity check, answers
under another instance id (`mismatch`), or is silent while its argv still names the record (an
initializing or wedged holder) holds the root. `existing_host` carries its `platform`, `session`,
`identity`, `holder_pid`, `holder_instance_id`, `acp_session_id`, and `state`, plus
`answering_holder_instance_id` on `mismatch` and `argv: "unreadable"` when a silent holder's argv
cannot be read, e.g. by a Seatbelt-sandboxed caller for another user's process or a zombie
(`existing_hosts`
lists all when there are several). The `list` identity probe is bounded at 2 s per socket, the start
guard's at 5 s; a silent derived socket is followed by at most one more probe of the socket the
holder's own argv names. A same-name start keeps `session-exists`, now only for a holder that
passes the check or whose live PID's argv still names this record directory (`error.identity`
reports the check). A live PID whose argv is provably another process is a reused PID: the start
replaces the stale record without signalling it and reports `replaced_record.pid_reused: true`.
`stop --force` on a live PID whose socket is absent or silent checks
`--expected-holder-instance-id` against the record (`holder-instance-mismatch`, nothing written),
stops a holder that answers, as the record's own instance, on the `--socket` its own argv names (a holder started under another
spelling of the same record root, e.g. `/tmp` vs `/private/tmp`, derives another socket path) with an
ordinary stop over that socket (`answering_socket`), and signals only a silent PID whose argv anchors
it to the record (`holder_force_killed`); a reused PID
gets no signal (`pid_reused: true`, `holder_signalled: false`), the dead holder's recorded groups
are swept exactly as for any dead holder (`force_killed_pids`: the agent's own process group when
its live leader still has the start time the holder recorded as `agent_started` (epoch seconds,
so time zones do not matter) at spawn, or has no
live leader left; a record written before `agent_started` keeps the group trusted as before; plus
child groups that still match their recorded start time), and the record is retired once nothing of them is left
(later `status` reads `no-session`; a survivor keeps the record and appears in `residual_pids`). An
unreadable argv refuses `holder-unreachable`. A force stop of a dead
holder that leaves nothing of its recorded groups marks the record `stopped`, so `status` reads
`stopped` with `residual_pids: []`.

### `steer` — Agent-chosen steering of a running turn (Issue #65)

`steer --repo ABS_PATH --session NAME [--text TEXT | --stdin] [--steer-mode native|interrupt]
[--timeout SECONDS] [--cancel-timeout SECONDS]` delivers one Agent-chosen message to the turn that is
**already running** on that exact session. It is a tool the controlling Agent decides to use, never a
Runner policy, and it reuses the same session/repo routing as `send`: no scheduler, no second stdin
writer, and no second lifecycle. It works over ACP, the only channel; the former
`steer-unsupported-transport` reason is retired with the PTY transport (Issue #130).

Every platform has a usable path inside ACP, and the Agent picks which one:

- `--steer-mode native` uses the platform's own mid-turn entry and exists only where that entry
  really does. The manifest is the single source of truth: `native_steering` is `supported`,
  `unsupported` or `unknown` (an uninvestigated surface stays `unknown` and never masquerades as
  `unsupported`), `acp_steer_method` carries the entry and may be non-empty only when
  `native_steering` is `supported`, and `steering_summary` records the versioned evidence. Read the
  current roster out of `platforms/*.yaml` rather than from this page: which platforms qualify
  changes as surfaces are investigated, so no count or list is pinned here. One case worth knowing is
  `opencode`, whose `-32601` probe ran on 1.18.17 and whose 2.0.11 `initialize` advertised no
  steering `_meta`, while `acp_verified_versions` names 2.0.15 (record-only since the 2026-09-24
  Pink batch) and no steering method was re-probed on either newer build: it is `unknown`, and the
  Runner reports an unverified capability (`steer_outcome: unknown`, `steer-capability-unknown`)
  instead of a proven absence. The refusal, the explicit composite and
  the no-auto-degrade rule are identical for `unsupported` and `unknown` alike.
- `--steer-mode interrupt` is the composite and works on every platform: cancel the running turn,
  confirm it actually stopped, then send the text **once** as the next prompt on the same ACP
  session, so the conversation keeps its context. It is interrupted-then-continued, never injection —
  the running turn is ended, and work it already did (files written, commands run) is not undone.
  The resend opens a new turn carrying the Agent's text verbatim on every session — it is not a
  Host recovery entry and adds no native Skill entry line; a caller wanting the resend to open a
  ZCode Host round supplies `/kaola-project-runner` as the text's own first line.
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

A `not_consumed` receipt can still carry `steer_confirmation: agent-confirmed` with
`error.code: steer-queued` and `mutation_performed: true` when the platform admitted the
text to its own follow-up queue — durable for a later turn, but not consumed by the
running one (Issue #81).

`mutation_performed` describes the steer itself, while `mutation_status` stays the running turn's.
The interrupted or steered turn keeps its own request id, output and terminal state: the native path
reports `turn_request_id`, `turn_request_id_after` and `turn_request_id_preserved`; the composite
reports `cancelled_turn_request_id`, `cancelled_turn_stop_reason` and a distinct
`new_turn_request_id`, plus `side_effects_possible: true`, because interrupting is not undoing. Both
report `steer_method`, `steer_request_id`, `steer_fingerprint`, `turn_prompt_fingerprint` and the raw
`steer_response`.

The composite binds to the turn **object** it targeted, not merely to its id: `self.turn` is
replaced when a prompt is admitted, so the cancel's admission check, its outbound `session/cancel`,
its wait and its receipt are all taken from that one turn while the lock is held, and nothing
downstream re-reads `self.turn`. Turns also start from worker events on another connection thread,
so this matters in ordinary operation. If the targeted turn simply finishes on its own before the cancel goes out, no cancel is sent and
the receipt is `resent_without_interrupt` with `cancel_sent: false` — an interruption that did not
happen is never claimed. If the targeted turn is replaced, the outcome is `unknown`
with `steer-turn-changed` and the steering text is not sent; `cancel_sent` distinguishes "nothing
was cancelled" (`false`) from "the target was asked to stop and we cannot confirm what followed"
(`true`), and `side_effects_possible` is reported for both. If the target did stop but another turn
already owns the session, the answer is the same refusal rather than a dispatch onto a turn nobody
asked to steer. The new turn's id comes from the send's own admission, never from whatever happens
to be running afterwards, and a late answer to a finished turn can no longer settle the turn
running now.

Two refusals protect against a double dispatch. An unconfirmed cancel sends **nothing**
(`steer-cancel-unconfirmed`, outcome `unknown`): a turn that will not confirm it stopped can never
receive a second prompt, and the Agent must `observe` before deciding — the Runner does not retry.
And an idle session is never natively steered: the holder refuses before writing, because some agents
answer an idle steering call by starting a detached turn (Codex 1.11.0 returns `startedNewTurn` even
when the request carries `idleBehavior: "promptRequired"`). The steering text is sent at most once in
either mode. A holder started before this release has no `steer` op and cannot gain one without a
restart, which answers `steer-holder-outdated` with nothing written.


## Status compatibility

Preflight reports runtime binary/version, optional Workflow capability discovery, recurring evidence,
project materialization evidence, and an adapter-specific summary. Missing Workflow carriers,
configuration health, or materialization does not block the CLI communication channel.

Preflight also resolves the declared Runner default without starting a session. `start` gives an
explicit user model/effort precedence; otherwise `--tier default|upgrade` selects the manifest preset
(`default` when `--tier` is omitted). A platform may declare one further preset under its own word
(`alt_tier_label`); requesting a tier the platform does not declare is the typed refusal
`{"result": "refused", "reason": "tier-not-declared"}` at exit 1, naming `available_tiers`,
never a silent fallback to `default`. A bare `--model` wins over the tier preset and does not inherit
its effort; `--effort` only applies to the model selected in the same request. Model IDs that already
encode effort or Fast variants get no invented extra effort/configuration calls. `--fast` defaults to
`off`; `--fast on` is the per-run opt-in and is applied through the platform's native mechanism (Codex
ACP `fast-mode` configId, Cursor parameterized `fast` option, the Claude bridge's `fast` config option, which the
vendored bridge turns into a per-turn `--settings '{"fastMode": ...}'` — the native CLI determines model support and effective reports `unknown` without
native evidence). Where no
native mechanism or advertised fast variant exists, the request is reported `resolved_fast:
"unsupported"`, never silently claimed. `--resume`/`--continue` without tier/model/effort preserves the
saved native session selection (`resume-preserved`); supplying any of them re-applies that selection.
There is no automatic escalation based on complexity, failures, or elapsed time. Catalog output is
reported as evidence and never rewrites or blocks the declared exact model literal. Actual mismatch,
catalog absence, or unreadable evidence never disables generic communication.

Model evidence under `model` on the `start`/`preflight` receipt includes `requested_model_source`,
`requested_model_name`, `requested_tier`, `requested_fast`, `resolved_runtime_model_id`,
`resolved_parameters`, `resolved_fast`, and structured provenance. `actual_runtime_model_id` and
`actual_parameters` are always `null` and `model_verified` is always `unknown`
(`model_mismatch_reason: actual-model-evidence-not-yet-read`): ACP computes no true/false verdict.
The agent's actual selection is `effective_selection` on `start`, beside
`resolved_runtime_model_id`; its `effort_config_id` names the effort option id it was read from
(the resolved `acp_effort_config_id` candidate). When the spawn argv already carries the resolved
model as `--model`, the model option is not re-sent: `config_application.model` is
`{"applied": true, "applied_via": "argv", "value": ...}` and `effective_selection.effective_model`
is that id with `effective_model_source: "launch-argv"`, the agent's own (possibly stale) value kept
as `advertised_model`. `status`/`observe` carry no request provenance; they report the
agent's own `session_meta.configOptions[].currentValue`. ACP `start` receipts additionally carry
`model_selection` and per-option `config_application` receipts; a rejected or unadvertised
`set_config_option` is reported as a limitation and leaves the session usable.

Droid's default is Auto Model (`auto`) with no effort pin, and `--tier upgrade` is the same Auto
preset because no stronger Droid tier is established. Its third tier, `--tier core`
(`alt_tier_label: core`), is Kimi K3 Max (`kimi-k3` at `reasoning_effort=max`) — a separate tier
below the default, not an upgrade. Both ids are first-class catalog values, so `acp_model_map`
stays empty. `--tier alternative` stays the typed `tier-not-declared` refusal. Its native ACP mode option is
manifest-driven as `acp_mode_config_id: autonomy_level`; the default bypass value is
`auto-high`, and there is no bridge or translator.

## Agent-directed transport results

Every action goes through the exact session's ACP holder. It does not quiesce the CLI, acquire a
lease, or create a later-output barrier. `send` and `stop` do not require a snapshot; the parser
still accepts legacy `--if-snapshot` and `--replace-editor` but does not forward them. No generic
action branches on editor, activity, approval, decision, worker count, prose, Git, Workflow, or
later-output-barrier interpretations.

`send` writes the text as one `session/prompt` text block over the agent's stdio JSON-RPC, never
through a shell or a terminal, and returns `prompt_fingerprint` (`sha256:` of the text) with
`mutation_performed: true` once the frame is written; a frame that was not written is
`acp-write-failed` with `mutation_performed: false`. `key` accepts only `escape`, which maps to
ACP `cancel`; every other key is `key-unsupported`. `answer` is `answer-unsupported` ("use send;
--decision-id maps to permit --request-id"). There is no native key, menu, or editor-replacement
transfer on ACP, and no Runner path to one since the PTY transport was retired (Issue #130).

After send, the agent observes/captures the response and, when applicable, verifies durable
Workflow/Git/forge state. The Runner does not decide how to handle a draft, approval, output,
login/trust, or decision surface.

Stop releases only the exactly-owned runtime: a
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
advertised capability) or `--continue` for the platform's latest
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
`adapter_extract_session_id`. Since Issue #130 the entrypoint calls only `adapter_preflight`, for
the base facts it adds to the ACP `preflight` receipt (Issue #114); the launch, TUI, and frame
functions remain in the files until a follow-on removes them. Adapters contain platform facts only
and must not evaluate runtime- or user-produced shell text. Starting a CLI does not invoke a
Workflow materializer. Cursor CLI start does not call a Workflow
materializer or mutate `.cursor`; installed/global/project command surfaces are reported only.
